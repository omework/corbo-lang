[Français](ASYNC_HANDLE_VECTOR_POP_CYCLE-fr.md)

<a id="pop-de-handles-dans-les-états-async"></a>

# Pop of handle in async states

<a id="règles-et-implémentation"></a>

## Rules and implementation

Application of H1–H2, VE1–VE3, U1, B1–B5, AS8–AS12 and SL1–SL2, unchanged
normatif. `pop` remove the last handle and produce `Some` ou `None`. Un handle
présent conserve son adresse et son pool. La responsabilité de nettoyage passe
the result, then the recipient of the Some arm if the program consumes it.

Async Translation recognizes the direct match with `<-`, the named options,
the game consuming, the travel, the direct drop and the named drop.
VectorHandleResult, already used by the synchronous backend, contains the status
and the pointer of the element. The persistent temporary of the state keep
this envelope during a suspension. The runtime of vector_pop remains unchanged.

The paths of destruction of the proprietary results, previously reserved to the
Result of join, also take into account the Option envelope.
conditional and loop outputs use their actual C type, keep
the sources and consume the previous connection. The suspended cleaning of a
The loss of Select destroys some content only.
also keeps the sources in the new link.

<a id="cas-ciblés"></a>

## Targeted cases

Eight methods in tests/test_async_handle_vector_pop.py, seventeen executions
and six invalid programs controlled at both entries:

- Direct match Some and None, unique destruction and re-use of pool.
- Missing transfer and shared vector refused.
- Option named retained during yield, then moved or consumed.
- Annotation Option<A<Int>> allowed; Int annotation, no use and
  reuse after drop refused.
- Direct drop and named, on empty and non-empty vector.
- Borrow used before pop allowed; last use after pop refused.
- Receives a block, an if and a break: transfer and then a consuming match.
- Return of the extracted element from async, via synchronous factory; branch
  None creating an element in the injected pool.
- Select loser branch having extracted before yield: option cleaned a
  time, empty vector observed after waiting and re-use of pool.
- Two separate pools: last element 9 removed from pool, first
  element 7 retained, cleaning and re-use independent.

<a id="exécutions"></a>

## Implementation

Journaux sous validation/ :

| Journal | Result |
| --- | --- |
| open-async-handle-vector-pop.log | Initial case refused to both entries: array_handle_len not supported |
| async-handle-vector-pop-first-o0.log | Successful targeted execution; two failed diagnostic assertions for the missing arrow |
| async-handle-vector-pop-second-o0.log | Diagnostics specified, seven methods, 6,822 s, code 0 |
| async-handle-vector-pop-third-o0.log | Eight methods, 7,658 s, code 0 |
| async-handle-vector-pop-regression-o2.log | 91 methods, 153.696 s, code 0 |
| async-handle-vector-pop-sync-regression.log | Five methods, 6,473 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_pop -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_pop test_async_handle_vector_remove test_async_handle_vector_push test_async_vector_operations test_async_awaited_owned_results test_async_owned_struct_returns test_select_source test_factory_owned_effects -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_buffered_handle_pop_cleans_only_a_present_payload test_foundation_rules.FoundationTests.test_buffered_handle_pop_match_consumes_saved_result test_foundation_rules.FoundationTests.test_buffered_handle_pop_returns_through_block_receivers test_foundation_rules.FoundationTests.test_buffered_handle_pop_survives_break_and_cleans_continue test_foundation_rules.FoundationTests.test_handle_vector_pop_match_requires_transfer_and_exclusivity -v
```

C11/pthread, error warning, fatal UBSan. Foundation methods use
their historic harness O2/UBSan with legacy-reset. Reset remains excluded from the profile
The oracles control values, refusals, destruction and the
Reuse of slots. No new independent model or change campaign
or extended adversarial search. Regression replays the list model
(seeds 37/91, 28 operations) and the pollution/cleaning order model
Select (nine pairs of suspensions). These models do not specifically cover
The cross-audit remains a separate step.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The return of the element A<Int> is tested; this batch does not connect signatures
functions that receive or return the Option<A<Int>> itself since
async. The following case is reproduced at both entries in
validation/open-async-handle-option-call.crust and .log: a synchronous helper
Returns the option and the task consumes it. Signature still not supported.
The async returns/captures of the envelope also remain to be completed.

The results tested do not establish any general safety evidence or any evidence of
cover of all scheduling. Replace, try_push and constructions
local/retours of vectors remain open, as well as public arbitrations
previously recorded.

Snapshot : /tmp/crust-before-async-handle-vector-pop/.
Diff : validation/async-handle-vector-pop-async_lowering.py.patch.
