[Français](SELECT_RESULT_STORAGE_CYCLE-fr.md)

<a id="select--type-concret-et-stockage-du-résultat"></a>

# Select: concrete type and result storage

<a id="règles-appliquées"></a>

## Rules applied

This lot applies SL1 (same type in all branches), V1 (segregated local T)
A<T>), explicit transfers and existing contracts of provenance.
No new normative rules are introduced.
a selection destroyed without being expected, and a branch that will not be
Never polluted: the execution order does not change the type of branches.

<a id="contre-exemples-et-correction"></a>

## Counter-examples and correction

`validation/counterexample-select-mixed-result-storage.crust` was accepted
by verify_program and compile_source. The first task made a Local Point,
the second one an A<Point> allowance. The backend compared only the couple
internal (owned, Point), of which ABI C uses in both cases Cell*.

Comparison now includes the class of the result storage.
follows Select transferred by if and break. The task choices before their
This distinction is also retained in Select.
from different pools remain of the same type A<T>: their provenances are
without requiring an identical pool. A &Int reference does not change
type depending on whether its target is local or allocated.

A second test showed that a task building a pool result could
keep in the sources of the result that of a destroyed local capture
before the return. The full contract of origin is now used even
when the function does not need a local result site injected.
The conservative syntax path remains the remedy when the contract does not
The test contrasts a local construction
fresh to a pool construction and also checks two constructions in
pools after destruction of local catches.

Storage remains stable. No change in runtime C or copy
implicite d'une allocation n'est ajouté. Les cas natifs couvrent les structures
with descendants owned and references, the drop of Select before use
The result, the re-use of slots, and the failure of the parent's launch.

<a id="validation-exécutée"></a>

## Validation executed

Next `tests/test_select_result_storage.py` passes 10 methods to O0 in
16.905 s : 17 native executions, 18 invalid programmes and 36 checks of
refus. Journal : `validation/select-result-storage-count-o0.log`.
Both verification inputs share components; they are not
two independent implementations.

The finished model crosses the two storage classes of each branch and the
suspension of the first branch: eight combinations, four programmes
The oracle compares the types of the oracle
source and calculate the winner according to the order of poll, without reading the decisions
These accounts are included in the above accounts.

The mutation campaign is moving from ten methods to O2 in 17.470 s
and detects five errors by assertions: omission of storage during the
construction, Select if, Select break, task selection and
Conservation of a local unreturned catch.
`validation/select-result-storage-mutations-o2.log`. The process ends with
code 0; internal failures of the five mutated compilers are expected.

The extended regression is estimated to increase to 167 methods at O2 in 150,209 s, in
`validation/select-result-storage-regression-o2.log`It understands the
Select contracts/source/runtime, results and structural handles,
task and hand arguments, local storage and cleaning
Existing models of pollution, destruction and reuse
in these suites complete the target model. All processes
Finals are completed with code 0.

Executables are compiled with clang C11, pthread, O0/O2, warnings
no new results for ASan or TSan nor proof
the formality is not claimed.

<a id="chronologie-et-limites"></a>

## Chronology and limitations

- The baseline retains 27 failures in `select-result-storage-baseline.log` :
  26 invalid acceptances at both entries and an instrumentation error
  This test injected into the async entry then
  the target launch was synchronous; the injection now targets the
  good entry, with re-use of two slots after failure.
- The first sequence of seven methods passes in 5,895 s, then the enriched suite
  of ten methods in 1,095 s. Newspapers `select-result-storage-first-o0.log`
  and `select-result-storage-second-o0.log`.
- Invalid programs were not executed in C. Their acceptances
  initials violate typing, without demonstration of memory corruption.
- The storage classes of the structures represented are covered, not
  all aggregate types or async signatures possible.
- This validation is not a general proof of safety.

The user confirmed that the type of custom scheduler and its
public signatures still to be arbitrated.
The point is recorded in the `design-buffer/points-ouverts.md`.
The overall construction site remains active and incomplete, particularly for the guards of the
The results of the study are not represented.
A further difference is retained in the `validation/open-async-owned-enum.crust` :
the transfer of a user enum in a task and then its return is refused
by the restriction of async catches, while the synchronous pendant is
The diagnosis is in `validation/open-async-owned-enum.log`.
This does not codify refusal as a rule of language.

## Reproduction

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_select_result_storage -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_select_result_storage_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_select_result_storage test_select_source test_select_results test_select_contracts test_select_runtime test_task_result_storage test_public_structure_handles test_sync_task_arguments test_async_execution_arguments test_async_result_storage test_async_local_owned_result_graphs test_suspended_cleanup -v
```

The implementation diff is archived in
`validation/select-result-storage-async_lowering.py.patch`, since the snapshot
`/tmp/crust-before-select-result-storage/`.
