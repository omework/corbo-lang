[Français](MUTABLE_ACCESS-fr.md)

# Mutable references: permission to mutate

Accepted on November 21, 2026. This is a core semantic change, not a new library
API or syntax. Corboc implements separate
mutation-permission, content-effect and lock-protection facts, with focused
validation. Unresolved effects/lock identities remain conservative refusals; the
compiler cycle report records implementation limits and evidence.

## Normative decision

**MA1 — Permission, not uniqueness.** `&mut T` grants permission to mutate the
referenced place. It does not assert that this reference is the only mutable
reference, or the only reference, to that place. Multiple mutable references may
coexist. `&T` grants read access through that reference; it does not by itself
promise that another authorized access cannot change the contents.

**MA2 — Access compatibility.** N5 concerns actual accesses and their effects,
not the count of references. Sequential reads and writes may use different
references to the same place. When potentially concurrent accesses overlap and
at least one writes, the compiler must establish the required synchronization
under the applicable lock contract. The proof must cover every relevant access
and the identity of its protecting lock. Merely creating references while holding
a lock does not protect later accesses. Existing proofs of disjoint places and
ordered, nonoverlapping execution remain usable.

**MA3 — Existing validity rules.** N2, N4, N6, N7 and N8 remain in force. Mutation
permission does not confer ownership or permission to destroy through a borrow.
Ownership remains necessary for destruction and is not sufficient to invalidate
a place still required by a reference. Removal, replacement, storage reclamation
and other invalidating effects must preserve all outstanding dependencies. Ordinary
content mutation does not automatically invalidate references to that content.
Moves, copying, mutable bindings and reference construction keep their existing
rules; this decision does not make mutable references Copy or introduce implicit
borrows or shared ownership.

**MA4 — Branch boundaries.** The compiler tracks dependencies for every branch
that can use a place. A completion point declared through `#(branch: join=...)`
can discharge that branch's execution dependency when reached and established
on the relevant path. Completing one branch does not discharge another branch.
Without a declared or otherwise established completion, the compiler cannot
assume that branch's accesses ended. Handle destruction alone is not completion.
Borrowed results retain their own dependencies after branch completion. Existing
success/failure cleanup effects, early exits and suspended execution remain
path-sensitive. A completion boundary establishes lifetime ordering; it does not
replace the synchronization proof for accesses before completion.

**MA5 — Explicit lock exclusivity remains.** `#(lock: on=...)` and its
`through_result=true` form retain their existing meaning and implementation
responsibilities. Their declared exclusive interval must be tracked separately
from write permission. The change does not allow a second blocking acquisition
whose release depends on passing that same call. Through-result lock retention
ends under the existing destruction/release contract, not merely at the result's
last syntactic use. The compiler relies on the declared contract; it does not
prove that native locking code implements it correctly.

**MA6 — Missing proof means rejection.** Corboc rejects when it establishes a
violation or cannot establish a required lifetime, synchronization or path fact.
It must not accept unknown effects by assuming that `&mut` is unique. Contracts
carry the relevant facts across calls, captures, aggregates and returned values.

## Precedence and implementation status

MA1–MA6 supersede the blanket single-mutable-reference and implicit-exclusive-
reborrow requirements in older B1/B2, returned-loan, aggregate, iterator and async
passages. This includes historical AS9/AS15 and MT1/MT2/MT8 descriptions where
mutable-reference existence alone caused exclusion. Explicit lock contracts,
actual storage-invalidating restrictions, ownership and branch lifetime rules
are preserved. Library operations may still require exclusion because of their
actual effects or explicit contracts, not simply because they receive `&mut`.

No grammar extension is required for the accepted `&mut`, `lock` and `branch`
notations. The compiler repository records the implementation and focused evidence in
`docs/MUTABLE_ACCESS_CYCLE.md`, and the original impact inventory in
`docs/MUTABLE_ACCESS_PLAN.md`. Historical tests and earlier validation reports
describe the former checker; they are not validation of this decision.

## Ordinary lock type names

`Mutex` and `AsyncMutex` have no builtin or reserved-name status. A declaration
with either name follows ordinary named-type, generic-argument and constructor
resolution. Synchronization facts come from contracts, not spelling. The object-level
`#(lock)` shorthand makes public instance methods inherit the receiver contract,
with checked same-object re-entry rejected. See MT11 in
[Async and multithread rules](ASYNC_MULTITHREAD_RULES.md).
