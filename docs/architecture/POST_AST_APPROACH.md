# Typed PostAST architecture — approach and review proposal

## Status and scope

This records the approved architecture and the canonical Rust semantic schema.
The definitions now live in `rust_frontend/src/post_ast/{model,passes}.rs`;
[post_ast.rs](post_ast.rs) and [post_ast_passes.rs](post_ast_passes.rs) re-export
that same source for standalone inspection. They are no longer duplicate schemas.

`rust_frontend/src/semantic` now implements an initial syntax-to-PostAST resolver.
It consumes `ParsedUnit` directly, without using the legacy frontend/verifier or
backend. The current implementation is **not complete over the grammar**.
Its supported scope, executed evidence and remaining limitations are recorded in
[the semantic population report](../cycles/RUST_SEMANTIC_POPULATION.md).
The old downstream pipeline has not been connected to this new artifact.
No new rule checker or C++ generator is included in this work.

Approved requirements:

- Resolve symbols, types, names, calls and contracts before downstream consumers.
- Represent semantically distinct operations with distinct Rust types, including
  separate `Assign`, `AddAssign`, `MultiplyAssign`, etc.
- Maintain explicit branch timelines, lexical moments, execution moments and
  branch relationships. They are mandatory architecture, not optional debug data.
- Preserve addresses, references, collections, ownership, scopes and provenance.
- Define every AST-to-semantic mapping and every rule/backend information need.
- Pass each stage's work forward. Rule checking and C++ generation never redo
  semantic resolution or parse source again.
- Make architectural gaps visible; obtain agreement before selecting new language
  behavior. Passing tests do not establish architectural completeness.

Not included: implementing resolution, contract matching, proof algorithms,
storage planning, runtime behavior or C++ emission. No compiler stage is replaced
by this proposal.

## Pipeline and single source of semantic information

```text
source + tokens -> syntax AST
    -> populated PostAst + type/lifetime/transfer facts
    -> logical final destinations
    -> rule checking -> CheckedPostAst
    -> physical memory planning -> PlannedPostAst
    -> complete backend plans -> LoweringReadyPostAst
    -> primitive C++ emission
```

`PostAst` owns resolved semantic information. The proposed population, checking
and memory results retain that same payload and add their own facts.
`LoweringReadyPostAst` retains the complete chain and backend plans. These are
proposed data-state wrappers, not independently resolved representations. Public
structs in the proposal do not mechanically certify that an instance meets a
phase contract; construction gates/invariant validators must
be designed before integration.

Validation may derive liveness, path states and proofs. Planning may select
storage/layout from those facts. Those computations are not repeated symbol,
type, overload or contract resolution. They must have one named producer and
retained results. Any consumer that lacks a needed fact reports a handoff gap;
it does not compensate by reconstructing it from source.

Generic declarations and their source are shared. The retained decision is to
produce and reuse one fully resolved body per distinct concrete specialization.
Known symbolic requirements may be retained in declaration/template metadata,
but an emitted body has concrete types/calls; C++ generation performs no semantic
substitution or contract matching. Logical final destinations are complete before
rule checking; there are no deferred language-rule proofs awaiting placement.

## Top-level ownership

`PostAst` contains:

| Component | Purpose |
| --- | --- |
| `SpecificationIdentity`, `TargetDescription` | Rule/grammar identity and target facts used by the resolution |
| `SourceOrigins` | Source text, original AST identity, spans and causes of synthesized units |
| `Declarations`, `Symbols`, `ResolvedTypes` | Canonical resolved definitions and identities |
| `Scopes` | Scope tree, bindings, exits and symbolic cursor/region information |
| `Objects` | Addresses, references, collections, places and temporal links |
| `Values` | Typed results, provenance and separate per-purpose summaries |
| `ExecutionGraph` | Timelines, both moment kinds, branch relationships and event edges |
| `Contracts`, `EffectSummary` | Resolved requirements, matches, effects and configuration |
| `FunctionBody` | Distinct executable semantic operation types |
| `RuleObligations`, `RuntimeCheck` | What must be established, not assertions that it already holds |

