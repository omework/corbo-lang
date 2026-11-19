[Français](INLINE_REFERENCE_VIEWS_CYCLE-fr.md)

<a id="vues-de-sous-structures-contenant-des-références-int"></a>

# Views of substructures containing references Int

<a id="périmètre"></a>

## Perimeter

Connection of ST7 and ST10–ST18 to substructures with terminal fields
are Int, &Int or &mut Int. No normative changes.
ST17: Shared fields are copyable, mutable fields are not.

The views remain non-proprietary descriptions of root storage.
The references contained indicate their existing targets; no slot is
created for a substructure or a simple borrowed target.

## Changements

The verifier projects the root dependencies on the view prefix.
Projection is refreshed from the root when accessing and checking
status. Reassignment via view prefixes the modified path and updates
root. Flow control snapshots therefore continue to carry the state
canonical of this root.

Subtree reservations include targets for reference fields
the re-borrowing of an inner mutable capacity is recognized
as a derivative of the carrier's capacity, without double counting.
the former target, porter or capacity remain controlled separately.

Analysis of results and constraints keeps the internal and
The effect of a call on a view is translated into
effects on this holder. A shared reference returned as value keeps its
The target, without adding artificial dependence to the substructure slot.
The replacement results take into account the new field condition.

The inside copy without explicit pool now lowers the requirement of a
The requirement is spread to calls, such as the local root in the contract.
Existing storage requirements. An independent copy loses metadata
The projectors are the ones who have been able to project its origin while still keeping its reference fields.

<a id="cas-exécutés"></a>

## Cases implemented

Nine methods in `tests/test_inline_reference_views.py` : neuf programmes
The programme is not accepted and is not accepted.

- Reading and copying a shared view; still usable copy after drop of the
  carrier, target retained until last use of copy.
- Shared reference extracted by relays, detached from the carrier; drop too
  Early from the rejected target.
- Copy returned by function from an inside view; shared target
  preserved after root destruction.
- Reassignment of a shared field, direct or through a contract; new target
  visible from the root and old target liberable.
- Mutilated view returned through two functions and then used to modify
  field; concurrent modification via the refused root.
- Reassignment followed by return of reference; new target remains
  protected after the bearer has been destroyed.
- Reborrowing the field &mut Int via a function; disjunct brother accessible,
  access to the denied capacity, target and bearer.
- Replacement of a mutable field; old target, free, new target
  reserved until the carrier is destroyed. Copy of the refused mutable field.

The final O0 also includes the six methods of the view batch:
15 methods, 16 admitted programmes implemented and 16 rejected both
Clang C11/pthread, fatal UBSan and warnings as errors.

<a id="résultats-et-corrections-intermédiaires"></a>

## Results and interim corrections

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Initial O0 | 6 methods, 3 failures, 1,232 s, code 1 | `inline-reference-views-o0-first.log` |
| Second O0 | 6 methods, 2,547 s, code 0 | `inline-reference-views-o0-second.log` |
| Third O0 | 7 methods, 3.727 s, code 0 | `inline-reference-views-o0-third.log` |
| First regression O2 | 70 methods, 54.232 s, code 0 | `inline-reference-views-regression-o2.log` |
| Fourth O0 | 9 methods, 1 failure, 4,690 seconds, code 1 | `inline-reference-views-o0-fourth.log` |
| Fifth O0 | 15 methods, 1 failure, 6.634 seconds, code 1 | `inline-reference-views-o0-fifth.log` |
| Sixth O0 | 15 methods, 2 sub-cases of failed diagnosis, 6,763 s, code 1 | `inline-reference-views-o0-sixth.log` |
| Final O0 | 15 methods, 9.288 s, code 0 | `inline-reference-views-o0-final.log` |
| Final regression O2 | 82 methods, 62.577 s, code 0 | `inline-reference-views-regression-o2-final.log` |
| Copies async O2 | 6 methods, 3,643 s, code 0 | `inline-reference-views-async-copy-o2.log` |

Faults encountered: double counting of the mutable capacity of the subtree,
return shared reference wrongly classified as booking a mutable carrier,
and loss of the inner path in the junction of the values of the analysis of
The latter prevented the requirement to store the
returned copy. They were corrected without deleting access checks.

Two fixture adjustments are explicit: the allocation of the parameter
reference now uses `v.data = &*n`, already retained reborrowing rating ;
the historical copy test without pool awaits the diagnosis of incompatibility
The waiting for refusal is kept at both sides of the border.
The chess logs are still available.

All these processes have been completed; their codes have been recovered.
The final regression includes both cases added and
the latest corrections of source and storage requirements.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_reference_views test_inline_view_copy
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_reference_views test_inline_view_copy test_inline_structure_borrows test_inline_structure_construction test_stored_field_reborrows test_async_field_reborrows test_nested_field_replacement test_nested_field_choices test_storage_requirements
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_async_direct_copy
```

<a id="limites-et-suite"></a>

## Limitations and follow-up

Still to be connected: views containing references of types other than Int
or fields A<T>, storage of a view as a reference field, catches
and async returns of views, and results mixing whole reference and
These cases are not declared implemented by this lot.

The public reset remains removed from the prototype.
exercise still reset use their explicit legacy profile.
of this lot are on drop and the ordinary lifespans.

No new campaign of mutations or adversary generation.
models present in regression modules are executed with their cases
no model independent of new projections is added.
The results do not demonstrate the overall safety or completion of complete ST7.

Snapshot : `/tmp/crust-before-inline-reference-views/`.
Patches : `validation/inline-reference-views-{crust,results,constraints,structure_views,array_syntax,storage_requirements}.py.patch`.
