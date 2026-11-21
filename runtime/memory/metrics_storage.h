/** @file metrics_storage.h
 * Atomic managed-storage counters shared by the runtime implementations.
 */
/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#ifndef CORBO_METRICS_STORAGE_H
#define CORBO_METRICS_STORAGE_H
/* Atomic counters only. Allocation/cleanup policy remains in the runtime. */
static _Atomic size_t memory_counters[5];
static _Thread_local Pools *metric_pool_head;
/** Add a successful storage transition without inspecting another thread's stack. */
static inline void memory_metric_add(size_t counter, size_t bytes) {
    if (bytes) atomic_fetch_add_explicit(&memory_counters[counter], bytes, memory_order_relaxed);
}
/** Remove bytes after their storage transition; never sample mutable descriptors. */
static inline void memory_metric_sub(size_t counter, size_t bytes) {
    if (bytes) atomic_fetch_sub_explicit(&memory_counters[counter], bytes, memory_order_relaxed);
}
/** Sample one atomic counter without stopping workers. */
static inline size_t memory_metric_read(size_t counter) {
    return atomic_load_explicit(&memory_counters[counter], memory_order_relaxed);
}
#endif
