"""Pre-test loops, condition effects and all exits from an iteration."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source, Error

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class WhileTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def test_false_condition_skips_body_and_preserves_parent(self):
        result = self.execute('let mut data = new(memory) Int(42); '
            'while false { -> data; <- data; print(data); } print(data);')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_true_condition_break_cleans_body(self):
        result = self.execute('while true { let mut temp = new(memory) Int(42); print(temp); break; }')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.count('destroy temp=42'), 1)

    def test_all_comparisons_accept_scalar_operands(self):
        for condition in ('1 == 1', '1 != 2', '1 < 2', '1 <= 1', '2 > 1', '2 >= 2'):
            with self.subTest(condition=condition):
                self.assertEqual(self.execute('while ' + condition + ' { let mut value = 7; print(value); break; }').stdout, '7\n')

    def test_condition_is_rechecked_after_continue_and_fallthrough(self):
        result = self.execute('fn probe(state: &Int) -> Int { print(state); return *state; } '
            'let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'while probe(&state) < 2 { let mut temp = new(memory) Int(42); '
            'if *state == 0 { state.set(1); continue; } state.set(2); } print(state);')
        self.assertEqual(result.stdout, '0\n1\n2\n2\n')
        self.assertEqual(result.stderr.count('destroy temp=42'), 2)

    def test_condition_temporaries_are_cleaned_on_false_exit_and_each_restart(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(1)'):
            with self.subTest(factory=factory):
                result = self.execute('fn probe(a: &Int, state: &Int) -> Int { '
                    'address(a); return *state; } let mut memory = ' + factory + '; '
                    'let mut controls = allocator(); let mut state = new(controls) Int(0); '
                    'while probe(&new(memory) Int(42), &state) == 0 { state.set(1); continue; } '
                    'let mut after = new(memory) Int(7); print(after); memory.reset();')
                lines = result.stdout.splitlines()
                if factory != 'allocator()':
                    self.assertEqual(lines[0], lines[1])
                self.assertEqual(lines[2:], ['7'])
                self.assertEqual(result.stderr.count('destroy a=42'), 2)
                self.assertEqual(result.stderr.count('destroy after=7'), 1)

    def test_condition_temporary_survives_until_iteration_cleanup(self):
        result = self.execute('fn probe(a: &Int) -> Int { return *a; } '
            'let mut memory = pool<Int>(2); while probe(&new(memory) Int(42)) == 42 { '
            'let mut body = new(memory) Int(7); break; }')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy body=7', 'destroy a=42'])

    def test_condition_operands_are_evaluated_left_to_right(self):
        result = self.execute('fn mark(n: Int) -> Int { print(n); return n; } '
            'while mark(1) < mark(2) { break; }')
        self.assertEqual(result.stdout, '1\n2\n')

    def test_zero_iteration_path_prevents_assuming_body_return(self):
        self.rejected('fn work() -> Int { while true { return 7; } } '
                      'let mut result = work(); print(result);', 'retour')
        result = self.execute('fn work(n: Int) -> Int { while n == 1 { return 7; } return 9; } '
            'let mut a = work(0); let mut b = work(1); print(a); print(b);')
        self.assertEqual(result.stdout, '9\n7\n')

    def test_conditional_consumption_invalidates_after_loop_access(self):
        self.rejected('let mut data = new(memory) Int(42); while false { -> data; drop(-> data); break; } '
                      'print(data);', 'plus utilisable')
        result = self.execute('let mut data = new(memory) Int(42); '
            'while false { -> data; drop(-> data); break; } memory.reset();')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_consumption_on_backedge_is_rejected(self):
        self.rejected('let mut data = new(memory) Int(42); '
                      'while true { -> data; drop(-> data); continue; }', 'plus utilisable')

    def test_parent_borrow_in_condition_protects_next_evaluation(self):
        self.rejected('let mut data = new(memory) Int(42); let mut view = &data; '
                      'while *view == 42 { memory.reset(); continue; }', 'reset interdit')
        self.rejected('let mut data = new(memory) Int(42); let mut view = &mut data; '
                      'while *view == 42 { data.set(1); }', 'emprunt actif')

    def test_break_path_can_end_condition_borrow(self):
        result = self.execute('let mut data = new(memory) Int(42); let mut view = &data; '
            'while *view == 42 { if true { memory.reset(); break; } }')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_after_loop_borrow_still_protects_break_path(self):
        self.rejected('let mut data = new(memory) Int(42); let mut view = &data; '
                      'while true { memory.reset(); break; } print(view);', 'reset interdit')

    def test_condition_effects_are_visible_even_when_false(self):
        result = self.execute('fn probe(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
            'let mut data = new(memory) Int(42); while probe(&mut memory) == 1 { let mut value = 99; print(value); } memory.reset();')
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)
        self.rejected('fn probe(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
            'let mut data = new(memory) Int(42); while probe(&mut memory) == 1 {} print(data);', 'reset interdit')

    def test_nested_loop_targets_and_private_source_cleanup(self):
        result = self.execute('let mut state = new(memory) Int(0); loop { '
            'while *state == 0 { let mut private = pool<Int>(1); let mut local = new(private) Int(42); '
            'state.set(1); continue; } print(state); break; }')
        self.assertEqual(result.stdout, '1\n')
        self.assertEqual(result.stderr.count('destroy local=42'), 1)

    def test_owned_function_return_from_body(self):
        result = self.execute('fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'while n == 1 { let mut temp = new(mem) Int(42); let mut selected = new(mem) Int(7); '
            'return <- selected; } let mut fallback = new(mem) Int(9); return <- fallback; } '
            'let mut memory = pool<Int>(2); let mut a = make(&mut memory, 1); print(a); drop(-> a); '
            'let mut b = make(&mut memory, 0); print(b); drop(-> b); memory.reset();')
        self.assertEqual(result.stdout, '7\n9\n')
        self.assertEqual(result.stderr.count('destroy temp=42'), 1)
        self.assertEqual(result.stderr.count('destroy selected=7'), 1)
        self.assertEqual(result.stderr.count('destroy fallback=9'), 1)

    def test_return_during_condition_cleans_function(self):
        result = self.execute('fn work(mem: &mut Allocator) -> Int { let mut parent = new(mem) Int(42); '
            'while { let mut temp = new(mem) Int(7); return 9; } == 0 { let mut value = 99; print(value); } } '
            'let mut result = work(&mut memory); print(result);')
        self.assertEqual(result.stdout, '9\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy temp=7', 'destroy parent=42'])

    def test_enum_pool_arm_slots_are_reused(self):
        result = self.execute('enum E { A { n: Int }, B { x: Int } } let mut memory = pool<E>(1); '
            'let mut controls = allocator(); let mut state = new(controls) Int(0); while *state < 2 { '
            'let mut a = new(memory) E.A { n: 10 }; let mut b = new(memory) E.B { x: 20 }; address(a); address(b); '
            'if *state == 0 { state.set(1); continue; } state.set(2); }')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:2], lines[2:])
        self.assertEqual(result.stderr.count('destroy a=E.A'), 2)
        self.assertEqual(result.stderr.count('destroy b=E.B'), 2)

    def test_continue_during_condition_targets_this_while(self):
        result = self.execute('fn probe(a: &Int) -> Int { return *a; } '
            'let mut memory = pool<Int>(1); let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'while probe(& { if *state == 0 { state.set(1); continue; } '
            'let mut temp = new(memory) Int(42); <- temp }) == 42 { print(state); break; }')
        self.assertEqual(result.stdout, '1\n')
        self.assertEqual(result.stderr.count('destroy temp=42'), 1)

    def test_break_during_condition_cleans_earlier_operand(self):
        result = self.execute('fn probe(a: &Int) -> Int { return *a; } '
            'let mut memory = pool<Int>(1); '
            'while probe(&new(memory) Int(42)) == { break; } {} memory.reset();')
        self.assertEqual(result.stderr.count('destroy a=42'), 1)

    def test_condition_reset_rejects_borrow_used_after_loop(self):
        self.rejected('fn probe(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
            'let mut data = new(memory) Int(42); let mut view = &data; '
            'while probe(&mut memory) == 1 {} print(view);', 'reset interdit')

    def test_invalid_conditions_and_truncated_sources(self):
        for source in ('while 1 {}', 'while new(memory) Int(1) == 1 {}', 'while false {} else {}'):
            with self.subTest(source=source), self.assertRaises(Error):
                compile_source('let mut memory = allocator(); ' + source)
        source = 'let mut memory = allocator(); while 1 < 2 { let mut a = new(memory) Int(42); break; }'
        for end in range(len(source) + 1):
            with self.subTest(end=end):
                try:
                    compile_source(source[:end])
                except Error:
                    pass


if __name__ == '__main__':
    unittest.main()
