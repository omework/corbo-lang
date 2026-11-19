[Français](ASYNC_EXCHANGE_JOIN_CYCLE-fr.md)

<a id="résultats-de-replacetry_push-enveloppés-par-spawn-et-join"></a>

# Replacement/try_push results wrapped by spamn and join

<a id="règles-et-réalisation"></a>

## Rules and implementation

Application of RT6, AS2–AS5, AS8–AS14, H1–H2, VE3–VE4, U1, F3–F4 and
SL1–SL2. No normative rules are changed. The launch error remains
separate from the job result: the connected types are
`Result<Result<A<Int>,A<Int>>,runtime::Error>` and
`Result<Result<(),A<Int>>,runtime::Error>`.

Signatures, contracts and representations C distinguish between the two envelopes.
Storage C contains an external status and an inner VectorHandleResult.
The external status determines if a load exists; for try_push, the status
then determines whether this charge has the rejected input.
cleaning uses these conditions in the scopes, catches and arguments
No object targeted by a handle is moved.

Join from hand and waiting for a handle since async return the envelope.
Public handles, synchronous helpers, captures, async returns and factories
Keep the contracts of provenance. The extraction of the Ok exterior returns
the domestic result, which in turn requires explicit consumption.
The junctions of blocks, branches and loops carry the sources of the
two arms and their cleaning obligations.

<a id="cas-exécutés"></a>

## Cases implemented

Eleven methods in `tests/test_async_exchange_join.py` : 33 native executions
and seven invalid programs verified by verify_program and compile_source.

- Replaces successfully or refused by index, then failed submission injected.
- Expecting a handle from async, with result or error of launch.
- Public handle, wait helper, relay of result; transfer absent refused.
- Drop the named result and after transfer by block, on both variants.
- Unused result and double consumption refused.
- Try_push with available space or area of 1 MiB actually full.
- Inactive Outcome Capture, Execution or Destruction, Single Destruction
  and re-use of slots.
- The result prepared before the following argument, with continuation or
  destruction of Select's losing branch.
- Return of the envelope from async, directly or via a synchronous factory.
- Pools separated by arm; old allowance returned after disappearance
  the incoming vector and pool; source too short refused.
- If and loop producing envelope; owner pattern ignored refused.
- Try_push wrapping relayed, destroyed, captured or released
  failed, with only one destruction of the entrant.

<a id="défauts-et-corrections"></a>

## Deficiencies and corrections

The first passage noted a loss of the metadata of the arms in the
symbolic relay parameters. Async launch failure test aimed
also the wrong meter: the harness counts separately the bids
The first asynchronous submission is now targeted,
without changing the expected result in case of failure.

The following passages revealed two static follow-up defects: identity
missing incoming in the relay C bridge and lost provenance at a junction
if. Load metadata and their collection at junctions have been corrected.
The auditor's invariants have been retained; valid programs are
The failure logs are still available.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| open-async-handle-exchange-join.log | Initial refusal of envelope at both entries |
| async-exchange-join-first-o0.log | Five methods, 5,539 s, two failures |
| async-exchange-join-second-o0.log | Five methods, 5,919 s, code 0 |
| async-exchange-join-third-o0.log | Ten methods, 8,984 s, two failures |
| async-exchange-join-fourth-o0.log | Ten methods, 10,174 s, a failure |
| async-exchange-join-fifth-o0.log | Eleven methods, 14,599 s, code 0 |
| async-exchange-join-sixth-o0.log | Eleven methods, 15.461 s, code 0, including factories |
| async-exchange-join-regression-o2.log | 127 methods, 127,747 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_exchange_join -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_exchange_join test_async_handle_exchange_results test_async_handle_exchange_calls test_async_option_join test_async_handle_option_results test_async_handle_option_calls test_async_structure_effects test_factory_owned_effects test_public_handle_contracts test_select_source test_task_wakes -v
```

C11/pthread, error warnings, fatal UBSan. The existing harness injects
the failure of submission; the expected values and cleanings are fixed by the
Regression includes existing Select pollution/cleaning models
and task wake-up. No new model, deployment campaign or audit
These results concern the paths carried out, without
general proof of safety.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The two envelopes around A<Int> are connected within the perimeter described.
Launching a task that already returns such an envelope adds another Result.
This additional level remains explicitly refused and must be connected;
This refusal is a limit of implementation, not a new language rule.
Reproduction : `validation/open-async-nested-exchange-join.crust` and `.log`.
Other types of elements and general interlocks are not closed
The public arbitrations already open remain unchanged.

Snapshot : `/tmp/crust-before-async-exchange-join/`.
Neuf diffs sous `validation/async-exchange-join-` : async_lowering.py, crust.py,
effects.py, async_structure_effects.py, results.py, handle_types.py,
Constraints.py, async_result_storage.py and the new exchange_join_types.py.
