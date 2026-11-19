[Français](ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE-fr.md)

<a id="cycle--contrats-de-vecteurs-complexes-appelés-depuis-async"></a>

# Cycle — Complex vector contracts called since async

<a id="règles-et-portée"></a>

## Rules and scope

ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE.md. H1–H3, VE1–VE4,
B1–B5/B4c, D1–D3, F2–F4, AS8–AS12 remain unchanged.
The guidelines were read before this work. Validation remains focused on
the selected features and their direct regressions.

A synchronous call from an async state must publish the dependencies of objects
a return of extraction must keep the loans
and pools of its load even after destruction of the container. The body of the call
is not re-arcouru by the appellant's analysis; his inferred contracts carry
The C Bridge checks and generates separately the body executed.

<a id="défauts-et-corrections"></a>

## Deficiencies and corrections

The case recorded `open-async-vector-payload-sync-call.crust` appelait put,
then extract a borrowing object n. A destroying variant n before extraction
The disabled programs were not implemented.

- Backend async now publishes `vector_write_payloads` in loans
  stored from the vector, when the call returns.
  retained when an insertion adds alternatives.
- Pools of the descendants possessed are included in the sources retained,
  and their life is verified in relation to the recipient vector.
- The vector parameters borrowed provide their loans to the results of the
  The fields of the descendants owners are covered recursively
  to return their loans to the extractor.
- Bridge C builds a symbolic graph of possible elements, for a
  The first is not arbitrarily read.
  box: the vector can be empty. Real C access is generated during extraction.
- The targets borrowed from this graph remain in the outer scope; they do not
  are not transferred with the container. A first version recorded them
  in a different scope from their connection, detected by verify_state and corrected
  without deactivating the invariant.

The first version only kept the direct fields of a result.
Item owning Inner borrowing n showed the loss of the loan after extraction.
The recursive course corrects this case; the refusal test no longer contains a second
direct use of n which may mask the reason for rejection sought.

<a id="scénarios-exécutés"></a>

## Scenarios implemented

Six targeted methods: **8 executions C**, **11 programmes invalides**, chacun
verified by verify_program and compile_source, which is 22 refusal checks.

- Direct and relay insertion; protected target before extraction and after
  destruction of the vector as long as the object extracted lives.
- Extraction by function receiving vector by &mut.
- Insertion of an object containing &mut Int: read and write competing
  of his refused target.
- Function consuming the vector and turning an element: cleaning the
  container and retention of the item's borrowing.
- Pop by function: Some and None; vector destroyed before match, suspension,
  Result 7 or 0 and release of post-consumer loans.
- Item → A<Inner> → &Int: insertion/extraction by function, reading via a
  helper, two Inner destructions with re-use of a capacity pool 1.
  Early destruction of n and pool Inner too short refused.

<a id="journaux-et-artefacts"></a>

## Newspapers and artifacts

Prefix `validation/async-vector-payload-contracts-` :

- targeted-first-o0: three methods, 1,383 s, failure; expected refusal missing and
  extraction not connected.
- targeted-second-o0: three methods, 1,558 s, failure in the extraction bridge.
- targeted-third-o0: three methods, 2,099 s, success.
- targeted-fourth-o0: same three methods, 1,802 s, success; an error of
  script had prevented the addition of new tests before this execution.
- targeted-fifth-o0: six methods, 3,150 s, failure; fused graph lost and
  Invariant bridge scope.
- targeted-sixth-o0 : **six methods, 3,856 s, code 0**.
- regression-o2 : **270 methods, 269,141 s, code 0** ; list in
  `validation/async-vector-payload-contracts-test-selection.txt`.

C11 harness, pthread, Wall/Wextra/Werrar, fatal UBSan, O0 and O2.
previous life, storage and Select are replayed in regression;
they do not constitute a new model independent of these contracts.
No new mutation campaign, ASan or Tsan.

C and description of the put contract: files `.c` and `-contract.json` Partners.
The contract distinguishes the effect on v, source p and target n.
Snapshot : `/tmp/crust-before-async-vector-payload-contracts`.
Accurate tracks and prints of both modules and test: file `-changes.json`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Local loans are still being joined by field road `[]`, without correlation
The bridge describes a finished graph; the
general recursive compositions remain to be validated and connected.

The return async of an entire vector is the next case:
`validation/open-async-vector-payload-return.crust/.log`. A vector received by
transfer, suspended and then returned via join is still refused to sign the
Two entries. Its rule is already retained; this refusal is a deviation from implementation.

Reset remains withdrawn. The results of this cycle are not a general proof of
The objective remains active.
