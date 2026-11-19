[Français](ASYNC_FIELD_APPLICATION_CYCLE-fr.md)

<a id="application-des-modifications-de-champs-après-join"></a>

# Application of field changes after join

<a id="périmètre"></a>

## Perimeter

No modified normative rules. This batch connects part of ST10/ST13,
B1/B2/B4/B5 and AS12/AS13 to executable C programs. An async function
with scalar result or Void can call a synchronous auxiliary that replaces
un champ `&Int` of a structure injected by `&mut`. The new target must be
come from an Int borrowed parameter injected, with a durable Cell descriptor.
Native thread methods and blocks follow this same connection.

The task retains the delayed changes in its static metadata.
Its creation and inactive destruction do not apply any writing.
transmits these metadata to the handle. After join, the dependencies of the carrier
bring together potential final targets and old targets: launch
The lifespan of the new targets is confronted with the scope
a person who is a holder before the publication of these dependencies.
or replaced by a copy to circumvent this verification.

In the async state, a modified field retains the loans of its new targets.
A conditional junction brings together alternatives; a branch without writing
keeps the initial field. The loop covers keep their strict control
and do not implicitly benefit from this extension.
before replacement retains the descriptor of the initial target, recorded
the creation of the state, rather than the current field.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

The programme `validation/open-async-sync-field-replacement.crust`, auparavant
refused, produced now `9\n9\n`. With failure of the first injection,
il produit `7\n` : the initial field is kept.

The audit of the handles reconstructions found a loss of metadata in
the enum game. The program kept in
`validation/counterexample-async-enum-match-field-effect.crust` was accepted
by verify and compiles with a drop of the new target before reading the field.
He was not executed in this invalid state. The match values meeting
now retain deferred changes; program is denied.
The admitted neighbors are running for both variants, in a borrowed match and
The compiler can exclude a known variant: its target is not
The first test was wrongly required to hold it;
his expectation has been corrected according to the actual possible paths.

This static selection also showed an unused C alias in an arm
deleted. The issue now marks alias C as used without changing
the Crust control for explicit use. The consuming form of the test has been corrected
of the `match <-choice` to the existing syntax `match (->choice)`.
Intermediate failures are retained in `async-field-application-enum.log`.

<a id="vérifications-exécutées"></a>

## Audits performed

The tests are in `tests/test_async_field_application.py`. Ils exercent :

- Yield and join followed replacement; launch failure and inactive task;
- drop and mutation of old/new targets before or after destruction
  the bearer, with re-use of the slot;
- target of a child's scope refused after waiting and inactive capture allowed;
- new loan and loan loan issued before replacement, transferred to helper
  which stores the reference itself;
- two successive replacements, conditional branches with or without writing,
  choice of hands of identical or different concrete types;
- match buildin, borrowed/consumer enum match, loop result after continuous ;
- methods, native block and historical reset behind the explicit option;
- explicit refusal of borders which are still unconnected.

The independent retention model has eight scenarios: inactive task
or expected, carrier destroyed or alive, destruction of the old or new
Five programmes are admitted and implemented, three rejected by both entries.
These numbers are for the model, not the total of programs in the whole suite.

Commandes finales :

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_async_field_application -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_field_application test_async_structure_effects -v
```

The 16 methods are increasing to O0 in 22.877 s; the 41 methods are increasing to O2
in 24,375 s. Newspapers: `validation/async-field-application-final-o{0,2}.log`.
Native tests compile with Clang C11, pthreads, blocker warnings
and fatal UBSan. Contract analysis methods are not counted as
The previous models 125/16 cases are taken from the previous models
by the contract module. The Python compilation of the modified files succeeds.

The first regression selection passed 107 methods in 63,316 s, before
correction of the enum match and extension of the conditional branches:
`validation/async-field-application-regression.log`. Final selection
Additional passes 112 methods in 99.794 seconds after all corrections:
`validation/async-field-application-final-regression.log`. It takes over the
descriptors caught, helpers storing references, catches of
structures, hand relays, native blocks, loop references
and local links, and loop outputs in async expressions.
These selections overlap; they do not constitute a global pass of
The patches of both modules since the start of the batch are
retained in `validation/async-field-application-*.py.patch`.

<a id="mutations-et-limites"></a>

## Changes and limits

`tests/run_async_field_application_mutations.py` transfers temporary copies,
without changing the checkout or the oracles. The campaign covers the publication at
The first is the launch, the results of the loop/match, the loans stored, the
initial descriptor and branch without writing. The final log is
`validation/async-field-application-complete-mutations.log`.
Eight mutations are detected; one survives.
missing static refusals and incorrect native exits, including 18
instead of 16 when the old loan uses the current field descriptor.

The mutation abolishing destination control at the join survives the scenario
chosen: verify and compile still refuse to read later with
"borrowed field: target not available". Isolated diagnosis is retained
in `async-field-application-lifetime-mutation-diagnostic.log`. This demonstrates
compensation in this scenario, not the general equivalence of the transfer.
The runner reports a failure when this mutation survives; this result is not
The first mutation of the collection of loop results
survived the chosen if test; loop output test now exercises
ce chemin distinct.

The changes are still open: children's tasks, factories and
synchronous auxiliary handling these handles, direct blinds in the body
async, champs `&mut`, projected or inline sources, aggregate/borrowed results
amending tasks, loop covers modifying fields and
Total correlation of effects with the Ok/Err branches. These refusals are
implementation limits, no new language rules.

No new ASan/TSan evidence, comparison between C compilers
The lot does not cover the costs of the
not all combinations of language and does not end the overall objective.
