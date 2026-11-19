[Français](ASYNC_OWNED_BORROWED_CAPTURES_CYCLE-fr.md)

<a id="captures-propriétaires-de-structures-contenant-des-emprunts"></a>

# Captures of structures containing borrowings

<a id="portée"></a>

## Scope

This lot applies existing rules T1/T6, B1/B2/B3/B4a, D1, ST6–ST15,
L1/L2/L6, AS2/AS5/AS8/AS9/AS13/AS14, RT6/RT7/RT8 and MT8.
AGENTS.md and VALIDATION_GUIDELINES.md are followed. No normative decision
The previous result is described in
LOCAL_RESULT_ENVELOPES_CYCLE.md.

Int, &Int and &mut Int field structure can be transferred in its entirety to
a task. This destroys the received bearer; it does not destroy the targets
The catches retain the sources and capacities of these fields
during the life of the task, regardless of the last use of the name of the task.
The transfer can be from a local value or pool allocation.

This coverage includes direct calls, synchronous manufacturers and relays,
Async appellants, native threads, prepared arguments and branches
Select losers without unsolved join obligation.
all mixed graphs or returns of the captured structure.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

- `validation/open-owned-borrowed-structure-capture.crust` was refused to the
  The backend now accepts these porters using the capture signature
  the existing Cell layout and cleaning, without moving their memory.
- The concrete task retains the targets and capabilities of the object fields
  The parents of loans are transported with them.
- The only reason for this was that the loan was not granted to the company.
  through a factory. `open-owned-borrowed-capture-factory-invalid.crust`
  was accepted in both stages while number was destroyed before join.
  This acceptance is maintained in
  `owned-borrowed-capture-factory-lifetime-counterexample.log`. The programme
  The summary now distinguishes the targets from the
  fields of a parameter transferred from references to the carrier itself.
- A task relay already built also lost the dependencies of the
  fields of his capture owner: `owned-borrowed-captures-task-relay-probe.log`.
  The symbolic task and handle parameters now retain these
  The actual verifier and the constraints of the
  sources reconstruct them to the calls.
- The C Bridge for Synchronous Calls from Async only described the fields
  It now also provides symbolic targets for the
  Int. borrowed fields. It does not support them as possessed values.
- Field loans move from the displaced bearer to the prepared arguments and then
  they are released after destruction/effective expectation of the child's
  The metadata of the old access should not continue to be reserved
  the target after that expectation.
- The suspended effects of a transferred holder are not entries in
  an external holder borrowed. The suspension summary distinguishes the two,
  which allows the cleaning of a losing branch with the holder.
- The header of a native thread transfers an existing value; it does not require
  implicit A<T> to a local structure. Concrete storage remains deduced
  the call, with the source checks.

<a id="tests-et-preuves-exécutées"></a>

## Tests and evidence performed

`tests/test_async_owned_borrowed_captures.py` contains 11 methods.
`validation/count_owned_borrowed_captures.py` counts actual executions
not affecting the oracles.

The final passage O0 (`owned-borrowed-captures-complete-o0.log`) succeeds in
10,653 s : 19 native executions, 24 invalid programmes, each verified in
The final O2 base passes these 11 steps, i.e. 48 refusal checks.
methods in 11.314 sec.

The cases admitted verify the unique values and destructions of the bearer and
The refusals concern premature drop, incompatible access with a
mutable field, source or target too short, use of a target during a
argument prepared, and destruction of target before a losing branch.
A split result is used after the holder has been destroyed; its
Target remains protected after join.

The independent cross pool model of the external/indoor and target carrier
external/indoor. The task leaves the block. Only the external couple /
Each arrangement is tested by direct call and by
manufacture: two executions allowed and six refusals included in the accounts.

The native harness uses Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function, fatal UBSan, at O0/O2. The failures of the scheduler and of the
pthread_create are injected separately. No results from ASan/TSan or proof
General Security Policy is not claimed.

`owned-borrowed-captures-regression-o2.log` : 155 methods go through
146,629 s with CRUST_TEST_OPT=-O2 and CRUST_SANITIZE=undefined. Modules:
async_owned_struct_captures, async_borrowed_struct_pools,
async_borrowed_local_results, local_result_envelopes, async_local_captures,
async_structure_effects, select_source, suspended_cleanup, native_blocks,
storage_requirements. The compiler has been unchanged since this launch; the
last test addition on detached reference was executed separately in
Final targeted follow-up.

<a id="mutations-et-essais-intermédiaires"></a>

## Intermediary mutations and tests

`tests/run_owned_borrowed_capture_mutations.py` injects eight errors in
Temporary copies of the compiler. The final journal
`owned-borrowed-captures-complete-mutations-o2.log` detects all of them:
loss of concrete target, loss of mutable capacity, loss of field in a
manufacture, loss in a task parameter, loss of a child's loans,
loss of C Bridge targets, inactive carrier leak and pool requirement
This is a targeted error, not a rate of error in a native thread.
global detection.

Intermediate tests are kept under validation/:

- `owned-borrowed-structure-capture-baseline.log`, then `...-direct.log`.
- The first factory probe used an unrecognized Task<read> annotation;
  the corrected probe uses the nominal read type. A first refusal due to double
  drop was minimized before identifying the incorrect acceptance above.
- `owned-borrowed-capture-factory-contract.log` keeps an internal error
  intermediate: confusion between the target type and the mode of a field.
  journal `...-contract-fixed.log` shows the correction and the published contract.
- `owned-borrowed-captures-initial-o0.log` and `...-relays-o0.log` keep the
  relay and bridge defects; `...-bridge-o0.log` I'm going through all four methods.
- `...-expanded-o0.log` Keeps native and Select refusals corrected;
  `...-contracts-o0.log` I'm going through ten methods.
- `...-mutations-o2.log` detects two mistakes and then stops on one point
  ambiguous injection. The anchor is made specific to the owner field;
  `...-mutations-final-o2.log` detects the eight errors with ten methods.
- The invalid argument prepared was then made explicitly transferring
  with `n ->;`, to check the loan conflict rather than a denial of a scope.
  The final suites keep this version.

All the final processes mentioned are completed.
`/tmp/crust-before-owned-borrowed-captures` are kept under validation/.

<a id="écarts-ouverts-et-prochain-lot"></a>

## Open deviations and next batch

Two valid programs remain unanswered and are retained:

- `open-owned-borrowed-capture-result-owner.crust` : return the structure
  The target contract for the result must project its fields
  from the owner capture; it must not ask for a &Int parameter
  additional.
- `open-owned-borrowed-mixed-task-relay.crust` : relay a task whose
  carrier has both a shared field and a mutable field.
  currently groups the capabilities by capture parameter and becomes
  too exclusive for the shared field target. The direct case without this relay
  The distinction must be kept by field.

Their newspapers are `owned-borrowed-captures-remaining-results.log` and
`owned-borrowed-captures-mixed-task-relay-probe.log`. Graphs containing
simultaneous A<T> fields and references, recursive projections
The overall objective of the programme is to provide a framework for the implementation of the programme.
The shared reading probe derived from a mutable parent is preserved as
observation, sans lui attribuer une violation normative ni durcir une règle.
The lot is validated within its described perimeter; the overall implementation of the
rules are not declared complete.


Next: the first two open programs are now admitted and tested
in [the field contract cycle](ASYNC_CAPTURE_FIELD_CONTRACTS_CYCLE.md).
The above findings describe the previous state; the general graphs remain
The new cycle retains another counter-example of the factory.
