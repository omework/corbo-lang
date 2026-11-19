"""RT2: generated await chains sleep until their launched child completes."""
import unittest

from crust import compile_source
from async_runtime import TASK_RUNTIME, TASK_THREAD_RUNTIME
import test_async_runtime


class AwaitNotificationTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_notification_races_parent_poll_on_two_workers(self):
        code = TASK_RUNTIME + TASK_THREAD_RUNTIME + r'''
#include <assert.h>
typedef struct { CrustTask task; int releases; } State;
static State parent, child;
static _Atomic int subscribed;
static int wait_inside_poll;
static CrustTaskStep child_resume(CrustTask *task) {
    (void)task;
    while (!atomic_load_explicit(&subscribed, memory_order_acquire)) sched_yield();
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) { (void)task; *(int *)out = 42; }
static void release(CrustTask *task) { ++((State *)task)->releases; }
static CrustTaskStep parent_resume(CrustTask *task) {
    CrustTaskStep step = task_subscribe(&child.task, task);
    atomic_store_explicit(&subscribed, 1, memory_order_release);
    if (wait_inside_poll)
        while (!atomic_load_explicit(&child.task.worker_done, memory_order_acquire)) sched_yield();
    if (!atomic_load_explicit(&child.task.worker_done, memory_order_acquire)) return step;
    int value = 0;
    assert(task_take(&child.task, &value) && value == 42);
    return TASK_STEP_RETURN;
}
static const CrustTaskOps parent_ops = {parent_resume, take, release};
static const CrustTaskOps child_ops = {child_resume, take, release};
int main(void) {
    CrustReadyQueue queue;
    CrustQueueEntry entries[2];
    assert(!task_queue_init(&queue));
    task_queue_entry_init(&entries[0]); task_queue_entry_init(&entries[1]);
    pthread_t workers[2];
    for (int i = 0; i < 2; ++i) assert(!pthread_create(&workers[i], NULL, task_queue_worker, &queue));
    CrustWakeTicket old = {0};
    for (int round = 0; round < 200; ++round) {
        parent = (State){0}; child = (State){0};
        atomic_store(&subscribed, 0);
        wait_inside_poll = round % 2;
        task_init(&parent.task, &parent_ops); task_init(&child.task, &child_ops);
        CrustWakeTicket parent_ticket, child_ticket;
        /* Launch child first: registration precedes every parent's subscription. */
        assert(!task_queue_submit(&queue, &entries[1], &child.task, &child_ticket));
        assert(!task_queue_submit(&queue, &entries[0], &parent.task, &parent_ticket));
        assert(!task_queue_wake(old));
        while (!atomic_load_explicit(&parent.task.worker_done, memory_order_acquire)) sched_yield();
        int value = 0;
        assert(task_take(&parent.task, &value) && value == 42);
        assert(parent.releases == 1 && child.releases == 1);
        old = parent_ticket;
    }
    assert(!task_queue_close(&queue));
    for (int i = 0; i < 2; ++i) assert(!pthread_join(workers[i], NULL));
    task_queue_entry_destroy(&entries[0]); task_queue_entry_destroy(&entries[1]);
    task_queue_destroy(&queue);
    return 0;
}
'''
        self.run_c_oracle(code)

    def test_completion_before_during_and_after_subscription(self):
        # Force the publication gap, rather than relying on thread timing.
        runtime = TASK_THREAD_RUNTIME.replace(
            '/* Completion notification finished. */',
            'publication_gap(task);')
        self.assertEqual(TASK_THREAD_RUNTIME.count('/* Completion notification finished. */'), 2)
        prefix = 'static void publication_gap(void *task);\n'
        body = r'''
#include <assert.h>
typedef struct { CrustTask task; int polls, releases; } State;
static State parent, child;
static CrustReadyQueue queue;
static int mode, external, fired, gap_polled;
static void finish_child(void);
static CrustTaskStep resume_child(CrustTask *task) {
    ++((State *)task)->polls;
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) { (void)task; *(int *)out = 42; }
static void release(CrustTask *task) { ++((State *)task)->releases; }
static CrustTaskStep resume_parent(CrustTask *task) {
    ++((State *)task)->polls;
    CrustTaskStep step = task_subscribe(&child.task, task);
    if (mode == 1 && !fired++) finish_child();
    if (!atomic_load_explicit(&child.task.worker_done, memory_order_acquire)) return step;
    int value = 0;
    assert(task_take(&child.task, &value) && value == 42);
    return TASK_STEP_RETURN;
}
static const CrustTaskOps parent_ops = {resume_parent, take, release};
static const CrustTaskOps child_ops = {resume_child, take, release};
static void publication_gap(void *task) {
    if (task == &child.task && mode == 3) {
        assert(!atomic_load(&child.task.worker_done));
        assert(task_queue_run_one(&queue, 0));
        ++gap_polled;
        assert(parent.polls == 2 && !atomic_load(&parent.task.worker_done));
    }
}
static void finish_child(void) {
    if (external) {
        task_claim_queued(&child.task);
        assert(task_resume_claimed(&child.task) == TASK_COMPLETE);
        task_external_complete(&child.task);
    } else assert(task_queue_run_one(&queue, 0));
}
int main(void) {
    for (external = 0; external < 2; ++external) {
        for (mode = 0; mode < 4; ++mode) {
            for (int repeat = 0; repeat < 25; ++repeat) {
                CrustQueueEntry entries[2];
                CrustWakeTicket tickets[2];
                parent = (State){0}; child = (State){0}; fired = gap_polled = 0;
                assert(!task_queue_init(&queue));
                task_queue_entry_init(&entries[0]); task_queue_entry_init(&entries[1]);
                task_init(&parent.task, &parent_ops); task_init(&child.task, &child_ops);
                if (mode != 0)
                    assert(!task_queue_submit(&queue, &entries[0], &parent.task, &tickets[0]));
                if (external) {
                    child.task.queue_entry = &entries[1];
                    atomic_store(&child.task.state, TASK_QUEUED);
                    assert(!task_external_register(&child.task));
                } else assert(!task_queue_submit(&queue, &entries[1], &child.task, &tickets[1]));
                if (mode == 0) {
                    finish_child();
                    assert(!task_queue_submit(&queue, &entries[0], &parent.task, &tickets[0]));
                }
                assert(task_queue_run_one(&queue, 0));
                if (mode >= 2) {
                    assert(parent.polls == 1 && !atomic_load(&parent.task.worker_done));
                    if (external) assert(!task_queue_run_one(&queue, 0));
                    else assert(queue.head == &entries[1] && queue.head->next == NULL);
                    finish_child();
                    assert(task_queue_run_one(&queue, 0));
                }
                assert(atomic_load(&parent.task.worker_done));
                /* Expected from the imposed event order, independent of ready flags. */
                assert(parent.polls == (mode < 2 ? 1 : mode == 2 ? 2 : 3));
                assert(gap_polled == (mode == 3));
                assert(child.polls == 1 && child.releases == 1);
                int value = 0;
                assert(task_take(&parent.task, &value) && value == 42 && parent.releases == 1);
                assert(!task_queue_run_one(&queue, 0));
                assert(!task_queue_close(&queue));
                task_queue_entry_destroy(&entries[0]); task_queue_entry_destroy(&entries[1]);
                task_queue_destroy(&queue);
            }
        }
    }
    return 0;
}
'''
        self.run_c_oracle(prefix + TASK_RUNTIME + runtime + body)

    def test_nested_generated_await_sleeps_and_reuses_slots(self):
        source = '''async fn leaf(v:&Int)->Int{return *v;}
            async fn middle(v:&Int)->Int{
                let h=runtime::spawn(->leaf(v));
                match h.await {Ok(n)=>{return n;},Err(_)=>{return 99;}}
            }
            async fn bridge(v:&Int)->Int{return middle(v).await;}
            async fn root()->Int{
                let values=[7,9];let view=&values[1];
                return bridge(view).await;
            }
            fn main(){let h=runtime::spawn(->root());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        code = compile_source(source)
        for name in ('root', 'bridge', 'middle', 'leaf'):
            anchor = f'static CrustTaskStep crust_async_{name}_resume(CrustTask *task) {{'
            self.assertEqual(code.count(anchor), 1)
            hook = f'\n    ++polls_{name};'
            if name == 'leaf':
                hook += '\n    if (!allow_leaf) return TASK_STEP_PENDING;'
            code = code.replace(anchor, anchor + hook)
        anchor = 'static int task_default_submit(CrustTask *task) {'
        self.assertEqual(code.count(anchor), 1)
        code = code.replace(anchor, 'static int test_submit(CrustTask *task);\n' +
                            anchor + '\n    return test_submit(task);')
        prefix = '''#include <assert.h>
