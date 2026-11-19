"""Runtime wrappers preserve typed owned results through arbitrary nesting."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure
from test_async_awaited_owned_results import FAMILIES

ACTION='let result=h.join();drop(->result);'


def envelope(depth, leaf='A<Int>'):
    for _ in range(depth):
        leaf=f'Result<{leaf},runtime::Error>'
    return leaf


def definitions(depth, typ='Int'):
    source=f'async fn work(n:->A<{typ}>)-><-A<{typ}>{{yield;return <-n;}}'
    previous='work'
    for level in range(1,depth):
        name=f'wrapped{level}'
        source+=f'async fn {name}(n:->A<{typ}>)-><-{envelope(level,"A<"+typ+">")}{{let h=runtime::spawn(->{previous}(->n));return <-h.await;}}'
        previous=name
    return source


def program(depth):
    return definitions(depth)+f'''fn main(){{let mut p=pool<Int>(1);let n=p.new(7);
        let h=runtime::spawn(->wrapped{depth-1}(->n));{ACTION}
        let next=p.new(8);print(*next);}}'''


def inspect(depth, expression='h.join()', read='print(*value);'):
    body=read+'drop(->value);'
    for level in range(depth):
        child='value' if level==0 else f'inner{level}'
        receiver=expression if level==depth-1 else f'inner{level+1}'
        body=f'match {receiver}{{Ok({child})=>{{{body}}},Err(_)=>{{print({90+level});}}}}'
    return body


class RecursiveOwnedJoinTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_depths_and_each_launch_failure(self):
        for depth in (3,5):
            source=program(depth).replace(ACTION,inspect(depth))
            self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        code=compile_source(program(3).replace(ACTION,inspect(3)))
        for asynchronous,at,tag in ((False,1,92),(True,1,91),(True,2,90)):
            run=self.run_c_oracle(inject_submission_failure(code,asynchronous=asynchronous,at=at))
            self.assertEqual(run.stdout,f'{tag}\n8\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_public_handle_and_sync_result_contract(self):
        helpers=f'''fn wait(h:->runtime::Handle<{envelope(2)}>)-><-{envelope(3)}{{return <-h.join();}}
            fn relay(r:->{envelope(3)})-><-{envelope(3)}{{return <-r;}}'''
        source=helpers+program(3).replace(ACTION,'let r=relay(->wait(->h));'+inspect(3,'r'))
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        self.refused(source.replace('wait(->h)','wait(h)'),'transfert|->')

    def test_async_extraction_and_factory(self):
        for expression in ('h.await','make(->n).await','child.await'):
            helper=f'''fn make(n:->A<Int>)-><-wrapped3{{return <-wrapped3(->n);}}
                async fn consume(n:->A<Int>)->Int{{PREPARE {inspect(3,expression)}return 42;}}'''.replace(
                    'PREPARE','let h=runtime::spawn(->wrapped2(->n));' if expression=='h.await' else 'let child=make(->n);' if expression=='child.await' else '')
            main=program(3)[program(3).index('fn main()'):].replace('spawn(->wrapped2(->n))','spawn(->consume(->n))')
            source=definitions(4)+helper+main.replace(ACTION,'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
            self.assertEqual(self.run_source(source).stdout,'7\n42\n8\n')

    def test_typed_payloads(self):
        for typ,fill,read in FAMILIES:
            source=definitions(3,typ)+f'''fn main(){{let mut p=pool<{typ}>(1);{fill.replace('value','n')}
                let h=runtime::spawn(->wrapped2(->n));{inspect(3,read=read)}
                let next=p.new();drop(->next);}}'''
            with self.subTest(typ=typ):
                self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_capture_pending_cleanup_and_select(self):
        helpers=f'''async fn dispose(r:->{envelope(3)})->Int{{yield;drop(->r);return 42;}}
            fn relay(r:->{envelope(3)},n:Int)-><-{envelope(3)}{{print(n);return <-r;}}
            async fn pause()->Int{{yield;return 4;}}
            async fn pending(r:->{envelope(3)})->Int{{let moved=relay(->r,pause().await);drop(->moved);return 42;}}
            async fn ready()->Int{{return 3;}}
            async fn choose(r:->{envelope(3)})->Int{{let mut s=runtime::select(->pending(->r),->ready());let n=s.await;drop(->s);return n;}}'''
        for action,expected in (
            ('let t=dispose(->r);drop(->t);','8\n'),
            ('let e=runtime::spawn(->dispose(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}','42\n8\n'),
            ('let e=runtime::spawn(->choose(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}','3\n8\n')):
            source=helpers+program(3).replace(ACTION,'let r=h.join();'+action)
            run=self.run_source(source)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)
        self.refused(source.replace('let e=runtime::spawn(->choose(->r));','let e=runtime::spawn(->choose(->r));drop(->r);'),'consomm|utilisable|transfert')

    def test_branches_usage_and_source_lifetime(self):
        for expression in ('if true{h ->;let x=h.join();<-x}else{h ->;let x=h.join();<-x}',
                           'loop{h ->;let x=h.join();break <-x;}'):
            self.assertEqual(self.run_source(program(3).replace(ACTION,'let r='+expression+';drop(->r);')).stdout,'8\n')
        source=program(3)
        self.refused(source.replace('drop(->result);',''),'sans usage explicite')
        self.refused(source.replace('drop(->result);','drop(->result);drop(->result);'),'consomm|utilisable')
        self.refused(source.replace(ACTION,'match h.join(){Ok(_)=>{},Err(_)=>{}}'),'motif|propriétaire|usage')
        invalid=definitions(3)+'''fn main(){let result={let mut p=pool<Int>(1);let n=p.new(7);
            let h=runtime::spawn(->wrapped2(->n));let r=h.join();<-r};drop(->result);}'''
        self.refused(invalid,'pool|source|survi')

    def test_local_carrier_keeps_borrow_and_storage_kind(self):
        prefix='''struct View{data:&Int}fn wrap(n:&Int)-><-View{let v=View{data:n};return <-v;}
            async fn work(n:&Int)-><-View{let v=wrap(n);yield;return <-v;}'''
        previous='work'
        for level in range(1,3):
            prefix+=f'''async fn wrapped{level}(n:&Int)-><-{envelope(level,'View')}{{
                let h=runtime::spawn(->{previous}(n));return <-h.await;}}'''
            previous=f'wrapped{level}'
        source=prefix+'''fn main(){let mut p=pool<Int>(1);let n=p.new(7);let h=runtime::spawn(->wrapped2(&n));
            OBSERVE drop(->n);let next=p.new(8);print(*next);}'''.replace('OBSERVE',inspect(3,read='print(*value.data);'))
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        self.refused(source.replace('print(*value.data);','drop(->n);print(*value.data);'),'emprunt|réserv|référenc')
        self.refused(source.replace(envelope(2,'View'),envelope(2,'A<View>')),'stockage|local|A<T>')

if __name__=='__main__':unittest.main()
