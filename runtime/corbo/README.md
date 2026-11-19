# Runtime implemented in Corbo

The algorithms corresponding to all 114 function definitions in the C reference
are implemented in the `.crb` files here. The existing C files remain the
comparison implementation. Both implementations use `corbo_runtime.h` and the
same C ABI, object layouts, cleanup callbacks and platform contracts.

| Source | Responsibility |
| --- | --- |
| `memory.crb` | Aligned fixed-stack allocation, region placement/lifetime, pools and slot reuse |
| `collections.crb` | Vector movement, map storage and owned-element cleanup |
| `reclaim.crb` | Live-byte boundaries, thresholds and page reclamation |
| `scheduler.crb` | Queueing, polling, publication, parking, joining and draining |
| `values.crb` | Future/handle storage, result extraction, abandonment and classic-stack switching |
| `threads.crb` | Native/blocking workers, launch failures and cleanup ordering |
| `readiness.crb` | Generation-indexed descriptor cohorts, detach/wake and rearm |
| `completion.crb` | Per-request completion state and task wakeup |
| `api.crb` | Public memory-interface policy |
| `primitives.crb`, `*_primitives.crb` | Explicit unchecked machine/ABI operations |
| `corbo_runtime_abi.h`, `exports.py` | ABI layouts, runtime state and typed entry-point marshalling |

## Bootstrap boundary

`corboc --emit-runtime-c FILE` checks a scalar-only runtime translation unit,
without requiring `main`, injecting an allocator, reserving a datastack or
emitting scope-rewind/reclamation calls. Its locals use the native C backend's
call stack/registers. Managed aggregates, pools, references and async bodies are
rejected in this mode. Normal Corbo program compilation is unchanged.

This is a compiler build mode, not a new source-language ownership exception.
The algorithms use ordinary Corbo control flow and explicit primitive copies.
Raw loads/stores, field access, atomics, callback invocation and OS/thread calls
are isolated behind existing `@unchecked`/`@c` boundaries. The current C backend
uses typed C ABI bindings for those operations. This is not a claim that every
machine instruction or platform binding has been rewritten as Corbo arithmetic
or assembly. No allocation/scheduling algorithm is delegated to the C reference.

The ABI bridge retains the existing private runtime structs and TLS/global state
needed by generated applications. It asserts the supported 64-bit pointer and
callback representation. It contains no second implementation of the allocator,
collections, scheduler, cleanup or reactor transitions. System-library thread
creation and its native attribute cleanup remain a platform binding.

## Generation and use

```sh
python3 runtime/corbo/build.py --compiler /path/to/corboc --out build/corbo-runtime
python3 scripts/build_c_runtime.py --implementation corbo --compiler /path/to/corboc --out build/corbo-library
python3 scripts/build_c_runtime.py --implementation c --out build/c-reference-library
```

The compiler must support `--emit-runtime-c`. The build tool retains the checked
combined source, generated C, resource sections and source/function manifest.
It namespaces generated functions before embedding them, so application function
IDs cannot collide. `exports.py` supplies only typed ABI declarations/marshalling;
aggregate input/result adaptation does not implement runtime policy.

The compiler repository's resource generator compiles these sources at its pinned
revision. Its packed byte resources are independently expanded in Python before
embedding and decoded by bounded Corbo code when emitting a program. Installed
compilers contain those resources and do not locate runtime sources at build time.
An explicit development-source override is labelled as such; release/default
builds must regenerate from the exact source pin.

## Evidence

[Runtime parity cycle](../../docs/cycles/CORBO_RUNTIME_CYCLE.md) records executed
comparisons, compiler reconstruction and platform limits. The differential
harness is `validation/check_corbo_runtime.py`. Passing those cases does not prove
all unchecked machine/ABI code safe. Windows ARM64 execution remains deferred.

## Function and ABI documentation

The [generated source reference](../../docs/RUNTIME.md) links every Corbo runtime
function and the C ABI/reference declarations to their comments. Raw-address
primitives document their storage, callback and synchronization obligations.
Regenerate both references and check coverage using the
[documentation workflow](../../docs/DOCUMENTING.md).
