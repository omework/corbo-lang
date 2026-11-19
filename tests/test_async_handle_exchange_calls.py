"""Sync helper contracts preserve the separate owned arms from async callers."""
from pathlib import Path
import unittest
import test_select_source as harness
from test_async_handle_vector_try_push import BASE as APPEND, full

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-exchange-call.crb').read_text()
REPLACE_RESULT='Result<A<Int>,A<Int>>'
PUSH_RESULT='Result<(),A<Int>>'


class AsyncHandleExchangeCallTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_replace_return_and_relay(self):
        helper=f'fn relay(r:->{REPLACE_RESULT})-><-{REPLACE_RESULT}{{return <-r;}}'
        for expression in ('exchange(v,->incoming)','relay(->exchange(v,->incoming))'):
            source=helper+BASE.replace('let r=exchange(v,->incoming);','let r='+expression+';')
            for index,expected in ((0,'7\n8\n9\n'),(5,'0\n7\n9\n')):
                self.assertEqual(self.run_source(source.replace('v.replace(0,','v.replace('+str(index)+',')).stdout,expected)
        self.refused(source.replace('relay(->exchange','relay(exchange'), 'transfert|->')

    def test_try_push_return_and_relay(self):
        helper=f'''fn insert(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-{PUSH_RESULT}{{return <-v.try_push(->incoming);}}
            fn relay(r:->{PUSH_RESULT})-><-{PUSH_RESULT}{{return <-r;}}'''
        source=helper+APPEND.replace('match <-v.try_push(->incoming)',
            'let r=relay(->insert(v,->incoming));yield;match (->r)')
        for program,expected in ((source,'1\n8\n9\n'),(full(source),'8\n1\n9\n')):
            self.assertEqual(self.run_source(program).stdout,expected)
        self.refused(source.replace('->Result<(),A<Int>>','->Result<A<Int>,A<Int>>'), 'type|incompatible|attendu')

    def test_argument_forms_and_await_order(self):
        helper=f'''async fn pause()->Int{{yield;return 4;}}
            fn relay(r:->{REPLACE_RESULT},n:Int)-><-{REPLACE_RESULT}{{print(n);return <-r;}}'''
        for setup,argument in (('', 'exchange(v,->incoming)'),
                               ('let original=exchange(v,->incoming);','original'),
                               ('','v.replace(0,->incoming)'),
                               ('','{incoming ->;let x=exchange(v,->incoming);<-x}')):
            source=helper+BASE.replace('let r=exchange(v,->incoming);',
                setup+'let r=relay(->'+argument+',pause().await);')
            with self.subTest(argument=argument):
                self.assertEqual(self.run_source(source).stdout,'4\n7\n8\n9\n')

    def test_void_consumer_and_drop_return(self):
        start=BASE.index('    let r=exchange')
        end=BASE.index('\n}\nfn main')
        helper=f'''fn consume(r:->{REPLACE_RESULT})->Void{{match (->r){{
            Ok(n)=>{{drop(->n);}},Err(n)=>{{drop(->n);}}}}}}'''
        for action in ('consume(->exchange(v,->incoming));','drop(->exchange(v,->incoming));'):
            source=helper+BASE[:start]+action+'return 42;'+BASE[end:]
            run=self.run_source(source)
            self.assertEqual(run.stdout,'42\n8\n9\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_select_cleans_prepared_argument(self):
        helper=f'''async fn pause()->Int{{yield;return 4;}}
            fn relay(r:->{REPLACE_RESULT},n:Int)-><-{REPLACE_RESULT}{{print(n);return <-r;}}
            async fn ready()->Int{{return 3;}}
            async fn choose(v:&mut Vector<A<Int>>,incoming:->Int)->Int{{
                let mut s=runtime::select(->replace(v,->incoming),->ready());let n=s.await;drop(->s);return n;}}'''
        source=helper+BASE.replace('    yield;','').replace('let r=exchange(v,->incoming);',
            'let r=relay(->exchange(v,->incoming),pause().await);').replace('spawn(->replace(','spawn(->choose(')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'3\n8\n9\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_returned_arm_outlives_other_pool(self):
        helper=f'''fn exchange(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-{REPLACE_RESULT}{{return <-v.replace(INDEX,->incoming);}}
            fn relay(r:->{REPLACE_RESULT})-><-{REPLACE_RESULT}{{return <-r;}}'''
        source=helper+'''async fn take(v:&mut Vector<A<Int>>,incoming:->Int,p:&mut Pool<Int>)-><-Int{
            let r=relay(->exchange(v,->incoming));yield;match (->r){Ok(old)=>{return <-old;},
            Err(rejected)=>{drop(->rejected);let n=p.new(17);return <-n;}}}
            fn main(){let mut p=pool<Int>(2);let r={let mut q=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);
                let mut v=vp.new();v.push(->p.new(7));let next=q.new(8);
                let h=runtime::spawn(->take(&mut v,->next,&mut p));let x=h.join();<-x};
                match r{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}}'''
        for index,expected in ((0,'7\n'),(5,'17\n')):
            self.assertEqual(self.run_source(source.replace('INDEX',str(index))).stdout,expected)
        invalid=source.replace('INDEX','0').replace('v.push(->p.new(7))','v.push(->q.new(7))').replace('pool<Int>(1)','pool<Int>(2)')
        self.refused(invalid, 'pool|source|survi')


    def test_try_push_prepared_argument_cleanup(self):
        helper=f'''async fn pause()->Int{{yield;return 4;}}
            fn relay(r:->{PUSH_RESULT},n:Int)-><-{PUSH_RESULT}{{print(n);return <-r;}}
            async fn ready()->Int{{return 3;}}
            async fn choose(v:&mut Vector<A<Int>>,incoming:->Int)->Int{{
                let mut s=runtime::select(->append(v,->incoming),->ready());let n=s.await;drop(->s);return n;}}'''
        source=helper+APPEND.replace('    yield;','').replace('match <-v.try_push(->incoming)',
            'let r=relay(->v.try_push(->incoming),pause().await);match (->r)')
        for selected in (False,True):
            program=source.replace('spawn(->append(','spawn(->choose(') if selected else source
            for filled in (False,True):
                candidate=full(program) if filled else program
                expected=('3' if selected else '4\n'+('8' if filled else '1'))+'\n'+('1' if filled else '8')+'\n9\n'
                run=self.run_source(candidate)
                self.assertEqual(run.stdout,expected)
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)

    def test_result_requires_explicit_use_and_single_transfer(self):
        start=BASE.index('    let r=exchange')
        end=BASE.index('\n}\nfn main')
        unused=BASE[:start]+'let unused=exchange(v,->incoming);return 0;'+BASE[end:]
        self.refused(unused,'sans usage explicite')
        helper=f'fn consume(r:->{REPLACE_RESULT})->Void{{drop(->r);}}'
        reused=helper+BASE[:start]+'let r=exchange(v,->incoming);consume(->r);drop(->r);return 0;'+BASE[end:]
        self.refused(reused,'consomm|utilisable')


if __name__=='__main__':unittest.main()
