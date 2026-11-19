
#include <stddef.h>
#include <stdint.h>
typedef enum { CRUST_RUNTIME_LAUNCH_FAILED = 5 } CrustRuntimeError;
typedef struct {
    const unsigned char *bytes;
    size_t length;
    int descends;
} CrustText;
typedef struct {
    const unsigned char *base;
    size_t length;
    int descends;
} VectorSlice;
typedef struct { int status; CrustText text; } CrustTextResult;
typedef uint32_t CrustChar;
typedef enum {
    CRUST_CHAR_OK = 0,
    CRUST_CHAR_OUT_OF_BOUNDS = 1,
    CRUST_CHAR_NOT_BOUNDARY = 2,
    CRUST_CHAR_EMPTY = 3,
    CRUST_CHAR_MULTIPLE = 4,
    CRUST_CHAR_NONE = 6
} CrustCharStatus;
typedef struct {
    CrustCharStatus status;
    CrustChar value;
} CrustCharResult;
typedef struct {
    int status;
    uint8_t value;
} CrustByteResult;

typedef struct { int status; } CrustStatus;
typedef struct { int status; int value; } CrustIntPayload;
typedef struct { int status; uint8_t value; } CrustBytePayload;

typedef struct {
    int status, value;
    CrustRuntimeError runtime_error_value;
    int read_error_value;
    int capacity_error_value;
    int byte_replace_error_value;
    int char_at_error_value;
    int char_from_str_error_value;
    int integer_conversion_error_value;
    int slice_error_value;

    uint8_t byte_value;
    uint32_t char_value;
    CrustText text_value;
    CrustCharResult decoded_value;
    CrustByteResult replaced_value;
    CrustTextResult sliced_value;
    CrustIntPayload vector_int_result;
    CrustBytePayload vector_byte_result;
    CrustStatus vector_status_result;
    const unsigned char *byte_ref_value;
    VectorSlice vector_slice_value;
    const int *reference;
    int *mutable_reference;
    uint8_t *mutable_byte_reference;
    struct Cell *allocation;
} CrustJoinResult;



#include <stdatomic.h>
#include <stdint.h>

typedef struct {
    int status;
    CrustJoinResult value;
} CrustNestedJoinResult;

typedef struct CrustTask CrustTask;

typedef enum {
    TASK_INACTIVE, TASK_QUEUED, TASK_RUNNING, TASK_SUSPENDED, TASK_COMPLETE, TASK_CONSUMED
} CrustTaskState;

typedef enum {
    TASK_STEP_YIELD, TASK_STEP_RETURN
} CrustTaskStep;

typedef struct {
    CrustTaskStep (*resume)(CrustTask *);
    void (*take_result)(CrustTask *, void *);
    void (*release)(CrustTask *);
} CrustTaskOps;

struct CrustTask {
    _Atomic CrustTaskState state;
    _Atomic int worker_done;
    const CrustTaskOps *ops;
};

static void task_init(CrustTask *task, const CrustTaskOps *ops) {
    task->ops = ops;
    atomic_init(&task->state, TASK_INACTIVE);
    atomic_init(&task->worker_done, 0);
}

static CrustTaskState task_resume_claimed(CrustTask *task) {
    CrustTaskStep step = task->ops->resume(task);
    CrustTaskState next = step == TASK_STEP_YIELD ? TASK_SUSPENDED : TASK_COMPLETE;
    atomic_store(&task->state, next);
    return next;
}

static CrustTaskState task_poll(CrustTask *task) {
    CrustTaskState state = atomic_load(&task->state);
    while (state == TASK_INACTIVE || state == TASK_SUSPENDED) {
        if (atomic_compare_exchange_strong(&task->state, &state, TASK_RUNNING))
            return task_resume_claimed(task);
    }
    return state;
}

