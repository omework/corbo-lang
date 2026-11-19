/** @file hashmap.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
enum { MAP_BUCKETS = 16 };

/** Rounds a map header or entry width to max_align_t, terminating on overflow. */
static size_t map_align(size_t n) {
    size_t align = _Alignof(max_align_t);
    if (n > SIZE_MAX - (align - 1)) region_error();
    return (n + align - 1) / align * align;
}

/** Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback. */
static inline __attribute__((unused)) RegionalMap *map_new(size_t width, void (*dispose)(void *)) {
#ifdef _WIN32
    void *storage = VirtualAlloc(NULL, sizeof(RegionalMap), MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!storage) region_error();
#else
    void *storage = mmap(NULL, sizeof(RegionalMap), PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (storage == MAP_FAILED) region_error();
#endif
    RegionalMap *map = storage;
    *map = (RegionalMap){.width=width,.dispose=dispose};
    value_region_new(&map->region, 1, 0, !current_band && !global_budget);
    return map;
}

/** Commits additional bytes in a map region without moving existing entries; capacity failure terminates. */
static void map_extend(RegionalMap *map, size_t bytes) {
    Region *r = &map->region;
    if (!bytes || bytes > r->bytes - r->len) region_error();
    r->len += bytes - 1;
    (void)value_region_add(r);
}

/** Returns the bucket-chain link containing key or the insertion link at its end; bucket storage must be initialized. */
static size_t *map_link(RegionalMap *map, uint64_t key) {
    uint64_t hash = (key ^ (key >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    hash ^= hash >> 27;
    unsigned char *data = map->region.data;
    size_t *link = (size_t *)data + (hash % MAP_BUCKETS);
    while (*link != 0) {
        MapEntry *entry = (MapEntry *)(data + *link);
        if (entry->key == key) break;
        link = &entry->next;
    }
    return link;
}

/** Returns the stored value address for key, or zero when absent; the map retains ownership. */
static inline __attribute__((unused)) void *map_get(RegionalMap *map, uint64_t key) {
    if (!map->region.len) return NULL;
    size_t slot = *map_link(map, key);
    return slot ? map->region.data + slot + map_align(sizeof(MapEntry)) : NULL;
}

/** Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists. */
static inline __attribute__((unused)) bool map_insert(RegionalMap *map, uint64_t key, const void *incoming, void *previous) {
    Region *r = &map->region;
    if (!r->len) {
        size_t index_bytes = map_align(MAP_BUCKETS * sizeof(size_t));
        map_extend(map, index_bytes);
        memset(r->data, 0, index_bytes);
    }
    size_t header = map_align(sizeof(MapEntry));
    size_t *link = map_link(map, key);
    size_t slot = *link;
    bool replaced = slot != 0;
    if (replaced) {
        memcpy(previous, r->data + slot + header, map->width);
    } else {
        if (map->free_slot) {
            slot = map->free_slot;
            map->free_slot = ((MapEntry *)(r->data + slot))->next;
        } else {
            if (map->width > SIZE_MAX - header) region_error();
            slot = r->len;
            map_extend(map, map_align(header + map->width));
        }
        *(MapEntry *)(r->data + slot) = (MapEntry){.key=key};
        *link = slot;
    }
    memcpy(r->data + slot + header, incoming, map->width);
    return replaced;
}

/** Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse. */
static inline __attribute__((unused)) bool map_remove(RegionalMap *map, uint64_t key, void *previous) {
    if (!map->region.len) return false;
    size_t *link = map_link(map, key);
    size_t slot = *link;
    if (!slot) return false;
    unsigned char *data = map->region.data;
    MapEntry *entry = (MapEntry *)(data + slot);
    memcpy(previous, data + slot + map_align(sizeof(MapEntry)), map->width);
    *link = entry->next;
    entry->next = map->free_slot;
    map->free_slot = slot;
    return true;
}

/** Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage. */
static inline __attribute__((unused)) void map_drop(RegionalMap **slot) {
    RegionalMap *map = *slot;
    if (!map) return;
    *slot = NULL;
    if (map->dispose && map->region.len) {
        unsigned char *data = map->region.data;
        const size_t *buckets = (const size_t *)data;
        for (size_t i = 0; i < MAP_BUCKETS; ++i) {
            for (size_t at = buckets[i]; at != 0; at = ((MapEntry *)(data + at))->next) {
                map->dispose(data + at + map_align(sizeof(MapEntry)));
            }
        }
    }
    value_region_drop(&map->region);
#ifdef _WIN32
    VirtualFree(map, 0, MEM_RELEASE);
#else
    munmap(map, sizeof(RegionalMap));
#endif
}
