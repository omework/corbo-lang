"""Evaluate the replacement before destroying the previous allocation."""
from functools import partial, update_wrapper
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class ReassignmentTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def check_sources(self, program, expected, output=''):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(4)'):
            with self.subTest(factory=factory):
                result = self.execute('let mut memory = ' + factory + '; ' + program)
                self.assertEqual(result.stdout, output)
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 expected)

    def test_rhs_function_finishes_before_previous_allocation_is_destroyed(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, old: &Int) -> <- Int { '
            'print(old); let mut marker = new(mem) Int(99); drop(-> marker); '
            'let mut fresh = new(mem) Int(20); return <- fresh; } '
            'let mut data = new(memory) Int(10); data = make(&mut memory, &data); print(data);',
            ['destroy marker=99', 'destroy data=10', 'destroy fresh=20'], '10\n20\n')

    def test_rhs_scalar_initializer_can_read_previous_allocation(self):
        self.check_sources(
            'fn read(old: &Int) -> Int { print(old); return 20; } '
            'let mut data = new(memory) Int(10); data = new(memory) Int(read(&data)); print(data);',
            ['destroy data=10', 'destroy data=20'], '10\n20\n')

    def test_borrow_last_used_in_rhs_ends_before_reassignment_destruction(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.check_sources(
                    'fn make(mem: &mut Allocator, old: ' + mode + 'Int) -> <- Int { '
                    + ('old.set(11); ' if mode == '&mut ' else '') +
                    'let mut fresh = new(mem) Int(20); return <- fresh; } '
                    'let mut data = new(memory) Int(10); let mut view = ' + mode + 'data; '
                    'data = make(&mut memory, view); print(data);',
                    ['destroy data=' + ('11' if mode == '&mut ' else '10'), 'destroy fresh=20'],
                    '20\n')

    def test_future_shared_or_mutable_borrow_rejects_reassignment(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.rejected(
                    'let mut data = new(memory) Int(10); let mut view = ' + mode + 'data; '
                    'data = new(memory) Int(20); print(view); print(data);',
                    'réaffectation interdite.*emprunt actif')

    def test_direct_self_move_does_not_destroy_the_allocation(self):
        self.check_sources('let mut data = new(memory) Int(10); data = <- data; print(data);',
                           ['destroy data=10'], '10\n')

    def test_function_round_trip_of_same_allocation_is_not_destroyed(self):
        self.check_sources(
            'fn identity(mut old: -> Int) -> <- Int { return <- old; } '
            'let mut data = new(memory) Int(10); data = identity(-> data); print(data);',
            ['destroy data=10'], '10\n')

    def test_rhs_consumes_old_allocation_without_duplicate_destruction(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, mut old: -> Int) -> <- Int { '
            'drop(-> old); let mut fresh = new(mem) Int(20); return <- fresh; } '
            'let mut data = new(memory) Int(10); data = make(&mut memory, -> data); print(data);',
            ['destroy data=10', 'destroy fresh=20'], '20\n')

    def test_rhs_can_reset_old_source_before_returning_replacement(self):
        self.check_sources(
            'fn make(mem: &mut Allocator) -> <- Int { '
            'mem.reset(); let mut fresh = new(mem) Int(20); return <- fresh; } '
            'let mut data = new(memory) Int(10); if *data != 10 { print(999); } data = make(&mut memory); print(data);',
            ['destroy data=10', 'destroy fresh=20'], '20\n')

    def test_replacement_from_another_source_retains_its_provenance(self):
        self.check_sources(
            'let mut other = pool<Int>(1); '
            'fn make(mem: &mut Pool<Int>) -> <- Int { '
            'let mut fresh = new(mem) Int(20); return <- fresh; } '
            'let mut data = new(memory) Int(10); if *data != 10 { print(999); } data = make(&mut other); '
            'memory.reset(); print(data); other.drop(-> data); other.reset();',
            ['destroy data=10', 'destroy fresh=20'], '20\n')

    def test_move_replacement_consumes_rhs_handle(self):
        self.check_sources('let mut data = new(memory) Int(10); if *data != 10 { print(999); } let mut next = new(memory) Int(20); '
                           'data = <- next; print(data);',
                           ['destroy data=10', 'destroy next=20'], '20\n')
        self.rejected('let mut data = new(memory) Int(10); if *data != 10 { print(999); } let mut next = new(memory) Int(20); '
                      'data = <- next; print(data); print(next);', 'plus utilisable')

    def test_two_pool_slots_support_repeated_reassignment_and_hole_reuse(self):
        program = ('let mut memory = pool<Int>(2); '
                   'fn make(mem: &mut Pool<Int>, n: Int) -> <- Int { '
                   'let mut fresh = new(mem) Int(n); return <- fresh; } '
                   'let mut data = new(memory) Int(0); address(data); ')
        for value in range(1, 11):
            program += 'data = make(&mut memory, ' + str(value) + '); address(data); '
        result = self.execute(program + 'print(data); memory.reset();')
        lines = result.stdout.splitlines()
        self.assertNotEqual(lines[0], lines[1])
        self.assertEqual(lines[:11:2], [lines[0]] * 6)
        self.assertEqual(lines[1:11:2], [lines[1]] * 5)
        self.assertEqual(lines[11:], ['10'])
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=0'] + ['destroy fresh=' + str(n) for n in range(1, 11)])
        self.assertIn('reuse fresh', result.stderr)

    def test_single_slot_pool_cannot_allocate_replacement_before_old_destruction(self):
        for expression in ('new(memory) Int(20)', 'make(&mut memory)'):
            with self.subTest(expression=expression):
                # execute() includes the actual runtime's stderr on failure.
                with self.assertRaises(subprocess.CalledProcessError) as failure:
                    self.execute(
                        'fn make(mem: &mut Pool<Int>) -> <- Int { '
                        'let mut fresh = new(mem) Int(20); return <- fresh; } '
                        'let mut memory = pool<Int>(1); let mut data = new(memory) Int(10); if *data != 10 { print(999); } '
                        'data = ' + expression + '; print(data);')
                self.assertIn('pool capacity exceeded', failure.exception.stderr)
                self.assertNotIn('destroy ', failure.exception.stderr)

    def test_borrow_rebinding_does_not_destroy_referenced_allocations(self):
        self.check_sources('let mut a = new(memory) Int(10); let mut b = new(memory) Int(20); '
                           'let mut view = &a; print(view); view = &b; print(view);',
                           ['destroy b=20', 'destroy a=10'], '10\n20\n')

    def test_enum_replacement_destroys_correct_arm_then_reuses_old_arm_slot(self):
        result = self.execute(
            'enum E { A { n: Int }, B { x: Int, y: Int } } let mut memory = pool<E>(1); '
            'fn make(mem: &mut Pool<E>, old: &E) -> <- E { '
            'print(old); let mut fresh = new(mem) E.B { x: 2, y: 3 }; return <- fresh; } '
            'let mut data = new(memory) E.A { n: 1 }; address(data); '
            'data = make(&mut memory, &data); print(data); '
            'let mut next = new(memory) E.A { n: 4 }; address(next); print(next); memory.reset();')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[3])
        self.assertEqual([lines[1], lines[2], lines[4]], ['E.A(1)', 'E.B(2, 3)', 'E.A(4)'])
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=E.A', 'destroy next=E.A', 'destroy fresh=E.B'])

    def test_reassignment_of_transferred_parameter_cleans_new_value_at_return(self):
        self.check_sources(
            'fn work(mem: &mut Allocator, mut data: -> Int) { '
            'data = new(mem) Int(20); print(data); return; } '
            'let mut data = new(memory) Int(10); work(&mut memory, -> data); memory.reset();',
            ['destroy data=10', 'destroy data=20'], '20\n')

    def test_generated_c_materializes_rhs_before_dropping_old_value(self):
        code = compile_source('let mut memory = allocator(); let mut data = new(memory) Int(10); if *data != 10 { print(999); } '
                              'data = new(memory) Int(20); print(data);')
        self.assertLess(code.index('20, "data"'), code.index('cell_drop(', code.index('int main(void)')))


if __name__ == '__main__':
    unittest.main()
