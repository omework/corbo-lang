enum { CRUST_REGION_FREE, CRUST_REGION_LIVE, CRUST_REGION_DIRTY };

typedef struct CrustRegionBand {
    struct CrustRegionBand *parent;
    unsigned char *data;
    size_t limit;
    size_t stride;
    size_t count;
    size_t cursor;
    size_t live;
    size_t high_water;
    bool reclaim_pending;
    size_t metadata_bytes;
#ifdef CRUST_HAS_THREADS
    pthread_mutex_t mutex;
#endif
    bool closed;
    unsigned char occupied[];
} CrustRegionBand;

typedef struct {
    CrustRegionBand *band;
    size_t slot;
    size_t used;
} CrustGrowing;

static CRUST_LOCAL CrustRegionBand *crust_region_scope;
static CRUST_LOCAL CrustRegionBand *crust_region_global;
static CRUST_LOCAL size_t crust_region_limit = 100 * 1024 * 1024;
static CRUST_LOCAL size_t crust_region_stack_limit;
static CRUST_LOCAL bool crust_region_stack_configured;

#ifdef CRUST_HAS_THREADS
#define CRUST_LOCK_REGIONS(band) pthread_mutex_lock(&(band)->mutex)
#define CRUST_UNLOCK_REGIONS(band) pthread_mutex_unlock(&(band)->mutex)
#else
#define CRUST_LOCK_REGIONS(band) ((void)0)
#define CRUST_UNLOCK_REGIONS(band) ((void)0)
#endif

static void crust_region_error(void) {
    fputs("corbo: limite de la datastack à régions\n", stderr);
    exit(EXIT_FAILURE);
}

static size_t crust_region_size(uintmax_t bytes) {
    if (bytes == 0 || bytes > PTRDIFF_MAX)
        crust_region_error();
    return (size_t)bytes;
}

static size_t crust_region_stride(size_t size) {
    size_t alignment = _Alignof(max_align_t);
    size_t remainder = size % alignment;
    size_t padding = remainder == 0 ? 0 : alignment - remainder;
    if (padding > PTRDIFF_MAX - size)
        crust_region_error();
    return size + padding;
}

static CrustRegionBand *crust_region_band(size_t limit, size_t count) {
    size_t stride = crust_region_stride(limit);
    if (count == 0 || count > PTRDIFF_MAX / stride ||
        count > (PTRDIFF_MAX - sizeof(CrustRegionBand)) / sizeof(unsigned char))
        crust_region_error();
    size_t metadata = sizeof(CrustRegionBand) + count * sizeof(unsigned char);
    CrustRegionBand *band = crust_guarded_map(metadata);
    if (band == MAP_FAILED)
        crust_region_error();
    void *data = crust_guarded_map(stride * count);
    if (data == MAP_FAILED) {
        crust_guarded_unmap(band, metadata);
        crust_region_error();
    }
    *band = (CrustRegionBand){
        .data = data,
        .limit = limit,
        .stride = stride,
        .count = count,
        .metadata_bytes = metadata,
    };
#ifdef CRUST_HAS_THREADS
    if (pthread_mutex_init(&band->mutex, NULL) != 0)
        crust_region_error();
#endif
    return band;
}

static void crust_region_destroy(CrustRegionBand *band) {
#ifdef CRUST_HAS_THREADS
    if (pthread_mutex_destroy(&band->mutex) != 0)
        crust_region_error();
#endif
    crust_guarded_unmap(band->data, band->stride * band->count);
    crust_guarded_unmap(band, band->metadata_bytes);
}

static inline __attribute__((unused)) void crust_regions_configure(uintmax_t stack, uintmax_t limit, size_t slots) {
    if (limit != 0)
        crust_region_limit = crust_region_size(limit);
    if (stack != 0) {
        crust_region_stack_limit = crust_region_size(stack);
        crust_region_stack_configured = true;
    } else if (slots != 0) {
        size_t stride = crust_region_stride(crust_region_limit);
        if (slots > PTRDIFF_MAX / stride)
            crust_region_error();
        crust_region_stack_limit = slots * stride;
        crust_region_stack_configured = true;
    }
}

