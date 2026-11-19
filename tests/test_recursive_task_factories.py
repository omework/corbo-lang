"""Recursive owned graphs retain concrete metadata through published contracts."""
import unittest
import test_select_source as harness
from test_async_recursive_owned import TYPES, SETUP

class RecursiveTaskFactoryTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_factory_and_task_relay_keep_descendant_variants(self):
        helpers=TYPES+'''async fn own(n:->Node)-><-Node{yield;return <-n;}
fn make(n:->Node)-><-own{return <-own(->n);}
fn relay(t:->own)-><-own{return <-t;}'''
        for call in ('make(->top)', 'relay(->make(->top))'):
            source=helpers+'fn main(){'+SETUP+'let h=runtime::spawn(->'+call+''');
match h.join(){Ok(r)=>{print(r);drop(->r);},Err(_)=>{}}
let again=new(ends) Node.End{value:9};print(again);}'''
            run=self.run_source(source)
            self.assertTrue(run.stdout.endswith('Node.End(9)\n'),run.stdout)
            self.assertEqual(run.stderr.count('destroy end=Node.End'),1)
            self.assertEqual(run.stderr.count('destroy mid=Node.Link'),1)
            self.assertEqual(run.stderr.count('destroy top=Node.Link'),1)
            self.refused(source.replace('match h.join()', 'drop(->ends);match h.join()'),
                         'source|pool|allocation|utilis')

    def test_factory_preserves_recursive_stored_reference(self):
        helpers='enum Node{End{value:&Int},Link{next:A<Node>}}'+'''
async fn own(n:->Node)-><-Node{yield;return <-n;}
fn make(n:->Node)-><-own{return <-own(->n);}
fn relay(t:->own)-><-own{return <-t;}'''
        source=helpers+'fn main(){let mut numbers=pool<Int>(1);let mut number=numbers.new(7);'+SETUP.replace('value:7','value:&number')+'''
let h=runtime::spawn(->relay(->make(->top)));
match h.join(){Ok(r)=>{CHECK print(r);drop(->r);},Err(_)=>{}}drop(->number);}'''
        for call in ('relay(->make(->top))', 'relay(->own(->top))'):
            case=source.replace('relay(->make(->top))',call)
            self.run_source(case.replace('CHECK',''))
            self.refused(case.replace('CHECK','number=8;'),'emprunt|référenc|utilis')

    def test_nonreturning_owner_keeps_deep_pool_until_completion(self):
        helpers=TYPES+'''async fn consume(n:->Node)->Int{yield;drop(->n);return 7;}
fn make(n:->Node)-><-consume{return <-consume(->n);}'''
        source=helpers+'fn main(){'+SETUP+'''let h=runtime::spawn(->make(->top));
CHECK match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}
let again=new(ends) Node.End{value:9};print(again);}'''
        self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'7\nNode.End(9)\n')
        self.refused(source.replace('CHECK','drop(->ends);'),'source|pool|allocation|utilis')

if __name__=='__main__':unittest.main()
