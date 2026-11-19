typedef struct CrustAllocation CrustAllocation;

typedef struct {
    size_t cursor;
    size_t stride;
    unsigned char *data;
    CrustAllocation *records;
} CrustPoolArm;

typedef struct {
    size_t capacity;
    CrustPoolArm *arms;
} CrustPool;

struct CrustAllocation {
    CrustAllocation *previous;
    CrustAllocation *next;
    CrustPoolArm *arm;
    void *data;
    size_t index;
    size_t tag;
    size_t owner;
#ifdef CRUST_HAS_REGIONS
    bool growing;
#endif
#ifdef CRUST_HAS_THREADS
    CrustHandle *handles;
#endif
#ifdef CRUST_HAS_DESTRUCTORS
    void (*finalize)(void *);
#endif
    CrustAllocation *children;
    CrustAllocation *sibling;
};

#ifdef CRUST_HAS_DATASTACK
static CRUST_LOCAL CrustAllocation *crust_allocations;
static CRUST_LOCAL size_t crust_pool_depth;
#define CRUST_POOL_MARK(name) size_t name##_pools = crust_pool_depth++
#define CRUST_POOL_REWIND(name) (crust_pool_depth = name##_pools)
#ifdef CRUST_HAS_ASYNC
static CRUST_LOCAL bool crust_async_pool;
#endif
#ifdef CRUST_HAS_THREADS
static pthread_mutex_t crust_pool_lock = PTHREAD_MUTEX_INITIALIZER;
#define CRUST_POOL_LOCK() pthread_mutex_lock(&crust_pool_lock)
#define CRUST_POOL_UNLOCK() pthread_mutex_unlock(&crust_pool_lock)
#else
#define CRUST_POOL_LOCK() ((void)0)
#define CRUST_POOL_UNLOCK() ((void)0)
#endif

static inline __attribute__((unused)) size_t crust_pool_current_owner(void) {
#ifdef CRUST_HAS_ASYNC
    if (crust_async_pool)
        return crust_thread_depth;
#endif
    return crust_pool_depth;
}

static inline __attribute__((unused)) CrustAllocation *crust_pool_take(CrustPool *pool, size_t tag) {
    CRUST_POOL_LOCK();
    CrustPoolArm *arm = &pool->arms[tag];
    size_t index = arm->cursor;
    if (index == pool->capacity) {
        for (index = 0; index < pool->capacity && arm->records[index].arm != NULL; ++index) {
        }
        if (index == pool->capacity) {
            fputs("corbo: pool épuisé\n", stderr);
            exit(EXIT_FAILURE);
        }
    } else {
        ++arm->cursor;
    }
    CrustAllocation *allocation = &arm->records[index];
    *allocation = (CrustAllocation){
        .next = crust_allocations,
        .arm = arm,
        .data = arm->data + index * arm->stride,
        .index = index,
        .tag = tag,
        .owner = crust_pool_current_owner(),
    };
    if (crust_allocations != NULL)
        crust_allocations->previous = allocation;
    crust_allocations = allocation;
    CRUST_POOL_UNLOCK();
    return allocation;
}

static inline void crust_pool_unlink(CrustAllocation *allocation) {
    if (allocation->previous != NULL)
        allocation->previous->next = allocation->next;
    else
        crust_allocations = allocation->next;
    if (allocation->next != NULL)
        allocation->next->previous = allocation->previous;
    allocation->next = allocation->previous = NULL;
}

// The walker enumerates the owning fields in cleanup order. Insert the
// whole group before the existing children without reversing it.
static inline void crust_pool_adopt_child(CrustAllocation ***tail, CrustAllocation *child) {
    crust_pool_unlink(child);
    **tail = child;
    *tail = &child->sibling;
}

static inline __attribute__((unused)) void crust_pool_extract_child(CrustAllocation *parent, CrustAllocation *child) {
    CrustAllocation **link = &parent->children;
    while (*link != child)
        link = &(*link)->sibling;
    *link = child->sibling;
    child->sibling = NULL;
    child->owner = crust_pool_current_owner();
    child->previous = NULL;
    child->next = crust_allocations;
    if (crust_allocations != NULL)
        crust_allocations->previous = child;
    crust_allocations = child;
}

typedef struct {
    CrustAllocation *parent;
    CrustAllocation **tail;
} CrustAdoption;

#ifdef CRUST_HAS_THREADS
static inline __attribute__((unused)) void crust_pool_adopt_handle(CrustAdoption *adoption, CrustHandle *handle) {
    if (handle == NULL)
        return;
    crust_thread_unlink(handle);
    handle->owned_next = adoption->parent->handles;
    adoption->parent->handles = handle;
}

