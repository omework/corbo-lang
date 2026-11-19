"""Collective destruction, call effects and access invalidation at reset."""
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
import test_crust


class ResetTransitionTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)
    factories = ('allocator()', 'stack(65536)', 'pool<Int>(4)')

    def check_sources(self, program, expected, output=''):
        for factory in self.factories:
            with self.subTest(factory=factory):
                result = self.execute('let mut memory = ' + factory + '; ' + program)
                self.assertEqual(result.stdout, output)
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 expected)
                self.assertEqual(result.stderr.splitlines().count('reset'), 1)

    def test_collective_destruction_skips_explicit_drop_and_final_cleanup(self):
        self.check_sources('let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); '
                           'let mut c = new(memory) Int(3); print(a); print(c); drop(-> b); memory.reset();',
                           ['destroy b=2', 'destroy c=3', 'destroy a=1'], '1\n3\n')

    def test_nested_reset_destroys_child_before_parent_and_preserves_other_source(self):
        self.check_sources('let mut other = allocator(); let mut safe = new(other) Int(99); '
                           'let mut a = new(memory) Int(1); { let mut b = new(memory) Int(2); '
                           'print(a); print(b); memory.reset(); } print(safe);',
                           ['destroy b=2', 'destroy a=1', 'destroy safe=99'], '1\n2\n99\n')

    def test_reception_order_overrides_creation_order(self):
        self.check_sources('let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); '
                           '{ -> a; <- a; } print(a); print(b); memory.reset();',
                           ['destroy a=1', 'destroy b=2'], '1\n2\n')

    def test_nested_function_reset_destroys_caller_values_at_the_reset_point(self):
        self.check_sources(
            'fn clear(mem: &mut Allocator) { let mut before = new(mem) Int(3); '
            'print(before); mem.reset(); let mut after = new(mem) Int(4); print(after); } '
            'fn forward(mem: &mut Allocator) { clear(mem); } '
            'let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); print(a); print(b); forward(&mut memory);',
            ['destroy before=3', 'destroy b=2', 'destroy a=1', 'destroy after=4'], '1\n2\n3\n4\n')

    def test_reset_of_returned_allocation_uses_its_original_source(self):
        self.check_sources(
            'fn make(mem: &mut Allocator) -> <- Int { '
            'let mut data = new(mem) Int(42); return <- data; } '
            'let mut result = make(&mut memory); print(result); memory.reset();',
            ['destroy data=42'], '42\n')

    def test_future_direct_or_borrowed_access_rejects_reset(self):
        for before, after in (
            ('', 'print(data);'), ('', 'address(data);'), ('', 'drop(-> data);'),
            ('', 'let mut moved = <- data; print(moved);'),
            ('let mut view = &data;', 'read(view);'),
            ('let mut view = &mut data;', 'write(view);'),
        ):
            for operation in ('memory.reset();', 'clear(&mut memory);'):
                with self.subTest(before=before, after=after, operation=operation):
                    self.rejected(
                        'fn read(a: &Int) { print(a); } '
                        'fn write(a: &mut Int) { a.set(3); } '
                        'fn clear(mem: &mut Allocator) { mem.reset(); } '
                        'let mut data = new(memory) Int(42); ' + before + operation + after,
                        'reset interdit.*encore être utilisé')

    def test_last_reborrow_does_not_prevent_reset_in_same_or_nested_function(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.check_sources(
                    'fn read(a: ' + mode + 'Int) { print(a); } '
                    'fn clear(mem: &mut Allocator, a: ' + mode + 'Int) { '
                    'read(a); mem.reset(); } '
                    'let mut data = new(memory) Int(42); let mut view = ' + mode + 'data; '
                    'clear(&mut memory, view);', ['destroy data=42'], '42\n')

    def test_reset_checks_suspended_caller_reborrow(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.rejected(
                    'fn clear(mem: &mut Allocator, a: ' + mode + 'Int) { '
                    'print(a); mem.reset(); } '
                    'let mut data = new(memory) Int(42); let mut view = ' + mode + 'data; '
                    'clear(&mut memory, view); print(view);',
                    'reset interdit.*encore être utilisé')

    def test_live_callee_borrow_rejects_reset(self):
        self.rejected(
            'fn clear(mem: &mut Allocator, a: &Int) { mem.reset(); print(a); } '
            'let mut data = new(memory) Int(42); clear(&mut memory, &data);',
            'reset interdit.*encore être utilisé')

    def test_reset_can_destroy_transferred_parameter(self):
        self.check_sources(
            'fn clear(mem: &mut Allocator, mut a: -> Int) { print(a); mem.reset(); } '
            'let mut data = new(memory) Int(42); clear(&mut memory, -> data);',
            ['destroy data=42'], '42\n')

    def test_readonly_source_cannot_reset(self):
        self.rejected('fn clear(mem: &Allocator) { mem.reset(); } '
                      'let mut data = new(memory) Int(42); clear(&memory);', 'emprunt mutable')

    def test_pool_reuses_reset_storage_without_reviving_old_allocation(self):
        result = self.execute(
            'let mut memory = pool<Int>(1); fn clear(mem: &mut Pool<Int>) { mem.reset(); } '
            'let mut data = new(memory) Int(42); address(data); clear(&mut memory); '
            'let mut fresh = new(memory) Int(43); address(fresh); print(fresh);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2:], ['43'])
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=42', 'destroy fresh=43'])
        self.rejected('let mut memory = pool<Int>(1); let mut data = new(memory) Int(42); '
                      'memory.reset(); let mut fresh = new(memory) Int(43); print(data);',
                      'reset interdit')

    def test_enum_reset_is_global_across_arms_and_reuses_both_stacks(self):
        result = self.execute(
            'enum E { A { n: Int }, B { x: Int, y: Int } } let mut memory = pool<E>(2); '
            'fn clear(mem: &mut Pool<E>) { mem.reset(); } '
            'let mut a = new(memory) E.A { n: 1 }; let mut b = new(memory) E.B { x: 2, y: 3 }; '
            'let mut c = new(memory) E.A { n: 4 }; print(c); address(a); address(b); clear(&mut memory); '
            'let mut d = new(memory) E.A { n: 5 }; let mut e = new(memory) E.B { x: 6, y: 7 }; '
            'address(d); address(e); print(d); print(e);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines.pop(0), 'E.A(4)')
        self.assertEqual(lines[:2], lines[2:4])
        self.assertEqual(lines[4:], ['E.A(5)', 'E.B(6, 7)'])
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy c=E.A', 'destroy b=E.B', 'destroy a=E.A',
                          'destroy e=E.B', 'destroy d=E.A'])

    def test_reset_in_descendant_then_return_new_allocation(self):
        self.check_sources(
            'fn clear(mem: &mut Allocator) { mem.reset(); } '
            'fn replace(mem: &mut Allocator) -> <- Int { '
            'let mut local = new(mem) Int(2); print(local); { clear(mem); '
            'let mut fresh = new(mem) Int(3); return <- fresh; } } '
            'let mut outer = new(memory) Int(1); print(outer); let mut result = replace(&mut memory); print(result);',
            ['destroy local=2', 'destroy outer=1', 'destroy fresh=3'], '1\n2\n3\n')

    def test_repeated_resets_do_not_repeat_destruction(self):
        for factory in self.factories:
            with self.subTest(factory=factory):
                result = self.execute(
                    'let mut memory = ' + factory + '; '
                    'fn clear(mem: &mut Allocator) { mem.reset(); mem.reset(); } '
                    'let mut a = new(memory) Int(1); print(a); clear(&mut memory); '
                    'let mut b = new(memory) Int(2); print(b); clear(&mut memory);')
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy a=1', 'destroy b=2'], '1\n2\n')
                self.assertEqual(result.stdout, '1\n2\n')
                self.assertEqual(result.stderr.splitlines().count('reset'), 4)

    def test_future_enum_borrow_in_any_arm_prevents_collective_destruction(self):
        for arm in ('A', 'B'):
            with self.subTest(arm=arm):
                self.rejected(
                    'enum E { A, B } let mut memory = pool<E>(1); '
                    'fn clear(mem: &mut Pool<E>) { mem.reset(); } '
                    'fn read(a: &E) { print(a); } '
                    'let mut a = new(memory) E.A; let mut b = new(memory) E.B; print(a); print(b); '
                    'let mut view = &' + arm.lower() + '; clear(&mut memory); read(view);',
                    'reset interdit.*encore être utilisé')


if __name__ == '__main__':
    unittest.main()
