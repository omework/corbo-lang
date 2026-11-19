[Français](ASYNC_DIVERGING_EXPRESSIONS_CYCLE-fr.md)

<a id="cycle--expressions-async-sans-continuation"></a>

# Cycle — async expressions without continuation

<a id="règles-et-changement"></a>

## Rules and change

Application of S4/S5/S5a, B1–B5, D1, AS8/AS10/AS11/AS12 and RT5/RT6, without
ENGINEERING.md, VALIDATION_GUIDELINES.md and the index of the seven
IF_EXPRESSIONS.md specifies that a recipient and its continuation
not produced when all paths leave the function.
S5 control boundaries apply to loop outputs.
previous had produced changes and evidence executed; this cycle
continue the lack that was kept there.

The generator now explicitly represents an expression that does not come back
Not to the instruction that evaluates. It propagates this absence of continuation.
to the border of the instruction, without creating a result, without carrying out its
suite inaccessible and without repeating the cleanings already associated with the exits.
This representation is internal to the compiler; no new type or keyword
The continuing paths remain checked for the use of the language n
their value, type, fashion and dependencies.

Loops whose absence of break results in their receiver may
so return directly from their paths, without intermediate result
The analysis of contracts also stops after an instruction which n
Short circuit operators are represented by their
branches: one branch ignored does not disappear the other path.

`validation/open-async-diverging-initializer.crust` is accepted and executed:
42, 20, 77. Historical refusal remains.

<a id="deux-défauts-trouvés-et-corrigés"></a>

## Two defects found and corrected

<a id="dépendance-fictive-dun-retour-inaccessible"></a>

### Fictive dependence on inaccessible return

`validation/async-diverging-dead-source.crust` always go back a or b since
l’initialisation. Un `return c` then placed is inaccessible, but its origin
The contract was still added. Change c to the appellant before using
The result was wrongly refused. The original newspaper kept this refusal.

The contract now retains a and b, without c. The program runs with
exit 42, 20, 50; premature mutations of a or b remain refused.
The test also covers a block and loop in initialization, with a suite
Inaccessible. Trace corrected: `async-diverging-dead-source-fixed.log`.

<a id="fuite-dune-allocation-préparée-pour-un-appel-interrompu"></a>

### Escape from a prepared allowance for an interrupted appeal

`validation/async-diverging-prepared-owner.crust` moves junk into the first
argument of the future task. The next argument returns from the function.
The task is never created, but the transfer had already emptied access
original. Temporary capture had no cleaning: the re-use of a pool
of capacity one failed with `pool capacity exceeded`.

This defect was observed at execution, then corrected. The compiler follows the
prepared owner catches, with their lexical depth.
which interrupt the call destroy these catches; an internal loop at a
argument can end without interrupting the call encompassing and therefore retains
the case of a owner's Result uses its allocation field,
which can be zero on a failed launch. Cleaning is kept against this
case. Temporary reservations and the stack of arguments are also removed
when the appeal assessment is interrupted.

The corrected trace contains output 88 and 42 and destructions Junk=77,
weld=88, a=42, each one. Both tracks and program are kept.
The runtime has not changed: this patch is about static tracking and C issued.

The C of this counter example is retained in
`validation/async-diverging-prepared-owner.c`. Its cleaning callback
destroyed and emptys the temporary capture prepared. The path that left the
function does not issue any construction call of the abandoned task.

<a id="scénarios-et-modèle"></a>

## Scenarios and Models

The final module `tests/test_async_diverging_expressions.py` compte douze
methods: 42 native executions and 33 refusals expected by complete passage.
These numbers are not an independent guarantee measure.

- All arms come out by break in an initialization, an assignment,
  a nested print or block; the markers of the suite do not run.
- Return from initialization or from a loop, with suspension and
  the two sources of the borrowed result.
- Continue and break in the same expression; independent arithmetic model
  for 1, 2 or 4 increments before output. Native output is compared to the number
  The results of the analysis are not available.
- && & &
  the right result and the two possible sources remain protected.
