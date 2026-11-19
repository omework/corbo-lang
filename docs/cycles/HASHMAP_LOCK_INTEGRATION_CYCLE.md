[Français](HASHMAP_LOCK_INTEGRATION_CYCLE-fr.md)

<a id="intégration-de-hashmap-et-transport-des-contrats-de-verrou"></a>

# HashMap integration and lock contract transport

<a id="règles-exercées"></a>

## Rules exercised

- HM1–HM6. `HashMap<K,V>::new()` Operations `insert`,
  `try_insert`, `get`, `get_mut` and `remove` go through the auditor
  and Generation C. Shared and exclusive loans are on the table.
  The loan of the key ends after the search. For a known key, the
  replacement or extraction only alters the dependence of its input.
- MT10. A borrowed argument keeps its bearer alive. Direct transfer
  by argument propagates the lock if the function returns the carrier.
  the order deducted in its contract decides whether it can
  a proprietary capture keeps the lock of the lock
  creation of the task to its clean-up or to the return of the bearer.
  The result of the `join()` keep the lock until the
  destruction of its value. `LaunchFailed` Cleans the catch.

<a id="exécutions"></a>

## Implementation

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest -v \
  test_hashmap test_hashmap_runtime test_lock_contracts
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest -v \
  test_hashmap test_hashmap_runtime test_lock_contracts test_core_integration \
  test_loop_replacements test_async_owned_struct_returns test_async_owned_struct_sync_calls
```

Native cases compile the C generated with UBSan and stop execution at
The first diagnosis. Targeted refusals are through `verify_program` and
`compile_source`. The oracle Python compares the sequence of table operations
with an independent dictionary. Native probes observe stability
address and re-use of the sites. Failure to insert is caused
reducing the capacity of the input area in the generated C. Both
branches check the value rendered and the maintenance of the table.
launch is injected at the point of submission of the runtime.

- 18 targeted tests passed on UBSan to `-O0`.
  [Journal](../../validation/hashmap-lock-integration-o0.log)
- 89 tests passed in the regression batch under UBSan at `-O2`.
  The case of successful replacement by `try_insert`, added during the pass,
  was replayed separately at the same level of optimization.
  [Regression Journal](../../validation/hashmap-lock-integration-o2.log) ·
  [Target game](../../validation/hashmap-lock-integration-o2-try.log)
- Four successful targeted grammar cases.
  Two expectations were for the customizable scheduler interface which
  has since been removed from the target kernel.
  [Specified cases](../../validation/hashmap-lock-integration-grammar.log)
- [Asan and UBSan Sondes](../../validation/hashmap-lock-integration-asan.log).
  The minimum tell-tale and the C generated each exceed the five-fold time limit.
  The ASan result is unknown.
- [Previous reproduction of the enum return test](../../validation/hashmap-lock-integration-legacy-baseline.log).
  The general discovery was interrupted after a failure of the test
  `test_enum_expression_transfers_preserve_arm_and_cleanup_order`.
  The same program fails with the same diagnosis in the previous copy
  `/private/tmp/crust-before-inline-vector-replace-contracts`. The pass
  Therefore, no conclusion can be reached on the entire deposit.

## Limites

- Source transactions cover scalar values, nominal values
  support, pool allowances and scalar references.
  Signatures of functions performed receive scalar-charged tables
  by borrowing. Contracts for transfer or return of a dependent table
  dependent, the nominal references stored and the direct use of the table
  in async functions remain open. In the presence of an unknown key,
  the auditor retains a union of dependencies and may refuse a case
  whose execution would have separated the entries.
- The MT10 lot covers the carrier's direct relay and waiting by `join()`,
  where the task relays the bearer by a `.await` Internal
  compound results, indirect storage by one argument in another
  load, and calls that directly create an annotated result from a
  Async body remain outside this perimeter. The marker describes a contract
  The actual exclusivity is the annotated body.
- These executions document the scope of the exercise.
  safety remains separate.
