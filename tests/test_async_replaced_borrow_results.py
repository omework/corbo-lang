"""Borrowed results keep the old snapshot or the installed descendant's target."""
from pathlib import Path
import unittest
from crust import verify_program,Parser,Error,compile_source
from async_structure_effects import AsyncStructureEffectAnalyzer
from scheduler_faults import inject_submission_failure
import test_select_source as sources

TYPES='''struct Leaf{view:&Int} struct Root{item:A<Leaf>}
fn replace(root:&mut Root,p:&mut Pool<Leaf>,n:&Int){root.item=<-p.new(view:n);}
fn borrow(root:&Root)->&Int{let leaf=&*root.item;return leaf.view;}'''
SETUP='''let mut values=pool<Int>(3);let old=values.new(7);let next=values.new(9);let fallback=values.new(11);
let mut leaves=pool<Leaf>(2);let leaf=leaves.new(view:&old);let mut roots=pool<Root>(1);
let mut root=roots.new(item:<-leaf);'''

def worker(old=False):
    return '''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&Int)->&Int{
let saved=borrow(root);print(*saved);replace(root,p,n);yield;return '''+('saved' if old else 'borrow(root)')+';}'

class AsyncReplacedBorrowResultTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    program=staticmethod(sources.SelectSourceTests.program)

    def test_recorded_return(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-replaced-descendant-borrow.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'9\n')
        self.refused(source.replace('drop(->old);','drop(->next);'),'emprunt|utilisé')

    def test_contract_distinguishes_old_and_new(self):
        interface=verify_program(TYPES)
        for old in (False,True):
            node=Parser(worker(old)).parse()[0]
            summary=AsyncStructureEffectAnalyzer({'modify':node},interface.function_contracts,interface.enums,Error).infer('modify')
            self.assertTrue(summary.complete,summary.reason)
            self.assertEqual({(t.kind,t.parameter,t.field) for t in summary.completion_result.reference_targets},
                             {('detached_field_parameter',0,'.item/.view')} if old else {('parameter',2,'')})

    def test_join_preserves_exact_target_and_launch_failure(self):
        for old in (False,True):
            released,retained,value=('next','old',7) if old else ('old','next',9)
            source=TYPES+worker(old)+'fn main(){'+SETUP+'''
let h=runtime::spawn(->modify(&mut root,&mut leaves,&next));
let view=match h.join(){Ok(view)=>{view},Err(_)=>{&fallback}};
drop(->root);drop(->RELEASED);print(*view);}'''
            source=source.replace('RELEASED',released)
            self.assertEqual(self.run_source(source).stdout,f'7\n{value}\n')
            self.refused(source.replace(f'drop(->{released});',f'drop(->{retained});'),'emprunt|utilisé')
            failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
            self.assertEqual(failed.stdout,'11\n')

    def test_direct_await_and_relay(self):
        for old in (False,True):
            released,retained,value=('next','old',7) if old else ('old','next',9)
            helpers=TYPES+worker(old)+'''async fn relay(root:&mut Root,p:&mut Pool<Leaf>,n:&Int)->&Int{
let view=modify(root,p,n).await;yield;return view;}'''
            body=SETUP+'''print(*fallback);let view=relay(&mut root,&mut leaves,&next).await;
drop(->root);drop(->RELEASED);print(*view);return 1;'''
            source=self.program(body.replace('RELEASED',released),helpers)
            self.assertEqual(self.run_source(source).stdout,f'11\n7\n{value}\n1\n')
            self.refused(source.replace(f'drop(->{released});',f'drop(->{retained});'),'emprunt|utilisé')

    def test_conditional_replacement_returns_either_target(self):
        helpers=TYPES+'''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&Int,flag:Bool)->&Int{
if flag{replace(root,p,n);}yield;return borrow(root);}'''
        body=SETUP+'''print(*fallback);let view=modify(&mut root,&mut leaves,&next,FLAG).await;
drop(->root);print(*view);return 1;'''
        for flag,value in (('true',9),('false',7)):
            source=self.program(body.replace('FLAG',flag),helpers)
            self.assertEqual(self.run_source(source).stdout,f'11\n{value}\n1\n')
            for target in ('old','next'):
                self.refused(source.replace('print(*view);',f'drop(->{target});print(*view);'),'emprunt|utilisé')

    def test_select_winner_returns_new_target_after_cleanup(self):
        helpers=TYPES+worker()+'''async fn other(n:&Int)->&Int{yield;yield;return n;}'''
        body=SETUP+'''let mut s=runtime::select(->modify(&mut root,&mut leaves,&next),->other(&fallback));
let view=s.await;drop(->s);drop(->root);drop(->old);print(*view);return 1;'''
        source=self.program(body,helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n1\n')
        self.refused(source.replace('drop(->old);','drop(->next);'),'emprunt|utilisé')

if __name__=='__main__':unittest.main()
