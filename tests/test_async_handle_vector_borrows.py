"""Named borrows of allocated vector contents remain live across suspension."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / 'validation/open-async-owned-vector-borrow.crb').read_text()


def mutable_program(body):
    return BASE.replace('values: &Vector<A<Int>>', 'values: &mut Vector<A<Int>>').replace(
        'count(&values)', 'count(&mut values)').replace(
        'let view = &*values[0];\n    yield;\n    return *view;', body)


class AsyncHandleVectorBorrowTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_recorded_shared_borrow(self):
        self.assertEqual(self.run_source(BASE).stdout, '7\n8\n')
        self.refused(BASE.replace('let view =', 'let mut view =').replace(
            'return *view;', 'view.set(9);return *view;'), 'mutable|partagé')
        self.refused(BASE.replace('let view =', 'let view: Int ='), 'annotation|type')

    def test_mutable_borrow_last_use(self):
        body = 'let mut view=&mut *values[0];yield;view.set(9);*values[0]=10;return *values[0];'
        run = self.run_source(mutable_program(body))
        self.assertEqual(run.stdout, '10\n8\n')
        self.assertEqual(sum(line.startswith('destroy ') and line.endswith('=10')
                             for line in run.stderr.splitlines()), 1)
        self.refused(mutable_program(body.replace('*values[0]=10;', '*values[0]=10;print(*view);')),
                     'emprunt actif')
        self.refused(mutable_program(body.replace('yield;', 'yield;print(*values[0]);')),
                     'emprunt actif')
        self.refused(mutable_program(body).replace('values: &mut Vector', 'values: &Vector').replace(
            'count(&mut values)', 'count(&values)'), 'mutable')

    def test_reborrow_to_awaited_child(self):
        helper = 'async fn edit(n:&mut Int)->Int{yield;n.set(*n+2);return *n;}'
        body = 'let mut view=&mut *values[0];let result=edit(&mut *view).await;yield;view.set(result+1);return *view;'
        self.assertEqual(self.run_source(helper+mutable_program(body)).stdout, '10\n8\n')
        conflicting = body.replace('let result=edit(&mut *view).await;',
            'let task=edit(&mut *view);print(*view);let result=task.await;')
        self.refused(helper+mutable_program(conflicting), 'emprunt actif')

    def test_owned_vector_can_drop_after_last_use(self):
        source = BASE.replace('values: &Vector<A<Int>>', 'values: -> Vector<A<Int>>').replace(
            'count(&values)', 'count(-> values)').replace('    drop(-> values);', '').replace(
            'return *view;', 'let answer=*view;drop(-> values);return answer;')
        self.assertEqual(self.run_source(source).stdout, '7\n8\n')
        self.refused(source.replace('let answer=*view;drop(-> values);',
                                    'drop(-> values);let answer=*view;'), 'emprunt actif')

    def test_suspended_index_and_bounds(self):
        helper = 'async fn index()->Int{yield;return 0;}'
        source = helper+BASE.replace('values[0]', 'values[index().await]')
        self.assertEqual(self.run_source(source).stdout, '7\n8\n')
        source = source.replace('yield;return 0;', 'yield;return 1;')
        run = self.run_c_oracle(compile_source(source), expected_error='indice de Vector hors limites')
        self.assertEqual(run.stdout, '')


if __name__ == '__main__':
    unittest.main()
