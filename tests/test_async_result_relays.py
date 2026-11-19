"""Fresh async output destinations propagate through scopes and child states."""
from pathlib import Path
import unittest
import test_async_result_storage as output
DUPLICATE=output.DUPLICATE

ROOT=Path(__file__).resolve().parents[1]
LEAF='async fn leaf(n:Int)-><-Point{let p=make(n);yield;return <-p;}'

class AsyncResultRelayTests(unittest.TestCase):
    run_source=output.AsyncResultStorageTests.run_source
    run_c_oracle=output.AsyncResultStorageTests.run_c_oracle
    refused=output.AsyncResultStorageTests.refused
    storage_probe=output.AsyncResultStorageTests.storage_probe
    program=staticmethod(output.AsyncResultStorageTests.program)

    def test_recorded_parent_and_relay(self):
        for suffix in ('child_parent','relay'):
            source=(ROOT/('validation/open-async-result-storage-'+suffix+'.crb')).read_text()
            self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_named_task_and_successive_parent_transfers(self):
        for constructor in ('let q=leaf(7).await;', 'let t=leaf(7);let q=t.await;'):
            source=self.program('let r={let middle={'+constructor+'yield;<-q};yield;<-middle};return r.x;',LEAF)
            self.assertEqual(self.run_source(source).stdout,'7\n')
        source=self.program('let t={let child=leaf(7);<-child};let r=t.await;return r.x;',LEAF)
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_conditional_and_loop_receivers(self):
        for flag,expected in (('true','7\n'),('false','9\n')):
            source=self.program('let q=if '+flag+'{let p=leaf(7).await;<-p}else{let p=leaf(9).await;<-p};return q.x;',LEAF)
            self.assertEqual(self.run_source(source).stdout,expected)
        source=self.program('let mut i=0;let q=loop{let p=leaf(i).await;i=i+1;if i<3{continue;}break <-p;};return q.x;',LEAF)
        run=self.run_source(source)
        self.assertEqual(run.stdout,'2\n');self.assertEqual(run.stderr.count('destroy p=Point\n'),3)

    def test_relay_computed_and_named_returns(self):
        for body in ('return <-leaf(n).await;', 'let t=leaf(n);let q=t.await;return <-q;',
                     'let q={let p=leaf(n).await;<-p};return <-q;',
                     'let mut q=make(n-1);{q=<-leaf(q.x+1).await;}return <-q;'):
            helpers=LEAF+'async fn relay(n:Int)-><-Point{'+body+'}async fn again(n:Int)-><-Point{let r=relay(n).await;yield;return <-r;}'
            self.assertEqual(self.run_source(self.program('let r=again(7).await;return r.x;',helpers)).stdout,'7\n')

    def test_local_copy_does_not_promote_original(self):
        helpers=DUPLICATE+'async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}'
        source=self.program('let r={let p=make(7);let q=leaf(&p).await;<-q};yield;return r.x;',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('let q=leaf(&p).await;', 'let t=leaf(&p);drop(->p);let q=t.await;'),
                     'emprunt|réserv|référenc')
        self.refused(self.program('let t={let p=make(7);let t=leaf(&p);<-t};let r=t.await;return r.x;',helpers),
                     'emprunt|réserv|référenc|source|survi')

    def test_parent_replacement_and_loop(self):
        source=self.program('let mut r=make(1);{r=<-leaf(r.x+6).await;}return r.x;',LEAF)
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n');self.assertEqual(run.stderr.count('destroy p=Point\n'),2)
        source=self.program('let r={let mut p=make(1);let mut i=0;while i<3{print(p.x);p=<-leaf(p.x+1).await;i=i+1;}<-p};return r.x;',LEAF)
        self.assertEqual(self.run_source(source).stdout,'1\n2\n3\n4\n')

    def test_pool_source_and_result_borrow_are_not_promoted(self):
        helpers=DUPLICATE+'async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}'
        self.refused(self.program('let r={let mut points=pool<Point>(2);let p=points.new(x:7);let q=leaf(&p).await;<-q};return r.x;',helpers.replace('-><-Point','-><-A<Point>')),
                     'pool|source|survi')
        source=self.program('let r={let q=leaf(7).await;<-q};let view=&r.x;drop(->r);return *view;',LEAF)
        self.refused(source,'emprunt|réserv|référenc')

    def test_child_storage_closed_but_result_identity_preserved(self):
        source=self.program('let r={let temp=make(2);print(temp.x);let q=leaf(7).await;<-q};yield;return r.x;',LEAF)
        self.storage_probe(source, '''
            CrustTask *task=crust_async_work_create();assert(task_poll(task)==TASK_SUSPENDED);
            assert(observed_count==2);Cell *result=observed_cells[1];Source *parent=result->source;
            Source *child=observed_cells[0]->source;assert(child!=parent);
            assert(task_poll(task)==TASK_SUSPENDED);
            assert(task_pool_is_empty(&crust_task_context.pool_leaf));
            assert(observed_close_count==1 && observed_closed[0]==child);
            assert(result==observed_cells[1] && result->alive && cell_load_int(result,0)==7);
            assert(task_poll(task)==TASK_COMPLETE);int answer;assert(task_take(task,&answer));assert(answer==7);
            assert(observed_close_count==2 && observed_closed[1]==parent);
        ''')

    def test_relay_suspended_cleanup_and_completed_identity(self):
        helpers=LEAF+'async fn relay(n:Int)-><-Point{let q=leaf(n).await;return <-q;}'
        source=self.program('let q=relay(7).await;yield;return q.x;',helpers)
        for finish in (False,True):
            ending=('assert(task_poll(task)==TASK_SUSPENDED);assert(result->alive);'
                    'assert(task_pool_is_empty(&crust_task_context.pool_relay));'
                    'assert(task_pool_is_empty(&crust_task_context.pool_leaf));'
                    'assert(observed_close_count==0);assert(task_poll(task)==TASK_COMPLETE);'
                    'int answer;assert(task_take(task,&answer));assert(answer==7);'
                    if finish else 'assert(task_owned_discardable(task));assert(task_drop_owned(task));')
            run=self.storage_probe(source,'''
                CrustTask *task=crust_async_work_create();assert(task_poll(task)==TASK_SUSPENDED);
                assert(observed_count==1);Cell *result=observed_cells[0];assert(result->alive);
                Source *source=result->source;'''+ending+'''
                assert(observed_close_count==1 && observed_closed[0]==source);
                assert(task_pool_is_empty(&crust_task_context.pool_relay));
                assert(task_pool_is_empty(&crust_task_context.pool_leaf));
                assert(task_pool_is_empty(&crust_task_context.pool_work));
            ''')
            self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

if __name__=='__main__':unittest.main()
