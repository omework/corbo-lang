// macOS: clang -std=c11 -O2 -Wall -Wextra -Werror -pthread benchmarks/datastack_reclaim.c -o /tmp/crust-reclaim
#define _DARWIN_C_SOURCE 1
#include <mach/mach.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <string.h>
#include <time.h>
#define CRUST_LOCAL _Thread_local
#define CRUST_HAS_THREADS 1
#include "../rust_frontend/src/datastack.c"
#include "../rust_frontend/src/region_storage.c"

enum { MiB = 1024 * 1024 };

static uint64_t now(void) {
    return clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
}

static task_vm_info_data_t memory(void) {
    task_vm_info_data_t info = {0};
    mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&info, &count) != KERN_SUCCESS)
        abort();
    return info;
}

static unsigned int faults(void) {
    task_events_info_data_t info;
    mach_msg_type_number_t count = TASK_EVENTS_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_EVENTS_INFO, (task_info_t)&info, &count) != KERN_SUCCESS)
        abort();
    return (unsigned int)info.faults;
}

static void touch(volatile unsigned char *data, size_t bytes, size_t page) {
    for (size_t i = 0; i < bytes; i += page)
        data[i] = 42;
}

static size_t resident(void *data, size_t bytes, size_t page, char *pages) {
    if (mincore(data, bytes, pages) != 0)
        abort();
    size_t count = 0;
    for (size_t i = 0; i < bytes / page; ++i)
        count += (pages[i] & MINCORE_INCORE) != 0;
    return count * page;
}

static atomic_uint ready;
static atomic_bool go;

static void *reclaim_worker(void *argument) {
    volatile unsigned char *data = argument;
    const size_t bytes = 8 * MiB;
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    uint64_t total = 0;
    atomic_fetch_add(&ready, 1);
    while (!atomic_load(&go))
        sched_yield();
    for (size_t i = 0; i < 64; ++i) {
        touch(data, bytes, page);
        uint64_t start = now();
        if (mmap((void *)data, bytes, PROT_READ | PROT_WRITE,
                 MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0) != (void *)data)
            abort();
        total += now() - start;
    }
    return (void *)(uintptr_t)(total / 64);
}

