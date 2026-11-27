# PostAST population, logical destinations, checking and physical planning

## Status and approved order

The staged Rust frontend now implements semantic population, logical final
destinations, N1–N8 verification and physical memory planning. C++ lowering is
still a later handoff. The legacy frontend remains present but is not consulted
by these stages.

The user retained this order:

```text
AST
 -> semantic population
    SemanticPopulationResult
 -> logical final destinations
    LogicalDestinationResult
 -> rule checking
    RuleAnalysisResult::Established(CheckedPostAst)
 -> physical memory planning
    MemoryPlanningResult::Planned(PlannedPostAst)
 -> completed backend plans
    LoweringReadyPostAst
```

This supersedes the earlier proposal to defer lifetime/rule obligations until
physical planning. There is no RequiresPlacement rule outcome or post-placement
N1–N8 pass. Logical destination facts must be complete before lifetime checking.
Physical planning checks that its reservations realize those already checked
semantics; it cannot change ownership, infer types or promote a borrowed target.

The Rust definitions are [post_ast_passes.rs](post_ast_passes.rs), importing the
shared schema [post_ast.rs](post_ast.rs). Both re-export the canonical definitions under `rust_frontend/src/post_ast`.
Each successful envelope owns the preceding artifact. Type explanations,
lifetime facts, logical destinations, proofs and target layouts all pass forward.
Rejected or incomplete outcomes are different enum variants; the next pass takes
the successful payload type, not an arbitrary result with an unchecked status.
Rust type-checking does not itself establish semantic invariants in public data.

## 1. Populate the semantic representations

### Symbols, calls and inference

`SemanticPopulationWorkspace` borrows the already parsed syntax. It is the only
proposed location for unresolved name/call requests, pending bindings and
inference variables. There is no second parser. Its TypeTerms can represent
known types, variables, references, tuples, arrays, slices, callables and generic
applications while solving.

Distinct constraints describe same/expected types, contextual literal bounds,
function argument/return types, array peer inference and consistent branch result
types. They define input problems, not an algorithm or permission to insert
coercions. Existing primitive defaults and explicit conversion rules still apply.

The successful PostAst contains resolved TypeIds, not inference variables. Known
generic parameters remain explicit in declarations/templates. A distinct concrete
specialization gets one fully resolved body, reused by equivalent calls; the
backend never applies semantic substitutions or selects methods. The source and
declaration remain shared. The initial resolver implements interning and bare-generic function instance caching. Structural contract matching and generic nominal specialization remain open; see the semantic population report.

TypeDerivation retains why a type was chosen: annotation, signature, peer,
branch result, substitution or primitive default. Diagnostics consume this
explanation rather than performing inference again.

PopulationCoverage retains a nonempty list of dispositions for each mapped AST
node: declarations, operations, resolved types/contracts, scope boundaries,
target exclusions or grouping/forwarding. A node may have multiple outputs.

### Lifetimes and hierarchical execution moments

LifetimeFacts records creations, uses/access kinds, guards, candidate cleanup
owners/exits, target/reference/storage/lock/boundary requirements and deferred
uses through task/handle results. These are requirements and facts, not proofs.

Each use identifies its execution moment and instance context. Contexts contain
typed hierarchical iteration coordinates: loop moment 3 and iteration x give
3.x; an event inside it gives 3.x.a. Nested loops extend the hierarchy. Known
coordinates and symbolic variables are distinct data variants. No unknown
iteration count is enumerated, and no runtime counter or instrumentation is
implicitly requested. A known loop bound does not make every occurrence concrete.

Lexical moments remain instruction/declaration order. Operands retain finer
source origins. Non-executing declarations have lexical sites without invented
runtime events. Execution moments can have multiple read/compute/write/etc.
phases for one lexical instruction; numeric IDs and paths are not a total order.

Every operation-produced Value records both its producer OperationId and the
produced_at ExecutionMomentId. A multi-phase operation does not make its result
available at its lexical beginning.

## 2. Resolve logical final destinations before rule checking

### Follow transfers, not physical addresses

DestinationRequirements retains transfers, guarded final candidates and call-
result storage contracts. Transfers identify the source/result values, entity
identity when relevant, operation/moment, guard and receiver.

LogicalDestinationResult completes those facts with LogicalFinalDestinations.
Each identifies the value, final scope/cleanup owner, cleanup exit, path guard,
choice timing and address-stability requirement. It does not contain a physical
reservation or offset.

