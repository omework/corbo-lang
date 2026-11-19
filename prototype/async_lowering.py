"""Lower async bodies to the task ABI with static checks of memory transitions."""

from owned_join_types import (
    OWNED_JOIN_TYPES, OWNED_JOIN_CTYPES, OWNED_JOIN_CELLS, OWNED_JOIN_PAYLOADS,
    OWNED_PAYLOAD_MODES, OWNED_NESTED_PAYLOAD_MODES, owned_join_mode, owned_inner_mode,
    owned_result_type, owned_cleanup,
)
from option_join_types import (
    OPTION_JOIN_TYPES, OPTION_JOIN_CTYPES, OPTION_JOIN_CELLS, OPTION_JOIN_PAYLOADS,
    OPTION_PAYLOAD_MODES, option_join_mode, option_inner_signature, option_cleanup, option_payload_type,
)
from exchange_join_types import (
    EXCHANGE_JOIN_TYPES, exchange_join_mode, EXCHANGE_JOIN_CTYPES, EXCHANGE_JOIN_CELLS,
    EXCHANGE_JOIN_PAYLOADS, EXCHANGE_PAYLOAD_MODES, exchange_inner_signature, exchange_cleanup, exchange_payload_type,
)
from handle_exchange_types import exchange_element, exchange_optional, exchange_type
from capture_paths import capture_index
from structure_views import field_kind, field_size, scalar_field_mode, FIELD_C_TYPES
from mutex_syntax import GUARD_TYPES, payload_type as mutex_payload

from collections import ChainMap
from dataclasses import dataclass, replace
from array_syntax import INLINE_VECTOR_ELEMENTS, HANDLE_VECTOR, HANDLE_VECTORS, is_handle_vector, handle_vector_element, consumed_result_expression, fixed_array_shape, reference_array_path, reference_type
from array_syntax import vector_payload_element
from integer_syntax import exact_integer_conversion
from numeric_core import (FORMATS, EXTRA_MODES, EXTRA_C_TYPES, MODE_TYPES, NUMERIC_JOIN_FIELDS,
                          NUMERIC_REFERENCE_FIELDS, NUMERIC_REFERENCE_SIGNATURES,
                          CONVERSION_PAYLOADS, CONVERSION_FAMILIES, CONVERSION_C_TYPES,
                          c_conversion, conversion_mode, c_literal, c_operation, c_print, numeric_type)
from utf8_syntax import ERROR_VALUE_TYPES, ERROR_VALUE_MODES, ERROR_VALUE_TAGS, RESULT_ERROR_MODES
from utf8_syntax import (
    ASYNC_CAPTURE_VIEW_MODES, ASYNC_SHARED_VIEW_MODES, ASYNC_VIEW_FIELDS, SHARED_VECTOR_SLICE_MODES,
    VECTOR_SLICE_ELEMENTS, VECTOR_SLICE_MODES,
    ASYNC_VALUE_RESULT_FAMILIES as UTF8_VALUE_RESULT_FAMILIES,
    ASYNC_VALUE_RESULT_CTYPES as UTF8_VALUE_RESULT_CTYPES,
    ASYNC_VALUE_RESULT_FIELDS as UTF8_VALUE_RESULT_FIELDS, VALUE_MODES,
    VECTOR_VALUE_RESULT_FAMILIES, VECTOR_VALUE_RESULT_CTYPES,
    text_slice_bound_error,
    PLAIN_JOIN_TYPES, PLAIN_JOIN_FIELDS, PLAIN_JOIN_C_TYPES, PLAIN_JOIN_ANNOTATIONS,
    PLAIN_JOIN_SCALAR_RESULTS, PLAIN_JOIN_INNER_MODES, PLAIN_RETURN_JOINS,
)


class NoAsyncContinuation(Exception):
    """An emitted expression has no path back to its enclosing instruction."""


@dataclass(frozen=True)
class SelectionState:
    c: str
    branches: tuple
    loans: list
    awaited: bool = False
    paths: tuple = ()


JOIN_PAYLOADS = {'join_owned': 'allocation', 'join_nested': 'nested', 'join_option': 'optional_nested', 'handle_option': 'optional_allocation', 'buffered_handle_exchange': 'exchange_allocation'}
JOIN_CELLS = {'join_owned': 'allocation', 'join_nested': 'value.allocation', 'join_option': 'value.value', 'handle_option': 'value', 'buffered_handle_exchange': 'value'}
OWNED_WRAPPER_TYPES = {'join_owned': 'CrustJoinResult', 'join_nested': 'CrustNestedJoinResult', 'join_option': 'CrustOptionJoinResult',
                       'handle_option': 'VectorHandleResult', 'buffered_handle_exchange': 'VectorHandleResult', 'buffered_handle_try_push': 'VectorHandleResult'}
OWNED_WRAPPER_PAYLOADS = {**JOIN_PAYLOADS, 'handle_option': 'optional_allocation',
                          'buffered_handle_exchange': 'exchange_allocation', 'buffered_handle_try_push': 'rejected_allocation'}
JOIN_PAYLOADS = ChainMap(OWNED_JOIN_PAYLOADS, OPTION_JOIN_PAYLOADS, EXCHANGE_JOIN_PAYLOADS, JOIN_PAYLOADS)
JOIN_CELLS = ChainMap(OWNED_JOIN_CELLS, OPTION_JOIN_CELLS, EXCHANGE_JOIN_CELLS, JOIN_CELLS)
OWNED_WRAPPER_TYPES = ChainMap(OWNED_JOIN_CTYPES, OPTION_JOIN_CTYPES, EXCHANGE_JOIN_CTYPES, OWNED_WRAPPER_TYPES)
OWNED_WRAPPER_PAYLOADS = ChainMap(OWNED_JOIN_PAYLOADS, OPTION_JOIN_PAYLOADS, EXCHANGE_JOIN_PAYLOADS, OWNED_WRAPPER_PAYLOADS)


def wrapper_cleanup(value, payload):
    if payload in OWNED_PAYLOAD_MODES:
        return owned_cleanup(value, OWNED_PAYLOAD_MODES[payload])
    if payload in OPTION_PAYLOAD_MODES:
        return option_cleanup(value, OPTION_PAYLOAD_MODES[payload])
    if payload in EXCHANGE_PAYLOAD_MODES:
        return exchange_cleanup(value, EXCHANGE_PAYLOAD_MODES[payload])
    cell = f'{value}.value' if payload in ('optional_allocation', 'exchange_allocation', 'rejected_allocation') else f'{value}.allocation'
    condition = ('1' if payload == 'exchange_allocation' else
                 f'{value}.status != 0' if payload == 'rejected_allocation' else f'{value}.status == 0')
    if payload == 'nested':
        cell = f'{value}.value.allocation'
        condition += f' && {value}.value.status == 0'
    return cell, condition


def wrapper_content_type(mode, typ):
    return exchange_element(typ) if mode == 'buffered_handle_exchange' else typ


def owned_wrapper_kind(mode, typ):
    return ('buffered_handle_try_push' if mode == 'buffered_handle_exchange'
            and exchange_optional(typ) else mode)


def owned_wrapper_payload(mode, typ):
    return OWNED_WRAPPER_PAYLOADS[owned_wrapper_kind(mode, typ)]


ARRAY_BORROWS = {'array_ref': 'ref', 'array_mut': 'mut'}
SCALAR_TYPES = ChainMap(PLAIN_JOIN_TYPES, { **ERROR_VALUE_TYPES, 'runtime_error': 'runtime::Error', 'scalar': 'Int', 'bool': 'Bool', 'byte': 'u8', 'char': 'char', 'text': '&str', 'byte_ref': '&u8',
                **EXTRA_MODES,
                **{mode: '&' + VALUE_MODES[mode] for mode in VECTOR_SLICE_ELEMENTS},
                **{mode: '&mut ' + VALUE_MODES[mode] for mode in SHARED_VECTOR_SLICE_MODES},
                **{mode: VALUE_MODES[mode] for mode in UTF8_VALUE_RESULT_FAMILIES}})
SCALAR_MODES = ChainMap(PLAIN_JOIN_ANNOTATIONS, {typ: mode for mode, typ in SCALAR_TYPES.items()})
ASYNC_VIEW_TYPES = tuple(SCALAR_TYPES[mode] for mode in ASYNC_CAPTURE_VIEW_MODES)
SCALAR_RESULTS = ChainMap(PLAIN_JOIN_SCALAR_RESULTS, { **{(mode, typ): typ for mode, typ in ERROR_VALUE_TYPES.items()},('runtime_error', 'runtime::Error'): 'runtime::Error', ('scalar', 'Int'): 'Int', ('scalar', 'Bool'): 'Bool',
                  **{(mode, typ): typ for mode, typ in EXTRA_MODES.items()},
                  ('byte', 'u8'): 'u8', ('char', 'char'): 'char',
                  ('text', 'str'): '&str', ('byte_ref', 'u8'): '&u8',
                  **{(mode, VALUE_MODES[mode]): SCALAR_TYPES[mode]
                     for mode in (*VECTOR_SLICE_ELEMENTS, *SHARED_VECTOR_SLICE_MODES)},
                  **{(mode, VALUE_MODES[mode]): VALUE_MODES[mode] for mode in UTF8_VALUE_RESULT_FAMILIES}})
WRAPPED_UTF8_TYPES = {family: VALUE_MODES[mode] for mode, family in UTF8_VALUE_RESULT_FAMILIES.items()}
WRAPPED_UTF8_MODES = {family: mode for mode, family in UTF8_VALUE_RESULT_FAMILIES.items()}


def public_handle_type(signature, *, storage='pool'):
    """Expose the result type; keep the concrete task and its loans internally."""
    mode, typ = signature
    if mode == 'owned':
        payload = typ if storage == 'local' else f'A<{typ}>'
    elif mode in ('ref', 'mut'):
        payload = ('&mut ' if mode == 'mut' else '&') + typ
    elif mode == 'buffered_handle_exchange':
        payload = typ
    elif mode in EXCHANGE_JOIN_TYPES:
        payload = EXCHANGE_JOIN_TYPES[mode]
    elif mode in OPTION_JOIN_TYPES:
        payload = OPTION_JOIN_TYPES[mode]
    elif mode == 'handle_option':
        payload = f'Option<{typ}>' if storage == 'local' else f'Option<A<{typ}>>'
    elif mode in OWNED_JOIN_TYPES:
        payload = owned_result_type(mode, typ, storage)
    else:
        payload = SCALAR_RESULTS.get(signature, typ)
    return f'runtime::Handle<{payload}>'


def push_new_receiver(expr):
    if (expr[0] == 'method_call' and expr[1][0] == 'name'
            and expr[2] == 'push_new'):
        return expr[1][1]
    return None


def capture_ctype(mode, typ=None, *, structures=()):
    if mode == 'async_execution':
        return 'CrustAsyncExecution'
    if mode in EXTRA_C_TYPES:
        return EXTRA_C_TYPES[mode]
    if mode in ('ref', 'mut') and typ in structures:
        return 'CrustStructureView'
    if mode in ('ref', 'mut') and typ and typ.startswith('Pool<'):
        return 'Source *'
    if (mode, typ) == ('mut', 'u8'):
        return 'uint8_t *'
    if mode in ('ref', 'mut') and typ in EXTRA_C_TYPES:
        return f'{EXTRA_C_TYPES[typ]} *'
    if mode in ERROR_VALUE_TYPES:
        return 'int'
    if mode in PLAIN_JOIN_TYPES:
        return PLAIN_JOIN_C_TYPES[mode]
    if mode in ('map_owned_ref_slot', 'map_owned_mut_slot'):
        return 'Cell * const *' if mode == 'map_owned_ref_slot' else 'Cell **'
    if mode == 'map_shared_ref_slot':
        from hashmap_syntax import value_layout
        return f'{value_layout(typ)[1]} const *'
    if mode in ('ref', 'mut') and typ is not None and typ not in ('Int', 'u8'):
        return 'Cell *'
    if mode in VECTOR_SLICE_ELEMENTS or mode in SHARED_VECTOR_SLICE_MODES:
        return 'VectorSlice'
    if mode in UTF8_VALUE_RESULT_FAMILIES:
        return UTF8_VALUE_RESULT_CTYPES[mode]
    return {'runtime_error': 'CrustRuntimeError', 'scalar': 'int', 'bool': 'int', 'byte': 'uint8_t', 'char': 'CrustChar', 'text': 'CrustText', 'byte_ref': 'const unsigned char *',
            'ref': 'const int *', 'mut': 'int *', 'owned': 'Cell *',
            'array': 'const void *', 'array_ref': 'const void *', 'array_mut': 'void *',
            'join_owned': 'CrustJoinResult', 'join_nested': 'CrustNestedJoinResult', 'join_option': 'CrustOptionJoinResult',
            'handle_option': 'VectorHandleResult', 'buffered_handle_exchange': 'VectorHandleResult',
            **EXCHANGE_JOIN_CTYPES, **OPTION_JOIN_CTYPES, **OWNED_JOIN_CTYPES}[mode]


def utf8_result_parameters(node, functions, cache=None, active=frozenset(), *, sync_contracts=None, sync_result_contract=None):
    if getattr(node, "public_result_views", ()):
        return frozenset(node.public_result_views)
    function_name, parameters, result, body = node.args
    if result[0] not in ASYNC_CAPTURE_VIEW_MODES:
        return frozenset()
    if cache is None:
        cache = {}
    if function_name in cache:
        return cache[function_name]
    def source_parameter(mode, typ):
        return (mode in ASYNC_CAPTURE_VIEW_MODES or mode in ('ref', 'mut') and (typ == 'String' or typ in VECTOR_SLICE_MODES)
                or result[0] == 'byte_ref' and (mode == 'mut' and typ == 'u8'
                    or mode in ARRAY_BORROWS and scalar_array_layout(typ)[1] == 'uint8_t'))

    if function_name in active:
        return frozenset(index for index, (_, mode, typ) in enumerate(parameters)
                         if source_parameter(mode, typ))
    definitions = {}
    returns = []

    def view_result_contract(callee):
        contract = (sync_contracts or {}).get(callee)
        return contract if contract is not None or sync_result_contract is None else sync_result_contract(callee)

    def branch_call_names(branch, expanding):
        if isinstance(branch, tuple):
            return awaited_call_names(branch, expanding)
        if not branch:
            return None
        terminal = branch[-1]
        if terminal.op == 'if_yield':
            return awaited_call_names(terminal.args[0], expanding)
        if terminal.op == '<-' and not terminal.terminated:
            return awaited_call_names(('name', terminal.args[0]), expanding)
        if terminal.op == 'return':
            # This branch returns from the enclosing function.
            return set()
        return None

    def loop_break_values(value):
        if hasattr(value, 'op'):
            if value.op == 'break':
                yield value.args[0]
            elif value.op not in ('loop', 'while'):
                yield from loop_break_values(value.args)
        elif isinstance(value, (tuple, list)):
            if isinstance(value, tuple) and value and value[0] == 'loop_expr':
                return
            for item in value:
                yield from loop_break_values(item)

    def awaited_call_names(operand, expanding):
        op = operand[0]
        if op in ('task_spawn', 'transfer', 'array_transfer', 'new_transfer'):
            return awaited_call_names(operand[1], expanding)
        if op == 'scope':
            return branch_call_names(operand[2], expanding)
        if op == 'value_match':
            return branch_call_names(operand[1], expanding)
        if op == 'if_expr':
            left = branch_call_names(operand[2], expanding)
            right = branch_call_names(operand[3], expanding)
            return left | right if left is not None and right is not None else None
        if op == 'loop_expr':
            alternatives = [awaited_call_names(value, expanding) if value is not None else None
                            for value in loop_break_values(operand[1].args)]
            if alternatives and all(origins is not None for origins in alternatives):
                return set().union(*alternatives)
            return None
        if op in ('name', 'down', 'move'):
            variable = operand[1]
            if variable in expanding:
                return None
            alternatives = [awaited_call_names(initializer, expanding | {variable})
                            for initializer in definitions.get(variable, ())]
            if alternatives and all(origins is not None for origins in alternatives):
                return set().union(*alternatives)
            return None
        if op == 'call' and (contract := view_result_contract(operand[1])) is not None:
            if contract.result_type[0] == 'execution':
                targets = {target for field, targets in contract.result.borrowed_fields
                           if field.partition('.')[2] in ('4', '5') for target in targets}
                if all(target.kind in ('utf8_parameter', 'parameter', 'string_parameter', 'vector_parameter')
                       for target in targets):
                    return {origin for target in targets for origin in mentions(operand[2][target.parameter], expanding)}
        if op != 'call' or operand[1] not in functions:
            return None
        child = functions[operand[1]]
        arguments = operand[2]
        if child.args[2][0] not in ASYNC_CAPTURE_VIEW_MODES or len(arguments) != len(child.args[1]):
            return None
        positions = utf8_result_parameters(child, functions, cache, active | {function_name},
                                          sync_contracts=sync_contracts, sync_result_contract=sync_result_contract)
        return {origin for position in positions for origin in mentions(arguments[position], expanding)}

    def mentions(value, expanding=frozenset()):
        if isinstance(value, tuple) and value and value[0] == 'call':
            contract = view_result_contract(value[1])
            if (contract is not None and contract.result_type[0] in ASYNC_CAPTURE_VIEW_MODES
                    and len(value[2]) == len(contract.parameters)
                    and all(target.kind in ('utf8_parameter', 'parameter', 'string_parameter', 'vector_parameter')
                            for target in contract.result.reference_targets)):
                return {name for target in contract.result.reference_targets
                        if 0 <= target.parameter < len(value[2])
                        for name in mentions(value[2][target.parameter], expanding)}
        if isinstance(value, tuple) and value and value[0] in ('utf8_slice', 'utf8_try_slice', 'array_index', 'array_split'):
            # A bound or index can read another capture without the result
            # borrowing that capture's storage.
            return mentions(value[1], expanding)
        if isinstance(value, tuple) and len(value) == 2 and value[0] == 'await':
            operand = value[1]
            origins = awaited_call_names(operand, expanding)
            if origins is not None:
                return origins
        if hasattr(value, 'args'):
            return mentions(value.args, expanding)
        if isinstance(value, str):
            return {value}
        if isinstance(value, (tuple, list)):
            return {name for item in value for name in mentions(item, expanding)}
        return set()

    def scan(value):
        if hasattr(value, 'op'):
            if value.op in ('var', 'assign'):
                name, initializer = value.args
                definitions.setdefault(name, []).append(initializer)
            elif value.op == 'return':
                returns.append(value.args)
            scan(value.args)
        elif isinstance(value, (tuple, list)):
            for item in value:
                scan(item)

    # Join all assignments and shadowed definitions. An unsupported expression
    # still contributes every name it mentions.
    scan(body)
    returned = {origin for value in returns for origin in mentions(value)}
    pending = list(returned)
    while pending:
        name = pending.pop()
        origins = {origin for initializer in definitions.get(name, ()) for origin in mentions(initializer)}
        for origin in origins - returned:
            returned.add(origin)
            pending.append(origin)
    cache[function_name] = frozenset(index for index, (parameter, mode, typ) in enumerate(parameters)
                                     if source_parameter(mode, typ) and parameter in returned)
    return cache[function_name]


def scalar_array_layout(typ):
    dimensions = []
    while (array := fixed_array_shape(typ)) is not None:
        typ, length = array
        dimensions.append(length)
    element = {'Int': 'int', 'u8': 'uint8_t', **EXTRA_C_TYPES}.get(typ)
    return (tuple(dimensions), element) if dimensions and element else ((), None)


def int_reference_layout(typ, mode):
    if mode not in ARRAY_BORROWS:
        return ()
    layout = []
    while (shape := fixed_array_shape(typ)) is not None:
        typ, length = shape
        reference = reference_type(typ)
        layout.append((length, reference[0] if reference else None))
        if reference:
            _, typ = reference
            if typ == 'Int':
                return tuple(layout)
    return ()


def int_reference_row(typ, mode):
    return tuple(length for length, _ in int_reference_layout(typ, mode))


def reference_loop_exits(body, definitions=()):
    """Yield only breaks belonging to this loop, with lexical initializers."""
    def in_expression(value, visible):
        if isinstance(value, list) and all(hasattr(part, 'op') for part in value):
            yield from reference_loop_exits(value, visible)
        elif isinstance(value, (list, tuple)):
            if value and value[0] == 'loop_expr':
                return  # This expression introduces a different break target.
            for part in value:
                yield from in_expression(part, visible)
        elif hasattr(value, 'op'):
            yield from reference_loop_exits([value], visible)

    definitions = list(definitions)
    for statement in body:
        if statement.op in ('loop', 'while'):
            if statement.op == 'loop' and branch_control_exit([statement]):
                return
            continue
        if statement.op == 'var':
            yield from in_expression(statement.args[1], definitions)
            definitions.append(statement)
        elif statement.op == 'break':
            yield from in_expression(statement.args[0], definitions)
            yield statement.args[0], statement.line, definitions
            return
        elif statement.op in ('return', 'continue'):
            yield from in_expression(statement.args, definitions)
            return
        elif statement.op == 'if':
            yield from in_expression(statement.args[0], definitions)
            for branch in statement.args[1:]:
                yield from reference_loop_exits(branch, definitions)
        elif statement.op == 'scope':
            yield from reference_loop_exits(statement.args[1], definitions)
        else:
            yield from in_expression(statement.args, definitions)
        if branch_control_exit([statement]):
            return


def expression_control_exit(value):
    """Whether expression evaluation is known not to reach its receiver."""
    if not isinstance(value, (tuple, list)) or not value:
        return False
    if value[0] == 'if_expr':
        return expression_control_exit(value[1]) or all(branch_control_exit(arm) for arm in value[2:])
    if value[0] == 'scope':
        return branch_control_exit(value[2])
    if value[0] == 'value_match':
        return branch_control_exit(value[1])
    if value[0] == 'loop_expr':
        return not any(reference_loop_exits(value[1].args[0]))
    return any(expression_control_exit(part) for part in value)


def task_has_only_value_dependencies(node):
    """Prove the task signature carries no external storage dependencies."""
    scalar_modes = {*MODE_TYPES, 'scalar', 'bool', 'byte', 'char'}

    def independent(mode, typ):
        return mode in scalar_modes or (mode == 'array' and scalar_array_layout(typ)[1] is not None)

    return (all(independent(mode, typ) for _, mode, typ in node.args[1])
            and (node.args[2][0] in ('void', 'async_execution') or independent(*node.args[2])))


def branch_control_exit(body):
    """Recognize a sequence with no path back to its receiver."""
    if not isinstance(body, list):
        return expression_control_exit(body)
    for statement in body:
        if statement.op in ('return', 'break', 'continue'):
            return True
        if statement.op == 'if':
            if (expression_control_exit(statement.args[0])
                    or all(branch_control_exit(arm) for arm in statement.args[1:])):
                return True
        elif statement.op == 'scope':
            if branch_control_exit(statement.args[1]):
                return True
        elif statement.op == 'loop':
            if not any(reference_loop_exits(statement.args[0])):
                return True
        elif statement.op != 'while' and expression_control_exit(statement.args):
            return True
    return False


def expand_reference_return_branches(node):
    """Lower tail conditional references to returns on the same control paths.

    No reference temporary or implicit lifetime extension is introduced. Both
    contract inference and frame lowering consume this form, retaining normal
    per-branch access checks, suspension points and cleanup.
    """
    if node.args[2] not in (('ref', 'Int'), ('mut', 'Int'), ('mut', 'u8')):
        return node

    def walk(value):
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, tuple):
            return tuple(walk(item) for item in value)
        if not hasattr(value, 'op'):
            return value
        statement = replace(value, args=walk(value.args))
        if statement.op != 'return' or not statement.args[0]:
            return statement
        expr = statement.args[0]
        if expr[0] != 'if_expr':
            return statement

        def arm(body):
            if isinstance(body, tuple):
                return [walk(replace(statement, args=(body,)))]
            body = list(body)
            if body and body[-1].op == 'if_yield':
                body[-1] = walk(replace(body[-1], op='return'))
            return body

        return replace(statement, op='if', args=(expr[1], arm(expr[2]), arm(expr[3])))

    return replace(node, args=(*node.args[:3], walk(node.args[3])))


def borrowed_result_parameters(node, functions, fail, cache, **options):
    return frozenset(index for index, _ in borrowed_result_paths(node, functions, fail, cache, **options))


def borrowed_result_paths(node, functions, fail, cache, visiting=(), *, sync_contracts=None, sync_result_contract=None):
    """Infer which input references can reach the result, including awaited relays."""
    if getattr(node, 'public_result_borrows', ()):
        return frozenset((index, ()) for index in node.public_result_borrows)
    node = expand_reference_return_branches(node)
    sync_contracts = sync_contracts or {}
    def result_contract(callee):
        contract = sync_contracts.get(callee)
        if contract is None and sync_result_contract is not None:
            contract = sync_result_contract(callee)
        return contract
    name, parameters, result, body = node.args
    if result[0] not in ('ref', 'mut'):
        return frozenset()
    completion = getattr(node, 'field_effect_summary', None)
    completed_targets = completion.completion_result.reference_targets if completion and completion.complete else ()
    if completion and completion.complete and (completion.structure_fields or completed_targets and all(
            target.kind in ('parameter', 'exclusive_join_parameter', 'async_handle_result', 'field_parameter', 'moved_field_parameter', 'detached_field_parameter',
                            'inline_field_parameter', 'indirect_field_parameter')
            for target in completed_targets)):
        # The completed contract follows stored references through local
        # carriers and helpers, and distinguishes old and new field targets.
        # Keep the syntax adapter for target representations not covered here.
        paths = set()
        for target in completion.completion_result.reference_targets:
            if target.kind in ('parameter', 'exclusive_join_parameter', 'async_handle_result'):
                path = ()
            elif target.kind in ('field_parameter', 'moved_field_parameter', 'detached_field_parameter', 'inline_field_parameter', 'indirect_field_parameter'):
                path = tuple(target.field.lstrip('.').split('.'))
            else:
                fail(node.line, 'prototype : provenance du résultat de terminaison non raccordée')
            paths.add((target.parameter, path))
            if target.kind == 'indirect_field_parameter':
                changed = dict(dict(completion.structure_fields).get(target.parameter, ()))
                for origin in changed.get('.' + target.field, ()):
                    if origin.kind == 'parameter':
                        paths.add((origin.parameter, ()))
                    elif origin.kind in ('field_parameter', 'detached_field_parameter'):
                        paths.add((origin.parameter, tuple(origin.field.lstrip('.').split('.'))))
                    else:
                        fail(node.line, 'prototype : cible du champ mutable retourné non raccordée')
        cache[name] = frozenset(paths)
        return cache[name]
    if name in cache:
        return cache[name]
    if name in visiting:
        fail(node.line, 'provenance récursive de résultat emprunté async non prise en charge')
    result_mode = result[0]
    inputs = {name: (index, mode) for index, (name, mode, _) in enumerate(parameters)
              if mode in ('ref', 'mut', *ARRAY_BORROWS)}
    diagnostic = (f'retour async &{result[1]} : un paramètre partagé durable ou un réemprunt est requis'
                  if result_mode == 'ref' else
                  f'retour async &mut {result[1]} : un paramètre mutable durable est requis')

    def projected_origin(expr, line):
        dereference = expr[0] == 'array_deref_slot'
        if expr[0] == 'array_deref_slot':
            expr = expr[1]
        name, indices = reference_array_path(expr)
        if name in inputs:
            index, mode = inputs[name]
            if dereference and parameters[index][2] == HANDLE_VECTOR and mode in ('ref', 'mut'):
                # A returned pointee loan keeps the owning vector reserved.
                return name, ()
        if name not in inputs or inputs[name][1] not in ARRAY_BORROWS:
            fail(line, diagnostic)
        return name, tuple(index[1] if index[0] == 'int' else None for index in indices)

    def task_calls_at(operand, tasks, awaited, line):
        if operand[0] in ('task_spawn', 'transfer'):
            yield from task_calls_at(operand[1], tasks, awaited, line)
        elif operand[0] == 'call':
            yield operand, awaited
        elif operand[0] in ('name', 'move', 'down') and operand[1] in tasks:
            yield from task_calls_at(*tasks[operand[1]], line)
        elif operand[0] in ('scope', 'value_match', 'loop_expr'):
            if operand[0] == 'loop_expr':
                body, exits = operand[1].args[0], 'break'
            else:
                body = operand[2] if operand[0] == 'scope' else operand[1]
                exits = '<-'
            yield from task_exits(body, tasks, awaited, line, exits)
        elif operand[0] == 'if_expr':
            for arm in operand[2:]:
                if isinstance(arm, list):
                    yield from task_exits(arm, tasks, awaited, line, '<-')
                else:
                    yield from task_calls_at(arm, tasks, awaited, line)
        else:
            fail(line, diagnostic)

    def task_exits(body, tasks, awaited, line, exits):
        tasks, awaited = tasks.copy(), awaited.copy()
        for statement in body:
            op, args = statement.op, statement.args
            if op == 'var':
                record_binding(*args, tasks, awaited)
            elif op == exits and (op == 'break' or not statement.terminated):
                operand = args[0] if op == 'break' else ('move', args[0])
                if operand is None:
                    fail(line, diagnostic)
                yield from task_calls_at(operand, tasks, awaited, line)
                return
            elif op == 'if_yield' and exits == '<-':
                yield from task_calls_at(args[0], tasks, awaited, line)
                return
            elif op in ('return', 'continue'):
                return
            elif exits == 'break' and op == 'if':
                for arm in args[1:]:
                    yield from task_exits(arm, tasks, awaited, line, exits)
            elif exits == 'break' and op == 'scope':
                yield from task_exits(args[1], tasks, awaited, line, exits)

    def record_binding(variable, expr, tasks, awaited):
        if push_new_receiver(expr) is not None:
            awaited[variable] = expr, tasks.copy(), awaited.copy()
            tasks.pop(variable, None)
        elif expr[0] == 'await':
            awaited[variable] = expr[1], tasks.copy(), awaited.copy()
            tasks.pop(variable, None)
        elif expr[0] in ('call', 'move', 'scope', 'if_expr', 'loop_expr', 'value_match', 'task_spawn'):
            tasks[variable] = expr, tasks.copy(), awaited.copy()
            awaited.pop(variable, None)
        else:
            tasks.pop(variable, None)
            awaited.pop(variable, None)
        if expr[0] != 'await' and push_new_receiver(expr) is None:
            prior = awaited.copy()
            prior.pop(variable, None)
            awaited[variable] = ('reference_value', expr), tasks.copy(), prior

    def awaited_origin(operand, tasks, awaited, line):
        if operand[0] == 'reference_value':
            return reference_origin(operand[1], tasks, awaited, line)
        if (receiver := push_new_receiver(operand)) is not None:
            if receiver not in inputs or inputs[receiver][1] != 'mut':
                fail(line, diagnostic)
            index = inputs[receiver][0]
            if parameters[index][2] != f'Vector<{result[1]}>':
                fail(line, diagnostic)
            return 'mut', {(index, ())}
        mode, origins = None, set()
        for call, context in task_calls_at(operand, tasks, awaited, line):
            child_mode, child_origins = call_origin(call, context, line)
            if mode is not None and child_mode != mode:
                fail(line, diagnostic)
            mode = child_mode
            origins.update(child_origins)
        if mode is None:
            fail(line, diagnostic)
        return mode, origins

    def call_origin(operand, awaited, line):
        if operand and operand[0] == 'call' and (contract := result_contract(operand[1])) is not None:
            from handle_types import public_signature
            signature = public_signature(contract.result_type[1]) if contract.result_type[0] == 'execution' else None
            if signature is not None and signature[0] in ('ref', 'mut') and signature[1] == result[1]:
                origins = set()
                for field, targets in contract.result.borrowed_fields:
                    if field.partition('.')[2] not in ('4', '5'):
                        continue
                    for target in targets:
                        if target.kind not in ('parameter', 'inline_field_parameter', 'indirect_field_parameter', 'detached_field_parameter'):
                            fail(line, 'prototype : projection du résultat du handle non prise en charge')
                        _, inherited = reference_origin(operand[2][target.parameter], {}, awaited, line)
                        suffix = tuple(target.field.lstrip('.').split('.')) if target.kind != 'parameter' else ()
                        origins.update((index, path + suffix) for index, path in inherited)
                return signature[0], origins
        if not operand or operand[0] != 'call' or operand[1] not in functions:
            fail(line, diagnostic)
        child = functions[operand[1]]
        mode, typ = child.args[2]
        if mode not in ('ref', 'mut') or typ != result[1] or len(operand[2]) != len(child.args[1]):
            fail(line, diagnostic)
        paths = borrowed_result_paths(child, functions, fail, cache, (*visiting, name),
                                      sync_contracts=sync_contracts, sync_result_contract=sync_result_contract)
        origins = set()
        for index, suffix in paths:
            argument = operand[2][index]
            if (argument[0] in ('name', 'reborrow') and argument[1] in inputs
                    and inputs[argument[1]][1] in ARRAY_BORROWS):
                origins.add((inputs[argument[1]][0], suffix))
                continue
            _, inherited = reference_origin(argument, {}, awaited, line)
            origins.update((source, prefix + suffix) for source, prefix in inherited)
        return mode, origins

    def reference_origin(expr, task_calls, awaited, line):
        if expr[0] == 'method_call' and expr[1][0] == 'name':
            _, receivers = reference_origin(expr[1], task_calls, awaited, line)
            types = {parameters[index][2] for index, path in receivers if not path}
            if len(types) != 1 or any(path for _, path in receivers):
                fail(line, diagnostic)
            symbol = next(iter(types)) + '.' + expr[2]
            if result_contract(symbol) is not None:
                expr = ('call', symbol, [expr[1], *expr[3]])
        if expr[0] == 'call' and (contract := result_contract(expr[1])) is not None:
            mode, typ = contract.result_type
            if mode not in ('ref', 'mut') or typ != result[1] or len(expr[2]) != len(contract.parameters):
                fail(line, diagnostic)
            origins = set()
            for target in contract.result.reference_targets:
                if target.kind not in ('parameter', 'inline_field_parameter', 'indirect_field_parameter', 'detached_field_parameter'):
                    fail(line, 'prototype : projection du résultat synchrone non prise en charge dans un état')
                _, inherited = reference_origin(expr[2][target.parameter], task_calls, awaited, line)
                suffix = tuple(target.field.lstrip('.').split('.')) if target.kind != 'parameter' else ()
                origins.update((index, path + suffix) for index, path in inherited)
            return mode, origins
        if expr[0] == 'loop_expr':
            possibilities = []
            for value, break_line, definitions in reference_loop_exits(expr[1].args[0]):
                if value is None:
                    fail(break_line, diagnostic)
                local_tasks, local_awaited = task_calls.copy(), awaited.copy()
                for binding in definitions:
                    record_binding(*binding.args, local_tasks, local_awaited)
                possibilities.append(reference_origin(value, local_tasks, local_awaited, break_line))
            if not possibilities:
                return result_mode, set()
            if any(mode != possibilities[0][0] for mode, _ in possibilities):
                fail(line, diagnostic)
            return possibilities[0][0], set().union(*(origins for _, origins in possibilities))
        if expr[0] == 'utf8_value' and expr[1][0] == 'name' and expr[1][1] in awaited:
            return awaited_origin(*awaited[expr[1][1]], line)
        if expr[0] in ('if_expr', 'scope', 'value_match'):
            def branch(body):
                if isinstance(body, tuple):
                    return reference_origin(body, task_calls, awaited, line)
                local_tasks, local_awaited = task_calls.copy(), awaited.copy()
                for statement in body:
                    if statement.op == 'var':
                        record_binding(*statement.args, local_tasks, local_awaited)
                    elif statement.op == 'return':
                        return None
                    elif statement.op == 'if_yield':
                        return reference_origin(statement.args[0], local_tasks, local_awaited, statement.line)
                return None
            arms = expr[2:] if expr[0] == 'if_expr' else (expr[1] if expr[0] == 'value_match' else expr[2],)
            possibilities = [origin for body in arms if (origin := branch(body)) is not None]
            if not possibilities:
                return result_mode, set()
            mode = possibilities[0][0]
            if any(other != mode for other, _ in possibilities):
                fail(line, diagnostic)
            return mode, set().union(*(origins for _, origins in possibilities))
        if expr[0] == 'await' or push_new_receiver(expr) is not None:
            mode, origins = awaited_origin(expr if push_new_receiver(expr) is not None else expr[1], task_calls, awaited, line)
        elif expr[0] == 'field' or expr[0] in ('ref_expr', 'mut_expr') and expr[1][0] in ('field', 'field_deref'):
            place = expr if expr[0] == 'field' else expr[1][1] if expr[1][0] == 'field_deref' else expr[1]
            inherited_mode, inherited = reference_origin(('name', place[1]), task_calls, awaited, line)
            mode = 'mut' if expr[0] == 'mut_expr' else 'ref'
            if mode == 'mut' and inherited_mode != 'mut':
                fail(line, diagnostic)
            origins = tuple((index, path + tuple(place[2].split('.'))) for index, path in inherited)
        elif expr[0] in ('ref_expr', 'mut_expr') and expr[1][0] in ('array_index', 'array_deref_slot'):
            source, path = projected_origin(expr[1], line)
            index, mode = inputs[source]
            if expr[0] == 'mut_expr' and mode not in ('mut', 'array_mut'):
                fail(line, diagnostic)
            mode = 'mut' if expr[0] == 'mut_expr' else 'ref'
            origins = ((index, path),)
        elif expr[0] in ('name', 'reborrow'):
            if expr[1] in inputs:
                index, mode = inputs[expr[1]]
                origins = ((index, ()),)
            elif expr[1] in awaited:
                mode, origins = awaited_origin(*awaited[expr[1]], line)
            else:
                fail(line, diagnostic)
            if mode not in ('ref', 'mut') or expr[0] == 'reborrow' and expr[2] == 'mut' and mode != 'mut':
                fail(line, diagnostic)
            if expr[0] == 'reborrow':
                mode = expr[2]
        else:
            fail(line, diagnostic)
        return mode, origins

    def scan(value, task_calls, awaited):
        if isinstance(value, list):
            task_calls, awaited = task_calls.copy(), awaited.copy()
            for item in value:
                if getattr(item, 'op', None) == 'var':
                    record_binding(*item.args, task_calls, awaited)
                yield from scan(item, task_calls, awaited)
                if hasattr(item, 'op') and branch_control_exit([item]):
                    break
        elif isinstance(value, tuple):
            for item in value:
                yield from scan(item, task_calls, awaited)
        elif hasattr(value, 'op'):
            if value.op != 'return':
                yield from scan(value.args, task_calls, awaited)
                return
            expr = value.args[0]
            if not expr:
                fail(value.line, diagnostic)
            # A return operand can itself exit the function (for example,
            # `return loop { if flag { return a; } break b; };`). Those
            # paths do not reach the outer result, but still belong to the
            # function's contract and must retain their borrowed sources.
            yield from scan(expr, task_calls, awaited)
            mode, origins = reference_origin(expr, task_calls, awaited, value.line)
            if mode != result_mode:
                fail(value.line, diagnostic)
            yield from origins

    cache[name] = frozenset(scan(body, {}, {}))
    return cache[name]


def owned_result_parameters(node, functions, cache=None, active=frozenset(), *, sync_result=None):
    """Trace returned cells through lexical bindings and awaited calls."""
    name, parameters, result, body = node.args
    if result[0] not in ('owned', *JOIN_PAYLOADS):
        return frozenset()
    effect = getattr(node, 'field_effect_summary', None)
    if (getattr(node, 'result_storage', False)
            or effect and effect.complete and effect.completion_result.candidates):
        from async_result_storage import result_storage
        plan = result_storage(node)
        if plan.parameters is not None:
            return plan.parameters
    # An opaque public handle describes this provenance in its contract;
    # it has no task body from which to infer it.
    if (position := getattr(node, 'public_result_storage', None)) is not None:
        return frozenset({position})
    if cache is None:
        cache = {}
    if name in cache:
        return cache[name]
    inputs = {parameter: ('owner', frozenset({index}))
              for index, (parameter, mode, _) in enumerate(parameters)
              if mode in ('owned', *JOIN_PAYLOADS)}
    inputs.update({parameter: ('source', frozenset({index}))
                   for index, (parameter, mode, typ) in enumerate(parameters)
                   if mode in ('ref', 'mut') and typ.startswith('Pool<')})
    all_captures = frozenset(index for _, origins in inputs.values() for index in origins)
    if name in active:
        return all_captures
    returned = []
    uncertain_replacement = False

    def combine(values):
        if not values or any(value is None for value in values):
            return None
        kind = values[0][0]
        if any(value[0] != kind for value in values):
            return None
        return kind, frozenset().union(*(origins for _, origins in values))

    def unknown_paths(value, breaks):
        nonlocal uncertain_replacement
        if isinstance(value, (list, tuple)):
            for item in value:
                unknown_paths(item, breaks)
        elif hasattr(value, 'op'):
            if value.op == 'return':
                returned.append(None)
            elif value.op == 'assign':
                uncertain_replacement = True
            elif value.op == 'break' and breaks is not None:
                breaks[0].append((None, None))
            elif value.op == 'continue' and breaks is not None:
                breaks[1].append(None)
            unknown_paths(value.args, breaks)

    def expression(expr, bindings, breaks):
        if not isinstance(expr, tuple) or not expr:
            return None
        op = expr[0]
        if op in ('move', 'name', 'down'):
            return bindings.get(expr[1])
        if op in ('ref', 'mut', 'reborrow') and bindings.get(expr[1]) is not None and bindings[expr[1]][0] == 'source':
            return bindings[expr[1]]
        if op == 'new' and bindings.get(expr[1]) is not None and bindings[expr[1]][0] == 'source':
            return 'owner', bindings[expr[1]][1]
        if op in ('task_spawn', 'transfer', 'array_transfer', 'new_transfer'):
            return expression(expr[1], bindings, breaks)
        if op in ('await', 'utf8_value'):
            value = expression(expr[1], bindings, breaks)
            if value is not None:
                return 'owner', value[1]
        elif op == 'call' and expr[1] in functions:
            arguments = [expression(arg, bindings, breaks) for arg in expr[2]]
            callee = functions[expr[1]]
            if len(arguments) == len(callee.args[1]):
                indexes = owned_result_parameters(callee, functions, cache, active | {name}, sync_result=sync_result)
                value = combine([arguments[index] for index in indexes])
                if value is not None:
                    return 'task', value[1]
        elif op == 'call' and sync_result is not None:
            summary = sync_result(expr[1])
            if summary is not None and summary.mode == 'owned' and summary.candidates:
                arguments = [expression(arg, bindings, breaks) for arg in expr[2]]
                origins = []
                for candidate in summary.candidates:
                    index = (candidate.parameter if candidate.kind == 'parameter' else
                             candidate.source.index if candidate.kind == 'fresh'
                             and candidate.source.kind == 'source_parameter' else None)
                    argument = arguments[index] if index is not None and 0 <= index < len(arguments) else None
                    origins.append(('owner', argument[1]) if argument is not None else None)
                value = combine(origins)
                if value is not None:
                    return 'owner', value[1]
        elif op == 'scope':
            return scoped_block(expr[2], bindings, breaks)[0]
        elif op == 'if_expr':
            expression(expr[1], bindings, breaks)
            return branches(expr[2:], bindings, breaks)[0]
        elif op == 'value_match':
            return scoped_block(expr[1], bindings, breaks)[0]
        elif op == 'loop_expr':
            return loop_body(expr[1].args[0], bindings)[0]
        else:
            unknown_paths(expr[1:], breaks)
        return None

    def scoped_block(statements, bindings, breaks):
        inner = bindings.copy()
        value, live = block(statements, inner, breaks)
        if live:
            for variable in bindings:
                bindings[variable] = inner[variable]
        return value, live

    def branches(arms, bindings, breaks):
        continuing = []
        for arm in arms:
            branch = bindings.copy()
            value, live = (block(arm, branch, breaks) if isinstance(arm, list)
                           else (expression(arm, branch, breaks), True))
            if live:
                continuing.append((value, branch))
        if continuing:
            for variable in bindings:
                bindings[variable] = combine([branch[variable] for _, branch in continuing])
        return combine([value for value, _ in continuing]), bool(continuing)

    def loop_body(statements, bindings):
        nonlocal uncertain_replacement
        condition = None
        if statements and statements[0].op == 'while_check':
            condition = statements[0].args[0]
            statements = statements[1:]
        head = bindings.copy()
        while True:
            state = head.copy()
            if condition is not None:
                expression(condition, state, None)
            exits = [(None, state.copy())] if condition is not None else []
            back_edges = []
            _, live = block(statements, state, (exits, back_edges))
            if live:
                back_edges.append(state)
            if any(state is None for state in back_edges):
                uncertain_replacement = True
                return None, True
            # Origins only grow across iterations, or become unknown.
            next_head = {
                variable: combine([head[variable], *(edge[variable] for edge in back_edges)])
                for variable in bindings
            }
            if head == next_head:
                break
            head = next_head
        if any(state is None for _, state in exits):
            uncertain_replacement = True
        elif exits:
            for variable in bindings:
                bindings[variable] = combine([state[variable] for _, state in exits])
        return combine([value for value, _ in exits]), bool(exits)

    def block(statements, bindings, breaks):
        nonlocal uncertain_replacement
        tail = None
        for statement in statements:
            op, args = statement.op, statement.args
            if op == 'var':
                variable, initializer = args
                bindings[variable] = expression(initializer, bindings, breaks)
            elif op == 'assign':
                variable, initializer = args
                value = expression(initializer, bindings, breaks)
                if value is not None and value[0] == 'owner':
                    bindings[variable] = value
                elif initializer[0] in ('await', 'if_expr', 'scope', 'loop_expr', 'value_match'):
                    # An unresolved expression can hide an allocation receipt.
                    uncertain_replacement = True
            elif op == 'return':
                returned.append(expression(args[0], bindings, breaks))
                return None, False
            elif op == 'break':
                value = expression(args[0], bindings, breaks)
                if breaks is not None:
                    breaks[0].append((value, bindings.copy()))
                return None, False
            elif op == 'continue':
                if breaks is not None:
                    breaks[1].append(bindings.copy())
                return None, False
            elif op == 'if':
                expression(args[0], bindings, breaks)
                if not branches(args[1:], bindings, breaks)[1]:
                    return None, False
            elif op == 'scope':
                if not scoped_block(args[1], bindings, breaks)[1]:
                    return None, False
            elif op in ('loop', 'while'):
                if not loop_body(args[0], bindings)[1]:
                    return None, False
            elif op == '<-' and not statement.terminated:
                tail = bindings.get(args[0])
            elif op == 'if_yield':
                tail = expression(args[0], bindings, breaks)
            else:
                unknown_paths(args, breaks)
        return tail, True

    tail, continuing = block(body, inputs.copy(), None)
    if continuing:
        returned.append(tail)
    value = combine(returned)
    result = value[1] if not uncertain_replacement and value is not None and value[0] == 'owner' else all_captures
    cache[name] = result
    return result


class _WidenUtf8Loop(Exception):
    def __init__(self, key, additions):
        self.key = key
        self.additions = additions


def lower_async_function(node, error, functions, warn, enable_threads, result_parameters_cache, array_c_type, frame_slots=None,
                         *, sync_contracts=None, sync_bridge=None, struct_layouts=None, enum_layouts=None,
                         local_parameters=frozenset(), variant_name=None, specialize=None, inline_layouts=None):
    # Each retry starts with fresh lowering state. Only finite sets of source
    # names survive, so no emitted frame member or cleanup is duplicated.
    node = expand_reference_return_branches(node)
    hints = {}
    while True:
        warnings = []
        slots = {}
        loop_activity = set()
        task_activity = set()
        returned_handle_pools = set()
        returned_handle_borrows = set()
        returned_handle_output_borrows = set()
        try:
            result = _lower_async_function(node, error, functions, lambda *args: warnings.append(args),
                                           enable_threads, result_parameters_cache, array_c_type, hints, slots,
                                           sync_contracts or {}, sync_bridge, struct_layouts or {}, enum_layouts or {},
                                           local_parameters, variant_name, specialize, inline_layouts or {},
                                           loop_activity, task_activity, returned_handle_pools, returned_handle_borrows,
                                           returned_handle_output_borrows)
        except _WidenUtf8Loop as request:
            entry = hints.setdefault(request.key, {})
            changed = False
            for name, additions in request.additions.items():
                previous = entry.get(name, ())
                widened = tuple(dict.fromkeys((*previous, *additions)))
                changed |= widened != previous
                entry[name] = widened
            if not changed:
                raise error('analyse des provenances de boucle async sans progression')
            continue
        if frame_slots is not None:
            for name, count in slots.items():
                frame_slots[name] = max(frame_slots.get(name, 0), count)
        node.async_loop_activity.update(loop_activity)
        node.async_task_activity.update(task_activity)
        node.async_returned_handle_pools.update(returned_handle_pools)
        node.async_returned_handle_borrows.update(returned_handle_borrows)
        node.async_returned_handle_output_borrows.update(returned_handle_output_borrows)
        for warning in warnings:
            warn(*warning)
        return result


def _lower_async_function(node, error, functions, warn, enable_threads, result_parameters_cache, array_c_type,
                          utf8_loop_hints, frame_slots, sync_contracts, sync_bridge, struct_layouts, enum_layouts,
                          local_parameters, variant_name, specialize, inline_layouts, loop_activity, task_activity,
                          returned_handle_pools, returned_handle_borrows, returned_handle_output_borrows):
    from functools import partial
    capture_type = partial(capture_ctype, structures=struct_layouts)
    from handle_types import HandleDefinitions, public_async_signature, public_signature
    from hashmap_syntax import (map_types, scalar_layout as map_scalar_layout, supports_capture as map_capture,
                                numeric_handle_element as map_handle_element, value_layout as map_value_layout)
    aggregate_layouts = struct_layouts | enum_layouts
    def mutex_structure_payload(typ):
        return typ in pool_structures

    def guard_roots(loans):
        return {loan_root(target) for target, _ in loans
                if mutex_payload(collection_types.get(loan_root(target)), GUARD_TYPES)}

    def guarded_field_owner(loans, line, *, injected=False):
        guards = guard_roots(loans)
        if not guards:
            return None
        if len(guards) == 1:
            guard, = guards
            if any(isinstance(target, tuple) and loan_root(target) == guard and target[1]
                   for target, _ in loans):
                fail(line, 'remplacement de dépendance gardée : charge entière requise')
            key = ('mutex_guard', guard)
            locked = active_loans.get(key, ())
            if len(locked) == 1:
                owner, _ = locked[0]
                if injected and parameter_modes.get(owner) == 'ref' and mutex_payload(reference_types.get(owner)):
                    return owner
                if (references.get(owner) == 'owned' and owner not in parameter_modes
                        and owner not in consumed and not any(
                            loan_root(target) == owner and mode not in ('storage', 'shared_target', 'stored_mut_target')
                            for other, held in active_loans.items() if other != key
                            for target, mode in held)):
                    return owner
        fail(line, 'remplacement de dépendance gardée : mutex local sans autre emprunt requis')

    def binding_depth(name):
        return next((depth for depth in reversed(range(len(scopes))) if name in scopes[depth][0]), -1)
    functions = HandleDefinitions(functions, structures=aggregate_layouts)
    name, parameters, result, body = node.args
    from async_result_storage import result_storage, pool_result_graph
    output_plan = result_storage(node, local_parameters) if node.result_storage else None

    def fail(line, message):
        raise error(f'ligne {line}: {message}')

    if output_plan and output_plan.mixed:
        fail(node.line, 'retours incompatibles : valeur locale T et allocation A<T>')
    if output_plan and output_plan.destination and output_plan.owned_fields and pool_result_graph(node) is None:
        fail(node.line, 'prototype : destination du résultat local async avec champs propriétaires non raccordée')

    scalar_sync_types = {('scalar', 'Int'): 'int', ('bool', 'bool'): 'int', ('byte', 'u8'): 'uint8_t',
                         ('char', 'char'): 'CrustChar'}
    scalar_sync_types.update({(mode, typ): EXTRA_C_TYPES[mode] for mode, typ in EXTRA_MODES.items()})
    reference_sync_types = {('ref', 'Int'): 'int *', ('mut', 'Int'): 'int *', ('mut', 'u8'): 'uint8_t *'}
    reference_sync_types.update({(mode, typ): f'{ctype} *'
                                 for typ, ctype in EXTRA_C_TYPES.items() for mode in ('ref', 'mut')})
    reference_sync_types.update({(mode, typ): 'Cell *'
        for params in [*(definition.args[1] for definition in functions.values()),
                       *(contract.parameters for contract in sync_contracts.values())]
        for _, mode, typ in params if (mode == 'ref' and mutex_payload(typ)) or map_capture(mode, typ)})
    # Whole owned captures use the existing Cell graph and its destructor.
    # Owned graphs retain their source pools. Direct borrowed fields additionally
    # retain caller-side loans when the whole carrier moves into the task.
    from structure_shapes import async_structure_shapes
    shape_layouts = struct_layouts | {typ: tuple(field for fields in arms.values() for field in fields)
                                    for typ, arms in enum_layouts.items()}
    owned_structure_types, reference_structure_types = async_structure_shapes(shape_layouts)
    reference_structs = {typ: struct_layouts[typ] for typ in reference_structure_types if typ in struct_layouts}
    owned_structures = {typ: struct_layouts[typ] for typ in owned_structure_types if typ in struct_layouts}
    owned_enums = {typ: enum_layouts[typ] for typ in owned_structure_types if typ in enum_layouts}
    owned_aggregates = owned_structures.keys() | owned_enums.keys()
    reference_aggregates = reference_structs.keys() | owned_enums.keys()
    pool_structures = owned_structures | reference_structs

    def inline_vector_layout(typ, line):
        element = INLINE_VECTOR_ELEMENTS[typ]
        layout = struct_layouts.get(element)
        if layout is None or element not in owned_structures or any(
                kind != 'Int' and not kind.startswith(('&', 'A<')) for _, kind in layout):
            fail(line, 'prototype async : Vector de structure exige des champs représentés')
        return element, layout

    def check_handle_payload(typ, line):
        if typ in INLINE_VECTOR_ELEMENTS:
            inline_vector_layout(typ, line)
            return
        element = handle_vector_element(typ)
        if element is None:
            return
        layouts = {name: {'': layout} for name, layout in struct_layouts.items()} | enum_layouts
        if element not in ('Int', 'String', 'Vector<Int>', 'Vector<u8>') and element not in layouts:
            fail(line, f'type de charge inconnu dans {typ}')

    for _, _, typ in parameters:
        check_handle_payload(typ[5:-1] if typ.startswith('Pool<') else typ, node.line)
    reference_sync_types.update({(mode, typ): capture_type(mode, typ) for typ in reference_aggregates for mode in ('ref', 'mut')})
    view_sync_types = {(mode, VALUE_MODES[mode]): capture_type(mode) for mode in ASYNC_CAPTURE_VIEW_MODES}
    owned_numeric_types = tuple(typ for typ in FORMATS if typ != 'i32')
    owned_sync_types = {('owned', typ): 'Cell *' for typ in ('Int', *owned_numeric_types, 'String', 'Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS)}
    owned_join_sync_types = {(mode, typ): OWNED_WRAPPER_TYPES[mode]
                            for mode in ('join_owned', 'join_nested', *OWNED_JOIN_TYPES) for _, typ in owned_sync_types}
    pool_sync_types = {(mode, f'Pool<{typ}>'): 'Source *'
                       for mode in ('ref', 'mut') for _, typ in owned_sync_types}
    owned_sync_types.update({('owned', typ): 'Cell *' for typ in owned_aggregates})
    owned_join_sync_types.update({(mode, typ): OWNED_WRAPPER_TYPES[mode]
                                 for mode in ('join_owned', 'join_nested', *OWNED_JOIN_TYPES) for typ in owned_aggregates})
    owned_join_sync_types.update({('handle_option', typ): 'VectorHandleResult'
                                 for typ in ('Int', 'String', 'Vector<Int>', 'Vector<u8>', *owned_aggregates)})
    owned_join_sync_types.update({('buffered_handle_exchange', typ): 'VectorHandleResult'
        for element in ('Int', 'String', 'Vector<Int>', 'Vector<u8>', *owned_aggregates)
        for typ in (exchange_type(element), exchange_type(element, True))})
    owned_join_sync_types.update({(mode, option_payload_type(mode)): ctype for mode, ctype in OPTION_JOIN_CTYPES.items()})
    owned_join_sync_types.update({(mode, exchange_payload_type(mode)): ctype for mode, ctype in EXCHANGE_JOIN_CTYPES.items()})
    pool_sync_types.update({(mode, f'Pool<{typ}>'): 'Source *'
                            for mode in ('ref', 'mut') for typ in (*pool_structures, *owned_enums)})
    owned_output_types = owned_sync_types | {('owned', typ): 'Cell *' for typ in reference_structs}
    output_join_types = owned_join_sync_types | {(mode, typ): OWNED_WRAPPER_TYPES[mode]
                                               for mode in ('join_owned', 'join_nested', *OWNED_JOIN_TYPES) for typ in reference_structs}
    collection_sync_types = {(mode, typ): 'Cell *' for mode in ('ref', 'mut')
                             for typ in (*HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS)}
    sync_types = scalar_sync_types | reference_sync_types | view_sync_types | owned_sync_types | owned_join_sync_types | pool_sync_types
    output_types = sync_types | owned_output_types | output_join_types
    sync_types |= collection_sync_types
    handle_sync_types = {contract.result_type: 'CrustExecution' for contract in sync_contracts.values()
                         if contract.result_type[0] == 'execution'
                         and (public_signature(contract.result_type[1], aggregate_layouts) is not None
                              or contract.result_type[1] in functions)}
    task_sync_types = {contract.result_type: 'CrustTask *' for contract in sync_contracts.values()
                       if contract.result_type[0] == 'task' and contract.result_type[1] in functions}
    task_argument_types = {('task', typ): 'CrustTask *' for contract in sync_contracts.values()
                           for _, mode, typ in contract.parameters if mode == 'task' and typ in functions}
    sync_types.update(task_argument_types)
    execution_argument_types = {('execution', typ): 'CrustExecution' for contract in sync_contracts.values()
        for _, mode, typ in contract.parameters if mode == 'execution'
        and (typ in functions or public_signature(typ, aggregate_layouts) is not None)}
    sync_types.update(execution_argument_types)

    def pool_argument(argument, mode, typ, line):
        local = argument[1] in local_pools if argument[0] in ('name', 'ref', 'mut') else False
        expected = mode if local else 'name'
        if argument[0] != expected or pool_types.get(argument[1]) != typ:
            fail(line, f'argument {typ} : passer le nom du pool déjà emprunté')
        name = argument[1]
        if mode == 'mut' and references[name] != 'mut':
            fail(line, 'allouer exige un emprunt mutable du pool')
        check_access(name, line, write=mode == 'mut')
        return f'frame->{fields[name]}', [(name, mode), *received_refs.get(name, ())]

    def pool_storage(name):
        return frozenset({name}) if name in local_pools else pool_alias_origins.get(name, frozenset())

    def storage_of(value):
        for name, member in fields.items():
            if value == f'frame->{member}':
                return storage_bindings.get(name, frozenset())
        return storage_values.get(value, frozenset())

    def keep_storage(value, origins):
        storage_values[value] = storage_values.get(value, frozenset()) | frozenset(origins)

    def stored_field_path(field):
        # Contract projections use both '.child/.view' and '.child/view'.
        # They denote the same owned descent followed by a member access.
        return tuple(component for component in field.replace('/', '.').split('.') if component)

    def owned_borrow_fields(typ):
        from array_syntax import owned_reference_paths
        return tuple(owned_reference_paths({name: {'': layout} for name, layout in struct_layouts.items()} | enum_layouts, typ))

    def concrete_borrow_field(typ, path):
        """Resolve a finite stored path, even when its types repeat."""
        element = vector_payload_element(typ)
        if element is not None and path and path[0] == '[]':
            child = concrete_borrow_field(element, path[1:])
            return ('[]/' + child[0], child[1]) if child is not None else None
        layouts = {name: {'': layout} for name, layout in struct_layouts.items()} | enum_layouts
        for arm, members in layouts.get(typ, {}).items():
            for name, declared in members:
                key = arm + '.' + name
                head = stored_field_path(key)
                if path[:len(head)] != head:
                    continue
                tail = path[len(head):]
                if not tail and declared.startswith('&'):
                    return key, declared
                if tail and declared.startswith('A<'):
                    child = concrete_borrow_field(declared[2:-1], tail)
                    if child is not None:
                        return key + '/' + child[0], child[1]
        return None

    def borrowed_field_type(typ, path):
        field = concrete_borrow_field(typ, path)
        return field[1] if field is not None else None

    def move_stored_fields(source, destination):
        invalidate_guarded_receipts(source)
        invalidate_guarded_receipts(destination)
        root = active_loans.pop(('storage_root', source, ()), None)
        prior_root = active_loans.pop(('storage_root', destination, ()), ())
        if root is not None:
            active_loans['storage_root', destination, ()] = list(dict.fromkeys((*prior_root, *root)))
        guard = active_loans.pop(('mutex_guard', source), None)
        if guard is not None:
            active_loans['mutex_guard', destination] = guard
        if source in inline_vector_items:
            inline_vector_items[destination] = inline_vector_items.pop(source)
        for key in list(active_loans):
            if isinstance(key, tuple) and key[0] in ('stored_field', 'owned_storage') and key[1] == source:
                target = (key[0], destination, key[2])
                held = active_loans.pop(key)
                active_loans[target] = list(dict.fromkeys((*active_loans.get(target, ()), *held)))

    def summary_borrowed_fields(summary):
        fields = {}
        def collect(value, prefix):
            for field, targets in getattr(value, 'borrowed_fields', getattr(value, 'fields', ())):
                key = prefix + field
                fields[key] = fields.get(key, frozenset()) | targets
            for field, child in value.owned_fields:
                collect(child, prefix + field + '/')
        collect(summary, '')
        return tuple(fields.items())

    def retain_result_fields(holder, summary_fields, argument_loans, line, argument_fields=None):
        for field, targets in summary_fields:
            held = []
            for target in targets:
                if target.kind == 'field_parameter' and argument_fields is not None:
                    captured = argument_fields.get((target.parameter, target.field))
                    if captured is None:
                        fail(line, 'résultat struct async : champ emprunté absent de la capture')
                    held.extend(captured)
                elif target.kind in ('parameter', 'exclusive_join_parameter'):
                    held.extend(argument_loans[target.parameter])
                else:
                    fail(line, 'résultat struct async : cible empruntée sans paramètre durable raccordé')
            active_loans[('stored_field', holder, stored_field_path(field))] = list(dict.fromkeys(held))

    def retain_vector_payload(receiver, incoming):
        element = vector_payload_element(collection_types[receiver])
        if collection_types[receiver] in INLINE_VECTOR_ELEMENTS:
            previous = inline_vector_items.get(receiver)
            if receiver not in inline_vector_items and not any(owned_capture_field_loans(receiver, collection_types[receiver]).values()):
                previous = ()
            payload = tuple(('stored_field', stored_field_path(field), tuple(held))
                            for field, held in owned_capture_field_loans(incoming, element).items())
            payload += tuple(('owned_storage', path, tuple(held))
                             for path, held in owned_storage_fields(incoming).items())
            set_vector_positions(receiver, (*previous, payload) if previous is not None else None)
        for field, held in owned_capture_field_loans(incoming, element).items():
            key = ('stored_field', receiver, ('[]', *stored_field_path(field)))
            install_field_change(key, list(dict.fromkeys((*active_loans.get(key, ()), *held))))
        if collection_types[receiver] in INLINE_VECTOR_ELEMENTS:
            for path, held in owned_storage_fields(incoming).items():
                key = ('owned_storage', receiver, ('[]', *path))
                install_field_change(key, list(dict.fromkeys((*active_loans.get(key, ()), *held))))

    def extract_vector_payload(receiver, result):
        for field, held in owned_capture_field_loans(receiver, collection_types[receiver]).items():
            path = stored_field_path(field)
            if path and path[0] == '[]':
                active_loans[('stored_field', result, path[1:])] = list(held)
        if collection_types[receiver] in INLINE_VECTOR_ELEMENTS:
            for path, held in owned_storage_fields(receiver).items():
                if path and path[0] == '[]':
                    active_loans[('owned_storage', result, path[1:])] = list(held)
                    keep_storage(result, (origin for origin, _ in held))

    def result_lock_loans(holder):
        return active_loans.get(('stored_field', holder, ('result_lock',)), ())

    def result_lock_roots():
        return {loan_root(target) for key, held in active_loans.items()
                if isinstance(key, tuple) and key[0] == 'stored_field' and key[2] == ('result_lock',)
                for target, _ in held}

    def check_result_lock_transfer(holder, line):
        if result_lock_loans(holder):
            fail(line, 'transfert d’un résultat portant un verrou hors de sa liaison locale non raccordé')

    def clear_stored_fields(holder):
        invalidate_guarded_receipts(holder)
        active_loans.pop(('storage_root', holder, ()), None)
        active_loans.pop(('mutex_guard', holder), None)
        inline_vector_items.pop(holder, None)
        for key in list(active_loans):
            if isinstance(key, tuple) and key[0] in ('stored_field', 'owned_storage') and key[1] == holder:
                del active_loans[key]

    # Immutable per-slot loan sets; an unknown layout retains the aggregate
    # loans conservatively. Branch snapshots below preserve these positions.
    inline_vector_items = {}

    def owned_storage_fields(value):
        holder = next((name for name, member in fields.items() if value == f'frame->{member}'), value)
        return {key[2]: list(origins) for key, origins in active_loans.items()
                if isinstance(key, tuple) and key[0] == 'owned_storage' and key[1] in (value, holder)}

    def owned_capture_field_loans(value, typ):
        holder = next((name for name, member in fields.items() if value == f'frame->{member}'), value)
        result = {}
        for field, _, _ in owned_borrow_fields(typ):
            path = stored_field_path(field)
            result[field] = list(active_loans.get(('stored_field', value, path),
                active_loans.get(('stored_field', holder, path), initial_stored_field_loans(holder, path))))
        # Constructed owners carry deeper paths than the finite type template.
        # Move every such concrete loan together with the owned child.
        for key, loans in active_loans.items():
            if isinstance(key, tuple) and key[0] == 'stored_field' and key[1] in (value, holder):
                field = concrete_borrow_field(typ, key[2])
                if field is not None:
                    result[field[0]] = list(loans)
        return result

    def publish_returned_result_lock(holder, line):
        key = ('stored_field', holder, ('result_lock',))
        held = active_loans.get(key)
        if not held:
            return
        indexes = {parameter: index for index, (parameter, mode, _) in enumerate(parameters)
                   if mode in ('ref', 'mut')}
        returned = set()
        for target, _ in held:
            root = loan_root(target)
            if root in indexes:
                returned.add(indexes[root])
            elif root not in received_refs:
                fail(line, 'retour de verrou : l’instance doit provenir d’un paramètre emprunté')
        if not returned:
            fail(line, 'retour de verrou : origine de l’instance introuvable')
        node.async_returned_lock_parameters.update(returned)
        del active_loans[key]

    def require_durable_storage(value, depth, line, *, local_receiver=False):
        if local_receiver:
            held = result_lock_loans(value)
            if held:
                remaining = surviving_reference_loans(held, depth, line)
                if not remaining:
                    fail(line, 'transfert de verrou : aucune origine durable dans le receveur')
                active_loans[('stored_field', value, ('result_lock',))] = remaining
        else:
            check_result_lock_transfer(value, line)
        leaving = {name for scope in scopes[depth:] for name in scope[0] if name in local_pools}
        if storage_of(value) & leaving:
            fail(line, 'transfert refusé : le pool local ne survit pas au receveur')
        for key, held in active_loans.items():
            if isinstance(key, tuple) and key[:2] == ('stored_field', value) and key[2][:1] == ('map_items',):
                surviving_reference_loans(held, depth, line)

    def implicit_stack():
        existing = next((name for name in scopes[-1][0] if name in implicit_stacks), None)
        if existing is not None:
            return existing
        storage = temporary('Source')
        name = '\0local-stack-' + storage
        local_pools[name] = storage
        implicit_stacks.add(name)
        scopes[-1][0][name] = None
        steps.append(f'{storage} = source_stack(16 * 1024 * 1024);')
        return name

    def inline_vector_placement_inputs():
        known = {name: ('inline_vector', typ) for name, typ in collection_types.items()
                 if typ in INLINE_VECTOR_ELEMENTS and name not in consumed}
        known.update((name, ('inline_vector_pool', typ[5:-1])) for name, typ in pool_types.items()
                     if typ[5:-1] in INLINE_VECTOR_ELEMENTS)
        return known

    def place_local_result(expr, *, destination=None):
        from async_local_placement import result_constructors
        locals_ = {name: collection_types.get(name, 'Int') for name, origins in storage_bindings.items()
                   if origins & implicit_stacks and name not in consumed}
        locals_.update(inline_vector_placement_inputs())
        constructors = result_constructors(expr, sync_contracts, locals_, async_functions=functions)
        unplaced = [constructor for constructor in constructors if id(constructor) not in local_destinations]
        if unplaced:
            destination = destination or implicit_stack()
            for constructor in unplaced:
                local_destinations[id(constructor)] = destination

    def place_local_assignments(body):
        from async_local_placement import result_constructors
        targets = {name: next(iter(origins & implicit_stacks)) for name, origins in storage_bindings.items()
                   if name not in consumed and references.get(name) == 'owned' and len(origins & implicit_stacks) == 1}
        if not targets:
            return
        locals_ = {name: collection_types.get(name, 'Int') for name in targets}
        locals_.update(inline_vector_placement_inputs())
        plans = result_constructors(('scope', '', body), sync_contracts, locals_, assigned_to=targets,
                                    async_functions=functions)
        depths = {name: depth for depth, scope in enumerate(scopes) for name in scope[0] if name in implicit_stacks}
        # Captured local storage and the output destination are external to
        # every scope of this frame. A replacement must not shorten that plan.
        for storage in implicit_stacks:
            depths.setdefault(storage, -1)
        for name, constructors in plans.items():
            for constructor in constructors:
                previous = local_destinations.get(id(constructor))
                if previous is None or depths.get(targets[name], len(scopes)) < depths.get(previous, len(scopes)):
                    local_destinations[id(constructor)] = targets[name]

    def sync_method_call(expr):
        if expr[0] == 'method_call' and expr[1][0] == 'name':
            receiver = expr[1][1]
            typ = reference_types.get(receiver, collection_types.get(receiver))
            if typ in reference_structs:
                symbol = typ + '.' + expr[2]
                if symbol in sync_contracts:
                    mode = sync_contracts[symbol].parameters[0][1]
                    argument = (mode, receiver) if references.get(receiver) == 'owned' and mode in ('ref', 'mut') else expr[1]
                    return ('call', symbol, [argument, *expr[3]])
        return expr

    def sync_signature(expr):
        expr = sync_method_call(expr)
        if expr[0] == 'call' and expr[1] in sync_contracts:
            return sync_contracts[expr[1]].result_type
        return None

    def sync_borrow_argument(argument, mode, typ, line):
        if held := guard_borrow_argument(argument, mode, typ, line):
            return held
        if map_capture(mode, typ):
            name = argument[1]
            actual = references.get(name)
            compatible = (argument[0] == 'name' and (actual == 'mut' or actual == mode == 'ref')
                          or argument[0] == mode and actual == 'owned' and (mode == 'ref' or name in mutable))
            if not compatible or reference_types.get(name, collection_types.get(name)) != typ:
                fail(line, 'argument HashMap : emprunt nommé du mode et du type déclarés requis')
            reservation = 'mut' if actual == 'mut' else mode
            check_access(name, line, write=reservation == 'mut')
            return f'frame->{fields[name]}', [(name, reservation), *received_refs.get(name, ())]
        if vector_payload_element(typ) is not None:
            if argument[0] not in ('ref', 'mut', 'name', 'reborrow'):
                fail(line, 'argument Vector<A<Int>> : emprunt explicite requis')
            name = argument[1]
            actual = references.get(name)
            if collection_types.get(name) != typ:
                fail(line, 'argument Vector<A<Int>> : type incompatible')
            compatible = (actual == 'owned' and argument[0] == mode and (mode == 'ref' or name in mutable)
                          or actual in ('ref', 'mut') and (mode == 'ref' or actual == 'mut')
                          and (argument[0] == 'name' or argument[0] == 'reborrow' and argument[2] == mode))
            if not compatible:
                fail(line, 'argument Vector<A<Int>> : mode ou mutabilité incompatible')
            reservation = 'mut' if actual == 'mut' else mode
            check_access(name, line, write=reservation == 'mut')
            return f'frame->{fields[name]}', [(name, reservation), *received_refs.get(name, ())]
        if argument[0] in ('ref', 'mut'):
            name = argument[1]
            actual = references.get(name, 'scalar')
            actual_type = reference_types.get(name, collection_types.get(name,
                'Bool' if name in boolean_bindings else SCALAR_TYPES.get(inline_scalar_mode(name))))
            if (name not in fields or name in arrays or actual not in ('scalar', 'owned')
                    or argument[0] != mode or actual_type != typ or mode == 'mut' and name not in mutable):
                fail(line, 'argument emprunté : type, mode ou mutabilité incompatible ; réemprunter une référence avec &* ou &mut *')
            check_access(name, line, write=mode == 'mut')
            member = f'frame->{fields[name]}'
            if actual == 'owned' and typ in EXTRA_C_TYPES:
                pointer = f'({EXTRA_C_TYPES[typ]} *){member}->fields'
            elif typ in aggregate_layouts or mutex_payload(typ):
                pointer = member
            else:
                pointer = f'&({value_place(name)})'
            loans = [(name, mode)]
        else:
            pointer, loans, shape = reference_value(argument, line)
            if (shape[1] != typ or mode == 'mut' and shape[0] != 'mut'
                    or argument[0] in ('reborrow', 'ref_expr', 'mut_expr') and shape[0] != mode):
                fail(line, 'argument emprunté : type ou mode incompatible')
            active_loans.pop(id(loans), None)
        if typ in struct_layouts:
            pointer = f'structure_reference_for((CrustStructureView){{0}}, {pointer})'
        return pointer, loans

    def release_sync_argument_loans(following):
        # An earlier scalar sub-call can finish a named reference's last use.
        # Keep remaining arguments, enclosing statement tails and loop
        # back-edges in the liveness calculation. Prepared argument loans are
        # not named scope bindings and therefore cannot expire here.
        depth = len(scopes) - 1
        tail = statement_tails.get(depth, ()) if following is None else following
        remaining = [item for owner, arguments in argument_tails if owner == depth for item in arguments]
        for owner_depth, scope in enumerate(scopes):
            for name, (held, _) in scope[4].items():
                if not utf8_current_live(tail, name, earlier=remaining,
                                         owner_depth=owner_depth, owned=True):
                    active_loans.pop(id(held), None)

    def sync_owned_value(expr, line, *, following=None):
        if expr[0] in ('array_transfer', 'new_transfer'):
            return sync_owned_value(expr[1], line, following=following)
        if inline_vector_source(expr) is not None:
            return inline_vector_value(expr, line, following=following)
        if handle_remove_receiver(expr) is not None:
            return vector_remove_value(expr, line, following=following)
        if structure_copy_source(expr) is not None:
            return copy_structure_value(expr, line)
        if sync_signature(expr) in owned_output_types:
            return sync_call(expr, line, following=following, owned=True)[0]
        if expr[0] in ('new', 'new_enum'):
            return pool_new_value(expr, line, following=following)
        if expr[0] in ('down', 'move'):
            require_local_async_value(expr[1], line)
            kind, value = export_async_value(expr[1], (), line)
        elif expr[0] == 'await':
            prepared = None
            if computed_await(expr):
                kind, prepared = emit_computed_transfer(expr[1], line, following=following)
                if kind != 'task':
                    fail(line, 'allocation attendue : un handle rend un Result, pas une allocation directe')
            signature = functions[prepared[3]].args[2] if prepared is not None else await_signature(expr)
            if signature not in owned_output_types:
                fail(line, 'allocation attendue : résultat async de type incompatible')
            return await_task(expr, line, returns_value=True, owned=True, prepared=prepared)
        else:
            kind, value = emit_computed_transfer(expr, line, following=following)
        if kind != 'owned':
            fail(line, 'transfert synchrone : une allocation possédée est requise')
        return value

    def owned_join_value(expr, line, *, following=None, prepared=None):
        """Consume a Result expression through the same paths as a named result.

        Callers enforce the transfer marker (or a consuming match). This
        routine preserves the actual payload type and its storage dependencies;
        awaiting a task returns T, whereas awaiting a handle wraps T in Result.
        """
        if expr[0] in ('down', 'move') and is_owned_join(expr[1], nested=True):
            if expr[0] == 'down':
                require_local_async_value(expr[1], line)
            return consume_owned_join(expr[1], line)
        if expr[0] in ('down', 'move'):
            fail(line, 'argument de résultat propriétaire : type incompatible')
        if sync_signature(expr) in output_join_types:
            mode, _ = sync_signature(expr)
            value, _ = sync_call(expr, line, following=following, owned=True)
            return value, owned_wrapper_payload(mode, sync_signature(expr)[1]), None
        if expr[0] in ('array_buffered_replace', 'array_buffered_try_push'):
            payload = 'rejected_allocation' if expr[0] == 'array_buffered_try_push' else 'exchange_allocation'
            return handle_replace_value(expr, line, following=following), payload, None
        if expr[0] == 'array_handle_option_pop':
            return handle_pop_value(expr, line, following=following), 'optional_allocation', None
        if expr[0] == 'await':
            if awaits_execution(expr):
                result = execution_await(expr, line)
            else:
                if prepared is None and computed_await(expr):
                    prepared = emit_computed_transfer(expr[1], line, following=following)
                if prepared is not None and prepared[0] == 'execution':
                    result = execution_await(expr, line, prepared=prepared[1])
                else:
                    if prepared is not None and prepared[0] != 'task':
                        fail(line, '.await exige une tâche ou un handle')
                    signature = (functions[prepared[1][3]].args[2] if prepared is not None
                                 else await_signature(expr))
                    if signature is None or signature[0] not in JOIN_PAYLOADS:
                        fail(line, 'expression Result propriétaire : type incompatible')
                    value = await_task(expr, line, returns_value=True, joined=True,
                                       prepared=prepared[1] if prepared is not None else None)
                    result = value, owned_wrapper_payload(*signature), None
            if result[1] not in OWNED_WRAPPER_PAYLOADS.values():
                fail(line, 'expression Result propriétaire : type incompatible')
            return result
        kind, value = emit_computed_transfer(expr, line, following=following)
        if kind not in OWNED_WRAPPER_PAYLOADS:
            fail(line, 'expression Result propriétaire : type incompatible')
        return value

    def guard_borrow_argument(argument, mode, typ, line):
        if argument[0] != 'reborrow':
            return None
        name = argument[1]
        guard = collection_types.get(name)
        if (payload := mutex_payload(guard, GUARD_TYPES)) is None:
            return None
        if payload != typ or (mode, typ) not in reference_sync_types or argument[2] != mode:
            fail(line, 'réemprunt de garde : type ou mode incompatible')
        if mode == 'mut' and name not in mutable:
            fail(line, 'réemprunt de garde : let mut est requis')
        check_access(name, line, write=mode == 'mut')
        value = f'crust_guard_value(frame->{fields[name]}, {int(guard.startswith("Async"))})'
        if mutex_structure_payload(typ):
            return f'structure_whole_view((Cell *){value})', [(name, mode)]
        return f'({reference_sync_types[mode, typ]}){value}', [(name, mode)]

    def pool_new_value(expr, line, *, following=None, label='async allocation'):
        if expr[0] == 'new_enum' and expr[1] is None and expr[2] in (*pool_structures, *owned_enums):
            return pool_structure_value(expr, line, following=following, label=label)
        pool_type = pool_types.get(expr[1])
        if pool_type is None:
            fail(line, 'prototype : création directe dans un état exige un pool injecté')
        if pool_type[5:-1] in pool_structures or pool_type[5:-1] in owned_enums:
            return pool_structure_value(expr, line, following=following, label=label)
        typ = pool_type[5:-1] if expr[4:] == ('pool_default',) else expr[3]
        primitive = numeric_type(typ)
        if pool_type != f'Pool<{typ}>' or (primitive is None and expr[4:] != ('pool_default',)):
            fail(line, f'création directe async : type incompatible avec {pool_type}')
        source, loans = pool_argument(('mut' if expr[1] in local_pools else 'name', expr[1]), 'mut', pool_type, line)
        active_loans[id(loans)] = loans
        try:
            if primitive not in (None, 'i32'):
                initial, actual = infer_scalar_value(expr[2], line, following=following)
                if actual != typ:
                    fail(line, f'création directe async : valeur {typ} requise')
                value = temporary(FORMATS[primitive].c_type)
                steps.append(f'{value} = {initial};')
            else:
                value = expression(expr[2], line, following=following)
        finally:
            active_loans.pop(id(loans), None)
        cell = temporary('Cell *')
        # Labels are diagnostics only; the pointer retains its source at runtime.
        if typ == 'Int':
            factory = f'cell_new({source}, {value}, "{label}")'
        elif primitive is not None:
            factory = f'cell_new({source}, 0, "{label}")'
        elif typ == 'String':
            factory = f'string_new({source}, UINT64_C({region_limits[-1]}), "{label}")'
        elif is_handle_vector(typ):
            factory = f'vector_new_handles({source}, UINT64_C({region_limits[-1]}), "{label}")'
        elif typ in INLINE_VECTOR_ELEMENTS:
            _, layout = inline_vector_layout(typ, line)
            size = structure_offset(layout, len(layout)) if layout else 'sizeof(int)'
            factory = (f'vector_new({source}, UINT64_C({region_limits[-1]}), {size}, '
                       f'_Alignof(int), 0, "{label}")')
        else:
            element = 'int' if typ == 'Vector<Int>' else 'uint8_t'
            factory = (f'vector_new({source}, UINT64_C({region_limits[-1]}), sizeof({element}), '
                       f'_Alignof({element}), 0, "{label}")')
        steps.append(f'{cell} = {factory};')
        if primitive not in (None, 'i32'):
            steps.append(f'cell_store_numeric({cell}, 0, {FORMATS[primitive].c_type}, {value});')
        owned_result_types[cell] = typ
        keep_storage(cell, pool_storage(expr[1]))
        if typ in INLINE_VECTOR_ELEMENTS:
            inline_vector_items[cell] = ()
            active_loans[('owned_storage', cell, ('vector_backing',))] = [
                (origin, 'storage') for origin in pool_storage(expr[1])]
        return cell

    def structure_offset(layout, index):
        # Same packed payload layout as cell_load/store (which use memcpy).
        return ' + '.join(field_size(kind) for _, kind in layout[:index]) or '0'

    def structure_copy_source(expr):
        if expr[0] == 'struct_copy' and expr[1] in pool_types:
            return expr[2]
        if expr[0] == 'array_copy' and expr[1][0] == 'name':
            name = expr[1][1]
            if reference_types.get(name, collection_types.get(name)) in pool_structures:
                return name
        return None

    def inline_vector_source(expr):
        if expr[0] == 'array_copy' and expr[1][0] == 'array_index':
            receiver, index = expr[1][1:]
            remove = False
        elif expr[0] == 'method_call' and expr[2] == 'remove' and len(expr[3]) == 1:
            receiver, index, remove = expr[1], expr[3][0], True
        else:
            return None
        if receiver[0] == 'name' and collection_types.get(receiver[1]) in INLINE_VECTOR_ELEMENTS:
            return receiver[1], index, remove
        return None

    def inline_vector_value(expr, line, *, following=None):
        receiver, index_expr, remove = inline_vector_source(expr)
        element, layout = inline_vector_layout(collection_types[receiver], line)
        if not remove and any(kind.startswith(('&mut ', 'A<')) for _, kind in layout):
            fail(line, 'structure non copiable : champ propriétaire ou référence mutable')
        if remove and not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable):
            fail(line, 'remove exige un Vector mutable')
        if following is not None:
            release_statement_loans(following, earlier=(expr,))
        check_access(receiver, line, write=remove)
        loan = [(receiver, 'mut' if remove else 'ref')]
        active_loans[id(loan)] = loan
        try:
            value = expression(index_expr, line)
            index = temporary('int')
            steps.append(f'{index} = {value};')
        finally:
            del active_loans[id(loan)]
        if following is not None:
            release_statement_loans(following)
        check_access(receiver, line, write=remove)
        destination = local_destinations.get(id(expr)) or implicit_stack()
        source = '&' + local_pools[destination]
        layout_name = local_layouts.setdefault(element, f'{prefix}_local_layout_{len(local_layouts)}')
        size = structure_offset(layout, len(layout))
        cell = temporary('Cell *')
        steps.append(f'{cell} = local_cell_new({source}, &{layout_name}, {size}, "async element");')
        data = f'{cell}->fields' if layout else '&(int){0}'
        operation = 'vector_remove' if remove else 'vector_read'
        steps.append(f'{operation}(frame->{fields[receiver]}, {index}, {data});')
        owned_result_types[cell] = element
        keep_storage(cell, frozenset({destination}))
        slots = inline_vector_items.get(receiver)
        literal = index_expr[1] if index_expr[0] == 'int' else None
        if slots is not None and literal is not None and 0 <= literal < len(slots):
            for category, path, held in slots[literal]:
                active_loans[(category, cell, path)] = list(held)
                if category == 'owned_storage':
                    keep_storage(cell, (origin for origin, _ in held))
            if remove:
                set_vector_positions(receiver, slots[:literal] + slots[literal + 1:])
        else:
            extract_vector_payload(receiver, cell)
            if remove:
                set_vector_positions(receiver, None)
        return cell

    def copy_structure_value(expr, line):
        name = structure_copy_source(expr)
        if result_lock_loans(name) or any(result_lock_loans(loan_root(target)) for target, _ in received_refs.get(name, ())):
            fail(line, 'copie interdite : la structure maintient un verrou')
        typ = reference_types.get(name, collection_types.get(name))
        if typ not in pool_structures:
            fail(line, 'pool.copy exige une structure allouée')
        layout = pool_structures[typ]
        if any(kind.startswith('A<') or kind.startswith('&mut ') for _, kind in layout):
            fail(line, 'structure non copiable : champ propriétaire ou référence mutable')
        check_access(name, line, write=references.get(name) == 'mut')
        original = f'frame->{fields[name]}'
        origins = received_refs.get(name, ())
        storage = storage_of(original) | frozenset(
            source for target, _ in origins for source in storage_bindings.get(loan_root(target), ()))
        local = expr[0] != 'struct_copy' and bool(storage & implicit_stacks)
        if expr[0] == 'struct_copy':
            source, _ = pool_argument(('mut' if expr[1] in local_pools else 'name', expr[1]),
                                      'mut', f'Pool<{typ}>', line)
            storage = pool_storage(expr[1])
        elif local:
            destination = local_destinations.get(id(expr)) or implicit_stack()
            source = '&' + local_pools[destination]
            storage = frozenset({destination})
        else:
            source = f'structure_reference_for((CrustStructureView){{0}}, {original}).root->source'
            for origin in storage:
                check_access(origin, line, write=True)
        cell = temporary('Cell *')
        if local:
            layout_name = local_layouts.setdefault(typ, f'{prefix}_local_layout_{len(local_layouts)}')
            factory = f'local_cell_new({source}, &{layout_name}, {structure_offset(layout, len(layout))}, "async copy")'
        else:
            factory = (f'enum_new({source}, 0, "async copy")' if expr[0] == 'struct_copy'
                       else f'cell_new({source}, 0, "async copy")')
        steps.extend((f'{cell} = {factory};',
                      f'memcpy({cell}->fields, structure_view_address(structure_reference_for((CrustStructureView){{0}}, {original}), 0, {structure_offset(layout, len(layout))}), {structure_offset(layout, len(layout))});'))
        owned_result_types[cell] = typ
        keep_storage(cell, storage)
        for path, held in owned_capture_field_loans(original, typ).items():
            if origins:
                held = project_result_field_loans(origins, typ, stored_field_path(path))
            active_loans[('stored_field', cell, stored_field_path(path))] = list(held)
        return cell

    def pool_structure_value(expr, line, *, following=None, label='async allocation'):
        local = expr[0] == 'new_enum' and expr[1] is None
        pool_type = None if local else pool_types[expr[1]]
        typ = expr[2] if local else pool_type[5:-1]
        variant = expr[3] if expr[0] == 'new_enum' else ''
        if typ in owned_enums:
            if variant not in owned_enums[typ]:
                fail(line, 'construction enum : variante déclarée explicite requise')
            layout = owned_enums[typ][variant]
            arm_index = tuple(owned_enums[typ]).index(variant)
        else:
            layout, arm_index = pool_structures[typ], 0
        if expr[0] == 'new_enum':
            if expr[2] not in (None, typ) or typ not in owned_enums and variant != '':
                fail(line, 'construction : type incompatible avec le pool de structures')
            provided = expr[4]
        elif expr[4:] == ('pool_default',):
            provided = []
        else:
            fail(line, 'construction de structure : champs nommés requis')
        declared = dict(layout)
        names = [name for name, _ in provided]
        if len(names) != len(set(names)):
            fail(line, 'champ initialisé plusieurs fois')
        if set(names) - declared.keys():
            fail(line, f'champ inconnu dans {typ}')
        if typ in owned_enums and set(names) != declared.keys():
            fail(line, f'champs incorrects pour {typ}.{variant} : fournir tous les champs déclarés')
        values = {}
        for field, field_type in layout:
            if field not in names:
                if scalar_field_mode(field_type) is None:
                    fail(line, f"champ '{field}' : aucune valeur par défaut")
                values[field] = '0'
        if local:
            destination = local_destinations.get(id(expr)) or implicit_stack()
            source, loans = '&' + local_pools[destination], []
        else:
            source, loans = pool_argument(('mut' if expr[1] in local_pools else 'name', expr[1]), 'mut', pool_type, line)
        # Already evaluated owners must be cleaned if a later field suspends
        # or exits. Publish the complete object only after every field exists.
        owners, stored_fields, stored_storage = [], {}, {}
        root_storage = {destination} if local else pool_storage(expr[1])
        storage = set(root_storage)
        active_loans[id(loans)] = loans
        pending_capture_groups.append((len(scopes) - 1, owners, loans))
        argument_depth = len(argument_tails)
        try:
            for index, (field, operand) in enumerate(provided):
                argument_tails.append((len(scopes) - 1, [value for _, value in provided[index + 1:]]))
                field_type = declared[field]
                if scalar_field_mode(field_type) is not None:
                    value, actual = infer_scalar_value(operand, line)
                    if actual != ('Bool' if field_type == 'bool' else field_type):
                        fail(line, f"champ '{field}' : valeur {field_type} requise")
                    snapshot = temporary(FIELD_C_TYPES.get(field_type, 'int'))
                    steps.append(f'{snapshot} = {value};')
                elif reference_type(field_type) is not None:
                    mode, target_type = reference_type(field_type)
                    pointer, held = sync_borrow_argument(operand, mode, target_type, line)
                    descriptor = stored_reference_cell(pointer, held, line) if target_type == 'Int' else pointer
                    snapshot = temporary('Cell *' if target_type == 'Int' else 'CrustStructureView')
                    steps.append(f'{snapshot} = {descriptor};')
                    loans.extend(held)
                    stored_fields[(*((variant,) if variant else ()), *field.split('.'))] = list(held)
                else:
                    if operand[0] not in ('move', 'new_transfer', 'array_transfer'):
                        fail(line, f"champ '{field}' : transfert explicite <- requis")
                    value = sync_owned_value(operand, line)
                    if owned_result_types.get(value, 'Int') != field_type[2:-1]:
                        fail(line, f"champ '{field}' : {field_type} requis")
                    if storage_of(value) & implicit_stacks:
                        fail(line, 'un champ A<T> exige une allocation de pool, pas une valeur locale')
                    snapshot = temporary('Cell *')
                    steps.extend((f'{snapshot} = {value};', f'{value} = NULL;'))
                    owners.append(snapshot)
                    storage.update(storage_of(value))
                    path = (*((variant,) if variant else ()), *field.split('.'))
                    stored_storage[path] = [(origin, 'storage') for origin in storage_of(value)]
                    for suffix, origins in owned_storage_fields(value).items():
                        stored_storage[path + suffix] = origins
                    for path, held in owned_capture_field_loans(value, field_type[2:-1]).items():
                        stored_fields[(*((variant,) if variant else ()), *field.split('.'), *stored_field_path(path))] = held
                        loans.extend(held)
                    clear_stored_fields(value)
                values[field] = snapshot
                argument_tails.pop()
        finally:
            del argument_tails[argument_depth:]
            pending_capture_groups.pop()
            active_loans.pop(id(loans), None)
        cell = temporary('Cell *')
        if local:
            # Layout metadata must outlive the frame when its local result is
            # received by the caller. Emit immutable static metadata, not a
            # pointer into the producer's state slot.
            layout_key = (typ, variant) if typ in owned_enums else typ
            layout_name = local_layouts.setdefault(layout_key, f'{prefix}_local_layout_{len(local_layouts)}')
            steps.append(f'{cell} = local_cell_new({source}, &{layout_name}, '
                         f'{structure_offset(layout, len(layout))}, "{label}");')
        else:
            steps.append(f'{cell} = enum_new({source}, {arm_index}, "{label}");')
        for index, (field, field_type) in enumerate(layout):
            if field_type in FIELD_C_TYPES:
                steps.append(f'cell_store_numeric({cell}, {structure_offset(layout, index)}, '
                             f'{FIELD_C_TYPES[field_type]}, {values[field]});')
                continue
            helper = ('cell_store_int' if field_type == 'Int' else
                      'cell_store_view' if field_type.startswith('&') and field_type not in ('&Int', '&mut Int') else 'cell_store_ref')
            steps.append(f'{helper}({cell}, {structure_offset(layout, index)}, {values[field]});')
        for owner in owners:
            steps.append(f'{owner} = NULL;')
        owned_result_types[cell] = typ
        for path, held in stored_fields.items():
            active_loans[('stored_field', cell, path)] = held
        for path, origins in stored_storage.items():
            active_loans[('owned_storage', cell, path)] = origins
        active_loans['storage_root', cell, ()] = [(origin, 'storage') for origin in root_storage]
        keep_storage(cell, storage)
        return cell

    def stored_reference_cell(pointer, loans, line):
        """Select an existing allocation descriptor from statically known loans.

        No descriptor is invented for a raw pointer or an inline scalar. The
        referenced Cell must itself survive a field store beyond the C call.
        """
        candidates = []
        for target, mode in loans:
            if mode == 'storage':
                continue
            root, path = target if isinstance(target, tuple) else (target, ())
            if root in received_refs:
                # Its actual origins are also present in the prepared loans.
                continue
            if not path and parameter_modes.get(root) in ('ref', 'mut') and reference_types.get(root) == 'Int':
                index = next(i for i, (parameter, _, _) in enumerate(parameters) if parameter == root)
                node.cell_reference_parameters.add(index)
                candidates.append(f'frame->capture_cell_{index}')
                continue
            if not path and references.get(root) == 'owned' and root not in collection_types:
                candidates.append(f'frame->{fields[root]}')
                continue
            layout = reference_structs.get(reference_types.get(root, collection_types.get(root)))
            if path and layout is not None:
                selected = '.'.join(path)
                offset = []
                for field, typ in layout:
                    if field == selected and typ in ('&Int', '&mut Int'):
                        position = ' + '.join(offset) or '0'
                        key = root, tuple(path)
                        if root in parameter_modes:
                            if key not in initial_field_cells:
                                member = f'initial_field_cell_{len(initial_field_cells)}'
                                initial_field_cells[key] = member, position
                            candidates.append('frame->' + initial_field_cells[key][0])
                        else:
                            candidates.append(f'cell_load_ref(frame->{fields[root]}, {position})')
                        break
                    offset.append(field_size(typ))
                else:
                    fail(line, 'référence stockée : descripteur de la cible non disponible dans cet état')
                continue
            fail(line, 'référence stockée : descripteur de la cible non disponible dans cet état')
        candidates = list(dict.fromkeys(candidates))
        if not candidates:
            fail(line, 'référence stockée : aucune allocation cible suivie')
        selected = candidates[-1]
        for candidate in reversed(candidates[:-1]):
            selected = f'(({pointer}) == &({candidate})->value ? ({candidate}) : ({selected}))'
        return selected

    def projected_type(typ, path):
        remaining = iter(path)
        for component in remaining:
            if typ in enum_layouts:
                layout = enum_layouts[typ].get(component, ())
                component = next(remaining, None)
            else:
                layout = struct_layouts.get(typ, ())
            child = dict(layout).get(component, '')
            typ = child[2:-1] if child.startswith('A<') else None
        return typ

    def prepare_field_changes(summary, callee_parameters, argument_loans, line, argument_storage=None,
                              argument_fields=None, *, local_guard=False, guarded_holders=None):
        def holders_for(index):
            if guarded_holders and index in guarded_holders:
                return [(guarded_holders[index], ())]
            typ = callee_parameters[index][2]
            if guard_roots(argument_loans[index]) and not local_guard:
                fail(line, 'remplacement de dépendance gardée par une tâche enfant non raccordé')
            if owner := guarded_field_owner(argument_loans[index], line):
                if mutex_payload(collection_types[owner]) != typ:
                    fail(line, 'remplacement de dépendance gardée : charge entière requise')
                return [(owner, ())]
            holders = []
            for target, _ in argument_loans[index]:
                root, path = target if isinstance(target,tuple) else (target,())
                if root in received_refs:
                    continue
                holder_type = reference_types.get(root, collection_types.get(root))
                holder_type = projected_type(holder_type, path)
                if not (parameter_modes.get(root) == 'mut' or references.get(root) == 'owned' and root in mutable) or holder_type != typ:
                    fail(line,'prototype : dépendances de champs async exigent un porteur injecté')
                holders.append((root, path))
            if not holders:
                fail(line,'prototype : dépendances de champs async sans porteur suivi')
            return holders

        # Owned replacements carry their own borrowed descendants. Publish
        # those targets through the same field-effect path as a direct write.
        structure_changes = {index: dict(changes) for index, changes in summary.structure_fields}
        preserved_replacements = set()
        def replacement_fields(child, prefix):
            for field, targets in child.fields:
                yield prefix + '/' + field, targets
            for field, nested in child.owned_fields:
                yield from replacement_fields(nested, prefix + '/' + field)
        for index, field, child in summary.owned_field_writes:
            changes = structure_changes.setdefault(index, {})
            if any(candidate.kind == 'owned_field_input' for candidate in child.candidates):
                preserved_replacements.add((index, stored_field_path(field)))
            for path, targets in replacement_fields(child, field):
                changes[path] = changes.get(path, frozenset()) | targets
        # Vector writes publish the payload loans as well as the element pools.
        # [] denotes any live element, so adding a payload must retain the
        # previous alternatives until their removal is established separately.
        for index, payloads in summary.vector_write_payloads:
            changes = structure_changes.setdefault(index, {})
            preserved_replacements.add((index, ('[]',)))
            for child in payloads:
                for path, targets in replacement_fields(child, '[]'):
                    changes[path] = changes.get(path, frozenset()) | targets
        field_changes = []
        for index, changes in structure_changes.items():
            changes = changes.items()
            typ = callee_parameters[index][2]
            holders = holders_for(index)
            for field, targets in changes:
                path = stored_field_path(field)
                field_type = borrowed_field_type(typ, path)
                field_reference = reference_type(field_type or '')
                if field_reference is None or field_reference[1] not in ('Int', *EXTRA_C_TYPES, *reference_structs):
                    fail(line,'prototype : dépendances de champs async non raccordées')
                retained = []
                for target in targets:
                    if target.kind == 'parameter':
                        origins = argument_loans[target.parameter]
                    elif target.kind in ('field_parameter', 'detached_field_parameter'):
                        source_type = callee_parameters[target.parameter][2]
                        source_path = stored_field_path(target.field)
                        if reference_type(borrowed_field_type(source_type, source_path) or '') is None:
                            fail(line, 'prototype : dépendances de champs sources non partagées non raccordées')
                        captured = None if argument_fields is None else argument_fields.get((target.parameter, target.field))
                        origins = (captured if captured is not None else
                                   project_result_field_loans(argument_loans[target.parameter], source_type, source_path))
                    else:
                        fail(line,'prototype : dépendances de champs async projetées non raccordées')
                    for origin, mode in origins:
                        root, source_path = origin if isinstance(origin,tuple) else (origin,())
                        if root in received_refs:
                            continue
                        source_type = reference_types.get(root, collection_types.get(root))
                        contained_type = next((layout.typ for layout in inline_layouts.get(source_type, ())
                                               if layout.path == '.'.join(source_path)), None)
                        durable_type = (source_type == field_reference[1] if not source_path else
                                        contained_type == field_reference[1] or
                                        reference_type(borrowed_field_type(source_type, source_path) or '') is not None)
                        local_target = references.get(root) == 'owned' and (
                            contained_type == field_reference[1] if source_path else
                            collection_types.get(root, 'Int') == field_reference[1])
                        local_holder = all(references.get(holder) == 'owned' for holder, _ in holders)
                        captured_reference = parameter_modes.get(root) == 'owned' and source_path and durable_type
                        own_capability = field_reference[0] == 'mut' and any(
                            root == holder and source_path == (*prefix, *path) for holder, prefix in holders)
                        if not (parameter_modes.get(root) in ('ref','mut') and durable_type
                                or captured_reference or local_holder and local_target or own_capability):
                            fail(line,'remplacement de champ async : cible locale ou provenance non raccordée')
                        for holder, _ in holders:
                            if mutex_payload(collection_types.get(holder)) and (
                                    root == holder or binding_depth(root) > binding_depth(holder)):
                                fail(line, 'transfert refusé : cible empruntée non durable pour le mutex')
                        retained.append((origin,mode))
                if not retained:
                    fail(line,'remplacement de champ async : cible sans provenance durable')
                for holder, prefix in holders:
                    full_path = (*prefix, *path)
                    key = ('stored_field',holder,full_path)
                    preserves_input = len(holders) > 1 or any(
                        source == index and path[:len(replaced)] == replaced
                        for source, replaced in preserved_replacements)
                    old = active_loans.get(key, initial_stored_field_loans(holder,full_path)) if preserves_input else []
                    # An unchanged field alternative owns its input capability;
                    # it is not an outstanding reborrow of that same field.
                    current = [(origin, 'stored_mut_target' if field_reference[0] == 'mut'
                                and origin == (holder, full_path) else mode) for origin, mode in retained]
                    field_changes.append((key,list(dict.fromkeys((*old,*current)))))
        def input_storage(index):
            if argument_storage is not None:
                return argument_storage[index]
            return frozenset(origin for target, access in argument_loans[index]
                for origin in ((target,) if access == 'storage' else
                               pool_storage(loan_root(target)) | storage_bindings.get(loan_root(target), frozenset())))

        def replacement_storage(child, previous):
            origins = set()
            for candidate in child.candidates:
                if candidate.kind == 'owned_field_input':
                    origins.update(previous)
                elif candidate.kind in ('parameter', 'owned_projection', 'vector_element'):
                    origins.update(input_storage(candidate.parameter))
                elif candidate.kind == 'fresh' and candidate.source.kind in (
                        'source_parameter', 'allocation_parameter', 'allocation_field_parameter'):
                    origins.update(input_storage(candidate.source.index))
                else:
                    fail(line, 'remplacement de champ propriétaire async : source non durable ou non représentée')
            for _, nested in child.owned_fields:
                origins.update(replacement_storage(nested, previous))
            return frozenset(origins)

        for index, field, child in summary.owned_field_writes:
            holders = holders_for(index)
            for holder, prefix in holders:
                path = (*prefix, *stored_field_path(field))
                key = ('owned_storage', holder, path)
                previous = frozenset(origin for origin, _ in active_loans.get(key, ()))
                origins = replacement_storage(child, previous)
                if len(holders) > 1:
                    origins |= previous
                field_changes.append((key, [(origin, 'storage') for origin in origins]))
        for index, slots, exact, replacements, removals in summary.vector_writes:
            if callee_parameters[index][2] in INLINE_VECTOR_ELEMENTS:
                from array_syntax import (VECTOR_LAST_ITEM, last_handle_index,
                                          remaining_handle_positions, replace_handle_positions)
                vector_type = callee_parameters[index][2]
                element = vector_payload_element(vector_type)
                payloads = dict(summary.vector_write_payloads).get(index, ())
                has_dependencies = any(kind.startswith(('&', 'A<')) for _, kind in pool_structures.get(element, ()))

                def payload_loans(payload):
                    fields = []
                    for field, targets in summary_borrowed_fields(payload):
                        held = []
                        for target in targets:
                            if target.kind == 'field_parameter' and argument_fields is not None:
                                captured = argument_fields.get((target.parameter, target.field))
                                if captured is None:
                                    fail(line, 'insertion dans un vecteur : champ emprunté absent de la capture')
                                held.extend(captured)
                            elif target.kind in ('parameter', 'exclusive_join_parameter'):
                                held.extend(argument_loans[target.parameter])
                            else:
                                fail(line, 'insertion dans un vecteur : provenance d’emprunt non raccordée')
                        fields.append(('stored_field', stored_field_path(field), tuple(dict.fromkeys(held))))
                    for field, child in payload.owned_fields:
                        inherited = frozenset().union(*(input_storage(candidate.parameter)
                            for candidate in child.candidates if candidate.kind == 'owned_field_input'))
                        origins = replacement_storage(child, inherited) - implicit_stacks
                        fields.append(('owned_storage', stored_field_path(field),
                                       tuple((origin, 'storage') for origin in sorted(origins))))
                    return tuple(fields)

                payload_fields = [(payload.candidates, payload_loans(payload)) for payload in payloads]
                def input_slot(candidate):
                    source_index = candidate.parameter
                    if not has_dependencies:
                        return True, ()
                    source_type = callee_parameters[source_index][2]
                    sources = []
                    for target, access in argument_loans[source_index]:
                        root, path = target if isinstance(target, tuple) else (target, ())
                        typ = reference_types.get(root, collection_types.get(root))
                        if access != 'storage' and projected_type(typ, path) == source_type:
                            sources.append((root, path))
                    alternatives = []
                    if not sources:
                        if argument_fields is None:
                            fail(line, 'insertion dans un vecteur : provenance de la case source non raccordée')
                        alternatives.extend(('stored_field', stored_field_path(field)[1:], tuple(held))
                            for (parameter, field), held in argument_fields.items()
                            if parameter == source_index and stored_field_path(field)[:1] == ('[]',))
                        alternatives.append(('owned_storage', (), tuple((origin, 'storage')
                            for origin in sorted(input_storage(source_index) - implicit_stacks))))
                    precise = bool(sources)
                    for source, prefix in sources:
                        positions = inline_vector_items.get(source) if not prefix else None
                        offset = candidate.item_index
                        if offset == VECTOR_LAST_ITEM:
                            offset = last_handle_index(positions, candidate.excluded_items, candidate.tail_offset)
                        if positions is not None and offset is not None and 0 <= offset < len(positions):
                            alternatives.extend(positions[offset])
                        else:
                            precise = False
                            element_path = (*prefix, '[]')
                            alternatives.extend((key[0], key[2][len(element_path):], tuple(held))
                                for key, held in active_loans.items() if isinstance(key, tuple)
                                and key[0] in ('stored_field', 'owned_storage') and key[1] == source
                                and key[2][:len(element_path)] == element_path)
                    return precise, tuple(dict.fromkeys(alternatives))

                vector_inputs = {candidate: input_slot(candidate)
                                 for slot in (*slots, *(row for _, row in replacements))
                                 for candidate in slot if candidate.kind == 'vector_element'}
                holders = holders_for(index)
                for holder, prefix in holders:
                    depth = binding_depth(holder)
                    leaving = {name for scope in scopes[depth + 1 if references.get(holder) == 'owned' else 0:]
                               for name in scope[0] if name in local_pools}
                    grouped = {}
                    all_fields = [fields for _, fields in payload_fields]
                    all_fields.extend(fields for _, fields in vector_inputs.values())
                    for fields in all_fields:
                        for category, path, held in fields:
                            key = (category, holder, (*prefix, '[]', *path))
                            if category == 'owned_storage':
                                if any(origin in leaving for origin, _ in held):
                                    fail(line, 'transfert refusé : le pool du champ propriétaire ne survit pas au vecteur')
                            else:
                                held = surviving_reference_loans(held, depth + 1, line)
                            grouped.setdefault(key, list(active_loans.get(key, ()))).extend(held)
                    field_changes.extend((key, tuple(dict.fromkeys(held))) for key, held in grouped.items())

                    def slot_fields(candidates):
                        alternatives = [fields for origins, fields in payload_fields if origins.intersection(candidates)]
                        represented = frozenset().union(*(origins for origins, _ in payload_fields))
                        for candidate in candidates:
                            if candidate in vector_inputs:
                                precise, fields = vector_inputs[candidate]
                                if not precise:
                                    return None
                                alternatives.append(fields)
                            elif has_dependencies and candidate not in represented:
                                return None
                        return tuple(dict.fromkeys(field for fields in alternatives for field in fields))

                    known = inline_vector_items.get(holder)
                    if exact and known is not None and not prefix and len(holders) == 1:
                        appended = tuple(slot_fields(candidates) for candidates in slots)
                        replaced = tuple((position, slot_fields(candidates)) for position, candidates in replacements)
                        if all(slot is not None for slot in (*appended, *(slot for _, slot in replaced))):
                            remaining = remaining_handle_positions(known, removals)
                            if remaining is not None:
                                completed = replace_handle_positions(remaining, replaced) + appended
                                field_changes.append((('vector_positions', holder, ()), completed))
                continue
            from results import Value
            items = frozenset(item for slot in (*slots, *(slot for _, slot in replacements)) for item in slot)
            if not items:
                continue
            for holder, prefix in holders_for(index):
                key = ('owned_storage', holder, (*prefix, 'items'))
                previous = frozenset(origin for origin, _ in active_loans.get(key, ()))
                origins = replacement_storage(Value('owned', 'Int', candidates=items), previous) | previous
                for payload in dict(summary.vector_write_payloads).get(index, ()):
                    origins |= replacement_storage(payload, previous)
                depth = next((position for position in reversed(range(len(scopes))) if holder in scopes[position][0]), 0)
                leaving = {name for scope in scopes[depth + 1 if references.get(holder) == 'owned' else 0:]
                           for name in scope[0] if name in local_pools}
                if origins & leaving:
                    fail(line, 'transfert refusé : le pool de l’élément ne survit pas au vecteur')
                field_changes.append((key, [(origin, 'storage') for origin in origins]))
        return tuple((key, tuple(held)) for key, held in field_changes)

    def prepare_guarded_task_changes(effects, arguments, holders, line, *, symbolic_holders=frozenset()):
        if not holders:
            return ()
        from results import BorrowTarget, FunctionResult
        parameters = tuple((name, mode, mutex_payload(typ) if index in holders else typ)
                           for index, (name, mode, typ) in enumerate(effects.parameters))
        def resolve(fields):
            summary = FunctionResult('void', 'Void', structure_fields=fields)
            return dict(prepare_field_changes(summary, parameters, arguments, line, guarded_holders=holders))

        written = {}
        # Validate every store, including one overwritten before completion.
        for index, field, source in effects.guarded_writes:
            fields = ((field, frozenset({BorrowTarget('parameter', source)})),)
            for key in resolve(((index, fields),)):
                if key not in active_loans and key[1] not in symbolic_holders:
                    fail(line, 'écriture de dépendance gardée : champ initial sans provenance suivie')
                written[key] = tuple(active_loans.get(key, ()))
        written.update(resolve(effects.guarded_fields))
        return tuple((('guarded_field', *key[1:]), loans) for key, loans in written.items())

    def invalidate_guarded_receipts(holder, prefix=()):
        for key in tuple(guarded_receipts):
            if key[1] == holder and key[2][:len(prefix)] == prefix:
                del guarded_receipts[key]

    def has_guarded_changes(alternatives):
        return any(key[0] == 'guarded_field' for changes in alternatives for key, _ in changes)

    def apply_guarded_await(alternatives, result, line):
        states = [{('stored_field', *key[1:]): held for key, held in changes if key[0] == 'guarded_field'}
                  for changes in alternatives]
        outcomes = []
        for key in set().union(*(state.keys() for state in states)):
            if key not in active_loans:
                fail(line, 'attente d’une écriture gardée : champ initial sans provenance suivie')
            initial = tuple(active_loans[key])
            success = tuple(dict.fromkeys(loan for state in states for loan in state.get(key, initial)))
            overlaps_ordinary_update = guarded_receipts.get(key) == result
            install_field_change(key, dict.fromkeys((*initial, *success)))
            if result is not None and not overlaps_ordinary_update:
                guarded_receipts[key] = result
                outcomes.append((key, success, initial))
        remember_result_outcomes(result, outcomes)

    def remember_result_outcomes(result, outcomes):
        if outcomes:
            _, earlier = result_field_outcomes.get(result, (None, ()))
            result_field_outcomes[result] = result, (*earlier, *outcomes)

    def refine_result_outcome(result, success):
        receipt, outcomes = result_field_outcomes.get(result, (None, ()))
        for key, completed, initial in outcomes:
            if guarded_receipts.get(key) == receipt:
                install_field_change(key, completed if success else initial)

    def set_vector_positions(holder, positions):
        guarded_receipts.pop(('vector_positions', holder, ()), None)
        inline_vector_items[holder] = positions
        if positions is None:
            return
        previous = {key: held for key, held in active_loans.items()
                    if isinstance(key, tuple) and key[0] in ('stored_field', 'owned_storage')
                    and key[1] == holder and key[2][:1] == ('[]',)}
        current = {}
        for slot in positions:
            for category, path, held in slot:
                key = category, holder, ('[]', *path)
                current.setdefault(key, []).extend(held)
        for key in previous.keys() | current.keys():
            guarded_receipts.pop(key, None)
            if key in current:
                active_loans[key] = list(dict.fromkeys(current[key]))
            elif key[0] == 'stored_field':
                active_loans[key] = []
            else:
                active_loans.pop(key, None)
        backing = ('owned_storage', holder, ('vector_backing',))
        if holder in storage_bindings and backing in active_loans:
            retired = {origin for key, held in previous.items() if key[0] == 'owned_storage'
                       for origin, _ in held}
            live = {origin for held in owned_storage_fields(holder).values() for origin, _ in held}
            storage_bindings[holder] = (storage_bindings[holder] - retired) | live

    def install_field_change(key, held):
        guarded_receipts.pop(key, None)
        if key[0] == 'vector_positions':
            set_vector_positions(key[1], held)
        elif key[0] == 'owned_storage':
            holder = key[1]
            previous = active_loans.get(key, ())
            if held:
                active_loans[key] = list(held)
            else:
                active_loans.pop(key, None)
            root = active_loans.get(('storage_root', holder, ()))
            origins = frozenset(origin for origin, _ in held)
            if root is None:
                origins |= storage_bindings.get(holder, frozenset())
            else:
                known = frozenset(origin for origin, _ in root)
                known |= frozenset(origin for sources in owned_storage_fields(holder).values()
                                   for origin, _ in sources)
                retired = frozenset(origin for origin, _ in previous) - known
                origins |= known | (storage_bindings.get(holder, frozenset()) - retired)
            storage_bindings[holder] = origins
        else:
            active_loans[key] = list(held)

    def apply_child_field_changes(alternatives, line, *, launched, receipt=None):
        from async_structure_effects import FIELD_RESULT_MODES, completion_hashmap_writes
        if not any(alternatives):
            return
        if has_guarded_changes(alternatives):
            fail(line, 'écriture de dépendance gardée : attendre le handle avec execution.await')
        aggregate_changes = any(key[0] != 'vector_positions' and key[2][:1] != ('map_items',)
                                for changes in alternatives for key, _ in changes)
        if aggregate_changes and (node.field_effect_summary is None or not node.field_effect_summary.complete
                                  or result[0] not in FIELD_RESULT_MODES):
            reason = getattr(node.field_effect_summary, 'reason', '')
            fail(line, 'prototype : terminaison des dépendances de champs enfant non raccordée'
                 + (': ' + reason if reason else ''))
        alternatives = [dict(changes) for changes in alternatives]
        outcomes = []
        keys = set().union(*(changes.keys() for changes in alternatives))
        positions = {}
        for key in tuple(keys):
            if key[0] != 'vector_positions':
                continue
            keys.remove(key)
            holder = key[1]
            initial = inline_vector_items.get(holder)
            candidates = {changes.get(key, initial) for changes in alternatives}
            completed = next(iter(candidates)) if len(candidates) == 1 else None
            merged = None if launched and completed != initial else completed
            positions[key] = merged, completed, initial
        for category, holder, path in keys:
            if path[:1] == ('map_items',):
                if parameter_modes.get(holder) == 'mut' and not any(
                        table == parameter_indexes[holder]
                        for path in completion_hashmap_writes(node) for table, _, _ in path):
                    fail(line, 'mutation de collection injectée : contrat de terminaison requis')
                invalidate_map_receipts(category, holder, path[1])
        for key in keys:
            _, holder, path = key
            has_initial_storage = key[0] == 'owned_storage' and key in active_loans
            initial = tuple(active_loans.get(key, initial_stored_field_loans(holder, path)
                                           if key[0] == 'stored_field' else ()))
            completed = tuple(dict.fromkeys(loan for changes in alternatives
                                            for loan in changes.get(key, initial)))
            held = (*initial, *completed) if launched else completed
            install_field_change(key, dict.fromkeys(held))
            if receipt is not None and (key[0] == 'stored_field' or has_initial_storage or path[:1] == ('map_items',)):
                guarded_receipts[key] = receipt
                outcomes.append((key, completed, initial))
            if key[1] in inline_vector_items:
                set_vector_positions(key[1], None)
        for key, (merged, completed, initial) in positions.items():
            install_field_change(key, merged)
            if receipt is not None and completed != initial:
                guarded_receipts[key] = receipt
                outcomes.append((key, completed, initial))
        remember_result_outcomes(receipt, outcomes)

    def prepare_hashmap_changes(paths, arguments, argument_loans, line):
        from async_structure_effects import completion_hashmap_writes
        if not any(paths):
            return ((),)
        alternatives = []
        for path in paths:
            changes = {}
            for table_index, key, value_index in path:
                table_arg = arguments[table_index]
                if table_arg[0] not in ('mut', 'name'):
                    fail(line, 'contrat HashMap : table nommée empruntée requise')
                table = table_arg[1]
                local = table_arg[0] == 'mut' and references.get(table) == 'owned'
                relayed = (table_arg[0] == 'name' and parameter_modes.get(table) == 'mut'
                           and (any(completion_hashmap_writes(node)) or node.field_effect_summary is not None
                                and any(node.field_effect_summary.returned_handle_map_paths)))
                if not (local or relayed):
                    fail(line, 'contrat HashMap : table locale ou paramètre mutable relayé requis')
                if isinstance(key, int):
                    key = known_map_key(arguments[key])
                elif key is not None:
                    key = int(key) & ((1 << 64) - 1)
                depth = binding_depth(table) + 1 if local else 1
                mapping = map_types(reference_types.get(table, collection_types.get(table)))
                owned = mapping and map_handle_element(mapping[1])
                category = 'owned_storage' if owned else 'stored_field'
                held = ()
                if value_index is not None:
                    if owned:
                        held = tuple(loan for loan in argument_loans[value_index] if loan[1] == 'storage')
                        leaving = {name for scope in scopes[depth:] for name in scope[0] if name in local_pools}
                        if any(origin in leaving or origin in implicit_stacks for origin, _ in held):
                            fail(line, 'contrat HashMap : le pool de l’allocation ne survit pas à la table')
                    else:
                        held = surviving_reference_loans(argument_loans[value_index], depth, line)
                        if not held:
                            fail(line, 'contrat HashMap : provenance de référence manquante')
                entry = (category, table, ('map_items', key))
                before = active_loans.get(entry, ())
                changes[entry] = (tuple(dict.fromkeys((*changes.get(entry, before), *held)))
                                  if key is None else tuple(held))
            alternatives.append(tuple(changes.items()))
        return tuple(alternatives)

    def sync_call(expr, line, expected=None, *, following=None, borrow=False, owned=False, execution=False, task=False):
        from async_structure_effects import FIELD_RESULT_MODES
        expression_id = id(expr)
        expr = sync_method_call(expr)
        contract = sync_contracts[expr[1]]
        task_activity.add(('sync', expr[1]))
        for loop in loops:
            loop['sync_calls'].add(expr[1])
        if contract.effects.blocking_join and not node.native_block:
            fail(line, 'join réservé au code synchrone, y compris à travers les appels auxiliaires ; utiliser await')
        signature = contract.result_type
        local_result = any(candidate.kind == 'fresh' and candidate.source.kind == 'local_value'
                           for candidate in contract.result.candidates)
        if (signature[0] in ('ref', 'mut') and map_types(signature[1]) is not None
                or signature not in output_types and signature not in handle_sync_types and signature not in task_sync_types and signature != ('void', 'Void')
                or any((mode, typ) not in sync_types for _, mode, typ in contract.parameters)):
            fail(line, 'prototype : appel synchrone depuis un état : signature non prise en charge')
        for _, mode, typ in contract.parameters:
            mapping = map_types(typ)
            if mode == 'mut' and mapping and map_handle_element(mapping[1]):
                fail(line, 'appel synchrone depuis une tâche : contrat de mutation des entrées propriétaires HashMap requis')
        if expected is not None and signature != expected:
            fail(line, f'appel synchrone : résultat {signature[1]}, attendu {expected[1]}')
        if signature in owned_output_types | output_join_types and not owned:
            fail(line, 'résultat propriétaire : recevoir, transférer ou drop explicitement')
        if signature in handle_sync_types and not execution:
            fail(line, 'handle lancé : recevoir puis attendre explicitement le résultat')
        if signature in task_sync_types and not task:
            fail(line, 'tâche inactive : recevoir, attendre ou détruire explicitement')
        if len(expr[2]) != len(contract.parameters):
            fail(line, f"'{expr[1]}' attend {len(contract.parameters)} argument(s), reçu {len(expr[2])}")
        prepared, loans, argument_loans, prepared_owners, argument_storage = [], [], [], [], []
        argument_fields = {}
        argument_payload_storage = {}
        argument_tasks = {}
        argument_locks = {}
        local_parameters = set()
        active_loans[id(loans)] = loans
        pending_capture_groups.append((len(scopes) - 1, prepared_owners, loans))
        argument_depth = len(argument_tails)
        try:
            for index, (argument, (_, mode, typ)) in enumerate(zip(expr[2], contract.parameters)):
                argument_tails.append((len(scopes) - 1, expr[2][index + 1:]))
                held = []
                argument_ctype = sync_types[(mode, typ)]
                if mode in ('task', 'execution'):
                    if argument[0] == 'down':
                        require_local_async_value(argument[1], line)
                        record = (consume_task if mode == 'task' else consume_execution)(argument[1], line)
                    elif argument[0] == 'transfer':
                        operand = argument[1]
                        if mode == 'task' and operand[0] == 'call':
                            record = create_task(operand, line)
                        else:
                            kind, record = emit_computed_transfer(operand, line)
                            if kind != mode:
                                fail(line, 'argument async : même mode de tâche ou de handle requis')
                    else:
                        fail(line, 'argument de tâche : transfert -> explicite requis')
                    if has_guarded_changes(record[5]):
                        summary = contract.result
                        plain_modes = {*MODE_TYPES, 'scalar', 'bool', 'byte', 'char'}
                        pure_relay = (summary.task_forward_only
                                      and summary.task_forward_parameters == {index}
                                      and index not in summary.task_wait_parameters
                                      and all(other == index or argument_mode in plain_modes
                                              for other, (_, argument_mode, _) in enumerate(contract.parameters)))
                        if not pure_relay:
                            fail(line, 'écriture de dépendance gardée : relais sans accès aux captures requis')
                    from handle_types import is_public_handle
                    actual = public_execution_type(record, typ, line) if mode == 'execution' and is_public_handle(typ) else record[3]
                    if actual != typ:
                        fail(line, f'argument de tâche : type {typ} attendu')
                    argument_tasks[index] = record
                    if any(target in implicit_stacks for target, access in record[4] if access == 'storage'):
                        local_parameters.add(index)
                    value, held = record[0], list(record[2])
                    active_loans.pop(id(record[2]), None)
                    loans.extend(held)
                elif mode == 'owned':
                    if argument[0] not in ('down', 'transfer'):
                        fail(line, 'argument propriétaire : transfert -> explicite requis')
                    operand = argument if argument[0] == 'down' else argument[1]
                    if operand[0] in ('down', 'move') and result_lock_loans(operand[1]):
                        require_local_async_value(operand[1], line)
                        _, value = export_async_value(operand[1], (), line, depth=len(scopes))
                    else:
                        value = sync_owned_value(operand, line)
                    carried = tuple(result_lock_loans(value))
                    if carried:
                        if index in contract.copied_lock_parameters:
                            fail(line, 'copie interdite : l’argument maintient un verrou')
                        summary = contract.result
                        if (signature not in scalar_sync_types and signature not in owned_output_types
                                and signature != ('void', 'Void')
                                or summary.owned_fields or summary.borrowed_fields
                                or summary.structure_fields or summary.owned_field_writes
                                or summary.vector_writes or summary.reference_appends
                                or summary.handle_writes or summary.exchange_payloads
                                or summary.task_sources or any(contract.hashmap_writes)):
                            fail(line, 'transfert du verrou : contrat de résultat ou d’écriture non raccordé')
                        argument_locks[index] = carried
                        node.async_lock_arguments.add((expr[1], index))
                        loans.extend(carried)
                    if owned_result_types.get(value, 'Int') != typ:
                        fail(line, f'argument propriétaire : allocation {typ} attendue')
                    if contract.parameters[index][0] in contract.handle_parameters and storage_of(value) & implicit_stacks:
                        fail(line, 'une valeur locale T ne peut pas devenir une allocation A<T>')
                    if storage_of(value) & implicit_stacks:
                        local_parameters.add(index)
                    field_loans = owned_capture_field_loans(value, typ)
                    argument_fields.update(((index, path), group) for path, group in field_loans.items())
                    held = [loan for group in field_loans.values() for loan in group]
                    loans.extend(held)
                elif (mode, typ) in owned_join_sync_types:
                    if argument[0] not in ('down', 'transfer'):
                        fail(line, 'argument Result propriétaire : transfert -> explicite requis')
                    value, payload, _ = owned_join_value(
                        argument if argument[0] == 'down' else argument[1], line)
                    content = wrapper_content_type(mode, typ)
                    if payload != owned_wrapper_payload(mode, typ) or owned_result_types.get(value, 'Int') != content:
                        fail(line, 'argument de résultat propriétaire : type incompatible')
                    if storage_of(value) & implicit_stacks:
                        local_parameters.add(index)
                    field_loans = owned_capture_field_loans(value, content)
                    argument_fields.update(((index, path), group) for path, group in field_loans.items())
                    held = [loan for group in field_loans.values() for loan in group]
                    loans.extend(held)
                    if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
                        for arm in ('ok', 'err'):
                            origins = active_loans.get(('owned_storage', value, (arm,)))
                            argument_payload_storage[index, arm] = (frozenset(origin for origin, _ in origins)
                                if origins is not None else storage_of(value))
                elif (mode, typ) in pool_sync_types:
                    value, held = pool_argument(argument, mode, typ, line)
                    loans.extend(held)
                elif (mode, typ) in view_sync_types:
                    operand = ('reborrow', argument[1], 'mut') if mode in SHARED_VECTOR_SLICE_MODES and argument[0] == 'name' else argument
                    if mode == 'text':
                        value = static_text_value(operand, line)
                    elif mode == 'byte_ref':
                        value = static_byte_ref_value(operand, line)
                    elif mode in VECTOR_SLICE_ELEMENTS:
                        value = vector_view_value(operand, line, mode)
                    elif mode in SHARED_VECTOR_SLICE_MODES:
                        value = mutable_slice_value(operand, line, mode)
                    else:
                        value = wrapped_utf8_value(operand, line)
                    held = list(local_utf8_loans(operand, value))
                    loans.extend(held)
                elif mode in ('ref', 'mut'):
                    value, held = sync_borrow_argument(argument, mode, typ, line)
                    loans.extend(held)
                    if vector_payload_element(typ) is not None:
                        argument_fields.update(((index, path), group)
                            for path, group in owned_capture_field_loans(value, typ).items())
                    if typ in struct_layouts and any(storage_bindings.get(loan_root(target), frozenset()) & implicit_stacks
                                                     for target, _ in held):
                        local_parameters.add(index)
                    # The existing sync ABI uses non-const C pointers for
                    # read loans too; Crust's contract forbids their mutation.
                    if index in contract.result.stored_reference_parameters:
                        value = stored_reference_cell(value, held, line)
                        argument_ctype = 'Cell *'
                    else:
                        value = (f'structure_reference_for((CrustStructureView){{0}}, {value})' if typ in struct_layouts
                                 else f'({sync_types[(mode, typ)]})({value})')
                else:
                    # A literal receives u8 context; a named Int never narrows.
                    if mode == 'byte' and argument[0] == 'int' and 0 <= argument[1] <= 255:
                        value, actual = str(argument[1]), 'u8'
                    else:
                        value, actual = infer_scalar_value(argument, line)
                    expected_type = 'Bool' if mode == 'bool' else typ
                    if actual != expected_type:
                        fail(line, f"argument de '{expr[1]}' : attendu {typ}, reçu {actual}")
                snapshot = temporary(argument_ctype)
                if mode == 'execution':
                    steps.append(f'task_sync_adopt(&{snapshot}, {value});')
                    prepared_owners.append(('execution', snapshot))
                else:
                    steps.append(f'{snapshot} = {value};')
                if mode == 'task':
                    prepared_owners.append(('task', snapshot))
                    steps.append(f'{value} = NULL;')
                elif mode == 'owned':
                    prepared_owners.append(snapshot)
                    steps.append(f'{value} = NULL;')
                    clear_stored_fields(value)
                elif (mode, typ) in owned_join_sync_types:
                    field = 'value' if mode == 'buffered_handle_exchange' else JOIN_CELLS[mode]
                    success = f'{snapshot}.status == 0' + (f' && {snapshot}.value.status == 0' if mode in ('join_nested', 'join_option') else '')
                    if mode == 'buffered_handle_exchange':
                        success = f'{snapshot}.status != 0' if exchange_optional(typ) else '1'
                    elif mode in EXCHANGE_JOIN_TYPES or mode in OPTION_JOIN_TYPES or mode in OWNED_JOIN_TYPES:
                        _, success = wrapper_cleanup(snapshot, JOIN_PAYLOADS[mode])
                    pending = temporary('Cell *')
                    steps.extend((f'{pending} = ({success}) ? {snapshot}.{field} : NULL;',
                                  f'{value}.{field} = NULL;'))
                    prepared_owners.append(pending)
                prepared.append(snapshot)
                if any(result_lock_loans(loan_root(target)) for target, _ in held):
                    if index in contract.copied_lock_parameters:
                        fail(line, 'copie interdite : l’argument maintient un verrou')
                    node.async_lock_arguments.add((expr[1], index))
                argument_loans.append(held)
                argument_storage.append((frozenset(target for target, access in held if access == 'storage') if mode in ('task', 'execution')
                                         else pool_storage(argument[1]) if (mode, typ) in pool_sync_types
                                         else storage_of(value) if mode == 'owned' or (mode, typ) in owned_join_sync_types
                                         else frozenset(origin for target, _ in held
                                             for origin in storage_bindings.get(loan_root(target), ()))))
                release_sync_argument_loans(following)
                argument_tails.pop()
        finally:
            del argument_tails[argument_depth:]
            pending_capture_groups.pop()
            active_loans.pop(id(loans), None)
        forwarded = {candidate.parameter for candidate in contract.result.candidates
                     if candidate.kind == 'parameter'} if signature in owned_output_types else set()
        returned_lock = [loan for index in forwarded for loan in argument_locks.get(index, ())]
        lock_origins = [frozenset(loan_root(target) for target, _ in held) for held in argument_loans]
        for left, right in contract.distinct_lock_parameters:
            if lock_origins[left] & lock_origins[right]:
                fail(line, 'contrat de verrou : les arguments doivent désigner des instances distinctes')
        pending = [record[2] for records in (tasks, executions) for record in records.values() if record is not None]
        pending.extend(selection.loans for selection in selections.values() if selection is not None)
        pending.extend(held for _, _, held in pending_capture_groups)
        for index in contract.lock_parameters:
            requested = lock_origins[index]
            if requested & result_lock_roots():
                fail(line, 'verrou déjà maintenu par un résultat vivant sur cette instance')
            for owner, held in argument_locks.items():
                if ((index, owner) in contract.live_lock_arguments
                        and requested & {loan_root(target) for target, _ in held}):
                    fail(line, 'verrou maintenu par un argument vivant pendant l’acquisition')
            if any(requested & {loan_root(target) for target, _ in held} for held in pending):
                fail(line, 'acquisition du verrou : instance déjà capturée par une tâche en cours')
        for index in contract.returned_lock_parameters:
            returned_lock.extend((target, 'ref') for target in lock_origins[index])
        if returned_lock and signature not in owned_output_types:
            fail(line, 'contrat de verrou : résultat propriétaire direct requis')
        symbol, diverges = (sync_bridge(expr[1], node.args[0], local_parameters=frozenset(local_parameters))
                            if local_parameters else sync_bridge(expr[1], node.args[0]))
        for index, required in contract.storage_requirements:
            if (index in local_parameters) != (required == 'local'):
                fail(line, f'exigence de stockage {required} (T local / allocation A<T>) non satisfaite dans un appel synchrone')
        local_result |= any(candidate.kind == 'fresh' and candidate.source.kind == 'allocation_parameter'
                            and candidate.source.index in local_parameters for candidate in contract.result.candidates)
        local_source = None
        from async_result_storage import needs_task_output
        output_sources = contract.result.task_result_sources
        if any(source.kind in ('task_output', 'task_output_parameter') for source in output_sources):
            storage_kinds = {source.kind == 'task_output' or source.kind == 'task_output_parameter'
                             and source.index in local_parameters for source in output_sources}
            if len(storage_kinds) > 1:
                fail(line, 'retours incompatibles : valeur locale T et allocation A<T>')
        if local_result or needs_task_output(contract.result.task_result_sources, lambda index: index in local_parameters):
            local_source = local_destinations.get(expression_id) or implicit_stack()
            prepared.append('&' + local_pools[local_source])
        if (any(not guard_roots(argument_loans[index]) for index, _ in contract.result.structure_fields)
                and (node.field_effect_summary is None or not node.field_effect_summary.complete
                     or result[0] not in FIELD_RESULT_MODES)):
            fail(line, 'prototype : remplacement des dépendances de champs par un appel depuis un état non raccordé')
        changes = prepare_field_changes(contract.result, contract.parameters, argument_loans, line,
                                        argument_storage, argument_fields, local_guard=True)
        for parameter, *_ in contract.result.vector_writes:
            for origin, _ in argument_loans[parameter]:
                if loan_root(origin) in inline_vector_items:
                    set_vector_positions(loan_root(origin), None)
        for key, held in changes:
            install_field_change(key, held)
            if key[0] != 'vector_positions' and key[1] in inline_vector_items:
                set_vector_positions(key[1], None)
        map_changes = prepare_hashmap_changes(contract.hashmap_writes, expr[2], argument_loans, line)
        apply_child_field_changes(map_changes, line, launched=False)
        for index in contract.result.task_wait_parameters:
            if index in argument_tasks:
                apply_child_field_changes(argument_tasks[index][5], line, launched=True)
        call = symbol + '(' + ', '.join(prepared) + ')'
        if signature == ('void', 'Void') or diverges:
            steps.append(call + ';')
            for record in argument_tasks.values():
                clear_stored_fields(record[0])
            if diverges:
                raise NoAsyncContinuation()
            return '', 'Void'
        def projected_argument_loans(target):
            typ = contract.parameters[target.parameter][2]
            if typ not in reference_aggregates:
                fail(line, 'projection du résultat : agrégat pris en charge requis')
            # Owned arguments have already yielded their field targets and
            # lost their carrier metadata. Projecting again would turn a
            # target into a fictional field inside that target.
            captured = argument_fields.get((target.parameter, target.field))
            if target.kind == 'detached_field_parameter' and captured is not None:
                return captured
            return project_result_field_loans(argument_loans[target.parameter], typ,
                                              tuple(target.field.lstrip('.').split('.')))
        value = temporary((output_types | handle_sync_types | task_sync_types)[signature])
        steps.append(f'{value} = {call};')
        if signature in handle_sync_types or signature in task_sync_types:
            retained, returned = [], []
            forwarded = [argument_tasks[index] for index in contract.result.task_forward_parameters
                         if index in argument_tasks]
            capture_loans = {}
            direct_capture_loans = {}
            capture_field_loans = {}
            concrete_definition = functions.get(signature[1])
            result_definition = concrete_definition or functions[signature[1]]
            result_handle_pools = frozenset().union(
                *(known_handle_result_pools(record[0], record[3]) for record in forwarded))
            result_handle_pools |= frozenset(
                pool for pool in contract.result.task_result_handle_pools if isinstance(pool, str))
            if not contract.result.task_forward_only:
                result_handle_pools |= known_handle_result_pools(value, signature[1])
            owner_result_indexes = owned_result_parameters(result_definition, functions,
                sync_result=lambda name: sync_contracts[name].result if name in sync_contracts else None)
            from async_result_storage import borrowed_result_fields
            from capture_paths import result_capture_selector
            result_field_selectors = {result_capture_selector(target)
                for _, targets in borrowed_result_fields(result_definition) for target in targets}
            result_capture_paths = (borrowed_result_paths(concrete_definition, functions, fail, {},
                                    sync_contracts=sync_contracts) if concrete_definition is not None else ())
            result_captures = (borrowed_result_parameters(functions[signature[1]], functions, fail, {},
                              sync_contracts=sync_contracts)
                               if concrete_definition is not None else {4, 5})
            if concrete_definition is not None:
                result_captures |= utf8_result_parameters(functions[signature[1]], functions,
                                                          sync_contracts=sync_contracts)
            for field, targets in contract.result.borrowed_fields:
                held = []
                for target in targets:
                    if target.kind == 'task_capture_parameter' and target.parameter in argument_tasks:
                        # The opaque task can only be forwarded or consumed.
                        # Its record already separates live captures from loans
                        # retained by its completion result.
                        continue
                    elif target.kind in ('inline_field_parameter', 'indirect_field_parameter', 'detached_field_parameter', 'field_parameter'):
                        held.extend(projected_argument_loans(target))
                    elif target.kind == 'owned_capture_field':
                        held.extend(argument_fields[(target.parameter, target.field)])
                    elif target.kind in ('parameter', 'utf8_parameter', 'string_parameter', 'vector_parameter'):
                        held.extend(argument_loans[target.parameter])
                    else:
                        fail(line, 'prototype : capture du handle synchrone sans paramètre direct')
                retained.extend(held)
                if not targets and '/' in field:
                    position = capture_index(field.partition('.')[2])
                    capture_field_loans[(position, field.partition('/')[2])] = []
                if not held:
                    continue
                position = capture_index(field.partition('.')[2])
                capture_loans.setdefault(position, []).extend(held)
                if '/' in field:
                    capture_field_loans[(position, field.partition('/')[2])] = held
                else:
                    direct_capture_loans.setdefault(position, []).extend(held)
                selected_field = field.partition('/')[2]
                if position in owner_result_indexes or position in result_captures and (not selected_field or any(
                        index == position and selected_field == '.' + '.'.join(path)
                        for index, path in result_capture_paths)
                        or f'{position}/{selected_field}' in result_field_selectors):
                    returned.extend(held)
            for sources, output in ((contract.result.task_sources, retained),
                                    (contract.result.task_result_sources, returned)):
                for source in sources:
                    if source.kind in ('task_parameter', 'task_result_parameter', 'task_result_field_parameter') and source.index in argument_tasks:
                        continue
                    if source.kind == 'task_output' or source.kind == 'task_output_parameter' and source.index in local_parameters:
                        output.append((local_source, 'storage'))
                        continue
                    if source.kind not in ('source_parameter', 'allocation_parameter', 'vector_element_parameter',
                                           'allocation_field_parameter', 'task_output_parameter'):
                        fail(line, 'prototype : stockage du handle synchrone sans paramètre direct')
                    # Owned argument storage includes all descendant pools.
                    # A field-origin contract must retain those pools too;
                    # retaining the aggregate union is conservative here.
                    output.extend((origin, 'storage') for origin in argument_storage[source.index])
            acquired_locks = []
            if not contract.result.task_forward_only:
                from handle_types import PUBLIC_RESULT_LOCK_SLOT
                indexes = getattr(result_definition, 'async_returned_lock_parameters', ())
                if concrete_definition is None and PUBLIC_RESULT_LOCK_SLOT in direct_capture_loans:
                    indexes = (PUBLIC_RESULT_LOCK_SLOT,)
                for index in indexes:
                    origins = {loan_root(target) for target, mode in direct_capture_loans.get(index, ()) if mode != 'storage'}
                    if not origins:
                        fail(line, 'fabrique de tâche : origine du verrou retourné introuvable')
                    if origins & result_lock_roots():
                        fail(line, 'verrou déjà maintenu par un résultat vivant sur cette instance')
                    pending = [record[2] for records in (tasks, executions) for record in records.values() if record is not None]
                    pending.extend(selection.loans for selection in selections.values() if selection is not None)
                    if any(origins & {loan_root(target) for target, _ in held} for held in pending):
                        fail(line, 'acquisition du verrou : instance déjà capturée par une tâche en cours')
                    acquired_locks.extend((origin, 'ref') for origin in origins)
            if acquired_locks:
                active_loans[('stored_field', value, ('result_lock',))] = list(dict.fromkeys(acquired_locks))
                retained.extend(acquired_locks)
            for record in forwarded:
                retained.extend(record[2])
                returned.extend(record[4])
            retained.extend(returned)
            active_loans[id(retained)] = retained
            pending = prepare_field_changes(
                replace(contract.result, structure_fields=contract.result.task_field_updates,
                        owned_field_writes=contract.result.task_owned_updates,
                        vector_writes=tuple((index, (items,), False, (), ())
                                            for index, items in contract.result.task_vector_updates)),
                contract.parameters, argument_loans, line)
            if signature in task_sync_types:
                definition = functions[signature[1]]
                if definition.args[2][0] == 'buffered_handle_exchange' or definition.args[2][0] in EXCHANGE_JOIN_TYPES:
                    for arm, symbols in contract.result.task_result_fields:
                        origins = set()
                        for source in symbols:
                            if source.kind == 'allocation_field_parameter' and source.name in ('ok', 'err'):
                                origins.update(argument_payload_storage.get((source.index, source.name), argument_storage[source.index]))
                            elif source.kind == 'task_result_field_parameter' and source.index in argument_tasks:
                                holder = argument_tasks[source.index][0]
                                origins.update(origin for origin, _ in active_loans.get(('owned_storage', holder, (source.name,)), ()))
                            else:
                                origins.update(argument_storage[source.index])
                        active_loans[('owned_storage', value, (arm,))] = [(origin, 'storage') for origin in origins]
                from async_result_storage import borrowed_result_fields
                if capture_loans or not forwarded:
                    retain_result_fields(value, borrowed_result_fields(definition), capture_loans, line, capture_field_loans)
                    for (position, field), loans in capture_field_loans.items():
                        if position in owner_result_indexes:
                            key = ('stored_field', value, stored_field_path(field))
                            active_loans[key] = list(dict.fromkeys((*active_loans.get(key, ()), *loans)))
                prefixes = tuple(prefix for record in forwarded for prefix in task_prefix_changes.get(record[0], ()))
                if capture_loans or not forwarded:
                    prefixes += ((definition.field_effect_summary, definition.args[1],
                        tuple(tuple(capture_loans.get(index, ())) for index in range(len(definition.args[1])))),)
                task_prefix_changes[value] = prefixes
                if result_handle_pools:
                    task_handle_result_pools[value] = result_handle_pools
                if forwarded and contract.result.task_forward_only:
                    task_handle_output_loans[value] = tuple(dict.fromkeys(
                        loan for record in forwarded for loan in task_output_projection(record)))
                if forwarded:
                    task_handle_field_changes[value] = tuple(
                        change for record in forwarded for change in task_handle_field_changes.get(record[0], ((),))
                    ) + (() if contract.result.task_forward_only else ((),))
                for record in forwarded:
                    move_stored_fields(record[0], value)
                for index, record in argument_tasks.items():
                    if index not in contract.result.task_forward_parameters:
                        clear_stored_fields(record[0])
                direct_changes = () if contract.result.task_forward_only and not pending else (pending,)
                changes = (*direct_changes, *(change for record in forwarded for change in record[5]))
                return value, definition.args[2] == ('scalar', 'Int'), retained, signature[1], returned, changes
            enable_threads()
            handle = temporary('CrustAsyncExecution')
            steps.append(f'task_async_adopt(&{handle}, &{value});')
            if result_handle_pools:
                task_handle_result_pools[f'&{handle}'] = result_handle_pools
            if forwarded and contract.result.task_forward_only:
                task_handle_output_loans[f'&{handle}'] = tuple(dict.fromkeys(
                    loan for record in forwarded for loan in task_output_projection(record)))
            if forwarded:
                task_handle_field_changes[f'&{handle}'] = tuple(
                    change for record in forwarded for change in task_handle_field_changes.get(record[0], ((),))
                ) + (() if contract.result.task_forward_only else ((),))
            forwarded_pools = {pool for record in forwarded
                               for pool in execution_pools.get(record[0], (record[3],))}
            independent = contract.branch_independent or contract.result.task_forward_only
            if (independent and len(forwarded) == len(contract.result.task_forward_parameters)
                    and all(autonomous_execution(record) for record in forwarded)):
                execution_pools[f'&{handle}'] = contract.branch_pools | forwarded_pools
            if capture_loans or not forwarded:
                from async_result_storage import borrowed_result_fields
                retain_result_fields(value, borrowed_result_fields(result_definition), capture_loans, line, capture_field_loans)
                move_stored_fields(value, f'&{handle}')
            for index, record in argument_tasks.items():
                if index in contract.result.task_forward_parameters:
                    move_stored_fields(record[0], f'&{handle}')
                else:
                    clear_stored_fields(record[0])
            direct_changes = () if contract.result.task_forward_only and not pending else (pending,)
            changes = (*direct_changes, *(change for record in forwarded for change in record[5]))
            returns_int = (concrete_definition.args[2] if concrete_definition is not None
                           else public_signature(signature[1], aggregate_layouts)) == ('scalar', 'Int')
            return f'&{handle}', returns_int, retained, signature[1], returned, changes
        if signature in owned_output_types | output_join_types:
            if returned_lock:
                active_loans[('stored_field', value, ('result_lock',))] = list(dict.fromkeys(returned_lock))
            owned_result_types[value] = wrapper_content_type(*signature)
            if local_source is not None:
                keep_storage(value, (local_source,))
            def storage_candidates(summary):
                yield from summary.candidates
                for _, child in summary.owned_fields:
                    yield from storage_candidates(child)
            def candidate_storage(candidate):
                if candidate.kind == 'exchange_parameter':
                    return argument_payload_storage.get((candidate.parameter, 'ok' if candidate.item_index == 0 else 'err'),
                                                        argument_storage[candidate.parameter])
                if candidate.kind == 'fresh' and (candidate.source.kind == 'local_value'
                        or candidate.source.kind == 'allocation_parameter'
                        and candidate.source.index in local_parameters):
                    return frozenset()
                index = (candidate.parameter if candidate.kind in ('parameter', 'vector_element') else
                         candidate.source.index if candidate.kind == 'fresh'
                         and candidate.source.kind == 'source_parameter' else None)
                return argument_storage[index] if index is not None else frozenset().union(*argument_storage)
            for candidate in storage_candidates(contract.result):
                keep_storage(value, candidate_storage(candidate))
            if signature[0] == 'buffered_handle_exchange' or signature[0] in EXCHANGE_JOIN_TYPES:
                for arm, candidates in zip(('ok', 'err'), contract.result.exchange_payloads):
                    origins = frozenset().union(*(candidate_storage(candidate) for candidate in candidates))
                    active_loans[('owned_storage', value, (arm,))] = [(origin, 'storage') for origin in origins]
            retain_result_fields(value, summary_borrowed_fields(contract.result), argument_loans, line, argument_fields)
            return value, signature[1]
        if signature in view_sync_types:
            retained_views = []
            for target in contract.result.reference_targets:
                if target.kind not in ('utf8_parameter', 'parameter'):
                    fail(line, 'prototype : vue synchrone sans paramètre direct')
                retained_views.extend(argument_loans[target.parameter])
            utf8_result_loans[value] = tuple(retained_views)
            return value, SCALAR_TYPES[signature[0]]
        if signature in reference_sync_types and borrow:
            retained = []
            for target in contract.result.reference_targets:
                if target.kind in ('inline_field_parameter', 'indirect_field_parameter', 'detached_field_parameter', 'field_parameter'):
                    retained.extend(projected_argument_loans(target))
                elif target.kind == 'parameter':
                    retained.extend(argument_loans[target.parameter])
                else:
                    fail(line, 'prototype : résultat synchrone emprunté sans paramètre direct')
            active_loans[id(retained)] = retained
            return value, retained, signature
        if signature in reference_sync_types:
            fail(line, 'un résultat emprunté exige une liaison ou un argument de référence')
        return value, 'Bool' if signature == ('bool', 'bool') else signature[1]

    if any(not (scalar_array_layout(typ)[0] or int_reference_row(typ, mode))
           if mode in ('array', *ARRAY_BORROWS) else
           (mode, typ) not in (('mut', 'u8'), ('runtime_error', 'runtime::Error'), ('scalar', 'Bool'), ('byte', 'u8'), ('char', 'char'), ('text', 'str'), ('byte_ref', 'u8'))
           and not (mode in (*EXTRA_MODES, *ERROR_VALUE_TYPES, *ASYNC_CAPTURE_VIEW_MODES, *UTF8_VALUE_RESULT_FAMILIES, *PLAIN_JOIN_TYPES) and typ == VALUE_MODES[mode])
           and not (mode in ('ref', 'mut', 'owned', *JOIN_PAYLOADS) and typ in ('String', 'Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS))
           and mode != 'async_execution'
           and (mode, typ) not in pool_sync_types
           and not (mode == 'buffered_handle_exchange' and (mode, typ) in owned_join_sync_types)
           and not (mode in ('owned', *JOIN_PAYLOADS) and typ in owned_aggregates)
           and not (mode == 'owned' and typ in owned_numeric_types)
           and not (mode in ('ref', 'mut') and typ in EXTRA_C_TYPES)
           and not map_capture(mode, typ)
           and not (mode == 'ref' and mutex_payload(typ) and (
               scalar_field_mode(mutex_payload(typ)) or mutex_structure_payload(mutex_payload(typ))))
           and not (mode in ('ref', 'mut') and typ in reference_aggregates)
           and (typ != 'Int' or mode not in ('scalar', 'ref', 'mut', 'owned', *JOIN_PAYLOADS))
           for _, mode, typ in parameters):
        fail(node.line, 'prototype async : captures Int, &Int, &mut Int ou -> Int, emprunts ou transferts de String et Vector<Int/u8>, Bool, u8, char, &str statique, &u8 statique, emprunt de tableau Int ou Result compatible requis')
    references = {name: mode for name, mode, _ in parameters if mode in ('ref', 'mut', 'owned')}
    reference_types = {name: typ for name, mode, typ in parameters if mode in ('ref', 'mut')
                       or mode == 'owned' and typ in owned_aggregates}
    pool_types = {name: typ for name, mode, typ in parameters if (mode, typ) in pool_sync_types}
    local_pools = {}
    implicit_stacks = set()
    local_destinations = {}
    local_layouts = {}
    pool_alias_origins = {}
    region_limits = [0]
    storage_bindings = {}
    storage_values = {}
    awaited_reference_types = {}
    returns_array, array_result_ctype = scalar_array_layout(result[1]) if result[0] == 'array' else ((), None)
    returns_execution = result[0] == 'async_execution'
    if returns_execution:
        if public_async_signature(result[1], aggregate_layouts, allow_borrowed=True) is None:
            fail(node.line, 'retour AsyncHandle : type de résultat non raccordé')
        enable_threads()
    if (not returns_array and result not in SCALAR_RESULTS
            and not returns_execution
            and not ((result[0] in EXCHANGE_JOIN_TYPES or result[0] in OPTION_JOIN_TYPES or result[0] in OWNED_JOIN_TYPES) and result[1] == 'Int')
            and not (result[0] == 'buffered_handle_exchange' and result in owned_join_sync_types)
            and not (result[0] in ('ref', 'mut') and result[1] in (*reference_structs, *EXTRA_C_TYPES))
            and not (result[0] in ('owned', *JOIN_PAYLOADS) and result[1] in ('String', 'Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS))
            and not (result[0] in ('owned', *JOIN_PAYLOADS) and result[1] in owned_aggregates)
            and not (result[0] == 'owned' and result[1] in owned_numeric_types)
            and result not in (
            ('ref', 'Int'), ('mut', 'Int'), ('mut', 'u8'), ('owned', 'Int'),
            ('scalar', 'Void'), ('void', 'Void'), ('join_owned', 'Int'), ('join_nested', 'Int'), ('handle_option', 'Int'), ('join_option', 'Int'))):
        fail(node.line, 'prototype async : résultat Int, Bool, u8, char, &str ou &u8 statique, &Int, &mut Int, <- Int, Result alloué transféré ou Void requis')
    if result[0] in ('owned', *JOIN_PAYLOADS) and owned_borrow_fields(result[1]):
        completion = node.field_effect_summary
        if completion is None or not completion.complete:
            fail(node.line, 'résultat struct async : contrat des cibles empruntées incomplet')
        for _, targets in completion.completion_result.borrowed_fields:
            if not targets or any(not (
                    target.kind in ('parameter', 'exclusive_join_parameter') and parameters[target.parameter][1] in ('ref', 'mut')
                    or target.kind == 'field_parameter' and parameters[target.parameter][1] in ('owned', *JOIN_PAYLOADS)
                    and reference_type(borrowed_field_type(parameters[target.parameter][2], stored_field_path(target.field)) or '') is not None
                    ) for target in targets):
                fail(node.line, 'résultat struct async : cible empruntée sans paramètre durable raccordé')
    returns_int = result == ('scalar', 'Int')
    returns_bool = result == ('scalar', 'Bool')
    returns_byte = result == ('byte', 'u8')
    returns_char = result == ('char', 'char')
    returns_text = result == ('text', 'str')
    returns_byte_ref = result == ('byte_ref', 'u8')
    returns_wrapped_utf8 = result[0] in UTF8_VALUE_RESULT_FAMILIES
    returns_ref = result[0] in ('ref', 'mut')
    borrowed_result_paths(node, functions, fail, result_parameters_cache, sync_contracts=sync_contracts)
    returns_owned = result[0] == 'owned'
    join_return_mode = result[0] if result[0] in JOIN_PAYLOADS else None
    returns_join = join_return_mode is not None
    returns_value = result in SCALAR_RESULTS or returns_ref or returns_owned or returns_join or returns_execution or bool(returns_array)
    result_ctype = array_result_ctype or (capture_type(*result) if returns_value else 'int')
    parameter_modes = {name: mode for name, mode, _ in parameters}
    parameter_indexes = {name: index for index, (name, _, _) in enumerate(parameters)}
    collection_types = {name: typ for name, mode, typ in parameters
                         if mode in ('ref', 'mut', 'owned') and typ in ('String', 'Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS)
                         or mode == 'owned' and typ in (*owned_numeric_types, *owned_aggregates)}
    boolean_bindings = {name for name, mode, typ in parameters if (mode, typ) == ('scalar', 'Bool')}
    numeric_bindings = {name: mode for name, mode, _ in parameters if mode in EXTRA_MODES}
    byte_bindings = {name for name, mode, _ in parameters if mode == 'byte'}
    builtin_error_bindings = {name: mode for name, mode, _ in parameters if mode in ERROR_VALUE_TYPES}
    runtime_error_bindings = {name for name, mode, _ in parameters if mode == 'runtime_error'}
    plain_join_bindings = {name: mode for name, mode, _ in parameters if mode in PLAIN_JOIN_TYPES}
    char_bindings = {name for name, mode, _ in parameters if mode == 'char'}
    text_bindings = {name for name, mode, _ in parameters if mode == 'text'}
    byte_ref_bindings = {name for name, mode, _ in parameters if mode == 'byte_ref'}
    slice_bindings = {name: SHARED_VECTOR_SLICE_MODES.get(mode, mode) for name, mode, _ in parameters
                      if mode in VECTOR_SLICE_ELEMENTS or mode in SHARED_VECTOR_SLICE_MODES}
    mutable_slices = {name for name, mode, _ in parameters if mode in SHARED_VECTOR_SLICE_MODES}
    pending_splits = {}
    tracks_utf8_captures = any(mode in ASYNC_CAPTURE_VIEW_MODES for _, mode, _ in parameters)
    static_utf8_bindings = set()
    utf8_match_results = {}
    wrapped_utf8_family_by_result = {}
    utf8_match_payloads = {}
    vector_match_payloads = {}
    utf8_match_tags = {}
    wrapped_utf8_bindings = {name: UTF8_VALUE_RESULT_FAMILIES[mode] for name, mode, _ in parameters
                             if mode in UTF8_VALUE_RESULT_FAMILIES}
    received_refs = {}
    initial_field_cells = {}
    owned_result_types = {}
    utf8_view_loans = {}
    mutable_utf8_bindings = (text_bindings | byte_ref_bindings | slice_bindings.keys()
                             | {name for name, mode, _ in parameters if mode == 'slice_result'}) & set(node.mutable_parameters)
    utf8_result_loans = {}
    arrays = {}
    array_elements = {}
    reference_rows = {parameter: (array_c_type(typ), layout) for parameter, mode, typ in parameters
                      if (layout := int_reference_layout(typ, mode))}
    prefix = f'crust_async_{variant_name or name}'
    fields = {}
    mutable = set(node.mutable_parameters)
    consumed = set()
    tasks = {}
    selections = {}
    selection_loan_sets = {}
    task_prefix_changes = {}
    executions = {}
    blocking_executions = set()
    execution_pools = {}
    task_handle_result_pools = {}
    task_handle_output_loans = {}
    task_handle_field_changes = {}
    joined_execution_values = {}
    joined_execution_loans = {}
    matched_map_slots = {}
    map_reference_payloads = {}
    dependent_waits = {}
    join_results = {}
    active_loans = {}
    guarded_receipts = {}
    result_field_outcomes = {}
    loops = []
    # Each scope records names in destruction-entry order.
    scopes = [({}, set(), set(), None, {})]
    inline_binding_scopes = {name: id(scopes[0][0]) for name in fields}
    lexical_tails = []
    statement_tails = {}
    argument_tails = []
    pending_capture_groups = []
    internal_members = []
    task_holder_count = 0
    resume_point = 0
    cleanup_paths = []
    suspended_paths = {}

    field_count = 0
    immutable_integer_members = {}

    def check_new_name(variable, line):
        if variable in fields or variable in tasks or variable in selections or variable in executions or variable in join_results:
            fail(line, f"variable '{variable}' déjà déclarée")

    def declare(variable, line):
        nonlocal field_count
        check_new_name(variable, line)
        fields[variable] = f'value_{field_count}'
        inline_binding_scopes[variable] = id(scopes[-1][0])
        field_count += 1
        return fields[variable]

    def temporary(ctype, suffix=''):
        nonlocal task_holder_count
        if ctype in ('CrustTask *', 'CrustAsyncExecution', 'CrustAsyncExecution *', 'CrustExecution'):
            task_holder_count += 1
        name = f'temporary_{len(internal_members)}'
        internal_members.append(f'    {ctype} {name}{suffix};\n')
        return f'frame->{name}'

    def task_carries_result_lock(declaration, visiting=frozenset()):
        # A transferred lock may follow the owned result through checked
        # synchronous calls or through directly awaited descendant tasks.
        name = declaration.args[0]
        if name in visiting:
            return False
        visiting = visiting | {name}
        parameters = {name for name, mode, typ in declaration.args[1]
                      if mode == 'owned' and declaration.args[2] == ('owned', typ)}

        def scalar(expression):
            if expression is None:
                return True
            op = expression[0]
            if op in ('int', 'bool', 'name', 'deref', 'field', 'array_numeric_literal'):
                return True
            if op in ('compare', 'arithmetic', 'array_numeric_operation', 'array_numeric_not'):
                return all(scalar(item) for item in expression[1:] if isinstance(item, tuple))
            return False

        def transferred_parameter(argument):
            if argument[0] == 'transfer':
                argument = argument[1]
            return argument[0] in ('move', 'down') and argument[1] in parameters

        def returns_awaited_owner(expression):
            call = expression[1]
            if call[0] != 'call' or (callee := functions.get(call[1])) is None:
                return False
            _, inputs, output, _ = callee.args
            arguments = call[2]
            if output != declaration.args[2] or len(arguments) != len(inputs):
                return False
            forwarded = owned_result_parameters(
                callee, functions, sync_result=lambda name: sync_contracts[name].result if name in sync_contracts else None)
            if not forwarded:
                return False
            for index, (argument, (_, mode, _)) in enumerate(zip(arguments, inputs, strict=True)):
                if mode == 'owned':
                    if not transferred_parameter(argument):
                        return False
                elif index in forwarded or mode not in SCALAR_TYPES or not scalar(argument):
                    return False
            return task_carries_result_lock(callee, visiting)

        def returns_owner(expression):
            if expression is None:
                return False
            if expression[0] == 'move':
                return expression[1] in parameters
            if expression[0] not in ('array_transfer', 'new_transfer'):
                return False
            call = expression[1]
            if call[0] == 'await':
                return returns_awaited_owner(call)
            if call[0] != 'call' or (contract := sync_contracts.get(call[1])) is None:
                return False
            summary = contract.result
            if (contract.result_type != declaration.args[2] or contract.lock_parameters
                    or contract.returned_lock_parameters or contract.distinct_lock_parameters
                    or contract.effects.blocking_join or any(contract.hashmap_writes)
                    or summary.structure_fields or summary.owned_field_writes or summary.owned_fields
                    or summary.borrowed_fields or summary.vector_writes or summary.handle_writes
                    or summary.reference_appends or summary.task_sources):
                return False
            candidates = summary.candidates
            if len(candidates) != 1 or (candidate := next(iter(candidates))).kind != 'parameter':
                return False
            index = candidate.parameter
            arguments = call[2]
            if (len(arguments) != len(contract.parameters) or not 0 <= index < len(arguments)
                    or index in contract.copied_lock_parameters):
                return False
            return (transferred_parameter(arguments[index])
                    and all(i == index or mode in SCALAR_TYPES and scalar(value)
                            for i, (value, (_, mode, _)) in enumerate(zip(arguments, contract.parameters))))

        def closed(body):
            for statement in body:
                if statement.op in ('yield', 'drop_value', 'print'):
                    continue
                if statement.op == 'return' and parameters:
                    if returns_owner(statement.args[0]):
                        continue
                    return False
                if statement.op in ('return', 'print_expr') and scalar(statement.args[0]):
                    continue
                if statement.op == 'var' and scalar(statement.args[1]):
                    continue
                if statement.op == 'scope' and closed(statement.args[1]):
                    continue
                if statement.op == 'if' and scalar(statement.args[0]) and all(closed(arm) for arm in statement.args[1:]):
                    continue
                return False
            return True

        supported_result = (parameters or declaration.args[2] == ('void', 'Void')
                            or declaration.args[2] in scalar_sync_types or declaration.args[2] == ('scalar', 'Bool'))
        return bool(supported_result) and closed(declaration.args[3])

    def capture_finishes_immediately(expression):
        op = expression[0]
        if op in ('name', 'move', 'down', 'ref', 'mut', 'reborrow', 'deref', 'field',
                  'int', 'bool', 'array_numeric_literal', 'text', 'char'):
            return True
        if op in ('arithmetic', 'compare'):
            operands = expression[2:]
        elif op == 'array_numeric_operation':
            operands = expression[3:]
        elif op in ('array_numeric_cast', 'array_numeric_try_from'):
            operands = expression[2:]
        elif op in ('array_numeric_not', 'array_byte_literal', 'not', 'and', 'or'):
            operands = expression[1:]
        else:
            return False
        return all(capture_finishes_immediately(operand) for operand in operands)

    def preserves_vector_positions(effects, index, parameter):
        _, mode, typ = parameter
        if mode != 'mut' or typ not in INLINE_VECTOR_ELEMENTS or effects is None or not effects.complete:
            return False
        if effects.may_suspend is not False and not effects.suspension_complete:
            return False
        for summary in (effects.completion_result, effects.suspension_result):
            if summary is None:
                continue
            if any(owner == index and (not exact or slots or replacements or removals)
                   for owner, slots, exact, replacements, removals in summary.vector_writes):
                return False
            if (any(owner == index for owner, _ in summary.structure_fields)
                    or any(owner == index for owner, _, _ in summary.owned_field_writes)):
                return False
        return True

    def create_task(expr, line, *, direct_wait=False):
        from async_structure_effects import completion_hashmap_writes
        _, callee, arguments = expr
        if sync_signature(expr) in task_sync_types:
            return sync_call(expr, line, task=True)
        declaration = functions.get(callee)
        if declaration is None:
            fail(line, f"fonction async inconnue '{callee}'")
        result_borrows = getattr(declaration, 'async_returned_handle_borrows', ())
        effects = declaration.field_effect_summary
        guarded_indexes = {index for index, _, _ in effects.guarded_writes} if effects else set()
        returned_guarded_indexes = ({index for index, _, _ in effects.returned_handle_guarded_writes}
                                    if effects else set())
        can_return_guarded = bool(returns_execution and node.field_effect_summary
                                  and node.field_effect_summary.returned_handle_guarded_writes)
        if guarded_indexes and not can_return_guarded and result[0] not in ('void', 'scalar', 'bool', 'byte', *EXTRA_MODES):
            fail(line, 'écriture de dépendance gardée : résultat appelant indépendant requis')
        guarded_holders = {}
        symbolic_guarded_holders = set()
        if len(arguments) != len(declaration.args[1]):
            fail(line, f"'{callee}' attend {len(declaration.args[1])} argument(s), reçu {len(arguments)}")
        captures, loans, returned_loans, argument_loans = [], [], [], []
        returned_result_locks = []
        argument_fields = {}
        local_captures = set()
        capture_storage = []
        capture_payload_storage = {}
        prepared_executions = []
        handle_capture_pools = {}
        dependent_captures = {}
        initial_waits = effects.handle_wait_order if effects is not None else ()
        owner_indexes = owned_result_parameters(declaration, functions,
                                                sync_result=lambda name: sync_contracts[name].result if name in sync_contracts else None)
        result_paths = {}
        utf8_indexes = utf8_result_parameters(declaration, functions, sync_contracts=sync_contracts)
        for index, path in borrowed_result_paths(declaration, functions, fail, result_parameters_cache):
            result_paths.setdefault(index, []).append(path)
        active_loans[id(loans)] = loans
        prepared_owners = []
        pending_capture_groups.append((len(scopes) - 1, prepared_owners, loans))
        argument_depth = len(argument_tails)
        try:
            for index, (argument, (_, mode, typ)) in enumerate(zip(arguments, declaration.args[1])):
                argument_loan_start = len(loans)
                if declaration.native_block and index not in declaration.native_copies:
                    check_access(argument[1], line, write=True)
                argument_tails.append((len(scopes) - 1, arguments[index + 1:]))
                if mode == 'async_execution':
                    if argument[0] in ('name', 'move', 'down'):
                        require_local_async_value(argument[1], line)
                        record = consume_execution(argument[1], line) if argument[1] in executions else None
                    else:
                        kind, record = emit_computed_transfer(argument, line)
                        if kind != 'execution':
                            record = None
                    if record is None or public_execution_type(record, typ, line) != typ:
                        fail(line, f'capture async : {typ} attendu')
                    handle_capture_pools[index] = execution_pools.get(record[0], (record[3],))
                    dependent = not autonomous_execution(record)
                    if dependent:
                        later_captures_are_immediate = all(
                            capture_finishes_immediately(following) for following in arguments[index + 1:])
                        result_mode = declaration.args[2][0]
                        payload = public_async_signature(typ, aggregate_layouts, allow_borrowed=True)
                        borrowed_payload = payload is not None and payload[0] in ('ref', 'mut')
                        ordinary_result = result_mode in ('void', 'scalar', 'bool', 'byte', 'char', 'ref', 'mut', 'array', *EXTRA_MODES)
                        independent_result = (not borrowed_payload
                                              and result_mode in ('owned', 'async_execution'))
                        if (not direct_wait or index not in initial_waits
                                or not later_captures_are_immediate or effects is None or not effects.complete
                                or record[4] and not borrowed_payload
                                or not (ordinary_result or independent_result)):
                            fail(line, 'capture AsyncHandle à dépendances : attente directe et inconditionnelle requise')
                        loans.extend(record[2])
                        loans.extend(record[4])
                        if index in result_paths:
                            if not record[4]:
                                fail(line, 'retour emprunté via AsyncHandle : cible non suivie')
                            returned_loans.extend(record[4])
                    value = f'(*{record[0]})'
                    hidden = '\0capture-execution:' + record[0]
                    executions[hidden] = record
                    scopes[-1][0][hidden] = None
                    prepared_executions.append(hidden)
                    if dependent:
                        dependent_captures[hidden] = index
                elif index in guarded_indexes or index in returned_guarded_indexes:
                    holder = argument[1] if argument[0] in ('ref', 'name') else None
                    local = (argument[0] == 'ref' and references.get(holder) == 'owned'
                             and collection_types.get(holder) == typ)
                    symbolic = (can_return_guarded and argument[0] == 'name'
                                and parameter_modes.get(holder) == 'ref' and reference_types.get(holder) == typ)
                    if not (local or symbolic):
                        fail(line, 'écriture de dépendance gardée : emprunt explicite d’un mutex possédé localement requis')
                    if symbolic:
                        symbolic_guarded_holders.add(holder)
                    check_access(holder, line, write=True)
                    invalidate_guarded_receipts(holder)
                    guarded_holders[index] = holder
                    # Reserve the graph through argument evaluation, spawn and
                    # suspension. The C ABI still receives a shared mutex.
                    loans.append((holder, 'mut'))
                    value = f'frame->{fields[holder]}'
                elif (mode, typ) in pool_sync_types:
                    value, held = pool_argument(argument, mode, typ, line)
                    loans.extend(held)
                    if index in owner_indexes:
                        returned_loans.extend((origin, 'storage') for origin in pool_storage(argument[1]))
                elif mode == 'scalar':
                    value = boolean_value(argument, line) if typ == 'Bool' else expression(argument, line)
                elif mode == 'byte':
                    value = byte_value(argument, line, context='une capture async u8')
                elif mode in EXTRA_MODES:
                    value, actual = infer_scalar_value(argument, line)
                    if actual != typ:
                        fail(line, f'capture async : attendu {typ}')
                elif mode in ERROR_VALUE_TYPES:
                    value = builtin_error_value(argument, mode, line)
                elif mode == 'runtime_error':
                    value = runtime_error_value(argument, line)
                elif mode in PLAIN_JOIN_TYPES:
                    value = plain_join_value(argument, mode, line)
                elif mode == 'char':
                    value = char_value(argument, line, context='une capture async char')
                elif mode == 'text':
                    value = static_text_value(argument, line)
                elif mode == 'byte_ref':
                    value = static_byte_ref_value(argument, line)
                elif mode in VECTOR_SLICE_ELEMENTS:
                    value = vector_view_value(argument, line, mode)
                elif mode in SHARED_VECTOR_SLICE_MODES:
                    reborrow = ('reborrow', argument[1], 'mut') if argument[0] == 'name' else argument
                    value = mutable_slice_value(reborrow, line, mode)
                    local_loans = local_utf8_loans(reborrow, value)
                    loans.extend(local_loans)
                    if index in utf8_indexes:
                        if reborrow[0] == 'reborrow' and declaration.args[2][0] in ASYNC_SHARED_VIEW_MODES:
                            source = reborrow[1]
                            returned_loans.extend(((source, 'ref'), *utf8_view_loans.get(source, ())))
                        else:
                            returned_loans.extend(local_loans)
                elif mode in UTF8_VALUE_RESULT_FAMILIES:
                    value, actual_type = infer_scalar_value(argument, line)
                    if actual_type != typ:
                        fail(line, f'capture async : attendu {typ}')
                elif mode == 'array':
                    shape, element = scalar_array_layout(typ)
                    if argument[0] == 'array_transfer':
                        argument = argument[1]
                    plan = None
                    if argument[0] == 'array_copy':
                        source, _ = array_element(argument[1], line, remaining=shape, expected_element=element)
                    elif argument[0] in ('down', 'move') and argument[1] in arrays:
                        original = argument[1]
                        require_local_async_value(original, line)
                        _, (source, actual, actual_element) = export_async_value(original, (), line)
                        if (actual, actual_element) != (shape, element):
                            fail(line, 'capture de tableau : dimensions incompatibles')
                    elif argument[0] in ('array_literal', 'array_repeat'):
                        actual, plan, _ = layout_array(argument, shape, line, element)
                        if actual != shape:
                            fail(line, 'capture de tableau : dimensions incompatibles')
                    else:
                        fail(line, 'capture de tableau par valeur : copie ou déplacement explicite requis')
                    snapshot = temporary(element, array_dimensions(shape))
                    if plan is not None:
                        initialize_array(snapshot, plan)
                    elif all(shape):
                        steps.append(f'memcpy({snapshot}, {source}, sizeof {snapshot});')
                    value = snapshot
                elif mode in ARRAY_BORROWS:
                    access = ARRAY_BORROWS[mode]
                    if argument[0] in (access + '_expr', 'array_ref' if access == 'ref' else 'array_mut_ref'):
                        projection = argument[1]
                    elif argument[0] == access and argument[1] not in parameter_modes:
                        projection = ('name', argument[1])
                    elif (argument[0] in ('name', 'reborrow') and parameter_modes.get(argument[1]) in ARRAY_BORROWS
                          and (argument[0] == 'name' or argument[2] == access)):
                        projection = ('name', argument[1])
                    else:
                        fail(line, 'capture de tableau async : emprunt explicite du mode déclaré requis')
                    row_shape = int_reference_row(typ, mode)
                    if row_shape:
                        root, indices = reference_array_path(projection)
                        if (root not in reference_rows
                                or reference_rows[root][1][len(indices):] != int_reference_layout(typ, mode)
                                or access == 'mut' and parameter_modes[root] != 'array_mut'):
                            fail(line, 'capture async : tableau de références du type déclaré requis')
                        place, (_, path) = array_element(projection, line, write=access == 'mut',
                                                         remaining=row_shape, defer_access=True,
                                                         reference_container=True)
                        reservation = ARRAY_BORROWS[parameter_modes[root]]
                        if reservation == 'mut':
                            path = ()
                        check_access(root, line, write=reservation == 'mut', path=path)
                        value, loan = f'&({place})', ((root, path), reservation)
                    else:
                        shape, element = scalar_array_layout(typ)
                        value, loan = capture_array_place(projection, access, line, remaining=shape, expected_element=element)
                    loans.append(loan)
                    (root, prefix), reservation = loan
                    if index in utf8_indexes:
                        returned_loans.append((root, reservation))
                    elif row_shape and reservation == 'mut' and index in result_paths:
                        returned_loans.append(loan)
                    else:
                        returned_loans.extend(((root, prefix + path), reservation) for path in result_paths.get(index, ()))
                elif mode in ('ref', 'mut') and sync_signature(argument) in reference_sync_types:
                    value, inherited, shape = reference_value(argument, line)
                    if shape[1] != typ or mode == 'mut' and shape[0] != 'mut':
                        fail(line, 'capture async : résultat synchrone de type ou mode incompatible')
                    active_loans.pop(id(inherited), None)
                    loans.extend(inherited)
                    if index in result_paths:
                        returned_loans.extend(inherited)
                elif mode in ('ref', 'mut') and field_reference_shape(argument) is not None:
                    value, inherited, shape = reference_value(argument, line)
                    if shape != (mode, typ):
                        fail(line, 'capture de champ : type ou mode incompatible')
                    active_loans.pop(id(inherited), None)
                    loans.extend(inherited)
                    if index in result_paths:
                        returned_loans.extend(inherited)
                elif mode == 'ref' and mutex_payload(typ):
                    value, held = sync_borrow_argument(argument, mode, typ, line)
                    loans.extend(held)
                elif mode in ('ref', 'mut') and (held := guard_borrow_argument(argument, mode, typ, line)):
                    value, inherited = held
                    loans.extend(inherited)
                    if index in result_paths:
                        returned_loans.extend(inherited)
                elif mode in ('ref', 'mut') and argument[0] == mode + '_expr' and argument[1][0] in (
                        'array_index', 'array_deref_slot'):
                    value, loan = capture_array_place(argument[1], mode, line,
                                                      expected_element=FIELD_C_TYPES.get(typ, 'int'))
                    loans.append(loan)
                    if index in result_paths:
                        returned_loans.append(loan)
                elif mode == 'owned' and argument[0] == 'transfer':
                    operand = argument[1]
                    if operand[0] in ('down', 'move') and result_lock_loans(operand[1]):
                        require_local_async_value(operand[1], line)
                        _, value = export_async_value(operand[1], (), line, depth=len(scopes))
                    else:
                        value = sync_owned_value(operand, line)
                    if owned_result_types.get(value, 'Int') != typ:
                        fail(line, 'capture par transfert : type incompatible')
                elif mode in JOIN_PAYLOADS:
                    if argument[0] not in ('down', 'transfer'):
                        fail(line, 'capture de Result alloué : transfert -> requis')
                    value, payload, _ = owned_join_value(
                        argument if argument[0] == 'down' else argument[1], line)
                    if payload != owned_wrapper_payload(mode, typ) or owned_result_types.get(value, 'Int') != wrapper_content_type(mode, typ):
                        fail(line, 'capture de Result alloué : type de Result incompatible')
                    if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
                        for arm in ('ok', 'err'):
                            held = active_loans.get(('owned_storage', value, (arm,)))
                            capture_payload_storage[index, arm] = (frozenset(origin for origin, _ in held)
                                if held is not None else storage_of(value))
                else:
                    operator, *operands = argument
                    if mode == 'owned':
                        if operator != 'down':
                            fail(line, 'capture par transfert : utiliser -> sur une allocation nommée')
                    elif operator not in (mode, 'name', 'reborrow'):
                        fail(line, 'capture async : emprunt explicite ou référence nommée requis')
                    name = operands[0]
                    if name not in fields:
                        fail(line, f"variable inconnue '{name}'")
                    if name in arrays:
                        fail(line, 'capture async : indexer le tableau pour emprunter un Int')
                    if name in boolean_bindings or name in byte_bindings and typ != 'u8':
                        typ = 'Bool' if name in boolean_bindings else 'u8'
                        fail(line, f'une capture par emprunt Int ne peut pas cibler une valeur {typ}')
                    if name in builtin_error_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler une erreur builtin')
                    if name in runtime_error_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler runtime::Error')
                    if name in plain_join_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler un Result')
                    if name in char_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler une valeur char')
                    if name in text_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler une vue &str')
                    if name in byte_ref_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler un &u8')
                    if name in slice_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler une tranche')
                    if name in wrapped_utf8_bindings:
                        fail(line, 'une capture par emprunt Int ne peut pas cibler un résultat UTF-8')
                    actual = references.get(name, 'scalar')
                    inferred = SCALAR_TYPES.get(inline_scalar_mode(name))
                    if reference_types.get(name, collection_types.get(name, inferred)) != typ:
                        fail(line, 'capture async : type incompatible avec la liaison')
                    if mode == 'owned':
                        compatible = actual == 'owned'
                    elif operator == mode:
                        compatible = actual in ('owned', 'scalar') and (mode == 'ref' or name in mutable)
                    else:
                        compatible = (actual == 'mut' or mode == actual == 'ref') and (
                            operator != 'reborrow' or operands[1] == mode)
                    if not compatible:
                        fail(line, 'capture async : mode incompatible avec la liaison')
                    shared_vector = mode == 'ref' and typ in VECTOR_SLICE_MODES
                    reservation = 'mut' if actual == 'mut' and not shared_vector else mode
                    check_access(name, line, write=reservation != 'ref')
                    value = f'frame->{fields[name]}'
                    if mode != 'owned':
                        if actual == 'owned' and typ in EXTRA_C_TYPES:
                            value = f'({EXTRA_C_TYPES[typ]} *){value}->fields'
                        elif actual in ('scalar', 'owned') and name not in collection_types:
                            value = f'&({value_place(name)})'
                        loan = (name, reservation)
                        capture_loans = (loan, *received_refs.get(name, ()))
                        loans.extend(capture_loans)
                        if (index in utf8_indexes and actual == 'mut' and typ in VECTOR_SLICE_MODES
                                and declaration.args[2][0] in (*VECTOR_SLICE_ELEMENTS, 'byte_ref')):
                            returned_loans.append((name, 'ref'))
                        elif index in result_paths and typ in reference_structs:
                            for path in result_paths[index]:
                                returned_loans.extend(project_result_field_loans(capture_loans, typ, path))
                        elif index in result_paths or index in utf8_indexes:
                            returned_loans.extend(capture_loans)
                if mode in ASYNC_SHARED_VIEW_MODES:
                    local_loans = local_utf8_loans(argument, value)
                    loans.extend(local_loans)
                    if index in utf8_indexes:
                        returned_loans.extend(local_loans)
                if tracks_utf8_captures and mode in ASYNC_CAPTURE_VIEW_MODES and not is_literal_utf8_storage(argument):
                    # This reservation has no local slot. It keeps the parent's
                    # caller-side loan alive by requiring the child to finish.
                    loans.append(('\0utf8-capture', 'ref'))
                origins = set(storage_of(value))
                for target, _ in loans[argument_loan_start:]:
                    origins.update(storage_bindings.get(loan_root(target), ()))
                if (mode, typ) in pool_sync_types:
                    origins.update(pool_storage(argument[1]))
                capture_storage.append(frozenset(origins))
                if mode in ('ref', 'mut') and typ in struct_layouts:
                    value = f'structure_reference_for((CrustStructureView){{0}}, {value})'
                captured = temporary(capture_type(mode, typ))
                if typ in struct_layouts and mode in ('ref', 'mut') and any(
                        storage_bindings.get(loan_root(target), frozenset()) & implicit_stacks
                        for target, _ in loans[argument_loan_start:]):
                    local_captures.add(index)
                if result_lock_roots() & {loan_root(target) for target, _ in loans[argument_loan_start:]}:
                    fail(line, 'capture async : instance dont un résultat maintient le verrou')
                if mode == 'owned':
                    holder = argument[1] if argument[0] == 'down' else value
                    held_lock = result_lock_loans(holder)
                    if held_lock:
                        if not task_carries_result_lock(declaration):
                            fail(line, 'capture d’un résultat portant un verrou : consommation locale ou retour direct requis')
                        loans.extend(held_lock)
                        if index in owner_indexes:
                            returned_result_locks.extend(held_lock)
                if mode in ('owned', *JOIN_PAYLOADS):
                    if mode in ('owned', *OWNED_JOIN_TYPES):
                        field_loans = owned_capture_field_loans(value, typ)
                        argument_fields.update(((index, path), group) for path, group in field_loans.items())
                        loans.extend(loan for group in field_loans.values() for loan in group)
                        for path in result_paths.get(index, ()):
                            field = '.'.join(path)
                            if (borrowed_field_type(typ, stored_field_path('.' + field)) or '').startswith('&') and not (borrowed_field_type(typ, stored_field_path('.' + field)) or '').startswith('&mut '):
                                returned_loans.extend(field_loans['.' + field])
                    if storage_of(value) & implicit_stacks:
                        if declaration.args[1][index][0] in declaration.handle_parameters:
                            fail(line, 'capture A<T> : une structure locale T ne peut pas remplacer une allocation de pool')
                        local_captures.add(index)
                    held_storage = [(origin, 'storage') for origin in storage_of(value)]
                    loans.extend(held_storage)
                    if index in owner_indexes:
                        returned_loans.extend(held_storage)
                steps.append(f'{captured} = {value};')
                if mode == 'buffered_handle_exchange' and exchange_optional(typ):
                    steps.append(f'if ({captured}.status == 0) {captured}.value = NULL;')
                captures.append(captured)
                if index in declaration.cell_reference_parameters:
                    descriptor = stored_reference_cell(captured, loans[argument_loan_start:], line)
                    captured_cell = temporary('Cell *')
                    steps.append(f'{captured_cell} = {descriptor};')
                    captures.append(captured_cell)
                if mode == 'owned':
                    if argument[0] == 'down':
                        consumed.add(name)
                        clear_stored_fields(name)
                    clear_stored_fields(value)
                    steps.append(f'{value} = NULL;')
                    prepared_owners.append(captured)
                elif mode in JOIN_PAYLOADS:
                    steps.append(f'{value}.{JOIN_CELLS[mode]} = NULL;')
                    prepared_owners.append(f'{captured}.{JOIN_CELLS[mode]}')
                if declaration.native_block and index not in declaration.native_copies:
                    consumed.add(argument[1])
                argument_loans.append(tuple(loans[argument_loan_start:]))
                argument_tails.pop()
            task = temporary('CrustTask *')
            positions_to_invalidate = {loan_root(origin)
                for index, held in enumerate(argument_loans)
                if not preserves_vector_positions(effects, index, declaration.args[1][index])
                for origin, mode in held if mode == 'mut' and loan_root(origin) in inline_vector_items}
            target = specialize(callee, frozenset(local_captures)) if specialize else callee
            if declaration.result_storage:
                plan = result_storage(declaration, local_captures)
                if plan.mixed:
                    fail(line, 'retours incompatibles : valeur locale T et allocation A<T>')
                if plan.parameters is not None:
                    returned_loans[:] = [(target, mode) for target, mode in returned_loans if mode != 'storage']
                    returned_loans.extend((origin, 'storage') for index in plan.parameters for origin in capture_storage[index])
                destination = None
                if plan.destination:
                    destination = local_destinations.get(id(expr)) or implicit_stack()
                    loans.append((destination, 'storage'))
                    returned_loans.append((destination, 'storage'))
                captures.append('&' + local_pools[destination] if destination else 'NULL')
            for index in declaration.async_returned_lock_parameters:
                requested = {(loan_root(origin), 'ref') for origin, access in argument_loans[index] if access != 'storage'}
                if not requested:
                    fail(line, 'tâche : origine du verrou retourné introuvable')
                roots = {target for target, _ in requested}
                pending = [record[2] for records in (tasks, executions) for record in records.values() if record is not None]
                pending.extend(selection.loans for selection in selections.values() if selection is not None)
                if any(roots & {loan_root(target) for target, _ in held} for held in pending):
                    fail(line, 'acquisition du verrou : instance déjà capturée par une tâche en cours')
                returned_result_locks.extend(requested)
                loans.extend(requested)
            if returned_result_locks:
                active_loans[('stored_field', task, ('result_lock',))] = list(dict.fromkeys(returned_result_locks))
            steps.append(f'{task} = crust_async_{target}_create({", ".join(captures)});')
            if declaration.args[2][0] == 'async_execution':
                from handle_types import resolve_handle_pool_origins
                task_handle_result_pools[task] = resolve_handle_pool_origins(
                    declaration.async_returned_handle_pools, handle_capture_pools)
                if result_borrows:
                    returned_loans.extend(dict.fromkeys(
                        loan for index in sorted(result_borrows) for loan in argument_loans[index]))
                output_borrows = declaration.async_returned_handle_output_borrows
                if output_borrows:
                    task_handle_output_loans[task] = tuple(dict.fromkeys(
                        loan for index in sorted(output_borrows) for loan in argument_loans[index]))
                if effects and (effects.returned_handle_fields or returned_guarded_indexes
                                or effects.returned_handle_owned_writes or effects.returned_handle_vector_updates
                                or any(effects.returned_handle_map_paths)):
                    from results import FunctionResult
                    deferred = FunctionResult('void', 'Void', structure_fields=effects.returned_handle_fields or (),
                        owned_field_writes=effects.returned_handle_owned_writes,
                        vector_writes=tuple((index, (items,), False, (), ())
                                            for index, items in effects.returned_handle_vector_updates))
                    changes = prepare_field_changes(deferred, declaration.args[1], argument_loans, line,
                                                    capture_storage, argument_fields)
                    for (category, holder, _), held in changes:
                        if category == 'owned_storage' and any(
                                origin in local_pools and binding_depth(origin) > binding_depth(holder)
                                for origin, _ in held):
                            fail(line, 'retour AsyncHandle : le pool ne survit pas au champ propriétaire')
                    definite = effects.returned_handle_definite_fields
                    required = tuple((index, tuple((field, sources) for field, sources in fields
                                                   if (index, field) in definite))
                                     for index, fields in deferred.structure_fields)
                    required = tuple((index, fields) for index, fields in required if fields)
                    required_owned = tuple((index, field, child) for index, field, child in deferred.owned_field_writes
                                           if (index, field) in definite)
                    returned_guards = {index: guarded_holders[index] for index in returned_guarded_indexes}
                    guarded = prepare_guarded_task_changes(replace(effects,
                        guarded_fields=effects.returned_handle_guarded_fields,
                        guarded_writes=effects.returned_handle_guarded_writes), argument_loans, returned_guards, line,
                        symbolic_holders=symbolic_guarded_holders)
                    required_guarded_keys = {
                        ('guarded_field', returned_guards[index], stored_field_path(field))
                        for index, fields in effects.returned_handle_guarded_fields for field, _ in fields
                        if (index, field) in definite and index in returned_guards}
                    required_guarded = tuple((key, held) for key, held in guarded if key in required_guarded_keys)
                    if (required == deferred.structure_fields and required_guarded == guarded
                            and required_owned == deferred.owned_field_writes):
                        field_paths = ((*changes, *guarded),)
                    else:
                        guaranteed = prepare_field_changes(replace(deferred, structure_fields=required,
                                                                  owned_field_writes=required_owned),
                            declaration.args[1], argument_loans, line, capture_storage, argument_fields)
                        field_paths = ((*guaranteed, *required_guarded), (*changes, *guarded))
                    map_paths = prepare_hashmap_changes(
                        effects.returned_handle_map_paths, arguments, argument_loans, line)
                    task_handle_field_changes[task] = tuple(
                        (*fields, *entries) for fields in field_paths for entries in map_paths)
            task_activity.add(('created', callee))
            for loop in loops:
                loop['created_tasks'].add(callee)
            inherited_changes = {}
            for hidden in prepared_executions:
                record = executions.pop(hidden)
                handle, _, captured_loans, nominal, _, _ = record
                steps.append(f'*({handle}) = (CrustAsyncExecution){{0}};')
                active_loans.pop(id(captured_loans), None)
                del scopes[-1][0][hidden]
                if hidden in dependent_captures:
                    inherited_changes[dependent_captures[hidden]] = record[5]
                    continue
                # Inactive cleanup and launch failure can abandon the
                # captured worker before the receiving body is polled.
                pools = {pool for pool in execution_pools.get(handle, (nominal,)) if pool in functions}
                task_activity.update(('abandoned', pool) for pool in pools)
                for loop in loops:
                    loop['abandoned_tasks'].update(pools)
            if inherited_changes:
                dependent_waits[task] = tuple(inherited_changes[index]
                                              for index in initial_waits if index in inherited_changes)
            if effects and effects.complete and (declaration.args[2][0] == 'buffered_handle_exchange' or declaration.args[2][0] in EXCHANGE_JOIN_TYPES):
                for arm, candidates in zip(('ok', 'err'), effects.completion_result.exchange_payloads):
                    origins = set()
                    for candidate in candidates:
                        if candidate.kind == 'exchange_parameter':
                            origins.update(capture_payload_storage.get((candidate.parameter,
                                ('ok', 'err')[candidate.item_index]), capture_storage[candidate.parameter]))
                        elif candidate.kind in ('parameter', 'vector_element'):
                            origins.update(capture_storage[candidate.parameter])
                        elif candidate.kind == 'fresh' and candidate.source.kind == 'source_parameter':
                            origins.update(capture_storage[candidate.source.index])
                        else:
                            origins.update(origin for held in capture_storage for origin in held)
                    active_loans[('owned_storage', task, (arm,))] = [(origin, 'storage') for origin in origins]

            from async_result_storage import borrowed_result_fields
            retain_result_fields(task, borrowed_result_fields(declaration), argument_loans, line, argument_fields)
            changes = (prepare_field_changes(effects.completion_result, declaration.args[1], argument_loans,
                                             line, capture_storage, argument_fields)
                       if effects is not None and effects.complete else ())
            reconstructed = {key[1] for key, _ in changes if key[0] == 'vector_positions'}
            for holder in positions_to_invalidate:
                guarded_receipts.pop(('vector_positions', holder, ()), None)
                if holder not in reconstructed:
                    set_vector_positions(holder, None)
            direct_guards = {index: guarded_holders[index] for index in guarded_indexes}
            changes += prepare_guarded_task_changes(effects, argument_loans, direct_guards, line,
                                                    symbolic_holders=symbolic_guarded_holders)
            # Resolve only when Select needs it; ordinary awaits may use types
            # whose suspended-field contract is still unknown.
            task_prefix_changes[task] = ((effects, declaration.args[1], tuple(argument_loans)),)
            map_changes = prepare_hashmap_changes(completion_hashmap_writes(declaration), arguments, argument_loans, line)
            alternatives = tuple((*changes, *path) for path in map_changes)
            return task, declaration.args[2] == ('scalar', 'Int'), loans, callee, returned_loans, alternatives
        except NoAsyncContinuation:
            active_loans.pop(id(loans), None)
            raise
        finally:
            del argument_tails[argument_depth:]
            pending_capture_groups.pop()

    def consume_task(name, line):
        if name not in tasks or tasks[name] is None:
            fail(line, f"tâche '{name}' inconnue ou déjà consommée")
        task = tasks[name]
        tasks[name] = None
        return task

    def discard_task(name, line):
        task, _, loans, _, _, _ = consume_task(name, line)
        steps.append(f'task_discard({task});')
        clear_stored_fields(task)
        del active_loans[id(loans)]

    def task_result_signature(record):
        """The source type includes T versus A<T>, even with the same Cell ABI.

        Only result storage participates: unrelated local captures and pools
        of owned descendants must not reclassify the returned root.
        """
        mode, typ = functions[record[3]].args[2]
        local = (any(origin in implicit_stacks for origin, access in record[4] if access == 'storage')
                 if mode in ('owned', *JOIN_PAYLOADS) and typ in struct_layouts else None)
        return mode, typ, local

    def create_selection(expr, line):
        enable_threads()
        records, hidden, signatures = [], [], set()
        for argument in expr[1]:
            if argument[0] == 'down':
                require_local_async_value(argument[1], line)
                record = consume_task(argument[1], line)
            elif argument[0] == 'transfer' and argument[1][0] == 'call' and argument[1][1] in functions:
                record = create_task(argument[1], line)
            elif argument[0] == 'transfer':
                kind, record = emit_computed_transfer(argument[1], line)
                if kind != 'task':
                    fail(line, 'Select exige des tâches inactives')
            else:
                fail(line, 'prototype : branche Select calculée non raccordée')
            if has_guarded_changes(record[5]):
                fail(line, 'écriture de dépendance gardée : branche Select non raccordée')
            if task_result_signature(record)[0] == 'async_execution' and (
                    record[4] or any(task_handle_field_changes.get(record[0], ()))):
                fail(line, 'Select : résultat AsyncHandle à dépendances non raccordé')
            signatures.add(task_result_signature(record))
            if len(signatures) != 1:
                fail(line, 'Select exige le même type de résultat et de stockage (T local / allocation A<T>) dans chaque branche')
            # Earlier constructed branches must also be destroyed if evaluating
            # a later argument suspends or leaves the enclosing scope.
            binding = '\0select_branch:' + record[0]
            tasks[binding] = record
            scopes[-1][0][binding] = None
            hidden.append(binding)
            records.append(record)
        state = temporary('CrustSelect')
        branches = temporary('CrustSelectBranch', f'[{len(records)}]')
        loans = []
        for index, (binding, record) in enumerate(zip(hidden, records)):
            task, _, held, _, _, _ = consume_task(binding, line)
            loans.extend(held)
            active_loans.pop(id(held), None)
            # Hidden construction owners cease to exist once the selection owns them.
            del tasks[binding]
            del scopes[-1][0][binding]
            steps.append(f'{branches}[{index}] = (CrustSelectBranch){{{task}, {task}->discard_suspended}};')
        loans = list(dict.fromkeys(loans))
        active_loans[id(loans)] = loans
        steps.append(f'task_select_init(&{state}, {branches}, {len(records)});')
        return SelectionState(state, tuple(records), loans)

    def discard_selection(name, line):
        selection = selections[name]
        if selection is None:
            fail(line, f"Select '{name}' déjà consommé")
        steps.append(f'if (!task_select_discardable(&{selection.c})) fail("unresolved Select cleanup");')
        steps.append(f'task_select_drop(&{selection.c});')
        active_loans.pop(id(selection.loans), None)
        for record in selection.branches:
            clear_stored_fields(record[0])
        selections[name] = None

    def selection_poll_paths(selection, line):
        # A control-flow alternative chooses a whole selection, not extra
        # branches after those of another alternative. Keep their orders apart.
        paths = []
        for path in selection.paths or (selection.branches,):
            reachable = []
            for record in path:
                if any(key[2][:1] == ('map_items',) for changes in record[5] for key, _ in changes):
                    fail(line, 'Select : effets HashMap avant la suspension non raccordés')
                if record[0] not in task_prefix_changes:
                    fail(line, 'prototype : contrat de suspension de la branche Select non raccordé')
                candidates = task_prefix_changes[record[0]]
                for effects, _, _ in candidates:
                    if effects is not None and effects.suspension_reason == 'effets suspendus de tâches lancées non raccordés':
                        fail(line, 'Select : branche pouvant perdre avec un handle lancé non attendu interdite (SL2)')
                    if effects is None or not effects.complete or not effects.suspension_complete:
                        fail(line, 'prototype : effets suspendus de la branche Select non raccordés')
                reachable.append((record, candidates))
                if all(not effects.may_suspend for effects, _, _ in candidates):
                    # Ready, or a poll that never returns: neither can reach
                    # the following branch. Its captures still belong to Select.
                    break
            paths.append(tuple(reachable))
        return tuple(paths)

    def selection_field_effects(paths, line):
        # Preserve writes of reachable winners and suspended losers. Keeping
        # the initial state in these unions is conservative across alternatives.
        for path in paths:
            for record, candidates in path:
                prefixes = [prepare_field_changes(effects.suspension_result, parameters, argument_loans, line)
                            for effects, parameters, argument_loans in candidates]
                apply_child_field_changes((*record[5], *prefixes), line, launched=True)

    def selection_loser_loans(selection, poll_paths):
        needed = set()
        for path, reachable in zip(selection.paths or (selection.branches,), poll_paths):
            winners = [record[0] for record, candidates in reachable
                       if any(effects.may_complete for effects, _, _ in candidates)]
            certain = winners[0] if len(winners) == 1 else None
            for record in path:
                if record[0] != certain:
                    needed.update(record[2])
        # Export may have removed expired local aliases from the combined
        # captures. Never restore them from a branch's construction record.
        retained = [loan for loan in selection.loans if loan in needed]
        if retained == selection.loans:
            return selection.loans
        # Equivalent waits in two control-flow arms must yield the same static
        # reservation identity, not different Python list identities.
        return selection_loan_sets.setdefault((selection.c, tuple(retained)), retained)

    def await_task(expr, line, *, returns_value, borrow=False, owned=False, joined=False, array_shape=(),
                   prepared=None, scalar_type='Int', execution=False):
        nonlocal resume_point
        if not returns_value and awaits_execution(expr):
            fail(line, 'résultat faillible du handle sans usage explicite')
        operand = expr[1]
        selection_name = operand[1] if operand[0] == 'name' and operand[1] in selections else None
        selection = None
        if selection_name is not None:
            selection = selections[selection_name]
            if selection is None or selection.awaited:
                fail(line, f"Select '{selection_name}' déjà attendu ou détruit")
            if selection_name not in mutable:
                fail(line, 'attendre Select exige une liaison let mut')
            task, returns_int, _, nominal, _, _ = selection.branches[0]
            loans = selection.loans
            poll_paths = selection_poll_paths(selection, line)
            returned_loans = list(dict.fromkeys(loan for path in poll_paths for record, candidates in path
                if any(effects.may_complete for effects, _, _ in candidates) for loan in record[4]))
            field_changes = ()
            # Check all needed contracts before emitting any poll/cleanup path.
            selection_field_effects(poll_paths, line)
        elif prepared is not None:
            task, returns_int, loans, nominal, returned_loans, field_changes = prepared
        elif operand[0] == 'call':
            task, returns_int, loans, nominal, returned_loans, field_changes = create_task(
                operand, line, direct_wait=True)
        elif operand[0] == 'name':
            task, returns_int, loans, nominal, returned_loans, field_changes = consume_task(operand[1], line)
        else:
            kind, record = emit_computed_transfer(operand, line)
            if kind != 'task':
                fail(line, '.await exige une tâche inactive')
            task, returns_int, loans, nominal, returned_loans, field_changes = record
        if has_guarded_changes(field_changes):
            fail(line, 'écriture de dépendance gardée : lancer puis attendre le handle avec execution.await')
        result_mode, result_type = functions[nominal].args[2]
        if (result_mode == 'async_execution') != execution:
            fail(line, 'un AsyncHandle retourné exige une liaison locale dédiée')
        actual_shape, array_element_type = scalar_array_layout(result_type) if result_mode == 'array' else ((), None)
        if actual_shape != array_shape:
            fail(line, 'un résultat de tableau async exige une liaison de forme compatible')
        if (result_mode in ('ref', 'mut')) != borrow:
            fail(line, 'un résultat emprunté async exige une liaison de référence dédiée')
        if (result_mode == 'owned') != owned:
            fail(line, 'un résultat transféré async exige une liaison locale')
        if (result_mode in JOIN_PAYLOADS) != joined:
            fail(line, 'un Result alloué exige une liaison locale')
        if not borrow and not owned and not joined and not array_shape and not execution:
            expected_type = SCALAR_RESULTS.get((result_mode, result_type))
            if returns_value != (expected_type is not None) or returns_value and scalar_type != expected_type:
                fail(line, f'.await exige un receveur {expected_type} pour un résultat {expected_type}' if expected_type else
                     '.await d’une tâche Void ne fournit pas de valeur')
        resume_point += 1
        ctype = capture_type(result_mode, result_type) if borrow or owned or joined or execution or result_mode in SCALAR_TYPES else 'int'
        result = temporary(array_element_type or ctype, array_dimensions(array_shape)) if returns_value else None
        output = f'&{result}' if result else 'NULL'
        if selection is not None:
            remember_suspended_cleanup(resume_point)
            steps.extend((f'frame->pc = {resume_point};', f'resume_{resume_point}: ;',
                f'CrustTaskStep selected_{resume_point} = task_select_poll(&{selection.c}, &frame->task);',
                f'if (selected_{resume_point} != TASK_STEP_RETURN) return selected_{resume_point};',
                f'if (!task_select_take(&{selection.c}, {output})) fail("invalid Select await");'))
            retained = selection_loser_loans(selection, poll_paths)
            active_loans.pop(id(loans), None)
            active_loans[id(retained)] = retained
            selections[selection_name] = replace(selection, awaited=True, loans=retained)
        else:
            remember_suspended_cleanup(resume_point, child=task,
                                       waiting_handle=task in dependent_waits)
            steps.extend((
            f'frame->pc = {resume_point};', f'resume_{resume_point}: ;',
            f'CrustTaskState child_{resume_point} = task_poll_child(&frame->task, {task});',
            f'if (child_{resume_point} == TASK_SUSPENDED) return task_child_suspension({task});',
            f'if (child_{resume_point} != TASK_COMPLETE || !task_take({task}, {output})) fail("invalid async await");',
            f'{task} = NULL;',
            ))
            del active_loans[id(loans)]
            for inherited in dependent_waits.get(task, ()):
                ordinary = tuple(tuple((key, held) for key, held in changes if key[0] != 'guarded_field')
                                 for changes in inherited)
                apply_child_field_changes(ordinary, line, launched=True)
                apply_guarded_await(inherited, None, line)
            apply_child_field_changes(field_changes, line, launched=False)
        if owned or joined:
            if selection is not None:
                for path in poll_paths:
                    for record, candidates in path:
                        if any(effects.may_complete for effects, _, _ in candidates):
                            move_stored_fields(record[0], result)
            else:
                move_stored_fields(task, result)
            owned_result_types[result] = wrapper_content_type(result_mode, result_type)
            keep_storage(result, (target for target, mode in returned_loans if mode == 'storage'))
        if result_mode in ASYNC_CAPTURE_VIEW_MODES:
            utf8_result_loans[result] = tuple(returned_loans)
        if borrow:
            awaited_reference_types[result] = result_type
            active_loans[id(returned_loans)] = returned_loans
            return result, returned_loans, result_mode
        if execution:
            pointer = f'&{result}'
            blocking_executions.add(pointer)
            execution_pools[pointer] = (
                frozenset().union(*(known_handle_result_pools(record[0], record[3])
                    for path in poll_paths for record, candidates in path
                    if any(effects.may_complete for effects, _, _ in candidates)))
                if selection is not None else known_handle_result_pools(task, nominal))
            retained = list(returned_loans)
            active_loans[id(retained)] = retained
            signature = public_async_signature(result_type, aggregate_layouts, allow_borrowed=True)
            output = inner_handle_output_loans(task, signature, retained)
            changes = task_handle_field_changes.get(task, ())
            return pointer, signature == ('scalar', 'Int'), retained, result_type, output, changes
        return result

    def consume_execution(name, line):
        execution = executions[name]
        if execution is None:
            fail(line, f"handle '{name}' déjà consommé")
        executions[name] = None
        return execution

    def autonomous_execution(record):
        handle, _, loans, nominal, returned_loans, field_changes = record
        if loans or returned_loans or any(field_changes):
            return False
        return (handle in execution_pools or nominal.startswith('runtime::AsyncHandle<') or
                nominal in functions and task_has_only_value_dependencies(functions[nominal]))

    def known_handle_result_pools(carrier, nominal):
        return task_handle_result_pools.get(carrier, frozenset(
            pool for pool in getattr(functions.get(nominal), 'async_returned_handle_pools', ())
            if isinstance(pool, str)))

    def inner_handle_output_loans(carrier, signature, captures):
        if signature is None or signature[0] not in ('ref', 'mut'):
            return []
        projection = task_handle_output_loans.get(carrier)
        if projection is None:
            return list(captures)
        return [loan for loan in captures if loan in projection]

    def task_output_projection(record):
        mode, typ = functions[record[3]].args[2]
        if mode != 'async_execution':
            return ()
        signature = public_async_signature(typ, aggregate_layouts, allow_borrowed=True)
        return inner_handle_output_loans(record[0], signature, record[4])

    def record_execution_abandonment(handle, nominal):
        pools = {pool for pool in execution_pools.get(handle, (nominal,)) if pool in functions}
        task_activity.update(('abandoned', pool) for pool in pools)
        for loop in loops:
            loop['abandoned_tasks'].update(pools)

    def abandon_execution(name, line):
        record = executions[name]
        if record is None:
            fail(line, f"handle '{name}' déjà consommé")
        handle, _, loans, nominal, _, _ = record
        if not node.numeric_profile or not autonomous_execution(record):
            fail(line, f"attente requise : le handle '{name}' doit être attendu avec .await, pas détruit ou abandonné")
        executions[name] = None
        active_loans.pop(id(loans), None)
        steps.append(f'task_abandon_async({handle});')
        record_execution_abandonment(handle, nominal)

    def require_local_async_value(name, line):
        if name not in scopes[-1][0]:
            fail(line, f"'{name}' doit être rattaché au scope courant : utiliser -> à l’entrée du bloc")

    def drop_map_owned_result(name, record):
        result = record[0]
        steps.append(f'if ({result}.status != 6) cell_drop(crust_map_result_handle(&{result}));')
        clear_stored_fields(result)
        join_results[name] = None

    def drop_async_binding(statement):
        if statement.op != 'drop_value':
            return False
        name = statement.args[0]
        record = join_results.get(name)
        if record is not None and record[1] in ('map_owned_option', 'map_owned_exchange'):
            require_local_async_value(name, statement.line)
            drop_map_owned_result(name, record)
            return True
        if record is not None and record[1] in ('map_slot', 'map_scalar', 'map_try_insert', 'map_ref_option', 'map_ref_exchange'):
            if name not in scopes[-1][4]:
                fail(statement.line, 'drop de résultat HashMap : liaison du scope courant requise')
            active_loans.pop(id(record[2]), None)
            join_results[name] = None
            return True
        if name in pool_types:
            fail(statement.line, 'un pool reste dans son scope et ne peut être transféré à drop')
        if name in wrapped_utf8_bindings or name in runtime_error_bindings or name in builtin_error_bindings or name in plain_join_bindings:
            if inline_binding_scopes.get(name) != id(scopes[-1][0]):
                fail(statement.line, 'drop exige une liaison locale du scope courant')
            check_access(name, statement.line)
            consumed.add(name)
            return True
        if name in arrays and parameter_modes.get(name) not in ARRAY_BORROWS:
            require_local_async_value(name, statement.line)
            check_access(name, statement.line, write=True)
            consumed.add(name)
            return True
        if (name in fields and name not in arrays and name not in references
                and inline_scalar_mode(name) in (*MODE_TYPES, 'bool', 'char')):
            if inline_binding_scopes.get(name) != id(scopes[-1][0]):
                fail(statement.line, 'drop exige une liaison locale du scope courant')
            check_access(name, statement.line, write=True)
            consumed.add(name)
            return True
        if name in selections:
            destroy = discard_selection
        elif name in executions:
            destroy = abandon_execution
        elif name in tasks:
            destroy = discard_task
        elif (is_owned_join(name, nested=True)
              or join_results.get(name) is not None and join_results[name][1] == 'async_execution'):
            destroy = discard_owned_join
        elif references.get(name) == 'owned':
            if parameter_modes.get(name) != 'owned' or len(scopes) != 1:
                require_local_async_value(name, statement.line)
            drop_owned(name, statement.line)
            return True
        else:
            return False
        require_local_async_value(name, statement.line)
        destroy(name, statement.line)
        return True

    def is_owned_join(name, *, nested=False):
        if name not in join_results:
            return False
        record = join_results[name]
        return record is None or record[1] in ('allocation', 'optional_allocation', 'exchange_allocation', 'rejected_allocation') or (nested and record[1] in ('nested', *OWNED_NESTED_PAYLOAD_MODES, 'optional_nested', *EXCHANGE_PAYLOAD_MODES, *OPTION_PAYLOAD_MODES))

    def consume_owned_join(name, line):
        record = join_results[name]
        if record is None:
            fail(line, f"résultat '{name}' déjà consommé")
        join_results[name] = None
        storage_bindings.pop(name, None)
        return record

    def discard_owned_join(name, line):
        result, payload, _ = consume_owned_join(name, line)
        clear_stored_fields(result)
        if payload == 'async_execution':
            handle, nominal = joined_execution_values[result]
            if joined_execution_loans.get(result):
                fail(line, 'le résultat AsyncHandle à dépendances doit être consommé avec match')
            steps.append(f'task_abandon_async({handle});')
            record_execution_abandonment(handle, nominal)
            return
        cell, success = wrapper_cleanup(result, payload)
        steps.extend((f'if ({success}) cell_drop({cell});', f'{cell} = NULL;'))

    def execution_await(expr, line, *, prepared=None):
        nonlocal resume_point
        record = (sync_call(expr[1], line, execution=True) if sync_signature(expr[1]) in handle_sync_types else
                  consume_execution(expr[1][1], line)) if prepared is None else prepared
        handle, returns_int, loans, nominal, returned_loans, field_changes = record
        mode, typ = functions[nominal].args[2]
        outer = PLAIN_RETURN_JOINS.get((mode, typ)) if mode in PLAIN_JOIN_TYPES else None
        exchange_outer = exchange_join_mode(typ if mode == 'buffered_handle_exchange' else EXCHANGE_JOIN_TYPES[mode]) if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES else None
        option_outer = option_join_mode((f'Option<{typ}>' if functions[nominal].join_storage_result == 'local' else f'Option<A<{typ}>>') if mode == 'handle_option' else OPTION_JOIN_TYPES[mode]) if mode == 'handle_option' or mode in OPTION_JOIN_TYPES else None
        owned_outer = owned_join_mode(mode) if mode in OWNED_JOIN_TYPES else None
        result = temporary(PLAIN_JOIN_C_TYPES[outer] if outer else EXCHANGE_JOIN_CTYPES[exchange_outer] if exchange_outer else OPTION_JOIN_CTYPES[option_outer] if option_outer else OWNED_JOIN_CTYPES[owned_outer] if owned_outer else 'CrustJoinResult')
        status_result = None
        payload = {'ref': 'reference', 'mut': 'mutable_reference', 'owned': 'allocation',
                   'join_owned': 'nested', 'handle_option': 'optional_nested'}.get(mode)
        if (mode, typ) == ('scalar', 'Bool'):
            payload = 'bool_value'
        if exchange_outer or option_outer or owned_outer:
            payload = JOIN_PAYLOADS[exchange_outer or option_outer or owned_outer]
        if (mode, typ) in NUMERIC_REFERENCE_FIELDS:
            payload = NUMERIC_REFERENCE_FIELDS[mode, typ]
        elif typ in struct_layouts and mode in ('ref', 'mut'):
            payload = 'mutable_structure_reference' if mode == 'mut' else 'structure_reference'
            awaited_reference_types[result] = typ
        elif (mode, typ) == ('mut', 'u8'):
            payload = 'mutable_byte_reference'
        if mode == 'async_execution':
            payload = 'async_execution'
            storage = temporary('CrustAsyncExecution')
            steps.append(f'{storage} = (CrustAsyncExecution){{0}};')
            pointer = f'&{storage}'
            execution_pools[pointer] = known_handle_result_pools(handle, nominal)
            joined_execution_values[result] = pointer, typ
            joined_execution_loans[result] = returned_loans
            if handle in task_handle_output_loans:
                task_handle_output_loans[pointer] = task_handle_output_loans[handle]
            if handle in task_handle_field_changes:
                task_handle_field_changes[pointer] = task_handle_field_changes[handle]
            take = f'task_async_take_into({handle}, &{result}, &{storage})'
        elif outer:
            payload = PLAIN_JOIN_FIELDS[outer]
            status_result = temporary('CrustJoinResult')
            steps.append(f'{result} = ({PLAIN_JOIN_C_TYPES[outer]}){{0}};')
            take = f'task_async_take_into({handle}, &{status_result}, &{result}.value)'
        elif mode in UTF8_VALUE_RESULT_FAMILIES:
            payload = mode
            take = f'task_async_take_into({handle}, &{result}, &{result}.{UTF8_VALUE_RESULT_FIELDS[mode]})'
        elif mode in VECTOR_SLICE_ELEMENTS or mode in SHARED_VECTOR_SLICE_MODES:
            payload = mode
            take = f'task_async_take_into({handle}, &{result}, &{result}.{ASYNC_VIEW_FIELDS[mode]})'
        elif mode in ('runtime_error', *ERROR_VALUE_TYPES, 'byte', 'char', 'text', 'byte_ref'):
            payload = mode + '_value'
            take = f'task_async_take_into({handle}, &{result}, &{result}.{payload})'
        elif mode in EXTRA_MODES:
            payload = NUMERIC_JOIN_FIELDS[f'join_{mode}']
            take = f'task_async_take_into({handle}, &{result}, &{result}.{payload})'
        elif mode == 'array':
            shape, element = scalar_array_layout(typ)
            storage = temporary(element, array_dimensions(shape))
            payload = storage, shape, element
            take = f'task_async_take_into({handle}, &{result}, &{storage})'
        elif payload in ('optional_nested', *EXCHANGE_PAYLOAD_MODES, *OPTION_PAYLOAD_MODES):
            status_result = temporary('CrustJoinResult')
            steps.append(f'{result} = ({OPTION_JOIN_CTYPES[option_outer] if option_outer else EXCHANGE_JOIN_CTYPES[exchange_outer]}){{0}};')
            take = f'task_async_take_into({handle}, &{status_result}, &{result}.value)'
        elif owned_outer:
            status_result = temporary('CrustJoinResult')
            steps.append(f'{result} = ({OWNED_JOIN_CTYPES[owned_outer]}){{0}};')
            take = f'task_async_take_into({handle}, &{status_result}, &{result}.value)'
        elif payload:
            take = f'task_async_take_into({handle}, &{result}, &{result}.{payload})'
        else:
            take = f'task_async_take({handle}, &{result})'
        if node.native_block:
            steps.append(f'while (!{take}) sched_yield();')
        else:
            resume_point += 1
            remember_suspended_cleanup(resume_point, waiting_handle=True)
            steps.extend((
                f'frame->pc = {resume_point};', f'resume_{resume_point}: ;',
                f'CrustTaskStep wait_{resume_point} = task_async_subscribe({handle}, &frame->task);',
                f'if (!{take}) return wait_{resume_point};',
            ))
        if status_result is not None:
            steps.append(f'{result}.status = {status_result}.status;')
        del active_loans[id(loans)]
        apply_child_field_changes(tuple(tuple((key, held) for key, held in changes if key[0] != 'guarded_field')
                                        for changes in field_changes), line, launched=True, receipt=result)
        apply_guarded_await(field_changes, result, line)
        if mode in ('owned', *JOIN_PAYLOADS):
            move_stored_fields(handle, result)
            owned_result_types[result] = wrapper_content_type(mode, typ)
            keep_storage(result, (target for target, access in returned_loans if access == 'storage'))
        if mode in ('ref', 'mut') or mode in ASYNC_CAPTURE_VIEW_MODES and returned_loans:
            active_loans[id(returned_loans)] = returned_loans
        else:
            if mode == 'async_execution' and returned_loans:
                active_loans[id(returned_loans)] = returned_loans
            returned_loans = None
        scalar_payload = 'value' if returns_int else None
        return result, payload or scalar_payload, returned_loans

    def awaits_execution(expr):
        return expr[0] == 'await' and (sync_signature(expr[1]) in handle_sync_types or
                                      expr[1][0] == 'name' and expr[1][1] in executions)

    def computed_await(expr):
        return expr[0] == 'await' and expr[1][0] not in ('name', 'call')

    def bind_execution_result(name, result, body, position, *, export_name=None, annotation=None, mutable_result=False):
        if name == '_' or (name != export_name and not has_future_value_use(name, body[position + 1:])):
            fail(body[position].line, f"résultat faillible '{name}' sans usage explicite")
        plain = next((mode for mode, field in PLAIN_JOIN_FIELDS.items()
                      if result[1] == field and result[2] is None), None)
        expected = (f'Result<{joined_execution_values[result[0]][1]},runtime::Error>'
                    if result[1] == 'async_execution' else PLAIN_JOIN_TYPES.get(plain))
        if annotation is not None and annotation != expected:
            fail(body[position].line, 'annotation incompatible avec le résultat du handle')
        if plain is not None:
            member = declare(name, body[position].line)
            plain_join_bindings[name] = plain
            steps.append(f'frame->{member} = {result[0]};')
            if not mutable_result and result[0] in result_field_outcomes:
                result_field_outcomes[f'frame->{member}'] = result_field_outcomes[result[0]]
            result = f'frame->{member}', result[1], None
            if mutable_result:
                mutable.add(name)
        join_results[name] = result
        if result[1] == 'async_execution' or is_owned_join(name, nested=True):
            scopes[-1][0][name] = None
            storage_bindings[name] = storage_of(result[0])
        if result[2] is not None:
            track_result(name, result[2], body, position)

    def require_owned_result_use(statement, body, position, export_name=None):
        name = statement.args[0]
        if name == '_':
            fail(statement.line, 'un motif _ ne peut pas écarter une allocation possédée')
        if name != export_name and not utf8_value_live(body[position + 1:], name, owned=True):
            fail(statement.line, f"résultat propriétaire '{name}' sans usage explicite")

    def public_execution_type(record, expected, line):
        from handle_types import contextual_public_type, public_storage
        payload_shape = expected.replace('runtime::AsyncHandle<', 'runtime::Handle<', 1)
        actual = contextual_public_type(record[3], payload_shape, functions)
        if node.numeric_profile and actual.endswith('<Bool>'):
            actual = actual.removesuffix('<Bool>') + '<bool>'
        if record[0] in blocking_executions:
            actual = actual.replace('runtime::Handle<', 'runtime::AsyncHandle<', 1)
        required = public_storage(payload_shape, aggregate_layouts)
        if required is not None:
            local = any(target in implicit_stacks for target, access in record[4] if access == 'storage')
            if local != (required == 'local'):
                fail(line, f'handle {expected} : exigence de stockage {required} non satisfaite')
        return actual

    def bind_transferred_value(name, kind, value, statement):
        if statement.annotation is not None and kind != 'array':
            expected = (public_execution_type(value, statement.annotation, statement.line) if kind == 'execution' else
                        (f'Option<{owned_result_types.get(value[0], "Int")}>' if storage_of(value[0]) & implicit_stacks else
                         f'Option<A<{owned_result_types.get(value[0], "Int")}>>') if kind == 'handle_option' else
                        f'Result<A<{owned_result_types.get(value[0], "Int")}>,A<{owned_result_types.get(value[0], "Int")}>>' if kind == 'buffered_handle_exchange' else
                        f'Result<(),A<{owned_result_types.get(value[0], "Int")}>>' if kind == 'buffered_handle_try_push' else
                        (owned_result_types.get(value, 'Int') if storage_of(value) & implicit_stacks else
                         f'A<{owned_result_types.get(value, "Int")}>') if kind == 'owned' else None)
            if statement.annotation != expected:
                if kind == 'execution':
                    fail(statement.line, f'annotation de handle : attendu {statement.annotation}, reçu {expected}')
                fail(statement.line, 'annotation incompatible avec le résultat transféré')
        if kind == 'array':
            source, shape, element = value
            if statement.annotation is not None and scalar_array_layout(statement.annotation) != (shape, element):
                fail(statement.line, 'tableau async : dimensions incompatibles avec le type déclaré')
            member = declare(name, statement.line)
            arrays[name] = shape
            array_elements[name] = element
            scopes[-1][0][name] = None
            if statement.mutable:
                mutable.add(name)
            if all(shape):
                steps.append(f'memcpy(frame->{member}, {source}, sizeof frame->{member});')
        elif kind == 'owned':
            member = declare(name, statement.line)
            storage_bindings[name] = storage_of(value)
            move_stored_fields(value, name)
            references[name] = 'owned'
            received_type = owned_result_types.get(value, 'Int')
            if received_type in reference_structs:
                reference_types[name] = received_type
            if received_type != 'Int':
                collection_types[name] = received_type
            if statement.mutable:
                mutable.add(name)
            scopes[-1][0][name] = None
            steps.append(f'frame->{member} = {value};')
        elif kind in OWNED_WRAPPER_TYPES:
            join_results[name] = value
            storage_bindings[name] = storage_of(value[0])
            scopes[-1][0][name] = None
        elif kind == 'selection':
            selections[name] = value
            scopes[-1][0][name] = None
            if statement.mutable:
                mutable.add(name)
        else:
            (tasks if kind == 'task' else executions)[name] = value

    def ends_in_transfer(body):
        return isinstance(body, list) and body and body[-1].op == '<-' and not body[-1].terminated

    def has_transfer_result(expr):
        if expr[0] == 'match_expr':
            return any(ends_in_transfer(arm[3]) for arm in expr[1].args[1])
        if expr[0] == 'value_match' and expr[1] and expr[1][-1].op == 'if_yield':
            expr = expr[1][-1].args[0]
        return expr[0] == 'if_expr' and any(ends_in_transfer(arm) for arm in expr[2:])

    def vector_push_new_value(expr, line, *, following=None):
        receiver = push_new_receiver(expr)
        typ = collection_types.get(receiver)
        if typ not in ('Vector<Int>', 'Vector<u8>') or expr[3]:
            fail(line, 'push_new exige un Vector sans argument')
        if not (references.get(receiver) == 'mut'
                or references.get(receiver) == 'owned' and receiver in mutable):
            fail(line, 'push_new exige un Vector mutable')
        if following is not None:
            release_statement_loans(following, earlier=(expr,))
        check_access(receiver, line, write=True)
        element = 'Int' if typ == 'Vector<Int>' else 'u8'
        ctype = 'int' if element == 'Int' else 'uint8_t'
        initial = temporary(ctype)
        pointer = temporary(ctype + ' *')
        steps.extend((f'{initial} = 0;',
                      f'{pointer} = vector_push_new(frame->{fields[receiver]}, &{initial});'))
        loans = [(receiver, 'mut'), *received_refs.get(receiver, ())]
        active_loans[id(loans)] = loans
        return pointer, loans, element

    def joined_reference_shape(subject):
        if subject[0] == 'name' and subject[1] in join_results:
            record = join_results[subject[1]]
            if record is not None:
                if record[1] in ('structure_reference', 'mutable_structure_reference'):
                    return ('mut' if record[1] == 'mutable_structure_reference' else 'ref', awaited_reference_types[record[0]])
                if record[1] in NUMERIC_REFERENCE_SIGNATURES:
                    return NUMERIC_REFERENCE_SIGNATURES[record[1]]
                return {'reference': ('ref', 'Int'), 'mutable_reference': ('mut', 'Int'),
                        'mutable_byte_reference': ('mut', 'u8')}.get(record[1])
        if subject[0] != 'await':
            return None
        operand = subject[1]
        if (signature := sync_signature(operand)) in handle_sync_types:
            payload = public_signature(signature[1], aggregate_layouts)
            return payload if payload[0] in ('ref', 'mut') else None
        nominal = None
        if operand[0] == 'name' and executions.get(operand[1]) is not None:
            nominal = executions[operand[1]][3]
        elif operand[0] == 'task_spawn':
            operand = operand[1]
            if operand[0] == 'transfer' and operand[1][0] == 'call':
                nominal = operand[1][1]
            elif operand[0] == 'down' and tasks.get(operand[1]) is not None:
                nominal = tasks[operand[1]][3]
        signature = functions[nominal].args[2] if nominal is not None else None
        return signature if signature and signature[0] in ('ref', 'mut') else None

    def reference_shape(expr, bindings=None):
        # Probe without evaluating; reference_value checks every continuing arm.
        if sync_signature(expr) in reference_sync_types:
            return sync_signature(expr)
        if shape := field_reference_shape(expr, bindings):
            return shape
        if expr[0] == 'deref':
            name = expr[1]
            shape = (bindings.get(name) if bindings is not None else
                     (references.get(name), reference_types.get(name)))
            if shape and shape[0] == 'map_shared_ref_slot':
                return 'ref', shape[1][1:]
        if expr[0] in ('ref', 'mut') and expr[1] in fields and references.get(expr[1]) in (None, 'owned'):
            typ = collection_types.get(expr[1], 'Bool' if expr[1] in boolean_bindings else
                                       SCALAR_TYPES.get(inline_scalar_mode(expr[1])))
            if typ in ('Int', 'u8', *EXTRA_C_TYPES, *reference_aggregates) and expr[1] not in arrays:
                return expr[0], typ
        if expr[0] == 'reborrow' and (payload := mutex_payload(collection_types.get(expr[1]), GUARD_TYPES)):
            return expr[2], payload
        if bindings is None:
            bindings = {name: (mode, reference_types.get(name, 'Int'))
                        for name, mode in references.items()
                        if mode in ('ref', 'mut') and name not in collection_types}
        if expr[0] == 'match_expr':
            match = expr[1]
            holder, arms = match.args
            typ = reference_types.get(holder, collection_types.get(holder))
            for _, variant, pattern, body in arms:
                local = bindings.copy()
                for field, alias in pattern:
                    declared = dict(enum_layouts.get(typ, {}).get(variant, ())).get(field)
                    if declared and declared.startswith('&'):
                        local[alias] = ('mut' if (match.mutable or match.consuming) and declared.startswith('&mut ') else 'ref',
                                        declared.removeprefix('&').removeprefix('mut '))
                    elif declared and declared.startswith('A<'):
                        local[alias] = None if match.consuming else ('mut' if match.mutable else 'ref', declared[2:-1])
                    else:
                        local[alias] = None
                for statement in body:
                    if statement.op == 'var':
                        local[statement.args[0]] = reference_shape(statement.args[1], local)
                    elif statement.op in ('if_yield', 'match_yield'):
                        value = ('name', statement.args[0]) if statement.op == 'match_yield' else statement.args[0]
                        if shape := reference_shape(value, local):
                            return shape
            return None
        if expr[0] == 'loop_expr':
            for value, _, definitions in reference_loop_exits(expr[1].args[0]):
                local = bindings.copy()
                for binding in definitions:
                    local[binding.args[0]] = reference_shape(binding.args[1], local)
                if value is not None and (shape := reference_shape(value, local)) is not None:
                    return shape
            return None
        if expr[0] == 'value_match':
            nodes = expr[1]
            local = bindings.copy()
            if nodes and nodes[0].op == 'var':
                local[nodes[0].args[0]] = joined_reference_shape(nodes[0].args[1])
            if nodes and nodes[-1].op == 'if_yield':
                return reference_shape(nodes[-1].args[0], local)
            return None
        if expr[0] == 'utf8_value' and expr[1][0] == 'name':
            return bindings.get(expr[1][1])
        if expr[0] in ('name', 'reborrow'):
            shape = bindings.get(expr[1])
            return (expr[2], shape[1]) if shape and expr[0] == 'reborrow' else shape
        if expr[0] == 'await':
            shape = await_signature(expr)
            return shape if shape and shape[0] in ('ref', 'mut') else None
        if (receiver := push_new_receiver(expr)) is not None:
            typ = collection_types.get(receiver)
            return ('mut', 'Int' if typ == 'Vector<Int>' else 'u8') if typ in VECTOR_SLICE_MODES else None
        if expr[0] in ('ref_expr', 'mut_expr') and expr[1][0] in ('array_index', 'array_deref_slot'):
            projection = expr[1][1] if expr[1][0] == 'array_deref_slot' else expr[1]
            collection = collection_index_type(projection)
            if collection == HANDLE_VECTOR and expr[1][0] == 'array_deref_slot':
                return ('mut' if expr[0] == 'mut_expr' else 'ref', 'Int')
            if collection in ('Vector<Int>', 'Vector<u8>'):
                return ('mut' if expr[0] == 'mut_expr' else 'ref', 'Int' if collection == 'Vector<Int>' else 'u8')
            root, _ = reference_array_path(projection)
            if root in arrays:
                return ('mut' if expr[0] == 'mut_expr' else 'ref', 'u8' if array_elements.get(root) == 'uint8_t' else 'Int')
        if expr[0] in ('if_expr', 'scope'):
            for arm in (expr[2:] if expr[0] == 'if_expr' else (expr[2],)):
                if isinstance(arm, tuple):
                    shape = reference_shape(arm, bindings)
                else:
                    local, shape = bindings.copy(), None
                    for statement in arm:
                        if statement.op == 'var':
                            local[statement.args[0]] = reference_shape(statement.args[1], local)
                        elif statement.op == 'if_yield':
                            shape = reference_shape(statement.args[0], local)
                if shape:
                    return shape
        return None

    def surviving_reference_loans(loans, depth, line):
        departing = {id(scope[0]) for scope in scopes[depth:]}
        retained = []
        for target, mode in loans:
            root = loan_root(target)
            if inline_binding_scopes.get(root) in departing:
                if root in received_refs:
                    continue  # Its underlying targets are independently checked.
                fail(line, 'emprunt de cible locale non durable dans le scope parent')
            retained.append((target, mode))
        return retained

    def reference_value(expr, line, *, following=None):
        if expr[0] == 'match_expr':
            return match_enum(expr[1], valued=True, following=following, boolean=None, reference_result=True)
        if sync_signature(expr) in reference_sync_types:
            return sync_call(expr, line, following=following, borrow=True)
        if expr[0] in ('ref', 'mut') and (shape := reference_shape(expr)) is not None:
            pointer, loans = sync_borrow_argument(expr, *shape, line)
            active_loans[id(loans)] = loans
            return pointer, loans, shape
        if expr[0] == 'loop_expr':
            kind, record = emit_loop(expr[1].args[0], line, valued=True, following=following)
            if kind != 'reference':
                fail(line, 'résultat emprunté de boucle requis')
            return record
        if expr[0] == 'value_match':
            return match_async_result(expr[1], line, following=following, boolean=None, reference_result=True)
        if expr[0] == 'if_expr':
            test = condition_value(expr[1], line)
            return emit_branches(test, expr[2], expr[3], line, valued=True, construct='if',
                                 following=following, boolean=None, reference_result=True)
        if expr[0] == 'scope':
            return emit_region_block(expr[2], expr[3] if len(expr) > 3 else None,
                                 line, valued=True, construct='bloc',
                                 following=following, boolean=None, reference_result=True)
        if push_new_receiver(expr) is not None:
            pointer, loans, typ = vector_push_new_value(expr, line, following=following)
            return pointer, loans, ('mut', typ)
        if expr[0] == 'await':
            pointer, loans, mode = await_task(expr, line, returns_value=True, borrow=True)
            return pointer, loans, (mode, awaited_reference_types[pointer])
        shape = reference_shape(expr)
        if shape is None or shape not in reference_sync_types:
            fail(line, 'expression empruntée Int ou mutable u8 requise')
        mode, typ = shape
        if field_reference_shape(expr) is not None:
            pointer, loans = borrow_struct_field(expr, mode, line)
        elif expr[0] == 'deref' and references.get(expr[1]) == 'map_shared_ref_slot':
            name = expr[1]
            check_access(name, line)
            pointer = f'*frame->{fields[name]}'
            loans = list(received_refs[name])
        elif held := guard_borrow_argument(expr, mode, typ, line):
            pointer, loans = held
        elif expr[0] in ('ref_expr', 'mut_expr'):
            pointer, loan = capture_array_place(expr[1], mode, line, expected_element=FIELD_C_TYPES.get(typ, 'int'))
            loans = [loan]
        elif expr[0] in ('name', 'reborrow'):
            name = expr[1]
            original = references.get(name)
            if original not in ('ref', 'mut') or mode == 'mut' and original != 'mut':
                fail(line, 'mode incompatible avec la référence source')
            reservation = 'mut' if original == 'mut' else mode
            check_access(name, line, write=reservation == 'mut')
            pointer = f'frame->{fields[name]}'
            loans = [(name, reservation), *received_refs.get(name, ())]
        else:
            fail(line, 'expression empruntée non prise en charge')
        if typ in struct_layouts:
            pointer = f'structure_reference_for((CrustStructureView){{0}}, {pointer})'
        active_loans[id(loans)] = loans
        return pointer, loans, shape

    def bind_special(statement, body, position, *, export_name=None):
        name, initializer = statement.args
        if initializer[0] == 'array_drop_result':
            inner = initializer[1]
            initializer = consumed_result_expression(inner, collection_types.get(inner[1][1]))
        operator = initializer[0]
        if operator == 'array_hashmap_method' and initializer[1] in ('get', 'get_mut', 'insert', 'remove', 'try_insert'):
            from hashmap_syntax import method_result
            check_new_name(name, statement.line)
            result, payload, _ = emit_hashmap_operation(initializer, statement.line)
            table, typ, _, mode = matched_map_slots[result]
            if statement.annotation not in (None, method_result(initializer[1], typ)) or statement.compact_transfer:
                fail(statement.line, 'annotation de résultat HashMap incompatible')
            loans = [(table, mode), *received_refs.get(table, ())] if payload == 'map_slot' else []
            if payload in ('map_ref_option', 'map_ref_exchange'):
                loans = list(dict.fromkeys(loan for held in map_reference_payloads[result].values() for loan in held))
            if loans:
                active_loans[id(loans)] = loans
            if payload in ('map_owned_option', 'map_owned_exchange'):
                scopes[-1][0][name] = None
            track_result(name, loans, body, position)
            join_results[name] = result, payload, loans
            return True
        if operator == 'array_hashmap_new':
            nominal = initializer[1]
            _, value_type = map_types(nominal)
            owned = map_handle_element(value_type) is not None
            layout = (map_value_layout(value_type) if owned or map_shared_element(value_type)
                      else map_scalar_layout(value_type))
            if layout is None:
                fail(statement.line, 'construction HashMap async : valeur scalaire, A<T> numérique ou référence partagée requise')
            check_new_name(name, statement.line)
            require_owned_result_use(statement, body, position, export_name)
            destination = implicit_stack()
            cell = temporary('Cell *')
            ctype = layout[1]
            steps.append(f'{cell} = crust_map_cell_new(&{local_pools[destination]}, '
                         f'{region_limits[-1] or 16 * 1024 * 1024}, sizeof({ctype}), _Alignof({ctype}), {int(owned)});')
            owned_result_types[cell] = nominal
            keep_storage(cell, (destination,))
            active_loans['storage_root', cell, ()] = [(destination, 'storage')]
            bind_transferred_value(name, 'owned', cell, statement)
            return True
        if operator in ('array_mutex_new', 'array_mutex_lock', 'array_mutex_acquire'):
            bind_mutex(statement, initializer, body[position + 1:])
            return True
        if operator in ('array_handle_exchange', 'array_buffered_replace', 'array_handle_try_push', 'array_buffered_try_push',
                        'array_handle_exchange_value', 'array_buffered_exchange_take'):
            check_new_name(name, statement.line)
            require_owned_result_use(statement, body, position, export_name)
            if operator in ('array_handle_exchange_value', 'array_buffered_exchange_take'):
                source = initializer[1][1]
                record = handle_exchange_record(source, statement.line)
                arm = 'ok' if initializer[2][1] == 0 else 'err'
                value = temporary('Cell *')
                origins = active_loans.get(('owned_storage', record[0], (arm,)))
                keep_storage(value, (origin for origin, _ in origins) if origins is not None else storage_of(record[0]))
                consume_owned_join(source, statement.line)
                for key, held in list(active_loans.items()):
                    if isinstance(key, tuple) and key[0] == 'stored_field' and key[1] == record[0] and key[2][:1] == (arm,):
                        active_loans[('stored_field', value, key[2][1:])] = list(held)
                clear_stored_fields(record[0])
                steps.extend((f'{value} = {record[0]}.value;', f'{record[0]}.value = NULL;'))
                owned_result_types[value] = owned_result_types.get(record[0], 'Int')
                kind = 'owned'
            else:
                value = handle_replace_value(initializer, statement.line, following=body[position + 1:])
                appending = operator in ('array_handle_try_push', 'array_buffered_try_push')
                kind = 'buffered_handle_try_push' if appending else 'buffered_handle_exchange'
                value = value, ('rejected_allocation' if appending else 'exchange_allocation'), None
            bind_transferred_value(name, kind, value, statement)
            return True
        if operator in ('array_pop_handle', 'array_handle_option_pop', 'array_handle_option_value'):
            check_new_name(name, statement.line)
            require_owned_result_use(statement, body, position, export_name)
            if operator == 'array_handle_option_value':
                source = initializer[1][1]
                record = handle_option_record(source, statement.line)
                value = temporary('Cell *')
                move_stored_fields(record[0], value)
                keep_storage(value, storage_of(record[0]))
                consume_owned_join(source, statement.line)
                steps.extend((f'{value} = {record[0]}.value;', f'{record[0]}.value = NULL;'))
                owned_result_types[value] = owned_result_types.get(record[0], 'Int')
                kind = 'owned'
            else:
                value = handle_pop_value(initializer, statement.line, following=body[position + 1:])
                kind = 'handle_option' if operator == 'array_handle_option_pop' else 'owned'
                if kind == 'handle_option':
                    value = (value, 'optional_allocation', None)
            bind_transferred_value(name, kind, value, statement)
            return True
        if operator in ('move', 'down') and initializer[1] in local_pools:
            fail(statement.line, 'un pool local ne peut être transféré')
        if operator == 'task_select' or operator == 'move' and initializer[1] in selections:
            check_new_name(name, statement.line)
            if statement.annotation is not None or statement.compact_transfer:
                fail(statement.line, 'Select exige une liaison locale de type inféré')
            if operator == 'task_select':
                selection = create_selection(initializer, statement.line)
            else:
                original = initializer[1]
                require_local_async_value(original, statement.line)
                selection = selections[original]
                if selection is None:
                    fail(statement.line, f"Select '{original}' déjà consommé")
                selections[original] = None
            selections[name] = selection
            names = scopes[-1][0]
            if operator == 'move':
                previous = tuple(names)
                names.clear()
                for existing in previous:
                    names[existing] = None
                    if existing == original:
                        names[name] = None
            else:
                names[name] = None
            if statement.mutable:
                mutable.add(name)
            return True
        if operator in ('ref', 'mut', 'reborrow') and initializer[1] in pool_types:
            source_name = initializer[1]
            mode = initializer[2] if operator == 'reborrow' else operator
            if (source_name in local_pools) == (operator == 'reborrow'):
                fail(statement.line, 'emprunt de pool : & sur une référence ajoute un niveau ; utiliser &* ou &mut *')
            if mode == 'mut' and references[source_name] != 'mut':
                fail(statement.line, 'emprunt mutable de pool : accès mutable requis')
            expected = '&' + ('mut ' if mode == 'mut' else '') + pool_types[source_name]
            if statement.annotation not in (None, expected) or statement.compact_transfer:
                fail(statement.line, 'annotation ou transfert incompatible avec un emprunt de pool')
            reservation = 'mut' if source_name not in local_pools and references[source_name] == 'mut' else mode
            check_access(source_name, statement.line, write=reservation == 'mut')
            loans = [(source_name, reservation), *received_refs.get(source_name, ())]
            member = declare(name, statement.line)
            references[name] = mode
            reference_types[name] = pool_types[name] = pool_types[source_name]
            pool_alias_origins[name] = pool_storage(source_name)
            received_refs[name] = loans
            active_loans[id(loans)] = loans
            track_result(name, loans, body, position)
            steps.append(f'frame->{member} = frame->{fields[source_name]};')
            return True
        if operator == 'source':
            check_handle_payload(initializer[3], statement.line)
            if initializer[1] != 'pool' or initializer[3] not in ('Int', *owned_numeric_types, 'String', 'Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS, *pool_structures, *owned_enums):
                fail(statement.line, 'prototype async : type de pool local non pris en charge')
            if statement.annotation is not None or statement.compact_transfer:
                fail(statement.line, 'un pool local ne peut être transféré ni annoté comme allocation')
            member = declare(name, statement.line)
            source = temporary('Source')
            typ = initializer[3]
            factory = f'source_pool({initializer[2]})'
            if typ in pool_structures or typ in owned_enums:
                variants = owned_enums[typ] if typ in owned_enums else {'': pool_structures[typ]}
                arm = temporary('Source', f'[{len(variants)}]')
                for tag, (variant, layout) in enumerate(variants.items()):
                    offsets = temporary('size_t', f'[{max(1, len(layout))}]')
                    kinds = temporary('unsigned char', f'[{max(1, len(layout))}]')
                    steps.append(f'{arm}[{tag}] = source_pool_layout({initializer[2]}, {structure_offset(layout, len(layout))});')
                    for index, (_, field_type) in enumerate(layout):
                        steps.extend((f'{offsets}[{index}] = {structure_offset(layout, index)};',
                                      f'{kinds}[{index}] = {field_kind(field_type)};'))
                    steps.extend((f'{arm}[{tag}].arm_name = "{variant}";', f'{arm}[{tag}].field_count = {len(layout)};',
                                  f'{arm}[{tag}].field_offsets = {offsets};', f'{arm}[{tag}].field_kinds = {kinds};'))
                factory = f'source_enum_pool({arm}, {len(variants)}, "{typ}")'
            elif typ in owned_numeric_types:
                factory = f'source_pool_layout({initializer[2]}, sizeof({FORMATS[typ].c_type}))'
            elif typ != 'Int':
                vectors = temporary('VectorStorage')
                steps.append(f'{vectors} = (VectorStorage){{0}};')
                factory = f'source_vector_pool({initializer[2]}, &{vectors})'
            steps.extend((f'{source} = {factory};', f'frame->{member} = &{source};'))
            references[name] = 'mut' if statement.mutable else 'ref'
            reference_types[name] = pool_types[name] = f'Pool<{typ}>'
            local_pools[name] = source
            scopes[-1][0][name] = None
            return True
        owned_initializer = initializer[1] if operator in ('array_transfer', 'new_transfer') else initializer
        if (handle_remove_receiver(owned_initializer) is not None
                or inline_vector_source(owned_initializer) is not None and inline_vector_source(owned_initializer)[2]):
            if operator not in ('array_transfer', 'new_transfer'):
                fail(statement.line, 'remove de A<Int> exige un transfert <- explicite')
            check_new_name(name, statement.line)
            require_owned_result_use(statement, body, position, export_name)
            value = sync_owned_value(owned_initializer, statement.line, following=body[position + 1:])
            bind_transferred_value(name, 'owned', value, statement)
            return True
        if sync_signature(owned_initializer) in output_join_types:
            check_new_name(name, statement.line)
            require_owned_result_use(statement, body, position, export_name)
            mode, typ = sync_signature(owned_initializer)
            value, _ = sync_call(owned_initializer, statement.line, following=body[position + 1:], owned=True)
            bind_transferred_value(name, owned_wrapper_kind(mode, typ), (value, owned_wrapper_payload(mode, typ), None), statement)
            return True
        if (sync_signature(owned_initializer) in owned_output_types or owned_initializer[0] in ('new', 'new_enum')
                or structure_copy_source(owned_initializer) is not None or inline_vector_source(owned_initializer) is not None):
            check_new_name(name, statement.line)
            require_owned_result_use(statement, body, position, export_name)
            value = (pool_new_value(owned_initializer, statement.line, following=body[position + 1:],
                                    label=name if '\0' not in name else 'temporary')
                     if owned_initializer[0] in ('new', 'new_enum') else
                     sync_owned_value(initializer, statement.line, following=body[position + 1:]))
            bind_transferred_value(name, 'owned', value, statement)
            return True
        if (operator != 'name' and push_new_receiver(initializer) is None
                and reference_shape(initializer) in reference_sync_types):
            if statement.compact_transfer:
                fail(statement.line, 'une référence ne transfère pas une allocation')
            check_new_name(name, statement.line)
            pointer, loans, (mode, typ) = reference_value(initializer, statement.line, following=body[position + 1:])
            annotation = '&' + ('mut ' if mode == 'mut' else '') + typ
            if statement.annotation not in (None, annotation):
                fail(statement.line, 'annotation incompatible avec le type emprunté')
            member = declare(name, statement.line)
            references[name], reference_types[name] = mode, typ
            if statement.mutable:
                mutable.add(name)
            received_refs[name] = loans
            track_result(name, loans, body, position)
            steps.append(f'frame->{member} = {pointer};')
            return True
        if push_new_receiver(initializer) is not None:
            if statement.compact_transfer:
                fail(statement.line, 'push_new renvoie un emprunt, pas une allocation transférée')
            check_new_name(name, statement.line)
            pointer, loans, typ = vector_push_new_value(initializer, statement.line,
                                                       following=body[position + 1:])
            if statement.annotation not in (None, '&mut ' + typ):
                fail(statement.line, 'push_new : annotation incompatible avec le type de la case')
            member = declare(name, statement.line)
            references[name] = 'mut'
            reference_types[name] = typ
            if statement.mutable:
                mutable.add(name)
            received_refs[name] = loans
            track_result(name, loans, body, position)
            steps.append(f'frame->{member} = {pointer};')
            return True
        if operator in ('array_split', 'array_split_half'):
            bind_vector_split(statement, body, position)
            return True
        task_creation = operator == 'call' and (initializer[1] in functions or sync_signature(initializer) in task_sync_types)
        handle_creation = sync_signature(initializer) in handle_sync_types
        task_move = operator == 'move' and initializer[1] in tasks
        handle_move = operator == 'move' and initializer[1] in executions
        join_move = operator == 'move' and is_owned_join(initializer[1], nested=True)
        owned_move = operator == 'move' and references.get(initializer[1]) == 'owned'
        join = awaits_execution(initializer)
        await_mode = await_result_mode(initializer)
        joined_await = await_mode in JOIN_PAYLOADS
        block = operator == 'scope' and initializer[2]
        export = ends_in_transfer(block)
        conditional_move = has_transfer_result(initializer)
        if not (operator in ('task_spawn', 'loop_expr') or task_creation or handle_creation or task_move or handle_move
                or join_move or owned_move or join or joined_await or export or conditional_move):
            return False
        array_annotation = statement.annotation is not None and scalar_array_layout(statement.annotation)[0]
        async_handle_annotation = (statement.annotation or '').startswith('runtime::AsyncHandle<')
        handle_annotation = (statement.annotation or '').startswith('runtime::Handle<')
        if (statement.annotation is not None and operator != 'loop_expr'
                and not (join and (statement.annotation in PLAIN_JOIN_TYPES.values()
                                  or statement.annotation.startswith('Result<runtime::AsyncHandle<')))
                and not (handle_annotation or async_handle_annotation)
                and not (array_annotation and (export or conditional_move))) or statement.compact_transfer:
            fail(statement.line, 'une tâche, un handle ou son résultat exige une nouvelle liaison locale')
        check_new_name(name, statement.line)
        if operator == 'loop_expr':
            if statement.annotation is not None and statement.annotation not in SCALAR_MODES and not array_annotation and not (handle_annotation or async_handle_annotation):
                fail(statement.line, 'annotation de résultat de boucle async incompatible')
            kind, value = emit_loop(initializer[1].args[0], statement.line, valued=True,
                                    following=body[position + 1:])
            if kind in SCALAR_TYPES:
                typ = SCALAR_TYPES[kind]
                if statement.annotation not in (None, typ):
                    fail(statement.line, 'annotation de résultat de boucle async incompatible')
                if typ.startswith('Result<') and (name == '_' or
                        name != export_name and not has_future_value_use(name, body[position + 1:])):
                    fail(statement.line, f"résultat faillible '{name}' sans usage explicite")
                member = declare(name, statement.line)
                record_inline_type(name, typ)
                track_utf8_binding(statement, initializer, value, typ, body, position)
                if statement.mutable:
                    mutable.add(name)
                steps.append(f'frame->{member} = {value};')
            else:
                bind_transferred_value(name, kind, value, statement)
        elif conditional_move:
            kind, result = emit_transferred_control(initializer, statement.line, following=body[position + 1:])
            bind_transferred_value(name, kind, result, statement)
        elif export:
            kind, value = emit_computed_transfer(initializer, statement.line, following=body[position + 1:])
            bind_transferred_value(name, kind, value, statement)
        elif handle_creation:
            executions[name] = sync_call(initializer, statement.line, execution=True, following=body[position + 1:])
        elif operator == 'task_spawn':
            if async_handle_annotation and initializer[2:] != ('blocking',):
                fail(statement.line, 'un AsyncHandle annoté exige runtime::spawn_blocking')
            if node.numeric_profile and handle_annotation and initializer[2:] == ('blocking',):
                fail(statement.line, 'runtime::spawn_blocking retourne un AsyncHandle')
            executions[name] = spawn_task(initializer[1], statement.line,
                blocking=len(initializer) > 2 and initializer[2] == 'blocking',
                native=len(initializer) > 2 and initializer[2] == 'native')
        elif joined_await:
            signature = await_signature(initializer)
            value = await_task(initializer, statement.line, returns_value=True, joined=True)
            join_results[name] = value, owned_wrapper_payload(*signature), None
        elif join:
            bind_execution_result(name, execution_await(initializer, statement.line), body, position,
                                  export_name=export_name, annotation=statement.annotation,
                                  mutable_result=statement.mutable)
        elif owned_move:
            original = initializer[1]
            require_local_async_value(original, statement.line)
            check_access(original, statement.line, write=True)
            # Renaming keeps the original frame slot and destruction entry.
            fields[name] = fields[original]
            inline_binding_scopes[name] = id(scopes[-1][0])
            references[name] = 'owned'
            if original in collection_types:
                collection_types[name] = collection_types[original]
            consumed.add(original)
            storage_bindings[name] = storage_bindings.pop(original, frozenset())
            move_stored_fields(original, name)
            if original in reference_types:
                reference_types[name] = reference_types[original]
            if statement.mutable:
                mutable.add(name)
        elif handle_move or task_move or join_move:
            require_local_async_value(initializer[1], statement.line)
            if join_move:
                join_results[name] = consume_owned_join(initializer[1], statement.line)
                storage_bindings[name] = storage_of(join_results[name][0])
            elif handle_move:
                executions[name] = consume_execution(initializer[1], statement.line)
            else:
                tasks[name] = consume_task(initializer[1], statement.line)
        else:
            tasks[name] = create_task(initializer, statement.line)
        if handle_annotation or async_handle_annotation:
            if name not in executions or executions[name] is None:
                fail(statement.line, 'annotation de handle : un handle lancé est requis')
            actual_type = public_execution_type(executions[name], statement.annotation, statement.line)
            if statement.annotation != actual_type:
                fail(statement.line, f'annotation de handle incompatible : {actual_type} attendu, reçu {statement.annotation}')
        if references.get(name) == 'owned' or is_owned_join(name, nested=True):
            require_owned_result_use(statement, body, position, export_name)
        if owned_move or name in tasks or name in executions or is_owned_join(name, nested=True):
            names = scopes[-1][0]
            if task_move or handle_move or join_move or owned_move:
                previous = tuple(names)
                names.clear()
                for existing in previous:
                    names[existing] = None
                    if existing == initializer[1]:
                        names[name] = None
            else:
                names[name] = None
        return True

    def bind_mutex(statement, initializer, following):
        nonlocal resume_point
        name = statement.args[0]
        line = statement.line
        operation, nominal, operand = initializer
        if statement.annotation not in (None, nominal):
            fail(line, f'annotation de mutex incompatible avec {nominal}')
        check_new_name(name, line)
        destination = implicit_stack()
        source = '&' + local_pools[destination]
        cell = temporary('Cell *')
        label = name if '\0' not in name else 'garde'
        moved_payload = None
        if operation == 'array_mutex_new':
            payload = mutex_payload(nominal)
            asynchronous = int(nominal.startswith('AsyncMutex<'))
            if mutex_structure_payload(payload):
                if operand[0] == 'name':
                    operand = ('move', operand[1])
                value = sync_owned_value(operand, line, following=following)
                storage = storage_of(value)
                if owned_result_types.get(value) != payload or not storage & implicit_stacks:
                    fail(line, f'constructeur de mutex : valeur locale {payload} attendue')
                steps.append(f'{cell} = crust_make_object_mutex({source}, {asynchronous}, {value}, "{label}");')
                keep_storage(cell, storage | {destination})
                steps.append(f'{value} = NULL;')
                moved_payload = value
            elif scalar_field_mode(payload):
                value, actual = infer_scalar_value(operand, line, following=following)
                if actual != ('Bool' if payload == 'bool' else payload):
                    fail(line, f'constructeur de mutex : {payload} attendu')
                saved = temporary(FIELD_C_TYPES.get(payload, 'int'))
                steps.extend((f'{saved} = {value};',
                              f'{cell} = crust_make_mutex({source}, {asynchronous}, '
                              f'&{saved}, sizeof({saved}), "{label}");'))
            else:
                fail(line, 'constructeur de mutex : structure locale de type représenté requise')
        else:
            asynchronous = nominal.startswith('AsyncMutexGuard<')
            if asynchronous != (operation == 'array_mutex_acquire'):
                fail(line, 'l’acquisition d’un AsyncMutex exige lock().await')
            if operand[0] != 'name' or operand[1] not in fields:
                fail(line, 'lock exige un mutex nommé')
            receiver = operand[1]
            check_access(receiver, line)
            requested = {receiver, *(loan_root(target) for target, _ in received_refs.get(receiver, ()))}
            if any(key[0] == 'mutex_guard' and requested.intersection(loan_root(target) for target, _ in held)
                   for key, held in active_loans.items() if isinstance(key, tuple)):
                fail(line, 'verrou déjà maintenu par une garde vivante sur cette instance')
            pointer = f'frame->{fields[receiver]}'
            if asynchronous:
                wait, guard = temporary('CrustMutexWait'), temporary('CrustAsyncGuard')
                resume_point += 1
                remember_suspended_cleanup(resume_point, mutex_wait=wait)
                steps.extend((f'crust_mutex_wait_init(&{wait});',
                              f'{guard} = (CrustAsyncGuard){{0}};',
                              f'frame->pc = {resume_point};', f'resume_{resume_point}: ;',
                              f'CrustTaskStep lock_{resume_point} = crust_async_mutex_poll('
                              f'&crust_mutex_cell({pointer})->lock.async, &{wait}, &frame->task, &{guard});',
                              f'if (lock_{resume_point} != TASK_STEP_RETURN) return lock_{resume_point};',
                              f'{cell} = crust_take_async_guard({source}, &{guard}, "{label}");'))
            else:
                steps.append(f'{cell} = crust_lock_sync_mutex({source}, {pointer}, "{label}");')
            active_loans[('mutex_guard', name)] = [(receiver, 'ref'), *received_refs.get(receiver, ())]
        owned_result_types[cell] = nominal
        keep_storage(cell, storage_of(cell) | {destination})
        bind_transferred_value(name, 'owned', cell, statement)
        if moved_payload is not None:
            move_stored_fields(moved_payload, name)
            root = active_loans.get(('storage_root', name, ()))
            if root is not None:
                active_loans['storage_root', name, ()] = list(dict.fromkeys((*root, (destination, 'storage'))))

    def suspend():
        nonlocal resume_point
        resume_point += 1
        remember_suspended_cleanup(resume_point)
        steps.extend((f'frame->pc = {resume_point};', 'return TASK_STEP_YIELD;', f'resume_{resume_point}: ;'))

    def remember_suspended_cleanup(point, *, child=None, waiting_handle=False, mutex_wait=None):
        """Describe live storage without consuming the verifier's live bindings.

        A suspended branch has not completed its surrounding expressions: the
        awaited child and earlier moved arguments therefore precede its scopes.
        Borrow descriptors themselves have no runtime destructor. This snapshot
        does not invent an implicit join for an outstanding launched handle.
        """
        if any(typ.startswith('MutexGuard<') and references.get(name) == 'owned' and name not in consumed
               for name, typ in collection_types.items()):
            fail(node.line, 'une garde de Mutex synchrone doit être détruite avant une suspension')
        cleanup = [f'crust_mutex_wait_discard(&{mutex_wait});'] if mutex_wait else []
        children, select_checks, seen = [], [], set()
        blocked = waiting_handle or any(value is not None for value in executions.values())

        def owned_child(task):
            children.append(task)
            cleanup.extend((f'if (!task_drop_owned({task})) fail("unresolved suspended child cleanup");',
                            f'{task} = NULL;'))

        if child is not None:
            owned_child(child)
        for _, cells, _ in reversed(pending_capture_groups):
            for cell in reversed(cells):
                if isinstance(cell, tuple):
                    if cell[0] == 'execution':
                        blocked = True
                    else:
                        owned_child(cell[1])
                else:
                    cleanup.extend((f'if ({cell}) cell_drop({cell});', f'{cell} = NULL;'))
        for names, *_ in reversed(scopes):
            for name in reversed(names):
                if name in seen:
                    continue
                seen.add(name)
                if name in local_pools:
                    cleanup.append(f'source_close(&{local_pools[name]});')
                elif name in arrays:
                    continue
                elif name in join_results:
                    record = join_results[name]
                    if record is None:
                        continue
                    result, payload, _ = record
                    if payload == 'async_execution':
                        handle, nominal = joined_execution_values[result]
                        if joined_execution_loans.get(result):
                            blocked = True
                        else:
                            cleanup.append(f'task_abandon_async({handle});')
                            record_execution_abandonment(handle, nominal)
                        continue
                    if payload in ('map_owned_option', 'map_owned_exchange'):
                        cleanup.append(f'if ({result}.status != 6) cell_drop(crust_map_result_handle(&{result}));')
                        continue
                    if payload not in OWNED_WRAPPER_PAYLOADS.values():
                        continue
                    cell, success = wrapper_cleanup(result, payload)
                    cleanup.extend((f'if ({success}) cell_drop({cell});', f'{cell} = NULL;'))
                elif references.get(name) == 'owned':
                    if name not in consumed:
                        cell = f'frame->{fields[name]}'
                        cleanup.extend((f'if ({cell}) cell_drop({cell});', f'{cell} = NULL;'))
                elif name in tasks and tasks[name] is not None:
                    owned_child(tasks[name][0])
                elif name in selections and selections[name] is not None:
                    selection = selections[name]
                    select_checks.append(f'task_select_discardable(&{selection.c})')
                    cleanup.append(f'task_select_drop(&{selection.c});')
        suspended_paths[point] = tuple(cleanup), tuple(children), blocked, tuple(select_checks)

    def control_state(depth=None):
        orders = tuple(tuple(name for name in names
                             if tasks.get(name) is not None or executions.get(name) is not None
                             or selections.get(name) is not None
                             or join_results.get(name) is not None
                             or (references.get(name) == 'owned' and name not in consumed))
                       for names, *_ in scopes[:depth])
        refs = tuple(scope[4].copy() for scope in scopes[:depth])
        visible = set().union(*(ref.keys() for ref in refs)) if refs else set()
        views = {name: loans for name, loans in utf8_view_loans.items() if name in visible}
        storage = {name: origins for name, origins in storage_bindings.items()
                   if name in set().union(*(scope[0].keys() for scope in scopes[:depth])) and name not in consumed}
        return tasks.copy(), executions.copy(), active_loans.copy(), consumed.copy(), join_results.copy(), orders, views, refs, storage, selections.copy(), inline_vector_items.copy(), guarded_receipts.copy()

    def non_utf8_control_state(state, *, ignore_stored_fields=False):
        task_state, handles, active, dead, joins, orders, views, refs, storage, selects, items, receipts = state
        mutable_ids = {id(loans) for local in refs for name, (loans, _) in local.items()
                       if name in mutable_utf8_bindings}
        return (task_state, handles, {key: value for key, value in active.items()
                                    if key not in mutable_ids and not (
                                        ignore_stored_fields and isinstance(key, tuple)
                                        and key[0] in ('stored_field', 'owned_storage', 'storage_root'))},
                dead, joins, orders,
                {name: value for name, value in views.items() if name not in mutable_utf8_bindings},
                tuple({name: value for name, value in local.items() if name not in mutable_utf8_bindings}
                      for local in refs), selects)

    def merge_utf8_control_states(left, right, line, message):
        if non_utf8_control_state(left, ignore_stored_fields=True) != non_utf8_control_state(right, ignore_stored_fields=True):
            fail(line, message)
        tasks_state, handles, active, dead, joins, orders, views, refs, selects = non_utf8_control_state(left, ignore_stored_fields=True)
        active, views = active.copy(), views.copy()
        # A conditional field store keeps every possible target. An untouched
        # branch still contains the capture-time field, not an empty loan.
        # Backedges widen these same field targets through the retry engine.
        for key in left[2].keys() | right[2].keys():
            if isinstance(key, tuple) and key[0] == 'storage_root':
                if key in left[2] and key in right[2]:
                    active[key] = list(dict.fromkeys((*left[2][key], *right[2][key])))
            elif isinstance(key, tuple) and key[0] in ('stored_field', 'owned_storage'):
                _, holder, path = key
                initial = initial_stored_field_loans(holder,path) if key[0] == 'stored_field' else ()
                active[key] = list(dict.fromkeys((*left[2].get(key, initial),
                                                 *right[2].get(key, initial))))
        refs = [local.copy() for local in refs]
        for depth, (left_refs, right_refs) in enumerate(zip(left[7], right[7], strict=True)):
            for name in (left_refs.keys() | right_refs.keys()) & mutable_utf8_bindings:
                loans = list(dict.fromkeys((*left[6].get(name, ()), *right[6].get(name, ()))))
                views[name] = tuple(loans)
                refs[depth][name] = loans, float('inf')
                if any(name in state[7][depth] and id(state[7][depth][name][0]) in state[2]
                       for state in (left, right)):
                    active[id(loans)] = loans
        storage = {name: left[8].get(name, frozenset()) | right[8].get(name, frozenset())
                   for name in left[8].keys() | right[8].keys()}
        items = {name: left[10].get(name) if left[10].get(name) == right[10].get(name) else None
                 for name in left[10].keys() | right[10].keys()}
        receipts = {key: receipt for key, receipt in left[11].items() if right[11].get(key) == receipt}
        return tasks_state, handles, active, dead, joins, orders, views, tuple(refs), storage, selects, items, receipts

    def restore_control_state(state):
        nonlocal tasks, selections, executions, active_loans, consumed, join_results, utf8_view_loans, storage_bindings, inline_vector_items
        nonlocal guarded_receipts
        tasks, executions, active_loans, consumed, join_results, orders, utf8_view_loans, refs, storage, selections, items, receipts = state
        guarded_receipts = receipts.copy()
        inline_vector_items = items.copy()
        selections = selections.copy()
        storage_bindings = storage.copy()
        tasks, executions, active_loans = tasks.copy(), executions.copy(), active_loans.copy()
        consumed, join_results = consumed.copy(), join_results.copy()
        utf8_view_loans = utf8_view_loans.copy()
        for scope, local_refs in zip(scopes, refs, strict=True):
            scope[4].clear()
            scope[4].update(local_refs)
        for (names, *_), order in zip(scopes, orders, strict=True):
            for name in order:
                del names[name]
                names[name] = None

    def map_owned_result_payload(result, status, name, line):
        _, declared, _, _ = matched_map_slots[result]
        origins = frozenset(origin for origin, _ in owned_storage_fields(result).get((status,), ()))
        member = declare(name, line)
        references[name] = 'owned'
        element = map_handle_element(declared)
        if element != 'Int':
            collection_types[name] = element
        storage_bindings[name] = origins
        scopes[-1][0][name] = None
        steps.append(f'frame->{member} = crust_map_result_handle(&{result});')

    def invalidate_map_receipts(category, table, key):
        for receipt in tuple(guarded_receipts):
            kind, holder, path = receipt
            if (kind == category and holder == table and path[:1] == ('map_items',)
                    and (key is None or path[1] in (None, key))):
                del guarded_receipts[receipt]

    def known_map_key(expression):
        op = expression[0]
        if op in ('int', 'bool') or (op == 'array_numeric_literal' and numeric_type(expression[1]) in FORMATS
                                     and not FORMATS[numeric_type(expression[1])].precision):
            return int(expression[-1]) & ((1 << 64) - 1)
        if op == 'array_byte_literal':
            return known_map_key(expression[1])
        if op in ('name', 'ref'):
            return immutable_integer_members.get(fields.get(expression[1]))
        return None

    def map_shared_element(typ):
        if not typ.startswith('&'):
            return None
        element = typ[1:]
        if ('ref', element) in reference_sync_types and map_scalar_layout(element):
            return element
        return None

    def emit_hashmap_operation(subject, line):
        _, method, receiver, argument, *arguments = subject
        is_lookup = method in ('get', 'get_mut')
        is_insert = method in ('insert', 'try_insert')
        mode = 'ref' if method == 'get' else 'mut'
        if receiver[0] != 'name' or not (mapping := map_types(
                reference_types.get(receiver[1], collection_types.get(receiver[1])))):
            fail(line, f'HashMap.{method} async : table nommée requise')
        table = receiver[1]
        key_type, value_type = mapping
        shared_ref_slot = method == 'get' and value_type.startswith('&') and not value_type.startswith('&mut ')
        owned = map_handle_element(value_type)
        reference = map_shared_element(value_type) if not is_lookup else None
        layout = (map_value_layout(value_type) if shared_ref_slot or owned or reference
                  else map_scalar_layout(value_type))
        if layout is None or is_lookup and value_type == 'bool':
            fail(line, f'HashMap.{method} async : type de valeur non raccordé')
        access = references.get(table)
        if (access not in ('owned', 'ref', 'mut') or mode == 'mut'
                and not (access == 'mut' or access == 'owned' and table in mutable)):
            fail(line, f'HashMap.{method} async : emprunt de table incompatible')
        contracted_operation = (reference or owned) and method in ('insert', 'remove', 'try_insert')
        injected_change = (contracted_operation and access == 'mut'
                           and table in parameter_modes and any(node.hashmap_writes))
        if (owned or reference) and not is_lookup and (access != 'owned' or table in parameter_modes) and not injected_change:
            fail(line, 'mutation des dépendances HashMap : table locale ou contrat de terminaison requis')
        check_access(table, line, write=mode == 'mut')
        incoming_storage = frozenset()
        incoming_refs = ()
        known_key = known_map_key(argument) if is_insert or argument[0] == 'ref' else None
        preparation = [(table, mode), *received_refs.get(table, ())]
        active_loans[id(preparation)] = preparation
        try:
            if is_insert:
                key, actual = infer_scalar_value(argument, line)
                if actual != ('Bool' if key_type == 'bool' else key_type):
                    fail(line, f'HashMap.{method} async : clé {key_type} attendue')
                saved_key = temporary('uint64_t')
                steps.append(f'{saved_key} = (uint64_t)({key});')
                if owned:
                    operand = arguments[0]
                    if operand[0] in ('down', 'move'):
                        require_local_async_value(operand[1], line)
                        kind, incoming = export_async_value(operand[1], (), line)
                    elif operand[0] in ('transfer', 'array_transfer'):
                        kind, incoming = 'owned', sync_owned_value(operand[1], line)
                    else:
                        fail(line, f'HashMap.{method} async : transfert explicite de {value_type} requis')
                    if kind != 'owned' or owned_result_types.get(incoming, 'Int') != owned:
                        fail(line, f'HashMap.{method} async : valeur {value_type} attendue')
                    incoming_storage = storage_of(incoming)
                    if incoming_storage & implicit_stacks:
                        fail(line, 'une entrée A<T> exige une allocation de pool')
                    depth = 0 if injected_change else binding_depth(table) + 1
                    require_durable_storage(incoming, depth, line)
                    clear_stored_fields(incoming)
                elif reference:
                    incoming, held = sync_borrow_argument(arguments[0], 'ref', reference, line)
                    if not injected_change:
                        incoming_refs = tuple(surviving_reference_loans(held, binding_depth(table) + 1, line))
                    elif method == 'try_insert':
                        incoming_refs = tuple(held)
                else:
                    incoming, actual = infer_scalar_value(arguments[0], line)
                    if actual != ('Bool' if value_type == 'bool' else value_type):
                        fail(line, f'HashMap.{method} async : valeur {value_type} attendue')
                saved_value = temporary(layout[1])
                steps.append(f'{saved_value} = {incoming};')
                call = f'crust_map_write(frame->{fields[table]}, {saved_key}, &{saved_value}, {int(method == "try_insert")})'
            elif key_type == 'bool':
                if argument[0] != 'ref' or argument[1] not in boolean_bindings:
                    fail(line, f'HashMap.{method} async : emprunt de clé bool requis')
                check_access(argument[1], line)
                key = f'frame->{fields[argument[1]]}'
            else:
                pointer, _ = sync_borrow_argument(argument, 'ref', key_type, line)
                key = f'*({pointer})'
            if not is_insert:
                call = f'crust_map_lookup(frame->{fields[table]}, (uint64_t)({key}), {int(method == "remove")})'
        finally:
            active_loans.pop(id(preparation), None)
        lookup = temporary('CrustMapResult')
        steps.append(f'{lookup} = {call};')
        matched_map_slots[lookup] = table, value_type, layout[1], mode
        payload = 'map_slot' if is_lookup else 'map_scalar'
        if method == 'try_insert':
            payload = 'map_try_insert'
        if injected_change:
            fallible = method == 'try_insert'
            if owned:
                payload = 'map_owned_exchange' if fallible else 'map_owned_option'
                if fallible and incoming_storage:
                    active_loans[('owned_storage', lookup, (5,))] = [(origin, 'storage') for origin in incoming_storage]
            else:
                payload = 'map_ref_exchange' if fallible else 'map_ref_option'
                map_reference_payloads[lookup] = {0: (), 5: incoming_refs}
        if (owned or reference) and not is_lookup and not injected_change:
            fallible = method == 'try_insert'
            if owned:
                payload = 'map_owned_exchange' if fallible else 'map_owned_option'
                category = 'owned_storage'
                added = tuple((origin, 'storage') for origin in incoming_storage)
            else:
                payload = 'map_ref_exchange' if fallible else 'map_ref_option'
                category = 'stored_field'
                added = incoming_refs
            entry_path = ('map_items', known_key)
            entries = {key[2]: held for key, held in active_loans.items()
                       if isinstance(key, tuple) and key[:2] == (category, table) and key[2][:1] == ('map_items',)}
            previous = tuple(dict.fromkeys(loan for path, held in entries.items()
                                           if known_key is None or path[1] in (None, known_key) for loan in held))
            if owned:
                if previous:
                    active_loans[('owned_storage', lookup, (0,))] = list(previous)
                if fallible and added:
                    active_loans[('owned_storage', lookup, (5,))] = list(added)
            else:
                map_reference_payloads[lookup] = {0: previous, 5: added if fallible else ()}
            invalidate_map_receipts(category, table, known_key)
            storage_key = (category, table, entry_path)
            if is_insert:
                initial = tuple(entries.get(entry_path, ()))
                completed = tuple(dict.fromkeys((*initial, *added))) if known_key is None else added
                held = tuple(dict.fromkeys((*initial, *completed))) if fallible else completed
                install_field_change(storage_key, held)
                if fallible:
                    guarded_receipts[storage_key] = lookup
                    remember_result_outcomes(lookup, ((storage_key, completed, initial),))
            elif known_key is not None:
                install_field_change(storage_key, ())
        return lookup, payload, None

    def match_async_result(nodes, line, *, valued=True, transfer_result=False, following=None, boolean=False, reference_result=False):
        # A value enum with one variant still evaluates and type-checks its
        # subject. Its single arm does not require a two-branch Result shape.
        if len(nodes) == 3 and tuple(n.op for n in nodes[:2]) == ('var', 'var'):
            tag = nodes[1].args[1]
            subject = nodes[0].args[1]
            builtin = builtin_error_mode(subject)
            if tag[0] == 'utf8_tag' and (builtin is not None or tag[2] in tuple(('int', v) for v in ERROR_VALUE_TAGS.values())):
                value, typ = infer_scalar_value(subject, line, following=following)
                mode = ERROR_VALUE_MODES.get(typ)
                if mode is None:
                    fail(line, 'match : erreur builtin requise')
                return match_builtin_error(nodes, mode, value, line, valued=valued, transfer_result=transfer_result,
                                           following=following, boolean=boolean, reference_result=reference_result)
            computed_error = (tag[0] == 'utf8_tag' and tag[2] == ('int', 0)
                              and subject[0] in ('scope', 'if_expr', 'loop_expr', 'value_match')
                              and (nodes[2].op == 'scope' or nodes[2].op == 'if_yield'
                                   and nodes[2].args[0][0] == 'scope'))
            prepared_error = None
            if computed_error:
                prepared_error, error_type = infer_scalar_value(subject, line, following=following)
                if error_type in ERROR_VALUE_MODES:
                    return match_builtin_error(nodes, ERROR_VALUE_MODES[error_type], prepared_error, line,
                                               valued=valued, transfer_result=transfer_result,
                                               following=following, boolean=boolean, reference_result=reference_result)
                if error_type != 'runtime::Error':
                    fail(line, 'match : une valeur d’erreur est requise')
            if tag[0] == 'utf8_tag' and (tag[2] == ('int', 15) or is_runtime_error(subject) or computed_error):
                if tag[2] not in (('int', 0), ('int', 15)) or tag[3] != ('int', 0):
                    fail(line, 'match runtime::Error : variante incompatible')
                value = prepared_error if prepared_error is not None else runtime_error_value(subject, line, following=following)
                snapshot = temporary('CrustRuntimeError')
                steps.append(f'{snapshot} = {value};')
                steps.append(f'if ({snapshot} != CRUST_RUNTIME_LAUNCH_FAILED) abort();')
                if valued:
                    if reference_result:
                        return reference_value(nodes[2].args[0], line, following=following)
                    return infer_scalar_value(nodes[2].args[0], line, following=following)
                if nodes[2].op != 'scope':
                    fail(line, 'match runtime::Error : un seul bras attendu')
                return emit_branches(None, nodes[2].args[1], None, line, valued=False,
                                     construct='match runtime::Error', following=following)
        branch_op = 'if_yield' if valued else 'if'
        if (len(nodes) != 3 or tuple(node.op for node in nodes) != ('var', 'var', branch_op)
                or not nodes[0].utf8_match_subject):
            fail(line, 'match async : résultat de handle requis')
        subject = nodes[0].args[1]
        if subject[0] == 'array_hashmap_method' and subject[1] in ('get', 'get_mut', 'insert', 'remove', 'try_insert'):
            map_result = emit_hashmap_operation(subject, line)
        elif subject[0] == 'name' and (record := join_results.get(subject[1])) is not None and record[1] in ('map_slot', 'map_scalar', 'map_try_insert', 'map_owned_option', 'map_owned_exchange', 'map_ref_option', 'map_ref_exchange'):
            map_result = record
            if record[1] in ('map_slot', 'map_owned_option', 'map_owned_exchange', 'map_ref_option', 'map_ref_exchange'):
                check_access(subject[1], line)
                join_results[subject[1]] = None
                active_loans.pop(id(record[2]), None)
        else:
            map_result = None
        if map_result is not None:
            lookup, payload, _ = map_result
            tag = nodes[1].args[1]
            branch = nodes[2].args[0] if valued else ('if_expr', *nodes[2].args)
            if payload in ('map_try_insert', 'map_owned_exchange', 'map_ref_exchange'):
                if tag[:3] != ('utf8_tag', ('name', nodes[0].args[0]), ('int', 17)):
                    fail(line, 'HashMap.try_insert async : match Ok(Some), Ok(None) et Err requis')
                arms = {}
                while isinstance(branch, tuple) and branch[0] == 'if_expr':
                    _, condition, body, branch = branch
                    if (condition[:3] != ('compare', '==', ('name', nodes[1].args[0]))
                            or condition[3] not in (('int', 0), ('int', 5), ('int', 6))
                            or condition[3][1] in arms):
                        fail(line, 'HashMap.try_insert async : motif incompatible')
                    arms[condition[3][1]] = body
                    if not valued and len(branch) == 1 and branch[0].op == 'if':
                        # The parser emits one nested if for a three-arm statement.
                        nested = branch[0]
                        if nested.args[0][:3] == ('compare', '==', ('name', nodes[1].args[0])):
                            branch = ('if_expr', *nested.args)
                if isinstance(branch, tuple) and branch[0] == 'scope':
                    branch = branch[2]
                for status in (0, 5, 6):
                    arms.setdefault(status, branch)
                return emit_branches(f'{lookup}.status', None, None, line, valued=valued,
                                     construct='match HashMap.try_insert',
                                     map_match=(lookup, arms, payload == 'map_owned_exchange'),
                                     following=following, transfer_result=transfer_result,
                                     boolean=boolean, reference_result=reference_result)
            if (tag[0] != 'utf8_tag' or tag[2] != ('int', 4) or branch[0] != 'if_expr'
                    or branch[1][:2] != ('compare', '==')
                    or branch[1][3] not in (('int', 0), ('int', 6))):
                fail(line, 'HashMap async : match Some et None requis')
            _, condition, yes, no = branch
            status = condition[3][1]
            if payload in ('map_owned_option', 'map_ref_option'):
                return emit_branches(f'{lookup}.status', None, None, line, valued=valued,
                                     construct='match HashMap', map_match=(lookup, {status: yes, 6 if status == 0 else 0: no}, payload == 'map_owned_option'),
                                     following=following, transfer_result=transfer_result,
                                     boolean=boolean, reference_result=reference_result)
            return emit_branches(f'{lookup}.status == {status}', yes, no, line, valued=valued,
                                 construct='match HashMap',
                                 join_payload=(lookup, payload, status, None, True, None),
                                 following=following, transfer_result=transfer_result,
                                 boolean=boolean, reference_result=reference_result)
        if (subject[0] == 'method_call' and subject[1][0] == 'name' and subject[2] == 'pop'
                and is_handle_vector(collection_types.get(subject[1][1]))):
            fail(line, 'pop de A<Int> exige un transfert <- explicite')
        if (nodes[0].consuming and subject[0] == 'name' and subject[1] in join_results
                and join_results[subject[1]] is not None
                and join_results[subject[1]][1] in ('exchange_allocation', 'rejected_allocation')):
            # Resolve the generic Result syntax from the typed carrier. Keep
            # each arm's distinct owned provenance in the existing extractor.
            tag = nodes[1].args[1]
            branch = nodes[2].args[0] if valued else ('if_expr', *nodes[2].args)
            _, condition, yes, no = branch
            hidden = nodes[0].args[0]
            pattern = tag[3]
            status = condition[3][1]
            def exchange_body(body, arm):
                converted = []
                for statement in body:
                    if (statement.op == 'var' and statement.args[1][0] in ('utf8_value', 'utf8_error')
                            and statement.args[1][1] == ('name', hidden)):
                        payload = ('array_buffered_exchange_take', subject, ('int', arm))
                        statement = replace(statement, args=(statement.args[0], payload))
                    if (statement.op == 'array_statement' and statement.args[0][0] == 'array_buffered_exchange_take'
                            and statement.args[0][1] == ('name', hidden)):
                        statement = replace(statement, args=((statement.args[0][0], subject, *statement.args[0][2:]),))
                    converted.append(statement)
                return converted
            checked = ('compare', '==', ('array_buffered_exchange_status', subject, pattern), ('int', status))
            test = condition_value(checked, line)
            return emit_branches(test, exchange_body(yes, status), exchange_body(no, 5 if status == 0 else 0),
                                 line, valued=valued, construct='match', following=following,
                                 transfer_result=transfer_result, boolean=boolean, reference_result=reference_result)
        if wrapped_utf8_family(subject) is not None:
            return match_wrapped_utf8(nodes, line, valued=valued, transfer_result=transfer_result,
                                      following=following, boolean=boolean, reference_result=reference_result)
        scalar_result = None
        owned_result = None
        prepared_execution = None
        if subject[0] in ('scope', 'if_expr', 'loop_expr', 'value_match'):
            scalar_result = infer_scalar_value(subject, line, following=following)
        elif computed_await(subject):
            kind, prepared = emit_computed_transfer(subject[1], line)
            if kind == 'task':
                mode, typ = functions[prepared[3]].args[2]
                if mode in JOIN_PAYLOADS:
                    owned_result = owned_join_value(subject, line, prepared=(kind, prepared))
                else:
                    scalar_type = SCALAR_RESULTS.get((mode, typ))
                    if scalar_type is None:
                        fail(line, 'match async : résultat scalaire requis')
                    scalar_result = (await_task(subject, line, returns_value=True, prepared=prepared,
                                                scalar_type=scalar_type), scalar_type)
            elif kind == 'execution':
                prepared_execution = prepared
            else:
                fail(line, 'match async : tâche ou handle requis')
        elif subject[0] == 'await' and plain_join_mode(subject) is not None:
            scalar_result = infer_scalar_value(subject, line, following=following)
        elif await_result_mode(subject) in JOIN_PAYLOADS:
            owned_result = owned_join_value(subject, line, following=following)
        direct = awaits_execution(subject) or prepared_execution is not None
        if owned_result is not None:
            result, payload, loans = owned_result
            direct = True
        elif scalar_result is not None:
            value, typ = scalar_result
            mode = SCALAR_MODES.get(typ)
            if mode in UTF8_VALUE_RESULT_FAMILIES:
                return match_wrapped_utf8(nodes, line, valued=valued, transfer_result=transfer_result,
                                          following=following, boolean=boolean,
                                          prepared=(UTF8_VALUE_RESULT_FAMILIES[mode], value), reference_result=reference_result)
            if mode not in PLAIN_JOIN_TYPES:
                fail(line, 'match async : résultat faillible requis')
            result, payload, loans = value, PLAIN_JOIN_FIELDS[mode], None
        elif direct:
            result, payload, loans = execution_await(subject, line, prepared=prepared_execution)
        elif sync_signature(subject) in output_join_types:
            mode, _ = sync_signature(subject)
            if mode in ('handle_option', 'buffered_handle_exchange'):
                fail(line, 'résultat propriétaire : recevoir puis consommer avec match (-> résultat)')
            result, _ = sync_call(subject, line, following=following, owned=True)
            payload, loans, direct = JOIN_PAYLOADS[mode], None, True
        elif subject[0] == 'name' and subject[1] in join_results:
            name = subject[1]
            check_access(name, line)
            record = join_results[name]
            if record is None:
                fail(line, 'résultat de handle déjà consommé')
            if is_owned_join(name, nested=True):
                require_local_async_value(name, line)
                record = consume_owned_join(name, line)
            elif record[1] == 'async_execution':
                require_local_async_value(name, line)
                record = consume_owned_join(name, line)
                direct = True
            result, payload, loans = record
            if isinstance(payload, str) and payload in SHARED_VECTOR_SLICE_MODES:
                join_results[name] = None
                direct = True
        else:
            fail(line, 'match async : résultat de handle requis')
        tag = nodes[1].args[1]
        patterns = (('int', 0), ('int', 2)) if payload in ('allocation', 'nested', *OWNED_NESTED_PAYLOAD_MODES, 'optional_nested', *EXCHANGE_PAYLOAD_MODES, *OPTION_PAYLOAD_MODES) else (('int', 2 if payload else 1),)
        if nodes[0].consuming:
            patterns += (('int', -1),)
        if tag[0] != 'utf8_tag' or tag[2] not in (('int', 3), ('int', 7), ('int', 14)) or tag[3] not in patterns:
            fail(line, 'match de handle : attend Ok et Err avec le type de résultat déclaré')
        if valued:
            branch = nodes[2].args[0]
            if branch[0] != 'if_expr':
                fail(line, 'match de handle : attend deux bras')
            _, condition, yes, no = branch
        else:
            condition, yes, no = nodes[2].args
        if condition[0] != 'compare' or condition[1] != '==' or condition[3][0] != 'int':
            fail(line, 'match de handle : attend Ok et Err')
        status = condition[3][1]
        if status not in (0, 5):
            fail(line, 'match de handle : attend Ok et Err')
        test = f'{result}.status == {status}'
        return emit_branches(test, yes, no, line, valued=valued,
                             join_payload=(result, payload, status, loans, direct, subject[1] if not direct and subject[0] == 'name' else None), construct='match',
                             transfer_result=transfer_result, following=following, boolean=boolean,
                             reference_result=reference_result)

    def vector_result_operation(expr):
        if expr[0] == 'array_replace':
            receiver, method, arguments = expr[1], 'replace', list(expr[2:])
        elif expr[0] == 'method_call':
            receiver, method, arguments = expr[1:]
        else:
            return None
        if receiver[0] != 'name' or collection_types.get(receiver[1]) not in ('Vector<Int>', 'Vector<u8>'):
            return None
        element = 'int' if collection_types[receiver[1]] == 'Vector<Int>' else 'byte'
        mode = {'pop': element + '_option', 'replace': element + '_replace',
                'try_push': element + '_try_push', 'try_extend': 'capacity_result',
                'read_fd': 'read_result'}.get(method)
        return (mode, receiver[1], method, arguments) if mode else None

    def vector_result_value(operation, subject, line, *, following=None):
        mode, receiver, method, arguments = operation
        arity = {'pop': 0, 'replace': 2, 'try_push': 1, 'try_extend': 1, 'read_fd': 1}[method]
        if len(arguments) != arity:
            fail(line, f'{method} exige {arity} argument(s)')
        collection = collection_types[receiver]
        if method in ('try_extend', 'read_fd') and collection != 'Vector<u8>':
            fail(line, f'{method} exige un Vector<u8>')
        if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable):
            fail(line, f'{method} exige un Vector mutable')
        if following is not None:
            release_statement_loans(following, earlier=(subject,))
        check_access(receiver, line, write=True)
        preparation = [(receiver, 'mut')]
        active_loans[id(preparation)] = preparation
        prepared = []
        try:
            for index, argument in enumerate(arguments):
                if method == 'try_extend':
                    ctype = 'VectorSlice'
                    value = byte_slice_argument(argument, line, context=method)
                elif method == 'read_fd' or method == 'replace' and index == 0 or collection == 'Vector<Int>':
                    ctype = 'int'
                    value = expression(argument, line)
                else:
                    ctype = 'uint8_t'
                    value = byte_value(argument, line, context=method)
                snapshot = temporary(ctype)
                steps.append(f'{snapshot} = {value};')
                prepared.append(snapshot)
        finally:
            del active_loans[id(preparation)]
        if following is not None:
            release_statement_loans(following)
        check_access(receiver, line, write=True)
        result = temporary(VECTOR_VALUE_RESULT_CTYPES[mode])
        cell = f'frame->{fields[receiver]}'
        steps.append(f'{result} = ({VECTOR_VALUE_RESULT_CTYPES[mode]}){{0}};')
        if method == 'pop':
            steps.append(f'{result}.status = vector_pop({cell}, &{result}.value);')
        elif method == 'replace':
            steps.append(f'{result}.value = {prepared[1]};')
            steps.append(f'{result}.status = vector_replace({cell}, {prepared[0]}, &{result}.value);')
        elif method == 'try_push':
            steps.append(f'{result}.value = {prepared[0]};')
            steps.append(f'{result}.status = vector_try_push({cell}, &{result}.value);')
        elif method == 'try_extend':
            steps.append(f'{result} = vector_try_extend_slice({cell}, {prepared[0]});')
        else:
            steps.append(f'{result} = vector_read_int({cell}, {prepared[0]});')
        return result

    def wrapped_utf8_family(expr):
        signature = sync_signature(expr)
        if signature and signature in view_sync_types and signature[0] in UTF8_VALUE_RESULT_FAMILIES:
            return UTF8_VALUE_RESULT_FAMILIES[signature[0]]
        if operation := vector_result_operation(expr):
            return VECTOR_VALUE_RESULT_FAMILIES[operation[0]]
        if expr[0] == 'utf8_try_slice':
            return 12
        if expr[0] == 'array_integer_try_from':
            return 11
        if expr[0] == 'array_numeric_try_from':
            return CONVERSION_FAMILIES[conversion_mode(expr[1])]
        if expr[0] == 'name':
            return wrapped_utf8_bindings.get(expr[1])
        if expr[0] == 'await':
            signature = await_signature(expr)
            return UTF8_VALUE_RESULT_FAMILIES.get(signature[0]) if signature else None
        if expr[0] == 'utf8_from_str':
            return 2
        if expr[0] == 'utf8_string_replace_byte' or (expr[0] == 'method_call' and expr[2] == 'replace_byte'
                and expr[1][0] == 'name' and collection_types.get(expr[1][1]) == 'String'):
            return 6
        if expr[0] == 'utf8_string_replace_bytes' or (expr[0] == 'method_call' and expr[2] == 'replace_bytes'
                and expr[1][0] == 'name' and collection_types.get(expr[1][1]) == 'String'):
            return 10
        if expr[0] == 'utf8_string_pop' or (expr[0] == 'method_call' and expr[2] == 'pop'
                and expr[1][0] == 'name' and collection_types.get(expr[1][1]) == 'String'):
            return 4
        if expr[0] == 'utf8_char_at' or (expr[0] == 'method_call' and expr[2] == 'char_at'):
            return 1
        return None

    def byte_slice_argument(expr, line, *, context="replace_bytes"):
        projection = None
        if expr[0] == 'ref' and parameter_modes.get(expr[1]) not in ARRAY_BORROWS:
            projection = ('name', expr[1])
        elif expr[0] in ('ref_expr', 'array_ref'):
            projection = expr[1]
        elif (expr[0] == 'name' and parameter_modes.get(expr[1]) == 'array_ref'
              or expr[0] == 'reborrow' and expr[2] == 'ref'
              and parameter_modes.get(expr[1]) in ARRAY_BORROWS):
            projection = ('name', expr[1])
        if projection is not None:
            if projection[0] in ('array_literal', 'array_repeat'):
                shape, plan, element = layout_array(projection, (), line)
                if len(shape) != 1 or element != 'uint8_t':
                    fail(line, f'{context} exige un emprunt de tableau u8 ou de tranche u8')
                pointer = temporary(element, array_dimensions(shape))
                initialize_array(pointer, plan)
            else:
                copy_source = projection[1] if projection[0] == 'array_copy' else None
                name, indices = reference_array_path(copy_source or projection)
                shape = arrays.get(name, ())[len(indices):]
                if len(shape) != 1 or array_elements.get(name) != 'uint8_t':
                    fail(line, f'{context} exige un emprunt de tableau u8 ou de tranche u8')
                if copy_source is not None:
                    source, _ = array_element(copy_source, line, remaining=shape)
                    pointer = temporary('uint8_t', array_dimensions(shape))
                    if all(shape):
                        steps.append(f'memcpy({pointer}, {source}, sizeof {pointer});')
                else:
                    pointer, _ = capture_array_place(projection, 'ref', line, remaining=shape,
                                                     expected_element='uint8_t')
            return f'(VectorSlice){{(const unsigned char *)({pointer}), {shape[0]}, 0}}'
        return vector_view_value(expr, line, 'vector_bytes')

    def vector_view_mode(expr):
        signature = sync_signature(expr)
        if signature and signature[0] in VECTOR_SLICE_ELEMENTS:
            return signature[0]
        op = expr[0]
        if (op == 'name' and expr[1] not in mutable_slices) or (op == 'reborrow' and expr[2] == 'ref'):
            return slice_bindings.get(expr[1])
        if op == 'utf8_slice':
            receiver = expr[1]
            if receiver[0] == 'name':
                if receiver[1] in mutable_slices:
                    return slice_bindings[receiver[1]]
                if mode := VECTOR_SLICE_MODES.get(collection_types.get(receiver[1])):
                    return mode
            return vector_view_mode(receiver)
        signature = await_signature(expr)
        return signature[0] if signature and signature[0] in VECTOR_SLICE_ELEMENTS else None

    def mutable_slice_mode(expr):
        signature = sync_signature(expr)
        if signature and signature[0] in SHARED_VECTOR_SLICE_MODES:
            return signature[0]
        if expr[0] == 'reborrow' and expr[2] == 'mut' and expr[1] in mutable_slices:
            return next(mode for mode, shared in SHARED_VECTOR_SLICE_MODES.items() if shared == slice_bindings[expr[1]])
        signature = await_signature(expr)
        return signature[0] if signature and signature[0] in SHARED_VECTOR_SLICE_MODES else None

    def mutable_slice_value(expr, line, mode, *, following=None):
        if sync_signature(expr) == (mode, VALUE_MODES[mode]):
            return sync_call(expr, line, (mode, VALUE_MODES[mode]), following=following)[0]
        if expr[0] == 'name' and expr[1] in mutable_slices:
            expr = 'reborrow', expr[1], 'mut'
        if mutable_slice_mode(expr) == mode:
            if expr[0] == 'await':
                return await_task(expr, line, returns_value=True, scalar_type=SCALAR_TYPES[mode])
            check_access(expr[1], line, write=True)
            return value_place(expr[1])
        if expr[0] in ('scope', 'if_expr', 'value_match', 'loop_expr') or computed_await(expr):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ == SCALAR_TYPES[mode]:
                return value
        fail(line, f'une tranche mutable {SCALAR_TYPES[mode]} est requise')

    def vector_view_value(expr, line, mode, *, following=None):
        if sync_signature(expr) == (mode, VALUE_MODES[mode]):
            return sync_call(expr, line, (mode, VALUE_MODES[mode]), following=following)[0]
        diagnostic = f'une tranche {VALUE_MODES[mode][1:-1]} ({SCALAR_TYPES[mode]}) est requise'
        op = expr[0]
        if op in ('scope', 'if_expr', 'value_match', 'loop_expr') or computed_await(expr):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ == SCALAR_TYPES[mode]:
                return value
            fail(line, diagnostic)
        if vector_view_mode(expr) != mode:
            fail(line, diagnostic)
        if op in ('name', 'reborrow'):
            check_access(expr[1], line)
            return value_place(expr[1])
        if op == 'await':
            return await_task(expr, line, returns_value=True, scalar_type=SCALAR_TYPES[mode])

        receiver, *bounds = expr[1:]
        if receiver[0] == 'name' and receiver[1] in mutable_slices:
            receiver = 'reborrow', receiver[1], 'ref'
        known = [bound[1] if bound[0] == 'int' else None for bound in bounds]
        if any(value is not None and value < 0 for value in known) or (
                len(known) == 2 and all(value is not None for value in known) and known[0] > known[1]):
            fail(line, 'bornes de tranche de Vector invalides')
        collection = receiver[0] == 'name' and collection_types.get(receiver[1]) in VECTOR_SLICE_MODES
        if collection:
            check_access(receiver[1], line)
            base = f'frame->{fields[receiver[1]]}'
            loans = [(receiver[1], 'ref')]
            origins = tuple(loans)
        else:
            view = vector_view_value(receiver, line, mode)
            base = temporary('VectorSlice')
            steps.append(f'{base} = {view};')
            origins = local_utf8_loans(receiver, view)
            loans = list(origins)
        active_loans[id(loans)] = loans
        prepared = []
        try:
            for bound in bounds:
                value = expression(bound, line)
                saved = temporary('int')
                steps.append(f'{saved} = {value};')
                prepared.append(saved)
        finally:
            del active_loans[id(loans)]
        end = prepared[1] if len(prepared) == 2 else '0'
        arguments = f'{base}, {prepared[0]}, {end}, {int(len(prepared) == 2)}'
        view = temporary('VectorSlice')
        if collection:
            steps.append(f'{view} = vector_slice({arguments});')
        else:
            steps.append(f'{view} = vector_subslice({arguments}, sizeof({VECTOR_SLICE_ELEMENTS[mode]}));')
        utf8_result_loans[view] = origins
        return view

    def indexed_vector_view_mode(expr):
        if expr[0] != 'array_index':
            return None
        receiver = expr[1]
        if receiver[0] == 'name' and receiver[1] in mutable_slices:
            return slice_bindings[receiver[1]]
        return vector_view_mode(receiver)

    def vector_view_address(expr, line, mode, *, write=False):
        _, receiver, index = expr
        if receiver[0] == 'name' and receiver[1] in mutable_slices:
            check_access(receiver[1], line, write=write)
            receiver = 'reborrow', receiver[1], 'ref'
        value = vector_view_value(receiver, line, mode)
        snapshot = temporary('VectorSlice')
        steps.append(f'{snapshot} = {value};')
        loans = list(local_utf8_loans(receiver, value))
        active_loans[id(loans)] = loans
        try:
            offset = expression(index, line)
        finally:
            del active_loans[id(loans)]
        element = VECTOR_SLICE_ELEMENTS[mode]
        ctype = f'{element} *' if write else f'const {element} *'
        pointer = temporary(ctype)
        steps.append(f'{pointer} = ({ctype})vector_slice_address({snapshot}, {offset}, sizeof({element}));')
        utf8_result_loans[pointer] = tuple(loans)
        return pointer

    def bind_vector_split(statement, body, position):
        name, initializer = statement.args
        line = statement.line
        if initializer[0] == 'array_split':
            _, receiver, index = initializer
            parent = receiver[1]
            nested = parent in mutable_slices
            mode = slice_bindings[parent] if nested else VECTOR_SLICE_MODES.get(collection_types.get(parent))
            if not name.startswith('\0vector-split-') or mode is None or not (
                    nested or references.get(parent) == 'mut' or
                    references.get(parent) == 'owned' and parent in mutable):
                fail(line, 'split_at_mut exige un Vector mutable et deux receveurs')
            check_access(parent, line, write=True)
            loans = [(parent, 'mut'), *utf8_view_loans.get(parent, ())]
            active_loans[id(loans)] = loans
            try:
                offset = expression(index, line)
            finally:
                del active_loans[id(loans)]
            base = f'frame->{fields[parent]}'
            operation = (f'vector_subsplit({base}, {offset}, sizeof({VECTOR_SLICE_ELEMENTS[mode]}))' if nested
                         else f'vector_split_at_mut({base}, {offset})')
            pair = temporary('VectorSplit')
            steps.append(f'{pair} = {operation};')
            pending_splits[name] = pair, mode, loans
            return
        _, (_, pair_name), (_, side) = initializer
        if pair_name not in pending_splits:
            fail(line, 'cette liaison exige une séparation locale de tranche')
        pair, mode, origins = pending_splits[pair_name]
        member = declare(name, line)
        slice_bindings[name] = mode
        mutable_slices.add(name)
        loans = list(origins)
        utf8_view_loans[name] = tuple(loans)
        active_loans[id(loans)] = loans
        track_result(name, loans, body, position)
        steps.append(f'frame->{member} = {pair}.{"right" if side else "left"};')
        if side:
            del pending_splits[pair_name]

    def wrapped_utf8_value(subject, line, *, following=None):
        signature = sync_signature(subject)
        if signature and signature in view_sync_types:
            return sync_call(subject, line, signature, following=following)[0]
        if operation := vector_result_operation(subject):
            return vector_result_value(operation, subject, line, following=following)
        if subject[0] == 'utf8_try_slice':
            value = prepare_text_slice(subject, line, fallible=True)
            saved = temporary('CrustTextResult')
            steps.append(f'{saved} = {value};')
            utf8_result_loans[saved] = local_utf8_loans(subject, value)
            return saved
        if subject[0] == 'array_integer_try_from':
            value, typ = infer_scalar_value(subject[1], line, following=following)
            if typ not in ('Int', 'u8'):
                fail(line, 'u8::try_from exige un Int ou un u8')
            snapshot = temporary('CrustByteResult')
            steps.append(f'{snapshot} = integer_try_u8({value});')
            return snapshot
        if subject[0] == 'array_numeric_try_from':
            target = subject[1]
            value, typ = infer_scalar_value(subject[2], line, following=following)
            source = numeric_type(typ)
            if source is None:
                fail(line, 'try_from exige une valeur numérique')
            snapshot = temporary(FORMATS[source].c_type)
            result = temporary(CONVERSION_C_TYPES[conversion_mode(target)])
            steps.append(f'{snapshot} = {value};')
            steps.extend(c_conversion(source, target, snapshot, result, declare=False))
            return result
        if subject[0] == 'name':
            check_access(subject[1], line)
            return value_place(subject[1])
        if subject[0] == 'await':
            typ = WRAPPED_UTF8_TYPES[wrapped_utf8_family(subject)]
            return await_task(subject, line, returns_value=True, scalar_type=typ)
        receiver = subject[1]
        if wrapped_utf8_family(subject) in (6, 10):
            method = 'replace_byte' if wrapped_utf8_family(subject) == 6 else 'replace_bytes'
            arguments = subject[3] if subject[0] == 'method_call' else subject[2:]
            if receiver[0] != 'name' or collection_types.get(receiver[1]) != 'String' or len(arguments) != 2:
                fail(line, f'{method} exige un String, un indice Int et une source du type déclaré')
            name = receiver[1]
            if not (references.get(name) == 'mut' or references.get(name) == 'owned' and name in mutable):
                fail(line, f'{method} exige un String mutable')
            if following is not None:
                release_statement_loans(following, earlier=(subject,))
            check_access(name, line, write=True)
            preparation = [(name, 'mut')]
            active_loans[id(preparation)] = preparation
            try:
                offset = expression(arguments[0], line)
                saved_offset = temporary('int')
                steps.append(f'{saved_offset} = {offset};')
                replacement = (byte_value(arguments[1], line, context=method) if method == 'replace_byte'
                               else byte_slice_argument(arguments[1], line))
                saved = temporary('uint8_t' if method == 'replace_byte' else 'VectorSlice')
                steps.append(f'{saved} = {replacement};')
            finally:
                del active_loans[id(preparation)]
            if following is not None:
                release_statement_loans(following)
            check_access(name, line, write=True)
            snapshot = temporary('CrustByteResult')
            implementation = 'string_replace_byte' if method == 'replace_byte' else 'string_replace_slice'
            steps.append(f'{snapshot} = {implementation}(frame->{fields[name]}, {saved_offset}, {saved});')
            return snapshot
        if wrapped_utf8_family(subject) == 4:
            arguments = subject[3] if subject[0] == 'method_call' else subject[2:]
            if receiver[0] != 'name' or collection_types.get(receiver[1]) != 'String' or arguments:
                fail(line, 'pop exige un String et aucun argument')
            name = receiver[1]
            if not (references.get(name) == 'mut' or references.get(name) == 'owned' and name in mutable):
                fail(line, 'pop exige un String mutable')
            if following is not None:
                release_statement_loans(following)
            check_access(name, line, write=True)
            snapshot = temporary('CrustCharResult')
            steps.append(f'{snapshot} = string_pop(frame->{fields[name]});')
            return snapshot
        if subject[0] == 'utf8_from_str':
            return f'char_from_text({static_text_value(receiver, line, following=following)})'
        arguments = subject[3] if subject[0] == 'method_call' else subject[2:]
        if len(arguments) != 1:
            fail(line, 'char_at exige un indice Int')
        snapshot, index = indexed_text_view(receiver, arguments[0], line, following=following)
        return f'text_char_at({snapshot}, {index})'

    def match_vector_result(nodes, line, *, valued, transfer_result, following, boolean, prepared=None, reference_result=False):
        (subject_name, subject), (tag_name, tag) = (node.args for node in nodes[:2])
        family = prepared[0] if prepared is not None else wrapped_utf8_family(subject)
        mode = WRAPPED_UTF8_MODES[family]
        option = mode in ('int_option', 'byte_option')
        unit = mode in ('int_try_push', 'byte_try_push', 'capacity_result')
        syntax_family = 8 if mode == 'capacity_result' else 9 if mode == 'read_result' else 7
        allowed = (0, 4) if option else (0, 3, 5, 7, syntax_family)
        bad_payload = tag[3] == ('int', 2) if unit else tag[3] == ('int', 1)
        if tag[2] not in tuple(('int', value) for value in allowed) or bad_payload:
            fail(line, 'match de résultat Vector : type ou motif incompatible')
        value = prepared[1] if prepared is not None else wrapped_utf8_value(subject, line, following=following)
        result = temporary(VECTOR_VALUE_RESULT_CTYPES[mode])
        steps.append(f'{result} = {value};')
        vector_match_payloads[subject_name] = mode, result
        utf8_match_tags[tag_name] = (f'({result}.status == 0 ? 0 : 5)' if tag[2] == ('int', 3) or tag[2] == ('int', 7) and mode in RESULT_ERROR_MODES
                                     else f'{result}.status')
        try:
            branch = nodes[2].args[0] if valued else nodes[2].args
            if (valued and branch[0] == 'scope') or (not valued and nodes[2].op == 'scope'):
                body = branch[2] if valued else branch[1]
                test, yes, no = None, body, None
            else:
                condition, yes, no = branch[1:] if valued else branch
                test = condition_value(condition, line)
            return emit_branches(test, yes, no, line, valued=valued, construct='match',
                                 transfer_result=transfer_result, following=following, boolean=boolean, reference_result=reference_result)
        finally:
            del vector_match_payloads[subject_name]
            del utf8_match_tags[tag_name]

    def match_wrapped_utf8(nodes, line, *, valued, transfer_result, following, boolean, prepared=None, reference_result=False):
        (subject_name, subject), (tag_name, tag) = (node.args for node in nodes[:2])
        family = prepared[0] if prepared is not None else wrapped_utf8_family(subject)
        if WRAPPED_UTF8_MODES[family] in VECTOR_VALUE_RESULT_FAMILIES:
            return match_vector_result(nodes, line, valued=valued, transfer_result=transfer_result,
                                       following=following, boolean=boolean, prepared=prepared, reference_result=reference_result)
        allowed = (0, 4) if family == 4 else (0, 3, 5, 7, 6 if family == 10 else family)
        numeric_payload = CONVERSION_PAYLOADS.get(WRAPPED_UTF8_MODES[family])
        if numeric_payload:
            allowed += (16,)
        if family in (1, 12):
            allowed += (13,)  # Unqualified OutOfBounds / NotCharBoundary patterns.
        bad_payload = tag[3] == ('int', 2) if family == 10 else tag[3] == ('int', 1)
        if tag[2] not in tuple(('int', value) for value in allowed) or bad_payload:
            fail(line, 'match UTF-8 : type du résultat ou de l’erreur incompatible')
        value = prepared[1] if prepared is not None else wrapped_utf8_value(subject, line, following=following)
        result = temporary(UTF8_VALUE_RESULT_CTYPES[WRAPPED_UTF8_MODES[family]])
        steps.append(f'{result} = {value};')
        utf8_match_payloads[subject_name] = (numeric_payload or
            ('text' if family == 12 else 'unit' if family == 10 else 'u8' if family in (6, 11) else 'char'))
        utf8_match_results[subject_name] = result
        wrapped_utf8_family_by_result[subject_name] = family
        if family == 12:
            utf8_result_loans[result] = local_utf8_loans(subject, value)
        utf8_match_tags[tag_name] = (f'({result}.status == 0 ? 0 : 5)' if tag[2] == ('int', 3) or tag[2] == ('int', 7) and WRAPPED_UTF8_MODES[family] in RESULT_ERROR_MODES
                                     else f'{result}.status')
        try:
            branch = nodes[2].args[0] if valued else nodes[2].args
            if (valued and branch[0] == 'scope') or (not valued and nodes[2].op == 'scope'):
                body = branch[2] if valued else branch[1]
                test, yes, no = None, body, None
            else:
                condition, yes, no = branch[1:] if valued else branch
                test = condition_value(condition, line)
            return emit_branches(test, yes, no, line, valued=valued, construct='match',
                                 transfer_result=transfer_result, following=following, boolean=boolean, reference_result=reference_result)
        finally:
            del utf8_match_results[subject_name]
            del wrapped_utf8_family_by_result[subject_name]
            del utf8_match_payloads[subject_name]
            del utf8_match_tags[tag_name]

    def is_boolean(expr):
        return (sync_signature(expr) == ('bool', 'bool')
                or expr[0] == 'bool' or expr[0] == 'name' and expr[1] in boolean_bindings
                or expr[0] == 'await' and await_signature(expr) == ('scalar', 'Bool'))

    def boolean_value(expr, line, *, following=None):
        if expr[0] == 'array_hashmap_target':
            value, typ = hashmap_target(expr, line)
            if typ != 'Bool':
                fail(line, 'une valeur bool est requise')
            return value
        if expr[0] == 'array_numeric_not':
            return f'!({boolean_value(expr[1], line, following=following)})'
        if expr[0] == 'match_expr':
            return match_enum(expr[1], valued=True, following=following, boolean=True)
        if sync_signature(expr) is not None:
            return sync_call(expr, line, ('bool', 'bool'), following=following)[0]
        if expr[0] == 'bool':
            return str(int(expr[1]))
        if expr[0] == 'field':
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != 'Bool':
                fail(line, 'une valeur bool est requise')
            return value
        if expr[0] == 'deref' and mutex_payload(collection_types.get(expr[1]), GUARD_TYPES) == 'bool':
            return infer_scalar_value(expr, line, following=following)[0]
        if expr[0] == 'name' and expr[1] in boolean_bindings:
            check_access(expr[1], line)
            return value_place(expr[1])
        if expr[0] == 'await' and (is_boolean(expr) or computed_await(expr)):
            return await_task(expr, line, returns_value=True, scalar_type='Bool')
        if expr[0] == 'if_expr':
            _, condition, yes, no = expr
            return conditional(condition, yes, no, line, valued=True, following=following, boolean=True)
        if expr[0] == 'value_match':
            return match_async_result(expr[1], line, following=following, boolean=True)
        if expr[0] == 'loop_expr':
            kind, value = emit_loop(expr[1].args[0], line, valued=True, following=following)
            if kind == 'bool':
                return value
        fail(line, 'une valeur Bool est requise')

    def collection_index_type(expr):
        if expr[0] == 'array_index' and expr[1][0] == 'name':
            return collection_types.get(expr[1][1])
        return None

    def vector_remove_type(expr):
        if expr[0] == 'method_call' and expr[2] == 'remove' and expr[1][0] == 'name':
            return {'Vector<Int>': 'Int', 'Vector<u8>': 'u8'}.get(collection_types.get(expr[1][1]))
        return None

    def handle_remove_receiver(expr):
        if (expr[0] == 'method_call' and expr[2] == 'remove' and expr[1][0] == 'name'
                and is_handle_vector(collection_types.get(expr[1][1]))):
            return expr[1][1]
        return None

    def handle_vector_mutation(receiver, line, *, following=None):
        if not (is_handle_vector(collection_types.get(receiver)) or collection_types.get(receiver) in INLINE_VECTOR_ELEMENTS):
            fail(line, 'pop transféré exige un Vector<A<Int>>')
        if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable):
            fail(line, 'pop exige un Vector mutable')
        if following is not None:
            release_statement_loans(following)
        check_access(receiver, line, write=True)

    def handle_pop_value(expr, line, *, following=None):
        receiver = expr[1][1]
        handle_vector_mutation(receiver, line, following=following)
        buffered = expr[0] == 'array_handle_option_pop'
        if collection_types[receiver] in INLINE_VECTOR_ELEMENTS:
            element, layout = inline_vector_layout(collection_types[receiver], line)
            destination = local_destinations.get(id(expr)) or implicit_stack()
            metadata = local_layouts.setdefault(element, f'{prefix}_local_layout_{len(local_layouts)}')
            result = temporary('VectorHandleResult')
            steps.append(f'{result} = vector_pop_local(frame->{fields[receiver]}, &{local_pools[destination]}, &{metadata}, {structure_offset(layout, len(layout))}, "async pop", NULL);')
            keep_storage(result, (destination,))
            owned_result_types[result] = element
            slots = inline_vector_items.get(receiver)
            if slots:
                for category, path, held in slots[-1]:
                    active_loans[(category, result, path)] = list(held)
                    if category == 'owned_storage':
                        keep_storage(result, (origin for origin, _ in held))
                set_vector_positions(receiver, slots[:-1])
            elif slots is None:
                extract_vector_payload(receiver, result)
            if buffered:
                return result
            value = temporary('Cell *')
            steps.extend((f'if ({result}.status != CRUST_CHAR_OK) fail("pop de valeur vide");',
                          f'{value} = {result}.value;'))
            move_stored_fields(result, value)
            keep_storage(value, storage_of(result))
            owned_result_types[value] = element
            return value
        result = temporary('VectorHandleResult' if buffered else 'Cell *')
        if buffered:
            steps.extend((f'{result} = (VectorHandleResult){{0}};',
                          f'{result}.status = vector_pop(frame->{fields[receiver]}, &{result}.value);'))
        else:
            steps.append(f'if (vector_pop(frame->{fields[receiver]}, &{result}) != CRUST_CHAR_OK) fail("pop de handle vide");')
        keep_storage(result, storage_bindings.get(receiver, ()))
        owned_result_types[result] = handle_vector_element(collection_types[receiver])
        extract_vector_payload(receiver, result)
        return result

    def handle_exchange_record(name, line):
        if name not in join_results or join_results[name] is not None and join_results[name][1] not in ('exchange_allocation', 'rejected_allocation'):
            fail(line, 'match consommant : résultat de replace ou try_push requis')
        if join_results[name] is None:
            fail(line, f"résultat '{name}' déjà consommé")
        return join_results[name]

    def handle_replace_value(expr, line, *, following=None):
        appending = expr[0] in ('array_handle_try_push', 'array_buffered_try_push')
        method = 'try_push' if appending else 'replace'
        receiver = expr[1][1]
        if following is not None:
            release_statement_loans(following, earlier=(expr,))
        handle_vector_mutation(receiver, line)
        preparation = [(receiver, 'mut')]
        active_loans[id(preparation)] = preparation
        try:
            if not appending:
                index_value = expression(expr[2], line)
                index = temporary('int')
                steps.append(f'{index} = {index_value};')
            argument = expr[-1]
            if argument[0] == 'down':
                require_local_async_value(argument[1], line)
                kind, incoming = export_async_value(argument[1], (), line)
            elif argument[0] == 'transfer':
                incoming = sync_owned_value(argument[1], line, following=following)
                kind = 'owned'
            else:
                fail(line, f'{method} de A<Int> exige un transfert explicite ->')
            element = handle_vector_element(collection_types[receiver])
            if kind != 'owned' or owned_result_types.get(incoming, 'Int') != element:
                fail(line, f'{method} de {collection_types[receiver]} exige une allocation {element}')
            if storage_of(incoming) & implicit_stacks:
                fail(line, 'une case A<Int> exige une allocation de pool')
            depth = next((index for index in reversed(range(len(scopes))) if receiver in scopes[index][0]), 0)
            require_durable_storage(incoming, depth + 1 if references.get(receiver) == 'owned' else 0, line)
            if references.get(receiver) != 'owned' and (node.field_effect_summary is None or not node.field_effect_summary.complete):
                fail(line, f'{method} dans un vecteur injecté : contrat de terminaison incomplet')
        finally:
            del active_loans[id(preparation)]
        if following is not None:
            release_statement_loans(following)
        check_access(receiver, line, write=True)
        result = temporary('VectorHandleResult')
        if not appending:
            for field, held in owned_capture_field_loans(receiver, collection_types[receiver]).items():
                path = stored_field_path(field)
                if path and path[0] == '[]':
                    active_loans[('stored_field', result, ('ok', *path[1:]))] = list(held)
        for field, held in owned_capture_field_loans(incoming, element).items():
            active_loans[('stored_field', result, ('err', *stored_field_path(field)))] = list(held)
        retain_vector_payload(receiver, incoming)
        previous = frozenset() if appending else storage_bindings.get(receiver, frozenset())
        added = storage_of(incoming)
        keep_storage(result, previous | added)
        active_loans[('owned_storage', result, ('ok',))] = [(origin, 'storage') for origin in previous]
        active_loans[('owned_storage', result, ('err',))] = [(origin, 'storage') for origin in added]
        key = ('owned_storage', receiver, ('items',))
        held = [*active_loans.get(key, ()), *((origin, 'storage') for origin in added)]
        install_field_change(key, list(dict.fromkeys(held)))
        arguments = f'&{result}.value' if appending else f'{index}, &{result}.value'
        steps.extend((f'{result} = (VectorHandleResult){{0, {incoming}}};',
                      f'{incoming} = NULL;',
                      f'{result}.status = vector_{method}(frame->{fields[receiver]}, {arguments});'))
        if appending:
            steps.append(f'if ({result}.status == 0) {result}.value = NULL;')
        clear_stored_fields(incoming)
        owned_result_types[result] = handle_vector_element(collection_types[receiver])
        return result

    def handle_option_record(name, line):
        if name not in join_results or join_results[name] is not None and join_results[name][1] != 'optional_allocation':
            fail(line, 'match consommant : Option<A<Int>> requis')
        if join_results[name] is None:
            fail(line, f"résultat '{name}' déjà consommé")
        return join_results[name]

    def vector_remove_value(expr, line, *, following=None):
        receiver, arguments = expr[1][1], expr[3]
        if len(arguments) != 1:
            fail(line, 'remove exige un indice Int')
        if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable):
            fail(line, 'remove exige un Vector mutable')
        if following is not None:
            release_statement_loans(following, earlier=(expr,))
        check_access(receiver, line, write=True)
        reservation = [(receiver, 'mut')]
        active_loans[id(reservation)] = reservation
        try:
            value = expression(arguments[0], line)
            index = temporary('int')
            steps.append(f'{index} = {value};')
        finally:
            del active_loans[id(reservation)]
        if following is not None:
            release_statement_loans(following)
        check_access(receiver, line, write=True)
        owned = handle_remove_receiver(expr) is not None
        result = temporary('Cell *' if owned else 'int' if vector_remove_type(expr) == 'Int' else 'uint8_t')
        steps.append(f'vector_remove(frame->{fields[receiver]}, {index}, &{result});')
        if owned:
            owned_result_types[result] = handle_vector_element(collection_types[receiver])
            keep_storage(result, storage_bindings.get(receiver, ()))
            extract_vector_payload(receiver, result)
        return result

    def owned_vector_element(expr, line, *, write=False):
        receiver = expr[1][1]
        if write and not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable):
            fail(line, 'écriture de Vector : une liaison mutable est requise')
        index = expression(expr[2], line)
        check_access(receiver, line, write=write)
        ctype = 'Cell *' if is_handle_vector(collection_types[receiver]) else {'Vector<Int>': 'int'}.get(collection_types[receiver], 'uint8_t')
        pointer = temporary(ctype + ' *')
        steps.append(f'{pointer} = ({ctype} *)vector_checked_item(frame->{fields[receiver]}, {index});')
        return f'*{pointer}'

    def handle_vector_target(expr, line, *, write=False):
        slot = owned_vector_element(expr, line, write=write)
        target = temporary('Cell *')
        steps.append(f'{target} = {slot};')
        return target

    def is_byte_array_element(expr):
        if expr[0] == 'array_replace':
            expr = ('array_index', expr[1], expr[2])
        if expr[0] != 'array_index':
            return False
        root, indices = reference_array_path(expr)
        return array_elements.get(root) == 'uint8_t' and len(indices) == len(arrays[root])

    def byte_value(expr, line, *, context='une opération u8', following=None):
        if expr[0] == 'array_hashmap_target':
            value, typ = hashmap_target(expr, line)
            if typ != 'u8':
                fail(line, f'{context} exige une valeur u8')
            return value
        if expr[0] == 'deref' and mutex_payload(collection_types.get(expr[1]), GUARD_TYPES) == 'u8':
            return infer_scalar_value(expr, line, following=following)[0]
        if expr[0] == 'deref' and collection_types.get(expr[1]) == 'u8':
            return infer_scalar_value(expr, line, following=following)[0]
        if expr[0].startswith('array_numeric_'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != 'u8':
                fail(line, f'{context} exige une valeur u8')
            return value
        if sync_signature(expr) is not None:
            return sync_call(expr, line, ('byte', 'u8'), following=following)[0]
        if vector_remove_type(expr) == 'u8':
            return vector_remove_value(expr, line, following=following)
        if expr[0] == 'array_byte_literal':
            return str(expr[1][1])
        if expr[0] == 'array_integer_cast':
            value, typ = integer_cast_value(expr, line, following=following)
            if typ != 'u8':
                fail(line, f'{context} exige une valeur u8')
            return value
        if indexed_vector_view_mode(expr) == 'vector_bytes':
            return f'*{vector_view_address(expr, line, "vector_bytes")}'
        if is_byte_array_element(expr):
            if expr[0] == 'array_replace':
                return store_array(('array_index', expr[1], expr[2]), expr[3], line,
                                   following=following, returns_old=True)
            return array_element(expr, line, expected_element='uint8_t')[0]
        if expr[0] == 'int':
            if not 0 <= expr[1] <= 255:
                fail(line, f'{context} : littéral hors intervalle u8')
            return str(expr[1])
        if (expr[0] == 'utf8_value' and expr[1][0] == 'name'
                and utf8_match_payloads.get(expr[1][1]) == 'u8'):
            subject = expr[1][1]
            result = utf8_match_results[subject]
            if wrapped_utf8_family_by_result.get(subject) in CONVERSION_FAMILIES.values():
                return f'{result}.value'
            return f'byte_result_value({result})'
        if collection_index_type(expr) == 'Vector<u8>':
            return owned_vector_element(expr, line)
        if is_text_index(expr) or collection_index_type(expr) == 'String':
            return f'*{static_text_byte_address(expr, line, following=following)}'
        if expr[0] == 'deref' and reference_types.get(expr[1]) == 'u8':
            check_access(expr[1], line)
            return value_place(expr[1])
        if expr[0] == 'deref' and expr[1] in byte_ref_bindings:
            check_access(expr[1], line)
            return f'*{value_place(expr[1])}'
        if expr[0] == 'await' and (await_signature(expr) == ('byte', 'u8') or computed_await(expr)):
            return await_task(expr, line, returns_value=True, scalar_type='u8')
        if expr[0] in ('if_expr', 'value_match', 'loop_expr'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ == 'u8':
                return value
            fail(line, f'{context} exige une valeur du même type')
        if expr[0] != 'name' or expr[1] not in byte_bindings:
            fail(line, f'{context} exige une valeur du même type')
        check_access(expr[1], line)
        return value_place(expr[1])

    def is_runtime_error(expr):
        return (expr[0] == 'utf8_runtime_error'
                or expr[0] == 'name' and expr[1] in runtime_error_bindings
                or expr[0] == 'await' and await_signature(expr) == ('runtime_error', 'runtime::Error'))

    def plain_join_mode(expr):
        if awaits_execution(expr):
            record = executions.get(expr[1][1])
            if record is not None:
                return PLAIN_RETURN_JOINS.get(functions[record[3]].args[2])
        signature = await_signature(expr)
        if signature is not None and signature[0] in PLAIN_JOIN_TYPES:
            return signature[0]
        if expr[0] != 'name':
            return None
        name = expr[1]
        if name in plain_join_bindings:
            return plain_join_bindings[name]
        record = join_results.get(name)
        if record is not None and record[2] is None:
            return next((mode for mode, field in PLAIN_JOIN_FIELDS.items() if record[1] == field), None)
        return None

    def plain_join_value(expr, mode, line, *, following=None):
        if awaits_execution(expr) and plain_join_mode(expr) == mode:
            return execution_await(expr, line)[0]
        if computed_await(expr):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != PLAIN_JOIN_TYPES[mode]:
                fail(line, f'résultat attendu : {PLAIN_JOIN_TYPES[mode]}')
            return value
        if expr[0] == 'await' and plain_join_mode(expr) == mode:
            return await_task(expr, line, returns_value=True, scalar_type=PLAIN_JOIN_TYPES[mode])
        if expr[0] in ('scope', 'if_expr', 'loop_expr', 'value_match'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != PLAIN_JOIN_TYPES[mode]:
                fail(line, f'résultat attendu : {PLAIN_JOIN_TYPES[mode]}')
            return value
        if plain_join_mode(expr) != mode:
            fail(line, f'résultat attendu : {PLAIN_JOIN_TYPES[mode]}')
        check_access(expr[1], line)
        return join_results[expr[1]][0]

    def builtin_error_mode(expr):
        if expr[0] == 'builtin_error':
            return expr[1]
        if expr[0] == 'name':
            return builtin_error_bindings.get(expr[1])
        signature = await_signature(expr)
        return signature[0] if signature and signature[0] in ERROR_VALUE_TYPES else None

    def builtin_error_value(expr, mode, line, *, following=None):
        if expr[0] in ('scope', 'if_expr', 'loop_expr', 'value_match') or computed_await(expr):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != ERROR_VALUE_TYPES[mode]:
                fail(line, f'erreur attendue : {ERROR_VALUE_TYPES[mode]}')
            return value
        if builtin_error_mode(expr) != mode:
            fail(line, f'erreur attendue : {ERROR_VALUE_TYPES[mode]}')
        if expr[0] == 'builtin_error':
            return str(expr[2])
        if expr[0] == 'await':
            return await_task(expr, line, returns_value=True, scalar_type=ERROR_VALUE_TYPES[mode])
        check_access(expr[1], line)
        return value_place(expr[1])

    def match_builtin_error(nodes, mode, value, line, *, valued, transfer_result, following, boolean, reference_result=False):
        tag_name, tag = nodes[1].args
        if tag[2] not in (('int', 0), ('int', ERROR_VALUE_TAGS[mode])) or tag[3] != ('int', 0):
            fail(line, 'match d’erreur builtin : variante incompatible')
        snapshot = temporary('int')
        steps.append(f'{snapshot} = {value};')
        utf8_match_tags[tag_name] = snapshot
        try:
            branch = nodes[2].args[0] if valued else nodes[2].args
            if (valued and branch[0] == 'scope') or (not valued and nodes[2].op == 'scope'):
                body = branch[2] if valued else branch[1]
                test, yes, no = None, body, None
            else:
                condition, yes, no = branch[1:] if valued else branch
                test = condition_value(condition, line)
            return emit_branches(test, yes, no, line, valued=valued, construct='match erreur',
                                 transfer_result=transfer_result, following=following, boolean=boolean, reference_result=reference_result)
        finally:
            del utf8_match_tags[tag_name]

    def runtime_error_value(expr, line, *, following=None):
        if expr[0] == 'utf8_runtime_error':
            return 'CRUST_RUNTIME_LAUNCH_FAILED'
        if expr[0] == 'await' and (is_runtime_error(expr) or computed_await(expr)):
            return await_task(expr, line, returns_value=True, scalar_type='runtime::Error')
        if expr[0] in ('scope', 'if_expr', 'value_match', 'loop_expr'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ == 'runtime::Error':
                return value
            fail(line, 'une valeur runtime::Error est requise')
        if expr[0] != 'name' or expr[1] not in runtime_error_bindings:
            fail(line, 'une valeur runtime::Error est requise')
        check_access(expr[1], line)
        return value_place(expr[1])

    def char_value(expr, line, *, context, following=None):
        if sync_signature(expr) is not None:
            return sync_call(expr, line, ('char', 'char'), following=following)[0]
        if (expr[0] == 'utf8_value' and expr[1][0] == 'name'
                and utf8_match_payloads.get(expr[1][1]) == 'char'):
            return f'char_result_value({utf8_match_results[expr[1][1]]})'
        if expr[0] == 'await' and (await_signature(expr) == ('char', 'char') or computed_await(expr)):
            return await_task(expr, line, returns_value=True, scalar_type='char')
        if expr[0] in ('if_expr', 'value_match', 'loop_expr'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ == 'char':
                return value
            fail(line, f'{context} exige une valeur char')
        if expr[0] != 'name' or expr[1] not in char_bindings:
            fail(line, f'{context} exige une valeur char')
        check_access(expr[1], line)
        return value_place(expr[1])

    def surviving_view_loans(loans, depth, line):
        for target, _ in loans:
            root = loan_root(target)
            for names, _, returned, _, _ in scopes[depth:]:
                if root not in names or not (references.get(root) == 'owned' or root in arrays):
                    continue
                if root in returned:
                    fail(line, 'transfert de la cible interdit pendant un emprunt actif')
                fail(line, 'une vue UTF-8 ne peut survivre à sa collection source locale')
        # A departing slice binding only describes an interval. Its backing
        # storage remains in the loan set and has been checked above.
        departing = {name for *_, local_refs in scopes[depth:] for name in local_refs if name in mutable_slices}
        return tuple(loan for loan in loans if loan_root(loan[0]) not in departing)

    def local_utf8_loans(expr, value=None):
        if value in utf8_result_loans:
            return tuple(utf8_result_loans[value])
        if expr[0] == 'ref' and expr[1] in byte_bindings:
            return ((expr[1], 'ref'),)
        if expr[0] == 'name':
            if reference_types.get(expr[1]) == 'u8':
                return ((expr[1], 'ref'), *received_refs.get(expr[1], ()))
            if collection_types.get(expr[1]) in ('String', *VECTOR_SLICE_MODES):
                return ((expr[1], 'mut' if references.get(expr[1]) == 'mut' else 'ref'),)
            return utf8_view_loans.get(expr[1], ())
        if expr[0] == 'ref_expr' and is_byte_array_element(expr[1]):
            root, _ = reference_array_path(expr[1])
            return ((root, 'mut' if parameter_modes.get(root) == 'array_mut' else 'ref'),)
        if expr[0] == 'utf8_value' and expr[1][0] == 'name' and utf8_match_payloads.get(expr[1][1]) == 'text':
            return utf8_result_loans.get(utf8_match_results[expr[1][1]], ())
        if expr[0] in ('utf8_slice', 'utf8_try_slice', 'ref_expr', 'array_index'):
            return local_utf8_loans(expr[1])
        if expr[0] == 'reborrow':
            if reference_types.get(expr[1]) == 'u8':
                return ((expr[1], expr[2]), *received_refs.get(expr[1], ()))
            if expr[1] in mutable_slices:
                return ((expr[1], expr[2]), *utf8_view_loans.get(expr[1], ()))
            return local_utf8_loans(('name', expr[1]))
        return ()

    def is_static_text(expr):
        if expr[0] == 'utf8_value' and expr[1][0] == 'name' and utf8_match_payloads.get(expr[1][1]) == 'text':
            return True
        return (expr[0] == 'text' or sync_signature(expr) == ('text', 'str') or await_signature(expr) == ('text', 'str') or (expr[0] == 'name' and expr[1] in text_bindings)
                or (expr[0] == 'utf8_slice' and (is_static_text(expr[1])
                    or expr[1][0] == 'name' and collection_types.get(expr[1][1]) == 'String')))

    def is_text_index(expr):
        return expr[0] == 'array_index' and (is_static_text(expr[1])
                or expr[1][0] == 'name' and collection_types.get(expr[1][1]) == 'String')

    def is_literal_utf8_storage(expr):
        if expr[0] == 'text':
            return True
        if expr[0] == 'name':
            return expr[1] in static_utf8_bindings
        if expr[0] in ('utf8_slice', 'utf8_try_slice'):
            return is_literal_utf8_storage(expr[1])
        return (expr[0] == 'ref_expr' and is_text_index(expr[1])
                and is_literal_utf8_storage(expr[1][1]))

    def indexed_text_view(receiver, index, line, *, following=None):
        collection = receiver[0] == 'name' and collection_types.get(receiver[1]) == 'String'
        if collection:
            name = receiver[1]
            check_access(name, line)
            view = f'string_view(frame->{fields[name]})'
            loans = [(name, 'mut' if references.get(name) == 'mut' else 'ref')]
        else:
            view = static_text_value(receiver, line, following=following)
            loans = list(local_utf8_loans(receiver, view))
        snapshot = temporary('CrustText')
        steps.append(f'{snapshot} = {view};')
        utf8_result_loans[snapshot] = tuple(loans)
        active_loans[id(loans)] = loans
        try:
            offset = expression(index, line)
        finally:
            del active_loans[id(loans)]
        return snapshot, offset

    def static_text_byte_address(expr, line, *, following=None):
        _, receiver, index = expr
        if index[0] == 'int' and (index[1] < 0 or
                (receiver[0] == 'text' and index[1] >= len(receiver[1]))):
            fail(line, 'indice UTF-8 hors bornes')
        snapshot, offset = indexed_text_view(receiver, index, line, following=following)
        pointer = f'text_byte_address({snapshot}, {offset})'
        utf8_result_loans[pointer] = utf8_result_loans.get(snapshot, ())
        return pointer

    def is_static_byte_ref(expr):
        return (sync_signature(expr) == ('byte_ref', 'u8')
                or await_signature(expr) == ('byte_ref', 'u8')
                or expr[0] == 'ref' and expr[1] in byte_bindings
                or expr[0] == 'name' and expr[1] in byte_ref_bindings
                or expr[0] == 'reborrow' and expr[2] == 'ref' and (expr[1] in byte_ref_bindings or reference_types.get(expr[1]) == 'u8')
                or expr[0] == 'ref_expr' and (is_text_index(expr[1]) or is_byte_array_element(expr[1])
                                             or collection_index_type(expr[1]) == 'Vector<u8>'
                                             or indexed_vector_view_mode(expr[1]) == 'vector_bytes'))

    def static_byte_ref_value(expr, line, *, following=None):
        if sync_signature(expr) == ('byte_ref', 'u8'):
            return sync_call(expr, line, ('byte_ref', 'u8'), following=following)[0]
        # An expected shared-byte parameter may read through a mutable loan.
        # Do not change the inferred type of a named &mut u8 elsewhere.
        if expr[0] == 'name' and reference_types.get(expr[1]) == 'u8':
            check_access(expr[1], line)
            return f'frame->{fields[expr[1]]}'
        if expr[0] == 'await' and (await_signature(expr) == ('byte_ref', 'u8') or computed_await(expr)):
            return await_task(expr, line, returns_value=True, scalar_type='&u8')
        if expr[0] in ('scope', 'if_expr', 'value_match', 'loop_expr'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ == '&u8':
                return value
            fail(line, 'un &u8 sur un stockage statique est requis')
        if not is_static_byte_ref(expr):
            fail(line, 'un &u8 sur un stockage statique est requis')
        if expr[0] == 'ref':
            check_access(expr[1], line)
            return f'&({value_place(expr[1])})'
        if expr[0] == 'ref_expr':
            if indexed_vector_view_mode(expr[1]) == 'vector_bytes':
                return vector_view_address(expr[1], line, 'vector_bytes')
            if is_byte_array_element(expr[1]) or collection_index_type(expr[1]) == 'Vector<u8>':
                pointer, _ = capture_array_place(expr[1], 'ref', line, expected_element='uint8_t')
                return pointer
            return static_text_byte_address(expr[1], line, following=following)
        check_access(expr[1], line)
        if reference_types.get(expr[1]) == 'u8':
            return f'frame->{fields[expr[1]]}'
        return value_place(expr[1])

    def static_text_value(expr, line, *, following=None):
        if sync_signature(expr) == ('text', 'str'):
            return sync_call(expr, line, ('text', 'str'), following=following)[0]
        if expr[0] == 'await' and (await_signature(expr) == ('text', 'str') or computed_await(expr)):
            return await_task(expr, line, returns_value=True, scalar_type='&str')
        if expr[0] in ('scope', 'if_expr', 'value_match', 'loop_expr'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ == '&str':
                return value
            fail(line, 'une vue &str statique est requise dans le corps async')
        if expr[0] == 'text':
            data = ''.join(f'\\{byte:03o}' for byte in expr[1])
            return f'((CrustText){{(const unsigned char *)"{data}", {len(expr[1])}, 0}})'
        if expr[0] == 'name' and expr[1] in text_bindings:
            check_access(expr[1], line)
            return value_place(expr[1])
        if expr[0] == 'utf8_value' and expr[1][0] == 'name' and utf8_match_payloads.get(expr[1][1]) == 'text':
            return f'text_result_value({utf8_match_results[expr[1][1]]})'
        if expr[0] == 'utf8_slice' and is_static_text(expr):
            return prepare_text_slice(expr, line)
        fail(line, 'une vue &str statique est requise dans le corps async')

    def prepare_text_slice(expr, line, *, fallible=False):
        receiver, *bounds = expr[1:]
        if not fallible and (error := text_slice_bound_error(receiver, bounds)):
            fail(line, error)
        snapshot = temporary('CrustText')
        collection = receiver[0] == 'name' and collection_types.get(receiver[1]) == 'String'
        if collection:
            check_access(receiver[1], line)
            view = f'string_view(frame->{fields[receiver[1]]})'
        else:
            view = static_text_value(receiver, line)
        steps.append(f'{snapshot} = {view};')
        prepared = []
        loans = list(local_utf8_loans(receiver, view))
        active_loans[id(loans)] = loans
        try:
            for bound in bounds:
                value = expression(bound, line)
                saved = temporary('int')
                steps.append(f'{saved} = {value};')
                prepared.append(saved)
        finally:
            del active_loans[id(loans)]
        end = prepared[1] if len(prepared) == 2 else '0'
        operation = 'text_try_slice' if fallible else 'text_slice'
        value = f'{operation}({snapshot}, {prepared[0]}, {end}, {int(len(prepared) == 2)})'
        utf8_result_loans[value] = tuple(loans)
        return value

    def condition_value(condition, line):
        if condition[0] == 'truth':
            return '1' if condition[1] else '0'
        _, operator, left, right = condition
        left_value, left_type = infer_scalar_value(left, line)
        saved_left = temporary(capture_type(SCALAR_MODES.get(left_type, 'scalar')))
        steps.append(f'{saved_left} = {left_value};')
        right_value, right_type = infer_scalar_value(right, line)
        if (left_type != right_type or left_type != 'Bool' and numeric_type(left_type) is None
                or (left_type == 'Bool' and operator not in ('==', '!='))):
            fail(line, 'comparaison async incompatible avec les types des opérandes')
        return f'{saved_left} {operator} {right_value}'

    def direct_exchange_success(condition):
        if (condition[0] == 'compare' and condition[1] == '==' and condition[3] == ('int', 0)
                and condition[2][0] == 'array_handle_exchange_status'):
            name = condition[2][1][1]
            record = join_results.get(name)
            if record is not None and record[1] == 'rejected_allocation':
                return name
        return None

    def conditional(condition, yes, no, line, *, valued, following=None, boolean=False):
        test = condition_value(condition, line)
        return emit_branches(test, yes, no, line, valued=valued, construct='if', following=following,
                             boolean=boolean, exchange_success=direct_exchange_success(condition))

    def emit_transferred_control(expr, line, *, following=None):
        place_local_result(expr)
        if expr[0] == 'match_expr':
            return match_enum(expr[1], valued=True, transfer_result=True, following=following)
        if expr[0] == 'value_match':
            return match_async_result(expr[1], line, transfer_result=True, following=following)
        _, condition, yes, no = expr
        test = condition_value(condition, line)
        return emit_branches(test, yes, no, line, valued=True, construct='if',
                             transfer_result=True, following=following, exchange_success=direct_exchange_success(condition))

    def emit_computed_transfer(expr, line, *, following=None):
        place_local_result(expr)
        if expr[0] == 'task_select':
            return 'selection', create_selection(expr, line)
        if sync_signature(expr) in task_sync_types:
            return 'task', create_task(expr, line)
        if sync_signature(expr) in handle_sync_types:
            return 'execution', sync_call(expr, line, execution=True, following=following)
        if (sync_signature(expr) in owned_output_types or expr[0] in ('new', 'new_enum')
                or handle_remove_receiver(expr) is not None
                or structure_copy_source(expr) is not None or inline_vector_source(expr) is not None):
            return 'owned', sync_owned_value(expr, line, following=following)
        if expr[0] == 'task_spawn':
            return 'execution', spawn_task(expr[1], line,
                blocking=len(expr) > 2 and expr[2] == 'blocking',
                native=len(expr) > 2 and expr[2] == 'native')
        if expr[0] in ('if_expr', 'value_match', 'match_expr'):
            return emit_transferred_control(expr, line, following=following)
        if expr[0] == 'loop_expr':
            return emit_loop(expr[1].args[0], line, valued=True, following=following)
        if expr[0] == 'scope' and ends_in_transfer(expr[2]):
            body = expr[2]
            return emit_region_block(body, expr[3] if len(expr) > 3 else None, line, valued=False,
                                 construct='bloc', export_name=body[-1].args[0], following=following)
        fail(line, 'une tâche calculée exige une expression avec transfert <-')

    def spawn_task(operand, line, *, blocking=False, native=False):
        if operand[0] == 'down':
            require_local_async_value(operand[1], line)
            record = consume_task(operand[1], line)
        elif operand[1][0] == 'call':
            record = create_task(operand[1], line)
        else:
            kind, record = emit_computed_transfer(operand[1], line)
            if kind != 'task':
                fail(line, 'spawn exige une tâche inactive')
        enable_threads()
        task, returns_int, loans, nominal, returned_loans, field_changes = record
        handle = temporary('CrustAsyncExecution')
        start = ('task_native_async_start' if native else
                 'task_async_start_blocking' if blocking else 'task_async_start')
        steps.append(f'{start}(&{handle}, {task});')
        if task in task_handle_result_pools:
            task_handle_result_pools[f'&{handle}'] = task_handle_result_pools[task]
        if task in task_handle_output_loans:
            task_handle_output_loans[f'&{handle}'] = task_handle_output_loans[task]
        if task in task_handle_field_changes:
            task_handle_field_changes[f'&{handle}'] = task_handle_field_changes[task]
        move_stored_fields(task, f'&{handle}')
        if blocking and node.numeric_profile:
            blocking_executions.add(f'&{handle}')
        return f'&{handle}', returns_int, loans, nominal, returned_loans, field_changes

    def prepare_utf8_loop(body, following, line):
        # Stored-field hints share the retry engine with view hints, but their
        # keys are tuples so they cannot collide with source variable names.
        for key, additions in utf8_loop_hints.get(id(body), {}).items():
            if isinstance(key, tuple) and key[0] == 'storage_binding':
                holder = key[1]
                origins = frozenset(origin for origin, _ in additions)
                if any(origin not in fields and origin not in local_pools for origin in origins):
                    fail(line, 'stockage non durable à la reprise de boucle')
                storage_bindings[holder] = storage_bindings.get(holder, frozenset()) | origins
            elif isinstance(key, tuple) and key[0] == 'storage_root':
                if (None, 'storage') in additions:
                    active_loans.pop(key, None)
                elif key in active_loans:
                    roots = list(dict.fromkeys((*active_loans[key], *additions)))
                    if any(origin not in fields and origin not in local_pools for origin, _ in roots):
                        fail(line, 'stockage de base non durable à la reprise de boucle')
                    active_loans[key] = roots
                if key[1] in storage_bindings:
                    storage_bindings[key[1]] |= frozenset(origin for origin, _ in additions if origin is not None)
            elif isinstance(key, tuple) and key[0] in ('stored_field', 'owned_storage'):
                _, holder, path = key
                initial = active_loans.get(key, initial_stored_field_loans(holder, path)
                                           if key[0] == 'stored_field' else ())
                roots = tuple(dict.fromkeys((*initial, *additions)))
                if any(loan_root(target) not in fields and target not in local_pools for target, _ in roots):
                    fail(line, 'cible de champ non durable à la reprise de boucle')
                install_field_change(key, roots)
        names = mutable_utf8_bindings & fields.keys()
        exit_live, head_live = {}, {}
        for name in names:
            owner = next((i for i, scope in enumerate(scopes) if name in scope[4]), 0)
            exit_live[name] = utf8_current_live(following, name, owner_depth=owner)
            head_live[name] = utf8_loop_live(body, name, exit_live[name])
            old = scopes[owner][4].get(name)
            if old is not None:
                active_loans.pop(id(old[0]), None)
            roots = tuple(dict.fromkeys((*utf8_view_loans.get(name, ()),
                                        *utf8_loop_hints.get(id(body), {}).get(name, ()))))
            if head_live[name] and any(loan_root(target) not in fields for target, _ in roots):
                fail(line, 'vue de boucle issue d’une source non durable à la reprise')
            loans = list(roots)
            utf8_view_loans[name] = roots
            scopes[owner][4][name] = loans, float('inf')
            if head_live[name] and loans:
                active_loans[id(loans)] = loans
        return names, exit_live, head_live

    def verify_utf8_backedge(loop, state, line,
                             message='la reprise doit préserver les obligations de nettoyage de la boucle async'):
        if non_utf8_control_state(state, ignore_stored_fields=True) != non_utf8_control_state(loop['entry'], ignore_stored_fields=True):
            fail(line, message)
        additions = {}
        for holder, initial in loop['entry'][8].items():
            extra = state[8].get(holder, frozenset()) - initial
            if extra:
                additions['storage_binding', holder, ()] = tuple((origin, 'storage') for origin in extra)
        for key, initial in loop['entry'][2].items():
            if isinstance(key, tuple) and key[0] == 'storage_root':
                if key not in state[2]:
                    additions[key] = ((None, 'storage'),)
                elif set(state[2][key]) - set(initial):
                    additions[key] = tuple(state[2][key])
        for key, roots in state[2].items():
            if isinstance(key, tuple) and key[0] in ('stored_field', 'owned_storage'):
                _, holder, path = key
                initial = loop['entry'][2].get(key, initial_stored_field_loans(holder, path)
                                               if key[0] == 'stored_field' else ())
                if set(roots) - set(initial):
                    additions[key] = tuple(roots)
        for name in loop['utf8_bindings']:
            if not loop['utf8_head_live'][name]:
                continue
            roots = state[6].get(name, ())
            record = next((local[name] for local in state[7] if name in local), None)
            if roots and (record is None or id(record[0]) not in state[2]):
                fail(line, 'prêt de vue de boucle perdu avant la reprise')
            if set(roots) - set(loop['entry'][6].get(name, ())):
                additions[name] = roots
        if additions:
            raise _WidenUtf8Loop(loop['key'], additions)

    def emit_loop(body, line, *, valued=False, following=None):
        # A loop may publish another write before a prior status is inspected.
        guarded_receipts.clear()
        if valued:
            from types import SimpleNamespace
            place_local_result(('loop_expr', SimpleNamespace(args=(body,))))
        names, exit_live, head_live = prepare_utf8_loop(body, following, line)
        entry = control_state()
        loop = {'entry': entry, 'depth': len(scopes), 'fields': set(fields),
                'valued': valued, 'result': None, 'loans': [], 'returned_loans': [], 'field_changes': [], 'exit': None,
                'selection_branches': [], 'selection_paths': [], 'task_prefixes': [], 'task_result_types': set(), 'handle_kinds': set(),
                'handle_origins': set(), 'handles_autonomous': True, 'returned_handle_pools': set(),
                'returned_handle_output_loans': [], 'returned_handle_changes': [],
                'following': following, 'body': body, 'utf8_loans': [], 'reference_loans': [], 'key': id(body),
                'utf8_bindings': names, 'utf8_exit_live': exit_live, 'utf8_head_live': head_live,
                'created_tasks': set(), 'abandoned_tasks': set(), 'sync_calls': set(), 'has_backedge': False}
        steps.append('for (;;) {')
        if body and body[0].op == 'while_check':
            test = condition_value(body[0].args[0], body[0].line)
            if control_state() != entry:
                fail(line, 'le test de boucle async doit préserver les obligations de nettoyage')
            steps.append(f'if (!({test})) break;')
            release_loop_exit_loans(loop)
            loop['exit'] = control_state()
            active_loans.update(entry[2])
            body = body[1:]
        loops.append(loop)
        emit_branches('1', body, [], line, valued=False, construct='boucle')
        if loop['has_backedge']:
            loop_activity.add((line, frozenset(loop['created_tasks']), frozenset(loop['abandoned_tasks']),
                               frozenset(loop['sync_calls'])))
        loops.pop()
        steps.append('}')
        exit_state = loop['exit']
        if exit_state is not None:
            restore_control_state(exit_state)
        if not valued:
            return exit_state is None
        if loop['result'] is None:
            if exit_state is None:
                raise NoAsyncContinuation
            fail(line, 'boucle expression async sans break avec résultat')
        kind, target, returns_int, nominal = loop['result']
        if kind == 'reference':
            loans = list(dict.fromkeys(loop['reference_loans']))
            active_loans[id(loans)] = loans
            return kind, (target, loans, (returns_int, nominal))
        if kind == 'owned':
            owned_result_types[target] = nominal
            return kind, target
        if kind in SCALAR_TYPES:
            if kind in ASYNC_CAPTURE_VIEW_MODES:
                utf8_result_loans[target] = tuple(dict.fromkeys(loop['utf8_loans']))
            return kind, target
        if kind == 'array':
            return kind, (target, returns_int, nominal)
        if kind in OWNED_WRAPPER_TYPES:
            owned_result_types[target] = nominal
            return kind, (target, OWNED_WRAPPER_PAYLOADS[kind], None)
        loans = list(dict.fromkeys(loop['loans']))
        active_loans[id(loans)] = loans
        if kind == 'selection':
            return kind, SelectionState(f'(*{target})', tuple(loop['selection_branches']), loans, returns_int,
                                        tuple(loop['selection_paths']))
        if kind == 'execution' and loop['handle_kinds'] == {True}:
            blocking_executions.add(target)
        if kind == 'execution' and loop['handles_autonomous']:
            execution_pools[target] = frozenset(loop['handle_origins'])
        if loop['returned_handle_pools']:
            task_handle_result_pools[target] = frozenset(loop['returned_handle_pools'])
        if loop['returned_handle_output_loans']:
            task_handle_output_loans[target] = tuple(dict.fromkeys(loop['returned_handle_output_loans']))
        if any(loop['returned_handle_changes']):
            task_handle_field_changes[target] = tuple(dict.fromkeys(loop['returned_handle_changes']))
        record = (target, returns_int, loans, nominal)
        if kind == 'task':
            task_prefix_changes[target] = tuple(loop['task_prefixes'])
        return kind, (*record, list(dict.fromkeys(loop['returned_loans'])), tuple(loop['field_changes']))

    def cleanup_async_values(names, returned, line):
        for name in reversed(names):
            if name in local_pools:
                if name in returned:
                    fail(line, 'un pool local ne peut être transféré')
                if any(name in origins for owner, origins in storage_bindings.items() if owner not in consumed):
                    fail(line, 'transfert refusé : une allocation survit à son pool local')
                if any(loan_root(target) == name for loans in active_loans.values() for target, _ in loans):
                    fail(line, 'fermeture du pool local avec une tâche ou un emprunt actif')
                steps.append(f'source_close(&{local_pools[name]});')
                continue
            if name in arrays:
                continue
            if name in join_results:
                record = join_results[name]
                if name in returned:
                    if record is None:
                        fail(line, f"transfert refusé : '{name}' déjà consommé")
                elif record is not None:
                    if record[1] in ('map_owned_option', 'map_owned_exchange'):
                        drop_map_owned_result(name, record)
                    else:
                        discard_owned_join(name, line)
                continue
            if references.get(name) == 'owned':
                if name in returned:
                    if name in consumed:
                        fail(line, f"transfert refusé : '{name}' déjà consommé")
                    check_access(name, line, write=True)
                elif name not in consumed:
                    drop_owned(name, line)
                continue
            if name in selections:
                value, destroy = selections[name], discard_selection
            elif name in executions:
                value, destroy = executions[name], abandon_execution
            else:
                value, destroy = tasks[name], discard_task
            if name in returned:
                if value is None:
                    fail(line, f"transfert refusé : '{name}' déjà consommé")
                continue
            if value is not None:
                if destroy is discard_task:
                    warn(line, 'tâche inactive nettoyée sans avoir été démarrée', name)
                destroy(name, line)

    def cleanup_scope(index, line):
        names, imports, returned, previous, local_refs = scopes[index]
        cleanup_async_values(names, returned, line)
        departing = mutable_slices & local_refs.keys()
        if departing:
            for *_, outer_refs in scopes[:index]:
                for name, (loans, last) in outer_refs.items():
                    if name not in utf8_view_loans:
                        continue
                    retained = [loan for loan in loans if loan_root(loan[0]) not in departing]
                    if len(retained) == len(loans):
                        continue
                    if active_loans.pop(id(loans), None) is not None:
                        active_loans[id(retained)] = retained
                    outer_refs[name] = retained, last
                    utf8_view_loans[name] = tuple(retained)
        if returned:
            parent_names = scopes[index - 1][0]
            for name in names:
                if name in returned:
                    del parent_names[name]
                    parent_names[name] = None
        for name in names.keys() - imports:
            if name in selections:
                del selections[name]
                mutable.discard(name)
            elif name in executions:
                del executions[name]
            elif name in tasks:
                del tasks[name]
            else:
                consumed.discard(name)
        # Plain locals have no destruction entry, but their drop state is
        # lexical too. It must not poison a later binding of the same name.
        local_storage = set()
        for name, owner in inline_binding_scopes.items():
            if owner == id(names):
                consumed.discard(name)
                if (name not in returned and name not in references and name not in received_refs
                        and name not in mutable_slices and parameter_modes.get(name) not in ARRAY_BORROWS
                        and (name in arrays or inline_scalar_mode(name) in (*MODE_TYPES, 'bool', 'char'))):
                    local_storage.add(name)
        if any(loan_root(target) in local_storage and mode != 'storage'
               for loans in active_loans.values() for target, mode in loans):
            fail(line, 'sortie de bloc : une réservation active vise encore une valeur locale')
        for name in join_results.keys() - previous[4].keys():
            del join_results[name]

    def cleanup_prepared_captures(depth=0):
        # A later argument can leave the call before its task exists. The
        # earlier moved arguments are then owned by these temporary captures.
        # A break/continue of a loop *inside* a later argument does not abort
        # the surrounding call, hence the lexical-depth check.
        for owner_depth, cells, loans in reversed(pending_capture_groups):
            if owner_depth < depth:
                continue
            active_loans.pop(id(loans), None)
            for cell in reversed(cells):
                if isinstance(cell, tuple):
                    if cell[0] == 'execution':
                        fail(node.line, 'attente requise : sortie abandonnant un handle préparé comme argument')
                    steps.extend((f'task_discard({cell[1]});', f'{cell[1]} = NULL;'))
                else:
                    steps.append(f'if ({cell}) cell_drop({cell});')
                    steps.append(f'{cell} = NULL;')

    def loop_exit(op, value, line):
        if not loops:
            fail(line, f'{op} hors boucle async')
        loop = loops[-1]
        entry, depth = loop['entry'], loop['depth']
        if op == 'break':
            if not loop['valued'] and value is not None and value[0] == 'move':
                name = value[1]
                if references.get(name) == 'owned' or name in arrays:
                    if name in consumed:
                        fail(line, f"'{name}' n’est plus utilisable après drop ou transfert")
                elif (executions.get(name) is None and tasks.get(name) is None
                        and selections.get(name) is None
                        and not (is_owned_join(name, nested=True) and join_results[name] is not None)):
                    fail(line, f"tâche ou handle '{name}' inconnu ou déjà consommé")
                warn(line, 'transfert sans receveur', name)
                value = None
            if loop['valued'] != (value is not None):
                fail(line, 'break async doit correspondre au résultat attendu de la boucle')
            if value is not None:
                release_loop_exit_loans(loop, earlier=(value,))
                save_break_result(loop, value, line)
            release_loop_exit_loans(loop)
        else:
            release_statement_loans((), utf8_only=True)
        cleanup_prepared_captures(depth)
        for index in range(len(scopes) - 1, depth - 1, -1):
            release_results(scopes[index][4])
            cleanup_scope(index, line)
        state = control_state(depth)
        if op == 'continue':
            loop['has_backedge'] = True
            verify_utf8_backedge(loop, state, line, 'continue doit préserver les obligations de nettoyage de la boucle async')
        elif loop['exit'] is None:
            loop['exit'] = state
        elif state != loop['exit']:
            loop['exit'] = merge_utf8_control_states(
                loop['exit'], state, line,
                'les sorties de boucle async doivent conserver les mêmes obligations de nettoyage')
        steps.append(f'{op};')

    def save_break_result(loop, value, line):
        if value[0] == 'move':
            name = value[1]
            names = set().union(*(scope[0] for scope in scopes[loop['depth']:]))
            imports = set().union(*(scope[1] for scope in scopes[loop['depth']:]))
            if name not in names or (name not in imports and any(name in loop['entry'][slot] for slot in (0, 1, 4, 9))):
                fail(line, 'break <- exige une tâche, un handle ou un Result créé dans la boucle async')
            local_names = fields.keys() - loop['fields']
            kind, record = export_async_value(name, local_names, line, names=names, depth=loop['depth'])
            if kind == 'owned':
                result, returns_int, nominal = record, None, owned_result_types.get(record, 'Int')
                ctype = 'Cell *'
            elif kind == 'array':
                result, returns_int, nominal = record
                ctype = nominal
            elif kind in OWNED_WRAPPER_TYPES:
                result, returns_int, nominal = record[0], None, owned_result_types.get(record[0], 'Int')
                ctype = OWNED_WRAPPER_TYPES[kind]
            elif kind == 'selection':
                result = f'&{record.c}'
                returns_int, nominal = record.awaited, task_result_signature(record.branches[0])
                ctype = 'CrustSelect *'
                loop['selection_branches'].extend(record.branches)
                loop['selection_paths'].extend(record.paths or (record.branches,))
                active_loans.pop(id(record.loans), None)
                loop['loans'].extend(record.loans)
            else:
                result, returns_int, loans, nominal = record[:4]
                if kind == 'execution':
                    loop['handles_autonomous'] &= autonomous_execution(record)
                    loop['handle_origins'].update(execution_pools.get(result, (nominal,)))
                    loop['handle_kinds'].add(result in blocking_executions)
                    if len(loop['handle_kinds']) > 1:
                        fail(line, 'les break exigent le même type de handle')
                loop['task_result_types'].add(task_result_signature(record))
                if len(loop['task_result_types']) > 1:
                    fail(line, 'les break de tâches exigent le même type et le même stockage de résultat')
                if kind == 'task':
                    loop['task_prefixes'].extend(task_prefix_changes.get(result, ((None, (), ()),)))
                loop['returned_handle_pools'].update(known_handle_result_pools(result, nominal))
                loop['returned_handle_output_loans'].extend(task_output_projection(record))
                loop['returned_handle_changes'].extend(task_handle_field_changes.get(result, ((),)))
                loop['returned_loans'].extend(record[4])
                loop['field_changes'].extend(record[5])
                del active_loans[id(loans)]
                loop['loans'].extend(loans)
                ctype = 'CrustTask *' if kind == 'task' else 'CrustAsyncExecution *'
        elif reference_shape(value) is not None:
            result, loans, (returns_int, nominal) = reference_value(value, line)
            loop['reference_loans'].extend(surviving_reference_loans(loans, loop['depth'], line))
            active_loans.pop(id(loans), None)
            kind = 'reference'
            ctype = capture_type(returns_int, nominal)
        else:
            result, typ = infer_scalar_value(value, line)
            if typ in ASYNC_VIEW_TYPES:
                loans = local_utf8_loans(value, result)
                loop['utf8_loans'].extend(surviving_view_loans(loans, loop['depth'], line))
            kind = SCALAR_MODES[typ]
            returns_int, nominal = None, None
            ctype = capture_type(kind)
        if loop['result'] is None:
            suffix = array_dimensions(returns_int) if kind == 'array' else ''
            loop['result'] = kind, temporary(ctype, suffix), returns_int, nominal
        expected, target, expected_result, expected_nominal = loop['result']
        if (kind, returns_int, nominal) != (expected, expected_result, expected_nominal):
            fail(line, 'les break async doivent fournir le même type et le même mode')
        if kind != 'array':
            if kind in ('owned', *OWNED_WRAPPER_TYPES):
                keep_storage(target, storage_of(result))
            if kind in ('owned', *OWNED_WRAPPER_TYPES, 'task', 'execution'):
                move_stored_fields(result, target)
            steps.append(f'{target} = {result};')
        elif all(returns_int):
            steps.append(f'memcpy({target}, {result}, sizeof {target});')

    def async_binding_values(name):
        if name in selections:
            return selections
        if is_owned_join(name, nested=True):
            return join_results
        return executions if name in executions else tasks

    def import_async_value(name, line):
        imports = scopes[-1][1]
        if name not in scopes[-2][0] or name in imports:
            fail(line, '-> exige une valeur rattachée au parent direct')
        if references.get(name) == 'owned':
            check_access(name, line, write=True)
        elif async_binding_values(name).get(name) is None:
            fail(line, f"'{name}' déjà consommé")
        imports.add(name)

    def emit_block(statement, following):
        return emit_region_block(statement.args[1], statement.region_limit, statement.line,
                             valued=False, construct='bloc', following=following)

    def emit_region_block(body, limit, line, **options):
        # Configuration is lexical, fixed at construction, and inherited only
        # through blocks of this function. Suspension does not change it.
        region_limits.append(region_limits[-1] if limit is None else limit)
        try:
            return emit_branches(None, body, None, line, **options)
        finally:
            region_limits.pop()

    def match_enum(statement, *, valued, following=None, boolean=False,
                   transfer_result=False, reference_result=False):
        holder, arms = statement.args
        line = statement.line
        typ = reference_types.get(holder, collection_types.get(holder))
        layouts = enum_layouts.get(typ)
        if layouts is None or holder not in fields:
            fail(line, 'match async : enum requis')
        if statement.consuming and references.get(holder) != 'owned':
            fail(line, 'match consommant : allocation possédée requise')
        if statement.mutable and not (references.get(holder) == 'mut'
                or references.get(holder) == 'owned' and holder in mutable):
            fail(line, 'match mutable : accès mutable au porteur requis')
        seen = set()
        for declared, variant, pattern, body in arms:
            if declared != typ or variant not in layouts or variant in seen:
                fail(line, 'match : variante inconnue, incompatible ou dupliquée')
            seen.add(variant)
            names = [field for field, _ in pattern]
            if len(set(names)) != len(names) or set(names) != dict(layouts[variant]).keys():
                fail(line, 'match : fournir tous les champs sans doublon')
            if statement.consuming:
                for field, alias in pattern:
                    if dict(layouts[variant])[field].startswith('A<'):
                        if alias == '_':
                            fail(line, 'un motif _ ne peut pas écarter une allocation possédée')
                        if not has_future_value_use(alias, body):
                            fail(line, f"résultat propriétaire '{alias}' sans usage explicite")
        if seen != layouts.keys():
            fail(line, 'match non exhaustif')
        check_access(holder, line, write=statement.mutable or statement.consuming)
        cell = f'frame->{fields[holder]}'
        tag = temporary('int')
        steps.append(f'{tag} = {cell}->layout->arm_tag;')
        return emit_branches(tag, None, None, line, valued=valued, construct='match',
            following=following, boolean=boolean, transfer_result=transfer_result,
            reference_result=reference_result, enum_match=(statement, typ, cell))

    def emit_branches(test, yes, no, line, *, valued, construct, join_payload=None,
                      export_name=None, transfer_result=False, following=None, boolean=False, reference_result=False,
                      enum_match=None, exchange_success=None, map_match=None):
        for branch in (map_match[1].values() if map_match else (yes, no)):
            if isinstance(branch, list):
                place_local_assignments(branch)
        target = temporary('int') if valued and not transfer_result and boolean is not None else None
        scalar_type = None
        selected_signature = None
        selected_loans, selected_returned_loans, selected_field_changes = [], [], []
        selected_execution_storage = set()
        selected_handle_kinds = set()
        selected_execution_origins = set()
        selected_returned_handle_pools = set()
        selected_returned_handle_output_loans = []
        selected_returned_handle_changes = []
        selected_executions_autonomous = True
        selected_branches, selected_paths, selected_task_prefixes = [], [], []
        selected_utf8_loans = []
        selected_reference_loans = []
        reference_signature = None
        before = control_state()
        had_result_loan = join_payload is not None and id(join_payload[3]) in active_loans
        continuing = []
        if map_match:
            _, map_arms, _ = map_match
            tags = tuple(sorted(map_arms))
            arms = tuple(map_arms[tag] for tag in tags)
            steps.append(f'if ({test} == {tags[0]}) {{')
        elif enum_match:
            match, enum_type, enum_cell = enum_match
            arms = tuple([replace(n, op='if_yield', args=(('name', n.args[0]),))
                          if n.op == 'match_yield' else n for n in arm[3]] for arm in match.args[1])
            tags = tuple(list(enum_layouts[enum_type]).index(arm[1]) for arm in match.args[1])
            steps.append(f'if ({test} == {tags[0]}) {{')
        else:
            steps.append('{' if no is None else f'if ({test}) {{')
            arms = (yes,) if no is None else (yes, no)
        exported = None
        if following is not None:
            lexical_tails.append((len(scopes) - 1, following))
        for index, body in enumerate(arms):
            arm_value = body if isinstance(body, tuple) else None
            if arm_value is not None:
                body = []
            locals_in_arm = []
            arm_entry = control_state()
            imports, returned_imports = set(), set()
            local_refs = {}
            scopes.append(({}, imports, returned_imports, arm_entry, local_refs))
            if join_payload:
                joined_value, _, status, *_ = join_payload
                refine_result_outcome(joined_value, (status == 0) == (index == 0))
            if map_match:
                result, _, owned_map = map_match
                status = tags[index]
                ref_map = result in map_reference_payloads
                if owned_map or ref_map:
                    refine_result_outcome(result, status != 5)
                binds_value = body and body[0].op == 'var' and body[0].args[1][0] in ('utf8_value', 'utf8_error')
                if binds_value:
                    if status == 6 or (status == 5) != (body[0].args[1][0] == 'utf8_error'):
                        fail(line, 'HashMap async : motif de valeur incompatible')
                    name = body[0].args[0]
                    if name != '_' and not body[0].discarded_pattern:
                        if owned_map:
                            map_owned_result_payload(result, status, name, line)
                        elif ref_map:
                            member = declare(name, line)
                            _, typ, _, _ = matched_map_slots[result]
                            references[name], reference_types[name] = 'ref', typ[1:]
                            held = list(map_reference_payloads[result][status])
                            active_loans[id(held)] = held
                            received_refs[name] = held
                            track_result(name, held, body[1:], -1)
                            steps.append(f'memcpy(&frame->{member}, &{result}.value, sizeof(frame->{member}));')
                        else:
                            _, typ, ctype, _ = matched_map_slots[result]
                            member = declare(name, line)
                            record_inline_type(name, 'Bool' if typ == 'bool' else typ)
                            saved = temporary(ctype)
                            steps.append(f'memcpy(&{saved}, &{result}.value, sizeof({saved}));')
                            steps.append(f'frame->{member} = {saved};')
                        locals_in_arm.append(name)
                    elif owned_map:
                        steps.append(f'cell_drop(crust_map_result_handle(&{result}));')
                    body = body[1:]
                elif owned_map and status != 6:
                    steps.append(f'cell_drop(crust_map_result_handle(&{result}));')
                if owned_map:
                    clear_stored_fields(result)
            if exchange_success is not None and index == 0:
                record = consume_owned_join(exchange_success, line)
                clear_stored_fields(record[0])
            if enum_match:
                holder = match.args[0]
                _, variant, pattern, _ = match.args[1][index]
                layout = enum_layouts[enum_type][variant]
                reservation = 'mut' if match.mutable or references.get(holder) == 'mut' else 'ref'
                held = [(holder, reservation), *received_refs.get(holder, ())]
                if not match.consuming:
                    active_loans[id(held)] = held
                    local_refs['\0match:' + holder] = held, float('inf')
                for field, alias in pattern:
                    if alias == '_':
                        continue
                    field_index = next(i for i, (name, _) in enumerate(layout) if name == field)
                    declared = layout[field_index][1]
                    member = declare(alias, line)
                    locals_in_arm.append(alias)
                    offset = structure_offset(layout, field_index)
                    if declared == 'Int':
                        steps.append(f'frame->{member} = cell_load_int({enum_cell}, {offset});')
                        continue
                    if declared in FIELD_C_TYPES:
                        record_inline_type(alias, 'Bool' if declared == 'bool' else declared)
                        destination = f'frame->{member}'
                        steps.append(f'memcpy(&{destination}, cell_numeric_address({enum_cell}, {offset}, '
                                     f'sizeof({destination})), sizeof({destination}));')
                        continue
                    owned = declared.startswith('A<')
                    pointee = declared.removeprefix('&').removeprefix('mut ')
                    typed_reference = declared.startswith('&') and pointee in reference_structs
                    if declared not in ('&Int', '&mut Int') and not owned and not typed_reference:
                        fail(line, 'match async : type de champ non représentable')
                    if owned and match.consuming:
                        target_type = declared[2:-1]
                        references[alias] = 'owned'
                        if target_type != 'Int':
                            collection_types[alias] = target_type
                            reference_types[alias] = target_type
                        scopes[-1][0][alias] = None
                        path = (variant, field)
                        origins = active_loans.get(('owned_storage', holder, path))
                        storage_bindings[alias] = (frozenset(origin for origin, _ in origins) if origins is not None
                                                   else storage_bindings.get(holder, frozenset()))
                        for key, loans in list(active_loans.items()):
                            if (isinstance(key, tuple) and key[0] in ('stored_field', 'owned_storage')
                                    and key[1] == holder and key[2][:2] == path and len(key[2]) > 2):
                                active_loans[(key[0], alias, key[2][2:])] = list(loans)
                        steps.extend((f'frame->{member} = cell_load_ref({enum_cell}, {offset});',
                                      f'cell_store_ref({enum_cell}, {offset}, NULL);'))
                        continue
                    mode = 'mut' if (match.mutable or match.consuming) and (declared.startswith('&mut ') or owned) else 'ref'
                    target_type = declared[2:-1] if owned else pointee
                    references[alias] = mode
                    reference_types[alias] = target_type
                    if mode == 'mut':
                        mutable.add(alias)
                    path = (variant, field)
                    loans = (list(active_loans.get(('stored_field', holder, path),
                                                  initial_stored_field_loans(holder, path))) if match.consuming else
                             project_field_loans(held, path) if owned else
                             project_result_field_loans(held, enum_type, path))
                    received_refs[alias] = loans
                    active_loans[id(loans)] = loans
                    track_result(alias, loans, body, -1)
                    pointer = f'cell_load_ref({enum_cell}, {offset})'
                    if typed_reference:
                        pointer = f'cell_load_view({enum_cell}, {offset})'
                    elif target_type in struct_layouts:
                        pointer = f'structure_whole_view({pointer})'
                    steps.append(f'frame->{member} = ' +
                                 (f'&{pointer}->value' if target_type == 'Int' else pointer) + ';')
                if match.consuming:
                    drop_owned(holder, line)
            prefix_count = 0
            copied_fields = {}
            for statement in body:
                if statement.op != '->':
                    break
                name = statement.args[0]
                if (statement.move_import and name in fields and name not in references
                        and name not in arrays and inline_scalar_mode(name) in ('scalar', 'bool', 'byte', 'char')):
                    if name in copied_fields:
                        fail(statement.line, f"capture répétée de '{name}'")
                    check_access(name, statement.line)
                    member = fields[name]
                    snapshot = temporary(capture_type(inline_scalar_mode(name)))
                    steps.append(f'{snapshot} = frame->{member};')
                    copied_fields[name] = member, inline_binding_scopes[name]
                    fields[name] = snapshot.removeprefix('frame->')
                    inline_binding_scopes[name] = id(scopes[-1][0])
                else:
                    import_async_value(name, statement.line)
                prefix_count += 1
            if prefix_count:
                scopes[-1][0].update((name, None) for name in scopes[-2][0] if name in imports)
            body = body[prefix_count:]
            if join_payload:
                result, payload_field, status, result_loans, direct, result_carrier = join_payload
                success = (status == 0) == (index == 0)
                if not success:
                    clear_stored_fields(result)
                if (success and not payload_field and body and body[0].op == 'array_statement'
                        and body[0].args[0][0] == 'array_buffered_exchange_take'
                        and body[0].args[0][2] == ('int', 1)):
                    body = body[1:]
                binds_payload = body and body[0].op == 'var' and body[0].args[1][0] == 'utf8_value'
                discards_payload = binds_payload and body[0].discarded_pattern
                execution_loans = joined_execution_loans.get(result, ()) if payload_field == 'async_execution' else ()
                if execution_loans and not success:
                    active_loans.pop(id(execution_loans), None)
                if success and payload_field == 'async_execution' and not binds_payload:
                    if execution_loans:
                        fail(line, 'Ok doit recevoir le handle à dépendances')
                    handle, nominal = joined_execution_values[result]
                    steps.append(f'task_abandon_async({handle});')
                    record_execution_abandonment(handle, nominal)
                if result_loans is not None and (not success or (direct and not binds_payload)):
                    active_loans.pop(id(result_loans), None)
                binds_error = body and body[0].op == 'var' and body[0].args[1][0] == 'utf8_error'
                if binds_error:
                    if success:
                        fail(line, 'une erreur doit être extraite dans Err')
                    error_name = body[0].args[0]
                    member = declare(error_name, line)
                    runtime_error_bindings.add(error_name)
                    locals_in_arm.append(error_name)
                    steps.append(f'frame->{member} = (CrustRuntimeError){result}.status;')
                    body = body[1:]
                owned_payload = success and payload_field in ('allocation', 'nested', *OWNED_NESTED_PAYLOAD_MODES, 'optional_nested', *EXCHANGE_PAYLOAD_MODES, *OPTION_PAYLOAD_MODES)
                if owned_payload:
                    if not binds_payload or body[0].discarded_pattern or body[0].args[0] == '_':
                        fail(line, 'un motif _ ne peut pas écarter une allocation possédée')
                    if not has_future_value_use(body[0].args[0], body[1:]):
                        fail(line, f"résultat propriétaire '{body[0].args[0]}' sans usage explicite")
                if (not owned_payload and body and body[0].op == 'array_statement'
                        and body[0].args[0][0] == 'array_buffered_exchange_take'
                        and body[0].args[0][2] == ('int', -1)):
                    body = body[1:]
                if binds_payload or owned_payload:
                    if not payload_field or not success:
                        fail(line, 'seul Ok fournit un résultat')
                    payload = body[0].args[0] if binds_payload else f'\0allocation:{result}'
                    if binds_payload:
                        body = body[1:]
                    if payload_field == 'map_scalar':
                        _, typ, ctype, _ = matched_map_slots[result]
                        declare(payload, line)
                        locals_in_arm.append(payload)
                        record_inline_type(payload, 'Bool' if typ == 'bool' else typ)
                        saved = temporary(ctype)
                        steps.append(f'memcpy(&{saved}, &{result}.value, sizeof({saved}));')
                        steps.append(f'frame->{fields[payload]} = {saved};')
                    elif payload_field == 'map_slot':
                        table, typ, ctype, mode = matched_map_slots[result]
                        declare(payload, line)
                        locals_in_arm.append(payload)
                        slot_mode = mode
                        if typ.startswith('&'):
                            slot_mode = 'map_shared_ref_slot'
                        elif map_handle_element(typ):
                            slot_mode = 'map_owned_' + mode + '_slot'
                        references[payload] = slot_mode
                        reference_types[payload] = typ
                        loans = [(table, mode), *received_refs.get(table, ())]
                        received_refs[payload] = loans
                        active_loans[id(loans)] = loans
                        track_result(payload, loans, body, -1)
                        steps.append(f'frame->{fields[payload]} = ({ctype} *){result}.slot;')
                    elif payload_field == 'async_execution':
                        handle, typ = joined_execution_values[result]
                        if payload == '_' or discards_payload:
                            if execution_loans:
                                fail(line, 'Ok doit recevoir le handle à dépendances')
                            steps.append(f'task_abandon_async({handle});')
                            record_execution_abandonment(handle, typ)
                        else:
                            check_new_name(payload, line)
                            blocking_executions.add(handle)
                            signature = public_async_signature(typ, aggregate_layouts, allow_borrowed=True)
                            loans = execution_loans or []
                            active_loans[id(loans)] = loans
                            output = inner_handle_output_loans(handle, signature, loans)
                            changes = task_handle_field_changes.get(handle, ())
                            executions[payload] = handle, signature == ('scalar', 'Int'), loans, typ, output, changes
                            scopes[-1][0][payload] = None
                    elif isinstance(payload_field, tuple):
                        source, shape, element = payload_field
                        member = declare(payload, line)
                        arrays[payload] = shape
                        array_elements[payload] = element
                        scopes[-1][0][payload] = None
                        locals_in_arm.append(payload)
                        if all(shape):
                            steps.append(f'memcpy(frame->{member}, {source}, sizeof frame->{member});')
                    elif payload_field in ('nested', *OWNED_NESTED_PAYLOAD_MODES, 'optional_nested', *EXCHANGE_PAYLOAD_MODES, *OPTION_PAYLOAD_MODES):
                        check_new_name(payload, line)
                        if payload_field in OWNED_NESTED_PAYLOAD_MODES:
                            inner_mode = owned_inner_mode(OWNED_NESTED_PAYLOAD_MODES[payload_field])
                            inner_ctype = OWNED_JOIN_CTYPES[inner_mode]
                            inner_payload = OWNED_JOIN_PAYLOADS[inner_mode]
                            cell = OWNED_JOIN_CELLS[inner_mode]
                        elif payload_field in OPTION_PAYLOAD_MODES:
                            inner_mode, inner_type = option_inner_signature(OPTION_PAYLOAD_MODES[payload_field])
                            inner_ctype = OWNED_WRAPPER_TYPES[inner_mode]
                            inner_payload = owned_wrapper_payload(inner_mode, inner_type)
                            cell = JOIN_CELLS[inner_mode]
                        elif payload_field in EXCHANGE_PAYLOAD_MODES:
                            inner_mode, inner_type = exchange_inner_signature(EXCHANGE_PAYLOAD_MODES[payload_field])
                            inner_ctype = OWNED_WRAPPER_TYPES[inner_mode]
                            inner_payload = owned_wrapper_payload(inner_mode, inner_type)
                            cell = JOIN_CELLS[inner_mode]
                        else:
                            inner_ctype = 'CrustJoinResult'
                            inner_payload = 'allocation'
                            cell = 'allocation'
                        inner = temporary(inner_ctype)
                        steps.extend((f'{inner} = {result}.value;', f'{result}.value.{cell} = NULL;'))
                        join_results[payload] = inner, inner_payload, None
                        owned_result_types[inner] = owned_result_types.get(result, 'Int')
                        keep_storage(inner, storage_of(result))
                        move_stored_fields(result, inner)
                        scopes[-1][0][payload] = None
                    else:
                        declare(payload, line)
                        locals_in_arm.append(payload)
                        field = payload_field
                        if isinstance(payload_field, str) and payload_field.startswith('plain:'):
                            inner_mode = payload_field[len('plain:'):]
                            if not has_future_value_use(payload, body):
                                fail(line, f"résultat faillible '{payload}' sans usage explicite")
                            record_inline_type(payload, PLAIN_JOIN_TYPES[inner_mode])
                            field = 'value'
                        elif payload_field == 'bool_value':
                            boolean_bindings.add(payload)
                        elif payload_field in NUMERIC_JOIN_FIELDS.values():
                            mode = next(mode.removeprefix('join_') for mode, field in NUMERIC_JOIN_FIELDS.items()
                                        if field == payload_field)
                            record_inline_type(payload, EXTRA_MODES[mode])
                        elif payload_field == 'byte_value':
                            byte_bindings.add(payload)
                        elif payload_field.endswith('_value') and payload_field[:-6] in ERROR_VALUE_TYPES:
                            builtin_error_bindings[payload] = payload_field[:-6]
                        elif payload_field == 'runtime_error_value':
                            runtime_error_bindings.add(payload)
                        elif payload_field == 'char_value':
                            char_bindings.add(payload)
                        elif payload_field == 'text_value':
                            text_bindings.add(payload)
                        elif payload_field == 'byte_ref_value':
                            byte_ref_bindings.add(payload)
                        elif payload_field in ASYNC_VIEW_FIELDS and payload_field not in ('text', 'byte_ref'):
                            record_inline_type(payload, SCALAR_TYPES[payload_field])
                            field = ASYNC_VIEW_FIELDS[payload_field]
                        elif payload_field in UTF8_VALUE_RESULT_FAMILIES:
                            if VALUE_MODES[payload_field].startswith('Result<') and not has_future_value_use(payload, body):
                                fail(line, f"résultat faillible '{payload}' sans usage explicite")
                            wrapped_utf8_bindings[payload] = UTF8_VALUE_RESULT_FAMILIES[payload_field]
                            field = UTF8_VALUE_RESULT_FIELDS[payload_field]
                        steps.append(f'frame->{fields[payload]} = {result}.{field};')
                        if owned_payload:
                            references[payload] = 'owned'
                            payload_type = owned_result_types.get(result, 'Int')
                            storage_bindings[payload] = storage_of(result)
                            move_stored_fields(result, payload)
                            if payload_type in reference_structs:
                                reference_types[payload] = payload_type
                            if payload_type != 'Int':
                                collection_types[payload] = payload_type
                            scopes[-1][0][payload] = None
                            steps.append(f'{result}.{payload_field} = NULL;')
                        elif result_loans is not None and payload_field in (
                                'text_value', 'byte_ref_value', 'slice_result', *VECTOR_SLICE_ELEMENTS, *SHARED_VECTOR_SLICE_MODES):
                            if direct:
                                active_loans.pop(id(result_loans), None)
                            payload_loans = list(result_loans)
                            utf8_view_loans[payload] = tuple(payload_loans)
                            active_loans[id(payload_loans)] = payload_loans
                            track_result(payload, payload_loans, body, -1)
                        elif result_loans is not None:
                            if direct:
                                active_loans.pop(id(result_loans), None)
                            payload_loans = list(result_loans)
                            mode, target_type = NUMERIC_REFERENCE_SIGNATURES.get(payload_field, (
                                'mut' if payload_field in ('mutable_reference', 'mutable_byte_reference', 'mutable_structure_reference') else 'ref',
                                awaited_reference_types.get(result, 'u8' if payload_field == 'mutable_byte_reference' else 'Int')))
                            if result_carrier is not None:
                                payload_loans.append((result_carrier, mode))
                            references[payload], reference_types[payload] = mode, target_type
                            if references[payload] == 'mut':
                                mutable.add(payload)
                            received_refs[payload] = payload_loans
                            active_loans[id(payload_loans)] = payload_loans
                            track_result(payload, payload_loans, body, -1)
            # The parser treats a trailing if/block as a yielded expression.
            # If every path exits, emit it as control flow: it provides no
            # value to this arm's receiver, but still exits the same loop.
            if body and body[-1].op == 'if_yield' and branch_control_exit(body):
                value = body[-1].args[0]
                if value[0] == 'if_expr':
                    body = [*body[:-1], replace(body[-1], op='if', args=value[1:])]
                elif value[0] == 'scope':
                    body = [*body[:-1], replace(body[-1], op='scope', args=value[1:3],
                                               region_limit=value[3] if len(value) > 3 else None)]
            try:
                terminal = body[-1] if body and (body[-1].op in ('return', 'if_yield')
                                                 or ((transfer_result or export_name is not None) and ends_in_transfer(body))) else None
                returned_in_branch = False
                statements = iter(enumerate(body[:-1] if terminal is not None else body))
                for position, statement in statements:
                    statement_tails[len(scopes) - 1] = body[position + 1:]
                    release_results(local_refs, before=position)
                    release_statement_loans(body[position:], utf8_only=True)
                    if returned_in_branch:
                        fail(statement.line, 'instruction après retour async')
                    if statement.op == '->':
                        fail(statement.line, '-> est autorisé uniquement à l’entrée du bloc async')
                    if statement.op == '<-' and statement.terminated:
                        name = statement.args[0]
                        if name not in scopes[-1][0]:
                            fail(statement.line, '<- exige une tâche ou un handle du bloc courant')
                        if references.get(name) == 'owned' or name in arrays:
                            if name in consumed:
                                fail(statement.line, f"'{name}' déjà consommé")
                        elif async_binding_values(name).get(name) is None:
                            fail(statement.line, f"'{name}' déjà consommé")
                        if name in returned_imports:
                            fail(statement.line, 'transfert déjà marqué')
                        if name in imports:
                            returned_imports.add(name)
                        else:
                            warn(statement.line, 'transfert sans receveur', name)
                    elif statement.op == 'yield':
                        suspend()
                    elif statement.op in ('break', 'continue'):
                        loop_exit(statement.op, statement.args[0], statement.line)
                        returned_in_branch = True
                    elif statement.op in ('loop', 'while'):
                        returned_in_branch = emit_loop(statement.args[0], statement.line, following=body[position + 1:])
                    elif statement.op == 'scope':
                        returned_in_branch = emit_block(statement, body[position + 1:])
                    elif statement.op == 'if':
                        returned_in_branch = conditional(*statement.args, statement.line, valued=False,
                                                         following=body[position + 1:])
                    elif statement.op == 'match':
                        returned_in_branch = match_enum(statement, valued=False, following=body[position + 1:])
                    elif statement.op == 'assign':
                        assign(*statement.args, statement.line, following=body[position + 1:])
                    elif statement.op == 'field_store':
                        store_struct_field(*statement.args, statement.line, following=body[position + 1:])
                    elif statement.op in ('array_store', 'array_deref_store'):
                        store_array(*statement.args, statement.line, following=body[position + 1:])
                    elif statement.op == 'array_statement' and statement.args[0][0] == 'array_numeric_compound':
                        numeric_compound_store(statement.args[0], statement.line, following=body[position + 1:])
                    elif statement.op == 'array_statement' and statement.args[0][0] == 'array_swap':
                        swap_array(statement.args[0], statement.line, following=body[position + 1:])
                    elif set_reference(statement, body[position + 1:]):
                        pass
                    elif drop_async_binding(statement):
                        pass
                    elif statement.op == 'await_statement':
                        await_task(statement.args[0], statement.line, returns_value=False)
                    elif statement.op in ('print', 'print_expr'):
                        emit_print(statement, body[position + 1:])
                    elif statement.op == 'var' and statement.utf8_match_subject:
                        returned_in_branch = match_statement(statement, (item for _, item in statements),
                                                             following=body[position + 3:])
                    elif statement.op == 'var':
                        check_noncontinuing_initializer(statement, body[position + 1:])
                        if bind_array(statement, following=body[position + 1:]):
                            locals_in_arm.append(statement.args[0])
                            continue
                        if receive_await_result(statement, body, position, export_name=export_name):
                            if statement.args[0] in fields:
                                locals_in_arm.append(statement.args[0])
                            continue
                        if bind_special(statement, body, position, export_name=export_name):
                            if statement.args[0] in fields:
                                locals_in_arm.append(statement.args[0])
                            continue
                        bind_scalar(statement, body[position + 1:], body, position)
                        locals_in_arm.append(statement.args[0])
                    else:
                        fail(statement.line, f'branche de {construct} async : instruction {statement.op} non prise en charge')
                release_results(local_refs, before=len(body) - 1)
                if returned_in_branch:
                    if terminal is not None:
                        fail(terminal.line, 'instruction après retour async')
                elif terminal is not None and terminal.op == 'return':
                    emit_return(terminal.args[0], terminal.line)
                else:
                    if valued and not transfer_result and terminal is None and arm_value is None:
                        fail(line, f'branche de {construct} async : résultat Int ou retour requis')
                    if transfer_result:
                        if terminal is None or terminal.op != '<-':
                            fail(line, 'chaque branche continuante doit transférer une valeur avec <-')
                        name = terminal.args[0]
                        require_local_async_value(name, terminal.line)
                        kind, record = export_async_value(name, locals_in_arm, terminal.line, depth=len(scopes) - 1)
                        if kind == 'owned':
                            result, signature, ctype = record, (kind, owned_result_types.get(record, 'Int')), 'Cell *'
                        elif kind == 'array':
                            result, shape, ctype = record
                            signature = kind, shape, ctype
                        elif kind in OWNED_WRAPPER_TYPES:
                            result, payload, _ = record
                            signature = kind, payload, owned_result_types.get(result, 'Int')
                            ctype = OWNED_WRAPPER_TYPES[kind]
                        elif kind == 'selection':
                            result, ctype = f'&{record.c}', 'CrustSelect *'
                            signature = kind, record.awaited, task_result_signature(record.branches[0])
                            active_loans.pop(id(record.loans), None)
                            selected_loans.extend(record.loans)
                            selected_branches.extend(record.branches)
                            selected_paths.extend(record.paths or (record.branches,))
                        else:
                            result, child_returns_int, loans, nominal, returned_loans, field_changes = record
                            if kind == 'task':
                                selected_task_prefixes.extend(task_prefix_changes.get(result, ((None, (), ()),)))
                            if kind == 'execution':
                                selected_executions_autonomous &= autonomous_execution(record)
                                selected_execution_origins.update(execution_pools.get(result, (nominal,)))
                                selected_handle_kinds.add(result in blocking_executions)
                                if len(selected_handle_kinds) > 1:
                                    fail(terminal.line, 'les branches exigent le même type de handle')
                            signature = kind, child_returns_int, nominal
                            ctype = 'CrustTask *' if kind == 'task' else 'CrustAsyncExecution *'
                            del active_loans[id(loans)]
                            selected_loans.extend(loans)
                            selected_returned_loans.extend(returned_loans)
                            selected_field_changes.extend(field_changes)
                            if kind in ('task', 'execution') and task_result_signature(record)[2] is not None:
                                local = task_result_signature(record)[2]
                                selected_execution_storage.add(local)
                                if len(selected_execution_storage) > 1:
                                    fail(terminal.line, 'branches de tâches ou handles : stockage incompatible (T local / allocation A<T>)')
                            if kind in ('task', 'execution') and functions[nominal].args[2][0] == 'async_execution':
                                selected_returned_handle_pools.update(known_handle_result_pools(result, nominal))
                                selected_returned_handle_output_loans.extend(task_output_projection(record))
                                selected_returned_handle_changes.extend(task_handle_field_changes.get(result, ((),)))
                        if selected_signature is None:
                            selected_signature = signature
                            target = temporary(ctype, array_dimensions(shape) if kind == 'array' else '')
                        elif signature != selected_signature:
                            from handle_types import common_public_handle
                            common = (common_public_handle((selected_signature[2], signature[2]), functions,
                                      storage='local' if selected_execution_storage == {True} else 'pool')
                                      if kind == selected_signature[0] == 'execution'
                                      and signature[1] == selected_signature[1] else None)
                            if common is None:
                                fail(terminal.line, 'même type et même mode requis dans toutes les branches async')
                            selected_signature = kind, child_returns_int, common
                        if kind != 'array':
                            if kind in ('owned', *OWNED_WRAPPER_TYPES):
                                keep_storage(target, storage_of(result))
                            if kind in ('owned', *OWNED_WRAPPER_TYPES, 'task', 'execution'):
                                move_stored_fields(result, target)
                            steps.append(f'{target} = {result};')
                        elif all(shape):
                            steps.append(f'memcpy({target}, {result}, sizeof {target});')
                    elif valued:
                        item = terminal.args[0] if arm_value is None else arm_value
                        item_line = terminal.line if arm_value is None else line
                        if reference_result:
                            value, loans, signature = reference_value(item, item_line, following=())
                            selected_reference_loans.extend(surviving_reference_loans(loans, len(scopes) - 1, item_line))
                            active_loans.pop(id(loans), None)
                            if reference_signature is not None and signature != reference_signature:
                                fail(item_line, 'branches empruntées : même type et même mode requis')
                            if reference_signature is None:
                                target = temporary(capture_type(*signature))
                            reference_signature = signature
                        elif boolean is None:
                            value, typ = infer_scalar_value(item, item_line, following=())
                            if typ in ASYNC_VIEW_TYPES:
                                loans = local_utf8_loans(item, value)
                                selected_utf8_loans.extend(surviving_view_loans(loans, len(scopes) - 1, item_line))
                            if scalar_type is not None and typ != scalar_type:
                                fail(item_line, f'branches de {construct} async : même type scalaire requis')
                            if scalar_type is None:
                                target = temporary(capture_type(SCALAR_MODES[typ]))
                            scalar_type = typ
                        else:
                            evaluate = boolean_value if boolean else expression
                            value = evaluate(item, item_line)
                        steps.append(f'{target} = {value};')
                    if export_name is not None:
                        exported = export_async_value(export_name, locals_in_arm, line, depth=len(scopes) - 1)
                    release_results(local_refs)
                    if join_payload and result_loans is not None:
                        if direct:
                            active_loans.pop(id(result_loans), None)
                        elif had_result_loan:
                            active_loans[id(result_loans)] = result_loans
                    if following is not None and no is not None:
                        # Compare only the loans that can survive the branch.
                        release_statement_loans(())
                    release_statement_loans((), utf8_only=True)
                    cleanup_scope(len(scopes) - 1, line)
                    continuing.append(control_state(len(scopes) - 1))
            except NoAsyncContinuation:
                # All paths already emitted their exit and cleanup. Do not
                # evaluate a receiver or generate its unreachable suffix.
                pass
            statement_tails.pop(len(scopes) - 1, None)
            scopes.pop()
            for name, (member, owner) in copied_fields.items():
                fields[name] = member
                inline_binding_scopes[name] = owner
            for name in locals_in_arm:
                # Frame members remain declared, but the names are arm-local.
                ctype = capture_type(references.pop(name, inline_scalar_mode(name)), reference_types.pop(name, collection_types.get(name)))
                member = fields.pop(name)
                shape = arrays.pop(name, ())
                ctype = array_elements.pop(name, ctype)
                if member not in fields.values():
                    internal_members.append(f'    {ctype} {member}{array_dimensions(shape)};\n')
                received_refs.pop(name, None)
                mutable.discard(name)
                boolean_bindings.discard(name)
                byte_bindings.discard(name)
                runtime_error_bindings.discard(name)
                builtin_error_bindings.pop(name, None)
                numeric_bindings.pop(name, None)
                if name in plain_join_bindings:
                    plain_join_bindings.pop(name)
                    join_results.pop(name, None)
                char_bindings.discard(name)
                text_bindings.discard(name)
                byte_ref_bindings.discard(name)
                slice_bindings.pop(name, None)
                mutable_slices.discard(name)
                static_utf8_bindings.discard(name)
                wrapped_utf8_bindings.pop(name, None)
                inline_binding_scopes.pop(name, None)
                collection_types.pop(name, None)
                pool_types.pop(name, None)
                local_pools.pop(name, None)
                pool_alias_origins.pop(name, None)
                storage_bindings.pop(name, None)
                utf8_view_loans.pop(name, None)
                mutable_utf8_bindings.discard(name)
            if index + 1 < len(arms):
                if enum_match or (map_match and index + 2 < len(arms)):
                    steps.append(f'}} else if ({test} == {tags[index + 1]}) {{')
                else:
                    steps.append('} else {')
                restore_control_state(before)
            else:
                steps.append('}')
        if following is not None:
            lexical_tails.pop()
        while len(continuing) > 1:
            other = continuing.pop()
            if continuing[0] == other:
                continue
            if construct == 'boucle':
                verify_utf8_backedge(loops[-1], continuing[0], line)
            continuing[0] = merge_utf8_control_states(
                continuing[0], other, line,
                f'les branches de {construct} async doivent conserver les mêmes obligations de nettoyage')
        if continuing:
            if construct == 'boucle':
                loops[-1]['has_backedge'] = True
            restore_control_state(continuing[0])
        if valued and not continuing:
            raise NoAsyncContinuation
        if export_name is not None:
            if exported is None:
                fail(line, 'bloc async sans sortie qui fournit le transfert')
            return exported
        if transfer_result:
            kind = selected_signature[0]
            if kind == 'owned':
                owned_result_types[target] = selected_signature[1]
                return kind, target
            if kind == 'array':
                return kind, (target, *selected_signature[1:])
            if kind in OWNED_WRAPPER_TYPES:
                owned_result_types[target] = selected_signature[2]
                return kind, (target, selected_signature[1], None)
            _, child_returns_int, nominal = selected_signature
            loans = list(dict.fromkeys(selected_loans))
            active_loans[id(loans)] = loans
            if kind == 'selection':
                return kind, SelectionState(f'(*{target})', tuple(selected_branches), loans, child_returns_int,
                                            tuple(selected_paths))
            if kind == 'task':
                task_prefix_changes[target] = tuple(selected_task_prefixes)
            if selected_returned_handle_pools:
                task_handle_result_pools[target] = frozenset(selected_returned_handle_pools)
            if selected_returned_handle_output_loans:
                task_handle_output_loans[target] = tuple(dict.fromkeys(selected_returned_handle_output_loans))
            if any(selected_returned_handle_changes):
                task_handle_field_changes[target] = tuple(dict.fromkeys(selected_returned_handle_changes))
            if kind == 'execution' and selected_executions_autonomous:
                execution_pools[target] = frozenset(selected_execution_origins)
            if kind == 'execution' and selected_handle_kinds == {True}:
                blocking_executions.add(target)
            return kind, (target, child_returns_int, loans, nominal, list(dict.fromkeys(selected_returned_loans)), tuple(selected_field_changes))
        if reference_result:
            loans = list(dict.fromkeys(selected_reference_loans))
            active_loans[id(loans)] = loans
            return target, loans, reference_signature
        if valued and boolean is None:
            if scalar_type in ASYNC_VIEW_TYPES:
                utf8_result_loans[target] = tuple(dict.fromkeys(selected_utf8_loans))
            return target, scalar_type
        return target if valued else not continuing

    def export_async_value(name, local_names, line, *, names=None, depth=None):
        names = scopes[-1][0] if names is None else names
        if name in names and name in arrays:
            check_access(name, line, write=True)
            consumed.add(name)
            return 'array', (f'frame->{fields[name]}', arrays[name], array_elements[name])
        if name in names and references.get(name) == 'owned':
            if depth is None:
                check_result_lock_transfer(name, line)
            check_access(name, line, write=True)
            member = f'frame->{fields[name]}'
            result = temporary('Cell *')
            keep_storage(result, storage_bindings.get(name, ()))
            move_stored_fields(name, result)
            if depth is not None:
                require_durable_storage(result, depth, line, local_receiver=True)
            owned_result_types[result] = collection_types.get(name, 'Int')
            steps.extend((f'{result} = {member};', f'{member} = NULL;'))
            consumed.add(name)
            storage_bindings.pop(name, None)
            return 'owned', result
        if name in executions and name in names:
            kind, value = 'execution', consume_execution(name, line)
        elif name in names and is_owned_join(name, nested=True):
            if depth is not None:
                require_durable_storage(join_results[name][0], depth, line)
            record = consume_owned_join(name, line)
            return next(kind for kind, payload in OWNED_WRAPPER_PAYLOADS.items() if payload == record[1]), record
        elif name in tasks and name in names:
            kind, value = 'task', consume_task(name, line)
        elif name in selections and name in names:
            kind, value = 'selection', selections[name]
            if value is None:
                fail(line, f"Select '{name}' déjà consommé")
            selections[name] = None
        else:
            fail(line, '<- exige une tâche ou un handle déclaré dans le bloc async')
        moving = set()
        if depth is not None:
            local_names = set(local_names)
            for attached, _, returning, *_ in scopes[depth:]:
                local_names.update(attached.keys() - returning)
                moving.update(returning)
        departing = (mutable_slices | pool_alias_origins.keys()).intersection(local_names)
        departing.update(name for name in local_names if name in received_refs)
        if kind == 'selection':
            loans = value.loans
        else:
            task, returns_int, loans, nominal, returned_loans, field_changes = value
        if any(loan_root(target) in local_names and loan_root(target) not in departing for target, _ in loans):
            fail(line, 'transfert refusé : cible empruntée non durable dans le scope parent')
        if any(loan_root(target) in moving for target, _ in loans):
            fail(line, 'transfert de la cible interdit pendant un emprunt actif')
        if departing:
            retained = [loan for loan in loans if loan_root(loan[0]) not in departing]
            del active_loans[id(loans)]
            active_loans[id(retained)] = retained
            if kind == 'selection':
                def retain_targets(record):
                    return (*record[:4],
                        [loan for loan in record[4] if loan_root(loan[0]) not in departing], record[5])
                branches = tuple(retain_targets(record) for record in value.branches)
                paths = tuple(tuple(retain_targets(record) for record in path) for path in value.paths)
                value = replace(value, loans=retained, branches=branches, paths=paths)
            else:
                returned_loans = [loan for loan in returned_loans if loan_root(loan[0]) not in departing]
                value = task, returns_int, retained, nominal, returned_loans, field_changes
        return kind, value

    def match_statement(statement, statements, *, following=None):
        tail = tuple(next(statements, None) for _ in range(2))
        if None in tail:
            fail(statement.line, 'match async incomplet')
        return match_async_result((statement, *tail), statement.line, valued=False, following=following)

    def discard_pending(line):
        # A guard leaves its lexical scope when the body returns. Holding its
        # lock until the result is collected could block another task's join.
        for _, _, _, _, local_refs in scopes:
            release_results(local_refs)
        for names, *_ in reversed(scopes):
            for name in reversed(names):
                if (references.get(name) == 'owned' and name not in consumed
                        and mutex_payload(collection_types.get(name), GUARD_TYPES)):
                    drop_owned(name, line)
        # The remaining state is released after result extraction.
        start = len(steps)
        cleanup_prepared_captures()
        for names, _, _, _, _ in reversed(scopes):
            cleanup_async_values(names, (), line)
        path = tuple(steps[start:])
        del steps[start:]
        if path not in cleanup_paths:
            cleanup_paths.append(path)
        steps.append(f'frame->cleanup_path = {cleanup_paths.index(path) + 1};')

    def check_utf8_return_sources(expr, evaluated, line):
        for target, _ in local_utf8_loans(expr, evaluated):
            root = loan_root(target)
            if root in mutable_slices or root in received_refs:
                continue  # The loan set also contains the underlying storage.
            mode = parameter_modes.get(root)
            borrowed_collection = mode in ('ref', 'mut') and collection_types.get(root) in ('String', *VECTOR_SLICE_MODES)
            borrowed_bytes = mode in ARRAY_BORROWS and array_elements.get(root) == 'uint8_t'
            borrowed_byte = mode == 'mut' and reference_types.get(root) == 'u8'
            if not (borrowed_collection or borrowed_bytes or borrowed_byte):
                fail(line, 'retour de vue issue d’une collection du cadre non durable chez l’appelant')

    def emit_return(value, line):
        if returns_value != (value is not None):
            fail(line, 'retour async incompatible avec la signature')
        if returns_execution:
            if value[0] in ('transfer', 'array_transfer'):
                value = value[1]
            if value[0] in ('name', 'move') and value[1] in executions:
                require_local_async_value(value[1], line)
                record = consume_execution(value[1], line)
            elif value[0] == 'task_spawn':
                record = spawn_task(value[1], line, blocking=value[2:] == ('blocking',),
                                    native=value[2:] == ('native',))
            elif value[0] == 'await':
                record = await_task(value, line, returns_value=True, execution=True)
            else:
                kind, record = emit_computed_transfer(value, line)
                if kind != 'execution':
                    fail(line, 'retour AsyncHandle : handle d’exécution requis')
            if public_execution_type(record, result[1], line) != result[1]:
                fail(line, 'retour AsyncHandle : type de handle incompatible')
            if not autonomous_execution(record):
                capture_indexes = {name: index for index, (name, mode, _) in enumerate(parameters)
                                   if mode in ('ref', 'mut')}
                if (not record[2]
                        or any(access not in ('ref', 'mut') or loan_root(target) not in capture_indexes
                               for target, access in (*record[2], *record[4]))):
                    fail(line, 'retour AsyncHandle : emprunts de paramètres directs requis')
                for path in record[5]:
                    for key, _ in path:
                        summary = node.field_effect_summary
                        category, holder, path = key
                        vector_items = (category == 'owned_storage' and path[-1:] == ('items',)
                                        and is_handle_vector(projected_type(
                                            reference_types.get(holder, collection_types.get(holder)), path[:-1])))
                        supported = (summary and (vector_items and summary.returned_handle_vector_updates
                            or path[:1] == ('map_items',) and any(summary.returned_handle_map_paths)
                            or key[0] == 'guarded_field' and summary.returned_handle_guarded_writes
                            or key[0] == 'stored_field' and key[2][:1] != ('map_items',)
                            and (summary.returned_handle_fields or summary.returned_handle_owned_writes)
                            or key[0] == 'owned_storage' and key[2][:1] != ('map_items',)
                            and summary.returned_handle_owned_writes))
                        if not supported:
                            fail(line, 'retour AsyncHandle : écriture différée sans contrat de champ')
                returned_handle_borrows.update(
                    capture_indexes[loan_root(target)] for target, _ in (*record[2], *record[4]))
                returned_handle_output_borrows.update(capture_indexes[loan_root(target)] for target, _ in record[4])
            active_loans.pop(id(record[2]), None)
            origins = execution_pools.get(record[0], (record[3],))
            returned_handle_pools.update(origin for origin in origins
                                         if isinstance(origin, int) or origin in functions)
            task_activity.update(('abandoned', pool) for pool in origins if pool in functions)
            steps.extend((f'frame->result = *({record[0]});',
                          f'*({record[0]}) = (CrustAsyncExecution){{0}};',
                          'frame->result_ready = 1;'))
        elif returns_array:
            if value[0] == 'move' and value[1] in arrays:
                require_local_async_value(value[1], line)
                _, (source, shape, element) = export_async_value(value[1], (), line)
                if (shape, element) != (returns_array, array_result_ctype):
                    fail(line, 'retour de tableau : dimensions incompatibles')
                if all(shape):
                    steps.append(f'memcpy(frame->result, {source}, sizeof frame->result);')
            elif value[0] == 'array_transfer' and value[1][0] == 'array_copy':
                source, _ = array_element(value[1][1], line, remaining=returns_array,
                                          expected_element=array_result_ctype)
                if all(returns_array):
                    steps.append(f'memcpy(frame->result, {source}, sizeof frame->result);')
            elif value[0] == 'array_transfer' and value[1][0] in ('array_literal', 'array_repeat'):
                shape, plan, _ = layout_array(value[1], returns_array, line, array_result_ctype)
                if shape != returns_array:
                    fail(line, 'retour de tableau : dimensions incompatibles')
                initialize_array('frame->result', plan)
            else:
                fail(line, 'retour de tableau : transfert explicite <- requis')
        elif returns_join:
            if value[0] in ('array_transfer', 'new_transfer', 'move', 'array_handle_option_pop', 'array_buffered_replace', 'array_buffered_try_push'):
                joined, payload, _ = owned_join_value(
                    value if value[0] in ('move', 'array_handle_option_pop', 'array_buffered_replace', 'array_buffered_try_push') else value[1], line, following=())
            else:
                fail(line, 'retour de Result alloué : <- explicite requis')
            require_durable_storage(joined, 0, line)
            if node.join_storage_result and any((source in implicit_stacks) != (node.join_storage_result == 'local')
                                               for source in storage_of(joined)):
                fail(line, f'retour Result : stockage {node.join_storage_result} requis (T local / allocation A<T>)')
            if (payload != owned_wrapper_payload(*result)
                    or owned_result_types.get(joined, 'Int') != wrapper_content_type(*result)):
                fail(line, 'retour de Result alloué : type de Result incompatible')
            steps.extend((f'frame->result = {joined};', f'{joined}.{JOIN_CELLS[join_return_mode]} = NULL;'))
        elif returns_owned:
            if value[0] in ('array_transfer', 'new_transfer'):
                received = sync_owned_value(value[1], line, following=())
                publish_returned_result_lock(received, line)
                require_durable_storage(received, 0, line)
                if node.handle_result and storage_of(received) & implicit_stacks:
                    fail(line, 'retour A<T> : une structure locale T ne peut pas remplacer une allocation de pool')
                if owned_result_types[received] != result[1]:
                    fail(line, 'retour propriétaire : type incompatible')
                steps.extend((f'frame->result = {received};', f'{received} = NULL;'))
                discard_pending(line)
                steps.append('return TASK_STEP_RETURN;')
                return
            if (value[0] != 'move' or references.get(value[1]) != 'owned'
                    or collection_types.get(value[1], 'Int') != result[1]):
                fail(line, f'retour async <- {result[1]} : transfert explicite du type déclaré requis')
            name = value[1]
            check_access(name, line, write=True)
            member = f'frame->{fields[name]}'
            publish_returned_result_lock(name, line)
            require_durable_storage(member, 0, line)
            if node.handle_result and storage_of(member) & implicit_stacks:
                fail(line, 'retour A<T> : une structure locale T ne peut pas remplacer une allocation de pool')
            steps.extend((f'frame->result = {member};', f'{member} = NULL;'))
            consumed.add(name)
        elif returns_ref:
            if value[0] in ('name', 'ref', 'mut', 'reborrow') and value[1] in collection_types:
                fail(line, 'retour emprunté Int incompatible avec une collection')
            if value[0] in ('if_expr', 'scope', 'value_match', 'match_expr', 'loop_expr') or sync_signature(value) in reference_sync_types:
                pointer, _, signature = reference_value(value, line, following=())
                if signature != result:
                    fail(line, 'retour emprunté async : type ou mode incompatible')
            elif push_new_receiver(value) is not None:
                pointer, _, element = vector_push_new_value(value, line, following=())
                if result != ('mut', element):
                    fail(line, 'retour push_new : type incompatible')
            elif value[0] == 'await':
                if await_signature(value) not in (None, result):
                    fail(line, 'retour emprunté async : type incompatible')
                pointer, _, _ = await_task(value, line, returns_value=True, borrow=True)
            elif field_reference_shape(value) is not None:
                pointer, _, signature = reference_value(value, line, following=())
                if signature != result:
                    fail(line, 'retour emprunté async : type ou mode incompatible')
            elif value[0] in ('ref_expr', 'mut_expr'):
                pointer, _ = capture_array_place(value[1], result[0], line, expected_element=FIELD_C_TYPES.get(result[1], 'int'))
            else:
                if value[0] not in ('name', 'reborrow') or references.get(value[1]) not in ('ref', 'mut'):
                    fail(line, 'retour emprunté async : référence requise, pas un Result')
                check_access(value[1], line)
                if reference_types.get(value[1], 'Int') != result[1]:
                    fail(line, 'retour emprunté async : type incompatible')
                if result[0] == 'mut' and (references[value[1]] != 'mut' or value[0] == 'reborrow' and value[2] != 'mut'):
                    fail(line, 'retour emprunté async : un emprunt mutable est requis')
                pointer = f'frame->{fields[value[1]]}'
            steps.append(f'frame->result = {pointer};')
        elif returns_int:
            steps.append(f'frame->result = {expression(value, line, following=())};')
        elif returns_bool:
            steps.append(f'frame->result = {boolean_value(value, line, following=())};')
        elif returns_byte:
            steps.append(f'frame->result = {byte_value(value, line, following=())};')
        elif result[0] in EXTRA_MODES:
            number, typ = infer_scalar_value(value, line, following=())
            if typ != result[1]:
                fail(line, f'retour async : attendu {result[1]}')
            steps.append(f'frame->result = {number};')
        elif result[0] in PLAIN_JOIN_TYPES:
            steps.append(f'frame->result = {plain_join_value(value, result[0], line, following=())};')
        elif result[0] in ERROR_VALUE_TYPES:
            steps.append(f'frame->result = {builtin_error_value(value, result[0], line, following=())};')
        elif result[0] == 'runtime_error':
            steps.append(f'frame->result = {runtime_error_value(value, line, following=())};')
        elif returns_char:
            converted = char_value(value, line, context='un retour char', following=())
            steps.append(f'frame->result = {converted};')
        elif returns_text:
            view = static_text_value(value, line, following=())
            check_utf8_return_sources(value, view, line)
            steps.append(f'frame->result = {view};')
        elif returns_byte_ref:
            pointer = static_byte_ref_value(value, line, following=())
            check_utf8_return_sources(value, pointer, line)
            steps.append(f'frame->result = {pointer};')
        elif result[0] in VECTOR_SLICE_ELEMENTS:
            view = vector_view_value(value, line, result[0], following=())
            check_utf8_return_sources(value, view, line)
            steps.append(f'frame->result = {view};')
        elif result[0] in SHARED_VECTOR_SLICE_MODES:
            view = mutable_slice_value(value, line, result[0], following=())
            check_utf8_return_sources(value, view, line)
            steps.append(f'frame->result = {view};')
        elif returns_wrapped_utf8:
            decoded, typ = infer_scalar_value(value, line, following=())
            if typ != result[1]:
                fail(line, f'retour UTF-8 : attendu {result[1]}')
            if result[0] == 'slice_result':
                check_utf8_return_sources(value, decoded, line)
            steps.append(f'frame->result = {decoded};')
        discard_pending(line)
        steps.append('return TASK_STEP_RETURN;')

    def loan_root(target):
        return target[0] if isinstance(target, tuple) else target

    def check_access(name, line, *, write=False, path=()):
        if name in consumed:
            fail(line, f"'{name}' n’est plus utilisable après drop ou transfert")
        if any(loan_root(target) == name and mode not in ('storage', 'shared_target', 'stored_mut_target') and (mode == 'mut' or write)
               and (not isinstance(target, tuple)
                    or all(left is None or right is None or left == right for left, right in zip(path, target[1])))
               for loans in active_loans.values() for target, mode in loans):
            fail(line, f"accès à '{name}' incompatible avec un emprunt actif")

    def drop_owned(name, line):
        check_access(name, line, write=True)
        consumed.add(name)
        clear_stored_fields(name)
        storage_bindings.pop(name, None)
        member = f'frame->{fields[name]}'
        steps.extend((f'cell_drop({member});', f'{member} = NULL;'))

    def record_inline_type(name, typ):
        if SCALAR_MODES.get(typ) in EXTRA_MODES:
            numeric_bindings[name] = SCALAR_MODES[typ]
            return
        if typ in ERROR_VALUE_MODES:
            builtin_error_bindings[name] = ERROR_VALUE_MODES[typ]
            return
        if SCALAR_MODES[typ] in PLAIN_JOIN_TYPES:
            mode = SCALAR_MODES[typ]
            plain_join_bindings[name] = mode
            join_results[name] = f'frame->{fields[name]}', PLAIN_JOIN_FIELDS[mode], None
            return
        bindings = {'runtime::Error': runtime_error_bindings, 'Bool': boolean_bindings, 'u8': byte_bindings, 'char': char_bindings,
                    '&str': text_bindings, '&u8': byte_ref_bindings}.get(typ)
        if bindings is not None:
            bindings.add(name)
        elif SCALAR_MODES[typ] in VECTOR_SLICE_ELEMENTS:
            slice_bindings[name] = SCALAR_MODES[typ]
        elif SCALAR_MODES[typ] in SHARED_VECTOR_SLICE_MODES:
            slice_bindings[name] = SHARED_VECTOR_SLICE_MODES[SCALAR_MODES[typ]]
            mutable_slices.add(name)
        elif SCALAR_MODES[typ] in UTF8_VALUE_RESULT_FAMILIES:
            wrapped_utf8_bindings[name] = UTF8_VALUE_RESULT_FAMILIES[SCALAR_MODES[typ]]

    def inline_scalar_mode(name):
        if name in numeric_bindings:
            return numeric_bindings[name]
        if name in builtin_error_bindings:
            return builtin_error_bindings[name]
        if name in plain_join_bindings:
            return plain_join_bindings[name]
        if name in runtime_error_bindings:
            return 'runtime_error'
        if name in slice_bindings:
            return slice_bindings[name]
        if name in wrapped_utf8_bindings:
            return WRAPPED_UTF8_MODES[wrapped_utf8_bindings[name]]
        if name in byte_ref_bindings:
            return 'byte_ref'
        if name in text_bindings:
            return 'text'
        if name in char_bindings:
            return 'char'
        if name in byte_bindings:
            return 'byte'
        return 'scalar'

    def value_place(name):
        if references.get(name) in ('map_shared_ref_slot', 'map_owned_ref_slot', 'map_owned_mut_slot'):
            fail(node.line, 'une case HashMap indirecte se lit par ** pour accéder à la valeur')
        if name in pool_types:
            fail(node.line, 'un pool ne fournit pas de valeur scalaire ou de pointeur vers un élément')
        typ = reference_types.get(name, collection_types.get(name))
        if typ in reference_aggregates or typ in owned_aggregates:
            fail(node.line, 'une structure ne fournit pas une valeur Int ; sélectionner un champ')
        member = f'frame->{fields[name]}'
        mode = references.get(name)
        if mode == 'owned':
            return f'{member}->value'
        if mode in ('ref', 'mut'):
            return f'*{member}'
        return member

    def struct_field(place, line, *, write=False):
        _, name, path = place
        typ = reference_types.get(name, collection_types.get(name))
        layout = reference_structs.get(typ, owned_structures.get(typ))
        if layout is None:
            fail(line, 'projection async : référence de structure à champs Int ou références Int requise')
        if write and not (references.get(name) == 'mut' or references.get(name) == 'owned' and name in mutable):
            fail(line, 'écriture de champ : une référence mutable est requise')
        for index, (field, field_type) in enumerate(layout):
            if field == path:
                offset = structure_offset(layout, index)
                return name, f'frame->{fields[name]}', offset, tuple(path.split('.')), field_type
        fail(line, f"champ inconnu '{path}' dans {typ}")

    def inline_field_layout(place, bindings=None):
        if place[0] != 'field':
            return None
        signature = bindings.get(place[1]) if bindings is not None else None
        typ = (signature[1] if signature else None) if bindings is not None else reference_types.get(place[1], collection_types.get(place[1]))
        return next((layout for layout in inline_layouts.get(typ, ()) if layout.path == place[2]), None)

    def field_reference_shape(expr, bindings=None):
        if expr[0] not in ('ref_expr', 'mut_expr', 'field'):
            return None
        place = expr if expr[0] == 'field' else expr[1][1] if expr[1][0] == 'field_deref' else expr[1]
        if place[0] != 'field':
            return None
        if expr[0] != 'field' and expr[1][0] == 'field' and (contained := inline_field_layout(place, bindings)) is not None:
            return ('mut' if expr[0] == 'mut_expr' else 'ref', contained.typ)
        if bindings is None:
            typ = reference_types.get(place[1], collection_types.get(place[1]))
        else:
            signature = bindings.get(place[1])
            typ = signature[1] if signature else None
        layout = reference_structs.get(typ, owned_structures.get(typ))
        if layout is None:
            return None
        declared = dict(layout).get(place[2], '')
        if expr[0] == 'field' and not (declared.startswith('&') and not declared.startswith('&mut ')):
            return None
        if declared.startswith('&') and declared.removeprefix('&').removeprefix('mut ') in reference_structs:
            return ('mut' if expr[0] == 'mut_expr' else 'ref', declared.removeprefix('&').removeprefix('mut '))
        if expr[0] != 'field' and expr[1][0] == 'field_deref' and declared.startswith('A<') and declared[2:-1] in pool_structures:
            return ('mut' if expr[0] == 'mut_expr' else 'ref', declared[2:-1])
        # The actual field type/mode is checked by borrow_struct_field. In
        # particular &view.reference is not shorthand for &*view.reference.
        payload = declared if expr[0] != 'field' and expr[1][0] == 'field' and declared in EXTRA_C_TYPES else 'Int'
        return ('mut' if expr[0] == 'mut_expr' else 'ref', payload)

    def project_field_loans(loans, path):
        projected = []
        for target, mode in loans:
            if mode == 'storage':
                projected.append((target, mode))
                continue
            root, prefix = target if isinstance(target, tuple) else (target, ())
            projected.append(((root, prefix + path), mode))
        return projected

    def initial_stored_field_loans(holder, path):
        if path[:1] in (('map_items',), ('result_lock',)):
            return []
        typ = borrowed_field_type(reference_types.get(holder, collection_types.get(holder)), path)
        return [((holder, path), 'stored_mut_target' if typ and typ.startswith('&mut ') else 'shared_target')]

    def project_result_field_loans(loans, typ, path):
        path = stored_field_path('.' + '.'.join(path))
        projected = project_field_loans(loans, path)
        declared = borrowed_field_type(typ, path) or ''
        if declared.startswith('&') and not declared.startswith('&mut '):
            # These origins identify the external target. They do not reserve
            # the carrier slot or its mutable capability (ST13).
            retained = []
            for target, mode in projected:
                root, full_path = target if isinstance(target,tuple) else (target,())
                key = ('stored_field', root, full_path)
                guard_origins = active_loans.get(('mutex_guard', root), ())
                if guard_origins:
                    retained.append((target, mode))
                    owner = loan_root(guard_origins[0][0])
                    key = ('stored_field', owner, full_path)
                retained.extend(active_loans.get(key,
                    [(target, 'shared_target' if mode != 'storage' else mode)]))
            return retained
        if declared.startswith('&mut '):
            # Keep the field capability as well as its current target. A
            # reborrow suspends access to that field until its final use.
            retained = list(projected)
            for target, _ in projected:
                root, full_path = target if isinstance(target,tuple) else (target,())
                retained.extend(active_loans.get(('stored_field',root,full_path), ()))
            return list(dict.fromkeys(retained))
        return projected

    def borrow_struct_field(expr, mode, line):
        indirect = expr[0] == 'field' or expr[1][0] == 'field_deref'
        place = expr if expr[0] == 'field' else expr[1][1] if indirect else expr[1]
        if not indirect and (contained := inline_field_layout(place)) is not None:
            name = place[1]
            if mode == 'mut' and not (references.get(name) == 'mut' or references.get(name) == 'owned' and name in mutable):
                fail(line, 'emprunt de sous-structure : accès mutable requis')
            path = tuple(place[2].split('.'))
            reservation = 'mut' if references.get(name) == 'mut' else mode
            check_access(name, line, write=reservation == 'mut', path=path)
            source_type = reference_types.get(name, collection_types.get(name))
            offset = structure_offset(struct_layouts[source_type], contained.first)
            size = structure_offset(struct_layouts[contained.typ], contained.count)
            metadata = local_layouts.setdefault(contained.typ, f'{prefix}_local_layout_{len(local_layouts)}')
            cell = f'frame->{fields[name]}'
            pointer = f'structure_subview(structure_reference_for((CrustStructureView){{0}}, {cell}), {offset}, {size}, &{metadata})'
            loans = project_field_loans([(name, reservation), *received_refs.get(name, ())], path)
            return pointer, loans
        name, cell, offset, path, typ = struct_field(place, line, write=mode == 'mut')
        if indirect:
            owned_structure = typ.startswith('A<') and typ[2:-1] in pool_structures
            typed_reference = typ.startswith('&') and typ.removeprefix('&').removeprefix('mut ') in reference_structs
            if typed_reference and mode == 'mut' and not typ.startswith('&mut '):
                fail(line, 'réemprunt mutable depuis un champ partagé interdit')
            if not typed_reference and not owned_structure and (typ not in ('&Int', '&mut Int', 'A<Int>') or mode == 'mut' and typ not in ('&mut Int', 'A<Int>')):
                fail(line, 'réemprunt de champ : type ou mode incompatible')
            pointer = (f'cell_load_view({cell}, {offset})' if typed_reference else
                       f'cell_load_ref({cell}, {offset})' if owned_structure else f'&cell_load_ref({cell}, {offset})->value')
        else:
            if typ not in ('Int', *EXTRA_C_TYPES):
                fail(line, 'emprunt imbriqué non pris en charge ; utiliser &* ou &mut * pour la cible')
            ctype = FIELD_C_TYPES.get(typ, 'int')
            pointer = f'({ctype} *)cell_numeric_address({cell}, {offset}, sizeof({ctype}))'
        reservation = 'mut' if references.get(name) == 'mut' else mode
        check_access(name, line, write=reservation == 'mut', path=path)
        origins = [(name, reservation), *received_refs.get(name, ())]
        if references.get(name) == 'owned' and not typ.startswith('&'):
            # A field target is owned by the carrier: retaining the projection
            # must still prevent transferring/dropping the whole carrier.
            loans = project_field_loans(origins, path)
        else:
            loans = project_result_field_loans(origins, reference_types.get(name, collection_types.get(name)), path)
        return pointer, loans

    def store_struct_field(place, rhs, line, *, following):
        name, cell, offset, path, typ = struct_field(place, line, write=True)
        origins = [(name, 'mut'), *received_refs.get(name, ())]
        owner = guarded_field_owner(origins, line, injected=True) if scalar_field_mode(typ) is None else None
        injected_owner = owner in parameter_modes
        if injected_owner and (reference_type(typ) != ('ref', 'Int') or result[0] != 'void'):
            fail(line, 'écriture de dépendance gardée injectée : champ &i32 et tâche Void requis')
        holder = owner or name
        if typ.startswith('A<'):
            if rhs[0] not in ('move', 'new_transfer', 'array_transfer'):
                fail(line, 'remplacement de champ propriétaire : transfert explicite <- requis')
            incoming = sync_owned_value(rhs, line, following=following)
            target_type = typ[2:-1]
            if owned_result_types.get(incoming, 'Int') != target_type:
                fail(line, 'remplacement de champ propriétaire : même type requis')
            incoming_fields = owned_capture_field_loans(incoming, target_type)
            from results import FunctionResult, BorrowTarget
            field_updates, field_arguments = [], [origins]
            field_parameters = [('carrier', 'mut', reference_types.get(name, collection_types.get(name)))]
            for field, held in incoming_fields.items():
                target = len(field_arguments)
                field_arguments.append(held)
                field_parameters.append(('target', 'ref', 'Int'))
                full_path = '.' + '.'.join((*path, *stored_field_path(field)))
                field_updates.append((full_path, frozenset({BorrowTarget('parameter', target)})))
            changes = prepare_field_changes(FunctionResult('void', 'Void',
                structure_fields=((0, tuple(field_updates)),) if field_updates else ()),
                field_parameters, field_arguments, line, local_guard=True)
            if storage_of(incoming) & implicit_stacks:
                fail(line, 'un champ A<T> exige une allocation de pool, pas une valeur locale')
            require_durable_storage(incoming, binding_depth(holder) + 1 if references.get(holder) == 'owned' else 0, line)
            release_statement_loans(following)
            check_access(name, line, write=True, path=path)
            if owner is not None:
                guarded_field_owner(origins, line)
            old = temporary('Cell *')
            steps.extend((f'{old} = cell_load_ref({cell}, {offset});',
                          f'cell_store_ref({cell}, {offset}, {incoming});',
                          f'{incoming} = NULL;', f'cell_drop({old});', f'{old} = NULL;'))
            invalidate_guarded_receipts(holder, path)
            for key in list(active_loans):
                if (isinstance(key, tuple) and key[0] in ('owned_storage', 'stored_field')
                        and key[1] == holder and key[2][:len(path)] == path
                        and key != ('owned_storage', holder, path)):
                    del active_loans[key]
            for suffix, storage in owned_storage_fields(incoming).items():
                active_loans[('owned_storage', holder, path + suffix)] = storage
            install_field_change(('owned_storage', holder, path),
                                 [(origin, 'storage') for origin in storage_of(incoming)])
            for key, held in changes:
                install_field_change(key, held)
            clear_stored_fields(incoming)
            return
        field_reference = reference_type(typ)
        if field_reference is not None:
            if owner is None and (node.field_effect_summary is None or not node.field_effect_summary.complete):
                fail(line, 'prototype : remplacement de champ référence sans contrat de terminaison')
            access, target_type = field_reference
            pointer, held = sync_borrow_argument(rhs, access, target_type, line)
            target = stored_reference_cell(pointer, held, line) if target_type == 'Int' else pointer
            saved = temporary('Cell *' if target_type == 'Int' else reference_sync_types[access, target_type])
            steps.append(f'{saved} = {target};')
            release_statement_loans(following)
            check_access(name, line, write=True, path=path)
            if injected_owner:
                indices = {parameter: index for index, (parameter, _, _) in enumerate(node.args[1])}
                effect = node.field_effect_summary
                target = rhs[1] if rhs[0] in ('name', 'reborrow') else None
                write = (indices[owner], '.' + '.'.join(path), indices.get(target))
                if not effect or not effect.complete or write not in effect.guarded_writes:
                    fail(line, 'écriture de dépendance gardée : emprunt injecté et contrat complet requis')
                steps.append(f'cell_store_ref({cell}, {offset}, {saved});')
                install_field_change(('stored_field', owner, path), held)
                return
            from results import FunctionResult, BorrowTarget
            summary = FunctionResult('void', 'Void', structure_fields=(
                (0, (('.' + '.'.join(path), frozenset({BorrowTarget('parameter', 1)})),)),))
            parameters = (('carrier', 'mut', reference_types.get(name, collection_types.get(name))),
                          ('target', access, target_type))
            changes = prepare_field_changes(summary, parameters, [origins, held], line, local_guard=True)
            helper = 'cell_store_ref' if target_type == 'Int' else 'cell_store_view'
            steps.append(f'{helper}({cell}, {offset}, {saved});')
            for key, loans in changes:
                install_field_change(key, loans)
            return
        if scalar_field_mode(typ) is None:
            fail(line, 'prototype : remplacement de champ référence mutable dans un état non raccordé')
        value, actual = infer_scalar_value(rhs, line, following=following)
        if actual != ('Bool' if typ == 'bool' else typ):
            fail(line, f'une écriture de champ exige {typ}')
        saved = temporary(FIELD_C_TYPES.get(typ, 'int'))
        steps.append(f'{saved} = {value};')
        release_statement_loans(following)
        check_access(name, line, write=True, path=path)
        if typ == 'Int':
            steps.append(f'cell_store_int({cell}, {offset}, {saved});')
        else:
            steps.append(f'cell_store_numeric({cell}, {offset}, {FIELD_C_TYPES[typ]}, {saved});')

    def layout_array(item, context, line, expected_element=None):
        if item[0] == 'array_repeat':
            shape, child, element = layout_array(item[1], context[1:], line, expected_element)
            return (item[2], *shape), ('repeat', item[2], child), element
        if item[0] == 'array_literal':
            children = [layout_array(child, context[1:], line, expected_element) for child in item[1:]]
            if not children:
                if not context or context[0] != 0:
                    fail(line, 'un tableau vide [] exige un type de contexte')
                return context, ('literal', ()), expected_element
            shape, _, element = children[0]
            if any(child_shape != shape or child_element != element for child_shape, _, child_element in children):
                fail(line, 'tableau async : dimensions incompatibles ou types d’éléments différents')
            return (len(children), *shape), ('literal', tuple(plan for _, plan, _ in children)), element
        if expected_element == 'uint8_t':
            value, element = byte_value(item, line), 'uint8_t'
        elif expected_element == 'int':
            value, element = expression(item, line), 'int'
        else:
            value, typ = infer_scalar_value(item, line)
            mode = SCALAR_MODES.get(typ)
            element = {'scalar': 'int', 'byte': 'uint8_t', **EXTRA_C_TYPES}.get(mode)
            if element is None or expected_element is not None and element != expected_element:
                fail(line, 'tableau async : élément numérique de type compatible requis')
        saved = temporary(element)
        steps.append(f'{saved} = {value};')
        return (), ('scalar', saved), element

    def initialize_array(place, plan):
        kind, *parts = plan
        if kind == 'scalar':
            steps.append(f'{place} = {parts[0]};')
        elif kind == 'literal':
            for index, child in enumerate(parts[0]):
                initialize_array(f'{place}[{index}]', child)
        elif parts[0]:
            index = f'init_index_{len(steps)}'
            steps.append(f'for (size_t {index} = 0; {index} < {parts[0]}; ++{index}) {{')
            initialize_array(f'{place}[{index}]', parts[1])
            steps.append('}')

    def bind_array(statement, *, following):
        name, initializer = statement.args
        if initializer[0] == 'move' and initializer[1] in arrays:
            if statement.compact_transfer:
                fail(statement.line, 'déplacement de tableau : receveur local requis')
            original = initializer[1]
            require_local_async_value(original, statement.line)
            kind, value = export_async_value(original, (), statement.line)
            bind_transferred_value(name, kind, value, statement)
            return True
        if initializer[0] == 'array_transfer':
            initializer = initializer[1]
        if structure_copy_source(initializer) is not None or inline_vector_source(initializer) is not None:
            return False
        row_replace = None
        if initializer[0] == 'array_replace':
            place = ('array_index', initializer[1], initializer[2])
            root, indices = reference_array_path(place)
            remaining = arrays.get(root, ())[len(indices):]
            if remaining:
                row_replace = place, remaining
        if row_replace is None and initializer[0] not in ('array_literal', 'array_repeat', 'array_copy'):
            return False
        expected, element = scalar_array_layout(statement.annotation) if statement.annotation is not None else ((), None)
        if statement.compact_transfer or statement.annotation is not None and not expected:
            fail(statement.line, 'tableau async : type de tableau Int ou u8 requis')
        if row_replace is not None:
            place, remaining = row_replace
            if expected and expected != remaining:
                fail(statement.line, 'tableau async : dimensions incompatibles avec le type déclaré')
            actual_element = array_elements[root]
            if element is not None and element != actual_element:
                fail(statement.line, 'tableau async : type d’élément incompatible')
            expected, element = remaining, actual_element
            destination, (root, path) = array_element(
                place, statement.line, write=True, defer_access=True, remaining=expected)
            initializer = initializer[3]
            if initializer[0] not in ('array_literal', 'array_repeat', 'array_copy'):
                fail(statement.line, 'replace de ligne exige une valeur de tableau explicite')

        source = None
        if initializer[0] == 'array_copy':
            original, indices = reference_array_path(initializer[1])
            shape = arrays.get(original, ())[len(indices):]
            if not shape:
                fail(statement.line, 'copy exige une ligne ou un tableau')
            actual_element = array_elements[original]
            if element is not None and element != actual_element:
                fail(statement.line, 'tableau async : type d’élément incompatible')
            element = actual_element
            source, _ = array_element(initializer[1], statement.line, remaining=shape)
        else:
            shape, plan, element = layout_array(initializer, expected, statement.line, element)
        if expected and shape != expected:
            fail(statement.line, 'tableau async : dimensions incompatibles avec le type déclaré')
        member = declare(name, statement.line)
        arrays[name] = shape
        array_elements[name] = element
        scopes[-1][0][name] = None
        if statement.mutable:
            mutable.add(name)
        old = f'frame->{member}'
        received = temporary(element, array_dimensions(shape)) if row_replace is not None else old
        if source is None:
            initialize_array(received, plan)
        elif all(shape):
            steps.append(f'memcpy({received}, {source}, sizeof {received});')
        if row_replace is not None:
            release_statement_loans(following)
            check_access(root, statement.line, write=True, path=path)
            if all(shape):
                steps.extend((f'memcpy({old}, {destination}, sizeof {old});',
                              f'memcpy({destination}, {received}, sizeof {received});'))
        return True

    def array_suffix(dimensions):
        return ''.join(f'[{dimension}]' for dimension in dimensions)

    def array_dimensions(shape):
        return array_suffix(max(1, length) for length in shape)

    def array_byte_size(shape, element):
        return f'sizeof({element}{array_dimensions(shape)})'

    def array_offset(index_expr, length, line):
        if length == 0:
            fail(line, 'indice hors limites : tableau vide')
        if index_expr[0] == 'int':
            index = index_expr[1]
            if not 0 <= index < length:
                fail(line, 'indice hors limites du tableau')
            return index, index
        if index_expr[0] == 'array_numeric_literal':
            typ, index = index_expr[1:]
            if FORMATS[typ].precision or not 0 <= index < length:
                fail(line, 'indice hors limites du tableau')
            return index, index
        value, typ = infer_scalar_value(index_expr, line)
        spec = FORMATS.get('i32' if typ == 'Int' else typ)
        if spec is None or spec.precision:
            fail(line, 'un indice doit être entier')
        saved = temporary(spec.c_type)
        offset = temporary('size_t')
        steps.append(f'{saved} = {value};')
        negative = f'{saved} < 0 || ' if spec.signed else ''
        steps.append(f'if ({negative}(uint64_t){saved} >= {length}) fail("indice hors limites du tableau");')
        steps.append(f'{offset} = (size_t){saved};')
        return offset, None

    def array_element(place, line, *, write=False, defer_access=False, remaining=(), dereference=False,
                      reference_container=False, expected_element=None):
        name, indices = reference_array_path(place)
        if name not in arrays:
            fail(line, 'projection de tableau Int : dimensions incompatibles')
        if name in consumed:
            fail(line, f"'{name}' n’est plus utilisable après drop ou transfert")
        shape = arrays[name]
        element_type = array_elements[name]
        if expected_element is not None and element_type != expected_element:
            fail(line, 'projection de tableau : type d’élément incompatible')
        if len(indices) > len(shape) or shape[len(indices):] != remaining:
            fail(line, 'projection de tableau Int : dimensions incompatibles')
        if name in reference_rows and not (dereference or reference_container):
            fail(line, 'une case de références exige un déréférencement explicite')
        capability = parameter_modes.get(name)
        if write and (capability == 'array_ref' or capability != 'array_mut' and name not in mutable):
            fail(line, f"'{name}' est immuable")
        if write and name in reference_rows and any(
                access == 'ref' for _, access in reference_rows[name][1][:len(indices)]):
            fail(line, 'écriture interdite à travers une référence partagée')
        path, offsets = [], []
        for index_expr, length in zip(indices, shape[:len(indices)], strict=True):
            offset, index = array_offset(index_expr, length, line)
            path.append(index)
            offsets.append(offset)
        path = tuple(path)
        if not defer_access:
            check_access(name, line, write=write, path=path)
        base = f'frame->{fields[name]}'
        if name in reference_rows:
            qualifier = 'const ' if capability == 'array_ref' else ''
            ctype, layout = reference_rows[name]
            element = f'(*({qualifier}{ctype} *){base})'
            for depth, offset in enumerate(offsets):
                element += f'.data[{offset}]'
                if layout[depth][1] and depth + 1 < len(layout):
                    element = f'(*({element}))'
        elif capability in ARRAY_BORROWS:
            # Captures may point into native arrays or nested synchronous structs.
            qualifier = 'const ' if capability == 'array_ref' else ''
            address = f'({qualifier}unsigned char *){base}'
            for depth, offset in enumerate(offsets):
                address += f' + (size_t)({offset}) * {array_byte_size(shape[depth + 1:], element_type)}'
            element = f'({address})' if remaining else f'(*({qualifier}{element_type} *)({address}))'
        else:
            element = f'{base}{array_suffix(offsets)}'
        return f'(*({element}))' if dereference else element, (name, path)

    def store_array(place, rhs, line, *, following, returns_old=False):
        if place[0] == 'array_hashmap_target':
            name = place[1][1]
            target, typ = hashmap_target(place, line, write=True)
            reservation = [(name, 'ref'), *received_refs[name]]
            active_loans[id(reservation)] = reservation
            try:
                value, actual = infer_scalar_value(rhs, line, following=following)
                if actual != typ:
                    fail(line, f'écriture dans une allocation de case HashMap : {typ} attendu')
            finally:
                active_loans.pop(id(reservation), None)
            check_access(name, line, write=True)
            steps.append(f'{target} = {value};')
            return
        if place[0] == 'name' and place[1] in references:
            receiver = place[1]
            guard_type = collection_types.get(receiver)
            if (payload := mutex_payload(guard_type, GUARD_TYPES)) is not None:
                if receiver not in mutable:
                    fail(line, 'écriture à travers une garde : let mut est requis')
                if not scalar_field_mode(payload):
                    fail(line, 'modifier les champs de la structure gardée via un réemprunt')
                value, actual = infer_scalar_value(rhs, line, following=following)
                if actual != ('Bool' if payload == 'bool' else payload):
                    fail(line, f'écriture à travers une garde : {payload} attendu')
                check_access(receiver, line, write=True)
                saved = temporary(FIELD_C_TYPES.get(payload, 'int'))
                steps.extend((f'{saved} = {value};',
                    f'memcpy(crust_guard_value(frame->{fields[receiver]}, {int(guard_type.startswith("Async"))}), '
                    f'&{saved}, sizeof({saved}));'))
                return
            if references[receiver] != 'mut' or receiver in collection_types:
                fail(line, 'écriture par référence : un emprunt mutable modifiable est requis')
            typ = reference_types.get(receiver)
            if typ in EXTRA_C_TYPES:
                value, actual = infer_scalar_value(rhs, line, following=following)
                if typ != actual:
                    fail(line, f'écriture par référence : {typ} attendu')
            else:
                value = (byte_value(rhs, line, following=following) if typ == 'u8'
                         else expression(rhs, line, following=following))
            check_access(receiver, line, write=True)
            steps.append(f'{value_place(receiver)} = {value};')
            return
        view_mode = indexed_vector_view_mode(place)
        preparation = []
        collection = collection_index_type(place)
        byte_element = collection == 'Vector<u8>' or is_byte_array_element(place)
        if place[0] == 'array_deref_slot' and collection_index_type(place[1]) == HANDLE_VECTOR:
            name, path = place[1][1][1], ()
            target = handle_vector_target(place[1], line, write=True) + '->value'
            # Preserve the selected allocation while evaluating the RHS.
            # Shared reads remain legal; mutation/drop of the carrier does not.
            preparation = [(name, 'ref')]
        elif view_mode is not None:
            if place[1][0] != 'name' or place[1][1] not in mutable_slices:
                fail(line, 'écriture interdite à travers une tranche partagée')
            name, path = place[1][1], ()
            byte_element = view_mode == 'vector_bytes'
            pointer = vector_view_address(place, line, view_mode, write=True)
            target = f'*{pointer}'
            preparation = list(utf8_result_loans[pointer])
        elif collection in ('Vector<Int>', 'Vector<u8>'):
            target = owned_vector_element(place, line, write=True)
            name, path = place[1][1], ()
        else:
            dereference = place[0] == 'array_deref_slot'
            if dereference:
                place = place[1]
                if reference_array_path(place)[0] not in reference_rows:
                    fail(line, 'écriture par référence stockée : tableau de références requis')
            target, (name, path) = array_element(place, line, write=True, defer_access=True, dereference=dereference)
        element = array_elements.get(name) if not view_mode and not collection and name not in reference_rows else None
        numeric_element = next((typ for typ, spec in FORMATS.items()
                                if spec.mode in EXTRA_MODES and spec.c_type == element), None)
        if preparation:
            active_loans[id(preparation)] = preparation
        try:
            if numeric_element is not None:
                value, actual = infer_scalar_value(rhs, line, following=following)
                if actual != numeric_element:
                    fail(line, 'une écriture doit conserver le type numérique de la case')
            else:
                value = byte_value(rhs, line) if byte_element else expression(rhs, line)
        finally:
            active_loans.pop(id(preparation), None)
        ctype = element if numeric_element is not None else 'uint8_t' if byte_element else 'int'
        saved = temporary(ctype)
        steps.append(f'{saved} = {value};')
        if following is not None:
            release_statement_loans(following)
        check_access(name, line, write=True, path=path)
        if returns_old:
            previous = temporary(ctype)
            steps.append(f'{previous} = {target};')
        steps.append(f'{target} = {saved};')
        if returns_old:
            return previous

    def swap_array(expr, line, *, following):
        _, receiver, first, second = expr
        name, indices = reference_array_path(receiver)
        shape = arrays.get(name, ())[len(indices):]
        if not shape:
            fail(line, 'swap exige un tableau Int')
        element_type = array_elements[name]
        length, *element = shape
        base, (_, prefix) = array_element(receiver, line, write=True, defer_access=True, remaining=shape)
        left, left_index = array_offset(first, length, line)
        right, right_index = array_offset(second, length, line)
        release_statement_loans(following)
        check_access(name, line, write=True, path=(*prefix, left_index))
        check_access(name, line, write=True, path=(*prefix, right_index))
        borrowed = parameter_modes.get(name) in ARRAY_BORROWS
        if borrowed and not element:
            base = f'(({element_type} *){base})'
        left_place, right_place = f'{base}[{left}]', f'{base}[{right}]'
        steps.append(f'if ({left} != {right}) {{')
        if not element:
            saved = temporary(element_type)
            steps.extend((f'{saved} = {left_place};', f'{left_place} = {right_place};', f'{right_place} = {saved};'))
        elif all(element):
            size = array_byte_size(element, element_type)
            left_bytes = f'{base} + (size_t)({left}) * {size}' if borrowed else f'(unsigned char *)&({left_place})'
            right_bytes = f'{base} + (size_t)({right}) * {size}' if borrowed else f'(unsigned char *)&({right_place})'
            steps.extend((f'unsigned char *left_bytes = {left_bytes};',
                          f'unsigned char *right_bytes = {right_bytes};',
                          f'for (size_t byte = 0; byte < {size}; ++byte) {{',
                          'unsigned char saved = left_bytes[byte];',
                          'left_bytes[byte] = right_bytes[byte];',
                          'right_bytes[byte] = saved;', '}'))
        steps.append('}')

    def capture_array_place(projection, mode, line, *, remaining=(), expected_element='int'):
        dereference = projection[0] == 'array_deref_slot'
        vector_projection = projection[1] if dereference else projection
        collection = collection_index_type(vector_projection)
        handle_target = dereference and collection == HANDLE_VECTOR
        if (not dereference and collection in ('Vector<Int>', 'Vector<u8>')) or handle_target:
            projection = vector_projection
            name = projection[1][1]
            element = 'int' if collection == 'Vector<Int>' or handle_target else 'uint8_t'
            if element != expected_element or remaining:
                fail(line, 'emprunt de case Vector : type incompatible')
            if mode == 'mut' and not (references.get(name) == 'mut'
                                     or references.get(name) == 'owned' and name in mutable):
                fail(line, 'emprunt de case Vector : une liaison mutable est requise')
            reservation = 'mut' if references.get(name) == 'mut' else mode
            check_access(name, line, write=reservation == 'mut')
            loans = [(name, reservation)]
            active_loans[id(loans)] = loans
            try:
                index = expression(projection[2], line)
            finally:
                active_loans.pop(id(loans), None)
            pointer = temporary(element + ' *')
            if handle_target:
                # Borrow the stable allocation contents, not the Cell* slot.
                # The carrier loan keeps that allocation alive until last use.
                steps.append(f'{pointer} = &(*(Cell **)vector_checked_item(frame->{fields[name]}, {index}))->value;')
            else:
                steps.append(f'{pointer} = ({element} *)vector_checked_item(frame->{fields[name]}, {index});')
            return pointer, (name, reservation)
        if dereference:
            projection = projection[1]
            if reference_array_path(projection)[0] not in reference_rows:
                fail(line, 'capture async : tableau de références requis')
        place, target = array_element(projection, line, write=mode == 'mut',
                                      defer_access=True, remaining=remaining, dereference=dereference,
                                      expected_element=expected_element)
        name, path = target
        reservation = 'mut' if parameter_modes.get(name) == 'array_mut' else mode
        if dereference and reservation == 'mut':
            # The frame knows the slot path, but not the ancestry of the
            # stored capability supplied by the caller.
            path = ()
        check_access(name, line, write=reservation == 'mut', path=path)
        if remaining and not all(remaining):
            pointer = 'NULL'
        elif remaining and parameter_modes.get(name) in ARRAY_BORROWS:
            pointer = place
        else:
            pointer = f'&({place})'
        return pointer, ((name, path), reservation)

    def assign(receiver, expr, line, *, following):
        if receiver in arrays:
            fail(line, 'affectation de tableau async : écrire un élément')
        if receiver in mutable_slices:
            fail(line, 'affectation de tranche mutable async : écrire un élément')
        if receiver not in mutable:
            fail(line, 'affectation async : un receveur mutable est requis')
        if references.get(receiver) == 'owned':
            if receiver in consumed:
                fail(line, f"'{receiver}' n’est plus utilisable après drop ou transfert")
            receiver_is_local = bool(storage_bindings.get(receiver, frozenset()) & implicit_stacks)
            if receiver_is_local:
                destinations = storage_bindings[receiver] & implicit_stacks
                if len(destinations) == 1:
                    place_local_result(expr, destination=next(iter(destinations)))
            if expr[0] in ('array_transfer', 'new_transfer') and expr[1][0] in ('scope', 'if_expr', 'value_match', 'loop_expr', 'await'):
                expr = expr[1]
            operator = expr[0]
            if operator == 'move':
                source = expr[1]
                require_local_async_value(source, line)
                if source == receiver:
                    check_access(source, line, write=True)
                    return
                depth = binding_depth(receiver) + 1 if result_lock_loans(source) else None
                kind, replacement = export_async_value(source, (), line, depth=depth)
            elif operator == 'scope' and ends_in_transfer(expr[2]):
                kind, replacement = emit_computed_transfer(expr, line, following=following)
            elif (sync_signature(expr) in owned_output_types or operator in ('new', 'new_enum')
                  or operator in ('new_transfer', 'array_transfer') and (
                      expr[1][0] in ('new', 'new_enum') or sync_signature(expr[1]) in owned_output_types
                      or handle_remove_receiver(expr[1]) is not None)):
                kind, replacement = 'owned', sync_owned_value(expr, line, following=following)
            elif operator in ('if_expr', 'value_match') and has_transfer_result(expr):
                kind, replacement = emit_computed_transfer(expr, line, following=following)
            elif operator == 'loop_expr':
                kind, replacement = emit_loop(expr[1].args[0], line, valued=True, following=following)
            elif operator == 'await' and (computed_await(expr) or await_result_mode(expr) == 'owned'):
                prepared = None
                result_type = await_signature(expr)
                if computed_await(expr):
                    selected, prepared = emit_computed_transfer(expr[1], line)
                    if selected != 'task':
                        fail(line, 'affectation async : une tâche inactive est requise')
                    result_type = functions[prepared[3]].args[2]
                expected_type = collection_types.get(receiver, 'Int')
                if result_type != ('owned', expected_type) and not (
                        expected_type == 'Int' and result_type == ('scalar', 'Int')):
                    fail(line, 'affectation async : un résultat du type du receveur est requis')
                kind = result_type[0]
                replacement = await_task(expr, line, returns_value=True, owned=kind == 'owned', prepared=prepared)
            else:
                kind = None
            if kind == 'scalar':
                check_access(receiver, line, write=True)
                steps.append(f'{value_place(receiver)} = {replacement};')
                return
            if kind is not None:
                if (kind != 'owned' or owned_result_types.get(replacement, 'Int')
                        != collection_types.get(receiver, 'Int')):
                    fail(line, 'remplacement async : une allocation du même type est requise')
                if receiver_is_local != bool(storage_of(replacement) & implicit_stacks):
                    fail(line, 'remplacement async : une valeur locale T et une allocation A<T> sont de types distincts')
                if map_types(collection_types.get(receiver)) or result_lock_loans(replacement):
                    require_durable_storage(replacement, binding_depth(receiver) + 1, line, local_receiver=True)
                if not utf8_current_live(following, receiver, owned=True):
                    fail(line, f"résultat propriétaire '{receiver}' sans usage explicite")
                release_statement_loans(following)
                if receiver not in consumed:
                    drop_owned(receiver, line)
                consumed.remove(receiver)
                storage_bindings[receiver] = storage_of(replacement)
                move_stored_fields(replacement, receiver)
                steps.append(f'frame->{fields[receiver]} = {replacement};')
                names = next(names for names, *_ in reversed(scopes) if receiver in names)
                del names[receiver]
                if operator == 'move' and names is scopes[-1][0]:
                    order = tuple(names)
                    names.clear()
                    for name in order:
                        names[name] = None
                        if name == source:
                            names[receiver] = None
                else:
                    names[receiver] = None
                return
        if receiver in collection_types:
            fail(line, 'réaffectation de collection : transfert explicite du même type requis')
        utf8_receiver = (receiver in text_bindings or receiver in byte_ref_bindings or receiver in slice_bindings
                         or wrapped_utf8_bindings.get(receiver) == 12)
        if utf8_receiver and not mentions(expr, receiver):
            for scope in scopes:
                if receiver in scope[4]:
                    active_loans.pop(id(scope[4][receiver][0]), None)
        if receiver in wrapped_utf8_bindings:
            value, actual_type = infer_scalar_value(expr, line, following=following)
            if actual_type != WRAPPED_UTF8_TYPES[wrapped_utf8_bindings[receiver]]:
                fail(line, 'la réaffectation doit conserver la famille du résultat UTF-8')
        elif receiver in numeric_bindings:
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != EXTRA_MODES[numeric_bindings[receiver]]:
                fail(line, 'la réaffectation doit conserver le type numérique')
        elif receiver in byte_bindings:
            value = byte_value(expr, line, following=following)
        elif receiver in char_bindings:
            value = char_value(expr, line, context='une affectation char', following=following)
        elif receiver in builtin_error_bindings:
            value = builtin_error_value(expr, builtin_error_bindings[receiver], line, following=following)
        elif receiver in runtime_error_bindings:
            value = runtime_error_value(expr, line, following=following)
        elif receiver in plain_join_bindings:
            value = plain_join_value(expr, plain_join_bindings[receiver], line, following=following)
        elif receiver in byte_ref_bindings:
            value = static_byte_ref_value(expr, line, following=following)
        elif receiver in text_bindings:
            value = static_text_value(expr, line, following=following)
        elif receiver in slice_bindings:
            value = vector_view_value(expr, line, slice_bindings[receiver], following=following)
        else:
            evaluate = boolean_value if receiver in boolean_bindings else expression
            value = evaluate(expr, line, following=following)
        if utf8_receiver:
            loans = list(local_utf8_loans(expr, value))
            owner = next((scope for scope in reversed(scopes) if receiver in scope[4]), scopes[0])
            old = owner[4].get(receiver)
            if old is not None:
                active_loans.pop(id(old[0]), None)
            utf8_view_loans[receiver] = tuple(loans)
            mutable_utf8_bindings.add(receiver)
            active_loans[id(loans)] = loans
            owner[4][receiver] = loans, float('inf')
        check_access(receiver, line, write=True)
        if references.get(receiver) not in (None, 'owned'):
            fail(line, 'affectation async : utiliser set sur un emprunt mutable')
        steps.append(f'{value_place(receiver)} = {value};')

    def numeric_compound_store(expr, line, following):
        _, place, operator, rhs = expr
        name, _ = reference_array_path(place)
        indirect = None
        if place[0] == 'name':
            name = place[1]
            if name not in mutable or name in references:
                fail(line, 'affectation composée : une variable numérique mutable est requise')
            mode = inline_scalar_mode(name)
            typ = MODE_TYPES.get(mode)
            target, path = value_place(name), ()
        elif place[0] == 'field':
            name, cell, offset, path, declared = struct_field(place, line, write=True)
            typ = numeric_type(declared)
            if typ is not None:
                indirect = f'cell_numeric_address({cell}, {offset}, sizeof({FORMATS[typ].c_type}))'
        elif place[0] == 'deref':
            name, path = place[1], ()
            capability = references.get(name)
            if capability != 'mut' and not (capability == 'owned' and name in mutable):
                fail(line, 'affectation composée : emprunt ou allocation mutable requis')
            nominal = collection_types.get(name, reference_types.get(name, 'Int'))
            guard_payload = mutex_payload(nominal, GUARD_TYPES)
            typ = numeric_type(guard_payload or nominal)
            if guard_payload:
                indirect = f'crust_guard_value(frame->{fields[name]}, {int(nominal.startswith("Async"))})'
            elif capability == 'owned' and typ not in (None, 'i32'):
                indirect = f'(unsigned char *)frame->{fields[name]}->fields'
            else:
                target = value_place(name)
        else:
            if name not in arrays:
                fail(line, 'affectation composée : case de tableau fixe attendue')
            element = array_elements[name]
            typ = next((typ for typ, spec in FORMATS.items()
                        if spec.c_type == element or typ == 'i32' and element == 'int'), None)
            target, (_, path) = array_element(place, line, write=True)
        if typ is None:
            fail(line, 'affectation composée : emplacement numérique attendu')
        check_access(name, line, write=True, path=path)
        ctype = FORMATS[typ].c_type
        address, previous = temporary('unsigned char *' if indirect else f'{ctype} *'), temporary(ctype)
        if indirect:
            steps.extend((f'{address} = {indirect};', f'memcpy(&{previous}, {address}, sizeof({previous}));'))
        else:
            steps.extend((f'{address} = &({target});', f'{previous} = *{address};'))
        loan = [((name, path), 'ref')]
        active_loans[id(loan)] = loan
        try:
            value, actual = infer_scalar_value(rhs, line, following=following)
        finally:
            active_loans.pop(id(loan), None)
        if actual != ('Int' if typ == 'i32' else typ):
            fail(line, f'affectation composée : valeur {typ} attendue')
        release_statement_loans(following)
        check_access(name, line, write=True, path=path)
        value = c_operation(operator, typ, previous, value)
        if indirect:
            steps.extend((f'{previous} = {value};', f'memcpy({address}, &{previous}, sizeof({previous}));'))
        else:
            steps.append(f'*{address} = {value};')

    def expression(expr, line, *, following=None):
        if expr[0] == 'deref' and mutex_payload(collection_types.get(expr[1]), GUARD_TYPES) == 'Int':
            return infer_scalar_value(expr, line, following=following)[0]
        if (expr[0] == 'utf8_value' and expr[1][0] == 'name'
                and utf8_match_payloads.get(expr[1][1]) == 'i32'):
            return f'{utf8_match_results[expr[1][1]]}.value'
        if expr[0].startswith('array_numeric_'):
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != 'Int':
                fail(line, 'une expression i32 est attendue')
            return value
        if expr[0] == 'array_handle_len':
            receiver = expr[1][1]
            handle_vector_mutation(receiver, line, following=following)
            return f'vector_len(frame->{fields[receiver]})'
        if expr[0] in ('array_handle_exchange_status', 'array_buffered_exchange_status'):
            name = expr[1][1]
            require_local_async_value(name, line)
            record = handle_exchange_record(name, line)
            if expr[0] == 'array_buffered_exchange_status' and expr[2][1] >= 0:
                if (expr[2][1] == 1) != (record[1] == 'rejected_allocation'):
                    fail(line, 'try_push exige Ok(()), replace exige Ok(handle)')
            return f'{record[0]}.status'
        if expr[0] == 'array_handle_option_status':
            name = expr[1][1]
            require_local_async_value(name, line)
            return f'{handle_option_record(name, line)[0]}.status'
        if expr[0] == 'match_expr':
            return match_enum(expr[1], valued=True, following=following)
        if sync_signature(expr) is not None:
            return sync_call(expr, line, ('scalar', 'Int'), following=following)[0]
        op = expr[0]
        if op == 'array_hashmap_target':
            value, typ = hashmap_target(expr, line)
            if typ != 'Int':
                fail(line, f'une valeur Int est requise, reçu {typ}')
            return value
        if op in ('field', 'field_deref'):
            name, cell, offset, path, typ = struct_field(expr[1] if op == 'field_deref' else expr, line)
            if typ not in ('Int', '&Int', '&mut Int', 'A<Int>'):
                fail(line, 'lecture Int : champ du type déclaré incompatible')
            if (op == 'field') != (typ == 'Int'):
                fail(line, 'lecture Int : déréférencer explicitement un champ référence')
            check_access(name, line, path=path)
            value = temporary('int')
            load = (f'cell_load_int({cell}, {offset})' if typ == 'Int'
                    else f'cell_load_ref({cell}, {offset})->value')
            steps.append(f'{value} = {load};')
            return value
        if (typ := vector_remove_type(expr)) is not None:
            if typ != 'Int':
                fail(line, 'une valeur Int est requise, reçu u8')
            return vector_remove_value(expr, line, following=following)
        if op == 'array_integer_cast':
            value, typ = integer_cast_value(expr, line, following=following)
            if typ != 'Int':
                fail(line, 'une valeur Int est requise, reçu u8')
            return value
        if op == 'array_byte_literal':
            fail(line, 'une valeur Int est requise, reçu u8')
        if op == 'name' and expr[1] in utf8_match_tags:
            return utf8_match_tags[expr[1]]
        family = wrapped_utf8_family(expr)
        if family is not None:
            fail(line, f'une valeur Int est requise, reçu {WRAPPED_UTF8_TYPES[family]}')
        if is_boolean(expr):
            fail(line, 'une valeur Int est requise, reçu Bool')
        if op in ('name', 'deref') and expr[1] in byte_bindings:
            fail(line, 'une valeur Int est requise, reçu u8')
        if (expr[0] == 'utf8_value' and expr[1][0] == 'name' and utf8_match_payloads.get(expr[1][1]) == 'u8'
                or indexed_vector_view_mode(expr) == 'vector_bytes' or is_byte_array_element(expr) or is_text_index(expr) or collection_index_type(expr) in ('Vector<u8>', 'String')
                or op == 'deref' and (expr[1] in byte_ref_bindings or reference_types.get(expr[1]) == 'u8')):
            fail(line, 'une valeur Int est requise, reçu u8')
        if is_static_byte_ref(expr):
            fail(line, 'une valeur Int est requise, reçu &u8')
        if vector_view_mode(expr) is not None or (op == 'name' and expr[1] in mutable_slices):
            fail(line, 'une valeur Int est requise, reçu une tranche')
        if builtin_error_mode(expr) is not None:
            fail(line, 'une valeur Int est requise, reçu une erreur builtin')
        if is_runtime_error(expr):
            fail(line, 'une valeur Int est requise, reçu runtime::Error')
        if plain_join_mode(expr) is not None:
            fail(line, 'une valeur Int est requise, reçu Result')
        if op in ('name', 'deref') and expr[1] in char_bindings:
            fail(line, 'une valeur Int est requise, reçu char')
        if is_static_text(expr):
            fail(line, 'une valeur Int est requise, reçu &str')
        if op == 'utf8_byte_len' or (op == 'method_call' and expr[2] == 'byte_len'):
            if op == 'method_call' and expr[3]:
                fail(line, 'byte_len ne prend aucun argument')
            receiver = expr[1]
            if receiver[0] == 'name' and collection_types.get(receiver[1]) == 'String':
                check_access(receiver[1], line)
                return f'string_byte_len(frame->{fields[receiver[1]]})'
            return f'text_byte_len({static_text_value(receiver, line, following=following)})'
        if op == 'method_call' and expr[2] == 'len' and expr[1][0] == 'name':
            receiver = expr[1][1]
            if collection_types.get(receiver) not in ('Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS) or expr[3]:
                fail(line, 'len exige un Vector sans argument')
            check_access(receiver, line)
            return f'vector_len(frame->{fields[receiver]})'
        if op == 'utf8_len' or (op == 'method_call' and expr[2] == 'utf8_len'):
            if op == 'method_call' and expr[3]:
                fail(line, 'utf8_len ne prend aucun argument')
            value = char_value(expr[1], line, context='utf8_len')
            return f'char_utf8_len({value})'
        if op in ('name', 'deref'):
            check_access(expr[1], line)
        if op == 'int':
            return str(expr[1])
        if op == 'array_index':
            if indexed_vector_view_mode(expr) == 'vector_ints':
                return f'*{vector_view_address(expr, line, "vector_ints")}'
            if collection_index_type(expr) == 'Vector<Int>':
                return owned_vector_element(expr, line)
            return array_element(expr, line)[0]
        if op == 'array_deref_slot' and collection_index_type(expr[1]) == HANDLE_VECTOR:
            return handle_vector_target(expr[1], line) + '->value'
        if op == 'array_deref_slot' and reference_array_path(expr[1])[0] in reference_rows:
            return array_element(expr[1], line, dereference=True)[0]
        if op == 'array_replace':
            return store_array(('array_index', expr[1], expr[2]), expr[3], line,
                               following=following, returns_old=True)
        if op == 'array_len':
            if expr[1][0] == 'name' and collection_types.get(expr[1][1]) in ('Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS):
                receiver = expr[1][1]
                check_access(receiver, line)
                return f'vector_len(frame->{fields[receiver]})'
            name, indices = reference_array_path(expr[1])
            if name not in arrays or len(indices) >= len(arrays[name]):
                fail(line, 'len exige un tableau Int')
            remaining = arrays[name][len(indices):]
            array_element(expr[1], line, remaining=remaining, defer_access=True, reference_container=True)
            return str(remaining[0])
        if op == 'deref' and expr[1] in references:
            if expr[1] in collection_types:
                fail(line, 'une valeur Int est requise, reçu une collection')
            return value_place(expr[1])
        if op == 'name':
            if expr[1] in arrays:
                fail(line, 'une valeur Int est requise : indexer le tableau')
            if expr[1] in references:
                fail(line, 'lecture d’un emprunt Int : utiliser le déréférencement explicite *')
            if expr[1] not in fields:
                fail(line, f"variable inconnue '{expr[1]}'")
            return f'frame->{fields[expr[1]]}'
        if op == 'arithmetic':
            left = expression(expr[2], line)
            saved_left = temporary('int')
            steps.append(f'{saved_left} = {left};')
            right = expression(expr[3], line)
            result = temporary('int')
            steps.append(f"{result} = int_arithmetic('{expr[1]}', {saved_left}, {right});")
            return result
        if op == 'scope':
            value, typ = infer_scalar_value(expr, line, following=following)
            if typ != 'Int':
                fail(line, f'une valeur Int est requise, reçu {typ}')
            return value
        if op == 'if_expr':
            _, condition, yes, no = expr
            return conditional(condition, yes, no, line, valued=True, following=following)
        if op == 'loop_expr':
            kind, value = emit_loop(expr[1].args[0], line, valued=True, following=following)
            if kind in SCALAR_TYPES and kind != 'scalar':
                typ = SCALAR_TYPES[kind]
                fail(line, f'une valeur Int est requise, reçu {typ}')
            if kind != 'scalar':
                fail(line, 'un résultat transféré de boucle async exige une liaison locale')
            return value
        if op == 'value_match':
            return match_async_result(expr[1], line, following=following)
        if op == 'await':
            if awaits_execution(expr):
                fail(line, 'un handle fournit un Result : recevoir le résultat ou utiliser match')
            return await_task(expr, line, returns_value=True)
        fail(line, f'prototype async : expression {op} non prise en charge')

    def integer_cast_value(expr, line, *, following=None):
        value, typ = infer_scalar_value(expr[1], line, following=following)
        mode, error = exact_integer_conversion({'Int': 'scalar', 'u8': 'byte'}.get(typ), expr[2])
        if error:
            fail(line, error)
        ctype = 'int' if mode == 'scalar' else 'uint8_t'
        return f'(({ctype})({value}))', expr[2]

    def hashmap_target(expr, line, *, write=False):
        name = expr[1][1]
        mode = references.get(name)
        if mode not in ('map_shared_ref_slot', 'map_owned_ref_slot', 'map_owned_mut_slot'):
            fail(line, '** exige ici une case HashMap indirecte')
        if write and mode != 'map_owned_mut_slot':
            fail(line, 'écriture indirecte : une case HashMap propriétaire empruntée en mutable est requise')
        check_access(name, line, write=write)
        member = f'frame->{fields[name]}'
        declared = reference_types[name]
        if mode == 'map_shared_ref_slot':
            typ = declared[1:]
            return f'(**{member})', 'Bool' if typ == 'bool' else typ
        typ = map_handle_element(declared)
        if typ == 'Int':
            return f'(*{member})->value', typ
        _, ctype = map_scalar_layout(typ)
        return f'(*({ctype} *)(*{member})->fields)', typ

    def infer_scalar_value(expr, line, *, following=None):
        op = expr[0]
        if op == 'array_hashmap_target':
            return hashmap_target(expr, line)
        if op == 'deref' and (payload := mutex_payload(collection_types.get(expr[1]), GUARD_TYPES)):
            if not scalar_field_mode(payload):
                fail(line, 'une structure gardée se consulte par un réemprunt explicite')
            name = expr[1]
            check_access(name, line)
            value = temporary(FIELD_C_TYPES.get(payload, 'int'))
            asynchronous = int(collection_types[name].startswith('Async'))
            steps.append(f'memcpy(&{value}, crust_guard_value(frame->{fields[name]}, {asynchronous}), sizeof({value}));')
            return value, 'Bool' if payload == 'bool' else payload
        if op == 'deref' and collection_types.get(expr[1]) in owned_numeric_types:
            name = expr[1]
            check_access(name, line)
            typ = collection_types[name]
            value = temporary(FORMATS[typ].c_type)
            steps.append(f'memcpy(&{value}, frame->{fields[name]}->fields, sizeof({value}));')
            return value, typ
        if op == 'deref' and reference_types.get(expr[1]) in EXTRA_C_TYPES:
            name = expr[1]
            check_access(name, line)
            return value_place(name), reference_types[name]
        if op == 'field' and expr[1] in fields:
            name, cell, offset, path, typ = struct_field(expr, line)
            if typ in FIELD_C_TYPES:
                check_access(name, line, path=path)
                value = temporary(FIELD_C_TYPES[typ])
                steps.append(f'memcpy(&{value}, cell_numeric_address({cell}, {offset}, sizeof({value})), sizeof({value}));')
                return value, 'Bool' if typ == 'bool' else typ
        if op == 'utf8_value' and expr[1][0] == 'name':
            subject = expr[1][1]
            if wrapped_utf8_family_by_result.get(subject) in CONVERSION_FAMILIES.values():
                typ = utf8_match_payloads[subject]
                return f'{utf8_match_results[subject]}.value', 'Int' if typ == 'i32' else typ
        if op == 'name' and expr[1] in numeric_bindings:
            check_access(expr[1], line)
            return value_place(expr[1]), EXTRA_MODES[numeric_bindings[expr[1]]]
        if op == 'array_numeric_literal':
            typ, value = expr[1:]
            return c_literal(typ, value), 'Int' if typ == 'i32' else typ
        if op == 'array_numeric_not':
            return boolean_value(expr, line, following=following), 'Bool'
        if op == 'array_numeric_cast':
            from numeric_core import exact_cast
            typ, operand = expr[1:]
            value, source = infer_scalar_value(operand, line, following=following)
            if numeric_type(source) is None or not exact_cast(numeric_type(source), typ):
                fail(line, f'conversion non exacte vers {typ}')
            return f'(({FORMATS[typ].c_type})({value}))', 'Int' if typ == 'i32' else typ
        if op == 'array_numeric_operation':
            typ, operator, *operands = expr[1:]
            prepared = []
            for index, operand in enumerate(operands):
                value, actual = infer_scalar_value(operand, line, following=following)
                actual = numeric_type(actual)
                if actual is None or (FORMATS[actual].precision if index and operator in ('<<', '>>') else actual != typ):
                    fail(line, f'opérande numérique incompatible avec {typ}')
                member = temporary(FORMATS[actual].c_type)
                steps.append(f'{member} = {value};')
                prepared.append(member)
            return c_operation(operator, typ, *prepared), 'Int' if typ == 'i32' else typ
        if op == 'array_numeric_len':
            return f'((uint64_t)({expression(expr[1], line, following=following)}))', 'u64'
        if op == 'array_numeric_slice_len':
            receiver = expr[1]
            if receiver[0] == 'name' and receiver[1] in mutable_slices:
                check_access(receiver[1], line)
                view = value_place(receiver[1])
            else:
                mode = vector_view_mode(receiver)
                if mode is None:
                    fail(line, 'len exige une tranche de Vector')
                view = vector_view_value(receiver, line, mode, following=following)
            return f'((uint64_t)({view}).length)', 'u64'
        if expr[0] in ('array_handle_len', 'array_handle_option_status', 'array_handle_exchange_status', 'array_buffered_exchange_status'):
            return expression(expr, line, following=following), 'Int'
        if expr[0] == 'match_expr':
            return match_enum(expr[1], valued=True, following=following, boolean=None)
        if sync_signature(expr) is not None:
            value, typ = sync_call(expr, line, following=following)
            if typ == 'Void':
                fail(line, 'un appel Void ne fournit pas de valeur')
            return value, typ
        if (typ := vector_remove_type(expr)) is not None:
            return vector_remove_value(expr, line, following=following), typ
        if (mode := builtin_error_mode(expr)) is not None:
            return builtin_error_value(expr, mode, line, following=following), ERROR_VALUE_TYPES[mode]
        if expr[0] == 'utf8_error' and expr[1][0] == 'name' and expr[1][1] in utf8_match_results:
            subject = expr[1][1]
            storage = utf8_match_results[subject]
            family = wrapped_utf8_family_by_result[subject]
            mode = RESULT_ERROR_MODES[WRAPPED_UTF8_MODES[family]]
            return f'{storage}.status', ERROR_VALUE_TYPES[mode]
        if expr[0] in ('utf8_value', 'utf8_error') and expr[1][0] == 'name' and expr[1][1] in vector_match_payloads:
            mode, storage = vector_match_payloads[expr[1][1]]
            error = expr[0] == 'utf8_error'
            if error and mode in RESULT_ERROR_MODES:
                return f'{storage}.status', ERROR_VALUE_TYPES[RESULT_ERROR_MODES[mode]]
            if mode == 'capacity_result':
                fail(line, 'Ok(()) ne fournit pas de valeur')
            if not error and mode in ('int_try_push', 'byte_try_push'):
                fail(line, 'Ok(()) ne fournit pas de valeur')
            return f'{storage}.value', 'u8' if mode in ('byte_option', 'byte_replace', 'byte_try_push') else 'Int'

        if expr[0] == 'array_drop_result':
            inner = expr[1]
            expr = consumed_result_expression(inner, collection_types.get(inner[1][1]))
        if expr[0] == 'array_byte_literal':
            return byte_value(expr, line), 'u8'
        if expr[0] == 'array_integer_cast':
            return integer_cast_value(expr, line, following=following)
        if expr[0] == 'scope':
            return emit_region_block(expr[2], expr[3] if len(expr) > 3 else None, line, valued=True,
                                 construct='bloc', following=following, boolean=None)
        if expr[0] == 'if_expr':
            _, condition, yes, no = expr
            return conditional(condition, yes, no, line, valued=True, following=following, boolean=None)
        if expr[0] == 'value_match':
            return match_async_result(expr[1], line, following=following, boolean=None)
        if expr[0] == 'loop_expr':
            kind, value = emit_loop(expr[1].args[0], line, valued=True, following=following)
            if kind in SCALAR_TYPES:
                return value, SCALAR_TYPES[kind]
            fail(line, 'un résultat transféré de boucle async exige une liaison locale')
        if computed_await(expr):
            kind, prepared = emit_computed_transfer(expr[1], line, following=following)
            if kind == 'execution':
                mode = PLAIN_RETURN_JOINS.get(functions[prepared[3]].args[2])
                if mode is None:
                    fail(line, 'un résultat emprunté ou propriétaire exige une liaison dédiée')
                value, _, _ = execution_await(expr, line, prepared=prepared)
                return value, PLAIN_JOIN_TYPES[mode]
            if kind != 'task':
                fail(line, '.await exige une tâche ou un handle')
            mode, typ = functions[prepared[3]].args[2]
            result_type = SCALAR_RESULTS.get((mode, typ))
            if result_type is None:
                fail(line, '.await exige ici un résultat scalaire')
            value = await_task(expr, line, returns_value=True, prepared=prepared, scalar_type=result_type)
            return value, result_type
        signature = await_signature(expr)
        if signature and signature[0] in EXTRA_MODES:
            typ = signature[1]
            return await_task(expr, line, returns_value=True, scalar_type=typ), typ
        if op in ('array_index', 'array_replace'):
            place = expr if op == 'array_index' else ('array_index', expr[1], expr[2])
            name, _ = reference_array_path(place)
            element = array_elements.get(name)
            typ = next((typ for typ, spec in FORMATS.items() if spec.c_type == element and spec.mode in EXTRA_MODES), None)
            if typ is not None:
                value = (array_element(place, line)[0] if op == 'array_index' else
                         store_array(place, expr[3], line, following=following, returns_old=True))
                return value, typ
        family = wrapped_utf8_family(expr)
        if family is not None:
            return wrapped_utf8_value(expr, line, following=following), WRAPPED_UTF8_TYPES[family]
        if is_runtime_error(expr):
            return runtime_error_value(expr, line, following=following), 'runtime::Error'
        if (mode := plain_join_mode(expr)) is not None:
            return plain_join_value(expr, mode, line, following=following), PLAIN_JOIN_TYPES[mode]
        if is_boolean(expr):
            return boolean_value(expr, line), 'Bool'
        if (expr[0] == 'utf8_value' and expr[1][0] == 'name' and utf8_match_payloads.get(expr[1][1]) == 'u8'
                or indexed_vector_view_mode(expr) == 'vector_bytes' or is_byte_array_element(expr) or is_text_index(expr) or collection_index_type(expr) in ('Vector<u8>', 'String')
                or expr[0] == 'deref' and (expr[1] in byte_ref_bindings or reference_types.get(expr[1]) == 'u8')
                or expr[0] == 'name' and expr[1] in byte_bindings
                or expr[0] == 'await' and await_signature(expr) == ('byte', 'u8')):
            return byte_value(expr, line), 'u8'
        if (expr[0] == 'name' and expr[1] in char_bindings
                or expr[0] == 'await' and await_signature(expr) == ('char', 'char')
                or expr[0] == 'utf8_value' and expr[1][0] == 'name' and utf8_match_payloads.get(expr[1][1]) == 'char'):
            return char_value(expr, line, context='une expression char'), 'char'
        if (mode := vector_view_mode(expr)) is not None:
            return vector_view_value(expr, line, mode, following=following), SCALAR_TYPES[mode]
        if (mode := mutable_slice_mode(expr)) is not None:
            return mutable_slice_value(expr, line, mode, following=following), SCALAR_TYPES[mode]
        if is_static_text(expr):
            return static_text_value(expr, line), '&str'
        if is_static_byte_ref(expr):
            return static_byte_ref_value(expr, line), '&u8'
        return expression(expr, line, following=following), 'Int'

    def emit_print(statement, following):
        operand = statement.args[0]
        expr = ('name', operand) if statement.op == 'print' else operand
        if expr[0] == 'name' and references.get(expr[1]) == 'owned' and collection_types.get(expr[1]) in owned_aggregates:
            check_access(expr[1], statement.line)
            steps.append(f'cell_print(frame->{fields[expr[1]]});')
            return
        value, typ = infer_scalar_value(expr, statement.line, following=following)
        if typ == '&str':
            steps.append(f'text_print({value});')
        elif typ == 'char':
            steps.append(f'char_print({value});')
        elif typ == 'Int':
            steps.append(f'printf("%d\\n", {value});')
        elif SCALAR_MODES.get(typ) in EXTRA_MODES:
            steps.append(c_print(SCALAR_MODES[typ], value))
        else:
            fail(statement.line, 'print async exige un Int, un char ou une vue &str')

    def track_utf8_binding(statement, initializer, value, typ, body, index):
        if typ not in ASYNC_VIEW_TYPES:
            return
        loans = list(local_utf8_loans(initializer, value))
        name = statement.args[0]
        if statement.mutable:
            mutable_utf8_bindings.add(name)
        if loans or statement.mutable:
            utf8_view_loans[name] = tuple(loans)
            active_loans[id(loans)] = loans
            track_result(name, loans, body, index)
            if statement.mutable:
                scopes[-1][4][name] = loans, float('inf')

    def check_noncontinuing_initializer(statement, following):
        _, initializer = statement.args
        annotation = statement.annotation
        if (annotation is not None and expression_control_exit(initializer)
                and initializer[0] in ('if_expr', 'scope', 'value_match', 'loop_expr')):
            known_type = (annotation in SCALAR_MODES
                          or bool(scalar_array_layout(annotation)[0])
                          or bool(int_reference_layout(annotation, 'array_ref')))
            if known_type:
                # Only continuing paths have to supply the annotated value.
                # Still lower/check every actual exit: this is not a license
                # to skip lifetime, transfer, or cleanup verification.
                infer_scalar_value(initializer, statement.line, following=following)
                fail(statement.line, 'initialisation attendue sans continuation')

    def bind_scalar(statement, following, body, index):
        name, initializer = statement.args
        annotation = statement.annotation
        if (annotation is not None and annotation not in SCALAR_MODES) or statement.compact_transfer:
            fail(statement.line, 'prototype async : liaison Int copiable requise')
        family = wrapped_utf8_family(initializer)
        if family is not None and annotation not in (None, WRAPPED_UTF8_TYPES[family]):
            fail(statement.line, f'liaison UTF-8 : attendu {WRAPPED_UTF8_TYPES[family]}')
        if annotation in WRAPPED_UTF8_TYPES.values():
            value, typ = infer_scalar_value(initializer, statement.line, following=following)
            if typ != annotation:
                fail(statement.line, f'liaison UTF-8 : attendu {annotation}')
        elif annotation == '&u8':
            typ = '&u8'
            value = static_byte_ref_value(initializer, statement.line, following=following)
        elif annotation == '&str':
            typ = '&str'
            value = static_text_value(initializer, statement.line, following=following)
        elif SCALAR_MODES.get(annotation) in VECTOR_SLICE_ELEMENTS:
            typ = annotation
            value = vector_view_value(initializer, statement.line, SCALAR_MODES[typ], following=following)
        elif annotation is None:
            value, typ = infer_scalar_value(initializer, statement.line, following=following)
        elif SCALAR_MODES.get(annotation) in EXTRA_MODES:
            value, typ = infer_scalar_value(initializer, statement.line, following=following)
            if typ != annotation:
                fail(statement.line, f'annotation : attendu {annotation}, reçu {typ}')
        elif annotation == 'u8':
            typ = annotation
            value = byte_value(initializer, statement.line, following=following)
        elif annotation in ERROR_VALUE_MODES:
            typ = annotation
            value = builtin_error_value(initializer, ERROR_VALUE_MODES[typ], statement.line, following=following)
        elif annotation == 'runtime::Error':
            typ = annotation
            value = runtime_error_value(initializer, statement.line, following=following)
        elif SCALAR_MODES.get(annotation) in PLAIN_JOIN_TYPES:
            typ = annotation
            value = plain_join_value(initializer, SCALAR_MODES[typ], statement.line, following=following)
        elif annotation == 'char':
            typ = annotation
            value = char_value(initializer, statement.line, context='une liaison char', following=following)
        elif initializer[0] not in ('if_expr', 'value_match') and is_boolean(initializer) != (annotation == 'Bool'):
            expected = 'Bool' if statement.annotation == 'Bool' else 'Int'
            fail(statement.line, f'prototype async : liaison {expected} copiable requise')
        else:
            typ = annotation
            evaluate = boolean_value if typ == 'Bool' else expression
            value = evaluate(initializer, statement.line, following=following)
        if typ.startswith('Result<') and (name == '_' or not has_future_value_use(name, body[index + 1:])):
            fail(statement.line, f"résultat faillible '{name}' sans usage explicite")
        member = declare(name, statement.line)
        if not statement.mutable and (key := known_map_key(initializer)) is not None:
            immutable_integer_members[member] = key
        record_inline_type(name, typ)
        track_utf8_binding(statement, initializer, value, typ, body, index)
        if typ in ('&str', '&u8') and not statement.mutable and is_literal_utf8_storage(initializer):
            static_utf8_bindings.add(name)
        if statement.mutable:
            mutable.add(name)
        steps.append(f'frame->{member} = {value};')

    def has_future_value_use(name, nodes):
        for node in nodes:
            if node.op in ('var', 'assign'):
                if mentions(node.args[1], name):
                    return True
                if node.args[0] == name:
                    return False
            elif mentions(node, name):
                return True
        return False

    def mentions(value, name):
        if isinstance(value, (list, tuple)):
            return any(mentions(item, name) for item in value)
        if hasattr(value, 'args'):
            return mentions(value.args, name)
        return value == name

    def await_signature(expr):
        if expr[0] != 'await':
            return None
        operand = expr[1]
        if operand[0] == 'call':
            signature = sync_signature(operand)
            nominal = signature[1] if signature in task_sync_types else operand[1]
        elif operand[0] == 'name' and tasks.get(operand[1]) is not None:
            nominal = tasks[operand[1]][3]
        elif operand[0] == 'name' and selections.get(operand[1]) is not None:
            nominal = selections[operand[1]].branches[0][3]
        else:
            return None
        return functions[nominal].args[2] if nominal in functions else None

    def await_result_mode(expr):
        signature = await_signature(expr)
        return signature[0] if signature else None

    def release_results(local_refs, *, before=None):
        for loans, last_use in local_refs.values():
            if before is None or before > last_use:
                active_loans.pop(id(loans), None)

    def contains_control_exit(value):
        if isinstance(value, (list, tuple)):
            return any(contains_control_exit(item) for item in value)
        return hasattr(value, 'op') and (
            value.op in ('break', 'continue', 'return') or contains_control_exit(value.args)
        )

    def guaranteed_break_prefix(following):
        for index, statement in enumerate(following):
            if contains_control_exit(statement.args):
                break
            if statement.op == 'break':
                return following[:index + 1]
            if statement.op in ('continue', 'return'):
                break
        return None

    def utf8_loop_live(body, name, exit_live, *, owned=False):
        head = False
        while True:
            incoming = utf8_value_live(body, name, head, loop_head=head, loop_exit=exit_live, owned=owned)
            if body and body[0].op == 'while_check':
                incoming |= exit_live
            if incoming == head:
                return head
            head = incoming

    def owned_expression_live(expr, name, after=False):
        if expr is None:
            return after
        op = expr[0]
        if op == 'scope':
            return utf8_value_live(expr[2], name, after, owned=True)
        if op == 'if_expr':
            condition, yes, no = expr[1:]
            def branch_live(branch):
                return (owned_expression_live(branch, name, after) if isinstance(branch, tuple)
                        else utf8_value_live(branch, name, after, owned=True))
            return mentions(condition, name) or branch_live(yes) or branch_live(no)
        if op == 'value_match':
            return utf8_value_live(expr[1], name, after, owned=True)
        if op == 'loop_expr':
            return utf8_loop_live(expr[1].args[0], name, after, owned=True)
        if op == 'call':
            operands = expr[2]
        elif op == 'method_call':
            operands = (expr[1], *expr[3])
        elif op == 'arithmetic':
            operands = expr[2:]
        elif op == 'await':
            operands = (expr[1],)
        else:
            return after or mentions(expr, name)
        live = after
        for operand in reversed(operands):
            live = owned_expression_live(operand, name, live)
        return live

    def utf8_value_live(statements, name, live_after=False, *, loop_head=None, loop_exit=None, owned=False):
        live = live_after
        for statement in reversed(statements):
            if not hasattr(statement, 'op'):
                live = owned_expression_live(statement, name, live) if owned else live or mentions(statement, name)
            elif statement.op == 'assign' and statement.args[0] == name:
                rhs = statement.args[1]
                replacement = (rhs[0] in ('move', 'loop_expr')
                               or rhs[0] == 'scope' and ends_in_transfer(rhs[2])
                               or has_transfer_result(rhs)
                               or rhs[0] == 'await' and (computed_await(rhs) or await_result_mode(rhs) == 'owned'))
                live = mentions(rhs, name) or owned and not replacement
            elif owned and statement.op == 'var' and statement.args[0] == name:
                live = mentions(statement.args[1], name)
            elif statement.op == 'return':
                live = mentions(statement.args, name)
            elif statement.op == 'continue' and loop_head is not None:
                live = loop_head
            elif statement.op == 'break' and loop_exit is not None:
                live = loop_exit or mentions(statement.args, name)
            elif statement.op == 'if':
                condition, yes, no = statement.args
                live = (mentions(condition, name)
                        or utf8_value_live(yes, name, live, loop_head=loop_head, loop_exit=loop_exit, owned=owned)
                        or utf8_value_live(no, name, live, loop_head=loop_head, loop_exit=loop_exit, owned=owned))
            elif statement.op == 'scope':
                live = utf8_value_live(statement.args[1], name, live,
                                       loop_head=loop_head, loop_exit=loop_exit, owned=owned)
            elif statement.op in ('loop', 'while'):
                live = utf8_loop_live(statement.args[0], name, live, owned=owned)
            else:
                live = live or mentions(statement.args, name)
        return live

    def utf8_current_live(self_tail, name, *, depth=None, earlier=(), owner_depth=None, owned=False):
        if self_tail is None:
            return True  # The surrounding expression has not supplied its continuation.
        if depth is None:
            depth = len(scopes) - 1
        loop = next((entry for entry in reversed(loops) if depth >= entry['depth']), None)
        tail = [*earlier, *self_tail]
        reached = depth
        def append_arguments(parent):
            if owned:
                for argument_depth, remaining in reversed(argument_tails):
                    if argument_depth == parent:
                        tail.extend(remaining)
        for parent, continuation in reversed(lexical_tails):
            if parent >= reached:
                continue
            if parent != reached - 1 or loop is not None and parent < loop['depth']:
                break
            append_arguments(parent)
            tail.extend(continuation)
            reached = parent
        if owned:
            # An expression used as an argument may not receive a lexical
            # continuation. The enclosing statement still has a known tail.
            while reached > 0 and (loop is None or reached > loop['depth']):
                parent = reached - 1
                if parent not in statement_tails:
                    break
                append_arguments(parent)
                tail.extend(statement_tails[parent])
                reached = parent
        if loop is not None:
            head = loop['utf8_head_live'].get(name, False)
            exit_live = loop['utf8_exit_live'].get(name, False)
            if owned:
                exit_live = utf8_value_live(loop['following'] or (), name, owned=True)
                head = utf8_loop_live(loop['body'], name, exit_live, owned=True)
            return utf8_value_live(tail, name, head, loop_head=head, loop_exit=exit_live, owned=owned)
        if owner_depth is not None and reached > owner_depth:
            return True
        return utf8_value_live(tail, name, owned=owned)

    def release_statement_loans(following, *, depth=None, earlier=(), utf8_only=False):
        if utf8_only and not mutable_utf8_bindings and not any(
                isinstance(key, tuple) and key[0] == 'stored_field'
                and references.get(key[1]) == 'owned' for key in active_loans):
            return
        loop = loops[-1] if depth is None and loops else None
        if depth is None:
            depth = len(scopes) - 1
        continuation = [(depth, following)]
        for parent, tail in reversed(lexical_tails):
            if parent >= depth:
                continue
            # Expression and iteration boundaries need separate continuations.
            if parent != depth - 1:
                break
            continuation.append((parent, tail))
            depth = parent
        if loop is not None and not utf8_only:
            iteration_tail = [
                statement for depth, tail in continuation if depth >= loop['depth']
                for statement in tail
            ]
            if (prefix := guaranteed_break_prefix(iteration_tail)) is not None:
                release_loop_exit_loans(loop, earlier=(*earlier, *prefix))
        tails = [earlier]
        for depth, tail in continuation:
            tails.append(tail)
            local_refs = scopes[depth][4]
            for name, (loans, _) in local_refs.items():
                if name.startswith('\0match:'):
                    continue  # The whole arm reserves its subject, even after the last field use.
                if utf8_only or name in mutable_utf8_bindings:
                    continue
                if not any(mentions(tail, name) for tail in tails):
                    active_loans.pop(id(loans), None)
        # A last lexical use is not a last use through a live carrier loan.
        # Iterate because retiring one stored reborrow can release another.
        while True:
            retired = []
            for key in list(active_loans):
                if not (isinstance(key, tuple) and key[0] == 'stored_field'):
                    continue
                _, holder, field_path = key
                borrowed = any(loan_root(target) == holder
                    and mode not in ('storage', 'shared_target', 'stored_mut_target')
                    and (not isinstance(target, tuple) or all(
                        left is None or right is None or left == right
                        for left, right in zip(field_path, target[1])))
                    for other, loans in active_loans.items() if other != key
                    for target, mode in loans)
                if references.get(holder) == 'owned' and not borrowed and not utf8_current_live(
                        following, holder, depth=continuation[0][0], earlier=earlier, owned=True):
                    retired.append(key)
            if not retired:
                break
            for key in retired:
                del active_loans[key]
                guarded_receipts.pop(key, None)
        current_depth = continuation[0][0]
        for owner_depth, scope in enumerate(scopes[:current_depth + 1]):
            for name, (loans, _) in scope[4].items():
                if name in mutable_utf8_bindings and not utf8_current_live(
                        following, name, depth=current_depth, earlier=earlier, owner_depth=owner_depth):
                    active_loans.pop(id(loans), None)

    def release_loop_exit_loans(loop, *, earlier=()):
        following = loop['following']
        if following is not None:
            release_statement_loans(following, depth=loop['depth'] - 1, earlier=earlier)

    def track_result(name, loans, body, index):
        last_use = next((position for position in range(len(body) - 1, index, -1)
                         if mentions(body[position], name)), index)
        scopes[-1][4][name] = loans, last_use

    def receive_await_result(statement, body, index, *, export_name=None):
        name, initializer = statement.args
        line = statement.line
        prepared = None
        mode = await_result_mode(initializer)
        if computed_await(initializer):
            kind, prepared = emit_computed_transfer(initializer[1], line)
            if kind == 'execution':
                if (statement.annotation not in (None, *PLAIN_JOIN_TYPES.values())
                        and not statement.annotation.startswith('Result<runtime::AsyncHandle<')
                        or statement.compact_transfer):
                    fail(line, 'un résultat de handle exige une nouvelle liaison locale')
                check_new_name(name, line)
                bind_execution_result(name, execution_await(initializer, line, prepared=prepared), body, index,
                                      export_name=export_name, annotation=statement.annotation,
                                      mutable_result=statement.mutable)
                return True
            if kind != 'task':
                fail(line, '.await exige une tâche inactive')
            mode = functions[prepared[3]].args[2][0]
        elif mode not in ('ref', 'mut', 'owned', 'array', 'async_execution'):
            return False
        if mode == 'async_execution':
            signature = functions[prepared[3]].args[2] if prepared is not None else await_signature(initializer)
            if statement.annotation not in (None, signature[1]) or statement.compact_transfer:
                fail(line, 'annotation incompatible avec le AsyncHandle retourné')
            check_new_name(name, line)
            executions[name] = await_task(initializer, line, returns_value=True, prepared=prepared, execution=True)
            scopes[-1][0][name] = None
            return True
        if mode == 'array':
            operand = initializer[1]
            nominal = prepared[3] if prepared is not None else (
                operand[1] if operand[0] == 'call' else selections[operand[1]].branches[0][3]
                if operand[1] in selections else tasks[operand[1]][3])
            shape, element = scalar_array_layout(functions[nominal].args[2][1])
            if statement.compact_transfer:
                fail(line, 'un résultat de tableau async exige une liaison locale')
            check_new_name(name, line)
            source = await_task(initializer, line, returns_value=True, array_shape=shape, prepared=prepared)
            bind_transferred_value(name, 'array', (source, shape, element), statement)
            return True
        if mode in ('runtime_error', *ERROR_VALUE_TYPES, 'scalar', 'byte', 'char', *EXTRA_MODES, *PLAIN_JOIN_TYPES, *ASYNC_CAPTURE_VIEW_MODES, *UTF8_VALUE_RESULT_FAMILIES):
            typ = functions[prepared[3]].args[2][1]
            annotation = SCALAR_RESULTS.get((mode, typ), typ)
            if statement.annotation not in (None, annotation) or statement.compact_transfer:
                fail(line, f'prototype async : liaison {typ} copiable requise')
            if annotation.startswith('Result<') and (name == '_' or not has_future_value_use(name, body[index + 1:])):
                fail(line, f"résultat faillible '{name}' sans usage explicite")
            value = await_task(initializer, line, returns_value=True, prepared=prepared, scalar_type=annotation)
            member = declare(name, line)
            record_inline_type(name, annotation)
            track_utf8_binding(statement, initializer, value, annotation, body, index)
            if statement.mutable:
                mutable.add(name)
            steps.append(f'frame->{member} = {value};')
            return True
        if statement.annotation is not None or statement.compact_transfer:
            fail(line, 'un résultat async emprunté ou transféré exige une liaison sans annotation')
        check_new_name(name, line)
        if mode in ('owned', *JOIN_PAYLOADS):
            require_owned_result_use(statement, body, index, export_name)
        if mode in JOIN_PAYLOADS:
            value = await_task(initializer, line, returns_value=True, joined=True, prepared=prepared)
            join_results[name] = value, owned_wrapper_payload(mode, functions[prepared[3]].args[2][1]), None
            storage_bindings[name] = storage_of(value)
            scopes[-1][0][name] = None
            return True
        if mode == 'owned':
            value = await_task(initializer, line, returns_value=True, owned=True, prepared=prepared)
        else:
            if mode not in ('ref', 'mut'):
                fail(line, '.await d’une tâche Void ne fournit pas de valeur')
            value, loans, mode = await_task(initializer, line, returns_value=True, borrow=True, prepared=prepared)
        member = declare(name, line)
        references[name] = mode
        if mode == 'owned':
            received_type = owned_result_types.get(value, 'Int')
            storage_bindings[name] = storage_of(value)
            move_stored_fields(value, name)
            if received_type in reference_structs:
                reference_types[name] = received_type
            if received_type != 'Int':
                collection_types[name] = received_type
            scopes[-1][0][name] = None
            if statement.mutable:
                mutable.add(name)
        else:
            reference_types[name] = awaited_reference_types[value]
            if statement.mutable:
                mutable.add(name)
            track_result(name, loans, body, index)
            received_refs[name] = loans
        steps.append(f'frame->{member} = {value};')
        return True

    def set_reference(statement, following):
        if (statement.op in ('call', 'array_statement')
                and statement.args[0][:2] in (('array_hashmap_method', 'insert'), ('array_hashmap_method', 'remove'))):
            result, payload, _ = emit_hashmap_operation(statement.args[0], statement.line)
            if payload == 'map_owned_option':
                steps.append(f'if ({result}.status == 0) cell_drop(crust_map_result_handle(&{result}));')
                clear_stored_fields(result)
            else:
                steps.append(f'(void){result};')
            return True
        if statement.op in ('call', 'array_statement') and sync_signature(statement.args[0]) is not None:
            if sync_signature(statement.args[0])[1].startswith('Result<'):
                fail(statement.line, 'résultat faillible sans usage explicite')
            if statement.args[0][0] == 'method_call' and sync_signature(statement.args[0]) != ('void', 'Void'):
                fail(statement.line, 'résultat de méthode sans receveur explicitement utilisé')
            sync_call(statement.args[0], statement.line, following=following)
            return True
        if statement.op in ('call', 'array_statement'):
            expr = statement.args[0]
            if expr[0] == 'array_buffered_exchange_take':
                name = expr[1][1]
                record = handle_exchange_record(name, statement.line)
                arm = expr[2][1]
                if record[1] != 'rejected_allocation' or not (arm == 1 or arm == -1 and expr[3] == ('int', 0)):
                    fail(statement.line, 'un motif _ ne peut pas écarter une allocation possédée')
                consume_owned_join(name, statement.line)
                clear_stored_fields(record[0])
                steps.append(f'{record[0]}.value = NULL;')
                return True
            if expr[0] == 'array_handle_option_empty':
                name = expr[1][1]
                record = handle_option_record(name, statement.line)
                consume_owned_join(name, statement.line)
                clear_stored_fields(record[0])
                steps.append(f'{record[0]}.value = NULL;')
                return True
            if vector_remove_type(expr) is not None:
                vector_remove_value(expr, statement.line, following=following)
                return True
            if operation := vector_result_operation(expr):
                if operation[0] not in ('int_option', 'byte_option'):
                    fail(statement.line, 'résultat faillible sans usage explicite')
                vector_result_value(operation, expr, statement.line, following=following)
                return True
        if statement.op != 'call':
            return False
        call = statement.args[0]
        if call[0] != 'method_call' or call[1][0] != 'name':
            return False
        _, (_, receiver), method, arguments = call
        collection = collection_types.get(receiver)
        if collection in ('String', 'Vector<Int>', 'Vector<u8>', *HANDLE_VECTORS, *INLINE_VECTOR_ELEMENTS) and following is not None:
            # A parent-scope view can end in the preceding nested statement.
            # Keep uses in this call alive while expiring those earlier loans
            # before reserving the receiver for its arguments.
            release_statement_loans(following, earlier=(statement,))
        if collection == 'String' and method in ('pop', 'replace_byte', 'replace_bytes'):
            wrapped_utf8_value(call, statement.line, following=following)
            return True
        if collection == 'String' and method == 'merge':
            line = statement.line
            if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable) or len(arguments) != 1:
                fail(line, 'merge exige un String mutable et un argument')
            check_access(receiver, line, write=True)
            reservation = [(receiver, 'mut')]
            active_loans[id(reservation)] = reservation
            try:
                argument = arguments[0]
                if argument[0] == 'down':
                    source = argument[1]
                    require_local_async_value(source, line)
                    if references.get(source) != 'owned' or collection_types.get(source) != 'String':
                        fail(line, 'merge exige une allocation String')
                    kind, value = export_async_value(source, (), line)
                elif argument[0] == 'transfer':
                    operand = argument[1]
                    if operand[0] == 'await':
                        value = await_task(operand, line, returns_value=True, owned=True)
                        kind = 'owned'
                    else:
                        kind, value = emit_computed_transfer(operand, line)
                else:
                    fail(line, 'merge exige un transfert explicite -> String')
                if kind != 'owned' or owned_result_types.get(value) != 'String':
                    fail(line, 'merge exige une allocation String')
            finally:
                del active_loans[id(reservation)]
            release_statement_loans(following)
            check_access(receiver, line, write=True)
            steps.extend((f'string_push_str(frame->{fields[receiver]}, string_view({value}));',
                          f'cell_drop({value});', f'{value} = NULL;'))
            return True
        if collection in INLINE_VECTOR_ELEMENTS and method == 'push':
            line = statement.line
            element, layout = inline_vector_layout(collection, line)
            if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable) or len(arguments) != 1:
                fail(line, 'push exige un Vector mutable et un argument')
            if arguments[0][0] not in ('down', 'transfer'):
                fail(line, 'push de structure exige un transfert -> explicite')
            check_access(receiver, line, write=True)
            loan = [(receiver, 'mut')]
            active_loans[id(loan)] = loan
            try:
                if arguments[0][0] == 'down':
                    require_local_async_value(arguments[0][1], line)
                    kind, incoming = export_async_value(arguments[0][1], (), line)
                else:
                    incoming = sync_owned_value(arguments[0][1], line, following=following)
                    kind = 'owned'
                if kind != 'owned' or owned_result_types.get(incoming) != element or not storage_of(incoming) & implicit_stacks:
                    fail(line, f'push exige une valeur locale {element}, pas une allocation A<T>')
            finally:
                del active_loans[id(loan)]
            release_statement_loans(following)
            check_access(receiver, line, write=True)
            data = f'{incoming}->fields' if layout else '&(int){0}'
            if any(kind.startswith('A<') for _, kind in layout):
                depth = next((index for index in reversed(range(len(scopes))) if receiver in scopes[index][0]), 0)
                leaving = {name for scope in scopes[depth + 1 if references.get(receiver) == 'owned' else 0:]
                           for name in scope[0] if name in local_pools}
                children = {origin for held in owned_storage_fields(incoming).values() for origin, _ in held}
                if children & leaving:
                    fail(line, 'transfert refusé : le pool du champ propriétaire ne survit pas au vecteur')
            retain_vector_payload(receiver, incoming)
            if any(kind.startswith('A<') for _, kind in layout):
                steps.extend((f'vector_push_owned_value(frame->{fields[receiver]}, {incoming});',
                              f'cell_release_storage({incoming}, 0);', f'{incoming} = NULL;'))
            else:
                steps.extend((f'vector_push(frame->{fields[receiver]}, {data});',
                              f'cell_drop({incoming});', f'{incoming} = NULL;'))
            clear_stored_fields(incoming)
            return True
        if is_handle_vector(collection) and method == 'push':
            line = statement.line
            if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable) or len(arguments) != 1:
                fail(line, 'push exige un Vector mutable et un argument')
            check_access(receiver, line, write=True)
            preparation = [(receiver, 'mut')]
            active_loans[id(preparation)] = preparation
            try:
                argument = arguments[0]
                if argument[0] == 'down':
                    require_local_async_value(argument[1], line)
                    kind, incoming = export_async_value(argument[1], (), line)
                elif argument[0] == 'transfer':
                    incoming = sync_owned_value(argument[1], line, following=following)
                    kind = 'owned'
                else:
                    fail(line, 'push de A<Int> exige un transfert explicite ->')
                if kind != 'owned' or owned_result_types.get(incoming, 'Int') != handle_vector_element(collection):
                    fail(line, f'push de {collection} exige une allocation {handle_vector_element(collection)}')
                if storage_of(incoming) & implicit_stacks:
                    fail(line, 'une case A<Int> exige une allocation de pool')
                depth = next((index for index in reversed(range(len(scopes))) if receiver in scopes[index][0]), 0)
                require_durable_storage(incoming, depth + 1 if references.get(receiver) == 'owned' else 0, line)
                if references.get(receiver) != 'owned' and (node.field_effect_summary is None or not node.field_effect_summary.complete):
                    fail(line, 'push dans un vecteur injecté : contrat de terminaison incomplet')
            finally:
                del active_loans[id(preparation)]
            release_statement_loans(following)
            check_access(receiver, line, write=True)
            key = ('owned_storage', receiver, ('items',))
            held = [*active_loans.get(key, ()), *((origin, 'storage') for origin in storage_of(incoming))]
            install_field_change(key, list(dict.fromkeys(held)))
            retain_vector_payload(receiver, incoming)
            steps.extend((f'vector_push(frame->{fields[receiver]}, &{incoming});', f'{incoming} = NULL;'))
            clear_stored_fields(incoming)
            return True
        if collection in ('Vector<Int>', 'Vector<u8>') and method == 'push':
            line = statement.line
            if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable) or len(arguments) != 1:
                fail(line, 'push exige un Vector mutable et un argument')
            check_access(receiver, line, write=True)
            preparation = [(receiver, 'mut')]
            active_loans[id(preparation)] = preparation
            try:
                value = (expression(arguments[0], line) if collection == 'Vector<Int>'
                         else byte_value(arguments[0], line, context='push'))
            finally:
                del active_loans[id(preparation)]
            check_access(receiver, line, write=True)
            item = temporary('int' if collection == 'Vector<Int>' else 'uint8_t')
            steps.append(f'{item} = {value};')
            steps.append(f'vector_push(frame->{fields[receiver]}, &{item});')
            return True
        if collection == 'String' and method in ('push', 'push_str'):
            line = statement.line
            if not (references.get(receiver) == 'mut' or references.get(receiver) == 'owned' and receiver in mutable) or len(arguments) != 1:
                fail(line, f'{method} exige un String mutable et un argument')
            check_access(receiver, line, write=True)
            preparation = [(receiver, 'mut')]
            active_loans[id(preparation)] = preparation
            try:
                value = (char_value(arguments[0], line, context=method) if method == 'push'
                         else static_text_value(arguments[0], line))
            finally:
                del active_loans[id(preparation)]
            argument_loans = list(local_utf8_loans(arguments[0], value)) if method == 'push_str' else []
            active_loans[id(argument_loans)] = argument_loans
            try:
                release_statement_loans(following)
                check_access(receiver, line, write=True)
                steps.append(f'string_{method}(frame->{fields[receiver]}, {value});')
            finally:
                del active_loans[id(argument_loans)]
            return True
        if method != 'set' or receiver not in references or receiver in collection_types:
            return False
        line = statement.line
        if (references[receiver] != 'mut'
                and not (references[receiver] == 'owned' and receiver in mutable)) or len(arguments) != 1:
            fail(line, 'set exige un emprunt mutable ou une allocation mutable, et un argument Int')
        value = byte_value(arguments[0], line) if reference_types.get(receiver) == 'u8' else expression(arguments[0], line)
        check_access(receiver, line, write=True)
        steps.append(f'{value_place(receiver)} = {value};')
        return True

    for parameter_index, (parameter, mode, typ) in enumerate(parameters):
        member = declare(parameter, node.line)
        if mode == 'async_execution':
            signature = public_async_signature(typ, aggregate_layouts, allow_borrowed=True)
            if signature is None:
                fail(node.line, 'paramètre AsyncHandle : type de résultat non raccordé')
            enable_threads()
            handle = f'(&frame->{member})'
            execution_pools[handle] = frozenset({parameter_index})
            blocking_executions.add(handle)
            result_loans = ([(f'\0async-handle-result:{parameter}', signature[0])]
                            if signature[0] in ('ref', 'mut') else [])
            loans = list(result_loans)
            active_loans[id(loans)] = loans
            executions[parameter] = handle, signature == ('scalar', 'Int'), loans, typ, result_loans, ()
            scopes[0][0][parameter] = None
        if parameter_index in local_parameters:
            origin = '\0local-input-' + parameter
            implicit_stacks.add(origin)
            pointer = f'frame->{member}' + (f'.{JOIN_CELLS[mode]}' if mode in JOIN_CELLS else '')
            if mode in ('ref', 'mut') and typ in struct_layouts:
                pointer += '.root'
            local_pools[origin] = f'(*({pointer}->source))'
            storage_bindings[parameter] = frozenset({origin})
        if mode in ('array', *ARRAY_BORROWS):
            shape, element = scalar_array_layout(typ)
            arrays[parameter] = shape or int_reference_row(typ, mode)
            array_elements[parameter] = element or 'int'
        if mode == 'array':
            scopes[0][0][parameter] = None
        if mode in JOIN_PAYLOADS:
            join_results[parameter] = f'frame->{member}', owned_wrapper_payload(mode, typ), None
            owned_result_types[f'frame->{member}'] = wrapper_content_type(mode, typ)
        if mode in PLAIN_JOIN_TYPES:
            join_results[parameter] = f'frame->{member}', PLAIN_JOIN_FIELDS[mode], None
        if mode in ('owned', *JOIN_PAYLOADS):
            scopes[0][0][parameter] = None
    captures = tuple(fields.values())
    steps = []
    if output_plan and output_plan.destination:
        from async_local_placement import result_constructors
        destination = '\0local-output'
        implicit_stacks.add(destination)
        local_pools[destination] = '(*frame->result_storage)'
        local_inputs = {parameter: typ for index, (parameter, _, typ) in enumerate(parameters) if index in local_parameters}
        local_inputs.update(inline_vector_placement_inputs())
        constructors = result_constructors(('scope', None, body), sync_contracts, local_inputs, returns=True,
                                           async_functions=functions)
        for constructor in constructors:
            local_destinations[id(constructor)] = destination
    resume_point = 0
    returned = False
    statements = iter(enumerate(body))
    for index, statement in statements:
        statement_tails[0] = body[index + 1:]
        release_results(scopes[-1][4], before=index)
        release_statement_loans(body[index:], utf8_only=True)
        op, args, line = statement.op, statement.args, statement.line
        if returned:
            fail(line, 'instruction après retour async')
        try:
            if op == 'yield':
                suspend()
            elif op == 'var' and statement.utf8_match_subject:
                returned = match_statement(statement, (item for _, item in statements), following=body[index + 3:])
            elif op == 'var':
                check_noncontinuing_initializer(statement, body[index + 1:])
                if bind_array(statement, following=body[index + 1:]):
                    continue
                if receive_await_result(statement, body, index):
                    continue
                if bind_special(statement, body, index):
                    continue
                bind_scalar(statement, body[index + 1:], body, index)
            elif set_reference(statement, body[index + 1:]):
                pass
            elif op == 'assign':
                assign(*args, line, following=body[index + 1:])
            elif op == 'field_store':
                store_struct_field(*args, line, following=body[index + 1:])
            elif op in ('array_store', 'array_deref_store'):
                store_array(*args, line, following=body[index + 1:])
            elif op == 'array_statement' and args[0][0] == 'array_numeric_compound':
                numeric_compound_store(args[0], line, body[index + 1:])
            elif op == 'array_statement' and args[0][0] == 'array_swap':
                swap_array(args[0], line, following=body[index + 1:])
            elif op == 'scope':
                returned = emit_block(statement, body[index + 1:])
            elif op == 'if':
                returned = conditional(*args, line, valued=False, following=body[index + 1:])
            elif op == 'match':
                returned = match_enum(statement, valued=False, following=body[index + 1:])
            elif op in ('loop', 'while'):
                returned = emit_loop(args[0], line, following=body[index + 1:])
            elif op in ('break', 'continue'):
                loop_exit(op, args[0], line)
            elif op in ('print', 'print_expr'):
                emit_print(statement, body[index + 1:])
            elif op == 'await_statement':
                await_task(args[0], line, returns_value=False)
            elif drop_async_binding(statement):
                pass
            elif op == 'return' or (op == '<-' and not statement.terminated and index == len(body) - 1):
                emit_return(args[0] if op == 'return' else ('move', args[0]), line)
                returned = True
            else:
                fail(line, f'prototype async : instruction {op} non prise en charge')
        except NoAsyncContinuation:
            returned = True
            break
    if not returned:
        if returns_value:
            fail(node.line, 'retour Int requis dans la fonction async' if not (returns_owned or returns_join) else
                 'retour transféré requis dans la fonction async')
        discard_pending(node.line)
        steps.append('return TASK_STEP_RETURN;')
    member_types = {member: (array_elements[name] if name in arrays and parameter_modes.get(name) not in ARRAY_BORROWS
                             else capture_type(parameter_modes.get(
                                 name, references.get(name, inline_scalar_mode(name))), reference_types.get(name, collection_types.get(name))))
                    for name, member in fields.items()}
    array_members = {fields[name]: shape for name, shape in arrays.items() if parameter_modes.get(name) not in ARRAY_BORROWS}
    members = ''.join(
        f'    {ctype} {member}{array_dimensions(array_members.get(member, ()))};\n'
        for member, ctype in member_types.items()
    )
    frame_slots[node.args[0]] = task_holder_count
    members += ''.join(internal_members)
    if node.result_storage:
        members += '    Source *result_storage;\n'
    members += ''.join(f'    Cell *capture_cell_{index};\n'
                       for index in sorted(node.cell_reference_parameters))
    members += ''.join(f'    Cell *{member};\n' for member,_ in initial_field_cells.values())
    if returns_value:
        members += f'    {result_ctype} result{array_dimensions(returns_array)};\n'
    if returns_execution:
        members += '    int result_ready;\n'
    dispatch = ''.join(f'    case {point}: goto resume_{point};\n'
                       for point in range(1, resume_point + 1))
    instructions = '\n'.join(f'    {step}' for step in steps)
    result_copy = (f'    *({result_ctype} *)out = (({prefix}_state *)task)->result;'
                   if returns_value else '    (void)task;\n    (void)out;')
    if returns_execution:
        result_copy += f'\n    (({prefix}_state *)task)->result_ready = 0;'
    if returns_array:
        result_copy = (f'    {prefix}_state *frame = ({prefix}_state *)task;\n'
                       '    memcpy(out, frame->result, sizeof frame->result);') if all(returns_array) else (
                           '    (void)task;\n    (void)out;')
    arguments = ''.join(', ' + declaration for declaration in task_capture_declarations(node, structures=struct_layouts))
    initialize = ''
    if returns_execution:
        initialize += '    frame->result_ready = 0;\n'
    if node.result_storage:
        initialize += '    frame->result_storage = result_storage;\n'
    for i, ((parameter, mode, _), member) in enumerate(zip(parameters, captures)):
        if mode == 'array':
            if all(arrays[parameter]):
                initialize += f'    memcpy(frame->{member}, capture_{i}, sizeof frame->{member});\n'
            else:
                initialize += f'    (void)capture_{i};\n'
        else:
            initialize += f'    frame->{member} = capture_{i};\n'
        if i in node.cell_reference_parameters:
            initialize += f'    frame->capture_cell_{i} = capture_cell_{i};\n'
    for (root,_), (member,offset) in initial_field_cells.items():
        initialize += f'    frame->{member} = cell_load_ref(frame->{fields[root]}, {offset});\n'
    inactive_cleanup = []
    for name, mode, typ in reversed(parameters):
        cell = f'frame->{fields[name]}'
        if mode == 'async_execution':
            inactive_cleanup.append(f'task_abandon_async(&{cell});')
            continue
        if mode in JOIN_CELLS:
            cell += f'.{JOIN_CELLS[mode]}'
        elif mode != 'owned':
            continue
        present = (f'frame->{fields[name]}.status != 0 && ' if mode == 'buffered_handle_exchange'
                   and exchange_optional(typ) else '')
        inactive_cleanup.append(f'if ({present}{cell}) cell_drop({cell});')
    members += '    size_t cleanup_path;\n'
    initialize += '    frame->cleanup_path = 0;\n'
    cases = []
    for index, path in enumerate((inactive_cleanup, *cleanup_paths)):
        cases.append(f'    case {index}:\n')
        cases.extend(f'        {step}\n' for step in path)
        cases.append('        break;\n')
    cleanup = ('    switch (frame->cleanup_path) {\n' + ''.join(cases)
               + '    default: fail("invalid async cleanup path");\n    }\n')
    if returns_execution:
        cleanup += '    if (frame->result_ready) task_abandon_async(&frame->result);\n'
    suspended_checks, suspended_cleanup = [], []
    for point, (path, children, blocked, select_checks) in sorted(suspended_paths.items()):
        child_checks = [f'task_owned_discardable({child})' for child in children]
        condition = '0' if blocked else ' && '.join((*child_checks, *select_checks)) or '1'
        suspended_checks.append(f'    case {point}: return {condition};\n')
        suspended_cleanup.append(f'    case {point}:\n')
        if blocked:
            suspended_cleanup.append('        fail("suspended cleanup has an outstanding execution handle");\n')
        else:
            suspended_cleanup.extend(f'        {step}\n' for step in path)
        suspended_cleanup.append('        break;\n')
    layout_definitions = []
    for key, symbol in local_layouts.items():
        typ, variant = key if isinstance(key, tuple) else (key, '')
        layout = owned_enums[typ][variant] if variant else pool_structures[typ]
        tag = tuple(owned_enums[typ]).index(variant) if variant else 0
        offsets = ', '.join(structure_offset(layout, i) for i in range(len(layout))) or '0'
        kinds = ', '.join(str(field_kind(field_type))
                          for _, field_type in layout) or '0'
        layout_definitions.append(f'static const size_t {symbol}_offsets[] = {{{offsets}}};\n'
            f'static const unsigned char {symbol}_kinds[] = {{{kinds}}};\n'
            f'static const Source {symbol} = {{.enum_name="{typ}", .arm_name="{variant}", .arm_tag={tag}, '
            f'.field_count={len(layout)}, .field_offsets={symbol}_offsets, .field_kinds={symbol}_kinds}};')
    return '\n'.join(layout_definitions) + f"""
typedef struct {{
    CrustTask task;
    CrustTaskSlot slot;
    size_t pc;
{members}}} {prefix}_state;

static CrustTaskStep {prefix}_resume(CrustTask *task) {{
    {prefix}_state *frame = ({prefix}_state *)task;
    switch (frame->pc) {{
    case 0: break;
{dispatch}    default:
        fail("invalid async resume point");
        return TASK_STEP_RETURN;
    }}
{instructions}
}}

static void {prefix}_take(CrustTask *task, void *out) {{
{result_copy}
}}

static void {prefix}_release(CrustTask *task) {{
    {prefix}_state *frame = ({prefix}_state *)task;
{cleanup}    if (!task_pool_release(frame->slot)) fail("invalid async slot");
}}

static int {prefix}_can_discard_suspended(CrustTask *task) {{
    {prefix}_state *frame = ({prefix}_state *)task;
    switch (frame->pc) {{
{''.join(suspended_checks)}    default: return 0;
    }}
}}

static void {prefix}_discard_suspended(CrustTask *task) {{
    {prefix}_state *frame = ({prefix}_state *)task;
    switch (frame->pc) {{
{''.join(suspended_cleanup)}    default: fail("invalid suspended cleanup point");
    }}
    if (!task_pool_release(frame->slot)) fail("invalid suspended async slot");
}}

static const CrustTaskOps {prefix}_ops = {{
    {prefix}_resume, {prefix}_take, {prefix}_release
}};

static CrustTask *{prefix}_create_in_pool(CrustTaskPool *pool{arguments}) {{
    CrustTaskSlot slot = task_pool_acquire(pool);
    {prefix}_state *frame = task_slot_address(slot);
    if (!frame) fail("task pool capacity exceeded");
    frame->slot = slot;
    frame->pc = 0;
{initialize}    task_init(&frame->task, &{prefix}_ops);
    frame->task.can_discard_suspended = {prefix}_can_discard_suspended;
    frame->task.discard_suspended = {prefix}_discard_suspended;
    return &frame->task;
}}
"""


def task_capture_declarations(node, *, structures=()):
    for i, (_, mode, typ) in enumerate(node.args[1]):
        yield f'{capture_ctype(mode, typ, structures=structures)} capture_{i}'
        if i in node.cell_reference_parameters:
            yield f'Cell * capture_cell_{i}'
    if getattr(node, 'result_storage', False):
        yield 'Source * result_storage'


def task_factory_signature(name, node, *, structures=()):
    declarations = ', '.join(task_capture_declarations(node, structures=structures)) or 'void'
    return f'static CrustTask *crust_async_{name}_create({declarations})'


def lower_task_context(definitions, *, capacities, threaded=False, async_threaded=False, variants=None, structures=()):
    variants = variants or {}
    members, initialize, checks, factories = [], [], [], []
    storage_types = []
    capacity_defines = []
    capacity_names = []
    for index, (name, node) in enumerate(definitions.items()):
        capacity = f'CRUST_TASK_POOL_{index}_CAPACITY'
        capacity_names.append(capacity)
        # The global macro is a raw-C oracle hook, never a source-language
        # fallback: checked source always supplies an inferred/explicit bound.
        capacity_defines.append(
            f'#ifndef CRUST_TASK_POOL_CAPACITY\n#define {capacity} {capacities[name]}\n'
            f'#else\n#define {capacity} CRUST_TASK_POOL_CAPACITY\n#endif\n'
            f'_Static_assert({capacity} > 0, "task pool capacity must be positive");')
        prefix = f'crust_async_{name}'
        specialized = [symbol for symbol, nominal in variants.items() if nominal == name]
        storage_type = prefix + '_state'
        if specialized:
            storage_type = prefix + '_storage'
            storage_types.append('typedef union {\n' +
                f'    {prefix}_state ordinary;\n' +
                ''.join(f'    crust_async_{symbol}_state variant_{i};\n'
                        for i, symbol in enumerate(specialized)) +
                f'}} {storage_type};\n')
        members.extend((
            f'    CrustTaskPool pool_{name};',
            f'    {storage_type} states_{name}[{capacity}];',
            f'    _Atomic size_t generations_{name}[{capacity}];',
        ))
        initialize.append(
            f'    task_pool_init(&crust_task_context.pool_{name}, &crust_task_context.states_{name}, '
            f'sizeof({storage_type}), {capacity}, crust_task_context.generations_{name});')
        if threaded:
            members.append(f'    CrustQueueEntry queue_entries_{name}[{capacity}];')
            initialize.append(f'    for (size_t i = 0; i < {capacity}; ++i) '
                              f'task_queue_entry_init(&crust_task_context.queue_entries_{name}[i]);')
        checks.append(
            f'    if (!task_pool_is_empty(&crust_task_context.pool_{name})) fail("live async task at context close");')
        if threaded:
            checks.append(f'    for (size_t i = 0; i < {capacity}; ++i) '
                          f'task_queue_entry_destroy(&crust_task_context.queue_entries_{name}[i]);')
        captures = ''.join(', ' + declaration.rsplit(' ', 1)[-1]
                           for declaration in task_capture_declarations(node, structures=structures))
        reap = '    task_thread_reap(&crust_abandoned_tasks);\n' if threaded else ''
        factories.append(
            f'{task_factory_signature(name, node, structures=structures)} {{\n'
            f'{reap}    CrustTask *task = {prefix}_create_in_pool(&crust_task_context.pool_{name}{captures});\n'
            + (f'    task->queue_entry = &crust_task_context.queue_entries_{name}'
               f'[(({prefix}_state *)task)->slot.index];\n' if threaded else '')
            + '    return task;\n'
            '}')
        for symbol in specialized:
            variant_prefix = f'crust_async_{symbol}'
            factories.append(
                f'{task_factory_signature(symbol, node, structures=structures)} {{\n'
                f'{reap}    CrustTask *task = {variant_prefix}_create_in_pool(&crust_task_context.pool_{name}{captures});\n'
                + (f'    task->queue_entry = &crust_task_context.queue_entries_{name}'
                   f'[(({variant_prefix}_state *)task)->slot.index];\n' if threaded else '')
                + '    return task;\n}')
    total_capacity = ' + '.join(capacity_names)
    abandoned = ''
    if threaded:
        abandoned = f'''
static CrustAbandonedExecution crust_abandoned_slots[{total_capacity}];
static CrustAbandonedTasks crust_abandoned_tasks = {{
    .entries = crust_abandoned_slots, .capacity = {total_capacity}
}};

static void crust_reap_abandoned(void) {{
    task_thread_reap(&crust_abandoned_tasks);
}}

static void task_abandon(CrustExecution *execution) {{
    task_thread_abandon(&crust_abandoned_tasks, execution);
    task_thread_reap(&crust_abandoned_tasks);
}}
'''
        if async_threaded:
            abandoned += """
static void task_abandon_async(CrustAsyncExecution *execution) {
    task_async_abandon(&crust_abandoned_tasks, execution);
    task_thread_reap(&crust_abandoned_tasks);
}
"""
        checks.insert(0, '    task_default_close();')
        checks.insert(0, '    task_thread_drain(&crust_abandoned_tasks);')
        initialize.insert(0, '    task_completion_reap = crust_reap_abandoned;')
    return '\n' + '\n'.join(storage_types + capacity_defines) + '''
static struct {
''' + '\n'.join(members) + '''
} crust_task_context;

''' + abandoned + '''
static void crust_task_context_init(void) {
''' + '\n'.join(initialize) + '''
}

static void crust_task_context_close(void) {
''' + '\n'.join(checks) + '''
}

static void task_discard(CrustTask *task) {
    if (!task_drop_inactive(task)) fail("invalid inactive task cleanup");
}

''' + '\n\n'.join(factories) + '\n'
