// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_MEMORY_HPP
#define CORBO_CPP_MEMORY_HPP
// Explicit virtual-memory datastack. Plain state and functions; no constructors.
#if defined(_WIN32)
#include <windows.h>
#elif defined(__APPLE__)
#include <sys/mman.h>
#include <pthread.h>
#include <unistd.h>
#include <mach/mach.h>
#else
#include <sys/mman.h>
#include <pthread.h>
#include <unistd.h>
#endif

// Mapping records live in their own committed prefix page. Registry locking is
// limited to creation, destruction and metric snapshots, never each slot push.
struct corbo_mapping_record {
    corbo_mapping_record *next;
    size_t reserved, committed, occupied, unused;
};
#if defined(_WIN32)
inline SRWLOCK corbo_mapping_registry_lock = SRWLOCK_INIT;
static inline void corbo_registry_acquire() { AcquireSRWLockExclusive(&corbo_mapping_registry_lock); }
static inline void corbo_registry_release() { ReleaseSRWLockExclusive(&corbo_mapping_registry_lock); }
#else
inline pthread_mutex_t corbo_mapping_registry_lock = PTHREAD_MUTEX_INITIALIZER;
static inline void corbo_registry_acquire() { if (pthread_mutex_lock(&corbo_mapping_registry_lock)) corbo_fail("corbo: metrics lock failed"); }
static inline void corbo_registry_release() { if (pthread_mutex_unlock(&corbo_mapping_registry_lock)) corbo_fail("corbo: metrics unlock failed"); }
#endif
inline corbo_mapping_record *corbo_mapping_records;
struct CorboMemoryStats { size_t reserved, committed, occupied; };
static inline size_t corbo_counter_read(const size_t *value) { return __atomic_load_n(value, __ATOMIC_RELAXED); }
static inline void corbo_counter_set(size_t *value, size_t next) { __atomic_store_n(value, next, __ATOMIC_RELAXED); }
static inline void corbo_counter_add(size_t *value, size_t amount) { __atomic_fetch_add(value, amount, __ATOMIC_RELAXED); }
static inline void corbo_counter_sub(size_t *value, size_t amount) { __atomic_fetch_sub(value, amount, __ATOMIC_RELAXED); }
// Like the public contract, fields sample adjacent instants. Registry nodes remain
// mapped until the reader releases this short-lived registry lock.
static inline CorboMemoryStats corbo_memory_stats() {
    CorboMemoryStats result = {};
    corbo_registry_acquire();
    for (corbo_mapping_record *record = corbo_mapping_records; record != NULL; record = record->next) {
        result.reserved += record->reserved;
        result.committed += corbo_counter_read(&record->committed);
        size_t occupied = corbo_counter_read(&record->occupied), unused = corbo_counter_read(&record->unused);
        result.occupied += occupied > unused ? occupied - unused : 0;
    }
    corbo_registry_release();
    return result;
}

// Virtual reservation, committed pages and logical occupancy are distinct.
struct corbo_datastack {
    uint8_t *base;
    corbo_mapping_record *record;
    size_t mapping_bytes;
    size_t capacity;
    size_t reserved;
    size_t committed;
    size_t cursor;
    size_t page_size;
    size_t reclaim_threshold;
};
inline thread_local corbo_datastack corbo_fixed_stack = {};