static int parallel(unsigned int workers) {
    if (workers != 1 && workers != 2 && workers != 4 && workers != 8)
        return 2;
    pthread_t threads[8];
    crust_regions_configure(0, 8 * MiB, workers);
    CrustGrowing values[8];
    for (unsigned int i = 0; i < workers; ++i)
        values[i] = crust_region_take();
    for (unsigned int i = 0; i < workers; ++i)
        if (pthread_create(&threads[i], NULL, reclaim_worker, crust_region_data(&values[i])))
            abort();
    while (atomic_load(&ready) != workers)
        sched_yield();
    uint64_t start = now();
    atomic_store(&go, true);
    void *worker_ns[8];
    for (unsigned int i = 0; i < workers; ++i)
        if (pthread_join(threads[i], &worker_ns[i]))
            abort();
    printf("elapsed,%llu\n", now() - start);
    for (unsigned int i = 0; i < workers; ++i)
        printf("worker,%zu\n", (size_t)(uintptr_t)worker_ns[i]);
    for (unsigned int i = 0; i < workers; ++i)
        crust_region_release(&values[i]);
    crust_worker_close_regions();
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 3)
        return 2;
    const char *policy = argv[1];
    if (strcmp(policy, "parallel") == 0)
        return parallel((unsigned int)strtoul(argv[2], NULL, 10));
    bool scattered = strcmp(argv[2], "scattered") == 0;
    bool pressure = strcmp(argv[2], "pressure") == 0;
    bool regions = scattered || pressure || strcmp(argv[2], "regions") == 0;
    if (!regions && strcmp(argv[2], "fixed") != 0)
        return 2;
    int threshold = strcmp(policy, "threshold") == 0;
    int reusable = strcmp(policy, "reusable") == 0;
    int remap = threshold || strcmp(policy, "remap") == 0;
    int advise = strcmp(policy, "dontneed") == 0;
    if (!remap && !advise && !reusable && strcmp(policy, "keep") != 0)
        return 2;

    long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0 || MiB % page_size != 0)
        return 2;
    size_t page = (size_t)page_size;
    const size_t sizes[] = {1 * MiB, 8 * MiB, 64 * MiB};
    char *pages = calloc(64 * MiB / page, 1);
    if (pages == NULL)
        abort();
    puts("bytes,release_ns,resident_before,resident_after,rss_drop,footprint_drop,reusable_delta,reuse_ns,faults,cold_ns,called");
    for (size_t i = 0; i < sizeof sizes / sizeof *sizes; ++i) {
        size_t bytes = sizes[i];
        enum { released_slots = 8 };
        CrustGrowing slots[released_slots];
        CrustGrowing retained[released_slots];
        size_t stride = bytes / released_slots;
        size_t ranges = scattered ? released_slots : 1;
        size_t span = bytes / ranges;
        size_t step = scattered ? 2 * stride : bytes;
        unsigned char *live;
        unsigned char *data;
        if (regions) {
            crust_region_global = crust_region_band(stride, scattered ? 2 * released_slots : released_slots + 1);
            for (size_t slot = 0; slot < released_slots; ++slot) {
                if (scattered || slot == 0) {
                    retained[slot] = crust_region_take();
                    crust_region_data(&retained[slot])[0] = 99;
                }
                slots[slot] = crust_region_take();
            }
            live = crust_region_data(&retained[0]);
            data = crust_region_data(&slots[0]);
        } else {
            crust_set_capacity(bytes + page);
            live = crust_push(1, 1, page);
            data = crust_push(1, 1, bytes);
        }
        live[0] = 99;
        uint64_t start = now();
        for (size_t i = 0; i < ranges; ++i)
            touch(data + i * step, span, page);
        uint64_t cold = now() - start;
        size_t before = 0;
        for (size_t i = 0; i < ranges; ++i)
            before += resident(data + i * step, span, page, pages);
        task_vm_info_data_t vm_before = memory();

        if (regions) {
            for (size_t slot = 0; slot < released_slots; ++slot)
                crust_region_release(&slots[slot]);
            crust_region_restore(NULL);
            if (crust_region_global->cursor != (scattered ? 2 * released_slots - 1 : 1))
                abort();
        } else {
            crust_cursor = page;
        }
        int called = advise || reusable || (remap && (!threshold || bytes >= 16 * MiB));
        start = now();
        for (size_t i = 0; called && i < ranges; ++i) {
            unsigned char *range = data + i * step;
            if (remap) {
                if (mmap(range, span, PROT_READ | PROT_WRITE,
                         MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0) != range)
                    abort();
            } else if (madvise(range, span, reusable ? MADV_FREE_REUSABLE : MADV_DONTNEED) != 0) {
                abort();
            }
        }
        uint64_t release = now() - start;
        task_vm_info_data_t vm_after = memory();
        void *load = NULL;
        const size_t load_size = 256 * MiB;
        if (pressure) {
            load = mmap(NULL, load_size, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (load == MAP_FAILED)
                abort();
            touch(load, load_size, page);
        }
        size_t after = 0;
        for (size_t i = 0; i < ranges; ++i)
            after += resident(data + i * step, span, page, pages);

        if (live[0] != 99)
            abort();
        if (regions) {
            for (size_t slot = 0; slot < released_slots; ++slot) {
                slots[slot] = crust_region_take();
                size_t expected = scattered ? (slot + released_slots - 1) % released_slots : slot;
                if (crust_region_data(&slots[slot]) != data + expected * (scattered ? step : stride))
                    abort();
            }
        } else if (crust_push(1, 1, bytes) != data) {
            abort();
        }
        unsigned int prior_faults = faults();
        start = now();
        for (size_t i = 0; reusable && i < ranges; ++i)
            if (madvise(data + i * step, span, MADV_FREE_REUSE) != 0)
                abort();
        for (size_t i = 0; i < ranges; ++i)
            touch(data + i * step, span, page);
        uint64_t reuse = now() - start;
        unsigned int new_faults = faults() - prior_faults;
        printf("%zu,%llu,%zu,%zu,%lld,%lld,%lld,%llu,%u,%llu,%d\n", bytes, release, before, after,
               (long long)vm_before.resident_size - (long long)vm_after.resident_size,
               (long long)vm_before.phys_footprint - (long long)vm_after.phys_footprint,
               (long long)vm_after.reusable - (long long)vm_before.reusable,
               reuse, new_faults, cold, called);
        if (load != NULL && munmap(load, load_size) != 0)
            abort();
        if (regions) {
            for (size_t slot = 0; slot < released_slots; ++slot) {
                crust_region_release(&slots[slot]);
                if (scattered || slot == 0) {
                    if (crust_region_data(&retained[slot])[0] != 99)
                        abort();
                    crust_region_release(&retained[slot]);
                }
            }
            crust_region_restore(NULL);
            crust_region_destroy(crust_region_global);
            crust_region_global = NULL;
        } else {
            crust_guarded_unmap(crust_stack, crust_capacity);
            crust_stack = NULL;
            crust_cursor = 0;
        }
    }
    free(pages);
}
