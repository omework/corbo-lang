"""Type-erased task transitions for the generated C runtime."""

from numeric_core import CONVERSION_C_TYPES, CONVERSION_LAYOUTS, EXTRA_C_TYPES, NUMERIC_JOIN_C, NUMERIC_REFERENCE_FIELDS

UTF8_VALUE_TYPES_C = r'''
#include <stddef.h>
#include <stdint.h>
struct Cell;
struct Source;
typedef struct {
    struct Cell *root;
    size_t offset, size;
    const struct Source *layout;
} CrustStructureView;
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
    int bool_value;
    CrustRuntimeError runtime_error_value;
    int read_error_value;
    int capacity_error_value;
    int byte_replace_error_value;
    int char_at_error_value;
    int char_from_str_error_value;
    int integer_conversion_error_value;
    int numeric_conversion_error_value;
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
    CrustStructureView structure_reference, mutable_structure_reference;
    struct Cell *allocation;
} CrustJoinResult;

typedef struct {
    int status;
    CrustJoinResult value;
} CrustNestedJoinResult;



'''.replace('typedef struct {\n    int status, value;',
            CONVERSION_LAYOUTS + '\ntypedef struct {\n    int status, value;', 1
).replace('    uint8_t byte_value;',
          NUMERIC_JOIN_C + '    union {\n' +
          ''.join(f'        {ctype} {mode};\n' for mode, ctype in CONVERSION_C_TYPES.items()) +
          '    };\n    uint8_t byte_value;', 1
).replace('    uint8_t *mutable_byte_reference;',
          '    uint8_t *mutable_byte_reference;\n    union {\n' +
          ''.join(f'        {EXTRA_C_TYPES[typ]} *{field};\n'
                  for (_, typ), field in NUMERIC_REFERENCE_FIELDS.items()) + '    };', 1)

TASK_RUNTIME_BODY = r'''
#include <stdatomic.h>
#include <stdint.h>


typedef struct CrustTask CrustTask;
typedef struct CrustQueueEntry CrustQueueEntry;
typedef struct { CrustQueueEntry *entry; uint64_t generation; } CrustWakeTicket;

typedef enum {
    TASK_INACTIVE, TASK_QUEUED, TASK_RUNNING, TASK_SUSPENDED, TASK_COMPLETE, TASK_CONSUMED
} CrustTaskState;

typedef enum {
    TASK_STEP_YIELD, TASK_STEP_RETURN, TASK_STEP_PENDING
} CrustTaskStep;

typedef struct {
    CrustTaskStep (*resume)(CrustTask *);
    void (*take_result)(CrustTask *, void *);
    void (*release)(CrustTask *);
} CrustTaskOps;

struct CrustTask {
    _Atomic CrustTaskState state;
    _Atomic int worker_done;
    _Atomic int scheduling_lock;
    int ready; /* Protected by scheduling_lock, including during a poll. */
    int yielded; /* Written by the current poller. */
    CrustQueueEntry *queue_entry; /* Stable scheduler storage, when generated. */
    CrustWakeTicket wake_target; /* Root poll owning a chain of direct awaits. */
    const CrustTaskOps *ops;
    int (*can_discard_suspended)(CrustTask *);
    void (*discard_suspended)(CrustTask *);
};

static void task_init(CrustTask *task, const CrustTaskOps *ops) {
    task->ops = ops;
    atomic_init(&task->state, TASK_INACTIVE);
    atomic_init(&task->worker_done, 0);
    atomic_init(&task->scheduling_lock, 0);
    task->ready = 1;
    task->yielded = 0;
    task->queue_entry = NULL;
    task->wake_target = (CrustWakeTicket){0};
    task->can_discard_suspended = NULL;
    task->discard_suspended = NULL;
}

/* Only short bookkeeping sections hold this gate, never user code. Callers
   must keep the task alive until their poll/wake calls have returned. */
static void task_scheduling_lock(CrustTask *task) {
    int expected = 0;
    while (!atomic_compare_exchange_weak_explicit(&task->scheduling_lock,
            &expected, 1, memory_order_acquire, memory_order_relaxed)) expected = 0;
}

static void task_scheduling_unlock(CrustTask *task) {
    atomic_store_explicit(&task->scheduling_lock, 0, memory_order_release);
}

static int task_wake(CrustTask *task) {
    /* Primitive readiness update. External producers for a queued task use
       task_queue_wake so that a waiting task is also placed on its queue. */
    task_scheduling_lock(task);
    CrustTaskState state = atomic_load(&task->state);
    int live = state != TASK_COMPLETE && state != TASK_CONSUMED;
    if (live) task->ready = 1;
    task_scheduling_unlock(task);
    return live;
}

static CrustTaskState task_resume_claimed(CrustTask *task) {
    CrustTaskStep step = task->ops->resume(task);
    task->yielded = step == TASK_STEP_YIELD;
    CrustTaskState next = step == TASK_STEP_RETURN ? TASK_COMPLETE : TASK_SUSPENDED;
    task_scheduling_lock(task);
    /* Pending keeps a wake received during resume. Yield makes itself ready. */
    if (step == TASK_STEP_YIELD) task->ready = 1;
    atomic_store(&task->state, next);
    task_scheduling_unlock(task);
    return next;
}

static CrustTaskState task_poll(CrustTask *task) {
    task_scheduling_lock(task);
    CrustTaskState state = atomic_load(&task->state);
    if ((state == TASK_INACTIVE || state == TASK_SUSPENDED) && task->ready) {
        if (atomic_compare_exchange_strong(&task->state, &state, TASK_RUNNING)) {
            task->ready = 0;
            task_scheduling_unlock(task);
            return task_resume_claimed(task);
        }
    }
    task_scheduling_unlock(task);
    return state;
}

static int task_consume(CrustTask *task, CrustTaskState expected) {
    task_scheduling_lock(task);
    int consumed = atomic_compare_exchange_strong(&task->state, &expected, TASK_CONSUMED);
    task_scheduling_unlock(task);
    return consumed;
}

static CrustTaskState task_poll_child(CrustTask *parent, CrustTask *child) {
    child->wake_target = parent->wake_target;
    /* A resumed parent rechecks its awaited chain. No child is polled in
       parallel: direct await owns it and executes it on the parent's thread. */
    task_wake(child);
    return task_poll(child);
}
static CrustTaskStep task_child_suspension(CrustTask *child) {
    task_scheduling_lock(child);
    int ready = child->ready;
    task_scheduling_unlock(child);
    return ready ? TASK_STEP_YIELD : TASK_STEP_PENDING;
}

static int task_take(CrustTask *task, void *result) {
    if (!task_consume(task, TASK_COMPLETE)) return 0;
    task->ops->take_result(task, result);
    task->ops->release(task);
    return 1;
}

static int task_drop_inactive(CrustTask *task) {
    if (!task_consume(task, TASK_INACTIVE)) return 0;
    task->ops->release(task);
    return 1;
}

static int task_drop_complete(CrustTask *task) {
    if (!task_consume(task, TASK_COMPLETE)) return 0;
    task->ops->release(task);
    return 1;
}

/* Private owned-state destruction used by Select cleanup. The caller has
   exclusive ownership of the whole direct-await tree, has revoked external
   wake routes, and never uses this on a scheduled execution handle. Preflight
   the tree before consuming anything, including captures of inactive children. */
static int task_owned_discardable(CrustTask *task) {
    CrustTaskState state = atomic_load(&task->state);
    if (state == TASK_INACTIVE || state == TASK_COMPLETE) return 1;
    return state == TASK_SUSPENDED && task->can_discard_suspended &&
        task->discard_suspended && task->can_discard_suspended(task);
}

static int task_drop_owned(CrustTask *task) {
    if (!task_owned_discardable(task)) return 0;
    CrustTaskState state = atomic_load(&task->state);
    if (!task_consume(task, state)) return 0;
    if (state == TASK_SUSPENDED) task->discard_suspended(task);
    else task->ops->release(task);
    return 1;
}
'''

