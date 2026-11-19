"""Existing owned-field replacement rules across async waits and suspension."""
import unittest
from crust import verify_program, compile_source, Parser, Error
from async_structure_effects import AsyncStructureEffectAnalyzer
from scheduler_faults import inject_submission_failure
import test_select_source as sources

TYPES='''struct Root{item:A<Int>}
fn replace(root:&mut Root,p:&mut Pool<Int>,n:Int){root.item=<-p.new(n);}
fn read(root:&Root)->Int{return *root.item;}'''
MODIFY='''async fn modify(root:&mut Root,p:&mut Pool<Int>,q:&mut Pool<Int>)->Int{
replace(root,p,9);yield;replace(root,q,11);return 1;}'''
SETUP='''let mut first=pool<Int>(1);let old=first.new(7);let mut roots=pool<Root>(1);
let mut root=roots.new(item:<-old);let mut p=pool<Int>(1);let mut q=pool<Int>(1);'''


class AsyncOwnedFieldWriteTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    program=staticmethod(sources.SelectSourceTests.program)

    def test_contract_keeps_suspended_and_final_sources(self):
        interface=verify_program(TYPES)
        node=Parser(MODIFY).parse()[0]
        summary=AsyncStructureEffectAnalyzer({'modify':node},interface.function_contracts,
                                             interface.enums,Error).infer('modify')
        self.assertTrue(summary.complete,summary.reason)
        self.assertTrue(summary.suspension_complete,summary.suspension_reason)
        for result,index in ((summary.suspension_result,1),(summary.completion_result,2)):
            self.assertEqual([(parameter,path,{(c.kind,c.source.kind,c.source.index) for c in child.candidates})
                              for parameter,path,child in result.owned_field_writes],
                             [(0,'.item',{('fresh','source_parameter',index)})])

    def test_join_applies_replacement_and_cleanup(self):
        source=TYPES+MODIFY+'fn main(){'+SETUP+'''
let h=runtime::spawn(->modify(&mut root,&mut p,&mut q));
match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*root.item);drop(->root);
let a=first.new(20);let b=p.new(30);let c=q.new(40);print(a);print(b);print(c);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'1\n11\n20\n30\n40\n')
        self.assertEqual(run.stderr.count('destroy old=7\n'),1)
        failed=self.run_c_oracle(inject_submission_failure(compile_source(source), asynchronous=False, at=1))
        self.assertEqual(failed.stdout,'7\n20\n30\n40\n')
        self.assertEqual(failed.stderr.count('destroy old=7\n'),1)

    def test_direct_await_and_direct_field_assignment(self):
        body=SETUP+'''let n=modify(&mut root,&mut p,&mut q).await;print(n);
print(read(&root));drop(->root);let a=p.new(20);print(*a);return 1;'''
        for modify in (MODIFY,MODIFY.replace('replace(root,p,9);','root.item=<-p.new(9);')
                                      .replace('replace(root,q,11);','root.item=<-q.new(11);')):
            self.assertEqual(self.run_source(self.program(body,TYPES+modify)).stdout,'1\n11\n20\n1\n')

    def test_select_loser_retains_suspended_replacement(self):
        helpers=TYPES+MODIFY+'async fn ready()->Int{return 99;}'
        body=SETUP+'''let mut s=runtime::select(->modify(&mut root,&mut p,&mut q),->ready());
let n=s.await;print(n);drop(->s);print(read(&root));drop(->root);
let a=first.new(20);let b=p.new(30);print(*a);print(*b);return 1;'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'99\n9\n20\n30\n1\n')

    def test_replacement_pool_must_survive_receiver(self):
        body=SETUP+'''{let mut short=pool<Int>(1);
let n=modify(&mut root,&mut short,&mut q).await;print(n);}
print(read(&root));drop(->root);return 1;'''
        # The intermediate allocation is destroyed before the short pool ends.
        self.assertEqual(self.run_source(self.program(body,TYPES+MODIFY)).stdout,'1\n11\n1\n')
        bad=body.replace('modify(&mut root,&mut short,&mut q)', 'modify(&mut root,&mut p,&mut short)')
        self.refused(self.program(bad,TYPES+MODIFY),'pool|source|survi|durée|dépend')

    def test_enum_descendant_replacement_in_select(self):
        helpers=TYPES+'''enum Outer{Item{root:A<Root>}}
fn read_outer(o:&Outer)->Int{match &o{Outer.Item{root:r}=>{return read(r);}}}
async fn modify(o:&mut Outer,p:&mut Pool<Int>,q:&mut Pool<Int>)->Int{
match &mut o{Outer.Item{root:r}=>{replace(r,p,9);yield;replace(r,q,11);}}return 1;}
async fn ready()->Int{return 99;}'''
        body=SETUP+'''let mut os=pool<Outer>(1);let mut o=new(os) Outer.Item{root:<-root};
let mut s=runtime::select(->modify(&mut o,&mut p,&mut q),->ready());
let n=s.await;print(n);drop(->s);print(read_outer(&o));drop(->o);return 1;'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'99\n9\n1\n')

    def test_receiver_transferred_into_child_uses_child_lifetime(self):
        body=SETUP+'''{root ->;let mut local=pool<Int>(1);
root.item=<-local.new(9);yield;print(read(&root));drop(->root);}
let again=first.new(20);print(*again);return 1;'''
        self.assertEqual(self.run_source(self.program(body,TYPES)).stdout,'9\n20\n1\n')


if __name__=='__main__':unittest.main()