static int task_take(CrustTask *task, void *result) {
    CrustTaskState expected = TASK_COMPLETE;
    if (!atomic_compare_exchange_strong(&task->state, &expected, TASK_CONSUMED)) return 0;
    task->ops->take_result(task, result);
    task->ops->release(task);
    return 1;
}

static int task_drop_inactive(CrustTask *task) {
    CrustTaskState expected = TASK_INACTIVE;
    if (!atomic_compare_exchange_strong(&task->state, &expected, TASK_CONSUMED)) return 0;
    task->ops->release(task);
    return 1;
}

static int task_drop_complete(CrustTask *task) {
    CrustTaskState expected = TASK_COMPLETE;
    if (!atomic_compare_exchange_strong(&task->state, &expected, TASK_CONSUMED)) return 0;
    task->ops->release(task);
    return 1;
}

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

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdlib.h>

/* Internal boundary. Success transfers one run invocation to a new thread.
   Failure leaves data untouched. wait synchronizes with a joinable launch.
   detach is optional and releases the native handle without waiting or
   reentering the abandoned-task registry. */
typedef struct {
    int (*launch)(pthread_t *, int detached, void *(*run)(void *), void *);
    int (*wait)(pthread_t);
    int (*detach)(pthread_t);
    int (*launch_blocking)(pthread_t *, int detached, void *(*run)(void *), void *);
} CrustThreadScheduler;

static int task_pthread_launch(pthread_t *thread, int detached, void *(*run)(void *), void *data) {
    (void)thread;
    (void)run;
    (void)data;
    if (!detached) return pthread_create(thread, NULL, run, data);
    pthread_attr_t attr;
    int error = pthread_attr_init(&attr);
    if (error) return error;
    error = pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
    if (!error) error = pthread_create(thread, &attr, run, data);
    pthread_attr_destroy(&attr);
    return error;
}

static int task_pthread_wait(pthread_t thread) {
    return pthread_join(thread, NULL);
}

static const CrustThreadScheduler task_default_scheduler = {
    .launch = reject_scheduler, .wait = task_pthread_wait, .detach = pthread_detach,
    .launch_blocking = reject_scheduler
};

typedef struct {
    pthread_t thread;
    int (*wait)(pthread_t);
    int (*detach)(pthread_t);
    CrustTask *task;
    _Atomic int joined;
    int error;
} CrustExecution;


typedef struct {
    pthread_t thread;
    int (*wait)(pthread_t);
    int (*detach)(pthread_t);
    CrustTask *task;
    int detached;
} CrustAbandonedExecution;

typedef struct {
    CrustAbandonedExecution *entries;
    size_t count, capacity;
} CrustAbandonedTasks;

static void *task_thread_run(void *pointer) {
    CrustTask *task = pointer;
    CrustTaskState queued = TASK_QUEUED;
    if (!atomic_compare_exchange_strong(&task->state, &queued, TASK_RUNNING)) abort();
    CrustTaskState state = task_resume_claimed(task);
    while (state == TASK_SUSPENDED) {
        sched_yield();
        state = task_poll(task);
    }
    if (state != TASK_COMPLETE) abort();
    /* Last access to the task slot, for both kinds of launch. */
    atomic_store_explicit(&task->worker_done, 1, memory_order_release);
    return NULL;
}

/* A native block is synchronous: invoke it exactly once. A yielded step here
   is a compiler/runtime contract violation, not a request to schedule it. */
static void *task_native_run(void *pointer) {
    CrustTask *task = pointer;
    CrustTaskState queued = TASK_QUEUED;
    if (!atomic_compare_exchange_strong(&task->state, &queued, TASK_RUNNING)) abort();
    if (task_resume_claimed(task) != TASK_COMPLETE) abort();
    /* No access to the task slot is allowed after this publication. */
    atomic_store_explicit(&task->worker_done, 1, memory_order_release);
    return NULL;
}

