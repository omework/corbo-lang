[Français](TYPED_ASYNC_OPTIONS_CYCLE-fr.md)

<a id="cycle--options-dallocations-typées-en-async"></a>

# Cycle — Async-typed allocation options

<a id="règles-et-portée"></a>

## Rules and scope

Application of rules H1, VE1–VE3, F2–F4, U1, B1–B5, AS2/AS8–AS14 and MT5–MT6.
The normative documents remain unchanged.
The index of decisions and the rules concerned were consulted; the scope of the decisions was
The implementation of the selected cases and their direct regressions remains.

The batch connects Option<A<T>> to async parameters and results, to expectations
Inactive and launched, interlocking Results envelopes and public handles.
The types used are Point, Int, String, Vector<Int> and Vector<u8>.
containing loans or allocations themselves remain an open site.

<a id="implémentation"></a>

## Implementation

- The register of options envelopes statically distinguishes each type of
  load, with Injective IDs derived from its UTF-8 spelling.
  Envelopes share existing C representation: status and Cell*.
- The parser, the contracts of results and constraints, the effects async,
  public handles and lowering keep the type until extraction
  Final cleaning tests the status of each envelope and Some/None.
- The possible variants of an element extracted from a vector are those of
  its type when the container does not provide precision per variant.
  A source of task keeps its known variants, if not all of the
  The verification of compliance with the contract remains in place.
- Pool runtime is not changed. Transfers copy descriptor
  The result and its pointer, without moving the target of the allocation.

<a id="défauts-rencontrés-et-corrigés"></a>

## Deficiencies encountered and corrected

1. The parser explicitly refused Option<A<T>> signatures, not Int.
   The case recorded `validation/open-typed-async-vector-option.crust` is
   Now accepted at both inputs and executed with outputs 7 then 9.
2. After initial connection, join contracts and field effects
   Async still produced the Int option identifier.
   The C was wrongly issuing the diagnosis.
   "handle pop: no possible element" on Some(Point).
   The program and C before correction are retained in
   `validation/typed-async-options-nested-before.crust/.c`.
3. The public handle relay kept the source, but omitted the
   variants of the load from the vector. Internal control detected
   "non-receipt variant of the contract of result". The minimum case is in
   `validation/typed-async-options-public-before.crust` ; hand-testing
   public cover after correction.
4. A readability edition has momentarily produced a Python error to
   import; it is recorded in `typed-async-options-refactor-import-error.log`.
   It was corrected before the final passes.
   regular owners also retain its original envelope.

<a id="cas-exécutés"></a>

## Cases implemented

Eight targeted methods: 26 C executions, eight of which failed to submit
Injected, and 17 invalid programs controlled at the audit and
compilation. Eighteen programs admitted pass the two entries before execution;
The eight injections start from the compiled C and simulate LaunchFailed.

- Some/None at the depths of join 1 and 3, with re-use of the capacity pool 1.
- Expectation named, synchronous manufacturing, capture and then return of option,
  typed annotation and synchronous relays.
- Public handle, envelope relay, async capture and extraction after wait.
- Launch failure at each of the three levels; single destruction and
  replacement allowance in the pool of origin.
- Drop an inactive task and failure of its launch: destroyed capture,
  body not executed in the inactive case.
- Result surviving to vector, but transfer refused if pool of the
  load does not survive; premature access to the vector refused before join.
- Incorrect types refused even for None; transfers absent, dual use
  and ignored result refused. Int and Point options coexisting in a program.
- UTF-8 Thong loads and digital vectors transferred into options,
  expected, extracted and read after suspension.

The final C of three envelopes is retained in
`validation/typed-async-options-nested.crust/.c` : refund of descriptors
`frame->result`, `task_async_take_into` Then extract the pointer from Some.
The artificial C failure marker before correction is no longer present.

<a id="exécutions"></a>

## Implementation

- Initial registered case: code 0; log `typed-async-options-first-o0.log`.
  Despite its name, this command did not have CRUST_TEST_OPT and therefore uses
  **O2**, default value of the harness.
- Intermediate targets O0: 7 methods, 8,983 seconds and 8,741 seconds, code 1,
  three failures; third pass 9,356 s, code 1, a variant failure.
- Target 4 O0: 7 methods, 10.778 s, code 0.
- Final target O0: 8 methods, 11,610 s, code 0,
  `validation/typed-async-options-targeted-final-o0.log`.
- Target 5 O0: 8 methods, 11,547 s, code 0; before last
  explicit preservation of the branch of ordinary proprietary results.
- Final regression O2: 119 methods, 163.268 s, code 0,
  `validation/typed-async-options-regression-o2.log`.

The names of regression suites are in
`validation/typed-async-options-test-selection.txt`. Reproduction :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_async_options -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_typed_async_options test_typed_async_handle_vectors test_typed_vector_options test_async_handle_option_results test_async_handle_option_calls test_async_option_join test_async_nested_option_join test_async_nested_exchange_join test_recursive_owned_join test_public_handle_contracts test_public_handle_types test_async_child_field_effects test_strict_structure_returns test_typed_vector_exchanges -v
```

Harness compiles in C11/pthread with Wall/Wextra/Werrar and fatal UBSan
(`-fsanitize=undefined -fno-sanitize-recover=all`) Expected values and
destruction is verified by the tests; no result is deducted
only from the acceptance of the compiler.

<a id="traçabilité-et-limites"></a>

## Traceability and limitations

Snapshot initial : `/tmp/crust-before-typed-async-options`. Seven files from
modified compiler and a new suite; exact diffs and prints in
`validation/typed-async-options-changes.json`. Intermediate logs remain
The existing interlocking independent retention model has been replayed in the
Regression: seven admitted programs implemented and five expected refusals.
n
mutations ou de recherche adversariale approfondie n’a été lancée. Les
LaunchFailed injections exercise the already defined failure paths.

The continuation does not prove general security or all the arrangements.
Async signatures of replace/try_push typed exchanges remain open:
`validation/open-typed-async-vector-exchange.crust/.log` records refusal
The following are the main points of the report:
transitive dependences of charges, other general compositions
and the work sites indicated in IMPLEMENTATION_CHECKLIST.md. Reset remains removed
by default; this lot n
