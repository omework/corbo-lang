typedef struct {
    unsigned char *stack;
    size_t cursor;
    size_t high_water;
    size_t capacity;
    int capacity_set;
    CrustRegionBand *region_scope;
    CrustRegionBand *region_global;
    size_t region_limit;
    size_t region_stack_limit;
    bool region_stack_configured;
    CrustHandle *handles;
    size_t thread_depth;
#ifdef CRUST_HAS_POOLS
    CrustAllocation *allocations;
#ifdef CRUST_HAS_DESTRUCTORS
    CrustDestructor *destructors;
#endif
    size_t pool_depth;
    bool pool_mode;
#endif
#ifdef CRUST_HAS_MAPS
    CrustMap *maps;
    size_t map_depth;
#endif
} CrustAsyncContext;

static void crust_async_exchange(CrustAsyncContext *context) {
#define CRUST_EXCHANGE(field, variable, type) do { \
    type saved = variable; \
    variable = context->field; \
    context->field = saved; \
} while (0)
    CRUST_EXCHANGE(stack, crust_stack, unsigned char *);
    CRUST_EXCHANGE(cursor, crust_cursor, size_t);
    CRUST_EXCHANGE(high_water, crust_high_water, size_t);
    CRUST_EXCHANGE(capacity, crust_capacity, size_t);
    CRUST_EXCHANGE(capacity_set, crust_capacity_set, int);
    CRUST_EXCHANGE(region_scope, crust_region_scope, CrustRegionBand *);
    CRUST_EXCHANGE(region_global, crust_region_global, CrustRegionBand *);
    CRUST_EXCHANGE(region_limit, crust_region_limit, size_t);
    CRUST_EXCHANGE(region_stack_limit, crust_region_stack_limit, size_t);
    CRUST_EXCHANGE(region_stack_configured, crust_region_stack_configured, bool);
    CRUST_EXCHANGE(handles, crust_handles, CrustHandle *);
    CRUST_EXCHANGE(thread_depth, crust_thread_depth, size_t);
#ifdef CRUST_HAS_POOLS
    CRUST_EXCHANGE(allocations, crust_allocations, CrustAllocation *);
#ifdef CRUST_HAS_DESTRUCTORS
    CRUST_EXCHANGE(destructors, crust_destructors, CrustDestructor *);
#endif
    CRUST_EXCHANGE(pool_depth, crust_pool_depth, size_t);
    CRUST_EXCHANGE(pool_mode, crust_async_pool, bool);
#endif
#ifdef CRUST_HAS_MAPS
    CRUST_EXCHANGE(maps, crust_maps, CrustMap *);
    CRUST_EXCHANGE(map_depth, crust_map_depth, size_t);
#endif
#undef CRUST_EXCHANGE
}

static void crust_async_close_context(void) {
    crust_worker_close_regions();
    if (crust_stack != NULL) {
        crust_guarded_unmap(crust_stack, crust_capacity);
        crust_stack = NULL;
    }
}

typedef struct {
    size_t cursor;
    CrustRegionBand *region;
    size_t threads;
#ifdef CRUST_HAS_MAPS
    size_t maps;
#endif
} CrustAsyncMark;

static inline __attribute__((unused)) CrustAsyncMark crust_async_mark(void) {
    return (CrustAsyncMark){
        .cursor = crust_cursor,
        .region = crust_region_scope,
        .threads = crust_thread_depth++,
#ifdef CRUST_HAS_MAPS
        .maps = crust_map_depth++,
#endif
    };
}

static inline __attribute__((unused)) void crust_async_rewind(CrustAsyncMark mark, uintmax_t fixed_threshold,
                               uintmax_t regional_threshold, bool force) {
    crust_thread_rewind(mark.threads);
#ifdef CRUST_HAS_MAPS
    crust_map_rewind(mark.maps);
#endif
    crust_rewind(mark.cursor);
    crust_reclaim_fixed(fixed_threshold, force);
    crust_region_restore_pages(mark.region, regional_threshold, force);
}

static inline __attribute__((unused)) void crust_future_take(CrustHandle *handle, void *result, size_t size) {
    if (size != 0)
        memcpy(result, handle->result, size);
    crust_thread_unlink(handle);
    crust_handle_release(handle, true);
}
