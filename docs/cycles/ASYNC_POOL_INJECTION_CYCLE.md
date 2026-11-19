[Français](ASYNC_POOL_INJECTION_CYCLE-fr.md)

<a id="cycle--pools-injectés-dans-les-états-async-et-natifs"></a>

# Cycle — pools injected into async and native states

Follow-up: the direct creation of String/Vector<Int/u8> is connected in the
[cycle suivant](ASYNC_COLLECTION_CREATION_CYCLE.md). Other limits of
ce rapport restent ouvertes.

Continue to [SYNC_BOOL_CALLS_CYCLE.md](SYNC_BOOL_CALLS_CYCLE.md). No rules
This lot connects pool loans to contracts and contracts.
states; it does not end all seven drafts.

<a id="périmètre-implémenté"></a>

## Perimeter implemented

- Captures `&Pool<T>` and `&mut Pool<T>` for Int, String, Vector<Int> and
  Vector<u8>. L’ABI transporte un `Source*`, distinct from an allowance.
- Reservation from the creation of the task, kept during its execution
  and until his expectation; release after join or inactive destruction.
  Returned allowance retains pool dependency without retaining
  automatically the exclusive task loan.
- Contract synchronous calls, manufacturing returns a task or a
  handle, child calls, explicit captures in native blocks and
  union of possible sources of the result.
- Direct creation from the injected pool; replacement after
  evaluation, return, yield, break and continuous with cleaning and re-use.
  String and Vector are currently passing through a synchronous factory.
- Named pool borrowings, annotations, last use,
  co-existence of shared loans and refusal of a mutable promotion.

Static pool capture markers are not listed as a
The bridge code does not close the injected pool.
The order of arguments protects a pool prepared during the evaluation of the
the following arguments, including through suspension.

<a id="contre-exemples-et-limites-rencontrées"></a>

## Counter-examples and limitations encountered

Valid case `validation/open-async-pool-helper.crust`previously refused,
The first passages revealed the missing follow-up
aliases named as sources in the effects and their annotation not recognized.
These connections are fixed. An explicitly typed creation String
from a Pool<Int> could be treated as Int by the new path
Direct: it is now refused, with two tests and a dedicated mutation.

Two pre-existing limitations were explicitly retained in the
fixtures: a calculated return owner of a synchronous helper passes through
a named receiver; the observation of address from a state passes through a
Synchronous helper. Failed intermediate logs are not presented
as final successes.

<a id="preuves-exécutées"></a>

## Evidence

Clang C11, pthread, O0/O2, blocking warning and fatal UBSan
(`-fsanitize=undefined -fno-sanitize-recover=all`).

| Passage | Result | Journal |
| --- | --- | --- |
| Module final O0 | 19 methods, 11.501 s, OK | [O0](../../validation/async-pool-current-o0.log) |
| Baseline finale O2 | 19 methods, 16,631 s, OK; 28 executions C, 36 refusals, one verification alone | [Baseline and mutations](../../validation/async-pool-final-mutations-o2.log) |
| Native/Runtime Regression O2 | 162 methods, 177,235 s, OK | [Regression](../../validation/async-pool-regression-o2.log) |
| Contrats O2 | 153 methods, 66,997 seconds, OK | [Contrats](../../validation/async-pool-contracts-o2.log) |

The two extended regressions precede the last nominal type guard;
native regression also precedes the addition of the additional loop test.
The final targeted passages include these additions.
not the full continuation of the project.

Oracles set values, unique destructions, prior identity
and after yield/join and re-employment of the same slot. Two pool candidates test
the accuracy of dependencies; an unturned source may close.
The EAGAIN launch failure does not execute the body and renders the catches.
Existing models of pool and provenance requirements are replayed
No new general model of the scheduler is added.
L’artefact [Crust](../../validation/async-pool-identity.crb), sound
[C generated](../../validation/async-pool-identity.c) and its
[trace](../../validation/async-pool-artifact-run.log) conservent l’observation
d) identity and destruction.

Seven errors injected into temporary copies are detected by the
unchanged tests: nominal type erasing, no reservation side
call, forget about the named loan, convert a shared loan into a mutual,
forgets the child's loan, forgets the fresh source of the result and
re-use of the name transferred to a native block. Chess displayed after
the basic in the journal are the expected detections of mutants.
No general detection rate is deducted.

## Travail restant

Creating local pools in states, creating String/Vector directly
in these states, pools of structures/enums, captures and general signatures
d
public of the scheduler, Select and other obligations of drafts
no results found. ASan, TSan, second compiler or proof
This cycle does not add to the formal safety test.
language and all competing executions.
