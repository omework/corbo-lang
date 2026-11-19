"""Async captures preserve vectors of owned handles and their source pools."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-owned-vector-capture.crb').read_text()

class AsyncHandleVectorCaptureTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_shared_capture_reserves_carrier_and_items(self):
        self.assertEqual(self.run_source(BASE).stdout,'1\n8\n')
        for operation in ('drop(-> values);','drop(-> numbers);','values.push(-> numbers.new(2));'):
            source=BASE.replace('match h.join()',operation+'match h.join()')
            if operation=='drop(-> values);':
                source=source.replace('    drop(-> values);\n','')
            self.refused(source,'emprunt|réserv|source|pool|allocation')

    def test_mutable_capture_and_child_await(self):
        helpers='''async fn count(values:&mut Vector<A<Int>>)->Int{yield;return values.len();}
async fn relay(values:&mut Vector<A<Int>>)->Int{yield;return count(values).await;}'''
        source=helpers+BASE[BASE.index('fn main()'):].replace('count(&values)','relay(&mut values)')
        self.assertEqual(self.run_source(source).stdout,'1\n8\n')
        self.refused(source.replace('match h.join()','print(values.len());match h.join()'),
                     'emprunt|réserv')

    def test_owned_capture_destroys_items_and_releases_slots(self):
        source=BASE.replace('values: &Vector<A<Int>>','values: ->Vector<A<Int>>').replace(
            'count(&values)','count(->values)').replace('    drop(-> values);\n','')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'1\n8\n')
        self.assertEqual(sum(line.startswith('destroy ') and line.endswith('=7')
                             for line in run.stderr.splitlines()),1)
        self.refused(source.replace('match h.join()','drop(-> numbers);match h.join()'),
                     'source|pool|allocation|emprunt')

    def test_owned_capture_cleanup_before_execution(self):
        source=BASE.replace('values: &Vector<A<Int>>','values: ->Vector<A<Int>>').replace(
            'count(&values)','count(->values)').replace('    drop(-> values);\n','')
        inactive=source.replace('let h = runtime::spawn(-> count(->values));',
                                'let task=count(->values);drop(->task);').replace(
            'match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }','')
        run=self.run_source(inactive)
        self.assertEqual(run.stdout,'8\n')
        self.assertEqual(sum(line.startswith('destroy ') and line.endswith('=7')
                             for line in run.stderr.splitlines()),1)
        failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
        self.assertEqual(failed.stdout,'99\n8\n')
        self.assertEqual(sum(line.startswith('destroy ') and line.endswith('=7')
                             for line in failed.stderr.splitlines()),1)

    def test_element_type_is_not_erased_by_capture(self):
        self.refused(BASE.replace('values: &Vector<A<Int>>','values: &Vector<Int>'),
                     'type|attendu|capture')

if __name__=='__main__':unittest.main()
