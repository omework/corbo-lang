"""Native HashMap storage for the generated C runtime."""

HASHMAP_RUNTIME = r'''
typedef struct {
    uint64_t key;
    size_t next_free;
    int occupied;
} CrustMapEntry;

typedef struct {
    GrowthStack stack;
    size_t stride, value_offset, value_size;
    size_t slots, count, bucket_count, free_slot;
} CrustHashMap;

_Static_assert(offsetof(Cell, fields) % _Alignof(CrustHashMap) == 0,
               "alignement du stockage HashMap");

typedef enum {
    CRUST_MAP_FULL, CRUST_MAP_INSERTED, CRUST_MAP_REPLACED
} CrustMapInsertion;

static CrustHashMap crust_map_new(size_t limit, size_t value_size, size_t alignment) {
    if (!alignment || _Alignof(max_align_t) % alignment || !value_size)
        fail("disposition de valeur HashMap invalide");
    size_t stride_alignment = _Alignof(max_align_t);
    size_t value_offset = (sizeof(CrustMapEntry) + alignment - 1) / alignment * alignment;
    if (value_size > SIZE_MAX - value_offset - (stride_alignment - 1))
        fail("valeur HashMap trop grande");
    size_t stride = (value_offset + value_size + stride_alignment - 1)
                    / stride_alignment * stride_alignment;
    limit -= limit % _Alignof(size_t);
    return (CrustHashMap){
        .stack = growth_stack(limit), .stride = stride,
        .value_offset = value_offset, .value_size = value_size,
        .free_slot = SIZE_MAX
    };
}

static CrustMapEntry *crust_map_entry(CrustHashMap *map, size_t slot) {
    return (CrustMapEntry *)(void *)(map->stack.mapping.base + slot * map->stride);
}

static void *crust_map_value(CrustHashMap *map, CrustMapEntry *entry) {
    return (unsigned char *)entry + map->value_offset;
}

static size_t *crust_map_index(CrustHashMap *map) {
    return (size_t *)(void *)(map->stack.mapping.base + map->stack.high);
}

static size_t crust_map_home(CrustHashMap *map, uint64_t key) {
    key ^= key >> 30;
    key *= UINT64_C(0xbf58476d1ce4e5b9);
    key ^= key >> 27;
    key *= UINT64_C(0x94d049bb133111eb);
    key ^= key >> 31;
    return (size_t)key & (map->bucket_count - 1);
}

static size_t crust_map_find(CrustHashMap *map, uint64_t key) {
    size_t *index = crust_map_index(map);
    size_t bucket = crust_map_home(map, key);
    while (index[bucket] && crust_map_entry(map, index[bucket] - 1)->key != key)
        bucket = (bucket + 1) & (map->bucket_count - 1);
    return bucket;
}

static void crust_map_reindex(CrustHashMap *map, size_t buckets, size_t offset) {
    map->stack.high = offset;
    map->bucket_count = buckets;
    size_t *index = crust_map_index(map);
    memset(index, 0, buckets * sizeof(*index));
    for (size_t slot = 0; slot < map->slots; ++slot) {
        CrustMapEntry *entry = crust_map_entry(map, slot);
        if (entry->occupied) index[crust_map_find(map, entry->key)] = slot + 1;
    }
}

static void *crust_map_get(CrustHashMap *map, uint64_t key) {
    if (!map->bucket_count) return NULL;
    size_t slot = crust_map_index(map)[crust_map_find(map, key)];
    return slot ? crust_map_value(map, crust_map_entry(map, slot - 1)) : NULL;
}

/* The caller owns incoming on FULL and receives previous only on REPLACED. */
static CrustMapInsertion crust_map_try_insert(CrustHashMap *map, uint64_t key,
                                               const void *incoming, void *previous) {
    void *present = crust_map_get(map, key);
    if (present) {
        memcpy(previous, present, map->value_size);
        memcpy(present, incoming, map->value_size);
        return CRUST_MAP_REPLACED;
    }

    size_t buckets = map->bucket_count;
    if (!buckets) {
        buckets = 4;
    } else if (map->count == buckets - buckets / 4) {
        if (buckets > SIZE_MAX / 2) return CRUST_MAP_FULL;
        buckets *= 2;
    }
    size_t limit = map->stack.mapping.capacity;
    if (buckets > limit / sizeof(size_t)) return CRUST_MAP_FULL;
    size_t offset = limit - buckets * sizeof(size_t);
    size_t low = map->stack.low;
    if (offset < low || (map->free_slot == SIZE_MAX && map->stride > offset - low))
        return CRUST_MAP_FULL;

    if (buckets != map->bucket_count) crust_map_reindex(map, buckets, offset);
    size_t slot = map->free_slot;
    if (slot == SIZE_MAX) {
        slot = map->slots++;
        map->stack.low += map->stride;
    } else {
        map->free_slot = crust_map_entry(map, slot)->next_free;
    }
    CrustMapEntry *entry = crust_map_entry(map, slot);
    *entry = (CrustMapEntry){.key = key, .occupied = 1};
    memcpy(crust_map_value(map, entry), incoming, map->value_size);
    crust_map_index(map)[crust_map_find(map, key)] = slot + 1;
    ++map->count;
    return CRUST_MAP_INSERTED;
}

static int crust_map_insert(CrustHashMap *map, uint64_t key, const void *incoming,
                            void *previous) {
    CrustMapInsertion result = crust_map_try_insert(map, key, incoming, previous);
    if (result == CRUST_MAP_FULL) fail("capacité de la HashMap dépassée");
    return result == CRUST_MAP_REPLACED;
}

static int crust_map_remove(CrustHashMap *map, uint64_t key, void *previous) {
    if (!map->bucket_count) return 0;
    size_t *index = crust_map_index(map);
    size_t hole = crust_map_find(map, key);
    if (!index[hole]) return 0;
    size_t slot = index[hole] - 1;
    CrustMapEntry *entry = crust_map_entry(map, slot);
    memcpy(previous, crust_map_value(map, entry), map->value_size);
    entry->occupied = 0;
    entry->next_free = map->free_slot;
    map->free_slot = slot;
    --map->count;

    /* Shift only indices whose search would otherwise stop at the hole. */
    size_t mask = map->bucket_count - 1;
    for (size_t probe = (hole + 1) & mask; index[probe]; probe = (probe + 1) & mask) {
        size_t home = crust_map_home(map, crust_map_entry(map, index[probe] - 1)->key);
        if (((hole - home) & mask) < ((probe - home) & mask)) {
            index[hole] = index[probe];
            hole = probe;
        }
    }
    index[hole] = 0;
    return 1;
}

static void crust_map_drop(CrustHashMap *map, void (*drop_value)(void *)) {
    if (drop_value) {
        for (size_t slot = map->slots; slot > 0; --slot) {
            CrustMapEntry *entry = crust_map_entry(map, slot - 1);
            if (entry->occupied) drop_value(crust_map_value(map, entry));
        }
    }
    growth_close(&map->stack);
    *map = (CrustHashMap){0};
}

typedef union {
    uint64_t bits;
    double floating;
    void *pointer;
    CrustStructureView structure;
} CrustMapValue;

typedef struct {
    int status;
    void *slot;
    CrustMapValue value;
} CrustMapResult;

static CrustHashMap *crust_map_data(Cell *cell) {
    return (CrustHashMap *)(void *)cell->fields;
}

static void crust_map_drop_handle(void *item) {
    Cell *value;
    memcpy(&value, item, sizeof(value));
    cell_drop(value);
}

static void crust_map_drop_plain(Cell *cell) {
    crust_map_drop(crust_map_data(cell), NULL);
}

static void crust_map_drop_owned(Cell *cell) {
    crust_map_drop(crust_map_data(cell), crust_map_drop_handle);
}

static Cell *crust_map_cell_new(Source *source, size_t capacity, size_t value_size,
                                size_t alignment, int owned) {
    static const Source plain = {.drop_payload = crust_map_drop_plain};
    static const Source handles = {.drop_payload = crust_map_drop_owned};
    Cell *cell = local_cell_new(source, owned ? &handles : &plain, sizeof(CrustHashMap), NULL);
    CrustHashMap map = crust_map_new(capacity, value_size, alignment);
    memcpy(cell->fields, &map, sizeof(map));
    return cell;
}

static CrustMapResult crust_map_write(Cell *cell, uint64_t key, const void *value, int fallible) {
    CrustHashMap *map = crust_map_data(cell);
    CrustMapResult result = {0};
    CrustMapInsertion status = crust_map_try_insert(map, key, value, &result.value);
    if (status == CRUST_MAP_FULL) {
        if (!fallible) fail("capacité de la HashMap dépassée");
        result.status = 5;
        memcpy(&result.value, value, map->value_size);
    } else if (status == CRUST_MAP_INSERTED) {
        result.status = 6;
    }
    return result;
}

static CrustMapResult crust_map_lookup(Cell *cell, uint64_t key, int remove) {
    CrustHashMap *map = crust_map_data(cell);
    CrustMapResult result = {0};
    if (remove) {
        if (!crust_map_remove(map, key, &result.value)) result.status = 6;
    } else {
        result.slot = crust_map_get(map, key);
        if (!result.slot) result.status = 6;
    }
    return result;
}

static Cell *crust_map_result_handle(const CrustMapResult *result) {
    Cell *cell;
    memcpy(&cell, &result->value, sizeof(cell));
    return cell;
}
'''
