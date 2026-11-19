"""AST traversal shared by the checker and its contract analyses."""

import re
from dataclasses import replace

ARRAY_STATEMENTS = ('array_store', 'array_deref_store', 'array_statement', 'print_expr')


VECTOR_ELEMENTS = {'Vector<Int>': 'Int', 'Vector<u8>': 'u8'}
HANDLE_VECTOR = 'Vector<A<Int>>'
SHARED_REF_VECTOR = 'Vector<&Int>'
MUT_REF_VECTOR = 'Vector<&mut Int>'
REFERENCE_VECTORS = (SHARED_REF_VECTOR, MUT_REF_VECTOR)
HANDLE_VECTORS = {HANDLE_VECTOR: 'Int'}
INLINE_VECTOR_ELEMENTS = {}
VECTOR_TYPES = dict.fromkeys((*VECTOR_ELEMENTS, HANDLE_VECTOR, *REFERENCE_VECTORS))


def is_handle_vector(typ):
    return isinstance(typ, str) and typ.startswith('Vector<A<') and typ.endswith('>>')


def handle_vector_element(typ):
    return typ[len('Vector<A<'):-2] if is_handle_vector(typ) else None


def is_payload_vector(typ):
    return is_handle_vector(typ) or typ in INLINE_VECTOR_ELEMENTS


def vector_payload_element(typ):
    return INLINE_VECTOR_ELEMENTS.get(typ) or handle_vector_element(typ)


def register_handle_vector(typ):
    if is_handle_vector(typ):
        HANDLE_VECTORS[typ] = handle_vector_element(typ)
        VECTOR_TYPES[typ] = None
    return typ


def register_vector_type(typ):
    register_handle_vector(typ)
    if typ.startswith('Vector<') and typ.endswith('>') and typ not in VECTOR_TYPES:
        element = typ[7:-1]
        if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9:]*', element):
            INLINE_VECTOR_ELEMENTS[typ] = element
            VECTOR_TYPES[typ] = None
    return typ

VECTOR_METHODS = {
    'len': ('array_vector_len', 0),
    'try_push': ('array_vector_try_push', 1),
    'try_extend': ('array_vector_try_extend', 1),
    'read_fd': ('array_vector_read_fd', 1),
    'push': ('array_vector_push', 1),
    'remove': ('array_vector_remove', 1),
    'replace': ('array_vector_replace', 2),
    'push_new': ('array_vector_push_new', 0),
    'pop': ('array_vector_pop', 0),
}


def vector_method(typ, method):
    if typ in INLINE_VECTOR_ELEMENTS:
        return VECTOR_METHODS.get(method)
    if typ in (*HANDLE_VECTORS, MUT_REF_VECTOR):
        return VECTOR_METHODS.get(method) if method in ('len', 'push', 'remove') else None
    if typ == SHARED_REF_VECTOR:
        return VECTOR_METHODS.get(method) if method in ('len', 'push', 'remove', 'pop', 'replace', 'try_push') else None
    if method in ('try_extend', 'read_fd') and typ != 'Vector<u8>':
        return None
    return VECTOR_METHODS.get(method) if typ in VECTOR_ELEMENTS else None


def consumed_result_expression(expr, nominal):
    """Resolve the explicit -> inside drop without adding moves to ordinary calls."""
    if (expr[0] == 'method_call' and expr[1][0] == 'name' and nominal in INLINE_VECTOR_ELEMENTS
            and expr[2] in ('remove', 'pop')):
        return ('array_transfer', expr) if expr[2] == 'remove' else ('array_handle_option_pop', expr[1])
    if expr[0] == 'method_call' and expr[1][0] == 'name' and nominal in (*HANDLE_VECTORS, MUT_REF_VECTOR):
        if expr[2] == 'remove':
            return ('array_transfer', expr)
        operation = {('pop', 0): 'array_handle_option_pop',
                     ('try_push', 1): 'array_buffered_try_push'}.get((expr[2], len(expr[3])))
        if operation is not None:
            return (operation, expr[1], *expr[3])
    return expr


