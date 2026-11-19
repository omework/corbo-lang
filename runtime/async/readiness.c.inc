/** @file readiness.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
/* Unix readiness registrations are indexed by a cohort token, never a Task address.
 * All state transitions and interest updates run under task_lock. */
static pthread_once_t socket_once = PTHREAD_ONCE_INIT;
static int64_t socket_queue = -1, socket_init_error = -1;
static Task *socket_waiters;
static uintptr_t socket_serial;

/** Combines active reader/writer interests for one socket generation; caller holds the scheduler lock. */
static unsigned socket_interest(uintptr_t token) {
    unsigned mask = 0;
    for (Task *p = socket_waiters; p; p = p->io_next)
        if (p->io_token == token) mask |= p->io_write ? 2u : 1u;
    return mask;
}

/* Detach before publishing: a resumed task may immediately release its frame. */
/** Publishes a socket readiness/error to one waiter and resumes its parked root; caller holds the scheduler lock. */
static void socket_signal(uintptr_t token, unsigned mask, int64_t status) {
    Task **link = &socket_waiters;
    while (*link) {
        Task *child = *link;
        if (child->io_token != token || !(mask & (child->io_write ? 2u : 1u))) {
            link = &child->io_next;
            continue;
        }
        *link = child->io_next;
        child->io_next = NULL;
        child->io_error = status;
        child->io_ready = true;
        Task *root = child->root ? child->root : child;
        root->waiting = false;
        if (root->parked) {
            root->parked = false;
            if (!root->blocking) task_enqueue(root);
        }
    }
    pthread_cond_broadcast(&task_ready);
}

/* Dispatch by generation while holding the registry lock for detach/rearm. */
/** Detaches matching waiters, publishes readiness and rearms remaining interests; ignores stale generation tokens. */
static void socket_dispatch(uintptr_t event) {
    uintptr_t token = event & ~(uintptr_t)3;
    unsigned mask = (unsigned)(event & 3);
    if (!token || !mask) return;
    pthread_mutex_lock(&task_lock);
    Task *first = socket_waiters;
    while (first && first->io_token != token) first = first->io_next;
    if (first) {
        uint64_t descriptor = first->io_socket;
        socket_signal(token, mask, 0);
        unsigned remaining = socket_interest(token);
        int64_t status = corbo_queue_watch(socket_queue, descriptor, remaining,
                           remaining ? token : 0);
        if (status < 0 && remaining) socket_signal(token, 3, status);
    }
    /* Stale queued events have no matching cohort and cannot dereference a freed frame. */
    pthread_mutex_unlock(&task_lock);
}

/** Waits on the platform readiness queue and dispatches returned events under the scheduler lock. */
static void *socket_events(void *unused) {
    (void)unused;
    if (!base) { reserve(1); worker_regions(); }
    for (;;) socket_dispatch(corbo_queue_wait(socket_queue));
    return NULL;
}

/** Creates the readiness queue and its detached event thread once; records initialization failure for future waits. */
static void socket_initialize(void) {
    socket_queue = corbo_queue_create();
    if (socket_queue < 0) { socket_init_error = socket_queue; return; }
    pthread_t worker;
    int status = pthread_create(&worker, NULL, socket_events, NULL);
    if (status) {
        socket_init_error = -(int64_t)status;
        close((int)socket_queue);
        socket_queue = -1;
        return;
    }
    pthread_detach(worker);
    socket_init_error = 0;
}

/** Registers one task wait for socket readability or writability without losing an intervening wake; returns readiness or a platform error. */
static bool corbo_socket_wait(Task *child, uint64_t descriptor, bool write, int64_t *out) {
    pthread_once(&socket_once, socket_initialize);
    if (socket_init_error) { *out = socket_init_error; return true; }
    Task *root = child->root ? child->root : child;
    pthread_mutex_lock(&task_lock);
    if (child->io_registered && child->io_ready) {
        child->io_registered = false;
        child->io_ready = false;
        *out = child->io_error;
        pthread_mutex_unlock(&task_lock);
        return true;
    }
    root->waiting = true;
    if (!child->io_registered) {
        uintptr_t token = 0;
        for (Task *p = socket_waiters; p; p = p->io_next)
            if (p->io_socket == descriptor) { token = p->io_token; break; }
        if (!token) {
            if (socket_serial >= UINTPTR_MAX / 4) {
                fputs("corbo: reactor token budget exhausted\n", stderr);
                exit(EXIT_FAILURE);
            }
            token = ++socket_serial * 4;
        }
        child->io_socket = descriptor;
        child->io_write = write;
        child->io_token = token;
        child->io_error = 0;
        child->io_ready = false;
        child->io_registered = true;
        child->io_next = socket_waiters;
        socket_waiters = child;
        int64_t status = corbo_queue_watch(socket_queue, descriptor, socket_interest(token), token);
        if (status < 0) {
            socket_signal(token, 3, status);
            child->io_registered = false;
            child->io_ready = false;
            *out = status;
            pthread_mutex_unlock(&task_lock);
            return true;
        }
    }
    pthread_mutex_unlock(&task_lock);
    return false;
}