static int polls_root, polls_bridge, polls_middle, polls_leaf, allow_leaf;
#define main original_main
'''
        suffix = r'''
#undef main
static CrustReadyQueue queue;
static CrustWakeTicket leaf_ticket;
static int test_submit(CrustTask *task) {
    return task_queue_submit(&queue, task->queue_entry, task, &leaf_ticket);
}
int main(void) {
    crust_task_context_init();
    assert(!task_queue_init(&queue));
    CrustWakeTicket previous = {0};
    for (int round = 0; round < 20; ++round) {
        polls_root = polls_bridge = polls_middle = polls_leaf = allow_leaf = 0;
        CrustTask *root = crust_async_root_create();
        CrustWakeTicket root_ticket;
        assert(!task_queue_submit(&queue, root->queue_entry, root, &root_ticket));
        assert(task_queue_run_one(&queue, 0)); /* Root subscribes through two direct children. */
        assert(task_queue_run_one(&queue, 0)); /* Leaf waits for external event. */
        for (int i = 0; i < 100; ++i) assert(!task_queue_run_one(&queue, 0));
        assert(polls_root == 1 && polls_bridge == 1 && polls_middle == 1 && polls_leaf == 1);
        assert(!task_queue_wake(previous));
        assert(!task_queue_run_one(&queue, 0));
        allow_leaf = 1;
        assert(task_queue_wake(leaf_ticket));
        assert(task_queue_run_one(&queue, 0)); /* Leaf completes, wakes the root. */
        assert(task_queue_run_one(&queue, 0)); /* Entire await chain returns. */
        assert(!task_queue_run_one(&queue, 0));
        assert(polls_root == 2 && polls_bridge == 2 && polls_middle == 2 && polls_leaf == 2);
        assert(atomic_load(&root->worker_done));
        int result = 0;
        assert(task_take(root, &result) && result == 9);
        assert(!task_queue_wake(leaf_ticket));
        previous = root_ticket;
    }
    assert(!task_queue_close(&queue));
    task_queue_destroy(&queue);
    crust_task_context_close();
    return 0;
}
'''
        self.run_c_oracle(prefix + code + suffix)


if __name__ == '__main__':
    unittest.main()
