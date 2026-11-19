[Français](RECURSIVE_MUTABLE_RESULTS_CYCLE-fr.md)

<a id="retours-mutables-depuis-des-descendants-récursifs"></a>

# Mutable returns from recursive descendants

<a id="règles-et-correction"></a>

## Rules and correction

Application of existing ST11–ST12, B1–B5 and AS8–AS12 rules.
a shared reference stored as a value (ST13), a reborrowing
mutable retains the exclusive capacity of its holder until the last use.
No new semantics or life-long promotion.

The contract for a match result lost the owner's path as soon as he
met a symbolic recursive descendant. results.py published
now the full path for the origins owned_projection and
owned_field_input instead of making it a local target. Other origins
locals stay local. crust.py solves symbolic proprietary fields
and prepare their terminal references before reconstructing reservations
The chain of bearers is kept by the existing mechanism.

<a id="cas-ciblés"></a>

## Targeted cases

Two methods in tests/test_recursive_mutable_results.py: three programs
valid natives and seven invalids at both entries (verify_program and
Compile_source). They follow two links A<Node> to a field &mut Int.

- Synchronous call and call from a task with yield between return and
  writing: Final value 8, wearer destroyed after last use.
- Drop of the carrier, drop of the target and direct write before use of the
  The results are rejected. The pest use after drop is removed in the tests.
- Synchronous relays adding a parameter before the carrier: retention of the
  from where after renumbering, access after last use and early drop refused.

Oracles are explicit outputs and life rules.
new independent model or mutation campaign; existing tests
related to returns and contracts are retained.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| recursive-mutable-results-first-o0.log | Two sub-cases wrongly rejected: non-sustainable target |
| recursive-mutable-results-second-o0.log | Two sub-cases refused: symbolic projection not resolved |
| recursive-mutable-results-third-o0.log | One method, 0.876 s, code 0 |
| recursive-mutable-results-fourth-o0.log | Two methods, 1,206 s, code 0 |

Regression completed: 97 methods in 42,486 s, code 0, in
validation/recursive-mutable-results-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_mutable_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_recursive_mutable_results test_recursive_borrow_results test_recursive_borrow_projections test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_shared_match_field_reads test_async_stored_views test_async_enum_nominal test_mutable_match_function_return test_mutable_borrow_returns test_direct_borrow_returns -v
```

Targeted harness: C11/pthread, error warning and fatal UBSan. Selection
async uses O2; the old synchronous harness activates UBSan via
CRUST_SANITIZE but do not add O2. Their reset cases explicitly use
the historical profile and do not reintroduce reset into the prototype.

## Limites

These tests concern the paths covered and the graphs constructed in the
no general evidence on recursive graphs;
link replacements still need to be completed.
open arbitrations are not closed by this lot.

Snapshot : /tmp/crust-before-recursive-mutable-results/.
Diffs : validation/recursive-mutable-results-{crust.py,results.py}.patch.
