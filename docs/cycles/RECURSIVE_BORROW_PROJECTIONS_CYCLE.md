[Français](RECURSIVE_BORROW_PROJECTIONS_CYCLE-fr.md)

<a id="projections-empruntées-dans-les-graphes-propriétaires-récursifs"></a>

# Projections borrowed from the recursive proprietary graphs

<a id="règles-et-changements"></a>

## Rules and changes

Application of existing rules for shared/mutable access, life and
A<T> field transfer, synchronous and async states. None
The lot continues the deep projections announced after the
Recursive waiting helpers.

The symbolic descendants were only preparing their own ties.
helper browsing several links and then reading a &Int field was refused for
The fields used are now prepared for the
the demand on the only explicitly symbolic descendants.
are cached by origin and field; concrete values do not benefit
no of this mechanism to hide a missing field.
keep the substructure descriptor, including the target offset.

The construction of the graph in a task also revealed a loss of loans:
the transfer of a owner only took the paths listed by the type
before its first rehearsal. The concrete deeper paths are now
solved by consuming the components of the path, then transferred with the
The transfer of an allowance remains a transfer of responsibility.

Finally, the play filter in a match recognizes the ordinary readings of
The normal control of the
The type, existence of the field and borrowings remain applied.

<a id="défauts-reproduits-et-oracles"></a>

## Reproduction and oracle defects

The first two playback programs, synchronous and with call from a
were refused for missing borrowed field.
After the projections were prepared, the readings were executable.
negative async was still refused only by subsequent use of the
variable already dropped. By deleting this parasitic use, verify_program and
compile_source accepted premature drop before reading the graph.
The spread of concrete paths corrects this acceptance.
then re-use the variable: it isolates the dependence of the graph.

The reading of a nominal reference then revealed the syntactic filter of the
match, corrected for the fields read. The inner target is preceded by an Int
99; read the right field must produce 7, not the beginning of the root.

<a id="cas-ciblés"></a>

## Targeted cases

Four methods in tests/test_recursive_borrow_projections.py: six executions
The first is the first year of the programme.

- Shared Helper that follows two homeowner links then reads &Int, called since
  hand then from an async state after yield; premature drop of the refused target.
- mutable helper following the same links and then writing through &mut Int,
  in synchronous and since async; direct concurrent writing of the refused target.
- Field &Point for an inner substructure, with two call paths;
  reading the right offset, refusing to write the target before the last access,
  then write it after the graph has been destroyed.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| recursive-borrow-projections-first-o0.log | 2 methods, 2 failures: missing provenance |
| recursive-borrow-projections-second-o0.log | Readings pass ; 2 diagnostic sub-failures for refusal too late |
| recursive-borrow-projections-third-o0.log | 2 methods, 1,152 s, code 0 |
| recursive-borrow-projections-fourth-o0.log | 3 methods, 1,755 s, code 0 |
| recursive-borrow-projections-fifth-o0.log | 4 methods, 1 field read filter failure |
| recursive-borrow-projections-sixth-o0.log | 4 methods, 4,615 s, code 0 |

Regressions completed with code 0: 86 methods at O2/UBSan in 70,513 s
(validation/recursive-borrow-projections-regression-o2.log) and five cases
O2/UBSan synchronous in 3,417 s
(validation/recursive-borrow-projections-sync-regression.log).
The targeted harness compiles the C11/pthread, error warnings, fatal UBSan.
The five historical cases require legacy-reset for their old controls.

The minimum invalidated programme is retained in
validation/recursive-borrow-target-drop.crust. Both diagnoses performed
are in validation/recursive-borrow-target-drop.log: active borrowing,
without depending on subsequent use of the already destroyed variable.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_borrow_projections -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_borrow_projections test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_shared_match_field_reads test_async_stored_views test_async_enum_nominal test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_owned_struct_sync_calls test_async_owned_struct_returns test_public_structure_handles -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_recursive_owned_parameter_can_be_inspected_relayed_and_destroyed test_foundation_rules.FoundationTests.test_recursive_mutable_parameter_updates_deep_leaf_in_place test_foundation_rules.FoundationTests.test_function_returns_consumed_recursive_owned_projection_through_relay test_foundation_rules.FoundationTests.test_recursive_enum_shared_links_match_terminal_variant test_foundation_rules.FoundationTests.test_recursive_enum_match_retains_all_referent_variants -v
``` Les sorties, diagnostics et
life rules are the explicit expectations of the tests; no new
Independent or mutation campaign n

## Limites

Operations are readings and writings about targets
The return of a loan
Since helper and replacements of recursive descendants are not
not declared complete by this lot. Symbolic continuations remain a
finished representation of unknowns, not proof of all operations.
The overall objective remains open; no independent audit carried out in this lot.

Snapshot : /tmp/crust-before-recursive-borrow-projections/.
Diffs: validation/recursive-borrow-projections-crust.py.patch and
validation/recursive-borrow-projections-async_lowering.py.patch.
