[Français](TYPED_ASYNC_HANDLE_VECTORS_CYCLE-fr.md)

<a id="cycle--vecteurs-de-handles-typés-dans-les-états-async"></a>

# Cycle — Handle vectors typed in async states

<a id="règles-et-portée"></a>

## Rules and scope

Application of H1–H3, VE1–VE4, F2–F4, U1, B1–B5 and capture rules,
suspension and cleaning AS2/AS8–AS14, without change of standard.
VALIDATION_GUIDELINES.md, the draft index and the normative rules were
The recommendation to focus on the cases selected and
direct regressions remain applied.

This batch connects the typed containers and their local results in a task.
He doesn't close the signature building `Option<A<T>>` async :
`validation/open-typed-async-vector-option.crust/.log` remains refused by the parser
for T not Int. The return of these options from the task, the envelopes of join
and the corresponding parameters are the explicit continuation of the work.

<a id="implémentation"></a>

## Implementation

`async_lowering.py` uses the vector element type for capture,
injected/local pools, synchronous calls, push, remove, pop local and replace
local. The type of load is retained after extraction of Some/Ok/Err and
suspension. Local annotations Option/Result are checked even when
the load may be absent. The previous Int digital forms remain
taken over.

The vectors created in the state call `vector_new_handles`The provision
remains the Cell cells* The existing runtime ensures the destruction of the
elements from their original pools. No target displacement, no
implicit conversion and no new container runtime are introduced.

Owned/borrowed field charges remain explicitly refused
as in the synchronous path: their transitive dependencies are not yet
This refusal is a limit of implementation, not a new rule.
It also applies to async parameters and pools created in a state.

<a id="défauts-rencontrés-et-corrigés"></a>

## Deficiencies encountered and corrected

1. The first building emission used the digital manufacturer,
   whose parameter tested was the direction of growth and not the property of the
   The vector did not destroy the remaining element.
   re-use failed with `pool capacity exceeded`. The call to the manufacturer of
   handle corrects the cleanup; the four Point of the scenario is destroyed.
2. After generalization of the container, the control of replace retained Int
   The program
   `validation/typed-async-handle-vectors-wrong-replace.crust` inserting a
   A<Int> in Vector<A<Point>> and was accepted at both entries.
   is executed in native. Before/after logs keep acceptance and then
   refusal `allocation Point`. Control and result now use
   the actual type of the element.
3. A growing load sample re-used a name already declared in
   the async state; it was renamed to remain within the existing perimeter.
   generalization of masking in async states is not claimed here.

<a id="scénarios-exécutés"></a>

## Scenarios implemented

`tests/test_typed_async_handle_vectors.py` contains nine methods: 16
Native programs admitted and 17 invalids controlled by both entries.

- Shared, mutable or transferred capture; length reading and cleaning.
- Push/remove with yield and synchronous relays; explicit transfer required,
  incorrect type and local value not allocated refused.
- Local pools, two pools of elements, destruction of extract and
  remaining, re-use of both slots.
- Some/No typed stored around yield, synchronous call returning option,
  Bad type of annotation refused even on None.
- Destruction of a task still inactive: unexecuted body, vector and
  clean contents, source transferred unusable.
- Loads String UTF-8, Vector<Int> and Vector<u8> extracted and read after yield.
- Replace with valid or invalid index, annotation Result typed, cleaning of the
  two pools and two variants.
- Explicit refusal of the out-of-connection field dependencies.

The C of the cleaning scenario is retained in
`validation/typed-async-handle-vectors-cleanup.c`, with its source `.crust`.

<a id="exécutions-et-preuves"></a>

## Executions and evidence

- First push/remove execution: code 0,
  `validation/typed-async-handle-vectors-first-o0.log`.
- First local option typed: code 0,
  `validation/typed-async-handle-vectors-local-pop-o0.log`.
- First target O0: five methods, 4,440 s, code 1 ; cleaning defect.
  `validation/typed-async-handle-vectors-targeted-o0.log`.
- Second target O0: five methods, 4,954 s, code 0.
  `validation/typed-async-handle-vectors-targeted-second-o0.log`.
- Third target O0: six methods, 4,462 s, code 1 ; name reused in
  the sample. `validation/typed-async-handle-vectors-targeted-third-o0.log`.
- Target 4 O0: six methods, 5,988 s, code 0.
  `validation/typed-async-handle-vectors-targeted-fourth-o0.log`.
- First regression O2: 82 methods, 79,791 s, code 0, before last
  Replacement and complex loads checks.
  `validation/typed-async-handle-vectors-regression-o2.log`.
- Final target O0: nine methods, 7.286 s, code 0.
  `validation/typed-async-handle-vectors-targeted-final-o0.log`.
- Final regression O2: 84 methods, 80.216 s, code 0.
  `validation/typed-async-handle-vectors-regression-final-o2.log`.
  Selection: typed_async_handle_vectors, typed_handle_vectors,
  typed_vector_options, async_handle_vector_push/remove/pop,
  async_handle_option_calls/results, async_handle_vector_replace/try_push and
  strict_structure_returns (modules test_ correspondants).

The tests go through verify_program and compile_source then C11/pthread,
Wall/Wextra/Werrar and fatal UBSan. Traces, exits and capacity to
Reusing pools are explicit oracles. No new models,
mutation generator or campaign is not added; existing regressions
Their success is not a general proof.

<a id="artefacts-et-limites-restantes"></a>

## Remaining artifacts and limits

Snapshot initial : `/tmp/crust-before-typed-async-handle-vectors`.
Two exact and obvious diffs of prints:
`validation/typed-async-handle-vectors-*.patch` and
`validation/typed-async-handle-vectors-changes.json`.

These include: async parameters/returns of options and typical results,
their envelopes of joins, charges containing loans or allowances,
generalisation of box borrowing/targets typed beyond the routes already
The other points of the global checklist are kept.
is not declared safe for all compositions and the overall objective remains
actif.

Final regression control:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_typed_async_handle_vectors test_typed_handle_vectors test_typed_vector_options test_async_handle_vector_push test_async_handle_vector_remove test_async_handle_vector_pop test_async_handle_option_calls test_async_handle_option_results test_async_handle_vector_replace test_async_handle_vector_try_push test_strict_structure_returns -v
```