static int task_start_joinable(CrustExecution *execution, CrustTask *task,
        int (*launch)(pthread_t *, int, void *(*)(void *), void *),
        int (*wait)(pthread_t), int (*detach)(pthread_t), void *(*run)(void *)) {
    CrustTaskState inactive = TASK_INACTIVE;
    if (!atomic_compare_exchange_strong(&task->state, &inactive, TASK_QUEUED)) return EINVAL;
    execution->task = task;
    atomic_init(&execution->joined, 0);
    execution->wait = wait;
    execution->detach = detach;
    int error = launch ? launch(&execution->thread, 0, run, task) : ENOTSUP;
    execution->error = error;
    if (error) {
        atomic_store(&task->state, TASK_INACTIVE);
        if (!task_drop_inactive(task)) abort();
        execution->task = NULL;
    }
    return error;
}

static int task_thread_start_mode(CrustExecution *execution, CrustTask *task,
                                  const CrustThreadScheduler *scheduler, int blocking) {
    return task_start_joinable(execution, task,
        blocking ? scheduler->launch_blocking : scheduler->launch,
        scheduler->wait, scheduler->detach, task_thread_run);
}

static int task_native_start(CrustExecution *execution, CrustTask *task) {
    return task_start_joinable(execution, task, task_pthread_launch,
                              task_pthread_wait, pthread_detach, task_native_run);
}

static int task_thread_start_with(CrustExecution *execution, CrustTask *task,
                                  const CrustThreadScheduler *scheduler) {
    return task_thread_start_mode(execution, task, scheduler, 0);
}

static int task_thread_start_blocking_with(CrustExecution *execution, CrustTask *task,
                                          const CrustThreadScheduler *scheduler) {
    return task_thread_start_mode(execution, task, scheduler, 1);
}

static int task_thread_start_blocking(CrustExecution *execution, CrustTask *task) {
    return task_thread_start_blocking_with(execution, task, &task_default_scheduler);
}

static int task_thread_start(CrustExecution *execution, CrustTask *task) {
    return task_thread_start_with(execution, task, &task_default_scheduler);
}

static int task_thread_join(CrustExecution *execution, void *result) {
    if (!execution->task || atomic_exchange(&execution->joined, 1)) return 0;
    /* A system join failure cannot establish that the task has terminated. */
    if (execution->wait(execution->thread) != 0) abort();
    if (!task_take(execution->task, result)) abort();
    return 1;
}

static CrustJoinResult task_join_into(CrustExecution *execution, void *out) {
    CrustJoinResult result = {0};
    if (execution->error) result.status = CRUST_RUNTIME_LAUNCH_FAILED;
    else if (!task_thread_join(execution, out)) abort();
    return result;
}

static CrustJoinResult task_join_result(CrustExecution *execution) {
    int value = 0;
    CrustJoinResult result = task_join_into(execution, &value);
    result.value = value;
    return result;
}

static CrustJoinResult task_join_allocation(CrustExecution *execution) {
    CrustJoinResult result = {0};
    if (execution->error) result.status = CRUST_RUNTIME_LAUNCH_FAILED;
    else if (!task_thread_join(execution, &result.allocation)) abort();
    return result;
}

static CrustNestedJoinResult task_join_nested(CrustExecution *execution) {
    CrustNestedJoinResult result = {0};
    if (execution->error) result.status = CRUST_RUNTIME_LAUNCH_FAILED;
    else if (!task_thread_join(execution, &result.value)) abort();
    return result;
}

static CrustJoinResult task_join_reference(CrustExecution *execution, int mutable) {
    CrustJoinResult result = {0};
    if (execution->error) result.status = CRUST_RUNTIME_LAUNCH_FAILED;
    else {
        void *out = mutable ? (void *)&result.mutable_reference : (void *)&result.reference;
        if (!task_thread_join(execution, out)) abort();
    }
    return result;
}

/* Registration may race with draining a parent that is still running.
   Release the lock before waiting, so that parent can register children. */
static pthread_mutex_t abandoned_mutex = PTHREAD_MUTEX_INITIALIZER;

