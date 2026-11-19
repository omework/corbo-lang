[Français](ASYNC_REGIONS_CYCLE-fr.md)

<a id="cycle--régions-annotées-dans-les-blocs-async-et-natifs"></a>

# Cycle — annotated regions in async and native blocks

Continue [pool aliases cycle]](ASYNC_POOL_ALIASES_CYCLE.md).
No regulatory rule has been amended. References: G4–G12, A1/A4, D1,
S4/S5, B1/B2/B4a, T6/T11, AS8/AS10/AS12 and RT8; drafts 03/04/05.
The overall support of language remains partial.

<a id="écart-et-implémentation"></a>

## Deviation and implementation

Lowering refused to accept any region annotation in an async block,
including when its content was already compileable without annotation.
The [programme retained]](../../validation/open-async-region.crb) utilise un
local pool Vector<u8>, an annotated 1M and yield scope. It is now
executable; [C generated](../../validation/async-region-basic.c),
[lowering diff]](../../validation/async-region-implementation.patch).

A lexical configuration stack accompanies the block generation.
A block without annotation inherits from its parent; an annotated block replaces
temporarily limit. The configuration is restored even if the block
does not reach its normal exit point.
blocks producing a scalar, allowance or loan follow this rule.
The String and Vector manufacturers<Int/u8> receive the current limit.

The boundary is established at the creation of the region: yield, transfer,
reception in a different annotated scope and function return does not the
An appeal does not implicitly transmit its directive to the
function called, as in the existing synchronous compiler.
Pools remain within their scope and life-long boundaries are
The primitives of regions and synchronization C are reused
The native block code is the same path.

<a id="oracles-et-contre-exemples"></a>

## Oracles and counter-examples

An oracle added to the test C reads the size of the region class actually
The expectations come from the source
and are not extracted from the product C. It also distinguishes the creation
without annotation, which uses a growth front without region class.

Scenarios cover inheritance, local replacement, restoration, transfers
2M → 1M, conditional returns 1M/2M received in 4M, pool aliases, helpers
synchronous, async children, loops, continuous/break, borrowing and
early returns. Variants that lose their pool or use a
collection during an incompatible loan are refused.

A Vector<u8> created in 1M and then transferred out of block is filled to 1,048,576
bytes. After yield, try_push returns the refused byte; length and length
last byte remain unchanged. This checks an effective limit after
transfer, not just a configuration value in the C.

The generated model uses an independent configuration stack and two
tree of telescopes from seeds 19 and 73. Each tree produces 14 regions,
with pre- and post-child allowances and suspensions.
The observed physical responses correspond to the expectations of this finite model.

<a id="preuves-exécutées"></a>

## Evidence

Clang C11 pthread, warnings bloquants, UBSan fatal, O0/O2. Aucun nouveau
ASan/TSan result, second compiler or formal proof.

| Passage | Result | Journal |
| --- | --- | --- |
| Initial O0 | Seven methods, 5,755 seconds, OK | [Initial](../../validation/async-regions-initial-o0.log) |
| Final O0 | Nine methods, 8.473 seconds, OK | [O0](../../validation/async-regions-final-o0.log) |
| Final O2 | Nine methods, 8,603 seconds, OK; 14 executions C, three refusals | [O2](../../validation/async-regions-final-o2.log) |
| Mutations O2 | Baseline eight methods/10,147 s, OK, before adding the generated model; four detected errors | [Mutations](../../validation/async-regions-mutations-o2.log) |
| Regression pools/collections/regions O2 | 102 methods, 111.887 seconds, OK | [Regression](../../validation/async-regions-regression-o2.log) |
| Flow control regression O2 | 36 methods, 58,798 s, OK | [Control](../../validation/async-regions-control-o2.log) |

Injected errors remove legacy, restore configuration,
The limit of the Strings or the limit of the Vector. All are detected in
temporary copies, without changing expectations.
Vector is detected by the exhaust test after transfer.
No universal coverage is deducted from the four mutations.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_regions -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_regions -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_region_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_pool_aliases test_async_local_pools test_async_collection_new test_async_vector_operations test_async_vector_push_new test_growth_annotations test_growth_runtime -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_expression_loop_exits test_async_diverging_expressions test_async_typed_divergence test_async_loop_references -v
```

## Limites

This extension connects the annotations to the constructions already taken in
It does not generalize collections of aggregates,
the capture of structures or any anticipated investments of data stack.
Injected and local sources continue to follow their existing rules.
The model tests finished trees; it does not prove all the programs or programs
All the schedules. Performances are not measured.

At the end of this batch, the next gap was reproduced without feature type: a task that captures
un `&Point` Local, hangs and then reads `point.x` remains refused by the list
The pool and the annotations of the
The following are not involved: [minimum programme](../../validation/open-async-struct-reference.crb),
[diagnostic actuel](../../validation/open-async-struct-reference.log).

This case is now connected in the [structural catch cycle]](ASYNC_STRUCT_CAPTURES_CYCLE.md).
