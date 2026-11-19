"""ST17/ST18: direct copies in async keep storage and shared targets."""
import unittest
import test_async_result_storage as storage


class AsyncDirectCopyTests(unittest.TestCase):
    run_source = storage.AsyncResultStorageTests.run_source
    run_c_oracle = storage.AsyncResultStorageTests.run_c_oracle
    refused = storage.AsyncResultStorageTests.refused
    storage_probe = storage.AsyncResultStorageTests.storage_probe

    def program(self, body, helpers=''):
        return storage.PREFIX + helpers + '''async fn work()->Int{''' + body + '''}
        fn main(){let h=runtime::spawn(->work());match h.join(){
            Ok(n)=>{print(n);},Err(_)=>{}}}'''

    def test_local_copy_and_successive_parent_transfers(self):
        source = self.program('''let q={let p=Point{x:7};let middle={
            let view=&p;let c=copy(view);yield;<-c};drop(->p);<-middle};yield;return q.x;''')
        run = self.run_source(source)
        self.assertEqual(run.stdout, '7\n')
        self.assertEqual(run.stderr.count('=Point\n'), 2)

    def test_captured_copy_returns_to_caller(self):
        helpers = 'async fn leaf(p:&Point)-><-Point{let q=copy(p);yield;return <-q;}'
        for creation in ('let p=Point{x:7};',
                         'let mut points=pool<Point>(2);let p=points.new(x:7);'):
            with self.subTest(creation=creation):
                typed_helpers = helpers if 'Point{x:7}' in creation else helpers.replace('-><-Point', '-><-A<Point>')
                source = self.program(creation + 'let q=leaf(&p).await;drop(->p);yield;return q.x;', typed_helpers)
                self.assertEqual(self.run_source(source).stdout, '7\n')

    def test_explicit_pool_copy_and_reuse(self):
        source = self.program('''let p=Point{x:7};let mut points=pool<Point>(1);
            let q=points.copy(p);drop(->p);print(q.x);drop(->q);
            let r=points.new(x:9);return r.x;''')
        self.assertEqual(self.run_source(source).stdout, '7\n9\n')

    def test_shared_fields_keep_target_after_original_drop(self):
        source = self.program('''let mut ints=pool<Int>(1);let n=ints.new(7);
            let p=View{n:&n};let q=copy(p);drop(->p);yield;
            print(*q.n);drop(->q);drop(->n);return 1;''', 'struct View{n:&Int}')
        self.assertEqual(self.run_source(source).stdout, '7\n1\n')
        self.refused(source.replace('print(*q.n);drop(->q);drop(->n);',
                                    'drop(->n);print(*q.n);drop(->q);'), 'emprunt|réserv|référenc')

    def test_noncopy_fields_and_short_pool_are_rejected(self):
        for typ, field in (('&mut Int', '&mut n'), ('A<Int>', '<-n')):
            source = self.program('''let mut ints=pool<Int>(1);let mut n=ints.new(7);
                let p=View{n:FIELD};let q=copy(p);drop(->q);return 1;'''.replace('FIELD', field),
                'struct View{n:' + typ + '}')
            self.refused(source, 'non copiable')
        source = self.program('''let q={let mut points=pool<Point>(2);
            let p=points.new(x:7);let c=copy(p);<-c};return q.x;''')
        self.refused(source, 'pool|source|survi')

    def test_returned_copy_uses_external_storage_before_suspension(self):
        source = self.program('let q=leaf().await;return q.x;',
            'async fn leaf()-><-Point{let p=Point{x:7};let q=copy(p);yield;return <-q;}')
        self.storage_probe(source, '''
            Source destination=source_stack(4096);
            CrustTask *task=crust_async_leaf_create(&destination);
            assert(task_poll(task)==TASK_SUSPENDED);
            assert(observed_count==2);
            Cell *original=observed_cells[0], *copy=observed_cells[1];
            assert(original!=copy && original->source!=copy->source);
            assert(copy->source==&destination && cell_load_int(copy,0)==7);
            assert(task_poll(task)==TASK_COMPLETE);
            Cell *result=NULL;assert(task_take(task,&result));assert(result==copy);
            assert(result->alive && cell_load_int(result,0)==7);
            assert(task_pool_is_empty(&crust_task_context.pool_leaf));
            cell_drop(result);assert(destination.live==0);source_close(&destination);
        ''')


if __name__ == '__main__':
    unittest.main()
