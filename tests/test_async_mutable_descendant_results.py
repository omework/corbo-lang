"""Mutable descendant results reserve their field and target until last use."""
from pathlib import Path
import unittest
from crust import compile_source
from scheduler_faults import inject_submission_failure
import test_select_source as sources

TYPES='''struct Leaf{view:&mut Int} struct Root{item:A<Leaf>}
fn replace(root:&mut Root,p:&mut Pool<Leaf>,n:&mut Int){root.item=<-p.new(view:n);}
fn borrow(root:&mut Root)->&mut Int{let mut leaf=&mut *root.item;return &mut *leaf.view;}
fn read(root:&Root)->Int{let leaf=&*root.item;return *leaf.view;}'''
MODIFY='''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&mut Int)->&mut Int{
replace(root,p,n);yield;return borrow(root);}'''
SETUP='''let mut values=pool<Int>(2);let mut old=values.new(7);let mut next=values.new(9);
let mut leaves=pool<Leaf>(2);let leaf=leaves.new(view:&mut old);let mut roots=pool<Root>(1);
let mut root=roots.new(item:<-leaf);'''

class AsyncMutableDescendantResultTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    program=staticmethod(sources.SelectSourceTests.program)

    def test_recorded_return_and_launch_failure(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-replaced-mutable-result.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'20\n30\n')
        failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
        self.assertEqual(failed.stdout,'30\n')

    def test_join_reserves_carrier_and_target(self):
        source=TYPES+MODIFY+'fn main(){'+SETUP+'''
let h=runtime::spawn(->modify(&mut root,&mut leaves,&mut next));
match h.join(){Ok(view)=>{BEFORE view.set(20);print(*view);print(read(&root));},Err(_)=>{}}
drop(->root);next=30;print(*next);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'20\n20\n30\n')
        for operation in ('print(read(&root));','next=40;'):
            self.refused(source.replace('BEFORE',operation),'emprunt|utilisé|réserv')

    def test_direct_await_keeps_reservation_until_last_use(self):
        body=SETUP+'''let mut view=modify(&mut root,&mut leaves,&mut next).await;
BEFORE view.set(20);print(*view);print(read(&root));drop(->root);next=30;return *next;'''
        source=self.program(body,TYPES+MODIFY)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'20\n20\n30\n')
        for operation in ('print(read(&root));','next=40;','drop(->root);',
                          'root.item=<-leaves.new(view:&mut old);'):
            self.refused(source.replace('BEFORE',operation),'emprunt|utilisé|réserv')

    def test_sync_descendant_return_uses_last_use(self):
        source=TYPES+'fn main(){'+SETUP+'''drop(->next);let mut view=borrow(&mut root);
BEFORE view.set(20);print(read(&root));drop(->root);print(*old);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'20\n20\n')
        self.refused(source.replace('BEFORE','print(read(&root));'),'emprunt|utilisé|réserv')

    def test_relay_and_select_preserve_reservations(self):
        helpers=TYPES+MODIFY+'''async fn relay(root:&mut Root,p:&mut Pool<Leaf>,n:&mut Int)->&mut Int{
let mut view=modify(root,p,n).await;yield;return view;}
async fn other(n:&mut Int)->&mut Int{yield;yield;yield;return n;}'''
        body=SETUP+'''let mut extras=pool<Int>(1);let mut extra=extras.new(11);
let mut s=runtime::select(->relay(&mut root,&mut leaves,&mut next),->other(&mut extra));
let mut view=s.await;drop(->s);BEFORE view.set(20);print(*view);
print(read(&root));drop(->root);next=30;return *next;'''
        source=self.program(body,helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'20\n20\n30\n')
        for op in ('print(read(&root));','next=40;'):
            self.refused(source.replace('BEFORE',op),'emprunt|utilisé|réserv')

if __name__=='__main__':unittest.main()
