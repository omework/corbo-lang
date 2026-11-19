"""SL1 compares concrete result storage as well as the lowered payload name."""
from itertools import product
from pathlib import Path
import unittest
from crust import compile_source
from scheduler_faults import inject_submission_failure
import test_select_source as sources

ROOT = Path(__file__).resolve().parents[1]
HELPERS = '''struct Point{x:Int}
async fn left(v:->Point)-><-Point{yield;return <-v;}
async fn right(v:->Point)-><-Point{return <-v;}'''


def program(first='Point{x:7}', second='Point{x:9}', selection=None, use=None):
    selection = selection or 'let mut s=runtime::select(->left(->a),->right(->b));'
    use = use or 'let result=s.await;drop(->s);print(result.x);drop(->result);'
    helpers = HELPERS
    if first.startswith('ps.new'): helpers = helpers.replace('left(v:->Point)-><-Point','left(v:->Point)-><-A<Point>')
    if second.startswith('ps.new'): helpers = helpers.replace('right(v:->Point)-><-Point','right(v:->Point)-><-A<Point>')
    return sources.SelectSourceTests.program('''let mut ps=pool<Point>(2);
let a=FIRST;let b=SECOND;SELECTION USE
let again=ps.new(x:20);print(again.x);drop(->again);return 1;'''.replace(
        'FIRST', first).replace('SECOND', second).replace('SELECTION', selection).replace('USE',use), helpers)


class SelectResultStorageTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused

    def test_recorded_mixed_storage(self):
        self.refused((ROOT/'validation/counterexample-select-mixed-result-storage.crb').read_text(),
                     'stockage|même type')

    def test_independent_storage_and_poll_model(self):
        # Equality of source-language result types is independent of polling.
        for first, second, ready in product(('local','pool'), ('local','pool'), (False,True)):
            a = 'Point{x:7}' if first == 'local' else 'ps.new(x:7)'
            b = 'Point{x:9}' if second == 'local' else 'ps.new(x:9)'
            source = program(a,b)
            if ready: source=source.replace('yield;','')
            with self.subTest(first=first,second=second,ready=ready):
                if first != second:
                    self.refused(source, 'stockage|même type')
                else:
                    self.assertEqual(self.run_source(source).stdout, ('7' if ready else '9')+'\n20\n1\n')

    def test_inactive_selection_still_requires_one_type(self):
        for a,b in (('Point{x:7}','ps.new(x:9)'),('ps.new(x:7)','Point{x:9}')):
            self.refused(program(a,b,use='drop(->s);'), 'stockage|même type')
        self.assertEqual(self.run_source(program(use='drop(->s);')).stdout, '20\n1\n')

    def test_selection_through_if_or_loop_keeps_storage(self):
        forms = (
            '''let mut s=if FLAG{a ->;b ->;drop(->b);let x=runtime::select(->left(->a));<-x}
            else{a ->;b ->;drop(->a);let y=runtime::select(->right(->b));<-y};''',
            '''let mut s=loop{a ->;b ->;if FLAG{a ->;b ->;drop(->b);
            let x=runtime::select(->left(->a));break <-x;}else{a ->;b ->;drop(->a);
            let y=runtime::select(->right(->b));break <-y;}};''',
        )
        for form,flag in product(forms,('true','false')):
            selection=form.replace('FLAG',flag)
            with self.subTest(form=form[:24],flag=flag):
                self.assertEqual(self.run_source(program(selection=selection)).stdout,
                                 ('7' if flag=='true' else '9')+'\n20\n1\n')
                self.refused(program(second='ps.new(x:9)',selection=selection), 'stockage|même type')

    def test_task_alternatives_cannot_hide_mixed_result_storage(self):
        forms=(
            '''let t=if FLAG{a ->;b ->;drop(->b);let x=left(->a);<-x}
            else{a ->;b ->;drop(->a);let y=left(->b);<-y};''',
            '''let t=loop{a ->;b ->;if FLAG{a ->;b ->;drop(->b);let x=left(->a);break <-x;}
            else{a ->;b ->;drop(->a);let y=left(->b);break <-y;}};''',
        )
        for form in forms:
            selection=form.replace('FLAG','false')+'let mut s=runtime::select(->t);'
            self.assertEqual(self.run_source(program(selection=selection)).stdout,'9\n20\n1\n')
            self.refused(program(second='ps.new(x:9)',selection=selection),'stockage|même type')

    def test_local_root_with_pool_descendant_and_returned_loan(self):
        helpers='''struct Inner{view:&Int}struct Outer{inner:A<Inner>}
fn read(v:&Inner)->Int{return *v.view;}
async fn left(v:->Outer)-><-Outer{yield;return <-v;}
async fn right(v:->Outer)-><-Outer{return <-v;}'''
        body='''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let mut ins=pool<Inner>(2);let x=ins.new(view:&a);let y=ins.new(view:&b);
let first=Outer{inner:<-x};let second=Outer{inner:<-y};
let mut s=runtime::select(->left(->first),->right(->second));
let result=s.await;drop(->s);BEFORE print(read(&*result.inner));drop(->result);
let reused=ins.new(view:&a);drop(->reused);drop(->a);drop(->b);return 1;'''
        source=sources.SelectSourceTests.program(body,helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'9\n1\n')
        for name in ('a','b'):
            self.refused(source.replace('drop(->'+name+');','').replace('BEFORE','drop(->'+name+');'),
                         'emprunt|réserv|référenc')

    def test_submission_failure_keeps_cleanup_and_reuse(self):
        source=HELPERS.replace('-><-Point','-><-A<Point>')+'''async fn work(a:->Point,b:->Point)->Int{
let mut s=runtime::select(->left(->a),->right(->b));let r=s.await;
drop(->s);let x=r.x;drop(->r);return x;}
fn main(){let mut ps=pool<Point>(2);let a=ps.new(x:7);let b=ps.new(x:9);
let h=runtime::spawn(->work(->a,->b));
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
let again=ps.new(x:20);let other=ps.new(x:30);print(again.x);print(other.x);}'''
        self.assertEqual(self.run_source(source).stdout,'9\n20\n30\n')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(compile_source(source),
            asynchronous=False, at=1)).stdout,'99\n20\n30\n')

    def test_fresh_results_do_not_inherit_unreturned_capture_storage(self):
        source=program().replace(
            'async fn left(v:->Point)-><-Point{yield;return <-v;}',
            'async fn left(v:->Point)-><-Point{yield;drop(->v);return <-Point{x:7};}').replace(
            'async fn right(v:->Point)-><-Point{return <-v;}',
            'async fn right(v:->Point,p:&mut Pool<Point>)-><-A<Point>{drop(->v);return <-p.new(x:9);}').replace(
            'right(->b)','right(->b,&mut ps)')
        self.refused(source,'stockage|même type')
        both_pool=source.replace('left(v:->Point)', 'left(v:->Point,p:&mut Pool<Point>)').replace(
            'return <-Point{x:7};','return <-p.new(x:7);').replace('left(v:->Point,p:&mut Pool<Point>)-><-Point','left(v:->Point,p:&mut Pool<Point>)-><-A<Point>').replace(
            'left(->a)','left(->a,&mut other)').replace('let a=', 'let mut other=pool<Point>(1);let a=')
        self.assertEqual(self.run_source(both_pool).stdout,'9\n20\n1\n')

    def test_sync_relays_preserve_selection_result_storage(self):
        helper='fn relay(t:->left)-><-left{return <-t;}'
        source=program().replace(HELPERS,HELPERS+helper).replace('->left(->a)','->relay(->left(->a))')
        self.assertEqual(self.run_source(source).stdout,'9\n20\n1\n')
        self.refused(source.replace('let b=Point{x:9}', 'let b=ps.new(x:9)'), 'stockage|même type')

    def test_shared_result_type_does_not_depend_on_target_storage(self):
        helpers='''async fn read(n:&Int)->&Int{yield;return n;}'''
        body='''let a=7;let mut ps=pool<Int>(1);let b=ps.new(9);
let mut s=runtime::select(->read(&a),->read(&b));let r=s.await;drop(->s);
BEFORE print(*r);drop(->b);return 1;'''
        source=sources.SelectSourceTests.program(body,helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'7\n1\n')
        self.refused(source.replace('drop(->b);','').replace('BEFORE','drop(->b);'),'emprunt|réserv|référenc')


if __name__=='__main__':unittest.main()
