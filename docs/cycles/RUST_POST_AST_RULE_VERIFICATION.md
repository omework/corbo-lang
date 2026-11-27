# PostAST rule verification — canonical obligation audit

This is core analysis work, not an API addition. The new `rule_check` module
consumes `LogicalDestinationResult` and returns the typed `RuleAnalysisResult`.
It imports neither the syntax AST, semantic resolver, legacy verifier nor backend.
No physical memory planning or code generation is run.

## Current checklist

- [x] Independent guarded execution graph and reaching-definition fixed point.
- [x] Derived conditions retain resolved value/predicate IDs in the handoff.
- [x] Initial N1/N3/N6 operand, availability, move, mutation and pattern checks.
- [x] Initial N4 dependency application across calls, aggregate projections,
  logical destinations, pools, join and await.
- [x] Initial N5 disjointness, last use, reborrows, lock intervals/re-entry and
  concurrent effect consumers.
- [x] Initial N2/N7 ownership forest and logical cleanup-order consumer.
- [x] Initial N8 resolved boundary/context/capture/thread-transfer checks.
- [x] 87 focused checks passed: accepted/rejected boundaries, independent
  copy/drop ownership, recursive formal origins, projection precision,
  explicit destruction, loop-carried loans and foreign-address writeback.
- [x] Every declared N1–N8 obligation is accounted for by a proof or an explicit
  rejection; no diagnostic is emitted outside the canonical obligation ledger.
- [x] Implicit/explicit cleanup, deferred mutation effects and collection
  dependency applications are consumed from PostAST facts.
- [x] The STD verifier audit completed for all six supported target selections.
- [x] The regression run, rule matrix and evidence snapshot are current.

## Producer defects found by verification

- `CompletionCapability.established_at` held the launch moment. It now starts
  empty and is populated only from resolved completion applications. Launch is
  not a join or completion proof.
- Assignment writes were missing from inferred effect summaries. Every resolved
  write now records its place, incoming value and dependency-summary identity.
- Value/entity mappings existed only in resolver-private maps. They are now
  retained as guarded `ValueEntityIdentity` records in the canonical PostAST.
- Runtime launches must own executing task state independently of the observer
  handle. `Owner::ExecutionBranch` and `ExecutionBranchEnd` record that existing
  runtime contract separately from the caller's wait-completion capability.
- Explicit `drop(place)` used ordinary implicit primitive copying. It now emits
  the consuming transfer required by V3/L6 before destruction.

V4 explicitly requires a live assignment receiver. An initially considered
optional cleanup-snapshot change was removed; it would have changed that rule.

Structural handoff validation now belongs to `post_ast::integrity`; the semantic
module re-exports its existing public entry point. This prevents the verifier
from depending on semantic resolution. No safety proof is inferred from the
structural integrity checks.

## Correction: copying and consuming destruction are separate

V3 governs value copying. `let second = first` copies an eligible enum into a
new value with its own cleanup owner. `drop(first)` consumes only `first`;
`second` remains available and is destroyed independently. This does not create
two cleanup owners for one value. The initially introduced design gate was
incorrect and has been removed; no copy-eligibility change is required.

## Executed focused evidence

- 87 focused verifier regressions passed after the destructor clarification and
  general dependency/flow corrections. Four decision-graph unit checks also passed.
- All 73 semantic representation checks passed.
- Both semantic grammar-family checks passed.
- Permanent all-STD parser/source-preservation regression passed.
- Six-target STD **semantic population** regression passed after producer
  corrections: all 107 files on Linux/macOS/Windows x86-64 and ARM64. This is
  distinct from rule verification of the STD.
- Canonical architecture definitions compile; `git diff --check` passes.

The focused cases cover guarded moves, loops, borrowed target/source-pool escape,
reference-field replacement, disjoint and overlapping loans, reborrows, returned
references via calls/join/await, reserved destructor invocation, consuming scalar
drop, explicit-versus-implicit cleanup, object lock re-entry and branch completion.
They do not establish full coverage or a general safety proof.

## Inspectable implementation

- `rust_frontend/src/rule_check/mod.rs`: typed verification gate and N1/N3/N6 consumers.
- `guards.rs`, `flow.rs`: per-run predicate table, guarded fixed point and cached
  execution-path/completion queries.
- `facts.rs`: resolved provenance/dependency/effect substitution; no source lookup.
- `safety.rs`, `concurrency.rs`, `effects.rs`, `locks.rs`: lifetime, branch,
  boundary and synchronization consumers.
- `cleanup.rs`, `checks.rs`: initial logical cleanup and runtime-check consumers.
- `rust_frontend/tests/rule_check.rs`: focused verdict and handoff regressions.

## Boundaries

The canonical-obligation audit is complete for the current PostAST producer and
the 107 STD files selected for each audited target. This establishes that every
obligation emitted by that producer was proved or explicitly rejected. It does
not establish that the obligation producer is a complete formal model of every
possible Corbo program, nor is it a general safety proof.

## Destructor clarification applied

`drop(value)` consumes its input. `fn drop(&mut self)` is the hook selected for
that type; it borrows the object while it is still valid. Runtime destruction
calls that hook once, destroys remaining owned components recursively, then ends
the object's lifetime. A user hook replaces only the default empty hook.
`VerifiedDestructionStep::{Hook, OwnedComponent, EndLifetime}` retains that
separation in the verifier handoff; this pass does not generate or execute code.
Independent cleanup uses reverse creation/receipt from execution edges, not entity
indices. Hook target requirements come from resolved read effects and helper-call
applications, rather than a syntactic dereference-count heuristic.