Cross-links use distinct Rust identifier types. A FieldId is not interchangeable
with a BindingId or TypeId. Spelling remains available for diagnostics but is not
an execution target or a substitute for resolved identity.

## Explicit timelines and the two kinds of moment

### Lexical moment

A `LexicalMoment` records written order within its `LexicalContainer`, its scope
and source origin. The proposed containers include modules, type declarations,
function bodies, constant expressions and contracts. Source order is not treated
as evidence of execution precedence across branches.

Retained granularity: one lexical moment per written instruction/declaration,
with operand-specific origins. Synthesized operations share the relevant lexical
moment and retain their own cause. Written/synthesized origins reference that
moment. Non-executing declarations have lexical sites without fabricated runtime
events; no separate compile-time execution timeline has been introduced.

### Execution moment

An `ExecutionMoment` identifies an event, its operation, phase, branch, timeline,
lexical origin and path guard. Phases distinguish reading, computing, writing,
invoking, receiving a result, transferring ownership, suspending, resuming,
destroying and exiting.

Every executable operation has an `OperationSite` with its scope, branch,
timeline, lexical moment and **nonempty execution-moment list**. One lexical
instruction can produce several operations, and one semantic operation can have
several execution phases. Compound assignments explicitly retain their
read/compute/write moments. Their source place is evaluated once and referred to
by `EvaluatedPlaceId`.

No moment ID, phase enum order or Vec position establishes execution order.
`ExecutionEdge` records the relationships. An event is an analysis event, not a
claim that an entire operation is atomic at runtime.

### Branch timelines and relationships

Every `Branch` references a `Timeline`, and each timeline identifies its branch.
A timeline contains its lexical ordering, execution-event membership, entry
moments and exits. Typed branch definitions distinguish root bodies, conditional
branches, match arms and concurrent branches.

Typed relationships record:

- `ExclusiveBranches`: alternatives selected by a decision.
- `BranchFork`: parent moment and child entry.
- `BranchMerge`: guarded incoming moments and a continuation.
- `BranchCompletion`: the contract-established completion, outcome and
  continuation.

Execution edges additionally represent sequence, conditional transitions, loop
back edges, call/return and suspension/resumption. Conditional branch merging
is not concurrent joining. A lexical scope is not a concurrent branch, and a
suspension is not necessarily a new branch or thread.

### Repetition, calls and concurrency

An `ExecutionMoment` is a static event template. `MomentOccurrence` pairs the
event with a parent-linked execution context. Contexts describe calls, loop
iterations, concurrent branches and async instances without enumerating unknown
runtime executions.

The approved iteration notation is hierarchical: `3.x` identifies iteration x
of loop moment 3; `3.x.a` identifies event a inside it. Nested loops can yield
`3.x.5.y.a`. These are presentation labels for strongly typed coordinates, not
floating-point numbers, strings used as identity, or sortable global timestamps.

`IterationMoment` records its LoopRegionId and an `IterationCoordinate`:
`Known(u64)` when that particular occurrence is established statically, or
`Symbolic(IterationVariableId)` otherwise. The region identifies its loop header
moment. The parent context supplies the outer hierarchy; a variable spelling x
alone is never global identity. Distinct symbolic variables are not proof that
two iterations differ; an analysis must establish any equality, difference or
ordering relationship it relies on. The index is an iteration coordinate, not the
source program's loop-variable value. No zero/one-based display convention or
runtime counter instrumentation is selected here.

One canonical context chain owns the hierarchy. Flattened display paths are
derived from it, not a second independently mutable source of semantics.
A known total iteration count does not force unrolling or concrete occurrence
records. Different contexts distinguish repeated allocations, values and owners.
Execution edges and contracts establish ordering; hierarchical coordinates do
not impose a total order on concurrent branches or imply operation atomicity.

