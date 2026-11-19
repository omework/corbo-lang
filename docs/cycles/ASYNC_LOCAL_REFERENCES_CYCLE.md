[Français](ASYNC_LOCAL_REFERENCES_CYCLE-fr.md)

# Cycle — liaisons locales d’emprunts conditionnels async

<a id="règles-et-réalisation"></a>

## Rules and implementation

Application of B1/B2/B3/B4/B5, D1, AS8/AS9/AS11/AS12 and RT5/RT6.
AGENTS.md, VALIDATION_GUIDELINES.md and the index of the seven drafts were
B4/B5, REFERENCE_VALUES.md and async clauses remain normative.
This cycle does not change any language rules.

The Counter-Example `validation/open-async-local-reference-if.crust` is corrected.
A reference received by `let mut selected = if ...` can survive yield and
The two sources are retained in the contract.
recorded displays 30 and 20; his old diagnosis remains historical.

The compiler now retains the expressions of origin of the links,
with their lexical context, rather than recognizing only references
Directly derived from wawait or push_new. L-inference follows re-borrowing
explicit, branches, blocks and relays, and brings together possible targets.
A mutable mode is never obtained from a shared mode.

The async frame materializes selection in a typed pointer field.
translation of branches checks an identical mode and type, then gathers
It keeps the parents of the necessary reborrowings.
exiting an arm, intermediate names that disappear can be removed
of this set only because their underlying targets remain there.
Any local target that disappears is refused before the arm is cleaned.
No target allowance is moved or extended implicitly.

B4 does not generalize `let alias = reference`. The new path therefore excludes
Direct initialization by name; reborrowings use `&*r` ou `&mut *r`.
Final branch values, parameters and returns can always be
forward the reference by name, in accordance with the rules already adopted.
A negative test explicitly maintains the restriction on implicit aliases.

<a id="scénarios-et-indépendance-des-attentes"></a>

## Scenarios and independence of expectations

The final module `tests/test_async_local_references.py` has eleven methods,
23 normal native executions and 34 refusals expected by complete passage.
These accounts include the parameter variants; they do not mean
all language interactions are covered.

- Two branches, shared/mutable modes, interlocked blocks, local reborrowing,
  suspension and return; writing only in the selected target.
- Re-borrowing child mutable and then re-use the parent after last use;
  access to both targets and the parent refused before the target.
- Shared reborrowing of a mutable selection; no silent conversion
  or loss of original exclusive reservation.
- Branch with early return and branch providing local result.
- New Vector boxes<Int/u8> from push_new or d-await,
  then move on to a second task that returns it.
  The mutation of each vector remains refused as long as the result serves.
- Type, mode, annotation, let without writing right, branch without result and
  invalid local target refused. Scope control is also tested in
  a Void function: refusal does not depend on the inference of returns.
- Reborrowing from a block after missing his parent name: his two
  targets remain protected and then become accessible after use.
- Boxes of a fixed table in a loop with yield, continuous and break;
  final result [2, 1], competing access to the rejected boxes.
- Result received after join: drop and transfer of each source refused before
  its last use; after use, cleaning and re-use of the pool succeed.
- Independent model: selection of two integers by explicit indices 0/1
  and two seed prints 2097. A Python list determines the final values
  The contract, internal loans or C generated are not consulted.

The cleaning invariants of the previous cycle are re-executed, including the
destruction before join of an inactive child task owner of a capture.
Memory, structure and runtime reservations remain unchanged.

<a id="défauts-trouvés-pendant-le-cycle"></a>

## Defaults found during cycle

The first neighbouring passage had a mistake on the shared re-borrowing of a u8.
The new detection recognized this form but its evaluator was planned
For &Int, &mut Int and &mut u8. L-Admission has been corrected: &u8 keeps the
traitement existant. `async-local-references-neighbors-initial.log` conserve
The final regressions include the same test, now successful.

The examination of B4/REFERENCE_VALUES also led to the withdrawal of acceptance too
wide `let alias = reference` The scenarios
positive use explicit reborrowing and a negative test retains the
This is not a new normative decision.

<a id="preuves-exécutées"></a>

## Evidence

All the native helpers used here have been inspected: Clang C11, pthread,
-Wall/-Wextra/-Werrar, fatal UBSan. CRUST_TEST_OPT selects O0 or O2.

| Trace in validation/ | Observation |
| --- | --- |
| async-local-references-initial.log | 8 methods, 7,763 s, OK, initial development |
| async-local-references-neighbors-initial.log | 25 methods, one &u8 error, corrected then |
| async-local-references-O2.log | 33 methods, 28.625 s, OK after correction &u8 |
| async-local-references-final-O2.log | 10 methods, 8,681 s, OK after maintaining the B4 restriction |
| async-local-references-final-O0.log | Same 10 methods, 10.762 s, OK |
| async-local-references-drop-transfer.log | Eleventh method, two variants and eight refusals, 0.889 seconds, OK in O2 |
| async-local-references-drop-transfer-O0.log | Same supplement, 0.753 s, OK in O0 |
| async-local-references-abi-regression.log | 10 nearby methods, 17,301 s, OK: returned references, reference tables, control and cleaning |
| async-local-references-final-regression.log | 39 methods, 33.853 s, OK: async conditional returns, push_new and synchronous borrowed expressions |

The first ten methods and the complement together constitute the module
final test at both optimizations, when passing separately. `py_compile`
has succeeded. The diff of this cycle is retained in
`validation/async-local-references.patch` to make change inspectable.

## Mutations

Four temporary copies of the compiler, four detected errors:

| Faute | Detection |
| --- | --- |
| Keep one loan after selection | No access to an accepted alternative |
| Keep only one source in the contract | Change of a still borrowed vector accepted after async relay |
| Remove parents from re-borrowing | Access to the accepted target while the child out of the block remains used |
| Reverse selected pointers | Incorrect final values in native test |

Initial and final traces are in
`async-local-references-mutations.log` and
`async-local-references-final-mutations.log`. The four final detections
are statements of behaviour or refusal; none is credited on
a simple Python crash or compilation error without an analyzed diagnosis.
No overall detection rate is extrapolated.

<a id="limites-et-suite"></a>

## Limitations and follow-up

`validation/open-async-local-reference-match.crust` repeats the following lack:
receive the reference produced by a match on the result of waiting for a
The success must show 30 and then 20; the
current refusal of provenance is not normative. The match is already
possible in the synchronous compiler; its support in the async frame
and its inference of origin still to be extended.

This cycle does not add the expressions of borrowing to all syntax positions,
general references of aggregates, or the results of loops borrowed.
The remaining N/A obligations of the seven drafts remain, including scheduler,
threads, Select, mutex and implicit storage. The overall target is not achieved.

Reset remains removed from the prototype. The tests of this cycle do not claim to
new reset cover. ASan was not restarted after the start failure
d-a-c-d-a-c-d-a-c-d-a-c-d-d-a-c-d-d-a-c-d-d-a-c-d-d-a-d-d-d-a-d-d-d-a-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-
compiler, formal proof or general security guarantee is not claimed.

## Suivi

The borrowed match indicated above is corrected and validated in
[ASYNC_MATCH_REFERENCES_CYCLE.md](ASYNC_MATCH_REFERENCES_CYCLE.md). Ce cycle
also reveals and corrects the mutable double projection of a named Result.
