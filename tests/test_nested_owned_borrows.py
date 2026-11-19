"""Borrowed descendants remain reachable through every owned edge."""
from pathlib import Path
from itertools import product
import unittest
import test_select_source as sources
import test_native_blocks as native
import test_async_local_parent as placement

ROOT = Path(__file__).resolve().parents[1]
TYPES = 'struct Inner{view:&Int}struct Outer{inner:A<Inner>}'
PREFIX = TYPES + '''async fn consume(v:->Outer)->Int{yield;drop(->v);return 1;}
fn make(v:->Outer)-><-consume{return <-consume(->v);}
fn again(t:->consume)-><-consume{return <-t;}'''
SETUP = '''let mut ns=pool<Int>(1);let n=ns.new(9);
let mut ins=pool<Inner>(1);let mut outs=pool<Outer>(1);
let inner=ins.new(view:&n);let outer=outs.new(inner:<-inner);'''


class NestedOwnedBorrowTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    run_native = native.NativeBlockTests.run_native
    storage_probe = placement.AsyncLocalParentTests.storage_probe

    @staticmethod
    def program(body, prefix=PREFIX):
        return prefix + 'async fn work()->Int{' + body + '''}
fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_capture_and_early_drop(self):
        source = (ROOT/'validation/open-nested-owned-borrowed-capture.crb').read_text()
        self.assertEqual(self.run_source(source).stdout, '1\n')
        invalid = source.replace('    drop(->number);', '').replace(
            '    match handle.join()', '    drop(->number);\n    match handle.join()')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_factories_and_task_relay(self):
        for call in ('consume(->outer)', 'make(->outer)'):
            body = SETUP + 'let t=' + call + ';yield;let result=t.await;drop(->n);return result;'
            with self.subTest(call=call):
                run = self.run_source(self.program(body))
                self.assertEqual(run.stdout, '1\n')
                self.assertEqual(run.stderr.count('=Inner\n'), 1)
                self.assertEqual(run.stderr.count('=Outer\n'), 1)
                invalid = body.replace('drop(->n);', '').replace('let result=t.await;', 'drop(->n);let result=t.await;')
                self.refused(self.program(invalid), 'emprunt|réserv|référenc')
        source = PREFIX + 'fn main(){' + SETUP + '''
let t=again(->make(->outer));let h=runtime::spawn(->t);
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}drop(->n);}'''
        self.assertEqual(self.run_source(source).stdout, '1\n')
        invalid = source.replace('drop(->n);', '').replace('let h=runtime::spawn', 'drop(->n);let h=runtime::spawn')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_whole_result_keeps_nested_target(self):
        prefix = TYPES + '''async fn relay(v:->Outer)-><-A<Outer>{yield;return <-v;}
fn make(v:->Outer)-><-relay{return <-relay(->v);}'''
        for call in ('relay', 'make'):
            body = SETUP + 'let result=' + call + '(->outer).await;yield;drop(->result);drop(->n);return 1;'
            with self.subTest(call=call):
                self.assertEqual(self.run_source(self.program(body, prefix)).stdout, '1\n')
                invalid = body.replace('drop(->n);', '').replace('yield;drop(->result);', 'drop(->n);yield;drop(->result);')
                self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_sync_caller_result_keeps_nested_target(self):
        prefix = TYPES + '''fn read(v:&Inner)->Int{return *v.view;}
async fn relay(v:->Outer)-><-A<Outer>{yield;return <-v;}
fn make(v:->Outer)-><-relay{return <-relay(->v);}'''
        source = prefix + 'fn main(){' + SETUP + '''let h=runtime::spawn(->make(->outer));
let result=match h.join(){Ok(r)=>{<-r},Err(_)=>{return;}};
print(read(&*result.inner));drop(->result);drop(->n);}'''
        self.assertEqual(self.run_source(source).stdout, '9\n')
        self.refused(source.replace('drop(->result);drop(->n);', 'drop(->n);drop(->result);'),
                     'emprunt|réserv|référenc')

    def test_three_lifetime_model(self):
        declarations = ('let mut outs=pool<Outer>(1);', 'let mut ins=pool<Inner>(1);',
                        'let mut ns=pool<Int>(1);let n=ns.new(9);')
        for durable in product((False, True), repeat=3):
            outer = ''.join(text for text, survives in zip(declarations, durable) if survives)
            inner = ''.join(text for text, survives in zip(declarations, durable) if not survives)
            source = PREFIX + 'fn main(){' + outer + 'let t={' + inner + '''
