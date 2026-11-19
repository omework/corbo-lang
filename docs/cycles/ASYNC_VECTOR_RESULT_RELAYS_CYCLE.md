[Français](ASYNC_VECTOR_RESULT_RELAYS_CYCLE-fr.md)

<a id="cycle--relais-des-result-contenant-un-vecteur-async"></a>

# Cycle — Relays of Results containing an async vector

<a id="règles-et-périmètre"></a>

## Rules and scope

ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md. AS8–AS12, H1–H3, VE1–VE4,
F2–F4, B1–B5/B4c and D1–D3 remain unchanged.
The rules governing the return and origin of goods have been adopted by the Council.
No further arbitration or normative change.

A Result received after waiting for a task can be explicitly transferred to
a function that restores it. Its envelope does not change the sources of the vector,
neither the borrowings carried by its elements nor the responsibility for cleaning.

<a id="défauts-et-corrections"></a>

## Deficiencies and corrections

The programme recorded in `validation/open-async-vector-result-relay.crust`
failed to meet the two entries on the invariant inventory of the pools of elements.
The Result parameter containing a vector now receives the same inventory
The verification paths by contract
and generation C re-establishing storage metadata and loans from
charges, including descendants possessed.

An additional relay revealed a reclassification of join_owned to
The declared mode is now retained.
The Result of stress analysis and source parameters retain
also the inventory of the elements. No internal invariant n

The arrowless argument diagnosis retains "anticipated mode" and specifies
now that an explicit -> transfer is required for proprietary modes.

<a id="scénarios-exécutés"></a>

## Scenarios implemented

Five new methods: **6 executions C**, one of which failed to submit
injected, and **7 programmes invalides** verified by verify_program and
compile_source, i.e. 14 refusal checks.

- Direct relay after wait, result named before consumption; destruction
  advance of the refused target, argument without -> refused.
- Two successive relays; the result keeps its charge and its loan.
- Field &mut Int: drop, read and write incompatible after relays refused.
- Item owning Inner borrowing n: value 7, an Inner destruction.
- Empty vector: zero length; failed launch: Err and destruction
  Item, without performing the task.

The fourteen methods of the two previous batches are replayed: **19 methods,
7,559 s, code 0**, O0/UBSan fatal. In total, this pass represents 19 executions
C and 22 invalids at both entrances. Invalids are not executed.
C11/pthread harness, Wall/Wextra/Werrar, UBSan non-recoverable.

Journaux `validation/async-vector-result-relays-targeted-*-o0.log` :

- First: 19 methods, 7.232 s, failure. Two controls correctly refused the
  program without arrow but diagnosis did not specify transfer;
  The succeeding relay lost the Result mode.
- second: 19 methods, 7,074 s, failure: symbolic inventory of elements
  absent in the analysis of the constraints of the successive relay.
- third: 19 methods, 7,559 s, success.

<a id="régression"></a>

## Regression

Completed: **289 methods, 240,778 s, code 0**, O2/UBSan fatal.
Journal : `validation/async-vector-result-relays-regression-o2.log`.
Selection in `validation/async-vector-result-relays-test-selection.txt`.
Manifest prints confirmed after the pass: compiler and tests
The same period of operation. Existing storage models, lifespan
and Select replayed, without new model independent of the result graphs.

<a id="artefacts-et-limites"></a>

## Artifacts and limits

Snapshot : `/tmp/crust-before-async-vector-result-relays`.
Tracks and fingerprints: `validation/async-vector-result-relays-changes.json`.
Test : `tests/test_async_vector_result_relays.py`.
C of the direct case: `validation/async-vector-result-relays.c`.

The three exploratory newspapers first/second/third keep the refusals before
successive corrections. The graphs remain conservative by path []
and provenance. No new independent model, no campaign of change,
ASan or TSan; existing models are included in the selected regression.
Reset remains removed. This lot is not a general proof of safety.

Prochain cas : `validation/open-async-vector-result-capture.crust/.log`.
Capture the Result in a new task that returns it still loses the results
vector elements at reception (remove thinks it empty), both inputs.
This is a gap in the implementation of a rule already retained.
open, with other checklist deviations.