A callee's lexical scope is not rewritten into every caller. Call/return edges
and instance domains describe activation ancestry separately. Source order in a
shared function body is reusable across its calls.

## Scopes and memory entities

A scope retains its lexical parent, children, bindings, entry and exits. A child
entry records the parent's lexical moment, execution moment and theoretical
cursor snapshot. `ScopeStorage` includes the relative cursor expression, upper
limit and datastack/region identity. Cursor expressions and snapshots are
symbolic and can be guarded/merged; they are not compiler-global mutable runtime
cursors.

The three memory-entity classes remain explicit:

- `Address`: symbolic allocation identity, type, creation, storage origin,
  initial scope and initial cleanup owner.
- `Reference`: a value in its own right, with its initial scope/owner,
  permission, target origins, projections and parent reborrow.
- `Collection`: descriptor identity, constraints and sparse ownership/borrow
  links. It does not eagerly enumerate all possible elements.

Fields, indices, keys and ranges are selectors. Unknown positions retain symbolic
identities/values; they are not replaced by an arbitrary known index or key.
These are general entities and relationships, not HashMap-specific rule logic.

`OwnershipLink`, `DependencyLink` and `CollectionLink` retain the establishing
moment and guard. Later moves and writes are operations/effects. The immutable
entity definition is not overwritten with one global current owner or moved flag.
`BindingStateAtMoment` and `OwnershipStateAtMoment` describe the state on a path,
including the move event and destination. Ownership identifies the relevant
instance domain where activations/iterations matter.

An allocation's origin remains distinct from its current owner and eventual
physical placement. Moving it does not manufacture another allocation identity.
Scope destination, source pool and cursor reclamation are separate facts.

## Values, provenance and summaries

`Value` retains its resolved type, definition, direct provenance link and IDs of
separate dependency/placement summaries. An operation result records the event
at which it is produced, not just the operation that eventually produces it.

Provenance represents construction, binding origin, moves, forwarding, merges
and call results. Guarded merges retain which source is available on which path.
Dependency summaries distinguish immediate dependencies from dependencies passed
through a deferred result. Placement summaries retain origins and guarded final
scope candidates; the final storage reservation belongs to the storage plan.

Summaries are reusable facts with a defined producer. No particular caching,
fixed-point, recursion or invalidation algorithm is selected here. A flat list
of origins that discards guards is not an acceptable replacement.

## Distinct semantic operations

The Rust file contains **113 distinct executable operation structs** (including loop-carried parameters and sequence place/length operations added during population), organized
by `Operation` for exhaustive dispatch. There is no generic operator-string node.

`Assign` is distinct from all ten compound assignments. Each arithmetic,
comparison, shift and bitwise operation has its own type. `ShortCircuitAnd` and
`ShortCircuitOr` identify conditional execution rather than eager operands.

Resolved numeric domains, equality plans, dereference routes and indexing/slicing
routes are retained. The C++ generator does not decide again whether equality
means numeric comparison, reference/slice identity or enum tag/payload equality.
It does not search for a ref/mut_ref method or infer an indexing implementation.

The inventory also covers binding initialization, receive/forward, move/copy,
borrow/reborrow, construction, replication, patterns, loop/control exits,
propagation/unwrap, call modes, captures, tasks, suspension, branch/lock effects,
cleanup, pool/growing-storage operations and trusted foreign regions.

Some units are semantic effects derived from calls and contracts, not extra
runtime mechanisms. `BeginBranch` does not independently spawn a second thread;
`BeginLockEffect` does not generate a lock implementation. The resolved call or
runtime entry performs the implementation; the semantic units expose its
contractual effects to analysis. Mutex and a function named join have no special
meaning merely from their names.

Array replication retains one seed evaluation and a structural replication plan.
Whether a type qualifies follows the existing language rules; the representation
does not introduce clone, arbitrary copying or a new default-construction policy.

## AST mapping and information ownership

