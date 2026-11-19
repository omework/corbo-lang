"""P8/P9/B4/B4b/B4e: independent and compositional pool-type obligations."""
from functools import partial, update_wrapper
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import __file__ as prototype_file
from crust import Compiler, Error, Parser, PathsReturned, verify_program, compile_program

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
from pool_requirement_model import generate_graph, obligations, render_graph, render_caller
import test_crust


ENUM = 'enum Message { Empty {}, Full { code: Int } } '
LEAF = 'fn inspect(p: &Pool<Int>) {} '
RELAY = LEAF + 'fn relay(p: &Allocator) { inspect(p); } '
BAD = ENUM + RELAY + 'fn main() { let mut p = pool<Message>(1); relay(&p); }'


class PoolRequirementTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def requirements(self, source, name):
        return verify_program(source).function_contracts[name].effects.pool_requirements

    def rejected_check(self, source, message='Pool<Int>|incompatible'):
        with self.assertRaisesRegex(Error, message):
            verify_program(source)

    def test_original_counterexample_rejected_without_backend(self):
        self.rejected_check(BAD)

    def test_minimally_different_correct_pool_accepted_and_executed(self):
        source = BAD.replace('let mut p = pool<Message>(1)', 'let mut p = pool<Int>(1)')
        verify_program(source)
        result = self.execute(source)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')

    def test_unused_typed_signature_requires_pool_even_with_empty_body(self):
        for mode in ('&', '&mut '):
            with self.subTest(mode=mode):
                source = f'fn empty(p: {mode}Pool<Int>) {{}}'
                self.assertEqual(self.requirements(source, 'empty'), {(0, 'Int')})

    def test_generic_readonly_relay_retains_requirement_without_allocation(self):
        checked = verify_program(RELAY)
        self.assertEqual(checked.function_effects['relay'].pool_requirements, {(0, 'Int')})
        self.assertEqual(checked.function_effects['relay'].allocations, set())
        self.assertEqual(checked.function_effects['relay'].resets, set())

    def test_multilevel_parameter_reordering(self):
        source = RELAY + ('fn middle(a: &Allocator, b: &Allocator) { relay(b); } '
                         'fn outer(n: Int, first: &Allocator, second: &Allocator) { middle(second, first); }')
        self.assertEqual(self.requirements(source, 'middle'), {(1, 'Int')})
        self.assertEqual(self.requirements(source, 'outer'), {(1, 'Int')})

    def test_unrelated_parameter_is_not_constrained(self):
        source = ENUM + LEAF + ('fn relay(a: &Allocator, b: &Allocator) { inspect(b); } '
            'fn main() { let mut a = pool<Message>(1); let mut b = pool<Int>(1); relay(&a, &b); }')
        self.assertEqual(self.requirements(source, 'relay'), {(1, 'Int')})

    def test_heap_or_datastack_cannot_satisfy_pool_requirement(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Message>(1)'):
            with self.subTest(factory=factory):
                self.rejected_check(ENUM + RELAY + f'fn main() {{ let mut p = {factory}; relay(&p); }}')

    def test_local_shadow_does_not_constrain_external_source(self):
        source = ENUM + LEAF + ('fn relay(p: &Allocator) { { let mut p = pool<Int>(1); inspect(&p); } } '
                               'fn main() { let mut p = pool<Message>(1); relay(&p); }')
        self.assertEqual(self.requirements(source, 'relay'), set())

    def test_wrong_local_pool_rejected_in_unused_body(self):
        self.rejected_check(ENUM + LEAF + 'fn unused() { let mut p = pool<Message>(1); inspect(&p); }')

    def test_incompatible_requirements_in_same_unused_body_rejected(self):
        self.rejected_check(ENUM + LEAF + 'fn message(p: &Pool<Message>) {} '
            'fn impossible(p: &Allocator) { inspect(p); message(p); }')

    def test_literal_branches_do_not_hide_incompatible_requirements(self):
        self.rejected_check(ENUM + LEAF + 'fn message(p: &Pool<Message>) {} '
            'fn impossible(p: &Allocator) { if false { inspect(p); } else { message(p); } }')

    def test_unreachable_call_after_return_adds_no_requirement(self):
        source = ENUM + LEAF + ('fn relay(p: &Allocator) { return; inspect(p); } '
                               'fn main() { let mut p = pool<Message>(1); relay(&p); }')
        self.assertEqual(self.requirements(source, 'relay'), set())

    def test_while_condition_and_nested_argument_propagate_requirements(self):
        declaration = 'fn probe(p: &Pool<Int>) -> Int { return 0; } fn take(n: Int) {} '
        for body in ('while probe(p) == 0 { break; }', 'take(probe(p));',
                     'loop { take(probe(p)); continue; }'):
            with self.subTest(body=body):
                self.assertEqual(self.requirements(declaration + f'fn relay(p: &Allocator) {{ {body} }}',
                                                   'relay'), {(0, 'Int')})

    def test_diverging_callee_still_requires_typed_input(self):
        source = 'fn forever(p: &Pool<Int>) { loop {} } fn relay(p: &Allocator) { forever(p); }'
        self.assertEqual(self.requirements(source, 'relay'), {(0, 'Int')})
        self.rejected_check(ENUM + source + 'fn main() { let mut p = pool<Message>(1); relay(&p); }')

    def test_int_allocation_does_not_imply_pool_requirement(self):
        declaration = 'fn make(p: &mut Allocator) -> <- Int { let mut x = new(p) Int(7); return <- x; } '
        self.assertEqual(self.requirements(declaration, 'make'), set())
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(1)'):
            verify_program(declaration + f'fn main() {{ let mut p = {factory}; let mut x = make(&mut p); print(x); }}')

    def test_enum_allocation_does_imply_pool_requirement(self):
        declaration = ENUM + ('fn make(p: &mut Allocator) -> <- Message { '
                               'let mut x = new(p) Message.Empty {}; return <- x; } ')
        self.assertEqual(self.requirements(declaration, 'make'), {(0, 'Message')})

    def test_pool_requirement_conflicts_with_different_allocation_type_in_either_order(self):
        declaration = ENUM + 'fn message(p: &Pool<Message>) {} '
        for body in ('message(p); let mut x = new(p) Int(1);',
                     'let mut x = new(p) Int(1); message(p);'):
            with self.subTest(body=body):
                self.rejected_check(declaration + f'fn impossible(p: &mut Allocator) {{ {body} }}')

    def test_required_pool_type_interacts_with_source_equality_for_drop(self):
        declaration = ENUM + LEAF + ('fn impossible(p: &mut Allocator, mut x: -> Message) { '
                                     'inspect(p); p.drop(-> x); }')
        self.rejected_check(declaration)

    def test_mutability_is_not_relaxed_by_matching_pool_type(self):
        self.rejected_check('fn clear(p: &mut Pool<Int>) { p.reset(); } '
                           'fn wrong(p: &Allocator) { clear(p); }', 'emprunt mutable')

    def test_opaque_contract_checks_without_body_catalog_or_inference_maps(self):
        interface = verify_program(RELAY)
        checker = Compiler(allow_legacy_reset=True)
        checker.contract_calls = True
        checker.function_contracts = interface.function_contracts
        nodes = Parser('let mut p = pool<Int>(1); relay(&p);').parse()
        checker.index(nodes)
        checker.block('root', nodes)
        self.assertEqual(checker.contract_call_log, ['relay'])
        self.assertEqual(checker.functions, {})
        self.assertEqual(checker.function_effects, {})
        wrong = Parser('let mut p = stack(65536); relay(&p);').parse()
        checker = Compiler(allow_legacy_reset=True)
        checker.contract_calls = True
        checker.function_contracts = interface.function_contracts
        checker.index(wrong)
        with self.assertRaisesRegex(Error, 'Pool<Int>'):
            checker.block('root', wrong)

    def test_generated_call_graphs_against_independent_route_model(self):
        valid, invalid = 0, 0
        for seed in range(40):
            declarations, calls = generate_graph(seed)
            expected = obligations(declarations, calls)
            source = render_graph(declarations, calls)
            with self.subTest(seed=seed):
                if any(len(types) > 1 for types in expected.values()):
                    self.rejected_check(source)
                    invalid += 1
                    continue
                checked = verify_program(source)
                for function in calls:
                    predicted = {(parameter, typ) for parameter in range(3)
                                 for typ in expected[function, parameter]}
                    self.assertEqual(checked.function_contracts[f'f{function}'].effects.pool_requirements, predicted)
                types = [next(iter(expected[6, p]), 'Int') for p in range(3)]
                verify_program(source + render_caller(types))
                valid += 1
                affected = next(p for p in range(3) if expected[6, p])
                types[affected] = 'Message' if types[affected] == 'Int' else 'Int'
                self.rejected_check(source + render_caller(types))
                invalid += 1
        self.assertEqual((valid, invalid), (20, 40))

    def test_identity_reuse_and_reset_trace_remain_unchanged(self):
        source = LEAF + ('fn relay(p: &Allocator, mut x: -> Int) -> <- Int { inspect(p); return <- x; } '
            'fn main() { let mut p = pool<Int>(2); let mut a = new(p) Int(1); let mut b = new(p) Int(2); '
            'address(a); drop(-> a); let mut c = new(p) Int(3); address(c); '
            'let mut result = relay(&p, -> b); print(c); print(result); p.reset(); }')
        result = self.execute(source)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[2:], ['3', '2'])
        self.assertEqual([line for line in result.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy a=1', 'destroy b=2', 'destroy c=3'])

    def test_effects_json_exports_requirements_without_claiming_allocation(self):
        cli = Path(prototype_file).resolve()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'requirements.crb'
            path.write_text(RELAY)
            result = subprocess.run([sys.executable, str(cli), 'effects', str(path)], capture_output=True,
                                    text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)['relay']
            self.assertEqual(summary['pool_requirements'], [{'source': 'p', 'type': 'Int'}])
            self.assertEqual(summary['allocations'], [])
            self.assertEqual(summary['resets'], [])


if __name__ == '__main__':
    unittest.main()
