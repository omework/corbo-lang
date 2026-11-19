"""Ordered source obligations, substitution and concrete call checks."""
from functools import partial, update_wrapper
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import __file__ as prototype_file
from crust import compile_program, Error

# These regressions exercise the historical reset profile.
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
import test_crust


AFTER = ('fn clear_then_read(mem: &mut Allocator, data: &Int) -> Int { '
         'mem.reset(); return *data; } ')
BEFORE = ('fn read_then_clear(mem: &mut Allocator, data: &Int) -> Int { '
          'let mut value = *data; mem.reset(); return value; } ')


class ConstraintTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def requirements(self, source, name):
        compiler, _ = compile_program(source)
        return compiler.function_constraints[name].requirements

    def pairs(self, requirements):
        return {(c.relation, frozenset({(c.left.kind, c.left.index), (c.right.kind, c.right.index)}))
                for c in requirements}

    def test_read_after_reset_requires_disjoint_sources(self):
        requirements = self.requirements(AFTER, 'clear_then_read')
        self.assertEqual(self.pairs(requirements),
            {('distinct', frozenset({('source_parameter', 0), ('allocation_parameter', 1)}))})

    def test_read_before_reset_has_no_disjointness_requirement(self):
        self.assertEqual(self.requirements(BEFORE, 'read_then_clear'), set())

    def test_equality_for_source_drop_and_no_equality_for_provenance_drop(self):
        source = ('fn named(mem: &mut Allocator, mut data: -> Int) { mem.drop(-> data); } '
                  'fn direct(mut data: -> Int) { drop(-> data); }')
        self.assertEqual(self.pairs(self.requirements(source, 'named')),
            {('equal', frozenset({('source_parameter', 0), ('allocation_parameter', 1)}))})
        self.assertEqual(self.requirements(source, 'direct'), set())

    def test_same_source_read_before_reset_is_allowed_for_all_backends(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(1)'):
            with self.subTest(factory=factory):
                result = self.execute(BEFORE + 'let mut memory = ' + factory + '; '
                    'let mut data = new(memory) Int(42); let mut value = read_then_clear(&mut memory, &data); print(value);')
                self.assertEqual(result.stdout, '42\n')
                self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_same_source_read_after_reset_is_rejected(self):
        self.rejected(AFTER + 'let mut data = new(memory) Int(42); '
                      'let mut value = clear_then_read(&mut memory, &data); print(value);', 'reset interdit')

    def test_other_source_read_after_reset_is_allowed(self):
        result = self.execute(AFTER + 'let mut other = pool<Int>(1); let mut old = new(memory) Int(7); print(old); '
            'let mut data = new(other) Int(42); let mut value = clear_then_read(&mut memory, &data); print(value);')
        self.assertEqual(result.stdout, '7\n42\n')
        self.assertEqual(result.stderr.count('destroy old=7'), 1)
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_transitive_constraints_substitute_reordered_parameters(self):
        source = AFTER + 'fn wrap(data: &Int, other: &mut Allocator) -> Int { '
        source += 'let mut value = clear_then_read(other, data); return value; }'
        self.assertEqual(self.pairs(self.requirements(source, 'wrap')),
            {('distinct', frozenset({('source_parameter', 1), ('allocation_parameter', 0)}))})

    def test_equality_is_checked_against_all_possible_provenances(self):
        self.rejected('fn consume(mem: &mut Allocator, mut data: -> Int) { mem.drop(-> data); } '
            'let mut other = pool<Int>(1); let mut result = if true { let mut a = new(memory) Int(1); <- a } '
            'else { let mut b = new(other) Int(2); <- b }; consume(&mut memory, -> result);', 'source de stockage')
        result = self.execute('fn consume(mem: &mut Allocator, mut data: -> Int) { mem.drop(-> data); } '
            'let mut result = if true { let mut a = new(memory) Int(1); <- a } '
            'else { let mut b = new(memory) Int(2); <- b }; consume(&mut memory, -> result);')
        self.assertEqual(result.stderr.count('destroy '), 1)

    def test_disjointness_rejects_any_overlapping_possible_source(self):
        self.rejected(AFTER + 'let mut other = pool<Int>(1); '
            'let mut result = if false { let mut a = new(memory) Int(1); <- a } else { let mut b = new(other) Int(2); <- b }; '
            'let mut value = clear_then_read(&mut memory, &result); print(value);', 'reset interdit')
        result = self.execute(AFTER + 'let mut other = pool<Int>(1); let mut third = pool<Int>(1); '
            'let mut result = if false { let mut a = new(memory) Int(1); <- a } else { let mut b = new(other) Int(2); <- b }; '
            'let mut value = clear_then_read(&mut third, &result); print(value);')
        self.assertEqual(result.stdout, '2\n')

    def test_new_value_after_reset_has_no_old_history(self):
        source = ('fn work(mem: &mut Allocator) -> Int { mem.reset(); '
                  'let mut value = new(mem) Int(42); return *value; }')
        self.assertEqual(self.requirements(source, 'work'), set())
        result = self.execute(source + 'let mut value = work(&mut memory); print(value);')
        self.assertEqual(result.stdout, '42\n')

    def test_known_same_source_use_after_reset_is_rejected_without_call(self):
        with self.assertRaisesRegex(Error, 'reset interdit'):
            compile_program('fn wrong(mem: &mut Allocator) -> Int { let mut value = new(mem) Int(42); '
                            'mem.reset(); return *value; }')

    def test_private_reset_does_not_constrain_external_data(self):
        source = ('fn work(data: &Int) -> Int { let mut local = pool<Int>(1); local.reset(); return *data; }')
        self.assertEqual(self.requirements(source, 'work'), set())
        result = self.execute(source + 'let mut data = new(memory) Int(42); let mut copy = work(&data); print(copy);')
        self.assertEqual(result.stdout, '42\n')

    def test_branch_reset_does_not_pollute_other_branch_read(self):
        source = ('fn work(mem: &mut Allocator, data: &Int, n: Int) -> Int { '
                  'if n == 0 { mem.reset(); return 0; } return *data; }')
        self.assertEqual(self.requirements(source, 'work'), set())
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(source + 'let mut data = new(memory) Int(42); '
                    'let mut value = work(&mut memory, &data, ' + str(flag) + '); print(value);')
                self.assertEqual(result.stdout, '0\n' if flag == 0 else '42\n')

    def test_read_after_conditional_reset_requires_disjointness(self):
        source = ('fn work(mem: &mut Allocator, data: &Int, n: Int) -> Int { '
                  'if n == 0 { mem.reset(); } return *data; }')
        self.assertEqual(len(self.requirements(source, 'work')), 1)

    def test_break_excludes_next_iteration_requirement(self):
        source = ('fn work(mem: &mut Allocator, data: &Int) { loop { print(data); mem.reset(); break; } }')
        self.assertEqual(self.requirements(source, 'work'), set())
        result = self.execute(source + 'let mut data = new(memory) Int(42); work(&mut memory, &data);')
        self.assertEqual(result.stdout, '42\n')

    def test_continue_backedge_protects_next_iteration_read(self):
        source = ('fn work(mem: &mut Allocator, data: &Int) { loop { print(data); mem.reset(); continue; } }')
        self.assertEqual(len(self.requirements(source, 'work')), 1)
        self.rejected(source + 'let mut data = new(memory) Int(42); work(&mut memory, &data);', 'reset interdit')

    def test_while_condition_reuse_and_post_loop_read_are_protected(self):
        for body in ('while *data == 1 { mem.reset(); continue; }',
                     'while false { mem.reset(); break; } print(data);'):
            with self.subTest(body=body):
                source = 'fn work(mem: &mut Allocator, data: &Int) { ' + body + ' }'
                self.assertEqual(len(self.requirements(source, 'work')), 1)

    def test_returned_value_is_alive_despite_conditional_callee_reset(self):
        source = ('fn pick(mem: &mut Allocator, mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
                  'if n == 0 { mem.reset(); return <- a; } return <- b; } '
                  'fn wrap(mem: &mut Allocator, mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
                  'let mut result = pick(mem, -> a, -> b, n); print(result); return <- result; }')
        requirements = self.pairs(self.requirements(source, 'wrap'))
        self.assertEqual(requirements,
            {('distinct', frozenset({('source_parameter', 0), ('allocation_parameter', 1)}))})
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(source + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut a = new(other) Int(10); let mut b = new(memory) Int(20); '
                    'let mut result = wrap(&mut memory, -> a, -> b, ' + str(flag) + '); print(result); '
                    'memory.reset(); other.reset();')
                self.assertEqual(result.stdout, '10\n10\n' if flag == 0 else '20\n20\n')
                self.assertEqual(result.stderr.count('destroy '), 2)

    def test_fresh_return_after_callee_reset_does_not_inherit_reset_history(self):
        source = ('fn make(mem: &mut Allocator) -> <- Int { mem.reset(); '
                  'let mut data = new(mem) Int(42); return <- data; } '
                  'fn work(mem: &mut Allocator) -> Int { let mut result = make(mem); return *result; }')
        self.assertEqual(self.requirements(source, 'work'), set())
        result = self.execute(source + 'let mut value = work(&mut memory); print(value);')
        self.assertEqual(result.stdout, '42\n')

    def test_future_caller_borrow_adds_requirement_even_if_callee_reads_before_reset(self):
        source = BEFORE + 'fn wrap(mem: &mut Allocator, data: &Int) { '
        source += 'let mut value = read_then_clear(mem, data); print(value); print(data); }'
        self.assertEqual(len(self.requirements(source, 'wrap')), 1)
        self.rejected(source + 'let mut data = new(memory) Int(42); wrap(&mut memory, &data);', 'reset interdit')

    def test_prepared_argument_requires_survival_across_later_reset(self):
        source = ('fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                  'fn inspect(data: &Int, n: Int) {} '
                  'fn wrap(mem: &mut Allocator, data: &Int) { inspect(data, clear(mem)); }')
        self.assertEqual(len(self.requirements(source, 'wrap')), 1)
        self.rejected(source + 'let mut data = new(memory) Int(42); wrap(&mut memory, &data);', 'reset interdit')

    def test_scalar_copied_in_earlier_argument_survives_later_reset(self):
        source = ('fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                  'fn take(a: Int, b: Int) { print(a); } '
                  'fn wrap(mem: &mut Allocator, data: &Int) { take(*data, clear(mem)); }')
        self.assertEqual(self.requirements(source, 'wrap'), set())
        result = self.execute(source + 'let mut data = new(memory) Int(42); wrap(&mut memory, &data);')
        self.assertEqual(result.stdout, '42\n')

    def test_source_argument_borrow_cannot_be_mutated_in_later_argument(self):
        with self.assertRaisesRegex(Error, 'aliasés'):
            compile_program('fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                            'fn take(mem: &mut Allocator, n: Int) {} '
                            'fn wrong(mem: &mut Allocator) { take(mem, clear(mem)); }')

    def test_source_equality_cannot_hold_for_a_fresh_private_source(self):
        with self.assertRaisesRegex(Error, 'source de stockage'):
            compile_program('fn wrong(mem: &mut Allocator, mut data: -> Int) { '
                            'let mut private = pool<Int>(1); private.drop(-> data); }')

    def test_match_subject_is_an_access_to_the_enum(self):
        source = ('enum E { A { n: Int } } fn work(mem: &mut Pool<E>, data: &E) { '
                  'mem.reset(); match &data { E.A { n: value } => { print(value); } } }')
        self.assertEqual(len(self.requirements(source, 'work')), 1)
        self.rejected(source + 'let mut memory = pool<E>(1); let mut data = new(memory) E.A { n: 42 }; '
                      'work(&mut memory, &data);', 'reset interdit')

    def test_unused_scalar_body_unknown_reads_now_have_checked_diagnostic(self):
        with self.assertRaisesRegex(Error, "inconnue 'missing'"):
            compile_program('fn broken() { print(missing); }')

    def test_effects_cli_includes_reusable_source_constraints(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'constraints.crb'
            source.write_text(AFTER + BEFORE)
            result = subprocess.run([sys.executable, str(Path(prototype_file).resolve()),
                                     'effects', str(source), '--legacy-reset'], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['read_then_clear']['constraints'], [])
            requirement = report['clear_then_read']['constraints'][0]
            self.assertEqual(requirement['relation'], 'distinct')
            self.assertEqual({requirement['left']['parameter'], requirement['right']['parameter']}, {'mem', 'data'})


if __name__ == '__main__':
    unittest.main()
