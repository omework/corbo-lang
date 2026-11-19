"""Path-sensitive ownership and exactly-once cleanup for if/else."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source, Error

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class ConditionalTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def check_paths(self, body, expected, output=('', ''), prelude=''):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(4)'):
            for flag in (0, 1):
                with self.subTest(factory=factory, flag=flag):
                    result = self.execute(prelude + ' fn work(mem: &mut Allocator, n: Int) { '
                                          + body + ' } let mut memory = ' + factory + '; '
                                          'work(&mut memory, ' + str(flag) + ');')
                    self.assertEqual(result.stdout, output[flag])
                    self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                     expected[flag])

    def test_conditional_drop_is_cleaned_once_on_both_paths(self):
        self.check_paths('let mut data = new(mem) Int(42); '
                         'if n == 1 { -> data; drop(-> data); }',
                         [['destroy data=42']] * 2)

    def test_access_requires_validity_on_every_continuing_path(self):
        self.rejected('fn work(mem: &mut Allocator, n: Int) { let mut data = new(mem) Int(42); '
                      'if n == 1 { -> data; drop(-> data); } print(data); } '
                      'work(&mut memory, 0);', 'plus utilisable')

    def test_returning_path_does_not_invalidate_continuation(self):
        self.check_paths('let mut data = new(mem) Int(42); '
                         'if n == 1 { -> data; drop(-> data); return; } print(data);',
                         [['destroy data=42']] * 2, ('42\n', ''))

    def test_branch_locals_and_sources_are_closed_before_continuation(self):
        self.check_paths('let mut outer = new(mem) Int(1); '
                         'if n == 1 { let mut private = stack(65536); '
                         'let mut local = new(private) Int(2); print(local); } '
                         'else { let mut other = new(mem) Int(3); print(other); } print(outer);',
                         [['destroy other=3', 'destroy outer=1'],
                          ['destroy local=2', 'destroy outer=1']], ('3\n1\n', '2\n1\n'))

    def test_else_if_and_scalar_returns(self):
        result = self.execute('fn choose(n: Int) -> Int { if n < 0 { return 7; } '
                              'else if n == 0 { return 8; } else { return 9; } } '
                              'let mut a = choose(-1); let mut b = choose(0); let mut c = choose(1); '
                              'print(a); print(b); print(c);')
        self.assertEqual(result.stdout, '7\n8\n9\n')

    def test_all_returning_paths_omit_unreachable_code_and_cleanup(self):
        # U1 requires an explicit use even when every path cleans the value.
        code = compile_source('fn main() { let mut memory = pool<Int>(1); '
                              'let mut data = new(memory) Int(42); print(data); '
                              'if true { return; } else { return; } '
                              'let mut unreachable = new(memory) Int(99); }')
        self.assertNotIn('"unreachable"', code)
        result = self.execute('fn main() { let mut memory = pool<Int>(1); '
                              'let mut data = new(memory) Int(42); print(data); '
                              'if false { return; } else { return; } }')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.splitlines(), ['destroy data=42', 'reclaim data'])

    def test_scalar_function_requires_return_on_every_path(self):
        self.rejected('fn choose(n: Int) -> Int { if n == 1 { return 7; } } '
                      'let mut result = choose(1); print(result);', 'retour.*attendu scalar')
        self.rejected('fn choose() -> Int { if true { return; } else { return 7; } } '
                      'let mut result = choose(); print(result);', 'retour conditionnel')

    def test_return_unwinds_nested_scopes_and_private_sources(self):
        self.check_paths('let mut outer = new(mem) Int(1); { '
                         'let mut private = pool<Int>(2); let mut middle = new(private) Int(2); '
                         'if n == 1 { let mut inner = new(mem) Int(3); print(inner); return; } '
                         'print(middle); } print(outer);',
                         [['destroy middle=2', 'destroy outer=1'],
                          ['destroy inner=3', 'destroy middle=2', 'destroy outer=1']],
                         ('2\n1\n', '3\n'))

    def test_reused_slot_does_not_revive_conditional_cleanup(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(
                    'fn work(mem: &mut Pool<Int>, n: Int) { let mut data = new(mem) Int(1); '
                    'address(data); if n == 1 { -> data; drop(-> data); } '
                    'let mut fresh = new(mem) Int(2); address(fresh); print(fresh); } '
                    'let mut memory = pool<Int>(2); work(&mut memory, ' + str(flag) + ');')
                lines = result.stdout.splitlines()
                self.assertEqual(lines[0] == lines[1], bool(flag))
                self.assertEqual(lines[2:], ['2'])
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy data=1', 'destroy fresh=2'] if flag else
                                 ['destroy fresh=2', 'destroy data=1'])

    def test_reset_at_join_cleans_maybe_live_allocation_once(self):
        self.check_paths('let mut data = new(mem) Int(1); '
                         'if n == 1 { -> data; drop(-> data); } mem.reset(); '
                         'let mut fresh = new(mem) Int(2); print(fresh);',
                         [['destroy data=1', 'destroy fresh=2']] * 2, ('2\n', '2\n'))

    def test_callee_return_effects_are_merged_back_into_caller_cleanup(self):
        self.check_paths('let mut data = new(mem) Int(1); print(data); clear(mem, n); '
                         'let mut fresh = new(mem) Int(2); print(fresh);',
                         [['destroy fresh=2', 'destroy data=1'],
                          ['destroy data=1', 'destroy fresh=2']], ('1\n2\n', '1\n2\n'),
                         'fn clear(mem: &mut Allocator, n: Int) { '
                         'if n == 1 { mem.reset(); return; } }')

    def test_callee_may_reset_caller_allocation_only_without_future_access(self):
        self.rejected('fn clear(mem: &mut Allocator, n: Int) { '
                      'if n == 1 { mem.reset(); return; } } '
                      'let mut data = new(memory) Int(42); clear(&mut memory, 0); print(data);',
                      'reset interdit')

    def test_borrow_used_only_on_surviving_path_does_not_block_early_return(self):
        self.check_paths('let mut data = new(mem) Int(42); let mut view = &data; '
                         'if n == 1 { -> data; drop(-> data); return; } print(view);',
                         [['destroy data=42']] * 2, ('42\n', ''))

    def test_borrow_in_other_branch_is_not_active_on_drop_path(self):
        self.check_paths('let mut data = new(mem) Int(42); let mut view = &data; '
                         'if n == 1 { -> data; drop(-> data); } else { print(view); }',
                         [['destroy data=42']] * 2, ('42\n', ''))

    def test_borrow_used_after_join_blocks_branch_drop(self):
        self.rejected('fn work(mem: &mut Allocator, n: Int) { '
                      'let mut data = new(mem) Int(42); let mut view = &data; '
                      'if n == 1 { -> data; drop(-> data); } print(view); } '
                      'work(&mut memory, 0);', 'emprunt encore utilisé')

    def test_guard_is_forwarded_when_owned_value_enters_another_function(self):
        self.check_paths('let mut data = new(mem) Int(42); '
                         'if n == 1 { print(data); } consume(-> data);',
                         [['destroy data=42']] * 2, ('', '42\n'),
                         'fn consume(mut data: -> Int) { drop(-> data); }')

    def test_local_guard_does_not_escape_with_unconditional_allocation_return(self):
        self.check_paths('let mut data = make(mem, n); print(data);',
                         [['destroy fresh=42']] * 2, ('42\n', '42\n42\n'),
                         'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
                         'let mut fresh = new(mem) Int(42); if n == 1 { print(fresh); } return <- fresh; }')

    def test_round_trip_to_branch_restores_original_access(self):
        self.check_paths('let mut data = new(mem) Int(42); '
                         'if n == 1 { -> data; <- data; } print(data);',
                         [['destroy data=42']] * 2, ('42\n', '42\n'))

    def test_different_reception_orders_at_join_have_explicit_diagnostic(self):
        self.rejected('let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); '
                      'if true { -> a; <- a; } print(a); print(b);', 'ordre de réception différent')

    def test_conditional_allocation_returns_can_select_the_same_allocation(self):
        result = self.execute('fn make(mem: &mut Allocator) -> <- Int { let mut data = new(mem) Int(42); '
                              'if true { -> data; return <- data; } return <- data; } '
                              'let mut data = make(&mut memory); print(data);')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=42'])

    def test_condition_comparison_operands_evaluate_left_to_right(self):
        result = self.execute('fn mark(n: Int) -> Int { print(n); return n; } '
                              'if mark(1) < mark(2) { let mut yes = 7; print(yes); } '
                              'else { let mut no = 8; print(no); }')
        self.assertEqual(result.stdout, '1\n2\n7\n')
        for source in ('if 1 {}', 'if true {', 'if true {} else',
                       'let mut a = new(memory) Int(1); if a == 1 {}'):
            with self.subTest(source=source), self.assertRaises(Error):
                compile_source(self.with_source(source))

    def test_conditional_reset_cannot_destroy_an_earlier_prepared_argument(self):
        self.rejected('fn clear(mem: &mut Allocator, n: Int) -> Int { '
                      'if n == 1 { mem.reset(); return 1; } return 0; } '
                      'fn outer(mut data: -> Int, n: Int) {} let mut data = new(memory) Int(42); '
                      'outer(-> data, clear(&mut memory, 0));', 'reset interdit')

    def test_conditional_return_in_argument_cleans_prepared_values(self):
        self.check_paths('consume(-> new(mem) Int(1), -> { '
                         'if n == 1 { return; } let mut kept = new(mem) Int(2); <- kept });',
                         [['destroy kept=2', 'destroy a=1'], ['destroy a=1']],
                         prelude='fn consume(mut a: -> Int, mut b: -> Int) {}')

    def test_branch_sources_and_names_cannot_escape(self):
        self.rejected('if true { let mut private = pool<Int>(1); } '
                      'let mut data = new(private) Int(1);', 'variable inconnue')
        self.rejected('let mut data = new(memory) Int(1); if true { drop(-> data); }',
                      'transférer avec ->')

    def test_sequential_joins_keep_independent_allocation_states(self):
        result = self.execute(
            'fn work(mem: &mut Pool<Int>, n: Int) { '
            'let mut a = new(mem) Int(1); let mut b = new(mem) Int(2); let mut c = new(mem) Int(3); '
            'if n == 0 { -> a; drop(-> a); } '
            'if n == 1 { -> b; drop(-> b); } '
            'if n != 2 { -> c; drop(-> c); } '
            'let mut fresh = new(mem) Int(4); print(fresh); mem.reset(); } '
            'let mut memory = pool<Int>(4); work(&mut memory, 0); '
            'work(&mut memory, 1); work(&mut memory, 2);')
        self.assertEqual(result.stdout, '4\n4\n4\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')], [
            'destroy a=1', 'destroy c=3', 'destroy fresh=4', 'destroy b=2',
            'destroy b=2', 'destroy c=3', 'destroy fresh=4', 'destroy a=1',
            'destroy fresh=4', 'destroy c=3', 'destroy b=2', 'destroy a=1'])

    def test_enum_arms_keep_global_order_after_conditional_drop_and_reuse(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(
                    'enum E { A { n: Int }, B { x: Int, y: Int } } '
                    'fn work(mem: &mut Pool<E>, n: Int) { '
                    'let mut a = new(mem) E.A { n: 1 }; let mut b = new(mem) E.B { x: 2, y: 3 }; '
                    'if n == 1 { -> a; drop(-> a); } '
                    'let mut fresh = new(mem) E.A { n: 4 }; print(b); print(fresh); mem.reset(); } '
                    'let mut memory = pool<E>(2); work(&mut memory, ' + str(flag) + ');')
                self.assertEqual(result.stdout, 'E.B(2, 3)\nE.A(4)\n')
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy a=E.A', 'destroy fresh=E.A', 'destroy b=E.B'] if flag else
                                 ['destroy fresh=E.A', 'destroy b=E.B', 'destroy a=E.A'])

    def test_nested_returning_paths_consume_owned_parameter_once(self):
        self.check_paths('let mut data = new(mem) Int(42); consume(-> data, n);',
                         [['destroy data=42']] * 2,
                         prelude='fn consume(mut data: -> Int, n: Int) { '
                         'if n == 1 { if true { return; } else { return; } } else { return; } }')

    def test_later_source_calls_receive_null_for_conditionally_dead_allocation(self):
        prelude = ('fn clear(mem: &mut Allocator) { mem.reset(); } '
                   'fn forward(mem: &mut Allocator) { clear(mem); } ')
        body = ('let mut data = new(mem) Int(42); '
                'if n == 1 { -> data; drop(-> data); } forward(mem);')
        self.check_paths(body, [['destroy data=42']] * 2, prelude=prelude)
        code = compile_source(prelude + 'fn work(mem: &mut Allocator, n: Int) { ' + body +
                              '} let mut memory = allocator(); work(&mut memory, 1);')
        self.assertRegex(code, r'\? (?:a\d+|cleanup\d+) : NULL')


if __name__ == '__main__':
    unittest.main()
