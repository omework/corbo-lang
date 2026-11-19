"""Typed async vector exchanges retain arm-specific ownership through waits."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure
from test_typed_vector_exchanges import filled

LEAF = 'Result<A<Point>,A<Point>>'
PUSH = 'Result<(),A<Point>>'
ACTION = 'let result=h.join();drop(->result);'
READ = 'match (->leaf){Ok(n)=>{print(n.x);drop(->n);},Err(n)=>{print(n.x);drop(->n);}}'


def envelope(depth, leaf=LEAF):
    for _ in range(depth):
        leaf=f'Result<{leaf},runtime::Error>'
    return leaf


def inspect(depth, expression='h.join()', insertion=False):
    body=('match (->leaf){Ok(())=>{print(1);},Err(n)=>{print(n.x);drop(->n);}}' if insertion else READ)
    for level in range(depth):
        child='leaf' if level==0 else f'inner{level}'
        receiver=expression if level==depth-1 else f'inner{level+1}'
        body=f'match {receiver}{{Ok({child})=>{{{body}}},Err(_)=>{{print({90+level});}}}}'
    return body


def program(depth=1,index=0):
    source=f'''struct Point{{x:Int}}
        async fn exchange(v:&mut Vector<A<Point>>,incoming:->A<Point>)-><-{LEAF}{{
            yield;let r=<-v.replace({index},->incoming);yield;return <-r;}}'''
    previous='exchange'
    for level in range(1,depth):
        name=f'wrapped{level}'
        source+=f'''async fn {name}(v:&mut Vector<A<Point>>,incoming:->A<Point>)-><-{envelope(level)}{{
            let h=runtime::spawn(->{previous}(v,->incoming));return <-h.await;}}'''
        previous=name
    source+=f'''fn main(){{let mut p=pool<Point>(1);let mut q=pool<Point>(1);
        let mut vp=pool<Vector<A<Point>>>(1);let mut v=vp.new();v.push(->p.new(x:7));
        let incoming=q.new(x:9);let h=runtime::spawn(->{previous}(&mut v,->incoming));{ACTION}
        let resident=<-v.remove(0);print(resident.x);drop(->resident);drop(->v);
        let a=p.new(x:11);let b=q.new(x:12);print(a.x);print(b.x);}}'''
    return source


class TypedAsyncExchangeTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_recorded_and_nested_both_arms(self):
        recorded=Path(__file__).resolve().parents[1].joinpath('validation/open-typed-async-vector-exchange.crb').read_text()
        self.assertEqual(self.run_source(recorded).stdout,'7\n8\n9\n')
        for depth in (1,3):
            for index,expected in ((0,'7\n9\n11\n12\n'),(4,'9\n7\n11\n12\n')):
                run=self.run_source(program(depth,index).replace(ACTION,inspect(depth)))
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('=Point\n'),4)
        self.refused(program().replace('return <-r;','return r;'),'explicite|transfert|<-')

    def test_direct_await_and_sync_async_relays(self):
        helpers=f'''fn relay(r:->{LEAF})-><-{LEAF}{{return <-r;}}
            async fn forward(r:->{LEAF})-><-{LEAF}{{yield;return <-r;}}
            fn make(v:&mut Vector<A<Point>>,incoming:->A<Point>)-><-exchange{{return <-exchange(v,->incoming);}}
            async fn work(v:&mut Vector<A<Point>>,incoming:->A<Point>)->Int{{
                let t=make(v,->incoming);let initial=t.await;
                let leaf:{LEAF}=relay(->forward(->initial).await);yield;{READ}return 42;}}'''
        for index,expected in ((0,'7\n42\n9\n11\n12\n'),(4,'9\n42\n7\n11\n12\n')):
            source=helpers+program(index=index).replace('spawn(->exchange(&mut v','spawn(->work(&mut v').replace(
                ACTION,'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
            self.assertEqual(self.run_source(source).stdout,expected)
            self.refused(source.replace('let leaf:'+LEAF,'let leaf:Result<A<Int>,A<Int>>'),'annotation|type')
        self.refused(source.replace('forward(->initial)','forward(initial)'),'transfert|->')

    def test_public_handle_and_nested_capture(self):
        helpers=f'''fn wait(h:->runtime::Handle<{envelope(2)}>)-><-{envelope(3)}{{return <-h.join();}}
            fn relay(r:->{envelope(3)})-><-{envelope(3)}{{return <-r;}}
            async fn forward(r:->{envelope(3)})-><-{envelope(3)}{{yield;return <-r;}}
            async fn work(r:->{envelope(3)})->Int{{let saved=forward(->r).await;{inspect(3,'saved')}return 42;}}'''
        for index,expected in ((0,'7\n42\n9\n11\n12\n'),(4,'9\n42\n7\n11\n12\n')):
            source=helpers+program(3,index).replace(ACTION,
                'let r=relay(->wait(->h));let e=runtime::spawn(->work(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
            self.assertEqual(self.run_source(source).stdout,expected)
        self.refused(source.replace('wait(->h)','wait(h)'),'transfert|->')

    def test_launch_failure_at_each_layer(self):
        code=compile_source(program(3).replace(ACTION,inspect(3)))
        for asynchronous,at,tag in ((False,1,92),(True,1,91),(True,2,90)):
            run=self.run_c_oracle(inject_submission_failure(code,asynchronous=asynchronous,at=at))
            self.assertEqual(run.stdout,f'{tag}\n7\n11\n12\n')
            self.assertEqual(run.stderr.count('=Point\n'),4)

    def test_capture_drop_inactive_and_failed_launch(self):
        helper=f'async fn consume(r:->{LEAF})->Int{{print(77);yield;drop(->r);return 42;}}'
        for index,resident in ((0,9),(4,7)):
            source=helper+program(index=index).replace('let h=runtime::spawn(->exchange(&mut v,->incoming));'+ACTION,
                f'let r=<-v.replace({index},->incoming);let t=consume(->r);drop(->t);')
            run=self.run_source(source)
            self.assertEqual(run.stdout,f'{resident}\n11\n12\n')
            self.assertEqual(run.stderr.count('=Point\n'),4)
            launched=source.replace('drop(->t);','let h=runtime::spawn(->t);match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
            run=self.run_c_oracle(inject_submission_failure(compile_source(launched),asynchronous=False,at=1))
            self.assertEqual(run.stdout,f'99\n{resident}\n11\n12\n')
            self.assertEqual(run.stderr.count('=Point\n'),4)
            self.refused(source.replace('consume(r:->'+LEAF,'consume(r:->Result<A<Int>,A<Int>>'), 'type|attend|Int')
            self.refused(source.replace('drop(->t);','drop(->t);drop(->r);'), 'consomm|utilis|transfert')

    def test_try_push_success_full_and_relay(self):
        helpers=f'''struct Point{{x:Int}}
            async fn insert(v:&mut Vector<A<Point>>,incoming:->A<Point>)-><-{PUSH}{{yield;return <-v.try_push(->incoming);}}
            fn relay(r:->{PUSH})-><-{PUSH}{{return <-r;}}
            async fn forward(r:->{PUSH})-><-{PUSH}{{yield;return <-r;}}
            async fn work(v:&mut Vector<A<Point>>,incoming:->A<Point>)-><-{PUSH}{{
                let first=insert(v,->incoming).await;let r=relay(->forward(->first).await);return <-r;}}'''
        main='''fn main(){let mut p=pool<Point>(1);let mut vp=pool<Vector<A<Point>>>(1);let mut v=vp.new();
            let incoming=p.new(x:9);let h=runtime::spawn(->work(&mut v,->incoming));ACTION
            let first=<-v.remove(0);print(first.x);drop(->first);drop(->v);
            let next=p.new(x:11);print(next.x);}'''.replace('ACTION',inspect(1,insertion=True))
        source=helpers+main
        for candidate,expected in ((source,'1\n9\n11\n'),(filled(source),'9\n1\n11\n')):
            self.assertEqual(self.run_source(candidate).stdout,expected)
        # A successful Result<(),A<Point>> is still typed and must be consumed.
        ignored=source.replace(inspect(1,insertion=True), 'let ignored=h.join();')
        self.refused(ignored, 'sans usage explicite')
        self.refused(source.replace('try_push(->incoming)','try_push(incoming)'), 'transfert|->')

    def test_try_push_capture_cleanup_and_select_loser(self):
        helpers=f'''struct Point{{x:Int}}
            async fn dispose(r:->{PUSH})->Int{{print(77);yield;drop(->r);return 42;}}
            async fn pending(r:->{PUSH})->Int{{yield;drop(->r);return 42;}}
            async fn ready()->Int{{return 3;}}
            async fn choose(r:->{PUSH})->Int{{let mut s=runtime::select(->pending(->r),->ready());
                let n=s.await;drop(->s);return n;}}'''
        main='''fn main(){let mut p=pool<Point>(1);let mut vp=pool<Vector<A<Point>>>(1);let mut v=vp.new();
            let incoming=p.new(x:9);let r=<-v.try_push(->incoming);ACTION
            let first=<-v.remove(0);print(first.x);drop(->first);drop(->v);
            let next=p.new(x:11);print(next.x);}'''
        for action,prefix in (
            ('let task=dispose(->r);drop(->task);',''),
            ('let h=runtime::spawn(->choose(->r));match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}','3\n'),
        ):
            source=helpers+main.replace('ACTION',action)
            for candidate,first in ((source,9),(filled(source),1)):
                self.assertEqual(self.run_source(candidate).stdout,prefix+f'{first}\n11\n')

    def test_growing_payloads(self):
        for typ,fill,read,expected in (
            ('String','item.push_str("été");','print(&item[..]);','été\n'),
            ('Vector<Int>','item.push(7);','print(item[0]);','7\n'),
            ('Vector<u8>','let byte:u8=7;item.push(byte);','print(item[0] as Int);','7\n'),
        ):
            leaf=f'Result<A<{typ}>,A<{typ}>>'
            source=f'''async fn take(v:&mut Vector<A<{typ}>>,n:->A<{typ}>)-><-{leaf}{{yield;return <-v.replace(0,->n);}}
                async fn forward(r:->{leaf})-><-{leaf}{{yield;return <-r;}}
                async fn work(v:&mut Vector<A<{typ}>>,n:->A<{typ}>)->Int{{
                    let initial=take(v,->n).await;let result=forward(->initial).await;
                    match (->result){{Ok(item)=>{{{read}drop(->item);}},Err(item)=>{{{read}drop(->item);}}}}return 1;}}
                fn main(){{let mut p=pool<{typ}>(2);let mut vp=pool<Vector<A<{typ}>>>(1);let mut v=vp.new();
                    let mut item=p.new();{fill}v.push(->item);let next=p.new();
                    let h=runtime::spawn(->work(&mut v,->next));match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(99);}}}}
                    drop(->v);let a=p.new();let b=p.new();drop(->a);drop(->b);}}'''
            self.assertEqual(self.run_source(source).stdout,expected+'1\n')

    def test_pool_lifetimes_borrows_and_consumption(self):
        source=program(3)
        self.refused(source.replace(ACTION,'print(v.len());'+ACTION),'emprunt|réserv')
        self.refused(source.replace('drop(->result);',''),'sans usage explicite')
        self.refused(source.replace('drop(->result);','drop(->result);drop(->result);'),'consomm|utilis')
        definitions=source.split('fn main()')[0]
        main='''fn main(){let mut p=pool<Point>(1);let mut q=pool<Point>(1);let result={
            let mut short=pool<Point>(1);let mut vp=pool<Vector<A<Point>>>(1);let mut v=vp.new();
            v.push(->p.new(x:7));let incoming=q.new(x:9);let h=runtime::spawn(->wrapped2(&mut v,->incoming));
            let r=h.join();<-r};OBSERVE
            let a=p.new(x:11);let b=q.new(x:12);print(a.x);print(b.x);}'''.replace('OBSERVE',inspect(3,'result'))
        self.assertEqual(self.run_source(definitions+main).stdout,'7\n11\n12\n')
        self.refused(definitions+main.replace('incoming=q.new','incoming=short.new'),'pool|source|survi')


if __name__=='__main__':unittest.main()
