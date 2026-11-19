"""Allocated if-expression values, explicit transfers and branch cleanup."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source, Error

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class IfExpressionTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def check_sources(self, program, expected, output=('', '')):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(6)'):
            for flag in (0, 1):
                with self.subTest(factory=factory, flag=flag):
                    result = self.execute('let mut memory = ' + factory + '; let mut flag = ' + str(flag) + '; ' + program)
                    self.assertEqual(result.stdout, output[flag])
                    self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                     expected[flag])

    def test_selected_branch_cleans_temporaries_then_receiver_cleans_result(self):
        self.check_sources(
            'let mut before = new(memory) Int(1); print(before); let mut result = if flag == 1 { '
            'let mut temp = new(memory) Int(99); print(temp); let mut a = new(memory) Int(10); <- a '
            '} else { let mut b = new(memory) Int(20); <- b }; '
            'let mut after = new(memory) Int(2); print(after); print(result);',
            [['destroy after=2', 'destroy b=20', 'destroy before=1'],
             ['destroy temp=99', 'destroy after=2', 'destroy a=10', 'destroy before=1']],
            ['1\n2\n20\n', '1\n99\n2\n10\n'])

    def test_else_if_selects_only_one_allocation_and_keeps_its_address(self):
        for flag in (-1, 0, 1):
            with self.subTest(flag=flag):
                result = self.execute(
                    'let mut memory = pool<Int>(1); let mut flag = ' + str(flag) + '; '
                    'let mut result = if flag < 0 { let mut a = new(memory) Int(10); address(a); <- a } '
                    'else if flag == 0 { let mut b = new(memory) Int(20); address(b); <- b } '
                    'else { let mut c = new(memory) Int(30); address(c); <- c }; '
                    'address(result); print(result); drop(-> result); '
                    'let mut fresh = new(memory) Int(40); address(fresh); print(fresh); memory.reset();')
                lines = result.stdout.splitlines()
                self.assertEqual(lines[0], lines[1])
                self.assertEqual(lines[0], lines[3])
                self.assertEqual([lines[2], lines[4]], [str((flag + 2) * 10), '40'])
                self.assertEqual(len([s for s in result.stderr.splitlines() if s.startswith('destroy ')]), 2)

    def test_parent_transfer_invalidates_original_and_preserves_unselected_value(self):
        self.check_sources(
            'let mut data = new(memory) Int(10); let mut result = if flag == 1 { -> data; <- data } '
            'else { let mut b = new(memory) Int(20); <- b }; print(result); memory.reset();',
            [['destroy b=20', 'destroy data=10'], ['destroy data=10']], ['20\n', '10\n'])
        self.rejected('let mut data = new(memory) Int(10); let mut result = if true { -> data; <- data } '
                      'else { let mut b = new(memory) Int(20); <- b }; print(data); print(result);',
                      'plus utilisable')

    def test_two_parent_candidates_transfer_only_the_selected_allocation(self):
        self.check_sources(
            'let mut a = new(memory) Int(10); let mut b = new(memory) Int(20); '
            'let mut result = if flag == 1 { -> a; <- a } else { -> b; <- b }; '
            'print(result); drop(-> result); memory.reset();',
            [['destroy b=20', 'destroy a=10'], ['destroy a=10', 'destroy b=20']], ['20\n', '10\n'])

    def test_reassignment_evaluates_expression_before_old_destruction(self):
        self.check_sources(
            'fn read(a: &Int) -> Int { print(a); return 20; } '
            'let mut data = new(memory) Int(10); data = if flag == 1 { '
            'let mut a = new(memory) Int(read(&data)); <- a } else { '
            'let mut b = new(memory) Int(read(&data)); <- b }; print(data);',
            [['destroy data=10', 'destroy b=20'], ['destroy data=10', 'destroy a=20']],
            ['10\n20\n', '10\n20\n'])

    def test_reassignment_can_select_original_without_destroying_it_twice(self):
        self.check_sources(
            'let mut data = new(memory) Int(10); data = if flag == 1 { -> data; <- data } '
            'else { let mut fresh = new(memory) Int(20); <- fresh }; print(data);',
            [['destroy data=10', 'destroy fresh=20'], ['destroy data=10']], ['20\n', '10\n'])

    def test_last_borrow_in_rhs_ends_before_replacement_cleanup(self):
        self.check_sources(
            'fn read(a: &Int) -> Int { print(a); return 20; } '
            'let mut data = new(memory) Int(10); let mut view = &data; '
            'data = if flag == 1 { let mut a = new(memory) Int(read(view)); <- a } '
            'else { let mut b = new(memory) Int(read(view)); <- b }; print(data);',
            [['destroy data=10', 'destroy b=20'], ['destroy data=10', 'destroy a=20']],
            ['10\n20\n', '10\n20\n'])
        self.rejected('let mut data = new(memory) Int(10); let mut view = &data; '
                      'data = if true { let mut a = new(memory) Int(20); <- a } '
                      'else { let mut b = new(memory) Int(30); <- b }; print(view); print(data);',
                      'emprunt actif')

    def test_function_can_receive_and_return_expression_result(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { let mut selected = if n == 1 { '
            'let mut a = new(mem) Int(10); <- a } else { let mut b = new(mem) Int(20); <- b }; '
            'return <- selected; } let mut result = make(&mut memory, flag); print(result);',
            [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])

    def test_function_returning_branch_does_not_need_an_expression_value(self):
        self.check_sources(
            'fn work(mem: &mut Allocator, n: Int) { let mut outer = new(mem) Int(99); print(outer); '
            'let mut selected = if n == 1 { return; } else { let mut b = new(mem) Int(20); <- b }; '
            'print(selected); } work(&mut memory, flag);',
            [['destroy b=20', 'destroy outer=99'], ['destroy outer=99']], ['99\n20\n', '99\n'])

    def test_owned_function_returns_and_if_values_keep_the_same_function_source(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'let mut selected = if n == 1 { let mut a = new(mem) Int(10); return <- a; } '
            'else { let mut b = new(mem) Int(20); <- b }; return <- selected; } '
            'let mut result = make(&mut memory, flag); print(result);',
            [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])

    def test_all_function_returning_branches_omit_receiver_and_continuation(self):
        source = ('fn main() { let mut memory = pool<Int>(1); let mut data = new(memory) Int(10); print(data); '
                  'let mut never_received = if true { return; } else { return; }; '
                  'let mut unreachable = new(memory) Int(20); }')
        self.assertNotIn('"unreachable"', compile_source(source))
        result = self.execute(source)
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=10'])

    def test_nested_expression_blocks_transfer_through_each_scope(self):
        self.check_sources(
            'let mut result = { let mut selected = if flag == 1 { let mut a = new(memory) Int(10); <- a } '
            'else { let mut b = new(memory) Int(20); <- b }; <- selected }; print(result);',
            [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])

    def test_expression_in_arguments_preserves_left_to_right_order(self):
        self.check_sources(
            'fn mark(n: Int) -> Int { print(n); return n; } '
            'fn consume(mut a: -> Int, n: Int) { print(a); print(n); } '
            'consume(-> if mark(flag) == 1 { let mut a = new(memory) Int(10); <- a } '
            'else { let mut b = new(memory) Int(20); <- b }, mark(7));',
            [['destroy b=20'], ['destroy a=10']], ['0\n7\n20\n7\n', '1\n7\n10\n7\n'])

    def test_borrowed_if_temporary_is_cleaned_by_its_caller_scope(self):
        self.check_sources(
            'fn read(a: &Int) { print(a); } '
            'read(&if flag == 1 { let mut a = new(memory) Int(10); <- a } '
            'else { let mut b = new(memory) Int(20); <- b }); memory.reset();',
            [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])

    def test_result_reset_and_live_borrow_checks_keep_its_source(self):
        prefix = ('let mut result = if true { let mut a = new(memory) Int(10); <- a } '
                  'else { let mut b = new(memory) Int(20); <- b }; ')
        self.rejected(prefix + 'let mut view = &result; memory.reset(); print(view);', 'reset interdit')
        self.rejected(prefix + 'drop(-> result); print(result);', 'plus utilisable')
        self.rejected(prefix + 'let mut view = &result; drop(-> result); print(view);', 'emprunt encore utilisé')

    def test_missing_else_or_value_is_rejected(self):
        cases = [
            'let mut result = if true { let mut a = new(memory) Int(10); <- a }; print(result);',
            'let mut result = if true { let mut a = new(memory) Int(10); <- a } else {}; print(result);',
            'let mut result = if true {} else { let mut b = new(memory) Int(20); <- b }; print(result);',
        ]
        for source in cases:
            with self.subTest(source=source):
                self.rejected(source, 'expression.*(else|terminer)')

    def test_scalar_tail_produces_branch_value_and_does_not_return_from_function(self):
        result = self.execute(
            'fn choose() -> Int { let result = if true { let n = 1; n } '
            'else { let n = 2; n }; print(result); return 7; } '
            'let result = choose(); print(result);')
        self.assertEqual(result.stdout, '1\n7\n')

    def test_different_candidate_types_are_rejected(self):
        self.rejected('enum E { A } let mut other = pool<E>(1); '
                      'let mut result = if true { let mut a = new(memory) Int(10); <- a } '
                      'else { let mut b = new(other) E.A; <- b }; print(result);', 'même type requis')

    def test_different_pools_of_identical_type_are_supported(self):
        result = self.execute('let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                              'let mut result = if true { let mut a = new(memory) Int(10); <- a } '
                              'else { let mut b = new(other) Int(20); <- b }; print(result);')
        self.assertEqual(result.stdout, '10\n')
        self.assertEqual(result.stderr.count('destroy a=10'), 1)

    def test_branch_local_source_and_names_cannot_escape(self):
        self.rejected('let mut result = if true { let mut local = pool<Int>(1); '
                      'let mut a = new(local) Int(10); <- a } '
                      'else { let mut b = new(memory) Int(20); <- b }; print(result);', 'source.*ne survit pas')
        self.rejected('let mut result = if true { let mut a = new(memory) Int(10); <- a } '
                      'else { let mut b = new(memory) Int(20); <- b }; print(a); print(result);', 'variable inconnue')

    def test_enum_variants_share_public_pool_and_dispatch_actual_cleanup(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(
                    'enum E { A { n: Int }, B { x: Int, y: Int } } let mut memory = pool<E>(1); '
                    'let mut flag = ' + str(flag) + '; let mut result = if flag == 1 { '
                    'let mut a = new(memory) E.A { n: 10 }; <- a } else { '
                    'let mut b = new(memory) E.B { x: 20, y: 30 }; <- b }; print(result); memory.reset();')
                self.assertEqual(result.stdout, 'E.A(10)\n' if flag else 'E.B(20, 30)\n')
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy a=E.A' if flag else 'destroy b=E.B'])

    def test_selection_inside_parent_conditional_hands_cleanup_over_once(self):
        self.check_sources(
            'let mut data = new(memory) Int(10); if flag == 1 { -> data; '
            'let mut picked = if true { -> data; <- data } else { -> data; <- data }; '
            'print(picked); } memory.reset();',
            [['destroy data=10']] * 2, ['', '10\n'])

    def test_unused_receiver_is_rejected(self):
        self.rejected('let mut unused = if true { let mut a = new(memory) Int(10); <- a } '
                      'else { let mut b = new(memory) Int(20); <- b };', 'sans usage explicite')

    def test_truncated_if_expression_sources_have_checked_diagnostics(self):
        valid = ('fn main() { let mut memory = pool<Int>(1); let mut result = if true { '
                 'let mut a = new(memory) Int(10); <- a } else if false { '
                 'let mut b = new(memory) Int(20); <- b } else { '
                 'let mut c = new(memory) Int(30); <- c }; print(result); }')
        for end in range(len(valid) + 1):
            with self.subTest(end=end):
                try:
                    compile_source(valid[:end])
                except Error:
                    pass


if __name__ == '__main__':
    unittest.main()
