"""Scope-exit contract: compare semantic destruction order with executed C."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class ScopeExitTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def check_backends(self, program, expected, output=''):
        for source in ('allocator()', 'stack(65536)', 'pool<Int>(8)'):
            with self.subTest(source=source):
                result = self.execute('let mut memory = ' + source + '; ' + program +
                                      ' memory.reset(); let mut probe = new(memory) Int(99); print(probe);')
                destructions = [s for s in result.stderr.splitlines() if s.startswith('destroy ')]
                self.assertEqual(destructions, expected + ['destroy probe=99'])
                self.assertEqual(result.stdout, output + '99\n')
                self.assertEqual(result.stderr.count('reset\n'), 1)

    def test_normal_exit_closes_only_inner_scopes(self):
        self.check_backends(
            'let mut outer = new(memory) Int(1); '
            '{ let mut middle = new(memory) Int(2); { let mut inner = new(memory) Int(3); } } '
            'print(outer); drop(-> outer);',
            ['destroy inner=3', 'destroy middle=2', 'destroy outer=1'], '1\n')

    def test_void_return_closes_all_function_scopes(self):
        self.check_backends(
            'fn work(mem: &mut Allocator) { let mut outer = new(mem) Int(1); '
            '{ let mut middle = new(mem) Int(2); { let mut inner = new(mem) Int(3); return; } } '
            'let mut unreachable = new(mem) Int(4); } work(&mut memory);',
            ['destroy inner=3', 'destroy middle=2', 'destroy outer=1'])

    def test_scalar_return_cleans_before_caller_continues(self):
        self.check_backends(
            'fn work(mem: &mut Allocator, n: Int) -> Int { '
            'let mut outer = new(mem) Int(1); { let mut inner = new(mem) Int(2); return n; } } '
            'let mut result = work(&mut memory, 7); print(result);',
            ['destroy inner=2', 'destroy outer=1'], '7\n')

    def test_allocation_return_excludes_result_from_child_cleanup(self):
        self.check_backends(
            'fn work(mem: &mut Allocator) -> <- Int { '
            'let mut outer = new(mem) Int(1); { let mut inner = new(mem) Int(2); '
            '{ let mut result = new(mem) Int(3); return <- result; } } } '
            'let mut received = work(&mut memory); print(received); drop(-> received);',
            ['destroy inner=2', 'destroy outer=1', 'destroy result=3'], '3\n'
        )

    def test_explicit_drop_is_not_repeated_during_unwinding(self):
        self.check_backends(
            'fn work(mem: &mut Allocator) { let mut outer = new(mem) Int(1); '
            '{ let mut inner = new(mem) Int(2); drop(-> inner); return; } } work(&mut memory);',
            ['destroy inner=2', 'destroy outer=1'])

    def test_reception_order_is_preserved_during_return(self):
        self.check_backends(
            'fn work(mem: &mut Allocator) -> <- Int { let mut before = new(mem) Int(1); '
            'let mut result = { let mut temporary = new(mem) Int(2); '
            'let mut kept = new(mem) Int(3); <- kept }; '
            'let mut after = new(mem) Int(4); return <- result; } '
            'let mut result = work(&mut memory); print(result); drop(-> result);',
            ['destroy temporary=2', 'destroy after=4', 'destroy before=1', 'destroy kept=3'], '3\n')

    def test_local_sources_close_while_external_result_survives(self):
        self.check_backends(
            'fn work(mem: &mut Allocator) -> <- Int { let mut outer = new(mem) Int(1); '
            '{ let mut private = stack(65536); let mut local = new(private) Int(2); '
            'let mut middle = new(mem) Int(3); { let mut dropped = new(mem) Int(4); '
            'drop(-> dropped); let mut result = new(mem) Int(5); return <- result; } } } '
            'let mut result = work(&mut memory); print(result); drop(-> result);',
            ['destroy dropped=4', 'destroy middle=3', 'destroy local=2', 'destroy outer=1',
             'destroy result=5'], '5\n')

    def test_returned_source_cannot_be_closed_in_an_intermediate_scope(self):
        for source in ('allocator()', 'stack(65536)', 'pool<Int>(2)'):
            with self.subTest(source=source):
                self.rejected('fn wrong() -> <- Int { { let mut private = ' + source + '; '
                              '{ let mut result = new(private) Int(1); return <- result; } } } '
                              'let mut result = wrong(); print(result);', 'ne survit pas')

    def test_unreachable_allocations_have_no_generated_cleanup(self):
        code = compile_source('fn main() { let mut memory = pool<Int>(1); '
                              'let mut alive = new(memory) Int(1); return; '
                              'let mut unreachable = new(memory) Int(2); }')
        self.assertNotIn('"unreachable"', code)


if __name__ == '__main__':
    unittest.main()
