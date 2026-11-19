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
/* Called with the scheduler lock held. Pollers publish completion once. */
/** Publishes completion and wakes or enqueues a waiting root exactly through the locked scheduler transition. */
static void task_publish(Task *task) {
    task->done = true;
    Task *waiter = task->waiter;
    if (waiter) {
        waiter->waiting = false;
        if (waiter->parked) {
            waiter->parked = false;
            if (!waiter->blocking) task_enqueue(waiter);
        }
    }
    pthread_cond_broadcast(&task_ready);
}

/** Registers the current root as child's waiter if unfinished; returns whether completion was already visible under the lock. */
static inline __attribute__((unused)) bool task_await(Task *child, Task *current) {
    Task *root = current->root ? current->root : current;
    pthread_mutex_lock(&task_lock);
    bool ready = child->done;
    if (!ready) {
        child->waiter = root;
        root->waiting = true;
    }
    pthread_mutex_unlock(&task_lock);
    return ready;
}

/** Consumes queued tasks, polls outside the lock, then publishes, parks or requeues them; releases its thread-local stack on exit. */
static void *task_poll_worker(void *unused) {
    (void)unused; if (!base) reserve(1);
    pthread_mutex_lock(&task_lock);
    for (;;) {
        while (!task_head && !task_stopping) pthread_cond_wait(&task_ready, &task_lock);
        if (!task_head) break;
        Task *task = task_head;
        task_head = task->next;
        if (!task_head) task_tail = &task_head;
        pthread_mutex_unlock(&task_lock);
        bool done = task->poll(task, false);
        pthread_mutex_lock(&task_lock);
        if (done) {
            task_publish(task);
            if (task->abandoned) {
                void (*discard)(Task *) = task->discard;
                pthread_mutex_unlock(&task_lock);
                discard(task);
                pthread_mutex_lock(&task_lock);
            }
            --task_active;
        } else if (task->waiting) task->parked = true;
        else task_enqueue(task);
        pthread_cond_broadcast(&task_ready);
    }
    pthread_mutex_unlock(&task_lock);
    if (base) release();
    return NULL;
}
/** Initializes a task and starts poll workers once; enqueues it or records launch failure and clears captures if no worker starts. */
static void task_spawn_with(Task *task, bool (*poll)(Task *, bool), void (*discard)(Task *)) {
    *task = (Task){ .poll = poll, .discard = discard };
    pthread_mutex_lock(&task_lock);
    if (!task_attempted) {
        task_attempted = true;
        for (size_t i = 0; i < sizeof(task_workers) / sizeof(*task_workers); ++i)
            if (pthread_create(&task_workers[task_worker_count], NULL, task_poll_worker, NULL) == 0)
                ++task_worker_count;
    }
    if (task_worker_count == 0) {
        pthread_mutex_unlock(&task_lock);
        task->failed = true;
        task->poll(task, true);
        task->done = true;
        return;
    }
    ++task_active;
    task_enqueue(task);
    pthread_cond_broadcast(&task_ready);
    pthread_mutex_unlock(&task_lock);
}
/** Schedules a task without an abandonment callback; its caller must preserve the frame through completion. */
void task_spawn(Task *task, bool (*poll)(Task *, bool)) {
    task_spawn_with(task,poll,NULL);
}
/** Blocks the current thread on the scheduler condition until the task is done. */
void task_join(Task *task) {
    pthread_mutex_lock(&task_lock);
    while (!task->done) pthread_cond_wait(&task_ready, &task_lock);
    pthread_mutex_unlock(&task_lock);
}
/** Drains active scheduled tasks, signals shutdown and joins every poll worker. */
void task_end(void) {
    if (task_worker_count == 0) return;
    pthread_mutex_lock(&task_lock);
    while (task_active) pthread_cond_wait(&task_ready, &task_lock);
    task_stopping = true;
    pthread_cond_broadcast(&task_ready);
    pthread_mutex_unlock(&task_lock);
    for (size_t i = 0; i < task_worker_count; ++i)
        if (pthread_join(task_workers[i], NULL) != 0) abort();
}
