/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#include <assert.h>
static unsigned destroyed;
static void dispose_integer(void *pointer){assert(*(uint64_t*)pointer==42);++destroyed;}
static void dispose_allocation(void *pointer){put(pointer);}
int main(void){
 corbo_runtime_init(8*1024*1024,4*1024*1024,64*1024);
 CorboStackMark origin=corbo_datastack_mark();
 assert(corbo_runtime_abi_version()==1);
 assert(numeric('+',20,22)==42&&numeric('-',50,8)==42&&numeric('*',-6,-7)==42);
 assert(numeric('/',-85,-2)==42&&numeric('%',LLONG_MIN,-1)==0);
 int used[3]={0};assert(take(used,3)==0&&take(used,3)==1);used[0]=0;assert(take(used,3)==0);
 CorboPool *pool=corbo_pool_create(4,sizeof(uint64_t),2);
 Owned values[8];for(size_t arm=0;arm<2;++arm)for(size_t i=0;i<4;++i){values[arm*4+i]=corbo_pool_take(pool,arm);assert(values[arm*4+i].index==arm*4+i);}
 *(uint64_t*)values[2].slot=42;values[2].destroy=dispose_integer;
 void *slot=values[2].slot;put(&values[2]);put(&values[2]);assert(destroyed==1);
 values[2]=pool_take(pool,0);assert(values[2].slot==slot&&*(uint64_t*)slot==0);
 for(size_t i=0;i<8;++i)put(&values[i]);
 CorboStackMark before_regions=corbo_datastack_mark();
 region_enter(64*1024,3,3);Region first,second,third,reused;
 region_new(&first,sizeof(uint64_t),0,0);region_new(&second,1,0,0);region_new(&third,8,0,0);
 region_push(&first,11);region_append(&second,(const unsigned char*)"abc",3);region_push(&third,33);
 void *hole=second.data;region_drop(&second);region_new(&reused,1,0,0);assert(reused.data==hole);
 region_append(&reused,(const unsigned char*)"xy",2);assert(region_read(&reused,1)=='y');region_drop(&reused);
 corbo_datastack_rewind(before_regions);assert(first.band->closed&&third.band->closed);
 assert(region_read(&first,0)==11&&region_read(&third,0)==33);region_drop(&first);region_drop(&third);
 Region vector;region_new(&vector,8,0,1);for(int i=0;i<8;++i)region_push(&vector,i);
 uint64_t removed=99;vector_remove(&vector,3,&removed);assert(removed==3&&vector.len==7&&region_read(&vector,3)==4);
 assert(vector_pop(&vector,&removed)&&removed==7);while(vector_pop(&vector,&removed)){}assert(!vector_pop(&vector,&removed));region_drop(&vector);
 Region rows;region_new(&rows,16,0,1);long long row[2]={10,20};region_push_row(&rows,row);assert(region_read_row(&rows,0,1)==20);region_drop(&rows);
 Region children,child;int live=1;region_new(&children,8,1,1);region_new(&child,1,0,1);region_push_owned(&children,&child,&live);region_drop(&children);assert(live==0);
 RegionalMap *map=map_new(sizeof(uint64_t),NULL);uint64_t previous=0;
 for(uint64_t key=0;key<120;++key){uint64_t value=key*3;assert(!map_insert(map,key,&value,&previous));}
 void *stable=map_get(map,77);assert(stable&&*(uint64_t*)stable==231);
 for(uint64_t key=0;key<120;key+=2)assert(map_remove(map,key,&previous)&&previous==key*3);
 for(uint64_t key=200;key<260;++key){uint64_t value=key;assert(!map_insert(map,key,&value,&previous));}
 assert(map_get(map,77)==stable);uint64_t replacement=1000;assert(map_insert(map,77,&replacement,&previous)&&previous==231);
 assert(map_remove(map,77,&previous)&&previous==1000&&!map_remove(map,77,&previous));map_drop(&map);assert(!map);
 map=map_new(sizeof(Owned),dispose_allocation);Owned owned=pool_take(pool,0);*(uint64_t*)owned.slot=42;owned.destroy=dispose_integer;
 Owned old={0};assert(!map_insert(map,1,&owned,&old));map_drop(&map);assert(destroyed==2);
 CorboStackMark before_classic=corbo_datastack_mark();ClassicStack saved=swap_classic((ClassicStack){0});reserve(65536);
 *(uint64_t*)push(8,8,1)=123;ClassicStack nested=swap_classic(saved);assert(nested.base!=base&&cursor==before_classic.position);
 saved=swap_classic(nested);release();(void)swap_classic(saved);
 corbo_datastack_rewind(origin);assert(cursor==origin.position);(void)push(1,1,page_size*3);assert(committed>=page_size*3);
 corbo_datastack_rewind(origin);corbo_free_pages();assert(committed==0);*(uint64_t*)push(8,8,1)=987;assert(committed==page_size);
 corbo_runtime_shutdown();assert(destroyed==2);puts("memory parity passed");
}
