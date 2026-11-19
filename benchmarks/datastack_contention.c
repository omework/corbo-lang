// Build with clang -std=c11 -O2 -pthread benchmarks/datastack_contention.c -o /tmp/crust-contention.
#define _DEFAULT_SOURCE 1
#define _DARWIN_C_SOURCE 1
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

enum { max_workers = 8 };
static const size_t cycles = 500000;
static atomic_uint ready;
static atomic_bool start;
static pthread_mutex_t finish_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t finish_condition = PTHREAD_COND_INITIALIZER;
static unsigned long finished;
static unsigned long worker_count;

typedef struct {
    uint64_t begin;
    uint64_t end;
} Sample;

static uint64_t now(void) {
    struct timespec stamp;
    if (clock_gettime(CLOCK_MONOTONIC, &stamp) != 0)
        abort();
    return (uint64_t)stamp.tv_sec * 1000000000 + stamp.tv_nsec;
}

static void *worker(void *argument) {
    Sample *sample = argument;
    crust_regions_configure(0, 1024 * 1024, 8);
    CrustGrowing warm = crust_region_take();
    unsigned char *address = crust_region_data(&warm);
    crust_region_release(&warm);
    atomic_fetch_add_explicit(&ready, 1, memory_order_release);
    while (!atomic_load_explicit(&start, memory_order_acquire))
        sched_yield();

    sample->begin = now();
    for (size_t i = 0; i < cycles; ++i) {
        CrustGrowing value = crust_region_take();
        if (crust_region_data(&value) != address)
            abort();
        crust_region_release(&value);
    }
    sample->end = now();
    pthread_mutex_lock(&finish_mutex);
    if (++finished == worker_count)
        pthread_cond_broadcast(&finish_condition);
    while (finished != worker_count)
        pthread_cond_wait(&finish_condition, &finish_mutex);
    pthread_mutex_unlock(&finish_mutex);
    crust_region_restore(NULL);
    crust_worker_close_regions();
    return NULL;
}

int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    char *end;
    unsigned long workers = strtoul(argv[1], &end, 10);
    if (argv[1] == end || *end || workers == 0 || workers > max_workers)
        return 2;

    worker_count = workers;
    pthread_t threads[max_workers];
    Sample samples[max_workers] = {0};
    for (size_t i = 0; i < workers; ++i) {
        if (pthread_create(&threads[i], NULL, worker, &samples[i]) != 0)
            abort();
    }
    while (atomic_load_explicit(&ready, memory_order_acquire) != workers)
        sched_yield();
    atomic_store_explicit(&start, true, memory_order_release);

    uint64_t first = UINT64_MAX;
    uint64_t last = 0;
    for (size_t i = 0; i < workers; ++i) {
        if (pthread_join(threads[i], NULL) != 0)
            abort();
        if (samples[i].begin < first)
            first = samples[i].begin;
        if (samples[i].end > last)
            last = samples[i].end;
    }

    printf("%lu,%zu,%llu\n", workers, cycles, (unsigned long long)(last - first));
    return 0;
}
