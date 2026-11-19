"""RT8 runtime boundary, independently of the pending native-block lowering.

The expected lifecycle is specified here rather than read from generated code.
These C probes do not establish capture checking by the Crust compiler.
"""
import unittest

from async_runtime import (TASK_RUNTIME, TASK_THREAD_RUNTIME,
                           TASK_ASYNC_THREAD_RUNTIME, TASK_POOL_RUNTIME)
import test_async_runtime as runtime_tests


SYSTEM_BOUNDARY = r'''
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
static int fail_native, native_calls, requested_detached;
static int scheduler_calls;
static int observed_create(pthread_t *thread, const pthread_attr_t *attr,
                           void *(*run)(void *), void *data) {
    native_calls++;
    int state = PTHREAD_CREATE_JOINABLE;
    if (attr) assert(pthread_attr_getdetachstate(attr, &state) == 0);
    requested_detached = state == PTHREAD_CREATE_DETACHED;
    return fail_native ? EAGAIN : pthread_create(thread, attr, run, data);
}
#define pthread_create observed_create
static int reject_scheduler(pthread_t *thread, int detached,
                             void *(*run)(void *), void *data) {
    (void)thread; (void)detached; (void)run; (void)data;
    scheduler_calls++;
    return EAGAIN;
}
'''

LIFECYCLE = r'''
typedef struct {
    CrustTask task;
    CrustTaskSlot slot;
    pthread_t caller, worker;
    _Atomic int entered, proceed;
    int *borrowed;
    int owned;
} Frame;
typedef struct { int value; int *borrowed; } Payload;
static char events[16];
static int event_count, released;
static void event(char c) { events[event_count++] = c; }
static CrustTaskStep run(CrustTask *task) {
    Frame *f = (Frame *)task;
    assert(task_slot_address(f->slot) == f);
    assert(atomic_load(&task->state) == TASK_RUNNING);
    f->worker = pthread_self();
    assert(!pthread_equal(f->worker, f->caller));
    event('r');
    atomic_store(&f->entered, 1);
    while (!atomic_load(&f->proceed)) sched_yield();
    *f->borrowed = 20;
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) {
    Frame *f = (Frame *)task;
    assert(atomic_load(&task->state) == TASK_CONSUMED);
    assert(task_slot_address(f->slot) == f && f->owned == 22);
    assert(!released);
    event('t');
    *(Payload *)out = (Payload){*f->borrowed + f->owned, f->borrowed};
}
static void release(CrustTask *task) {
    Frame *f = (Frame *)task;
    assert(task_slot_address(f->slot) == f && f->owned == 22);
    assert(atomic_load(&task->state) == TASK_CONSUMED);
    event('d');
    f->owned = 0;
    released++;
    assert(task_pool_release(f->slot));
}
static const CrustTaskOps ops = {run, take, release};
int main(void) {
    Frame storage[1];
    _Atomic size_t generations[1];
    CrustTaskPool pool;
    task_pool_init(&pool, storage, sizeof(Frame), 1, generations);
    CrustTaskSlot slot = task_pool_acquire(&pool);
    Frame *f = task_slot_address(slot);
    assert(f == storage);
    int target = 10;
    *f = (Frame){.slot = slot, .caller = pthread_self(), .borrowed = &target, .owned = 22};
    atomic_init(&f->entered, 0);
    atomic_init(&f->proceed, 0);
    task_init(&f->task, &ops);
    fail_native = FAIL_NATIVE;
    Payload payload = {0};
    CrustJoinResult result = {0};
    START_AND_WAIT
    event('w');
    printf("%s %d %d %d %d %d %d\n", events, result.status, payload.value,
           target, released, native_calls, requested_detached);
    assert(scheduler_calls == 0);
    if (!fail_native) assert(payload.borrowed == &target);
    assert(task_pool_is_empty(&pool));
    assert(task_slot_address(slot) == NULL);
    CrustTaskSlot next = task_pool_acquire(&pool);
    assert(task_slot_address(next) == f && next.generation != slot.generation);
    assert(!task_pool_release(slot));
    assert(task_pool_release(next));
    return 0;
}
'''

