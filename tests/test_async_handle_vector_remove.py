"""Explicit extraction preserves element ownership across async calls."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT/'validation/open-async-handle-vector-remove.crb').read_text()
RETURN = (ROOT/'validation/open-async-handle-vector-remove-return.crb').read_text()


class AsyncHandleVectorRemoveTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_recorded_local_extraction_and_explicit_move(self):
        run = self.run_source(BASE)
        self.assertEqual(run.stdout, '7\n8\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7')
                             for s in run.stderr.splitlines()), 1)
        self.refused(BASE.replace('<-values.remove(0)', 'values.remove(0)'), 'transfert|<-')
        self.refused(BASE.replace('drop(->value);', 'drop(->value);print(*value);'),
                     'utilisable|détruit|drop|transfert')
        self.refused(BASE.replace('&mut Vector', '&Vector').replace('count(&mut values)', 'count(&values)'),
                     'mutable')

    def test_return_direct_factory_and_awaited_relay(self):
        factory = 'fn make(v:&mut Vector<A<Int>>)-><-count{return <-count(v);}'
        relay = 'async fn relay(v:&mut Vector<A<Int>>)-><-Int{let n=make(v).await;yield;return <-n;}'
        for callee in ('count', 'make', 'relay'):
            with self.subTest(callee=callee):
                run = self.run_source(factory+relay+RETURN.replace('spawn(-> count(', 'spawn(-> '+callee+'('))
                self.assertEqual(run.stdout, '7\n8\n')

    def test_order_and_distinct_pools(self):
        source = '''async fn take(v:&mut Vector<A<Int>>)-><-Int{
            yield;let n=<-v.remove(1);print(*v[0]);print(*v[1]);return <-n;}
            fn main(){let mut p=pool<Int>(2);let mut q=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);
            let mut v=vp.new();v.push(->p.new(10));v.push(->q.new(20));v.push(->p.new(30));
            let h=runtime::spawn(->take(&mut v));
            match h.join(){Ok(n)=>{v ->;drop(->v);print(*n);drop(->n);},Err(_)=>{v ->;drop(->v);}}
            let a=p.new(11);let b=p.new(31);let c=q.new(21);print(*a);print(*b);print(*c);}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout, '10\n30\n20\n11\n31\n21\n')
        for n in (10, 20, 30):
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('='+str(n))
                                 for s in run.stderr.splitlines()), 1)

    def test_borrow_last_use(self):
        source = BASE.replace('let value=<-values.remove(0);',
                              'let view=&*values[0];print(*view);yield;let value=<-values.remove(0);')
        self.assertEqual(self.run_source(source).stdout, '7\n7\n8\n')
        self.refused(source.replace('let answer=*value;', 'print(*view);let answer=*value;'), 'emprunt actif')

    def test_suspended_index_and_bounds(self):
        helper = 'async fn index()->Int{print(4);yield;return 0;}'
        source = helper+BASE.replace('values.remove(0)', 'values.remove(index().await)')
        self.assertEqual(self.run_source(source).stdout, '4\n7\n8\n')
        run = self.run_c_oracle(compile_source(source.replace('return 0;', 'return 1;')),
                                expected_error='indice de Vector hors limites')
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(run.stdout, '4\n')
        self.assertRegex(run.stderr, 'indice|index|borne')

    def test_sync_helper_and_explicit_drop(self):
        helper = 'fn take(v:&mut Vector<A<Int>>)-><-Int{return <-v.remove(0);}'
        source = helper+BASE.replace('<-values.remove(0)', 'take(values)')
        self.assertEqual(self.run_source(source).stdout, '7\n8\n')
        direct = BASE.replace('let value=<-values.remove(0);let answer=*value;drop(->value);return answer;',
                              'drop(->values.remove(0));return 7;')
        self.assertEqual(self.run_source(direct).stdout, '7\n8\n')

    def test_result_outlives_vector_but_not_element_pool(self):
        helper = '''async fn take(mut v:->Vector<A<Int>>)-><-Int{
            yield;let n=<-v.remove(0);return <-n;}
            fn make(v:->Vector<A<Int>>)-><-take{return <-take(->v);}'''
        main = '''fn main(){OUTER
            let result={INNER let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
                v.push(->p.new(7));let h=runtime::spawn(->CALLEE(->v));let r=h.join();<-r};
            match result{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}}'''
        pool = 'let mut p=pool<Int>(1);'
        for callee in ('take', 'make'):
            source = helper+main.replace('CALLEE', callee)
            with self.subTest(callee=callee):
                self.assertEqual(self.run_source(source.replace('OUTER', pool).replace('INNER', '')).stdout, '7\n')
                self.refused(source.replace('OUTER', '').replace('INNER', pool), 'pool|source|survi')

    def test_replacement_destroys_previous_after_new_is_ready(self):
        source = '''async fn work(v:&mut Vector<A<Int>>)->Int{
            let mut old=<-v.remove(0);yield;old=<-v.remove(0);return *old;}
            fn main(){let mut p=pool<Int>(2);let mut vp=pool<Vector<A<Int>>>(1);
                let mut v=vp.new();v.push(->p.new(7));v.push(->p.new(9));
                let h=runtime::spawn(->work(&mut v));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                drop(->v);let next=p.new(8);print(*next);}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout, '9\n8\n')
        for n in (7, 9):
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('='+str(n))
                                 for s in run.stderr.splitlines()), 1)
        self.refused(source.replace('yield;old=', 'let view=&old;yield;old=').replace(
            'return *old;', 'print(*view);return *old;'), 'emprunt actif')


if __name__ == '__main__':
    unittest.main()
