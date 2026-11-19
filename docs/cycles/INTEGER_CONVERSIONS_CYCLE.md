[Français](INTEGER_CONVERSIONS_CYCLE-fr.md)

<a id="conversions-entières--intégration-du-brouillon-07"></a>

# Whole conversions — integration of draft 07

<a id="règles-et-portée"></a>

## Rules and scope

F5 and I5 record the validated decision: `as` preserves all values of
type source; a conversion that could fail is via `try_from`.
The first stage has implemented `as` for current whole types
Supported, Int32 (`Int`) and `u8`, ainsi que l’initialisation explicitement
typed by a literal `u8`. The second step below adds `u8::try_from`
and control of use of inline bankrupt results supported.

The control is based on the intervals of the types, without exception for a
The synchronous C evaluates the operand once in a temporary type
destination. The async path applies the same control and retains the value
in her condition when she passes through a suspension.
of constraints and effects go through the operand to maintain its uses and
A cast does not implicitly dereference an allowance.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_integer_conversions.py` adds five methods.
are compiled and executed at O0 and then O2 with C11, UBSan and
`-fno-sanitize-recover=all`The five methods are divided into two levels:
`/tmp/crust-integer-casts.log`.

- An independent Python list gives 256 expected values for all
  the values of u8 extended to Int. The two extremes Int32 remain unchanged.
  Identity conversions, priority over multiplication and
  The initialisation of typed literals is exercised.
- Two calls produce observable effects in order 1 then 2, one
  The pool is then cleaned.
- Converted reading can survive the drop in the original allowance and
  to the re-use of its slot. Convert from a loan still used
  after drop or reset is refused. Converting a variable already dropped is
  Reset is only exercised in the historical profile.
- A task captures a u8, creates another u8, suspends its execution and then renders
  The extended sum 297. The capture and result go through spawn/join.

After reinforcing negative cases, 15 programmes are covered:
11 invalid forms of conversion/initialization, three uses after
destruction and a reduction conversion to async. The test of eleven forms
was replayed separately: `/tmp/crust-integer-casts-refusals.log`.

## Mutations

Two temporary mutations are detected:

1. Remove the check d'inclusion of intervals makes accept three
   Int to u8 conversions prohibited, including constants 0 and 42.
   Negative programs use the result as u8 before expanding
   to display, so that an independent refusal of print does not mask the
   default. `/tmp/crust-integer-narrowing-mutation-final.log`.
2. Passing through int8_t in generated C corrupts 128, first
   The difference with the independent enumeration of 256 values.
   `/tmp/crust-integer-casts-mutations.log`.

Copies temporaires :
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-cast-mutations.be40pzxx`.
These two targeted mutants do not give any general detection rates.

<a id="régression-et-limites"></a>

## Regression and limitations

The arithmetic regressions, short circuit, comparisons, bytes async,
arguments, fixed tables and mutability end with **129 successful tests**
in 62.011 seconds. `/tmp/crust-integer-casts-regression.log`.
The Python compilation of the six modified modules also succeeds.

A first scenario of order used `.set` with arithmetical expression,
form not supported by this existing API. It has been replaced by two
separate calls writing constants; order and uniqueness of effects
remain observable, without extending this API in the conversion site.

The evidence relates to Int and u8.
The model of the types of integers is simple and
shared between compilation paths; the oracle of expected values
No general proof of security is claimed.

<a id="deuxième-étape--try_from-usage-explicite-et-drop-dexpression"></a>

## Step two — try_from, explicit use and drop expression

`u8::try_from(value)` evaluates once an Int or u8 and renders
`Result<u8,IntegerConversionError>`. The variant of the prototype error is
`IntegerConversionError::OutOfRange`. The check precedes cast C; none
pool allocation n
This guy and the backend async can capture him, keep him for yield,
Return it by wait and carry it in the result of join.

U1/L6 integrates the decision of draft 07. A failed result link
inline must be used, even for a statically established variant.
`_` does not allow for circumvention of this rule. A conditional use is sufficient.
Reassignment alone does not count as the use of the old value.
`drop(-> expression)` lowers the evaluation in an internal link and then
consumes this result before the next instruction. The same form applies
ownership operations already supported; their full coverage
according to draft 01 still to be completed.

A counter example revealed a dispatch error: an arm `Err(_)` written
avant `Ok` compared the status to code 5 only.
could reach the Ok arm and trigger an invalid extraction.
generic discriminant now normalizes any non-zero status like Err,
in synchronous and async; precise error patterns keep their discriminant.

