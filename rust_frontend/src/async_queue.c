static CRUST_LOCAL CrustHandle *crust_poll_root;
static pthread_once_t crust_async_init = PTHREAD_ONCE_INIT;
static pthread_mutex_t crust_async_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t crust_async_ready = PTHREAD_COND_INITIALIZER;
static CrustHandle *crust_async_first;
static CrustHandle **crust_async_tail = &crust_async_first;
static unsigned crust_async_workers;

static void crust_async_enqueue(CrustHandle *handle) {
    pthread_mutex_lock(&crust_async_lock);
    handle->queued_next = NULL;
    *crust_async_tail = handle;
    crust_async_tail = &handle->queued_next;
    pthread_cond_signal(&crust_async_ready);
    pthread_mutex_unlock(&crust_async_lock);
}

static void *crust_async_worker(void *unused) {
    (void)unused;
    for (;;) {
        pthread_mutex_lock(&crust_async_lock);
        while (crust_async_first == NULL)
            pthread_cond_wait(&crust_async_ready, &crust_async_lock);
        CrustHandle *handle = crust_async_first;
        crust_async_first = handle->queued_next;
        if (crust_async_first == NULL)
            crust_async_tail = &crust_async_first;
        pthread_mutex_unlock(&crust_async_lock);
        crust_poll_root = handle;
        bool done = handle->poll(handle);
        crust_poll_root = NULL;
        if (done) {
            crust_thread_complete(handle);
        } else {
            pthread_mutex_lock(&crust_threads_lock);
            bool parked = handle->waiting;
            handle->parked = parked;
            pthread_mutex_unlock(&crust_threads_lock);
            if (!parked)
                crust_async_enqueue(handle);
        }
    }
    return NULL;
}

static void crust_async_start_workers(void) {
    for (unsigned index = 0; index < 2; ++index) {
        pthread_t worker;
        if (pthread_create(&worker, NULL, crust_async_worker, NULL) == 0) {
            if (pthread_detach(worker) != 0)
                crust_thread_fatal();
            ++crust_async_workers;
        }
    }
}

static inline __attribute__((unused)) CrustHandle *crust_future_spawn(CrustHandle *handle) {
    pthread_once(&crust_async_init, crust_async_start_workers);
    if (crust_async_workers == 0) {
        crust_thread_drop(handle);
        return NULL;
    }
    atomic_init(&handle->status, CRUST_RUNNING);
    handle->scheduled = true;
    crust_thread_started();
    crust_async_enqueue(handle);
    return handle;
}

static void *crust_async_blocking_worker(void *argument) {
    CrustHandle *handle = argument;
    crust_poll_root = handle;
    while (!handle->poll(handle)) {
        pthread_mutex_lock(&crust_threads_lock);
        while (handle->waiting)
            pthread_cond_wait(&crust_threads_idle, &crust_threads_lock);
        pthread_mutex_unlock(&crust_threads_lock);
    }
    crust_poll_root = NULL;
    crust_thread_complete(handle);
    return NULL;
}

static inline __attribute__((unused)) CrustHandle *crust_future_spawn_blocking(CrustHandle *handle) {
    atomic_init(&handle->status, CRUST_RUNNING);
    handle->scheduled = true;
    crust_thread_started();
    if (pthread_create(&handle->thread, NULL, crust_async_blocking_worker, handle) != 0) {
        handle->scheduled = false;
        crust_thread_drop(handle);
        crust_thread_finished();
        return NULL;
    }
    if (pthread_detach(handle->thread) != 0)
        crust_thread_fatal();
    return handle;
}

// -1 means pending. Zero is LaunchFailed, one is completion.
// The lock orders registration, completion and the poller's transition to parked.
static inline __attribute__((unused)) int crust_async_handle_take(CrustHandle *handle, void *result, size_t size) {
    if (handle == NULL)
        return 0;
    pthread_mutex_lock(&crust_threads_lock);
    if (atomic_load(&handle->status) != CRUST_COMPLETE) {
        handle->waiter = crust_poll_root;
        crust_poll_root->waiting = true;
        pthread_mutex_unlock(&crust_threads_lock);
        return -1;
    }
    pthread_mutex_unlock(&crust_threads_lock);
    crust_thread_unlink(handle);
    if (size != 0)
        memcpy(result, handle->result, size);
    crust_handle_release(handle, true);
    return 1;
}
