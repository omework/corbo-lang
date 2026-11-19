# Conditional annotations, foreign C and recorded compiler limits

## Scope

This is a core/compiler cycle. It changes the approved conditional spelling,
adds the requested C header parameter and fixes the composition limitations
recorded during the STD work. The active implementation is in
`compiler/corboc/`; the Rust bootstrap remains frozen. No independent audit
or mutation campaign was performed. The memory rules were not changed.

## Integrated changes

- `#(if: condition)` / `#(endif)` replaces the parenthesized-body spelling.
  Nested selections preserve source positions and introduce no scope.
  Selection precedes import resolution, collision checks and C header emission.
  Missing/unmatched markers and invalid conditions are rejected. The migration
  covered 124 compiler, STD and example selections, plus documentation examples.
- `@c(includes={"header.h", ...}) { ... }` accepts explicit literal header
  paths. Selected headers are emitted once per spelling. `${name}` exposes an
  available primitive binding; mutable bindings are lvalues and immutable
  bindings are typed rvalues. C statements require `@unchecked`. C strings,
  character literals and comments are opaque. See [the contract](../FOREIGN_C.md).
- Primitive tuple conditionals now compose nested alternatives, literals and
  tuple-returning calls. Types agree by position. Scalar moves are checked
  before alternatives are merged; use of a moved input after the join is refused.
- Scalar pooled-vector `pop()` uses the existing Option representation and
  checks pool/vector liveness, mutability and conflicting borrows.
- Constructor argument summaries distinguish inputs used during evaluation
  from references actually retained in the returned fields. This includes
  multiple borrowed inputs, transient record configuration, block results and
  the corresponding async constructor marker.
- Slice parameters have separate movable binding and symbolic storage
  identities. Borrowed enum parameters support explicit `match &*value`.
  Qualified constructor results at the end of a block use the same resolution
  as other associated calls.
- The recorded `?` gap is connected from lexing through lowering. The exercised
  cases include Result success/error, Option Some/None, unit and nominal payloads,
  scalar/record references, exact static error conversion, `.await?`, ordinary
  scope cleanup and cleanup of earlier owned call arguments on propagation.
  The receiving binding keeps the payload's dependency summary.

Simple local slice forwarding and plain record-valued method results were
already accepted by the seed compiler. They were rechecked and retained as
regressions; no new implementation is claimed for those two witnesses.

## Executed evidence

`validation/check_core_extensions.py` completed with the final self-hosted
compiler on macOS ARM64:

- 21 programs compiled and executed at O2 with fatal UBSan, with exact stdout.
- 20 expected refusals checked the expected lexer/parser/verifier exit status.
- An additional program used an actual custom header and printed its macro's
  value. Assignment through an immutable C operand was rejected by the native
  C compiler, as required by the rvalue crossing contract.
- A package containing excluded unresolved imports, duplicate declarations and
  a missing C header emitted successfully without that header.

Relevant regressions completed on the host: structural contracts (12 accepted
programs at O0/O2 and 11 refusals), STD iterator adapters (ten accepted programs
at O0/O2 and seven refusals), returned slice records and multiple distinct slice
fields. Earlier runs in this cycle also executed custom synchronous and async
buffered streams. These are functional/regression results, not a safety proof.

| Executable target | Focused programs | Configuration |
| --- | --- | --- |
| macOS ARM64 | 21 passed | O2, fatal UBSan |
| macOS x86-64 through Rosetta | 21 passed | O2, fatal UBSan |
| Linux x86-64 in Docker | 21 passed | O2, fatal UBSan |
| Windows x86-64 under Wine | 21 passed | O2, fatal UBSan traps |
| Windows ARM64 | Not executed | Explicitly deferred |

The compiler ran on macOS ARM64. Other targets compiled and executed its
portable generated C. This does not establish execution of the compiler itself
on those targets or target-selection behavior of a Windows/Linux compiler
binary. Wine execution is not native Windows evidence. Seventeen initial
platform witnesses were compared byte-for-byte against final compiler output;
the four additional witnesses were then executed on each target.

## Reconstruction

The final compiler generated its own package and produced identical C to the
previous generation:

```text
SHA-256  5556f434179528316868fd20aae4245a31dce37a474f04182783b292c1f750a2
```

The normal `corboc build compiler/corboc` command also completed with automatic
STD discovery. The rebuilt binary reproduced the selected foreign-C witness.
The local installation is `build/corbo-install/bin/corboc`, with its rebuilt
successor at `build/corbo-install/bin/corboc-next`.

## Boundaries

Correction to the completion summary: three limits from the earlier generic
adapter/reactor cycle remain open and were omitted from that summary: multiple
different nested specializations of one dependent template, caller-side use of
borrow-bearing tuple returns (notably `split()`), and overlapping readiness
registrations on one descriptor. The executed witnesses in this report do not
establish these capabilities. They remain unchecked in the global checklist.


The focused tuple summary covers primitive result positions. It does not claim
arbitrary resource-bearing tuple alternatives or arbitrary side-effecting
branch bodies. Constructor retained-field summaries cover the direct field
transfers represented by the existing constructor contracts. The propagation
operator uses the existing envelope payload representations; this pass is not
a general implementation of every possible generic Result/Option payload.

Foreign C is a trust boundary. Pointer accesses, hidden threads, retained
addresses and nonlocal C control flow are not verified by Corbo. Header lookup
uses the native compiler search path, not the originating Corbo module's path.

The Rust bootstrap retains the old annotation syntax and cannot bootstrap the
current sources directly. Rebuilding now requires a seed supporting the current
self-hosted grammar. Historical Rust fixtures remain historical reference data.
Native Windows validation, Windows ARM64 and independent adversarial analysis
remain separate, explicitly unexecuted work.

## Reproduction

```sh
python3 validation/check_core_extensions.py --corboc /path/to/corboc --keep /tmp/core-extensions
python3 validation/check_generic_structs.py --native-only --corboc /path/to/corboc
python3 validation/check_std_iter.py --corboc /path/to/corboc --keep /tmp/core-iter
python3 validation/check_rust_buffered_io.py --slice-result --corboc /path/to/corboc
python3 scripts/stdlib_docs.py --check
python3 scripts/runtime_sources.py --check
```

`--cc`, `--runner` and `--reuse-c` select another generated-executable target;
`--only` can select individual positive witnesses. The host compiler's target
selection has already happened when `--reuse-c` is used.
