[Français](ASYNC_HANDLE_EXCHANGE_RESULTS_CYCLE-fr.md)

<a id="captures-et-retours-async-des-résultats-de-replace-et-try_push"></a>

# Async returns and captures of the results of replace and try_push

<a id="règles-et-implémentation"></a>

## Rules and implementation

Application of H1–H2, VE3–VE4, U1, F4, B1–B5, AS2–AS5, AS8–AS14 and
SL1–SL2, without any change in the standard. An async instance may receive by
transfert `Result<A<Int>,A<Int>>` ou `Result<(),A<Int>>` and return this
envelope by await of an inactive instance. The displacement carries the
The target allocation is not moved.

The generator keeps the Int content type separately from the type of
the envelope, distinguishes the loads Ok/Err, and connects the catches, returns
direct or named, synchronous factories, async relays and synchronous helpers.
The termination summaries carry the provenances by arm.
projection in factory contracts and in task storage
Keep this information after dawn.

For replacement, both variants have an allowance. For try_push,
Ok(()) has nothing; Err owns the rejected entrant. Prepared catches
and inactive states respect this distinction.
successful try_push is normalized to NULL and its inactive cleaning also checks
The suspended paths use the corresponding obligations.

<a id="défauts-rencontrés"></a>

## Faults encountered

The first passage revealed the catches not connected by hand and the
loss of arms provenances in factories, their contracts and bridges
The data were collected by the capture team.
this modification interrupted the second passage before native execution;
it was corrected in the next passage.

The fifth passage detected double cleaning after capture of a
try_push succeeded, then destroy the inactive task. Synchronous C
kept a pointer in the Ok variant; inactive cleaning treated
This pointer as an allocation still possessed. The vector then cleaned
UBSan reported access via a zero pointer after the
double passage. The test and its oracle are kept; the cleaning was
corrected, without changing the semantics of try_push.

Reproduction : `validation/regression-async-try-push-inactive-capture.crust`.
The expected result is 8 then 9, with only one destruction of the entrant.
This case is executed in the targeted suite, with full capacity variants,
failure of launch and suspended preparation.

<a id="cas-ciblés"></a>

## Targeted cases

Ten methods in `tests/test_async_handle_exchange_results.py` : 28
native executions and seven invalid programs at both entries.

- Direct and named returns, success/replace error; no arrow refused.
- Synchronous manufacturing, async relays of capture and synchronous helper after await.
- Handheld capture, explicit transfer and reuse of the refused source.
- Inactive destruction and failure of submission, with unique cleaning and reuse.
- Former allocation from an outside pool, while the vector and
  the pool of the entrant disappears; source too short refused.
- Booking the vector until await and double consumption refused.
- Result try_push returned and captured, on success and ability achieved.
- Child suspended from a loser Select and cleaning his result.
- Capture prepared from a synchronous helper before the await of the argument
  next; continuation or destruction by Select, on success and error.

Full cases actually reach an area of 1 MiB. No limit of
runtime is not reduced in the generated C. Submission failures are injected
by the existing device, distinct from the oracles of values and destruction.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| open-async-handle-exchange-result.log | Initial refusal of the async signature at both entries |
| async-handle-exchange-results-first-o0.log | Four methods, 1.881 s, three failures |
| async-handle-exchange-results-second-o0.log | Four methods, 0.026 s, Python syntax error |
| async-handle-exchange-results-third-o0.log | Four methods, 5,418 s, code 0 |
| async-handle-exchange-results-fourth-o0.log | Eight methods, 8,607 s, code 0 |
| async-handle-exchange-results-fifth-o0.log | Nine methods, 9.296 s, one failure: double cleaning detected by UBSan |
| async-handle-exchange-results-sixth-o0.log | Nine methods, 11.589 s, code 0 |
| async-handle-exchange-results-seventh-o0.log | Ten methods, 13.515 s, code 0 |
| async-handle-exchange-results-regression-o2.log | 109 methods, 105,405 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_exchange_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_exchange_results test_async_handle_exchange_calls test_async_handle_vector_replace test_async_handle_vector_try_push test_async_handle_option_results test_async_handle_option_calls test_async_option_join test_async_structure_effects test_factory_owned_effects test_select_source -v
```

Native tests via harness C11/pthread, error warnings and UBSan
The regression is based on modified functions and contracts, the number of jobs and the number of jobs, the number of jobs and the number of jobs.
handle operations, options and Select. No new campaign
adversarial or mutations; the existing model of poll/cleaning of Select
This evidence relates to the paths executed;
they do not constitute general proof of safety.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The external result of spawn/join adds a separate Result level. It is
not yet connected for these two envelopes and remains explicitly refused,
Since then, as in the past, refusal is not a normative rule.
`validation/open-async-handle-exchange-join.crust` and its diary reproduce
the next work at both entrances.
the types of elements other than A<Int> are not closed here.

Snapshot : `/tmp/crust-before-async-handle-exchange-results/`.
The five diffs are archived under `validation/async-handle-exchange-results-`
for async_lowering.py, crust.py, async_structure_effects.py, results.py and
async_result_storage.py.
