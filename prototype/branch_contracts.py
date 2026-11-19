"""Follow returned branch identities through launcher bodies."""

HANDLE, TASK, RESULT, TASK_RESULT, HANDLE_RESULT = range(5)


def returned_launches(body, parameters, resolve_call, *, return_slot=HANDLE):
    unknown = (None,) * 5

    def unwrap(value):
        while value and value[0] in ('transfer', 'array_transfer'):
            value = value[1]
        return value

    def has_untracked_flow(value):
        if hasattr(value, 'op'):
            return value.op in ('assign', 'return', 'break', 'continue') or has_untracked_flow(value.args)
        if isinstance(value, (tuple, list)):
            return any(has_untracked_flow(item) for item in value)
        return False

    def completed_handle(names):
        if names is None:
            return None
        completions = [resolve_call(name, TASK_RESULT, lambda *_: None)
                       for name in names if isinstance(name, str)]
        if len(completions) != len(names) or any(completion is None for completion in completions):
            return None
        return frozenset().union(*completions)

    def origin(value, bindings, *, slot=HANDLE):
        value = unwrap(value)
        if not value:
            return None
        if value[0] == 'loop_expr':
            result = loop_paths(value[1].args[0], bindings, break_slot=slot)
            if result is None:
                return None
            returns, _, jumps = result
            exits = jumps['break']
            if returns or not exits or any(state != bindings or origins is None
                                            for state, origins in exits):
                return None
            return frozenset().union(*(origins for _, origins in exits))
        if has_untracked_flow(value):
            return None
        if value[0] in ('name', 'move', 'down'):
            return bindings.get(value[1], unknown)[slot]
        if slot == RESULT and value[0] in ('await', 'task_join', 'task_join_value'):
            handle = ('name', value[1]) if value[0] == 'task_join' else value[1]
            completion = origin(handle, bindings, slot=HANDLE_RESULT)
            return completion if completion is not None else completed_handle(origin(handle, bindings))
        if slot == HANDLE and value[0] == 'utf8_value':
            return origin(value[1], bindings, slot=RESULT)
        if value[0] == 'call':
            if slot == RESULT:
                return None
            _, name, arguments = value
            return resolve_call(name, slot, lambda index, part: (
                origin(arguments[index], bindings, slot=part) if index < len(arguments) else None))
        if value[0] == 'await' and slot == HANDLE:
            task = value[1]
            completion = origin(task, bindings, slot=TASK_RESULT)
            return completion if completion is not None else completed_handle(origin(task, bindings, slot=TASK))
        if value[0] == 'native_thread':
            return frozenset({None}) if slot == HANDLE else None
        if value[0] == 'task_spawn':
            if slot == HANDLE:
                return origin(value[1], bindings, slot=TASK)
            if slot == HANDLE_RESULT:
                return origin(value[1], bindings, slot=TASK_RESULT)
            return None
        if value[0] in ('if_expr', 'scope', 'capture_scope', 'match_expr', 'value_match'):
            if value[0] == 'match_expr':
                arms = [(arm, {name for _, name in fields})
                        for _, _, fields, arm in value[1].args[1]]
            else:
                blocks = (value[2:] if value[0] == 'if_expr' else
                          (value[2],) if value[0] in ('scope', 'capture_scope') else (value[1],))
                arms = [(block, set()) for block in blocks]
            alternatives = []
            for arm, hidden in arms:
                visible = {name: bound for name, bound in bindings.items() if name not in hidden}
                if isinstance(arm, tuple):
                    alternatives.append(origin(arm, visible, slot=slot))
                    continue
                if not arm or arm[-1].op not in ('if_yield', '<-'):
                    return None
                prefix = walk(arm[:-1], visible)
                if prefix is None or prefix[0] or prefix[1] is None or any(prefix[2].values()):
                    return None
                # The expression summary returns a value origin only. Do
                # not erase assignments to the surrounding environment.
                if any(prefix[1].get(name) != previous for name, previous in visible.items()):
                    return None
                tail = arm[-1].args[0]
                alternatives.append(origin(('name', tail) if arm[-1].op == '<-' else tail,
                                           prefix[1], slot=slot))
            if alternatives and all(isinstance(item, frozenset) for item in alternatives):
                return frozenset().union(*alternatives)
        return None

    def merge_bindings(paths, names):
        merged = {}
        for name in names:
            values = [path.get(name, unknown) for path in paths]
            merged[name] = tuple(frozenset().union(*alternatives)
                                 if all(item is not None for item in alternatives) else None
                                 for alternatives in zip(*values))
        return merged

    def loop_paths(body, bindings, *, break_slot=HANDLE):
        head = bindings.copy()
        while True:
            result = walk(body, head, child_scope=True, in_loop=True, break_slot=break_slot)
            if result is None:
                return None
            _, tail, jumps = result
            back = [state for state, _ in jumps['continue']]
            if tail is not None:
                back.append(tail)
            next_head = merge_bindings([head, *back], bindings)
            if next_head == head:
                return result
            head = next_head

    def statements(nodes):
        for node in nodes:
            if node.op == 'utf8_match_lowered':
                yield from statements(node.args)
            else:
                yield node

    def walk(nodes, outer, *, child_scope=False, in_loop=False, break_slot=HANDLE):
        bindings, returns, shadowed = outer.copy(), set(), {}
        exits = {'break': [], 'continue': []}

        def project(state):
            if not child_scope:
                return state.copy()
            return {name: shadowed.get(name, state[name]) for name in outer}

        for node in statements(nodes):
            if node.op == 'return':
                launches = origin(node.args[0], bindings, slot=return_slot)
                if not isinstance(launches, frozenset):
                    return None
                return returns | launches, None, exits
            if node.op in exits:
                if not in_loop or has_untracked_flow(node.args):
                    return None
                value = (origin(node.args[0], bindings, slot=break_slot)
                         if node.op == 'break' and node.args else None)
                exits[node.op].append((project(bindings), value))
                return returns, None, exits
            if node.op == 'while_check':
                if not in_loop or has_untracked_flow(node.args):
                    return None
                exits['break'].append((project(bindings), None))
                continue
            if node.op in ('var', 'assign'):
                name, value = node.args
                if child_scope and node.op == 'var' and name in outer:
                    shadowed.setdefault(name, bindings[name])
                value = unwrap(value)
                if value[0] != 'loop_expr' and has_untracked_flow(value):
                    return None
                known = tuple(origin(value, bindings, slot=slot) for slot in range(len(unknown)))
                if value[0] == 'loop_expr' and known == unknown:
                    return None
                bindings[name] = known
            elif node.op == '->':
                # Importing into the child preserves the branch identity.
                # Move legality and reuse of the original name are checked
                # by the ordinary body verifier.
                if node.args[0] not in bindings:
                    return None
            elif node.op in ('if', 'scope', 'capture_scope', 'match'):
                if node.op == 'if' and has_untracked_flow(node.args[0]):
                    return None
                if node.op == 'match':
                    children = [(arm, {name for _, name in fields})
                                for _, _, fields, arm in node.args[1]]
                else:
                    blocks = node.args[1:] if node.op == 'if' else (node.args[1],)
                    children = [(block, set()) for block in blocks]
                paths = []
                for child, hidden in children:
                    visible = {name: value for name, value in bindings.items() if name not in hidden}
                    result = walk(child, visible, child_scope=True, in_loop=in_loop,
                                  break_slot=break_slot)
                    if result is None:
                        return None
                    sources, state, jumps = result
                    returns.update(sources)
                    preserved = {name: bindings[name] for name in hidden if name in bindings}
                    for jump, states in jumps.items():
                        exits[jump].extend((project(path | preserved), value) for path, value in states)
                    if state is not None:
                        paths.append(state | preserved)
                if not paths:
                    return returns, None, exits
                bindings = merge_bindings(paths, bindings)
            elif node.op in ('loop', 'while'):
                result = loop_paths(node.args[0], bindings)
                if result is None:
                    return None
                sources, _, jumps = result
                returns.update(sources)
                if not jumps['break']:
                    return returns, None, exits
                bindings = merge_bindings([state for state, _ in jumps['break']], bindings)
            elif node.op not in ('call', 'drop_value', 'print', 'yield') or has_untracked_flow(node.args):
                return None
        return returns, project(bindings), exits

    def parameter_origin(index, mode, typ, slot):
        if mode == 'task' and slot == TASK:
            return frozenset({typ})
        if (mode == 'task' and slot == TASK_RESULT
                or mode in ('execution', 'async_execution') and slot in (HANDLE, HANDLE_RESULT)):
            return frozenset({('parameter', index, slot)})
        return None

    inputs = {name: tuple(parameter_origin(index, mode, typ, slot) for slot in range(len(unknown)))
              for index, (name, mode, typ) in enumerate(parameters)}
    result = walk(body, inputs)
    return frozenset(result[0]) if result and result[0] and result[1] is None else None
