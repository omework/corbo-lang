/** @file reclaim.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
static size_t fixed_reclaim_threshold;
static size_t region_reclaim_threshold;

/** Requests OS decommit/discard for a page range; reports whether the platform operation succeeded. */
static bool release_pages(unsigned char *start, size_t size) {
#ifdef _WIN32
    return VirtualFree(start, size, MEM_DECOMMIT) != 0;
#else
    if (madvise(start, size, MADV_DONTNEED) != 0) return false;
    return mprotect(start, size, PROT_NONE) == 0;
#endif
}

/* Leave any page touched by live bytes mapped. */
/** Returns complete unused pages beyond live to the OS when forced or above threshold; updates committed only on success. */
static void reclaim_after(unsigned char *start, size_t live, size_t *committed,
                          size_t threshold, bool force) {
    if (!start || !page_size || (!force && !threshold) || live >= *committed) return;
    size_t boundary = live + (page_size - live % page_size) % page_size;
    if (boundary >= *committed) return;
    size_t bytes = *committed - boundary;
    if ((force || bytes >= threshold) && release_pages(start + boundary, bytes)) *committed = boundary;
}

/** Computes the last live byte across active regions before considering complete tail pages for reclamation. */
static void reclaim_band(RegionBand *band, bool force) {
    size_t live = 0;
    for (Region *r = band->active; r; r = r->next) {
        size_t stop = r->offset + r->len * r->width;
        if (stop > live) live = stop;
    }
    reclaim_after(band->base, live, &band->committed, region_reclaim_threshold, force);
}

/** Reclaims unused fixed/region tail pages using the configured thresholds or force, without releasing live storage. */
static inline __attribute__((unused)) void reclaim_scope(bool force) {
    reclaim_after(base, cursor, &committed, fixed_reclaim_threshold, force);
    if (force || region_reclaim_threshold) {
#if CORBO_THREADED
pthread_mutex_lock(&task_lock);
#endif /* CORBO_THREADED */
        for (RegionBand *band = current_band; band; band=band->parent) reclaim_band(band, force);
        reclaim_band(&global_band, force);
#if CORBO_THREADED
pthread_mutex_unlock(&task_lock);
#endif /* CORBO_THREADED */
    }
}
