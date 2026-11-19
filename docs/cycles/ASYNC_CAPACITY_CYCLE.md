[Français](ASYNC_CAPACITY_CYCLE-fr.md)

<a id="cycle-as7--dimensionnement-des-pools-détats-async"></a>

# AS7 cycle — Dimensioning of async state pools

<a id="périmètre-et-décisions"></a>

## Perimeter and decisions

Application of AS7 and draft 04; no new normative rule.
The default C capacity of 16 no longer dimension Crust programs.
`#(directive, async_pool_sizes={nom:capacité, ...})` configures pools to
The capacity must be strictly positive Int32;
duplicates, unknown names and embedded guidelines are refused.
accepts qualified names in the directive, but declarations of namesspaces
A qualified unknown name receives the corresponding diagnosis.

The specializations of the same generic async function have pools
separate; the capacity indicated for its source name applies to each.
Explicit abilities remain physical limits: an insufficient limit
causes the existing controlled stop, without re-use of a live slot or enlargement
The cyclic creation diagnosis lists all the pools still not
bounded, including cycle dependent descendants.

<a id="calcul-et-hypothèses"></a>

## Calculation and assumptions

`async_capacity.py` extracts creations between functions async.
synchronous identifies the task/hand locations encountered in the
This statement is monotonous: restore a state
to analyze another branch does not remove the locations of the first one.
It includes opaque call results, symbolic parameters and
alias; he therefore overestimates the necessary storage.

The backend takes up temporary workers who may hold a task or a handle in
Each async state. For an acyclic graph, the terminal of a type adds up the
synchronous locations and, for each parent type that can create it, the terminal
The parent's number of temporary tasks multiplied by the number of temporary tasks.
explicit cuts the corresponding dependency and allows to limit descendants.
An unused pool receives at least one slot to produce a valid table C.
A calculated terminal exceeding Int32 is refused with explicit capacity request.

Preservation rationale, **not formal evidence** : chaque instance vivante
the current subset has a proprietary location in the code
In a living parent state. Count all these locations, even
between roads or aliases of the same state, increases the number of instances.
The recursive parent remains counted as long as he awaits his child. The boundary follows the
live instances, not just the number of active threads.

Premises to be reviewed in the next extensions: synchronous functions
are not recursive; they are not arbitrarily invoked by the backend
async; async states do not currently accept catches/results of
The loops re-use a new one.
finite number of locations. Select, runtime::thread and new forms of
This analysis must be enriched before it can be accepted.

Crochet C `CRUST_TASK_POOL_CAPACITY` remains available for oracles that
the C factories are directly invoked outside the verified program.
Implicit language capacity, or evidence of arbitrary C.

<a id="contre-exemples-et-interactions"></a>

## Counter-examples and interactions

- Nineteen tasks returned by a synchronous factory and kept together:
  The previous fault of 16, now accepted and executed.
- Nineteen tasks in a branch completed by `return` : collecter uniquement
  The final state of the auditor would forget this branch.
  A mutation restoring oblivion is detected.
- Direct depth recursion four: capacity four admitted, capacity three
  exhausted with `task pool capacity exceeded`. The parent is not released before
  the child's return.
- Mutual recursion and independent cycle: all missing names are included in
  diagnosis; an explicit capacity on one member of the terminal cycle the other.
- Independent model: 1 or 3 parents each retain 1 or 3 children inactive.
  The expected peak is the product, calculated without consulting the verifier.
  C takes all parents to the Yield before finishing one, then
  Make sure all pools are empty. Four configurations executed.
- Return of hands by contract, transfer of an allowance to parent and
  child, waiting, unique capture cleaning and re-use of address.
  Using the transferred value remains denied.
- Two specialisations of character type, two data pools, shared catches,
  Waiting for the hand and resuming the mutation after waiting. A mutation before
  The wait is still denied.
- Loop with continuous and break: the tasks are cleaned every time iteration.

<a id="exécutions"></a>

## Implementation

