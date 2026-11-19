"""Runtime failure envelopes preserve the owned arms of vector operation results."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure
from test_async_handle_vector_try_push import full

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-exchange-join.crb').read_text()
INNER='Result<A<Int>,A<Int>>'
OUTER='Result<'+INNER+',runtime::Error>'
MATCH='''match h.join(){Ok(inner)=>{match (->inner){
    Ok(n)=>{print(*n);drop(->n);},Err(n)=>{print(*n);drop(->n);}}},Err(_)=>{print(99);}}'''
SOURCE=BASE.replace('let result=h.join();drop(->result);',MATCH)

class AsyncExchangeJoinTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_join_inner_variants_and_launch_failure(self):
        for index,expected in ((0,'7\n8\n9\n'),(5,'8\n7\n9\n')):
            self.assertEqual(self.run_source(SOURCE.replace('v.replace(0,','v.replace('+str(index)+',')).stdout,expected)
        run=self.run_c_oracle(inject_submission_failure(compile_source(SOURCE),asynchronous=False,at=1))
        self.assertEqual(run.stdout,'99\n7\n9\n')
        self.refused(SOURCE.replace('Ok(inner)=>{match (->inner)', 'Ok(inner)=>{match inner'),'consomm|transfert|prototype|type')

    def test_async_handle_await(self):
        helper='''async fn perform(v:&mut Vector<A<Int>>,incoming:->A<Int>)->Int{
            let h=runtime::spawn(->exchange(v,->incoming));match h.await{
                Ok(inner)=>{match (->inner){Ok(n)=>{let value=*n;drop(->n);return value;},
                    Err(n)=>{let value=*n;drop(->n);return value;}}},Err(_)=>{return 99;}}}'''
        source=helper+BASE.replace('spawn(->exchange(', 'spawn(->perform(').replace(
            'let result=h.join();drop(->result);','match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
        self.assertEqual(self.run_source(source).stdout,'7\n8\n9\n')
        run=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=True,at=1))
        self.assertEqual(run.stdout,'99\n7\n9\n')

    def test_public_handle_and_result_helpers(self):
        helpers=f'''fn wait(h:->runtime::Handle<{INNER}>)-><-{OUTER}{{let r=h.join();return <-r;}}
            fn relay(r:->{OUTER})-><-{OUTER}{{return <-r;}}'''
        for expression in ('wait(->h)','relay(->wait(->h))'):
            source=helpers+SOURCE.replace('match h.join()', 'let r='+expression+';match r')
            self.assertEqual(self.run_source(source).stdout,'7\n8\n9\n')
        self.refused(source.replace('wait(->h)','wait(h)'), 'transfert|->')

    def test_named_drop_scope_and_transfer(self):
        for action in ('let r=h.join();drop(->r);',
                       'let r={h ->;let inner=h.join();<-inner};drop(->r);'):
            for index,expected in ((0,'8\n9\n'),(5,'7\n9\n')):
                source=BASE.replace('let result=h.join();drop(->result);',action).replace('v.replace(0,','v.replace('+str(index)+',')
                self.assertEqual(self.run_source(source).stdout,expected)
        self.refused(BASE.replace('drop(->result);',''), 'sans usage explicite')
        self.refused(BASE.replace('drop(->result);','drop(->result);drop(->result);'), 'utilisable|consomm')

    def test_try_push_join_variants(self):
        source=SOURCE.replace(INNER,'Result<(),A<Int>>').replace('v.replace(0,->incoming)','v.try_push(->incoming)').replace(
            'v.push(->p.new(7));','').replace('let next=p.new(8);','let incoming=p.new(8);').replace('->next','->incoming').replace(
            'Ok(n)=>{print(*n);drop(->n);}', 'Ok(())=>{print(1);}')
        # full() uses the compact main spelling shared by the vector fixtures.
        source=source.replace('fn main() {','fn main(){')
        for program,expected in ((source,'1\n8\n9\n'),(full(source),'8\n1\n9\n')):
            self.assertEqual(self.run_source(program).stdout,expected)

    def test_capture_outer_result_and_inactive_cleanup(self):
        helpers=f'async fn consume(r:->{OUTER})->Int{{yield;drop(->r);return 42;}}'
        for active in (False,True):
            action=('let t=consume(->r);drop(->t);' if not active else
                'let e=runtime::spawn(->consume(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
            source=helpers+BASE.replace('let result=h.join();drop(->result);','let r=h.join();'+action)
            for index,remaining in ((0,'8'),(5,'7')):
                run=self.run_source(source.replace('v.replace(0,','v.replace('+str(index)+','))
                self.assertEqual(run.stdout,('42\n' if active else '')+remaining+'\n9\n')
        self.refused(source.replace('let e=runtime::spawn(->consume(->r));','let e=runtime::spawn(->consume(->r));drop(->r);'),'utilisable|consomm|transfert')

    def test_prepared_result_and_select_cleanup(self):
        helpers=f'''fn relay(r:->{OUTER},n:Int)-><-{OUTER}{{print(n);return <-r;}}
            async fn pause()->Int{{yield;return 4;}}
            async fn consume(r:->{OUTER})->Int{{let moved=relay(->r,pause().await);drop(->moved);return 42;}}
            async fn ready()->Int{{return 3;}}
            async fn choose(r:->{OUTER})->Int{{let mut s=runtime::select(->consume(->r),->ready());
                let n=s.await;drop(->s);return n;}}'''
        for callee,expected in (('consume','4\n42\n8\n9\n'),('choose','3\n8\n9\n')):
            source=helpers+BASE.replace('let result=h.join();drop(->result);',
                'let r=h.join();let e=runtime::spawn(->'+callee+'(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
            run=self.run_source(source)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_async_return_of_outer_envelope(self):
        helpers=f'''async fn wrapped(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-{OUTER}{{
            let h=runtime::spawn(->exchange(v,->incoming));return <-h.await;}}
            async fn consume(v:&mut Vector<A<Int>>,incoming:->A<Int>)->Int{{let r=wrapped(v,->incoming).await;
                match r{{Ok(inner)=>{{match (->inner){{Ok(n)=>{{let value=*n;drop(->n);return value;}},
                    Err(n)=>{{let value=*n;drop(->n);return value;}}}}}},Err(_)=>{{return 99;}}}}}}'''
        source=helpers+BASE.replace('spawn(->exchange(', 'spawn(->consume(').replace(
            'let result=h.join();drop(->result);','match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
        factory='fn make(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-wrapped{return <-wrapped(v,->incoming);}'
        for callee in ('wrapped','make'):
            candidate=factory+source.replace('let r=wrapped(v,->incoming).await;', 'let r='+callee+'(v,->incoming).await;')
            for index,expected in ((0,'7\n8\n9\n'),(5,'8\n7\n9\n')):
                self.assertEqual(self.run_source(candidate.replace('v.replace(0,','v.replace('+str(index)+',')).stdout,expected)

    def test_source_pools_and_branch_projection(self):
        helpers='''async fn take(v:&mut Vector<A<Int>>,incoming:->A<Int>,p:&mut Pool<Int>)-><-Int{
            let h=runtime::spawn(->exchange(v,->incoming));match h.await{
            Ok(inner)=>{match (->inner){Ok(old)=>{return <-old;},
                Err(n)=>{drop(->n);let fresh=p.new(17);return <-fresh;}}},
            Err(_)=>{let fresh=p.new(18);return <-fresh;}}}'''
        source=BASE[:BASE.index('fn main()')]+helpers+'''fn main(){let mut p=pool<Int>(2);
            let result={let mut q=pool<Int>(2);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
                v.push(->p.new(7));let incoming=q.new(8);let h=runtime::spawn(->take(&mut v,->incoming,&mut p));
                let r=h.join();<-r};match result{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('v.push(->p.new(7))','v.push(->q.new(7))'),'pool|source|survi')

    def test_outer_envelope_branch_and_loop(self):
        for expression in ('if true{h ->;let x=h.join();<-x}else{h ->;let x=h.join();<-x}',
                           'loop{h ->;let x=h.join();break <-x;}'):
            source=SOURCE.replace('match h.join()', 'let r='+expression+';match r')
            self.assertEqual(self.run_source(source).stdout,'7\n8\n9\n')
        self.refused(SOURCE.replace('Ok(inner)=>{match (->inner){\n    Ok(n)=>{print(*n);drop(->n);},Err(n)=>{print(*n);drop(->n);}}}', 'Ok(_)=>{}'), 'motif|propriétaire|usage')

    def test_try_push_outer_drop_and_capture(self):
        inner='Result<(),A<Int>>'
        outer='Result<'+inner+',runtime::Error>'
        source=BASE.replace(INNER,inner).replace('v.replace(0,->incoming)','v.try_push(->incoming)').replace(
            'v.push(->p.new(7));','').replace('let next=p.new(8);','let incoming=p.new(8);').replace('->next','->incoming').replace('fn main() {','fn main(){')
        helpers=f'''fn relay(r:->{outer})-><-{outer}{{return <-r;}}
            async fn consume(r:->{outer})->Int{{yield;drop(->r);return 42;}}'''
        for filled in (False,True):
            program=helpers+(full(source) if filled else source)
            remaining='1' if filled else '8'
            for action,prefix in (('let r=relay(->h.join());drop(->r);',''),
                                 ('let r=h.join();let t=consume(->r);drop(->t);',''),
                                 ('let r=h.join();let e=runtime::spawn(->consume(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}','42\n')):
                run=self.run_source(program.replace('let result=h.join();drop(->result);',action))
                self.assertEqual(run.stdout,prefix+remaining+'\n9\n')
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)
        run=self.run_c_oracle(inject_submission_failure(compile_source(full(source)),asynchronous=False,at=1))
        self.assertEqual(run.stdout,'1\n9\n')

if __name__=='__main__':unittest.main()
