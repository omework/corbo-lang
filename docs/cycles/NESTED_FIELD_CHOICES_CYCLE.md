[Français](NESTED_FIELD_CHOICES_CYCLE-fr.md)

<a id="choix-entre-plusieurs-descendants-empruntés"></a>

# Choice between several borrowed descendants

<a id="règles-et-portée"></a>

## Rules and scope

This lot applies the connection rules, B1–B5, D1, ST6–ST15 and the contracts
a mutable reference may designate a chosen descendant
by if or by a loop result. Change your field only changes a
the contract must contain the possible effects and
keep the old target of each location that may not be selected.
Two branches designating the same location allow for a certain replacement.
No new normative semantics are added.

`validation/open-nested-field-choice.crust`previously refused, is accepted and
The following checks the two choices to the execution, the published effects by the
field, mutable references and a choice between an integer and a descendant.

<a id="implémentation"></a>

## Implementation

Symbolic values keep alternatives to wearer and projection.
The fusions of if, loop, match and environment preserve them.
An update separately analyzes each alternative from the input state,
then gathers the states obtained. It does not apply the successive writings
The additional projections after the selection follow.
The same mechanism. The same alternatives are deduced.

The analysis of results and constraints each keep this track.
The fusion utility of the reference values is shared with the tables,
This is why the specific regression of this subsystem is the result of which the structures possessed
remain stable in memory; no allocation displacement is introduced.

The backend also recognizes the unchanged alternative of a mutable field: the
capacity of the same field is not a new local escape target.
This exception requires the exact identity of the carrier and the destination path.

<a id="contre-exemple-trouvé"></a>

## Counter-example found

During connection, `verify_program` accepted the destruction of first
before waiting for a task, while `compile_source` refused the program.
The contract kept it well `.inner/.view`, but his resolution at the appellant
opaque was looking for dependency on the parent instead of the descendant.
This disappeared from the obligations applied.

The programme is retained in
`validation/counterexample-choice-sync-first.crust`. Both stages refuse to do so
Now. Resolution goes through the source of the intermediate carrier,
then solves the terminal field with the appropriate type and capabilities.
The invalid C was not executed.
resolving returns with an incorrect intermediate type refused cases
The journal of the second suite keeps this failure.

<a id="preuves-exécutées"></a>

## Evidence

The targeted suite passes 11 methods to O0 in 17,777 s: 17 native executions,
15 invalid programs and 30 refusal checks.
`validation/nested-field-choice-count-o0.log`.

The independent model calculates the targets still available depending on whether the
branches refer to the same or different children, and then depending on whether
destruction occurs before or after waiting. Its 12 combinations give
7 programs executed and 5 rejected in both stages, included in the numbers
above. Other tests cover synchronous relays, loops,
the repeated writings, the projection of an additional level and both
choices observable in the generated C.

Regression of fixed tables and lines containing references passes
90 methods at O2 in 85,967 s. Journal
`validation/nested-field-choice-array-regression-o2.log`. Elle inclut leurs
List templates and their existing generated scenarios.

Final regression of contracts, structures and async interactions passes
178 methods at O2 in 204,690 s. Journal
`validation/nested-field-choice-final-regression-o2.log`. A first campaign,
launched before the unchanged mutable capacity correction, had completed
176 methods in 200,480 s with this only known failure; his diary is kept
in `nested-field-choice-regression-o2.log`.

The first mutation campaign detects four out of five errors.
the alternatives of stress analysis survive the initial test chosen,
but fails on the complete targeted suite, executed in 14,411 seconds: the mixing case
entire object and descendant is wrongly refused. This existing test is now
The target of this mutation, no oracle was weakened.
`nested-field-choice-mutations-o2.log` and `nested-field-choice-survivor-o2.log`
keep the investigation in validation.

The final campaign increased its baseline from 11 methods to O2 in 10.033 s and
detects the five errors by assertions.
`validation/nested-field-choice-final-mutations-o2.log`. All processes
The final campaigns are out with code 0; the tests are over.
intermediates keep their chess codes, without masking the timeline.

Native programs use clang C11/pthread, O0/O2, warnings
as errors and fatal UBSan. Historical suites require
`CRUST_SANITIZE=undefined`. No new ASan or TSan results are claimed.
A successful campaign does not provide general safety evidence or overall rate
mutation detection.

Commandes reproductibles :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_nested_field_choices.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_nested_field_choice_mutations.py
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_nested_field_choices test_nested_field_wrappers test_nested_field_replacement test_nested_owned_borrows test_nested_detached_references test_public_structure_handles test_async_execution_arguments test_async_field_application test_async_child_field_effects test_reference_fields test_stored_field_reborrows test_stored_field_reborrow_model test_mutable_field_completion -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_fixed_arrays test_nested_reference_rows -v
```

<a id="limites-et-suite"></a>

## Limitations and follow-up

The target unions remain conservative and do not describe all the
The recursive graphs, the
general signatures and unrepresented compositions remain to be audited.
This lot does not claim the full implementation of the seven drafts.

The public interface of the scheduler remains open: RT3 sets the point
and responsibilities, without specifying the type or signatures
A clarification was sought as to the existence of a
more recent arbitration, without blocking self-employment or inventing this API.

The five differences are archived in
`validation/nested-field-choice-*.py.patch` since snapshot
`/tmp/crust-before-nested-field-choice`. The overall objective remains active.
