[Français](ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE-fr.md)

<a id="cycle--retours-async-de-vecteurs-et-dépendances-des-éléments"></a>

# Cycle — Async returns of vectors and dependencies of elements

<a id="règles-et-périmètre"></a>

## Rules and scope

ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md. H1–H3, VE1–VE4,
B1–B5/B4c, D1–D3, F2–F4 and AS8–AS12 remain unchanged.
VALIDATION_GUIDELINES reread; tests focused on selected cases and their
direct regressions, without new adversarial campaign.

A vector transferred as an async result retains the pools of its elements,
their descendants and their borrowings. The end of the state async does not destroy
The same constraints apply after await or join.

<a id="défauts-corrigés"></a>

## Corrected defects

The case `validation/open-async-vector-payload-return.crust` was refused to the
signature. Admission alone was not enough: the receiver lost the sources
then remove it considered it empty. The result storage graph
now includes the virtual path `[]` and his descendants.
extraction from Result restore sources, charges and loans.

The stress analysis also reconstructs the loads of the vector received instead
only keep flattened fields. The Item test with Inner that
borrowed n revealed this loss: the Inner parameter was then refused.
This correction shall retain the graph in the contract checks.

No new metadata of borrowing is added to the runtime.
concern async_lowering.py, async_result_storage.py, crust.py and constraints.py.
No normative rule has been amended.

<a id="scénarios-ciblés-exécutés"></a>

## Targeted scenarios implemented

Ten methods: **9 native performances**, **9 programmes invalides** Controlled
each by verify_program and compile_source, i.e. 18 refusal checks.

- Return via join, result named and then consumed; expected drop of the rejected target.
- Synchronous task factory, then return vector.
- Await in a parent async, suspension and extraction after receipt.
- Return of an empty vector: length zero.
- Mutable field: concurrent reading or writing of target after join refused.
- Element possessing Inner borrowing n; value 7 and exactly an Inner destruction.
- Construction of the vector in the task from injected pools.
- Two successive async transfers with wave and intermediate suspension.
- Items A<Int> without fields: their storage is also retained.
- Result coming out of the pool's scope of its elements: refusal.

C11 harness, pthread, Wall/Wextra/Werrar, fatal UBSan. Targeted pass O0
`validation/async-vector-payload-returns-targeted-fourth-o0.log` ends with
**10 methods, 4.015 s, success**. The first passes of seven methods have
revealed the defect of the Inner descendant; the third passes corrects it.
The small exploratory newspapers first/second/third-o0 do not prove the
level O0: the harness used its O2 fault. The targeted passes have
explicitly fixed CRUST_TEST_OPT=-O0.

<a id="régression"></a>

## Regression

Regression completed: **280 methods, 236,594 s, code 0**, O2/UBSan fatal.
Selection in `validation/async-vector-payload-returns-test-selection.txt`,
exit in `validation/async-vector-payload-returns-regression-o2.log`.
The compiler remained unchanged during this pass. Existing models
The following are the main features of the project:
not a new model independent of the result graph.

<a id="artefacts-et-limites"></a>

## Artifacts and limits

- C of the case of return: `validation/async-vector-payload-returns.c`.
- Snapshot : `/tmp/crust-before-async-vector-payload-returns`.
- Tracks and fingerprints: `validation/async-vector-payload-returns-changes.json`.
- Test : `tests/test_async_vector_payload_returns.py`.

The graph of the elements is conservative by path `[]` and provenance, without
Total correlation index/branche/target. Signatures, catches and envelopes
general asyncs remain to be connected according to their forms. No new model
independent of this graph, no new mutation campaign, ASan or TSan.
The following case is recorded in the
`validation/open-async-vector-payload-handle-return.crust/.log` : a function
receiving runtime::Handle<A<Vector<A<Item>>>>> and returning his join is
refused both entries (form of result of the contract Handle not connected).
It is a gap in implementation, without any further semantic arbitration.

Reset remains withdrawn. These results do not constitute general evidence of
safety and a closure of the overall objective.
