"""Finite provenance sets, stable addresses and source-specific invalidation."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


MAKE = ('fn make(a: &mut Allocator, b: &mut Allocator, n: Int) -> <- Int { '
        'if n == 0 { let mut x = new(a) Int(10); return <- x; } '
        'let mut y = new(b) Int(20); return <- y; } ')
CHOOSE = ('fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
          'if n == 0 { return <- a; } return <- b; } ')


class ProvenanceTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def test_function_results_from_distinct_source_kinds(self):
        factories = ('allocator()', 'stack(65536)', 'pool<Int>(1)')
        for first in factories:
            for second in factories:
                for n in (0, 1):
                    with self.subTest(first=first, second=second, n=n):
                        result = self.execute(MAKE + 'let mut memory = ' + first + '; let mut other = ' + second + '; '
                            'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); '
                            'drop(-> result); memory.reset(); other.reset();')
                        self.assertEqual(result.stdout, '10\n' if n == 0 else '20\n')
                        self.assertEqual(result.stderr.count('destroy '), 1)

    def test_owned_selection_preserves_address_and_destroys_other_candidate(self):
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute(CHOOSE + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut a = new(memory) Int(10); let mut b = new(other) Int(20); address(a); address(b); '
                    'let mut result = choose(-> a, -> b, ' + str(n) + '); address(result); print(result); '
                    'drop(-> result); memory.reset(); other.reset();')
                lines = result.stdout.splitlines()
                self.assertEqual(lines[2], lines[n])
                self.assertEqual(lines[3:], ['10' if n == 0 else '20'])
                drops = [s for s in result.stderr.splitlines() if s.startswith('destroy ')]
                self.assertEqual(drops, ['destroy b=20', 'destroy a=10'] if n == 0 else
                                 ['destroy a=10', 'destroy b=20'])

    def test_both_possible_sources_are_protected_until_last_use(self):
        for source in ('memory', 'other'):
            for use in ('print(result);', 'let mut view = &result; print(view);', 'drop(-> result);'):
                with self.subTest(source=source, use=use):
                    self.rejected(MAKE + 'let mut other = pool<Int>(1); '
                        'let mut result = make(&mut memory, &mut other, 0); ' + source + '.reset(); ' + use,
                        'reset interdit')

    def test_stored_borrow_protects_each_possible_source(self):
        for source in ('memory', 'other'):
            with self.subTest(source=source):
                self.rejected(MAKE + 'let mut other = pool<Int>(1); '
                    'let mut result = make(&mut memory, &mut other, 0); let mut view = &result; '
                    + source + '.reset(); print(view);', 'reset interdit')

    def test_reset_only_destroys_the_selected_object_when_it_belongs_to_source(self):
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute(MAKE + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); '
                    'memory.reset(); let mut fresh = new(memory) Int(30); print(fresh); other.reset(); memory.reset();')
                self.assertEqual(result.stdout, ('10\n' if n == 0 else '20\n') + '30\n')
                drops = [s for s in result.stderr.splitlines() if s.startswith('destroy ')]
                self.assertEqual(drops, ['destroy x=10', 'destroy fresh=30'] if n == 0 else
                                 ['destroy y=20', 'destroy fresh=30'])

    def test_reset_of_other_source_keeps_survivor_for_automatic_cleanup(self):
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute(MAKE + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); memory.reset();')
                self.assertEqual(result.stderr.count('destroy '), 1)
                lines = result.stderr.splitlines()
                if n == 1:
                    self.assertLess(lines.index('reset'), lines.index('destroy y=20'))

    def test_reset_through_nested_functions_uses_cleanup_handles(self):
        for factory in ('allocator()', 'pool<Int>(1)'):
            for n in (0, 1):
                with self.subTest(factory=factory, n=n):
                    result = self.execute(MAKE + 'fn clear(mem: &mut Allocator) { mem.reset(); } '
                        'fn relay(mem: &mut Allocator) { clear(mem); } '
                        'let mut memory = ' + factory + '; let mut other = ' + factory + '; '
                        'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); '
                        'relay(&mut memory); relay(&mut memory); relay(&mut other);')
                    self.assertEqual(result.stderr.count('destroy '), 1)

    def test_reset_via_function_rejects_future_owner_and_reborrow_use(self):
        for source in ('memory', 'other'):
            with self.subTest(source=source):
                self.rejected(MAKE + 'fn clear(mem: &mut Allocator) { mem.reset(); } '
                    'let mut other = pool<Int>(1); let mut result = make(&mut memory, &mut other, 0); '
                    'clear(&mut ' + source + '); print(result);', 'reset interdit')
                self.rejected(MAKE + 'fn clear(mem: &mut Allocator, view: &Int) { mem.reset(); } '
                    'let mut other = pool<Int>(1); let mut result = make(&mut memory, &mut other, 0); let mut view = &result; '
                    'clear(&mut ' + source + ', view); print(view);', 'reset interdit')

    def test_nested_calls_and_third_source_union(self):
        prelude = MAKE + CHOOSE + ('fn forward(mut data: -> Int, n: Int) -> <- Int { '
                                  'if n == 0 { return <- data; } return <- data; } ')
        for first, second in ((0, 0), (1, 0), (1, 1)):
            with self.subTest(first=first, second=second):
                result = self.execute(prelude + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut third = pool<Int>(1); let mut a = make(&mut memory, &mut other, ' + str(first) + '); '
                    'let mut b = new(third) Int(30); let mut chosen = choose(-> a, -> b, ' + str(second) + '); '
                    'let mut result = forward(-> chosen, 0); print(result); memory.reset(); other.reset(); third.reset();')
                expected = 30 if second else (10 if first == 0 else 20)
                self.assertEqual(result.stdout, str(expected) + '\n')
                self.assertEqual(result.stderr.count('destroy '), 2)
        for source in ('memory', 'other', 'third'):
            with self.subTest(source=source):
                self.rejected(prelude + 'let mut other = pool<Int>(1); let mut third = pool<Int>(1); '
                    'let mut a = make(&mut memory, &mut other, 0); let mut b = new(third) Int(30); '
                    'let mut result = choose(-> a, -> b, 0); ' + source + '.reset(); print(result);', 'reset interdit')

    def test_if_expression_unions_sources_and_preserves_address(self):
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute('let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut a = new(memory) Int(10); let mut b = new(other) Int(20); address(a); address(b); '
                    'let mut n = ' + str(n) + '; let mut result = if n == 0 { -> a; <- a } else { -> b; <- b }; '
                    'address(result); print(result); memory.reset(); other.reset();')
                lines = result.stdout.splitlines()
                self.assertEqual(lines[n], lines[2])
                self.assertEqual(result.stderr.count('destroy '), 2)

    def test_local_source_cannot_escape_in_any_candidate(self):
        self.rejected('fn wrong(mem: &mut Allocator, n: Int) -> <- Int { let mut local = pool<Int>(1); '
            'if n == 0 { let mut a = new(mem) Int(10); return <- a; } '
            'let mut b = new(local) Int(20); return <- b; } let mut result = wrong(&mut memory, 0); print(result);',
            'source.*ne survit pas')
        self.rejected(MAKE + 'let mut result = { let mut local = pool<Int>(1); '
            'let mut a = make(&mut memory, &mut local, 0); <- a }; print(result);', 'source.*ne survit pas')

    def test_source_specific_drop_requires_unambiguous_provenance(self):
        for source in ('memory', 'other'):
            with self.subTest(source=source):
                self.rejected(MAKE + 'let mut other = pool<Int>(1); '
                    'let mut result = make(&mut memory, &mut other, 0); '
                    + source + '.drop(-> result);', 'source de stockage')
        # Repeated aliases of a mutable source are still rejected at the call.
        self.rejected(MAKE + 'let mut result = make(&mut memory, &mut memory, 0); print(result);', 'aliasés')

    def test_duplicate_actual_provenance_is_deduplicated(self):
        result = self.execute(CHOOSE + 'let mut memory = pool<Int>(2); let mut a = new(memory) Int(10); '
            'let mut b = new(memory) Int(20); let mut result = choose(-> a, -> b, 0); '
            'print(result); memory.drop(-> result); memory.reset();')
        self.assertEqual(result.stdout, '10\n')
        self.assertEqual(result.stderr.count('destroy '), 2)

    def test_reassignment_destroys_old_selected_value_after_new_rhs(self):
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute(MAKE + 'let mut memory = pool<Int>(2); let mut other = pool<Int>(1); '
                    'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); '
                    'result = new(memory) Int(30); print(result); memory.reset(); other.reset();')
                self.assertEqual(result.stdout, ('10\n' if n == 0 else '20\n') + '30\n')
                self.assertEqual(result.stderr.count('destroy '), 2)

    def test_pending_arguments_protect_every_possible_source(self):
        for source in ('memory', 'other'):
            with self.subTest(source=source):
                self.rejected(MAKE + 'fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                    'fn consume(mut data: -> Int, n: Int) {} let mut other = pool<Int>(1); '
                    'consume(-> make(&mut memory, &mut other, 0), clear(&mut ' + source + '));', 'reset interdit')
                self.rejected(MAKE + 'fn clear(mem: &mut Allocator) -> Int { mem.reset(); return 0; } '
                    'fn inspect(data: &Int, n: Int) {} let mut other = pool<Int>(1); '
                    'inspect(&make(&mut memory, &mut other, 0), clear(&mut ' + source + '));', 'reset interdit')

    def test_partial_resets_and_conditional_joins_keep_cleanup_guard(self):
        for chosen in (0, 1):
            for reset in (0, 1):
                with self.subTest(chosen=chosen, reset=reset):
                    result = self.execute(MAKE + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                        'let mut result = make(&mut memory, &mut other, ' + str(chosen) + '); print(result); '
                        'let mut n = ' + str(reset) + '; if n == 0 { memory.reset(); } '
                        'memory.reset(); other.reset();')
                    self.assertEqual(result.stderr.count('destroy '), 1)

    def test_loop_reanalysis_can_reset_unused_selected_value_repeatedly(self):
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute(MAKE + 'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); '
                    'let mut controls = allocator(); let mut state = new(controls) Int(0); '
                    'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); '
                    'while *state < 2 { memory.reset(); '
                    'if *state == 0 { state.set(1); continue; } state.set(2); } other.reset();')
                self.assertEqual(result.stderr.count('destroy x=10') + result.stderr.count('destroy y=20'), 1)

    def test_loop_reads_protect_all_possible_sources(self):
        for source in ('memory', 'other'):
            with self.subTest(source=source):
                self.rejected(MAKE + 'let mut other = pool<Int>(1); '
                    'let mut result = make(&mut memory, &mut other, 0); let mut view = &result; '
                    'loop { print(view); ' + source + '.reset(); continue; }', 'reset interdit')

    def test_enum_pool_root_matches_actual_arm_on_partial_reset(self):
        prelude = ('enum E { A { n: Int }, B { x: Int, y: Int } } '
            'fn make(a: &mut Pool<E>, b: &mut Pool<E>, n: Int) -> <- E { '
            'if n == 0 { let mut x = new(a) E.A { n: 10 }; return <- x; } '
            'let mut y = new(b) E.B { x: 20, y: 30 }; return <- y; } ')
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute(prelude + 'fn clear(mem: &mut Pool<E>) { mem.reset(); } '
                    'let mut memory = pool<E>(1); let mut other = pool<E>(1); '
                    'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); '
                    'clear(&mut memory); let mut fresh = new(memory) E.A { n: 99 }; print(fresh); '
                    'clear(&mut other); clear(&mut memory);')
                self.assertEqual(result.stdout, ('E.A(10)\n' if n == 0 else 'E.B(20, 30)\n') + 'E.A(99)\n')
                self.assertEqual(result.stderr.count('destroy '), 2)
        self.rejected(prelude + 'let mut memory = pool<E>(1); let mut other = pool<E>(1); '
            'let mut result = make(&mut memory, &mut other, 0); other.reset(); print(result);', 'reset interdit')

    def test_reset_unrelated_source_preserves_access(self):
        result = self.execute(MAKE + 'let mut other = pool<Int>(1); let mut third = pool<Int>(1); '
            'let mut result = make(&mut memory, &mut other, 0); third.reset(); print(result); drop(-> result);')
        self.assertEqual(result.stdout, '10\n')

    def test_rhs_partial_reset_then_replacement_cleans_surviving_old_candidate(self):
        for n in (0, 1):
            with self.subTest(n=n):
                result = self.execute(MAKE + 'fn replace(a: &mut Allocator, b: &mut Allocator) -> <- Int { '
                    'a.reset(); let mut fresh = new(b) Int(30); return <- fresh; } '
                    'let mut memory = pool<Int>(1); let mut other = pool<Int>(2); '
                    'let mut result = make(&mut memory, &mut other, ' + str(n) + '); print(result); '
                    'result = replace(&mut memory, &mut other); print(result); memory.reset(); other.reset();')
                self.assertEqual(result.stdout, ('10\n' if n == 0 else '20\n') + '30\n')
                self.assertEqual(result.stderr.count('destroy '), 2)

    def test_function_conditional_reset_preserves_path_sensitive_cleanup(self):
        for chosen in (0, 1):
            for reset in (0, 1):
                with self.subTest(chosen=chosen, reset=reset):
                    result = self.execute(MAKE + 'fn clear(mem: &mut Allocator, n: Int) { '
                        'if n == 0 { mem.reset(); } } '
                        'let mut memory = allocator(); let mut other = allocator(); '
                        'let mut result = make(&mut memory, &mut other, ' + str(chosen) + '); print(result); '
                        'clear(&mut memory, ' + str(reset) + '); clear(&mut memory, 0); clear(&mut other, 0);')
                    self.assertEqual(result.stderr.count('destroy '), 1)

    def test_loop_reanalysis_discards_provisional_multi_source_returns(self):
        result = self.execute(MAKE + 'fn work(a: &mut Allocator, b: &mut Allocator, state: &mut Int) -> <- Int { '
            'loop { a.reset(); if *state == 1 { let mut value = make(a, b, *state); return <- value; } '
            'state.set(1); continue; } } '
            'let mut memory = pool<Int>(1); let mut other = pool<Int>(1); let mut old = new(memory) Int(99); '
            'print(old); '
            'let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'let mut result = work(&mut memory, &mut other, &mut state); print(result); memory.reset(); other.reset();')
        self.assertEqual(result.stdout, '99\n20\n')
        self.assertEqual(result.stderr.count('destroy old=99'), 1)
        self.assertEqual(result.stderr.count('destroy y=20'), 1)

    def test_wrong_candidate_type_remains_rejected(self):
        self.rejected('enum E { A } let mut other = pool<E>(1); '
            'fn wrong(a: &mut Allocator, b: &mut Pool<E>, n: Int) -> <- Int { '
            'if n == 0 { let mut x = new(a) Int(10); return <- x; } '
            'let mut y = new(b) E.A; return <- y; } let mut result = wrong(&mut memory, &mut other, 0); print(result);',
            'allocation Int attendue')


if __name__ == '__main__':
    unittest.main()
