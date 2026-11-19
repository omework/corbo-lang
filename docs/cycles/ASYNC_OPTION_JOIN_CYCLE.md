[Français](ASYNC_OPTION_JOIN_CYCLE-fr.md)

<a id="option-propriétaire-dans-lenveloppe-dun-handle"></a>

# Owner option in the envelope of a handle

<a id="règles-et-périmètre"></a>

## Rules and scope

Application of H1–H2, VE3, U1, B1–B5, AS2–AS5, AS8–AS15, RT6 and SL1–SL2,
The launch of a task returning Option<A<Int>>
produit un handle dont l'attente restitue Result<Option<A<Int>>,runtime::Error>.
Ok(Some(...)), Ok(None) and Err(...) remain distinct. The result keeps the
pool of the possible allocation, not the life of the vector that contained it.
Explicit transfers and uses remain required.

<a id="implémentation"></a>

## Implementation

CrustOptionJoinResult contains an external status and a VectorHandleResult.
Its definition is issued with the compiler's type values; the runtime
generic remains independent of this envelope.
Cleaning is conditioned by external success and internal presence.
Transfer transitions empty the source pointer; the receiver assumes
The result is connected to signatures, contracts and contracts for the
from and constraints, to matches, blocks and returns.

Synchronous join and async waiting use existing primitives of
return in a typed storage. runtime::Handle<Option<A<Int>>>> conserves
an opaque group for the source of its result in public contracts.
The catch and relay of the envelope shall use the same follow-up as the other
results owners. The arguments prepared before a suspension are
recorded for cleaning if the call is not finally executed.

An optional result with an empty resolved set of sources does not have
its envelope retains its type of pool storage,
This distinction corrects both of the two
defects encountered on None during the batch.

<a id="cas-ciblés-et-défauts-rencontrés"></a>

## Targeted cases and defects encountered

Seven methods in tests/test_async_option_join.py: 19 native executions,
five invalid programs with both verify_program and compile_source entries.

- Some/None success and failed launch injected; exits and single destruction.
- Async of the handle and return of the envelope by a task expected directly.
- Waiting helper with public handle, then synchronous relays, with Some and None.
- Named and direct drop; capture in an inactive task and then destruction.
- Pool surviving to the allowed vector, local pool too short refused.
- Argument owner prepared before a wait; cleaning in a loser of Select.
- Transfers per block, if and break, with explicit injection of the handle into the child block.
- Reason ignoring content, result without use, no arrow and reuse
  After transfer refused.

The first passage detected the wrong invariant "living allowance without
The internal failure test also injected into the
wrong launch path: it now targets the first async submission,
The third was the synchronous submission that launched the appellant.
passage detected loss of type of storage of None in the helper.
test programs also omitted the downward transfer of the handle: their
snippets were corrected, without relaxing the join litter rule.

The regression of the runtime alone then revealed that the definition of the envelope
had been placed in its generic module while depending on a type
It was moved next to VectorHandleResult.
The async_runtime.py module is finally identical to the previous snapshot.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| async-option-join-first-o0.log | Five methods, 4.288 s; two failures described above |
| async-option-join-second-o0.log | Five methods, 5.885 s, code 0 |
| async-option-join-third-o0.log | Seven methods, 6.589 s; None/helper defect and three snippets without descending transfer |
| async-option-join-fourth-o0.log | Seven methods, 8.415 s, code 0 |
| async-option-join-regression-o2.log | 83 methods, 152,442 s, code 0, before moving definition C |
| async-option-join-runtime-before.log | Four failed compilation methods C: VectorHandleResult absent from the standalone runtime |
| async-option-join-final-o2.log | Seven targeted methods and four runtime: eleven methods, 11.856 s, code 0 after correction |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_option_join -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_option_join test_async_handle_option_results test_async_handle_option_calls test_async_awaited_owned_results test_public_handle_contracts test_public_handle_types test_recursive_join_helpers test_select_source -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_option_join test_task_wakes -v
```

C11/pthread, error warnings and fatal UBSan. Oracles check for
The existing model of the
Select pollution/cleaning is included in regression. No new model
indépendant ni campagne de mutations ; l'audit approfondi reste différé. Ces
The results are not a general proof of safety.
n
The four of the runtime were replayed after this correction.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The type tested is Option<A<Int>>. Adding an additional envelope around
Result<Option<A<Int>>,runtime::Error> remains unconnected: such a task
It can be expected directly, but its launch by spamn is still refused.
Other generic types are not covered by this lot.

The following case is kept in validation/open-async-handle-vector-replace.crust
and his diary: replacing a vector handle in an async state is
refused both entries, with "expression array_handle_exchange not supported".
try_push, constructions and other vector returns, as well as
interface arbitrations already opened, are not closed here.

Snapshot : /tmp/crust-before-async-option-join/.
Diffs : validation/async-option-join-*.py.patch (eight compiler files).
