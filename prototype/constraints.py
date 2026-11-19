"""Infer ordered source equality/disjointness obligations independently of calls."""

from owned_join_types import (
    OWNED_JOIN_TYPES, owned_join_mode, owned_inner_mode,
)
from option_join_types import (
    OPTION_JOIN_TYPES, option_join_mode, option_inner_signature,
)
from exchange_join_types import (
    EXCHANGE_JOIN_TYPES, exchange_join_mode, exchange_payload_type, exchange_inner_signature, exchange_is_try_push,
)
from capture_paths import result_capture_selector, capture_index, capture_slots
from integer_syntax import exact_integer_conversion
from numeric_core import FORMATS, MODE_TYPES, EXTRA_MODES, CONVERSION_PAYLOADS, NUMERIC_JOIN_FIELDS, conversion_mode, conversion_type, numeric_type
from structure_views import scalar_field_mode
from utf8_syntax import ERROR_VALUE_TYPES, RESULT_ERROR_MODES
from utf8_syntax import ASYNC_VALUE_RESULT_FAMILIES
from utf8_syntax import PLAIN_JOIN_TYPES, PLAIN_RETURN_JOINS, PLAIN_JOIN_INNER_MODES
from utf8_syntax import ASYNC_CAPTURE_VIEW_MODES, VECTOR_SLICE_ELEMENTS, VECTOR_SPLIT_TYPES, SHARED_VECTOR_SLICE_MODES, VECTOR_SLICE_MODES, VECTOR_MUT_SLICE_MODES, VECTOR_OPTION_MODES, VECTOR_REPLACE_MODES, VECTOR_TRY_PUSH_MODES, UTF8_EXPRESSION_MODES, UTF8_METHODS, UTF8_TEXT_RESULT, UTF8_SLICE_RESULT, UTF8_BORROW_MODES, VALUE_MODES, UTF8_VALUE_RESULT_FAMILIES
from dataclasses import dataclass, field, replace
from effects import allocation_handle_method, allocation_value_borrow, builtin_method_statement, check_builtin_expression_arity, method_arguments, method_candidate

from handle_exchange_types import exchange_type, exchange_element, exchange_optional
from array_syntax import is_payload_vector, vector_payload_element
from array_syntax import HANDLE_VECTORS, INLINE_VECTOR_ELEMENTS, is_handle_vector, handle_vector_element, register_handle_vector
from array_syntax import consumed_result_expression, aggregate_owned_paths, aggregate_reference_paths, nested_reference_fields, replace_shared_vector_item, shared_vector_field_items, update_shared_vector_items, MUT_REF_VECTOR, REFERENCE_VECTORS, merge_exchange_values, merge_exchange_payloads, UNKNOWN_VECTOR_REMOVALS, replace_handle_positions, remaining_handle_items, VECTOR_LAST_ITEM, last_handle_index, merge_handle_items, handle_items_at, handle_items_after_exchange, handle_items_after_removal, possible_handle_items, ARRAY_STATEMENTS, HANDLE_VECTOR, VECTOR_TYPES, VECTOR_ELEMENTS, vector_method, array_operands, reference_array_shape, fixed_array_shape, borrowed_array_name, update_array_aliases, update_structure_parameters, update_local_structure_locations, restore_array_binding, reference_array_path, reference_array_projection, replace_reference_fields, swap_reference_fields, reference_array_variable, project_reference_array, merge_container_positions, reference_type, reference_array_element, reference_tree_fields, reference_tree_slot, reference_tree_targets, merge_reference_values, merge_reference_rows, unflatten_reference_value, reference_value_place, replace_reference_rows, swapped_reference_rows, target_row_templates, rebuild_reference_tree, reference_tree_type


@dataclass(frozen=True, order=True)
class Source:
    kind: str
    index: int
    name: str = ''
    element: str | None = field(default=None, compare=False)

    def describe(self, params):
        result = {'kind': self.kind, 'parameter': params[self.index][0]}
        if self.kind in ('allocation_field_parameter', 'task_result_field_parameter'):
            result['field'] = self.name
        return result


@dataclass(frozen=True)
class Constraint:
    relation: str
    left: Source
    right: Source
    reason: str = field(default='reset', compare=False)

    def describe(self, params):
        return {'relation': self.relation, 'left': self.left.describe(params),
                'right': self.right.describe(params)}


@dataclass(frozen=True)
class FunctionConstraints:
    requirements: frozenset[Constraint]
    reservation_requirements: frozenset[Constraint] = frozenset()
    copy_writes: frozenset[Source] = frozenset()

    @property
    def all_requirements(self):
        return self.requirements | self.reservation_requirements

    def describe(self, params):
        return [c.describe(params) for c in sorted(self.all_requirements,
                key=lambda c: (c.relation, c.left, c.right))]


@dataclass(frozen=True)
class Asset:
    token: tuple
    source: Source


@dataclass(frozen=True)
class Value:
    mode: str
    typ: str
    assets: frozenset[Asset] = frozenset()
    fields: tuple = ()
    reservations: frozenset[Asset] = frozenset()
    container_origins: frozenset = frozenset()
    container_positions: tuple = ()
    container_borrow: bool = False
    container_mode: str = 'ref'
    rows: tuple = ()
    variants: frozenset[str] = frozenset()
    storage_owner: str | None = None
    projection_assets: frozenset[Asset] = frozenset()
    handle_items: tuple[frozenset[Asset], ...] | frozenset[Asset] | None = None
    handle_payloads: tuple = ()
    handle_exchange: tuple | None = None
    exchange_payloads: tuple = ()
    handle_slot: tuple[frozenset[Asset], int | None] | None = None
    task_result_assets: frozenset[Asset] = frozenset()
    task_result_fields: tuple = ()
    task_reference_assets: frozenset[Asset] = frozenset()
    execution_tokens: frozenset[tuple] = frozenset()
    absent_owned_payload: bool = False
    owned_path: tuple = ()
    structure_choices: tuple = ()
    inline_path: str = ''
    # The carrier identity and the graph returned by each arm are independent.
    exchange_values: tuple = ()

    def __post_init__(self):
        if self.mode == 'buffered_handle_exchange' and (self.exchange_values or self.handle_payloads):
            fields = {}
            for arm, assets in zip(('ok', 'err'), self.exchange_payloads):
                active = ((self.exchange_values[('ok', 'err').index(arm)],) if self.exchange_values else
                          tuple(item for item in self.handle_payloads if item.assets & assets))
                for item in active:
                    if item.assets:
                        for name, targets in item.fields:
                            key = arm + '/' + name
                            fields[key] = fields.get(key, frozenset()) | targets
            object.__setattr__(self, 'fields', tuple(sorted(fields.items())))
            return
        if not is_payload_vector(self.typ):
            return
        items = possible_handle_items(self.handle_items)
        fields = {}
        for item in self.handle_payloads:
            if items is not None and not item.assets & items:
                continue
            for name, assets in item.fields:
                path = '[]/' + name
                fields[path] = fields.get(path, frozenset()) | assets
        object.__setattr__(self, 'fields', tuple(sorted(fields.items())))

    @property
    def all_assets(self):
        items = possible_handle_items(self.handle_items) if is_payload_vector(self.typ) else self.assets
        retained = frozenset(asset for item in self.handle_payloads
                             if items is None or item.assets & items for asset in item.all_assets)
        return self.assets | self.reservations | self.task_result_assets | self.task_reference_assets | retained | frozenset(
            a for _, assets in (*self.fields, *self.task_result_fields) for a in assets)


def restore_handle_payload(value, carrier):
    if not isinstance(carrier, Value):
        return value
    payloads = tuple(item for item in carrier.handle_payloads if item.assets & value.assets)
    if not payloads:
        return value
    merged = join_values(payloads)
    return replace(merged, mode=value.mode, typ=value.typ, assets=value.assets)


def merge_fields(values, attribute='fields'):
    fields = {}
    for value in values:
        for name, assets in getattr(value, attribute):
            fields[name] = fields.get(name, frozenset()) | assets
    return tuple(sorted(fields.items()))


SCALAR = Value('scalar', 'Int')
VOID = Value('void', 'Void')
UNKNOWN = Value('unknown', '?')


@dataclass
class State:
    environment: dict
    history: dict
    break_values: frozenset[Value] = frozenset()
    shadows: tuple[dict, ...] = ()
    inserted_sources: frozenset[Source] = frozenset()
    vector_sources: dict[Asset, frozenset[Source]] = field(default_factory=dict)
    pending_executions: dict[tuple, frozenset[Asset]] = field(default_factory=dict)

    def clone(self):
        return State(self.environment.copy(), self.history.copy(), self.break_values,
                     tuple(scope.copy() for scope in self.shadows), self.inserted_sources,
                     self.vector_sources.copy(), self.pending_executions.copy())

    def shadow(self, name):
        if self.shadows and name in self.environment:
            self.shadows[-1].setdefault(name, self.environment[name])


def join_values(values):
    from array_syntax import merge_structure_choices
    values = tuple(values)
    first = values[0]
    if all(isinstance(value, Value) for value in values):
        return Value(first.mode, first.typ, frozenset(a for value in values for a in value.assets),
                     merge_fields(values), frozenset(a for value in values for a in value.reservations),
                     frozenset(o for value in values for o in value.container_origins), merge_container_positions(values), any(value.container_borrow for value in values), first.container_mode, merge_reference_rows(values),
                     frozenset(arm for value in values for arm in value.variants)
                     if all(value.variants for value in values) else frozenset(),
                     first.storage_owner if all(value.storage_owner == first.storage_owner for value in values) else None,
                     inline_path=first.inline_path if all(value.inline_path == first.inline_path for value in values) else '',
                     handle_items=merge_handle_items(values),
                    handle_payloads=tuple(dict.fromkeys(item for value in values for item in value.handle_payloads)),
                     exchange_payloads=merge_exchange_payloads(values),
                     exchange_values=merge_exchange_values(values),
                     handle_exchange=first.handle_exchange if all(value.handle_exchange == first.handle_exchange for value in values) else None,
                     handle_slot=first.handle_slot if all(value.handle_slot == first.handle_slot for value in values) else None,
                     task_result_assets=frozenset(a for value in values for a in value.task_result_assets),
                     task_result_fields=merge_fields(values, 'task_result_fields'),
                     task_reference_assets=frozenset(a for value in values for a in value.task_reference_assets),
                     execution_tokens=frozenset(token for value in values for token in value.execution_tokens),
                     owned_path=first.owned_path if all(value.owned_path == first.owned_path for value in values) else (),
                     structure_choices=merge_structure_choices(values),
                     absent_owned_payload=all(value.absent_owned_payload for value in values))
    return replace(first, variants=frozenset()) if isinstance(first, Value) else first


def reachable_field(target, actual):
    return (target.kind not in ('field_parameter', 'shared_field_parameter', 'moved_field_parameter',
                               'reserved_field_parameter')
            or not isinstance(actual, Value) or not actual.variants
            or target.field.split('.', 1)[0] in actual.variants)


def array_contract_assets(target, actual):
    if target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
        return reference_tree_targets(actual, target.field)
    if target.kind == 'detached_field_parameter':
        return shared_vector_field_items(actual, target.field)
    if target.kind == 'indirect_field_parameter':
        return actual.assets | actual.reservations | dict(actual.fields).get('.' + target.field, frozenset())
    return actual.all_assets


def join_states(states):
    states = list(states)
    result = states[0].clone()
    for name in result.environment:
        result.environment[name] = join_values([state.environment.get(name) for state in states])
    for index, scope in enumerate(result.shadows):
        names = set().union(*(state.shadows[index] for state in states))
        for name in names:
            scope[name] = join_values([state.shadows[index].get(name, state.environment.get(name))
                                       for state in states])
    for state in states[1:]:
        for token, assets in state.pending_executions.items():
            result.pending_executions[token] = result.pending_executions.get(token, frozenset()) | assets
        result.break_values |= state.break_values
        result.inserted_sources |= state.inserted_sources
        for asset, sources in state.vector_sources.items():
            result.vector_sources[asset] = result.vector_sources.get(asset, frozenset()) | sources
        for asset, resets in state.history.items():
            result.history[asset] = result.history.get(asset, frozenset()) | resets
    return result


def merge_paths(*flows):
    groups = {}
    for flow in flows:
        for outcome, state in flow.items():
            groups.setdefault(outcome, []).append(state)
    return {outcome: join_states(states) for outcome, states in groups.items()}


class ConstraintAnalyzer:
    def __init__(self, functions, effects, results, error, enums=None, async_functions=None):
        from handle_types import HandleDefinitions
        self.async_functions = HandleDefinitions(async_functions or {}, structures=enums or {})
        self.functions, self.effects, self.results, self.error = functions, effects, results, error
        self.summaries, self.visiting = {}, set()
        self.enums = enums or {}

    def sync_result_contract(self, name):
        if name not in self.functions or name not in self.results:
            return None
        from results import ResultContract
        node = self.functions[name]
        return ResultContract(tuple(node.args[1]), node.args[2], self.results[name])

    def infer_all(self):
        for name in self.functions:
            self.infer(name)
        return self.summaries

    def infer(self, name):
        if name in self.summaries:
            return self.summaries[name]
        node = self.functions[name]
        if name in self.visiting:
            raise self.error(f'ligne {node.line}: prototype : récursion non prise en charge')
        self.visiting.add(name)
        try:
            context = Context(self, node)
            result = context.infer()
            self.summaries[name] = result
            return result
        finally:
            self.visiting.remove(name)


