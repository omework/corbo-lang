"""Resolve numeric contexts before ownership contracts and C lowering."""

from dataclasses import replace
import re

from effects import allocation_value_borrow
from numeric_core import FORMATS, NumericError, conversion_type, evaluate, exact_cast, literal_value, numeric_type
from mutex_syntax import GUARD_TYPES, payload_type as mutex_payload
from hashmap_syntax import METHODS as MAP_METHODS, map_types, method_result as map_method_result


RAW = {'numeric_integer', 'numeric_decimal'}
def element_type(typ):
    match = re.fullmatch(r'\[(.*);[0-9]+\]', typ or '')
    return match[1] if match else None


def pointee(typ):
    if typ and typ.startswith('A<'):
        return typ[2:-1]
    if typ and typ.startswith('&'):
        return typ[1:].removeprefix('mut ')
    return mutex_payload(typ, GUARD_TYPES)


def allocation_borrow_type(carrier, method):
    if carrier and carrier.startswith('A<'):
        content = pointee(carrier)
        mode = allocation_value_borrow(content, method)
        if mode is not None:
            return ('&mut ' if mode == 'mut' else '&') + content
    return None


class Elaborator:
    def __init__(self, nodes, error):
        self.error = error
        self.current_function = None
        self.functions = {node.args[0]: node for node in nodes if node.op in ('fn', 'async_fn')}
        self.structures = {node.args[0]: dict(node.args[1][0][1])
                           for node in nodes if node.op == 'struct'}
        self.enums = {node.args[0]: {arm: dict(fields) for arm, fields in node.args[1]}
                      for node in nodes if node.op == 'enum'}
        self.methods = {(node.args[0], method.args[0]): method
                        for node in nodes if node.op == 'impl' for method in node.args[1]}
        self.methods.update({tuple(name.rsplit('.', 1)): function
                             for name, function in self.functions.items() if '.' in name})

    def fail(self, line, message):
        raise self.error(f'ligne {line}: {message}')

    @staticmethod
    def result_type(function):
        if function.op == 'async_fn':
            return f'Task<{function.args[0]}>'
        return Elaborator.declared_result_type(function)

    @staticmethod
    def declared_result_type(function):
        mode, typ = function.args[2]
        if function.handle_result:
            return f'A<{typ}>'
        if mode in ('ref', 'mut', 'array_ref', 'array_mut'):
            return ('&mut ' if mode in ('mut', 'array_mut') else '&') + typ
        return typ

    @staticmethod
    def parameter_type(function, parameter):
        name, mode, typ = parameter
        if name in function.handle_parameters:
            return f'A<{typ}>'
        if mode in ('ref', 'mut', 'array_ref', 'array_mut'):
            return ('&mut ' if mode in ('mut', 'array_mut') else '&') + typ
        return typ

    def field_type(self, typ, field):
        for name in field.split('.'):
            typ = self.structures.get(pointee(typ) or typ, {}).get(name)
        return typ

    def anchor(self, expr, env):
        """A literal has no fixed type before its context is known."""
        op = expr[0]
        if op == 'array_hashmap_new':
            return expr[1]
        if op == 'array_hashmap_target':
            first = pointee(self.anchor(expr[1], env))
            return pointee(first)
        if op in ('utf8_value', 'utf8_error'):
            subject_type = self.anchor(expr[1], env) or ''
            if subject_type.startswith('Result<Option<') and subject_type.endswith('>'):
                option, separator, failure = subject_type[7:-1].rpartition('>,')
                if separator:
                    return option[7:] if op == 'utf8_value' else failure
            if op == 'utf8_value' and subject_type.startswith('Option<'):
                return subject_type[7:-1]
        if op in RAW:
            return None
        if op in ('array_numeric_literal', 'array_numeric_operation'):
            return expr[1]
        if op in ('array_mutex_new', 'array_mutex_lock', 'array_mutex_acquire'):
            return expr[1] if '<' in expr[1] else None
        if op == 'array_byte_literal':
            return 'u8'
        if op in ('name', 'move', 'down'):
            return env.get(expr[1])
        if op in ('ref', 'mut', 'reborrow'):
            target = env.get(expr[1])
            if target is None:
                return None
            return ('&mut ' if op == 'mut' or op == 'reborrow' and expr[2] == 'mut' else '&') + (pointee(target) or target)
        if op == 'field':
            return self.field_type(env.get(expr[1]), expr[2])
        if op == 'deref':
            return pointee(env.get(expr[1]))
        if op in ('ref_expr', 'mut_expr'):
            target = self.anchor(expr[1], env)
            return ('&mut ' if op == 'mut_expr' else '&') + target if target else None
        if op == 'field_deref':
            return pointee(self.anchor(expr[1], env))
        if op in ('array_integer_cast', 'numeric_cast'):
            return expr[2]
        if op == 'numeric_try_from':
            return conversion_type(expr[1])
        if op == 'utf8_value':
            subject = self.anchor(expr[1], env)
            if subject and subject.startswith('Result<'):
                return subject[7:].split(',', 1)[0]
        if op == 'utf8_tag':
            return 'Int'
        if op in ('array_index', 'array_replace'):
            receiver = self.anchor(expr[1], env)
            return element_type(pointee(receiver) or receiver)
        if op == 'array_deref_slot':
            return pointee(self.anchor(expr[1], env))
        if op == 'source' and expr[1] == 'pool':
            return f'Pool<{expr[3]}>'
        if op in ('new', 'new_enum', 'struct_copy'):
            source = env.get(expr[1], '')
            if source.startswith('&mut Pool<'):
                source = source[5:]
            if source.startswith('Pool<'):
                return f'A<{source[5:-1]}>'
            if op == 'new_enum':
                return expr[2]
            if op == 'new':
                return f'A<{expr[3]}>'
        if op == 'bool':
            return 'bool'
        if op == 'numeric_not':
            return 'bool'
        if op == 'numeric_binary':
            return self.anchor(expr[2], env) or (self.anchor(expr[3], env) if expr[1] not in ('<<', '>>') else None)
        if op == 'numeric_unary':
            return self.anchor(expr[2], env)
        if op in ('transfer', 'new_transfer', 'array_transfer', 'array_copy'):
            return self.anchor(expr[1], env)
        if op == 'scope':
            return self.tail_anchor(expr[2], env)
        if op == 'if_expr':
            return next((hint for branch in expr[2:] if (hint := self.branch_anchor(branch, env))), None)
        if op == 'loop_expr':
            return self.loop_anchor(expr[1].args[0], env)
        if op == 'match_expr':
            node = expr[1]
            return next((hint for typ, arm, fields, body in node.args[1]
                         if (hint := self.tail_anchor(body, self.arm_env(typ, arm, fields, env)))), None)
        if op == 'value_match':
            return self.tail_anchor(expr[1], env)
        if op == 'call' and expr[1] in self.functions:
            return self.result_type(self.functions[expr[1]])
        if op == 'method_call':
            carrier = self.anchor(expr[1], env)
            method = self.methods.get((pointee(carrier) or carrier, expr[2]))
            if (mapping := map_types(pointee(carrier) or carrier)) and expr[2] in MAP_METHODS:
                return map_method_result(expr[2], mapping[1])
            return self.result_type(method) if method else allocation_borrow_type(carrier, expr[2])
        if op == 'array_len':
            receiver = self.anchor(expr[1], env)
            contents = pointee(receiver) or receiver
            return 'u64' if element_type(contents) or contents in ('[u8]', '[Int]') else 'Int'
        if op == 'array_numeric_len':
            return 'u64'
        if op == 'await':
            if expr[1][0] == 'array_mutex_lock':
                return expr[1][1]
            task = self.anchor(expr[1], env)
            if task and task.startswith('Task<') and task[5:-1] in self.functions:
                return self.declared_result_type(self.functions[task[5:-1]])
            return self.join_type(task)
        if op == 'task_spawn':
            task = self.anchor(expr[1], env)
            if task and task.startswith('Task<'):
                return 'Execution' + task[4:]
        if op in ('task_join', 'task_join_value'):
            task = env.get(expr[1]) if op == 'task_join' else self.anchor(expr[1], env)
            return self.join_type(task)
        return None

    def join_type(self, task):
        if task and task.startswith('Execution<'):
            function = self.functions.get(task[10:-1])
            if function:
                return f'Result<{self.declared_result_type(function)},runtime::Error>'
        for prefix in ('runtime::Handle<', 'runtime::AsyncHandle<'):
            if task and task.startswith(prefix):
                return f'Result<{task[len(prefix):-1]},runtime::Error>'
        return None

    def family(self, expr):
        if expr[0] == 'numeric_decimal':
            return 'f64'
        if expr[0] == 'numeric_integer':
            return 'i64'
        if expr[0] in ('numeric_binary', 'numeric_unary'):
            return self.family(expr[2]) or (self.family(expr[3]) if expr[0] == 'numeric_binary' else None)
        return None

    def binding_hint(self, node, env):
        return node.annotation or self.anchor(node.args[1], env) or self.family(node.args[1])

    def tail_anchor(self, body, outer):
        env = outer.copy()
        for node in body:
            if node.op == 'var':
                env[node.args[0]] = self.binding_hint(node, env)
            elif node.op == 'if_yield':
                return self.anchor(node.args[0], env)
            elif node.op in ('<-', 'match_yield'):
                return env.get(node.args[0])
        return None

    def loop_anchor(self, body, outer):
        env = outer.copy()
        for node in body:
            if node.op == 'var':
                env[node.args[0]] = self.binding_hint(node, env)
            elif node.op == 'break' and node.args[0] is not None:
                if typ := self.anchor(node.args[0], env):
                    return typ
            elif node.op == 'scope':
                if typ := self.loop_anchor(node.args[1], env):
                    return typ
            elif node.op == 'if':
                for branch in node.args[1:]:
                    if typ := self.loop_anchor(branch, env):
                        return typ
            elif node.op == 'match':
                for typ, arm, fields, branch in node.args[1]:
                    if hint := self.loop_anchor(branch, self.arm_env(typ, arm, fields, env)):
                        return hint
        return None

    def arm_env(self, typ, arm, fields, env):
        declared = self.enums.get(typ, {}).get(arm, {})
        return env | {alias: declared.get(field) for field, alias in fields}

    def branch_anchor(self, branch, env):
        return self.tail_anchor(branch, env) if isinstance(branch, list) else self.anchor(branch, env)

    def same_type(self, types, line, message):
        present = {numeric_type(typ) or ('bool' if typ == 'Bool' else typ) for typ in types if typ is not None}
        if len(present) > 1:
            self.fail(line, f'{message} : {", ".join(sorted(present))}')
        return next(iter(present), None)

    def literal(self, expr, expected, line):
        typ = numeric_type(expected) or self.family(expr)
        if bool(FORMATS[typ].precision) != (expr[0] == 'numeric_decimal'):
            self.fail(line, f'littéral de famille incompatible avec {typ}')
        try:
            value = literal_value(expr[1], typ)
        except NumericError as error:
            self.fail(line, error)
        return ('array_numeric_literal', typ, value), typ

    def operation(self, expr, env, expected, line):
        _, operator, *operands = expr
        shift = operator in ('<<', '>>')
        left_anchors = [self.anchor(operand, env) for operand in (operands[:1] if shift else operands)]
        typ = self.same_type(left_anchors, line, 'opérandes de types différents')
        typ = numeric_type(typ) or (numeric_type(expected) if typ is None else None)
        if typ is None:
            typ = next((family for operand in operands if (family := self.family(operand))), None)
        if typ is None:
            self.fail(line, 'opération numérique exige des opérandes numériques typés')
        compiled = [self.expr(operand, env, line, None if shift and i else typ)
                    for i, operand in enumerate(operands)]
        for i, (_, actual) in enumerate(compiled):
            if shift and i:
                if numeric_type(actual) is None or FORMATS[numeric_type(actual)].precision:
                    self.fail(line, 'un nombre de positions doit être entier')
            elif actual is not None and numeric_type(actual) != typ:
                self.fail(line, f'opérandes de types différents : attendu {typ}, reçu {actual}')
        spec = FORMATS[typ]
        if operator == 'neg' and not spec.signed:
            self.fail(line, 'la négation exige un type signé ou flottant')
        if spec.precision and operator not in ('+', '-', '*', '/', 'neg'):
            self.fail(line, f'{operator} exige un type entier')
        lowered = [operand for operand, _ in compiled]
        if len(lowered) == 2 and lowered[1][0] == 'array_numeric_literal':
            right = lowered[1][2]
            if operator in ('/', '%') and right == 0:
                self.fail(line, 'division par zéro')
            if shift and not 0 <= right < spec.bits:
                self.fail(line, 'nombre de positions hors limites')
        if all(operand[0] == 'array_numeric_literal' for operand in lowered):
            try:
                value = evaluate(operator, typ, *(operand[2] for operand in lowered))
            except NumericError as error:
                self.fail(line, error)
            return ('array_numeric_literal', typ, value), typ
        return ('array_numeric_operation', typ, operator, *lowered), typ

    def condition(self, condition, env, line):
        if condition[0] == 'truth':
            return condition
        _, operator, left, right = condition
        expected = self.same_type((self.anchor(left, env), self.anchor(right, env)),
                                  line, 'comparaison entre types différents')
        if expected is None:
            expected = self.family(left) or self.family(right)
        lhs, left_type = self.expr(left, env, line, expected)
        rhs, right_type = self.expr(right, env, line, expected)
        self.same_type((left_type, right_type), line, 'comparaison entre types différents')
        return 'compare', operator, lhs, rhs

    def branches(self, branches, env, line, expected):
        typ = expected or self.same_type(
            (self.branch_anchor(branch, env) for branch in branches), line, 'résultats de types différents')
        lowered = []
        actual = []
        for branch in branches:
            if isinstance(branch, list):
                actual.append(self.block(branch, env, tail_type=typ))
                lowered.append(branch)
            else:
                value, result = self.expr(branch, env, line, typ)
                lowered.append(value)
                actual.append(result)
        return lowered, self.same_type(actual, line, 'résultats de types différents') or typ

    def call(self, expr, env, line):
        if expr[0] == 'call':
            op, name, arguments = expr
            head = (op, name)
            function = self.functions.get(name)
            offset = 0
        else:
            receiver, typ = self.expr(expr[1], env, line)
            name, arguments = expr[2:]
            head = (expr[0], receiver, name)
            function = self.methods.get((pointee(typ) or typ, name))
            nominal = pointee(typ) or typ
            if (mapping := map_types(nominal)) and name in MAP_METHODS:
                key, value = mapping
                insertion = name in ('insert', 'try_insert')
                expected = (key, value) if insertion else ('&' + key,)
                if len(arguments) != len(expected):
                    self.fail(line, f'HashMap.{name} exige {len(expected)} argument(s)')
                lowered = [self.expr(arg, env, line, want)[0] for arg, want in zip(arguments, expected)]
                return ('array_hashmap_method', name, receiver, *lowered), map_method_result(name, value)
            if typ == 'runtime::Future' and name in ('enqueue', 'launch_failed'):
                if arguments or receiver[0] != 'name':
                    self.fail(line, f'{name} exige une Future nommée et aucun argument')
                return ('array_scheduler_resolve', name, receiver), 'Void'
            if name == 'lock' and mutex_payload(nominal):
                if arguments:
                    self.fail(line, 'lock ne prend aucun argument')
                guard = nominal.replace('Mutex<', 'MutexGuard<', 1)
                return ('array_mutex_lock', guard, receiver), guard
            if function is None and name == 'set' and len(arguments) == 1 and numeric_type(pointee(typ) or typ):
                return (*head, [self.expr(arguments[0], env, line, pointee(typ) or typ)[0]]), None
            if function is None and not arguments and (borrowed := allocation_borrow_type(typ, name)):
                return (*head, arguments), borrowed
            offset = 1
        parameters = function.args[1][offset:] if function else ()
        lowered = [self.expr(arg, env, line, self.parameter_type(function, parameters[i])
                             if i < len(parameters) else None)[0] for i, arg in enumerate(arguments)]
        return (*head, lowered), self.result_type(function) if function else None

    def expr(self, expr, env, line, expected=None):
        op = expr[0]
        if op == 'array_start_poller':
            name = self.current_function or ''
            if '.' not in name or name.rsplit('.', 1)[-1] not in ('spawn', 'spawn_blocking', 'wake'):
                self.fail(line, 'runtime::start_poller exige un callback du scheduler')
            return expr, 'bool'
        if op == 'array_set_scheduler':
            from scheduler_syntax import check_scheduler_methods
            if self.current_function != 'main':
                self.fail(line, 'runtime::set_scheduler doit être appelé directement dans main')
            value, typ = self.expr(expr[1], env, line)
            nominal = pointee(typ) or typ
            if nominal not in self.structures or (typ and typ.startswith('&')):
                self.fail(line, 'runtime::set_scheduler exige une instance concrète par valeur')
            check_scheduler_methods(nominal, self.methods, lambda message: self.fail(line, message))
            return (op, value), 'Void'
        if op == 'array_mutex_new':
            _, family, initializer = expr
            value, typ = self.expr(initializer, env, line, mutex_payload(expected))
            if numeric_type(typ) is None and typ != 'bool' and typ not in self.structures:
                self.fail(line, 'constructeur de mutex : valeur scalaire ou structure locale requise')
            if typ == 'i32':
                typ = 'Int'
            nominal = f'{family}<{typ}>'
            return (op, nominal, value), nominal
        if op == 'array_numeric_compound':
            _, place, operator, rhs = expr
            place, typ = self.expr(place, env, line)
            typ = numeric_type(typ)
            if typ is None or operator == '%' and FORMATS[typ].precision:
                self.fail(line, 'affectation composée : emplacement numérique compatible attendu')
            rhs, actual = self.expr(rhs, env, line, typ)
            if numeric_type(actual) != typ:
                self.fail(line, f'affectation composée : valeur {typ} attendue')
            return (op, place, operator, rhs), None
        if op in RAW:
            return self.literal(expr, expected, line)
        if op in ('numeric_binary', 'numeric_unary'):
            return self.operation(expr, env, expected, line)
        if op == 'numeric_not':
            operand, typ = self.expr(expr[1], env, line, 'bool')
            if typ not in ('bool', 'Bool'):
                self.fail(line, '! exige un bool')
            return ('array_numeric_not', operand), 'bool'
        if op == 'numeric_cast':
            operand, source_type = self.expr(expr[1], env, line)
            source, target = numeric_type(source_type), numeric_type(expr[2])
            if not source or not target or not exact_cast(source, target):
                self.fail(line, f'conversion {source_type} as {expr[2]} non exacte pour le type source ; utiliser try_from')
            return ('array_numeric_cast', target, operand), target
        if op == 'numeric_try_from':
            target, operand = expr[1:]
            operand, source = self.expr(operand, env, line)
            if numeric_type(source) is None:
                self.fail(line, 'try_from exige une valeur numérique')
            return ('array_numeric_try_from', target, operand), conversion_type(target)
        if op in ('call', 'method_call'):
            return self.call(expr, env, line)
        if op == 'await':
            operand, typ = self.expr(expr[1], env, line)
            if operand[0] == 'array_mutex_lock':
                if not typ.startswith('AsyncMutexGuard<'):
                    self.fail(line, 'un Mutex synchrone s’acquiert avec lock()')
                return ('array_mutex_acquire', *operand[1:]), typ
            lowered = ('await', operand)
            return lowered, self.anchor(lowered, env)
        if op == 'array_replace':
            receiver, index, incoming = expr[1:]
            typ = self.anchor(expr, env)
            return (op, self.expr(receiver, env, line)[0], self.expr(index, env, line)[0],
                    self.expr(incoming, env, line, typ)[0]), typ
        if op == 'if_expr':
            condition = self.condition(expr[1], env, line)
            branches, typ = self.branches(expr[2:], env, line, expected)
            return (op, condition, *branches), typ
        if op == 'scope':
            typ = self.block(expr[2], env, tail_type=expected)
            return expr, typ
        if op == 'value_match':
            typ = self.block(expr[1], env, tail_type=expected)
            return expr, typ
        if op == 'match_expr':
            return expr, self.match(expr[1], env, None, None, expected)
        if op == 'loop_expr':
            typ = expected or self.loop_anchor(expr[1].args[0], env)
            results = []
            self.block(expr[1].args[0], env, break_context=(typ, results))
            return expr, self.same_type(results, line, 'résultats de boucle de types différents')
        if op in ('array_literal', 'array_repeat'):
            operands = expr[1:] if op == 'array_literal' else expr[1:2]
            typ = element_type(expected) or self.same_type(
                (self.anchor(item, env) for item in operands), line, 'éléments de types différents')
            lowered = [self.expr(item, env, line, typ) for item in operands]
            actual = self.same_type((item_type for _, item_type in lowered), line, 'éléments de types différents') or typ
            count = len(operands) if op == 'array_literal' else expr[2]
            values = tuple(item for item, _ in lowered)
            return ((op, *values) if op == 'array_literal' else (op, *values, count),
                    f'[{actual};{count}]' if actual else None)
        if op == 'new':
            typ = self.anchor(expr, env)
            element = pointee(typ)
            initializer = expr[2]
            if len(expr) == 5 and expr[4] == 'pool_default' and numeric_type(element):
                initializer = ('numeric_decimal', '0.') if FORMATS[numeric_type(element)].precision else ('numeric_integer', 0)
            operand, _ = self.expr(initializer, env, line, element)
            declared = element if len(expr) == 5 and numeric_type(element) else expr[3]
            return (*expr[:2], operand, declared, *expr[4:]), typ
        if op == 'new_enum':
            typ = self.anchor(expr, env)
            nominal = pointee(typ) or typ
            fields = self.structures.get(nominal, self.enums.get(nominal, {}).get(expr[3], {}))
            return (*expr[:4], [(name, self.expr(value, env, line, fields.get(name))[0])
                                for name, value in expr[4]]), typ
        if op in ('transfer', 'new_transfer', 'array_transfer', 'array_copy'):
            operand, typ = self.expr(expr[1], env, line, expected)
            return (op, operand), typ
        if op == 'native_thread':
            self.block(expr[2], env)
            return expr, None
        if op == 'array_len' and self.anchor(expr, env) == 'u64':
            receiver, typ = self.expr(expr[1], env, line)
            if (pointee(typ) or typ) in ('[u8]', '[Int]'):
                return ('array_numeric_slice_len', receiver), 'u64'
            return ('array_numeric_len', (op, receiver)), 'u64'
        lowered = (op, *(self.tree(item, env, line) for item in expr[1:]))
        return lowered, self.anchor(lowered, env)

    def tree(self, item, env, line):
        if isinstance(item, tuple):
            if item and isinstance(item[0], str):
                return self.expr(item, env, line)[0]
            return tuple(self.tree(value, env, line) for value in item)
        if isinstance(item, list):
            return [self.tree(value, env, line) for value in item]
        return item

    def match(self, node, env, return_type, break_context, expected=None):
        arms = [(body, self.arm_env(typ, arm, fields, env))
                for typ, arm, fields, body in node.args[1]]
        typ = expected or self.same_type((self.tail_anchor(body, branch) for body, branch in arms),
                                         node.line, 'résultats de match de types différents')
        actual = [self.block(body, branch, return_type=return_type,
                             tail_type=typ, break_context=break_context) for body, branch in arms]
        return self.same_type(actual, node.line, 'résultats de match de types différents') or typ

    def block(self, nodes, outer, *, return_type=None, tail_type=None, break_context=None):
        env = outer.copy()
        tail = None
        for i, node in enumerate(nodes):
            op, args, line = node.op, node.args, node.line
            if op in ('fn', 'async_fn', 'impl', 'struct', 'enum', 'feature'):
                continue
            if op in ('var', 'assign'):
                name, expr = args
                expected = node.annotation if op == 'var' else env.get(name)
                if op == 'assign':
                    expected = pointee(expected) if expected and expected.startswith('A<') else expected
                value, typ = self.expr(expr, env, line, expected)
                if op == 'var':
                    if numeric_type(expected) and typ and typ.startswith('A<'):
                        self.fail(line, f"annotation {expected} incompatible avec l’allocation {typ}")
                    env[name] = node.annotation or typ
                nodes[i] = replace(node, args=(name, value))
            elif op in ('return', 'if_yield', 'break') and args[0] is not None:
                expected = return_type if op == 'return' else tail_type if op == 'if_yield' else break_context[0] if break_context else None
                value, actual = self.expr(args[0], env, line, expected)
                if op == 'if_yield':
                    tail = actual
                if op == 'break' and break_context:
                    break_context[1].append(actual)
                nodes[i] = replace(node, args=(value, *args[1:]))
            elif op in ('<-', 'match_yield'):
                tail = env.get(args[0])
            elif op in ('scope', 'capture_scope'):
                self.block(args[1], env, return_type=return_type, break_context=break_context)
            elif op == 'if':
                condition, yes, no = args
                for branch in (yes, no):
                    self.block(branch, env, return_type=return_type, break_context=break_context)
                nodes[i] = replace(node, args=(self.condition(condition, env, line), yes, no))
            elif op == 'while_check':
                nodes[i] = replace(node, args=(self.condition(args[0], env, line),))
            elif op in ('loop', 'while'):
                self.block(args[0], env, return_type=return_type)
            elif op == 'match':
                self.match(node, env, return_type, break_context)
            elif op in ('array_store', 'array_deref_store'):
                place, rhs = args
                typ = self.anchor(place, env)
                if op == 'array_deref_store' and place[0] == 'name':
                    typ = pointee(typ)
                nodes[i] = replace(node, args=(self.expr(place, env, line)[0],
                                               self.expr(rhs, env, line, typ)[0]))
            elif op == 'field_store':
                place, rhs = args
                nodes[i] = replace(node, args=(place, self.expr(rhs, env, line, self.anchor(place, env))[0]))
            elif op == 'set_expr':
                name, rhs = args
                typ = env.get(name)
                nodes[i] = replace(node, args=(name, self.expr(rhs, env, line, pointee(typ) or typ)[0]))
            else:
                nodes[i] = replace(node, args=tuple(self.tree(arg, env, line) for arg in args))
        return tail

    def run(self, nodes):
        self.block(nodes, {})
        methods = ((f'{owner}.{name}', function) for (owner, name), function in self.methods.items())
        for name, function in dict((*self.functions.items(), *methods)).items():
            _, params, (_, typ), body = function.args
            self.current_function = name
            env = {param[0]: self.parameter_type(function, param) for param in params}
            self.block(body, env, return_type=f'A<{typ}>' if function.handle_result else typ)
