[Français](ASYNC_COLLECTION_CREATION_CYCLE-fr.md)

<a id="cycle--création-directe-de-collections-dans-les-états"></a>

# Cycle — Direct creation of collections in the states

Monitoring: The connection of local pools to states is described in
[the next cycle](ASYNC_LOCAL_POOLS_CYCLE.md), with its validation status.

Follow-up of [injected pool cycle]](ASYNC_POOL_INJECTION_CYCLE.md).
No regulatory rules modified. References: A1–A4/A6, B1–B5, V4/V5,
T6/T11, U1, L1/L6, H1, VE1, TX9/TX10/TX21, G9/G12, AS2/AS8–AS13 and RT8.
The seven drafts remain partially implemented.

## Raccordements

`p.new()` construit maintenant directement String, Vector<Int> ou Vector<u8>
In a native or async body that receives the corresponding pool.
The empty construction retains the variable UTF-8.
does not transform a String/Vector construction into an Int creation.
The existing runtime manufacturers are reused, without modification of the
Without annotation applicable, the limit transmitted
remains zero, selecting the existing policy without annotated region.

The result keeps the collection type, address and provenance at
The following is a summary of the results of the study:
origins also recognizes the wrapper of a direct creation transfer:
a second unreturned pool is not held for no reason. The pool really
used must always survive the result.

Construction tests revealed a similar lack: `&vector[i]` and
`&mut vector[i]` n) were not connected to the states for Int/u8.
now use the control of the runtime index and book the collection
The loans provide for the protection of the environment and the environment.
collection during their last use or that of a child task.
remains conservative at the collection level; no general evidence of
The number of dynamic cells is added.

<a id="contre-exemples-et-corrections-de-validation"></a>

## Counter-examples and validation corrections

The programme [minimum](../../validation/open-async-collection-new.crb) was
refused with "direct creation in a state requires an injected Pool<Int>".
The [initial diagnosis]](../../validation/async-collection-new-before.log), on
[C final](../../validation/async-collection-new.c) and
[trace native](../../validation/async-collection-new-artifact.log) are retained.

The first passage found the lack of direct borrowing of boxes and a
fixture error: `pool` had been used as a variable name while
the parser recognizes it as a constructor. The extended passage then
refused a validly mutable reception without `let mut`. The fixings were
negative variants also contained a second final drop;
this parasitic refusal was removed before the final validation so that the scenario
The initial newspapers are still failing.

<a id="exécutions"></a>

## Implementation

`tests/test_async_collection_new.py` 14 methods, 34 normal executions,
seven diagnosed runtime stops and 64 negative checks.
Clang C11 pthread, O0/O2, blocking warning and fatal UBSan. The seven stops
cover three pool exhaustions before replacement and four indices
EAGAIN is also injected into the
three normal runs to test the launch error and re-use.

- [O0 final](../../validation/async-collection-new-final-o0.log) : 14 methods,
  13,932 s, OK.
- [Baseline O2 and mutations](../../validation/async-collection-new-mutations-o2.log) :
  14 methods, 25,113 s, OK before injection.
- The minimum C artifact was also compiled and executed separately at O2 with
  UBSan fatal ; il affiche `été` and destroys his collection once.
- [Interactions O2](../../validation/async-collection-new-interactions-o2.log) :
  97 methods, 69,168 s, OK, including vector operations, push_new,
  removes, borrowed returns, loops, u8 borrowings and pool requirements.
- [Native/Runtime Regression O2](../../validation/async-collection-new-native-o2.log) :
  177 methods, 154,100 s, OK. This pass includes the 14 new methods
  and the module of the injected pools. It partially covers the selection
  d) interactions; their accounts do not represent separate tests.
- [Mutations of replayed pools](../../validation/async-collection-new-pool-mutations-o2.log) :
  baseline of 19 methods, 11,525 s, OK; the seven faults of the previous batch
  The type mutation is adapted to the new type of mutation.
  control; the expectations of the tests are unchanged.

Reproducible commands from the root:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_collection_new -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_collection_new_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_pool_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_vector_operations test_async_vector_push_new test_async_vector_remove test_async_loop_references test_async_reference_returns test_sync_byte_borrows test_pool_requirements -v
```

The oracles compare the expected values, the descriptor addresses,
The number of destructions and the re-use of limited pools.
vectors replay their independent list models; no model
the Auditor General or the Orders n

Six isolated errors are detected with unchanged tests: erasure of the
type of collection, loss of direct return origin, omission of
cleaning, poor pointer index, booking absent during index,
The tests detect the potential for the transfer of the
incorrect acceptances and refusals, as well as errors in execution.
This result is not a general detection rate.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Annotated async blocks, locally created pools in states and states
Other types of collections/pools remain open.
`validation/open-native-async-local-pool.crust` is reverified and its refusal
current retention in `validation/async-collection-new-next-local-pool.log`.
The limit on general signatures and structural catches remains.
No new results found.ASan/TSan, second compiler C or formal proof.
The clean UBSan passages do not prove all the interleavings.

The five modified or added Python files pass syntax analysis.
The local links of the report were monitored.
[lowering diff]](../../validation/async-collection-new-implementation.patch)
Keeps comparison with the pre-batch snapshot.
