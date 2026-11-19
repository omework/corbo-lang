"""Types and expression forms shared by the UTF-8 analyses."""
from collections import ChainMap
from numeric_core import (EXTRA_MODES, CONVERSION_PAYLOADS, CONVERSION_FAMILIES,
                          CONVERSION_C_TYPES, NUMERIC_JOIN_FIELDS, conversion_type)

UTF8_TEXT_RESULT = 'Result<&str,Utf8Error>'
UTF8_SLICE_RESULT = 'Result<&str,SliceError>'
CHAR_RESULT_FAMILIES = {'char_at_result': 1, 'char_from_str_result': 2, 'char_option': 4}
UTF8_VALUE_RESULT_FAMILIES = {**CHAR_RESULT_FAMILIES, 'byte_replace_result': 6,
                              'bytes_replace_result': 10, 'integer_conversion_result': 11, 'slice_result': 12}
UTF8_VALUE_RESULT_CTYPES = {**dict.fromkeys(CHAR_RESULT_FAMILIES, 'CrustCharResult'),
                            'byte_replace_result': 'CrustByteResult', 'bytes_replace_result': 'CrustByteResult',
                            'integer_conversion_result': 'CrustByteResult', 'slice_result': 'CrustTextResult'}
UTF8_VALUE_RESULT_FIELDS = {**dict.fromkeys(CHAR_RESULT_FAMILIES, 'decoded_value'),
                            'byte_replace_result': 'replaced_value', 'bytes_replace_result': 'replaced_value',
                            'integer_conversion_result': 'replaced_value', 'slice_result': 'sliced_value'}
# Internal async discriminants are distinct even when source match syntax
# shares Ok/Err or Some/None. These modes have no borrowed/owned payload.
VECTOR_VALUE_RESULT_FAMILIES = {
    'int_option': 16, 'byte_option': 17, 'int_replace': 18, 'byte_replace': 19,
    'int_try_push': 20, 'byte_try_push': 21, 'capacity_result': 22, 'read_result': 23,
}
VECTOR_VALUE_RESULT_CTYPES = {
    'int_option': 'CrustIntPayload', 'byte_option': 'CrustBytePayload',
    'int_replace': 'CrustIntPayload', 'byte_replace': 'CrustBytePayload',
    'int_try_push': 'CrustIntPayload', 'byte_try_push': 'CrustBytePayload',
    'capacity_result': 'CrustStatus', 'read_result': 'CrustIntPayload',
}
VECTOR_VALUE_RESULT_FIELDS = {
    mode: ('vector_byte_result' if ctype == 'CrustBytePayload' else
           'vector_status_result' if ctype == 'CrustStatus' else 'vector_int_result')
    for mode, ctype in VECTOR_VALUE_RESULT_CTYPES.items()
}
ASYNC_VALUE_RESULT_FAMILIES = {**UTF8_VALUE_RESULT_FAMILIES, **VECTOR_VALUE_RESULT_FAMILIES, **CONVERSION_FAMILIES}
ASYNC_VALUE_RESULT_CTYPES = {**UTF8_VALUE_RESULT_CTYPES, **VECTOR_VALUE_RESULT_CTYPES, **CONVERSION_C_TYPES}
ASYNC_VALUE_RESULT_FIELDS = {**UTF8_VALUE_RESULT_FIELDS, **VECTOR_VALUE_RESULT_FIELDS,
                             **{mode: mode for mode in CONVERSION_PAYLOADS}}
UTF8_BORROW_MODES = {
    'text': 'borrowed_text',
    'vector_bytes': 'borrowed_vector_bytes',
    'vector_ints': 'borrowed_vector_ints',
    'vector_mut_bytes': 'borrowed_vector_mut_bytes',
    'vector_mut_ints': 'borrowed_vector_mut_ints',
    'byte_ref': 'borrowed_byte',
    'text_result': 'utf8_text_result',
    'slice_result': 'utf8_slice_result',
}
OPTION_PAYLOADS = {'char_option': 'char', 'int_option': 'scalar', 'byte_option': 'byte'}
VECTOR_OPTION_MODES = {'Int': 'int_option', 'u8': 'byte_option'}

VECTOR_REPLACE_MODES = {'Int': 'int_replace', 'u8': 'byte_replace'}
VECTOR_TRY_PUSH_MODES = {'Int': 'int_try_push', 'u8': 'byte_try_push'}
VECTOR_VALUE_ERRORS = (*VECTOR_REPLACE_MODES.values(), *VECTOR_TRY_PUSH_MODES.values())
UNIT_RESULT_MODES = ('bytes_replace_result', 'capacity_result', *VECTOR_TRY_PUSH_MODES.values())
VECTOR_PAYLOAD_TYPES = {
    'Result<Int,ReadError>': 'Int',
    'Option<Int>': 'Int', 'Option<u8>': 'u8',
    'Result<(),Int>': 'Int', 'Result<(),u8>': 'u8',
    'Result<Int,Int>': 'Int', 'Result<u8,u8>': 'u8',
}