TASK_THREAD_RUNTIME = r'''
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
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
    .launch = task_pthread_launch, .wait = task_pthread_wait, .detach = pthread_detach,
    .launch_blocking = task_pthread_launch
};

static int task_default_submit(CrustTask *task);
static void task_default_wait(CrustTask *task);
static void task_default_close(void);

typedef void (*CrustSchedulerSubmit)(void *, int *);
typedef void (*CrustSchedulerWake)(void *, CrustWakeTicket);
static pthread_mutex_t crust_scheduler_mutex = PTHREAD_MUTEX_INITIALIZER;
static void *crust_scheduler_instance;
static CrustSchedulerSubmit crust_scheduler_spawn, crust_scheduler_spawn_blocking;
static CrustSchedulerWake crust_scheduler_wake;
static _Atomic int crust_scheduler_launch_seen;
static _Thread_local int crust_scheduler_in_callback;

static _Noreturn void crust_scheduler_violation(const char *message) {
    fprintf(stderr, "Crust: %s\n", message);
    exit(EXIT_FAILURE);
}

static void crust_scheduler_install(void *instance, CrustSchedulerSubmit spawn,
                                    CrustSchedulerSubmit blocking, CrustSchedulerWake wake) {
    if (crust_scheduler_instance || atomic_load(&crust_scheduler_launch_seen))
        crust_scheduler_violation("scheduler installation must precede the first launch and may occur only once");
    crust_scheduler_instance = instance;
    crust_scheduler_spawn = spawn;
    crust_scheduler_spawn_blocking = blocking;
    crust_scheduler_wake = wake;
}
static void crust_future_resolve(int *disposition, int queued) {
    if (*disposition) crust_scheduler_violation("Future already consumed by scheduler");
    *disposition = queued ? 1 : -1;
}
static int crust_scheduler_dispatch(int blocking) {
    atomic_store(&crust_scheduler_launch_seen, 1);
    if (!crust_scheduler_instance) return 0;
    if (crust_scheduler_in_callback) crust_scheduler_violation("recursive scheduler submission");
    if (pthread_mutex_lock(&crust_scheduler_mutex)) abort();
    crust_scheduler_in_callback = 1;
    int disposition = 0;
    CrustSchedulerSubmit submit = blocking ? crust_scheduler_spawn_blocking : crust_scheduler_spawn;
    submit(crust_scheduler_instance, &disposition);
    crust_scheduler_in_callback = 0;
    if (pthread_mutex_unlock(&crust_scheduler_mutex)) abort();
    return disposition == 1 ? 0 : EAGAIN;
}
static void crust_scheduler_notify(CrustWakeTicket id) {
    if (!crust_scheduler_instance) return;
    if (crust_scheduler_in_callback) crust_scheduler_violation("recursive scheduler wake");
    if (pthread_mutex_lock(&crust_scheduler_mutex)) abort();
    crust_scheduler_in_callback = 1;
    crust_scheduler_wake(crust_scheduler_instance, id);
    crust_scheduler_in_callback = 0;
    if (pthread_mutex_unlock(&crust_scheduler_mutex)) abort();
}
static void crust_scheduler_close(void) {
    if (!crust_scheduler_instance) return;
    task_default_close();
    crust_scheduler_instance = NULL;
}
static int task_external_register(CrustTask *task);
static void task_external_forget(CrustTask *task);
static void task_external_complete(CrustTask *task);

typedef struct {
    pthread_t thread;
    int (*wait)(pthread_t);
    int (*detach)(pthread_t);
    CrustTask *task;
    _Atomic int joined;
    int error;
    int pooled;
} CrustExecution;


typedef struct {
    pthread_t thread;
    int (*wait)(pthread_t);
    int (*detach)(pthread_t);
    CrustTask *task;
    int detached;
    int pooled;
} CrustAbandonedExecution;

typedef struct {
    CrustAbandonedExecution *entries;
    size_t count, capacity, reaping;
} CrustAbandonedTasks;

/* Installed before any worker is launched. */
static void (*task_completion_reap)(void);

static void task_claim_queued(CrustTask *task) {
    task_scheduling_lock(task);
    CrustTaskState queued = TASK_QUEUED;
    if (!atomic_compare_exchange_strong(&task->state, &queued, TASK_RUNNING)) abort();
    task->ready = 0;
    task_scheduling_unlock(task);
}

static void *task_thread_run(void *pointer) {
    CrustTask *task = pointer;
    task_claim_queued(task);
    CrustTaskState state = task_resume_claimed(task);
    while (state == TASK_SUSPENDED) {
        sched_yield();
        state = task_poll(task);
    }
    if (state != TASK_COMPLETE) abort();
    /* Last access to the task slot, for both kinds of launch. */
    task_external_complete(task);
    return NULL;
}

/* A native block is synchronous: invoke it exactly once. A yielded step here
   is a compiler/runtime contract violation, not a request to schedule it. */
static void *task_native_run(void *pointer) {
    CrustTask *task = pointer;
    task_claim_queued(task);
    if (task_resume_claimed(task) != TASK_COMPLETE) abort();
    /* No access to the task slot is allowed after this publication. */
    task_external_complete(task);
    return NULL;
}

static int task_start_joinable(CrustExecution *execution, CrustTask *task,
        int (*launch)(pthread_t *, int, void *(*)(void *), void *),
        int (*wait)(pthread_t), int (*detach)(pthread_t), void *(*run)(void *)) {
    CrustTaskState inactive = TASK_INACTIVE;
    if (!atomic_compare_exchange_strong(&task->state, &inactive, TASK_QUEUED)) return EINVAL;
    execution->task = task;
    execution->pooled = 0;
    atomic_init(&execution->joined, 0);
    execution->wait = wait;
    execution->detach = detach;
    int error = task_external_register(task);
    if (!error) error = launch ? launch(&execution->thread, 0, run, task) : ENOTSUP;
    execution->error = error;
    if (error) {
        task_external_forget(task);
        atomic_store(&task->state, TASK_INACTIVE);
        if (!task_drop_inactive(task)) abort();
        execution->task = NULL;
    }
    return error;
}

static int task_thread_start_mode(CrustExecution *execution, CrustTask *task,
                                  const CrustThreadScheduler *scheduler, int blocking) {
    if (scheduler == &task_default_scheduler) {
        int error = crust_scheduler_dispatch(blocking);
        if (error) {
            if (!task_drop_inactive(task)) abort();
            execution->error = error;
            execution->task = NULL;
            return error;
        }
    }
    if (scheduler == &task_default_scheduler && !blocking && task->queue_entry) {
        if (atomic_load(&task->state) != TASK_INACTIVE) return EINVAL;
        execution->task = task;
        execution->pooled = 1;
        execution->thread = (pthread_t){0};
        execution->wait = NULL;
        execution->detach = NULL;
        atomic_init(&execution->joined, 0);
        int error = task_default_submit(task);
        execution->error = error;
        if (error) {
            if (error == EINVAL) return error;
            if (!task_drop_inactive(task)) abort();
            execution->task = NULL;
        }
        return error;
    }
    return task_start_joinable(execution, task,
        blocking ? scheduler->launch_blocking : scheduler->launch,
        scheduler->wait, scheduler->detach, task_thread_run);
}

static int task_native_start(CrustExecution *execution, CrustTask *task) {
    atomic_store(&crust_scheduler_launch_seen, 1);
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
    if (execution->pooled) task_default_wait(execution->task);
    else if (execution->wait(execution->thread) != 0) abort();
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
static pthread_cond_t abandoned_changed = PTHREAD_COND_INITIALIZER;

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
        .thread = execution->thread, .wait = execution->wait, .detach = execution->detach,
        .task = execution->task, .pooled = execution->pooled
    });
}

static void task_thread_reap(CrustAbandonedTasks *tasks) {
    for (;;) {
        CrustTask *completed = NULL;
        if (pthread_mutex_lock(&abandoned_mutex) != 0) abort();
        for (size_t i = 0; i < tasks->count; ++i) {
            CrustAbandonedExecution *execution = &tasks->entries[i];
            if (!atomic_load_explicit(&execution->task->worker_done, memory_order_acquire)) continue;
            if (!execution->pooled && !execution->detached && (!execution->detach || execution->detach(execution->thread))) continue;
            completed = execution->task;
            *execution = tasks->entries[--tasks->count];
            tasks->reaping++;
            break;
        }
        if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
        if (!completed) return;
        if (!task_drop_complete(completed)) abort();
        if (pthread_mutex_lock(&abandoned_mutex) != 0) abort();
        tasks->reaping--;
        if (pthread_cond_broadcast(&abandoned_changed) != 0) abort();
        if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
    }
}

static void task_thread_drain(CrustAbandonedTasks *tasks) {
    for (;;) {
        if (pthread_mutex_lock(&abandoned_mutex) != 0) abort();
        while (!tasks->count && tasks->reaping)
            if (pthread_cond_wait(&abandoned_changed, &abandoned_mutex) != 0) abort();
        if (!tasks->count) {
            if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
            return;
        }
        CrustAbandonedExecution execution = tasks->entries[--tasks->count];
        if (pthread_mutex_unlock(&abandoned_mutex) != 0) abort();
        if (execution.pooled) task_default_wait(execution.task);
        else if (execution.detached) {
            while (!atomic_load_explicit(&execution.task->worker_done, memory_order_acquire))
                sched_yield();
        } else if (execution.wait(execution.thread) != 0) abort();
        if (!task_drop_complete(execution.task)) abort();
    }
}

'''

