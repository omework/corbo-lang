"""Task transfers through synchronous contracts called from async states."""
from pathlib import Path
import unittest
import test_select_source as sources
import test_native_blocks as native

ROOT = Path(__file__).resolve().parents[1]


class SyncTaskArgumentTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    run_native = native.NativeBlockTests.run_native
    program = staticmethod(sources.SelectSourceTests.program)

    def test_recorded_nested_owned_capture(self):
        source = (ROOT/'validation/open-async-task-relay-argument.crb').read_text()
        run = self.run_source(source)
        self.assertEqual(run.stdout, '1\n')
        self.assertEqual(run.stderr.count('=Inner\n'), 1)
        self.assertEqual(run.stderr.count('=Outer\n'), 1)
        invalid = source.replace('drop(->number);', '').replace('let result = task.await;',
            'drop(->number);let result = task.await;')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_relay_borrowed_result_and_last_use(self):
        for mode in ('', 'mut '):
            helpers = f'''async fn read(n:&{mode}Int)->&{mode}Int{{yield;return n;}}
fn relay(t:->read)-><-read{{return <-t;}}'''
            body = f'''let mut ns=pool<Int>(1);let mut n=ns.new(7);
let task=read(&{mode}n);let next=relay(->task);let mut view=next.await;
yield;print(*view);drop(->n);return 1;'''
            self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n1\n')
            for marker in ('let mut view=next.await;', 'yield;print(*view);'):
                bad = body.replace('drop(->n);', '').replace(marker, 'drop(->n);' + marker)
                self.refused(self.program(bad, helpers), 'emprunt|réserv|référenc')
            self.refused(self.program(body.replace('let next=relay(->task);',
                'let next=relay(->task);drop(->task);'), helpers), 'consomm|inconnue|utilisable')

    def test_drop_helper_releases_capture_and_task_slot(self):
        helpers = '''#(directive, async_pool_sizes={read:1,work:1})
async fn read(n:&Int)->Int{yield;return *n;}
fn forget(t:->read){drop(->t);}'''
        body = '''let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut i=0;
while i<3{let task=read(&n);forget(->task);n=i;i=i+1;}drop(->n);return i;'''
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '3\n')
        self.refused(self.program(body.replace('forget(->task)', 'forget(task)'), helpers), 'transfert|mode')

    def test_public_spawn_helper_keeps_returned_borrow(self):
        helpers = '''async fn read(n:&Int)->&Int{yield;return n;}
fn start(t:->read)-><-runtime::Handle<&Int>{return <-runtime::spawn(->t);}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);let h=start(->read(&n));
let view=match h.await{Ok(v)=>{v},Err(_)=>{return 99;}};
yield;print(*view);drop(->n);return 1;'''
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n1\n')
        bad = body.replace('drop(->n);', '').replace('yield;print(*view);', 'drop(->n);yield;print(*view);')
        self.refused(self.program(bad, helpers), 'emprunt|réserv|référenc')

    def test_left_to_right_prepared_task_holds_capture(self):
        helpers = '''async fn read(n:&Int)->Int{yield;return *n;}
fn relay(t:->read,x:Int)-><-read{print(x);return <-t;}'''
        body = '''let mut ns=pool<Int>(1);let mut n=ns.new(7);
let t=relay(->read(&n),{yield;print(2);3});return t.await;'''
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '2\n3\n7\n')
        self.refused(self.program(body.replace('yield;print(2);', 'yield;n=9;print(2);'), helpers),
                     'emprunt|réserv|référenc')

    def test_early_return_destroys_prepared_task_before_pool(self):
        helpers = '''#(directive, async_pool_sizes={own:1,work:1})
async fn own(n:->Int)->Int{yield;return *n;}
fn relay(t:->own,x:Int)-><-own{print(999);return <-t;}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);
let t=relay(->own(->n),{yield;return 3;});return t.await;'''
        source = self.program(body, helpers)
        source = source[:source.index('fn main()')] + '''fn main(){let mut i=0;while i<2{
let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}i=i+1;}}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout, '3\n3\n')
        self.assertEqual(run.stderr.count('=7\n'), 2)

    def test_select_cleanup_in_later_suspended_argument(self):
        helpers = '''async fn own(n:->Int)->Int{yield;return *n;}
