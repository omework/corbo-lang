# Rust PostAST physical memory planning

Date: 2026-11-27

## Scope

This cycle implements the physical memory-planning stage of the new Rust
frontend. Its only accepted semantic input is `CheckedPostAst`; rejected or
incomplete N1–N8 results cannot enter the planner. The legacy parser, verifier,
placement code and backend are not inputs.

The implementation is `rust_frontend/src/memory_plan.rs`. It consumes resolved
`TypeId`, logical final destinations, target facts, verified cleanup sequences,
resolved predicates and physical placement requirements. It never reads source
syntax, resolves names, infers types, chooses ownership or repeats a rule proof.

## Implemented plan

- C-like target layouts for primitives, references and fat references, tuples,
  arrays, structs, enums, closures, futures, handles, pools and collection
  descriptors.
- Fixed values and collection descriptors on the classic data stack.
- Fixed pool-slot backing areas following the pool descriptor.
- Bounded regional backing for `Vector`, `String` and `HashMap`.
- Local `stack_region` classes, inherited templates, explicit `count` slot
  reservation and a dedicated overflow region stack.
- Parent reservation before child construction and caller reservation for newly
  constructed aggregate call results.
- Compatible, mutually exclusive constructions sharing one reservation, with
  explicit physical exclusivity and layout proofs.
- Explicit, inferred and platform-default data-stack/region budgets. A statically
  proven plan larger than an explicit capacity is rejected physically.
- Verified leaf-to-root destruction actions before cursor rewind or region
  return. Completion retention is carried by reservations and regions.
- One physical realization record for each named placement requirement.
- A standalone integrity audit for IDs, layouts, stacks, cursors, region classes,
  sharing proofs, requirement realization and cleanup order.

The capacity inference is deliberately conservative: it may sum storage whose
lifetimes could later be packed more tightly. This remains a valid upper bound;
placement optimization is not a semantic condition.

## Complete value-storage handoff

The first C++ backend restart exposed an architectural omission in the original
plan: `StoragePlan::reservations` described durable values with an address
identity, but copy-only scalars and other intermediate values had no physical
assignment. The former backend compensated by creating ordinary C++ locals.
That made code generation decide placement and therefore violated the stage
boundary.

`StoragePlan::values` now provides one `ValueStoragePlan` for every resolved
`ValueId`. Its guarded alternatives identify exactly one of these physical
sources:

- a final-destination `StorageReservation`;
- a temporary fixed-value range on a planned datastack, including its start,
  end and allocation moment;
- caller-provided parameter storage;
- a resolved closure-capture field;
- immutable constant storage;
- an alias or conditional alias to another already-planned value;
- an explicit absence of runtime storage for a diverging, `Never`, abstract or
  unsized semantic value.

Move, receive, forward, merge, loop-parameter and parametric-transfer results
are represented as aliases in the memory plan. The C++ backend therefore does
not decide whether to copy bytes or reuse an address. Exclusive alternatives
retain their PostAST guards.

The invariant for later work is:

> Every executable `ValueId` has a planned physical source before C++
> generation. If no source is present, C++ generation must reject the handoff;
> it must never create an unplanned local as a fallback.

The current implementation is intentionally conservative. Temporary ranges are
not yet lifetime-packed beyond the existing scope cursor model, and this pass
does not claim that its upper bound is minimal. Those are planner optimizations,
not backend responsibilities.

## Reservation timing and single physical allocation

The first executable produced by the restarted C++ backend exposed two related
planner defects. The witness was an ordinary binding such as `let value = 20`.
The literal operation produces its `ValueId` before the binding operation makes
the name visible. The initial plan used the binding moment for both events, so
generated code attempted to initialize a null address and only reserved the
final slot one moment later.

`ReservationAssignment` now distinguishes three facts:

- `reserved_at`: when the physical address becomes available;
- `initialization_at`: when the producing operation first writes the value;
- `construction_at`: when the logical destination or binding is established.

For existing local storage, `reserved_at` equals `initialization_at`. A parent
or caller reservation may be earlier, but never later. This keeps direct
construction in the final destination without confusing value production with
name visibility.

The same witness exposed a second defect in the inferred data-stack capacity.
Semantic resolution advances `ScopeStorage::relative_cursor` to record which
storage identities materialize in a scope. The physical planner had reused that
final semantic cursor as its initial physical cursor and then allocated every
reservation again. Cursor expressions therefore described two copies of the
same values while capacity inference counted only one.

Physical planning now starts each scope at the cursor stored in its entry
snapshot. It then lays out reservations, temporaries and backing areas exactly
once. The semantic relative cursor remains evidence for ownership and logical
placement; it is not an already-allocated physical prefix.

The preserved invariants are:

> A planned address is usable no later than the first operation that writes to
> it, independently of when its destination name becomes visible.

> Every physical byte range is introduced by the memory planner exactly once;
> semantic cursor advances are never charged or emitted as physical storage.

