[Français](VECTOR_PAYLOAD_CONTAINERS_CYCLE-fr.md)

<a id="cycle--retours-de-vecteurs-contenant-des-graphes-dobjets"></a>

# Cycle — Returns of vectors containing graphs of objects

<a id="règles-et-portée"></a>

## Rules and scope

VECTOR_PAYLOAD_EXCHANGES_CYCLE.md. H1–H3, VE1–VE4, B1–B5/B4c,
D1–D3, F2–F4 and cleaning rules remain unchanged.
The guidelines, the seven drafts index and the rules concerned were
read in this session. Validation remains focused on the features
The results of the survey are based on the results of the survey.

Vector's synchronous returns now retain the graphs of
their components in the factories, relays and transformations tested.
may be new or return a vector received by transfer. The pool of the vector,
The pools of objects and the targets of their borrowings remain distinct.

<a id="implémentation"></a>

## Implementation

- The FunctionResult contract is `vector_values`, inventory of active graphs
  the container returned. The descriptions of existing positions/deletions
  retain their role; virtual paths `[]` do not become fields
  ordinary owners of the vector.
- The inference of results returns these graphs upon the return of a sub-call and
  The references and descendants possessed follow the elements.
- The opaque verifier solves the graphs before publishing the effects of
  The call, then links them to the identities of the elements of the result.
  and targets are controlled at the destination with existing mechanisms.
- Body verification and generation C keep the path graphs
  Returning objects, including when new objects do not receive their identity
  in the course of this verification.
- Constraint analysis links graphs to the identity of the elements
  The re-entry of the land is carried out in the following areas:
  charges, instead of only reporting their direct sources.

Addresses, runtime and C format do not change.
is not modified by this lot.

<a id="tests-ciblés"></a>

## Targeted tests

Nine methods, **12 executions C** after verify_program and compile_source,
and **18 programmes invalides** refused to go to both entrances.

- Manufacture with injected pools and Int reference; additional relay.
- Return of a vector transferred, directly and via a relay; arrow
  mandatory and protection of the target after return.
- Item with Inner borrowing Int: reading the descendant, cleaning and
  Re-use of a Capacity Pool 1.
- Load containing &mut Int: read by the allowed object, read/write
  direct from its rejected target before extraction.
- Pools of vector or its objects too short: transfer parent refused.
- Two conditional returns using a and b respectively: outputs 7 and 9,
  each of the potential targets protected in the appellant.
- Manufactures turning an empty or filled vector: lengths 0 and 1.
- Vector received, old entrance destroyed and then new entrance transferred before
  restitution: value 9 and target of the new protected entry.
- Two elements then deletion of the first before restitution: the second guard
  its reference and target remain protected after extraction.

<a id="défaut-rencontré-et-précision"></a>

## Fault encountered and accuracy

The first essay on the Item/Inner graph failed: stress analysis
created a different result identity from that of the boxes of the
The filter of active loads was therefore lost its graph.
now uses the elements actually described in the storage contract.
Their inherited fields and descendants' references are also resolved.

The graphs may be attached by source where the contract does not distinguish between
Nor are identities. This union is conservative; it does not promise
a complete correlation between each index, branch and target.
Not all cycles or field types are covered by the scenarios executed.

<a id="exécutions-et-artefacts"></a>

## Executions and artifacts

- First recorded case executed: output 7, code 0,
  `validation/vector-payload-containers-first-o0.log`.
- First target O0: five methods, 2,226 seconds, a failure on Inner,
  `validation/vector-payload-containers-targeted-first-o0.log`.
- Second: five methods, 2.630 seconds, code 0.
- Third: eight methods, 5,017 s, code 0.
- Final Target O0: **nine methods, 5.179 s, code 0**,
  `validation/vector-payload-containers-targeted-fourth-o0.log`.
- Regression O2/UBSan: **168 methods, 164,706 s, code 0**, selection
  `validation/vector-payload-containers-test-selection.txt`, journal
  `validation/vector-payload-containers-regression-o2.log`.

C11, pthread, Wall/Wextra/Werrar and fatal UBSan. The programme
`validation/open-vector-payload-container-contract.crust` previously refused
The C and the contract are now being executed; its former newspaper remains historic.
are in `validation/vector-payload-containers.c` and
`validation/vector-payload-containers-contract.json`. The contract separates the
vector source vp, its element source p and the borrowed target n.

Snapshot : `/tmp/crust-before-vector-payload-containers`. Accurate and accurate
prints of the three modules and the test:
`validation/vector-payload-containers-changes.json`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The async catch/results of vectors containing borrowings remain open.
Minimum case `validation/open-async-vector-payload-graph.crust` transfer a
vector to a task that suspends, extracts and reads an Item, and is then expected by
It remains explicitly refused both entries, associated journal kept.
The general nominal references, some consumers of results and the
recursive compositions still require their connection and validation.

Reset remains removed from normal profile. No new independent model or test
The previous regression models do not prove that the
not the new container graphs. The scenarios executed and UBSan are
The overall objective remains active.
