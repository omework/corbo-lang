[Français](ASYNC_ENUM_MATCH_CYCLE-fr.md)

<a id="match-denums-par-emprunt-dans-un-état-async"></a>

# Match of enums per loan in an async state

<a id="règles-et-périmètre"></a>

## Rules and scope

This lot applies P9, B1–B5, D1, ST13, the rules of projection and return of match,
AS8–AS15 and SL1. No new normative semantics are added.
remains reserved throughout the arm, even after the last use of a
projection. A reference that comes out of the arm retains its targets and the
necessary capabilities; an Int copied does not take these loans.

`validation/open-async-enum-match.crust` was refused to both entrances of the
compiler, while his synchronous counterpart was accepted.
Now the backend emits branches according to the discriminants of the pool,
keeps the necessary projections in the stable state and uses the
existing cleanings for suspension, return, break and continuous.

Shared and mutable matches are connected in instruction and expression,
with multiple arms, scalar results, Int references and allowances
A field A<Int> can be read by projection without
The names of the projections remain local to the arms.
A named alias of the wearer can pass through a suspension before the match.

<a id="corrections-et-invariants"></a>

## Corrections and invariants

- The async branches now manage more than two alternatives.
  merge the obligations of the continuous roads; the terminal paths
  do not bring value to the recipient.
- A reservation of the subject lasts until the arm exits. It is withdrawn
  by regular or anticipated outflows, without shortening the duration of loans
  who are coming out of the arm or caught by a childish task.
- Results contracts recognise paths `Variant.field` and
  &Int fields can make their target independently of the
  porter; &mut Int fields keep the reservation of its capacity.
- The follow-up of reservations distinguishes the path `.field` of a structure and
  `Variant.field` The old interpretation produced an invariant
  internal exclusivity instead of properly processing a mutable return.
- A shared result created from a mutable parent also keeps that parent
  The test contrasts a mutation before and after
  use of the result.
- Direct field enums have a suspension contract that can be used by
  Select. A loser keeps her bearer and targets until the drop of
  Select; its writing done before yield remains observable.

The effects review identified a separate limitation: changes in the
descendant possessed of an enum do not yet have a representation
The termination summary may be complete, but
the suspension summary must be explicitly incomplete when the graph
monitoring changes. A test inspects this status without classifying the program as
This limit is still an implementation work.

<a id="validation-ciblée-exécutée"></a>

## Targeted validation executed

Next `tests/test_async_enum_match.py` passed 17 methods to O0 in 16,579 seconds:
20 native executions, 16 invalid programmes and 32 refusal checks.
Journal : `validation/async-enum-match-complete-count-o0.log`.
Verify_program and compile_source share analyses; both refusals do
are not two independent evidence.

The programmes admitted cover three variants in a different order from the
declaration, suspensions in arms, calls and reborrowings, the result
the result shared after destruction of the
The main features of the project are:
early, break and continuous returns, a child task capturing a projection,
failure of parent launch, re-use of pools and cleaning of a
- You loser of Select.

Invalid programs cover completeness, fields and variants
incorrect, access to the carrier during the arm, access to the projection during
a re-borrowing still in use, premature drop and results towards targets
the caller before the caller has a
last use and then release it.

The small oracle of variants combines each manufacturer with its values with
its source result, regardless of the backend tags: three constructions
with different arm order and yield, followed by a re-use of the slot.
The subject is a uniquely destroyed trail.
finished, not a model of the whole system of types or all traces.

## Mutations

The final campaign increased its baseline from 17 methods to O2 in 16.855 s and
detects six errors by assertions: wrong tag, game reservation released
too early, poor path of mutable capacity, loss of projection of a
shared capture, read instead of mutable reborrowing, and publish a
Incomplete and complete suspension contract.
`validation/async-enum-match-complete-mutations-o2.log`, process completed
with code 0. Failures of mutated compilers are expected.

