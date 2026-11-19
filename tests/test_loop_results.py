"""Interactions between loop results, cleanup, provenance and the pool cursor."""
from functools import partial, update_wrapper
import random
import unittest

import test_crust
from crust import Error, compile_program, verify_program

# These regressions exercise the historical reset profile.
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)


class LoopResultTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self, source, diagnostic):
        for check in (verify_program, compile_program):
            with self.subTest(check=check.__name__):
                with self.assertRaisesRegex(Error, diagnostic):
                    check(source)

    @staticmethod
    def destructions(result):
        return [line for line in result.stderr.splitlines() if line.startswith('destroy ')]

    def test_two_transfers_preserve_identity_and_cleanup_order(self):
        result = self.execute('''
            let mut p = pool<Int>(2);
            let recu = loop {
                let temp = new(p) Int(10);
                let middle = loop {
                    let result = new(p) Int(20);
                    address(result);
                    break <- result;
                };
                print(temp);
                address(middle);
                break <- middle;
            };
            address(recu);
            print(recu);
        ''')
        a, value, b, c, received = result.stdout.splitlines()
        self.assertEqual((a, value, b, c, received), (a, '10', a, a, '20'))
        self.assertEqual(self.destructions(result), ['destroy temp=10', 'destroy result=20'])

    def test_each_transfer_checks_storage_and_borrow_target(self):
        self.reject('''
            let out = loop {
                let mut p = pool<Int>(1);
                let middle = loop { let a = new(p) Int(20); break <- a; };
                print(middle);
                break <- middle;
            }; print(out);
        ''', 'ne survit pas à la boucle')
        self.reject('''
            let mut p = pool<Int>(1);
            let view = loop { let a = new(p) Int(20); break &a; };
            print(view);
        ''', 'cible empruntée non durable')
        self.reject('''
            enum View { Item { target: &Int } }
            let mut p = pool<Int>(1); let mut q = pool<View>(1);
            let view = loop {
                let a = new(p) Int(20);
                let b = new(q) View.Item { target: &a };
                break <- b;
            };
            print(view);
        ''', 'cible empruntée non durable')

    def test_borrowed_field_survives_transfers_and_protects_its_pool(self):
        prefix = """
            enum View { Item { target: &Int } }
            let mut p = pool<Int>(1); let mut q = pool<View>(1);
            let a = new(p) Int(20);
            let view = loop {
                let middle = loop {
                    let b = new(q) View.Item { target: &a };
                    break <- b;
                };
                print(middle);
                break <- middle;
            };
        """
        self.reject(prefix + 'p.reset(); print(view);', 'reset interdit')
        result = self.execute(prefix + 'print(view); q.reset(); p.reset();')
        self.assertEqual(result.stdout, 'View.Item(20)\nView.Item(20)\n')
        self.assertEqual(self.destructions(result), ['destroy b=View.Item', 'destroy a=20'])

    def test_warning_does_not_transfer_or_prevent_slot_reuse(self):
        source = '''
            fn main() {
                loop { let mut p = pool<Int>(1); let local = new(p) Int(9); break <- local; }
                let mut q = pool<Int>(1);
                loop { let first = new(q) Int(10); address(first); break <- first; };
                let second = new(q) Int(20);
                address(second);
                print(second);
            }
        '''
        for compiler in (verify_program(source), compile_program(source)[0]):
            self.assertEqual(len(compiler.warnings), 2)
            self.assertTrue(all('transfert sans receveur' in w for w in compiler.warnings))
        result = self.execute(source)
        first, second, output = result.stdout.splitlines()
        self.assertEqual((first, second, output), (first, first, '20'))
        self.assertEqual(self.destructions(result), ['destroy local=9', 'destroy first=10', 'destroy second=20'])

    def test_exit_modes_and_missing_receivers(self):
        for source, diagnostic in [
            ('let x = loop { if true { break; } break 1; }; print(x);', 'break sans valeur'),
            ('let x = loop { if true { break 1; } break &x; }; print(x);', 'variable inconnue'),
            ('let x = while false { break 1; }; print(x);', 'while ne fournit'),
            ('while true { break 1; }', 'while ne fournit'),
            ('loop { break 1; }', 'exige un receveur'),
            ('let x = loop { break 1; };', 'sans usage explicite'),
        ]:
            self.reject(source, diagnostic)
        prefix = 'let mut p = pool<Int>(1); let a = new(p) Int(10); '
        self.reject(prefix + 'let x = loop { if true { break 1; } break &a; }; print(x);', 'même type et même mode')
        self.reject(prefix + 'let x = loop { a ->; break a; }; print(x);', 'implicite interdite')
        self.assertEqual(self.execute('let x = loop { break 17; }; print(x);').stdout, '17\n')

    def test_continue_and_break_use_different_join_points(self):
        prefix = 'let mut p = pool<Int>(1); let a = new(p) Int(10); '
        self.reject(prefix + 'loop { print(a); a ->; continue; }', 'entrée')
        self.reject(prefix + 'while true { a ->; print(a); continue; }', 'plus utilisable')
        self.reject(prefix + 'loop { if true { p.reset(); break; } break; } print(a);', 'reset interdit')

    def test_reborrow_reserves_writer_and_base_until_last_use(self):
        prefix = '''
            let mut p = pool<Int>(1);
            let mut a = new(p) Int(10);
            let mut writer = &mut a;
            let mut view = loop { break &mut *writer; };
        '''
        self.reject(prefix + 'print(writer); view.set(20);', 'emprunt actif')
        self.reject(prefix + 'print(a); view.set(20);', 'emprunt actif')
        self.reject(prefix + 'p.reset(); view.set(20);', 'reset interdit')
        self.assertEqual(self.execute(prefix + 'view.set(20); print(writer); a.set(30); print(a);').stdout,
                         '20\n30\n')

    def test_conditional_mutable_targets_remain_reserved(self):
        program = '''
            fn choose(n: Int) {
                let mut p = pool<Int>(2);
                let mut a = new(p) Int(10);
                let mut b = new(p) Int(20);
                let mut view = loop { if n == 0 { break &mut a; } break &mut b; };
                ACCESS
                view.set(30);
                print(a);
                print(b);
            }
            fn main() { choose(0); choose(1); }
        '''
        for name in ('a', 'b'):
            self.reject(program.replace('ACCESS', f'print({name});'), 'emprunt actif')
        self.assertEqual(self.execute(program.replace('ACCESS', '')).stdout, '30\n20\n10\n30\n')

    def test_reset_after_loop_result_depends_on_every_possible_pool(self):
        program = '''
            fn choose(p: &mut Pool<Int>, q: &mut Pool<Int>, n: Int) -> <- Int {
                let r = loop {
                    if n == 0 { let a = new(p) Int(10); break <- a; }
                    let b = new(q) Int(20); break <- b;
                };
                return <- r;
            }
            fn run(n: Int) {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let r = choose(&mut p, &mut q, n);
                OPERATIONS
            }
            fn main() { run(0); run(1); }
        '''
        self.reject(program.replace('OPERATIONS', 'p.reset(); print(r);'), 'reset interdit')
        result = self.execute(program.replace('OPERATIONS', 'print(r); p.reset(); q.reset();'))
        self.assertEqual(result.stdout, '10\n20\n')
        self.assertEqual(self.destructions(result), ['destroy a=10', 'destroy b=20'])

    def test_loop_constraints_include_reset_and_reborrow(self):
        prefix = '''
            fn borrow(a: &mut Int) -> &mut Int {
                let mut view = loop { break &mut *a; };
                return view;
            }
            fn use_view(p: &mut Pool<Int>, a: &mut Int) {
                let mut view = loop { break borrow(a); };
                p.reset();
                view.set(20);
            }
            let mut p = pool<Int>(1); let mut q = pool<Int>(1);
        '''
        self.reject(prefix + 'let mut a = new(p) Int(10); use_view(&mut p, &mut a);', 'reset interdit')
        self.assertEqual(self.execute(prefix + 'let mut a = new(q) Int(10); use_view(&mut p, &mut a); print(a);').stdout,
                         '20\n')

    def test_replacement_after_conditional_move_requires_live_destination(self):
        self.reject('''
            let mut p = pool<Int>(3);
            let mut a = new(p) Int(10);
            let recu = if true { a ->; <- a } else { let b = new(p) Int(20); <- b };
            let nouveau = new(p) Int(30);
            a = <- nouveau;
            print(recu); print(a);
        ''', 'plus utilisable')
        result = self.execute('''
            fn run(n: Int) {
                let mut p = pool<Int>(2); let mut a = new(p) Int(10);
                if n == 0 { a ->; let r = <- a; print(r); return; }
                let nouveau = new(p) Int(30); a = <- nouveau; print(a);
            }
            fn main() { run(0); run(1); }
        ''')
        self.assertEqual(result.stdout, '10\n30\n')

    def test_return_and_continue_do_not_complete_replacement(self):
        program = '''
            fn run(n: Int) {
                let mut p = pool<Int>(2);
                let mut a = new(p) Int(10);
                let view = &a;
                let mut passage = 0;
                a = loop {
                    let candidate = new(p) Int(20);
                    if n == 0 { return; }
                    if passage == 0 { passage = 1; continue; }
                    print(view);
                    break <- candidate;
                };
                print(a);
            }
            fn main() { run(0); run(1); }
        '''
        result = self.execute(program)
        self.assertEqual(result.stdout, '10\n20\n')
        self.assertEqual(self.destructions(result), [
            'destroy candidate=20', 'destroy a=10',
            'destroy candidate=20', 'destroy a=10', 'destroy candidate=20',
        ])
        self.reject(program.replace('print(a);', 'print(view); print(a);'), 'emprunt actif')

    def test_copy_if_result_updates_int_in_place(self):
        prefix = 'let mut p = pool<Int>(1); let mut a = new(p) Int(10); '
        result = self.execute(prefix + 'address(a); a = if true { 20 } else { 30 }; address(a); print(a);')
        before, after, value = result.stdout.splitlines()
        self.assertEqual((before, value), (after, '20'))
        self.assertEqual(self.destructions(result), ['destroy a=20'])
        self.reject(prefix + 'let r = if true { a } else { 20 }; print(r);', 'implicite interdite')

    def test_statement_transfer_is_distinct_from_if_tail(self):
        prefix = 'let mut p = pool<Int>(1); '
        self.reject(prefix + 'let x = if true { let a = new(p) Int(10); <- a; } '
                    'else { let b = new(p) Int(20); <- b }; print(x);', 'sans point-virgule')
        self.reject(prefix + 'let x = { let a = new(p) Int(10); <- a; }; print(x);',
                    'sans point-virgule')
        compiler, _ = compile_program(prefix + '{ let a = new(p) Int(10); <- a; }')
        self.assertEqual(len(compiler.warnings), 1)

    def test_explicit_ancestor_receiver_validates_destination(self):
        result = self.execute('''
            let mut p = pool<Int>(2);
            let mut r = new(p) Int(10);
            print(r);
            { { let a = new(p) Int(20); address(a); r = <- a; } }
            address(r); print(r);
        ''')
        initial, a, b, value = result.stdout.splitlines()
        self.assertEqual(initial, '10')
        self.assertEqual((a, b, value), (a, a, '20'))
        self.assertEqual(self.destructions(result), ['destroy r=10', 'destroy a=20'])
        self.reject('''
            let mut p = pool<Int>(1); let mut r = new(p) Int(10); print(r);
            { let mut q = pool<Int>(1); { let a = new(q) Int(20); r = <- a; } }
            print(r);
        ''', 'ne survit pas dans le scope')

    def test_cursor_first_then_hole_then_group_reset(self):
        result = self.execute('''
            let mut p = pool<Int>(3);
            let a = new(p) Int(10); let b = new(p) Int(20); address(a); print(b);
            drop(-> a);
            let c = new(p) Int(30); address(c);
            let d = new(p) Int(40); address(d);
            p.reset();
            let e = new(p) Int(50); address(e);
        ''')
        a, b, c, d, e = result.stdout.splitlines()
        self.assertEqual(b, '20')
        self.assertNotEqual(a, c)
        self.assertEqual((a, d, e), (a, a, a))
        self.assertEqual(result.stderr.splitlines()[:9], [
            'destroy a=10', 'reuse d',
            'destroy d=40', 'destroy c=30', 'destroy b=20',
            'reclaim c', 'reclaim b', 'reclaim d', 'reset',
        ])

    def test_nested_reset_rewinds_across_hole_after_destroying_inner_then_outer(self):
        result = self.execute("""
            let mut p = pool<Int>(3);
            let mut r = new(p) Int(10);
            address(r);
            {
                let temp = new(p) Int(20);
                print(temp);
                let result = new(p) Int(30);
                r = <- result;
                print(r);
                p.reset();
            }
            let next = new(p) Int(40);
            address(next);
        """)
        old, temp, received, next_address = result.stdout.splitlines()
        self.assertEqual((temp, received), ('20', '30'))
        self.assertEqual(old, next_address)
        self.assertEqual(result.stderr.splitlines(), [
            'destroy r=10', 'destroy temp=20', 'destroy result=30',
            'reclaim result', 'reclaim temp', 'reclaim r', 'reset',
            'destroy next=40', 'reclaim next',
        ])

    def test_generated_reset_trace_against_block_model(self):
        rng = random.Random(20261103)
        for _ in range(8):
            n = rng.randrange(2, 8)
            choice = rng.randrange(2)
            # The model records live labels per block, independently of C
            # guards, the free index, and physical slot order.
            parents = [f'destroy old={n}']
            iteration = [f'destroy temp={n + 1}', f'destroy candidate={n + 2}']
            source = f'''
                let mut p = pool<Int>(3);
                let mut old = new(p) Int({n});
                print(old);
                let r = loop {{
                    let temp = new(p) Int({n + 1});
                    print(temp);
                    let candidate = new(p) Int({n + 2});
                    if {choice} == 0 {{ break <- candidate; }}
                    break 0;
                }};
                print(r); p.reset();
            '''
            # The scalar branch is the generated invalid neighbor of
            # the valid program, whose alternate exit is also an allocation.
            self.reject(source, 'même type et même mode')
            source = source.replace('break 0;', 'break <- temp;')
            selected = iteration.pop(1 - choice)
            expected = [*reversed(iteration), selected, *reversed(parents)]
            self.assertEqual(self.destructions(self.execute(source)), expected)
