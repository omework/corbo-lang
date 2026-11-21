/** @file runtime_api.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
/* SPDX-License-Identifier: MIT OR Apache-2.0 */
/** Returns the experimental C ABI version; clients must use the matching runtime header. */
unsigned corbo_runtime_abi_version(void) { return CORBO_RUNTIME_ABI_VERSION; }
/** Initializes C-owned runtime storage with optional fixed-stack, region-stack and region-width budgets; repeated initialization terminates. */
void corbo_runtime_init(size_t fixed_size, size_t region_stack_size, size_t region_size) {
    if (base) storage_error();
    if (region_size) global_limit = region_size;
    global_budget = region_stack_size;
    reserve(fixed_size ? fixed_size : global_fixed_budget);
}
/** Releases the calling thread's C-owned runtime after all live resources and workers have been cleaned up; a stopped runtime is a no-op. */
void corbo_runtime_shutdown(void) {
    if (!base) return;
    region_restore(NULL); region_release(); release();
    base = NULL; cursor = limit = committed = mapped_size = 0;
    global_band = (RegionBand){0};
}
/** Allocates count aligned elements on the calling thread's initialized stack; invalid size/alignment or exhaustion terminates. */
void *corbo_datastack_alloc(size_t size, size_t alignment, size_t count) {
    if (!base || !size || !alignment || (alignment & (alignment - 1))
        || alignment > _Alignof(max_align_t)) storage_error();
    return push(size, alignment, count);
}
/** Returns a mark containing the current cursor, stack identity and region-scope marker. */
CorboStackMark corbo_datastack_mark(void) {
    return (CorboStackMark){cursor, base, current_band};
}
/** Returns the current cursor, committed-byte boundary and fixed-stack capacity. */
CorboStackInfo corbo_datastack_info(void) {
    return (CorboStackInfo){cursor, committed, limit};
}
/** Restores a mark from this stack after caller cleanup; rejects foreign or forward marks and preserves live transferred regions. */
void corbo_datastack_rewind(CorboStackMark mark) {
    if (!base || mark.stack != base || mark.position > cursor) storage_error();
#ifdef CORBO_RUNTIME_TASKS
    pthread_mutex_lock(&task_lock);
#endif
    region_restore(mark.region_scope); memory_cursor(mark.position);
#ifdef CORBO_RUNTIME_TASKS
    pthread_mutex_unlock(&task_lock);
#endif
}
/** Requests immediate reclamation of complete unused pages without changing live values or their reserved address ranges. */
void corbo_free_pages(void) { reclaim_scope(true); }
/** Creates fixed slots for each enum arm on the current datastack; zero element width or invalid capacity terminates. */
CorboPool *corbo_pool_create(size_t slots, size_t size, size_t arms) {
    if (!size) storage_error();
    return new_pool(slots, region_stride(size), arms);
}
/** Claims a free slot in arm and returns its allocation descriptor; invalid arms or exhaustion terminate. */
CorboAllocation corbo_pool_take(CorboPool *pool, size_t arm) {
    if (!pool || arm >= pool->arms) storage_error();
    return pool_take(pool, arm);
}
/** Returns an allocation's payload address without transferring ownership or extending its lifetime. */
void *corbo_allocation_data(const CorboAllocation *allocation) { return allocation->slot; }
/** Destroys a live allocation before releasing its slot and clears its pool link; a cleared descriptor is harmless. */
void corbo_allocation_drop(CorboAllocation *allocation) { put(allocation); }
/** Enters a local region scope with the requested maximum region size and count budget. */
void corbo_region_enter(size_t max_size, size_t count) {
#ifdef CORBO_RUNTIME_TASKS
    pthread_mutex_lock(&task_lock);
#endif
    region_enter(max_size, count, count);
#ifdef CORBO_RUNTIME_TASKS
    pthread_mutex_unlock(&task_lock);
#endif
}
/** Initializes a stable caller-owned region descriptor for element_size bytes per item; dedicated selects independent band storage. */
void corbo_region_new(CorboRegion *region, size_t size, bool dedicated) {
    if (!size) region_error();
    value_region_new(region, size, 0, dedicated);
}
/** Appends one uninitialized region element and returns its address; region exhaustion terminates. */
void *corbo_region_push(CorboRegion *region) { return value_region_add(region); }
/** Destroys child-region links, releases payload storage and zeroes the caller's region descriptor. */
void corbo_region_drop(CorboRegion *region) { value_region_drop(region); memset(region, 0, sizeof *region); }
/** Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback. */
CorboHashMap *corbo_map_new(size_t size, void (*dispose)(void *)) { return map_new(size, dispose); }
/** Returns the stored value address for key, or zero when absent; the map retains ownership. */
void *corbo_map_get(CorboHashMap *map, uint64_t key) { return map_get(map, key); }
/** Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists. */
bool corbo_map_insert(CorboHashMap *map, uint64_t key, const void *value, void *previous) {
    return map_insert(map, key, value, previous);
}
/** Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse. */
bool corbo_map_remove(CorboHashMap *map, uint64_t key, void *previous) { return map_remove(map, key, previous); }
/** Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage. */
void corbo_map_drop(CorboHashMap **map) { map_drop(map); }

/** Samples managed-storage counters atomically; fields may represent adjacent instants. */
CorboMemoryStats corbo_memory_stats(void) {
    size_t reserved=memory_metric_read(0),committed=memory_metric_read(1);
    size_t total=memory_metric_read(2)+memory_metric_read(3),holes=memory_metric_read(4);
    return (CorboMemoryStats){reserved,committed,holes>total?0:total-holes};
}
