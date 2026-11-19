[Français](ASYNC_HANDLE_VECTOR_CAPTURES_CYCLE-fr.md)

<a id="captures-async-de-vecteurs-de-handles"></a>

# Async captures of handlivators

<a id="règles-et-implémentation"></a>

## Rules and implementation

Application of VE1–VE2, H1, B1–B5 and AS2/AS8–AS12, without change of standard.
Vector<A<Int>> contains owner handles; the task that receives the
transfer vector supports cleaning of elements.
shared or mutable keeps the ordinary reservations of the vector and its
pools until the established termination.

Lowering refused to do so in the catches, while the representation
Cell of the vector and its cleaning already existed. The type is now admitted
for the transition to the frame and classified as a collection. Both internal forms
read its length via vector_len. No new allocation runtime
No copy of the content was introduced.

<a id="cas-ciblés"></a>

## Targeted cases

Five methods in tests/test_async_handle_vector_captures.py: five executions
and six invalids at both compiler entries.

- Shared borrowing: length reading after yield; destruction of vector,
  destruction of the pool of elements and pre-join addition refused.
- Mutable borrowing: Async relay with expected child; concurrent reading
  the appellant refused.
- Transfer of vector: destruction of element once in termination
  normal, then re-use of the Int pool of capacity one.
- Same cleaning for an explicitly destroyed inactive task and for a
  EAGAIN injection failure. No body execution in these cases.
- A Vector signature<Int> does not receive Vector<A<Int> silently.

The fixture validation/open-async-owned-vector-capture.crust, refused in the
Associated historical journal, is now executed by the shared test.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| async-handle-vector-captures-first-o0.log | Three methods, 1.401 s, code 0 |
| async-handle-vector-captures-second-o0.log | Five methods, 1.787 s, code 0 |

Regression completed: 57 methods, 73.554 s, code 0, in
validation/async-handle-vector-captures-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_captures -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_captures test_async_vector_operations test_async_vector_remove test_async_vector_results test_async_collection_new -v
```

C11/pthread, error warning, fatal UBSan. Targeted oracles are for
the exits, the single destruction and the re-use of capacity one.
existing finished collections suites are reexecuted; no new
independent model or campaign of mutations.

## Limites

This batch connects the captures and length reading, not the entire API
Vector<A<Int>> in states. Access to elements, insertions/extractions,
the returns of these vectors and their local construction async remain at
The reference vectors and other types of elements are not included in the list of references.
The overall objective and public arbitrations remain
open; no general evidence of safety.

Snapshot : /tmp/crust-before-async-handle-vector-captures/.
Diff : validation/async-handle-vector-captures-async_lowering.py.patch.

Reading again refused both entries:
validation/open-async-owned-vector-read.crust and .log. This case is the next one
connection, not a normative restriction.