static inline __attribute__((unused)) void crust_region_enter(uintmax_t limit, uintmax_t count, size_t inferred) {
    size_t size = crust_region_size(limit);
    size_t inherited = crust_region_scope == NULL ? crust_region_limit : crust_region_scope->limit;
    if (count == 0 && size == inherited)
        return;
    size_t slots = count == 0
        ? (inferred == 0 ? 1 : inferred)
        : crust_region_size(count);
    CrustRegionBand *band = crust_region_band(size, slots);
    band->parent = crust_region_scope;
    crust_region_scope = band;
}

// Called under the region lock, after a group of releases or before reuse.
static void crust_region_trim(CrustRegionBand *band) {
    size_t cursor = band->live == 0 ? 0 : band->cursor;
    while (cursor != 0 && band->occupied[cursor - 1] != CRUST_REGION_LIVE)
        --cursor;
    if (cursor != band->cursor)
        band->cursor = cursor;
}

// Called under the band mutex. CRUST_REGION_DIRTY denotes a released slot whose pages
// may still be resident. Contiguous dead slots can share a single remapping.
static void crust_region_reclaim(CrustRegionBand *band, uintmax_t threshold, bool force) {
    if ((!force && threshold == 0) || !band->reclaim_pending)
        return;
    size_t page_size = crust_page_size();
    if (page_size == 0)
        return;
    size_t eligible = 0;
    for (int pass = 0; pass < 2; ++pass) {
        bool pending = false;
        for (size_t slot = 0; slot < band->high_water;) {
            if (band->occupied[slot] != CRUST_REGION_DIRTY) {
                ++slot;
                continue;
            }
            size_t start = slot++;
            while (slot < band->high_water && band->occupied[slot] == CRUST_REGION_DIRTY)
                ++slot;
            size_t first = start * band->stride;
            size_t bytes = crust_reclaim_pages(&first, slot * band->stride, page_size);
            if (pass == 0) {
                eligible += bytes;
            } else if (bytes != 0 && crust_reclaim_mapping(band->data + first, bytes)) {
                for (size_t i = start; i < slot; ++i)
                    band->occupied[i] = CRUST_REGION_FREE;
            } else {
                pending = true;
            }
        }
        if (pass == 0 && (eligible == 0 || (!force && eligible < threshold)))
            return;
        if (pass == 1)
            band->reclaim_pending = pending;
    }
}

// The open scope or worker and each live slot keep the band alive.
static void crust_region_close(CrustRegionBand *band, uintmax_t threshold, bool force) {
    CRUST_LOCK_REGIONS(band);
    crust_region_trim(band);
    if (band->live != 0)
        crust_region_reclaim(band, threshold, force);
    band->closed = true;
    bool destroy = band->live == 0;
    CRUST_UNLOCK_REGIONS(band);
    if (destroy)
        crust_region_destroy(band);
}

static void crust_region_restore_pages(CrustRegionBand *mark, uintmax_t threshold, bool force) {
    while (crust_region_scope != mark) {
        CrustRegionBand *band = crust_region_scope;
        crust_region_scope = band->parent;
        crust_region_close(band, threshold, force);
    }
    CrustRegionBand *inherited = mark == NULL ? crust_region_global : mark;
    if (inherited != NULL) {
        CRUST_LOCK_REGIONS(inherited);
        crust_region_trim(inherited);
        crust_region_reclaim(inherited, threshold, force);
        CRUST_UNLOCK_REGIONS(inherited);
    }
}

static inline __attribute__((unused)) void crust_region_restore(CrustRegionBand *mark) {
    crust_region_restore_pages(mark, 0, false);
}

static CrustGrowing crust_region_new_dedicated(size_t limit) {
    CrustRegionBand *band = crust_region_band(limit, 1);
    band->closed = true;
    band->occupied[0] = CRUST_REGION_LIVE;
    band->cursor = 1;
    band->high_water = 1;
    band->live = 1;
    return (CrustGrowing){ .band = band };
}

static inline __attribute__((unused)) CrustGrowing crust_region_take_dedicated(void) {
    size_t limit = crust_region_scope == NULL ? crust_region_limit : crust_region_scope->limit;
    return crust_region_new_dedicated(limit);
}

