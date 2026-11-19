/** @file completion.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
/* Each overlapped operation owns its request and its waiting task until dequeue. */
static pthread_once_t completion_once = PTHREAD_ONCE_INIT;
static uintptr_t completion_port;
static int64_t completion_init_error = -8;

/** Receives per-operation completion records and resumes their task roots under the scheduler lock. */
static void *completion_events(void *unused) {
    (void)unused;
    if (!base) { reserve(1); worker_regions(); }
    for (;;) {
        uintptr_t address = corbo_completion_next(completion_port);
        if (!address) continue;
        uint64_t *request = (uint64_t *)address;
        pthread_mutex_lock(&task_lock);
        Task *child = (Task *)(uintptr_t)request[4];
        if (child && child->io_registered && child->io_token == address) {
            request[4] = 0;
            child->io_ready = true;
            Task *root = child->root ? child->root : child;
            root->waiting = false;
            if (root->parked) {
                root->parked = false;
                if (!root->blocking) task_enqueue(root);
            }
            pthread_cond_broadcast(&task_ready);
        }
        pthread_mutex_unlock(&task_lock);
    }
    return NULL;
}

/** Creates the completion port and its event thread once, recording initialization errors. */
static void completion_initialize(void) {
    completion_port = corbo_completion_create();
    if (!completion_port) return;
    pthread_t worker;
    if (pthread_create(&worker, NULL, completion_events, NULL) != 0) {
#ifdef _WIN32
        CloseHandle((HANDLE)completion_port);
#endif
        completion_port = 0;
        return;
    }
    pthread_detach(worker);
    completion_init_error = 0;
}

/** Associates a socket with the runtime completion port and returns the platform status. */
static int64_t corbo_socket_attach(uint64_t descriptor) {
    pthread_once(&completion_once, completion_initialize);
    if (completion_init_error) return completion_init_error;
    return corbo_completion_attach(completion_port, descriptor);
}

/** Submits or observes one operation-specific completion request and coordinates its task wakeup without sharing request state. */
static bool corbo_socket_complete(Task *child, uint64_t descriptor,
                                  uintptr_t address, int64_t *out) {
    pthread_once(&completion_once, completion_initialize);
    if (completion_init_error) { *out = completion_init_error; return true; }
    Task *root = child->root ? child->root : child;
    pthread_mutex_lock(&task_lock);
    if (child->io_registered && child->io_ready) {
        child->io_registered = child->io_ready = false;
        *out = 0;
        pthread_mutex_unlock(&task_lock);
        return true;
    }
    root->waiting = true;
    if (!child->io_registered) {
        uint64_t *request = (uint64_t *)address;
        request[4] = (uintptr_t)child;
        request[5] = descriptor;
        child->io_token = address;
        child->io_registered = true;
        child->io_ready = false;
        int64_t status = corbo_completion_submit(address);
        if (status < 0) {
            request[4] = 0;
            child->io_registered = false;
            root->waiting = false;
            *out = status;
            pthread_mutex_unlock(&task_lock);
            return true;
        }
    }
    pthread_mutex_unlock(&task_lock);
    return false;
}
