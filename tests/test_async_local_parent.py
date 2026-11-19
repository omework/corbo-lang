"""Parent placement must preserve identity and release child storage."""
from pathlib import Path
import unittest
from crust import compile_source
from async_runtime import TASK_SELECT_RUNTIME
import test_select_source as sources
import test_suspended_cleanup as cleanup
import test_native_blocks as native_tests

ROOT=Path(__file__).resolve().parents[1]
PREFIX='''struct Point{x:Int}fn make(n:Int)-><-Point{let p=Point{x:n};return <-p;}'''


class AsyncLocalParentTests(unittest.TestCase):
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    run_source=sources.SelectSourceTests.run_source
    refused=sources.SelectSourceTests.refused
    native=cleanup.SuspendedCleanupTests.native
    run_native=native_tests.NativeBlockTests.run_native

    @staticmethod
    def program(body,helpers=''):
        return PREFIX+helpers+'async fn work()->Int{'+body+'''}
            fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''

    def test_recorded_parent_and_successive_transfers(self):
        source=(ROOT/'validation/open-async-local-helper-parent-transfer.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')
        source=self.program('''let r={let middle={let p=make(7);yield;<-p};yield;<-middle};return r.x;''')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

    def test_conditional_results_and_early_return(self):
        for flag in ('true','false'):
            source=self.program('''let r=if FLAG{let temp=make(2);print(temp.x);let p=make(7);yield;<-p}
                else{let temp=make(3);print(temp.x);let p=make(9);yield;<-p};return r.x;'''.replace('FLAG',flag))
            with self.subTest(flag=flag):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'2\n7\n' if flag=='true' else '3\n9\n')
                self.assertEqual(run.stderr.count('destroy p=Point\n'),2)
            source=self.program('let r=if '+flag+'{return 3;}else{let p=make(7);yield;<-p};return r.x;')
            self.assertEqual(self.run_source(source).stdout,'3\n' if flag=='true' else '7\n')

    def test_loop_result_with_continue(self):
        source=self.program('''let mut i=0;let r=loop{let temp=make(2);print(temp.x);
            let p=make(i);yield;i=i+1;if i<3{continue;}break <-p;};return r.x;''')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'2\n2\n2\n2\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),6)

    def test_alias_and_parameter_return_relay(self):
        helpers='fn identity(p:->Point)-><-Point{return <-p;}'
        for body in ('let p=make(7);let moved=<-p;<-moved',
                     'let p=identity(->make(7));yield;<-p'):
            with self.subTest(body=body):
                self.assertEqual(self.run_source(self.program('let r={'+body+'};return r.x;',helpers)).stdout,'7\n')

    def test_match_result_and_branch_assignment(self):
        source=self.program('''let e=runtime::spawn(->child());let value=e.await;
            let r=match value{Ok(n)=>{let p=make(n);yield;<-p},Err(_)=>{let p=make(9);yield;<-p}};
            return r.x;''','async fn child()->Int{yield;return 7;}')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'9\n')
        for flag in ('true','false'):
            source=self.program('let r={let mut p=make(1);print(p.x);if '+flag+
                '{p=<-make(7);}yield;<-p};return r.x;')
            self.assertEqual(self.run_source(source).stdout,'1\n'+('7\n' if flag=='true' else '1\n'))

    def test_replacement_keeps_old_until_new_is_evaluated(self):
        source=self.program('let mut r=make(1);r=<-{let p=make(r.x+6);yield;<-p};return r.x;')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),2)

    def test_existing_parent_receiver_in_child_blocks_and_loops(self):
        source=self.program('let mut r=make(1);print(r.x);{r=<-make(7);yield;}return r.x;')
        self.assertEqual(self.run_source(source).stdout,'1\n7\n')
        source=self.program('''let mut r=make(1);let mut i=0;while i<3{
            print(r.x);r=<-make(r.x+1);yield;i=i+1;if i<3{continue;}break;
            }return r.x;''')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'1\n2\n3\n4\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),4)
        named=(ROOT/'validation/open-async-local-named-parent-replacement.crb').read_text()
        self.assertEqual(self.run_source(named).stdout,'1\n7\n')
        for flag in ('true','false'):
            source=self.program('let mut r=make(1);print(r.x);{let q=make(7);if '+flag+
                '{q ->;r=<-q;}else{q ->;print(q.x);}yield;}return r.x;')
            self.assertEqual(self.run_source(source).stdout,'1\n7\n' if flag=='true' else '1\n7\n1\n')

    def test_copies_do_not_retain_original_child_stack(self):
        for parameter,argument in (('->Point','->p'),('&Point','&p')):
            source=self.program('let q={let p=make(7);let q=duplicate('+argument+');yield;<-q};return q.x;',
                'fn duplicate(p:'+parameter+')-><-Point{let q=copy(p);return <-q;}')
            with self.subTest(parameter=parameter):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'7\n')
                self.assertEqual([row for row in run.stderr.splitlines() if row.startswith('destroy ')],
                                 ['destroy p=Point','destroy q=Point'])
        source=self.program('let q={let p=make(7);let q=p.duplicate();yield;<-q};return q.x;',
            'impl Point{fn duplicate(self:&Point)-><-Point{let q=copy(self);return <-q;}}')
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_two_receivers_choose_the_enclosing_storage(self):
        for flag in ('true','false'):
            source=self.program('''let mut r=make(1);print(r.x);{
                let mut s=make(2);print(s.x);{
                    let q=make(7);if FLAG{q ->;r=<-q;}else{q ->;s=<-q;}
                }print(s.x);
            }return r.x;'''.replace('FLAG',flag))
            with self.subTest(flag=flag):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'1\n2\n2\n7\n' if flag=='true' else '1\n2\n7\n1\n')
                self.assertEqual(run.stderr.count('destroy p=Point\n'),3)

    def test_result_borrow_reserves_value(self):
        source=self.program('let q={let p=make(7);<-p};let view=&q.x;yield;print(*view);drop(->q);return 9;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('print(*view);drop(->q);','drop(->q);print(*view);'),'emprunt|réserv|référenc')

    def test_placement_does_not_relax_moves(self):
        self.refused(self.program('let q={let p=make(7);p};return q.x;'),'structure|transfert|explicite')
        self.refused(self.program('let r={let p=make(7);let q=<-p;print(p.x);<-q};return r.x;'),
                     'consomm|utilis|transfér')
        self.refused(self.program('let r={let p=make(7);let q=identity(p);<-q};return r.x;',
            'fn identity(p:->Point)-><-Point{return <-p;}'),'transfert|explicite')

    def test_field_pool_cannot_be_promoted_with_root(self):
        prefix='''struct Holder{value:A<Int>}fn wrap(n:->A<Int>)-><-Holder{
            let h=Holder{value:<-n};return <-h;}'''
        body='''async fn work()->Int{OUTER let r={INNER let n=p.new(7);let h=wrap(->n);yield;<-h};
            return *r.value;}fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        pool='let mut p=pool<Int>(1);'
        self.assertEqual(self.run_source(prefix+body.replace('OUTER',pool).replace('INNER','')).stdout,'7\n')
        self.refused(prefix+body.replace('OUTER','').replace('INNER',pool),'pool|source|survi')

    def storage_probe(self, source, body):
        code=compile_source(source)
        anchor='static Cell *local_cell_new('
        self.assertEqual(code.count(anchor),1)
        code=code.replace(anchor,'''static Cell *observed_cells[32];
static Source *observed_closed[32];
static int observed_count, observed_close_count;
'''+anchor)
        anchor='if (!cell) fail("data stack capacity exceeded");\n    return cell;'
        self.assertEqual(code.count(anchor),1)
        code=code.replace(anchor,'if (!cell) fail("data stack capacity exceeded");\n    observed_cells[observed_count++]=cell;\n    return cell;')
        anchor='static void source_close(Source *source) {'
        self.assertEqual(code.count(anchor),1)
        code=code.replace(anchor,anchor+'\n    observed_closed[observed_close_count++]=source;')
        extra_select = '' if TASK_SELECT_RUNTIME in code else TASK_SELECT_RUNTIME
        code='#define main original_main\n'+code+'\n#undef main\n'+extra_select
        return self.run_c_oracle(code+'\n#include <assert.h>\nint main(void){crust_task_context_init();'+body+
                                 'crust_task_context_close();return 0;}')

    def test_parent_identity_survives_child_reclamation(self):
        source=self.program('''let q={let temp=make(2);print(temp.x);let p=make(7);yield;<-p};yield;return q.x;''')
        for complete in (False,True):
            ending=('assert(task_poll(task)==TASK_COMPLETE);int answer;assert(task_take(task,&answer));assert(answer==7);'
                    if complete else 'assert(task_owned_discardable(task));assert(task_drop_owned(task));')
            with self.subTest(complete=complete):
                run=self.storage_probe(source,'''
    CrustTask *task=crust_async_work_create();
    assert(task_poll(task)==TASK_SUSPENDED);assert(observed_count==2);
    Cell *result=observed_cells[1];Source *parent=result->source;Source *child=observed_cells[0]->source;
    assert(parent!=child && parent->stack && !parent->pool);
    assert(parent->live==1 && child->live==1 && observed_close_count==0);
    assert(task_poll(task)==TASK_SUSPENDED);
    assert(observed_close_count==1 && observed_closed[0]==child);
    assert(child->used==0 && child->live==0);
    assert(result==observed_cells[1] && result->alive && cell_load_int(result,0)==7);
'''+ending+'''
    assert(observed_close_count==2 && observed_closed[1]==parent);
''')
                self.assertEqual(run.stderr.count('destroy p=Point\n'),2)

    def test_loop_model_reuses_parent_slot(self):
        source=self.program('''let mut i=0;let r=loop{let temp=make(2);print(temp.x);let p=make(i);
            yield;i=i+1;if i<3{continue;}break <-p;};yield;return r.x;''')
        run=self.storage_probe(source,'''
    CrustTask *task=crust_async_work_create();Cell *slot=NULL;Source *parent=NULL;size_t used=0;
    for(int i=0;i<3;++i){
        assert(task_poll(task)==TASK_SUSPENDED);assert(observed_count==2*(i+1));
        Cell *current=observed_cells[2*i+1];
        if(i==0){slot=current;parent=current->source;used=parent->used;}
        assert(current==slot && current->source==parent && parent->used==used && parent->live==1);
        assert(cell_load_int(current,0)==i && observed_close_count==i);
    }
    assert(task_poll(task)==TASK_SUSPENDED);assert(observed_close_count==3);
    assert(slot->alive && cell_load_int(slot,0)==2);
    assert(task_poll(task)==TASK_COMPLETE);int result;assert(task_take(task,&result));assert(result==2);
    assert(observed_close_count==4);
''')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),6)


if __name__=='__main__':unittest.main()
