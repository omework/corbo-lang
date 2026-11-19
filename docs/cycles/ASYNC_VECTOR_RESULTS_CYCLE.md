[Français](ASYNC_VECTOR_RESULTS_CYCLE-fr.md)

<a id="cycle-as2rt5rt6--transport-async-des-résultats-de-vecteurs"></a>

# Cycle AS2/RT5/RT6 — Async transport of vector results

<a id="portée-normative-et-implémentation"></a>

## Normative scope and implementation

This cycle applies the immediately selected catch rules AS2, d'attendance AS4,
The results and sources of AS12, of join RT5/RT6 and of U1 use.
vector scalar were already defined and synchronous executable.
No new semantics or normative decisions are introduced.
VALIDATION_GUIDELINES.md, the index of decisions and the relevant clauses are
re-read, in continuity with the full reading of previous cycles.

The Counter-Example `validation/open-async-vector-value-result.crust` run
maintenant : un `Result<(),u8>` can be captured and returned by a task.
Its old log of refusal is kept. Support covers eight families already
existantes : Option<Int>, Option<u8>, Result<Int,Int>, Result<u8,u8>,
Result<(),Int>, Result<(),u8>, Result<(),CapacityError> and Result<Int,ReadError>.

Three existing C representations (status alone, status/int, status/u8) are
moved to shared header. The join result has dedicated fields
The inferred and explicit signatures use the following:
same type modes; envelopes `runtime::Error` peuvent s’imbriquer comme
for previous simple loads. Effects and provenance analyses
extract the right guy at each level.

Async code can copy, capture, receive, return, reassign, destroy
and process these values by match. If branches, loop results and
direct expectations are connected. Option/Result, unit/value
and Int/u8 loads remain separate. In Err d
extraction makes the value rejected; it does not render a runtime::Error.
The borrowed views and the owners are not converted into these modes.

Methods that produce these results directly in the async body
This cycle validates their production
synchronous followed by async transport and treatment, without claiming to cover
the execution of these methods in a task.

<a id="modèle-et-scénarios"></a>

## Model and scenarios

The test table is independent of the internal modes and the generated C. It
sets out the results of eight operations, including the values rejected -23 and 255.
Capacity scenarios actually fill a 1M annotated region:
262144 Int or 1048576 u8. No saturation status is manufactured in the
The Vector source is destroyed after the calculation of the
result, before it is captured by a task.

The 32 main configurations combine eight families, two variants and
one synchronous or after recapture/suspension async, with two
join levels. Sixteen additional configurations exercise direct join
to control each copy field C. Four scenarios refuse launch
internal task; error must remain in the runtime envelope, not become
a value rejected by the vector.

Play uses controlled stdin: three bytes received, end of stream, error
with descriptor -1 and capacity exceeded before access to descriptor.
The other scenarios remain distinct through contracts and joins.
exercise direct returns, if/loop, copy, reassign and drop.

The final module **11 methods, 56 native executions and 13 expected refusals**.
Refusals relate to bad type of capture/return/notation, confusion
Option/Result, confusion unit/value, use of u8 as Int without
conversion, unused result and reading after drop.
valid are executed; a simple syntax error is not used as
evidence of semantic refusal.

<a id="vérification-du-c-et-limites"></a>

## C Audit and Limitations

Clang Homebrew 20.1.3., arm64 macOS, C11, pthread, strict warnings in the
UBSan is fatal to O0/O2. The displacement of common types C
is also verified by the old scenarios of tasks, tables,
reference, calculated expectations and re-use of pools.

The results without borrowing do not prolong the source storage.
does not prove this fact for all containers: it covers modes explicitly
The results with owners or references retain their
separate verification paths. PR1 is not modified; regressions
historical with reset retain their explicit option.

The autonomous materialization of CapacityError and ReadError in a link
`Err(error)` is not yet supported in the async code.
explicit variants are executable and tested. This prototype limit
is not a new language rule or a decision to reject these uses
in the final design.

Update: CapacityError and ReadError standalone values are integrated
in [BUILTIN_ERROR_VALUES_CYCLE.md](BUILTIN_ERROR_VALUES_CYCLE.md), with the
other named buildin errors and their contracts/captures/returns.

Another lack is reproduced in
`validation/open-async-vector-result-producer.crust` and its log: one
`return v.try_push(n)` directly in a task remains refused for expression
The type of result is now accepted, which is
allows to continue on the implementation of the operation itself.

Update of the following cycle: this gap is corrected and its program is
run in [ASYNC_VECTOR_OPERATIONS_CYCLE.md](ASYNC_VECTOR_OPERATIONS_CYCLE.md).
The log of the initial refusal remains historical.

The other obligations of the seven drafts remain open: types and
general containers, runtime::Handle<T>, public scheduler, runtime::thread,
Select, storage guards and gaps already recorded. Points expressly
No results of this cycle are presented as
general proof of security; neither ASan nor TSan nor formal evidence were
executed here.

<a id="preuves-dexécution-et-mutations"></a>

## Evidence of execution and transfers

| Completed | Result | Trace |
| --- | --- | --- |
| New lot O0 before adding direct join | 10 successful methods, 23.852 s; 40 native programmes and 13 refusals | validation/async-vector-results-O0-final.log |
| O0 supplement to direct join | 1 successful method, 5,948 s; 16 native programmes | validation/async-vector-results-O0-direct.log |
| Nouveau lot complet O2 | 11 successful methods, 38,523 s | validation/async-vector-results-O2-final.log |
| Business/Imbricated/Simple Results, Runtime::Error, Constraints and Effects | 86 successful methods, 95,422 s | validation/async-vector-results-regression.log |
| ABI, calculated expectations, Bool/tables, borrowings and pools | 15 successful methods, 29.247 s | validation/async-vector-results-abi.log |
| Mutations finales | 5 detected | validation/async-vector-results-mutations-final.log |

The old stress/effect helpers have their own level of optimization;
CRUST_SANITIZE activates UBSan but CRUST_TEST_OPT does not prove their execution at
O2. New helpers explicitly use this variable.
logs, prior to the two cover supplements, are retained.
Python compilation of modules and new tests/scripts has been successful.

The mutations are applied in temporary copies.
value of direct join, control of type of capture, pre-game status,
The value returned in Err and the form control of the motifs.
The first four mutations in the
initial campaign were already detected; the fifth checks the path
no surviving mutations are hidden and
no overall coverage rate is deducted from this selection.

Commandes reproductibles :

```sh
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_vector_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_async_vector_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_business_result_envelopes test_nested_plain_results test_plain_join_contracts test_runtime_error_values test_constraints test_effects -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_result_mutations.py
```
