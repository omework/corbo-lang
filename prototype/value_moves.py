"""Lower by-value syntax to the compiler's checked transfer operations."""

from dataclasses import replace

from array_syntax import handle_vector_element, is_handle_vector
from mutex_syntax import GUARD_TYPES, payload_type as mutex_payload
from utf8_syntax import VALUE_MODES


BORROW_MODES = {'ref', 'mut', 'array_ref', 'array_mut'}
COPY_MODES = {'scalar', 'bool', 'byte', 'char', 'void', 'text', 'byte_ref',
              'runtime_error'}
NAME_OPERANDS = {'name', 'move', 'down', 'ref', 'mut', 'deref', 'reborrow',
                 'field', 'task_join'}
TRANSFER_OPS = {'move', 'down', 'transfer', 'array_transfer', 'new_transfer',
                'array_buffered_replace', 'array_buffered_try_push',
                'array_handle_option_pop'}
RESULT_OPERATIONS = {'scope', 'if_expr', 'loop_expr', 'match_expr', 'value_match'}
UNKNOWN = (None, None)


def argument_move(expr):
    if expr[0] in ('down', 'transfer'):
        return expr
    return ('down', expr[1]) if expr[0] == 'name' else ('transfer', expr)


def result_move(expr):
    op = expr[0]
    if op in TRANSFER_OPS:
        return expr
    if op == 'name':
        return 'move', expr[1]
    if op in ('new', 'new_enum', 'struct_copy'):
        return 'new_transfer', expr
    if op == 'method_call':
        receiver, method, args = expr[1:]
        if receiver[0] == 'name' and method == 'pop' and not args:
            return 'array_handle_option_pop', receiver
        if receiver[0] == 'name' and method == 'try_push' and len(args) == 1:
            return 'array_buffered_try_push', receiver, args[0]
    if op == 'array_replace' and expr[1][0] == 'name' and expr[3][0] in ('down', 'transfer'):
        return ('array_buffered_replace', *expr[1:])
    return 'array_transfer', expr


def owned(signature):
    mode, _ = signature
    return (mode is not None and mode not in COPY_MODES | BORROW_MODES | {'source'}
            and mode not in VALUE_MODES)


