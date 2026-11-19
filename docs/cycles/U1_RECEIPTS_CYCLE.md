[Français](U1_RECEIPTS_CYCLE-fr.md)

<a id="u1--usage-des-valeurs-reçues-cycle-du-7-novembre-2026"></a>

# U1 — Use of received values, cycle of 7 November 2026

<a id="règles-et-portée"></a>

## Rules and scope

Next to [OWNED_RESULTS_CYCLE.md](OWNED_RESULTS_CYCLE.md), integration of
drafts 01 and 07, without new language decision.
limit more to wrappers Option/Result: ordinary allowances, structures
local areas represented by an allocation, copies of structures, travel,
Await receptions and block/if/loop results are checked.

Un nom `_` is not a valid owner receiver. A prefixed name `_` do not
The use of the product is not required.
exiting a range or replacing an old allowance
The following are not counted as explicit use of this receipt:
content retain their existing behaviour: they use the allowance.
Control of approvals does not change the convention of parameters
and the warning for an abandoned inactive task.

<a id="contre-exemples-corrigés"></a>

## Corrected Counter-Examples

The two programs wrongly accepted in the previous cycle are now
refused: `let unused = p.new(1);` and unused receipt of the result
owner of `f(-> n).await`.

Other cases found during this cycle:

- Reading the old content could misrepresent a replacement
  from a child block, without further use of the new allowance.
- A reading after a second replacement could be attributed to the
  The first reception. An identical name is not enough to prove the use.
- An async reassignment could abandon its new result without use.
- The first async control wrongly rejected a use after a
  expression passed as argument: he did not see the continuation of
  l'instruction englobante.
- It also rejected a use in a subsequent argument.
  count left order → right, including intermediate replacement.

Synchronous verification follows continuations, replacements, arms,
local masking and loop covers. The async keeps the
continuation of instructions and arguments necessary for the same control.
UTF-8 loan analyses keep their normal mode separate from the mode
"use of an owner-receipt"; UTF-8 regression is included.

<a id="modèle-indépendant-et-tests-dédiés"></a>

## Independent model and dedicated tests

`tests/test_owner_usage.py` The model is moving forward in the
order of instructions and opens a new identity of receipt to each
It retains, for each, the existence of an explicit transaction.
It does not consult the compiler's contracts or the generated C.

The alphabet is read, write content, replace and read
conditional. The two-length sequences are crossed with the presence
or the absence of a final drop and the two values of the flag: 64 cases,
of which 42 admitted programmes implemented and 22 rejected programmes.
program admitted, outputs and order of destroyed values are compared to the model.
No seed: the enumeration is deterministic and exhaustive on this small domain.

Other dedicated cases check `_`, prefixed names `_`, structures locales,
copying, allocated chains and vectors, renamings, blocks, loops, reassignment
to a parent, out by await, out of join, masking a name,
continuation after a call and use by the following argument.

Commande standard :

```sh
PYTHONPATH=.:tests python3 -m unittest test_owner_usage test_owned_results -v
```

The two modules bring together 21 methods; the 9 methods of the previous cycle
keep controls on loans, consumer reasons,
ability and re-use. The script `/tmp/crust_owner_usage_optimizations.py`
executes these methods at O0/O2 by keeping clang C11, UBSan and
`-fno-sanitize-recover=all`. Successful final transition: 21 methods to O0
(41.651 s) and 21 to O2 (41.396 s), newspaper
`/tmp/crust-owner-usage-optimizations-final.log`. At each level, the loops
and sub-cases of both modules run 71 admitted native programs and verify
128 rejected configurations. These numbers refer to programs/configurations,
no separate rules or comprehensive coverage.

<a id="régression-et-migration-des-anciens-tests"></a>

## Regression and migration of old tests

First selection: 180 methods (FoundationTests: names containing `handle`,
`consum`, `owned_field` ou `local_structure` ; AsyncRuntimeTests : noms
contenant `owned`), 151,487 s, eight chess and two errors.
`/tmp/crust-owner-usage-regression.log`.

Several fixtures included voluntary unused allowances
or were checking a different diagnosis with another unused allowance.
They have been adapted with an explicit reading or borrowing, without weakening
the diagnosis or re-use checks. The instance kept until the exit
of the `consume` is now explicitly borrowed before the external reset.

An async fixture renames a proprietary result and then transfers it to a
The most recent reception is legitimately changing.
destruction order with the other parameter: the test now checks
the exact trace of this modified program. The separate test of simple renaming
continue to check the order's preservation without this additional transfer.
An invalid loop case now reads the new value before `continue`
to isolate the active loan diagnosis, instead of being also disabled according to U1.

Two passages from 191 methods, including the eleven methods of
`test_utf8_try_slice_async`, revealed the above continuation problems
and the last two fixtures to be adapted:
`/tmp/crust-owner-usage-regression-final.log` (158.144 s) and
`/tmp/crust-owner-usage-regression-paths.log` (162,170 s), each with a failure
and an async error. In the second passage, the 154 synchronous methods are
successful with the analysis of the receptions in place. Both methods async
The following changes are made in 10.836 secs:
`/tmp/crust-owner-usage-async-final.log`.
The last revival of the 37 async/UTF-8 methods was achieved in 79.726 s:
`/tmp/crust-owner-usage-async-regression-final.log`. It includes corrections
The 154 synchronous methods had been
passed in the previous passage; no synchronous code has changed since.
The Python compilation of the modified modules and the three test modules
also succeeds (`python3 -m py_compile`).

<a id="mutations-exécutées"></a>

## Changes performed

Unchanged temporary copies, tests and oracles:

| Mutation | Detection |
| --- | --- |
| Withdrawal of control of ordinary type-approvals | Unused allowances and renamings wrongly accepted |
| Withdrawal of the owner-use control async | Unused receptions and transfers accepted |
| Return to a simple search for the last name used | Another reception or masked name wrongly justifies abandonment |
| Withdrawal of control of async reallocation | New unused allowance accepted |
| Forgetting the arguments that remain to be evaluated | Valid program using the following rejected argument |

The five mutations are detected.
`/tmp/crust-owner-usage-mutations.log` and
`/tmp/crust-owner-usage-argument-mutation.log`.
The last mutant is detected by false refusal, the others by false agreements.
No overall detection rate is deducted from these five selected errors.

## Limites

- The model covers only its small alphabet; it does not prove the safety of
  analysis of uses and all possible compositions.
- Reset tests are those of the explicit historical profile. The public API
  remains removed from the prototype.
- No new ASan, TSan or comparison between compilers C.
- The full audit of interlocked expressions, other forms of reception,
  contract functions and all junctions remain to be continued.
  The proprietary elements of all types of containers are not
  declared to be covered by this cycle.
- Function parameters are not transformed into new links
  their existing consumer agreement is retained.
- This cycle does not end the entire 01 draft or the seven batches of the goal.
  Data stack completes, features type and last set of rules
  runtime/scheduler/Select/mutex remain within the perimeter to be completed.
