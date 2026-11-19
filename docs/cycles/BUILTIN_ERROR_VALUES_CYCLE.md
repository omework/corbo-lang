[Français](BUILTIN_ERROR_VALUES_CYCLE-fr.md)

<a id="cycle--valeurs-derreurs-builtin-dans-les-contrats-et-les-tâches"></a>

# Cycle — builtin error values in contracts and tasks

<a id="portée-normative-et-changement"></a>

## Normative scope and change

This cycle applies F2/B5, F5, VE4, TX4 and AS2/AS8/AS10/AS12 with RT5/RT6.
The rules remain those of LANGUAGE_RULES.md and its extensions.
AGENTS.md, VALIDATION_GUIDELINES.md, index of drafts and points
No new semantics or reset reintroduction.

The Counter-Example `validation/open-async-read-error-binding.crust` lie
Error, explicitly consumes this error and returns -1.
refused by the reason check; he now executes with -1.
The limitation was not only syntactic: the analyses of results,
of constraints and effects assimilated several errors to their value of
They now produce the type of error without storage dependency.

Integrated Types : ReadError, CapacityError, ByteReplaceError, CharAtError,
CharFromStrError, IntegerConversionError and SliceError. Variants already
APIs are recognized as values. Links, copies,
reassignments, if/loop/match results, drop, sync signatures, captures and
Async returns retain their nominal type. The same integer C does not constitute
not a conversion between Crust types. Join fields are dedicated and the
business load remains separate from running status::Start error.

Error extracts the exact status, including after a specific error arm.
The parser then develops the only remaining variants as for Err(_),
with separate AST bodies. The completeness and type checks remain
a calculated match subject is materialized once before the arm,
even when it suspends. Meter tests check this property.

A C detail generated has also been corrected: the handle named d'une
immediately destroyed allowance was sometimes unused, destruction
using the internal name of the allowance.
Drop, without adding destruction or deactivating the compiler C warning.

<a id="scénarios-oracles-et-contre-exemples"></a>

## Scenarios, oracles and counter-examples

The final module `tests/test_builtin_error_values.py` contains 14 methods,
60 native executions and 61 refusals expected by complete passage.
independent of seven types and thirteen variants determines expected outputs;
it does not matter the compiler's internal codes.
by capture and return, with sync or async observation. Seven results
are also extracted by await from a handle in an async parent.

Thirteen operations cover EOF, capacity and Io, replacement d í byte,
decoding, conversion and cutting. The first variants are included in order to
that an erroneous status is not masked by the last branch of a game.
Saturation actually uses a 1M region. An error is read after
drop the Result, after suspension and after drop/reuse of source storage.
The result of the error must not be taken to the value of success.

The nominal matrix contains 42 pairs of incompatible types.
refusal to convert to Int, read after drop, bad returns,
catches or contracts, and incomplete, duplicated or incompatible reasons.
The envelopes of join are tested successfully and EAGAIN injected.
13 variants and types pairs constitute a finite exploration;
not a general proof of the type system.

The initial logs are kept. Seven executions had failed on
The warning C of the immediately destroyed handle; the issue was corrected.
An initial test also attempted to drop a Result of the parent scope directly
in the child's arm: this scenario was invalid according to the scope rule.
It is replaced by an error extraction followed by drop in the scope
The result, then a suspension and independent reading.

<a id="validation-exécutée"></a>

## Validation executed

Clang Homebrew 20.1.3, arm64 macOS, C11/pthread, avertissements stricts,
UBSan fatal to O0/O2 for new tests. The old helpers have their own
own options; CRUST_TEST_OPT does not guarantee their level of optimization.

| Implementation | Result | Trace |
| --- | --- | --- |
| Lot O0 before adding the named residual | 13 methods, 31,875 s, passed | validation/builtin-error-values-O0-final.log |
| Complement extraction sync O0 | 1 method, 1,541 s, passed | validation/builtin-error-values-sync-O0.log |
| Complement extraction sync O2 | 1 method, 2,069 s, passed | validation/builtin-error-values-sync-O2.log |
| Residual supplement named O0 | 1 method, 1,550 s, passed | validation/builtin-error-values-residual-O0.log |
| Final O2 batch and residual reasons | 20 methods, 31230 s, passed | validation/builtin-error-values-O2-final.log |
| Results, vectors, motives, runtime::Error, contracts, constraints and effects | 113 methods, 105,447 s, passed | validation/builtin-error-values-O2-regression.log |
| Imbriqué/business results and UTF-8 views | 38 methods, 55,465 s, passed | validation/builtin-error-values-envelopes.log |
| ABI, tables, borrowings, pools and calculated expectations | 15 methods, 24,034 s, passed | validation/builtin-error-values-abi.log |
| Nouvelles mutations | Five detected | validation/builtin-error-values-mutations.log |
| Changes in replayed business envelopes | Four detected | validation/builtin-error-values-old-mutations.log |

O0 is covered by the initial batch and its complements.
adds an Empty case that was missing from the original oracle.
The final pass must not be retroactively allocated to the first pass.

Mutations erase the status extracted in Vector async, UTF-8 async and
sync, disable the nominal control of the catch and the game error.
The five are detected by semantic assertions.
The old mutation test of catch control is inferred.
was adapted to the enriched guard; his oracle did not change.
Python of modified modules and scripts has succeeded.

<a id="limites-et-travail-restant"></a>

## Limitations and remaining work

This cycle does not generalize all user enums, their borrowings,
their storage in aggregates or all Parametric Results.
historical Utf8Error, whose named variants are not defined in
this catalogue is not artificially added to these seven types.
new public variant n

The next difference is reproduced in
`validation/open-async-vector-remove.crust` and its log: removes an element
Copy in a suspension body is still refused. The program should make 17,
29. The larger work on the
public handles, scheduler, threads, Select, mutex and other lines
N/A of the matrix remain open. Points explicitly carried forward remain
Neither ASan/TSan nor second compiler C nor formal evidence in this cycle.

Update: [ASYNC_VECTOR_REMOVE_CYCLE.md](ASYNC_VECTOR_REMOVE_CYCLE.md)
corrects and executes the above-mentioned counter example. The log of the initial refusal
remains historical.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_builtin_error_values -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_builtin_error_values test_residual_error_patterns -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_builtin_error_values test_async_vector_operations.AsyncVectorOperationTests test_async_vector_results test_residual_error_patterns test_runtime_error_values test_plain_join_contracts test_constraints test_effects -v
CRUST_TEST_OPT=-O2 python3 tests/run_builtin_error_value_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_business_envelope_mutations.py
```