// Resolve an unknown static bound to available physical memory per online CPU.
static inline size_t corbo_default_capacity() {
#if defined(_WIN32)
    MEMORYSTATUSEX memory = {};
    memory.dwLength = sizeof memory;
    SYSTEM_INFO info = {};
    GetSystemInfo(&info);
    if (!GlobalMemoryStatusEx(&memory) || info.dwNumberOfProcessors == 0)
        corbo_fail("corbo: cannot determine default datastack capacity");
    return (size_t)(memory.ullAvailPhys / info.dwNumberOfProcessors);
#else
    long cores = sysconf(_SC_NPROCESSORS_ONLN);
    long page = sysconf(_SC_PAGESIZE);
    if (cores <= 0 || page <= 0) corbo_fail("corbo: cannot determine datastack configuration");
#if defined(__APPLE__)
    vm_statistics64_data_t memory = {};
    mach_msg_type_number_t count = HOST_VM_INFO64_COUNT;
    mach_port_t host = mach_host_self();
    kern_return_t status = host_statistics64(host, HOST_VM_INFO64, (host_info64_t)&memory, &count);
    mach_port_deallocate(mach_task_self(), host);
    if (status != KERN_SUCCESS) corbo_fail("corbo: cannot determine available memory");
    uint64_t pages = (uint64_t)memory.free_count + memory.inactive_count;
#else
    long available = sysconf(_SC_AVPHYS_PAGES);
    if (available <= 0) corbo_fail("corbo: cannot determine available memory");
    uint64_t pages = (uint64_t)available;
#endif
    if (pages > SIZE_MAX / (size_t)page) corbo_fail("corbo: memory capacity overflow");
    return (size_t)(pages * (size_t)page / (size_t)cores);
#endif
}

