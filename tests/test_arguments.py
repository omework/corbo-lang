"""Left-to-right argument effects and lifetimes of prepared arguments."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source, Error

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class ArgumentTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def check_sources(self, program, output, destructions):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(6)'):
            with self.subTest(factory=factory):
                result = self.execute('let mut memory = ' + factory + '; ' + program)
                self.assertEqual(result.stdout, output)
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 destructions)

    def test_nested_scalar_calls_evaluate_left_to_right(self):
        result = self.execute(
            'fn mark(n: Int) -> Int { print(n); return n; } '
            'fn pair(a: Int, b: Int) -> Int { print(a); print(b); return 9; } '
            'let mut result = pair(mark(1), pair(mark(2), mark(3))); print(result);')
        self.assertEqual(result.stdout, '1\n2\n3\n2\n3\n1\n9\n9\n')

    def test_read_completes_before_transfer(self):
        self.check_sources(
            'fn read(a: &Int) -> Int { print(a); return 7; } '
            'fn consume(n: Int, mut a: -> Int) { print(n); print(a); drop(-> a); } '
            'let mut data = new(memory) Int(42); consume(read(&data), -> data); memory.reset();',
            '42\n7\n42\n', ['destroy data=42'])

    def test_stored_borrow_last_used_by_earlier_argument_can_end_before_transfer(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.check_sources(
                    'fn read(a: ' + mode + 'Int) -> Int { print(a); return 7; } '
                    'fn consume(n: Int, mut a: -> Int) { print(n); drop(-> a); } '
                    'let mut data = new(memory) Int(42); let mut view = ' + mode + 'data; '
                    'consume(read(view), -> data);',
                    '42\n7\n', ['destroy data=42'])

    def test_access_after_transfer_in_later_argument_is_rejected(self):
        self.rejected(
            'fn read(a: &Int) -> Int { print(a); return 7; } '
            'fn consume(mut a: -> Int, n: Int) {} '
            'let mut data = new(memory) Int(42); consume(-> data, read(&data));', 'plus utilisable')

    def test_future_use_of_stored_borrow_still_prevents_transfer(self):
        self.rejected(
            'fn read(a: &Int) -> Int { print(a); return 7; } '
            'fn consume(n: Int, mut a: -> Int) {} '
            'let mut data = new(memory) Int(42); let mut view = &data; '
            'consume(read(view), -> data); print(view);', 'emprunt encore utilisé')

    def test_pending_shared_or_mutable_borrow_blocks_conflicting_later_expression(self):
        cases = [
            ('a: &Int', '&data', 'fn effect(a: &mut Int) -> Int { a.set(9); return 1; }',
             'effect(&mut data)'),
            ('a: &mut Int', '&mut data', 'fn effect(a: &Int) -> Int { print(a); return 1; }',
             'effect(&data)'),
            ('a: &Int', '&data', 'fn effect(mut a: -> Int) -> Int { drop(-> a); return 1; }',
             'effect(-> data)'),
        ]
        for param, first, helper, second in cases:
            with self.subTest(first=first, second=second):
                self.rejected(helper + ' fn outer(' + param + ', n: Int) { print(a); } '
                              'let mut data = new(memory) Int(42); outer(' + first + ', ' + second + ');',
                              'emprunt')

    def test_pending_shared_borrow_allows_another_shared_nested_read(self):
        self.check_sources(
            'fn read(a: &Int) -> Int { print(a); return 7; } '
            'fn outer(a: &Int, n: Int) { print(a); print(n); } '
            'let mut data = new(memory) Int(42); let mut view = &data; '
            'outer(view, read(view)); print(data);',
            '42\n42\n7\n42\n', ['destroy data=42'])

    def test_reset_cannot_destroy_prepared_owned_or_borrowed_argument(self):
        for param, first in (('mut a: -> Int', '-> data'), ('a: &Int', '&data'),
                             ('a: &mut Int', '&mut data')):
            with self.subTest(param=param):
                self.rejected(
                    'fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                    'fn outer(' + param + ', n: Int) { print(a); } '
                    'let mut data = new(memory) Int(42); outer(' + first + ', clear(&mut memory));',
                    'reset interdit')

    def test_reset_before_later_read_is_rejected_but_prior_read_can_end(self):
        prefix = ('fn read(a: &Int) -> Int { print(a); return 7; } '
                  'fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 8; } '
                  'fn pair(a: Int, b: Int) { print(a); print(b); } '
                  'let mut data = new(memory) Int(42); ')
        self.rejected(prefix + 'pair(clear(&mut memory), read(&data));', 'reset interdit')
        self.check_sources(prefix + 'let mut view = &data; '
                           'pair(read(view), clear(&mut memory));',
                           '42\n7\n8\n', ['destroy data=42'])

    def test_pending_source_borrow_blocks_later_conflicting_source_call(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.rejected(
                    'fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                    'fn outer(mem: ' + mode + 'Allocator, n: Int) {} '
                    'outer(' + mode + 'memory, clear(&mut memory));', 'arguments aliasés')

    def test_owned_allocation_expressions_require_explicit_transfer(self):
        self.check_sources(
            'fn make(mem: &mut Allocator) -> <- Int { '
            'let mut fresh = new(mem) Int(20); return <- fresh; } '
            'fn consume(mut a: -> Int, mut b: -> Int) { print(a); print(b); } '
            'consume(-> new(memory) Int(10), -> make(&mut memory)); memory.reset();',
            '10\n20\n', ['destroy fresh=20', 'destroy a=10'])
        self.rejected('fn consume(mut a: -> Int) {} consume(new(memory) Int(10));', 'mode attendu')

    def test_borrowed_expression_temporaries_remain_valid_until_scope_cleanup(self):
        self.check_sources(
            'fn make(mem: &mut Allocator) -> <- Int { '
            'let mut fresh = new(mem) Int(20); return <- fresh; } '
            'fn read(a: &Int, b: &mut Int) { print(a); b.set(21); print(b); } '
            'read(&new(memory) Int(10), &mut make(&mut memory)); memory.reset();',
            '10\n21\n', ['destroy fresh=21', 'destroy a=10'])

    def test_prepared_temporary_cannot_be_destroyed_by_later_reset(self):
        for param, argument in (('mut a: -> Int', '-> new(memory) Int(10)'),
                                ('a: &Int', '&new(memory) Int(10)')):
            with self.subTest(argument=argument):
                self.rejected(
                    'fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                    'fn outer(' + param + ', n: Int) {} '
                    'outer(' + argument + ', clear(&mut memory));', 'reset interdit')

    def test_block_expressions_in_arguments_are_indexed_and_transferred(self):
        self.check_sources(
            'fn consume(mut a: -> Int, n: Int) { print(a); print(n); } '
            'fn mark(n: Int) -> Int { print(n); return n; } '
            'consume(-> { let mut temp = new(memory) Int(99); print(temp); '
            'let mut kept = new(memory) Int(42); <- kept }, mark(7));',
            '99\n7\n42\n7\n', ['destroy temp=99', 'destroy kept=42'])

    def test_early_return_in_later_argument_cleans_prepared_allocation_once(self):
        self.check_sources(
            'fn consume(mut a: -> Int, mut b: -> Int) {} '
            'fn work(mem: &mut Allocator) { '
            'consume(-> new(mem) Int(10), -> { return; }); } work(&mut memory);',
            '', ['destroy a=10'])

    def test_enum_expression_transfers_preserve_arm_and_cleanup_order(self):
        result = self.execute('''
            enum E { A { n: i32 }, B }

            fn make(mem: &mut Pool<E>) -> A<E> {
                let fresh = mem.new(E.B {});
                return fresh;
            }

            fn consume(a: A<E>, b: A<E>) {
                print(a);
                print(b);
            }

            fn main() {
                let mut memory = pool<E>(1);
                consume(memory.new(E.A { n: 42 }), make(&mut memory));
            }
        ''', add_source=False, allow_legacy_reset=False)
        self.assertEqual(result.stdout, 'E.A(42)\nE.B()\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy fresh=E.B', 'destroy a=E.A'])

    def test_wrong_expression_results_produce_diagnostics(self):
        prefix = ('fn scalar(a: Int) {} fn owned(mut a: -> Int) {} '
                  'fn read(a: &Int) {} fn nothing() {} ')
        for call in ('scalar(nothing());', 'scalar(new(memory) Int(1));',
                     'scalar(-> new(memory) Int(1));', 'owned(-> nothing());',
                     'read(&nothing());', 'read(&1);', 'scalar(allocator());'):
            with self.subTest(call=call), self.assertRaises(Error):
                compile_source('let mut memory = allocator(); ' + prefix + call)

    def test_successive_mutable_reborrows_complete_in_argument_order(self):
        self.check_sources(
            'fn edit(a: &mut Int, n: Int) -> Int { a.set(9); print(n); return n; } '
            'fn pair(a: Int, b: Int) { print(a); print(b); } '
            'let mut data = new(memory) Int(42); let mut view = &mut data; '
            'pair(edit(view, 1), edit(view, 2)); print(data);',
            '1\n2\n1\n2\n9\n', ['destroy data=9'])

    def test_nested_reborrow_cannot_end_protection_of_outer_argument(self):
        self.rejected(
            'fn read(a: &Int) -> Int { print(a); return 1; } '
            'fn edit(a: &mut Int) -> Int { a.set(9); return 2; } '
            'fn outer(a: &Int, b: Int, c: Int) { print(a); } '
            'let mut data = new(memory) Int(42); let mut view = &data; '
            'outer(view, read(view), edit(&mut data));', 'emprunt')

    def test_scalar_copy_survives_reset_and_reuse_in_following_argument(self):
        result = self.execute(
            'let mut memory = pool<Int>(1); '
            'fn read(a: &Int) -> Int { print(a); return 7; } '
            'fn replace(mem: &mut Pool<Int>) -> <- Int { '
            'mem.reset(); let mut fresh = new(mem) Int(43); return <- fresh; } '
            'fn consume(n: Int, mut a: -> Int) { print(n); print(a); } '
            'let mut data = new(memory) Int(42); '
            'consume(read(&data), -> replace(&mut memory));')
        self.assertEqual(result.stdout, '42\n7\n43\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=42', 'destroy fresh=43'])


if __name__ == '__main__':
    unittest.main()
