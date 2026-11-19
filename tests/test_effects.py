"""Symbolic source effects and their use by specialized calls/C cleanup."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import __file__ as prototype_file
from crust import Compiler, Parser, Error
import test_crust


class EffectTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def analyze(self, source):
        compiler = Compiler(allow_legacy_reset=True)
        code = compiler.compile(Parser(source).parse())
        return compiler, code

    def test_direct_and_transitive_effects_in_unused_functions(self):
        compiler, _ = self.analyze('fn clear(mem: &mut Allocator) { mem.reset(); } '
            'fn relay(mem: &mut Allocator) { clear(mem); } '
            'fn make(mem: &mut Allocator) -> <- Int { let mut a = new(mem) Int(42); return <- a; }')
        self.assertEqual(compiler.function_effects['clear'].resets, {0})
        self.assertEqual(compiler.function_effects['relay'].resets, {0})
        make = compiler.function_effects['make']
        self.assertEqual(make.resets, set())
        self.assertEqual(make.allocations, {(0, 'Int')})
        self.assertTrue(make.may_return)

    def test_parameter_substitution_tracks_reordered_source_arguments(self):
        compiler, _ = self.analyze('fn clear(a: &mut Allocator, b: &mut Allocator) { b.reset(); } '
            'fn relay(n: Int, first: &mut Allocator, second: &mut Allocator) { clear(second, first); }')
        summary = compiler.function_effects['relay']
        self.assertEqual(summary.resets, {1})
        self.assertEqual(summary.describe(compiler.functions['relay'].args[1])['resets'], ['first'])

    def test_allocation_requirements_propagate_through_wrappers(self):
        compiler, _ = self.analyze('fn make(mem: &mut Allocator) -> <- Int { let mut a = new(mem) Int(7); return <- a; } '
            'fn wrap(a: &mut Allocator, b: &mut Allocator) { let mut v = make(b); print(v); }')
        self.assertEqual(compiler.function_effects['wrap'].allocations, {(1, 'Int')})
        self.assertEqual(compiler.function_effects['wrap'].resets, set())

    def test_private_sources_and_shadowed_names_do_not_escape_summary(self):
        compiler, _ = self.analyze('fn clear(mem: &mut Allocator) { mem.reset(); } '
            'fn wrap(mem: &mut Allocator) { { let mut mem = pool<Int>(1); '
            'let mut a = new(mem) Int(1); print(a); clear(&mut mem); } '
            'let mut a = new(mem) Int(2); print(a); }')
        summary = compiler.function_effects['wrap']
        self.assertEqual(summary.resets, set())
        self.assertEqual(summary.allocations, {(0, 'Int')})

    def test_branches_are_conservative_including_literal_conditions(self):
        compiler, _ = self.analyze('fn work(a: &mut Allocator, b: &mut Allocator) { '
            'if false { a.reset(); } else { let mut x = new(b) Int(1); print(x); } }')
        self.assertEqual(compiler.function_effects['work'].resets, {0})
        self.assertEqual(compiler.function_effects['work'].allocations, {(1, 'Int')})

    def test_unreachable_effects_after_return_break_and_continue_are_excluded(self):
        for prefix in ('return;', 'loop { break; mem.reset(); } return;',
                       'loop { continue; mem.reset(); }'):
            with self.subTest(prefix=prefix):
                compiler, _ = self.analyze('fn work(mem: &mut Allocator) { ' + prefix + ' mem.reset(); }')
                self.assertEqual(compiler.function_effects['work'].resets, set())
        self.assertFalse(compiler.function_effects['work'].may_return)

    def test_diverging_subcalls_stop_later_effects(self):
        compiler, _ = self.analyze('fn never() -> Int { loop {} } '
            'fn work(mem: &mut Allocator) { let mut n = never(); mem.reset(); } '
            'fn outer(mem: &mut Allocator) { work(mem); mem.reset(); }')
        for name in ('never', 'work', 'outer'):
            with self.subTest(name=name):
                self.assertFalse(compiler.function_effects[name].may_return)
                self.assertEqual(compiler.function_effects[name].resets, set())

    def test_loop_and_while_condition_effects_are_collected(self):
        compiler, _ = self.analyze('fn probe(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
            'fn work(a: &mut Allocator, b: &mut Allocator) { '
            'while probe(a) == 0 { let mut x = new(b) Int(1); print(x); break; } } '
            'fn forever(mem: &mut Allocator) { loop { mem.reset(); continue; } }')
        summary = compiler.function_effects['work']
        self.assertEqual(summary.resets, {0})
        self.assertEqual(summary.allocations, {(1, 'Int')})
        self.assertTrue(summary.may_return)
        self.assertEqual(compiler.function_effects['forever'].resets, {0})
        self.assertFalse(compiler.function_effects['forever'].may_return)

    def test_nested_argument_and_initializer_effects(self):
        compiler, _ = self.analyze('fn count(mem: &mut Allocator) -> Int { mem.reset(); return 7; } '
            'fn take(n: Int) {} fn work(a: &mut Allocator, b: &mut Allocator) { '
            'take(count(a)); let mut value = new(b) Int(count(a)); print(value); }')
        summary = compiler.function_effects['work']
        self.assertEqual(summary.resets, {0})
        self.assertEqual(summary.allocations, {(1, 'Int')})

    def test_enum_field_effects_and_type_requirements(self):
        compiler, _ = self.analyze('enum E { A { n: Int } } '
            'fn count(mem: &mut Allocator) -> Int { mem.reset(); return 7; } '
            'fn make(pool: &mut Pool<E>, temps: &mut Allocator) -> <- E { '
            'let mut value = new(pool) E.A { n: count(temps) }; return <- value; }')
        summary = compiler.function_effects['make']
        self.assertEqual(summary.resets, {1})
        self.assertEqual(summary.allocations, {(0, 'E')})

    def test_early_argument_exit_excludes_unreached_callee_effects(self):
        compiler, _ = self.analyze('fn clear(mem: &mut Allocator, mut n: -> Int) { mem.reset(); } '
            'fn work(mem: &mut Allocator) { clear(mem, -> { return; }); }')
        self.assertEqual(compiler.function_effects['work'].resets, set())
        self.assertTrue(compiler.function_effects['work'].may_return)

    def test_readonly_source_effects_are_rejected_even_when_unused(self):
        for operation in ('mem.reset();', 'let mut x = new(mem) Int(7); print(x);', 'mem.drop(-> data);'):
            with self.subTest(operation=operation), self.assertRaisesRegex(Error, 'emprunt mutable'):
                self.analyze('fn wrong(mem: &Allocator, mut data: -> Int) { ' + operation + ' }')
        with self.assertRaisesRegex(Error, 'emprunt mutable'):
            self.analyze('fn clear(mem: &mut Allocator) { mem.reset(); } '
                         'fn wrong(mem: &Allocator) { clear(mem); }')

    def test_source_drop_does_not_mean_collective_reset(self):
        compiler, _ = self.analyze('fn consume(mem: &mut Allocator, mut data: -> Int) { mem.drop(-> data); }')
        summary = compiler.function_effects['consume']
        self.assertEqual(summary.resets, set())
        self.assertEqual(summary.allocations, set())

    def test_unknown_subcalls_and_recursion_cannot_have_silent_empty_summaries(self):
        for source, message in (
            ('fn unused(mem: &mut Allocator) { missing(mem); }', 'fonction inconnue'),
            ('fn unused() { let mut value = new(memory) Int(7); print(value); }', "inconnue 'memory'"),
            ('fn unused(n: Int) { n.reset(); }', 'pas une source'),
            ('fn unused() { unused(); }', 'récursion'),
            ('fn a() { b(); } fn b() { a(); }', 'récursion')):
            with self.subTest(source=source), self.assertRaisesRegex(Error, message):
                self.analyze(source)

    def test_allocate_only_calls_keep_existing_borrow_and_omit_cleanup_captures(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(2)'):
            with self.subTest(factory=factory):
                source = ('fn make(mem: &mut Allocator) -> <- Int { '
                    'let mut fresh = new(mem) Int(20); return <- fresh; } '
                    'let mut memory = ' + factory + '; let mut old = new(memory) Int(10); let mut view = &old; '
                    'let mut result = make(&mut memory); print(view); print(result);')
                _, code = self.analyze(source)
                self.assertNotIn('cleanup', code)
                result = self.execute(source)
                self.assertEqual(result.stdout, '10\n20\n')
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy fresh=20', 'destroy old=10'])

    def test_transitive_reset_captures_only_the_affected_source(self):
        source = ('fn clear(a: &mut Allocator, b: &mut Allocator) { b.reset(); } '
            'fn relay(first: &mut Allocator, second: &mut Allocator) { clear(second, first); } '
            'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
            'let mut a = new(memory) Int(10); let mut b = new(other) Int(20); '
            'print(a); '
            'relay(&mut memory, &mut other); print(b); other.reset();')
        compiler, code = self.analyze(source)
        self.assertEqual(compiler.function_effects['relay'].resets, {0})
        self.assertIn('cleanup', code)
        result = self.execute(source)
        self.assertEqual(result.stdout, '10\n20\n')
        self.assertEqual(result.stderr.count('destroy a=10'), 1)
        self.assertEqual(result.stderr.count('destroy b=20'), 1)

    def test_transitive_effect_still_protects_future_borrow(self):
        self.rejected('fn clear(mem: &mut Allocator) { mem.reset(); } '
            'fn relay(mem: &mut Allocator) { clear(mem); } '
            'let mut data = new(memory) Int(42); let mut view = &data; relay(&mut memory); print(view);', 'reset interdit')

    def test_local_source_effects_still_execute_and_cleanup(self):
        result = self.execute('fn clear(mem: &mut Allocator) { mem.reset(); } '
            'fn work(mem: &mut Allocator) { let mut private = pool<Int>(1); '
            'let mut local = new(private) Int(7); print(local); clear(&mut private); '
            'let mut external = new(mem) Int(42); print(external); } work(&mut memory);')
        self.assertEqual(result.stdout, '7\n42\n')
        self.assertEqual(result.stderr.count('destroy local=7'), 1)
        self.assertEqual(result.stderr.count('destroy external=42'), 1)

    def test_allocation_requirement_rejects_incompatible_concrete_pool(self):
        self.rejected('enum E { A } fn allocate(mem: &mut Allocator) { '
            'let mut value = new(mem) Int(7); print(value); } '
            'let mut memory = pool<E>(1); allocate(&mut memory);', 'pool<E> incompatible')

    def test_effects_cli_exports_json_without_running_program(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'effects.crb'
            output = Path(directory) / 'effects.json'
            source.write_text('fn clear(mem: &mut Allocator) { mem.reset(); } '
                              'fn main() { loop {} }')
            command = [sys.executable, str(Path(prototype_file).resolve()),
                       'effects', str(source), '--legacy-reset']
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['clear']['resets'], ['mem'])
            self.assertFalse(report['main']['may_return'])
            result = subprocess.run(command + ['-o', str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text()), report)


if __name__ == '__main__':
    unittest.main()