let i=ins.new(view:&n);let o=outs.new(inner:<-i);let t=make(->o);<-t};
let h=runtime::spawn(->t);match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
            with self.subTest(durable=durable):
                if all(durable):
                    self.assertEqual(self.run_source(source).stdout, '1\n')
                else:
                    self.refused(source, 'pool|source|survi|durable|emprunt|référenc')

    def test_mutable_target_stays_exclusive(self):
        prefix = PREFIX.replace('view:&Int', 'view:&mut Int')
        setup = SETUP.replace('let n=', 'let mut n=').replace('view:&n', 'view:&mut n')
        body = setup + 'let t=make(->outer);let result=t.await;print(*n);drop(->n);return result;'
        self.assertEqual(self.run_source(self.program(body, prefix)).stdout, '9\n1\n')
        for operation in ('print(*n);', 'n=12;', 'drop(->n);'):
            invalid = body.replace('print(*n);drop(->n);', '').replace('let result=t.await;', operation + 'let result=t.await;')
            self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_two_same_named_fields_keep_distinct_targets(self):
        prefix = '''struct Inner{view:&Int}struct Outer{left:A<Inner>,right:A<Inner>}
async fn consume(v:->Outer)->Int{yield;drop(->v);return 1;}
fn make(v:->Outer)-><-consume{return <-consume(->v);}'''
        body = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let mut ins=pool<Inner>(2);let left=ins.new(view:&a);let right=ins.new(view:&b);
let outer=Outer{left:<-left,right:<-right};let t=make(->outer);
let result=t.await;let next_left=ins.new(view:&a);let next_right=ins.new(view:&b);
let next=Outer{left:<-next_left,right:<-next_right};drop(->next);
drop(->a);drop(->b);return result;'''
        run = self.run_source(self.program(body, prefix))
        self.assertEqual(run.stdout, '1\n')
        self.assertEqual(run.stderr.count('=Inner\n'), 4)
        self.assertEqual(run.stderr.count('=Outer\n'), 2)
        for target in ('a', 'b'):
            invalid = body.replace('drop(->' + target + ');', '').replace('let result=t.await;',
                                              'drop(->' + target + ');let result=t.await;')
            self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_inactive_failure_and_slot_reuse(self):
        source = PREFIX + 'fn main(){' + SETUP + '''let t=make(->outer);ACTION
let next_inner=ins.new(view:&n);let next_outer=outs.new(inner:<-next_inner);
drop(->next_outer);print(*n);drop(->n);}'''
        self.assertEqual(self.run_source(source.replace('ACTION', 'drop(->t);')).stdout, '9\n')
        launched = source.replace('ACTION', '''let h=runtime::spawn(->t);
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}''')
        for failure, expected in ((None, '1\n9\n'), (1, '99\n9\n')):
            run = self.run_native(launched, fail_submission_at=failure)
            self.assertEqual(run.stdout, expected)
            self.assertEqual(run.stderr.count('=Inner\n'), 2)
            self.assertEqual(run.stderr.count('=Outer\n'), 2)

    def test_reads_across_owned_edges_and_after_return(self):
        prefix = TYPES + '''fn read(v:&Inner)->Int{return *v.view;}
async fn relay(v:->Outer)-><-A<Outer>{yield;print(read(&*v.inner));return <-v;}
fn make(v:->Outer)-><-relay{return <-relay(->v);}'''
        body = SETUP + '''let result=make(->outer).await;yield;print(read(&*result.inner));
drop(->result);drop(->n);return 1;'''
        self.assertEqual(self.run_source(self.program(body, prefix)).stdout, '9\n9\n1\n')
        invalid = body.replace('drop(->n);', '').replace('yield;print(read(&*result.inner));',
                                              'drop(->n);yield;print(read(&*result.inner));')
        self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_select_loser_keeps_nested_target(self):
        prefix = PREFIX + 'async fn ready()->Int{return 3;}'
        body = SETUP + '''let mut s=runtime::select(->make(->outer),->ready());
let result=s.await;drop(->s);
let next_inner=ins.new(view:&n);let next_outer=outs.new(inner:<-next_inner);
drop(->next_outer);drop(->n);return result;'''
        run = self.run_source(self.program(body, prefix))
        self.assertEqual(run.stdout, '3\n')
        self.assertEqual(run.stderr.count('=Inner\n'), 2)
        self.assertEqual(run.stderr.count('=Outer\n'), 2)
        invalid = body.replace('drop(->n);', '').replace('drop(->s);', 'drop(->n);drop(->s);')
        self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_native_thread_owns_graph_but_not_target(self):
        source = TYPES + 'fn read(v:&Inner)->Int{return *v.view;}fn main(){' + SETUP + '''
let h=runtime::thread({->(outer);return read(&*outer.inner);});
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
let next_inner=ins.new(view:&n);let next_outer=outs.new(inner:<-next_inner);
drop(->next_outer);drop(->n);}'''
        for failure, expected in ((False, '9\n'), (True, '99\n')):
            run = self.run_native(source, fail_native=failure)
            self.assertEqual(run.stdout, expected)
            self.assertEqual(run.stderr.count('=Inner\n'), 2)
            self.assertEqual(run.stderr.count('=Outer\n'), 2)
        invalid = source.replace('drop(->n);', '').replace('match h.join()', 'drop(->n);match h.join()')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_deeper_paths_preserve_target_after_return(self):
        for depth in (2, 4):
            types = 'struct Level0{view:&Int}' + ''.join(
                f'struct Level{i}{{child:A<Level{i-1}>}}' for i in range(1, depth + 1))
            prefix = types + f'''async fn relay(v:->Level{depth})-><-A<Level{depth}>{{yield;return <-v;}}