TASK_READY_QUEUE_RUNTIME = r'''
/* Entries live in scheduler storage, independently of task frames. A ticket
   may outlive a frame, but never its entry. Entry storage is retired only after
   all workers and event producers using it have stopped. No heap allocation. */
typedef struct CrustReadyQueue CrustReadyQueue;
struct CrustQueueEntry {
    pthread_mutex_t mutex;
    CrustReadyQueue *queue;
    CrustTask *task;
    uint64_t generation;
    CrustWakeTicket waiter;
    CrustWakeTicket forward; /* Select branch -> enclosing poll, never a frame pointer. */
    int scheduled; /* Queued, claimed by a worker, or currently being polled. */
    CrustQueueEntry *next; /* Queue mutex, not entry mutex. */
};
struct CrustReadyQueue {
    pthread_mutex_t mutex;
    pthread_cond_t changed;
    CrustQueueEntry *head, *tail;
    size_t outstanding;
    int closed;
};

static void task_queue_lock(pthread_mutex_t *mutex) {
    if (pthread_mutex_lock(mutex)) abort();
}
static void task_queue_unlock(pthread_mutex_t *mutex) {
    if (pthread_mutex_unlock(mutex)) abort();
}
static int task_queue_init(CrustReadyQueue *queue) {
    int error = pthread_mutex_init(&queue->mutex, NULL);
    if (error) return error;
    error = pthread_cond_init(&queue->changed, NULL);
    if (error) {
        if (pthread_mutex_destroy(&queue->mutex)) abort();
        return error;
    }
    queue->head = queue->tail = NULL;
    queue->outstanding = 0;
    queue->closed = 0;
    return 0;
}
static void task_queue_entry_init(CrustQueueEntry *entry) {
    if (pthread_mutex_init(&entry->mutex, NULL)) abort();
    entry->queue = NULL;
    entry->task = NULL;
    entry->generation = 0;
    entry->waiter = (CrustWakeTicket){0};
    entry->forward = (CrustWakeTicket){0};
    entry->scheduled = 0;
    entry->next = NULL;
}
/* Caller holds both entry and queue mutexes. No consumer holds the queue
   mutex while acquiring an entry mutex: the lock order cannot be reversed. */
static void task_queue_push_locked(CrustReadyQueue *queue, CrustQueueEntry *entry) {
    entry->next = NULL;
    if (queue->tail) queue->tail->next = entry;
    else queue->head = entry;
    queue->tail = entry;
    entry->scheduled = 1;
    if (pthread_cond_broadcast(&queue->changed)) abort();
}
static void task_queue_push(CrustReadyQueue *queue, CrustQueueEntry *entry) {
    task_queue_lock(&queue->mutex);
    if (queue->closed) abort();
    task_queue_push_locked(queue, entry);
    task_queue_unlock(&queue->mutex);
}
static int task_queue_submit(CrustReadyQueue *queue, CrustQueueEntry *entry,
                             CrustTask *task, CrustWakeTicket *ticket) {
    int error = 0;
    task_queue_lock(&entry->mutex);
    task_queue_lock(&queue->mutex);
    if (entry->task || entry->scheduled) error = EBUSY;
    else if (queue->closed) error = EPIPE;
    else if (entry->generation == UINT64_MAX) error = EOVERFLOW;
    else {
        CrustTaskState inactive = TASK_INACTIVE;
        if (!atomic_compare_exchange_strong(&task->state, &inactive, TASK_QUEUED)) error = EINVAL;
        else {
            ++entry->generation;
            entry->queue = queue;
            entry->task = task;
            task->queue_entry = entry;
            ++queue->outstanding;
            *ticket = (CrustWakeTicket){entry, entry->generation};
            task->wake_target = *ticket;
            entry->waiter = (CrustWakeTicket){0};
            entry->forward = (CrustWakeTicket){0};
            task_queue_push_locked(queue, entry);
        }
    }
    task_queue_unlock(&queue->mutex);
    task_queue_unlock(&entry->mutex);
    return error;
}
static int task_queue_wake(CrustWakeTicket ticket) {
    CrustQueueEntry *entry = ticket.entry;
    if (!entry) return 0;
    task_queue_lock(&entry->mutex);
    int valid = entry->generation == ticket.generation && entry->task;
    CrustWakeTicket forward = {0};
    if (valid) {
        valid = task_wake(entry->task);
        if (valid && !entry->scheduled) task_queue_push(entry->queue, entry);
        if (valid) forward = entry->forward;
    }
    task_queue_unlock(&entry->mutex);
    if (valid) crust_scheduler_notify(ticket);
    /* Never nest entry locks. A detached/reused enclosing entry rejects the
       saved generation; no task frame is retained across this notification. */
    if (forward.entry) task_queue_wake(forward);
    return valid;
}

static int task_external_register(CrustTask *task) {
    CrustQueueEntry *entry = task->queue_entry;
    if (!entry) return 0;
    task_queue_lock(&entry->mutex);
    int error = entry->task || entry->scheduled ? EBUSY :
                entry->generation == UINT64_MAX ? EOVERFLOW : 0;
    if (!error) {
        ++entry->generation;
        entry->queue = NULL;
        entry->task = task;
        entry->scheduled = 1; /* Dedicated worker or owned Select branch; never enqueued. */
        entry->waiter = (CrustWakeTicket){0};
        entry->forward = (CrustWakeTicket){0};
        task->wake_target = (CrustWakeTicket){entry, entry->generation};
    }
    task_queue_unlock(&entry->mutex);
    return error;
}
static void task_external_forget(CrustTask *task) {
    CrustQueueEntry *entry = task->queue_entry;
    if (!entry) return;
    task_queue_lock(&entry->mutex);
    if (entry->task == task) {
        entry->task = NULL;
        entry->scheduled = 0;
        entry->waiter = (CrustWakeTicket){0};
        entry->forward = (CrustWakeTicket){0};
    }
    task_queue_unlock(&entry->mutex);
}
static void task_external_complete(CrustTask *task) {
    CrustQueueEntry *entry = task->queue_entry;
    CrustWakeTicket waiter = {0};
    if (entry) {
        task_queue_lock(&entry->mutex);
        if (entry->task != task || entry->queue) abort();
        waiter = entry->waiter;
        entry->waiter = (CrustWakeTicket){0};
        entry->task = NULL;
        entry->scheduled = 0;
        task_queue_unlock(&entry->mutex);
    }
    /* Notify before the final frame access: a detached thread must not retain
       a ticket into the context after its completion becomes observable. */
    task_queue_wake(waiter);
    /* Completion notification finished. */
    atomic_store_explicit(&task->worker_done, 1, memory_order_release);
    if (task_completion_reap) task_completion_reap();
}

static CrustTaskStep task_subscribe(CrustTask *child, CrustTask *parent) {
    CrustQueueEntry *entry = child->queue_entry;
    if (!entry || !parent->wake_target.entry) return TASK_STEP_YIELD;
    task_queue_lock(&entry->mutex);
    CrustTaskStep step = TASK_STEP_YIELD;
    if (entry->task == child) {
        CrustWakeTicket existing = entry->waiter;
        CrustWakeTicket target = parent->wake_target;
        if (existing.entry && (existing.entry != target.entry || existing.generation != target.generation)) abort();
        entry->waiter = target;
        step = TASK_STEP_PENDING;
    }
    /* If completion detached the entry but has not published worker_done yet,
       Yield bridges that finite publication interval; no notification is lost. */
    task_queue_unlock(&entry->mutex);
    return step;
}
/* A popped entry remains scheduled until the poll has been finalized.
   Wakes in the dequeue-to-poll gap therefore cannot enqueue it twice. */
static CrustQueueEntry *task_queue_pop(CrustReadyQueue *queue, int wait) {
    task_queue_lock(&queue->mutex);
    while (wait && !queue->head && !queue->closed)
        if (pthread_cond_wait(&queue->changed, &queue->mutex)) abort();
    CrustQueueEntry *entry = queue->head;
    if (entry) {
        queue->head = entry->next;
        if (!queue->head) queue->tail = NULL;
        entry->next = NULL;
    }
    task_queue_unlock(&queue->mutex);
    return entry;
}
static int task_queue_run_one(CrustReadyQueue *queue, int wait) {
    CrustQueueEntry *entry = task_queue_pop(queue, wait);
    if (!entry) return 0;
    task_queue_lock(&entry->mutex);
    CrustTask *task = entry->task;
    if (!task || !entry->scheduled) abort();
    task_queue_unlock(&entry->mutex);
    CrustTaskState state;
    if (atomic_load(&task->state) == TASK_QUEUED) {
        task_claim_queued(task);
        state = task_resume_claimed(task);
    } else state = task_poll(task);
    task_queue_lock(&entry->mutex);
    CrustWakeTicket waiter = {0};
    if (state == TASK_COMPLETE) {
        waiter = entry->waiter;
        entry->waiter = (CrustWakeTicket){0};
        entry->task = NULL;
        entry->scheduled = 0;
        task_queue_lock(&queue->mutex);
        if (!queue->outstanding) abort();
        --queue->outstanding;
        task_queue_unlock(&queue->mutex);
    } else if (state == TASK_SUSPENDED) {
        if (task->yielded && crust_scheduler_instance) {
            CrustWakeTicket yielded = {entry, entry->generation};
            task_queue_unlock(&entry->mutex);
            crust_scheduler_notify(yielded);
            task_queue_lock(&entry->mutex);
        }
        task_scheduling_lock(task);
        int ready = task->ready;
        task_scheduling_unlock(task);
        entry->scheduled = 0;
        if (ready) task_queue_push(queue, entry);
    } else abort();
    task_queue_unlock(&entry->mutex);
    if (state == TASK_COMPLETE) {
        task_queue_wake(waiter);
        /* Completion notification finished. */
        task_queue_lock(&queue->mutex);
        /* Last frame access, after the outgoing notification has returned. */
        atomic_store_explicit(&task->worker_done, 1, memory_order_release);
        if (pthread_cond_broadcast(&queue->changed)) abort();
        task_queue_unlock(&queue->mutex);
        if (task_completion_reap) task_completion_reap();
    }
    return 1;
}
static void *task_queue_worker(void *pointer) {
    CrustReadyQueue *queue = pointer;
    while (task_queue_run_one(queue, 1)) {}
    return NULL;
}
static int task_queue_close(CrustReadyQueue *queue) {
    task_queue_lock(&queue->mutex);
    int error = queue->outstanding ? EBUSY : 0;
    if (!error) {
        queue->closed = 1;
        if (pthread_cond_broadcast(&queue->changed)) abort();
    }
    task_queue_unlock(&queue->mutex);
    return error;
}
/* Shutdown precondition: workers joined and event producers stopped. */
static void task_queue_entry_destroy(CrustQueueEntry *entry) {
    if (entry->task || entry->scheduled) abort();
    if (pthread_mutex_destroy(&entry->mutex)) abort();
}
static void task_queue_destroy(CrustReadyQueue *queue) {
    if (!queue->closed || queue->outstanding || queue->head) abort();
    if (pthread_cond_destroy(&queue->changed)) abort();
    if (pthread_mutex_destroy(&queue->mutex)) abort();
}

/* The default cooperative scheduler has reusable workers. Blocking requests
   keep their separate launch path; native blocks never pass through this pool. */
static pthread_mutex_t task_default_mutex = PTHREAD_MUTEX_INITIALIZER;
static CrustReadyQueue task_default_queue;
enum { CRUST_MAX_POLLERS = 64 };
static pthread_t task_default_workers[CRUST_MAX_POLLERS];
static unsigned task_default_worker_count;
static int task_default_started;

static int crust_scheduler_start_poller(void) {
    if (!crust_scheduler_in_callback) crust_scheduler_violation("start_poller requires a scheduler callback");
    task_queue_lock(&task_default_mutex);
    int error = 0;
    if (!task_default_started) {
        error = task_queue_init(&task_default_queue);
        if (!error) task_default_started = 1;
    }
    if (!error && task_default_worker_count == CRUST_MAX_POLLERS) error = EAGAIN;
    if (!error) {
        error = task_pthread_launch(&task_default_workers[task_default_worker_count], 0,
                                    task_queue_worker, &task_default_queue);
        if (!error) ++task_default_worker_count;
    }
    task_queue_unlock(&task_default_mutex);
    return !error;
}

static int task_default_submit(CrustTask *task) {
    task_queue_lock(&task_default_mutex);
    if (crust_scheduler_instance && !task_default_worker_count) {
        task_queue_unlock(&task_default_mutex);
        return EAGAIN;
    }
    if (!task_default_started) {
        int error = task_queue_init(&task_default_queue);
        if (error) {
            task_queue_unlock(&task_default_mutex);
            return error;
        }
        unsigned created = 0;
        for (; created < 2; ++created) {
            error = task_pthread_launch(&task_default_workers[created], 0,
                                        task_queue_worker, &task_default_queue);
            if (error) break;
        }
        if (error) {
            if (task_queue_close(&task_default_queue)) abort();
            for (unsigned i = 0; i < created; ++i)
                if (pthread_join(task_default_workers[i], NULL)) abort();
            task_queue_destroy(&task_default_queue);
            task_queue_unlock(&task_default_mutex);
            return error;
        }
        task_default_started = 1;
        task_default_worker_count = created;
    }
    CrustWakeTicket ticket;
    int error = task_queue_submit(&task_default_queue, task->queue_entry, task, &ticket);
    task_queue_unlock(&task_default_mutex);
    return error;
}
static void task_default_wait(CrustTask *task) {
    task_queue_lock(&task_default_queue.mutex);
    while (!atomic_load_explicit(&task->worker_done, memory_order_acquire))
        if (pthread_cond_wait(&task_default_queue.changed, &task_default_queue.mutex)) abort();
    task_queue_unlock(&task_default_queue.mutex);
}
static void task_default_close(void) {
    task_queue_lock(&task_default_mutex);
    if (task_default_started) {
        if (task_queue_close(&task_default_queue)) abort();
        for (unsigned i = 0; i < task_default_worker_count; ++i)
            if (pthread_join(task_default_workers[i], NULL)) abort();
        task_queue_destroy(&task_default_queue);
        task_default_started = 0;
        task_default_worker_count = 0;
    }
    task_queue_unlock(&task_default_mutex);
}
'''

