[Français](INLINE_VIEW_COPY_CYCLE-fr.md)

<a id="copie-explicite-des-vues-de-sous-structures"></a>

# Explicit copy of substructure views

<a id="périmètre-et-résultat"></a>

## Perimeter and result

Connection of ST17–ST18 and draft 07 to substructure views
already supported, in Int terminal fields. No rule of law changed.

`copy(vue)` reads the bytes of the local substructure and builds a value
independent of its type on the data stack of the recipient. `points.copy(vue)`
constructs this value in a slot of `Pool<Point>`. Copying does not hold
the root by the mere fact of reading its Int fields; the root remains usable
and can be destroyed after the last use of the view. Cleaning the copy
is from its own source.

A view of Point inside a Pool slot<Segment> does not have a
Pool<Point> of origin. The form without pool remains refused with a diagnosis
requesting a pool of the substructure type; no alternative pool is
selected silently. `points.copy(vue)` is exercised, including
through a function and after destruction of the original Segment.

<a id="implémentation"></a>

## Implementation

- Backend copy from `structure_view_address`, with the size of the layout
  Point, to storage created by existing copying mechanisms.
- Investment analysis recognises the projections and references
  The copy is stored at the recipient's place before entry.
  the block, loop or function producing. A simple view returned
  does not itself cause an allowance.
- The analysis of the results keeps separately `copy_candidates`, the provenances
  storage useful for a copy. They are not added to the targets of
  The loan: a view of the `s.debut` does not become an alternative loan of `s`.
- The contracts of copies instil these sources in relays, with a
  type and a new local value identity specific to the copy.
- The shape `break <-copy(vue);` is connected to the explicit owner result.
  The arrowless writing is not implicitly made moveable.

<a id="cas-et-preuves-exécutés"></a>

## Cases and evidence executed

Six methods in `tests/test_inline_view_copy.py` : sept programmes admis
C-based, four programs refused both entries.

- Independent local copy: different address, source modified and then destroyed,
  copie encore lisible, deux destructions.
- Copy to explicit pool: slot reused after destruction of copy;
  internal source copied without asking for a slot of the wrong type.
- Reference returned through two relays, then copied by a function,
  Then return the copy after the synchronous frames are released.
- Copy to an injected pool, returned result; pool of the result too short
  refused despite the possible survival of the original.
- Copies transferred to the output of a block and by `break`, clean child root.
- Copying during a refused active mutable re-borrowing, then authorized after its
  dernier usage.

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Initial O0 | 5 methods, 3 failures, 1,055 s, code 1 | `inline-view-copy-o0-first.log` |
| Second O0 | 5 methods, 1 failure, 1.669 s, code 1 | `inline-view-copy-o0-second.log` |
| Third O0 | 5 methods, 1 failure, 1.655 seconds, code 1 | `inline-view-copy-o0-third.log` |
| Fourth O0 | 5 methods, 1,984 s, code 0 | `inline-view-copy-o0-fourth.log` |
| Final O0 | 6 methods, 2.514 s, code 0 | `inline-view-copy-o0-final.log` |
| Regression O2 | 35 methods, 16.429 s, code 0 | `inline-view-copy-regression-o2.log` |

The intermediate failures were the placement of outgoing copies, the
treatment of `break` and loss/confusion of provenance in the
The programme and expected results were retained during the period of the
The processes have been completed and their codes have been recovered.

Clang C11/pthread, fatal UBSan, warnings as errors for testing
The eight historical regression methods use their target source.
O2/UBSan harness and explicit legacy-reset profile. No test jumped.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_view_copy
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_view_copy test_inline_structure_borrows test_inline_structure_construction test_async_direct_copy test_foundation_rules.FoundationTests.test_local_structure_copy_is_independent_and_reuses_dead_storage test_foundation_rules.FoundationTests.test_local_structure_copies_transfer_without_moving test_foundation_rules.FoundationTests.test_local_structure_copy_keeps_shared_target_across_return test_foundation_rules.FoundationTests.test_local_structure_copy_from_parameter_uses_receiver_storage test_foundation_rules.FoundationTests.test_local_structure_copied_parameter_retains_target_without_original test_foundation_rules.FoundationTests.test_local_structure_copy_rejects_noncopy_fields_and_active_mutation test_foundation_rules.FoundationTests.test_local_structure_return_through_loop_preserves_reservation test_foundation_rules.FoundationTests.test_local_structure_loop_conditional_breaks_share_reservation
```

<a id="limites-et-prochaine-étape"></a>

## Limitations and next step

Substructure views containing references or proprietary fields
The work required includes the projection of their targets,
the propagation of mutations to the root and corresponding contracts.
Storage of views in other values, their async capture and results
mixing inner view and entire reference are also incomplete.

This batch does not add any mutation campaign, adversary generation, or model
Independent Audits are conducted on the routes cited and regressions
directly linked; they do not prove general security or completion
all the rules of structure.

Snapshot : `/tmp/crust-before-inline-view-copy/`.
Patches : `validation/inline-view-copy-{crust,results}.py.patch`.
