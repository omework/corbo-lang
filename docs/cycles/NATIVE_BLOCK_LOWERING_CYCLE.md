[Français](NATIVE_BLOCK_LOWERING_CYCLE-fr.md)

<a id="cycle--compilation-des-premiers-blocs-natifs"></a>

# Cycle — compilation of the first native blocks

Continue: [synchronous calls from states](NATIVE_SYNC_CALLS_CYCLE.md).
The refusal of the add auxiliary described below is historic; its signature
scalar is now connected. Calls for general signatures remain open.

<a id="règles-et-périmètre"></a>

## Rules and scope

Application of RT8, RT4–RT7, AS7/AS10/AS11 and existing rules of
transfer, mutability, life and provenance. No decision
The previous cycle was a progress achieved:
This cycle connects these elements to the compiler.
AGENTS.md, guidelines, draft index and relevant rules
were consulted; readings of LANGUAGE_RULES.md and extension async
the previous cycle shall remain applicable.

The minimum programme `validation/open-native-thread-basic.crust` compiles and
now runs with output `7`The old refusal logs are
preserved as historical, not as current status. RT8 remains partial:
synchronous auxiliary called from the block, pool creations
in bodies using this backend, handholds and types
not all are connected.

<a id="traduction-et-contrôles"></a>

## Translation and controls

`native_threads.py` isolating each block in an internal definition whose
type of result is inferred from returns and final value.
types of catches come from the lexical environment. The body does not receive
the links explicitly listed. Internal names contain a
not accepted in source identifiers; the program cannot
not artificially call these definitions as async functions.

The definition reuses the ABI states and its typed pool, with the marking
interne `native_block`. This marking does not change the block to function
suspensionable: the parser always refuses yield and is in his body and
The launch calls the native primitive independent of the scheduler.
transitional control which refused all blocks was replaced by this passage.

The existing auditors then monitor the types and effects of the
The new passage does not constitute proof of borrowing.
The allocation of catches is made through existing transfers; links
scalar and borrowed are also invalidated after capture.
The following are the main factors which are followed by the dependences of the state and the result.
The branches of the result retain the union of possible provenances.

A wait join in the block uses results and results checks
common sources, but wait by a polling blocking loop with
sched_yield, without producing TASK_STEP_YIELD. This first implementation
is not an optimized OS expectation. An async caller is waiting for the handle with
Await. The launch failure retains the LaunchFailed treatment and the
clean up catches; the handle remains to be explicitly expected.

The terminal returns which the operand already leaves all the paths do not create
No additional fictitious result. This point was necessary for a
terminal match with return in each arm. The pictures captured by value
use the internal table shift operation; allowances
use their pointer transfer.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

`tests/test_native_blocks.py` comporte treize méthodes, 29 exécutions de
Crust programs compiled in C and 40 refusals expected in full passage.
The parsing module retains seven methods; its four transitional refusals
were replaced by verifications of the waiting obligation on the
the same programs that give up their handle.

Cases executed include:

- Returns Int, Bool, u8 and Void; final value, anticipated return and result
  The Bool/u8 values are observed by connection/conversion
  explicit to Int, depending on the display operations available.
- Scalar capture in a sync or async caller, old unusable link
  before and after waiting; transfer of the complete table with storage
  the observed content and invalidation of its former access.
- Reference to a table box, transfer allowed after waiting;
  mutable reference returned, read/mutation/drop of the rejected target
  during execution and as long as the borrowed result is to be used.
- Two possible sources of a mutable result: the two branches are:
  and each of the two premature mutations is refused.
- Int allocation received by a native block from hand or a parent task,
  cleaning on exit or failure, then re-use of a pool capacity one.
- Returned allocation: address stored between capture and receipt,
  then even slot reused after drop; failed, re-use after cleaning.
  The traces of destroyers require exactly 7 then 9, without duplicate.
- Native block that creates a native child and calls join, successfully, failure of the
  The child is not allowed to leave the child.
- Calling synchronous function that captures its borrowed parameter in a
  native and treatative bloc; independence of native launch from a native
  Scheduler who refuses additional launches.

