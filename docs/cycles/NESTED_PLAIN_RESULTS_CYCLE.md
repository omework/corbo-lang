[Français](NESTED_PLAIN_RESULTS_CYCLE-fr.md)

<a id="cycle-rt5rt6--retours-async-et-résultats-imbriqués-sans-emprunt"></a>

# Cycle RT5/RT6 — Async returns and interlocked non-borrowed results

<a id="portée-normative"></a>

## Normative scope

Application of the rules already adopted, without change of normative: AS4
(inactive task expected giving T), RT5/RT6 (handle expected giving
Result<T,runtime::Error>, separate launch error from internal result),
U1 (explicit use), rules for the capture, drop and reuse of pools.
AGENTS.md, the design-buffer guidelines and index have been read; this cycle
prolongs previous cycles whose complete normative reading is already
The objective of the seven drafts remains open.

The six loads Int, Bool, u8, tank, (), runtime::Error were already usable
as a result of join in synchronous contracts and async captures.
Their return from an async function was refused, even when the function
simply returned the result of a wait.
validation/open-async-plain-result-return.crust now runs; sound
old log refusal is retained as historical evidence.

<a id="implémentation-et-invariants-examinés"></a>

## Implementation and invariants examined

The interlocked types are recorded structurally when analysing the
signatures, and the envelope added by the join of each definition
Async. There is no artificial limit fixed at two levels.
shared record of canonical facts, not information of
C only states the necessary levels for the current program.
A test compiles the same program before and after a deeper program
and requires an identical C. A deep signature without a task executed is tested.

The first level uses the existing type C; each additional level
contains its own status and a value from the previous level.
Synchronizes the load directly in this field and receives separately the
external status. L'attendance async uses a separate status temporary,
kept in the state; no pointer conversion between size structures
The temporary result is initialized before the end of the year.
point of recovery, not at every poll. The match only extracts the level
internal error therefore does not become either success or external error.

Contracts and effects/provenance analyses keep the type complete.
representation also applies to catches, copies, direct returns of waiting,
if, loop, match, annotations, reassignments and drop of these values.
simple does not contain any dependence on the allowances used for the
calculate: after waiting, its reading can follow the drop of these allowances.
The results of the ownership or borrowing remain in their existing paths.

<a id="modèle-et-contre-exemples"></a>

## Model and counter-examples

The test generator builds chains of joins. Its oracle n
neither compiler tables nor C: each successful launch adds a
successful layer; refusing a launch prevents the execution of his child and
The error is exactly at this level. Six terminal values are followed to
depth 2 and 4, synchronous observation and async capture/suspension
(24 configurations). Eight configurations refuse one of the four levels of
launch, with the same two modes of observation. A depth program
7 verifies that the support is not limited to two-layer examples.

Cleaning test transfers allowance through parent/child: success
and refusal to launch must destroy the capture once and then allow for
Reuse the same address. Another program keeps a mutable capture
until the join, then destroys its target, then reads the simple result.
variants with read, drop or reset history before waiting are refused.
`reset()` remains removed from the prototype; this last control explicitly uses
allow_legacy_reset=True.

Invalid neighbours change depth or load, substitute an integer or
an error to a Result, re-use a link after drop, or ignore a
The three diagnostics used are explicitly controlled.
These are 23 expected refusals and 52 native executions in the final module of the
11 methods, by level of optimization. This count does not include the following
and the transfer campaigns.

<a id="exécutions-terminées"></a>

## Completed

Clang Homebrew 20.1.3, arm64 macOS, C11, pthread, UBSan fatal
(-fsanitize=undefined -fno-sanitize-recover=all). Runtime oracles add
-Wall -Wextra -Werrar. Old stress/effect helpers use their
default optimization and enable UBSan via CRUST_SANITIZE; do not
assign them O2 on the basis of CRUST_TEST_OPT only.

| Verification | Terminal result | Trace |
| --- | --- | --- |
| Nouveau module final O0 | 11 successful methods, 30.583 s | validation/nested-plain-O0-final.log |
| Nouveau module final O2 | 11 successful methods, 32.593 s | validation/nested-plain-O2-final.log |
| First 10 new methods, runtime::Error, constraints and effects | 67 successful methods, 50,626 s | validation/nested-plain-O2-regression.log |
| Direct returns of expectations, named/calculated/conditional | 1 method, 8 successful executions | validation/nested-plain-direct-returns.log |
| Simple results, spawn_blocking, obligations, capabilities, features async | 39 successful methods, 48,193 s | validation/nested-plain-runtime-regression.log |
| Results Bool/tables, calculated expectations, borrowings, existing ABI and pools | 15 successful methods, 29,331 s | validation/nested-plain-typed-regression.log |
| Accurate diagnosis of the three results ignored | 1 successful method | validation/nested-plain-use-diagnostics.log |
| Mutations finales | 5 detected | validation/nested-plain-mutations-final.log |

The regression of 67 methods precedes the addition of direct hand returns;
the two final complete executions and the 39 runtime methods follow them.
The first log nested-plain-O0.log also inadvertently loaded the 11 tests
Imported module; import has been corrected and final accounts above
The new module is the only one to be used.
The Python compilation of modified modules and new tests was successful.

The mutations, applied to temporary copies, erase respectively
synchronous external status, async external status, internal status,
the type control of the return and the obligation to use the extracted result.
The five produce failures in the expected tests.
counted as detected on the basis of a syntax or build error alone.
The campaign targets these five mistakes; it does not measure global coverage.

<a id="limites-et-travail-restant"></a>

## Limitations and remaining work

The current C construction concerns runtime envelopes::Error repeated
It does not make all Results<T,E> generic,
signatures of proprietary/borrowed charges or result containers.
A similar gap was repeated in the
validation/open-async-business-result-envelope.crust and its log: the result
existing Result<u8,IntegerConversionError> can be removed from a task, but a
function async declaring the envelope of its join is not yet accepted.
This program was a valid case still to be implemented, not a negative test of
This gap is corrected in the
[BUSINESS_RESULT_ENVELOPES_CYCLE.md](BUSINESS_RESULT_ENVELOPES_CYCLE.md), without
additional normative arbitration.

L'API runtime::Handle<T>, the public installation of the scheduler, wake-ups and equity,
runtime::thread, Select, mutex and other previously recorded deviations remain
This cycle does not claim to be covered. There is no formal evidence,
Neither Tsan nor ASan campaign nor the entire monolithic suite.

Commandes reproductibles :

```sh
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_nested_plain_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_nested_plain_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_plain_join_contracts test_spawn_blocking test_handle_obligations test_async_capacity test_async_type_features -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_nested_plain_mutations.py
```
