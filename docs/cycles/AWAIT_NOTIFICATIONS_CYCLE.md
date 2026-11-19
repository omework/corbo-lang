[Français](AWAIT_NOTIFICATIONS_CYCLE-fr.md)

<a id="rt2--notifications-des-attentes-async"></a>

# RT2 — Notifications of expectations async

<a id="portée-et-implémentation"></a>

## Scope and implementation

This lot applies RT2 and AS4 of draft 04, without changing the normative rules.
The waiting for a launched handle will record a ticket to the task that drives the poll.
A direct line of waits transmits this ticket to the child waiting
The direct child remains executed on the thread of his appellant.

A recorded expectation makes Pending; it no longer spontaneously returns to line.
Yield retains his voluntary behavior.
dedicated workers and native blocks also provide notifications.
A harness without a ticket or entry retains its former behavior by Yield.

The registration and withdrawal of the child is serialized by the mutex of his/her
The notification of his parent comes outside this mutex, so that he can
not to interlock the locks of two entries. It precedes the final publication
of the `worker_done` : a detached thread should no longer notify a context after
to have made its own end observable. If the parent resumes in this interval,
he makes Yield until publication; he does not fall asleep without notification
This transitional passage does not promise the absolute absence of re-pollution.

Generational tickets protect the re-use of frames.
waiting for the handls ensures that the appellant retains the necessary condition.
The current protocol contains only one consumer per handle; Select is not
Not implemented by this lot.

<a id="contre-exemple-corrigé"></a>

## Corrected counter-example

A C submission with a different entry than the pre-associated one in the frame
did not update `task->queue_entry`. The expectation therefore consulted the wrong
entry, or no entry, and the parent could turn by Yield rather than
The sequence test of events, without manual pre-association,
fails on the assertion that only the child task is ready.
now the actual input frame used.

Previous reproduction:
`validation/await-notifications-submission-entry-before.log`.
This defect concerns the internal protocol; normal factories used
already the same entry when submitting.

<a id="vérification-ciblée"></a>

## Targeted verification

`tests/test_await_notifications.py` has three scenarios:

- Crust Program: A local picture and its borrowing go through two expectations
  The sheet is suspended by the harness.
  A hundred attempts to withdraw find no task ready before it wakes up.
  Two poll per function is then enough, the result is 9, and twenty
  re-employment reject the old tickets.
- Orders imposed: end before registration, during the parental's poll, after its
  The two parties are:
  End paths (dedicated thread and worker) are exercised, twenty-five times each,
  The oracle sets the number of pollutants and the number of emissions.
  destruction since this order of events, regardless of the flags ready.
- Two real workers reuse the states 200 times, alternatively with
  waiting for the end of the child inside the poll and immediate return of the child
  Pending. Each result is 42, each state is released once and
  The old tickets are refused.

The tests use Clang C11/pthread, fatal warnings, fatal UBSan.
Implemented:

- Initial selection O2: 21 methods, 16.267 s, success
  (`validation/await-notifications-initial-o2.log`).
- Final targeted selection with queue and wake-up: 12 successful methods at O2
  in 14,580 s and at O0 in 11,256 s
  (`validation/await-notifications-final-o2.log`, `…-final-o0.log`).
- The concurrent test was then added: the three specific methods
  go to O2 (`validation/await-notifications-concurrent-o2.log`) and O0
  (`validation/await-notifications-concurrent-o0.log`).

Selections are overlapping. They do not measure a general coverage
programs and/or scheduling.

## Mutations

Seven errors detected by behavioural assertions: root ticket not
transfer, registration deleted, notification deleted, Pending changed to
Yield, sleep in the publication interval, end published too early and
non-associated submission entry.
`validation/await-notifications-corrected-mutations-o2.log`.

The first campaign changed `TASK_RUNTIME` for the transmission of the ticket,
while the compiler assembles `TASK_RUNTIME_BODY`. Its survival was a
The script now changes the process of the transfer from the generated program to the
body and reconstruct the constant of the harness; fault is detected without
The original logs are kept.

The six line mutations and the six native border mutations are
also detected after adaptation of anchors to new functions:
`validation/await-notifications-queue-mutations-o2.log` and
`validation/await-notifications-native-mutations-o2.log`.
Timeouts and compilation errors do not count as detection in
the new campaign.

<a id="régressions-et-limites"></a>

## Regressions and limitations

The expanded campaigns have been successfully completed: 275 async methods in
553,965 s (`validation/await-notifications-async-o2.log`) and 311 native methods
in 293.694 s (`validation/await-notifications-native-o2.log`) They precede
the entry association correction and the last competing test, covered
The two selections are overlapping.
The validation cycle of this step is complete; the complete async model
and the overall objective is not.

No new ASan/TSan validation, second C compiler or evidence
tickets cannot survive the context that carries their entry.
The dedicated runner keeps its poll loop for its own expectations; this lot
eliminates the permanent re-entry of expectations on cooperative workers.
The public scheduler, Select, mutex guards and general forms of
catches/results remain separate from the overall objective.

The next API deviation is materialized in
`validation/open-public-handle.crust` : two different async functions make
Int and transmit their handls to the same auxiliary who receives
`runtime::Handle<Int>`. Both check/compile entries currently refuse
`type runtime non pris en charge : Handle`
(`validation/open-public-handle.log`) The draft 04 rule imposes this type of
public; historical signatures `Execution<fonction>` I'm not enough.