fn make(v:->Level{depth})-><-relay{{return <-relay(->v);}}'''
            body = 'let mut ns=pool<Int>(1);let n=ns.new(9);'
            body += ''.join(f'let mut p{i}=pool<Level{i}>(1);' for i in range(depth + 1))
            body += 'let v0=p0.new(view:&n);' + ''.join(
                f'let v{i}=p{i}.new(child:<-v{i-1});' for i in range(1, depth + 1))
            body += f'let r=make(->v{depth}).await;yield;drop(->r);drop(->n);return 1;'
            with self.subTest(depth=depth):
                run = self.run_source(self.program(body, prefix))
                self.assertEqual(run.stdout, '1\n')
                for i in range(depth + 1):
                    self.assertEqual(run.stderr.count(f'=Level{i}\n'), 1)
                invalid = body.replace('drop(->r);drop(->n);', 'drop(->n);drop(->r);')
                self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_conditional_return_conserves_all_possible_targets(self):
        prefix = TYPES + '''async fn choose(a:->Outer,b:->Outer,flag:Bool)-><-Outer{
yield;if flag{a ->;return <-a;}return <-b;}
fn make(a:->Outer,b:->Outer,flag:bool)-><-choose{return <-choose(->a,->b,flag);}'''
        body = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let mut ins=pool<Inner>(2);let left=ins.new(view:&a);let right=ins.new(view:&b);
let x=Outer{inner:<-left};let y=Outer{inner:<-right};
let result=make(->x,->y,FLAG).await;yield;drop(->result);drop(->a);drop(->b);return 1;'''
        for flag in ('true', 'false'):
            source = body.replace('FLAG', flag)
            run = self.run_source(self.program(source, prefix))
            self.assertEqual(run.stdout, '1\n')
            self.assertEqual(run.stderr.count('=Inner\n'), 2)
            self.assertEqual(run.stderr.count('=Outer\n'), 2)
            for target in ('a', 'b'):
                invalid = source.replace('drop(->' + target + ');', '').replace('yield;drop(->result);',
                                           'drop(->' + target + ');yield;drop(->result);')
                self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_returned_mutable_graph_and_child_reborrow(self):
        prefix = TYPES.replace('&Int', '&mut Int') + '''
fn read(v:&Inner)->Int{return *v.view;}
async fn relay(v:->Outer)-><-A<Outer>{yield;return <-v;}
fn make(v:->Outer)-><-relay{return <-relay(->v);}'''
        setup = SETUP.replace('let n=', 'let mut n=').replace('view:&n', 'view:&mut n')
        body = setup + '''let result=make(->outer).await;
let view=&*result.inner;yield;print(read(view));drop(->result);print(*n);return 1;'''
        self.assertEqual(self.run_source(self.program(body, prefix)).stdout, '9\n9\n1\n')
        for operation in ('print(*n);', 'n=12;', 'drop(->n);', 'drop(->result);'):
            invalid = body.replace('drop(->result);print(*n);', '').replace('yield;print(read(view));',
                                                                                     operation + 'yield;print(read(view));')
            self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_nested_addresses_survive_suspensions_and_return(self):
        prefix = TYPES + '''fn read(v:&Inner)->Int{return *v.view;}
async fn relay(v:->Outer)-><-Outer{yield;return <-v;}
fn make(v:->Outer)-><-relay{return <-relay(->v);}'''
        setup = SETUP.replace('let mut outs=pool<Outer>(1);', '').replace(
            'outs.new(inner:<-inner)', 'Outer{inner:<-inner}')
        body = setup + 'let result=make(->outer).await;yield;return read(&*result.inner);'
        self.storage_probe(self.program(body, prefix), '''
CrustTask *task=crust_async_work_create();Cell *root=NULL,*inner=NULL,*target=NULL;
int suspensions=0;
while(task_poll(task)==TASK_SUSPENDED){
    assert(observed_count==1);
    if(!root){root=observed_cells[0];inner=cell_load_ref(root,0);target=cell_load_ref(inner,0);}
    assert(root==observed_cells[0] && root->alive);
    assert(cell_load_ref(root,0)==inner && inner->alive);
    assert(cell_load_ref(inner,0)==target && target->alive && target->value==9);
    assert(++suspensions<10);
}
assert(suspensions>=2);int answer;assert(task_take(task,&answer));assert(answer==9);
''')


if __name__ == '__main__':
    unittest.main()
