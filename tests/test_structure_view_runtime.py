"""Internal representation only; source-level substructure loans remain pending."""
import unittest
from crust import compile_source, verify_program
from structure_views import ContainedLayout
from async_runtime import TASK_RUNTIME_BODY
import test_async_runtime as native

LAYOUTS = r'''
#include <assert.h>
static const size_t point_offsets[]={0,sizeof(int)};
static const unsigned char point_kinds[]={0,0};
static const Source point={.enum_name="Point",.arm_name="",.field_count=2,
    .field_offsets=point_offsets,.field_kinds=point_kinds};
static const Source outer={.enum_name="Outer",.arm_name="",.field_count=4};
static CrustStructureView right(Cell *root) {
    CrustStructureView all=structure_view(root,0,4*sizeof(int),&outer);
    return structure_subview(all,2*sizeof(int),2*sizeof(int),&point);
}
static CrustStructureView relay(Cell *root) { return right(root); }
'''


class StructureViewRuntimeTests(unittest.TestCase):
    run_c_oracle = native.AsyncRuntimeTests.run_c_oracle

    def code(self, body, extra=''):
        return compile_source('fn main(){}').replace('int main(void)', 'int crust_unused_main(void)') + extra + LAYOUTS + body

    def test_compiler_preserves_nominal_contained_paths(self):
        checker = verify_program('''struct Point{x:Int,y:Int}struct Segment{start:Point,end:Point}
            struct Path{code:Int,line:Segment}fn main(){}''')
        self.assertEqual(checker.inline_structures['Path'], (
            ContainedLayout('line','Segment',1,4),
            ContainedLayout('line.start','Point',1,2),
            ContainedLayout('line.end','Point',3,2)))
        self.assertEqual(checker.enums['Path'][''],
                         [('code','Int'),('line.start.x','Int'),('line.start.y','Int'),
                          ('line.end.x','Int'),('line.end.y','Int')])

    def test_returned_descriptor_mutates_one_slot_and_reuses_it(self):
        run = self.run_c_oracle(self.code(r'''
int main(void) {
    Source slots=source_pool_layout(1,4*sizeof(int));
    Cell *root=cell_new(&slots,0,"root");root->layout=&outer;
    for(int i=0;i<4;++i) cell_store_int(root,i*sizeof(int),i+1);
    CrustStructureView first=structure_view(root,0,2*sizeof(int),&point);
    CrustStructureView second=relay(root);
    assert(first.root==second.root && slots.live==1);
    assert(structure_view_address(second,0,sizeof(int))==(unsigned char *)root->fields+2*sizeof(int));
    structure_view_store_int(second,0,9);
    assert(structure_view_load_int(first,0)==1 && cell_load_int(root,2*sizeof(int))==9);
    assert(structure_view_load_int(second,sizeof(int))==4);
    cell_drop(root);assert(slots.live==0 && slots.used==0);
    Cell *again=cell_new(&slots,0,"again");assert(again==root);
    cell_store_int(again,2*sizeof(int),20);
    CrustStructureView fresh=relay(again);assert(structure_view_load_int(fresh,0)==20);
    cell_drop(again);source_close(&slots);
}
'''))
        self.assertEqual(run.stderr.count('destroy root=Outer\n'), 1)
        self.assertEqual(run.stderr.count('destroy '), 2)

    def test_shared_reference_payload_is_not_cloned_or_destroyed(self):
        self.run_c_oracle(self.code(r'''
int main(void) {
    Source ints=source_pool(1), stack=source_stack(4096);
    Cell *target=cell_new(&ints,7,"target");
    const size_t offsets[]={sizeof(int)};
    const unsigned char kinds[]={1};
    Source layout={.enum_name="Carrier",.arm_name="",.field_count=1,
        .field_offsets=offsets,.field_kinds=kinds};
    Cell *root=local_cell_new(&stack,&layout,sizeof(int)+sizeof(Cell *),"carrier");
    cell_store_int(root,0,3);cell_store_ref(root,sizeof(int),target);
    CrustStructureView view=structure_view(root,sizeof(int),sizeof(Cell *),&layout);
    assert(structure_view_load_ref(view,0)==target);
    structure_view_store_ref(view,0,target);
    cell_drop(root);assert(target->alive && ints.live==1 && stack.live==0);
    cell_drop(target);source_close(&stack);source_close(&ints);
}
'''))

    def test_view_in_task_state_survives_suspend_and_thread_change(self):
        self.run_c_oracle(self.code(r'''
#include <pthread.h>
typedef struct { CrustTask task;CrustStructureView view;int phase; } Frame;
static CrustTaskStep resume(CrustTask *task) {
    Frame *frame=(Frame *)task;
    if(!frame->phase++) return TASK_STEP_YIELD;
    structure_view_store_int(frame->view,0,21);
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task,void *out) {
    *(int *)out=structure_view_load_int(((Frame *)task)->view,0);
}
static void release(CrustTask *task) {(void)task;}
static const CrustTaskOps ops={resume,take,release};
static void *continue_task(void *task) {assert(task_poll(task)==TASK_COMPLETE);return NULL;}
int main(void) {
    Source slots=source_pool_layout(1,4*sizeof(int));
    Cell *root=cell_new(&slots,0,"root");root->layout=&outer;
    cell_store_int(root,2*sizeof(int),7);
    Frame frame={.view=relay(root)};task_init(&frame.task,&ops);
    assert(task_poll(&frame.task)==TASK_SUSPENDED);
    assert(slots.live==1 && structure_view_load_int(frame.view,0)==7);
    pthread_t thread;assert(!pthread_create(&thread,NULL,continue_task,&frame.task));
    assert(!pthread_join(thread,NULL));
    int answer=0;assert(task_take(&frame.task,&answer));assert(answer==21);
    assert(root->alive && cell_load_int(root,2*sizeof(int))==21);
    cell_drop(root);source_close(&slots);
}
''', TASK_RUNTIME_BODY))

    def test_internal_boundaries_are_checked_before_access(self):
        for operation, diagnostic in (
            ('structure_view(root,SIZE_MAX,1,&point);','outside allocation'),
            ('structure_subview(view,sizeof(int),2*sizeof(int),&point);','outside parent'),
            ('structure_view_load_int(view,2*sizeof(int));','outside view'),
        ):
            with self.subTest(operation=operation):
                self.run_c_oracle(self.code('''int main(void){
                    Source slots=source_pool_layout(1,4*sizeof(int));
                    Cell *root=cell_new(&slots,0,"root");
                    CrustStructureView view=structure_view(root,0,2*sizeof(int),&point);
                    (void)view;OP return 0;}'''.replace('OP',operation)), diagnostic)


if __name__ == '__main__':
    unittest.main()
