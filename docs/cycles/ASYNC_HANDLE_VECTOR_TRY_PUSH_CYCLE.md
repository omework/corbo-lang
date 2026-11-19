[Français](ASYNC_HANDLE_VECTOR_TRY_PUSH_CYCLE-fr.md)

<a id="insertion-faillible-de-handles-dans-async"></a>

# Failed insertion of handle into async

<a id="règles-et-implémentation"></a>

## Rules and implementation

Application of H1–H2, VE3–VE4, U1, B1–B5, AS8–AS12 and SL1–SL2, without
normative change. try_push transfers the input to the vector after success.
If the limit is reached, the vector remains unchanged and Err has the input.
Ok(()) does not have any allocation, but the result must be explicitly used.

The async generator shares the preparation of the receiver and input with
replace. It retains a distinct variant of result, of which only the arm
Err requires cleaning. After successful insertion, the result pointer is
placed at NULL; the vector box keeps the handle and its cleaning.
Failure, extraction transfers this pointer to the recipient of the arm. A drop destroyed
Only rejected content. Select's suspended paths apply the
Same rule.

Direct match also consumes the result on his arm Ok() to allow
the continuation after both arms without residual obligation.
Named, annotated Result<(),A<Int>>, moved and preserved through yield are
The sources published by the insertion remain followed in the vector.

<a id="cas-ciblés"></a>

## Targeted cases

Seven methods in tests/test_async_handle_vector_try_push.py: fourteen
native executions and nine invalid programs at both entrances.

- Achievements and actual ability: rendered value, vector content
  and the unique destruction of the ingress.
- Missing arrow, pattern Ok incompatible and reuse of the refused input.
- Result named and annotated, yield, moving and then consuming match.
- Direct and named drop, success and error; result unused and double
  consumption refused.
- Continuation after a direct match or named with Ok(()).
- Borrowing of finished item before insertion allowed; use still to come,
  shared receiver and local source too short refused.
- Inward allocation produced by a task expected.
- Losing Select suspended after try_push: value stored in vector
  over-success, rejected value destroyed by error; re-use of slots.

Full cases use an explicit region of 1 MiB and fill it with
1 MiB / size of a native pointer. On the tested platform, it makes
131072 boxes. These are Crust programs run, without artificial reduction
limit in the generated C.

The first passage had a snippet defect: a n link added by the
The snippet was replaced by a snippet.
an effective element loan, with pre-/post-insertion use.
The report has not been made more flexible.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| open-async-handle-vector-try-push.log | Initial refusal to both inputs: array_handle_try_push not connected |
| async-handle-vector-try-push-first-o0.log | Six methods, 5.846 s; failure due to collision of names of the snippet |
| async-handle-vector-try-push-second-o0.log | Seven methods, 6,981 s, code 0 |
| async-handle-vector-try-push-regression-o2.log | 72 methods, 75,217 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_try_push -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_try_push test_async_handle_vector_replace test_async_handle_vector_push test_async_handle_vector_pop test_async_handle_option_results test_factory_owned_effects test_select_source test_foundation_rules.FoundationTests.test_handle_vector_try_push_requires_transfer_and_unit_success test_foundation_rules.FoundationTests.test_buffered_handle_try_push_cleans_only_rejected_handle test_foundation_rules.FoundationTests.test_handle_vector_try_push_returns_incoming_at_capacity -v
```

C11/pthread, warnings processed in error and fatal UBSan. Tests check
the exits, the unique cleaning and the reuse of the pools. Foundation keeps
its historical legacy-reset profile, without reintroducing reset into the prototype.
The existing Select poll/cleaning model is included in the regression.
No new independent model or adversary campaign or mutations.
These results are not a general proof of safety.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Perimeter: insertion of A<Int> and local envelopes into async states.
Signatures carrying Result<A<Int>,A<Int>> and Result<(),A<Int>> remain
connecting calls from async, then to captures and task results.
Constructions and other vector returns are not closed here.

Next case reproduced: validation/open-async-handle-exchange-call.crust and .log.
Synchronous helper returns the result of replacing a task; both
The public arbitrations opened remain unchanged.

Snapshot : /tmp/crust-before-async-handle-vector-try-push/.
Diff : validation/async-handle-vector-try-push-async_lowering.py.patch.
