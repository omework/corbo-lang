// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_REACTOR_HPP
#define CORBO_CPP_REACTOR_HPP
// OS queue operations are ordinary generated Corbo functions (their boundaries
// use @asm). This layer owns only registration, wake IDs and cohort lifetime.
struct corbo_socket_cohort {
    corbo_socket_cohort *next;
    uint64_t socket;
    corbo_wait_queue readers, writers;
};
struct corbo_reactor_state {
    corbo_band_lock lock;
    corbo_condition stopped;
    corbo_datastack registrations;
    corbo_socket_cohort *cohorts;
    intptr_t queue;
    bool initialized, stopping, running;
    int64_t (*create)();
    int64_t (*watch)(int64_t, uint64_t, uint64_t, uintptr_t);
    uintptr_t (*wait)(int64_t);
    uintptr_t (*completion_create)();
    int64_t (*completion_attach)(uintptr_t, uint64_t);
    int64_t (*completion_submit)(uintptr_t);
    uintptr_t (*completion_next)(uintptr_t);
#if !defined(_WIN32)
    int control[2];
#endif
};
inline corbo_reactor_state corbo_reactor;
// Configuration runs before user main, while there can be no registrations.
static inline void corbo_reactor_configure(int64_t (*create)(),
    int64_t (*watch)(int64_t,uint64_t,uint64_t,uintptr_t), uintptr_t (*wait)(int64_t),
    uintptr_t (*completion_create)(), int64_t (*completion_attach)(uintptr_t,uint64_t),
    int64_t (*completion_submit)(uintptr_t), uintptr_t (*completion_next)(uintptr_t)) {
    corbo_reactor.create = create; corbo_reactor.watch = watch; corbo_reactor.wait = wait;
    corbo_reactor.completion_create = completion_create; corbo_reactor.completion_attach = completion_attach;
    corbo_reactor.completion_submit = completion_submit; corbo_reactor.completion_next = completion_next;
    corbo_band_lock_init(&corbo_reactor.lock); corbo_condition_init(&corbo_reactor.stopped);
}
static inline void corbo_socket_rearm(corbo_socket_cohort *cohort) {
    uint64_t interests = (cohort->readers.head != NULL ? 1 : 0) | (cohort->writers.head != NULL ? 2 : 0);
    if (corbo_reactor.watch(corbo_reactor.queue, cohort->socket, interests,
        interests != 0 ? (uintptr_t)cohort : 0) < 0) corbo_fail("corbo: socket readiness registration failed");
}
#if defined(_WIN32)
static DWORD WINAPI corbo_reactor_worker(void *) {
#else
static void *corbo_reactor_worker(void *) {
#endif
    corbo_stack_open(0);
    for (;;) {
        uintptr_t token;
#if defined(_WIN32)
        token = corbo_reactor.completion_next((uintptr_t)corbo_reactor.queue);
#else
        token = corbo_reactor.wait(corbo_reactor.queue);
#endif
        corbo_band_acquire(&corbo_reactor.lock);
        if (corbo_reactor.stopping) { corbo_band_release(&corbo_reactor.lock); break; }
#if defined(_WIN32)
        if (token != 0) {
            uint64_t *request = (uint64_t *)token;
            // Publication and Pending observation use the same reactor lock.
            corbo_waiter *waiter = (corbo_waiter *)(uintptr_t)request[4];
            if (waiter == NULL) corbo_fail("corbo: completion lost its registration");
            request[4] = 0; waiter->queued = false; waiter->notified = true;
            corbo_waker wake = waiter->waker;
            corbo_band_release(&corbo_reactor.lock); corbo_notify(wake); continue;
        }
#else
        if (token != 0) {
            corbo_socket_cohort *cohort = (corbo_socket_cohort *)(token & ~(uintptr_t)3);
            for (size_t direction = 0; direction < 2; ++direction) {
                if (!(token & ((uintptr_t)1 << direction))) continue;
                corbo_wait_queue *queue = direction == 0 ? &cohort->readers : &cohort->writers;
                while (queue->head != NULL) {
                    corbo_waker wake = corbo_wait_one(queue);
                    corbo_band_release(&corbo_reactor.lock); corbo_notify(wake); corbo_band_acquire(&corbo_reactor.lock);
                }
            }
            if (cohort->readers.head != NULL || cohort->writers.head != NULL) corbo_socket_rearm(cohort);
        }
#endif
        corbo_band_release(&corbo_reactor.lock);
    }
    corbo_stack_close();
    corbo_band_acquire(&corbo_reactor.lock); corbo_reactor.running = false;
    corbo_condition_broadcast(&corbo_reactor.stopped); corbo_band_release(&corbo_reactor.lock);
#if defined(_WIN32)
    return 0;
#else
    return NULL;
#endif
}
// Caller holds the reactor lock. Cohorts keep their address until the OS queue
// is stopped, so an event already returned by the kernel cannot name freed data.
static inline void corbo_reactor_start_locked() {
    if (corbo_reactor.initialized) return;
#if defined(_WIN32)
    if (corbo_reactor.completion_create == NULL) corbo_fail("corbo: completion backend was not linked");
    corbo_reactor.queue = (intptr_t)corbo_reactor.completion_create();
    if (corbo_reactor.queue == 0) corbo_fail("corbo: completion queue creation failed");
#else
    if (corbo_reactor.create == NULL) corbo_fail("corbo: readiness backend was not linked");
    corbo_reactor.queue = corbo_reactor.create();
    if (corbo_reactor.queue < 0 || pipe(corbo_reactor.control)) corbo_fail("corbo: readiness queue creation failed");
    // A stable aligned control cohort wakes an otherwise idle OS queue at shutdown.
    corbo_datastack_open(&corbo_reactor.registrations, 1024 * 1024);
    corbo_socket_cohort *control = ::new(corbo_datastack_alloc(&corbo_reactor.registrations,
        sizeof(corbo_socket_cohort), alignof(corbo_socket_cohort))) corbo_socket_cohort{};
    control->socket = (uint64_t)corbo_reactor.control[0];
    if (corbo_reactor.watch(corbo_reactor.queue, control->socket, 1, (uintptr_t)control) < 0)
        corbo_fail("corbo: readiness control registration failed");
#endif
    corbo_reactor.initialized = true; corbo_reactor.running = true;
#if defined(_WIN32)
    HANDLE worker = CreateThread(NULL, 0, corbo_reactor_worker, NULL, 0, NULL);
    if (worker == NULL) corbo_fail("corbo: completion worker launch failed"); CloseHandle(worker);
#else
    pthread_t worker;
    if (pthread_create(&worker, NULL, corbo_reactor_worker, NULL) || pthread_detach(worker)) corbo_fail("corbo: readiness worker launch failed");
#endif
}
static inline bool corbo_socket_poll(uint64_t socket, corbo_waiter *waiter, corbo_waker wake, bool write) {
    corbo_band_acquire(&corbo_reactor.lock); corbo_reactor_start_locked();
    if (waiter->notified) { waiter->notified = false; corbo_band_release(&corbo_reactor.lock); return true; }
    corbo_socket_cohort *cohort = corbo_reactor.cohorts;
    while (cohort != NULL && cohort->socket != socket) cohort = cohort->next;
    if (cohort == NULL) {
        cohort = ::new(corbo_datastack_alloc(&corbo_reactor.registrations,
            sizeof(corbo_socket_cohort), alignof(corbo_socket_cohort))) corbo_socket_cohort{};
        cohort->socket = socket; cohort->next = corbo_reactor.cohorts; corbo_reactor.cohorts = cohort;
    }
    waiter->waker = wake; corbo_wait_append(write ? &cohort->writers : &cohort->readers, waiter);
    corbo_socket_rearm(cohort); corbo_band_release(&corbo_reactor.lock); return false;
}
static inline int64_t corbo_socket_attach(uint64_t socket) {
    corbo_band_acquire(&corbo_reactor.lock); corbo_reactor_start_locked();
    int64_t status = corbo_reactor.completion_attach((uintptr_t)corbo_reactor.queue, socket);
    corbo_band_release(&corbo_reactor.lock); return status;
}
static inline bool corbo_socket_complete(uint64_t socket, uintptr_t address, corbo_context *context, corbo_waiter *waiter, int64_t *status) {
    uint64_t *request = (uint64_t *)address;
    corbo_band_acquire(&corbo_reactor.lock); corbo_reactor_start_locked();
    if (waiter->notified) {
        waiter->notified = false; *status = 0;
        corbo_band_release(&corbo_reactor.lock); return true;
    }
    if (!waiter->queued) {
        waiter->waker = context->waker; waiter->queued = true;
        request[4] = (uintptr_t)waiter; request[5] = socket;
        int64_t submitted = corbo_reactor.completion_submit(address);
        if (submitted < 0) {
            request[4] = 0; waiter->queued = false; *status = submitted;
            corbo_band_release(&corbo_reactor.lock); return true;
        }
    }
    corbo_band_release(&corbo_reactor.lock); return false;
}
static inline void corbo_reactor_shutdown() {
    if (!corbo_reactor.initialized) return;
    corbo_band_acquire(&corbo_reactor.lock); corbo_reactor.stopping = true;
#if defined(_WIN32)
    if (!PostQueuedCompletionStatus((HANDLE)corbo_reactor.queue, 0, 0, NULL)) corbo_fail("corbo: completion shutdown wake failed");
#else
    uint8_t byte = 1;
    if (write(corbo_reactor.control[1], &byte, 1) != 1) corbo_fail("corbo: readiness shutdown wake failed");
#endif
    while (corbo_reactor.running) corbo_condition_wait(&corbo_reactor.stopped, &corbo_reactor.lock);
    corbo_band_release(&corbo_reactor.lock);
#if defined(_WIN32)
    CloseHandle((HANDLE)corbo_reactor.queue);
#else
    close((int)corbo_reactor.queue); close(corbo_reactor.control[0]); close(corbo_reactor.control[1]);
    corbo_datastack_close(&corbo_reactor.registrations);
#endif
    corbo_reactor.initialized = false;
}
#endif
