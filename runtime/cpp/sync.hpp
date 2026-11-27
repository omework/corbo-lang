// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_SYNC_HPP
#define CORBO_CPP_SYNC_HPP
// Wake callbacks enqueue an ID; they never poll a future while holding a lock.
struct corbo_waker { void *context; uint64_t id; void (*wake)(void *, uint64_t); };
struct corbo_waiter { corbo_waiter *next; corbo_waker waker; bool queued; bool notified; };
struct corbo_wait_queue { corbo_waiter *head; corbo_waiter *tail; };
static inline void corbo_wait_append(corbo_wait_queue *queue, corbo_waiter *waiter) {
    if (waiter->queued) return;
    waiter->next = NULL; waiter->queued = true; waiter->notified = false;
    if (queue->tail != NULL) queue->tail->next = waiter; else queue->head = waiter;
    queue->tail = waiter;
}
static inline corbo_waiter *corbo_wait_pop(corbo_wait_queue *queue) {
    corbo_waiter *waiter = queue->head;
    if (waiter == NULL) return NULL;
    queue->head = waiter->next;
    if (queue->head == NULL) queue->tail = NULL;
    waiter->next = NULL; waiter->queued = false; waiter->notified = true;
    return waiter;
}
static inline void corbo_wait_remove(corbo_wait_queue *queue, corbo_waiter *waiter) {
    corbo_waiter *previous = NULL, *current = queue->head;
    while (current != NULL && current != waiter) { previous = current; current = current->next; }
    if (current == NULL) return;
    if (previous != NULL) previous->next = current->next; else queue->head = current->next;
    if (queue->tail == current) queue->tail = previous;
    current->next = NULL; current->queued = false;
}
static inline corbo_waker corbo_wait_one(corbo_wait_queue *queue) {
    corbo_waiter *waiter = corbo_wait_pop(queue);
    return waiter != NULL ? waiter->waker : corbo_waker{};
}
static inline void corbo_notify(corbo_waker waker) {
    if (waker.wake != NULL) waker.wake(waker.context, waker.id);
}
struct corbo_condition {
#if defined(_WIN32)
    CONDITION_VARIABLE native;
#else
    pthread_cond_t native;
#endif
};
static inline void corbo_condition_init(corbo_condition *condition) {
#if defined(_WIN32)
    InitializeConditionVariable(&condition->native);
#else
    if (pthread_cond_init(&condition->native, NULL) != 0) corbo_fail("corbo: condition initialization failed");
#endif
}
static inline void corbo_condition_wait(corbo_condition *condition, corbo_band_lock *lock) {
#if defined(_WIN32)
    if (!SleepConditionVariableSRW(&condition->native, &lock->native, INFINITE, 0)) corbo_fail("corbo: condition wait failed");
#else
    if (pthread_cond_wait(&condition->native, &lock->native) != 0) corbo_fail("corbo: condition wait failed");
#endif
}
static inline void corbo_condition_broadcast(corbo_condition *condition) {
#if defined(_WIN32)
    WakeAllConditionVariable(&condition->native);
#else
    if (pthread_cond_broadcast(&condition->native) != 0) corbo_fail("corbo: condition wake failed");
#endif
}
static inline void corbo_condition_destroy(corbo_condition *condition) {
#if defined(_WIN32)
    (void)condition;
#else
    if (pthread_cond_destroy(&condition->native) != 0) corbo_fail("corbo: condition still in use");
#endif
}
static inline void corbo_native_lock_destroy(corbo_band_lock *lock) {
#if defined(_WIN32)
    (void)lock;
#else
    if (pthread_mutex_destroy(&lock->native) != 0) corbo_fail("corbo: mutex still in use");
#endif
}
struct corbo_mutex_state {
    corbo_datastack storage;
    corbo_band_lock lock;
    corbo_condition ready;
    corbo_wait_queue waiters;
    corbo_waiter *reserved;
    bool asynchronous;
    bool held;
};
// Native objects use fixed datastacks and remain at stable addresses.
static inline uintptr_t mutex_create(bool asynchronous) {
    corbo_datastack storage = {};
    corbo_datastack_open(&storage, sizeof(corbo_mutex_state));
    corbo_mutex_state *state = ::new(corbo_datastack_alloc(&storage, sizeof(corbo_mutex_state), alignof(corbo_mutex_state))) corbo_mutex_state{};
    state->storage = storage; state->asynchronous = asynchronous;
    corbo_band_lock_init(&state->lock); corbo_condition_init(&state->ready);
    return (uintptr_t)state;
}
static inline void mutex_acquire(uintptr_t raw) {
    corbo_mutex_state *state = (corbo_mutex_state *)raw;
    corbo_band_acquire(&state->lock);
    if (state->asynchronous) {
        while (state->held) corbo_condition_wait(&state->ready, &state->lock);
        state->held = true; corbo_band_release(&state->lock);
    } else { state->held = true; }
}
// Logical async ownership is handed directly to the oldest registered waiter.
static inline void mutex_release(uintptr_t raw) {
    corbo_mutex_state *state = (corbo_mutex_state *)raw;
    if (!state->asynchronous) { state->held = false; corbo_band_release(&state->lock); return; }
    corbo_band_acquire(&state->lock);
    if (!state->held || state->reserved != NULL) corbo_fail("corbo: invalid mutex release");
    state->reserved = corbo_wait_pop(&state->waiters);
    state->held = state->reserved != NULL;
    corbo_waker wake = state->reserved != NULL ? state->reserved->waker : corbo_waker{};
    corbo_condition_broadcast(&state->ready); corbo_band_release(&state->lock);
    corbo_notify(wake);
}
static inline bool corbo_mutex_poll(uintptr_t raw, corbo_waiter *waiter, corbo_waker wake) {
    corbo_mutex_state *state = (corbo_mutex_state *)raw;
    corbo_band_acquire(&state->lock);
    if (!state->asynchronous) corbo_fail("corbo: async wait requires an asynchronous mutex");
    waiter->waker = wake;
    if (state->reserved == waiter) {
        state->reserved = NULL; waiter->notified = false;
        corbo_band_release(&state->lock); return true;
    }
    if (!state->held && state->waiters.head == NULL) {
        state->held = true; corbo_band_release(&state->lock); return true;
    }
    corbo_wait_append(&state->waiters, waiter);
    corbo_band_release(&state->lock); return false;
}
// Remove frame-owned registration before releasing its storage.
static inline void corbo_mutex_detach(uintptr_t raw, corbo_waiter *waiter) {
    corbo_mutex_state *state = (corbo_mutex_state *)raw;
    corbo_band_acquire(&state->lock);
    corbo_wait_remove(&state->waiters, waiter);
    corbo_waker wake = {};
    if (state->reserved == waiter) {
        state->reserved = corbo_wait_pop(&state->waiters); state->held = state->reserved != NULL;
        if (state->reserved != NULL) wake = state->reserved->waker;
        corbo_condition_broadcast(&state->ready);
    }
    waiter->notified = false; corbo_band_release(&state->lock); corbo_notify(wake);
}
static inline void mutex_destroy(uintptr_t raw) {
    corbo_mutex_state *state = (corbo_mutex_state *)raw;
    if (state->held || state->waiters.head != NULL || state->reserved != NULL)
        corbo_fail("corbo: destroying a mutex with live users");
    corbo_condition_destroy(&state->ready); corbo_native_lock_destroy(&state->lock);
    corbo_datastack storage = state->storage; corbo_datastack_close(&storage);
}
struct corbo_channel_state {
    corbo_datastack storage;
    corbo_band_lock lock;
    corbo_condition ready;
    corbo_wait_queue senders;
    corbo_wait_queue receivers;
    uint8_t *data;
    size_t capacity, width, count, head;
    uint64_t epoch;
    bool closed;
};
static inline uintptr_t channel_create(size_t capacity, size_t width) {
    if (capacity == 0 || width == 0 || capacity > (SIZE_MAX - sizeof(corbo_channel_state) - alignof(max_align_t)) / width)
        corbo_fail("corbo: invalid channel capacity");
    size_t bytes = sizeof(corbo_channel_state) + alignof(max_align_t) + capacity * width;
    corbo_datastack storage = {}; corbo_datastack_open(&storage, bytes);
    corbo_channel_state *state = ::new(corbo_datastack_alloc(&storage, sizeof(corbo_channel_state), alignof(corbo_channel_state))) corbo_channel_state{};
    state->data = (uint8_t *)corbo_datastack_alloc(&storage, capacity * width, alignof(max_align_t));
    state->storage = storage; state->capacity = capacity; state->width = width;
    corbo_band_lock_init(&state->lock); corbo_condition_init(&state->ready);
    return (uintptr_t)state;
}
// 0 transfers ownership, 1 requests a retry after waiting, 2 denotes closed.
static inline int64_t channel_send(uintptr_t raw, void *input, uint64_t *epoch, bool blocking) {
    corbo_channel_state *state = (corbo_channel_state *)raw;
    corbo_band_acquire(&state->lock);
    while (blocking && !state->closed && state->count == state->capacity) corbo_condition_wait(&state->ready, &state->lock);
    *epoch = state->epoch;
    if (state->closed || state->count == state->capacity) { int64_t status = state->closed ? 2 : 1; corbo_band_release(&state->lock); return status; }
    size_t remaining = state->capacity - state->head;
    size_t slot = state->count >= remaining ? state->count - remaining : state->head + state->count;
    memcpy(state->data + slot * state->width, input, state->width); memset(input, 0, state->width);
    ++state->count; ++state->epoch;
    corbo_waker wake = corbo_wait_one(&state->receivers);
    corbo_condition_broadcast(&state->ready); corbo_band_release(&state->lock); corbo_notify(wake);
    return 0;
}
static inline int64_t channel_receive(uintptr_t raw, void *output, uint64_t *epoch, bool blocking) {
    corbo_channel_state *state = (corbo_channel_state *)raw;
    corbo_band_acquire(&state->lock);
    while (blocking && !state->closed && state->count == 0) corbo_condition_wait(&state->ready, &state->lock);
    *epoch = state->epoch;
    if (state->count == 0) { int64_t status = state->closed ? 2 : 1; corbo_band_release(&state->lock); return status; }
    void *slot = state->data + state->head * state->width;
    memcpy(output, slot, state->width); memset(slot, 0, state->width);
    if (++state->head == state->capacity) state->head = 0;
    --state->count; ++state->epoch;
    corbo_waker wake = corbo_wait_one(&state->senders);
    corbo_condition_broadcast(&state->ready); corbo_band_release(&state->lock); corbo_notify(wake);
    return 0;
}
static inline bool corbo_channel_poll(uintptr_t raw, corbo_waiter *waiter, corbo_waker wake, uint64_t epoch, bool sending) {
    corbo_channel_state *state = (corbo_channel_state *)raw;
    corbo_band_acquire(&state->lock);
    waiter->waker = wake;
    bool ready = state->closed || state->epoch != epoch || waiter->notified
        || (sending ? state->count < state->capacity : state->count != 0);
    corbo_wait_queue *queue = sending ? &state->senders : &state->receivers;
    if (ready) { corbo_wait_remove(queue, waiter); waiter->notified = false; }
    else { corbo_wait_append(queue, waiter); }
    corbo_band_release(&state->lock); return ready;
}
static inline void corbo_channel_detach(uintptr_t raw, corbo_waiter *waiter, bool sending) {
    corbo_channel_state *state = (corbo_channel_state *)raw;
    corbo_band_acquire(&state->lock);
    corbo_wait_queue *queue = sending ? &state->senders : &state->receivers;
    corbo_wait_remove(queue, waiter);
    corbo_waker wake = waiter->notified ? corbo_wait_one(queue) : corbo_waker{};
    waiter->notified = false; corbo_band_release(&state->lock); corbo_notify(wake);
}
static inline void channel_close(uintptr_t raw) {
    corbo_channel_state *state = (corbo_channel_state *)raw;
    corbo_band_acquire(&state->lock); state->closed = true; ++state->epoch;
    corbo_condition_broadcast(&state->ready);
    // Drain by ID snapshots so no callback dereferences an unregistered frame.
    while (state->senders.head != NULL || state->receivers.head != NULL) {
        corbo_waker send = corbo_wait_one(&state->senders), receive = corbo_wait_one(&state->receivers);
        corbo_band_release(&state->lock); corbo_notify(send); corbo_notify(receive); corbo_band_acquire(&state->lock);
    }
    corbo_band_release(&state->lock);
}
static inline void channel_destroy(uintptr_t raw) {
    corbo_channel_state *state = (corbo_channel_state *)raw;
    if (state->count != 0 || state->senders.head != NULL || state->receivers.head != NULL)
        corbo_fail("corbo: destroying a channel with live users");
    corbo_condition_destroy(&state->ready); corbo_native_lock_destroy(&state->lock);
    corbo_datastack storage = state->storage; corbo_datastack_close(&storage);
}
#endif
