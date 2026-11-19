[Français](ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE-fr.md)

<a id="cycle--captures-de-structures-contenant-des-références"></a>

# Cycle — captures of structures containing references

The differences in direct reborrowing and async return have since been
processed in [ASYNC_FIELD_REBORROWS_CYCLE.md](ASYNC_FIELD_REBORROWS_CYCLE.md)
and [ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md](ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md).
The limits indicated in this report remain the observations of its cycle.

The [Int field structure cycle] continues](ASYNC_STRUCT_CAPTURES_CYCLE.md).
No regulatory changes.
B1/B2/B4/B4a, AS2/AS8–AS15, MT1–MT4/MT8 and RT8; PR1 for separation
The remaining obligations of the seven drafts remain open.

<a id="implémentation"></a>

## Implementation

A task can capture `&View` ou `&mut View` when View layout contains
Int, &Int and &mut Int fields. Existing pointers are kept.
The follow-up retains the bearer and, transitively, its targets and their sources.
Reading `*view.data` load the field pointer and then its Int content.
Mixed offsets take into account the size of pointers; a writing
Int cannot overwrite a reference field.

The auxiliary and synchronous methods receive symbolic inputs including
The dependencies correspond to the real fields.
Int targeted remain checked by the synchronous backend.
Field pointers are established at the bridge entrance.
contract changes the dependencies of a structure remain explicitly non
Connected: to accept them without spreading effects would not be correct.

The catches are relayed between tasks and in native thread blocks.
The Int result does not artificially retain the loan after waiting.
An inactive task destroyed or a rejected launch releases its reservations,
The C runtime is unchanged.

The [historical case]](../../validation/open-async-struct-reference-field.crb) affiche
now 7; sound [C generated](../../validation/async-struct-reference-field-basic.c)
is kept. The patches of this cycle are in `validation/async-struct-reference-fields-*.patch`.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

The first passage revealed that the historical reset only looked at the
Directly captured targets: task → View masked the second link View → Int.
So he could destroy this Int before waiting.
The test requires refusal in the `verify_program` and
`compile_source`After waiting and last use, the reset remains accepted in the
Historical profile only. PR1 is not modified.

The first tests also set out a previous limitation: `target.set(n)`
does not yet take a general expression in the synchronous path.
bridge uses `*target = n`, whose mutation semantics are already established.
The [case set not connected](../../validation/open-sync-set-expression.crb) and its
[diagnostic](../../validation/open-sync-set-expression.log) remain recorded.
An nested manufacturer test used not-recognized pointed names
It was not proof of support for the construction of the
nested ; layout test uses several explicitly referenced fields
declared, separated by Ints, and retains its oracle of mixed offsets.

The historical reset/reference fields also derived from U1:
they created allowances without explicit use.
The same 20 assertion failures and 39 errors are reproduced with the
Three modules of the compiler before this cycle. Logs are kept.
The fixed amounts now read the allocations before the transactions studied;
the added outputs are explicitly expected. The traces of destruction,
slot identities, model decisions (19 admissions, 13 refusals), and
The expected memory diagnoses are not weakened.
on an existing reference use its name in accordance with the chosen rule.

<a id="preuves-exécutées"></a>

## Evidence

Async/native passages use Clang C11, pthread, blocking warnings,
UBSan fatal and O0/O2. Recontrol of the 72 synchronous methods uses Clang
C11, blocking warning and fatal UBSan **without explicit optimisation option** :
their old harness doesn't read CRUST_TEST_OPT. No new results found.
TSan, second compilateur ou preuve formelle.

