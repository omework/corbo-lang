[Français](TASK_WAKES_CYCLE-fr.md)

<a id="rt2--réveils-conservés-et-attente-dévénement"></a>

# RT2 — Revealing and waiting for events

<a id="périmètre-normatif"></a>

## Normative perimeter

This lot applies the part of RT2 and draft 04 concerning a single poll
active, keeping a wake-up reception during this pollution and regrouping
No language rules are changed. The protocol is internal
at the C of the runtime; it is not yet a clock API accessible in Crust.

The old runtime distinguished only `YIELD` and `RETURN`. Toute suspension
So immediately it was possible to reinvocation the body.
did not represent the expectation of an event required to schedule it and
Select. The new internal result `TASK_STEP_PENDING` suspend the body
until a wake-up call; `TASK_STEP_YIELD` makes it ready immediately again.

<a id="implémentation-et-invariants"></a>

## Implementation and invariants

- An initialized task has a permission to poll.
  this permission presents, without accumulating a meter of future pollution.
- The take of the poll consumes permission under a short atomic lock.
  The body runs out of the lock, so that it can wake up itself.
- A wake-up while the body is in the body retains permission.
  Pending does not erase. A task completed or consumed ignores the awakening.
- Synchronous and detached launches also consume their permission
  If not, Pending would be re-polished without an event.
- The consumption of the finished state is synchronized with its publication.
  Extraction and release take place out of the lock, in this order.
- Storage remains stable during the poll. Another thread can resume
  The condition after the end of the previous poll; no simultaneous body is allowed.

The code is in `async_runtime.py`. The difference with snapshot
previous is kept in `validation/task-wakes-runtime.patch`.

<a id="oracles-et-contre-exemples"></a>

## Oracles and counter-examples

`tests/test_task_wakes.py` contains four methods:

1. An independent model describes a permission to execute and four phases
   logic, without using the locks, pointers or compiler decisions.
   It lists the 2,401 sequences of four operations among seven operations
   (revealing, poll Pending/Yield/Return, wake-up during Pending, taking the result,
   Inactive destruction), or 9,604 transitions.
   Numbers of invocations, results of operations and number of releases.
2. Vingt essais gardent un poll ouvert pendant que quatre autres threads
   Each try to a hundred alarms and poll. A replay on the main thread
   keeps the address and ends the task. The first thread remains alive
   to prevent the re-use of its identifier in migration control.
3. Launches with join and with detached waiting remain suspended without
   notification, then produce their result and only one cleaning after alarm.
4. Two hundred essays run Pending's publication and awakening.
   The next recovery must be completed, and then destruction will only take place once.

The first targeted test contained a døoracle error: `task_async_finish`
returns a zero status if successful, not a true boolean.
has been corrected; neither the runtime status nor the rule has been changed.
The initial log is kept. An import class of tests had
also included the entire async suite in this first launch; import
is corrected and this launch is reported separately from the targeted passages.

The general regression also found a historical expectation contrary to V4:
`test_async_mutable_result_extends_exclusivity_until_its_last_use` exigeait un
refusal to grant `let view = lend(&mut n).await; view.set(...)`. V4 allows writing
of the target via `&mut` even if the bond cannot be reassigned.
reproduced with the previous snapshot runtime
(`task-wakes-mutable-result-baseline.log`) The test now requires admission
and execution giving 4; its exclusivity and local leak checks remain
unchanged. `task-wakes-mutable-result-final.log` pass: one method, 2,460 seconds.

<a id="preuves-exécutées"></a>

## Evidence

- `validation/task-wakes-complete-o0.log` : four successful methods,
  4.664 s, including the model and the races.
- `validation/task-wakes-complete-mutations-o2.log` : baseline of four
  successful methods, 4,649 s; the six injected errors are detected by
  Asserts executed in binary. Mistakes render Pending
  spontaneously ready, erase an alarm clock during the poll, ignore alarms,
  omit availability control, retain initial permission of
  worker ou autorisent un poll pendant un autre poll.
- `validation/task-wakes-native-mutations-o2.log` : the six mutations
  The pre-existing native border is detected.
  native thread to the scheduler fails by assertion in its variant
  synchronizes and also exceeds the time limit in its detached variant; the time limit
  only is not presented as evidence of detection.
- `validation/task-wakes-native-o2.log` : 302 successful methods in 312.219 s.
  This launch includes the first three methods of waking up; the fourth
  (Course alarm clock/publication) was then added and passed into both
  Final targeted baselines above.
- `validation/task-wakes-initial-o2.log` : 278 methods, 489.570 s,
  276 successes and two failures in testing expectations.
  the former assertions before their correction: null status of the
  `task_async_finish` and immutable reference link.
  The adjusted target baselines are the final and the
  `task-wakes-mutable-result-final.log`. Runtime did not change during
  The original newspaper is still being presented with its two failures.
- Python compilation of successful runtime modules and modified tests.

Harnesses use Clang C11/pthread, fatal warnings, fatal UBSan
and O0/O2. Counts are methods or transitions according to their wording,
not interchangeable Crust source program numbers.

The native and async suites are overlapping: their counts are not at the same time
add in number of separate programs. Final coverage is
distributed between regression and targeted re-executions; no passage
unique entirely green of the entire deposit n

<a id="limites-et-travail-restant"></a>

## Limitations and remaining work

Runtime Runtime Runtime Continues to Call `sched_yield` and to check availability
He's not running the Pending body without permission, but this
lot does not yet provide a task queue or a cost-effective system expectation.
It does not establish the general fairness of the scheduler or its public replacement.
Current expectations from the compiler continue to use
Yield; event connection of expectations and awakenings of parents,
Select and mutex still have to be realized.

The pointer that woke up must stay alive until this call returns.
The tests explicitly retain the states until all the
threads. A public alarm API will ensure the life of the registrations,
the withdrawal and protection against re-use of a slot; this lot does not provide
No alarm clock on a pointer already released is allowed.

The races performed are over; the tests do not prove all the
no general absence of data races. No new results
ASan/TSan, second compiler, benchmark or formal evidence is claimed.
RT2 remains partially implemented and the overall objective remains open.
