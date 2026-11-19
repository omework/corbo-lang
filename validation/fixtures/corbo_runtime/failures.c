/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#include <assert.h>
static unsigned cleaned;
static bool failure_poll(Task *task,bool failure){assert(task->failed&&failure);++cleaned;return true;}
static void failure_dispose(TaskState *state,bool completed){assert(state->task.failed&&!completed);++cleaned;}
int main(void){
 corbo_runtime_init(1024*1024,1024*1024,64*1024);
 Task plain={0};task_spawn(&plain,failure_poll);assert(plain.done&&plain.failed&&cleaned==1);
 TaskValue blocked=make_task(sizeof(TaskState),failure_poll);blocked=start_blocking(blocked);assert(blocked.state->task.done&&blocked.state->task.failed&&cleaned==2);discard_handle(blocked);
 TaskValue worker=make_native(sizeof(TaskState),failure_poll,failure_dispose);start_native(worker);assert(worker.state->task.done&&worker.state->task.failed&&cleaned==3);TaskCompletion result=join_task(worker);assert(!result.ok);
 native_drain();task_end();corbo_runtime_shutdown();puts("failure parity passed");
}
