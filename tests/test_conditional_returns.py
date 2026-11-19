"""Conditional allocation returns: one selected object, one known source."""
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
import test_crust


class ConditionalReturnTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def check_sources(self, program, expected, output):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(6)'):
            for flag in (0, 1):
                with self.subTest(factory=factory, flag=flag):
                    result = self.execute('let mut memory = ' + factory + '; let mut flag = ' + str(flag) + '; ' + program)
                    self.assertEqual(result.stdout, output[flag])
                    self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                     expected[flag])

    def test_each_branch_returns_one_allocation_after_cleaning_its_temporaries(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'let mut outer = new(mem) Int(99); print(outer); if n == 1 { '
            'let mut temp = new(mem) Int(98); print(temp); let mut a = new(mem) Int(10); return <- a; '
            '} else { let mut b = new(mem) Int(20); return <- b; } } '
            'let mut result = make(&mut memory, flag); print(result); drop(-> result); memory.reset();',
            [['destroy outer=99', 'destroy b=20'],
             ['destroy temp=98', 'destroy outer=99', 'destroy a=10']], ['99\n20\n', '99\n98\n10\n'])

    def test_branch_return_and_normal_return_share_the_source(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { let mut a = new(mem) Int(10); return <- a; } '
            'let mut b = new(mem) Int(20); return <- b; } '
            'let mut result = make(&mut memory, flag); print(result);',
            [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])

    def test_nested_function_returns_keep_address_and_source(self):
        program = (
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { let mut a = new(mem) Int(10); address(a); return <- a; } '
            'else { let mut b = new(mem) Int(20); address(b); return <- b; } } '
            'fn forward(mem: &mut Allocator, n: Int) -> <- Int { '
            'let mut result = make(mem, n); address(result); return <- result; } '
            'let mut result = forward(&mut memory, flag); address(result); '
            'drop(-> result); memory.reset();')
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(1)'):
            for flag in (0, 1):
                with self.subTest(factory=factory, flag=flag):
                    result = self.execute('let mut memory = ' + factory + '; let mut flag = ' + str(flag) + '; ' + program)
                    lines = result.stdout.splitlines()
                    self.assertEqual(len(lines), 3)
                    self.assertEqual(lines, [lines[0]] * 3)
                    self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                     ['destroy a=10' if flag else 'destroy b=20'])

    def test_selection_between_owned_arguments_consumes_both_original_handles(self):
        self.check_sources(
            'fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
            'if n == 1 { -> a; return <- a; } else { -> b; return <- b; } } '
            'let mut a = new(memory) Int(10); let mut b = new(memory) Int(20); '
            'let mut result = choose(-> a, -> b, flag); print(result);',
            [['destroy a=10', 'destroy b=20'], ['destroy b=20', 'destroy a=10']],
            ['20\n', '10\n'])
        self.rejected('fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
                      'if n == 1 { -> a; return <- a; } else { -> b; return <- b; } } '
                      'let mut a = new(memory) Int(10); let mut b = new(memory) Int(20); '
                      'let mut result = choose(-> a, -> b, 0); print(a); print(result);', 'plus utilisable')

    def test_rhs_can_return_original_or_replace_it_without_double_destruction(self):
        self.check_sources(
            'fn replace(mem: &mut Allocator, mut old: -> Int, n: Int) -> <- Int { '
            'if n == 1 { -> old; return <- old; } '
            'let mut fresh = new(mem) Int(20); return <- fresh; } '
            'let mut data = new(memory) Int(10); data = replace(&mut memory, -> data, flag); print(data);',
            [['destroy data=10', 'destroy fresh=20'], ['destroy data=10']], ['20\n', '10\n'])

    def test_reset_tracks_the_selected_result_after_return(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { let mut a = new(mem) Int(10); return <- a; } '
            'let mut b = new(mem) Int(20); return <- b; } '
            'let mut result = make(&mut memory, flag); print(result); memory.reset();',
            [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])
        self.rejected('fn make(mem: &mut Allocator) -> <- Int { '
                      'if true { let mut a = new(mem) Int(10); return <- a; } '
                      'let mut b = new(mem) Int(20); return <- b; } '
                      'let mut result = make(&mut memory); memory.reset(); print(result);', 'reset interdit')

    def test_only_selected_branch_allocates_in_a_single_slot_pool(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(
                    'fn make(mem: &mut Pool<Int>, n: Int) -> <- Int { '
                    'if n == 1 { let mut a = new(mem) Int(10); address(a); return <- a; } '
                    'else { let mut b = new(mem) Int(20); address(b); return <- b; } } '
                    'let mut memory = pool<Int>(1); let mut result = make(&mut memory, ' + str(flag) + '); '
                    'address(result); print(result); drop(-> result); '
                    'let mut fresh = new(memory) Int(30); address(fresh); print(fresh); memory.reset();')
                lines = result.stdout.splitlines()
                self.assertEqual(lines[0], lines[1])
                self.assertEqual(lines[0], lines[3])
                self.assertEqual([lines[2], lines[4]], ['10' if flag else '20', '30'])
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy a=10' if flag else 'destroy b=20', 'destroy fresh=30'])

    def test_unselected_owned_input_is_freed_before_returned_slot_reuse(self):
        self.check_sources(
            'fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
            'if n == 1 { -> a; return <- a; } else { -> b; return <- b; } } '
            'let mut a = new(memory) Int(10); let mut b = new(memory) Int(20); '
            'let mut result = choose(-> a, -> b, flag); let mut fresh = new(memory) Int(30); '
            'print(result); print(fresh); memory.reset();',
            [['destroy a=10', 'destroy fresh=30', 'destroy b=20'],
             ['destroy b=20', 'destroy fresh=30', 'destroy a=10']], ['20\n30\n', '10\n30\n'])

    def test_enum_arms_can_differ_but_enum_type_and_root_pool_are_identical(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(
                    'enum E { A { n: Int }, B { x: Int, y: Int } } '
                    'fn make(mem: &mut Pool<E>, n: Int) -> <- E { '
                    'if n == 1 { let mut a = new(mem) E.A { n: 10 }; return <- a; } '
                    'else { let mut b = new(mem) E.B { x: 20, y: 30 }; return <- b; } } '
                    'let mut memory = pool<E>(1); let mut result = make(&mut memory, ' + str(flag) + '); '
                    'print(result); memory.reset();')
                self.assertEqual(result.stdout, 'E.A(10)\n' if flag else 'E.B(20, 30)\n')
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy a=E.A' if flag else 'destroy b=E.B'])

    def test_different_return_sources_work_for_both_return_shapes(self):
        for tail in ('else { let mut b = new(second) Int(20); return <- b; }',
                     'let mut b = new(second) Int(20); return <- b;'):
            with self.subTest(tail=tail):
                result = self.execute(
                    'let mut memory = pool<Int>(2); '
                    'fn make(first: &mut Allocator, second: &mut Allocator) -> <- Int { '
                    'if true { let mut a = new(first) Int(10); return <- a; } ' + tail + ' } '
                    'let mut other = pool<Int>(1); let mut result = make(&mut memory, &mut other); print(result);')
                self.assertEqual(result.stdout, '10\n')
                self.assertEqual(result.stderr.count('destroy a=10'), 1)

    def test_different_sources_of_owned_candidates_are_supported(self):
        result = self.execute('fn choose(mut a: -> Int, mut b: -> Int) -> <- Int { '
                              'if true { -> a; return <- a; } else { -> b; return <- b; } } '
                              'let mut other = pool<Int>(1); let mut a = new(memory) Int(10); '
                              'let mut b = new(other) Int(20); let mut result = choose(-> a, -> b); print(result);')
        self.assertEqual(result.stdout, '10\n')
        self.assertEqual(result.stderr.count('destroy a=10'), 1)
        self.assertEqual(result.stderr.count('destroy b=20'), 1)

    def test_declared_return_type_must_match_every_candidate(self):
        self.rejected('enum E { A } let mut other = pool<E>(1); '
                      'fn make(mem: &mut Allocator, pool: &mut Pool<E>) -> <- Int { '
                      'if true { let mut a = new(mem) Int(10); return <- a; } '
                      'else { let mut b = new(pool) E.A; return <- b; } } '
                      'let mut result = make(&mut memory, &mut other); print(result);',
                      'allocation Int attendue')

    def test_source_must_survive_the_function_on_every_return_path(self):
        self.rejected('fn make() -> <- Int { let mut local = pool<Int>(1); '
                      'if true { let mut a = new(local) Int(10); return <- a; } '
                      'else { let mut b = new(local) Int(20); return <- b; } } '
                      'let mut result = make(); print(result);', 'source.*ne survit pas')

    def test_all_paths_need_explicit_allocation_return(self):
        cases = [
            'if true { let mut a = new(mem) Int(10); return <- a; }',
            'if true { let mut a = new(mem) Int(10); return <- a; } else { return; }',
            'if true { let mut a = new(mem) Int(10); return a; } '
            'else { let mut b = new(mem) Int(20); return <- b; }',
        ]
        for body in cases:
            with self.subTest(body=body):
                self.rejected('fn make(mem: &mut Allocator) -> <- Int { ' + body + ' } '
                              'let mut result = make(&mut memory); print(result);',
                              'retour|affectation implicite')

    def test_unused_receiver_is_still_rejected(self):
        self.rejected('fn make(mem: &mut Allocator) -> <- Int { '
                      'if true { let mut a = new(mem) Int(10); return <- a; } '
                      'else { let mut b = new(mem) Int(20); return <- b; } } '
                      'let mut unused = make(&mut memory);', 'sans usage explicite')

    def test_nested_conditional_wrappers_preserve_selected_result(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { if true { let mut a = new(mem) Int(10); return <- a; } '
            'else { let mut unreachable = new(mem) Int(11); return <- unreachable; } } '
            'let mut b = new(mem) Int(20); return <- b; } '
            'fn forward(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { let mut first = make(mem, n); return <- first; } '
            'let mut second = make(mem, n); return <- second; } '
            'let mut result = forward(&mut memory, flag); print(result); memory.reset();',
            [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])

    def test_caller_borrow_of_selected_result_obeys_drop_and_reset_rules(self):
        prefix = (
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { let mut a = new(mem) Int(10); return <- a; } '
            'let mut b = new(mem) Int(20); return <- b; } '
            'fn read(a: &Int) { print(a); } '
            'fn consume(mut a: -> Int) { drop(-> a); } ')
        self.check_sources(prefix + 'let mut result = make(&mut memory, flag); '
                           'let mut view = &result; read(view); consume(-> result); memory.reset();',
                           [['destroy b=20'], ['destroy a=10']], ['20\n', '10\n'])
        for action, message in (('drop(-> result);', 'emprunt encore utilisé'),
                                ('memory.reset();', 'reset interdit')):
            with self.subTest(action=action):
                self.rejected(prefix + 'let mut result = make(&mut memory, 1); let mut view = &result; '
                              + action + 'read(&view);', message)

    def test_return_merge_keeps_conditional_reset_effects_on_caller(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { mem.reset(); let mut a = new(mem) Int(10); return <- a; } '
            'let mut b = new(mem) Int(20); return <- b; } '
            'let mut old = new(memory) Int(99); print(old); let mut result = make(&mut memory, flag); '
            'print(result); drop(-> result); memory.reset();',
            [['destroy b=20', 'destroy old=99'], ['destroy old=99', 'destroy a=10']],
            ['99\n20\n', '99\n10\n'])

    def test_reassignment_cleans_old_value_only_on_paths_not_already_reset(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { mem.reset(); let mut a = new(mem) Int(10); return <- a; } '
            'let mut b = new(mem) Int(20); return <- b; } '
            'let mut data = new(memory) Int(99); print(data); data = make(&mut memory, flag); print(data);',
            [['destroy data=99', 'destroy b=20'], ['destroy data=99', 'destroy a=10']],
            ['99\n20\n', '99\n10\n'])

    def test_selected_result_can_be_transferred_or_borrowed_as_an_argument(self):
        self.check_sources(
            'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
            'if n == 1 { let mut a = new(mem) Int(10); return <- a; } '
            'let mut b = new(mem) Int(20); return <- b; } '
            'fn consume(mut a: -> Int) { print(a); drop(-> a); } '
            'fn read(a: &Int) { print(a); } '
            'consume(-> make(&mut memory, flag)); read(&make(&mut memory, flag)); memory.reset();',
            [['destroy b=20', 'destroy b=20'], ['destroy a=10', 'destroy a=10']],
            ['20\n20\n', '10\n10\n'])

    def test_owned_return_can_reset_then_reuse_a_single_slot_explicitly(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute(
                    'fn replace(mem: &mut Pool<Int>, mut old: -> Int, n: Int) -> <- Int { '
                    'if n == 1 { mem.reset(); let mut fresh = new(mem) Int(20); return <- fresh; } '
                    'return <- old; } let mut memory = pool<Int>(1); let mut data = new(memory) Int(10); '
                    'address(data); data = replace(&mut memory, -> data, ' + str(flag) + '); '
                    'address(data); print(data); memory.reset();')
                lines = result.stdout.splitlines()
                self.assertEqual(lines[0], lines[1])
                self.assertEqual(lines[2:], ['20' if flag else '10'])
                self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                 ['destroy data=10', 'destroy fresh=20'] if flag else ['destroy data=10'])

    def test_conditional_call_hands_cleanup_to_selected_result(self):
        self.check_sources(
            'fn choose(mut data: -> Int, n: Int) -> <- Int { '
            'if n == 1 { -> data; return <- data; } return <- data; } '
            'let mut data = new(memory) Int(10); if flag == 1 { -> data; '
            'let mut selected = choose(-> data, flag); print(selected); } memory.reset();',
            [['destroy data=10']] * 2, ['', '10\n'])

    def test_round_trip_through_function_then_branch_rearms_cleanup(self):
        self.check_sources(
            'fn identity(mut data: -> Int) -> <- Int { return <- data; } '
            'let mut data = new(memory) Int(10); if flag == 1 { -> data; '
            'data = identity(-> data); <- data; } print(data); memory.reset();',
            [['destroy data=10']] * 2, ['10\n', '10\n'])

    def test_later_branch_does_not_reuse_flags_from_finished_callee(self):
        self.check_sources(
            'fn consume(mut a: -> Int) { if true { return; } else { return; } } '
            'let mut discarded = new(memory) Int(5); consume(-> discarded); '
            'let mut data = new(memory) Int(10); if flag == 1 { print(data); } memory.reset();',
            [['destroy discarded=5', 'destroy data=10']] * 2, ['', '10\n'])


if __name__ == '__main__':
    unittest.main()
