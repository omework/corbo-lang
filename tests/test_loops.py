"""Iteration cleanup, break exits and memory states at the backedge."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source, Error

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class LoopTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def check_sources(self, program, expected, output=''):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(4)'):
            with self.subTest(factory=factory):
                result = self.execute('let mut memory = ' + factory + '; ' + program)
                self.assertEqual(result.stdout, output)
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')], expected)

    def test_break_cleans_iteration_and_keeps_parent_source_available(self):
        self.check_sources('loop { let mut temp = new(memory) Int(42); print(temp); break; } '
                           'memory.reset(); let mut after = new(memory) Int(7); print(after);',
                           ['destroy temp=42', 'destroy after=7'], '42\n7\n')

    def test_nested_blocks_and_private_sources_are_cleaned_before_break(self):
        self.check_sources('let mut parent = new(memory) Int(1); loop { '
                           'let mut outer = new(memory) Int(2); let seen_outer = *outer; { let mut private = stack(65536); '
                           'let mut middle = new(private) Int(3); let seen_middle = *middle; '
                           '{ let mut inner = new(memory) Int(4); let seen_inner = *inner; break; } } } '
                           'print(parent);',
                           ['destroy inner=4', 'destroy middle=3', 'destroy outer=2', 'destroy parent=1'], '1\n')

    def test_pool_slot_is_reused_across_iterations_and_guards_are_reactivated(self):
        result = self.execute(
            'let mut memory = pool<Int>(1); let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'loop { let mut temp = new(memory) Int(42); address(temp); '
            'if *state == 1 { break; } state.set(1); } print(state); memory.reset();')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2:], ['1'])
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy temp=42', 'destroy temp=42', 'destroy state=1'])

    def test_three_iterations_with_branch_local_values(self):
        self.check_sources('let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'loop { let mut temp = new(memory) Int(42); let seen_temp = *temp; '
                           'if *state == 2 { break; } '
                           'if *state == 1 { let mut local = new(memory) Int(99); let seen_local = *local; state.set(2); } '
                           'else { state.set(1); } } print(state);',
                           ['destroy temp=42', 'destroy local=99', 'destroy temp=42',
                            'destroy temp=42', 'destroy state=2'], '2\n')

    def test_break_targets_nearest_loop(self):
        self.check_sources('let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'loop { let mut outer = new(memory) Int(1); '
                           'loop { let mut inner = new(memory) Int(2); let seen_inner = *inner; break; } '
                           'print(outer); if *state == 1 { break; } state.set(1); }',
                           ['destroy inner=2', 'destroy outer=1', 'destroy inner=2',
                            'destroy outer=1', 'destroy state=1'], '1\n1\n')

    def test_direct_return_in_loop_cleans_function_scopes(self):
        self.check_sources('fn work(mem: &mut Allocator) { let mut parent = new(mem) Int(1); let seen_parent = *parent; '
                           'loop { let mut temp = new(mem) Int(2); let seen_temp = *temp; return; } } '
                           'work(&mut memory); memory.reset();',
                           ['destroy temp=2', 'destroy parent=1'])

    def test_scalar_return_after_multiple_iterations(self):
        self.check_sources('fn work(mem: &mut Allocator, state: &mut Int) -> Int { '
                           'loop { let mut temp = new(mem) Int(42); let seen_temp = *temp; '
                           'if *state == 1 { return 7; } state.set(1); } } '
                           'let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'let mut result = work(&mut memory, &mut state); print(result);',
                           ['destroy temp=42', 'destroy temp=42', 'destroy state=1'], '7\n')

    def test_owned_return_after_multiple_iterations_preserves_source(self):
        self.check_sources('fn work(mem: &mut Allocator, state: &mut Int) -> <- Int { '
                           'loop { let mut temp = new(mem) Int(42); let seen_temp = *temp; if *state == 1 { '
                           'let mut selected = new(mem) Int(7); return <- selected; } state.set(1); } } '
                           'let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'let mut result = work(&mut memory, &mut state); print(result); drop(-> result); memory.reset();',
                           ['destroy temp=42', 'destroy temp=42', 'destroy selected=7', 'destroy state=1'], '7\n')

    def test_break_does_not_cross_function_boundary(self):
        self.rejected('break;', 'break exige une boucle')
        self.rejected('fn wrong() { break; } loop { wrong(); break; }', 'fonction courante')

    def test_parent_consumed_only_on_break_path_is_not_reused(self):
        self.check_sources('let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'let mut data = new(memory) Int(42); loop { -> data; <- data; '
                           'if *state == 1 { -> data; drop(-> data); break; } state.set(1); } memory.reset();',
                           ['destroy data=42', 'destroy state=1'])
        self.rejected('let mut data = new(memory) Int(42); loop { -> data; drop(-> data); break; } '
                      'print(data);', 'plus utilisable')

    def test_parent_consumption_cannot_repeat_on_backedge(self):
        self.rejected('let mut data = new(memory) Int(42); loop { -> data; drop(-> data); }',
                      'plus utilisable')

    def test_reset_after_last_use_of_parent_allocation_can_repeat_safely(self):
        self.check_sources('let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'let mut old = new(memory) Int(10); let seen_old = *old; loop { memory.reset(); '
                           'let mut temp = new(memory) Int(42); let seen_temp = *temp; if *state == 1 { break; } state.set(1); }',
                           ['destroy old=10', 'destroy temp=42', 'destroy temp=42', 'destroy state=1'])

    def test_reads_in_next_iteration_protect_parent_from_reset(self):
        self.rejected('let mut data = new(memory) Int(42); loop { let mut copy = *data; print(copy); memory.reset(); }',
                      'reset interdit')

    def test_mutable_borrow_spans_backedge_and_blocks_owner_access(self):
        self.rejected('let mut data = new(memory) Int(0); let mut view = &mut data; '
                      'loop { let mut copy = *view; data.set(1); if copy == 1 { break; } }', 'emprunt actif')

    def test_break_path_excludes_next_iteration_borrow_use(self):
        self.check_sources('let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'let mut data = new(memory) Int(42); let mut view = &data; loop { '
                           'if *state == 1 { memory.reset(); break; } print(view); state.set(1); }',
                           ['destroy data=42', 'destroy state=1'], '42\n')

    def test_borrow_used_after_loop_still_protects_break_path(self):
        self.rejected('let mut data = new(memory) Int(42); let mut view = &data; '
                      'loop { if true { memory.reset(); break; } } print(view);', 'reset interdit')

    def test_explicit_round_trip_to_parent_across_iterations_preserves_access(self):
        self.check_sources('let mut controls = allocator(); let mut state = new(controls) Int(0); '
                           'let mut data = new(memory) Int(42); loop { -> data; <- data; '
                           'if *state == 1 { break; } state.set(1); } print(data); memory.reset();',
                           ['destroy data=42', 'destroy state=1'], '42\n')

    def test_break_in_if_expression_skips_receiver_and_cleans_iteration(self):
        self.check_sources('let mut controls = allocator(); let mut state = new(controls) Int(0); loop { '
                           'let mut selected = if *state == 1 { break; } else { '
                           'let mut temp = new(memory) Int(42); <- temp }; print(selected); state.set(1); }',
                           ['destroy temp=42', 'destroy state=1'], '42\n')

    def test_break_during_later_argument_cleans_prepared_owned_value(self):
        self.check_sources('fn consume(mut a: -> Int, mut b: -> Int) {} '
                           'loop { consume(-> new(memory) Int(42), -> { break; }); } memory.reset();',
                           ['destroy a=42'])

    def test_unreachable_allocations_after_break_are_not_emitted(self):
        code = compile_source('let mut memory = pool<Int>(1); loop { '
                              'let mut temp = new(memory) Int(42); let seen_temp = *temp; break; let mut unreachable = new(memory) Int(99); }')
        self.assertNotIn('"unreachable"', code)

    def test_diverging_functions_are_compiled_without_fabricated_result(self):
        for result_type in ('Int', '<- Int'):
            with self.subTest(result_type=result_type):
                result = self.execute('fn never(mem: &mut Allocator) -> ' + result_type + ' { '
                                      'loop { let mut temp = new(mem) Int(42); let seen_temp = *temp; } } '
                                      'fn work(mem: &mut Allocator, n: Int) -> Int { if n == 1 { '
                                      'let mut unreachable = never(mem); print(unreachable); } return 7; } '
                                      'let mut result = work(&mut memory, 0); print(result);')
                self.assertEqual(result.stdout, '7\n')
                self.assertEqual(result.stderr, '')
        for source in ('fn main() { loop {} let mut unreachable = 1; }',
                       'loop {} let mut unreachable = 1;'):
            with self.subTest(source=source):
                code = compile_source(source)
                self.assertNotIn('unreachable', code)

    def test_dereference_copies_int_and_obeys_borrow_and_liveness_checks(self):
        self.check_sources('let mut data = new(memory) Int(42); let mut view = &data; '
                           'let mut copy = *view; drop(-> data); print(copy);', ['destroy data=42'], '42\n')
        cases = [
            ('let mut n = 1; let mut copy = *n; print(copy);', '* exige'),
            ('let mut copy = *memory; print(copy);', '* exige'),
            ('let mut data = new(memory) Int(42); drop(-> data); let mut copy = *data; print(copy);', 'plus utilisable'),
            ('let mut data = new(memory) Int(42); let mut view = &mut data; '
             'let mut copy = *data; print(view); print(copy);', 'emprunt actif'),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                self.rejected(source, message.replace('*', r'\*'))

    def test_other_loop_forms_labels_and_values_are_deferred(self):
        for source in ('for n {}',
                       'loop { break 7; }', 'loop { break outer; }'):
            with self.subTest(source=source), self.assertRaises(Error):
                compile_source(source)

    def test_truncated_loop_sources_raise_checked_diagnostics(self):
        valid = ('fn main() { let mut memory = pool<Int>(1); loop { '
                 'let mut temp = new(memory) Int(42); if true { break; } } memory.reset(); }')
        for end in range(len(valid) + 1):
            with self.subTest(end=end):
                try:
                    compile_source(valid[:end])
                except Error:
                    pass

    def test_mixed_break_and_return_paths_preserve_only_reachable_borrows(self):
        self.check_sources(
            'fn work(mem: &mut Allocator, state: &mut Int) { '
            'let mut data = new(mem) Int(42); let mut view = &data; loop { '
            'if *state == 1 { mem.reset(); if true { break; } else { return; } } '
            'print(view); state.set(1); } } '
            'let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'work(&mut memory, &mut state); print(state);',
            ['destroy data=42', 'destroy state=1'], '42\n1\n')
        self.rejected('fn work(mem: &mut Allocator) { let mut data = new(mem) Int(42); '
                      'let mut view = &data; loop { if true { data.set(9); '
                      'if true { break; } return; } } print(view); } work(&mut memory);',
                      'emprunt actif')

    def test_enum_pool_slots_are_cleaned_and_reused_each_iteration(self):
        result = self.execute(
            'enum E { A { n: Int }, B { x: Int, y: Int } } let mut memory = pool<E>(1); '
            'let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'loop { let mut a = new(memory) E.A { n: 10 }; let mut b = new(memory) E.B { x: 20, y: 30 }; '
            'address(a); address(b); if *state == 1 { break; } state.set(1); } memory.reset();')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:2], lines[2:])
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy b=E.B', 'destroy a=E.A', 'destroy b=E.B', 'destroy a=E.A',
                          'destroy state=1'])

    def test_private_source_and_function_cleanup_flags_restart_each_iteration(self):
        self.check_sources(
            'fn make(mem: &mut Allocator) -> <- Int { let mut a = new(mem) Int(42); '
            'if true { print(a); } return <- a; } '
            'let mut controls = allocator(); let mut state = new(controls) Int(0); loop { '
            'let mut private = pool<Int>(1); let mut local = make(&mut private); print(local); '
            'if *state == 1 { break; } state.set(1); }',
            ['destroy a=42', 'destroy a=42', 'destroy state=1'], '42\n42\n42\n42\n')

    def test_reanalysis_does_not_keep_first_pass_function_return_candidates(self):
        self.check_sources(
            'fn work(mem: &mut Allocator, state: &mut Int) -> <- Int { '
            'loop { mem.reset(); if *state == 1 { let mut result = new(mem) Int(7); return <- result; } '
            'state.set(1); } } let mut old = new(memory) Int(99); let seen_old = *old; '
            'let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'let mut result = work(&mut memory, &mut state); print(result); drop(-> result); memory.reset();',
            ['destroy old=99', 'destroy result=7', 'destroy state=1'], '7\n')


if __name__ == '__main__':
    unittest.main()