async fn pause()->Int{yield;return 3;}
fn relay(t:->own,x:Int)-><-own{return <-t;}
async fn left()->Int{let mut ns=pool<Int>(1);let n=ns.new(7);
let t=relay(->own(->n),pause().await);return t.await;}
async fn ready()->Int{return 9;}'''
        helpers = '#(directive, async_pool_sizes={own:1,pause:1,left:1,ready:1,work:1})' + helpers
        body = '''let mut i=0;while i<2{
let mut s=runtime::select(->left(),->ready());let result=s.await;
drop(->s);print(result);i=i+1;}return i;'''
        run = self.run_source(self.program(body, helpers))
        self.assertEqual(run.stdout, '9\n9\n2\n')
        self.assertEqual(run.stderr.count('=7\n'), 2)

    def test_conditional_forward_unions_targets(self):
        helpers = '''async fn read(n:&Int)->&Int{yield;return n;}
fn choose(a:->read,b:->read,flag:bool)-><-read{
if flag{b ->;drop(->b);return <-a;}drop(->a);return <-b;}'''
        for flag, expected in (('true', 7), ('false', 9)):
            body = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let t=choose(->read(&a),->read(&b),FLAG);let view=t.await;
yield;print(*view);drop(->a);drop(->b);return 1;'''.replace('FLAG', flag)
            self.assertEqual(self.run_source(self.program(body, helpers)).stdout, f'{expected}\n1\n')
            for target in ('a', 'b'):
                bad = body.replace('drop(->'+target+');', '').replace('yield;print(*view);',
                    'drop(->'+target+');yield;print(*view);')
                self.refused(self.program(bad, helpers), 'emprunt|réserv|référenc')

    def test_forwarded_owned_graph_result_keeps_nested_reference(self):
        helpers = '''struct Inner{view:&Int}struct Outer{inner:A<Inner>}
fn get(v:&Inner)->Int{return *v.view;}
async fn own(v:->Outer)-><-Outer{yield;return <-v;}
fn relay(t:->own)-><-own{return <-t;}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);let mut ins=pool<Inner>(1);
let inner=ins.new(view:&n);let outer=Outer{inner:<-inner};
let t=relay(->own(->outer));let result=t.await;yield;
print(get(&*result.inner));drop(->result);drop(->n);return 1;'''
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n1\n')
        bad = body.replace('drop(->n);', '').replace('yield;', 'drop(->n);yield;')
        self.refused(self.program(bad, helpers), 'emprunt|réserv|référenc')

    def test_fresh_local_result_and_pool_result_through_relay(self):
        for helper, call, setup in (
            ('struct Point{x:Int}async fn make()-><-Point{yield;return <-Point{x:7};}',
             'make()', ''),
            ('struct Point{x:Int}async fn make(p:&mut Pool<Point>)-><-A<Point>{yield;return <-p.new(x:7);}',
             'make(&mut ps)', 'let mut ps=pool<Point>(1);')):
            helpers = helper + 'fn relay(t:->make)-><-make{return <-t;}'
            body = setup + 'let t=relay(->' + call + ');let result=t.await;yield;print(result.x);drop(->result);return 1;'
            self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n1\n')

    def test_conditional_fresh_or_forwarded_task(self):
        helpers = '''async fn read(n:&Int)->&Int{yield;return n;}
fn choose(t:->read,n:&Int,flag:bool)-><-read{
if flag{return <-t;}drop(->t);return <-read(n);}'''
        for flag, expected in (('true', 7), ('false', 9)):
            body = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let t=choose(->read(&a),&b,FLAG);let view=t.await;
yield;print(*view);drop(->a);drop(->b);return 1;'''.replace('FLAG', flag)
            self.assertEqual(self.run_source(self.program(body, helpers)).stdout, f'{expected}\n1\n')
            for target in ('a', 'b'):
                bad = body.replace('drop(->'+target+');', '').replace('yield;print(*view);',
                    'drop(->'+target+');yield;print(*view);')
                self.refused(self.program(bad, helpers), 'emprunt|réserv|référenc')

    def test_multiple_prepared_tasks_clean_in_reverse_order(self):
        helpers = '''async fn own(n:->Int)->Int{yield;return *n;}
