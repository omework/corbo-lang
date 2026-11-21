# Foreign C blocks

This is a core compiler feature. A C block must be inside `@unchecked` and
contains ordinary C statements. The block has its own C scope.

```rust
fn main() {
    let mut value: i64 = 0;
    @unchecked {
        @c(includes={"stdint.h"}) {
            uint64_t next = 41;
            ${value} = (int64_t)(next + 1);
        }
    }
    print(value);
}
```

`includes` is optional. An empty set and a trailing comma are accepted. Entries
are nonempty literal header paths containing ASCII letters, digits, `_`, `.`,
`/`, `-` or `:`. Each selected header spelling produces one quoted `#include`
per generated translation unit, after the generated type declarations.
`corbo_runtime.h` is already provided automatically; requesting that exact
header spelling does not emit a second include. Header paths
are resolved by the C toolchain's normal quoted-include search: relative paths
are relative to the generated C file and the toolchain's include directories,
not automatically to the originating Corbo module. Absolute paths are allowed.
No compiler flags or preprocessor directives are accepted in this parameter.

`${name}` explicitly inserts an existing, available, typed Corbo binding,
including a struct, enum, array, tuple, reference, allocation, collection,
Option, Result, Future or handle. Mutable bindings expose the original C
storage. Immutable scalars are typed C rvalues; immutable aggregates are const
C views of their original storage. This preserves binding immutability, not
transitive constness of pointed-to memory. There is no implicit aggregate copy.
The native C compiler checks the resulting C and header declarations.
Strings, character literals and comments are opaque; `${name}` inside those
constructs is not substituted. Braces inside them do not close the Corbo block.

`@unchecked` marks the trust boundary. Corbo does not interpret C pointer
accesses, retained addresses, hidden threads, nonlocal jumps or C cleanup.
The developer is responsible for those effects and the target ABI. This
feature does not introduce a checked C expression result or a new ownership
conversion.

## Corbo types and the runtime library

The C runtime remains available as a library when Corbo later emits machine
code directly. The C11 header [corbo_runtime.h](../runtime/corbo_runtime.h)
contains the canonical layouts for pools, allocation descriptors, regions,
vectors, strings and maps, plus primitive aliases and the public memory API.
The compiler embeds that same header and runtime implementation in generated
programs. It does not require an installed header for a standalone `--emit-c`
translation unit.

For a program's own types the compiler emits:

- `Corbo_Point` for a nominal type named `Point`. Linked packages and generic
  specializations use the resolver's concrete names.
- `corbo_type_point` inside a C block using `${point}`. This local typedef names
  the operand's concrete C type, including inferred and specialized types.
- `.f_x` for a struct field named `x`; original backend members remain aliases
  of the same storage. This also handles names reserved by C, such as `switch`.
- `.items[i]` for fixed arrays, including arrays placed indirectly by the
  datastack plan; `.m0`, `.m1`, etc. for tuples.
- `.tag` and `.v_Number_f_value` for an enum variant `Number { value: ... }`.
  `corbo_tag_Choice_v_Number` names its tag. Within the enum-name component of
  tag macros and the variant-name component of field aliases, `_` is encoded
  as `_u`, so generated separators cannot collide with source names. A variant
  `Alpha_f_B` thus has a field alias `.v_Alpha_uf_uB_f_value`.

These declarations reflect the existing backend layout; they do not introduce
packed layouts or a separate C copy of the object. Per-field anonymous unions
retain member size, alignment and offsets. Runtime descriptors use the layouts
in the header. A slice retains its generated pointer/length representation;
Option, Result and task operands retain their generated concrete layouts.
Use the local operand typedef when its generated nominal name is irrelevant.
The runtime header alone does not contain a particular program's nominal types;
those are declared in that program's generated translation unit. User headers
are included afterwards and can use them.

A `Pool<T>` binding is a `CorboPool *`; `A<T>` is a `CorboAllocation` whose
`slot` points at `T`. A vector or string's growing payload uses `CorboRegion`;
when it is held in `A<T>`, obtain that payload through
`corbo_allocation_data()`. HashMap bindings use `CorboHashMap *`. These aliases
describe the runtime payloads, not an automatic unwrapping of allocation handles.

