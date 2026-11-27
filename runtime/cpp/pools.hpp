// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_POOLS_HPP
#define CORBO_CPP_POOLS_HPP
// Fixed pool storage belongs to the fixed datastack, never a general heap.
struct corbo_pool_state {
    corbo_mapping_record *record;
    uint8_t *data;
    uint8_t *occupied;
    size_t *free_slots;
    size_t capacity;
    size_t width;
    size_t cursor;
    size_t free_count;
    size_t live_count;
    void (*destroy)(void *);
};
struct corbo_pool { corbo_pool_state *state; };
struct corbo_allocation {
    corbo_pool_state *pool;
    uint8_t *slot;
    size_t index;
};
// Query capacity without mutating the pool. Runtime checks use the same
// cursor/hole policy as `corbo_pool_take`; code generation never reconstructs
// this bookkeeping from source-level pool syntax.
static inline bool corbo_pool_can_take(const corbo_pool *descriptor, size_t required) {
    if (descriptor == NULL || descriptor->state == NULL) return false;
    const corbo_pool_state *pool = descriptor->state;
    return required <= pool->capacity - pool->live_count;
}
// Initialize a pool from addresses selected by the compiler's memory plan.
// No cursor movement or hidden storage choice is allowed in this entry point.
static inline void corbo_pool_init_planned(corbo_pool *descriptor,
                                           corbo_pool_state *pool,
                                           uint8_t *data,
                                           uint8_t *occupied,
                                           size_t *free_slots,
                                           size_t capacity,
                                           size_t width,
                                           void (*destroy)(void *)) {
    if (descriptor == NULL || pool == NULL || data == NULL || occupied == NULL
        || free_slots == NULL || capacity == 0 || width == 0)
        corbo_fail("corbo: invalid planned pool storage");
    *pool = {};
    descriptor->state = pool;
    pool->record = corbo_fixed_stack.record;
    pool->data = data;
    pool->occupied = occupied;
    pool->free_slots = free_slots;
    memset(pool->occupied, 0, capacity);
    pool->capacity = capacity;
    pool->width = width;
    pool->destroy = destroy;
    corbo_counter_add(&pool->record->unused, capacity * width);
}
// Reserve payload and bookkeeping once. Every slot preserves its address.
static inline void corbo_pool_init(corbo_pool *descriptor, size_t capacity,
                                  size_t width, size_t alignment,
                                  void (*destroy)(void *)) {
    if (capacity == 0 || width == 0 || capacity > SIZE_MAX / width
        || capacity > SIZE_MAX / sizeof(size_t))
        corbo_fail("corbo: invalid pool capacity");
    corbo_pool_state *pool = ::new(corbo_stack_alloc(sizeof(corbo_pool_state), alignof(corbo_pool_state))) corbo_pool_state{};
    uint8_t *data = (uint8_t *)corbo_stack_alloc(capacity * width, alignment);
    uint8_t *occupied = (uint8_t *)corbo_stack_alloc(capacity, 1);
    size_t *free_slots = (size_t *)corbo_stack_alloc(capacity * sizeof(size_t), alignof(size_t));
    corbo_pool_init_planned(descriptor, pool, data, occupied, free_slots,
                            capacity, width, destroy);
}
// Prefer the cursor. Reuse an indexed hole only after the cursor reaches capacity.
static inline bool corbo_pool_take(corbo_pool *descriptor, corbo_allocation *result) {
    corbo_pool_state *pool = descriptor->state;
    size_t index = pool->cursor;
    if (index < pool->capacity) ++pool->cursor;
    else {
        bool found = false;
        while (pool->free_count != 0) {
            index = pool->free_slots[--pool->free_count];
            if (index < pool->cursor && pool->occupied[index] == 0) { found = true; break; }
        }
        if (!found) return false;
    }
    pool->occupied[index] = 1;
    ++pool->live_count;
    corbo_counter_sub(&pool->record->unused, pool->width);
    result->pool = pool;
    result->index = index;
    result->slot = pool->data + index * pool->width;
    return true;
}
// Cleanup precedes slot release. The cursor follows the last occupied slot.
static inline void corbo_allocation_drop(corbo_allocation *value) {
    corbo_pool_state *pool = value->pool;
    if (pool == NULL) return;
    if (value->index >= pool->capacity || pool->occupied[value->index] == 0)
        corbo_fail("corbo: invalid pool allocation release");
    value->pool = NULL;
    if (pool->destroy != NULL) pool->destroy(value->slot);
    pool->occupied[value->index] = 0;
    --pool->live_count;
    corbo_counter_add(&pool->record->unused, pool->width);
    if (value->index + 1 == pool->cursor) {
        while (pool->cursor != 0 && pool->occupied[pool->cursor - 1] == 0) --pool->cursor;
    } else {
        // There is at most one indexed entry for each current interior hole.
        if (pool->free_count == pool->capacity) {
            size_t count = 0;
            for (size_t hole = 0; hole < pool->cursor; ++hole)
                if (pool->occupied[hole] == 0) pool->free_slots[count++] = hole;
            pool->free_count = count;
        } else {
            pool->free_slots[pool->free_count++] = value->index;
        }
    }
    value->slot = NULL;
}
// Pool destruction never silently abandons outstanding owners.
static inline void corbo_pool_drop(corbo_pool *descriptor) {
    corbo_pool_state *pool = descriptor->state;
    if (pool == NULL) return;
    if (pool->live_count != 0) corbo_fail("corbo: pool still has live allocations");
    corbo_counter_sub(&pool->record->unused, pool->capacity * pool->width);
    descriptor->state = NULL;
}
#endif
