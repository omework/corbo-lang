# C++ compilation target

The accepted replacement backend generates primitive, C-like C++ from the
post-AST representation. This is a rewrite, not a conversion of generated C.
The compiler's placement and ownership plans remain authoritative.

Generated code uses plain layouts, scalars, pointers, fixed arrays, direct calls,
explicit allocation/commit/cursor operations and explicit cleanup. It does not
use smart pointers, STL containers, exceptions, automatic C++ destructor cleanup
or hidden general-purpose heap allocations. C++ object-lifetime requirements still
apply: raw reserved storage must be initialized in a way that starts the lifetime
of its trivial object representation.

The foreign forms are `@c { ... }`, `@c++ { ... }` and `@asm { ... }`. All require
an enclosing `@unchecked`. Existing implementation blocks were rewritten as
`@c++`; the language retains `@c` regions, which are parsed, resolved into
foreign PostAST fragments and emitted verbatim through the C++ translation
unit. This does not retain the former
C compilation path. The unchecked block's foreign effects remain the developer's
responsibility; restrictions on compiler-generated C++ do not forbid a developer
from using richer C++ facilities explicitly inside that block.

The independent emitter is in the corboc repository's `src/cpp_backend/`.
Default package builds select C++20; the old C emitter has been removed from
active compiler sources. The readable support is under `runtime/cpp/`.
The installed PATH compiler and committed STD pin are not changed by development
validation. Full package reconstruction has executed on macOS ARM64: the C++-built compiler
reproduces its own generated C++ byte for byte. The normal package build command
also compiles an external two-module package with automatic STD discovery.
The development validation used an explicit working-tree STD/runtime override;
the committed pin and installed PATH compiler remain unchanged.

## Runtime continuation evidence

The new readable `runtime/cpp` support uses ordinary structs/functions and explicit
storage transitions. Pool, region, map, guarded memory metrics/reclamation,
mutex/channel and task runtime probes have executed on macOS ARM64 with fatal
UBSan, Linux ARM64/x86-64 in local containers, and Windows x86-64 under Wine.
Cross-platform runs do not yet establish complete generated-code/STD parity.
Windows ARM64 native execution remains deferred. The compiler repository keeps
`CPP_BACKEND_CYCLE.md` and `CPP_BACKEND_CONTINUATION_RESULTS.json` as the detailed
record; the cycle report records the completed fixed point and the exact scope of the
focused execution evidence. Full-source verification currently takes roughly
eleven minutes per emission; this is a known performance cost, not a skipped check.

## Exhaustive completion criterion

Backend completion is defined by the representation inventory, not by the test
suite. `rust_frontend/src/cpp_backend_inventory.rs` contains exhaustive Rust
matches for executable PostAST operations and for the nested semantic and
physical variants consumed by generation. Adding an enum variant makes the
compiler fail to build until the new representation receives an explicit
backend disposition.

Before generating declarations, the backend traverses the concrete program and
its memory plan. Concrete occurrences classified as abstract-only are rejected;
they are never silently skipped and never translated by repeating semantic
resolution. Operations classified as execution-graph or physical-plan units are
realized at their resolved moments or through their planned storage/cleanup
records rather than at their lexical operation site.

The detailed inventory is recorded in
[`architecture/CPP_BACKEND_INVENTORY.md`](architecture/CPP_BACKEND_INVENTORY.md).
