/* SPDX-License-Identifier: MIT OR Apache-2.0 */
/* Exact quiescent accounting and concurrent atomic sampling of the public C ABI. */
#include "corbo_runtime.h"
#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>

static _Atomic unsigned finished;
/* Configure C-owned runtime settings serially; allocation loops remain concurrent. */
static pthread_mutex_t lifecycle = PTHREAD_MUTEX_INITIALIZER;

/** Exercise one isolated fixed stack and repeated shared-pool accounting updates. */
static void *worker(void *unused) {
    (void)unused;
    pthread_mutex_lock(&lifecycle);
    corbo_runtime_init(65536, 65536, 4096);
    pthread_mutex_unlock(&lifecycle);
    CorboPool *pool = corbo_pool_create(4, 16, 1);
    for (unsigned i = 0; i < 10000; ++i) {
        CorboAllocation value = corbo_pool_take(pool, 0);
        corbo_allocation_drop(&value);
    }
    pthread_mutex_lock(&lifecycle);
    corbo_runtime_shutdown();
    pthread_mutex_unlock(&lifecycle);
    atomic_fetch_add(&finished, 1);
    return NULL;
}

int main(void) {
    assert(corbo_runtime_abi_version() == CORBO_RUNTIME_ABI_VERSION);
    corbo_runtime_init(65536, 65536, 4096);
    CorboMemoryStats initial = corbo_memory_stats();
    assert(initial.reserved == 65536 && initial.committed == 0 && initial.occupied == 0);
    CorboStackMark mark = corbo_datastack_mark();
    CorboPool *pool = corbo_pool_create(4, 16, 1);
    CorboMemoryStats empty = corbo_memory_stats();
    CorboAllocation value = corbo_pool_take(pool, 0);
    assert(corbo_memory_stats().occupied == empty.occupied + pool->stride);
    corbo_allocation_drop(&value);
    assert(corbo_memory_stats().occupied == empty.occupied);
    CorboRegion region = {0};
    corbo_region_new(&region, 8, false);
    CorboMemoryStats before = corbo_memory_stats();
    corbo_region_push(&region);
    assert(corbo_memory_stats().occupied == before.occupied + 8);
    corbo_region_drop(&region);
    assert(corbo_memory_stats().occupied == before.occupied);
    corbo_datastack_rewind(mark);
    assert(corbo_memory_stats().occupied == 0);
    corbo_free_pages();
    assert(corbo_memory_stats().committed == 0);
    corbo_runtime_shutdown();
    assert(corbo_memory_stats().reserved == 0);
    pthread_t threads[3];
    for (unsigned i = 0; i < 3; ++i) assert(!pthread_create(&threads[i], NULL, worker, NULL));
    do {
        /* Fields are independent samples; cross-field inequalities are not asserted. */
        (void)corbo_memory_stats();
    } while (atomic_load(&finished) != 3);
    for (unsigned i = 0; i < 3; ++i) assert(!pthread_join(threads[i], NULL));
    CorboMemoryStats final = corbo_memory_stats();
    assert(!final.reserved && !final.committed && !final.occupied);
    return 0;
}
