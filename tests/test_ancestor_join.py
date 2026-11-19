"""Conditional replacement of an allocation in an enclosing block."""
from functools import partial, update_wrapper
import random
import unittest

import test_crust
from crust import Error, compile_program, verify_program

# These regressions exercise the historical reset profile.
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)


class AncestorJoinTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self, source, diagnostic):
        for check in (verify_program, compile_program):
            with self.assertRaisesRegex(Error, diagnostic):
                check(source)

    def test_both_paths_keep_their_address_and_destroy_once(self):
        result = self.execute('''
            fn run(n: Int) {
                let mut p = pool<Int>(3);
                let older = new(p) Int(1);
                let mut r = new(p) Int(10);
                if n == 0 {
                    let x = new(p) Int(20); address(x); r = <- x;
                } else { address(r); }
                address(r); print(r); print(older);
                p.reset();
            }
            fn main() { run(0); run(1); }
        ''')
        a, b, value, older, c, d, other, older_again = result.stdout.splitlines()
        self.assertEqual((a, value, older, c, other, older_again), (b, '20', '1', d, '10', '1'))
        self.assertEqual([l for l in result.stderr.splitlines() if l.startswith('destroy ')],
                         ['destroy r=10', 'destroy x=20', 'destroy older=1',
                          'destroy r=10', 'destroy older=1'])

    def test_nested_branches_and_early_return_keep_only_continuing_candidates(self):
        result = self.execute('''
            fn run(n: Int) {
                let mut p = pool<Int>(2);
                let mut r = new(p) Int(10);
                print(r);
                if n == 0 { return; } else {
                    if n == 1 { let x = new(p) Int(20); r = <- x; }
                    else { let y = new(p) Int(30); r = <- y; }
                }
                print(r);
            }
            fn main() { run(0); run(1); run(2); }
        ''')
        self.assertEqual(result.stdout, '10\n10\n20\n10\n30\n')
        self.assertEqual([l for l in result.stderr.splitlines() if l.startswith('destroy ')],
                         ['destroy r=10', 'destroy r=10', 'destroy x=20',
                          'destroy r=10', 'destroy y=30'])

    def test_return_contract_keeps_both_pools_and_reset_checks_them(self):
        prefix = '''
            fn choose(p: &mut Pool<Int>, q: &mut Pool<Int>, n: Int) -> <- Int {
                let mut r = new(p) Int(10);
                if n == 0 { let x = new(q) Int(20); r = <- x; }
                return <- r;
            }
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
            let r = choose(&mut p, &mut q, 0);
        '''
        self.assertEqual(self.execute(prefix + 'print(r); p.reset(); q.reset();').stdout, '20\n')
        direct = '''
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
            let mut r = new(p) Int(10);
            if true { let x = new(q) Int(20); r = <- x; }
        '''
        for pool in ('p', 'q'):
            suffix = f'{pool}.reset(); print(r);'
            self.reject(prefix + suffix, 'reset interdit')
            self.reject(direct + suffix, 'reset interdit')

    def test_callee_contract_keeps_replacement_through_block_and_join(self):
        prefix = '''
            fn check(p: &mut Pool<Int>, q: &mut Pool<Int>, clear: &mut Pool<Int>, n: Int) {
                let mut r = new(p) Int(10);
                if n == 0 { { let x = new(q) Int(20); r = <- x; } }
                clear.reset(); print(r);
            }
            let mut p = pool<Int>(1); let mut q = pool<Int>(1); let mut z = pool<Int>(1);
        '''
        self.assertEqual(self.execute(prefix + 'check(&mut p, &mut q, &mut z, 0);').stdout, '20\n')
        self.reject(prefix.replace('clear.reset()', 'q.reset()'), 'reset interdit')

    def test_live_loan_and_conflicting_cleanup_order_are_rejected(self):
        prefix = 'let mut p = pool<Int>(3); let mut r = new(p) Int(10); '
        self.reject(prefix + 'let v = &r; if true { let x = new(p) Int(20); r = <- x; } print(v);',
                    'emprunt actif')
        self.reject(prefix + 'let younger = new(p) Int(5); '
                    'if true { let x = new(p) Int(20); r = <- x; } print(younger); print(r);',
                    'ordre de réception différent')

    def test_shadowed_names_do_not_change_the_outer_binding(self):
        result = self.execute('''
            fn choose(p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- Int {
                let mut r = new(p) Int(10);
                if true { let r = new(q) Int(20); print(r); }
                return <- r;
            }
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
            let r = choose(&mut p, &mut q); q.reset(); print(r);
        ''')
        self.assertEqual(result.stdout, '20\n10\n')

    def test_if_expression_can_replace_ancestor_and_return_independent_value(self):
        result = self.execute("""
            let mut p = pool<Int>(2); let mut r = new(p) Int(10);
            let n = if true { let x = new(p) Int(20); r = <- x; 7 } else { 8 };
            print(n); print(r);
        """)
        self.assertEqual(result.stdout, '7\n20\n')

    def test_generated_cleanup_matches_branch_model(self):
        rng = random.Random(20261103)
        for _ in range(6):
            old, left, right = rng.sample(range(1, 100), 3)
            choice = rng.randrange(2)
            chosen_name, chosen = ('x', left) if choice == 0 else ('y', right)
            result = self.execute(f"""
                let mut p = pool<Int>(3);
                let older = new(p) Int(0);
                let mut r = new(p) Int({old});
                print(r);
                if {choice} == 0 {{ let x = new(p) Int({left}); r = <- x; }}
                else {{ let y = new(p) Int({right}); r = <- y; }}
                print(r); print(older); p.reset();
            """)
            self.assertEqual(result.stdout, f'{old}\n{chosen}\n0\n')
            # Replace destroys the original immediately. Reset walks the
            # model's receiver list in reverse, regardless of slot positions.
            live = [('older', 0), (chosen_name, chosen)]
            expected = [f'destroy r={old}'] + [f'destroy {n}={v}' for n, v in reversed(live)]
            self.assertEqual([line for line in result.stderr.splitlines() if line.startswith('destroy ')],
                             expected)

    def test_moved_sibling_does_not_keep_a_second_cleanup(self):
        result = self.execute('''
            fn run(n: Int) {
                let mut p = pool<Int>(2);
                let mut r = new(p) Int(10);
                let a = new(p) Int(20);
                if n == 0 { a ->; r = <- a; }
                print(r);
            }
            fn main() { run(0); run(1); }
        ''')
        self.assertEqual(result.stdout, '20\n10\n')
        self.assertEqual([l for l in result.stderr.splitlines() if l.startswith('destroy ')],
                         ['destroy r=10', 'destroy a=20', 'destroy a=20', 'destroy r=10'])

    def test_if_join_inside_iteration_cleans_each_local_replacement(self):
        result = self.execute('''
            let mut p = pool<Int>(2); let mut n = 0;
            while n < 2 {
                let mut r = new(p) Int(10);
                if n == 0 { let x = new(p) Int(20); r = <- x; }
                print(r);
                n = 1;
                if *r == 20 { continue; }
                break;
            }
        ''')
        self.assertEqual(result.stdout, '20\n10\n')
        self.assertEqual([l for l in result.stderr.splitlines() if l.startswith('destroy ')],
                         ['destroy r=10', 'destroy x=20', 'destroy r=10'])

    def test_join_rejects_result_that_would_retain_old_tracking_identity(self):
        self.reject('''
            enum View { Item { target: &Int } }
            let mut p = pool<Int>(2); let mut q = pool<View>(1);
            let mut r = new(p) Int(10);
            let v = if true {
                let x = new(p) Int(20); r = <- x;
                let a = new(q) View.Item { target: &r }; <- a
            } else {
                let b = new(q) View.Item { target: &r }; <- b
            };
            print(v);
        ''', 'jonction if : emprunt actif')

    def test_outer_replacement_on_backedge_updates_next_test(self):
        result = self.execute("""
            let mut p = pool<Int>(2); let mut r = new(p) Int(10);
            while *r == 10 {
                let x = new(p) Int(20); r = <- x;
                continue;
            }
            print(r);
        """)
        self.assertEqual(result.stdout, '20\n')

    def test_reset_of_replaced_pool_stays_on_its_branch(self):
        source = """
            fn run(p: &mut Pool<Int>, q: &mut Pool<Int>, n: Int) {
                let mut r = new(p) Int(10);
                if n == 0 { let x = new(q) Int(20); r = <- x; p.reset(); }
                print(r);
            }
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                run(&mut p, &mut q, 0); run(&mut p, &mut q, 1);
            }
        """
        self.assertEqual(self.execute(source).stdout, '20\n10\n')
        self.reject(source.replace('p.reset()', 'q.reset()'), 'reset interdit')

    def test_joined_object_keeps_borrow_targets_from_both_branches(self):
        prefix = """
            enum View { Item { target: &Int } }
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
            let mut views = pool<View>(2);
            let a = new(p) Int(10); let b = new(q) Int(20);
            let mut r = new(views) View.Item { target: &a };
            if true { let x = new(views) View.Item { target: &b }; r = <- x; }
        """
        self.assertEqual(self.execute(prefix + 'print(r); views.reset(); p.reset(); q.reset();').stdout,
                         'View.Item(20)\n')
        for pool in ('p', 'q'):
            self.reject(prefix + f'{pool}.reset(); print(r);', 'reset interdit')

    def test_shadow_after_replacement_keeps_the_updated_outer_provenance(self):
        prefix = """
            fn choose(p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- Int {
                let mut r = new(p) Int(10);
                print(r);
                {
                    let x = new(q) Int(20); r = <- x;
                    let r = new(p) Int(30); print(r);
                }
                return <- r;
            }
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
            let r = choose(&mut p, &mut q);
        """
        self.assertEqual(self.execute(prefix + 'p.reset(); print(r);').stdout, '10\n30\n20\n')
        self.reject(prefix + 'q.reset(); print(r);', 'reset interdit')
        self.reject(prefix.replace('return <- r;', 'q.reset(); return <- r;') + 'print(r);',
                    'reset interdit')
