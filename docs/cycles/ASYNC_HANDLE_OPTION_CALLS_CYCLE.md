[Français](ASYNC_HANDLE_OPTION_CALLS_CYCLE-fr.md)

<a id="options-propriétaires-dans-les-appels-synchrones-depuis-async"></a>

# Own options in synchronous calls from async

<a id="règles-et-implémentation"></a>

## Rules and implementation

Application of H1–H2, VE3, U1, B1–B5, AS8–AS12 and SL1–SL2, unchanged
A transfer option<A<Int>> can pass through a synchronous helper
The result keeps the element pool and its
No one has no allowance.

The signature is connected to VectorHandleResult in calls and bridges C.
The result is declared owner and requires a recipient used or a drop.
The argument requires -> and retains the status and pointer.
prepared from left to right; content already transferred is recorded for
cleaning a suspension before the call is completed.
Fields of the missing result are not read in the contract calculation.
The drop of a statically empty option materializes its use in C with (void),
without inventing any allowance or destruction.

<a id="cas-ciblés-et-défauts-rencontrés"></a>

## Targeted cases and defects encountered

Seven methods in tests/test_async_handle_option_calls.py: fifteen executions
The first is the first time that the programme has been completed.

- Back Some/None by helper, consumption and reuse of the pool.
- The result was ignored owner and the match was not explicitly rejected.
- Named option, nested call, explicitly transferred direct pop and block
  retournant l'option ; argument suivant contenant un await, ordre 4/7/8.
- No arrow, second consumption and A<Int> instead of Option refused.
- Consumer Void and direct drop of the result, on Some and None.
- Option still usable after destruction of the vector transferred to the task.
- Losing Select suspended during the following argument: the helper is not
  Called, the prepared item is destroyed once, the slot is reusable.
- Async return of the element after extraction by helper; exit of the block of the
  allowed vector, pool of the element too short refused on both branches.
- Synchronous relay of a statically empty option, followed by a drop.

Two synchronous regressions encountered a pre-existing crash: the contract
The first part of the study was the following:
snapshot prior to the batch (baseline-empty journal). The minimum case retained
is valid/empty-handle-option-forward.crust: before correction,
verify_program accepted and compiled_source raised AttributeError.
native compilation revealed a missing C use for drop
empty; it is also corrected. The tests concerned pass without weakening
leurs oracles.

<a id="exécutions"></a>

## Implementation

Journals in validation/:

| Journal | Result |
| --- | --- |
| open-async-handle-option-call.log | Initial refusal to both entries: signature not supported |
| async-handle-option-calls-first-o0.log | Five methods, successful executions; diagnosis of a incompatible type too vague |
| async-handle-option-calls-second-o0.log | Six methods, 6,401 s, code 0 |
| async-handle-option-calls-regression-o2.log | 61 methods, 99,319 s, code 0, before the static empty case and match diagnosis corrections |
| async-handle-option-calls-sync-regression.log | Four methods, two errors on the None relay |
| async-handle-option-calls-baseline-empty.log | Same two errors on the previous snapshot, 0.118 s |
| empty-handle-option-forward-before.log | Minimum case: check accepts, compilation raises AttributeError |
| async-handle-option-calls-third-o0.log | Seven methods, C warnings-as-errors failure for the drop of the empty result |
| async-handle-option-calls-final-o2.log | Seven targeted methods + four synchronous: eleven methods, 10,245 s, code 0 after all corrections |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_option_calls -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_option_calls test_async_handle_vector_pop test_async_handle_vector_remove test_sync_owned_calls test_async_awaited_owned_results.AsyncAwaitedOwnedResultsTests.test_argument_expression_families_and_forms test_async_awaited_owned_results.AsyncAwaitedOwnedResultsTests.test_suspended_prepared_result_cleanup test_select_source -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_option_calls test_foundation_rules.FoundationTests.test_buffered_handle_pop_return_contract_across_calls test_foundation_rules.FoundationTests.test_buffered_handle_pop_passes_statically_empty_option_from_function test_foundation_rules.FoundationTests.test_buffered_handle_pop_transfers_as_argument test_foundation_rules.FoundationTests.test_buffered_handle_pop_cleans_only_a_present_payload -v
```

C11/pthread, error warnings, fatal UBSan. Foundation retains its
historical profile legacy-reset; reset remains excluded from the normal prototype.
The 61 method pass includes the existing model of pollution/cleaning order
Select; no new independent model or change campaign.
evidence relates to the routes carried out and does not constitute evidence
The continuation of 61 methods was not replayed after the two
Final corrections: their targeted cases and the four synchronous regressions
were replayed in O2, successfully.

<a id="suite-et-limites"></a>

## Continuation and limitations

The result of an async task option<A<Int>>, its capture and envelope after
Spawn/join still to be connected. Next case reproduced at both inputs:
validation/open-async-handle-option-result.crust and .log, where extract becomes
Async and its option is received by await. Async signature is still refused.
Other delivery transactions and public arbitrations already open do not
The game consuming an option tested passes through a
liaison explicite.

Snapshot : /tmp/crust-before-async-handle-option-calls/.
Diffs : validation/async-handle-option-calls-{async_lowering.py,crust.py}.patch.
