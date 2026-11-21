/** @file vector_owned.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
/** Grows byte storage through the synchronized path, then copies a readable source range into the new tail. */
static inline __attribute__((unused)) void value_region_append(Region*r,const unsigned char*data,size_t n){
if(!n)return;if(n>r->bytes-r->len)region_error();size_t at=r->len;
memory_metric_add(3,(n-1)*r->width);r->len+=n-1;(void)value_region_add(r);memcpy(r->data+at,data,n);}
/** Moves the selected element into out and shifts the remaining tail; out must hold one element and index must be live. */
static inline __attribute__((unused)) void vector_remove(Region*r,uint64_t i,void*out){
if(i>=r->len){fputs("corbo: indice hors du vecteur\n",stderr);exit(EXIT_FAILURE);}
unsigned char*p=r->data+i*r->width;memcpy(out,p,r->width);memory_metric_sub(3,r->width);--r->len;
memmove(p,p+r->width,(r->len-i)*r->width);}
/** Moves the last element into out and shortens the region; returns false without writing when empty. */
static inline __attribute__((unused)) bool vector_pop(Region*r,void*out){
if(!r->len)return false;memory_metric_sub(3,r->width);--r->len;memcpy(out,r->data+r->len*r->width,r->width);return true;}
/** Destroys pooled elements from the last slot to the first, then releases the vector's region. */
static inline __attribute__((unused)) void destroy_owned_region(void*raw){Region*r=raw;Owned*v=(void*)r->data;for(size_t i=r->len;i!=0;--i)put(&v[i-1]);value_region_drop(r);}
