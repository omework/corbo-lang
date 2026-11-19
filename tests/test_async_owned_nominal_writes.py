"""Owned descendants keep nominal reference targets through async replacement."""
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

TYPES='''struct Point{x:Int}struct Pair{a:Point,b:Point}
struct Leaf{view:&Point}struct Root{item:A<Leaf>}
fn replace(root:&mut Root,p:&mut Pool<Leaf>,n:&Point){root.item=<-p.new(view:n);}
fn read(root:&Root)->Int{let leaf=&*root.item;let target=leaf.view;return target.x;}'''
MODIFY='''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&Point)->Int{
replace(root,p,n);yield;return 1;}'''
SETUP='''let mut pair=Pair{a:Point{x:7},b:Point{x:9}};
let mut leaves=pool<Leaf>(2);let leaf=leaves.new(view:&pair.a);
let mut roots=pool<Root>(1);let mut root=roots.new(item:<-leaf);'''

class AsyncOwnedNominalWriteTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_await_direct_and_helper_replacements(self):
        body=SETUP+'''let n=modify(&mut root,&mut leaves,&pair.b).await;print(n);
print(read(&root));drop(->root);pair.b.x=20;print(pair.b.x);return 1;'''
        for modify in (MODIFY,MODIFY.replace('replace(root,p,n);','root.item=<-p.new(view:n);')):
            source=self.program(body,TYPES+modify)
            self.assertEqual(self.run_source(source).stdout,'1\n9\n20\n1\n')
            self.refused(source.replace('print(read(&root));','pair.b.x=30;print(read(&root));'),
                         'emprunt|référenc|réserv|utilisé')

    def test_join_failure_retains_old_target(self):
        source=TYPES+MODIFY+'fn main(){'+SETUP+'''
let h=runtime::spawn(->modify(&mut root,&mut leaves,&pair.b));
match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
print(read(&root));drop(->root);pair.b.x=20;print(pair.b.x);}'''
        self.assertEqual(self.run_source(source).stdout,'1\n9\n20\n')
        failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
        self.assertEqual(failed.stdout,'7\n20\n')
        for field in ('a','b'):
            self.refused(source.replace('print(read(&root));',f'pair.{field}.x=30;print(read(&root));'),
                         'emprunt|référenc|réserv|utilisé')

    def test_select_preserves_suspended_target(self):
        source=self.program(SETUP+'''let mut s=runtime::select(->modify(&mut root,&mut leaves,&pair.b),->ready());
let n=s.await;print(n);drop(->s);print(read(&root));drop(->root);pair.b.x=20;print(pair.b.x);return 1;''',
            TYPES+MODIFY+'async fn ready()->Int{return 99;}')
        self.assertEqual(self.run_source(source).stdout,'99\n9\n20\n1\n')
        self.refused(source.replace('print(read(&root));','pair.b.x=30;print(read(&root));'),
                     'emprunt|référenc|réserv|utilisé')

    def test_mutable_target_and_reborrow(self):
        types=TYPES.replace('view:&Point','view:&mut Point').replace('n:&Point','n:&mut Point')
        types=types.replace('let target=leaf.view;', 'let target=&*leaf.view;')
        setup=SETUP.replace('view:&pair.a','view:&mut pair.a')
        modify=MODIFY.replace('n:&Point','n:&mut Point')
        body=setup+'''let n=modify(&mut root,&mut leaves,&mut pair.b).await;print(n);
print(read(&root));drop(->root);pair.b.x=20;print(pair.b.x);return 1;'''
        for implementation in (modify,modify.replace('replace(root,p,n);','root.item=<-p.new(view:n);')):
            source=self.program(body,types+implementation)
            self.assertEqual(self.run_source(source).stdout,'1\n9\n20\n1\n')
            self.refused(source.replace('print(read(&root));','pair.b.x=30;print(read(&root));'),
                         'emprunt|référenc|réserv|utilisé')

    def test_conditional_replacement_keeps_both_targets(self):
        modify='''async fn modify(root:&mut Root,p:&mut Pool<Leaf>,n:&Point,flag:Bool)->Int{
            if flag{replace(root,p,n);}yield;return 1;}'''
        for flag,expected in (('true',9),('false',7)):
            source=self.program(SETUP+'''let n=modify(&mut root,&mut leaves,&pair.b,FLAG).await;
print(n);print(read(&root));drop(->root);return 1;'''.replace('FLAG',flag),TYPES+modify)
            self.assertEqual(self.run_source(source).stdout,f'1\n{expected}\n1\n')
            for field in ('a','b'):
                self.refused(source.replace('print(read(&root));',f'pair.{field}.x=30;print(read(&root));'),
                             'emprunt|référenc|réserv|utilisé')

    def test_short_interior_target_is_refused(self):
        source=self.program(SETUP+'''{let short=Pair{a:Point{x:11},b:Point{x:13}};
let n=modify(&mut root,&mut leaves,&short.b).await;print(n);}
print(read(&root));drop(->root);return 1;''',TYPES+MODIFY)
        self.refused(source,'emprunt|survi|durée|dépend|détruit')

if __name__=='__main__':unittest.main()
