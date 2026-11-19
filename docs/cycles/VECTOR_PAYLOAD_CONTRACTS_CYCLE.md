[Français](VECTOR_PAYLOAD_CONTRACTS_CYCLE-fr.md)

<a id="cycle--contrats-des-éléments-de-vecteurs-empruntants"></a>

# Cycle — Contracts for the components of the means of delivery

<a id="règles-et-portée"></a>

## Rules and scope

VECTOR_PAYLOAD_GRAPHS_CYCLE.md suite, according to H1–H3, VE1–VE4, B1–B5,
B4c, D1–D3, F2–F4 and destruction rules. No normative change.
The AGENTS.md and VALIDATION_GUIDELINES.md instructions, the index of the seven
drafts and the relevant rules were read in this session.

This batch connects Vector synchronous parameters<A<Item>> which Item contains
a function can extract references or descendants owners.
an object and return it, insert an object received or built with pools
Injected, or replace an element. The caller retains dependencies from
The complex Option/Result envelopes, vector returns
The projectors are not the only ones who have the same idea of how to use the system.

<a id="implémentation"></a>

## Implementation

- A vector parameter has a symbolic graph of its elements.
  interne `[]/…` means the fields of possible content; it does not introduce
  no new source rating or life-span promotion.
- Results and stress analyses reconstruct active fields
  from the elements still possible. The proprietary fields and targets
  borrowed remain distinct from the vector allocation.
- Transfer contracts add `vector_write_payloads` Inventory
  existing insertions/replacements/deletions: content type,
  source, references and descendants owned. Contracts without graphs
  This information is not unnecessarily provided.
- The application of a contract solves these graphs with actual allowances and
  Checks their destination. The pools of descendants and the targets borrowed
  must survive the recipient vector.
- The descendants of an extracted result are solved **avant** to publish the
  deletion in the vector. Otherwise, the path that allows to find the
  The next projection is wrongly refused.
- Existing rules for returning owner aggregate now recognize
  extraction of a mutable/transferred vector as the owner's source.
  This does not allow the displacement of a field through a shared reference.

Runtime and C representation remain unchanged: objects keep their
The enrichment concerns static and
The native C code is always executed in the intake tests.

<a id="scénarios-ciblés"></a>

## Targeted scenarios

Ten methods, **15 executions C** first via verify_program and
compile_source, and **22 programmes invalides** refused to go to both entrances.
Two additional checks isolated the appellant: one admission and one
refusal, with only contracts and type descriptions, without function body
They are not executions C.

- Extraction and direct return, then additional relays; target remains
  The caller and the empty vector may die before the object extracted.
- Insertion of a fresh allowance from an injected pool, directly and
  via a relay; drop of the rejected target before extraction and before reading.
- Insertion of a transferred handle: mandatory arrow, responsibilities and
  preserved dependencies.
- Mutilated reference stored: read and transfer of the target refused so much
  the vector has yet to be used.
- Insertion from a child's refused scope when its target does not survive
  parent vector, even if the Item pool survives.
- Item owning Inner, which borrows Int: insertion by transfer, return via
  Two functions, downhill reading, single cleaning and re-use of the pool.
- Construction of the same graph in a function with two injected pools; the
  Item, Inner and Int sources are kept separately.
- Conditional insertion using one of two targets: the two variants
  are executed; the contract retains the two possible targets.
- Replacement in a function with valid/invalid index, result consumed
  immediately; the item retained keeps its own loan.
- Pop consumed in function then return of its object: ready kept after
  Out of the arm.

<a id="défauts-rencontrés-et-limites-de-précision"></a>

## Faults encountered and precision limits

The first trial has stopped on the old refusal of the returned owner aggregates
The extractions of elements of the
vectors are now recognized as source of transfer, with the
Field graph expected.

The second trial revealed the incorrect order described above: metadata
Inner were searched after the removal of their entry into the vector.
The result is now resolved before the release of this transfer.
Internal controls on the source and disposition of the fields remain active.

The regression detected two incorrect refusals of returns: the elements
The result contract is now
n-n-n-solved none. Resolution now uses content type
to describe these variants; the control of variants remains active and the
expectations of existing tests remain unchanged.

The roads `[]/…` attach the possible contents; the contract does not claim
maintain all correlations between an index, variant and its references.
A conservative union may still refuse certain valid programs.
proprietary cycles, all enums and all collections projections
are not covered by the scenarios of this lot.

<a id="preuves-dexécution"></a>

## Evidence of enforcement

- First case recorded: code 0, output 7, tracks Item/v/n in
  `validation/vector-payload-contracts-first-o0.log`.
- Insertion and relay: three C admissions and two invalid programmes
  both entrances, `validation/vector-payload-contracts-probes-o0.log`.
  These probations are not added to the accounts of the targeted suite.
- First target O0: seven methods, 4.889 s, code 1, a failure.
- Second target O0: seven methods, 4.889 s, code 1, a downfall failure.
- Target 3 O0: seven methods, 5.649 s, code 0.
- Final target O0: 10 methods, 6,780 s, code 0,
  `validation/vector-payload-contracts-targeted-fourth-o0.log`.
- Regression correction check: 19 O0 methods, 19.768 s, code 0,
  `validation/vector-payload-contracts-corrected-o0.log`.
- First regression O2: 145 methods, 143.117 s, code 1, two incorrect refusals
  on returns replace ; journal `validation/vector-payload-contracts-regression-o2.log`.
- Final Regression O2: **145 methods, 144,001 s, code 0**, selection in
  `validation/vector-payload-contracts-test-selection.txt` and newspaper
  `validation/vector-payload-contracts-regression-final-o2.log`.

C11, pthread, Wall/Wextra/Werrar, fatal UBSan. The failing newspapers are kept.
The source/C/contracts of insertion and extraction are in
`validation/vector-payload-contracts-insert.crust`, `.c` and `.json`.

<a id="suite-et-critères-non-atteints"></a>

## Follow-up and criteria not met

`validation/open-vector-payload-option-contract.crust` described the next case
valid: return option<A<Item>> directly from a function that receives
The vector. It remains explicitly refused both entries; the associated journal
keeps the diagnosis. This limitation is an implementation step, not a
New normative rule. Result signatures and vector returns
whole complexes also remain to be connected, then catches/results async.

Existing replayed models remain unchanged: eight duration combinations
of interlocked life (one admitted, seven refused) and four storage combinations
(four admissions and four refusals) They do not model the new graphs
vectors.

Reset remains removed from normal profile. No new independent model or
mutation campaign is not added here; the adversarial laboratory requested
The results are evidence for cases
No general proof of security or closure of the overall objective.

<a id="traçabilité"></a>

## Traceability

Snapshot avant lot : `/tmp/crust-before-vector-payload-contracts`.
Accurate Patches and Prints: `validation/vector-payload-contracts-changes.json`.
