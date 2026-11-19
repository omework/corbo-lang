[Français](ASYNC_NESTED_OPTION_JOIN_CYCLE-fr.md)

<a id="enveloppes-runtime-imbriquées-autour-doptionaint"></a>

# Runtime envelopes nested around Option<A<Int>>

<a id="règles-et-réalisation"></a>

## Rules and implementation

Application of RT6, AS8–AS14, H1–H2, VE3, U1, F3–F4 and SL1–SL2.
No normative rules are changed. Waiting for a handle always adds
`Result<T, runtime::Error>`, even when T already contains runtime envelopes.
Some content remains attached to its pool; None has no allowance.

The compiler now recursively describes the envelopes around
The common registry of provisions is available in the
`result_envelopes.py` ; `option_join_types.py` and `exchange_join_types.py`
configure leaf families, with their conditions of presence
The source registers remain separate: Option has a
load possible; replace/try_push keep their provenances by arm.

The descriptions give the interior type, type C, the handle path and
The extraction removes a single envelope.
contains one status per envelope; it cleans the load only if all the
status runtime indicates Ok and if the sheet is Some. Addresses of
Targeted allocations are not displaced. Types are recorded from
signatures; caches avoid reconstructing the same descriptions.

Contracts, public signatures, transfers, results captures, returns
Async and factories use these modes with varying depth.
prepared arguments and losing branches of Select consult the same
conditions of presence.

<a id="cas-exécutés"></a>

## Cases implemented

Seven methods of `tests/test_async_nested_option_join.py` : 25 native executions
and seven invalid programs, controlled by verify_program and compile_source.

- Some and None, two, three and five runtime envelopes, successive extraction.
- Failed to inject at each of the three launch levels, with and without element.
- Public handle, synchronous wait helper and relay of the result.
- Extraction from async, was from an inactive instance produced by a factory.
- Capture executed or destroyed inactive; prepared result before suspension and
  Cleans in Select's loser. Counting destruction and re-use.
- Result transferred by if or loop, explicit consumption and cleaning.
- Result retained after the vector has disappeared, when the element pool
  The variant where this pool disappears is refused.
- Refusal of the absent transfer, of the re-use after transfer, of the result
  without use, of double consumption, of the reason ignoring the charge and of a
  access to the vector still reserved by its execution.

The C is compiled in C11 with pthread, Wall/Wextra/Werrar, UBSan and
`-fno-sanitize-recover=all`. Sanitizer diagnostics fail the test.
The depth limit of these types is no longer hard coded; only the
The samples are carried out in depth and are experimental evidence in this batch.

<a id="défauts-et-étapes"></a>

## Failures and steps

Reproduction `validation/open-async-nested-option-join.crust` was refused
by the guard "three levels of Result". It now runs and returns
the pool slot before the new allocation.

The first passage of the new suite revealed a signature filter of the
Lowering async remained limited to the previously known modes.
optional modes are now taken into account by this filter.
The expected values and oracles of destruction have not been weakened.

Newspapers in `validation/` :

| Journal | Result |
| --- | --- |
| async-nested-option-join-first-o0.log | Initial reproduction executed, code 0 |
| async-nested-option-join-second-o0.log | 7 methods, 0.822 s, code 1 ; incomplete signature filter |
| async-nested-option-join-third-o0.log | 7 methods, 9.689 s, code 0; 25 executions, seven refusals |
| async-nested-option-join-regression-o2.log | 142 methods, 135,869 s, code 0; O2/UBSan |

The targeted suite is launched with:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_nested_option_join -v
```

The regression uses:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
  test_async_nested_option_join test_async_nested_exchange_join \
  test_async_exchange_join test_async_handle_exchange_results \
  test_async_handle_exchange_calls test_async_option_join \
  test_async_handle_option_results test_async_handle_option_calls \
  test_async_structure_effects test_factory_owned_effects \
  test_public_handle_contracts test_select_source test_task_wakes -v
```

<a id="portée-et-limites"></a>

## Scope and limitations

The regression suite successfully implemented existing models of
Select and Wake Up Clean/Clean. No new general model, mutation test or adversarial audit
ASan and other C compilers are not claimed.
The tests cover the programs and paths mentioned, without
prove general safety or all depths.

The optional sheets covered bear A<Int>.
The results of simple allowances and other types of allowances remain open.
publics scheduler/mutex and capture of hands in an inactive instance
The overall objective remains active.

The eleven Python files modified or created are compared to
`/tmp/crust-before-nested-option-joins`. The diffs are archived under
`validation/async-nested-option-join-*.py.patch`.

The depth program three and its generated C are retained in
`validation/async-nested-option-depth3.crust` and `.c`. L'inspection confirme
that the cleaning condition combines the three running status and the status
Some of the sheet; the program is subsequently executed targeted.
The next restriction is reproduced in both entries in
`validation/open-async-nested-owned-join.crust` and `.log` : start a task
already turning two envelopes around A<Int> remains refused.
