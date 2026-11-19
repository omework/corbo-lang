[Français](ASYNC_VECTOR_PUSH_NEW_CYCLE-fr.md)

<a id="cycle--push_new-et-emprunts-de-cases-dans-les-tâches"></a>

# Cycle — push_new and task box borrowing

<a id="règles-et-modification"></a>

## Rules and amendments

No change in the rules. AGENTS.md, VALIDATION_GUIDELINES.md, index
the seven drafts and relevant clauses of LANGUAGE_RULES.md,
FOUNDATIONS_AND_VECTORS.md and ASYNC_MULTITHREAD_RULES.md have been re-read.
VE6 requires default initialization before the loan is published;
B1/B2/B4a, F4, AS2/AS9/AS15 impose sustainable origin, exclusivity,
the last use and conservation of catches during suspension.
VE1/GR1/GR2 is about identity and both growth directions.
The async normative extension prevails over the historical synchronous perimeter
The introduction of guidelines.

The Counter-Example `validation/open-async-vector-push-new.crust` is now
executed and produced 0, 23, 1, 23. His previous log of refusal remains historical.
Lowering accepts a direct connection or return of `push_new()` on
Vector<Int/u8>. The existing runtime initializes the box before rendering its
address. The frame keeps an exact pointer and the verifier
reserves the source until the last use, including continuations,
the capture and return of child tasks.
vector received by transfer cannot escape from its frame.

Translation of the `&mut u8` is now distinct from that of `&mut Int`
in the catches, states, expectations, arms and results of join. A field
`uint8_t *` dedicated avoids writing a d-byte pointer into a type C object
`int *`. Synchronous contracts shall retain the type and origin of the
box returned by join, then relayed to their caller. The shared reborrowing
`&*cell` keeps the loan mutable ancestor: the parent remains reserved until
last use of the view or task that captures it.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

`tests/test_async_vector_push_new.py` includes 15 methods:
24 normal native executions, two controlled stops for capacity and
31 static refusals expected by complete passage.

- Int/u8 on both fronts, with actual management verification
  chosen in the C; the surrounding cells remain intact after writing.
- Observable zero before writing, maintaining value after yield,
  then growth after the last use of the loan.
- Booking vector against reading, new insertion, remove and
  second push_new as long as the initial loan is still in use.
- Reborrowable, child suspended, two relays back, join in
  a synchronous caller and waiting for a handle in an async parent.
- Synchronous contract that returns the join box, with separate return
  in each arm; premature destruction of its refused source.
- Shared borrowing d   , inactive capture and return of shared view,
  mutations of the parent or vector refused before the last use.
- Branches, loop, continuous, break, writing `*cell = valeur` and `.set()`.
- Two independent models in the form of Python lists, seeds 817 and
  810: 16 inserts by type, length and each content compared.
- Real region limit 1 Mio, two element sizes: front stop
  Next printing push_new, without UBSan diagnosis.
- Source possessed by the task, read before drop, then re-use the same
  slot after join; drop before last reading and reuse after drop refused.
- Bad types, annotation, inarity, mutability, overflow of literal u8
  and escape from a reference to a refused capture.

Expected outputs and lists are not calculated since the
internal structures of the compiler. Steering control in the C
check a test precondition, not the expected value. Reuse at
identical address does not constitute a general proof of single destruction.

<a id="défauts-et-ajustements-découverts"></a>

## Deficiencies and adjustments discovered

The first batch exhibited a link from await whose mutable marker
was not registered; this metadata is now preserved.
a region originally used by value and
The second front was therefore not exercised: the annotation was withdrawn from this only
scenario, keeping the assertion on the direction actually achieved.

The return contract of a box after join initially retained a
raw parameter instead of the source of storage of the vector. It is
The relay is executed. An old restriction test refused any
signature async `&mut u8` This expectation has been withdrawn, as this refusal is not
The new tests perform the scripts and
require refusal of invalid types and lifespans.
The original logs are kept.

<a id="preuves-exécutées"></a>

## Evidence

Configuration native : Clang Homebrew 20.1.3, arm64 macOS, C11, pthread,
`-Wall -Wextra -Werror -Wno-unused-function`, UBSan with
`-fno-sanitize-recover=all`. The new helpers follow CRUST_TEST_OPT;
old tests keep their own parameters.

| Implementation | Result | Trace |
| --- | --- | --- |
| Lot complet O0 | 15 methods, 20.917 s, successful | validation/async-vector-push-new-O0-complete.log |
| O2 with operations, removal and vector results | 53 methods, 70,537 s, passed | validation/async-vector-push-new-O2-final.log |
| Borrowings, contracts, tables, UTF-8 and synchronous neighbours | 44 methods, 64,683 s, passed | validation/async-vector-push-new-neighbors-final.log |
| ABI, typed results, states and pools | 15 methods, 29,586 s, passed | validation/async-vector-push-new-abi.log |
| Mutations | Four detected | validation/async-vector-push-new-mutations.log |

The follow-up is overlapping; these numbers are not a total of separate cases.
The Python compilation of the modified modules and the three test files and
validation succeeded. The first passage of the neighbors included waiting
&mut u8; its record remains in
`validation/async-vector-push-new-borrow-regression.log`.

The four mutations controlled in temporary copies are detected
by semantic assertions: non-zero default, reservation of receiver
deleted, address of the first box returned in place of the new,
and the result is erased.
`validation/async-vector-push-new-mutations.log`No overall rate
extrapolated from this sample.

The ASan+UBSan trial was interrupted after several delays; it was interrupted by a number of delays.
is not a successful validation. An independent executable does not contain
que `int main(void){return 0;}` compiles with ASan+UBSan, but also exceeds
10 seconds at launch without exit:
`validation/async-vector-push-new-ASan-smoke.log`. The mechanism of the time limit
is not identified. Partial trace remains in
`validation/async-vector-push-new-ASan.log`. No results ASan, TSan,
second compiler or formal evidence is claimed.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Another valid program remains denied:
`validation/open-join-element-match-expression.crust`. The relay can be
return from each arm, but shape `return match ...` which produces
The loan is refused by the analysis of conditional expressions.
expected is 255; the duplicate diagnosis is kept in the file `.log`.
This refusal remains a misapplication, not a language decision.

This lot does not extend the async vectors to owners and other types
d) General terms of borrowing and other
N/P lines of the matrix still to be completed. Reset public remains removed;
the obligations relating to public contracts,
scheduler, threads, Select, mutex and implicit data stack remain open.
The success of the scenarios carried out does not prove the general safety or
completion of the seven drafts.


Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_vector_push_new -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_vector_push_new test_async_vector_remove test_async_vector_operations test_async_vector_results -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_push_new_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
python3 tests/run_async_vector_push_new_mutations.py
```


Update: the program `open-join-element-match-expression.crust` is
corrected in [REFERENCE_EXPRESSIONS_CYCLE.md](REFERENCE_EXPRESSIONS_CYCLE.md).
The conditional form in an async body remains distinct and open.