- Match after wave with all arms leaving the loop; success and EAGAIN
  Injected, suspended in the arms, then used the result.
- Inactive child owner: cleaning once before re-use after join.
- Call abandoned after an argument moved, branch alternative that ends
  normally call, break interrupting call and loop argument that
  does not interrupt it; use of the old access after transfer refused.
- Prepared capture of a owner's Result: success, rejected launch and
  call that ends normally; clean without double destruction.
- Divergent modes, local targets destroyed, worthless break and arms
  continuing worthless remain refused.

The model is finished. It does not establish the general correction of the control of the
flows, sources and cleanings of all aggregates.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| async-diverging-expressions-initial.log | 7 methods, 12.860 s, OK; before discovery of the lost prepared capture |
| async-diverging-expressions-expanded.log | 26 methods, 34,047 s, OK; did not yet prove the leak of arguments |
| async-diverging-expressions-prepared.log | 11 methods, an error on a block used as Int argument; corrected by treating this form via typified block evaluation |
| async-diverging-expressions-prepared-result.log | Test of the prepared Result: 1 method, 1,818 s, OK |
| async-diverging-expressions-O0.log | 11 methods, 25,569 seconds, OK |
| async-diverging-expressions-short-circuit-O0.log | Twelfth method added: 2,461 s, OK |
| async-diverging-expressions-short-circuit-O2.log | Same O2 supplement: 2,250 s, OK |
| async-diverging-expressions-O2-regression.log | 176 methods, 247,789 s, OK, without jump; before adding the short circuit complement, executed separately |

The extended O2 regression is completed, thus the final module is covered at O0
and O2 by the original eleven methods plus the complement executed separately.
`py_compile` The differences between the two documents and the local links of the modified documents have been successful.
compiler is kept in `validation/async-diverging-expressions.patch`.
Native helpers use Clang C11, pthread, -Wall/-Wextra/-Werrar and UBSan
fatal. No leap of method is hidden in the above results.

Commandes reproductibles :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_diverging_expressions -v
python3 tests/run_async_diverging_expression_mutations.py
```

The regression O2 + UBSan loads the modules of this cycle, outputs
expressions, loops borrowed, games borrowed, local connections
async, async returns and synchronous expressions.
the methods of AsyncRuntimeTests containing loop, continuous, break, conditional,
argument, capture or cleanup. His journal provides the exact names executed.
It was launched before the short circuit test was added, performed separately.

## Mutations

| Faute | Observation |
| --- | --- |
| Reintroduce inaccessible returns into contract | Valid program denied due to c |
| Omit cleaning of prepared catches | Pool of capacity one out of stock |
| Clean the catch of the outside call to the break of a loop of argument | Native defect detected after refinement of fault |
| Clear a Returning Origin | Incompatible access to a possible accepted target |

The first change in depth also removed a reservation and made
Fail the compiler with KeyError. The script has ranked inconclusive; this
trace remains in `async-diverging-expressions-mutations.log`. The fault was
refined to preserve reservations and remove only the border of
memory cleaning. It is detected when running in
`async-diverging-expressions-depth-mutation.log`. The other three errors were
No general rates are extrapolated.

<a id="limites-et-suite"></a>

## Limitations and follow-up

A fully non-continuous initialization annotated `[Int;1]` remains refused:
`validation/open-async-diverging-typed-initializer.crust` and his diary.
The annotation must not impose a value that no path
This border of typed links remains to be integrated.

Suivi : [ASYNC_TYPED_DIVERGENCE_CYCLE.md](ASYNC_TYPED_DIVERGENCE_CYCLE.md)
treats this fixture and the annotations recognized by the backend async.
The above limit describes the state at the end of this cycle.

Not all types of aggregates and syntactic positions are
The other obligations of the seven drafts remain open, including:
Scheduler, native threads, Select, mutex and implicit storage. Reset remains removed.
ASan was not restarted after blocking the documented empty C program
No evidence of ASan/TSan, second compiler, formal evidence or
General language safety is claimed. The overall objective remains active.
