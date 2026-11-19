/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#include <assert.h>
static _Atomic unsigned completed,dropped,inactive,failed;
typedef struct {TaskState header;unsigned remaining;} Example;
static bool poll_example(Task *raw,bool failure){
 Example *state=(void*)raw;
 if(failure){atomic_fetch_add(&failed,1);return true;}
 if(state->remaining){--state->remaining;return false;}
 state->header.value.k2=42;atomic_fetch_add(&completed,1);return true;
}
static void dispose_example(TaskState *state,bool done){(void)state;atomic_fetch_add(done?&dropped:&inactive,1);}
int main(void){
 corbo_runtime_init(8*1024*1024,8*1024*1024,64*1024);
 TaskValue cold=make_task(sizeof(Example),poll_example);cold.state->dispose=dispose_example;discard_future(cold);assert(inactive==1);
 TaskValue tasks[12];for(unsigned i=0;i<12;++i){tasks[i]=make_task(sizeof(Example),poll_example);tasks[i].state->dispose=dispose_example;((Example*)tasks[i].state)->remaining=i%4;tasks[i]=start_task(tasks[i]);}
 for(unsigned i=0;i<12;++i){TaskCompletion result=join_task(tasks[i]);assert(result.ok&&result.value.k2==42);}
 assert(completed==12&&dropped==0);
 TaskValue abandoned=make_task(sizeof(Example),poll_example);abandoned.state->dispose=dispose_example;abandoned=start_task(abandoned);discard_handle(abandoned);
 TaskValue blocking=make_task(sizeof(Example),poll_example);blocking.state->dispose=dispose_example;((Example*)blocking.state)->remaining=2;blocking=start_blocking(blocking);TaskCompletion b=join_task(blocking);assert(b.ok&&b.value.k2==42);
 TaskValue worker=make_native(sizeof(Example),poll_example,dispose_example);start_native(worker);TaskCompletion n=join_task(worker);assert(n.ok&&n.value.k2==42);
 worker=make_native(sizeof(Example),poll_example,dispose_example);start_native(worker);discard_handle(worker);
 native_drain();task_end();assert(completed==16&&dropped==2&&inactive==1&&failed==0);
 corbo_runtime_shutdown();puts("task parity passed");
}
