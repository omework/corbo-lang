[Français](SAFETY-fr.md)

<a id="périmètre-et-vérification-mémoire-de-crust"></a>

# Corbo Perimeter and Memory Verification

<a id="annotations-demprunt-et-littéraux-à-travers-mut_vref"></a>

## Borrowing and literal annotations through mut_vref

The parser accepts the prefix of borrowing in the annotation of a `let`.
The synchronous verifier compares the mode and type of the target to the borrow
produced. The digital pass recognises the type of return of the target.
`vref()` and `mut_vref()` on `A<T>`. In `*vue = 20`, the literal
So take the target guy.

Synchronous cases read `10` by an annotated view, write `20` via
a mutable view annotated or inferred, then release the allowance. Both entries refuse
an incompatible mode of borrowing, a target of bad
type, confusion between borrowing content and handle, a `drop`
before the last reading and a literal out of the terminals of `i32`.
An async case has an annotation on a direct digital loan
used after `yield`. Methods `vref()` and `mut_vref()` are
exercised in the synchronous compiler.

Two tests targeted at `-O0` and 55 tests at `-O2` pass, with UBSan
for native executions.

[Population target O0](../validation/core-borrow-annotations-o0.log) ·
[Regression O2](../validation/core-borrow-annotations-o2.log)

<a id="effets-de-dépendance-après-executionawait"></a>

## Effects of dependency after execution.await

N4–N5, AS8, RT5–RT6 and MT9. The appellant async resolves the existing task contract
against its local mutex. The mutex is reserved from capture. The original field and
arguments borrowed remain alive until the result is recovered. The compiler checks
the life of each written target, including a target replaced before the task is
completed.

After waiting, `Ok(())` find the end-of-task source and
`Err(LaunchFailed)` retrouve celle d'origine. Sans discrimination, les
Two remain possible. A conditional writing retains the old target on paths without
writing. A new writing invalidates the link between an old status and the current
graph.

The witness tests the direct match and the result named immutable, with a
`yield` In the task and in the appellant.
the appellant destroys the old target and re-reads `2` Injecting in custody.
`EAGAIN` to the submission of the handle child, it destroys the new target
and re-reading `1`. Both targets are destroyed once only.
compiler entries refuse to destroy one of the targets or mutex before waiting, to
read the mutex by another call during this reservation, and to store a target of too
short range. Variations also check for inverse destruction and ignored or outdated
status.

Connecting is about Void tasks that replace a field
`&i32` of a local mutex explicitly borrowed. The appellant async returns
Void or an independent scalar. Competitor players during booking, handle relays,
Select and direct wait for the task
Inactive remain outside this perimeter. `-O0` execute
4 methods and the replay to `-O2` 129. Both pass, with
UBSan for native oracles.

[Population target O0](../validation/guarded-await-targeted-o0.log) ·
[Regression O2](../validation/guarded-await-regression-o2.log)

<a id="effets-de-dépendance-des-tâches-sous-garde"></a>

## Dependence effects of custodial duties

N4–N5, AS8, RT5–RT6 and MT9. The contract for a task that writes
`charge.vue = &*nouvelle` in custody identifies the mutex argument, the field
and the argument that provides the target. The compiler checks each target stored by
the task against the duration of the mutex in the caller. He reserves the mutex to
the access of the task to the wait.

When reading the result of the `join()`, both branches are reunited with
graphes distincts. `Ok(())` uses end-of-task provenances.
`Err(LaunchFailed)` retains the initial provenances.
is ignored or that the exact graph is no longer identifiable, the two possibilities
remain followed. A conditional replacement also retains the origin of entry on the
paths without writing.

Witness checks the inferred contract, then executes the success paths
and failure of the first submission with a `match` direct and one result
appointed. `Ok`, it destroys the old target and re-reads `2` sous garde.
In `Err`, it destroys the new target and re-reads `1`. He checks the
The two entries of the compiler refuse the destruction of the target still stored in
each arm, its destruction before the join, a competing reader, a target too short,
the destruction of the old target when the writing is conditional and the same
destruction when the status is ignored.

The first extended replay found a refusal on the replacement of a field possessed
after transferring the recipient into a child block. The duration calculation chose
the parent's connection while the recipient was now in the child. The search starts
from the nearest range and the existing test returns to the two levels of
optimization.
[Premier rejeu](../validation/guarded-task-initial-o2.log)

Lot Perimeter. Direct Writing of a Shared Field `&i32` from a
Void task, target borrowed as a parameter and mutex possessed in the synchronous code
that creates the task and joins the handle. Competitive provenance mutations, handle
relays and async expectation of these effects remain outside this perimeter. Native
oracles use UBSan. Four methods
Targeted `-O0`, two to `-O2`, and the expanded replay passes on
128 methods to `-O2`. The ASan indicator of the previous cycle does not end
in this environment.

[Population target O0](../validation/guarded-task-targeted-o0.log) ·
[Targeted down O2](../validation/guarded-task-targeted-o2.log) ·
[Regression](../validation/guarded-task-regression-o2.log)

<a id="clôture-du-lot-dintégration-du-noyau"></a>

## Close the kernel integration batch

- Field replacements `&i32` and `A<Item>` in charge of a mutex
  The local authorities update the borrowing and the source of the allowance.
  scenario goes with `Mutex` and `AsyncMutex`, in direct writing and via
  A synchronous auxiliary. It releases the old target, reuses the slot of
  old field and check for only one destruction of the new field before
  The two entries refuse the premature drop of the
  The new target, the borrowing of a target too short and the transfer of a
  field whose pool does not survive the mutex.
- The verification requires a local mutex followed without further borrowing and a
  It refuses the change of origin of the entire charge.
  by a child task or through a shared mutex.
  content behind a already installed mutable loan remains covered by
  the competing scenario of the previous cycle.
- EBNF and kernel source entries exclude the four entries
  The Python APIs and the CLI expose them to the experimental scheduler.
  option. `check`, `effects`, `emit-c` and `build` have been
  tested in both profiles on the same experimental source.