The complete current mapping is [post_ast_mapping.csv](post_ast_mapping.csv):
**all 55 NodeKind variants**, with semantic units, required information, N1–N8
consumers and C++ information. Individual operator forms are in
[post_ast_operators.csv](post_ast_operators.csv): **35 forms**, including all 11
assignment operators, 18 binary operators and six unary forms. Reborrows are
selected from resolved reference context, not a new written operator.

The nested syntax families map as follows:

| Syntax family | Semantic destination |
| --- | --- |
| TypeSyntax Path/Reference/Tuple/Array/Slice/Callable | Canonical resolved type and component identities; written origin retained |
| TypeSyntax Constrained | Resolved contract type parameter and AllowedTypes set |
| PatternSyntax Wildcard/Binding/Tuple/Variant/Field | ResolvedPattern, concrete field/variant IDs, branch binders and extraction operations |
| AnnotationSyntax Marker/Properties | Typed configuration, thread/lock or constant metadata according to the annotation's declared role |
| AnnotationSyntax TypeContract | StructuralTypeContract with a common mode and nonempty OR alternatives, or explicit unconstrained form |
| AnnotationSyntax Branch | BranchContract with resolved completion selector or explicitly unspecified completion |

Mapping is not one-to-one lowering. Parentheses need no runtime operation; a call
or assignment can produce multiple units. Every generated unit needs an origin
and every source unit needs a mapping, exclusion record or documented syntax-only
role. A typed runtime unit may not use a string to rediscover its operation. A known
contract-method requirement is allowed in a parameterized body, but the complete
concrete call resolution must be supplied for any emitted instance. The backend
must not perform contract matching from that symbolic requirement.

## Contract and effect records

OR matching records the complete matching-alternative set and the concrete
method resolutions. It does not select the first alternative, merge &T with
&mut T or invent a conversion. Selection/use policy when several alternatives
match remains open.

Branch completion refers to the resolved contract and result selector. An
unspecified join creates no completion fact; this is not an implicit obligation
to create a handle or always wait for an autonomous task. Deferred effects retain
timing and outcome guards, including the distinction between successful work and
launch failure. Cleanup/completion facts must follow approved contracts.

Lock contracts retain the resolved target identity and through-call/result
extent. Thread-transfer restrictions are attached to resolved types and owned
components. Capture records retain copy/move mode, source binding, destination
field and creation moment. Creating an inactive future must not execute its body.

Foreign regions retain already separated text/operand fragments and resolved
operand identities, types and headers. Code generation substitutes known operands;
it does not reparse ${...} or look up names. `UncheckedOpaque` records the trusted
boundary instead of claiming to infer arbitrary C/C++/assembly effects. Addr-derived
values retain confinement dependencies even if represented as usize.

## Rule obligations versus proof results

| Rule | PostAST inputs and resulting obligation |
| --- | --- |
| N1 | Initialized bindings, typed operands, resolved expected/actual types, variant guards and check requirements |
| N2 | Ownership identities, initial owners, transfer/adoption/release events and path-sensitive owner states |
| N3 | Distinct transfer operations, eligibility/type facts, explicit borrow modes and capture-at-creation facts |
| N4 | Reference origins/projections, storage/pool dependencies, scope exits and branch-completion relationships |
| N5 | Evaluated places, alias/overlap information, access events, active references and resolved lock identities/extents |
| N6 | Guards, definitions/uses, merges, loop/call/suspension edges and exact evaluation relationships |
| N7 | Drop hooks, owned components, dependency order, exit paths, storage reclamation and completed branch cleanup |
| N8 | Resolved signatures, substitutions, call/capture mappings and immediate/deferred effect summaries |

Rule obligations are distinct Rust types. A requirement record is not a proof.
`ValidationResult` contains proofs, guarded state facts and check dispositions.
A required unresolved static proof still prevents a lowering-ready program;
the architecture does not weaken that rule.

