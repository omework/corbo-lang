# Rust semantic population — initial implementation

## Scope and status

This is core compiler work, not a STD API change. The new stage consumes the
source-preserving syntax AST. It does not call `legacy_parser`, `tree`, `flow`,
`verify`, `c_backend`, or a backend executable. No normative rule was changed.

The historical checkpoints below describe successive implementation subsets.
The current construct-level coverage and executed evidence are recorded in the
final section. This is a semantic handoff, not rule-safety or backend validation.
The old `check` and backend paths remain separate and are not migrated here.

## Inspectable implementation

- `rust_frontend/src/post_ast/model.rs`: canonical semantic IDs, declarations,
  operations, objects, provenance, dependency/placement summaries and timelines.
- `rust_frontend/src/post_ast/passes.rs`: stage input/output envelopes.
- `rust_frontend/src/semantic/resolver.rs`: declaration collection, interning,
  contextual typing, concrete bare-generic function specialization, typed operations,
  references, guarded branch joins, symbolic loop instances, function summary
  applications, ownership transfers and logical destination resolution.
- `rust_frontend/src/semantic/integrity.rs`: structural ID/moment handoff audit.
- `rust_frontend/src/main.rs`: `resolve` command reads stdin and prints the artifact.
- `rust_frontend/tests/semantic_stage.rs`: focused inspections of the populated graph.

Canonical schemas were moved into compiler source. The architecture `.rs` files
re-export these definitions; there is no maintained second copy of the model.

## Populated mechanisms

Local module/type/function symbols are declared before bodies. Body bindings
have concrete scopes; source lexical scopes/moments are shared by specializations.
Primitive/reference/tuple/array/nominal types are interned. Literals use contextual
integer/float domains, array peers, function signatures and defaults. Explicit
signed literal bounds apply after the sign. Every value retains a type derivation.

`Assign` and each compound assignment remain separate operation types. Compound
assignment records old-value read, RHS evaluation, compute and write phases.
No rule proof is attempted for access compatibility during these phases.

Primitive loads produce copies with independent binding storage. Nonprimitive
loads retain move provenance. Aggregates adopt their component ownership links.
Borrowed values record targets and lifetime/access obligations, not proof results.
Static text has a static storage origin plus an explicit reference identity.

Function instances have concrete parameter bindings, their own body and result
summary. Repeated bare-generic substitutions share an instance; different concrete
substitutions share lexical source moments but not runtime bindings/events.
Recursive calls retain finite, resolved applications: the callee instance and
actual argument values are available without consulting AST or repeating lookup.
A later analysis must traverse the result/effect graph with these substitutions;
an unresolved recursive dependency is never represented as an empty safe summary.

Each execution moment identifies its body, branch, timeline, lexical anchor,
execution phase, guard and hierarchical instance context. Short-circuit RHS
execution is conditional. Nested iteration contexts retain symbolic coordinates;
unknown counts are not enumerated. `LoopParameter` represents initial/back-edge
values and is the source of post-loop bindings, rather than their original values.
Call results become available at the receive phase, with call and return edges.

Scope storage contains symbolic incoming/relative/upper cursor expressions and
snapshots. This is logical information, not byte offsets or physical placement.
Logical destination analysis follows successive ownership links, including adopted
components, and records conditional cleanup owners and caller-result destinations.
Parent reservations are requirements only. Actual layout/reservation is excluded.

## Executed validation

