[Français](RECURSIVE_OWNED_JOIN_CYCLE-fr.md)

<a id="résultats-propriétaires-à-profondeur-variable"></a>

# Owner results with varying depth

<a id="règles-et-réalisation"></a>

## Rules and implementation

RT6 ajoute un `Result<T, runtime::Error>` every time you wait for a handle.
AS8–AS14, H1–H2, B1–B5, U1, F3–F4 and SL1–SL2 continue to protect the environment.
type, storage, dependencies and cleaning of its load.
amends no normative rules.

`owned_join_types.py` describes the boundless proprietary results levels
The type of load and its local nature T or allocated A<T>
remain in the signature; depth determines the layout C and the path
The historical layouts of the first two levels are
retained. `CrustNestedJoinResult` is now declared with the types of
common values, before deeper layouts.

Parser, contracts, field effects, storage requirements, public handles,
The descriptions are consulted by each extraction.
remove one level and keep the own and borrowed fields as well
that the information of absence proved of a charge. Cleaning checks all
the status runtime before destroying the content. Targeted allowances do not
are not displaced.

<a id="validation-ciblée"></a>

## Target validation

Seven new methods in `tests/test_recursive_owned_join.py` :
19 native executions and eight invalid programmes monitored at both entries,
verify_program and compile_source.

- Three and five envelopes around A<Int>, extraction and re-use.
- Failed injected at each of the three levels of launch, single destruction.
- Public handle, synchronous wait helper and result relay.
- Async extraction, synchronous manufacturing and named inactive instance.
- Int, String, Vector<Int> and Vector<u8>: preserved type, reading, destruction
  then re-use the slot.
- Capture executed or inactive; argument prepared before await, cleaning by
  Select's losing branch.
- If and loop producers of the result; explicit consumption and transfer.
- Local View object containing a &Int: three envelope result, ready
  retained and the View/A<View> distinction verified.
- Refusal of the absent transfer, of the re-use after transfer, of the result
  without use, of double consumption, of reason ignoring a charge, of the
  too short pool, drop of a still borrowed target and substitution
  implicit between local storage and pool allocation.

Historical method
`AsyncRuntimeTests.test_nested_join_result_transfers_through_sync_and_async_signatures`
executes eight native programs and three refusals via verify_program. It keeps
its sync/async scenarios and its failures injected. The former refusal of principle of the
third level is replaced by its execution with explicit expectation;
The return abandoning this expectation remains refused.

<a id="défaut-préexistant-découvert-et-corrigé"></a>

## Pre-existing defect discovered and corrected

This historical test revealed a TypeError of the lowering during the `child.await` :
the named task was consumed before reading its signature.
is reproduced on the pre-batch backup, in
`recursive-owned-join-legacy-baseline-o0.log`. The signature is now
The new suite keeps a deterministic case
with a named instance from a factory.

The first historical passage also noted its assertion that it had become a
obsolete on the diagnosis "three levels". The replacement snippet
really waits for the third handle and treats each envelope; its
values and destruction are verified. Previous oracles are not
weakened to mask the Eror Type.

<a id="commandes-et-résultats"></a>

## Commands and results

The tests use C11, pthread, Wall/Wextra/Werrar, UBSan and
`-fno-sanitize-recover=all`. Sanitizer diagnostics fail the test.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest \
  test_recursive_owned_join \
  test_async_runtime.AsyncRuntimeTests.test_nested_join_result_transfers_through_sync_and_async_signatures -v
```

Journaux sous `validation/` :

| Journal | Result |
| --- | --- |
| recursive-owned-join-first-o0.log | Initial reproduction executed, code 0 |
| recursive-owned-join-second-o0.log | 7 methods, 8,059 s, code 0; before the additional name case |
| recursive-owned-join-legacy-o0.log | 1 method, 1,580 s, code 1 ; TypeError and historical diagnosis obsolete |
| recursive-owned-join-legacy-baseline-o0.log | Previous backup, 1 method, 1,568 s, code 1 ; same TypeError |
| recursive-owned-join-third-o0.log | 8 methods, 10.001 s, code 0; corrected targeted and historical suites |
| recursive-owned-join-regression-o2.log | 186 methods, 231,142 s, code 0; O2/UBSan |

Regression:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
  test_recursive_owned_join \
  test_async_runtime.AsyncRuntimeTests.test_nested_join_result_transfers_through_sync_and_async_signatures \
  test_async_nested_option_join test_async_nested_exchange_join \
  test_async_exchange_join test_async_option_join test_async_awaited_owned_results \
  test_async_failure_only_results test_local_result_envelopes \
  test_async_borrowed_local_results test_async_local_owned_result_graphs \
  test_async_structure_effects test_factory_owned_effects \
  test_public_handle_contracts test_select_source test_task_wakes -v
```

<a id="limites-et-traçabilité"></a>

## Limitations and traceability

The depths and types executed do not prove all combinations.
general limits for the recursion of the prototype remain applicable.
The existing models of pollution/cleaning have been successfully implemented.
of Select and Wake-up; no new independent adversarial audit or campaign of
Asan and the other C compilers are not claimed.
practiced here.

This work does not generalize the Options sheets and replace/try_push to all
Other restrictions on signatures, collections and captures
The public interface of the scheduler, the
construction of the mutex and other deferred arbitrations are not resolved.
The overall objective remains active.

Eleven Python files from compiler/runtime and a historical test file
are compared to `/tmp/crust-before-recursive-owned-joins`. The diffs are
retained in `validation/recursive-owned-join-*.py.patch` ; the new suite
is kept with the project.

The depth program three and its generated C are retained in
`validation/recursive-owned-join-depth3.crust` and `.c`. The C uses the layout
interlocked expected and checks all three statutes before the handle is cleaned.
The next deviation of VE1–VE3 is reproduced at both entries in
`validation/open-vector-allocated-structure.crust` and `.log` :
`Vector<A<Point>>`, insertion then pop and re-use of the pool. The current refusal
The system is used to provide a diagnostic of the integra tion of the vector.
This is not a regulatory restriction on T.