The regression witness asserts both the timing distinction and that the first
reservation of a scope starts at the scope-entry cursor. The generated
executable also runs within the inferred capacity. These corrections are
recorded separately because later packing improvements may change cursor
expressions, but must preserve both invariants.

## Logical lifetime end is not physical allocation release

The first enum-match executable exposed a third planner defect. The rule
checker correctly emitted `EndLifetime` for every owned semantic address, but
the physical planner translated every such step into `ReleaseAllocation`.
That action calls the pool-allocation release ABI and is only valid for an
`A<T>` descriptor. Applying it to an inline integer, enum payload or ordinary
stack aggregate reinterprets value bytes as an allocation descriptor and can
corrupt memory.

The corrected stage boundary is:

- `VerifiedDestructionStep::EndLifetime` closes the logical lifetime of an
  entity. It does not prescribe a reclamation mechanism;
- user hooks and owned components remain explicit verified destruction steps;
- `CleanupAction::ReleaseAllocation` is emitted only when the resolved address
  type is `TypeDefinition::Allocation`, meaning an actual `A<T>` value owns a
  pool slot;
- ordinary fixed stack storage is reclaimed by the planned scope cursor rewind;
- regional payloads are released through their planned region actions.

The memory planner performs this classification from resolved PostAST types.
The C++ backend consumes the resulting cleanup actions and never attempts to
infer whether an address denotes a pool allocation.

The preserved invariant is:

> Ending a semantic lifetime and selecting a physical reclamation operation
> are separate facts. A pool slot is released exactly for a resolved `A<T>`
> owner; an ordinary stack address is never passed to the allocation-release
> ABI.

The regression evidence covers both sides: a pool allocation is released
before cursor recovery, while an inline enum payload ends without any
`ReleaseAllocation` action.

## Runtime ABI is planned, not reconstructed

The C++ backend restart also exposed that the initial native descriptor layouts
described abstract three-word or four-word collections rather than the concrete
runtime ABI. For example, a growing value was planned as `(data, length,
capacity)`, while the runtime actually represents it as `corbo_region`; a pool
was planned as six inline bookkeeping words, while `corbo_pool` actually owns a
pointer to a separately reserved `corbo_pool_state`.

This mismatch could only be hidden by making code generation recognize concrete
types and reproduce runtime conventions. That would move physical resolution
back into the backend.

`NativeDescriptorLayout` therefore now carries the exact target offsets and
extents of the runtime-facing values:

- `Vector` and growing `String` use the seven-word `corbo_region` descriptor;
- `HashMap` embeds two planned `corbo_region` descriptors followed by its map
  bookkeeping fields;
- `Pool<T>` is the one-pointer `corbo_pool` descriptor;
- `A<T>` is the three-word `corbo_allocation` descriptor, including the exact
  pool, slot and index offsets;
- execution handles use the one-pointer `corbo_task_value` descriptor.

Pool backing storage is planned with the same precision. A `Pool<T>` plan now
contains separate cursor ranges for `corbo_pool_state`, aligned element slots,
the occupancy bytes and the free-slot index. The runtime entry point
`corbo_pool_init_planned` only initializes those supplied addresses. It cannot
advance a stack cursor or silently choose replacement storage. The older
`corbo_pool_init` remains a runtime convenience wrapper, but generated code must
use the planned entry point.

Region-slot lifetime and region-band lifetime are also represented separately.
Each growing value releases its own planned slot. A local region class records
the exact scope-entry moment at which its shared band becomes current, and each
scope cleanup restores that class exactly once after all member slots have been
released. Code generation no longer infers that several `RegionPlan` entries
share one runtime band.

Consequently an allocation-content projection follows the planned `slot`
offset. It does not assume that the first word of `A<T>` points to `T`. The same
rule applies to later collection operations: they must consume the native
layout carried by `TypeLayout`, or reject an incomplete handoff.

This correction is intentionally recorded here for later inspection and
optimization. Exact ABI planning is a correctness boundary; compacting or
replacing these descriptors remains a separate planner/runtime optimization.

## Evidence

```sh
cd rust_frontend
cargo test --test memory_plan
cargo test --test semantic_stage --test rule_check --test memory_plan
```

The focused planner suite covers fixed aggregates, enum/array/tuple layouts,
child-to-parent placement, caller results, exclusive branches, pools,
Vector/String/HashMap regions, local region classes and overflow, async state
layouts, cleanup order, capacity rejection and all six supported target
descriptions.

The whole STD currently contains programs deliberately rejected by the N1–N8
audit. Those programs correctly do not reach physical planning. This cycle does
not weaken a rule or bypass `CheckedPostAst` to manufacture a whole-STD planning
claim.

## Boundary

This cycle does not emit C++, commit pages, implement virtual-memory commitment,
or replace the legacy command pipeline. It completes the new architecture's
`CheckedPostAst -> PlannedPostAst` stage.
