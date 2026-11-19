"""RT2 FIFO scheduling, independent wake tickets, frame retirement and reuse."""
import collections
import random
import unittest

from async_runtime import TASK_RUNTIME, TASK_THREAD_RUNTIME
from crust import compile_source
import test_async_runtime


class ReadyQueueTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_default_workers_reused_and_partial_launch_failure_cleaned(self):
        source = '''async fn work(n:-> Int)->Int{yield;return *n;}
            fn main(){let mut memory=pool<Int>(1);let mut i=0;
                while i<3 {let n=new(memory) Int(i+10);
                    let h=runtime::spawn(->work(->n));
                    match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}
                    i=i+1;}}
        '''
        prefix = r'''
#include <pthread.h>
#include <errno.h>
static int starts, joins, conditions;
static int observed_create(pthread_t *thread, const pthread_attr_t *attr,
                           void *(*run)(void *), void *data) {
    ++starts;
    if (FAIL_SECOND && starts == 2) return EAGAIN;
    return pthread_create(thread, attr, run, data);
}
static int observed_join(pthread_t thread, void **out) {
    ++joins;
    return pthread_join(thread, out);
}
static int observed_cond_init(pthread_cond_t *condition, const pthread_condattr_t *attr) {
    if (FAIL_CONDITION && ++conditions == 1) return EAGAIN;
    return pthread_cond_init(condition, attr);
}
#define pthread_create observed_create
#define pthread_join observed_join
#define pthread_cond_init observed_cond_init
#define main original_main
'''
        suffix = r'''
#undef main
#include <assert.h>
int main(void) {
    int status = original_main();
    assert(starts == EXPECTED_STARTS && joins == EXPECTED_JOINS);
    return status;
}
'''
        for fail, condition in ((False, False), (True, False), (False, True)):
            with self.subTest(fail_second=fail, fail_condition=condition):
                code = prefix.replace('FAIL_SECOND', str(int(fail))).replace(
                    'FAIL_CONDITION', str(int(condition))) + compile_source(source)
                code += suffix.replace('EXPECTED_STARTS', str(4 if fail else 2)).replace(
                    'EXPECTED_JOINS', str(3 if fail else 2))
                run = self.run_c_oracle(code)
                self.assertEqual(run.stdout, ('99' if fail or condition else '10') + '\n11\n12\n')
                self.assertEqual(run.stderr.count('destroy n='), 3)

    def test_generated_frames_run_on_shared_workers(self):
        source = '''#(directive, async_pool_sizes={count:2})
            async fn count(n:Int)->Int {
                let mut memory=pool<Int>(1);
                let mut value=new(memory) Int(n);
                yield; value.set(*value+1); return *value;
            }
            fn main(){let a=count(10);let b=count(20);
                let x=runtime::spawn(->a);let y=runtime::spawn(->b);
                match x.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}
                match y.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}}
        '''
        code = '#define main original_main\n' + compile_source(source) + r'''
#undef main
#include <assert.h>
int main(void) {
    crust_task_context_init();
    CrustReadyQueue queue;
    CrustQueueEntry entries[2];
    CrustWakeTicket tickets[2];
    assert(!task_queue_init(&queue));
    for (int i = 0; i < 2; ++i) task_queue_entry_init(&entries[i]);
    pthread_t workers[2];
    for (int i = 0; i < 2; ++i) assert(!pthread_create(&workers[i], NULL, task_queue_worker, &queue));
    for (int round = 0; round < 3; ++round) {
        CrustTask *tasks[2];
        for (int i = 0; i < 2; ++i) {
            tasks[i] = crust_async_count_create(round * 10 + i);
            assert(!task_queue_submit(&queue, &entries[i], tasks[i], &tickets[i]));
        }
        for (int i = 0; i < 2; ++i) {
            while (!atomic_load_explicit(&tasks[i]->worker_done, memory_order_acquire)) sched_yield();
            int value = -1;
            assert(task_take(tasks[i], &value));
            assert(value == round * 10 + i + 1);
            assert(!task_queue_wake(tickets[i]));
            printf("%d\n", value);
        }
    }
    assert(!task_queue_close(&queue));
    for (int i = 0; i < 2; ++i) assert(!pthread_join(workers[i], NULL));
    for (int i = 0; i < 2; ++i) task_queue_entry_destroy(&entries[i]);
    task_queue_destroy(&queue);
    crust_task_context_close();
    return 0;
}
'''
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '1\n2\n11\n12\n21\n22\n')
        self.assertEqual(run.stderr.count('destroy value='), 6)

    def test_generated_local_borrow_survives_forced_migration(self):
        source = '''async fn child(v:&Int)->Int{yield;return *v;}
            async fn migrate()->Int{let values=[7,9];let view=&values[1];
                yield;let result=child(view).await;return result;}
            fn main(){let h=runtime::spawn(->migrate());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        code = compile_source(source)
        anchor = 'static CrustTaskStep crust_async_migrate_resume(CrustTask *task) {'
        self.assertEqual(code.count(anchor), 1)
        code = code.replace(anchor, anchor + '\n    observe_poll(task);')
        prefix = r'''
