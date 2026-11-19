[Français](ASYNC_HELPER_RESULT_CONTRACTS_CYCLE-fr.md)

<a id="résultats-empruntés-à-travers-les-contrats-sync-et-async"></a>

# Results borrowed through sync and async contracts

Cycle of 7 November 2026. Application of existing rules B4c/B4e,
ST8/ST12/ST14, B1/B2/B4a, AS12/AS13 and MT3. No rule of law changed.

## Corrections

The Counter-Example `validation/open-async-helper-result-sync-contract.crust`
is now accepted and displays 21, 8, 21. Summary of a synchronous helper
is available on request during the inference of async results, before
the assembly of full effects and constraints contracts.
A cyclic dependence does not receive a
The bodies and calls are always in the hands of the public.
Checked by existing passes.

The projection also retains when a function makes and returns
The capture still reserves the full argument before waiting;
the result of join then reserves only its paths and capacities.

Another function can receive the handle, attach it and return the reference.
Symbolic verification now builds dependencies of the fields of
its catches, with separate keys by capture.
The results are also based on its origins and paths, although the
The scalar representation marker did not cross a relay.
do not become a means of erasing the targets or ancestry of borrowing.

The C of the initial case is retained in
`validation/async-helper-result-contract-fixed.c`. Implementation diffs
are `validation/async-helper-contracts-{async_lowering,crust,results}.py.patch`.

<a id="validation-exécutée"></a>

## Validation executed

- `async-helper-contracts-final-o0.log` Nine methods, 23.797 seconds, OK.
- `async-helper-contracts-complete-o2.log` 24 methods, 33,762 s, OK,
  before the last conditional test and the correction of the handle parameter.
- `async-helper-contracts-full-mutations-o2.log` : baseline final of eight
  successful methods, nine C executions (including an injected launch failure),
  15 invalid programs controlled by check and compilation (30 checks).
- Independent model: 24 combinations, 18 executions and six refusals.
  oracle of paths and last uses is exercised via helper → child async
  → join → synchronous result; only the program generator changes.
- `async-helper-contracts-final-regression-o2.log` 67 methods, 52.559 s,
  66 successes and a historical U1 error, detailed below.
- `async-helper-contracts-fields.log` : 56 historical methods on the fields
  Share/mutable, 42,193 seconds, OK.

The new harnesses use Clang C11 pthread, fatal UBSan, O0/O2 depending on
The historical methods of testing_crust ignore CRUST_TEST_OPT and
do not add any explicit optimisation option, even in the selection of which
no results added.

The six final mutations are detected: helper contract unavailable,
path erased, projection lost in a factory, alternative omitted,
symbolic capture dependencies omitted, projected classification omitted.
The omitted alternative makes a forbidden access accepted; other errors are
This is not a case in point, particularly in the case of refusal of valid programs.
The survivor of the
previous cycle is not reclassified by these results.

<a id="échecs-conservés"></a>

## Cheques kept

`async-helper-contracts-initial-o0.log` : two errors, factory projection
missing and fixture that read a target before the last use of its wearer.
The fixture now destroys the carrier before rereading the target and checking
the re-use of the pool. The next targeted passage succeeds.

The handle-parameter, handle-parameter-recheck and handle-parameter-final
keep the rejected steps: symbolic targets are absent, then contract and
The paper handle-parameter-resolved-o2
confirms the correction; the test is included in the final passages.
The first mutation campaign retains an ambiguous anchor; the anchor of the
Reference contract was specified prior to the full marketing year.

Historical fixture `test_same_input_preserves_pending_export_and_reception_order`
recevait `other` The U1 failure was reproduced in a
copy of the compiler restored to snapshots before this lot:
`async-helper-contracts-results-baseline.log`. `print(other)` was added,
with the corresponding expected output; the expected destruction order
Stay exactly `data` then `other`. The corrected check succeeds in
`async-helper-contracts-results-fixture-recheck.log`. The initial journal of
67 methods are not presented as entirely green.

## Limites

The projections supported remain those of the Int and Int fields.
reborrowing &mut Int, with their already available modes. The detached return of a
shared field, more general graphs, field updates in
the states and other batches of the lens remain open.
The models are finished and the results are not added.
The tests don't explore all the schedules.

The extended native regression is complete: 278 methods, 224.718 s, OK,
in `validation/async-helper-contracts-native-o2.log`. It started before the
last addition on handle parameters; final targeted passages
and contract/field regressions cover this supplement.
The final baseline of the six mutations consists of eight methods, 9.202 s, OK.
The corrected historical fixture was re-executed alone in 0.314 seconds, OK.
