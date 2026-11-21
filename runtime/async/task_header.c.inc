/** @file scheduler.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
#include <pthread.h>
#include <stdbool.h>

/** Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock. */
typedef struct Task Task;
/** Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock. */
struct Task {
    /** pc: resume-state program counter. */
    size_t pc;
    /** poll: typed poll/clear callback. */
    bool (*poll)(Task *, bool);
    /** next: ready-queue next link. */
    Task *next;
    /** failed: launch-failure flag. */
    bool failed;
    /** done: completion-publication flag. */
    bool done;
    /** abandoned: worker-owned final-cleanup flag. */
    bool abandoned;
    /** discard: typed abandoned-task cleanup callback. */
    void (*discard)(Task *);
    /** root: outer polling-root link. waiter: dependent polling-root link. */
    Task *root, *waiter;
    /** io_ready: readiness-publication flag. io_registered: active-wait registration flag. */
    bool io_ready, io_registered;
    /** io_socket: native socket identifier. */
    uint64_t io_socket;
    /** io_write: write-interest selector. */
    bool io_write;
    /** io_next: intrusive readiness-waiter link. */
    Task *io_next;
    /** io_token: readiness-generation token. */
    uintptr_t io_token;
    /** io_error: recorded platform I/O status. */
    int64_t io_error;
    /** waiting: dependency-wait predicate. parked: removed-from-ready-queue flag. blocking: dedicated blocking-worker flag. */
    bool waiting, parked, blocking;
    /** mutex_next: next waiter in a mutex FIFO, protected by task_lock. */
    Task *mutex_next;
    /** mutex_owner: logical async mutex currently retaining this waiter. */
    uintptr_t mutex_owner;
    /** mutex_reserved: release handed this waiter the next acquisition. */
    bool mutex_reserved;
};
static pthread_t task_workers[2];
static size_t task_worker_count;
static pthread_mutex_t task_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t task_ready = PTHREAD_COND_INITIALIZER;
static Task *task_head;
static Task **task_tail = &task_head;
static bool task_attempted, task_stopping;
static size_t task_active;

/** Links a task at the queue tail; caller holds the scheduler lock and the task is not already queued. */
static void task_enqueue(Task *task) {
    task->next = NULL;
    *task_tail = task;
    task_tail = &task->next;
}
