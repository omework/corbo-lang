"""SL1 internal selection: readiness, retention, cleanup and stable wake routes.

The source-language Select lowering is intentionally not asserted here. The
generated-frame probe supplies its suspended destructor for a capture-only
body, rather than pretending ordinary release handles arbitrary suspensions.
"""
import random
import unittest

from async_runtime import TASK_RUNTIME, TASK_THREAD_RUNTIME, TASK_SELECT_RUNTIME
from crust import compile_source
import test_async_runtime


RUNTIME = TASK_RUNTIME + TASK_THREAD_RUNTIME + TASK_SELECT_RUNTIME
STATES = r'''
#include <assert.h>
typedef struct {
    CrustTask task;
    int id, calls, released, discarded, taken;
    const char *script;
} Branch;
static int poll_mask, release_order;
static CrustTaskStep resume(CrustTask *task) {
    Branch *b = (Branch *)task;
    poll_mask |= 1 << b->id;
    char c = b->script[b->calls++];
    assert(c);
    return c == 'R' ? TASK_STEP_RETURN : c == 'Y' ? TASK_STEP_YIELD : TASK_STEP_PENDING;
}
static void take(CrustTask *task, void *out) {
    Branch *b = (Branch *)task;
    assert(!b->taken++);
    *(int *)out = 10 + b->id;
}
static void release(CrustTask *task) {
    Branch *b = (Branch *)task;
    assert(!b->released++);
    release_order = release_order * 10 + b->id + 1;
}
static void discard(CrustTask *task) {
    Branch *b = (Branch *)task;
    assert(!b->discarded++);
    release(task);
}
static const CrustTaskOps ops = {resume, take, release};
static void branch_init(Branch *b, CrustQueueEntry *entry, int id, const char *script) {
    *b = (Branch){.id=id, .script=script};
    task_init(&b->task, &ops);
    b->task.queue_entry = entry;
}
'''


class SelectRuntimeTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_independent_eligibility_model(self):
        # Abstract events give a branch permission to run its next instruction.
        # A scan consumes permissions in source order, stopping at a result.
        # There are no queue entries, locks, tickets or task states in the model.
        rng = random.Random(8112026)
        scripts = ('PPR', 'YPR', 'PYR')
        rows = []
        for trial in range(80):
            ready, calls, winner = {0, 1, 2}, [0, 0, 0], -1
            operations = [('p', 0)] + [
                ('w', rng.randrange(3)) if rng.randrange(3) else ('p', 0)
                for _ in range(24)]
            operations += [('w', 2), ('w', 1), ('w', 0), ('p', 0)] * 4
            for index, (op, target) in enumerate(operations):
                mask, result = 0, -1
                if op == 'w':
                    result = int(winner == -1)
                    if result:
                        ready.add(target)
                elif winner == -1:
                    for b in range(3):
                        if b not in ready:
                            continue
                        ready.remove(b)
                        mask |= 1 << b
                        instruction = scripts[b][calls[b]]
                        calls[b] += 1
                        if instruction == 'R':
                            winner = b
                            break
                        if instruction == 'Y':
                            ready.add(b)
                    result = 1 if winner != -1 else 0 if ready else 2
                else:
                    result = 1
                rows.append(f"{{{int(index == 0)},{int(index == len(operations)-1)},"
                            f"'{op}',{target},{mask},{result},{winner},"
                            f"{{{','.join(map(str,calls))}}}}}")
            self.assertNotEqual(winner, -1)
        self.assertEqual(len(rows), 3280)
        code = RUNTIME + STATES + r'''
struct Row { int init, end; char op; int target, mask, result, winner, calls[3]; };
static const struct Row rows[] = {ROWS};
int main(void) {
    CrustQueueEntry entries[3]; Branch b[3]; CrustSelectBranch members[3];
    CrustSelect selection; CrustTask parent;
    task_init(&parent, &ops);
    for (int i=0; i<3; ++i) task_queue_entry_init(&entries[i]);
    const char *scripts[] = {"PPR", "YPR", "PYR"};
    for (size_t row=0; row<sizeof(rows)/sizeof(*rows); ++row) {
        const struct Row *r=&rows[row];
        if (r->init) {
            release_order=0;
            for (int i=0; i<3; ++i) {
                branch_init(&b[i], &entries[i], i, scripts[i]);
                members[i]=(CrustSelectBranch){&b[i].task, discard};
            }
            task_select_init(&selection, members, 3);
        }
        poll_mask=0;
        int result = r->op=='p' ? (int)task_select_poll(&selection, &parent)
            : task_queue_wake(b[r->target].task.wake_target);
        assert(result==r->result && poll_mask==r->mask);
        assert(selection.winner==(r->winner<0 ? SIZE_MAX : (size_t)r->winner));
        for (int i=0; i<3; ++i) assert(b[i].calls==r->calls[i] && !b[i].released);
        if (r->end) {
            int value=-1;
            assert(task_select_take(&selection, &value) && value==10+r->winner);
            assert(!task_select_take(&selection, &value));
            for (int i=0; i<3; ++i) assert(b[i].released==(i==r->winner));
            task_select_drop(&selection);
            for (int i=0; i<3; ++i) assert(b[i].released==1);
        }
    }
    for (int i=0; i<3; ++i) task_queue_entry_destroy(&entries[i]);
    return 0;
}
'''
        self.run_c_oracle(code.replace('ROWS', ',\n'.join(rows)))

    def test_cleanup_inactive_pending_completed_and_taken(self):
        self.run_c_oracle(RUNTIME + STATES + r'''
int main(void) {
    CrustQueueEntry entries[3]; CrustTask parent;
    task_init(&parent, &ops);
    for (int i=0; i<3; ++i) task_queue_entry_init(&entries[i]);
    for (int phase=0; phase<4; ++phase) {
        Branch b[3]; CrustSelectBranch members[3]; CrustSelect selection;
        for (int i=0; i<3; ++i) {
            branch_init(&b[i], &entries[i], i, phase==1 ? "P" : i==1 ? "R" : "Y");
            members[i]=(CrustSelectBranch){&b[i].task, discard};
        }
        task_select_init(&selection, members, 3);
        release_order=0;
        if (phase) assert(task_select_poll(&selection, &parent)==
                          (phase==1 ? TASK_STEP_PENDING : TASK_STEP_RETURN));
        if (phase==3) {
            int out=-1;
            assert(task_select_take(&selection, &out) && out==11);
            assert(!b[0].released && !b[2].released);
        }
        task_select_drop(&selection);
        assert(release_order==(phase==3 ? 231 : 321));
        for (int i=0; i<3; ++i) {
            assert(b[i].released==1);
            assert(b[i].discarded==(phase==1 || (phase>=2 && i==0)));
            assert(b[i].calls==(phase==0 || (phase>=2 && i==2) ? 0 : 1));
            assert(!task_queue_wake(b[i].task.wake_target));
        }
    }
    for (int i=0; i<3; ++i) task_queue_entry_destroy(&entries[i]);
    return 0;
}
''')

    def test_branch_wake_during_poll_survives_and_routes_to_parent(self):
        self.run_c_oracle(RUNTIME + STATES + r'''
static _Atomic int entered, proceed;
static CrustTaskStep delayed(CrustTask *task) {
    Branch *b=(Branch *)task;
    if (!b->calls++) {
        atomic_store(&entered, 1);
        while (!atomic_load(&proceed)) sched_yield();
        return TASK_STEP_PENDING;
    }
    assert(b->calls==2);
    return TASK_STEP_RETURN;
}
static const CrustTaskOps delayed_ops={delayed, take, release};
typedef struct { CrustTask task; CrustSelect selection; int result, calls, releases; } Root;
static CrustTaskStep root_resume(CrustTask *task) {
    Root *r=(Root *)task; ++r->calls;
    CrustTaskStep step=task_select_poll(&r->selection, task);
    if (step==TASK_STEP_RETURN) assert(task_select_take(&r->selection, &r->result));
    return step;
}
static void root_take(CrustTask *task, void *out) { *(int *)out=((Root *)task)->result; }
static void root_release(CrustTask *task) {
    Root *r=(Root *)task; assert(!r->releases++); task_select_drop(&r->selection);
}
static const CrustTaskOps root_ops={root_resume, root_take, root_release};
int main(void) {
    for (int round=0; round<24; ++round) {
        release_order=0;
        CrustReadyQueue queue; CrustQueueEntry entries[3]; CrustWakeTicket ticket;
        assert(!task_queue_init(&queue));
        for (int i=0; i<3; ++i) task_queue_entry_init(&entries[i]);
        Branch b[2]; CrustSelectBranch members[2]; Root root={0};
        for (int i=0; i<2; ++i) {
            branch_init(&b[i], &entries[i], i, "PR");
            members[i]=(CrustSelectBranch){&b[i].task, discard};
        }
        b[0].task.ops=&delayed_ops;
        task_init(&root.task, &root_ops);
        task_select_init(&root.selection, members, 2);
        atomic_store(&entered, 0); atomic_store(&proceed, 0);
        assert(!task_queue_submit(&queue, &entries[2], &root.task, &ticket));
        pthread_t workers[3];
        for (int i=0; i<3; ++i) assert(!pthread_create(&workers[i], NULL, task_queue_worker, &queue));
        while (!atomic_load(&entered)) sched_yield();
        CrustWakeTicket old=b[0].task.wake_target;
        for (int i=0; i<64; ++i) assert(task_queue_wake(old));
        atomic_store(&proceed, 1);
        while (!atomic_load(&root.task.worker_done)) sched_yield();
        assert(root.calls==2 && b[0].calls==2 && b[1].calls==1);
        assert(!b[1].released); /* Pending loser is still owned after selection. */
        int out=-1; assert(task_take(&root.task, &out) && out==10);
        assert(b[0].released==1 && b[1].discarded==1);
        assert(!task_queue_wake(old));
        assert(!task_queue_close(&queue));
        for (int i=0; i<3; ++i) assert(!pthread_join(workers[i], NULL));
        for (int i=0; i<3; ++i) task_queue_entry_destroy(&entries[i]);
        task_queue_destroy(&queue);
    }
    return 0;
}
''')

    def test_nested_routes_wake_only_the_selected_chain(self):
        self.run_c_oracle(RUNTIME + STATES + r'''
typedef struct { CrustTask task; CrustSelect selection; int result, calls; } Group;
static CrustTaskStep group_resume(CrustTask *task) {
    Group *g=(Group *)task; ++g->calls;
    CrustTaskStep step=task_select_poll(&g->selection, task);
    if (step==TASK_STEP_RETURN) assert(task_select_take(&g->selection, &g->result));
    return step;
}
static void group_take(CrustTask *task, void *out) { *(int *)out=((Group *)task)->result; }
static void group_release(CrustTask *task) { task_select_drop(&((Group *)task)->selection); }
static const CrustTaskOps group_ops={group_resume, group_take, group_release};
int main(void) {
    CrustReadyQueue queue; CrustQueueEntry entries[5]; CrustWakeTicket ticket;
    assert(!task_queue_init(&queue));
    for (int i=0; i<5; ++i) task_queue_entry_init(&entries[i]);
    Branch b[3];
    for (int i=0; i<3; ++i) branch_init(&b[i], &entries[i], i, "PR");
    Group inner={0}, outer={0};
    task_init(&inner.task, &group_ops); inner.task.queue_entry=&entries[3];
    task_init(&outer.task, &group_ops);
    CrustSelectBranch inside[]={{&b[0].task, discard},{&b[1].task, discard}};
    CrustSelectBranch outside[]={{&inner.task, group_release},{&b[2].task, discard}};
    task_select_init(&inner.selection, inside, 2);
    task_select_init(&outer.selection, outside, 2);
    assert(!task_queue_submit(&queue, &entries[4], &outer.task, &ticket));
    assert(task_queue_run_one(&queue, 0) && !task_queue_run_one(&queue, 0));
    assert(inner.calls==1 && outer.calls==1);
    /* Wake right then left: source order still makes left win. */
    assert(task_queue_wake(b[1].task.wake_target));
    assert(task_queue_wake(b[0].task.wake_target));
    assert(task_queue_run_one(&queue, 0) && !task_queue_run_one(&queue, 0));
    assert(inner.calls==2 && outer.calls==2);
    assert(b[0].calls==2 && b[1].calls==1 && b[2].calls==1);
    assert(b[0].released==1 && b[1].released==1 && !b[2].released);
    int out=-1; assert(task_take(&outer.task, &out) && out==10);
    assert(b[2].discarded==1);
    for (int i=0; i<3; ++i) assert(!task_queue_wake(b[i].task.wake_target));
    assert(!task_queue_close(&queue));
    for (int i=0; i<5; ++i) task_queue_entry_destroy(&entries[i]);
    task_queue_destroy(&queue);
    return 0;
}
''')

    def test_concurrent_old_tickets_after_free_and_entry_reuse(self):
        self.run_c_oracle(RUNTIME + STATES + r'''
static _Atomic int stage, late;
static CrustWakeTicket old_tickets[2];
static int freed;
static void release_free(CrustTask *task) { ++freed; free(task); }
static const CrustTaskOps free_ops={resume, take, release_free};
static void *producer(void *unused) {
    (void)unused;
    while (!atomic_load(&stage)) {
        task_queue_wake(old_tickets[0]);
        task_queue_wake(old_tickets[1]);
    }
    for (int i=0; i<5000; ++i) {
        assert(!task_queue_wake(old_tickets[0]));
        assert(!task_queue_wake(old_tickets[1]));
    }
    atomic_store(&late, 1);
    return NULL;
}
int main(void) {
    CrustQueueEntry entries[3];
    for (int i=0; i<3; ++i) task_queue_entry_init(&entries[i]);
    for (int round=0; round<16; ++round) {
        Branch *parent=calloc(1, sizeof(*parent)); assert(parent);
        branch_init(parent, &entries[2], 2, "P");
        assert(!task_external_register(&parent->task));
        CrustSelectBranch members[2]; CrustSelect selection;
        for (int i=0; i<2; ++i) {
            Branch *b=calloc(1, sizeof(*b)); assert(b);
            branch_init(b, &entries[i], i, "P"); b->task.ops=&free_ops;
            members[i]=(CrustSelectBranch){&b->task, release_free};
        }
        task_select_init(&selection, members, 2);
        assert(task_select_poll(&selection, &parent->task)==TASK_STEP_PENDING);
        for (int i=0; i<2; ++i) old_tickets[i]=members[i].task->wake_target;
        atomic_store(&stage, 0); atomic_store(&late, 0);
        pthread_t event; assert(!pthread_create(&event, NULL, producer, NULL));
        /* Producer only retains tickets. It can race with detach, destruction
           and replacement at exactly the same persistent entry addresses. */
        task_select_drop(&selection);
        task_external_forget(&parent->task); free(parent);
        Branch replacement[3];
        for (int i=0; i<3; ++i) {
            branch_init(&replacement[i], &entries[i], i, "PR");
            assert(!task_external_register(&replacement[i].task));
            assert(task_poll(&replacement[i].task)==TASK_SUSPENDED);
        }
        atomic_store(&stage, 1);
        while (!atomic_load(&late)) sched_yield();
        assert(!pthread_join(event, NULL));
        for (int i=0; i<3; ++i) {
            assert(task_poll(&replacement[i].task)==TASK_SUSPENDED);
            assert(replacement[i].calls==1); /* An old wake did not revive it. */
            task_external_forget(&replacement[i].task);
        }
    }
    assert(freed==32);
    for (int i=0; i<3; ++i) task_queue_entry_destroy(&entries[i]);
    return 0;
}
''')

    def test_handle_completion_notifies_its_branch_and_enclosing_poll(self):
        self.run_c_oracle(RUNTIME + STATES + r'''
typedef struct { CrustTask task; CrustTask *child; int result, calls, released; } Waiting;
static CrustTaskStep waiting_resume(CrustTask *task) {
    Waiting *w=(Waiting *)task; ++w->calls;
    if (!atomic_load(&w->child->worker_done)) return task_subscribe(w->child, task);
    assert(task_take(w->child, &w->result)); w->child=NULL;
    return TASK_STEP_RETURN;
}
static void waiting_take(CrustTask *task, void *out) { *(int *)out=((Waiting *)task)->result; }
static void waiting_release(CrustTask *task) {
    Waiting *w=(Waiting *)task;
    assert(!w->child && !w->released++);
}
static const CrustTaskOps waiting_ops={waiting_resume,waiting_take,waiting_release};
typedef struct { CrustTask task; CrustSelect selection; int result, calls; } Root;
static CrustTaskStep root_resume(CrustTask *task) {
    Root *r=(Root *)task; ++r->calls;
    CrustTaskStep step=task_select_poll(&r->selection, task);
    if (step==TASK_STEP_RETURN) assert(task_select_take(&r->selection, &r->result));
    return step;
}
static void root_take(CrustTask *task, void *out) { *(int *)out=((Root *)task)->result; }
static void root_release(CrustTask *task) { task_select_drop(&((Root *)task)->selection); }
static const CrustTaskOps root_ops={root_resume,root_take,root_release};
int main(void) {
    CrustReadyQueue queue; CrustQueueEntry entries[4]; CrustWakeTicket ticket;
    assert(!task_queue_init(&queue));
    for (int i=0;i<4;++i) task_queue_entry_init(&entries[i]);
    Branch child, loser; branch_init(&child,&entries[0],0,"R");
    branch_init(&loser,&entries[1],1,"P");
    Waiting waiting={.child=&child.task}; task_init(&waiting.task,&waiting_ops);
    waiting.task.queue_entry=&entries[2];
    Root root={0}; task_init(&root.task,&root_ops);
    CrustSelectBranch members[]={{&waiting.task,waiting_release},{&loser.task,discard}};
    task_select_init(&root.selection,members,2);
    assert(!task_queue_submit(&queue,&entries[3],&root.task,&ticket));
    assert(!task_queue_submit(&queue,&entries[0],&child.task,&ticket));
    assert(task_queue_run_one(&queue,0)); /* selection subscribes and sleeps */
    assert(root.calls==1 && waiting.calls==1 && loser.calls==1);
    assert(task_queue_run_one(&queue,0)); /* child completion routes a wake */
    assert(task_queue_run_one(&queue,0)); /* only the waiting branch resumes */
    assert(!task_queue_run_one(&queue,0));
    assert(root.calls==2 && waiting.calls==2 && loser.calls==1);
    assert(waiting.released==1 && child.released==1 && !loser.released);
    int out=-1; assert(task_take(&root.task,&out) && out==10);
    assert(loser.discarded==1);
    assert(!task_queue_close(&queue));
    for (int i=0;i<4;++i) task_queue_entry_destroy(&entries[i]);
    task_queue_destroy(&queue); return 0;
}
''')

    def test_generated_captures_retained_and_winner_allocation_extracted(self):
        source = '''async fn left(n:-> Int)-><- Int {yield;return <- n;}
            async fn right(n:-> Int)-><- Int {return <- n;}
            fn main(){let mut memory=pool<Int>(2);let a=memory.new(7);let b=memory.new(9);
                let one=runtime::spawn(->left(->a));let two=runtime::spawn(->right(->b));
                match one.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                match two.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        code = '#define main original_main\n' + compile_source(source) + '\n#undef main\n'
        code += TASK_SELECT_RUNTIME + r'''
