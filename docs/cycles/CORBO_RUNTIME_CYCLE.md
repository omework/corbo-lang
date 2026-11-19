# Corbo runtime implementation and C parity

Scope: compiler/runtime implementation and build integration. No normative
language rule changed. This is functional/regression evidence, not an independent
safety audit or a proof about arbitrary unchecked code.

## Implementation

The algorithms for all **114 function definitions** inventoried in the C reference
are implemented in `runtime/corbo/`. Compilation produces 478 internal Corbo
functions and 114 typed ABI entry points. The compiler source lock selects this
implementation by default. The existing C fragments remain selectable and were
not rewritten to accommodate the new implementation.

Corbo now implements fixed datastacks, virtual-memory growth policy, regions,
pool slot reuse, vectors/maps and owned cleanup, page reclamation, task values,
scheduling/parking/publication, native and blocking workers, launch-failure
cleanup, descriptor-generation cohorts and per-operation IOCP completion state.
Public C memory APIs retain the existing header and ABI version.

The remaining C boundary is explicit: ABI struct layouts, raw field access,
atomics, memory operations, typed callbacks and operating-system/pthread calls
are provided by small `@unchecked`/`@c` bindings. The generated target is still C11.
Thread attributes and their platform cleanup remain in that binding layer.
No allocation or scheduling algorithm calls the C comparison implementation.
This is a port of runtime algorithms to Corbo, not removal of every C/platform
binding from the compilation chain.

`--emit-runtime-c` checks scalar runtime source without requiring `main` or
injecting a managed allocator into the allocator. Arrays, pools, managed
references and async bodies are refused in this build mode. Ordinary application
checking remains enabled. Runtime functions are namespaced before embedding, so
application function IDs cannot collide with them. Runtime resources use bounded
packed byte streams; Python expansion and the executed Corbo decoder check their
contents independently of the packing algorithm.

The compiler pins source commit `6c16675e4073dd9778c1ac7c1c73d51ebe1a7199`.
The checked combined runtime source has SHA-256
`0cb95ee67aee51e634dc2ff208d5ca3f9e03bd5fe7a6d45cca5d073ca168e7a3`.
The runtime source is versioned in the language repository; its compiler
integration and immutable source pin are versioned separately in `omework/corboc`.

## Differential execution

`validation/check_corbo_runtime.py` compiles the same C fixture against each
implementation. It checks expected exit status, stdout and stderr as well as
agreement between implementations. The inventory check refuses missing exports.

| Target | Execution environment | Completed executions | Result |
| --- | --- | ---: | --- |
| macOS ARM64 | Native host | 48 | Matched |
| macOS x86-64 | Rosetta | 48 | Matched |
| Linux x86-64 | Docker, GCC | 48 | Matched |
| Windows x86-64 | Zig/MinGW, Wine | 48 | Matched |

Per target: six functional fixtures at O0/O2 with both implementations (24 runs),
plus twelve boundary fixtures with both implementations (24 runs). Unix uses
fatal UBSan; the Windows toolchain uses undefined-behavior traps.

Functional coverage:

- Alignment, fixed-stack marks/rewind, stable region storage, region holes and
  transfers that survive a rewind; pool arm/slot reuse and exactly-once cleanup.
- Vector append/pop/remove, row movement, owned children and map growth,
  replacement/removal with stable entry addresses.
- Classic-stack switching and reclamation/regrowth.
- Inactive futures, yields/polling, native/blocking execution, abandonment,
  joins, draining and launch failures with destructor-order assertions.
- Multiple reader/writer waits, detach, stale generations, rearm failures and
  per-operation completion registrations.
- Default region capacity, including Windows byte/CPU division and zero-available-memory
  behavior using controlled platform values.

Boundary failures cover fixed/pool/region exhaustion, invalid vector index,
misalignment, foreign marks, integer add/subtract/multiply overflow, zero
arithmetic divisors and signed division overflow. Both implementations retain
the same failing exit/status and diagnostic behavior.

The cross-platform resource sections were compared byte for byte with the final
source build, avoiding a stale-implementation comparison.

## Integrated applications and C library

The normal compiler emits Corbo runtime resources directly. Differential C
section replacement is retained only as a test adapter; it is not the normal
compiler path.

Completed host suites with that normal compiler:

