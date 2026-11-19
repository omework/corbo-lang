"""Reusable closures exercise the ordinary value and borrow rules."""
import unittest

from crust import Error, verify_program
import test_type_features


class ClosureTests(unittest.TestCase):
    native = test_type_features.TypeFeatureTests.native

    def test_closure_calls_a_structurally_contracted_function(self):
        contracts = test_type_features.FunctionTypeContractTests
        source = contracts.declarations + contracts.contract + """
            fn main() {
                let counter = Counter { n:42 };
                let view = &counter;
                let read = || { inspect(view) };
                print(read());
                print(read());
            }
        """
        self.assertEqual(self.native(source).stdout, '42\n42\n42\n42\n')
        with self.assertRaisesRegex(Error, 'non Copy.*exige move'):
            verify_program(source.replace('inspect(view)', 'inspect(&counter)'))

    def test_captured_reference_to_local_scalar_keeps_its_loan(self):
        source = '''
            fn main() {
                let mut n: i64 = 42;
                let vue = &n;
                let read = || { *vue };
                print(read());
                drop(read);
                n = 7;
                print(n);
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n7\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(read());', 'n = 8; print(read());'))
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program('''
                fn main() {
                    let read = { let n: i64 = 42; let vue = &n; || { *vue } };
                    print(read());
                }
            ''')

    def test_mutable_reference_moves_into_a_reusable_read_closure(self):
        source = '''
            fn main() {
                let mut n: i64 = 42;
                let vue = &mut n;
                let read = move || { *vue };
                print(read());
                print(read());
                drop(read);
                n = 7;
                print(n);
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n42\n7\n')
        with self.assertRaisesRegex(Error, 'exige move'):
            verify_program(source.replace('move ||', '||'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('print(read());', 'print(*vue);', 1))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(read());', 'print(n);', 1))

    def test_moved_mutable_structure_reference_can_be_read_through_closure(self):
        source = """
            struct Counter { n:i64 }
            fn main() {
                let mut counter=Counter { n:42 };
                let view=&mut counter;
                let read=move || { view.n };
                print(read());
                print(read());
                drop(read);
                counter.n=7;
                print(counter.n);
            }
        """
        self.assertEqual(self.native(source).stdout, '42\n42\n7\n')
        with self.assertRaisesRegex(Error, 'exige move'):
            verify_program(source.replace('move ||', '||'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('print(read());', 'print(view.n);', 1))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(read());', 'counter.n=7; print(read());', 1))

    def test_owned_local_structure_is_transferred_into_the_closure(self):
        source = '''
            struct Point { x: i64 }
            fn main() {
                let point = Point { x: 42 };
                let read = move || { point.x };
                print(read());
                print(read());
            }
        '''
        run = self.native(source)
        self.assertEqual(run.stdout, '42\n42\n')
        self.assertEqual(run.stderr.count('destroy point=Point'), 1)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('print(read());', 'print(point.x);', 1))

    def test_copy_capture_is_taken_when_the_closure_is_created(self):
        source = '''
            fn main() {
                let mut n: i64 = 40;
                let add = |x: i64| -> i64 { n + x };
                n = 100;
                print(add(2));
                print(add(3));
                print(n);
                print((|x: i64| { x * 2 })(21));
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n43\n100\n42\n')

    def test_closure_parameter_preserves_concrete_captures(self):
        source = '''
            fn twice(f: closure(i64) -> i64, x: i64) -> i64 {
                let first = f(x);
                f(first)
            }
            fn main() {
                let offset: i64 = 2;
                let add = |x: i64| { x + offset };
                let multiply = |x: i64| { x * 2 };
                print(twice(add, 38));
                print(twice(multiply, 5));
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n20\n')
        with self.assertRaisesRegex(Error, 'signature closure'):
            verify_program(source.replace('closure(i64) -> i64', 'closure(i32) -> i64'))

    def test_async_function_can_receive_and_reuse_a_scalar_closure(self):
        source = '''
            async fn twice(f: closure(i64) -> i64) -> i64 {
                yield;
                f(f(38))
            }
            fn main() {
                let offset: i64 = 2;
                let add = |x: i64| { x + offset };
                let h = runtime::spawn(twice(add));
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(0); } }
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n')

    def test_async_closure_preserves_a_local_scalar_loan_across_yield(self):
        source = """
            async fn read(f: closure() -> i64) -> i64 {
                yield;
                f()
            }
            fn main() {
                let mut n: i64 = 42;
                let view = &n;
                let captured = || { *view };
                let h = runtime::spawn(read(captured));
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(0); } }
                n = 7;
                print(n);
            }
        """
        self.assertEqual(self.native(source).stdout, '42\n7\n')
        with self.assertRaises(Error):
            verify_program(source.replace('match h.join()', 'n = 8; match h.join()'))

    def test_unused_closure_parameter_can_take_a_borrowed_structure(self):
        source = """
            struct Point { n:i64 }
            fn unused(f: closure(&Point) -> i64, p: &Point) -> i64 { f(p) }
            fn main() {}
        """
        verify_program(source)
        with self.assertRaisesRegex(Error, 'allocation Point'):
            verify_program(source.replace('f(p)', 'f(42)'))

    def test_closure_signature_can_return_a_structure(self):
        source = """
            struct Point { n:i64 }
            fn read(f: closure() -> Point) -> i64 { let p=f(); p.n }
        """
        verify_program(source + 'fn main() {}')
        with self.assertRaisesRegex(Error, 'champ inconnu'):
            verify_program(source.replace('p.n', 'p.missing') + 'fn main() {}')
        run = self.native(source + """
            fn main() {
                let make = || -> Point { Point { n:42 } };
                print(read(make));
            }
        """)
        self.assertEqual(run.stdout, '42\n')

    def test_closure_signature_relays_borrowed_result(self):
        relay = """
            fn relay(f: closure(&i64) -> &i64, p: &i64) -> &i64 { f(p) }
        """
        verify_program(relay + 'fn main() {}')
        with self.assertRaises(Error):
            verify_program(relay.replace('f(p)', 'f(42)') + 'fn main() {}')
        source = relay + """
            fn main() {
                let mut n:i64=42;
                let identity=|v: &i64| -> &i64 { v };
                let view=relay(identity, &n);
                print(*view);
                n=7;
                print(n);
            }
        """
        self.assertEqual(self.native(source).stdout, '42\n7\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(*view);', 'n=8; print(*view);'))

    def test_returned_scalar_capture_survives_closure_drop(self):
        source = """
            fn main() {
                let mut n:i64=42;
                let original=&n;
                let read=|| -> &i64 { original };
                let view=read();
                drop(read);
                print(*view);
                n=7;
                print(n);
            }
        """
        self.assertEqual(self.native(source).stdout, '42\n7\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(*view);', 'n=8; print(*view);'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn escape() -> &i64 {
                    let n:i64=42;
                    let original=&n;
                    let read=|| -> &i64 { original };
                    read()
                }
                fn main() {}
            """)

    def test_closure_can_return_shared_view_of_exclusive_capture(self):
        scalar = """
            fn main() {
                let mut n:i64=42;
                let original=&mut n;
                let read=move || -> &i64 { original };
                let view=read();
                drop(read);
                print(*view);
                n=7;
                print(n);
            }
        """
        structure = """
            struct Counter { n:i64 }
            fn main() {
                let mut counter=Counter { n:42 };
                let original=&mut counter;
                let read=move || -> &Counter { original };
                let view=read();
                print(view.n);
                drop(read);
                counter.n=7;
                print(counter.n);
            }
        """
        for source, access, write in ((scalar, 'print(*view);', 'n=8;'),
                                      (structure, 'print(view.n);', 'counter.n=8;')):
            with self.subTest(access=access):
                self.assertEqual(self.native(source).stdout, '42\n7\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace(access, write + access))
        detached = structure.replace('print(view.n);\n                drop(read);',
                                     'drop(read); print(view.n);')
        self.assertEqual(self.native(detached).stdout, '42\n7\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(detached.replace('print(view.n);', 'counter.n=8; print(view.n);'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(structure.replace('print(view.n);', 'print(counter.n); print(view.n);'))
        relayed = """
            struct Counter { n:i64 }
            fn read(original:&mut Counter) -> &Counter {
                let closure_read=move || -> &Counter { original };
                closure_read()
            }
            fn main() {
                let mut counter=Counter { n:42 };
                let view=read(&mut counter);
                print(view.n);
                counter.n=7;
                print(counter.n);
            }
        """
        self.assertEqual(self.native(relayed).stdout, '42\n7\n')

    def test_unused_scalar_closure_parameter_body_is_type_checked(self):
        source = 'fn unused(f:closure(i64)->i64)->i64 { f(42) } fn main() {}'
        verify_program(source)
        with self.assertRaises(Error):
            verify_program(source.replace('f(42)', 'f(true)'))

    def test_shared_capture_preserves_the_pool_loan(self):
        source = '''
            fn main() {
                let mut pool_values = pool<i64>(1);
                let n = pool_values.new(42);
                let vue = n.vref();
                let read = || { *vue };
                print(read());
                drop(read);
                drop(n);
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n')
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program(source.replace('print(read());', 'drop(n); print(read());'))
        copied = source.replace('let read = ||', 'let read = move ||').replace(
            'print(read());', 'print(read()); print(*vue);')
        self.assertEqual(self.native(copied).stdout, '42\n42\n')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program('''
                fn main() {
                    let read = {
                        let mut values = pool<i64>(1);
                        let n = values.new(42);
                        let vue = n.vref();
                        || { *vue }
                    };
                    print(read());
                }
            ''')

    def test_owner_capture_transfers_cleanup_and_requires_move(self):
        source = '''
            fn main() {
                let mut pool_values = pool<i64>(1);
                let n = pool_values.new(42);
                let read = move || { *n };
                print(read());
                print(read());
                drop(read);
                let next = pool_values.new(9);
                print(*next);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.stdout, '42\n42\n9\n')
        self.assertEqual(run.stderr.count('destroy n='), 1)
        with self.assertRaisesRegex(Error, 'exige move'):
            verify_program(source.replace('move ||', '||'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('print(read());', 'print(*n);', 1))

    def test_scalar_move_and_returns(self):
        source = '''
            fn main() {
                let n: i64 = 42;
                let choose = move |use_capture: bool| {
                    if use_capture { return n; }
                    2
                };
                print(choose(true));
                print(choose(false));
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n2\n')
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('print(choose(true));', 'print(n);'))
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(source.replace('return n;', 'print(n); return true;'))
