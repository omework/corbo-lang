"""Contained nominal layouts and a by-value ABI for borrowed substructures.

The descriptor has no ownership or cleanup operation. Compiler loan checking
must keep its root alive; copying this C value does not authorize a language
level copy of a mutable borrow.
"""
from dataclasses import dataclass

from numeric_core import FORMATS, c_print, numeric_type


def scalar_field_mode(typ):
    if typ == 'bool':
        return 'bool'
    primitive = numeric_type(typ)
    return FORMATS[primitive].mode if primitive else None


FIELD_C_TYPES = {'bool': 'int', **{typ: spec.c_type for typ, spec in FORMATS.items() if typ != 'i32'}}
FIELD_TAGS = {typ: 4 + index for index, typ in enumerate(FIELD_C_TYPES)}


def numeric_field_printer():
    cases = []
    for typ, tag in FIELD_TAGS.items():
        display = ('printf("%d", value);' if typ == 'bool' else
                   c_print(FORMATS[typ].mode, 'value').replace(r'\n', ''))
        cases.append(f'    case {tag}: {{ {FIELD_C_TYPES[typ]} value; '
                     f'memcpy(&value, bytes, sizeof value); {display} break; }}')
    return ('static void cell_print_numeric_field(unsigned char kind, const unsigned char *bytes) {\n'
            '    switch (kind) {\n' + '\n'.join(cases) +
            '\n    default: fail("unknown numeric field");\n    }\n}\n')


def field_kind(typ):
    if typ.startswith('A<'):
        return 2
    if typ.startswith('&'):
        return 1 if typ in ('&Int', '&mut Int') else 3
    return FIELD_TAGS.get(typ, 0)


def field_size(typ):
    # Legacy Int projections use int pointers. Smaller fields must leave
    # the next field on the same alignment boundary.
    kind = field_kind(typ)
    ctype = ('int' if typ in ('u8', 'u16') else FIELD_C_TYPES.get(typ)
             or ('CrustStructureView' if kind == 3 else 'Cell *' if kind else 'int'))
    return f'CRUST_FIELD_STRIDE(sizeof({ctype}))'


@dataclass(frozen=True)
class ContainedLayout:
    path: str
    typ: str
    first: int
    count: int


class StructureSchemas(dict):
    """Existing aggregate leaf schemas plus nominal interior projections."""
    inline_structures = None


def contained_field(schemas, typ, path):
    return next((view for view in (getattr(schemas, 'inline_structures', None) or {}).get(typ, ())
                 if view.path == path), None)


def paths_overlap(left, right):
    return left == right or left.startswith(right + '.') or right.startswith(left + '.')


def project_fields(fields, path):
    if not path:
        return fields
    prefix = '.' + path + '.'
    return tuple((key[len(path) + 1:], targets) for key, targets in fields
                 if key.startswith(prefix))


def prefix_fields(fields, path):
    if not path:
        return fields
    return tuple(('.' + path + key, targets) for key, targets in fields)


def contained_layouts(structures):
    """Preserve nominal interior types alongside the existing leaf layouts.

    Offsets are expressed as leaf indexes. C sizes/alignment are supplied by
    the backend, never guessed from the machine running the Python compiler.
    """
    result = {}

    def build(typ, active):
        if typ in result:
            return result[typ]
        if typ in active:
            raise ValueError('cycle de structures contenues directement')
        count, views = 0, []
        for field, field_type in structures[typ]:
            if field_type in structures:
                children, width = build(field_type, (*active, typ))
                views.append(ContainedLayout(field, field_type, count, width))
                views.extend(ContainedLayout(field + '.' + child.path, child.typ,
                                             count + child.first, child.count) for child in children)
                count += width
            else:
                count += 1
        result[typ] = tuple(views), count
        return result[typ]

    for typ in structures:
        build(typ, ())
    return {typ: views for typ, (views, _) in result.items()}


