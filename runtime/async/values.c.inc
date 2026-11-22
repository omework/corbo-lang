/** @file values.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
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
/** Installs next as the thread-local fixed-stack/region context and returns the previous context for later restoration. */
static inline __attribute__((unused)) ClassicStack swap_classic(ClassicStack next){
ClassicStack old={base,cursor,limit,committed,page_size,mapped_size,current_band,metric_pool_head};
base=next.base;cursor=next.cursor;limit=next.limit;committed=next.committed;page_size=next.page_size;
mapped_size=next.mapped_size;current_band=next.band;metric_pool_head=next.metric_pools;return old;}
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
/** Returns an inactive task descriptor backed by the supplied stable region; caller holds the runtime lock. */
static TaskValue make_task_in(Region *r,size_t size,bool(*poll)(Task*,bool),bool dedicated){
region_new(r,size,0,dedicated);TaskState *s=(void*)region_add(r);*s=(TaskState){.region=r};return(TaskValue){.state=s,.storage=r,.poll=poll};}
#include <string.h>
/** Releases a completed native execution, destroying its result only when it was not transferred to the caller. */
static void release_native(TaskValue task,bool taken);
/** Transfers final cleanup of a running native frame to its worker; completed frames are released immediately. */
static void abandon_native(TaskValue task);
/** Maps separate runtime metadata of the requested byte size; terminates if the OS cannot provide it. */
static void* task_metadata(size_t bytes){
#ifdef _WIN32
void *p=VirtualAlloc(NULL,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!p)region_error();
#else
void *p=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(p==MAP_FAILED)region_error();
#endif
return p;}
/** Unmaps a metadata address with the original mapping byte count after its users finish. */
static void task_unmap(void*p,size_t bytes){
#ifdef _WIN32
(void)bytes;VirtualFree(p,0,MEM_RELEASE);
#else
munmap(p,bytes);
#endif
}
/** Returns an inactive task descriptor backed by a region and separately owned metadata. */
static inline __attribute__((unused)) TaskValue make_task(size_t size,bool(*poll)(Task*,bool)){
Region*r=task_metadata(sizeof(Region));pthread_mutex_lock(&task_lock);
TaskValue v=make_task_in(r,size,poll,!current_band&&!global_budget);pthread_mutex_unlock(&task_lock);
v.state->own_region=true;return v;}
/** Cleans an untaken result or inactive captures, releases frame storage, and unmaps separately owned metadata. */
static void release_future(TaskState*s,bool completed,bool taken){
channel_detach(&s->task);
mutex_detach(&s->task);
Region*r=s->region;bool own=s->own_region;if(s->dispose&&!taken)s->dispose(s,completed);
pthread_mutex_lock(&task_lock);region_drop(r);pthread_mutex_unlock(&task_lock);if(own)task_unmap(r,sizeof(Region));}
/** Releases a completed abandoned task, including its untaken result. */
static void task_abandoned(Task*task){TaskState*s=(void*)task;release_future(s,true,false);}
/** Schedules a TaskValue using its poll function and the abandoned-task cleanup callback. */
static inline __attribute__((unused)) TaskValue start_task(TaskValue v){task_spawn_with(&v.state->task,v.poll,task_abandoned);return v;}
/** Marks an active execution abandoned or releases a completed one; native executions use their separate ownership path. */
static inline __attribute__((unused)) void discard_handle(TaskValue v){
if(!v.storage)return;if(v.native){abandon_native(v);return;}
pthread_mutex_lock(&task_lock);bool done=v.state->task.done;if(!done)v.state->task.abandoned=true;pthread_mutex_unlock(&task_lock);
if(done)release_future(v.state,true,v.state->task.failed);}
/** Waits for completion, returns a scalar completion descriptor and releases consumed handle storage. */
static inline __attribute__((unused)) TaskCompletion join_task(TaskValue v){
task_join(&v.state->task);TaskCompletion r={!v.state->task.failed,v.state->value};if(v.native)release_native(v,true);else release_future(v.state,true,true);return r;}
/** Waits for completion and moves a successful aggregate payload into caller storage; returns false on launch failure. */
static inline __attribute__((unused)) bool join_task_into(TaskValue v,void *out,size_t bytes){
task_join(&v.state->task);bool ok=!v.state->task.failed;if(ok)memcpy(out,v.state->payload,bytes);
if(v.native)release_native(v,ok);else release_future(v.state,true,true);return ok;}
/** Destroys captures and storage of a nonempty inactive future descriptor. */
static inline __attribute__((unused)) void discard_future(TaskValue v){if(v.storage)release_future(v.state,false,false);}
