"""User enum matches retain loans and cleanup across async control flow."""
from pathlib import Path
import unittest
from crust import compile_source, verify_program, Parser, Error
from async_structure_effects import AsyncStructureEffectAnalyzer
from scheduler_faults import inject_submission_failure
import test_select_source as sources

ROOT = Path(__file__).resolve().parents[1]


class AsyncEnumMatchTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    program = staticmethod(sources.SelectSourceTests.program)

    def test_recorded_scalar_match(self):
        source = (ROOT/'validation/open-async-enum-match.crb').read_text()
        self.assertEqual(self.run_source(source).stdout, '7\n')

    def test_named_carrier_alias_across_suspension(self):
        source=(ROOT/'validation/open-async-enum-match.crb').read_text()
        source=source.replace('let n=match &v','let alias=&v;yield;BEFORE let n=match &alias')
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'7\n')
        self.refused(source.replace('BEFORE','drop(->v);'),'emprunt|réserv|incompatible')

    def test_three_arms_reordered_with_suspension_model(self):
        helpers = '''enum Choice{Small{x:Int},Pair{x:Int,y:Int},Empty{}}
async fn read(v:->Choice)->Int{
let n=match &v{Choice.Empty{}=>{yield;30},Choice.Pair{x:a,y:b}=>{yield;a+b},Choice.Small{x:a}=>{yield;a}};
return n;}'''
        for variant, fields, expected in [('Small','x:7',7),('Pair','x:10,y:20',30),('Empty','',30)]:
            source = helpers + '''fn main(){let mut p=pool<Choice>(1);let v=new(p) Choice.VARIANT{FIELDS};
let h=runtime::spawn(->read(->v));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
let again=new(p) Choice.VARIANT{FIELDS};drop(->again);}'''.replace('VARIANT',variant).replace('FIELDS',fields)
            run = self.run_source(source)
            self.assertEqual(run.stdout, str(expected)+'\n')
            self.assertEqual(run.stderr.count('destroy v=Choice.'+variant+'\n'),1)

    def test_exhaustiveness_fields_and_subject_type(self):
        source = (ROOT/'validation/open-async-enum-match.crb').read_text()
        self.refused(source.replace(', Choice.Right{x:n}=>{n}', ''), 'exhaustif')
        self.refused(source.replace('Choice.Right{x:n}', 'Choice.Left{x:n}'), 'dupliqu|répét|deux fois')
        self.refused(source.replace('Choice.Right{x:n}', 'Choice.Right{bad:n}'), 'champ')
        self.refused(source.replace('match &v', 'match &missing'), 'inconn|enum|déclar')

    def test_mutable_projection_and_reborrow_inside_arm(self):
        helpers = '''enum Writer{One{n:&mut Int},Two{pad:Int,n:&mut Int}}
fn borrow(n:&mut Int)->&mut Int{return n;}
async fn change(w:&mut Writer)->Int{
let n=match &mut w{
Writer.One{n:v}=>{let mut other=borrow(v);yield;other.set(20);v.set(30);*v},
Writer.Two{pad:_,n:v}=>{yield;v.set(40);*v}};return n;}'''
        for variant, fields, expected in [('One','n:&mut n',30),('Two','pad:1,n:&mut n',40)]:
            source = helpers+'''fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);let mut ws=pool<Writer>(1);
let mut w=new(ws) Writer.VARIANT{FIELDS};let h=runtime::spawn(->change(&mut w));
match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}drop(->w);print(n);}'''.replace('VARIANT',variant).replace('FIELDS',fields)
            self.assertEqual(self.run_source(source).stdout,f'{expected}\n{expected}\n')
            self.refused(source.replace('v.set(30);*v','v.set(30);print(*other);*v'), 'emprunt|incompatible|réserv')

    def test_match_reserves_carrier_until_arm_exit(self):
        helpers = '''enum Writer{One{n:&mut Int}}
fn see(w:&Writer){print(w);}
async fn change(w:&mut Writer)->Int{
match &mut w{Writer.One{n:v}=>{v.set(20);yield;FORBIDDEN}}
see(w);return 1;}'''
        source = helpers+'''fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);let mut ws=pool<Writer>(1);
let mut w=new(ws) Writer.One{n:&mut n};let h=runtime::spawn(->change(&mut w));
match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}drop(->w);}'''
        self.assertEqual(self.run_source(source.replace('FORBIDDEN','')).stdout,'Writer.One(20)\n1\n')
        self.refused(source.replace('FORBIDDEN','see(w);'), 'emprunt|incompatible|réserv')

    def test_returned_mutable_projection_reserves_caller(self):
        helpers = '''enum Writer{One{n:&mut Int},Two{n:&mut Int}}
async fn get(w:&mut Writer)->&mut Int{
let mut result=match &mut w{Writer.One{n:v}=>{yield;v},Writer.Two{n:v}=>{yield;v}};
return result;}'''
        source = helpers+'''fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);let mut ws=pool<Writer>(1);
let mut w=new(ws) Writer.One{n:&mut n};let h=runtime::spawn(->get(&mut w));
match h.join(){Ok(r)=>{BEFORE r.set(30);},Err(_)=>{}}print(w);drop(->w);print(n);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'Writer.One(30)\n30\n')
        self.refused(source.replace('BEFORE','print(w);'),'emprunt|réserv|incompatible')
        self.refused(source.replace('BEFORE','drop(->w);'),'emprunt|réserv|incompatible')

    def test_shared_projection_outlives_owned_carrier(self):
        helpers = '''enum View{One{n:&Int},Two{n:&Int}}
