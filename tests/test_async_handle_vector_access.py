"""Read/write allocated Int contents through async Vector<A<Int>> captures."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from test_async_handle_vector_captures import BASE, ROOT

class AsyncHandleVectorAccessTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_read_content_after_suspension(self):
        source=(ROOT/'validation/open-async-owned-vector-read.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        self.refused(source.replace('return *values[0];','return values[0];'),
                     'Int|tableau|cop|transfert|index')

    def test_mutate_content_without_replacing_handle(self):
        source=BASE.replace('values: &Vector<A<Int>>','values: &mut Vector<A<Int>>').replace(
            'return values.len();','*values[0]=*values[0]+2;yield;return *values[0];').replace(
            'count(&values)','count(&mut values)').replace('    drop(-> values);','    print(*values[0]);drop(-> values);')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n9\n8\n')
        self.assertEqual(sum(line.startswith('destroy ') and line.endswith('=9')
                             for line in run.stderr.splitlines()),1)
        self.refused(source.replace('values: &mut Vector<A<Int>>','values: &Vector<A<Int>>').replace(
            'count(&mut values)','count(&values)'), 'mutable|lecture|immuable')
        self.refused(source.replace('match h.join()', 'print(*values[0]);match h.join()'),
                     'emprunt|réserv')

    def test_suspended_index_and_rhs(self):
        helpers='async fn index()->Int{yield;return 0;}async fn next()->Int{yield;return 12;}'
        source=helpers+BASE.replace('values: &Vector<A<Int>>','values: &mut Vector<A<Int>>').replace(
            'return values.len();','*values[index().await]=next().await;return *values[0];').replace(
            'count(&values)','count(&mut values)')
        self.assertEqual(self.run_source(source).stdout,'12\n8\n')

    def test_out_of_bounds_precedes_rhs_effect(self):
        helpers='async fn effect()->Int{print(123);return 9;}'
        source=helpers+BASE.replace('values: &Vector<A<Int>>','values: &mut Vector<A<Int>>').replace(
            'return values.len();','*values[1]=effect().await;return 0;').replace(
            'count(&values)','count(&mut values)')
        run=self.run_c_oracle(compile_source(source),expected_error='indice de Vector hors limites')
        self.assertNotIn('123',run.stdout)

if __name__=='__main__':unittest.main()
