[Français](SELECT_SOURCE_CYCLE-fr.md)

<a id="sl1--select-depuis-le-langage-source"></a>

# SL1 — Select from source language

<a id="portée"></a>

## Scope

This lot connects the syntax and the contracts of the lot
[previous](SELECT_CONTRACTS_CYCLE.md) to the catch verifier, the statements
The SL1, AS2–AS15, B1/B2/B4/B5, T1/T2/T11 and
L1/L2 remain unchanged. AGENTS.md and VALIDATION_GUIDELINES.md are followed.

`runtime::select(-> ...)` is now executable in async bodies for
This status replaces the restriction of the
source compilation indicated in historical reports, without changing their
past results of execution. This lot does not complete the entire async yard.

<a id="implémentation"></a>

## Implementation

- The arguments are evaluated from left to right. Tasks already built
  have a temporary cleaning manager during the assessment of the arguments
  the following, including if the latter suspends or leaves the block.
- The manufacturer checks the catches as soon as they are created and requires a type
  branches can be named tasks,
  direct calls or tasks produced by blocks, ifs and loops.
- The wait requires a mutable link and produces a single result.
  "Already expected" follows the renaming and transfers.
  losers remain reserved until the cleanup of Select.
- Select's state and branch inputs remain in stable limbs
  a transfer chosen by if or break transmits a pointer
  to this state, without moving the states of the branches or their allocations.
- The transfers check the lifespan of the targets and pools.
  The results are based on the following data:
  stored after drop of Select.
- Cleaning works at the end of the blocks, at the early exits and at the
  suspensions of an interlocked selection. Prevalidation of cleanings
  suspensions include its branches, without adding a hidden waiting of a handle.
- Select mechanism code C is included when the program builds it
  a. Existing dimensioning includes the locations of the retained tasks.

<a id="contre-exemple-et-renforcement-des-tests"></a>

## Counter-example and strengthening of tests

The source transfer of a selection from a block was refused prior to the batch.
Reproducing with previous copy of async_lowering.py and acceptance
after correction are kept in
`validation/select-source-before-transfer-counterexample.log` ; the programme
is `validation/select-source-block-transfer.crust` and his family is executed
by transfer tests. The complete example `examples/select.crust` passe
also by the LTB: `validation/select-source-cli-final.log`, sorties 20
Then 9, unique destruction of numbers.

The programme
[select-immutable-shadow-counterexample.crust](../../validation/select-immutable-shadow-counterexample.crb)
was wrongly accepted: a mutable selection destroyed in a block left
its name in all the mutable links. A new unmistakable link
then the same name could be expected. The output of the scope now removes
The programme is refused in both courses; the neighbour
with `let mut` is executed. The mutation that reintroduces the mutability leak
is exercised separately.

A mutation reset the waiting state at branch junction a
The test was only passing through a simple block.
now also covers two branches each having expected their Select, and
the refusal of a second expectation of the transferred result. The oracle remains the rule
No change in the normative behaviour.

<a id="scénarios-et-preuves"></a>

## Scenarios and evidence

`tests/test_select_source.py` contient maintenant vingt-quatre méthodes. Elles couvrent les
shared and mutable catches, conditional and loop transfers,
loans returned, owners returned from two pools,
Single wait, inactive construction, break/continuous outputs,
re-use, suspended cleaning and modification of left-over fields
The results Int, Bool, u8, char, &str and fixed tables
are executed; this is not worth covering all types of language.

An independent model chooses the first result from two branches with
Zero, one or two breaks. It uses only two pause counters;
no contract or internal object of compiler. The nine combinations compare
the value returned, the single destruction of both catches and the re-use
Pool. Wake-up models and field effects from previous batches
restent distincts de ce modèle volontairement limité aux `yield`.

The native harness uses Clang C11, pthread, Wall/Wextra/Werrar and fatal UBSan,
The results of the tests are based on the results of the tests. `verify_program`
and `compile_source`. Mutation tests work on copies
the compiler with the same oracles.

Newspapers already completed:

- `validation/select-source-initial-o0.log` - Nine methods, 5,098 s, OK.
- `validation/select-source-transfers-initial-o0.log` : 12 methods,
  6,762 s, OK.
- `validation/select-source-expanded-initial-o0.log` : 17 methods,
  Three errors of fixeds kept. They used print(Bool), a
  Int to u8 conversion not exact and a literal tank not supported.
  Fixtures now use a boolean condition, a literal
  context u8 and explicit conversion to char_at.
- `validation/select-source-expanded-o0.log` : 17 methods,
  10,626 seconds, OK after fixing.
- `validation/select-source-computed-initial-o0.log` : 20 methods,
  15,810 s, OK.
- `validation/select-source-regression-contracts-o2.log` 76 methods,
  24,119 seconds, OK. This passage precedes the final reinforcement of the waiting test
  After joining; it includes the 20 source tests, 16 Select contracts,
  15 suspension contracts and 25 async field contracts.
- `validation/select-source-mutations-initial-o2.log` : successful baseline;
  six mutations identified, one survivor described above and one
  The latter did indeed cause the judgment of the Court of First Instance in Case C-329/92, which was not inconclusive.
  `internal error: source still has live allocations` ; the classifier
  confused this diagnosis of runtime with a C compilation error.
  The classification now distinguishes this diagnosis.

- `validation/select-source-final-o0.log` Twenty methods, 31.867 s, OK;
  46 native performances admitted and 34 programmes refused in both courses
  (68 checks) Cases are repeated with previous passages.
- `validation/select-source-mutations-final-o2.log` : baseline of twenty
  successful methods and eight detected errors: loss of losers' loans,
  oblivion of the single wait, leakage of mutability, omission of normal cleaning
  or suspended, loss of life on transfer, loss of returned targets,
  forget about the state already expected at the junction.
