[Français](NESTED_FIELD_WRAPPERS_CYCLE-fr.md)

<a id="contrats-modifiant-un-descendant-via-un-emprunt-du-parent"></a>

# Contracts modifying a descendant via a parent loan

<a id="périmètre-normatif"></a>

## Normative perimeter

This lot continues ST6–ST15, B1–B5, D1, T1/T6 and existing effects contracts.
A function can receive the parent by &mut and change a reference in
A<T> descendant. The appellant must apply this amendment to the descendant
The target of the other fields is retained and lifespans verified.
No new language rules are introduced.

The programme `validation/open-nested-field-wrapper.crust`, refused both stages
the previous batch, is now executed. The successive relays, a loan
named of the parent, shared/mutable targets and one source from another
The call is still checked from the contracts.

<a id="implémentation-et-défauts-trouvés"></a>

## Implementation and defects found

Constraint analysis retains the owner and path of a projection
The contract may update this projection and publish
dependencies on the parent's complete paths. The backend uses the
owned fields paths, such as `.inner/.view`, to find their type
and the implementation of the corresponding loans.

During this connection, a conditional replacement lost the initial target:
symbolic children of a borrowed parameter were built without their
The old target could then be destroyed before the transfer
The initial journal keeps the expected refusal missing both
steps; `validation/counterexample-nested-field-wrapper-conditional.crust`
is the minimum variant where the branch does not change the field.
The two outcomes of the contract are now the result of the initial targets.
The disabled C was not executed.
The compiler of the previous batch refused the entire wrapper; this defect was
detected in the current extension before declaring it validated.

In the synchronous caller, the update was then applied to the wrong
level: the nested paths were ignored by the solver intended for the
fields of a single slot. The compiler now travels through the possessed edges,
solves the targets for the type of descendant and prepares the modification of this
last. The previous target is no longer improperly retained after an assignment
certain. Unconnected indirect paths are refused
explicitly, without replacing them with an empty effect.

<a id="vérification"></a>

## Verification

The final targeted suite passes 10 methods to O0 in 14,634 seconds: 17 executions
16 invalid programmes and 32 refusal checks.
`validation/nested-field-wrapper-final-count-o0.log`. The O2 baseline of the
The same 10 methods passed in 14.638 s; the five mutations
are detected by assertions, without survivor in this chosen campaign.
Journal `validation/nested-field-wrapper-final-mutations-o2.log`.

The extended regression went from 153 methods to O2 in 149.359 s, with UBSan.
Journal `validation/nested-field-wrapper-regression-o2.log`. She had been
launched with the first seven methods of the batch; the next three pass
in the final O0/O2 baselines. The command below is now launched
Therefore, 156 methods are included. All processes cited are completed with code 0.
This small sample of mutations does not provide an overall detection rate.

The targeted suite covers:

- the published contract `.inner/.view` and its source of parameter;
- two relays, one borrowed parent named, another source carrier;
- the maintenance of the mutable target and the refusal of premature destruction;
- the conditional variant and the registered counter example;
- Sync/async callers, a failure to launch and re-use the slot;
- an independent model of two edges and three targets: 12 combinations,
  7 admitted executed and 5 refused both stages;
- reading the modified descendant followed by assignment to his brother.

This last scenario detects the mutation `forget_child_targets`, surviving
previous batch. The loss of the child's fields now causes a refusal
The previous finding remains historical, without any
The experience of the project is that it demonstrates the equivalence of this mutation.
stored in `validation/nested-field-wrapper-former-survivor-o2.log` and
integrated into the permanent campaign.

Native programs use clang C11/pthread, warnings like
errors, fatal UBSan and O0/O2. No results new ASan/Tsan. Trials
The oracle of valid/refused cases has not been kept
weakened to bypass defects.

Commandes finales :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_nested_field_wrappers.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_nested_field_wrapper_mutations.py
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_nested_field_wrappers test_nested_field_replacement test_nested_owned_borrows test_nested_detached_references test_public_structure_handles test_async_execution_arguments test_async_field_application test_async_child_field_effects test_reference_fields test_stored_field_reborrows test_stored_field_reborrow_model test_mutable_field_completion -v
```

<a id="limites-et-suite"></a>

## Limitations and follow-up

The conditional choice between two descendants before the modification remains valid
but refused: `validation/open-nested-field-choice.crust`. The newspaper
`validation/nested-field-wrapper-choice-probe.log` Keeps both diagnoses.
Monitoring must represent several possible projections, without assigning
the change in a certain way to all descendants or forget their
This point remains open, as well as general signatures
and the public API to replace the scheduler.

Update: the choice between descendants is now dealt with in
[NESTED_FIELD_CHOICES_CYCLE.md](NESTED_FIELD_CHOICES_CYCLE.md). Results
The report remains the original campaign.

Tests are neither general proof of safety nor cover
The four differences in the compiler are archived
in `validation/nested-field-wrapper-*.py.patch` since snapshot
`/tmp/crust-before-nested-field-wrapper`. The overall objective remains active.