- Thirteen examples use value displacement and primitives
  The non-notation controls exercise defects `i64` and `f64`.
  The two families of async aggregate tests were corrected to
  `A<T>`. Their historical fixtures retain the arrows used by
  negative variants. The first replay after text migration of the
  fixtures broke the substitutions of these tests and mixed both
  syntax. Modern equivalents check return
  owner and consumption by a sync function after `yield`,
  with re-use of the slot. Both cases of enums failed in `test_crust`
  and historical examples `borrowed_returns` and
  `mutable_reference_fields` received the same type correction.

The final pass performs 29 targeted tests at `-O0` and 170 tests at `-O2`.
The replay of the `test_crust` run 137 tests. The three passes pass
with UBSan in the oracles C.

The ASan minimum witness compiles and exceeds five seconds at execution. The coverage
of this cycle is based on UBSan and the oracles of exit and destruction. The
independent audit remains separate.

[Integration tests](../validation/core-close-integration-o0.log) ·
[Specified cases](../validation/core-close-final-targeted-o0.log) ·
[Final regression](../validation/core-close-final-regression-o2.log) ·
[Rejeu historique](../validation/core-close-legacy-ubsan.log) ·
[Exemples CLI](../validation/core-close-cli-examples.log) ·
[Scheduler's climax]](../validation/core-close-cli-scheduler.log) ·
[Asan Testimony]](../validation/core-close-asan-witness.log)

<a id="cycle-des-retours-async-et-charges-gardées"></a>

## Cycle of async returns and guarded loads

- Large-scale digital loan returns re-use the
  source of borrowings. The result of the waiting uses a member C
  the exact type pointer. `u64` covers direct waiting, both
  expectations of handle and return by an auxiliary after `join()`. Un
  test `f64` reads a field aligned borrowed from a structure.
  invalid variants check reservations until last use
  and the refusal to return a local target.
- A represented guarded charge retains the borrowed targets and the
  The sync, async and local async cases
  check access to the borrowed field and the possessed child, destruction
  The only one and the re-use of its pool. Two tasks modify a target
  borrowed mutable under the lock of the same mutex.
  a new provenance is refused in custody,
  including by an appeal the contract of which indicates that replacement.
- Two valid programs were refused with source diagnosis
  The local structure is too short.
  preceded or followed by a `if` The compiler now reserves
  the parent slot when the path joins the transfer with the same
  producer. The test controls the construction in the reservation and
  The cases not reproduced remain in the existing plan.

The targeted pass to `-O0` implemented 24 successful methods. `-O2`,
190 regression methods pass, as well as complements of 38
The oracle C uses UBSan with a stop at the first report.
[Pick-up target](../validation/core-dependencies-returns-o0.log) ·
[Placement](../validation/core-dependencies-placement-o2.log) ·
[Regression](../validation/core-dependencies-returns-o2.log) ·
[Running of returns](../validation/core-dependencies-reference-replay-o2.log)

<a id="cycle-du-runtime-intégré--9-novembre-2026"></a>

## Integrated Runtime Cycle · November 9, 2026

Perimeter. Integrated Runtime of RT2–RT8 and interactions with the
`.await` The context of pollution is represented by the direct, mutex and Select
in the C by a wake-up ticket that identifies the entrance and its generation. A child
poll inherits the target of its parent.

- The availability suite compares the runtime to an independent model
  On 2,401 tracks of four actions. Synchronised tests check
  alarms during the poll, the merger of notifications and the resumption
  on another thread without simultaneous poll. FIFO and Select suites
  also exercise their models and expired tickets after re-use.
- The new test forces the `Pending` a mutex in a chain of two
  `.await` direct. He checks that the file removed the root before the
  release of the mutex and that the mutex ticket means the root.
  Both pools of children are empty at completion.
  and his own capture are still busy. `join` extrait
  `17`, destroys the capture once, makes both slots and allows the
  Reuse of the catch address.
- Cleaning tests shall carry out inactive and suspended catches,
  launch failures and waiting obligations through the
  Calls. Select tests replay branch cleaning
  losers and the refusal to abandon a handle launched.

The wait chain test is now `-O0` and `-O2`, in addition
of 70 methods `-O0` and 124 methods to `-O2` of the two successful passes.
The regression to `-O2` also covers the memory kernel and placement
Async results. The oracle compiles in C11 with UBSan and stops at the first report.
No deviation of behavior required modification of the runtime in this perimeter.
[Pick-up target](../validation/core-builtin-runtime-o0.log) ·
[Regression to O2](../validation/core-builtin-runtime-o2.log) ·
[O0 Waiting Chain](../validation/core-builtin-runtime-direct-await-o0.log) ·
[O2 Waiting Chain](../validation/core-builtin-runtime-direct-await-o2.log)

The ASan witness compiles and exceeds the five-second time frame for execution. The
results of this cycle relate to scenarios and scheduling
[Asan Test](../validation/core-builtin-runtime-asan.log)

<a id="dernier-lot-du-noyau--9-novembre-2026"></a>

## Last batch of the kernel · 9 November 2026

This batch connects RT3, the digital borrowings of draft 07, MT9 and L7's parent
placement on the branches that continue. The signatures and language rules remain
those of the normative documents.

- The auditor monitors the possibility of a facility or launch
  It merges the paths that continue and reanalyzes the
  loop covers. Opaque calls propagate the launch effect
  This summary is conservative when an auxiliary throws
  a task only on a path that never returns.
  runtime remains. Exclusive branches can install instances
  if their storage is `main`.
- The fields of the digital profile are spaced to align with the `Cell`.
  This choice of backend C also maintains the alignment of the projections of
  nested structures. A field `u64` is borrowed by a sync auxiliary
  Another case lends a local scalar and refuses to accept a job.
  to make a copy of it by block `move` before the join.
- The structure mutex takes local value at its original address.
  The destruction of the charge destroys the charge.
  the latter, and a task that returns a copied value can release
  custody after the end of his local references.
