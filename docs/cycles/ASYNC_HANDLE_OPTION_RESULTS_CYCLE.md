[Français](ASYNC_HANDLE_OPTION_RESULTS_CYCLE-fr.md)

<a id="captures-et-retours-async-doptions-propriétaires"></a>

# Captures and returns async of proprietary options

<a id="règles-appliquées"></a>

## Rules applied

Application of H1–H2, VE3, U1, B1–B5, AS2–AS5, AS8–AS15 and SL1–SL2,
An option<A<Int>> has its own content.
Its capture requires an explicit transfer; its return transmits the content and
None of the companies are carrying any allowances.
the element must survive the task and then the result that keeps it.

<a id="implémentation"></a>

## Implementation

VectorHandleResult representation is connected to captures and results
Async statements. Results and field contracts retain sources
The synchronous and async relays are propagating these contracts.
The waiting for an inactive instance receives the option before destroying its state.
Existing cleaning paths only treat the content if it is present.
Statically empty capture does not create a fictitious allocation dependency.

The direct result of the task and the flawless envelope of his handle are
This lot connects the first. A join or a handle wait whose
result is Option<A<Int>> still produces an explicit functional diagnosis
not connected, instead of using the representation of an Int result.

<a id="cas-exécutés"></a>

## Cases implemented

Eight methods in tests/test_async_handle_option_results.py: thirteen executions
and seven invalid programs controlled by verify_program and compile_source.

- Returns Some/None by await; return without an arrow refused.
- Option named before yield, synchronous manufacturing and async relays.
- Some/None captures; no transfer and reuse after transfer refused.
- Destruction of an inactive task and failure of the first injection:
  clean up transferred content, single destruction and re-use of slot.
- Capture returned by a child task, then transmitted to a synchronous helper.
- Child suspended after extraction, in a loser of Select: unique cleaning.
- Reading the vector after await allowed; reading during the mutable capture
  and received option without explicitly refused use.
- Return of the allocation out of the block of the allowed vector if its pool survives;
  local pool too short refused. The case of too short capture is refused as soon as
  insertion into the outer vector: it does not constitute isolated evidence
  control at the exit border.

The initial case retained is validation/open-async-handle-option-result.crust.
His .log journal documents the previous refusal; the same program is now
performed by the targeted test and produces 7 then 8.

<a id="preuves-dexécution"></a>

## Evidence of enforcement

| Journal in validation/ | Result |
| --- | --- |
| async-handle-option-results-first-o0.log | Six methods, 4,437 s, code 0 |
| async-handle-option-results-second-o0.log | Eight methods, 4.734 s, code 0 |
| async-handle-option-results-regression-o2.log | 74 methods, 113,097 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_option_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_option_results test_async_handle_option_calls test_async_handle_vector_pop test_async_awaited_owned_results test_async_owned_struct_returns test_select_source test_factory_owned_effects -v
```

C11/pthread, warnings processed in error, fatal UBSan. Results
The number of people who have been killed and the re-use of the pools is monitored.
The regression includes the existing model of the order of pollution/cleaning
de Select. Aucun nouveau modèle indépendant, aucune campagne de mutations ni
The second phase of the programme is still separate, in accordance with the
The execution of the execution does not prove the security of the user
General language.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The perimeter is about Option<A<Int>>, not all generic forms
The Result<Option<A<Int>> envelope,runtime::Error> of spawn/join and the
The other public handling operations are still to be connected.
Open public arbitrations and delivery systems are not closed by this lot.
reset remains removed from the prototype; no new validation reintroduces it.

Snapshot : /tmp/crust-before-async-handle-option-results/.
Diffs : validation/async-handle-option-results-{async_lowering.py,async_result_storage.py,async_structure_effects.py,results.py,crust.py}.patch.
