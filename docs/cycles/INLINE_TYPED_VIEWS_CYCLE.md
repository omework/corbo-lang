[Français](INLINE_TYPED_VIEWS_CYCLE-fr.md)

<a id="vues-de-sous-structures-contenant-des-références-typées"></a>

# Views of substructures containing typed references

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Extension of the connection of ST7 and ST10–ST18 to views containing references
No normative changes. The view has no
no independent storage: its address and fields remain those of the
root. A shared reference extracted retains its target; a mutable reborrowing
Also retains the reservation of the capacity from which it derives.

The validation follows the required scope: agreed functional cases and
direct regressions. No new generation campaign,
no general proof of security.

<a id="implémentation"></a>

## Implementation

- Authorization of the reference fields typed in the internal projections.
- Composition of the inner path in typical reborrowing contracts.
- Comparison of mutation effects with actual root snapshots,
  projected on the subtree concerned; views are not allocations.
- Standardisation of the carriers of mutable capacities when comparing
  between the contract and the body audited.
- Distinction between an effect on a descendant owner and dependencies
  transitory cached through a reference field. `link.leaf`
  does not change the field `data` These dependencies remain
  in the symbolic contract; they do not become physical scriptures.

Changes in the `crust.py` and `results.py` are archived in
`validation/inline-typed-views-*.py.patch`, compared with the copy
`/tmp/crust-before-inline-typed-views/` prior to the batch.

<a id="cas-ciblés"></a>

## Targeted cases

`tests/test_inline_typed_views.py` contains six methods: six programs admitted
exécutés nativement et dix programmes invalides refusés par `verify_program`
and `compile_source`.

1. Shared return to Point through two functions and an inner view;
   destruction of the authorized holder, early destruction/mutation of the refused point.
2. Copy Link and then extraction of Point; destruction of both authorized carriers,
   Early destruction of the refused target.
3. Replacement of the reference field by a call on a view; old target
   free and new protected target, read from the updated root.
4. Reborrowing typed mutable returned by relay; brother field accessible, destruction
   the holder and incompatible access to the refused target or capacity.
5. Transit extraction of &Int; destruction of authorized intermediate carriers,
   destruction of the refused target.
6. Replacement of the mutable field followed by the return of the new target; old
   free-standing target, new target and carrier retained until last use.

<a id="exécutions-et-corrections"></a>

## Implementation and corrections

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Initial O0 | 5 methods, 2 failures, 1,320 s, code 1 | `inline-typed-views-o0-first.log` |
| Second O0 | 5 methods, 1,704 s, code 0 | `inline-typed-views-o0-second.log` |
| Third O0 | 6 methods, 1 failure, 2,048 s, code 1 | `inline-typed-views-o0-third.log` |
| Fourth O0 | 6 methods, 1 failure, 1.763 seconds, code 1 | `inline-typed-views-o0-fourth.log` |
| Fifth O0 | 6 methods, 2,102 s, code 0 | `inline-typed-views-o0-fifth.log` |
| Initial regression O2 | 40 methods, 2 failures and 4 subcase errors, 17,179 s; terminal status not recovered | `inline-typed-views-regression-o2.log` |
| Final target | 9 methods, 4.247 s, code 0 | `inline-typed-views-o0-sixth.log` |
| Final regression O2 | 40 methods, 20.156 s, code 0 | `inline-typed-views-regression-o2-final.log` |
| Owners' Regression O2 | 19 methods, 9,989 s, code 0 | `inline-typed-views-owned-regression-o2.log` |

The first two failures came from a fixture with an allocation `b`
unused: it was moved in the case only that uses it, without releasing
the explicit rule of use. The following two revealed the loss of the path
In the contract, then compare a porter seen at its root.

The first regression then revealed the incorrect treatment of dependencies
transitive as indirect scriptures. The historical test
`test_replace_shared_typed_field_updates_nested_provenance` was also executed
on the copy prior to the batch: same error, one method, 0.096 s, code 1
(out of tool, no separate log). The defect preceded this batch for
The expectations of historical tests are maintained.

The six new tests use Clang C11/pthread, fatal UBSan, warnings
as errors, at O0 and then O2. The final targeted passage adds three historical tests
whose harness imposes O2 and explicitly activates the legacy-reset profile.
The main regression takes over the modules `test_inline_typed_views`,
`test_inline_reference_views`, `test_inline_view_copy`, `test_inline_structure_borrows`
and 12 methods `test_foundation_rules` (full names in the journal).
The owner regression resumes `test_returned_owned_replacement`,
`test_factory_owned_effects` and `test_async_owned_field_writes`.

## Limites

The cases carried out cover targeted structures; not all of them demonstrate
recursive graphs or enum combinations.
in a view, the storage of a view in a reference field, its catches and
results async as well as results mixing view and whole allocation remain
The projections already have a `carrier_kind` are not extended
by this lot. No independent model, ASan or other C compiler was executed
for this batch. Reset remains a historical API removed from the default prototype.
