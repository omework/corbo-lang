[Français](ASYNC_HANDLE_EXCHANGE_CALLS_CYCLE-fr.md)

<a id="résultats-de-replace-et-try_push-dans-les-appels-depuis-async"></a>

# Results of repositioning and try_push in calls from async

<a id="règles-et-réalisation"></a>

## Rules and implementation

Application of H1–H2, VE3–VE4, U1, F4, B1–B5, AS8–AS13 and SL1–SL2.
No normative changes.
now transmit `Result<A<Int>,A<Int>>` and `Result<(),A<Int>>` one
Calling async, receive these envelopes by transfer and return them.

Bridge C uses `VectorHandleResult`. To replace, each variant has
a handle; for try_push, only Err has one. Transferring an argument
prepared before a suspension keeps this conditional cleaning until the call.
If Select destroys this suspended branch, it cleans the prepared argument a
Only once. On success of try_push, the vector retains the input alone.

The origin of each arm is kept separately through the contracts,
The old allowance can thus survive the pool of
the entry if its own pool remains valid.
transferred `helper(->v.replace(...), ...)` and `helper(->v.try_push(...), ...)`
are recognized by the parser, as named results and blocks.

<a id="cas-exécutés"></a>

## Cases implemented

Eight methods in `tests/test_async_handle_exchange_calls.py` : dix-neuf
native executions and five invalid programs verified by both entries.

- Direct return, relays and variants replace/error and try_push.
- Named arguments, interlocking calls, direct operations and blocks; a wait
  in the following argument checks the order of assessment.
- Consumer Void and drop of a helper's return; single destruction and
  Reuse of slots.
- Select losing during the preparation of a call: replace and try_push,
  non-full vector or limit of region actually reached.
- Separate pools by arm, old allowance returned after disappearance
  the vector and pool of the entrant; source too short refused.
- No arrow, wrong type of envelope, result without use and double
  consumption refused.

Capacity cases re-use actual filling of 1 MiB region,
without changing the limits of runtime C. Cleanup claims check
the unique destruction of the values concerned and the reuse of pools.

<a id="exécutions-et-corrections"></a>

## Implementation and corrections

| Journal in validation/ | Result |
| --- | --- |
| open-async-handle-exchange-call.log | Initial refusal to both entries: synchronous signature not connected |
| async-handle-exchange-calls-first-o0.log | Six methods, 5.298 s, failure on direct argument replaced |
| async-handle-exchange-calls-second-o0.log | Six methods, 6.141 s, code 0 after the parser connection |
| async-handle-exchange-calls-third-o0.log | Eight methods, 7,466 s, code 0 |
| async-handle-exchange-calls-regression-o2.log | 131 methods, 87,844 s, code 0 |

The initial fixture has been corrected to declare the synchronous helper input
`->A<Int>` The initial refusal was
reproduced on this valid version with the snapshot prior to the batch.
oracle or type requirement has not been relaxed.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_exchange_calls -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_exchange_calls test_async_handle_vector_replace test_async_handle_vector_try_push test_async_handle_option_calls test_async_option_join test_select_source test_fixed_arrays test_foundation_rules.FoundationTests.test_handle_vector_replace_error_return_preserves_parameter_identity test_foundation_rules.FoundationTests.test_buffered_handle_replace_preserves_result_after_vector_changes test_foundation_rules.FoundationTests.test_buffered_handle_try_push_cleans_only_rejected_handle -v
```

C11/pthread, warnings processed in error, O2 and fatal UBSan for testing
async. The FixedArray suite uses its default settings (without optimization)
nor explicitly sanitizer activated in this command); it does not read
CRUST_TEST_OPT. The three Foundation tests use O2 and fatal UBSan.
The regression includes the existing sequence of fixed tables, directly
covered by the common replacement syntax, as well as synchronous contracts
and the cleanup of Select. The historic suites FixedArray and Foundation
keep their legacy-reset profile; this does not reintroduce into the
prototype. Existing models of tables and Select are replayed.
No new model, no change campaign or in-depth adversarial audit.
Successful testing is not a general proof of safety.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Perimeter: Synchronous helpers from async, envelopes bearing A<Int>.
The catches and returns of tasks of these envelopes remain to be connected,
and their external envelope of spawn/join.
`validation/open-async-handle-exchange-result.crust` reproduces the refusal of a
return async via await to both entries; his diary is kept.
The types of additional elements and the total constructions of the
The public arbitrations open are not closed by this lot.
remain unchanged.

Snapshot : `/tmp/crust-before-async-handle-exchange-calls/`.
Diffs : `validation/async-handle-exchange-calls-async_lowering.py.patch` and
`validation/async-handle-exchange-calls-crust.py.patch`.
