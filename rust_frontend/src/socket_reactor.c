typedef struct {
    pthread_once_t init;
    int64_t queue;
    bool write;
} CrustSocketQueue;

static CrustSocketQueue crust_socket_queues[2] = {
    {PTHREAD_ONCE_INIT, -1, false},
    {PTHREAD_ONCE_INIT, -1, true},
};

static void *crust_socket_worker(void *argument) {
    CrustSocketQueue *queue = argument;
    for (;;) {
        uintptr_t token;
        CRUST_SOCKET_WAIT(&token, queue->queue);
        if (token == 0)
            crust_thread_fatal();
        CrustHandle *handle = (CrustHandle *)token;
        pthread_mutex_lock(&crust_threads_lock);
        // Linux removes the interest before the socket can re-register.
        // The kqueue filter is already removed by EV_ONESHOT.
        int64_t removed;
        CRUST_SOCKET_WATCH(&removed, queue->queue, handle->watched_socket, queue->write, 0);
        if (removed != 0)
            crust_thread_fatal();
        bool parked = crust_async_unpark_locked(handle);
        pthread_cond_broadcast(&crust_threads_idle);
        pthread_mutex_unlock(&crust_threads_lock);
        if (parked)
            crust_async_enqueue(handle);
    }
}

static void crust_socket_start(CrustSocketQueue *queue) {
    pthread_t worker;
    CRUST_SOCKET_CREATE(&queue->queue);
    if (queue->queue < 0)
        return;
    if (pthread_create(&worker, NULL, crust_socket_worker, queue) != 0)
        crust_thread_fatal();
    if (pthread_detach(worker) != 0)
        crust_thread_fatal();
}

static void crust_socket_start_read(void) { crust_socket_start(&crust_socket_queues[0]); }
static void crust_socket_start_write(void) { crust_socket_start(&crust_socket_queues[1]); }

static int64_t crust_socket_park(uint64_t socket, bool write) {
    CrustHandle *root = crust_poll_root;
    CrustSocketQueue *queue = &crust_socket_queues[write];
    pthread_once(&queue->init, write ? crust_socket_start_write : crust_socket_start_read);
    if (queue->queue < 0)
        return queue->queue;

    pthread_mutex_lock(&crust_threads_lock);
    int64_t status;
    root->watched_socket = socket;
    CRUST_SOCKET_WATCH(&status, queue->queue, socket, write, (uintptr_t)root);
    if (status == 0)
        root->waiting = true;
    pthread_mutex_unlock(&crust_threads_lock);
    return status;
}