def array_operands(expr):
    if expr[0] == 'array_hashmap_new':
        return ()
    if expr[0] == 'array_hashmap_method':
        return expr[2:]
    if expr[0] in ('array_mutex_new', 'array_mutex_lock', 'array_mutex_acquire'):
        return expr[2:]
    if expr[0] == 'array_ffi_call':
        return expr[3:]
    if expr[0] == 'array_scheduler_resolve':
        return expr[2:]
    if expr[0] == 'array_numeric_compound':
        return expr[1], expr[3]
    if expr[0] == 'array_numeric_literal':
        return ()
    if expr[0] == 'array_numeric_operation':
        return expr[3:]
    if expr[0] == 'array_numeric_cast':
        return expr[2:]
    if expr[0] == 'array_numeric_try_from':
        return expr[2:]
    if expr[0] == 'array_integer_cast':
        return expr[1:2]
    if expr[0] in ('array_input', 'array_borrow_input', 'array_stored_input'):
        return ()
    if expr[0] == 'array_repeat':
        return expr[1:2]
    return expr[1:]


def fixed_array_shape(typ):
    match = re.fullmatch(r'\[(.+);(\d+)\]', typ)
    return (match[1], int(match[2])) if match else None


def nested_reference_fields(fields, key):
    prefix = key + '/'
    return tuple((path[len(prefix):], targets) for path, targets in fields if path.startswith(prefix))


def aggregate_reference_paths(enums, typ, prefix=''):
    """Enumerate a finite signature's reference paths, with parents first."""
    for arm, fields in enums.get(typ, {}).items():
        for field, declared in fields:
            capability = reference_type(declared)
            if capability is None:
                continue
            _, pointee = capability
            path = f'{prefix}{arm}.{field}'
            yield path, pointee
            yield from aggregate_reference_paths(enums, pointee, path + '/')


def aggregate_owned_paths(enums, typ, prefix='', visited=frozenset()):
    """Enumerate fields up to the first repeated type on each path."""
    if typ in visited:
        return
    for arm, fields in enums.get(typ, {}).items():
        for field, declared in fields:
            if declared.startswith('A<'):
                pointee = declared[2:-1]
                path = f'{prefix}{arm}.{field}'
                yield path, pointee
                yield from aggregate_owned_paths(enums, pointee, path + '/', visited | {typ})


def owned_reference_paths(enums, typ, prefix='', visited=frozenset()):
    """Borrowed fields reachable through owned edges, preserving each path."""
    if typ in visited:
        return
    if (element := vector_payload_element(typ)) is not None:
        yield from owned_reference_paths(enums, element, prefix + '[]/', visited | {typ})
        return
    for arm, fields in enums.get(typ, {}).items():
        for field, declared in fields:
            path = f'{prefix}{arm}.{field}'
            if (capability := reference_type(declared)) is not None:
                yield path, capability[0], capability[1]
            elif declared.startswith('A<'):
                yield from owned_reference_paths(enums, declared[2:-1], path + '/', visited | {typ})


def reference_type(typ):
    if typ.startswith('&mut '):
        return 'mut', typ[5:]
    if typ.startswith('&'):
        return 'ref', typ[1:]
    return None


def reference_array_element(typ):
    while fixed_array_shape(typ):
        typ = fixed_array_shape(typ)[0]
    return reference_type(typ)


def reference_array_shape(typ):
    shape = fixed_array_shape(typ)
    if shape is None:
        return None
    element, length = shape
    if reference_type(element):
        return reference_type(element)[0], length
    nested = reference_array_shape(element)
    return (nested[0], length * nested[1]) if nested else None


def borrowed_array_name(argument):
    if argument[0] in ('name', 'mut', 'reborrow', 'down'):
        return argument[1]
    if argument[0] in ('array_mut_ref', 'array_ref', 'ref_expr', 'mut_expr'):
        return reference_array_path(argument[1])[0]
    return None


def update_structure_parameters(environment, indices, changes, *, conditional=False):
    keys = {f'\0structure:{index}' for index in indices}
    if not keys or not keys <= environment.keys():
        return False
    for name, value in environment.items():
        if name not in keys and getattr(value, 'storage_owner', None) not in keys:
            continue
        fields = dict(value.fields)
        from structure_views import project_fields
        incoming = (project_fields(changes.items(), value.inline_path)
                    if getattr(value, 'inline_path', '') else changes.items())
        for field, targets in incoming:
            fields[field] = (fields.get(field, frozenset()) | targets
                             if conditional or len(keys) > 1 else targets)
        environment[name] = replace(value, fields=tuple(fields.items()))
    return True


