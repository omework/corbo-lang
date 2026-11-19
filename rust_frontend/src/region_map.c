typedef struct {
    uint64_t key;
    size_t next;
} CrustMapEntry;

typedef struct CrustMap {
    CrustGrowing contents;
    struct CrustMap *next;
    size_t free_slot;
    size_t owner;
    void (*destroy_entry)(void *);
} CrustMap;

enum { CRUST_MAP_BUCKETS = 16 };
static CRUST_LOCAL CrustMap *crust_maps;
static CRUST_LOCAL size_t crust_map_depth;

static inline __attribute__((unused)) void crust_map_new(CrustMap *map, bool dedicated) {
    CrustGrowing region = dedicated ? crust_region_take_dedicated() : crust_region_take();
    *map = (CrustMap){ .contents = region, .next = crust_maps, .owner = crust_map_depth };
    crust_maps = map;
}

static void crust_map_unlink(CrustMap *map) {
    CrustMap **link = &crust_maps;
    while (*link != map)
        link = &(*link)->next;
    *link = map->next;
    map->next = NULL;
}

static void crust_map_destroy(CrustMap *map);

static inline __attribute__((unused)) void crust_map_drop(CrustMap *map) {
    crust_map_unlink(map);
    crust_map_destroy(map);
}

static inline __attribute__((unused)) void crust_map_attach(CrustMap *map, size_t owner) {
    map->owner = owner;
    map->next = crust_maps;
    crust_maps = map;
}

static inline __attribute__((unused)) void crust_map_resource(CrustMap *map, size_t owner, int action) {
    switch (action) {
    case CRUST_REHOME: map->owner = owner; break;
    case CRUST_ATTACH: crust_map_attach(map, owner); break;
    case CRUST_DETACH: crust_map_unlink(map); break;
    case CRUST_DESTROY: crust_map_destroy(map); break;
    case CRUST_DROP: crust_map_drop(map); break;
    default: abort();
    }
}

static void crust_map_rewind(size_t mark) {
    CrustMap **link = &crust_maps;
    while (*link != NULL) {
        CrustMap *map = *link;
        if (map->owner > mark) {
            *link = map->next;
            crust_map_destroy(map);
        } else {
            link = &map->next;
        }
    }
    crust_map_depth = mark;
}

static size_t crust_map_round(size_t bytes) {
    const size_t alignment = _Alignof(max_align_t);
    size_t remainder = bytes % alignment;
    return remainder ? bytes + alignment - remainder : bytes;
}

static void crust_map_destroy(CrustMap *map) {
    if (map->destroy_entry != NULL && map->contents.used != 0) {
        unsigned char *data = crust_region_data(&map->contents);
        const size_t *buckets = (const size_t *)data;
        for (size_t bucket = 0; bucket < CRUST_MAP_BUCKETS; ++bucket) {
            for (size_t slot = buckets[bucket]; slot != 0;) {
                CrustMapEntry *entry = (CrustMapEntry *)(data + slot);
                map->destroy_entry(data + slot + crust_map_round(sizeof(*entry)));
                slot = entry->next;
            }
        }
    }
    crust_region_release(&map->contents);
}

static inline __attribute__((unused)) size_t crust_map_growth_bound(size_t bytes) {
    return crust_map_round(CRUST_MAP_BUCKETS * sizeof(size_t))
        + crust_map_round(crust_map_round(sizeof(CrustMapEntry)) + bytes);
}

static size_t *crust_map_find(CrustMap *map, uint64_t key) {
    key ^= key >> 30;
    uint64_t hash = key * UINT64_C(0xbf58476d1ce4e5b9);
    hash ^= hash >> 27;
    return (size_t *)crust_region_data(&map->contents) + (hash % CRUST_MAP_BUCKETS);
}

static size_t *crust_map_link(CrustMap *map, uint64_t key) {
    /* The hash selects a chain; equality uses the original key. */
    size_t *link = crust_map_find(map, key);
    unsigned char *data = crust_region_data(&map->contents);
    while (*link != 0) {
        CrustMapEntry *entry = (CrustMapEntry *)(data + *link);
        if (entry->key == key)
            break;
        link = &entry->next;
    }
    return link;
}

static inline __attribute__((unused)) void *crust_map_get(CrustMap *map, uint64_t key) {
    if (map->contents.used == 0)
        return NULL;
    size_t slot = *crust_map_link(map, key);
    return slot == 0 ? NULL : crust_region_data(&map->contents)
        + slot + crust_map_round(sizeof(CrustMapEntry));
}

static inline __attribute__((unused)) bool crust_map_insert(
    CrustMap *map, uint64_t key, const void *incoming, size_t size, void *previous
) {
    CrustGrowing *region = &map->contents;
    size_t header = crust_map_round(sizeof(CrustMapEntry));
    if (size > region->band->limit || header > region->band->limit - size)
        crust_region_error();
    size_t stride = crust_map_round(header + size);
    unsigned char *data = crust_region_data(region);
    if (region->used == 0) {
        size_t index_bytes = crust_map_round(CRUST_MAP_BUCKETS * sizeof(size_t));
        if (index_bytes > region->band->limit)
            crust_region_error();
        memset(data, 0, index_bytes);
        region->used = index_bytes;
    }
    size_t *link = crust_map_link(map, key);
    bool replaced = *link != 0;
    size_t slot = *link;
    if (!replaced) {
        if (map->free_slot != 0) {
            slot = map->free_slot;
            map->free_slot = ((CrustMapEntry *)(data + slot))->next;
        } else {
            if (stride > region->band->limit - region->used)
                crust_region_error();
            slot = region->used;
            region->used += stride;
        }
        *(CrustMapEntry *)(data + slot) = (CrustMapEntry){ .key = key };
        *link = slot;
    } else {
        memcpy(previous, data + slot + header, size);
    }
    memcpy(data + slot + header, incoming, size);
    return replaced;
}

static inline __attribute__((unused)) bool crust_map_remove(
    CrustMap *map, uint64_t key, size_t size, void *previous
) {
    if (map->contents.used == 0)
        return false;
    size_t *link = crust_map_link(map, key);
    size_t slot = *link;
    if (slot == 0)
        return false;
    unsigned char *data = crust_region_data(&map->contents);
    CrustMapEntry *entry = (CrustMapEntry *)(data + slot);
    memcpy(previous, data + slot + crust_map_round(sizeof(CrustMapEntry)), size);
    *link = entry->next;
    entry->next = map->free_slot;
    map->free_slot = slot;
    return true;
}
