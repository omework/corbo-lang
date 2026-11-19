"""MT9/SL1 internal ABI checks, without inventing public mutex constructors."""
import unittest
from async_runtime import TASK_RUNTIME, TASK_THREAD_RUNTIME, TASK_SELECT_RUNTIME
import test_async_runtime as runtime

RUNTIME=TASK_RUNTIME+TASK_THREAD_RUNTIME+TASK_SELECT_RUNTIME+r'''
#include <assert.h>
static int destroyed;
static void destroy_value(void *value) { assert(value); ++destroyed; }
static CrustTaskStep unused_resume(CrustTask *task) {(void)task;return TASK_STEP_RETURN;}
static void unused_take(CrustTask *task,void *out) {(void)task;(void)out;}
static void unused_release(CrustTask *task) {(void)task;}
static const CrustTaskOps unused_ops={unused_resume,unused_take,unused_release};
'''

class MutexRuntimeTests(unittest.TestCase):
    run_c_oracle=runtime.AsyncRuntimeTests.run_c_oracle

    def test_sync_guard_thread_affinity_and_visibility(self):
        self.run_c_oracle(RUNTIME+r'''
static CrustSyncMutex mutex;
static CrustSyncGuard guard;
static _Atomic int entered,acquired;
static void *wrong_thread(void *arg) {
    (void)arg;
    assert(crust_sync_guard_drop(&guard)==EPERM);
    atomic_store(&entered,1);
    CrustSyncGuard next={0};
    crust_sync_mutex_lock(&mutex,&next);
    assert(*(int *)next.value==20);
    *(int *)next.value=30;
    atomic_store(&acquired,1);
    assert(crust_sync_guard_drop(&next)==0);
    return NULL;
}
int main(void) {
    (void)unused_ops;
    int value=10;
    assert(crust_sync_mutex_init(&mutex,&value,destroy_value)==0);
    crust_sync_mutex_lock(&mutex,&guard);
    assert(guard.value==&value);
    assert(crust_sync_mutex_destroy(&mutex)==EBUSY);
    pthread_t thread;
    assert(pthread_create(&thread,NULL,wrong_thread,NULL)==0);
    while(!atomic_load(&entered)) sched_yield();
    assert(!atomic_load(&acquired));
    value=20;
    assert(crust_sync_guard_drop(&guard)==0);
    assert(crust_sync_guard_drop(&guard)==EINVAL);
    assert(pthread_join(thread,NULL)==0);
    assert(value==30 && atomic_load(&acquired));
    assert(crust_sync_mutex_destroy(&mutex)==0 && destroyed==1);
    return 0;
}
''')

    def test_async_guard_migrates_and_wakes_parked_task(self):
        self.run_c_oracle(RUNTIME+r'''
typedef struct {
    CrustTask task;
    CrustMutexWait wait;
    CrustAsyncGuard guard;
    CrustAsyncMutex *mutex;
    int phase,id,seen;
    pthread_t acquired_on;
} Frame;
static CrustTaskStep resume(CrustTask *task) {
    Frame *f=(Frame *)task;
    if(!f->phase) {
        CrustTaskStep step=crust_async_mutex_poll(f->mutex,&f->wait,task,&f->guard);
        if(step!=TASK_STEP_RETURN) return step;
        f->acquired_on=pthread_self();
        f->seen=*(int *)f->guard.value;
        f->phase=1;
        return TASK_STEP_YIELD;
    }
    if(f->id==1) assert(!pthread_equal(f->acquired_on,pthread_self()));
    *(int *)f->guard.value+=10;
    assert(crust_async_guard_drop(&f->guard)==0);
    crust_mutex_wait_discard(&f->wait);
    return TASK_STEP_RETURN;
}
static const CrustTaskOps ops={resume,unused_take,unused_release};
static void *one_poll(void *queue) {
    assert(task_queue_run_one(queue,0));return NULL;
}
int main(void) {
    (void)unused_ops;
    int value=10;
    CrustAsyncMutex mutex;
    assert(crust_async_mutex_init(&mutex,&value,destroy_value)==0);
    CrustReadyQueue queue;
    assert(task_queue_init(&queue)==0);
    CrustQueueEntry entries[2];
    Frame frames[2]={0};
    for(int i=0;i<2;++i) {
        task_queue_entry_init(&entries[i]);
        frames[i].mutex=&mutex;frames[i].id=i+1;
        task_init(&frames[i].task,&ops);
        CrustWakeTicket ticket;
        assert(task_queue_submit(&queue,&entries[i],&frames[i].task,&ticket)==0);
    }
    assert(task_queue_run_one(&queue,0)); /* First holds guard across yield. */
    assert(task_queue_run_one(&queue,0)); /* Second parks, without requeueing. */
    assert(frames[1].wait.state==CRUST_MUTEX_WAITING);
    assert(queue.head==&entries[0] && queue.tail==&entries[0]);
    pthread_t thread;
    assert(pthread_create(&thread,NULL,one_poll,&queue)==0);
    assert(pthread_join(thread,NULL)==0);
    assert(queue.head==&entries[1]); /* Cross-thread drop woke the waiter. */
    assert(task_queue_run_one(&queue,0));
    assert(frames[1].seen==20);
    assert(task_queue_run_one(&queue,0));
    assert(value==30 && frames[0].seen==10);
    for(int i=0;i<2;++i) {
        assert(task_take(&frames[i].task,NULL));
        task_queue_entry_destroy(&entries[i]);
    }
    assert(task_queue_close(&queue)==0);task_queue_destroy(&queue);
    assert(crust_async_mutex_destroy(&mutex)==0 && destroyed==1);
    return 0;
}
''')

    def test_select_drop_cleans_wait_reservation_or_acquired_guard(self):
        code=RUNTIME+r'''
static CrustAsyncMutex mutex;
static CrustAsyncGuard owner;
static int released;
typedef struct {CrustTask task;CrustMutexWait wait;CrustAsyncGuard guard;int ready;} Branch;
static CrustTaskStep resume(CrustTask *task) {
    Branch *b=(Branch *)task;
    if(b->ready) {
        if(MODE==1) assert(crust_async_guard_drop(&owner)==0);
        return TASK_STEP_RETURN;
    }
    CrustTaskStep step=crust_async_mutex_poll(&mutex,&b->wait,task,&b->guard);
    return step==TASK_STEP_RETURN ? TASK_STEP_YIELD : step;
}
static void release(CrustTask *task) {
    Branch *b=(Branch *)task;
    crust_mutex_wait_discard(&b->wait);
    if(b->guard.mutex) assert(crust_async_guard_drop(&b->guard)==0);
    ++released;
}
static const CrustTaskOps ops={resume,unused_take,release};
int main(void) {
    (void)unused_ops;
    int value=7;
    assert(crust_async_mutex_init(&mutex,&value,destroy_value)==0);
    CrustTask parent;task_init(&parent,&unused_ops);
    CrustMutexWait first={0};
    if(MODE!=2) assert(crust_async_mutex_poll(&mutex,&first,&parent,&owner)==TASK_STEP_RETURN);
    CrustQueueEntry entries[2];Branch branches[2]={0};
    for(int i=0;i<2;++i) {
        task_queue_entry_init(&entries[i]);task_init(&branches[i].task,&ops);
        branches[i].task.queue_entry=&entries[i];branches[i].ready=i;
    }
    CrustSelectBranch descriptors[2]={{&branches[0].task,release},{&branches[1].task,release}};
    CrustSelect selection;task_select_init(&selection,descriptors,2);
    assert(task_select_poll(&selection,&parent)==TASK_STEP_RETURN);
    assert(selection.winner==1 && released==0);
    assert(branches[0].wait.state==(MODE==0 ? CRUST_MUTEX_WAITING :
           MODE==1 ? CRUST_MUTEX_RESERVED : CRUST_MUTEX_TAKEN));
    assert(crust_async_mutex_destroy(&mutex)==EBUSY);
    assert(task_select_take(&selection,NULL) && released==1);
    assert(crust_async_mutex_destroy(&mutex)==EBUSY); /* Loser retained. */
    task_select_drop(&selection);assert(released==2);
    assert(mutex.head==NULL && mutex.reservation==NULL);
    if(MODE==0) assert(crust_async_guard_drop(&owner)==0);
    for(int i=0;i<2;++i)task_queue_entry_destroy(&entries[i]);
    assert(crust_async_mutex_destroy(&mutex)==0 && destroyed==1);
    /* Completed wait cleanup must not touch an already destroyed mutex. */
    crust_mutex_wait_discard(&first);
    return 0;
}
'''
        for mode in (0,1,2):
            with self.subTest(mode=mode):self.run_c_oracle(code.replace('MODE',str(mode)))

    def test_discarded_reservation_hands_lock_to_next_waiter(self):
        self.run_c_oracle(RUNTIME+r'''
int main(void) {
    (void)unused_ops;
    int value=10;CrustAsyncMutex mutex;
    assert(crust_async_mutex_init(&mutex,&value,NULL)==0);
    CrustTask tasks[4];CrustQueueEntry entries[4];
    CrustMutexWait waits[4]={0};CrustAsyncGuard guards[4]={0};
    for(int i=0;i<4;++i) {
        task_init(&tasks[i],&unused_ops);task_queue_entry_init(&entries[i]);
        tasks[i].queue_entry=&entries[i];assert(task_external_register(&tasks[i])==0);
    }
    assert(crust_async_mutex_poll(&mutex,&waits[0],&tasks[0],&guards[0])==TASK_STEP_RETURN);
    for(int i=1;i<3;++i)
        assert(crust_async_mutex_poll(&mutex,&waits[i],&tasks[i],&guards[i])==TASK_STEP_PENDING);
    assert(crust_async_guard_drop(&guards[0])==0);
    assert(waits[1].state==CRUST_MUTEX_RESERVED);
    /* A fresh arrival cannot steal the reservation. */
    assert(crust_async_mutex_poll(&mutex,&waits[3],&tasks[3],&guards[3])==TASK_STEP_PENDING);
    crust_mutex_wait_discard(&waits[1]);
    assert(waits[2].state==CRUST_MUTEX_RESERVED);
    assert(crust_async_mutex_poll(&mutex,&waits[2],&tasks[2],&guards[2])==TASK_STEP_RETURN);
    assert(guards[2].value==&value);
    crust_mutex_wait_discard(&waits[3]);
    assert(mutex.head==NULL && mutex.tail==NULL);
    assert(crust_async_guard_drop(&guards[2])==0);
    assert(crust_async_guard_drop(&guards[2])==EINVAL);
    for(int i=0;i<4;++i) {
        crust_mutex_wait_discard(&waits[i]);
        task_external_forget(&tasks[i]);task_queue_entry_destroy(&entries[i]);
    }
    assert(crust_async_mutex_destroy(&mutex)==0);
    return 0;
}
''')

if __name__=='__main__':unittest.main()