// Reserve addresses explicitly; zero requests the documented runtime default.
static inline void corbo_datastack_open(corbo_datastack *stack, size_t capacity) {
    if (stack->base != NULL) corbo_fail("corbo: datastack already initialized");
#if defined(_WIN32)
    SYSTEM_INFO info = {};
    GetSystemInfo(&info);
    size_t page = info.dwPageSize;
#else
    long raw_page = sysconf(_SC_PAGESIZE);
    if (raw_page <= 0) corbo_fail("corbo: cannot determine page size");
    size_t page = (size_t)raw_page;
#endif
    if (capacity == 0) capacity = corbo_default_capacity();
    if (page == 0 || capacity > SIZE_MAX - 4 * page) corbo_fail("corbo: invalid datastack capacity");
    size_t reserved = (capacity + page - 1) / page * page;
    size_t mapping_bytes = reserved + 3 * page;
#if defined(_WIN32)
    size_t granularity = info.dwAllocationGranularity;
    if (granularity == 0 || mapping_bytes > SIZE_MAX - (granularity - 1))
        corbo_fail("corbo: invalid virtual reservation granularity");
    mapping_bytes = (mapping_bytes + granularity - 1) / granularity * granularity;
#endif
#if defined(_WIN32)
    void *base = VirtualAlloc(NULL, mapping_bytes, MEM_RESERVE, PAGE_NOACCESS);
    if (base == NULL) corbo_fail("corbo: datastack address reservation failed");
#else
    void *base = mmap(NULL, mapping_bytes, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (base == MAP_FAILED) corbo_fail("corbo: datastack address reservation failed");
#endif
#if defined(_WIN32)
    if (VirtualAlloc(base, page, MEM_COMMIT, PAGE_READWRITE) == NULL)
        corbo_fail("corbo: datastack metadata commitment failed");
#else
    if (mprotect(base, page, PROT_READ | PROT_WRITE))
        corbo_fail("corbo: datastack metadata commitment failed");
#endif
    corbo_mapping_record *record = ::new(base) corbo_mapping_record{};
    record->reserved = mapping_bytes; record->committed = page;
    corbo_registry_acquire(); record->next = corbo_mapping_records; corbo_mapping_records = record; corbo_registry_release();
    stack->record = record; stack->mapping_bytes = mapping_bytes;
    // Prefix metadata, inaccessible lower guard, payload, inaccessible upper guard.
    stack->base = (uint8_t *)base + 2 * page;
    stack->capacity = capacity;
    stack->reserved = reserved;
    stack->page_size = page;
    stack->reclaim_threshold = 16ULL * 1024 * 1024;
}

// Commit an extent without moving the logical cursor or relocating storage.
static inline void corbo_datastack_commit(corbo_datastack *stack, size_t end) {
    if (end > stack->capacity) corbo_fail("corbo: datastack capacity exceeded");
    if (end > stack->committed) {
        size_t committed = (end + stack->page_size - 1) / stack->page_size * stack->page_size;
#if defined(_WIN32)
        if (VirtualAlloc(stack->base + stack->committed, committed - stack->committed,
                         MEM_COMMIT, PAGE_READWRITE) == NULL)
            corbo_fail("corbo: datastack commitment failed");
#else
        if (mprotect(stack->base + stack->committed, committed - stack->committed,
                     PROT_READ | PROT_WRITE) != 0)
            corbo_fail("corbo: datastack commitment failed");
#endif
        corbo_counter_add(&stack->record->committed, committed - stack->committed);
        stack->committed = committed;
    }
}

// Reserve one aligned slot and commit only the pages touched by its extent.
static inline void *corbo_datastack_alloc(corbo_datastack *stack, size_t size, size_t alignment) {
    if (stack->base == NULL || alignment == 0 || (alignment & (alignment - 1)) != 0)
        corbo_fail("corbo: invalid datastack allocation");
    size_t padding = (alignment - ((uintptr_t)stack->base + stack->cursor) % alignment) % alignment;
    if (padding > stack->capacity - stack->cursor || size > stack->capacity - stack->cursor - padding)
        corbo_fail("corbo: datastack capacity exceeded");
    size_t start = stack->cursor + padding;
    size_t end = start + size;
    corbo_datastack_commit(stack, end);
    stack->cursor = end;
    corbo_counter_set(&stack->record->occupied, end);
    return stack->base + start;
}

// Return complete dead tail pages only. Decommit never changes addresses or
// logical capacity; subsequent allocation recommits them explicitly.
static inline void corbo_datastack_reclaim(corbo_datastack *stack, size_t live, bool force) {
    if (live >= stack->committed || (!force && stack->reclaim_threshold == 0)) return;
    size_t boundary = (live + stack->page_size - 1) / stack->page_size * stack->page_size;
    if (boundary >= stack->committed) return;
    size_t bytes = stack->committed - boundary;
    if (!force && bytes < stack->reclaim_threshold) return;
#if defined(_WIN32)
    bool success = VirtualFree(stack->base + boundary, bytes, MEM_DECOMMIT) != 0;
#else
    bool success = madvise(stack->base + boundary, bytes, MADV_DONTNEED) == 0;
    if (success && mprotect(stack->base + boundary, bytes, PROT_NONE)) corbo_fail("corbo: reclaimed page protection failed");
#endif
    if (success) {
        stack->committed = boundary;
        corbo_counter_sub(&stack->record->committed, bytes);
    }
}
// Rewind after compiler-emitted cleanup; this function never runs destructors.
static inline void corbo_stack_restore(size_t mark) {
    if (mark > corbo_fixed_stack.cursor) corbo_fail("corbo: invalid datastack restoration");
    corbo_fixed_stack.cursor = mark;
    corbo_counter_set(&corbo_fixed_stack.record->occupied, mark);
    corbo_datastack_reclaim(&corbo_fixed_stack, mark, false);
}

// Release the reservation explicitly after all root-scope cleanup is complete.
static inline void corbo_datastack_close(corbo_datastack *stack) {
    if (stack->base == NULL) return;
    corbo_registry_acquire();
    corbo_mapping_record **link = &corbo_mapping_records;
    while (*link != NULL && *link != stack->record) link = &(*link)->next;
    if (*link == NULL) corbo_fail("corbo: unregistered datastack release");
    *link = stack->record->next;
    corbo_registry_release();
    void *mapping = stack->record;
#if defined(_WIN32)
    if (!VirtualFree(mapping, 0, MEM_RELEASE)) corbo_fail("corbo: datastack release failed");
#else
    if (munmap(mapping, stack->mapping_bytes) != 0)
        corbo_fail("corbo: datastack release failed");
#endif
    *stack = {};
}
// Fixed-stack wrappers retain the compiler's explicit per-thread cursor ABI.
static inline void corbo_stack_open(size_t capacity) {
    corbo_datastack_open(&corbo_fixed_stack, capacity);
}
static inline void *corbo_stack_alloc(size_t size, size_t alignment) {
    return corbo_datastack_alloc(&corbo_fixed_stack, size, alignment);
}
static inline void corbo_stack_close() {
    corbo_datastack_close(&corbo_fixed_stack);
}
#endif
