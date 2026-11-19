[Français](TASK_RESULT_STORAGE_CYCLE-fr.md)

<a id="stockage-du-résultat-dune-tâche-dans-les-contrats"></a>

# Storage of the result of a task in contracts

<a id="règles-et-défauts"></a>

## Rules and defects

This lot applies V1, T1/T6, contracts, B1–B5, D1, L1/L2/L6,
AS9/AS12 and MT5/MT6. It does not change the normative rules.
T and A<T> allocation remain separate, even when the result
goes through an opaque task, a concrete handle and several functions.

`validation/open-task-result-storage-contract.crust` was refused to both
steps: the consummation contract could only express the result of the task
The baseline reproduced this refusal.
Point is now a requirement passed on to the callers; it does not convert
A call whose result is in pool is refused.

Two other valid counter-examples were retained and corrected:

- `open-task-result-storage-copy.crust` : a task copy a structure
  The symbolic entry did not describe the storage of this copy.
- `open-task-result-storage-graph.crust` : a task builds a root
  The local pool allowance. The symbolic description and the
  The source of the descendant was confused with that of the
  root; the match or call rejected the local result.

All three fixtures are now accepted in both stages and executed
The control of storage does not remove dependencies on the
descendants pools or the borrowings of the result.

<a id="implémentation"></a>

## Implementation

The further analysis of the requirements project the future result of a
task/execution parameter before examining its sources.
A parameter imposes a local/pool obligation on this parameter.
obligations are propagated until stabilization and published in the contract.
The results already known to be incompatible are refused, even in a function
no call: local fee result, allowance from an injected pool, parameter
explicit A<T>, or already present requirement on the source.

The call verifier reviews task_result_sources for tasks and
The input is not the same as the input from the other catch.
A copy of a loan
receives a result identity distinct from its borrowed target.

`async_result_storage.root_result_parameters` projects the only sources of
the root since the completion contract. The proprietary fields remain
This projection is shared by the flow of constraints
and symbolic descriptions; she does not decide on a new placement.

The public type of connection Handle<Structure> is still in progress.
registry preparations present in handle_types.py/async_lowering.py do
are not activated by this lot, and do not constitute a support for this syntax.
New tests use the Nominal Tasks and Execution<routine>.

<a id="vérification-exécutée"></a>

## Verification performed

Eleven methods in `tests/test_task_result_storage.py` couvrent :

- model independent of the four local storage/pool combinations requested and
  provided; relaying of three functions and inspection of contracts;
- choice between two tasks, the two branches and the two possible sources;
- already launched contracts, and then explicitly expected;
- storage of the result different from that of a destroyed capture without return;
- copy of a borrowed, local or pool structure;
- local root and downhill pool, cleaning and re-use of a pool of
  ability one after destruction of the result;
- result containing a loan, read after relay and refuse a drop
  premature target;
- refusal of a requirement incompatible with an already determined provenance;
- Maintaining the prohibition of hiding synchronous joins in an async call.

`validation/task-result-storage-count-o0.log` : **11 methods, 14 executions
native peoples, 18 invalid programmes, 36 refusal checks**, in 8,301 s.
Refusals are controlled by verify_program and compile_source.
contracts are additional, without performance C.

`validation/task-result-storage-regression-o2.log` : **128 methods in
85,870 s**, including new tests, historical storage requirements,
task arguments, local graphs returned, placement of
results, concrete hand-rails, second references, contracts
of public contracts and Select contracts. CRUST_SANITIZE=undefined and
CRUST_TEST_OPT=-O2 are enabled.

The native harness uses Clang C11/pthread, Wall/Wextra/Werrar,
Wno-unused-function and fatal UBSan, at O0/O2. py_compile succeeds for modules
No new results found. ASan/TSan.

<a id="mutations-échecs-conservés-et-limites"></a>

## Mutations, preserved failures and limitations

`validation/task-result-storage-mutations-o2.log` contains a baseline of
11 methods in 6.444 s followed by seven detected errors: oblivion of the projection of the
result, forgets its requirement, keeps only one possible source,
symbolic entry always in pool, confusion of descendants with root,
omission of copy storage and use of catch sources instead
The detections are assertions, including refusals to accept the results.
Incorrect programs or incomplete contracts.
not presented as seven observed memory corruptions.

The six historical changes in the `run_storage_requirement_mutations.py` are
also detected after a baseline of 10 methods in 7.541 s:
`validation/task-result-storage-historical-mutations-o2.log`Both
campaigns are over and do not give any general coverage rate.

Initial/second O0 logs retain two fixture errors: a join
hidden in a function called since async, yet forbidden, and absence
transfer down before a result expression in a child block.
The second execution followed a failed editing script and repeated the
The same fixed amounts have been corrected according to the existing rules; the
hidden is now explicitly tested as invalid.
The fourth reveals the confusion of sources in the flow
The fifth method passes eleven methods after its correction.
The first copy/graph probes also had non-syntactic forms
supported; final fixings retain valid counter-examples
having revealed the defects, and intermediate logs are not removed.

`validation/task-result-storage-remaining.log` confirme :

- the three counter-examples of this batch accepted at both stages;
- Handle<View> again refused by the public signature register;
- replacing dependencies of a descending field since async still
  refused (`open-nested-field-replacement.crust`) ;
- SL2 refusal of `open-select-launched-handle.crust` The two stages.
  user decision "refus this case in the prototype" is already integrated
  in ASYNC_MULTITHREAD_RULES.md and SELECT_LAUNCHED_HANDLE_DECISION.md.

The separate case of an inactive task capturing a handle already launched remains in
General signatures, descending effects, the
The general placement and public replacement of the scheduler are not completed.
Unloaded bankrupt exits, recursive types and all the
combinations of envelopes are not covered exhaustively by this lot.
No resets are reintroduced. The overall objective remains active.

The diffs of the four modules in this batch are archived in
`validation/task-result-storage-*.py.patch`, since the snapshot
`/tmp/crust-before-task-result-storage/`All the processes mentioned are completed.
These finished tests and models are not a general proof of safety.
