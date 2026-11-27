// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_REGIONS_HPP
#define CORBO_CPP_REGIONS_HPP
#if !defined(_WIN32)
#include <pthread.h>
#endif
// A lock belongs to one band, never to all datastacks in the process.
struct corbo_band_lock {
#if defined(_WIN32)
    SRWLOCK native;
#else
    pthread_mutex_t native;
#endif
};
static inline void corbo_band_lock_init(corbo_band_lock *lock) {
#if defined(_WIN32)
    InitializeSRWLock(&lock->native);
#else
    if (pthread_mutex_init(&lock->native, NULL) != 0) corbo_fail("corbo: region lock initialization failed");
#endif
}
static inline void corbo_band_acquire(corbo_band_lock *lock) {
#if defined(_WIN32)
    AcquireSRWLockExclusive(&lock->native);
#else
    if (pthread_mutex_lock(&lock->native) != 0) corbo_fail("corbo: region lock failed");
#endif
}
static inline void corbo_band_release(corbo_band_lock *lock) {
#if defined(_WIN32)
    ReleaseSRWLockExclusive(&lock->native);
#else
    if (pthread_mutex_unlock(&lock->native) != 0) corbo_fail("corbo: region unlock failed");
#endif
}
// Metadata is in the band's own datastack prefix; payload occupies fixed regions.
struct corbo_region_band {
    corbo_datastack mapping;
    corbo_band_lock lock;
    corbo_region_band *parent;
    uint8_t *occupied;
    size_t *lengths;
    size_t *free_slots;
    size_t prefix;
    size_t maximum;
    size_t stride;
    size_t capacity;
    size_t cursor;
    size_t free_count;
    size_t live_count;
    bool closed;
};
struct corbo_region {
    corbo_region_band *band;
    uint8_t *data;
    size_t index;
    size_t len;
    size_t width;
    size_t maximum;
    void (*destroy)(void *);
};
static inline bool corbo_region_can_append(const corbo_region *region, size_t count) {
    return region != NULL && region->band != NULL && region->width != 0
        && count <= region->maximum / region->width - region->len;
}
inline thread_local corbo_region_band *corbo_current_band;
inline thread_local corbo_region_band *corbo_global_band;
// A task borrows its creation policy; it must not traverse or close ancestors.
inline thread_local corbo_region_band *corbo_region_floor;
inline size_t corbo_region_stack_size;
inline size_t corbo_region_reclaim_threshold = 16ULL * 1024 * 1024;
inline size_t corbo_region_size = 100ULL * 1024 * 1024;

