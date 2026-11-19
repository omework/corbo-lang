[Français](TYPED_VECTOR_OPTIONS_CYCLE-fr.md)

# Contrats synchrones Option<A<T>>

<a id="règles-et-réalisation"></a>

## Rules and implementation

This batch applies VE3, H1–H3, U1, B1–B5 and F3–F4 to the handle options
No normative rules are changed.

`handle_option_types.py` describes the public type Option<A<T>> and its T load.
The parser, parameters and function results, annotations,
if/loop junctions and calls now retain T instead of assuming Int.
The type of pool of a symbolic load is fixed by the signature.

An empty option now keeps a descriptor typed in the compiler,
with proof of absence of charge and no source/identity of allowance.
This descriptor is a verification metadata; it does not assign any objects in
The C maintains its VectorHandleResult and its indicator of
presence. Some absent is an inaccessible path; drop only destroys the load
This means that None of the Option type<A<Point>> is not interchangeable with
Option type None<A<Int>>.

Storage requirements know that an option parameter<A<T>> contains, the case
The relay of an option also retains the contract of
variants of its nominal load. Newly typed async signatures remain
explicitly refused until they were connected to runtime envelopes.

<a id="cas-exécutés"></a>

## Cases implemented

Eight methods in `tests/test_typed_vector_options.py` : 21 native executions
and eleven invalid programs each controlled by verify_program and compile_source.

- Some and None, annotations, named result and then transferred to a relay.
- None keeps his type in a function argument; a bad type is refused.
- Options from an if or loop/break, present or empty; junction of
  two types of incompatible charges refused even for two empty options.
- The option survives the empty vector pool, but cannot carry a load of which
  The pool ends before it. An empty option does not invent this dependency.
- Parameter consumer Option<A<Point>> restoring the Some handle or a
  replacement allowance in case of None.
- Local annotation Point of a charge A<Point> refused.
- Direct destruction, result named/moved, cleaning and re-use at capacity one.
- Result without use, dual consumption, reason ignoring load and absence
  transfer to a rejected parameter.
- Borrowing used before pop allowed; use remaining after pop refused.
- String, Vector<Int> and Vector<u8> cross the contract, are read and then destroyed,
  before re-use of slots in their pools.

The harness uses C11/pthread, Wall/Wextra/Werrar, UBSan and
`-fno-sanitize-recover=all`. The output code of each execution is checked.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_vector_options -v
```

`validation/typed-vector-options-targeted-third-o0.log` : eight methods,
7,113 s, code 0.

<a id="régressions"></a>

## Regressions

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
 test_typed_vector_options test_typed_handle_vectors test_typed_vector_exchanges \
 test_storage_requirements test_async_handle_vector_pop \
 test_async_handle_option_calls test_async_handle_option_results \
 test_async_option_join test_async_nested_option_join test_async_failure_only_results \
 test_foundation_rules.FoundationTests.test_buffered_handle_pop_passes_statically_empty_option_from_function \
 test_foundation_rules.FoundationTests.test_buffered_handle_pop_moves_across_explicit_scope_entries \
 test_foundation_rules.FoundationTests.test_buffered_handle_pop_survives_break_and_cleans_continue -v
```

`validation/typed-vector-options-regression-o2.log` 87 methods, 100.393 s,
Code 0. The suites use O2/UBSan; the three Foundation methods use
their native O2/UBSan configuration and explicit legacy-reset profile.
Regressions include empty Int options, async results without load,
Envelopes interlocked and cleaning of already tested losing branches.
They do not prove the async integration of the new typed loads.

<a id="traces-et-limites"></a>

## Traces and limits

The initial refusal is retained in
`validation/open-typed-vector-option-contract.crust/.log`. The C now
product is `validation/typed-vector-option-point.c`.

- `typed-vector-options-first-o0.log` : the initial program runs.
- `targeted-o0` : Option<A<Point>> relay lost variant contract
  The invariant of the backend signaled it. Resolution of this contract
  extended to options, without removing the invariant.
- `targeted-second-o0` 7 methods, 7.211 s, code 0.
- `targeted-third-o0` : addition of the case of borrowing and transfer of arguments,
  Eight methods, code 0.

Differences with the backup before this lot are archived in
`validation/typed-vector-options-*.patch`.

Charges containing references or allowances themselves, enums
The general principles and the async signatures/envelopes typed remain to be completed.
The deviation of the old T return signatures accepting A<T>, documented in
TYPED_VECTOR_EXCHANGES_CYCLE.md, remains open: the refusal of a local annotation
does not prove control of all signatures.

No in-depth adversarial campaign, mutation or random generation
The models already present in the selected suites
The global construction project is not completed and these tests are still being carried out.
do not constitute general proof of safety.
