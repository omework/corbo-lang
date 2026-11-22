/** @file corbo_runtime_abi.h
 * Typed platform/ABI layouts for the Corbo runtime; raw access requires caller-managed lifetime and synchronization.
 */
/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#ifndef CORBO_RUNTIME_CORBO_ABI_H
#define CORBO_RUNTIME_CORBO_ABI_H
#ifndef CORBO_RUNTIME_H
#include "corbo_runtime.h"
#endif
#include <pthread.h>
#include <string.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
#ifndef _WIN32
#include <unistd.h>
#include <sys/mman.h>
#else
#include <windows.h>
#endif
_Static_assert(sizeof(uintptr_t)==8,"Corbo runtime requires a supported 64-bit target");
_Static_assert(sizeof(void(*)(void))==sizeof(uintptr_t),"unsupported callback representation");
#include "../memory/metrics_storage.h"
static _Thread_local unsigned char *base;
static _Thread_local size_t cursor,limit,committed,page_size,mapped_size;
static size_t global_fixed_budget=1073741824ULL,global_budget,global_limit=104857600ULL;
static RegionBand global_band;
static _Thread_local RegionBand *current_band;
static size_t fixed_reclaim_threshold,region_reclaim_threshold;
/** Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock. */
typedef struct Task Task;
/** Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock. */
struct Task {
    /** pc: resume-state program counter. */
    size_t pc;
    /** poll: typed poll/clear callback. */
    bool (*poll)(Task *, bool);
    /** next: ready-queue next link. */
    Task *next;
    /** failed: launch-failure flag. */
    bool failed;
    /** done: completion-publication flag. */
    bool done;
    /** abandoned: worker-owned final-cleanup flag. */
    bool abandoned;
    /** discard: typed abandoned-task cleanup callback. */
    void (*discard)(Task *);
    /** root: outer polling-root link. waiter: dependent polling-root link. */
    Task *root, *waiter;
    /** io_ready: readiness-publication flag. io_registered: active-wait registration flag. */
    bool io_ready, io_registered;
    /** io_socket: native socket identifier. */
    uint64_t io_socket;
    /** io_write: write-interest selector. */
    bool io_write;
    /** io_next: intrusive readiness-waiter link. */
    Task *io_next;
    /** io_token: readiness-generation token. */
    uintptr_t io_token;
    /** io_error: recorded platform I/O status. */
    int64_t io_error;
    /** waiting: dependency-wait predicate. parked: removed-from-ready-queue flag. blocking: dedicated blocking-worker flag. */
    bool waiting, parked, blocking;
    /** mutex_next: next waiter in a mutex FIFO, protected by task_lock. */
    Task *mutex_next;
    /** mutex_owner: logical async mutex currently retaining this waiter. */
    uintptr_t mutex_owner;
    /** mutex_reserved: release handed this waiter the next acquisition. */
    bool mutex_reserved;
    /** channel_wait: selects the channel queue owning this wait record. */
    /** Distinguishes channel registration from the reused mutex wait fields. */
    bool channel_wait;
};
/** Native mutex storage; its address remains stable until the owner is destroyed. */
typedef struct CorboMutexState {
    /** gate: native mutex, held through synchronous guard ownership only. */
    pthread_mutex_t gate;
    /** owner: thread which acquired the synchronous guard. */
    pthread_t owner;
    /** asynchronous: chooses logical task ownership instead of native guard ownership. */
    bool asynchronous;
    /** held: logical async lock state, protected by task_lock. */
    bool held;
    /** head: first queued waiter. tail: FIFO insertion point. */
    Task *head, *tail;
    /** reservation: waiter receiving a release-to-next handoff. */
    Task *reservation;
} CorboMutexState;
/** Fixed-capacity typed-byte ring and intrusive async waiter queues. All mutable fields require task_lock. */
/** Bounded erased storage; the STD retains typed ownership and destructor dispatch. */
typedef struct CorboChannelState {
    /** Dedicated queue region, independent of the constructor's scope. */
    Region storage;
    /** Capacity and descriptor width; live count and oldest ring position. */
    size_t capacity, width, count, head;
    /** Readiness change counter, protected with all queue fields by task_lock. */
    uint64_t epoch;
    /** Once closed, sends fail and receivers only drain existing values. */
    bool closed;
    /** Intrusive receive/send queues; task records outlive their registrations. */
    Task *heads[2], *tails[2];
} CorboChannelState;
static pthread_t task_workers[2];
static size_t task_worker_count;
static pthread_mutex_t task_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t task_ready = PTHREAD_COND_INITIALIZER;
static Task *task_head;
static Task **task_tail = &task_head;
static bool task_attempted, task_stopping;
static size_t task_active;

