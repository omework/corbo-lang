/** @file datastack.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
#ifndef _WIN32
#define _DEFAULT_SOURCE
#define _DARWIN_C_SOURCE
#include <sys/mman.h>
#include <unistd.h>
#else
#include <windows.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
static _Thread_local unsigned char *base;
static _Thread_local size_t cursor, limit, committed, page_size, mapped_size;
static size_t __attribute__((unused)) global_fixed_budget=1073741824ULL;
/** Reserves the calling thread's fixed datastack, initializes page metadata and commits storage on demand. */
static void reserve(uint64_t bytes) {
    if (bytes > SIZE_MAX) exit(1);
    limit = bytes ? (size_t)bytes : 1;
#ifdef _WIN32
    SYSTEM_INFO info;
    GetSystemInfo(&info);
    page_size = info.dwPageSize;
#else
    long page = sysconf(_SC_PAGESIZE);
    if (page <= 0) exit(1);
    page_size = (size_t)page;
#endif
    if (limit > SIZE_MAX - (page_size - 1)) exit(1);
    mapped_size = ((limit + page_size - 1) / page_size) * page_size;
#ifdef _WIN32
    base = VirtualAlloc(NULL, mapped_size, MEM_RESERVE, PAGE_NOACCESS);
    if (!base) exit(1);
#else
    void *mapping = mmap(NULL, mapped_size, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (mapping == MAP_FAILED) exit(1);
    base = mapping;
#endif
}
/** Reserves count aligned fixed-size elements at the current cursor; checks multiplication, alignment and capacity before advancing. */
void *push(size_t size, size_t align, size_t count) {
    size_t pad = (align - cursor % align) % align;
    if (pad > limit - cursor || count > (limit - cursor - pad) / size) { fputs("corbo: limite de la datastack fixe\n",stderr);exit(EXIT_FAILURE); }
    size_t start = cursor + pad;
    size_t end = start + size * count;
    if (end > committed) {
        size_t pages = ((end + page_size - 1) / page_size) * page_size;
#ifdef _WIN32
        if (!VirtualAlloc(base + committed, pages - committed, MEM_COMMIT, PAGE_READWRITE)) exit(1);
#else
        if (mprotect(base + committed, pages - committed, PROT_READ | PROT_WRITE)) exit(1);
#endif
        committed = pages;
    }
    cursor = end;
    return base + start;
}
/** Unmaps the calling thread's fixed datastack after its values and workers have been cleaned up. */
static void release(void) {
#ifdef _WIN32
    VirtualFree(base, 0, MEM_RELEASE);
#else
    munmap(base, mapped_size);
#endif
}
/** Finds the first free flag in a count-element slot bitmap, marks it used and returns its index; exhaustion terminates. */
size_t take(int *used, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        if (!used[i]) { used[i] = 1; return i; }
    }
    exit(1);
}
#include <limits.h>
/** Evaluates the selected signed integer operation with the reference runtime's overflow and zero-divisor failures. */
long long numeric(int op, long long a, long long b) {
    long long result = 0;
    switch (op) {
    case '+': if (__builtin_add_overflow(a, b, &result)) exit(1); return result;
    case '-': if (__builtin_sub_overflow(a, b, &result)) exit(1); return result;
    case '*': if (__builtin_mul_overflow(a, b, &result)) exit(1); return result;
    case '/': if (!b || (a == LLONG_MIN && b == -1)) exit(1); return a / b;
    case '%': if (!b) exit(1); return a == LLONG_MIN && b == -1 ? 0 : a % b;
    default: exit(1);
    }
}
static RegionBand global_band;
static _Thread_local RegionBand *current_band;
static size_t global_budget;
static size_t global_limit = 104857600ULL;
/** Reports an invalid or exhausted region operation and terminates the process. */
static void region_error(void) {
    fputs("corbo: limite de la datastack à régions\n", stderr);
    exit(EXIT_FAILURE);
}
/** Computes the region-stack byte budget from OS memory and CPU information, bounded by PTRDIFF_MAX. */
static size_t region_default_capacity(void) {
#ifdef _WIN32
    MEMORYSTATUSEX memory = {0};
    SYSTEM_INFO info;
    memory.dwLength = sizeof(memory);
    GetSystemInfo(&info);
    if (!GlobalMemoryStatusEx(&memory) || !info.dwNumberOfProcessors) region_error();
    uintmax_t bytes = memory.ullAvailPhys / info.dwNumberOfProcessors;
#else
#ifdef _SC_AVPHYS_PAGES
    long pages = sysconf(_SC_AVPHYS_PAGES);
    if (pages <= 0) pages = sysconf(_SC_PHYS_PAGES);
#else
    long pages = sysconf(_SC_PHYS_PAGES);
#endif
    long cpus = sysconf(_SC_NPROCESSORS_ONLN);
    if (pages <= 0 || cpus <= 0 || (uintmax_t)pages > SIZE_MAX / page_size) region_error();
    uintmax_t bytes = (size_t)pages * page_size / (size_t)cpus;
#endif
    return bytes > PTRDIFF_MAX ? PTRDIFF_MAX : (size_t)bytes;
}
/** Maps zero-initialized RegionBand metadata independently of storage whose scope may end first. */
static RegionBand *region_metadata(void) {
#ifdef _WIN32
    void *memory = VirtualAlloc(NULL, sizeof(RegionBand), MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!memory) region_error();
#else
    void *memory = mmap(NULL, sizeof(RegionBand), PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (memory == MAP_FAILED) region_error();
#endif
    return memory;
}
/** Reserves a virtual address range for a band and records its capacity and per-region limit; commits no payload yet. */
static void region_reserve(RegionBand *band, size_t bytes, size_t limit) {
    if (!bytes || bytes > SIZE_MAX - (page_size - 1)) region_error();
    band->capacity = bytes;
    band->limit = limit;
    size_t pages = ((bytes + page_size - 1) / page_size) * page_size;
#ifdef _WIN32
    band->base = VirtualAlloc(NULL, pages, MEM_RESERVE, PAGE_NOACCESS);
    if (!band->base) region_error();
#else
    void *mapping = mmap(NULL, pages, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (mapping == MAP_FAILED) region_error();
    band->base = mapping;
#endif
}
/** Unmaps an empty band and its separately mapped metadata when applicable; no active region may remain. */
static void region_release_band(RegionBand *band) {
#ifdef _WIN32
    VirtualFree(band->base, 0, MEM_RELEASE);
#else
    size_t pages = ((band->capacity + page_size - 1) / page_size) * page_size;
    munmap(band->base, pages);
#endif
    if (band != &global_band) {
#ifdef _WIN32
        VirtualFree(band, 0, MEM_RELEASE);
#else
        munmap(band, sizeof(*band));
#endif
    }
}
/** Rounds a region width to max_align_t with checked size arithmetic. */
static size_t region_stride(size_t bytes) {
    size_t align = _Alignof(max_align_t);
    if (!bytes || bytes > SIZE_MAX - (align - 1)) region_error();
    return ((bytes + align - 1) / align) * align;
}
/** Creates a child region scope with the explicit or inferred count; the caller holds the runtime lock. */
void region_enter(size_t bytes, size_t count, size_t inferred) {
    size_t inherited = current_band ? current_band->limit : global_limit;
    if (!count && bytes == inherited) return;
    if (!bytes) region_error();
    if (!count) count = inferred ? inferred : 1;
    size_t stride = region_stride(bytes);
    if (count > SIZE_MAX / stride) region_error();
    RegionBand *band = region_metadata();
    region_reserve(band, stride * count, bytes);
    band->parent = current_band;
    current_band = band;
}
/** Closes region scopes back to mark, releasing only empty bands so transferred live regions survive; requires the lock. */
static void region_restore(RegionBand *mark) {
    while (current_band != mark) {
        RegionBand *band = current_band;
        current_band = band->parent;
        band->closed = 1;
        if (!band->active) region_release_band(band);
    }
}
/** Links a stable descriptor into an available band or a dedicated band; owned regions store child-region cleanup links. Requires the runtime lock. */
void region_new(Region *r, size_t width, int owned, int dedicated) {
    RegionBand *band = current_band ? current_band : &global_band;
    size_t bytes = current_band ? band->limit : global_limit;
    if (owned) width = sizeof(RegionOwner);
    if (bytes < width) region_error();

    size_t stride = region_stride(bytes);
    if (dedicated) {
        band = region_metadata();
        region_reserve(band, stride, bytes);
        band->closed = 1;
    } else if (!band->base) {
        region_reserve(band, global_budget ? global_budget : region_default_capacity(), bytes);
    }
    size_t offset = 0;
    Region **link = &band->active;
    while (*link && stride > (*link)->offset - offset) {
        offset = (*link)->offset + region_stride((*link)->bytes);
        link = &(*link)->next;
    }
    if (stride > band->capacity - offset) {
        if (band == &global_band) region_error();
        band = region_metadata();
        region_reserve(band, stride, bytes);
        band->closed = 1;
        offset = 0;
        link = &band->active;
    }
    *r = (Region){ band->base + offset, 0, offset, bytes, width, *link, band, owned };
    *link = r;
}
/** Destroys owned child regions before unlinking this region and releasing an empty closed band; requires the runtime lock. */
void region_drop(Region *r) {
    if (r->owned) {
        RegionOwner *items = (RegionOwner *)r->data;
        for (size_t i = r->len; i != 0; --i) {
            RegionOwner item = items[i - 1];
            region_drop(item.region);
            *item.slot = 0;
        }
    }
    RegionBand *band = r->band;
    Region **link = &band->active;
    while (*link && *link != r) link = &(*link)->next;
    if (!*link) region_error();
    *link = r->next;
    if (band->closed && !band->active) region_release_band(band);
}
/** Commits pages as needed and returns one new element slot; terminates at the region limit. Requires the runtime lock. */
static unsigned char *region_add(Region *r) {
    if (r->len == r->bytes / r->width) region_error();
    RegionBand *band = r->band;
    size_t end = r->offset + (r->len + 1) * r->width;
    size_t pages = ((end + page_size - 1) / page_size) * page_size;
    if (pages > band->committed) {
#ifdef _WIN32
        if (!VirtualAlloc(band->base + band->committed, pages - band->committed, MEM_COMMIT, PAGE_READWRITE)) region_error();
#else
        if (mprotect(band->base + band->committed, pages - band->committed, PROT_READ | PROT_WRITE)) region_error();
#endif
        band->committed = pages;
    }
    return r->data + r->width * r->len++;
}
