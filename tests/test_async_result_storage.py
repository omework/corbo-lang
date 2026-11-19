"""Fresh async locals use caller storage; pooled copies retain their pool."""
from pathlib import Path
import unittest
from crust import Error
import test_async_local_captures as captures
import test_storage_requirements as requirements

ROOT=Path(__file__).resolve().parents[1]
PREFIX=captures.PREFIX
DUPLICATE=requirements.DUPLICATE

class AsyncResultStorageTests(unittest.TestCase):
    run_source=captures.AsyncLocalCaptureTests.run_source
    run_c_oracle=captures.AsyncLocalCaptureTests.run_c_oracle
    run_native=captures.AsyncLocalCaptureTests.run_native
    refused=captures.AsyncLocalCaptureTests.refused
    program=staticmethod(captures.AsyncLocalCaptureTests.program)

    def storage_probe(self, source, body):
        try:
            return captures.AsyncLocalCaptureTests.storage_probe(self, source, body)
        except Error as error:
            self.fail(f'programme attendu valide refusé avant la sonde C : {error}')

    def test_recorded_copy_return(self):
        source=(ROOT/'validation/open-async-fresh-local-result-destination.crb').read_text()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy q=Point\n'),1)

    def test_fresh_result_from_scalar_capture(self):
        helpers='async fn leaf(n:Int)-><-Point{let p=make(n);yield;return <-p;}'
        source=self.program('let q=leaf(7).await;yield;return q.x;',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        source=PREFIX+helpers+'''fn main(){let task=leaf(8);let h=runtime::spawn(->task);
            match h.join(){Ok(q)=>{print(q.x);drop(->q);},Err(_)=>{}}}'''
        self.assertEqual(self.run_source(source).stdout,'8\n')

    def test_returned_copy_releases_original_borrow(self):
        helpers=DUPLICATE+'async fn leaf(p:&Point)-><-Point{let q:Point=duplicate(p);yield;return <-q;}'
        source=self.program('let p=make(7);let q=leaf(&p).await;drop(->p);yield;return q.x;',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(self.program('let p=make(7);let t=leaf(&p);drop(->p);let q=t.await;return q.x;',helpers),
                     'emprunt|réserv|référenc')

    def test_conditional_fresh_results(self):
        helpers='async fn leaf(n:Int)-><-Point{if n==0{let a=make(7);yield;return <-a;}let b=make(9);yield;return <-b;}'
        for flag,expected in ((0,'7\n'),(1,'9\n')):
            source=self.program('let q=leaf('+str(flag)+').await;return q.x;',helpers)
            self.assertEqual(self.run_source(source).stdout,expected)

    def test_computed_and_nested_return_producers(self):
        for body in ('yield;return <-make(n);',
                     'let q={if n==7{yield;return <-make(n);}let p=make(9);<-p};return <-q;'):
            for n in (7,9):
                helpers='async fn leaf(n:Int)-><-Point{'+body+'}'
                with self.subTest(body=body,n=n):
                    source=self.program('let q=leaf('+str(n)+').await;return q.x;',helpers)
                    self.assertEqual(self.run_source(source).stdout,str(n)+'\n')

    def test_result_borrow_still_prevents_drop(self):
        helpers='async fn leaf(n:Int)-><-Point{yield;return <-make(n);}'
        source=self.program('let q=leaf(7).await;let view=&q.x;yield;print(*view);drop(->q);return 9;',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('print(*view);drop(->q);','drop(->q);print(*view);'),
                     'emprunt|réserv|référenc')

    def test_reference_row_capture_and_independent_result(self):
        source=PREFIX+'''async fn leaf(p:&Point,row:&[&Int;2])-><-Point{
            let q=duplicate(p);yield;print(*row[0]);return <-q;}
            '''+DUPLICATE+'''fn main(){let mut ints=pool<Int>(2);let a=ints.new(3);let b=ints.new(4);
            let row=[&a,&b];POINT let h=runtime::spawn(->leaf(&p,&row));
            let q=match h.join(){Ok(q)=>{<-q},Err(_)=>{return;}};
            drop(->row);drop(->a);drop(->b);drop(->p);print(q.x);drop(->q);}'''
        for creation in ('let p=make(7);', 'let mut points=pool<Point>(2);let p=points.new(x:7);'):
            with self.subTest(creation=creation):
                self.assertEqual(self.run_source((source if 'make(7)' in creation else source.replace('leaf(p:&Point,row:&[&Int;2])-><-Point','leaf(p:&Point,row:&[&Int;2])-><-A<Point>').replace('duplicate(p:&Point)-><-Point','duplicate(p:&Point)-><-A<Point>')).replace('POINT',creation)).stdout,'3\n7\n')

    def test_two_concurrent_fresh_results(self):
        source=PREFIX+'''async fn leaf(n:Int)-><-Point{let p=make(n);yield;return <-p;}
            fn main(){let a=runtime::spawn(->leaf(7));let b=runtime::spawn(->leaf(9));
                let first=a.join();let second=b.join();
                match first{Ok(p)=>{print(p.x);drop(->p);},Err(_)=>{}}
                match second{Ok(p)=>{print(p.x);drop(->p);},Err(_)=>{}}}'''
        self.assertEqual(self.run_native(source).stdout,'7\n9\n')

    def test_loop_result_and_repeated_reuse(self):
        helpers='''async fn leaf(n:Int)-><-Point{let mut i=0;let p=loop{
            let q=make(n+i);yield;i=i+1;if i<2{continue;}break <-q;};return <-p;}'''
        source=self.program('let mut i=0;while i<4{let p=leaf(i).await;print(p.x);drop(->p);i=i+1;}return i;',helpers)
        run=self.run_source(source)
        self.assertEqual(run.stdout,'1\n2\n3\n4\n4\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),8)

    def test_pool_copy_keeps_pool_but_not_original(self):
        helpers=DUPLICATE+'async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}'
        source=PREFIX+helpers.replace('-><-Point','-><-A<Point>')+'''fn main(){let mut points=pool<Point>(2);let p=points.new(x:7);
            let h=runtime::spawn(->leaf(&p));let q=match h.join(){Ok(q)=>{<-q},Err(_)=>{return;}};
            drop(->p);print(q.x);drop(->q);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_pool_copy_cannot_escape_pool(self):
        source=(ROOT/'validation/open-async-copy-result-short-pool.crb').read_text()
        self.refused(source.replace('-><-Point','-><-A<Point>'),'pool|source|survi')

    def test_launch_failure_and_inactive_drop(self):
        source=PREFIX+'''async fn leaf(n:Int)-><-Point{let p=make(n);yield;return <-p;}
            fn main(){let h=runtime::spawn(->leaf(7));match h.join(){Ok(q)=>{print(q.x);drop(->q);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'99\n')
        inactive=source[:source.index('fn main')]+ 'fn main(){let t=leaf(7);drop(->t);}'
        self.assertNotIn('destroy p=Point',self.run_source(inactive).stderr)

    def test_result_identity_after_child_release(self):
        helpers='async fn leaf(n:Int)-><-Point{let p=make(n);yield;return <-p;}'
        source=self.program('let q=leaf(7).await;yield;return q.x;',helpers)
        run=self.storage_probe(source, '''
            CrustTask *task=crust_async_work_create();assert(task_poll(task)==TASK_SUSPENDED);
            assert(observed_count==1);Cell *result=observed_cells[0];Source *destination=result->source;
            assert(result->alive && cell_load_int(result,0)==7);
            assert(task_poll(task)==TASK_SUSPENDED);
            assert(task_pool_is_empty(&crust_task_context.pool_leaf));
            assert(observed_cells[0]==result && result->alive && result->source==destination);
            assert(cell_load_int(result,0)==7 && observed_close_count==0);
            assert(task_poll(task)==TASK_COMPLETE);int answer;assert(task_take(task,&answer));assert(answer==7);
            assert(observed_close_count==1 && observed_closed[0]==destination);
        ''')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

    def test_suspended_child_discards_partial_result(self):
        helpers='async fn leaf(n:Int)-><-Point{let p=make(n);yield;return <-p;}'
        source=self.program('let q=leaf(7).await;return q.x;',helpers)
        run=self.storage_probe(source, '''
            CrustTask *task=crust_async_work_create();assert(task_poll(task)==TASK_SUSPENDED);
            assert(observed_count==1 && observed_cells[0]->alive);
            assert(task_owned_discardable(task));assert(task_drop_owned(task));
            assert(observed_close_count==1);
            assert(task_pool_is_empty(&crust_task_context.pool_leaf));
            assert(task_pool_is_empty(&crust_task_context.pool_work));
        ''')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

if __name__=='__main__':unittest.main()
