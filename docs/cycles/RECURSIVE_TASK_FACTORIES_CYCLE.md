[Français](RECURSIVE_TASK_FACTORIES_CYCLE-fr.md)

<a id="fabriques-de-tâches-portant-des-graphes-récursifs"></a>

# Task factories with recursive graphs

<a id="règles-et-périmètre"></a>

## Rules and scope

Continue ASYNC_RECURSIVE_OWNED_CYCLE.md. Application of existing rules
AS8–AS12, explicit transfers and parameter contracts to factories
No change in the standard.
Calls remain checked from contracts, without browsing the body.

<a id="défauts-et-corrections"></a>

## Deficiencies and corrections

The description of the paths of a type stops with the first type repeated.
In the case of the United Kingdom, it was not sufficient to instigate the concrete value received by a factory: only the
The first descendants were preserved, and their variant was lost.
The concrete metadata of the argument
are now informed by the published origins of the contract; each
path retains its sources, identities and variants, as well as its descendants.
The fields explicitly described in the contract are connected separately.

The catches borrowed from an entire owner, as well as those taken by the owner, are
d
repeated. A proven path missing for the active variant is represented by a
empty capture; it can be relayed without being confused with an unknown capture.
Pools of all captured descendants remain protected, even if the
future result is a scalar and does not retain any owner.

<a id="vérification-ciblée"></a>

## Targeted verification

Three methods in tests/test_recursive_task_factories.py: five executions
the first five programmes were rejected by verify_program and
compile_source.

- Manufactured from a owner and then relayed a task: two-link graph,
  terminal variant, single destruction and re-use of terminal slot; drop of the
  pool terminal before waiting refused.
- Reference stored in the terminal descendant: manufacture then relay, and
  direct creation then relay; premature mutation after join refused.
- Task that destroys the graph and returns Int: protection of the terminal pool
  until completion and subsequent re-use.

Expectations are written in the tests. Native output, traces of
cleaning and diagnostics are checked. The harness uses C11/pthread,
the warnings in error and fatal UBSan.

| Journal in validation/ | Result |
| --- | --- |
| recursive-task-factories-first-o0.log | 2 methods, 2 failures: incomplete descendants and unobtainable capture |
| recursive-task-factories-second-o0.log | 2 methods, 1.428 s, code 0 |
| recursive-task-factories-third-o0.log | 3 methods, 2.282 s, code 0 |

The bound regression ends with code 0: 99 methods in 77,697 s,
`validation/recursive-task-factories-regression-o2.log`, in O2/UBSan.
The deterministic models in the selection are replayed; none
new generation or change campaign n

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_task_factories -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_task_factories test_async_recursive_owned test_async_result_factories test_detached_task_factories test_task_result_storage test_public_structure_handles test_async_owned_borrowed_captures test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_owned_struct_returns -v
```

The first O0 journal deals with the first version of two methods; the first O0 journal deals with the first version of two methods.
The third version adds the scalar consumer and the relay
The five executions and five refusals described above.

## Limites

This batch covers the concrete origins inherited from the parameters and tasks
It does not declare finished the results built with a shape
new recursive completely opaque, auxiliaries waiting for a result
symbolic recursive, nor all deep projections and substitutions.
The programme `validation/open-recursive-join-helper.crust` reproduces the refusal
d-a helper receiving Handle<A<Node>> and returning the result of join.
`validation/open-recursive-join-helper.log` locates infinite unfolding in
ResultContext.async_owned_result_value. It is an open implementation deviation,
not a semantic arbitration or a rule-invalidated program.
Conservation of whole catches may remain conservative when a
The regressions on the entries of the
fields are included in the selection; they do not constitute evidence
No new adversarial campaign or mutation.

Snapshot : /tmp/crust-before-recursive-task-factories/.
Patch : validation/recursive-task-factories-crust.py.patch.

Next: the case of the public join helper is now corrected and tested in
[RECURSIVE_JOIN_HELPERS_CYCLE.md](RECURSIVE_JOIN_HELPERS_CYCLE.md).
