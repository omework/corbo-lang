"""Finite values of recursive owned types cross async boundaries without relocation."""
import unittest
import test_select_source as harness
from crust import compile_source, verify_program
from scheduler_faults import inject_submission_failure

TYPES='enum Node{End{value:Int},Link{next:A<Node>}}'
SETUP='''let mut ends=pool<Node>(1);let mut links=pool<Node>(2);
let end=new(ends) Node.End{value:7};let mid=new(links) Node.Link{next:<-end};
let top=new(links) Node.Link{next:<-mid};'''

class AsyncRecursiveOwnedTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_return_graph_and_reuse_all_slots(self):
        helpers=TYPES+'async fn own(n:->A<Node>)-><-A<Node>{yield;return <-n;}'
        source=helpers+'fn main(){'+SETUP+'''let h=runtime::spawn(->own(->top));
match h.join(){Ok(r)=>{drop(->r);},Err(_)=>{}}
let again=new(ends) Node.End{value:9};let a=new(links) Node.Link{next:<-again};
let b=new(links) Node.Link{next:<-a};drop(->b);}'''
        verify_program(source)
        for failed in (False,True):
            code=compile_source(source)
            run=self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1) if failed else code)
            destroyed=[line for line in run.stderr.splitlines() if line.startswith('destroy')]
            self.assertEqual(destroyed[:3],['destroy end=Node.End','destroy mid=Node.Link','destroy top=Node.Link'])
            self.assertEqual(len(destroyed),6)
        self.refused(source.replace('let h=runtime::spawn','drop(->ends);let h=runtime::spawn'),'source|pool|allocation|utilis')

    def test_nested_match_with_suspension(self):
        helpers=TYPES+'''async fn inspect(n:&Node)->Int{let value=match &n{
Node.End{value:v}=>{v},Node.Link{next:a}=>{yield;match &a{
Node.End{value:v}=>{v},Node.Link{next:b}=>{yield;match &b{
Node.End{value:v}=>{v},Node.Link{next:_}=>{0}}}}}};return value;}'''
        source=helpers+'fn main(){'+SETUP+'''let h=runtime::spawn(->inspect(&top));
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}drop(->top);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('match h.join()', 'drop(->top);match h.join()'),'emprunt|réserv|référenc')

    def test_local_pools_and_inactive_task_cleanup(self):
        helpers=TYPES+'async fn own(n:->A<Node>)-><-A<Node>{yield;return <-n;}'
        source=self.program(SETUP+'''let task=own(->top);drop(->task);
let again=new(ends) Node.End{value:9};print(again);return 1;''',helpers)
        self.assertEqual(self.run_source(source).stdout,'Node.End(9)\n1\n')

    def test_synchronous_helpers_inspect_relay_and_destroy(self):
        helpers=TYPES+'''fn peek(n:&Node){match &n{
Node.End{value:v}=>{print(v);},Node.Link{next:a}=>{match &a{
Node.End{value:v}=>{print(v);},Node.Link{next:b}=>{match &b{
Node.End{value:v}=>{print(v);},Node.Link{next:_}=>{print(0);}}}}}}}
fn relay(n:->A<Node>)-><-A<Node>{return <-n;}
fn discard(n:->A<Node>){drop(->n);}'''
        source=self.program(SETUP+'''yield;peek(&top);let received=relay(->top);
discard(->received);let again=new(ends) Node.End{value:9};peek(&again);return 1;''',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n1\n')

    def test_returned_descendant_keeps_stored_reference(self):
        helpers='enum Node{End{value:&Int},Link{next:A<Node>}}'+'''
async fn own(n:->A<Node>)-><-A<Node>{yield;return <-n;}'''
        setup=SETUP.replace('value:7','value:&number')
        source=helpers+'fn main(){let mut numbers=pool<Int>(1);let mut number=numbers.new(7);'+setup+'''
let h=runtime::spawn(->own(->top));match h.join(){Ok(r)=>{CHECK print(r);drop(->r);},Err(_)=>{}}
drop(->number);}'''
        for declaration in ('let h=', 'let h:runtime::Handle<A<Node>>='):
            case=source.replace('let h=', declaration)
            self.run_source(case.replace('CHECK',''))
            self.refused(case.replace('CHECK','number=8;'),'emprunt|référenc|utilis')

if __name__=='__main__':unittest.main()