| Passage | Result | Journal |
| --- | --- | --- |
| Initial O0 | 23 methods, 14,520 s; 2 failures and 1 error. Accidentally includes imported native tests; import was then corrected | [Initial](../../validation/async-struct-reference-fields-initial-o0.log) |
| Recheck O0 | 10 methods, 4,846 seconds, OK | [Rechecking](../../validation/async-struct-reference-fields-recheck-o0.log) |
| Targeted + model O0 | 13 methods, 9,159 seconds, OK | [O0](../../validation/async-struct-reference-fields-complete-o0.log) |
| Eff. boundary, explicit reborrowing corrected | 1 method O2, 0.011 s, OK | [Front](../../validation/async-struct-reference-fields-update-boundary-o2.log) |
| Final target O2 | 12 methods, 6.550 s, OK; 16 C performances, including an injected LaunchFailed and a historical reset; 25 programmes rejected in each of the two courses, i.e. 50 checks | [Final runner's baseline](../../validation/async-struct-reference-fields-classified-mutations-o2.log) |
| Model O2 + initial historical regressions | The model passes its 16 cases (11 executions, 5 refusals). 73 methods: 48.253 seconds, 20 failures and 39 historical errors | [Initial expanded pass](../../validation/async-struct-reference-fields-model-and-sync-o2.log) |
| Same regressions on previous compiler | 72 methods, 23.936 s; same 20 failures and 39 errors | [Baseline historique](../../validation/async-struct-reference-fields-sync-baseline.log) |
| Corrected historical fixtures, fatal UBSan | 72 methods, 43,956 seconds, OK | [Synchronous control](../../validation/async-struct-reference-fields-sync-recheck.log) |
| Regression of contracts/features/references O2 | 76 methods, 72,495 s, OK | [Contrats](../../validation/async-struct-reference-fields-contracts-o2.log) |
| Native regression O2 | 244 methods, 207.068 s, OK | [Native](../../validation/async-struct-reference-fields-native-o2.log) |

Selections overlap. Native regression has loaded the initial fixture
field replacement; the final targeted passage uses explicit re-borrowing
There is no change in the compiler between these two passages.

The independent model reason on two life links, task → carrier
→ Int, exclusivity and waiting. It does not consult the compiler's decisions.
Tests also cover aliases out of their block, arguments actually
The following are the main features of the project:

## Mutations

The [targeted runner]](../../tests/run_async_struct_reference_field_mutations.py) modifie
Five behavioral errors are detected: offsets
calculated as Int, value read replaced, bridge dependencies removed,
restet limited to the first lost deal and dependency of capture.

The removal of the refusal of changes in dependency is classified
`STAGE_DIVERGENCE` : verify_program accepts the program, but compile_source
yet refuses it by another limitation of representation.
between courses detected, not a sixth proof of detection of a memory violation
The intermediate newspapers that labeled it DETECTED are
The final runner distinguishes this case.
The [journal classified by internship](../../validation/async-struct-reference-fields-stage-mutations-o2.log)
retains the names of the two entry points to make this deviation explicit.

The six mutations of the previous cycle are also detected after adaptation
their anchors to the new offset calculation. Their baseline succeeds 14 methods,
15 C executions and 29 refusals: [journal](../../validation/async-struct-reference-fields-prior-mutations-o2.log).
No overall detection rate is derived from this selected sample.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The [re-borrowing field directly in a task](../../validation/open-async-struct-field-reborrow.crb)
remains refused: [diagnosis](../../validation/open-async-struct-field-reborrow.log).
Projections, loans by field, calls and calls must be linked.
The changes in field dependencies must be based on the results of the study.
then spread into the job contracts and to their callers.
Owner fields, more general types of graphs, catches
by transfer and general construction of structures in the states remain
The flattened layout is used, but this cycle has not validated the construction
nested structures containing references.

Other storage obligations, signatures, public scheduler, Select and
This cycle does not end the overall objective and does not prove
not the safety of all reference graphs or of all schedules.

## Reproduction

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_struct_reference_fields test_async_struct_reference_field_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_struct_reference_field_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_struct_capture_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_SANITIZE=undefined python3 -m unittest test_reset_transitions test_reference_fields test_mutable_reference_fields -v
```
