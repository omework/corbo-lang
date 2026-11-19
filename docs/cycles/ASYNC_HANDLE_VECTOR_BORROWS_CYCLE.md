[Français](ASYNC_HANDLE_VECTOR_BORROWS_CYCLE-fr.md)

<a id="emprunts-nommés-des-cibles-de-vectoraint-dans-async"></a>

# Named Borrowers of Vector's Targets<A<Int>> in async

<a id="règles-et-implémentation"></a>

## Rules and implementation

Application of H1–H2, VE1/VE4, B1–B5 and AS9: &*values[i] emprunte
the Int content of the allocation designated by the box. &mut *values[i] exige
A suspension does not release the reservation; this one is not a guarantee.
stop at last use, taking into account the re-borrowings passed on to children.
No rule of law has been amended.

Lowering recognizes these expressions as Int references and produces a
pointer to Cell.value after index control. It uses tracking
the existence of vector loans, their last use and descendants.
The pointer refers to the content allocated, not the box containing its handle.
The vector remains reserved to keep the target alive.

<a id="cas-et-exécutions"></a>

## Cases and executions

Five methods in tests/test_async_handle_vector_borrows.py: six executions
natives including controlled termination out of bounds; seven invalid programs
verified by verify_program and compile_source.

- Historical fixture: shared reference retained during yield, result 7,
  destruction of vector and reuse of capacity pool one with 8.
- Transfer via shared reference and Int annotation on a loan refused.
- Mutilable reference, yield, write 9, then write directly 10 after last
  Use: result 10/8 and single destruction of content 10. Direct access
  during the borrowing, subsequent use of the reference and non-mutable capture refused.
- Re-borrowing to a child expected and then taking over the reference: 10/8.
  Use the parent while the child is not on reserve.
- Transfer to task: drop after last read allowed, drop before
  read-out refused; result copied 7 and then re-use 8.
- Index provided by a suspended child: correct reading or controlled stop
  out of bounds before reading the target.

Journals in validation/:

| Journal | Result |
| --- | --- |
| async-handle-vector-borrows-first-o0.log | Five methods, 2,971 s; the annotation oracle used an unpaved &mut Int syntax in this position. Replaced by the Int annotation, which must be refused by type control. No runtime defects observed. |
| async-handle-vector-borrows-second-o0.log | Five methods, 2.726 s, code 0 |
| async-handle-vector-borrows-regression-o2.log | 41 methods, 35,948 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_borrows -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_borrows test_async_handle_vector_access test_async_handle_vector_captures test_async_vector_push_new test_async_local_references -v
```

C11/pthread, error warning, fatal UBSan. Oracles are about the
values, diagnostics, destruction and reuse; models already present in
The regression results remain unchanged.
These executions do not prove general safety.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The local loan uses the existing reservation of the entire vector.
Not all combinations of disjointed or unknown clues are proven.
The returns of loans from these vectors still have to be connected: reproduction
validation/open-async-handle-vector-borrow-return.crust and .log, refusal to both
The introductions/extractions, the
local constructions and returns owners also remain to be completed.
The public arbitrations which have already been opened are not closed.

Snapshot : /tmp/crust-before-async-handle-vector-borrows/.
Diff : validation/async-handle-vector-borrows-async_lowering.py.patch.
The open-async-owned-vector-borrow.crust fixture is now executed; its
The old refusal log remains historical evidence.
