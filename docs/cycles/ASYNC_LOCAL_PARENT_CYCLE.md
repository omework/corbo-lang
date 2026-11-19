[Français](ASYNC_LOCAL_PARENT_CYCLE-fr.md)

<a id="placement-des-structures-locales-dans-le-scope-parent-async"></a>

# Placement of local structures in the parent async scope

<a id="règles-et-périmètre"></a>

## Rules and scope

This lot applies drafts 03 and 05, explicit transfers T1/T3/T5/T6,
stability V5, cleaning L1/L2/L6/L7, copying rules ST17/ST18 and
AS8/AS9/AS12. It does not change any normative rules.

The programme `validation/open-async-local-helper-parent-transfer.crust`,
refused the previous cycle, is now executable. A local structure
produced by a synchronous helper can get out of an async block and stay alive
The interlocked blocks, if, match buildin, loops to the result,
The copies and relays of the
parameters are followed, including the copy given by a method.

Replacement of a parent receiver is also connected: call result
direct or block construction, named in the child then `r = <-q`, branche
condition, and updates from iterations. If a construction can
reach two receivers of different depths, the destination that includes
The borrowing and explicit transfer obligations are retained.
remain separately verified from the placement.

<a id="implémentation-et-invariants"></a>

## Implementation and invariants

`async_local_placement.py` monitoring the producers of local results in the
The appeals are described in their contracts, without re-routing
a copy of a result copied has a new construction; a relay
The writings in the arguments
recipients already present are also linked to their producers.

The generator opens the data stack range of the parent before the evaluation of the
The block concerned and transmits this destination to the producer call.
reserves its cell at the entrance of the helper and the helper built directly in
No living allowance is moved after construction.
Temporary children who are not transferred from the child use their own beach.
branch that returns without building the result leaves an empty parent range,
which is closed by its normal cleaning; it does not create a fictitious object.

An interior plan does not replace an existing external destination.
For several recipients, the depth comparison avoids choosing a
The plan does not promote the allowances owned in the
fields: their pools must always survive the result.
unknown to the plan will remain subject to the regular auditor.

Two additional corrections were required:

- A local copy from an argument possessed wrongly retained the stack of
  the original in the sources of the result. The new root now retains
  its destination; the fields are covered separately and keep their pools.
- The `<-` The final block had been removed too early from the analysed instructions.
  A conditional reassignment was then refused for lack of use,
  despite this final transfer. The marker remains visible to the duration analysis
  use, without being executed twice by the backend.

The shape `r = <-{ ... <-p };` is also standardized to the transfer path
the new value before the
destruction of the old.

<a id="preuves-exécutées"></a>

## Evidence

The tests are in `tests/test_async_local_parent.py`. Executions C
use Clang C11, pthread, Wall/Wextra/Werrar, Wno-unused-function and UBSan
Blocking. O0/O2 levels are explicitly selected.

- **14 targeted methods** go to O0 in 17.182 s: **29 native executions**,
  **cinq programmes invalides** refused both courses (**10 checks**).
  Journal : `validation/async-local-parent-complete-counted-o0.log`.
- The final baseline O2 of the same fourteen methods goes in 17.445 s in
  `validation/async-local-parent-mutations-complete-o2.log`.
- A larger regression of **148 methods** passed in 172,746 s before the
  latest additions to methods and recipients named:
  `validation/async-local-parent-regression-o2.log`. It covers the results
  premises/owners, catches, sync calls, loop outputs,
  divergent expressions, Select and source constraints.
- The final selection of **51 methods** go to O2 in 49,433 seconds on the code
  final: local results, parent placement, structural bridges and calls
  Journal: `validation/async-local-parent-regression-named-o2.log`.
  The last two-receiver test is added after loading this
  selection; it passes separately to O0 and in the final baseline O2.
- `py_compile` succeeds in the relevant modules and tests. The diffs are
  archived in `validation/async-local-parent-*.py.patch`, relative to
  `/tmp/crust-before-async-local-parent/`. The new module is archived as
  addition, without prior fictitious state.

The C probes do not follow only the values displayed.
created cells and closed sources in the generated C:

1. Before the transfer, temporary and result occupy separate stacks.
   After the child exit, its source has zero living cells and a cursor to
   the parent result retains its address and value.
   and suspended cleaning destroy each of the two values exactly once.
2. The model of a loop of three iterations awaits a child closure by
   Iteration and a final parent closure. They continue to destroy the value
   not returned; the following iteration reuses exactly the same cell
   parent, with a constant cursor and number of living cells.
   Break, this cell stays alive until it is destroyed in the receiver.

These probes have only an unlaunched task.
The source tests also go through the scheduler.
The Err Road of a match is exercised by injecting a refusal to launch the
child task; its alternative construction produces good value and cleans up.

Invalid neighbors cover a pool of too short fields, a drop for a
ready still used, a transfer absent, a read after move and an argument
The placement does not make any of these programs valid.

<a id="mutations-et-chronologie-conservée"></a>

## Changes and chronology retained

`tests/run_async_local_parent_mutations.py` changes temporary copies to
keeping the source oracles and C unchanged. The final campaign detects **huit
fautes** : choice of a destination too short, forget the destination of a
named receiver, no parent placement, external plan crash,
loss of field pools, omission of stack closure, retention of the
stack of the original copied and disappearing of the use represented by the `<-` final.
Journal : `validation/async-local-parent-mutations-complete-o2.log`.

Several mutations are detected by refusing a valid program; the
fields have an invalid program accepted, without running this program.
Failure to close fails on observations C. These forms of detection
are not presented as equivalent or extrapolated to all defects.

The first six mutations campaign and the five mutations from the previous batch
were also successfully executed before the last additions:
`validation/async-local-parent-mutations-o2.log` and
`validation/async-local-parent-previous-mutations-o2.log`. Campaigns
Intermediate `mutations-final-o2` and `mutations-named-o2` are preserved.
After adding the tracking of the assignments named, the corresponding error target
This plan is a prerequisite, rather than the only direct treatment of a reallocation.

Initial failures remain available:

- `suite-initial-o0` : copy holding the source of the original and envelope
  explicit block transfer unconnected.
- `probes-o0` : collision of C names in the probe (`Cell *result` and `int result`),
  corrected in the harness without changing the oracle of identity.
- `expanded-o0` : same harness defect and end use lost in a branch.
- `named-o0` : a conditional fixture omited `q ->;` at the entrance of its
  arms; markers were added in accordance with existing rules.

Corrective logs and intermediate selections of 50 methods
remain with the prefix `validation/async-local-parent-`.

<a id="écarts-encore-ouverts"></a>

## Differences still open

Current diagnoses are included in the
`validation/async-local-parent-remaining-final.log` :

- `open-async-local-named-parent-replacement.crust` is now accepted by
  the two courses and executed in the suite, while the intermediate newspaper
  `remaining.log` retained its refusal before the additional assignments.
- `open-async-local-loop-updated-parent-result.crust` remains refused: a variable
  local is reassigned by a loop statement, then transferred out of the block
  The results obtained from the analysis should be calculated until the stabilization is achieved.
  through this loop. The current refusal is not a rule of language.
- `open-async-local-helper-child-capture.crust` remains refused: the provenance
  local/pool does not yet cross the signatures of children states.
  a local value outside the task also requires destination storage
  outside his condition.

General graphs with borrowings, direct construction in the states and
the refund after replacement of a proprietary field remain the deviations
The models of this lot are finished; they do not constitute a single
no general evidence of safety. No new results found for ASan/TSan is
All the processes mentioned are completed; the overall objective remains
ouvert.