static inline __attribute__((unused)) CrustGrowing crust_region_take(void) {
    CrustRegionBand *band = crust_region_scope;
    if (band == NULL) {
        if (crust_region_global == NULL) {
            size_t capacity = crust_region_stack_configured
                ? crust_region_stack_limit : crust_default_capacity();
            crust_region_global = crust_region_band(
                crust_region_limit, capacity / crust_region_stride(crust_region_limit));
        }
        band = crust_region_global;
    }
    CRUST_LOCK_REGIONS(band);
    crust_region_trim(band);
    size_t slot = band->cursor;
    if (slot == band->count) {
        for (slot = 0; slot < band->count && band->occupied[slot] == CRUST_REGION_LIVE; ++slot) {
        }
        if (slot == band->count) {
            if (band == crust_region_global)
                crust_region_error();
            CRUST_UNLOCK_REGIONS(band);
            return crust_region_new_dedicated(band->limit);
        }
    }
    if (slot == band->cursor)
        ++band->cursor;
    if (band->cursor > band->high_water)
        band->high_water = band->cursor;
    band->occupied[slot] = CRUST_REGION_LIVE;
    ++band->live;
    CRUST_UNLOCK_REGIONS(band);
    return (CrustGrowing){ .band = band, .slot = slot };
}

static inline __attribute__((unused)) void crust_region_release(CrustGrowing *value) {
    CrustRegionBand *band = value->band;
    CRUST_LOCK_REGIONS(band);
    band->occupied[value->slot] = CRUST_REGION_DIRTY;
    band->reclaim_pending = true;
    --band->live;
    bool destroy = band->closed && band->live == 0;
    CRUST_UNLOCK_REGIONS(band);
    if (destroy)
        crust_region_destroy(band);
}

#ifdef CRUST_HAS_THREADS
static inline __attribute__((unused)) void crust_worker_close_regions(void) {
    CrustRegionBand *band = crust_region_global;
    crust_region_global = NULL;
    if (band != NULL)
        crust_region_close(band, 0, false);
}
#define CRUST_THREAD_MARK(name) size_t name##_threads = crust_thread_depth++
#define CRUST_THREAD_REWIND(name) crust_thread_rewind(name##_threads)
#else
#define CRUST_THREAD_MARK(name)
#define CRUST_THREAD_REWIND(name) ((void)0)
#endif

static inline __attribute__((unused)) unsigned char *crust_region_data(const CrustGrowing *value) {
    return value->band->data + value->slot * value->band->stride;
}

static inline __attribute__((unused)) void crust_region_append(CrustGrowing *value, const void *bytes, size_t count) {
    if (count > value->band->limit - value->used)
        crust_region_error();
    if (count != 0)
        memcpy(crust_region_data(value) + value->used, bytes, count);
    value->used += count;
}

static inline __attribute__((unused)) const void *crust_region_element(const CrustGrowing *value, uint64_t index, size_t size) {
    if (index >= value->used / size) {
        fputs("corbo: indice hors du vecteur\n", stderr);
        exit(EXIT_FAILURE);
    }
    return crust_region_data(value) + (size_t)index * size;
}

static inline __attribute__((unused)) bool crust_vector_extract(
    CrustGrowing *value, uint64_t index, size_t size, bool pop, void *result
) {
    size_t length = value->used / size;
    if (pop && length == 0)
        return false;
    if (pop)
        index = length - 1;
    const unsigned char *element = crust_region_element(value, index, size);
    memcpy(result, element, size);
    size_t offset = (size_t)index * size;
    value->used -= size;
    memmove((unsigned char *)element, element + size, value->used - offset);
    return true;
}

#ifdef CRUST_HAS_MAPS
#define CRUST_MAP_MARK(name) size_t name##_depth = crust_map_depth++
#define CRUST_MAP_REWIND(name) crust_map_rewind(name##_depth)
#else
#define CRUST_MAP_MARK(name)
#define CRUST_MAP_REWIND(name) ((void)0)
#endif

#define CRUST_REGION_MARK(name) CrustRegionBand *name = crust_region_scope; CRUST_MAP_MARK(name); CRUST_THREAD_MARK(name); CRUST_POOL_MARK(name)
#define crust_scope_rewind(mark, region, fixed_threshold, regional_threshold, force) do { \
    CRUST_THREAD_REWIND(region); \
    CRUST_MAP_REWIND(region); \
    CRUST_POOL_REWIND(region); \
    crust_rewind(mark); \
    crust_reclaim_fixed(fixed_threshold, force); \
    crust_region_restore_pages(region, regional_threshold, force); \
} while (0)