def update_local_structure_locations(environment, locations, changes, identify, shadow_scopes):
    # A construction site can stand for several allocations across iterations.
    # Keep each old target until the concrete checker can identify the holder.
    if not locations:
        return False
    owners = [(scope, name, value) for scope in (environment, *shadow_scopes)
              for name, value in scope.items()
              if getattr(value, 'mode', None) == 'owned' and locations & identify(value)]
    if not locations <= frozenset(location for _, _, value in owners for location in identify(value)):
        return False
    for scope, name, value in owners:
        fields = dict(value.fields)
        for field, targets in changes.items():
            fields[field] = fields.get(field, frozenset()) | targets
        scope[name] = replace(value, fields=tuple(fields.items()))
    return True


def array_container_positions(value):
    return value.container_positions or tuple((slot,) for slot in range(len(value.fields)))


def project_reference_array(value, typ, groups):
    previous = dict(value.fields)
    positions = array_container_positions(value)
    fields = tuple((str(slot), frozenset(target for index in group
                                        for target in previous.get(str(index), ())))
                   for slot, group in enumerate(groups))
    projected = tuple(tuple(sorted({position for index in group for position in positions[index]}))
                      for group in groups)
    source_rows = dict(value.rows)
    rows = tuple((str(slot), merge_reference_values([source_rows[str(index)] for index in group]))
                 for slot, group in enumerate(groups) if group and all(str(index) in source_rows for index in group))
    return replace(value, typ=typ, fields=fields, container_positions=projected, rows=rows)


def merge_container_positions(values):
    if any(getattr(value, 'mode', None) != 'array_refs' for value in values):
        return ()
    projections = [array_container_positions(value) for value in values]
    if projections and any(len(projection) != len(projections[0]) for projection in projections):
        return ()
    return tuple(tuple(sorted({position for projection in projections for position in projection[slot]}))
                 for slot in range(len(projections[0]))) if projections else ()


def patch_reference_fields(target, source, fields, changed_only):
    updated = dict(target.fields)
    original = dict(source.fields)
    source_positions = array_container_positions(source)
    target_positions = array_container_positions(target)
    same_origin = (len(source.container_origins) == 1
                   and source.container_origins == target.container_origins)
    for slot, incoming in fields:
        if changed_only and incoming == original.get(slot, frozenset()):
            continue
        positions = source_positions[int(slot)]
        for index, destinations in enumerate(target_positions):
            if set(positions).isdisjoint(destinations):
                continue
            exact = same_origin and len(positions) == len(destinations) == 1
            updated[str(index)] = incoming if exact else updated.get(str(index), frozenset()) | incoming
    return tuple(sorted(updated.items()))


def update_array_aliases(environment, name, fields, source=None, rows=None):
    previous = source if source is not None else environment[name]
    incoming = unflatten_reference_value(previous, fields)
    if rows is not None:
        incoming = replace(incoming, rows=tuple(rows))
    updates = []

    def collect(before, after):
        updates.append((before, after))
        old = dict(before.rows)
        for slot, row in after.rows:
            if slot in old and old[slot].container_origins & row.container_origins:
                collect(old[slot], row)
    collect(previous, incoming)

    def patch(value):
        if not hasattr(value, 'rows'):
            return value
        value = replace(value, rows=tuple((slot, patch(row)) for slot, row in value.rows))
        for before, after in updates:
            if not value.container_origins & before.container_origins:
                continue
            fields = patch_reference_fields(value, before, after.fields, True)
            child_rows = dict(value.rows)
            before_positions = array_container_positions(before)
            positions = array_container_positions(value)
            for slot, row in after.rows:
                if dict(before.rows).get(slot) == row:
                    continue
                for index, destinations in enumerate(positions):
                    if set(before_positions[int(slot)]).isdisjoint(destinations):
                        continue
                    exact = (value.container_origins == before.container_origins
                             and len(value.container_origins) == 1
                             and len(before_positions[int(slot)]) == len(destinations) == 1)
                    key = str(index)
                    child_rows[key] = row if exact or key not in child_rows else merge_reference_values([child_rows[key], row])
            value = replace(value, fields=fields, rows=tuple(sorted(child_rows.items())))
        return value
    for alias, value in list(environment.items()):
        if alias == name and source is None:
            environment[alias] = incoming
        else:
            environment[alias] = patch(value)


