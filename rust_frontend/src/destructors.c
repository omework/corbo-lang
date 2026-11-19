typedef struct CrustDestructor {
    struct CrustDestructor *next;
    void (*run)(void *);
    void *value;
    size_t owner;
} CrustDestructor;

static CRUST_LOCAL CrustDestructor *crust_destructors;

static void crust_destructor_unlink(CrustDestructor *entry) {
    CrustDestructor **link = &crust_destructors;
    while (*link != NULL && *link != entry)
        link = &(*link)->next;
    if (*link == entry)
        *link = entry->next;
}

static inline __attribute__((unused)) void crust_destructor_resource(
    CrustDestructor *entry, void *value, void (*run)(void *), size_t owner, int action
) {
    switch (action) {
    case CRUST_REHOME:
    case CRUST_ATTACH:
    case CRUST_EXTRACT:
        crust_destructor_unlink(entry);
        *entry = (CrustDestructor){crust_destructors, run, value, owner};
        crust_destructors = entry;
        break;
    case CRUST_UNREGISTER:
    case CRUST_ADOPT:
    case CRUST_DETACH:
        crust_destructor_unlink(entry);
        break;
    case CRUST_DROP:
        crust_destructor_unlink(entry);
        run(value);
        break;
    case CRUST_DESTROY:
    case CRUST_FINALIZE:
        run(value);
        break;
    default:
        abort();
    }
}

static CrustDestructor *crust_destructor_collect(size_t owner) {
    CrustDestructor *expired = NULL;
    CrustDestructor **tail = &expired;
    CrustDestructor **link = &crust_destructors;
    while (*link != NULL) {
        CrustDestructor *entry = *link;
        if (entry->owner > owner) {
            *link = entry->next;
            entry->next = NULL;
            *tail = entry;
            tail = &entry->next;
        } else {
            link = &entry->next;
        }
    }
    return expired;
}
