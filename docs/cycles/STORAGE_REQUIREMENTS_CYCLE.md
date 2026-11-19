[Français](STORAGE_REQUIREMENTS_CYCLE-fr.md)

<a id="exigences-de-stockage-déduites-des-types-et-conservées-dans-les-contrats"></a>

# Storage requirements deducted from types and retained in contracts

<a id="problème-et-règles"></a>

## Problem and rules

This lot applies the distinct types T and A<T>, copies ST17/ST18, T1/T6,
the contract of office, L7 and AS9/AS12, and drafts 03/05/07.
It does not change any normative rules.

`validation/open-async-local-only-copy-annotation.crust` is now accepted
by both steps and displays 7. `leaf(p:&Point)` contient
`let q:Point=duplicate(p)`. This annotation requires that the copy be local,
and therefore the source of the parameter of this operation is local.
call with pool value does not meet this requirement and remains refused.
The annotation is not deleted to make the program compileable.

Inversement, `let q:A<Point>=duplicate(p)` Is imposing a pool provenance.
conflicting requirements on the same source are refused.
from written operations and types; they do not convert or
move an allowance to another source.

<a id="implémentation"></a>

## Implementation

`storage_requirements.py` reuse the flow of assemblies of the stress module,
with observation points for annotations, explicit A<T> returns
and calls. An obligation on a root parameter becomes an input
`(index, local|pool)` The sources already known are controlled
The possible sources of a result are all examined.

Obligations are spread until stabilization between functions
Asynchronous, task factories and async functions. Each call consults the
The body of the caller is not reanalyzed at the call site.
The synchronous contracts publish these obligations in
`FunctionContract.storage_requirements`; the statements async keep them
in the corresponding field. Symbolic bodies are checked with the
requirements derived from their parameters, instead of assuming a pool source.

The ordinary async representation now uses the minimum parameters
The other compatible features may be:
select the static variants of the previous batch. All calls,
including those without local parameters, check the requirements before selection.
Variations retain a single nominal pool of states.

Requirements analysis is enabled for bodies containing annotation
or a call that already carries an obligation, and then spreads to the point
This avoids imposing a second incomplete validation on expressions
The regular auditor remains systematic.
The additional stream crosses await and Select, keeping the sources
The results are not replaced by life-span analysis, by the
réservation ou de nettoyage de ces opérations.

A synchronous placement correction was also needed: a return
calculated explicitly marked (`return <-duplicate(a)`) in a branch may
receive a local storage reservation directly. The plan is not limited to
more to `return <-nom`. Both copy branches are performed in the tests.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_storage_requirements.py` contains ten methods.
O0 succeeds in 4,894 s, with **12 native executions** and **9 programmes invalides**
refused to attend both stages (**18 checks**) The final O2 baseline of mutations
The C performances use Clang C11, pthread,
Wall/Wextra/Werrar, Wno-unused-function and fatal UBSan.

- The program recorded, with inspection of his async contract.
- Local call allowed and pool call refused for an annotation T; reverse
  for an A<T> annotation.
- Obligation from a synchronous helper and then relayed by two tasks.
- Two levels of synchronous mills, with contract verification and
  refusal of the same appeal on an incompatible source.
- Two possible sources of copying: both parameters must be local;
  the branches true/false are exercised with an Int discriminant.
- Contrary requirements refused.
- Capture followed by waiting then drop allowed; drop before waiting refused.
- Model independent of the four local/pool combinations on two parameters:
  four executions admitted and four neighbours whose first source is
  The expected obligations are written since then.
  This model, not calculated by the compiler.
- Annotated copy combined with Select, yield, await and conversion from u8 to Int.

The final newspapers are `validation/storage-requirements-counted-o0.log` and
`validation/storage-requirements-mutations-final-o2.log`.

The regression of **108 methods** succeeds in 54,934 s in
`regression-corrected-o2.log`. The expanded async selection of **97 methods**
succeeds in 78,094 s in `async-regression-final-o2.log`. Ces deux passages
before the last addition to the Select flow of the requirements analysis.
A selection of **46 methods** then passes in 44,558 seconds on the final code:
targeted tests, Select source and select results, in
`selection-final-o2.log`All these newspapers have the prefix
`validation/storage-requirements-`. The first 22 targeted tests/interactions
have also passed in `targeted-third-o0.log`.

`py_compile` succeeds. The diffs of the five modules are archived in
`validation/storage-requirements-*.py.patch`, compared to snapshot
`/tmp/crust-before-storage-requirements/`; the new module is an addition.
All the processes cited are completed and their results recovered.

<a id="mutations-et-chronologie"></a>

## Changes and chronology

The six errors of `tests/run_storage_requirement_mutations.py` are detected:
omission of an annotation, loss of propagation by call, stop after a single
the obligation to publish in the synchronous contract, retention
the only possible first source, and forgets local storage in the
symbolic entries. Several detections are refusals of valid programs;
Others find an incomplete contract. They are not memory corruptions
and this finished campaign is not a comprehensive coverage measure.

Initial failures remain:

- `regression-initial-o0.log` : eight claims of diagnosis failed,
  although invalid programs are refused; diagnostics specify
  now the local T/A<T> award, without weakening the tests.
- `suite-initial-o0.log` : missing propagation through await, and fixture
  using Bool in a synchronous signature that awaits another notation.
  The fixture now uses an Int discriminant with both branches.
- `suite-second-o0.log` : the auditor accepted both sources,
  but the backend refused to return a local copy calculated; placement corrected.
- `regression-o2.log` : three errors and one failure due to unknown values
  crossing await in the additional pass; the results owners
  simple and nested are now preserved.
- `async-regression-o2.log` : three failures to type expressions without obligation
  The use of the additional pass is too wide.
  The trigger is limited to the relevant dependencies, and the Select flow
  is covered when a storage annotation is actually present.

The intermediate newspapers and the two transfer campaigns remain available.

<a id="limites-et-prochain-travail"></a>

## Limitations and Next Work

The newspaper `validation/storage-requirements-remaining.log` confirms closure
Two valid programs remain unanswered:

- `open-async-fresh-local-result-destination.crust` : a task creates a new one
  local copy, then return it. You have to inject an outside destination
  in its condition, rather than closing the storage containing the result.
- `open-async-return-replaced-owned-field.crust` : return of a graph after
  replacement of a proprietary field; its sources must be updated.

The obligations of this lot relate to the root parameters of the structures
Supported. A requirement for a non-storage projection
represented is explicitly refused, without inferring an implicit promotion.
The flow conservatively brings together the possible sources; the correlations more
The general signatures remain open.

No new ASan/TSan result or general security evidence is claimed.
The tests and models are finished. The complete objective of the seven drafts remains
ouvert.
