/* SPDX-License-Identifier: MIT OR Apache-2.0 */
/** @file channel.c.inc C reference for the bounded channel Corbo runtime. */
#include <string.h>
/** Stable queue descriptor; all mutable fields require task_lock. */
typedef struct CorboChannelState {
    /** Dedicated managed payload storage. */
    Region storage;
    /** Fixed capacity, descriptor width, queued count and oldest ring index. */
    size_t capacity, width, count, head;
    /** Readiness change sequence, protected by task_lock. */
    uint64_t epoch;
    /** Prevents sends while permitting queued values to drain. */
    bool closed;
    /** Receive/send FIFO registration queues. */
    Task *heads[2], *tails[2];
} CorboChannelState;
/** Select one registered task; task_lock is held and polling never occurs inline. */
static void channel_wake_one(CorboChannelState *c, unsigned side) {
    Task *t=c->heads[side];
    if(!t)return;
    c->heads[side]=t->mutex_next;
    if(!c->heads[side])c->tails[side]=NULL;
    t->mutex_next=NULL;t->mutex_reserved=true;
    Task *root=t->root?t->root:t;root->waiting=false;
    if(root->parked){root->parked=false;if(!root->blocking)task_enqueue(root);}
}
/** Remove a persistent wait record before freeing its frame, forwarding a notification. */
static void channel_unlink(Task *t) {
    if(!t->channel_wait||!t->mutex_owner)return;
    CorboChannelState *c=(void*)t->mutex_owner;unsigned side=t->io_write?1:0;
    if(t->mutex_reserved)channel_wake_one(c,side);
    else {
        Task *previous=NULL,*next=c->heads[side];
        while(next&&next!=t){previous=next;next=next->mutex_next;}
        if(next){if(previous)previous->mutex_next=next->mutex_next;else c->heads[side]=next->mutex_next;
            if(c->tails[side]==t)c->tails[side]=previous;}
    }
    t->mutex_owner=0;t->mutex_next=NULL;t->mutex_reserved=false;t->channel_wait=false;
}
/** Reserve a finite byte ring in a detached managed region. */
static uintptr_t channel_create(size_t capacity,size_t width) {
    if(!capacity||!width||capacity>SIZE_MAX/width)abort();
#ifdef _WIN32
    CorboChannelState *c=VirtualAlloc(NULL,sizeof(*c),MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    if(!c)abort();
#else
    CorboChannelState *c=mmap(NULL,sizeof(*c),PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(c==MAP_FAILED)abort();
#endif
    c->capacity=capacity;c->width=width;
    pthread_mutex_lock(&task_lock);
    region_new(&c->storage,width,0,1);
    for(size_t i=0;i<capacity;++i)region_add(&c->storage);
    pthread_mutex_unlock(&task_lock);return(uintptr_t)c;
}
/** Move one complete typed descriptor into the ring, or leave it untouched on failure. */
static int64_t channel_send(uintptr_t raw,void *input,uint64_t *epoch,bool blocking) {
    CorboChannelState *c=(void*)raw;pthread_mutex_lock(&task_lock);
    while(blocking&&!c->closed&&c->count==c->capacity)pthread_cond_wait(&task_ready,&task_lock);
    *epoch=c->epoch;
    if(c->closed){pthread_mutex_unlock(&task_lock);return 2;}
    if(c->count==c->capacity){pthread_mutex_unlock(&task_lock);return 1;}
    size_t slot=(c->head+c->count)%c->capacity;
    memcpy(c->storage.data+slot*c->width,input,c->width);memset(input,0,c->width);
    c->count++;c->epoch++;channel_wake_one(c,0);pthread_cond_broadcast(&task_ready);
    pthread_mutex_unlock(&task_lock);return 0;
}
/** Move the oldest descriptor out; closed channels drain before signaling exhaustion. */
static int64_t channel_receive(uintptr_t raw,void *output,uint64_t *epoch,bool blocking) {
    CorboChannelState *c=(void*)raw;pthread_mutex_lock(&task_lock);
    while(blocking&&!c->closed&&!c->count)pthread_cond_wait(&task_ready,&task_lock);
    *epoch=c->epoch;
    if(!c->count){int64_t result=c->closed?2:1;pthread_mutex_unlock(&task_lock);return result;}
    void *slot=c->storage.data+c->head*c->width;
    memcpy(output,slot,c->width);memset(slot,0,c->width);
    c->head=(c->head+1)%c->capacity;c->count--;c->epoch++;
    channel_wake_one(c,1);pthread_cond_broadcast(&task_ready);
    pthread_mutex_unlock(&task_lock);return 0;
}
/** Close once and wake both waiting senders and receivers. */
static void channel_close(uintptr_t raw) {
    CorboChannelState *c=(void*)raw;pthread_mutex_lock(&task_lock);
    if(!c->closed){c->closed=true;c->epoch++;
        while(c->heads[0])channel_wake_one(c,0);
        while(c->heads[1])channel_wake_one(c,1);
        pthread_cond_broadcast(&task_ready);}
    pthread_mutex_unlock(&task_lock);
}
/** Check the epoch and register under the same lock, closing the lost-wakeup window. */
static bool channel_poll(Task *t,uintptr_t raw,uint64_t epoch,bool sending) {
    CorboChannelState *c=(void*)raw;pthread_mutex_lock(&task_lock);
    if(c->epoch!=epoch||c->closed){channel_unlink(t);pthread_mutex_unlock(&task_lock);return true;}
    if(!t->mutex_owner){unsigned side=sending?1:0;t->mutex_owner=raw;t->channel_wait=true;
        t->mutex_reserved=false;t->mutex_next=NULL;t->io_write=sending;
        if(c->tails[side])c->tails[side]->mutex_next=t;else c->heads[side]=t;
        c->tails[side]=t;}
    Task *root=t->root?t->root:t;root->waiting=true;pthread_mutex_unlock(&task_lock);return false;
}
/** Unregister before frame reclamation. */
static void channel_detach(Task *t){if(!t->channel_wait)return;pthread_mutex_lock(&task_lock);channel_unlink(t);pthread_mutex_unlock(&task_lock);}
/** Release drained storage only after all borrowed users have ended. */
static void channel_destroy(uintptr_t raw) {
    CorboChannelState *c=(void*)raw;pthread_mutex_lock(&task_lock);
    if(c->count||c->heads[0]||c->heads[1])abort();
    region_drop(&c->storage);
#ifdef _WIN32
    if(!VirtualFree(c,0,MEM_RELEASE))abort();
#else
    if(munmap(c,sizeof(*c)))abort();
#endif
    pthread_mutex_unlock(&task_lock);
}