// Configure defaults before starting program branches. No memory is mapped yet.
static inline void corbo_regions_configure(size_t stack_size, size_t region_size) {
    corbo_region_stack_size = stack_size;
    if (region_size != 0) corbo_region_size = region_size;
}
static inline size_t corbo_aligned_extent(size_t value, size_t alignment) {
    if (value > SIZE_MAX - (alignment - 1)) corbo_fail("corbo: regional size overflow");
    return (value + alignment - 1) / alignment * alignment;
}
// Reserve one datastack with a fixed metadata prefix and count payload regions.
static inline corbo_region_band *corbo_band_new(size_t maximum, size_t count, bool closed) {
    if (maximum == 0) corbo_fail("corbo: empty region limit");
    size_t stride = corbo_aligned_extent(maximum, alignof(max_align_t));
    if (count == 0) {
        size_t budget = corbo_region_stack_size != 0 ? corbo_region_stack_size : corbo_default_capacity();
        count = budget / stride;
        if (count == 0) corbo_fail("corbo: region exceeds region-datastack capacity");
    }
    if (count > (SIZE_MAX - sizeof(corbo_region_band) - alignof(max_align_t)) / (2 * sizeof(size_t) + 1))
        corbo_fail("corbo: regional metadata overflow");
    size_t prefix = corbo_aligned_extent(sizeof(corbo_region_band) + count * (2 * sizeof(size_t) + 1), alignof(max_align_t));
    if (count > (SIZE_MAX - prefix) / stride) corbo_fail("corbo: regional reservation overflow");
    corbo_datastack mapping = {};
    corbo_datastack_open(&mapping, prefix + count * stride);
    corbo_region_band *band = ::new (corbo_datastack_alloc(&mapping, sizeof(corbo_region_band), alignof(corbo_region_band))) corbo_region_band{};
    band->free_slots = (size_t *)corbo_datastack_alloc(&mapping, count * sizeof(size_t), alignof(size_t));
    band->lengths = (size_t *)corbo_datastack_alloc(&mapping, count * sizeof(size_t), alignof(size_t));
    memset(band->lengths, 0, count * sizeof(size_t));
    band->occupied = (uint8_t *)corbo_datastack_alloc(&mapping, count, 1);
    memset(band->occupied, 0, count);
    band->mapping = mapping;
    band->mapping.reclaim_threshold = corbo_region_reclaim_threshold;
    band->prefix = prefix;
    band->maximum = maximum;
    band->stride = stride;
    band->capacity = count;
    band->closed = closed;
    corbo_band_lock_init(&band->lock);
    return band;
}
// Release only after the last region and owning scope have finished.
static inline void corbo_band_dispose(corbo_region_band *band) {
    corbo_datastack mapping = band->mapping;
#if !defined(_WIN32)
    if (pthread_mutex_destroy(&band->lock.native) != 0) corbo_fail("corbo: region lock still in use");
#endif
    corbo_datastack_close(&mapping);
}
// Enter an explicit region scope; an identical inherited layout can be reused.
static inline corbo_region_band *corbo_region_enter(size_t maximum, size_t count) {
    corbo_region_band *mark = corbo_current_band;
    size_t inherited = mark != NULL ? mark->maximum : corbo_region_size;
    if (count == 0 && maximum == inherited) return mark;
    corbo_region_band *band = corbo_band_new(maximum, count == 0 ? 1 : count, false);
    band->parent = mark;
    corbo_current_band = band;
    return mark;
}
// Closing does not invalidate a transferred region; its final owner releases it.
static inline void corbo_region_restore(corbo_region_band *mark) {
    while (corbo_current_band != mark) {
        corbo_region_band *band = corbo_current_band;
        if (band == NULL) corbo_fail("corbo: invalid region scope restoration");
        corbo_current_band = band->parent;
        corbo_band_acquire(&band->lock);
        band->closed = true;
        bool empty = band->live_count == 0;
        corbo_band_release(&band->lock);
        if (empty) corbo_band_dispose(band);
    }
}
// Allocate a stable region index. Descriptors can move without relinking a list.
static inline void corbo_region_init(corbo_region *region, size_t width, void (*destroy)(void *)) {
    if (corbo_current_band == NULL && corbo_global_band == NULL)
        corbo_global_band = corbo_band_new(corbo_region_size, 0, false);
    corbo_region_band *band = corbo_current_band != NULL ? corbo_current_band : corbo_global_band;
    corbo_band_acquire(&band->lock);
    size_t index = band->cursor;
    if (index < band->capacity) ++band->cursor;
    else {
        bool found = false;
        while (band->free_count != 0) {
            index = band->free_slots[--band->free_count];
            if (index < band->cursor && band->occupied[index] == 0) { found = true; break; }
        }
        if (!found) {
            corbo_band_release(&band->lock);
            // Explicit child layouts can spill to a dedicated band as before.
            if (band == corbo_global_band)
                corbo_fail("corbo: region datastack exhausted");
            band = corbo_band_new(band->maximum, 1, true);
            corbo_band_acquire(&band->lock);
            index = 0; band->cursor = 1;
        }
    }
    if (width == 0 || width > band->maximum) corbo_fail("corbo: element exceeds region limit");
    band->lengths[index] = 0;
    band->occupied[index] = 1; ++band->live_count;
    region->band = band;
    region->data = band->mapping.base + band->prefix + index * band->stride;
    region->index = index; region->len = 0; region->width = width;
    region->maximum = band->maximum; region->destroy = destroy;
    corbo_band_release(&band->lock);
}
// Extend within the stable region and commit only the newly needed extent.
static inline void *corbo_region_append(corbo_region *region, size_t count) {
    if (region->band == NULL || count > region->maximum / region->width - region->len)
        corbo_fail("corbo: region capacity exceeded");
    corbo_region_band *band = region->band;
    size_t old = region->len;
    size_t end = band->prefix + region->index * band->stride + (old + count) * region->width;
    corbo_band_acquire(&band->lock);
    corbo_datastack_commit(&band->mapping, end);
    band->lengths[region->index] += count * region->width;
    corbo_counter_add(&band->mapping.record->occupied, count * region->width);
    corbo_band_release(&band->lock);
    region->len += count;
    return region->data + old * region->width;
}
// Collection extraction changes the live payload size without moving addresses.
static inline void corbo_region_shrink(corbo_region *region, size_t count) {
    if (count > region->len) corbo_fail("corbo: invalid region shrink");
    corbo_region_band *band = region->band;
    corbo_band_acquire(&band->lock);
    region->len -= count;
    band->lengths[region->index] -= count * region->width;
    corbo_counter_sub(&band->mapping.record->occupied, count * region->width);
    corbo_band_release(&band->lock);
}
static inline void corbo_band_reclaim(corbo_region_band *band, bool force) {
    size_t live = band->prefix;
    for (size_t at = 0; at < band->cursor; ++at)
        if (band->occupied[at] && band->lengths[at] != 0) {
            size_t end = band->prefix + at * band->stride + band->lengths[at];
            if (end > live) live = end;
        }
    corbo_datastack_reclaim(&band->mapping, live, force);
}
// Explicit child cleanup is complete before the index becomes reusable.
static inline void corbo_region_drop(corbo_region *region) {
    corbo_region_band *band = region->band;
    if (band == NULL) return;
    region->band = NULL;
    if (region->destroy != NULL)
        for (size_t at = region->len; at != 0;) region->destroy(region->data + --at * region->width);
    corbo_band_acquire(&band->lock);
    if (region->index >= band->capacity || band->occupied[region->index] == 0)
        corbo_fail("corbo: invalid region release");
    corbo_counter_sub(&band->mapping.record->occupied, band->lengths[region->index]);
    band->lengths[region->index] = 0;
    band->occupied[region->index] = 0; --band->live_count;
    if (region->index + 1 == band->cursor) {
        while (band->cursor != 0 && band->occupied[band->cursor - 1] == 0) --band->cursor;
    } else if (band->free_count == band->capacity) {
        band->free_count = 0;
        for (size_t at = 0; at < band->cursor; ++at)
            if (band->occupied[at] == 0) band->free_slots[band->free_count++] = at;
    } else { band->free_slots[band->free_count++] = region->index; }
    corbo_band_reclaim(band, false);
    bool dispose = band->closed && band->live_count == 0;
    corbo_band_release(&band->lock);
    if (dispose) corbo_band_dispose(band);
    region->data = NULL; region->len = 0;
}
// Annotation-triggered reclamation follows cleanup and cursor restoration.
static inline void corbo_free_pages() {
    corbo_datastack_reclaim(&corbo_fixed_stack, corbo_fixed_stack.cursor, true);
    for (corbo_region_band *band = corbo_current_band; band != NULL; band = band->parent) {
        corbo_band_acquire(&band->lock); corbo_band_reclaim(band, true); corbo_band_release(&band->lock);
        if (band == corbo_region_floor) break;
    }
    if (corbo_global_band != NULL) {
        corbo_band_acquire(&corbo_global_band->lock); corbo_band_reclaim(corbo_global_band, true); corbo_band_release(&corbo_global_band->lock);
    }
}
// Thread/program teardown closes the default band after generated root cleanup.
static inline void corbo_regions_close() {
    corbo_region_restore(corbo_region_floor);
    corbo_region_band *band = corbo_global_band;
    corbo_global_band = NULL;
    if (band == NULL) return;
    corbo_band_acquire(&band->lock);
    band->closed = true;
    bool empty = band->live_count == 0;
    corbo_band_release(&band->lock);
    if (empty) corbo_band_dispose(band);
}
#endif
