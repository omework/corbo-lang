#define _DEFAULT_SOURCE 1
#define _DARWIN_C_SOURCE 1
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
#define MAP_FAILED ((void *)-1)
#else
#include <sys/mman.h>
#include <unistd.h>
#endif

#ifndef CRUST_LOCAL
#define CRUST_LOCAL
#endif

static CRUST_LOCAL unsigned char *crust_stack;
static CRUST_LOCAL size_t crust_cursor;
static CRUST_LOCAL size_t crust_high_water;
static CRUST_LOCAL size_t crust_capacity;
static CRUST_LOCAL int crust_capacity_set;

static inline void crust_stack_error(void) {
    fputs("corbo: limite de la datastack fixe\n", stderr);
    exit(EXIT_FAILURE);
}

static inline __attribute__((unused)) void crust_set_capacity(uintmax_t bytes) {
    if (bytes > PTRDIFF_MAX)
        crust_stack_error();
    crust_capacity = (size_t)bytes;
    crust_capacity_set = 1;
}

static inline size_t crust_advance(size_t cursor, size_t size, size_t alignment, size_t count) {
    size_t remainder = cursor % alignment;
    size_t padding = remainder == 0 ? 0 : alignment - remainder;
    size_t remaining = PTRDIFF_MAX - cursor;
    if (padding > remaining || count > (remaining - padding) / size)
        crust_stack_error();
    return cursor + padding + count * size;
}

static size_t crust_page_size(void) {
#ifdef _WIN32
    SYSTEM_INFO info;
    GetSystemInfo(&info);
    return info.dwPageSize;
#else
    long page = sysconf(_SC_PAGESIZE);
    return page > 0 ? (size_t)page : 0;
#endif
}

static inline size_t crust_default_capacity(void) {
#ifdef _WIN32
    MEMORYSTATUSEX memory = {0};
    SYSTEM_INFO info;
    memory.dwLength = sizeof(memory);
    GetSystemInfo(&info);
    if (!GlobalMemoryStatusEx(&memory) || !info.dwNumberOfProcessors)
        crust_stack_error();
    uintmax_t capacity = memory.ullAvailPhys / info.dwNumberOfProcessors;
#else
#ifdef _SC_AVPHYS_PAGES
    long pages = sysconf(_SC_AVPHYS_PAGES);
    if (pages <= 0)
        pages = sysconf(_SC_PHYS_PAGES);
#else
    long pages = sysconf(_SC_PHYS_PAGES);
#endif
    long page_size = sysconf(_SC_PAGESIZE);
    long cpus = sysconf(_SC_NPROCESSORS_ONLN);
    if (pages <= 0 || page_size <= 0 || cpus <= 0 ||
        (uintmax_t)pages > SIZE_MAX / (uintmax_t)page_size)
        crust_stack_error();
    size_t capacity = (size_t)pages * (size_t)page_size / (size_t)cpus;
#endif
    return capacity > PTRDIFF_MAX ? PTRDIFF_MAX : (size_t)capacity;
}

// The guard starts on the first page boundary at or beyond the logical limit.
static size_t crust_guarded_size(size_t bytes, size_t *usable) {
    size_t page = crust_page_size();
    if (page == 0 || bytes > PTRDIFF_MAX)
        return 0;
    size_t remainder = bytes % page;
    size_t padding = remainder == 0 ? 0 : page - remainder;
    if (page > PTRDIFF_MAX - bytes || padding > PTRDIFF_MAX - bytes - page)
        return 0;
    if (usable != NULL)
        *usable = bytes + padding;
    return bytes + padding + page;
}

static void *crust_guarded_map(size_t bytes) {
    size_t usable;
    size_t total = crust_guarded_size(bytes, &usable);
    if (total == 0 || usable == 0)
        return MAP_FAILED;
#ifdef _WIN32
    void *mapping = VirtualAlloc(NULL, total, MEM_RESERVE, PAGE_NOACCESS);
    if (mapping == NULL)
        return MAP_FAILED;
    if (VirtualAlloc(mapping, usable, MEM_COMMIT, PAGE_READWRITE) == NULL) {
        VirtualFree(mapping, 0, MEM_RELEASE);
        return MAP_FAILED;
    }
#else
    void *mapping = mmap(NULL, total, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (mapping != MAP_FAILED && mprotect(mapping, usable, PROT_READ | PROT_WRITE) != 0) {
        munmap(mapping, total);
        return MAP_FAILED;
    }
#endif
    return mapping;
}

static inline __attribute__((unused)) void crust_guarded_unmap(void *mapping, size_t bytes) {
#ifdef _WIN32
    (void)bytes;
    VirtualFree(mapping, 0, MEM_RELEASE);
#else
    munmap(mapping, crust_guarded_size(bytes, NULL));
#endif
}

// A range is eligible only when both ends fit inside wholly dead pages.
static inline size_t crust_reclaim_pages(size_t *first, size_t end, size_t page) {
    size_t padding = (page - *first % page) % page;
    end -= end % page;
    if (end <= *first || padding >= end - *first)
        return 0;
    *first += padding;
    return end - *first;
}

static inline int crust_reclaim_mapping(unsigned char *address, size_t bytes) {
#ifdef _WIN32
    if (!VirtualFree(address, bytes, MEM_DECOMMIT))
        return 0;
    if (VirtualAlloc(address, bytes, MEM_COMMIT, PAGE_READWRITE) != address)
        crust_stack_error();
    return 1;
#else
    return mmap(address, bytes, PROT_READ | PROT_WRITE,
                MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0) == address;
#endif
}

static inline __attribute__((unused)) void crust_reclaim_fixed(uintmax_t threshold, int force) {
    if ((!force && threshold == 0) || crust_stack == NULL || crust_cursor >= crust_high_water)
        return;
    size_t page_size = crust_page_size();
    if (page_size == 0)
        return;
    size_t first = crust_cursor;
    size_t bytes = crust_reclaim_pages(&first, crust_high_water, (size_t)page_size);
    if (bytes != 0 && (force || bytes >= threshold) && crust_reclaim_mapping(crust_stack + first, bytes))
        crust_high_water = crust_cursor;
}

static inline __attribute__((unused)) void *crust_push(size_t size, size_t alignment, size_t count) {
    size_t next = crust_advance(crust_cursor, size, alignment, count);
    if (!crust_capacity_set) {
        crust_capacity = crust_default_capacity();
        crust_capacity_set = 1;
    }
    if (next > crust_capacity)
        crust_stack_error();
    if (crust_stack == NULL) {
        void *mapping = crust_guarded_map(crust_capacity);
        if (mapping == MAP_FAILED)
            crust_stack_error();
        crust_stack = mapping;
    }
    crust_cursor = next;
    if (next > crust_high_water)
        crust_high_water = next;
    return crust_stack + (next - count * size);
}

#define crust_reserve(type, count) crust_push(sizeof(type), _Alignof(type), count)

