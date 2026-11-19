"""Infer external source effects without concrete allocations or C emission."""
from owned_join_types import (
    OWNED_JOIN_TYPES, owned_result_type,
)
from option_join_types import (
    OPTION_JOIN_TYPES,
)
from exchange_join_types import (
    EXCHANGE_JOIN_TYPES,
)
from utf8_syntax import ASYNC_CAPTURE_VIEW_MODES, ERROR_VALUE_TYPES, RESULT_ERROR_MODES
from utf8_syntax import PLAIN_JOIN_TYPES, PLAIN_JOIN_PAYLOADS, PLAIN_RETURN_JOINS
from utf8_syntax import VECTOR_SPLIT_TYPES, VECTOR_SLICE_MODES, VECTOR_OPTION_MODES, VECTOR_REPLACE_MODES, VECTOR_TRY_PUSH_MODES, VECTOR_PAYLOAD_TYPES, UTF8_EXPRESSION_MODES, UTF8_METHODS, UTF8_TEXT_RESULT, UTF8_SLICE_RESULT, VALUE_MODES
from dataclasses import dataclass

from array_syntax import HANDLE_VECTORS, INLINE_VECTOR_ELEMENTS, is_handle_vector, handle_vector_element, register_handle_vector
from array_syntax import consumed_result_expression, SHARED_REF_VECTOR, REFERENCE_VECTORS, ARRAY_STATEMENTS, HANDLE_VECTOR, VECTOR_TYPES, VECTOR_ELEMENTS, vector_method, array_operands, fixed_array_shape, reference_type


ARRAY_METHOD_ARITY = {'len': 0, 'ref': 0, 'mut_ref': 0, 'replace': 2, 'swap': 2}


def method_candidate(expr, nominal=None, functions=()):
    if expr[0] == 'task_join' and f'{nominal}.join' in functions:
        return ('method_call', ('name', expr[1]), 'join', [])
    op = expr[0]
    if op == 'method_call':
        return expr
    if op == 'new' and expr[4:] in (('typed_pool',), ('pool_default',)):
        return ('method_call', ('name', expr[1]), 'new', [expr[2]] if expr[4] == 'typed_pool' else [])
    if op == 'struct_copy':
        return ('method_call', ('name', expr[1]), 'copy', [('name', expr[2])])
    if op == 'array_split':
        return ('method_call', expr[1], 'split_at_mut', [expr[2]])
    if op.startswith('array_') and op[6:] in ARRAY_METHOD_ARITY and expr[1][0] == 'name':
        return ('method_call', expr[1], op[6:], list(expr[2:]))
    return None


def allocation_value_borrow(typ, method, functions=()):
    if typ is None or typ == 'Allocator' or typ.startswith('Pool<') or f'{typ}.{method}' in functions:
        return None
    return {'vref': 'ref', 'mut_vref': 'mut'}.get(method)


def allocation_handle_method(typ, method, functions=()):
    if typ is None or typ == 'Allocator' or typ.startswith(('Pool<', 'A<', '[')) or f'{typ}.{method}' in functions:
        return None
    if method == 'ref':
        return 'array_handle_ref', 0
    if method == 'mut_ref':
        return 'array_handle_mut', 0
    if method == 'vequals':
        return 'array_handle_vequals', 1
    return None


def check_builtin_expression_arity(expr, fail):
    _, receiver, method, _ = expr
    if receiver[0] != 'name':
        return
    if method in ARRAY_METHOD_ARITY:
        fail(f'{method} exige {ARRAY_METHOD_ARITY[method]} argument(s)')
    if method == 'new':
        fail('pool<Int>.new attend zéro ou un argument Int')
    if method == 'copy':
        fail('pool.copy exige un argument nommé')
    if method == 'split_at_mut':
        fail('split_at_mut exige un indice')


def method_arguments(receiver, mode, existing_mode, arguments, fail):
    explicit = receiver[0] == 'down'
    if (mode == 'owned') != explicit:
        fail('un receveur consommé exige (-> valeur)' if mode == 'owned'
             else '-> interdit pour une méthode qui emprunte son receveur')
    if explicit or existing_mode in ('ref', 'mut'):
        argument = receiver
    else:
        argument = (mode, receiver[1])
    return [argument, *arguments]