static void task_register_abandoned(CrustAbandonedTasks *tasks, CrustAbandonedExecution execution) {
    if (pthread_mutex_lock(&abandoned_mutex) != 0) abort();
    if (tasks->count == tasks->capacity) abort();
    tasks->entries[tasks->count++] = execution;
    if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
}

static void task_thread_abandon(CrustAbandonedTasks *tasks, CrustExecution *execution) {
    if (atomic_exchange(&execution->joined, 1)) abort();
    if (!execution->task) return;
    task_register_abandoned(tasks, (CrustAbandonedExecution){
        .thread = execution->thread, .wait = execution->wait, .detach = execution->detach, .task = execution->task
    });
}

static void task_thread_reap(CrustAbandonedTasks *tasks) {
    for (;;) {
        CrustTask *completed = NULL;
        if (pthread_mutex_lock(&abandoned_mutex) != 0) abort();
        for (size_t i = 0; i < tasks->count; ++i) {
            CrustAbandonedExecution *execution = &tasks->entries[i];
            if (!atomic_load_explicit(&execution->task->worker_done, memory_order_acquire)) continue;
            if (!execution->detached && (!execution->detach || execution->detach(execution->thread))) continue;
            completed = execution->task;
            *execution = tasks->entries[--tasks->count];
            break;
        }
        if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
        if (!completed) return;
        if (!task_drop_complete(completed)) abort();
    }
}

static void task_thread_drain(CrustAbandonedTasks *tasks) {
    for (;;) {
        if (pthread_mutex_lock(&abandoned_mutex) != 0) abort();
        if (!tasks->count) {
            if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
            return;
        }
        CrustAbandonedExecution execution = tasks->entries[--tasks->count];
        if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
        if (execution.detached) {
            while (!atomic_load_explicit(&execution.task->worker_done, memory_order_acquire))
                sched_yield();
        } else if (execution.wait(execution.thread) != 0) abort();
        if (!task_drop_complete(execution.task)) abort();
    }
}


/* The worker only accesses its own stable task slot. It publishes
   completion as its last access, so the parent handle can disappear. */
typedef struct {
    CrustTask *task;
    int error;
} CrustAsyncExecution;

static void task_start_detached(CrustAsyncExecution *execution, CrustTask *task,
        int (*launch)(pthread_t *, int, void *(*)(void *), void *), void *(*run)(void *)) {
    CrustTaskState inactive = TASK_INACTIVE;
    if (!atomic_compare_exchange_strong(&task->state, &inactive, TASK_QUEUED)) abort();
    execution->task = task;
    pthread_t thread;
    int error = launch ? launch(&thread, 1, run, task) : ENOTSUP;
    execution->error = error;
    if (error) {
        atomic_store(&task->state, TASK_INACTIVE);
        if (!task_drop_inactive(task)) abort();
        execution->task = NULL;
    }
}

static void task_async_start_mode(CrustAsyncExecution *execution, CrustTask *task,
                                  const CrustThreadScheduler *scheduler, int blocking) {
    task_start_detached(execution, task,
        blocking ? scheduler->launch_blocking : scheduler->launch, task_thread_run);
}

static void task_native_async_start(CrustAsyncExecution *execution, CrustTask *task) {
    task_start_detached(execution, task, task_pthread_launch, task_native_run);
}

static void task_async_start_with(CrustAsyncExecution *execution, CrustTask *task,
                                  const CrustThreadScheduler *scheduler) {
    task_async_start_mode(execution, task, scheduler, 0);
}

static void task_async_start_blocking_with(CrustAsyncExecution *execution, CrustTask *task,
                                         const CrustThreadScheduler *scheduler) {
    task_async_start_mode(execution, task, scheduler, 1);
}

static void task_async_start_blocking(CrustAsyncExecution *execution, CrustTask *task) {
    task_async_start_blocking_with(execution, task, &task_default_scheduler);
}