class ValueMoves:
    def __init__(self, nodes, node_type, *, callable_bindings=False):
        self.Node = node_type
        self.callable_bindings = callable_bindings
        self.functions = {n.args[0]: n for n in nodes if n.op in ('fn', 'async_fn')}
        self.methods = {(n.args[0], m.args[0]): m for n in nodes if n.op == 'impl'
                        for m in n.args[1]}
        self.methods.update({tuple(name.rsplit('.', 1)): function
                             for name, function in self.functions.items() if '.' in name})
        self.layouts = {n.args[0]: dict(n.args[1]) for n in nodes if n.op in ('struct', 'enum')}

    def run(self, nodes):
        self.block(nodes, {})
        functions = {id(function): function for function in (*self.functions.values(), *self.methods.values())}
        for function in functions.values():
            _, parameters, result, body = function.args
            self.block(body, {name: (mode, typ) for name, mode, typ in parameters},
                       result=result)

    @staticmethod
    def use(name, environment, captures):
        if name in environment and captures is not None:
            captures.setdefault(name, None)

    def capture(self, body, environment, line, result, enclosing):
        used = {}
        tail = self.block(body, environment, result=result, captures=used)
        explicit = {n.args[0] for n in body if n.op == '->'}
        imports = [self.Node('->', (name,), line, move_import=True)
                   for name in used if name not in explicit]
        for name in used:
            self.use(name, environment, enclosing)
        return [*imports, *body], tail

    def block(self, nodes, outer, *, result=UNKNOWN, captures=None):
        environment = outer.copy()
        hidden = set()
        uses = {} if captures is not None else None
        computed_tails = []
        tail = UNKNOWN
        for i, node in enumerate(nodes):
            op, args, line = node.op, node.args, node.line
            if op in ('fn', 'async_fn', 'impl', 'enum', 'struct', 'feature'):
                continue
            if op in ('var', 'assign'):
                name, expr = args
                if op == 'assign':
                    self.use(name, environment, uses)
                expr, signature = self.expression(expr, environment, line, uses)
                if expr[0] == 'name' and owned(signature):
                    expr = result_move(expr)
                elif op == 'assign' and owned(environment.get(name, UNKNOWN)) and owned(signature):
                    # An owned call result already arrives as a fresh receiver
                    # value. The array-transfer wrapper rejects this result.
                    if expr[0] not in RESULT_OPERATIONS | {'call', 'method_call'}:
                        expr = result_move(expr)
                nodes[i] = replace(node, args=(name, expr))
                if op == 'var':
                    environment[name] = signature
                elif name in environment and signature != UNKNOWN and not (
                        owned(environment[name]) and not owned(signature)):
                    environment[name] = signature
            elif op == 'field_store':
                place, rhs = args
                self.use(place[1], environment, uses)
                _, typ = environment.get(place[1], UNKNOWN)
                layout = dict(self.layouts.get(typ, {}).get('', ()))
                value, signature = self.expression(rhs, environment, line, uses)
                if layout.get(place[2], '').startswith('A<') and owned(signature):
                    value = result_move(value)
                nodes[i] = replace(node, args=(place, value))
            elif op in ('scope', 'capture_scope'):
                label, body = args
                if op == 'capture_scope':
                    body, _ = self.capture(body, environment, line, result, uses)
                    nodes[i] = replace(node, op='scope', args=(label, body))
                else:
                    self.block(body, environment, result=result, captures=uses)
            elif op in ('return', 'break', 'if_yield') and args[0] is not None:
                expr, tail = self.expression(args[0], environment, line, uses)
                if owned(tail) or op == 'return' and owned(result):
                    if op == 'if_yield' and expr[0] == 'name':
                        nodes[i] = replace(node, op='<-', args=(expr[1],))
                    elif op == 'if_yield' and tail[0] not in ('array', 'array_refs'):
                        name = f'\0move-result-{line}'
                        computed_tails.append((i, self.Node('var', (name, expr), line),
                                               self.Node('<-', (name,), line)))
                    else:
                        nodes[i] = replace(node, args=(result_move(expr), *args[1:]))
                else:
                    nodes[i] = replace(node, args=(expr, *args[1:]))
            elif op == 'if':
                condition, yes, no = args
                condition = self.tree(condition, environment, line, uses)
                self.block(yes, environment, result=result, captures=uses)
                self.block(no, environment, result=result, captures=uses)
                nodes[i] = replace(node, args=(condition, yes, no))
            elif op in ('loop', 'while'):
                tail = self.block(args[0], environment, result=result, captures=uses)
            elif op == 'match':
                subject, arms = args
                self.use(subject, environment, uses)
                for typ, arm, fields, body in arms:
                    layout = dict(self.layouts.get(typ, {}).get(arm, ()))
                    names = {name: ('owned', layout[field][2:-1])
                             if node.consuming and layout.get(field, '').startswith('A<')
                             else UNKNOWN for field, name in fields}
                    arm_uses = {} if uses is not None else None
                    branch = self.block(body, environment | names, result=result, captures=arm_uses)
                    if branch != UNKNOWN:
                        tail = branch
                    if arm_uses is not None:
                        for name in arm_uses:
                            if name not in names:
                                self.use(name, environment, uses)
            elif op in ('print', 'address', 'drop_value', '->', '<-', 'match_yield'):
                self.use(args[0], environment, uses)
            else:
                nodes[i] = replace(node, args=tuple(
                    self.tree(arg, environment, line, uses) for arg in args))
            if uses is not None:
                for name in uses:
                    if name in outer and name not in hidden:
                        captures.setdefault(name, None)
                uses.clear()
            if op == 'var':
                hidden.add(args[0])
        for i, binding, transfer in reversed(computed_tails):
            nodes[i:i + 1] = [binding, transfer]
        return tail

    def tree(self, value, environment, line, uses):
        if isinstance(value, tuple):
            if value and isinstance(value[0], str):
                return self.expression(value, environment, line, uses)[0]
            return tuple(self.tree(item, environment, line, uses) for item in value)
        if isinstance(value, list):
            return [self.tree(item, environment, line, uses) for item in value]
        return value

    def expression(self, expr, env, line, uses):
        if not expr:
            return expr, UNKNOWN
        op = expr[0]
        if op == 'array_hashmap_new':
            return expr, ('owned', expr[1])
        if op in NAME_OPERANDS:
            name = expr[1]
            self.use(name, env, uses)
            mode, typ = env.get(name, UNKNOWN)
            if op in ('ref', 'mut', 'reborrow'):
                if op == 'reborrow':
                    return expr, (expr[2], mutex_payload(typ, GUARD_TYPES) or typ)
                return expr, (op, typ)
            if op in ('deref', 'field'):
                return expr, UNKNOWN
            if op == 'task_join':
                function = self.functions.get(typ) if mode == 'execution' else None
                if function and function.args[2][0] == 'async_execution':
                    return expr, ('join_async_execution', function.args[2][1])
                return expr, UNKNOWN
            return expr, (mode, typ)
        if op in ('scope', 'capture_scope'):
            label, body = expr[1:3]
            if op == 'capture_scope':
                body, signature = self.capture(body, env, line, UNKNOWN, uses)
            else:
                signature = self.block(body, env, captures=uses)
            return ('scope', label, body, *expr[3:]), signature
        if op == 'if_expr':
            condition, *branches = expr[1:]
            condition = self.tree(condition, env, line, uses)
            lowered = []
            signature = UNKNOWN
            for branch in branches:
                if isinstance(branch, list):
                    value = branch
                    kind = self.block(branch, env, captures=uses)
                else:
                    value, kind = self.expression(branch, env, line, uses)
                lowered.append(value)
                if kind != UNKNOWN:
                    signature = kind
            return ('if_expr', condition, *lowered), signature
        if op in ('loop_expr', 'match_expr', 'value_match'):
            body = expr[1] if op == 'value_match' else [expr[1]]
            signature = self.block(body, env, captures=uses)
            return (op, body if op == 'value_match' else body[0]), signature
        if op in ('call', 'method_call'):
            if op == 'call' and self.callable_bindings:
                self.use(expr[1], env, uses)
            if op == 'call':
                _, name, arguments = expr
                function = self.functions.get(name)
                head = (op, name)
            else:
                receiver, (_, typ) = self.expression(expr[1], env, line, uses)
                name, arguments = expr[2:]
                if name == 'lock' and not arguments and mutex_payload(typ):
                    guard = typ.replace('Mutex<', 'MutexGuard<', 1)
                    mode = 'pending_guard' if typ.startswith('Async') else 'owned'
                    return (op, receiver, name, arguments), (mode, guard)
                if is_handle_vector(typ or '') and name == 'push' and len(arguments) == 1:
                    value, _ = self.expression(arguments[0], env, line, uses)
                    return (op, receiver, name, [argument_move(value)]), UNKNOWN
                if is_handle_vector(typ or '') and name == 'pop' and not arguments and receiver[0] == 'name':
                    return ('array_handle_option_pop', receiver), ('handle_option', handle_vector_element(typ))
                function = self.methods.get((typ, name))
                if function and function.args[1][0][1] == 'owned':
                    receiver = argument_move(receiver)
                head = (op, receiver, name)
            parameters = function.args[1][op == 'method_call':] if function else []
            arguments = [self.expression(arg, env, line, uses)[0] for arg in arguments]
            for i, (_, mode, typ) in enumerate(parameters[:len(arguments)]):
                if mode == 'array':
                    if arguments[i][0] == 'name':
                        arguments[i] = result_move(arguments[i])
                elif owned((mode, typ)):
                    arguments[i] = argument_move(arguments[i])
            signature = function.args[2] if function else UNKNOWN
            if function and function.op == 'async_fn':
                signature = 'task', name
            return (*head, arguments), signature
        if op in ('new', 'new_enum', 'struct_copy'):
            self.use(expr[1], env, uses)
            if op == 'new':
                value = self.tree(expr[2], env, line, uses)
                typ = (env.get(expr[1], UNKNOWN)[1] if expr[4:] in (
                    ('typed_pool',), ('pool_default',)) else expr[3])
                return (op, expr[1], value, *expr[3:]), ('owned', typ)
            if op == 'new_enum':
                typ = expr[2] or env.get(expr[1], UNKNOWN)[1]
                layout = dict(self.layouts.get(typ, {}).get(expr[3], ()))
                fields = []
                for name, value in expr[4]:
                    value, signature = self.expression(value, env, line, uses)
                    if layout.get(name, '').startswith('A<') and owned(signature):
                        value = result_move(value)
                    fields.append((name, value))
                return (*expr[:4], fields), ('owned', typ)
            self.use(expr[2], env, uses)
            return expr, ('owned', env.get(expr[2], UNKNOWN)[1])
        if op == 'source':
            return expr, ('source', expr[3] if len(expr) > 3 else None)
        if op == 'array_mutex_new':
            operand, (_, payload) = self.expression(expr[2], env, line, uses)
            return (op, expr[1], operand), ('owned', f'{expr[1]}<{payload}>' if payload else expr[1])
        if op == 'native_thread':
            captures = expr[1]
            inferred = {} if captures is None else None
            self.block(expr[2], env, captures=inferred)
            if inferred is not None:
                captures = tuple(inferred)
            for name in captures:
                self.use(name, env, uses)
            return (op, captures, *expr[2:]), ('execution', None)
        if op == 'task_spawn':
            operand, (_, name) = self.expression(expr[1], env, line, uses)
            return (op, operand, *expr[2:]), ('execution', name)
        if op == 'task_join_value':
            operand, (mode, name) = self.expression(expr[1], env, line, uses)
            function = self.functions.get(name) if mode == 'execution' else None
            signature = (('join_async_execution', function.args[2][1])
                         if function and function.args[2][0] == 'async_execution' else UNKNOWN)
            return (op, operand), signature
        if op == 'utf8_value':
            operand, (mode, typ) = self.expression(expr[1], env, line, uses)
            signature = ('async_execution', typ) if mode == 'join_async_execution' else UNKNOWN
            return (op, operand, *expr[2:]), signature
        if op == 'task_select':
            return (op, tuple(self.tree(arg, env, line, uses) for arg in expr[1])), ('selection', None)
        if op == 'await':
            operand, (kind, name) = self.expression(expr[1], env, line, uses)
            function = self.functions.get(name)
            if kind == 'pending_guard':
                return (op, operand), ('owned', name)
            return (op, operand), function.args[2] if kind == 'task' and function else UNKNOWN
        if op in ('transfer', 'array_transfer', 'new_transfer', 'array_copy'):
            value, signature = self.expression(expr[1], env, line, uses)
            return (op, value), signature
        values = tuple(self.tree(value, env, line, uses) for value in expr[1:])
        modes = {'int': 'scalar', 'arithmetic': 'scalar', 'bool': 'bool', 'text': 'text',
                 'array_literal': 'array', 'array_repeat': 'array'}
        return (op, *values), (modes.get(op), None)


def lower_value_moves(nodes, node_type):
    ValueMoves(nodes, node_type).run(nodes)
