[Français](ASYNC_RECURSIVE_OWNED_CYCLE-fr.md)

<a id="graphes-propriétaires-récursifs-aux-frontières-async"></a>

# Graphics owners recursive at the borders async

<a id="périmètre-et-changements"></a>

## Perimeter and changes

Application of existing explicit transfer rules, stable addresses,
of a recursive type containing
`A<T>`. No new normative rules. The proprietary edges have a size
of a known handle; they must not impose an infinite unfolding of the type
to represent an async state. Nominal reference cycles are not
extended by this lot.

- The layout classification accepts cycles through fields A<T>.
- The concrete metadata of the result retain the variant of each
  descendant. The restoration stops on the terminal variant.
- Synchronous bridges stop unfolding recursive types; the
  opaque projections use the symbolic mechanism of synchronous inputs.
- The return of a landlord keeps the concrete paths taken which
  The fields explicitly exceed the finished list of paths of type.
  The public authorities are also responsible for the implementation of the public procurement contract.
  calculate the mode of borrowing by traversing the path actually present.

<a id="défauts-reproduits"></a>

## Reproduced defects

The first batch tests refused recursive catches; after extension
restoration was looking for a non-existent descendant in the terminal variant.
The synchronous helper caused an infinite unfolding, converted by the LTC into
"over-interlocked program" means both connections are corrected.

Un programme renvoyant Link → Link → End{value:&number} autorisait `number=8`
while the living result always contained the reference. The test failed
the two inputs of the compiler. The propagation of the concrete paths corrects
This flaw. The handlet's annotation then revealed a KeyError on the same
path; the mode of the field is now obtained by type path.

The first negative test used drop from the child arm and was refused
for this reason before exercising the borrowing. It was corrected in mutation of the
target from the arm, to isolate the reservation actually sought.

<a id="cas-et-preuves-ciblées"></a>

## Targeted cases and evidence

`tests/test_async_recursive_owned.py` contains five methods, seven executions
and four invalid programs checked by both entries.

- Return of a graph of three objects in two pools, destruction sheet front
  carriers, re-use of all slots; normal submission and injected failure.
- Play in nested matches separated by yield; drop of the holder refused before join.
- Local pools in a task, destruction of an inactive task and re-use.
- Synchronous helpers of inspection, relay and destruction of the graph.
- Reference stored in the terminal descendant, inferred or annotated handle:
  still alive result protects the target, then destruction allows its drop.

The expectations of values and traces are written in the tests.
async compiles C in C11/pthread, error warnings, fatal UBSan. The level
d
use their C11 harness to O2/UBSan and the legacy-reset option.

<a id="exécutions"></a>

## Implementation

The final target passage O0 is in
`validation/async-recursive-owned-public-second-o0.log` : five methods,
3.142 s, code 0. Previous newspapers retain the failures described above.

| Journal in validation/ | Terminal result |
| --- | --- |
| async-recursive-owned-regression-o2.log | 120 methods, 98,500 s, code 0 |
| async-recursive-owned-sync-regression.log | 7 methods, 4,156 s, 1 error of source |
| async-recursive-owned-sync-baseline.log | Same error reproduced on snapshot before batch, 1 method, 0.101 s |
| async-recursive-owned-storage-regression-o2.log | After correction: 22 methods, 13,706 s, code 0 |
| async-recursive-owned-storage-boundary-o2.log | 11 methods, 1 fixture failure: structure pattern not expected |
| async-recursive-owned-storage-boundary-second-o2.log | Fixed in sum: 11 methods, 7,354 s, code 0 |

Historical correction recognizes the sources of proprietary fields A<T>
as pool allowances independent of the bearer. The additional test
Extract the same field from a local carrier and then from a pool carrier:
two executions admitted, two incompatible local annotations refused to both
The test uses a match consuming d
The first wrong fixture is kept in his diary.

Reproducible commands (direct to corresponding logs):

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_recursive_owned
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_recursive_owned test_async_owned_enums test_async_enum_match test_async_owned_struct_sync_calls test_async_owned_struct_returns test_async_owned_borrowed_captures test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_stored_views test_public_structure_handles test_public_local_enums test_local_enums -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_storage_requirements test_async_recursive_owned test_foundation_rules.FoundationTests.test_recursive_handle_field_layout_is_pointer_sized test_foundation_rules.FoundationTests.test_recursive_owned_fields_drop_children_once_in_origin_pools test_foundation_rules.FoundationTests.test_function_returns_finite_value_of_recursive_owned_type test_foundation_rules.FoundationTests.test_recursive_owned_parameter_can_be_inspected_relayed_and_destroyed test_foundation_rules.FoundationTests.test_recursive_mutable_parameter_updates_deep_leaf_in_place test_foundation_rules.FoundationTests.test_consuming_match_extracts_recursive_owned_child_beyond_first_repeat test_foundation_rules.FoundationTests.test_function_returns_consumed_recursive_owned_projection_through_relay -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_storage_requirements -v
```

The 22 method command precedes the addition of the last test: it selects one
The 120 methods precede the isolated correction in the final state.
storage_requirements.py; second selection and storage module were
These numbers are not test accounts.
The deterministic models already present in the modules
selected were replayed; no new independent oracle was added.

## Limites

The coverage covers the concrete graphs and paths listed above.
The projections borrowed deeply in a helper, the opaque factories
and recursive depth replacements are not declared covered by
A symbolic bridge source describes a requirement to
life; this is not a new pool of running allowances.
The retention of inherited paths not specified by the contract may be
The other rules still open remain in the overall objective.
No new transfer campaign or independent audit.

Snapshot avant lot : `/tmp/crust-before-async-recursive-owned/`.

Diffs of the three modules archived in `validation/async-recursive-owned-*.py.patch`.
