[Français](FRESH_RECURSIVE_FACTORIES_CYCLE-fr.md)

<a id="graphes-récursifs-neufs-dans-les-fabriques-de-tâches"></a>

# New recursive graphs in task factories

<a id="règles-et-implémentation"></a>

## Rules and implementation

Existing rules of contracts, source, transfers, sustainability of pools and
AS8–AS12. No regulatory rule modified. This batch completes the case where a factory
build a new graph in injected pools and then return a task that
The previous lots covered the graphs received by transfer.

The analysis used only the finished prefix of the type until its first
It produced a local target for an absent variant and
lost the pool and borrowing the deep descendant actually built.
results.py now follows the concrete paths of Value.
also the variants by path via task_result_shapes; these metadata are
The graph is then restored after waiting.
Lowering async retains the deep fields of the owner's result and
the explicitly empty catches for proven variants not present.

<a id="cas-exécutés"></a>

## Cases implemented

Three methods in tests/test_fresh_recursive_factories.py: five
Native programs and seven invalids at both entrances. Construction of two
links A<Node> and a Node.End containing &Int ; direct and relayed call from
hand, then call from a task and read after yield. Reading 7, cleaning,
Reuse terminal pool and write 8 ; target mutation before reading and
destruction of pool before waiting refused.

| Journal in validation/ | Result |
| --- | --- |
| fresh-recursive-factories-first-o0.log | 2 rejected methods: non-sustainable target |
| fresh-recursive-factories-second-o0.log | Paths found; variations of descendants and missing catches |
| fresh-recursive-factories-third-o0.log | Executions pass; CHECK marker forgotten in drop cases |
| fresh-recursive-factories-fourth-o0.log | 2 methods, success |
| fresh-recursive-factories-fifth-o0.log | 2 methods, 1,733 s, code 0 |
| fresh-recursive-factories-conditional-first.log | Junction End/Link refused: field source absent |

The third method checks the junction of the two returned forms:
a direct Node.End or the two-link graph. Both branches pass, so
the rejection of premature mutation. The junction ignores only one form
if a variant of an ancestor proves that the path is missing; a variant
unknown remains unknown. The forms come from the final contract of the task,
no assumption that the captured graph remains unchanged.

First regression: 82 methods in 118,799 s, code 0, in
validation/fresh-recursive-factories-regression-o2.log. Final target O0: three
methods in 2,554 s, code 0, in fresh-recursive-factories-final-o0.log.
Final regression: 83 methods in 119,547 s, code 0, in
fresh-recursive-factories-final-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_fresh_recursive_factories -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_fresh_recursive_factories test_recursive_task_factories test_recursive_join_helpers test_async_recursive_owned test_factory_owned_effects test_task_result_storage test_async_local_owned_result_graphs test_async_result_storage test_async_awaited_owned_results test_select_result_storage test_recursive_link_replacement test_recursive_mutable_results test_recursive_borrow_results -v
```

Targeted harnesses compile C11/pthread, warnings in error and fatal UBSan.
No adversarial campaign or added mutations.
destruction and life are the explicit oracles of cases.

## Limites

Forms of which an alternative remains opaque
are not reduced to a known variant of another branch; they may
No general evidence or declaration of completion
overall integration.

The following deviation is reproduced in both entries: a &Vector loan<A<Int>> cannot be used
not yet captured by a task. The program and diagnostics are
stored in validation/open-async-owned-vector-capture.crust and .log.
program builds a vector, transfers an allocation, waits for a task
which reads only its length, then destroys the vector and re-uses the Int pool.
This limit is a gap in implementation, not a new language rule.

Snapshot : /tmp/crust-before-fresh-recursive-factories/.

Diffs : validation/fresh-recursive-factories-{results.py,crust.py,async_lowering.py}.patch.
