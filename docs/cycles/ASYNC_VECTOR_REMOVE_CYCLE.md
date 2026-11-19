[Français](ASYNC_VECTOR_REMOVE_CYCLE-fr.md)

<a id="cycle--remove-dans-les-corps-async"></a>

# Cycle — removes in async bodies

<a id="modification-et-invariants"></a>

## Amendment and invariants

VE3 requires extraction which keeps the order of the remaining cells.
contre-exemple `validation/open-async-vector-remove.crust` was refused in
The body is suspended. It now produces 17, 1, 29. The previous log
no change in the rules: AGENTS.md,
VALIDATION_GUIDELINES.md, the index of drafts and VE1–VE6 were read.
The life and suspension references remain LANGUAGE_RULES.md
and ASYNC_MULTITHREAD_RULES.md.

Lowering recognizes the removal on Vector<Int/u8>, in expression, back,
The transferable receiver is
The number of persons in the index is calculated by the number of persons in the index.
index after its possible suspensions; another receives the extracted element.
The type remains Int or u8, without implicit conversion. The existing runtime
checks the index, copies the value, shifts the logical boxes and then reduces the
length and recovers storage. It has not been modified in this cycle.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

The module `tests/test_async_vector_remove.py` has twelve methods,
15 native executions that normally end, six that must stop
with the terminal diagnosis, and 15 programs rejected statically.

Both types are tested on both storage fronts.
C checks the direction actually chosen, rather than assuming it from
of the order of the declarations. Extracts at the beginning, middle and end
check each remaining contents and length, up to the empty vector.
Two Python lists (seeds 81/183, 32 operations each) calculate the
effects independently of compiler and runtime. Comparison observed
the result, length and all remaining boxes after each step.

The suspended clues have an observable effect executed once.
In addition, the index is sequential.
already reserved receiver is refused; a disjointed vector is allowed.
reading of a slice may precede removal; its subsequent uses, even
after yield or in a branch, are refused. A loop combines local view,
extraction, suspension, continuous and break without holding an expired loan.

A result u8=255 passes through a child, a parent, and then a join after drop
The vector and the pool re-use. A captured catch retains its obligation
cleaning. An independent meter of slot lists finds two
destruction for both scenario allocations; same slot is reused,
successful and on EAGAIN injected at launch.

The -1, length and INT_MAX indices are provided via a suspension task
for Int/u8. The six programs must stop with the Vector diagnosis,
before printing after operation and without diagnosis UBSan. L-stop
The safety of all index calculations is not proven by the controlled method.

<a id="preuves-exécutées"></a>

## Evidence

Clang Homebrew 20.1.3, arm64 macOS, C11, pthread, avertissements stricts,
UBSan fatal. New helpers follow CRUST_TEST_OPT. Old ones
regression helpers retain their own options.

| Implementation | Result | Trace |
| --- | --- | --- |
| Lot O0 | 12 methods, 10.814 s, passed | validation/async-vector-remove-O0.log |
| Batch O2 and regressions of operations/results/errors | 52 methods, 100.106 s, passed | validation/async-vector-remove-O2-regression.log |
| Union/async neighbours, slices, handles and re-use | 20 methods, 39,662 s, passed | validation/async-vector-remove-neighbors.log |
| ABI, expectations, tables and pools | 15 methods, 35,254 s, passed | validation/async-vector-remove-abi.log |
| Mutations | Four detected | validation/async-vector-remove-mutations.log |

The transfers target the reservation of the receiver, the choice of index,
copying the following boxes and reducing length. The last two
modify the runtime C in a temporary copy. All are detected by
semantic assertions; no overall rate is deducted from this sample.
The Python compilation of the modified files was successful. The first batch of ten
methods also succeeded; its initial log is retained.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The result of removing is a Copy value in this lot.
borrowings and other types of elements in async vectors remain to be completed.
The following defect is reproduced in `validation/open-async-vector-push-new.crust`
and its log: push_new should initialize a zero box and allow for a
This box can be borrowed through yield, but the lowering refuses.
The valid program should display 0, 23, 1, 23.

No change in reset, placement or destruction policy.
Public handle, scheduler, threads, Select, mutex and other N/P lines
None of the ASan/TSan, second compiler C, test
comprehensive or formal evidence in this cycle.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_vector_remove -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_vector_remove test_async_vector_operations.AsyncVectorOperationTests test_async_vector_results test_builtin_error_values -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 tests/run_plain_join_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_remove_mutations.py
```


Update to the next cycle: the push_new counter example described above
is corrected for Int/u8. See [ASYNC_VECTOR_PUSH_NEW_CYCLE.md](ASYNC_VECTOR_PUSH_NEW_CYCLE.md)
for evidence, relays and limits that remain open.
