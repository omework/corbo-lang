[Français](RECURSIVE_JOIN_HELPERS_CYCLE-fr.md)

<a id="helpers-dattente-sur-handles-récursifs"></a>

# Waiting Helpers on Recursive Handles

<a id="périmètre"></a>

## Perimeter

Application of existing AS10–AS12 rules, public outcome
Result<T,runtime::Error>, from transfers and borrowings to synchronous helpers
No change in the standard; calls continue
The draft 04 still prohibits join from using the code
async, including indirectly by a helper.

<a id="implémentation-et-défauts-corrigés"></a>

## Implemented and corrected defects

The program kept in validation/open-recursive-join-helper.crust
caused infinite unfolding in ResultContext.async_owned_result_value.
The analysis now unfolds the storage paths described by the contract,
without building an infinite value from the recursive type alone.

Symbolic entries distinguish a concrete sheet from a continuation
This continuation retains symbolic sources for the
later projections; it does not reserve any new runtime storage.
Its metadata crosses field descriptions and junctions.

The expected result of the helper finds the variants of the entry actually
They are no longer presented as fresh variants
The descendants obtained from a field of the result
The task force retains their identity, variant and descendants.
The targets borrowed from the entry are transmitted until the helper's result.
Restoration ignores the fields of proven variants absent, without
delete checks on possible variants.

<a id="tests-ciblés"></a>

## Targeted tests

Four methods in tests/test_recursive_join_helpers.py: five executions
The first is the first time that the programme has been completed.

- Helper public sending the Result of the join; three objects in two pools,
  destruction of the front-carrier sheet and re-use of the terminal slot.
- Reference stored in the terminal descendant: mutation refused as long as the
  result remains used, then drop the target after destruction of the result.
- Two successive helpers, graph with links and then simple terminal variant;
  Failure of tender injected with single destruction and re-use.
- Call for a helper blocking from the refused async in accordance with draft 04.

The original fixture was corrected to write match r on the Join Result,
and not match (>r), which designates other operations in the prototype.
the removal of infinite unfolding, this fixture error became visible.
Another fixture was wrongly waiting for acceptance of indirect join since l'async:
the table of rejected cases of draft 04 confirms the expected refusal.
was corrected, not the rule or the compiler control.

## Journaux

| Journal in validation/ | Terminal result |
| --- | --- |
| recursive-join-helpers-first-o0.log | 2 methods, 1 failure: missing borrowed source |
| recursive-join-helpers-second-o0.log | 2 methods, same refusal of origin |
| recursive-join-helpers-third-o0.log | 2 methods, target missing from result contract |
| recursive-join-helpers-fourth-o0.log | 2 methods, 0.914 s, code 0 |
| recursive-join-helpers-fifth-o0.log | 3 methods, 2,414 s, code 0 |
| recursive-join-helpers-sixth-o0.log | 4 methods, fixture error on join since async |
| recursive-join-helpers-seventh-o0.log | 4 methods, 2,230 s, code 0 |

The O2/UBSan regression completes 112 methods in 120,958 s, code 0:
validation/recursive-join-helpers-regression-o2.log. The three synchronous cases
selected pass in 2,209 s, code 0 :
validation/recursive-join-helpers-sync-regression.log.

The targeted harness compiles the C11 with pthread, error warning and UBSan
The regression selection also uses O2/UBSan; the harness of the
job results do not activate the same warnings and add pthread when the
C generated requires. The three synchronous historical tests use their harness
O2/UBSan with legacy-reset.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_join_helpers -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_public_structure_handles test_public_local_enums test_task_result_storage test_local_result_envelopes test_business_result_envelopes test_async_owned_struct_returns test_async_owned_borrow_writes test_async_result_factories test_async_stored_views -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_function_returns_consumed_recursive_owned_projection_through_relay test_foundation_rules.FoundationTests.test_function_composes_two_owned_extractions_with_fresh_fallback test_foundation_rules.FoundationTests.test_recursive_owned_parameter_can_be_inspected_relayed_and_destroyed -v
```
Values, diagnostics, traces of destruction and reuse are the oracles
No new independent oracle or mutation campaign.

## Limites

These tests do not cover all recursive projection routes, nor all
the replacements of descendants. The symbolic continuation gives a
finished representation of the entrance; it does not prove that all its operations
The results of the new recursive form and the
The overall objective remains open.

Snapshot : /tmp/crust-before-recursive-join-helpers/.
Diffs: validation/recursive-join-helpers-crust.py.patch and
validation/recursive-join-helpers-results.py.patch.
