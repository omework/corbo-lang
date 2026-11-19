static pthread_once_t crust_iocp_init = PTHREAD_ONCE_INIT;
static uintptr_t crust_iocp_port;

static void *crust_iocp_worker(void *unused) {
    (void)unused;
    for (;;) {
        uintptr_t address;
        CRUST_IOCP_NEXT(&address, crust_iocp_port);
        if (address == 0)
            crust_thread_fatal();
        uint64_t *request = (uint64_t *)address;
        pthread_mutex_lock(&crust_threads_lock);
        CrustHandle *handle = (CrustHandle *)(uintptr_t)request[4];
        bool parked = crust_async_unpark_locked(handle);
        pthread_cond_broadcast(&crust_threads_idle);
        pthread_mutex_unlock(&crust_threads_lock);
        if (parked)
            crust_async_enqueue(handle);
    }
}

static void crust_iocp_start(void) {
    CRUST_IOCP_CREATE(&crust_iocp_port);
    if (crust_iocp_port == 0)
        return;
    pthread_t worker;
    if (pthread_create(&worker, NULL, crust_iocp_worker, NULL) != 0)
        crust_thread_fatal();
    if (pthread_detach(worker) != 0)
        crust_thread_fatal();
}

static int64_t crust_iocp_attach(uint64_t socket) {
    pthread_once(&crust_iocp_init, crust_iocp_start);
    if (crust_iocp_port == 0)
        return -8; // ERROR_NOT_ENOUGH_MEMORY

    int64_t status;
    CRUST_IOCP_ATTACH(&status, crust_iocp_port, socket);
    return status;
}

static int64_t crust_iocp_park(uint64_t socket, uintptr_t address) {
    CrustHandle *root = crust_poll_root;
    uint64_t *request = (uint64_t *)address;
    pthread_mutex_lock(&crust_threads_lock);
    request[4] = (uintptr_t)root;
    request[5] = socket;
    int64_t status;
    CRUST_IOCP_SUBMIT(&status, address);
    if (status == 0)
        root->waiting = true;
    pthread_mutex_unlock(&crust_threads_lock);
    return status;
}
