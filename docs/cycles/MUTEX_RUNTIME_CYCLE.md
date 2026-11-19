[Français](MUTEX_RUNTIME_CYCLE-fr.md)

<a id="mutex-et-gardes--mécanisme-interne-du-runtime"></a>

# Mutex and guards: internal mechanism of running

<a id="périmètre"></a>

## Perimeter

This batch implements the internal primitives necessary for MT9 and cleaning
SL1. Public manufacturers remain expressly deferred.
type or name of public method is not added to the language and no normative rules
is not modified. This lot is not a complete source implementation of the
mutex: typing of guards, transfer deduction and verification of borrowings
derivatives remain to be connected.

<a id="mécanismes-implémentés"></a>

## Mechanisms implemented

`mutex_runtime.py` provides an integrated C fragment after the task queue in
`TASK_THREAD_RUNTIME`. Storage of mutex, guards and expectations is provided by
the caller; these primitives do not allocate on the heap. The value pointer
and destruction callback represent storage and cleaning that the
compiler will have to provide. This callback does not add any user destroyer.

The synchronous mutex uses pthread_mutex. Its guard memorizes the purchaser thread;
an internal drop from another thread makes EPERM without releasing the lock.
A second drop makes EINVAL. The destruction of a still locked mutex fails.
Runtime cannot establish a static ban on crossing a suspension.

The async mutex keeps its internal pthread lock only during the setting
The logical lock can therefore remain acquired during a metadata day.
then be released from another thread. A wait is a node
Intrusive in a stable address state. FIFO file and first booking
waiting prevent a new arrival from taking the lock; it is a
choice of internal implementation, not a new public guarantee.

Release locks it to the next time you wait and wakes up your ticket
The alarm is emitted after release of the internal lock, with a
copy of the generation ticket; it does not retain any frame or node pointer
The tickets follow the conditions of the duration of the
existing scheduler. A task without ticket uses Yield fold; tasks
recorded make Pending while waiting.

Cleaning a waiting tie removes its node, or transmits a reservation already
The following is received. Once custody is acquired, the waiting is disarmed: its
destruction does not release custody and no longer access mutex.
be destroyed separately by the cleaning of the state.
calls for the cleaning of its value before destroying its synchronization.

<a id="résultats-exécutés"></a>

## Implemented

- O0 : 4 methods, 6 native C probes, 2,101 s, code 0 ;
  `validation/mutex-runtime-final-o0.log`.
- O2: 26 mutex methods, ready line, wake-up, Select and native border,
  13,026 s, code 0 ; `validation/mutex-runtime-regression-o2.log`.
- Both passages use Clang C11, pthread and UBSan without recovery.
  Regressions include frames produced by the compiler.

The assertions test: exclusive access and visibility after sync lock,
refusal of drop sync from the wrong thread, keep async kept during
yield and released by another thread, waiting Pending without queue
immediate, wake up after release, visibility of scriptures, transmission of a
abandoned reservation, no flight of reservation, destruction of value
once and refusal to destroy during occupation.

Three probes use the real internal Select mechanism.
The loser has a queued wait, a reservation,
or a custody acquired. The resource remains retained after the return;
the drop of Select then cleans the corresponding state. The frame callbacks
of these probes are written in the test, not generated from a mutex syntax.

The first passage consisted of two compilation errors of bench C: one
constant unused callbacks was treated as an error by -Werrar.
The probes now refer explicitly to it.
`validation/mutex-runtime-first-o0.log`.

<a id="limites-et-travail-restant"></a>

## Limitations and remaining work

Life, non-copying of guards, termination of borrowing
before unlock and suspension ban with a sync guard are not
The compiler will have to impose these functions when the
The exclusive destruction of a mutex implies the connection of public types.
no competing calls begin or remain pending; entries of
The probes must survive the competing notifications.
internal C functions are not a safe border for
Arbitrary C.

No Crust program with mutex manufacturer is announced accepted or refused.
No new independent model, transfer campaign or audit
adversarial; models already present in regressions were replayed.
UBSan does not detect all races: no ThreadSanitizer results are
The extensive audit with another officer remains deferred.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_mutex_runtime -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_mutex_runtime test_ready_queue test_task_wakes test_select_runtime test_native_thread_runtime -v
```

Snapshot : `/tmp/crust-before-mutex-runtime/`. Archived differences:
`validation/mutex-runtime-async_runtime.py.patch` and
`validation/mutex-runtime-new-module.patch`.
