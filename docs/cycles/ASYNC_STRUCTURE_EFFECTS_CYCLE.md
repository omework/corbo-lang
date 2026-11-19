[Français](ASYNC_STRUCTURE_EFFECTS_CYCLE-fr.md)

<a id="contrats-différés-de-remplacement-des-champs-références"></a>

# Delayed contracts for replacement of reference fields

<a id="périmètre-de-cette-étape"></a>

## Perimeter of this step

Update: The results of the expected children are now being used
in conjunction with the effects, in
[the cycle of termination contracts](ASYNC_COMPLETION_RESULTS_CYCLE.md).
The following limits describe the state at the end of this cycle.

No amended normative rules. ST10, ST8/ST12/ST13, B4 and AS2/AS12/AS13
require that new targets of a borrowed carrier be followed, including after
wait for a task. This step implements **Inference of Effects**, not
The appellant's refusal to accept the application of the
Async calls for changes in these dependencies remain in place.
is not finished.

The compiler produces `async_structure_effects` before the condition is lowered.
Each entry distinguishes a contract calculated, possibly empty, from a contract
not resolved (`structure_fields=None`, with diagnosis). An unknown case cannot be
The summary also indicates whether the body is not a proof of no mutation.
has a normal path of termination; he does not affirm that this path will be
taken into account in the execution.

The module `async_structure_effects.py` reuse symbolic field calculation
The synchronous auditor's auxiliary synchronous data shall be represented by the following:
The replacement instinculates the origins of the
The common application of the contract has been
was extracted in `ResultContext.apply_structure_updates`, without change of
synchronous semantics.

The creation of a child retains its arguments; it does not apply its
The waiting applies the child's termination contract.
destruction of an inactive task does not apply anything. An expected execution launched
the state after execution with the initial state possible in case of refusal of
launch. A child diverges does not make continuation; refusal to
son lancement peut en revanche rendre la main. Les branches, retours,
reborrowings of porters, renames and loops use existing junctions.
Delayed catches have their own symbolic field, distinct from identities
storage of structures.

Unsolved contracts include recursive effects, aggregates excluding
Int/&Int/&mut Int, the origins of child-supplied results and the
The latter case is the case.
is explicitly detected: the current contract of the auxiliary cannot make
to disappear the still delayed writings.

<a id="contre-exemples-et-frontières"></a>

## Counter-examples and boundaries

The programme retained in `validation/open-async-sync-field-replacement.crust`
had an implicit writing `view.data = next`. Body verification
synchronous requires explicit re-borrowing `view.data = &*next`. The original is
stored under suffix `-original.crust`, and previous diagnoses remain
The corrected version has the expected contract: the field `.data`
the first parameter targets the second parameter.

In a temporary copy only, removing the refusal async allows
`verify_program` accept the corrected case, but `compile_source` refuse encore
The bridge transmits a pointer to the Int, while the bridge transmits a pointer to the Int.
the reference field stores a `Cell *`. Journal :
`validation/async-structure-effects-next-boundary.log`. It is neither a
program execution or validation of the removal of control.
The temporary control has been removed and the control remains in active sources.

A supplement revealed an error in the new analysis: after a choice
between two functions async, the public type `runtime::Handle<Int>` is not
a key to the function table. The old reading by this name produces a
KeyError, reproduced in a temporary copy in
`validation/async-structure-effects-choice-counterexample.log`. Signatures
have been gathered since the delayed capture of the concrete functions.
The choice retains the two new targets and the old target possible at
failure of launch. No user refusal replaces this patch.

The necessary steps remain: sustainable representation of the target through
bridge, tracking of fields in suspended state, task-related effects and
handles, then application at the appellant after waiting and following loans,
The results tables and public contracts
must retain the same effects before lifting the refusal.

<a id="validation-exécutée"></a>

## Validation executed

`tests/test_async_structure_effects.py` covers 17 methods: 16 of
The new programmes include the following:
Async entries are not presented as executable.
synchronous auxiliaries are normally checked before the target analysis.

