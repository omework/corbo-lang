[Français](ASYNC_HANDLE_VECTOR_BORROW_RETURNS_CYCLE-fr.md)

<a id="retours-async-demprunts-vers-les-éléments-de-vectoraint"></a>

# Async returns of borrowings to Vector elements<A<Int>>

<a id="règles-et-changements"></a>

## Rules and changes

Application of H2, VE1/VE4, B1–B5 and AS9–AS12. A shared or transferable loan
to the content of an allocation contained in a vector may exit from the
task if the external carrier remains valid. The result keeps its reservation
until last use, including through the expected relays. A vector
transferred to the task and then destroyed at its termination does not allow this return.
No rule of law has been amended.

The source calculation now recognizes the projections &*v[i] and
&mut *v[i] Vector parameters<A<Int>>. It keeps the carrier vector in
The result is represented as a synchronous caller side.*
borrowed with reservation of the holder; the descriptor is no longer confused with
the Cell of the vector. The relayed returns and the results used in a state
async uses existing life-span mechanisms.

The validation after join encountered a missing synchronous writing:
*values[i] = value. It is connected with check box, selection
the target before the HHR, shared reservation during this HHR, then control
mutable access before writing. Read vector in the HHR is allowed;
borrowing it mutably during this preparation is refused.

<a id="couverture-ciblée"></a>

## Targeted coverage

Six methods in tests/test_async_handle_vector_borrow_returns.py: seven
native (six normal, one controlled termination) and ten programs
disabled persons checked at both entries.

- Retour shared and then mutation of the vector after last reading: admitted.
  Drop, write or replace the holder before reading: refused.
- Return from a vector transferred to the task: refused, without promotion.
- Transferable return, write 11 via result, then 12 by the holder after
  last use; single destruction of 12 and re-use of pool with 8.
  Premature reading of the bearer and use of the loan after transfer refused.
- Shared and mutable async relays, yield in both statements: results 7/13,
  cleaning and re-use; premature drop of the vector refused in both cases.
- Await result kept in a state, yield, read and then mutation after
  last use; prolonging use beyond mutation is refused.
- RHS synchronizes reading the allowed vector; RHS asking &mut refused.
- Off synchronous terminals: diagnosis before the HHR marker 123.

<a id="exécutions-et-défauts-rencontrés"></a>

## Performance and defects encountered

Newspapers kept in validation/:

| Journal | Result |
| --- | --- |
| async-handle-vector-borrow-returns-first-o0.log | Synchronous Writing *v[i] still treated as reference table; connected |
| async-handle-vector-borrow-returns-second-o0.log | Drop Oracle of the pool refused earlier for prohibited transfer; replaced by a carrier replacement to test the conflict |
| async-handle-vector-borrow-returns-third-o0.log | Missing arrow in the new negative replacement; added. Reservation of HHR too strong, corrected to allow shared reading |
| async-handle-vector-borrow-returns-fourth-o0.log | Five methods, 2,860 s, code 0 |
| async-handle-vector-borrow-returns-final-o0.log | Six methods, 3,248 s, code 0 |
| async-handle-vector-borrow-returns-regression-o2.log | 49 methods, 41,046 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_borrow_returns -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_borrow_returns test_async_handle_vector_borrows test_async_handle_vector_access test_async_handle_vector_captures test_async_reference_returns test_async_vector_push_new test_recursive_borrow_results test_recursive_mutable_results -v
```

C11/pthread, error warning and fatal UBSan. Regression exerts the
returns of references to tables, scalar vectors and recursive fields.
Values, diagnostics, order of effects and destruction are explained
no new model or adversarial/mutation campaign;
models of existing suites are retained. No general proof of safety.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The source of the result reserves the entire vector, without precision by index.
This lot does not claim to check all the disjointed indices or all API of the
vectors. Insertion from async remains open:
validation/open-async-handle-vector-push.crust and .log reproduce the refusal
at both push(-> numbers.new(7)) inputs after yield, with injected pools.
The remaining transactions and public arbitrations scheduler/mutex remain open.

The open-async-handle-vector-borrow-return.crust fixture is now covered;
His refusal diary remains historic.
Snapshot : /tmp/crust-before-async-handle-vector-borrow-returns/.
Diffs : validation/async-handle-vector-borrow-returns-{crust.py,async_lowering.py}.patch.
