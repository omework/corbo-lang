"""Borrowed Int results retain their owning Vector<A<Int>> after await/join."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / 'validation/open-async-handle-vector-borrow-return.crb').read_text()


class AsyncHandleVectorBorrowReturnTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_recorded_shared_result_and_last_use(self):
        source = BASE.replace('print(*n);', 'print(*n);*values[0]=9;')
        self.assertEqual(self.run_source(source).stdout, '7\n8\n')
        for action in ('drop(-> values);', '*values[0]=9;', 'values=<-vectors.new();'):
            with self.subTest(action=action):
                self.refused(BASE.replace('print(*n);', action+'print(*n);'), 'emprunt|réserv|dépend|vivant')
        self.refused(BASE.replace('values: &Vector<A<Int>>', 'values: -> Vector<A<Int>>').replace(
            'count(&values)', 'count(-> values)').replace('    drop(-> values);', ''),
            'durable|paramètre|local')

    def test_mutable_result(self):
        source = BASE.replace('values: &Vector<A<Int>>', 'values: &mut Vector<A<Int>>').replace(
            '-> &Int', '-> &mut Int').replace('let view = &*', 'let mut view = &mut *').replace(
            'count(&values)', 'count(&mut values)').replace(
            'print(*n);', '*n=11;print(*n);*values[0]=12;')
        run = self.run_source(source)
        self.assertEqual(run.stdout, '11\n8\n')
        self.assertEqual(sum(line.startswith('destroy ') and line.endswith('=12')
                             for line in run.stderr.splitlines()), 1)
        self.refused(source.replace('*n=11;', 'print(*values[0]);*n=11;'), 'emprunt|réserv')
        self.refused(source.replace('*values[0]=12;', '*values[0]=12;print(*n);'), 'emprunt|réserv')

    def test_result_through_awaited_relay(self):
        for mode in ('ref', 'mut'):
            mutable = mode == 'mut'
            signature = '&mut' if mutable else '&'
            source = BASE.replace('async fn count',
                f'async fn relay(values:{signature} Vector<A<Int>>)->{signature} Int{{'
                f'let {"mut " if mutable else ""}view=count({signature} *values).await;yield;return view;}}'
                'async fn count').replace('runtime::spawn(-> count(', 'runtime::spawn(-> relay(')
            if mutable:
                source = source.replace('values: &Vector', 'values: &mut Vector').replace(
                    'count(values: &mut Vector<A<Int>>) -> &Int',
                    'count(values: &mut Vector<A<Int>>) -> &mut Int').replace(
                    'let view = &*', 'let mut view = &mut *').replace('relay(&values)', 'relay(&mut values)').replace(
                    'print(*n);', '*n=13;print(*n);')
            with self.subTest(mode=mode):
                self.assertEqual(self.run_source(source).stdout, ('13' if mutable else '7')+'\n8\n')
                self.refused(source.replace('print(*n);', 'drop(-> values);print(*n);'), 'emprunt|réserv')

    def test_borrow_result_used_inside_async(self):
        helper = '''async fn work(values:&mut Vector<A<Int>>)->Int{
            let view=count(&*values).await;yield;print(*view);*values[0]=14;return *values[0];}
        '''
        source = helper+BASE.replace('runtime::spawn(-> count(&values))',
            'runtime::spawn(-> work(&mut values))').replace('print(*n);', 'print(n);')
        self.assertEqual(self.run_source(source).stdout, '7\n14\n8\n')
        self.refused(source.replace('*values[0]=14;', '*values[0]=14;print(*view);'), 'emprunt actif')

    def test_sync_write_reserves_target_during_rhs(self):
        helper = 'fn read(v:&Vector<A<Int>>)->Int{return *v[0]+1;}'
        source = helper+BASE.replace('print(*n);', 'print(*n);*values[0]=read(&values);print(*values[0]);')
        self.assertEqual(self.run_source(source).stdout, '7\n8\n8\n')
        self.refused(source.replace('v:&Vector', 'v:&mut Vector').replace('read(&values)', 'read(&mut values)'),
                     'emprunt|réserv')

    def test_sync_write_checks_bounds_before_rhs(self):
        helper = 'fn effect()->Int{print(123);return 9;}'
        source = helper+BASE.replace('print(*n);', 'print(*n);*values[1]=effect();')
        run = self.run_c_oracle(compile_source(source), expected_error='indice de Vector hors limites')
        self.assertNotIn('123', run.stdout)


if __name__ == '__main__':
    unittest.main()
