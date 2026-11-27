// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_TASKS_HPP
#define CORBO_CPP_TASKS_HPP
// Plain task records and explicit callbacks. No C++ coroutines, futures or RAII.
struct corbo_task;
struct corbo_task_arena;
struct corbo_task_value { corbo_task *state; };
struct corbo_context { corbo_task *task; corbo_waker waker; };
struct corbo_task {
    corbo_task_arena *arena;
    corbo_datastack stack;
    corbo_region_band *regions, *default_regions, *regional_root;
    corbo_task *registry_next, *queue_next;
    corbo_wait_queue waiters;
    // One outstanding child wait per suspended poll frame. Corbo executes a
    // poll sequentially, so the registration is stable until that await is
    // resumed or completed.
    corbo_waiter child_waiter;
    bool (*poll)(corbo_task *, corbo_context *);
    bool (*generated_poll)(void *, void *, corbo_context *);
    void (*destroy)(corbo_task *);
    void (*state_destroy)(void *);
    uint64_t id;
    size_t refs, program_counter, state_offset;
    void *result;
    bool started, running, queued, notified, waiting, done, failed, result_live, state_consumed;
};
// Frames of equal extent share a growing region, with intrusive hole reuse.
// This keeps a loop of small futures from reserving one maximum region per task.
struct corbo_task_arena {
    corbo_datastack registration;
    corbo_region frames;
    corbo_task_arena *next;
    corbo_task *free_head;
    size_t live;
};
struct corbo_scheduler {
    corbo_band_lock lock;
    corbo_condition ready;
    corbo_task *registry, *head, *tail;
    corbo_task_arena *arenas;
    uint64_t next_id;
    size_t workers, active, disposing;
    bool stopping;
};
inline corbo_scheduler corbo_tasks;
inline bool corbo_tasks_initialized;
#if defined(_WIN32)
inline INIT_ONCE corbo_tasks_once = INIT_ONCE_STATIC_INIT;
static BOOL CALLBACK corbo_tasks_initialize(PINIT_ONCE, PVOID, PVOID *) {
    corbo_band_lock_init(&corbo_tasks.lock); corbo_condition_init(&corbo_tasks.ready);
    corbo_tasks_initialized = true; return TRUE;
}
static inline void corbo_tasks_init() { if (!InitOnceExecuteOnce(&corbo_tasks_once, corbo_tasks_initialize, NULL, NULL)) corbo_fail("corbo: scheduler initialization failed"); }
#else
inline pthread_once_t corbo_tasks_once = PTHREAD_ONCE_INIT;
static void corbo_tasks_initialize() {
    corbo_band_lock_init(&corbo_tasks.lock); corbo_condition_init(&corbo_tasks.ready);
    corbo_tasks_initialized = true;
}
static inline void corbo_tasks_init() { if (pthread_once(&corbo_tasks_once, corbo_tasks_initialize)) corbo_fail("corbo: scheduler initialization failed"); }
#endif
static inline void corbo_task_enqueue(corbo_task *task) {
    if (task->queued || task->running || task->done) return;
    task->queue_next = NULL; task->queued = true;
    if (corbo_tasks.tail != NULL) corbo_tasks.tail->queue_next = task; else corbo_tasks.head = task;
    corbo_tasks.tail = task; corbo_condition_broadcast(&corbo_tasks.ready);
}
// A wake carries an identity, never a pointer to a potentially released frame.
static void corbo_task_wake(void *, uint64_t id) {
    corbo_tasks_init(); corbo_band_acquire(&corbo_tasks.lock);
    for (corbo_task *task = corbo_tasks.registry; task != NULL; task = task->registry_next) {
        if (task->id != id || task->done) continue;
        task->notified = true; task->waiting = false;
        if (task->started) corbo_task_enqueue(task);
        corbo_condition_broadcast(&corbo_tasks.ready);
        break;
    }
    corbo_band_release(&corbo_tasks.lock);
}
static inline corbo_task *corbo_task_allocate(size_t bytes, bool (*poll)(corbo_task *, corbo_context *), void (*destroy)(corbo_task *), void (*initialize)(void *)) {
    if (bytes < sizeof(corbo_task)) corbo_fail("corbo: invalid task frame extent");
    bytes = corbo_aligned_extent(bytes, alignof(max_align_t));
    corbo_tasks_init(); corbo_band_acquire(&corbo_tasks.lock);
    corbo_region_band *band = corbo_current_band != NULL ? corbo_current_band : corbo_global_band;
    corbo_task_arena *arena = corbo_tasks.arenas;
    while (arena != NULL && (arena->frames.band != band || arena->frames.width != bytes
        || (arena->free_head == NULL && arena->frames.len == arena->frames.maximum / bytes))) arena = arena->next;
    if (arena == NULL) {
        corbo_datastack registration = {}; corbo_datastack_open(&registration, sizeof(corbo_task_arena));
        arena = ::new(corbo_datastack_alloc(&registration, sizeof(corbo_task_arena), alignof(corbo_task_arena))) corbo_task_arena{};
        arena->registration = registration; corbo_region_init(&arena->frames, bytes, NULL);
        arena->next = corbo_tasks.arenas; corbo_tasks.arenas = arena;
    }
    corbo_task *task;
    if (arena->free_head != NULL) {
        task = arena->free_head; arena->free_head = task->queue_next;
        corbo_counter_sub(&arena->frames.band->mapping.record->unused, bytes);
    } else { task = (corbo_task *)corbo_region_append(&arena->frames, 1); }
    ++arena->live;
    memset(task, 0, bytes);
    if (initialize != NULL) initialize(task);
    task->arena = arena; task->regions = arena->frames.band; task->regional_root = arena->frames.band; task->poll = poll; task->destroy = destroy; task->refs = 1;
    if (++corbo_tasks.next_id == 0) corbo_fail("corbo: task identity space exhausted");
    task->id = corbo_tasks.next_id;
    task->registry_next = corbo_tasks.registry; corbo_tasks.registry = task;
    corbo_band_release(&corbo_tasks.lock); return task;
}
static inline bool corbo_generated_task_poll(corbo_task *task, corbo_context *context) {
    void *state = (uint8_t *)task + task->state_offset;
    bool done = task->generated_poll(state, task->result, context);
    if (done) task->state_consumed = true;
    return done;
}
static inline void corbo_generated_task_destroy(corbo_task *task) {
    if (!task->state_consumed && task->state_destroy != NULL)
        task->state_destroy((uint8_t *)task + task->state_offset);
}
static inline corbo_task *corbo_task_from_future(
    const void *source, size_t state_bytes, size_t state_alignment,
    size_t result_bytes,
    bool (*poll)(void *, void *, corbo_context *),
    void (*state_destroy)(void *)) {
    size_t state_offset = corbo_aligned_extent(sizeof(corbo_task), state_alignment);
    size_t result_offset = corbo_aligned_extent(state_offset + state_bytes, alignof(max_align_t));
    if (result_offset > SIZE_MAX - result_bytes) corbo_fail("corbo: task frame size overflow");
    corbo_task *task = corbo_task_allocate(result_offset + result_bytes,
        corbo_generated_task_poll, corbo_generated_task_destroy, NULL);
    task->generated_poll = poll; task->state_destroy = state_destroy;
    task->state_offset = state_offset;
    task->result = (uint8_t *)task + result_offset;
    if (state_bytes != 0) memcpy((uint8_t *)task + state_offset, source, state_bytes);
    return task;
}
// Save/restore the worker's TLS explicitly. A suspended frame owns its cursor
// and region context, so a later poll may run on another native worker.
static inline bool corbo_task_poll(corbo_task *task) {
    corbo_datastack previous = corbo_fixed_stack;
    corbo_region_band *regions = corbo_current_band, *defaults = corbo_global_band, *floor = corbo_region_floor;
    corbo_fixed_stack = task->stack; corbo_current_band = task->regions; corbo_global_band = task->default_regions; corbo_region_floor = task->regional_root;
    if (corbo_fixed_stack.base == NULL) corbo_stack_open(0);
    corbo_context context = {task, {NULL, task->id, corbo_task_wake}};
    bool done = task->poll(task, &context);
    task->stack = corbo_fixed_stack; task->regions = corbo_current_band; task->default_regions = corbo_global_band;
    corbo_fixed_stack = previous; corbo_current_band = regions; corbo_global_band = defaults; corbo_region_floor = floor;
    return done;
}
static inline void corbo_task_dispose(corbo_task *task) {
    corbo_datastack previous = corbo_fixed_stack;
    corbo_region_band *regions = corbo_current_band, *defaults = corbo_global_band, *floor = corbo_region_floor;
    corbo_fixed_stack = task->stack; corbo_current_band = task->regions; corbo_global_band = task->default_regions; corbo_region_floor = task->regional_root;
    if (corbo_fixed_stack.base == NULL) corbo_stack_open(0);
    task->destroy(task);
    corbo_regions_close(); corbo_stack_close();
    corbo_fixed_stack = previous; corbo_current_band = regions; corbo_global_band = defaults; corbo_region_floor = floor;
    corbo_band_acquire(&corbo_tasks.lock);
    corbo_task_arena *arena = task->arena;
    if (--arena->live == 0) {
        corbo_task_arena **link = &corbo_tasks.arenas;
        while (*link != NULL && *link != arena) link = &(*link)->next;
        if (*link == NULL) corbo_fail("corbo: task arena registry mismatch");
        *link = arena->next;
        // Remove hole corrections before returning the entire region extent.
        corbo_counter_sub(&arena->frames.band->mapping.record->unused, (arena->frames.len - 1) * arena->frames.width);
        corbo_region_drop(&arena->frames);
        corbo_datastack registration = arena->registration;
        corbo_datastack_close(&registration);
    } else {
        corbo_counter_add(&arena->frames.band->mapping.record->unused, arena->frames.width);
        task->queue_next = arena->free_head; arena->free_head = task;
    }
    --corbo_tasks.disposing; corbo_condition_broadcast(&corbo_tasks.ready);
    corbo_band_release(&corbo_tasks.lock);
}
// Caller holds the scheduler lock. Remove the registry node before releasing
// its final owner, so a late OS wake cannot resolve a freed identity.
static inline bool corbo_task_unref_locked(corbo_task *task) {
    if (task->refs == 0) corbo_fail("corbo: duplicate task owner release");
    if (--task->refs != 0) return false;
    corbo_task **link = &corbo_tasks.registry;
    while (*link != NULL && *link != task) link = &(*link)->registry_next;
    if (*link == NULL) corbo_fail("corbo: task registry mismatch");
    *link = task->registry_next; ++corbo_tasks.disposing; return true;
}
static inline void corbo_task_release(corbo_task *task) {
    if (task == NULL) return;
    corbo_band_acquire(&corbo_tasks.lock); bool dispose = corbo_task_unref_locked(task); corbo_band_release(&corbo_tasks.lock);
    if (dispose) corbo_task_dispose(task);
}
static inline void corbo_task_complete(corbo_task *task) {
    // Publish after all poll writes, then wake waiters using ID snapshots.
    corbo_band_acquire(&corbo_tasks.lock); task->running = false; task->done = true;
    while (task->waiters.head != NULL) {
        corbo_waker wake = corbo_wait_one(&task->waiters);
        corbo_band_release(&corbo_tasks.lock); corbo_notify(wake); corbo_band_acquire(&corbo_tasks.lock);
    }
    --corbo_tasks.active; bool dispose = corbo_task_unref_locked(task);
    corbo_condition_broadcast(&corbo_tasks.ready); corbo_band_release(&corbo_tasks.lock);
    if (dispose) corbo_task_dispose(task);
}
#if defined(_WIN32)
static DWORD WINAPI corbo_task_worker(void *) {
#else
static void *corbo_task_worker(void *) {
#endif
    corbo_band_acquire(&corbo_tasks.lock);
    for (;;) {
        while (corbo_tasks.head == NULL && !corbo_tasks.stopping) corbo_condition_wait(&corbo_tasks.ready, &corbo_tasks.lock);
        if (corbo_tasks.head == NULL) break;
        corbo_task *task = corbo_tasks.head;
        corbo_tasks.head = task->queue_next; if (corbo_tasks.head == NULL) corbo_tasks.tail = NULL;
        task->queued = false; task->running = true; task->notified = false; task->waiting = false;
        corbo_band_release(&corbo_tasks.lock);
        bool done = corbo_task_poll(task);
        if (done) corbo_task_complete(task);
        else {
            corbo_band_acquire(&corbo_tasks.lock); task->running = false;
            if (!task->waiting || task->notified) corbo_task_enqueue(task);
            corbo_band_release(&corbo_tasks.lock);
        }
        corbo_band_acquire(&corbo_tasks.lock);
    }
    --corbo_tasks.workers; corbo_condition_broadcast(&corbo_tasks.ready); corbo_band_release(&corbo_tasks.lock);
#if defined(_WIN32)
    return 0;
#else
    return NULL;
#endif
}
static inline bool corbo_start_worker() {
#if defined(_WIN32)
    HANDLE thread = CreateThread(NULL, 0, corbo_task_worker, NULL, 0, NULL);
    if (thread == NULL) return false; CloseHandle(thread);
#else
    pthread_t thread;
    if (pthread_create(&thread, NULL, corbo_task_worker, NULL)) return false;
    if (pthread_detach(thread)) corbo_fail("corbo: worker detach failed");
#endif
    ++corbo_tasks.workers; return true;
}
static inline void corbo_task_spawn(corbo_task *task) {
    corbo_tasks_init(); corbo_band_acquire(&corbo_tasks.lock);
    if (task->started) corbo_fail("corbo: task launched twice");
    task->started = true;
    if (corbo_tasks.workers == 0) {
#if defined(_WIN32)
        SYSTEM_INFO info = {}; GetSystemInfo(&info); size_t desired = info.dwNumberOfProcessors;
#else
        long cores = sysconf(_SC_NPROCESSORS_ONLN); size_t desired = cores > 0 ? (size_t)cores : 1;
#endif
        for (size_t at = 0; at < desired; ++at) if (!corbo_start_worker()) break;
    }
    if (corbo_tasks.workers == 0) { task->failed = true; task->done = true; }
    else { ++task->refs; ++corbo_tasks.active; corbo_task_enqueue(task); }
    corbo_band_release(&corbo_tasks.lock);
}
// Dedicated native workers execute blocking Corbo bodies outside the poll queue.
#if defined(_WIN32)
static DWORD WINAPI corbo_blocking_worker(void *raw) {
#else
static void *corbo_blocking_worker(void *raw) {
#endif
    corbo_task *task = (corbo_task *)raw;
    for (;;) {
        if (corbo_task_poll(task)) break;
        corbo_band_acquire(&corbo_tasks.lock);
        while (task->waiting && !task->notified) corbo_condition_wait(&corbo_tasks.ready, &corbo_tasks.lock);
        task->notified = false;
        corbo_band_release(&corbo_tasks.lock);
    }
    corbo_task_complete(task);
#if defined(_WIN32)
    return 0;
#else
    return NULL;
#endif
}
static inline void corbo_task_thread(corbo_task *task) {
    corbo_tasks_init(); corbo_band_acquire(&corbo_tasks.lock);
    if (task->started) corbo_fail("corbo: task launched twice");
    task->started = true; task->running = true; ++task->refs; ++corbo_tasks.active;
#if defined(_WIN32)
    HANDLE thread = CreateThread(NULL, 0, corbo_blocking_worker, task, 0, NULL);
    bool failed = thread == NULL;
    if (!failed) CloseHandle(thread);
#else
    pthread_t thread;
    bool failed = pthread_create(&thread, NULL, corbo_blocking_worker, task) != 0;
    if (!failed && pthread_detach(thread)) corbo_fail("corbo: blocking worker detach failed");
#endif
    if (failed) {
        task->running = false; task->failed = true; task->done = true;
        --task->refs; --corbo_tasks.active; corbo_condition_broadcast(&corbo_tasks.ready);
    }
    corbo_band_release(&corbo_tasks.lock);
}
// Pollers publish parking intent under the same lock as wake(id). A wake
// arriving during readiness registration remains remembered by notified.
static inline void corbo_task_parking(corbo_context *context, bool waiting) {
    corbo_band_acquire(&corbo_tasks.lock);
    context->task->waiting = waiting && !context->task->notified;
    corbo_band_release(&corbo_tasks.lock);
}
// Completion registration and the done check share one lock. No wake can be
// lost between observing Pending and parking the parent poll.
static inline bool corbo_task_await(corbo_task *child, corbo_context *context, corbo_waiter *waiter) {
    if (!child->started) corbo_task_spawn(child);
    corbo_band_acquire(&corbo_tasks.lock);
    bool ready = child->done;
    if (!ready) {
        waiter->waker = context->waker; corbo_wait_append(&child->waiters, waiter);
        context->task->waiting = true;
    } else { corbo_wait_remove(&child->waiters, waiter); }
    corbo_band_release(&corbo_tasks.lock); return ready;
}
static inline void corbo_task_join(corbo_task *task) {
    corbo_band_acquire(&corbo_tasks.lock);
    if (!task->started) corbo_fail("corbo: join requires a launched task");
    while (!task->done) corbo_condition_wait(&corbo_tasks.ready, &corbo_tasks.lock);
    corbo_band_release(&corbo_tasks.lock);
}
static inline void corbo_tasks_shutdown() {
    if (!corbo_tasks_initialized) return;
    corbo_band_acquire(&corbo_tasks.lock);
    while (corbo_tasks.active != 0 || corbo_tasks.disposing != 0) corbo_condition_wait(&corbo_tasks.ready, &corbo_tasks.lock);
    corbo_tasks.stopping = true; corbo_condition_broadcast(&corbo_tasks.ready);
    while (corbo_tasks.workers != 0) corbo_condition_wait(&corbo_tasks.ready, &corbo_tasks.lock);
    corbo_band_release(&corbo_tasks.lock);
}
#endif
