[Français](ASYNC_HANDLE_VECTOR_PUSH_CYCLE-fr.md)

<a id="insertion-de-handles-dans-vectoraint-depuis-async"></a>

# Inserting handlers in Vector<A<Int>> since async

<a id="règles-et-implémentation"></a>

## Rules and implementation

Application of H1–H2, VE1–VE2, B1–B5, AS8–AS12 and SL1–SL2, unchanged
standard. push explicitly receives an A<Int>, keeps the address and pool
The target, and transmits the unique responsibility for cleaning to the box.
The source of each element must survive the recipient vector.

Lowering accepts transfers of variables and pool constructions.
It reserves the vector during the assessment of the argument, controls the type and
the life of the source, then write the handle and withdraw the responsibility
The temporary loan may be released before the new entry.
Vector cleaning uses the already existing handle destroyer.

The contracts publish the sources added to the termination and the points of
The manufacturers and relays retain these delayed effects in the
FunctionResult.task_vector_updates/task_suspension_vectors. Creating a
task does not perform integration. Join applies union of success states
and fail launch. Select also takes into account additions made by the
The short pools are statically refused.

Synchronous C bridges can receive a Vector<A<Int>> by borrowing: the
parameter remains a Cell* with the symbolic sources of its elements.
calls to the processing plants and synchronous mutation helpers use these bridges.
The calculation of synchronous vector effects was extracted in a method
reused for suspension snapshots, without change of intent.

<a id="cas-ciblés-et-défauts-rencontrés"></a>

## Targeted cases and defects encountered

Nine methods in tests/test_async_handle_vector_push.py: thirteen executions
and 12 programmes which are invalid at the national level
two entries verify_program/compile_source.

- Program recorded: allocation 7 in an injected pool, insertion, reading,
  unique destruction and re-use of the capacity pool one with 8.
- Absence arrow, Int inline, transferred Bool and shared vector refused.
- Transfer of a variable after last use of its loan; use after
  transfer, double transfer and borrowing still used refused.
- Synchronous factory and expected async relay; too short child pool refused
  in direct call as in the call via factory.
- Two elements transferred from two separate pools, directly or via
  production; result 30, single destruction of 10 and 20, re-use with 11 and 21.
- Inactive task destroyed without insertion; failure to launch without creation of
  No 7 destroyers in these paths without the execution of the body.
- Loaned a target then second push after last use; still alive ready refused.
- Synchronous helper performing insertion from async state.
- Vector himself transferred to the task: new element destroyed before join,
  Reuse vector and element pools.
- Select loser branch having inserted before yield, directly and via
  manufacture: the element remains present after destruction of Select. A pool plus
  The vector is refused in both cases.

During integration, the last direct case was wrongly accepted when the
pool expired before the vector. The writings made in the arguments
temporary symbolics were not carried over to their external aliases.
Correction propagates vector inventory to its aliases after application
of a contract of termination or suspension. Reproduction preserved in
validation/async-handle-vector-select-short-pool.crust, now refused to
This invalid program was not executed in C.

<a id="exécutions"></a>

## Implementation

Journals in validation/:

| Journal | Result |
| --- | --- |
| async-handle-vector-push-first-o0.log | Manufactured from async: unconnected collection signature |
| async-handle-vector-push-second-o0.log | Bridge C: vector parameter still treated as scalar reference |
| async-handle-vector-push-third-o0.log | Five methods, 3,487 s, code 0 |
| async-handle-vector-push-fourth-o0.log | Diagnosis of two invalid arguments masked by contract control; type checks and transfer placed before this check |
| async-handle-vector-push-fifth-o0.log | Eight methods, 4.042 s, code 0 |
| async-handle-vector-push-sixth-o0.log | Pool too short accepted on the path Select direct ; failure to publish fixed aliases |
| async-handle-vector-push-seventh-o0.log | Nine methods, 4,878 s, code 0 |
| async-handle-vector-push-regression-o2.log | 68 methods, 55,594 s, code 0 |
| async-handle-vector-push-sync-regression.log | Five methods, 5.353 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_push -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_push test_async_handle_vector_captures test_async_handle_vector_borrows test_async_handle_vector_borrow_returns test_factory_owned_effects test_factory_field_effects test_select_source -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_handle_vector_optional_push_through_borrow_keeps_possible_pool test_foundation_rules.FoundationTests.test_handle_vector_replacement_through_borrow_updates_caller test_foundation_rules.FoundationTests.test_handle_vector_extract_through_borrow_updates_caller test_foundation_rules.FoundationTests.test_owned_handle_vector_return_keeps_inserted_parameter_pool test_foundation_rules.FoundationTests.test_handle_vector_try_push_at_capacity_returns_injected_handle -v
```

C11/pthread, error warning, fatal UBSan. The five Foundation cases use
their O2/UBSan harness and legacy-reset profile of historical scenarios.
Oracles check values, refusal, destruction and reuse.
independent model or campaign of mutation or adversarial research
The independent audit remains separate, and these results do not prove
General safety or all combinations of the model.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Delayed manufacturing contracts retain all possible sources
additions; they do not promise an exact length or inventory per box.
Extraction and other proprietary operations are not implicitly
This lot is covered by this lot. Next refusal reproduced in both entries:
validation/open-async-handle-vector-remove.crust and .log, for reception
explicit values.remove(0), read and then destroy the extracted element.
Try_push, pop, replace, local constructions and vector returns
The arbitrations already open are not yet to be completed in the async states.
Not fenced.

Snapshot : /tmp/crust-before-async-handle-vector-push/.
Diffs : validation/async-handle-vector-push-{async_lowering.py,crust.py,results.py,async_structure_effects.py}.patch.
