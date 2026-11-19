[Français](ASYNC_FAILURE_ONLY_RESULTS_CYCLE-fr.md)

<a id="résultats-sans-charge-propriétaire-et-relais-asyncsynchrones"></a>

# Results without owner load and async/synchronous relays

<a id="portée"></a>

## Scope

This lot continues [Select results](SELECT_RESULTS_CYCLE.md). Il applique
existing rules AS4/AS12/AS16, RT6/RT7, B1/B2/B4/B5, T1/T2/T11,
L1/L2, D1/D3 and U1, without new syntax or normative change.
AGENTS.md and VALIDATION_GUIDELINES.md are followed.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

`validation/open-owned-noncompleting-child.crust` contains a child with result
owner whose body does not end. The waiting for his handle can yet
continue if launch fails. The parent then changes a field.
initial of both entries is kept in
`validation/owned-noncompleting-write-before.log` : contract of termination absent.
The previous probe without this modification passed; its summary was incomplete
and its two injected launch failures made the expected values
(`owned-noncompleting-before.log`, `owned-noncompleting-probe.log`).

Analysis now distinguishes an absence of termination proved by a summary
complete of an unknown summary. LaunchFailed provides a continuing path without
A direct expectation of the instance, it does not create a positive load source.
no continuation if the child does not finish.
unknown are not transformed into failure paths.

The return of this envelope revealed a second limitation: a list of sources
empty did not allow to distinguish an absent load from an unknown origin.
`Value` and `FunctionResult` portent maintenant `absent_owned_payload`, which is
evidence, not a consequence derived from an empty list.
is spread by transfer, contract, junction and loop. A junction does not keep it
If all its alternatives prove it. A result of ownership naked
The fields and dependencies of the result are
collected separately from this information.

The concrete auditor keeps this absence on the conditional descriptor
He does not create a fictitious pool source. The invariant from where he comes
allows the absence of a source only for this proven optional load.
The interlocked extraction retains the proof; the final extraction impossible
ends this path with an internal diagnosis in the generated C.

Compositional tests also revealed and corrected:

- The junction, in an if async, of handles from different functions
  The catches, sources and effects of the
  branches remain together; inactive tasks keep their nominal type.
- The explicit descending transfer of a pre-existing Result, then its return
  The import of the block is distinguished from implicit access to the parent.
- The connection to the scope of a Transferred Result received by the backend async.
- The parameters and results of the owner's helpers are bankrupt
  synchronous calls from an async state, for Int, String and Vector<Int/u8>,
  including two Result levels. The bridge uses the published contract.
- Temporary responsibility for the burden during the assessment of the arguments
  a suspension keeps it; an anticipated return destroys it.
- Export of the Result from the synchronous bridge, to avoid its destruction before
  the return. The exported symbolic guards are explicitly read by void
  to keep the compilation under Werror without deactivating diagnostics.
- Direct employment of the bridge return in match and in `return <- appel(...)`.
  `drop(-> appel(...))` was already connected; the probe before correction is
  `validation/failure-only-direct-expressions-probe.log`. Intermediate liaison
  is not imposed, and a return without arrow remains refused.
- The interlocked transfer `relay(-> relay(-> resultat))`. The probe
  `validation/open-nested-owned-result-argument.crust` and his diary keep
  the previous refusal despite the arrows.
  calls now receive the same responsibility for cleaning as names.

<a id="tests-modèle-et-mutations"></a>

## Tests, Models and Mutations

`tests/test_async_failure_only_results.py` now contains twelve methods.
no termination include Int/String/Vector allocated, &str, &u8, shared bands
and mutable, and Result<&str,SliceError>. The trials that would actually launch
an infinite child are not executed: the harness imposes a refusal of launch
parent or child and verify the result and destruction.

The finished child-crossing model ends/not ending and failure to launch
absent/parent/child. It excludes the only infinite execution and calculates the traces
The final case produced
the other none. The source of the possible result must remain
in the contract even if the other alternative does not end.

The owners relays are also tested with a really present load,
a wait in the following argument, an anticipated return, the re-use of the pool,
errors at different Result levels, missing transfers and
re-uses after transfer. The case of charge absent without any pool of
result is exercised; it does not depend on an artificial pool added to the program.
An additional method exercises two different handle frames turning back
&Int: Each choice makes the right target and both destruction premature
The results of the test are not available before the result is used.

