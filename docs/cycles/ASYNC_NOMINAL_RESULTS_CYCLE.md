[Français](ASYNC_NOMINAL_RESULTS_CYCLE-fr.md)

<a id="retours-async-directs-de-références-nominales"></a>

# Direct async returns of nominal references

<a id="règles-et-périmètre"></a>

## Rules and scope

Connection of AS8–AS12 and ST7–ST14: a task can return &T or &mut T
the result retains its provenances and capabilities;
target storage is not moved. A reference to a variable
Locally destroyed with state remains refused. No rule of law changed.

<a id="implémentation"></a>

## Implementation

- Async returns of nominal references use CrustStructureView,
  The copy of the result precedes the release of the fish.
  the state slot, via existing take/join_into operations.
- CrustJoinResult has shared and mutable descriptor fields.
  The type of descriptor belongs to the declarations common to the runtime
  and the full C programme; its pointers are declared forward.
- Task and handle wait results keep their nominal type
  in connections, branches and matches. Synchronous generator extracts
  either the internal descriptor or its root if all targets are complete.
- Inference of the results borrowed and their projection in the appellant
  cover nominal references, stored fields and substructures
  A previously projected capture does not apply twice its path.
- Public signatures `runtime::Handle<&T>` and `runtime::Handle<&mut T>`
  reconnaissent les structures nominales ; leurs contrats conservent le type
  the result and refuse an annotation of incompatible mutability.
- The nominal paths of the contained fields are transmitted to the backend async.
  A projection uses the offsets and sizes of the layout, and keeps the
  Subtree reservations. Layout metadata survives the task.

<a id="cas-ciblés"></a>

## Targeted cases

The 11 methods of `tests/test_async_nominal_results.py` couvrent douze
admitted programs implemented and eight invalid programs rejected by both
entries `verify_program` and `compile_source`.

- Join a shared reference: whole object and substructure.
- Joining a mutable reference: visible mutation in the caller and access
  competitor to the refused target before last use.
- Relay mutable by wait with suspension after receipt.
- Return of a reference stored from a transferred bearer; destruction
  the carrier does not destroy the target, whose reservation remains effective.
- Return of a mutable reference stored in a borrowed carrier.
- Waiting for a handle in a task, linking the result and his match Ok.
- Conditional return mixing whole target and inner: both
  branches executed, without changing the address of the storage by the operation.
- &mut p.b return from a &mut Pair parameter, with target protection.
- Two refusals to return reference to a local state structure,
  whole or inside.
- Synchronous task factory and Select whose result is a reference
  Nominal; explicit cleaning of Select after use.

- Public handle switched to synchronous function: nominal result consumed
  then reusable target; mutable annotation incompatible refused.

<a id="exécutions"></a>

## Implementation

Commandes : `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0|-O2 python3 -m unittest ... -v`.
Native C11/pthread compilation with error warning and fatal UBSan.
The expected outputs are written in the tests, regardless of the C generated.

| Journal in validation/ | Result |
| --- | --- |
| async-nominal-results-o0-first.log | 3 methods, 1,765 s, code 0 |
| async-nominal-results-o0-second.log | Re-executing the first 3 methods, code 0; the previous edition failed before any Python modification |
| async-nominal-results-o0-third.log | 7 methods, 4.259 s, code 0 |
| async-nominal-results-o0-fourth.log | 9 methods, 4,640 s, code 0 |
| async-nominal-results-o0-fifth.log | 10 methods, 4.843 seconds, code 0 |
| async-nominal-results-regression-o2.log | 116 methods, 96,074 s, code 0 |
| async-nominal-results-handles-o2.log | After connection of the public type: 42 methods, 48.479 s, code 0 |

The failure of the editing tool was a quote error in a Python script
The script did not apply any changes.
Then the new tests were applied separately, then the new tests actually performed.

The regression covers Int/u8 returns, existing tables and vectors,
stored typed references, direct views, synchronous carriers,
proprietary synchronous calls, Select and internal runtime views.
Five additional autonomous tests exercise the return of the result before
release, competing re-use of slots, multithread runner,
the border scheduler and the failure to create thread.

## Limites

These tests do not prove all combinations of graphs, nor all the
no new transfer campaign or adversarial audit.
Enum matches with nominal reference fields and recursive graphs
This lot does not modify or reset out of the list.
by default, nor the public arbitrations of the scheduler still open.
The overall objective remains ongoing.

Snapshot : `/tmp/crust-before-async-nominal-results/` ; patches archived in
validation/ at the end of the batch.
