# Foreign C++ blocks

This core feature embeds opaque C++ statements inside `@unchecked` using `@c++`.
The language also retains distinct `@c` and `@asm` regions; all three require
`@unchecked`. Rewriting existing STD/compiler implementations in C++ did not mean
removing C-source blocks from the language.

The reference Rust lexer recognizes all three regions. The existing Corbo parser
and C++ backend have not yet been realigned to the restored `@c` form; the stage
work does not claim end-to-end C integration. See [foreign C](FOREIGN_C.md).

```rust
fn main() {
    let mut value: i64 = 0;
    @unchecked {
        @c++(includes={"stdint.h"}) {
            uint64_t next = 41;
            ${value} = (int64_t)(next + 1);
        }
    }
    print(value);
}
```

## Headers and operands

`includes` is optional. Entries are literal header paths, not compiler flags or
preprocessor directives. Selected headers are deduplicated and emitted after
concrete Corbo type declarations. The C++ toolchain resolves quoted header paths
relative to the generated translation unit and its configured include search.
The generated unit already embeds the primitive runtime; requesting
`corbo_runtime.hpp` does not embed a second runtime.

`${name}` explicitly inserts an available Corbo binding. A local typedef named
`corbo_type_name` identifies its concrete C++ representation. Mutable operands
expose their existing storage. Immutable scalars are values; immutable aggregate
operands are constant references to their existing storage, with no aggregate
copy. Constness is not transitive through stored pointers.

Strings, raw strings, character literals and comments remain opaque to operand
substitution. The foreign braces introduce a C++ statement scope.

## Plain representations

The generated translation unit declares concrete POD layouts before foreign
statements and requested headers. Use the operand typedef rather than depending
on an internal numeric generated type name. Struct fields use `f_` followed by
the field name. Tuples use `m0`, `m1`, etc.; fixed arrays use `items`. Enum tags,
payload members and ownership flags are implementation details visible in the
generated unit, not a stable external serialization format.

A pool has a `corbo_pool` descriptor; an allocation has a `corbo_allocation`
descriptor whose `slot` points to its payload. A growing vector uses
`corbo_region`; a map uses `corbo_map`. These are plain descriptors, not smart
pointers. Source-level wrappers retain their generated fields and do not acquire
implicit unwrapping in C++.

The readable support interface is [corbo_runtime.hpp](../runtime/corbo_runtime.hpp)
and [runtime/cpp](../runtime/cpp/). Shared runtime state uses inline definitions
across translation units. Program-specific nominal layouts are declared by that
program's generated unit, not by the generic runtime header.

## Responsibility boundary

Corbo checks operand availability and its checked-side dependencies. It does not
verify foreign pointer accesses, retained addresses, threads, nonlocal exits or
resource cleanup. Those effects remain the developer's responsibility. Native
addresses must still obey the checked `@unchecked` escape boundary.

Compiler-generated C++ uses primitive layouts, pointers, fixed arrays, direct
calls, nonallocating placement initialization and explicit cleanup. It does not
use STL containers, smart pointers, exception-based control flow or automatic
C++ destructors to implement Corbo ownership. Developers may explicitly use richer
C++ inside their own unchecked blocks; doing so does not extend checked guarantees.
