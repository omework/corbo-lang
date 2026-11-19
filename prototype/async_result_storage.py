"""Storage of an owned async result, evaluated for a static instantiation."""
from owned_join_types import (
    OWNED_JOIN_TYPES,
)
from option_join_types import (
    OPTION_JOIN_TYPES,
)
from exchange_join_types import (
    EXCHANGE_JOIN_TYPES,
)
from dataclasses import dataclass

@dataclass(frozen=True)
class ResultStorage:
    destination: bool = False
    parameters: frozenset | None = None
    mixed: bool = False
    owned_fields: bool = False


def root_result_parameters(node, fallback):
    """Parameter sources of the root, excluding independently owned children."""
    effect = getattr(node, 'field_effect_summary', None)
    completed = effect.completion_result if effect and effect.complete else None
    if completed and completed.candidates and all(
            candidate.kind == 'parameter' or candidate.kind == 'fresh'
            and candidate.source.kind in ('local_value', 'allocation_parameter', 'source_parameter')
            for candidate in completed.candidates):
        return frozenset(candidate.parameter if candidate.kind == 'parameter' else candidate.source.index
            for candidate in completed.candidates
            if candidate.kind == 'parameter' or candidate.source.kind != 'local_value')
    return fallback


def may_need_destination(node, structures):
    effect = getattr(node, 'field_effect_summary', None)
    if node.args[2][0] not in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange') or node.args[2][1] not in structures or not effect or not effect.complete:
        return False
    return any(candidate.kind == 'fresh' and candidate.source.kind in ('local_value','allocation_parameter')
               for candidate in effect.completion_result.candidates)


def result_storage(node, local_parameters=frozenset()):
    effect = getattr(node, 'field_effect_summary', None)
    if not effect or not effect.complete or node.args[2][0] not in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange'):
        return ResultStorage()
    summary = effect.completion_result
    if not summary.candidates:
        return ResultStorage()
    kinds, parameters, destination, unknown = set(), set(), False, False
    for candidate in summary.candidates:
        if candidate.kind in ('parameter', 'vector_element', 'exchange_parameter'):
            parameters.add(candidate.parameter)
            kinds.add('local' if candidate.kind == 'parameter' and candidate.parameter in local_parameters else 'pool')
        elif candidate.kind == 'fresh':
            source = candidate.source
            if source.kind == 'local_value' or source.kind == 'allocation_parameter' and source.index in local_parameters:
                kinds.add('local'); destination = True
            elif source.kind in ('source_parameter','allocation_parameter'):
                kinds.add('pool'); parameters.add(source.index)
            else:
                unknown = True
        else:
            unknown = True
    graph = pool_result_graph(node) if summary.owned_fields else None
    if graph is not None:
        parameters.update(source.index for _, symbols in graph[1] for source in symbols)
    return ResultStorage(destination, None if unknown or summary.owned_fields and graph is None else frozenset(parameters),
                         len(kinds)>1, bool(summary.owned_fields))


def output_origin(source, typ):
    """A copy uses caller output storage for local values, its pool otherwise."""
    from results import SourceOrigin
    if source.kind in ('local_value', 'task_output'):
        return SourceOrigin('task_output', -1, element=typ)
    if source.kind in ('allocation_parameter', 'task_output_parameter'):
        return SourceOrigin('task_output_parameter', source.index, element=typ)
    return source


def task_result_origins(node, actuals):
    """Symbolic sources of the future result, distinct from captured inputs."""
    if not node.result_storage or node.field_effect_summary.completion_result.owned_fields:
        return None
    summary = node.field_effect_summary.completion_result
    sources = set()
    for candidate in summary.candidates:
        if candidate.kind == 'fresh' and candidate.source.kind == 'local_value':
            sources.add(output_origin(candidate.source, summary.typ))
        elif candidate.kind == 'fresh' and candidate.source.kind == 'allocation_parameter':
            actual = actuals[candidate.source.index]
            candidates = getattr(actual, 'candidates', ())
            if not candidates:
                return None
            sources.update(output_origin(item.storage(), summary.typ) for item in candidates)
        elif candidate.kind == 'fresh' and candidate.source.kind == 'source_parameter':
            sources.add(actuals[candidate.source.index])
        elif candidate.kind == 'parameter':
            sources.update(item.storage() for item in actuals[candidate.parameter].candidates)
        elif candidate.kind == 'vector_element':
            from results import vector_result_candidates
            from array_syntax import VECTOR_LAST_ITEM
            items = vector_result_candidates(actuals[candidate.parameter], candidate.item_index,
                last=candidate.item_index == VECTOR_LAST_ITEM, excluded=candidate.excluded_items,
                tail_offset=candidate.tail_offset)
            if items is None:
                return None
            sources.update(item.storage() for item in items)
        else:
            return None
    return frozenset(sources)


def needs_task_output(symbols, local_parameter):
    return any(symbol.kind == 'task_output' or symbol.kind == 'task_output_parameter'
               and local_parameter(symbol.index) for symbol in symbols)


