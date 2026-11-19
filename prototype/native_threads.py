"""Give each synchronous native block a concrete task-state definition.

This pass infers signatures only. The ordinary memory verifier/lowerer still
checks every operation, captured target, return and outstanding handle.
"""
from dataclasses import dataclass, replace

from array_syntax import fixed_array_shape, reference_type
from builtin_signatures import normalized_type
from async_lowering import branch_control_exit, expression_control_exit
from numeric_core import FORMATS, MODE_TYPES, conversion_mode, conversion_type


@dataclass(frozen=True)
class Local:
    signature: tuple | None
    mutable: bool = False


class NativeBlocks:
    def __init__(self, nodes, node_type, error):
        self.nodes, self.Node, self.error = nodes, node_type, error
        self.functions = {n.args[0]: n for n in nodes if n.op in ('fn', 'async_fn')}
        self.structures = {n.args[0]: dict(n.args[1][0][1]) for n in nodes if n.op == 'struct'}
        self.methods = {(n.args[0], method.args[0]): method for n in nodes if n.op == 'impl'
                        for method in n.args[1]}
        self.generated = []
        self.serial = 0
        self.native_depth = 0

    def fail(self, line, message):
        raise self.error(f'ligne {line}: bloc runtime::thread : {message}')

    @staticmethod
    def declared(typ, mode='scalar'):
        if mode == 'scalar' and typ.startswith('A<') and typ.endswith('>'):
            return 'owned', typ[2:-1]
        capability = reference_type(typ)
        if capability:
            mode, typ = capability
        mode, typ, _ = normalized_type(mode, typ, result=True)
        return mode, typ

    @staticmethod
    def common(values):
        values = set(values)
        return next(iter(values)) if len(values) == 1 else None

    def joined(self, signature):
        mode, typ = signature
        payload = f'A<{typ}>' if mode == 'owned' else '&mut ' + typ if mode == 'mut' else '&' + typ if mode in ('ref', 'byte_ref', 'text') else '()' if typ == 'Void' else typ
        return self.declared(f'Result<{payload},runtime::Error>')

    def expression(self, expr, env, returns):
        if expr is None:
            return None, ('void', 'Void')
        if not isinstance(expr, tuple) or not expr:
            return expr, None
        op = expr[0]
        if op == 'native_thread':
            _, captures, body, line, modern = expr
            parameters, arguments, mutable = [], [], set()
            copied = set()
            captured_env = {}
            for name in captures:
                binding = env.get(name)
                if binding is None or binding.signature is None:
                    self.fail(line, f"type de capture non déduit pour '{name}'")
                mode, typ = binding.signature
                if modern and mode in (*MODE_TYPES, 'bool', 'char', 'runtime_error'):
                    copied.add(len(parameters))
                if mode == 'source':
                    self.fail(line, 'un pool local ne se transfère pas ; préparer un emprunt')
                parameters.append((name, mode, typ))
                arguments.append(('down' if mode == 'owned' else 'move' if mode == 'array' else 'name', name))
                captured_env[name] = binding
                if binding.mutable:
                    mutable.add(name)
            body = list(body)
            if body and body[-1].op == 'if_yield':
                body[-1] = replace(body[-1], op='return')
            elif body and body[-1].op == '<-' and not body[-1].terminated:
                tail = body[-1]
                body[-1] = replace(tail, op='return', args=(('move', tail.args[0]),))
            results = []
            self.native_depth += 1
            try:
                body, _ = self.block(body, captured_env, results)
            finally:
                self.native_depth -= 1
            if not branch_control_exit(body):
                results.append(('void', 'Void'))
            result = self.common(results)
            if result is None:
                self.fail(line, 'les retours et la valeur finale doivent avoir un même type déductible')
            while True:
                name = f'__crust_native_block${self.serial}'
                self.serial += 1
                if name not in self.functions:
                    break
            definition = self.Node('async_fn', (name, parameters, result, body), line,
                                   mutable_parameters=frozenset(mutable), native_block=True,
                                   native_copies=frozenset(copied),
                                   # The native header transfers existing values;
                                   # it does not declare a new A<T> requirement.
                                   # Concrete storage is selected by the caller.
                                   handle_parameters=frozenset(n for n, m, t in parameters
                                                               if m == 'owned' and t not in self.structures),
                                   handle_result=result[0] == 'owned')
            self.generated.append(definition)
            self.functions[name] = definition
            return ('task_spawn', ('transfer', ('call', name, arguments)), 'native'), ('execution', name)
        if op == 'scope':
            body, tails = self.block(expr[2], env.copy(), returns)
            return (op, expr[1], body, *expr[3:]), self.common(tails)
        if op == 'value_match':
            body, tails = self.block(expr[1], env.copy(), returns)
            return (op, body), self.common(tails)
        if op == 'loop_expr':
            loop = expr[1]
            body, tails = self.block(loop.args[0], env.copy(), returns)
            return (op, replace(loop, args=(body,))), self.common(tails)
        if op == 'if_expr':
            condition = self.any(expr[1], env, returns)
            bodies, values = [], []
            for branch in expr[2:]:
                if isinstance(branch, list):
                    body, tails = self.block(branch, env.copy(), returns)
                    values.extend(tails)
                else:
                    body, signature = self.expression(branch, env.copy(), returns)
                    values.append(signature)
                bodies.append(body)
            return (op, condition, *bodies), self.common(values)
        transformed = (op, *(self.any(value, env, returns) for value in expr[1:]))
        expr = transformed
        if op in ('array_numeric_literal', 'array_numeric_operation', 'array_numeric_cast'):
            typ = expr[1]
            return transformed, (FORMATS[typ].mode, 'Int' if typ == 'i32' else typ)
        if op == 'array_numeric_not':
            return transformed, ('scalar', 'Bool')
        if op in ('array_numeric_len', 'array_numeric_slice_len'):
            return transformed, ('u64', 'u64')
        if op == 'array_numeric_try_from':
            return transformed, (conversion_mode(expr[1]), conversion_type(expr[1]))
        if op in ('array_mutex_new', 'array_mutex_lock'):
            return transformed, ('owned', expr[1])
        if op in ('name', 'move', 'down'):
            return transformed, env.get(expr[1], Local(None)).signature
        if op in ('ref', 'mut', 'reborrow', 'deref'):
            binding = env.get(expr[1], Local(None)).signature
            if binding is not None:
                mode = expr[2] if op == 'reborrow' else op
                return transformed, self.declared(binding[1], 'scalar' if op == 'deref' else mode)
        if op in ('ref_expr', 'mut_expr'):
            _, signature = self.expression(expr[1], env, [])
            return transformed, self.declared(signature[1], op[:-5]) if signature else None
        if op in ('transfer', 'new_transfer', 'array_transfer', 'array_copy'):
            return transformed, self.expression(expr[1], env, [])[1]
        if op == 'source':
            return transformed, ('source', f'Pool<{expr[3]}>') if expr[1] == 'pool' else None
        if op == 'new':
            source = env.get(expr[1], Local(None)).signature
            typ = source[1][5:-1] if source and source[1].startswith('Pool<') else expr[3]
            return transformed, ('owned', typ)
        if op == 'new_enum':
            source = env.get(expr[1], Local(None)).signature
            typ = expr[2] or (source[1][5:-1] if source and source[1].startswith('Pool<') else None)
            return transformed, ('owned', typ) if typ else None
        if op == 'field':
            binding = env.get(expr[1], Local(None)).signature
            typ = binding[1] if binding else None
            for field in expr[2].split('.'):
                typ = self.structures.get(typ, {}).get(field)
            return transformed, self.declared(typ) if typ else None
        if op == 'field_deref':
            _, signature = self.expression(expr[1], env, [])
            if signature in (('ref', 'Int'), ('mut', 'Int'), ('owned', 'Int')):
                return transformed, ('scalar', 'Int')
        if op == 'method_call' and expr[1][0] == 'name':
            binding = env.get(expr[1][1], Local(None)).signature
            method = self.methods.get((binding[1], expr[2])) if binding else None
            if method is not None:
                result = method.args[2]
                return transformed, ('scalar', 'Bool') if result == ('bool', 'bool') else result
        if op == 'utf8_slice':
            _, source = self.expression(expr[1], env, [])
            if source and source[1] in ('str', 'String'):
                return transformed, ('text', 'str')
            if source and source[1] in ('Vector<Int>', 'Vector<u8>', '[Int]', '[u8]'):
                element = 'Int' if source[1] in ('Vector<Int>', '[Int]') else 'u8'
                return transformed, self.declared(f'&[{element}]')
        if op == 'array_index':
            _, source = self.expression(expr[1], env, [])
            shape = fixed_array_shape(source[1]) if source else None
            if shape:
                return transformed, self.declared(shape[0])
            if source and source[1] in ('str', 'String', 'Vector<u8>'):
                return transformed, ('byte', 'u8')
        if op in ('array_literal', 'array_repeat'):
            items = expr[1:] if op == 'array_literal' else expr[1:2]
            signatures = [self.expression(item, env, [])[1] for item in items]
            common = self.common(signatures)
            if common:
                count = len(items) if op == 'array_literal' else expr[2]
                prefix = '&mut ' if common[0] == 'mut' else '&' if common[0] == 'ref' else ''
                return transformed, ('array', f'[{prefix}{common[1]};{count}]')
        if op == 'call' and expr[1] in self.functions:
            fn = self.functions[expr[1]]
            # Ordinary bool signatures and state Bool signatures have distinct
            # historical modes. Preserve the boolean type at this boundary.
            result = ('scalar', 'Bool') if fn.args[2] == ('bool', 'bool') else fn.args[2]
            return transformed, ('task', expr[1]) if fn.op == 'async_fn' else result
        if op == 'task_spawn':
            signature = self.expression(expr[1], env, [])[1]
            return transformed, ('execution', signature[1]) if signature else None
        if op == 'await':
            signature = self.expression(expr[1], env, [])[1]
            if signature and signature[1] in self.functions:
                result = self.functions[signature[1]].args[2]
                if signature[0] == 'task':
                    return transformed, result
                return transformed, self.joined(result)
        if op in ('task_join', 'task_join_value'):
            operand = ('name', expr[1]) if op == 'task_join' else expr[1]
            _, signature = self.expression(operand, env, [])
            result = None
            if signature and signature[0] == 'execution' and signature[1] in self.functions:
                result = self.joined(self.functions[signature[1]].args[2])
            # Internal await-shaped operation shares result/provenance checking.
            # native_block selects a blocking wait in the backend, never yield.
            return (('await', operand) if self.native_depth else transformed), result
        if op == 'utf8_value':
            _, signature = self.expression(expr[1], env, [])
            if signature and signature[1].startswith(('Result<', 'Option<')):
                content = signature[1][7:-1]
                depth = 0
                for index, char in enumerate(content):
                    if char == ',' and depth == 0:
                        content = content[:index]
                        break
                    depth += (char == '<') - (char == '>')
                return transformed, self.declared(content, 'owned' if content.startswith('A<') else 'scalar')
        types = {'int': 'Int', 'arithmetic': 'Int', 'bool': 'Bool', 'text': '&str',
                 'array_byte_literal': 'u8', 'utf8_runtime_error': 'runtime::Error',
                 'array_integer_try_from': 'Result<u8,IntegerConversionError>'}
        typ = expr[2] if op == 'array_integer_cast' else types.get(op)
        return transformed, self.declared(typ) if typ else None

    def any(self, value, env, returns):
        if isinstance(value, list):
            if value and isinstance(value[0], self.Node):
                return self.block(value, env.copy(), returns)[0]
            return [self.any(item, env, returns) for item in value]
        if isinstance(value, self.Node):
            return self.block([value], env.copy(), returns)[0][0]
        if isinstance(value, tuple):
            return self.expression(value, env, returns)[0]
        return value

    def block(self, nodes, env, returns):
        output, tails = [], []
        reachable = True
        for node in nodes:
            result_paths = returns if reachable else []
            op, args = node.op, node.args
            if op in ('var', 'assign'):
                expression, signature = self.expression(args[1], env, result_paths)
                if node.annotation:
                    signature = self.declared(node.annotation, 'owned' if node.annotation.startswith('A<') else 'scalar')
                if op == 'var':
                    env[args[0]] = Local(signature, node.mutable)
                node = replace(node, args=(args[0], expression))
            elif op in ('return', 'if_yield', 'break'):
                expression, signature = self.expression(args[0], env, result_paths)
                if reachable and not expression_control_exit(expression):
                    (result_paths if op == 'return' else tails).append(signature)
                node = replace(node, args=(expression, *args[1:]))
            elif op in ('<-', 'match_yield'):
                if reachable:
                    tails.append(env.get(args[0], Local(None)).signature)
            elif op in ('fn', 'async_fn'):
                name, params, result, body = args
                local = {n: Local((m, t), n in node.mutable_parameters) for n, m, t in params}
                body, _ = self.block(body, local, [])
                node = replace(node, args=(name, params, result, body))
            elif op == 'if':
                condition = self.any(args[0], env, result_paths)
                branches = []
                for branch in args[1:]:
                    body, values = self.block(branch, env.copy(), result_paths)
                    if reachable:
                        tails.extend(values)
                    branches.append(body)
                node = replace(node, args=(condition, *branches))
            elif op == 'scope':
                body, values = self.block(args[1], env.copy(), result_paths)
                if reachable:
                    tails.extend(values)
                node = replace(node, args=(args[0], body))
            else:
                node = replace(node, args=tuple(self.any(arg, env, result_paths) for arg in args))
            output.append(node)
            if reachable and branch_control_exit([node]):
                reachable = False
        return output, tails

    def run(self):
        rewritten, _ = self.block(self.nodes, {}, [])
        return [*self.generated, *rewritten]


def lower_native_blocks(nodes, node_type, error):
    def contains(value):
        if isinstance(value, node_type):
            return contains(value.args)
        if isinstance(value, (tuple, list)):
            return bool(value and value[0] == 'native_thread') or any(contains(item) for item in value)
        return False
    return NativeBlocks(nodes, node_type, error).run() if contains(nodes) else nodes
