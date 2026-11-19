"""Caller data-stack storage for fresh synchronous results used in async."""
from pathlib import Path
import unittest
from crust import verify_program,compile_source
import test_select_source as sources
import test_suspended_cleanup as cleanup

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-local-owned-struct-helper.crb').read_text()
POINT='''struct Point{x:Int}
    fn make(n:Int)-><-Point{let p=Point{x:n};return <-p;}
    fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''


class AsyncLocalStructHelperTests(unittest.TestCase):
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    run_source=sources.SelectSourceTests.run_source
    refused=sources.SelectSourceTests.refused
    native=cleanup.SuspendedCleanupTests.native

    @staticmethod
    def program(body,helpers=''):
        return helpers+POINT.replace('fn main()', 'async fn work()->Int{'+body+'}fn main()')

    def test_recorded_owned_child_and_suspension(self):
        for pause in ('','yield;'):
            with self.subTest(pause=pause):
                run=self.run_source(BASE.replace('let result = *h.value;',pause+'let result = *h.value;'))
                self.assertEqual(run.stdout,'7\n')
                self.assertEqual(run.stderr.count('destroy n=7\n'),1)
                self.assertEqual(run.stderr.count('destroy h=Holder\n'),1)
                self.assertLess(run.stderr.index('destroy n='),run.stderr.index('destroy h='))

    def test_copy_owned_and_borrowed_local_values(self):
        for parameter,argument in (('->Point','->p'),('&Point','&p')):
            source=self.program('let p=make(7);let q=duplicate('+argument+');yield;return q.x;',
                'fn duplicate(p:'+parameter+')-><-Point{let q=copy(p);return <-q;}')
            with self.subTest(parameter=parameter):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'7\n')
                self.assertEqual(run.stderr.count('destroy p=Point\n'),1)
                self.assertEqual(run.stderr.count('destroy q=Point\n'),1)
                self.assertNotIn('destroy q=0',run.stderr)

    def test_copy_helpers_declare_pool_and_local_returns(self):
        source=self.program('''let p=make(7);let a=duplicate(->p);print(a.x);
            let b=duplicate_pool(->q);
            print(b.x);drop(->a);drop(->b);return 11;''',
            'fn duplicate(p:->Point)-><-Point{let q=copy(p);return <-q;}'
            'fn duplicate_pool(p:->A<Point>)-><-A<Point>{let q=copy(p);return <-q;}')
        # The pool input and its copy coexist during RHS evaluation.
        source=source.replace('work()->Int','work(q:->Point)->Int').replace(
            'let h=runtime::spawn(->work());',
            'let mut points=pool<Point>(2);let q=points.new(x:9);let h=runtime::spawn(->work(->q));')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n11\n')

    def test_multiple_live_results_and_replacement(self):
        source=self.program('''let mut p=make(7);let q=make(8);yield;
            p=<-make(q.x);print(p.x);print(q.x);return 9;''')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'8\n8\n9\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),3)

    def test_branches_loops_and_early_return(self):
        for count in (0,1,3):
            source=self.program('''let mut i=0;while i<COUNT{
                let p=make(i);yield;print(p.x);i=i+1;
                if i==2{continue;}if i==3{break;}
            }return i;'''.replace('COUNT',str(count)))
            with self.subTest(count=count):
                run=self.run_source(source)
                self.assertEqual(run.stdout,''.join(f'{i}\n' for i in range(count))+f'{count}\n')
                self.assertEqual(run.stderr.count('destroy p=Point\n'),count)
        self.assertEqual(self.run_source(self.program('if true{let p=make(7);yield;return p.x;}return 0;')).stdout,'7\n')

    def test_borrow_and_drop_follow_last_use(self):
        source=self.program('let p=make(7);let v=&p.x;yield;print(*v);drop(->p);return 9;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('print(*v);drop(->p);','drop(->p);print(*v);'),'emprunt|réserv|référenc')
        self.refused(source.replace('drop(->p);return 9;','drop(->p);return p.x;'),'consomm|utilis|transfér')

    def test_local_value_is_not_a_pool_allocation(self):
        source=self.program('let p=make(7);return consume(->p);',
            'fn consume(p:->A<Point>)->Int{return p.x;}')
        self.refused(source,'locale|A<T>|allocation')
        typed=self.program('let p:Point=make(7);return p.x;')
        self.assertEqual(self.run_source(typed).stdout,'7\n')
        self.refused(typed.replace('p:Point','p:A<Point>'),'annotation|locale|allocation')

    def test_methods_on_local_receivers(self):
        source=self.program('let mut p=make(7);p.increment();yield;return p.read();',
            'impl Point{fn read(self:&Point)->Int{return self.x;}fn increment(self:&mut Point){self.x=self.x+1;}}')
        self.assertEqual(self.run_source(source).stdout,'8\n')
        self.refused(source.replace('let mut p=make','let p=make'),'mutab|immuable')

    def test_replacement_preserves_local_or_allocated_type(self):
        source=(ROOT/'validation/rejected-async-local-pool-replacement.crb').read_text()
        self.refused(source,'types distincts')
        reverse=source.replace('work(q:','work(mut q:').replace(
            'let mut p=make();print(p.x);print(q.x);p=<-q;return p.x;',
            'let p=make();print(p.x);print(q.x);q=<-p;return q.x;')
        self.refused(reverse,'types distincts')

    def test_suspended_cleanup_releases_receiver_stack(self):
        source=self.program('let p=make(7);yield;return p.x;')
        for finished in (False,True):
            steps=('assert(task_poll(task)==TASK_COMPLETE);int result;assert(task_take(task,&result));assert(result==7);'
                   if finished else 'assert(task_owned_discardable(task));assert(task_drop_owned(task));')
            with self.subTest(finished=finished):
                run=self.native(source,'''
    CrustTask *task=crust_async_work_create();
    int before=observed_closes;
    assert(task_poll(task)==TASK_SUSPENDED);
    Cell *local=((crust_async_work_state *)task)->value_0;
    assert(local->alive && local->source->stack && !local->source->pool);
    assert(local->source->live==1 && cell_load_int(local,0)==7);
    assert(local->layout->enum_name && strcmp(local->layout->enum_name,"Point")==0);
'''+steps+'''
    assert(observed_closes==before+1);
''')
                self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

    def test_scope_cleanup_count_model(self):
        # For k completed iterations the model closes k scope stores. At a
        # suspension in the next iteration, discarding closes exactly one more.
        source=self.program('let mut i=0;while i<3{let p=make(i);yield;print(p.x);i=i+1;}return i;')
        for completed in range(3):
            with self.subTest(completed=completed):
                run=self.native(source,f'''
    CrustTask *task=crust_async_work_create();int before=observed_closes;
    for(int i=0;i<{completed+1};++i) assert(task_poll(task)==TASK_SUSPENDED);
    assert(observed_closes==before+{completed});
    assert(task_owned_discardable(task));assert(task_drop_owned(task));
    assert(observed_closes==before+{completed+1});
''')
                self.assertEqual(run.stderr.count('destroy p=Point\n'),completed+1)


if __name__=='__main__':unittest.main()
