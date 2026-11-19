[Français](ASYNC_FIELD_LOOPS_CYCLE-fr.md)

<a id="provenances-de-champs-aux-reprises-de-boucles-async"></a>

# Field sources for async loops

<a id="implémentation"></a>

## Implementation

This batch connects ST10/ST11, B1/B2/B5, AS9/AS12/AS16 and the rules of
loop/while/break/continue without changing normative semantics.
Targets of fields stored in states can now vary
The comparison of the obligations to the recoveries distinguishes between two iterations.
These targets of other cleaning obligations, which remain strictly compared.

The backend reuses its UTF-8 view reanalysis engine.
adds new targets to the abstract loop entry.
start again with a new state, then the body is reverified with the whole
Expanded. Field keys are distinct from view names; each loop
The initial storage remains an alternative, and the
when the test is not performed.

The data stored between tests are symbolic target sets,
not the C code, frames or task obligations of a previous trial.
Targets that are no longer sustainable at the entrance are refused.
cleaning, waiting obligations and other borrowings are not deleted
to make compatible two times.

<a id="scénarios-et-contre-exemples"></a>

## Scenarios and counter-examples

Eight methods of `tests/test_async_field_loops.py` couvrent :

- while zero, one or three iterations, read before replacement and yield;
- loop with explicit continuous, direct store, helper and child expected;
- access to the mutable parameter before the blind: allowed for the first passage
  only but incompatible with the repeats, therefore programme refused;
- interlocking loops, two new targets and early return;
- Repeated rotation of two fields, with preservation of their cells
  origin despite successive changes;
- reference saved before a store and then passed to a helper that
  stores in a new object: the old cell of the first passage and the
  new of the following are correctly selected;
- historical reset refused as long as the external carrier holds the target,
  re-use after the bearer has been destroyed;
- 12 trace independent model: zero/one/three iterations and two
  value choice for each target. The oracle performs a field transition
  The compilation of the results of the work is not available in the abstracts.

The negative recovery program is checked at both entries, without running it.
Valid variants with shared input perform the same sequence of
readings. Trace models do not prove an arbitrary number of iterations.

<a id="preuves-exécutées"></a>

## Evidence

Journaux `validation/async-field-loops-*.log`.
The initial selection of seven methods is 10,309 s (`-initial`).
The final selection of eight methods is increased to O0 in 10.737 seconds (`-final-o0`).
The following selection O2 passes 40 methods in 42,611 seconds (`-final-o2`) :

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_field_loops test_mutable_field_completion test_borrowed_field_completion test_async_child_field_effects -v
```

The regression selection of the views and loop results passes 20 methods
at O2 in 16,589 s (`-view-regression`) It brings together the module
`test_async_loop_references` and methods of `AsyncRuntimeTests` contenant
`loop_carried`, plus the following five methods:

- `test_async_while_carried_utf8_view_preserves_zero_iteration_source` ;
- `test_async_loop_resumes_and_cleans_each_iteration` ;
- `test_async_loop_exit_can_finish_a_worker_from_the_enclosing_scope` ;
- `test_async_mutable_utf8_view_replaced_before_continue` ;
- `test_async_shared_vector_slice_reassignment_and_loop_sources`.

These accounts are methods, sometimes composed of several programmes;
The selections are overlapping. No changes in the compiler between these passes.

Four mutations are detected (`-mutations`) : forgotten the targets of recovery,
non-installation of expanded sets, forget about the initial target and corruption
The third key is detected by the
value read in the helper after saving the old field; mutations
which prevent convergence are detected by the undue refusal of neighbours
This is not an overall defect detection rate.

Native programs are compiled in C11/pthreads with warnings
Blockers and fatal UBSan. Python compilation of modified modules/tests
succeeds. The compiler patch is kept in
`validation/async-field-loops-async_lowering.py.patch`.

## Limites

This batch covers the targets already represented of the injected carriers.
is conservative: a reallocation requires a precise correlation
between meter, current target and exclusive availability of a parameter can
The new executions are mainly in the fields of
shared; mutable fields retain exclusive controls and do not
are not considered as generally resolved by this extension.

Incompatible cleaning states, general inline targets
The tests do not establish the
Security of any program or any scheduling. No new evidence
ASan/TSan, for comparison between independent C compilers or for formal evidence.
The overall objective remains open.