- The plan for booking a `if` may exclude a branch that leaves
  the function. The test checks that the C builds the result in the
  parent's reservation, that the temporary is recovered before the result
  and that the return path releases the unused reservation.

The initial pass noted installation fixtures that reported a second unused scheduler.
The fixtures were corrected to achieve the desired control.
21 failures and 8 errors of sub-tests in historical suites
`test_async_owned_struct_returns` and `test_async_owned_struct_sync_calls`.
Auditor rejects local parameter compositions `T` and
pool allowances `A<T>`. Both of these suites remain in failure and their
fixtures have been preserved.
[Extended Pass Journal](../validation/core-final-lot-placement-o2.log)

The 19 methods targeted at `-O0` and 63 methods of placement replay
à `-O2` The regression of the kernel has executed 219 methods to `-O2`
In 160.7 seconds. The complement after the connection of the last return
field played 26 methods to `-O2`. These two passes have succeeded.
Oracle C uses UBSan with a stop at the first report.
[Pick-up target](../validation/core-final-lot-o0.log) ·
[Cut-off game](../validation/core-final-lot-placement-replay-o2.log) ·
[Neural regression](../validation/core-final-lot-verified-o2.log) ·
[Additional field borrowing](../validation/core-final-lot-fields-o2.log)

The programmable poll and line remain open, the returns of large digital borrowings
from a task, the loads of mutex that carry dependencies and the generalization of the
early placement. The ASan control of the previous cycle remains the last ASan control
executed.

<a id="cycle-dintégration-du-noyau--9-novembre-2026"></a>

## Kernel Integration Cycle · November 9, 2026

Perimeter of this pass. Numerical core of draft 07, transfers by value of native
threads, scheduler RT2–RT5, mutex MT9 and border
Scalar FFI1–FFI6. The [matrix]](VERIFICATION_MATRIX.md#intégration-du-noyau)
The collections APIs were used as a regression when they exercised a kernel rule.

- The kernel program uses the default target digital widths.
  Historical and `--legacy-numeric` keep a path of
  compatibility. `try_from` uses kernel error in the new profile.
  The results retain their width in the async states, including
  on a native jawn nested.
- Code C receives scalar signatures and Void compiles sources
  provided to `build` ou `run` Then bind them. The lexical perimeter
  of the `unsafe` is checked before lowering. The CLI tests compile
  and bind with native C compiler. Oracle C executes cases
  The first alert is interrupted by the first alert.
- The installation of a scheduler connects its three callbacks to the runtime under
  mutex. The backend C of this pass provides the FIFO file and loops
  - No, I'm not. `runtime::start_poller()` starts and records a polluter of
  this file, up to 64 for this implementation. `future.enqueue()`
  hands the task over to the backend, and `future.launch_failed()` triggers its
  clean and publish `LaunchFailed` via the handle. `spawn_blocking` utilise
  the path dedicated to blocking operations. The native thread bypasses
  callbacks. Order and single installation are checked at
  execution. Storage of an installed instance must belong to
  direct to `main` and its condition cannot contain borrowings.
  The tests also replay two exclusive installation branches,
  two installation diagnostics and a launch from a task with
  recovery of success and failure by `.await`.
  [Scedular testing]](../validation/core-integration-scheduler-smoke.log)
- The mutex source tests perform scalar loads.
  runtime separate exercise affinity of sync guard, wake up after
  release of an async guard on another thread and destruction
  reservations in Select.

The deviations encountered and corrected include writing a numerical join result via
a wrong type pointer, aligning the field
`i32` following a small scalar, the call of scalar function wide since
The first regression C also noted that the standalone runtime depended on a diagnosis
of the generated code. The diagnosis of the scheduler was based on the following:
now local to runtime. [C primitives' game]](../validation/core-integration-runtime-replay.log)

The target pass includes 13 methods to `-O0` and the replay of primitives C
22 methods `-O2`. The final regression to the `-O2` implemented 213 methods
In 154.5 seconds, all successful. It also covers the memory kernel, fixed arrays,
sync calls from a thread and Select.
`build --c-source` produced a binary whose output is `301`.
[Pick-up target](../validation/core-integration-o0.log) ·
[Final regression](../validation/core-integration-verified-o2.log) ·
[Commande build](../validation/core-integration-ffi-build.log)

The ASan minimum indicator compiles, then exceeds the five-second time limit
the execution in this environment. [Witness log](../validation/core-integration-asan-witness.log)

The remaining limits. `Future` and the line of a written scheduler
in Corbo remain open. The non-scalar loads of the mutex, the
Reborrowing of custody outside `i32`, direct borrowing of digital fields
The general anticipated placement and the removal of the historical profile remain
followed in the
[checklist](IMPLEMENTATION_CHECKLIST.md). Tests cover the programmes
A general proof, the transfer campaigns and independent audit are out of the way.

<a id="cycle-de-la-grammaire-du-noyau"></a>

## Cycle of the grammar of the nucleus

The [EBNF grammar]](../CORE_GRAMMAR.ebnf) describes the target kernel, including
Async forms. It is not used to compile programs. Compiler controls, including types,
lifespans and waiting obligations, apply after syntax recognition.

A temporary EBNF reader translated productions into recognition rules and exercised
them on 18 sources. Eleven are recognized,
dont `yield;` in an ordinary function, which must fail to
The other seven are rejected. The journal keeps each source and its expected result.
[Grandom verification]](../validation/core-grammar-check.log)

Four recognized sources were also verified, translated into C and executed under
UBSan with the current compiler, after substitution
d'`Int` à `i32`. They cover the named transfer, the capture block,
Select and native thread without capture. The compiler rejects well
`yield;` These are the prototypes.
[Verification of prototype](../validation/core-grammar-prototype.log)

After arbitration, the grammar was completed for the floating literals and both forms
of thread captures. The EBNF reader replayed the 18 initial cases and 14 additional
cases, without any deviation.
include the five forms of floating, one `let` annotated `f32`the distinction
with `1..3`, catches named or deducted, and refusals to accept a
This check is about syntax. The compiler is still to be adapted.
[Supplementary Journal](../validation/core-grammar-floats-and-thread-moves.log)

