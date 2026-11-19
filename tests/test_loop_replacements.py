"""Receiver identity, ownership and pool effects across iteration edges."""
from functools import partial, update_wrapper
import random
import unittest

import test_crust
from crust import Error, compile_program, verify_program

# These regressions exercise the historical reset profile.
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)


class LoopReplacementTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self, source, diagnostic):
        for check in (verify_program, compile_program):
            with self.subTest(check=check.__name__):
                with self.assertRaisesRegex(Error, diagnostic):
                    check(source)

    @staticmethod
    def drops(result):
        return [line for line in result.stderr.splitlines() if line.startswith('destroy ')]

    def test_break_joins_retained_and_replaced_allocations(self):
        result = self.execute("""
            fn run(n: Int) {
                let mut p = pool<Int>(2); let mut r = new(p) Int(10);
                loop {
                    if n == 0 {
                        let x = new(p) Int(20); address(x); r = <- x; break;
                    }
                    address(r); break;
                }
                address(r); print(r);
            }
            fn main() { run(0); run(1); }
        """)
        a, b, first, c, d, second = result.stdout.splitlines()
        self.assertEqual((a, c, first, second), (b, d, '20', '10'))
        self.assertEqual(self.drops(result), ['destroy r=10', 'destroy x=20', 'destroy r=10'])

    def test_continue_and_fallthrough_preserve_slot_identity(self):
        for edge in ('continue;', ''):
            with self.subTest(edge=edge):
                result = self.execute("""
                    let mut p = pool<Int>(2); let mut r = new(p) Int(0);
                    let mut n = 0;
                    while n < 1 {
                        let x = new(p) Int(20); address(x); r = <- x; n = 1;
                        EDGE
                    }
                    address(r); print(r);
                """.replace('EDGE', edge))
                a, b, value = result.stdout.splitlines()
                self.assertEqual((a, value), (b, '20'))
                self.assertEqual(self.drops(result), ['destroy r=0', 'destroy x=20'])

    def test_continue_through_nested_if_and_break_value(self):
        result = self.execute("""
            let mut p = pool<Int>(2); let mut r = new(p) Int(0);
            let n = loop {
                if *r == 0 {
                    let x = new(p) Int(20); r = <- x; continue;
                }
                break 7;
            };
            print(r); print(n);
        """)
        self.assertEqual(result.stdout, '20\n7\n')
        self.assertEqual(self.drops(result), ['destroy r=0', 'destroy x=20'])

    def test_multi_pool_contract_includes_zero_iteration_and_replacement(self):
        program = """
            fn choose(p: &mut Pool<Int>, q: &mut Pool<Int>, n: Int) -> <- Int {
                let mut r = new(p) Int(n);
                while *r == 0 {
                    let x = new(q) Int(20); r = <- x; continue;
                }
                return <- r;
            }
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
            let r = choose(&mut p, &mut q, 0);
        """
        self.assertEqual(self.execute(program + 'print(r); p.reset(); q.reset();').stdout, '20\n')
        for pool in ('p', 'q'):
            self.reject(program + f'{pool}.reset(); print(r);', 'reset interdit')

    def test_backedge_checks_new_pool_before_next_iteration(self):
        program = """
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
            let mut r = new(p) Int(0);
            loop {
                q.reset();
                if *r == 20 { break; }
                let x = new(q) Int(20); r = <- x; continue;
            }
            print(r);
        """
        self.reject(program, 'reset interdit')

    def test_old_borrow_cannot_follow_new_allocation(self):
        self.reject("""
            let mut p = pool<Int>(2); let mut r = new(p) Int(0); let view = &r;
            loop {
                if *r == 20 { break; }
                print(view);
                let x = new(p) Int(20); r = <- x; continue;
            }
            print(r);
        """, 'emprunt actif')
        self.reject("""
            let mut p = pool<Int>(2); let mut r = new(p) Int(0); let view = &r;
            loop { let x = new(p) Int(20); r = <- x; break; }
            print(view); print(r);
        """, 'emprunt actif')

    def test_local_pool_cannot_supply_carried_allocation(self):
        self.reject("""
            let mut p = pool<Int>(1); let mut r = new(p) Int(0);
            loop {
                let seen_r = *r;
                let mut local = pool<Int>(1);
                let x = new(local) Int(20); r = <- x; continue;
            }
        """, 'ne survit pas')

    def test_generated_replacements_follow_sequential_cleanup_model(self):
        rng = random.Random(20261103)
        for _ in range(6):
            count = rng.randrange(2, 8)
            result = self.execute(f"""
                fn increment(x: Int) -> Int {{
                    if x == 0 {{ return 1; }}
                    if x == 1 {{ return 2; }}
                    if x == 2 {{ return 3; }}
                    if x == 3 {{ return 4; }}
                    if x == 4 {{ return 5; }}
                    if x == 5 {{ return 6; }}
                    return 7;
                }}
                let mut p = pool<Int>(2); let mut r = new(p) Int(0);
                loop {{
                    if *r == {count} {{ break; }}
                    let x = new(p) Int(increment(*r)); r = <- x;
                    continue;
                }}
                print(r); p.reset();
            """)
            self.assertEqual(result.stdout, f'{count}\n')
            self.assertEqual(self.drops(result),
                             ['destroy r=0', *(f'destroy x={n}' for n in range(1, count + 1))])

    def test_imported_old_handle_does_not_revive_on_scope_exit(self):
        prefix = """
            let mut p = pool<Int>(2); let mut r = new(p) Int(10);
            {
                r ->;
                while *r == 10 {
                    let x = new(p) Int(20); r = <- x; continue;
                }
                print(r);
                <- r;
            }
        """
        self.assertEqual(self.execute(prefix).stdout, '20\n')
        self.reject(prefix + 'print(r);', 'plus utilisable')

    def test_incompatible_order_across_reentry_is_rejected(self):
        self.reject("""
            let mut p = pool<Int>(3); let mut r = new(p) Int(10);
            let younger = new(p) Int(30);
            while *r == 10 {
                let x = new(p) Int(20); r = <- x; continue;
            }
            print(r); print(younger);
        """, 'ordre de réception différent')

    def test_iteration_local_borrow_can_end_before_replacement(self):
        result = self.execute("""
            let mut p = pool<Int>(2); let mut r = new(p) Int(10);
            while *r == 10 {
                let view = &r; print(view);
                let x = new(p) Int(20); r = <- x; continue;
            }
            print(r);
        """)
        self.assertEqual(result.stdout, '10\n20\n')

    def test_nested_break_can_supply_outer_continue(self):
        result = self.execute("""
            let mut p = pool<Int>(2); let mut r = new(p) Int(0);
            while *r == 0 {
                loop { let x = new(p) Int(20); r = <- x; break; }
                continue;
            }
            print(r);
        """)
        self.assertEqual(result.stdout, '20\n')
        self.assertEqual(self.drops(result), ['destroy r=0', 'destroy x=20'])

    def test_enum_variant_changes_across_continue(self):
        result = self.execute("""
            enum Tag { A, B }
            let mut p = pool<Tag>(1); let mut r = new(p) Tag.A;
            let mut n = 0;
            while n == 0 {
                let x = new(p) Tag.B; r = <- x; n = 1; continue;
            }
            print(r);
        """)
        self.assertEqual(result.stdout, 'Tag.B()\n')
        self.assertEqual(self.drops(result), ['destroy r=Tag.A', 'destroy x=Tag.B'])

    def test_return_after_continue_keeps_loop_provenance(self):
        result = self.execute("""
            fn choose(p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- Int {
                let mut r = new(p) Int(0);
                loop {
                    if *r == 20 { return <- r; }
                    let x = new(q) Int(20); r = <- x; continue;
                }
            }
            let mut p = pool<Int>(1); let mut q = pool<Int>(2);
            let r = choose(&mut p, &mut q);
            print(r);
        """)
        self.assertEqual(result.stdout, '20\n')
        self.assertEqual(self.drops(result), ['destroy r=0', 'destroy x=20'])

    def test_unused_reference_field_does_not_block_reentry(self):
        for field in ('&', '&mut '):
            with self.subTest(field=field):
                prefix = f"""
                    enum View {{ Item {{ target: {field}Int }} }}
                    let mut p = pool<Int>(2); let mut q = pool<View>(1);
                    let mut r = new(p) Int(10);
                    {{
                    let view = new(q) View.Item {{ target: {field}r }};
                    print(view);
                """
                loop = """
                    let mut n = 0;
                    while n == 0 {
                        let x = new(p) Int(20); r = <- x; n = 1; continue;
                    }
                """
                cleanup = 'q.reset();' if field == '&' else ''
                result = self.execute(prefix + loop + 'print(r); ' + cleanup + ' } p.reset();')
                self.assertEqual(result.stdout, 'View.Item(10)\n20\n')
                self.assertEqual(self.drops(result), [
                    'destroy r=10', 'destroy view=View.Item', 'destroy x=20',
                ])
                self.reject(prefix + loop + 'print(view); }', 'emprunt actif')
                self.reject(prefix + loop.replace('let x', 'print(view); let x') + '}',
                            'emprunt actif')
                self.reject(prefix + 'let alias = &view; ' + loop + 'print(alias); }',
                            'emprunt actif')