```rust
struct Point { x: i64, y: i64 }

fn main() {
    let mut point = Point { x: 1, y: 2 };
    let mut memory = Pool<i64>::new(2);
    let mut number = memory.new(3);
    @unchecked {
        @c(includes={"corbo_runtime.h", "assert.h"}) {
            corbo_type_point *p = &${point};
            p->f_x = 10;
            assert(sizeof(Corbo_Point) == sizeof(int64_t) * 2);
            assert(${number}.pool == ${memory});
            *(int64_t *)corbo_allocation_data(&${number}) = 20;
        }
    }
    print(point.x);
    print(*number);
}
```

### Linking and storage

Build the standalone **memory runtime** for C-owned programs with:

```sh
python3 scripts/build_c_runtime.py --out build/c-runtime
cc -std=c11 app.c -Ibuild/c-runtime/include \
    -Lbuild/c-runtime/lib -lcorbo_runtime -o app
```

`--cc`, `--ar` and `--cflags` select the target toolchain. Use an archiver for
that target. The archive covers datastacks, pools, regions and maps; this is
not a new standalone public scheduler API.

A C-owned program calls `corbo_runtime_init()` and `corbo_runtime_shutdown()`.
Generated Corbo already initializes its runtime. Separately compiled C helpers
include the header and link with the generated Corbo translation unit, which
provides the public functions. They then use **the same runtime state**, not a
second pool or datastack. Do not additionally link the standalone archive into
that program: there must be one runtime implementation. In particular, Windows
COFF linkage can otherwise report duplicate runtime definitions.

The API exposes stack allocation, marks/rewind, region append/drop, pool slot
allocation/release, map operations and page reclamation. Marks belong to their
originating thread's stack. Rewind does not run Corbo destructors; the caller
must first finish threads and clean resources that use the reclaimed storage.
Pool handles carry an optional destroy callback; `corbo_allocation_drop()` calls
it before releasing the slot and clears the handle to avoid a second release.
C must initialize a slot before installing a callback that reads its contents.

### Responsibility boundary

Providing a C representation does not extend Corbo's borrow checker or ownership
analysis into C. Every `@c` block is inside `@unchecked`; its body follows C
semantics. Copies, aliases, ownership transfers, retained pointers, threads,
destruction and cursor manipulation are the developer's responsibility. A C
assignment of an allocation descriptor is an ordinary C copy, not an inferred
Corbo move. The developer must preserve Corbo values used after the block and
avoid premature release, stale dependencies and duplicate cleanup.

Region descriptors must remain at stable addresses while registered with their
region stack. A C copy does not relocate the runtime's links to that descriptor.
Never pass stack allocations to `free()`. C writes do not update Corbo ownership
or dependency summaries. No checked ownership wrappers are required here.

This is an experimental **C11 ABI**, versioned by
`CORBO_RUNTIME_ABI_VERSION`. Match the compiler, header, runtime and target ABI;
there is no cross-version or C++ ABI guarantee. Executed platform evidence and
remaining gaps are recorded in the [integration report](cycles/C_RUNTIME_BRIDGE_CYCLE.md).

## Conditional source

```rust
#(if: target.family == "unix")
use std::sys::unix::FileHandle;
#(endif)
```

Selections can nest and introduce no scope. `&&` binds more tightly than `||`.
The supported properties are `target.os`, `target.family`, `target.arch` and
`target.pointer_width`, compared to strings with `==`. Missing or unmatched
`#(endif)` is a syntax error. Source selection precedes import resolution and
header collection: excluded imports, declarations and includes contribute no
collisions or native header requirements. The old parenthesized-body spelling
is rejected by the active self-hosted compiler.

See [the grammar](../CORE_GRAMMAR.ebnf), [language rules](LANGUAGE_RULES.md#conditional-annotations-and-foreign-c)
and [executed validation](cycles/CORE_EXTENSIONS_CYCLE.md).

The compiler and its C-bridge regression fixtures are now maintained in
[corboc](https://github.com/omework/corboc). The language-repository validation
commands remain compatibility entry points; see [the repository boundary](COMPILER_REPOSITORY.md).

## Trusted interior-mutability borrows

`@unchecked` can also enclose a Corbo construction that forms `&mut` to a field
through a shared reference. The STD mutex uses this only after native lock
acquisition. Such a reference keeps its ordinary provenance and lifetime graph;
the compiler does not verify that native locking actually occurred. Public
mutex acquisition therefore uses `lock(&self)` while its guard exposes tracked
mutable payload access. Code outside the trusted block still requires mutation
permission. This does not relax the separate rule forbidding raw-address escape.
