"""Explicit async insertion retains handle pools and unique cleanup."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-vector-push.crb').read_text()
FACTORY='fn make(v:&mut Vector<A<Int>>,p:&mut Pool<Int>)-><-append{return <-append(v,p);}'

class AsyncHandleVectorPushTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_recorded_case_and_explicit_type(self):
        run=self.run_source(BASE)
        self.assertEqual(run.stdout,'7\n8\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)
        for argument in ('numbers.new(7)','7','-> true'):
            with self.subTest(argument=argument):
                self.refused(BASE.replace('-> numbers.new(7)',argument),'transfert|allocation|type|propriétaire')
        self.refused(BASE.replace('values: &mut Vector','values: &Vector').replace('append(&mut values,','append(&values,'),'mutable')

    def test_named_transfer_and_borrow_last_use(self):
        source=BASE.replace('values.push(-> numbers.new(7));',
            'let n=numbers.new(7);let view=&n;print(*view);yield;values.push(-> n);')
        self.assertEqual(self.run_source(source).stdout,'7\n7\n8\n')
        self.refused(source.replace('values.push(-> n);','values.push(-> n);print(*n);'),'utilisable|transfert|consomm')
        self.refused(source.replace('values.push(-> n);','values.push(-> n);print(*view);'),'emprunt actif')
        self.refused(source.replace('print(*view);yield;', 'print(*view);yield;values.push(-> n);'),
                     'utilisable|transfert|consomm')

    def test_factory_and_awaited_relay(self):
        source=FACTORY+BASE.replace('spawn(-> append(', 'spawn(-> make(')
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        helper='async fn relay(v:&mut Vector<A<Int>>,p:&mut Pool<Int>)->Int{let n=make(v,p).await;yield;return n;}'
        self.assertEqual(self.run_source(helper+source.replace('spawn(-> make(', 'spawn(-> relay(')).stdout,'7\n8\n')
        for item in (BASE,source):
            short=item.replace('    let mut numbers = pool<Int>(1);\n','').replace(
                '    let h =','    {let mut numbers=pool<Int>(1);let h =').replace(
                '    drop(-> values);','    }drop(-> values);').replace('    let reused = numbers.new(8);\n    print(*reused);','')
            self.refused(short,'surviv|durable|source|pool')

    def test_two_owned_inputs_from_distinct_pools(self):
        helpers='''async fn append(v:&mut Vector<A<Int>>,a:->Int,b:->Int)->Int{
            yield;v.push(->a);yield;v.push(->b);return *v[0]+*v[1];}
            fn make(v:&mut Vector<A<Int>>,a:->Int,b:->Int)-><-append{return <-append(v,->a,->b);}'''
        main='''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);
            let mut v=vp.new();let a=p.new(10);let b=q.new(20);
            let h=runtime::spawn(->make(&mut v,->a,->b));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
            drop(->v);let x=p.new(11);let y=q.new(21);print(*x);print(*y);}'''
        for callee in ('make','append'):
            with self.subTest(callee=callee):
                run=self.run_source(helpers+main.replace('spawn(->make(',f'spawn(->{callee}('))
                self.assertEqual(run.stdout,'30\n11\n21\n')
                for value in (10,20):
                    self.assertEqual(sum(s.startswith('destroy ') and s.endswith('='+str(value)) for s in run.stderr.splitlines()),1)

    def test_inactive_and_failed_launch_do_not_insert(self):
        inactive=BASE.replace('let h = runtime::spawn(-> append(&mut values, &mut numbers));',
            'let task=append(&mut values,&mut numbers);drop(->task);').replace(
            '    match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }','    print(values.len());')
        self.assertEqual(self.run_source(inactive).stdout,'0\n8\n')
        run=self.run_c_oracle(inject_submission_failure(compile_source(BASE),asynchronous=False,at=1))
        self.assertEqual(run.stdout,'99\n8\n')
        self.assertFalse(any(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()))

    def test_receiver_borrow_ends_before_next_push(self):
        source=BASE.replace('pool<Int>(1)', 'pool<Int>(2)').replace(
            'values.push(-> numbers.new(7));',
            'values.push(-> numbers.new(7));let view=&*values[0];print(*view);yield;values.push(-> numbers.new(9));')
        self.assertEqual(self.run_source(source).stdout,'7\n7\n8\n')
        self.refused(source.replace('values.push(-> numbers.new(9));',
                                   'values.push(-> numbers.new(9));print(*view);'), 'emprunt actif')

    def test_sync_insertion_helper(self):
        helper='fn put(v:&mut Vector<A<Int>>,p:&mut Pool<Int>){v.push(->p.new(7));}'
        source=helper+BASE.replace('values.push(-> numbers.new(7));','put(values,numbers);yield;')
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')

    def test_owned_vector_cleans_new_item_at_completion(self):
        source='''async fn consume(mut v:->Vector<A<Int>>,n:->Int)->Int{v.push(->n);yield;return *v[0];}
            fn main(){let mut p=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);
            let v=vp.new();let n=p.new(7);let h=runtime::spawn(->consume(->v,->n));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
            let next=p.new(8);let empty=vp.new();print(*next);print(empty.len());drop(->empty);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n8\n0\n')

    def test_suspended_loser_publishes_inserted_pool(self):
        helper='''async fn ready()->Int{return 9;}
            async fn choose(v:&mut Vector<A<Int>>,p:&mut Pool<Int>)->Int{
                let mut s=runtime::select(->MAKE(v,p),->ready());
                let r=s.await;drop(->s);print(v.len());return r;}'''
        for callee in ('append','make'):
            source=FACTORY+helper.replace('MAKE',callee)+BASE.replace('    yield;\n','').replace(
                '    return *values[0];','    yield;return *values[0];').replace(
                'spawn(-> append(', 'spawn(-> choose(')
            with self.subTest(callee=callee):
                self.assertEqual(self.run_source(source).stdout,'1\n9\n8\n')
                short=source.replace('    let mut numbers = pool<Int>(1);\n','').replace(
                    '    let h =','    {let mut numbers=pool<Int>(1);let h =').replace(
                    '    drop(-> values);','    }drop(-> values);').replace('    let reused = numbers.new(8);\n    print(*reused);','')
                self.refused(short,'surviv|durable|source|pool')

if __name__=='__main__':unittest.main()
