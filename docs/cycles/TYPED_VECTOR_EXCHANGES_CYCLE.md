[Français](TYPED_VECTOR_EXCHANGES_CYCLE-fr.md)

<a id="résultats-typés-de-replace-et-try_push"></a>

# Typical results of replace and try_push

<a id="réalisation"></a>

## Implementation

VE3–VE4, H1–H3, U1, F2–F4 and B1–B5 now apply to the results
Vector<A<Point>>, Vector<A<String>> and vectors of
Vector's handle<Int>/Vector<u8>. No regulatory rule is amended.

`handle_exchange_types.py` recognizes and builds both forms:
`Result<A<T>,A<T>>` for replacement and `Result<(),A<T>>` for try_push. Type T
is kept by the parser, contract analyses, symbolic parameters,
the extraction of arms and the junctions of results.
signature also checks that its load belongs to the supported types.

Both arms keep their sources and identities separately.
per parameter can return your handle without confusing local storage and pool.
Storage of an A<T> load is known to be from a pool; an annotation
local T cannot convert it implicitly. C always uses
VectorHandleResult and Cell* : the static type does not change their layout.
Dry_push cleaning remains conditioned by the presence of the rejected handle.

Temporary refusal to replace/try_push non Int is withdrawn. However, a
signature async of these new results still gets an explicit diagnosis
of unconnected functionality, before any attempt at runtime envelope.
Historical Async signatures with A<Int> charge remain in charge.

<a id="validation-ciblée"></a>

## Target validation

Nine methods in `tests/test_typed_vector_exchanges.py` implement 30 programmes
natives and nine invalid programs at both entries, verify_program and
compile_source.

- replace: invalid success and index, direct result, named, annotated or moved.
- Functions: return result, relay, consumption of an injected result and
  The hand of each arm is restored.
- Direct cleaning with drop, result of if and loop/break.
- Immediate consuming match, as well as deferred processing of the named result.
- String and digital vectors: typed load returned, read, destroyed and then
  re-used slots, for both re-placement exits.
- try_push: success and refusal to the real limit of a region of 1 Mio, contract,
  relay, match and direct destruction of result. Filling boxes
  use Point; the number is calculated with the host pointer size.
- Return of the only durable arm beyond the scope of the other pool; variant
  replacing the durable source with the rejected short pool.
- Refusal of the arrows absent, result without use, double consumption, annotation
  bad result/type, owner pattern ignored and local annotation T
  applied to an A<T> handlet extracted.

The unique exits and destructions of the named Points are controlled; pools
with one/two capacity are reused after cleaning. No new search
a profound adversary, random generation or campaign of mutations.
Targeted tests use C11/pthread, Wall/Wextra/Werrar, UBSan and
`-fno-sanitize-recover=all`. A sanitizer diagnosis makes the test fail.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_vector_exchanges -v
```

`validation/typed-vector-exchanges-targeted-sixth-o0.log` : nine methods,
11,012 s, code 0.

<a id="régressions"></a>

## Regressions

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
 test_typed_vector_exchanges test_typed_handle_vectors test_storage_requirements \
 test_async_handle_vector_replace test_async_handle_vector_try_push \
 test_async_handle_exchange_calls test_async_handle_exchange_results \
 test_async_exchange_join test_async_nested_exchange_join -v
```

`validation/typed-vector-exchanges-regression-o2.log` 78 methods,
86,134 s, code 0, O2/UBSan. Regressions retain failures in particular
Injected runtime and historic interlocked Int-charged async envelopes.
They do not yet validate the same envelopes for the new charges.

<a id="traces-de-développement"></a>

## Development traces

- `validation/typed-vector-exchanges-first-o0.log` : the Item programme before
  refused to execute after propagation of the type in the local envelope.
- `targeted-o0` : native programs pass; the oracle of a refusal expected
  A different wording than "expected mode". He now checks this actual diagnosis.
- `targeted-second-o0` : the new snippets of increasing loads
  redeclared a name; separate names added without changing expected values.
- `targeted-third-o0` : eight methods pass, 10.462 seconds.
- `consumer-first-o0` : storage of a load from a non-parameter result
  connected; corrected in the analysis of storage requirements.
- `targeted-fourth-o0` : the symbolic parameter of the backend did not indicate the
  type of his pool; corrected. A negative test construction had not changed
  the snippet targeted and corrected.
- `targeted-fifth-o0` : the historical return `-> <- Point` accept one more
  The difference in the difference between the T/A<T> and the T/A<T> is not resolved.
  The accepted program is kept separately (see below).
  The targeted suite also controls the explicit annotation `let local:Point=<-n`,
  which is refused; this separate test does not replace the missing check
  No normative rules are amended to allow the case.
- `targeted-sixth-o0` : nine methods pass, with extraction from parameter
  and refusal of implicit conversion of storage by explicit annotation.

The initial programme is retained in `validation/open-typed-vector-exchange.crust` ;
his old diagnosis is kept in the homonymous log. The C now generated
is `validation/typed-vector-exchange-point.c`. Differences with backup
before this lot are archived in `validation/typed-vector-exchanges-*.patch`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The distinction between returns from local T structures and allocations A<T>
is not systematically imposed by the old signatures `-> <- T`.
The case observed in this batch is kept in
`validation/open-plain-structure-return-from-handle-result.crust/.log` : accepted
at both entrances despite its return Point containing an A<Point>. V1/T6 and H1
keep the distinction of types; current acceptance is not authoritative
This signature control has yet to be completed.
the lifespan of the product remains monitored in this case, but this does not prove compliance with the
The nine refusals counted do not cover this open gap.

Async/runtime results typed beyond A<Int> and loads containing
The fields owned or borrowed remain to be connected.
cover not all interlocked enums, structures or containers.
`Option<A<Point>>` since one function is still refused: program and diagnosis
in both entries in `validation/open-typed-vector-option-contract.crust/.log`.
This refusal is the next implementation gap, not a normative restriction.

The cases carried out give local evidence; they do not prove the safety of the
The independent audit is separate and still to be organised
with the other agent in the subsequent pass requested by the user.
