"""Select forwards the receiver's local destination to all possible producers."""
from pathlib import Path
import unittest

import test_async_result_storage as storage

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'validation/open-async-result-factory-select-result.crb').read_text()


class SelectResultPlacementTests(unittest.TestCase):
    run_source = storage.AsyncResultStorageTests.run_source
    run_c_oracle = storage.AsyncResultStorageTests.run_c_oracle
    run_native = storage.AsyncResultStorageTests.run_native
    storage_probe = storage.AsyncResultStorageTests.storage_probe
    refused = storage.AsyncResultStorageTests.refused

    def test_recorded_factory_result_survives_relay(self):
        run = self.run_source(SOURCE)
        self.assertEqual(run.stdout, '7\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'), 2)

    def test_direct_branches_and_successive_block_transfers(self):
        direct = SOURCE.replace('prepare(n)', 'leaf(n)').replace('prepare(n+1)', 'leaf(n+1)')
        self.assertEqual(self.run_source(direct).stdout, '7\n')
        nested = SOURCE.replace('let a=prepare(n);let b=prepare(n+1);',
                                'let outside={let a=prepare(n);let b=prepare(n+1);').replace(
            'drop(->s);return <-q;', 'drop(->s);<-q};yield;return <-outside;')
        self.assertEqual(self.run_source(nested).stdout, '7\n')

    def test_output_address_and_loser_cleanup(self):
        for finish in (False, True):
            ending = ('''
                assert(task_poll(task)==TASK_COMPLETE);
                Cell *result=NULL;assert(task_take(task,&result));
                assert(result==first && result->alive && result->source==&destination);
                assert(cell_load_int(result,0)==7 && destination.live==1);
                cell_drop(result);
            ''' if finish else '''
                assert(task_owned_discardable(task));assert(task_drop_owned(task));
            ''')
            run = self.storage_probe(SOURCE, '''
                Source destination=source_stack(4096);
                CrustTask *task=crust_async_relay_create(7,&destination);
                assert(task_poll(task)==TASK_SUSPENDED);
                assert(observed_count==2 && destination.live==2);
                Cell *first=observed_cells[0];(void)first;
                assert(first->source==&destination && observed_cells[1]->source==&destination);
            ''' + ending + '''
                assert(destination.live==0 && destination.used==0);
                assert(task_pool_is_empty(&crust_task_context.pool_leaf));
                assert(task_pool_is_empty(&crust_task_context.pool_relay));
                source_close(&destination);
            ''')
            self.assertEqual(run.stderr.count('destroy p=Point\n'), 2)

    def test_result_reference_still_prevents_drop(self):
        source = SOURCE.replace('print(q.x);drop(->q);',
                                'let view=&q.x;print(*view);drop(->q);')
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.refused(source.replace('print(*view);drop(->q);', 'drop(->q);print(*view);'),
                     'emprunt|réserv|référenc')

    def test_pool_results_and_borrowed_inputs_are_not_promoted(self):
        declarations = '''struct Point{x:Int}
            fn duplicate(p:&Point)-><-Point{let q=copy(p);return <-q;}
            async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}
            fn prepare(p:&Point)-><-leaf{return <-leaf(p);}
            async fn choose(p:&Point)-><-Point{
                let a=prepare(p);let b=prepare(p);let mut s=runtime::select(->a,->b);
                let q=s.await;drop(->s);return <-q;}'''
        main = '''fn main(){let q={let mut points=pool<Point>(3);let p=points.new(x:7);
            let h=runtime::spawn(->choose(&p));
            let q=match h.join(){Ok(q)=>{<-q},Err(_)=>{return;}};drop(->p);<-q};
            print(q.x);drop(->q);}'''
        self.refused(declarations + main, 'pool|source|survi')


if __name__ == '__main__':
    unittest.main()
