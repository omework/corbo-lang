"""Existing field-write rules through enum descendants and Select suspension."""
import unittest
from crust import verify_program, Parser, Error
from async_structure_effects import AsyncStructureEffectAnalyzer
import test_select_source as sources


HELPERS = '''struct Inner{view:&Int}enum Outer{Item{inner:A<Inner>}}
fn change(inner:&mut Inner,n:&Int){inner.view=&*n;}
fn value(inner:&Inner)->Int{return *inner.view;}
fn read(o:&Outer)->Int{match &o{Outer.Item{inner:i}=>{return value(i);}}}
'''
MODIFY = '''async fn modify(o:&mut Outer,n:&Int,after:&Int)->Int{
match &mut o{Outer.Item{inner:i}=>{change(i,n);yield;change(i,after);}}
return 1;}'''


class AsyncEnumSuspensionFieldTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    program = staticmethod(sources.SelectSourceTests.program)

    def summary(self, declarations, name='modify'):
        interface = verify_program(HELPERS)
        definitions = {node.args[0]:node for node in Parser(declarations).parse() if node.op=='async_fn'}
        summary = AsyncStructureEffectAnalyzer(definitions,interface.function_contracts,
                                             interface.enums,Error).infer(name)
        self.assertTrue(summary.complete,summary.reason)
        self.assertTrue(summary.suspension_complete,summary.suspension_reason)
        return summary

    @staticmethod
    def fields(summary):
        return {(index,field):{(t.kind,t.parameter,t.field) for t in targets}
                for index,fields in summary.structure_fields for field,targets in fields}

    def test_suspended_and_completed_targets_remain_distinct(self):
        summary = self.summary(MODIFY)
        self.assertEqual(self.fields(summary.suspension_result),
                         {(0,'Item.inner/.view'):{('parameter',1,'')}})
        self.assertEqual(self.fields(summary.completion_result),
                         {(0,'Item.inner/.view'):{('parameter',2,'')}})
        multiple = self.summary(MODIFY.replace('change(i,after);','change(i,after);yield;'))
        self.assertEqual(self.fields(multiple.suspension_result),
                         {(0,'Item.inner/.view'):{('parameter',1,''),('parameter',2,'')}})

    def test_child_suspension_propagates_through_await(self):
        summary = self.summary(MODIFY+'''async fn parent(o:&mut Outer,a:&Int,b:&Int)->Int{
return modify(o,a,b).await;}''','parent')
        self.assertEqual(self.fields(summary.suspension_result),
                         {(0,'Item.inner/.view'):{('parameter',1,'')}})
        self.assertEqual(self.fields(summary.completion_result),
                         {(0,'Item.inner/.view'):{('parameter',2,'')}})

    def test_select_loser_keeps_write_before_yield(self):
        helpers = HELPERS+MODIFY+'async fn ready()->Int{return 9;}'
        body = '''let mut ns=pool<Int>(3);let a=ns.new(7);let b=ns.new(20);let c=ns.new(30);
let mut ins=pool<Inner>(1);let inner=ins.new(view:&a);let mut os=pool<Outer>(1);
let mut o=new(os) Outer.Item{inner:<-inner};
let mut s=runtime::select(->modify(&mut o,&b,&c),->ready());let result=s.await;
print(result);drop(->s);BEFORE print(read(&o));drop(->o);return 1;'''
        self.assertEqual(self.run_source(self.program(body.replace('BEFORE',''),helpers)).stdout,'9\n20\n1\n')
        self.refused(self.program(body.replace('BEFORE','drop(->b);'),helpers),
                     'emprunt|référenc|survi|incompatible')

    def test_completed_task_keeps_final_write(self):
        body = '''let mut ns=pool<Int>(3);let a=ns.new(7);let b=ns.new(20);let c=ns.new(30);
let mut ins=pool<Inner>(1);let inner=ins.new(view:&a);let mut os=pool<Outer>(1);
let mut o=new(os) Outer.Item{inner:<-inner};
let result=modify(&mut o,&b,&c).await;print(result);print(read(&o));drop(->o);return 1;'''
        self.assertEqual(self.run_source(self.program(body,HELPERS+MODIFY)).stdout,'1\n30\n1\n')


if __name__=='__main__':unittest.main()
