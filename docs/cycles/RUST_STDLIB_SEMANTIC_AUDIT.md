# Whole-STD staged frontend audit — 2026-11-26

## Current result

**The STD audit covers all six supported target selections:** Linux, macOS and
Windows, each on x86-64 and ARM64. Every run loads all 107 `.crb` files as one
package with preserved source/token streams and file-local imports. Target
selection happens before semantic resolution; each target's selected bodies are
resolved on the host. Excluded branches remain parsed and are assessed when their
corresponding target is selected. No source is removed to bypass failures.

Every active generic source definition has a canonical **symbolic semantic
body**, including definitions with no concrete callers. The test requires this
link and checks that its instance retains the definition's real parameter IDs.
No representative types or Cartesian enumeration of specializations are used.
Concrete instances requested by actual source calls still exist separately; their
resolution was not rewritten into a new downstream monomorphization pass here.

| Target | Files | Bodies | Generic definitions resolved symbolically | Function instances (total) |
| --- | ---: | ---: | ---: | ---: |
| linux / x86_64 | 107 | 912 | 71 / 71 | 1477 |
| linux / aarch64 | 107 | 713 | 57 / 57 | 1127 |
| macos / aarch64 | 107 | 931 | 71 / 71 | 1504 |
| macos / x86_64 | 107 | 913 | 71 / 71 | 1479 |
| windows / x86_64 | 107 | 928 | 71 / 71 | 1499 |
| windows / aarch64 | 107 | 928 | 71 / 71 | 1499 |

## Reproduction

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target \
  --test semantic_stdlib --test semantic_stage --test semantic_grammar --test parser_stdlib
```

The whole-STD test is now an ordinary permanent regression, with no ignore marker.
It writes `rust_frontend/target/semantic-stdlib-matrix.json` and one
`semantic-stdlib-<os>-<arch>.json` per selection, including per-file syntax results,
diagnostic/failure status and artifact counts. `semantic-stdlib.json` aliases the
host result. `CORBO_SEMANTIC_AUDIT_TARGET=windows-aarch64` selects one target. On any future
semantic failure it fails explicitly; later bodies are never reported as passed.
The shared `rust_frontend/target` directory is reused.

## General compiler mechanisms corrected

- **Lexical bindings:** the user confirmed classical same-block `let` shadowing.
  Each declaration gets a distinct binding identity; initializers resolve before
  introduction, and earlier references, ownership and cleanup remain attached to
  the earlier binding. This is not assignment or early destruction. Duplicate
  names within one tuple pattern remain errors.
- **Receiver dispatch:** builtin methods are selected from the already-evaluated
  receiver place, rather than a separate syntax-shape/type probe. Fields,
  references and temporary receivers therefore share the same path.
- **Namespaces:** bare lexical lookup does not accidentally bind an instance
  member requiring an explicit receiver. Source `std::runtime` explicitly exposes
  compiler-owned runtime identities through `NativeNamespaceBinding`; downstream
  stages need not rediscover exports.
- **Type constraints:** concrete type evidence flows through nested operators,
  indexing and projections without evaluating operands to obtain that evidence.
  Shift counts can have any integer type, including compound shifts, while result
  type and bounds checks use the shifted operand's domain.
- **Enum payloads:** constructor/pattern payload visibility follows the visible
  enum variant, rather than incorrectly treating payloads as private struct fields.
- **Primitive boundaries:** byte views, UTF-8 validation and fallible numeric
  conversions have typed operands/results and explicit `PrimitiveOperation`
  identities. Numeric conversion uses the existing `NumericConversionError`
  carrier. Byte-slice `content_eq` links to the ordinary STD implementation and
  shared concrete-call machinery; no comparison algorithm was duplicated.
- **Runtime boundaries:** existing process-argument, synchronization and network
  runtime hooks have typed identities/signatures. Futures and runtime waits share
  one ready/pending/suspend/resume-to-poll transition builder. Blocking workers
  accept the existing inactive Future form used by the STD.
- **Handoff integrity:** primitive operands, namespace exports and runtime-wait
  suspension/retry links are structurally checked alongside existing IDs/moments.

There is no dispatch based on a STD filename, particular source snippet, or
combination of enclosing constructs. Builtin API bindings identify existing
compiler/runtime primitives; ordinary source functions retain ordinary call targets.

## STD corrections

The initial audit correctly rejected HTTP `Header.name` and `Header.value`
field/method collisions under ME3. Private fields are now `field_name` and
`field_value`; the existing methods remain `name()` and `value()`.

The audit also exposed existing cross-module API uses whose declarations omitted
`pub`. Documented crypto, File, socket, mutex and timer methods now have explicit
visibility. DER's documented result offsets are explicitly public. Private state
and free implementation helpers remain private; the compiler's privacy checks
were not weakened. The 64-bit binary usize wrappers now use explicit conversions
instead of implicitly mixing `usize` and `u64`.

A direct member-name inventory over all 107 source files passes, including
platform-specific files. That inventory is distinct from target-selected semantic
resolution; every supported target selection is assessed in the matrix.

## Executed evidence and exclusions

- Whole-STD package resolution and structural integrity: passed for all six targets.
- Canonical symbolic-body coverage and parameter-identity checks: passed.
- All-STD direct field/method name inventory: passed.
- Semantic representation regressions: **72 passed**.
- Grammar-family semantic checks: **2 passed**.
- Permanent all-STD parser/source-preservation regression: passed.

The focused regressions include shadowed borrowed values, mixed-width shift
counts, public enum payloads versus private struct fields, runtime namespace
exports and runtime poll retry paths.

This is source → lexer → AST → semantic PostAST, **not rule verification**.
The new chain still records N1–N8 obligations without proving them. Deliberately
conflicting mutable borrows and synchronous await remain representation-only
checks. No legacy verifier was substituted, and no rule checker, physical memory
plan, C++ generation, executable, sanitizer, cross-platform runtime test or corboc
rebuild was performed. Successful STD resolution is not a safety proof.

## Symbolic resolution mechanisms

- Rigid enclosing parameters and unsolved callee inference variables are distinct;
  nested Result/Option and error-enum expected types retain the enclosing IDs.
- Contract method calls carry all applicable requirement references. Parameter
  forwarding records resolved interface-implication evidence; no method names
  remain to be matched by a later rule checker or generator.
- Contract async calls retain inactive futures and the ordinary poll transition,
  with argument dependency recipes and result substitution identities.
- Abstract transfers and captures retain type-dependent copy/move choices,
  including abstract enum payload eligibility, rather than prematurely declaring
  every parameter a move. Generated closure bodies retain their free parameters.
- Nominal fields, variants and recursive cleanup are populated with symbolic
  arguments. Abstract cleanup has a parametric destructor identity.

Inspectable implementation: `rust_frontend/src/semantic/resolver/symbolic.rs`,
`resolver/contracts.rs`, `resolver/packages.rs`, and the canonical
`rust_frontend/src/post_ast/model.rs`. Structural handoff checks are in
`semantic/integrity.rs`; permanent matrix/body-coverage checks are in
`tests/semantic_stdlib.rs`. Focused tests also reject an unconstrained forwarded
parameter and inspect inactive async calls, parametric captures and transfers.

This changes core semantic representation, not STD APIs or language policy. It
adds no filename/snippet dispatch, rule checker, physical allocator or backend.
A target-selection audit does not prove that each target exposes an identical
API: existing target conditions can exclude implementations (including Linux
ARM64 I/O paths). Native execution and platform capability auditing are separate.
