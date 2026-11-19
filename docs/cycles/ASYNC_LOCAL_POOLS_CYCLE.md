[Français](ASYNC_LOCAL_POOLS_CYCLE-fr.md)

<a id="cycle--pools-locaux-dans-les-états-async-et-natifs"></a>

# Cycle — local pools in async and native states

The [cycle of collections]](ASYNC_COLLECTION_CREATION_CYCLE.md).
No normative changes. References: drafts 03/04/05,
A1–A4/A6, S4/S5, B1/B4/B4a/B4c, T6/T9/T11, L1/L2/L6, V4/V5,
AS2/AS8–AS14, RT6/RT7/RT8 and MT7.

**Status: Implementation and validation of the executed perimeter.
async_runtime has completed with two diagnostic differences, examined and
reexecuted separately below; its initial log remains in check.**
The overall objective and other obligations of the seven drafts remain open.

<a id="implémentation"></a>

## Implementation

A native or async body can declare a local pool Int, String,
Vector<Int> or Vector<u8>. The descriptor Source and, for collections,
VectorStorage are members of the stable state. The manufacturer executes
the transition from the declaration, not the creation of the inactive task.
The mappings use existing pool builders of runtime.
A cover retains their address; a new iteration reconstructs the
pool after closing the previous one.

The local source is followed independently of the borrowing which allows for
allocations, returns of helpers, transfers, child tasks,
Await/join results and branch junctions retain their origins.
A child who owns an allowance shall retain the life of the pool
without borrowing this pool exclusively. Receive the pool in &mut reserve
However, until the child's end.

Outputs check that each transferred allocation retains a pool
Sustainable. Potential sources of receivers are gathered at junctions;
a subsequent replacement updates the current provenance.
refuses an external receiver or a task still dependent.
Inactive children and allowances precede source_close.
The sources are not displaced.

## Contre-exemples

The [historical case]](../../validation/open-native-async-local-pool.crb), which creates
an allowance in the local pool of a task and then transfers it to a thread
native, now runs and displays 7.](../../validation/async-local-pool-basic.c)
and its [trace](../../validation/async-local-pool-artifact.log) are retained.

The variants refused bring out an allowance by return, helper,
Await, a result of join, block or break while his pool closes.
allocation to an outside recipient is also refused if it retains
the source too short at the exit; then replace with an allowance
The two sources of a conditional result are allowed.
Stay protected.

The three errors of the first targeted passage came from fixtures using
`print(a)` in an async body where the reading of the inmate is explicitly held
`*a`. They are corrected without altering the expected results or destruction.
The initial journal is still in failure. The first campaign of mutations has been
stopped on a non-single anchor: `loans.extend` also appeared in
`returned_loans.extend`. The anchor has been specified and the campaign revived in
new temporary copies.

<a id="preuves-exécutées"></a>

## Evidence

Clang C11 pthread, O0/O2, warnings bloquants, UBSan fatal. Aucun nouvel
essai ASan/TSan, second compilateur ou preuve formelle.

| Passage | Result | Journal |
| --- | --- | --- |
| Preregression pools injected + collections O0 | 33 methods, 23.977 seconds, OK | [Pre-regression](../../validation/async-local-pool-preregression-o0.log) |
| Initial target | 11 methods, three fixture errors | [Initial](../../validation/async-local-pool-initial-o0.log) |
| Targeted O0 | 17 methods, 7,375 s, OK, before the last competing case | [O0](../../validation/async-local-pool-final-o0.log) |
| Baseline finale O2 | 18 methods, 13.767 s, OK; 21 normal executions, one controlled exhaustion, 20 refusals | [Baseline and mutations](../../validation/async-local-pool-final-mutations-o2.log) |
| Descent model O0 | Nine programs performed, three refusals; the loading also replayed the 18 imported methods, 19 methods/18,901 s, OK | [Model O0](../../validation/async-local-pool-model-o0.log) |
| Descent model O2 | One method, nine executions and three refusals, 5.312 s, OK; import corrected to avoid rediscovery | [Model O2](../../validation/async-local-pool-model-o2.log) |
| Native/runtime O2 | 195 methods, 175,346 s, OK, including the 18 final target | [Native regression](../../validation/async-local-pool-native-o2.log) |
| Module async_runtime complet O2 | 275 methods, 412.76 s; 273 successes, two claims of failing diagnosis | [Regression async](../../validation/async-local-pool-runtime-o2.log) |

The model calculates admission by comparison of the lexical depths of the
The following is a copy of the report:
The first is the need for a pool of at least as long as possible.
other oracles impose values, order and number of destructions.
One oracle C has four openings and four pool closures through
Three iterations and the final scope. It detects a mapping leak that the
Only evidence of destruction would not reveal.

Six injected errors are detected: origin forgotten at creation, control
missing border, missing mapping closure, dependence of a forgotten child,
The origin lost after awat and origin of a forgotten branch.
The same applies to the mutated copies. No general rate is deducted.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_local_pools -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_local_pool_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_local_pool_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_runtime -v
```

<a id="limites-et-suite"></a>

## Limitations and follow-up

At the end of this lot, the loan named from a local pool remained to be connected:
[programme](../../validation/open-async-local-pool-alias.crb),
[diagnostic](../../validation/open-async-local-pool-alias.log). L’injection directe
`child(&mut p)` is exercised; `let memory = &mut p; child(memory)` remains refused
by the lowering. General types of pools, annotated async blocks and the
Other catch families remain open. Models and tests are limited,
and do not prove all forms of control or all ordering.

The [diff of the lowering](../../validation/async-local-pool-implementation.patch) is
The [Aka cycle]](ASYNC_POOL_ALIASES_CYCLE.md) poursuit ce travail.

<a id="résultat-terminal-de-la-régression-complète"></a>

## Final result of complete regression

Both programs are not supported, but earlier than diagnostics
The same behavior is reproduced with the lowering
prior to local pools: [reproduction](../../validation/async-local-pool-diagnostic-baseline.log).
The first test now recognizes the precise diagnosis String/Int in addition
The second removes only, in its negative variant,
l’appel Vector-only `received.push(11)` : he thus checks the return contract
Incorrect instead of failing first on an absent method d
The programs admitted and their oracles do not change. Both methods are
O2: two successes, 5.839 s, [newspaper](../../validation/async-local-pool-diagnostic-recheck-o2.log).
The complete module is not presented as completely green: the result is
273 initial successes and two methods corrected and re-executed.