async fn get(v:->View)->&Int{
let result=match &v{View.One{n:r}=>{yield;r},View.Two{n:r}=>{yield;r}};
return result;}'''
        source = helpers+'''fn main(){let mut p=pool<Int>(1);let n=p.new(7);let mut vs=pool<View>(1);
let v=new(vs) View.One{n:&n};let h=runtime::spawn(->get(->v));
match h.join(){Ok(r)=>{BEFORE print(*r);},Err(_)=>{}}drop(->n);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'7\n')
        self.refused(source.replace('BEFORE','drop(->n);').replace('}drop(->n);','}'),'emprunt|référenc|survi')

    def test_shared_result_keeps_exclusive_ancestor(self):
        source='''enum View{Item{n:&Int}}
async fn get(v:->View)->&Int{return match &v{View.Item{n:r}=>{yield;r}};}
fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut parent=&mut n;
let mut vs=pool<View>(1);let v=new(vs) View.Item{n:&*parent};let h=runtime::spawn(->get(->v));
match h.join(){Ok(r)=>{BEFORE print(*r);},Err(_)=>{}}parent.set(40);print(*parent);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'7\n40\n')
        self.refused(source.replace('BEFORE','parent.set(20);'),'emprunt|réserv|incompatible|suspendu')

    def test_return_break_continue_and_pool_cleanup(self):
        helpers = '''enum Choice{First{x:Int},Last{x:Int}}
async fn read(v:->Choice)->Int{let mut i=0;loop{
match &v{Choice.First{x:n}=>{yield;if i==0{i=1;continue;}return n;},
Choice.Last{x:n}=>{yield;break n;}}
}}'''
        # A loop result is returned explicitly; a return in the other arm exits the routine.
        helpers = helpers.replace('let mut i=0;loop{','let mut i=0;let result=loop{').replace('\n}}','\n};return result;}')
        for arm in ('First','Last'):
            source = helpers+'''fn main(){let mut p=pool<Choice>(1);let v=new(p) Choice.ARM{x:7};
let h=runtime::spawn(->read(->v));match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}
let again=new(p) Choice.ARM{x:9};print(again);}'''.replace('ARM',arm)
            self.assertEqual(self.run_source(source).stdout,f'7\nChoice.{arm}(9)\n')

    def test_owned_result_constructed_in_arm(self):
        helpers = '''enum Choice{First{x:Int},Last{x:Int}}
async fn get(v:->Choice,p:&mut Pool<Int>)-><-Int{
let result=match &v{Choice.First{x:n}=>{let value=p.new(n);yield;<-value},
Choice.Last{x:n}=>{let value=p.new(n+1);yield;<-value}};
return <-result;}'''
        for arm,expected in [('First',7),('Last',8)]:
            source = helpers+'''fn main(){let mut p=pool<Choice>(1);let v=new(p) Choice.ARM{x:7};let mut ns=pool<Int>(1);
let h=runtime::spawn(->get(->v,&mut ns));match h.join(){Ok(n)=>{print(n);drop(->n);},Err(_)=>{}}
let again=ns.new(20);print(again);}'''.replace('ARM',arm)
            self.assertEqual(self.run_source(source).stdout,f'{expected}\n20\n')

    def test_select_loser_holds_mutable_enum_until_drop(self):
        helpers = '''enum Writer{One{n:&mut Int}}
fn see(w:&Writer){print(w);}
async fn lose(w:&mut Writer)->Int{match &mut w{Writer.One{n:v}=>{v.set(20);yield;v.set(30);}}return 1;}
async fn win()->Int{return 9;}'''
        body = '''let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut ws=pool<Writer>(1);
