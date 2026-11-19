[Français](ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE-fr.md)

<a id="cycle--vecteurs-retournés-par-les-contrats-publics-de-handles"></a>

# Cycle — Vectors returned by public contracts for hands

<a id="règles-et-portée"></a>

## Rules and scope

ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md. AS8–AS12, H1–H3, VE1–VE4,
F2–F4, B1–B5/B4c and D1–D3 remain unchanged.
A runtime::Handle<A<Vector<A<Item>>>>> received by transfer must be capable of being
The returned Result retains the dependencies of its
elements, including after passing through a hand relay.

<a id="écarts-corrigés"></a>

## Adjusted deviations

The programme `validation/open-async-vector-payload-handle-return.crust` was
refused both entries: public form of the result not connected.
Public and Recognition of Results Envelopes Now Accept This
vector load. The symbolic graph of the handle describes the elements via [] and
The projections distinguish between shared loans and the progeny of the
mutable to the elements.

The results of the analysis of provenance and the analysis of the
constraints rebuild the carrier's loads and sources.
by contract and the generation C path keep this same information.
Before this correction, the result was considered empty by removal; then the
path checked by contracts passed while compile_source was still losing
Both entries are now being tested.

Internal control of the source of components of a Result containing a vector
remains active; the historical bypass used for other charges does not
No invariant has been deactivated and no normative rules have been applied.
n , has been amended.

<a id="validation-ciblée"></a>

## Target validation

Four new methods: **4 performances by natives**, **6 invalides** verified
each by verify_program and compile_source, i.e. 12 refusal checks.

- Handle public received by a wait function that returns its join.
- Relay transferring the handle before waiting.
- Item with Inner borrowing n.
- &mut Int: drop, read and write incompatible after wait
  rejected before consumption of the result.

The ten methods of the previous batch are replayed with the four new ones:
**14 methods, 6,200 s, code 0**, O0/UBSan fatal, in
`validation/async-vector-public-handles-targeted-second-o0.log`.
This represents 13 C executions and 15 invalids at both entries in total.
Harnesses C11/pthread, Wall/Wextra/Werrar; invalids are not executed.

First pass: 14 methods, 5.691 seconds, three failures. Two were from the same
test program: text replacement did not insert the anticipated drop
in the handle relay, so the program actually tested was valid.
Generator has been corrected to insert the invalidation case desired, without changing
The third revealed a loss of Inner descendant in the analysis.
It has been corrected.

<a id="régression"></a>

## Regression

Completed: **284 methods, 277,479 s, code 0**, O2/UBSan fatal.
Journal : `validation/async-vector-public-handles-regression-o2.log`.
Selection: `validation/async-vector-public-handles-test-selection.txt`.
The fingerprints of the manifest were checked during this pass: compiler
and tests unchanged. Existing storage models, life and Select
are replayed, without new model independent of the result graph.

<a id="artefacts-et-limites"></a>

## Artifacts and limits

Snapshot : `/tmp/crust-before-async-vector-public-handles`.
Tracks and fingerprints of the five modified modules and test:
`validation/async-vector-public-handles-changes.json`.
The first to sixth logs keep the steps of connection of the minimum case.

The tracking of the elements remains conservative by way [] and from where.
does not validate all envelopes, catches or signatures async.
new independent model, mutation, ASan or TSan. Previous models
are included in the selected regression. Reset remains removed. L
The overall and other deviations of the checklist remain open.

Prochain raccordement reproduit : `validation/open-async-vector-result-relay.crust/.log`.
After waiting, transmit the Result itself to a function that returns it
fails both entries on the inventory of the pools of elements of the contract.
The transfer rule is already retained; this minimum programme has yet to be corrected.
The C of the direct case is retained in `validation/async-vector-public-handles.c`.
