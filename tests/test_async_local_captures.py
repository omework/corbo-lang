"""Static local/pool capture variants preserve storage, loans and cleanup."""
from pathlib import Path
import unittest
from crust import compile_source
import test_async_local_parent as parent
import test_native_blocks as native

ROOT=Path(__file__).resolve().parents[1]
PREFIX='struct Point{x:Int}fn make(n:Int)-><-Point{let p=Point{x:n};return <-p;}'

class AsyncLocalCaptureTests(unittest.TestCase):
    run_source=parent.AsyncLocalParentTests.run_source
    run_c_oracle=parent.AsyncLocalParentTests.run_c_oracle
    refused=parent.AsyncLocalParentTests.refused
    storage_probe=parent.AsyncLocalParentTests.storage_probe
    run_native=native.NativeBlockTests.run_native
    program=staticmethod(parent.AsyncLocalParentTests.program)

    def test_recorded_shared_capture_and_relay(self):
        recorded=(ROOT/'validation/open-async-local-helper-child-capture.crb').read_text()
        self.assertEqual(self.run_source(recorded).stdout,'7\n')
        helpers='async fn leaf(p:&Point)->Int{yield;return p.x;}async fn relay(p:&Point)->Int{yield;return leaf(p).await;}'
        self.assertEqual(self.run_source(self.program('let p=make(9);return relay(&p).await;',helpers)).stdout,'9\n')

    def test_mutable_capture_reserves_parent(self):
        helpers='async fn edit(p:&mut Point)->Int{yield;p.x=p.x+1;return p.x;}'
        body='let mut p=make(7);let task=edit(&mut p);BEFORE let n=task.await;print(n);return p.x;'
        self.assertEqual(self.run_source(self.program(body.replace('BEFORE',''),helpers)).stdout,'8\n8\n')
        for invalid in ('print(p.x);','p.x=9;','drop(->p);'):
            with self.subTest(invalid=invalid):
                self.refused(self.program(body.replace('BEFORE',invalid),helpers),'emprunt|réserv|référenc')

    def test_owned_capture_relay_and_inactive_cleanup(self):
        helpers='async fn leaf(p:->Point)->Int{yield;return p.x;}async fn relay(p:->Point)->Int{yield;return leaf(->p).await;}'
        for code,expected in (('return relay(->p).await;','7\n'),('let task=relay(->p);drop(->task);return 9;','9\n')):
            run=self.run_source(self.program('let p=make(7);'+code,helpers))
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('destroy p=Point\n'),1)
        self.refused(self.program('let p=make(7);let task=relay(->p);print(p.x);return task.await;',helpers),'consomm|utilis|transfér')

    def test_sync_caller_and_mixed_copy_variants(self):
        source=PREFIX+'''
            async fn read(p:&Point)->Int{let q=copy(p);yield;return q.x;}
            fn main(){let local=make(7);let mut points=pool<Point>(2);let allocated=points.new(x:9);
                let a=runtime::spawn(->read(&local));let b=runtime::spawn(->read(&allocated));
                match a.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                match b.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(local.x);print(allocated.x);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n9\n7\n9\n')
        code=compile_source(source)
        self.assertEqual(code.count('CrustTaskPool pool_read;'),1)
        self.assertIn('crust_async_read_storage states_read',code)
        self.assertIn('sizeof(crust_async_read_storage)',code)
        self.assertEqual(run.stderr.count('destroy async copy=Point\n'),2)

    def test_local_copy_in_child_is_independent(self):
        helpers='''fn duplicate(p:&Point)-><-Point{let q=copy(p);return <-q;}
            async fn leaf(p:&Point)->Int{let q=duplicate(p);yield;return q.x;}
            async fn relay(p:&Point)->Int{yield;return leaf(p).await;}'''
        source=self.program('let p=make(7);let n=relay(&p).await;print(n);return p.x;',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n7\n')

    def test_one_slot_reused_between_variants(self):
        source=PREFIX+'''#(directive, async_pool_sizes={read:1})
            
            async fn read(p:&Point)->Int{let q=copy(p);yield;return q.x;}
            fn main(){let local=make(7);let mut points=pool<Point>(2);let allocated=points.new(x:9);
                let mut i=0;while i<4{
                    let a=runtime::spawn(->read(&local));match a.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                    let b=runtime::spawn(->read(&allocated));match b.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                    i=i+1;}print(local.x);print(allocated.x);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n9\n'*4+'7\n9\n')

    def test_local_owned_return_preserves_parent_storage(self):
        helpers='async fn echo(p:->Point)-><-Point{yield;return <-p;}'
        source=self.program('let p=make(7);let q=echo(->p).await;yield;return q.x;',helpers)
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

    def test_explicit_allocation_type_rejects_local(self):
        helpers='async fn consume(p:->A<Point>)->Int{return p.x;}'
        self.refused(self.program('let p=make(7);return consume(->p).await;',helpers),'A<T>|allocation|local')
        source=PREFIX+helpers+'fn main(){let p=make(7);let h=runtime::spawn(->consume(->p));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'
        self.refused(source,'A<T>|allocation|local')

    def test_child_cannot_escape_local_storage(self):
        source=PREFIX+'''async fn read(p:&Point)->Int{yield;return p.x;}
            fn main(){let task={let p=make(7);let task=read(&p);<-task};
                let h=runtime::spawn(->task);match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.refused(source,'source|survi|emprunt|capture')

    def test_launch_failure_releases_owned_local(self):
        source=PREFIX+'''async fn consume(p:->Point)->Int{yield;return p.x;}
            fn main(){let p=make(7);let h=runtime::spawn(->consume(->p));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        for failure,expected in ((None,'7\n'),(1,'99\n')):
            with self.subTest(failure=failure):
                run=self.run_native(source,fail_submission_at=failure)
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

    def test_explicit_allocation_return_rejects_local(self):
        for returned in ('<-p', '<-identity(->p)'):
            helpers=('fn identity(p:->Point)-><-Point{return <-p;}'
                     'async fn echo(p:->Point)-><-A<Point>{yield;return '+returned+';}')
            self.refused(self.program('let p=make(7);let q=echo(->p).await;return q.x;',helpers),
                         'A<T>|allocation|local')

    def test_borrowed_result_reserves_local_after_child_completion(self):
        helpers='async fn lend(p:&mut Point)->&mut Int{yield;return &mut p.x;}'
        source=self.program('let mut p=make(7);let mut view=lend(&mut p).await;BEFORE view.set(9);return p.x;',helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'9\n')
        for invalid in ('print(p.x);','drop(->p);'):
            self.refused(source.replace('BEFORE',invalid),'emprunt|réserv|référenc')

    def test_copy_storage_and_suspended_cleanup(self):
        helpers='''fn duplicate(p:&Point)-><-Point{let q=copy(p);return <-q;}
            async fn leaf(p:&Point)->Int{let q=duplicate(p);yield;return q.x;}'''
        source=self.program('let p=make(7);let n=leaf(&p).await;print(n);yield;return p.x;',helpers)
        # Inspect the actual ABI, including a mutant which omits specialization.
        # The independent oracle below still requires separate lifetimes/storage.
        code=compile_source(source)
        storage_type='crust_async_leaf_storage' if '} crust_async_leaf_storage;' in code else 'crust_async_leaf_state'
        for complete in (False,True):
            ending=('assert(task_poll(task)==TASK_SUSPENDED);assert(observed_cells[0]->alive);'
                    'assert(copy_source->live==0 && copy_source->used==0);assert(task_poll(task)==TASK_COMPLETE);'
                    'int answer;assert(task_take(task,&answer));assert(answer==7);'
                    if complete else 'assert(task_owned_discardable(task));assert(task_drop_owned(task));')
            run=self.storage_probe(source, '''
                assert(crust_task_context.pool_leaf.stride==sizeof(STORAGE_TYPE));
                CrustTask *task=crust_async_work_create();assert(task_poll(task)==TASK_SUSPENDED);
                assert(observed_count==2);Cell *original=observed_cells[0];Cell *copy=observed_cells[1];
                Source *copy_source=copy->source;(void)copy_source;assert(original!=copy && original->source!=copy_source);
                assert(original->alive && copy->alive && original->source->stack && copy->source->stack);
                assert(cell_load_int(original,0)==7 && cell_load_int(copy,0)==7);
            '''.replace('STORAGE_TYPE',storage_type)+ending+'''
                assert(observed_close_count==2);
                assert(task_pool_is_empty(&crust_task_context.pool_leaf));
                assert(task_pool_is_empty(&crust_task_context.pool_work));
            ''')
            self.assertEqual(run.stderr.count('destroy p=Point\n'),1)
            self.assertEqual(run.stderr.count('destroy q=Point\n'),1)

if __name__=='__main__':unittest.main()