STRUCTURE_VIEW_RUNTIME = r'''
/* A view carries its root and offset by value. It never points at another
   view descriptor, so returning it cannot retain a callee's stack variable. */
static CrustStructureView structure_view(Cell *root, size_t offset, size_t size,
                                         const Source *layout) {
    if (!root || !root->alive || !layout || root->storage_size < sizeof(Cell))
        fail("invalid structure view root");
    size_t available = root->storage_size - sizeof(Cell);
    if (offset > available || size > available - offset)
        fail("structure view outside allocation");
    return (CrustStructureView){root, offset, size, layout};
}

static CrustStructureView structure_subview(CrustStructureView parent, size_t offset,
                                            size_t size, const Source *layout) {
    if (offset > parent.size || size > parent.size - offset || offset > SIZE_MAX - parent.offset)
        fail("structure subview outside parent");
    return structure_view(parent.root, parent.offset + offset, size, layout);
}

static CrustStructureView structure_whole_view(Cell *cell) {
    return structure_view(cell, 0, cell->storage_size - sizeof(Cell), cell->layout);
}
static CrustStructureView structure_reference_identity(CrustStructureView view) { return view; }
static Cell *cell_reference_identity(Cell *cell) { return cell; }

/* The destination's type is fixed after all branches have been checked.
   Convert only the representation, without allocating or moving the target. */
#define structure_reference_for(destination,value) _Generic((destination), \
    CrustStructureView: _Generic((value), CrustStructureView: structure_reference_identity, default: structure_whole_view), \
    default: cell_reference_identity)(value)

static unsigned char *structure_view_address(CrustStructureView view, size_t offset,
                                             size_t width) {
    if (!view.root || !view.root->alive)
        fail("inactive structure view root");
    if (offset > view.size || width > view.size - offset)
        fail("structure field outside view");
    return (unsigned char *)view.root->fields + view.offset + offset;
}

static void *structure_reference_address(CrustStructureView view) {
    unsigned char *payload = structure_view_address(view, 0, 0);
    return view.offset == 0 && view.layout == view.root->layout ? (void *)view.root : (void *)payload;
}

static int structure_view_load_int(CrustStructureView view, size_t offset) {
    int value;
    memcpy(&value, structure_view_address(view, offset, sizeof value), sizeof value);
    return value;
}

static void structure_view_store_int(CrustStructureView view, size_t offset, int value) {
    memcpy(structure_view_address(view, offset, sizeof value), &value, sizeof value);
}

static Cell *structure_view_load_ref(CrustStructureView view, size_t offset) {
    Cell *value;
    memcpy(&value, structure_view_address(view, offset, sizeof value), sizeof value);
    return value;
}

static void structure_view_store_ref(CrustStructureView view, size_t offset, Cell *value) {
    (void)structure_view_address(view, offset, sizeof value);
    cell_store_ref(view.root, view.offset + offset, value);
}

static CrustStructureView cell_load_view(Cell *cell, size_t offset) {
    CrustStructureView value;
    memcpy(&value, (unsigned char *)cell->fields + offset, sizeof value);
    return structure_view(value.root, value.offset, value.size, value.layout);
}

static void cell_store_view(Cell *cell, size_t offset, CrustStructureView value) {
    memcpy((unsigned char *)cell->fields + offset, &value, sizeof value);
}

static CrustStructureView structure_view_load_view(CrustStructureView view, size_t offset) {
    (void)structure_view_address(view, offset, sizeof(CrustStructureView));
    return cell_load_view(view.root, view.offset + offset);
}

static void structure_view_store_view(CrustStructureView view, size_t offset, CrustStructureView value) {
    (void)structure_view_address(view, offset, sizeof value);
    cell_store_view(view.root, view.offset + offset, value);
}

static void structure_view_print(CrustStructureView view) {
    printf("%s(", view.layout->enum_name);
    for (size_t i=0;i<view.layout->field_count;++i) {
        size_t offset=view.layout->field_offsets[i];
        unsigned char kind = view.layout->field_kinds[i];
        if (i) fputs(", ", stdout);
        if (kind >= 4) cell_print_numeric_field(kind, structure_view_address(view, offset, 0));
        else printf("%d", kind ? structure_view_load_ref(view,offset)->value : structure_view_load_int(view,offset));
    }
    puts(")");
}

/* Bodies are specialized for the concrete reference representation. */
#define cell_load_int(cell,offset) _Generic((cell), CrustStructureView: structure_view_load_int, default: cell_load_int)(cell,offset)
#define cell_store_int(cell,offset,value) _Generic((cell), CrustStructureView: structure_view_store_int, default: cell_store_int)(cell,offset,value)
static unsigned char *cell_numeric_address(Cell *cell, size_t offset, size_t width) {
    (void)width;
    return (unsigned char *)cell->fields + offset;
}
#define cell_numeric_address(cell,offset,width) _Generic((cell), CrustStructureView: structure_view_address, default: cell_numeric_address)(cell,offset,width)
#define cell_store_numeric(cell,offset,type,value) do { \
    type payload_value = (value); \
    memcpy(cell_numeric_address(cell, offset, sizeof payload_value), &payload_value, sizeof payload_value); \
} while (0)
#define cell_load_ref(cell,offset) _Generic((cell), CrustStructureView: structure_view_load_ref, default: cell_load_ref)(cell,offset)
#define cell_store_ref(cell,offset,value) _Generic((cell), CrustStructureView: structure_view_store_ref, default: cell_store_ref)(cell,offset,value)
#define cell_print(cell) _Generic((cell), CrustStructureView: structure_view_print, default: cell_print)(cell)
#define cell_load_view(cell,offset) _Generic((cell), CrustStructureView: structure_view_load_view, default: cell_load_view)(cell,offset)
#define cell_store_view(cell,offset,value) _Generic((cell), CrustStructureView: structure_view_store_view, default: cell_store_view)(cell,offset,value)
'''
