/* SPDX-License-Identifier: MIT OR Apache-2.0 */
/* Included after a generated program/runtime, exercising queue policy independently of Corbo lowering. */
#include <stdio.h>
/** Always evaluates operations, including in toolchains that define NDEBUG. */
#define CHECK(condition) do { if (!(condition)) { fprintf(stderr,"mutex check failed at %d: %s\n",__LINE__,#condition); abort(); } } while (0)
static uintptr_t shared_gate;
static unsigned shared_count;
/** Native workers serialize payload writes through the thread-owned mutex. */
static void *mutex_counter(void *unused) {
    (void)unused;
    for(unsigned i=0;i<1000;i++) {
        mutex_acquire(shared_gate);shared_count++;mutex_release(shared_gate);
    }
    return NULL;
}
/** A task-owned guard may be released by a different native thread. */
static void *mutex_async_release(void *gate) {mutex_release((uintptr_t)gate);return NULL;}
/** Check contention, FIFO handoff, pending cleanup and cross-thread async release. */
int main(void) {
    shared_gate=mutex_create(false);
    pthread_t threads[3];
    for(unsigned i=0;i<3;i++)CHECK(!pthread_create(&threads[i],NULL,mutex_counter,NULL));
    for(unsigned i=0;i<3;i++)CHECK(!pthread_join(threads[i],NULL));
    CHECK(shared_count==3000);mutex_destroy(shared_gate);
    uintptr_t gate=mutex_create(true);
    Task a={0},b={0},c={0},d={0};
    CHECK(mutex_poll(&a,gate));
    CHECK(!mutex_poll(&b,gate));CHECK(!mutex_poll(&c,gate));CHECK(!mutex_poll(&d,gate));
    mutex_detach(&c);
    pthread_t worker;CHECK(!pthread_create(&worker,NULL,mutex_async_release,(void*)gate));CHECK(!pthread_join(worker,NULL));
    CHECK(b.mutex_reserved && !d.mutex_reserved);
    mutex_detach(&b); // Dropping a handoff recipient passes ownership onward.
    CHECK(d.mutex_reserved && mutex_poll(&d,gate));
    mutex_release(gate);
    CHECK(mutex_poll(&a,gate));mutex_release(gate);mutex_destroy(gate);
    return 0;
}
