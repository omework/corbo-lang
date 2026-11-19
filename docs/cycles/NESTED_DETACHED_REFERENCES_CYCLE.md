[Français](NESTED_DETACHED_REFERENCES_CYCLE-fr.md)

<a id="références-détachées-des-descendants-possédés"></a>

# Separate references of the descendants possessed

<a id="règles-et-portée"></a>

## Rules and scope

Ce cycle applique ST12–ST15, H1/H2, B1–B5, D1, T1/T6,
AS2/AS8–AS15, RT6/RT8 and SL1. No normative rules are amended.
A shared return from Outer → A<Inner> → &Int keeps the target
the storage of destroyed carriers.
Access to a child's content remains explicit: `read(&*value.inner)`.
A reference to an Int stored in the bearer cannot survive it;
a mutable reference is not copied to obtain this detachment.

<a id="défauts-corrigés"></a>

## Corrected defects

Fixture `validation/open-nested-detached-reference.crust` was refused
as an unsustainable return. Symbolic projections now retain
the child's type, his own path and the references to his fields.
Task and handle factories make up the originals.

The first connection allowed however a premature drop after await:
the backend was looking for the returned field only in the direct members.
`nested-detached-first-tests-o0.log` keep these invalid acceptances in the
The minimum cases are: `open-nested-detached-target-dropped.crust`
and `open-nested-detached-target-too-short.crust`. The selection of the returned loan
by downhill path corrects these cases; they are not executed as C
supposedly sure.

Three other shortcomings had invalid programs refused:

- The projection of a contract confused the separator owner `/` with
  a part of the field name. Standardization now uses the same
  path that storage metadata.
- The concrete crossing of a contract implied that each intermediary was
  It also follows the edges possessed, checking availability
  of each child, then preserves the descent of the final field.
- The C bridge of a borrowed structure parameter described its references
  Direct but not his children A<T>. Reuses recursive description
  The graph is alive, without taking responsibility for destroying it.

The newspapers `nested-detached-projection-fix-o2.log` and
`nested-detached-owned-traversal-o2.log` keep intermediate refusals.
The patches are `validation/nested-detached-*.py.patch`, relative to
`/tmp/crust-before-nested-detached`.

<a id="contre-exemple-trouvé-après-la-première-clôture"></a>

### Counter-example found after first closing

The first review of thirteen methods covered the public handle from a caller
Synchronous. Use from an async state reveals an additional loss
The tests accepted passed, but the neighbor who destroyed
the target before reading the result was accepted in both stages.
Synchronous directly consuming Outer to render &Int had the same defect.

The newspapers `nested-detached-public-async-unshadowed-o2.log` and
`nested-detached-sync-owned-probe-o2.log` Keep these failures.
minimum `open-nested-detached-public-handle-target-dropped.crust` and
`open-nested-detached-sync-target-dropped.crust`No invalid C of these
The initial public test in the
`nested-detached-public-async-o2.log` used the name r for a child and then
for match liaison: backend refused to take this mask before the check
The final test clearly identifies the charge of the match.

The cause was a double projection: the proprietary arguments provide
already the targets of their fields. Apply again the carrier's path on
These targets invented a field in the outside Int and lost the reservation.
`projected_argument_loans` now reuse the selected target for a
shared field detached, in direct results as in the handles.
The parameters borrowed continue to project from their wearer.
The lot has been reopened; the previous evidence is not presented as
validation of the final patch.

<a id="vérifications-exécutées"></a>

## Audits performed

`tests/test_nested_detached_references.py` has 14 methods.
The O0 passage prior to the projection supplement is
`validation/nested-detached-final-count-o0.log` :
13 methods in 21 273 s, 20 native executions, 25 invalid programmes and
50 refusal checks, one check and one compilation for each case.
At O2, the first 12 methods go to 9,670 s in the
`nested-detached-interactions-o2.log`, then adding native thread passes
separately in 1,102 s in `nested-detached-native-o2.log`.

After the double projection patch, the fourteen methods move to O2
in 12,105 s in `nested-detached-final-targets-o2.log`. Final count O0
in `nested-detached-complete-count-o0.log` passes in 17,753 s : 22 executions
27 invalid programmes and 54 refusal checks.

The tests cover:

- Direct, fabricated, interlocked auxiliary, public handle and waiting function.
  The complement exercises the public handle from an async state and the auxiliary
  synchronous consuming the carrier to make its reference.
- A target independent model × instant × call path: before termination
  both targets are retained; after termination only the returned field
  The public handle also checks the release of the unused field.
- The two paths of conditional return and the protection of the union of
  their targets, even when an argument is a constant.
- The end of the carrier pools before using the external target,
  and the refusal of the reverse case. The possessed storage is never implicitly promoted.
- Inactive task, injected launch failure, normal/failed native thread,
  Select loser, suspensions and immediate re-use of looped slots.
- Expected values and unique destruction of carriers; targets
  borrowed are not destroyed with them.

The native harness uses Clang C11/pthread, Wall/Wextra/Werrar,
Wno-unused-function, fatal UBSan at O0/O2. No new evidence ASan/TSan.

<a id="mutations-et-régressions"></a>

## Changes and regressions

The initial campaign of `tests/run_nested_detached_mutations.py` detects six
the withdrawal of the returned loan makes accept two invalid dropes,
The other five errors cause a valid program to be refused:
loss of the projected type, normalization, owned crossing, children
in the C deck or the detached origin of the handle. The baseline of twelve methods
and the six detections are in `nested-detached-mutations-o2.log`.

The six mutations from the previous batch are also detected after a baseline
15 methods: `nested-detached-historical-mutations-o2.log`.
These selected errors do not define a general detection rate.

The double projection patch adds a seventh mutation, detected by
incorrect acceptance of the drop of the target after waiting for the public handle
in an async state. `nested-detached-final-mutations-o2.log` contains the
Final baseline of fourteen methods and seven O2 detections.

The regression of shared/mutable fields passes 56 methods in 50.678 s:
`nested-detached-sync-regression-o2.log`, with CRUST_SANITIZE=undefined.
Async and C-bridge regressions pass 110 methods in 120,916 s:
`nested-detached-regression-o2.log`, with CRUST_SANITIZE=undefined.
It covers borrowing descendants, detached factories, structures and
mixed, field returns, reference bridges, synchronous calls
The declines are due to the increase in the number of people employed in the labour force, and to the increase in the number of persons employed in the labour force.
The final extended passage of 110 methods is changed to 107,404 s
in `nested-detached-final-regression-o2.log`, with the same UBSan options.
The selection is made with the previous one; these accounts do not add up
not like unique tests. All the processes mentioned are completed.

<a id="limites-et-suites"></a>

## Limitations and consequences

The evidence relates to finished type graphs and &Int sheets.
They don't prove general safety, all types, all depths,
cyclic graphs are not generalized.
reset() remains removed from normal profile.

Synchronous relay receiving a task from an async body
(`open-async-task-relay-argument.crust`) and modifications of progeny fields
per auxiliary (`open-nested-field-replacement.crust`) restent ouverts.
Their refusal to both stages of the final code are retained in
`nested-detached-remaining-probes.log`.
The public API of the scheduler, general placement and arbitrations on the
The overall objective remains active.