#include <assert.h>
#include <pthread.h>
static void *expected_task;
static pthread_t first_worker;
static int polls;
static void observe_poll(void *task) {
    assert(task == expected_task);
    if (polls++) assert(!pthread_equal(first_worker, pthread_self()));
    else first_worker = pthread_self();
}
#define main original_main
'''
        suffix = r'''
#undef main
static _Atomic int first_done, second_done;
static void *first_poll(void *p) {
    assert(task_queue_run_one(p, 0));
    atomic_store(&first_done, 1);
    while (!atomic_load(&second_done)) sched_yield();
    return NULL;
}
int main(void) {
    crust_task_context_init();
    CrustReadyQueue queue;
    CrustQueueEntry entry;
    CrustWakeTicket ticket;
    assert(!task_queue_init(&queue));
    task_queue_entry_init(&entry);
    CrustTask *task = crust_async_migrate_create();
    expected_task = task;
    assert(!task_queue_submit(&queue, &entry, task, &ticket));
    pthread_t worker;
    assert(!pthread_create(&worker, NULL, first_poll, &queue));
    while (!atomic_load(&first_done)) sched_yield();
    assert(polls == 1 && !atomic_load(&task->worker_done));
    while (!atomic_load(&task->worker_done)) assert(task_queue_run_one(&queue, 0));
    int value = 0;
    assert(task_take(task, &value) && value == 9 && polls == 3);
    atomic_store(&second_done, 1);
    assert(!pthread_join(worker, NULL));
    assert(!task_queue_close(&queue));
    task_queue_entry_destroy(&entry);
    task_queue_destroy(&queue);
    crust_task_context_close();
    return 0;
}
'''
        self.run_c_oracle(prefix + code + suffix)

    def test_nested_direct_await_wakes_root_and_releases_at_join(self):
        source = '''#(directive, async_pool_sizes={root:1,middle:1,leaf:1})
            async fn leaf(m:&AsyncMutex<i64>)->i64 {
                let mut guard=m.lock().await;*guard+=1;*guard
            }
            async fn middle(m:&AsyncMutex<i64>)->i64 {leaf(m).await}
            async fn root(m:&AsyncMutex<i64>, input:A<i64>)->i64 {
                let value=middle(m).await;yield;value+*input
            }
            fn main(){
                let mutex=AsyncMutex::new(10);
                let mut numbers=pool<i64>(1);let input=numbers.new(6);
                let h=runtime::spawn(root(&mutex,input));
                match h.join(){Ok(value)=>{print(value);},Err(_)=>{},}
            }'''
        code = '#define main original_main\n' + compile_source(source) + r'''