def restore_array_binding(value, environment):
    candidates = []
    def visit(candidate):
        if not hasattr(candidate, 'rows'):
            return
        candidates.append(candidate)
        for _, row in candidate.rows:
            visit(row)
    for candidate in environment.values():
        visit(candidate)

    def restore(current):
        if not hasattr(current, 'rows'):
            return current
        result = current
        for candidate in candidates:
            if not result.container_origins & candidate.container_origins:
                continue
            fields = patch_reference_fields(result, candidate, candidate.fields, False)
            rows = dict(result.rows)
            positions = array_container_positions(result)
            for slot, row in candidate.rows:
                source = array_container_positions(candidate)[int(slot)]
                for index, destinations in enumerate(positions):
                    if set(source).isdisjoint(destinations):
                        continue
                    exact = (len(result.container_origins) == 1
                             and result.container_origins == candidate.container_origins
                             and len(source) == len(destinations) == 1)
                    key = str(index)
                    rows[key] = row if exact or key not in rows else merge_reference_values([rows[key], row])
            result = replace(result, fields=fields, rows=tuple(sorted(rows.items())))
        return replace(result, rows=tuple((slot, restore(row)) for slot, row in result.rows))
    return restore(value)


def reference_array_projection(typ, indices):
    starts = (0,)
    for index in indices:
        element, length = fixed_array_shape(typ)
        nested = reference_array_shape(element)
        stride = nested[1] if nested else 1
        selected = (index[1],) if index[0] == 'int' else range(length)
        starts = tuple(start + slot * stride for start in starts for slot in selected)
        typ = element
    nested = reference_array_shape(typ)
    width = nested[1] if nested else 1
    return typ, tuple(tuple(start + slot for start in starts) for slot in range(width))


def reference_array_path(expr):
    indices = []
    while expr[0] == 'array_index':
        indices.append(expr[2])
        expr = expr[1]
    return (expr[1], tuple(reversed(indices))) if expr[0] == 'name' else (None, ())


def replace_reference_fields(fields, positions, replacement):
    previous = dict(fields)
    updated = previous.copy()
    old = tuple((str(slot), frozenset(target for index in indices
                                     for target in previous.get(str(index), ())))
                for slot, indices in enumerate(positions))
    for slot, indices in enumerate(positions):
        for index in indices:
            value = replacement[slot]
            updated[str(index)] = value if len(indices) == 1 else previous.get(str(index), frozenset()) | value
    return old, tuple(sorted(updated.items()))


def swap_reference_fields(fields, typ, prefix, first, second):
    receiver, groups = reference_array_projection(typ, prefix)
    element, length = fixed_array_shape(receiver)
    nested = reference_array_shape(element)
    stride = nested[1] if nested else 1
    previous = dict(fields)
    updated = previous.copy()
    if not groups:
        return tuple(sorted(updated.items()))
    starts = groups[0]
    left = (first[1],) if first[0] == 'int' else tuple(range(length))
    right = (second[1],) if second[0] == 'int' else tuple(range(length))
    for start in starts:
        for row in set(left) | set(right):
            possible = set(right if row in left else ()) | set(left if row in right else ())
            if len(starts) > 1 or (left != (row,) and right != (row,)):
                possible.add(row)
            for column in range(stride):
                position = start + row * stride + column
                updated[str(position)] = frozenset(
                    target for source in possible
                    for target in previous.get(str(start + source * stride + column), ()))
    return tuple(sorted(updated.items()))


def reference_array_variable(expr, environment):
    name, indices = reference_array_path(expr)
    value = environment.get(name)
    if getattr(value, 'mode', None) != 'array_refs':
        return None
    typ = value.typ
    for _ in indices:
        if reference_type(typ):
            typ = reference_type(typ)[1]
        shape = fixed_array_shape(typ)
        if shape is None or not reference_array_shape(typ):
            return None
        typ = shape[0]
    return name


def reference_tree_fields(value, prefix=''):
    for slot, targets in getattr(value, 'fields', ()):
        yield prefix + slot, targets
    for slot, row in getattr(value, 'rows', ()):
        yield from reference_tree_fields(row, prefix + slot + '/')


