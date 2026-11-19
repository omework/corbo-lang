// Compile from the repository root with clang -std=c11 -O2 benchmarks/datastack.c -o /tmp/crust-datastack.
#define _DEFAULT_SOURCE 1
#define _DARWIN_C_SOURCE 1
#include <stdbool.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach/mach.h>
#endif

static size_t maps, unmaps;

static void *counted_map(void *addr, size_t size, int prot, int flags, int fd, off_t offset) {
    ++maps;
    return mmap(addr, size, prot, flags, fd, offset);
}

static int counted_unmap(void *addr, size_t size) {
    ++unmaps;
    return munmap(addr, size);
}

#define mmap counted_map
#define munmap counted_unmap
#include "../rust_frontend/src/datastack.c"
#include "../rust_frontend/src/region_storage.c"
#undef mmap
#undef munmap

static uint64_t now(void) {
#ifdef __APPLE__
    return clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
#else
    struct timespec stamp;
    if (clock_gettime(CLOCK_MONOTONIC, &stamp) != 0)
        abort();
    return (uint64_t)stamp.tv_sec * 1000000000 + stamp.tv_nsec;
#endif
}

static uint64_t rss(void) {
#ifdef __APPLE__
    mach_task_basic_info_data_t info;
    mach_msg_type_number_t count = MACH_TASK_BASIC_INFO_COUNT;
    if (task_info(mach_task_self(), MACH_TASK_BASIC_INFO, (task_info_t)&info, &count) != KERN_SUCCESS)
        abort();
    return info.resident_size;
#else
    return 0;
#endif
}

static uint64_t faults(void) {
#ifdef __APPLE__
    task_events_info_data_t events;
    mach_msg_type_number_t count = TASK_EVENTS_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_EVENTS_INFO, (task_info_t)&events, &count) != KERN_SUCCESS)
        abort();
    return events.faults;
#else
    struct rusage usage;
    if (getrusage(RUSAGE_SELF, &usage) != 0)
        abort();
    return usage.ru_minflt + usage.ru_majflt;
#endif
}

static void touch(unsigned char *data, size_t bytes, size_t page) {
    volatile unsigned char *memory = data;
    for (size_t i = 0; i < bytes; i += page)
        memory[i] = 1;
}

// Keep cursor operations observable in the timing loop.
static void observe(void) {
    __asm__ volatile("" ::: "memory");
}

int main(int argc, char **argv) {
    if (argc != 4)
        return 2;
    bool regions = strcmp(argv[1], "regions") == 0;
    size_t stride = strtoul(argv[2], NULL, 10) * 1024 * 1024;
    size_t count = strtoul(argv[3], NULL, 10);
    size_t capacity = 256 * 1024 * 1024;
    if ((!regions && strcmp(argv[1], "fixed") != 0) ||
        stride == 0 || count == 0 || count > capacity / stride)
        return 2;
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    size_t bytes = 1024 * 1024;
    unsigned char **data = calloc(count, sizeof(*data));
    CrustGrowing *values = calloc(count, sizeof(*values));
    if (!data || !values)
        abort();

    // Initialize measurement APIs before the baseline.
    now();
    faults();
    uint64_t rss_before = rss();
    uint64_t start = now();
    if (regions) {
        crust_region_global = crust_region_band(stride, capacity / stride);
    } else {
        crust_set_capacity(capacity);
        crust_push(1, 1, 1);
        crust_cursor = 0;
    }
    uint64_t reservation = now() - start;
    uint64_t rss_reserved = rss();
    size_t reservation_maps = maps;

    for (size_t i = 0; i < count; ++i) {
        if (regions) {
            values[i] = crust_region_take();
            data[i] = crust_region_data(&values[i]);
        } else {
            data[i] = crust_push(1, 1, stride);
        }
    }
    uint64_t faults_before = faults();
    start = now();
    for (size_t i = 0; i < count; ++i)
        touch(data[i], bytes, page);
    uint64_t cold = now() - start;
    uint64_t cold_faults = faults() - faults_before;
    uint64_t rss_touched = rss();

    start = now();
    if (regions) {
        for (size_t i = 0; i < count; ++i)
            crust_region_release(&values[i]);
        crust_region_restore(NULL);
    } else {
        crust_cursor = 0;
    }
    observe();
    uint64_t rewind = now() - start;
    uint64_t rss_rewound = rss();

    const size_t repeats = 200000;
    start = now();
    for (size_t round = 0; round < repeats; ++round) {
        for (size_t i = 0; i < count; ++i) {
            if (regions) {
                values[i] = crust_region_take();
                if (crust_region_data(&values[i]) != data[i])
                    abort();
            } else if (crust_push(1, 1, stride) != data[i]) {
                abort();
            }
            observe();
        }
        if (regions) {
            for (size_t i = 0; i < count; ++i)
                crust_region_release(&values[i]);
            crust_region_restore(NULL);
        } else {
            crust_cursor = 0;
        }
        observe();
    }
    uint64_t churn = now() - start;
    faults_before = faults();
    start = now();
    for (size_t i = 0; i < count; ++i)
        touch(data[i], bytes, page);
    uint64_t warm = now() - start;
    uint64_t warm_faults = faults() - faults_before;

    double hole_ns = 0;
    if (regions && crust_region_global->count >= 2) {
        size_t slots = crust_region_global->count;
        CrustGrowing *filled = calloc(slots, sizeof(*filled));
        if (!filled)
            abort();
        for (size_t i = 0; i < slots; ++i)
            filled[i] = crust_region_take();
        size_t hole = slots - 2;
        start = now();
        for (size_t round = 0; round < repeats; ++round) {
            crust_region_release(&filled[hole]);
            filled[hole] = crust_region_take();
            if (filled[hole].slot != hole)
                abort();
            observe();
        }
        hole_ns = (double)(now() - start) / repeats;
        for (size_t i = 0; i < slots; ++i)
            crust_region_release(&filled[i]);
        crust_region_restore(NULL);
        free(filled);
    }

    start = now();
    if (regions)
        crust_region_destroy(crust_region_global);
    else
        crust_guarded_unmap(crust_stack, capacity);
    uint64_t destroy = now() - start;
    uint64_t rss_destroyed = rss();
    printf("%s,%zu,%zu,%zu,%zu,%zu,%zu,%zu,%llu,%llu,%llu,%llu,%llu,%.2f,%llu,%llu,%lld,%lld,%lld,%lld,%.2f\n",
           argv[1], stride >> 20, count, page, capacity, count * bytes,
           reservation_maps, unmaps, (unsigned long long)reservation,
           (unsigned long long)cold, (unsigned long long)cold_faults,
           (unsigned long long)rewind, (unsigned long long)warm,
           (double)churn / repeats / count, (unsigned long long)warm_faults,
           (unsigned long long)destroy, (long long)rss_reserved - (long long)rss_before,
           (long long)rss_touched - (long long)rss_before,
           (long long)rss_rewound - (long long)rss_before,
           (long long)rss_destroyed - (long long)rss_before, hole_ns);
    free(values);
    free(data);
    return 0;
}