VECTOR_SLICE_MODES = {'Vector<u8>': 'vector_bytes', 'Vector<Int>': 'vector_ints'}
VECTOR_SLICE_ELEMENTS = {'vector_bytes': 'uint8_t', 'vector_ints': 'int'}
ASYNC_SHARED_VIEW_MODES = ('text', 'byte_ref', 'slice_result', *VECTOR_SLICE_ELEMENTS)
VECTOR_MUT_SLICE_MODES = {'Vector<u8>': 'vector_mut_bytes', 'Vector<Int>': 'vector_mut_ints'}
VECTOR_SPLIT_TYPES = {f'(&mut [{element}],&mut [{element}])': f'[{element}]' for element in ('Int', 'u8')}
VECTOR_MUT_VIEW_KINDS = tuple(UTF8_BORROW_MODES[mode] for mode in VECTOR_MUT_SLICE_MODES.values())
SHARED_VECTOR_SLICE_MODES = {mode: VECTOR_SLICE_MODES[typ] for typ, mode in VECTOR_MUT_SLICE_MODES.items()}
ASYNC_CAPTURE_VIEW_MODES = (*ASYNC_SHARED_VIEW_MODES, *SHARED_VECTOR_SLICE_MODES)
ASYNC_VIEW_FIELDS = {
    'text': 'text_value',
    'slice_result': 'sliced_value',
    'byte_ref': 'byte_ref_value',
    **dict.fromkeys((*VECTOR_SLICE_ELEMENTS, *SHARED_VECTOR_SLICE_MODES), 'vector_slice_value'),
}

# Finite builtin error values are Copy and carry no storage dependencies.
ERROR_VALUE_TYPES = {
    'read_error': 'ReadError', 'capacity_error': 'CapacityError',
    'byte_replace_error': 'ByteReplaceError', 'char_at_error': 'CharAtError',
    'char_from_str_error': 'CharFromStrError',
    'integer_conversion_error': 'IntegerConversionError', 'slice_error': 'SliceError',
    'numeric_conversion_error': 'NumericConversionError',
}
ERROR_VALUE_MODES = {typ: mode for mode, typ in ERROR_VALUE_TYPES.items()}
ERROR_VALUE_TAGS = {mode: 100 + index for index, mode in enumerate(ERROR_VALUE_TYPES)}
RESULT_ERROR_MODES = {
    'read_result': 'read_error', 'capacity_result': 'capacity_error',
    'byte_replace_result': 'byte_replace_error', 'bytes_replace_result': 'byte_replace_error',
    'char_at_result': 'char_at_error', 'char_from_str_result': 'char_from_str_error',
    'integer_conversion_result': 'integer_conversion_error',
    'slice_result': 'slice_error', 'utf8_slice_result': 'slice_error',
}

# These Result payloads contain neither ownership nor borrowing metadata.
# Borrowed/owning joins deliberately use separate lifetime-aware modes.
PLAIN_JOIN_PAYLOADS = {
    **{'join_' + mode: typ for mode, typ in ERROR_VALUE_TYPES.items()},
    **{'join_' + mode: typ for mode, typ in EXTRA_MODES.items()},
    'join_int': 'Int', 'join_bool': 'Bool', 'join_byte': 'u8',
    'join_char': 'char', 'join_void': '()', 'join_runtime_error': 'runtime::Error',
}
PLAIN_JOIN_TYPES = {mode: f'Result<{payload},runtime::Error>'
                    for mode, payload in PLAIN_JOIN_PAYLOADS.items()}
