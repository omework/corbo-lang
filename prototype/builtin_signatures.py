"""Source signatures of builtin methods for structural feature matching.

Only signatures live here. The existing builtin AST, contract inference and C
emitter still implement every effect, provenance and runtime operation.
"""
from array_syntax import (fixed_array_shape, reference_array_shape, reference_type,
                          VECTOR_ELEMENTS, INLINE_VECTOR_ELEMENTS, VECTOR_TYPES, HANDLE_VECTOR,
                          SHARED_REF_VECTOR, MUT_REF_VECTOR)
from effects import method_candidate
from utf8_syntax import VALUE_SIGNATURES, VECTOR_SPLIT_TYPES


def normalized_type(mode, typ, *, result=False):
    mode = VALUE_SIGNATURES.get((mode, typ), mode)
    handle = False
    if mode == 'scalar' and typ == 'Void':
        mode = 'void'
    if reference_array_shape(typ) and (mode == 'scalar' or (not result and mode == 'owned')):
        mode = 'array_refs' if mode == 'scalar' else 'array_refs_owned'
    elif fixed_array_shape(typ):
        mapping = {'scalar': 'array'} if result else {'scalar': 'array', 'ref': 'array_ref', 'mut': 'array_mut'}
        mode = mapping.get(mode, mode)
    if mode == 'owned' and typ.startswith('A<'):
        mode, typ, handle = 'owned', typ[2:-1], True
    if mode == 'owned' and typ == 'Option<A<Int>>':
        mode, typ = 'handle_option', 'Int'
    elif mode == 'owned' and typ in ('Result<A<Int>,A<Int>>', 'Result<(),A<Int>>'):
        mode = 'buffered_handle_exchange'
    if result and mode == 'scalar' and typ in VECTOR_SPLIT_TYPES:
        mode = 'vector_split'
    return mode, typ, handle


def builtin_method_signatures(typ, method):
    """Return normalized signature alternatives, including optional arguments."""
    signatures = []
    def add(receiver, parameters=(), result=('void', 'Void')):
        signatures.append((tuple(normalized_type(mode, nominal) for mode, nominal in
                                 ((receiver, typ), *parameters)), normalized_type(*result, result=True)))

    if typ in VECTOR_TYPES:
        element = INLINE_VECTOR_ELEMENTS.get(typ) or VECTOR_ELEMENTS.get(typ, 'A<Int>' if typ == HANDLE_VECTOR else
                                      '&Int' if typ == SHARED_REF_VECTOR else '&mut Int')
        capability = reference_type(element)
        item = capability if capability else ('owned', element) if element.startswith('A<') or typ in INLINE_VECTOR_ELEMENTS else ('scalar', element)
        if method == 'len':
            add('ref', result=('scalar', 'Int'))
        elif method in ('push', 'try_push'):
            returned = ('void', 'Void') if method == 'push' else (
                'owned' if typ in (HANDLE_VECTOR, MUT_REF_VECTOR) else 'scalar', f'Result<(),{element}>')
            add('mut', (item,), returned)
        elif method == 'remove':
            add('mut', (('scalar', 'Int'),), item)
        elif method == 'pop':
            add('mut', result=('owned' if typ in (HANDLE_VECTOR, MUT_REF_VECTOR) else 'scalar', f'Option<{element}>'))
        elif method == 'replace':
            add('mut', (('scalar', 'Int'), item),
                ('owned' if typ in (HANDLE_VECTOR, MUT_REF_VECTOR) else 'scalar', f'Result<{element},{element}>'))
        elif method == 'push_new' and typ in VECTOR_ELEMENTS:
            add('mut', result=('mut', element))
        elif method == 'try_extend' and typ == 'Vector<u8>':
            add('mut', (('ref', '[u8]'),), ('scalar', 'Result<(),CapacityError>'))
        elif method == 'read_fd' and typ == 'Vector<u8>':
            add('mut', (('scalar', 'Int'),), ('scalar', 'Result<Int,ReadError>'))
        elif method == 'split_at_mut' and typ in VECTOR_ELEMENTS:
            add('mut', (('scalar', 'Int'),), ('scalar', f'(&mut [{element}],&mut [{element}])'))
    elif typ in ('String', 'str'):
        if method == 'byte_len':
            add('ref', result=('scalar', 'Int'))
        elif method == 'char_at' and typ == 'str':
            add('ref', (('scalar', 'Int'),), ('scalar', 'Result<char,CharAtError>'))
        elif method == 'try_slice':
            for count in (1, 2):
                add('ref', (('scalar', 'Int'),) * count, ('scalar', 'Result<&str,SliceError>'))
        elif typ == 'String':
            parameters = {
                'push': (('scalar', 'char'),), 'push_str': (('ref', 'str'),),
                'merge': (('owned', 'String'),), 'pop': (),
                'replace_byte': (('scalar', 'Int'), ('scalar', 'u8')),
                'replace_bytes': (('scalar', 'Int'), ('ref', '[u8]')),
            }
            results = {'pop': ('scalar', 'Option<char>'),
                       'replace_byte': ('scalar', 'Result<u8,ByteReplaceError>'),
                       'replace_bytes': ('scalar', 'Result<(),ByteReplaceError>')}
            if method in parameters:
                add('mut', parameters[method], results.get(method, ('void', 'Void')))
    elif typ is not None and (shape := fixed_array_shape(typ)):
        if method == 'len':
            add('ref', result=('scalar', 'Int'))
        elif method == 'swap':
            add('mut', (('scalar', 'Int'), ('scalar', 'Int')))
        elif method == 'replace' and shape[0] in ('Int', 'u8'):
            add('mut', (('scalar', 'Int'), ('scalar', shape[0])), ('scalar', shape[0]))
        elif method in ('ref', 'mut_ref'):
            mode = 'ref' if method == 'ref' else 'mut'
            add(mode, result=(mode, typ))
    elif typ is not None and typ.startswith('Pool<') and method == 'new':
        element = typ[5:-1]
        # The currently implemented positional initializer is the Int variant.
        if element == 'Int':
            add('mut', (('scalar', 'Int'),), ('owned', 'A<Int>'))
        if element in ('Int', 'String', *VECTOR_TYPES):
            add('mut', result=('owned', f'A<{element}>'))
    return signatures


def feature_method_candidate(expr):
    # These surface methods can be lowered by the parser before nominal types
    # are known. They must not bypass the abstract feature guarantee check.
    names = {'utf8_len': 'utf8_len', 'utf8_byte_len': 'byte_len',
             'utf8_string_len': 'byte_len', 'utf8_char_at': 'char_at',
             'utf8_try_slice': 'try_slice'}
    if expr[0] in names:
        return ('method_call', expr[1], names[expr[0]], list(expr[2:]))
    return method_candidate(expr)
