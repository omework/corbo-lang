[Français](VECTOR_PAYLOAD_OPTIONS_CYCLE-fr.md)

<a id="cycle--options-déléments-contenant-des-emprunts"></a>

# Cycle — Options for elements containing borrowings

<a id="portée-normative"></a>

## Normative scope

Suite of VECTOR_PAYLOAD_CONTRACTS_CYCLE.md. H1–H3, VE2–VE3, B1–B5/B4c,
D1–D3, F2–F4 and U1 remain unchanged. AGENTS.md and guidelines were
The basics of the vectors and the
The control remains case-based
and direct regressions, in accordance with the user priority.

This batch connects the synchronous parameters and results Option<A<Item>> when
Item has Int references or representative proprietary descendants.
The responsibility for cleaning, the targets borrowed and the sources of the
Items owned survive the return, relay and consuming match.
No change in C representation or runtime.

<a id="implémentation-et-défauts-rencontrés"></a>

## Implementation and defects encountered

The symbolic parameters of options receive their proprietary descendants.
The receipt of an optional result rebuilt since the contract its references,
variants and descendants, in the opaque verifier as in generation C.
Existing destination and disposal controls remain active.

A statically empty result does not receive a fictitious graph.
`[]` d
the absence of a burden, without promotion of an allowance.

The imbricated empty case revealed a refusal in the stress analysis: it
The Som arm was in the direction of the provenances, and then the provenances established None.
required an Inner allowance for an inaccessible call.
is now spread by pop and options contracts.
uses this fact for instructions and expressions.
continue their checks and the bodies of functions are checked with
their symbolic parameters; no borrowing control is removed.

<a id="scénarios-exécutés"></a>

## Scenarios implemented

Seven targeted methods: **13 executions C**, each preceded by verify_program
and compile_source, and **13 programmes invalides** refused by these two entrances.

- Some and None, direct return and relay of a transferred option.
- Drop of the target refused before the game and before use in Some.
- Destruction of the empty vector before consumption of its former element.
- Object borrowing too short a target refused; the pool must survive the
  result transferred to a parent.
- Mandatory arrow, explicit use mandatory, double consumption refused.
- Mutilable reference contained: read or write directly of the refused target
  before the last use of the result.
- Item with Inner that borrows Int: return, relay, read and destroy
  unique; empty variant, including match producing Int.
- Consumer returning the object received or a relief allowance from a
  Injected pool; both paths are executed and protect the target.

Traces check the number of item/inner destructions; small pools
capacity and scenarios of the previous batch are replayed in regression.
Reset remains removed from the normal profile, without reintroduction by this batch.

<a id="exécutions-et-artefacts"></a>

## Executions and artifacts

- Baseline: five methods, 0.013 s, nine expected failures/sub-failures due to
  implementation guards, `validation/vector-payload-options-baseline-o0.log`.
- First attempt: five methods, 2,868 seconds, two failures (guard of the descendants and
  fictitious dependencies of None), `vector-payload-options-first-o0.log`.
- Second: five methods, 3.882 s, code 0.
- Third: seven methods, 4.751 s, code 0.
- Added the embedded empty case: seven methods, 5,209 s, code 1; log
  `vector-payload-options-final-o0.log` retained despite its historical name.
- After correction: seven methods, 5.326 s, code 0, journal forth.
- Final Target O0: **seven methods, 5,724 s, code 0**,
  `validation/vector-payload-options-targeted-final-o0.log`.
- Regression O2: **152 methods, 150,976 s, code 0**, selection
  `validation/vector-payload-options-test-selection.txt`, journal
  `validation/vector-payload-options-regression-o2.log`.

C11, pthread, Wall/Wextra/Werrar and fatal UBSan. The case previously refused
`validation/open-vector-payload-option-contract.crust` is now executed
The old newspaper is still a historical proof of refusal.
The C and the current summary are archived in `validation/vector-payload-options.c`
and `validation/vector-payload-options-contract.json` : the item result keeps
`.value -> v[]/.value`, and the deletion of the last element.

Snapshot avant lot : `/tmp/crust-before-vector-payload-options`.
Accurate tracks and prints of both modules and test:
`validation/vector-payload-options-changes.json`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Options containing typed nominal references, cycles and all
The correlations of variants/provenances are not declared covered.
Conservative unions can still refuse valid compositions.
Trade Result of borrowing charges, returns of entire containers
and their integration async remain open. The next minimum case is
`validation/open-vector-payload-exchange-contract.crust` ; both entries
yet explicitly refuse it, a kept associate newspaper.

Existing models have been replayed: eight life combinations
interlocked (one admitted, seven refused), four storage combinations
(four admissions and four refusals) Their predictions remain unchanged.
No new independent model or campaign of mutations; these models
do not prove the options graphs. No result is presented as general proof of
or as a closure of the overall objective.
