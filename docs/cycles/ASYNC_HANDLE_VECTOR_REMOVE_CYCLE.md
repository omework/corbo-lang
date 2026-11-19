[Français](ASYNC_HANDLE_VECTOR_REMOVE_CYCLE-fr.md)

<a id="extraction-de-handles-de-vecteurs-dans-les-états-async"></a>

# Extraction of vector handles in async states

<a id="périmètre"></a>

## Perimeter

Application of rules H1–H2, VE1–VE3, B1–B5, AS8–AS12 and U1, unchanged
normatif. `remove` transfers an A<Int>, keeps the address and source of its
target, shift remaining boxes and transmit the cleaning to the recipient.
L'extraction exige `<-`, or the already explicit transfer of `drop(-> ...)`.

Lowering materializes the result in Cell*, reserves the vector for
the evaluation of the index, and then the result is linked to the sources retained.
The returns and contracts of factories distinguish the sources from the components of the
The async relays reconstruct an element candidate from
The result can survive the vector pool, never to
The runtime of the removal remains unchanged.

The synchronous bridge retains the symbolic sources of the elements instead of the
replace with the field graph, empty for this type.
also retains the explicit extract marker.
consumed by drop now recognizes remove, without adding any transfer to the
appels ordinaires.

<a id="cas-exécutés"></a>

## Cases implemented

Eight methods in tests/test_async_handle_vector_remove.py: thirteen executions
natives, including one out-of-bound controlled stop, and seven invalid programs
verified with verify_program and compile_source.

- Local extraction recorded, single destruction of 7 and re-use of slot with 8.
- Absence arrow, shared vector and use after drop refused.
- Direct return, synchronous manufacturing and async relays expected.
- Three elements from two pools: extraction from the middle, order 10/30
  retained, result 20 still usable after destruction of the vector,
  unique cleaning and re-use of the three slots.
- Borrowing completed before extraction allowed; last use after extraction refused.
- Index calculated per task with suspension; index off-bound.
- Synchronous helper and direct consumption by drop.
- Transferred vector to task: result coming out of the block of its admitted pool,
  directly and via manufacture; pool of the item too short refused.
- Replacement of a recipient: old allowance destroyed once, new
  allowance cleaned at the end of the task; old content still borrowed refused.

<a id="journaux-et-corrections"></a>

## Newspapers and corrections

All logs are in validation/.

| Journal | Result |
| --- | --- |
| async-handle-vector-remove-first-o0.log | Incomplete harness and block transfer missing in the corrected test; factory connections and back sync missing |
| async-handle-vector-remove-second-o0.log | Relay losing provenance; bridge sync erasing the sources of the elements |
| async-handle-vector-remove-third-o0.log | Previous paths pass; drop direct does not recognize its transfer |
| async-handle-vector-remove-fourth-o0.log | Six methods, code 0 |
| async-handle-vector-remove-fifth-o0.log | Eight methods, 5,864 s, code 0 |
| async-handle-vector-remove-sync-regression.log | Five methods, 6.278 s, code 0 |
| async-handle-vector-remove-regression-o2.log | 77 methods, 60.691 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_remove -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_remove test_async_handle_vector_push test_async_handle_vector_captures test_async_handle_vector_borrows test_async_handle_vector_borrow_returns test_async_vector_remove test_async_result_storage test_async_owned_struct_returns test_factory_owned_effects -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_handle_vector_remove_preserves_identity_and_frees_origin_after_drop test_foundation_rules.FoundationTests.test_handle_vector_remove_dynamic_index_inside_function test_foundation_rules.FoundationTests.test_handle_vector_extraction_returns_injected_handle test_foundation_rules.FoundationTests.test_handle_vector_extract_through_borrow_updates_caller test_foundation_rules.FoundationTests.test_handle_vector_extraction_infers_drop_pool_through_a_call -v
```

C11/pthread, error warnings, fatal UBSan. The five Foundation methods
use the historical harness O2/UBSan with legacy-reset; reset remains excluded
The oracles are about values, refusal, destruction
No new independent model or campaign of
The detailed cross-audit remains planned separately.
re-executes the existing list template for remove Int/u8 (seeds 81
and 183, 32 operations each), without extending it to the handle.

## Limites

The async contract retains the union of possible pools of elements; it does not
This is not a promise of precise origin by index in all relays.
approximation may refuse valid programs. The above scenarios do not
prove neither the general security nor all combinations of rules.
Pop, replace, try_push and local/retour vector constructions in the
The arbitrations of public scheduler,
construction of mutex and inactive handlet catches remain open.

Snapshot : /tmp/crust-before-async-handle-vector-remove/.
Diffs : validation/async-handle-vector-remove-{async_lowering.py,async_result_storage.py,crust.py,results.py,array_syntax.py}.patch.