- `validation/select-source-cleanup-mutations-o2.log` : baseline of ten
  successful methods and eight previous cleaning errors detected.
- `validation/select-source-contract-mutations-o2.log` : baseline of sixteen
  successful methods and eight mutations of Select contracts detected.
- `validation/select-source-runtime-mutations-o2.log` : baseline of seven
  successful methods and seven mutations of the Select mechanism detected.
- Python compilation of successfully modified files. Differences with the
  copy prior to the batch are kept in
  `validation/async_lowering-select-source.patch`,
  `validation/async_runtime-select-source.patch` and
  `validation/crust-select-source.patch`.

The extended runtime regression is completed:
`validation/select-source-regression-runtime-o2.log`, 292 methods,
542,077 s, OK. She loaded the code before the two supplements below.

<a id="complément--branches-impossibles-à-poller"></a>

## Supplement: branches impossible to pollute

The [open-select-source-unpolled-contract.crust] programme](../../validation/open-select-source-unpolled-contract.crb)
the following recursive branch cannot therefore be
The symbolic contract already knew, but the backend
requested his suspension summary and refused the program. Both refusals
initial are retained in `validation/select-source-next-gap.log`.

The backend now operates this frontier: a branch of which all the
possible contracts exclude suspension prevents the following from polluting.
However, their catches are still retained for cleaning.
result only reachable branches can end.

Alternative selections from if and break each retain their own
The same thing happens in the same way as the other branches.
one alternative by the first branch lends another. The test checks
the value of the field modified on both paths, and the refusal of a
premature mutation of its target in async state.

- `validation/select-source-poll-paths-initial-o0.log` : 22 methods,
  34,084 s, OK; before strengthening local field control.
- `validation/select-source-poll-paths-field-o0.log` : enhanced control
  passes separately, 3.397 s.
- `validation/select-source-poll-paths-mutations-o2.log` : neuf mutations
  The latter reintroduces the refusal
  known from the valid program with non-polished branch. The harness reports
  now this explicit refusal as a failure to assert the admitted case,
  separate from the compiler's internal exceptions; the expectation remains unchanged.
- `validation/select-source-poll-paths-final-mutations-o2.log` : baseline of the
  22 methods, 39.275 s, OK; the ten mutations are detected.
- `validation/select-source-poll-paths-final-o0.log` : 22 methods,
  42,715 s, OK; 51 native executions and 43 programmes rejected in both
  The training courses, i.e. 86 refusal checks.
- `validation/select-source-poll-paths-regression-o2.log` 95 methods,
  73.991 s, OK. This passage only precedes the explanation of the assertion
  The compiler and expectations are identical.

The runtime regression of 292 methods loaded the code before this addition.
The new regression selection includes contracts, the backend Select and
cleanings suspended on the code after addition. Do not assign
old results to a version they didn't run.

<a id="complément--captures-dune-gagnante-certaine"></a>

## Complement: captures of a certain winner

The programme
[open-select-single-winner-loan.crust](../../validation/open-select-single-winner-loan.crb)
was refused after waiting for a single branch selection: its result
Int contains no borrowing and no loser keeps his capture, but
access to the target remained reserved until the drop of Select. Both refusals
before correction are kept in `validation/select-source-single-winner-gap.log`.

For each selection alternative, the backend now identifies the
branches can end. If only one can win, it removes
his catch completed from Select's loans. He keeps those of all the
possible losers, including those never polluted. References
by the result and the fields modified have their own dependencies: this
Liberation does not erase them.

Two equivalent expectations of an external selection, one in each arm,
produce the same static reservations. They join without inventing
a difference in obligations due to the identities of the Python lists.
The additional number after the junction remains refused.

The passage `validation/select-source-winner-initial-o0.log` implements 23 methods,
25,159 s, OK. The external junction test passes separately in
`validation/select-source-outer-paths-o0.log`. Final passages of the code
after these supplements are followed in `select-source-winner-final-o0.log`,
`select-source-winner-final-mutations-o2.log` and `select-source-winner-regression-o2.log`.
Their final results are:

- O0: 24 methods, 49.026 s, OK; 56 native executions and 49 programmes
  The two courses were rejected, i.e. 98 refusal checks.
- O2 mutations: baseline of 24 methods, 48,408 s, OK; 12 mutations
  The results of the survey were not available.
  artificial difference in bookings after two equivalent expectations.
- O2 regression: 97 methods, 71,348 s, OK; final code of the three parts
  of this lot, including the results of suspended cleanings and runtime Select.

All cycle validation processes are completed with their codes
The results of the intermediate passages are still observed.
This cycle does not demonstrate general security and does not end the objective
The following limits are always open.

## Limites explicites

- The Unions of catches and effects of the backend are conservative.
  do not exactly distinguish the winning branch, and can retain from
  Additional targets where contracts describe only a possible suspension.
  This may refuse valid programs; it is not a new rule.
  The certain winner benefits from the above complement; correlation
  The overall value of the result and the identity of the winner remain open.
- The general aggregate results, other reference containers and the
  path correlations still need to be connected. A scalar success or a
  Int allocation returned does not prove support for all results.
- The paths that conditionally await the same external Select
  the maintenance of the control states when a
  Two paths that each awaited are covered.
- The destruction of a loser holding a launched handle and the capture of a
  The inactive task of the trade union is still open.
  mutex guards and the public interface of the scheduler are not added.
- No ASan/TSan new result, no formal proof, no guarantee
  on all schedules or combinations of types.

L'objectif global demeure incomplet.