#undef main
#include <assert.h>
int main(void) {
    crust_task_context_init();
    Source storage = source_stack(16 * 1024 * 1024);
    int64_t initial = 10;
    Cell *holder = crust_make_mutex(&storage, 1, &initial, sizeof initial, "mutex");
    CrustAsyncMutex *mutex = &crust_mutex_cell(holder)->lock.async;
    CrustTask initial_locker = {0};
    CrustMutexWait wait = {0};
    CrustAsyncGuard guard = {0};
    assert(crust_async_mutex_poll(mutex, &wait, &initial_locker, &guard) == TASK_STEP_RETURN);

    Source numbers = source_pool_layout(1, sizeof(int64_t));
    int64_t six = 6;
    Cell *input = cell_new(&numbers, 0, "input");
    memcpy(input->fields, &six, sizeof six);
    CrustTask *task = crust_async_root_create(holder, input);
    CrustQueueEntry *entry = task->queue_entry;
    CrustExecution execution;
    assert(!task_thread_start(&execution, task));

    /* Holding the mutex forces Pending. Wait for the root to leave the
       ready queue so the guard's release is the only way to resume it. */
    for (;;) {
        task_queue_lock(&entry->mutex);
        int parked = !entry->scheduled;
        task_queue_unlock(&entry->mutex);
        if (parked) break;
        sched_yield();
    }
    assert(atomic_load(&task->state) == TASK_SUSPENDED);
    task_queue_lock(&mutex->gate);
    assert(mutex->head && mutex->head == mutex->tail);
    CrustWakeTicket ticket = mutex->head->wake;
    task_queue_unlock(&mutex->gate);
    assert(ticket.entry == entry && ticket.generation == entry->generation);
    assert(!crust_async_guard_drop(&guard));

    task_default_wait(task);
    assert(!task_queue_wake(ticket));
    assert(task_pool_is_empty(&crust_task_context.pool_leaf));
    assert(task_pool_is_empty(&crust_task_context.pool_middle));
    assert(!task_pool_is_empty(&crust_task_context.pool_root));
    assert(numbers.live == 1);
    int64_t result = 0;
    assert(task_thread_join(&execution, &result) && result == 17);
    assert(!task_thread_join(&execution, &result));
    assert(task_pool_is_empty(&crust_task_context.pool_root));
    assert(numbers.live == 0);

    Cell *again = cell_new(&numbers, 0, "reused");
    assert(again == input);
    cell_drop(again);
    cell_drop(holder);
    source_close(&numbers);
    source_close(&storage);
    crust_task_context_close();
    return 0;
}
'''
        run = self.run_c_oracle(code)
        self.assertEqual(run.stderr.count('destroy input='), 1)

    def test_fifo_model(self):
        rows = []
        scripts = ('YPR', 'PYR', 'YYR', 'R')
        rng = random.Random(4112026)
        for trial in range(40):
            queue = collections.deque(range(4))
            finished, steps = set(), [0] * 4
            operations = [('w', rng.randrange(4)) if rng.randrange(2) else ('p', 0)
                          for _ in range(40)]
            # Drain every unfinished branch, including those waiting for events.
            operations += [('w', i) for _ in range(4) for i in range(4)]
            for _ in range(4):
                operations += [('w', i) for i in range(4)] + [('p', 0)] * 16
            for i, (op, target) in enumerate(operations):
                result = 0
                polled = -1
                if op == 'w':
                    result = int(target not in finished)
                    if result and target not in queue: queue.append(target)
                elif queue:
                    result = 1
                    polled = queue.popleft()
                    step = scripts[polled][steps[polled]]
                    steps[polled] += 1
                    if step == 'R': finished.add(polled)
                    elif step == 'Y': queue.append(polled)
                rows.append(f"{{{int(i == 0)},{int(i == len(operations)-1)},'{op}',"
                            f"{target},{result},{polled}}}")
            self.assertEqual(finished, set(range(4)))
            self.assertEqual(steps, [3, 3, 3, 1])
        code = TASK_RUNTIME + TASK_THREAD_RUNTIME + r'''
