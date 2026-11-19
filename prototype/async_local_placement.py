"""Find local constructors that supply a block result, using call contracts.

This is a placement plan, not a validity checker. Unknown producers are left
to the normal lifetime/type checker; no target borrowed by a value is promoted.
"""

from array_syntax import INLINE_VECTOR_ELEMENTS


def result_constructors(expression, contracts, known_locals, *, assigned_to=None, returns=False,
                        async_functions=None):
    async_functions = async_functions or {}
    assignments = {name: [] for name in assigned_to or ()}
    returned = []
    def merge(values):
        if not values or any(value is None for value in values):
            return None
        if len({value[0] for value in values}) != 1:
            return None
        calls = {}
        for _, constructors in values:
            calls.update(constructors)
        return values[0][0], calls

    def evaluate(expr, env):
        if not expr:
            return None
        op = expr[0]
        if op == 'source' and expr[1] == 'pool' and expr[3] in INLINE_VECTOR_ELEMENTS:
            return ('inline_vector_pool', expr[3]), {}
        if op == 'new':
            source = env.get(expr[1])
            if source and isinstance(source[0], tuple) and source[0][0] == 'inline_vector_pool':
                return ('inline_vector', source[0][1]), {}
        if op == 'new_enum' and expr[1] is None:
            return expr[2], {id(expr): expr}
        if op == 'array_copy':
            if expr[1][0] == 'array_index':
                vector = evaluate(expr[1][1], env)
                if vector and isinstance(vector[0], tuple) and vector[0][0] == 'inline_vector':
                    return INLINE_VECTOR_ELEMENTS[vector[0][1]], {id(expr): expr}
            original = evaluate(expr[1], env)
            if original is not None and isinstance(original[0], str):
                return original[0], {id(expr): expr}
            return None
        if op == 'array_handle_option_pop':
            vector = evaluate(expr[1], env)
            if vector and isinstance(vector[0], tuple) and vector[0][0] == 'inline_vector':
                return INLINE_VECTOR_ELEMENTS[vector[0][1]], {id(expr): expr}
        if op in ('name', 'ref', 'mut', 'move', 'down'):
            return env.get(expr[1])
        if op in ('array_transfer', 'new_transfer', 'transfer'):
            return evaluate(expr[1], env)
        if op == 'task_select':
            branches = [evaluate(argument, env) for argument in expr[1]]
            if any(branch is None or not isinstance(branch[0], tuple) or branch[0][0] != 'task'
                   for branch in branches):
                return None
            selected = merge(branches)
            if selected is not None:
                return ('selection', selected[0][1]), selected[1]
            return None
        if op in ('task_spawn', 'await', 'task_join', 'task_join_value', 'utf8_value'):
            operand = ('name', expr[1]) if op == 'task_join' else expr[1]
            value = evaluate(operand, env)
            if value is None or not isinstance(value[0], tuple):
                return None
            kind, typ = value[0]
            if op == 'task_spawn' and kind == 'task':
                return ('execution', typ), value[1]
            if op in ('task_join', 'task_join_value', 'await') and kind == 'execution':
                return ('join', typ), value[1]
            if op == 'await' and kind in ('task', 'selection') or op == 'utf8_value' and kind == 'join':
                return typ, value[1]
            return None
        call_name, arguments = (expr[1], expr[2]) if op == 'call' else (None, ())
        if op == 'method_call':
            receiver = evaluate(expr[1], env)
            if (expr[2] == 'remove' and receiver and isinstance(receiver[0], tuple)
                    and receiver[0][0] == 'inline_vector'):
                return INLINE_VECTOR_ELEMENTS[receiver[0][1]], {id(expr): expr}
            receiver_type = receiver[0] if receiver is not None else None
            if isinstance(receiver_type, tuple) and receiver_type[0] == 'borrowed_receiver':
                receiver_type = receiver_type[1]
            if isinstance(receiver_type, str):
                call_name = receiver_type + '.' + expr[2]
                arguments = (expr[1], *expr[3])
        if call_name in async_functions:
            from async_result_storage import result_storage, pool_result_graph
            node = async_functions[call_name]
            effect = getattr(node, 'field_effect_summary', None)
            if effect and effect.complete and node.args[2][0] in ('owned', 'join_owned', 'join_nested'):
                candidates = effect.completion_result.candidates
                if candidates and all(candidate.kind == 'parameter' for candidate in candidates):
                    origin = merge([evaluate(arguments[candidate.parameter], env) for candidate in candidates])
                    if origin is not None:
                        shape = node.args[2][1]
                        for _ in range({'join_owned': 1, 'join_nested': 2}.get(node.args[2][0], 0)):
                            shape = 'join', shape
                        return ('task', shape), origin[1]
            if not node.result_storage:
                return None
            local_parameters = frozenset(index for index, argument in enumerate(arguments)
                                         if (value := evaluate(argument, env)) is not None
                                         and not isinstance(value[0], tuple))
            plan = result_storage(node, local_parameters)
            # Relocate only the fresh root. A complete graph contract retains
            # the separately pooled descendants at their original addresses.
            if plan.destination and not plan.mixed and (
                    plan.parameters == frozenset() or pool_result_graph(node) is not None):
                shape = node.args[2][1]
                for _ in range({'join_owned': 1, 'join_nested': 2}.get(node.args[2][0], 0)):
                    shape = 'join', shape
                return ('task', shape), {id(expr): expr}
            return None
        if call_name in contracts:
            summary = contracts[call_name].result
            if getattr(summary, 'mode', None) == 'task':
                from async_result_storage import needs_task_output
                def local_argument(index):
                    value = evaluate(arguments[index], env)
                    return value is not None and not isinstance(value[0], tuple)
                if needs_task_output(summary.task_result_sources, local_argument):
                    node = async_functions.get(summary.typ)
                    if node is not None:
                        return ('task', node.args[2][1]), {id(expr): expr}
                sources = summary.task_result_sources
                if sources and all(source.kind == 'allocation_parameter' for source in sources):
                    origin = merge([evaluate(arguments[source.index], env) for source in sources])
                    node = async_functions.get(summary.typ)
                    if origin is not None and node is not None:
                        shape = node.args[2][1]
                        for _ in range({'join_owned': 1, 'join_nested': 2}.get(node.args[2][0], 0)):
                            shape = 'join', shape
                        return ('task', shape), origin[1]
                return None
            candidates = []
            for candidate in summary.candidates:
                if candidate.kind == 'fresh' and candidate.source.kind == 'local_value':
                    candidates.append((summary.typ, {id(expr): expr}))
                elif candidate.kind == 'fresh' and candidate.source.kind == 'allocation_parameter':
                    origin = evaluate(arguments[candidate.source.index], env)
                    candidates.append((summary.typ, {id(expr): expr}) if origin else None)
                elif candidate.kind == 'parameter':
                    candidates.append(evaluate(arguments[candidate.parameter], env))
                elif candidate.kind == 'task_capture':
                    origin = evaluate(arguments[candidate.parameter], env)
                    if origin is not None and isinstance(origin[0], tuple) and origin[0][0] in ('task', 'execution'):
                        candidates.append((origin[0][1], origin[1]))
                    else:
                        candidates.append(None)
                else:
                    candidates.append(None)
            return merge(candidates)
        if op == 'scope':
            _, results = block(expr[2], env)
            return merge(results)
        if op == 'value_match':
            _, results = block(expr[1], env)
            return merge(results)
        if op == 'if_expr':
            results = []
            for branch in expr[2:]:
                if isinstance(branch, tuple):
                    results.append(evaluate(branch, env))
                else:
                    _, outputs = block(branch, env)
                    results.extend(outputs)
            return merge(results)
        if op == 'loop_expr':
            _, results = loop(expr[1].args[0], env, valued=True)
            return merge(results)
        return None

    def join_states(states, names):
        return {name: merge([state.get(name) for state in states]) for name in names}

    def loop(nodes, incoming, *, valued=False):
        # Constructors are AST identities: union reaches a finite fixed point.
        # None is unknown, never an empty set of possible producers.
        head = incoming.copy()
        while True:
            back, exits = [], []
            state, results = block(nodes, head, breaks=valued,
                                   loop_back=back, loop_exits=exits)
            if state is not None:
                back.append(state)
            updated = join_states([incoming, head, *back], incoming)
            if updated == head:
                return (join_states(exits, incoming) if exits else None), results
            head = updated

    def block(nodes, incoming, *, breaks=False, loop_back=None, loop_exits=None):
        env = incoming.copy()
        results = []
        for node in nodes:
            op, args = node.op, node.args
            if op in ('var', 'assign'):
                env[args[0]] = evaluate(args[1], env)
                if op == 'assign' and args[0] in assignments:
                    assignments[args[0]].append(env[args[0]])
            elif op == 'if':
                following = []
                for branch in args[1:]:
                    state, outputs = block(branch, env, breaks=breaks,
                                           loop_back=loop_back, loop_exits=loop_exits)
                    results.extend(outputs)
                    if state is not None:
                        following.append(state)
                if not following:
                    return None, results
                env = {name: merge([state.get(name) for state in following]) for name in env}
            elif op == '<-' and not node.terminated:
                results.append(env.get(args[0]))
                return None, results
            elif op == 'if_yield':
                results.append(evaluate(args[0], env))
                return None, results
            elif op == 'break':
                if breaks:
                    results.append(evaluate(args[0], env))
                if loop_exits is not None:
                    loop_exits.append(env.copy())
                return None, results
            elif op == 'continue':
                if loop_back is not None:
                    loop_back.append(env.copy())
                return None, results
            elif op == 'return':
                if returns:
                    returned.append(evaluate(args[0], env))
                return None, results
            elif op == 'while_check':
                if loop_exits is not None:
                    loop_exits.append(env.copy())
            elif op in ('loop', 'while'):
                state, _ = loop(args[0], env)
                if state is None:
                    return None, results
                env = state
            elif op == 'scope':
                state, outputs = block(args[1], env, breaks=breaks,
                                       loop_back=loop_back, loop_exits=loop_exits)
                results.extend(outputs)
                if state is None:
                    return None, results
                env = {name: state.get(name) for name in env}
        return env, results

    result = evaluate(expression, {name: (typ, {}) for name, typ in known_locals.items()})
    if returns:
        result = merge([*returned, *([result] if result is not None else [])])
    if assigned_to is not None:
        return {name: tuple(merged[1].values()) if (merged := merge(values)) is not None else ()
                for name, values in assignments.items()}
    return tuple(result[1].values()) if result is not None else ()
