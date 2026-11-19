"""Lower reusable closure expressions to ordinary structures and methods."""
from copy import deepcopy
from dataclasses import replace

from async_lowering import branch_control_exit
from native_threads import Local, NativeBlocks
from numeric_elaboration import Elaborator, element_type, pointee
from numeric_core import FORMATS, numeric_type
from structure_views import scalar_field_mode
from value_moves import ValueMoves


class ClosureElaborator(Elaborator):
    def __init__(self, nodes, node_type, error):
        super().__init__(nodes, error)
        self.Node = node_type
        self.moves = ValueMoves(nodes, node_type, callable_bindings=True)
        self.declarations = [node for node in nodes if node.op in ('struct', 'enum', 'impl')]
        self.generated = []
        self.closure_methods = {}
        self.templates = {name: function for name, function in self.functions.items()
                          if any(typ.startswith('closure(') for _, _, typ in function.args[1])}
        self.specializations = {}
        self.active = set()

    def run(self, nodes):
        nodes[:] = [node for node in nodes if not (
            node.op in ('fn', 'async_fn') and node.args[0] in self.templates)]
        self.functions = {name: function for name, function in self.functions.items()
                          if name not in self.templates}
        super().run(nodes)
        for name, function in self.templates.items():
            if not any(key[0] == name for key in self.specializations):
                self.check_unused_function(name, function)
        nodes.extend(self.generated)

    def check_unused_function(self, name, function):
        """Check callable interfaces using a synthetic implementation."""
        env = {}
        arguments = []
        for index, parameter in enumerate(function.args[1]):
            pname = f'\0closure_input{index}'
            typ = self.parameter_type(function, parameter)
            parameter_name, mode, declared = parameter
            argument = ('name', pname)
            if declared.startswith('closure('):
                inputs, _, output = declared[len('closure('):].partition(')->')
                types = inputs.split(',') if inputs else []
                parameters = tuple((f'\0argument{i}', item, False) for i, item in enumerate(types))
                captures = {}
                choices = []
                moving = False
                if output.startswith('&'):
                    choices = [('name', pname) for pname, item, _ in parameters if item == output]
                    captured = '\0closure_borrowed_result'
                    mutable_receiver = mode == 'mut' or (
                        mode == 'scalar' and parameter_name in function.mutable_parameters)
                    target = output[5:]
                    if not output.startswith('&mut '):
                        captures[captured] = output
                        choices.append(('name', captured))
                    elif mutable_receiver and (numeric_type(target) is not None
                                                or target in self.structures or target in self.enums):
                        captures[captured] = output
                        choices.append(('reborrow', captured, 'mut'))
                        moving = True
                    if not choices:
                        self.fail(function.line, f"prototype : '{name}' exige un appel avec une closure concrète")
                    result = choices.pop()
                elif output == 'Void':
                    result = None
                elif output == 'bool':
                    result = ('bool', False)
                elif number := numeric_type(output):
                    result = ('numeric_decimal', '0.') if FORMATS[number].precision else ('numeric_integer', 0)
                elif output in self.structures and all(
                        field == 'bool' or numeric_type(field)
                        for field in self.structures[output].values()):
                    fields = [(name, ('bool', False) if field == 'bool' else
                               ('numeric_decimal', '0.') if FORMATS[numeric_type(field)].precision else
                               ('numeric_integer', 0))
                              for name, field in self.structures[output].items()]
                    result = ('new_enum', None, output, '', fields)
                else:
                    self.fail(function.line, f"prototype : '{name}' exige un appel avec une closure concrète")
                body = []
                for choice_index, candidate in enumerate(choices):
                    selector = f'\0closure_choice{choice_index}'
                    captures[selector] = 'bool'
                    branch = self.Node('return', (candidate,), function.line)
                    body.append(self.Node('if', (('name', selector), [branch], []), function.line))
                if result is not None:
                    body.append(self.Node('return', (result,), function.line))
                literal = ('closure_literal', moving, parameters, output, body, function.line)
                _, typ = self.make_closure(literal, captures)
                if mode in ('ref', 'mut'):
                    argument = (mode, pname)
            env[pname] = typ
            arguments.append(argument)
        self.specialize_call(name, arguments, env, function.line)

    def make_closure(self, expression, env):
        _, moving, parameters, declared, body, line = expression
        names = {name for name, _, _ in parameters}
        if len(names) != len(parameters):
            self.fail(line, 'paramètre de closure dupliqué')
        outer = {name: (None, typ) for name, typ in env.items() if name not in names}
        captures = {}
        self.moves.block(deepcopy(body), outer, captures=captures)
        nominal = f'__crust_closure${len(self.closure_methods)}'
        # Reserve the name before elaborating a nested closure.
        self.closure_methods[nominal] = None
        receiver = '\0closure'
        fields, initializers, aliases, local = [], [], [], {}
        mutable_receiver = False
        for name in captures:
            typ = env[name]
            if typ is None:
                self.fail(line, f"type de capture indéterminé pour '{name}'")
            scalar = scalar_field_mode(typ) is not None
            shared = typ.startswith('&') and not typ.startswith('&mut ')
            mutable_reference = typ.startswith('&mut ') and (numeric_type(typ[5:]) is not None
                                or typ[5:] in self.structures or typ[5:] in self.enums)
            contained = typ in self.structures or typ in self.enums
            owned = typ.startswith('A<') or contained
            if (owned or mutable_reference) and not moving:
                self.fail(line, f"la capture non Copy de '{name}' exige move")
            if not scalar and not shared and not owned and not mutable_reference:
                if not moving:
                    self.fail(line, f"la capture non Copy de '{name}' exige move")
                self.fail(line, f"prototype : capture propriétaire ou mutable de '{name}' non raccordée")
            fields.append((name, f'A<{typ}>' if contained else typ))
            value = (('move', name, 'closure_capture') if moving and scalar
                     else ('move', name) if owned else ('name', name))
            initializers.append((name, value))
            place = ('field', receiver, name)
            captured_type = (typ[5:] if mutable_reference else typ if contained
                             else typ[2:-1] if owned else None)
            exclusive = captured_type is not None and self.writes_capture(body, name, captured_type)
            mutable_receiver |= exclusive
            alias = (('mut_expr', ('field_deref', place)) if exclusive else
                     ('ref_expr', ('field_deref', place)) if owned else place)
            aliases.append(self.Node('var', (name, alias), line, mutable=exclusive))
            local[name] = (('&mut ' if exclusive else '&') + captured_type if owned
                           else '&' + typ[5:] if mutable_reference and not exclusive else typ)

        layout = self.Node('struct', (nominal, [('', fields)]), line)
        self.structures[nominal] = dict(fields)
        local.update({name: typ for name, typ, _ in parameters})
        body = list(body)
        if body and body[-1].op == 'if_yield':
            body[-1] = replace(body[-1], op='return')
        self.block(body, local, return_type=declared)
        inference = NativeBlocks([*self.declarations, *self.generated, *self.functions.values()],
                                 self.Node, self.error)
        results = []
        body, _ = inference.block(body, {name: self.local_type(typ) for name, typ in local.items()}, results)
        if not branch_control_exit(body):
            results.append(('void', 'Void'))
        result = inference.common(results)
        if result is None:
            self.fail(line, 'les chemins de retour de la closure doivent produire un même type')
        if result == ('scalar', 'Bool'):
            result = ('bool', 'bool')
        if declared is not None:
            wanted = self.signature_type(declared)
            if self.type_key(wanted) != self.type_key(result):
                self.fail(line, f'le résultat de la closure doit être de type {declared}')
            result = wanted
        args = [(receiver, 'mut' if mutable_receiver else 'ref', nominal)]
        args.extend((name, *self.signature_type(typ)) for name, typ, _ in parameters)
        method = self.Node('fn', ('invoke', args, result, [*aliases, *body]), line,
                           mutable_parameters=frozenset(name for name, _, mutable in parameters if mutable),
                           handle_parameters=frozenset(name for name, typ, _ in parameters if typ.startswith('A<')),
                           handle_result=bool(declared and declared.startswith('A<')))
        implementation = replace(method, args=(f'{nominal}.invoke', *method.args[1:]))
        self.generated.extend((layout, implementation))
        self.methods[nominal, 'invoke'] = method
        self.closure_methods[nominal] = method
        return ('new_enum', None, nominal, '', initializers), nominal

    def writes_capture(self, tree, name, typ):
        def place_type(place, aliases):
            op = place[0]
            if op == 'name':
                return aliases.get(place[1])
            if op == 'deref':
                return pointee(aliases.get(place[1]))
            if op == 'field' and place[1] in aliases:
                return self.field_type(aliases[place[1]], place[2])
            if op in ('field_deref', 'array_deref_slot'):
                declared = place_type(place[1], aliases)
                return pointee(declared)
            if op == 'array_index':
                declared = place_type(place[1], aliases)
                return element_type(pointee(declared) or declared)
            return None

        def update_alias(statement, aliases):
            if statement.op not in ('var', 'assign'):
                return
            target, initializer = statement.args
            declared = alias_type(initializer, aliases)
            if declared is None:
                aliases.pop(target, None)
            else:
                aliases[target] = declared

        def arm_aliases(match, enum, variant, fields, aliases):
            local = aliases.copy()
            captures_match_subject = isinstance(match.args[0], str) and match.args[0] in aliases
            declared = self.enums.get(enum, {}).get(variant, {})
            for field, alias in fields:
                field_type = declared.get(field)
                if (captures_match_subject and field_type
                        and field_type.startswith(('&mut ', 'A<'))):
                    local[alias] = field_type
                else:
                    local.pop(alias, None)
            return local

        def tail_alias(body, aliases):
            if not isinstance(body, list):
                return alias_type(body, aliases)
            if len(body) == 1 and body[0].op == 'scope' and body[0].region_limit is not None:
                body = body[0].args[1]
            result = []
            scan(body, aliases, tail=result)
            return result[0] if result else None

        def call_signature(expression, aliases):
            if expression[0] == 'method_call':
                _, receiver, name, arguments = expression
                declared = place_type(receiver, aliases)
                return self.methods.get((pointee(declared) or declared, name)), (receiver, *arguments)
            _, name, arguments = expression
            if name in aliases:
                declared = aliases[name]
                return (self.closure_methods.get(pointee(declared) or declared),
                        (('name', name), *arguments))
            return self.functions.get(name) or self.templates.get(name), arguments

        def alias_type(expression, aliases):
            if expression is None:
                return None
            op = expression[0]
            if op in ('name', 'move', 'down'):
                return aliases.get(expression[1])
            if op in ('transfer', 'array_transfer', 'new_transfer'):
                return alias_type(expression[1], aliases)
            if op in ('field', 'array_index'):
                projected = place_type(expression, aliases)
                if projected and projected.startswith(('&', 'A<')):
                    return projected
            if op in ('ref', 'mut', 'reborrow'):
                source = aliases.get(expression[1])
                if source:
                    mutable = op == 'mut' or (op == 'reborrow' and expression[2] == 'mut')
                    return ('&mut ' if mutable else '&') + (pointee(source) or source)
            if op in ('ref_expr', 'mut_expr'):
                source = place_type(expression[1], aliases)
                if source:
                    return ('&mut ' if op == 'mut_expr' else '&') + source
            if op in ('call', 'method_call'):
                function, arguments = call_signature(expression, aliases)
                if function:
                    mode, result = function.args[2]
                    reference_modes = ('ref', 'mut', 'array_ref', 'array_mut')
                    if mode in reference_modes and any(
                            parameter_mode in reference_modes and alias_type(argument, aliases)
                            for argument, (_, parameter_mode, _) in zip(arguments, function.args[1])):
                        return ('&mut ' if mode in ('mut', 'array_mut') else '&') + result
            if op == 'if_expr':
                return next((typ for arm in expression[2:] if (typ := tail_alias(arm, aliases))), None)
            if op in ('scope', 'capture_scope', 'value_match'):
                return tail_alias(expression[1] if op == 'value_match' else expression[2], aliases)
            if op == 'match_expr':
                match = expression[1]
                return next((typ for enum, variant, fields, body in match.args[1]
                             if (typ := tail_alias(body, arm_aliases(match, enum, variant, fields, aliases)))), None)
            if op == 'loop_expr':
                return scan_loop(expression[1].args[0], aliases)[2]
            return None

        def restore_shadowed(state, incoming, shadowed):
            for alias in shadowed:
                if alias in incoming:
                    state[alias] = incoming[alias]
                else:
                    state.pop(alias, None)
            return state

        def merge_aliases(states):
            return {alias: declared for state in states for alias, declared in state.items()}

        def scan_loop(body, incoming):
            head = incoming.copy()
            while True:
                edges = {'break': [], 'continue': []}
                writes, outgoing = scan(body, head, edges)
                if writes:
                    return True, incoming, None
                backedges = [state for state, _ in edges['continue']]
                if not branch_control_exit(body):
                    backedges.append(outgoing)
                widened = merge_aliases((*backedges, head))
                if widened == head:
                    breaks = edges['break']
                    outgoing = merge_aliases(state for state, _ in breaks) if breaks else incoming
                    result = next((declared for _, declared in breaks if declared is not None), None)
                    return False, outgoing, result
                head = widened

        def scan(body, aliases, exits=None, tail=None):
            local = aliases.copy()
            shadowed = set()
            edges = {'break': [], 'continue': []}
            for statement in body:
                op, args = statement.op, statement.args
                if tail is not None and op in ('if_yield', '<-', 'match_yield'):
                    if op == 'if_yield':
                        tail.append(alias_type(args[0], local))
                        break
                    if op == 'match_yield' or not statement.terminated:
                        tail.append(local.get(args[0]))
                        break
                branches = None
                if op in ('scope', 'capture_scope'):
                    branches = [(args[1], local, ())]
                elif op == 'if':
                    if visit(args[0], local):
                        return True, local
                    branches = [(arm, local, ()) for arm in args[1:]]
                elif op == 'match':
                    holder, arms = args
                    if statement.mutable and isinstance(holder, str) and holder in local:
                        return True, local
                    branches = [(body, arm_aliases(statement, enum, variant, fields, local),
                                 tuple(alias for _, alias in fields))
                                for enum, variant, fields, body in arms]
                if branches is not None:
                    continuations = []
                    for arm, incoming, patterns in branches:
                        arm_edges = {'break': [], 'continue': []}
                        writes, outgoing = scan(arm, incoming, arm_edges)
                        if writes:
                            return True, local
                        for edge, states in arm_edges.items():
                            for state, declared in states:
                                restore_shadowed(state, local, patterns)
                                edges[edge].append((restore_shadowed(state, aliases, shadowed), declared))
                        if not branch_control_exit(arm):
                            continuations.append(restore_shadowed(outgoing, local, patterns))
                    if not continuations:
                        break
                    local = merge_aliases(continuations)
                elif op in ('loop', 'while'):
                    writes, local, _ = scan_loop(args[0], local)
                    if writes:
                        return True, local
                elif visit(statement, local):
                    return True, local
                if op in ('break', 'continue', 'while_check'):
                    declared = alias_type(args[0], local) if op == 'break' else None
                    state = restore_shadowed(local.copy(), aliases, shadowed)
                    edges['break' if op == 'while_check' else op].append((state, declared))
                if op == 'var':
                    shadowed.add(args[0])
                update_alias(statement, local)
                if branch_control_exit([statement]):
                    break
            if exits is not None:
                for edge, states in edges.items():
                    exits[edge].extend(states)
            return False, restore_shadowed(local, aliases, shadowed)

        def passes_capture_mutably(arguments, parameters, aliases):
            return any(mode in ('mut', 'array_mut')
                       and (place_type(argument, aliases) or alias_type(argument, aliases))
                       for argument, (_, mode, _) in zip(arguments, parameters))

        def visit(value, aliases):
            if isinstance(value, self.Node):
                if value.op in ('loop', 'while'):
                    return scan_loop(value.args[0], aliases)[0]
                if value.op == 'match':
                    holder = value.args[0]
                    if value.mutable and isinstance(holder, str) and holder in aliases:
                        return True
                    return any(visit(body, arm_aliases(value, enum, variant, fields, aliases))
                               for enum, variant, fields, body in value.args[1])
                if value.op in ('field_store', 'array_deref_store', 'array_store'):
                    if place_type(value.args[0], aliases) is not None:
                        return True
                return visit(value.args, aliases)
            if isinstance(value, list) and all(isinstance(item, self.Node) for item in value):
                return scan(value, aliases)[0]
            if not isinstance(value, (list, tuple)) or not value:
                return False
            op = value[0]
            if op == 'mut' and value[1] in aliases:
                return True
            if op == 'reborrow' and value[1] in aliases and value[2] == 'mut':
                return True
            if op in ('mut_expr', 'array_numeric_compound', 'array_split', 'array_mut_ref',
                      'array_replace', 'array_buffered_replace', 'array_swap') and place_type(value[1], aliases) is not None:
                return True
            if (op == 'method_call' and value[2] in ('mut_ref', 'mut_vref', 'set')
                    and place_type(value[1], aliases) is not None):
                return True
            if op == 'array_hashmap_method' and value[1] in ('get_mut', 'insert', 'try_insert', 'remove'):
                if place_type(value[2], aliases) is not None:
                    return True
            if op in ('call', 'method_call'):
                function, arguments = call_signature(value, aliases)
                if function and passes_capture_mutably(arguments, function.args[1], aliases):
                    return True
            return any(visit(item, aliases) for item in value)

        return visit(tree, {name: typ})

    def signature_type(self, typ):
        if typ in self.structures or typ in self.enums:
            return 'owned', typ
        mode, content = NativeBlocks.declared(typ)
        if typ == 'bool':
            return 'bool', 'bool'
        return mode, content

    @staticmethod
    def type_key(signature):
        mode, typ = signature
        return 'bool' if typ in ('Bool', 'bool') else (mode, numeric_type(typ) or typ)

    def local_type(self, typ):
        return Local(self.signature_type(typ))

    def call(self, expression, env, line):
        if expression[0] == 'call':
            _, name, arguments = expression
            typ = env.get(name)
            if method := self.closure_methods.get(pointee(typ) or typ):
                if len(arguments) != len(method.args[1]) - 1:
                    self.fail(line, 'nombre d’arguments incompatible avec la signature de la closure')
                return super().call(('method_call', ('name', name), 'invoke', arguments), env, line)
            if name in self.templates and name not in env:
                return self.specialize_call(name, arguments, env, line)
        return super().call(expression, env, line)

    def specialize_call(self, name, arguments, env, line):
        function = self.templates[name]
        _, parameters, result, body = function.args
        if len(arguments) != len(parameters):
            self.fail(line, 'nombre d’arguments incompatible avec la signature de la fonction')
        actual, concrete = [], []
        for argument, parameter in zip(arguments, parameters):
            pname, mode, expected = parameter
            value, typ = self.expr(argument, env, line, self.parameter_type(function, parameter))
            if expected.startswith('closure('):
                nominal = pointee(typ) if mode in ('ref', 'mut') else typ
                method = self.closure_methods.get(nominal)
                prefix = {'ref': '&', 'mut': '&mut '}.get(mode, '')
                if method is None or typ != prefix + nominal or self.callable_type(method) != expected:
                    self.fail(line, f"argument '{pname}' : signature {expected} requise")
                concrete.append((pname, 'owned' if mode == 'scalar' else mode, nominal))
            else:
                concrete.append(parameter)
            actual.append(value)
        key = name, tuple(concrete)
        if key in self.active:
            self.fail(line, 'prototype : spécialisation récursive de closure non raccordée')
        if key not in self.specializations:
            specialized = f'{name}$closure{len(self.specializations)}'
            self.specializations[key] = specialized
            node = replace(function, args=(specialized, concrete, result, deepcopy(body)))
            self.functions[specialized] = node
            self.active.add(key)
            previous = self.current_function
            self.current_function = specialized
            try:
                local = {param[0]: self.parameter_type(node, param) for param in concrete}
                self.block(node.args[3], local, return_type=self.declared_result_type(node))
            finally:
                self.current_function = previous
                self.active.remove(key)
            self.generated.append(node)
        specialized = self.specializations[key]
        return ('call', specialized, actual), self.result_type(self.functions[specialized])

    def callable_type(self, method):
        inputs = ','.join(self.parameter_type(method, param) for param in method.args[1][1:])
        return f'closure({inputs})->{self.declared_result_type(method)}'

    def anchor(self, expression, env):
        if expression[0] == 'call':
            name = expression[1]
            typ = env.get(name)
            if method := self.closure_methods.get(pointee(typ) or typ):
                return self.result_type(method)
            if name in self.templates:
                return self.result_type(self.templates[name])
        return super().anchor(expression, env)

    def expr(self, expression, env, line, expected=None):
        if expression[0] == 'closure_literal':
            return self.make_closure(expression, env)
        if expression[0] == 'closure_apply':
            _, literal, arguments = expression
            value, nominal = self.make_closure(literal, env)
            name = f'{nominal}$immediate'
            result, typ = self.call(('call', name, arguments), env | {name: nominal}, line)
            body = [self.Node('var', (name, value), line), self.Node('if_yield', (result,), line)]
            return ('scope', 'appel immédiat de closure', body), typ
        return super().expr(expression, env, line, expected)
