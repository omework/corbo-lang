"""Waits delegated to synchronous helpers retain recursive results."""
from pathlib import Path
import unittest
import test_select_source as harness
from test_async_recursive_owned import SETUP
from crust import compile_source, verify_program
from scheduler_faults import inject_submission_failure

ROOT=Path(__file__).resolve().parents[1]

class RecursiveJoinHelperTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_recorded_public_handle_join(self):
        source=(ROOT/'validation/open-recursive-join-helper.crb').read_text()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'Node.End(9)\n')
        destroyed=[line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed[:3],['destroy end=Node.End','destroy mid=Node.Link','destroy top=Node.Link'])
        self.refused(source.replace('let r=finish(->h);','drop(->ends);let r=finish(->h);'),
                     'source|pool|allocation|utilis')

    def test_join_result_keeps_deep_reference(self):
        helpers='''enum Node{End{value:&Int},Link{next:A<Node>}}
async fn own(n:->Node)-><-Node{yield;return <-n;}
fn finish(h:->runtime::Handle<A<Node>>)-><-Result<A<Node>,runtime::Error>{return <-h.join();}'''
        source=helpers+'fn main(){let mut numbers=pool<Int>(1);let mut number=numbers.new(7);'+SETUP.replace('value:7','value:&number')+'''
let h=runtime::spawn(->own(->top));let result=finish(->h);
match result{Ok(r)=>{CHECK print(r);drop(->r);},Err(_)=>{}}drop(->number);}'''
        self.run_source(source.replace('CHECK',''))
        self.refused(source.replace('CHECK','number=8;'),'emprunt|référenc|utilis')

    def test_two_helpers_terminal_variant_and_launch_failure(self):
        base=(ROOT/'validation/open-recursive-join-helper.crb').read_text()
        relay='''fn relay(h:->runtime::Handle<A<Node>>)-><-Result<A<Node>,runtime::Error>{
return <-finish(->h);}'''
        source=base.replace('fn main()', relay+'fn main()').replace('let r=finish(->h);','let r=relay(->h);')
        self.assertEqual(self.run_source(source).stdout,'Node.End(9)\n')
        verify_program(source)
        failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
        self.assertEqual(failed.stdout,'Node.End(9)\n')
        self.assertEqual(failed.stderr.count('destroy end=Node.End'),1)
        self.assertEqual(failed.stderr.count('destroy mid=Node.Link'),1)
        self.assertEqual(failed.stderr.count('destroy top=Node.Link'),1)
        terminal=source.replace(SETUP,'''let mut ends=pool<Node>(1);let top=new(ends) Node.End{value:7};''')
        self.assertEqual(self.run_source(terminal).stdout,'Node.End(9)\n')

    def test_async_caller_cannot_hide_blocking_join(self):
        source=(ROOT/'validation/open-recursive-join-helper.crb').read_text()
        helpers,body=source.split('fn main(){',1)
        body=body[:-1]+'return 1;'
        self.refused(self.program(body,helpers),'join réservé au code synchrone')

if __name__=='__main__':unittest.main()