After the removal of exponential notation, the syntax verification
replayed 33 cases without a break. `1.5`, `1.` and `.5` restent reconnus, `1..3`
remains an interval and forms with `e` ou `E` are rejected.
[Journal of Decimal Literals](../validation/core-grammar-decimal-floats.log)

Four cases then checked the Boolean denial syntax
`!` and its distinction `!=`, without any deviation.
syntactic of an entire condition does not validate its type.
[Journal of conditions](../validation/core-grammar-boolean.log)

Five cases checked the bit-to-bit forms of operators, with no deviations. Cases
combine borrowing, comparisons and logical operators.
[Diary of operators bit to bit](../validation/core-grammar-bitwise.log)

Five cases of offset syntax pass. They distinguish the operators from comparison
chevrons or nested types and separate the syntax from the control of the number of
positions.
[Diary of Time difference](../validation/core-grammar-shifts.log)

Six cases check the syntax of the compound assignments, with no deviations. They
cover the five operators, an indexed access and a de-reference.
[Composite postings journal](../validation/core-grammar-compound-assignment.log)

The EBNF now covers the source forms of RT3, MT9, FFI1–FFI5 and the public name of
the digital error. The EBNF reader has replayed 53 archived cases and executed 15 new
cases, without any deviation. Eight are recognized, two of which are part of a
contextual rejection, and seven are refused by grammar. This passage exercises syntax
recognition. It does not validate the compiler for these new forms, nor the option
`--c-source` FFI6.
[Interface Journal](../validation/core-grammar-interfaces.log)

<a id="cycle-des-déplacements-par-valeur"></a>

## Value-based displacement cycle

The new forms of the [brown 02](../design-buffer/02-marqueur-transfert.md)
The signatures identify the parameters received by value and the proprietary results.
Blocks `move` calculate the lexical catches before analysis of the
The verifier retains responsibility for life, exclusivity and cleaning checks. The
movement transmits the same object. A captured scalar has its own copy in the block.

| Implementation | Result |
| --- | --- |
| Initial target pass O0/UBSan | 8 successful methods. [Journal](../validation/value-moves-targeted-first.log) |
| O2/UBSan decrease in functions, aggregates, borrowings, loops and tasks | 158 successful methods in 183.533 s. [Journal](../validation/value-moves-regression.log) |
| O2/UBSan replay after connecting table arguments and fixture correction | 38 successful methods in 37,748 s. [Journal](../validation/value-moves-final.log) |
| O2/UBSan replay with block result calculated by a call | 38 successful methods in 22,758 s. [Journal](../validation/value-moves-final-replay.log) |
| O0/UBSan final pass, with direct allocation as block result | 9 successful methods in 4,076 s. [Journal](../validation/value-moves-targeted-final.log) |

The modern suite runs eleven native programs. It checks twelve invalid variants at
the two compiler entries, including the second usage after displacement, a capture
before the last use of a borrow,
a pool too short and a pool too short `move a;` After the entrance of the block.
on the executed C verify the identity of the allowance, the single destruction and
the re-use of the slot.
copy of a scalar through `yield`.
[Tests](../tests/test_value_moves.py)

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest -v \
  test_value_moves test_core_memory test_spawn_blocking \
  test_strict_structure_returns test_local_enums
