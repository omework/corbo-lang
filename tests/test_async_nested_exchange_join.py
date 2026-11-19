"""Repeated waits preserve vector-result ownership through runtime envelopes."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure
from test_async_handle_vector_try_push import full

BASE = (Path(__file__).resolve().parents[1] / 'validation/open-async-nested-exchange-join.crb').read_text()
LEAF = 'Result<A<Int>,A<Int>>'
ACTION = 'let result=h.join();drop(->result);'


def envelope(depth, leaf=LEAF):
    for _ in range(depth):
        leaf = f'Result<{leaf},runtime::Error>'
    return leaf


def program(depth, *, insertion=False):
    leaf = 'Result<(),A<Int>>' if insertion else LEAF
    source = BASE[:BASE.index('async fn wrapped')].replace(LEAF, leaf)
    if insertion:
        source = source.replace('v.replace(0,->incoming)', 'v.try_push(->incoming)')
    previous = 'exchange'
    for level in range(1, depth):
        name = f'wrapped{level}'
        source += f'''async fn {name}(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-{envelope(level, leaf)}{{
            let h=runtime::spawn(->{previous}(v,->incoming));return <-h.await;}}\n'''
        previous = name
    source += BASE[BASE.index('fn main()'):].replace('wrapped(&mut', previous+'(&mut')
    if insertion:
        source = source.replace('fn main() {', 'fn main(){').replace('v.push(->p.new(7));', '').replace(
            'let next=p.new(8);', 'let incoming=p.new(8);').replace('->next', '->incoming')
    return source


def inspect(depth, *, insertion=False, expression='h.join()'):
    success = 'print(1);' if insertion else 'print(*n);drop(->n);'
    body = ('match (->leaf){Ok(())=>{'+success+'},Err(n)=>{print(*n);drop(->n);}}' if insertion else
            'match (->leaf){Ok(n)=>{'+success+'},Err(n)=>{print(*n);drop(->n);}}')
    for level in range(depth):
        child = 'leaf' if level == 0 else f'inner{level}'
        receiver = expression if level == depth - 1 else f'inner{level+1}'
        body = f'match {receiver}{{Ok({child})=>{{{body}}},Err(_)=>{{print({90+level});}}}}'
    return body


class AsyncNestedExchangeJoinTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_depths_and_both_vector_arms(self):
        for depth in (2, 3, 5):
            for index, expected in ((0, '7\n8\n9\n'), (5, '8\n7\n9\n')):
                with self.subTest(depth=depth, index=index):
                    source = program(depth).replace(ACTION, inspect(depth)).replace('v.replace(0,', f'v.replace({index},')
                    self.assertEqual(self.run_source(source).stdout, expected)

    def test_launch_failure_at_each_layer(self):
        depth = 3
        c = compile_source(program(depth).replace(ACTION, inspect(depth)))
        for asynchronous, at, tag in ((False, 1, 92), (True, 1, 91), (True, 2, 90)):
            with self.subTest(asynchronous=asynchronous, at=at):
                run = self.run_c_oracle(inject_submission_failure(c, asynchronous=asynchronous, at=at))
                self.assertEqual(run.stdout, f'{tag}\n7\n9\n')
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()), 1)

    def test_public_handles_and_relay(self):
        depth = 3
        helper = f'''fn wait(h:->runtime::Handle<{envelope(depth-1)}>)-><-{envelope(depth)}{{
            let r=h.join();return <-r;}}
            fn relay(r:->{envelope(depth)})-><-{envelope(depth)}{{return <-r;}}'''
        source = helper + program(depth).replace(ACTION, 'let r=relay(->wait(->h));'+inspect(depth, expression='r'))
        self.assertEqual(self.run_source(source).stdout, '7\n8\n9\n')
        self.refused(source.replace('wait(->h)', 'wait(h)'), 'transfert|->')

    def test_async_extraction_and_return(self):
        depth = 3
        helper = f'''async fn consume(v:&mut Vector<A<Int>>,incoming:->A<Int>)->Int{{
            let h=runtime::spawn(->wrapped2(v,->incoming));
            {inspect(depth, expression='h.await')} return 42;}}'''
        source = helper + program(depth).replace('spawn(->wrapped2(&mut', 'spawn(->consume(&mut').replace(
            ACTION, 'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
        self.assertEqual(self.run_source(source).stdout, '7\n42\n8\n9\n')

    def test_capture_drop_and_prepared_select_cleanup(self):
        depth = 3
        helpers = f'''async fn dispose(r:->{envelope(depth)})->Int{{yield;drop(->r);return 42;}}
            fn relay(r:->{envelope(depth)},n:Int)-><-{envelope(depth)}{{print(n);return <-r;}}
            async fn pause()->Int{{yield;return 4;}}
            async fn pending(r:->{envelope(depth)})->Int{{let moved=relay(->r,pause().await);drop(->moved);return 42;}}
            async fn ready()->Int{{return 3;}}
            async fn choose(r:->{envelope(depth)})->Int{{let mut s=runtime::select(->pending(->r),->ready());let n=s.await;drop(->s);return n;}}'''
        for action, expected in (
            ('let t=dispose(->r);drop(->t);', '8\n9\n'),
            ('let e=runtime::spawn(->dispose(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}', '42\n8\n9\n'),
            ('let e=runtime::spawn(->choose(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}', '3\n8\n9\n')):
            with self.subTest(action=action):
                source = helpers + program(depth).replace(ACTION, 'let r=h.join();'+action)
                run = self.run_source(source)
                self.assertEqual(run.stdout, expected)
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()), 1)
        self.refused(source.replace('let e=runtime::spawn(->choose(->r));', 'let e=runtime::spawn(->choose(->r));drop(->r);'), 'consomm|utilisable|transfert')

    def test_try_push_payload_presence(self):
        depth = 3
        for filled in (False, True):
            source = program(depth, insertion=True).replace(ACTION, inspect(depth, insertion=True))
            if filled:
                source = full(source)
            self.assertEqual(self.run_source(source).stdout, '8\n1\n9\n' if filled else '1\n8\n9\n')
            outer = envelope(depth, 'Result<(),A<Int>>')
            helper = f'async fn dispose(r:->{outer})->Int{{yield;drop(->r);return 42;}}'
            source = program(depth, insertion=True).replace(ACTION, 'let r=h.join();let t=dispose(->r);drop(->t);')
            run = self.run_source(helper + (full(source) if filled else source))
            self.assertEqual(run.stdout, '1\n9\n' if filled else '8\n9\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()), 1)

    def test_separate_source_pools_survive_projection(self):
        source = program(3)
        definitions = source[:source.index('fn main()')]
        selected = 'match (->leaf){Ok(old)=>{return <-old;},Err(n)=>{drop(->n);let fresh=p.new(17);return <-fresh;}}'
        for level in range(3):
            child = 'leaf' if level == 0 else f'inner{level}'
            receiver = 'h.await' if level == 2 else f'inner{level+1}'
            selected = f'match {receiver}{{Ok({child})=>{{{selected}}},Err(_)=>{{let fresh=p.new(18);return <-fresh;}}}}'
        definitions += 'async fn take(v:&mut Vector<A<Int>>,incoming:->A<Int>,p:&mut Pool<Int>)-><-Int{let h=runtime::spawn(->wrapped2(v,->incoming));'+selected+'}'
        source = definitions + '''fn main(){let mut p=pool<Int>(2);
            let result={let mut q=pool<Int>(2);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
                v.push(->p.new(7));let incoming=q.new(8);let h=runtime::spawn(->take(&mut v,->incoming,&mut p));
                let r=h.join();<-r};match result{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.refused(source.replace('v.push(->p.new(7))', 'v.push(->q.new(7))'), 'pool|source|survi')

    def test_explicit_usage_and_branch_transfer(self):
        source = program(3)
        for expr in ('if true{h ->;let x=h.join();<-x}else{h ->;let x=h.join();<-x}',
                     'loop{h ->;let x=h.join();break <-x;}'):
            self.assertEqual(self.run_source(source.replace(ACTION, 'let r='+expr+';drop(->r);')).stdout, '8\n9\n')
        self.refused(source.replace('drop(->result);', ''), 'sans usage explicite')
        self.refused(source.replace('drop(->result);', 'drop(->result);drop(->result);'), 'consomm|utilisable')
        self.refused(source.replace(ACTION, 'match h.join(){Ok(_)=>{},Err(_)=>{}}'), 'motif|propriétaire|usage')

if __name__ == '__main__':
    unittest.main()
