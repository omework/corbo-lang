"""Symbolic owned-result origins, inferred without call-site allocations."""
from __future__ import annotations
from owned_join_types import (
    OWNED_JOIN_TYPES, owned_join_mode, owned_inner_mode,
)
from option_join_types import (
    OPTION_JOIN_TYPES, option_join_mode, option_inner_signature,
)
from exchange_join_types import (
    EXCHANGE_JOIN_TYPES, exchange_join_mode, exchange_payload_type, exchange_inner_signature, exchange_is_try_push,
)
from capture_paths import result_capture_selector, capture_fields, capture_index
from integer_syntax import exact_integer_conversion
from numeric_core import FORMATS, MODE_TYPES, CONVERSION_PAYLOADS, NUMERIC_JOIN_FIELDS, conversion_mode, conversion_type, numeric_type
from structure_views import scalar_field_mode
from utf8_syntax import ERROR_VALUE_TYPES, RESULT_ERROR_MODES
from utf8_syntax import ASYNC_VALUE_RESULT_FAMILIES
from utf8_syntax import PLAIN_JOIN_TYPES, PLAIN_RETURN_JOINS, PLAIN_JOIN_INNER_MODES

from utf8_syntax import ASYNC_CAPTURE_VIEW_MODES, ASYNC_SHARED_VIEW_MODES, VECTOR_SLICE_ELEMENTS, VECTOR_SPLIT_TYPES, SHARED_VECTOR_SLICE_MODES, VECTOR_SLICE_MODES, VECTOR_MUT_SLICE_MODES, VECTOR_OPTION_MODES, VECTOR_REPLACE_MODES, VECTOR_TRY_PUSH_MODES, UTF8_EXPRESSION_MODES, UTF8_METHODS, UTF8_TEXT_RESULT, UTF8_SLICE_RESULT, UTF8_BORROW_MODES, VALUE_MODES, UTF8_VALUE_RESULT_FAMILIES
from dataclasses import dataclass, field, replace
from handle_exchange_types import exchange_type, exchange_element, exchange_optional
from handle_types import resolve_handle_pool_origins
from array_syntax import is_payload_vector, vector_payload_element
from array_syntax import HANDLE_VECTORS, INLINE_VECTOR_ELEMENTS, is_handle_vector, handle_vector_element, register_handle_vector
from array_syntax import aggregate_owned_paths
from array_syntax import merge_structure_choices
from effects import allocation_handle_method, allocation_value_borrow, builtin_method_statement, check_builtin_expression_arity, method_arguments, method_candidate

from array_syntax import consumed_result_expression, merge_owned_values, aggregate_reference_paths, nested_reference_fields, replace_shared_vector_item, shared_vector_field_items, update_shared_vector_items, MUT_REF_VECTOR, REFERENCE_VECTORS, merge_exchange_values, merge_exchange_payloads, replace_handle_positions, UNKNOWN_VECTOR_REMOVALS, possible_handle_items, remaining_handle_items, VECTOR_LAST_ITEM, last_handle_index, merge_handle_items, handle_items_at, handle_items_after_exchange, handle_items_after_removal, ARRAY_STATEMENTS, HANDLE_VECTOR, VECTOR_TYPES, VECTOR_ELEMENTS, vector_method, array_operands, reference_array_shape, fixed_array_shape, borrowed_array_name, update_array_aliases, update_structure_parameters, update_local_structure_locations, restore_array_binding, reference_array_path, reference_array_projection, replace_reference_fields, swap_reference_fields, reference_array_variable, project_reference_array, merge_container_positions, reference_type, reference_array_element, reference_tree_fields, reference_tree_slot, reference_tree_targets, merge_reference_values, merge_reference_rows, unflatten_reference_value, reference_value_place, replace_reference_rows, swapped_reference_rows, target_row_templates, rebuild_reference_tree, reference_tree_type


@dataclass(frozen=True, order=True)
class SourceOrigin:
    kind: str
    index: int
    name: str = ''
    element: str | None = field(default=None, compare=False)

    def describe(self, params):
        if self.kind == 'task_output':
            return {'kind': 'task_output', 'type': self.element}
        if self.kind == 'task_output_parameter':
            return {'kind': self.kind, 'parameter': params[self.index][0], 'type': self.element}
        if self.kind == 'local_value':
            return {'kind': 'local_value', 'type': self.element}
        if self.kind == 'source_parameter':
            return {'kind': 'parameter', 'parameter': params[self.index][0]}
        if self.kind in ('allocation_parameter', 'vector_element_parameter', 'task_parameter', 'task_result_parameter'):
            return {'kind': self.kind, 'parameter': params[self.index][0]}
        if self.kind in ('allocation_field_parameter', 'task_result_field_parameter'):
            return {'kind': self.kind, 'parameter': params[self.index][0], 'field': self.name}
        return {'kind': 'local', 'name': self.name}


@dataclass(frozen=True, order=True)
class ResultCandidate:
    kind: str
    parameter: int = -1
    source: SourceOrigin | None = None
    item_index: int = -1
    excluded_items: tuple[int, ...] = ()
    tail_offset: int = 0
    vector_removals: tuple[int, ...] = ()
    vector_added_parameters: tuple[int, ...] = ()
    vector_added_pools: tuple[int, ...] = ()
    vector_added_elements: tuple[ResultCandidate, ...] = ()
    vector_layout: tuple[tuple[ResultCandidate, ...], ...] = ()
    vector_replacements: tuple[tuple[int, tuple[ResultCandidate, ...]], ...] = ()
    field_path: str = ''

    def storage(self):
        if self.kind == 'fresh':
            return self.source
        if self.kind == 'owned_projection':
            return SourceOrigin('allocation_field_parameter', self.parameter, self.field_path)
        kind = {'vector_element': 'vector_element_parameter', 'task_capture': 'task_result_parameter'}.get(
            self.kind, 'allocation_parameter')
        return SourceOrigin(kind, self.parameter)

    def describe(self, params):
        if self.kind in ('parameter', 'vector_element', 'exchange_parameter', 'owned_projection', 'task_capture'):
            result = {'kind': self.kind, 'parameter': params[self.parameter][0]}
            if self.kind == 'owned_projection':
                result['field'] = self.field_path
            elif self.kind == 'exchange_parameter':
                result['arm'] = ('Ok', 'Err')[self.item_index]
            elif self.item_index >= 0:
                result['index'] = self.item_index
            elif self.item_index == VECTOR_LAST_ITEM:
                result['index'] = 'last'
                if self.excluded_items:
                    result['excluded_indices'] = list(self.excluded_items)
                if self.tail_offset:
                    result['tail_offset'] = self.tail_offset
        else:
            result = {'kind': 'fresh', 'source': self.source.describe(params)}
        if self.vector_layout:
            key = 'appended_positions' if self.kind == 'parameter' else 'item_positions'
            result[key] = [[item.describe(params) for item in slot] for slot in self.vector_layout]
        if self.vector_replacements:
            result['replaced_positions'] = {
                index: [item.describe(params) for item in slot] for index, slot in self.vector_replacements}
        if self.vector_added_parameters:
            result['added_parameters'] = [params[index][0] for index in self.vector_added_parameters]
        if self.vector_added_elements:
            result['added_elements'] = [item.describe(params) for item in self.vector_added_elements]
        if self.vector_added_pools:
            result['added_pools'] = [params[index][0] for index in self.vector_added_pools]
        if self.vector_removals == UNKNOWN_VECTOR_REMOVALS:
            result['removals'] = 'unknown'
        elif self.vector_removals:
            tail, *indices = self.vector_removals
            result['removed_indices'] = indices
            result['removed_tail'] = tail
        return result


def async_owned_candidates(sources):
    candidates = set()
    for source in sources:
        if source.kind == 'task_output':
            candidates.add(ResultCandidate('fresh', source=SourceOrigin(
                'local_value', source.index, 'data stack implicite', source.element)))
        elif source.kind == 'task_output_parameter':
            candidates.add(ResultCandidate('fresh', source=SourceOrigin(
                'allocation_parameter', source.index, element=source.element)))
        elif source.kind == 'allocation_parameter':
            candidates.add(ResultCandidate('parameter', source.index))
        elif source.kind == 'vector_element_parameter':
            candidates.add(ResultCandidate('vector_element', source.index))
        elif source.kind == 'task_result_parameter':
            candidates.add(ResultCandidate('task_capture', source.index))
        elif source.kind in ('source_parameter', 'local', 'allocation_field_parameter', 'task_result_field_parameter'):
            candidates.add(ResultCandidate('fresh', source=source))
        else:
            candidates.add(ResultCandidate('fresh', source=SourceOrigin('local', -1, 'capture')))
    return frozenset(candidates)


def merge_deferred_map_paths(values):
    if not any(value.deferred_map_paths for value in values):
        return frozenset()
    return frozenset(path for value in values for path in value.deferred_map_paths or ((),))


def merge_deferred_definite_fields(values):
    groups = tuple(value.deferred_definite_fields for value in values)
    return frozenset.intersection(*groups) if groups else frozenset()


def merge_task_result_fields(values):
    fields = {}
    for value in values:
        for path, sources in value.task_result_fields:
            fields[path] = fields.get(path, frozenset()) | sources
    return tuple(sorted(fields.items()))


def merge_task_result_shapes(values):
    maps = [dict(value.task_result_shapes) for value in values]

    def absent(fields, path):
        prefix = ''
        for component in path.split('/') if path else ():
            variants = fields.get(prefix)
            if variants and component.partition('.')[0] not in variants:
                return True
            prefix += ('/' if prefix else '') + component
        return False

    output = []
    for path in sorted({path for fields in maps for path in fields}):
        groups = [fields.get(path, frozenset()) for fields in maps if not absent(fields, path)]
        output.append((path, frozenset().union(*groups) if all(groups) else frozenset()))
    return tuple(output)


@dataclass(frozen=True)
class FunctionResult:
    mode: str
    typ: str
    candidates: frozenset[ResultCandidate] = frozenset()
    borrowed_fields: tuple = ()
    fresh_variants: frozenset[str] = frozenset()

    reference_targets: frozenset = frozenset()
    parameter_fields: tuple = ()
    payload_reference: bool = False
    referent_fields: tuple = ()
    structure_fields: tuple = ()
    vector_slot: tuple[int, int | None] | None = None
    vector_writes: tuple = ()
    vector_write_payloads: tuple = field(default=(), kw_only=True)
    vector_values: tuple = field(default=(), kw_only=True)
    handle_writes: tuple[tuple[int, tuple[ResultCandidate, ...]], ...] = ()
    handle_write_fields: tuple = ()
    exchange_payloads: tuple = ()
    exchange_values: tuple = field(default=(), kw_only=True)
    shared_vector_layout: tuple | None = None
    shared_vector_passthrough: int | None = None
    reference_appends: tuple = ()
    owned_fields: tuple = ()
    owned_field_writes: tuple = ()
    task_sources: frozenset[SourceOrigin] = frozenset()
    task_result_sources: frozenset[SourceOrigin] = frozenset()
    task_result_fields: tuple = ()
    task_result_shapes: tuple = ()
    task_result_handle_pools: frozenset[str | int] = field(default=frozenset(), kw_only=True)
    # Includes temporary stores restored before return. Final field deltas
    # alone cannot describe the reference representation needed by a bridge.
    stored_reference_parameters: frozenset[int] = frozenset()
    # Possible waits and returned inputs across normal control-flow paths.
    # The body checker separately enforces each launched handle's wait duty.
    task_wait_parameters: frozenset[int] = frozenset()
    task_forward_parameters: frozenset[int] = frozenset()
    task_field_updates: tuple = ()
    # Proven absence, not an unknown source: an owned Result contains no
    # allocation on any continuing path (for example LaunchFailed only).
    absent_owned_payload: bool = False
    task_forward_only: bool = False
    task_suspension_fields: tuple | None = None
    task_may_suspend: bool | None = None
    task_owned_updates: tuple = ()
    task_vector_updates: tuple = ()
    task_suspension_vectors: tuple | None = None
    task_suspension_owned: tuple | None = None

    @property
    def same_parameter(self):
        if len(self.candidates) == 1:
            candidate = next(iter(self.candidates))
            if candidate.kind == 'parameter':
                return candidate.parameter
        return None

    def describe(self, params):
        description = {'mode': self.mode, 'type': self.typ,
                'alternatives': [candidate.describe(params) for candidate in sorted(self.candidates)],
                'borrowed_fields': [{'field': name, 'targets': [t.describe(params) for t in sorted(targets)]}
                                    for name, targets in self.borrowed_fields],
                'fresh_variants': sorted(self.fresh_variants),
                'reference_targets': [t.describe(params) for t in sorted(self.reference_targets)]}
        if self.absent_owned_payload:
            description['absent_owned_payload'] = True
        if self.task_field_updates:
            description['task_field_updates'] = [
                {'parameter': params[index][0], 'fields': [
                    {'field': field, 'targets': [t.describe(params) for t in sorted(targets)]}
                    for field, targets in fields]} for index, fields in self.task_field_updates]
        for attribute in ('task_vector_updates', 'task_suspension_vectors'):
            updates = getattr(self, attribute)
            if updates is not None and self.mode in ('task', 'execution'):
                description[attribute] = [
                    {'parameter': params[index][0], 'items': [item.describe(params) for item in sorted(items)]}
                    for index, items in updates]
        for attribute in ('task_owned_updates', 'task_suspension_owned'):
            updates = getattr(self, attribute)
            if updates is not None and self.mode in ('task', 'execution'):
                description[attribute] = [
                    {'parameter': params[index][0], 'field': path, 'alternatives': [
                        {'kind': 'unchanged'} if item.kind == 'owned_field_input' else item.describe(params)
                        for item in sorted(child.candidates)]}
                    for index, path, child in updates]
        if self.mode == 'task':
            description['task_suspension_complete'] = self.task_suspension_fields is not None
            description['task_may_suspend'] = self.task_may_suspend
            if self.task_suspension_fields is not None:
                description['task_suspension_fields'] = [
                    {'parameter': params[index][0], 'fields': [
                        {'field': field, 'targets': [target.describe(params) for target in sorted(targets)]}
                        for field, targets in fields]} for index, fields in self.task_suspension_fields]
        if self.task_wait_parameters:
            description['task_wait_parameters'] = [params[i][0] for i in sorted(self.task_wait_parameters)]
        if self.task_forward_parameters:
            description['task_forward_parameters'] = [params[i][0] for i in sorted(self.task_forward_parameters)]
        if self.task_result_sources:
            description['task_result_sources'] = [source.describe(params) for source in sorted(self.task_result_sources)]
        if self.task_result_fields:
            description['task_result_fields'] = [
                {'field': path, 'sources': [source.describe(params) for source in sorted(sources)]}
                for path, sources in self.task_result_fields]
        if self.task_result_shapes:
            description['task_result_shapes'] = {path: sorted(variants) for path, variants in self.task_result_shapes}
        if self.task_result_handle_pools:
            description['task_result_handle_pools'] = {
                'pools': sorted(pool for pool in self.task_result_handle_pools if isinstance(pool, str)),
                'parameters': [params[index][0] for index in sorted(
                    pool for pool in self.task_result_handle_pools if isinstance(pool, int))],
            }
        if self.task_sources:
            description['task_sources'] = [source.describe(params) for source in sorted(self.task_sources)]
        if self.reference_appends:
            description['reference_appends'] = [
                {'parameter': params[index][0], 'slots': [
                    [target.describe(params) for target in sorted(slot)] for slot in slots]}
                for index, slots in self.reference_appends]
        if self.owned_fields:
            def describe_fields(fields):
                return {name: {'alternatives': [candidate.describe(params) for candidate in sorted(child.candidates)],
                               'owned_fields': describe_fields(child.owned_fields)}
                        for name, child in fields}
            description['owned_fields'] = describe_fields(self.owned_fields)
        if self.owned_field_writes:
            description['owned_field_writes'] = [
                {'parameter': params[index][0], 'field': name, 'alternatives': [
                    {'kind': 'unchanged'} if item.kind == 'owned_field_input' else item.describe(params)
                    for item in sorted(child.candidates)]}
                for index, name, child in self.owned_field_writes]
        if self.shared_vector_passthrough is not None:
            description['shared_vector_passthrough'] = params[self.shared_vector_passthrough][0]
        if self.shared_vector_layout is not None:
            description['shared_vector_layout'] = [
                [target.describe(params) for target in sorted(slot)] for slot in self.shared_vector_layout]
        if self.exchange_payloads:
            description['exchange_payloads'] = {
                arm: [candidate.describe(params) for candidate in sorted(candidates)]
                for arm, candidates in zip(('Ok', 'Err'), self.exchange_payloads)}
        if self.vector_writes:
            description['vector_writes'] = [
                {'parameter': params[index][0], 'exact': exact,
                 'slots': [[item.describe(params) for item in slot] for slot in slots],
                 'replacements': {position: [item.describe(params) for item in slot]
                                  for position, slot in replacements},
                 'removals': list(removals)}
                for index, slots, exact, replacements, removals in self.vector_writes]
        if self.vector_write_payloads or self.exchange_values or self.vector_values:
            def describe_payload(payload):
                return {'type': payload.typ,
                        'alternatives': [item.describe(params) for item in sorted(payload.candidates)],
                        'borrowed_fields': {name: [target.describe(params) for target in sorted(targets)]
                                            for name, targets in payload.fields},
                        'owned_fields': {name: describe_payload(child) for name, child in payload.owned_fields}}
            description['vector_write_payloads'] = [
                {'parameter': params[index][0], 'payloads': [describe_payload(payload) for payload in payloads]}
                for index, payloads in self.vector_write_payloads]
            if self.exchange_values:
                description['exchange_values'] = {
                    arm: describe_payload(value) for arm, value in zip(('Ok', 'Err'), self.exchange_values)}
            if self.vector_values:
                description['vector_values'] = [describe_payload(value) for value in self.vector_values]
        if self.vector_slot is not None:
            parameter, index = self.vector_slot
            description['vector_slot'] = {'parameter': params[parameter][0], 'index': index}
        if self.handle_writes:
            fields = dict(self.handle_write_fields)
            description['handle_writes'] = [
                {'parameter': params[index][0], 'alternatives': [item.describe(params) for item in candidates],
                 'fields': {field: [target.describe(params) for target in sorted(targets)]
                            for field, targets in fields.get(index, ())}}
                for index, candidates in self.handle_writes]
        if self.payload_reference:
            description['payload_reference'] = True
        if self.parameter_fields:
            description['parameter_fields'] = [
                {'parameter': params[index][0], 'fields': [
                    {'field': slot, 'targets': [target.describe(params) for target in sorted(targets)]}
                    for slot, targets in fields]}
                for index, fields in self.parameter_fields]
        if self.referent_fields:
            description['referent_fields'] = [
                {'parameter': params[index][0], 'path': path, 'fields': [
                    {'field': slot, 'targets': [target.describe(params) for target in sorted(targets)]}
                    for slot, targets in fields]} for index, path, fields in self.referent_fields]
        if self.structure_fields:
            description['structure_fields'] = [
                {'parameter': params[index][0], 'fields': [
                    {'field': field, 'targets': [target.describe(params) for target in sorted(targets)]}
                    for field, targets in fields]} for index, fields in self.structure_fields]
        if self.stored_reference_parameters:
            description['stored_reference_parameters'] = [
                params[index][0] for index in sorted(self.stored_reference_parameters)]
        return description


@dataclass(frozen=True, order=True)
class BorrowTarget:
    kind: str
    parameter: int = -1
    field: str = ''
    detached_prefix: str = ''
    carrier_kind: str = ''

    def describe(self, params):
        result = {'kind': self.kind, 'parameter': params[self.parameter][0]}
        if self.field:
            result['field'] = self.field
        if self.detached_prefix:
            result['detached_prefix'] = self.detached_prefix
        if self.carrier_kind:
            result['carrier_kind'] = self.carrier_kind
        return result




def capture_result_origins(fields, indexes, shared):
    return frozenset(
        replace(origin, kind='exclusive_join_parameter')
        if shared and key.startswith('mut.') and origin.kind == 'parameter' else origin
        for index in indexes for key, origins in capture_fields(fields, index) for origin in origins
    )


def projected_field_origin(origin, target):
    if origin.kind == 'parameter':
        return replace(target, parameter=origin.parameter)
    if (origin.kind == 'inline_field_parameter' and not origin.carrier_kind
            and target.field.startswith('.')):
        prefix = '.' + origin.field
        return replace(target, parameter=origin.parameter, field=prefix + target.field,
                       detached_prefix=prefix + target.detached_prefix if target.detached_prefix else '')
    if origin.kind == 'detached_field_parameter' and target.kind == 'shared_field_parameter':
        prefix = '/'.join(part for part in (origin.field, target.detached_prefix) if part)
        return BorrowTarget(target.kind, origin.parameter, origin.field + '/' + target.field, prefix)
    if origin.kind in ('field_parameter', 'shared_field_parameter') and not target.detached_prefix:
        return replace(origin, field=origin.field + '/' + target.field)
    return BorrowTarget('local')


def merge_fields(values):
    result = {}
    for value in values:
        for name, targets in value.fields:
            result[name] = result.get(name, frozenset()) | targets
    return tuple(sorted(result.items()))


def merge_task_suspensions(values):
    if any(value.deferred_suspension_updates is None for value in values):
        return None
    # These are alternative task states, not successive writes. Keep all
    # targets of each carrier instead of letting frozenset iteration pick one.
    updates = {}
    for value in values:
        for carrier, fields in value.deferred_suspension_updates:
            merged = updates.setdefault(carrier, {})
            for field, targets in fields:
                merged[field] = merged.get(field, frozenset()) | targets
    return frozenset((carrier, tuple(sorted(fields.items()))) for carrier, fields in updates.items())


def merge_task_may_suspend(values):
    return None if any(value.task_may_suspend is None for value in values) else any(
        value.task_may_suspend for value in values)


def merge_task_vector_updates(values, attribute):
    if any(getattr(value, attribute) is None for value in values):
        return None
    return frozenset(update for value in values for update in getattr(value, attribute))


def merge_task_owned_updates(values, attribute):
    if any(getattr(value, attribute) is None for value in values):
        return None
    updates = {}
    for value in values:
        for carrier, path, child in getattr(value, attribute):
            key = carrier, path
            updates[key] = merge_owned_values((updates[key], child)) if key in updates else child
    return frozenset((carrier, path, child) for (carrier, path), child in updates.items())


def borrowed_targets(value):
    return value.reference_targets | frozenset(
        BorrowTarget('parameter', c.parameter) if c.kind == 'parameter'
        else BorrowTarget('local') for c in value.candidates)


def text_origins(value):
    targets = borrowed_targets(value)
    carrier = 'vector_parameter' if value.typ in VECTOR_TYPES else 'string_parameter' if value.typ == 'String' else None
    if carrier is None:
        return targets
    return frozenset(BorrowTarget(carrier, t.parameter) if t.kind == 'parameter' else t
                     for t in targets) or frozenset({BorrowTarget('local')})


def stored_targets(value):
    return frozenset(BorrowTarget('reserved_field_parameter', t.parameter, t.field)
                     if t.kind == 'field_parameter' else t for t in borrowed_targets(value))


@dataclass(frozen=True)
class InputVectorHistory:
    excluded: tuple[int, ...] = ()
    tail: int = 0
    appended: tuple[frozenset[ResultCandidate], ...] = ()
    replaced: tuple[tuple[int, frozenset[ResultCandidate]], ...] = ()

    def original_index(self, index):
        for removed in self.excluded:
            if removed <= index:
                index += 1
        return index

    def remove(self, index, last):
        if last:
            return self.compose((1,))
        if index is None or index < 0:
            return None
        return self.compose((0, index))

    def replace_slot(self, index, items):
        if index is None or index < 0 or self.appended:
            return None
        return replace(self, replaced=tuple(sorted((dict(self.replaced) | {index: items}).items())))

    def compose(self, removals):
        if removals == (0,):
            return self
        tail, *indices = removals
        if self.appended or (tail and self.replaced):
            return None
        excluded = tuple(sorted((*self.excluded, *(self.original_index(i) for i in indices))))
        replaced = tuple((index - sum(removed < index for removed in indices), items)
                         for index, items in self.replaced if index not in indices)
        return InputVectorHistory(excluded, self.tail + tail, replaced=replaced)


@dataclass(frozen=True)
class Value:
    mode: str
    typ: str
    candidates: frozenset[ResultCandidate] = frozenset()
    fields: tuple = ()
    fresh_variants: frozenset[str] = frozenset()
    reference_targets: frozenset[BorrowTarget] = frozenset()
    payload_reference: bool = False
    container_origins: frozenset = frozenset()
    container_positions: tuple = ()
    container_borrow: bool = False
    container_mode: str = 'ref'
    rows: tuple = ()
    storage_owner: str | None = None
    structure_origins: frozenset = frozenset()
    # Equal-length paths retain a tuple of per-slot alternatives. A join with
    # different lengths retains only the set of possible elements.
    handle_items: tuple[frozenset[ResultCandidate], ...] | frozenset[ResultCandidate] | None = None
    handle_payloads: tuple = ()
    handle_exchange: tuple | None = None
    exchange_payloads: tuple = ()
    handle_slot: tuple[frozenset, int | None] | None = None
    input_item_history: InputVectorHistory | None = None
    input_items_changed: bool = False
    input_items_written: bool = False
    owned_fields: tuple = ()
    owned_path: tuple = ()
    owned_alternatives: tuple = ()
    task_sources: frozenset[SourceOrigin] = frozenset()
    task_result_sources: frozenset[SourceOrigin] = frozenset()
    task_result_fields: tuple = ()
    deferred_vector_updates: frozenset = frozenset()
    deferred_suspension_vectors: frozenset | None = None
    task_result_shapes: tuple = ()
    task_result_handle_pools: frozenset[str | int] = field(default=frozenset(), kw_only=True)
    # Deferred field-effect analysis keeps capture snapshots until await/join.
    # This is separate from storage identities of ordinary structures.
    pending_structure_calls: frozenset = frozenset()
    pending_structure_complete: bool = field(default=False, kw_only=True)
    deferred_guarded_writes: frozenset = field(default=frozenset(), kw_only=True)
    deferred_definite_fields: frozenset = field(default=frozenset(), kw_only=True)
    deferred_map_paths: frozenset = field(default=frozenset(), kw_only=True)
    task_parameters: frozenset[int] = frozenset()
    deferred_field_updates: frozenset = frozenset()
    absent_owned_payload: bool = False
    task_forward_only: bool = False
    deferred_suspension_updates: frozenset | None = None
    task_may_suspend: bool | None = None
    deferred_owned_updates: frozenset = frozenset()
    deferred_suspension_owned: frozenset | None = None
    structure_choices: tuple = ()
    # Storage provenance for an explicit copy of a borrowed interior value.
    # These are not additional borrowed targets of the reference itself.
    copy_candidates: frozenset[ResultCandidate] = frozenset()
    inline_path: str = ''
    # The carrier identity and the graph returned by each arm are independent.
    exchange_values: tuple = ()

    def __post_init__(self):
        if self.mode == 'buffered_handle_exchange' and (self.exchange_values or any(item.fields or item.owned_fields for item in self.handle_payloads)):
            fields, owned = {}, []
            for arm, candidates in zip(('ok', 'err'), self.exchange_payloads):
                active = ((self.exchange_values[('ok', 'err').index(arm)],) if self.exchange_values else
                          tuple(item for item in self.handle_payloads if item.candidates & candidates))
                if not active:
                    continue
                payload = merge_owned_values(active)
                owned.append((arm, payload))
                def collect(value, prefix):
                    for name, targets in value.fields:
                        fields[prefix + name] = fields.get(prefix + name, frozenset()) | targets
                    for name, child in value.owned_fields:
                        collect(child, prefix + name + '/')
                collect(payload, arm + '/')
            object.__setattr__(self, 'fields', tuple(sorted(fields.items())))
            object.__setattr__(self, 'owned_fields', tuple(owned))
            return
        if not is_payload_vector(self.typ):
            return
        items = possible_handle_items(self.handle_items)
        active = tuple(item for item in self.handle_payloads
                       if items is None or item.candidates & items)
        fields = {}
        def collect(item, prefix):
            for name, targets in item.fields:
                fields[prefix + name] = fields.get(prefix + name, frozenset()) | targets
            for name, child in item.owned_fields:
                collect(child, prefix + name + '/')
        for item in active:
            collect(item, '[]/')
        object.__setattr__(self, 'fields', tuple(sorted(fields.items())))
        object.__setattr__(self, 'owned_fields', (('[]', merge_owned_values(active)),)
                           if active and any(item.owned_fields for item in active) else ())


SCALAR = Value('scalar', 'Int')
VOID = Value('void', 'Void')
UNKNOWN = Value('unknown', '?')


UNKNOWN_HANDLE_ITEM = ResultCandidate('fresh', source=SourceOrigin('local', -1, 'élément de vecteur'))


def extracted_handle(items, typ='Int'):
    return Value('owned', typ, items or frozenset({UNKNOWN_HANDLE_ITEM}))


def restore_handle_payload(value, carrier):
    if not isinstance(carrier, Value):
        return value
    payloads = tuple(item for item in carrier.handle_payloads if item.candidates & value.candidates or any(
        left.kind == right.kind == 'vector_element' and left.parameter == right.parameter
        for left in item.candidates for right in value.candidates))
    if not payloads:
        return value
    merged = merge_owned_values(payloads)
    return replace(merged, mode=value.mode, typ=value.typ, candidates=value.candidates)


def merge_input_item_history(values):
    if not values:
        return None
    histories = [value.input_item_history for value in values]
    first = histories[0]
    if all(history == first for history in histories):
        return first
    if first is None or any(history is None or
                            (history.excluded, history.tail, len(history.appended)) !=
                            (first.excluded, first.tail, len(first.appended))
                            for history in histories):
        return None
    appended = tuple(frozenset().union(*slots) for slots in zip(*(history.appended for history in histories)))
    replacements = [dict(history.replaced) for history in histories]
    merged = []
    for index in sorted(set().union(*replacements)):
        candidates = set()
        original = first.original_index(index)
        for value, slots in zip(values, replacements):
            if index in slots:
                candidates.update(slots[index])
            elif not value.candidates or any(item.kind != 'parameter' for item in value.candidates):
                return None
            else:
                candidates.update(ResultCandidate('vector_element', item.parameter, item_index=original)
                                  for item in value.candidates)
        merged.append((index, frozenset(candidates)))
    return replace(first, appended=appended, replaced=tuple(merged))


