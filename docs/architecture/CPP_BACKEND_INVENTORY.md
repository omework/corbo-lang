# Exhaustive PostAST and memory-plan C++ inventory

## Completion rule

Passing backend tests is validation evidence. It does not define backend scope.
C++ generation is complete only when every applicable semantic representation
and every physical memory-plan operation has an explicit translation path.

The executable inventory is
`rust_frontend/src/cpp_backend_inventory.rs`. Its matches have no wildcard arms,
and every physical-plan record is destructured without `..`. Consequently, a
new PostAST or memory-plan variant, or a new physical-plan field, cannot compile
until its C++ disposition is declared. `Backend::audit_representation_inventory`
then traverses every representation present in the concrete handoff before any
C++ is emitted.

## Dispositions

| Disposition | Meaning |
| --- | --- |
| `Emitted` | Produces typed C++ IR, a declaration, an expression, a statement, or an explicit foreign fragment. |
| `ExecutionGraph` | Is emitted from resolved execution moments and edges rather than from lexical order. |
| `PhysicalPlan` | Is consumed from layout, storage, cursor, cleanup, async-frame, or foreign layout plans. |
| `SemanticFact` | Has already affected a resolved operation or plan and has no independent runtime instruction. |
| `AbstractOnly` | Is valid in symbolic/parametric PostAST but must not reach a concrete C++ body. |
| `NoRuntimeRepresentation` | Deliberately occupies no runtime bytes and emits no instruction. |

An empty statement list is therefore not an implicit omission. It is permitted
only for units classified as graph, physical, semantic fact, abstract, or
representation-free, and abstract forms are diagnosed if they reach concrete
generation.

## Exhaustive semantic families

The source inventory covers every variant of:

- `Operation`, including arithmetic and compound assignments, calls,
  aggregate construction and projection, control flow, propagation, closures,
  futures, ownership, pools, growing storage, unchecked/foreign regions, and
  runtime checks;
- `TypeDefinition`, `PredicateKind`, `NativeOperationKind`,
  `PrimitiveOperation`, `RuntimePrimitiveKind`, `RuntimeLaunchKind`,
  `CollectionOperationKind`, `ConstantValue`, `NumericType`, `PlaceRoot`,
  `PlaceProjection`, `PatternTest`, `BodyOwner`, `InstanceResolution`,
  `ExecutionPhase`, `ForeignBoundaryEffects`,
  `TransferKind`, `ResolvedDereference`, `ResolvedIndexAccess`,
  `ResolvedSliceAccess`, `ResolvedIteration`, `AwaitProtocol`, `EqualityKind`,
  `StructuralReplicationStrategy`, `DefaultInitializationKind`,
  `ErrorConversion`, `RuntimeCheck`, `FailureContinuation`, `ExecutionEdge`,
  `PositionSelector`, `ForeignOperandMode`, and `ForeignFragment`.

Control operations such as `if`, `match`, loops, short-circuiting, branch
completion, `await`, and `yield` are driven by `ExecutionMoment` and
`ExecutionEdge`. `ForControl` does not rediscover iteration: ordinary resolved
calls/projections produce the item, while the graph and planned iteration
counter implement repetition.

`break`, `continue`, and `return` consume their resolved scope-exit cleanup
plans before control leaves the current path. The backend never reconstructs an
enclosing scope from syntax.

## Exhaustive physical families

The inventory covers all variants of `NativeDescriptorLayout`, `LayoutSize`,
`ValueStorageKind`, `ValueStorageAbsence`, `StorageCreation`,
`BackingStorageKind`, `DataStackKind`, `MemoryBudget`, `CursorExpressionKind`
and `CleanupAction`.

It also records every complete physical record consumed by generation: target
and aggregate layouts; datastacks, scope cursors, regions and region classes;
reservations, guarded value storage, edge transfers and iteration counters;
backing plans; cursor expressions and snapshots; exit cleanup; async frame
layouts, saved values and transitions; and foreign regions and operand layouts.

Reservations and temporaries bind values directly to planned datastack ranges.
Aliases reuse already-planned physical values. Cursor expressions are translated
exactly as supplied by the planner. Cleanup invokes destructors, releases pool
allocations, rewinds cursors, returns regions, and restores region classes from
their planned identifiers.

## Non-applicable concrete forms

Parametric transfers, unresolved contract futures/methods, symbolic positions,
runtime-sized concrete layouts and intrinsics without a runtime binding are not
silently approximated. They may exist in abstract PostAST, but concrete
generation reports an explicit handoff error if one survives specialization or
physical planning.

This separation keeps the PostAST and memory plan as the sole semantic source
for C++ generation. Tests validate the implementation of this inventory; they
do not enlarge or reduce it.
