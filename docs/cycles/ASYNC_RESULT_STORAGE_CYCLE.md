[Français](ASYNC_RESULT_STORAGE_CYCLE-fr.md)

<a id="destination-des-résultats-locaux-neufs-des-tâches"></a>

# Destination of new local task results

<a id="règles-et-portée"></a>

## Rules and scope

This lot applies T1/T6, V5, L1/L2/L7, B1/B2 and AS2/AS8–AS14,
with drafts 03/04/05/07. It does not change any normative rules.
A new local structure returned by a task must be built in
a storage that survives this task, without further displacement.
The pool is a pool that keeps the pool. The original copied and the source
storage of the copy are not the same dependency.

The case `validation/open-async-fresh-local-result-destination.crust`, refused to
previous cycle, now runs and displays 7.
structures without proprietary fields or borrowed fields supported
by existing async signatures. Other graphs are not declared
Implemented by this result.

<a id="implémentation"></a>

## Implementation

`async_result_storage.py` deducted, since the contract for full profit or loss,
the need for an external destination and the parameters of which sources
This decision depends on the static instantization of the
local/pool; no displacement or choice of provenance to runtime is added.

The plants generated receive a hidden source of destination when the
routine can produce a new local structure. Pool variants
pass NULL when they do not need this destination.
synchronous and async retain the source until the instance is cleaned and,
after delivery, until the result is cleaned. Routine uses this source
But don't shut it down. The investment plan follows the producers of returns,
including calculated returns, branches and loops.
do not retain the original root as the source of their result; copies
pool keep its source.

The local storage of a source is now distinct from the generation of the
layout of a structure: creating a task does not emit an unused layout in
The dictionary of captured parameters is also distinct from the
targets of a reference table, which already used a similar name.

The diffs against `/tmp/crust-before-async-result-storage` are retained in
`validation/async-result-storage-*.py.patch`. The new module and the tests
are directly available in the project.

<a id="vérifications-exécutées"></a>

## Audits performed

- `validation/async-result-storage-suite-initial-o0.log` : ten methods,
  Two were C-refusals by `-Werror` (unused)
  The third test destroyed the original in a child's arm without transfer
  down; his scenario was corrected by receiving the result in the
  parent scope before destroying the original.
- `validation/async-result-storage-suite-corrected-o0.log` : 10 methods
  successful, 5,330 s.
- `validation/async-result-storage-expanded-o2.log` : 14 methods
  successful before adding the pool neighbour to the reference table test.
- `validation/async-result-storage-counted-final-o0.log` : 14 methods,
  **20 native executions**, **3 programmes invalides**, each verified in
  the two courses (**6 refusal checks**), 16,990 s. Aucun skip.
- `validation/async-result-storage-mutations-final-o2.log` : baseline finale
  of the 14 successful methods, 16.969 s, then five mutations detected.
- `validation/async-result-storage-runtime-mutation-o2.log` : sixth mutation
  detected by UBSan fatal to execution.
- `validation/async-result-storage-regression-o2.log` : initial selection of
  70 successful methods, 55,826 seconds, before final corrections.
- `validation/async-result-storage-regression-final-o2.log` : **116 methods**
  The only changes during the final compiler, 115,974 sec.
  This section concerns the targeted tests of this lot, which are not included in this selection.

All processes of these passages are completed with terminal status
observed. Failed initial campaigns are kept separately.

Native performances use Clang C11, pthread, `-Wall -Wextra -Werrar
-Wno-unused-function`, UBSan avec `-fno-sanitize-recover=all`, at levels
`-O0` and `-O2` no results found for ASan/Tsan new.

Scenarios cover: sync/async callers, local and pool copies,
conditional/calculated/interlocked returns, loop with continuous and break,
re-use, borrowing the result then drop allowed/refused, table capture of
references, two creations on native threads, injected failure of launch and
destruction of an inactive instance. Three invalid programs protect
The loan is captured, the result pool and a result loan respectively.

Two C probes observe storage independently of the investment calculation:
the cell remains at the same address, alive, after release of the slot of
the child; the source of the recipient only closes at the end of his own life.
The second probe destroys a tree not launched but suspended by poll,
and requires unique destruction and closure, with the two pools of states
This internal control does not create a public cancellation API.

<a id="mutations-et-contre-exemples"></a>

## Changes and counter-examples

The first campaign retained two detections, two inconclusive results
The two inconclusive results were refusals of the
compiler before probes: the harness did not rank them as failure
the local wrapper now reports these
refusal as explicit assertions, without changing the storage oracle.

The survivor erased the provenances captured before a table argument of
The initial test placed this table first and used only one
independent local copy of the original. The final test sets the parameter
structure before the table and exercises both local and pool sources.
The mutation is then detected. The initial logs are preserved.

The six faults target the destination flag, the follow-up of the producers
returned, source of a pool copy, undue closure of the source
external, the table of captured parameters and the destination pointer at
runtime. The first five are detected by unexpected refusal of programs
The sixth one causes a UBSan diagnosis of access to a NULL source.
This is not an overall rate of detection of memory errors.

`validation/async-result-storage-pool-before.log` Review of the
too short pool with the files from the previous snapshot: both stages
already refused, with a diagnosis of internal invariant without provenance.
This lot is therefore not presented as correcting a dangerous acceptance
The programme is based on the previous programme.

<a id="écarts-encore-ouverts"></a>

## Differences still open

Later update: the local result with proprietary fields and its graphs
finished are connected in [the cycle of local graphs](ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE.md).
The local field result is still open.

Update: the first two cases below are connected and exercised in
[the next cycle](ASYNC_RESULT_RELAYS_CYCLE.md). The list keeps the observation
at the end of this batch.

Minimum programs and diagnostics are retained in
`validation/async-result-storage-exploration.log` and
`validation/async-result-storage-aggregate-gaps.log` :

- `open-async-result-storage-child_parent.crust` expected in a
  then transferred to the parent; destination of the creator to be propagated.
- `open-async-result-storage-relay.crust` : new result relayed by a
  second task; destination contract to be spread between states.
- `open-async-result-storage-factory.crust` : fabrique synchrone retournant
  a task that will produce a new result; hidden storage to place at its
  receiver, not in the factory's scope.
- `open-async-result-storage-owned.crust` : new root with field
  owner; sources of descendants to be kept independently of the root.
- `open-async-result-storage-borrowed.crust` : new root with field
  borrowed; signature and result dependencies still not connected.

The refund after replacing a proprietary field is also retained
ouverte (`open-async-return-replaced-owned-field.crust`) These programmes do not
are not transformed into normative refusal tests: their current restrictions
are implementation deviations. Cases where a real target borrowed or
A pool disappears, but is not allowed, without any implicit promotion.

The probes and sequences are finished, without formal proof or validation of all
The full objective of the seven drafts remains open.