PLAIN_JOIN_FIELDS = {
    **{'join_' + mode: mode + '_value' for mode in ERROR_VALUE_TYPES},
    **NUMERIC_JOIN_FIELDS,
    'join_int': 'value', 'join_bool': 'bool_value', 'join_byte': 'byte_value',
    'join_char': 'char_value', 'join_void': None, 'join_runtime_error': 'runtime_error_value',
}
PLAIN_RETURN_JOINS = {
    **{(mode, typ): 'join_' + mode for mode, typ in ERROR_VALUE_TYPES.items()},
    **{(mode, typ): 'join_' + mode for mode, typ in EXTRA_MODES.items()},
    ('scalar', 'Int'): 'join_int', ('scalar', 'Bool'): 'join_bool',
    ('byte', 'u8'): 'join_byte', ('char', 'char'): 'join_char',
    ('void', 'Void'): 'join_void', ('scalar', 'Void'): 'join_void',
    ('runtime_error', 'runtime::Error'): 'join_runtime_error',
}
PLAIN_JOIN_C_TYPES = dict.fromkeys(PLAIN_JOIN_TYPES, 'CrustJoinResult')
PLAIN_JOIN_INNER_MODES = {}
PLAIN_JOIN_SIGNATURES = {('scalar', typ): mode for mode, typ in PLAIN_JOIN_TYPES.items()}
PLAIN_JOIN_ANNOTATIONS = {typ: mode for mode, typ in PLAIN_JOIN_TYPES.items()}
PLAIN_JOIN_SCALAR_RESULTS = {(mode, typ): typ for mode, typ in PLAIN_JOIN_TYPES.items()}


def register_plain_join_type(typ):
    """Intern a finite, structural Result type; no program-specific semantics.

    These monotonic tables only cache canonical type facts. Generated C emits
    layouts needed by the current program, independently of prior compilations.
    Owning and borrowed payloads deliberately do not enter this registry.
    """
    if typ in PLAIN_JOIN_ANNOTATIONS:
        return PLAIN_JOIN_ANNOTATIONS[typ]
    suffix = ',runtime::Error>'
    if not typ.startswith('Result<') or not typ.endswith(suffix):
        return None
    inner_type = typ[len('Result<'):-len(suffix)]
    inner = register_plain_join_type(inner_type)
    if inner is None:
        # Existing scalar Result/Option representations contain no loans.
        # slice_result is deliberately excluded: its &str retains provenance.
        inner = next((mode for mode in ASYNC_VALUE_RESULT_FAMILIES
                      if mode != 'slice_result' and VALUE_MODES[mode] == inner_type), None)
    if inner is None:
        return None
    nested = inner in PLAIN_JOIN_TYPES
    mode = 'join_' + inner
    PLAIN_JOIN_TYPES[mode] = typ
    PLAIN_JOIN_PAYLOADS[mode] = inner_type
    PLAIN_JOIN_FIELDS[mode] = 'plain:' + inner if nested else inner
    if nested:
        PLAIN_JOIN_INNER_MODES[mode] = inner
    PLAIN_JOIN_C_TYPES[mode] = f'CrustPlainJoin{mode.count("join_")}' if nested else 'CrustJoinResult'
    PLAIN_JOIN_SIGNATURES['scalar', typ] = mode
    PLAIN_JOIN_ANNOTATIONS[typ] = mode
    PLAIN_JOIN_SCALAR_RESULTS[mode, typ] = typ
    PLAIN_RETURN_JOINS[inner, inner_type] = mode
    return mode


def plain_join_layouts(depth):
    return '\n'.join(
        'typedef struct { int status; ' +
        ('CrustJoinResult' if level == 2 else f'CrustPlainJoin{level - 1}') +
        f' value; }} CrustPlainJoin{level};'
        for level in range(2, depth + 1)) + '\n'

RESULT_ERROR_MODES.update(dict.fromkeys(CONVERSION_PAYLOADS, 'numeric_conversion_error'))

VALUE_MODES = ChainMap(PLAIN_JOIN_TYPES, {
    **EXTRA_MODES,
    **{mode: conversion_type(typ) for mode, typ in CONVERSION_PAYLOADS.items()},
    **ERROR_VALUE_TYPES,
    'runtime_error': 'runtime::Error',
    'task_id': 'runtime::TaskId',
    'bool': 'bool',
    'vector_bytes': '[u8]',
    'vector_ints': '[Int]',
    'vector_mut_bytes': '[u8]',
    'vector_mut_ints': '[Int]',
    'text': 'str',
    'byte': 'u8',
    'byte_ref': 'u8',
    'text_result': UTF8_TEXT_RESULT,
    'slice_result': UTF8_SLICE_RESULT,
    'char': 'char',
    'char_option': 'Option<char>',
    'int_try_push': 'Result<(),Int>',
    'byte_try_push': 'Result<(),u8>',
    'capacity_result': 'Result<(),CapacityError>',
    'read_result': 'Result<Int,ReadError>',
    'int_replace': 'Result<Int,Int>',
    'byte_replace': 'Result<u8,u8>',
    'int_option': 'Option<Int>',
    'byte_option': 'Option<u8>',
    'byte_replace_result': 'Result<u8,ByteReplaceError>',
    'bytes_replace_result': 'Result<(),ByteReplaceError>',
    'char_at_result': 'Result<char,CharAtError>',
    'char_from_str_result': 'Result<char,CharFromStrError>',
    'integer_conversion_result': 'Result<u8,IntegerConversionError>',
})
# Intern the already-supported nonborrowing async payload families so inferred
# joins and explicitly annotated envelopes always use the same contract type.
for _mode in ASYNC_VALUE_RESULT_FAMILIES:
    if _mode != 'slice_result':
        register_plain_join_type(f'Result<{VALUE_MODES[_mode]},runtime::Error>')

