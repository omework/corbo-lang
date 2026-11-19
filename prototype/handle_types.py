"""Public execution shapes and opaque capture groups for modular contracts.

These descriptors are not async definitions: they generate no frame or pool.
Capture groups 1 and 2 retain shared/exclusive loans independently. Group 3
retains an exclusive ancestor while exposing only its shared reborrow. Group 0
represents storage retained by owned captures, not a concrete Int allocation.
Borrowed results have separate projections: group 4 carries the result loan,
and group 5 preserves an exclusive capability behind a shared result. These
groups survive join; unrelated capture groups do not.
"""

from owned_join_types import (
    OWNED_JOIN_TYPES, owned_join_mode,
)
from option_join_types import (
    OPTION_JOIN_TYPES, option_type_mode, option_payload_type,
)
from exchange_join_types import (
    EXCHANGE_JOIN_TYPES, exchange_type_mode, exchange_payload_type,
)
from handle_exchange_types import exchange_element
from capture_paths import capture_index
from types import SimpleNamespace
from numeric_core import EXTRA_C_TYPES


def is_public_handle(typ):
    return typ.startswith('runtime::Handle<') and typ.endswith('>')


def resolve_handle_pool_origins(origins, captured):
    """Replace symbolic capture indexes with the argument's pool origins."""
    return frozenset(pool for origin in origins
                     for pool in (captured.get(origin, ()) if isinstance(origin, int) else (origin,)))


def initial_handle_waits(declaration):
    parameters = {name: index for index, (name, mode, _) in enumerate(declaration.args[1])
                  if mode == 'async_execution'}
    waited = []

    def scan(statements):
        for statement in statements:
            if statement.op == 'yield':
                continue
            if statement.op == 'scope':
                if not scan(statement.args[1]):
                    return False
                continue
            if statement.op != 'var':
                return False
            initializer = statement.args[1]
            if initializer[0] in ('int', 'bool', 'array_numeric_literal'):
                continue
            if initializer[0] != 'await' or initializer[1][0] != 'name':
                return False
            index = parameters.get(initializer[1][1])
            if index is None or index in waited:
                return False
            waited.append(index)
            if statement.utf8_match_subject:
                # The arms may write through another capture. Keep their
                # effects after this wait and stop the initial sequence.
                return False
        return True

    scan(declaration.args[3])
    return tuple(waited)


def public_async_signature(typ, structures=(), *, allow_borrowed=False):
    if not typ.startswith('runtime::AsyncHandle<') or not typ.endswith('>'):
        return None
    from async_lowering import SCALAR_RESULTS
    signature = public_signature(typ.replace('runtime::AsyncHandle<', 'runtime::Handle<', 1), structures)
    if signature is not None and (signature in SCALAR_RESULTS or signature[0] in ('void', 'array')):
        return signature
    if (allow_borrowed and signature is not None and signature[0] in ('ref', 'mut')
            and signature[1] in ('Int', 'u8', *EXTRA_C_TYPES)):
        return signature
    return None


def public_signature(typ, structures=()):
    if not is_public_handle(typ):
        return None
    payload = typ[len('runtime::Handle<'):-1]
    if public_async_signature(payload, structures) is not None:
        return 'async_execution', payload
    if payload.startswith('&'):
        mode, content = ('mut', payload[5:]) if payload.startswith('&mut ') else ('ref', payload[1:])
        if content == 'Int' or content in structures or content in EXTRA_C_TYPES or (mode, content) == ('mut', 'u8'):
            return mode, content
    from async_lowering import SCALAR_RESULTS, scalar_array_layout
    if payload == 'Void':
        return ('void', 'Void')
    if payload == 'bool':
        return ('scalar', 'Bool')
    if scalar_array_layout(payload)[1] is not None:
        return ('array', payload)
    if payload.startswith('A<') and payload.endswith('>'):
        content = payload[2:-1]
        from array_syntax import is_handle_vector, INLINE_VECTOR_ELEMENTS
        if (content in ('Int', 'String', 'Vector<Int>', 'Vector<u8>') or content in structures
                or is_handle_vector(content) or INLINE_VECTOR_ELEMENTS.get(content) in structures):
            return ('owned', content)
    if exchange_element(payload) is not None:
        return ('buffered_handle_exchange', payload)
    if (mode := exchange_type_mode(payload)) is not None:
        return mode, exchange_payload_type(mode)
    if (mode := option_type_mode(payload)) is not None:
        return mode, option_payload_type(mode)
    from handle_option_types import option_element, local_option_element
    if (element := option_element(payload) or local_option_element(payload)) is not None:
        return ('handle_option', element)
    if payload in structures:
        return ('owned', payload)
    if payload.startswith('Result<') and payload.endswith(',runtime::Error>'):
        inner = payload[len('Result<'):-len(',runtime::Error>')]
        signature = public_signature(f'runtime::Handle<{inner}>', structures)
        if signature is not None and signature[0] in ('owned', *OWNED_JOIN_TYPES):
            return (owned_join_mode(signature[0]), signature[1])
    return next((signature for signature, name in SCALAR_RESULTS.items()
                 if name == payload), None)


def public_storage(typ, structures=()):
    """The public payload keeps local T distinct from an allocation A<T>."""
    if not is_public_handle(typ):
        return None
    payload = typ[len('runtime::Handle<'):-1]
    if payload.startswith('Result<') and payload.endswith(',runtime::Error>'):
        return public_storage('runtime::Handle<' + payload[len('Result<'):-len(',runtime::Error>')] + '>', structures)
    from handle_option_types import option_element, local_option_element
    if payload in structures or local_option_element(payload) in structures:
        return 'local'
    if option_element(payload) is not None:
        return 'pool'
    if payload.startswith('A<') and payload[2:-1] in structures:
        return 'pool'
    return None


