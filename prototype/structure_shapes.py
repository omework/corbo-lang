"""Layouts represented by async owned graphs and borrowed descriptors.

Owned edges store handles, so a recursive type does not require an infinite
frame. Typed reference edges keep the existing acyclic representation rule.
This classifies layouts only; lifetime and ownership checking remain separate.
"""

from structure_views import scalar_field_mode
from numeric_core import numeric_type


def async_structure_shapes(layouts):
    represented = set()
    leaves = {'Int', 'String', 'Vector<Int>', 'Vector<u8>'}
    while True:
        candidates = set(layouts)
        while True:
            available = leaves | candidates
            supported = {typ for typ in candidates if all(
                scalar_field_mode(declared) is not None or declared in ('&Int', '&mut Int')
                or typ.startswith('__crust_closure$') and declared.startswith('&')
                and numeric_type(declared[1:].removeprefix('mut '))
                or declared.startswith('A<') and declared[2:-1] in available
                or declared.startswith('&') and declared.removeprefix('&').removeprefix('mut ') in represented
                for _, declared in layouts[typ])}
            if supported == candidates:
                break
            candidates = supported
        if candidates <= represented:
            return represented, represented.copy()
        represented.update(candidates)