#include <assert.h>
typedef struct { CrustTask task; int id, pc, released; } State;
static const char *scripts[] = {"YPR", "PYR", "YYR", "R"};
static int polled;
static CrustTaskStep resume(CrustTask *task) {
    State *s = (State *)task;
    polled = s->id;
    char step = scripts[s->id][s->pc++];
    assert(step);
    return step == 'Y' ? TASK_STEP_YIELD : step == 'P' ? TASK_STEP_PENDING : TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) { *(int *)out = ((State *)task)->pc; }
static void release(CrustTask *task) { ++((State *)task)->released; }
static const CrustTaskOps ops = {resume, take, release};
struct Row { int init, end; char op; int target, answer, polled; };
static const struct Row rows[] = {ROWS};
int main(void) {
    CrustReadyQueue queue;
    CrustQueueEntry entries[4];
    CrustWakeTicket tickets[4];
    State states[4];
    for (unsigned i = 0; i < sizeof(rows)/sizeof(*rows); ++i) {
        const struct Row *r = &rows[i];
        if (r->init) {
            assert(!task_queue_init(&queue));
            for (int j = 0; j < 4; ++j) {
                states[j] = (State){.id = j};
                task_init(&states[j].task, &ops);
                task_queue_entry_init(&entries[j]);
                assert(!task_queue_submit(&queue, &entries[j], &states[j].task, &tickets[j]));
            }
            assert(task_queue_close(&queue) == EBUSY);
        }
        polled = -1;
        int answer = r->op == 'w' ? task_queue_wake(tickets[r->target]) : task_queue_run_one(&queue, 0);
        assert(answer == r->answer && polled == r->polled);
        if (r->end) {
            for (int j = 0; j < 4; ++j) {
                assert(atomic_load(&states[j].task.worker_done));
                int out = -1;
                assert(task_take(&states[j].task, &out) && out == (j == 3 ? 1 : 3));
                assert(states[j].released == 1 && !task_queue_wake(tickets[j]));
                task_queue_entry_destroy(&entries[j]);
            }
            assert(!task_queue_close(&queue));
            task_queue_destroy(&queue);
        }
    }
    return 0;
}
'''
        self.run_c_oracle(code.replace('ROWS', ',\n'.join(rows)))

    def test_old_tickets_cannot_wake_reused_frame(self):
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + r'''
#include <assert.h>
typedef struct { CrustTask task; int calls, released; } State;
static CrustTaskStep resume(CrustTask *task) {
    return ++((State *)task)->calls == 1 ? TASK_STEP_PENDING : TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *out) { *(int *)out = ((State *)task)->calls; }
