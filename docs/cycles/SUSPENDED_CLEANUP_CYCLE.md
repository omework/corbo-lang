[Français](SUSPENDED_CLEANUP_CYCLE-fr.md)

<a id="sl1--as8as10--nettoyage-généré-aux-points-de-suspension"></a>

# SL1 / AS8–AS10 — Cleaning generated at the suspension points

<a id="portée"></a>

## Scope

This lot continues the [Select internal mechanism]](SELECT_RUNTIME_CYCLE.md).
SL1 requires to keep and then destroy losing states; AS8, L1/L2 and V4
require that resources still alive be distinguished from each suspension.
No normative rules are changed. Select remains unconnected to the parser,
contracts and the source auditor.

<a id="implémentation"></a>

## Implementation

Backend records a separate destruction path for each point
Yield/Wawait. He builds it without consuming normal analysis links.
The paths describe, in this order:

1. The direct child whose result is still expected, when he exists.
2. Own-owner catches already prepared during the assessment of arguments.
3. The scopes are still open, from the most internal to the most external, with their
   Inverse destruction inputs.

The movements and drop-outs already made are taken into account.
imported from a parent scope is cleaned only once.
enveloped only destroys its load on its path of success. A local pool is
closed after the allowance and children who can still use it.
The references have no runtime destroyers that would destroy their targets.

Each generated state provides `can_discard_suspended` and `discard_suspended`.
The capacity is checked recursively on direct children before
consumption of the first state. Cleaning then restores the state slots
Inactive and completed states continue to use their resources
their previous liberation paths.

`task_drop_owned` is an internal primitive C, reserved to the exclusive owner
a tree of direct waits after the revival roads have been revoked.
does not allow to destroy a launched handle and does not add any public cancellation.
The selection runtime can use the callbacks generated without adapter
manuscript for the cases exercised here.

If a suspension point keeps a handle thrown, or waits for a child who
in one can, the prevalidation responds without modifying or releasing the state.
The task can resume normally and satisfy its expectations.
does not dispose of [arbitration pending](../SELECT_LAUNCHED_HANDLE_DECISION.md)
and is not yet a source diagnosis for Select.

<a id="écart-découvert-et-corrigé"></a>

## Difference discovered and corrected

Explicit replacement `a = <- p.new(40)` in an async body was directed
towards scalar analysis and refused as `new_transfer` Not supported.
The backend now recognizes the marker around a construction or
a synchronous call returning an allocation and using the path of
existing replacement: new value evaluated, then destroyed.

The test shall include: `a = <- p.new(read(&a).await)` : at the first stop,
the old allocation exists; the next one, it was destroyed and the
new is possessed. The synchronous call creator with explicit marker is
also executed. Undestructable receiver and loan used after replacement
remain refused by check and compile.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

`tests/test_suspended_cleanup.py` contains ten methods:

- Six branch/point pairs: already destroyed capture, allowances
  local and conditional, replacement and re-use of the entry pool.
- Twelve direct-waiting executions on three levels, with two pools
  local: destruction of the child before the target of the parent he or she borrows.
- Arguments already transferred during a later await, for a synchronous call
  and an async call, then suspension after actual creation of the child.
- Five stop points with downlink, back to the parent, renaming,
  Inactive children and three loop iterations.
- Result `Result<A<Int>, runtime::Error>` still possessed at the suspension,
  successful and refused to submit injected; only one destruction.
- Tree containing a handle launched: negative prevalidation without closure of the
  pool, then recovery, explicit expectation and normal result.
- True selection in C with generated callbacks: the winner provides 9 and the
  loser keeps her local allowance until Select drops.
- Replacement whose calculation borrows the old allowance and suspends;
  synchronous creative call; neighbors refused for mutability and active borrowing.
- Independent model of scopes: lists of living and historical values of
  destructions, 22 scenarios (0/1/3 turns, two branches, each breakpoint).
  He predicts the order of the values destroyed and the number of pool closures,
  without using auditor statements or take-back points C.
