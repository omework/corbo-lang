[Français](ASYNC_HANDLE_VECTOR_REPLACE_CYCLE-fr.md)

<a id="remplacement-de-handles-de-vecteur-dans-async"></a>

# Replacement of vector handles in async

<a id="règles-appliquées-et-implémentation"></a>

## Rules applied and implementation

Application of H1–H2, VE3, U1, B1–B5, AS8–AS12 and SL1–SL2, unchanged
The index is then the inward value.
receives the new handle and the result has the old one. On invalid index,
the vector remains unchanged and the result has the input.
target does not change; only the responsibility for cleaning is transferred.

Async state generator connects direct match and result forms
named to vector_replace and VectorHandleResult. The result content is
owned on both branches, unlike Option: its drop is therefore
Unconditional extraction in an arm emptys its source pointer and gives
responsibility to the recipient of the arm. Possible sources of the old and
The value of the input shall remain distinct for this extraction.

The recipient is reserved during the assessment of the arguments, including the
await. Incoming sources are published in the effects of the vector in order to
to survive normal return or destruction of a suspended branch of
Select. The result can be moved, stored during yield or destroyed
Directly. Signatures of functions carrying the complete envelope
are not connected by this lot.

<a id="cas-ciblés"></a>

## Targeted cases

Seven methods in tests/test_async_handle_vector_replace.py. The final version
contains fourteen native executions and seven invalids at both entrances.

- Successful replacement and invalid index; returned value, saved value
  in the vector, the unique destruction of the old and the ingress.
- Missing arrow and reuse of transferred input refused.
- Named result, yield, displacement and drop; missing and double usage
  Direct drop tested on success and error.
- Borrowing completed before replacement allowed; borrowing still used after and
  Shared receiver refused.
- Inward index and allocation produced by two expected tasks: the order
  The values are 1, 2, and then 7, 8 and 9.
- Losing Select suspended after replacement: the old one is destroyed once,
  the new one remains in the vector and its pool remains followed.
- Pool local too short for the inserted value refused.
- Return of the old or replacement emergency, via direct or
  The vector and pool of the input disappear before
  use of the result, which the outdoor pool survives.

The initial case validation/open-async-handle-vector-replace.crust was refused
both entries with "expression array_handle_exchange not supported".
It is now executed and produces 7, 8, 9. No new semantic gap has been achieved.
was discovered in the targeted passes and the regressions performed.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| async-handle-vector-replace-first-o0.log | Six methods, 3.523 s, code 0 |
| async-handle-vector-replace-second-o0.log | Seven methods, 5,466 s, code 0; before adding both cases of direct drop |
| async-handle-vector-replace-regression-o2.log | 72 methods, 77.334 s, code 0, with both direct drop cases |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_replace -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_replace test_async_handle_vector_pop test_async_handle_vector_push test_async_handle_vector_remove test_async_option_join test_factory_owned_effects test_select_source test_foundation_rules.FoundationTests.test_handle_vector_replace_error_return_preserves_parameter_identity test_foundation_rules.FoundationTests.test_handle_vector_replace_match_requires_explicit_transfer test_foundation_rules.FoundationTests.test_buffered_handle_replace_preserves_result_after_vector_changes -v
```

C11/pthread, warnings in error, fatal UBSan. The Foundation suite
retains its legacy profile legacy-reset; reset remains removed from the prototype.
The regression includes the existing Select poll/cleaning model. No new independent model or campaign of
mutations. The tests cover agreed cases and their related regressions;
the detailed audit remains separate. No general evidence of security is claimed.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Perimeter: Vector<A<Int>> in async states, with local results and return
The source of the old boxes remains precise.
The signature(s) carrying the goods in the same position as the signature(s) carrying the goods in the same position as the signature(s) carrying the goods in the same position.
Result<A<Int>,A<Int>>, constructions and other vector returns remain
to be completed in the relevant async paths.

The next case reproduced is validation/open-async-handle-vector-try-push.crust
and .log: handle try_push is refused to both entries, "expression
"Open Public Arbitrations"
remain unchanged.

Snapshot : /tmp/crust-before-async-handle-vector-replace/.
Diff : validation/async-handle-vector-replace-async_lowering.py.patch.
