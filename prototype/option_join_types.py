"""Runtime envelopes whose leaf is an optional allocation handle."""
from result_envelopes import ResultLeaf, RuntimeResultEnvelopes
from handle_option_types import option_element, local_option_element

_registry = RuntimeResultEnvelopes({
    'Option<A<Int>>': ResultLeaf('join_option', 'CrustOptionJoinResult',
        'optional_nested', 'handle_option', 'Int', '=='),
})
OPTION_JOIN_TYPES = _registry.types
OPTION_JOIN_CTYPES = _registry.ctypes
OPTION_JOIN_CELLS = _registry.cells
OPTION_JOIN_PAYLOADS = _registry.payloads
OPTION_PAYLOAD_MODES = _registry.payload_modes
OPTION_JOIN_DEPTHS = _registry.depths


def _register_leaf(typ):
    """Keep distinct static payloads while sharing the Cell-pointer C ABI."""
    while typ.startswith('Result<') and typ.endswith(',runtime::Error>'):
        typ = typ[len('Result<'):-len(',runtime::Error>')]
    local = local_option_element(typ)
    element = option_element(typ) or local
    if element is not None and typ not in _registry.leaves:
        # An injective spelling avoids collisions across qualified/nested types.
        suffix = ('local_' if local else '') + element.encode('utf-8').hex()
        _registry.leaves[typ] = ResultLeaf('join_option_t' + suffix,
            'CrustOptionJoinResult', 'optional_t' + suffix + '_nested',
            'handle_option', element, '==')


def option_type_mode(typ):
    _register_leaf(typ)
    return _registry.type_mode(typ)


def option_join_mode(inner):
    _register_leaf(inner)
    return _registry.wrap(inner)


def option_payload_type(mode):
    return _registry.roots[mode].typ


def option_inner_signature(mode):
    inner_mode, _ = _registry.inner_signature(mode)
    return inner_mode, option_payload_type(mode)


option_cleanup = _registry.cleanup
option_join_layouts = _registry.layouts
