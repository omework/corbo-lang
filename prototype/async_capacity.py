"""Conservative state-pool bounds from task-holding storage and creation edges.

Counts deliberately overestimate aliases and sequential reuse. Every supported
live task has an owning task/handle slot in synchronous storage or in another
async frame. Recursive creation edges need an explicit physical bound to cut
the dependency cycle; no fixed fallback capacity stands in for that bound.
"""


def creation_graph(definitions, synchronous=None):
    synchronous = synchronous or {}
    def calls(value, visiting=frozenset()):
        if hasattr(value, 'args'):
            yield from calls(value.args, visiting)
        elif isinstance(value, (tuple, list)):
            if value and value[0] == 'call' and len(value) == 3:
                name = value[1]
                if name in definitions:
                    yield name
                elif name in synchronous and name not in visiting:
                    yield from calls(synchronous[name].args[3], visiting | {name})
            if value and value[0] == 'method_call' and len(value) == 4:
                # Receiver resolution belongs to the type checker. Include
                # every possible concrete method here so a local call cannot
                # hide task creation from the capacity graph.
                for name in synchronous:
                    if name.endswith('.' + value[2]) and name not in visiting:
                        yield from calls(synchronous[name].args[3], visiting | {name})
            for item in value:
                yield from calls(item, visiting)
    return {name: set(calls(node.args[3])) for name, node in definitions.items()}


def resolve_order(graph, explicit):
    remaining = set(graph) - explicit.keys()
    order = []
    while remaining:
        ready = sorted(name for name in remaining
                       if not any(name in graph[parent] for parent in remaining))
        if not ready:
            break
        order.extend(ready)
        remaining.difference_update(ready)
    return order, remaining


def configure(definitions, entries, error, synchronous=None):
    graph = creation_graph(definitions, synchronous)
    def public_name(name):
        return name.split('$feature', 1)[0].split('$closure', 1)[0]

    public = {public_name(name) for name in definitions}
    specified = {}
    for name, capacity, line in entries:
        if name in specified:
            raise error(f"ligne {line}: capacité async dupliquée pour '{name}'")
        if name not in public:
            raise error(f"ligne {line}: pool async inconnu '{name}'")
        specified[name] = capacity
    explicit = {name: specified[public_name(name)] for name in definitions
                if public_name(name) in specified}
    _, missing = resolve_order(graph, explicit)
    if missing:
        names = sorted({public_name(name) for name in missing})
        details = '\n'.join(f"- {name} : cycle de création d'états ou dépendance sur ce cycle" for name in names)
        raise error('async_pool_sizes requis : borne statique non établie pour les pools suivants\n' + details)
    return graph, explicit


def capacities(graph, explicit, synchronous_slots, frame_slots, error):
    order, missing = resolve_order(graph, explicit)
    if missing:
        raise error('invariant interne : capacités async non résolues')
    result = dict(explicit)
    for name in order:
        bound = synchronous_slots.get(name, 0)
        for parent, children in graph.items():
            if name in children:
                bound += result[parent] * frame_slots[parent]
        # Zero-instance programs still need a legal C array for the emitted
        # unused factory. One slot is also a valid conservative upper bound.
        result[name] = max(1, bound)
    oversized = sorted(name for name, size in result.items() if size > (1 << 31) - 1)
    if oversized:
        raise error('async_pool_sizes requis : borne conservative trop grande pour le prototype : '
                    + ', '.join(oversized))
    return result