## General dependency and flow corrections

- Dependency queries retain formal owned contents explicitly as
  `CarriedByParameter`; callers instantiate their actual dependencies.
- Recursive value summaries use a monotone consumer worklist. Cyclic traversal is
  not silently treated as an empty completed summary. Formal result origins are
  summarized before applying caller arguments; callee-local predicates are not
  mistaken for predicates of another dynamic invocation.
- Parameter-relative field paths and dereferences are interpreted from resolved
  places. Selected reference fields retain their own targets without attaching
  unrelated fields' targets to them.
- Unchecked confinement propagates through the same dependency summaries. Lock
  and completion capabilities are retained separately from memory targets.
- Branch completion barriers distinguish a later occurrence of the originating
  loop from the launch occurrence. A later iteration's join cannot complete an
  earlier task merely because their static operation IDs coincide.
- Explicit destruction is checked against dependency target identities. Lexical
  containment alone does not keep a destroyed pool alive; moving its descriptor
  is distinct from destroying it.
- Availability uses cached per-binding predecessor queries, with a shared
  decision graph and existential abstraction of predicates unrelated to the
  binding's updates. Abstraction enlarges the path set rather than assuming
  unreachable paths. Body termination remains a lifecycle boundary, not a local
  definition propagated into another call instance.
- Handoff integrity checks validate dependency IDs before rule consumers use
  them. Generated evidence IDs are disjoint from source obligation IDs, and an
  unproved obligation is distinguished from a demonstrated violation.

The earlier interrupted audit binaries are not validation evidence. They have
been superseded by the completed six-target run recorded below.

The decision-graph implication query traverses node pairs directly. A truth-table
regression verifies implication and checks that it allocates no intermediate
nodes. Execution-path searches first prune nodes that cannot structurally reach
the requested target; this removes irrelevant terminal paths without weakening
path conditions.

## Consuming destruction: rule-check review, not a new language decision

The agreed hook borrows a fully valid object. A consuming pattern can move a
non-Copy payload out of an enum that has such a hook:

```rust
struct Item {
    value: i64;
}

enum Packet {
    Stored(Item);

    fn drop(&mut self) {
        match &*self {
            Packet::Stored(item) => { let observed = item.value; }
        }
    }
}

fn extract(packet: Packet) Item {
    match packet {
        Packet::Stored(item) => { item }
    }
}

fn main() {}
```

The grammar and semantic producer accept this input. Inspection exposed that the
initial verifier established it and scheduled the parent hook/component teardown
without a defined policy for the moved payload. The specification explicitly lists
consuming matches with custom destructors outside the implemented subset
(`DROP.md`, destructor-method section). That implementation boundary is not
authorization to reinterpret N1/N2/N7.
The earlier request for new timing semantics was withdrawn. The grammar and
N1–N8 are fixed; the compiler must establish a compliant destruction sequence or
reject the program as unproved. Missing implementation is not missing semantics.

While that proof is absent, `consuming_cleanup_contracts` returns an **unproved N7**
diagnostic for the unresolved operation, not a claim that a language rule has
already been violated. Eligible-enum copies and borrowed patterns are unaffected.
A regression checks only that this unresolved contract is not silently reported
as established. It does not change the language policy.

Additional producer correction: compound writes now record their inferred effect
once, at their resolved Write phase. N5 consumes the operation-independent access
obligations for those writes. Focused accepted/rejected checks cover overlapping
and disjoint places. Loan-use queries also distinguish loop occurrences: a loan
created inside one iteration is not the descriptor created in the next, while a
loan created outside the loop remains live through its actual uses.

At the previous checkpoint the whole-STD audit was incomplete. The fresh
target-selected STD audit has now completed with violations and unproved cases
both rejected.

## Completed six-target STD audit

Executed in release mode for Linux, macOS and Windows, each on x86-64 and
ARM64 target selection. Every run covered 107 STD files.

For every target:

- the canonical applicability inventory is complete;
- zero obligations are unproved;
- zero obligations are unaccounted;
- zero diagnostics exist outside the obligation ledger;
- N1, N2, N3, N6, N7 and N8 have no rejected obligation;
- N4 has 49 explicit rejections in `std::net::http`;
- N5 has one explicit rejection in `std::iter::Reduce`;
- the whole STD verdict is therefore `rejected`, not compliant.

The N4 rejections follow from the current reader contract, which permits the
generic error `E` to depend on the caller-provided buffer. Returning
`ParseError<E>` therefore cannot prove that a local parsing buffer outlives the
error. The N5 rejection follows from `next() -> Option<V>` permitting `V` to
carry a reference into the previous iterator while `remaining(&mut self, first)`
mutably re-enters that iterator. These are contract-level rejections under the
frozen grammar and N1–N8, not missing verifier paths.

The Windows false N1 rejection was a PostAST defect: a scalar address passed to
foreign code did not invalidate the referent's earlier constant value. Foreign
operands now produce explicit writeback facts, and both Windows audits prove all
N1 obligations.

[Compact audit snapshot](../../validation/post_ast_std_rule_restart.json).

## Restarted audit and rejection register

The language designer froze the current grammar and N1–N8. Every accepted program
requires proof of every applicable obligation; the absence of a diagnostic is
not a proof. The completed audit now has a complete applicability inventory for
the emitted obligations, with proof or explicit rejection links. No STD
compliance certificate is claimed because the STD verdict is rejected on every
target. Per-target reports retain the exact diagnostic locations.

[Six suspected valid rejections, controls and reproduction](POST_AST_REJECTED_ACCEPTANCE_CANDIDATES.md).