def builtin_method_statement(expr, structure, fail):
    if expr[0] != 'method_call' or structure:
        return None
    receiver, method, args = expr[1:]
    if receiver[0] != 'name' or method not in ('set', 'drop', 'reset'):
        return None
    name = receiver[1]
    if method == 'set':
        if len(args) != 1:
            fail('set exige une expression Int32')
        return (method, (name, args[0][1])) if args[0][0] == 'int' else ('set_expr', (name, args[0]))
    if method == 'drop':
        if len(args) != 1 or args[0][0] != 'down':
            fail('drop exige un transfert -> explicite')
        return method, (name, args[0][1])
    if args:
        fail('reset ne prend aucun argument')
    return method, (name,)


@dataclass(frozen=True)
class FunctionEffects:
    # Parameter indices, not concrete source identities or call-site objects.
    resets: frozenset[int]
    allocations: frozenset[tuple[int, str]]
    may_return: bool
    pool_requirements: frozenset[tuple[int, str]] = frozenset()
    blocking_join: bool = False
    launches_task: bool = False

    def describe(self, params):
        return {
            'resets': [params[i][0] for i in sorted(self.resets)],
            'allocations': [{'source': params[i][0], 'type': typ}
                            for i, typ in sorted(self.allocations)],
            'may_return': self.may_return,
            'pool_requirements': [{'source': params[i][0], 'type': typ}
                                  for i, typ in sorted(self.pool_requirements)],
        }


@dataclass(frozen=True)
class SymbolicSource:
    parameter: int | None
    writable: bool
    element: str | None = None
    kind: str | None = None
    borrowed: bool = False


def result_type_name(mode, typ):
    if mode in EXCHANGE_JOIN_TYPES:
        return EXCHANGE_JOIN_TYPES[mode]
    if mode in ('task', 'execution'):
        return f'{mode.capitalize()}<{typ}>'
    if mode in OPTION_JOIN_TYPES:
        return OPTION_JOIN_TYPES[mode]
    if mode in OWNED_JOIN_TYPES:
        return owned_result_type(mode, typ)
    return typ


