[Français](ASYNC_OWNED_NOMINAL_WRITES_CYCLE-fr.md)

<a id="remplacements-de-descendants-à-références-nominales"></a>

# Replacements of progeny with nominal references

<a id="règles-et-périmètre"></a>

## Rules and scope

Extension of the connection of AS12/AS16 and SL1 to descendants A<T> who
contain &Point or &mut Point. The rules of replacement, service life,
The new concept of exclusivity and last use remains unchanged.
allocation is prepared before the destruction of the replaced descendant.
simply borrowed is not destroyed with him.

Tests prolong the already listed cases of the lot
[of descendants with references Int](ASYNC_OWNED_BORROW_WRITES_CYCLE.md).
No new arbitration or normative rule.

## Changements

- The proprietary signature filter accepts descendants containing
  nominal references whose parameter graph is already represented and
  Reference cycles are not permitted by this change.
- Application of field effects in an async state recognizes paths
  of substructures contained from the layout. It retains the provenance
  `(racine, chemin)` and checks the type of sub-object; it no longer confuses
  this path with a field that would contain a reference itself.
- The rest uses existing descriptors and contracts: old targets
  and new in a conditional replacement or a failed launch,
  Select suspended effects and control at the output of the telescopes.

<a id="cas-et-résultats"></a>

## Cases and results

Six methods in `tests/test_async_owned_nominal_writes.py` : nine executions
natives admises, dont une avec échec de soumission injecté, et douze programmes
disabled persons controlled by `verify_program` and `compile_source`.

- Direct and via auxiliary replacement, then wait: read the new
  Target and authorized transfer after destruction of the bearer.
- Normal Join and Launch Failure: New and Old respectively
  target; all possible targets remain protected before reading.
- Select's Lost Hanging: Replacement before yield remains
  visible after cleaning the selection.
- Mutilable reference: direct and auxiliary replacement, read by
  Reborrowing and premature writing of the refused target.
- Conditional replacement: both branches are executed and both branches are performed
  cibles possibles restent suivies statiquement.
- Substructure of a child block: refusal if the child holder survives the reference
  After it was destroyed.

The expected outputs are written in the tests independently of the C code.
Compilation Clang C11/pthread, error warning, UBSan without recovery.

| Journal in validation/ | Result |
| --- | --- |
| async-owned-nominal-writes-first-o0.log | 3 methods, 3 failures: owner signature filter |
| async-owned-nominal-writes-second-o0.log | 3 methods, 2 failures: local domestic origin not recognized |
| async-owned-nominal-writes-third-o0.log | 3 methods, 2,788 s, code 0 |
| async-owned-nominal-writes-fourth-o0.log | 6 methods, 4,079 s, code 0 |
| async-owned-nominal-writes-regression-o2.log | 101 methods, 82,937 s, code 0 |

Regression control:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_owned_nominal_writes test_async_owned_borrow_writes test_async_owned_field_writes test_async_stored_views test_async_enum_nominal test_nested_field_wrappers test_nested_field_choices test_async_owned_struct_sync_calls test_public_structure_handles test_inline_owned_views -v
```

## Limites

This batch does not prove all the compositions of graphs or all the
Interlacings. Recursive graphs and unrepresented signatures
no new campaign of change, of generation
adversarial or new independent model; the subsequent audit is not
Reset remains removed by default. The overall objective remains active.

Snapshot : `/tmp/crust-before-async-owned-nominal-writes/` ; patches of both
modules sous `validation/async-owned-nominal-writes-*.py.patch`.