This follows explicit moves/forwarding to the last receiver on each path. Every
possible final destination remains attached to its guard. The construction scope
is not mistaken for the final cleanup scope. A borrow alone never authorizes
promotion of its target to a parent. Source pools retain their own lifetime.

The existing G1 priority (scopes attracting more values first) is recorded here
as values associated with candidate scopes, so it need not be rediscovered from
AST/source during physical planning. No new tie-breaking policy is chosen.

### Produce physical requirements without solving them

Logical analysis also produces PhysicalPlacementRequirements, such as:

- Preserve an already established allocation address/source pool.
- Reserve parent storage before entering a child.
- Let the caller supply a newly constructed function result's storage.
- Keep the selected physical storage alive through specified uses or completion.

These are constraints on physical realization. They are not postponed language-
rule proofs and have their own identifier type, separate from ObligationId.

For a function result, the storage contract distinguishes constructing into a
caller reservation from transferring an already existing allocation. Logical
owners, references and storage origins must not be conflated.

## 3. Check rules using complete logical information

RuleCheckInput takes LogicalDestinationResult, not an earlier partially populated
semantic artifact. The checker receives resolved symbols/types/calls, provenance,
ownership links, lifetime requirements, timelines and logical final destinations.
It can derive liveness, alias/overlap facts, branch completion and proofs without
repeating semantic resolution.

RuleAnalysisResult distinguishes:

- Established(CheckedPostAst): required language obligations are established.
- Rejected: a rule fails or a required static proof cannot be established.
- MissingSemanticInput: an earlier compiler stage failed to supply a needed fact.

Missing information is an architecture/implementation gap, not a demonstrated
user-rule violation. Neither failure outcome can be passed to physical planning.
There is no RequiresPlacement outcome. The checker must not reject a valid move
from creation scope alone or claim success while a lifetime proof is pending.

CheckedPostAst retains the logical result, derived guarded states, evidence and
check dispositions. Evidence names the exact obligation and premises: type
identity, owner states, live targets, disjoint places, common lock identity,
branch completion, loop invariants, logical cleanup destinations or call effects.
These are data definitions, not implemented proof algorithms or certificates.

The shared model has separate N1–N8 obligation types. The current single-active-
mutable prototype decision remains authoritative over contradictory historical
text. Lock contracts, reference validity and completion are separate facts.

## 4. Plan physical memory without revising semantics

MemoryPlanningInput accepts CheckedPostAst plus already computed target layouts.
It does not accept a rejected/unresolved RuleAnalysisResult.

The successful PlannedPostAst retains all of those inputs and supplies physical
reservations, sharing groups, storage/cursor plans, cleanup plans and realization
evidence. RejectedMemoryPlan and IncompleteMemoryPlan are separate outcomes.
A physical planning failure does not change the logical destination or turn an
invalid borrow into a valid one.

ReservationAssignment references a stable FinalDestinationId from the earlier
logical analysis. It records the reservation's issuer (parent/caller/existing
storage), reserved_at and construction_at moments, storage origin and actual
reservation. No later stage rediscovers the final destination by following source
names or infers a new receiver.

PhysicalPlacementEvidence connects each realization constraint to its destination,
reservation and previously established semantic premises. This checks the plan's
conformance to accepted semantics; it is not a second lifetime/type analysis.

### Existing placement rules carried forward

From [GROWING_REGIONS.md](../GROWING_REGIONS.md):

- Successive transfers can use storage in the final receiving scope.
- Durable parent storage is reserved before child construction when required.
- The caller reserves storage for a new result constructed by the callee.
- Already constructed allocations preserve their address and source pool.
- Exclusive construction sites can share compatible storage for one receiver.
- Multiple final destinations remain guarded. A path selected before construction
  can select its reservation; a later choice needs an address valid for all paths.
- Async-frame placement consumes the same destination and dependency facts.

ExclusiveReservationGroup retains initializer sites and exclusivity/compatibility
evidence. Its membership does not authorize overlapping simultaneous values.
Physical layout details, allocator algorithms and priority ties are not invented
by these schema definitions.

## 5. C++ receives the single completed artifact

LoweringReadyPostAst owns PlannedPostAst and completed async/foreign/runtime plans.
The retained chain is:

```text
ready.planned.checked_flow.semantics.semantics.post_ast
```

The nested envelopes expose stage ownership; an implementation can provide typed
accessors without copying or independently resolving the payload. Container/API
choices remain reviewable. There is one semantic source, not parallel AST-derived
checker and generator programs.