Historical documentation disagrees about N5: the memory-model document still
starts with the earlier multiple-mutability policy, whereas the current
LANGUAGE_RULES N5 table states one active mutable borrow per overlapping place.
The user most recently explicitly retained the single-active-mutable prototype.
This discrepancy is reported here, not silently resolved by changing either rule
or hardcoding the older policy into the proposal. Reconcile the normative source
set before implementing the new verifier.

## Information required before C++ emission

`LoweringReadyPostAst` retains the validated PostAST and completed plans:

- Target type/field/variant layouts and ABI choices.
- Storage origins, final reservations, scope/region budgets and cursor actions.
- Exit-specific cleanup actions, dependencies and branch prerequisites.
- Async frame fields, suspension transitions and preserved dependencies.
- Resolved foreign fragments, operand layouts and runtime bindings.
- Proof/runtime-check dispositions and their explicit failure continuations.

No C++ overload resolution, implicit conversion, default construction, smart
pointer ownership or destructor machinery may be used to decide Corbo semantics.
The emitter follows resolved units and plans using primitive C++ constructs.
Target layout, allocation and cleanup planning remain actual compiler work;
putting their result types in this proposal does not implement those algorithms.

User drop hooks and release of storage are distinct actions. Existing approved
hook-before-field-cleanup requirements and dependency-constrained storage release
must be encoded in the cleanup plan. This proposal does not impose a new field
order or invent exceptional-exit behavior.

## Completeness and handoff criteria

Before calling the architecture ready for engine implementation:

1. Every active grammar form maps through an AST form to an explicit semantic
   representation; syntax-only constructs and target exclusions are documented.
2. Every distinct executable operation has a concrete Rust type and defined
   inputs/results; related operators are not collapsed into a spelling field.
3. Every executable unit has a branch, timeline, lexical moment and nonempty
   execution-moment set. Every event belongs to its stated unit and timeline.
4. Entries, exits, exclusive paths, concurrent forks/completion, calls/returns,
   loop back edges and suspend/resume relationships are represented explicitly.
5. Repeated activations/iterations cannot alias identities solely because they
   share a static event, scope, binding or allocation definition.
6. Every resolved operand, call, method, variant, default and conversion is a
   known identity or an explicit symbolic parameter under an approved contract.
   Unknown semantic choices do not enter an emitted body.
7. Ownership, reference, collection and storage links retain guards and relevant
   moments. Merges do not discard provenance or incompatible path states.
8. Every N1–N8 obligation can name its inputs in this schema. A missing fact is a
   schema/producer gap, not permission for the verifier to parse/re-resolve.
9. Every executable operation has a defined C++ lowering and every required
   layout/storage/cleanup/async/runtime plan is supplied before emission.
10. Every check is proved, retained as an approved runtime check, or diagnosed.
    Missing static proof is not an implicit runtime fallback.
11. Origins exist for written and synthesized work, so diagnostics can explain
    declarations, move/borrow creation and relevant branch/execution moments.
12. Each derived fact/summary/plan has one producer, invalidation boundary and
    consumer contract. No stage silently recomputes another stage's decisions.

These are criteria to meet, not claims already established by a compiling file.
Semantic-state cardinality, graph consistency and lowering completeness need
explicit invariant checks after the architecture is reviewed.

## Decisions retained and remaining review

The user retained instruction/declaration lexical moments, lexical-only sites for
non-executing declarations, one resolved body per concrete specialization, and
logical final destinations before checking followed by physical memory planning.
Execution occurrences use the hierarchical loop/iteration/event refinement above.
The earlier deferred-placement-rule-proof proposal is superseded.

The schema is canonical compiler source and remains subject to inspection for missing fields or duplicated
facts. Rust containers, ID allocation, caching, parallel producer scheduling and
algorithm implementations have not been silently finalized by Vec-based examples.

Existing inconsistencies remain reported: legacy `bloc_unsafe` is still written
in the grammar despite the approved @unchecked direction; historical memory-model
text disagrees with the current single-active-mutable N5 prototype. Reconcile the
source documents without using the new resolver to compensate for them. These
are not approvals to invent new language behavior.