/** Inline scalar result union; the generated frame contract determines the active member. */
typedef union {
    /** k1: Result storage for i32. */
    int32_t k1;
    /** k2: Result storage for i64. */
    int64_t k2;
    /** k3: Result storage for bool. */
    bool k3;
    /** k4: Result storage for u8. */
    uint8_t k4;
    /** k5: Result storage for u16. */
    uint16_t k5;
    /** k6: Result storage for u32. */
    uint32_t k6;
    /** k7: Result storage for u64. */
    uint64_t k7;
    /** k8: Result storage for f32. */
    float k8;
    /** k9: Result storage for f64. */
    double k9;
} TaskResult;
/** Saved thread-local fixed-stack mapping and region-scope context for task suspension/resumption. */
typedef struct {
    /** base: saved fixed-stack base. */
    unsigned char *base;
    /** cursor: saved next free byte offset. limit: saved fixed-stack capacity. committed: saved committed-byte boundary. page_size: saved OS page size. mapped_size: saved mapping extent. */
    size_t cursor,limit,committed,page_size,mapped_size;
    /** band: saved region-scope link. */
    RegionBand *band;
    /** metric_pools: suspended fixed-stack pool accounting chain. */
    Pools *metric_pools;
} ClassicStack;
/** Task header at offset zero plus result, frame-region ownership, cleanup callback and saved storage context. */
typedef struct TaskState {
    /** task: scheduler header at offset zero. */
    Task task;
    /** value: inline scalar result storage. */
    TaskResult value;
    /** payload: aggregate result address. */
    void *payload;
    /** region: frame-storage region link. */
    Region *region;
    /** own_region: separate region-descriptor ownership flag. */
    bool own_region;
    /** dispose: typed capture/result cleanup callback. */
    void (*dispose)(struct TaskState*,bool);
    /** classic: suspended thread-local datastack context. */
    ClassicStack classic;
} TaskState;
/** Future/handle descriptor linking an execution frame, backing region, typed poll callback and native-worker mode. */
typedef struct {
    /** state: execution frame address. */
    TaskState *state;
    /** storage: owned backing-region link. */
    Region *storage;
    /** poll: frame-specific poll callback. */
    bool (*poll)(Task *,bool);
    /** native: native-worker ownership selector. */
    bool native;
} TaskValue;
/** Success flag and inline scalar result moved out by join_task. */
typedef struct {
    /** ok: successful-launch/completion flag. */
    bool ok;
    /** value: moved scalar result bits. */
    TaskResult value;
} TaskCompletion;
/** Worker metadata with its Region prefix at offset zero; abandonment can transfer final cleanup to the worker. */
typedef struct NativeBox {
    /** region: embedded frame region at offset zero. */
    Region region;
    /** state: native frame address. */
    TaskState *state;
    /** run: native frame run callback. */
    bool (*run)(Task *, bool);
    /** abandoned: worker-owned cleanup flag. */
    bool abandoned;
    /** dispose: capture/result cleanup callback. */
    void (*dispose)(TaskState *,bool);
} NativeBox;

static size_t native_count;

_Static_assert(offsetof(TaskState,task)==0,"TaskState ABI prefix changed");
_Static_assert(offsetof(NativeBox,region)==0,"NativeBox ABI prefix changed");
static pthread_once_t socket_once=PTHREAD_ONCE_INIT,completion_once=PTHREAD_ONCE_INIT;
static int64_t socket_queue=-1,socket_init_error=-1,completion_init_error=-8;
static Task *socket_waiters;
static uintptr_t socket_serial,completion_port;
#endif
