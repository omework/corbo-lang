[Français](SYNC_TASK_ARGUMENTS_CYCLE-fr.md)

<a id="arguments-de-tâches-depuis-un-état-async"></a>

# Task arguments from an async state

<a id="règles-et-décision-intégrée"></a>

## Rules and integrated decision

Ce lot applique T1/T6, B1–B5, D1, L1/L2/L6, AS2/AS8–AS15, RT6/RT7/RT8
and SL1: an inactive task is explicitly transferable to a function
The passage does not throw its body. The calle
may return, destroy or transmit it at launch; catches,
sources and dependencies of the result remain monitored by contract.

During this cycle, the user decided on the arbitration of Select: **refuser
in the prototype a branch that can lose with a handle launched again to
attendre**. This decision became SL2 in ASYNC_MULTITHREAD_RULES.md,
referenced in LANGUAGE_RULES.md and draft 04.
SELECT_LAUNCHED_HANDLE_DECISION.md closes this arbitration. No hidden join or
handl's abandonment is not introduced. Arbitration separate from an inactive task
Capturing a launched handle remains open.

<a id="implémentation"></a>

## Implementation

- The symbolic description of a task parameter is shared between the
  body check and deck C. The task remains opaque; the deck described
  The sources of the catches live without reading or executing its state.
  in the outer scope of the bridge, and the task parameter in that of the call.
- Backend prepares the transfer from left to right, invalidates the original name
  and retains loans during the following arguments.
  a separate cleaning element from a Cell allocation.
- A return, break/continue exiting the call or cleaning a suspended condition
  destroys the tasks prepared before the telescopes on which they depend.
  of capacity one and repeat verify the return of the states, not only
  the trace of destruction that could be reproduced by closing the pool.
- The relays keep separately the loans of the catches and those of the result.
  A conditional choice brings together the possibilities. Fields borrowed from a graph
  possessed returned remain attached to their targets after waiting.
- `task_forward_only` is inferred on all return routes. An alternative
  which builds a task makes this fact false, even if another branch makes a
  The context of suspended effects re-uses known catches of a
  pure relay; it does not transform an unknown factory in fact empty.
- Launch helpers can produce public hands already represented
  and practical handles Execution<routine>. For these, the type of
  results and its fields are taken from the definition of routine, including
  for a fresh construction rather than a transmitted parameter.

Fixture `open-async-task-relay-argument.crust` was refused both stages
for signature not supported. `sync-task-arguments-baseline.log` the reproduction
with the snapshot `/tmp/crust-before-sync-task-arguments-current`. Elle compile
Now, print 1 and destroy Inner and Outer exactly once.
source `validation/sync-task-arguments-*.py.patch`.

<a id="vérification-exécutée"></a>

## Verification performed

`tests/test_sync_task_arguments.py` comporte dix-huit méthodes finales. Le
O0 counting of `sync-task-arguments-final-count-o0.log` passes in 8,475 seconds:
24 native executions, 26 invalid programmes and 52 refusal checks
(verify_program and compile_source). Among these methods, one examines directly
contracts for three functions, without native C.

The tests cross:

- Direct relay and interlocked catches owned, shared/mutable borrowings,
  tables, premature destruction, last use and old name consumed.
- Refusal of implicit transfer and of a different routine of the same signature;
  refusal to export a task whose target does not survive the recipient.
- Drop from a helper, repeated re-use of a pool of capacity states one,
  left to right assessment and suspension in a later argument.
- Early return during preparation, two prepared tasks destroyed in
  the reverse order, Select losing and re-use of states after its cleanup.
  The supplement distinguishes break/continue leaving the call and internal break
  the calculation of an argument that allows this call to continue.
- Local or pool-based returns, graphs containing borrowings,
  borrowed public handles and concrete owners handles, with return
  by parameter or fresh construction.
- Choice between two incoming tasks or between an incoming task and a task
  fresh ; union of possible targets before their last use.
- SL2 refusal of `open-select-launched-handle.crust` The cases
  positive use inactive tasks and do not circumvent the obligation
  Waiting for a handle to be thrown.

The first eight methods go to O0, then 14 to O2.
final mutations includes a baseline of 15 methods at O2; both
The 18th method is then included in the final regression.
on break/continue passes separately to O2 in
`sync-task-arguments-loop-exits-o2.log`. Newspapers
The first test of conditional choice remains available.
omits the downward transfer `b ->;` before his drop in the if: this
fixture has been corrected according to the existing rule, without change of normative.

The C harness uses Clang C11/pthread, Wall/Wextra/Werrar,
Wno-unused-function, UBSan fatal to O0/O2. No new results ASan/TSan.

<a id="mutations-et-régressions"></a>

## Changes and regressions

The campaign `sync-task-arguments-final-mutations-o2.log` detects seven errors:
six per assertion and one per compiler crash on a valid program.
The latter removes the invalidation of a task consumed and causes a
KeyError at second cleanup: it is not counted as a semantic refusal
correct d'un programme invalide.

The other six errors remove prepared loans, catch after relay,
loans of the result, cleaning of tasks prepared during a suspension
or early exit, or proof that all returns are relays.
The re-use of capacity one reveals the two state leaks.

The first campaign, `sync-task-arguments-mutations-o2.log`contains a
surviving mutation: removing the capture of a task returning itself
the reference was compensated by the loan of the result.
now uses a task returning Int; loss of capture makes accept
a drop before waiting and is detected at both stages.
initially classified as inconclusive by the runner filter; its classification
No general detection rate is claimed.

The first extended regression went 140 methods in 110.754 s at O2, with
CRUST_SANITIZE=undefined, in `sync-task-arguments-regression-o2.log`.
It covers interlocked contracts and returns of references, handles,
synchronous calls, suspended cleaning, structural effects
The final regression passes 132 methods in 92,121 s, with the same
options, in `sync-task-arguments-final-regression-o2.log`. It includes the
The first seventeen methods of the new lot and the contracts of Select and the
The selections are covered;
their accounts do not add up as unique tests.

The eight historical mutations of the suspended cleaning are detected after a
basic ten methods: `sync-task-arguments-historical-mutations-o2.log`.
All of the final processes cited are completed.

<a id="limites-et-suites"></a>

## Limitations and consequences

`runtime::Handle<View>` for a local structure remains refused by the register
public signatures. `open-public-local-structure-handle.crust` conserve
This valid case, without turning it into a normative ban.
Owner result uses Execution<own> and therefore does not prove the take in
charge of this public signature.
Final refusals of this fixture and replacement of a descending field
are reproduced in both stages in `sync-task-arguments-remaining-probes.log`.

General factory suspension prefixes with an alternative
The effects of a helper waiting or launching a new
The general follow-up of the handles launched, the
signatures and descendants fields still to be completed.
SL2 restriction now has a decision; capture of a handle launched
in an inactive task remains waiting for arbitration. The Scheduler API and
the general placement is not completed. The overall objective remains active.

These completed tests do not constitute formal evidence or cover
exhaustive rules, types or compositions.