SYNC_WAIT = r'''
    CrustExecution execution;
    int status = task_native_start(&execution, &f->task);
    assert(status == (fail_native ? EAGAIN : 0));
    if (!fail_native) {
        while (!atomic_load(&f->entered)) sched_yield();
        assert(strcmp(events, "r") == 0 && released == 0);
        CrustExecution duplicate;
        assert(task_native_start(&duplicate, &f->task) == EINVAL);
        assert(native_calls == 1);
        assert(!task_pool_acquire(&pool).pool);
        atomic_store(&f->proceed, 1);
    } else {
        assert(released == 1 && execution.task == NULL);
    }
    result = task_join_into(&execution, &payload);
    assert(!task_thread_join(&execution, &payload));
'''

ASYNC_WAIT = r'''
    CrustAsyncExecution execution;
    task_native_async_start(&execution, &f->task);
    if (!fail_native) {
        while (!atomic_load(&f->entered)) sched_yield();
        assert(strcmp(events, "r") == 0 && released == 0);
        assert(!task_async_take_into(&execution, &result, &payload));
        assert(!task_pool_acquire(&pool).pool);
        atomic_store(&f->proceed, 1);
    } else {
        assert(released == 1 && execution.task == NULL);
    }
    while (!task_async_take_into(&execution, &result, &payload)) sched_yield();
    assert(!task_async_ready(&execution));
'''


