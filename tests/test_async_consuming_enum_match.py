"""Consuming enum matches transfer cleanup across suspension, not addresses."""
from pathlib import Path
import unittest
import test_select_source as sources

ROOT = Path(__file__).resolve().parents[1]


class AsyncConsumingEnumMatchTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    program = staticmethod(sources.SelectSourceTests.program)

    def test_recorded_counterexample_and_cleanup_order(self):
        source = (ROOT/'validation/open-async-consuming-enum-match.crb').read_text()
        run = self.run_source(source)
        self.assertEqual(run.stdout, '7\n')
        self.assertEqual(run.stderr.count('destroy item=Item.Value\n'), 1)
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        self.assertLess(run.stderr.index('destroy item='), run.stderr.index('destroy n='))

    def test_every_owned_pattern_requires_usage(self):
        source = (ROOT/'validation/open-async-consuming-enum-match.crb').read_text()
        for replacement in ('Item.Value{data:_}=>{0}', 'Item.Value{data:unused}=>{0}'):
            bad = source.replace('Item.Value{data:value}=>{yield;let n=*value;drop(->value);n}', replacement)
            self.refused(bad, 'motif _|sans usage explicite')
            self.refused(bad.replace('Item.Value{data:<-n}', 'Item.Empty{}').replace('let n=ns.new(7);', ''),
                         'motif _|sans usage explicite')

    def test_subject_is_consumed_and_child_borrow_guards_drop(self):
        source = (ROOT/'validation/open-async-consuming-enum-match.crb').read_text()
        subject = source.replace('async fn take', 'fn see(item:&Item){print(item);}async fn take')
        self.refused(subject.replace('yield;let n=*value;', 'see(&item);yield;let n=*value;'),
                     'consomm|utilisable|transfér|invalide|déplac')
        bad = source.replace('yield;let n=*value;drop(->value);n',
                             'let view=&value;yield;drop(->value);*view')
        self.refused(bad, 'emprunt|référenc|survi|incompatible')

    def test_return_owned_child_and_reuse_both_pools(self):
        source = '''enum Boxed{Item{n:A<Int>},Other{n:A<Int>}}
async fn take(b:->Boxed)-><-Int{
let result=match (->b){Boxed.Other{n:v}=>{yield;<-v},Boxed.Item{n:v}=>{yield;<-v}};
return <-result;}
fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);address(n);
let mut bs=pool<Boxed>(1);let b=new(bs) Boxed.Item{n:<-n};
let h=runtime::spawn(->take(->b));match h.join(){Ok(r)=>{address(r);print(r);drop(->r);},Err(_)=>{}}
let next=ns.new(9);address(next);let again=new(bs) Boxed.Other{n:<-next};drop(->again);}'''
        run = self.run_source(source)
        before, returned, value, reused = run.stdout.splitlines()
        self.assertEqual((returned, value, reused), (before, '7', before))
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)

    def test_shared_and_mutable_fields_survive_carrier(self):
        for mode, output, action in (('&Int','&Int','print(*r);'),
                                     ('&mut Int','&mut Int','r.set(20);print(*r);')):
            source = '''enum View{Item{n:MODE}}
async fn take(v:->View)->OUTPUT{
return match (->v){View.Item{n:r}=>{yield;r}};}
fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut vs=pool<View>(1);
let v=new(vs) View.Item{n:BORROW};let h=runtime::spawn(->take(->v));
match h.join(){Ok(r)=>{BEFORE ACTION},Err(_)=>{}}drop(->n);}'''
            source = source.replace('MODE',mode).replace('OUTPUT',output).replace('ACTION',action)
            source = source.replace('BORROW','&mut n' if mode=='&mut Int' else '&n')
            self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,
                             '20\n' if mode=='&mut Int' else '7\n')
            self.refused(source.replace('BEFORE','drop(->n);').replace('}drop(->n);','}'),
                         'emprunt|référenc|survi|incompatible')

    def test_select_loser_destroys_extracted_child_once(self):
        helpers = '''enum Boxed{Item{n:A<Int>}}
async fn lose(b:->Boxed)->Int{match (->b){Boxed.Item{n:v}=>{print(*v);yield;print(99);}}return 1;}
async fn win()->Int{return 9;}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);let mut bs=pool<Boxed>(1);
let b=new(bs) Boxed.Item{n:<-n};let mut s=runtime::select(->lose(->b),->win());
let r=s.await;print(r);drop(->s);let next=ns.new(20);print(*next);
let again=new(bs) Boxed.Item{n:<-next};drop(->again);return 1;'''
        run = self.run_source(self.program(body,helpers))
        self.assertEqual(run.stdout, '7\n9\n20\n1\n')
        self.assertEqual(run.stderr.count('destroy b=Boxed.Item\n'), 1)
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)

    def test_child_survives_local_carrier_pool_but_not_own_pool(self):
        body = '''OUTER let result={INNER let mut bs=pool<Boxed>(1);let n=ns.new(7);
let b=new(bs) Boxed.Item{n:<-n};
let extracted=match (->b){Boxed.Item{n:v}=>{yield;<-v}};<-extracted};
print(*result);drop(->result);return 1;'''
        pool = 'let mut ns=pool<Int>(1);'
        helpers = 'enum Boxed{Item{n:A<Int>}}'
        good = self.program(body.replace('OUTER',pool).replace('INNER',''),helpers)
        self.assertEqual(self.run_source(good).stdout,'7\n1\n')
        bad = self.program(body.replace('OUTER','').replace('INNER',pool),helpers)
        self.refused(bad,'pool|source|survit|surviv')

    def test_loop_continue_break_and_return_cleanup(self):
        helpers = 'enum Boxed{Item{n:A<Int>}}'
        body = '''let mut ns=pool<Int>(1);let mut bs=pool<Boxed>(1);let mut i=0;
loop{let n=ns.new(i+7);let b=new(bs) Boxed.Item{n:<-n};
match (->b){Boxed.Item{n:v}=>{yield;print(*v);if i==0{i=1;continue;}EXIT}}}
let next=ns.new(20);print(*next);return 1;'''
        for exit_, expected in (('break;','7\n8\n20\n1\n'), ('return *v;','7\n8\n8\n')):
            variant = body.replace('EXIT',exit_)
            if exit_.startswith('return'):
                variant = variant.replace('let next=ns.new(20);print(*next);return 1;', '')
            run = self.run_source(self.program(variant,helpers))
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)
            self.assertEqual(run.stderr.count('destroy n=8\n'),1)

    def test_nested_owned_child_preserves_descendant_pool(self):
        source = '''struct Inner{n:A<Int>}enum Outer{Item{inner:A<Inner>}}
async fn take(o:->Outer)-><-Inner{
return <-match (->o){Outer.Item{inner:v}=>{yield;<-v}};}
fn main(){let mut ns=pool<Int>(1);let mut ins=pool<Inner>(1);let mut outs=pool<Outer>(1);
let n=ns.new(7);let inner=ins.new(n:<-n);let o=new(outs) Outer.Item{inner:<-inner};
let h=runtime::spawn(->take(->o));match h.join(){Ok(v)=>{print(*v.n);drop(->v);},Err(_)=>{}}
let next=ns.new(20);let again=ins.new(n:<-next);let o2=new(outs) Outer.Item{inner:<-again};drop(->o2);}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)

    def test_extracted_child_keeps_stored_reference(self):
        helpers = '''struct View{n:&Int}enum Outer{Item{inner:A<View>}}
fn see(v:&View)->Int{return *v.n;}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);let mut vs=pool<View>(1);
let mut os=pool<Outer>(1);let v=vs.new(n:&n);let o=new(os) Outer.Item{inner:<-v};
match (->o){Outer.Item{inner:item}=>{yield;BEFORE print(see(&item));}}
drop(->n);return 1;'''
        source = self.program(body.replace('BEFORE',''),helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n1\n')
        bad = body.replace('=>{yield;BEFORE', '=>{n ->;yield;drop(->n);')
        self.refused(self.program(bad,helpers),
                     'emprunt|référenc|survi|incompatible')


if __name__ == '__main__':
    unittest.main()