static void release(CrustTask *task) { ++((State *)task)->released; }
static const CrustTaskOps ops = {resume, take, release};
int main(void) {
    CrustReadyQueue queue;
    CrustQueueEntry entry, spare;
    assert(!task_queue_init(&queue));
    task_queue_entry_init(&entry);
    task_queue_entry_init(&spare);
    State state = {0}, other = {0};
    CrustWakeTicket old = {0}, ticket = {0};
    for (int round = 0; round < 20; ++round) {
        state.calls = state.released = 0;
        task_init(&state.task, &ops);
        assert(!task_queue_submit(&queue, &entry, &state.task, &ticket));
        assert(!task_queue_wake(old));
        assert(task_queue_submit(&queue, &entry, &state.task, &old) == EBUSY);
        assert(task_queue_submit(&queue, &spare, &state.task, &old) == EINVAL);
        assert(task_queue_run_one(&queue, 0));
        assert(!task_queue_wake(old));
        assert(!task_queue_run_one(&queue, 0));
        assert(task_queue_close(&queue) == EBUSY);
        for (int i = 0; i < 100; ++i) assert(task_queue_wake(ticket));
        assert(task_queue_run_one(&queue, 0));
        assert(!task_queue_run_one(&queue, 0));
        int out = 0;
        assert(task_take(&state.task, &out) && out == 2 && state.released == 1);
        assert(!task_queue_wake(ticket));
        old = ticket;
    }
    entry.generation = UINT64_MAX;
    task_init(&other.task, &ops);
    assert(task_queue_submit(&queue, &entry, &other.task, &ticket) == EOVERFLOW);
    assert(!task_queue_close(&queue));
    assert(task_queue_submit(&queue, &spare, &other.task, &ticket) == EPIPE);
    assert(task_drop_inactive(&other.task) && other.released == 1);
    task_queue_entry_destroy(&entry);
    task_queue_entry_destroy(&spare);
    task_queue_destroy(&queue);
    return 0;
}
''')

    def test_workers_and_wakes_outlive_freed_frames(self):
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + r'''
#include <assert.h>
enum { N = 8 };
typedef struct { CrustTask task; CrustWakeTicket ticket; _Atomic int active; int calls; } State;
static _Atomic int released, stop, notifications;
static CrustTaskStep resume(CrustTask *task) {
    State *s = (State *)task;
    assert(atomic_fetch_add(&s->active, 1) == 0);
    int calls = ++s->calls;
    assert(calls <= 20);
    if (calls < 20) { assert(task_queue_wake(s->ticket)); sched_yield(); }
    assert(atomic_fetch_sub(&s->active, 1) == 1);
    return calls == 20 ? TASK_STEP_RETURN : calls % 2 ? TASK_STEP_PENDING : TASK_STEP_YIELD;
}
static void take(CrustTask *task, void *out) { *(int *)out = ((State *)task)->calls; }
static void release(CrustTask *task) { atomic_fetch_add(&released, 1); free(task); }
static const CrustTaskOps ops = {resume, take, release};
static void *notify(void *p) {
    CrustWakeTicket *tickets = p;
    while (!atomic_load(&stop)) {
        for (int i = 0; i < N; ++i) (void)task_queue_wake(tickets[i]);
        atomic_fetch_add(&notifications, 1);
        sched_yield();
    }
    return NULL;
}
int main(void) {
    CrustReadyQueue queue;
    CrustQueueEntry entries[N];
    CrustWakeTicket tickets[N];
    State *states[N];
    assert(!task_queue_init(&queue));
    for (int i = 0; i < N; ++i) {
        states[i] = calloc(1, sizeof(State)); assert(states[i]);
        task_init(&states[i]->task, &ops);
        atomic_init(&states[i]->active, 0);
        task_queue_entry_init(&entries[i]);
        assert(!task_queue_submit(&queue, &entries[i], &states[i]->task, &states[i]->ticket));
        tickets[i] = states[i]->ticket;
    }
    pthread_t notifier, workers[3];
    assert(!pthread_create(&notifier, NULL, notify, tickets));
    for (int i = 0; i < 3; ++i) assert(!pthread_create(&workers[i], NULL, task_queue_worker, &queue));
    for (int i = 0; i < N; ++i) {
        while (!atomic_load_explicit(&states[i]->task.worker_done, memory_order_acquire)) sched_yield();
        int out = 0;
        assert(task_take(&states[i]->task, &out) && out == 20);
    }
    /* Old event producers keep sending tickets after every frame was freed. */
    int before = atomic_load(&notifications);
    while (atomic_load(&notifications) < before + 100) sched_yield();
    for (int i = 0; i < N; ++i) assert(!task_queue_wake(tickets[i]));
    atomic_store(&stop, 1);
    assert(!pthread_join(notifier, NULL));
    assert(!task_queue_close(&queue));
    for (int i = 0; i < 3; ++i) assert(!pthread_join(workers[i], NULL));
    assert(atomic_load(&released) == N);
    for (int i = 0; i < N; ++i) task_queue_entry_destroy(&entries[i]);
    task_queue_destroy(&queue);
    return 0;
}
''')


if __name__ == '__main__': unittest.main()
