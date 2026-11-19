[Français](NATIVE_THREAD_BOUNDARY_CYCLE-fr.md)

<a id="cycle--frontière-des-blocs-de-thread-natif"></a>

# Cycle — native thread block boundary

Follow-up: This report describes the step before connection.
[cycle suivant](NATIVE_BLOCK_LOWERING_CYCLE.md) replace transitional refusal
by compiling the first blocks, and running the minimum program.
The limitations and figures below are those of this historical cycle.

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Partial application of RT8, RT4–RT6 and AS10, without change of regulations.
AGENTS.md, VALIDATION_GUIDELINES.md, LANGUAGE_RULES.md, index of seven
The first is the async/multithread passages.
exchange on model setting had not advanced implementation.
This cycle adds syntax and native-launching internal primitives.

**The primitive Crust complete is not yet implemented.** The inference of
and results, contracts, pools of states of these blocks and their
translation remain to be connected. The valid program kept in
`validation/open-native-thread-basic.crust` his current diagnosis,
retained in `validation/open-native-thread-basic-current.log`indicates the
lack of contracts, instead of the old parsing error. L
This refusal is not a language decision.

<a id="implémentation"></a>

## Implementation

The parser produces an expression `native_thread` with the ordered list of
captures, body and source line. L-header `-> (a, b);` appartient
only at the entrance of this block. Returns and final value remain in
this body, without being transformed into returns of the calling function.
The parsing context is synchronous in the block, even in an async caller,
Then restored after it. A wait applied to the handle after the block remains
syntaxiquement possible chez l’appelant async.

A transitional control at the beginning of the verification explicitly refuses to grant such
expressions before generic analyses. They cannot be ignored
or let their nested returns contaminate the calling contract.
must be replaced by analysis of block contracts, not simply removed.

Runtime provides `task_native_start` for a handle expected by join and
`task_native_async_start` for a polluted wait. These functions call
directly the primitive pthread, without consulting the callbacks of the scheduler.
They share with spawn the mechanisms of preparation and cleaning to
Failure, but choose a dedicated synchronous executor. It calls the body a
only once; a suspended return constitutes an internal violation and causes
This guard does not replace the static refusal of yield/await.

The thread publishes its end after the last use of its state.
is extracted before re-establishing the slot. The launch failure destroys the state and
The system code remains in the handle.
A block can block on the join of another native thread. No implicit join,
hand-absorbing or cancellation is added.

<a id="vérifications-distinctes"></a>

## Separate verifications

`tests/test_native_thread_runtime.py` includes five methods and ten executions
C by passage: nine normal terminations and one SIGABRT stop expected for
an impossible suspension at the level of the ABI. They cover:

- Join and wait polluted, each successfully and refusing EAGAIN creation.
- Performance on a separate thread, independence from a scheduler, of which
  both launch callbacks refuse, and result composed with loan.
- Lack of result and release while the body remains blocked;
  result visible after waiting; single cleaning; reusable slot and
  old invalidated generation ticket.
- Failed to prepare attributes of a detached thread, before pthread_create,
  with destruction of captured and initialized attributes exactly once.
- Blocking join made by a native block on another native thread, then
  clean up both states before the return of the outside wait.

L-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O------------------------------------------------------------------------------------------------- `rtdw` (corps,
extraction, destruction, return of waiting), failure `dw`. It also verifies
results 42/20 or 0/10, cleaning and system creation accounts.
It is not a general pattern of scheduling or proof of safety of the
The targets borrowed from the C probes are set to the level of the language.
explicitly in place and live long enough by construction.

`tests/test_native_thread_parser.py` has seven methods: ten programmes
syntaxiquement admis, quinze refus syntaxiques et quatre vérifications du
The first is the temporary refusal before the effects are analysed.
owners, the join, the nested native blocks, the ordered catches,
poorly formed headers and restoration of the async context are examined.
A parsing success is not counted as a compiled Crust program.

The first passage of the parser revealed an erroneous expectation in the test:
The operator is represented by `arithmetic`, non `add`. The assertion has been corrected
on the exact AST form; no language rule changed. The original log
is kept in `validation/native-thread-parser-initial.log`.

<a id="exécutions-et-artefacts"></a>

## Executions and artifacts

| Journal in validation/ | Result |
| --- | --- |
| native-thread-runtime-o0.log | 5 methods, 3,411 s, OK; 10 C executions |
| native-thread-parser.log | 7 methods, 0.002 seconds, OK |
| native-thread-runtime-mutations.log | Five runtime errors detected |
| native-thread-parser-mutations.log | Incorrect inheritance of the async context detected |
| native-thread-regression-o2.log | 68 methods, 65,491 s, OK, no jump; includes the 10 C executions of the new module |

The C probes use Clang C11, pthread, `-Wall -Wextra -Werror`, UBSan fatal,
and `-O0` ou `-O2`. The regression runs the two new modules,
spawn_blocking, handle bonds, async-typed initializations,
then runtime methods related to threads, scheduler, workers, spawn,
Cleaning and re-use of pool. The exact names are kept in the log.

```sh
PYTHONPATH=tests CRUST_TEST_OPT=-O0 python3 -m unittest -v test_native_thread_runtime
PYTHONPATH=tests python3 -m unittest -v test_native_thread_parser
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_runtime_mutations.py
```

`validation/native-thread-abi.c` is a C probe of the ABI, **not C generated
from a Crust block**. The diff of compiler and runtime files is
retained in `validation/native-thread-runtime.patch`. Python modules
modified and added pass py_compile. Local links of the four documents
The process of this cycle has been completed.

<a id="mutations-et-limites"></a>

## Changes and limits

Six targeted errors, only in temporary copies, were detected:
passage of native launch through the scheduler; acceptance of a suspension;
omission of cleaning to failure; publication of end before body; release
before extraction; legacy of the async context in the synchronous block.
Runtime errors fail on the expected native claims or traces; the
last wrongly makes the suspensions accept the parser. No overall rate
The sample shall be taken from the sample.

Static catch checks, their effective transfer, provenances
of the result and the obligation to wait for the new primitive remain not
The existing obligations of spawn are replayed without being presented
as proof of runtime::thread. The next step is representation
blocks with types and contracts, then the generation of their states and calls
native primitives established here.

ASan was not restarted after the documented blockages of previous cycles.
No TSan execution, no second compiler or formal evidence is
claimed. The public installation of the scheduler, wake-ups and fairness,
Select, mutex guards and other open lines of the matrix remain
This cycle does not end RT8 or the seven drafts.