static void task_async_start(CrustAsyncExecution *execution, CrustTask *task) {
    task_async_start_with(execution, task, &task_default_scheduler);
}

static int task_async_ready(const CrustAsyncExecution *execution) {
    return execution->error || (execution->task &&
        atomic_load_explicit(&execution->task->worker_done, memory_order_acquire));
}

static int task_async_finish(CrustAsyncExecution *execution, void *out) {
    int status = execution->error ? CRUST_RUNTIME_LAUNCH_FAILED : 0;
    if (!status && !task_take(execution->task, out)) abort();
    execution->task = NULL;
    execution->error = 0;
    return status;
}

static int task_async_take_into(CrustAsyncExecution *execution, CrustJoinResult *result, void *out) {
    if (!task_async_ready(execution)) return 0;
    *result = (CrustJoinResult){0};
    result->status = task_async_finish(execution, out);
    return 1;
}
static int task_async_take(CrustAsyncExecution *execution, CrustJoinResult *result) {
    return task_async_take_into(execution, result, &result->value);
}

static int task_async_take_nested(CrustAsyncExecution *execution, CrustNestedJoinResult *result) {
    if (!task_async_ready(execution)) return 0;
    *result = (CrustNestedJoinResult){0};
    result->status = task_async_finish(execution, &result->value);
    return 1;
}

static void task_async_abandon(CrustAbandonedTasks *tasks, CrustAsyncExecution *execution) {
    if (execution->task) {
        task_register_abandoned(tasks, (CrustAbandonedExecution){
            .task = execution->task, .detached = 1
        });
        execution->task = NULL;
    }
    execution->error = 0;
}


#include <stddef.h>
#include <stdint.h>
#include <stdint.h>
#include <stdatomic.h>

typedef struct {
    unsigned char *storage;
    size_t stride;
    size_t count;
    _Atomic size_t *generations;
} CrustTaskPool;

typedef struct {
    CrustTaskPool *pool;
    size_t index;
    size_t generation;
} CrustTaskSlot;

static void task_pool_init(CrustTaskPool *pool, void *storage, size_t stride,
                           size_t count, _Atomic size_t *generations) {
    *pool = (CrustTaskPool){storage, stride, count, generations};
    for (size_t i = 0; i < count; ++i) atomic_init(&generations[i], 0);
}

static CrustTaskSlot task_pool_acquire(CrustTaskPool *pool) {
    for (size_t i = 0; i < pool->count; ++i) {
        size_t generation = atomic_load(&pool->generations[i]);
        /* Even generations are free. Retire the final even generation
           rather than letting an obsolete ticket become valid again. */
        if (generation % 2 || generation == SIZE_MAX - 1) continue;
        if (atomic_compare_exchange_strong(&pool->generations[i], &generation, generation + 1))
            return (CrustTaskSlot){pool, i, generation + 1};
    }
    return (CrustTaskSlot){0};
}

static void *task_slot_address(CrustTaskSlot slot) {
    if (!slot.pool || slot.index >= slot.pool->count || slot.generation % 2 == 0 ||
            atomic_load(&slot.pool->generations[slot.index]) != slot.generation) return NULL;
    return slot.pool->storage + slot.index * slot.pool->stride;
}

static int task_pool_release(CrustTaskSlot slot) {
    if (!slot.pool || slot.index >= slot.pool->count ||
            slot.generation % 2 == 0 || slot.generation == SIZE_MAX) return 0;
    return atomic_compare_exchange_strong(&slot.pool->generations[slot.index],
                                          &slot.generation, slot.generation + 1);
}

/* The owner calls this after synchronizing with any threads using the pool. */
static int task_pool_is_empty(const CrustTaskPool *pool) {
    for (size_t i = 0; i < pool->count; ++i)
        if (atomic_load(&pool->generations[i]) % 2) return 0;
    return 1;
}

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
    fail_native = 0;
    Payload payload = {0};
    CrustJoinResult result = {0};
    
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