let mut w=new(ws) Writer.One{n:&mut n};let mut s=runtime::select(->lose(&mut w),->win());
let r=s.await;print(r);BEFORE drop(->s);see(&w);drop(->w);drop(->n);
let next=ns.new(40);print(*next);return 1;'''
        source = self.program(body,helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'9\nWriter.One(20)\n40\n1\n')
        self.refused(source.replace('BEFORE','see(&w);'),'emprunt|réserv|incompatible')

    def test_owned_field_projection_does_not_escape_carrier(self):
        helpers = '''enum Boxed{Item{n:A<Int>},Empty{}}
async fn read(v:->Boxed)->Int{return match &v{Boxed.Item{n:r}=>{yield;*r},Boxed.Empty{}=>{0}};}'''
        source = helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let mut bs=pool<Boxed>(1);
let b=new(bs) Boxed.Item{n:<-n};let h=runtime::spawn(->read(->b));
match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}let next=ns.new(40);print(next);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n40\n')
        invalid=source.replace('->Int{return match','->&Int{return match').replace('yield;*r','yield;r').replace('Boxed.Empty{}=>{0}','Boxed.Empty{}=>{loop{}}')
        self.refused(invalid, 'durable|provenance|retour|emprunt')

    def test_nested_bool_and_direct_reference_result(self):
        helpers = '''enum View{One{n:&Int},Two{n:&Int}}
async fn read(v:&View)->&Int{return match &v{View.One{n:r}=>{yield;r},View.Two{n:r}=>{yield;r}};}
async fn check(v:&View)->Bool{return match &v{
View.One{n:_}=>{match &v{View.One{n:_}=>{yield;},View.Two{n:_}=>{}}true},
View.Two{n:_}=>{false}};}'''
        source=helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let mut vs=pool<View>(1);
let v=new(vs) View.One{n:&n};let a=runtime::spawn(->check(&v));match a.join(){Ok(b)=>{if b==true{print(1);}else{print(0);}},Err(_)=>{}}
let b=runtime::spawn(->read(&v));match b.join(){Ok(r)=>{print(*r);},Err(_)=>{}}drop(->v);drop(->n);}'''
        self.assertEqual(self.run_source(source).stdout,'1\n7\n')

    def test_projection_captured_by_child_and_launch_failure(self):
        helpers = '''enum Writer{One{n:&mut Int}}
async fn change(n:&mut Int)->Int{yield;n.set(30);return *n;}
async fn work(w:&mut Writer)->Int{let result=match &mut w{Writer.One{n:v}=>{
let child=change(v);BEFORE let r=child.await;v.set(40);r}};return result;}'''
        source = helpers+'''fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut ws=pool<Writer>(1);
let mut w=new(ws) Writer.One{n:&mut n};let h=runtime::spawn(->work(&mut w));
match h.join(){Ok(r)=>{print(r);},Err(_)=>{print(99);}}drop(->w);print(n);drop(->n);
let next=ns.new(50);print(next);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'30\n40\n50\n')
        self.refused(source.replace('BEFORE','v.set(20);'),'emprunt|réserv|incompatible')
        code=compile_source(source.replace('BEFORE',''))
        failed=inject_submission_failure(code,asynchronous=False)
        self.assertEqual(self.run_c_oracle(failed).stdout,'99\n7\n50\n')

    def test_shared_projection_cannot_escape_local_target(self):
        source='''enum View{Item{n:&Int}}
async fn bad()->&Int{let mut ns=pool<Int>(1);let n=ns.new(7);let mut vs=pool<View>(1);
let v=new(vs) View.Item{n:&n};return match &v{View.Item{n:r}=>{yield;r}};}
fn main(){let h=runtime::spawn(->bad());match h.join(){Ok(r)=>{print(*r);},Err(_)=>{}}}'''
        self.refused(source,'durable|provenance|retour|emprunt')

    def test_changed_owned_graph_is_not_an_empty_suspension_contract(self):
        interface=verify_program('''struct Inner{view:&Int} enum Outer{Item{inner:A<Inner>}}
fn change(inner:&mut Inner,n:&Int){inner.view=&*n;}''')
        declaration=Parser('''async fn modify(o:&mut Outer,n:&Int)->Int{
match &mut o{Outer.Item{inner:i}=>{change(i,n);yield;}}return 1;}''').parse()[0]
        summary=AsyncStructureEffectAnalyzer({'modify':declaration},interface.function_contracts,
            interface.enums,Error).infer('modify')
        self.assertTrue(summary.complete,summary.reason)
        self.assertTrue(summary.structure_fields)
        self.assertTrue(summary.suspension_complete,summary.suspension_reason)
        self.assertEqual(summary.suspension_result.structure_fields, summary.structure_fields)
        self.assertEqual({(index,field,origin.kind,origin.parameter,origin.field)
                          for index,fields in summary.suspension_result.structure_fields
                          for field,origins in fields for origin in origins},
                         {(0,'Item.inner/.view','parameter',1,'')})


if __name__ == '__main__':
    unittest.main()