# Map source-level signatures to their lowered value modes.
VALUE_SIGNATURES = ChainMap(PLAIN_JOIN_SIGNATURES, {
    ('ref' if kind in ('text', 'byte_ref', *VECTOR_SLICE_MODES.values()) else 'scalar', typ): kind
    for kind, typ in VALUE_MODES.items() if kind not in VECTOR_MUT_SLICE_MODES.values()
})
VALUE_SIGNATURES.maps[1].update({('mut', VALUE_MODES[mode]): mode for mode in VECTOR_MUT_SLICE_MODES.values()})
VALUE_ANNOTATIONS = ChainMap(PLAIN_JOIN_ANNOTATIONS, {('&' if mode == 'ref' else '') + typ: kind
                     for (mode, typ), kind in VALUE_SIGNATURES.items()})

FALLIBLE_VALUE_MODES = ChainMap(PLAIN_JOIN_TYPES, dict.fromkeys(
    [mode for mode, typ in VALUE_MODES.items() if typ.startswith('Result<')] + ['utf8_text_result', 'utf8_slice_result']))
UTF8_EXPRESSION_MODES = {
    'utf8_error': 'runtime_error',
    'utf8_runtime_error': 'runtime_error',
    'utf8_char_at': 'char_at_result',
    'utf8_validate': 'text_result',
    'utf8_from_str': 'char_from_str_result',
    'utf8_len': 'scalar',
    'utf8_byte_len': 'scalar',
    'utf8_string_len': 'scalar',
    'utf8_string_push_str': 'void',
    'utf8_string_push': 'void',
    'utf8_string_pop': 'char_option',
    'utf8_string_merge': 'void',
    'utf8_string_replace_byte': 'byte_replace_result',
    'utf8_string_replace_bytes': 'bytes_replace_result',
    'utf8_slice': 'text',
    'utf8_try_slice': 'slice_result',
    'utf8_tag': 'scalar',
    'utf8_value': 'char',
}
UTF8_METHODS = {
    ('String', 'byte_len'): ('utf8_string_len', 0),
    ('String', 'replace_byte'): ('utf8_string_replace_byte', 2),
    ('String', 'replace_bytes'): ('utf8_string_replace_bytes', 2),
    ('String', 'merge'): ('utf8_string_merge', 1),
    ('String', 'pop'): ('utf8_string_pop', 0),
    ('String', 'push'): ('utf8_string_push', 1),
    ('String', 'push_str'): ('utf8_string_push_str', 1),
    ('str', 'byte_len'): ('utf8_byte_len', 0),
    ('str', 'char_at'): ('utf8_char_at', 1),
    ('char', 'utf8_len'): ('utf8_len', 0),
}
UTF8_ERRORS = {
    'runtime::Error': {'LaunchFailed': 5},
    'SliceError': {'OutOfBounds': 1, 'NotCharBoundary': 2},
    'TextBoundaryError': {'OutOfBounds': 1, 'NotCharBoundary': 2},
    'IntegerConversionError': {'OutOfRange': 13},
    'NumericConversionError': {'NotRepresentable': 13},
    'ReadError': {'EndOfStream': 10, 'CapacityExceeded': 11, 'Io': 12},
    'CapacityError': {'CapacityExceeded': 9},
    'ByteReplaceError': {'OutOfBounds': 7, 'InvalidUtf8': 8},
    'Utf8Error': {'_': 5},
    'CharAtError': {'OutOfBounds': 1, 'NotCharBoundary': 2},
    'CharFromStrError': {'Empty': 3, 'MultipleChars': 4},
}


def text_slice_bound_error(receiver, bounds):
    literal = receiver[1] if receiver[0] == 'text' else None
    known = [bound[1] if bound[0] == 'int' else None for bound in bounds]
    for index in known:
        if index is None:
            continue
        if index < 0 or (literal is not None and index > len(literal)):
            return 'bornes de découpe UTF-8 invalides'
        if literal is not None and index < len(literal) and literal[index] & 0xc0 == 0x80:
            return 'borne de découpe sur un octet de continuation UTF-8'
    if len(known) == 2 and None not in known and known[0] > known[1]:
        return 'bornes de découpe UTF-8 invalides'
    return None