def vector_result_candidates(vector, index, *, last=False, excluded=(), tail_offset=0):
    if not isinstance(vector, Value):
        return None
    if last:
        index = last_handle_index(vector.handle_items, excluded, tail_offset)
    items = handle_items_at(vector.handle_items, index)
    history = vector.input_item_history
    if items and history is not None:
        if history.appended or history.replaced:
            return items
        if last:
            excluded = tuple(sorted((*history.excluded, *(history.original_index(i) for i in excluded))))
            return frozenset(replace(item, item_index=VECTOR_LAST_ITEM, excluded_items=excluded,
                                     tail_offset=history.tail + tail_offset) for item in items)
        if index is not None and index >= 0:
            original = history.original_index(index)
            return frozenset(replace(item, item_index=original) for item in items)
    return items


@dataclass(frozen=True)
class ResultContract:
    """Result-only interface available before effect constraints are assembled."""
    parameters: tuple
    result_type: tuple
    result: FunctionResult


class ResultAnalyzer:
    """Nominal result flow; the concrete verifier still checks moves/loans."""
    def __init__(self, functions, effects, error, enums=None, async_functions=None):
        from handle_types import HandleDefinitions
        self.async_functions = HandleDefinitions(async_functions or {}, structures=enums or {})
        self.functions = functions
        self.effects = effects
        self.error = error
        self.summaries = {}
        self.visiting = set()
        self.enums = enums or {}
        self.async_effect_analyzer = None
        self.async_summary_resolver = None

    def async_definition(self, name):
        """Resolve a needed completion contract before inspecting its result.

        This is inference, not call-site verification. Only completed summaries
        are published; a dependency cycle remains explicitly incomplete.
        """
        node = self.async_functions[name]
        if hasattr(node, 'public_result_storage') or getattr(node, 'field_effect_summary', None) is not None:
            return node
        if self.async_summary_resolver is None:
            if self.async_effect_analyzer is None:
                from types import SimpleNamespace
                from async_structure_effects import AsyncStructureEffectAnalyzer
                interfaces = {symbol: SimpleNamespace(parameters=tuple(function.args[1]),
                    result_type=function.args[2], effects=self.effects[symbol], result=None)
                    for symbol, function in self.functions.items()}
                self.async_effect_analyzer = AsyncStructureEffectAnalyzer(
                    self.async_functions, interfaces, self.enums, self.error,
                    sync_resolver=self.sync_summary)
            summary = self.async_effect_analyzer.infer(name)
        else:
            summary = self.async_summary_resolver(name)
        if summary.complete:
            node.field_effect_summary = summary
        return node

    def infer_all(self):
        for name in self.functions:
            self.infer(name)
        return self.summaries

    def sync_summary(self, name):
        # A cycle keeps the conservative async approximation; do not recurse
        # through a function whose result is currently being inferred.
        if name not in self.functions or name in self.visiting:
            return None
        return self.infer(name)

    def sync_result_contract(self, name):
        summary = self.sync_summary(name)
        if summary is None:
            return None
        node = self.functions[name]
        return ResultContract(tuple(node.args[1]), node.args[2], summary)

    def infer(self, name):
        if name in self.summaries:
            return self.summaries[name]
        node = self.functions[name]
        mode, typ = node.args[2]
        mutable_containers = any((parameter_mode == 'array_mut' and reference_array_shape(parameter_type))
                                 or (reference_array_shape(parameter_type) and reference_array_shape(reference_array_element(parameter_type)[1]))
                                 or (parameter_mode == 'mut' and parameter_type in (*HANDLE_VECTORS, *REFERENCE_VECTORS, *INLINE_VECTOR_ELEMENTS))
                                 or (parameter_mode == 'mut' and parameter_type.startswith('A<'))
                                 or (parameter_mode == 'mut' and any(
                                     reference_type(typ)
                                     for _, typ in self.enums.get(parameter_type, {}).get('', ())))
                                 or (parameter_mode == 'mut' and any(
                                     declared.startswith('A<') for fields in self.enums.get(parameter_type, {}).values()
                                     for _, declared in fields))
                                 for _, parameter_mode, parameter_type in node.args[1])
        scalar_reference_inputs = any(mode in ('ref', 'mut') and typ == 'Int'
                                      for _, mode, typ in node.args[1])
        task_inputs = any(mode in ('task', 'execution') for _, mode, _ in node.args[1])
        if mode not in ('task', 'execution', 'owned', 'handle_option', 'buffered_handle_exchange', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'ref', 'mut', 'array_refs', 'vector_split', *UTF8_BORROW_MODES) and not mutable_containers and not scalar_reference_inputs and not task_inputs:
            result = FunctionResult(mode, typ)
        else:
            if name in self.visiting:
                raise self.error(f'ligne {node.line}: prototype : récursion non prise en charge')
            self.visiting.add(name)
            try:
                result = ResultContext(self, node).infer()
            finally:
                self.visiting.remove(name)
        self.summaries[name] = result
        return result


