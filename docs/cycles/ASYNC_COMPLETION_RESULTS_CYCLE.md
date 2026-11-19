[Français](ASYNC_COMPLETION_RESULTS_CYCLE-fr.md)

<a id="contrats-async--résultat-emprunté-et-champs-modifiés-à-la-terminaison"></a>

# Async contracts: borrowed result and fields modified at termination

<a id="périmètre"></a>

## Perimeter

No rule of law has been changed. This batch completes the analysis required for ST10,
ST11–ST13, B4/B5 and AS12/AS13. A child task can change a reference field
and return a loan. His termination contract must keep both
information, including when the result is the target before writing.
This lot does not lift the backend's refusal for external replacements: their
application to actual statements and appellants remains open.

`AsyncStructureEffects.completion_result` The contract of
result, in addition to the modified fields and the possibility to finish.
Results `&Int`, `&mut Int` and `&mut u8` are collected with the controls
Other families not connected remain reported
as incomplete; they do not become empty contracts.

Waiting for a symbolic bodyless adapter publishes the child's contract
The existing contract engine, which presents the effects and the result
from the same arguments saved at creation.
shared results posted remain distinct from carrier reservations
A handle result keeps its envelope `join_ref`/`join_mut`.
Launch failure contributes to initial field status, but no target
a different task does not create a normal continuation.

<a id="contre-exemple-découvert-par-le-modèle"></a>

## Counter-example discovered by the model

The independent model found a loss of effect in six of its 16
After the `child(v,n).await`, write in `v.spare` reconstruisait parfois
v from the old state of its visible name. `v.data` by
The symbolic call used to use the child's
temporary names saved, whose status had been updated, but his alias
visible had not been.

After the contract has been applied, the fields of the bearer aliases are now
updated from their common symbolic storage before bringing together branches.
The values of loans separated before writing remain snapshots: they
are not replaced by the new field target.

The complete programme is retained in
`validation/open-async-completion-result-and-write.crust` This border is illustrated.
The child contract writes `.data -> n` and returns the old one `.data` ; the
work conserve `.data -> n` and `.spare -> ancienne .data`. The newspaper
`validation/async-completion-results-recorded.log` shows these two contracts and
the retained refusal to compile the complete program. This journal is not a
program execution or evidence of the spread of effects to runtime.

<a id="vérification-exécutée"></a>

## Verification performed

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_async_structure_effects -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_structure_effects -v
```

The 25 methods are increased to O0 in 0.990 s and O2 in 1.403 s:
`validation/async-completion-results-complete-o{0,2}.log`.
Twenty-three methods are concerned with the analysis of contracts, including models; two
execute neighbors supported under Clang C11/UBSan fatal.
The second is waiting for a borrowed result.
then stores it in a local object via a synchronous auxiliary: output 14,
drop of target after admitted join, drop before join refused both entries.
This does not constitute 25 async replacement programs implemented.

The new model has sixteen scenarios: four possible entries
(none, a, b, conditional choice), pre/post-writing result and expectation
a concrete state of two fields provides independently
The 16 summaries correspond after correction.
The previous model of 125 scenarios is also being re-executed.
cover permutations, aliases, loops, task selection and handles, references
mutable, local target refused and aggregate result explicitly not connected.

The first supplement combined two distinct types of inactive tasks in the
one if, which the rules of type refuse. He now uses two catches
different from the same type of task; another case covers two specific types via
The public's common role.
retained in `async-completion-results-expanded.log` and `-model.log`.
The model's failure was not circumvented by a change in expectations.

The campaign `tests/run_async_structure_effect_mutations.py` comprend onze
Targeted transfers: the previous seven and four loss of results, of
reservation of the carrier, instant field or update of aliases.
The eleven are detected in the final pass:
`validation/async-completion-results-complete-mutations.log`.
The stages here concern contracts and their assertions, not eleven defects
memory observed in multithreads programs.

The O2 regression selection of captured descriptors and returns
Async borrowing (fields, direct returns, local connections, games and loops)
passes 73 methods in 65.197 s :
`validation/async-completion-results-reference-regression.log`. This selection
started before final addition of incomplete status for the borrowed results
This guard and its counter-example are included in the final targeted passes.
Selections are overlapping and do not constitute a passage of the whole sequence.

The Python compilation of modified modules and tests succeeds.
module and tests are stored under `validation/async-completion-results-*.patch`.

## Limites

The effects transmitted to a synchronous auxiliary receiving a hand
The results of the study are not explicitly connected.
The contract contains the following statements:
possible after successful or failed launch; it does not yet constitute a
general propagation correlated with the appellant's Ok/Err branches.

Field replacements from the states remain refused by the backend.
The new information must still be attached to tasks and handles,
applied after waiting, and faced with the lifespans of the carriers/targets.
Inline targets without a sustainable descriptor are also open.
No new ASan/TSan evidence, comparison between C compilers
The overall objective remains open.