def reference_tree_slot(value, path):
    slots = path.split('/')
    for slot in slots[:-1]:
        value = dict(value.rows)[slot]
    return value, slots[-1]


def reference_tree_targets(value, path):
    holder, slot = reference_tree_slot(value, path)
    return dict(holder.fields).get(slot, frozenset())


def merge_exchange_payloads(values):
    return tuple(frozenset().union(*arm) for arm in zip(*(value.exchange_payloads for value in values)))


def merge_exchange_values(values):
    if not values or not all(getattr(value, 'exchange_values', ()) for value in values):
        return ()
    return tuple((merge_owned_values(arms) if hasattr(arms[0], "candidates") else merge_reference_values(arms))
                 for arms in zip(*(value.exchange_values for value in values)))


def merge_structure_choices(values):
    """Preserve alternative borrowed places, including a whole-object arm."""
    if not any(getattr(value, 'structure_choices', ()) or getattr(value, 'owned_path', ()) or getattr(value, 'inline_path', '')
               for value in values):
        return ()
    return tuple(dict.fromkeys(choice for value in values
                               for choice in getattr(value, 'structure_choices', ()) or (value,)))


def merge_reference_values(values):
    first = values[0]
    changes = {}
    for attribute in ('candidates', 'fresh_variants', 'reference_targets', 'container_origins',
                      'structure_origins', 'copy_candidates', 'assets', 'reservations',
                      'task_sources', 'task_result_sources', 'task_result_assets', 'pending_structure_calls', 'task_parameters', 'deferred_field_updates'):
        if hasattr(first, attribute):
            changes[attribute] = frozenset(item for value in values for item in getattr(value, attribute))
    fields = {}
    for value in values:
        for slot, targets in value.fields:
            fields[slot] = fields.get(slot, frozenset()) | targets
    changes['fields'] = tuple(sorted(fields.items()))
    changes['rows'] = merge_reference_rows(values)
    if hasattr(first, 'owned_fields'):
        changes['owned_fields'] = merge_reference_rows(values, 'owned_fields')
    changes['container_positions'] = merge_container_positions(values)
    if hasattr(first, 'exchange_payloads'):
        changes['exchange_payloads'] = merge_exchange_payloads(values)
        changes['exchange_values'] = merge_exchange_values(values)
    if hasattr(first, 'handle_payloads'):
        changes['handle_payloads'] = tuple(dict.fromkeys(item for value in values for item in value.handle_payloads))
    if hasattr(first, 'absent_owned_payload'):
        changes['absent_owned_payload'] = all(value.absent_owned_payload for value in values)
    if hasattr(first, 'structure_choices'):
        changes['structure_choices'] = merge_structure_choices(values)
    return replace(first, **changes)


def merge_reference_rows(values, attribute='rows'):
    rows = {}
    for value in values:
        for slot, row in getattr(value, attribute, ()):
            rows.setdefault(slot, []).append(row)
    merge = merge_owned_values if attribute == 'owned_fields' else merge_reference_values
    return tuple((slot, merge(candidates)) for slot, candidates in sorted(rows.items()))


def merge_owned_values(values):
    merged = merge_reference_values(values)
    kinds = {candidate.kind for candidate in merged.candidates}
    if 'owned_field_input' not in kinds or len(kinds) == 1:
        return merged
    alternatives = tuple(dict.fromkeys(alternative for value in values
                                      for alternative in value.owned_alternatives or (value,)))
    return replace(merged, owned_alternatives=alternatives)


def unflatten_reference_value(value, fields):
    direct = tuple((slot, targets) for slot, targets in fields if '/' not in slot)
    rows = []
    for slot, row in value.rows:
        prefix = slot + '/'
        nested = tuple((key[len(prefix):], targets) for key, targets in fields if key.startswith(prefix))
        rows.append((slot, unflatten_reference_value(row, nested) if nested else row))
    return replace(value, fields=direct, rows=tuple(rows))


