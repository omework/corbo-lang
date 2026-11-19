[Français](ASYNC_EXECUTION_ARGUMENTS_CYCLE-fr.md)

<a id="handles-lancés-transmis-à-une-fonction-depuis-un-état-async"></a>

# Runs transmitted to a function from an async state

<a id="règles-et-périmètre"></a>

## Rules and scope

This lot applies explicit transfers, reservations until waiting,
The results dependencies and RT5–RT7, MT5–MT6, SL2. No new semantics
is invented. The user choice SL2 remains: refuse a loser of Select
who has a handle that is still being thrown to wait, without hidden join.

The explicit transition from a handle to a synchronous relay from async is connected
for the signatures represented. This does not start the task again and
The auxiliary is required to wait and may be required to complete the procedure.
A man who calls join has been forbidden since then.
an async function; it is usable in a native thread block.

<a id="défauts-trouvés-et-corrections"></a>

## Faults found and corrections

The programme `validation/open-public-structure-async-relay.crust`, valide,
The two stages of the C-bridge were rejected by the registry of signatures.
the backend now accepts the parameters of execution, public or concrete,
keeping catches, storage sources, profit loans and deferred effects.
The arguments are prepared from left to right. A suspension in an argument
later keeps reservations; an output abandoning the prepared handle
A release before its creation remains allowed.

`task_sync_adopt` transmits pointer and error to synchronous representation
without submission or expectation, invalidates the source and retains the common protocol
The native async workers are already detached; their end is
observed by the same worker_done protocol.

The effects analysis also treated a pure handle relay as a launch.
It now retains its deferred catches without carrying out their effects.

A counter-example of safety was then found: in
`validation/open-native-wait-argument-field-effects.crust`, insert `drop(->b)`
avant `print(*v.data)` after the call from the auxiliary `wait` was accepted both
The journal is now able to refer to the following: b.
`validation/async-execution-arguments-native-field-probe.log` keeps this
acceptance; invalid C was not executed.

The waiting indicated by the contract now applies the effects of the handle
backend and field analysis, and it also retains the initial state,
in case of LaunchFailed. The test covers the local fields in the block
native and the fields of injected carriers, visible in his caller.
Omitting each of these two corrections separately is targeted by mutation.

<a id="validation-exécutée"></a>

## Validation executed

The final targeted suite passes 19 methods to O0 in 21,740 s : 26 executions
natives (dont l'oracle du pont C), 25 programmes invalides et 50 contrôles de
refus. Journal `validation/async-execution-arguments-complete-count-o0.log`.
The baseline of mutations at O2 passes these 19 methods in 22,020 s; the six
final mutations are detected by assertions, without survivors or delay
Overtaken in this last campaign.
`validation/async-execution-arguments-complete-mutations-o2.log`.
These six selected errors do not give an overall detection rate.

The extended regression went from 214 methods to O2 in 255,973 s, with
`CRUST_SANITIZE=undefined` for historical harness. It includes the
17 first methods of this batch, the arguments of tasks, public handles
structures/references/allocations/views, field effects, cleaning
suspension, Select, native blocks, concrete relays and storage of
The last two batch methods are covered by the basics
Final O0 and O2 above.
`validation/async-execution-arguments-regression-o2.log`.
All the processes mentioned are completed. The final campaigns are with
Code 0; intermediate failed tests remain archived.

Reproducible final commands since filing:

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_async_execution_arguments.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_async_execution_argument_mutations.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_sync_task_argument_mutations.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_async_field_return_model test_async_field_reborrow_model test_async_struct_reference_field_model -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_async_execution_arguments test_sync_task_arguments test_public_structure_handles test_public_borrowed_handles test_public_owned_handles test_public_view_handles test_async_field_application test_sync_handle_field_effects test_suspended_cleanup test_select_contracts test_select_source test_native_blocks test_native_sync_calls test_concrete_handle_relays test_task_result_storage test_async_child_field_effects -v
```

The last command now includes both methods added after the
launch of the archived campaign; its expected number is 216.

- Targeted follow-up: repeated transfers, public/concrete types, scalar results,
  shared/mutable references, tables, str, local/pool structures,
  Re-use of capacity one, launch errors and no re-submission.
- Refusal: too short targets/pools, early drop, re-use of the consumed handle,
  implicit transfer, incompatible type, hidden join, return/break/continue outputs
  and loser Select abandoning a prepared handle.
- Three existing finished models pass: result paths/last use,
  Field/reborrow breakup, task dependency → carrier → target.
  They cover 53 admitted native executions and 19 refusals to the auditor,
  in three methods, 36,986 s, at O2. They are not a complete model
  the scheduler or the new C bridge.
- The historical campaign of task arguments passes its basic of 18
  methods in 17.775 s; the seven errors are detected, including one by crash
  The compiler. `async-execution-arguments-historical-mutations-o2.log`.

Native executions use clang C11, pthread, treated warnings
as errors, fatal UBSan and O0/O2 according to the newspaper. No results ASan or
TSan nouveau is claimed.

<a id="essais-intermédiaires-conservés"></a>

## Intermediate tests retained

The first tests corrected fixture errors: link names
re-used, transfer to an absent child block, expression after return,
and non-explicit native block captures. Newspapers remain available.
The sixth suite refused the valid case of post-waiting fields: the backend
had been corrected but not yet the field summary.
17 methods in 10,029 s.

The first two mutation campaigns met with non-unique anchors
The second also observed delays on the
mutations losing pointer or error: classified as inconclusive, without masking
a direct oracle C of the transfer between representations control
Now these invariants without schedule or expectation.
generated the necessary runtime async; it was corrected by asking
a launch from async. No result of this incorrect fixture is
counted as proof on the runtime.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Auxiliary persons waiting for a handle and also changing fields, or returning
a result borrowed/owner depending on this expectation, are not
The analysis of delayed effects maintains a diagnosis
The following conditions apply:
Cases tested use scalar result and do not add writings
clean in the waiting auxiliary.

The replacement of dependencies of a descending field, general signatures
and the public API replacing the scheduler remain open.
handle launched by an inactive task remains a separate arbitration of SL2.
A successful sequel does not establish the general safety of language or executions
This report does not close the overall objective.

The four compiler/runtime differences are archived under
`validation/async-execution-arguments-*.py.patch`, since the snapshot
`/tmp/crust-before-async-execution-arguments`.
