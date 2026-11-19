"""New recursive graphs retain storage and borrow metadata through task factories."""
import unittest
import test_select_source as harness
from test_recursive_borrow_projections import PEEK

TYPES='enum Node{End{value:&Int},Link{next:A<Node>}}'
HELPERS=TYPES+PEEK+'''async fn own(n:->Node)-><-Node{yield;return <-n;}
fn make(ends:&mut Pool<Node>,links:&mut Pool<Node>,n:&Int)-><-own{
let end=new(ends)Node.End{value:n};let mid=new(links)Node.Link{next:<-end};
let top=new(links)Node.Link{next:<-mid};return <-own(->top);}
fn relay(t:->own)-><-own{return <-t;}'''
SETUP='''let mut ends=pool<Node>(1);let mut links=pool<Node>(2);
let mut numbers=pool<Int>(1);let mut number=numbers.new(7);'''

class FreshRecursiveFactoryTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_new_graph_after_factory_and_relay(self):
        for call in ('make(&mut ends,&mut links,&number)',
                     'relay(->make(&mut ends,&mut links,&number))'):
            source=HELPERS+'fn main(){'+SETUP+'let h=runtime::spawn(->'+call+''');
match h.join(){Ok(r)=>{CHECK peek(&r);drop(->r);},Err(_)=>{}}
number=8;let again=new(ends)Node.End{value:&number};peek(&again);}'''
            run=self.run_source(source.replace('CHECK',''))
            self.assertEqual(run.stdout,'7\n8\n')
            for name in ('end','mid','top'):
                self.assertEqual(run.stderr.count('destroy '+name+'=Node.'),1)
            self.refused(source.replace('CHECK','number=9;'),'emprunt|référenc|réserv')
            self.refused(source.replace('CHECK','').replace('match h.join()', 'drop(->ends);match h.join()'),
                         'source|pool|allocation|utilis')

    def test_new_graph_from_factory_inside_async(self):
        source=self.program(SETUP+'''let t=make(&mut ends,&mut links,&number);
let r=t.await;yield;CHECK peek(&r);drop(->r);number=8;return *number;''',HELPERS)
        self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'7\n8\n')
        self.refused(source.replace('CHECK','number=9;'),'emprunt|référenc|réserv')

    def test_conditional_factory_keeps_each_returned_shape(self):
        helpers=HELPERS.replace('links:&mut Pool<Node>,n:&Int)-><-own{',
            'links:&mut Pool<Node>,n:&Int,flag:bool)-><-own{'+
            'if flag{let single=new(ends)Node.End{value:n};return <-own(->single);}')
        for flag in ('true','false'):
            source=helpers+'fn main(){'+SETUP+'''
let h=runtime::spawn(->make(&mut ends,&mut links,&number,FLAG));
match h.join(){Ok(r)=>{CHECK peek(&r);drop(->r);},Err(_)=>{}}
number=8;print(*number);}'''.replace('FLAG',flag)
            self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'7\n8\n')
            self.refused(source.replace('CHECK','number=9;'),'emprunt|référenc|réserv')

if __name__=='__main__':unittest.main()