def reference_value_place(value, indices):
    owner, typ, starts = value, value.typ, (0,)
    for index in indices:
        pointer = reference_type(typ)
        if pointer:
            rows = dict(owner.rows)
            owner = merge_reference_values([rows[str(slot)] for slot in starts])
            typ, starts = pointer[1], (0,)
        element, length = fixed_array_shape(typ)
        nested = reference_array_shape(element)
        stride = nested[1] if nested else 1
        selected = (index[1],) if index[0] == 'int' else range(length)
        starts = tuple(start + slot * stride for start in starts for slot in selected)
        typ = element
    width = reference_array_shape(typ)[1] if reference_array_shape(typ) else 1
    return owner, typ, tuple(tuple(start + slot for start in starts) for slot in range(width))


def replace_reference_rows(value, positions, incoming):
    rows = dict(value.rows)
    incoming_rows = dict(incoming.rows) if incoming.mode == 'array_refs' and not incoming.container_borrow else {'0': incoming}
    for column, group in enumerate(positions):
        if str(column) not in incoming_rows:
            continue
        new = incoming_rows[str(column)]
        for position in group:
            key = str(position)
            rows[key] = new if len(group) == 1 or key not in rows else merge_reference_values([rows[key], new])
    return tuple(sorted(rows.items()))


def swapped_reference_rows(value, first, second):
    tokens = tuple((str(slot), frozenset({slot})) for slot in range(reference_array_shape(value.typ)[1]))
    mapping = swap_reference_fields(tokens, value.typ, (), first, second)
    rows = dict(value.rows)
    return tuple((slot, merge_reference_values([rows[str(index)] for index in indices if str(index) in rows]))
                 for slot, indices in mapping if indices and all(str(index) in rows for index in indices))


def target_row_templates(actuals, targets):
    candidates = []
    for target in targets:
        actual = actuals[target.parameter]
        if target.kind in ('stored_array_parameter', 'reserved_stored_array_parameter'):
            holder, slot = reference_tree_slot(actual, target.field)
            row = dict(holder.rows).get(slot)
        else:
            row = actual if getattr(actual, 'mode', None) == 'array_refs' else None
        if row is not None:
            candidates.append(row)
    return merge_reference_values(candidates) if candidates else None


def rebuild_reference_tree(prototype, typ, fields, original_fields, actuals, prefix=''):
    count = reference_array_shape(typ)[1]
    flat = dict(fields)
    original = dict(original_fields)
    if prototype.typ != typ and reference_array_shape(prototype.typ):
        groups = []
        positions = array_container_positions(prototype)
        for slot in range(count):
            selected = set()
            for target in original.get(prefix + str(slot), ()):
                if target.kind not in ('stored_array_parameter', 'reserved_stored_array_parameter'):
                    continue
                holder, field = reference_tree_slot(actuals[target.parameter], target.field)
                if not holder.container_origins & prototype.container_origins:
                    continue
                source = set(array_container_positions(holder)[int(field)])
                selected.update(index for index, destination in enumerate(positions)
                                if source & set(destination))
            groups.append(tuple(sorted(selected)) or tuple(range(len(prototype.fields))))
        prototype = project_reference_array(prototype, typ, tuple(groups))
    direct = tuple((str(slot), flat.get(prefix + str(slot), frozenset())) for slot in range(count))
    pointee = reference_array_element(typ)[1]
    rows = []
    if reference_array_shape(pointee):
        for slot in range(count):
            key = prefix + str(slot)
            template = target_row_templates(actuals, original.get(key, ()))
            if template is None:
                template = dict(prototype.rows).get(str(slot))
            if template is None:
                template = replace(prototype, typ=pointee, fields=(), rows=(), container_positions=(),
                                   container_origins=frozenset({('contract_row', key)}))
            rows.append((str(slot), rebuild_reference_tree(template, pointee, fields, original_fields, actuals, key + '/')))
    return replace(prototype, typ=typ, fields=direct, rows=tuple(rows))


def reference_tree_type(typ, path):
    for _ in path.split('/'):
        typ = reference_array_element(typ)[1]
    return typ


def possible_handle_items(items):
    return frozenset().union(*items) if isinstance(items, tuple) else items


def merge_handle_items(values):
    rows = [value.handle_items for value in values]
    if not rows or any(row is None for row in rows):
        return None
    if isinstance(rows[0], tuple) and all(isinstance(row, tuple) and len(row) == len(rows[0]) for row in rows):
        return tuple(frozenset().union(*items) for items in zip(*rows))
    return frozenset().union(*(possible_handle_items(row) for row in rows))


