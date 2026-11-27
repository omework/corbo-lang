# Primitive C++ runtime

The active C++ backend embeds the readable headers in [cpp/](cpp/) through
[corbo_runtime.hpp](corbo_runtime.hpp). These implement explicit bounded
memory, pools, regions, maps, synchronization, task scheduling and OS-reactor
bridges. The compiler remains responsible for program-specific layouts,
placement decisions and explicit recursive cleanup.

| Source | Responsibility |
| --- | --- |
| `cpp/core.hpp` | Primitive arithmetic, bounds and runtime failure helpers |
| `cpp/memory.hpp` | Guarded virtual-memory datastacks, cursors, metrics and page reclamation |
| `cpp/pools.hpp` | Stable slots, allocation descriptors and hole reuse |
| `cpp/regions.hpp` | Bounded growing payloads, regional bands and deferred release |
| `cpp/maps.hpp` | Stable entries and rebuildable indexes |
| `cpp/sync.hpp` | Mutexes, channels and wait registrations |
| `cpp/tasks.hpp` | Explicit task frames, native workers, polling, wakeup and result cleanup |
| `cpp/reactor.hpp` | Read/write wait cohorts and completion wakeup bridges |
| `cpp/bridge.hpp` | Plain descriptor helpers for unchecked STD implementations |
| `cpp/text.hpp`, `cpp/process.hpp` | Text views, formatting and process arguments |

There are no generated smart pointers, STL containers, exception-driven control
flow or automatic C++ destructors implementing Corbo ownership. Placement `new`
starts plain object lifetimes in already reserved storage; it does not allocate.
Platform threads, virtual mappings and wait primitives remain explicit native
boundaries. See [the target contract](../docs/CPP_BACKEND.md).

The compiler's `scripts/cpp_runtime.py` packs these readable headers into its
emitter resource. Edit the headers and regenerate; do not edit packed byte arrays.
The committed STD/runtime pin is changed separately after a release is committed.

## Historical comparison sources

The previous [Corbo runtime](corbo/README.md), C fragments and `corbo_runtime.h`
remain source/history references for the earlier backend. Their C-only build
scripts require a historical compiler with `--emit-runtime-c`; the new backend
does not use them or fall back to them. Earlier execution evidence is retained
in [the runtime cycle](../docs/cycles/CORBO_RUNTIME_CYCLE.md).

Current runtime and generated-code execution evidence, including Linux/Windows
limits, is recorded in the compiler repository's `docs/CPP_BACKEND_CYCLE.md`.
Windows ARM64 native execution remains deferred.
