/** @file pools.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
#include <stdatomic.h>
/** Cleanup-callback adapter for a region descriptor; releases its payload through the synchronized region path. */
static inline __attribute__((unused)) void destroy_region(void*raw){value_region_drop(raw);}
/** Reports fixed datastack exhaustion or an invalid storage operation and terminates the process. */
static void storage_error(void){fputs("corbo: limite de la datastack fixe\n",stderr);exit(EXIT_FAILURE);}
/** Allocates a pool descriptor, atomic occupancy bytes and fixed slots on the datastack; validates sizes and arm counts. */
static inline __attribute__((unused)) Pools* new_pool(size_t n,size_t bytes,size_t arms){
if(!n||!arms||n>SIZE_MAX/arms||n*arms>SIZE_MAX/bytes)storage_error();
Pools *p=push(sizeof(Pools),_Alignof(Pools),1);p->cap=n;p->stride=bytes;p->arms=arms;
p->used=push(sizeof(*p->used),_Alignof(_Atomic unsigned char),n*arms);p->data=push(bytes,_Alignof(max_align_t),n*arms);for(size_t i=0;i<n*arms;++i)atomic_init(&p->used[i],0);return p;}
/** Atomically claims and zeroes a slot; full pools return false without mutation. */
static inline __attribute__((unused)) bool pool_try_take(Owned* out,Pools* p,size_t arm){size_t low=arm*p->cap,hi=low+p->cap;
for(size_t i=low;i<hi;++i){unsigned char empty=0;if(!atomic_compare_exchange_strong(&p->used[i],&empty,1))continue;void* slot=p->data+i*p->stride;memset(slot,0,p->stride);*out=(Owned){p,slot,i,NULL};return true;}return false;}
/** Claims a free slot; exhaustion terminates. */
static inline __attribute__((unused)) Owned pool_take(Pools* p,size_t arm){Owned out={0};if(pool_try_take(&out,p,arm))return out;fputs("corbo: pool épuisé\n",stderr);exit(EXIT_FAILURE);}
/** Calls a live allocation's typed cleanup callback before releasing its pool slot, then clears the descriptor's pool link. */
static inline __attribute__((unused)) void put(Owned *v){if(v->pool){if(v->destroy)v->destroy(v->slot);atomic_store(&v->pool->used[v->index],0);v->pool=NULL;}}
/** Cleanup-callback adapter that destroys and releases the Owned descriptor at pointer. */
static inline __attribute__((unused)) void dispose_owned(void*raw){put(raw);}