fn combine(a:->own,b:->own,x:Int)->Int{drop(->b);drop(->a);return x;}'''
        body = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
return combine(->own(->a),->own(->b),{yield;return 3;});'''
        run = self.run_source(self.program(body, helpers))
        self.assertEqual(run.stdout, '3\n')
        trace = [line.rsplit('=', 1)[-1] for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(trace, ['9', '7'])

    def test_task_nominal_type_and_capture_scope(self):
        helpers = '''async fn first(n:&Int)->Int{yield;return *n;}
async fn second(n:&Int)->Int{yield;return *n;}
fn relay(t:->first)-><-first{return <-t;}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);let t=relay(->first(&n));return t.await;'''
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n')
        self.refused(self.program(body.replace('relay(->first(&n))', 'relay(->second(&n))'), helpers), 'type|attendu|requis')
        bad = '''let t={let mut ns=pool<Int>(1);let n=ns.new(7);let t=relay(->first(&n));<-t};return t.await;'''
        self.refused(self.program(bad, helpers), 'survi|durable|réserv|capture|emprunt')

    def test_forwarding_contract_marks_fresh_alternative(self):
        from crust import Compiler, Parser
        source = '''async fn leaf()->Int{yield;return 7;}
fn relay(t:->leaf)-><-leaf{return <-t;}
fn again(t:->leaf)-><-leaf{return <-relay(->t);}
fn mixed(t:->leaf,flag:bool)-><-leaf{if flag{return <-t;}drop(->t);return <-leaf();}
fn main(){}'''
        compiler = Compiler()
        compiler.verify(Parser(source).parse())
        for name, expected in (('relay', True), ('again', True), ('mixed', False)):
            self.assertEqual(compiler.function_contracts[name].result.task_forward_only, expected)

    def test_select_rejects_loser_with_outstanding_launched_handle(self):
        source = (ROOT/'validation/open-select-launched-handle.crb').read_text()
        self.refused(source, 'SL2')

    def test_break_continue_clean_only_aborted_call(self):
        helpers = '''#(directive, async_pool_sizes={own:1,work:1})
async fn own(n:->Int)->Int{yield;return *n;}
fn relay(t:->own,x:Int)-><-own{return <-t;}'''
        for exit, expected in (('break', 1), ('continue', 2)):
            body = '''let mut ns=pool<Int>(1);let mut i=0;while i<2{
let n=ns.new(7);i=i+1;let t=relay(->own(->n),{yield;EXIT;});drop(->t);}return i;'''.replace('EXIT', exit)
            run = self.run_source(self.program(body, helpers))
            self.assertEqual(run.stdout, f'{expected}\n')
            self.assertEqual(run.stderr.count('=7\n'), expected)
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);
let t=relay(->own(->n),loop{yield;break 3;});return t.await;'''
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n')

    def test_array_capture_through_relay(self):
        for mode in ('', 'mut '):
            helpers = f'''async fn read(a:&{mode}[Int;2])->Int{{yield;return a[0];}}
fn relay(t:->read)-><-read{{return <-t;}}'''
            body = f'''let mut a=[7,9];let t=relay(->read(&{mode}a));
let result=t.await;drop(->a);return result;'''
            self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n')
            bad = body.replace('drop(->a);', '').replace('let result=t.await;', 'drop(->a);let result=t.await;')
            self.refused(self.program(bad, helpers), 'emprunt|réserv|référenc')

    def test_concrete_spawn_helper_keeps_owned_result_fields(self):
        helpers = '''struct View{target:&Int}
async fn own(v:->View)-><-View{yield;return <-v;}
fn start(t:->own)-><-Execution<own>{return <-runtime::spawn(->t);}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{target:&n};
let h=start(->own(->v));let result=match h.await{Ok(v)=>{<-v},Err(_)=>{return 99;}};
yield;print(*result.target);drop(->result);drop(->n);return 1;'''
        # Keep payload names distinct from the already moved source variable.
        body = body.replace('Ok(v)=>{<-v}', 'Ok(found)=>{<-found}')
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '7\n1\n')
        bad = body.replace('drop(->n);', '').replace('yield;print', 'drop(->n);yield;print')
        self.refused(self.program(bad, helpers), 'emprunt|réserv|référenc')
        fresh_helpers = helpers.replace('start(t:->own)', 'start(v:->View)').replace(
            'runtime::spawn(->t)', 'runtime::spawn(->own(->v))')
        fresh_body = body.replace('start(->own(->v))', 'start(->v)')
        self.assertEqual(self.run_source(self.program(fresh_body, fresh_helpers)).stdout, '7\n1\n')
        invalid = fresh_body.replace('drop(->n);', '').replace('yield;print', 'drop(->n);yield;print')
        self.refused(self.program(invalid, fresh_helpers), 'emprunt|réserv|référenc')


if __name__ == '__main__':
    unittest.main()