class EffectAnalyzer:
    """A source-effect pass, not a replacement for the full memory verifier."""
    def __init__(self, functions, enums, error, async_functions=None):
        from handle_types import HandleDefinitions
        self.async_functions = HandleDefinitions(async_functions or {}, structures=enums or {})
        self.functions = functions
        self.enums = enums
        self.error = error
        self.summaries = {}
        self.visiting = set()
        self.blocking_join_frames = []
        self.task_launch_frames = []

    def fail(self, line, message):
        raise self.error(f'ligne {line}: {message}')

    def infer_all(self):
        for name in self.functions:
            self.infer(name)
        return self.summaries

    def infer(self, name):
        if name in self.summaries:
            return self.summaries[name]
        node = self.functions[name]
        if name in self.visiting:
            self.fail(node.line, 'prototype : récursion non prise en charge')
        self.visiting.add(name)
        self.blocking_join_frames.append(False)
        self.task_launch_frames.append(False)
        try:
            _, params, _, body = node.args
            environment = {}
            for index, (pname, mode, typ) in enumerate(params):
                source = None
                if typ == 'Allocator' or typ.startswith('Pool<'):
                    source = SymbolicSource(index, mode == 'mut',
                                            typ[5:-1] if typ.startswith('Pool<') else None,
                                            'pool' if typ.startswith('Pool<') else None)
                else:
                    source = result_type_name(mode, typ)
                environment[pname] = source
            resets, allocations, pools = set(), set(), set()
            for index, (_, _, typ) in enumerate(params):
                if typ.startswith('Pool<'):
                    pools.add((index, typ[5:-1]))
            outcomes = self.nodes(body, environment, resets, allocations, pools)
            result = FunctionEffects(frozenset(resets), frozenset(allocations),
                                     bool(outcomes & {'next', 'return'}), frozenset(pools),
                                     self.blocking_join_frames[-1], self.task_launch_frames[-1])
            self.summaries[name] = result
            return result
        finally:
            self.blocking_join_frames.pop()
            self.task_launch_frames.pop()
            self.visiting.remove(name)

    def source(self, name, environment, line, write=True):
        if name not in environment:
            self.fail(line, f"variable inconnue '{name}'")
        source = environment[name]
        if not isinstance(source, SymbolicSource):
            self.fail(line, f"'{name}' n'est pas une source de stockage")
        if write and not source.writable:
            self.fail(line, f"'{name}' exige un emprunt mutable de l'allocateur")
        return source

    def require_pool(self, source, typ, allocations, pools, line):
        if source.kind is not None and (source.kind != 'pool' or source.element != typ):
            self.fail(line, f'source incompatible : attend une source Pool<{typ}>')
        if source.parameter is not None:
            index = source.parameter
            if any(i == index and other != typ for i, other in pools):
                self.fail(line, 'exigences de types de pools incompatibles pour la même source')
            if any(i == index and other != typ for i, other in allocations):
                self.fail(line, f'pool<{typ}> incompatible avec les allocations de cette source')
            pools.add((index, typ))

    def allocation(self, source, typ, allocations, pools, line):
        if source.element is not None and source.element != typ:
            self.fail(line, f'pool<{source.element}> incompatible avec une allocation {typ}')
        if typ != 'Int' and source.kind in ('allocator', 'stack'):
            self.fail(line, f'construction de {typ} : pool<{typ}> requis')
        if source.parameter is not None:
            if any(i == source.parameter and other != typ for i, other in pools):
                self.fail(line, f'allocation {typ} incompatible avec le type de pool exigé')
            allocations.add((source.parameter, typ))
        if typ in self.enums:
            self.require_pool(source, typ, allocations, pools, line)

    def condition(self, condition, environment, resets, allocations, pools, line, break_types=None):
        flow = {'next'}
        if condition[0] == 'compare':
            for expr in condition[2:]:
                if 'next' not in flow:
                    break
                flow = (flow - {'next'}) | self.expression(expr, environment, resets, allocations, pools, line, break_types=break_types)
        return flow

    def receiver_type(self, expr, environment):
        if expr[0] == 'array_hashmap_new':
            return expr[1]
        if expr[0] == 'array_drop_result':
            inner = expr[1]
            return self.receiver_type(consumed_result_expression(inner, self.receiver_type(inner[1], environment)), environment)
        if expr[0] == 'array_integer_try_from':
            return 'Result<u8,IntegerConversionError>'
        if expr[0] == 'array_byte_literal':
            return 'u8'
        if expr[0] == 'array_integer_cast':
            return expr[2]
        op = expr[0]
        if op == 'bool':
            return 'bool'
        if op in ('int', 'deref', 'field_deref', 'arithmetic'):
            return 'Int'
        if op == 'field':
            carrier = environment.get(expr[1])
            declared = dict(self.enums.get(carrier, {}).get('', ())).get(expr[2])
            capability = reference_type(declared) if declared is not None else None
            return capability[1] if capability else declared
        if op == 'utf8_try_slice':
            return UTF8_SLICE_RESULT
        if op == 'utf8_validate':
            return UTF8_TEXT_RESULT
        if op == 'array_split_half':
            typ = self.receiver_type(expr[1], environment)
            return VECTOR_SPLIT_TYPES.get(typ, typ)
        if op in ('utf8_slice', 'array_split'):
            typ = self.receiver_type(expr[1], environment)
            mode = VECTOR_SLICE_MODES.get(typ)
            if mode is not None:
                return VALUE_MODES[mode]
            if op == 'array_split' and typ in ('[Int]', '[u8]'):
                return typ
        if op == 'call' and expr[1] in self.async_functions:
            return f'Task<{expr[1]}>'
        if op == 'task_spawn':
            task = self.receiver_type(expr[1], environment)
            return task.replace('Task<', 'Execution<', 1) if task and task.startswith('Task<') else None
        if op in ('task_join', 'task_join_value'):
            execution = (environment.get(expr[1]) if op == 'task_join'
                         else self.receiver_type(expr[1], environment))
            if execution and execution.startswith('Execution<'):
                mode, typ = self.async_functions[execution[len('Execution<'):-1]].args[2]
                if mode in ASYNC_CAPTURE_VIEW_MODES:
                    from async_lowering import SCALAR_RESULTS
                    return f'Result<{SCALAR_RESULTS[mode, typ]},runtime::Error>'
                if mode == 'owned':
                    return f'Result<A<{typ}>,runtime::Error>'
                if mode == 'join_owned':
                    return f'Result<{result_type_name(mode, typ)},runtime::Error>'
                if (plain := PLAIN_RETURN_JOINS.get((mode, typ))) is not None:
                    return PLAIN_JOIN_TYPES[plain]
        if op == 'builtin_error':
            return ERROR_VALUE_TYPES[expr[1]]
        if op in ('utf8_value', 'utf8_error'):
            from handle_exchange_types import exchange_element
            subject = self.receiver_type(expr[1], environment)
            if (element := exchange_element(subject)) is not None:
                return element
            if subject in ('Result<&mut Int,&mut Int>', 'Result<(),&mut Int>'):
                return 'Int'
        if op == 'utf8_error':
            subject = self.receiver_type(expr[1], environment)
            if subject and subject.endswith(',runtime::Error>'):
                return 'runtime::Error'
            error = next((ERROR_VALUE_TYPES[mode] for kind, mode in RESULT_ERROR_MODES.items()
                          if VALUE_MODES.get(kind) == subject), None)
            if error is not None:
                return error
            op = 'utf8_value'
        if op == 'utf8_value':
            subject = self.receiver_type(expr[1], environment)
            if subject and subject.startswith('Result<') and subject.endswith(',runtime::Error>'):
                from handle_types import public_signature
                inner = subject[len('Result<'):-len(',runtime::Error>')]
                signature = public_signature(f'runtime::Handle<{inner}>')
                if signature is not None and signature[0] in ASYNC_CAPTURE_VIEW_MODES:
                    return signature[1]
            for mode, typ in PLAIN_JOIN_TYPES.items():
                if subject == typ:
                    return PLAIN_JOIN_PAYLOADS[mode]
            if subject and subject.startswith('Result<Result<A<') and subject.endswith('>,runtime::Error>,runtime::Error>'):
                return subject[len('Result<'):-len(',runtime::Error>')]
            if subject and subject.startswith('Result<A<') and subject.endswith('>,runtime::Error>'):
                return subject[len('Result<A<'):-len('>,runtime::Error>')]
            payload = {UTF8_TEXT_RESULT: 'str', UTF8_SLICE_RESULT: 'str', 'Option<&Int>': 'Int', 'Result<&Int,&Int>': 'Int', 'Result<(),&Int>': 'Int', **VECTOR_PAYLOAD_TYPES}.get(subject)
            if payload is not None:
                return payload
        if op in UTF8_EXPRESSION_MODES:
            mode = UTF8_EXPRESSION_MODES[op]
            return VALUE_MODES.get(mode, 'Void' if mode == 'void' else 'Int')
        if op == 'text':
            return 'str'
        if op in ('array_vector_len', 'array_vector_push'):
            return 'Int' if op == 'array_vector_len' else 'Void'
        if op == 'method_call':
            typ = self.receiver_type(expr[1], environment)
            if allocation_handle_method(typ, expr[2], self.functions) is not None:
                return 'bool' if expr[2] == 'vequals' else f'A<{typ}>'
            if allocation_value_borrow(typ, expr[2], self.functions) is not None:
                return typ
            vector = vector_method(typ, expr[2])
            if vector is not None:
                if expr[2] == 'read_fd':
                    return VALUE_MODES['read_result']
                if expr[2] == 'try_extend':
                    return VALUE_MODES['capacity_result']
                if expr[2] == 'replace' and typ == SHARED_REF_VECTOR:
                    return 'Result<&Int,&Int>'
                if expr[2] == 'try_push':
                    return 'Result<(),&Int>' if typ == SHARED_REF_VECTOR else VALUE_MODES[VECTOR_TRY_PUSH_MODES[VECTOR_ELEMENTS[typ]]]
                if expr[2] == 'push_new':
                    return VECTOR_ELEMENTS[typ]
                if expr[2] == 'pop':
                    return 'Option<&Int>' if typ == SHARED_REF_VECTOR else VALUE_MODES[VECTOR_OPTION_MODES[VECTOR_ELEMENTS[typ]]]
                if expr[2] == 'remove':
                    return (handle_vector_element(typ) if is_handle_vector(typ) else 'Int' if typ in REFERENCE_VECTORS
                            else INLINE_VECTOR_ELEMENTS[typ] if typ in INLINE_VECTOR_ELEMENTS else VECTOR_ELEMENTS[typ])
                return 'Int' if expr[2] == 'len' else 'Void'
            builtin = UTF8_METHODS.get((typ, expr[2]))
            if builtin is not None:
                mode = UTF8_EXPRESSION_MODES[builtin[0]]
                return VALUE_MODES.get(mode, 'Void' if mode == 'void' else 'Int')
        if op in ('name', 'move', 'down', 'ref', 'mut'):
            value = environment.get(expr[1])
            return value if isinstance(value, str) else None
        if op == 'call' and expr[1] in self.functions:
            return result_type_name(*self.functions[expr[1]].args[2])
        method = self.resolve_method_candidate(expr, environment)
        if method is not None:
            name = self.method_name(method, environment)
            nominal = self.receiver_type(method[1], environment)
            if allocation_handle_method(nominal, method[2], self.functions) is not None:
                return 'bool' if method[2] == 'vequals' else f'A<{nominal}>'
            if method[2] == 'replace' and nominal in VECTOR_ELEMENTS:
                return VALUE_MODES[VECTOR_REPLACE_MODES[VECTOR_ELEMENTS[nominal]]]
            return self.functions[name].args[2][1] if name else None
        if op in ('new_enum', 'new', 'struct_copy'):
            source = environment.get(expr[1])
            if op == 'new_enum' and expr[2] is not None:
                return expr[2]
            if op == 'new' and expr[4:] != ('pool_default',):
                return expr[3]
            return source.element if isinstance(source, SymbolicSource) else None
        if op in ('transfer', 'new_transfer', 'array_transfer', 'array_copy', 'ref_expr', 'mut_expr'):
            return self.receiver_type(expr[1], environment)
        if op in ('array_index', 'array_replace'):
            nominal = self.receiver_type(expr[1], environment)
            shape = fixed_array_shape(nominal) if nominal else None
            if op == 'array_index' and is_handle_vector(nominal):
                return f'A<{handle_vector_element(nominal)}>'
            if op == 'array_index' and nominal in INLINE_VECTOR_ELEMENTS:
                return INLINE_VECTOR_ELEMENTS[nominal]
            if op == 'array_index' and nominal == '[Int]':
                return 'Int'
            if op == 'array_index' and nominal in VECTOR_ELEMENTS:
                return VECTOR_ELEMENTS[nominal]
            if (op == 'array_index' and nominal in ('str', 'String', '[u8]')) or (shape and shape[0] == 'u8'):
                return 'u8'
        if op in ('array_literal', 'array_repeat', 'array_index', 'array_ref', 'array_mut_ref'):
            return '[]'
        return None

    def resolve_method_candidate(self, expr, environment):
        if expr[0] == 'task_join':
            return method_candidate(expr, environment.get(expr[1]), self.functions)
        candidate = method_candidate(expr)
        if candidate is None or expr[0] == 'method_call':
            return candidate
        nominal = environment.get(candidate[1][1])
        return candidate if isinstance(nominal, str) and (
            '' in self.enums.get(nominal, {}) or vector_method(nominal, candidate[2]) or allocation_handle_method(nominal, candidate[2], self.functions)) else None

    def method_name(self, expr, environment):
        receiver, method, _ = expr[1:]
        if isinstance(environment.get(receiver[1]), SymbolicSource):
            return None
        typ = self.receiver_type(receiver, environment)
        if typ is not None:
            return f'{typ}.{method}' if f'{typ}.{method}' in self.functions else None
        matches = [name for name in self.functions if name.endswith('.' + method)]
        return matches[0] if len(matches) == 1 else None

    def expression(self, expr, environment, resets, allocations, pools, line, result_types=None, break_types=None):
        flow = self.expression_flow(expr, environment, resets, allocations, pools, line, result_types, break_types)
        if (result_types is not None and 'next' in flow
                and (expr is None or expr[0] not in ('if_expr', 'match_expr', 'value_match', 'loop_expr', 'scope'))):
            result_types.add(self.receiver_type(expr, environment) if expr is not None else None)
        return flow

    def expression_flow(self, expr, environment, resets, allocations, pools, line, result_types, break_types):
        if expr is None:
            return {'next'}
        if expr[0] == 'array_drop_result':
            inner = expr[1]
            expr = consumed_result_expression(inner, self.receiver_type(inner[1], environment))

        candidate = self.resolve_method_candidate(expr, environment)
        if candidate is None:
            builtin = method_candidate(expr)
            if (builtin is not None and environment.get(builtin[1][1]) is None
                    and any(name.endswith('.' + builtin[2]) for name in self.functions)):
                self.fail(line, f"type du receveur indéterminé pour '{builtin[2]}'")
        expr = candidate or expr
        op = expr[0]
        if op in ('task_join', 'task_join_value'):
            self.blocking_join_frames[-1] = True
        if op == 'arithmetic' or op.startswith(('array_', 'utf8_')):
            flow = {'next'}
            for operand in (expr[2:] if op == 'arithmetic' else array_operands(expr)):
                if 'next' not in flow:
                    break
                flow = (flow - {'next'}) | self.expression(operand, environment, resets, allocations, pools, line, break_types=break_types)
            return flow
        if op == 'match_expr':
            return self.match(expr[1], environment, resets, allocations, pools, result_types, break_types)
        if op == 'loop_expr':
            return self.loop(expr[1], environment, resets, allocations, pools, result_types)
        if op in ('scope', 'value_match'):
            body = expr[1] if op == 'value_match' else expr[2]
            return self.nodes(body, environment.copy(), resets, allocations, pools, result_types, break_types)
        if op == 'if_expr':
            condition, yes, no = expr[1:]
            flow = self.condition(condition, environment, resets, allocations, pools, line, break_types)
            if 'next' not in flow:
                return flow
            left = (self.expression(yes, environment.copy(), resets, allocations, pools, line, result_types, break_types)
                    if isinstance(yes, tuple) else self.nodes(yes, environment.copy(), resets, allocations, pools, result_types, break_types))
            right = (self.expression(no, environment.copy(), resets, allocations, pools, line, result_types, break_types)
                     if isinstance(no, tuple) else self.nodes(no, environment.copy(), resets, allocations, pools, result_types, break_types))
            return (flow - {'next'}) | left | right
        if op in ('transfer', 'new_transfer', 'ref_expr', 'mut_expr', 'task_spawn', 'task_join_value'):
            flow = self.expression(expr[1], environment, resets, allocations, pools, line, break_types=break_types)
            if op == 'task_spawn' and 'next' in flow:
                self.task_launch_frames[-1] = True
            return flow
        if op == 'struct_copy':
            source = self.source(expr[1], environment, line)
            if '' not in self.enums.get(source.element, {}):
                self.fail(line, 'pool.copy exige un pool de structures')
            self.allocation(source, source.element, allocations, pools, line)
            return {'next'}
        if op in ('new', 'new_enum'):
            values = [expr[2]] if op == 'new' else [v for _, v in expr[4]]
            flow = {'next'}
            for value in values:
                if 'next' not in flow:
                    break
                flow = (flow - {'next'}) | self.expression(value, environment, resets, allocations, pools, line, break_types=break_types)
            if op == 'new_enum' and expr[1] is None:
                return flow
            if 'next' in flow:
                source = self.source(expr[1], environment, line)
                typ = expr[3] if op == 'new' else expr[2] or source.element
                if op == 'new_enum' and expr[2] is None and '' not in self.enums.get(typ, {}):
                    self.fail(line, 'new avec champs nommés exige un pool de structures')
                if op == 'new' and expr[4:] == ('pool_default',) and ('' in self.enums.get(source.element, {}) or source.element in ('String', *VECTOR_TYPES)):
                    typ = source.element
                self.allocation(source, typ, allocations, pools, line)
            return flow
        if op == 'method_call':
            receiver, method, arguments = expr[1:]
            typ = self.receiver_type(receiver, environment)
            borrow = allocation_value_borrow(typ, method, self.functions)
            if borrow is not None:
                if receiver[0] != 'name' or arguments:
                    self.fail(line, f'{method} exige un receveur nommé et aucun argument')
                return {'next'}
            builtin = allocation_handle_method(typ, method, self.functions) or vector_method(typ, method) or UTF8_METHODS.get((typ, method))
            if builtin is not None:
                operation, arity = builtin
                if receiver[0] != 'name' or len(arguments) != arity:
                    self.fail(line, f'{method} exige un &str et aucun argument' if method == 'byte_len' else f'{method} exige un receveur et {arity} argument(s)')
                return self.expression((operation, receiver, *arguments), environment, resets, allocations, pools, line,
                                       break_types=break_types)
            name = self.method_name(expr, environment)
            if name is None:
                nominal = environment.get(expr[1][1])
                if not isinstance(nominal, str) or '' not in self.enums.get(nominal, {}):
                    check_builtin_expression_arity(expr, lambda message: self.fail(line, message))
                self.fail(line, f"méthode inconnue ou receveur indéterminé '{expr[2]}'")
            receiver, _, arguments = expr[1:]
            mode = self.functions[name].args[1][0][1]
            args = method_arguments(receiver, mode, None, arguments, lambda message: self.fail(line, message))
            expr = ('call', name, args)
        elif op != 'call':
            return {'next'}
        name, args = expr[1:]
        # Infer argument effects before the invoked body's effects, matching
        # evaluation order and abrupt returns/breaks during argument creation.
        flow = {'next'}
        for arg in args:
            if 'next' not in flow:
                break
            flow = (flow - {'next'}) | self.expression(arg, environment, resets, allocations, pools, line, break_types=break_types)
        if 'next' not in flow:
            return flow
        if name in self.async_functions:
            return flow
        if name not in self.functions:
            self.fail(line, f"fonction inconnue '{name}'")
        params = self.functions[name].args[1]
        if len(args) != len(params):
            self.fail(line, f"'{name}' attend {len(params)} argument(s), reçu {len(args)}")
        actual_sources = {}
        for index, ((pname, mode, typ), arg) in enumerate(zip(params, args)):
            if typ != 'Allocator' and not typ.startswith('Pool<'):
                continue
            expected = 'mut' if mode == 'mut' else 'ref'
            if arg[0] not in (expected, 'name'):
                self.fail(line, f"argument '{pname}' : mode attendu {mode} ({typ})")
            source = self.source(arg[1], environment, line, write=mode == 'mut')
            if arg[0] == 'name' and source.parameter is None and not source.borrowed:
                self.fail(line, f"argument '{pname}' : mode attendu {mode} ; emprunt explicite requis")
            if arg[0] != 'name' and (source.parameter is not None or source.borrowed):
                self.fail(line, 'emprunt imbriqué non pris en charge : & sur un emprunt ajoute un niveau ; utiliser son nom')
            if typ.startswith('Pool<') and source.kind is not None and (
                    source.kind != 'pool' or source.element != typ[5:-1]):
                self.fail(line, f"'{pname}' attend une source {typ}")
            actual_sources[index] = source
        summary = self.infer(name)
        self.blocking_join_frames[-1] |= summary.blocking_join
        self.task_launch_frames[-1] |= summary.launches_task
        for index, typ in summary.pool_requirements:
            self.require_pool(actual_sources[index], typ, allocations, pools, line)
        for index in summary.resets:
            source = actual_sources[index]
            if source.parameter is not None:
                resets.add(source.parameter)
        for index, typ in summary.allocations:
            self.allocation(actual_sources[index], typ, allocations, pools, line)
        return flow if summary.may_return else flow - {'next'}

    def loop(self, node, environment, resets, allocations, pools, break_types=None):
        outcomes = self.nodes(node.args[0], environment.copy(), resets, allocations, pools, break_types=break_types)
        return (outcomes & {'return'}) | ({'next'} if 'break' in outcomes else set())

    def match(self, node, environment, resets, allocations, pools, result_types=None, break_types=None):
        flow = set()
        for arm_type, arm, fields, body in node.args[1]:
            branch = environment.copy()
            declared = dict(self.enums.get(arm_type, {}).get(arm, ()))
            for field, name in fields:
                if name == '_':
                    continue
                field_type = declared.get(field)
                capability = reference_type(field_type) if field_type is not None else None
                if field_type and field_type.startswith('A<'):
                    branch[name] = field_type[2:-1]
                else:
                    branch[name] = capability[1] if capability else field_type
            flow |= self.nodes(body, branch, resets, allocations, pools, result_types, break_types)
        return flow

    def nodes(self, nodes, environment, resets, allocations, pools, result_types=None, break_types=None):
        flow = {'next'}
        for node in nodes:
            if 'next' not in flow:
                break
            op, args, line = node.op, node.args, node.line
            if op == 'call' and args[0][0] == 'method_call':
                expr = args[0]
                nominal = environment.get(expr[1][1])
                structure = isinstance(nominal, str) and '' in self.enums.get(nominal, {})
                if (nominal is None and expr[2] in ('set', 'drop', 'reset')
                        and any(name.endswith('.' + expr[2]) for name in self.functions)):
                    self.fail(line, f"type du receveur indéterminé pour '{expr[2]}'")
                builtin = builtin_method_statement(expr, structure, lambda message: self.fail(line, message))
                if builtin is not None:
                    op, args = builtin
            part = {'next'}
            if op == 'set_expr':
                part = self.expression(args[1], environment, resets, allocations, pools, line,
                                       break_types=break_types)
            elif op in ('var', 'assign'):
                name, expr = args
                if expr[0] == 'source':
                    if op == 'assign':
                        self.fail(line, 'prototype : une source de stockage ne peut pas être réaffectée')
                    environment[name] = SymbolicSource(None, node.mutable,
                        expr[3] if expr[1] == 'pool' else None, expr[1])
                elif expr[0] in ('ref', 'mut') and isinstance(environment.get(expr[1]), SymbolicSource):
                    if op != 'var':
                        self.fail(line, 'un emprunt de pool exige une nouvelle liaison')
                    source = self.source(expr[1], environment, line, write=expr[0] == 'mut')
                    environment[name] = SymbolicSource(source.parameter, expr[0] == 'mut',
                                                       source.element, source.kind, True)
                else:
                    types = set()
                    part = self.expression(expr, environment, resets, allocations, pools, line, types, break_types)
                    if 'next' in part and (op == 'var' or any(typ is not None for typ in types)):
                        annotation = fixed_array_shape(node.annotation) if node.annotation else None
                        environment[name] = (node.annotation if annotation and annotation[0] == 'u8'
                                             else next(iter(types)) if len(types) == 1 else None)
            elif op == 'reset':
                source = self.source(args[0], environment, line)
                if source.parameter is not None:
                    resets.add(source.parameter)
            elif op == 'drop':
                self.source(args[0], environment, line)
            elif op == 'scope':
                part = self.nodes(args[1], environment.copy(), resets, allocations, pools, break_types=break_types)
            elif op == 'if':
                condition, yes, no = args
                part = self.condition(condition, environment, resets, allocations, pools, line, break_types)
                if 'next' in part:
                    part = ((part - {'next'}) |
                            self.nodes(yes, environment.copy(), resets, allocations, pools, break_types=break_types) |
                            self.nodes(no, environment.copy(), resets, allocations, pools, break_types=break_types))
            elif op == 'while_check':
                part = self.condition(args[0], environment, resets, allocations, pools, line, break_types)
                if 'next' in part:
                    part |= {'break'}
            elif op in ('loop', 'while'):
                part = self.loop(node, environment, resets, allocations, pools)
            elif op == 'break':
                part = self.expression(args[0], environment, resets, allocations, pools, line, break_types, break_types)
                if 'next' in part:
                    part = (part - {'next'}) | {'break'}
            elif op == 'continue':
                part = {'continue'}
            elif op == 'return':
                part = self.expression(args[0], environment, resets, allocations, pools, line, break_types=break_types)
                if 'next' in part:
                    part = (part - {'next'}) | {'return'}
            elif op in ('call', 'if_yield'):
                part = self.expression(args[0], environment, resets, allocations, pools, line,
                                       result_types if op == 'if_yield' else None, break_types)
            elif result_types is not None and (op == 'match_yield' or op == '<-' and not node.terminated):
                result_types.add(self.receiver_type(('name', args[0]), environment))
            elif op in ARRAY_STATEMENTS or op in ('field_store', 'print_expr'):
                for expr in args:
                    if 'next' not in part:
                        break
                    part = (part - {'next'}) | self.expression(expr, environment, resets, allocations, pools, line, break_types=break_types)
            elif op == 'match':
                part = self.match(node, environment, resets, allocations, pools, break_types=break_types)
            flow = (flow - {'next'}) | part
        return flow
