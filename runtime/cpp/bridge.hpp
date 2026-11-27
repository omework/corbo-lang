// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_BRIDGE_HPP
#define CORBO_CPP_BRIDGE_HPP
// Public names used by unchecked STD bindings. Definitions are primitive C++.
typedef corbo_region CorboRegion;
// Caller owns descriptor storage; this function initializes only its region.
static inline void corbo_region_new(CorboRegion *region, size_t width, bool) {
    *region = {};
    corbo_region_init(region, width, NULL);
}
static inline void *corbo_region_push(CorboRegion *region) {
    return corbo_region_append(region, 1);
}
static inline bool vector_pop(CorboRegion *region, void *output) {
    if (region->len == 0) return false;
    corbo_region_shrink(region, 1);
    memcpy(output, region->data + region->len * region->width, region->width);
    return true;
}
static inline void corbo_region_clear(CorboRegion *region) {
    if (region->destroy != NULL)
        for (size_t at = region->len; at != 0;)
            region->destroy(region->data + --at * region->width);
    corbo_region_shrink(region, region->len);
}
static inline void vector_remove(CorboRegion *region, size_t index, void *output) {
    if (index >= region->len) corbo_fail("corbo: vector index out of bounds");
    memcpy(output, region->data + index * region->width, region->width);
    corbo_region_shrink(region, 1);
    memmove(region->data + index * region->width, region->data + (index + 1) * region->width,
            (region->len - index) * region->width);
}
static inline void vector_insert(CorboRegion *region, size_t index, const void *input) {
    if (index > region->len) corbo_fail("corbo: vector insertion index out of bounds");
    size_t previous = region->len;
    corbo_region_append(region, 1);
    memmove(region->data + (index + 1) * region->width,
            region->data + index * region->width,
            (previous - index) * region->width);
    memcpy(region->data + index * region->width, input, region->width);
}
static inline void vector_replace(CorboRegion *region, size_t index,
                                  const void *input, void *previous) {
    if (index >= region->len) corbo_fail("corbo: vector replacement index out of bounds");
    void *slot = region->data + index * region->width;
    memcpy(previous, slot, region->width);
    memcpy(slot, input, region->width);
}
static inline void region_append(CorboRegion *region, const void *bytes, size_t count) {
    void *destination = corbo_region_append(region, count);
    if (count != 0) memcpy(destination, bytes, count);
}
// Stable private registrations are themselves fixed datastacks, not heap blocks.
struct corbo_region_registration {
    corbo_datastack storage;
    CorboRegion region;
};
static inline CorboRegion *corbo_region_register(size_t width) {
    corbo_datastack storage = {};
    corbo_datastack_open(&storage, sizeof(corbo_region_registration));
    corbo_region_registration *registration = ::new(corbo_datastack_alloc(&storage,
        sizeof(corbo_region_registration), alignof(corbo_region_registration))) corbo_region_registration{};
    registration->storage = storage;
    corbo_region_new(&registration->region, width, false);
    return &registration->region;
}
static inline void corbo_region_unregister(CorboRegion *region) {
    corbo_region_registration *registration = (corbo_region_registration *)
        ((uint8_t *)region - offsetof(corbo_region_registration, region));
    corbo_region_drop(region);
    corbo_datastack storage = registration->storage;
    corbo_datastack_close(&storage);
}
#endif
