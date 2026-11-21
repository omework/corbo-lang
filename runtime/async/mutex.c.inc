/** @file mutex.c.inc
 * C reference for stable native locks and FIFO asynchronous task ownership.
 */
/* SPDX-License-Identifier: MIT OR Apache-2.0 */
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
/** Creates stable OS-backed mutex metadata; no native lock is moved. */
static uintptr_t mutex_create(bool asynchronous) {
#ifdef _WIN32
 CorboMutexState*m=VirtualAlloc(NULL,sizeof(*m),MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
 if(!m)abort();
#else
 CorboMutexState*m=mmap(NULL,sizeof(*m),PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(m==MAP_FAILED)abort();
#endif
 if(pthread_mutex_init(&m->gate,NULL))abort();m->asynchronous=asynchronous;return(uintptr_t)m;
}
/** Acquires a blocking native-thread-bound guard. */
static void mutex_acquire(uintptr_t raw){CorboMutexState*m=(void*)raw;if(pthread_mutex_lock(&m->gate))abort();m->owner=pthread_self();}
/** Reserves the FIFO successor; caller holds task_lock. */
static void mutex_handoff(uintptr_t raw){
 CorboMutexState*m=(void*)raw;Task*t=m->head;m->reservation=t;
 if(!t){m->held=false;return;}m->head=t->mutex_next;if(!m->head)m->tail=NULL;t->mutex_next=NULL;t->mutex_reserved=true;
 Task*r=t->root?t->root:t;r->waiting=false;if(r->parked){r->parked=false;if(!r->blocking)task_enqueue(r);}pthread_cond_broadcast(&task_ready);
}
/** Acquires or parks one persistent task wait record. */
static bool mutex_poll(Task*t,uintptr_t raw){
 CorboMutexState*m=(void*)raw;pthread_mutex_lock(&task_lock);
 if(t->mutex_owner==raw&&t->mutex_reserved){if(m->reservation!=t)abort();m->reservation=NULL;t->mutex_owner=0;t->mutex_reserved=false;pthread_mutex_unlock(&task_lock);return true;}
 if(!m->held){m->held=true;pthread_mutex_unlock(&task_lock);return true;}
 if(!t->mutex_owner){t->mutex_owner=raw;t->mutex_next=NULL;if(m->tail)m->tail->mutex_next=t;else m->head=t;m->tail=t;}
 Task*r=t->root?t->root:t;r->waiting=true;pthread_mutex_unlock(&task_lock);return false;
}
/** Releases native-thread ownership or hands logical ownership to a waiter. */
static void mutex_release(uintptr_t raw){CorboMutexState*m=(void*)raw;
 if(!m->asynchronous){if(!pthread_equal(m->owner,pthread_self())||pthread_mutex_unlock(&m->gate))abort();return;}
 pthread_mutex_lock(&task_lock);if(!m->held||m->reservation)abort();mutex_handoff(raw);pthread_mutex_unlock(&task_lock);
}
/** Removes a pending wait before its frame storage is reclaimed. */
static void mutex_detach(Task*t){uintptr_t raw=t->mutex_owner;if(!raw)return;CorboMutexState*m=(void*)raw;
 pthread_mutex_lock(&task_lock);if(m->reservation==t){m->reservation=NULL;mutex_handoff(raw);}else{
 Task*p=NULL,*n=m->head;while(n&&n!=t){p=n;n=n->mutex_next;}if(n){if(p)p->mutex_next=n->mutex_next;else m->head=n->mutex_next;if(m->tail==n)m->tail=p;}}
 t->mutex_owner=0;t->mutex_next=NULL;t->mutex_reserved=false;pthread_mutex_unlock(&task_lock);
}
/** Destroys unlocked metadata only after its guards and waiters have ended. */
static void mutex_destroy(uintptr_t raw){CorboMutexState*m=(void*)raw;
 if(m->asynchronous){pthread_mutex_lock(&task_lock);if(m->held||m->head||m->reservation)abort();pthread_mutex_unlock(&task_lock);}
 if(pthread_mutex_trylock(&m->gate))abort();if(pthread_mutex_unlock(&m->gate)||pthread_mutex_destroy(&m->gate))abort();
#ifdef _WIN32
 if(!VirtualFree(m,0,MEM_RELEASE))abort();
#else
 if(munmap(m,sizeof(*m)))abort();
#endif
}
