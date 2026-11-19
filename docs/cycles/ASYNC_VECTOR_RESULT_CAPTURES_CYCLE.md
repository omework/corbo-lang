[Français](ASYNC_VECTOR_RESULT_CAPTURES_CYCLE-fr.md)

<a id="cycle--captures-et-réceptions-imbriquées-de-result-de-vecteurs"></a>

# Cycle — Entwined vector result captures and receptions

<a id="règles-et-portée"></a>

## Rules and scope

ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md. AS8–AS12, H1–H3, VE1–VE4,
F2–F4, B1–B5/B4c, D1–D3 and T4 remain unchanged.
The rules are published in continuous work;
standards of restitution, provenance and downward transfer were consulted.

A Result transferred in the state of a task can be returned.
a Result envelope; the consumption of the envelopes keeps the sources and
the loans of the charge, as well as its responsibility for cleaning.
by a loop branch or output must not lose this graph.

<a id="défauts-et-corrections"></a>

## Deficiencies and corrections

The case `validation/open-async-vector-result-capture.crust` lost the elements
The trace shows that the jewel was well-invented []; this one
was lost at the branch meeting, which only kept the
common proprietary fields. This meeting now also retains the
metadata of vector elements.

The unpacking of an intermediate envelope only retained direct loans
The loans of the elements and descendants are now returned,
with their paths, during the unpacking, the branch meeting and the
reception of a loop result.

The successive envelope test revealed a second point: the backend async
collected loans by field only for a captured, without doing so
for a proprietary Result. These modes are now supported during the
transfer of the argument to the child task.

No normative or runtime changes; no invariant disabled.

<a id="scénarios-ciblés-exécutés"></a>

## Targeted scenarios implemented

Seven new methods: **9 executions C**, including failure to submit
injected, and **9 programmes invalides** at the two entries of the compiler,
18 refusal checks. Invalids are not executed.

- Capturing a Result after join, return and reception by match.
- Mutable field: drop, read and write incompatible refused after receipt.
- Item owning Inner borrowing n; value 7, an Inner destruction.
- Several successive envelopes, with spawn and awaited in the parent task.
- Result reception by if and loop break, with downward transfer
  explicit according to T4; loans retained after receipt.
- Destruction of an inactive task: body not executed, charge cleaned, slot
  capacity 1 reused; two item destructions with new allocation.
- Empty vector: zero length. Second launch failed: early return
  since Err, an item destruction and no standard output.

Harnais C11/pthread, Wall/Wextra/Werror, UBSan fatal. Journaux sous
`validation/async-vector-result-captures-` :

- targeted-first-o0: 25 methods, 10,304 s, failure of the if snippet that omited
  l’injection `first ->;` T4 required. Corrected Snippet, rule retained.
- targeted-second-o0: 25 methods, 10.507 s, success; six new methods
  and 19 methods of previous batches.
- targeted-third-o0: seven methods, 3,275 s, failure of new envelope case
  successive loans; loans absent from the capture of the Result in the backend async.
- targeted-fourth-o0 : **seven methods, 4,013 s, code 0**, after correction.

<a id="régression"></a>

## Regression

Completed: **296 methods, 244.806 s, code 0**, O2/UBSan fatal.
Journal : `validation/async-vector-result-captures-regression-o2.log`.
Selection: `validation/async-vector-result-captures-test-selection.txt`.
The fingerprints of the manifest are confirmed after the pass: compiler and
tests unchanged during its execution. Existing storage models,
life and Select were replayed, without new independent model.

<a id="artefacts-et-limites"></a>

## Artifacts and limits

Snapshot : `/tmp/crust-before-async-vector-result-captures`.
Tracks and fingerprints: `validation/async-vector-result-captures-changes.json`.
C of the direct case: `validation/async-vector-result-captures.c`.
Test : `tests/test_async_vector_result_captures.py`.

The graphs are conservative by road [] and from; this lot n
not a general correlation between indices, branches and targets.
independent model, mutation campaign, ASan or TSan. Existing models
The remaining deviations from the
checklist remains open; these results do not demonstrate general safety.

<a id="prochains-raccordements-et-contrôles-dinventaire"></a>

## Next connections and inventory checks

The following controls were only executed verify_program and compile_source:

- `open-async-vector-result-consumer.crust/.log` : consumption of the Result in
  a task, accepted at both entries; native execution not verified here.
- `open-vector-nominal-reference-payload.crust/.log` and its variant
  `open-async-vector-nominal-reference-payload.crust/.log` : bearing element
  &Point, accepted at both entries; do not prove their native execution.
- `open-inline-struct-vector.crust/.log` : Vector<Point> containing the value
  directly, refused to both entries ("Int Allowance"). VE1 distinguishes
  This support is not a means of achieving this goal.
  not replaced by Vector<A<Point>>.

Accuracy of the following cycle: This historical example also included a copy
implied prohibited by ST17. INLINE_STRUCT_VECTORS_CYCLE.md uses copy(v[0])
and connects the first direct storage perimeter, without replacing this type
by a hand-held carrier.