OR matching retains all matching alternatives. A concrete specialization resolves
actual method signatures without choosing the first branch or merging reference
permissions. Any genuinely unspecified call ambiguity must be reported before
implementing a policy for it.

## Inspectable checks performed

The proposal was formatted and type-checked as a standalone Rust library:

```sh
rustfmt --edition 2024 docs/architecture/post_ast.rs
rustc --edition 2024 --crate-name corbo_post_ast_architecture \
  --crate-type lib --emit metadata docs/architecture/post_ast.rs \
  -o rust_frontend/target/post-ast-architecture.rmeta
```

The mapping inventory was compared with all 55 current syntax NodeKind variants;
all were present. The 35 operator mappings reference distinct declared Rust
operation structs. These are definition/coverage checks only. No semantic
resolution, rule validation, C++ generation, runtime or platform behavior was
implemented or validated by them. No production compiler files were modified.


## Resolved iteration, dereference and structural replication

The canonical schema now retains recursive field-by-field repetition plans rather
than an empty list of positions. Restriction facts remain separate from checking
those facts. `ResolvedDereference::MethodResult` points to an already-emitted
method call; dereference does not invoke the method again. For loops retain their
resolved protocol, item pattern, source owner scope and symbolic IterationIndex.
A PatternMatches unit records the test on a resolved next() result. These are
semantic units with ordinary sites/moments, not source transformations for later
stages to resolve again. Generic contract matching and full per-iteration cleanup
precision remain incomplete and are tracked in the cycle report.


## Current semantic handoff

The canonical implementation is `rust_frontend/src/post_ast/model.rs` and
`post_ast/passes.rs`; these architecture modules re-export it. Resolved place
reads have `ProvenanceKind::PlaceRead` and event-indexed `CarriedByPlace`
dependency applications. Consumers follow these identities and resolved write
operations rather than reconstructing names or assuming constructor contents are
unchanged. `ConfiguredConstant` carries its effective configuration and value.

Callable fields and temporary receivers share ordinary place/call resolution.
Async function items and named task types share the future identity produced by
direct async calls. Execution context requirements are facts for later checking,
not verdicts produced by population. Grammar-family coverage and its limits are
recorded in `docs/cycles/RUST_SEMANTIC_POPULATION.md`.


## Symbolic generic-body handoff

Each generic source definition has `FunctionDefinition.parametric_body`, pointing
at its canonical `FunctionInstance` with `InstanceResolution::Parametric`.
Its substitutions retain the actual declared `TypeParameterId`s. The body has
ordinary typed operations, scopes, dependencies, lexical/execution moments and
logical destinations; it is not merely an AST template awaiting a sample type.
Existing source-selected concrete instances remain separate semantic artifacts.
This work does not implement downstream monomorphization or machine layout.

Calls on abstract receivers retain `ContractMethodReference` identities for the
applicable declared alternatives. Forwarding a parameter to another constrained
function retains `SymbolicContractEvidence`: provided/required alternative IDs
and resolved requirement signatures. Consumers do not repeat method-name matching.
Methods not guaranteed by the declared interface cannot be used by the body.
Different observable alternative signatures are diagnosed rather than silently
choosing a representative alternative or inventing a conversion.

`CreateContractFuture` and the corresponding poll protocol represent inactive
async interface calls without inventing a concrete state layout. Contract-result
dependencies retain arguments and method identities for later substitution.
`ParametricTransfer` and `CaptureParametric` retain compile-time copy/move choices,
including enums whose eligibility depends on abstract payloads. These choices
carry guarded provenance and moments; they are not runtime control-flow choices.
Abstract cleanup uses a parametric destructor identity rather than an assumed
empty destructor. No ownership, lifetime or synchronization rule is proved here.

The package resolver accepts an explicit `TargetDescription` before selection of
imports/declarations. The permanent STD audit resolves each supported target
selection, then checks artifact references and canonical symbolic-body links.
It does not run target binaries, a rule checker, a physical planner or generation.