Clang Homebrew 20.1.3., arm64 macOS; C11, UBSan with
`-fsanitize=undefined -fno-sanitize-recover=all`. Oracles C also use
`-Wall -Wextra -Werror -Wno-unused-function -pthread`.

| Implementation | Result | Trace |
| --- | --- | --- |
| 9 methods targeted at O0 | Successful, 10,623 s | validation/async-capacity-final-O0.log |
| 9 methods targeted at O2 | Successful, 10.898 s | validation/async-capacity-final-O2.log |
| 7 first methods + handle obligations + async features | 19 successful, 17,289 s | validation/async-capacity-O2-regression.log |
| Two interactions added then | Successful, 1,368 s, then included in both final executions | validation/async-capacity-interactions.log |
| Two oracles C of concurrent register and re-use | Successful, 1.578 s | validation/async-capacity-C-boundary.log |
| Quatre mutations | All detected | validation/async-capacity-mutations.log |
| Inferred Borne beyond Int32 and cut by explicit capacity | A successful method, 0.01 s | validation/async-capacity-overflow.log |
| Return of recursive borrowing after explicit capacity | Diagnosis of provenance retained, successful method, 0.565 s | validation/async-capacity-relay-final.log |

The nine targeted methods run 13 binarys per level: 12 successes and 1
The program is being tested for 11 rejected programs.
The four are the only ones that have been accepted, but the only one that has been accepted is the refusal and compilation of the giant C.
mutations replace the boundary with a ceiling of 16, forget the children,
forget the history of branches, or enlarge an explicit capacity.
The last is detected by the native behaviour of exhaustion; the three
The first is the assertions of a boundary arising from independent scenarios.

The historical test of return of recursive borrowing was awaiting diagnosis of
AS7 now gives priority to the
the missing capacity. This test now provides `relay:4` to continue to
test the restriction of origin; no acceptance was relaxed.

The first run revealed errors in the new test driver:
incorrect ABI state names, non-existent release method and bad name
for the expected diagnostic argument. They were corrected by reading the ABI,
without changing the tested semantics. The initial log is kept. L
test classes in this module also launched runtime/features suites;
they have been replaced by import modules.

Large regression of the initial journal: 304 methods in 521.670 s, with five
failure d'assertion and one error (including four sub-case failures of the ABI pilot)
(a) Among the pre-existing follow-up: **274/275 async methods and 22/22
successful typical features methods**. The only remaining async method is that of
Diagnosis of provenance, adapted and successfully re-executed above.
new cases of failure have all passed in the final targeted executions.
There was no second monolithic execution of 304 methods.

An additional synchronous regression performed 243 methods in 128,684 s:
239 successful, four methods with 14 sub-case errors, all due to
(U1), in the case of the `test_conditionals`.
The newspaper is `validation/async-capacity-sync-regression.log`. Ces quatre
programs have been explicitly read out `data`, `inner` ou `fresh`, with
assertions on the updated exits. The assertions of destruction and their
order are kept: no one has replaced a cleaning of the scope/reset with a
The 28 methods of `test_conditionals` then succeeded in
55.242 s with fatal UBSan (`CRUST_SANITIZE=undefined`), at the level of optimisation
default of Clang; trace `validation/async-capacity-conditionals-migrated.log`.
The first synchronous batch used the strict historical flags of its helpers,
without imposing a sanitizer overall; it does not constitute an UBSan execution
The reset tests remain in the explicit compatibility profile.

The final validation consolidates these executions and targeted re-runs: it does not
claims that a single global suite was relaunched after migration.

## Limites restantes

The terminal is not minimal: exclusive branches, sequential calls, functions
unused and aliases may inflate it. The explicit limit is then usable.
The recursion is tested here for scalar results; the results
Recursive borrowed is not covered. The exhaustion stops the process:
it does not constitute proof of cleaning all other tasks.
Namspaces, Select, user structure captures, the scheduler
public, public types runtime::Handle/runtime::Error and mutex remain
This validation does not demonstrate the general safety of the language or the
completion of the seven drafts.
