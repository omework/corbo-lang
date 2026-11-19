[Français](ASYNC_CHILD_FIELD_EFFECTS_CYCLE-fr.md)

<a id="modifications-de-champs-à-travers-les-tâches-enfants"></a>

# Field changes through child tasks

## Raccordement

No modified normative rules. This lot extends ST10/ST13, B1/B2/B4/B5 and
AS4/AS12/AS13 from the ASYNC_FIELD_APPLICATION_CYCLE.md. Async tasks
and native scalar or Void blocks can now transmit
their changes in shared fields Int through a child expected.

The internal record of a task or a handle carries the alternatives of
The following are the changes, prepared since the arguments captured.
through launch, block transfer, conditional result and exit of
The creation does not publish these changes. A direct expectation of the
applies to the termination; the waiting of a handle also retains the initial state,
Because the launch can fail. Destroy an inactive task withdraws its borrowings
without applying his termination contract.

The published field loans are used for access controls in the parent
and at the choice of the descriptor Cell when a helper stores the loan.
of the parent then keeps the dependencies at his own
The targets are not copied or promoted. Shared source fields
are now resolved since the catches, allowing replacements
The first is the first time that the project has been completed.
All entries in a contract are prepared before publication.

<a id="contre-exemple-confirmé"></a>

## Confirmed counter-example

A child returning Void can change a field despite the absence of a receiver.
`ResultContext.nodes` did not know the AST form `await_statement`. After opening
the connection of the children, the contract of the parent `work` So announced none
effect on `write(v,n).await;`, while the C was executing the writing.

`validation/counterexample-async-void-child-field-effect.crust` reproduit ce cas :
after the parent's join, a drop in the new target preceded a reading of the
field. Verify and compile accepted the program; it was not executed in
This invalid state. `async-child-field-effects-void-before.log`
This acceptance is maintained. The Await instruction now calls the same
expression analysis that expectations with receiver. The journal `-void-after.log`
shows the refusal by both entries. The neighbor without drop runs and the test
explicitly serves as the presence of effect in the parent's contract.

Analysis of the scalar results expected from a handle also lost
The launch result envelope. A match that made his payload was
then described as two branches of different types. `join_int`,
`join_bool`The case of the native
expected and then returned by a match runs without deleting the effects of the field.

Un premier test utilisait `Ok(n)` in a task with a parameter `n` ;
it has been fixed to `Ok(value)`, in accordance with the refusal to mask the backend.
A historical synchronous helper test called by a task was waiting for the
The report states that the situation in the country is not as good as the situation in the country.
normative diagnosis "join reserved for synchronous code"; the deferred summary y
The program has not become accepted.

<a id="couverture-exécutée"></a>

## Coverage

`tests/test_async_child_field_effects.py` couvre :

- three relays, argument swapping, named task and direct wait;
- Inactive child destroyed, then transferred from his permitted capture;
- finished child keeping the reservation of his new target in the parent;
- child launched, Yield, expected result and refusal of injection submission;
- task selection, block transfer and loop result, with direct wait
  or launch, for 12 combinations of shapes and branches;
- former reference detached before waiting, conditionally unchanged field,
  and simultaneous exchange of two fields;
- Child Void and native block expected from a task;
- Childscope target refused, without promotion;
- Independent model of retention with inactive/direct/launched child, carrier
  destroyed or alive and old/new target: 12 cases, 7 executed and
  Five rejected by verify and compile.

Native performances use Clang C11, pthreads, `-Wall -Wextra -Werror`,
Fatal UBSan and explicit compilation/execution time. Simulations of
refusal to launch inject EAGAIN to the selected submission.
Python of modified modules and tests succeeds.

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_async_child_field_effects -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_child_field_effects test_async_structure_effects test_async_field_application -v
```

The eleven targeted methods are increasing to O0 in 31.356 s:
`validation/async-child-field-effects-complete-o0.log`.
The O2 pass that brings together the new module, the contracts and the previous batch passes
52 methods in 57.744 s: `-complete-o2.log`. Final decline in catches
of fields, descriptors captured, public handles and synchronous relays passes
48 methods in 67,462 s: `-final-regression.log`These modules have been loaded
after the corrections to the Void instruction and scalar envelope.

A selection of 75 methods is passed in 131,182 s in
`async-child-field-effects-regression.log` : handles publics, relais synchrones,
results owners, loop references/outputs, divergence and blocks
It had started before the correction of the instruction had been Void and
The first selection of 50 methods of contracts and
descriptors failed only on the expectation of the historical diagnosis described
The final passes replace this evidence for the modules concerned.

The campaign `tests/run_async_child_field_mutations.py` edit copies
temporaires. Elle couvre neuf omissions : instruction await Void, enveloppe
scalar, application after direct waiting or hand, publication at the
creation, initial state over-launch failure, conditional choice, output by
The final log is the seconded reference and descriptor.
`validation/async-child-field-effects-complete-mutations.log`.
The nine mutations are detected in this final pass.
This target sample is not a general detection rate.
An undue rejection of an admitted program is distinguished from an invalid acceptance or
a native bad output; an internal Python error is not enough to
classify the mutation as detected.

Intermediate failures remain in the newspapers `-initial`, `-expanded`,
`-contract-regression` and `-final-o2`. The patches since the start of the batch are
retained in `validation/async-child-field-effects-*.py.patch`.

## Limites encore ouvertes

Synchronous relays of handles carrying field changes are not
not connected. The amending tasks returning a loan or aggregate,
mutable fields, inline/local sources that are unsustainable and blinds
The monitoring of blinds is incomplete.
through a loop recovery and complete correlation to the Ok/Err branches
The conservative union of success/failure can retain the old
Target beyond the only successful path.

The scenarios performed do not demonstrate all the task compositions and
No new ASan/TSan evidence, comparison between compilers
C independent and formal proof.
mutex and general placement remain in the active objective; this batch does not end
Not the implementation of the seven drafts.
