[Français](SET_EXPRESSIONS_CYCLE-fr.md)

<a id="expressions-calculées-dans-intset"></a>

# Expressions calculated in Int.set

<a id="périmètre"></a>

## Perimeter

V4 and B4a describe the mutation of Int content, without replacing its
allocation, with assessment of the new value before writing.
completes the synchronous connection of `nombre.set(expression)` for
Int expressions already supported. The mention of the literal in V4 describes
the initial prototype; no new conversion or transfer of collection
is not introduced. The user methods named set remain resolved
selon leurs propres signatures.

The result of the expression is calculated once. The target is then
reverified: a name or C address saved before calculation does not prove
not that the value is always alive. Writings via readonly reference,
The analysis of the
effects, results and constraints also go through the expression, including
calls, forward returns and resets from the historical profile.

The general course of the match arms manages the scriptures calculated on their
The historical path of the literals is preserved. The backend async
already had calculated writings; an async call to an auxiliary
synchronous using set is included in the tests.

<a id="preuves-ciblées"></a>

## Targeted evidence

The first eight methods of `tests/test_set_expressions.py` go to O2 (4,128 seconds,
`validation/set-expressions-complete-o2.log`) and O0 (3.884 s,
`validation/set-expressions-complete-o0.log`) C11 with Clang,
pthread, fatal warnings and fatal UBSan.
A ninth test checks that an anticipated return in the new value jumps
the writing and keeping the previous content. The final pass of the nine methods
, was in O2 in 4,948 s (`…-final-o2.log`) and O0 in 4,938 seconds (`…-final-o0.log`).

Programs test left-right order of two calls, identity
address before/after writing and after re-use of the slot, destruction
unique with the last value, local scalar, mutable references,
boxes of tables, match projections and user methods. Neighbors
invalids are checked by verify_program and compile_source : read
future borrowing, writing readily, destruction/transfer/reset of the
target during calculation, bad type and bad inarity.

An auxiliary performs a reset in the new value; two relays retain
The program is allowed if the allowances allocated to the appellant are
have finished using, and refused if a reading still has to follow.
The reset remains exclusively historical and explicitly activated.

The independent model uses Python integers to calculate three suites
It compares the 36 observations of 12 mutations (seeds 72, 190 and 602).
native outputs without reading compiler decisions.

Three errors are detected in temporary copies, journal
`validation/set-expressions-mutations-o2.log` : removal of control
of writing, deletion of the calculation of the new value, omission of the effects
The latter results in an internal invariant
"reset absent from the function summary" on the valid program; it does not
is not evidence that a dangerous program has been implemented.

<a id="régression-et-limites"></a>

## Regression and limitations

The extended regression is recorded in
`validation/set-expressions-regression-o2.log` : 150 methods, three failures
of assertions and twelve errors divided into six historical methods.
These six methods reproduce exactly these failures with the compiler
prior to the batch (`validation/set-expressions-before-change-failures.log`).
They replaced an allowance without using its old value; U1
The programs now include
a controlled reading of this initial value. Original assertions
The following are retained: exit, destruction, order of C, exceedance and diagnosis.
The initial log is not deleted. A first selection script had
duplicated method names; its loading error is kept
separately in `…-before-change-loader-error.log`.
The second pass of 150 methods (`…-regression-fixtures-fixed-o2.log`)
succeeds except for a waiting diagnosis: the negative test of displacement
did not use the new receiver either. It is now read before
voluntarily invalid access to the displaced name. The assertion "more usable"
is retained. The modified modules are replayed in
`validation/set-expressions-reassignment-final-o2.log`.
These 41 methods go in 13.910 seconds. There is no third execution
The overall 150 methods after this last fixture correction; the
149 other methods had succeeded in the previous pass.

No new ASan/TSan, second compiler C, no formal evidence.
exercise finite compositions; they do not prove all interactions.
The diffs are kept in `validation/set-expressions-*.py.patch`.
The set of calculated writings is complete for this tested perimeter.

Extension of the async parameters of handle remains pending arbitration
Documented in ASYNC_HANDLE_CAPTURE_DECISION.md. The rest of the overall objective
remains active, without amendment of the AS14/RT6/RT7 rules before reply.
