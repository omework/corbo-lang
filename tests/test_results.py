"""Symbolic result contracts and their concrete identity/provenance checks."""
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
from crust import Compiler, Parser, Error, compile_program, compile_source

# These regressions exercise the historical reset profile.
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
from effects import EffectAnalyzer
from results import FunctionResult, ResultAnalyzer, ResultCandidate, SourceOrigin
import test_crust


MAKE = ('fn make(memory: &mut Allocator) -> <- Int { '
        'let mut data = new(memory) Int(42); return <- data; } ')
IDENTITY = ('fn forward(mut data: -> Int, n: Int) -> <- Int { '
            'let mut selected = if n == 0 { -> data; <- data } else { -> data; <- data }; '
            'return <- selected; } ')
CHOOSE = ('fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
          'if n == 0 { return <- a; } return <- b; } ')


class ResultTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def test_handle_write_contract_preserves_alternatives_across_a_relay(self):
        source = """
            fn swap(h: &mut A<Int>, b: -> A<Int>, q: &mut Pool<Int>, n: Int) {
                if n == 0 { return; }
                let r = &mut *h;
                if n == 1 { *r = <- b; return; }
                *r = <- q.new(3);
            }
            fn relay(h: &mut A<Int>, b: -> A<Int>, q: &mut Pool<Int>, n: Int) {
                swap(h, -> b, q, n);
            }
        """
        functions = {node.args[0]: node for node in Parser(source).parse()}
        effects = EffectAnalyzer(functions, {}, Error).infer_all()
        summaries = ResultAnalyzer(functions, effects, Error).infer_all()
        expected = {
            ResultCandidate('parameter', 0),
            ResultCandidate('parameter', 1),
            ResultCandidate('fresh', source=SourceOrigin('source_parameter', 2)),
        }
        for name in ('swap', 'relay'):
            with self.subTest(name=name):
                ((receiver, candidates),) = summaries[name].handle_writes
                self.assertEqual(receiver, 0)
                self.assertEqual(set(candidates), expected)

    def test_handle_write_contract_rejects_a_callee_local_pool(self):
        source = """
            fn swap(h: &mut A<Int>) {
                let mut local = pool<Int>(1);
                *h = <- local.new(3);
            }
        """
        functions = {node.args[0]: node for node in Parser(source).parse()}
        effects = EffectAnalyzer(functions, {}, Error).infer_all()
        with self.assertRaisesRegex(Error, 'provenance non durable'):
            ResultAnalyzer(functions, effects, Error).infer_all()

    def test_fresh_result_is_inferred_without_any_call(self):
        compiler, _ = compile_program(MAKE)
        summary = compiler.function_results['make']
        self.assertEqual(summary.mode, 'owned')
        self.assertEqual(summary.typ, 'Int')
        self.assertEqual(summary.candidates, {ResultCandidate('fresh', source=SourceOrigin('source_parameter', 0))})
        self.assertIsNone(summary.same_parameter)

    def test_same_input_is_inferred_through_if_expression(self):
        compiler, _ = compile_program(IDENTITY)
        summary = compiler.function_results['forward']
        self.assertEqual(summary.same_parameter, 0)
        self.assertEqual(summary.candidates, {ResultCandidate('parameter', 0)})

    def test_input_selection_is_not_a_same_identity_guarantee(self):
        compiler, _ = compile_program(CHOOSE)
        summary = compiler.function_results['choose']
        self.assertEqual(summary.candidates, {ResultCandidate('parameter', 0), ResultCandidate('parameter', 1)})
        self.assertIsNone(summary.same_parameter)

    def test_nested_fresh_result_substitutes_source_parameter(self):
        compiler, _ = compile_program(MAKE + 'fn wrap(n: Int, mem: &mut Allocator) -> <- Int { '
            'let mut value = make(mem); return <- value; }')
        self.assertEqual(compiler.function_results['wrap'].candidates,
                         {ResultCandidate('fresh', source=SourceOrigin('source_parameter', 1))})

    def test_nested_parameter_selection_substitutes_owned_arguments(self):
        compiler, _ = compile_program(CHOOSE + 'fn wrap(n: Int, mut first: -> Int, mut second: -> Int) -> <- Int { '
            'let mut result = choose(-> second, -> first, n); return <- result; }')
        self.assertEqual(compiler.function_results['wrap'].candidates,
                         {ResultCandidate('parameter', 1), ResultCandidate('parameter', 2)})

    def test_mixed_fresh_and_input_candidates_keep_their_distinction(self):
        compiler, _ = compile_program('fn replace(mut data: -> Int, mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 0 { return <- data; } let mut fresh = new(mem) Int(7); return <- fresh; }')
        self.assertEqual(compiler.function_results['replace'].candidates,
            {ResultCandidate('parameter', 0), ResultCandidate('fresh', source=SourceOrigin('source_parameter', 1))})

    def test_owned_expression_argument_can_be_fresh_relative_to_wrapper(self):
        compiler, _ = compile_program(IDENTITY + 'fn wrap(mem: &mut Allocator) -> <- Int { '
            'let mut result = forward(-> new(mem) Int(7), 0); return <- result; }')
        self.assertEqual(compiler.function_results['wrap'].candidates,
                         {ResultCandidate('fresh', source=SourceOrigin('source_parameter', 0))})

    def test_same_source_different_fresh_sites_do_not_claim_an_input_identity(self):
        compiler, _ = compile_program('fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 0 { let mut a = new(mem) Int(1); return <- a; } '
            'let mut b = new(mem) Int(2); return <- b; }')
        summary = compiler.function_results['make']
        self.assertIsNone(summary.same_parameter)
        self.assertEqual(len(summary.candidates), 1)
        self.assertEqual(next(iter(summary.candidates)).kind, 'fresh')

    def test_local_source_escape_is_rejected_without_a_call(self):
        with self.assertRaisesRegex(Error, 'source.*ne survit pas'):
            compile_program('fn wrong() -> <- Int { let mut local = pool<Int>(1); '
                            'let mut value = new(local) Int(7); return <- value; }')
        with self.assertRaisesRegex(Error, 'source.*ne survit pas'):
            compile_program(MAKE + 'fn wrong() -> <- Int { let mut local = pool<Int>(1); '
                            'let mut value = make(&mut local); return <- value; }')

    def test_missing_and_incompatible_owned_results_are_rejected_without_call(self):
        for source, message in (
            ('fn wrong() -> <- Int {}', 'retour'),
            ('fn wrong() -> <- Int { return 7; }', 'retour'),
            ('fn wrong(data: &Int) -> <- Int { return <- data; }', 'allocation explicite'),
            ('enum E { A } fn wrong(mut data: -> E) -> <- Int { return <- data; }', 'allocation Int attendue')):
            with self.subTest(source=source), self.assertRaisesRegex(Error, message):
                compile_program(source)

    def test_diverging_owned_function_has_no_fabricated_candidate(self):
        compiler, _ = compile_program('fn never() -> <- Int { loop {} } '
            'fn wrap() -> <- Int { let mut result = never(); return <- result; }')
        for name in ('never', 'wrap'):
            self.assertFalse(compiler.function_effects[name].may_return)
            self.assertEqual(compiler.function_results[name].candidates, set())

    def test_early_return_in_later_argument_supplies_actual_result(self):
        compiler, _ = compile_program('fn consume(mut a: -> Int, mut b: -> Int) {} '
            'fn work(mem: &mut Allocator) -> <- Int { let mut result = new(mem) Int(42); '
            'consume(-> new(mem) Int(1), -> { return <- result; }); }')
        self.assertEqual(compiler.function_results['work'].candidates,
                         {ResultCandidate('fresh', source=SourceOrigin('source_parameter', 0))})

    def test_same_input_survives_nested_imports_and_keeps_address(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(1)'):
            for flag in (0, 1):
                with self.subTest(factory=factory, flag=flag):
                    result = self.execute(IDENTITY + 'let mut memory = ' + factory + '; '
                        'let mut data = new(memory) Int(42); address(data); { -> data; { -> data; '
                        'data = forward(-> data, ' + str(flag) + '); <- data; } <- data; } '
                        'address(data); print(data); drop(-> data); memory.reset();')
                    lines = result.stdout.splitlines()
                    self.assertEqual(lines[0], lines[1])
                    self.assertEqual(lines[2:], ['42'])
                    self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_same_input_preserves_pending_export_and_reception_order(self):
        result = self.execute(IDENTITY + 'let mut data = new(memory) Int(42); '
            'let mut other = new(memory) Int(7); print(other); { -> data; <- data; data = forward(-> data, 0); print(data); }')
        self.assertEqual(result.stdout, '7\n42\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=42', 'destroy other=7'])

    def test_same_input_after_phi_roundtrip_does_not_reactivate_an_old_receiver(self):
        self.rejected(IDENTITY + 'let mut data = new(memory) Int(42); '
            'let mut result = { -> data; let mut selected = forward(-> data, 0); <- selected }; '
            'print(data); print(result);', 'plus utilisable')

    def test_ended_borrow_variable_can_be_reassigned_after_identity_return(self):
        identity = 'fn identity(mut data: -> Int) -> <- Int { return <- data; } '
        result = self.execute(identity + 'let mut data = new(memory) Int(42); '
            'let mut view = &data; print(view); let mut result = identity(-> data); view = &result; print(view);')
        self.assertEqual(result.stdout, '42\n42\n')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)
        self.rejected(identity + 'let mut data = new(memory) Int(42); let mut view = &data; '
                      'let mut result = identity(-> data); print(view); print(result);', 'emprunt')

    def test_source_union_survives_result_summary_wrappers_and_reset(self):
        prelude = CHOOSE + IDENTITY
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(prelude + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut a = new(memory) Int(10); let mut b = new(other) Int(20); address(a); address(b); '
                    'let mut selected = choose(-> a, -> b, ' + str(flag) + '); '
                    'let mut result = forward(-> selected, 0); address(result); print(result); memory.reset(); other.reset();')
                lines = result.stdout.splitlines()
                self.assertEqual(lines[2], lines[flag])
                self.assertEqual(result.stderr.count('destroy '), 2)
        for source in ('memory', 'other'):
            self.rejected(prelude + 'let mut other = pool<Int>(1); '
                'let mut a = new(memory) Int(10); let mut b = new(other) Int(20); '
                'let mut selected = choose(-> a, -> b, 0); let mut result = forward(-> selected, 1); '
                + source + '.reset(); print(result);', 'reset interdit')

    def test_same_identity_roundtrip_through_loop_and_continue(self):
        result = self.execute(IDENTITY + 'let mut memory = pool<Int>(1); let mut controls = allocator(); '
            'let mut state = new(controls) Int(0); let mut data = new(memory) Int(42); '
            'while *state < 2 { -> data; data = forward(-> data, *state); <- data; '
            'if *state == 0 { state.set(1); continue; } state.set(2); } print(data); memory.reset();')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_returns_inside_loop_and_while_fallback_are_joined(self):
        compiler, _ = compile_program('fn work(mut a: -> Int, mem: &mut Allocator, n: Int) -> <- Int { '
            'while n == 0 { return <- a; } let mut fresh = new(mem) Int(7); return <- fresh; }')
        self.assertEqual(compiler.function_results['work'].candidates,
                         {ResultCandidate('parameter', 0), ResultCandidate('fresh', source=SourceOrigin('source_parameter', 1))})

    def test_enum_identity_and_fresh_sources(self):
        source = ('enum E { A { n: Int }, B } '
            'fn forward(mut data: -> E, n: Int) -> <- E { let mut result = if n == 0 { -> data; <- data } '
            'else { -> data; <- data }; return <- result; } '
            'fn make(mem: &mut Pool<E>) -> <- E { let mut data = new(mem) E.A { n: 42 }; return <- data; } '
            'let mut memory = pool<E>(1); let mut data = make(&mut memory); { -> data; '
            'data = forward(-> data, 1); <- data; } print(data); memory.reset();')
        compiler, _ = compile_program(source)
        self.assertEqual(compiler.function_results['forward'].same_parameter, 0)
        result = self.execute(source)
        self.assertEqual(result.stdout, 'E.A(42)\n')
        self.assertEqual(result.stderr.count('destroy data=E.A'), 1)

    def test_slot_reuse_is_a_fresh_result_even_when_address_is_equal(self):
        source = ('fn replace(mem: &mut Allocator, mut old: -> Int) -> <- Int { '
            'drop(-> old); let mut fresh = new(mem) Int(20); return <- fresh; } '
            'let mut memory = pool<Int>(1); let mut old = new(memory) Int(10); address(old); '
            'let mut result = replace(&mut memory, -> old); address(result); print(result);')
        compiler, _ = compile_program(source)
        self.assertIsNone(compiler.function_results['replace'].same_parameter)
        result = self.execute(source)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2:], ['20'])
        self.assertEqual(result.stderr.count('destroy old=10'), 1)
        self.assertEqual(result.stderr.count('destroy fresh=20'), 1)

    def test_reassignment_from_input_to_fresh_changes_summary(self):
        compiler, _ = compile_program('fn work(mem: &mut Allocator, mut old: -> Int) -> <- Int { '
            'old = new(mem) Int(20); return <- old; }')
        self.assertEqual(compiler.function_results['work'].candidates,
                         {ResultCandidate('fresh', source=SourceOrigin('source_parameter', 0))})

    def test_incorrect_same_input_contract_is_rejected_before_emitting_runnable_c(self):
        from results import ResultAnalyzer
        real_infer = ResultAnalyzer.infer_all
        def incorrect(analyzer):
            summaries = real_infer(analyzer)
            summaries['replace'] = FunctionResult('owned', 'Int', frozenset({ResultCandidate('parameter', 1)}))
            return summaries
        with patch('crust.ResultAnalyzer.infer_all', incorrect), self.assertRaisesRegex(Error, 'résumé de résultat'):
            compile_source('fn replace(mem: &mut Allocator, mut old: -> Int) -> <- Int { '
                'drop(-> old); let mut fresh = new(mem) Int(20); return <- fresh; } '
                'let mut memory = pool<Int>(1); let mut old = new(memory) Int(10); '
                'let mut result = replace(&mut memory, -> old); print(result);')

    def test_wrong_fresh_source_cannot_hide_behind_an_allowed_input_source(self):
        from results import ResultAnalyzer
        real_infer = ResultAnalyzer.infer_all
        def incorrect(analyzer):
            summaries = real_infer(analyzer)
            summaries['work'] = FunctionResult('owned', 'Int', frozenset({
                ResultCandidate('parameter', 2), ResultCandidate('fresh', source=SourceOrigin('source_parameter', 1))}))
            return summaries
        with patch('crust.ResultAnalyzer.infer_all', incorrect), self.assertRaisesRegex(Error, 'résumé de résultat'):
            compile_source('fn work(first: &mut Allocator, second: &mut Allocator, mut old: -> Int) -> <- Int { '
                'drop(-> old); let mut fresh = new(first) Int(20); return <- fresh; } '
                'let mut memory = pool<Int>(2); let mut other = pool<Int>(1); let mut old = new(memory) Int(10); '
                'let mut result = work(&mut memory, &mut other, -> old); print(result);')

    def test_effects_cli_exposes_symbolic_result_alternatives(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'results.crb'
            source.write_text(MAKE + IDENTITY + CHOOSE)
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     'effects', str(source)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['forward']['result']['alternatives'],
                             [{'kind': 'parameter', 'parameter': 'data'}])
            self.assertEqual(report['make']['result']['alternatives'],
                             [{'kind': 'fresh', 'source': {'kind': 'parameter', 'parameter': 'memory'}}])
            self.assertEqual(len(report['choose']['result']['alternatives']), 2)


if __name__ == '__main__':
    unittest.main()
