[Français](BUILTIN_FEATURES_CYCLE-fr.md)

<a id="cycle--méthodes-intégrées-et-résultats-empruntés-des-type-features"></a>

# Cycle — Integrated methods and selected characteristics

<a id="périmètre-et-invariants"></a>

## Perimeter and invariants

This cycle applies TF1–TF5 to the integrated operations already retained for the
vectors, tables, chains and pools. It does not change their memory rules.
The catalogue `builtin_signatures.py` describes signatures; operations
In practice, their contracts and verifications continue to be carried out.
The effects are not replaced by an abstract contract supposedly neutral.

The Counter-Example `Vector.len()` the previous cycle has been corrected.
common standardization of signatures recognises in particular `&str`, the tables,
the results of the collapse and the handles. `&String` and
`&mut Vector<Int>` are now usable after specialization.
built since a return of `&String` keeps the targets and parents of
the borrowing, including during the assessment of the following arguments.

<a id="contre-exemples-recherchés"></a>

## Counter-examples sought

- A known parser method (`try_slice`, `char_at`, `byte_len`) must not
  not bypass abstract guarantees because it has already been converted
  in an internal operation. The requirements absent are refused in a
  body not called, on a recipient named or provided by a return.
- A method of good name but bad signature does not satisfy a
  feature, even if the body of the function never calls it.
- `push_new` and mutable returns reserve the target until the last use.
- A cut returned by two relays retains the borrowing of the chain;
  and `drop` The first is the "independent" decoded character.
  can be used after the chain has been destroyed.
- Return `identity(&s).try_slice(...)` protect `s` and storage, also
  against a historical reset during the calculation of the next terminal.
  public profile continues to refuse reset.
- A Returning Pool Method `A<Int>` keeps the source through two
  calls. Too short a pool is refused; destruction then re-use retains
  The slot address. `merge` consume and destroy only once its source.
- Byte replacements refusing an invalid UTF-8 result leave the
  unchanged chain. Bad-type parameters and borrowing conflicts
  remain refused after resolution of a feature.

Two defects in concrete support were revealed during this work: the
filter of the types of return refused `&String`, then the construction of a view
Since that return did not materialize its origin. They are corrected and
covered by the minimum cases of `test_builtin_features`.

<a id="exécutions"></a>

## Implementation

Newspapers kept in `validation/builtin-features-*.log`.

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest
  test_buildin_features test_type_features -v` : 32 successful methods,
  15.832 sec. Same as O2: 32 successful, 14.673 sec.
- The helper's native programs use C11, UBSan and
  `-fno-sanitize-recover=all` both levels of optimization.
- The instrumented passage of the only new module is covered by 18 programmes
  compiled/executed and 57 rejected programs, in 16 methods, 7,963 s.
  His independent model lists 36 source signatures (receiver, arguments,
  of which 2 admitted/executed and 34 refused.
  compiler normalizer. These numbers are included in the previous ones.
- Targeted regression contracts, body, pool requirements, shared returns and
  mutables, guidelines, methods and local structures: 173 methods
  successful, 41,763 s, with `CRUST_SANITIZE=undefined`.
- `PYTHONPATH=tests:. python3 -m unittest test_utf8_try_slice
  test_utf8_try_slice_async test_integer_conversions -v` : 32 methods
  successful, 16,412 s. This covers the cutting and conversion paths
  concerned by the pooling of the modes of signature.

Method accounts are not independent property accounts.
Regressions do not cover all the project features.

## Mutations

`python3 tests/run_builtin_feature_mutations.py` uses temporary copies
Four mutations detected:

1. Failure to control the methods already transformed by the
   parseur: methods not guaranteed accepted.
2. Existence of the name used instead of the full signature: the 34
   prohibited signatures of the model are wrongly accepted.
3. Failure to standardize text modes: accepted program rejected
   with `type de paramètre inconnu 'str'`.
4. Clearing the origin of the view built since a return of
   `&String` : `drop` premature acceptance wrongly.

These are targeted errors; no general detection rate is deducted.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The catalogue includes other signatures that do not all have a native test
their presence does not prove that each compound form is
the case `char.utf8_len()` The feature is still to be integrated.
general support for projections, interlocking constraints and async
The diagnosis produced by a function never instantiated
does not constitute universal proof of its memory properties.

A TF2 counter example was reproduced at the end of the cycle: a feature of which
the method takes another argument of the same feature is wrongly substituted
as if this argument were to have the type of receiver.
The correction is the subject of the
There is no blocking normative ambiguity on this point.

Update: this deviation and results of forced methods are corrected
in [NESTED_FEATURES_CYCLE.md](NESTED_FEATURES_CYCLE.md), which adds the
first async-executed interactions.

No formal evidence, new ASan/Tsan campaign or general validation
Multithread is not claimed. Lot 06 and overall objective remain open.