<a id="preuves-ciblées"></a>

### Targeted evidence

The 11 methods of `test_integer_conversions.py` go to O0 and O2 under
UBSan bloquant. Journal `/tmp/crust-try-from-final-tests.log`.

- An independent Python oracle ranks 260 entries from -2 to 257 and both
  Int32 extremes. Two functions relay the Result; Err(_) figure avant Ok.
  Variations named error are also exercised.
- Evaluations of two expressions consumed per drop have effects
  Observable only once, before the following instructions.
  named can be consumed and its second drop is refused.
- The result does not keep any borrowing of the entire copied: it remains usable
  after drop, re-use or historical reset of the original pool. Conversion
  since a loan became invalid is refused.
- Conditional use and transmission to a function are permitted.
  Thirteen negative forms cover abandonment, `_`, the name `_unused`, double the
  consumption, absence of arrow, incorrect types/criteria, crushing
  d) an unused result and two existing UTF-8 families.
- The path async suspends before and after the return of the Result. The join of a
  other task makes the Result complete, unpacked by two successive matches.
  Unused async bond, first value crushed without use and one
  return after drop are refused.
- The drop of a UTF-8 validation result ends its borrowing; the table
  d-bytes may then be modified.

Three temporary mutants are detected at O2: removal of the terminals,
removal of the control of use (six refusals become accepted), and return
Gross error code instead of Err(_). Journaux
`/tmp/crust-try-from-mutations.log`, copies in
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-try-from-mutations.z0aouxqx`.

<a id="migration-des-tests-existants"></a>

### Migration of existing tests

The first regression of 155 tests completed with three methods concerned
by the new usage rule (three errors and two sub-case failures),
journal `/tmp/crust-fallible-results-regression.log`. Programmes which
crush or abandon a Result received a game without exit or drop
Explicitly. Incorrect type tests now consume the result
previous so that its abandonment does not mask the error of the type targeted.
The expected values, traces and memory invariants were not changed.
The three methods migrated pass, newspapers
`/tmp/crust-fallible-migrated-tests.log` and `/tmp/crust-fallible-bytes-migrated.log`.

The second 155 test regression ended in 183.441 seconds with an error:
the scenario named char_at was still crushing its first Result without use.
An explicit match before the crash retains the object of the test; this method
Replayed passes in 2,214 seconds (`/tmp/crust-fallible-char-migrated.log`).
The global newspaper keeps failing: `/tmp/crust-fallible-results-final-regression.log`.
It is therefore not an overall green execution.

Another counter-example was the one-time priority: `-byte as Int` was
interpreted as `-(byte as Int)`. The unaire operator now binds its operand
avant `as` ; u8 denial is refused, and `-(byte as Int)` both are allowed.
Targeted methods go to O0 and O2 (`/tmp/crust-integer-cast-precedence.log`).

<a id="résultat-propriétaire-consommé-par-drop"></a>

### Owner result consumed by drop

The example of draft 01 with `drop(-> valeurs.replace(index, -> entrant))`
is also connected to the existing owner result of replacing.
executes, valid index then invalid, check that the returned slot contains
respectivement l’ancien objet et l’entrant rejeté. L’allocation suivante dans
the capacity pool two reuses exactly this slot; the vector preserves
The first two destructions are compared to the second, respectively,
The third program consumes directly `pool.new(7)`
then reuse the capacity pool one.

These three programs go to O0 and O2 under UBSan blocker, journal
`/tmp/crust-drop-expression-owned-tests.log`. The test also revealed a defect
generated C: the internal name of the temporary receiver contained a character
NUL in the cleaning label. The logical name remains internal; label
C now uses `drop-result`, and the absence of NUL is verified.

This connection does not yet cover all proprietary operations,
in particular the direct drop of pop result, or the prohibition of all
motifs consommateurs `_` covered by draft 01.

<a id="limites-de-cette-étape"></a>

### Limitations of this stage

The use check covers the inline results reported in the
prototype; proprietary families, consumer patterns and all
join course still to be fully confronted with draft 01.
The case law of the Court of Justice of the European Communities
The following are the main features of the system:
The public border of running, Select and mutex errors is
the remaining async lot. The bankrupt UTF-8 cuts still have to be added.

The subsequent regression of the UTF8_TRY_SLICE_CYCLE.md cycle includes the twelve
conversion methods, migration UTF-8/async scenarios and arithmetic:
124 methods pass (`/tmp/crust-try-slice-regression.log`) This perimeter is
It does not replace a full performance of all tests.