- Core extensions: 21 accepted programs at O2, 20 expected refusals, custom
  header/immutable C operand and selection-before-import checks.
- Generic/tuple/registry mechanisms: nine programs at O0/O2, seven expected
  refusals and readiness transition checks.
- C runtime/type bridge: 22 O0/O2 executions, three Corbo refusals and three C
  mutability refusals. Its reference-library subtest remains a C baseline.
- STD iterator suite: owned cleanup, composition, closure captures, collection
  and related expected refusals.
- Runtime emission: two scalar accepts, six managed/unchecked-boundary refusals,
  five pack/expand round trips and a fatal-UBSan execution of the actual Corbo
  decoder across its 64 KiB history boundary.

TCP split, UDP and the production multi-wait registry also completed on all four
targets above: four O0/O2 network executions plus one native registry execution
per target. These exercise real kqueue, epoll and IOCP behavior, in addition to
the deterministic differential fixtures. Each target also refused destruction
of the connection while split tasks still retained it.

The Corbo-backed standalone C memory archive was linked to the existing
`library.c` client and executed on all four targets in the matrix above.
The C-reference archive remains selectable. Both expose the same memory API;
this cycle does not introduce a public standalone scheduler ABI.

## Compiler reconstruction

The source/token capacity was increased to accommodate compiled runtime
resources. Resource packing reduces their source size without an external
compression dependency. A compatible seed must support `--emit-runtime-c` and
the current 4 MiB source/wide-array capacity.

The first transition rebuild intentionally exposed a difference: its old seed
embedded the earlier runtime prelude while the rebuilt compiler embedded the
new source pin. This was not counted as byte-identical self-hosting evidence.
The final comparison uses a seed rebuilt with the same pinned runtime.

Final pinned self-reconstruction completed successfully. Three generated
compiler C files matched byte for byte, with SHA-256
`cb0b0304fa0680c81462562cfaf3187eff4075d4058c2225b794f05ff56719f9`.
The normal `corboc build` command rebuilt the compiler, and that binary compiled
and executed the external two-module smoke package, which printed `42`.
`build/bootstrap/report.json` records `self_verified: true` and the source pin.

## Defects corrected and evidence limits

An x86 UBSan execution detected invocation of a `void (*)(Task *)` destructor
through a `void (*)(void *)` function pointer. A separate typed primitive now
preserves the callback signature. The affected matrix was rerun to completion.
The controlled Windows capacity fixture detected byte-versus-page rounding and
fallback discrepancies; the Corbo policy was corrected and all target runs
completed again.

A full host filesystem caused Wine registry-save errors, including in the C
reference run. Generated temporary compiler cache was reclaimed and that run
was repeated. The stderr assertion was retained. Fixture feature-test macro
ordering was also corrected; a compile failure was not counted as a pass.

No new mutation campaign, ASan claim or independent audit is included. Timed
concurrency cases do not prove fairness or every interleaving. Public C ABI and
unchecked platform operations retain their documented caller obligations.
Windows ARM64 execution remains deferred by explicit user decision; Wine is not
native Windows hardware. Linux ARM64 was not newly executed in this cycle.

## Reproduce

From the compiler checkout, prepare the pinned inputs and rebuild:

```sh
python3 scripts/corbo_sources.py --from-repo ../crust
python3 scripts/runtime_sources.py --compiler /path/to/compatible/corboc
python3 scripts/build.py --seed /path/to/compatible/corboc --verify-self
python3 validation/check_runtime_emission.py --compiler build/install/bin/corboc --keep build/check-runtime
```

From the language checkout:

```sh
python3 validation/check_corbo_runtime.py --compiler ../corboc/build/install/bin/corboc --keep build/runtime-parity
python3 scripts/build_c_runtime.py --compiler ../corboc/build/install/bin/corboc --out build/corbo-library
python3 scripts/build_c_runtime.py --implementation c --out build/c-reference
python3 validation/check_network_waits.py --corboc ../corboc/build/install/bin/corboc --keep build/runtime-network --registry unix
```

The differential/network harnesses accept `--cc` and `--runner` for cross-target
execution. Use the compiler repository's test-only target emitter for alternate
OS/architecture selection. This does not establish native compiler execution on
those target systems. Reports and generated sources are retained under each
`--keep` directory; compiler reconstruction retains `build/bootstrap/report.json`.
