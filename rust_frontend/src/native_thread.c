#include <stdatomic.h>

typedef struct CrustHandle {
    CrustGrowing region;
    pthread_t thread;
    void *result;
    uintmax_t region_limit;
    uintmax_t region_stack_limit;
    struct CrustHandle *next;
    struct CrustHandle *owned_next;
    struct CrustHandle *queued_next;
    bool (*poll)(struct CrustHandle *);
    bool scheduled;
    void (*dispose)(struct CrustHandle *);
#ifdef CRUST_HAS_ASYNC
    struct CrustHandle *waiter;
    bool waiting;
    bool parked;
    uint64_t watched_socket;
#endif
    size_t owner;
    atomic_uint status;
} CrustHandle;

enum { CRUST_RUNNING, CRUST_COMPLETE, CRUST_ABANDONED };
static CRUST_LOCAL CrustHandle *crust_handles;
static CRUST_LOCAL size_t crust_thread_depth;
static pthread_mutex_t crust_threads_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t crust_threads_idle = PTHREAD_COND_INITIALIZER;
static size_t crust_threads_running;

static void crust_thread_fatal(void) {
    fputs("corbo: échec de l’attente du thread\n", stderr);
    exit(EXIT_FAILURE);
}

static void crust_thread_started(void) {
    pthread_mutex_lock(&crust_threads_lock);
    ++crust_threads_running;
    pthread_mutex_unlock(&crust_threads_lock);
}

static void crust_thread_finished(void) {
    pthread_mutex_lock(&crust_threads_lock);
    --crust_threads_running;
    pthread_cond_broadcast(&crust_threads_idle);
    pthread_mutex_unlock(&crust_threads_lock);
}

static void crust_thread_drain(void) {
    pthread_mutex_lock(&crust_threads_lock);
    while (crust_threads_running != 0)
        pthread_cond_wait(&crust_threads_idle, &crust_threads_lock);
    pthread_mutex_unlock(&crust_threads_lock);
}

static inline __attribute__((unused)) void crust_thread_own(CrustHandle *handle, size_t owner) {
    if (handle != NULL)
        handle->owner = owner;
}

static void crust_handle_release(CrustHandle *handle, bool taken) {
    if (!taken && handle->dispose != NULL)
        handle->dispose(handle);
    crust_region_release(&handle->region);
}

#ifdef CRUST_HAS_ASYNC
static void crust_async_enqueue(CrustHandle *handle);

// Called with crust_threads_lock held. If notification wins the race with
// parking, the poller sees waiting=false and puts itself back on the queue.
static bool crust_async_unpark_locked(CrustHandle *handle) {
    handle->waiting = false;
    bool parked = handle->parked;
    handle->parked = false;
    return parked;
}
#endif

static inline __attribute__((unused)) void crust_thread_complete(CrustHandle *handle) {
    pthread_mutex_lock(&crust_threads_lock);
#ifdef CRUST_HAS_ASYNC
    CrustHandle *wake = NULL;
    CrustHandle *waiter = handle->waiter;
    if (waiter != NULL && crust_async_unpark_locked(waiter))
        wake = waiter;
#endif
    bool abandoned = atomic_exchange(&handle->status, CRUST_COMPLETE) == CRUST_ABANDONED;
    pthread_cond_broadcast(&crust_threads_idle);
    pthread_mutex_unlock(&crust_threads_lock);
#ifdef CRUST_HAS_ASYNC
    if (wake != NULL)
        crust_async_enqueue(wake);
#endif
    if (abandoned)
        crust_handle_release(handle, false);
    crust_thread_finished();
}

static void crust_thread_unlink(CrustHandle *handle) {
    CrustHandle **link = &crust_handles;
    while (*link != handle)
        link = &(*link)->next;
    *link = handle->next;
}

static inline __attribute__((unused)) bool crust_thread_join(CrustHandle *handle, void *result, size_t size) {
    if (handle == NULL)
        return false;
    crust_thread_unlink(handle);
    if (handle->poll != NULL) {
        pthread_mutex_lock(&crust_threads_lock);
        while (atomic_load(&handle->status) != CRUST_COMPLETE)
            pthread_cond_wait(&crust_threads_idle, &crust_threads_lock);
        pthread_mutex_unlock(&crust_threads_lock);
    } else if (pthread_join(handle->thread, NULL) != 0) {
        crust_thread_fatal();
    }
    if (size != 0)
        memcpy(result, handle->result, size);
    crust_handle_release(handle, true);
    return true;
}

static void crust_thread_detach(CrustHandle *handle) {
    if (handle->poll != NULL && !handle->scheduled) {
        crust_handle_release(handle, false);
        return;
    }
    if (handle->poll == NULL && pthread_detach(handle->thread) != 0)
        crust_thread_fatal();
    if (atomic_exchange(&handle->status, CRUST_ABANDONED) == CRUST_COMPLETE)
        crust_handle_release(handle, false);
}

static inline __attribute__((unused)) void crust_thread_drop(CrustHandle *handle) {
    if (handle != NULL) {
        crust_thread_unlink(handle);
        crust_thread_detach(handle);
    }
}

static void crust_thread_rewind(size_t mark) {
    CrustHandle **link = &crust_handles;
    while (*link != NULL) {
        CrustHandle *handle = *link;
        if (handle->owner > mark) {
            *link = handle->next;
            crust_thread_detach(handle);
        } else {
            link = &handle->next;
        }
    }
    crust_thread_depth = mark;
}

static inline CrustHandle *crust_thread_register(CrustHandle *handle) {
    handle->owner = crust_thread_depth;
    handle->next = crust_handles;
    crust_handles = handle;
    return handle;
}

static inline __attribute__((unused)) void crust_handle_resource(CrustHandle *handle, size_t owner, int action) {
    if (handle == NULL)
        return;
    switch (action) {
    case CRUST_REHOME: crust_thread_own(handle, owner); break;
    case CRUST_DETACH: crust_thread_unlink(handle); break;
    case CRUST_ATTACH: crust_thread_register(handle); crust_thread_own(handle, owner); break;
    case CRUST_DESTROY: crust_thread_detach(handle); break;
    case CRUST_DROP: crust_thread_drop(handle); break;
    default: abort();
    }
}

static inline __attribute__((unused)) CrustHandle *crust_thread_launch(CrustHandle *handle, void *(*worker)(void *), void *frame, void (*dispose)(CrustHandle *)) {
    handle->poll = NULL;
    handle->dispose = dispose;
#ifdef CRUST_HAS_ASYNC
    handle->waiter = NULL;
#endif
    atomic_init(&handle->status, CRUST_RUNNING);
    crust_thread_started();
    if (pthread_create(&handle->thread, NULL, worker, frame) != 0) {
        crust_handle_release(handle, false);
        crust_thread_finished();
        return NULL;
    }
    return crust_thread_register(handle);
}