```

The first extended passage started before the stabilization of compatibility and test
expectations. Its balance is 593 methods with 29 assertion failures and 37 errors,
including sub-tests.
historical methods in failure of `test_foundation_rules` were then
Replayed on the current compiler and on a copy prior to the construction site. The
identifiers of the 15 claims failures and 10 remaining errors coincided between the
two executions. They remained open. Other failures in the first passage included
tests that still required the presence of arrows.
[Premier passage](../validation/value-moves-regression-first.log) ·
[Ancienne version](../validation/value-moves-historical-baseline.log) ·
[Rejeu actuel](../validation/value-moves-historical-current.log)

The compiler selects the historical grammar for a source with transfer arrows or with
reset compatibility enabled.
with `move` uses modern grammar.
native thread capture forms and async borrowing catches have not been the subject of
a general migration into this cycle. The results cover the cases exercised. ASan and
the adversarial audit are not part of the passes of this cycle.

<a id="cycle-de-validation-du-noyau-mémoire--8-novembre-2026"></a>

## Memory kernel validation cycle — November 8, 2026

The cycle covers N1–N8 transitions and their composition in selected cases, with
existing collections APIs. The grid is a synthesis of the rules. No normative rules
have changed.
[Rules](LANGUAGE_RULES.md) · [Matrice](VERIFICATION_MATRIX.md)

- The default profile ran ten targeted C programs. Nineteen variants
  invalids are refused with the diagnosis expected at both entries
  `verify_program` and `compile_source`. The assertions check in particular
  values, address identity, destruction order and re-use
  The target pass after correction also includes the case of a slot
  historical origin, i.e. ten successful methods in 4,087 s.
  [Tests](../tests/test_core_memory.py) · [Journal](../validation/core-memory-shadow-targeted.log)
- In the C of the transfer, the relay returns the same `Cell *`. L'appelant
  destroys the value before re-use of the slot. In replacement,
  the call and `cell_new` above `cell_drop` the old allowance.
  `cell_drop_impl` executes destruction before `cell_release_storage`.
  [Transfert](../validation/core-memory-transfer.c) · [Remplacement](../validation/core-memory-replacement.c)
- The old assertion of return `T` received a more accurate diagnosis
  of incompatibility `T / A<T>`Both entries already refused the program.
  The assertion was adjusted and the six methods of this module were successful.
  [Passe initiale](../validation/core-memory-regression.log) · [Rejeu](../validation/core-memory-diagnostic-replay.log)
- Three historical fixtures replaced the first value without using it.
  Each now reads this value, according to U1. The case with masking
  Then revealed an incorrect refusal. The compiler's analysis deals with
  now the name as masked until the end of the block, taking into account
  the exits that prevent the outside use. The current test
  exercises accepted external use and refusals when only the inner name
  is read or when a return prevents outside use.
  [Refus initial](../validation/core-memory-legacy-flow-replay.log) · [Target game](../validation/core-memory-shadow-targeted.log)
- The ASan+UBSan pass of the historical profile was interrupted after
  The minimum instrumented C executable, which displays
  a line then ends, reproduced the time limit without exit.
  The ASan result is
  The selected suites use UBSan with a stop at the first
  diagnosis in the harnesses.
  [Harness control]](../validation/core-memory-asan-toolchain.log) · [Journal interrompu](../validation/core-memory-legacy-flow.log)

The four final passes returned the code 0. The manifest keeps the controls, the
harness variables and the 415 Python prints, identical before and after the passes.
The C compiler used is Clang 20.1.3. on arm64.
[Manifeste](../validation/core-memory-final.json)

| Passe | Successful methods | Temps unittest | Configuration and journal |
| --- | ---: | ---: | --- |
| Core, contracts, Select and launch | 111 | 96,775 s | [O2/UBSan](../validation/core-memory-final-regression.log), with historical variants in the refusal of spamn_blocking |
| Native threads and wake-ups | 23 | 24,242 s | [O0/UBSan](../validation/core-memory-final-threads.log) |
| Placement, limits and suspension cleaning | 32 | 29,612 s | [UBSan](../validation/core-memory-final-storage.log), O2 and O0/O2 for regional probes |
| Buckles, junctions and receiver use | 42 | 47,333 s | [O0/UBSan](../validation/core-memory-final-legacy-flow.log), mainly compatibility profile |

Existing models have been replayed for Select storage requirements, poll and
cleaning, both cursor intervals, suspension cleaning and receiver replacements. The
generated scenarios retain the seeds reported in their tests, including 9081, 2219
and 6077 for storage intervals, and 20261103 for junctions.

The proof of execution covers the paths exercised. General advance placement and
competing guarantees beyond the tested scenarios remain open. The public construction
of the mutex and the public interface of the personalized scheduler remain to be
arbitrated. The transfer campaign and the in-depth adversarial audit are the
responsibility of the independent lab.

<a id="historique-de-laudit-initial--1er-novembre-2026"></a>

## History of the initial audit — November 1, 2026

## Statut

Corbo is designed to generate C according to pre-issue verified memory rules. Checker
tests, executable invariants, and runtime controls provide verifiable evidence. They
do not constitute formal proof that all accepted programs are safe.

The initial audit sought counter-examples without adding functionality. The following
developments are now implemented and tested separately: collective reset, destruction
of the old allocation after evaluation of a reallocation and expressions in the
arguments evaluated from left to right.
Instructions `if / else` with memory effects and return Void/scalar or
same type of allocations with possible sources being added to the bounded perimeter
described below.
Expressions `if` may also provide an allowance of the same
type to a receiver, via a `<-` final in each branch that continues.
`loop`, `while`, `break` and `continue` add analysed repeats until stabilization,
Iteration cleaning and separate output of function returns.

<a id="sous-ensemble-concerné"></a>

## Sub-group concerned

- Synchronous execution, lexical blocks, non-recursive functions and `main`.
- Symbolic summaries of external effects of sources, inferred for all sources
  functions and spread in sub-calls, even without a concrete call.
- Symbolic summaries of the results allocated: new origins, incoming identities
  returned or selected, propagation and verification of origin of calls.
- Symbolic constraints on equality and distinction between sources, inferred
  in the order of operations and verified for all sources of call.
- Verification of movements, borrowings and memory transitions of each body
  with symbolic entries, even without a real call.
  Specialisation remains active at calls; unused bodies are not issued.
- Expressions in the arguments evaluated from left to right, with protection
  allocations and loans prepared until the call.
- Int32, Int explicit allocations and Int field enums, &Int or &mut Int.
- Lecture `*data` the Int content of a valid loan or allowance.
- Explicitly selected local sources: pile, data stack or typified pool.
- Reading and mutable borrowings, direct transfers and transfers between
  activations parentes/enfants.
- Destruction automatique, `drop` and collective destruction by
  `reset`, with refusal of future access to the relevant allowances.
- Branches `if / else`, Int comparisons, literacy conditions and returns
  Void/scalar or similar allowances; junction and conditional cleaning.
- Expressions `if / else` providing an allowance to a recipient, including
  `else if`, transfers of the parent and branches leaving the office.
- `loop`, `while`, `break` and `continue` Unlabelled, with results of `break` for `loop` : analysis, cleaning
  Iterations and meeting of exits; divergence without fictitious result.
- `match` comprehensive. `&mut`, arms can write in targets of
  leurs projections mutables via `.set()` or re-borrow them by a call
  `Void`. The arguments mentioned remain projections of the arm.
  [Validation](MATCH_MUTABLE.md).

Return of loans to other types than Int, reference fields
Other than &Int/&mut Int, transiting graphs of
dependencies, user destroyers, collections, `for`,
Loop labels, threads, asyncs and external C calls are not part of this subset. They
should not be considered covered by current tests.
The immutable &Int fields are described in [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md).
The automatic transfer of their dependencies is prohibited by D1; function returns
are now allowed for targets already quite durable in the destination. Refusal is a
rule of language, not a delayed promotion.

[direct returns &Int](DIRECT_BORROW_RETURNS.md) follow the identities of the
targets and checks them at each child border → parent, without any implicit
allocation or promotion. Their future uses protect all possible targets, including
through multiple calls and storage in a &Int field.

<a id="obligations-et-contrôles"></a>

## Obligations and controls

| Obligation | Current mechanism | Validation elements |
| --- | --- | --- |
| Allocation attached to an active scope | Status of allocations, check at the border of instructions and scopes | Block tests, calls, returns and cleanings |
| Living source during the life of the allowance | Source retained; refusal to escape from a local source; invariant state | Transfers from too short sources, parameters and enum pools |
| Direct access usable by allocation | Invalidation during travel; separate local access during downward transfer | Returns with explicit receiver and regular returns |
| Emprunt mutable exclusif | Latest uses, access control and arguments aliases, suspension during reborrowing | Reading, writing, interlocking calls and attempts to move |
| No access after destruction or double destruction | Shared status of allocation, invalidation of accesses consumed, withdrawal of final cleaning | `drop`, collective reset, call effects and re-use of slots |
| Valid access on all paths that continue | Separate branches, junction, independent cleaning indicators of slots | Conditional destruction, returns, borrowings, calls and enum pools |
| Consistent type and initialization | Typed source, field and signature validation | Variations, missing/duplicated fields, bad pools and returns |
| Access to the fields in the right variant | Known diagram and `match` comprehensive translation into `switch` | Reading each variant and refusing incorrect patterns |
| Stable and bounded storage | Virtual reservations, aligned strides, capacity controls and on-call page | Address comparisons, exhaustions, oracle of runtime |
| Free index and coherent cursor | Removal of slots from the suffix before recoil, intrusive list of free locations | Arbitrary and oracle sequences independent of compiler |

The auditor's executable invariants share his status model: they detect
inconsistencies in this model, without independently proving that his life-span
analysis always corresponds to the execution of the C.

`drop(-> value)` and `source.drop(-> value)` share the checks of
The first form uses recorded provenance, while the second also checks the explicitly
supplied receiver. Destruction via provenance does not create an implied source and
does not circumvent borrowing restrictions. These two forms are compared by trace and
cleaning tests exactly once.
The [Explicit destruction contract]](DROP.md) also details calls
The main objective of the programme is to:
These cases are verified in a slot `tests/test_drop_transitions.py`.
The [reset contract](RESET.md) specifies collective destruction, refusal
the future uses and internal C parameters necessary for its implementation
regressions are in a function. `tests/test_reset_transitions.py`.
The [reassignment contract]](REASSIGNMENT.md) distinguishes the end of the evaluation
The tests include borrowings used in this expression, functions that consume or
return the same allocation, and limited pools.
The [Argument Contract]](ARGUMENTS.md) specifies the order of the effects, the end of the
sub-call borrowings and the protection of prepared arguments. The last-use analysis
now distinguishes sub-expressions from an instruction.
Regressions are in `tests/test_arguments.py`.
The [Contract of Conditions](CONDITIONALS.md) describes the separate states by branch,
availability on all paths that continue and independent cleaning indicators of slots.
Branch returns are also gathered when the function returns to keep their effects at
the caller.
are in `tests/test_conditionals.py`.
[conditional returns of allowances](CONDITIONAL_RETURNS.md) the
A uniform return of the same incoming allowance retains its identity and its import
correspondence; the other candidates follow the meeting that removes the old returned
identities without destroying the executed objects and retains the other effects of
the paths. The responsibility for cleaning is transferred with the result:
disarmament of the old indicator, restoration to the same scope when necessary, and
exclusion of indicators of a finished function. The junction only obliges the order
for the still alive allocations on each path.
Regressions are in `tests/test_conditional_returns.py`.
The [if expressions with receiver](IF_EXPRESSIONS.md) use variable C
The balance sheet distinguishes the branches which provide an allocation of the
branches making up
`return` ; the types must coincide on the paths that continue.
Regressions are in `tests/test_if_expressions.py`.
The [loop contract]](LOOPS.md) describes the analysis of the recoveries, the borrowings
used in the following iterations, front cleanings `break` ou `continue` and
The indicators are activated at the point of use, in each iteration concerned, and
their context C is followed so as not to reference a variable of the caller from
another function.
are in `tests/test_loops.py` and `tests/test_continue.py`.
The [Wheel contract](WHILE.md) add the test in the iteration scope, its
the re-examination of the test after the `continue`, and the connection with
exits by false condition, including that preceding any execution of the body.
Regressions are in `tests/test_while.py`.

Runtime controls also impose a target with a `int` 32-bit C,
compatible page alignment and controlled capacity calculations. The cursor
verification precedes subtraction of the remaining capacity.

<a id="contre-exemples-trouvés-et-corrigés"></a>

## Counter-examples found and corrected

<a id="accès-dupliqué-après-réception-explicite"></a>

### Duplicated access after explicit receipt

The programme was accepted:

```rust
let mut memory = allocator();
let mut a = new(memory) Int(1);
let mut b = {
    -> a;
    <- a;
};
let mut c = <- b;
print(a); // Ancien accès encore accepté à tort.
print(c);
```

Downward transfer used the same tracking object for parent access
and the child's. Receive the return in `b` laissait donc `a` utilisable.
This example showed a deviation from our displacement rule; it did not alone
demonstrate access to a freed memory.

The parent now loses access to the child's entrance, which receives separate access.
A return received in a new variable does not reactivate the old one.
The above programme is rejected on `print(a)`.

The already defined case of ordinary return remains valid:

```rust
let mut a = new(memory) Int(1);
{
    -> a;
    <- a;
}
print(a); // Le retour restaure explicitement l'accès initial du parent.
```

<a id="bloc-imbriqué-dans-un-initialiseur"></a>

### Block embedded in an initializer

A block used in an Int initializer could cause a `KeyError`
Python: its instructions had not been indexed for analysis. Crossing of
sub-expressions is now common to indexing and last-use analysis. Non-typeable
constructions produce a verified diagnosis, without C emission, instead of this
internal error.

The audit also added limited diagnostics for too long integers, non-ASCII numbers,
truncated source ends and interlockings that exceed the prototype capacity.

<a id="résumés-deffets-des-fonctions"></a>

## Summary of effects of functions

The [contract of effects](EFFECTS.md) describes the symbolic analysis of the sources of
The external effects observed by the specialized analysis should be included in the
inferred summary; a deviation causes the compilation to be refused before the C is
executed.

Local sources are not confused with parameters of the same name. A reset forbidden by
a read parameter is detected even in a non-called function. The passage on bodies and
opaque contracts completes this analysis for the types, identities and lifespans of
the subset. Pool requirements are retained even when a sub-call does not allocate
anything.
in `tests/test_effects.py` and `tests/test_pool_requirements.py` ; the
[cycle report](POOL_REQUIREMENTS_VALIDATION.md) details of the evidence and limitations.

<a id="résumés-des-résultats"></a>

## Summary of results

The [performance contract]](RESULTS.md) describes the alternatives to allowances
The results of the specialisation must comply with the contract before the C is
compiled. This does not replace the checks of movements and borrowings or the
complete memory verification of the bodies to the calls. The regressions are not a
substitute for the arguments; the possible sources of the result are protected and
its identity restored when guaranteed. The original roots are followed statically
through the selections, without comparing addresses, in particular to distinguish a
re-used slot from an object rendered.
in `tests/test_results.py`.

## Contraintes entre sources

The [source relations contract](SOURCE_CONSTRAINTS.md) describes equality
for destruction with explicit receiver and distinctions necessary when accessing
after resets. Historicals are separated in branches, gathered on continuations and
stabilized on loop covers. Subcalls substitute their obligations and the results
received alive are not invalidated by a blind application of the possible resets.

Any possible source must satisfy the constraints of the call. The appellant's
prepared arguments and future usages remain protected. This analysis does not add to
the runtime control and does not replace the complete controls on borrowing and
travel.
`tests/test_constraints.py`.

<a id="corps-vérifiés-sans-appel-réel"></a>

## Body checked without actual call

The [body verification passage]](FUNCTION_BODIES.md) gives each function
symbolic inputs respecting modes, types and source equities. It re-uses the verifier
of the displacements, borrowings, branches, loops and outputs of telescopes; its
state and temporary C are isolated and then thrown away.
Regressions are in `tests/test_function_bodies.py`.

This control also detects memory errors in unused functions,
The [contract calls]](MODULAR_CALLS.md)
control the caller's modes, types, sources and transitions without opening the called
bodies. The concrete sources are verified in the instructions of the
programme or `main`. The specialized backend keeps a generation path
with its consistency checks; `check` Stop before that backend.
This is not independent evidence of the existing auditor.

## Provenances multiples

The [contract of provenances](PROVENANCES.md) describes the source unions in
returns and expressions `if`, their spread in calls and the
Conservation protection of each possible source. The lifespans and types are checked
for all these sources. The objects remain at their address.

After the last use, a reset of a possible source destroys the selected object only if
it actually belongs to this source. Indicators protect cells already dead; survivors
remain followed for other resets or final cleaning. Enum pools are recognized by
their public root despite the physical provenance of the arm.
are in `tests/test_provenances.py`. This is not yet a
general proof of provenance; symbolic control of bodies and contractual calls is
described above.

<a id="audit-des-correspondances-avec-le-c"></a>

## Audit of correspondence with C

The [targeted audit of 2 November](AUDIT_MEMORY.md) corrected a reading too late
enum fields in C and loss of identity upon conditional return
the first changed a calculated value;
the second refused a valid return. Neither of the two counter-examples
demonstrated access after release. Tests add an independent model
destruction order, as well as combinations of loops, borrowings and
transfers. `tests/test_audit_regressions.py`.

<a id="tests-et-instrumentation"></a>

## Testing and instrumentation

The extension of [fields &int](REFERENCE_FIELDS.md) adds dependencies of
reading allowances, prepared borrowings and call constraints.
The [matrix]](VERIFICATION_MATRIX.md) reference its limited coverage.
the return containing these loans is not implemented; the returns containing these loans are
controlled according to [BORROWED_RETURNS.md](BORROWED_RETURNS.md). The
conservative behavior of the diverging resets is maintained.

The contract for cleaning normal exits and anticipated returns, with
an example of C translation, is detailed in [SCOPE_EXIT.md](SCOPE_EXIT.md).
The corresponding regressions are in `tests/test_scope_exit.py`.

Validation results, after adding returns containing borrowed fields:
605 tests passed in the standard suite and 605 tests passed with
`CRUST_SANITIZE=undefined`. The oracle of the runtime is included in both
The details of the instrumental binaries are given below.
The [matrix of the 66 rules]](VERIFICATION_MATRIX.md) distingue couverture partielle,
specification review and unimplemented rules.
[Report of pool requirements](POOL_REQUIREMENTS_VALIDATION.md) keep the
results of the independent model, mutations and controls C to several
optimization levels. [field cycle &Int](REFERENCE_FIELDS.md) conserve
his model of dependencies, his four mutations and his twelve executions C. None of
these measures establishes a general proof of safety.
The [cycle of returns of borrowing objects](BORROWED_RETURNS.md) add the model
the boundaries of the scopes, the regressions of reborrowings and the re-launched
campaigns after discovery of an additional counter example of exclusivity.

The [direct &Int return cycle](DIRECT_BORROW_RETURNS.md) then carry the
post- **632 tests passed in standard mode and 632 in UBSan**. Il ajoute
27 methods, a limited model of 24 roads (12 admitted/12 refused), five mutations
selected and nine replayed previous, plus twelve C-runs
The [gross results]](../validation/direct-borrow-suites.json)
The return is not responsible for destruction and does not extend the life of its
target.

The [clarification of existing references](REFERENCE_VALUES.md) remplace
then the written reborrowings `&reference` by the name of the reference in the
calls and returns. **647 standard tests and 647 UBSan tests pass**,
With 15 new methods, five specific mutations and 14 previous detected, and 36
optimized C performances compliant. Contracts, last uses, drop/reset and child
borders → parent remain checked. The nested references are refused, without
flattening.
[gross results](../validation/reference-values-suites.json) distinguent ce cycle
previous measurements; memory oracles of migrated fixtures are preserved.

The [cycle let / let mut](LET_MUTABILITY.md) then add the mutability of the
Bindings and Int content writings without allocation. **672 tests standard
and 672 UBSan pass**with 25 new methods, 33 programmes
In the case of new applications and 50 rejected in their corpus, five new and 19
previous mutations detected, and 48 C performances optimized in accordance. The
content/capacity models and the monitoring of resets in contracts are described in the
[rapport brut](../validation/let-suites.json). Meters of previous cycles
The deletion of var/global set does not alter the memory oracles expected from the
migrated fixtures.

[back &mut Int](MUTABLE_BORROW_RETURNS.md) then extend B5 to loans
exclusifs. **700 standard tests and 700 UBSan tests pass**,
with 28 new methods, a corpus of 28 programs admitted / 58 refused,
29 selected errors detected and 60 C-exes optimized in accordance.
Returns do not create object or responsibility for cleaning; each possible target
keeps child exclusivity and verification → parent. The last use of an Int allocated
after writing content has also been corrected for V4/U1.
The [gross report](../validation/mutable-return-suites.json) distinguishes the measures,
the repaired injection incident and the limits of this limited validation.

```sh
# Suite complète, y compris compilations et exécutions C.
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q

