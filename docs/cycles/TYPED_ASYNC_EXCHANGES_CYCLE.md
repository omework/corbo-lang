[Français](TYPED_ASYNC_EXCHANGES_CYCLE-fr.md)

<a id="cycle--résultats-async-typés-de-replace-et-try_push"></a>

# Cycle — Async results typed for replacement and try_push

<a id="règles-et-portée"></a>

## Rules and scope

Application of H1–H3, VE1–VE4, F2–F4, U1, B1–B5, AS2/AS8–AS14, MT5–MT6
and rules for cleaning the losers of Select. Normative documents
The decision index is the same.
and the relevant rules were read in this session.
the functions selected and their direct regressions.

This batch connects the signatures async Result<A<T>,A<T>> and Result<(),A<T>>,
their catch and their runtime envelopes. It prolongs the exchanges
The tasks of the two bodies are:
Point, String, Vector<Int> and Vector<u8>, with regression of the Int route.
The elements containing transitory dependencies remain an open site.

<a id="implémentation"></a>

## Implementation

- The trade register distinguishes the type of load and the form of result
  at every depth. L-ABI C remains shared: status and pointer Cell*.
- Parseur, contracts, async effects, public handles and lowering keep
  the actual type and provenances of each branch. Returns and parameters
  n
- The analysis of storage requirements now retains the loads of a
  exchange after wait, directly or through a handle.
  The contract sources; it does not promote local value in a pool.
- Cleaning the result of try_push depends on its variant: Ok(())
  destroys the allocation placed in the vector; Err keeps and cleans
  This check is used for the prepared arguments, the
  captures, inactive tasks, expectations and losers of Select.
- A nominal variant unprecision exchange charge retains the
  The internal control of the contract remains active.

No changes in allocators/pools of runtime and no displacement of
the target of the allowances is not introduced.

<a id="défauts-rencontrés"></a>

## Faults encountered

1. The explicit refusal of typed Async signatures prevented the program
   `validation/open-typed-async-vector-exchange.crust`. It is now
   accepted at both entries and executed: 7, 8, 9.
2. The analysis of storage requirements produced a load-free value after
   await. Valid relays were rejected with "waiting for an allowance" or
   "requires a result of repositioning or try_push". The result descriptor and
   its sources by branch are now being propagated in this analysis.
3. A relay of results wrapped retained the source of the exchange but
   not possible variations of Point. Internal control signalled
   "non-receipt variant of the contract of result". Type information is
   kept without removing this control.

The first failing newspapers are kept. The second attempt was
interrupted after failure of an assertion of the edit script, before application
The two existing models
included in regression are replayed without modification: four combinations
of two parameters (four admitted and four refused), and 36 cases of
capture permits (18 admitted and 18 refused) and they do not model alone
new exchange results.

<a id="scénarios-ciblés"></a>

## Targeted scenarios

Nine methods, 26 C executions, five with LaunchFailed injected, and 15
invalid programs controlled by verify_program and compile_source.
21 executions without injection pass both inputs before generation/execution
C ; the five injections start from the compiled C and simulate a failure of the scheduler.

- Replaces with valid or invalid index, separate pools of origin and depths
  of join 1/3: former returned element or incoming element, read resident element,
  four point destructions and re-use of the two pools.
- Inactive wait named, synchronous factory, sync/async relays, annotation
  exact result and type/transfer errors refused.
- Public handle, three envelopes, capture/restitution/extraction after await.
- Launch failure at each level; lentrant is cleaned, vector keeps
  its former element, the two pools are reusable.
- Capture of each branch of the result, inactive drop and LaunchFailed:
  no body executed in inactive case, single cleaning of the received charge.
- Try_push accepted or refused on an area of 1 MiB actually full;
  The accepted element remains in the vector, the rejected remains in Err.
- Capture of both variants in an inactive task or a loser of
  Select suspended: cleaning according to the actual presence of the load.
- UTF-8 Thong loads and digital vectors read after transfers and suspensions.
- Sources too short, access to the vector before join, use after transfer,
  result ignored and double consumption refused.

The source and C of three envelopes are stored in
`validation/typed-async-exchanges-nested.crust/.c`. The statutes guide the
extractions and cleanings; the transferred value remains the Cell pointer*.

<a id="preuves-dexécution"></a>

## Evidence of enforcement

- First registered program O0: code 0,
  `validation/typed-async-exchanges-first-o0.log`.
- Target 1 O0: eight methods, 7.557 s, code 1, three failures.
- Second attempt: interrupted, code 130, not validation.
- Third target O0: eight methods, 9.285 s, code 1, a failure of variants.
- Target 4 O0: eight methods, 10.419 s, code 0.
- Final target O0: nine methods, 12,541 s, code 0,
  `validation/typed-async-exchanges-targeted-final-o0.log`.
- Final regression O2: 135 methods, 183.427 s, code 0,
  `validation/typed-async-exchanges-regression-o2.log`.

Exact selection: `validation/typed-async-exchanges-test-selection.txt`.
Reproduction :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_async_exchanges -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_typed_async_exchanges test_typed_async_options test_typed_async_handle_vectors test_typed_vector_exchanges test_typed_vector_options test_async_handle_exchange_calls test_async_handle_exchange_results test_async_handle_vector_try_push test_async_exchange_join test_async_nested_exchange_join test_async_nested_option_join test_recursive_owned_join test_public_handle_contracts test_storage_requirements test_strict_structure_returns -v
```

The harness compiles in C11/pthread, Wall/Wextra/Werrar and fatal UBSan
(`-fsanitize=undefined -fno-sanitize-recover=all`) The tests check the
expected values and destruction, not just acceptance of the source.
Targeted passes are not a general proof of safety.

<a id="traçabilité-et-suite"></a>

## Traceability and continuity

Snapshot : `/tmp/crust-before-typed-async-exchanges`. Eight compiler files
and a new suite; exact diffs and prints in
`validation/typed-async-exchanges-changes.json`. No reference model
No campaign of mutation or deep adversary exploration.
The injections of the scheduler exercise the already defined failure paths.

The transitive dependencies of vector elements, other types and
compositions not yet connected remain open. The next case recorded,
`validation/open-vector-handle-borrowed-fields.crust/.log`, is still refused
explicitly at both entries: it stores an item allocation containing &Int
Then remove it and use its reference before destruction.
The other part of the construction site is owned by the owners.

Reset remains removed by default. The public interfaces of the scheduler and the
construction of mutex still to be arbitrated. The overall objective is not finished.
