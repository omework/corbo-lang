[Français](ASYNC_HANDLE_VECTOR_ACCESS_CYCLE-fr.md)

<a id="accès-au-contenu-des-handles-dun-vecteur-depuis-async"></a>

# Access to the contents of the handle of a vector from async

<a id="règles-et-changements"></a>

## Rules and changes

Application of H1, VE1/VE4, B1–B5 and assessment and evaluation rules
suspension. `*values[i]` reads the Int targeted by the handle; it is not a copy
A handle A, Int. `*values[i] = valeur` edits this content with mutable access,
without replacing the allowance or changing its pool.

Lowering charges a Cell* from the vector check box, then reads or
writes its content. For writing, the target is selected and the boundaries are
Checked prior to the Incoming Value Assessment. A Shared Reservation
temporary vector allows a reading in the HHR but prevents its mutation
destruction during such assessment, including suspension.

Synchronous Play `*values[i]` met during the result check
after join was not connected: she used the path of the paintings of
It now uses the existing box borrowing control of
Vector<A<Int>>, then copy only the target Int. No rule changed.

<a id="cas-ciblés"></a>

## Targeted cases

Four methods in tests/test_async_handle_vector_access.py: four
native executions, including a controlled termination out of bounds, and three
programs that are invalid at both entries.

- Play after yield, result 7 then re-use pool with 8. Play
  implied handle as Int is refused.
- Writing `*values[0] = *values[0] + 2`, suspension and then reading 9 ; the code
  Synchronous also sees 9 after join. Unique destruction of target worth 9.
  Writing via shared capture and read the rejected caller before join.
- Index provided by one expected child, then RHS provided by another child
  expected: result 12, cleaning and reuse.
- Index 1 in a vector of length 1: diagnosis « Vector index outside
  limits", no impression of marker 123 in the HHR.

The validation/open-async-owned-vector-read.crust fixture is now executed
The first method. His old newspaper of refusal remains historical.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| async-handle-vector-access-first-o0.log | Missing sync reading; oracle of outbound diagnosis in corrected English |
| async-handle-vector-access-second-o0.log | Four methods, 1,708 s, code 0 |

Regressions completed with code 0: 50 methods in 48,365 s in
validation/async-handle-vector-access-regression-o2.log; three methods
synchronous in 2.469 s in validation/async-handle-vector-access-sync-regression.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_access -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_access test_async_handle_vector_captures test_async_collection_new test_async_vector_remove test_async_vector_operations -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_shared_handle_vector_signature_relays_a_case_borrow test_foundation_rules.FoundationTests.test_handle_vector_result_tracks_replacement_through_a_slot_loan test_foundation_rules.FoundationTests.test_vector_rejects_type_mismatch_and_effectful_alias -v
```

Targeted harness and async: C11/pthread, error warning, fatal UBSan.
The Foundation cases use their O2/UBSan harness and legacy-rest for the
No new adversary campaign or mutations.
Expectations are about values, diagnostics, order of effects
and destruction; they are not general evidence.

## Limites

Borrowings named as elements, insertions/extractions, local construction
Async and Vector's return<A<Int>> remain to be connected.
Int does not imply that the entire vector API is available.
Open features and arbitrations are not closed.

Snapshot : /tmp/crust-before-async-handle-vector-access/.
Diffs : validation/async-handle-vector-access-{crust.py,async_lowering.py}.patch.

Next case reproduced: validation/open-async-owned-vector-borrow.crust and .log.
The &*values[0] retained during yield is still refused both entries.
