[Français](ASYNC_NESTED_EXCHANGE_JOIN_CYCLE-fr.md)

<a id="enveloppes-runtime-imbriquées-autour-de-replace-et-try_push"></a>

# Runtime envelopes nestled around replace and try_push

<a id="règles-appliquées"></a>

## Rules applied

RT1 tax on imports of certain products `Result<T, runtime::Error>` each expectation of a
AS10–AS13, H1–H2 and VE3–VE4 require that allowances be retained,
their sources and responsibility for their cleaning. U1, F3–F4, AS14 and
SL1–SL2 remains applicable to suspended transfers, catches and arguments.
No normative rules are amended.

This lot removes the fixed depth limit for runtime envelopes around
of the `Result<A<Int>,A<Int>>` and `Result<(),A<Int>>`. Each type is described by
its depth, its interior type, its representation C, the way of the handle
and the conditions of presence of its charge. `Ok` removes a
The two sources of the operation remain distinct.
For try_push, only the failure arm of the operation has the input; a
launch error, at any level, does not have this result.

Signatures, contracts, synchronous public handles, captures of results,
Async returns, junctions and cleanings use these descriptions.
The results of the analysis are based on the new types recorded during the analysis.
provisions C are issued according to the program signatures.
The pool objects keep their address: the envelopes carry their
The target allocation is not copied.

<a id="cas-ciblés"></a>

## Targeted cases

`tests/test_async_nested_exchange_join.py` has eight methods, with
21 native and six invalid programs verified by verify_program
and compile_source:

- Two, three and five envelopes around the place, on both variants.
- Injected launch failure at each of the three levels of a chain.
- Public handle, synchronous wait helper and relay of the result.
- Extracting envelopes in async after waiting for a handle.
- Capture of result: execution, inactive destruction and prepared argument
  before suspension, cleaned in a losing branch of Select.
- Try_push passed or refused after actual filling of a region of 1 MiB,
  with inactive extraction or destruction; single destruction of the input.
- Pools separated by arms; extraction of the old allowance out of the
  Incoming pool block, and refusal when its own source does not survive.
- Result from an if or a loop, cleaning and re-use of slots.
- Refusal of the absent transfer, the re-use of a transferred result,
  the result without use, double consumption and the ignorant motive
  a proprietary charge.

The number of depths executed is not evidence for any
depth. The description is recursive, without new specific terminal to
These envelopes; the general limits for the recursion of the prototype remain.

<a id="défauts-rencontrés"></a>

## Faults encountered

Initial reproduction `validation/open-async-nested-exchange-join.crust`
was refused by the depth guard of the compiler. After connection,
elle produit `8`, then `9`, with cleaning and re-use.

The first passage of the new suite used match scoring
consuming replace/try_push on intermediate runtime envelopes.
The snippet generator has been fixed to use their already taken syntax
The expected results and memory oracles have not changed.
A subsequent passage also noted a final acclaim absent in the new
Snippet with separate pools, corrected before its native execution.

The lack of implementation discovered by the additional depths was
a list of results modes frozen when importing the effects module
Async. It therefore depended on the types already encountered in the process.
dynamic view of the registry replaces this copy, including for effects
field delays. Empty loads of try_push are also recognized
at every depth in symbolic parameters.

<a id="exécutions-et-preuves"></a>

## Executions and evidence

Targeted commands use `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0
python3 -m unittest test_async_nested_exchange_join -v`. The harness compiles
C11 with pthread, Wall/Wextra/Werrar, UBSan and
`-fno-sanitize-recover=all`. Sanitizer diagnostics fail the test.

Newspapers in `validation/` :

| Journal | Result |
| --- | --- |
| async-nested-exchange-join-first-o0.log | Initial reproduction executed, code 0 |
| async-nested-exchange-join-second-o0.log | 7 methods, 1,983 s, code 1 ; generator match rating |
| async-nested-exchange-join-third-o0.log | 7 methods, 5.394 s, code 1 ; modes frozen in async effects |
| async-nested-exchange-join-fourth-o0.log | 7 methods, 8,156 s, code 0 |
| async-nested-exchange-join-fifth-o0.log | 8 methods, 8,134 s, code 1 ; no snippet hook added |
| async-nested-exchange-join-sixth-o0.log | 8 methods, 8,848 seconds, code 0; 21 executions and six refusals |
| async-nested-exchange-join-regression-o2.log | 135 methods, 121.391 s, code 0; O2/UBSan |

Regression control:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
  test_async_nested_exchange_join test_async_exchange_join \
  test_async_handle_exchange_results test_async_handle_exchange_calls \
  test_async_option_join test_async_handle_option_results \
  test_async_handle_option_calls test_async_structure_effects \
  test_factory_owned_effects test_public_handle_contracts \
  test_select_source test_task_wakes -v
```

<a id="portée-et-suite"></a>

## Scope and follow-up

Targeted results are compared to their expected values, their traces of
destruction and re-use of restricted pools. The existing harness of Select and
The wake-up tests have succeeded in regression (including their existing independent models).
no independent adversarial transfer campaign or audit is claimed.
ASan and other C compilers are not exercised in this batch.

The generalization of envelopes around Option<A<Int>>, allocations
The catch of handles remains distinct and open.
inactive instance are not added: diagnosis
existing is reproduced in `async-nested-exchange-public-layout-first.log`.
This refusal occurred before C and did not prove anything about its provisions.
The public arbitrations scheduler/mutex identified in design-buffer remain
This lot does not end the overall implementation objective.

The seven modified Python files are compared to the backup
`/tmp/crust-before-nested-exchange-joins`. The diffs are kept under
`validation/async-nested-exchange-join-*.py.patch`.

The depth program three and its generated C are retained in
`validation/async-nested-exchange-depth3.crust` and `.c`. The inspection of
cleaning conditions confirms the test of each runtime status before
access to the load; the implementation of this program is subsequently covered.
The next restriction is reproduced in both entries in
`validation/open-async-nested-option-join.crust` and `.log` : a returnable task
`Result<Option<A<Int>>,runtime::Error>` Can't be launched yet.