Host: macOS ARM64. Reused `rust_frontend/target` throughout.

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --test semantic_stage
```

Sixteen focused checks passed at this point: typed calls/compound phases; recording
conflicting mutable borrows without checking; symbolic loops; parent destinations;
branch provenance; semantic errors without partial output; short-circuit timelines;
primitive storage identity; caller-result destinations; call dependency applications;
finite recursive calls; deliberately broken handoff detection; generic instance
reuse; nested loop-carried values; contextual type/boundary errors; static text.
Additional validation results are appended below when actually executed.

These tests inspect representations. They do not execute Corbo code or establish
ownership, lifetime, synchronization or backend correctness. No sanitizer run is
relevant to a backend that was not invoked. No cross-platform execution was done.

## Remaining implementation limits

The resolver reports `ImplementationLimit` and emits no successful partial PostAST
for unsupported syntax. Current explicit limits include:

- Package/import input and qualified type resolution across modules.
- Structural/OR type-contract matching, full nominal generic specialization and
  dependent specialization inference beyond the implemented bare-generic functions.
- Async functions/states, closures/captures, indirect callable invocation and await.
- Match, if-let, for, propagation/unwrap, unchecked and foreign boundary population.
- Diverging child blocks and complete unwind/control-flow joins for return/break/continue.
- Runtime slice/view formation, collection protocols and non-native dereference methods.
- Nonliteral constant expressions and full configurable/override/memory annotations.
- Aggregate equality/replication plans, full component cleanup planning and complete
  guarded lifetime/destination precision over loops and alternative ownership paths.

The initial resolver's coverage must be extended and audited before it can replace
the old semantic path. The public `ResolvedProgram` is not `CheckedPostAst`,
`PlannedPostAst` or `LoweringReadyPostAst`.

### Final checks executed in this pass

- `semantic_stage`: 16/16 checks passed.
- `parser_stdlib`: the permanent exhaustive STD parsing/source-preservation test passed.
- `cargo build --bin corbo-frontend`: passed using the existing target directory.
- Standalone `rustc` checks of both architecture re-exports: passed, artifacts in the same target directory.
- `resolve` CLI smoke: a moved child aggregate produced caller destinations, type
  derivations, move operations, lexical moments and execution moments.
- Unsupported async CLI smoke: nonzero exit, explicit `ImplementationLimit`, empty
  stdout; no partial PostAST advertised as successful.


## Grammar-coverage continuation

The next pass added these mechanisms without invoking rule checking or generation:

- `resolver/constants.rs`: constant dependency traversal, including forward and
  associated declarations; arithmetic, min/max, text and cycle/bound diagnostics.
- `resolver/slices.rs`: dynamic sequence lengths, indexed slice places, explicit
  range endpoints and bounds requirements; string views additionally retain UTF-8
  boundary requirements.
- `resolver/foreign.rs`: lexical unchecked boundaries, addr confinement facts,
  resolved foreign operands and per-output write-back values. Original body
  fragments and parsed header tokens are consumed directly from lexer payloads.
- Enum tag/payload equality plans and primitive-payload enum copy operations.

A missing foreign-region arena was found in the original schema and added to the
canonical PostAST. Operand storage modes and write-back values are now explicit.
The integrity audit checks foreign region/operand/output links.

Twenty focused checks now pass. The permanent STD parser regression also passes.
The foreign-outside-unchecked negative case is rejected by the parser, as required
by the grammar; addr outside unchecked is diagnosed by semantic resolution.
These results do not establish full semantic grammar coverage.

### Unreachable-source decision — retained and implemented

The user chose successful compilation with both unreachable-statement and
undefined-name diagnostics. These are warning-only for unreachable source;
reachable undefined names remain errors. `ResolvedProgram.warnings` carries the
non-blocking diagnostics and the resolve CLI prints their source line/column.

`resolver/unreachable.rs` reuses the resolver's symbol lookup and records
non-executing source, diagnostic-only locals, and resolved/undefined name uses.
Undefined names get no fabricated runtime symbol or type. Lexical scopes and
source anchors are retained; no executable value/moment or allocation is created
for those statements. Syntactically invalid source is still a parser error.

`resolver/control.rs` now models terminating child blocks with internal control
bottom, explicit scope-unwind chains and optional branch continuations. Returning
arms do not contribute false value/continuation edges. Loops preserve normal,
break and continue data paths, and retain only the corresponding back/exit edges.
A scope with no reachable exit has an explicit logical cleanup fact, not an
invented destruction event.

`resolver/patterns.rs` resolves patterns once into tests and extraction plans,
then introduces binders inside their branch scopes. Match and if-let retain owned
or borrowed payload transfers, named/positional field identities, branch guards,
merges or termination, and an unmatched-path coverage requirement. Exhaustiveness
requirements are recorded, not proved by this semantic-population stage.
Named enum field constructors now reuse the field-initialization mechanism.

Twenty-seven focused checks pass at this checkpoint. Remaining open coverage:
packages/imports, structural/effect/configuration annotations, full nominal generic
specializations, closures/async, general callable/iteration protocols,
propagation/unwrap, structural replication and complete cleanup/guarded-flow plans.
No rule checker, physical memory planner or C++ generator was added.


## Nominal specialization, propagation and iteration continuation

This is core semantic-resolution work. No STD API, N1–N8 checker, physical
allocator or C++ generator was added.

The resolver now retains concrete nominal field/variant identities and owner
substitutions (`resolver/nominals.rs`). Compiler-provided Option/Result identities
are explicit (`prelude.rs`), rather than recognized from user spelling. `?` and
`!` retain payload fields, success/failure branches, continuation and unwind
information (`propagation.rs`). Exact-source `from` overloads use one selector in
both ordinary calls and failure conversion (`overloads.rs`). The conversion call
belongs only to the failure branch. Projection provenance retains the source and
selected position, including across resolved function-result applications.

`replication.rs` populates a recursive structural plan with resolved field/type
IDs. The initializer is evaluated once. Zero/one destinations require no
duplication; an empty result does not inherit the seed's dependencies or own it.
Custom destructors and nonstructural fields are retained as explicit restriction
facts for subsequent checking. This pass does not claim they passed that check.

`dereference.rs` shares `invoke_function` with ordinary calls. The separate
`read_place` mechanism reads a reference descriptor without moving it. Wrapper
`*` records the already-emitted ref/mut_ref call and selected permission; it does
not ask a downstream stage to find or execute the method a second time. Universal
ref on a reference targets the descriptor, as specified.

`iteration.rs` uses shared runtime scope construction and the existing loop
engine. The source is evaluated once and owned by a loop-source scope, with
iteration body scopes beneath it. Array/slice access retains a symbolic
IterationIndex and bounds checks; borrowed items use ordinary reference creation.
Concrete next methods use ordinary instance resolution, call effects, Option
identity, conditional payload extraction and resolved pattern bindings. The
ForControl record retains the protocol and full pattern as well as binding IDs.
No parser text rewriting, invented source nodes or downstream method resolution
was introduced. Named child captures use distinct source/destination bindings and
ordinary copy/move operations with their original execution moments.

Executed evidence: **41/41 semantic-stage checks pass**. The newly covered checks
inspect nested structural plans, one seed evaluation, empty dependencies,
wrapper/native dereference, descriptor borrowing, source-once loops, mutable tuple
item references, concrete next method links and named capture provenance. These
checks inspect PostAST facts; they execute no generated program and establish no
rule-safety proof or universal grammar-completeness claim.

Still open: packages/imports, structural/effect/configuration contracts,
closures and callable environments, async state/poll/await, complete generic
constraint inference, collection/native protocols, aggregate default/cleanup
plans, and the full guarded lifetime/destination and per-iteration cleanup audit.
The old downstream checker/generator remains separate from this artifact.


At this checkpoint the permanent whole-STD parser regression also passes, and
both canonical documentation re-export modules type-check independently with
rustc. Structural handoff auditing additionally checks repetition field/type
links, iteration-coordinate/region links and the already-emitted dereference call.
It does not re-resolve method names or decide replication eligibility.


## Core grammar handoff audit — 2026-11-26

The pass returned to core mechanisms rather than extending library interfaces.
No grammar or normative rule was changed during this continuation. The previously
started SliceError declaration is an API change, not evidence of grammar coverage.

`semantic/grammar.rs` exhaustively classifies all 55 `NodeKind` variants and gives
them stable inventory names. The expression resolver has an exhaustive match:
context-only syntax is explicitly distinguished from a standalone expression.
Adding an AST variant now requires updating the inventory and dispatch. Removing
an implementation-limit fallback is not used as evidence on its own.

`tests/semantic_grammar.rs` successfully resolves a multi-module corpus containing
every one of the 55 families in `post_ast_mapping.csv`; the test compares the
actual AST inventory to that file. It includes imports/aliases, target selection,
structural OR contracts and constrained arguments, named and positional enum
payloads, closures, async, control flow, slicing, foreign boundaries and ordinary
expressions. A separate check covers all ten compound assignments, the numeric,
bitwise and comparison operators, short-circuit operations and external calls.
This is bounded construct coverage, not exhaustive grammar-combination coverage.

The continuation also corrected core composition gaps:

- Callable fields share callable invocation; aggregate-producing expressions become
  evaluated temporary places, so receiver expressions are evaluated once.
- Async function items return the same resolved inactive future identity used by
  direct construction and explicit async-function-name task type annotations.
- Generated closure/async environments preserve their enclosing module identity.
- Configured constant uses retain their effective value and configuration ID.
- Place reads retain the evaluated place, read event and root-value provenance.
  Reference-valued projections retain reference descriptor targets; dependencies
  use `CarriedByPlace` at that event, not stale constructor component aliases.
- Replacement snapshots read the previous value from the already-evaluated target;
  the new RHS is never substituted for the previous value to be destroyed.
- Compiler-generated destructor signatures take a mutable reference consistently.
- Terminating unchecked bodies do not fabricate a reachable boundary exit.
- Execution-context requirements retain actual and required modes for later N8
  checking; population deliberately does not compare them to issue a rule verdict.
- Structural handoff validation checks capture, async-frame, configuration,
  projection and context-requirement IDs in addition to existing event links.

Inspectable code is in `rust_frontend/src/semantic/resolver.rs`, its `callables`,
`asynchronous`, `configuration`, `packages` and `foreign` modules, the canonical
`post_ast/model.rs`, and `semantic/integrity.rs`.

Executed representation checks at this checkpoint: **59 semantic-stage checks
and 2 semantic grammar checks passed**, on macOS ARM64 using the shared Cargo
target directory. No rule checker, physical memory planning, generated program,
C++ compilation, sanitizer or platform runtime was executed for these checks.

The artifact remains `LogicalDestinationResult`, not `CheckedPostAst` or
`LoweringReadyPostAst`. Dependency recipes and guarded cleanup obligations are
inputs to later analysis, not proofs. Generic declarations now retain both source templates and canonical symbolically
resolved semantic bodies; concrete instances remain separately identified. See
[RUST_STDLIB_SEMANTIC_AUDIT.md](RUST_STDLIB_SEMANTIC_AUDIT.md) for the six-target
audit and contract-based generic-body evidence.
Whole-STD semantic/API completeness, precision over every combination and legacy
checker/backend migration are not established by this audit.

Final handoff checks also executed successfully: permanent whole-STD parser/source
preservation regression; standalone Rust compilation of both canonical architecture
re-export modules; `git diff --check`. The existing `rust_frontend/target` was
reused for all artifacts. Formatting was limited to the semantic/PostAST modules
and their focused test files.


## Whole-STD composition audit completed

After the user confirmed classical same-block shadowing, the complete STD package
now resolves into the semantic PostAST on macOS ARM64. The permanent audit covers
107 source files and passes structural integrity; 65 focused semantic and
2 grammar-family regressions pass. See
[the complete source corrections, general mechanisms, counts and boundaries](RUST_STDLIB_SEMANTIC_AUDIT.md).
This supersedes the earlier pending-binding-policy checkpoint; it does not add a
rule checker, physical memory planner or code generator.