TASK_THREAD_RUNTIME += TASK_READY_QUEUE_RUNTIME

# Guard/wait primitives share the scheduler ticket implementation.
from mutex_runtime import MUTEX_RUNTIME
TASK_THREAD_RUNTIME += MUTEX_RUNTIME

TASK_SELECT_RUNTIME = r'''
/* Internal Select mechanism. Storage and branch descriptors belong to the
   enclosing state. The compiler must provide a suspended destructor for each
   branch; the ordinary release callback alone describes only inactive and
   completed states. No Select operation races with its own poll or drop.
   Event producers use persistent entries/tickets and may race with either. */
typedef struct {
    CrustTask *task;
    void (*discard_suspended)(CrustTask *);
} CrustSelectBranch;
typedef struct {
    CrustSelectBranch *branches;
    size_t count, winner;
    int started, taken, dropped;
} CrustSelect;

static void task_select_init(CrustSelect *selection,
                            CrustSelectBranch *branches, size_t count) {
    if (!count) abort();
    for (size_t i = 0; i < count; ++i) {
        CrustTask *task = branches[i].task;
        if (!task || !task->queue_entry || !branches[i].discard_suspended ||
                atomic_load(&task->state) != TASK_INACTIVE) abort();
        for (size_t j = 0; j < i; ++j)
            if (task == branches[j].task ||
                    task->queue_entry == branches[j].task->queue_entry) abort();
    }
    *selection = (CrustSelect){.branches = branches, .count = count, .winner = SIZE_MAX};
}

static void task_select_detach(CrustSelect *selection) {
    if (!selection->started) return;
    for (size_t i = 0; i < selection->count; ++i)
        if (selection->branches[i].task)
            task_external_forget(selection->branches[i].task);
}

static CrustTaskStep task_select_poll(CrustSelect *selection, CrustTask *parent) {
    if (selection->dropped || selection->taken) abort();
    if (selection->winner != SIZE_MAX) return TASK_STEP_RETURN;
    /* Register all branches before polling any one: their wake targets must
       distinguish siblings, including through chains of direct awaits. */
    for (size_t i = 0; i < selection->count; ++i) {
        CrustTask *task = selection->branches[i].task;
        if (!selection->started && task_external_register(task)) abort();
        CrustQueueEntry *entry = task->queue_entry;
        task_queue_lock(&entry->mutex);
        if (entry->task != task || entry->queue ||
                parent->wake_target.entry == entry) abort();
        entry->forward = parent->wake_target;
        task_queue_unlock(&entry->mutex);
    }
    selection->started = 1;
    for (size_t i = 0; i < selection->count; ++i) {
        CrustTask *task = selection->branches[i].task;
        /* task_poll spends readiness. Do not force a wake as for a direct
           child: an unrelated branch notification cannot make this eligible. */
        if (task_poll(task) == TASK_COMPLETE) {
            selection->winner = i;
            task_select_detach(selection);
            return TASK_STEP_RETURN;
        }
    }
    /* Yield is a readiness event for that branch. A concurrent wake received
       after this check also reaches the parent and survives its Pending. */
    for (size_t i = 0; i < selection->count; ++i) {
        CrustTask *task = selection->branches[i].task;
        task_scheduling_lock(task);
        int ready = task->ready;
        task_scheduling_unlock(task);
        if (ready) return TASK_STEP_YIELD;
    }
    return TASK_STEP_PENDING;
}

static int task_select_take(CrustSelect *selection, void *out) {
    if (selection->dropped || selection->taken || selection->winner == SIZE_MAX) return 0;
    CrustSelectBranch *branch = &selection->branches[selection->winner];
    if (!task_take(branch->task, out)) abort();
    branch->task = NULL;
    selection->taken = 1;
    return 1;
}

static int task_select_discardable(CrustSelect *selection) {
    if (selection->dropped) return 0;
    for (size_t i = 0; i < selection->count; ++i)
        if (selection->branches[i].task &&
                !task_owned_discardable(selection->branches[i].task)) return 0;
    return 1;
}

static void task_select_drop(CrustSelect *selection) {
    if (selection->dropped) abort();
    /* Revoke routes before any frame can be released. Concurrent producers
       can then only notify a persistent entry with an obsolete generation. */
    task_select_detach(selection);
    for (size_t i = selection->count; i > 0; --i) {
        CrustSelectBranch *branch = &selection->branches[i - 1];
        CrustTask *task = branch->task;
        if (!task) continue;
        CrustTaskState state = atomic_load(&task->state);
        if ((state != TASK_INACTIVE && state != TASK_SUSPENDED && state != TASK_COMPLETE) ||
                !task_consume(task, state)) abort();
        if (state == TASK_SUSPENDED) branch->discard_suspended(task);
        else task->ops->release(task);
        branch->task = NULL;
    }
    selection->dropped = 1;
}
'''

