"""Memory checks must not depend on whether a function has callers."""
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_program, compile_source, Error
import test_crust


class FunctionBodyTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def rejected_body(self, source, message):
        with self.assertRaisesRegex(Error, message):
            compile_source(source)

    def test_unused_use_after_drop(self):
        self.rejected_body('fn broken(mut data: -> Int) { drop(-> data); print(data); }', 'plus utilisable')

    def test_unused_double_drop(self):
        self.rejected_body('fn broken(mut data: -> Int) { drop(-> data); drop(-> data); }', 'plus utilisable')

    def test_unused_use_after_move(self):
        self.rejected_body('fn broken(mut data: -> Int) { let mut next = <- data; print(next); print(data); }',
                           'plus utilisable')

    def test_unused_use_after_child_destruction(self):
        self.rejected_body('fn broken(mut data: -> Int) { { -> data; } print(data); }', 'plus utilisable')

    def test_unused_borrow_blocks_drop(self):
        self.rejected_body('fn broken(mut data: -> Int) { let mut view = &data; drop(-> data); print(view); }',
                           'emprunt')

    def test_unused_borrow_blocks_move(self):
        self.rejected_body('fn broken(mut data: -> Int) { let mut view = &data; let mut next = <- data; '
                           'print(view); print(next); }', 'emprunt')

    def test_unused_double_mutable_borrow(self):
        self.rejected_body('fn broken(mut data: -> Int) { let mut a = &mut data; let mut b = &mut data; '
                           'print(a); print(b); }', 'emprunt')

    def test_unused_read_borrow_blocks_mutable_borrow(self):
        self.rejected_body('fn broken(mut data: -> Int) { let mut a = &data; let mut b = &mut data; '
                           'print(a); print(b); }', 'emprunt')

    def test_unused_mutable_borrow_blocks_direct_read(self):
        self.rejected_body('fn broken(mut data: -> Int) { let mut view = &mut data; print(data); print(view); }',
                           'emprunt')

    def test_unused_read_parameter_cannot_mutate(self):
        self.rejected_body('fn broken(data: &Int) { data.set(2); }', 'lecture')

    def test_unused_borrowed_parameter_cannot_be_consumed(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                self.rejected_body('fn broken(data: ' + mode + 'Int) { drop(-> data); }',
                                   'allocation explicite')

    def test_unused_branch_consumption_invalidates_following_access(self):
        self.rejected_body('fn broken(mut data: -> Int, n: Int) { '
                           'if n == 0 { -> data; drop(-> data); } print(data); }',
                           'plus utilisable|chemins')

    def test_unused_loop_cannot_consume_on_every_iteration(self):
        self.rejected_body('fn broken(mut data: -> Int) { loop { -> data; drop(-> data); continue; } }',
                           'boucle|itération|plus utilisable')

    def test_unused_reassignment_rejects_live_borrow(self):
        self.rejected_body('fn broken(mem: &mut Allocator, mut data: -> Int) { '
                           'let mut view = &data; data = new(mem) Int(2); print(view); }', 'emprunt')

    def test_unused_call_rejects_same_value_in_two_exclusive_arguments(self):
        self.rejected_body('fn edit(a: &mut Int, b: &mut Int) {} '
                           'fn broken(mut data: -> Int) { edit(&mut data, &mut data); }',
                           'aliasés|emprunt')

    def test_unused_argument_protects_earlier_borrow_from_later_consumption(self):
        self.rejected_body('fn consume(mut data: -> Int) -> Int { drop(-> data); return 1; } '
                           'fn observe(data: &Int, n: Int) {} '
                           'fn broken(mut data: -> Int) { observe(&data, consume(-> data)); }', 'emprunt')

    def test_unused_stored_reborrow_is_still_restricted(self):
        self.rejected_body('fn broken(data: &mut Int) { let mut view = &mut data; print(view); }',
                           'emprunt imbriqué')

    def test_unused_scalar_return_type_checked(self):
        self.rejected_body('fn broken() -> Int {}', 'retour.*attendu scalar')

    def test_unused_owned_return_cannot_return_borrow(self):
        self.rejected_body('fn broken(data: &Int) -> <- Int { return <- data; }',
                           'allocation explicite|paramètre|emprunt')

    def test_last_use_allows_successive_mutable_borrows(self):
        compiler, _ = compile_program('fn valid(mut data: -> Int) { let mut first = &mut data; first.set(2); '
                                      'let mut second = &mut data; second.set(3); drop(-> data); }')
        self.assertEqual(compiler.verified_functions, {'valid'})

    def test_shared_parameter_aliasing_remains_allowed(self):
        result = self.execute('fn read(a: &Int, b: &Int) { print(a); print(b); } '
                              'let mut data = new(memory) Int(42); read(&data, &data);')
        self.assertEqual(result.stdout, '42\n42\n')

    def test_mutable_parameter_can_be_reborrowed_for_a_call(self):
        compiler, _ = compile_program('fn edit(data: &mut Int) { data.set(2); } '
                                      'fn valid(data: &mut Int) { edit(data); print(data); }')
        self.assertEqual(compiler.verified_functions, {'edit', 'valid'})

    def test_consumption_then_break_is_allowed(self):
        compiler, _ = compile_program('fn valid(mut data: -> Int) { loop { -> data; drop(-> data); break; } }')
        self.assertEqual(compiler.verified_functions, {'valid'})

    def test_symbolic_sources_respect_inferred_equality(self):
        compiler, _ = compile_program('fn consume(mem: &mut Allocator, mut data: -> Int) { mem.drop(-> data); } '
                                      'fn valid(mem: &mut Allocator, mut data: -> Int) { consume(mem, -> data); }')
        self.assertEqual(compiler.verified_functions, {'consume', 'valid'})

    def test_unused_enum_body_and_generic_source_forwarding(self):
        compiler, _ = compile_program('enum E { A { value: Int }, B {} } '
            'fn make(mem: &mut Pool<E>) -> <- E { let mut value = new(mem) E.A { value: 7 }; return <- value; } '
            'fn valid(mem: &mut Allocator) -> <- E { let mut value = make(mem); return <- value; }')
        self.assertEqual(compiler.verified_functions, {'make', 'valid'})

    def test_unused_function_does_not_emit_definitions_or_symbolic_values(self):
        compiler, c = compile_program('fn unused(mut data: -> Int) { print(data); } fn main() {}')
        self.assertEqual(compiler.verified_functions, {'unused', 'main'})
        self.assertEqual(len(compiler.definitions), 1)
        self.assertNotIn('symbolic_', c)

    def test_called_and_uncalled_bodies_reject_same_memory_errors(self):
        for body, message in (
            ('drop(-> data); print(data);', 'plus utilisable'),
            ('let mut r = &data; drop(-> data); print(r);', 'emprunt'),
            ('let mut a = &mut data; let mut b = &mut data; print(a); print(b);', 'emprunt'),
        ):
            function = 'fn broken(mut data: -> Int) { ' + body + ' } '
            for caller in ('', 'let mut memory = pool<Int>(1); let mut x = new(memory) Int(7); broken(-> x);'):
                with self.subTest(body=body, called=bool(caller)):
                    self.rejected_body(function + caller, message)


if __name__ == '__main__':
    unittest.main()
