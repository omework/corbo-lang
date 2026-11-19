"""Owned-field replacement preserves borrowed descendants across async boundaries."""
import unittest
import test_select_source as sources
from crust import compile_source
from scheduler_faults import inject_submission_failure

TYPES='''struct Leaf{view:&Int} struct Root{item:A<Leaf>}
fn replace(root:&mut Root,p:&mut Pool<Leaf>,n:&Int){root.item=<-p.new(view:n);}
fn read(root:&Root)->Int{let leaf=&*root.item;return *leaf.view;}'''
MODIFY='''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&Int)->Int{
replace(root,p,n);yield;return 1;}'''
SETUP='''let mut values=pool<Int>(2);let old=values.new(7);let next=values.new(9);
let mut leaves=pool<Leaf>(2);let leaf=leaves.new(view:&old);
let mut roots=pool<Root>(1);let mut root=roots.new(item:<-leaf);'''

class AsyncOwnedBorrowWriteTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    program=staticmethod(sources.SelectSourceTests.program)

    def test_await_preserves_target_and_reuses_slot(self):
        body=SETUP+'''let n=modify(&mut root,&mut leaves,&next).await;print(n);
print(read(&root));drop(->root);drop(->next);let again=values.new(20);print(*again);return 1;'''
        for modify in (MODIFY,MODIFY.replace('replace(root,p,n);','root.item=<-p.new(view:n);')):
            with self.subTest(direct='root.item=' in modify):
                source=self.program(body,TYPES+modify)
                self.assertEqual(self.run_source(source).stdout,'1\n9\n20\n1\n')
                self.refused(source.replace('print(read(&root));','drop(->next);print(read(&root));'),
                             'emprunt|utilisé|détruit')

    def test_join_keeps_new_borrow(self):
        source=TYPES+MODIFY+'fn main(){'+SETUP+'''
let h=runtime::spawn(->modify(&mut root,&mut leaves,&next));
match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
print(read(&root));drop(->root);print(*next);}'''
        self.assertEqual(self.run_source(source).stdout,'1\n9\n9\n')
        failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
        self.assertEqual(failed.stdout,'7\n9\n')
        self.refused(source.replace('print(read(&root));','drop(->next);print(read(&root));'),
                     'emprunt|utilisé|détruit')

    def test_select_preserves_intermediate_borrow(self):
        helpers=TYPES+MODIFY+'async fn ready()->Int{return 99;}'
        body=SETUP+'''let mut s=runtime::select(->modify(&mut root,&mut leaves,&next),->ready());
let n=s.await;print(n);drop(->s);print(read(&root));drop(->root);print(*next);return 1;'''
        source=self.program(body,helpers)
        self.assertEqual(self.run_source(source).stdout,'99\n9\n9\n1\n')
        self.refused(source.replace('print(read(&root));','drop(->next);print(read(&root));'),
                     'emprunt|utilisé|détruit')

    def test_local_direct_replacement(self):
        body=SETUP+'''root.item=<-leaves.new(view:&next);yield;
print(read(&root));drop(->root);print(*next);return 1;'''
        source=self.program(body,TYPES)
        self.assertEqual(self.run_source(source).stdout,'9\n9\n1\n')
        self.refused(source.replace('print(read(&root));','drop(->next);print(read(&root));'),
                     'emprunt|utilisé|détruit')

    def test_mutable_target_remains_reserved(self):
        types=TYPES.replace('view:&Int','view:&mut Int').replace('n:&Int','n:&mut Int')
        setup=SETUP.replace('let old=', 'let mut old=').replace('let next=', 'let mut next=').replace('view:&old','view:&mut old')
        modify=MODIFY.replace('n:&Int','n:&mut Int')
        body=setup+'''let n=modify(&mut root,&mut leaves,&mut next).await;print(n);
print(read(&root));drop(->root);next=20;print(*next);return 1;'''
        for implementation in (modify,modify.replace('replace(root,p,n);','root.item=<-p.new(view:n);')):
            source=self.program(body,types+implementation)
            self.assertEqual(self.run_source(source).stdout,'1\n9\n20\n1\n')
            self.refused(source.replace('print(read(&root));','next=30;print(read(&root));'),'emprunt|utilisé')

    def test_short_target_cannot_escape_through_replacement(self):
        body=SETUP+'''drop(->next);{let mut short=pool<Int>(1);let n=short.new(11);
let r=modify(&mut root,&mut leaves,&n).await;print(r);}
print(read(&root));drop(->root);return 1;'''
        self.refused(self.program(body,TYPES+MODIFY),'emprunt|survi|durée|dépend')

    def test_successive_replacements_keep_suspended_target(self):
        helpers=TYPES+'''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&Int,last:&Int)->Int{
replace(root,p,n);yield;replace(root,p,last);return 1;}
async fn ready()->Int{return 99;}'''
        setup=SETUP.replace('pool<Int>(2)', 'pool<Int>(3)')+'let last=values.new(11);'
        selection='''let mut s=runtime::select(->modify(&mut root,&mut leaves,&next,&last),->ready());
let n=s.await;print(n);drop(->s);print(read(&root));drop(->root);return 1;'''
        source=self.program(setup+selection,helpers)
        self.assertEqual(self.run_source(source).stdout,'99\n9\n1\n')
        self.refused(source.replace('print(read(&root));','drop(->next);print(read(&root));'),'emprunt|utilisé')
        normal='''let n=modify(&mut root,&mut leaves,&next,&last).await;print(n);
print(read(&root));drop(->root);return 1;'''
        self.assertEqual(self.run_source(self.program(setup+normal,helpers)).stdout,'1\n11\n1\n')

    def test_conditional_replacement_preserves_both_targets(self):
        helpers=TYPES+'''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&Int,flag:Bool)->Int{
if flag {replace(root,p,n);}yield;return 1;}'''
        body=SETUP+'''let n=modify(&mut root,&mut leaves,&next,FLAG).await;print(n);
print(read(&root));drop(->root);return 1;'''
        for flag,value in (('true',9),('false',7)):
            source=self.program(body.replace('FLAG',flag),helpers)
            self.assertEqual(self.run_source(source).stdout,f'1\n{value}\n1\n')
            for target in ('old','next'):
                self.refused(source.replace('print(read(&root));',f'drop(->{target});print(read(&root));'),
                             'emprunt|utilisé')

if __name__=='__main__':unittest.main()
