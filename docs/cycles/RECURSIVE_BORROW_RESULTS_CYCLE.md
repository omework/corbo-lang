[Français](RECURSIVE_BORROW_RESULTS_CYCLE-fr.md)

<a id="retours-partagés-depuis-des-descendants-récursifs"></a>

# Shared returns from recursive descendants

<a id="règles-appliquées"></a>

## Rules applied

ST13, the rules of provenance B1–B5, match and AS8–AS12 are unchanged.
A shared reference stored in a descendant is an external target.
The returned reference retains this target, without artificial dependence on
the bearer. The destruction of the bearer is permitted after the call; the writing or
destruction of the target remains refused before the last use of the result.
The mutable references do not become copyable.

<a id="implémentation-et-défauts-corrigés"></a>

## Implemented and corrected defects

- results.py keeps the path of A<T> projections in a borrowed match,
  then publish the detached provenance of the shared terminal field. Previously,
  Two similar links resulted in a local non-sustainable source.
- crust.py solves these paths on symbolic descendants, prepares the
  necessary borrowed fields and ignores proven variants absent.
  The match results filter now admits an nested, submitted match
  then to the ordinary controls. The connection of a shared field does not retain
  plus temporary loan of the subject of the game after exit; the subject remains
  The mutable fields retain their capacity.
- async_lowering.py admits enums, like structures, for projection
  a synchronous call result from the contract.

The first to fourth newspapers keep the steps of the previous refusals: target
local non-sustainable, match read filter, carrier absent from contract, then
limitation of the projection async to the structures. fifth completes both cases.

<a id="cas-et-résultats-exécutés"></a>

## Cases and results achieved

Two methods in tests/test_recursive_borrow_results.py: two programs
valid natives and four invalids tested by verify_program and compile_source.
The graph contains two links A<Node> followed by a &Int field. A helper returns
this field, with another target in rescue in the remaining branches.

- Call from hand: destruction of the graph, reading 7, then writing 8 admitted.
- Call from an async state: destruction of the graph, yield, reading 7, then
  writing after last use allowed.
- In each case, write before reading and drop before reading are refused.
  Drop variants remove the subsequent use of number: the diagnosis does not
  can not be justified only by a second use after destruction.

| Journal in validation/ | Result |
| --- | --- |
| recursive-borrow-results-fifth-o0.log | 2 methods, 1,041 s, success |
| recursive-borrow-results-final-o0.log | 2 methods, 1,077 s, code 0; refusal of drop added |
| recursive-borrow-results-regression-o2.log | 81 methods, 48,141 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_borrow_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_borrow_results test_recursive_borrow_projections test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_shared_match_field_reads test_async_stored_views test_async_enum_nominal test_async_owned_borrow_writes test_async_owned_nominal_writes test_mutable_match_function_return test_direct_borrow_returns -v
```

Async/target harnesses compile C11/pthread, error warning, fatal UBSan,
The historical synchronous harnesses of direct returns
and mutable match compile in C without explicitly optimising/sanitizer
activated in this command; they use the legacy-reset profile for their
The regression re-executes their finished models and controls of the
existing contracts, without new adversarial campaign or changes.

## Limites

Cover of shared &Int return from this finished graph and its use in
no general evidence, no independent validation added.
The deep mutable return and the replacement of recursive bonds remain at
complete. The public interface of the scheduler and other arbitrations reported
remain open; this batch does not end the overall objective.

Snapshot : /tmp/crust-before-recursive-borrow-results/.
Diffs : validation/recursive-borrow-results-{crust.py,results.py,async_lowering.py}.patch.
