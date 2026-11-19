"""Opaque pool call contracts, independent of the specialized backend."""
from functools import partial, update_wrapper
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import __file__ as prototype_file
from crust import Compiler, Parser, Error, PathsReturned, verify_program, compile_program

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
import test_crust


MAKE = ('fn create(mem: &mut Pool<Int>, n: Int) -> <- Int { '
        'let mut data = new(mem) Int(n); return <- data; } ')
CLEAR = 'fn clear(mem: &mut Pool<Int>) { mem.reset(); } '
CHOOSE = ('fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
          'if n == 0 { return <- a; } return <- b; } ')
IDENTITY = 'fn forward(mut data: -> Int) -> <- Int { return <- data; } '


class ModularCallTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def opaque_caller(self, declarations, script):
        interface = verify_program(declarations)
        caller = Compiler(allow_legacy_reset=True)
        caller.contract_calls = True
        # No bodies or separate inference maps are available at all.
        caller.function_contracts = interface.function_contracts
        caller.enums = interface.enums
        nodes = Parser(script).parse()
        caller.index(nodes)
        try:
            caller.block('root', nodes)
        except PathsReturned:
            pass
        return caller

    def rejected_call(self, declarations, script, message):
        with self.assertRaisesRegex(Error, message):
            self.opaque_caller(declarations, script)

    def test_call_uses_no_body_catalog_or_inference_maps(self):
        caller = self.opaque_caller(MAKE, 'let mut memory = pool<Int>(1); '
            'let mut value = create(&mut memory, 42); print(value);')
        self.assertEqual(caller.contract_call_log, ['create'])
        self.assertEqual(caller.functions, {})
        self.assertEqual(caller.function_effects, {})
        self.assertEqual(caller.function_results, {})
        self.assertEqual(caller.function_constraints, {})
        self.assertEqual(caller.definitions, [])

    def test_each_body_is_entered_once_without_entering_callees(self):
        visits = []
        block = Compiler.block
        def track(checker, label, nodes, returns=False, bindings=None, function=None, loop_frame=None):
            if function is not None:
                visits.append((function, tuple(checker.call_stack)))
            return block(checker, label, nodes, returns, bindings, function, loop_frame)
        source = MAKE + ('fn wrap(mem: &mut Pool<Int>) -> <- Int { '
            'let mut value = create(mem, 7); return <- value; } '
            'fn main() { let mut memory = pool<Int>(1); let mut x = wrap(&mut memory); '
            'print(x); drop(-> x); let mut y = wrap(&mut memory); print(y); }')
        with patch.object(Compiler, 'block', track):
            checked = verify_program(source)
        self.assertEqual(visits, [('create', ('create',)), ('wrap', ('wrap',)), ('main', ('main',))])
        self.assertEqual(checked.body_call_contracts['wrap'], ('create',))
        self.assertEqual(checked.body_call_contracts['main'], ('wrap', 'wrap'))
        self.assertEqual(checked.definitions, [])

    def test_check_does_not_run_backend(self):
        with patch.object(Compiler, 'compile', side_effect=AssertionError('backend entered')):
            compiler = verify_program(MAKE + 'fn main() {}')
        self.assertEqual(compiler.verified_functions, {'create', 'main'})

    def test_result_provenance_rejects_future_use_after_pool_reset(self):
        self.rejected_call(MAKE + CLEAR, 'let mut mem = pool<Int>(1); let mut x = create(&mut mem, 1); '
            'clear(&mut mem); print(x);', 'reset interdit')

    def test_reset_after_last_use_allows_slot_reuse_and_runtime_cleanup_once(self):
        source = MAKE + CLEAR + ('fn main() { let mut mem = pool<Int>(1); '
            'let mut x = create(&mut mem, 42); print(x); clear(&mut mem); '
            'let mut y = create(&mut mem, 7); print(y); }')
        verify_program(source)
        result = self.execute(source)
        self.assertEqual(result.stdout, '42\n7\n')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)
        self.assertEqual(result.stderr.count('destroy data=7'), 1)

    def test_read_before_reset_is_allowed_and_later_use_rejected(self):
        declaration = ('fn read_clear(mem: &mut Pool<Int>, x: &Int) -> Int { '
                       'let mut n = *x; mem.reset(); return n; } ')
        prefix = 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(42); '
        self.opaque_caller(declaration, prefix + 'let mut n = read_clear(&mut mem, &x); print(n);')
        self.rejected_call(declaration, prefix + 'let mut n = read_clear(&mut mem, &x); '
                           'print(n); print(x);', 'reset interdit')

    def test_source_equality_and_disjointness_are_checked_from_contract(self):
        declaration = ('fn consume(mem: &mut Pool<Int>, mut x: -> Int) { mem.drop(-> x); } '
            'fn clear_read(mem: &mut Pool<Int>, x: &Int) -> Int { mem.reset(); return *x; } ')
        prefix = 'let mut a = pool<Int>(1); let mut b = pool<Int>(1); let mut x = new(a) Int(1); '
        self.rejected_call(declaration, prefix + 'consume(&mut b, -> x);', 'source de stockage')
        self.rejected_call(declaration, prefix + 'let mut n = clear_read(&mut a, &x); print(n);', 'reset interdit')
        self.opaque_caller(declaration, prefix + 'let mut n = clear_read(&mut b, &x); print(n); consume(&mut a, -> x);')

    def test_identity_result_keeps_plain_return_import_markers(self):
        self.opaque_caller(IDENTITY, 'let mut mem = pool<Int>(1); let mut data = new(mem) Int(7); '
            '{ -> data; data = forward(-> data); <- data; } print(data);')

    def test_transferred_input_name_is_not_revived_by_explicit_receiver(self):
        self.rejected_call(IDENTITY, 'let mut mem = pool<Int>(1); let mut data = new(mem) Int(7); '
            'let mut result = forward(-> data); print(result); print(data);', 'plus utilisable')

    def test_multiple_input_result_sources_protect_both_pools(self):
        prefix = ('let mut a = pool<Int>(1); let mut b = pool<Int>(1); '
                  'let mut x = new(a) Int(1); let mut y = new(b) Int(2); '
                  'let mut result = choose(-> x, -> y, 0); ')
        for memory in ('a', 'b'):
            with self.subTest(memory=memory):
                self.rejected_call(CHOOSE + CLEAR, prefix + f'clear(&mut {memory}); print(result);', 'reset interdit')
        self.opaque_caller(CHOOSE + CLEAR, prefix + 'print(result); clear(&mut a); clear(&mut b);')

    def test_multi_source_result_cannot_be_dropped_by_one_pool(self):
        self.rejected_call(CHOOSE, 'let mut a = pool<Int>(1); let mut b = pool<Int>(1); '
            'let mut x = new(a) Int(1); let mut y = new(b) Int(2); '
            'let mut result = choose(-> x, -> y, 0); a.drop(-> result);', 'source de stockage')

    def test_conditional_reset_and_returned_candidate_is_received_alive(self):
        source = ('fn pick(mem: &mut Pool<Int>, mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
                  'if n == 0 { mem.reset(); return <- a; } return <- b; } ')
        script = ('let mut a = pool<Int>(1); let mut b = pool<Int>(1); let mut x = new(a) Int(1); '
                  'let mut y = new(b) Int(2); let mut value = pick(&mut b, -> x, -> y, 0); print(value);')
        self.opaque_caller(source, script)
        for flag in (0, 1):
            result = self.execute(source + script.replace(', 0);', f', {flag});'))
            self.assertEqual(result.stdout, f'{flag + 1}\n')
            self.assertEqual(result.stderr.count('destroy '), 2)

    def test_fresh_result_after_reset_is_received_alive(self):
        declaration = ('fn replace(mem: &mut Pool<Int>) -> <- Int { mem.reset(); '
                       'let mut value = new(mem) Int(7); return <- value; } ')
        self.opaque_caller(declaration, 'let mut mem = pool<Int>(1); let mut old = new(mem) Int(1); '
            'print(old); let mut value = replace(&mut mem); print(value);')

    def test_prepared_borrow_blocks_reset_in_later_argument(self):
        declaration = ('fn effect(mem: &mut Pool<Int>) -> Int { mem.reset(); return 1; } '
                       'fn observe(x: &Int, n: Int) {} ')
        self.rejected_call(declaration, 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(7); '
            'observe(&x, effect(&mut mem));', 'reset interdit.*argument')

    def test_scalar_argument_copied_before_reset_has_no_storage_dependency(self):
        declaration = ('fn effect(mem: &mut Pool<Int>) -> Int { mem.reset(); return 1; } '
                       'fn observe(x: Int, n: Int) {} ')
        self.opaque_caller(declaration, 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(7); '
            'observe(*x, effect(&mut mem));')

    def test_pending_source_borrow_remains_exclusive(self):
        declaration = ('fn effect(mem: &mut Pool<Int>) -> Int { mem.reset(); return 1; } '
                       'fn observe(mem: &Pool<Int>, n: Int) {} ')
        self.rejected_call(declaration, 'let mut mem = pool<Int>(1); observe(&mem, effect(&mut mem));', 'aliasés')

    def test_aliasing_and_transfer_modes_are_still_checked(self):
        declaration = 'fn edit(a: &mut Int, b: &Int) {} '
        prefix = 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(1); '
        self.rejected_call(declaration, prefix + 'edit(&mut x, &x);', 'aliasés|emprunt')
        self.rejected_call(IDENTITY, prefix + 'let mut value = forward(&x); print(value);', 'mode attendu')

    def test_read_parameter_stays_usable_after_temporary_reborrow(self):
        declaration = 'fn read(x: &Int) -> Int { return *x; } '
        verify_program(declaration + 'fn wrapper(x: &Int) -> Int { let mut n = read(x); print(x); return n; }')

    def test_conditional_reset_invalidates_external_value_even_if_condition_literal(self):
        declaration = 'fn maybe(mem: &mut Pool<Int>) { if false { mem.reset(); } } '
        self.rejected_call(declaration, 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(7); '
            'maybe(&mut mem); print(x);', 'reset interdit')

    def test_owned_parameter_is_consumed_even_when_unused_by_callee(self):
        self.rejected_call('fn consume(mut x: -> Int) {} ', 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(7); '
            'consume(-> x); print(x);', 'plus utilisable')

    def test_loop_checks_contract_effect_on_next_iteration(self):
        declaration = 'fn read(x: &Int) -> Int { return *x; } ' + CLEAR
        self.rejected_call(declaration, 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(7); '
            'loop { let mut n = read(&x); print(n); clear(&mut mem); continue; }', 'reset interdit|plus utilisable|boucle')

    def test_loop_with_break_after_last_use_is_allowed(self):
        self.opaque_caller(CLEAR, 'let mut mem = pool<Int>(1); let mut x = new(mem) Int(7); '
            'loop { print(x); clear(&mut mem); break; }')

    def test_nonreturning_call_has_no_continuing_path(self):
        caller = self.opaque_caller('fn forever(mut x: -> Int) { loop {} } ',
            'let mut mem = pool<Int>(1); let mut x = new(mem) Int(7); forever(-> x); print(x);')
        self.assertEqual(caller.contract_call_log, ['forever'])

    def test_enum_pool_contracts_keep_type_and_provenance(self):
        declaration = ('enum E { A { n: Int }, B {} } '
            'fn make(mem: &mut Pool<E>) -> <- E { let mut x = new(mem) E.A { n: 7 }; return <- x; } ')
        self.opaque_caller(declaration, 'let mut mem = pool<E>(1); let mut x = make(&mut mem); print(x);')
        self.rejected_call(declaration, 'let mut mem = pool<Int>(1); let mut x = make(&mut mem); print(x);', 'attend une source')

    def test_generic_interface_allocation_requirements_are_still_checked(self):
        declaration = ('enum E { A {} } fn make(mem: &mut Allocator) -> <- E { '
                       'let mut x = new(mem) E.A {}; return <- x; } ')
        self.opaque_caller(declaration, 'let mut mem = pool<E>(1); let mut x = make(&mut mem); print(x);')
        self.rejected_call(declaration, 'let mut mem = pool<Int>(1); let mut x = make(&mut mem); print(x);', 'incompatible')

    def test_modular_and_backend_acceptance_agree_for_pool_paths(self):
        for flag in (0, 1):
            source = MAKE + CHOOSE + ('fn main() { let mut a = pool<Int>(1); let mut b = pool<Int>(1); '
                'let mut x = create(&mut a, 42); let mut y = create(&mut b, 7); '
                f'let mut chosen = choose(-> x, -> y, {flag}); print(chosen); }}')
            verify_program(source)
            compiler, code = compile_program(source)
            self.assertEqual(compiler.verified_functions, {'create', 'choose', 'main'})
            self.assertNotIn('contract_result_', code)
            result = self.execute(source)
            self.assertEqual(result.stdout, '42\n' if flag == 0 else '7\n')
            self.assertEqual(result.stderr.count('destroy '), 2)

    def test_cli_check_without_c_compiler_and_rejection(self):
        cli = Path(prototype_file).resolve()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'program.crb'
            path.write_text(MAKE + 'fn main() { let mut mem = pool<Int>(1); let mut x = create(&mut mem, 7); print(x); }')
            result = subprocess.run([sys.executable, str(cli), 'check', str(path)], capture_output=True, text=True,
                                    env={'PATH': ''}, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('vérification réussie', result.stdout)
            path.write_text('fn bad(mut x: -> Int) { drop(-> x); print(x); }')
            result = subprocess.run([sys.executable, str(cli), 'check', str(path)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn('plus utilisable', result.stderr)

    def test_cli_effects_does_not_need_backend(self):
        cli = Path(prototype_file).resolve()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'program.crb'
            path.write_text(MAKE)
            result = subprocess.run([sys.executable, str(cli), 'effects', str(path)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['create']['allocations'], [{'source': 'mem', 'type': 'Int'}])


if __name__ == '__main__':
    unittest.main()
