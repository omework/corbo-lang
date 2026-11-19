[Français](ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE-fr.md)

<a id="cycle--graphes-des-éléments-de-vecteurs-dans-les-états-async"></a>

# Cycle — Graphs of vector elements in async states

<a id="portée-et-règles"></a>

## Scope and rules

Suite of VECTOR_PAYLOAD_CONTAINERS_CYCLE.md. H1–H3, VE1–VE4, B1–B5/B4c,
D1–D3, F2–F4, AS2/AS5/AS8–AS14 remain unchanged.
VALIDATION_GUIDELINES.md, the draft index and the relevant rules were
This lot connects rules already adopted; no normative change.
Validation follows the listed cases and the regressions directly concerned.

Handlers can capture borrowed field objects and
descendants. The state still uses Cell and destroyers
the metadata added is static; neither the address moved nor the
graph of borrowings added to runtime.

<a id="implémentation"></a>

## Implementation

- The proprietary reference paths also cross the elements of the
  Vector<A<T>>, under virtual projection `[]/`. The practical course of the
  dependencies fall into the actual loads present.
- The contracts for factories and task relays retain these references with
  their mode, as well as the pools of the elements, distinct from the vector pool.
- Backend async keeps loans of the values inserted in the vector.
  Remove/pop transmits them to the extracted load. Replace/try_push describe
  separately loans from the Ok and Err charges; extraction selects the arm.
- The game of an empty option erases the loans from the empty result.
  d − a practically empty vector are absent: a generic contract does not have them
  Don't make up a target at the reception.
- Catches and transfers to a child task keep the same loans.
  An inactive task destroyed cleanses his captures without executing his body.

Local vector graphs are attached in a conservative manner.
does not systematically establish which target has disappeared from a vector still alive.
The tests destroy the vector before verifying the release of the remaining loans.
The overall accuracy per index/branch remains to be completed.

<a id="défauts-rencontrés-et-corrigés"></a>

## Deficiencies encountered and corrected

Only lifting the signature restriction allowed the allowed case to be compiled,
The loans were lost when they were captured and inserted locally.
with early drop or concurrent access to a mutable target were accepted.
The tests have now refused to be carried out at both entrances.

A factory kept the vector pool but lost the one of an element: a
task could get out of the block of this pool. L-inference now includes storage
In contrast, an empty vector was refused by the generic contract,
lack of field target: proven roads are now recognized.

The empty option kept a fictitious loan after match.
Removes. The fields of the Some charge are transmitted to the receiver before consumption.

<a id="tests-ciblés"></a>

## Targeted tests

Twelve methods: **15 executions C**, **18 programmes invalides** checked with
verify_program and compile_source (36 refusal checks).

- Direct owner and manufacturer capture; drop before join refused.
- Local vector then extract element: reading after destruction of vector,
  suspension, cleaning and re-use; drop of target before extraction and after
  destruction of the rejected vector.
- Fields &mut Int in capture and local vector: access to competitors denied.
- Item with Inner borrowing Int: read by a helper and clean.
- Relay of an inactive task: body not executed, two destructions Item with
  Re-use; Target protected until task destruction.
- Vector captured by &mut: extraction after suspension and waiting.
- Pool of elements too short: direct refusal and through a factory.
- Pop then match: the reference survives the destruction of the vector and to yield.
- Replaces with valid/invalid: output 7/8, target of protected result.
- Parent async transferring vector to a child: protected target up to and including wait.
- Direct vacuum vector per factory: length 0, without fictitious dependence.
- Try_push passed: Ok(()) does not retain a fictitious charge, the vector keeps
  the reference of the value actually inserted.

Intermediate fixtures have been corrected: field arrow `<-`access to
down by helper, no double drop and local consumption at the right scope.
The first refusals due to these fixture errors did not prove protection
The final oracles use the same invariants, without weakening them.

<a id="exécutions"></a>

## Implementation

Journaux `validation/async-vector-payload-graphs-*` :

- first-o0: the case admitted historical executed; his first refusal included
  yet a double drop and therefore did not prove the refusal in the right place.
- targeted-first: four methods, 2,783 s, failure; loan losses and fixtures.
- targeted-second: four methods, 2,505 s, failure; fabricated and nested fixture.
- targeted-third: four methods, 2.863 s, success.
- targeted-fourth: eight methods, 3,752 s, failure; element source and pop fixture.
- targeted-fifth: eight methods, 3,805 s, failure; pop fixture out of the right scope.
- targeted-sixth: eight methods, 3,559 s, failure; fictitious loan after None.
- targeted-seventh: nine methods, 4,789 s, failure; attempt to double consumption
  in None, corrected in its existing consumption operation.
- targeted-eighth: ten methods, 5,433 s, success.
- targeted-ninth: twelve methods, 6,270 s, failure; empty vector in manufacture.
- targeted-tenth-o0 : **12 methods, 6,901 s, code 0**.
- regression-o2 : **264 methods, 260,741 s, code 1** ; eight sub-failures of the
  test which was still waiting for the refusal of the four forms of vectors, and two
  sub-failures of a mixed/A fixture prior to the batch.
- baseline-mixed-fixture: same test performed with the compiler snapshot
  before this batch, one method, 0.167 seconds, even two sub-failures.
- corrected-o2 : **14 methods, 11,408 s, code 0** : the 12 targeted methods
  and the two historical methods corrected. The compiler did not change
  between regression and this complement. The first fixture now executes
  its four forms allowed (vacant local pools and captures).
  announces A<Mixed> for its pool value; its model retains the eight
  life provisions and both call routes.

This is a regression supplemented by the replay of fixeds, not
 d
 in the associated test-selection.txt file.

Harness : C11, pthread, Wall/Wextra/Werrar, fatal UBSan, O0 and O2.
Previous models of lifespans (eight provisions) and storage
(four configurations) are included in the regression.
new independent models of async vector graphs. No new
mutation campaign, ASan or Tsan in this batch.

Snapshot : `/tmp/crust-before-async-vector-payload-graphs`. Patches and fingerprints:
`validation/async-vector-payload-graphs-changes.json`The former refusal of
`open-async-vector-payload-graph.crust` remains as historical evidence.

<a id="écart-suivant-identifié"></a>

## Next difference identified

`validation/open-async-vector-payload-sync-call.crust/.log` describes an insertion
by synchronous function called from async. The program allowed and its variant
with premature destruction of the target are currently accepted both
The invalid program was not executed.
vector entries are not yet published in the async state upon return
This correction is still necessary; the lot does not prove
the security of all calls combining functions and async collections.

Async returns of whole containers, nominal references and compositions
general recursives remain open. Reset remains removed from the normal profile.
The overall objective remains active, without a claim of general security.