class NativeThreadRuntimeTests(unittest.TestCase):
    run_c_oracle = runtime_tests.AsyncRuntimeTests.run_c_oracle

    @staticmethod
    def runtime(poison_scheduler=False):
        thread = TASK_THREAD_RUNTIME
        if poison_scheduler:
            # Model an installed scheduler that rejects both scheduled paths.
            # Only its callbacks change; the native system primitive stays real.
            thread = thread.replace('.launch = task_pthread_launch,', '.launch = reject_scheduler,')
            thread = thread.replace('.launch_blocking = task_pthread_launch',
                                    '.launch_blocking = reject_scheduler')
        return (TASK_RUNTIME + SYSTEM_BOUNDARY + thread + TASK_ASYNC_THREAD_RUNTIME
                + TASK_POOL_RUNTIME)

    def lifecycle(self, asynchronous, failed, poison=False):
        harness = LIFECYCLE.replace('FAIL_NATIVE', str(int(failed))).replace(
            'START_AND_WAIT', ASYNC_WAIT if asynchronous else SYNC_WAIT)
        return self.run_c_oracle(self.runtime(poison) + harness)

    @staticmethod
    def expected(asynchronous, failed):
        # Successful wait: body, extraction, destruction, wait returns.
        # Failed launch: no body/extraction, destruction before wait returns.
        return (f'dw 5 0 10 1 1 {int(asynchronous)}\n' if failed
                else f'rtdw 0 42 20 1 1 {int(asynchronous)}\n')

    def test_native_waits_publish_result_cleanup_and_slot_reuse(self):
        for asynchronous in (False, True):
            for failed in (False, True):
                with self.subTest(asynchronous=asynchronous, failed=failed):
                    self.assertEqual(self.lifecycle(asynchronous, failed).stdout,
                                     self.expected(asynchronous, failed))

    def test_native_launch_bypasses_both_scheduler_callbacks(self):
        for asynchronous in (False, True):
            with self.subTest(asynchronous=asynchronous):
                self.assertEqual(self.lifecycle(asynchronous, False, poison=True).stdout,
                                 self.expected(asynchronous, False))

    def test_detached_attribute_failures_destroy_captures_without_launch(self):
        for failure in ('init', 'detachstate'):
            with self.subTest(failure=failure):
                boundary = (r'''
static int attr_destroys;
static int observed_attr_destroy(pthread_attr_t *attr) {
    attr_destroys++;
    return pthread_attr_destroy(attr);
}
#define pthread_attr_destroy observed_attr_destroy
''' + ('\n#define pthread_attr_init(attr) EAGAIN\n' if failure == 'init' else
       '\n#define pthread_attr_setdetachstate(attr, state) EAGAIN\n'))
                harness = LIFECYCLE.replace('FAIL_NATIVE', '1').replace('START_AND_WAIT', ASYNC_WAIT)
                harness = harness.replace("event('w');", "event('w'); assert(attr_destroys == "
                                          + ('0' if failure == 'init' else '1') + ');')
                code = self.runtime().replace('#define pthread_create observed_create',
                                              boundary + '\n#define pthread_create observed_create')
                self.assertEqual(self.run_c_oracle(code + harness).stdout,
                                 'dw 5 0 10 1 0 0\n')

    def test_native_block_can_synchronously_join_another_native_thread(self):
        harness = r'''
static pthread_t caller;
static _Atomic int child_started, parent_started;
static int value, released;
static CrustExecution child_handle;
static CrustTaskStep child_run(CrustTask *task) {
    (void)task;
    assert(!pthread_equal(caller, pthread_self()));
    atomic_store(&child_started, 1);
    while (!atomic_load(&parent_started)) sched_yield();
    value = 41;
    return TASK_STEP_RETURN;
}
static void child_take(CrustTask *task, void *out) { (void)task; *(int *)out = value; }
static void child_release(CrustTask *task) { (void)task; released++; }
static CrustTaskStep parent_run(CrustTask *task) {
    (void)task;
    assert(!pthread_equal(caller, pthread_self()));
    while (!atomic_load(&child_started)) sched_yield();
    atomic_store(&parent_started, 1);
    CrustJoinResult result = task_join_result(&child_handle);
    assert(!result.status && result.value == 41 && released == 1);
    value = result.value + 1;
    return TASK_STEP_RETURN;
}
int main(void) {
    caller = pthread_self();
    CrustTask child, parent;
    CrustExecution parent_handle;
    const CrustTaskOps child_ops = {child_run, child_take, child_release};
    const CrustTaskOps parent_ops = {parent_run, child_take, child_release};
    task_init(&child, &child_ops);
    task_init(&parent, &parent_ops);
    assert(!task_native_start(&child_handle, &child));
    assert(!task_native_start(&parent_handle, &parent));
    CrustJoinResult result = task_join_result(&parent_handle);
    assert(!result.status && result.value == 42 && released == 2);
    assert(native_calls == 2 && scheduler_calls == 0);
    puts("42; two cleanups; two native launches");
}
'''
        self.assertEqual(self.run_c_oracle(self.runtime(True) + harness).stdout,
                         '42; two cleanups; two native launches\n')

    def test_native_runner_rejects_a_suspended_block(self):
        harness = r'''
#include <signal.h>
static int calls;
static CrustTaskStep illegal_yield(CrustTask *task) {
    (void)task;
    return ++calls == 1 ? TASK_STEP_YIELD : TASK_STEP_RETURN;
}
static void unreachable(CrustTask *task) { (void)task; }
static void unreachable_take(CrustTask *task, void *out) { (void)task; (void)out; }
int main(void) {
    CrustTask task;
    const CrustTaskOps ops = {illegal_yield, unreachable_take, unreachable};
    task_init(&task, &ops);
    atomic_store(&task.state, TASK_QUEUED);
    task_native_run(&task);
    return 0;
}
'''
        # The ABI rejects an impossible generated block. The frontend must also
        # reject yield statically; this test makes no claim about that stage.
        run = self.run_c_oracle(self.runtime() + harness, expected_error='')
        self.assertEqual(run.returncode, -6)  # SIGABRT, not a sanitizer failure.


if __name__ == '__main__':
    unittest.main()