class ResultContext:
    def __init__(self, analyzer, node):
        self.analyzer = analyzer
        self.node = node
        self.name, self.params, self.declared, self.body = node.args
        self.loops = []
        self.blocks = []
        self.returned = set()
        self.returned_payload_absence = []
        self.returned_task_sources = set()
        self.returned_task_result_sources = set()
        self.returned_task_result_fields = {}
        self.returned_task_shape_values = []
        self.task_wait_parameters = set()
        self.task_forward_parameters = set()
        self.task_forward_only = True
        self.returned_task_field_updates = {}
        self.returned_task_suspension_updates = {}
        self.returned_task_owned_updates = {}
        self.returned_task_vector_updates = {}
        self.returned_task_suspension_vectors = {}
        self.returned_task_suspension_owned = {}
        self.returned_task_suspension_complete = True
        self.returned_task_may_suspend = False
        self.returned_references = set()
        self.returned_fields = {}
        self.returned_owned_fields = {}
        self.owned_field_writes = {}
        self.owned_exit_states = []
        self.shared_vector_returns = []
        self.shared_vector_passthroughs = set()
        self.returned_exchange_payloads = ()
        self.returned_exchange_values = ()
        self.returned_vector_values = {}
        self.fresh_variants = frozenset()
        self.updated_parameters = {}
        self.returned_payload = False
        self.returned_vector_slots = set()
        self.referent_inputs = {}
        self.updated_referents = {}
        self.structure_inputs = {}
        self.updated_structures = {}
        self.changed_shared_vectors = set()
        self.reference_append_paths = {}
        self.vector_write_paths = {}
        self.vector_write_payloads = {}
        self.updated_handles = {}
        self.updated_handle_fields = {}
        self.stored_reference_parameters = set()

    def fail(self, line, message):
        raise self.analyzer.error(f'ligne {line}: {message}')

    def lookup(self, name, environment, line):
        if name not in environment:
            self.fail(line, f"variable inconnue '{name}'")
        return environment[name]

    def check_call_actuals(self, name, actuals, line):
        """Extension point for additional symbolic payloads crossing contracts."""

    def record_stored_references(self, targets):
        for target in targets:
            if (target.kind == 'parameter'
                    and self.params[target.parameter][1] in ('ref', 'mut')
                    and self.params[target.parameter][2] == 'Int'):
                self.stored_reference_parameters.add(target.parameter)

    def public_handle_value(self, value, typ, line):
        from handle_types import is_public_handle, canonical_captures, PUBLIC_RESULT_LOCK_CAPTURE
        if not is_public_handle(typ) or not isinstance(value, Value) or value.mode != 'execution':
            return value
        from handle_types import contextual_public_type
        actual = contextual_public_type(value.typ, typ, self.analyzer.async_functions)
        if actual != typ:
            self.fail(line, f'handle {typ} attendu, reçu {actual}')
        if value.typ == typ:
            return value
        fields = tuple((key, frozenset(targets)) for key, targets in canonical_captures(
            value.fields, self.analyzer.async_functions[value.typ].args[1]))
        definition = self.analyzer.async_functions[value.typ]
        result_mode = definition.args[2][0]
        if result_mode == 'owned':
            locked = frozenset(target for index in getattr(definition, 'async_returned_lock_parameters', ())
                               for key, targets in capture_fields(value.fields, index)
                               if '/' not in key for target in targets)
            if locked:
                fields += ((PUBLIC_RESULT_LOCK_CAPTURE, locked),)
        if result_mode in ('owned', 'join_owned'):
            from async_result_storage import borrowed_result_fields
            projected = {}
            for field, targets in borrowed_result_fields(self.analyzer.async_functions[value.typ]):
                for target in targets:
                    selector = result_capture_selector(target)
                    if selector is None:
                        self.fail(line, 'résultat struct public : origine de champ non représentée')
                    for key, origins in capture_fields(value.fields, selector):
                        result_key = ('mut.' if key.startswith('mut.') else 'ref.') + '4/' + field
                        projected.setdefault(result_key, set()).update(origins)
            fields += tuple((key, frozenset(targets)) for key, targets in projected.items())
        if result_mode in ('ref', 'mut'):
            result_fields = {}
            for target in value.reference_targets:
                exclusive = (target.kind == 'exclusive_join_parameter' or any(
                    key.startswith('mut.') and target in origins for key, origins in value.fields))
                key = ('mut.5' if exclusive else 'ref.4') if result_mode == 'ref' else 'mut.4'
                if target.kind == 'exclusive_join_parameter':
                    target = replace(target, kind='parameter')
                result_fields.setdefault(key, set()).add(target)
            fields += tuple((key, frozenset(targets)) for key, targets in result_fields.items())
        if result_mode in ASYNC_CAPTURE_VIEW_MODES:
            from async_lowering import utf8_result_parameters
            definition = self.analyzer.async_functions[value.typ]
            indexes = utf8_result_parameters(definition, self.analyzer.async_functions,
                sync_result_contract=self.analyzer.sync_result_contract)
            result_fields = {}
            for index in indexes:
                for key, targets in capture_fields(value.fields, index):
                    result_key = (('mut.5' if key.startswith('mut.') else 'ref.4')
                                  if result_mode in ASYNC_SHARED_VIEW_MODES else 'mut.4')
                    result_fields.setdefault(result_key, set()).update(targets)
            fields += tuple((key, frozenset(targets)) for key, targets in result_fields.items())
        return replace(value, typ=typ, fields=fields)

    def unify_handle_values(self, values, line):
        from handle_types import common_public_handle
        if values and all(isinstance(value, Value) and value.mode == 'execution' for value in values):
            from handle_types import is_public_handle
            expected = self.declared[1] if self.declared[0] == 'execution' and is_public_handle(self.declared[1]) else None
            public = common_public_handle((value.typ for value in values), self.analyzer.async_functions, expected=expected)
            if public is not None:
                return [self.public_handle_value(value, public, line) for value in values]
        return values

    def parameter_array(self, index, typ, prefix=''):
        mode, count = reference_array_shape(typ)
        targets = tuple((str(slot), frozenset({BorrowTarget('stored_array_parameter', index, prefix + str(slot))}))
                        for slot in range(count))
        rows = ()
        pointee = reference_array_element(typ)[1]
        if reference_array_shape(pointee):
            rows = tuple((str(slot), replace(self.parameter_array(index, pointee, prefix + str(slot) + '/'),
                        container_borrow=True, container_mode=mode, reference_targets=dict(targets)[str(slot)]))
                         for slot in range(count))
        return Value('array_refs', typ, fields=targets, rows=rows,
                     container_origins=frozenset({('parameter', index, prefix)}))

    def async_owned_result_value(self, mode, typ, sources, fields, prefix='', shapes=()):
        storage = dict(fields)
        if is_handle_vector(typ):
            path = prefix + '[]'
            items = async_owned_candidates(storage.get(path, ()))
            child = self.async_owned_result_value('owned', handle_vector_element(typ),
                storage.get(path, ()), fields, path + '/', shapes)
            return Value(mode, typ, async_owned_candidates(sources),
                         handle_items=items, handle_payloads=(child,) if items else ())
        if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
            return Value(mode, typ, async_owned_candidates(sources),
                         exchange_payloads=tuple(async_owned_candidates(storage.get(arm, ()))
                                                 for arm in ('ok', 'err')))
        children = []
        for arm, members in self.analyzer.enums.get(typ, {}).items():
            for name, declared in members:
                if declared.startswith('A<'):
                    key = f'{arm}.{name}'
                    path = prefix + key
                    if path in storage:
                        children.append((key, self.async_owned_result_value(
                            'owned', declared[2:-1], storage[path], fields, path + '/', shapes)))
        inherited_root = bool(sources) and all(source.kind in ('task_result_parameter', 'allocation_parameter')
                                              for source in sources)
        opaque_field = not children and any(source.kind == 'task_result_field_parameter' for source in sources)
        # Input variants are instantiated at the call; they are not freshly
        # constructed alternatives of this helper's result.
        variants = frozenset() if inherited_root or opaque_field else frozenset(self.analyzer.enums.get(typ, {}))
        variants = dict(shapes).get(prefix.rstrip('/'), variants)
        return Value(mode, typ, async_owned_candidates(sources), owned_fields=tuple(children),
                     fresh_variants=variants)

    def owned_capture_storage(self, value, path=''):
        """Resolve an owned descendant without inspecting the async body.

        Parameter fields can remain symbolic until an actual call. Constructed
        fields instead retain their individual sources, including local pools.
        """
        if (value.mode == 'buffered_handle_exchange' or value.mode in EXCHANGE_JOIN_TYPES) and path in ('ok', 'err'):
            return {candidate.storage() for candidate in value.exchange_payloads[('ok', 'err').index(path)]}
        if value.owned_alternatives:
            return set().union(*(self.owned_capture_storage(item, path) for item in value.owned_alternatives))
        if path:
            key, _, tail = path.partition('/')
            if key == '[]' and is_handle_vector(value.typ):
                items = possible_handle_items(value.handle_items)
                payloads = tuple(child for child in value.handle_payloads if items is None or child.candidates & items)
                if payloads:
                    return set().union(*(self.owned_capture_storage(child, tail) for child in payloads))
            child = dict(value.owned_fields).get(key)
            if child is not None:
                return self.owned_capture_storage(child, tail)
        sources = set()
        for candidate in value.candidates:
            if candidate.kind in ('owned_field_input', 'owned_projection'):
                base = candidate.source.name if candidate.kind == 'owned_field_input' else candidate.field_path
                sources.add(SourceOrigin('allocation_field_parameter', candidate.parameter,
                                         base + ('/' + path if path else '')))
            elif candidate.kind == 'parameter' and path:
                sources.add(SourceOrigin('allocation_field_parameter', candidate.parameter, path))
            elif not path:
                sources.add(candidate.storage())
        return sources or {SourceOrigin('local', -1, 'capture')}

    @staticmethod
    def owned_value_shapes(value, prefix=''):
        if value.owned_alternatives:
            return merge_task_result_shapes([
                replace(item, task_result_shapes=ResultContext.owned_value_shapes(item, prefix))
                for item in value.owned_alternatives])
        shapes = [(prefix, value.fresh_variants)]
        for key, child in value.owned_fields:
            shapes.extend(ResultContext.owned_value_shapes(child, prefix + ('/' if prefix else '') + key))
        return tuple(shapes)

    def resolved_owned_shapes(self, value, actuals):
        alternatives = []
        for candidate in value.candidates:
            if candidate.kind == 'parameter':
                actual = actuals[candidate.parameter]
                shapes = self.owned_value_shapes(actual)
            elif candidate.kind == 'owned_projection':
                actual = self.project_owned_value(actuals[candidate.parameter], candidate.field_path, value.typ)
                shapes = self.owned_value_shapes(actual)
            elif candidate.kind == 'fresh':
                shapes = (('', value.fresh_variants),)
            else:
                shapes = (('', frozenset()),)
            alternatives.append(Value('owned', value.typ, task_result_shapes=shapes))
        shapes = dict(merge_task_result_shapes(alternatives))
        for key, child in value.owned_fields:
            # Explicit final fields replace inherited descendants in the contract.
            shapes = {path: variants for path, variants in shapes.items()
                      if path != key and not path.startswith(key + '/')}
            for path, variants in self.resolved_owned_shapes(child, actuals):
                shapes[key + ('/' + path if path else '')] = variants
        return tuple(sorted(shapes.items()))

    def instantiate_task_shapes(self, summary, actuals):
        shapes = dict(summary.task_result_shapes)
        explicit_paths = {path for path, _ in summary.task_result_fields}
        for path, sources in (('', summary.task_result_sources), *summary.task_result_fields):
            inherited = []
            complete = True
            for source in sources:
                if source.kind in ('task_result_parameter', 'task_result_field_parameter'):
                    actual = actuals[source.index]
                    prefix = source.name if source.kind == 'task_result_field_parameter' else ''
                    fields = tuple((key[len(prefix):].lstrip('/'), variants)
                                   for key, variants in actual.task_result_shapes
                                   if not prefix or key == prefix or key.startswith(prefix + '/'))
                    inherited.append(replace(actual, task_result_shapes=fields))
                elif source.kind in ('allocation_parameter', 'allocation_field_parameter'):
                    actual = actuals[source.index]
                    if source.kind == 'allocation_field_parameter':
                        for key in source.name.split('/'):
                            actual = dict(actual.owned_fields).get(key)
                            if actual is None:
                                break
                        if actual is None:
                            complete = False
                            continue
                    inherited.append(replace(actual, task_result_shapes=self.owned_value_shapes(actual)))
                else:
                    complete = False
            if inherited and complete:
                for key, variants in merge_task_result_shapes(inherited):
                    projected = path + ('/' if path and key else '') + key
                    if not any((not path or field.startswith(path + '/'))
                               and (projected == field or projected.startswith(field + '/'))
                               for field in explicit_paths):
                        shapes.setdefault(projected, variants)
        return tuple(sorted(shapes.items()))

    @staticmethod
    def owned_capture_path_absent(current, path):
        if current.owned_alternatives:
            return all(ResultContext.owned_capture_path_absent(item, path) for item in current.owned_alternatives)
        key, _, tail = path.partition('/')
        if current.fresh_variants and key.partition('.')[0] not in current.fresh_variants:
            return True
        child = dict(current.owned_fields).get(key)
        return bool(tail and child is not None and ResultContext.owned_capture_path_absent(child, tail))

    def owned_capture_paths(self, value):
        """Combine the finite type prefix with the actually constructed graph."""
        from array_syntax import owned_reference_paths

        owned = {path: typ for path, typ in aggregate_owned_paths(self.analyzer.enums, value.typ)
                 if not self.owned_capture_path_absent(value, path)}
        references = {path: (mode, typ)
                      for path, mode, typ in owned_reference_paths(self.analyzer.enums, value.typ)}
        if is_handle_vector(value.typ):
            items = possible_handle_items(value.handle_items)
            payloads = tuple(child for child in value.handle_payloads if items is None or child.candidates & items)
            if not payloads and items is not None and not items:
                return {}, {}
            for child in payloads:
                owned['[]'] = child.typ
                children, fields = self.owned_capture_paths(child)
                owned.update(('[]/' + path, typ) for path, typ in children.items())
                references.update(('[]/' + path, capability) for path, capability in fields.items())
        for alternative in value.owned_alternatives:
            children, fields = self.owned_capture_paths(alternative)
            owned.update(children)
            references.update(fields)
        for key, child in value.owned_fields:
            owned[key] = child.typ
            children, fields = self.owned_capture_paths(child)
            owned.update((key + '/' + path, typ) for path, typ in children.items())
            references.update((key + '/' + path, capability) for path, capability in fields.items())
        return owned, references

    def infer(self):
        environment = {}
        for index, (name, mode, typ) in enumerate(self.params):
            if mode in ('task', 'execution'):
                definition = self.analyzer.async_definition(typ)
                sources = frozenset({SourceOrigin('task_parameter', index)}) if any(
                    capture in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) or capture_type.startswith('Pool<')
                    for _, capture, capture_type in definition.args[1]) else frozenset()
                from async_lowering import borrowed_result_paths, owned_result_parameters
                fields = tuple((f'{"ref" if capture in ASYNC_SHARED_VIEW_MODES else "mut" if capture in SHARED_VECTOR_SLICE_MODES else capture.removeprefix("array_")}.{position}',
                                frozenset({BorrowTarget('task_capture_parameter', index, str(position))}))
                               for position, (_, capture, _) in enumerate(definition.args[1])
                               if capture in ('ref', 'mut', 'array_ref', 'array_mut', *ASYNC_CAPTURE_VIEW_MODES))
                from array_syntax import owned_reference_paths
                fields += tuple((f'{access}.{position}/{path}',
                                  frozenset({BorrowTarget('task_capture_parameter', index, f'{position}/{path}')}))
                    for position, (_, capture, capture_type) in enumerate(definition.args[1])
                    if capture in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES)
                    for path, access, _ in owned_reference_paths(self.analyzer.enums, capture_type))
                from handle_types import is_public_handle
                if is_public_handle(typ):
                    fields = tuple(('mut.' + key[4:] if key in ('ref.3', 'ref.5') else key, targets)
                                   for key, targets in fields)
                paths = borrowed_result_paths(definition, self.analyzer.async_functions, self.fail, {},
                                              sync_result_contract=self.analyzer.sync_result_contract)
                result_fields = tuple((key, origins) for key, origins in fields if '/' not in key or any(
                    index == capture_index(key.partition('.')[2]) and key.partition('/')[2] == '.' + '.'.join(path)
                    for index, path in paths))
                targets = capture_result_origins(result_fields, {index for index, _ in paths}, definition.args[2][0] == 'ref')
                result_sources = frozenset({SourceOrigin('task_result_parameter', index)}) if (
                    definition.args[2][0] in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) or owned_result_parameters(
                    definition, self.analyzer.async_functions, sync_result=self.analyzer.sync_summary)) else frozenset()
                if getattr(definition, 'result_storage', False):
                    sources |= frozenset({SourceOrigin('task_parameter', index)})
                owned_paths = tuple(aggregate_owned_paths(self.analyzer.enums, definition.args[2][1]))
                if is_handle_vector(definition.args[2][1]):
                    element = handle_vector_element(definition.args[2][1])
                    owned_paths = (('[]', element), *(( '[]/' + path, child_type)
                        for path, child_type in aggregate_owned_paths(self.analyzer.enums, element)))
                environment[name] = Value(mode, typ, fields=fields, reference_targets=targets, task_sources=sources,
                                          task_result_sources=result_sources, task_parameters=frozenset({index}), task_forward_only=True,
                                          task_result_fields=tuple((path, frozenset({SourceOrigin(
                                              'task_result_field_parameter', index, path)}))
                                              for path, _ in owned_paths))
            elif mode == 'async_execution':
                environment[name] = Value(mode, typ,
                    task_result_handle_pools=frozenset({index}),
                    reference_targets=frozenset({BorrowTarget('async_handle_result', index)}))
            elif typ == 'Allocator' or typ.startswith('Pool<'):
                environment[name] = SourceOrigin('source_parameter', index,
                                                 element=typ[5:-1] if typ.startswith('Pool<') else None)
            elif mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
                payloads = (frozenset() if exchange_optional(typ) or exchange_is_try_push(mode) else
                            frozenset({ResultCandidate('exchange_parameter', index, item_index=0)}),
                            frozenset({ResultCandidate('exchange_parameter', index, item_index=1)}))
                environment[name] = Value(mode, typ, frozenset().union(*payloads), exchange_payloads=payloads)
            elif mode == 'scalar':
                environment[name] = SCALAR
            elif mode in VALUE_MODES:
                origins = frozenset({BorrowTarget('utf8_parameter', index)}) if mode in UTF8_BORROW_MODES else frozenset()
                environment[name] = Value(mode, typ, reference_targets=origins)
            elif mode in ('array_ref', 'array_mut') and reference_array_shape(typ):
                environment[name] = self.parameter_array(index, typ)
            elif mode in ('array_ref', 'array_mut'):
                environment[name] = Value(mode, typ, reference_targets=frozenset({BorrowTarget('array_parameter', index)}))
            elif mode in ('array_refs', 'array_refs_owned'):
                environment[name] = self.parameter_array(index, typ)
            else:
                from array_syntax import owned_reference_paths
                fields = tuple((key, frozenset({BorrowTarget(
                    'detached_field_parameter' if '/' in key else 'field_parameter', index, key)}))
                               for key, _ in aggregate_reference_paths(self.analyzer.enums, typ))
                existing_fields = dict(fields)
                existing_fields.update((path, frozenset({BorrowTarget('field_parameter', index, path)}))
                    for path, _, _ in owned_reference_paths(self.analyzer.enums, typ) if '/' in path)
                fields = tuple(existing_fields.items())
                tracks_reference_items = typ in REFERENCE_VECTORS and mode in ('owned', 'mut')
                if typ in REFERENCE_VECTORS:
                    fields = (('.items', frozenset({BorrowTarget('detached_field_parameter', index, '.items')})),)
                origins = (frozenset({('vector_parameter', index)}) if is_payload_vector(typ)
                           else frozenset({('owned_parameter', index)})
                           if tracks_reference_items or (mode == 'owned' and typ in self.analyzer.enums)
                           else frozenset())
                environment[name] = Value(mode, typ, frozenset({ResultCandidate('parameter', index)}), fields,
                                          structure_origins=origins,
                                          handle_items=(frozenset({ResultCandidate('vector_element', index)})
                                                        if is_payload_vector(typ) and mode in ('owned', 'ref', 'mut', *OWNED_JOIN_TYPES)
                                                        else fields[0][1] if tracks_reference_items else None),
                                          input_item_history=InputVectorHistory()
                                          if (is_payload_vector(typ) and mode in ('owned', 'ref', 'mut', *OWNED_JOIN_TYPES))
                                          or (typ in REFERENCE_VECTORS and mode == 'mut') else None)
        def vector_payload(index, typ, path='[]', seen=frozenset()):
            if typ in seen:
                return Value('owned', typ)
            fields = tuple((key, frozenset({BorrowTarget('field_parameter', index, path + '/' + key)}))
                           for key, _ in aggregate_reference_paths(self.analyzer.enums, typ))
            children = tuple((f'{arm}.{name}', vector_payload(index, declared[2:-1],
                               path + '/' + f'{arm}.{name}', seen | {typ}))
                             for arm, fields in self.analyzer.enums.get(typ, {}).items()
                             for name, declared in fields if declared.startswith('A<'))
            candidate = (ResultCandidate('vector_element', index) if path == '[]' else
                         ResultCandidate('owned_projection', index, field_path=path))
            return Value('owned', typ, frozenset({candidate}), fields,
                         fresh_variants=frozenset(self.analyzer.enums.get(typ, {})), owned_fields=children)

        for index, (name, mode, typ) in enumerate(self.params):
            if is_payload_vector(typ):
                environment[name] = replace(environment[name], handle_payloads=(
                    vector_payload(index, vector_payload_element(typ)),))
            elif mode == 'buffered_handle_exchange':
                payloads = tuple(replace(vector_payload(index, exchange_element(typ), arm),
                    candidates=candidates) for arm, candidates in zip(('ok', 'err'), environment[name].exchange_payloads)
                    if candidates)
                environment[name] = replace(environment[name], handle_payloads=payloads)

        for index, (name, mode, typ) in enumerate(self.params):
            if mode in ('array_ref', 'array_mut') and reference_array_shape(typ):
                environment[name] = replace(environment[name], container_borrow=True, container_mode=mode[6:],
                                            reference_targets=frozenset({BorrowTarget('array_parameter', index)}))
                environment[f'\0parameter:{index}'] = environment[name]
            elif mode == 'mut' and (typ in REFERENCE_VECTORS or '' in self.analyzer.enums.get(typ, {}) or any(
                    declared.startswith('A<') for fields in self.analyzer.enums.get(typ, {}).values()
                    for _, declared in fields)):
                key = f'\0structure:{index}'
                def initial_fields(typ, prefix='', visited=frozenset()):
                    if typ in visited:
                        return ()
                    return tuple(
                        (f'{arm}.{field}', Value('owned', declared[2:-1], frozenset({
                            ResultCandidate('owned_field_input', index, SourceOrigin(
                                'allocation_field_parameter', index, f'{prefix}{arm}.{field}'))
                        }), fields=nested_reference_fields(environment[name].fields, f'{prefix}{arm}.{field}'),
                            owned_fields=initial_fields(declared[2:-1], f'{prefix}{arm}.{field}/', visited | {typ})))
                        for arm, fields in self.analyzer.enums.get(typ, {}).items()
                        for field, declared in fields if declared.startswith('A<'))
                initial_owned = initial_fields(typ)
                environment[name] = replace(environment[name], storage_owner=key, owned_fields=initial_owned)
                environment[key] = self.structure_inputs[index] = environment[name]
            elif mode == 'mut' and typ.startswith('A<'):
                key = f'\0handle:{index}'
                environment[name] = replace(environment[name], storage_owner=key)
                content = typ[2:-1]
                fields = tuple((f'{arm}.{field}', frozenset({BorrowTarget('field_parameter', index, f'{arm}.{field}')}))
                               for arm, declarations in self.analyzer.enums.get(content, {}).items()
                               for field, field_type in declarations if field_type in ('&Int', '&mut Int'))
                environment[key] = Value('owned', content, environment[name].candidates, fields,
                    handle_items=frozenset({ResultCandidate('vector_element', index)}) if is_handle_vector(content) else None)
        def capture(index, value, prefix=''):
            for slot, row in value.rows:
                path = prefix + slot
                if row.container_mode == 'mut':
                    key = f'\0referent:{index}:{path}'
                    self.referent_inputs[index, path] = row
                    environment[key] = row
                capture(index, row, path + '/')
        for index, (name, _, _) in enumerate(self.params):
            if isinstance(environment[name], Value):
                capture(index, environment[name])
        flow, tail = self.nodes(self.body, environment, valued=True)
        if 'next' in flow:
            self.collect(tail, self.node.line, environment)
        self.collect_owned_writes()
        handle_writes = self.handle_write_summary()
        layouts = self.shared_vector_returns
        layout = None
        if layouts and isinstance(layouts[0], tuple) and all(
                isinstance(row, tuple) and len(row) == len(layouts[0]) for row in layouts):
            layout = tuple(frozenset().union(*slots) for slots in zip(*layouts))
        reference_appends = []
        for index, paths in sorted(self.reference_append_paths.items()):
            first = paths[0]
            if first and all(path is not None and len(path) == len(first) for path in paths):
                reference_appends.append((index, tuple(frozenset().union(*slots) for slots in zip(*paths))))
        return FunctionResult(self.declared[0], self.declared[1], frozenset(self.returned) if self.declared[0] in ('owned', 'handle_option', 'buffered_handle_exchange', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) else frozenset(),
                              tuple(sorted(self.returned_fields.items())), self.fresh_variants,
                              frozenset(self.returned_references),
                              tuple((index, tuple(sorted(fields.items())))
                                    for index, fields in sorted(self.updated_parameters.items())), self.returned_payload,
                              tuple((index, path, tuple(sorted(fields.items())))
                                    for (index, path), fields in sorted(self.updated_referents.items())
                                    if fields != dict(reference_tree_fields(self.referent_inputs[index, path]))),
                              tuple((index, tuple((field, targets) for field, targets in sorted(fields.items())
                                                  if index in self.changed_shared_vectors or targets != dict(self.structure_inputs[index].fields)[field]))
                                    for index, fields in sorted(self.updated_structures.items())
                                    if index in self.changed_shared_vectors or fields != dict(self.structure_inputs[index].fields)),
                              next(iter(self.returned_vector_slots)) if len(self.returned_vector_slots) == 1 else None,
                              self.vector_write_summary(), handle_writes,
                              tuple((index, tuple(sorted(self.updated_handle_fields[index].items())))
                                    for index, _ in handle_writes if self.updated_handle_fields[index]),
                              vector_write_payloads=tuple((index, tuple(payloads)) for index, payloads in sorted(self.vector_write_payloads.items())),
                              exchange_payloads=self.returned_exchange_payloads,
                              exchange_values=self.returned_exchange_values, shared_vector_layout=layout,
                              vector_values=tuple(self.returned_vector_values),
                              shared_vector_passthrough=next(iter(self.shared_vector_passthroughs))
                              if len(self.shared_vector_passthroughs) == 1 else None,
                              reference_appends=tuple(reference_appends),
                              owned_fields=tuple(sorted(self.returned_owned_fields.items())),
                              task_sources=frozenset(self.returned_task_sources),
                              task_result_sources=frozenset(self.returned_task_result_sources),
                              task_result_fields=tuple(sorted(self.returned_task_result_fields.items())),
                              task_result_shapes=merge_task_result_shapes(self.returned_task_shape_values),
                              task_result_handle_pools=frozenset().union(*(
                                  value.task_result_handle_pools for value in self.returned_task_shape_values)),
                              stored_reference_parameters=frozenset(self.stored_reference_parameters),
                              task_wait_parameters=frozenset(self.task_wait_parameters),
                              task_forward_parameters=frozenset(self.task_forward_parameters),
                              task_forward_only=bool(self.task_forward_parameters) and self.task_forward_only,
                              absent_owned_payload=bool(self.returned_payload_absence)
                                  and all(self.returned_payload_absence),
                              task_suspension_fields=tuple((i, tuple(sorted(fields.items()))) for i, fields
                                  in sorted(self.returned_task_suspension_updates.items()))
                                  if self.returned_task_suspension_complete else None,
                              task_may_suspend=self.returned_task_may_suspend
                                  if self.returned_task_suspension_complete else None,
                              task_owned_updates=tuple((i, path, child) for (i, path), child
                                  in sorted(self.returned_task_owned_updates.items())),
                              task_vector_updates=tuple(sorted(self.returned_task_vector_updates.items())),
                              task_suspension_vectors=tuple(sorted(self.returned_task_suspension_vectors.items()))
                                  if self.returned_task_suspension_complete else None,
                              task_suspension_owned=tuple((i, path, child) for (i, path), child
                                  in sorted(self.returned_task_suspension_owned.items()))
                                  if self.returned_task_suspension_complete else None,
                              task_field_updates=tuple((i, tuple(sorted(fields.items()))) for i, fields
                                  in sorted(self.returned_task_field_updates.items())),
                              owned_field_writes=tuple((index, name, child) for (index, name), child
                                  in sorted(self.owned_field_writes.items())
                                  if any(item.kind != 'owned_field_input' for item in child.candidates)))

    def handle_write_summary(self):
        return tuple((index, tuple(sorted(candidates))) for index, candidates in sorted(self.updated_handles.items())
                     if candidates != {ResultCandidate('parameter', index)})

    def collect_vector_writes(self, visible, line):
        for index, (name, mode, typ) in enumerate(self.params):
            if mode != 'mut' or not is_payload_vector(typ):
                continue
            final = visible[name]
            history = final.input_item_history
            slots, exact, replacements, removals = (), True, (), ()
            if final.input_items_written or final.input_items_changed:
                if history is not None:
                    slots, replacements = history.appended, history.replaced
                    if history.tail or history.excluded:
                        removals = (history.tail, *history.excluded)
                else:
                    items = possible_handle_items(final.handle_items)
                    if items is None:
                        self.fail(line, 'mutation du vecteur emprunté sans provenance vérifiable')
                    slots = (frozenset(item for item in items
                                       if item.kind != 'vector_element' or item.parameter != index),)
                    exact = False
                if any(item.kind not in ('parameter', 'vector_element') and (
                        item.kind != 'fresh' or (item.source.kind != 'source_parameter'
                        and not (typ in INLINE_VECTOR_ELEMENTS and item.source.kind == 'local_value')))
                       for slot in (*slots, *(row for _, row in replacements)) for item in slot):
                    self.fail(line, 'le pool de l’élément doit survivre au vecteur emprunté')
            self.vector_write_paths.setdefault(index, []).append((slots, exact, replacements, removals))
            added = frozenset(item for slot in (*slots, *(row for _, row in replacements)) for item in slot)
            for payload in final.handle_payloads:
                if payload.candidates & added and (payload.fields or payload.owned_fields):
                    pending = [payload]
                    while pending:
                        part = pending.pop()
                        if any(self.has_nondurable_array_target(targets) for _, targets in part.fields):
                            self.fail(line, 'insertion refusée : cible empruntée non durable dans le vecteur injecté')
                        pending.extend(child for _, child in part.owned_fields)
                    self.vector_write_payloads.setdefault(index, {})[payload] = None

    def vector_write_summary(self):
        updates = []
        for index, paths in self.vector_write_paths.items():
            if not any(slots or replacements or removals or not exact
                       for slots, exact, replacements, removals in paths):
                continue
            positions = tuple(position for position, _ in paths[0][2])
            exact = all(known and len(slots) == len(paths[0][0])
                        and tuple(position for position, _ in replacements) == positions
                        and removals == paths[0][3]
                        for slots, known, replacements, removals in paths)
            replacements, removals = (), ()
            if exact:
                slots = tuple(tuple(sorted(frozenset().union(*alternatives)))
                              for alternatives in zip(*(slots for slots, _, _, _ in paths)))
                replacements = tuple((position, tuple(sorted(frozenset().union(
                    *(path[2][offset][1] for path in paths)))))
                    for offset, position in enumerate(positions))
                removals = paths[0][3]
            else:
                slots = (tuple(sorted({item for slots, _, replacements, _ in paths
                                       for slot in (*slots, *(row for _, row in replacements))
                                       for item in slot})),)
            updates.append((index, slots, exact, replacements, removals))
        return tuple(updates)

    def collect_owned_writes(self):
        for line, states in self.owned_exit_states:
            for index, initial in self.structure_inputs.items():
                final = states[index]
                def changed_paths(before, after, prefix=''):
                    for field, original in before.owned_fields:
                        value = dict(after.owned_fields).get(field, original)
                        path = prefix + field
                        for alternative in value.owned_alternatives or (value,):
                            if any(item.kind != 'owned_field_input' for item in alternative.candidates):
                                yield path, alternative
                            else:
                                yield path, replace(original, owned_fields=())
                                yield from changed_paths(original, alternative, path + '/')
                for name, child in changed_paths(initial, final):
                    pending = [(child, True)]
                    while pending:
                        candidate_field, top = pending.pop()
                        if not candidate_field.candidates or any(
                                not ((top and item.kind == 'owned_field_input')
                                     or item.kind in ('parameter', 'owned_projection')
                                     or (item.kind == 'fresh' and item.source.kind == 'source_parameter'))
                                for item in candidate_field.candidates):
                            self.fail(line, 'remplacement du champ propriétaire injecté : provenance non durable')
                        pending.extend((value, False) for _, value in candidate_field.owned_fields)
                    key = index, name
                    previous = self.owned_field_writes.get(key)
                    self.owned_field_writes[key] = merge_reference_values((previous, child)) if previous else child

    def collect(self, value, line, environment=None):
        if environment is not None:
            visible = environment.copy()
            for outer, shadows in reversed(self.blocks):
                visible = {name: restore_array_binding(shadows.get(name, visible[name]), visible) for name in outer}
            self.owned_exit_states.append((line, {index: visible[f'\0structure:{index}']
                                                  for index in self.structure_inputs}))
            for index, (_, mode, typ) in enumerate(self.params):
                if mode == 'mut' and typ.startswith('A<'):
                    final = visible[f'\0handle:{index}']
                    candidates = final.candidates
                    if not candidates or any(
                            (item.kind == 'fresh' and item.source.kind != 'source_parameter')
                            or (item.kind == 'parameter' and item.parameter != index
                                and self.params[item.parameter][1] != 'owned')
                            or item.kind not in ('fresh', 'parameter', 'vector_element')
                            for item in candidates):
                        self.fail(line, 'remplacement du handle injecté : provenance non durable')
                    if is_handle_vector(final.typ):
                        if final.handle_items is None and any(item.kind == 'fresh' for item in candidates):
                            self.fail(line, 'remplacement du handle injecté : inventaire neuf non vérifiable')
                        candidates = self.describe_vector_result(final, line)
                    self.updated_handles.setdefault(index, set()).update(candidates)
                    fields = self.updated_handle_fields.setdefault(index, {})
                    for field, targets in final.fields:
                        if any(target.kind == 'local' or (target.kind == 'parameter' and
                               self.params[target.parameter][1] not in ('ref', 'mut')) for target in targets):
                            self.fail(line, 'remplacement refusé : cible empruntée non durable dans le handle injecté')
                        fields[field] = fields.get(field, frozenset()) | targets
            self.collect_vector_writes(visible, line)
            for index, original in self.structure_inputs.items():
                final = visible[f'\0structure:{index}']
                if original.typ in REFERENCE_VECTORS:
                    history = final.input_item_history
                    self.reference_append_paths.setdefault(index, []).append(history.appended if history else None)
                    if final.input_items_changed:
                        self.changed_shared_vectors.add(index)
                fields = self.updated_structures.setdefault(index, {})
                for field, targets in final.fields:
                    if targets != dict(original.fields)[field]:
                        if any(target.kind not in ('field_parameter', 'parameter', 'detached_field_parameter')
                               or (self.params[target.parameter][1] == 'owned'
                                   and not (original.typ in REFERENCE_VECTORS
                                            and target.kind == 'detached_field_parameter'))
                               for target in targets):
                            self.fail(line, 'mise à jour refusée : cible non durable dans le champ injecté')
                    fields[field] = fields.get(field, frozenset()) | targets
            for (index, path), original in self.referent_inputs.items():
                final = visible[f'\0referent:{index}:{path}']
                fields = self.updated_referents.setdefault((index, path), {})
                for slot, targets in reference_tree_fields(final):
                    if self.has_nondurable_array_target(targets):
                        self.fail(line, 'mise à jour refusée : cible locale non durable dans une ligne injectée')
                    fields[slot] = fields.get(slot, frozenset()) | targets
            for index, (name, mode, typ) in enumerate(self.params):
                if mode == 'array_mut' and reference_array_shape(typ):
                    fields = self.updated_parameters.setdefault(index, {})
                    for slot, targets in reference_tree_fields(visible[f'\0parameter:{index}']):
                        if self.has_nondurable_array_target(targets):
                            self.fail(line, 'mise à jour refusée : cible locale non durable dans le conteneur')
                        fields[slot] = fields.get(slot, frozenset()) | targets
        mode, typ = self.declared
        if mode in UTF8_BORROW_MODES or mode == 'vector_split':
            if not isinstance(value, Value) or (value.mode, value.typ) != (mode, typ):
                self.fail(line, f"retour de '{self.name}' : attendu {mode} ({typ})")
            targets = borrowed_targets(value)
            if mode == 'vector_split' and not targets:
                self.fail(line, 'retour de paire sans provenance durable')
            for target in targets:
                if target.kind in ('utf8_parameter', 'array_parameter'):
                    continue
                if target.kind == 'task_capture_parameter' and self.params[target.parameter][1] in ('task', 'execution'):
                    continue
                if target.kind in ('string_parameter', 'vector_parameter') and self.params[target.parameter][1] in (
                        ('mut',) if mode in (*VECTOR_MUT_SLICE_MODES.values(), 'vector_split') else ('ref', 'mut')):
                    continue
                self.fail(line, 'retour UTF-8 refusé : source empruntée non durable dans le scope parent')
            self.returned_references.update(targets)
            return
        if mode in ('task', 'execution'):
            if mode == 'execution':
                value = self.public_handle_value(value, typ, line)
            if not isinstance(value, Value) or (value.mode, value.typ) != (mode, typ):
                self.fail(line, f"retour de '{self.name}' : {mode} de {typ} attendu")
            if any(source.kind not in ('source_parameter', 'allocation_parameter', 'vector_element_parameter', 'allocation_field_parameter', 'task_parameter', 'task_result_parameter', 'task_result_field_parameter', 'task_output', 'task_output_parameter')
                   for source in value.task_sources | value.task_result_sources):
                self.fail(line, 'retour de tâche refusé : le pool de capture ne survit pas au retour')
            self.returned_task_sources.update(value.task_sources)
            self.returned_task_result_sources.update(value.task_result_sources)
            self.returned_task_shape_values.append(value)
            for path, sources in value.task_result_fields:
                self.returned_task_result_fields[path] = self.returned_task_result_fields.get(path, frozenset()) | sources
            self.task_forward_parameters.update(value.task_parameters)
            self.task_forward_only &= value.task_forward_only
            self.collect_deferred_owned(value.deferred_owned_updates, self.returned_task_owned_updates, line)
            self.collect_deferred_vectors(value.deferred_vector_updates, self.returned_task_vector_updates, line)
            if (value.deferred_suspension_updates is None or value.task_may_suspend is None
                    or value.deferred_suspension_owned is None or value.deferred_suspension_vectors is None):
                self.returned_task_suspension_complete = False
            else:
                self.collect_deferred_vectors(value.deferred_suspension_vectors, self.returned_task_suspension_vectors, line)
                self.collect_deferred_owned(value.deferred_suspension_owned,
                                            self.returned_task_suspension_owned, line)
                self.returned_task_may_suspend |= value.task_may_suspend
                for carrier, fields in value.deferred_suspension_updates:
                    for target in borrowed_targets(carrier):
                        if target.kind != 'parameter' or self.params[target.parameter][1] != 'mut':
                            self.fail(line, 'préfixe de tâche : porteur de modification non durable')
                        output = self.returned_task_suspension_updates.setdefault(target.parameter, {})
                        for field, targets in fields:
                            if any(t.kind not in ('parameter', 'field_parameter', 'detached_field_parameter') for t in targets):
                                self.fail(line, 'préfixe de tâche : cible de modification non durable')
                            output[field] = output.get(field, frozenset()) | targets
            for carrier, fields in value.deferred_field_updates:
                for target in borrowed_targets(carrier):
                    if target.kind != 'parameter' or self.params[target.parameter][1] != 'mut':
                        self.fail(line, 'retour de tâche : porteur de modification non durable')
                    output = self.returned_task_field_updates.setdefault(target.parameter, {})
                    for field, targets in fields:
                        if any(t.kind not in ('parameter', 'field_parameter', 'detached_field_parameter') for t in targets):
                            self.fail(line, 'retour de tâche : cible de modification non durable')
                        output[field] = output.get(field, frozenset()) | targets
            for key, targets in value.fields:
                if any(not (
                        target.kind in ('parameter', 'exclusive_join_parameter', 'inline_field_parameter', 'indirect_field_parameter')
                        and self.params[target.parameter][1] in ('ref', 'mut')
                        or target.kind == 'array_parameter'
                        and self.params[target.parameter][1] in ('array_ref', 'array_mut')
                        or target.kind == 'stored_array_parameter'
                        and self.params[target.parameter][1] in ('array_refs', 'array_ref', 'array_mut')
                        or target.kind == 'reserved_stored_array_parameter'
                        and self.params[target.parameter][1] in ('array_ref', 'array_mut')
                        or target.kind == 'detached_field_parameter'
                        and self.params[target.parameter][1] in ('ref', 'mut', 'owned')
                        or target.kind == 'owned_capture_field'
                        and self.params[target.parameter][1] in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES)
                        or target.kind == 'task_capture_parameter'
                        and self.params[target.parameter][1] in ('task', 'execution')
                        or target.kind == 'utf8_parameter'
                        and self.params[target.parameter][1] in ASYNC_CAPTURE_VIEW_MODES
                        or target.kind in ('string_parameter', 'vector_parameter')
                        and self.params[target.parameter][1] in ('ref', 'mut'))
                       for target in targets):
                    self.fail(line, 'retour de tâche refusé : cible empruntée non durable dans le scope parent')
                self.returned_fields[key] = self.returned_fields.get(key, frozenset()) | targets
            return
        if mode not in ('owned', 'handle_option', 'buffered_handle_exchange', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'ref', 'mut', 'array_refs'):
            return
        value = value if isinstance(value, Value) else UNKNOWN
        if self.declared[0] in ('ref', 'mut') and value.mode == 'array_refs' and value.container_borrow:
            for slot, targets in reference_tree_fields(value):
                self.returned_fields[slot] = self.returned_fields.get(slot, frozenset()) | targets
            value = replace(value, mode=value.container_mode)
        if self.declared[0] in ('ref', 'mut') and value.mode in ('array_ref', 'array_mut'):
            value = replace(value, mode=value.mode[6:])
        if self.declared[0] in ('ref', 'mut'):
            self.returned_payload |= value.payload_reference
            vector_slot = None
            if value.handle_slot is not None:
                origins, index = value.handle_slot
                if len(origins) == 1:
                    root = next(iter(origins))
                    if isinstance(root, tuple) and root[0] == 'vector_parameter':
                        vector_slot = (root[1], index)
            self.returned_vector_slots.add(vector_slot)
        if self.declared[0] == 'ref' and value.mode == 'mut':
            value = Value('ref', value.typ, reference_targets=borrowed_targets(value), payload_reference=value.payload_reference)
        if value.mode != self.declared[0]:
            self.fail(line, f"retour de '{self.name}' : attendu {self.declared[0]}, reçu {value.mode}")
        if value.typ != self.declared[1]:
            self.fail(line, f'retour conditionnel : allocation {self.declared[1]} attendue, reçu {value.typ}')
        if self.declared[0] in ('ref', 'mut'):
            targets = borrowed_targets(value)
            if not targets:
                self.fail(line, 'retour sans provenance symbolique vérifiable')
            for target in targets:
                if target.kind == 'local':
                    self.fail(line, 'retour refusé : cible empruntée non durable dans le scope parent')
                parameter_mode = self.params[target.parameter][1]
                if target.kind == 'async_handle_result' and parameter_mode == 'async_execution':
                    continue
                if target.kind == 'task_capture_parameter' and parameter_mode in ('task', 'execution'):
                    continue
                if target.kind == 'mutable_vector_parameter':
                    if parameter_mode not in ('ref', 'mut') or (mode == 'mut' and parameter_mode != 'mut'):
                        self.fail(line, 'retour de case : capacité du vecteur insuffisante')
                    continue
                if target.kind == 'detached_field_parameter':
                    if self.declared[0] != 'ref' or parameter_mode not in ('ref', 'mut', 'owned'):
                        self.fail(line, 'retour de champ partagé incompatible avec le porteur')
                    continue
                if target.kind == 'shared_field_parameter':
                    if self.declared[0] != 'ref' or parameter_mode not in ('ref', 'mut'):
                        self.fail(line, 'retour de champ partagé : porteur emprunté requis')
                    continue
                if target.kind == 'moved_field_parameter':
                    if parameter_mode != 'owned':
                        self.fail(line, 'retour de champ déplacé : porteur reçu par transfert requis')
                    continue
                if target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
                    allowed = parameter_mode in ('array_refs', 'array_ref', 'array_mut')
                    if self.declared[0] == 'mut':
                        allowed = parameter_mode == 'array_mut' and reference_array_shape(self.params[target.parameter][2])[0] == 'mut'
                    if not allowed:
                        self.fail(line, 'retour de réemprunt refusé : la case mutable ne survit pas')
                    continue
                if target.kind == 'utf8_parameter' and parameter_mode == 'vector_ints' and self.declared[0] == 'ref':
                    continue
                if target.kind == 'array_parameter':
                    if parameter_mode not in ('array_ref', 'array_mut') or (self.declared[0] == 'mut' and parameter_mode != 'array_mut'):
                        self.fail(line, 'retour emprunté incompatible avec le paramètre tableau')
                    if self.declared[1] == 'Int' and reference_array_shape(self.params[target.parameter][2]):
                        self.fail(line, 'prototype : retour synchrone d’un prêt de join sur tableau de références non pris en charge')
                    continue
                if parameter_mode not in ('ref', 'mut'):
                    self.fail(line, 'retour refusé : cible empruntée non durable dans le scope parent')
                if target.kind == 'field_parameter' and self.params[target.parameter][1] != 'mut':
                    self.fail(line, 'retour de match : porteur emprunté avec &mut requis')
                if self.declared[0] == 'mut' and self.params[target.parameter][1] != 'mut':
                    self.fail(line, 'retour mutable : paramètre mutable requis')
            self.returned_references.update(targets)
            return
        if self.declared[0] == 'array_refs':
            for slot, targets in reference_tree_fields(value):
                if not targets or any(
                        target.kind not in ('array_parameter', 'stored_array_parameter', 'parameter', 'field_parameter',
                                            'moved_field_parameter', 'shared_field_parameter',
                                            'reserved_stored_array_parameter', 'inline_field_parameter',
                                            'detached_field_parameter', 'indirect_field_parameter')
                        or (target.kind in ('parameter', 'inline_field_parameter', 'indirect_field_parameter')
                            and self.params[target.parameter][1] not in ('ref', 'mut'))
                        or (target.kind == 'detached_field_parameter' and self.params[target.parameter][1] not in ('ref', 'mut', 'owned'))
                        or (target.kind == 'field_parameter' and self.params[target.parameter][1] != 'mut')
                        or (target.kind == 'moved_field_parameter' and self.params[target.parameter][1] != 'owned')
                        or (target.kind == 'shared_field_parameter' and self.params[target.parameter][1] not in ('ref', 'mut'))
                        or (target.kind == 'reserved_stored_array_parameter'
                            and self.params[target.parameter][1] not in ('array_ref', 'array_mut'))
                        for target in targets):
                    self.fail(line, 'retour refusé : cible de case empruntée non durable')
                self.returned_fields[slot] = self.returned_fields.get(slot, frozenset()) | targets
            return
        absent_payload = value.mode in ('join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) and value.absent_owned_payload
        if not value.candidates and value.mode != 'handle_option' and not absent_payload:
            self.fail(line, 'retour sans provenance symbolique vérifiable')
        self.returned_payload_absence.append(absent_payload and not value.candidates)
        candidates = self.describe_vector_result(value, line)
        for candidate in candidates:
            if candidate.kind == 'fresh' and candidate.source.kind == 'local':
                self.fail(line, f"transfert refusé : la source '{candidate.source.name}' ne survit pas à ce bloc")
        self.returned.update(candidates)
        if is_handle_vector(typ):
            items = possible_handle_items(value.handle_items)
            self.returned_vector_values.update((item, None) for item in value.handle_payloads
                if (items is None or item.candidates & items) and (item.fields or item.owned_fields))
        for name, child in (() if is_handle_vector(typ) else value.owned_fields):
            previous = self.returned_owned_fields.get(name)
            self.returned_owned_fields[name] = merge_reference_values((previous, child)) if previous else child
        if typ in REFERENCE_VECTORS:
            self.shared_vector_returns.append(value.handle_items)
            candidate = next(iter(candidates)) if len(candidates) == 1 else None
            self.shared_vector_passthroughs.add(
                candidate.parameter if candidate is not None and candidate.kind == 'parameter'
                and not value.input_items_changed else None)
        if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
            previous = self.returned_exchange_payloads or (frozenset(), frozenset())
            self.returned_exchange_payloads = tuple(a | b for a, b in zip(previous, value.exchange_payloads))
            if mode == 'buffered_handle_exchange':
                values = value.exchange_values or tuple(restore_handle_payload(Value('owned', exchange_element(typ), arm), value)
                               for arm in value.exchange_payloads)
                if value.exchange_values or self.returned_exchange_values or any(value.fields or value.owned_fields for value in values):
                    self.returned_exchange_values = (tuple(merge_owned_values((a, b)) for a, b in
                        zip(self.returned_exchange_values, values)) if self.returned_exchange_values else values)
        for name, targets in value.fields:
            for target in targets:
                if (target.kind in ('local', 'mutable_vector_parameter') or
                        target.kind == 'parameter' and self.params[target.parameter][1] not in ('ref', 'mut')):
                    self.fail(line, 'retour refusé : cible empruntée non durable dans le scope parent')
            self.returned_fields[name] = self.returned_fields.get(name, frozenset()) | targets
        self.fresh_variants |= value.fresh_variants

    def describe_vector_result(self, value, line):
        candidates = value.candidates
        fresh_vector = is_handle_vector(value.typ) and any(candidate.kind == 'fresh' for candidate in candidates)
        items = possible_handle_items(value.handle_items)
        history = value.input_item_history
        if value.input_items_written and history is not None:
            items = frozenset().union(*history.appended, *(slot for _, slot in history.replaced))
        if is_handle_vector(value.typ) and (value.input_items_written or (fresh_vector and items)):
            if items is None:
                self.fail(line, 'retour d’un vecteur injecté après écriture sans contrat de cases')
            added = tuple(sorted({item.parameter for item in items if item.kind == 'parameter'}))
            if any(item.kind not in ('parameter', 'vector_element')
                   and not (item.kind == 'fresh' and item.source.kind == 'source_parameter')
                   for item in items):
                self.fail(line, 'retour d’un vecteur injecté après écriture sans source durable vérifiable')
            pools = tuple(sorted({item.source.index for item in items if item.kind == 'fresh'}))
            returned = set()
            for candidate in candidates:
                layout, replacements, removals = (), (), UNKNOWN_VECTOR_REMOVALS
                if candidate.kind == 'fresh' and isinstance(value.handle_items, tuple):
                    layout = value.handle_items
                elif candidate.kind == 'parameter' and history is not None:
                    layout, replacements = history.appended, history.replaced
                    removals = (history.tail, *history.excluded)
                returned.add(replace(
                    candidate, vector_removals=removals, vector_added_parameters=added,
                    vector_added_pools=pools, vector_layout=tuple(tuple(sorted(slot)) for slot in layout),
                    vector_replacements=tuple((index, tuple(sorted(slot))) for index, slot in replacements),
                    vector_added_elements=tuple(sorted(
                        item for item in items if item.kind == 'vector_element'
                        and (candidate.kind != 'parameter' or item.parameter != candidate.parameter)))))
            candidates = frozenset(returned)
        elif is_handle_vector(value.typ) and value.input_items_changed:
            history = value.input_item_history
            if value.handle_items is None or any(candidate.kind != 'parameter' for candidate in candidates):
                self.fail(line, 'retour d’un vecteur injecté après extraction sans historique vérifiable')
            removals = (history.tail, *history.excluded) if history is not None else UNKNOWN_VECTOR_REMOVALS
            candidates = frozenset(replace(candidate, vector_removals=removals) for candidate in candidates)
        return candidates

    @staticmethod
    def resolve_vector_slot(slot, actuals):
        items = set()
        for item in slot:
            if item.kind == 'fresh' and item.source.kind == 'local_value':
                items.add(item)
                continue
            actual = actuals[item.parameter if item.kind != 'fresh' else item.source.index]
            if item.kind == 'parameter':
                candidates = actual.candidates
            elif item.kind == 'vector_element':
                candidates = vector_result_candidates(
                    actual, item.item_index, last=item.item_index == VECTOR_LAST_ITEM,
                    excluded=item.excluded_items, tail_offset=item.tail_offset)
            else:
                candidates = {ResultCandidate('fresh', source=actual)} if isinstance(actual, SourceOrigin) else None
            items.update(candidates or {UNKNOWN_HANDLE_ITEM})
        return frozenset(items)

    def apply_vector_result_candidates(self, candidates, actuals, site):
        vectors = []
        for item in candidates:
            vector = (actuals[item.parameter] if item.kind == 'parameter'
                      else Value('owned', HANDLE_VECTOR, structure_origins=frozenset({site}),
                                 handle_items=()))
            if item.vector_removals or item.vector_layout or item.vector_replacements:
                history = vector.input_item_history
                if history is not None and item.vector_removals:
                    history = (None if item.vector_removals == UNKNOWN_VECTOR_REMOVALS
                               else history.compose(item.vector_removals))
                items = remaining_handle_items(vector.handle_items, item.vector_removals)
                adds_items = bool(item.vector_added_parameters or item.vector_added_pools
                                  or item.vector_added_elements)
                if (items is not None and adds_items and item.vector_removals == UNKNOWN_VECTOR_REMOVALS
                        and not (item.vector_layout or item.vector_replacements)):
                    items |= frozenset(c for index in item.vector_added_parameters
                                       for c in actuals[index].candidates)
                    items |= frozenset(
                        ResultCandidate('fresh', source=actuals[index])
                        if isinstance(actuals[index], SourceOrigin) else UNKNOWN_HANDLE_ITEM
                        for index in item.vector_added_pools)
                    for added in item.vector_added_elements:
                        candidates_from_donor = vector_result_candidates(
                            actuals[added.parameter], added.item_index,
                            last=added.item_index == VECTOR_LAST_ITEM,
                            excluded=added.excluded_items, tail_offset=added.tail_offset)
                        items |= candidates_from_donor or {UNKNOWN_HANDLE_ITEM}
                if item.vector_replacements:
                    replacements = tuple((index, self.resolve_vector_slot(slot, actuals))
                                         for index, slot in item.vector_replacements)
                    if isinstance(items, tuple):
                        items = replace_handle_positions(items, replacements)
                    elif items is not None:
                        items |= frozenset().union(*(slot for _, slot in replacements))
                    if history is not None:
                        for index, slot in replacements:
                            history = history.replace_slot(index, slot)
                            if history is None:
                                break
                if item.vector_layout:
                    suffix = tuple(self.resolve_vector_slot(slot, actuals) for slot in item.vector_layout)
                    if item.kind == 'fresh':
                        items = suffix
                    elif isinstance(items, tuple):
                        items += suffix
                    elif items is not None:
                        items |= frozenset().union(*suffix)
                    if history is not None:
                        history = replace(history, appended=(*history.appended, *suffix))
                vector = replace(vector, handle_items=items,
                                 input_item_history=history,
                                 input_items_written=vector.input_items_written or bool(
                                     adds_items and any(
                                         c.kind == 'parameter' for c in vector.candidates)),
                                 input_items_changed=vector.input_items_changed or any(
                                     c.kind == 'parameter' for c in vector.candidates))
            vectors.append(vector)
        return vectors

    def condition(self, condition, environment, line):
        flow = {'next'}
        if condition[0] == 'compare':
            for expr in condition[2:]:
                if 'next' not in flow:
                    break
                part, _ = self.expression(expr, environment, line)
                flow = (flow - {'next'}) | part
        return flow

    def block(self, nodes, environment, valued=False, bindings=None, expected_array=None):
        local = environment.copy()
        shadows = {}
        if bindings:
            shadows.update((name, environment[name]) for name in bindings if name in environment)
            local.update(bindings)
        self.blocks.append((environment, shadows))
        try:
            flow, value = self.nodes(nodes, local, valued, shadows, expected_array)
        finally:
            self.blocks.pop()
        if 'next' in flow:
            for name in environment:
                environment[name] = restore_array_binding(shadows.get(name, local[name]), local)
        return flow, value

    def join_environments(self, environment, branches):
        def complete_input(value, initial):
            if value.owned_alternatives:
                return merge_owned_values([complete_input(item, initial) for item in value.owned_alternatives])
            if not any(item.kind in ('parameter', 'owned_field_input') for item in value.candidates):
                return value
            fields = dict(value.owned_fields)
            for key, original in initial.owned_fields:
                fields[key] = complete_input(fields[key], original) if key in fields else original
            return replace(value, owned_fields=tuple(fields.items()))

        for name in environment:
            values = [branch[name] for flow, branch in branches if 'next' in flow]
            if values and all(isinstance(value, Value) for value in values):
                if name.startswith('\0structure:'):
                    initial = self.structure_inputs[int(name.split(':', 1)[1])]
                    values = [complete_input(value, initial) for value in values]
                first = values[0]
                environment[name] = Value(
                    first.mode, first.typ, frozenset(c for value in values for c in value.candidates),
                    merge_fields(values), frozenset(v for value in values for v in value.fresh_variants),
                    frozenset(t for value in values for t in value.reference_targets), any(value.payload_reference for value in values), frozenset(o for value in values for o in value.container_origins), merge_container_positions(values), any(value.container_borrow for value in values), next(iter(values)).container_mode, merge_reference_rows(values))
                if all(value.storage_owner == first.storage_owner for value in values):
                    environment[name] = replace(environment[name], storage_owner=first.storage_owner)
                environment[name] = replace(
                    environment[name],
                    owned_fields=merge_reference_rows(values, 'owned_fields'),
                    owned_path=first.owned_path if all(value.owned_path == first.owned_path for value in values) else (),
                    structure_choices=merge_structure_choices(values),
                    copy_candidates=frozenset(candidate for value in values for candidate in value.copy_candidates),
                    structure_origins=frozenset(origin for value in values for origin in value.structure_origins),
                    handle_items=merge_handle_items(values),
                    handle_payloads=tuple(dict.fromkeys(item for value in values for item in value.handle_payloads)),
                    input_item_history=merge_input_item_history(values),
                    input_items_changed=any(value.input_items_changed for value in values),
                    input_items_written=any(value.input_items_written for value in values),
                    handle_slot=first.handle_slot if all(value.handle_slot == first.handle_slot for value in values) else None,
                    task_sources=frozenset(source for value in values for source in value.task_sources),
                    task_result_sources=frozenset(source for value in values for source in value.task_result_sources),
                    task_result_fields=merge_task_result_fields(values),
                    task_result_shapes=merge_task_result_shapes(values),
                    task_result_handle_pools=frozenset().union(*(value.task_result_handle_pools for value in values)),
                    pending_structure_calls=frozenset(call for value in values for call in value.pending_structure_calls),
                    pending_structure_complete=all(value.pending_structure_complete for value in values),
                    deferred_map_paths=merge_deferred_map_paths(values),
                    task_forward_only=all(value.task_forward_only for value in values),
                    task_parameters=frozenset(index for value in values for index in value.task_parameters),
                    deferred_field_updates=frozenset(update for value in values for update in value.deferred_field_updates),
                    deferred_guarded_writes=frozenset(update for value in values for update in value.deferred_guarded_writes),
                    deferred_definite_fields=merge_deferred_definite_fields(values),
                    deferred_suspension_updates=merge_task_suspensions(values),
                    deferred_owned_updates=merge_task_owned_updates(values, 'deferred_owned_updates'),
                    deferred_vector_updates=frozenset(update for value in values for update in value.deferred_vector_updates),
                    deferred_suspension_owned=merge_task_owned_updates(values, 'deferred_suspension_owned'),
                    deferred_suspension_vectors=merge_task_vector_updates(values, 'deferred_suspension_vectors'),
                    task_may_suspend=merge_task_may_suspend(values),
                    absent_owned_payload=all(value.absent_owned_payload for value in values))

    def remember_handle_payload(self, environment, receiver, item):
        vector = environment.get(receiver)
        if not isinstance(vector, Value) or not is_payload_vector(vector.typ):
            return
        if vector.typ in INLINE_VECTOR_ELEMENTS:
            def owned_tree(value, seen=frozenset()):
                if value.typ in seen:
                    return value
                children = dict(value.owned_fields)
                for arm, fields in self.analyzer.enums.get(value.typ, {}).items():
                    for field, declared in fields:
                        if declared.startswith('A<'):
                            key = arm + '.' + field
                            child = children.get(key) or self.project_owned_value(value, key, declared[2:-1])
                            children[key] = owned_tree(child, seen | {value.typ})
                return replace(value, owned_fields=tuple(children.items()))
            item = owned_tree(item)
        owner = vector.storage_owner or receiver
        for name in (owner, receiver):
            root = environment.get(name)
            if isinstance(root, Value):
                environment[name] = replace(root, handle_payloads=tuple(dict.fromkeys((*root.handle_payloads, item))))

    def publish_handle_exchange(self, environment, exchange, *, exact=True):
        receiver, index, incoming, append = exchange
        vector = environment.get(receiver)
        if not isinstance(vector, Value) or not is_payload_vector(vector.typ):
            return
        owner = vector.storage_owner
        alias = vector if owner is not None else None
        if alias is not None:
            root = environment.get(owner)
            if not isinstance(root, Value) or root.structure_origins != alias.structure_origins:
                self.invalidate_handle_items(environment, writing=True)
                return
            receiver, vector = owner, root
        items = handle_items_after_exchange(vector.handle_items, index, incoming, append, weak=not exact)
        if not exact:
            items = possible_handle_items(items)
        history = vector.input_item_history if exact else None
        if history is not None:
            history = (replace(history, appended=(*history.appended, incoming)) if append
                       else history.replace_slot(index, incoming))
        environment[receiver] = replace(vector, handle_items=items, input_item_history=history,
                                        input_items_written=vector.input_items_written or any(
                                            candidate.kind == 'parameter' for candidate in vector.candidates))
        if alias is not None:
            name = exchange[0]
            environment[name] = replace(environment[receiver], mode=alias.mode, storage_owner=owner)

    def extract_vector_item(self, environment, receiver, index=None, *, last=False, optional=False):
        name = receiver[1] if receiver[0] == 'name' else None
        vector = environment.get(name)
        alias = vector if isinstance(vector, Value) and vector.storage_owner is not None else None
        if alias is not None:
            name = alias.storage_owner
            vector = environment.get(name)
            if not isinstance(vector, Value) or vector.structure_origins != alias.structure_origins:
                self.invalidate_handle_items(environment, writing=True)
                return extracted_handle(None)
        items = vector.handle_items if isinstance(vector, Value) else None
        candidates = vector_result_candidates(vector, index, last=last)
        typ = vector_payload_element(vector.typ) if isinstance(vector, Value) else 'Int'
        result = (Value('handle_option', typ) if optional and items == ()
                  and not candidates else extracted_handle(candidates, typ))
        result = restore_handle_payload(result, vector)
        if last:
            index = last_handle_index(items)
        if isinstance(vector, Value):
            history = vector.input_item_history
            if history is not None:
                history = history.remove(index, last)
            environment[name] = replace(vector, handle_items=handle_items_after_removal(items, index),
                                               input_item_history=history,
                                               input_items_changed=vector.input_items_changed or any(
                                                   candidate.kind == 'parameter' for candidate in vector.candidates))
        if alias is not None:
            environment[receiver[1]] = replace(environment[name], mode=alias.mode, storage_owner=name)
        return result

    def refine_handle_branches(self, condition, yes, no):
        if condition[0] != 'compare':
            return
        operand = condition[2]
        if operand[0] == 'array_handle_exchange_status':
            exchange = yes[operand[1][1]].handle_exchange
            if exchange is not None:
                self.publish_handle_exchange(yes, exchange)
        elif operand[0] == 'array_handle_len':
            name = operand[1][1]
            vector = no.get(name)
            if isinstance(vector, Value):
                no[name] = replace(vector, handle_items=())

    def invalidate_handle_items(self, environment, *, writing=False):
        for bindings in (environment, *(shadows for _, shadows in self.blocks)):
            for name, value in bindings.items():
                if isinstance(value, Value) and is_payload_vector(value.typ):
                    bindings[name] = replace(value, handle_items=None, input_item_history=None,
                                             input_items_written=value.input_items_written or (writing and any(
                                                 candidate.kind == 'parameter' for candidate in value.candidates)))

    def store_handle_slot(self, target, incoming, environment):
        if target.handle_slot is None:
            self.invalidate_handle_items(environment, writing=True)
            return
        origins, index = target.handle_slot
        if any(isinstance(value, Value) and is_handle_vector(value.typ) and value.structure_origins & origins
               for _, shadows in self.blocks for value in shadows.values()):
            self.invalidate_handle_items(environment, writing=True)
            return
        roots = [(name, value) for name, value in environment.items()
                 if isinstance(value, Value) and is_handle_vector(value.typ) and value.structure_origins & origins]
        if not roots:
            self.invalidate_handle_items(environment, writing=True)
            return
        candidates = incoming.candidates if isinstance(incoming, Value) else frozenset()
        candidates = candidates or frozenset({UNKNOWN_HANDLE_ITEM})
        for name, root in roots:
            exact = len(roots) == len(origins) == 1 and root.structure_origins == origins
            items = handle_items_after_exchange(root.handle_items, index, candidates, weak=not exact)
            history = root.input_item_history
            history = history.replace_slot(index, candidates) if exact and history is not None else None
            environment[name] = replace(root, handle_items=items, handle_payloads=tuple(dict.fromkeys((*root.handle_payloads, incoming))), input_item_history=history,
                                        input_items_written=root.input_items_written or any(
                                            candidate.kind == 'parameter' for candidate in root.candidates))

    @staticmethod
    def update_handle(environment, target, incoming):
        owner = target.storage_owner
        environment[owner] = incoming
        if owner.startswith('\0handle:'):
            return
        for name, alias in environment.items():
            if isinstance(alias, Value) and alias.typ == target.typ and alias.storage_owner == owner:
                environment[name] = replace(alias, reference_targets=borrowed_targets(incoming))

    def reference_value_fields(self, value, typ, line):
        shape = reference_array_shape(typ)
        if shape:
            if not isinstance(value, Value) or value.mode != 'array_refs' or value.typ != typ:
                self.fail(line, 'une écriture doit conserver le type de la ligne')
            return tuple(dict(value.fields).get(str(slot), frozenset()) for slot in range(shape[1]))
        mode, pointee = reference_type(typ)
        if isinstance(value, Value) and value.mode == 'array_refs' and value.container_borrow:
            if value.typ != pointee or value.container_mode != mode:
                self.fail(line, 'une écriture doit conserver le type et le mode de référence de la case')
            return (borrowed_targets(value),)
        if not isinstance(value, Value) or value.mode not in (mode, 'array_' + mode) or value.typ != pointee:
            self.fail(line, 'une écriture doit conserver le type de référence de la case')
        return (borrowed_targets(value),)

    def store_reference_array(self, place, rhs, environment, line):
        name, indices = reference_array_path(place)
        flow = {'next'}
        for index in indices:
            part, _ = self.expression(index, environment, line)
            flow = (flow - {'next'}) | part
            if 'next' not in flow:
                return flow
        part, incoming = self.expression(rhs, environment, line)
        flow = (flow - {'next'}) | part
        if 'next' in flow:
            root = environment[name]
            root, typ, positions = reference_value_place(root, indices)
            replacement = self.reference_value_fields(incoming, typ, line)
            _, updated = replace_reference_fields(root.fields, positions, replacement)
            update_array_aliases(environment, name, updated, root, replace_reference_rows(root, positions, incoming))
        return flow

    def expression(self, expr, environment, line, expected_array=None, *, call_site=None):
        if expr is None:
            return {'next'}, VOID
        if expr[0] == 'array_drop_result':
            inner = expr[1]
            nominal = getattr(environment.get(inner[1][1]), 'typ', None)
            expr = consumed_result_expression(inner, nominal)
        if expr[0] == 'task_join':
            nominal = getattr(environment.get(expr[1]), 'typ', None)
            expr = method_candidate(expr, nominal, self.analyzer.functions) or expr
        op = expr[0]
        shape = fixed_array_shape(expected_array) if expected_array is not None else None
        if expr == ('array_literal',) and shape is not None and shape[1] == 0:
            mode = 'array_refs' if reference_array_shape(expected_array) else 'array'
            return {'next'}, Value(mode, expected_array)
        if op == 'task_spawn':
            flow, task = self.expression(expr[1], environment, line)
            if isinstance(task, Value) and task.mode == 'task':
                return flow, replace(task, mode='execution')
            return flow, UNKNOWN
        if op in ('task_join', 'task_join_value'):
            if op == 'task_join':
                flow, execution = {'next'}, self.lookup(expr[1], environment, line)
            else:
                flow, execution = self.expression(expr[1], environment, line)
            if isinstance(execution, Value) and execution.mode == 'execution':
                self.task_wait_parameters.update(execution.task_parameters)
                self.apply_deferred_field_updates(execution, environment, line)
                declaration = self.analyzer.async_definition(execution.typ)
                mode, typ = declaration.args[2]
                if mode in ('ref', 'mut'):
                    from async_lowering import borrowed_result_parameters, int_reference_row
                    indexes = borrowed_result_parameters(declaration, self.analyzer.async_functions, self.fail, {},
                                                         sync_result_contract=self.analyzer.sync_result_contract)
                    row_payload = any(index in indexes and int_reference_row(capture_type, capture_mode)
                                      for index, (_, capture_mode, capture_type) in enumerate(declaration.args[1]))
                    return flow, Value('join_' + mode, typ, reference_targets=execution.reference_targets,
                                       payload_reference=row_payload)
                if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
                    value = self.async_owned_result_value(mode, typ, execution.task_result_sources, execution.task_result_fields)
                    outer = exchange_join_mode(typ if mode == 'buffered_handle_exchange' else EXCHANGE_JOIN_TYPES[mode])
                    return flow, replace(value, mode=outer, typ=exchange_payload_type(outer))
                if mode in ('owned', 'join_owned', *OWNED_JOIN_TYPES, 'handle_option', *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
                    if mode in ('owned', *OWNED_JOIN_TYPES):
                        kind = owned_join_mode(mode)
                    else:
                        inner = OPTION_JOIN_TYPES[mode] if mode in OPTION_JOIN_TYPES else (f'Option<{typ}>' if declaration.join_storage_result == 'local' else f'Option<A<{typ}>>')
                        kind = option_join_mode(inner)
                    effects = getattr(declaration, 'field_effect_summary', None)
                    if effects is not None and effects.complete and (
                            effects.may_complete is False or
                            effects.completion_result.absent_owned_payload):
                        # Only a completed analysis proves that Ok carries no
                        # allocation. An empty/unknown source set is not proof.
                        return flow, Value(kind, typ, absent_owned_payload=True)
                    result = self.async_owned_result_value(kind, typ, execution.task_result_sources, execution.task_result_fields, shapes=execution.task_result_shapes)
                    from async_result_storage import borrowed_result_fields
                    fields = []
                    for field, targets in borrowed_result_fields(declaration):
                        origins = set()
                        for target in targets:
                            selector = result_capture_selector(target)
                            if selector is None:
                                origins.add(BorrowTarget('local'))
                            else:
                                for _, capture in capture_fields(execution.fields, selector):
                                    origins.update(capture)
                        fields.append((field, frozenset(origins)))
                    if is_handle_vector(typ):
                        def attach(value, prefix):
                            children = tuple((key, attach(child, prefix + key + '/')) for key, child in value.owned_fields)
                            return replace(value, fields=tuple((path[len(prefix):], targets)
                                for path, targets in fields if path.startswith(prefix)), owned_fields=children)
                        return flow, replace(result, handle_payloads=tuple(
                            attach(child, '[]/') for child in result.handle_payloads))
                    return flow, replace(result, fields=tuple(fields))
                if (plain := PLAIN_RETURN_JOINS.get((mode, typ))) is not None:
                    return flow, Value(plain, PLAIN_JOIN_TYPES[plain])
                if mode == 'array':
                    return flow, Value('join_array', typ)
                if mode == 'async_execution':
                    return flow, Value('join_async_execution', typ,
                                       task_result_handle_pools=execution.task_result_handle_pools)
                if mode in ASYNC_CAPTURE_VIEW_MODES:
                    from async_lowering import utf8_result_parameters
                    origins = frozenset(
                        replace(origin, kind='string_parameter')
                        if origin.kind == 'parameter' and declaration.args[1][index][2] == 'String'
                        else replace(origin, kind='vector_parameter')
                        if origin.kind == 'parameter' and declaration.args[1][index][2] in VECTOR_SLICE_MODES else origin
                        for index in utf8_result_parameters(declaration, self.analyzer.async_functions,
                            sync_result_contract=self.analyzer.sync_result_contract)
                        for _, targets in capture_fields(execution.fields, index) for origin in targets)
                    return flow, Value('join_' + mode, typ, reference_targets=origins)
                if mode in UTF8_VALUE_RESULT_FAMILIES:
                    return flow, Value('join_' + mode, VALUE_MODES[mode])
                return flow, Value({'Int': 'join_int', 'Bool': 'join_bool', 'u8': 'join_byte', 'char': 'join_char', 'str': 'join_text'}.get(typ, 'join_void'), typ)
            return flow, UNKNOWN
        if op == 'text':
            return {'next'}, Value('text', 'str')
        candidate = method_candidate(expr)
        if candidate is not None:
            receiver, method, rest = candidate[1:]
            value = self.lookup(receiver[1], environment, line)
            borrow = allocation_value_borrow(value.typ, method, self.analyzer.functions) if isinstance(value, Value) else None
            if borrow is not None:
                if receiver[0] != 'name' or rest:
                    self.fail(line, f'{method} exige un receveur nommé et aucun argument')
                return self.expression((borrow, receiver[1]), environment, line)
            builtin = UTF8_METHODS.get((value.typ, method)) if isinstance(value, Value) and (value.mode in VALUE_MODES or value.typ == 'String') else None
            if isinstance(value, Value):
                builtin = allocation_handle_method(value.typ, method, self.analyzer.functions) or vector_method(value.typ, method) or builtin
            if builtin is not None:
                operation, arity = builtin
                if receiver[0] != 'name' or len(rest) != arity:
                    self.fail(line, f'{method} exige un &str et aucun argument' if method == 'byte_len' else f'{method} exige un receveur et {arity} argument(s)')
                return self.expression((operation, receiver, *rest), environment, line)
            structure = isinstance(value, Value) and '' in self.analyzer.enums.get(value.typ, {})
            if op == 'method_call' or structure:
                fail = lambda message: self.fail(line, message)
                if not structure:
                    check_builtin_expression_arity(candidate, fail)
                name = f'{value.typ}.{method}' if isinstance(value, Value) else method
                declaration = self.analyzer.functions.get(name)
                if declaration is None:
                    self.fail(line, f"méthode inconnue '{name}'")
                arguments = method_arguments(receiver, declaration.args[1][0][1], value.mode, rest, fail)
                return self.expression(('call', name, arguments), environment, line, call_site=expr)
        if op == 'arithmetic' or op.startswith(('array_', 'utf8_')):
            flow = {'next'}
            values = []
            operand_type = None
            if shape is not None:
                if op == 'array_transfer':
                    operand_type = expected_array
                elif op in ('array_literal', 'array_repeat') and fixed_array_shape(shape[0]):
                    operand_type = shape[0]
            for operand in (expr[2:] if op == 'arithmetic' else array_operands(expr)):
                if 'next' not in flow:
                    break
                part, value = self.expression(operand, environment, line, operand_type)
                flow = (flow - {'next'}) | part
                values.append(value)
            if 'next' not in flow:
                return flow, UNKNOWN
            if op == 'array_hashmap_method' and values and isinstance(values[0], Value):
                from hashmap_syntax import map_types, numeric_handle_element, scalar_layout, value_layout
                mapping = map_types(values[0].typ)
                if mapping is not None:
                    value_type = mapping[1]
                    if (expr[1] == 'get' and value_type.startswith('&') and not value_type.startswith('&mut ')
                            and value_layout(value_type)):
                        return flow, Value('hashmap_slot_option', value_type)
                    if (expr[1] in ('insert', 'remove', 'try_insert') and value_type.startswith('&')
                            and not value_type.startswith('&mut ') and value_layout(value_type)):
                        mode = 'hashmap_ref_exchange' if expr[1] == 'try_insert' else 'hashmap_ref_option'
                        return flow, Value(mode, value_type[1:],
                                           reference_targets=frozenset({BorrowTarget('local')}))
                    if expr[1] in ('get', 'get_mut') and numeric_handle_element(value_type):
                        mode = 'hashmap_mut_slot_option' if expr[1] == 'get_mut' else 'hashmap_slot_option'
                        return flow, Value(mode, value_type)
                    if expr[1] in ('insert', 'remove', 'try_insert') and (element := numeric_handle_element(value_type)):
                        mode = 'hashmap_owned_exchange' if expr[1] == 'try_insert' else 'hashmap_owned_option'
                        return flow, Value(mode, element)
                if mapping is not None and scalar_layout(mapping[1]) is not None:
                    mode = {'get': 'hashmap_slot_option', 'get_mut': 'hashmap_mut_slot_option',
                            'insert': 'hashmap_scalar_option', 'remove': 'hashmap_scalar_option',
                            'try_insert': 'hashmap_scalar_exchange'}.get(expr[1])
                    if mode is not None:
                        return flow, Value(mode, mapping[1])
            if values and isinstance(values[0], Value) and values[0].typ in REFERENCE_VECTORS:
                vector = values[0]
                items = vector.handle_items
                if items is None:
                    items = dict(vector.fields).get('.items', frozenset())
                if vector.typ == MUT_REF_VECTOR and op in ('array_handle_try_push', 'array_buffered_try_push'):
                    incoming = borrowed_targets(values[-1]) if isinstance(values[-1], Value) else frozenset()
                    updated = (possible_handle_items(items) or frozenset()) | incoming
                    update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), vector, updated,
                                               lambda value: getattr(value, 'structure_origins', frozenset()))
                    return flow, Value('mutable_ref_try_push', 'Result<(),&mut Int>', reference_targets=incoming)
                if vector.typ == MUT_REF_VECTOR and op in ('array_handle_exchange', 'array_buffered_replace'):
                    index = expr[2][1] if expr[2][0] == 'int' else None
                    incoming = borrowed_targets(values[-1]) if isinstance(values[-1], Value) else frozenset()
                    updated, targets = replace_shared_vector_item(items, index, incoming)
                    update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), vector, updated,
                                               lambda value: getattr(value, 'structure_origins', frozenset()))
                    return flow, Value('mutable_ref_replace', 'Result<&mut Int,&mut Int>', reference_targets=targets)
                if op == 'array_vector_try_push':
                    incoming = borrowed_targets(values[-1]) if isinstance(values[-1], Value) else frozenset()
                    updated = (possible_handle_items(items) or frozenset()) | incoming
                    update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), vector, updated,
                                               lambda value: getattr(value, 'structure_origins', frozenset()))
                    return flow, Value('shared_ref_try_push', 'Result<(),&Int>', reference_targets=incoming)
                if op == 'array_vector_replace':
                    index = expr[2][1] if expr[2][0] == 'int' else None
                    incoming = borrowed_targets(values[-1]) if isinstance(values[-1], Value) else frozenset()
                    updated, targets = replace_shared_vector_item(items, index, incoming)
                    update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), vector, updated,
                                               lambda value: getattr(value, 'structure_origins', frozenset()))
                    return flow, Value('shared_ref_replace', 'Result<&Int,&Int>', reference_targets=targets)
                if op == 'array_vector_pop':
                    targets = handle_items_at(items, len(items) - 1 if isinstance(items, tuple) else None)
                    updated = items[:-1] if isinstance(items, tuple) else items
                    update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), vector, updated,
                                               lambda value: getattr(value, 'structure_origins', frozenset()))
                    return flow, Value('shared_ref_option', 'Option<&Int>', reference_targets=targets or frozenset())
                index = expr[2][1] if op in ('array_index', 'array_vector_remove') and expr[2][0] == 'int' else None
                if op in ('array_vector_push', 'array_vector_remove'):
                    if op == 'array_vector_push':
                        incoming = borrowed_targets(values[-1]) if isinstance(values[-1], Value) else frozenset()
                        updated = handle_items_after_exchange(items, None, incoming, append=True)
                    else:
                        updated = handle_items_after_removal(items, index)
                    update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), vector, updated,
                                               lambda value: getattr(value, 'structure_origins', frozenset()),
                                               appended=(incoming,) if op == 'array_vector_push' else None)
                if op == 'array_vector_push':
                    return flow, VOID
                if op in ('array_index', 'array_vector_remove'):
                    targets = (self.detached_field_targets(vector, f'.items:{index}')
                               if op == 'array_index' and index is not None and vector.handle_items is None
                               else handle_items_at(items, index) or frozenset())
                    return flow, Value(('mutable_vector_slot' if op == 'array_index' else 'mut')
                                       if vector.typ == MUT_REF_VECTOR else 'ref', 'Int', reference_targets=targets)
            if op in ('array_vector_push', 'array_handle_exchange', 'array_handle_try_push',
                      'array_buffered_replace', 'array_buffered_try_push'):
                item = values[-1]
                incoming = item.candidates if isinstance(item, Value) else frozenset()
                receiver = expr[1][1] if expr[1][0] == 'name' else None
                vector = environment.get(receiver)
                self.remember_handle_payload(environment, receiver, item)
                vector = environment.get(receiver)
                old_items = vector.handle_items if isinstance(vector, Value) else None
                append = op not in ('array_handle_exchange', 'array_buffered_replace')
                index = expr[2][1] if not append and expr[2][0] == 'int' else None
                exchange = (receiver, index, incoming or frozenset({UNKNOWN_HANDLE_ITEM}), append)
                if op == 'array_vector_push':
                    self.publish_handle_exchange(environment, exchange)
                    return flow, VOID
                if op in ('array_buffered_replace', 'array_buffered_try_push'):
                    self.publish_handle_exchange(environment, exchange, exact=False)
                    old = frozenset() if append else handle_items_at(old_items, index) or frozenset()
                    typ = exchange_type(vector_payload_element(vector.typ), append, "local" if vector.typ in INLINE_VECTOR_ELEMENTS else "pool")
                    if vector.typ in INLINE_VECTOR_ELEMENTS and not append:
                        previous = restore_handle_payload(Value('owned', vector_payload_element(vector.typ), old), vector)
                        previous = replace(previous, candidates=incoming)
                        return flow, Value('buffered_handle_exchange', typ, incoming,
                            exchange_payloads=(incoming, incoming), exchange_values=(previous, item))
                    return flow, Value('buffered_handle_exchange', typ, incoming | old,
                                       exchange_payloads=(old, incoming), handle_payloads=vector.handle_payloads)
                return flow, Value('handle_exchange', handle_vector_element(vector.typ), incoming,
                                   handle_items=handle_items_at(old_items, index), handle_exchange=exchange, handle_payloads=vector.handle_payloads)
            if op == 'array_handle_exchange_status':
                return flow, SCALAR
            if op == 'array_handle_exchange_value':
                exchange = values[0]
                if exchange.mode in ('mutable_ref_replace', 'mutable_ref_try_push'):
                    return flow, replace(exchange, mode='mut', typ='Int')
                if expr[2][1] != 0:
                    return flow, restore_handle_payload(Value('owned', exchange.typ, exchange.candidates), exchange)
                return flow, restore_handle_payload(extracted_handle(exchange.handle_items, exchange.typ), exchange)
            if op == 'array_handle_len':
                return flow, SCALAR
            if op == 'array_buffered_exchange_status':
                return flow, SCALAR
            if op == 'array_buffered_exchange_take':
                arm = expr[2][1]
                if arm in (-1, 1):
                    return flow, VOID
                exchange = values[0]
                if isinstance(exchange, Value) and exchange.mode in ('mutable_ref_replace', 'mutable_ref_try_push'):
                    return flow, replace(exchange, mode='mut', typ='Int')
                if not isinstance(exchange, Value) or len(exchange.exchange_payloads) != 2:
                    self.fail(line, 'match (-> résultat) exige un résultat de replace ou try_push')
                if exchange.exchange_values:
                    return flow, exchange.exchange_values[arm == 5]
                return flow, restore_handle_payload(extracted_handle(exchange.exchange_payloads[arm == 5], exchange_element(exchange.typ)), exchange)
            if op == 'array_handle_option_status':
                return flow, SCALAR
            if op == 'array_handle_option_value':
                return flow, replace(values[0], mode='mut', typ='Int') if values[0].mode == 'mutable_ref_option' else replace(values[0], mode='owned')
            if op == 'array_handle_option_empty':
                return flow, VOID
            if op in ('array_pop_handle', 'array_handle_option_pop'):
                vector = values[0]
                if isinstance(vector, Value) and vector.typ == MUT_REF_VECTOR:
                    items = vector.handle_items
                    if items is None:
                        items = dict(vector.fields).get('.items', frozenset())
                    targets = items[-1] if isinstance(items, tuple) and items else possible_handle_items(items)
                    updated = items[:-1] if isinstance(items, tuple) else items
                    update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), vector, updated,
                                               lambda value: getattr(value, 'structure_origins', frozenset()))
                    buffered = op == 'array_handle_option_pop'
                    return flow, Value('mutable_ref_option' if buffered else 'mut',
                                        'Option<&mut Int>' if buffered else 'Int', reference_targets=targets or frozenset())
                value = self.extract_vector_item(environment, expr[1], last=True, optional=op == 'array_handle_option_pop')
                if isinstance(vector, Value) and vector.typ in INLINE_VECTOR_ELEMENTS:
                    element = INLINE_VECTOR_ELEMENTS[vector.typ]
                    origin = id(expr[1])
                    candidate = ResultCandidate('fresh', source=SourceOrigin('local_value', origin, 'data stack implicite', element))
                    value = replace(value, typ=element, candidates=frozenset({candidate}),
                                    fresh_variants=frozenset({''}), structure_origins=frozenset({origin}))
                return flow, replace(value, mode='handle_option') if op == 'array_handle_option_pop' else value
            if op == 'array_handle_vequals':
                return flow, Value('bool', 'bool')
            if op in ('array_handle_ref', 'array_handle_mut'):
                return flow, Value('mut' if op == 'array_handle_mut' else 'ref',
                                   f'A<{values[0].typ}>', reference_targets=borrowed_targets(values[0]),
                                   storage_owner=expr[1][1])
            if op == 'array_split' and isinstance(values[0], Value):
                value = values[0]
                mode = VECTOR_MUT_SLICE_MODES.get(value.typ, value.mode)
                if mode in VECTOR_MUT_SLICE_MODES.values():
                    typ = VALUE_MODES[mode]
                    return flow, Value('vector_split', f'(&mut {typ},&mut {typ})', reference_targets=text_origins(value))
            if op == 'array_split_half':
                pair = values[0]
                if not isinstance(pair, Value) or pair.mode != 'vector_split':
                    self.fail(line, 'cette liaison exige un résultat de séparation')
                typ = VECTOR_SPLIT_TYPES[pair.typ]
                mode = VECTOR_MUT_SLICE_MODES['Vector<Int>' if typ == '[Int]' else 'Vector<u8>']
                return flow, replace(pair, mode=mode, typ=typ)
            if op in ('array_vector_len', 'array_vector_push'):
                return flow, SCALAR if op == 'array_vector_len' else VOID
            if op == 'array_vector_push_new':
                return flow, Value('mut', VECTOR_ELEMENTS[values[0].typ],
                                   reference_targets=text_origins(values[0]), payload_reference=True)
            if op == 'array_vector_read_fd':
                return flow, Value('read_result', VALUE_MODES['read_result'])
            if op == 'array_vector_try_extend':
                return flow, Value('capacity_result', VALUE_MODES['capacity_result'])
            if op in ('array_vector_pop', 'array_vector_replace', 'array_vector_try_push') and values and isinstance(values[0], Value) and values[0].typ in VECTOR_ELEMENTS:
                modes = {'array_vector_pop': VECTOR_OPTION_MODES,
                         'array_vector_replace': VECTOR_REPLACE_MODES,
                         'array_vector_try_push': VECTOR_TRY_PUSH_MODES}[op]
                mode = modes[VECTOR_ELEMENTS[values[0].typ]]
                return flow, Value(mode, VALUE_MODES[mode])
            if op in ('utf8_value', 'utf8_error') and values and isinstance(values[0], Value):
                exchange = values[0]
                if exchange.mode in ('mutable_ref_replace', 'mutable_ref_try_push'):
                    return flow, replace(exchange, mode='mut', typ='Int')
                if exchange.mode == 'buffered_handle_exchange':
                    payload = exchange.exchange_payloads[op == 'utf8_error']
                    return flow, restore_handle_payload(extracted_handle(payload, exchange_element(exchange.typ)), exchange)
            if op == 'utf8_error' and values and isinstance(values[0], Value):
                if values[0].mode.startswith('join_'):
                    return flow, Value('runtime_error', 'runtime::Error')
                if values[0].mode in RESULT_ERROR_MODES:
                    mode = RESULT_ERROR_MODES[values[0].mode]
                    return flow, Value(mode, VALUE_MODES[mode])
                op = 'utf8_value'
            if op == 'utf8_value' and values and isinstance(values[0], Value):
                if values[0].mode in ('hashmap_ref_option', 'hashmap_ref_exchange'):
                    return flow, replace(values[0], mode='ref')
                if values[0].mode in ('hashmap_owned_option', 'hashmap_owned_exchange'):
                    return flow, Value('owned', values[0].typ, frozenset({UNKNOWN_HANDLE_ITEM}))
                if values[0].mode in ('hashmap_scalar_option', 'hashmap_scalar_exchange'):
                    from hashmap_syntax import scalar_layout
                    return flow, Value(scalar_layout(values[0].typ)[0], values[0].typ)
                if values[0].mode in ('hashmap_slot_option', 'hashmap_mut_slot_option'):
                    mode = 'mut' if values[0].mode == 'hashmap_mut_slot_option' else 'ref'
                    return flow, Value(mode, values[0].typ,
                                       reference_targets=frozenset({BorrowTarget('local')}))
                if values[0].mode == 'join_async_execution':
                    return flow, Value('async_execution', values[0].typ,
                                       deferred_field_updates=values[0].deferred_field_updates,
                                       deferred_guarded_writes=values[0].deferred_guarded_writes,
                                       deferred_owned_updates=values[0].deferred_owned_updates,
                                       deferred_vector_updates=values[0].deferred_vector_updates,
                                       deferred_map_paths=values[0].deferred_map_paths,
                                       deferred_definite_fields=values[0].deferred_definite_fields,
                                       task_result_handle_pools=values[0].task_result_handle_pools)
                if values[0].mode in CONVERSION_PAYLOADS:
                    typ = CONVERSION_PAYLOADS[values[0].mode]
                    return flow, Value(FORMATS[typ].mode, 'Int' if typ == 'i32' else typ)
                if values[0].mode in NUMERIC_JOIN_FIELDS:
                    mode = values[0].mode.removeprefix('join_')
                    return flow, Value(mode, mode)
                if values[0].mode in PLAIN_JOIN_INNER_MODES:
                    inner = PLAIN_JOIN_INNER_MODES[values[0].mode]
                    return flow, Value(inner, PLAIN_JOIN_TYPES[inner])
                if values[0].mode.startswith('join_') and values[0].mode[5:] in ERROR_VALUE_TYPES:
                    mode = values[0].mode[5:]
                    return flow, Value(mode, VALUE_MODES[mode])
                if values[0].mode == 'join_runtime_error':
                    return flow, Value('runtime_error', 'runtime::Error')
                if values[0].mode == 'join_array':
                    return flow, Value('array', values[0].typ)
                if values[0].mode in EXCHANGE_JOIN_TYPES:
                    return flow, replace(values[0], mode=exchange_inner_signature(values[0].mode)[0], typ=exchange_inner_signature(values[0].mode)[1])
                if values[0].mode in OPTION_JOIN_TYPES:
                    return flow, replace(values[0], mode=option_inner_signature(values[0].mode)[0])
                if values[0].mode in OWNED_JOIN_TYPES and owned_inner_mode(values[0].mode) != 'owned':
                    return flow, replace(values[0], mode=owned_inner_mode(values[0].mode))
                if values[0].mode == 'join_owned':
                    return flow, replace(values[0], mode='owned', absent_owned_payload=False)
                if values[0].mode in ('join_ref', 'join_mut'):
                    targets = frozenset(replace(origin, kind='vector_parameter')
                        if origin.kind == 'parameter' and self.params[origin.parameter][2] in VECTOR_SLICE_MODES
                        else origin for origin in values[0].reference_targets)
                    return flow, Value(values[0].mode[5:], values[0].typ, reference_targets=targets,
                                       payload_reference=values[0].payload_reference or any(
                                           origin.kind == 'vector_parameter' for origin in targets))
                if values[0].mode in ('shared_ref_option', 'shared_ref_replace', 'shared_ref_try_push'):
                    return flow, Value('ref', 'Int', reference_targets=values[0].reference_targets)
                if values[0].mode in ('int_option', 'int_replace', 'int_try_push', 'read_result', 'join_int'):
                    return flow, SCALAR
                if values[0].mode.startswith('join_') and values[0].mode[5:] in ASYNC_VALUE_RESULT_FAMILIES:
                    mode = values[0].mode[5:]
                    return flow, Value(mode, VALUE_MODES[mode], reference_targets=values[0].reference_targets)
                if values[0].mode == 'join_byte_ref':
                    return flow, Value('byte_ref', 'u8', reference_targets=values[0].reference_targets)
                if values[0].mode == 'join_text':
                    return flow, Value('text', 'str', reference_targets=values[0].reference_targets)
                if values[0].mode.startswith('join_') and values[0].mode[5:] in (*VECTOR_SLICE_ELEMENTS, *SHARED_VECTOR_SLICE_MODES):
                    return flow, Value(values[0].mode[5:], values[0].typ, reference_targets=values[0].reference_targets)
                if values[0].mode == 'join_char':
                    return flow, Value('char', 'char')
                if values[0].mode == 'join_bool':
                    return flow, Value('bool', 'Bool')
                if values[0].mode in ('byte_option', 'byte_replace', 'byte_try_push', 'join_byte'):
                    return flow, Value('byte', 'u8')
            if op == 'array_vector_remove' and isinstance(values[0], Value) and values[0].typ in INLINE_VECTOR_ELEMENTS:
                element = INLINE_VECTOR_ELEMENTS[values[0].typ]
                index = expr[2][1] if expr[2][0] == 'int' else None
                payload = self.extract_vector_item(environment, expr[1], index)
                # The lowered operation tuple is rebuilt at each inference pass.
                # Its receiver is the stable source AST node for this operation.
                origin = id(expr[1])
                candidate = ResultCandidate('fresh', source=SourceOrigin('local_value', origin, 'data stack implicite', element))
                return flow, replace(payload, mode='owned', typ=element, candidates=frozenset({candidate}),
                                     fresh_variants=frozenset({''}), structure_origins=frozenset({origin}))
            if op == 'array_index' and isinstance(values[0], Value) and values[0].typ in INLINE_VECTOR_ELEMENTS:
                element = INLINE_VECTOR_ELEMENTS[values[0].typ]
                candidate = ResultCandidate('fresh', source=SourceOrigin('local_value', id(expr), 'data stack implicite', element))
                index = expr[2][1] if expr[2][0] == 'int' else None
                payload = restore_handle_payload(extracted_handle(vector_result_candidates(values[0], index), element), values[0])
                return flow, replace(payload, mode='inline_vector_slot', copy_candidates=frozenset({candidate}))
            if op == 'array_index' and isinstance(values[0], Value) and is_handle_vector(values[0].typ):
                root = values[0]
                index = expr[2][1] if expr[2][0] == 'int' else None
                return flow, Value('handle_slot', f'A<{handle_vector_element(root.typ)}>', reference_targets=text_origins(root), payload_reference=True,
                                   handle_slot=(root.structure_origins, index) if root.structure_origins else None)
            if op == 'array_vector_remove' and isinstance(values[0], Value) and is_handle_vector(values[0].typ):
                index = expr[2][1] if expr[2][0] == 'int' else None
                return flow, self.extract_vector_item(environment, expr[1], index)
            if op in ('array_index', 'array_vector_remove') and values and isinstance(values[0], Value) and values[0].typ in VECTOR_ELEMENTS:
                return flow, SCALAR if VECTOR_ELEMENTS[values[0].typ] == 'Int' else Value('byte', 'u8')
            if op == 'utf8_try_slice':
                if not values or not isinstance(values[0], Value) or values[0].typ not in ('str', 'String'):
                    self.fail(line, 'try_slice exige un &str ou String')
                return flow, Value('slice_result', UTF8_SLICE_RESULT, reference_targets=text_origins(values[0]))
            if op == 'utf8_validate':
                targets = borrowed_targets(values[0]) if values and isinstance(values[0], Value) else frozenset()
                return flow, Value('text_result', UTF8_TEXT_RESULT,
                                   reference_targets=targets or frozenset({BorrowTarget('local')}))
            if op == 'utf8_value' and values and isinstance(values[0], Value) and values[0].mode in ('text_result', 'slice_result'):
                return flow, Value('text', 'str', reference_targets=borrowed_targets(values[0]))
            if op == 'utf8_value' and values and isinstance(values[0], Value) and values[0].mode in ('byte_replace_result', 'integer_conversion_result'):
                return flow, Value('byte', 'u8')
            if op == 'utf8_slice' and values and isinstance(values[0], Value) and values[0].typ in VECTOR_SLICE_MODES:
                mode = VECTOR_SLICE_MODES[values[0].typ]
                return flow, Value(mode, VALUE_MODES[mode], reference_targets=text_origins(values[0]))
            if op == 'utf8_slice' and values and isinstance(values[0], Value):
                mode = SHARED_VECTOR_SLICE_MODES.get(values[0].mode, values[0].mode)
                if mode in VECTOR_SLICE_MODES.values():
                    return flow, replace(values[0], mode=mode)
            if op == 'utf8_slice' and values and isinstance(values[0], Value) and values[0].typ in ('str', 'String'):
                return flow, Value('text', 'str', reference_targets=text_origins(values[0]))
            if op == 'array_integer_try_from':
                if getattr(values[0], 'mode', None) not in ('scalar', 'byte'):
                    self.fail(line, 'u8::try_from exige un Int ou un u8')
                return flow, Value('integer_conversion_result', 'Result<u8,IntegerConversionError>')
            if op == 'array_byte_literal':
                return flow, Value('byte', 'u8')
            if op in ('array_numeric_literal', 'array_numeric_operation', 'array_numeric_cast'):
                typ = expr[1]
                return flow, Value(FORMATS[typ].mode, 'Int' if typ == 'i32' else typ)
            if op in ('array_numeric_not', 'array_start_poller'):
                return flow, Value('bool', 'bool')
            if op == 'array_ffi_call':
                return flow, Value(*expr[2])
            if op in ('array_mutex_new', 'array_mutex_lock', 'array_mutex_acquire', 'array_hashmap_new'):
                source = SourceOrigin('local_value', id(expr), 'data stack implicite', expr[1])
                return flow, Value('owned', expr[1], frozenset({ResultCandidate('fresh', source=source)}))
            if op in ('array_numeric_len', 'array_numeric_slice_len'):
                return flow, Value('u64', 'u64')
            if op == 'array_numeric_try_from':
                return flow, Value(conversion_mode(expr[1]), conversion_type(expr[1]))
            if op == 'array_integer_cast':
                mode, error = exact_integer_conversion(getattr(values[0], 'mode', None), expr[2])
                if error:
                    self.fail(line, error)
                return flow, Value(mode, expr[2])
            if op == 'builtin_error':
                return flow, Value(expr[1], VALUE_MODES[expr[1]])
            if op in UTF8_EXPRESSION_MODES:
                mode = UTF8_EXPRESSION_MODES[op]
                return flow, SCALAR if mode == 'scalar' else VOID if mode == 'void' else Value(mode, VALUE_MODES[mode])
            if op == 'array_hashmap_target' and values and isinstance(values[0], Value):
                from hashmap_syntax import numeric_handle_element, scalar_layout
                slot = values[0]
                if slot.mode in ('ref', 'mut'):
                    typ = slot.typ[1:] if slot.typ.startswith('&') else numeric_handle_element(slot.typ)
                    if typ and (layout := scalar_layout(typ)):
                        return flow, Value(layout[0], typ)
            if op == 'array_deref_slot' and values and isinstance(values[0], Value) and values[0].mode == 'ref' and values[0].typ == 'Int':
                return flow, SCALAR
            if op == 'array_deref_call' and values and isinstance(values[0], Value) and values[0].typ == 'u8' and values[0].mode in ('byte_ref', 'mut'):
                return flow, Value('byte', 'u8')
            if op == 'arithmetic':
                return flow, SCALAR
            if op == 'array_index' and values and isinstance(values[0], Value) and values[0].typ == '[Int]':
                return flow, Value('scalar', 'Int', reference_targets=borrowed_targets(values[0]), payload_reference=True)
            if op == 'array_index' and values and isinstance(values[0], Value) and values[0].typ in ('str', 'String', '[u8]'):
                return flow, Value('byte', 'u8', reference_targets=text_origins(values[0]))
            if values and isinstance(values[0], Value) and values[0].mode == 'array_refs':
                holder = values[0]
                fields = dict(holder.fields)
                element, length = fixed_array_shape(holder.typ)
                nested = reference_array_shape(element)
                if op == 'array_index' and nested:
                    _, groups = reference_array_projection(holder.typ, (expr[2],))
                    return flow, project_reference_array(holder, element, groups)
                selected = (str(expr[2][1]),) if len(expr) > 2 and expr[2][0] == 'int' else tuple(fields)
                if op == 'array_index' and reference_type(element) and reference_array_shape(reference_type(element)[1]):
                    rows = dict(holder.rows)
                    chosen = [rows[slot] for slot in selected if slot in rows]
                    if not chosen:
                        self.fail(line, 'provenance de ligne référencée manquante')
                    row = merge_reference_values(chosen)
                    targets = frozenset(t for slot in selected for t in fields.get(slot, ()))
                    return flow, replace(row, reference_targets=targets, container_borrow=True,
                                         container_mode=reference_array_shape(holder.typ)[0])
                if op == 'array_index':
                    targets = frozenset(t for slot in selected for t in fields.get(slot, ()))
                    mode = reference_array_shape(holder.typ)[0]
                    return flow, Value(mode, reference_type(element)[1], reference_targets=targets, payload_reference=True)
                if op in ('array_replace', 'array_swap'):
                    name, prefix = reference_array_path(expr[1])
                    root = holder
                    if op == 'array_swap':
                        updated = swap_reference_fields(root.fields, root.typ, (), expr[2], expr[3])
                        update_array_aliases(environment, name, updated, root, swapped_reference_rows(root, expr[2], expr[3]))
                        return flow, VOID
                    target_type, positions = reference_array_projection(root.typ, (expr[2],))
                    incoming = values[2]
                    row = reference_array_shape(target_type)
                    if row:
                        if not isinstance(incoming, Value) or incoming.mode != 'array_refs' or incoming.typ != target_type:
                            self.fail(line, 'le remplacement doit conserver le type de la ligne')
                        replacement = tuple(dict(incoming.fields).get(str(slot), frozenset()) for slot in range(row[1]))
                    else:
                        mode, pointee = reference_type(target_type)
                        replacement = self.reference_value_fields(incoming, target_type, line)
                    old, updated = replace_reference_fields(root.fields, positions, replacement)
                    updated_rows = replace_reference_rows(root, positions, incoming)
                    update_array_aliases(environment, name, updated, root, updated_rows)
                    if not row and reference_array_shape(pointee):
                        stored_rows = dict(root.rows)
                        removed = merge_reference_values([stored_rows[str(index)] for index in positions[0]])
                        return flow, replace(removed, container_borrow=True, container_mode=mode,
                                             reference_targets=dict(old).get('0', frozenset()))
                    if row:
                        return flow, Value('array_refs', target_type, fields=old,
                                           container_origins=frozenset({('replace', id(expr))}))
                    return flow, Value(mode, pointee, reference_targets=dict(old).get('0', frozenset()),
                                       payload_reference=True)
            if (op == 'array_transfer' and expr[1] == ('array_literal',)
                    and self.declared[0] == 'array_refs' and reference_array_shape(self.declared[1])[1] == 0):
                return flow, Value('array_refs', self.declared[1])
            if op in ('array_ref', 'array_mut_ref') and values and values[0].mode == 'array_refs':
                return flow, replace(values[0], container_borrow=True, container_mode='mut' if op == 'array_mut_ref' else 'ref',
                    reference_targets=values[0].reference_targets or frozenset({BorrowTarget('local')}))
            if op == 'array_copy' and values and values[0].mode == 'array_refs':
                value = values[0]
                return flow, Value(value.mode, value.typ, fields=value.fields, rows=value.rows,
                                   container_origins=frozenset({('copy', id(expr))}))
            if op == 'array_copy' and values and isinstance(values[0], Value) and '' in self.analyzer.enums.get(values[0].typ, {}):
                original = values[0]
                candidates = frozenset(ResultCandidate('fresh', source=(
                    SourceOrigin('local_value', id(expr), 'data stack implicite', original.typ)
                    if candidate.storage().kind == 'local_value' else candidate.storage()))
                                       for candidate in (original.copy_candidates or original.candidates))
                return flow, Value('owned', original.typ, candidates, original.fields, frozenset({''}),
                                   structure_origins=frozenset({id(expr)}))
            if op in ('array_transfer', 'array_copy'):
                return flow, values[0]
            if op in ('array_literal', 'array_repeat') and values and all(
                    isinstance(child, Value) and child.mode == 'array_refs' and child.container_borrow for child in values):
                child = values[0]
                count = expr[2] if op == 'array_repeat' else len(values)
                children = [child] * count if op == 'array_repeat' else values
                element = ('&mut ' if child.container_mode == 'mut' else '&') + child.typ
                return flow, Value('array_refs', f'[{element};{count}]',
                    fields=tuple((str(slot), borrowed_targets(child)) for slot, child in enumerate(children)),
                    rows=tuple((str(slot), child) for slot, child in enumerate(children)),
                    container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_repeat' and values and values[0].mode == 'array_refs':
                child = values[0]
                width = reference_array_shape(child.typ)[1]
                fields = tuple((str(row * width + int(slot)), targets)
                               for row in range(expr[2]) for slot, targets in child.fields)
                return flow, Value('array_refs', f'[{child.typ};{expr[2]}]', fields=fields,
                                   container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_literal' and values and all(value.mode == 'array_refs' for value in values):
                width = reference_array_shape(values[0].typ)[1]
                fields = tuple((str(row * width + int(slot)), targets)
                               for row, child in enumerate(values) for slot, targets in child.fields)
                return flow, Value('array_refs', f'[{values[0].typ};{len(values)}]', fields=fields,
                                   container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_repeat' and values and values[0].mode in ('ref', 'array_ref'):
                return flow, Value('array_refs', f'[&{values[0].typ};{expr[2]}]', fields=tuple(
                    (str(slot), borrowed_targets(values[0])) for slot in range(expr[2])), container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_literal' and values and all(
                    isinstance(value, Value) and value.mode == values[0].mode and value.mode in ('ref', 'mut', 'array_ref', 'array_mut')
                    for value in values):
                element = ('&mut ' if values[0].mode in ('mut', 'array_mut') else '&') + values[0].typ
                return flow, Value('array_refs', f'[{element};{len(values)}]', fields=tuple(
                    (str(slot), borrowed_targets(value)) for slot, value in enumerate(values)),
                                   container_origins=frozenset({('literal', id(expr))}))
            if values and isinstance(values[0], Value):
                holder = values[0]
                shape = fixed_array_shape(holder.typ)
                if op in ('array_ref', 'array_mut_ref') and shape:
                    return flow, Value('mut' if op == 'array_mut_ref' else 'ref', holder.typ,
                        reference_targets=borrowed_targets(holder) or frozenset({BorrowTarget('local')}), payload_reference=True)
                if op in ('array_index', 'array_replace') and shape and shape[0] == 'u8':
                    return flow, Value('byte', 'u8')
                if op == 'array_index' and shape:
                    element, _ = shape
                    return flow, Value('array' if fixed_array_shape(element) else 'scalar', element,
                        reference_targets=borrowed_targets(holder) or frozenset({BorrowTarget('local')}))
                if op in ('array_literal', 'array_repeat'):
                    length = expr[2] if op == 'array_repeat' else len(values)
                    return flow, Value('array', f'[{holder.typ};{length}]',
                        reference_targets=frozenset({BorrowTarget('local')}))
            return flow, SCALAR if op in ('array_index', 'array_len', 'array_replace') else UNKNOWN
        if op == 'loop_expr':
            return self.loop(expr[1], environment, valued=True, expected_array=expected_array)
        if op == 'reborrow':
            parent = self.lookup(expr[1], environment, line)
            if not isinstance(parent, Value):
                return {'next'}, UNKNOWN
            if parent.mode in (*SHARED_VECTOR_SLICE_MODES, *VECTOR_SLICE_MODES.values()):
                mode = SHARED_VECTOR_SLICE_MODES.get(parent.mode, parent.mode) if expr[2] == 'ref' else parent.mode
                return {'next'}, replace(parent, mode=mode)
            if parent.mode == 'byte_ref':
                return {'next'}, parent
            if parent.mode == 'array_refs':
                return {'next'}, replace(parent, container_borrow=True, container_mode=expr[2])
            if parent.typ.startswith('A<') or is_payload_vector(parent.typ):
                return {'next'}, replace(parent, mode=expr[2])
            if parent.typ in self.analyzer.enums:
                return {'next'}, replace(parent, mode=expr[2], reference_targets=borrowed_targets(parent))
            return {'next'}, Value(expr[2], parent.typ, reference_targets=borrowed_targets(parent), payload_reference=parent.payload_reference)
        if op == 'match_expr':
            if expr[1].consuming:
                return self.nodes([expr[1]], environment, valued=True, expected_array=expected_array)
            return self.borrowed_match(expr[1], environment, valued=True, expected_array=expected_array)
        if op == 'field':
            carrier = self.lookup(expr[1], environment, line)
            key = '.' + expr[2]
            if isinstance(carrier, Value):
                declared = dict(self.analyzer.enums.get(carrier.typ, {}).get('', ())).get(expr[2], '')
                if (mode := scalar_field_mode(declared)) is not None:
                    return {'next'}, Value(mode, declared)
                capability = reference_type(declared)
                if capability and (capability[0] == 'ref' or
                                   carrier.typ.startswith('__crust_closure$') and capability[0] == 'mut'):
                    return {'next'}, Value('ref', capability[1], fields=nested_reference_fields(carrier.fields, key),
                                           reference_targets=self.detached_field_targets(carrier, key))
            return {'next'}, SCALAR
        if op == 'deref':
            value = self.lookup(expr[1], environment, line)
            if isinstance(value, Value) and value.mode == 'ref' and value.typ.startswith('&'):
                from hashmap_syntax import scalar_layout
                typ = value.typ[1:]
                if scalar_layout(typ):
                    return {'next'}, Value('ref', typ, reference_targets=borrowed_targets(value))
            from mutex_syntax import GUARD_TYPES, payload_type
            content = (payload_type(value.typ, GUARD_TYPES) or value.typ) if isinstance(value, Value) else None
            mode = scalar_field_mode(content) if content else None
            return {'next'}, Value(mode, content) if mode else SCALAR
        if op == 'bool':
            return {'next'}, Value('bool', 'bool')
        if op in ('int', 'field_deref'):
            return {'next'}, SCALAR
        if op in ('name', 'move', 'down', 'ref', 'mut'):
            value = self.lookup(expr[1], environment, line)
            if op == 'move' and (not isinstance(value, Value) or value.mode not in ('owned', 'array', 'array_refs', 'handle_option', 'buffered_handle_exchange', 'task', 'execution', 'selection', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES)):
                self.fail(line, 'seule une allocation explicite est déplaçable')
            if op in ('ref', 'mut') and isinstance(value, Value):
                if value.mode == 'array_refs':
                    return {'next'}, replace(value, container_borrow=True, container_mode=op,
                        reference_targets=value.reference_targets or frozenset({BorrowTarget('local')}))
                if value.mode in ('ref', 'mut'):
                    self.fail(line, 'emprunt imbriqué non pris en charge : & sur un emprunt ajoute un niveau ; utiliser son nom')
                if is_payload_vector(value.typ):
                    return {'next'}, replace(value, mode=op, storage_owner=expr[1])
                value = Value(op, value.typ, value.candidates, value.fields, value.fresh_variants,
                              borrowed_targets(value) or (frozenset({BorrowTarget('local')}) if fixed_array_shape(value.typ) else frozenset()),
                              fixed_array_shape(value.typ) is not None,
                              storage_owner=expr[1] if op == 'mut' and value.typ in self.analyzer.enums else None,
                              structure_origins=value.structure_origins, owned_fields=value.owned_fields)
            return {'next'}, value
        if op in ('ref_expr', 'mut_expr') and expr[1][0] == 'array_deref_slot':
            flow, value = self.expression(expr[1][1], environment, line)
            if value.mode == 'mutable_vector_slot':
                slot = expr[1][1]
                carrier = environment.get(slot[1][1]) if slot[1][0] == 'name' else None
                field = f'.items:{slot[2][1]}' if slot[2][0] == 'int' else '.items'
                return flow, Value('mut' if op == 'mut_expr' else 'ref', 'Int',
                                   reference_targets=self.mutable_vector_result_targets(carrier, field))
            if value.mode == 'array_refs':
                roots = frozenset(BorrowTarget('reserved_stored_array_parameter', target.parameter, target.field)
                                  if target.kind == 'stored_array_parameter' and value.container_mode == 'mut' else target
                                  for target in value.reference_targets)
                return flow, replace(value, container_borrow=True, container_mode='mut' if op == 'mut_expr' else 'ref',
                                     reference_targets=roots)
            if value.typ.startswith('A<'):
                return flow, replace(value, mode='mut' if op == 'mut_expr' else 'ref')
            targets = frozenset(BorrowTarget('reserved_stored_array_parameter', t.parameter, t.field)
                                if t.kind == 'stored_array_parameter' and value.mode == 'mut' else t for t in borrowed_targets(value))
            return flow, Value('mut' if op == 'mut_expr' else 'ref', value.typ, reference_targets=targets, payload_reference=True)
        if op in ('ref_expr', 'mut_expr') and expr[1][0] == 'array_index':
            flow, projected = self.expression(expr[1], environment, line)
            if isinstance(projected, Value) and projected.mode == 'handle_slot':
                return flow, replace(projected, mode='mut' if op == 'mut_expr' else 'ref')
            if isinstance(projected, Value) and projected.mode == 'scalar' and projected.payload_reference:
                return flow, Value('mut' if op == 'mut_expr' else 'ref', 'Int',
                                   reference_targets=borrowed_targets(projected), payload_reference=True)
            if isinstance(projected, Value) and projected.mode == 'byte':
                return flow, Value('mut' if op == 'mut_expr' else 'byte_ref', 'u8',
                                   reference_targets=borrowed_targets(projected), payload_reference=op == 'mut_expr')
            if isinstance(projected, Value) and projected.mode == 'array_refs':
                return flow, replace(projected, container_borrow=True, container_mode='mut' if op == 'mut_expr' else 'ref')
            base = expr[1]
            while base[0] == 'array_index':
                base = base[1]
            value = self.lookup(base[1], environment, line) if base[0] == 'name' else UNKNOWN
            targets = borrowed_targets(value) if isinstance(value, Value) else frozenset()
            return flow, Value('ref' if op == 'ref_expr' else 'mut', projected.typ,
                               reference_targets=borrowed_targets(projected) or targets or frozenset({BorrowTarget('local')}), payload_reference=True)
        if op in ('ref_expr', 'mut_expr') and expr[1][0] == 'field':
            _, name, path = expr[1]
            carrier = self.lookup(name, environment, line)
            targets = self.inline_field_targets(carrier, path)
            from structure_views import contained_field
            projection = contained_field(self.analyzer.enums, carrier.typ, path) if isinstance(carrier, Value) else None
            if projection is not None:
                from structure_views import project_fields
                return {'next'}, Value('mut' if op == 'mut_expr' else 'ref', projection.typ,
                                       copy_candidates=carrier.copy_candidates or carrier.candidates,
                                       reference_targets=targets, fields=project_fields(carrier.fields, path),
                                       owned_fields=project_fields(carrier.owned_fields, path),
                                       storage_owner=carrier.storage_owner or name,
                                       structure_origins=carrier.structure_origins,
                                       inline_path=(carrier.inline_path + '.' if carrier.inline_path else '') + path)
            declared = (dict(self.analyzer.enums.get(carrier.typ, {}).get('', ())).get(path)
                        if isinstance(carrier, Value) else None)
            return {'next'}, Value('mut' if op == 'mut_expr' else 'ref', declared if declared in FORMATS else 'Int',
                                    reference_targets=targets, payload_reference=True)
        if op in ('ref_expr', 'mut_expr') and expr[1][0] == 'field_deref':
            _, name, path = expr[1][1]
            carrier = self.lookup(name, environment, line)
            if isinstance(carrier, Value) and carrier.structure_choices:
                branches, values, flow = [], [], set()
                for choice in carrier.structure_choices:
                    branch = environment.copy()
                    branch[name] = choice
                    part, value = self.expression(expr, branch, line)
                    flow |= part
                    branches.append((part, branch))
                    if 'next' in part:
                        values.append(value)
                self.join_environments(environment, branches)
                return flow, merge_reference_values(values) if values else UNKNOWN
            mode = 'mut' if op == 'mut_expr' else 'ref'
            if isinstance(carrier, Value):
                declared = dict(self.analyzer.enums.get(carrier.typ, {}).get('', ())).get(path, '')
                if declared.startswith('A<') and mode == 'mut' and (
                        carrier.storage_owner is not None or carrier.mode == 'owned'):
                    if carrier.storage_owner is None:
                        carrier = replace(carrier, storage_owner=name)
                    child = self.owned_field_at(environment, carrier, '.' + path)
                    if child is not None:
                        targets = frozenset(projected_field_origin(origin,
                            BorrowTarget('field_parameter', field='.' + path))
                            for origin in borrowed_targets(carrier))
                        return {'next'}, replace(child, mode=mode, candidates=frozenset(),
                                                 reference_targets=targets,
                                                 storage_owner=carrier.storage_owner,
                                                 owned_path=(*carrier.owned_path,
                                                     ('.' + carrier.inline_path if carrier.inline_path else '') + '.' + path))
                if declared.startswith('A<') and declared[2:-1] in self.analyzer.enums:
                    key = '.' + path
                    return {'next'}, Value(mode, declared[2:-1], carrier.candidates,
                        fields=nested_reference_fields(carrier.fields, key),
                        reference_targets=self.inline_field_targets(carrier, path, 'indirect_field_parameter'),
                        storage_owner=carrier.storage_owner or name,
                        owned_path=(*carrier.owned_path,
                            ('.' + carrier.inline_path if carrier.inline_path else '') + key))
                capability = reference_type(declared)
                if capability and capability[0] == 'ref' and mode == 'ref':
                    return self.expression(expr[1][1], environment, line)
                if (capability and capability[0] == 'mut' and numeric_type(capability[1])
                        and carrier.typ.startswith('__crust_closure$')):
                    targets = self.inline_field_targets(carrier, path, 'indirect_field_parameter')
                    return {'next'}, Value(mode, capability[1], reference_targets=targets,
                                           payload_reference=True)
                if capability and capability[0] == 'mut' and capability[1] in self.analyzer.enums:
                    key = '.' + path
                    kind = 'field_parameter' if carrier.mode == 'mut' else 'shared_field_parameter'
                    targets = frozenset(projected_field_origin(origin, BorrowTarget(kind, field=key))
                                        for origin in borrowed_targets(carrier)
                                        if carrier.mode in ('mut', 'ref'))
                    return {'next'}, Value(mode, capability[1], fields=nested_reference_fields(carrier.fields, key),
                                           reference_targets=targets or frozenset({BorrowTarget('local')}))
            targets = self.inline_field_targets(carrier, path, 'indirect_field_parameter')
            return {'next'}, Value(mode, 'Int',
                                    reference_targets=targets)
        if op in ('transfer', 'new_transfer', 'ref_expr', 'mut_expr'):
            flow, value = self.expression(expr[1], environment, line, expected_array if op != 'new_transfer' else None)
            if op in ('ref_expr', 'mut_expr') and isinstance(value, Value):
                if expected_array is not None and expr[1][0] in ('array_literal', 'array_repeat'):
                    mode = 'mut' if op == 'mut_expr' else 'ref'
                    targets = frozenset({BorrowTarget('local')})
                    if value.mode == 'array_refs':
                        return flow, replace(value, container_borrow=True, container_mode=mode, reference_targets=targets)
                    return flow, replace(value, mode='array_' + mode, reference_targets=targets)
                if value.mode in ('ref', 'mut'):
                    self.fail(line, 'emprunt imbriqué non pris en charge : & sur un emprunt ajoute un niveau ; utiliser son nom')
                value = Value('ref' if op == 'ref_expr' else 'mut', value.typ, value.candidates,
                              value.fields, value.fresh_variants)
            return flow, value
        if op in ('scope', 'value_match'):
            body = expr[1] if op == 'value_match' else expr[2]
            return self.block(body, environment, valued=True, expected_array=expected_array)
        if op == 'if_expr':
            condition, yes, no = expr[1:]
            flow = self.condition(condition, environment, line)
            if 'next' not in flow:
                return flow, UNKNOWN
            left_env, right_env = environment.copy(), environment.copy()
            self.refine_handle_branches(condition, left_env, right_env)
            left, a = (self.expression(yes, left_env, line, expected_array) if isinstance(yes, tuple)
                       else self.block(yes, left_env, valued=True, expected_array=expected_array))
            right, b = (self.expression(no, right_env, line, expected_array) if isinstance(no, tuple)
                        else self.block(no, right_env, valued=True, expected_array=expected_array))
            self.join_environments(environment, ((left, left_env), (right, right_env)))
            candidates, returning = set(), []
            kind, typ = None, None
            if 'next' in left and 'next' in right:
                a, b = self.unify_handle_values([a, b], line)
            for branch, value in ((left, a), (right, b)):
                if 'next' not in branch:
                    continue
                if not isinstance(value, Value) or value.mode not in (
                        'owned', 'scalar', 'array', 'array_refs', 'handle_option', 'buffered_handle_exchange',
                        'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'vector_split', 'task', 'execution', 'selection', 'ref', 'mut', *VALUE_MODES):
                    self.fail(line, 'une expression if exige une allocation transférée par <- ou une valeur copiable')
                if typ is not None and typ != value.typ:
                    self.fail(line, 'expression if : même type requis dans toutes les branches')
                if kind is not None and kind != value.mode:
                    self.fail(line, 'expression if : même mode requis dans toutes les branches')
                kind, typ = value.mode, value.typ
                candidates.update(value.candidates)
                returning.append(value)
            return ((flow - {'next'}) | left | right,
                    Value(kind, typ, frozenset(candidates), merge_fields(returning),
                          frozenset(arm for v in returning for arm in v.fresh_variants),
                          reference_targets=frozenset(t for v in returning for t in v.reference_targets),
                          copy_candidates=frozenset(c for v in returning for c in v.copy_candidates),
                          payload_reference=any(v.payload_reference for v in returning),
                          rows=merge_reference_rows(returning),
                          owned_fields=merge_reference_rows(returning, 'owned_fields'),
                          structure_origins=frozenset(o for v in returning for o in v.structure_origins),
                          structure_choices=merge_structure_choices(returning),
                          handle_items=merge_handle_items(returning),
                          exchange_payloads=merge_exchange_payloads(returning),
                          exchange_values=merge_exchange_values(returning),
                          input_item_history=merge_input_item_history(returning),
                          input_items_changed=any(value.input_items_changed for value in returning),
                          input_items_written=any(value.input_items_written for value in returning),
                          task_sources=frozenset(source for value in returning for source in value.task_sources),
                          task_result_sources=frozenset(source for value in returning for source in value.task_result_sources),
                    task_result_fields=merge_task_result_fields(returning),
                    task_result_shapes=merge_task_result_shapes(returning),
                    task_result_handle_pools=frozenset().union(*(value.task_result_handle_pools for value in returning)),
                          pending_structure_calls=frozenset(call for value in returning for call in value.pending_structure_calls),
                          pending_structure_complete=all(value.pending_structure_complete for value in returning),
                          deferred_map_paths=merge_deferred_map_paths(returning),
                    task_forward_only=all(value.task_forward_only for value in returning),
                    task_parameters=frozenset(index for value in returning for index in value.task_parameters),
                    deferred_field_updates=frozenset(update for value in returning for update in value.deferred_field_updates),
                    deferred_guarded_writes=frozenset(update for value in returning for update in value.deferred_guarded_writes),
                    deferred_definite_fields=merge_deferred_definite_fields(returning),
                    deferred_suspension_updates=merge_task_suspensions(returning),
                    deferred_owned_updates=merge_task_owned_updates(returning, 'deferred_owned_updates'),
                    deferred_vector_updates=frozenset(update for value in returning for update in value.deferred_vector_updates),
                    deferred_suspension_owned=merge_task_owned_updates(returning, 'deferred_suspension_owned'),
                    deferred_suspension_vectors=merge_task_vector_updates(returning, 'deferred_suspension_vectors'),
                    task_may_suspend=merge_task_may_suspend(returning),
                    absent_owned_payload=bool(returning) and all(value.absent_owned_payload for value in returning)))
        if op == 'struct_copy':
            source = self.lookup(expr[1], environment, line)
            original = self.lookup(expr[2], environment, line)
            if not isinstance(source, SourceOrigin) or not isinstance(original, Value) or original.typ != source.element:
                self.fail(line, 'pool.copy : type du porteur incompatible avec le pool')
            return {'next'}, Value('owned', original.typ, frozenset({ResultCandidate('fresh', source=source)}),
                                   original.fields, frozenset({''}), structure_origins=frozenset({id(expr)}))
        if op in ('new', 'new_enum'):
            values = [expr[2]] if op == 'new' else [v for _, v in expr[4]]
            flow, evaluated = {'next'}, []
            for value in values:
                if 'next' not in flow:
                    return flow, UNKNOWN
                part, field_value = self.expression(value, environment, line)
                evaluated.append(field_value)
                flow = (flow - {'next'}) | part
            if 'next' not in flow:
                return flow, UNKNOWN
            source = (SourceOrigin('local_value', id(expr), 'data stack implicite', expr[2])
                      if op == 'new_enum' and expr[1] is None
                      else self.lookup(expr[1], environment, line))
            if not isinstance(source, SourceOrigin):
                self.fail(line, f"'{expr[1]}' n'est pas une source de stockage")
            typ = expr[3] if op == 'new' else expr[2] or source.element
            arm = expr[3] if op == 'new_enum' else None
            if op == 'new' and expr[4:] == ('pool_default',) and ('' in self.analyzer.enums.get(source.element, {}) or source.element in ('String', *VECTOR_TYPES)):
                typ, arm = source.element, ''
            fields, owned_fields = [], []
            if op == 'new_enum':
                declarations = dict(self.analyzer.enums.get(typ, {}).get(expr[3], ()))
                for (name, _), value in zip(expr[4], evaluated):
                    declared = declarations.get(name, '')
                    capability = reference_type(declared)
                    if declared.startswith('A<') and isinstance(value, Value):
                        owned_fields.append((f'{expr[3]}.{name}', value))
                        fields.extend((f'{expr[3]}.{name}/{path}', targets) for path, targets in value.fields)
                    if capability and isinstance(value, Value):
                        if capability[0] == 'mut' and value.mode != 'mut':
                            self.fail(line, 'champ mutable : emprunt mutable requis')
                        key = f'{expr[3]}.{name}'
                        fields.append((key, stored_targets(value)))
                        self.record_stored_references(stored_targets(value))
                        fields.extend((f'{key}/{path}', self.detached_field_targets(value, path))
                                      for path, targets in value.fields if targets)
            return flow, Value('owned', typ, frozenset({ResultCandidate('fresh', source=source)}),
                               tuple(fields), frozenset({arm}) if arm is not None else frozenset(),
                               owned_fields=tuple(owned_fields),
                               structure_origins=frozenset({id(expr)}) if typ in (*HANDLE_VECTORS, *REFERENCE_VECTORS, *INLINE_VECTOR_ELEMENTS) or typ in self.analyzer.enums else frozenset(),
                               handle_items=() if typ in (*HANDLE_VECTORS, *REFERENCE_VECTORS, *INLINE_VECTOR_ELEMENTS) else None)
        if op == 'call':
            # A method is desugared to a temporary call tuple on each pass.
            # Provenance belongs to the original, stable source expression.
            call_id = id(expr if call_site is None else call_site)
            name, args = expr[1:]
            if name in self.analyzer.async_functions:
                from async_lowering import borrowed_result_paths, int_reference_row, owned_result_parameters
                declaration = self.analyzer.async_definition(name)
                result_paths = {}
                for index, path in borrowed_result_paths(declaration, self.analyzer.async_functions, self.fail, {},
                                                        sync_result_contract=self.analyzer.sync_result_contract):
                    result_paths.setdefault(index, []).append(path)
                owned_indexes = owned_result_parameters(declaration, self.analyzer.async_functions,
                                                       sync_result=self.analyzer.sync_summary)
                task_result_sources = set()
                task_result_fields = {}
                result_shapes = []
                result_mode = declaration.args[2][0]
                targets, captures, task_sources = set(), [], set()
                captured_actuals = []
                flow = {'next'}
                for index, arg in enumerate(args):
                    if 'next' not in flow:
                        break
                    part, value = self.expression(arg, environment, line)
                    flow = (flow - {'next'}) | part
                    captured_actuals.append(value)
                    if index in getattr(declaration, 'cell_reference_parameters', ()):
                        self.record_stored_references(borrowed_targets(value))
                    if index < len(declaration.args[1]) and isinstance(value, SourceOrigin):
                        _, capture_mode, capture_type = declaration.args[1][index]
                        if capture_type.startswith('Pool<') and capture_mode in ('ref', 'mut'):
                            target = (BorrowTarget('parameter', value.index) if value.kind == 'source_parameter'
                                      else BorrowTarget('local'))
                            captures.append((f'{capture_mode}.{index}', frozenset({target})))
                            task_sources.add(value)
                            if index in owned_indexes:
                                task_result_sources.add(value)
                    if index < len(declaration.args[1]) and isinstance(value, Value):
                        capture_mode = declaration.args[1][index][1]
                        if capture_mode in ('ref', 'mut', 'array_ref', 'array_mut'):
                            origins = borrowed_targets(value) or frozenset({BorrowTarget('local')})
                            exclusive = capture_mode in ('mut', 'array_mut') or value.mode in ('mut', 'array_mut') or any(
                                origin.kind in ('parameter', 'inline_field_parameter', 'array_parameter')
                                and origin.carrier_kind != 'detached_field_parameter'
                                and self.params[origin.parameter][1] in ('mut', 'array_mut')
                                for origin in origins)
                            captures.append((f'{"mut" if exclusive else "ref"}.{index}', origins))
                        elif capture_mode in ASYNC_CAPTURE_VIEW_MODES:
                            origins = text_origins(value)
                            if origins:
                                access = 'mut' if capture_mode in SHARED_VECTOR_SLICE_MODES else 'ref'
                                captures.append((f'{access}.{index}', origins))
                        elif capture_mode in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange'):
                            owned_paths, reference_paths = self.owned_capture_paths(value)
                            for field, (access, _) in reference_paths.items():
                                origins = self.owned_capture_field_targets(value, field)
                                captures.append((f'{access}.{index}/{field}', origins))
                            sources = {candidate.storage() for candidate in value.candidates}
                            task_sources.update(sources or {SourceOrigin('local', -1, 'capture')})
                            for field in owned_paths:
                                task_sources.update(self.owned_capture_storage(value, field))
                            if index in owned_indexes:
                                task_result_sources.update(sources or {SourceOrigin('local', -1, 'capture')})
                                for path in owned_paths:
                                    task_result_fields[path] = task_result_fields.get(path, frozenset()) | frozenset(self.owned_capture_storage(value, path))
                    if index in result_paths:
                        origins = borrowed_targets(value) if isinstance(value, Value) else ()
                        _, capture_mode, capture_type = declaration.args[1][index]
                        if isinstance(value, Value) and int_reference_row(capture_type, capture_mode):
                            origins = self.reference_row_result_targets(value, capture_type, capture_mode, result_paths[index])
                        elif isinstance(value, Value) and '' in self.analyzer.enums.get(capture_type, {}):
                            origins = self.async_structure_result_targets(value, capture_type, result_paths[index])
                        for origin in origins or (BorrowTarget('local'),):
                            if (result_mode == 'ref' and origin.kind == 'parameter'
                                    and self.params[origin.parameter][1] == 'mut'):
                                origin = replace(origin, kind='exclusive_join_parameter')
                            targets.add(origin)
                field_summary = getattr(declaration, 'field_effect_summary', None)
                from async_result_storage import task_result_origins
                output_sources = task_result_origins(declaration, captured_actuals)
                if output_sources is not None:
                    task_result_sources = set(output_sources)
                    task_sources.update(output_sources)
                from async_result_storage import pool_result_graph
                graph = pool_result_graph(declaration, self.analyzer.enums)
                if graph is not None:
                    def resolve_graph_sources(symbols):
                        sources = set()
                        for symbol in symbols:
                            if symbol.kind == 'task_output':
                                sources.add(symbol)
                                continue
                            actual = captured_actuals[symbol.index]
                            if symbol.kind == 'source_parameter' and isinstance(actual, SourceOrigin):
                                sources.add(actual)
                            elif symbol.kind == 'allocation_parameter' and isinstance(actual, Value):
                                sources.update(candidate.storage() for candidate in actual.candidates)
                            elif symbol.kind == 'vector_element_parameter' and isinstance(actual, Value):
                                items = possible_handle_items(actual.handle_items)
                                if items is None:
                                    sources.add(SourceOrigin('local', -1, 'capture'))
                                else:
                                    sources.update(candidate.storage() for candidate in items)
                            elif symbol.kind == 'allocation_field_parameter' and isinstance(actual, Value):
                                sources.update(self.owned_capture_storage(actual, symbol.name))
                            else:
                                sources.add(SourceOrigin('local', -1, 'capture'))
                        return frozenset(sources)
                    task_result_sources = set(resolve_graph_sources(graph[0]))
                    task_sources.update(task_result_sources)
                    task_result_fields = {path: resolve_graph_sources(symbols) for path, symbols in graph[1]}
                if field_summary and field_summary.complete and result_mode in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option'):
                    result_shapes = [Value('owned', declaration.args[2][1],
                        task_result_shapes=self.resolved_owned_shapes(field_summary.completion_result, captured_actuals))]
                pending = self.instantiate_deferred_fields(field_summary.structure_fields, captured_actuals) if (
                    field_summary and field_summary.complete) else frozenset()
                suspended = getattr(field_summary, 'suspension_result', None)
                suspension_known = suspended is not None
                prefixes = self.instantiate_deferred_fields(suspended.structure_fields, captured_actuals) if suspension_known else None
                handle_pools = resolve_handle_pool_origins(
                    getattr(declaration, 'async_returned_handle_pools', ()),
                    {index: value.task_result_handle_pools for index, value in enumerate(captured_actuals)
                     if isinstance(value, Value) and value.mode == 'async_execution'})
                return flow, Value('task', name, fields=tuple(captures), reference_targets=frozenset(targets),
                                   task_result_handle_pools=handle_pools,
                                   deferred_vector_updates=self.instantiate_deferred_vectors(
                                       self.vector_update_sources(field_summary.completion_result.vector_writes), captured_actuals)
                                       if field_summary and field_summary.complete else frozenset(),
                                   deferred_owned_updates=self.instantiate_deferred_owned(
                                       field_summary.completion_result.owned_field_writes, captured_actuals, environment)
                                       if field_summary and field_summary.complete else frozenset(),
                                   deferred_suspension_owned=self.instantiate_deferred_owned(
                                       suspended.owned_field_writes, captured_actuals, environment) if suspension_known else None,
                                   deferred_suspension_updates=prefixes,
                                   deferred_suspension_vectors=self.instantiate_deferred_vectors(
                                       self.vector_update_sources(suspended.vector_writes), captured_actuals) if suspension_known else None,
                                   task_may_suspend=field_summary.may_suspend if suspension_known else None,
                                   deferred_field_updates=pending,
                                   task_sources=frozenset(task_sources), task_result_sources=frozenset(task_result_sources),
                                   task_result_fields=tuple(sorted(task_result_fields.items())),
                                   task_result_shapes=merge_task_result_shapes(result_shapes))
            if name not in self.analyzer.functions:
                self.fail(line, f"fonction inconnue '{name}'")
            params = self.analyzer.functions[name].args[1]
            if len(args) != len(params):
                self.fail(line, f"'{name}' attend {len(params)} argument(s), reçu {len(args)}")
            actuals = []
            flow = {'next'}
            for (_, mode, typ), arg in zip(params, args):
                if 'next' not in flow:
                    return flow, UNKNOWN
                expected = typ if mode in ('array', 'array_refs', 'array_refs_owned', 'array_ref', 'array_mut') else None
                part, value = self.expression(arg, environment, line, expected)
                flow = (flow - {'next'}) | part
                if mode == 'execution':
                    value = self.public_handle_value(value, typ, line)
                actuals.append(value)
            if 'next' not in flow:
                return flow - {'next'}, UNKNOWN
            for index in self.analyzer.infer(name).stored_reference_parameters:
                self.record_stored_references(borrowed_targets(actuals[index]))
            if not self.analyzer.effects[name].may_return:
                return flow - {'next'}, UNKNOWN
            self.check_call_actuals(name, actuals, line)
            for (parameter_name, _, parameter_type), actual in zip(params, actuals):
                if reference_array_shape(parameter_type) and (
                        not isinstance(actual, Value) or actual.typ != parameter_type):
                    self.fail(line, f"'{parameter_name}' attend un tableau {parameter_type}")
            if any(mode == 'mut' and typ.startswith('A<') and typ != f'A<{HANDLE_VECTOR}>' for _, mode, typ in params):
                self.invalidate_handle_items(environment)
            summary = self.analyzer.infer(name)
            for index in summary.task_wait_parameters:
                if isinstance(actuals[index], Value):
                    self.task_wait_parameters.update(actuals[index].task_parameters)
                    self.apply_deferred_field_updates(actuals[index], environment, line)
            for index, field, child in reversed(summary.owned_field_writes):
                projected_receiver = args[index][0] not in ('name', 'mut')
                if projected_receiver and not (isinstance(actuals[index], Value) and
                        (actuals[index].inline_path or actuals[index].owned_path)):
                    continue
                receiver = '\0owned_write_receiver' if projected_receiver else args[index][1]
                if projected_receiver:
                    environment[receiver] = actuals[index]
                owner = environment.get(receiver)
                if not isinstance(owner, Value):
                    continue
                previous = self.owned_field_at(environment, owner, field)
                updated = self.resolve_owned_child(child, actuals, previous)
                self.update_owned_field(environment, receiver, owner, field, updated)
                if projected_receiver:
                    environment.pop(receiver)
            if summary.handle_writes:
                write_fields = dict(summary.handle_write_fields)
                inputs = [
                    environment.get(value.storage_owner, value)
                    if isinstance(value, Value) and value.typ.startswith('A<') else value
                    for value in actuals]
                for parameter, candidates in summary.handle_writes:
                    handle = actuals[parameter]
                    if not isinstance(handle, Value) or handle.storage_owner not in environment:
                        self.fail(line, 'remplacement du handle injecté : receveur indéterminé')
                    fields = tuple((field, frozenset(origin for target in targets
                        for origin in (dict(inputs[target.parameter].fields).get(target.field, ())
                                       if target.kind == 'field_parameter'
                                       else self.array_update_targets(target, inputs[target.parameter]))))
                        for field, targets in write_fields.get(parameter, ()))
                    vectors = (self.apply_vector_result_candidates(candidates, inputs, call_id)
                               if is_handle_vector(inputs[parameter].typ) else ())
                    incoming = replace(inputs[parameter], candidates=self.resolve_vector_slot(candidates, inputs),
                                       fields=fields, handle_items=merge_handle_items(vectors) if vectors else None,
                                       input_item_history=merge_input_item_history(vectors) if vectors else None,
                                       input_items_changed=any(v.input_items_changed for v in vectors),
                                       input_items_written=any(v.input_items_written for v in vectors))
                    self.update_handle(environment, handle, incoming)
            for parameter, slots, exact, replacements, removals in summary.vector_writes:
                receiver = borrowed_array_name(args[parameter])
                if receiver is None or receiver not in environment:
                    self.fail(line, 'push sur vecteur emprunté exige un receveur nommé')
                if removals or not exact:
                    current = environment[receiver]
                    owner = current.storage_owner or receiver
                    vector = environment.get(owner)
                    if not isinstance(vector, Value) or vector.structure_origins != current.structure_origins:
                        self.fail(line, 'suppression sur vecteur emprunté exige un porteur déterminé')
                    history = vector.input_item_history
                    history = history.compose(removals) if history is not None and removals else history
                    items = remaining_handle_items(vector.handle_items, removals)
                    if not exact:
                        items, history = possible_handle_items(items), None
                    environment[owner] = replace(vector, handle_items=items, input_item_history=history,
                                                 input_items_changed=True)
                    if owner != receiver:
                        environment[receiver] = replace(environment[owner], mode=current.mode, storage_owner=owner)
                for payload in dict(summary.vector_write_payloads).get(parameter, ()):
                    incoming_payload = self.resolve_owned_child(payload, actuals, map_fields=True)
                    self.remember_handle_payload(environment, receiver, incoming_payload)
                for index, slot in replacements:
                    incoming = self.resolve_vector_slot(slot, actuals)
                    self.publish_handle_exchange(environment, (receiver, index, incoming, False))
                for slot in slots:
                    incoming = self.resolve_vector_slot(slot, actuals)
                    self.publish_handle_exchange(environment, (receiver, None, incoming, True), exact=exact)
            updated_arrays = {}
            for parameter, fields in summary.parameter_fields:
                argument = args[parameter]
                actual_name = borrowed_array_name(argument)
                updated = []
                for slot, targets in fields:
                    origins = set()
                    for target in targets:
                        actual = actuals[target.parameter]
                        if target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
                            candidates = reference_tree_targets(actual, target.field)
                            origins.update(
                                BorrowTarget('reserved_stored_array_parameter', candidate.parameter, candidate.field)
                                if target.kind == 'reserved_stored_array_parameter' and candidate.kind == 'stored_array_parameter'
                                else candidate for candidate in candidates)
                        elif target.kind == 'field_parameter':
                            origins.update(BorrowTarget('field_parameter', c.parameter, target.field)
                                           for c in actual.candidates if c.kind == 'parameter')
                        elif target.kind in ('inline_field_parameter', 'indirect_field_parameter'):
                            origins.update(self.inline_field_targets(actual, target.field, target.kind, target.carrier_kind, target.detached_prefix))
                        elif target.kind == 'detached_field_parameter':
                            origins.update(self.detached_field_targets(actual, target.field))
                        else:
                            origins.update(borrowed_targets(actual))
                    updated.append((slot, frozenset(origins)))
                rebuilt = rebuild_reference_tree(actuals[parameter], params[parameter][2], tuple(updated), fields, actuals)
                update_array_aliases(environment, actual_name, rebuilt.fields, actuals[parameter], rebuilt.rows)
                updated_arrays[parameter] = rebuilt
            for parameter, path, fields in summary.referent_fields:
                holder, slot = reference_tree_slot(actuals[parameter], path)
                row = dict(holder.rows)[slot]
                mapped = []
                for field, targets in fields:
                    mapped.append((field, frozenset(origin for target in targets
                        for origin in self.array_update_targets(target, actuals[target.parameter]))))
                rebuilt = rebuild_reference_tree(row, row.typ, mapped, fields, actuals)
                name = borrowed_array_name(args[parameter])
                update_array_aliases(environment, name, rebuilt.fields, row, rebuilt.rows)
            updated_structures = self.apply_structure_updates(summary, actuals, args, environment, line)
            if summary.mode in ('task', 'execution'):
                from async_lowering import borrowed_result_paths, int_reference_row
                declaration = self.analyzer.async_definition(summary.typ)
                result_paths = {}
                for index, path in borrowed_result_paths(declaration, self.analyzer.async_functions, self.fail, {},
                                                        sync_result_contract=self.analyzer.sync_result_contract):
                    result_paths.setdefault(index, []).append(path)
                captures = []
                row_result_targets = set()
                row_result_indexes = set()
                for key, targets in summary.borrowed_fields:
                    index = capture_index(key.partition('.')[2])
                    _, capture_mode, capture_type = declaration.args[1][index]
                    projects_row = index in result_paths and int_reference_row(capture_type, capture_mode)
                    projects_structure = index in result_paths and '' in self.analyzer.enums.get(capture_type, {})
                    if projects_row or projects_structure:
                        row_result_indexes.add(index)
                    exclusive = key.startswith('mut.')
                    origins = set()
                    for target in targets:
                        actual = actuals[target.parameter]
                        if isinstance(actual, SourceOrigin) and actual.kind == 'source_parameter':
                            origins.add(BorrowTarget('parameter', actual.index))
                        elif not isinstance(actual, Value):
                            origins.add(BorrowTarget('local'))
                        elif target.kind == 'task_capture_parameter':
                            for actual_key, actual_origins in capture_fields(actual.fields, target.field):
                                exclusive |= actual_key.startswith('mut.')
                                origins.update(actual_origins)
                        elif target.kind == 'owned_capture_field':
                            origins.update(self.owned_capture_field_targets(actual, target.field))
                        elif target.kind in ('utf8_parameter', 'string_parameter', 'vector_parameter'):
                            origins.update(text_origins(actual))
                        elif target.kind == 'detached_field_parameter':
                            origins.update(self.detached_field_targets(actual, target.field))
                        elif target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
                            origins.update(
                                replace(candidate, kind='reserved_stored_array_parameter')
                                if target.kind == 'reserved_stored_array_parameter' and candidate.kind == 'stored_array_parameter'
                                else candidate for candidate in reference_tree_targets(actual, target.field))
                        elif target.kind == 'inline_field_parameter' and target.carrier_kind == 'detached_field_parameter':
                            carrier_path, _, field = target.field.rpartition('/')
                            carrier = Value('ref', 'Int', reference_targets=self.detached_field_targets(actual, carrier_path))
                            origins.update(self.inline_field_targets(carrier, field))
                        elif target.kind in ('inline_field_parameter', 'indirect_field_parameter'):
                            origins.update(self.inline_field_targets(actual, target.field, target.kind,
                                                                    target.carrier_kind, target.detached_prefix))
                        else:
                            origins.update(borrowed_targets(actual) or {BorrowTarget('local')})
                        if projects_row or projects_structure:
                            if target.kind == 'task_capture_parameter' and isinstance(actual, Value):
                                projected = actual.reference_targets
                            elif projects_structure and capture_mode in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option') and '/' in key:
                                from array_syntax import owned_reference_paths
                                selected = key.partition('/')[2]
                                if not any('.' + '.'.join(path) == selected for path in result_paths[index]):
                                    continue
                                shared = any(path == selected and access == 'ref' and typ == 'Int'
                                             for path, access, typ in owned_reference_paths(self.analyzer.enums, capture_type))
                                projected = frozenset(replace(origin, kind='detached_field_parameter')
                                    if origin.kind == 'owned_capture_field' else origin for origin in origins) if shared else ()
                            elif projects_structure and isinstance(actual, Value):
                                carrier = Value(capture_mode, capture_type, reference_targets=frozenset(origins))
                                projected = self.async_structure_result_targets(carrier, capture_type, result_paths[index])
                            elif target.kind == 'array_parameter' and isinstance(actual, Value):
                                row = updated_arrays.get(target.parameter, actual)
                                projected = self.reference_row_result_targets(row, capture_type, capture_mode,
                                                                              result_paths[index])
                            else:
                                projected = ()
                            row_result_targets.update(projected or {BorrowTarget('local')})
                    mode = 'mut' if exclusive else 'ref'
                    from handle_types import is_public_handle
                    if not origins and capture_mode not in ASYNC_SHARED_VIEW_MODES and not is_public_handle(summary.typ):
                        origins.add(BorrowTarget('local'))
                    if origins:
                        captures.append((f"{mode}.{key.partition('.')[2]}", frozenset(origins)))
                captures = tuple(captures)
                reference_targets = capture_result_origins(
                    captures, result_paths.keys() - row_result_indexes, declaration.args[2][0] == 'ref')
                reference_targets |= frozenset(row_result_targets)
                def resolve_sources(symbols):
                    sources = set()
                    for source in symbols:
                        if source.kind == 'task_output':
                            sources.add(source)
                            continue
                        actual = actuals[source.index]
                        if source.kind == 'task_output_parameter' and isinstance(actual, Value):
                            from async_result_storage import output_origin
                            sources.update(output_origin(candidate.storage(), source.element)
                                           for candidate in actual.candidates)
                        elif source.kind == 'source_parameter' and isinstance(actual, SourceOrigin):
                            sources.add(actual)
                        elif source.kind == 'allocation_parameter' and isinstance(actual, Value) and actual.candidates:
                            sources.update(candidate.storage() for candidate in actual.candidates)
                        elif source.kind == 'vector_element_parameter' and isinstance(actual, Value):
                            items = possible_handle_items(actual.handle_items)
                            if items is None:
                                sources.add(SourceOrigin('local', -1, 'capture'))
                            else:
                                sources.update(candidate.storage() for candidate in items)
                        elif source.kind == 'allocation_field_parameter' and isinstance(actual, Value):
                            sources.update(self.owned_capture_storage(actual, source.name))
                        elif source.kind == 'task_result_field_parameter' and isinstance(actual, Value):
                            sources.update(dict(actual.task_result_fields).get(source.name, ()))
                        elif source.kind == 'task_parameter' and isinstance(actual, Value):
                            sources.update(actual.task_sources)
                        elif source.kind == 'task_result_parameter' and isinstance(actual, Value) and actual.task_result_sources:
                            sources.update(actual.task_result_sources)
                        else:
                            sources.add(SourceOrigin('local', -1, 'capture'))
                    return frozenset(sources)
                forwarded = [actuals[index] for index in summary.task_forward_parameters]
                prefix_base = frozenset() if summary.task_forward_only else (
                    self.instantiate_deferred_fields(summary.task_suspension_fields, actuals)
                    if summary.task_suspension_fields is not None else None)
                prefix_parts = [Value('task', summary.typ, deferred_suspension_updates=prefix_base,
                    deferred_suspension_vectors=frozenset() if summary.task_forward_only else (
                        self.instantiate_deferred_vectors(summary.task_suspension_vectors, actuals)
                        if summary.task_suspension_vectors is not None else None),
                    deferred_suspension_owned=frozenset() if summary.task_forward_only else (
                        self.instantiate_deferred_owned(summary.task_suspension_owned, actuals, environment)
                        if summary.task_suspension_owned is not None else None),
                    task_may_suspend=False if summary.task_forward_only else summary.task_may_suspend), *forwarded]
                return flow, Value(summary.mode, summary.typ, fields=captures, reference_targets=reference_targets,
                                   task_result_handle_pools=resolve_handle_pool_origins(
                                       summary.task_result_handle_pools,
                                       {index: value.task_result_handle_pools for index, value in enumerate(actuals)
                                        if isinstance(value, Value) and value.mode == 'async_execution'})
                                       | frozenset().union(*(value.task_result_handle_pools for value in forwarded)),
                                   deferred_vector_updates=self.instantiate_deferred_vectors(summary.task_vector_updates, actuals)
                                       | frozenset(update for value in forwarded for update in value.deferred_vector_updates),
                                   deferred_owned_updates=merge_task_owned_updates([
                                       Value('task', summary.typ, deferred_owned_updates=self.instantiate_deferred_owned(
                                           summary.task_owned_updates, actuals, environment)), *forwarded], 'deferred_owned_updates'),
                                   deferred_suspension_owned=merge_task_owned_updates(prefix_parts, 'deferred_suspension_owned'),
                    deferred_suspension_vectors=merge_task_vector_updates(prefix_parts, 'deferred_suspension_vectors'),
                                   deferred_suspension_updates=merge_task_suspensions(prefix_parts),
                                   task_may_suspend=merge_task_may_suspend(prefix_parts),
                                   pending_structure_calls=frozenset(call for index in summary.task_forward_parameters
                                       for call in actuals[index].pending_structure_calls) if summary.task_forward_only else frozenset(),
                                   pending_structure_complete=bool(forwarded) and summary.task_forward_only
                                       and all(value.pending_structure_complete for value in forwarded),
                                   deferred_map_paths=merge_deferred_map_paths(forwarded)
                                       if summary.task_forward_only else frozenset(),
                                   task_forward_only=summary.task_forward_only and all(
                                       actuals[index].task_forward_only for index in summary.task_forward_parameters),
                                   task_sources=resolve_sources(summary.task_sources),
                                   deferred_field_updates=self.instantiate_deferred_fields(summary.task_field_updates, actuals)
                                       | frozenset(update for index in summary.task_forward_parameters
                                                   for update in actuals[index].deferred_field_updates),
                                   task_parameters=frozenset(origin for index in summary.task_forward_parameters
                                                             for origin in actuals[index].task_parameters),
                                   task_result_sources=resolve_sources(summary.task_result_sources),
                                   task_result_fields=tuple((path, resolve_sources(sources)) for path, sources in summary.task_result_fields),
                                   task_result_shapes=self.instantiate_task_shapes(summary, actuals))
            if summary.mode in ('ref', 'mut'):
                targets = set()
                for target in summary.reference_targets:
                    actual = actuals[target.parameter]
                    if target.kind == 'async_handle_result':
                        origins = actual.reference_targets if isinstance(actual, Value) else ()
                        targets.update(origins or {BorrowTarget('local')})
                    elif target.kind == 'task_capture_parameter':
                        fields = actual.fields if isinstance(actual, Value) else ()
                        origins = capture_result_origins(fields, (target.field,), summary.mode == 'ref')
                        from handle_types import is_public_handle
                        if not origins and isinstance(actual, Value) and is_public_handle(actual.typ):
                            # Public result groups are alternatives. Conversion
                            # of a concrete handle may leave one group empty.
                            continue
                        if isinstance(actual, Value) and actual.mode in ('task', 'execution'):
                            from async_lowering import int_reference_row
                            declaration = self.analyzer.async_definition(actual.typ)
                            _, capture_mode, capture_type = declaration.args[1][capture_index(target.field)]
                            if (int_reference_row(capture_type, capture_mode)
                                    or '' in self.analyzer.enums.get(capture_type, {})):
                                origins = actual.reference_targets
                        targets.update(origins or {BorrowTarget('local')})
                    elif target.kind == 'exclusive_join_parameter':
                        origins = borrowed_targets(actual) if isinstance(actual, Value) else ()
                        targets.update(replace(origin, kind='exclusive_join_parameter')
                                       if origin.kind == 'parameter' else origin
                                       for origin in origins or (BorrowTarget('local'),))
                    elif target.kind in ('field_parameter', 'shared_field_parameter'):
                        origins = {projected_field_origin(origin, target) for origin in borrowed_targets(actual)
                                   } if isinstance(actual, Value) else set()
                        targets.update(origins or {BorrowTarget('local')})
                    elif target.kind in ('inline_field_parameter', 'indirect_field_parameter'):
                        targets.update(self.inline_field_targets(actual, target.field, target.kind, target.carrier_kind, target.detached_prefix))
                    elif target.kind == 'detached_field_parameter':
                        if (isinstance(actual, Value) and '/' in target.field
                                and actual.candidates and all(c.kind == 'fresh' for c in actual.candidates)
                                and actual.fresh_variants
                                and target.field.partition('.')[0] not in actual.fresh_variants):
                            continue
                        targets.update(self.detached_field_targets(actual, target.field))
                    elif target.kind == 'mutable_vector_parameter':
                        targets.update(self.mutable_vector_result_targets(actual, target.field))
                    elif target.kind == 'moved_field_parameter':
                        origins = dict(actual.fields).get(target.field, ()) if isinstance(actual, Value) else ()
                        targets.update(self.moved_field_origins(origins))
                    elif target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
                        targets.update(BorrowTarget('reserved_stored_array_parameter', candidate.parameter, candidate.field)
                                       if target.kind == 'reserved_stored_array_parameter' and candidate.kind == 'stored_array_parameter'
                                       else candidate for candidate in reference_tree_targets(actual, target.field))
                    elif target.kind == 'vector_parameter':
                        targets.update(text_origins(actual) if isinstance(actual, Value) else {BorrowTarget('local')})
                    elif target.kind == 'array_parameter':
                        origins = borrowed_targets(actual) if isinstance(actual, Value) else frozenset()
                        targets.update(origins or {BorrowTarget('local')})
                    elif isinstance(actual, Value):
                        targets.update(borrowed_targets(actual))
                if reference_array_shape(summary.typ):
                    mapped = []
                    for slot, origins in summary.borrowed_fields:
                        resolved = frozenset(origin for target in origins
                            for origin in self.array_update_targets(target, actuals[target.parameter]))
                        mapped.append((slot, resolved))
                    template = target_row_templates(actuals, summary.reference_targets)
                    prototype = template or Value('array_refs', summary.typ)
                    result = rebuild_reference_tree(prototype, summary.typ, mapped, summary.borrowed_fields, actuals)
                    return flow, replace(result, container_borrow=True, container_mode=summary.mode,
                                         reference_targets=frozenset(targets), payload_reference=True)
                fields = ()
                projected = []
                if summary.typ in self.analyzer.enums:
                    shared = {f'{arm}.{name}' for arm, declarations in self.analyzer.enums[summary.typ].items()
                              for name, declared in declarations
                              if (capability := reference_type(declared)) and capability[0] == 'ref'}
                    for target in summary.reference_targets:
                        actual = actuals[target.parameter]
                        if target.kind == 'parameter':
                            projected.append(replace(actual, fields=tuple(
                                (key, self.detached_field_targets(actual, key) if key in shared else origins)
                                for key, origins in actual.fields)))
                        elif target.kind == 'inline_field_parameter' and not target.carrier_kind:
                            from structure_views import project_fields
                            name = actual.storage_owner or (args[target.parameter][1]
                                if args[target.parameter][0] in ('ref', 'mut', 'name', 'reborrow') else None)
                            projected.append(replace(actual, typ=summary.typ, mode=summary.mode,
                                fields=project_fields(actual.fields, target.field), storage_owner=name,
                                owned_fields=project_fields(actual.owned_fields, target.field),
                                inline_path=(actual.inline_path + '.' if actual.inline_path else '') + target.field))
                        elif target.kind in ('detached_field_parameter', 'shared_field_parameter',
                                             'moved_field_parameter', 'field_parameter'):
                            if target.kind == 'field_parameter' and target.field.startswith('.'):
                                actual = updated_structures.get(target.parameter, actual)
                            projected.append(replace(actual, fields=nested_reference_fields(actual.fields, target.field)))
                    fields = merge_fields(projected)
                structure_origins = frozenset(origin for t in summary.reference_targets if t.kind == 'parameter'
                                              for origin in actuals[t.parameter].structure_origins)
                handle_slot = None
                if summary.vector_slot is not None:
                    parameter, index = summary.vector_slot
                    root = actuals[parameter]
                    if isinstance(root, Value) and root.structure_origins:
                        handle_slot = (root.structure_origins, index)
                candidates = frozenset(candidate for target in summary.reference_targets
                    if target.kind in ('parameter', 'inline_field_parameter') and not target.carrier_kind
                    for candidate in (actuals[target.parameter].copy_candidates or actuals[target.parameter].candidates)) if summary.typ in self.analyzer.enums else frozenset()
                return flow, Value(summary.mode, summary.typ, copy_candidates=candidates, fields=fields, reference_targets=frozenset(targets),
                                   owned_fields=merge_owned_values(projected).owned_fields if projected else (),
                                   storage_owner=projected[0].storage_owner if len(projected) == 1 else None,
                                   inline_path=projected[0].inline_path if len(projected) == 1 else '',
                                   structure_choices=merge_structure_choices(projected) if len(projected) > 1 else (),
                                   structure_origins=structure_origins, handle_slot=handle_slot,
                                   payload_reference=summary.payload_reference or any(
                                       actuals[t.parameter].payload_reference for t in summary.reference_targets))
            if summary.mode == 'array_refs':
                fields = []
                for slot, targets in summary.borrowed_fields:
                    origins = set()
                    for target in targets:
                        actual = actuals[target.parameter]
                        if isinstance(actual, Value):
                            if target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
                                origins.update(reference_tree_targets(actual, target.field))
                            elif target.kind in ('field_parameter', 'shared_field_parameter'):
                                origins.update(BorrowTarget(target.kind, candidate.parameter, target.field)
                                               for candidate in actual.candidates if candidate.kind == 'parameter')
                            elif target.kind in ('inline_field_parameter', 'indirect_field_parameter'):
                                origins.update(self.inline_field_targets(actual, target.field, target.kind, target.carrier_kind, target.detached_prefix))
                            elif target.kind == 'detached_field_parameter':
                                origins.update(self.detached_field_targets(actual, target.field))
                            elif target.kind == 'moved_field_parameter':
                                origins.update(self.moved_field_origins(dict(actual.fields).get(target.field, ())))
                            else:
                                origins.update(borrowed_targets(actual))
                    fields.append((slot, frozenset(origins or {BorrowTarget('local')})))
                prototype = Value('array_refs', summary.typ, container_origins=frozenset({('call', call_id)}))
                return flow, rebuild_reference_tree(prototype, summary.typ, fields, summary.borrowed_fields, actuals)
            if summary.mode not in ('owned', 'handle_option', 'buffered_handle_exchange', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
                if summary.mode in UTF8_BORROW_MODES or summary.mode == 'vector_split':
                    targets = set()
                    for target in summary.reference_targets:
                        actual = actuals[target.parameter]
                        if target.kind == 'task_capture_parameter' and isinstance(actual, Value):
                            capture_type = self.analyzer.async_functions[actual.typ].args[1][capture_index(target.field)][2]
                            targets.update(replace(origin, kind='string_parameter')
                                           if origin.kind == 'parameter' and capture_type == 'String' else origin
                                           for _, origins in capture_fields(actual.fields, target.field)
                                           for origin in origins)
                            continue
                        origins = text_origins(actual) if isinstance(actual, Value) else frozenset()
                        targets.update(origins or ({BorrowTarget('local')} if target.kind in ('array_parameter', 'string_parameter', 'vector_parameter') else set()))
                    return flow, Value(summary.mode, summary.typ, reference_targets=frozenset(targets))
                if summary.mode in VALUE_MODES:
                    return flow, Value(summary.mode, summary.typ)
                return flow, SCALAR if summary.mode == 'scalar' else VOID
            def resolve_candidates(entries):
                candidates = set()
                for candidate in entries:
                    if candidate.kind == 'parameter':
                        actual = actuals[candidate.parameter]
                        if not isinstance(actual, Value) or actual.mode not in ('owned', 'handle_option', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
                            self.fail(line, 'seule une allocation explicite est déplaçable')
                        candidates.update(actual.candidates)
                    elif candidate.kind == 'task_capture':
                        actual = actuals[candidate.parameter]
                        candidates.update(async_owned_candidates(actual.task_result_sources))
                    elif candidate.kind == 'owned_projection':
                        candidates.update(self.project_owned_value(actuals[candidate.parameter],
                                                                   candidate.field_path, summary.typ).candidates)
                    elif candidate.kind == 'exchange_parameter':
                        actual = actuals[candidate.parameter]
                        if not isinstance(actual, Value) or len(actual.exchange_payloads) != 2:
                            self.fail(line, 'argument Result non Copy attendu')
                        candidates.update(actual.exchange_payloads[candidate.item_index])
                    elif candidate.kind == 'vector_element':
                        actual = actuals[candidate.parameter]
                        items = vector_result_candidates(actual, candidate.item_index,
                            last=candidate.item_index == VECTOR_LAST_ITEM, excluded=candidate.excluded_items,
                            tail_offset=candidate.tail_offset)
                        if summary.mode == 'handle_option' and actual.handle_items == () and not items:
                            continue
                        candidates.update(items or {UNKNOWN_HANDLE_ITEM})
                    elif candidate.source.kind == 'local_value':
                        candidates.add(replace(candidate, source=replace(candidate.source, index=call_id)))
                    else:
                        source = actuals[candidate.source.index]
                        if candidate.source.kind == 'allocation_parameter' and isinstance(source, Value):
                            for item in source.copy_candidates or source.candidates:
                                origin = item.storage()
                                if origin.kind == 'local_value':
                                    origin = replace(origin, index=call_id, element=summary.typ)
                                candidates.add(ResultCandidate('fresh', source=origin))
                            continue
                        if not isinstance(source, SourceOrigin):
                            self.fail(line, f"'{params[candidate.source.index][0]}' n'est pas une source de stockage")
                        candidates.add(ResultCandidate('fresh', source=source))
                return frozenset(candidates)
            if summary.same_parameter is not None and not summary.owned_fields and any(
                    field.startswith('A<') for fields in self.analyzer.enums.get(summary.typ, {}).values()
                    for _, field in fields):
                return flow, actuals[summary.same_parameter]
            candidates = resolve_candidates(summary.candidates)
            fields = []
            for field, targets in summary.borrowed_fields:
                resolved = frozenset()
                for target in targets:
                    actual = actuals[target.parameter]
                    if target.kind == 'parameter':
                        resolved |= stored_targets(actual)
                    elif target.kind == 'task_capture_parameter':
                        resolved |= frozenset(origin for _, origins in capture_fields(actual.fields, target.field)
                                              for origin in origins)
                    elif target.kind == 'shared_field_parameter' and target.detached_prefix:
                        resolved |= frozenset(projected_field_origin(origin, target)
                                              for origin in borrowed_targets(actual)) or frozenset({BorrowTarget('local')})
                    elif target.kind in ('reserved_field_parameter', 'shared_field_parameter'):
                        origins = frozenset(BorrowTarget(target.kind, c.parameter, target.field)
                                            for c in actual.candidates if c.kind == 'parameter')
                        resolved |= origins or frozenset({BorrowTarget('local')})
                    elif target.kind == 'detached_field_parameter':
                        resolved |= self.detached_field_targets(actual, target.field)
                    elif target.kind in ('inline_field_parameter', 'indirect_field_parameter'):
                        resolved |= self.array_update_targets(target, actual)
                    else:
                        resolved |= dict(actual.fields).get(target.field, frozenset())
                fields.append((field, resolved))
            fresh_variants = summary.fresh_variants | frozenset(
                arm for candidate in summary.candidates if candidate.kind == 'parameter'
                for arm in actuals[candidate.parameter].fresh_variants)
            if is_handle_vector(summary.typ):
                vectors = self.apply_vector_result_candidates(summary.candidates, actuals, call_id)
                return flow, Value(summary.mode, summary.typ, frozenset(candidates), fresh_variants=fresh_variants,
                                   handle_items=merge_handle_items(vectors),
                                   handle_payloads=tuple(self.resolve_owned_child(value, actuals, map_fields=True)
                                                         for value in summary.vector_values),
                                   input_item_history=merge_input_item_history(vectors),
                                   input_items_changed=any(vector.input_items_changed for vector in vectors),
                                   input_items_written=any(vector.input_items_written for vector in vectors),
                                   structure_origins=frozenset(origin for vector in vectors
                                                               for origin in vector.structure_origins))
            shared_items = None
            shared_changed = False
            if summary.typ in REFERENCE_VECTORS:
                shared_items = dict(fields).get('.items', frozenset())
                shared_changed = True
                if summary.shared_vector_passthrough is not None:
                    original = actuals[summary.shared_vector_passthrough]
                    shared_items = original.handle_items
                    shared_changed = original.input_items_changed
                elif summary.shared_vector_layout is not None:
                    shared_items = tuple(frozenset(origin for target in slot
                        for origin in self.array_update_targets(target, actuals[target.parameter]))
                        for slot in summary.shared_vector_layout)
            owned_fields = merge_reference_rows([
                                   self.project_owned_value(actuals[item.parameter], item.field_path, summary.typ)
                                   for item in summary.candidates if item.kind == 'owned_projection'
                               ] + [Value('owned', summary.typ, owned_fields=tuple(
                                   (field, self.resolve_owned_child(child, actuals, map_fields=True))
                                   for field, child in summary.owned_fields))], 'owned_fields')
            if summary.same_parameter is not None:
                owned_fields = tuple((dict(actuals[summary.same_parameter].owned_fields) | dict(owned_fields)).items())
            return flow, Value(summary.mode, summary.typ, frozenset(candidates), tuple(fields), fresh_variants,
                               owned_fields=owned_fields,
                               handle_payloads=tuple(self.resolve_owned_child(value, actuals, map_fields=True)
                                                     for value in summary.exchange_values if value.candidates),
                               exchange_payloads=tuple(resolve_candidates(arm) for arm in summary.exchange_payloads),
                               exchange_values=tuple(self.resolve_owned_child(value, actuals, map_fields=True)
                                                     for value in summary.exchange_values),
                               structure_origins=frozenset({call_id})
                               if summary.typ in REFERENCE_VECTORS or '' in self.analyzer.enums.get(summary.typ, {})
                               else frozenset(),
                               handle_items=shared_items, input_items_changed=shared_changed,
                               absent_owned_payload=not candidates and (summary.absent_owned_payload or
                                   bool(summary.candidates) and all(item.kind == 'parameter'
                                       and actuals[item.parameter].absent_owned_payload
                                       for item in summary.candidates)))
        return {'next'}, UNKNOWN

    def record_loop_edge(self, outcome, environment):
        if not self.loops:
            return
        frame = self.loops[-1]
        visible = environment.copy()
        for outer, shadows in reversed(self.blocks[frame['depth']:]):
            visible = {name: restore_array_binding(shadows.get(name, visible[name]), visible) for name in outer}
        frame[outcome].append(({'next'}, visible))

    def loop(self, node, environment, valued=False, expected_array=None):
        frame = {'depth': len(self.blocks), 'values': [] if valued else None,
                 'break': [], 'continue': [], 'expected_array': expected_array}
        initial = environment.copy()
        head = initial.copy()
        self.loops.append(frame)
        try:
            for _ in range(len(head) * 2 + 3):
                frame['break'].clear()
                frame['continue'].clear()
                if valued:
                    frame['values'].clear()
                tail = head.copy()
                outcomes, _ = self.block(node.args[0], tail)
                edges = frame['continue'][:]
                if 'next' in outcomes:
                    edges.append(({'next'}, tail))
                following = initial.copy()
                self.join_environments(following, [({'next'}, initial), *edges])
                if following == head:
                    break
                head = following
            else:
                self.fail(node.line, 'prototype : résultats de boucle sans convergence')
        finally:
            self.loops.pop()
        flow = outcomes & {'return'}
        if frame['break']:
            flow.add('next')
            self.join_environments(environment, frame['break'])
        values = frame['values']
        if not values:
            return flow, UNKNOWN
        first = values[0]
        return flow, Value(
            first.mode, first.typ,
            frozenset(c for v in values for c in v.candidates), merge_fields(values),
            frozenset(arm for v in values for arm in v.fresh_variants),
            frozenset(t for v in values for t in v.reference_targets), any(v.payload_reference for v in values), frozenset(o for v in values for o in v.container_origins), merge_container_positions(values), any(value.container_borrow for value in values), next(iter(values)).container_mode, merge_reference_rows(values),
            structure_origins=frozenset(o for value in values for o in value.structure_origins),
            structure_choices=merge_structure_choices(values),
            owned_fields=merge_reference_rows(values, 'owned_fields'),
            handle_items=merge_handle_items(values),
                    handle_payloads=tuple(dict.fromkeys(item for value in values for item in value.handle_payloads)),
            exchange_payloads=merge_exchange_payloads(values),
                          exchange_values=merge_exchange_values(values),
            input_item_history=merge_input_item_history(values),
            input_items_changed=any(value.input_items_changed for value in values),
            input_items_written=any(value.input_items_written for value in values),
            task_sources=frozenset(source for value in values for source in value.task_sources),
            task_result_sources=frozenset(source for value in values for source in value.task_result_sources),
                    task_result_fields=merge_task_result_fields(values),
                    task_result_shapes=merge_task_result_shapes(values),
                    task_result_handle_pools=frozenset().union(*(value.task_result_handle_pools for value in values)),
            pending_structure_calls=frozenset(call for value in values for call in value.pending_structure_calls),
            pending_structure_complete=all(value.pending_structure_complete for value in values),
            deferred_map_paths=merge_deferred_map_paths(values),
                    task_forward_only=all(value.task_forward_only for value in values),
                    task_parameters=frozenset(index for value in values for index in value.task_parameters),
                    deferred_field_updates=frozenset(update for value in values for update in value.deferred_field_updates),
                    deferred_guarded_writes=frozenset(update for value in values for update in value.deferred_guarded_writes),
                    deferred_definite_fields=merge_deferred_definite_fields(values),
                    deferred_suspension_updates=merge_task_suspensions(values),
                    deferred_owned_updates=merge_task_owned_updates(values, 'deferred_owned_updates'),
                    deferred_vector_updates=frozenset(update for value in values for update in value.deferred_vector_updates),
                    deferred_suspension_owned=merge_task_owned_updates(values, 'deferred_suspension_owned'),
                    deferred_suspension_vectors=merge_task_vector_updates(values, 'deferred_suspension_vectors'),
                    task_may_suspend=merge_task_may_suspend(values),
                    absent_owned_payload=all(value.absent_owned_payload for value in values))

    def observe_suspension(self, environment, line):
        """Extension point: synchronous completion inference has no prefix exits."""

    def nodes(self, nodes, environment, valued=False, shadows=None, expected_array=None):
        flow, tail = {'next'}, UNKNOWN
        for index, node in enumerate(nodes):
            if 'next' not in flow:
                break
            op, args, line = node.op, node.args, node.line
            if op == 'call' and args[0][0] == 'method_call':
                carrier = environment.get(args[0][1][1])
                structure = isinstance(carrier, Value) and '' in self.analyzer.enums.get(carrier.typ, {})
                builtin = builtin_method_statement(args[0], structure, lambda message: self.fail(line, message))
                if builtin is not None:
                    op, args = builtin
            part = {'next'}
            if op == 'yield':
                self.observe_suspension(environment, line)
            elif op == 'set_expr':
                part, _ = self.expression(args[1], environment, line)
            elif op in ('var', 'assign'):
                name, expr = args
                if expr[0] == 'source':
                    value = SourceOrigin('local', id(node), name, expr[3] if expr[1] == 'pool' else None)
                else:
                    previous = environment.get(name)
                    expected = node.annotation
                    if (op == 'assign' and isinstance(previous, Value) and previous.mode in ('array', 'array_refs')
                            and not previous.container_borrow):
                        expected = previous.typ
                    part, value = self.expression(expr, environment, line, expected)
                if 'next' in part:
                    annotation = fixed_array_shape(node.annotation) if node.annotation else None
                    if annotation and annotation[0] == 'u8' and isinstance(value, Value) and value.mode == 'array':
                        value = replace(value, typ=node.annotation)
                    previous = environment.get(name)
                    if op == 'var' and shadows is not None and name in environment:
                        shadows.setdefault(name, previous)
                    if (op == 'assign' and isinstance(previous, Value) and previous.mode == 'array_refs' and not previous.container_borrow
                            and isinstance(value, Value) and value.mode == 'array_refs'):
                        update_array_aliases(environment, name, value.fields)
                        continue
                    if not (op == 'assign' and isinstance(previous, Value)
                            and previous.mode == 'owned' and isinstance(value, Value) and value.mode in MODE_TYPES):
                        environment[name] = value
            elif op == '->' and shadows is not None and args[0] in environment:
                shadows.setdefault(args[0], environment[args[0]])
            elif op == '<-' and valued and not node.terminated:
                if index != len(nodes) - 1:
                    self.fail(line, 'prototype : le retour <- doit être la dernière instruction')
                tail = self.lookup(args[0], environment, line)
            elif op == 'if_yield' and valued:
                part, tail = self.expression(args[0], environment, line, expected_array)
            elif op == 'match_yield' and valued:
                tail = self.lookup(args[0], environment, line)
            elif op == 'scope':
                part, _ = self.block(args[1], environment)
            elif op == 'if':
                condition, yes, no = args
                part = self.condition(condition, environment, line)
                if 'next' in part:
                    left_env, right_env = environment.copy(), environment.copy()
                    self.refine_handle_branches(condition, left_env, right_env)
                    left, _ = self.block(yes, left_env)
                    right, _ = self.block(no, right_env)
                    self.join_environments(environment, ((left, left_env), (right, right_env)))
                    part = (part - {'next'}) | left | right
            elif op == 'while_check':
                part = self.condition(args[0], environment, line)
                if 'next' in part:
                    self.record_loop_edge('break', environment)
                    part |= {'break'}
            elif op in ('loop', 'while'):
                part, _ = self.loop(node, environment)
            elif op == 'break':
                expected = self.loops[-1]['expected_array'] if self.loops else None
                part, value = self.expression(args[0], environment, line, expected)
                if 'next' in part:
                    part = (part - {'next'}) | {'break'}
                    self.record_loop_edge('break', environment)
                    if self.loops and self.loops[-1]['values'] is not None:
                        if args[0] is None:
                            self.fail(line, 'break sans valeur dans une boucle avec receveur')
                        if isinstance(value, Value):
                            values = self.loops[-1]['values']
                            combined = self.unify_handle_values([*values, value], line)
                            values[:], value = combined[:-1], combined[-1]
                            if values and (value.mode, value.typ) != (values[0].mode, values[0].typ):
                                self.fail(line, 'break : même type et même mode requis sur toutes les sorties')
                            values.append(value)
            elif op == 'continue':
                self.record_loop_edge('continue', environment)
                part = {'continue'}
            elif op == 'return':
                expected = self.declared[1] if self.declared[0] in ('array', 'array_refs') else None
                part, value = self.expression(args[0], environment, line, expected)
                if 'next' in part:
                    if isinstance(value, Value) and value.mode == 'owned' and args[0][0] not in ('move', 'array_transfer', 'new_transfer'):
                        self.fail(line, 'retour d’allocation : <- explicite requis')
                    self.collect(value, line, environment)
                    part = (part - {'next'}) | {'return'}
            elif op in ('call', 'await_statement'):
                part, _ = self.expression(args[0], environment, line)
            elif (op in ('array_store', 'array_deref_store')
                  and reference_array_variable(args[0], environment) is not None):
                part = self.store_reference_array(args[0], args[1], environment, line)
            elif op == 'field_store':
                place, rhs = args
                part, value = self.expression(rhs, environment, line)
                if 'next' in part:
                    carrier = self.lookup(place[1], environment, line)
                    typ = dict(self.analyzer.enums.get(carrier.typ, {}).get('', ())).get(place[2]) if isinstance(carrier, Value) else None
                    capability = reference_type(typ) if typ is not None else None
                    if typ and typ.startswith('A<') and isinstance(value, Value):
                        self.update_owned_field(environment, place[1], carrier, '.' + place[2], value)
                    if capability and isinstance(value, Value) and (value.mode, value.typ) == capability:
                        key = '.' + place[2]
                        changes = {key + '/' + path: frozenset()
                                   for path, _ in nested_reference_fields(carrier.fields, key)}
                        changes.update((key + '/' + path, self.detached_field_targets(value, path))
                                       for path, targets in value.fields if targets)
                        changes[key] = stored_targets(value)
                        self.update_structure(environment, place[1], carrier, changes, line)
            elif (op == 'array_deref_store' and args[0][0] == 'name'
                  and isinstance(environment.get(args[0][1]), Value)
                  and environment[args[0][1]].typ.startswith('A<')):
                target = environment[args[0][1]]
                part, incoming = self.expression(args[1], environment, line)
                if 'next' in part:
                    if target.storage_owner is not None and isinstance(incoming, Value):
                        self.update_handle(environment, target, incoming)
                    else:
                        self.store_handle_slot(target, incoming, environment)
            elif op in ARRAY_STATEMENTS or op == 'print_expr':
                for expr in args:
                    if 'next' not in part:
                        break
                    flow_part, _ = self.expression(expr, environment, line)
                    part = (part - {'next'}) | flow_part
            elif op == 'match':
                if not node.consuming:
                    part, _ = self.borrowed_match(node, environment, valued=False)
                    flow = (flow - {'next'}) | part
                    continue
                part = set()
                continuing = []
                values = []
                subject = self.lookup(args[0], environment, line)
                for arm_type, arm, fields, body in args[1]:
                    branch = environment.copy()
                    names = {name for _, name in fields if name != '_'}
                    bindings = dict.fromkeys(names, SCALAR)
                    if isinstance(subject, Value):
                        declarations = dict(self.analyzer.enums.get(arm_type, {}).get(arm, ()))
                        origins = dict(subject.fields)
                        for field, name in fields:
                            declared = declarations.get(field, '')
                            if name != '_' and (mode := scalar_field_mode(declared)) is not None:
                                bindings[name] = Value(mode, declared)
                            capability = reference_type(declared)
                            key = f'{arm}.{field}'
                            if name != '_' and declared.startswith('A<'):
                                bindings[name] = self.project_owned_value(subject, key, declared[2:-1])
                            if name != '_' and capability:
                                targets = self.moved_field_origins(origins.get(key, ()))
                                bindings[name] = Value(capability[0], capability[1],
                                                       fields=nested_reference_fields(subject.fields, key),
                                                       reference_targets=targets)
                    outcome, value = self.block(body, branch, valued=valued, bindings=bindings,
                                                expected_array=expected_array)
                    if valued and 'next' in outcome:
                        values.append(value)
                    continuing.append((outcome, branch))
                    part |= outcome
                self.join_environments(environment, continuing)
                if values and all(isinstance(value, Value) and value.mode != 'unknown' for value in values):
                    values = self.unify_handle_values(values, line)
                    signatures = {(value.mode.removeprefix('array_') if value.mode in ('array_ref', 'array_mut')
                                   else value.mode, value.typ,
                                   value.container_mode if value.container_borrow else None)
                                  for value in values}
                    if len(signatures) != 1:
                        self.fail(line, 'expression match : même type et même mode requis dans tous les bras continuants')
                    tail = replace(merge_reference_values(values),
                                   payload_reference=any(value.payload_reference for value in values),
                                   handle_items=merge_handle_items(values),
                    handle_payloads=tuple(dict.fromkeys(item for value in values for item in value.handle_payloads)),
                                   input_item_history=merge_input_item_history(values),
                                   input_items_changed=any(value.input_items_changed for value in values),
                                   input_items_written=any(value.input_items_written for value in values))
            flow = (flow - {'next'}) | part
        return flow, tail

    def borrowed_match(self, node, environment, valued, expected_array=None):
        line = node.line
        mutable = node.mutable
        subject_name, arms = node.args
        subject = self.lookup(subject_name, environment, line)
        flow = set()
        values = []
        continuing = []
        for typ, arm, fields, body in arms:
            branch = environment.copy()
            bindings = {}
            declarations = dict(self.analyzer.enums.get(typ, {}).get(arm, ()))
            for field, name in fields:
                if name == '_':
                    continue
                field_type = declarations.get(field, '')
                if (mutable and field_type.startswith('A<') and isinstance(subject, Value)
                        and subject.storage_owner is not None):
                    key = f'{arm}.{field}'
                    child = self.owned_field_at(branch, subject, key)
                    if child is not None:
                        bindings[name] = replace(child, mode='mut', storage_owner=subject.storage_owner,
                                                 owned_path=(*subject.owned_path, key))
                        continue
                if field_type.startswith('A<') and isinstance(subject, Value):
                    child = self.project_owned_value(subject, f'{arm}.{field}', field_type[2:-1])
                    bindings[name] = replace(child, mode='mut' if mutable else 'ref')
                    continue
                capability = reference_type(field_type)
                if not capability:
                    mode = scalar_field_mode(field_type)
                    bindings[name] = Value(mode, field_type) if mode is not None else SCALAR
                    continue
                projections = (tuple(candidate for candidate in subject.candidates
                                     if candidate.kind in ('owned_projection', 'owned_field_input'))
                               if isinstance(subject, Value) and subject.mode in ('ref', 'mut') else ())
                carriers = (borrowed_targets(replace(subject, candidates=subject.candidates.difference(projections)))
                            if isinstance(subject, Value) and subject.mode in ('ref', 'mut') else ())
                origins = frozenset(
                    BorrowTarget('field_parameter' if mutable else 'shared_field_parameter',
                                 origin.parameter, f'{arm}.{field}')
                    if origin.kind == 'parameter' else BorrowTarget('local')
                    for origin in carriers
                )
                origins |= frozenset(
                    BorrowTarget('field_parameter' if mutable else 'shared_field_parameter',
                                 candidate.parameter,
                                 (candidate.field_path if candidate.kind == 'owned_projection'
                                  else candidate.source.name) + '/' + f'{arm}.{field}')
                    for candidate in projections)
                mode = 'mut' if mutable and capability[0] == 'mut' else 'ref'
                if field_type.startswith('&') and not field_type.startswith('&mut ') and isinstance(subject, Value):
                    # A shared field points outside its carrier. Its target
                    # survives independently; mutable fields retain a capability.
                    origins = frozenset(replace(target, kind='detached_field_parameter')
                        if target.kind in ('field_parameter', 'shared_field_parameter') else target
                        for target in dict(subject.fields).get(f'{arm}.{field}', ()))
                    if not origins:
                        for candidate in subject.candidates:
                            if candidate.kind == 'owned_projection':
                                path = candidate.field_path + '/' + f'{arm}.{field}'
                            elif candidate.kind == 'owned_field_input':
                                path = candidate.source.name + '/' + f'{arm}.{field}'
                            else:
                                continue
                            origins |= frozenset({BorrowTarget('detached_field_parameter', candidate.parameter, path)})
                fields = nested_reference_fields(subject.fields, f'{arm}.{field}') if isinstance(subject, Value) else ()
                bindings[name] = Value(mode, capability[1], fields=fields,
                                       reference_targets=origins or frozenset({BorrowTarget('local')}))
            outcome, value = self.block(body, branch, valued=valued, bindings=bindings,
                                        expected_array=expected_array)
            continuing.append((outcome, branch))
            flow |= outcome
            if valued and 'next' in outcome and isinstance(value, Value) and value.mode != 'unknown':
                values.append(value)
        self.join_environments(environment, continuing)
        if values:
            values = self.unify_handle_values(values, line)
            return flow, replace(merge_reference_values(values),
                                 payload_reference=any(value.payload_reference for value in values),
                                 handle_items=merge_handle_items(values),
                    handle_payloads=tuple(dict.fromkeys(item for value in values for item in value.handle_payloads)),
                                 input_item_history=merge_input_item_history(values),
                                 input_items_changed=any(value.input_items_changed for value in values),
                                 input_items_written=any(value.input_items_written for value in values))
        return flow, Value('mut' if mutable else 'ref', 'Int')

    def mutable_vector_result_targets(self, carrier, field):
        if not isinstance(carrier, Value) or carrier.input_items_changed or not carrier.candidates:
            return frozenset({BorrowTarget('local')})
        return frozenset(
            BorrowTarget('mutable_vector_parameter', candidate.parameter, field)
            if candidate.kind == 'parameter' and self.params[candidate.parameter][1] in ('ref', 'mut')
            else BorrowTarget('local') for candidate in carrier.candidates)

    @staticmethod
    def owned_capture_field_targets(carrier, key):
        if ResultContext.owned_capture_path_absent(carrier, key):
            return frozenset()
        parameters = {candidate.parameter for candidate in carrier.candidates if candidate.kind == 'parameter'}
        return frozenset(
            BorrowTarget('owned_capture_field', target.parameter, key)
            if target.kind == 'field_parameter' and target.parameter in parameters and target.field == key
            else target for target in dict(carrier.fields).get(key, ())) or frozenset({BorrowTarget('local')})

    @staticmethod
    def detached_field_targets(carrier, key):
        if not isinstance(carrier, Value):
            return frozenset({BorrowTarget('local')})
        parameters = {candidate.parameter for candidate in (*carrier.candidates, *carrier.copy_candidates)
                      if candidate.kind == 'parameter'}
        if carrier.owned_path:
            parameters.update(target.parameter for target in carrier.reference_targets
                              if target.kind in ('field_parameter', 'shared_field_parameter',
                                                 'indirect_field_parameter'))
        projected_key = '/'.join((*carrier.owned_path, key))
        inline_key = '.' + carrier.inline_path + key if carrier.inline_path else key
        targets = shared_vector_field_items(carrier, key)
        return frozenset(
            BorrowTarget('detached_field_parameter', target.parameter, target.field)
            if target.parameter in parameters and (
                target.kind == 'field_parameter' and target.field in (key, projected_key, inline_key)
                or carrier.typ in REFERENCE_VECTORS and carrier.handle_items is None
                and target.kind == 'detached_field_parameter' and target.field == '.items')
            else target for target in targets
        ) or frozenset({BorrowTarget('local')})

    def async_structure_result_targets(self, carrier, typ, paths):
        projected = set()
        fields = dict(self.analyzer.enums[typ][''])
        from array_syntax import owned_reference_paths
        borrowed_fields = {field: (access, target) for field, access, target in owned_reference_paths(self.analyzer.enums, typ)}
        for path in paths:
            field = '.'.join(path)
            if borrowed_fields.get('.' + field) == ('ref', 'Int'):
                projected.update(self.detached_field_targets(carrier, '.' + field))
                continue
            kind = ('indirect_field_parameter' if fields.get(field) == '&mut Int'
                    else 'inline_field_parameter')
            projected.update(self.inline_field_targets(carrier, field, kind))
        return frozenset(projected)

    @staticmethod
    def inline_field_targets(carrier, path, kind='inline_field_parameter', carrier_kind='', detached_prefix=''):
        if not isinstance(carrier, Value):
            return frozenset({BorrowTarget('local')})
        targets = set()
        for origin in borrowed_targets(carrier):
            if origin.kind == 'parameter':
                targets.add(BorrowTarget(kind, origin.parameter, path, detached_prefix, carrier_kind))
                continue
            if origin.kind == 'inline_field_parameter' and not carrier_kind:
                targets.add(replace(origin, kind=kind, field=origin.field + '.' + path))
                continue
            if carrier_kind:
                prefix, _, field = path.rpartition('/')
                projected = projected_field_origin(origin, BorrowTarget(carrier_kind, field=prefix,
                                                                        detached_prefix=detached_prefix))
            else:
                field, projected = path, origin
            if projected.kind in ('field_parameter', 'shared_field_parameter', 'detached_field_parameter'):
                targets.add(BorrowTarget(kind, projected.parameter, projected.field + '/' + field,
                                         projected.detached_prefix, projected.kind))
            else:
                targets.add(BorrowTarget('local'))
        return frozenset(targets or {BorrowTarget('local')})

    def has_nondurable_array_target(self, targets):
        return any(target.kind == 'local' or (target.kind in ('inline_field_parameter', 'indirect_field_parameter')
                   and self.params[target.parameter][1] not in ('ref', 'mut')) for target in targets)

    @staticmethod
    def reference_row_result_targets(value, capture_type, capture_mode, paths):
        if value.mode != 'array_refs' or value.typ != capture_type:
            return frozenset()
        from async_lowering import int_reference_layout
        mutable_leaf = int_reference_layout(capture_type, capture_mode)[-1][1] == 'mut'
        def targets(row, path):
            dimensions, typ = 0, row.typ
            while (shape := fixed_array_shape(typ)) is not None:
                typ = shape[0]
                dimensions += 1
            indices = tuple(('int', index) if index is not None else ('name', '') for index in path[:dimensions])
            _, groups = reference_array_projection(row.typ, indices)
            selected = {str(slot) for group in groups for slot in group}
            if row.rows:
                for slot, child in row.rows:
                    if slot in selected:
                        yield from targets(child, path[dimensions:])
            else:
                for slot, candidates in row.fields:
                    if slot in selected:
                        yield from candidates
        return frozenset(
            replace(origin, kind='reserved_stored_array_parameter')
            if mutable_leaf and origin.kind == 'stored_array_parameter' else origin
            for path in paths for origin in targets(value, path))

    def array_update_targets(self, target, actual):
        if target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
            return reference_tree_targets(actual, target.field)
        if target.kind in ('inline_field_parameter', 'indirect_field_parameter'):
            return self.inline_field_targets(actual, target.field, target.kind, target.carrier_kind, target.detached_prefix)
        if target.kind == 'detached_field_parameter':
            return self.detached_field_targets(actual, target.field)
        return borrowed_targets(actual)

    def instantiate_deferred_fields(self, fields, actuals):
        """Snapshot targets at creation; do not publish stores before completion."""
        updates = set()
        for index, changes in fields:
            mapped = tuple((field, frozenset(origin for target in targets for origin in (
                dict(actuals[target.parameter].fields).get(target.field, ())
                if target.kind == 'field_parameter'
                else self.array_update_targets(target, actuals[target.parameter]))))
                for field, targets in changes)
            updates.add((actuals[index], mapped))
        return frozenset(updates)

    def collect_deferred_vectors(self, updates, output, line):
        for carrier, items in updates:
            if any(item.kind not in ('parameter', 'vector_element') and not (
                    item.kind == 'fresh' and item.source.kind == 'source_parameter') for item in items):
                self.fail(line, 'retour de tâche : pool des éléments non durable')
            for origin in carrier.structure_origins:
                if not isinstance(origin, tuple) or origin[0] != 'vector_parameter' or self.params[origin[1]][1] != 'mut':
                    self.fail(line, 'retour de tâche : vecteur modifié non durable')
                index = origin[1]
                output[index] = output.get(index, frozenset()) | items

    def instantiate_deferred_vectors(self, writes, actuals):
        return frozenset((actuals[index], self.resolve_vector_slot(items, actuals))
                         for index, items in writes)

    @staticmethod
    def vector_update_sources(writes):
        return tuple((index, frozenset(item for slot in (*slots, *(slot for _, slot in replacements)) for item in slot))
                     for index, slots, _, replacements, _ in writes)

    def instantiate_deferred_owned(self, writes, actuals, environment):
        updates = set()
        for index, path, child in writes:
            carrier = actuals[index]
            previous = self.owned_field_at(environment, carrier, path)
            updates.add((carrier, path, self.resolve_owned_child(child, actuals, previous, map_fields=True)))
        return frozenset(updates)

    def collect_deferred_owned(self, updates, output, line):
        for carrier, path, child in updates:
            pending = [child]
            while pending:
                current = pending.pop()
                if not current.candidates or any(not (
                        candidate.kind in ('parameter', 'owned_projection', 'owned_field_input')
                        or candidate.kind == 'fresh' and candidate.source.kind == 'source_parameter')
                        for candidate in current.candidates):
                    self.fail(line, 'retour de tâche : remplacement de champ depuis une source non durable')
                pending.extend(value for _, value in current.owned_fields)
            for target in borrowed_targets(carrier):
                if target.kind != 'parameter' or self.params[target.parameter][1] != 'mut':
                    self.fail(line, 'retour de tâche : porteur propriétaire de modification non durable')
                key = target.parameter, path
                output[key] = merge_owned_values((output[key], child)) if key in output else child

    def apply_deferred_owned(self, updates, environment, *, include_initial=False):
        for carrier, path, child in sorted(updates, key=lambda item: item[1], reverse=True):
            previous = self.owned_field_at(environment, carrier, path)
            if include_initial and previous is not None:
                child = merge_owned_values((previous, child))
            name = '\0completed_owned_carrier'
            current = environment.get(carrier.storage_owner, carrier)
            # Preserve a projection into a descendant, if the carrier is one.
            if carrier.owned_path:
                current = carrier
            environment[name] = current
            self.update_owned_field(environment, name, current, path, child)
            environment.pop(name)

    def apply_deferred_vectors(self, updates, environment):
        for carrier, items in updates:
            for name, current in tuple(environment.items()):
                if (isinstance(current, Value) and is_handle_vector(current.typ)
                        and current.structure_origins == carrier.structure_origins):
                    previous = possible_handle_items(current.handle_items)
                    environment[name] = replace(current,
                        handle_items=previous | items if previous is not None else None,
                        input_item_history=None, input_items_written=True)

    def apply_deferred_field_updates(self, task, environment, line):
        # A launched task can fail before its first poll. The old state must
        # remain a possible state. Resolve all captured targets before stores.
        self.apply_deferred_owned(task.deferred_owned_updates, environment, include_initial=True)
        self.apply_deferred_vectors(task.deferred_vector_updates, environment)
        for carrier, fields in task.deferred_field_updates:
            name = '\0completed_task_carrier'
            current = environment.get(carrier.storage_owner, carrier)
            changes = {field: dict(current.fields).get(field, frozenset()) | targets
                       for field, targets in fields}
            environment[name] = carrier
            self.update_structure(environment, name, carrier, changes, line)
            environment.pop(name)

    def apply_structure_updates(self, summary, actuals, args, environment, line):
        """Instantiate a field-effect contract using input snapshots, not callee bodies."""
        updated = {}
        for parameter, fields in summary.structure_fields:
            name = borrowed_array_name(args[parameter])
            projected = name is None and isinstance(actuals[parameter], Value) and (
                actuals[parameter].owned_path or actuals[parameter].structure_choices or actuals[parameter].inline_path)
            if projected:
                name = '\0projected_structure_update'
                environment[name] = actuals[parameter]
            if name not in environment:
                self.fail(line, 'prototype : mise à jour de champ exige un porteur nommé')
            carrier = environment[name]
            changes = {}
            for field, targets in fields:
                changes[field] = frozenset(origin for target in targets
                    for origin in (dict(actuals[target.parameter].fields).get(target.field, ())
                                   if target.kind == 'field_parameter'
                                   else self.array_update_targets(target, actuals[target.parameter])))
            if carrier.typ in REFERENCE_VECTORS:
                slots = dict(summary.reference_appends).get(parameter)
                appended = None if slots is None else tuple(frozenset(
                    origin for target in slot for origin in self.array_update_targets(target, actuals[target.parameter]))
                    for slot in slots)
                items = changes['.items']
                if appended is not None and isinstance(carrier.handle_items, tuple):
                    items = (*carrier.handle_items, *appended)
                update_shared_vector_items(environment, (bindings for _, bindings in self.blocks), carrier,
                                           items, lambda value: value.structure_origins, appended=appended)
            else:
                self.update_structure(environment, name, carrier, changes, line)
                updated[parameter] = environment[name]
            if projected:
                environment.pop(name)
        return updated

    def update_structure(self, environment, name, carrier, changes, line):
        # Shadowing a name cannot retarget a reference created before the block.
        # Resolve the hidden root by construction identity in the shadow scopes.
        if (carrier.mode == 'mut' and carrier.storage_owner and carrier.structure_origins
                and not carrier.inline_path and not carrier.owned_path):
            owner = environment.get(carrier.storage_owner)
            if not carrier.structure_origins & getattr(owner, 'structure_origins', frozenset()):
                carrier = replace(carrier, storage_owner=None)
        if carrier.inline_path and not carrier.structure_choices:
            owner = self.lookup(carrier.storage_owner, environment, line)
            from structure_views import prefix_fields, project_fields
            self.update_structure(environment, carrier.storage_owner, owner,
                                  dict(prefix_fields(changes.items(), carrier.inline_path)), line)
            environment[name] = replace(carrier, fields=project_fields(
                environment[carrier.storage_owner].fields, carrier.inline_path))
            return
        if carrier.structure_choices:
            branches = []
            for choice in carrier.structure_choices:
                branch = environment.copy()
                self.update_structure(branch, name, choice, changes, line)
                branches.append(({'next'}, branch))
            self.join_environments(environment, branches)
            return
        for targets in changes.values():
            self.record_stored_references(targets)
        if carrier.mode == 'mut' and carrier.storage_owner is None:
            indices = {target.parameter for target in carrier.reference_targets
                       if target.kind == 'parameter' and self.params[target.parameter][1] == 'mut'}
            if carrier.structure_origins:
                shadows = (bindings for _, bindings in self.blocks)
                mapped = update_local_structure_locations(environment, carrier.structure_origins, changes,
                                                          lambda value: getattr(value, 'structure_origins', frozenset()), shadows)
            else:
                mapped = bool(indices)
            if indices:
                mapped = mapped and update_structure_parameters(
                    environment, indices, changes, conditional=bool(carrier.structure_origins))
            if not mapped or any(target.kind not in ('parameter', 'local') for target in carrier.reference_targets):
                self.fail(line, 'prototype : mise à jour indirecte de porteurs par contrat')
        fields = dict(carrier.fields) | changes
        environment[name] = replace(carrier, fields=tuple(fields.items()))
        owner = environment.get(carrier.storage_owner)
        if carrier.owned_path and isinstance(owner, Value):
            def update_descendant(value, path):
                if value.owned_alternatives:
                    return merge_owned_values([update_descendant(item, path) for item in value.owned_alternatives])
                if not path:
                    return replace(value, fields=tuple((dict(value.fields) | changes).items()))
                key, *tail = path
                children = dict(value.owned_fields)
                if key not in children:
                    self.fail(line, 'mise à jour du descendant : provenance propriétaire manquante')
                children[key] = update_descendant(children[key], tail)
                prefix = '/'.join(path) + '/'
                flattened = dict(value.fields) | {prefix + field: targets for field, targets in changes.items()}
                return replace(value, fields=tuple(flattened.items()), owned_fields=tuple(children.items()))
            environment[carrier.storage_owner] = update_descendant(owner, carrier.owned_path)
            return
        if isinstance(owner, Value):
            environment[carrier.storage_owner] = replace(owner, fields=tuple(fields.items()))
            original = environment.get(owner.storage_owner)
            if isinstance(original, Value):
                environment[owner.storage_owner] = replace(original, fields=tuple(fields.items()))

    def owned_field_at(self, environment, carrier, field):
        if carrier.inline_path:
            return self.owned_field_at(environment, replace(carrier, inline_path=''),
                                       '.' + carrier.inline_path + field)
        root = environment.get(carrier.storage_owner, carrier)
        path = (*carrier.owned_path, *field.split('/'))
        prefix = '\0structure:'
        if carrier.storage_owner and carrier.storage_owner.startswith(prefix):
            index = int(carrier.storage_owner[len(prefix):])

            def expand(value, remaining, parent_path=''):
                if not remaining:
                    return value
                if value.owned_alternatives:
                    return merge_owned_values([expand(item, remaining, parent_path)
                                               for item in value.owned_alternatives])
                key, *tail = remaining
                fields = dict(value.owned_fields)
                child = fields.get(key)
                if child is None:
                    arm, _, name = key.partition('.')
                    declared = dict(self.analyzer.enums.get(value.typ, {}).get(arm, ())).get(name, '')
                    if not declared.startswith('A<') or not any(
                            item.kind in ('parameter', 'owned_field_input') for item in value.candidates):
                        return value
                    child = Value('owned', declared[2:-1], frozenset({ResultCandidate(
                        'owned_field_input', index, SourceOrigin('allocation_field_parameter', index, parent_path + key))}))
                fields[key] = expand(child, tail, parent_path + key + '/')
                return replace(value, owned_fields=tuple(fields.items()))

            self.structure_inputs[index] = expand(self.structure_inputs[index], path)
            root = environment[carrier.storage_owner] = expand(root, path)
        elif carrier.storage_owner and root.mode == 'owned':
            def expand_owned(value, remaining):
                if not remaining:
                    return value
                if value.owned_alternatives:
                    return merge_owned_values([expand_owned(item, remaining) for item in value.owned_alternatives])
                key, *tail = remaining
                children = dict(value.owned_fields)
                child = children.get(key)
                if child is None:
                    arm, _, member = key.partition('.')
                    declared = dict(self.analyzer.enums.get(value.typ, {}).get(arm, ())).get(member, '')
                    if not declared.startswith('A<'):
                        return value
                    child = replace(self.project_owned_value(value, key, declared[2:-1]),
                                    fields=nested_reference_fields(value.fields, key))
                children[key] = expand_owned(child, tail)
                return replace(value, owned_fields=tuple(children.items()))
            root = environment[carrier.storage_owner] = expand_owned(root, path)
        for key in path:
            root = dict(root.owned_fields).get(key)
            if root is None:
                break
        return root

    def update_owned_field(self, environment, name, carrier, field, value):
        if carrier.inline_path:
            from structure_views import project_fields
            owner = environment[carrier.storage_owner]
            self.update_owned_field(environment, carrier.storage_owner, owner,
                                    '.' + carrier.inline_path + field, value)
            updated = environment[carrier.storage_owner]
            environment[name] = replace(carrier, fields=project_fields(updated.fields, carrier.inline_path),
                owned_fields=project_fields(updated.owned_fields, carrier.inline_path))
            return
        def update(parent, path):
            if parent.owned_alternatives:
                return merge_owned_values([update(alternative, path) for alternative in parent.owned_alternatives])
            key, *tail = path
            fields = dict(parent.owned_fields)
            if tail and key not in fields:
                return parent
            fields[key] = update(fields[key], tail) if tail else value
            # A later read through the carrier must observe the installed
            # descendant, while an earlier detached reference keeps its snapshot.
            prefix = key + '/'
            borrowed = {path: targets for path, targets in parent.fields
                        if not path.startswith(prefix)}
            def descendant_fields(child, path):
                for member, targets in child.fields:
                    yield path + member, targets
                for member, nested in child.owned_fields:
                    yield from descendant_fields(nested, path + member + '/')
            for path, targets in descendant_fields(fields[key], prefix):
                borrowed[path] = borrowed.get(path, frozenset()) | targets
            return replace(parent, fields=tuple(borrowed.items()), owned_fields=tuple(fields.items()))

        self.owned_field_at(environment, carrier, field)
        path = field.split('/')
        owner = environment.get(carrier.storage_owner)
        if isinstance(owner, Value):
            environment[carrier.storage_owner] = update(owner, (*carrier.owned_path, *path))
        if len(path) == 1 or dict(carrier.owned_fields).get(path[0]) is not None:
            environment[name] = update(carrier, path)

    def resolve_owned_child(self, child, actuals, previous=None, *, map_fields=False):
        alternatives = [actuals[item.parameter] for item in sorted(child.candidates) if item.kind == 'parameter']
        alternatives.extend(self.project_owned_value(actuals[item.parameter], item.field_path, child.typ)
                            for item in sorted(child.candidates) if item.kind == 'owned_projection')
        for item in child.candidates:
            if item.kind == 'vector_element':
                vector = actuals[item.parameter]
                candidates = vector_result_candidates(vector, item.item_index,
                    last=item.item_index == VECTOR_LAST_ITEM, excluded=item.excluded_items, tail_offset=item.tail_offset)
                alternatives.append(restore_handle_payload(extracted_handle(candidates, child.typ), vector))
            elif item.kind == 'exchange_parameter':
                carrier = actuals[item.parameter]
                candidates = carrier.exchange_payloads[item.item_index]
                alternatives.append(restore_handle_payload(Value('owned', child.typ, candidates), carrier))
        if previous is not None and any(item.kind == 'owned_field_input' for item in child.candidates):
            alternatives.append(previous)
        fresh = set()
        for item in child.candidates:
            if item.kind != 'fresh':
                continue
            if item.source.kind == 'local_value':
                fresh.add(item)
                continue
            actual = actuals[item.source.index]
            if isinstance(actual, SourceOrigin):
                fresh.add(ResultCandidate('fresh', source=actual))
            elif item.source.kind == 'allocation_field_parameter':
                fresh.update(ResultCandidate('fresh', source=source)
                             for source in self.owned_capture_storage(actual, item.source.name))
            elif item.source.kind == 'task_result_field_parameter':
                fresh.update(ResultCandidate('fresh', source=source)
                             for source in dict(actual.task_result_fields).get(item.source.name, ()))
        if fresh:
            fields = child.fields
            if map_fields:
                fields = tuple((field, frozenset(origin for target in targets
                    for origin in self.array_update_targets(target, actuals[target.parameter])))
                    for field, targets in fields)
            alternatives.append(replace(child, candidates=frozenset(fresh), fields=fields, owned_fields=tuple(
                (field, self.resolve_owned_child(nested, actuals, map_fields=map_fields)) for field, nested in child.owned_fields)))
        return merge_owned_values(alternatives) if alternatives else UNKNOWN

    @staticmethod
    def project_owned_value(subject, path, typ):
        projected = subject
        for key in path.split('/'):
            projected = dict(projected.owned_fields).get(key)
            if projected is None:
                break
        if projected is not None:
            return projected
        candidates = frozenset(
            ResultCandidate('owned_projection', item.parameter,
                            field_path=f'{item.field_path}/{path}' if item.field_path else path)
            for item in subject.candidates if item.kind in ('parameter', 'owned_projection'))
        return Value('owned', typ, candidates)

    def moved_field_origins(self, origins):
        return frozenset(
            BorrowTarget('moved_field_parameter', target.parameter, target.field)
            if target.kind == 'field_parameter' and self.params[target.parameter][1] == 'owned'
            else target for target in origins
        )