- The independent model lists 125 scenarios: one initial action and two
  branches of no writing, target a, target b, expected child and child
  destroyed inactive. A concrete "old/a/b" state calculates the expected targets,
  without using contracts or generator C.
- Other tests cover two exchanged fields, detached origins, fields
  mutable, masked aliases, three levels of waiting, parameter permutations,
  choice of tasks by if/loop, early exits, loops and divergence.
  A supplement checks the convergence of a loop of expected children who
  exchange two fields; a concrete model of period two provides the targets
  can be done independently of symbolic analysis.
- Unresolved cases must produce an explicit incomplete status.
  the full program verifies that the contract is calculated and that both
  entries retain the backend's refusal.

First pass: fixture error due to implicit reborrowing, without test run.
Pass 2: eleven successful methods and an assertion of incorrect origin;
ST13 exige ici `detached_field_parameter`, not a reservation from the porter.
The expected targets and paths have not been changed. The following passes
pass twelve, then fourteen, then fifteen methods.
`validation/async-structure-effects-{initial,recheck,contracts,expanded,final,complete}.log`.
The final grouping of sixteen methods is retained in
`validation/async-structure-effects-loop-final.log`.
Synchronous complement executes replacement, destroys the old target and
displays twice 9; destroy new target before reading is refused
The 17 methods then go together to O0 (0.543 s)
and O2 (0,749 s), in `validation/async-structure-effects-final-o{0,2}.log`.
Each passage includes a C execution of this neighbour under fatal UBSan; the
tests of the new contract remain static analyses, independent of the
niveau d'optimisation C.
After the addition of choices between distinct functions, the seventeen methods
go back to O0 (0.597 s) and O2 (0.453 s), in
`validation/async-structure-effects-choice-final-o{0,2}.log`.

Field/handl regression succeeded 85 methods at O2 in 79,808 s, with Clang,
C11, pthread and fatal UBSan in the native harness. It precedes the last
incomplete status supplements, covered by the final targeted pass and the
This is a large native regression followed separately.
The first synchronous selection finishes 56 successful methods and an error of
loading: name `test_structure_field_updates` There's no such thing as a newspaper.
is not presented as green; the corrected selection is recorded separately.
She succeeded 56 methods in 26,157 s in
`validation/async-structure-effects-sync-final.log`With UBSan fatal.
synchronous history does not add explicit optimization option; this passage
is not labelled O2.
The extended native selection succeeded 312 methods at O2 in 233.060 s in
`validation/async-structure-effects-native-o2.log`It covers the integration of
the inference in the compiler and precedes the last corrective of the choice of
specific functions, covered by the following targeted passages.
The number of the units is not added as a single cover.
Seventeen methods of public contracts for hands pass after this corrective
at O2 in 16.072 s: `validation/async-structure-effects-public-regression-o2.log`.
The last seven mutations campaign also follows this corrective:
`validation/async-structure-effects-mutations-complete.log`.

## Mutations

`tests/run_async_structure_effect_mutations.py` changes temporary copies.
The initial campaign detects six errors; the final campaign detects seven:
forgotten child writings, forgotten launch failure, continuation after
Invented divergence, unknown transformed into empty contract, lost catches
of choice, synchronous effects ignored, loss of effects at the border of a
The contract assertions detect these errors; this does not mean that the contract is not a good one.
are not seven memory violations demonstrated at execution.
`validation/async-structure-effects-mutations*.log`.

## Limites

The calculation re-uses the auditor's junctions: it does not constitute a
The second independent auditor. Only the small oracle of 125 scenarios calculates
There is no formal evidence, no new evidence, no new evidence, no
A. A complete inference does not replace the
verification of borrowings, types, waiting obligations or backends.

Snapshot : `/tmp/crust-before-async-structure-effects`. Differences and differences
new modules are kept in `validation/async-structure-effects-*.patch`.
