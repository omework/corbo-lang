"""Mutable recursive projections keep the carrier capability until last use."""
import unittest
import test_select_source as harness
from test_recursive_borrow_results import PICK
from test_recursive_borrow_projections import TYPES, SETUP_REF

HELPERS=TYPES.replace('&Int','&mut Int')+PICK.replace('&Int','&mut Int').replace('&Node','&mut Node').replace('match &','match &mut ')
SETUP=SETUP_REF.replace('value:&number','value:&mut number').replace('let top=','let mut top=')

class RecursiveMutableResultTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_mutable_result_keeps_recursive_carriers(self):
        for asynchronous in (False,True):
            with self.subTest(asynchronous=asynchronous):
                body=SETUP+'''let mut spare=pool<Int>(1);let mut fallback=spare.new(99);
let mut view=pick(&mut top,&mut fallback);CHECK PAUSE view.set(8);drop(->top);'''
                body=body.replace('PAUSE','yield;' if asynchronous else '')
                source=(self.program(body+'return *number;',HELPERS) if asynchronous else
                        HELPERS+'fn main(){'+body+'print(*number);}')
                self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'8\n')
                for operation in ('drop(->top);','drop(->number);','number=9;'):
                    invalid=source.replace('CHECK',operation)
                    if operation=='drop(->top);':
                        invalid=invalid.replace('view.set(8);drop(->top);','view.set(8);')
                    if operation=='drop(->number);':
                        invalid=invalid.replace('return *number;','return 8;').replace('print(*number);','print(8);')
                    self.refused(invalid,'emprunt|référenc|réserv')

    def test_relay_preserves_deep_capability(self):
        helpers=HELPERS+'''fn relay(unused:Int,n:&mut Node,fallback:&mut Int)->&mut Int{
return pick(n,fallback);}'''
        body=SETUP+'''let mut spare=pool<Int>(1);let mut fallback=spare.new(99);
let mut view=relay(0,&mut top,&mut fallback);CHECK view.set(8);drop(->top);print(*number);'''
        source=helpers+'fn main(){'+body+'}'
        self.assertEqual(self.run_source(source.replace('CHECK','')).stdout,'8\n')
        self.refused(source.replace('CHECK','drop(->top);').replace(
            'view.set(8);drop(->top);','view.set(8);'),'emprunt|référenc|réserv')

if __name__=='__main__':unittest.main()
