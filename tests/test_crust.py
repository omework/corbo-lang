from functools import partial, update_wrapper
import os
import random
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import __file__ as prototype_file
from crust import compile_source, Error, Parser

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)


class PrototypeTests(unittest.TestCase):
    @staticmethod
    def with_source(source):
        # Existing semantic cases explicitly select a heap source.
        if any((node.op == 'var' and node.args[0] == 'memory') or
               (node.op == 'fn' and node.args[0] == 'main') for node in Parser(source).parse()):
            return source
        return 'let mut memory = allocator();\n' + source

    def rejected(self, source, message):
        with self.assertRaisesRegex(Error, message):
            compile_source(self.with_source(source))

    def execute(self, source, *, add_source=True, allow_legacy_reset=True):
        compiler = shutil.which('clang') or shutil.which('cc')
        if not compiler:
            self.skipTest('C compiler unavailable')
        with tempfile.TemporaryDirectory() as folder:
            source_path = Path(folder) / 'program.c'
            executable = Path(folder) / 'program'
            source_path.write_text(compile_source(self.with_source(source) if add_source else source,
                                                 allow_legacy_reset=allow_legacy_reset))
            command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Wno-unused-variable',
                       '-Wno-unused-function', '-Werror', str(source_path), '-o', str(executable)]
            if os.environ.get('CRUST_SANITIZE'):
                sanitizers = os.environ['CRUST_SANITIZE']
                if sanitizers == '1':
                    sanitizers = 'address,undefined'
                if sanitizers not in ('address', 'undefined', 'address,undefined'):
                    raise ValueError('CRUST_SANITIZE: address, undefined, address,undefined ou 1')
                command[1:1] = [f'-fsanitize={sanitizers}', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
            build = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            return subprocess.run([str(executable)], check=True, capture_output=True, text=True, timeout=10)

    def test_real_demo(self):
        result = self.execute((Path(__file__).resolve().parents[1] / 'examples/valid.crb').read_text())
        self.assertEqual(result.stdout, '99\n42\n43\n2\n43\n')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy temporary=99', 'free temporary',
            'destroy first=2', 'free first', 'destroy data=43', 'free data'])

    def test_destroy_then_free_reverse_creation(self):
        result = self.execute('let mut a = new(memory) Int(1); print(a); let mut b = new(memory) Int(2); print(b);')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy b=2', 'free b', 'destroy a=1', 'free a'])

    def test_move_and_primitive_copy(self):
        result = self.execute('let mut n = 7; let mut m = n; print(n); print(m); '
                              'let mut a = new(memory) Int(3); let mut b = <- a; print(b);')
        self.assertEqual(result.stdout, '7\n7\n3\n')
        self.assertEqual(result.stderr.count('destroy'), 1)

    def test_reassignment_destroys_old_allocation(self):
        result = self.execute('let mut a = new(memory) Int(1); print(a); a = new(memory) Int(2); print(a);')
        self.assertEqual(result.stdout, '1\n2\n')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy a=1', 'free a', 'destroy a=2', 'free a'])

    def test_multiple_read_borrows(self):
        self.execute('let mut a = new(memory) Int(1); let mut r = &a; let mut s = &a; print(r); print(s);')

    def test_last_use_ends_borrow(self):
        self.execute('let mut a = new(memory) Int(1); let mut r = &mut a; r.set(2); '
                     'let mut s = &mut a; s.set(3); print(s); let mut b = <- a; print(b);')

    def test_live_borrow_blocks_move(self):
        self.rejected('let mut a = new(memory) Int(1); let mut r = &a; let mut b = <- a; print(r);', 'emprunt')

    def test_exclusive_mutable_borrow(self):
        self.rejected('let mut a = new(memory) Int(1); let mut r = &mut a; let mut s = &mut a; print(r);', 'emprunt')

    def test_reader_blocks_writer(self):
        self.rejected('let mut a = new(memory) Int(1); let mut r = &a; let mut s = &mut a; print(r);', 'emprunt')

    def test_mutable_borrow_blocks_direct_read(self):
        self.rejected('let mut a = new(memory) Int(1); let mut r = &mut a; print(a); print(r);', 'emprunt')

    def test_read_borrow_cannot_write(self):
        self.rejected('let mut a = new(memory) Int(1); let mut r = &a; r.set(2);', 'lecture')

    def test_implicit_alias_rejected(self):
        self.rejected('let mut a = new(memory) Int(1); let mut b = a;', 'implicite')

    def test_use_after_move(self):
        self.rejected('let mut a = new(memory) Int(1); let mut b = <- a; print(b); print(a);', 'plus utilisable')

    def test_use_after_child_destruction(self):
        self.rejected('let mut a = new(memory) Int(1); { -> a; } print(a);', 'plus utilisable')

    def test_downward_transfer_requires_entry(self):
        self.rejected('let mut a = new(memory) Int(1); { print(a); -> a; }', 'entrée')

    def test_downward_transfer_requires_direct_parent(self):
        self.rejected('let mut a = new(memory) Int(1); { { -> a; } }', 'parent direct')

    def test_unused_receiver_rejected(self):
        self.rejected('let mut a = { let mut x = new(memory) Int(1); <- x };', 'sans usage')

    def test_local_scalar_not_transferable(self):
        self.rejected('let mut a = { let mut x = 1; <- x }; print(a);', 'allocation explicite')

    def test_no_implicit_downward_move(self):
        self.rejected('let mut a = new(memory) Int(1); { let mut b = <- a; print(b); }', 'descendant')

    def test_reception_and_child_cleanup_order(self):
        result = self.execute('let mut result = { let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); print(b); '
                              '<- a }; print(result);')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy b=2', 'free b', 'destroy a=1', 'free a'])

    def test_group_reception_keeps_relative_order(self):
        result = self.execute('let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); '
                              '{ -> a; -> b; <- b; <- a; } print(a); print(b);')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy b=2', 'free b', 'destroy a=1', 'free a'])

    def test_uninitialized_new_rejected(self):
        self.rejected('let mut a = new(memory) Int();', 'initialisée attendue')

    def test_unknown_syntax_rejected(self):
        self.rejected('free(a);', 'fonction inconnue')

    def test_source_required(self):
        self.rejected('let mut a = new Int(1);', 'source explicite')

    def test_unknown_source(self):
        self.rejected('let mut a = new(missing) Int(1);', 'inconnue')

    def test_wrong_source_type(self):
        self.rejected('let mut count = 10; let mut a = new(count) Int(1);', 'source de stockage')

    def test_drop_runs_once_and_reset_succeeds(self):
        result = self.execute('let mut a = new(memory) Int(1); memory.drop(-> a); memory.reset();')
        self.assertEqual(result.stderr.splitlines(), ['destroy a=1', 'free a', 'reset'])

    def test_use_after_drop(self):
        self.rejected('let mut a = new(memory) Int(1); memory.drop(-> a); print(a);', 'plus utilisable')

    def test_double_drop(self):
        self.rejected('let mut a = new(memory) Int(1); memory.drop(-> a); memory.drop(-> a);', 'plus utilisable')

    def test_drop_requires_move(self):
        self.rejected('let mut a = new(memory) Int(1); memory.drop(&a);', "drop exige un transfert -> explicite")

    def test_drop_checks_allocator_identity(self):
        self.rejected('let mut other = allocator(); let mut a = new(memory) Int(1); other.drop(-> a);', 'origine')

    def test_drop_with_live_borrow(self):
        self.rejected('let mut a = new(memory) Int(1); let mut r = &a; memory.drop(-> a); print(r);', 'emprunt')

    def test_reset_destroys_unused_but_live_allocation(self):
        result = self.execute('let mut a = new(memory) Int(1); print(a); memory.reset();')
        self.assertEqual(result.stdout, '1\n')
        self.assertEqual(result.stderr.splitlines(), ['destroy a=1', 'free a', 'reset'])

    def test_reset_does_not_repeat_reassignment_cleanup(self):
        result = self.execute('let mut a = new(memory) Int(1); print(a); a = new(memory) Int(2); '
                              'memory.drop(-> a); memory.reset();')
        self.assertEqual(result.stderr.splitlines(),
                         ['destroy a=1', 'free a', 'destroy a=2', 'free a', 'reset'])

    def test_reset_after_child_cleanup(self):
        self.execute('{ let mut a = new(memory) Int(1); print(a); } memory.reset();')

    def test_transfer_from_child_allocator_rejected(self):
        self.rejected('let mut result = { let mut local = allocator(); let mut a = new(local) Int(1); <- a }; '
                      'print(result);', 'ne survit pas')

    def test_nested_transfer_preserves_address(self):
        result = self.execute('let mut result = { let mut middle = { let mut a = new(memory) Int(42); '
                              'address(a); <- a }; <- middle }; address(result); print(result);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2], '42')

    def test_stack_delays_reclamation_until_suffix_dies(self):
        result = self.execute('let mut memory = stack(65536); let mut a = new(memory) Int(1); '
                              'let mut b = new(memory) Int(2); memory.drop(-> a); '
                              'print(b); memory.drop(-> b); memory.reset();')
        self.assertEqual(result.stdout, '2\n')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy a=1', 'destroy b=2', 'reclaim b', 'reclaim a', 'reset'])

    def test_stack_transfer_address_and_reset_reuse(self):
        result = self.execute('let mut memory = stack(65536); let mut result = { '
                              'let mut a = new(memory) Int(42); address(a); <- a }; '
                              'address(result); memory.drop(-> result); memory.reset(); '
                              'let mut b = new(memory) Int(43); address(b);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[0], lines[2])

    def test_stack_allocator_cannot_escape(self):
        self.rejected('let mut result = { let mut local = stack(65536); '
                      'let mut a = new(local) Int(42); <- a }; print(result);', 'ne survit pas')

    def test_source_cannot_implicitly_move(self):
        self.rejected('let mut other = memory;', 'implicite')

    def test_source_reassignment_rejected(self):
        self.rejected('memory = allocator();', 'réaffectée')

    def test_stack_reservation_must_be_positive(self):
        self.rejected('let mut local = stack(0);', 'strictement positive')

    def test_stack_overflow_has_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'overflow.crb'
            source.write_text('let mut memory = stack(1); let mut a = new(memory) Int(1); print(a);')
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     str(source), '--run'], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('data stack capacity exceeded', result.stderr)

    def test_functions_demo(self):
        result = self.execute((Path(__file__).resolve().parents[1] / 'examples/functions.crb').read_text(),
                              add_source=False)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2:], ['42', '43'])
        self.assertEqual(result.stderr.splitlines(), [
            'destroy temporary=99', 'free temporary', 'destroy data=43', 'free data', 'reset'])

    def test_function_can_allocate_repeatedly_from_same_source(self):
        result = self.execute('fn make(mem: &mut Allocator, value: Int) -> <- Int { '
                              'let mut a = new(mem) Int(value); <- a } '
                              'let mut a = make(&mut memory, 1); let mut b = make(&mut memory, 2); '
                              'print(a); print(b);')
        self.assertEqual(result.stdout, '1\n2\n')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy a=2', 'free a', 'destroy a=1', 'free a'])

    def test_function_accepts_stack_source(self):
        result = self.execute('let mut memory = stack(65536); '
                              'fn make(mem: &mut Allocator) -> <- Int { '
                              'let mut a = new(mem) Int(7); address(a); return <- a; } '
                              'let mut a = make(&mut memory); address(a); print(a);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2], '7')
        self.assertEqual(result.stderr.splitlines(), ['destroy a=7', 'reclaim a'])

    def test_function_scalar_copy_and_return(self):
        result = self.execute('fn identity(n: Int) -> Int { return n; } '
                              'let mut n = 7; let mut result = identity(n); print(result); print(n);')
        self.assertEqual(result.stdout, '7\n7\n')

    def test_function_scalar_tail_return(self):
        result = self.execute('fn identity(n: Int) -> Int { n } '
                              'let mut result = identity(8); print(result);')
        self.assertEqual(result.stdout, '8\n')

    def test_function_consumes_and_automatically_destroys(self):
        result = self.execute('fn consume(mut a: -> Int) { print(a); } '
                              'let mut a = new(memory) Int(9); consume(-> a); memory.reset();')
        self.assertEqual(result.stderr.splitlines(), ['destroy a=9', 'free a', 'reset'])

    def test_function_move_invalidates_caller(self):
        self.rejected('fn consume(mut a: -> Int) {} let mut a = new(memory) Int(9); '
                      'consume(-> a); print(a);', 'plus utilisable')

    def test_function_move_blocks_live_borrow(self):
        self.rejected('fn consume(mut a: -> Int) {} let mut a = new(memory) Int(9); '
                      'let mut r = &a; consume(-> a); print(r);', 'emprunt')

    def test_function_call_mode_must_match_signature(self):
        self.rejected('fn consume(mut a: -> Int) {} let mut a = new(memory) Int(9); consume(&a);', 'mode attendu')

    def test_function_mutable_borrow_and_nested_reborrow(self):
        result = self.execute('fn write(a: &mut Int) { a.set(10); } '
                              'fn forward(a: &mut Int) { write(a); print(a); } '
                              'let mut a = new(memory) Int(1); let mut edit = &mut a; '
                              'forward(edit); print(edit); print(a);')
        self.assertEqual(result.stdout, '10\n10\n10\n')

    def test_function_read_borrow_cannot_write(self):
        self.rejected('fn write(a: &Int) { a.set(10); } '
                      'let mut a = new(memory) Int(1); write(&a);', 'lecture')

    def test_function_read_borrow_cannot_be_upgraded(self):
        self.rejected('fn write(a: &mut Int) {} fn forward(a: &Int) { write(a); } '
                      'let mut a = new(memory) Int(1); forward(&a);', 'lecture')

    def test_function_arguments_exclusivity(self):
        self.rejected('fn write(a: &mut Int, b: &Int) {} '
                      'let mut a = new(memory) Int(1); write(&mut a, &a);', 'aliasés')

    def test_function_read_aliases_allowed(self):
        result = self.execute('fn read(a: &Int, b: &Int) { print(a); print(b); } '
                              'let mut a = new(memory) Int(1); read(&a, &a);')
        self.assertEqual(result.stdout, '1\n1\n')

    def test_function_allocator_arguments_exclusivity(self):
        self.rejected('fn work(a: &mut Allocator, b: &mut Allocator) {} '
                      'work(&mut memory, &mut memory);', 'aliasés')

    def test_function_readonly_allocator_cannot_allocate(self):
        self.rejected('fn work(mem: &Allocator) { let mut a = new(mem) Int(1); } '
                      'work(&memory);', 'emprunt mutable')

    def test_function_reset_sees_caller_allocations(self):
        result = self.execute('fn clear(mem: &mut Allocator) { mem.reset(); } '
                              'let mut a = new(memory) Int(1); print(a); clear(&mut memory);')
        self.assertEqual(result.stderr.splitlines(), ['destroy a=1', 'free a', 'reset'])

    def test_function_drop_checks_real_source_through_parameters(self):
        self.rejected('fn destroy(mem: &mut Allocator, mut a: -> Int) { mem.drop(-> a); } '
                      'let mut other = allocator(); let mut a = new(memory) Int(1); '
                      'destroy(&mut other, -> a);', 'origine')

    def test_function_local_allocator_cannot_escape(self):
        self.rejected('fn make() -> <- Int { let mut local = allocator(); '
                      'let mut a = new(local) Int(1); return <- a; } '
                      'let mut a = make(); print(a);', 'ne survit pas')

    def test_function_cannot_capture_caller_allocator(self):
        self.rejected('fn make() -> <- Int { let mut a = new(memory) Int(1); <- a } '
                      'let mut a = make(); print(a);', "inconnue 'memory'")

    def test_function_cannot_capture_caller_allocation(self):
        self.rejected('fn hidden() { print(a); } let mut a = new(memory) Int(1); hidden();', "inconnue 'a'")

    def test_function_return_cleans_nested_scopes(self):
        result = self.execute('fn make(mem: &mut Allocator) -> <- Int { '
                              'let mut first = new(mem) Int(1); print(first); { let mut second = new(mem) Int(2); print(second); '
                              '{ let mut result = new(mem) Int(3); return <- result; } } '
                              'let mut unreachable = new(mem) Int(99); } '
                              'let mut result = make(&mut memory); print(result);')
        self.assertEqual(result.stdout, '1\n2\n3\n')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy second=2', 'free second', 'destroy first=1', 'free first',
            'destroy result=3', 'free result'])

    def test_function_void_early_return_cleans(self):
        result = self.execute('fn work(mem: &mut Allocator) { let mut a = new(mem) Int(1); print(a); '
                              '{ let mut b = new(mem) Int(2); print(b); return; } print(a); } work(&mut memory);')
        self.assertEqual(result.stdout, '1\n2\n')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy b=2', 'free b', 'destroy a=1', 'free a'])

    def test_function_nested_forwarding_keeps_provenance(self):
        result = self.execute('fn make(mem: &mut Allocator) -> <- Int { '
                              'let mut a = new(mem) Int(5); <- a } '
                              'fn forward(mem: &mut Allocator) -> <- Int { '
                              'let mut a = make(mem); return <- a; } '
                              'let mut a = forward(&mut memory); memory.drop(-> a); memory.reset();')
        self.assertEqual(result.stderr.splitlines(), ['destroy a=5', 'free a', 'reset'])

    def test_function_owned_argument_group_order(self):
        result = self.execute('fn consume(mut b: -> Int, mut a: -> Int) {} '
                              'let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); '
                              'consume(-> b, -> a);')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy b=2', 'free b', 'destroy a=1', 'free a'])

    def test_function_return_type_checked(self):
        self.rejected('fn wrong(n: Int) -> <- Int { return n; } '
                      'let mut n = wrong(1); print(n);', 'retour')

    def test_function_return_allocation_requires_explicit_move(self):
        self.rejected('fn make(mem: &mut Allocator) -> <- Int { '
                      'return new(mem) Int(1); } let mut a = make(&mut memory); print(a);',
                      '<- explicite requis')

    def test_function_forwarded_result_requires_explicit_move(self):
        self.rejected('fn make(mem: &mut Allocator) -> <- Int { '
                      'let mut a = new(mem) Int(1); <- a } '
                      'fn forward(mem: &mut Allocator) -> <- Int { return make(mem); } '
                      'let mut a = forward(&mut memory); print(a);', '<- explicite requis')

    def test_function_nonvoid_result_needs_receiver(self):
        self.rejected('fn make(mem: &mut Allocator) -> <- Int { '
                      'let mut a = new(mem) Int(1); <- a } make(&mut memory);', 'sans receveur')

    def test_function_result_needs_use(self):
        self.rejected('fn make(mem: &mut Allocator) -> <- Int { '
                      'let mut a = new(mem) Int(1); <- a } let mut a = make(&mut memory);', 'sans usage')

    def test_function_allocator_parameter_mode_required(self):
        self.rejected('fn work(mem: Allocator) {}', 'explicitement emprunté')

    def test_function_arity_checked(self):
        self.rejected('fn work(n: Int) {} work();', 'attend 1')

    def test_function_duplicate_parameters(self):
        self.rejected('fn work(n: Int, n: Int) {}', 'dupliqué')

    def test_function_recursion_rejected_for_now(self):
        self.rejected('fn recurse() { recurse(); } recurse();', 'récursion')

    def test_forward_declaration_and_scalar_initializer(self):
        result = self.execute('let mut a = new(memory) Int(identity(6)); print(a); '
                              'fn identity(n: Int) -> Int { return n; }')
        self.assertEqual(result.stdout, '6\n')

    def test_pool_demo(self):
        result = self.execute((Path(__file__).resolve().parents[1] / 'examples/pool.crb').read_text(),
                              add_source=False)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2:], ['10', '30', '40'])
        self.assertEqual(result.stderr.splitlines(), [
            'destroy data=20', 'reuse data', 'destroy data=40', 'destroy data=30',
            'reclaim data', 'reclaim data', 'destroy data=10', 'reclaim data', 'reset'])

    def test_pool_reuses_hole_at_capacity(self):
        result = self.execute('let mut memory = pool<Int>(3); let mut a = new(memory) Int(1); '
                              'let mut b = new(memory) Int(2); let mut c = new(memory) Int(3); '
                              'address(b); memory.drop(-> b); let mut d = new(memory) Int(4); '
                              'address(d); print(a); print(c); print(d);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2:], ['1', '3', '4'])
        self.assertIn('reuse d', result.stderr)
        self.assertNotIn('free ', result.stderr)

    def test_pool_lifo_free_slots(self):
        result = self.execute('let mut memory = pool<Int>(4); let mut a = new(memory) Int(1); '
                              'let mut b = new(memory) Int(2); let mut c = new(memory) Int(3); '
                              'let mut d = new(memory) Int(4); address(b); address(c); '
                              'memory.drop(-> b); memory.drop(-> c); '
                              'let mut e = new(memory) Int(5); let mut f = new(memory) Int(6); '
                              'address(e); address(f); print(a); print(d);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[3])
        self.assertEqual(lines[1], lines[2])
        self.assertEqual(lines[4:], ['1', '4'])

    def test_pool_reclamation_removes_slots_from_free_index(self):
        result = self.execute('let mut memory = pool<Int>(4); let mut a = new(memory) Int(1); '
                              'let mut b = new(memory) Int(2); let mut c = new(memory) Int(3); '
                              'let mut d = new(memory) Int(4); address(b); address(c); address(d); '
                              'memory.drop(-> b); memory.drop(-> c); let mut e = new(memory) Int(5); '
                              'memory.drop(-> d); memory.drop(-> e); '
                              'let mut f = new(memory) Int(6); let mut g = new(memory) Int(7); '
                              'let mut h = new(memory) Int(8); address(f); address(g); address(h); '
                              'print(a); print(f); print(g); print(h);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:3], lines[3:6])
        self.assertEqual(lines[6:], ['1', '6', '7', '8'])

    def test_pool_reset_reuse(self):
        result = self.execute('let mut memory = pool<Int>(1); let mut a = new(memory) Int(1); '
                              'address(a); memory.drop(-> a); memory.reset(); '
                              'let mut b = new(memory) Int(2); address(b); print(b);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2], '2')

    def test_pool_can_use_generic_allocator_parameter(self):
        result = self.execute('let mut memory = pool<Int>(2); '
                              'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
                              'let mut a = new(mem) Int(n); <- a } '
                              'let mut a = make(&mut memory, 12); print(a);')
        self.assertEqual(result.stdout, '12\n')

    def test_pool_rejects_other_allocation_type(self):
        self.rejected('let mut memory = pool<Int>(2); let mut a = new(memory) Buffer(1);', 'incompatible')

    def test_pool_type_survives_generic_parameter(self):
        # The body check now rejects an unknown type before the real call.
        self.rejected('let mut memory = pool<Int>(2); fn wrong(mem: &mut Allocator) { '
                      'let mut a = new(mem) Buffer(1); } wrong(&mut memory);',
                      'type d.allocation non pris en charge')
        # A valid enum reaches the concrete call's storage compatibility check.
        self.rejected('enum E { A {} } let mut memory = pool<Int>(2); '
                      'fn wrong(mem: &mut Allocator) { let mut a = new(mem) E.A {}; print(a); } '
                      'wrong(&mut memory);', 'incompatible')

    def test_pool_signature_requires_pool(self):
        self.rejected('fn work(mem: &mut Pool<Int>) {} work(&mut memory);', 'attend une source Pool')

    def test_pool_type_must_be_supported(self):
        self.rejected('let mut memory = pool<Buffer>(2);', 'type de pool non pris en charge')

    def test_pool_capacity_positive(self):
        self.rejected('let mut memory = pool<Int>(0);', 'strictement positive')

    def test_pool_parameter_requires_borrow(self):
        self.rejected('fn work(mem: Pool<Int>) {}', 'explicitement emprunté')

    def test_pool_readonly_parameter_cannot_allocate(self):
        self.rejected('let mut memory = pool<Int>(2); fn work(mem: &Pool<Int>) { '
                      'let mut a = new(mem) Int(1); } work(&memory);', 'emprunt mutable')

    def test_pool_local_source_cannot_escape(self):
        self.rejected('let mut result = { let mut local = pool<Int>(2); let mut a = new(local) Int(1); '
                      '<- a }; print(result);', 'ne survit pas')

    def test_pool_reused_slot_does_not_revive_old_binding(self):
        self.rejected('let mut memory = pool<Int>(2); let mut a = new(memory) Int(1); '
                      'let mut b = new(memory) Int(2); print(b); memory.drop(-> a); '
                      'let mut c = new(memory) Int(3); print(c); print(a);', 'plus utilisable')

    def test_pool_drop_checks_provenance(self):
        self.rejected('let mut memory = pool<Int>(2); let mut other = pool<Int>(2); '
                      'let mut a = new(memory) Int(1); other.drop(-> a);', 'origine')

    def test_pool_reset_destroys_remaining_values(self):
        result = self.execute('let mut memory = pool<Int>(2); let mut a = new(memory) Int(1); print(a); '
                              'memory.reset();')
        self.assertEqual(result.stderr.splitlines(), ['destroy a=1', 'reclaim a', 'reset'])

    def test_pool_drop_blocks_live_borrow(self):
        self.rejected('let mut memory = pool<Int>(2); let mut a = new(memory) Int(1); '
                      'let mut r = &a; memory.drop(-> a); print(r);', 'emprunt')

    def test_pool_exhaustion_has_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'overflow.crb'
            source.write_text('let mut memory = pool<Int>(1); let mut a = new(memory) Int(1); '
                              'let mut b = new(memory) Int(2); print(a); print(b);')
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     str(source), '--run'], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pool capacity exceeded', result.stderr)

    def test_pool_interleaved_allocations_preserve_live_values(self):
        # Exercise arbitrary destruction/reuse while staying within seven live slots.
        rng = random.Random(2026)
        code = ['let mut memory = pool<Int>(7);']
        live, expected = {}, []
        created = 0
        for _ in range(100):
            if live and (len(live) == 7 or rng.random() < 0.45):
                name = rng.choice(list(live))
                code.append(f'memory.drop(-> {name});')
                del live[name]
            else:
                name = f'a{created}'
                live[name] = created
                code.append(f'let mut {name} = new(memory) Int({created});')
                created += 1
            for name, value in live.items():
                code.append(f'print({name});')
                expected.append(str(value))
        for name in list(live):
            code.append(f'memory.drop(-> {name});')
        code.append('memory.reset();')
        result = self.execute(' '.join(code))
        self.assertEqual(result.stdout.splitlines(), expected)
        self.assertEqual(result.stderr.count('destroy '), created)

    def test_enum_demo(self):
        result = self.execute((Path(__file__).resolve().parents[1] / 'examples/enums.crb').read_text(),
                              add_source=False)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:2], ['Message.Large(1, 2, 3, 4)', '0'])
        self.assertEqual(lines[2], lines[3])
        self.assertEqual(lines[4:], ['30', '20', '1', '2', '0'])
        self.assertEqual(result.stderr.count('destroy '), 5)
        self.assertIn('reuse message', result.stderr)
        self.assertTrue(result.stderr.endswith('reset\n'))

    def test_enum_slots_have_variant_specific_sizes(self):
        result = self.execute('enum E { Small { n: Int }, Large { a: Int, b: Int, c: Int, d: Int } } '
                              'let mut memory = pool<E>(2); '
                              'let mut s1 = new(memory) E.Small { n: 1 }; '
                              'let mut s2 = new(memory) E.Small { n: 2 }; '
                              'let mut l1 = new(memory) E.Large { a: 1, b: 2, c: 3, d: 4 }; '
                              'let mut l2 = new(memory) E.Large { a: 5, b: 6, c: 7, d: 8 }; '
                              'address(s1); address(s2); address(l1); address(l2);')
        s1, s2, l1, l2 = (int(s, 16) for s in result.stdout.splitlines())
        self.assertGreater(s2 - s1, 0)
        self.assertGreater(l2 - l1, s2 - s1)

    def test_enum_capacity_independent_per_variant(self):
        result = self.execute('enum E { A { n: Int }, B, C { x: Int, y: Int } } '
                              'let mut memory = pool<E>(1); '
                              'let mut a = new(memory) E.A { n: 1 }; let mut b = new(memory) E.B; '
                              'let mut c = new(memory) E.C { x: 2, y: 3 }; '
                              'print(a); print(b); print(c);')
        self.assertEqual(result.stdout, 'E.A(1)\nE.B()\nE.C(2, 3)\n')

    def test_enum_cleanup_preserves_order_across_variants(self):
        result = self.execute('enum E { A, B } let mut memory = pool<E>(2); '
                              'let mut a = new(memory) E.A; print(a); let mut b = new(memory) E.B; print(b); '
                              'let mut c = new(memory) E.A; print(c);')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy c=E.A', 'destroy b=E.B', 'destroy a=E.A'])

    def test_enum_reuse_does_not_move_other_variant(self):
        result = self.execute('enum E { A { n: Int }, B { x: Int, y: Int, z: Int } } '
                              'let mut memory = pool<E>(2); let mut a = new(memory) E.A { n: 1 }; '
                              'let mut a2 = new(memory) E.A { n: 2 }; '
                              'let mut b = new(memory) E.B { x: 3, y: 4, z: 5 }; '
                              'address(a); address(b); memory.drop(-> a); '
                              'let mut a3 = new(memory) E.A { n: 6 }; address(a3); address(b); '
                              'print(a2); print(b); print(a3);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0:2], lines[2:4])
        self.assertEqual(lines[4:], ['E.A(2)', 'E.B(3, 4, 5)', 'E.A(6)'])

    def test_enum_match_reads_named_fields_in_any_order(self):
        result = self.execute('enum E { Pair { x: Int, y: Int }, Empty } '
                              'let mut memory = pool<E>(1); let mut e = new(memory) E.Pair { y: 7, x: 6 }; '
                              'match &e { E.Pair { y: b, x: a } => { print(a); print(b); }, '
                              'E.Empty => { let mut zero = 0; print(zero); } }')
        self.assertEqual(result.stdout, '6\n7\n')

    def test_enum_pool_reset_restores_all_stacks(self):
        result = self.execute('enum E { A, B { n: Int } } let mut memory = pool<E>(1); '
                              'let mut a = new(memory) E.A; let mut b = new(memory) E.B { n: 1 }; '
                              'address(a); address(b); memory.drop(-> a); memory.drop(-> b); '
                              'memory.reset(); let mut c = new(memory) E.A; '
                              'let mut d = new(memory) E.B { n: 2 }; address(c); address(d); print(d);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:2], lines[2:4])
        self.assertEqual(lines[4], 'E.B(2)')

    def test_enum_generic_allocator_function_and_transfer(self):
        result = self.execute('enum E { A { n: Int }, B } '
                              'fn make(mem: &mut Allocator, n: Int) -> <- A<E> { '
                              'let mut e = new(mem) E.A { n: n }; address(e); return <- e; } '
                              'fn forward(mut e: -> A<E>) -> <- A<E> { return <- e; } '
                              'let mut memory = pool<E>(1); let mut e = make(&mut memory, 9); '
                              'let mut result = forward(-> e); address(result); print(result);')
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2], 'E.A(9)')

    def test_enum_reassignment_destroys_old_allocation(self):
        result = self.execute('enum E { A, B } let mut memory = pool<E>(1); '
                              'let mut e = new(memory) E.A; print(e); e = new(memory) E.B; print(e);')
        self.assertEqual(result.stdout, 'E.A()\nE.B()\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy e=E.A', 'destroy e=E.B'])

    def test_enum_validation_diagnostics(self):
        cases = [
            ('enum E {}', 'au moins une variante'),
            ('enum E { A, A }', 'variante dupliquée'),
            ('enum E { A { n: Int, n: Int } }', 'champ enum dupliqué'),
            ('enum E { A { n: Buffer } }', 'champs des variantes doivent être Int'),
            ('enum E { A } enum E { B }', "nom d'enum"),
            ('enum Int { A }', "nom d'enum"),
            ('enum E { A { n: Int } } let mut memory = pool<E>(1); '
             'let mut e = new(memory) E.Unknown;', 'variante inconnue'),
            ('enum E { A { n: Int } } let mut memory = pool<E>(1); '
             'let mut e = new(memory) E.A;', 'champs incorrects'),
            ('enum E { A { n: Int } } let mut memory = pool<E>(1); '
             'let mut e = new(memory) E.A { n: 1, extra: 2 };', 'champs incorrects'),
            ('enum E { A { n: Int } } let mut memory = pool<E>(1); '
             'let mut e = new(memory) E.A { n: 1, n: 2 };', 'plusieurs fois'),
        ]
        for source, diagnostic in cases:
            with self.subTest(source=source):
                self.rejected(source, diagnostic)

    def test_enum_requires_matching_pool(self):
        self.rejected('enum E { A } let mut e = new(memory) E.A;', 'pool<E> requis')

    def test_enum_wrong_pool_enum_type(self):
        self.rejected('enum E { A } enum F { A } let mut memory = pool<E>(1); '
                      'let mut e = new(memory) F.A;', 'pool<F> requis')

    def test_enum_match_diagnostics(self):
        prefix = ('enum E { A { n: Int }, B } let mut memory = pool<E>(1); '
                  'let mut e = new(memory) E.A { n: 1 }; ')
        cases = [
            ('match &e { E.A { n: a } => { print(a); } }', 'non exhaustif'),
            ('match &e { E.A { n: a } => {} E.A { n: b } => {} E.B => {} }', 'dupliquée'),
            ('match &e { E.A { other: a } => {} E.B => {} }', 'champs de match'),
            ('match &e { E.A => {} E.B => {} }', 'champs de match'),
            ('match &e { E.Unknown => {} E.B => {} }', 'variante de match incorrecte'),
            ('match &e { F.A { n: a } => {} E.B => {} }', 'variante de match incorrecte'),
            ('match &e { E.A { n: a } => { memory.drop(-> e); } E.B => {} }', 'lecture uniquement'),
        ]
        for source, diagnostic in cases:
            with self.subTest(source=source):
                self.rejected(prefix + source, diagnostic)

    def test_enum_function_argument_type_checked(self):
        self.rejected('enum E { A } fn f(e: &Int) {} let mut memory = pool<E>(1); '
                      'let mut e = new(memory) E.A; f(&e);', 'attend une allocation Int')

    def test_enum_return_type_checked(self):
        self.rejected('enum E { A } enum F { A } '
                      'fn make(mem: &mut Pool<F>) -> <- E { let mut f = new(mem) F.A; <- f } '
                      'let mut memory = pool<F>(1); let mut e = make(&mut memory); print(e);', 'allocation E attendue')

    def test_enum_implicit_parameter_copy_rejected(self):
        self.rejected('enum E { A } fn f(e: E) {}', 'emprunté ou transféré')

    def test_enum_set_cannot_change_variant_payload(self):
        self.rejected('enum E { A } let mut memory = pool<E>(1); '
                      'let mut e = new(memory) E.A; e.set(1);', 'set exige Int')

    def test_enum_pool_reset_checks_all_arms(self):
        result = self.execute('enum E { A, B } let mut memory = pool<E>(1); '
                              'let mut a = new(memory) E.A; let mut b = new(memory) E.B; print(b); '
                              'memory.drop(-> a); memory.reset();')
        self.assertEqual(result.stderr.splitlines(),
                         ['destroy a=E.A', 'reclaim a', 'destroy b=E.B', 'reclaim b', 'reset'])

    def test_enum_local_pool_cannot_escape(self):
        self.rejected('enum E { A } fn make() -> <- E { let mut local = pool<E>(1); '
                      'let mut e = new(local) E.A; return <- e; } '
                      'let mut e = make(); print(e);', 'ne survit pas')

    def test_enum_drop_preserves_borrow_rules(self):
        self.rejected('enum E { A } let mut memory = pool<E>(1); let mut e = new(memory) E.A; '
                      'let mut r = &e; memory.drop(-> e); print(r);', 'emprunt')

    def test_enum_reuse_does_not_revive_old_handle(self):
        self.rejected('enum E { A } let mut memory = pool<E>(1); let mut e = new(memory) E.A; '
                      'memory.drop(-> e); let mut f = new(memory) E.A; print(f); print(e);', 'plus utilisable')

    def test_enum_wrong_root_pool_drop_rejected(self):
        self.rejected('enum E { A } let mut memory = pool<E>(1); let mut other = pool<E>(1); '
                      'let mut e = new(memory) E.A; other.drop(-> e);', 'origine')

    def test_enum_arm_exhaustion_does_not_borrow_other_arm_capacity(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'overflow.crb'
            source.write_text('enum E { A, B } let mut memory = pool<E>(1); '
                              'let mut a = new(memory) E.A; let mut b = new(memory) E.A; print(a); print(b);')
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     str(source), '--run'], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pool capacity exceeded', result.stderr)

    def test_explicit_main_demo(self):
        result = self.execute((Path(__file__).resolve().parents[1] / 'examples/main.crb').read_text(),
                              add_source=False, allow_legacy_reset=False)
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.splitlines(), [
            'destroy message=Message.Value', 'reclaim message'])

    def test_void_main_automatically_cleans_allocations(self):
        result = self.execute('fn main() { let mut memory = pool<Int>(1); '
                              'let mut data = new(memory) Int(42); print(data); }')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.splitlines(), ['destroy data=42', 'reclaim data'])

    def test_main_requires_no_parameters(self):
        self.rejected('fn main(n: Int) {}', 'main doit être sans paramètre')

    def test_main_cannot_return_allocation(self):
        self.rejected('fn main() -> <- Int {}', 'retour Void ou Int')

    def test_main_rejects_mixed_top_level_statements(self):
        self.rejected('let mut n = 1; fn main() {}', 'instructions au niveau du programme')

    def test_main_return_type_checked(self):
        self.rejected('fn main() -> Int { return; }', 'retour')

    def test_cli_builds_standalone_binary_and_preserves_exit_status(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'main.crb'
            source.write_text('fn main() -> Int { let mut memory = pool<Int>(1); '
                              'let mut value = new(memory) Int(7); print(value); return 7; }')
            binary = Path(folder) / 'nested directory' / 'demo program'
            compiler = str(Path(prototype_file).resolve())
            build = subprocess.run([sys.executable, compiler, 'build', str(source), '-o', str(binary)],
                                   capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertTrue(os.access(binary, os.X_OK))
            # Source and generated C are not required to execute the native artifact.
            source.unlink()
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout, '7\n')
            self.assertEqual(result.stderr.splitlines(), ['destroy value=7', 'reclaim value'])

    def test_cli_run_subcommand(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'main.crb'
            source.write_text('fn main() -> Int { return 3; }')
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     'run', str(source)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 3, result.stderr)

    def test_cli_build_rejection_creates_no_binary(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'invalid.crb'
            source.write_text('fn main() { let mut a = new Int(1); }')
            binary = Path(folder) / 'invalid'
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     'build', str(source), '-o', str(binary)],
                                    capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('source explicite', result.stderr)
            self.assertFalse(binary.exists())

    def test_cli_cannot_overwrite_input_with_binary(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'main.crb'
            original = 'fn main() {}'
            source.write_text(original)
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     'build', str(source), '-o', str(source)],
                                    capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_text(), original)

    def test_cli_emit_c_subcommand(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'main.crb'
            source.write_text('fn main() {}')
            output = Path(folder) / 'main.c'
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     'emit-c', str(source), '-o', str(output)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            code = output.read_text()
            self.assertIn('int main(void)', code)
            self.assertNotIn('source_reset(', code)
            self.assertNotIn('cell_drop_for_reset(', code)

    def test_cli_prototype_rejects_legacy_reset_in_all_commands(self):
        cli = Path(prototype_file).resolve()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'main.crb'
            source.write_text('fn old(p: &mut Pool<Int>) { p.reset(); } fn main() {}')
            for command in ('check', 'effects', 'emit-c', 'build', 'run'):
                with self.subTest(command=command):
                    result = subprocess.run([sys.executable, str(cli), command, str(source)],
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn('reset() retiré du prototype', result.stderr)
            legacy = subprocess.run([sys.executable, str(cli), 'check', str(source), '--legacy-reset'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(legacy.returncode, 0, legacy.stderr)
            source.write_text('fn main() { let mut p = pool<Int>(1); '
                              'let a = p.new(7); drop(-> a); let b = p.new(9); print(b); }')
            run = subprocess.run([sys.executable, str(cli), 'run', str(source)],
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
            self.assertEqual(run.stderr.splitlines(), [
                'destroy a=7', 'reclaim a', 'destroy b=9', 'reclaim b',
            ])

    def test_python_prototype_requires_explicit_legacy_reset(self):
        import crust

        source = 'let mut p = pool<Int>(1); p.reset();'
        for entry in (crust.verify_program, crust.compile_program, crust.compile_source):
            with self.subTest(entry=entry.__name__):
                with self.assertRaisesRegex(Error, r'reset\(\) retiré du prototype'):
                    entry(source)
                entry(source, allow_legacy_reset=True)
        with self.assertRaisesRegex(Error, r'reset\(\) retiré du prototype'):
            crust.Compiler().verify(Parser(source).parse())
        code = crust.compile_source('fn main() {}')
        self.assertNotIn('source_reset(', code)
        self.assertNotIn('cell_drop_for_reset(', code)

    def test_parser_distinguishes_async_functions_and_suspension_points(self):
        task, parent = Parser("""
            async fn task() -> Int { yield; return 7; }
            async fn parent() {
                let pending = task();
                let first = pending.await;
                let second = task().await;
                task().await;
                pending.await;
            }
        """).parse()
        self.assertEqual((task.op, task.args[3][0].op, parent.op), ('async_fn', 'yield', 'async_fn'))
        _, first, second, call_statement, named_statement = parent.args[3]
        self.assertEqual(first.args[1], ('await', ('name', 'pending')))
        self.assertEqual(second.args[1], ('await', ('call', 'task', [])))
        self.assertEqual((call_statement.op, named_statement.op), ('await_statement', 'await_statement'))

    def test_sync_context_rejects_suspension_even_after_async_declaration(self):
        prefix = 'async fn task() -> Int { yield; return 7; } '
        for statement, diagnostic in (
            ('yield;', 'yield exige'),
            ('{ let t = task(); let n = t.await; }', r'\.await exige'),
            ('task().await;', r'\.await exige'),
            ('let n = task().await;', r'\.await exige'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                Parser(prefix + f'fn sync() {{ {statement} }}').parse()
        with self.assertRaisesRegex(Error, 'main doit rester synchrone'):
            compile_source('async fn main() {}')


if __name__ == '__main__':
    unittest.main()