# Régressions adversariales et oracle du runtime.
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_safety.py -v

# UBSan, avec arrêt au premier comportement indéfini détecté.
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q

# AddressSanitizer et UBSan, quand l'environnement les exécute correctement.
CRUST_SANITIZE=address,undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
```

The sanitizer options are applied to the C compilations of the test harness and to
the oracle. The integration tests invoking the CLI build their binaries with the
usual options of the latter; these binaries do not become instrumented by this test
variable.

The oracle of `tests/test_safety.py` Call the runtime directly, without passing
On 3,000 deterministic operations, he compares the living values to a reference table
and checks, after each operation: the uniqueness of living slots, meters, physical
order, free list, alignment of positions, cursor terminals and recovery of suffixes.
He uses two variants of different sizes and then resets and closes the whole.

This exploration is limited. It does not cover all possible sizes, sequences,
platforms or exhaustion conditions.

On the environment of this audit, AddressSanitizer could not be validated: the
instrumented oracle expires after 10 seconds, and an empty C program instrumented
with ASan also expires after 5 seconds, including outside the sandbox. No "ASan
successful" result should be inferred from this trial.

<a id="base-de-confiance-et-suites-nécessaires"></a>

## Trust and follow-up required

The confidence base includes the parser, effects, results and constraints parser,
Python memory checker, C generation, runtime, C compiler and system memory
mechanisms. Change the generated C or manually link arbitrary C comes out of the targeted warranties.

The absence of immediate leakage does not mean that any dead storage is returned to
the system: slots can remain reserved for reuse. A stop on exhaustion does not unfold
the destroyers. This is part of the explicit limits of the prototype.

Before presenting the subset as a safe one, the following are the main points:

1. Formalize the transitions of telescopes, access and borrowing, and then connect them
   operations C issued.
2. Check for properties to be retained in each form of expression and to
   each scope output; internal invariants alone are not enough.
3. Expand independent exploration and operate ASan on target
   adapted, especially for heap allocations and mapping limits.
4. Re-evaluate these obligations on each language extension: add a new language
   functionality does not mean automatically extend the warranties.

## Champs contenant &mut Int

The &mut Int fields retain the exclusive capacity on their targets through the
movement and return of objects. The shared references to the same carrier retain this
capacity.
of the arm described in [the next cycle](MATCH_MUTABLE.md). Chaque
child border → parent checks sustainability without implicit promotion.

The cycle consists of 29 dedicated tests, 24 separate sources allowed performed and
43 rejected by both courses.
24 scenarios; 35 injections selected from copies are detected and
48 C-exements cover O0/O2/Os/O2-UBSan. The audit corrected a descriptor that
It lost its real type and could have a W borrow accepted in an Int field. Overall
measurements, first replaced campaigns, incidents and
limits are described in [MUTABLE_REFERENCE_FIELDS.md](MUTABLE_REFERENCE_FIELDS.md).
This is not a general proof of safety.

The overall results of this cycle pass 729 tests each, in standard and in
the UBSan configuration of the harness, without any test ignored.](../validation/mutable-field-suites.json)
are kept; this instrumentation does not automatically apply to every binary built via
the LTC.

<a id="cycle-du-noyau-numérique"></a>

## Digital kernel cycle

The digital profile of [brown 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#types-primitifs-du-noyau)
connects the scalar types to the parser, context typing, contracts and backend C. It
uses the historical internal representations of Int and C
Bool for paths that share them. The profile syntax uses `i32`
and `bool`. A source without a digital type or syntax marker may
explicitly select the profile with `--numeric-core`. The inference of the
profile preserves historical programs.

The constant evaluation rounds the floats from an exact fraction. The backend
materializes the operation in the order of evaluation and controls the terminals
before the conversions that can truncate.
use intermediaries `__int128` The backend is exercised with
IEEE binary formats to be rounded to the nearest, on the validation target.
`try_from` reuse `IntegerConversionError::OutOfRange` for failure of
representability, including when a floating type is involved.

- The [targeted follow-up]](../tests/test_numeric_core.py) passes his 10 methods in
  [O0/UBSan](../validation/numeric-core-targeted-o0.log) and in
  [O2/UBSan](../validation/numeric-core-targeted-o2.log). Each pass checks
  21 invalid variants at both entries and run 19 native programs,
  of which nine must stop on a diagnosis at the execution.
- The [regression O2/UBSan]](../validation/numeric-core-regression.log) passe
  131 methods in 63,325 s. The suites cover the memory kernel, the
  historical conversions, storage, local enums,
  Async loop copies and outputs and fixed tables. The test
  history of the drop of a result now awaits acceptance of
  `drop(u8::try_from(42))` in modern syntax.
- Orders `check`, `run` and `effects` accept the program without
  annotation that prints the high terminal of `i64`, with the forced profile.
  [Journal CLI](../validation/numeric-core-cli.log)

The typing of the aggregate fields with the new formats, the numerical conversions
and allocations carried by the tasks and the assignments composed on fields or
de-references remain to be connected. The composite assignments exercised concern
variables and fixed tables. The re-use of synchronous pools is measured by the
address and the value re-read. The trace of historical destruction shows the entire
field of the slot, which does not contain the expanded numerical load. The evidence
is limited to these executions and to this target.
