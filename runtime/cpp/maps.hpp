// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_MAPS_HPP
#define CORBO_CPP_MAPS_HPP
// Entries never move during index growth. Only the integer lookup index changes.
struct corbo_map_entry { uint64_t key; size_t next_free; bool live; };
struct corbo_map {
    corbo_region entries;
    corbo_region index;
    size_t value_width;
    size_t value_offset;
    size_t count;
    size_t free_head;
    void (*destroy)(void *);
};
static inline uint64_t corbo_map_hash(uint64_t key) {
    key ^= key >> 30; key *= UINT64_C(0xbf58476d1ce4e5b9);
    key ^= key >> 27; key *= UINT64_C(0x94d049bb133111eb);
    return key ^ (key >> 31);
}
static inline corbo_map_entry *corbo_map_entry_at(corbo_map *map, size_t index) {
    return (corbo_map_entry *)(map->entries.data + index * map->entries.width);
}
static inline void *corbo_map_payload(corbo_map *map, corbo_map_entry *entry) {
    return (uint8_t *)entry + map->value_offset;
}
// Both growable components are independently bounded by the current region policy.
static inline void corbo_map_init(corbo_map *map, size_t width, size_t alignment, void (*destroy)(void *)) {
    map->value_offset = corbo_aligned_extent(sizeof(corbo_map_entry), alignment);
    if (width > SIZE_MAX - map->value_offset) corbo_fail("corbo: map entry size overflow");
    size_t stride = corbo_aligned_extent(map->value_offset + width, alignof(max_align_t));
    corbo_region_init(&map->entries, stride, NULL);
    corbo_region_init(&map->index, sizeof(size_t), NULL);
    map->value_width = width; map->count = 0; map->free_head = SIZE_MAX; map->destroy = destroy;
}
static inline size_t corbo_map_bucket(corbo_map *map, uint64_t key) {
    size_t capacity = map->index.len;
    size_t bucket = (size_t)corbo_map_hash(key) & (capacity - 1);
    size_t *slots = (size_t *)map->index.data;
    for (size_t visited = 0; visited < capacity; ++visited) {
        size_t encoded = slots[bucket];
        if (encoded == 0 || corbo_map_entry_at(map, encoded - 1)->key == key) return bucket;
        bucket = (bucket + 1) & (capacity - 1);
    }
    corbo_fail("corbo: map lookup index exhausted");
}
// Rebuild from stable live entries; no entry payload is copied or relocated.
static inline void corbo_map_reindex(corbo_map *map, size_t capacity) {
    if (capacity > map->index.maximum / sizeof(size_t)) corbo_fail("corbo: map index region exhausted");
    if (capacity > map->index.len) corbo_region_append(&map->index, capacity - map->index.len);
    memset(map->index.data, 0, capacity * sizeof(size_t));
    map->index.len = capacity;
    for (size_t at = 0; at < map->entries.len; ++at) {
        corbo_map_entry *entry = corbo_map_entry_at(map, at);
        if (entry->live) ((size_t *)map->index.data)[corbo_map_bucket(map, entry->key)] = at + 1;
    }
}
static inline void *corbo_map_get(corbo_map *map, uint64_t key) {
    if (map->index.len == 0) return NULL;
    size_t encoded = ((size_t *)map->index.data)[corbo_map_bucket(map, key)];
    return encoded == 0 ? NULL : corbo_map_payload(map, corbo_map_entry_at(map, encoded - 1));
}
// Returns the replaced value through caller storage; insertion owns input bytes.
static inline bool corbo_map_insert(corbo_map *map, uint64_t key, const void *input, void *previous) {
    void *existing = corbo_map_get(map, key);
    if (existing != NULL) {
        memcpy(previous, existing, map->value_width);
        memcpy(existing, input, map->value_width);
        return true;
    }
    if (map->index.len == 0) {
        size_t maximum = map->index.maximum / sizeof(size_t), initial = 8;
        while (initial > maximum && initial > 1) initial /= 2;
        if (initial < 2) corbo_fail("corbo: map index region too small");
        corbo_map_reindex(map, initial);
    }
    size_t slack = map->index.len / 3;
    if (slack == 0) slack = 1;
    if (map->count + 1 > map->index.len - slack) {
        if (map->index.len > SIZE_MAX / 2) corbo_fail("corbo: map index size overflow");
        corbo_map_reindex(map, map->index.len * 2);
    }
    size_t at;
    corbo_map_entry *entry;
    if (map->free_head != SIZE_MAX) {
        at = map->free_head; entry = corbo_map_entry_at(map, at); map->free_head = entry->next_free;
        corbo_counter_sub(&map->entries.band->mapping.record->unused, map->value_width);
    } else {
        at = map->entries.len;
        entry = ::new(corbo_region_append(&map->entries, 1)) corbo_map_entry{};
    }
    entry->key = key; entry->live = true;
    memcpy(corbo_map_payload(map, entry), input, map->value_width);
    ((size_t *)map->index.data)[corbo_map_bucket(map, key)] = at + 1;
    ++map->count;
    return false;
}
// Reuse the removed entry on later insertion; the extracted payload is not dropped.
static inline bool corbo_map_remove(corbo_map *map, uint64_t key, void *output) {
    if (map->index.len == 0) return false;
    size_t encoded = ((size_t *)map->index.data)[corbo_map_bucket(map, key)];
    if (encoded == 0) return false;
    corbo_map_entry *entry = corbo_map_entry_at(map, encoded - 1);
    memcpy(output, corbo_map_payload(map, entry), map->value_width);
    entry->live = false; entry->next_free = map->free_head; map->free_head = encoded - 1;
    --map->count;
    corbo_counter_add(&map->entries.band->mapping.record->unused, map->value_width);
    corbo_map_reindex(map, map->index.len);
    return true;
}
static inline void corbo_map_clear(corbo_map *map) {
    for (size_t at = map->entries.len; at != 0;) {
        corbo_map_entry *entry = corbo_map_entry_at(map, --at);
        if (entry->live && map->destroy != NULL) map->destroy(corbo_map_payload(map, entry));
    }
    corbo_counter_sub(&map->entries.band->mapping.record->unused, (map->entries.len - map->count) * map->value_width);
    corbo_region_shrink(&map->entries, map->entries.len); map->count = 0; map->free_head = SIZE_MAX;
    if (map->index.len != 0) memset(map->index.data, 0, map->index.len * sizeof(size_t));
}
static inline void corbo_map_drop(corbo_map *map) {
    corbo_map_clear(map);
    corbo_region_drop(&map->index); corbo_region_drop(&map->entries);
}
#endif