The refusals also cover returns of incompatible types, the absence of
explicit capture, insufficient mutability, transfer of the pool itself,
the escape of a local loan and exits where a target or pool does not survive
Not in the handle. Life-span cases now end with a treated join,
so that a voluntary hand-absorbing does not mask the error.

Expectations are explicit values, traces, identities and decisions
The two selection flags, the two categories
d-appellants and the failures injected constitute a finite exploration; none
The models are not claimed.
The regression is part of the existing manual and scheduler systems.

<a id="résultats-exécutés"></a>

## Implemented

| Journal in validation/ | Result |
| --- | --- |
| native-block-initial.log | Programme minimal : sortie 7 |
| native-block-captures-initial.log | Quatre premiers programmes : 8, 7, 7, 8 |
| native-block-joins-initial.log | Return mutable and calling async pass; terminal match still refused before correction |
| native-block-nested-join.log | Corrected terminal match: output 8 |
| native-blocks-initial-o0.log | Initial failures retained: local async pools not supported, unsuitable displays and separate waiting diagnoses |
| native-blocks-o0.log | 16 methods, 9,374 s, OK, before the three interactions added |
| native-blocks-interactions-initial.log | Two methods pass; table displacement refused before correction of its internal operation |
| native-blocks-o0-final.log | 19 methods, 11,019 s, OK, before adding the dispatch probe |
| native-blocks-dispatch-o0.log | Added probe: 1 method, 1,532 s, OK |
| native-blocks-regression-o2.log | 81 methods, 92,846 s, OK, no jump |
| native-blocks-identity-o0.log / identity-o2.log | Regression of identity: 1 method, 1,197 / 1,554 s, respectively, OK |
| native-blocks-cleanup-o0.log / cleanup-o2.log | Final strength of identities and traces: 2 methods, respectively 2,885 / 3,086 s, OK |

Regression loads native_blocks, native_thread_parser,
native_thread_runtime, spamn_blocking, handle_obligations and
async_typed_divergence, then runtime methods selected by
threads/scheduler/workers/spawn/cleaning/re-use. Reproducible script
is `tests/run_native_thread_regression.py` ; the exact names are in the newspaper.
Clang C11, pthread, strict warnings and fatal UBSan are used.

```sh
PYTHONPATH=tests CRUST_TEST_OPT=-O0 python3 -m unittest -v test_native_blocks test_native_thread_parser
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_block_mutations.py
```

Modified modules pass py_compile and local document links
modified are verified (`validation/native-blocks-artifacts.log`) The artifacts
`validation/native-block-basic.c` and `validation/native-block-ownership.c`
this time C generated from the corresponding Crust programs.
The inspection of the second shows the pointer given to the result, the capture set
at NULL, the cleaning path that does not destroy the returned result,
task_native_start and task_join_allocation. The diff of implementation is
retained in `validation/native-block-lowering.patch`.

## Mutations

The mutations live only in temporary copies.
first passage are detected: unconsumed sync capture, async capture
Unconsumed and native launch sent to the scheduler. Clear all
sources triggers the variable "borrowing returned without target": this result
is retained as inconclusive in the protocol targeting undue admission.

The refined mutation only retains one of the two origins. The test then detects
The two flags were given undue acceptance of the b mutation.
The target test is therefore detected; the initial inconclusive test is not
Cleared. `native-blocks-mutations.log` and `native-blocks-origin-mutation.log`.

## Obligations encore ouvertes

Two valid rejected programs are retained with their diagnoses in
`validation/native-blocks-open-cases.log` :

- `open-native-sync-helper.crust` : call for a synchronous function add since
  The native block, refused by the body backend.
- `open-native-async-local-pool.crust` : creation of a pool in the appellant
  Async, refused by the same backend.
  use an allowance received from hand; they do not validate this local case.

The catches of pools and handles, other aggregates and composite references,
l-inference of all expressions, the bodies diverge without result
Deductible, generic interactions with features and annotations
public running::Handle<T> still to be completed.
cycle concern A<Int>, not the universal stability of the displaced tables.
The capabilities of anonymous states are handled by existing terminals;
general and recursive configurations remain to be tested.

The cycle is not ASan/TSan proof, multi-compiler or formal.
has not been restarted after previously documented blockages.
The seven drafts remain open obligations for active purpose.
