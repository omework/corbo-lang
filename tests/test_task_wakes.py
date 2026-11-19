"""RT2 readiness protocol: finite traces and explicitly synchronized races.

These probes exercise the internal C runtime, not a public waker API.
Task storage remains live until every poll/wake thread has returned.
"""
import itertools
import unittest

from async_runtime import TASK_RUNTIME, TASK_THREAD_RUNTIME, TASK_ASYNC_THREAD_RUNTIME
import test_async_runtime


class TaskWakeTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_readiness_model(self):
        # Abstract model: an execution permission is either present or absent.
        # Notifications add permission, never a count. A poll spends it; a
        # cooperative yield returns it. The model has no lock/CAS/C pointers.
        traces = []
        states = {'new': 'TASK_INACTIVE', 'waiting': 'TASK_SUSPENDED',
                  'done': 'TASK_COMPLETE', 'gone': 'TASK_CONSUMED'}
        for actions in itertools.product('wpyritd', repeat=4):
            phase, permit, calls, releases = 'new', True, 0, 0
            for index, action in enumerate(actions):
                answer = -1
                if action == 'w':
                    answer = int(phase not in ('done', 'gone'))
                    if answer: permit = True
                elif action in 'pyri':
                    if phase in ('new', 'waiting') and permit:
                        calls += 1
                        permit = action in 'yi'
                        phase = 'done' if action == 'r' else 'waiting'
                else:
                    answer = int(phase == ('done' if action == 't' else 'new'))
                    if answer:
                        phase = 'gone'
                        releases += 1
                traces.append(f"{{{int(index == 0)},'{action}',{states[phase]},"
                              f"{calls},{releases},{answer}}}")
        code = TASK_RUNTIME + r'''
#include <assert.h>
typedef struct { CrustTask task; int calls, releases; char action; } State;
static CrustTaskStep resume(CrustTask *task) {
    State *s = (State *)task;
    ++s->calls;
    if (s->action == 'i') { assert(task_wake(task)); assert(task_wake(task)); }
    if (s->action == 'r') return TASK_STEP_RETURN;
    return s->action == 'y' ? TASK_STEP_YIELD : TASK_STEP_PENDING;
}
static void take(CrustTask *task, void *out) { *(int *)out = ((State *)task)->calls; }
static void release(CrustTask *task) { ++((State *)task)->releases; }
static const CrustTaskOps ops = {resume, take, release};
struct Row { int init; char action; CrustTaskState phase; int calls, releases, answer; };
static const struct Row rows[] = {ROWS};
int main(void) {
    State s = {0};
    for (unsigned i = 0; i < sizeof(rows)/sizeof(*rows); ++i) {
        const struct Row *r = &rows[i];
        if (r->init) { s.calls = s.releases = 0; task_init(&s.task, &ops); }
        s.action = r->action;
        int answer = -1, out = -1;
        switch (r->action) {
        case 'w': answer = task_wake(&s.task); break;
        case 't': answer = task_take(&s.task, &out); if (answer) assert(out == s.calls); break;
        case 'd': answer = task_drop_inactive(&s.task); break;
        default: assert(task_poll(&s.task) == r->phase); break;
        }
        assert(atomic_load(&s.task.state) == r->phase);
        assert(s.calls == r->calls && s.releases == r->releases && answer == r->answer);
    }
    return 0;
}
'''
        self.assertEqual(len(traces), 9604)
        self.run_c_oracle(code.replace('ROWS', ',\n'.join(traces)))

    def test_wake_during_poll_and_migration(self):
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + r'''
#include <assert.h>
typedef struct {
    CrustTask task;
    _Atomic int entered, proceed, first_done, second_done;
    int calls, released;
    pthread_t first_thread;
} State;
static CrustTaskStep resume(CrustTask *task) {
    State *s = (State *)task;
    ++s->calls;
    if (s->calls == 1) {
        s->first_thread = pthread_self();
        atomic_store(&s->entered, 1);
        while (!atomic_load(&s->proceed)) sched_yield();
        return TASK_STEP_PENDING;
    }
    assert(s->calls == 2);
    assert(!pthread_equal(s->first_thread, pthread_self()));
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) { *(int *)out = ((State *)task)->calls; }
static void release(CrustTask *task) { ++((State *)task)->released; }
static const CrustTaskOps ops = {resume, take, release};
static void *first(void *p) {
    State *s = p;
    assert(task_poll(&s->task) == TASK_SUSPENDED);
    atomic_store(&s->first_done, 1);
    /* Keep this thread alive so its identity cannot be reused. */
    while (!atomic_load(&s->second_done)) sched_yield();
    return NULL;
}
static void *contender(void *p) {
    State *s = p;
    for (int i = 0; i < 100; ++i) {
        assert(task_wake(&s->task));
        assert(task_poll(&s->task) == TASK_RUNNING);
    }
    return NULL;
}
int main(void) {
    for (int round = 0; round < 20; ++round) {
        State s = {0};
        task_init(&s.task, &ops);
        pthread_t initial, others[4];
        assert(!pthread_create(&initial, NULL, first, &s));
        while (!atomic_load(&s.entered)) sched_yield();
        for (int i = 0; i < 4; ++i) assert(!pthread_create(&others[i], NULL, contender, &s));
        for (int i = 0; i < 4; ++i) assert(!pthread_join(others[i], NULL));
        atomic_store(&s.proceed, 1);
        while (!atomic_load(&s.first_done)) sched_yield();
        assert(s.calls == 1);
        assert(task_poll(&s.task) == TASK_COMPLETE);
        assert(!task_wake(&s.task));
        atomic_store(&s.second_done, 1);
        assert(!pthread_join(initial, NULL));
        int out = -1;
        assert(task_take(&s.task, &out) && out == 2 && s.released == 1);
        assert(!task_wake(&s.task));
    }
    return 0;
}
''')

    def test_launched_pending_task_needs_notification(self):
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + TASK_ASYNC_THREAD_RUNTIME + r'''
#include <assert.h>
typedef struct { CrustTask task; _Atomic int event; int calls, released; } State;
static CrustTaskStep resume(CrustTask *task) {
    State *s = (State *)task;
    ++s->calls;
    if (s->calls == 1) return TASK_STEP_PENDING;
    assert(s->calls == 2 && atomic_load(&s->event));
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) { *(int *)out = ((State *)task)->calls; }
static void release(CrustTask *task) { ++((State *)task)->released; }
static const CrustTaskOps ops = {resume, take, release};
int main(void) {
    for (int detached = 0; detached < 2; ++detached) {
        State s = {0};
        CrustExecution sync;
        CrustAsyncExecution async;
        task_init(&s.task, &ops);
        if (detached) task_async_start(&async, &s.task);
        else assert(!task_thread_start(&sync, &s.task));
        while (atomic_load(&s.task.state) != TASK_SUSPENDED) sched_yield();
        /* A non-ready poll must not call user code. */
        for (int i = 0; i < 1000; ++i) assert(task_poll(&s.task) == TASK_SUSPENDED);
        atomic_store(&s.event, 1);
        assert(task_wake(&s.task));
        int out = -1;
        if (detached) {
            while (!task_async_ready(&async)) sched_yield();
            assert(task_async_finish(&async, &out) == 0);
        } else assert(task_thread_join(&sync, &out));
        assert(out == 2 && s.released == 1);
    }
    return 0;
}
''')

    def test_notification_races_pending_publication(self):
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + r'''
#include <assert.h>
typedef struct {
    CrustTask task;
    _Atomic int entered, go;
    int calls, released, payload;
} State;
static CrustTaskStep resume(CrustTask *task) {
    State *s = (State *)task;
    if (++s->calls == 1) {
        atomic_store(&s->entered, 1);
        while (!atomic_load(&s->go)) sched_yield();
        return TASK_STEP_PENDING;
    }
    assert(s->calls == 2 && s->payload == 123);
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) { *(int *)out = ((State *)task)->calls; }
static void release(CrustTask *task) { ++((State *)task)->released; }
static const CrustTaskOps ops = {resume, take, release};
static void *poll_once(void *p) {
    State *s = p;
    assert(task_poll(&s->task) == TASK_SUSPENDED);
    return NULL;
}
static void *notify_once(void *p) {
    State *s = p;
    while (!atomic_load(&s->go)) sched_yield();
    s->payload = 123;
    assert(task_wake(&s->task));
    return NULL;
}
int main(void) {
    for (int i = 0; i < 200; ++i) {
        State s = {0};
        task_init(&s.task, &ops);
        pthread_t poller, notifier;
        assert(!pthread_create(&poller, NULL, poll_once, &s));
        while (!atomic_load(&s.entered)) sched_yield();
        assert(!pthread_create(&notifier, NULL, notify_once, &s));
        atomic_store(&s.go, 1);
        assert(!pthread_join(poller, NULL));
        assert(!pthread_join(notifier, NULL));
        assert(task_poll(&s.task) == TASK_COMPLETE);
        assert(task_drop_complete(&s.task) && s.released == 1);
        assert(!task_drop_complete(&s.task));
        assert(!task_wake(&s.task));
    }
    return 0;
}
''')


if __name__ == '__main__': unittest.main()
