/** @file threads.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
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

/** Maps native-worker metadata whose lifetime can extend beyond its launching scope. */
static NativeBox *native_box(void) {
#ifdef _WIN32
    void *memory = VirtualAlloc(NULL, sizeof(NativeBox), MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!memory) region_error();
#else
    void *memory = mmap(NULL, sizeof(NativeBox), PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (memory == MAP_FAILED) region_error();
#endif
    return memory;
}

/* The caller holds task_lock while it links or releases a native region. */
/** Releases a native worker's region and metadata; its frame must no longer be in use. */
static void native_release(NativeBox *box) {
    region_drop(&box->region);
#ifdef _WIN32
    VirtualFree(box, 0, MEM_RELEASE);
#else
    munmap(box, sizeof(NativeBox));
#endif
}

/** Establishes the worker's region scope from the configured budget before executing its frame. */
static void worker_regions(void){
if(!global_budget)return;size_t cells=global_budget/region_stride(global_limit);
if(cells){pthread_mutex_lock(&task_lock);region_enter(global_limit,cells,cells);pthread_mutex_unlock(&task_lock);}}
/** Runs a native frame on its worker datastack, publishes completion and handles abandoned-result cleanup before decrementing the active count. */
static void *native_run(void *data) {
    NativeBox *box = data;
    reserve(global_fixed_budget);worker_regions();
    if (!box->run(&box->state->task, false)) abort();
    pthread_mutex_lock(&task_lock);region_restore(NULL);pthread_mutex_unlock(&task_lock);
    release();
    pthread_mutex_lock(&task_lock);
    box->state->task.done = true;
    bool abandoned = box->abandoned;
    if (abandoned) {
        pthread_mutex_unlock(&task_lock);
        box->dispose(box->state,true);
        pthread_mutex_lock(&task_lock);
        native_release(box);
    }
    --native_count;
    pthread_cond_broadcast(&task_ready);
    pthread_mutex_unlock(&task_lock);
    return NULL;
}

/** Returns an inactive native execution descriptor with frame, run callback and cleanup callback. */
static inline __attribute__((unused)) TaskValue make_native(size_t size, bool (*run)(Task *, bool),void (*dispose)(TaskState *,bool)) {
    NativeBox *box = native_box();
    pthread_mutex_lock(&task_lock);
    TaskValue task = make_task_in(&box->region, size, run, !current_band && !global_budget);
    pthread_mutex_unlock(&task_lock);
    box->state = task.state;
    box->run = run;
    box->dispose = dispose;
    task.native = true;
    return task;
}

/** Starts a detached worker or records LaunchFailed and destroys the unexecuted captures; publication uses the runtime lock. */
static inline __attribute__((unused)) void start_native(TaskValue task) {
    pthread_t thread;
    pthread_attr_t attr;
    pthread_mutex_lock(&task_lock);
    int error = pthread_attr_init(&attr);
    if (!error) {
        error = pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
        if (!error) error = pthread_create(&thread, &attr, native_run, (NativeBox *)task.storage);
        pthread_attr_destroy(&attr);
    }
    if (error) {
        task.state->task.failed = true;
        task.state->task.done = true;
    } else ++native_count;
    pthread_mutex_unlock(&task_lock);
    if (error) ((NativeBox*)task.storage)->dispose(task.state,false);
}
/** Releases a completed native execution, destroying its result only when it was not transferred to the caller. */
static void release_native(TaskValue task,bool taken){
    NativeBox *box=(NativeBox*)task.storage;
    if(!taken&&!task.state->task.failed)box->dispose(task.state,true);
    pthread_mutex_lock(&task_lock);native_release(box);pthread_mutex_unlock(&task_lock);
}
/** Transfers final cleanup of a running native frame to its worker; completed frames are released immediately. */
static void abandon_native(TaskValue task) {
    if (!task.storage) return;
    pthread_mutex_lock(&task_lock);
    bool done=task.state->task.done;
    if(!done)((NativeBox*)task.storage)->abandoned=true;
    pthread_mutex_unlock(&task_lock);
    if(done)release_native(task,false);
}

/** Initializes a region while holding the shared runtime lock; the descriptor must remain at a stable address. */
static inline __attribute__((unused)) void value_region_new(Region*r,size_t width,int owned,int dedicated){
pthread_mutex_lock(&task_lock);region_new(r,width,owned,dedicated);pthread_mutex_unlock(&task_lock);}
/** Appends one region slot under the runtime lock and returns its address. */
static inline __attribute__((unused)) unsigned char *value_region_add(Region*r){
pthread_mutex_lock(&task_lock);unsigned char *place=region_add(r);pthread_mutex_unlock(&task_lock);return place;}
/** Unlinks and releases a region under the runtime lock after owned child cleanup. */
static inline __attribute__((unused)) void value_region_drop(Region*r){
pthread_mutex_lock(&task_lock);region_drop(r);pthread_mutex_unlock(&task_lock);}
/** Discards the execution stored at value and clears its storage link to prevent repeated cleanup. */
static inline __attribute__((unused)) void dispose_handle_value(void*raw){TaskValue*v=raw;discard_handle(*v);v->storage=NULL;}
/** Discards every stored handle from last to first before releasing the containing region. */
static inline __attribute__((unused)) void destroy_task_region(void*raw){Region*r=raw;TaskValue*v=(void*)r->data;
for(size_t i=r->len;i;--i)dispose_handle_value(&v[i-1]);value_region_drop(r);}
/** Enters a region scope under the runtime lock using explicit and inferred slot budgets. */
static inline __attribute__((unused)) void scoped_region_enter(size_t bytes,size_t count,size_t inferred){
pthread_mutex_lock(&task_lock);region_enter(bytes,count,inferred);pthread_mutex_unlock(&task_lock); }
/** Restores the saved region-scope mark under the runtime lock while preserving live transferred regions. */
static inline __attribute__((unused)) void scoped_region_restore(RegionBand *mark){
pthread_mutex_lock(&task_lock);region_restore(mark);pthread_mutex_unlock(&task_lock); }
/** Polls a blocking execution on its dedicated worker, waits for dependencies, publishes completion and releases worker storage. */
static void *run_blocking(void *arg) {
    Task *task = arg;
    if (!base) reserve(1);
    while (!task->poll(task, false)) {
        pthread_mutex_lock(&task_lock);
        while (task->waiting) pthread_cond_wait(&task_ready, &task_lock);
        pthread_mutex_unlock(&task_lock);
    }
    pthread_mutex_lock(&task_lock);
    task_publish(task);
    if (task->abandoned) {
        pthread_mutex_unlock(&task_lock);
        task->discard(task);
        pthread_mutex_lock(&task_lock);
    }
    --native_count;
    pthread_cond_broadcast(&task_ready);
    pthread_mutex_unlock(&task_lock);
    if (base) release();
    return NULL;
}

/** Launches a blocking worker for a TaskValue; on launch failure, clears captures and publishes a completed failed state. */
static inline __attribute__((unused)) TaskValue start_blocking(TaskValue v) {
    Task *task = &v.state->task;
    *task = (Task){.blocking=true,.poll=v.poll,.discard=task_abandoned};
    pthread_t thread;
    pthread_attr_t attr;
    pthread_mutex_lock(&task_lock);
    int error = pthread_attr_init(&attr);
    if (!error) {
        error = pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
        if (!error) error = pthread_create(&thread,&attr,run_blocking,task);
        pthread_attr_destroy(&attr);
    }
    if (!error) ++native_count;
    pthread_mutex_unlock(&task_lock);
    if (error) {
        task->failed = true;
        task->poll(task,true);
        task->done = true;
    }
    return v;
}
/** Waits under the condition variable until native/blocking executions and scheduled tasks have all finished. */
static inline __attribute__((unused)) void native_drain(void) {
    pthread_mutex_lock(&task_lock);
    while (native_count || task_active) pthread_cond_wait(&task_ready, &task_lock);
    pthread_mutex_unlock(&task_lock);
}
