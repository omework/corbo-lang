[Français](ASYNC_POOL_ALIASES_CYCLE-fr.md)

<a id="cycle--emprunts-nommés-de-pools-dans-les-états"></a>

# Cycle — named pool borrowings in the states

[Local Pool Cycle]](ASYNC_LOCAL_POOLS_CYCLE.md).
Aucune modification normative : B1/B2/B4/B4a/B4c, A1–A4, D1,
T6/T9/T11, AS2/AS12/AS13, RT8 and MT7, drafts 03/04/05.
The overall objective and the seven drafts remain partially implemented.

<a id="implémentation"></a>

## Implementation

Async and native bodies can bind a local pool by `&p` ou `&mut p`,
and reborrow a pool reference by `&*memory` ou `&mut *memory`.
The nominal type, mode and annotations must correspond. `&`
additional reference is not flattened. A read source
The reservation follows the last use, the
the arguments prepared and the tasks which capture the reference.

L-alias retains the actual local sources of the allowances created by the
The results summaries also follow the alias of the pools.
Injected: a result from p does not unnecessarily hold back q.
continue to refuse an allowance the pool does not survive the recipient.

A task can exit the block of the alias link when the pool remains
The loan to this link is withdrawn at the border; the loan
The local values to states always have an address
stable. No change in runtime C is necessary for this extension.

[Diff of Lowering](../../validation/async-pool-alias-implementation.patch),
[programme historique](../../validation/open-async-local-pool-alias.crb),
[C generated](../../validation/async-pool-alias-basic.c).

<a id="scénarios-et-contre-exemples"></a>

## Scenarios and counter-examples

The programs allowed cover the four types of pools supported,
re-use after drop, yield, interlocking re-borrowing, calls
synchronous, child and native tasks, loops with continuous/break,
transfer beyond the block of an alias and disjointed sources.

The rejected programmes cover incorrect modes and levels, conflicts
d    , use of pool before waiting for a task, arguments
the re-use of a consumed catch and the leakage of allowances.
The pool can be reused after the end of the loan without destroying the allowances
which remain alive: exclusive loan and storage dependency remain distinct.

The first mutation campaign will survive the omission of the root loan
in a child's argument: the alias still present in the block protects
The test was completed by a task transferred from the
The programme must be based on the following criteria:
The final campaign detects this omission.
The original journal is kept and is not presented as entirely green.

<a id="preuves-exécutées"></a>

## Evidence

Clang C11 pthread, warnings bloquants, UBSan fatal, O0/O2. Aucun nouveau
ASan/TSan result, second compiler or formal proof.

| Passage | Result | Journal |
| --- | --- | --- |
| Initial target O0 | 12 methods, 4,552 seconds, OK | [Initial](../../validation/async-pool-alias-initial-o0.log) |
| Final target + model O0 | 15 methods, 20.429 seconds, OK | [O0](../../validation/async-pool-alias-final-and-model-o0.log) |
| Baseline finale O2 | 14 methods, 8,804 seconds, OK; 15 C executions and 27 refusals | [Baseline and mutations](../../validation/async-pool-alias-final-mutations-o2.log) |
| Descent model O2 | One method, 5.179 s, OK; nine executions, three refusals | [Model](../../validation/async-pool-alias-model-o2.log) |
| Mutations initiales | Six detected, one survivor examined | [Initial](../../validation/async-pool-alias-mutations-o2.log) |
| Mutations finales | Seven detected errors | [Final](../../validation/async-pool-alias-final-mutations-o2.log) |
| Replayed local pools changes | Baseline 18 methods/19.546 s, OK; six detected errors | [Regression mutations](../../validation/async-pool-alias-local-mutations-o2.log) |
| Native regression O2 | 209 methods, 213,343 s, OK | [Regression](../../validation/async-pool-alias-native-o2.log) |

The model is an ancestry independent of the previous cycle, applied
to a chain alias → reborrow → child async → allowance returned. It compares
lexical depths of pool and receiver, and distinguishes scalar copy
The compiler does not use the compiler's summary or its internal condition.

The seven mutations target root loan, storage origins, level
de référence, la promotion mutable, les conflits à la création, la durée de vie
The intermediate binding and the accuracy of the source summary.
The same applies to mutated copies. No general rates are extrapolated.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_pool_aliases test_async_pool_alias_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_pool_alias_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_pool_alias_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_local_pool_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
```

## Limites

This batch covers Pool<Int>, Pool<String>, Pool<Vector<Int>> and Pool<Vector<u8>>.
It does not generalize async signatures to user aggregates, does not provide
not proof of all the arrangements and does not end the rules of
The annotated regions in the async bodies
are treated in the [next cycle](ASYNC_REGIONS_CYCLE.md). Method counts between
campaigns overlap and do not add up as independent scenarios.
