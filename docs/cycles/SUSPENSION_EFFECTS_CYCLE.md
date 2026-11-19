[Français](SUSPENSION_EFFECTS_CYCLE-fr.md)

<a id="sl1--as9--as12--effets-des-champs-aux-suspensions"></a>

# SL1 / AS9 / AS12 — Effects of the fields on suspensions

<a id="problème-et-portée"></a>

## Problem and scope

A branch can write `view.data = next`, suspend, then restore the old
field after its `yield`. If she loses a Select, the restoration is never
The termination contract does not describe the external condition left behind.
after destruction of the loser. The design program remains in
[open-select-partial-field-effect.crust](../../validation/open-select-partial-field-effect.crb).
It is not currently compileable: the source connection of Select remains
This batch prepares this connection without changing the normative rules.

AGENTS.md, VALIDATION_GUIDELINES.md, index and draft 04 were consulted.
The distinction is derived from SL1 and the existing rules of origin and origin.
destruction; no public cancellation or hidden expectation is added.
The old "unimplemented" global entries of LANGUAGE_RULES.md and the
headers of async extensions, regions and UTF-8 are updated in status
The old list
These status corrections do not apply to any of the
Don't change the rules semantics.

<a id="implémentation"></a>

## Implementation

`AsyncStructureEffects` presents two distinct results:

- `completion_result`, used by ordinary calls and expectations ;
- `suspension_result`, describing the union of field targets with suspensions
  atteignables. `may_suspend` distinguishes the absence of suspension from a suspension
  without field modification. `suspension_complete` is independent of `complete`.

The comments are taken at the `yield`, after the previous instructions.
A blind whose right member is suspended shall not be observed until it has been completed.
The expected children transmit their suspended states through their captures
Saved even if they never finish.
parameters do not change these catches. A simple inactive creation
does not perform any effect. A child finished without suspension does not create a point
A fictitious suspension in his parent's home.

The branches and loop covers are combined.
Synchronous auxiliary devices are used without function body.
a child suspended uses a separate environment; it does not replace
the normal continuation state. The results borrowed and their capabilities
remain in the termination contract, separated from the suspended fields summary.

An unsustainable target observed in a field, or a task composition
of which the competing effects are not yet represented,
an unknown suspension summary with reason. This unknown result spreads
The term "parental" is never replaced by an empty summary; the contract of
termination may nevertheless remain available. This does not yet allow
the destruction of a branch with a handle launched.

<a id="scénarios-et-preuves"></a>

## Scenarios and evidence

`tests/test_suspension_effects.py` includes 15 methods:

- Store/restoration before or after yield; function without suspension.
- Inactive child destroyed, child immediately finished, parent suspended.
- Right-hand member suspended before field assignment.
- Choice of tasks with different catches; branch-alternatives unchanged.
- Three levels of waiting, parameter permutation, aliases and masked name.
- Child who hangs indefinitely and neighbouring branch that ends normally.
- Buckles exchanging references, mutable fields and borrowed result.
- Unknown local and propagated abstracts, without loss of termination contract.
- Reference containers whose suspended effects are not represented:
  a guard prevents their missing updates from being presented as an empty effect.
- Independent model of 64 sequences of three actions: writing a, writing b,
  exchange two targets, suspend. Two labels in a list describe
  the concrete state; only breaks add an observation.
  are calculated without the compiler's control values or graph.
- Regular programme completed after full wait: drop of target
  Temporary accepted, read restored target equal to 1.
  Destroying the latter is denied by check and compile.
- Select C probe with frames and cleanings actually generated, eight jobs:
  the winning branch renders 9; the field of the loser keeps the second
  The harness keeps this cell after destruction, with value 2.
  It does not artificially cause access after liberation.

The C probe shows the difference between suspension and termination.
not yet the static refusal of the Select source program, which remains to be connected.

Performances Clang C11/pthread, Wall/Wextra/Werrar, fatal UBSan, O0/O2:

- `validation/suspension-effects-existing-initial.log` 25 methods
  contrats existants, 1,447 s, OK.
- `validation/suspension-effects-initial-o0.log` 19 methods, 11,625 seconds, OK.
  Ten came from an imported class also collected by unitittest.
  was replaced by a module import to avoid doubling this collection.
- `validation/suspension-effects-final-o0.log` 11 methods, 1,136 seconds, OK.
- `validation/suspension-effects-complete-o0.log` and `complete-o2.log` :
  13 methods, 1.645 s and 1.610 s, OK.
- `validation/suspension-effects-final-14-o0.log` and `final-14-o2.log` :
  14 methods, 1.264 s and 1.129 s, OK.
- `validation/suspension-effects-propagation-o0.log` : extension of the test of the
  unknown summaries to parents, one method, 0.008 s, OK.
- `validation/suspension-effects-final-mutations-o2.log` : baseline finale
  14 methods, 1,134 s, OK; seven mutations detected. Are targeted forgetfulness
  Yield, loss of an earlier state, oblivion of child suspensions,
  a invented continuation, confusion of contracts, unknown rendered empty
  and acceptance of an unsustainable target.
  The previous campaign on 11 methods is
  stored in `suspension-effects-mutations-o2.log` (seven detections as well).
- `validation/suspension-effects-contract-regression-o2.log` : 94 methods,
  61,545 s, OK: synchronous results, async contracts, mutable fields,
  borrowed returns, factories and loops.
- `validation/suspension-effects-final-15-o0.log` 15 methods, 1,071 s, OK,
  After adding the guard on the other reference containers.
- `validation/suspension-effects-final-15-mutations-o2.log` : baseline finale
  of 15 methods, 1,128 s, OK; the eight mutations are detected.
  transfer removes the guard on unfollowed containers.
- `validation/suspension-effects-final-contracts-o2.log` 52 methods,
  8,750 s, OK, after adding the guard on the other containers.
- `validation/suspension-effects-legacy-mutations-o2.log` : the eleven mutations
  previous async contracts are detected. Three anchors have been moved
  to the new common point of application of the summaries; that of LaunchFailed
  has been specified to distinguish its two occurrences.
  the expected assertions retain their meaning; no oracle is weakened.
- `validation/suspension-effects-runtime-regression-o2.log` 292 methods,
  524.837 s, OK: 275 of the async/runtime suite, ten of suspended cleaning,
  seven of the Select mechanism. The instrumentation test corrected in the previous batch
  also goes through this complete execution.
- Compilation of successful batch modules and tests.
- Local links of the seven modified documents checked: no missing targets.

The selection of 94 methods and the runtime suite loaded the code before
the final addition of this guard. This only affects the availability of the
new suspension summary; termination contracts and backend do not
The final baseline and contract/result selection are not consumed.
executed on the version containing this guard.

Counts overlap and do not represent separate programs.
The mutation tests that fail are the expected detections, not the
Normal version failures.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The summary covers the fields represented by the existing analysis, in
Int, &Int and &mut Int.
not all aggregates, tables modified to suspensions,
mutex or recursive signatures. Alternatives are conservative,
without a complete correlation between each field and each path.

In order to compose a Select, the future consumer must also consider the
non-polished branches and finished branches: suspension summary
The inference of the competing effects of handles is not the only one that represents these states.
launched and opaque factories remain open, regardless of arbitration
The standard waiting tests remain based on the
termination contracts and are not rendered unnecessarily conservative.

No formal evidence, no new ASan/TSan result, no validation
by a second compiler C. The overall objective remains incomplete.