The native compilation uses Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function and fatal UBSan at O0/O2. The rejected programs go through
verify_program and compile_source. ASan/TSan and general security are not
established by these tests.

Runner `tests/run_failure_only_result_mutations.py` injects eight errors in
temporary copies: refuse the proven case empty, treat an unknown as
not ending, invent a direct continuation, erase a successful source,
lose proof of absence, lose it when a contract is passed, forget a burden
prepared, destroy the exported Result before its return.

<a id="chronologie-et-journaux"></a>

## Chronology and newspapers

The following newspapers are in `validation/`.

- `failure-only-results-initial-o0.log` - four methods, 5,040 s, OK.
- `failure-only-results-expanded-o0.log` : six methods, two failures.
  different nominal types of tasks was an incorrect fixture and was
  The return of an empty Result revealed the
  lack of evidence, corrected thereafter.
- `failure-only-results-marked-o0.log` : marker added ; choice of handles
  was still refused by the backend async, corrected afterwards.
- `failure-only-results-handles-o0.log` Six methods, 8.412 seconds, OK.
- `failure-only-results-relays-o0.log` : seven methods, four errors ; invariant
  of unloaded source, import/break and output bridge not connected.
- `failure-only-results-absence-o0.log` : concrete absence connected ; loop and
  bridge remained in error.
- `failure-only-results-bridge-o0.log` and `failure-only-results-bridge-expanded-o0.log` :
  connected implementation, Werror diagnostics of unused exported guards;
  corrected without releasing compiler C options.
- `failure-only-results-bridge-final-o0.log` - nine methods, 17.918 seconds, OK.
- `failure-only-results-regression-o2.log` : 127 methods, 76,017 seconds, OK on
  the condition prior to the last connections of bridge, loop and concrete absence.
- `failure-only-results-mutations-o2.log` : baseline nine methods, 22.845 s,
  seven errors detected; one inconclusive because an Error expected from the mutant
  The order of the two audits was corrected,
  The final campaign is launched separately.

Final completed passes:

- `failure-only-results-final-o0.log` : nine methods, 30.595 s, OK ; counter
  38 native programmes and 12 rejected programmes in both courses
  (24 refusal checks).
- `failure-only-results-final-regression-o2.log` 149 methods, 133.909 s,
  OK on the code before the last two direct expression connections.
  The supplement is exercised separately below.
- `failure-only-results-mutations-final-o2.log` : basic nine methods,
  32,489 s, OK; eight mutations detected. None inconclusive or surviving
  in this final campaign.
- `failure-only-select-mutations-o2.log` : baseline twelve methods, OK ; the
  five previous mutations of Select results remain detected.
- `failure-only-results-borrowed-handles-o2.log` : an additional method,
  1,436 s, OK.
- `failure-only-results-final-targeted-o2.log` 10 methods, 17,905 seconds, OK;
  includes the chosen loan and four re-use neighbours after transfer
  by renaming, if, break and synchronous contract.
- `failure-only-results-direct-expressions-o2.log` : one method, 7.199 s, OK;
  12 native programmes and 4 programmes rejected by both courses,
  for the four types allocated and the forms drop/match/return.
- `failure-only-results-direct-regression-o2.log` 42 methods, 66.298 s, OK,
  after the direct forms and before the last connection of nested argument.
- `failure-only-results-nested-final-o2.log` 12 methods, 34.714 seconds, OK on
  The interlocked complement has seven native programmes (two,
  three or five calls with/without failure injected, then returns to an argument
  The second stage of the programme is the following:

`failure-only-results-runtime-o2.log` : 275 methods, 514,093 s, OK, process
completed with code 0. This suite loaded the code before the connections
The three complements are exercised in the form of direct and intertwined expressions.
the following selections completed, without restarting the same runtime suite for
There is no process in this lot that covers the roads that it does not directly cover.
Python modules modified and new tests/runners are still in progress.
pass py_compile; the links of the two cycle reports point to
fichiers existants.

## Limites

Abstracts do not generally distinguish the variants of Result in each
The absence of a proven allowance is a more limited property.
field unions remain conservative. Containers and general signatures,
general recursion, public scheduler and handling arbitrations in
Select inactive or losing tasks remain open. Tests for this lot
do not perform implicit clean-up of a launched handle.

The patches in this lot are stored under
`validation/*-failure-only-results.patch`. The overall objective remains ongoing.