static inline __attribute__((unused)) void crust_pool_extract_handle(CrustAllocation *parent, CrustHandle *handle) {
    if (handle == NULL)
        return;
    CrustHandle **link = &parent->handles;
    while (*link != handle)
        link = &(*link)->owned_next;
    *link = handle->owned_next;
    crust_thread_register(handle);
}
static inline __attribute__((unused)) void crust_pool_handle_resource(CrustHandle *handle, uintptr_t owner, int action) {
    switch (action) {
    case CRUST_ADOPT: crust_pool_adopt_handle((CrustAdoption *)owner, handle); break;
    case CRUST_EXTRACT: crust_pool_extract_handle((CrustAllocation *)owner, handle); break;
    default: crust_handle_resource(handle, owner, action); break;
    }
}
#endif

static void crust_pool_dispose(CrustAllocation *root) {
#ifdef CRUST_HAS_THREADS
    CrustHandle *handles = NULL;
    CrustHandle **tail = &handles;
#endif
    CRUST_POOL_LOCK();
    // Once a child is removed from its sibling list, its link can hold
    // the parent to resume. Runtime nesting needs no extra C stack.
    root->sibling = NULL;
    CrustAllocation *allocation = root;
    while (allocation != NULL) {
#ifdef CRUST_HAS_DESTRUCTORS
        if (allocation->finalize != NULL) {
            void (*finalize)(void *) = allocation->finalize;
            allocation->finalize = NULL;
            CRUST_POOL_UNLOCK();
            finalize(allocation->data);
            CRUST_POOL_LOCK();
        }
#endif
        if (allocation->children != NULL) {
            CrustAllocation *child = allocation->children;
            allocation->children = child->sibling;
            child->sibling = allocation;
            allocation = child;
            continue;
        }

#ifdef CRUST_HAS_THREADS
        *tail = allocation->handles;
        while (*tail != NULL)
            tail = &(*tail)->owned_next;
#endif
        CrustAllocation *parent = allocation->sibling;
#ifdef CRUST_HAS_REGIONS
        if (allocation->growing)
            crust_region_release(allocation->data);
#endif
        CrustPoolArm *arm = allocation->arm;
        allocation->arm = NULL;
        while (arm->cursor != 0 && arm->records[arm->cursor - 1].arm == NULL)
            --arm->cursor;
        allocation = parent;
    }
    CRUST_POOL_UNLOCK();
#ifdef CRUST_HAS_THREADS
    while (handles != NULL) {
        CrustHandle *next = handles->owned_next;
        crust_thread_detach(handles);
        handles = next;
    }
#endif
}

static inline void crust_pool_drop(CrustAllocation *allocation) {
    crust_pool_unlink(allocation);
    crust_pool_dispose(allocation);
}

static inline __attribute__((unused)) void crust_pool_resource(CrustAllocation *allocation, uintptr_t target, int action) {
    switch (action) {
    case CRUST_REHOME:
        allocation->owner = target;
        break;
    case CRUST_DETACH:
        crust_pool_unlink(allocation);
        break;
    case CRUST_ATTACH:
        allocation->owner = target;
        allocation->next = crust_allocations;
        allocation->previous = NULL;
        if (crust_allocations != NULL)
            crust_allocations->previous = allocation;
        crust_allocations = allocation;
        break;
    case CRUST_DESTROY:
        crust_pool_dispose(allocation);
        break;
    case CRUST_DROP:
        crust_pool_drop(allocation);
        break;
    case CRUST_EXTRACT:
        crust_pool_extract_child((CrustAllocation *)target, allocation);
        break;
    case CRUST_ADOPT:
        crust_pool_adopt_child(&((CrustAdoption *)target)->tail, allocation);
        break;
    default:
        abort();
    }
}

static void crust_rewind(size_t mark) {
    size_t owner = crust_pool_current_owner();
    CrustAllocation *expired = NULL;
    CrustAllocation **tail = &expired;
    CrustAllocation *allocation = crust_allocations;
    while (allocation != NULL) {
        CrustAllocation *next = allocation->next;
        if (allocation->owner > owner) {
            crust_pool_unlink(allocation);
            *tail = allocation;
            tail = &allocation->next;
        }
        allocation = next;
    }
    // A finalizer can enter and leave another Crust scope. Detach the
    // current scope's cleanup lists before invoking any of those callbacks.
#ifdef CRUST_HAS_DESTRUCTORS
    CrustDestructor *destructor = crust_destructor_collect(owner);
    while (destructor != NULL) {
        CrustDestructor *next = destructor->next;
        destructor->next = NULL;
        destructor->run(destructor->value);
        destructor = next;
    }
#endif
    while (expired != NULL) {
        CrustAllocation *next = expired->next;
        expired->next = NULL;
        crust_pool_dispose(expired);
        expired = next;
    }
    crust_cursor = mark;
}

#else
#define crust_rewind(mark) (crust_cursor = (mark))
#endif
