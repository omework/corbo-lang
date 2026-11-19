[Français](TYPED_HANDLE_VECTORS_CYCLE-fr.md)

<a id="vecteurs-de-handles-typés--opérations-synchrones"></a>

# Typed handle vectors: synchronous operations

<a id="périmètre-et-règles"></a>

## Perimeter and rules

This lot applies H1–H3, VE1–VE3, B1–B5, F3–F4 and storage requirements
No regulatory rules are changed. It generalizes the operations
synchronous tests beyond Vector<A<Int>>; it does not end the entire family
Vector<A<T>>.

The parser records the types of hand-held vectors encountered.
contracts for profit, effects and constraints shall retain type T of the
The runtime keeps storing Cells.* ; the pool of each target
ensures its cleanup. No new case layout or target copy is added.

Builder, push, remove, pop local, shared/mutable parameters,
Hands returns, relays and box loans now use
This type. An extraction no longer recreates an Int descriptor for a Point target.
Replacement with a mutable box loan also controls type T.
Non-Int handle slots have a distinct typeofdef to prevent confusion
static with A<Int>, while maintaining the C representation.

Storage tracking recognizes that a target extracted from a Vector<A<T>> comes from
He does not assign this target to a local T structure.
explicite &mut *v retains the candidates from which its elements come.

<a id="cas-exécutés"></a>

## Cases implemented

`tests/test_typed_handle_vectors.py` contains seven methods: nine executions
and nine invalid programs each controlled by verify_program and
compile_source.

- Point: push, remove, pop/some, destroy the vector still filled and re-use.
- Two pools: extraction in order after transfer of vector from a block.
- Functions: Injected insertion, length reading, extraction and relay by
  explicit re-borrowing, with restitution of the A<Point>.
- String, Vector<Int> and Vector<u8>: insertion, extraction, reading of content,
  destruction and reuse of the target pool.
- Typed shared borrowing, content comparison, replacement via a
  mutable borrowing, unique destruction of old and new content.
- Refusal: absent transfer, incompatible type, use after transfer, extraction
  no arrow, destruction of a loan, too short pool, implicit conversion
  Local Point in A<Point>, and extraction during a loan still in use.

Traces verify destruction for the named Points concerned.
a check that slots are actually made available.
selected historical regressions also verify the identity of addresses
for A<Int>; this batch does not claim to test all identities for all Ts.

<a id="résultats-et-reproductibilité"></a>

## Results and reproducibility

Native harness uses C11, pthread, Wall/Wextra/Werrar and UBSan with
`-fno-sanitize-recover=all`. Controlling the return code makes the tests fail
on a sanitizer diagnosis.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_handle_vectors -v
```

`validation/typed-handle-vectors-targeted-fifth-o0.log` : seven methods,
3,782 s, code 0. The last subsequent addition to the compiler is a diagnosis
explicit for replace/try_push typed yet unconnected; final state is
performed by the regression O2 below.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
 test_typed_handle_vectors test_storage_requirements \
 test_async_handle_vector_push test_async_handle_vector_remove \
 test_async_handle_vector_pop test_async_handle_vector_borrows \
 test_async_handle_vector_borrow_returns \
 test_foundation_rules.FoundationTests.test_handle_vector_push_transfers_cleanup_to_vector \
 test_foundation_rules.FoundationTests.test_handle_vector_push_tracks_injected_origins_across_calls \
 test_foundation_rules.FoundationTests.test_handle_vector_borrowed_slot_replacement_tracks_injected_origin \
 test_foundation_rules.FoundationTests.test_handle_vector_remove_preserves_identity_and_frees_origin_after_drop \
 test_foundation_rules.FoundationTests.test_handle_vector_cell_borrows_keep_the_slot_and_its_vector_alive -v
```

`validation/typed-handle-vectors-regression-o2.log` : 59 methods, 45,216 s,
code 0. Async suites, storage and new suite use O2/UBSan.
The five Foundation methods use their native historical configuration
(and their legacy-reset profile explicit), not CRUST_TEST_OPT. Models already
included in selected suites are retained; no new model,
mutation or random program was not added.

The initial programme is retained in
`validation/open-vector-allocated-structure.crust`its initial refusal in the
log homonym, and the C now generated in
`validation/typed-handle-vector-point.c`. Differences with backup
before this lot are archived in `validation/typed-handle-vectors-*.patch`.

<a id="échecs-intermédiaires-consignés"></a>

## Recorded intermediate failures

- `first-o0` : extraction of Some reconstructed in Int, invariant of the source violated.
- `second-o0` First Point programme completed after correction.
- `probes-*` : progression diagnoses, not successful test results;
  parameter typed first unknown, then unconnected storage requirement.
- `targeted-o0` : the re-borrowing lost the origin of the elements; the u8 test
  The snippet was also trying to print it without conversion to Int.
  the explicit conversion retained. The direct import of the harness had executed
  also its 24 Select methods: they passed. The import is corrected for
  Keep the new suite focused.
- `targeted-second-o0` and `targeted-third-o0` : source of the reborrowing, then
  Restriction of the backend on the re-borrowed type, corrected without weakening the oracle.
- `targeted-fourth-o0` : six methods, code 0; `targeted-fifth-o0` ajoute
  borrowing and replacement of typed boxes, seven methods, code 0.

<a id="limites-et-suite"></a>

## Limitations and follow-up

- The typical results of replace/try_push remain to be connected.
  valide `validation/open-typed-vector-exchange.crust` is refused to both
  entries with explicit missing function diagnosis, recorded
  This refusal is a deviation from implementation, not a rule.
- Generic annotations/signatures Option<A<T>> and their runtime envelopes
  are not covered by the local pop of this lot.
- Targets containing proprietary or borrowed fields remain refused
  The vectors still have to spread the metadata of these
  fields. Complex enums and structures are not validated by the Point alone.
- Async operations on these new types are not integrated into this batch.
  The async regressions performed are for A<Int>.
- Handles, interlocking containers of handles, conditional results
  Not all types combinations are covered here.
- No in-depth adversarial research or mutations in this batch, according to
  the user priority. The independent pass will be made separately; none
  The results of this audit are not presumed. The tests are not general evidence
  The safety and the overall construction site remains open.
