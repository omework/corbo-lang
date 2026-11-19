/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#include <assert.h>
static uintptr_t pending[8];static size_t pending_count;static pthread_mutex_t completion_input=PTHREAD_MUTEX_INITIALIZER;static pthread_cond_t completion_input_ready=PTHREAD_COND_INITIALIZER;static int64_t submit_error;
static uintptr_t corbo_completion_create(void){return 1;}
static uintptr_t corbo_completion_next(uintptr_t port){(void)port;pthread_mutex_lock(&completion_input);while(!pending_count)pthread_cond_wait(&completion_input_ready,&completion_input);uintptr_t request=pending[--pending_count];pthread_mutex_unlock(&completion_input);return request;}
static int64_t corbo_completion_attach(uintptr_t port,uint64_t descriptor){return port==1&&descriptor==42?0:-1;}
static int64_t corbo_completion_submit(uintptr_t request){(void)request;return submit_error;}
/* RUNTIME_REACTOR */
static void initialized(void){completion_port=1;completion_init_error=0;}
int main(void){
 corbo_runtime_init(1024*1024,0,64*1024);pthread_once(&completion_once,initialized);assert(corbo_socket_attach(42)==0);
 Task tasks[4]={{0}};uint64_t requests[4][16]={{0}};int64_t result=99;
 for(unsigned i=0;i<4;++i){assert(!corbo_socket_complete(&tasks[i],42,(uintptr_t)requests[i],&result));assert(requests[i][4]==(uintptr_t)&tasks[i]&&requests[i][5]==42);tasks[i].parked=true;}
 pthread_t worker;assert(!pthread_create(&worker,NULL,completion_events,NULL));pthread_detach(worker);
 pthread_mutex_lock(&completion_input);for(unsigned i=0;i<4;++i)pending[pending_count++]=(uintptr_t)requests[i];pthread_cond_signal(&completion_input_ready);pthread_mutex_unlock(&completion_input);
 pthread_mutex_lock(&task_lock);for(;;){bool done=true;for(unsigned i=0;i<4;++i)done=done&&tasks[i].io_ready;if(done)break;pthread_cond_wait(&task_ready,&task_lock);}pthread_mutex_unlock(&task_lock);
 for(unsigned i=0;i<4;++i){assert(requests[i][4]==0&&!tasks[i].waiting&&!tasks[i].parked);assert(corbo_socket_complete(&tasks[i],42,(uintptr_t)requests[i],&result)&&result==0&&!tasks[i].io_registered);}
 Task failure={0};uint64_t rejected[16]={0};submit_error=-8;assert(corbo_socket_complete(&failure,42,(uintptr_t)rejected,&result)&&result==-8&&!failure.waiting&&!failure.io_registered&&rejected[4]==0);
 corbo_runtime_shutdown();puts("completion parity passed");
}
