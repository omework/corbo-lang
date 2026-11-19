[Français](INLINE_OWNED_VIEWS_CYCLE-fr.md)

<a id="champs-propriétaires-dans-les-vues-de-sous-structures"></a>

# Owner fields in the views of substructures

<a id="périmètre"></a>

## Perimeter

Connection of ST7, ST8 and ST15–ST18: a view borrows storage of its
The root, including fields A<T>. It does not become the owner of the objects
The replacement evaluates the new allowance, destroys the old one,
then install the new handle in the real field. Transfers remain
explicites. Aucune modification normative.

The cycle covers functional cases and their directly related regressions,
in accordance with the user priority. It does not launch a new campaign
or mutations.

## Changements

Auditor projections now include proprietary fields
The direct writings and call effects are standardized in
paths on this root; views are not added to the inventory of
Cleanup. Code C uses existing accesses to the inner field address.

The analysis of the results keeps the proprietary fields in the views and
in the returned views. Paths alternate correctly the projections
The direct domestic arguments are
taken into account in the writing effects. The signatures of borrowed return
to a structure with fields are connected to existing contracts.

Extraction of a shared reference from a descendant keeps the target
The final report does not contain artificially the carrier.
descending himself retains the necessary reservations for his survival.

Archived Diffs: `validation/inline-owned-views-{crust,results,constraints}.py.patch`,
compared to `/tmp/crust-before-inline-owned-views/`.

<a id="cas-exécutés"></a>

## Cases implemented

`tests/test_inline_owned_views.py` 7 methods, 8 programmes admitted
exécutés nativement, sept programmes invalides refusés par `verify_program`
and `compile_source`.

- Reading via a function, unique destruction of the descendant before the root,
  then re-use its slot. Copy of the non-Copy view and early drop rejected.
- Mutation of the Int possessed and access to the disjointed brother field.
- &mut Int returns through view and relay; reserved root and target
  until last use, then reusable slot.
- Direct replacement with an allocation from another pool: old and new
  recoverable slots at the right time; no arrow refused.
- Replacement via contract; replacement pool too short refused.
- Replacement from a returned view and argument `&mut s.inner`.
- Change of reference in the A<Leaf> descendant, extraction of this
  reference, destruction of carriers and maintenance of the new target.

<a id="passages-ciblés"></a>

## Targeted crossings

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Premier O0 | 5 methods, 3 failures, 0.815 s, code 1 | `inline-owned-views-o0-first.log` |
| Second O0 | 5 methods, 2 sub-case failures, 2.222 s, code 1 | `inline-owned-views-o0-second.log` |
| Third O0 | 7 methods, 3 sub-case failures, 1,889 s, code 1 | `inline-owned-views-o0-third.log` |
| Fourth O0 | 7 methods, 1 failure, 3.123 s, code 1 | `inline-owned-views-o0-fourth.log` |
| Fifth O0 | 7 methods, 3,218 s, code 0 | `inline-owned-views-o0-fifth.log` |
| Historique O2 | 6 methods, 4.824 s, code 0 | `inline-owned-views-historical-o2.log` |
| Regressions O2 | 84 methods, 46,476 s, code 0 | `inline-owned-views-regression-o2.log` |

Two fixture defects were corrected without changing the language's expectations:
un nom `n` re-declared and subsequent access to `q` in the case to be checked
The other failures guided the connection of the
The last one is the return contracts and downhill paths.
correction removes an artificial &mut requirement on a shared reference
extracted from a shared carrier.

Native tests use Clang C11/pthread, fatal UBSan and warnings
The historical tests explicitly activate legacy-reset and
impose O2; they do not reintroduce into the public API.

The O2 regression includes `test_inline_owned_views`, `test_inline_typed_views`,
`test_inline_reference_views`, `test_inline_view_copy`, `test_inline_structure_borrows`,
`test_inline_structure_construction`, `test_nested_field_replacement`,
`test_nested_field_choices`, `test_returned_owned_replacement`,
`test_factory_owned_effects` and `test_async_owned_field_writes`. It includes the
existing model of target set `test_nested_field_replacement`, without
extend this model to the interior views or assign it this coverage.

## Limites

These results cover the recorded routes, not all combinations
alternative views, recursive graphs and mixed projections.
of a view in a reference field, catches/results async of views and
results mixing view and whole allocation remain to be connected. No other
C and ASan compiler was not executed for this lot.
Not a general proof of safety.