#include <assert.h>
/* For these capture-only bodies, the suspended cleanup equals the inactive
   cleanup. This adapter is not claimed to work for a general generated body. */
static void suspended_capture(CrustTask *task) { task->ops->release(task); }
int main(void) {
    crust_task_context_init(); Source pool=source_pool(2);
    CrustTask parent; task_init(&parent, &crust_async_left_ops);
    for (int round=0; round<8; ++round) {
        Cell *a=cell_new(&pool, 7, "left"), *b=cell_new(&pool, 9, "right");
        CrustTask *left=crust_async_left_create(a), *right=crust_async_right_create(b);
        CrustSelectBranch branches[]={{left,suspended_capture},{right,suspended_capture}};
        CrustSelect selection; task_select_init(&selection, branches, 2);
        assert(task_select_poll(&selection, &parent)==TASK_STEP_RETURN && selection.winner==1);
        assert(!cell_try_new(&pool, 0, "premature"));
        CrustWakeTicket old=left->wake_target;
        Cell *out=NULL; assert(task_select_take(&selection, &out) && out==b && out->value==9);
        assert(!cell_try_new(&pool, 0, "premature"));
        task_select_drop(&selection); /* Only left's allocation is released. */
        Cell *reused=cell_new(&pool, 8, "reused"); assert(reused==a);
        assert(!cell_try_new(&pool, 0, "premature"));
        assert(out->value==9);
        cell_drop(reused); cell_drop(out);
        CrustTask *next=crust_async_left_create(cell_new(&pool, 7, "next"));
        assert(next==left && !task_queue_wake(old));
        assert(task_drop_inactive(next));
    }
    source_close(&pool); crust_task_context_close(); return 0;
}
'''
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '')
        self.assertEqual(run.stderr.count('destroy left=7'), 8)
        self.assertEqual(run.stderr.count('destroy right=9'), 8)
        self.assertEqual(run.stderr.count('destroy reused=8'), 8)
        self.assertEqual(run.stderr.count('destroy next=7'), 8)


if __name__ == '__main__':
    unittest.main()