- String, Vector<Int> and Vector<u8>, with 1M region and still present in
  The continuation that would use the view
  is not executed; the data is destroyed and their sources closed.

The harnesses that destroy an ongoing instance have only its own
tree; they do not perform this operation on a scheduled task.
preconditions of the internal primitive are not a new source syntax.

<a id="chronologie-et-preuves-exécutées"></a>

## Chronology and evidence performed

Clang C11/pthread, Wall/Wextra/Werrar, fatal UBSan; optimization controlled by
`CRUST_TEST_OPT`. Journaux sous `validation/`.

- `suspended-cleanup-select-initial.log` : seven tests of the Select mechanism
  previous successful at O0, 3,035 s.
- `suspended-cleanup-initial-o0.log` : seven methods, nine subcases in error
  before execution. Fixed fixes: explicit de-reference in the
  Async readings and payload names distinct from previously reported links.
- `suspended-cleanup-second-o0.log` : seven methods, six sub-cases refused on
  `new_transfer`. This is the corrected replacement deviation in the compiler.
- `suspended-cleanup-third-o0.log` : seven methods, two assertions on the label
  diagnostic of anonymous construction. This label is `async allocation`,
  The identity of values and the order expected have not been
  not changed; fixture has been corrected.
- `suspended-cleanup-model-o0.log` : nine methods, even two assertions and
  a scenario of the model rejected for lack of explicit use of `current`. Reading
  The destruction oracle is unchanged.
- `suspended-cleanup-final-o0.log` : nine successful methods, 7,930 sec.
- `suspended-cleanup-complete-o0.log` 10 final methods, 14.782 s, OK.
- `suspended-cleanup-mutations-o2.log` : baseline of ten methods, 11,386 s, OK.
  Eight mutations detected: missing child, omitted prepared catch, order of
  reverse cleaning, hand obligation ignored, child prevalidation omitted,
  status of the inverted result, suspension points combined, lost state slot.
  Temporary copies of the compiler are modified without touching the oracles.
- `suspended-cleanup-regression-o2.log` 47 methods, 30.966 s, OK, with the
  new cleanings, Select, local pools, regions and waiting notifications.
- `suspended-cleanup-fields-o2.log` 42 methods, 42,472 s, OK, covering the
  field covers, borrowed and mutable results, and synchronous factories.
- `suspended-cleanup-async-regression-o2.log` 275 methods, 451.134 s;
  274 successes and a failure of instrumentation described below.
  loaded the old anchor before its correction; the corrected method was
  No single passage of 275 methods without failure
  is claimed.
- `suspended-cleanup-slice-counterexample.log` then
  `suspended-cleanup-slice-final.log` : a test instrumentation was looking for
  the frame statement followed by the switch pc, now also present in
  The two new callbacks. Its anchor now explicitly targets the
  The method is changed to O2 (1,197 s), with the same expectations of
  values and refusal; the control of the anchor's uniqueness is maintained.
- Compilation Python of successful batch files.

These counts overlap and are not separate program numbers.
The first failed passages remain recorded separately from the final versions.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Cleanings are now generated for the points recognized by the backend,
but not all types and control compositions
no formal evidence, new ASan/TSan result or second
compiler C. Destruction of a losing branch with a waiting obligation
remains to be arbitrated; no hidden expectation was introduced.

The source connection of Select, its capture/result contracts and
of the losers, verification of the only expectation, the dimensioning
pools with state retention and interactions with mutex.
Open families of the project are not declared completed by this lot.

The connection review also identifies a requirement for contracts:
a loser may have changed an outside field before suspending.
termination alone is not enough, for a restoration written after yield
The scenario will not be executed.
[open-select-partial-field-effect.crust](../../validation/open-select-partial-field-effect.crb)
must have the drop of `second` : the losing branch stored it in
`view.data`. This is a counter-example to a connection that would ignore the
effects of suspended prefixes, not of a currently accepted program; Select
The compiler has not yet analysed this requirement.
and does not require a change in semantics.
