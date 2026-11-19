"""Canonical builtin types shared by the HashMap front end and verifier."""

from numeric_core import FORMATS, numeric_type


KEY_TYPES = frozenset(('Int', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'bool'))
METHODS = frozenset(('insert', 'try_insert', 'remove', 'get', 'get_mut'))


def map_types(typ):
    if typ and typ.startswith('HashMap<'):
        key, _, value = typ[8:-1].partition(',')
        return key, value
    return None


def scalar_layout(typ):
    if typ == 'bool':
        return 'bool', '_Bool'
    spec = FORMATS.get(numeric_type(typ))
    if spec:
        return spec.mode, 'int' if spec.mode == 'scalar' else spec.c_type
    return None


def numeric_handle_element(typ):
    if typ.startswith('A<'):
        element = typ[2:-1]
        if numeric_type(element):
            return 'Int' if numeric_type(element) == 'i32' else element
    return None


def supports_capture(mode, typ):
    mapping = map_types(typ)
    if mapping is None:
        return False
    _, value = mapping
    if mode in ('ref', 'mut') and numeric_handle_element(value):
        return True
    if mode == 'ref':
        return scalar_layout(value.removeprefix('&')) is not None
    return mode == 'mut' and scalar_layout(value.removeprefix('&')) is not None


def value_layout(typ):
    if typ.startswith('A<'):
        return 'owned', 'Cell *'
    if typ.startswith('&'):
        layout = scalar_layout(typ[1:].removeprefix('mut '))
        if layout:
            return 'reference', layout[1] + ' *'
    return scalar_layout(typ)


def method_result(method, value):
    if method == 'get':
        value = '&' + value
    elif method == 'get_mut':
        value = '&mut ' + value
    result = f'Option<{value}>'
    return f'Result<{result},{value}>' if method == 'try_insert' else result