def update_shared_vector_items(environment, shadows, vector, items, identify, *, appended=None):
    locations = identify(vector)
    holders = [(scope, name, candidate) for scope in (environment, *shadows) for name, candidate in scope.items()
               if getattr(candidate, 'typ', None) == vector.typ and locations & identify(candidate)]
    # Several bindings can represent different generations of one site.
    for scope, name, candidate in holders:
        precise = len(holders) == len(locations) == 1 and identify(candidate) == locations
        updated = replace(candidate, handle_items=items)
        if not precise:
            updated = replace(updated, handle_items=merge_handle_items((candidate, updated)))
        targets = possible_handle_items(updated.handle_items)
        if targets is None:
            targets = dict(candidate.fields).get('.items', frozenset()) | (possible_handle_items(items) or frozenset())
        scope[name] = replace(updated, fields=(('.items', targets),) if targets else ())
        if hasattr(updated, 'input_items_changed'):
            history = candidate.input_item_history
            symbolic = len(locations) == 1 and any(
                isinstance(origin, tuple) and origin[0] == 'owned_parameter' for origin in locations)
            if appended is not None and history is not None and (precise or symbolic and identify(candidate) == locations):
                history = replace(history, appended=(*history.appended, *appended))
            else:
                history = None
            scope[name] = replace(scope[name], input_items_changed=True, input_item_history=history)


def handle_items_at(items, index):
    if isinstance(items, tuple) and index is not None and 0 <= index < len(items):
        return items[index]
    return possible_handle_items(items)


def shared_vector_field_items(value, field):
    if value.typ in REFERENCE_VECTORS and field.startswith('.items:'):
        if value.handle_items is not None:
            return handle_items_at(value.handle_items, int(field.split(':')[1]))
        field = '.items'
    return dict(value.fields).get(field, frozenset())


def replace_shared_vector_item(items, index, incoming):
    if index is not None and index < 0:
        return items, incoming
    if isinstance(items, tuple):
        if not items or index is not None and not 0 <= index < len(items):
            return items, incoming
        if index is not None:
            return handle_items_after_exchange(items, index, incoming), items[index]
        return handle_items_after_exchange(items, None, incoming), possible_handle_items(items) | incoming
    combined = (items or frozenset()) | incoming
    return combined, combined


def handle_items_after_exchange(items, index, incoming, append=False, *, weak=False):
    if items is None:
        return None
    if not isinstance(items, tuple):
        return items | incoming
    if append:
        return (*items, incoming)
    if index is None:
        return tuple(old | incoming for old in items)
    if 0 <= index < len(items):
        replacement = items[index] | incoming if weak else incoming
        return items[:index] + (replacement,) + items[index + 1:]
    return items


def handle_items_after_removal(items, index):
    if not isinstance(items, tuple) or not items:
        return items
    if index is not None and 0 <= index < len(items):
        return items[:index] + items[index + 1:]
    return tuple(left | right for left, right in zip(items, items[1:]))


VECTOR_LAST_ITEM = -2


def last_handle_index(positions, excluded=(), offset=0):
    if not isinstance(positions, tuple):
        return None
    excluded = set(excluded)
    for index in range(len(positions) - 1, -1, -1):
        if index in excluded:
            continue
        if offset == 0:
            return index
        offset -= 1
    return None


UNKNOWN_VECTOR_REMOVALS = (-1,)


def remaining_handle_positions(positions, removals):
    if removals == UNKNOWN_VECTOR_REMOVALS:
        return None
    if not isinstance(positions, tuple) or not removals:
        return positions
    tail, *excluded = removals
    excluded = set(excluded)
    remaining = tuple(item for index, item in enumerate(positions) if index not in excluded)
    return remaining[:max(0, len(remaining) - tail)] if tail else remaining



def remaining_handle_items(items, removals):
    if removals == UNKNOWN_VECTOR_REMOVALS:
        return possible_handle_items(items)
    return remaining_handle_positions(items, removals)


def replace_handle_positions(positions, replacements):
    if not isinstance(positions, tuple):
        return positions
    by_index = dict(replacements)
    return tuple(by_index.get(index, value) for index, value in enumerate(positions))
