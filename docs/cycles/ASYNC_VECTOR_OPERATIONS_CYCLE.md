[Français](ASYNC_VECTOR_OPERATIONS_CYCLE-fr.md)

<a id="cycle--opérations-scalaires-de-vecteurs-dans-les-corps-async"></a>

# Cycle — scalar vector operations in async bodies

<a id="portée-et-décisions"></a>

## Scope and decisions

Implementation of VE3/VE4 with AS2/AS4/AS8/AS10, F4/B4a, B1/B2 and U1,
The reference documents are not amended by regulation.
LANGUAGE_RULES.md, FOUNDATIONS_AND_VECTORS.md and ASYNC_MULTITHREAD_RULES.md.
AGENTS.md, VALIDATION_GUIDELINES.md and the index of the seven drafts were
The current prohibition of reset (PR1) remains.

`pop`, `replace` and `try_push` produisent directement leurs Option/Result
in an async body on Vector<Int/u8>. `try_extend` and `read_fd` operations
on Vector<u8>. The result representation retains the rejected value,
The former value or the appropriate status.
primitives of the runtime already present; no new memory policy.

The recipient is reserved before the arguments. Each argument is evaluated,
then copied into a temporary state before the next.
Surviving suspensions. Mutability, type and use checks
explicit apply also to calls in instruction; a scalar pop
a Rebel Result requires explicit use.

<a id="contre-exemples-modèle-et-observations"></a>

## Counter-examples, models and observations

The programme `validation/open-async-vector-result-producer.crust`, auparavant
refused for expression not supported, now produced `1` then `1`.
The historical log is preserved. The replacement test evaluates an index,
then suspended during a change of this variable: the old index
The transaction remains the same. Delete your snapshot changes actually
the box replaced and failed the test.

Eight families of result are exercised in both of their exits.
A full vectors occupy a region of 1M. An extension of two
Bytes with only one available byte must fail without publishing the first;
The next insertion occupies this last box. Read on the vector
full reports the capacity before the descriptor error. EOF and Io preserve
the length and content existing. This is not a test of all systems
files or all of the d-E/S errors.

Two generated programs (seeds 37 and 91) perform 28 operations each.
A Python list calculates independently the results of push, pop and replace,
including invalid indices; 112 observations of value/length are
The compiler choices are not used to do oracle.

The loans are contested by the self-extension, the call for a task reading
the recipient during the preparation of his arguments and the reuse
d , a slice after mutation. Valid neighbors are executed.
and one slice obtained per await are accepted.
read and drop before join are refused; drop then re-use after join are
Scalar returns do not retain the source vector.

A captured capture is tested on success and launch failure EAGAIN.
The result is read after re-use of the same slot.
counts the entries of the destroyer independently of the list of free slots:
two scenario allocations give exactly two destructions, with the
This instrumentation does not alter decisions
The Court found that the Court had not ruled that the Court had not ruled that the Court had not been able to rule on the grounds that the Court had not been able to determine whether the Court had not held that the proceedings were not based on the facts of the case.

The first tests contained scenario errors: name masking
vector in a pattern, re-borrowed written `&other` for `&*other`, and
re-use of the index of the first sub-case in the second. These errors
were corrected in the tests; the initial logs are not erased.

A genuine independent gap has been minimized in the
`validation/open-read-error-residual-pattern.crust` and its log: the parser
assimile Err(_) to Utf8Error and refuses its association with a variant
ReadError precise. F2 allows the residual arm. This lack remains open;
the capacity test uses explicit variants to check separately
The extension was atomic. No rule was changed to legitimize the refusal.

Update: the next cycle
[RESIDUAL_ERROR_PATTERNS_CYCLE.md](RESIDUAL_ERROR_PATTERNS_CYCLE.md) correct and
validates this residual reason. The historical refusal above describes the discovery.

<a id="validation-exécutée"></a>

## Validation executed

The new final module comprises 15 methods, 35 native and
21 refusals expected. The first 14 methods represent 33 executions
natives ; the instrumented cleaning supplement adds two.
Clang Homebrew 20.1.3., arm64 macOS, C11, pthread, strict warnings and
The helpers concerned comply with CRUST_TEST_OPT for O0/O2.

| Implementation | Result / trace |
| --- | --- |
| Lot O0, before meter complement | 14 methods, 16,238 s, passed; validation/async-vector-operations-O0-final.log |
| Meter and ID O0 | 1 method, 0.754 s, passed; validation/async-vector-operations-cleanup-O0.log |
| Meter and ID O2 | 1 method, 0.808 s, successfully; validation/async-vector-operations-cleanup-O2.log |
| Lot O2 and scalar/business/intermediate results | 64 methods, 104,622 s, passed; validation/async-vector-operations-O2-regression.log |
| Neighbors Thong, slices and collections owned | 31 methods, 50.114 s, passed; validation/async-vector-operations-neighbor-regression.log |
| ABI, borrowings, tables, calculated expectations | 15 methods, 19.995 s, successful; validation/async-vector-operations-abi.log |
| Mutations | Five detected; validation/async-vector-operations-mutations.log |

The five transfers use temporary copies: booking deleted,
deleted instant, replacement load deleted, extension falsely
successfully and keep U1 removed. Each mutation is detected by an assertion
semantics, not by a syntax failure. No survivors in this sample;
no general detection rate is deducted. The runtime itself did not
was transferred into this cycle. Python compilation of modified files was successful.

<a id="limites-et-suites"></a>

## Limitations and consequences

This lot does not cover general proprietary/borrowing items, all of which are
Vector APIs, nor standalone enum errors in async bodies.
The remaining obligations of the seven drafts remain open.
include public handles, scheduler, native thread, Select, mutex and
storage gaps already recorded.
formal evidence or general evidence of safety in this cycle.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_vector_operations.AsyncVectorOperationTests -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_vector_operations.AsyncVectorOperationTests test_async_vector_results test_business_result_envelopes test_nested_plain_results test_plain_join_contracts test_runtime_error_values -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 tests/run_plain_join_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_operation_mutations.py
```
