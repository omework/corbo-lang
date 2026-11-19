[Français](ASYNC_REPLACED_BORROW_RESULTS_CYCLE-fr.md)

<a id="résultats-empruntés-après-remplacement-dun-descendant"></a>

# Results borrowed after replacement of a descendant

<a id="règles-et-défaut-corrigé"></a>

## Corrected Rules and Default

This lot applies the existing rules for return of loan, replacement and
No new semantics are introduced.
A shared reference saved before replacement keeps its old
target. A reading of the descendant after replacement is the new target.
The result borrowed can survive the bearer when its target is outside
and remains valid.

The case recorded is
`validation/open-async-replaced-descendant-borrow.crust`. The previous snapshot
refuses to accept both entries with "projection of the return async: field Int or
The corrected state checks it, produces C and displays 9.

The owner contract followed the new descendant, but the view flattened
the fields borrowed from the parent kept the old projection.
symbol now updates this view when replacing, without changing
The snapshots of the already detached references.
result also crosses the descendants possessed before projecting the field
terminal: it can thus keep the old target of a saved result.

<a id="cas-exécutés"></a>

## Cases implemented

The module `test_async_replaced_borrow_results` has six methods:

- Contracts that distinguish exactly the old target and the new parameter.
- Saved example, with refusal of drop of the returned target.
- Join from hand, for an old or new result; destruction of the wearer
  and the target became useless before reading; failed launch injected.
- Relays by two functions async, yield and successive expectations.
- Conditional replacement: two branches executed and two targets retained
  statically in the contract.
- Result of the Select winner used after destruction of Select and the carrier.

By complete passage: ten native executions, ten invalid programs tested
both entries (twenty refusal checks), plus both contract checks.
The valid programs distinguish 7 for the old loan, 9 for the new one
and 11 for the result of a fail-start.

<a id="résultats"></a>

## Results

- Six methods at O0: 4,968 s, code 0;
  `validation/async-replaced-borrow-results-expanded-o0.log`.
- Six O2 methods: 4.891 s, code 0;
  `validation/async-replaced-borrow-results-final-o2.log`.
- Related regression: 125 methods, 64.791 s, code 0;
  `validation/async-replaced-borrow-results-regression-o2.log`.
  She loaded the first four targeted tests, before the last two were added.
  No change in implementation has been made since its launch; the six tests
  Final Targets cover both additions to O0 and O2.

Native executions use Clang C11, pthread and UBSan without recovery.
Regression includes field effects, proprietary results, fields
mutable, progeny, alternative and synchronous relays.
Other test classes are imported, included in the announced total.

The first draft of the recorded case destroyed from a match arm of the
variables owned in his parent without transfer of input. It has been fixed
to receive the result and then perform the drops in the parent scope.
then reproduced on this case corrected with snapshot
No rules were made more flexible to admit the program.

## Limites

Results are shared references to targets
This lot does not declare all the
mutable results, other types of targets, recursive graphs or any
the forms of factories. Alternatives of launch and branch remain
no new adversarial audit or transfer campaign;
models already included in regressions were executed, without new model
These results are not a general proof of safety.

&mut Int returns from descendants are now connected in the
[Next block dedicated to mutable capabilities](ASYNC_MUTABLE_DESCENDANT_RESULTS_CYCLE.md),
with its own cases and limitations.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_replaced_borrow_results -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_replaced_borrow_results -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_replaced_borrow_results test_async_owned_borrow_writes test_async_owned_field_writes test_borrowed_field_completion test_mutable_field_completion test_async_enum_suspension_fields test_async_structure_effects test_suspension_effects test_owned_results test_nested_field_choices test_nested_field_wrappers -v
```

The last command now includes two methods more than the passage
Snapshot:
`/tmp/crust-before-async-replaced-borrow-results/`Differences:
`validation/async-replaced-borrow-results-results.py.patch` and
`validation/async-replaced-borrow-results-crust.py.patch`.