Required static proofs must already hold. Physical requirements, target layouts,
runtime check/failure routes, cleanup actions, frame transitions and foreign
operands must be supplied. C++ overloads, conversions, RAII or allocator behavior
cannot be used to decide Corbo semantics.

## Handoff completeness criteria

| Boundary | Required | Forbidden repair |
| --- | --- | --- |
| Population -> logical destinations | Resolved identities, types/calls, explicit transfers, effects, lifetime uses and timelines | Reparse, guess a call, lose a guard or invent a move |
| Logical destinations -> checking | All guarded final cleanup owners/scopes, stable-address and source-pool facts | Defer N4 to physical allocation, infer promotion from a borrow |
| Checking -> physical planning | Established rule facts, check dispositions and unchanged logical destinations | Accept an unresolved rule result or alter ownership to fit storage |
| Physical planning -> C++ | Matching reservations/layouts, realization evidence, cursor/cleanup/frame/runtime plans | Re-resolve, recompute destinations or invent C++ semantics |

Every missing fact has a named producer. Unknown semantic choices or required
unproved obligations cannot reach emission. Public Rust fields alone do not
prove graph consistency, completeness or validity; construction gates and
invariant checks are future engine work.

## Retained decisions and remaining work

Approved: instruction/declaration lexical moments; lexical-only non-executing
declarations; hierarchical execution occurrences with symbolic iterations;
resolved body once per concrete specialization; logical destinations before rule
checking and physical memory planning afterwards.

The physical planner is implemented in `rust_frontend/src/memory_plan.rs`. It
computes C-like target layouts, fixed-stack reservations, pool backing areas,
growing region classes, cursor ranges, cleanup/recovery order and realization
evidence. `memory_plan::validate` audits the completed artifact without reading
syntax or repeating semantic resolution. The OR contract retains all matches;
specialization resolves concrete method signatures without first-branch
guessing or merging `&T` with `&mut T`.

## Definition checks

```sh
rustfmt --edition 2024 docs/architecture/post_ast.rs \
  docs/architecture/post_ast_passes.rs
rustc --edition 2024 --crate-name corbo_post_ast_passes \
  --crate-type lib --emit metadata docs/architecture/post_ast_passes.rs \
  -o rust_frontend/target/post-ast-passes.rmeta
```

These definition checks remain useful for the standalone schema. Production
validation additionally runs `cargo test --test semantic_stage --test
rule_check --test memory_plan`. C++ emission is not part of this stage.

## Initial engine integration

The canonical implementation is `rust_frontend/src/semantic/resolver.rs`.
`semantic::resolve(ParsedUnit)` returns `ResolvedProgram` owning the retained syntax
and a `LogicalDestinationResult`, or semantic diagnostics. Unsupported constructs
produce `ImplementationLimit`; they do not return an incomplete successful artifact.
`semantic::validate_population` audits structural ID/moment links, not N1–N8.
The populated subset and gaps are explicitly listed in
[the cycle report](../cycles/RUST_SEMANTIC_POPULATION.md).

Population required these explicit handoff refinements:

- Distinguish source lexical scopes from concrete specialization scopes.
- Give every execution moment its hierarchical instance context, not just its uses.
- Distinguish anonymous signature parameters from named concrete body bindings.
- Keep each concrete function body/result summary on its instance; share the source template.
- Preserve recursive call effects and return dependencies as resolved applications
  with actual argument values. Traversing this graph later is not name/type resolution.
- Record reference creation moments and static literal targets explicitly.
- Model loop-carried values as `LoopParameter` operations, rather than resetting
  a binding to its pre-loop value after the loop.
- Keep logical cursor expressions and caller-result destinations before physical planning.
  No bytes, alignments, runtime allocation or physical reservation are selected here.

## Current dependency/destruction handoff additions

The canonical schema now retains `DependencyRequirement::CarriedByParameter` for
owned formal contents. This is an origin recipe: callers substitute the actual
value's dependencies; the formal parameter's stack slot is not mistaken for the
referenced target. The semantic producer records the recipe once, and the rule
consumer follows the resolved binding/instance IDs.

`VerifiedDestructionStep` distinguishes `Hook`, `OwnedComponent` and `EndLifetime`.
Component positions and their destructor predicates remain resolved identities;
the backend must not rediscover field types or infer which hook to call. The user
hook borrows `&mut self`; responsibility for the complete teardown belongs to the
destruction procedure. Consuming patterns on values with custom hooks require a proof of compliant
initialization, ownership and destruction under N1/N2/N7. If that proof cannot be
established, reject them; do not change the frozen specification or invent hook
timing in code generation.
