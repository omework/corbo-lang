"""Explicit iteration restarts clean scopes and participate in memory analysis."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class ContinueTests(unittest.TestCase):
    with_source = staticmethod(test_crust.PrototypeTests.with_source)
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected

    def test_nested_cleanup_precedes_restart_and_pool_slot_is_reused(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(1)'):
            with self.subTest(factory=factory):
                result = self.execute('let mut memory = ' + factory + '; '
                    'let mut controls = allocator(); let mut state = new(controls) Int(0); '
                    'loop { let mut temp = new(memory) Int(42); address(temp); '
                    'if *state == 1 { break; } { let mut private = pool<Int>(1); '
                    'let mut local = new(private) Int(9); state.set(1); continue; } } print(state);')
                lines = result.stdout.splitlines()
                if factory != 'allocator()':
                    self.assertEqual(lines[0], lines[1])
                self.assertEqual(lines[2:], ['1'])
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                    ['destroy local=9', 'destroy temp=42', 'destroy temp=42', 'destroy state=1'])

    def test_normal_and_explicit_backedges_coexist(self):
        result = self.execute('let mut memory = pool<Int>(1); let mut controls = allocator(); '
            'let mut state = new(controls) Int(0); loop { let mut temp = new(memory) Int(42); '
            'print(temp); if *state == 2 { break; } '
            'if *state == 0 { state.set(1); continue; } state.set(2); }')
        self.assertEqual(result.stdout, '42\n42\n42\n')
        self.assertEqual(result.stderr.count('destroy temp=42'), 3)

    def test_nearest_loop_is_restarted(self):
        result = self.execute('let mut memory = allocator(); let mut state = new(memory) Int(0); '
            'loop { loop { if *state == 0 { state.set(1); continue; } break; } '
            'print(state); break; }')
        self.assertEqual(result.stdout, '1\n')

    def test_continue_requires_loop_in_current_function(self):
        self.rejected('continue;', 'continue exige une boucle')
        self.rejected('fn wrong() { continue; } loop { wrong(); break; }', 'fonction courante')

    def test_consumption_on_continue_path_cannot_repeat(self):
        self.rejected('let mut memory = allocator(); let mut data = new(memory) Int(42); '
            'loop { -> data; drop(-> data); continue; }', 'plus utilisable')

    def test_next_iteration_borrow_blocks_reset_even_when_all_paths_stop(self):
        self.rejected('let mut memory = allocator(); let mut data = new(memory) Int(42); '
            'let mut view = &data; loop { print(view); memory.reset(); continue; }', 'reset interdit')
        self.rejected('let mut memory = allocator(); let mut data = new(memory) Int(42); '
            'let mut view = &data; loop { print(view); if true { memory.reset(); '
            'if true { break; } else { continue; } } continue; }', 'reset interdit')

    def test_mutable_borrow_protects_owner_across_explicit_backedge(self):
        self.rejected('let mut memory = allocator(); let mut data = new(memory) Int(0); '
            'let mut view = &mut data; loop { print(view); data.set(1); continue; }', 'emprunt actif')

    def test_parent_roundtrip_is_restored_before_restart(self):
        result = self.execute('let mut memory = allocator(); let mut state = new(memory) Int(0); '
            'let mut data = new(memory) Int(42); loop { -> data; <- data; '
            'if *state == 1 { break; } state.set(1); continue; } print(data);')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_continue_in_if_expression_skips_receiver(self):
        result = self.execute('let mut memory = pool<Int>(1); let mut controls = allocator(); '
            'let mut state = new(controls) Int(0); loop { '
            'let mut selected = if *state == 0 { state.set(1); continue; } '
            'else { let mut temp = new(memory) Int(42); <- temp }; print(selected); break; }')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.count('destroy temp=42'), 1)

    def test_continue_in_argument_cleans_prepared_allocation(self):
        result = self.execute('fn consume(mut a: -> Int, mut b: -> Int) {} '
            'let mut memory = pool<Int>(1); let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'loop { if *state == 1 { break; } state.set(1); '
            'consume(-> new(memory) Int(42), -> { continue; }); } memory.reset();')
        self.assertEqual(result.stderr.count('destroy a=42'), 1)

    def test_function_return_after_restart_preserves_allocation(self):
        result = self.execute('fn work(mem: &mut Allocator, state: &mut Int) -> <- Int { '
            'loop { let mut temp = new(mem) Int(42); if *state == 0 { state.set(1); continue; } '
            'let mut selected = new(mem) Int(7); return <- selected; } } '
            'let mut memory = pool<Int>(2); let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'let mut result = work(&mut memory, &mut state); print(result); drop(-> result); memory.reset();')
        self.assertEqual(result.stdout, '7\n')
        self.assertEqual(result.stderr.count('destroy temp=42'), 2)
        self.assertEqual(result.stderr.count('destroy selected=7'), 1)

    def test_enum_arm_slots_are_reused_after_continue(self):
        result = self.execute('enum E { A { n: Int }, B { x: Int, y: Int } } '
            'let mut memory = pool<E>(1); let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'loop { let mut a = new(memory) E.A { n: 10 }; let mut b = new(memory) E.B { x: 20, y: 30 }; '
            'address(a); address(b); if *state == 1 { break; } state.set(1); continue; }')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:2], lines[2:])
        self.assertEqual(result.stderr.count('destroy a=E.A'), 2)
        self.assertEqual(result.stderr.count('destroy b=E.B'), 2)

    def test_unreachable_code_and_infinite_continue(self):
        code = compile_source('fn main() { loop { continue; let mut unreachable = 1; } }')
        self.assertNotIn('unreachable', code)
        self.assertIn('goto loop_next', code)
        result = self.execute('fn never() -> Int { loop { continue; } } '
            'if false { let mut result = never(); print(result); }')
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