The intermediate campaigns of five and then six mutations are preserved in
`async-enum-match-mutations-o2.log` and `async-enum-match-final-mutations-o2.log`.
No extrapolation of the detection rate to the entire compiler is made.

<a id="régressions-et-anomalie-historique"></a>

## Regressions and historical anomaly

Synchronous regression passes 125 methods to O2 in 84,630 s, code 0:
`validation/async-enum-match-sync-regression-o2.log`. It includes matches
mutables, calls, returns, projection outputs, shared/mutable fields,
direct returns of loans and results owners.

The first regression async executes 170 methods in 174,516 s and meets
Failure: `test_deferred_writes_cannot_disappear_inside_sync_handle_helper`.
This failure is also reproduced on the snapshot prior to this batch.
In the previous work, the waiting contract had already been connected; the
The program is still not accepted because it is not a complete summary.
the test keeps this refusal.
and now requires exactly the origins of the field: old target if
The launch fails, new target if the child runs.
previous behaviour is in `async-enum-match-existing-effect-test.log`.
Expectations are not changed to mask a loss of effect.

The final async regression passed 173 methods to O2 in 164.353 s, with code 0:
`validation/async-enum-match-final-async-regression-o2.log`. It covers the
enums captured, buildin results matches, delayed effects, pools and results
of structures, Select, public handles and local graphs returned.
All final processes are complete. The lot is closed for this perimeter,
without closing the global construction site or the explicitly open compositions.

Executables use clang C11, pthread, O0/O2, warnings as
errors and fatal UBSan. No results new ASan/TSan nor formal proof
is claimed.

<a id="échecs-intermédiaires-et-limites"></a>

## Intermediate failures and limits

Initial snapshot fails on 16 assertions of the first nine methods
in 0.123 seconds (`async-enum-match-baseline.log`) Newspapers `first-o0` à
`fifth-o0` keep the deficiencies in the classification of catches, contracts of
champs, notation interne `match_yield`, Python range `replace` and way
reservation mutable. `sixth-o0` also contains two preparation errors
test: Bool display not connected in synchronous and reading an allocation
Int async without de-reference. Oracles now use a condition
Explicit Bool and `*next`The twelve methods go through `seventh-o0`.
The following additions cover children, launch failures, alias and parent
exclusive; their targeted newspapers remain available.

At the close of this game, the consuming match was not yet connected in async.
It is now treated by [the next lot](ASYNC_CONSUMING_ENUM_MATCH_CYCLE.md).
Minimum case
`validation/open-async-consuming-enum-match.crust` is refused both entrances,
while its synchronous duration is accepted; diagnostics in the file
`.log` This refusal is not a new language rule.
Reference entries in descendants are now processed in
[the suspension batch](ASYNC_ENUM_SUSPENSION_FIELDS_CYCLE.md). Replacements
the storage possessed and the general compositions of results still have to be completed.
This lot doesn't prove all the combinations
of functions, pools, catches, Select, recursion or aggregated types.

The global construction site remains active: consuming match, remaining async compositions,
mutex guards and audit of the seven drafts. The type and public signatures
The scheduler is explicitly left to arbitrate, in accordance with the user's decision.

<a id="reproduction-et-archives"></a>

## Reproduction and archives

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_enum_match -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_async_enum_match_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_enum_match test_async_owned_enums test_async_match_references test_async_structure_effects test_async_borrowed_struct_pools test_async_borrowed_local_results test_select_source test_select_results test_async_owned_struct_returns test_public_structure_handles test_async_local_owned_result_graphs -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_mutable_match test_mutable_match_calls test_mutable_match_function_return test_mutable_match_escape test_reference_fields test_mutable_reference_fields test_direct_borrow_returns test_owned_results -v
```

The five implementation diffs are archived in
`validation/async-enum-match-*.py.patch`, since
`/tmp/crust-before-async-enum-match/`. New tests, historical test
The report is updated with the minimum programmes and the newspapers.
