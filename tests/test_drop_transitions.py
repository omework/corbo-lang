"""Explicit destruction across calls, including pool slot reuse."""
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
import test_crust


class DropTransitionTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    @staticmethod
    def destructions(result):
        return [line for line in result.stderr.splitlines() if line.startswith('destroy ')]

    def test_last_reborrow_can_precede_consumption_through_nested_calls(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(1)'):
            for mode in ('&', '&mut '):
                with self.subTest(factory=factory, mode=mode):
                    result = self.execute(
                        'let mut memory = ' + factory + '; '
                        'fn read(a: ' + mode + 'Int) { ' +
                        ('a.set(43); ' if mode == '&mut ' else '') + 'print(a); } '
                        'fn forward(a: ' + mode + 'Int) { read(a); } '
                        'fn release(mut a: -> Int) { drop(-> a); } '
                        'fn consume(mut a: -> Int) { release(-> a); } '
                        'let mut data = new(memory) Int(42); let mut view = ' + mode + 'data; '
                        'forward(view); consume(-> data); memory.reset();')
                    value = '43' if mode == '&mut ' else '42'
                    self.assertEqual(result.stdout, value + '\n')
                    self.assertEqual(self.destructions(result), ['destroy data=' + value])
                    self.assertTrue(result.stderr.endswith('reset\n'))

    def test_future_reborrow_prevents_consuming_call(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.rejected(
                    'fn read(a: ' + mode + 'Int) { print(a); } '
                    'fn forward(a: ' + mode + 'Int) { read(a); } '
                    'fn consume(mut a: -> Int) { drop(-> a); } '
                    'let mut data = new(memory) Int(42); let mut view = ' + mode + 'data; '
                    'consume(-> data); forward(view);', 'emprunt encore utilisé')

    def test_borrowed_parameter_cannot_be_consumed_by_nested_function(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.rejected(
                    'fn release(mut a: -> Int) { drop(-> a); } '
                    'fn wrong(a: ' + mode + 'Int) { release(-> a); } '
                    'let mut data = new(memory) Int(42); wrong(' + mode + 'data);',
                    'allocation explicite est déplaçable')

    def test_consumed_and_borrowed_arguments_must_not_alias(self):
        for params, args in (('mut a: -> Int, b: &Int', '-> data, &data'),
                             ('b: &Int, mut a: -> Int', '&data, -> data')):
            with self.subTest(params=params):
                self.rejected(
                    'fn wrong(' + params + ') { drop(-> a); print(b); } '
                    'let mut data = new(memory) Int(42); wrong(' + args + ');',
                    'aliasés|plus utilisable')

    @staticmethod
    def replacement_program(hole=True):
        return (
            'let mut memory = pool<Int>(' + ('2' if hole else '1') + '); '
            'fn release(mut a: -> Int) { drop(-> a); } '
            'fn replace(mem: &mut Pool<Int>, mut old: -> Int) -> <- Int { '
            'release(-> old); let mut fresh = new(mem) Int(43); '
            'address(fresh); return <- fresh; } '
            'let mut data = new(memory) Int(42); '
            + ('let mut guard = new(memory) Int(99); ' if hole else '') +
            'address(data); let mut next = replace(&mut memory, -> data); address(next); ')

    def test_replacement_reuses_hole_or_reclaimed_suffix_through_functions(self):
        for hole in (False, True):
            with self.subTest(hole=hole):
                result = self.execute(self.replacement_program(hole) +
                                      'print(next); drop(-> next); ' +
                                      ('print(guard); drop(-> guard); ' if hole else '') +
                                      'memory.reset();')
                lines = result.stdout.splitlines()
                self.assertRegex(lines[0], r'^0x[0-9a-fA-F]+$')
                self.assertEqual(lines[:3], [lines[0]] * 3)
                self.assertEqual(lines[3:], ['43', '99'] if hole else ['43'])
                self.assertEqual(self.destructions(result),
                                 ['destroy data=42', 'destroy fresh=43'] +
                                 (['destroy guard=99'] if hole else []))
                self.assertEqual('reuse fresh\n' in result.stderr, hole)
                self.assertTrue(result.stderr.endswith('reset\n'))

    def test_replacement_never_revives_old_handle(self):
        for operation in ('print(data);', 'address(data);', 'read(&data);',
                          'let mut view = &data;', 'let mut moved = <- data;',
                          'drop(-> data);', 'release(-> data);'):
            with self.subTest(operation=operation):
                self.rejected('fn read(a: &Int) { print(a); } ' +
                              self.replacement_program() + operation, 'plus utilisable')

    def test_replacement_cannot_invalidate_a_future_borrow(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.rejected(
                    'let mut memory = pool<Int>(1); '
                    'fn read(a: ' + mode + 'Int) { print(a); } '
                    'fn replace(mem: &mut Pool<Int>, mut old: -> Int) -> <- Int { '
                    'drop(-> old); let mut fresh = new(mem) Int(43); return <- fresh; } '
                    'let mut data = new(memory) Int(42); let mut view = ' + mode + 'data; '
                    'let mut next = replace(&mut memory, -> data); read(view);',
                    'emprunt encore utilisé')

    def test_nested_drop_cannot_be_repeated_by_enclosing_function(self):
        self.rejected(
            'fn release(mut a: -> Int) { drop(-> a); } '
            'fn wrong(mut a: -> Int) { release(-> a); drop(-> a); } '
            'let mut data = new(memory) Int(42); wrong(-> data);', 'plus utilisable')

    def test_enum_replacement_reuses_its_arm_without_affecting_other_arm(self):
        result = self.execute(
            'enum E { A { n: Int }, B { x: Int, y: Int } } '
            'let mut memory = pool<E>(2); '
            'fn release(mut a: -> E) { drop(-> a); } '
            'fn replace(mem: &mut Pool<E>, mut old: -> E) -> <- E { '
            'release(-> old); let mut fresh = new(mem) E.A { n: 43 }; return <- fresh; } '
            'let mut data = new(memory) E.A { n: 42 }; '
            'let mut guard = new(memory) E.A { n: 99 }; '
            'let mut other = new(memory) E.B { x: 1, y: 2 }; '
            'address(data); address(other); '
            'let mut next = replace(&mut memory, -> data); address(next); address(other); '
            'print(next); print(guard); print(other); '
            'drop(-> next); drop(-> guard); drop(-> other); memory.reset();')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:2], lines[2:4])
        self.assertNotEqual(lines[0], lines[1])
        self.assertEqual(lines[4:], ['E.A(43)', 'E.A(99)', 'E.B(1, 2)'])
        self.assertIn('reuse fresh\n', result.stderr)
        self.assertEqual(self.destructions(result),
                         ['destroy data=E.A', 'destroy fresh=E.A',
                          'destroy guard=E.A', 'destroy other=E.B'])
        self.assertTrue(result.stderr.endswith('reset\n'))

    def test_nested_explicit_source_drop_preserves_provenance(self):
        self.rejected(
            'fn release(mem: &mut Allocator, mut a: -> Int) { mem.drop(-> a); } '
            'fn forward(mem: &mut Allocator, mut a: -> Int) { release(mem, -> a); } '
            'let mut other = pool<Int>(1); let mut data = new(memory) Int(42); '
            'forward(&mut other, -> data);', 'origine')

    def test_enum_replacement_does_not_revive_handle_or_borrow(self):
        prefix = (
            'enum E { A { n: Int }, B } let mut memory = pool<E>(1); '
            'fn read(a: &E) { print(a); } '
            'fn replace(mem: &mut Pool<E>, mut old: -> E) -> <- E { '
            'drop(-> old); let mut fresh = new(mem) E.A { n: 43 }; return <- fresh; } '
            'let mut data = new(memory) E.A { n: 42 }; ')
        for operation in ('read(&data);', 'drop(-> data);'):
            with self.subTest(operation=operation):
                self.rejected(prefix + 'let mut next = replace(&mut memory, -> data); '
                              'print(next); ' + operation, 'plus utilisable')
        self.rejected(prefix + 'let mut view = &data; '
                      'let mut next = replace(&mut memory, -> data); read(view); print(next);',
                      'emprunt encore utilisé')

    def test_repeated_function_replacement_destroys_each_allocation_once(self):
        program = (
            'let mut memory = pool<Int>(2); '
            'fn release(mut a: -> Int) { drop(-> a); } '
            'fn replace(mem: &mut Pool<Int>, mut old: -> Int, n: Int) -> <- Int { '
            'release(-> old); let mut fresh = new(mem) Int(n); return <- fresh; } '
            'let mut first = new(memory) Int(0); let mut guard = new(memory) Int(99); '
            'address(first); ')
        previous = 'first'
        for value in range(1, 21):
            current = 'next' + str(value)
            program += ('let mut ' + current + ' = replace(&mut memory, -> ' + previous +
                        ', ' + str(value) + '); address(' + current + '); ')
            previous = current
        result = self.execute(program + 'print(' + previous + '); drop(-> ' + previous +
                              '); print(guard); drop(-> guard); memory.reset();')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:21], [lines[0]] * 21)
        self.assertEqual(lines[21:], ['20', '99'])
        self.assertEqual(self.destructions(result), ['destroy first=0'] +
                         ['destroy fresh=' + str(value) for value in range(1, 21)] +
                         ['destroy guard=99'])
        self.assertEqual(result.stderr.splitlines().count('reuse fresh'), 20)
        self.assertTrue(result.stderr.endswith('reset\n'))


if __name__ == '__main__':
    unittest.main()
