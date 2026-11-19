[Français](REFERENCE_EXPRESSIONS_CYCLE-fr.md)

<a id="cycle--emprunts-produits-par-if-et-match"></a>

# Cycle — loans produced by if and match

<a id="règles-et-changement"></a>

## Rules and change

This cycle applies B1/B2/B3, B4a, B5 and D1 without changing the normative rules.
AGENTS.md, VALIDATION_GUIDELINES.md, the index of the seven drafts and the clauses
on the borrowings and borders of the telescopes have been read.
The following are the main features of the existing integrated normative framework:
borrowed result does not require an arrow and does not promote its target.

The case `validation/open-join-element-match-expression.crust`, refused to cycle
previous, is now executed. The result of `join` can provide a box
in the Ok arm and a rescue loan in Err; synchronous function can
return the result of this expression match. Both paths show 255,
including with EAGAIN injected at blocker launch. The previous log remains
a historical trace of the defect.

The analysis of the results accepts the borrowing methods and gathers their sources
without losing the indication of a pointer to an inline box.
conditional expressions keep separately the targets, paths of
The same type of information is required from each branch.
and the same mode. Branches that return directly from the function do not
provide no result to continuation.

An Int allocated in pool is represented by a Cell*, while a table box
or vector uses an inte*. If a selection mixes these representations,
C receives a pointer to the value of each branch.
The traditional way of moving towards structures is to retain their existing representation.
child checks → parent perform before arm cleaning; they
refuse local targets without implicit promotion. Runtime is not changed.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

`tests/test_reference_expressions.py` has 14 methods: 30
It does not take into account the fact that there is no legal basis for the application of the principle of equal treatment.
not all of them are distinct programs: some parameters and variants
repeat the same invariant.

- Shared or mutable selection between two pool Ints; two branches
  executed, old values observed, writings directed to the right target.
- Mixing table/pool box, in both arm orders and
  with both decisions; the other values remain intact.
- New Int/u8 boxes from two pools, last use, drop and
  re-use after use; premature destruction of each refused source.
- Join then return by contract, on success and refusal of launch; a
  branch marker and lengths show that only one arm is running.
- Local connections, reborrowing, loops with continuous and break, and
  conditional sub-expressions with early return.
- Structure references, and mutable projection of an enum through if:
  the holder remains reserved until the last use, then becomes accessible again.
- Condition with observable effect: one call, before the chosen arm.
- Independent model of selection from three values, seed 1771,
  five draws; target selected and all final values compared.
  Each of the three possible sources remains protected against drop before use.
- Refusal of local pool/table/vector targets to one arm, mode or
  types of incompatible and access that violate a loan still in use.
- Public reset refused. Two additional checks in the profile
  historique `allow_legacy_reset=True` keep the refusal of early reset;
  they do not reintroduce this API into the current prototype.

Expectations are calculated from program values, identities, and
The model is selected in a logical manner, regardless of the contracts and the C issued.
The model remains finished and does not prove all combinations of paths.

<a id="défauts-et-préparation-des-tests"></a>

## Failures and preparation of tests

The initial refusal existed in the analysis of the results and then in the selection
C: both n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-n-N-n-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N-N
keeps the existing provenances and life checks.
for box borrowings now also applies to
If arms and buildin matches, before destruction of their premises.

The first scenarios used a synchronous Bool parameter, still refused
by the prototype, and a calculated argument of `.set()` in a function
The tests in this cycle use selectors
In comparison with 1 and `*n = *n + 1`, without changing their selection expectations or
The two initial limitations are not corrected by this lot; the
initial logs remain available. Refusals of invalid programs of the first
passage are not counted as proof of their invariants since Bool
At that time, it was not possible to achieve these verifications.

<a id="exécutions-et-régression-historique"></a>

## Performance and historical regression

- `validation/reference-expressions-O0.log` 14 methods, 26,128 s, OK;
  native tests of the new module under Clang C11, `-O0`, UBSan fatal.
- `validation/reference-expressions-async.log` 29 neighbouring methods, 59,656 s,
  OK (push_new async and buildin error values).
- `validation/reference-expressions-legacy-UBSan.log` : 13 borrowing methods
  Of carriers, 4,565 s, OK with `CRUST_SANITIZE=undefined`.
- First regression: `validation/reference-expressions-O2-regression.log`,
  158 methods, 166.441 s, 18 errors in three historical methods.
  The historical helper does not use `CRUST_TEST_OPT` : this passage was not
  The new module was tested.

Historical errors were proprietary connections `outer`, `temp`,
`old` and the first value of `data`, without reading, borrowing or consumption
This is contrary to U1 reinforced by draft 01.
A temporary copy of the compiler **avant** this cycle, with its former
`crust.py` and `results.py`reproduces the 18 errors of the three methods in
0,061 s : `validation/reference-expressions-baseline-legacy.log`.

The fixings received `print` before exit, reset or replacement;
the expected outputs contain these readings.
The U1 rule remains unchanged and the test remains unchanged.
The corrected module executes the release of a non-use receiver.
24 methods in 40.275 s, OK under historical UBSan:
`validation/reference-expressions-legacy-updated.log`.

Final regression `validation/reference-expressions-regression-final.log`
Runs the same eight modules: 158 methods, 188.023 s, OK. Command:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_reference_expressions test_if_expressions test_conditionals test_conditional_returns test_direct_borrow_returns test_mutable_borrow_returns test_mutable_match_escape test_mutable_match_function_return -v
```

UBSan is active for both helpers in this passage. The new helper uses
O2; the historical synchronous helper keeps the default C compiler optimization.
The 18 initial errors are therefore not hidden by a change of rule or
exclusion of regression methods.

## Mutations

The compiler's temporary copies receive four controlled errors:

| Mutation | Observation |
| --- | --- |
| Reversed condition | Bad target/observed value detected by native test |
| A case from which no reference has been made | Prohibited transfer of accepted b, assertion of refusal in failure |
| Zero pointer for a pool/table branch | Native execution refused by UBSan, assertion of success failed |
| Erased porter ascendance | Valid program rejected by internal compiler exclusivity invariant |

The fourth case was initially classified as inconclusive by the script, which
Only recognized the FAIL lines of unitittest. L-inspection established that
the positive test failed by `crust.Error: internal invariant: mutable borrowing
The script now recognizes this result.
This is a specific transfer and a new targeted execution reproduces it.
Both traces are preserved: `validation/reference-expressions-mutations.log`
and `validation/reference-expressions-writer-mutation.log`. The latter is
an internal guard detection, not proof that the exit oracle would have
identified as a missing ancestry.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The same shape in the suspension body remains open:
`validation/open-async-reference-if-expression.crust` receives two loans
mutables durables mais refuse encore `return if ...`. The expected output is
30 and 20; his diagnosis is recorded.
This lot extends the synchronous compiler expressions,
including calls and results of tasks that it manages; it does not extend yet
the lowering of conditional returns from borrowings in an async setting.

ASan was not restarted: the previous cycle reproduced a start time
even for an empty executable C under ASan. No hits ASan, TSan, second
Compiler or formal evidence is not claimed.
between conditional destruction and selection of a loan remain outside the
The other open bonds of the seven drafts,
In particular, scheduler, threads, Select, mutex and implicit storage remain.

## Suivi

The cycle [ASYNC_REFERENCE_RETURNS_CYCLE.md](ASYNC_REFERENCE_RETURNS_CYCLE.md)
corrects since the conditional return async quoted above. Local link
d) Such a result remains a separate counter example, as reproduced in this report.
