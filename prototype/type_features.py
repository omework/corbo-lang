"""Static feature resolution before memory-contract inference.

This pass chooses concrete signatures; it does not discharge ownership, borrow,
source or effect obligations. Those remain with the ordinary concrete verifier.
The abstract pass deliberately runs independently of call-site specializations.
"""
from dataclasses import replace
import re

from effects import EffectAnalyzer, SymbolicSource, method_arguments
from array_syntax import reference_type
from builtin_signatures import normalized_type, builtin_method_signatures, feature_method_candidate


TYPE_ATOM = re.compile(r'\$[0-9]+[TR]|[A-Za-z_][A-Za-z_0-9]*')


def substitute(typ, bindings):
    return TYPE_ATOM.sub(lambda token: bindings.get(token[0], token[0]), typ)


class FeatureResolver:
    def __init__(self, nodes, enums, error):
        self.nodes, self.enums, self.error = nodes, enums, error
        self.features, self.functions = {}, {}
        self.contracts, self.result_parameters = {}, set()
        self.resolved, self.instances, self.visiting = {}, {}, set()
        self.line = 1
        for node in nodes:
            if node.op == 'feature':
                name, method = node.args
                if name in self.features or name in enums or name in (
                        'Int', 'bool', 'u8', 'char', 'str', 'String', 'Void', 'Pool',
                        'Allocator', 'A', 'Vector', 'Option', 'Result'):
                    self.fail(f"nom de feature déjà utilisé ou réservé : '{name}'", node.line)
                self.features[name] = method
            elif node.op in ('fn', 'async_fn'):
                name = node.args[0]
                if name in self.functions:
                    self.fail(f"nom de fonction déjà utilisé : '{name}'", node.line)
                if node.type_contract:
                    node = self.scope_contract(node, len(self.functions))
                self.functions[name] = node
        self.analyzer = EffectAnalyzer(self.functions, enums, error,
            {name: node for name, node in self.functions.items() if node.op == 'async_fn'})

    def fail(self, message, line=None):
        raise self.error(f'ligne {self.line if line is None else line}: {message}')

    def feature_names(self, typ):
        return set(TYPE_ATOM.findall(typ or '')) & (
            self.features.keys() | self.contracts.keys() | self.result_parameters)

    def abstract_type(self, typ):
        return isinstance(typ, str) and bool(self.feature_names(typ))

    @staticmethod
    def bind_signature(node, bindings):
        name, params, (mode, typ), body = node.args
        return replace(node, args=(name, [(p, m, substitute(t, bindings)) for p, m, t in params],
                                   (mode, substitute(typ, bindings)), body))

    def scope_contract(self, node, index):
        carrier, result, alternatives, methods, _ = node.type_contract
        if not any(typ == carrier for _, _, typ in node.args[1]):
            self.fail(f"le contrat exige un paramètre de type '{carrier}'", node.line)
        carrier_id, result_id = f'${index}T', f'${index}R'
        names = {carrier: carrier_id, result: result_id}
        if any(substitute(typ, names) != typ for typ in alternatives):
            self.fail('les alternatives du contrat doivent être des types concrets', node.line)
        requirements = {method.args[0]: self.bind_signature(method, names) for method in methods}
        self.contracts[carrier_id] = (carrier, result_id, alternatives, requirements)
        self.result_parameters.add(result_id)
        return self.bind_signature(node, names)

    def infer_signature(self, supplied, expected, variable, bound):
        supplied_params, supplied_result = supplied
        expected_params, expected_result = expected
        if len(supplied_params) != len(expected_params):
            return False, bound
        for index, ((smode, stype, shandle), (emode, etype, ehandle)) in enumerate(zip(
                (*supplied_params, supplied_result), (*expected_params, expected_result))):
            if bound is None and variable in TYPE_ATOM.findall(etype):
                parts = etype.split(variable)
                pattern = re.escape(parts[0]) + '(.+?)' + re.escape(parts[1])
                for part in parts[2:]:
                    pattern += r'\1' + re.escape(part)
                actual = f'A<{stype}>' if shandle and not ehandle and etype == variable else stype
                match = re.fullmatch(pattern, actual)
                if match is None:
                    return False, bound
                bound = match[1]
            etype = substitute(etype, {variable: bound or variable})
            emode, etype, inferred = self.concrete_type(emode, etype, result=index == len(supplied_params))
            if (smode, stype, shandle) != (emode, etype, ehandle or inferred):
                return False, bound
        return True, bound

    def concrete_type(self, mode, typ, *, result=False):
        if mode == 'scalar' and (typ in self.enums or typ.startswith(('A<', 'Task<', 'runtime::Handle<'))):
            mode = 'owned'
        return normalized_type(mode, typ, result=result)

    @staticmethod
    def future_method(typ, method, payload):
        if method == 'id':
            return ((('ref', typ, False),), ('i64', 'i64', False))
        if method == 'poll':
            return ((('mut', typ, False), ('mut', 'runtime::Context', False)),
                    ('scalar', f'runtime::Poll<{payload}>', False))
        return None

    def task_method(self, task, method):
        definition = self.resolved.get(task[5:-1]) or self.functions.get(task[5:-1])
        if definition is None or definition.op != 'async_fn':
            return ()
        from async_lowering import public_handle_type
        storage = definition.join_storage_result or (
            'local' if not definition.handle_result and definition.args[2][1] in self.enums else 'pool')
        handle = public_handle_type(definition.args[2], storage=storage)
        signature = self.future_method(task, method, handle[len('runtime::Handle<'):-1])
        return (signature,) if signature else ()

    def contract_bindings(self, node, actual_types):
        carrier_id = next(typ for _, _, typ in node.args[1] if typ in self.contracts)
        carrier, variable, alternatives, requirements = self.contracts[carrier_id]
        concrete = {actual for (_, _, typ), actual in zip(node.args[1], actual_types) if typ == carrier_id}
        if len(concrete) != 1 or None in concrete:
            self.fail(f"le contrat de '{carrier}' exige un seul type concret par appel")
        actual = concrete.pop()
        bindings = {carrier_id: actual}
        candidates = {None}
        for method, requirement in requirements.items():
            expected = self.signature(self.bind_signature(requirement, bindings))
            if actual in self.contracts:
                other = self.contracts[actual][3].get(method)
            elif actual in self.features:
                other = self.features[actual] if self.features[actual].args[0] == method else None
            else:
                other = self.functions.get(f'{actual}.{method}')
            if other is not None:
                signatures = (self.signature(other),)
            elif actual.startswith('Task<'):
                signatures = self.task_method(actual, method)
            else:
                signatures = builtin_method_signatures(actual, method)
            candidates = {bound for signature in signatures for previous in candidates
                          for matches, bound in [self.infer_signature(signature, expected, variable, previous)]
                          if matches}
            if not candidates:
                self.fail(f"type '{actual}' : exigence de contrat non satisfaite pour '{method}'")
        if alternatives:
            candidates = {bound for bound in candidates if bound in alternatives or
                          (bound == 'Bool' and 'bool' in alternatives) or
                          (bound in self.result_parameters and any(
                              other_var == bound and other_choices and set(other_choices) <= set(alternatives)
                              for _, other_var, other_choices, _ in self.contracts.values()))}
        if len(candidates) != 1 or None in candidates:
            self.fail(f"le contrat de '{carrier}' exige un paramètre de type unique compatible")
        bindings[variable] = candidates.pop()
        return bindings

    def signature(self, node, concrete=None):
        _, params, result, _ = node.args
        def normalized(mode, typ, handle, *, result=False):
            mode, typ, inferred_handle = normalized_type(mode, typ, result=result)
            return mode, typ, handle or inferred_handle
        # Only the receiver denotes the implementation selected here. Other
        # feature parameters remain independent constraints (TF2), even when
        # they use the same feature name. A feature result also remains a
        # constraint, not an implicit promise to return the receiver's type.
        joined = dict(getattr(node, 'join_storage_parameters', ()))
        return (tuple(normalized(mode, concrete if index == 0 and concrete is not None else typ,
                                 name in node.handle_parameters or joined.get(name) == 'pool')
                      for index, (name, mode, typ) in enumerate(params)),
                normalized(*result, node.handle_result or getattr(node, 'join_storage_result', None) == 'pool', result=True))

    def signatures_match(self, supplied, required, pending):
        supplied_params, supplied_result = supplied
        required_params, required_result = required
        if len(supplied_params) != len(required_params):
            return False
        for (smode, stype, shandle), (rmode, rtype, rhandle) in zip(supplied_params, required_params):
            if (smode, shandle) != (rmode, rhandle):
                return False
            if stype != rtype:
                if stype not in self.features or rtype not in self.features:
                    return False
                if not (self.satisfies(stype, rtype, pending) and self.satisfies(rtype, stype, pending)):
                    return False
        smode, stype, shandle = supplied_result
        rmode, rtype, rhandle = required_result
        if rtype in self.features:
            # A feature result describes a constraint on the concrete result,
            # not equality with the receiver. Normalize its capability for the
            # actual result type, just as a specialized function signature does.
            rmode, _, inferred_handle = normalized_type(rmode, stype, result=True)
            return ((smode, shandle) == (rmode, rhandle or inferred_handle)
                    and self.satisfies(stype, rtype, pending))
        return supplied_result == required_result

    def satisfies(self, actual, feature, pending=frozenset()):
        pair = actual, feature
        if pair in pending:
            # Recursive structural requirements are checked coinductively.
            # The enclosing comparison still checks every method name, mode,
            # parameter and result. This is not recursion in executable code.
            return True
        pending = pending | {pair}
        required = self.features[feature]
        if actual in self.features:
            supplied = self.features[actual]
            return (supplied.args[0] == required.args[0]
                    and self.signatures_match(self.signature(supplied, '$self'),
                                              self.signature(required, '$self'), pending))
        method = self.functions.get(f'{actual}.{required.args[0]}')
        expected = self.signature(required, actual)
        if method is not None:
            return self.signatures_match(self.signature(method), expected, pending)
        return any(self.signatures_match(signature, expected, pending)
                   for signature in builtin_method_signatures(actual, required.args[0]))

    def require(self, actual, feature):
        if not self.satisfies(actual, feature):
            self.fail(f"type '{actual}' : exigence de feature '{feature}' non garantie "
                      f"(méthode {self.features[feature].args[0]} et signature conformes requises)")

    def generic(self, node):
        return (node.type_contract is not None or
                any(typ in self.features for _, _, typ in node.args[1]) or node.args[2][1] in self.features)

    def validate_types(self):
        for typ, variants in self.enums.items():
            for fields in variants.values():
                for name, field in fields:
                    if self.feature_names(field):
                        self.fail(f"champ '{typ}.{name}' : une feature est réservée aux signatures")
        requirements = {id(method): method for _, _, _, methods in self.contracts.values()
                        for method in methods.values()}
        for node in (*self.functions.values(), *self.features.values(), *requirements.values()):
            self.line = node.line
            allows_bound_types = node.type_contract is not None or id(node) in requirements
            names = [name for name, _, _ in node.args[1]]
            if len(names) != len(set(names)):
                self.fail('paramètre dupliqué dans la signature')
            if node.args[0] == 'main' and self.generic(node):
                self.fail('main doit être sans paramètre, avec un retour Void ou Int')
            for name, mode, typ in node.args[1]:
                if self.feature_names(typ) and typ not in self.features and not allows_bound_types:
                    self.fail('une collection ou un emplacement doit avoir un type concret')
                if typ in self.features and mode not in ('ref', 'mut', 'owned'):
                    self.fail('un paramètre feature exige & ou &mut ou -> explicite')
                if typ in self.features and name in node.handle_parameters:
                    self.fail('un emplacement A<T> doit avoir un type concret')
            mode, typ = node.args[2]
            if self.feature_names(typ) and typ not in self.features and not allows_bound_types:
                self.fail('un résultat composé doit avoir un type concret')
            if typ in self.features and (mode not in ('ref', 'mut', 'owned') or node.handle_result):
                self.fail('un résultat feature exige un emprunt ou un transfert explicite')

    def run(self):
        self.validate_types()
        # Check guarantees even in never-instantiated functions. No concrete
        # method inventory is substituted into this environment.
        for node in self.functions.values():
            if self.generic(node):
                env, modes = self.environment(node.args[1])
                self.block(node.args[3], env, modes, True, [])
        output = [node for node in self.nodes if node.op in ('struct', 'enum')]
        for name, node in self.functions.items():
            if not self.generic(node):
                self.instantiate(name, ())
        main = [node for node in self.nodes if node.op not in ('struct', 'enum', 'feature', 'fn', 'async_fn')]
        main, _ = self.block(main, {}, {}, False, [])
        output.extend(self.resolved.values())
        output.extend(main)
        return output

    @staticmethod
    def environment(params):
        env, modes = {}, {}
        for name, mode, typ in params:
            env[name] = (SymbolicSource(None, mode == 'mut', typ[5:-1], 'pool')
                         if typ.startswith('Pool<') else typ)
            modes[name] = mode
        return env, modes

    def instantiate(self, name, concrete, bindings=None):
        key = name, tuple(concrete)
        if key in self.visiting:
            self.fail('prototype : récursion de résolution de feature non prise en charge')
        if key in self.instances:
            return self.instances[key]
        node = self.functions[name]
        contracted = node.type_contract is not None
        if contracted:
            node = self.bind_signature(node, bindings)
        params = list(node.args[1])
        handles = set(node.handle_parameters)
        if concrete:
            for i, actual in enumerate(concrete):
                pname, mode, typ = params[i]
                if typ in self.features:
                    self.require(actual, typ)
                    mode, typ, handle = normalized_type(mode, actual)
                    params[i] = pname, mode, typ
                    if handle:
                        handles.add(pname)
                elif contracted:
                    mode, typ, handle = self.concrete_type(mode, typ)
                    params[i] = pname, mode, typ
                    if handle:
                        handles.add(pname)
        generic = self.generic(node)
        concrete_name = f'{name}$feature{len(self.instances)}' if generic else name
        self.instances[key] = concrete_name
        self.visiting.add(key)
        env, modes = self.environment(params)
        returns = []
        body, tails = self.block(node.args[3], env, modes, False, returns)
        result = node.args[2]
        handle_result = node.handle_result
        if contracted:
            mode, typ, handle = self.concrete_type(*result, result=True)
            result, handle_result = (mode, typ), handle_result or handle
            # The concrete verifier represents a task parameter by the async
            # definition name. The structural pass uses Task<name> to keep the
            # task distinct from nominal structures while resolving calls.
            params = [(p, m, t[5:-1] if m == 'owned' and t.startswith('Task<') else t)
                      for p, m, t in params]
            if mode == 'owned' and typ.startswith('Task<'):
                result = mode, typ[5:-1]
        if result[1] in self.features:
            candidates = set(returns + tails)
            if len(candidates) != 1 or None in candidates:
                self.fail('le résultat feature exige un type concret unique déductible', node.line)
            typ = next(iter(candidates))
            self.require(typ, result[1])
            mode, typ, handle_result = normalized_type(result[0], typ, result=True)
            result = mode, typ
        resolved = replace(node, args=(concrete_name, params, result, body),
                           handle_parameters=frozenset(handles), handle_result=handle_result,
                           type_contract=None)
        self.resolved[concrete_name] = resolved
        # The lightweight type query needs signatures only, never contracts.
        self.analyzer.functions = {**self.functions, **self.resolved}
        self.analyzer.async_functions.update({name: node for name, node in self.resolved.items()
                                             if node.op == 'async_fn'})
        self.visiting.remove(key)
        return concrete_name

    def call(self, name, args, env, modes, abstract, returns):
        transformed, types = [], []
        for arg in args:
            value, typ = self.expression(arg, env, modes, abstract, returns)
            transformed.append(value)
            types.append(typ)
        node = self.functions.get(name)
        if node is None:
            if any(self.abstract_type(typ) for typ in types):
                self.fail(f"appel '{name}' sans garantie pour le paramètre feature")
            return ('call', name, transformed), self.type_of(('call', name, transformed), env)
        if len(node.args[1]) != len(args):
            self.fail(f"'{name}' : nombre d’arguments incompatible")
        bindings = self.contract_bindings(node, types) if node.type_contract else None
        bound_node = self.bind_signature(node, bindings) if bindings else node
        for (_, _, expected), actual in zip(bound_node.args[1], types):
            if expected in self.features:
                self.require(actual, expected)
            elif self.abstract_type(actual) and actual != expected:
                self.fail(f"type concret '{expected}' non garanti par la feature '{actual}'")
        if self.generic(node) and not abstract:
            resolved = self.instantiate(name, types, bindings)
            typ = (f'Task<{resolved}>' if node.type_contract and node.op == 'async_fn' else
                   self.resolved[resolved].args[2][1])
            return ('call', resolved, transformed), typ
        typ = f'Task<{name}>' if self.contracts and node.op == 'async_fn' else bound_node.args[2][1]
        return ('call', name, transformed), typ

    def type_of(self, expr, env):
        if expr is None:
            return 'Void'
        if expr[0] in ('ref_deref', 'mut_deref', 'reborrow'):
            return env.get(expr[1])
        if expr[0] in ('name', 'ref', 'mut') and isinstance(env.get(expr[1]), SymbolicSource):
            source = env[expr[1]]
            return f'Pool<{source.element}>' if source.kind == 'pool' else 'Allocator'
        if expr[0] in ('array_literal', 'array_repeat'):
            elements = expr[1:] if expr[0] == 'array_literal' else expr[1:2]
            typ = self.common(self.type_of(value, env) for value in elements)
            if typ is not None:
                count = len(elements) if expr[0] == 'array_literal' else expr[2]
                return f'[{typ};{count}]'
        if expr[0] in ('array_ref', 'array_mut_ref'):
            return self.type_of(expr[1], env)
        if expr[0] == 'deref' and self.abstract_type(env.get(expr[1])):
            return env[expr[1]]
        return self.analyzer.receiver_type(expr, env)

    @staticmethod
    def common(types):
        values = set(types)
        return next(iter(values)) if len(values) == 1 else None

    def any(self, value, env, modes, abstract, returns):
        if isinstance(value, list):
            if value and hasattr(value[0], 'op'):
                return self.block(value, env.copy(), modes.copy(), abstract, returns)[0]
            return [self.any(x, env, modes, abstract, returns) for x in value]
        if isinstance(value, tuple):
            return self.expression(value, env, modes, abstract, returns)[0]
        if hasattr(value, 'op'):
            return self.block([value], env.copy(), modes.copy(), abstract, returns)[0][0]
        return value

    def expression(self, expr, env, modes, abstract, returns):
        if expr is None or not isinstance(expr, tuple) or not expr:
            return expr, None
        op = expr[0]
        if op == 'call':
            return self.call(expr[1], expr[2], env, modes, abstract, returns)
        if op == 'task_spawn':
            operand, typ = self.expression(expr[1], env, modes, abstract, returns)
            if self.abstract_type(typ):
                _, variable, _, requirements = self.contracts.get(typ, (None, None, (), {}))
                if any(name not in requirements or self.signature(requirements[name]) !=
                       self.future_method(typ, name, variable) for name in ('id', 'poll')):
                    self.fail('spawn exige le contrat Future avec id et poll')
                return (op, operand, *expr[2:]), f'runtime::Handle<{variable}>'
            value = (op, operand, *expr[2:])
            return value, self.type_of(value, env)
        if op == 'field' and self.abstract_type(env.get(expr[1])):
            self.fail(f"champ '{expr[2]}' non garanti par la feature")
        candidate = feature_method_candidate(expr)
        if candidate is not None:
            receiver, method, arguments = candidate[1:]
            receiver, typ = self.expression(receiver, env, modes, abstract, returns)
            if abstract and typ is None:
                self.fail('type du receveur non déduit dans le corps contraint par une feature')
            if self.abstract_type(typ):
                if typ in self.contracts:
                    declaration = self.contracts[typ][3].get(method)
                else:
                    declaration = self.features.get(typ)
                if declaration is None or method != declaration.args[0]:
                    self.fail(f"méthode '{method}' non garantie par la feature '{typ}'")
                mode = declaration.args[1][0][1]
                named = receiver[0] in ('name', 'down')
                receiver_mode = modes.get(receiver[1]) if named else None
                if named:
                    if typ not in self.contracts:
                        method_arguments(receiver, mode, receiver_mode, arguments, self.fail)
                elif mode == 'owned':
                    self.fail('un receveur consommé exige (-> valeur)')
                if receiver_mode == 'ref' and mode in ('mut', 'owned'):
                    self.fail('la méthode exige un receveur mutable ou consommable')
                transformed = []
                if len(arguments) + 1 != len(declaration.args[1]):
                    self.fail('méthode de feature : nombre d’arguments incompatible')
                for arg, (_, _, expected) in zip(arguments, declaration.args[1][1:]):
                    val, actual = self.expression(arg, env, modes, abstract, returns)
                    if expected in self.features:
                        self.require(actual, expected)
                    elif self.abstract_type(actual) and actual != expected:
                        self.fail(f"type '{expected}' non garanti par la feature")
                    transformed.append(val)
                return ('method_call', receiver, method, transformed), declaration.args[2][1]
            concrete_method = self.functions.get(f'{typ}.{method}')
            if concrete_method is not None and self.generic(concrete_method):
                mode = concrete_method.args[1][0][1]
                args = method_arguments(receiver, mode, modes.get(receiver[1]), arguments, self.fail)
                return self.call(f'{typ}.{method}', args, env, modes, abstract, returns)
        if op == 'scope':
            body, tails = self.block(expr[2], env.copy(), modes.copy(), abstract, returns)
            return (op, expr[1], body, *expr[3:]), self.common(tails)
        if op == 'if_expr':
            condition = self.any(expr[1], env, modes, abstract, returns)
            bodies, types = [], []
            for branch in expr[2:]:
                if isinstance(branch, list):
                    body, tails = self.block(branch, env.copy(), modes.copy(), abstract, returns)
                    types.extend(tails)
                else:
                    body, typ = self.expression(branch, env.copy(), modes.copy(), abstract, returns)
                    types.append(typ)
                bodies.append(body)
            return (op, condition, *bodies), self.common(types)
        if op in ('match_expr', 'value_match', 'loop_expr'):
            node = expr[1]
            body, tails = self.block([node], env.copy(), modes.copy(), abstract, returns,
                                     value_context=True)
            return (op, body[0], *expr[2:]), self.common(tails)
        if op == 'source' and self.feature_names(expr[3] if len(expr) > 3 else ''):
            self.fail('un pool doit avoir un type concret')
        # Recurse into all operands, including nested constructors and arguments.
        if op in ('transfer', 'new_transfer', 'array_transfer', 'ref_expr', 'mut_expr'):
            value, typ = self.expression(expr[1], env, modes, abstract, returns)
            return (op, value, *expr[2:]), typ
        transformed = (op, *(self.any(x, env, modes, abstract, returns) for x in expr[1:]))
        return transformed, self.type_of(transformed, env)

    def block(self, nodes, env, modes, abstract, returns, *, value_context=False):
        output, tails = [], []
        for node in nodes:
            self.line = node.line
            op, args = node.op, node.args
            if node.annotation and self.feature_names(node.annotation):
                self.fail('une annotation de stockage doit avoir un type concret')
            if op in ('var', 'assign'):
                name, expr = args
                value, typ = self.expression(expr, env, modes, abstract, returns)
                if expr[0] == 'source':
                    typ = SymbolicSource(None, node.mutable, expr[3] if expr[1] == 'pool' else None, expr[1])
                if op == 'var' or typ is not None:
                    if node.annotation is not None:
                        capability = reference_type(node.annotation)
                        typ = capability[1] if capability else node.annotation
                    env[name] = typ
                    mode = (expr[0] if expr[0] in ('ref', 'mut') else
                            modes.get(expr[1]) if expr[0] == 'name' else None)
                    if expr[0] == 'reborrow':
                        mode = expr[2]
                    if expr[0] == 'call':
                        callee = self.resolved.get(value[1], self.functions.get(value[1]))
                        mode = callee.args[2][0] if callee else mode
                    modes[name] = mode
                node = replace(node, args=(name, value))
            elif op in ('return', 'if_yield', 'break'):
                value, typ = self.expression(args[0], env, modes, abstract, returns)
                (returns if op == 'return' else tails).append(typ)
                node = replace(node, args=(value,))
            elif op in ('<-', 'match_yield'):
                tails.append(env.get(args[0]))
            elif op == 'scope':
                body, _ = self.block(args[1], env.copy(), modes.copy(), abstract, returns)
                node = replace(node, args=(args[0], body))
            elif op == 'if':
                condition = self.any(args[0], env, modes, abstract, returns)
                branches = []
                for branch in args[1:]:
                    body, yields = self.block(branch, env.copy(), modes.copy(), abstract, returns)
                    branches.append(body)
                    tails.extend(yields)
                node = replace(node, args=(condition, *branches))
            elif op in ('loop', 'while'):
                body, yields = self.block(args[0], env.copy(), modes.copy(), abstract, returns)
                if value_context:
                    tails.extend(yields)
                node = replace(node, args=(body,))
            elif op == 'match':
                subject, arms = args
                if self.abstract_type(env.get(subject)):
                    self.fail('les variantes ne sont pas garanties par une feature')
                rewritten = []
                for typ, arm, fields, body in arms:
                    arm_env, arm_modes = env.copy(), modes.copy()
                    layout = dict(self.enums.get(typ, {}).get(arm, ()))
                    for field, name in fields:
                        field_type = layout.get(field)
                        cap = reference_type(field_type) if field_type else None
                        arm_env[name] = cap[1] if cap else field_type
                        arm_modes[name] = cap[0] if cap else 'scalar'
                    new_body, yields = self.block(body, arm_env, arm_modes, abstract, returns)
                    rewritten.append((typ, arm, fields, new_body))
                    tails.extend(yields)
                node = replace(node, args=(subject, rewritten))
            elif op in ('fn', 'async_fn', 'feature', 'impl', 'struct', 'enum'):
                self.fail('une déclaration de type ou fonction doit être au niveau du programme')
            else:
                node = replace(node, args=tuple(self.any(x, env, modes, abstract, returns) for x in args))
            output.append(node)
        return output, tails


def resolve_features(nodes, enums, error):
    if not any(node.op == 'feature' or node.type_contract for node in nodes):
        return nodes
    return FeatureResolver(nodes, enums, error).run()
