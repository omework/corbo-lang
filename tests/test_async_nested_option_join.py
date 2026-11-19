"""Repeated runtime waits preserve Some/None and the original pool lifetime."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

BASE = (Path(__file__).resolve().parents[1] / 'validation/open-async-option-join.crb').read_text()
ACTION = 'let result=h.join();drop(->result);'


def envelope(depth):
    typ = 'Option<A<Int>>'
    for _ in range(depth):
        typ = f'Result<{typ},runtime::Error>'
    return typ


def program(depth, *, some=True):
    source = BASE[:BASE.index('fn main()')]
    previous = 'extract'
    for level in range(1, depth):
        name = f'wrapped{level}'
        source += f'''async fn {name}(v:&mut Vector<A<Int>>)-><-{envelope(level)}{{
            let h=runtime::spawn(->{previous}(v));return <-h.await;}}\n'''
        previous = name
    source += '''fn main(){let mut p=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
        v.push(->p.new(7));let h=runtime::spawn(->CALLEE(&mut v));ACTION
        drop(->v);let next=p.new(8);print(*next);}'''.replace('CALLEE', previous).replace('ACTION', ACTION)
    return source if some else source.replace('v.push(->p.new(7));', '')


def inspect(depth, expression='h.join()'):
    body = 'match (->option){Some(n)=>{print(*n);drop(->n);},None=>{print(0);}}'
    for level in range(depth):
        child = 'option' if level == 0 else f'inner{level}'
        receiver = expression if level == depth - 1 else f'inner{level+1}'
        body = f'match {receiver}{{Ok({child})=>{{{body}}},Err(_)=>{{print({90+level});}}}}'
    return body


class AsyncNestedOptionJoinTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_depths_some_none_and_runtime_extraction(self):
        for depth in (2, 3, 5):
            for some in (False, True):
                with self.subTest(depth=depth, some=some):
                    source = program(depth, some=some).replace(ACTION, inspect(depth))
                    self.assertEqual(self.run_source(source).stdout, ('7' if some else '0')+'\n8\n')

    def test_each_launch_failure_layer(self):
        for some in (False, True):
            code = compile_source(program(3, some=some).replace(ACTION, inspect(3)))
            for asynchronous, at, tag in ((False, 1, 92), (True, 1, 91), (True, 2, 90)):
                run = self.run_c_oracle(inject_submission_failure(code, asynchronous=asynchronous, at=at))
                self.assertEqual(run.stdout, f'{tag}\n8\n')
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()), int(some))

    def test_public_handle_and_sync_relay(self):
        helpers = f'''fn wait(h:->runtime::Handle<{envelope(2)}>)-><-{envelope(3)}{{return <-h.join();}}
            fn relay(r:->{envelope(3)})-><-{envelope(3)}{{return <-r;}}'''
        for some in (False, True):
            source = helpers + program(3, some=some).replace(ACTION, 'let r=relay(->wait(->h));'+inspect(3, 'r'))
            self.assertEqual(self.run_source(source).stdout, ('7' if some else '0')+'\n8\n')
        self.refused(source.replace('wait(->h)', 'wait(h)'), 'transfert|->')

    def test_async_extraction_and_inactive_factory_result(self):
        for expression in ('h.await', 'make(v).await'):
            helper = f'''fn make(v:&mut Vector<A<Int>>)-><-wrapped3{{return <-wrapped3(v);}}
                async fn consume(v:&mut Vector<A<Int>>)->Int{{PREPARE
                {inspect(3, expression)}return 42;}}'''.replace('PREPARE',
                'let h=runtime::spawn(->wrapped2(v));' if expression == 'h.await' else '')
            definitions = program(4)[:program(4).index('fn main()')]
            main = program(3)[program(3).index('fn main()'):].replace('spawn(->wrapped2(&mut v))', 'spawn(->consume(&mut v))')
            source = definitions + helper + main.replace(ACTION, 'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}')
            self.assertEqual(self.run_source(source).stdout, '7\n42\n8\n')

    def test_capture_drop_select_and_slot_reuse(self):
        helpers = f'''async fn dispose(r:->{envelope(3)})->Int{{yield;drop(->r);return 42;}}
            fn relay(r:->{envelope(3)},n:Int)-><-{envelope(3)}{{print(n);return <-r;}}
            async fn pause()->Int{{yield;return 4;}}
            async fn pending(r:->{envelope(3)})->Int{{let moved=relay(->r,pause().await);drop(->moved);return 42;}}
            async fn ready()->Int{{return 3;}}
            async fn choose(r:->{envelope(3)})->Int{{let mut s=runtime::select(->pending(->r),->ready());let n=s.await;drop(->s);return n;}}'''
        for some in (False, True):
            for action, expected in (
                ('let t=dispose(->r);drop(->t);', '8\n'),
                ('let e=runtime::spawn(->dispose(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}', '42\n8\n'),
                ('let e=runtime::spawn(->choose(->r));match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}', '3\n8\n')):
                source = helpers + program(3, some=some).replace(ACTION, 'let r=h.join();'+action)
                run = self.run_source(source)
                self.assertEqual(run.stdout, expected)
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()), int(some))
        self.refused(source.replace('let e=runtime::spawn(->choose(->r));', 'let e=runtime::spawn(->choose(->r));drop(->r);'), 'consomm|utilisable|transfert')

    def test_branch_loop_and_explicit_consumption(self):
        source = program(3)
        for expression in ('if true{h ->;let x=h.join();<-x}else{h ->;let x=h.join();<-x}',
                           'loop{h ->;let x=h.join();break <-x;}'):
            self.assertEqual(self.run_source(source.replace(ACTION, 'let r='+expression+';drop(->r);')).stdout, '8\n')
        self.refused(source.replace('drop(->result);', ''), 'sans usage explicite')
        self.refused(source.replace('drop(->result);', 'drop(->result);drop(->result);'), 'consomm|utilisable')
        self.refused(source.replace(ACTION, 'match h.join(){Ok(_)=>{},Err(_)=>{}}'), 'motif|propriétaire|usage')
        self.refused(source.replace(ACTION, 'print(v.len());'+ACTION), 'emprunt|utilisable|réserv')

    def test_pool_lifetime_with_nested_optional_payload(self):
        definitions = program(3)[:program(3).index('fn main()')]
        main = '''fn main(){let mut p=pool<Int>(1);let result={
            let mut q=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
            v.push(->p.new(7));let h=runtime::spawn(->wrapped2(&mut v));
            let r=h.join();<-r};OBSERVE let next=p.new(8);print(*next);}'''.replace('OBSERVE', inspect(3, 'result'))
        source = definitions + main
        self.assertEqual(self.run_source(source).stdout, '7\n8\n')
        self.refused(source.replace('v.push(->p.new(7))', 'v.push(->q.new(7))'), 'pool|source|survi')

if __name__ == '__main__':
    unittest.main()