TASK_ASYNC_THREAD_RUNTIME = r'''
/* The worker only accesses its own stable task slot. It publishes
   completion as its last access, so the parent handle can disappear. */
typedef struct {
    CrustTask *task;
    int error;
} CrustAsyncExecution;

/* Transfer the wait obligation to a synchronous ABI without waiting or
   submitting the task again. Async-native workers are already detached;
   all workers publish worker_done through the shared completion protocol. */
static void task_sync_adopt(CrustExecution *target, CrustAsyncExecution *source) {
    *target = (CrustExecution){0};
    target->task = source->task;
    target->error = source->error;
    target->pooled = 1;
    atomic_init(&target->joined, 0);
    source->task = NULL;
    source->error = 0;
}

/* Consume a synchronous handle without waiting for its worker. The worker
   publishes completion through the task slot, so the async waiter uses the
   same notification protocol as a handle created directly in an async body. */
static void task_async_adopt(CrustAsyncExecution *target, CrustExecution *source) {
    if (atomic_exchange(&source->joined, 1)) abort();
    if (!source->error && !source->pooled &&
            (!source->detach || source->detach(source->thread))) abort();
    target->task = source->task;
    target->error = source->error;
    source->task = NULL;
    source->error = 0;
}

static void task_start_detached(CrustAsyncExecution *execution, CrustTask *task,
        int (*launch)(pthread_t *, int, void *(*)(void *), void *), void *(*run)(void *)) {
    CrustTaskState inactive = TASK_INACTIVE;
    if (!atomic_compare_exchange_strong(&task->state, &inactive, TASK_QUEUED)) abort();
    execution->task = task;
    pthread_t thread;
    int error = task_external_register(task);
    if (!error) error = launch ? launch(&thread, 1, run, task) : ENOTSUP;
    execution->error = error;
    if (error) {
        task_external_forget(task);
        atomic_store(&task->state, TASK_INACTIVE);
        if (!task_drop_inactive(task)) abort();
        execution->task = NULL;
    }
}

static void task_async_start_mode(CrustAsyncExecution *execution, CrustTask *task,
                                  const CrustThreadScheduler *scheduler, int blocking) {
    if (scheduler == &task_default_scheduler) {
        int error = crust_scheduler_dispatch(blocking);
        if (error) {
            if (!task_drop_inactive(task)) abort();
            execution->error = error;
            execution->task = NULL;
            return;
        }
    }
    if (scheduler == &task_default_scheduler && !blocking && task->queue_entry) {
        execution->task = task;
        int error = task_default_submit(task);
        execution->error = error;
        if (error) {
            if (!task_drop_inactive(task)) abort();
            execution->task = NULL;
        }
        return;
    }
    task_start_detached(execution, task,
        blocking ? scheduler->launch_blocking : scheduler->launch, task_thread_run);
}

static void task_native_async_start(CrustAsyncExecution *execution, CrustTask *task) {
    atomic_store(&crust_scheduler_launch_seen, 1);
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

static CrustTaskStep task_async_subscribe(const CrustAsyncExecution *execution, CrustTask *parent) {
    return execution->error || !execution->task ? TASK_STEP_YIELD : task_subscribe(execution->task, parent);
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

'''

TASK_RUNTIME = UTF8_VALUE_TYPES_C + TASK_RUNTIME_BODY

TASK_POOL_RUNTIME = r'''
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
'''
