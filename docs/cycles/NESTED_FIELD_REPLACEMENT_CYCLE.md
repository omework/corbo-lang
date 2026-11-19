[Français](NESTED_FIELD_REPLACEMENT_CYCLE-fr.md)

<a id="remplacement-des-références-dans-les-descendants-possédés"></a>

# Replacement of references in possessed descendants

<a id="règles-appliquées"></a>

## Rules applied

This lot applies existing rules ST6–ST15, B1–B5, D1, T1/T6,
AS2/AS8–AS15 and RT6: a field change changes dependencies
of this field, without changing those of his brothers; the transfer of the graph
keeps all targets still accessible.
No changes in the rules are introduced.

The programme `validation/open-nested-field-replacement.crust` peut maintenant
remplacer `outer.inner.view`, transfer out into a task and destroy
the old target before waiting. The new target remains reserved until
destruction of the wearer. Tests also cover a return of the entire graph,
a change in the production task and two levels of descendants.

<a id="implémentation-et-recherche-de-contre-exemples"></a>

## Implementation and search for counter-examples

Analysis of results keeps the owner and the way of a loan
Deteriorating mutable. Contract updates may be directed at this
projection. They update the fields of the descendant and the complete paths
on the parent, without replacing the parent's fields with the child's.
Symbolic descendants of the parameters possessed are developed on demand
by keeping their sources and the targets borrowed.

The backend resolves each A<T> edge of the path before applying a
field. It keeps the prefix of the descendant in the key of the loan.
the old and new targets; the brothers remain
separate, even with identical field names.

Additional composition was refused: the launch of a task that had been completed
The analysis of the end of a factory, without delayed field effects.
now use its full contract even if the list of entries is empty.
An unknown contract does not become an empty effect; the effects of suspension
of this form remain explicitly unconnected.

The original file also contained `value.view = target`, notation implicite
The rules have been adopted and he is now using `&*target`Refusal
from the previous compiler on this corrected version is kept in
`validation/nested-field-replacement-corrected-baseline.log` : both stages
The async producer's fixture was not the descendant's dependencies.
also was corrected to declare its parameter possessed `mut`.

<a id="preuves-exécutées"></a>

## Evidence

- Targeted follow-up to O0: 11 methods, 18 native executions, 18 programmes
  36 refusal checks, in 8,251 s.
  `validation/nested-field-replacement-count-o0.log`.
- The same 11 methods go to 8.639 s.
- Async to O2 regression: 144 methods pass in 129,322 s; regression
  synchronous: 46 methods pass in 38,188 s. The newspapers are
  `nested-field-replacement-regression-o2.log` and
  `nested-field-replacement-sync-regression-o2.log` in validation.
- Independent model included: two edges owned and three targets, replacement
  The 12 combinations
  The oracle is the result of 7 cases and 5 programmes rejected in both stages.
  calculates the accessible target sets without questioning the compiler.
- Checked exits and destruction order; return of graph, maintenance of graph
  new mutable loan, block target too short, homonymous and launch
  refused by the scheduler are covered.
- Four mutations targeted: three detected, one survivor.
  prefix of descend, omit any projected update or lose the
  targets stored on the parent fail the assertions. Delete only
  updating the fields of the child node survives the targeted test and the 11 methods
  The paths of the
  In these scenarios, there is no general equivalence between parents.
  The campaign keeps its code 1; investigation in
  `validation/nested-field-replacement-survivor-o2.log`.

Native programs use clang C11/pthread, O0 or O2, warnings
no new results ASan/Tsan.
Initial and intermediate logs are kept; the tests expected
valid tests were not changed to refusal tests to circumvent the restrictions.
All the processes of the lot are completed. The final suites come out with the
code 0; the mutation campaign comes out with code 1 for the survivor.

Commandes reproductibles :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_nested_field_replacement.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_nested_field_replacement_mutations.py
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_nested_owned_borrows test_nested_detached_references test_public_structure_handles test_async_execution_arguments test_async_field_application test_async_child_field_effects test_async_owned_borrowed_captures test_async_capture_field_contracts test_sync_handle_field_effects test_select_source -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_reference_fields test_stored_field_reborrows test_stored_field_reborrow_model test_mutable_field_completion -v
```

<a id="limites-et-travail-restant"></a>

## Limitations and remaining work

The relay `change_outer(value: &mut Outer, target: &Int)` who borrows the parent
then call changes on his descendant remains refused.
valid is `validation/open-nested-field-wrapper.crust` • refusal of both
steps is kept in `validation/nested-field-wrapper-probe.log`.
Monitoring of projections must also go through stress analysis and the
signatures of aggregate borrowings containing A<T>. This site remains open.

Update: this relay is processed in [NESTED_FIELD_WRAPPERS_CYCLE.md](NESTED_FIELD_WRAPPERS_CYCLE.md).
This later cycle also detects the surviving mutation with a reading of the
modified descendant followed by assignment to his brother. The results above
The campaign was not the only one that had been in the original form.

The recursive type graphs, general signatures and the public API of
The replacement of the scheduler is not generalized by this lot.
finite model does not prove the safety of all compositions.
survivor remains an explicit limit of validation.

The three differences are archived in
`validation/nested-field-replacement-*.py.patch` from the snapshot
`/tmp/crust-before-nested-field-replacement`. The overall objective remains active.