class Context:
    @staticmethod
    def start_execution(value, token, state):
        state.pending_executions[token] = value.all_assets
        return replace(value, mode='execution', execution_tokens=frozenset({token}))

    def public_handle_value(self, value, public):
        if value.typ == public:
            return value
        from handle_types import canonical_captures, PUBLIC_RESULT_LOCK_SLOT
        from async_lowering import utf8_result_parameters
        definition = self.analyzer.async_functions[value.typ]
        parameters = definition.args[1]
        captures = tuple((f'{"mut" if parameters[capture_index(key)][1] in ("mut", "array_mut", *SHARED_VECTOR_SLICE_MODES) else "ref"}.{key}', targets)
                         for key, targets in value.fields)
        fields = tuple((key.partition('.')[2], frozenset(targets))
                       for key, targets in canonical_captures(captures, parameters))
        if definition.args[2][0] == 'owned':
            locked = frozenset(asset for index in getattr(definition, 'async_returned_lock_parameters', ())
                               for key, assets in capture_slots(value.fields, index)
                               if '/' not in key for asset in assets)
            if locked:
                fields += ((str(PUBLIC_RESULT_LOCK_SLOT), locked),)
        if definition.args[2][0] in ('owned', 'join_owned'):
            from async_result_storage import borrowed_result_fields
            fields += tuple(('4/' + field, frozenset(asset for target in targets
                for _, assets in capture_slots(value.fields, result_capture_selector(target)) for asset in assets))
                for field, targets in borrowed_result_fields(definition))
        if definition.args[2][0] in ('ref', 'mut'):
            fields += (('4', value.task_reference_assets),)
        if definition.args[2][0] in ASYNC_CAPTURE_VIEW_MODES:
            indexes = utf8_result_parameters(definition, self.analyzer.async_functions,
                                            sync_result_contract=self.analyzer.sync_result_contract)
            returned = frozenset(asset for key, assets in value.fields if capture_index(key) in indexes for asset in assets)
            fields += (('4', returned),)
        return replace(value, typ=public, fields=fields)

    def reference_projection_assets(self, actual, path):
        if not isinstance(actual, Value):
            return frozenset()
        field = '.'.join(map(str, path))
        variants = self.analyzer.enums.get(actual.typ, {})
        if path and '' not in variants and path[0] in variants:
            declared = dict(variants[path[0]]).get('.'.join(path[1:]))
            if declared and declared.startswith('&'):
                targets = dict(actual.fields).get(field, frozenset())
                return targets | (actual.assets | actual.reservations if declared.startswith('&mut ') else frozenset())
        declared = dict(self.analyzer.enums.get(actual.typ, {}).get('', ())).get(field)
        if declared and declared.startswith('&'):
            targets = dict(actual.fields).get('.' + field, frozenset())
            return targets | (actual.assets | actual.reservations if declared.startswith('&mut ') else frozenset())
        if reference_array_shape(actual.typ):
            def select(row, typ, coordinates, offset=0):
                if not coordinates:
                    return row.all_assets
                element, length = fixed_array_shape(typ)
                nested = reference_array_shape(element)
                stride = nested[1] if nested else 1
                selected = range(length) if coordinates[0] is None else (coordinates[0],)
                targets = set()
                for index in selected:
                    slot = offset + index * stride
                    fields = dict(row.fields)
                    if len(coordinates) == 1:
                        targets.update(fields.get(str(slot), ()))
                    elif (capability := reference_type(element)) is not None:
                        child = dict(row.rows).get(str(slot))
                        if child is not None:
                            targets.update(select(child, capability[1], coordinates[1:]))
                        if capability[0] == 'mut':
                            targets.update(fields.get(str(slot), ()))
                    else:
                        targets.update(select(row, element, coordinates[1:], slot))
                return frozenset(targets)
            return select(actual, actual.typ, path) | actual.reservations
        return actual.assets | actual.reservations

    def async_reference_assets(self, definition, actuals, line):
        if definition.args[2][0] not in ('ref', 'mut'):
            return frozenset()
        from async_lowering import borrowed_result_paths
        paths = borrowed_result_paths(definition, self.analyzer.async_functions, self.fail, {},
                                      sync_result_contract=self.analyzer.sync_result_contract)
        assets = set()
        for index, path in paths:
            assets.update(self.reference_projection_assets(actuals[index], path))
        return frozenset(assets)

    def unify_handle_values(self, values):
        from handle_types import common_public_handle
        if values and all(isinstance(value, Value) and value.mode == 'execution' for value in values):
            from handle_types import is_public_handle
            result = self.node.args[2]
            expected = result[1] if result[0] == 'execution' and is_public_handle(result[1]) else None
            public = common_public_handle((value.typ for value in values), self.analyzer.async_functions, expected=expected)
            if public is not None:
                return [self.public_handle_value(value, public) for value in values]
        return values

    def __init__(self, analyzer, node):
        self.analyzer, self.node = analyzer, node
        self.params = node.args[1]
        self.requirements = set()
        self.copy_writes = set()
        self.pending_sources = []
        self.valued_loops = []

    def fail(self, line, message):
        raise self.analyzer.error(f'ligne {line}: {message}')

    def parameter_array(self, index, typ, history, prefix=''):
        mode, count = reference_array_shape(typ)
        fields = []
        for slot in range(count):
            path = prefix + str(slot)
            asset = Asset(('stored_array', index, path), Source('allocation_field_parameter', index, path))
            history[asset] = frozenset()
            fields.append((str(slot), frozenset({asset})))
        pointee = reference_array_element(typ)[1]
        rows = tuple((str(slot), replace(self.parameter_array(index, pointee, history, prefix + str(slot) + '/'),
                                        container_borrow=True, container_mode=mode))
                     for slot in range(count)) if reference_array_shape(pointee) else ()
        return Value('array_refs', typ, fields=tuple(fields), rows=rows,
                     container_origins=frozenset({('parameter', index, prefix)}))

    def infer(self):
        environment, history = {}, {}
        contained_sources = set()
        for index, (name, mode, typ) in enumerate(self.params):
            if typ == 'Allocator' or typ.startswith('Pool<'):
                environment[name] = Source('source_parameter', index,
                                           element=typ[5:-1] if typ.startswith('Pool<') else None)
            elif mode in ('array_refs', 'array_refs_owned') or (mode in ('array_ref', 'array_mut') and reference_array_shape(typ)):
                environment[name] = self.parameter_array(index, typ, history)
            elif mode in UTF8_BORROW_MODES:
                asset = Asset(('parameter', index), Source('allocation_parameter', index))
                history[asset] = frozenset()
                environment[name] = Value(mode, typ, frozenset({asset}))
            elif mode in ('task', 'execution'):
                owned_capture = any(capture in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) or capture_type.startswith('Pool<')
                                    for _, capture, capture_type in
                                    self.analyzer.async_functions[typ].args[1])
                assets = frozenset()
                if owned_capture:
                    asset = Asset(('task_parameter', index), Source('task_parameter', index))
                    history[asset] = frozenset()
                    assets = frozenset({asset})
                from async_lowering import owned_result_parameters, utf8_result_parameters
                result_assets = frozenset()
                if self.analyzer.async_functions[typ].args[2][0] in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
                    asset = Asset(('task_result_parameter', index), Source('task_result_parameter', index))
                    history[asset] = frozenset()
                    result_assets = frozenset({asset})
                captures = []
                returned = utf8_result_parameters(self.analyzer.async_functions[typ], self.analyzer.async_functions,
                                                  sync_result_contract=self.analyzer.sync_result_contract)
                borrowed = getattr(self.analyzer.async_functions[typ], 'public_result_borrows', ())
                for position, (_, capture, capture_type) in enumerate(self.analyzer.async_functions[typ].args[1]):
                    from array_syntax import owned_reference_paths
                    owned_borrows = [path for path, _, _ in owned_reference_paths(self.analyzer.enums, capture_type)
                                    ] if capture in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) else []
                    if capture in ('ref', 'mut', 'array_ref', 'array_mut', *ASYNC_CAPTURE_VIEW_MODES) or position in returned or owned_borrows:
                        kind = 'task_borrow_parameter' if capture in ('ref', 'mut', 'array_ref', 'array_mut') or owned_borrows else 'task_utf8_parameter'
                        for selector in ([f'{position}/{path}' for path in owned_borrows] or [str(position)]):
                            asset = Asset((kind, index, selector), Source(kind, index, selector))
                            history[asset] = frozenset()
                            captures.append((selector, frozenset({asset})))
                reservations = frozenset(asset for _, targets in captures for asset in targets)
                reference_assets = frozenset(asset for position, targets in captures
                                             if capture_index(position) in borrowed for asset in targets)
                definition = self.analyzer.async_functions[typ]
                if definition.args[2][0] in ('ref', 'mut') and not borrowed:
                    asset = Asset(('task_reference_result_parameter', index),
                                  Source('task_reference_result_parameter', index))
                    history[asset] = frozenset()
                    reference_assets = frozenset({asset})
                result_fields = []
                result_type = definition.args[2][1]
                owned_paths = tuple(aggregate_owned_paths(self.analyzer.enums, result_type))
                if is_handle_vector(result_type):
                    element = handle_vector_element(result_type)
                    owned_paths = (('[]', element), *(( '[]/' + path, child_type)
                        for path, child_type in aggregate_owned_paths(self.analyzer.enums, element)))
                for path, child_type in owned_paths:
                    asset = Asset(('task_result_field_parameter', index, path),
                                  Source('task_result_field_parameter', index, path, child_type))
                    history[asset] = frozenset()
                    result_fields.append((path, frozenset({asset})))
                environment[name] = Value(mode, typ, assets, tuple(captures), reservations=reservations,
                                          task_result_assets=result_assets, task_reference_assets=reference_assets,
                                          task_result_fields=tuple(result_fields))
            elif mode in ASYNC_CAPTURE_VIEW_MODES:
                asset = Asset(('utf8_parameter', index), Source('allocation_parameter', index))
                history[asset] = frozenset()
                environment[name] = Value(mode, typ, frozenset({asset}))
            elif mode in ('scalar', *VALUE_MODES, 'array', 'array_ref', 'array_mut', 'array_refs', 'array_refs_owned'):
                environment[name] = SCALAR if mode == 'scalar' else Value(mode, typ)
            else:
                asset = Asset(('parameter', index), Source('allocation_parameter', index))
                history[asset] = frozenset()
                fields = []
                content = typ[2:-1] if mode == 'mut' and typ.startswith('A<') else typ
                from array_syntax import owned_reference_paths
                reference_paths = dict(aggregate_reference_paths(self.analyzer.enums, content))
                reference_paths.update((path, pointee) for path, _, pointee in owned_reference_paths(self.analyzer.enums, content))
                for key in reference_paths:
                    target = Asset(('field', index, key), Source('allocation_field_parameter', index, key))
                    history[target] = frozenset()
                    fields.append((key, frozenset({target})))
                for key, element in aggregate_owned_paths(self.analyzer.enums, content):
                    source = Source('allocation_field_parameter', index, key, element)
                    target = Asset(('field', index, key), source)
                    history[target] = frozenset()
                    fields.append((key, frozenset({target})))
                    contained_sources.add(source)
                tracks_reference_items = typ in REFERENCE_VECTORS and mode in ('owned', 'mut')
                if typ in REFERENCE_VECTORS:
                    target = Asset(('field', index, '.items'), Source('allocation_field_parameter', index, '.items'))
                    history[target] = frozenset()
                    fields.append(('.items', frozenset({target})))
                reservation = Asset(('reservation', index), Source('reservation_parameter', index))
                history[reservation] = frozenset()
                environment[name] = Value(mode, typ, frozenset({asset}), tuple(fields),
                                          frozenset({reservation}),
                                          handle_items=fields[0][1] if tracks_reference_items else None)
                if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
                    payloads = (frozenset() if exchange_optional(typ) or exchange_is_try_push(mode) else frozenset({asset}),
                                frozenset({asset}))
                    environment[name] = replace(environment[name], exchange_payloads=payloads)
                    if mode == 'buffered_handle_exchange':
                        element = exchange_element(typ)
                        paths = dict(aggregate_reference_paths(self.analyzer.enums, element))
                        paths.update((path, pointee) for path, _, pointee in owned_reference_paths(self.analyzer.enums, element))
                        paths.update(aggregate_owned_paths(self.analyzer.enums, element))
                        prototypes = []
                        for arm, assets in zip(('ok', 'err'), payloads):
                            if not assets:
                                continue
                            payload_fields = []
                            for path in paths:
                                target = Asset(('exchange_field', index, arm, path),
                                    Source('allocation_field_parameter', index, arm + '/' + path))
                                history[target] = frozenset()
                                payload_fields.append((path, frozenset({target})))
                            prototypes.append(Value('owned', element, assets, tuple(payload_fields)))
                        environment[name] = replace(environment[name], handle_payloads=tuple(prototypes))
                if mode == 'mut' and typ.startswith('A<'):
                    key = f'\0handle:{index}'
                    environment[name] = replace(environment[name], storage_owner=key)
                    environment[key] = Value('owned', content, frozenset({asset}), tuple(fields))
                if is_payload_vector(content) and mode in ('owned', 'ref', 'mut', *OWNED_JOIN_TYPES):
                    source = Source('vector_element_parameter', index, element=vector_payload_element(content))
                    item = Asset(('vector_element', index), source)
                    history[item] = frozenset()
                    contained_sources.add(source)
                    element = vector_payload_element(content)
                    paths = dict(aggregate_reference_paths(self.analyzer.enums, element))
                    paths.update((path, pointee) for path, _, pointee in owned_reference_paths(self.analyzer.enums, element))
                    paths.update(aggregate_owned_paths(self.analyzer.enums, element))
                    payload_fields = []
                    for path, pointee in paths.items():
                        source = Source('allocation_field_parameter', index, '[]/' + path, pointee)
                        child = Asset(('vector_field', index, path), source)
                        history[child] = frozenset()
                        payload_fields.append((path, frozenset({child})))
                    payload = Value('owned', element, frozenset({item}), tuple(payload_fields))
                    environment[name] = replace(environment[name], handle_items=frozenset({item}), handle_payloads=(payload,))
                    if typ != content:
                        environment[key] = replace(environment[key], handle_items=frozenset({item}), handle_payloads=(payload,))
                if mode == 'mut' and '' in self.analyzer.enums.get(typ, {}):
                    key = f'\0structure:{index}'
                    environment[name] = replace(environment[name], storage_owner=key)
                    environment[key] = environment[name]
        for index, (name, mode, typ) in enumerate(self.params):
            if mode in ('array_ref', 'array_mut') and reference_array_shape(typ):
                environment[name] = replace(environment[name], container_borrow=True, container_mode=mode[6:])
        initial = State(environment, history, inserted_sources=frozenset(contained_sources))
        for name, value in tuple(environment.items()):
            if isinstance(value, Value) and value.mode == 'execution':
                environment[name] = self.start_execution(value, ('parameter', name), initial)
        paths, tail = self.nodes(self.node.args[3], initial,
                                 valued=self.node.args[2][0] == 'owned')
        mode, typ = self.node.args[2]
        if mode == 'owned' and 'next' in paths and (
                hook := getattr(self.analyzer, 'storage_annotation_hook', None)):
            hook(self, tail, f'A<{typ}>' if self.node.handle_result else typ, self.node.line)
        reserved = frozenset(c for c in self.requirements
                             if 'reservation_parameter' in (c.left.kind, c.right.kind))
        return FunctionConstraints(frozenset(self.requirements) - reserved, reserved, frozenset(self.copy_writes))

    def lookup(self, name, state, line):
        if name not in state.environment:
            self.fail(line, f"variable inconnue '{name}'")
        return state.environment[name]

    def source(self, name, state, line):
        result = self.lookup(name, state, line)
        if not isinstance(result, Source):
            self.fail(line, f"'{name}' n'est pas une source de stockage")
        return result

    def known_distinct(self, left, right):
        if left == right:
            return False
        if left.kind == 'local' or right.kind == 'local':
            return True
        if left.kind == right.kind == 'source_parameter':
            # Existing call-mode alias checks enforce this part of the signature.
            return self.params[left.index][1] == 'mut' or self.params[right.index][1] == 'mut'
        return False

    def require(self, relation, left, right, line, reason='reset'):
        if left == right:
            if relation == 'equal':
                return
            self.impossible(reason, line)
        if self.known_distinct(left, right):
            if relation == 'distinct':
                return
            self.impossible(reason, line)
        left, right = sorted((left, right))
        constraint = Constraint(relation, left, right, reason)
        opposite = Constraint('equal' if relation == 'distinct' else 'distinct', left, right)
        if opposite in self.requirements:
            self.fail(line, 'reset interdit : contraintes de sources incompatibles')
        self.requirements.add(constraint)

    def impossible(self, reason, line):
        if reason == 'drop':
            self.fail(line, 'drop exige la source de stockage d’origine : égalité impossible')
        if reason == 'borrow':
            self.fail(line, 'arguments aliasés : source empruntée pendant l’évaluation des arguments')
        self.fail(line, 'reset interdit : une allocation doit encore être utilisée dans cette source')

    def projected_assets(self, value, field, state):
        assets = shared_vector_field_items(value, field)
        if value.typ not in REFERENCE_VECTORS or value.handle_items is not None or not field.startswith('.items:'):
            return assets
        projected = set()
        for asset in assets:
            if asset.source.kind == 'allocation_field_parameter' and asset.source.name == '.items':
                slot = Asset(('vector_slot', asset.token, field), replace(asset.source, name=field))
                state.history[slot] = state.history.get(slot, frozenset()) | state.history.get(asset, frozenset())
                projected.add(slot)
            else:
                projected.add(asset)
        return frozenset(projected)

    def touch(self, value, state, line, *, place=False, before=None):
        if isinstance(value, Value):
            assets = value.all_assets | value.projection_assets if place else value.all_assets
            self.touch_assets(assets, state, line, before=before)

    def touch_assets(self, assets, state, line, *, before=None):
        for asset in assets:
            resets = state.history.get(asset, frozenset())
            if before is not None:
                resets = resets - before.get(asset, frozenset())
            for reset in resets:
                self.require('distinct', asset.source, reset, line)

    def use_source(self, source, write, line):
        for frame in self.pending_sources:
            for held, mode in frame:
                if write or mode == 'mut':
                    self.require('distinct', held, source, line, 'borrow')

    def reset(self, source, state, line):
        self.use_source(source, True, line)
        # A launched task can access its captures even on a path which never
        # reaches a later join. Their protection is not ordinary last-use.
        for assets in state.pending_executions.values():
            for asset in assets:
                self.require('distinct', asset.source, source, line)
        for origin in state.inserted_sources.union(*state.vector_sources.values()):
            self.require('distinct', origin, source, line)
        for asset in state.history:
            if not self.known_distinct(asset.source, source):
                state.history[asset] |= frozenset({source})

    def copy_write(self, source, line):
        self.use_source(source, True, line)
        for index, (_, mode, typ) in enumerate(self.params):
            if mode == 'ref' and (typ == 'Allocator' or typ.startswith('Pool<')):
                self.require('distinct', source, Source('source_parameter', index), line, 'borrow')
        if source.kind != 'local':
            self.copy_writes.add(source)

    def retain_handle_origin(self, value, state, vector=None):
        if isinstance(value, Value):
            sources = frozenset(asset.source for asset in value.assets if asset.source.kind != 'local')
            if isinstance(vector, Value) and vector.mode == 'owned' and len(vector.assets) == 1:
                carrier = next(iter(vector.assets))
                if carrier.token[0] == 'new':
                    state.vector_sources[carrier] = state.vector_sources.get(carrier, frozenset()) | sources
                    return
            state.inserted_sources |= sources

    def born(self, token, source, state):
        asset = Asset(token, source)
        state.history[asset] = frozenset()
        return asset

    def condition(self, condition, state, line):
        paths = {'next': state}
        if condition[0] == 'compare':
            for expr in condition[2:]:
                if 'next' not in paths:
                    break
                following, _ = self.expression(expr, paths.pop('next'), line)
                paths = merge_paths(paths, following)
        return paths

    def block(self, nodes, state, valued=False, bindings=None, expected_array=None):
        environment, previous = state.environment.copy(), set(state.history)
        entry = state.clone()
        entry.shadows += ({},)
        if bindings:
            for name, binding in bindings.items():
                entry.shadow(name)
                entry.environment[name] = binding
        paths, value = self.nodes(nodes, entry, valued, expected_array)
        for outcome, path in paths.items():
            shadowed = path.shadows[-1]
            path.shadows = path.shadows[:-1]
            path.environment = {name: restore_array_binding(shadowed.get(name, path.environment[name]), path.environment)
                                for name in environment}
            keep = previous | (set(value.all_assets) if valued and outcome == 'next' and isinstance(value, Value) else set())
            keep.update(asset for binding in path.environment.values() if isinstance(binding, Value)
                        for asset in binding.all_assets)
            keep.update(asset for result in path.break_values for asset in result.all_assets)
            carriers = [*path.environment.values(), *path.break_values]
            if valued and outcome == 'next':
                carriers.append(value)
            for carrier in carriers:
                if isinstance(carrier, Value):
                    keep.update(possible_handle_items(carrier.handle_items) or ())
            path.history = {asset: resets for asset, resets in path.history.items() if asset in keep}
            path.vector_sources = {asset: sources for asset, sources in path.vector_sources.items() if asset in keep}
        return paths, value

    def remember_handle_payload(self, environment, receiver, item):
        vector = environment.get(receiver)
        if not isinstance(vector, Value) or not is_payload_vector(vector.typ):
            return
        owner = vector.storage_owner or receiver
        for name in (owner, receiver):
            root = environment.get(name)
            if isinstance(root, Value):
                environment[name] = replace(root, handle_payloads=tuple(dict.fromkeys((*root.handle_payloads, item))))

    def publish_handle_exchange(self, state, exchange, *, exact=True):
        receiver, index, incoming, append = exchange
        vector = state.environment.get(receiver)
        if not isinstance(vector, Value) or vector.handle_items is None:
            return
        alias = vector if vector.storage_owner is not None else None
        if alias is not None:
            receiver = alias.storage_owner
            vector = state.environment.get(receiver)
            if not isinstance(vector, Value) or vector.assets != alias.assets:
                self.invalidate_handle_items(state)
                return
        items = handle_items_after_exchange(vector.handle_items, index, incoming, append, weak=not exact)
        if not exact:
            items = possible_handle_items(items)
        state.environment[receiver] = replace(vector, handle_items=items)
        if alias is not None:
            state.environment[exchange[0]] = replace(alias, handle_items=items)

    def extract_vector_item(self, state, receiver, index, line):
        name = receiver[1] if receiver[0] == 'name' else None
        vector = state.environment.get(name)
        alias = vector if isinstance(vector, Value) and vector.storage_owner is not None else None
        if alias is not None:
            name = alias.storage_owner
            vector = state.environment.get(name)
            if not isinstance(vector, Value) or vector.assets != alias.assets:
                self.invalidate_handle_items(state)
                return Value('owned', 'Int')
        items = vector.handle_items if isinstance(vector, Value) else None
        typ = vector_payload_element(vector.typ) if isinstance(vector, Value) else 'Int'
        result = restore_handle_payload(Value('owned', typ, handle_items_at(items, index) or frozenset()), vector)
        self.touch(result, state, line)
        if isinstance(items, tuple) and items:
            items = handle_items_after_removal(items, index)
            state.environment[name] = replace(vector, handle_items=items)
            if alias is not None:
                state.environment[receiver[1]] = replace(alias, handle_items=items)
        return result

    def refine_handle_branches(self, condition, yes, no):
        if condition[0] != 'compare':
            return
        operand = condition[2]
        if operand[0] == 'array_handle_exchange_status':
            exchange = yes.environment[operand[1][1]].handle_exchange
            if exchange is not None:
                self.publish_handle_exchange(yes, exchange)
        elif operand[0] == 'array_handle_len':
            name = operand[1][1]
            vector = no.environment.get(name)
            if isinstance(vector, Value):
                no.environment[name] = replace(vector, handle_items=())

    @staticmethod
    def absent_option_success(condition, state):
        if (condition[0:2] != ('compare', '==') or condition[3] != ('int', 0)
                or condition[2][0] != 'array_handle_option_status'):
            return False
        operand = condition[2][1]
        value = state.environment.get(operand[1]) if operand[0] == 'name' else None
        return isinstance(value, Value) and value.mode == 'handle_option' and value.absent_owned_payload

    @staticmethod
    def invalidate_handle_items(state):
        for environment in (state.environment, *state.shadows):
            for name, value in environment.items():
                if isinstance(value, Value) and is_payload_vector(value.typ) and value.handle_items is not None:
                    environment[name] = replace(value, handle_items=None)

    @staticmethod
    def update_handle(state, target, incoming):
        owner = target.storage_owner
        if owner is None:
            return
        state.environment[owner] = incoming
        for name, alias in state.environment.items():
            if isinstance(alias, Value) and alias.typ == target.typ and alias.storage_owner == owner:
                state.environment[name] = replace(alias, assets=incoming.assets, fields=incoming.fields,
                                                  reservations=incoming.reservations, handle_items=incoming.handle_items)

    def store_handle_slot(self, state, target, incoming):
        if target.handle_slot is None or not incoming.assets:
            self.invalidate_handle_items(state)
            return
        origins, index = target.handle_slot
        if any(isinstance(value, Value) and is_handle_vector(value.typ) and value.assets & origins
               for shadow in state.shadows for value in shadow.values()):
            self.invalidate_handle_items(state)
            return
        roots = [(name, value) for name, value in state.environment.items()
                 if isinstance(value, Value) and is_handle_vector(value.typ) and value.assets & origins]
        if not roots:
            self.invalidate_handle_items(state)
            return
        for name, root in roots:
            exact = len(roots) == len(origins) == 1 and root.assets == origins
            items = handle_items_after_exchange(root.handle_items, index, incoming.assets, weak=not exact)
            state.environment[name] = replace(root, handle_items=items, handle_payloads=tuple(dict.fromkeys((*root.handle_payloads, incoming))))

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
            return (value.all_assets,)
        if not isinstance(value, Value) or value.mode not in (mode, 'array_' + mode) or value.typ != pointee:
            self.fail(line, 'une écriture doit conserver le type de référence de la case')
        return (value.all_assets,)

    def store_reference_array(self, place, rhs, state, line):
        name, indices = reference_array_path(place)
        paths = {'next': state}
        for index in indices:
            following, _ = self.expression(index, paths.pop('next'), line)
            paths = merge_paths(paths, following)
            if 'next' not in paths:
                return paths
        following, incoming = self.expression(rhs, paths.pop('next'), line)
        paths = merge_paths(paths, following)
        if 'next' in paths:
            current = paths['next']
            root = current.environment[name]
            root, typ, positions = reference_value_place(root, indices)
            replacement = self.reference_value_fields(incoming, typ, line)
            _, updated = replace_reference_fields(root.fields, positions, replacement)
            update_array_aliases(current.environment, name, updated, root, replace_reference_rows(root, positions, incoming))
        return paths

    def expression(self, expr, state, line, expected_array=None):
        if expr is None:
            return {'next': state}, VOID
        if expr[0] == 'array_drop_result':
            inner = expr[1]
            nominal = getattr(state.environment.get(inner[1][1]), 'typ', None)
            expr = consumed_result_expression(inner, nominal)
        if expr[0] == 'task_join':
            nominal = getattr(state.environment.get(expr[1]), 'typ', None)
            expr = method_candidate(expr, nominal, self.analyzer.functions) or expr
        op = expr[0]
        shape = fixed_array_shape(expected_array) if expected_array is not None else None
        if expr == ('array_literal',) and shape is not None and shape[1] == 0:
            mode = 'array_refs' if reference_array_shape(expected_array) else 'array'
            return {'next': state}, Value(mode, expected_array)
        if op == 'task_spawn':
            paths, task = self.expression(expr[1], state, line)
            if isinstance(task, Value) and 'next' in paths:
                return paths, self.start_execution(task, ('spawn', id(expr)), paths['next'])
            return paths, UNKNOWN
        if op in ('task_join', 'task_join_value'):
            if op == 'task_join':
                paths, execution = {'next': state}, self.lookup(expr[1], state, line)
            else:
                paths, execution = self.expression(expr[1], state, line)
            if isinstance(execution, Value) and execution.mode == 'execution':
                if 'next' in paths:
                    self.touch_assets(execution.all_assets, paths['next'], line)
                    for token in execution.execution_tokens:
                        paths['next'].pending_executions.pop(token, None)
                definition = self.analyzer.async_functions[execution.typ]
                mode = definition.args[2][0]
                if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
                    inner = definition.args[2][1] if mode == 'buffered_handle_exchange' else EXCHANGE_JOIN_TYPES[mode]
                    fields = dict(execution.task_result_fields)
                    outer = exchange_join_mode(inner)
                    return paths, Value(outer, exchange_payload_type(outer), execution.task_result_assets,
                        exchange_payloads=tuple(fields.get(arm, execution.task_result_assets) for arm in ('ok', 'err')))
                if mode in ('owned', 'join_owned', *OWNED_JOIN_TYPES, 'handle_option', *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
                    if mode in ('owned', *OWNED_JOIN_TYPES):
                        kind = owned_join_mode(mode)
                    else:
                        inner = OPTION_JOIN_TYPES[mode] if mode in OPTION_JOIN_TYPES else (f'Option<{definition.args[2][1]}>' if definition.join_storage_result == 'local' else f'Option<A<{definition.args[2][1]}>>')
                        kind = option_join_mode(inner)
                    effects = getattr(definition, 'field_effect_summary', None)
                    if effects is not None and effects.complete and (
                            effects.may_complete is False or effects.completion_result.absent_owned_payload):
                        return paths, Value(kind, definition.args[2][1], absent_owned_payload=True)
                    from async_result_storage import borrowed_result_fields
                    fields = dict(execution.task_result_fields)
                    for field, targets in borrowed_result_fields(definition):
                        fields[field] = frozenset(asset for target in targets
                            for _, assets in capture_slots(execution.fields, result_capture_selector(target))
                            for asset in assets)
                    typ = definition.args[2][1]
                    if is_handle_vector(typ):
                        items = fields.get('[]', frozenset())
                        payload = Value('owned', handle_vector_element(typ), items,
                            tuple((path[3:], targets) for path, targets in fields.items() if path.startswith('[]/')))
                        return paths, Value(kind, typ, execution.task_result_assets,
                            handle_items=items, handle_payloads=(payload,) if items else ())
                    return paths, Value(kind, typ, execution.task_result_assets, tuple(fields.items()))
                if (plain := PLAIN_RETURN_JOINS.get(definition.args[2])) is not None:
                    return paths, Value(plain, PLAIN_JOIN_TYPES[plain])
                if mode in ASYNC_CAPTURE_VIEW_MODES:
                    from async_lowering import utf8_result_parameters
                    captures = dict(execution.fields)
                    retained = frozenset(asset for position in utf8_result_parameters(definition, self.analyzer.async_functions,
                                                          sync_result_contract=self.analyzer.sync_result_contract)
                                         for asset in captures.get(str(position), ()))
                    return paths, Value('join_' + mode, definition.args[2][1], retained)
                if mode in ('ref', 'mut'):
                    return paths, Value('join_' + mode, definition.args[2][1], execution.task_reference_assets)
                if mode in UTF8_VALUE_RESULT_FAMILIES:
                    return paths, Value('join_' + mode, VALUE_MODES[mode])
            return paths, UNKNOWN
        if op == 'text':
            return {'next': state}, Value('text', 'str')
        candidate = method_candidate(expr)
        if candidate is not None:
            receiver, method, rest = candidate[1:]
            value = self.lookup(receiver[1], state, line)
            borrow = allocation_value_borrow(value.typ, method, self.analyzer.functions) if isinstance(value, Value) else None
            if borrow is not None:
                if receiver[0] != 'name' or rest:
                    self.fail(line, f'{method} exige un receveur nommé et aucun argument')
                return self.expression((borrow, receiver[1]), state, line)
            builtin = UTF8_METHODS.get((value.typ, method)) if isinstance(value, Value) and (value.mode in VALUE_MODES or value.typ == 'String') else None
            if isinstance(value, Value):
                builtin = allocation_handle_method(value.typ, method, self.analyzer.functions) or vector_method(value.typ, method) or builtin
            if builtin is not None:
                operation, arity = builtin
                if receiver[0] != 'name' or len(rest) != arity:
                    self.fail(line, f'{method} exige un &str et aucun argument' if method == 'byte_len' else f'{method} exige un receveur et {arity} argument(s)')
                return self.expression((operation, receiver, *rest), state, line)
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
                return self.expression(('call', name, arguments), state, line)
        if op == 'field':
            carrier = self.lookup(expr[1], state, line)
            self.touch(carrier, state, line)
            if isinstance(carrier, Value):
                declared = dict(self.analyzer.enums.get(carrier.typ, {}).get('', ())).get(expr[2], '')
                if (mode := scalar_field_mode(declared)) is not None:
                    return {'next': state}, Value(mode, declared)
                capability = reference_type(declared)
                if capability and capability[0] == 'ref':
                    key = '.' + expr[2]
                    return {'next': state}, Value('ref', capability[1],
                        dict(carrier.fields).get(key, frozenset()), nested_reference_fields(carrier.fields, key))
            return {'next': state}, SCALAR
        if op == 'arithmetic' or op.startswith(('array_', 'utf8_')):
            paths = {'next': state}
            values = []
            before_index = state.history.copy() if op == 'array_index' else None
            operand_type = None
            if shape is not None:
                if op == 'array_transfer':
                    operand_type = expected_array
                elif op in ('array_literal', 'array_repeat') and fixed_array_shape(shape[0]):
                    operand_type = shape[0]
            for index, operand in enumerate((expr[2:] if op == 'arithmetic' else array_operands(expr))):
                if 'next' not in paths:
                    break
                if index == 0 and op in ('array_index', 'array_replace', 'array_swap', 'array_len') and operand[0] == 'name':
                    value = self.lookup(operand[1], paths['next'], line)
                    if isinstance(value, Value) and value.mode == 'array_refs':
                        values.append(value)
                        continue
                following, value = self.expression(operand, paths.pop('next'), line, operand_type)
                paths = merge_paths(paths, following)
                values.append(value)
            if 'next' not in paths:
                return paths, UNKNOWN
            if (op in ('array_vector_push', 'array_buffered_replace', 'array_buffered_try_push') and len(values) > 1
                    and isinstance(values[0], Value) and values[0].typ in INLINE_VECTOR_ELEMENTS
                    and (hook := getattr(self.analyzer, 'storage_vector_item_hook', None))):
                hook(self, values[-1], line)
            if op == 'array_literal':
                for value in values:
                    if isinstance(value, Value) and value.mode in ('ref', 'mut', 'array_ref', 'array_mut', 'array_refs'):
                        self.touch(value, paths['next'], line)
            if (len(values) > 1 and isinstance(values[0], Value) and values[0].typ in VECTOR_TYPES
                    and (op.startswith('array_vector_') or op in (
                        'array_index', 'array_handle_exchange', 'array_handle_try_push',
                        'array_buffered_replace', 'array_buffered_try_push'))):
                # The operation uses its receiver after all operands have run.
                self.touch(values[0], paths['next'], line)
            if len(values) > 1 and (op.startswith('utf8_string_') or op in ('utf8_slice', 'utf8_try_slice', 'utf8_char_at', 'array_split')
                                    or (op == 'array_index' and isinstance(values[0], Value)
                                        and values[0].typ in ('String', 'str', '[u8]', '[Int]'))):
                self.touch(values[0], paths['next'], line)
            if values and isinstance(values[0], Value) and values[0].typ in REFERENCE_VECTORS:
                vector = values[0]
                current = paths['next']
                items = vector.handle_items
                if items is None:
                    items = dict(vector.fields).get('.items', frozenset())
                if vector.typ == MUT_REF_VECTOR and op in ('array_handle_try_push', 'array_buffered_try_push'):
                    incoming = values[-1].all_assets if isinstance(values[-1], Value) else frozenset()
                    updated = (possible_handle_items(items) or frozenset()) | incoming
                    update_shared_vector_items(current.environment, current.shadows, vector, updated,
                                               lambda value: getattr(value, 'assets', frozenset()))
                    return paths, Value('mutable_ref_try_push', 'Result<(),&mut Int>', assets=incoming,
                                        reservations=vector.assets)
                if vector.typ == MUT_REF_VECTOR and op in ('array_handle_exchange', 'array_buffered_replace'):
                    index = expr[2][1] if expr[2][0] == 'int' else None
                    incoming = values[-1].all_assets if isinstance(values[-1], Value) else frozenset()
                    updated, targets = replace_shared_vector_item(items, index, incoming)
                    update_shared_vector_items(current.environment, current.shadows, vector, updated,
                                               lambda value: getattr(value, 'assets', frozenset()))
                    remaining = possible_handle_items(updated) or frozenset()
                    return paths, Value('mutable_ref_replace', 'Result<&mut Int,&mut Int>', assets=targets,
                                        reservations=vector.assets if not targets.isdisjoint(remaining) else frozenset())
                if op == 'array_vector_try_push':
                    incoming = values[-1].all_assets if isinstance(values[-1], Value) else frozenset()
                    updated = (possible_handle_items(items) or frozenset()) | incoming
                    update_shared_vector_items(current.environment, current.shadows, vector, updated,
                                               lambda value: getattr(value, 'assets', frozenset()))
                    return paths, Value('shared_ref_try_push', 'Result<(),&Int>', assets=incoming)
                if op == 'array_vector_replace':
                    index = expr[2][1] if expr[2][0] == 'int' else None
                    incoming = values[-1].all_assets if isinstance(values[-1], Value) else frozenset()
                    updated, targets = replace_shared_vector_item(items, index, incoming)
                    update_shared_vector_items(current.environment, current.shadows, vector, updated,
                                               lambda value: getattr(value, 'assets', frozenset()))
                    return paths, Value('shared_ref_replace', 'Result<&Int,&Int>', assets=targets)
                if op == 'array_vector_pop':
                    targets = handle_items_at(items, len(items) - 1 if isinstance(items, tuple) else None)
                    updated = items[:-1] if isinstance(items, tuple) else items
                    update_shared_vector_items(current.environment, current.shadows, vector, updated,
                                               lambda value: getattr(value, 'assets', frozenset()))
                    return paths, Value('shared_ref_option', 'Option<&Int>', assets=targets or frozenset())
                index = expr[2][1] if op in ('array_index', 'array_vector_remove') and expr[2][0] == 'int' else None
                if op in ('array_vector_push', 'array_vector_remove'):
                    if op == 'array_vector_push':
                        incoming = values[-1].all_assets if isinstance(values[-1], Value) else frozenset()
                        updated = handle_items_after_exchange(items, None, incoming, append=True)
                    else:
                        updated = handle_items_after_removal(items, index)
                    update_shared_vector_items(current.environment, current.shadows, vector, updated,
                                               lambda value: getattr(value, 'assets', frozenset()))
                if op == 'array_vector_push':
                    return paths, VOID
                if op in ('array_index', 'array_vector_remove'):
                    targets = (self.projected_assets(vector, f'.items:{index}', current)
                               if op == 'array_index' and index is not None else handle_items_at(items, index))
                    carrier = vector.assets if vector.typ == MUT_REF_VECTOR else frozenset()
                    reservations = frozenset()
                    if carrier and op == 'array_vector_remove':
                        remaining = possible_handle_items(updated) or frozenset()
                        if not (targets or frozenset()).isdisjoint(remaining):
                            reservations = carrier
                    return paths, Value(('mutable_vector_slot' if op == 'array_index' else 'mut')
                                       if vector.typ == MUT_REF_VECTOR else 'ref', 'Int', targets or frozenset(),
                                       reservations=reservations,
                                       projection_assets=carrier if op == 'array_index' else frozenset())
            if op in ('array_vector_push', 'array_handle_exchange', 'array_handle_try_push',
                      'array_buffered_replace', 'array_buffered_try_push'):
                current = paths['next']
                item = values[-1]
                receiver = expr[1][1] if expr[1][0] == 'name' else None
                vector = current.environment.get(receiver)
                self.remember_handle_payload(current.environment, receiver, item)
                vector = current.environment.get(receiver)
                incoming = item.assets if isinstance(item, Value) else frozenset()
                append = op not in ('array_handle_exchange', 'array_buffered_replace')
                index = expr[2][1] if not append and expr[2][0] == 'int' else None
                exchange = (receiver, index, incoming, append)
                if isinstance(vector, Value) and is_handle_vector(vector.typ):
                    self.retain_handle_origin(item, current, vector)
                if op == 'array_vector_push':
                    self.publish_handle_exchange(current, exchange)
                    return paths, VOID
                items = vector.handle_items if isinstance(vector, Value) else None
                if op in ('array_buffered_replace', 'array_buffered_try_push'):
                    self.publish_handle_exchange(current, exchange, exact=False)
                    old = frozenset() if append else handle_items_at(items, index) or frozenset()
                    typ = exchange_type(vector_payload_element(vector.typ), append, "local" if vector.typ in INLINE_VECTOR_ELEMENTS else "pool")
                    if vector.typ in INLINE_VECTOR_ELEMENTS and not append:
                        previous = restore_handle_payload(Value('owned', vector_payload_element(vector.typ), old), vector)
                        previous = replace(previous, assets=incoming)
                        return paths, Value('buffered_handle_exchange', typ, incoming,
                            exchange_payloads=(incoming, incoming), exchange_values=(previous, item))
                    return paths, Value('buffered_handle_exchange', typ, incoming | old,
                                       exchange_payloads=(old, incoming), handle_payloads=vector.handle_payloads)
                return paths, Value('handle_exchange', handle_vector_element(vector.typ), incoming,
                                    handle_items=handle_items_at(items, index), handle_exchange=exchange, handle_payloads=vector.handle_payloads)
            if op == 'array_handle_exchange_status':
                return paths, SCALAR
            if op == 'array_handle_exchange_value':
                exchange = values[0]
                if exchange.mode in ('mutable_ref_replace', 'mutable_ref_try_push'):
                    return paths, replace(exchange, mode='mut', typ='Int',
                                          reservations=exchange.reservations
                                          if exchange.mode == 'mutable_ref_replace' and expr[2][1] == 0
                                          else frozenset())
                assets = exchange.assets if expr[2][1] != 0 else exchange.handle_items or frozenset()
                result = restore_handle_payload(Value('owned', exchange.typ, assets), exchange)
                self.touch(result, paths['next'], line)
                return paths, result
            if op == 'array_handle_len':
                return paths, SCALAR
            if op == 'array_buffered_exchange_status':
                return paths, SCALAR
            if op == 'array_buffered_exchange_take':
                arm = expr[2][1]
                if arm in (-1, 1):
                    return paths, VOID
                exchange = values[0]
                if isinstance(exchange, Value) and exchange.mode in ('mutable_ref_replace', 'mutable_ref_try_push'):
                    return paths, replace(exchange, mode='mut', typ='Int',
                                          reservations=exchange.reservations
                                          if exchange.mode == 'mutable_ref_replace' and expr[2][1] == 0
                                          else frozenset())
                if not isinstance(exchange, Value) or len(exchange.exchange_payloads) != 2:
                    self.fail(line, 'match (-> résultat) exige un résultat de replace ou try_push')
                assets = exchange.exchange_payloads[arm == 5]
                result = (exchange.exchange_values[arm == 5] if exchange.exchange_values else
                          restore_handle_payload(Value('owned', exchange_element(exchange.typ), assets), exchange))
                self.touch(result, paths['next'], line)
                return paths, result
            if op == 'array_handle_option_status':
                return paths, SCALAR
            if op == 'array_handle_option_value':
                return paths, replace(values[0], mode='mut', typ='Int') if values[0].mode == 'mutable_ref_option' else replace(values[0], mode='owned')
            if op == 'array_handle_option_empty':
                return paths, VOID
            if op in ('array_pop_handle', 'array_handle_option_pop'):
                current = paths['next']
                vector = values[0]
                if isinstance(vector, Value) and vector.typ == MUT_REF_VECTOR:
                    items = vector.handle_items
                    if items is None:
                        items = dict(vector.fields).get('.items', frozenset())
                    targets = items[-1] if isinstance(items, tuple) and items else possible_handle_items(items)
                    updated = items[:-1] if isinstance(items, tuple) else items
                    update_shared_vector_items(current.environment, current.shadows, vector, updated,
                                               lambda value: getattr(value, 'assets', frozenset()))
                    buffered = op == 'array_handle_option_pop'
                    targets = targets or frozenset()
                    remaining = possible_handle_items(updated) or frozenset()
                    return paths, Value('mutable_ref_option' if buffered else 'mut',
                                        'Option<&mut Int>' if buffered else 'Int', assets=targets,
                                        reservations=vector.assets if not targets.isdisjoint(remaining) else frozenset())
                vector = current.environment.get(expr[1][1])
                items = vector.handle_items if isinstance(vector, Value) else None
                index = len(items) - 1 if isinstance(items, tuple) and items else None
                value = self.extract_vector_item(current, expr[1], index, line)
                if isinstance(vector, Value) and vector.typ in INLINE_VECTOR_ELEMENTS:
                    origin = id(expr[1])
                    source = Source('local', origin, 'data stack implicite', value.typ)
                    value = replace(value, assets=frozenset({self.born(('pop', origin), source, current)}))
                return paths, replace(value, mode='handle_option', absent_owned_payload=not value.assets) if op == 'array_handle_option_pop' else value
            if op == 'array_handle_vequals':
                self.touch(values[0], paths['next'], line)
                return paths, Value('bool', 'bool')
            if op in ('array_handle_ref', 'array_handle_mut'):
                return paths, replace(values[0], mode='mut' if op == 'array_handle_mut' else 'ref',
                                      typ=f'A<{values[0].typ}>', storage_owner=expr[1][1])
            if op == 'array_split' and isinstance(values[0], Value):
                value = values[0]
                mode = VECTOR_MUT_SLICE_MODES.get(value.typ, value.mode)
                if mode in VECTOR_MUT_SLICE_MODES.values():
                    typ = VALUE_MODES[mode]
                    return paths, Value('vector_split', f'(&mut {typ},&mut {typ})', value.all_assets)
            if op == 'array_split_half':
                pair = values[0]
                if not isinstance(pair, Value) or pair.mode != 'vector_split':
                    self.fail(line, 'cette liaison exige un résultat de séparation')
                typ = VECTOR_SPLIT_TYPES[pair.typ]
                mode = VECTOR_MUT_SLICE_MODES['Vector<Int>' if typ == '[Int]' else 'Vector<u8>']
                return paths, replace(pair, mode=mode, typ=typ)
            if op == 'array_vector_len':
                return paths, SCALAR
            if op == 'array_vector_push_new':
                return paths, Value('mut', VECTOR_ELEMENTS[values[0].typ], values[0].all_assets)
            if op == 'array_vector_read_fd':
                return paths, Value('read_result', VALUE_MODES['read_result'])
            if op == 'array_vector_try_extend':
                return paths, Value('capacity_result', VALUE_MODES['capacity_result'])
            if op in ('array_vector_pop', 'array_vector_replace', 'array_vector_try_push') and values and isinstance(values[0], Value) and values[0].typ in VECTOR_ELEMENTS:
                modes = {'array_vector_pop': VECTOR_OPTION_MODES,
                         'array_vector_replace': VECTOR_REPLACE_MODES,
                         'array_vector_try_push': VECTOR_TRY_PUSH_MODES}[op]
                mode = modes[VECTOR_ELEMENTS[values[0].typ]]
                return paths, Value(mode, VALUE_MODES[mode])
            if op in ('utf8_value', 'utf8_error') and values and isinstance(values[0], Value):
                exchange = values[0]
                if exchange.mode in ('mutable_ref_replace', 'mutable_ref_try_push'):
                    return paths, replace(exchange, mode='mut', typ='Int', reservations=exchange.reservations
                        if exchange.mode == 'mutable_ref_replace' and op == 'utf8_value' else frozenset())
                if exchange.mode == 'buffered_handle_exchange':
                    payload = exchange.exchange_payloads[op == 'utf8_error']
                    result = restore_handle_payload(Value('owned', exchange_element(exchange.typ), payload), exchange)
                    self.touch(result, paths['next'], line)
                    return paths, result
            if op == 'utf8_error' and values and isinstance(values[0], Value):
                if values[0].mode.startswith('join_'):
                    return paths, Value('runtime_error', 'runtime::Error')
                if values[0].mode in RESULT_ERROR_MODES:
                    mode = RESULT_ERROR_MODES[values[0].mode]
                    return paths, Value(mode, VALUE_MODES[mode])
                op = 'utf8_value'
            if op == 'utf8_value' and values and isinstance(values[0], Value):
                if values[0].mode in CONVERSION_PAYLOADS:
                    typ = CONVERSION_PAYLOADS[values[0].mode]
                    return paths, Value(FORMATS[typ].mode, 'Int' if typ == 'i32' else typ)
                if values[0].mode in NUMERIC_JOIN_FIELDS:
                    mode = values[0].mode.removeprefix('join_')
                    return paths, Value(mode, mode)
                if values[0].mode in PLAIN_JOIN_INNER_MODES:
                    inner = PLAIN_JOIN_INNER_MODES[values[0].mode]
                    return paths, Value(inner, PLAIN_JOIN_TYPES[inner])
                if values[0].mode.startswith('join_') and values[0].mode[5:] in ERROR_VALUE_TYPES:
                    mode = values[0].mode[5:]
                    return paths, Value(mode, VALUE_MODES[mode])
                if values[0].mode == 'join_runtime_error':
                    return paths, Value('runtime_error', 'runtime::Error')
                if values[0].mode in EXCHANGE_JOIN_TYPES:
                    return paths, replace(values[0], mode=exchange_inner_signature(values[0].mode)[0], typ=exchange_inner_signature(values[0].mode)[1])
                if values[0].mode in OPTION_JOIN_TYPES:
                    return paths, replace(values[0], mode=option_inner_signature(values[0].mode)[0])
                if values[0].mode in OWNED_JOIN_TYPES and owned_inner_mode(values[0].mode) != 'owned':
                    return paths, replace(values[0], mode=owned_inner_mode(values[0].mode))
                if values[0].mode == 'join_owned':
                    return paths, replace(values[0], mode='owned')
                if values[0].mode in ('join_ref', 'join_mut'):
                    return paths, Value(values[0].mode[5:], values[0].typ, values[0].assets)
                if values[0].mode in ('shared_ref_option', 'shared_ref_replace', 'shared_ref_try_push'):
                    return paths, Value('ref', 'Int', assets=values[0].assets)
                if values[0].mode in ('int_option', 'int_replace', 'int_try_push', 'read_result', 'join_int'):
                    return paths, SCALAR
                if values[0].mode.startswith('join_') and values[0].mode[5:] in ASYNC_VALUE_RESULT_FAMILIES:
                    mode = values[0].mode[5:]
                    return paths, Value(mode, VALUE_MODES[mode], values[0].all_assets)
                if values[0].mode == 'join_byte_ref':
                    return paths, Value('byte_ref', 'u8', values[0].assets)
                if values[0].mode == 'join_text':
                    return paths, Value('text', 'str', values[0].assets)
                if values[0].mode.startswith('join_') and values[0].mode[5:] in (*VECTOR_SLICE_ELEMENTS, *SHARED_VECTOR_SLICE_MODES):
                    return paths, Value(values[0].mode[5:], values[0].typ, values[0].assets)
                if values[0].mode == 'join_char':
                    return paths, Value('char', 'char')
                if values[0].mode == 'join_bool':
                    return paths, Value('bool', 'Bool')
                if values[0].mode in ('byte_option', 'byte_replace', 'byte_try_push', 'join_byte'):
                    return paths, Value('byte', 'u8')
            if op == 'array_vector_remove' and isinstance(values[0], Value) and values[0].typ in INLINE_VECTOR_ELEMENTS:
                element = INLINE_VECTOR_ELEMENTS[values[0].typ]
                index = expr[2][1] if expr[2][0] == 'int' else None
                payload = self.extract_vector_item(paths['next'], expr[1], index, line)
                origin = id(expr[1])
                source = Source('local', origin, 'data stack implicite', element)
                assets = frozenset({self.born(('remove', origin), source, paths['next'])})
                return paths, replace(payload, mode='owned', typ=element, assets=assets)
            if op == 'array_index' and isinstance(values[0], Value) and values[0].typ in INLINE_VECTOR_ELEMENTS:
                vector = values[0]
                index = expr[2][1] if expr[2][0] == 'int' else None
                payload = restore_handle_payload(Value('owned', INLINE_VECTOR_ELEMENTS[vector.typ],
                    handle_items_at(vector.handle_items, index) or frozenset()), vector)
                return paths, replace(payload, mode='inline_vector_slot', assets=vector.assets,
                                      projection_assets=vector.assets)
            if op == 'array_index' and isinstance(values[0], Value) and is_handle_vector(values[0].typ):
                vector = values[0]
                index = expr[2][1] if expr[2][0] == 'int' else None
                return paths, Value('handle_slot', 'A<Int>', vector.all_assets,
                                    handle_slot=(vector.assets, index) if vector.assets else None)
            if op == 'array_vector_remove' and isinstance(values[0], Value) and is_handle_vector(values[0].typ):
                index = expr[2][1] if expr[2][0] == 'int' else None
                return paths, self.extract_vector_item(paths['next'], expr[1], index, line)
            if op in ('array_index', 'array_vector_remove') and values and isinstance(values[0], Value) and values[0].typ in VECTOR_ELEMENTS:
                element = VECTOR_ELEMENTS[values[0].typ]
                return paths, Value('scalar' if element == 'Int' else 'byte', element,
                                    projection_assets=values[0].all_assets if op == 'array_index' else frozenset())
            if op == 'utf8_try_slice':
                if not values or not isinstance(values[0], Value) or values[0].typ not in ('str', 'String'):
                    self.fail(line, 'try_slice exige un &str ou String')
                return paths, Value('slice_result', UTF8_SLICE_RESULT, values[0].all_assets)
            if op == 'utf8_validate':
                assets = values[0].all_assets if values and isinstance(values[0], Value) else frozenset()
                return paths, Value('text_result', UTF8_TEXT_RESULT, assets)
            if op == 'utf8_value' and values and isinstance(values[0], Value) and values[0].mode in ('text_result', 'slice_result'):
                return paths, Value('text', 'str', values[0].all_assets)
            if op == 'utf8_value' and values and isinstance(values[0], Value) and values[0].mode in ('byte_replace_result', 'integer_conversion_result'):
                return paths, Value('byte', 'u8')
            if op == 'utf8_slice' and values and isinstance(values[0], Value) and values[0].typ in VECTOR_SLICE_MODES:
                mode = VECTOR_SLICE_MODES[values[0].typ]
                return paths, Value(mode, VALUE_MODES[mode], values[0].all_assets)
            if op == 'utf8_slice' and values and isinstance(values[0], Value):
                mode = SHARED_VECTOR_SLICE_MODES.get(values[0].mode, values[0].mode)
                if mode in VECTOR_SLICE_MODES.values():
                    return paths, replace(values[0], mode=mode)
            if op == 'utf8_slice' and values and isinstance(values[0], Value) and values[0].typ in ('str', 'String'):
                return paths, Value('text', 'str', values[0].all_assets)
            if op == 'array_integer_try_from':
                if getattr(values[0], 'mode', None) not in ('scalar', 'byte'):
                    self.fail(line, 'u8::try_from exige un Int ou un u8')
                return paths, Value('integer_conversion_result', 'Result<u8,IntegerConversionError>')
            if op == 'array_byte_literal':
                return paths, Value('byte', 'u8')
            if op in ('array_numeric_literal', 'array_numeric_operation', 'array_numeric_cast'):
                typ = expr[1]
                return paths, Value(FORMATS[typ].mode, 'Int' if typ == 'i32' else typ)
            if op in ('array_numeric_not', 'array_start_poller'):
                return paths, Value('bool', 'bool')
            if op == 'array_ffi_call':
                return paths, Value(*expr[2])
            if op in ('array_mutex_new', 'array_mutex_lock', 'array_mutex_acquire', 'array_hashmap_new'):
                current = paths['next']
                source = Source('local', id(expr), 'data stack implicite', expr[1])
                asset = self.born((op, id(expr)), source, current)
                targets = (('mutex', values[0].all_assets),) if op in ('array_mutex_lock', 'array_mutex_acquire') and isinstance(values[0], Value) else ()
                return paths, Value('owned', expr[1], frozenset({asset}), targets)
            if op in ('array_numeric_len', 'array_numeric_slice_len'):
                return paths, Value('u64', 'u64')
            if op == 'array_numeric_try_from':
                return paths, Value(conversion_mode(expr[1]), conversion_type(expr[1]))
            if op == 'array_integer_cast':
                mode, error = exact_integer_conversion(getattr(values[0], 'mode', None), expr[2])
                if error:
                    self.fail(line, error)
                return paths, Value(mode, expr[2])
            if op == 'builtin_error':
                return paths, Value(expr[1], VALUE_MODES[expr[1]])
            if op in UTF8_EXPRESSION_MODES:
                mode = UTF8_EXPRESSION_MODES[op]
                return paths, SCALAR if mode == 'scalar' else VOID if mode == 'void' else Value(mode, VALUE_MODES[mode])
            if op == 'array_deref_slot' and values and isinstance(values[0], Value) and values[0].mode in ('ref', 'mutable_vector_slot') and values[0].typ == 'Int':
                return paths, SCALAR
            if op == 'array_deref_call' and values and isinstance(values[0], Value) and values[0].typ == 'u8' and values[0].mode in ('byte_ref', 'mut'):
                return paths, Value('byte', 'u8')
            if op == 'arithmetic':
                return paths, SCALAR
            if op == 'array_index' and values and isinstance(values[0], Value) and values[0].typ == '[Int]':
                return paths, Value('scalar', 'Int', projection_assets=values[0].all_assets)
            if op == 'array_index' and values and isinstance(values[0], Value) and values[0].typ in ('str', 'String', '[u8]'):
                return paths, Value('byte', 'u8', projection_assets=values[0].all_assets)
            if op in ('array_ref', 'array_mut_ref') and values and values[0].mode == 'array_refs':
                return paths, replace(values[0], container_borrow=True, container_mode='mut' if op == 'array_mut_ref' else 'ref')
            if op == 'array_copy' and values and values[0].mode == 'array_refs':
                value = values[0]
                self.touch(value, paths['next'], line)
                return paths, Value(value.mode, value.typ, fields=value.fields, rows=value.rows,
                                    container_origins=frozenset({('copy', id(expr))}))
            if op == 'array_copy' and values and isinstance(values[0], Value) and '' in self.analyzer.enums.get(values[0].typ, {}):
                original = values[0]
                current = paths['next']
                sources = {Source('local', id(expr), 'data stack implicite', original.typ)
                           if asset.source.kind == 'local' and asset.source.name == 'data stack implicite'
                           else asset.source for asset in original.assets}
                if original.mode == 'inline_vector_slot':
                    self.touch(original, current, line)
                    sources = {Source('local', id(expr), 'data stack implicite', original.typ)}
                for source in sources:
                    self.copy_write(source, line)
                assets = frozenset(self.born(('copy', id(expr), source), source, current)
                                   for source in sources)
                return paths, replace(original, mode='owned', assets=assets, storage_owner=None,
                                      inline_path='', structure_choices=())
            if op in ('array_copy', 'array_transfer'):
                return paths, values[0]
            if op in ('array_literal', 'array_repeat') and values and all(
                    isinstance(child, Value) and child.mode == 'array_refs' and child.container_borrow for child in values):
                child = values[0]
                count = expr[2] if op == 'array_repeat' else len(values)
                children = [child] * count if op == 'array_repeat' else values
                element = ('&mut ' if child.container_mode == 'mut' else '&') + child.typ
                return paths, Value('array_refs', f'[{element};{count}]',
                    fields=tuple((str(slot), child.all_assets) for slot, child in enumerate(children)),
                    rows=tuple((str(slot), child) for slot, child in enumerate(children)),
                    container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_repeat' and values and values[0].mode == 'array_refs':
                child = values[0]
                width = reference_array_shape(child.typ)[1]
                fields = tuple((str(row * width + int(slot)), assets)
                               for row in range(expr[2]) for slot, assets in child.fields)
                return paths, Value('array_refs', f'[{child.typ};{expr[2]}]', fields=fields,
                                    container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_literal' and values and all(value.mode == 'array_refs' for value in values):
                width = reference_array_shape(values[0].typ)[1]
                fields = tuple((str(row * width + int(slot)), assets)
                               for row, child in enumerate(values) for slot, assets in child.fields)
                return paths, Value('array_refs', f'[{values[0].typ};{len(values)}]', fields=fields,
                                    container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_repeat' and values and values[0].mode in ('ref', 'array_ref'):
                return paths, Value('array_refs', f'[&{values[0].typ};{expr[2]}]', fields=tuple(
                    (str(slot), values[0].all_assets) for slot in range(expr[2])), container_origins=frozenset({('literal', id(expr))}))
            if op == 'array_literal' and values and all(
                    isinstance(value, Value) and value.mode in ('ref', 'mut', 'array_ref', 'array_mut')
                    for value in values):
                element = ('&mut ' if values[0].mode in ('mut', 'array_mut') else '&') + values[0].typ
                return paths, Value('array_refs', f'[{element};{len(values)}]', fields=tuple(
                    (str(slot), value.all_assets) for slot, value in enumerate(values)),
                                    container_origins=frozenset({('literal', id(expr))}))
            if values and isinstance(values[0], Value) and values[0].mode == 'array_refs':
                holder = values[0]
                fields = dict(holder.fields)
                element, length = fixed_array_shape(holder.typ)
                nested = reference_array_shape(element)
                if op == 'array_index' and nested:
                    _, groups = reference_array_projection(holder.typ, (expr[2],))
                    row = project_reference_array(holder, element, groups)
                    self.touch(row, paths['next'], line, before=before_index)
                    return paths, row
                selected = (str(expr[2][1]),) if len(expr) > 2 and expr[2][0] == 'int' else tuple(fields)
                assets = frozenset(a for slot in selected for a in fields.get(slot, ()))
                if op == 'array_index' and reference_type(element) and reference_array_shape(reference_type(element)[1]):
                    rows = dict(holder.rows)
                    chosen = [rows[slot] for slot in selected if slot in rows]
                    if not chosen:
                        self.fail(line, 'provenance de ligne référencée manquante')
                    row = merge_reference_values(chosen)
                    self.touch(row, paths['next'], line, before=before_index)
                    return paths, replace(row, container_borrow=True, container_mode=reference_array_shape(holder.typ)[0])
                if op == 'array_index':
                    value = Value('array_' + reference_array_shape(holder.typ)[0], reference_type(element)[1], assets)
                    self.touch(value, paths['next'], line)
                    return paths, value
                if op in ('array_replace', 'array_swap'):
                    name, prefix = reference_array_path(expr[1])
                    root = holder
                    if op == 'array_swap':
                        _, left = reference_array_projection(root.typ, (expr[2],))
                        _, right = reference_array_projection(root.typ, (expr[3],))
                        fields = dict(root.fields)
                        assets = frozenset(asset for group in (*left, *right) for index in group
                                           for asset in fields.get(str(index), ()))
                        self.touch(Value('ref', 'Int', assets), paths['next'], line)
                        updated = swap_reference_fields(root.fields, root.typ, (), expr[2], expr[3])
                        update_array_aliases(paths['next'].environment, name, updated, root, swapped_reference_rows(root, expr[2], expr[3]))
                        return paths, VOID
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
                    if not row and reference_array_shape(pointee):
                        stored_rows = dict(root.rows)
                        removed = merge_reference_values([stored_rows[str(index)] for index in positions[0]])
                        removed = replace(removed, container_borrow=True, container_mode=mode)
                        self.touch(removed, paths['next'], line)
                        update_array_aliases(paths['next'].environment, name, updated, root, updated_rows)
                        return paths, removed
                    result = (Value('array_refs', target_type, fields=old,
                                    container_origins=frozenset({('replace', id(expr))})) if row else
                              Value(mode, pointee, dict(old).get('0', frozenset())))
                    self.touch(result, paths['next'], line)
                    update_array_aliases(paths['next'].environment, name, updated, root, updated_rows)
                    return paths, result
            if values and isinstance(values[0], Value):
                holder = values[0]
                shape = fixed_array_shape(holder.typ)
                if op in ('array_ref', 'array_mut_ref') and shape:
                    return paths, Value('array_mut' if op == 'array_mut_ref' else 'array_ref', holder.typ, holder.all_assets)
                if op in ('array_index', 'array_replace') and shape and shape[0] == 'u8':
                    return paths, Value('byte', 'u8')
                if op == 'array_index' and shape:
                    element, _ = shape
                    return paths, Value('array' if fixed_array_shape(element) else 'scalar', element, holder.all_assets)
                if op in ('array_literal', 'array_repeat'):
                    length = expr[2] if op == 'array_repeat' else len(values)
                    return paths, Value('array', f'[{holder.typ};{length}]', holder.all_assets)
            return paths, SCALAR if op in ('array_index', 'array_len', 'array_replace') else UNKNOWN
        if op == 'loop_expr':
            return self.loop(expr[1], state, valued=True, expected_array=expected_array)
        if op == 'reborrow':
            parent = self.lookup(expr[1], state, line)
            self.touch(parent, state, line)
            if isinstance(parent, Value):
                if parent.mode in (*SHARED_VECTOR_SLICE_MODES, *VECTOR_SLICE_MODES.values()):
                    mode = SHARED_VECTOR_SLICE_MODES.get(parent.mode, parent.mode) if expr[2] == 'ref' else parent.mode
                    return {'next': state}, replace(parent, mode=mode)
                if parent.mode == 'byte_ref':
                    return {'next': state}, parent
                if parent.mode == 'array_refs':
                    return {'next': state}, replace(parent, container_borrow=True, container_mode=expr[2])
                mode = 'array_' + expr[2] if parent.mode in ('array_ref', 'array_mut') else expr[2]
                return {'next': state}, replace(parent, mode=mode)
            return {'next': state}, UNKNOWN
        if op == 'match_expr':
            return self.nodes([expr[1]], state, valued=True, expected_array=expected_array)
        if op == 'bool':
            return {'next': state}, Value('bool', 'bool')
        if op == 'int':
            return {'next': state}, SCALAR
        if op in ('name', 'move', 'down', 'ref', 'mut', 'deref'):
            value = self.lookup(expr[1], state, line)
            self.touch(value, state, line)
            if op == 'deref':
                from mutex_syntax import GUARD_TYPES, payload_type
                content = (payload_type(value.typ, GUARD_TYPES) or value.typ) if isinstance(value, Value) else None
                mode = scalar_field_mode(content) if content else None
                return {'next': state}, Value(mode, content) if mode else SCALAR
            if op in ('ref', 'mut') and isinstance(value, Value):
                if value.mode in EXTRA_MODES:
                    return {'next': state}, replace(value, mode='array_' + op)
                if value.mode == 'array_refs':
                    return {'next': state}, replace(value, container_borrow=True, container_mode=op)
                if value.mode in ('ref', 'mut'):
                    self.fail(line, 'emprunt imbriqué non pris en charge : & sur un emprunt ajoute un niveau ; utiliser son nom')
                value = replace(value, mode=op, storage_owner=expr[1]
                                if op == 'mut' and (is_handle_vector(value.typ) or '' in self.analyzer.enums.get(value.typ, {})) else None)
            return {'next': state}, value
        if op in ('ref_expr', 'mut_expr') and expr[1][0] == 'array_deref_slot':
            paths, value = self.expression(expr[1][1], state, line)
            if value.mode == 'mutable_vector_slot':
                return paths, Value('mut' if op == 'mut_expr' else 'ref', 'Int', value.assets,
                                    reservations=value.projection_assets)
            if value.mode == 'array_refs':
                return paths, replace(value, container_borrow=True, container_mode='mut' if op == 'mut_expr' else 'ref')
            if value.typ.startswith('A<'):
                return paths, replace(value, mode='mut' if op == 'mut_expr' else 'ref')
            return paths, Value('array_mut' if op == 'mut_expr' else 'array_ref', value.typ,
                                value.assets, value.fields, value.reservations)
        if op in ('ref_expr', 'mut_expr') and expr[1][0] == 'array_index':
            paths, projected = self.expression(expr[1], state, line)
            if isinstance(projected, Value) and projected.mode == 'handle_slot':
                return paths, replace(projected, mode='mut' if op == 'mut_expr' else 'ref')
            if isinstance(projected, Value) and projected.mode == 'scalar' and projected.projection_assets:
                return paths, Value('mut' if op == 'mut_expr' else 'ref', 'Int', projected.projection_assets)
            if isinstance(projected, Value) and projected.mode == 'byte':
                mode = ('mut' if projected.projection_assets else 'array_mut') if op == 'mut_expr' else 'byte_ref'
                return paths, Value(mode, 'u8', projected.projection_assets)
            if isinstance(projected, Value) and projected.mode == 'array_refs':
                return paths, replace(projected, container_borrow=True, container_mode='mut' if op == 'mut_expr' else 'ref')
            return paths, Value('array_mut' if op == 'mut_expr' else 'array_ref', projected.typ, projected.all_assets)
        if op in ('ref_expr', 'mut_expr') and expr[1][0] == 'field':
            carrier = self.lookup(expr[1][1], state, line)
            if not isinstance(carrier, Value):
                self.fail(line, 'un emprunt de champ exige une structure')
            self.touch(carrier, state, line)
            from structure_views import contained_field
            projection = contained_field(self.analyzer.enums, carrier.typ, expr[1][2])
            if projection is not None:
                from structure_views import project_fields
                path = expr[1][2]
                return {'next': state}, Value('mut' if op == 'mut_expr' else 'ref', projection.typ, carrier.assets,
                    fields=project_fields(carrier.fields, path), storage_owner=carrier.storage_owner or expr[1][1],
                    inline_path=(carrier.inline_path + '.' if carrier.inline_path else '') + path)
            declared = dict(self.analyzer.enums.get(carrier.typ, {}).get('', ())).get(expr[1][2])
            return {'next': state}, Value('array_mut' if op == 'mut_expr' else 'array_ref',
                                         declared if declared in FORMATS else 'Int', carrier.assets)
        if op == 'field_deref' or (op in ('ref_expr', 'mut_expr') and expr[1][0] == 'field_deref'):
            place = expr[1] if op == 'field_deref' else expr[1][1]
            carrier = self.lookup(place[1], state, line)
            if op == 'field_deref':
                self.touch(carrier, state, line)
                return {'next': state}, SCALAR
            if not isinstance(carrier, Value):
                self.fail(line, 'un réemprunt de champ exige une structure')
            if carrier.structure_choices:
                branches, values = [], []
                for choice in carrier.structure_choices:
                    branch = state.clone()
                    branch.environment[place[1]] = choice
                    paths, value = self.expression(expr, branch, line)
                    branches.append(paths)
                    if 'next' in paths:
                        values.append(value)
                return merge_paths(*branches), join_values(values) if values else UNKNOWN
            key = '.' + place[2]
            targets = dict(carrier.fields).get(key, frozenset())
            declared = dict(self.analyzer.enums.get(carrier.typ, {}).get('', ())).get(place[2], '')
            capability = reference_type(declared)
            if capability and capability[0] == 'ref' and op == 'ref_expr':
                return self.expression(place, state, line)
            self.touch(carrier, state, line)
            if declared.startswith('A<'):
                capability = 'mut', declared[2:-1]
            if capability and capability[0] == 'mut' and capability[1] in self.analyzer.enums:
                return {'next': state}, Value('mut' if op == 'mut_expr' else 'ref', capability[1], targets,
                                              nested_reference_fields(carrier.fields, key),
                                              carrier.assets | carrier.reservations,
                                              storage_owner=(carrier.storage_owner or place[1]) if declared.startswith('A<') else None,
                                              owned_path=(*carrier.owned_path,
                                                  ('.' + carrier.inline_path if carrier.inline_path else '') + key)
                                              if declared.startswith('A<') else ())
            return {'next': state}, Value('array_mut' if op == 'mut_expr' else 'array_ref',
                                          'Int', targets, reservations=carrier.assets | carrier.reservations)
        if op in ('transfer', 'new_transfer', 'ref_expr', 'mut_expr'):
            paths, value = self.expression(expr[1], state, line, expected_array if op != 'new_transfer' else None)
            if op in ('ref_expr', 'mut_expr') and isinstance(value, Value):
                if expected_array is not None and expr[1][0] in ('array_literal', 'array_repeat'):
                    mode = 'mut' if op == 'mut_expr' else 'ref'
                    if value.mode == 'array_refs':
                        return paths, replace(value, container_borrow=True, container_mode=mode)
                    return paths, replace(value, mode='array_' + mode)
                if value.mode in ('ref', 'mut'):
                    self.fail(line, 'emprunt imbriqué non pris en charge : & sur un emprunt ajoute un niveau ; utiliser son nom')
                value = replace(value, mode='ref' if op == 'ref_expr' else 'mut')
            return paths, value
        if op in ('scope', 'value_match'):
            body = expr[1] if op == 'value_match' else expr[2]
            return self.block(body, state, valued=True, expected_array=expected_array)
        if op == 'if_expr':
            condition, yes, no = expr[1:]
            paths = self.condition(condition, state, line)
            if 'next' not in paths:
                return paths, UNKNOWN
            entry = paths.pop('next')
            if self.absent_option_success(condition, entry):
                branch, value = (self.expression(no, entry, line, expected_array) if isinstance(no, tuple)
                                 else self.block(no, entry, valued=True, expected_array=expected_array))
                return merge_paths(paths, branch), value
            yes_entry, no_entry = entry.clone(), entry.clone()
            self.refine_handle_branches(condition, yes_entry, no_entry)
            left, a = (self.expression(yes, yes_entry, line, expected_array) if isinstance(yes, tuple)
                       else self.block(yes, yes_entry, valued=True, expected_array=expected_array))
            right, b = (self.expression(no, no_entry, line, expected_array) if isinstance(no, tuple)
                        else self.block(no, no_entry, valued=True, expected_array=expected_array))
            values = [value for branch, value in ((left, a), (right, b))
                      if 'next' in branch and isinstance(value, Value)]
            value = join_values(self.unify_handle_values(values)) if values else UNKNOWN
            return merge_paths(paths, left, right), value
        if op == 'struct_copy':
            source = self.source(expr[1], state, line)
            original = self.lookup(expr[2], state, line)
            if not isinstance(original, Value) or original.typ != source.element:
                self.fail(line, 'pool.copy : type du porteur incompatible avec le pool')
            self.touch(original, state, line)
            self.use_source(source, True, line)
            asset = self.born(('new', id(expr)), source, state)
            return {'next': state}, replace(original, mode='owned', assets=frozenset({asset}), storage_owner=None,
                                           inline_path='', structure_choices=())
        if op in ('new', 'new_enum'):
            values = [expr[2]] if op == 'new' else [v for _, v in expr[4]]
            paths = {'next': state}
            evaluated = []
            for value in values:
                if 'next' not in paths:
                    return paths, UNKNOWN
                following, field_value = self.expression(value, paths.pop('next'), line)
                evaluated.append(field_value)
                paths = merge_paths(paths, following)
            if 'next' not in paths:
                return paths, UNKNOWN
            current = paths['next']
            source = (Source('local', id(expr), 'data stack implicite', expr[2])
                      if op == 'new_enum' and expr[1] is None
                      else self.source(expr[1], current, line))
            typ = expr[3] if op == 'new' else expr[2] or source.element
            arm = expr[3] if op == 'new_enum' else None
            if op == 'new' and expr[4:] == ('pool_default',) and ('' in self.analyzer.enums.get(source.element, {}) or source.element in ('String', *VECTOR_TYPES)):
                typ, arm = source.element, ''
            fields = []
            if op == 'new_enum':
                declared = dict(self.analyzer.enums.get(typ, {}).get(arm, ()))
                for (field_name, _), field_value in zip(expr[4], evaluated):
                    field_type = declared.get(field_name, '')
                    if (reference_type(field_type) or field_type.startswith('A<')) and isinstance(field_value, Value):
                        self.touch(field_value, current, line)
                        key = f'{expr[3]}.{field_name}'
                        fields.append((key, field_value.assets if field_type.startswith('A<') else field_value.all_assets))
                        fields.extend((f'{key}/{path}', targets) for path, targets in field_value.fields)
            self.use_source(source, True, line)
            asset = self.born(('new', id(expr)), source, current)
            if op == 'new_enum':
                # A stored handle must survive even if the aggregate is only
                # used by its implicit destructor after a reset.
                contained = frozenset(origin.source for (field_name, _), field_value in zip(expr[4], evaluated)
                                      if declared.get(field_name, '').startswith('A<') and isinstance(field_value, Value)
                                      for origin in field_value.assets if origin.source.kind != 'local')
                if contained:
                    current.vector_sources[asset] = contained
            return paths, Value('owned', typ, frozenset({asset}), tuple(fields),
                                frozenset(a for v in evaluated if isinstance(v, Value)
                                          for a in v.reservations) if op == 'new_enum' else frozenset(),
                                variants=frozenset({arm}) if arm is not None else frozenset(),
                                handle_items=() if typ in (*HANDLE_VECTORS, *REFERENCE_VECTORS, *INLINE_VECTOR_ELEMENTS) else None)
        if op == 'call':
            return self.call(expr, state, line)
        return {'next': state}, UNKNOWN

    def call(self, expr, state, line):
        name, args = expr[1:]
        asynchronous = name in self.analyzer.async_functions
        catalog = self.analyzer.async_functions if asynchronous else self.analyzer.functions
        if name not in catalog:
            self.fail(line, f"fonction inconnue '{name}'")
        params = catalog[name].args[1]
        if len(args) != len(params):
            self.fail(line, f"'{name}' attend {len(params)} argument(s), reçu {len(args)}")
        paths, actuals, frame = {'next': state}, [], []
        self.pending_sources.append(frame)
        try:
            for index, arg in enumerate(args):
                if 'next' not in paths:
                    return paths, UNKNOWN
                _, mode, typ = params[index]
                expected = typ if mode in ('array', 'array_refs', 'array_refs_owned', 'array_ref', 'array_mut') else None
                following, value = self.expression(arg, paths.pop('next'), line, expected)
                paths = merge_paths(paths, following)
                from handle_types import is_public_handle
                if mode == 'execution' and is_public_handle(typ) and isinstance(value, Value) and value.mode == 'execution':
                    from handle_types import contextual_public_type
                    actual_type = contextual_public_type(value.typ, typ, self.analyzer.async_functions)
                    if actual_type != typ:
                        self.fail(line, f'handle {typ} attendu, reçu {actual_type}')
                    value = self.public_handle_value(value, typ)
                actuals.append(value)
                if 'next' in paths and isinstance(value, Source):
                    self.use_source(value, mode == 'mut', line)
                    frame.append((value, mode))
            if 'next' not in paths:
                return paths, UNKNOWN
            if hook := getattr(self.analyzer, 'storage_call_hook', None):
                hook(self, catalog[name], actuals, line)
            if asynchronous:
                assets = frozenset(asset for (_, mode, _), value in zip(params, actuals)
                                   if mode in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) and isinstance(value, Value) for asset in value.all_assets)
                from async_lowering import owned_result_parameters, utf8_result_parameters
                returned = utf8_result_parameters(catalog[name], catalog,
                                                  sync_result_contract=self.analyzer.sync_result_contract)
                captures = tuple((str(position), value.all_assets)
                                 for position, ((_, mode, _), value) in enumerate(zip(params, actuals))
                                 if (mode in ('ref', 'mut', 'array_ref', 'array_mut', *ASYNC_CAPTURE_VIEW_MODES)
                                     or position in returned) and isinstance(value, Value))
                captures += tuple((f'{position}/{path}', targets)
                    for position, ((_, mode, _), value) in enumerate(zip(params, actuals))
                    if mode in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) and isinstance(value, Value)
                    for path, targets in value.fields)
                reservations = frozenset(asset for _, targets in captures for asset in targets)
                self.touch_assets(reservations, paths['next'], line)
                indexes = owned_result_parameters(catalog[name], catalog, sync_result=self.analyzer.results.get)
                from async_result_storage import root_result_parameters
                root_indexes = root_result_parameters(catalog[name], indexes)
                result_assets = frozenset(asset for index in root_indexes if isinstance(actuals[index], Value)
                                          for asset in actuals[index].assets)
                pool_assets = {index: self.born(('task_pool', id(expr), index), value, paths['next'])
                               for index, value in enumerate(actuals) if isinstance(value, Source)}
                assets |= frozenset(pool_assets.values())
                result_assets |= frozenset(asset for index, asset in pool_assets.items() if index in root_indexes)
                from async_result_storage import result_storage
                local_inputs = frozenset(index for index, value in enumerate(actuals)
                    if isinstance(value, Value) and value.assets and all(
                        asset.source.kind == 'local' and asset.source.name == 'data stack implicite'
                        for asset in value.assets))
                plan = result_storage(catalog[name], local_inputs)
                if plan.destination:
                    output = self.born(('task_output', id(expr)),
                        Source('local', id(expr), 'data stack implicite', catalog[name].args[2][1]), paths['next'])
                    result_assets |= frozenset({output})
                    assets |= frozenset({output})
                reference_assets = self.async_reference_assets(catalog[name], actuals, line)
                result_fields = dict(merge_fields(actuals[index] for index in indexes if isinstance(actuals[index], Value)))
                from async_result_storage import pool_result_graph
                graph = pool_result_graph(catalog[name], self.analyzer.enums)
                if graph is not None and is_handle_vector(catalog[name].args[2][1]):
                    def graph_assets(symbol):
                        if symbol.kind == 'source_parameter':
                            return frozenset({pool_assets[symbol.index]})
                        actual = actuals[symbol.index]
                        if not isinstance(actual, Value):
                            return frozenset()
                        if symbol.kind == 'allocation_parameter':
                            return actual.assets
                        if symbol.kind == 'vector_element_parameter':
                            return possible_handle_items(actual.handle_items) or frozenset()
                        if symbol.kind == 'allocation_field_parameter':
                            return self.projected_assets(actual, symbol.name, paths['next'])
                        return frozenset()
                    for path, symbols in graph[1]:
                        result_fields[path] = frozenset().union(*(graph_assets(symbol) for symbol in symbols))
                return paths, Value('task', name, assets, captures, reservations=reservations,
                                    task_result_assets=result_assets, task_reference_assets=reference_assets,
                                    task_result_fields=tuple(result_fields.items()))
            current = paths['next']
            for (pname, mode, typ), value in zip(params, actuals):
                if mode in ('task', 'execution'):
                    if not isinstance(value, Value) or (value.mode, value.typ) != (mode, typ):
                        self.fail(line, f"'{pname}' attend un {mode} de {typ}")
                    continue
                if typ != 'Allocator' and not typ.startswith('Pool<') and mode not in ('scalar', *VALUE_MODES, 'array', 'array_ref', 'array_mut', 'array_refs', 'array_refs_owned'):
                    if not isinstance(value, Value) or (
                            not value.assets and value.mode not in ('array_ref', 'array_mut')
                            and not (mode == value.mode and mode in ('join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES)
                                     and value.absent_owned_payload)
                            and (mode, value.mode) != ('handle_option', 'handle_option')):
                        self.fail(line, f"'{pname}' attend une allocation {typ}")
                if mode in UTF8_BORROW_MODES or mode not in ('scalar', *VALUE_MODES, 'array', 'array_ref', 'array_mut', 'array_refs', 'array_refs_owned'):
                    self.touch(value, current, line)
                elif reference_array_shape(typ) and isinstance(value, Value):
                    targets = frozenset(asset for _, assets in reference_tree_fields(value) for asset in assets)
                    self.touch(replace(value, assets=value.assets | targets), current, line)
            for (parameter_name, _, parameter_type), actual in zip(params, actuals):
                if reference_array_shape(parameter_type) and (
                        not isinstance(actual, Value) or actual.typ != parameter_type):
                    self.fail(line, f"'{parameter_name}' attend un tableau {parameter_type}")
            frame.clear()
            if any(mode == 'mut' and typ.startswith('A<') and typ != f'A<{HANDLE_VECTOR}>' for _, mode, typ in params):
                self.invalidate_handle_items(current)
            summary = self.analyzer.infer(name)
            def sources(symbol):
                if symbol.kind in ('local_value', 'task_output'):
                    return (Source('local', id(expr), 'data stack implicite', symbol.element),)
                actual = actuals[symbol.index]
                if symbol.kind == 'task_output_parameter':
                    return tuple(Source('local', id(expr), 'data stack implicite', symbol.element)
                                 if a.source.kind == 'local' and a.source.name == 'data stack implicite'
                                 else a.source for a in actual.assets)
                if symbol.kind == 'task_result_field_parameter':
                    return tuple(asset.source for asset in dict(actual.task_result_fields).get(symbol.name, ()))
                if symbol.kind == 'task_result_parameter':
                    return tuple(asset.source for asset in actual.task_result_assets)
                if symbol.kind == 'task_reference_result_parameter':
                    return tuple(asset.source for asset in actual.task_reference_assets)
                if symbol.kind in ('task_utf8_parameter', 'task_borrow_parameter'):
                    return tuple(asset.source for asset in dict(actual.fields).get(symbol.name, ()))
                if symbol.kind == 'allocation_field_parameter':
                    assets = (self.projected_assets(actual, symbol.name, current)
                              if actual.typ in REFERENCE_VECTORS else
                              reference_tree_targets(actual, symbol.name) if reference_array_shape(actual.typ) else
                              dict(actual.fields).get(symbol.name, ()))
                    return tuple(a.source for a in assets)
                if symbol.kind == 'vector_element_parameter':
                    items = possible_handle_items(actual.handle_items)
                    if items is None:
                        self.fail(line, 'provenance des éléments du vecteur inconnue pour cet appel')
                    return tuple(a.source for a in items)
                if symbol.kind == 'reservation_parameter':
                    return tuple(a.source for a in actual.reservations)
                return (actual,) if isinstance(actual, Source) else tuple(a.source for a in actual.assets)
            for requirement in summary.all_requirements:
                for left in sources(requirement.left):
                    for right in sources(requirement.right):
                        self.require(requirement.relation, left, right, line, requirement.reason)
            for symbol in summary.copy_writes:
                for source in sources(symbol):
                    self.copy_write(source, line)
            effects = self.analyzer.effects[name]
            for (_, mode, _), actual in zip(params, actuals):
                if mode == 'execution' and isinstance(actual, Value):
                    for token in actual.execution_tokens:
                        current.pending_executions.pop(token, None)
            for index in effects.resets:
                self.reset(actuals[index], current, line)
            if not effects.may_return:
                del paths['next']
                return paths, UNKNOWN
            result = self.analyzer.results[name]
            def replacement_sources(child):
                for item in child.candidates:
                    if item.kind == 'fresh':
                        yield actuals[item.source.index]
                    elif item.kind == 'parameter':
                        yield from (asset.source for asset in actuals[item.parameter].all_assets)
                    elif item.kind == 'owned_projection':
                        actual = actuals[item.parameter]
                        yield from (asset.source for asset in dict(actual.fields).get(item.field_path, ()))
                        for _, targets in nested_reference_fields(actual.fields, item.field_path):
                            yield from (asset.source for asset in targets)
                for _, nested in child.owned_fields:
                    yield from replacement_sources(nested)

            for _, _, child in result.owned_field_writes:
                current.inserted_sources |= frozenset(replacement_sources(child))
            handle_updates = {}
            write_fields = dict(result.handle_write_fields)
            for parameter, candidates in result.handle_writes:
                target = actuals[parameter]
                assets = set()
                for candidate in candidates:
                    if candidate.kind == 'parameter':
                        assets.update(actuals[candidate.parameter].assets)
                    elif candidate.kind == 'vector_element':
                        items = actuals[candidate.parameter].handle_items
                        if items is None:
                            self.fail(line, 'provenance des éléments du vecteur inconnue pour cet appel')
                        index = candidate.item_index
                        if index == VECTOR_LAST_ITEM:
                            index = last_handle_index(items, candidate.excluded_items, candidate.tail_offset)
                        assets.update(handle_items_at(items, index))
                    else:
                        assets.update(self.born(('handle-write', id(expr), parameter, source), source, current)
                                      for source in sources(candidate.source))
                fields = tuple((field, frozenset(asset for borrow in borrows
                    for asset in (dict(actuals[borrow.parameter].fields).get(borrow.field, ())
                                  if borrow.kind == 'field_parameter'
                                  else array_contract_assets(borrow, actuals[borrow.parameter]))))
                    for field, borrows in write_fields.get(parameter, ()))
                reservations = frozenset(asset for _, borrows in write_fields.get(parameter, ())
                                         for borrow in borrows for asset in actuals[borrow.parameter].reservations)
                items = (self.apply_vector_result_candidates(candidates, actuals, current, (id(expr), parameter))
                         if target.typ == f'A<{HANDLE_VECTOR}>' else None)
                handle_updates[parameter] = replace(target, assets=frozenset(assets), fields=fields,
                                                    reservations=reservations,
                                                    handle_items=items)
            for parameter, target in handle_updates.items():
                actuals[parameter] = target
                self.update_handle(current, target, replace(target, mode='owned', typ=target.typ[2:-1], storage_owner=None))
            for parameter, slots, exact, replacements, removals in result.vector_writes:
                receiver = borrowed_array_name(args[parameter])
                if removals or not exact:
                    alias = current.environment.get(receiver)
                    if isinstance(alias, Value):
                        owner = alias.storage_owner or receiver
                        vector = current.environment.get(owner)
                        if isinstance(vector, Value) and vector.assets == alias.assets:
                            items = remaining_handle_items(vector.handle_items, removals)
                            if not exact:
                                items = possible_handle_items(items)
                            current.environment[owner] = replace(vector, handle_items=items)
                            if owner != receiver:
                                current.environment[receiver] = replace(alias, handle_items=items)
                        else:
                            self.invalidate_handle_items(current)
                for index, slot in (*replacements, *((None, slot) for slot in slots)):
                    assets = set()
                    for item in slot:
                        if item.kind == 'parameter':
                            assets.update(actuals[item.parameter].assets)
                        elif item.kind == 'vector_element':
                            donor = actuals[item.parameter].handle_items
                            index = item.item_index
                            if index == VECTOR_LAST_ITEM:
                                index = last_handle_index(donor, item.excluded_items, item.tail_offset)
                            if donor is None:
                                self.fail(line, 'provenance des éléments du vecteur inconnue pour cet appel')
                            assets.update(handle_items_at(donor, index))
                        else:
                            source = (Source('local', id(expr), 'inline vector case', vector_payload_element(actuals[parameter].typ))
                                      if item.source.kind == 'local_value' and actuals[parameter].typ in INLINE_VECTOR_ELEMENTS
                                      else actuals[item.source.index])
                            assets.add(self.born(('vector_call', id(expr), source), source, current))
                    incoming = Value('owned', vector_payload_element(actuals[parameter].typ), frozenset(assets))
                    def resolve_payload(payload, root_assets):
                        inherited = [actuals[item.parameter] for item in payload.candidates if item.kind == 'parameter']
                        fields = dict(merge_fields(inherited)) if inherited else {}
                        for field, targets in payload.fields:
                            fields[field] = frozenset(asset for target in targets for asset in
                                (dict(actuals[target.parameter].fields).get(target.field, ())
                                 if target.kind == 'field_parameter' else
                                 array_contract_assets(target, actuals[target.parameter])))
                        for field, child in payload.owned_fields:
                            child_assets = set()
                            for candidate in child.candidates:
                                actual = actuals[candidate.parameter] if candidate.parameter >= 0 else None
                                if candidate.kind == 'parameter':
                                    child_assets.update(actual.assets)
                                elif candidate.kind == 'owned_projection':
                                    child_assets.update(dict(actual.fields).get(candidate.field_path, ()))
                                elif candidate.kind == 'fresh':
                                    child_assets.update(self.born(('vector_child', id(expr), field, source), source, current)
                                                        for source in sources(candidate.source))
                            child_value = resolve_payload(child, frozenset(child_assets))
                            fields[field] = child_value.assets
                            fields.update((field + '/' + key, targets) for key, targets in child_value.fields)
                        return Value('owned', payload.typ, root_assets, tuple(fields.items()),
                                     reservations=frozenset(asset for value in inherited for asset in value.reservations))
                    for payload in dict(result.vector_write_payloads).get(parameter, ()):
                        if payload.candidates.intersection(slot):
                            self.remember_handle_payload(current.environment, receiver, resolve_payload(payload, incoming.assets))
                    if actuals[parameter].typ not in INLINE_VECTOR_ELEMENTS:
                        self.retain_handle_origin(incoming, current)
                    self.publish_handle_exchange(current, (receiver, index, incoming.assets, index is None), exact=exact)
            updated_structures = {}
            for parameter, fields in result.structure_fields:
                name = borrowed_array_name(args[parameter])
                projected = name is None and isinstance(actuals[parameter], Value) and (
                    actuals[parameter].owned_path or actuals[parameter].structure_choices or actuals[parameter].inline_path)
                if projected:
                    name = '\0projected_structure_update'
                    current.environment[name] = actuals[parameter]
                if name not in current.environment:
                    self.fail(line, 'prototype : mise à jour de champ exige un porteur nommé')
                carrier = current.environment[name]
                changes = {}
                for field, targets in fields:
                    assets = frozenset(asset for target in targets for asset in (
                        dict(actuals[target.parameter].fields).get(target.field, ())
                        if target.kind == 'field_parameter' else array_contract_assets(target, actuals[target.parameter])))
                    self.touch(Value('ref', 'Int', assets), current, line)
                    if carrier.typ not in REFERENCE_VECTORS:
                        self.retain_handle_origin(Value('ref', 'Int', assets), current)
                    changes[field] = assets
                if carrier.typ in REFERENCE_VECTORS:
                    slots = dict(result.reference_appends).get(parameter)
                    items = changes['.items']
                    if slots is not None and isinstance(carrier.handle_items, tuple):
                        items = (*carrier.handle_items, *(frozenset(
                            asset for target in slot for asset in array_contract_assets(target, actuals[target.parameter]))
                            for slot in slots))
                    update_shared_vector_items(current.environment, current.shadows, carrier, items,
                                               lambda value: value.assets)
                else:
                    updated_structures[parameter] = self.update_structure(current, name, carrier, changes, line)
                if projected:
                    current.environment.pop(name)
            def result_actual(target):
                actual = actuals[target.parameter]
                if target.parameter in updated_structures and (
                        target.kind == 'indirect_field_parameter'
                        or (target.kind == 'field_parameter' and target.field.startswith('.'))):
                    return replace(actual, fields=tuple(updated_structures[target.parameter].items()))
                return actual

            for parameter, fields in result.parameter_fields:
                argument = args[parameter]
                actual_name = borrowed_array_name(argument)
                updated = []
                for slot, targets in fields:
                    assets = frozenset(
                        asset for target in targets
                        for asset in array_contract_assets(target, result_actual(target)))
                    updated.append((slot, assets))
                rebuilt = rebuild_reference_tree(actuals[parameter], params[parameter][2], tuple(updated), fields, actuals)
                update_array_aliases(current.environment, actual_name, rebuilt.fields, actuals[parameter], rebuilt.rows)
            for parameter, path, fields in result.referent_fields:
                holder, slot = reference_tree_slot(actuals[parameter], path)
                row = dict(holder.rows)[slot]
                mapped = tuple((field, frozenset(asset for target in targets
                    for asset in array_contract_assets(target, result_actual(target)))) for field, targets in fields)
                rebuilt = rebuild_reference_tree(row, row.typ, mapped, fields, actuals)
                actual_name = borrowed_array_name(args[parameter])
                update_array_aliases(current.environment, actual_name, rebuilt.fields, row, rebuilt.rows)
            if result.mode in ('ref', 'mut'):
                targets = tuple(target for target in result.reference_targets
                                if reachable_field(target, actuals[target.parameter]))
                assets = frozenset(a for target in targets
                                   if target.kind != 'array_parameter'
                                   for a in (actuals[target.parameter].task_reference_assets
                                             if target.kind == 'task_capture_parameter'
                                             else self.projected_assets(actuals[target.parameter], target.field, current)
                                             if target.detached_prefix
                                             else result_actual(target).all_assets
                                             if (target.kind in ('field_parameter', 'shared_field_parameter')
                                                 or target.carrier_kind in ('field_parameter', 'shared_field_parameter'))
                                             else self.projected_assets(actuals[target.parameter], target.field.rpartition('/')[0], current)
                                             if target.carrier_kind == 'detached_field_parameter'
                                             else self.projected_assets(actuals[target.parameter], target.field, current)
                                             if target.kind in ('moved_field_parameter', 'detached_field_parameter', 'mutable_vector_parameter')
                                             else dict(result_actual(target).fields).get('.' + target.field, ())
                                             if target.kind == 'indirect_field_parameter'
                                             else reference_tree_targets(actuals[target.parameter], target.field)
                                             if target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter')
                                             else actuals[target.parameter].assets))
                reservations = frozenset(a for target in targets
                                         if target.kind not in ('array_parameter', 'detached_field_parameter', 'task_capture_parameter')
                                         for a in (self.projected_assets(actuals[target.parameter], target.detached_prefix, current)
                                                   if target.detached_prefix
                                                   else result_actual(target).all_assets
                                                   if target.kind in ('field_parameter', 'shared_field_parameter')
                                                   else actuals[target.parameter].assets | actuals[target.parameter].reservations
                                                   if target.kind in ('indirect_field_parameter', 'mutable_vector_parameter')
                                                   else actuals[target.parameter].reservations))
                array_result = result.typ not in self.analyzer.enums and bool(result.reference_targets) and all(
                    target.kind in ('array_parameter', 'stored_array_parameter', 'reserved_stored_array_parameter',
                                    'inline_field_parameter', 'indirect_field_parameter')
                    or actuals[target.parameter].mode in ('array_ref', 'array_mut')
                    for target in result.reference_targets)
                if reference_array_shape(result.typ):
                    mapped = tuple((slot, frozenset(asset for target in targets
                        for asset in array_contract_assets(target, result_actual(target)))) for slot, targets in result.borrowed_fields)
                    prototype = target_row_templates(actuals, result.reference_targets) or Value('array_refs', result.typ)
                    row = rebuild_reference_tree(prototype, result.typ, mapped, result.borrowed_fields, actuals)
                    return paths, replace(row, container_borrow=True, container_mode=result.mode)
                fields = ()
                projected = []
                if result.typ in self.analyzer.enums:
                    for target in targets:
                        actual = result_actual(target)
                        if target.kind == 'parameter':
                            projected.append(actual)
                        elif target.kind == 'inline_field_parameter' and not target.carrier_kind:
                            from structure_views import project_fields
                            name = actual.storage_owner or (args[target.parameter][1]
                                if args[target.parameter][0] in ('ref', 'mut', 'name', 'reborrow') else None)
                            projected.append(replace(actual, typ=result.typ, mode=result.mode,
                                fields=project_fields(actual.fields, target.field), storage_owner=name,
                                inline_path=(actual.inline_path + '.' if actual.inline_path else '') + target.field))
                        elif target.kind in ('detached_field_parameter', 'shared_field_parameter',
                                             'moved_field_parameter', 'field_parameter'):
                            projected.append(replace(actual, fields=nested_reference_fields(actual.fields, target.field)))
                    fields = merge_fields(projected)
                handle_slot = None
                if result.vector_slot is not None:
                    parameter, index = result.vector_slot
                    vector = actuals[parameter]
                    if vector.assets:
                        handle_slot = (vector.assets, index)
                return paths, Value('array_' + result.mode if array_result else result.mode,
                                    result.typ, assets, fields, reservations=reservations, handle_slot=handle_slot,
                                    storage_owner=projected[0].storage_owner if len(projected) == 1 else None,
                                    inline_path=projected[0].inline_path if len(projected) == 1 else '',
                                    structure_choices=tuple(projected) if len(projected) > 1 and any(v.inline_path for v in projected) else ())
            if result.mode == 'array_refs':
                fields = []
                reservations = set()
                for slot, targets in result.borrowed_fields:
                    assets = set()
                    for target in targets:
                        actual = result_actual(target)
                        if not reachable_field(target, actual):
                            continue
                        if target.kind == 'moved_field_parameter':
                            assets.update(dict(actual.fields).get(target.field, ()))
                            reservations.update(actual.reservations)
                        elif target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
                            assets.update(reference_tree_targets(actual, target.field))
                        elif target.kind == 'detached_field_parameter':
                            assets.update(shared_vector_field_items(actual, target.field))
                        elif target.kind == 'indirect_field_parameter':
                            assets.update(array_contract_assets(target, actual))
                        else:
                            assets.update(actual.all_assets)
                    fields.append((slot, frozenset(assets)))
                prototype = Value('array_refs', result.typ, reservations=frozenset(reservations),
                                  container_origins=frozenset({('call', id(expr))}))
                return paths, rebuild_reference_tree(prototype, result.typ, fields, result.borrowed_fields, actuals)
            if result.mode in UTF8_BORROW_MODES or result.mode == 'vector_split':
                assets = frozenset(asset for target in result.reference_targets
                                   if isinstance(actuals[target.parameter], Value)
                                   for asset in (dict(actuals[target.parameter].fields).get(target.field, ())
                                                 if target.kind == 'task_capture_parameter'
                                                 else actuals[target.parameter].all_assets))
                return paths, Value(result.mode, result.typ, assets)
            if result.mode in ('task', 'execution'):
                assets = frozenset(self.born(('task_call', id(expr), source), source, current)
                                   for symbol in result.task_sources for source in sources(symbol))
                result_assets = frozenset(self.born(('task_call', id(expr), source), source, current)
                                          for symbol in result.task_result_sources for source in sources(symbol))
                captures = []
                for key, targets in result.borrowed_fields:
                    captured = set()
                    for target in targets:
                        actual = actuals[target.parameter]
                        if not isinstance(actual, Value):
                            continue
                        if target.kind in ('utf8_parameter', 'string_parameter', 'vector_parameter'):
                            captured.update(actual.all_assets)
                        elif target.kind in ('parameter', 'inline_field_parameter'):
                            captured.update(actual.assets | actual.reservations)
                        elif target.kind == 'indirect_field_parameter':
                            captured.update(array_contract_assets(target, actual))
                        elif target.kind in ('detached_field_parameter', 'owned_capture_field'):
                            captured.update(self.projected_assets(actual, target.field, current))
                        elif target.kind == 'task_capture_parameter':
                            captured.update(dict(actual.fields).get(target.field, ()))
                    if captured:
                        captures.append((key.partition('.')[2], frozenset(captured)))
                reservations = frozenset(asset for _, targets in captures for asset in targets)
                definition = self.analyzer.async_functions[result.typ]
                returned = getattr(definition, 'public_result_borrows', ())
                reference_assets = frozenset(asset for position, targets in captures
                                             if capture_index(position) in returned for asset in targets)
                if definition.args[2][0] in ('ref', 'mut') and not returned:
                    from async_lowering import borrowed_result_paths
                    paths_to_result = borrowed_result_paths(
                        definition, self.analyzer.async_functions, self.fail, {},
                        sync_result_contract=self.analyzer.sync_result_contract)
                    retained = set()
                    for index, path in paths_to_result:
                        for key, targets in result.borrowed_fields:
                            if capture_index(key.partition('.')[2]) != index:
                                continue
                            for target in targets:
                                actual = actuals[target.parameter]
                                if target.kind == 'task_capture_parameter':
                                    retained.update(actual.task_reference_assets)
                                elif target.kind in ('parameter', 'array_parameter', 'inline_field_parameter'):
                                    prefix = tuple(target.field.lstrip('.').split('.')) if target.field else ()
                                    retained.update(self.reference_projection_assets(actual, prefix + path))
                                else:
                                    retained.update(array_contract_assets(target, actual))
                    reference_assets = frozenset(retained)
                value = Value(result.mode, result.typ, assets, tuple(captures), reservations=reservations,
                              task_result_assets=result_assets, task_reference_assets=reference_assets,
                              task_result_fields=tuple((path, frozenset(self.born(('task_field', id(expr), source), source, current)
                                  for symbol in symbols for source in sources(symbol))) for path, symbols in result.task_result_fields))
                if result.mode == 'execution':
                    value = self.start_execution(value, ('call', id(expr)), current)
                return paths, value
            if result.mode in VALUE_MODES:
                return paths, Value(result.mode, result.typ)
            if result.mode not in ('owned', 'handle_option', 'buffered_handle_exchange', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
                return paths, SCALAR if result.mode == 'scalar' else UNKNOWN if result.mode == 'array' else VOID
            def resolve_assets(entries):
                result_sources = set()
                for candidate in entries:
                    if candidate.kind == 'task_capture':
                        result_sources.update(asset.source for asset in actuals[candidate.parameter].task_result_assets)
                    elif candidate.kind == 'parameter':
                        result_sources.update(asset.source for asset in actuals[candidate.parameter].assets)
                    elif candidate.kind == 'owned_projection':
                        result_sources.update(asset.source for asset in
                                              dict(actuals[candidate.parameter].fields).get(candidate.field_path, ()))
                    elif candidate.kind == 'exchange_parameter':
                        actual = actuals[candidate.parameter]
                        if not isinstance(actual, Value) or len(actual.exchange_payloads) != 2:
                            self.fail(line, 'argument Result non Copy attendu')
                        result_sources.update(asset.source for asset in actual.exchange_payloads[candidate.item_index])
                    elif candidate.kind == 'vector_element':
                        vector = actuals[candidate.parameter]
                        if vector.handle_items is None:
                            self.fail(line, 'provenance des éléments du vecteur inconnue pour cet appel')
                        index = candidate.item_index
                        if index == VECTOR_LAST_ITEM:
                            index = last_handle_index(vector.handle_items, candidate.excluded_items, candidate.tail_offset)
                        result_sources.update(asset.source for asset in handle_items_at(vector.handle_items, index))
                    else:
                        result_sources.update(sources(candidate.source))
                return frozenset(self.born(('call', id(expr), source), source, current) for source in result_sources)
            if result.same_parameter is not None and any(
                    field.startswith('A<') for fields in self.analyzer.enums.get(result.typ, {}).values()
                    for _, field in fields):
                return paths, actuals[result.same_parameter]
            assets = resolve_assets(result.candidates)
            fields = []
            projected_fields = {}
            for item in result.candidates:
                if item.kind == 'owned_projection':
                    for path, targets in nested_reference_fields(actuals[item.parameter].fields, item.field_path):
                        projected_fields[path] = projected_fields.get(path, frozenset()) | targets
            fields.extend(sorted(projected_fields.items()))
            def owned_fields(entries, prefix=''):
                for name, child in entries:
                    path = prefix + name
                    for candidate in child.candidates:
                        if candidate.kind == 'parameter':
                            actual = actuals[candidate.parameter]
                            yield path, actual.assets
                            yield from ((path + '/' + key, targets) for key, targets in actual.fields)
                        elif candidate.kind == 'owned_projection':
                            actual = actuals[candidate.parameter]
                            yield path, dict(actual.fields).get(candidate.field_path, frozenset())
                            yield from ((path + '/' + key, targets) for key, targets in
                                        nested_reference_fields(actual.fields, candidate.field_path))
                    fresh = frozenset(candidate for candidate in child.candidates if candidate.kind == 'fresh')
                    if fresh:
                        yield path, resolve_assets(fresh)
                        yield from owned_fields(child.owned_fields, path + '/')

            if result.owned_fields or projected_fields:
                merged = {}
                for path, children in owned_fields(result.owned_fields):
                    merged[path] = merged.get(path, frozenset()) | children
                fields.extend(sorted(merged.items()))
                contained = frozenset(child.source for _, children in fields for child in children
                                      if child.source.kind != 'local')
                for asset in assets:
                    current.vector_sources[asset] = current.vector_sources.get(asset, frozenset()) | contained
            def exchange_value(value):
                payload_assets = resolve_assets(value.candidates)
                mapped = {}
                for candidate in value.candidates:
                    if candidate.kind == 'parameter':
                        inherited = actuals[candidate.parameter].fields
                    elif candidate.kind == 'exchange_parameter':
                        inherited = nested_reference_fields(actuals[candidate.parameter].fields,
                                                            ('ok', 'err')[candidate.item_index])
                    elif candidate.kind == 'vector_element':
                        vector = actuals[candidate.parameter]
                        selected_sources = {asset.source for asset in payload_assets}
                        inherited = merge_fields(item for item in vector.handle_payloads
                                                 if any(asset.source in selected_sources for asset in item.assets))
                    else:
                        inherited = ()
                    for key, children in inherited:
                        mapped[key] = mapped.get(key, frozenset()) | children
                for key, targets in value.fields:
                    mapped[key] = frozenset(asset for target in targets for asset in (
                        actuals[target.parameter].all_assets if target.kind == 'parameter'
                        else self.projected_assets(actuals[target.parameter], target.field, current)))
                for key, children in owned_fields(value.owned_fields):
                    mapped[key] = mapped.get(key, frozenset()) | children
                for key, child in value.owned_fields:
                    nested = exchange_value(child)
                    mapped[key] = mapped.get(key, frozenset()) | nested.assets
                    for field, children in nested.fields:
                        path = key + '/' + field
                        mapped[path] = mapped.get(path, frozenset()) | children
                return Value('owned', value.typ, payload_assets, tuple(mapped.items()))
            reservations = {a for candidate in result.candidates if candidate.kind == 'parameter'
                            for a in actuals[candidate.parameter].reservations}
            for name, targets in result.borrowed_fields:
                resolved = frozenset()
                for target in targets:
                    actual = actuals[target.parameter]
                    if not reachable_field(target, actual):
                        continue
                    if target.detached_prefix:
                        resolved |= self.projected_assets(actual, target.field, current)
                        reservations.update(self.projected_assets(actual, target.detached_prefix, current))
                    elif target.kind in ('reserved_field_parameter', 'shared_field_parameter'):
                        resolved |= actual.all_assets
                        reservations.update(actual.all_assets)
                    elif target.kind == 'parameter':
                        resolved |= actual.all_assets
                        reservations.update(actual.reservations)
                    else:
                        resolved |= self.projected_assets(actual, target.field, current)
                        reservations.update(actual.reservations)
                fields.append((name, resolved))
            variant_sets = [actuals[candidate.parameter].variants if candidate.kind == 'parameter'
                            else result.fresh_variants for candidate in result.candidates]
            variants = frozenset().union(*variant_sets) if all(variant_sets) else frozenset()
            item_sets = None
            if is_handle_vector(result.typ):
                item_sets = self.apply_vector_result_candidates(result.candidates, actuals, current, id(expr))
            elif result.typ in REFERENCE_VECTORS:
                item_sets = dict(fields).get('.items', frozenset())
                if result.shared_vector_passthrough is not None:
                    item_sets = actuals[result.shared_vector_passthrough].handle_items
                elif result.shared_vector_layout is not None:
                    item_sets = tuple(frozenset(asset for target in slot for asset in (
                        self.projected_assets(actuals[target.parameter], target.field, current)
                        if target.kind == 'detached_field_parameter' else
                        array_contract_assets(target, actuals[target.parameter])))
                        for slot in result.shared_vector_layout)
            payloads = tuple(exchange_value(value) for value in (*result.exchange_values, *result.vector_values) if value.candidates)
            if is_handle_vector(result.typ):
                active_items = possible_handle_items(item_sets) or frozenset()
                payloads = tuple(replace(value, assets=frozenset(asset for asset in active_items
                    if any(asset.source == original.source for original in value.assets))) for value in payloads)
            return paths, Value(result.mode, result.typ, assets, tuple(fields), frozenset(reservations),
                                handle_payloads=payloads,
                                exchange_payloads=tuple(resolve_assets(arm) for arm in result.exchange_payloads),
                                exchange_values=tuple(exchange_value(value) for value in result.exchange_values),
                                variants=variants, handle_items=item_sets,
                                absent_owned_payload=not assets and (result.mode == 'handle_option' or result.absent_owned_payload or
                                    bool(result.candidates) and all(candidate.kind == 'parameter'
                                        and actuals[candidate.parameter].absent_owned_payload
                                        for candidate in result.candidates)))
        finally:
            self.pending_sources.pop()

    def apply_vector_result_candidates(self, candidates, actuals, current, site):
        vectors = []
        for candidate in candidates:
            vector = (actuals[candidate.parameter] if candidate.kind == 'parameter'
                      else Value('owned', HANDLE_VECTOR, handle_items=()))
            if candidate.kind == 'task_capture':
                vector = Value('owned', HANDLE_VECTOR, handle_items=dict(
                    actuals[candidate.parameter].task_result_fields).get('[]', frozenset()))
            items = remaining_handle_items(vector.handle_items, candidate.vector_removals)
            if (candidate.vector_removals == UNKNOWN_VECTOR_REMOVALS and items is not None
                    and not (candidate.vector_layout or candidate.vector_replacements)
                    and (candidate.vector_added_parameters or candidate.vector_added_pools
                         or candidate.vector_added_elements)):
                items |= frozenset(asset for index in candidate.vector_added_parameters
                                   for asset in actuals[index].assets)
                fresh = frozenset(self.born(('vector_call', site, source), source, current)
                                  for source in (actuals[index] for index in candidate.vector_added_pools))
                items |= fresh
                self.retain_handle_origin(Value('owned', 'Int', fresh), current)
                for added in candidate.vector_added_elements:
                    donor_items = actuals[added.parameter].handle_items
                    if donor_items is None:
                        items = None
                        break
                    index = added.item_index
                    if index == VECTOR_LAST_ITEM:
                        index = last_handle_index(donor_items, added.excluded_items, added.tail_offset)
                    items |= handle_items_at(donor_items, index)
            if candidate.vector_layout or candidate.vector_replacements:
                rows = []
                for slot in (*[slot for _, slot in candidate.vector_replacements], *candidate.vector_layout):
                    slot_assets = set()
                    for item in slot:
                        if item.kind == 'parameter':
                            slot_assets.update(actuals[item.parameter].assets)
                        elif item.kind == 'fresh':
                            source = actuals[item.source.index]
                            asset = self.born(('vector_call', site, source), source, current)
                            slot_assets.add(asset)
                            self.retain_handle_origin(Value('owned', 'Int', frozenset({asset})), current)
                        else:
                            donor = actuals[item.parameter].handle_items
                            index = item.item_index
                            if index == VECTOR_LAST_ITEM:
                                index = last_handle_index(donor, item.excluded_items, item.tail_offset)
                            assets_from_donor = handle_items_at(donor, index)
                            if assets_from_donor is None:
                                rows = None
                                break
                            slot_assets.update(assets_from_donor)
                    if rows is None:
                        break
                    rows.append(frozenset(slot_assets))
                if rows is None:
                    items = None
                elif candidate.kind == 'fresh':
                    items = tuple(rows)
                elif isinstance(items, tuple):
                    count = len(candidate.vector_replacements)
                    replacements = zip((index for index, _ in candidate.vector_replacements), rows[:count])
                    items = replace_handle_positions(items, replacements) + tuple(rows[count:])
                elif items is not None:
                    items |= frozenset().union(*rows)
            vectors.append(replace(vector, handle_items=items))
        return merge_handle_items(vectors)

    def loop(self, node, state, valued=False, expected_array=None):
        self.valued_loops.append((valued, expected_array))
        try:
            return self.loop_paths(node, state)
        finally:
            self.valued_loops.pop()

    def loop_paths(self, node, state):
        initial, head = state.clone(), state.clone()
        # External assets persist, local temporaries are pruned at each iteration.
        limit = (len(state.history) + 1) * (len(self.params) + 2) + 3
        for _ in range(limit):
            outcomes, _ = self.block(node.args[0], head.clone())
            edges = [outcomes[k] for k in ('next', 'continue') if k in outcomes]
            if not edges:
                break
            following = join_states([initial, *edges])
            if (following.history == head.history and following.environment == head.environment
                    and following.inserted_sources == head.inserted_sources
                    and following.vector_sources == head.vector_sources
                    and following.pending_executions == head.pending_executions):
                break
            head = following
        else:
            self.fail(node.line, 'prototype : contraintes de boucle sans convergence')
        paths = {}
        if 'return' in outcomes:
            paths['return'] = outcomes['return']
        value = UNKNOWN
        if 'break' in outcomes:
            exit_state = outcomes['break']
            values = exit_state.break_values
            if values:
                if any(value.mode == 'vector_split' for value in values):
                    signatures = {(value.mode, value.typ) for value in values}
                    if len(signatures) != 1:
                        self.fail(node.line, 'break : même type et même mode requis sur toutes les sorties')
                value = join_values(self.unify_handle_values(values))
            exit_state.break_values = frozenset()
            paths['next'] = exit_state
        return paths, value

    def nodes(self, nodes, state, valued=False, expected_array=None):
        paths, tail = {'next': state}, UNKNOWN
        for index, node in enumerate(nodes):
            if 'next' not in paths:
                break
            current = paths.pop('next')
            op, args, line = node.op, node.args, node.line
            if op == 'call' and args[0][0] == 'method_call':
                carrier = current.environment.get(args[0][1][1])
                structure = isinstance(carrier, Value) and '' in self.analyzer.enums.get(carrier.typ, {})
                builtin = builtin_method_statement(args[0], structure, lambda message: self.fail(line, message))
                if builtin is not None:
                    op, args = builtin
            following = {'next': current}
            if op == 'set_expr':
                target = self.lookup(args[0], current, line)
                following, _ = self.expression(args[1], current, line)
                if 'next' in following:
                    self.touch(target, following['next'], line)
            elif op in ('var', 'assign'):
                name, expr = args
                if expr[0] == 'source':
                    if op == 'var':
                        current.shadow(name)
                    current.environment[name] = Source('local', id(node), name,
                                                       expr[3] if expr[1] == 'pool' else None)
                else:
                    previous = current.environment.get(args[0])
                    expected = node.annotation
                    if (op == 'assign' and isinstance(previous, Value) and previous.mode in ('array', 'array_refs')
                            and not previous.container_borrow):
                        expected = previous.typ
                    following, value = self.expression(args[1], current, line, expected)
                    if 'next' in following:
                        continuing = following['next']
                        if node.annotation and (hook := getattr(self.analyzer, 'storage_annotation_hook', None)):
                            hook(self, value, node.annotation, line)
                        annotation = fixed_array_shape(node.annotation) if node.annotation else None
                        if annotation and annotation[0] == 'u8' and isinstance(value, Value) and value.mode == 'array':
                            value = replace(value, typ=node.annotation)
                        if op == 'var':
                            continuing.shadow(args[0])
                        if (op == 'assign' and isinstance(previous, Value) and previous.mode == 'array_refs' and not previous.container_borrow
                                and isinstance(value, Value) and value.mode == 'array_refs'):
                            update_array_aliases(continuing.environment, args[0], value.fields)
                            paths = merge_paths(paths, following)
                            continue
                        replacing_owned = (op == 'assign' and isinstance(previous, Value)
                                           and previous.mode == 'owned' and isinstance(value, Value))
                        if replacing_owned and value.mode in MODE_TYPES:
                            self.touch(previous, continuing, line)
                        else:
                            if replacing_owned and value.mode == 'owned':
                                # A reset later on this path cannot affect the destroyed candidates.
                                for asset in previous.assets - value.assets:
                                    continuing.history.pop(asset, None)
                            continuing.environment[args[0]] = value
            elif op == 'reset':
                self.reset(self.source(args[0], current, line), current, line)
            elif op in ('print', 'address', 'set', 'drop_value', '<-', '->'):
                value = self.lookup(args[0], current, line)
                self.touch(value, current, line)
                if op == '->':
                    current.shadow(args[0])
                if (op == 'drop_value' and isinstance(value, Value) and is_handle_vector(value.typ)
                        and value.mode == 'owned' and len(value.assets) == 1):
                    asset = next(iter(value.assets))
                    aliases = [other for name, other in current.environment.items() if name != args[0]]
                    aliases.extend(other for shadow in current.shadows for other in shadow.values())
                    if not any(isinstance(other, Value) and asset in other.assets for other in aliases):
                        current.vector_sources.pop(asset, None)
                if valued and op == '<-' and not node.terminated and index == len(nodes) - 1:
                    tail = value
            elif op == 'drop':
                source = self.source(args[0], current, line)
                self.use_source(source, True, line)
                value = self.lookup(args[1], current, line)
                self.touch(value, current, line)
                if isinstance(value, Value):
                    for asset in value.assets:
                        self.require('equal', asset.source, source, line, 'drop')
            elif op == 'scope':
                following, _ = self.block(args[1], current)
            elif op == 'if':
                following = self.condition(args[0], current, line)
                if 'next' in following:
                    entry = following.pop('next')
                    if self.absent_option_success(args[0], entry):
                        no, _ = self.block(args[2], entry)
                        paths = merge_paths(paths, following, no)
                        continue
                    yes_entry, no_entry = entry.clone(), entry.clone()
                    self.refine_handle_branches(args[0], yes_entry, no_entry)
                    yes, _ = self.block(args[1], yes_entry)
                    no, _ = self.block(args[2], no_entry)
                    following = merge_paths(following, yes, no)
            elif op == 'while_check':
                following = self.condition(args[0], current, line)
                if 'next' in following:
                    entry = following.pop('next')
                    following = merge_paths(following, {'next': entry.clone(), 'break': entry.clone()})
            elif op in ('loop', 'while'):
                following, _ = self.loop(node, current)
            elif op == 'break':
                valued_break, expected = self.valued_loops[-1] if self.valued_loops else (False, None)
                following, value = self.expression(args[0], current, line, expected)
                if 'next' in following:
                    exiting = following.pop('next')
                    if valued_break and isinstance(value, Value):
                        exiting.break_values = frozenset({value})
                    following = merge_paths(following, {'break': exiting})
            elif op == 'continue':
                following = {'continue': current}
            elif op == 'if_yield':
                following, tail = self.expression(args[0], current, line, expected_array)
            elif op == 'match_yield' and valued:
                tail = self.lookup(args[0], current, line)
                self.touch(tail, current, line)
            elif op == 'return':
                mode, typ = self.node.args[2]
                following, value = self.expression(args[0], current, line, typ if mode in ('array', 'array_refs') else None)
                if mode == 'owned' and (hook := getattr(self.analyzer, 'storage_annotation_hook', None)):
                    hook(self, value, f'A<{typ}>' if self.node.handle_result else typ, line)
                if mode == 'execution' and (hook := getattr(self.analyzer, 'storage_annotation_hook', None)):
                    hook(self, value, typ, line)
                if 'next' in following:
                    returning = following.pop('next')
                    following = merge_paths(following, {'return': returning})
            elif op == 'call':
                following, _ = self.expression(args[0], current, line)
            elif (op in ('array_store', 'array_deref_store')
                  and reference_array_variable(args[0], current.environment) is not None):
                following = self.store_reference_array(args[0], args[1], current, line)
            elif op in ('array_store', 'array_deref_store'):
                place = args[0][1] if args[0][0] == 'array_deref_slot' else args[0]
                following, target = self.expression(place, current, line)
                if 'next' in following:
                    right, incoming = self.expression(args[1], following.pop('next'), line)
                    following = merge_paths(following, right)
                    if 'next' in following:
                        continued = following['next']
                        self.touch(target, continued, line, place=True)
                        if (op == 'array_deref_store' and place[0] == 'name'
                                and isinstance(target, Value) and target.typ.startswith('A<')
                                and isinstance(incoming, Value)):
                            if target.storage_owner is None:
                                self.retain_handle_origin(incoming, continued)
                                self.store_handle_slot(continued, target, incoming)
                            else:
                                self.update_handle(continued, target, incoming)
            elif op == 'field_store':
                place, rhs = args
                target = self.lookup(place[1], current, line)
                self.touch(target, current, line)
                following, value = self.expression(rhs, current, line)
                if 'next' in following:
                    continued = following['next']
                    target = self.lookup(place[1], continued, line)
                    self.touch(target, continued, line)
                    typ = dict(self.analyzer.enums.get(target.typ, {}).get('', ())).get(place[2]) if isinstance(target, Value) else None
                    capability = reference_type(typ) if typ is not None else None
                    if typ and typ.startswith('A<'):
                        self.retain_handle_origin(value, continued, target)
                    if capability and isinstance(value, Value) and (value.mode, value.typ) == capability:
                        if target.mode == 'mut':
                            self.touch(value, continued, line)
                            self.retain_handle_origin(value, continued)
                        key = '.' + place[2]
                        changes = {key + '/' + path: frozenset()
                                   for path, _ in nested_reference_fields(target.fields, key)}
                        changes.update((key + '/' + path, assets) for path, assets in value.fields)
                        changes[key] = value.all_assets
                        self.update_structure(continued, place[1], target, changes, line)
            elif op in ARRAY_STATEMENTS or op == 'print_expr':
                for expr in args:
                    if 'next' not in following:
                        break
                    part, _ = self.expression(expr, following.pop('next'), line)
                    following = merge_paths(following, part)
            elif op == 'match':
                self.touch(self.lookup(args[0], current, line), current, line)
                following = {}
                values = []
                subject = self.lookup(args[0], current, line)
                if node.consuming and isinstance(subject, Value):
                    for asset in subject.assets:
                        current.vector_sources.pop(asset, None)
                variants = subject.variants if isinstance(subject, Value) else frozenset()
                explicit = {arm for _, arm, _, _ in args[1] if arm is not None}
                for arm_type, arm, fields, body in args[1]:
                    if variants and (arm not in variants if arm is not None else variants <= explicit):
                        continue
                    bindings = {name: SCALAR for _, name in fields if name != '_'}
                    declarations = dict(self.analyzer.enums.get(arm_type, {}).get(arm, ()))
                    for field_name, name in fields:
                        declared = declarations.get(field_name, '')
                        if name != '_' and (mode := scalar_field_mode(declared)) is not None:
                            bindings[name] = Value(mode, declared)
                        capability = reference_type(declared)
                        if name != '_' and declared.startswith('A<') and isinstance(subject, Value):
                            key = f'{arm}.{field_name}'
                            mode = 'owned' if node.consuming else 'mut' if node.mutable else 'ref'
                            bindings[name] = Value(mode, declared[2:-1], dict(subject.fields).get(key, frozenset()),
                                                   nested_reference_fields(subject.fields, key), subject.reservations)
                        if name != '_' and capability and isinstance(subject, Value):
                            mode = 'mut' if (node.mutable or node.consuming) and capability[0] == 'mut' else 'ref'
                            reservations = subject.reservations if node.consuming else subject.all_assets
                            key = f'{arm}.{field_name}'
                            bindings[name] = Value(mode, capability[1], dict(subject.fields).get(key, frozenset()),
                                                   nested_reference_fields(subject.fields, key), reservations)
                    arm, value = self.block(body, current, valued=valued, bindings=bindings,
                                            expected_array=expected_array)
                    if valued and 'next' in arm and isinstance(value, Value):
                        values.append(value)
                    following = merge_paths(following, arm)
                if values:
                    tail = join_values(self.unify_handle_values(values))
            paths = merge_paths(paths, following)
        return paths, tail

    def update_structure(self, state, name, carrier, changes, line):
        if (carrier.mode == 'mut' and carrier.storage_owner and carrier.assets
                and not carrier.inline_path and not carrier.owned_path):
            owner = state.environment.get(carrier.storage_owner)
            if not carrier.assets & getattr(owner, 'assets', frozenset()):
                carrier = replace(carrier, storage_owner=None)
        if carrier.inline_path and not carrier.structure_choices:
            owner = self.lookup(carrier.storage_owner, state, line)
            from structure_views import prefix_fields, project_fields
            self.update_structure(state, carrier.storage_owner, owner,
                                  dict(prefix_fields(changes.items(), carrier.inline_path)), line)
            fields = project_fields(state.environment[carrier.storage_owner].fields, carrier.inline_path)
            state.environment[name] = replace(carrier, fields=fields)
            return dict(fields)
        if carrier.structure_choices:
            branches = []
            for choice in carrier.structure_choices:
                branch = state.clone()
                self.update_structure(branch, name, choice, changes, line)
                branches.append(branch)
            merged = join_states(branches)
            state.environment.update(merged.environment)
            state.shadows = merged.shadows
            return dict(state.environment[name].fields)
        if carrier.mode == 'mut' and carrier.storage_owner is None:
            borrowed = frozenset(asset for asset in carrier.assets
                                 if asset.token[0] == 'parameter' and self.params[asset.token[1]][1] == 'mut')
            indices = {asset.token[1] for asset in borrowed}
            local = carrier.assets - borrowed
            if local:
                mapped = update_local_structure_locations(state.environment, local, changes,
                                                          lambda value: getattr(value, 'assets', frozenset()), state.shadows)
            else:
                mapped = bool(indices)
            if indices:
                mapped = mapped and update_structure_parameters(state.environment, indices, changes,
                                                                conditional=bool(local))
            if not mapped:
                self.fail(line, 'prototype : mise à jour indirecte de porteurs par contrat')
        fields = dict(carrier.fields) | changes
        state.environment[name] = replace(carrier, fields=tuple(fields.items()))
        owner = state.environment.get(carrier.storage_owner)
        if carrier.owned_path and isinstance(owner, Value):
            prefix = '/'.join(carrier.owned_path) + '/'
            updated = dict(owner.fields) | {prefix + field: assets for field, assets in changes.items()}
            state.environment[carrier.storage_owner] = replace(owner, fields=tuple(updated.items()))
            return fields
        if isinstance(owner, Value):
            state.environment[carrier.storage_owner] = replace(owner, fields=tuple(fields.items()))
            original = state.environment.get(owner.storage_owner)
            if isinstance(original, Value):
                state.environment[owner.storage_owner] = replace(original, fields=tuple(fields.items()))
        return fields
