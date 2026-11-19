"""Read borrowed leaves through recursive owned links in synchronous helpers."""
import unittest
import test_select_source as harness
from test_async_recursive_owned import SETUP

TYPES='enum Node{End{value:&Int},Link{next:A<Node>}}'
PEEK='''fn peek(n:&Node){match &n{
Node.End{value:v}=>{print(*v);},Node.Link{next:a}=>{match &a{
Node.End{value:v}=>{print(*v);},Node.Link{next:b}=>{match &b{
Node.End{value:v}=>{print(*v);},Node.Link{next:_}=>{print(0);}}}}}}}'''
SETUP_REF='let mut numbers=pool<Int>(1);let mut number=numbers.new(7);'+SETUP.replace('value:7','value:&number')

class RecursiveBorrowProjectionTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_read_deep_borrow_in_sync_helper(self):
        source=TYPES+PEEK+'fn main(){'+SETUP_REF+'peek(&top);drop(->top);number=8;print(*number);}'
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        self.refused(source.replace('peek(&top);','drop(->number);peek(&top);'),'emprunt|référenc')

    def test_async_state_calls_same_helper(self):
        source=self.program(SETUP_REF+'yield;peek(&top);drop(->top);number=8;return *number;',TYPES+PEEK)
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        invalid=source.replace('yield;peek(&top);','drop(->number);yield;peek(&top);')
        invalid=invalid.replace('number=8;return *number;', 'return 8;')
        self.refused(invalid,'emprunt|référenc')

    def test_mutable_borrowed_leaf_through_helper(self):
        helpers=TYPES.replace('&Int','&mut Int')+PEEK.replace('fn peek(', 'fn edit(').replace('n:&Node','n:&mut Node').replace('match &','match &mut ').replace('print(*v);','v.set(9);')
        setup=SETUP_REF.replace('value:&number','value:&mut number').replace('let top=', 'let mut top=')
        for asynchronous in (False,True):
            body=setup+'CHECK edit(&mut top);drop(->top);'
            source=(self.program(body+'return *number;',helpers) if asynchronous else
                    helpers+'fn main(){'+body+'print(*number);}')
            self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'9\n')
            self.refused(source.replace('CHECK','number=11;'),'emprunt|référenc|réserv')

    def test_nominal_borrowed_leaf_keeps_interior_descriptor(self):
        helpers='struct Point{x:Int}struct Outer{before:Int,part:Point}'+TYPES.replace('&Int','&Point')+PEEK.replace('print(*v);','print(v.x);')
        setup='let mut outer=Outer{before:99,part:Point{x:7}};'+SETUP.replace('value:7','value:&outer.part')
        for asynchronous in (False,True):
            body=setup+'CHECK peek(&top);drop(->top);outer.part.x=8;'
            source=(self.program(body+'return outer.part.x;',helpers) if asynchronous else
                    helpers+'fn main(){'+body+'print(outer.part.x);}')
            self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'7\n8\n')
            self.refused(source.replace('CHECK','outer.part.x=11;'),'emprunt|référenc|réserv')

if __name__=='__main__':unittest.main()