def contextual_public_type(nominal, expected, definitions):
    """Check payload shape here; source constraints separately check T/A<T>."""
    if is_public_handle(nominal):
        return nominal
    from async_lowering import public_handle_type
    declaration = definitions[nominal]
    if isinstance(declaration, tuple):
        declaration = declaration[0]
    return public_handle_type(declaration.args[2],
        storage=public_storage(expected, definitions.structures) or 'pool')


PUBLIC_RESULT_LOCK_SLOT = 6
PUBLIC_RESULT_LOCK_CAPTURE = f'ref.{PUBLIC_RESULT_LOCK_SLOT}'


def canonical_captures(fields, parameters):
    groups = {'ref.1': [], 'mut.2': [], 'mut.3': []}
    seen = {key: set() for key in groups}
    for key, targets in fields:
        shared_capability = parameters[capture_index(key.partition('.')[2])][1] == 'ref'
        key = ('mut.3' if shared_capability else 'mut.2') if key.startswith('mut.') else 'ref.1'
        group = groups[key]
        for target in targets:
            identity = ('allocation', target.id) if hasattr(target, 'id') else target
            if identity not in seen[key]:
                seen[key].add(identity)
                group.append(target)
    return tuple((key, tuple(targets)) for key, targets in groups.items() if targets)


def common_public_handle(nominals, definitions, *, expected=None, storage='pool'):
    """Unify distinct execution frames only when their public payload agrees."""
    names = set(nominals)
    if len(names) < 2:
        return None
    if expected is not None and all(contextual_public_type(name, expected, definitions) == expected for name in names):
        return expected
    from async_lowering import public_handle_type
    payloads = set()
    for name in names:
        declaration = definitions[name]
        if isinstance(declaration, tuple):
            declaration = declaration[0]
        payloads.add(name if is_public_handle(name) else public_handle_type(declaration.args[2], storage=storage))
    if len(payloads) == 1:
        public = payloads.pop()
        if public_signature(public, getattr(definitions, 'structures', ())) is not None:
            return public
    return None


class HandleDefinitions(dict):
    def __init__(self, values=(), *, compiled=False, structures=None):
        super().__init__(values)
        self.compiled = compiled
        self.structures = structures if structures is not None else getattr(values, 'structures', {})

    def copy(self):
        return type(self)(self, compiled=self.compiled, structures=self.structures)

    def __missing__(self, key):
        signature = (public_async_signature(key, self.structures, allow_borrowed=True)
                     if key.startswith('runtime::AsyncHandle<') else public_signature(key, self.structures))
        if signature is None:
            raise KeyError(key)
        parameters = [
            ('opaque_storage', 'owned', 'Int'),
            ('opaque_shared', 'ref', 'Int'),
            ('opaque_exclusive', 'mut', 'Int'),
            ('opaque_shared_capability', 'ref', 'Int'),
        ]
        declaration_storage = public_storage(key, self.structures)
        result_storage = None
        result_borrows = ()
        result_views = ()
        from utf8_syntax import ASYNC_CAPTURE_VIEW_MODES, ASYNC_SHARED_VIEW_MODES
        if signature[0] in ASYNC_CAPTURE_VIEW_MODES:
            shared = signature[0] in ASYNC_SHARED_VIEW_MODES
            result_views = (4, 5) if shared else (4,)
            parameters.append(("opaque_result_view", *signature))
            if shared:
                parameters.append(("opaque_result_view_capability", *signature))
        if signature[0] in ('ref', 'mut'):
            result_borrows = (4, 5) if signature[0] == 'ref' else (4,)
            parameters.append(('opaque_result_borrow', signature[0], signature[1]))
            if signature[0] == 'ref':
                parameters.append(('opaque_result_capability', 'ref', signature[1]))
        if signature[0] in ('owned', 'join_owned', 'handle_option', 'buffered_handle_exchange', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
            result_storage = len(parameters)
            parameters.append(('opaque_result_storage', 'owned', exchange_element(signature[1]) if signature[0] == 'buffered_handle_exchange' else signature[1]))
        if signature[0] == 'owned':
            while len(parameters) < PUBLIC_RESULT_LOCK_SLOT:
                parameters.append(('opaque_reserved', 'ref', 'Int'))
            parameters.append(('opaque_result_lock', 'ref', 'Int'))
        declaration = SimpleNamespace(args=(key, parameters, signature, []),
                                      join_storage_result=declaration_storage, public_result_storage=result_storage,
                                      public_result_borrows=result_borrows, public_result_views=result_views, native_block=False, line=0)
        from array_syntax import is_handle_vector
        if signature[0] in ('owned', 'handle_option', *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES) and (signature[1] in self.structures or is_handle_vector(signature[1])):
            from array_syntax import owned_reference_paths
            from results import FunctionResult, ResultCandidate, BorrowTarget
            enums = {name: layout if isinstance(layout, dict) else {'': layout}
                     for name, layout in self.structures.items()}
            fields = tuple((path, frozenset({BorrowTarget('field_parameter', result_storage, path)}))
                           for path, _, _ in owned_reference_paths(enums, signature[1]))
            result = FunctionResult(signature[0], signature[1],
                candidates=frozenset({ResultCandidate('parameter', result_storage)}), borrowed_fields=fields)
            declaration.field_effect_summary = SimpleNamespace(
                complete=True, may_complete=True, completion_result=result)
            declaration.join_storage_result = public_storage(key, self.structures)
        return (declaration, None) if self.compiled else declaration
