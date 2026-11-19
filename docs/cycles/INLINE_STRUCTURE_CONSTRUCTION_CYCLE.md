[Français](INLINE_STRUCTURE_CONSTRUCTION_CYCLE-fr.md)

<a id="initialisation-des-structures-inline-imbriquées"></a>

# Initialization of interlocked inline structures

<a id="règles-et-écart"></a>

## Rules and deviations

ST1 requires that the fields directly contained belong to the allocation
ST3/ST4 define defects, named initializations and their
order; ST6–ST8, ST17/ST18 and async rules retain the constraints of
No regulations have been amended.

The layout already flattened the fields contained, and the shapes named as
`segment.start.x: expression` The construction was taken over.
`Outer { a: Pair { left: 1, right: 2 }, ... }` restait refusée par
"Unknown field in Outer". The refusal of the registered program
`validation/open-nested-structure-literal.crust` is reproduced on the snapshot
initial in `validation/inline-structure-construction-baseline.log`.

<a id="implémentation"></a>

## Implementation

`structure_construction.py` normalizes the manufacturers contained after the
type/feature resolution and prior to inference of effects, results and
The fields become the paths of the outer layout.
manufacturer's nominal content must correspond to the declared type; a
structure of the same shape but of another name is not interchangeable.

Standardization retains written order, field expressions and their
The missing defects are dealt with by existing checks.
The named paths remain available; the initializations that overlap
The Pool<T>, local pools and named alias settings are followed.
lexically to solve constructions `pool.new(...)`.

The structures contained do not create any Cell or independent slot.
references and owners join the graph of the allowance only
The existing preparation and cleaning also apply if a
later field suspends execution before the construction of the complete object.

<a id="tests-ciblés"></a>

## Targeted tests

Eight methods, nine native executions and eight invalid programmes
entry, i.e. sixteen refusal checks:

- Registered program: one local allocation and one destruction.
- Order written different from layout, recursive defects, aliased pool and re-used slot.
- Synchronous return, copying, mutable borrowings of separate fields and rejected conflict.
- Fields evaluated with await, local async return and copy after receipt.
- Builders in a pool injected from sync and async functions.
- Shared fields contents, sync/async returns, copy and then destroy the porter;
  premature destruction of the refused target.
- Field A<Int> content prepared before suspension: normal cleaning and destruction
  the task suspended via its ABI, not partially published external object.
- Incorrect nominal types, duplicates, unknown fields and defaultless reference
  - No, I'm not.

<a id="résultats-exécutés-et-corrections-de-fixtures"></a>

## Implemented results and corrections to fixed assets

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Initial target O0 | 8 methods, 1 fixture failure, 3.122 s, code 1 | `inline-structure-construction-o0-first.log` |
| Targeted after correcting variable name | 8 methods, 3,064 s, code 0 | `inline-structure-construction-o0-second.log` |
| First regression O2 | 62 methods, 1 diagnostic failure and 3 historical errors, 39,842 s, code 1 | `inline-structure-construction-regression-o2.log` |
| Trois tests historiques avant migration | 3 errors reproduced on the snapshot, 0.013 s, code 1 | `inline-structure-construction-legacy-baseline.log` |
| Migrated fixes on the initial snapshot | 3 methods, 1,327 s, code 0 | `inline-structure-construction-migrated-fixtures-baseline-final.log` |
| Final target O0 | 8 methods, 3,746 s, code 0 | `inline-structure-construction-o0-final.log` |
| Final regression O2 | 62 methods, 41,024 s, code 0 | `inline-structure-construction-regression-o2-final.log` |

The first failure used `pool` as a variable name, which conflicts
with the buildin when borrowing. The fixture now uses `items`.
Three historical tests used a T-notation on a pool allocation,
incompatible with V1 and current storage requirements.
and signatures passed to A<T>, without changing the statements of order, address,
They pass on the old compiler too.
A diagnosis expected for a non-constructible subfield has become more accurate.

A first test of loading the migrated fixtures had taken over the file of the
snapshot because of the order of the imports; its journal is kept separately
(`inline-structure-construction-migrated-fixtures-baseline.log`). L'essai final
explicitly loads the current test file with the snapshot compiler.

Targeted native executions use Clang C11/pthread and fatal UBSan.
No test jumped in the final passages. Regression includes models
existing pools async; no new mutation campaign or new
This is not the complete continuation of the deposit.

<a id="reproduction-et-limites"></a>

## Reproduction and limitations

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_structure_construction
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_structure_construction test_async_direct_copy test_async_struct_pools test_async_borrowed_struct_pools test_async_local_owned_result_graphs test_foundation_rules.FoundationTests.test_nested_structure_defaults_are_inline_in_one_slot test_foundation_rules.FoundationTests.test_nested_structure_named_paths_initialize_inline_in_written_order test_foundation_rules.FoundationTests.test_direct_recursive_structure_layout_is_rejected test_foundation_rules.FoundationTests.test_struct_pool_defaults_order_and_reuse test_foundation_rules.FoundationTests.test_struct_pool_reference_survives_return_and_checks_initializer_effects test_foundation_rules.FoundationTests.test_structure_methods_share_names_with_expression_builtins
```

Snapshot : `/tmp/crust-before-inline-structure-construction/` ; patches of
files modified in `validation/inline-structure-construction-*.py.patch`.

This lot connects the literals contained, not the insertion of a structure named
or calculated in an inline field. It does not define a displacement of a
The total number of loans from sub-structures
The results are based on the layouts already representative,
not on a general warranty for all types and combinations.