def pool_result_graph(node, enums=None):
    """A returned root and its final owned fields, after any replacements.

    This is a contract projection, not a new lifetime or a placement decision.
    Local descendant sources remain unsupported and must not be promoted.
    """
    effect = getattr(node, 'field_effect_summary', None)
    if not effect or not effect.complete or node.args[2][0] not in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange'):
        return None
    summary = effect.completion_result
    from array_syntax import is_handle_vector
    if is_handle_vector(summary.typ):
        from results import SourceOrigin
        roots = frozenset(candidate.storage() if candidate.kind == 'parameter'
            else output_origin(candidate.source, summary.typ) for candidate in summary.candidates
            if candidate.kind == 'parameter' or candidate.kind == 'fresh')
        fields = {}
        def visit(value, path):
            fields[path] = fields.get(path, frozenset()) | frozenset(candidate.storage() for candidate in value.candidates)
            for key, child in value.owned_fields:
                visit(child, path + '/' + key)
        for value in summary.vector_values:
            visit(value, '[]')
        # Scalar payloads have no field graph. Their storage still belongs to
        # the returned vector and must survive the async state.
        items = set(fields.get('[]', ()))
        for candidate in summary.candidates:
            if candidate.kind == 'parameter':
                items.add(SourceOrigin('vector_element_parameter', candidate.parameter))
            for slot in candidate.vector_layout:
                items.update(item.storage() for item in slot)
            items.update(SourceOrigin('allocation_parameter', index) for index in candidate.vector_added_parameters)
            items.update(SourceOrigin('source_parameter', index) for index in candidate.vector_added_pools)
        fields['[]'] = frozenset(items)
        return roots, tuple(sorted(fields.items()))
    if (summary.mode == 'buffered_handle_exchange' or summary.mode in EXCHANGE_JOIN_TYPES) and len(summary.exchange_payloads) == 2:
        from results import SourceOrigin
        def storage(candidate):
            if candidate.kind == 'exchange_parameter':
                return SourceOrigin('allocation_field_parameter', candidate.parameter,
                                    ('ok', 'err')[candidate.item_index])
            return candidate.storage()
        arms = tuple((name, frozenset(storage(candidate) for candidate in candidates))
                     for name, candidates in zip(('ok', 'err'), summary.exchange_payloads))
        return frozenset().union(*(sources for _, sources in arms)), arms
    if (not summary.owned_fields and any(candidate.kind == 'vector_element' for candidate in summary.candidates)
            and all(candidate.kind in ('parameter', 'vector_element') or candidate.kind == 'fresh'
                    and candidate.source.kind == 'source_parameter' for candidate in summary.candidates)):
        return frozenset(candidate.storage() for candidate in summary.candidates), ()
    if summary.candidates and all(candidate.kind == 'owned_projection' for candidate in summary.candidates):
        from array_syntax import aggregate_owned_paths
        from results import SourceOrigin
        fields = tuple((path, frozenset(SourceOrigin('allocation_field_parameter',
            candidate.parameter, candidate.field_path + '/' + path) for candidate in summary.candidates))
            for path, _ in aggregate_owned_paths(enums or {}, summary.typ))
        return frozenset(candidate.storage() for candidate in summary.candidates), fields
    if not summary.owned_fields or not summary.candidates or any(
            candidate.kind != 'parameter' and (candidate.kind != 'fresh'
                or candidate.source.kind not in ('source_parameter', 'local_value'))
            for candidate in summary.candidates):
        return None
    from array_syntax import aggregate_owned_paths
    from results import SourceOrigin
    inherited = {}
    for candidate in summary.candidates:
        if candidate.kind == 'parameter':
            for path, _ in aggregate_owned_paths(enums or {}, summary.typ):
                inherited[path] = inherited.get(path, frozenset()) | frozenset({SourceOrigin(
                    'allocation_field_parameter', candidate.parameter, path)})
    fields = []
    def visit(children, prefix=''):
        for key, child in children:
            if any(candidate.kind not in ('parameter', 'fresh', 'owned_projection') for candidate in child.candidates):
                return False
            symbols = frozenset(candidate.storage() for candidate in child.candidates)
            if not symbols or any(source.kind not in (
                    'source_parameter', 'allocation_parameter', 'allocation_field_parameter')
                    for source in symbols):
                return False
            path = prefix + key
            fields.append((path, symbols))
            if enums is not None:
                from array_syntax import aggregate_owned_paths
                from results import SourceOrigin
                # A transferred parameter may represent a whole owned tree,
                # without spelling every descendant in its Value contract.
                for candidate in child.candidates:
                    if candidate.kind == 'parameter':
                        for suffix, _ in aggregate_owned_paths(enums, child.typ):
                            fields.append((path + '/' + suffix, frozenset({SourceOrigin(
                                'allocation_field_parameter', candidate.parameter, suffix)})))
            if not visit(child.owned_fields, path + '/'):
                return False
        return True
    if not visit(summary.owned_fields):
        return None
    merged = {}
    for path, symbols in fields:
        merged[path] = merged.get(path, frozenset()) | symbols
    inherited.update(merged)
    roots = frozenset(candidate.storage() if candidate.kind == 'parameter'
        else output_origin(candidate.source, summary.typ) for candidate in summary.candidates)
    return roots, tuple(sorted(inherited.items()))


def borrowed_result_fields(node):
    """Completed stored-reference origins, distinct from captures kept while running."""
    effect = getattr(node, 'field_effect_summary', None)
    if node.args[2][0] not in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange') or not effect or not effect.complete:
        return ()
    return effect.completion_result.borrowed_fields
