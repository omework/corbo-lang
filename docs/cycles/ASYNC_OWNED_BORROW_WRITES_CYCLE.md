[Français](ASYNC_OWNED_BORROW_WRITES_CYCLE-fr.md)

<a id="remplacement-async-de-descendants-contenant-des-emprunts"></a>

# Async replacement of descendants containing borrowings

<a id="périmètre-et-règles"></a>

## Perimeter and rules

This lot connects the already retained field replacements A<T> when T contains
&Int or &mut Int fields. It applies the last life rules, last
use, replacement after evaluation, AS16 and SL1. No normative rules
is not changed; reset remains removed from the prototype. The tests are about cases
The following are the main features of the system:

<a id="implémentation"></a>

## Implementation

Backend async projecting dependencies of the new descendant since
`owned_field_writes` to the common monitoring of the fields borrowed.
the direct transmits the targets of the new object before cleaning up its
Temporary metadata. Sources of allocations and borrowed targets
restent deux obligations distinctes.

A conditional replacement retains the targets of the former descendant when
the contract contains an alternative `owned_field_input`. Contracts suspended
and finished remain distinct: a loser of Select keeps the target already
installed before yield, not the one that would be installed later.

The common solver of the fresh descendants kept their pools but omited
It now solves them from the parameters of the
This correction is necessary for the join
and also benefits from the synchronous contracts concerned.

<a id="exécutions"></a>

## Implementation

- Final target O0: 8 methods, 5.826 s, code 0;
  `validation/async-owned-borrow-writes-conditional-o0.log`.
- This module includes 12 native performances and 13 invalid programs verified
  both entries, i.e. 26 refusal checks by full passage.
- O2/UBSan regression: 127 methods, 65.758 s, code 0;
  `validation/async-owned-borrow-writes-regression-o2.log`.
  This process had loaded the modules before the last conditional adjustment.
- Final verification O2/UBSan after this adjustment: 19 methods, 10,630 s,
  code 0 ; `validation/async-owned-borrow-writes-final-o2.log`. Elle comprend
  the new module, non-borrowing replacements and suspended effects
  The continuation of 127 methods has not been repeated.

Native executions use Clang C11, pthread and UBSan without recovery.
The following are used: auxiliary calls and direct assignments, await, join, failure
Injected launch, Select loser, successive and conditional replacement,
re-use of slots, shared/mutable borrowings, premature drop and scope target
too short. Failed launch retains initial value 7; replacement
realized expounds 9; a second writing after yield exposes 11 only after
terminaison normale.

The first passage revealed the defect of the common solver described above.
The first example of a short scope was refused for another reason: a
allocation `next` The amount of the allowance is not included in the amount of the allowance.
the test to achieve the expected life-time control.
intermediates are kept.

## Limites

The targets in this lot are Int.
nominales](ASYNC_OWNED_NOMINAL_WRITES_CYCLE.md) extend this support to
The recursive graphs and all the
Task factories are not covered here.
It does not provide any information on the extent to which it is possible to achieve its objectives.
general proof of security or independent audit results.
The campaign of mutations or adversarial research is not carried out, according to the
user log; no new independent model is claimed.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_owned_borrow_writes -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_borrow_writes test_async_owned_field_writes test_async_enum_suspension_fields -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_borrow_writes test_async_owned_field_writes test_async_consuming_enum_match test_async_enum_suspension_fields test_suspension_effects test_async_structure_effects test_select_source test_async_owned_struct_returns test_task_result_storage test_owned_results test_foundation_rules.FoundationTests.test_owned_field_preserves_child_borrows_without_destroying_targets test_foundation_rules.FoundationTests.test_borrowed_owned_field_replacement_keeps_alternative_sources test_foundation_rules.FoundationTests.test_nested_owned_field_replacement_joins_child_metadata -v
```

The last order executed 127 methods before the addition of the eighth test; it
Now includes one more. Snapshot:
`/tmp/crust-before-async-owned-borrow-writes/`. Archived differences:
`validation/async-owned-borrow-writes-async_lowering.py.patch` and
`validation/async-owned-borrow-writes-crust.py.patch`.
