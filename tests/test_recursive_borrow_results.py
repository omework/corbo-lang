"""References returned from recursive owned descendants retain their target."""
import unittest
import test_select_source as harness
from test_recursive_borrow_projections import TYPES, SETUP_REF

PICK='''fn pick(n:&Node,fallback:&Int)->&Int{return match &n{
Node.End{value:v}=>{v},Node.Link{next:a}=>{match &a{
Node.End{value:v}=>{v},Node.Link{next:b}=>{match &b{
Node.End{value:v}=>{v},Node.Link{next:_}=>{fallback}}}}}};}'''

class RecursiveBorrowResultTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_detached_shared_target_after_helper(self):
        source=TYPES+PICK+'fn main(){'+SETUP_REF+'''let mut spare=pool<Int>(1);let fallback=spare.new(99);
let view=pick(&top,&fallback);drop(->top);CHECK print(*view);number=8;print(*number);}'''
        self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'7\n8\n')
        self.refused(source.replace('CHECK','number=9;'),'emprunt|référenc|réserv')
        self.refused(source.replace('CHECK','drop(->number);').replace('number=8;print(*number);',''),
                     'emprunt|référenc|réserv')

    def test_async_state_keeps_returned_target_after_porter_drop(self):
        source=self.program(SETUP_REF+'''let mut spare=pool<Int>(1);let fallback=spare.new(99);
let view=pick(&top,&fallback);drop(->top);CHECK yield;let value=*view;number=8;return value;''',TYPES+PICK)
        self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'7\n')
        self.refused(source.replace('CHECK','number=9;'),'emprunt|référenc|réserv')
        self.refused(source.replace('CHECK','drop(->number);').replace('number=8;',''),
                     'emprunt|référenc|réserv')

if __name__=='__main__':unittest.main()
