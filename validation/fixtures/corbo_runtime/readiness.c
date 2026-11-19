/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#include <assert.h>
#include <unistd.h>
static unsigned watched;static uintptr_t token_seen;static int64_t next_error;
static int64_t corbo_queue_create(void){return 1;}
static uintptr_t corbo_queue_wait(int64_t queue){(void)queue;return 0;}
static int64_t corbo_queue_watch(int64_t queue,uint64_t descriptor,unsigned mask,uintptr_t token){(void)queue;(void)descriptor;watched=mask;token_seen=token;int64_t result=next_error;next_error=0;return result;}
/* RUNTIME_REACTOR */
static void initialized(void){socket_queue=1;socket_init_error=0;}
static size_t queued(void){size_t count=0;for(Task *p=task_head;p;p=p->next)++count;return count;}
int main(void){
 corbo_runtime_init(1024*1024,0,64*1024);pthread_once(&socket_once,initialized);
 Task readers[3]={{0}},writer={0};int64_t result=99;
 for(unsigned i=0;i<3;++i){assert(!corbo_socket_wait(&readers[i],12,false,&result));readers[i].parked=true;}
 uintptr_t token=token_seen;assert(token&&watched==1);
 assert(!corbo_socket_wait(&writer,12,true,&result));writer.parked=true;assert(token_seen==token&&watched==3);
 socket_dispatch(token|1);assert(queued()==3&&watched==2&&!writer.io_ready&&writer.waiting);
 for(unsigned i=0;i<3;++i){assert(corbo_socket_wait(&readers[i],12,false,&result)&&result==0&&!readers[i].io_registered);}
 task_head=NULL;task_tail=&task_head;
 socket_dispatch(token|2);assert(queued()==1&&watched==0&&token_seen==0);assert(corbo_socket_wait(&writer,12,true,&result)&&result==0);
 task_head=NULL;task_tail=&task_head;socket_dispatch(token|3);assert(queued()==0);
 Task failed={0};next_error=-9;assert(corbo_socket_wait(&failed,33,false,&result)&&result==-9&&!failed.io_registered&&!failed.waiting);
 Task reader={0};writer=(Task){0};assert(!corbo_socket_wait(&reader,44,false,&result));reader.parked=true;assert(!corbo_socket_wait(&writer,44,true,&result));writer.parked=true;token=writer.io_token;next_error=-7;
 socket_dispatch(token|1);assert(reader.io_ready&&writer.io_ready&&queued()==2);assert(corbo_socket_wait(&reader,44,false,&result)&&result==0);assert(corbo_socket_wait(&writer,44,true,&result)&&result==-7);
 corbo_runtime_shutdown();puts("readiness parity passed");
}
