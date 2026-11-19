[Français](ASYNC_FIELD_REFERENCE_RETURNS_CYCLE-fr.md)

<a id="retours-de-projections-de-champs-depuis-une-fonction-async"></a>

# Field projection returns from an async function

The synchronous helper relay → child async → synchronous return report open
below is since corrected in
[ASYNC_HELPER_RESULT_CONTRACTS_CYCLE.md](ASYNC_HELPER_RESULT_CONTRACTS_CYCLE.md).

Cycle of 7 November 2026. Existing rules: ST6–ST9/ST11–ST12/ST14,
B1/B2/B4a, AS8/AS12/AS13, MT3 and V5. No rules amended.

<a id="implémentation"></a>

## Implementation

The async contract now retains the path of the Int direct field or the
Int re-borrowed capacity. The paths consist through aliases,
Async functions, helpers and synchronous methods, branches and
The C makes the pointer real without moving the target.

After join, the verifier reconstructs field and target reservations
from the contract. The returned field remains protected, as well as its bearer
and its target; the disjunct fields become available again. Before waiting,
the capture continues to reserve all the argument required by the signature.
In an async parent, the loans of the result are also projected.

The Counter-Example `validation/open-async-field-reference-return.crust` is
Now accepted and displayed 21, 2, 3, 21. His former newspaper keeps the
refus historique ; `validation/async-field-reference-return-fixed.c` conserve
the new C. The diffs are `validation/async-field-returns-*.py.patch`.

<a id="preuves-exécutées"></a>

## Evidence

- `async-field-returns-initial-o0.log` : eight successful methods.
- `async-field-returns-final-o0.log` 12 methods, 12,542 seconds, OK.
- `async-field-returns-final-o2.log` 14 methods, 15.940 seconds, OK.
- `async-field-returns-complete-final-o0.log` 14 methods, 23 075 s, OK.
- `async-field-returns-regression-o2.log` : 34 return methods, links
  previous loans, 28.393 s, OK. This passage precedes the last
  addition of fixtures and correction of the lookup of nested fields.
- `async-field-returns-final-mutations-o2.log` : basic of 13 methods,
  21 C executions (two of which were rejected for injection), 50 programmes
  Checked invalids at both entries, i.e. 100 checks.
- Independent model: 24 combinations of all possible fields,
  Access, read/write and last use; 18 executions
  C and six refusals. The expected state is calculated by an independent dictionary.
- `async-field-returns-recapture-o2.log` : a successful additional method
  after the baseline; recapture of the result of join by another task,
  one execution and four programs refused to both entries.

Clang C11 pthread, fatal UBSan, O0/O2. The tests also cover pools
the carrier, their re-use after drop, the failures of launch, the branches
The normal profile
continues to refuse reset. No results or general evidence added.

<a id="mutations-et-limites"></a>

## Changes and limits

Five detected errors: loss of path in contract, loss of suffix
in a relay, loss of loan after await, undue reservation of the whole holder
after join, offset of the returned pointer. Detections include refusals
Undue and incorrect values, not just invalid memory access.

A mutation survived: replacing the target/capacity paths of the &mut field
by its only storage path. In the cases exercised, this path preserves
the carrier and its transitive dependencies; the four premature accesses
This finding does not establish the general equivalence of
the mutation and remains a limit of coverage. The runner thus ends with
a non-zero status, explicitly retained; no fictitious detection.

Expanded audit of this survivor: `async-field-returns-survivor-audit-o2.log`.
The 14 methods of the batch (22 C executions, 54 programmes rejected in two internships)
pass with the muted code, then the 24 cases of the model pass also
(18 executions, six refusals). The generic meter displays zero refusals for the
model because it imports its own verification entry; its six refusals
The audit confirms that the audit is not in conformity with the requirements of the Directive.
Redundancy within this perimeter, without establishing a universal equivalence.

The first campaign of mutations stopped on an ambiguous anchor of the
return pointer (two occurrences). The final anchor targets only the
The two newspapers are kept.

<a id="échecs-intermédiaires-et-écarts-ouverts"></a>

## Intermediate failures and open deviations

`async-field-returns-targeted-o2.log` keeps 15 errors: method fixture
poorly written, embedded initialization not supported, and processing regression
buildin push_new by the method solver. The latter no longer intercepts
constructions without synchronous contract. `async-field-returns-complete-o0.log`
Keeps 14 errors (some duplicated by importing a test class):
method fixture and lookup of nested fields. Resolution now uses
The model import no longer makes the duplicate class discover.

The test of interlocked projections initializes a complete object with its defects
then write his fields. The construction by literal substructure is not
- What? `validation/open-nested-structure-literal.crust` and diagnosis
keep this other gap for the next.

ST13 remains open in async: return the value of a shared field by untagging
the result of the holder. The minimum program is kept in
`validation/open-async-detached-field-return.crust`. Replacements of
field references, more general target types and other lots
of the objective remain open.

Another composition still refused: if the child async gets his own
a synchronous helper, then a synchronous caller returns the
The inference of abstracts has not yet been reached by the contracts of the
helpers available. Contra-example and diagnosis kept in
`validation/open-async-helper-result-sync-contract.crust` and his diary.
The direct case at hand is tested and accepted; this limit concerns the
additional relays by a synchronous contract.

The expanded native regression `validation/async-field-returns-native-o2.log`
is completed: 269 methods, 199.684 s, OK. It precedes the addition of
recapture and the synchronous relay patch below.

<a id="relais-synchrone-après-join"></a>

## Synchronous relays after join

An additional counter example is retained in
`validation/probe-sync-relay-async-field-return.crust`. A synchronous function
Launches the task, waits for his handle, then returns the field reference.
The first diagnosis (`un tableau de références Int exige des cibles Int`)
came from the erasure of the path in the symbolic summary of result.
`results.py` Now keep the projection in this summary.
the descent of capture during the reconstruction of the roads
of join: without it, a parent reference still alive appeared as
un emprunt concurrent, produisant `emprunt mutable non exclusif`.

The new test passes through two synchronous auxiliaries and distinguishes the field
The first is the "C" execution, which is the first to be carried out by the police.
21, 8, 21; four invalid programs are checked at both entries.
`async-field-returns-sync-relay-o0.log` : one method, 0.382 seconds, OK.
The regression and mutations of this supplement are preserved in
`async-field-returns-relay-regression-o2.log` and
`async-field-returns-relay-mutations-o2.log`.

Final results of this supplement: 42 methods, 37,343 seconds, OK to O2.
Baseline of mutations: 15 methods, 9,518 s, OK; 23 C and
58 invalid programmes monitored in both courses (116 checks).
Seven mutations detected, including the erasure of the path in the contract
synchronous and loss of join ancestry; previously surviving mutation
The target case is still surviving, and no overall detection rate is deducted.
The additional recapture test and the synchronous relay test were not included.
not in the 269 methods of the previous native campaign; selection
final of 42 methods and the final baseline cover them.
