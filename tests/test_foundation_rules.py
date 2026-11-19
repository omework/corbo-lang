"""Executable checks of F4 and F5 against the native C backend."""

from functools import partial, update_wrapper
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from crust import Error, compile_source, verify_program

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)


class FoundationTests(unittest.TestCase):
    def test_local_structure_copy_is_independent_and_reuses_dead_storage(self):
        run = self.native('''
            struct Point { x: Int, y: Int }
            fn main() {
                let original = Point { x: 10, y: 20 };
                address(original);
                let mut duplicate = copy(original);
                address(duplicate);
                duplicate.x = 30;
                print(original.x);
                print(duplicate.x);
                print(duplicate.y);
                drop(-> duplicate);
                let again = copy(original);
                address(again);
                print(again.x);
            }
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        original, duplicate, x, changed, y, again, restored = run.stdout.splitlines()
        self.assertNotEqual(original, duplicate)
        self.assertEqual(duplicate, again)
        self.assertEqual((x, changed, y, restored), ('10', '30', '20', '10'))
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy')],
                         ['destroy duplicate=Point', 'destroy again=Point', 'destroy original=Point'])

    def test_local_structure_copies_transfer_without_moving(self):
        bodies = [
            '''let result = { let original = Point { x: 10 };
                let duplicate = copy(original); address(duplicate); <- duplicate };''',
            '''let original = Point { x: 10 }; let mut i = 0;
                let result = loop { let duplicate = copy(original); address(duplicate);
                    i = i + 1; if i < 3 { continue; } break <- duplicate; };''',
            '''let result = make();''',
        ]
        for body, copies in zip(bodies, (1, 3, 1)):
            with self.subTest(body=body):
                run = self.native('''
                    struct Point { x: Int }
                    fn make() -> <- Point {
                        let original = Point { x: 10 };
                        let duplicate = copy(original);
                        address(duplicate);
                        return <- duplicate;
                    }
                    fn main() { ''' + body + ''' address(result); print(result.x); }
                ''')
                self.assertEqual(run.returncode, 0, run.stderr)
                addresses = run.stdout.splitlines()
                self.assertEqual(addresses.pop(), '10')
                self.assertEqual(len(addresses), copies + 1)
                self.assertEqual(len(set(addresses)), 1)
                self.assertEqual(run.stderr.count('destroy duplicate=Point'), copies)
                self.assertEqual(run.stderr.count('reclaim duplicate'), 1)

    def test_local_structure_copy_keeps_shared_target_across_return(self):
        source = '''
            struct View { target: &Int }
            fn make(target: &Int) -> <- View {
                let original = View { target: target };
                let duplicate = copy(original);
                address(duplicate);
                return <- duplicate;
            }
            fn main() {
                let mut numbers = pool<Int>(1);
                let number = numbers.new(10);
                let view = make(&number);
                address(view);
                print(view);
                drop(-> view);
                drop(-> number);
                let reused = numbers.new(20);
                print(*reused);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        output = run.stdout.splitlines()
        self.assertEqual(output[0], output[1])
        self.assertEqual(output[2:], ['View(10)', '20'])
        for invalid in (source.replace('print(view);', 'drop(-> number); print(view);'),
                        source.replace('print(view);', 'numbers.reset(); print(view);')):
            with self.subTest(source=invalid), self.assertRaisesRegex(Error, 'emprunt|encore .*utilisée'):
                verify_program(invalid)
        with self.assertRaisesRegex(Error, 'locale|survit|durable'):
            verify_program('''
                struct Point { x: Int }
                struct View { target: &Point }
                fn make() -> <- View {
                    let target = Point { x: 1 };
                    let original = View { target: &target };
                    let duplicate = copy(original);
                    return <- duplicate;
                }
                fn main() { let view = make(); drop(-> view); }
            ''')

    def test_local_structure_copy_from_parameter_uses_receiver_storage(self):
        source = '''
            struct Point { x: Int }
            fn duplicate(original: &Point) -> <- Point {
                let result = copy(original);
                address(result);
                return <- result;
            }
            fn relay(original: &Point) -> <- Point {
                let result = duplicate(original);
                address(result);
                return <- result;
            }
            fn main() {
                let result = {
                    let original = Point { x: 10 };
                    address(original);
                    let duplicate = relay(&original);
                    <- duplicate
                };
                address(result);
                print(result.x);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, copied, relayed, received, value = run.stdout.splitlines()
        self.assertNotEqual(original, copied)
        self.assertEqual((copied, relayed, value), (received, received, '10'))
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy')],
                         ['destroy original=Point', 'destroy result=Point'])
        with self.assertRaisesRegex(Error, 'A<Point>|allocation'):
            verify_program(source.replace('let result = {', 'let result: A<Point> = {'))

    def test_local_structure_copied_parameter_retains_target_without_original(self):
        source = '''
            struct View { target: &Int }
            fn duplicate(original: &View) -> <- View {
                let result = copy(original);
                return <- result;
            }
            fn relay(original: &View) -> <- View {
                let result = duplicate(original);
                return <- result;
            }
            fn main() {
                let mut numbers = pool<Int>(1);
                let number = numbers.new(10);
                let result = {
                    let original = View { target: &number };
                    let result = relay(&original);
                    <- result
                };
                print(result);
                drop(-> result);
                drop(-> number);
            }
        '''
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, 'View(10)\n'), run.stderr)
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy')],
                         ['destroy original=View', 'destroy result=View', 'destroy number=10'])
        for effect in ('drop(-> number);', 'numbers.reset();'):
            with self.subTest(effect=effect), self.assertRaisesRegex(Error, 'emprunt|encore .*utilisée'):
                verify_program(source.replace('print(result);', effect + 'print(result);'))

    def test_local_structure_copy_rejects_noncopy_fields_and_active_mutation(self):
        for typ, field in (('&mut Int', '&mut number'), ('A<Int>', '<- number')):
            with self.subTest(typ=typ), self.assertRaisesRegex(Error, 'non copiable'):
                verify_program('''
                    struct Holder { value: ''' + typ + ''' }
                    fn main() {
                        let mut numbers = pool<Int>(1);
                        let mut number = numbers.new(10);
                        let original = Holder { value: ''' + field + ''' };
                        let duplicate = copy(original);
                        drop(-> duplicate);
                    }
                ''')
        with self.assertRaisesRegex(Error, 'emprunt|réserv'):
            verify_program('''
                struct Point { x: Int }
                fn main() {
                    let mut original = Point { x: 1 };
                    let mut view = &mut original;
                    let duplicate = copy(original);
                    view.x = 2;
                    drop(-> duplicate);
                }
            ''')

    def test_local_structure_return_through_loop_preserves_reservation(self):
        source = '''
            struct Point { x: Int }
            fn create(flag: Int) -> <- Point {
                let mut iteration = 0;
                let result = loop {
                    let value = Point { x: iteration };
                    address(value);
                    iteration = iteration + 1;
                    if iteration < 3 { continue; }
                    if flag == 1 { return <- value; }
                    break <- value;
                };
                return <- result;
            }
            fn main() {
                let first = create(1);
                address(first);
                print(first.x);
                drop(-> first);
                let second = create(0);
                address(second);
                print(second.x);
                drop(-> second);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        output = run.stdout.splitlines()
        self.assertEqual((output[4], output[9]), ('2', '2'))
        addresses = output[:4] + output[5:9]
        self.assertEqual(len(set(addresses)), 1)
        self.assertEqual(run.stderr.count('destroy value=Point'), 6)
        self.assertEqual(run.stderr.count('reclaim value'), 2)

        with self.assertRaisesRegex(Error, 'locale|durable|survit'):
            verify_program('''
                struct Point { x: Int }
                struct View { target: &Point }
                fn create() -> <- View {
                    loop {
                        let p = Point { x: 1 };
                        let view = View { target: &p };
                        return <- view;
                    }
                }
                fn main() { let result = create(); drop(-> result); }
            ''')
        direct = source.replace('let result = loop {', 'loop {').replace(
            'if flag == 1 { return <- value; }\n                    break <- value;', 'return <- value;').replace(
            '};\n                return <- result;', '}')
        run = self.native(direct)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr.count('destroy value=Point'), 6)
        self.assertEqual(run.stderr.count('reclaim value'), 2)

    def test_local_reservation_cleanup_on_early_function_return(self):
        source = '''
            struct Holder { value: A<Int> }
            fn run(flag: Int) -> Int {
                let mut numbers = pool<Int>(1);
                let mut iteration = 0;
                let result = loop {
                    if flag == 0 { return 11; }
                    let number = numbers.new(iteration);
                    let holder = Holder { value: <- number };
                    iteration = iteration + 1;
                    if iteration < 2 { continue; }
                    if flag == 1 { return 22; }
                    break <- holder;
                };
                drop(-> result);
                return 33;
            }
            fn main() {
                print(run(0));
                print(run(1));
                print(run(2));
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '11\n22\n33\n')
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        expected = ['destroy number=0', 'destroy holder=Holder',
                    'destroy number=1', 'destroy holder=Holder']
        self.assertEqual(destroyed, expected * 2)

    def test_local_structure_constructed_before_continue_drops_owned_fields(self):
        source = '''
            struct Holder { value: A<Int> }
            fn main() {
                let mut numbers = pool<Int>(1);
                let mut iteration = 0;
                let result = loop {
                    let number = numbers.new(iteration);
                    let holder = Holder { value: <- number };
                    address(holder);
                    iteration = iteration + 1;
                    if iteration < 3 { continue; }
                    break <- holder;
                };
                address(result);
                drop(-> result);
                let last = numbers.new(99);
                print(*last);
                drop(-> last);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        a, b, c, result, value = run.stdout.splitlines()
        self.assertEqual((a, b, c, value), (result, result, result, '99'))
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed, ['destroy number=0', 'destroy holder=Holder',
                                     'destroy number=1', 'destroy holder=Holder',
                                     'destroy number=2', 'destroy holder=Holder', 'destroy last=99'])
        self.assertEqual(run.stderr.count('reclaim holder'), 1)

    def test_local_structure_result_relays_keep_identity_and_borrow(self):
        source = '''
            struct Point { x: Int }
            fn create() -> <- Point {
                let value = Point { x: 10 };
                address(value);
                return <- value;
            }
            fn relay() -> <- Point {
                let value = create();
                address(value);
                return <- value;
            }
            fn main() {
                let result = {
                    let value = relay();
                    address(value);
                    <- value
                };
                address(result);
                print(result.x);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        a, b, c, d, value = run.stdout.splitlines()
        self.assertEqual((a, b, c, value), (d, d, d, '10'))
        self.assertEqual(run.stderr.count('destroy value=Point'), 1)
        borrowed = '''
            struct Point { x: Int }
            struct View { target: &Point }
            fn create(target: &Point) -> <- View {
                let result = View { target: target };
                return <- result;
            }
            fn relay(target: &Point) -> <- View {
                let result = create(target);
                return <- result;
            }
            fn main() {
                let p = Point { x: 10 };
                let view = relay(&p);
                drop(-> view);
                print(p.x);
                drop(-> p);
            }
        '''
        run = self.native(borrowed)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '10\n')
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program(borrowed.replace('drop(-> view);\n                print(p.x);\n                drop(-> p);',
                                            'drop(-> p); drop(-> view);'))

    def test_local_structure_function_return_keeps_caller_storage(self):
        source = '''
            struct Point { x: Int }
            fn create(flag: Int) -> <- Point {
                let temporary = Point { x: 7 };
                print(temporary.x);
                if flag == 1 {
                    let first = Point { x: 10 };
                    address(first);
                    return <- first;
                }
                let second = Point { x: 20 };
                address(second);
                return <- second;
            }
            fn main() {
                let result = create(FLAG);
                address(result);
                print(result.x);
                drop(-> result);
            }
        '''
        for flag, value, label in ((1, '10', 'first'), (0, '20', 'second')):
            with self.subTest(flag=flag):
                run = self.native(source.replace('FLAG', str(flag)))
                self.assertEqual(run.returncode, 0, run.stderr)
                temporary, before, after, actual = run.stdout.splitlines()
                self.assertEqual((temporary, actual), ('7', value))
                self.assertEqual(before, after)
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
                self.assertEqual(destroyed, ['destroy temporary=Point', f'destroy {label}=Point'])
        with self.assertRaises(Error):
            verify_program(source.replace('FLAG', '1').replace('-> <- Point', '-> <- A<Point>'))
        with self.assertRaisesRegex(Error, 'locale|durable|survit'):
            verify_program('''
                struct Point { x: Int }
                struct View { target: &Point }
                fn create() -> <- View {
                    let p = Point { x: 1 };
                    let view = View { target: &p };
                    return <- view;
                }
                fn main() { let result = create(); drop(-> result); }
            ''')

    def test_local_structure_loop_conditional_breaks_share_reservation(self):
        source = '''
            struct Point { x: Int }
            fn main() {
                let flag = FLAG;
                let mut iteration = 0;
                let result = loop {
                    let temporary = Point { x: iteration };
                    print(temporary.x);
                    iteration = iteration + 1;
                    if iteration < 3 { continue; }
                    if flag == 1 {
                        let first = Point { x: 9 };
                        address(first);
                        break <- first;
                    } else {
                        let second = Point { x: 10 };
                        address(second);
                        break <- second;
                    }
                };
                address(result);
                print(result.x);
                drop(-> result);
            }
        '''
        for flag, value, label in ((1, '9', 'first'), (0, '10', 'second')):
            with self.subTest(flag=flag):
                run = self.native(source.replace('FLAG', str(flag)))
                self.assertEqual(run.returncode, 0, run.stderr)
                first, second, third, before, after, returned = run.stdout.splitlines()
                self.assertEqual((first, second, third, returned), ('0', '1', '2', value))
                self.assertEqual(before, after)
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
                self.assertEqual(destroyed, ['destroy temporary=Point'] * 3 + [f'destroy {label}=Point'])
        invalid = source.replace('FLAG', '1').replace('struct Point { x: Int }',
                   'struct Point { x: Int } struct Other { x: Int }').replace('second = Point', 'second = Other')
        with self.assertRaisesRegex(Error, 'type'):
            verify_program(invalid)

    def test_local_structure_loop_break_after_continue_and_slot_reuse(self):
        source = """
            struct Point { x: Int }
            fn main() {
                let mut iteration = 0;
                let result = loop {
                    let temporary = Point { x: iteration };
                    print(temporary.x);
                    iteration = iteration + 1;
                    if iteration < 3 { continue; }
                    let final = Point { x: 9 };
                    address(final);
                    break <- final;
                };
                address(result);
                print(result.x);
                drop(-> result);
                let next = Point { x: 10 };
                address(next);
                print(next.x);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, third, a, b, value, c, following = run.stdout.splitlines()
        self.assertEqual((first, second, third, value, following), ('0', '1', '2', '9', '10'))
        self.assertEqual((a, b), (c, c))
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed, ['destroy temporary=Point'] * 3 + ['destroy final=Point', 'destroy next=Point'])
        with self.assertRaises(Error):
            verify_program(source.replace('break <- final;', 'break final;'))
        with self.assertRaisesRegex(Error, 'emprunt|durable|survit'):
            verify_program('''
                struct Point { x: Int }
                struct View { target: &Point }
                fn main() {
                    let result = loop {
                        let temporary = Point { x: 1 };
                        let final = View { target: &temporary };
                        break <- final;
                    };
                    drop(-> result);
                }
            ''')

    def test_local_structure_conditional_result_uses_one_parent_slot(self):
        source = """
            struct Point { x: Int }
            fn main() {
                let flag = FLAG;
                let received = {
                    let result = if flag == 1 {
                        let temp = Point { x: 4 };
                        print(temp.x);
                        let first = Point { x: 10 };
                        address(first);
                        <- first
                    } else {
                        let temp = Point { x: 5 };
                        print(temp.x);
                        let second = Point { x: 20 };
                        address(second);
                        <- second
                    };
                    address(result);
                    <- result
                };
                address(received);
                print(received.x);
                drop(-> received);
            }
        """
        for flag, temporary, value, name in ((1, '4', '10', 'first'), (0, '5', '20', 'second')):
            with self.subTest(flag=flag):
                run = self.native(source.replace('FLAG', str(flag)))
                self.assertEqual(run.returncode, 0, run.stderr)
                temp, a, b, c, result = run.stdout.splitlines()
                self.assertEqual((temp, result), (temporary, value))
                self.assertEqual((a, b), (c, c))
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
                self.assertEqual(destroyed, ['destroy temp=Point', f'destroy {name}=Point'])
        invalid = source.replace('FLAG', '1').replace('struct Point { x: Int }',
                    'struct Point { x: Int } struct Other { x: Int }').replace('second = Point', 'second = Other')
        with self.assertRaisesRegex(Error, 'type'):
            verify_program(invalid)
        for replacement in ('local = <- allocated;', 'allocated = <- local;'):
            with self.subTest(replacement=replacement), self.assertRaisesRegex(Error, 'type'):
                verify_program('''
                    struct Point { x: Int }
                    fn main() {
                        let mut points = pool<Point>(1);
                        let mut local = Point { x: 1 };
                        let mut allocated = points.new(x: 2);
                        print(local.x); print(allocated.x);
                ''' + replacement + '}')

    def test_local_structure_nested_transfer_preserves_address_and_cleanup(self):
        source = """
            struct Point { x: Int }
            fn main() {
                let received = {
                    let outer = Point { x: 7 };
                    print(outer.x);
                    let intermediate = {
                        let temporary = Point { x: 8 };
                        print(temporary.x);
                        let value = Point { x: 9 };
                        address(value);
                        <- value
                    };
                    address(intermediate);
                    <- intermediate
                };
                address(received);
                print(received.x);
                drop(-> received);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, a, b, c, result = run.stdout.splitlines()
        self.assertEqual((first, second, result), ('7', '8', '9'))
        self.assertEqual((a, b), (c, c))
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed, ['destroy temporary=Point', 'destroy outer=Point', 'destroy value=Point'])
        with self.assertRaisesRegex(Error, 'emprunt|durable|survit'):
            verify_program("""
                struct Point { x: Int }
                struct View { target: &Point }
                fn main() {
                    let received = {
                        let local = Point { x: 9 };
                        let view = View { target: &local };
                        <- view
                    };
                    drop(-> received);
                }
            """)

    def test_local_structure_literal_storage_and_borrows(self):
        source = """
            struct Point { x: Int, y: Int }
            struct Holder { value: A<Int> }
            fn main() {
                let mut numbers = pool<Int>(1);
                let mut p: Point = Point { x: 10, y: 20 };
                let view = &p.x;
                print(*view);
                p.x = 30;
                {
                    let number = numbers.new(7);
                    let holder = Holder { value: <- number };
                    print(p.x);
                    drop(-> holder);
                }
                let reused = numbers.new(9);
                print(*reused);
                drop(-> reused);
                drop(-> p);
                let zero = Point {};
                print(zero.x);
                print(zero.y);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '10\n30\n9\n0\n0\n')
        for old, new in (
            ('p.x = 30;', 'p.x = 30; print(*view);'),
            ('drop(-> p);', 'drop(-> p); print(p.x);'),
            ('p: Point', 'p: A<Point>'),
            ('x: 10, y: 20', 'x: 10, x: 20'),
        ):
            with self.subTest(new=new), self.assertRaises(Error):
                verify_program(source.replace(old, new))

    def test_storage_draft_typed_pool_reuses_an_interior_slot_without_moving_others(self):
        source = """
            struct Point { x: Int, y: Int }
            fn creer(points: &mut Pool<Point>, x: Int) -> <- A<Point> {
                let point = points.new(x: x, y: 20);
                return <- point;
            }
            fn main() {
                let mut points = pool<Point>(2);
                let a = creer(&mut points, 10);
                let b = creer(&mut points, 30);
                address(a);
                address(b);
                drop(-> a);
                let c = creer(&mut points, 50);
                address(c);
                address(b);
                print(b.x);
                print(c.x);
                drop(-> c);
                drop(-> b);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        a, b, c, b_after, *fields = run.stdout.splitlines()
        self.assertEqual((c, b_after, fields), (a, b, ['30', '50']))
        self.assertNotEqual(a, b)
        exhausted = self.native(source.replace('drop(-> a);', '').replace('drop(-> b);', 'drop(-> b); drop(-> a);'))
        self.assertEqual(exhausted.returncode, 1, exhausted.stderr)
        self.assertIn('pool capacity exceeded', exhausted.stderr)
        for invalid in ('pool<Point>()', 'pool<Point>(0)'):
            with self.subTest(invalid=invalid), self.assertRaises(Error):
                verify_program(source.replace('pool<Point>(2)', invalid))
        with self.assertRaisesRegex(Error, 'attendu'):
            verify_program(source.replace('drop(-> a)', 'drop(a)'))
        with self.assertRaisesRegex(Error, 'locale|non durable|survit'):
            verify_program('''
                struct Point { x: Int }
                fn escape() -> <- A<Point> {
                    let mut points = pool<Point>(1);
                    let p = points.new(x: 1);
                    return <- p;
                }
                fn main() {}
            ''')

    def test_storage_draft_drop_consumes_copyable_locals(self):
        source = """
            fn main() {
                let first = [1; 4096];
                print(first[0]);
                drop(-> first);
                let second = [2; 4096];
                print(second[0]);
                let count = 3;
                print(count);
                drop(-> count);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n2\n3\n')
        for statement, diagnostic in (
            ('print(first[0]);', 'plus utilisable'),
            ('drop(-> first);', 'plus utilisable'),
            ('let copy = copy(first);', 'plus utilisable'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('let second =', statement + ' let second ='))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('drop(-> first);', 'let view = &first[0]; drop(-> first); print(*view);'))

    def native(self, source, stdin=None, transform=None):
        compiler = shutil.which("clang") or shutil.which("cc")
        if compiler is None:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as folder:
            c_path = Path(folder) / "test.c"
            executable = Path(folder) / "test"
            code = compile_source(source)
            c_path.write_text(transform(code) if transform is not None else code)
            build = subprocess.run(
                [compiler, "-std=c11", "-O2", "-fsanitize=undefined",
                 "-fno-sanitize-recover=all", str(c_path), "-o", str(executable)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            return subprocess.run([str(executable)], input=stdin, capture_output=True, text=True, timeout=10)

    def test_recursive_handle_field_layout_is_pointer_sized(self):
        source = """
            struct Left { right: Right }
            struct Right { marker: Int, left: A<Left> }
            enum Node { End { value: Int }, Link { next: A<Node>, marker: Int } }
            let mut structs = pool<Left>(1);
            let mut nodes = pool<Node>(1);
            let end = new(nodes) Node.End { value: 7 };
            match &end {
                Node.End { value: v } => { print(v); },
                Node.Link { next: _, marker: _ } => {}
            }
        """
        code = compile_source(source)
        self.assertIn('source_pool_layout(1, sizeof(int) + sizeof(Cell *))', code)
        self.assertIn('source_pool_layout(1, sizeof(Cell *) + sizeof(int))', code)
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'cycle de champs'):
            verify_program('struct Left { right: Right } struct Right { left: Left }')
        with self.assertRaisesRegex(Error, 'type de handle inconnu'):
            verify_program('struct Left { target: A<Missing> }')
        with self.assertRaisesRegex(Error, 'transfert explicite'):
            verify_program(source + 'let next = new(nodes) Node.Link { next: end, marker: 1 };')

    def test_recursive_owned_fields_drop_children_once_in_origin_pools(self):
        source = """
            enum Node { End { value: Int }, Link { next: A<Node> } }
            let mut ends = pool<Node>(1);
            let mut links = pool<Node>(2);
            let end = new(ends) Node.End { value: 7 };
            let mid = new(links) Node.Link { next: <- end };
            let top = new(links) Node.Link { next: <- mid };
            CHECK
            drop(-> top);
            let again = new(ends) Node.End { value: 9 };
            match &again {
                Node.End { value: value } => { print(value); },
                Node.Link { next: _ } => {}
            }
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed[:3], ['destroy end=Node.End', 'destroy mid=Node.Link', 'destroy top=Node.Link'])
        self.assertEqual(destroyed.count('destroy end=Node.End'), 1)
        for statement, diagnostic in (
            ('ends.reset();', 'handles encore stockés dans un agrégat'),
            ('drop(-> end);', 'plus utilisable'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'pool d’élément ne survit pas'):
            verify_program("""
                enum Node { End, Link { next: A<Node> } }
                let mut links = pool<Node>(1);
                let root = {
                    let mut local = pool<Node>(1);
                    let end = new(local) Node.End;
                    let link = new(links) Node.Link { next: <- end };
                    <- link
                };
                drop(-> root);
            """)

    def test_reset_owned_structure_reclaims_child_in_different_pool(self):
        source = """
            struct Leaf { value: Int }
            struct Root { next: A<Leaf>, marker: Int }
            let mut leaves = pool<Leaf>(1);
            let mut roots = pool<Root>(1);
            let leaf = leaves.new(value: 7);
            let root = roots.new(next: <- leaf, marker: 9);
            print(root.marker);
            roots.reset();
            let again = leaves.new(value: 11);
            print(again.value);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '9\n11\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy leaf=Leaf\n'), 1)
        with self.assertRaisesRegex(Error, 'structure non copiable'):
            verify_program(source.replace('print(root.marker);', 'let copied = copy(root);'))

    def test_owned_match_projection_preserves_joined_children_and_carrier(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Item { leaf: A<Leaf> } }
            let mut first = pool<Leaf>(1);
            let mut second = pool<Leaf>(1);
            let mut links = pool<Link>(1);
            let mut link = if SIDE == 0 {
                let leaf = first.new(data: 7);
                let holder = new(links) Link.Item { leaf: <- leaf };
                <- holder
            } else {
                let leaf = second.new(data: 8);
                let holder = new(links) Link.Item { leaf: <- leaf };
                <- holder
            };
            let mut view = match &mut link { Link.Item { leaf: child } => { child } };
            CHECK
            print(view.data);
            view.data = 9;
            match &link {
                Link.Item { leaf: child } => { let value = child.data; print(value); }
            }
            drop(-> link);
        """
        for side, expected in ((0, '7\n9\n'), (1, '8\n9\n')):
            with self.subTest(side=side):
                case = source.replace('SIDE', str(side))
                run = self.native(case.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                self.assertEqual(run.stderr.count('destroy leaf=Leaf\n'), 1)
        case = source.replace('SIDE', '0')
        for statement, diagnostic in (
            ('drop(-> link);', 'emprunt encore utilisé'),
            ('first.reset();', 'handles encore stockés'),
            ('second.reset();', 'handles encore stockés'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(case.replace('CHECK', statement))
    def test_consuming_match_moves_owned_field_and_drops_ignored_field(self):
        source = """
            enum Link { Item { leaf: A<Int>, ignored: A<Int> } }
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let mut other = pool<Int>(1);
            let mut links = pool<Link>(1);
            let link = if SIDE == 0 {
                let a = first.new(7);
                let b = other.new(8);
                let holder = new(links) Link.Item { leaf: <- a, ignored: <- b };
                <- holder
            } else {
                let a = second.new(9);
                let b = other.new(8);
                let holder = new(links) Link.Item { leaf: <- a, ignored: <- b };
                <- holder
            };
            let result: A<Int> = match (-> link) {
                Link.Item { leaf: child, ignored: unused } => { drop(-> unused); <- child }
            };
            let again = other.new(10);
            print(*result);
            print(*again);
            drop(-> result);
        """
        for side, expected in ((0, 7), (1, 9)):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)))
                self.assertEqual((run.returncode, run.stdout), (0, f'{expected}\n10\n'), run.stderr)
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
                self.assertEqual(destroyed, [
                    # Both fields are extracted before the arm: the empty holder dies first.
                    'destroy holder=Link.Item', 'destroy b=8', f'destroy a={expected}', 'destroy again=10',
                ])
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('SIDE', '0').replace('print(*result);', 'drop(-> link);'))

    def test_consuming_match_owned_field_keeps_its_borrow(self):
        source = """
            struct Leaf { view: &Int }
            enum Link { Item { leaf: A<Leaf> } }
            let mut values = pool<Int>(1);
            let mut leaves = pool<Leaf>(1);
            let mut links = pool<Link>(1);
            let mut number = values.new(7);
            let leaf = leaves.new(view: &number);
            let link = new(links) Link.Item { leaf: <- leaf };
            let result = match (-> link) {
                Link.Item { leaf: child } => { <- child }
            };
            CHECK
            let view = result.view;
            print(view);
            drop(-> result);
            number.set(9);
            print(number);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'number.set(9);'))

    def test_shared_owned_parameter_tracks_nested_pool_through_relay(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Item { leaf: A<Leaf> } }
            struct Root { link: A<Link> }
            fn inspect(link: &Link, mem: &mut Pool<Leaf>) -> Int {
                mem.reset();
                let n = match &link {
                    Link.Item { leaf: child } => { child.data }
                };
                return n;
            }
            fn relay(root: &Root, mem: &mut Pool<Leaf>) -> Int {
                let link = &*root.link;
                return inspect(link, mem);
            }
            let mut leaves = pool<Leaf>(1);
            let mut other = pool<Leaf>(1);
            let mut links = pool<Link>(1);
            let mut roots = pool<Root>(1);
            let leaf = leaves.new(data: 7);
            let link = new(links) Link.Item { leaf: <- leaf };
            let root = roots.new(link: <- link);
            let n = relay(&root, &mut SOURCE);
            print(n);
            drop(-> root);
            let next = leaves.new(data: 9);
            print(next.data);
        """
        run = self.native(source.replace('SOURCE', 'other'))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy leaf=Leaf\n'), 1)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source.replace('SOURCE', 'leaves'))
        with self.assertRaisesRegex(Error, 'seule une allocation explicite'):
            verify_program(source.replace('SOURCE', 'other').replace('match &link', 'match (-> link)'))

    def test_mutable_owned_parameter_updates_child_without_relocating_it(self):
        source = """
            struct Leaf { value: Int }
            struct Root { item: A<Leaf> }
            fn edit(root: &mut Root) {
                let child = &mut *root.item;
                child.value = 9;
            }
            fn relay(root: &mut Root) { edit(root); }
            let mut items = pool<Leaf>(1);
            let mut roots = pool<Root>(1);
            let mut root = roots.new(item: <- items.new(value: 7));
            let before = &*root.item;
            address(before);
            relay(&mut root);
            CHECK
            let after = &*root.item;
            address(after);
            print(after.value);
            drop(-> root);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value = run.stdout.splitlines()
        self.assertEqual((after, value), (before, '9'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(before.value);'))
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program("""
                struct Leaf { value: Int }
                struct Child { item: A<Leaf> }
                struct Root { child: A<Child> }
                fn edit(root: &mut Root, p: &mut Pool<Leaf>) {
                    let child = &mut *root.child;
                    child.item = <- p.new(value: 9);
                }
                let mut original = pool<Leaf>(1);
                let mut replacement = pool<Leaf>(1);
                let mut children = pool<Child>(1);
                let mut roots = pool<Root>(1);
                let child = children.new(item: <- original.new(value: 7));
                let mut root = roots.new(child: <- child);
                edit(&mut root, &mut replacement);
                replacement.reset();
                let view = &*root.child;
                let leaf = &*view.item;
                print(leaf.value);
            """)

    def test_mutable_call_replaces_owned_field_along_nested_path(self):
        source = """
            struct Child { item: A<Int> }
            struct Root { child: A<Child> }
            fn edit(child: &mut Child, p: &mut Pool<Int>) {
                child.item = <- p.new(8);
            }
            fn relay(root: &mut Root, p: &mut Pool<Int>) {
                let child = &mut *root.child;
                edit(child, p);
            }
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let mut children = pool<Child>(1);
            let mut roots = pool<Root>(1);
            let child = children.new(item: <- first.new(7));
            let mut root = roots.new(child: <- child);
            relay(&mut root, &mut second);
            CHECK
            let view = &*root.child;
            print(*view.item);
            drop(-> root);
            let reuse = second.new(9);
            print(reuse);
        """
        run = self.native(source.replace('CHECK', 'first.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '8\n9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(source.replace('CHECK', 'second.reset();'))

    def test_mutable_call_composes_owned_field_and_descendant_replacements(self):
        source = """
            struct Child { item: A<Int> }
            struct Root { child: A<Child> }
            fn edit(side: Int, root: &mut Root, children: &mut Pool<Child>,
                    temp: &mut Pool<Int>, output: &mut Pool<Int>) {
                INSTALL
                let child = &mut *root.child;
                child.item = <- output.new(9);
            }
            let mut first = pool<Int>(1);
            let mut temp = pool<Int>(1);
            let mut output = pool<Int>(1);
            let mut children = pool<Child>(2);
            let mut roots = pool<Root>(1);
            let child = children.new(item: <- first.new(7));
            let mut root = roots.new(child: <- child);
            edit(SIDE, &mut root, &mut children, &mut temp, &mut output);
            CHECK
            let view = &*root.child;
            print(*view.item);
            drop(-> root);
        """
        install = 'root.child = <- children.new(item: <- temp.new(8));'
        sequential = source.replace('INSTALL', install).replace('SIDE', '0')
        run = self.native(sequential.replace('CHECK', 'first.reset(); temp.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(sequential.replace('CHECK', 'output.reset();'))
        conditional = source.replace('INSTALL', f'if side == 0 {{ {install} return; }}')
        joined = conditional.replace(' return; }', ' } else {').replace(
            'child.item = <- output.new(9);', 'child.item = <- output.new(9); }',
        ).replace('let mut first', '''
            fn relay(side: Int, root: &mut Root, children: &mut Pool<Child>,
                     temp: &mut Pool<Int>, output: &mut Pool<Int>) {
                edit(side, root, children, temp, output);
            }
            let mut first
        ''').replace('edit(SIDE, &mut root', 'relay(SIDE, &mut root')
        for mode, case in (('separate exits', conditional), ('joined relay', joined)):
            for side, expected in ((0, '8\n'), (1, '9\n')):
                with self.subTest(mode=mode, side=side):
                    run = self.native(case.replace('SIDE', str(side)).replace('CHECK', 'first.reset();'))
                    self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
            for pool in ('temp', 'output'):
                with self.subTest(mode=mode, pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(case.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))

    def test_mutable_parameter_replaces_direct_owned_field_through_relay(self):
        source = """
            struct Root { item: A<Int> }
            fn edit(side: Int, root: &mut Root, p: &mut Pool<Int>) {
                UPDATE
            }
            fn relay(side: Int, root: &mut Root, p: &mut Pool<Int>) {
                edit(side, root, p);
            }
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let mut roots = pool<Root>(1);
            let mut root = roots.new(item: <- first.new(7));
            relay(SIDE, &mut root, &mut second);
            CHECK
            print(*root.item);
            drop(-> root);
            let next = second.new(9);
            print(next);
        """
        replacement = 'root.item = <- p.new(8);'
        always = source.replace('UPDATE', replacement).replace('SIDE', '0')
        run = self.native(always.replace('CHECK', 'first.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '8\n9\n'), run.stderr)
        conditional = source.replace('UPDATE', f'if side == 0 {{ {replacement} }}')
        for side, expected in ((0, '8\n9\n'), (1, '7\n9\n')):
            with self.subTest(side=side):
                run = self.native(conditional.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for pool in ('first', 'second'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(conditional.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))

    def test_mutable_call_replaces_owned_aggregate_and_tracks_its_descendants(self):
        source = """
            struct Child { item: A<Int> }
            struct Root { child: A<Child> }
            fn edit(root: &mut Root, p: &mut Pool<Child>, v: &mut Pool<Int>) {
                let child = p.new(item: <- v.new(8));
                root.child = <- child;
            }
            fn relay(root: &mut Root, p: &mut Pool<Child>, v: &mut Pool<Int>) { edit(root, p, v); }
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let mut children = pool<Child>(2);
            let mut roots = pool<Root>(1);
            let child = children.new(item: <- first.new(7));
            let mut root = roots.new(child: <- child);
            relay(&mut root, &mut children, &mut second);
            CHECK
            let view = &*root.child;
            print(*view.item);
            drop(-> root);
            let next = second.new(9);
            print(next);
        """
        transferred = source.replace(
            'root: &mut Root, p: &mut Pool<Child>, v: &mut Pool<Int>',
            'root: &mut Root, child: -> A<Child>',
        ).replace('let child = p.new(item: <- v.new(8));', '').replace(
            'edit(root, p, v);', 'edit(root, -> child);',
        ).replace(
            'relay(&mut root, &mut children, &mut second);',
            'let fresh = children.new(item: <- second.new(8)); relay(&mut root, -> fresh);',
        )
        for case in (source, transferred):
            run = self.native(case.replace('CHECK', 'first.reset();'))
            self.assertEqual((run.returncode, run.stdout), (0, '8\n9\n'), run.stderr)
            self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
            with self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(case.replace('CHECK', 'second.reset();'))
        local_descendant = source.replace(
            'let child = p.new(item: <- v.new(8));',
            'let mut local = pool<Int>(1); let child = p.new(item: <- local.new(8));',
        )
        with self.assertRaisesRegex(Error, 'provenance non durable'):
            verify_program(local_descendant.replace('CHECK', ''))

    def test_transferred_owned_parameter_cleans_extracted_field_through_relay(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Item { leaf: A<Leaf> } }
            fn inspect(link: -> Link, mem: &mut Pool<Leaf>) -> Int {
                mem.reset();
                let n = match (-> link) { Link.Item { leaf: child } => { child.data } };
                return n;
            }
            fn relay(link: -> Link, mem: &mut Pool<Leaf>) -> Int {
                return inspect(-> link, mem);
            }
            let mut leaves = pool<Leaf>(1);
            let mut other = pool<Leaf>(1);
            let mut links = pool<Link>(1);
            let leaf = leaves.new(data: 7);
            let link = new(links) Link.Item { leaf: <- leaf };
            BEFORE
            let n = relay(-> link, &mut SOURCE);
            AFTER
            print(n);
            let next = leaves.new(data: 9);
            print(next.data);
        """
        valid = source.replace('SOURCE', 'other')
        run = self.native(valid.replace('BEFORE', '').replace('AFTER', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed, ['destroy link=Link.Item', 'destroy leaf=Leaf', 'destroy next=Leaf'])
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source.replace('SOURCE', 'leaves').replace('BEFORE', '').replace('AFTER', ''))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(valid.replace('BEFORE', '''
                let view = match &link { Link.Item { leaf: child } => { child } };
            ''').replace('AFTER', 'print(view.data);'))

    def test_function_returns_fresh_aggregate_with_alternative_child_pools(self):
        source = """
            struct Root { item: A<Int> }
            fn make(side: Int, roots: &mut Pool<Root>, mem: &mut Pool<Int>, item: -> A<Int>) -> <- A<Root> {
                if side == 0 {
                    item ->;
                    let root = roots.new(item: <- item);
                    return <- root;
                }
                drop(-> item);
                let root = roots.new(item: <- mem.new(8));
                return <- root;
            }
            fn relay(side: Int, roots: &mut Pool<Root>, mem: &mut Pool<Int>, item: -> A<Int>) -> <- A<Root> {
                let root = make(side, roots, mem, -> item);
                return <- root;
            }
            let mut items = pool<Int>(1);
            let mut alternatives = pool<Int>(1);
            let mut roots = pool<Root>(1);
            let item = items.new(7);
            let result = relay(SIDE, &mut roots, &mut alternatives, -> item);
            CHECK
            print(*result.item);
            drop(-> result);
            let next = items.new(9);
            print(next);
        """
        for side, expected in ((0, '7\n9\n'), (1, '8\n9\n')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
        for pool in ('items', 'alternatives'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))

    def test_function_returns_nested_owned_fields_through_relay(self):
        source = """
            struct Child { item: A<Int> }
            struct Root { child: A<Child> }
            fn make(roots: &mut Pool<Root>, children: &mut Pool<Child>, values: &mut Pool<Int>) -> <- A<Root> {
                let child = children.new(item: <- values.new(7));
                let root = roots.new(child: <- child);
                return <- root;
            }
            fn relay(roots: &mut Pool<Root>, children: &mut Pool<Child>, values: &mut Pool<Int>) -> <- A<Root> {
                let root = make(roots, children, values);
                return <- root;
            }
            let mut values = pool<Int>(1);
            let mut replacements = pool<Int>(1);
            let mut children = pool<Child>(1);
            let mut roots = pool<Root>(1);
            let mut root = relay(&mut roots, &mut children, &mut values);
            let child = &mut *root.child;
            BEFORE
            print(*child.item);
            child.item = <- replacements.new(8);
            AFTER
            print(*child.item);
            drop(-> root);
            let again = replacements.new(9);
            print(again);
        """
        run = self.native(source.replace('BEFORE', '').replace('AFTER', 'values.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n8\n9\n'), run.stderr)
        for pool in ('values', 'children'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('BEFORE', f'{pool}.reset();').replace('AFTER', ''))
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(source.replace('BEFORE', '').replace('AFTER', 'replacements.reset();'))

    def test_function_returns_finite_value_of_recursive_owned_type(self):
        source = """
            enum Node { End { value: Int }, Link { next: A<Node> } }
            fn make(side: Int, ends: &mut Pool<Node>, links: &mut Pool<Node>) -> <- A<Node> {
                if side == 0 {
                    let single = new(ends) Node.End { value: 5 };
                    return <- single;
                }
                let end = new(ends) Node.End { value: 7 };
                let middle = new(links) Node.Link { next: <- end };
                let top = new(links) Node.Link { next: <- middle };
                return <- top;
            }
            fn relay(side: Int, ends: &mut Pool<Node>, links: &mut Pool<Node>) -> <- A<Node> {
                let root = make(side, ends, links);
                return <- root;
            }
            let mut ends = pool<Node>(1);
            let mut links = pool<Node>(2);
            let root = relay(SIDE, &mut ends, &mut links);
            CHECK
            match &root {
                Node.End { value: n } => { print(n); },
                Node.Link { next: mid } => {
                    match &mid {
                        Node.End { value: n } => { print(n); },
                        Node.Link { next: last } => {
                            match &last {
                                Node.End { value: n } => { print(n); },
                                Node.Link { next: _ } => {}
                            }
                        }
                    }
                }
            }
            drop(-> root);
            let again = new(ends) Node.End { value: 9 };
            match &again { Node.End { value: n } => { print(n); }, _ => {} }
        """
        for side, expected in ((0, '5\n9\n'), (1, '7\n9\n')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                if side == 1:
                    destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
                    self.assertEqual(destroyed[:3], [
                        'destroy end=Node.End', 'destroy middle=Node.Link', 'destroy top=Node.Link',
                    ])
        for pool in ('ends', 'links'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('SIDE', '1').replace('CHECK', f'{pool}.reset();'))

    def test_recursive_owned_parameter_can_be_inspected_relayed_and_destroyed(self):
        source = """
            enum Node { End { value: Int }, Link { next: A<Node> } }
            fn peek(node: &Node) {
                match &node {
                    Node.End { value: n } => { print(n); },
                    Node.Link { next: child } => {
                        match &child {
                            Node.End { value: n } => { print(n); },
                            Node.Link { next: grandchild } => {
                                match &grandchild { Node.End { value: n } => { print(n); }, _ => {} }
                            }
                        }
                    }
                }
            }
            fn relay(node: -> A<Node>) -> <- A<Node> { return <- node; }
            fn destroy(node: -> A<Node>) { drop(-> node); }
            let mut ends = pool<Node>(1);
            let mut links = pool<Node>(2);
            let leaf = new(ends) Node.End { value: 7 };
            let root = new(links) Node.Link { next: <- leaf };
            peek(&root);
            let top = new(links) Node.Link { next: <- root };
            peek(&top);
            address(top);
            let received = relay(-> top);
            address(received);
            CHECK
            destroy(-> received);
            let reused = new(ends) Node.End { value: 9 };
            peek(&reused);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        first, deep, before, after, reused = run.stdout.splitlines()
        self.assertEqual((first, deep, after, reused), ('7', '7', before, '9'))
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed[:3], ['destroy leaf=Node.End', 'destroy root=Node.Link', 'destroy top=Node.Link'])
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(source.replace('CHECK', 'ends.reset();'))
        with self.assertRaisesRegex(Error, 'reset avec un paramètre propriétaire récursif'):
            verify_program(source.replace('CHECK', '') + """
                fn reset_while_borrowed(node: &Node, p: &mut Pool<Node>) {
                    p.reset();
                    peek(node);
                }
            """)

    def test_mutable_enum_match_replaces_owned_field_only_for_matching_variant(self):
        source = """
            struct Child { item: A<Int> }
            enum Node { End { child: A<Child> }, Link { next: A<Node> } }
            fn edit(node: &mut Node, p: &mut Pool<Int>) {
                match &mut node {
                    Node.End { child: child } => { child.item = <- p.new(8); },
                    Node.Link { next: _ } => {}
                }
            }
            fn relay(node: &mut Node, p: &mut Pool<Int>) { edit(node, p); }
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let mut children = pool<Child>(1);
            let mut nodes = pool<Node>(1);
            let child = children.new(item: <- first.new(7));
            ROOT
            relay(&mut root, &mut second);
            CHECK
            match (-> root) {
                Node.End { child: child } => { print(*child.item); },
                Node.Link { next: remaining } => { drop(-> remaining); print(0); }
            }
        """
        end = source.replace('ROOT', 'let mut root = new(nodes) Node.End { child: <- child };')
        run = self.native(end.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '8\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(end.replace('CHECK', 'second.reset();'))
        link = source.replace('ROOT', '''
            let end = new(nodes) Node.End { child: <- child };
            let mut root = new(nodes) Node.Link { next: <- end };
        ''')
        run = self.native(link.replace('CHECK', 'second.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '0\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
        deep = link.replace('Node.Link { next: _ } => {}', '''
            Node.Link { next: next } => {
                match &mut next {
                    Node.End { child: child } => { child.item = <- p.new(9); },
                    _ => {}
                }
            }
        ''', 1).replace('Node.Link { next: remaining } => { drop(-> remaining); print(0); }', '''
            Node.Link { next: next } => {
                match (-> next) { Node.End { child: child } => { print(*child.item); }, Node.Link { next: rest } => { drop(-> rest); } }
            }
        ''')
        run = self.native(deep.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(deep.replace('CHECK', 'second.reset();'))

    def test_recursive_mutable_parameter_updates_deep_leaf_in_place(self):
        source = """
            struct Leaf { value: Int }
            enum Node { End { leaf: A<Leaf> }, Link { next: A<Node> } }
            fn edit(node: &mut Node) {
                match &mut node {
                    Node.End { leaf: leaf } => { leaf.value = 9; },
                    Node.Link { next: child } => {
                        match &mut child {
                            Node.End { leaf: leaf } => { leaf.value = 9; },
                            Node.Link { next: last } => {
                                match &mut last {
                                    Node.End { leaf: leaf } => { leaf.value = 9; },
                                    _ => {}
                                }
                            }
                        }
                    }
                }
            }
            fn relay(node: &mut Node) { edit(node); }
            let mut nodes = pool<Node>(2);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(value: 7);
            address(leaf);
            let end = new(nodes) Node.End { leaf: <- leaf };
            let child = new(nodes) Node.Link { next: <- end };
            let mut root = new(nodes) Node.Link { next: <- child };
            BEFORE
            relay(&mut root);
            AFTER
            match &root {
                Node.End { leaf: _ } => {},
                Node.Link { next: child } => {
                    match &child {
                        Node.End { leaf: _ } => {},
                        Node.Link { next: last } => {
                            match &last {
                                Node.End { leaf: leaf } => {
                                    address(leaf);
                                    let value = leaf.value;
                                    print(value);
                                },
                                _ => {}
                            }
                        }
                    }
                }
            }
            drop(-> root);
        """
        run = self.native(source.replace('BEFORE', '').replace('AFTER', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value = run.stdout.splitlines()
        self.assertEqual((after, value), (before, '9'))
        self.assertEqual(run.stderr.count('destroy leaf=Leaf\n'), 1)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'let held = &root;').replace('AFTER', 'address(held);'))

    def test_consuming_match_extracts_recursive_owned_child_beyond_first_repeat(self):
        source = """
            enum Node { End { value: Int }, Link { next: A<Node> } }
            fn read(node: -> A<Node>) -> Int {
                let result = match (-> node) {
                    Node.End { value: n } => { n },
                    Node.Link { next: child } => {
                        let result = match (-> child) {
                            Node.End { value: n } => { n },
                            Node.Link { next: grandchild } => {
                                let result = match (-> grandchild) {
                                    Node.End { value: n } => { n },
                                    Node.Link { next: remaining } => { drop(-> remaining); 0 }
                                };
                                result
                            }
                        };
                        result
                    }
                };
                return result;
            }
            let mut ends = pool<Node>(1);
            let mut links = pool<Node>(2);
            let leaf = new(ends) Node.End { value: 7 };
            let middle = new(links) Node.Link { next: <- leaf };
            let root = new(links) Node.Link { next: <- middle };
            let result = read(-> root);
            print(result);
            let reused = new(ends) Node.End { value: 9 };
            let n = read(-> reused);
            print(n);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed, [
            'destroy root=Node.Link', 'destroy middle=Node.Link', 'destroy leaf=Node.End',
            'destroy reused=Node.End',
        ])
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('print(result);', 'drop(-> root); print(result);'))

    def test_function_returns_consumed_recursive_owned_projection_through_relay(self):
        source = """
            enum Node { End { value: Int }, Link { next: A<Node> } }
            enum Wrapper { Item { node: A<Node> } }
            fn extract(value: -> A<Wrapper>) -> <- A<Node> {
                let result = match (-> value) { Wrapper.Item { node: child } => { <- child } };
                return <- result;
            }
            fn relay(value: -> A<Wrapper>) -> <- A<Node> {
                let result = extract(-> value);
                return <- result;
            }
            let mut ends = pool<Node>(1);
            let mut links = pool<Node>(1);
            let mut wrappers = pool<Wrapper>(1);
            let end = new(ends) Node.End { value: 7 };
            let node = new(links) Node.Link { next: <- end };
            address(node);
            let root = new(wrappers) Wrapper.Item { node: <- node };
            let result = relay(-> root);
            address(result);
            CHECK
            match &result {
                Node.End { value: n } => { print(n); },
                Node.Link { next: child } => {
                    match &child { Node.End { value: n } => { print(n); }, _ => {} }
                }
            }
            drop(-> result);
            let next = new(ends) Node.End { value: 9 };
            match &next { Node.End { value: n } => { print(n); }, _ => {} }
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value, reuse = run.stdout.splitlines()
        self.assertEqual((after, value, reuse), (before, '7', '9'))
        self.assertEqual(run.stderr.count('destroy root=Wrapper.Item\n'), 1)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(source.replace('CHECK', 'ends.reset();'))

    def test_function_composes_two_owned_extractions_with_fresh_fallback(self):
        source = """
            enum Node { End { value: Int }, Link { next: A<Node> } }
            fn peel(node: -> A<Node>, ends: &mut Pool<Node>) -> <- A<Node> {
                let result = match (-> node) {
                    Node.End { value: v } => {
                        let replacement = new(ends) Node.End { value: v + 1 };
                        <- replacement
                    },
                    Node.Link { next: child } => { <- child }
                };
                return <- result;
            }
            fn twice(node: -> A<Node>, ends: &mut Pool<Node>) -> <- A<Node> {
                let child = peel(-> node, ends);
                let result = peel(-> child, ends);
                return <- result;
            }
            let mut ends = pool<Node>(1);
            let mut links = pool<Node>(2);
            let end = new(ends) Node.End { value: 7 };
            address(end);
            ROOT
            let result = twice(-> TARGET, &mut ends);
            address(result);
            match &result { Node.End { value: n } => { print(n); }, _ => {} }
            drop(-> result);
        """
        deep = source.replace('ROOT', '''
            let mid = new(links) Node.Link { next: <- end };
            let root = new(links) Node.Link { next: <- mid };
        ''').replace('TARGET', 'root')
        run = self.native(deep)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value = run.stdout.splitlines()
        self.assertEqual((after, value), (before, '7'))
        self.assertEqual(run.stderr.count('destroy end=Node.End\n'), 1)
        short = self.native(source.replace('ROOT', '').replace('TARGET', 'end'))
        self.assertEqual(short.returncode, 0, short.stderr)
        self.assertEqual(short.stdout.splitlines()[-1], '9')
        self.assertEqual(short.stderr.count('destroy replacement=Node.End\n'), 2)

    def test_owned_projection_can_be_installed_in_returned_or_borrowed_aggregate(self):
        source = """
            enum Node { End { value: Int }, Link { next: A<Node> } }
            enum Wrapper { Item { node: A<Node> } }
            struct Package { content: A<Node> }
            fn extract(value: -> A<Wrapper>) -> <- A<Node> {
                let result = match (-> value) { Wrapper.Item { node: child } => { <- child } };
                return <- result;
            }
            fn repack(value: -> A<Wrapper>, p: &mut Pool<Package>) -> <- A<Package> {
                let node = extract(-> value);
                let result = p.new(content: <- node);
                return <- result;
            }
            fn install(value: -> A<Wrapper>, p: &mut Package) {
                let node = extract(-> value);
                p.content = <- node;
            }
            let mut ends = pool<Node>(1);
            let mut links = pool<Node>(1);
            let mut wrappers = pool<Wrapper>(1);
            let mut packages = pool<Package>(1);
            let end = new(ends) Node.End { value: 7 };
            let node = new(links) Node.Link { next: <- end };
            address(node);
            let root = new(wrappers) Wrapper.Item { node: <- node };
            INTEGRATE
            CHECK
            let content = &*result.content;
            address(content);
            match &content {
                Node.End { value: n } => { print(n); },
                Node.Link { next: child } => {
                    match &child { Node.End { value: n } => { print(n); }, _ => {} }
                }
            }
            drop(-> result);
        """
        integrations = (
            'let result = repack(-> root, &mut packages);',
            '''
                let mut old = pool<Node>(1);
                let mut result = packages.new(content: <- new(old) Node.End { value: 3 });
                install(-> root, &mut result);
                old.reset();
            ''',
        )
        for integration in integrations:
            with self.subTest(integration=integration):
                case = source.replace('INTEGRATE', integration)
                run = self.native(case.replace('CHECK', ''))
                self.assertEqual(run.returncode, 0, run.stderr)
                before, after, value = run.stdout.splitlines()
                self.assertEqual((after, value), (before, '7'))
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(case.replace('CHECK', 'ends.reset();'))

    def test_function_wraps_transferred_aggregate_with_its_nested_pool_origins(self):
        source = """
            struct Child { item: A<Int> }
            struct Root { child: A<Child> }
            fn make(roots: &mut Pool<Root>, child: -> A<Child>) -> <- A<Root> {
                let root = roots.new(child: <- child);
                return <- root;
            }
            fn relay(roots: &mut Pool<Root>, child: -> A<Child>) -> <- A<Root> {
                let root = make(roots, -> child);
                return <- root;
            }
            let mut one = pool<Int>(1);
            let mut two = pool<Int>(1);
            let mut children = pool<Child>(1);
            let mut roots = pool<Root>(1);
            let child = if SIDE == 0 {
                let left = children.new(item: <- one.new(7));
                <- left
            } else {
                let right = children.new(item: <- two.new(8));
                <- right
            };
            address(child);
            let root = relay(&mut roots, -> child);
            CHECK
            let view = &*root.child;
            address(view);
            print(*view.item);
            drop(-> root);
            let reuse = one.new(9);
            print(reuse);
        """
        for side, expected in ((0, '7'), (1, '8')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual(run.returncode, 0, run.stderr)
                before, after, value, reused = run.stdout.splitlines()
                self.assertEqual((after, value, reused), (before, expected, '9'))
        for pool in ('one', 'two', 'children'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))

    def test_function_returns_either_fresh_or_transferred_aggregate_in_same_field(self):
        source = """
            struct Child { item: A<Int> }
            struct Root { child: A<Child> }
            fn make(side: Int, roots: &mut Pool<Root>, children: &mut Pool<Child>,
                    values: &mut Pool<Int>, child: -> A<Child>) -> <- A<Root> {
                if side == 0 {
                    child ->;
                    let root = roots.new(child: <- child);
                    return <- root;
                }
                drop(-> child);
                let fresh = children.new(item: <- values.new(8));
                let root = roots.new(child: <- fresh);
                return <- root;
            }
            fn relay(side: Int, roots: &mut Pool<Root>, children: &mut Pool<Child>,
                     values: &mut Pool<Int>, child: -> A<Child>) -> <- A<Root> {
                let root = make(side, roots, children, values, -> child);
                return <- root;
            }
            let mut old_values = pool<Int>(1);
            let mut new_values = pool<Int>(1);
            let mut old_children = pool<Child>(1);
            let mut new_children = pool<Child>(1);
            let mut roots = pool<Root>(1);
            let child = old_children.new(item: <- old_values.new(7));
            address(child);
            let root = relay(SIDE, &mut roots, &mut new_children, &mut new_values, -> child);
            CHECK
            let view = &*root.child;
            address(view);
            print(*view.item);
            drop(-> root);
            let reused = new_values.new(9);
            print(reused);
        """
        for side, expected in ((0, '7'), (1, '8')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual(run.returncode, 0, run.stderr)
                before, after, value, reused = run.stdout.splitlines()
                self.assertEqual((before == after, value, reused), (side == 0, expected, '9'))
        for pool in ('old_values', 'new_values', 'old_children', 'new_children'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))

    def test_function_restitutes_aggregate_and_owned_field_identity(self):
        source = """
            struct Root { item: A<Int>, mark: Int }
            fn update(mut root: -> Root) -> <- A<Root> {
                root.mark = 9;
                return <- root;
            }
            fn relay(root: -> Root) -> <- A<Root> {
                let received = update(-> root);
                return <- received;
            }
            let mut items = pool<Int>(1);
            let mut roots = pool<Root>(1);
            let root = roots.new(item: <- items.new(7));
            address(root);
            let received = relay(-> root);
            address(received);
            CHECK
            print(*received.item);
            print(received.mark);
            drop(-> received);
            let next = items.new(10);
            print(next);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, item, mark, reused = run.stdout.splitlines()
        self.assertEqual((after, item, mark, reused), (before, '7', '9', '10'))
        self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(source.replace('CHECK', 'items.reset();'))
        # The later returned-field replacement rule preserves the root identity.
        replacement = """
                struct Root { item: A<Int> }
                fn replace(mut root: -> Root, p: &mut Pool<Int>) -> <- A<Root> {
                    root.item = <- p.new(8);
                    return <- root;
                }
                let mut old = pool<Int>(1);
                let mut next = pool<Int>(1);
                let mut roots = pool<Root>(1);
                let root = roots.new(item: <- old.new(7));
                address(root);
                let result = replace(-> root, &mut next);
                address(result);
                print(*result.item);
                drop(-> result);
                let reuse_old = old.new(9);
                let reuse_next = next.new(10);
                print(reuse_old); print(reuse_next);
            """
        run = self.native(replacement)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value, old, new = run.stdout.splitlines()
        self.assertEqual((after, value, old, new), (before, '8', '9', '10'))
        self.assertEqual(run.stderr.count('destroy item=7\n'), 1)
        self.assertEqual(run.stderr.count('destroy champ=8\n'), 1)

    def test_function_can_return_owned_field_extracted_from_local_enum(self):
        source = """
            enum Link { Item { leaf: A<Int> } }
            fn wrap(links: &mut Pool<Link>, a: -> A<Int>) -> <- A<Int> {
                let link = new(links) Link.Item { leaf: <- a };
                let result = match (-> link) { Link.Item { leaf: child } => { <- child } };
                return <- result;
            }
            fn relay(links: &mut Pool<Link>, a: -> A<Int>) -> <- A<Int> {
                let result = wrap(links, -> a);
                return <- result;
            }
            let mut values = pool<Int>(1);
            let mut links = pool<Link>(1);
            let a = values.new(7);
            address(a);
            let result = relay(&mut links, -> a);
            address(result);
            print(*result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value = run.stdout.splitlines()
        self.assertEqual((after, value), (before, '7'))
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)

    def test_function_can_return_owned_field_with_conditional_pool_origin(self):
        source = """
            enum Link { Item { leaf: A<Int> } }
            fn select(side: Int, links: &mut Pool<Link>, one: &mut Pool<Int>, two: &mut Pool<Int>) -> <- A<Int> {
                let link = if side == 0 {
                    let left = new(links) Link.Item { leaf: <- one.new(7) };
                    <- left
                } else {
                    let right = new(links) Link.Item { leaf: <- two.new(9) };
                    <- right
                };
                let selected = match (-> link) { Link.Item { leaf: child } => { <- child } };
                return <- selected;
            }
            let mut one = pool<Int>(1);
            let mut two = pool<Int>(1);
            let mut links = pool<Link>(1);
            let result = select(SIDE, &mut links, &mut one, &mut two);
            CHECK
            print(*result);
        """
        for side, expected in ((0, '7\n'), (1, '9\n')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for pool in ('one', 'two'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'doit encore être utilisé'):
                verify_program(source.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))

    def test_function_contract_protects_pool_of_implicitly_dropped_owned_field(self):
        source = """
            enum Link { Item { leaf: A<Int> } }
            fn consume(links: &mut Pool<Link>, reset: &mut Pool<Int>, a: -> A<Int>) {
                let link = new(links) Link.Item { leaf: <- a };
                let observed = &link;
                reset.reset();
            }
            let mut values = pool<Int>(1);
            let mut links = pool<Link>(1);
            let mut other = pool<Int>(1);
            let a = values.new(7);
            consume(&mut links, &mut SOURCE, -> a);
            let next = values.new(9);
            print(*next);
        """
        run = self.native(source.replace('SOURCE', 'other'))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source.replace('SOURCE', 'values'))

    def test_consuming_match_cleans_owned_field_on_continue_and_break(self):
        run = self.native("""
            enum Link { Item { leaf: A<Int> } }
            let mut values = pool<Int>(1);
            let mut links = pool<Link>(1);
            let mut i = 0;
            loop {
                let a = values.new(i);
                let link = new(links) Link.Item { leaf: <- a };
                match (-> link) {
                    Link.Item { leaf: child } => {
                        print(*child);
                        if i == 1 { break; }
                        i = i + 1;
                        continue;
                    }
                }
            }
            let again = values.new(9);
            print(*again);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '0\n1\n9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy a='), 2, run.stderr)

    def test_owned_struct_field_replacement_preserves_disjoint_borrow(self):
        source = """
            struct Root { item: A<Int>, other: A<Int> }
            let mut first = pool<Int>(1);
            let old = first.new(7);
            let mut second = pool<Int>(2);
            let keep = second.new(8);
            let mut roots = pool<Root>(1);
            let mut root = roots.new(item: <- old, other: <- keep);
            let view = &*root.other;
            root.item = <- second.new(*root.item + 2);
            print(*view);
            print(*root.item);
            let reclaimed = first.new(12);
            print(reclaimed);
            first.reset();
            drop(-> root);
            let reuse = second.new(11);
            print(reuse);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '8\n9\n12\n11\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy old=7\n'), 1)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('let view = &*root.other;', 'let view = &*root.item;'))
        same_pool = source.replace('second.new(*root.item + 2)', 'first.new(*root.item + 2)')
        run = self.native(same_pool.replace('first.reset();', ''))
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('pool capacity exceeded', run.stderr)
        self.assertNotIn('destroy old=7', run.stderr)

    def test_borrowed_owned_field_replacement_keeps_alternative_sources(self):
        source = """
            struct Root { item: A<Int> }
            enum Choice { One { root: &mut Root }, Two { root: &mut Root } }
            fn edit(root: &mut Root, value: -> A<Int>) { root.item = <- value; }
            let mut first = pool<Int>(1);
            let a = first.new(7);
            let mut second = pool<Int>(1);
            let b = second.new(8);
            let mut replacements = pool<Int>(1);
            let next = replacements.new(9);
            let mut roots = pool<Root>(2);
            let mut left = roots.new(item: <- a);
            let mut right = roots.new(item: <- b);
            let mut choices = pool<Choice>(1);
            let mut choice = if SIDE == 0 {
                let value = new(choices) Choice.One { root: &mut left };
                <- value
            } else {
                let value = new(choices) Choice.Two { root: &mut right };
                <- value
            };
            let mut view = match &mut choice {
                Choice.One { root: r } => { r },
                Choice.Two { root: r } => { r }
            };
            UPDATE
            drop(-> choice);
            CHECK
            print(*left.item);
            print(*right.item);
            drop(-> left);
            drop(-> right);
        """
        for update in ('view.item = <- next;', 'edit(view, -> next);'):
            case = source.replace('UPDATE', update)
            for side, expected in ((0, '9\n8\n'), (1, '7\n9\n')):
                with self.subTest(update=update, side=side):
                    run = self.native(case.replace('SIDE', str(side)).replace('CHECK', ''))
                    self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                    self.assertEqual(run.stderr.count('destroy next=9\n'), 1)
            for pool in ('first', 'second', 'replacements'):
                with self.subTest(update=update, pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(case.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))

    def test_owned_field_preserves_child_borrows_without_destroying_targets(self):
        source = """
            struct Leaf { data: &Int }
            struct Root { leaf: A<Leaf> }
            let mut values = pool<Int>(1);
            let n = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &n);
            let mut roots = pool<Root>(1);
            let root = roots.new(leaf: <- leaf);
            CHECK
            let child = &*root.leaf;
            let view = child.data;
            drop(-> root);
            print(*view);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
        self.assertEqual(destroyed, ['destroy leaf=Leaf', 'destroy root=Root', 'destroy n=7'])
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'values.reset();'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('CHECK', 'drop(-> n);'))

        mutable = source.replace('data: &Int', 'data: &mut Int').replace(
            'let n =', 'let mut n =',
        ).replace('data: &n', 'data: &mut n').replace('let root =', 'let mut root =').replace(
            'let child = &*root.leaf;\n            let view = child.data;',
            'let mut child = &mut *root.leaf; let mut view = &mut *child.data; view.set(9);',
        ).replace('print(*view);', 'print(n);')
        run = self.native(mutable.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(mutable.replace('CHECK', 'print(n);'))

    def test_owned_field_replacement_rejects_cycle_with_borrowed_back_edge(self):
        with self.assertRaisesRegex(Error, 'cycle entre allocations empruntées'):
            verify_program("""
                struct Root { leaf: A<Leaf> }
                enum Leaf { Empty, Back { root: &Root } }
                let mut leaves = pool<Leaf>(1);
                let mut roots = pool<Root>(1);
                let empty = new(leaves) Leaf.Empty;
                let mut root = roots.new(leaf: <- empty);
                let back = new(leaves) Leaf.Back { root: &root };
                root.leaf = <- back;
            """)

    def test_nested_owned_field_replacement_joins_child_metadata(self):
        source = """
            struct Child { data: A<Int> }
            struct Root { child: A<Child> }
            let mut first = pool<Int>(1);
            let a = first.new(7);
            let mut replacement = pool<Int>(1);
            let mut children = pool<Child>(1);
            let child = children.new(data: <- a);
            let mut roots = pool<Root>(1);
            let mut root = roots.new(child: <- child);
            let mut view = &mut *root.child;
            UPDATE
            CHECK
            print(*view.data);
            drop(-> root);
        """
        update = 'view.data = <- replacement.new(9);'
        conditional = source.replace('UPDATE', f'if SIDE == 0 {{ {update} }}')
        for side, expected in ((0, '9\n'), (1, '7\n')):
            with self.subTest(side=side):
                run = self.native(conditional.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for pool in ('first', 'replacement'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(conditional.replace('SIDE', '0').replace('CHECK', f'{pool}.reset();'))
        run = self.native(source.replace('UPDATE', update).replace('CHECK', 'first.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)

    def test_loop_tracks_nested_owned_replacement_with_same_pool(self):
        source = """
            struct Leaf { data: &Int }
            struct Child { leaf: A<Leaf> }
            struct Root { child: A<Child> }
            let mut values = pool<Int>(2);
            let first = values.new(7);
            let mut second = values.new(9);
            let mut leaves = pool<Leaf>(2);
            let initial = leaves.new(data: &first);
            let mut children = pool<Child>(1);
            let child = children.new(leaf: <- initial);
            let mut roots = pool<Root>(1);
            let mut root = roots.new(child: <- child);
            let mut view = &mut *root.child;
            let mut i = 0;
            if i == 1 { print(i); }
            loop {
                if i == 2 { break; }
                view.leaf = <- leaves.new(data: &second);
                i = i + 1;
                continue;
            }
            CHECK
            drop(-> root);
            second.set(12);
            print(second);
        """
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'second.set(11);'))
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '12\n'), run.stderr)
        self.assertEqual(run.stderr.count('=Leaf\n'), 3, run.stderr)

    def test_struct_shared_indirections_layout_and_transitive_lifetime(self):
        source = """
            struct Left { right: &Right }
            struct Right { left: &Left }
            struct Leaf { n: Int }
            struct Mid { leaf: &Leaf }
            struct Top { marker: Int, mid: &Mid, tail: Int }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(n: 7);
            let mut mids = pool<Mid>(1);
            let mid = mids.new(leaf: &leaf);
            let mut tops = pool<Top>(1);
            let top = tops.new(marker: 2, mid: &mid, tail: 3);
            CHECK
            print(top.marker);
            print(top.tail);
            let through = top.mid;
            let view = through.leaf;
            print(view.n);
            drop(-> top);
            drop(-> mid);
            leaves.reset();
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '2\n3\n7\n'), run.stderr)
        for statement, diagnostic in (
            ('leaves.reset();', 'reset interdit'),
            ('drop(-> leaf);', 'emprunt encore utilisé'),
            ('leaf.n = 9;', 'emprunt actif'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement).replace('drop(-> mid);', ''))
        with self.assertRaisesRegex(Error, 'cycle de champs'):
            verify_program('struct Left { right: Right } struct Right { left: Left }')
        with self.assertRaisesRegex(Error, 'type de structure non pris en charge'):
            verify_program('struct Left { right: &Missing }')

    def test_function_contract_tracks_reference_through_local_typed_chain(self):
        declarations = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf }
        """
        chain = """
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: SOURCE);
            let mut links = pool<Link>(1);
            let link = links.new(leaf: &leaf);
            let projected = link.leaf;
        """
        caller = """
            let mut input = pool<Int>(1);
            let mut other = pool<Int>(1);
            let data = input.new(7);
        """
        read = declarations + """
            fn read(data: &Int, memory: &mut Pool<Int>) -> Int {
        """ + chain.replace('SOURCE', 'data') + """
                let value = projected.data;
                memory.reset();
                return *value;
            }
        """ + caller
        run = self.native(read + 'print(read(&data, &mut other));')
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(read + 'print(read(&data, &mut input));')

        extract = declarations + """
            fn extract(data: &Int) -> &Int {
        """ + chain.replace('SOURCE', 'data') + """
                return projected.data;
            }
        """
        call = caller + 'let value = extract(&data);'
        run = self.native(extract + call + 'other.reset(); print(*value);')
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(extract + call + 'input.reset(); print(*value);')

        copied = extract.replace('pool<Link>(1)', 'pool<Link>(2)').replace(
            'let projected = link.leaf;',
            'let saved = copy(link); drop(-> link); let projected = saved.leaf;',
        )
        run = self.native(copied + call + 'print(*value);')
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(copied + call + 'input.reset(); print(*value);')

        local_target = extract.replace(
            'let mut leaves', 'let mut local = pool<Int>(1); let x = local.new(7); let mut leaves',
        ).replace('data: data', 'data: &x')
        with self.assertRaisesRegex(Error, 'local|provenance|retour'):
            verify_program(local_target)

    def test_typed_chain_prevents_overwriting_a_live_intermediate_field(self):
        source = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf }
            fn extract(data: &Int, other: &Int) -> &Int {
                let mut leaves = pool<Leaf>(1);
                let mut leaf = leaves.new(data: data);
                let mut links = pool<Link>(1);
                let link = links.new(leaf: &leaf);
                let projected = link.leaf;
                leaf.data = &*other;
                return projected.data;
            }
        """
        with self.assertRaisesRegex(Error, "accès à 'leaf' incompatible avec un emprunt actif"):
            verify_program(source)

    def test_effects_resolve_overloaded_method_on_typed_projection(self):
        source = """
            struct Leaf { data: Int }
            struct Link { leaf: &Leaf }
            struct Other { data: Int }
            impl Leaf {
                fn read(self: &Leaf, out: &mut Pool<Int>) -> Int {
                    let n = out.new(self.data);
                    return *n;
                }
            }
            impl Other { fn read(self: &Other, out: &mut Pool<Int>) -> Int { return 99; } }
            fn read(out: &mut Pool<Int>) -> Int {
                let mut leaves = pool<Leaf>(1);
                let leaf = leaves.new(data: 7);
                let mut links = pool<Link>(1);
                let link = links.new(leaf: &leaf);
                let projected = link.leaf;
                return projected.read(out);
            }
            let mut out = pool<Int>(1);
            print(read(&mut out));
        """
        compiler = verify_program(source)
        self.assertEqual(compiler.function_effects['read'].allocations, {(0, 'Int')})
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)

    def test_nested_typed_match_returns_scalar_and_checks_pool_separation(self):
        source = """
            enum Node { End { value: &Int }, Link { next: &Node } }
            fn read(data: &Int, memory: &mut Pool<Int>) -> Int {
                let mut nodes = pool<Node>(2);
                let end = new(nodes) Node.End { value: data };
                let top = new(nodes) Node.Link { next: &end };
                memory.reset();
                match &top {
                    Node.End { value: v } => { return *v; },
                    Node.Link { next: child } => {
                        match &child {
                            Node.End { value: v } => { return *v; },
                            Node.Link { next: _ } => { return 0; }
                        }
                    }
                }
            }
            let mut values = pool<Int>(1);
            let mut other = pool<Int>(1);
            let value = values.new(7);
        """
        run = self.native(source + 'print(read(&value, &mut other));')
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source + 'print(read(&value, &mut values));')

    def test_shared_structure_parameter_tracks_nested_detached_borrow(self):
        source = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf }
            fn extract(link: &Link) -> &Int {
                let leaf = link.leaf;
                return leaf.data;
            }
            fn read(link: &Link, memory: &mut Pool<Int>) -> Int {
                let value = extract(link);
                memory.reset();
                return *value;
            }
            fn forward(link: &Link, memory: &mut Pool<Int>) -> Int {
                return read(link, memory);
            }
            let mut values = pool<Int>(1);
            let mut other = pool<Int>(1);
            let data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &data);
            let mut links = pool<Link>(1);
            let link = links.new(leaf: &leaf);
        """
        constraints = verify_program(source).function_constraints['forward'].all_requirements
        self.assertEqual(
            {(rule.relation, rule.left.kind, rule.left.index, rule.left.name, rule.right.index)
             for rule in constraints},
            {('distinct', 'allocation_field_parameter', 0, '.leaf/.data', 1)},
        )
        for body in (
            'print(forward(&link, &mut other));',
            'let view = extract(&link); drop(-> link); drop(-> leaf); print(*view);',
        ):
            with self.subTest(body=body):
                run = self.native(source + body)
                self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source + 'print(forward(&link, &mut values));')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source + 'let view = extract(&link); values.reset(); print(*view);')

    def test_acyclic_enum_contract_resolves_only_reachable_reference_paths(self):
        source = """
            struct Leaf { data: &Int }
            enum Link { Node { leaf: &Leaf }, End { data: &Int } }
            fn read(link: &Link) -> Int {
                match &link {
                    Link.Node { leaf: leaf } => { let data = leaf.data; return *data; },
                    Link.End { data: data } => { return *data; }
                }
            }
            fn extract(link: -> Link) -> &Int {
                match (-> link) {
                    Link.Node { leaf: leaf } => { return leaf.data; },
                    Link.End { data: data } => { return data; }
                }
            }
            fn forward(link: -> Link) -> &Int { return extract(-> link); }
            fn from_end(data: &Int) -> &Int {
                let mut links = pool<Link>(1);
                let end = new(links) Link.End { data: data };
                return forward(-> end);
            }
            let mut left = pool<Int>(1);
            let mut right = pool<Int>(1);
            let n = left.new(7);
            let m = right.new(9);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &n);
            let mut links = pool<Link>(1);
            let node = new(links) Link.Node { leaf: &leaf };
            let end = new(links) Link.End { data: &m };
        """
        run = self.native(source + """
            print(read(&node));
            print(read(&end));
            let a = forward(-> node);
            let b = forward(-> end);
            print(*a);
            left.reset();
            print(*b);
            let c = from_end(&m);
            print(*c);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n7\n9\n9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy node=Link.Node\n'), 1)
        self.assertEqual(run.stderr.count('destroy end=Link.End\n'), 2)
        for subject, pool in (('node', 'left'), ('end', 'right')):
            with self.subTest(subject=subject), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source + f'let view = forward(-> {subject}); {pool}.reset(); print(*view);')

    def test_mutable_aggregate_contract_preserves_nested_detached_borrow(self):
        source = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf, number: Int, direct: &Int }
            fn update(link: &mut Link, replacement: &Int) -> &Int {
                link.number = 3;
                link.direct = &*replacement;
                let leaf = link.leaf;
                return leaf.data;
            }
            fn forward(link: &mut Link, replacement: &Int) -> &Int {
                return update(link, replacement);
            }
            let mut old = pool<Int>(1);
            let old_data = old.new(1);
            let mut replacements = pool<Int>(1);
            let fresh = replacements.new(2);
            let mut values = pool<Int>(1);
            let data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &data);
            let mut links = pool<Link>(1);
            let mut link = links.new(leaf: &leaf, number: 0, direct: &old_data);
            let view = forward(&mut link, &fresh);
        """
        run = self.native(source + """
            old.reset();
            print(link.number);
            let direct = link.direct;
            print(*direct);
            print(*view);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '3\n2\n7\n'), run.stderr)
        for reset, use in (
            ('values.reset();', 'print(*view);'),
            ('replacements.reset();', 'let direct = link.direct; print(*direct); print(*view);'),
        ):
            with self.subTest(reset=reset), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source + reset + use)

    def test_mutable_enum_contract_keeps_projected_capabilities_separate(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &Leaf }, End { data: &mut Int } }
            fn update(link: &mut Link) -> Int {
                match &mut link {
                    Link.Node { leaf: leaf } => { let value = leaf.data; return value; },
                    Link.End { data: data } => { data.set(9); return *data; }
                }
            }
            let mut values = pool<Int>(1);
            let mut n = values.new(1);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: 7);
            let mut links = pool<Link>(1);
            let mut node = new(links) Link.Node { leaf: &leaf };
            let mut end = new(links) Link.End { data: &mut n };
            print(update(&mut node));
            CHECK
            print(update(&mut end));
            drop(-> end);
            print(n);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(n);'))

    def test_owned_aggregate_return_keeps_typed_dependencies_across_calls(self):
        declarations = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf }
        """
        source = declarations + """
            fn make(links: &mut Pool<Link>, leaf: &Leaf) -> <- A<Link> {
                let result = links.new(leaf: leaf);
                return <- result;
            }
            fn relay(links: &mut Pool<Link>, leaf: &Leaf) -> <- A<Link> {
                let result = make(links, leaf);
                return <- result;
            }
            fn extract(links: &mut Pool<Link>, leaf: &Leaf) -> &Int {
                let result = relay(links, leaf);
                let child = result.leaf;
                return child.data;
            }
            let mut values = pool<Int>(1);
            let data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &data);
            let mut links = pool<Link>(1);
        """
        run = self.native(source + """
            let result = relay(&mut links, &leaf);
            let child = result.leaf;
            let first = child.data;
            print(*first);
            drop(-> result);
            let second = extract(&mut links, &leaf);
            drop(-> leaf);
            print(*second);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n7\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy result=Link\n'), 2)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source + """
                let result = relay(&mut links, &leaf);
                values.reset();
                let child = result.leaf;
                let view = child.data;
                print(*view);
            """)
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(declarations + """
                fn invalid(links: &mut Pool<Link>, data: &Int) -> <- A<Link> {
                    let mut leaves = pool<Leaf>(1);
                    let local = leaves.new(data: data);
                    let result = links.new(leaf: &local);
                    return <- result;
                }
            """)

    def test_conditional_owned_enum_return_preserves_variants_and_typed_link(self):
        source = """
            struct Leaf { data: &Int }
            enum Link { Node { leaf: &Leaf }, Empty }
            fn relay(value: -> Link) -> <- A<Link> { return <- value; }
            fn make(links: &mut Pool<Link>, leaf: &Leaf, side: Int) -> <- A<Link> {
                if side == 0 {
                    let result = new(links) Link.Node { leaf: leaf };
                    return <- result;
                }
                let result = new(links) Link.Empty;
                return <- result;
            }
            fn borrow(link: &Link) -> &Link { return link; }
            fn read(link: &Link) -> Int {
                let view = borrow(link);
                match &view {
                    Link.Node { leaf: child } => { let value = child.data; return *value; },
                    Link.Empty => { return 0; }
                }
            }
            let mut values = pool<Int>(1);
            let data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &data);
            let mut links = pool<Link>(1);
            let node = make(&mut links, &leaf, 0);
            let first = relay(-> node);
            print(read(&first));
            drop(-> first);
            let empty = make(&mut links, &leaf, 1);
            let second = relay(-> empty);
            print(read(&second));
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n0\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy result=Link.Node\n'), 1)
        self.assertEqual(run.stderr.count('destroy result=Link.Empty\n'), 1)

    def test_borrowed_aggregate_return_preserves_nested_contract_paths(self):
        source = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf }
            struct Top { link: &Link }
            fn direct(link: &Link) -> &Link { return link; }
            fn projected(top: &Top) -> &Link { return top.link; }
            fn extract(top: &Top, memory: &mut Pool<Int>) -> &Int {
                let link = projected(top);
                let second = direct(link);
                let child = second.leaf;
                let value = child.data;
                memory.reset();
                return value;
            }
            let mut values = pool<Int>(1);
            let mut other = pool<Int>(1);
            let data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &data);
            let mut links = pool<Link>(1);
            let link = links.new(leaf: &leaf);
            let mut tops = pool<Top>(1);
            let top = tops.new(link: &link);
        """
        run = self.native(source + """
            let view = extract(&top, &mut other);
            drop(-> top);
            drop(-> link);
            drop(-> leaf);
            print(*view);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source + 'let view = extract(&top, &mut values); print(*view);')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source + 'let view = extract(&top, &mut other); values.reset(); print(*view);')

    def test_mutable_aggregate_borrow_return_preserves_exclusivity(self):
        source = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf, marker: Int }
            fn direct(link: &mut Link) -> &mut Link { return link; }
            let mut values = pool<Int>(1);
            let data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &data);
            let mut links = pool<Link>(1);
            let mut link = links.new(leaf: &leaf, marker: 0);
            let mut view = direct(&mut link);
            CHECK
            view.marker = 4;
            let child = view.leaf;
            let value = child.data;
            print(*value);
            print(link.marker);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n4\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(link.marker);'))

    def test_replace_shared_typed_field_updates_nested_provenance(self):
        source = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf }
            fn change(link: &mut Link, replacement: &Leaf) {
                link.leaf = &*replacement;
            }
            fn forward(link: &mut Link, replacement: &Leaf) -> &Int {
                change(link, replacement);
                let child = link.leaf;
                return child.data;
            }
            let mut old = pool<Int>(1);
            let n = old.new(7);
            let mut fresh = pool<Int>(1);
            let m = fresh.new(9);
            let mut leaves = pool<Leaf>(2);
            let a = leaves.new(data: &n);
            let b = leaves.new(data: &m);
            let mut links = pool<Link>(1);
            let mut link = links.new(leaf: &a);
            let view = forward(&mut link, &b);
        """
        run = self.native(source + 'drop(-> a); old.reset(); print(*view);')
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source + 'fresh.reset(); print(*view);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(source.replace(
                'let view = forward(&mut link, &b);',
                'print(b); { let local = leaves.new(data: &m); link.leaf = &local; }',
            ))

    def test_conditional_typed_field_update_tracks_both_returned_targets(self):
        source = """
            struct Leaf { data: &Int }
            struct Link { leaf: &Leaf }
            fn change(link: &mut Link, replacement: &Leaf, side: Int) {
                if side == 0 {
                    link.leaf = &*replacement;
                    return;
                }
            }
            fn forward(link: &mut Link, replacement: &Leaf, side: Int) -> &Int {
                change(link, replacement, side);
                let child = link.leaf;
                return child.data;
            }
            let mut old = pool<Int>(1);
            let n = old.new(7);
            let mut fresh = pool<Int>(1);
            let m = fresh.new(9);
            let mut leaves = pool<Leaf>(2);
            let a = leaves.new(data: &n);
            let b = leaves.new(data: &m);
            let mut links = pool<Link>(1);
            let mut link = links.new(leaf: &a);
            let view = forward(&mut link, &b, SIDE);
        """
        for side, expected in ((0, '9\n'), (1, '7\n')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)) + 'print(*view);')
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for pool in ('old', 'fresh'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('SIDE', '0') + f'{pool}.reset(); print(*view);')

    def test_replace_shared_typed_field_rejects_allocation_cycle(self):
        source = """
            struct Node { edge: &Edge }
            enum Edge { End, Next { node: &Node } }
            let mut edges = pool<Edge>(1);
            let end = new(edges) Edge.End;
            let mut nodes = pool<Node>(1);
            let mut node = nodes.new(edge: &end);
            let next = new(edges) Edge.Next { node: &node };
            node.edge = &next;
        """
        with self.assertRaisesRegex(Error, 'cycle entre allocations empruntées'):
            verify_program(source)

    def test_typed_match_projection_preserves_method_pool_effects(self):
        source = """
            struct Leaf { value: &Int }
            struct Other { value: Int }
            enum Link { Node { leaf: &Leaf }, End }
            impl Leaf {
                fn read(self: &Leaf, out: &mut Pool<Int>) -> Int {
                    out.reset();
                    let view = self.value;
                    let value = out.new(*view);
                    return *value;
                }
            }
            impl Other { fn read(self: &Other, out: &mut Pool<Int>) -> Int { return 99; } }
            fn read(link: &Link, out: &mut Pool<Int>) -> Int {
                match &link {
                    Link.Node { leaf: leaf } => { return leaf.read(out); },
                    Link.End => { return 0; }
                }
            }
            let mut values = pool<Int>(1);
            let n = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(value: &n);
            let mut links = pool<Link>(1);
            let link = new(links) Link.Node { leaf: &leaf };
            let mut output = pool<Int>(1);
        """
        valid = source + 'print(read(&link, &mut output));'
        effects = verify_program(valid).function_effects['read']
        self.assertEqual(effects.allocations, {(1, 'Int')})
        self.assertEqual(effects.resets, {1})
        run = self.native(valid)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source + 'print(read(&link, &mut values));')

    def test_match_returns_typed_borrow_from_each_possible_carrier(self):
        source = """
            struct Leaf { data: &Int }
            enum Link { A { leaf: &Leaf }, B { leaf: &Leaf } }
            fn project(link: &Link) -> &Leaf {
                match &link {
                    Link.A { leaf: leaf } => { return leaf; },
                    Link.B { leaf: leaf } => { return leaf; }
                }
            }
            fn extract(link: &Link, memory: &mut Pool<Int>) -> &Int {
                let leaf = project(link);
                let value = leaf.data;
                memory.reset();
                return value;
            }
            fn choose(a: &Link, b: &Link, side: Int) -> &Link {
                if side == 0 { return a; }
                return b;
            }
            let mut first = pool<Int>(1);
            let n = first.new(7);
            let mut second = pool<Int>(1);
            let m = second.new(9);
            let mut leaves = pool<Leaf>(2);
            let a = leaves.new(data: &n);
            let b = leaves.new(data: &m);
            let mut links = pool<Link>(1);
            let left = new(links) Link.B { leaf: &a };
            let right = new(links) Link.A { leaf: &b };
        """
        for side, expected in ((0, '7\n'), (1, '9\n')):
            with self.subTest(side=side):
                run = self.native(source + f"""
                    let selected = choose(&left, &right, {side});
                    let projected = project(selected);
                    let value = projected.data;
                    print(*value);
                """)
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for pool in ('first', 'second'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
                verify_program(source + f"""
                    let selected = choose(&left, &right, 0);
                    let value = extract(selected, &mut {pool});
                    print(*value);
                """)
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source + """
                let selected = choose(&left, &right, 0);
                let projected = project(selected);
                drop(-> right);
                let value = projected.data;
                print(*value);
            """)

    def test_array_return_keeps_match_projections_from_each_carrier(self):
        source = """
            enum Link { A { data: &Int }, B { data: &Int } }
            fn wrap(link: &Link) -> [&Int; 1] {
                match &link {
                    Link.A { data: data } => { return <- [data]; },
                    Link.B { data: data } => { return <- [data]; }
                }
            }
            fn choose(a: &Link, b: &Link, side: Int) -> &Link {
                if side == 0 { return a; }
                return b;
            }
            let mut first = pool<Int>(1);
            let a = first.new(7);
            let mut second = pool<Int>(1);
            let b = second.new(9);
            let mut links = pool<Link>(1);
            let left = new(links) Link.A { data: &a };
            let right = new(links) Link.B { data: &b };
            let selected = choose(&left, &right, SIDE);
            let refs = wrap(selected);
        """
        for side, expected in ((0, '7\n'), (1, '9\n')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)) + 'print(*refs[0]);')
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for pool in ('first', 'second'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'référence de tableau'):
                verify_program(source.replace('SIDE', '0') + f'{pool}.reset(); print(*refs[0]);')

    def test_owned_return_keeps_stored_match_projections_from_each_carrier(self):
        source = """
            struct View { data: &Int }
            enum Link { A { data: &Int }, B { data: &Int } }
            fn wrap(link: &Link, out: &mut Pool<View>) -> <- A<View> {
                match &link {
                    Link.A { data: data } => {
                        let view = out.new(data: data);
                        return <- view;
                    },
                    Link.B { data: data } => {
                        let view = out.new(data: data);
                        return <- view;
                    }
                }
            }
            fn choose(a: &Link, b: &Link, side: Int) -> &Link {
                if side == 0 { return a; }
                return b;
            }
            let mut first = pool<Int>(1);
            let a = first.new(7);
            let mut second = pool<Int>(1);
            let b = second.new(9);
            let mut links = pool<Link>(1);
            let left = new(links) Link.A { data: &a };
            let right = new(links) Link.B { data: &b };
            let selected = choose(&left, &right, SIDE);
            let mut views = pool<View>(1);
            let view = wrap(selected, &mut views);
        """
        use = 'let value = view.data; print(*value);'
        for side, expected in ((0, '7\n'), (1, '9\n')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)) + use)
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for reset in ('first.reset();', 'second.reset();'):
            with self.subTest(reset=reset), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('SIDE', '0') + reset + use)
        # A copied shared field retains its target, not the old carrier.
        run = self.native(source.replace('SIDE', '0') + 'drop(-> right);' + use)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('SIDE', '0') + 'drop(-> b);' + use)

    def test_match_expression_returns_typed_shared_projection(self):
        declarations = """
            struct Leaf { data: &Int }
            struct Other { data: &Int }
            enum Link { A { leaf: &Leaf }, B { leaf: &Leaf } }
            fn project(link: &Link) -> &Leaf {
                return match &link {
                    Link.A { leaf: leaf } => { leaf },
                    Link.B { leaf: leaf } => { leaf }
                };
            }
        """
        source = declarations + """
            let mut values = pool<Int>(1);
            let data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &data);
            let mut links = pool<Link>(1);
            let link = new(links) Link.B { leaf: &leaf };
            let view = project(&link);
            CHECK
            let value = view.data;
            print(*value);
            drop(-> link);
        """
        mutable_source = (source.replace('link: &Link', 'link: &mut Link')
                          .replace('match &link', 'match &mut link')
                          .replace('let link = new', 'let mut link = new')
                          .replace('project(&link)', 'project(&mut link)'))
        for case in (source, mutable_source):
            run = self.native(case.replace('CHECK', ''))
            self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(case.replace('CHECK', 'drop(-> link);'))
        with self.assertRaisesRegex(Error, 'même type et même mode'):
            verify_program(declarations.replace('B { leaf: &Leaf }', 'B { leaf: &Other }'))

    def test_match_expression_early_return_has_function_result_type(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &Leaf }, End }
            fn read(link: &Link, fallback: &Leaf, temporary: &mut Pool<Int>) -> Int {
                let value = match &link {
                    Link.Node { leaf: leaf } => {
                        let scratch = temporary.new(11);
                        print(scratch);
                        return leaf.data;
                    },
                    Link.End => { fallback }
                };
                return value.data;
            }
            let mut leaves = pool<Leaf>(2);
            let leaf = leaves.new(data: 7);
            let fallback = leaves.new(data: 9);
            let mut links = pool<Link>(1);
            let node = new(links) Link.Node { leaf: &leaf };
            let end = new(links) Link.End;
            let mut temporary = pool<Int>(1);
            print(read(&node, &fallback, &mut temporary));
            print(read(&end, &fallback, &mut temporary));
            let reused = temporary.new(13);
            print(reused);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '11\n7\n9\n13\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy scratch=11\n'), 1)
        # U1 requires a use, but keep destruction at the early return so this
        # remains an oracle for scope cleanup rather than an explicit drop.
        with self.assertRaisesRegex(Error, 'sans usage explicite'):
            verify_program(source.replace('print(scratch);', ''))
        with self.assertRaisesRegex(Error, 'retour|type'):
            verify_program(source.replace('return leaf.data;', 'return leaf;'))

    def test_mutable_typed_match_projection_keeps_exclusive_target(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &mut Leaf }, End }
            fn run() -> Int {
                let mut leaves = pool<Leaf>(1);
                let mut leaf = leaves.new(data: 7);
                let mut links = pool<Link>(1);
                let mut link = new(links) Link.Node { leaf: &mut leaf };
                CHECK
                match &mut link {
                    Link.Node { leaf: child } => { child.data = 9; },
                    Link.End => {}
                }
                drop(-> link);
                return leaf.data;
            }
            print(run());
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        for statement in ('print(leaf.data);', 'leaf.data = 8;'):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'leaves.reset();'))
        with self.assertRaisesRegex(Error, 'match de lecture'):
            verify_program(source.replace('CHECK', '').replace('match &mut link', 'match &link'))
        with self.assertRaisesRegex(Error, 'structure non copiable'):
            verify_program("""
                struct Leaf { data: Int }
                struct Link { leaf: &mut Leaf }
                let mut leaves = pool<Leaf>(1);
                let mut leaf = leaves.new();
                let mut links = pool<Link>(2);
                let link = links.new(leaf: &mut leaf);
                let copied = copy(link);
            """)

    def test_typed_mutable_field_contract_reserves_carrier_and_target(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &mut Leaf } }
            fn project(link: &mut Link) -> &mut Leaf {
                return match &mut link { Link.Node { leaf: child } => { child } };
            }
            fn relay(link: &mut Link) -> &mut Leaf { return project(link); }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut links = pool<Link>(1);
            let mut link = new(links) Link.Node { leaf: &mut leaf };
            let mut view = relay(&mut link);
            CHECK
            view.data = 9;
            drop(-> link);
            print(leaf.data);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        for statement, diagnostic in (
            ('print(leaf.data);', 'emprunt actif'),
            ('match &link { Link.Node { leaf: child } => { let n = child.data; print(n); } }',
             'emprunt actif'),
            ('drop(-> link);', 'emprunt encore utilisé'),
            ('links.reset();', 'reset interdit'),
            ('leaves.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_typed_mutable_match_reserves_all_possible_carriers(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &mut Leaf } }
            fn project(link: &mut Link) -> &mut Leaf {
                return match &mut link { Link.Node { leaf: child } => { child } };
            }
            fn relay(link: &mut Link) -> &mut Leaf { return project(link); }
            fn choose(a: &mut Link, b: &mut Link, side: Int) -> &mut Link {
                if side == 0 { return a; }
                return b;
            }
            let mut first = pool<Leaf>(1);
            let mut a = first.new(data: 7);
            let mut second = pool<Leaf>(1);
            let mut b = second.new(data: 8);
            let mut links = pool<Link>(2);
            let mut left = new(links) Link.Node { leaf: &mut a };
            let mut right = new(links) Link.Node { leaf: &mut b };
            let mut selected = choose(&mut left, &mut right, SIDE);
            let mut view = relay(selected);
            CHECK
            view.data = 9;
            drop(-> left);
            drop(-> right);
            print(a.data);
            print(b.data);
        """
        for side, expected in ((0, '9\n8\n'), (1, '7\n9\n')):
            with self.subTest(side=side):
                run = self.native(source.replace('SIDE', str(side)).replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        for statement, diagnostic in (
            ('drop(-> right);', 'emprunt encore utilisé'),
            ('first.reset();', 'reset interdit'),
            ('second.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('SIDE', '0').replace('CHECK', statement))

    def test_direct_typed_field_reborrow_survives_function_relay(self):
        source = """
            struct Leaf { data: Int }
            struct Link { leaf: &mut Leaf }
            fn project(link: &mut Link) -> &mut Leaf { return &mut *link.leaf; }
            fn relay(link: &mut Link) -> &mut Leaf { return project(link); }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut links = pool<Link>(1);
            let mut link = links.new(leaf: &mut leaf);
            let mut view = BORROW;
            CHECK
            view.data = 9;
            drop(-> link);
            print(leaf.data);
        """
        for borrow in ('&mut *link.leaf', 'relay(&mut link)'):
            with self.subTest(borrow=borrow):
                case = source.replace('BORROW', borrow)
                run = self.native(case.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
                for statement, diagnostic in (
                    ('drop(-> link);', 'emprunt encore utilisé'),
                    ('leaf.data = 8;', 'emprunt actif'),
                ):
                    with self.assertRaisesRegex(Error, diagnostic):
                        verify_program(case.replace('CHECK', statement))
        shared = source.replace('let mut view = BORROW;', 'let view = &*link.leaf;')
        shared = shared.replace('view.data = 9;', 'print(view.data);')
        run = self.native(shared.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n7\n'), run.stderr)

    def test_direct_typed_reborrows_allow_disjoint_fields(self):
        source = """
            struct Leaf { data: Int }
            struct Link { first: &mut Leaf, second: &mut Leaf, marker: Int }
            fn project(link: &mut Link) -> &mut Leaf { return &mut *link.first; }
            let mut leaves = pool<Leaf>(2);
            let mut a = leaves.new(data: 7);
            let mut b = leaves.new(data: 8);
            let mut links = pool<Link>(1);
            let mut link = links.new(first: &mut a, second: &mut b);
            let mut left = BORROW;
            CHECK
            let mut right = &mut *link.second;
            link.marker = 3;
            left.data = 9;
            right.data = 10;
            print(link.marker);
            drop(-> link);
            print(a.data);
            print(b.data);
        """
        for borrow in ('&mut *link.first', 'project(&mut link)'):
            with self.subTest(borrow=borrow):
                case = source.replace('BORROW', borrow)
                run = self.native(case.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '3\n9\n10\n'), run.stderr)
                for statement in ('b.data = 2;', 'let mut again = &mut *link.first; again.data = 2;'):
                    with self.subTest(statement=statement), self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(case.replace('CHECK', statement))

    def test_typed_field_reborrow_return_uses_post_update_target(self):
        source = """
            struct Leaf { data: Int, shared: &Int }
            struct Link { leaf: &mut Leaf }
            fn update(link: &mut Link, next: &mut Leaf) -> &mut Leaf {
                link.leaf = &mut *next;
                return &mut *link.leaf;
            }
            fn read(link: &mut Link, next: &mut Leaf) -> &Int {
                let mut view = update(link, next);
                view.data = 9;
                return view.shared;
            }
            let mut left = pool<Int>(1);
            let a = left.new(1);
            let mut right = pool<Int>(1);
            let b = right.new(2);
            let mut leaves = pool<Leaf>(2);
            let mut old = leaves.new(data: 7, shared: &a);
            let mut next = leaves.new(data: 8, shared: &b);
            let mut links = pool<Link>(1);
            let mut link = links.new(leaf: &mut old);
            let view = read(&mut link, &mut next);
            drop(-> link);
            print(old.data);
            print(next.data);
            drop(-> old);
        """
        run = self.native(source + 'left.reset(); print(*view);')
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n2\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source + 'right.reset(); print(*view);')

    def test_reset_after_typed_field_update_uses_post_update_dependencies(self):
        source = """
            struct Leaf { data: Int }
            struct Link { leaf: &mut Leaf }
            fn update(link: &mut Link, next: &mut Leaf) -> &mut Leaf {
                link.leaf = &mut *next;
                return &mut *link.leaf;
            }
            fn forward(link: &mut Link, next: &mut Leaf, memory: &mut Pool<Leaf>) -> Int {
                let mut view = update(link, next);
                memory.reset();
                view.data = 9;
                return view.data;
            }
            let mut previous = pool<Leaf>(1);
            let mut old = previous.new(data: 7);
            let mut replacement = pool<Leaf>(1);
            let mut next = replacement.new(data: 8);
            let mut links = pool<Link>(1);
            let mut link = links.new(leaf: &mut old);
            print(forward(&mut link, &mut next, &mut TARGET));
            drop(-> link);
            print(next.data);
        """
        valid = source.replace('TARGET', 'previous')
        run = self.native(valid)
        self.assertEqual((run.returncode, run.stdout), (0, '9\n9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy old=Leaf\n'), 1)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('TARGET', 'replacement'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(valid.replace(
                'let mut view = update(link, next);\n                memory.reset();',
                'memory.reset();\n                let mut view = update(link, next);',
            ))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(valid + 'print(old.data);')

    def test_nested_typed_mutable_fields_share_the_underlying_capability(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &mut Leaf }
            struct Top { mid: &mut Mid }
            fn project(top: &mut Top) -> &mut Mid { return &mut *top.mid; }
            fn edit(leaf: &mut Leaf) { leaf.data = 9; }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut mids = pool<Mid>(1);
            let mut mid = mids.new(leaf: &mut leaf);
            let mut tops = pool<Top>(1);
            let mut top = tops.new(mid: &mut mid);
            CHECK
            let mut middle = BORROW;
            edit(&mut *middle.leaf);
            drop(-> top);
            drop(-> mid);
            print(leaf.data);
        """
        for borrow in ('&mut *top.mid', 'project(&mut top)'):
            with self.subTest(borrow=borrow):
                case = source.replace('BORROW', borrow)
                run = self.native(case.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
                for statement, diagnostic in (
                    ('print(leaf.data);', 'emprunt actif'),
                    ('drop(-> mid);', 'emprunt encore utilisé'),
                    ('leaves.reset();', 'reset interdit'),
                ):
                    with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                        verify_program(case.replace('CHECK', statement))

    def test_projected_mutable_arguments_keep_only_returned_field_reserved(self):
        source = """
            struct Leaf { data: Int }
            struct Pair { left: &mut Leaf, right: &mut Leaf }
            fn choose(a: &mut Leaf, b: &mut Leaf) -> &mut Leaf {
                a.data = 1;
                b.data = 2;
                return a;
            }
            let mut leaves = pool<Leaf>(2);
            let mut a = leaves.new();
            let mut b = leaves.new();
            let mut pairs = pool<Pair>(1);
            let mut pair = pairs.new(left: &mut a, right: &mut b);
            let mut kept = choose(&mut *pair.left, &mut *pair.right);
            let mut sibling = &mut *pair.right;
            sibling.data = 5;
            kept.data = 3;
            drop(-> pair);
            print(a.data);
            print(b.data);
        """
        for first, second, output in (('left', 'right', '3\n5\n'), ('right', 'left', '5\n3\n')):
            with self.subTest(first=first):
                call = f'choose(&mut *pair.{first}, &mut *pair.{second})'
                variant = source.replace('choose(&mut *pair.left, &mut *pair.right)', call)
                variant = variant.replace('sibling = &mut *pair.right', f'sibling = &mut *pair.{second}')
                run = self.native(variant)
                self.assertEqual((run.returncode, run.stdout), (0, output), run.stderr)
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(variant.replace(call, f'choose(&mut *pair.{first}, &mut *pair.{first})'))
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(variant.replace(f'sibling = &mut *pair.{second}',
                                                   f'sibling = &mut *pair.{first}'))
                with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(variant.replace('kept.data = 3;', 'drop(-> pair); kept.data = 3;'))

    def test_shared_typed_link_preserves_inherited_mutable_capability(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &mut Leaf }
            struct Top { mid: &Mid }
            fn project(top: &Top) -> &Mid { return top.mid; }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut mids = pool<Mid>(1);
            let mid = mids.new(leaf: &mut leaf);
            let mut tops = pool<Top>(2);
            let top = tops.new(mid: &mid);
            let copied = copy(top);
            drop(-> top);
            let middle = project(&copied);
            let view = &*middle.leaf;
            CHECK
            print(view.data);
            drop(-> copied);
            drop(-> mid);
            print(leaf.data);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n7\n'), run.stderr)
        for statement, diagnostic in (
            ('print(leaf.data);', 'emprunt actif'),
            ('leaf.data = 8;', 'emprunt actif'),
            ('let mut bad = &mut *middle.leaf; bad.data = 9;', 'emprunté en lecture'),
            ('drop(-> mid);', 'emprunt encore utilisé'),
            ('mids.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_nested_typed_reborrow_return_retains_each_carrier(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &mut Leaf }
            struct Top { mid: &mut Mid }
            fn terminal(top: &mut Top) -> &mut Leaf {
                let mut middle = &mut *top.mid;
                return &mut *middle.leaf;
            }
            fn project(top: &mut Top) -> &mut Mid { return &mut *top.mid; }
            fn finish(mid: &mut Mid) -> &mut Leaf { return &mut *mid.leaf; }
            fn relay(top: &mut Top) -> &mut Leaf {
                let mut middle = project(top);
                return finish(middle);
            }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut mids = pool<Mid>(1);
            let mut mid = mids.new(leaf: &mut leaf);
            let mut tops = pool<Top>(1);
            let mut top = tops.new(mid: &mut mid);
            let mut terminal = CALL;
            CHECK
            terminal.data = 9;
            drop(-> top);
            drop(-> mid);
            print(leaf.data);
        """
        for name in ('terminal', 'relay'):
            with self.subTest(name=name):
                case = source.replace('CALL', name + '(&mut top)')
                run = self.native(case.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
                for statement, diagnostic in (
                    ('drop(-> top);', 'emprunt encore utilisé'),
                    ('drop(-> mid);', 'emprunt encore utilisé'),
                    ('leaves.reset();', 'reset interdit'),
                ):
                    with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                        verify_program(case.replace('CHECK', statement))

    def test_mixed_typed_reborrow_releases_only_detached_prefix(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &mut Leaf }
            struct Top { mid: &Mid }
            fn terminal(top: &Top) -> &Leaf {
                let middle = top.mid;
                return &*middle.leaf;
            }
            fn finish(mid: &Mid) -> &Leaf { return &*mid.leaf; }
            fn relay(top: &Top) -> &Leaf {
                let middle = top.mid;
                return finish(middle);
            }
            fn read(top: &Top, memory: &mut Pool<Top>) -> Int {
                let view = relay(top);
                memory.reset();
                return view.data;
            }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut mids = pool<Mid>(1);
            let mid = mids.new(leaf: &mut leaf);
            let mut tops = pool<Top>(1);
            let top = tops.new(mid: &mid);
        """
        run = self.native(source + 'print(read(&top, &mut tops));')
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        tail = 'let view = terminal(&top); drop(-> top); CHECK print(view.data);'
        run = self.native(source + tail.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        for statement, diagnostic in (
            ('drop(-> mid);', 'emprunt encore utilisé'),
            ('leaves.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source + tail.replace('CHECK', statement))

    def test_owned_return_stores_mixed_typed_reborrow_path(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &mut Leaf }
            struct Top { mid: &Mid }
            struct Saved { leaf: &Leaf }
            fn terminal(top: &Top) -> &Leaf {
                let middle = top.mid;
                return &*middle.leaf;
            }
            fn wrap(top: &Top, saved: &mut Pool<Saved>) -> <- A<Saved> {
                let view = terminal(top);
                let result = saved.new(leaf: view);
                return <- result;
            }
            fn relay(top: &Top, saved: &mut Pool<Saved>) -> <- A<Saved> {
                let result = wrap(top, saved);
                return <- result;
            }
            fn read(top: &Top, memory: &mut Pool<Top>, saved: &mut Pool<Saved>) -> Int {
                let result = relay(top, saved);
                memory.reset();
                let view = result.leaf;
                return view.data;
            }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut mids = pool<Mid>(1);
            let mid = mids.new(leaf: &mut leaf);
            let mut tops = pool<Top>(1);
            let top = tops.new(mid: &mid);
            let mut saved = pool<Saved>(1);
        """
        run = self.native(source + 'print(read(&top, &mut tops, &mut saved));')
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        tail = """
            let result = relay(&top, &mut saved);
            drop(-> top);
            let view = result.leaf;
            CHECK
            print(view.data);
        """
        run = self.native(source + tail.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        for statement, diagnostic in (
            ('drop(-> mid);', 'emprunt encore utilisé'),
            ('leaves.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source + tail.replace('CHECK', statement))

    def test_shared_field_detaches_after_traversing_mutable_link(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &Leaf }
            struct Top { mid: &mut Mid }
            fn detach(top: &mut Top) -> &Leaf {
                let mut middle = &mut *top.mid;
                return middle.leaf;
            }
            fn relay(top: &mut Top) -> &Leaf { return detach(top); }
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: 7);
            let mut mids = pool<Mid>(1);
            let mut mid = mids.new(leaf: &leaf);
            let mut tops = pool<Top>(1);
            let mut top = tops.new(mid: &mut mid);
            let view = relay(&mut top);
            drop(-> top);
            drop(-> mid);
            CHECK
            print(view.data);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'leaves.reset();'))

    def test_owned_return_stores_nested_exclusive_reborrow(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &mut Leaf }
            struct Top { mid: &mut Mid }
            struct Saved { leaf: &mut Leaf }
            fn terminal(top: &mut Top) -> &mut Leaf {
                let mut mid = &mut *top.mid;
                return &mut *mid.leaf;
            }
            fn wrap(top: &mut Top, output: &mut Pool<Saved>) -> <- A<Saved> {
                let mut view = terminal(top);
                let result = output.new(leaf: view);
                return <- result;
            }
            fn relay(top: &mut Top, output: &mut Pool<Saved>) -> <- A<Saved> {
                let result = wrap(top, output);
                return <- result;
            }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut mids = pool<Mid>(1);
            let mut mid = mids.new(leaf: &mut leaf);
            let mut tops = pool<Top>(1);
            let mut top = tops.new(mid: &mut mid);
            let mut saved = pool<Saved>(1);
            let mut result = relay(&mut top, &mut saved);
            CHECK
            let mut view = &mut *result.leaf;
            view.data = 9;
            drop(-> result);
            drop(-> top);
            drop(-> mid);
            print(leaf.data);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        for statement, diagnostic in (
            ('drop(-> top);', 'emprunt encore utilisé'),
            ('drop(-> mid);', 'emprunt encore utilisé'),
            ('leaves.reset();', 'reset interdit'),
            ('print(leaf.data);', 'emprunt actif'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_match_arm_calls_void_method_on_typed_projection(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &mut Leaf } }
            impl Leaf {
                fn write(self: &mut Leaf, value: Int) { self.data = value; }
                fn read(self: &Leaf) -> Int { return self.data; }
            }
            fn update(link: &mut Link) {
                match &mut link { Link.Node { leaf: child } => { child.write(9); } }
            }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut links = pool<Link>(1);
            let mut link = new(links) Link.Node { leaf: &mut leaf };
            update(&mut link);
            drop(-> link);
            print(leaf.data);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'lecture ne peut pas devenir mutable'):
            verify_program(source.replace('match &mut link', 'match &link'))
        with self.assertRaisesRegex(Error, 'résultat de fonction sans receveur'):
            verify_program(source.replace('child.write(9);', 'child.read();'))

    def test_match_arm_receives_method_reborrow_until_last_use(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &mut Leaf } }
            impl Leaf {
                fn edit(self: &mut Leaf) -> &mut Int { return &mut self.data; }
            }
            fn update(link: &mut Link) {
                match &mut link {
                    Link.Node { leaf: child } => {
                        let mut view = child.edit();
                        CHECK
                        view.set(9);
                        let observed = child.data;
                        print(observed);
                        child.data = 10;
                    }
                }
            }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut links = pool<Link>(1);
            let mut link = new(links) Link.Node { leaf: &mut leaf };
            update(&mut link);
            drop(-> link);
            print(leaf.data);
        """
        for name, parameter, argument in (('edit', '', ''), ('join', '', ''),
                                          ('split_at_mut', ', index: Int', '0')):
            with self.subTest(name=name):
                program = source.replace('edit(self: &mut Leaf)', f'{name}(self: &mut Leaf{parameter})')
                program = program.replace('child.edit()', f'child.{name}({argument})')
                run = self.native(program.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '9\n10\n'), run.stderr)
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('CHECK', 'child.data = 8;'))
                with self.assertRaisesRegex(Error, 'lecture ne peut pas devenir mutable'):
                    verify_program(program.replace('match &mut link', 'match &link').replace(
                        'CHECK\n                        view.set(9);\n                        let observed = child.data;\n'
                        '                        print(observed);\n                        child.data = 10;',
                        'print(view);',
                    ))

    def test_match_expression_uses_typed_method_result_and_pool_effects(self):
        source = """
            struct Leaf { data: &Int }
            enum Link { Node { leaf: &Leaf }, End }
            impl Leaf {
                fn read(self: &Leaf, memory: &mut Pool<Int>) -> Int {
                    memory.reset();
                    let view = self.data;
                    return *view;
                }
            }
            fn read(link: &Link, memory: &mut Pool<Int>, fallback: &Int) -> Int {
                return match &link {
                    Link.Node { leaf: child } => { child.read(memory) },
                    Link.End => { *fallback }
                };
            }
            let mut values = pool<Int>(2);
            let n = values.new(7);
            let fallback = values.new(9);
            let mut leaves = pool<Leaf>(1);
            let leaf = leaves.new(data: &n);
            let mut links = pool<Link>(1);
            let node = new(links) Link.Node { leaf: &leaf };
            let end = new(links) Link.End;
            let mut other = pool<Int>(1);
            print(read(&node, &mut TARGET, &fallback));
            print(read(&end, &mut other, &fallback));
        """
        valid = source.replace('TARGET', 'other')
        run = self.native(valid)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source.replace('TARGET', 'values'))
        with self.assertRaisesRegex(Error, 'même type et même mode'):
            verify_program(valid.replace('Link.End => { *fallback }', 'Link.End => { fallback }'))

    def test_match_method_returns_inline_field_through_typed_projection(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &mut Leaf } }
            impl Leaf {
                fn edit(self: &mut Leaf) -> &mut Int { return &mut self.data; }
            }
            fn project(link: &mut Link) -> &mut Int {
                return match &mut link { Link.Node { leaf: child } => { child.edit() } };
            }
            fn relay(link: &mut Link) -> &mut Int { return project(link); }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut links = pool<Link>(1);
            let mut link = new(links) Link.Node { leaf: &mut leaf };
            let mut view = relay(&mut link);
            CHECK
            view.set(11);
            drop(-> link);
            print(leaf.data);
        """
        for name, parameter, argument in (('edit', '', ''), ('join', '', ''),
                                          ('split_at_mut', ', index: Int', '0')):
            with self.subTest(name=name):
                program = source.replace('edit(self: &mut Leaf)', f'{name}(self: &mut Leaf{parameter})')
                program = program.replace('child.edit()', f'child.{name}({argument})')
                run = self.native(program.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '11\n'), run.stderr)
                for statement, diagnostic in (
                    ('drop(-> link);', 'emprunt encore utilisé'),
                    ('leaves.reset();', 'reset interdit'),
                    ('leaf.data = 8;', 'emprunt actif'),
                ):
                    with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                        verify_program(program.replace('CHECK', statement))

        reset_after_relay = source.replace(
            '            let mut leaves = pool<Leaf>(1);',
            """            fn reset_after(link: &mut Link, memory: &mut Pool<Leaf>) -> Int {
                let mut view = relay(link);
                memory.reset();
                view.set(11);
                return *view;
            }
            let mut leaves = pool<Leaf>(1);""",
        ).split('            let mut view = relay(&mut link);')[0]
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(reset_after_relay + 'print(reset_after(&mut link, &mut leaves));')

    def test_match_method_reborrows_stored_field_through_typed_projection(self):
        source = """
            struct Leaf { data: &mut Int }
            enum Link { Node { leaf: &mut Leaf } }
            struct Top { link: &mut Link }
            impl Leaf {
                fn edit(self: &mut Leaf) -> &mut Int { return &mut *self.data; }
            }
            fn project(link: &mut Link) -> &mut Int {
                return match &mut link { Link.Node { leaf: child } => { child.edit() } };
            }
            fn relay(top: &mut Top) -> &mut Int {
                let mut link = &mut *top.link;
                return project(link);
            }
            let mut values = pool<Int>(1);
            let mut data = values.new(7);
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: &mut data);
            let mut links = pool<Link>(1);
            let mut link = new(links) Link.Node { leaf: &mut leaf };
            let mut tops = pool<Top>(1);
            let mut top = tops.new(link: &mut link);
            let mut view = relay(&mut top);
            CHECK
            view.set(11);
            drop(-> top);
            drop(-> link);
            drop(-> leaf);
            print(data);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '11\n'), run.stderr)
        for statement, diagnostic in (
            ('data.set(8);', 'emprunt actif'),
            ('drop(-> top);', 'emprunt encore utilisé'),
            ('drop(-> link);', 'emprunt encore utilisé'),
            ('leaves.reset();', 'reset interdit'),
            ('values.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_match_method_inline_return_composes_detached_and_reserved_paths(self):
        source = """
            struct Leaf { data: Int }
            enum Link { Node { leaf: &mut Leaf } }
            struct Top { link: &Link }
            impl Leaf {
                fn read(self: &Leaf) -> &Int { return &self.data; }
            }
            fn project(link: &Link) -> &Int {
                return match &link { Link.Node { leaf: child } => { child.read() } };
            }
            fn relay(top: &Top) -> &Int {
                let link = top.link;
                return project(link);
            }
            let mut leaves = pool<Leaf>(1);
            let mut leaf = leaves.new(data: 7);
            let mut links = pool<Link>(1);
            let link = new(links) Link.Node { leaf: &mut leaf };
            let mut tops = pool<Top>(1);
            let top = tops.new(link: &link);
            let view = relay(&top);
            drop(-> top);
            CHECK
            print(*view);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        for statement, diagnostic in (
            ('drop(-> link);', 'emprunt encore utilisé'),
            ('leaves.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_recursive_enum_shared_links_match_terminal_variant(self):
        source = """
            enum Node { End { value: Int }, Link { next: &Node } }
            let mut ends = pool<Node>(1);
            let end = new(ends) Node.End { value: 7 };
            let mut links = pool<Node>(1);
            let mid = new(links) Node.Link { next: &end };
            let mut tops = pool<Node>(1);
            let top = new(tops) Node.Link { next: &mid };
            CHECK
            match &top {
                Node.End { value: value } => { print(value); },
                Node.Link { next: middle } => {
                    match &middle {
                        Node.End { value: value } => { print(value); },
                        Node.Link { next: last } => {
                            match &last {
                                Node.End { value: value } => { print(value); },
                                Node.Link { next: _ } => {}
                            }
                        }
                    }
                }
            }
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'ends.reset();'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('CHECK', 'drop(-> end);'))
        with self.assertRaisesRegex(Error, 'champs des variantes doivent être Int'):
            verify_program('enum Node { Invalid { next: Node } }')

    def test_recursive_enum_match_retains_all_referent_variants(self):
        source = """
            enum Node { End { value: Int }, Link { next: &Node } }
            let mut p = pool<Node>(4);
            let base = new(p) Node.End { value: 7 };
            let next = new(p) Node.Link { next: &base };
            let mut flag = FLAG;
            let chosen = if flag == 0 {
                let a = new(p) Node.Link { next: &base };
                <- a
            } else {
                let b = new(p) Node.Link { next: &next };
                <- b
            };
            match &chosen {
                Node.End { value: value } => { print(value); },
                Node.Link { next: target } => {
                    match &target {
                        Node.End { value: value } => { print(value); },
                        Node.Link { next: _ } => { let value = 9; print(value); }
                    }
                }
            }
        """
        for flag, output in ((0, '7\n'), (1, '9\n')):
            with self.subTest(flag=flag):
                run = self.native(source.replace('FLAG', str(flag)))
                self.assertEqual((run.returncode, run.stdout), (0, output), run.stderr)

    def test_mutable_reference_vector_moves_exclusive_loan(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a = p.new(7);
            let mut b = q.new(9);
            address(a);
            let mut first = &mut a;
            let mut second = &mut b;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> first);
            v.push(-> second);
            CHECK
            let mut extracted = <- v.remove(0);
            extracted.set(11);
            address(extracted);
            print(*extracted);
            p.reset();
            let mut last = <- v.remove(0);
            last.set(13);
            print(*last);
            drop(-> v);
            q.reset();
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, first, second = run.stdout.splitlines()
        self.assertEqual((returned, first, second), (original, '11', '13'))
        for statement, diagnostic in (
            ('print(*first);', 'déplacée'),
            ('print(*a);', 'emprunt actif'),
            ('p.reset();', 'reset interdit'),
            ('let stolen = v.remove(0);', 'extraction explicite'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'transfert explicite'):
            verify_program(source.replace('push(-> first)', 'push(first)').replace('CHECK', ''))

    def test_mutable_reference_vector_relays_extracted_loan(self):
        source = """
            fn extract(data: &mut Int) -> &mut Int {
                let mut vp = pool<Vector<&mut Int>>(1);
                let mut v = vp.new();
                v.push(-> data);
                let mut view = <- v.remove(0);
                return view;
            }
            let mut p = pool<Int>(1);
            let mut data = p.new(7);
            let mut view = extract(&mut data);
            CHECK
            view.set(9);
            print(*view);
            print(*data);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(*data);'))

    def test_mutable_reference_vector_reborrow_reserves_carrier(self):
        source = """
            let mut p = pool<Int>(1);
            let mut x = p.new(7);
            address(x);
            let mut incoming = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> incoming);
            let mut view = &mut *v[0];
            CHECK
            view.set(9);
            address(view);
            print(*view);
            print(*v[0]);
            let shared = &*v[0];
            print(*shared);
            drop(-> v);
            print(*x);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, *values = run.stdout.splitlines()
        self.assertEqual((returned, values), (original, ['9'] * 4))
        for statement, diagnostic in (
            ('drop(-> v);', 'emprunt encore utilisé'),
            ('let mut other = &mut *v[0]; other.set(10);', 'emprunt actif'),
            ('print(*v[0]);', 'emprunt actif'),
            ('p.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('CHECK', '').replace(
                'print(*shared);\n            drop(-> v);', 'drop(-> v); print(*shared);'))

    def test_mutable_reference_vector_disjoint_reborrows(self):
        source = """
            let mut p = pool<Int>(2);
            let mut x = p.new(7);
            let mut y = p.new(8);
            let mut a = &mut x;
            let mut b = &mut y;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            v.push(-> b);
            let index = 1;
            let mut first = &mut *v[0];
            let mut second = &mut *v[INDEX];
            CHECK
            first.set(11);
            second.set(12);
            print(*first);
            print(*second);
            print(*v[0]);
            print(*v[1]);
        """
        accepted = source.replace('INDEX', 'index')
        run = self.native(accepted.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '11\n12\n11\n12\n'), run.stderr)
        for index in ('0', 'index'):
            with self.subTest(index=index), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('let index =', 'let mut index =')
                               .replace('INDEX', index).replace('CHECK', ''))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(accepted.replace('CHECK', 'drop(-> v);'))

    def test_mutable_reference_vector_store_evaluates_destination_first(self):
        source = """
            fn index(i: Int) -> Int { print(1); return i; }
            fn next(value: Int) -> Int { print(2); return value + 1; }
            fn clear(memory: &mut Pool<Int>) -> Int { memory.reset(); return 0; }
            let mut p = pool<Int>(1);
            let mut x = p.new(7);
            let mut incoming = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> incoming);
            let old = &*v[0];
            *v[index(INDEX)] = RHS;
            print(*v[0]);
        """
        valid = source.replace('RHS', 'next(*old)')
        run = self.native(valid.replace('INDEX', '0'))
        self.assertEqual((run.returncode, run.stdout), (0, '1\n2\n8\n'), run.stderr)
        bounds = self.native(valid.replace('INDEX', '1'))
        self.assertNotEqual(bounds.returncode, 0)
        self.assertEqual(bounds.stdout, '1\n')
        self.assertIn('indice de Vector hors limites', bounds.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('INDEX', '0').replace('RHS', 'clear(&mut p)'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('INDEX', '0') + 'print(*old);')

    def test_mutable_reference_vector_pop_moves_option_exclusively(self):
        source = """
            let mut p = pool<Int>(1);
            let mut x = p.new(7);
            let mut a = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            let result: Option<&mut Int> = <- v.pop();
            CHECK
            print(v.len());
            match (-> result) {
                Some(view) => { view.set(9); print(*view); },
                None => { print(0); }
            }
            print(*x);
            match <- v.pop() {
                Some(view) => { print(*view); },
                None => { print(0); }
            }
            p.reset();
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '0\n9\n9\n0\n'), run.stderr)
        discarded = self.native(source.split('CHECK', 1)[0] + 'match (-> result) { _ => {} } print(*x);')
        self.assertEqual((discarded.returncode, discarded.stdout), (0, '7\n'), discarded.stderr)
        self.assertEqual(discarded.stderr.count('destroy x=7'), 1)
        for statement, diagnostic in (('p.reset();', 'reset interdit'),
                                      ('print(*x);', 'emprunt actif')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'déplacée'):
            verify_program(source.replace('CHECK', '').replace('print(*x);', 'drop(-> result);'))

    def test_mutable_reference_vector_replace_moves_selected_loan(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut x = p.new(7);
            let mut y = q.new(9);
            let mut a = &mut x;
            let mut b = &mut y;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            let result: Result<&mut Int, &mut Int> = <- v.replace(INDEX, -> b);
            CHECK
            match (-> result) {
                Ok(view) => { view.set(11); print(1); print(*view); },
                Err(view) => { view.set(13); print(0); print(*view); }
            }
            print(*v[0]);
        """
        for index, protected, expected in ((0, 'p', '1\n11\n9\n'), (1, 'q', '0\n13\n7\n')):
            with self.subTest(index=index):
                program = source.replace('INDEX', str(index))
                run = self.native(program.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('CHECK', f'{protected}.reset();'))
                with self.assertRaisesRegex(Error, 'déplacée'):
                    verify_program(program.replace('CHECK', 'print(*b);'))
                target = 'x' if index == 0 else 'y'
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('CHECK', f'print(*{target});'))
        direct = source.replace('INDEX', '1').replace('CHECK', '').replace(
            'let result: Result<&mut Int, &mut Int> = <- v.replace(1, -> b);', ''
        ).replace('match (-> result)', 'match <- v.replace(1, -> b)')
        run = self.native(direct)
        self.assertEqual((run.returncode, run.stdout), (0, '0\n13\n7\n'), run.stderr)

    def test_mutable_reference_vector_try_push_resolves_loan_in_match(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut x = p.new(7);
            let mut y = q.new(9);
            let mut a = &mut x;
            let mut b = &mut y;
            #(directive, stack_region_max_size=1M) {
                let mut vp = pool<Vector<&mut Int>>(1);
                let mut v = vp.new();
                v.push(-> a);
                let result: Result<(), &mut Int> = <- v.try_push(-> b);
                CHECK
                match (-> result) {
                    Ok(()) => { *v[1] = 11; print(*v[1]); },
                    Err(view) => { view.set(13); print(*view); }
                }
                print(v.len());
                print(*v[0]);
            }
        """
        accepted = source.replace('CHECK', '')
        run = self.native(accepted)
        self.assertEqual((run.returncode, run.stdout), (0, '11\n2\n7\n'), run.stderr)

        def one_slot(code):
            original = 'UINT64_C(1048576), sizeof(Cell *)'
            self.assertEqual(code.count(original), 1)
            return code.replace(original, 'sizeof(Cell *), sizeof(Cell *)')

        full = self.native(accepted, transform=one_slot)
        self.assertEqual((full.returncode, full.stdout), (0, '13\n1\n7\n'), full.stderr)
        direct = accepted.replace('let result: Result<(), &mut Int> = <- v.try_push(-> b);', '').replace(
            'match (-> result)', 'match <- v.try_push(-> b)')
        immediate = self.native(direct)
        self.assertEqual((immediate.returncode, immediate.stdout), (0, '11\n2\n7\n'), immediate.stderr)
        for statement in ('print(*y);', 'print(v.len());'):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('CHECK', statement))
        for pool in ('q', 'vp'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('CHECK', f'{pool}.reset();'))

    def test_mutable_reference_vector_borrowed_parameter_checks_targets(self):
        source = """
            fn read(v: &Vector<&mut Int>) -> Int { return *v[0]; }
            fn bump(v: &mut Vector<&mut Int>) { *v[0] = *v[0] + 1; }
            fn relay(v: &mut Vector<&mut Int>, other: &mut Pool<Int>) -> Int {
                other.reset();
                bump(v);
                return read(v);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut x = p.new(7);
            let mut incoming = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> incoming);
            print(relay(&mut v, &mut q));
            print(read(&v));
        """
        contract = verify_program(source).function_constraints['relay']
        self.assertTrue(any(
            requirement.relation == 'distinct'
            and {requirement.left.name, requirement.right.name} == {'', '.items'}
            for requirement in contract.requirements
        ))
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '8\n8\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source.replace('relay(&mut v, &mut q)', 'relay(&mut v, &mut p)'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(relay(&mut v, &mut q));',
                'let mut view = &mut *v[0]; print(relay(&mut v, &mut q)); print(*view);'))
        with self.assertRaisesRegex(Error, 'emprunt en lecture'):
            verify_program('fn bad(v: &Vector<&mut Int>) { *v[0] = 1; }')
        with self.assertRaisesRegex(Error, 'emprunt en lecture'):
            verify_program('fn bad(v: &Vector<&mut Int>, data: &mut Int) { let r = <- v.replace(0, -> data); }')

    def test_mutable_reference_vector_transfer_preserves_exclusive_slots(self):
        source = """
            fn make(out: &mut Pool<Vector<&mut Int>>, a: &mut Int, b: &mut Int) -> <- Vector<&mut Int> {
                let mut v = out.new();
                v.push(-> a);
                v.push(-> b);
                return <- v;
            }
            fn relay(v: -> Vector<&mut Int>) -> <- Vector<&mut Int> { return <- v; }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut x = p.new(7);
            let mut y = q.new(9);
            address(x);
            let mut original = &mut x;
            let mut out = pool<Vector<&mut Int>>(1);
            let v = make(&mut out, original, &mut y);
            let mut received = relay(-> v);
            CHECK
            let mut view = <- received.remove(0);
            view.set(11);
            address(view);
            print(*view);
            print(*original);
            p.reset();
            print(*received[0]);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, edited, resumed, remaining = run.stdout.splitlines()
        self.assertEqual((returned, edited, resumed, remaining), (original, '11', '11', '9'))
        for statement, diagnostic in (
            ('print(*original);', 'emprunt actif'),
            ('print(*x);', 'emprunt actif'),
            ('print(v.len());', 'déplacée'),
            ('p.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program('''
                fn bad(out: &mut Pool<Vector<&mut Int>>) -> <- Vector<&mut Int> {
                    let mut p = pool<Int>(1);
                    let mut x = p.new(7);
                    let mut view = &mut x;
                    let mut v = out.new();
                    v.push(-> view);
                    return <- v;
                }
            ''')

    def test_mutable_reference_vector_injected_push_preserves_parent(self):
        source = """
            fn add(v: &mut Vector<&mut Int>, data: &mut Int) { v.push(-> data); }
            fn relay(v: &mut Vector<&mut Int>, data: &mut Int) { add(v, data); }
            let mut p = pool<Int>(1);
            let mut x = p.new(7);
            let mut parent = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            relay(&mut v, parent);
            CHECK
            *v[0] = 9;
            print(*v[0]);
            drop(-> v);
            print(*parent);
            p.reset();
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '9\n9\n'), run.stderr)
        for statement, diagnostic in (
            ('print(*parent);', 'emprunt actif'),
            ('print(*x);', 'emprunt actif'),
            ('p.reset();', 'reset interdit'),
            ('relay(&mut v, parent);', 'emprunt actif'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(source.replace('relay(&mut v, parent);',
                '{ let mut q = pool<Int>(1); let mut y = q.new(8); relay(&mut v, &mut y); }')
                .replace('CHECK', ''))

    def test_mutable_reference_vector_injected_try_push_updates_caller(self):
        source = """
            fn add(v: &mut Vector<&mut Int>, data: &mut Int) -> Int {
                let result = <- v.try_push(-> data);
                match (-> result) {
                    Ok(()) => { return 1; },
                    Err(view) => { view.set(13); return *view; }
                }
            }
            let mut p = pool<Int>(2);
            let mut x = p.new(7);
            let mut y = p.new(9);
            let mut incoming = &mut x;
            #(directive, stack_region_max_size=1M) {
                let mut vp = pool<Vector<&mut Int>>(1);
                let mut v = vp.new();
                v.push(-> incoming);
                print(add(&mut v, &mut y));
                print(v.len());
                print(*v[0]);
                drop(-> v);
                print(*y);
            }
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '1\n2\n7\n9\n'), run.stderr)
        full = self.native(source, transform=lambda code: code.replace(
            'UINT64_C(1048576), sizeof(Cell *)', 'sizeof(Cell *), sizeof(Cell *)'))
        self.assertEqual((full.returncode, full.stdout), (0, '13\n1\n7\n13\n'), full.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(v.len());', 'print(*y); print(v.len());'))

    def test_mutable_reference_vector_returned_reborrow_reserves_case(self):
        source = """
            fn first(v: &mut Vector<&mut Int>) -> &mut Int { return &mut *v[0]; }
            fn relay(v: &mut Vector<&mut Int>) -> &mut Int { return first(v); }
            fn read(v: &Vector<&mut Int>) -> &Int { return &*v[0]; }
            let mut p = pool<Int>(2);
            let mut x = p.new(7);
            let mut y = p.new(8);
            let mut a = &mut x;
            let mut b = &mut y;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            v.push(-> b);
            let mut first = relay(&mut v);
            CHECK
            let mut second = &mut *v[1];
            first.set(11);
            second.set(12);
            print(*first);
            print(*second);
            let shared = read(&v);
            print(*shared);
            drop(-> v);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '11\n12\n11\n'), run.stderr)
        for statement, diagnostic in (
            ('drop(-> v);', 'emprunt encore utilisé'),
            ('let other = &*v[0]; print(*other);', 'emprunt actif'),
            ('vp.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('CHECK', '').replace(
                'print(*shared);\n            drop(-> v);', 'drop(-> v); print(*shared);'))
        with self.assertRaisesRegex(Error, 'capacité du vecteur'):
            verify_program('fn bad(v: &Vector<&mut Int>) -> &mut Int { return &mut *v[0]; }')
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program('''
                fn changed(v: &mut Vector<&mut Int>, data: &mut Int) -> &mut Int {
                    v.push(-> data);
                    return &mut *v[0];
                }
            ''')

    def test_mutable_reference_vector_dynamic_index_with_unique_outcome(self):
        source = """
            fn index(i: Int) -> Int { print(1); return i; }
            let mut p = pool<Int>(1);
            let mut x = p.new(7);
            let mut a = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            let mut view = <- v.remove(index(INDEX));
            CHECK
            view.set(9);
            print(*view);
            print(v.len());
        """
        valid = source.replace('INDEX', '0')
        run = self.native(valid.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '1\n9\n0\n'), run.stderr)
        bounds = self.native(source.replace('INDEX', '1').replace('CHECK', ''))
        self.assertNotEqual(bounds.returncode, 0)
        self.assertEqual(bounds.stdout, '1\n')
        self.assertIn('indice de Vector hors limites', bounds.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(valid.replace('CHECK', 'p.reset();'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('pool<Int>(1)', 'pool<Int>(2)').replace(
                'v.push(-> a);', 'v.push(-> a); let mut y = p.new(8); let b = &mut y; v.push(-> b);'
            ).replace('CHECK', 'print(*v[0]);'))

        empty = source.split('v.push(-> a);', 1)[0] + """
            let result = <- v.replace(index(0), -> a);
            match (-> result) {
                Ok(view) => { print(*view); },
                Err(view) => { view.set(11); print(*view); }
            }
            print(v.len());
        """
        run = self.native(empty)
        self.assertEqual((run.returncode, run.stdout), (0, '1\n11\n0\n'), run.stderr)

    def test_mutable_reference_vector_injected_push_keeps_case_order(self):
        source = """
            fn add(v: &mut Vector<&mut Int>, data: &mut Int) { v.push(-> data); }
            fn relay(v: &mut Vector<&mut Int>, data: &mut Int) { add(v, data); }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut x = p.new(7);
            let mut y = q.new(9);
            let mut a = &mut x;
            let mut b = &mut y;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            relay(&mut v, b);
            let mut removed = <- v.remove(0);
            removed.set(11);
            print(*removed);
            RESET
            print(*v[0]);
        """
        run = self.native(source.replace('RESET', 'p.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '11\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('RESET', 'q.reset();'))
        conditional = source.replace('data: &mut Int) { add(v, data); }',
            'data: &mut Int, flag: Int) { if flag == 1 { add(v, data); } }').replace(
            'relay(&mut v, b);', 'relay(&mut v, b, 1);')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(conditional.replace('RESET', 'p.reset();'))

    def test_immutable_indices_check_array_bounds_and_move_vector_cases(self):
        with self.assertRaisesRegex(Error, 'indice hors limites du tableau'):
            verify_program('let a = [7]; let zero = 0; let i = zero + 1; print(a[i]);')
        source = """
            let a = [4, 6];
            let one = 1;
            let zero = one - 1;
            print(a[one]);
            let mut p = pool<Int>(3);
            let mut x = p.new(7);
            let mut y = p.new(8);
            let mut z = p.new(9);
            let mut first = &mut x;
            let mut second = &mut y;
            let mut incoming = &mut z;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> first);
            v.push(-> second);
            let result = <- v.replace(one, -> incoming);
            match (-> result) {
                Ok(view) => { print(*view); },
                Err(view) => { print(0); }
            }
            let mut removed = <- v.remove(zero);
            print(*removed);
            print(*v[zero]);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '6\n8\n7\n9\n'), run.stderr)

    def test_mutable_reference_vector_dynamic_remove_reserves_remaining_cases(self):
        source = """
            fn take(v: &mut Vector<&mut Int>, i: Int) -> Int {
                let mut extracted = <- v.remove(i);
                extracted.set(11);
                return *extracted;
            }
            let mut p = pool<Int>(2);
            let mut x = p.new(7);
            let mut y = p.new(9);
            let mut a = &mut x;
            let mut b = &mut y;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            v.push(-> b);
            let mut i = 0;
            let mut view = <- v.remove(i);
            CHECK
            view.set(12);
            print(*view);
            print(*v[0]);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '12\n9\n'), run.stderr)
        injected = source.split('let mut view =', 1)[0] + 'print(take(&mut v, i)); print(*v[0]);'
        run = self.native(injected)
        self.assertEqual((run.returncode, run.stdout), (0, '11\n9\n'), run.stderr)
        for statement, diagnostic in (('print(*v[0]);', 'emprunt actif'),
                                      ('drop(-> v);', 'emprunt encore utilisé'),
                                      ('vp.reset();', 'reset interdit')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_mutable_reference_vector_pop_through_injected_parameter(self):
        source = """
            fn take(v: &mut Vector<&mut Int>) -> Int {
                let r = <- v.pop();
                CHECK
                match (-> r) {
                    Some(view) => { view.set(11); print(*view); },
                    None => { print(0); }
                }
                return v.len();
            }
            fn relay(v: &mut Vector<&mut Int>) -> Int { return take(v); }
            let mut p = pool<Int>(1);
            let mut x = p.new(7);
            let mut a = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            print(relay(&mut v));
            print(v.len());
            print(relay(&mut v));
            drop(-> v);
            print(*x);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '11\n0\n0\n0\n0\n11\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(v.len());'))

    def test_mutable_reference_vector_replace_through_injected_parameter(self):
        source = """
            fn replace(v: &mut Vector<&mut Int>, i: Int, data: &mut Int) -> Int {
                let result = <- v.replace(i, -> data);
                CHECK
                match (-> result) {
                    Ok(view) => { view.set(11); print(*view); },
                    Err(view) => { view.set(13); print(*view); }
                }
                return *v[0];
            }
            let mut p = pool<Int>(2);
            let mut x = p.new(7);
            let mut y = p.new(9);
            let mut a = &mut x;
            let mut vp = pool<Vector<&mut Int>>(1);
            let mut v = vp.new();
            v.push(-> a);
            print(replace(&mut v, INDEX, &mut y));
            drop(-> v);
            print(*x);
            print(*y);
        """
        for index, output in ((0, '11\n9\n11\n9\n'), (1, '13\n7\n7\n13\n')):
            with self.subTest(index=index):
                run = self.native(source.replace('INDEX', str(index)).replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, output), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('INDEX', '0').replace('CHECK', 'print(v.len());'))

    def test_shared_reference_vector_borrows_without_destroying_targets(self):
        source = """
            fn stored(d: &Int) -> &Int {
                let mut vp = pool<Vector<&Int>>(1);
                let mut v = vp.new();
                v.push(d);
                return v[0];
            }
            let mut p = pool<Int>(1);
            let mut d = p.new(7);
            address(d);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&d);
            CHECK
            let view = v[0];
            drop(-> v);
            address(view);
            print(*view);
            let r = stored(&d);
            print(*r);
            d.set(8);
            print(*d);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, first, second, changed = run.stdout.splitlines()
        self.assertEqual((returned, first, second, changed), (original, '7', '7', '8'))
        self.assertEqual(run.stderr.count('destroy d=8'), 1)
        for statement, diagnostic in (('p.reset();', 'reset interdit'),
                                      ('drop(-> d);', 'emprunt encore utilisé'),
                                      ('d.set(9);', 'emprunt actif')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(source.replace('CHECK', '{ let local = p.new(10); v.push(&local); }'))
        with self.assertRaisesRegex(Error, 'exige un emprunt partagé'):
            verify_program(source.replace('v.push(&d);', 'v.push(&mut d);').replace('CHECK', ''))
        contract = """
            fn read(d: &Int, memory: &mut Pool<Int>) {
                let mut vp = pool<Vector<&Int>>(1);
                let mut v = vp.new();
                v.push(d);
                memory.reset();
                let view = v[0];
                print(*view);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let d = p.new(7);
            read(&d, &mut q);
        """
        run = self.native(contract)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(contract.replace('read(&d, &mut q)', 'read(&d, &mut p)'))

    def test_shared_reference_vector_contract_relays_targets(self):
        source = """
            fn read(v: &Vector<&Int>, memory: &mut Pool<Int>, i: Int) -> &Int {
                memory.reset();
                return v[i];
            }
            fn relay(v: &Vector<&Int>, memory: &mut Pool<Int>, i: Int) -> &Int {
                return read(v, memory, i);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut scratch = pool<Int>(1);
            let first = p.new(7);
            let second = q.new(9);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&first);
            v.push(&second);
            address(second);
            let view = relay(&v, &mut scratch, 1);
            drop(-> v);
            CHECK
            address(view);
            print(*view);
            q.reset();
        """
        accepted = source.replace('CHECK', '')
        requirements = verify_program(accepted).function_constraints['relay'].requirements
        self.assertTrue(any(
            requirement.relation == 'distinct' and
            {(source.kind, source.index, source.name) for source in (requirement.left, requirement.right)}
            == {('allocation_field_parameter', 0, '.items'), ('source_parameter', 1, '')}
            for requirement in requirements
        ))
        run = self.native(accepted)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, value = run.stdout.splitlines()
        self.assertEqual((returned, value), (original, '9'))
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
                verify_program(accepted.replace('&mut scratch, 1', f'&mut {pool}, 1'))
        for statement, diagnostic in (('q.reset();', 'reset interdit'),
                                      ('drop(-> second);', 'emprunt encore utilisé')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        with self.assertRaisesRegex(Error, 'emprunt en lecture'):
            verify_program(accepted.replace('return v[i];', 'return v.remove(i);'))

    def test_shared_reference_vector_contract_allows_reset_after_last_use(self):
        source = """
            fn read(v: &Vector<&Int>, memory: &mut Pool<Int>) -> Int {
                let view = v[0];
                let value = *view;
                memory.reset();
                return value;
            }
            let mut p = pool<Int>(1);
            let d = p.new(7);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&d);
            print(read(&v, &mut p));
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy d=7'), 1)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source + 'print(*v[0]);')

    def test_shared_reference_vector_out_of_bounds_traps(self):
        source = """
            fn index() -> Int {
                print(42);
                return 0;
            }
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            ACCESS
            print(99);
        """
        for access, output in (('print(*v[index()]);', '42\n'),
                               ('let view = v.remove(0); print(*view);', ''),
                               ('let mut p = pool<Int>(1); let d = p.new(7); v.push(&d); print(*v[1]);', '')):
            with self.subTest(access=access):
                run = self.native(source.replace('ACCESS', access))
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(run.stdout, output)
                self.assertIn('indice de Vector hors limites', run.stderr)
                self.assertNotIn('runtime error', run.stderr)

        borrowed = self.native("""
            fn read(v: &Vector<&Int>) -> Int { return *v[0]; }
            let mut vp = pool<Vector<&Int>>(1);
            let v = vp.new();
            print(read(&v));
        """)
        self.assertNotEqual(borrowed.returncode, 0)
        self.assertEqual(borrowed.stdout, '')
        self.assertIn('indice de Vector hors limites', borrowed.stderr)
        self.assertNotIn('runtime error', borrowed.stderr)

    def test_shared_reference_vector_contract_preserves_literal_slot(self):
        source = """
            fn first(v: &Vector<&Int>) -> &Int { return v[0]; }
            fn relay(v: &Vector<&Int>) -> &Int { return first(v); }
            fn use_first(v: &Vector<&Int>, memory: &mut Pool<Int>) -> Int {
                let view = relay(v);
                memory.reset();
                return *view;
            }
            fn relay_reset(v: &Vector<&Int>, memory: &mut Pool<Int>) -> Int {
                return use_first(v, memory);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let x = p.new(7);
            let y = q.new(9);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&x);
            v.push(&y);
            CHECK
            address(x);
            let view = relay(&v);
            drop(-> v);
            q.reset();
            address(view);
            print(*view);
        """
        accepted = source.replace('CHECK', '')
        run = self.native(accepted)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, value = run.stdout.splitlines()
        self.assertEqual((returned, value), (original, '7'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(accepted.replace('q.reset();', 'p.reset();'))
        before_check = source.split('CHECK', 1)[0]
        disjoint = self.native(before_check + 'print(relay_reset(&v, &mut q));')
        self.assertEqual((disjoint.returncode, disjoint.stdout), (0, '7\n'), disjoint.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(before_check + 'print(relay_reset(&v, &mut p));')

    def test_shared_reference_vector_empty_contract_preserves_call_and_alternatives(self):
        source = """
            fn first(v: &Vector<&Int>) -> &Int {
                print(42);
                return v[0];
            }
            fn choose(v: &Vector<&Int>, fallback: &Int, flag: Int) -> &Int {
                if flag == 1 { return first(v); }
                return fallback;
            }
            let mut p = pool<Int>(1);
            let d = p.new(7);
            let mut vp = pool<Vector<&Int>>(1);
            let v = vp.new();
            let view = choose(&v, &d, FLAG);
            print(*view);
        """
        fallback = self.native(source.replace('FLAG', '0'))
        self.assertEqual((fallback.returncode, fallback.stdout), (0, '7\n'), fallback.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('FLAG', '0').replace('print(*view);', 'p.reset(); print(*view);'))
        empty = self.native(source.replace('FLAG', '1'))
        self.assertNotEqual(empty.returncode, 0)
        self.assertEqual(empty.stdout, '42\n')
        self.assertIn('indice de Vector hors limites', empty.stderr)
        self.assertNotIn('runtime error', empty.stderr)
        direct = self.native(source.replace('choose(&v, &d, FLAG)', 'first(&v)'))
        self.assertNotEqual(direct.returncode, 0)
        self.assertEqual(direct.stdout, '42\n')
        self.assertIn('indice de Vector hors limites', direct.stderr)
        self.assertNotIn('runtime error', direct.stderr)

    def test_shared_reference_vector_pop_retains_only_extracted_target(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let x = p.new(7);
            let y = q.new(9);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&x);
            v.push(&y);
            address(y);
            let result: Option<&Int> = v.pop();
            print(*v[0]);
            drop(-> v);
            p.reset();
            CHECK
            match result {
                Some(view) => { address(view); print(*view); },
                None => { print(0); }
            }
            q.reset();
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, remaining, extracted, value = run.stdout.splitlines()
        self.assertEqual((remaining, extracted, value), ('7', original, '9'))
        self.assertEqual(run.stderr.count('destroy y=9'), 1)
        for statement, diagnostic in (('q.reset();', 'reset interdit'),
                                      ('drop(-> y);', 'emprunt encore utilisé')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))
        empty = self.native("""
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            match v.pop() {
                Some(view) => { print(*view); },
                None => { print(0); }
            }
        """)
        self.assertEqual((empty.returncode, empty.stdout), (0, '0\n'), empty.stderr)

    def test_shared_reference_vector_pop_relays_reference(self):
        source = """
            fn extract(data: &Int, fallback: &Int) -> &Int {
                let mut vp = pool<Vector<&Int>>(1);
                let mut v = vp.new();
                v.push(data);
                let result = v.pop();
                match result {
                    Some(view) => { return view; },
                    None => { return fallback; }
                }
            }
            fn relay(data: &Int, fallback: &Int) -> &Int {
                return extract(data, fallback);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let data = p.new(7);
            let fallback = q.new(9);
            let view = relay(&data, &fallback);
            CHECK
            print(*view);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'p.reset();'))

    def test_shared_reference_vector_replace_preserves_both_outcomes(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let x = p.new(7);
            let y = q.new(9);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&x);
            let result: Result<&Int, &Int> = v.replace(INDEX, &y);
            print(*v[0]);
            drop(-> v);
            RESET
            match result {
                Ok(old) => { print(1); print(*old); },
                Err(incoming) => { print(0); print(*incoming); }
            }
        """
        for index, disjoint, protected, output in (
            (0, 'q', 'p', '9\n1\n7\n'), (1, 'p', 'q', '7\n0\n9\n')
        ):
            with self.subTest(index=index):
                program = source.replace('INDEX', str(index))
                run = self.native(program.replace('RESET', f'{disjoint}.reset();'))
                self.assertEqual((run.returncode, run.stdout), (0, output), run.stderr)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('RESET', f'{protected}.reset();'))

    def test_shared_reference_vector_try_push_restitutes_at_capacity(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let x = p.new(7);
            let y = q.new(9);
            #(directive, stack_region_max_size=1M) {
                let mut vp = pool<Vector<&Int>>(1);
                let mut v = vp.new();
                let mut i = 0;
                while i < COUNT {
                    v.push(&x);
                    i = i + 1;
                }
                let result: Result<(), &Int> = v.try_push(&y);
                print(v.len());
                print(*v[0]);
                drop(-> v);
                p.reset();
                CHECK
                match result {
                    Ok(()) => { print(1); },
                    Err(view) => { print(0); print(*view); }
                }
                q.reset();
            }
        """
        for count, expected in ((0, '1\n9\n1\n'), (131072, '131072\n7\n0\n9\n')):
            with self.subTest(count=count):
                program = source.replace('COUNT', str(count))
                run = self.native(program.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                self.assertEqual(run.stderr.count('destroy y=9'), 1)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('CHECK', 'q.reset();'))

    def test_shared_reference_vector_transfer_consumes_vector_and_preserves_target(self):
        source = """
            fn take(mut v: -> Vector<&Int>) -> &Int {
                let view = v.remove(0);
                drop(-> v);
                return view;
            }
            fn relay(v: -> Vector<&Int>) -> &Int {
                return take(-> v);
            }
            let mut p = pool<Int>(1);
            let x = p.new(7);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&x);
            address(x);
            let view = relay(-> v);
            CHECK
            let reuse = vp.new();
            print(reuse.len());
            address(view);
            print(*view);
            p.reset();
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, length, returned, value = run.stdout.splitlines()
        self.assertEqual((length, returned, value), ('0', original, '7'))
        self.assertEqual(run.stderr.count('destroy x=7'), 1)
        for statement, diagnostic in (('p.reset();', 'reset interdit'),
                                      ('print(v.len());', 'déplacée')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_shared_reference_vector_transfer_tracks_conditional_shift(self):
        source = """
            fn choose(mut v: -> Vector<&Int>, flag: Int) -> &Int {
                if flag == 1 { let removed = v.remove(0); print(*removed); }
                return v[0];
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let x = p.new(7);
            let y = q.new(9);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&x);
            v.push(&y);
            let view = choose(-> v, FLAG);
            CHECK
            print(*view);
        """
        for flag, expected in ((0, '7\n'), (1, '7\n9\n')):
            with self.subTest(flag=flag):
                program = source.replace('FLAG', str(flag))
                run = self.native(program.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('CHECK', 'q.reset();'))

    def test_shared_reference_vector_return_keeps_target_pools(self):
        source = """
            fn make(output: &mut Pool<Vector<&Int>>, data: &Int) -> <- Vector<&Int> {
                let mut v = output.new();
                v.push(data);
                return <- v;
            }
            fn relay(v: -> Vector<&Int>) -> <- Vector<&Int> { return <- v; }
            let mut p = pool<Int>(1);
            let data = p.new(7);
            let mut output = pool<Vector<&Int>>(2);
            address(data);
            let v = make(&mut output, &data);
            let received = relay(-> v);
            CHECK
            let view = received[0];
            drop(-> received);
            address(view);
            print(*view);
            p.reset();
            let empty = output.new();
            let forwarded = relay(-> empty);
            print(forwarded.len());
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, value, length = run.stdout.splitlines()
        self.assertEqual((returned, value, length), (original, '7', '0'))
        for pool in ('p', 'output'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('CHECK', f'{pool}.reset();'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn bad(output: &mut Pool<Vector<&Int>>) -> <- Vector<&Int> {
                    let mut local = pool<Int>(1);
                    let data = local.new(7);
                    let mut v = output.new();
                    v.push(&data);
                    return <- v;
                }
            """)

    def test_shared_reference_vector_mutable_parameter_publishes_targets(self):
        source = """
            fn add(v: &mut Vector<&Int>, data: &Int) { v.push(data); }
            fn relay(v: &mut Vector<&Int>, data: &Int) { add(v, data); }
            fn take(v: &mut Vector<&Int>) -> &Int { return v.remove(0); }
            let mut p = pool<Int>(1);
            let x = p.new(7);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            relay(&mut v, &x);
            CHECK
            let view = take(&mut v);
            print(v.len());
            print(*view);
            drop(-> v);
            p.reset();
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '0\n7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'p.reset();'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(source.replace('relay(&mut v, &x);',
                '{ let mut local = pool<Int>(1); let y = local.new(9); relay(&mut v, &y); }')
                .replace('CHECK', ''))

    def test_shared_reference_vector_return_preserves_case_order(self):
        source = """
            fn make(out: &mut Pool<Vector<&Int>>, a: &Int, b: &Int) -> <- Vector<&Int> {
                let mut v = out.new();
                v.push(a);
                v.push(b);
                return <- v;
            }
            fn relay(out: &mut Pool<Vector<&Int>>, a: &Int, b: &Int) -> <- Vector<&Int> {
                let v = make(out, a, b);
                return <- v;
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(7);
            let b = q.new(9);
            let mut out = pool<Vector<&Int>>(1);
            let mut v = relay(&mut out, &a, &b);
            let removed = v.remove(0);
            print(*removed);
            RESET
            print(*v[0]);
        """
        run = self.native(source.replace('RESET', 'p.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('RESET', 'q.reset();'))

    def test_shared_reference_vector_round_trip_preserves_case_order(self):
        source = """
            fn same(v: -> Vector<&Int>) -> <- Vector<&Int> { return <- v; }
            fn relay(v: -> Vector<&Int>) -> <- Vector<&Int> {
                let received = same(-> v);
                return <- received;
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(7);
            let b = q.new(9);
            let mut out = pool<Vector<&Int>>(1);
            let mut v = out.new();
            v.push(&a);
            v.push(&b);
            let mut r = relay(-> v);
            let gone = r.remove(0);
            print(*gone);
            RESET
            print(*r[0]);
        """
        run = self.native(source.replace('RESET', 'p.reset();'))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('RESET', 'q.reset();'))
        changed = source.replace('same(v: ->', 'same(mut v: ->').replace(
            '{ return <- v; }', '{ let removed = v.remove(0); print(*removed); return <- v; }'
        ).replace('let gone = r.remove(0);', 'let view = r[0]; drop(-> r);').replace('print(*gone);', '')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(changed.replace('RESET', 'q.reset();').replace('print(*r[0]);', 'print(*view);'))

    def test_shared_reference_vector_remove_preserves_order_and_address(self):
        source = """
            let mut p = pool<Int>(3);
            let first = p.new(4);
            let middle = p.new(7);
            let last = p.new(9);
            address(middle);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&first);
            v.push(&middle);
            v.push(&last);
            let removed = v.remove(INDEX);
            print(v.len());
            print(*v[0]);
            print(*v[1]);
            drop(-> v);
            CHECK
            address(removed);
            print(*removed);
        """
        run = self.native(source.replace('INDEX', '1').replace('CHECK', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        original, length, first, last, returned, removed = run.stdout.splitlines()
        self.assertEqual((length, first, last, returned, removed), ('2', '4', '9', original, '7'))
        self.assertEqual(run.stderr.count('destroy middle=7'), 1)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('INDEX', '1').replace('CHECK', 'p.reset();'))
        outside = self.native(source.replace('INDEX', '3').replace('CHECK', ''))
        self.assertEqual(outside.returncode, 1)
        self.assertIn('indice de Vector hors limites', outside.stderr)

    def test_shared_reference_vector_literal_remove_releases_only_removed_target(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a = p.new(4);
            let mut b = q.new(7);
            let mut vp = pool<Vector<&Int>>(1);
            let mut v = vp.new();
            v.push(&a);
            v.push(&b);
            let removed = v.remove(1);
            print(*removed);
            CHECK
            b.set(8);
            print(*v[0]);
            print(*b);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n4\n8\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'a.set(9);'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('let removed = v.remove(1);', 'let mut index = 1; let removed = v.remove(index);')
                                 .replace('CHECK', ''))
        reset = self.native(source.replace('CHECK', 'q.reset();')
                            .replace('b.set(8);', 'let reused = q.new(8);').replace('print(*b);', 'print(*reused);'))
        self.assertEqual((reset.returncode, reset.stdout), (0, '7\n4\n8\n'), reset.stderr)
        contract = """
            fn read(a: &Int, b: &Int, memory: &mut Pool<Int>) -> Int {
                let mut vp = pool<Vector<&Int>>(1);
                let mut v = vp.new();
                v.push(a); v.push(b);
                let removed = v.remove(1);
                let value = *removed;
                memory.reset();
                return *v[0] + value;
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(4);
            let b = q.new(7);
            print(read(&a, &b, &mut q));
        """
        run = self.native(contract)
        self.assertEqual((run.returncode, run.stdout), (0, '11\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(contract.replace('&mut q));', '&mut p));'))

    def test_vector_read_fd_publishes_only_received_bytes(self):
        source = """
            fn read_once(v: &mut Vector<u8>, fd: Int) -> Result<Int, ReadError> {
                return v.read_fd(fd);
            }
            fn report(result: Result<Int, ReadError>) {
                match result {
                    Ok(count) => { print(count); },
                    Err(ReadError::EndOfStream) => { print(-1); },
                    Err(ReadError::CapacityExceeded) => { print(-2); },
                    Err(ReadError::Io) => { print(-3); }
                }
            }
            let mut bytes = pool<Vector<u8>>(1);
            let mut v = bytes.new();
            report(read_once(&mut v, 0));
            report(read_once(&mut v, -1));
            report(read_once(&mut v, 0));
            print(v.len());
        """
        run = self.native(source, stdin='abc')
        self.assertEqual((run.returncode, run.stdout), (0, '3\n-3\n-1\n3\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('report(read_once(&mut v, -1));',
                'let view = &v[..]; report(read_once(&mut v, -1)); print(view.len());'))
        with self.assertRaisesRegex(Error, 'descripteur Int'):
            verify_program(source.replace('v.read_fd(fd)', 'v.read_fd(true)'))
        full = source[:source.index('            let mut bytes =')] + """
            let mut bytes = pool<Vector<u8>>(1);
            #(directive, stack_region_max_size=1M) {
                let mut v = bytes.new();
                loop {
                    match read_once(&mut v, 0) {
                        Ok(_) => { continue; },
                        Err(ReadError::CapacityExceeded) => { break; },
                        _ => { print(-9); break; }
                    }
                }
                report(read_once(&mut v, -1));
                print(v.len());
            }
        """
        run = self.native(full, stdin='a' * 1048576)
        self.assertEqual((run.returncode, run.stdout), (0, '-2\n1048576\n'), run.stderr)

    def test_vector_read_fd_reserves_receiver_during_descriptor_evaluation(self):
        source = """
            fn clear(p: &mut Pool<Vector<u8>>) -> Int { p.reset(); return -1; }
            fn read(mut v: -> Vector<u8>, p: &mut Pool<Vector<u8>>) -> Result<Int, ReadError> {
                return v.read_fd(clear(p));
            }
            let mut pool_a = pool<Vector<u8>>(1);
            let mut pool_b = pool<Vector<u8>>(1);
            let v = pool_a.new();
            let status = read(-> v, &mut pool_b);
            match status { Err(ReadError::Io) => { print(1); }, _ => { print(0); } }
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '1\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source.replace('&mut pool_b);', '&mut pool_a);'))
        with self.assertRaisesRegex(Error, 'déplacement.*emprunt encore utilisé'):
            verify_program("""
                fn close(v: -> Vector<u8>) -> Int { drop(-> v); return -1; }
                let mut p = pool<Vector<u8>>(1);
                let mut v = p.new();
                let status = v.read_fd(close(-> v));
                match status { _ => {} }
            """)

    def test_vector_operand_reset_checks_receiver_pool_in_contract(self):
        source = """
            fn clear(p: &mut Pool<Vector<Int>>) -> Int { p.reset(); return 0; }
            fn take(mut v: -> Vector<Int>, p: &mut Pool<Vector<Int>>) -> Int {
                OPERATION
            }
            let mut source = pool<Vector<Int>>(1);
            let mut disjoint = pool<Vector<Int>>(1);
            let mut v = source.new();
            v.push(7);
            print(take(-> v, &mut disjoint));
        """
        for operation in (
            'return v.remove(clear(p));',
            'return v[clear(p)];',
            'let saved = v.replace(0, clear(p)); '
            'match saved { Ok(old) => { return old; }, Err(incoming) => { return incoming; } }',
            'v.push(clear(p)); return 7;',
        ):
            with self.subTest(operation=operation):
                program = source.replace('OPERATION', operation)
                run = self.native(program)
                self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
                with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
                    verify_program(program.replace('&mut disjoint)', '&mut source)'))

    def test_string_operand_reset_checks_receiver_pool_in_contract(self):
        source = """
            fn clear(p: &mut Pool<String>) -> Int { p.reset(); return 0; }
            fn change(mut s: -> String, p: &mut Pool<String>) {
                OPERATION
            }
            let mut source = pool<String>(1);
            let mut disjoint = pool<String>(1);
            let mut s = source.new();
            s.push_str("abc");
            change(-> s, &mut disjoint);
        """
        for operation, expected in (
            ('let result = s.replace_byte(clear(p), 0x7a); '
             'match result { Ok(_) => { print(1); }, _ => { print(0); } }', '1\n'),
            ('print(&s[clear(p)..]);', 'abc\n'),
            ('let view = &s[..]; let result = view.char_at(clear(p)); '
             'match result { Ok(c) => { print(c); }, _ => {} }', 'a\n'),
        ):
            with self.subTest(operation=operation):
                program = source.replace('OPERATION', operation)
                run = self.native(program)
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
                    verify_program(program.replace('&mut disjoint)', '&mut source)'))

    def test_slice_write_contract_tracks_place_across_rhs_reset(self):
        source = """
            fn clear(p: &mut Pool<Vector<Int>>) -> Int { p.reset(); return 11; }
            fn write(view: &mut [Int], p: &mut Pool<Vector<Int>>) { view[0] = clear(p); }
            let mut p = pool<Vector<Int>>(1);
            let mut q = pool<Vector<Int>>(1);
            let mut v = p.new();
            v.push(7);
            let (mut left, mut right) = v.split_at_mut(1);
            write(left, &mut q);
            print(v[0]);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '11\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
            verify_program(source.replace('write(left, &mut q);\n            print(v[0]);', 'write(left, &mut p);'))
        copied = self.native("""
            fn read(view: &[Int], p: &mut Pool<Vector<Int>>) -> Int {
                let value = view[0];
                p.reset();
                return value;
            }
            let mut p = pool<Vector<Int>>(1);
            let mut v = p.new();
            v.push(7);
            let view = &v[..];
            print(read(view, &mut p));
        """)
        self.assertEqual((copied.returncode, copied.stdout), (0, '7\n'), copied.stderr)

    def test_reference_array_argument_stays_live_until_modular_call(self):
        source = """
            fn clear(p: &mut Pool<Int>) -> Int { p.reset(); return 1; }
            fn use(row: ROW_TYPE, marker: Int) { print(READ); print(marker); }
            fn relay(d: &Int, p: &mut Pool<Int>) {
                let row = [d];
                let nested = [&row];
                use(ARG, clear(p));
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let d = p.new(7);
            relay(&d, &mut q);
        """
        for typ, argument, read in (
            ('[&Int;1]', 'copy(row)', '*row[0]'),
            ('&[&Int;1]', '&row', '*row[0]'),
            ('[&[&Int;1];1]', 'copy(nested)', '*row[0][0]'),
        ):
            with self.subTest(typ=typ):
                program = source.replace('ROW_TYPE', typ).replace('ARG', argument).replace('READ', read)
                run = self.native(program)
                self.assertEqual((run.returncode, run.stdout), (0, '7\n1\n'), run.stderr)
                with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
                    verify_program(program.replace('relay(&d, &mut q)', 'relay(&d, &mut p)'))

    def test_arithmetic_precedence_and_branch_result(self):
        run = self.native("""
            fn calculate(n: Int) -> Int {
                return if n > 0 { (n + 2) * 3 - 4 % 3 } else { -n };
            }
            print(calculate(4));
            print(calculate(-9));
            print(20 / 2 / 2);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "17\n9\n5\n")

    def test_arithmetic_reads_left_operand_before_right_mutates_it(self):
        run = self.native("""
            fn change(n: &mut Int) -> Int { n.set(20); return 1; }
            let mut p = pool<Int>(1);
            let mut n = new(p) Int(10);
            print(*n + change(&mut n));
            print(n);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "11\n20\n")
        self.assertEqual(run.stderr.splitlines(), ["destroy n=20", "reclaim n"])

    def test_constant_errors(self):
        for expr, message in [
            ("2147483647 + 1", "débordement"),
            ("-2147483648 - 1", "débordement"),
            ("-2147483648 / -1", "débordement"),
            ("50000 * 50000", "débordement"),
            ("3 / (2 - 2)", "division par zéro"),
            ("3 % 0", "division par zéro"),
        ]:
            with self.subTest(expr=expr), self.assertRaisesRegex(Error, message):
                compile_source(f"print({expr});")

    def test_immutable_scalar_constants_are_checked_statically(self):
        for source, message in (
            ('let a = 2; let zero = a - 2; print(1 / zero);', 'division par zéro'),
            ('let max = 2147483647; let one = 1; print(max + one);', 'débordement'),
            ('fn divide(a: Int) -> Int { let zero = 0; return a % zero; }', 'division par zéro'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, message):
                verify_program(source)
        run = self.native("""
            let value = 2;
            { let value = 4; print(value * value); }
            let mut divisor = 0;
            divisor = value;
            print(20 / divisor);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '16\n10\n'), run.stderr)

    def test_dynamic_errors_diagnose_without_undefined_behavior(self):
        for op, a, b, message in [
            ("+", 2147483647, 1, "débordement"),
            ("-", -2147483648, 1, "débordement"),
            ("*", 50000, 50000, "débordement"),
            ("/", -2147483648, -1, "débordement"),
            ("/", 1, 0, "division par zéro"),
            ("%", 1, 0, "division par zéro"),
        ]:
            with self.subTest(op=op, a=a, b=b):
                run = self.native(
                    f"fn op(a: Int, b: Int) -> Int {{ return a {op} b; }} print(op({a}, {b}));"
                )
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertIn(message, run.stderr)
                self.assertNotIn("runtime error:", run.stderr)
                self.assertEqual(run.stdout, "")

    def test_dynamic_division_and_remainder_against_model(self):
        cases = [(a, b) for a in (-2147483648, -23, -1, 0, 1, 23, 2147483647)
                 for b in (-2147483648, -7, -1, 1, 7, 2147483647)
                 if (a, b) != (-2147483648, -1)]
        source = """
            fn quotient(a: Int, b: Int) -> Int { return a / b; }
            fn remainder(a: Int, b: Int) -> Int { return a % b; }
            print(remainder(-2147483648, -1));
        """
        expected = [0]
        for a, b in cases:
            q, r = divmod(abs(a), abs(b))
            expected.extend([q if (a < 0) == (b < 0) else -q, r if a >= 0 else -r])
            source += f"print(quotient({a}, {b})); print(remainder({a}, {b}));\n"
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual([int(line) for line in run.stdout.splitlines()], expected)

    def test_short_circuit_and_precedence(self):
        run = self.native("""
            fn mark(n: Int) -> Int { print(n); return n; }
            if mark(1) == 0 && mark(2) == 2 { print(20); }
            if mark(3) == 3 || mark(4) == 4 && mark(5) == 5 { print(30); }
            if (mark(6) == 6 || mark(7) == 7) && mark(8) == 8 { print(80); }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "1\n3\n30\n6\n8\n80\n")

    def test_short_circuit_bool_values_in_bindings_arguments_and_returns(self):
        source = """
            fn mark(n: Int, value: bool) -> bool { print(n); return value; }
            fn relay(value: bool) -> bool { return value && mark(6, true); }
            let value = mark(1, false) && mark(2, true) || mark(3, true);
            if relay(value || mark(4, true)) { print(7); }
            if relay(mark(8, false) && mark(9, true)) { print(10); }
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '1\n3\n6\n7\n8\n'), run.stderr)
        for invalid in ('let x = 1 && true;', 'let x = true || 1;'):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(Error, 'types|même type'):
                verify_program(invalid)
        with self.assertRaisesRegex(Error, 'plus utilisable|chemin|conditionnel'):
            verify_program("""
                fn consume(a: -> Int) -> bool { drop(-> a); return true; }
                fn choose(flag: bool) {
                    let mut p = pool<Int>(1);
                    let a = p.new(4);
                    let b = flag && consume(-> a);
                    if b {}
                    print(*a);
                }
            """)

    def test_comparison_values_compose_with_short_circuit_and_arithmetic(self):
        source = """
            fn mark(n: Int) -> Int { print(n); return n; }
            fn in_range(n: Int) -> bool { return n >= 1 && n < 3; }
            fn use(value: bool) { if value { print(6); } }
            let b = mark(1) < mark(2) || mark(3) > mark(4);
            if (1 + 1) * 2 == 4 && (b == true) { print(5); }
            use((1 < 2) == true && in_range(2));
            if true == b { print(7); }
            if ("é").byte_len() == 2 { print(8); }
            let values = [9];
            while (values)[0] > 0 { print((values)[0]); break; }
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '1\n2\n5\n6\n7\n8\n9\n'), run.stderr)
        for invalid in ('let b = true < false;', 'let b = 1 == true;'):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(Error, 'comparaison.*incompatible'):
                verify_program(invalid)

    def test_possible_short_circuit_move_reaches_join(self):
        with self.assertRaisesRegex(Error, "plus utilisable|chemin|conditionnel"):
            compile_source("""
                fn flag() -> Int { return 1; }
                fn consume(mut n: -> Int) -> Int { drop(-> n); return 1; }
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(9);
                if flag() == 1 && consume(-> n) == 1 { print(10); }
                print(n);
            """)

    def test_short_circuit_move_changes_pool_state_only_on_taken_path(self):
        for flag, expected in [(0, "0\n"), (1, "9\n1\n")]:
            with self.subTest(flag=flag):
                run = self.native("""
                    fn consume(mut n: -> Int) -> Int { print(n); drop(-> n); return 1; }
                    fn run(flag: Int) {
                        let mut p = pool<Int>(1);
                        let mut n = new(p) Int(9);
                        if flag == 1 && consume(-> n) == 1 { print(1); }
                        else { print(0); }
                    }
                """ + f"run({flag});")
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected)
                self.assertEqual(run.stderr.splitlines().count("destroy n=9"), 1)

    def test_short_circuit_temporary_is_cleaned_only_when_created(self):
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                run = self.native("""
                    fn read(n: &Int) -> Int { print(n); return 1; }
                    fn run(enabled: Int) {
                        let mut p = pool<Int>(2);
                        let before = p.new(7);
                        if enabled == 1 && (false || read(&p.new(9)) == 1) { print(10); }
                        print(before);
                    }
                """ + f"run({enabled});")
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, "9\n10\n7\n" if enabled else "7\n")
                destructions = [line for line in run.stderr.splitlines() if line.startswith("destroy ")]
                self.assertEqual(destructions, (["destroy n=9"] if enabled else []) + ["destroy before=7"])

    def test_short_circuit_temporary_reuses_slot_on_continue_and_false_exit(self):
        run = self.native("""
            fn read(n: &Int) -> Int { print(n); return *n; }
            let mut p = pool<Int>(1);
            let mut i = 0;
            while i < 4 && read(&p.new(i)) < 2 {
                i = i + 1;
                continue;
            }
            print(i);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "0\n1\n2\n2\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy n=0", "destroy n=1", "destroy n=2"])

    def test_match_wildcard_covers_multiple_variants(self):
        run = self.native("""
            enum Choice { A { value: Int }, B, C { ignored: Int } }
            let mut p = pool<Choice>(1);
            let a = new(p) Choice.A { value: 7 };
            let b = new(p) Choice.B;
            let c = new(p) Choice.C { ignored: 11 };
            match &a { Choice.A { value: value } => { print(value); }, _ => { let n = 2; print(n); } }
            match &b { Choice.A { value: value } => { print(value); }, _ => { let n = 2; print(n); } }
            match &c { Choice.A { value: value } => { print(value); }, _ => { let n = 2; print(n); } }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "7\n2\n2\n")

    def test_consuming_match_reuses_subject_slot_inside_arm(self):
        run = self.native("""
            enum E { Item { first: Int, second: Int }, Empty }
            let mut p = pool<E>(1);
            let e = new(p) E.Item { first: 4, second: 7 };
            match (-> e) {
                E.Item { second: b, first: a } => {
                    let next = new(p) E.Item { first: b, second: a };
                    match &next { E.Item { first: x, second: y } => { print(x); print(y); }, _ => {} }
                },
                _ => {}
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "7\n4\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy e=E.Item", "destroy next=E.Item"])

    def test_consuming_match_handles_returns_and_outer_scalar_writes(self):
        run = self.native("""
            enum E { Item { n: Int }, Empty }
            fn read(e: -> E) -> Int {
                let mut n = 3;
                match (-> e) {
                    E.Item { n: v } => { n = v; },
                    _ => { return 8; }
                }
                return n;
            }
            let mut p = pool<E>(1);
            let e = new(p) E.Item { n: 4 };
            print(read(-> e));
            let empty = new(p) E.Empty;
            print(read(-> empty));
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "4\n8\n")

    def test_consuming_match_rejects_live_borrows_and_use_after_move(self):
        prefix = "enum E { A } let mut p = pool<E>(1); let e = new(p) E.A; "
        cases = [
            ("let r = &e; match (-> e) { E.A => {} } print(r);", "emprunt encore utilisé"),
            ("match (-> e) { E.A => { print(e); } }", "plus utilisable"),
            ("match (-> e) { E.A => {} } print(e);", "plus utilisable"),
        ]
        for code, message in cases:
            with self.subTest(code=code), self.assertRaisesRegex(Error, message):
                compile_source(prefix + code)

    def test_consuming_match_reaches_break_and_continue_with_cleanup(self):
        run = self.native("""
            enum E { A }
            let mut p = pool<E>(1);
            let mut i = 0;
            while i < 3 {
                let e = new(p) E.A;
                match (-> e) {
                    E.A => {
                        if i == 1 { break; }
                        i = i + 1;
                        continue;
                    }
                }
            }
            let after = new(p) E.A;
            print(i);
            drop(-> after);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "1\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy e=E.A", "destroy e=E.A", "destroy after=E.A"])

    def test_consuming_match_moves_shared_and_mutable_fields(self):
        source = """
            enum E { Item { shared: &Int, unique: &mut Int }, Empty }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(2);
            let a = ints.new(7);
            let mut b = ints.new(9);
            let mut parent = &mut b;
            let e = new(p) E.Item { shared: &a, unique: parent };
            match (-> e) {
                E.Item { shared: read, unique: edit } => {
                    print(read);
                    edit.set(20);
                },
                _ => {}
            }
            parent.set(21);
            print(b);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "7\n21\n")
        for statement, diagnostic in [
            ("read.set(11);", "lecture"),
            ("parent.set(11);", "emprunt actif"),
        ]:
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                compile_source(source.replace("edit.set(20);", statement + " edit.set(20);"))

    def test_consuming_match_can_return_reference_from_local_holder(self):
        source = """
            enum E { Item { r: &mut Int } }
            fn project(p: &mut Pool<E>, n: &mut Int) -> &mut Int {
                let e = new(p) E.Item { r: n };
                match (-> e) { E.Item { r: moved } => { return moved; } }
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let mut n = ints.new(9);
            let mut result = project(&mut p, &mut n);
            result.set(20);
            print(n);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "20\n")
        self.assertEqual(run.stderr.splitlines(),
                         ["destroy e=E.Item", "reclaim e", "destroy n=20", "reclaim n"])
        with self.assertRaisesRegex(Error, "emprunt actif"):
            compile_source(source.replace("result.set(20);", "n.set(15); result.set(20);"))

    def test_consumed_parameter_field_return_survives_pool_reuse_and_forwarding(self):
        source = """
            enum E { Item { r: &mut Int } }
            fn project(e: -> E) -> &mut Int {
                match (-> e) { E.Item { r: moved } => { return moved; } }
            }
            fn relay(e: -> E) -> &mut Int { return project(-> e); }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(2);
            let mut n = ints.new(9);
            let mut other = ints.new(7);
            let e = new(p) E.Item { r: &mut n };
            let mut result = relay(-> e);
            let fresh = new(p) E.Item { r: &mut other };
            drop(-> fresh);
            result.set(20);
            print(n);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "20\n")
        self.assertEqual(run.stderr.splitlines()[:4],
                         ["destroy e=E.Item", "reclaim e", "destroy fresh=E.Item", "reclaim fresh"])
        with self.assertRaisesRegex(Error, "emprunt actif"):
            compile_source(source.replace("result.set(20);", "n.set(15); result.set(20);"))

    def test_consumed_parameter_shared_field_tracks_target_lifetime(self):
        declaration = """
            enum E { Item { r: &Int } }
            fn project(e: -> E) -> &Int {
                match (-> e) { E.Item { r: moved } => { return moved; } }
            }
        """
        source = """
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let n = ints.new(9);
            let e = new(p) E.Item { r: &n };
            let result = project(-> e);
            print(result);
        """
        run = self.native(declaration + source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "9\n")
        with self.assertRaisesRegex(Error, "non durable"):
            compile_source(declaration + """
                fn escape(p: &mut Pool<E>, ints: &mut Pool<Int>) -> &Int {
                    let n = ints.new(9);
                    let e = new(p) E.Item { r: &n };
                    return project(-> e);
                }
            """)

    def test_consumed_fields_survive_array_return_and_relay(self):
        source = """
            enum E { Item { left: &mut Int, right: &mut Int } }
            fn take(e: -> E) -> [&mut Int; 2] {
                match (-> e) {
                    E.Item { left: x, right: y } => { return <- [y, x]; }
                }
            }
            fn relay(e: -> E) -> [&mut Int; 2] { return <- take(-> e); }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(2);
            let mut a = ints.new(9);
            let mut b = ints.new(7);
            let e = new(p) E.Item { left: &mut a, right: &mut b };
            let refs = relay(-> e);
            p.reset();
            *refs[0] = 21;
            *refs[1] = 22;
            print(a);
            print(b);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "22\n21\n")
        with self.assertRaisesRegex(Error, "reset interdit"):
            compile_source(source.replace("p.reset();", "ints.reset();"))

    def test_consumed_field_returned_from_array_case(self):
        source = """
            enum E { Item { r: &mut Int } }
            fn take(e: -> E) -> [&mut Int; 1] {
                match (-> e) { E.Item { r: moved } => { return <- [moved]; } }
            }
            fn first(e: -> E) -> &mut Int {
                let refs = take(-> e);
                return &mut *refs[0];
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let mut n = ints.new(9);
            let e = new(p) E.Item { r: &mut n };
            let mut result = first(-> e);
            *result = 22;
            print(n);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "22\n")
        with self.assertRaisesRegex(Error, "emprunt actif"):
            compile_source(source.replace("*result = 22;", "n.set(15); *result = 22;"))

    def test_consumed_array_field_ignores_absent_variants(self):
        run = self.native("""
            enum E { A { r: &Int }, B { r: &Int } }
            fn take(e: -> E) -> [&Int; 1] {
                match (-> e) {
                    E.A { r: x } => { return <- [x]; },
                    E.B { r: y } => { return <- [y]; }
                }
            }
            fn first(e: -> E) -> &Int {
                let refs = take(-> e);
                return refs[0];
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(2);
            let n = ints.new(9);
            let m = ints.new(7);
            let a = new(p) E.A { r: &n };
            let refs = take(-> a);
            print(*refs[0]);
            let b = new(p) E.B { r: &m };
            let result = first(-> b);
            print(*result);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "9\n7\n")

    def test_consuming_match_expression_joins_scalars_and_excludes_return(self):
        run = self.native("""
            enum E { A { n: Int }, B, C }
            fn f(e: -> E) -> Int {
                let x = match (-> e) {
                    E.A { n: a } => { a + 3 },
                    E.B => { return 9; },
                    _ => { 5 }
                };
                return x * 2;
            }
            let mut p = pool<E>(1);
            let a = new(p) E.A { n: 4 };
            print(f(-> a));
            let b = new(p) E.B;
            print(f(-> b));
            let c = new(p) E.C;
            print(f(-> c));
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "14\n9\n10\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy a=E.A", "destroy b=E.B", "destroy c=E.C"])

    def test_consuming_match_expression_rejects_missing_or_incompatible_results(self):
        for body, diagnostic in (("", "résultat"), ("<- [1]", "même type")):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                compile_source("""
                    enum E { A, B }
                    fn f(e: -> E) -> Int {
                        return match (-> e) { E.A => { 1 }, E.B => { """ + body + """ } };
                    }
                """)

    def test_consuming_match_returns_allocation_and_reference_array(self):
        source = """
            enum E { A, B }
            fn make(e: -> E, p: &mut Pool<Int>) -> <- Int {
                let n = match (-> e) {
                    E.A => { let x = p.new(11); <- x },
                    E.B => { let y = p.new(12); <- y }
                };
                return <- n;
            }
            fn refs(e: -> E, a: &Int, b: &Int) -> [&Int; 1] {
                let values = match (-> e) { E.A => { <- [a] }, E.B => { <- [b] } };
                return <- values;
            }
            let mut ep = pool<E>(1);
            let mut p = pool<Int>(2);
            let a = new(ep) E.A;
            let mut n = make(-> a, &mut p);
            let b = new(ep) E.B;
            let mut m = make(-> b, &mut p);
            let c = new(ep) E.B;
            let v = refs(-> c, &n, &m);
            print(*v[0]);
            let d = new(ep) E.A;
            let arr = match (-> d) { E.A => { <- [1, 2] }, E.B => { <- [3, 4] } };
            print(arr[1]);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "12\n2\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")][-2:],
                         ["destroy y=12", "destroy x=11"])
        for target in ("n", "m"):
            with self.subTest(target=target), self.assertRaisesRegex(Error, "emprunt actif"):
                compile_source(source.replace("print(*v[0]);", f"{target}.set(90); print(*v[0]);"))

    def test_consuming_match_expression_returns_mutable_field(self):
        source = """
            enum E { A { r: &mut Int }, B { r: &mut Int } }
            fn choose(e: -> E) -> &mut Int {
                let mut field = match (-> e) {
                    E.A { r: a } => { a },
                    E.B { r: b } => { b }
                };
                return field;
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let mut n = ints.new(9);
            let mut parent = &mut n;
            let e = new(p) E.B { r: parent };
            let mut result = choose(-> e);
            p.reset();
            result.set(20);
            parent.set(21);
            print(n);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "21\n")
        self.assertEqual(run.stderr.splitlines(),
                         ["destroy e=E.B", "reclaim e", "reset", "destroy n=21", "reclaim n"])
        with self.assertRaisesRegex(Error, "emprunt actif"):
            compile_source(source.replace("result.set(20);", "parent.set(15); result.set(20);"))

    def test_consuming_match_expression_rejects_borrow_from_arm_local(self):
        with self.assertRaisesRegex(Error, "non durable"):
            compile_source("""
                enum E { A }
                let mut p = pool<E>(1);
                let mut ints = pool<Int>(1);
                let e = new(p) E.A;
                let result = match (-> e) {
                    E.A => { let n = ints.new(9); &n }
                };
                print(result);
            """)

    def test_consuming_match_expression_returns_array_borrow(self):
        source = """
            enum E { A, B }
            fn choose(e: -> E, a: &mut [Int; 2], b: &mut [Int; 2]) -> &mut [Int; 2] {
                return match (-> e) { E.A => { &mut *a }, E.B => { b } };
            }
            fn run(flag: Int) {
                let mut p = pool<E>(1);
                let mut a = [1, 2];
                let mut b = [3, 4];
                let e = if flag == 0 { let a = new(p) E.A; <- a } else { let b = new(p) E.B; <- b };
                let r = choose(-> e, &mut a, &mut b);
                p.reset();
                r[0] = 20;
                print(a[0]);
                print(b[0]);
            }
            run(0);
            run(1);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "20\n3\n1\n20\n")
        for target in ("a", "b"):
            with self.subTest(target=target), self.assertRaisesRegex(Error, "emprunt actif"):
                compile_source(source.replace("r[0] = 20;", f"{target}[0] = 90; r[0] = 20;"))

    def test_consuming_match_expression_rejects_borrow_of_arm_array(self):
        with self.assertRaisesRegex(Error, "non durable|ne survit pas"):
            compile_source("""
                enum E { A }
                let mut p = pool<E>(1);
                let e = new(p) E.A;
                let r = match (-> e) { E.A => { let local = [9]; &local } };
                print(r[0]);
            """)

    def test_consuming_match_joins_cell_and_array_element_borrows(self):
        source = """
            enum E { A, B }
            fn choose(e: -> E, n: &mut Int, a: &mut [Int; 1]) -> &mut Int {
                return match (-> e) { E.A => { n }, E.B => { &mut a[0] } };
            }
            fn run(flag: Int) {
                let mut p = pool<E>(1);
                let mut ints = pool<Int>(1);
                let mut n = ints.new(9);
                let mut a = [7];
                let e = if flag == 0 { let x = new(p) E.A; <- x } else { let x = new(p) E.B; <- x };
                let mut r = choose(-> e, &mut n, &mut a);
                r.set(20);
                print(n);
                print(a[0]);
            }
            run(0);
            run(1);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "20\n7\n9\n20\n")
        for write in ("n.set(15);", "a[0] = 15;"):
            with self.subTest(write=write), self.assertRaisesRegex(Error, "emprunt actif"):
                compile_source(source.replace("r.set(20);", write + " r.set(20);"))

    def test_consuming_match_preserves_enum_borrow_representation(self):
        run = self.native("""
            enum E { A }
            enum W { Value { n: Int } }
            let mut p = pool<E>(1);
            let mut q = pool<W>(1);
            let e = new(p) E.A;
            let w = new(q) W.Value { n: 12 };
            let r = match (-> e) { E.A => { &w } };
            print(r);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "W.Value(12)\n")

    def test_shared_match_expression_reads_subject_and_excludes_early_return(self):
        run = self.native("""
            enum E { A { n: Int }, B }
            fn read(e: &E) -> Int {
                return 2 * match &e { E.A { n: n } => { n + 1 }, _ => { return 7; } };
            }
            let mut p = pool<E>(1);
            let a = new(p) E.A { n: 4 };
            print(read(&a));
            print(a);
            let b = new(p) E.B;
            print(read(&b));
            print(b);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "10\nE.A(4)\n7\nE.B()\n")

    def test_shared_match_expression_reads_projection_and_rejects_mutation(self):
        source = """
            enum E { A { r: &mut Int } }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let mut n = ints.new(9);
            let e = new(p) E.A { r: &mut n };
            let v = match &e { E.A { r: r } => { *r + 1 } };
            print(v);
            print(e);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "10\nE.A(9)\n")
        with self.assertRaisesRegex(Error, "lecture uniquement"):
            compile_source(source.replace("*r + 1", "r.set(20); *r + 1"))

    def test_shared_match_result_reserves_holder_through_relay(self):
        source = """
            enum E { A { r: &mut Int } }
            fn project(e: &E) -> &Int {
                return match &e { E.A { r: field } => { &*field } };
            }
            fn relay(e: &E) -> &Int { return project(e); }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let mut n = ints.new(9);
            let e = new(p) E.A { r: &mut n };
            let view = relay(&e);
            print(e);
            print(view);
            drop(-> e);
            n.set(10);
            print(n);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "E.A(9)\n9\n10\n")
        for statement in ("drop(-> e);", "n.set(10);"):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, "emprunt"):
                compile_source(source.replace(statement, "").replace("print(view);", statement + " print(view);"))

    def test_shared_match_reference_cannot_escape_local_holder(self):
        with self.assertRaisesRegex(Error, "non durable"):
            compile_source("""
                enum E { A { r: &mut Int } }
                fn bad(p: &mut Pool<E>, n: &mut Int) -> &Int {
                    let e = new(p) E.A { r: n };
                    return match &e { E.A { r: field } => { field } };
                }
            """)

    def test_shared_match_external_borrow_outlives_subject(self):
        source = """
            enum E { A, B }
            fn choose(e: &E, a: &Int, b: &mut Int) -> &Int {
                return match &e { E.A => { a }, E.B => { &*b } };
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(2);
            let a = ints.new(9);
            let mut b = ints.new(7);
            let e = new(p) E.B;
            let result = choose(&e, &a, &mut b);
            drop(-> e);
            print(result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "7\n")
        with self.assertRaisesRegex(Error, "emprunt actif"):
            compile_source(source.replace("print(result);", "b.set(20); print(result);"))

    def test_shared_match_returns_external_array_borrow(self):
        run = self.native("""
            enum E { A, B }
            fn choose(e: &E, a: &[Int; 1], b: &[Int; 1]) -> &[Int; 1] {
                return match &e { E.A => { a }, E.B => { &*b } };
            }
            let mut p = pool<E>(1);
            let a = [9];
            let b = [7];
            let first = new(p) E.A;
            let x = choose(&first, &a, &b);
            drop(-> first);
            print(x[0]);
            let second = new(p) E.B;
            let y = choose(&second, &a, &b);
            drop(-> second);
            print(y[0]);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "9\n7\n")

    def test_constraints_filter_absent_match_field_after_constructor_call(self):
        declarations = """
            enum E { A { r: &Int }, B }
            fn choose(e: &E, fallback: &Int) -> &Int {
                return match &e { E.A { r: field } => { field }, E.B => { fallback } };
            }
            fn empty(p: &mut Pool<E>) -> <- A<E> {
                let e = new(p) E.B;
                return <- e;
            }
        """
        body = """
            fn run(p: &mut Pool<E>, ints: &mut Pool<Int>) {
                let n = ints.new(7);
                let e = empty(p);
                let holder = &e;
                let view = choose(holder, &n);
                p.reset();
                print(view);
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            run(&mut p, &mut ints);
        """
        run = self.native(declarations + body)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "7\n")
        # Resetting the carrier's pool leaves the copied shared target alive.
        copied = declarations + body.replace("empty(p)", "new(p) E.A { r: &n }")
        run = self.native(copied)
        self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
        with self.assertRaisesRegex(Error, "reset interdit"):
            compile_source(copied.replace('p.reset();', 'ints.reset();'))

    def test_constraints_keep_possible_match_field_at_conditional_join(self):
        with self.assertRaisesRegex(Error, "reset interdit"):
            compile_source("""
                enum E { A { r: &Int }, B }
                fn choose(e: &E, fallback: &Int) -> &Int {
                    return match &e { E.A { r: field } => { field }, E.B => { fallback } };
                }
                fn run(p: &mut Pool<E>, ints: &mut Pool<Int>, flag: Int) {
                    let n = ints.new(7);
                    let e = if flag == 0 {
                        let x = new(p) E.A { r: &n }; <- x
                    } else {
                        let x = new(p) E.B; <- x
                    };
                    let view = choose(&e, &n);
                    p.reset();
                    print(view);
                }
            """)

    def test_mutable_match_expression_writes_projection_and_returns_int(self):
        run = self.native("""
            enum E { A { r: &mut Int }, B { n: Int }, C, D }
            fn read(e: &mut E) -> Int {
                return match &mut e {
                    E.A { r: field } => { field.set(20); *field + 1 },
                    E.B { n: value } => { value },
                    E.C => { 6 },
                    _ => { return 7; }
                };
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let mut n = ints.new(9);
            let mut a = new(p) E.A { r: &mut n };
            print(read(&mut a));
            print(a);
            let mut b = new(p) E.B { n: 5 };
            print(read(&mut b));
            let mut c = new(p) E.C;
            print(read(&mut c));
            let mut d = new(p) E.D;
            print(read(&mut d));
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "21\nE.A(20)\n5\n6\n7\n")

    def test_mutable_match_expression_rejects_mixed_scalar_and_projection(self):
        with self.assertRaisesRegex(Error, "même type et même mode"):
            compile_source("""
                enum E { A { r: &mut Int }, B }
                let mut p = pool<E>(1);
                let mut ints = pool<Int>(1);
                let mut n = ints.new(9);
                let mut a = new(p) E.A { r: &mut n };
                let mut result = match &mut a { E.A { r: field } => { field }, _ => { 6 } };
                print(result);
            """)

    def test_mutable_match_joins_projection_and_external_borrow(self):
        source = """
            enum E { A { r: &mut Int }, B }
            fn choose(e: &mut E, fallback: &mut Int) -> &mut Int {
                return match &mut e { E.A { r: field } => { field }, E.B => { &mut *fallback } };
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(2);
            let mut n = ints.new(9);
            let mut m = ints.new(7);
            let mut e = new(p) E.B;
            let mut view = choose(&mut e, &mut m);
            drop(-> e);
            view.set(21);
            print(m);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "21\n")
        projection = source.replace("new(p) E.B", "new(p) E.A { r: &mut n }")
        with self.assertRaisesRegex(Error, "emprunt"):
            compile_source(projection)
        run = self.native(projection.replace("drop(-> e);", "").replace("print(m);", "print(e);"))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "E.A(21)\n")

    def test_mutable_match_returns_external_array_borrow(self):
        source = """
            enum E { A, B }
            fn choose(e: &mut E, a: &mut [Int; 1], b: &mut [Int; 1]) -> &mut [Int; 1] {
                return match &mut e { E.A => { a }, _ => { &mut *b } };
            }
            let mut p = pool<E>(1);
            let mut a = [9];
            let mut b = [7];
            let mut e = new(p) E.B;
            let r = choose(&mut e, &mut a, &mut b);
            drop(-> e);
            r[0] = 21;
            print(a[0]);
            print(b[0]);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "9\n21\n")
        with self.assertRaisesRegex(Error, "emprunt actif"):
            compile_source(source.replace("r[0] = 21;", "b[0] = 20; r[0] = 21;"))

    def test_mutable_match_can_return_shared_field(self):
        source = """
            enum E { A { r: &Int } }
            fn choose(e: &mut E) -> &Int {
                return match &mut e { E.A { r: field } => { field } };
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            let n = ints.new(9);
            let mut e = new(p) E.A { r: &n };
            let view = choose(&mut e);
            print(view);
            print(e);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "9\nE.A(9)\n")
        with self.assertRaisesRegex(Error, "emprunt actif"):
            compile_source(source.replace("print(view);", "print(e); print(view);"))

    def test_mutable_match_local_known_variant_releases_subject_pool(self):
        source = """
            enum E { A { r: &mut Int }, B }
            fn run(p: &mut Pool<E>, ints: &mut Pool<Int>) {
                let mut n = ints.new(9);
                let mut e = new(p) E.B;
                let mut view = match &mut e { E.A { r: field } => { field }, _ => { &mut n } };
                p.reset();
                view.set(21);
                print(n);
            }
            let mut p = pool<E>(1);
            let mut ints = pool<Int>(1);
            run(&mut p, &mut ints);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "21\n")
        with self.assertRaisesRegex(Error, "reset interdit"):
            compile_source(source.replace("new(p) E.B", "new(p) E.A { r: &mut n }"))

    def test_shared_match_transfers_allocation_and_cleans_other_local(self):
        run = self.native("""
            enum E { A { n: Int }, B }
            fn make(e: &E, p: &mut Pool<Int>) -> <- Int {
                let result = match &e {
                    E.A { n: n } => { let scratch = p.new(90); let x = p.new(n); <- x },
                    _ => { let x = p.new(12); <- x }
                };
                return <- result;
            }
            let mut ep = pool<E>(1);
            let mut p = pool<Int>(2);
            let e = new(ep) E.A { n: 4 };
            let n = make(&e, &mut p);
            let next = p.new(50);
            print(e);
            print(n);
            print(next);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "E.A(4)\n4\n50\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy scratch=90", "destroy next=50", "destroy x=4", "destroy e=E.A"])

    def test_mutable_match_transfers_array_with_projected_reference(self):
        source = """
            enum E { A { r: &mut Int } }
            fn make(e: &mut E) -> [&Int; 1] {
                let result = match &mut e { E.A { r: field } => { field.set(20); <- [&*field] } };
                return <- result;
            }
            let mut ep = pool<E>(1);
            let mut p = pool<Int>(1);
            let mut n = p.new(9);
            let mut e = new(ep) E.A { r: &mut n };
            let result = make(&mut e);
            print(*result[0]);
            print(e);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "20\nE.A(20)\n")
        with self.assertRaisesRegex(Error, "emprunt encore utilisé"):
            compile_source(source.replace("print(e);", "").replace("print(*result[0]);",
                                                                    "drop(-> e); print(*result[0]);"))

    def test_borrowed_match_initializer_calls_function_with_subject_reserved(self):
        source = """
            enum E { A { n: Int } }
            fn read(n: Int) -> Int { print(n); return n + 1; }
            fn clear(p: &mut Pool<E>) -> Int { p.reset(); return 0; }
            let mut ep = pool<E>(1);
            let mut p = pool<Int>(1);
            let e = new(ep) E.A { n: 4 };
            let result = match &e {
                E.A { n: n } => { let x = p.new(read(n) + 2); <- x }
            };
            print(e);
            print(result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "4\nE.A(4)\n7\n")
        with self.assertRaisesRegex(Error, "reset interdit"):
            compile_source(source.replace("read(n) + 2", "clear(&mut ep)"))

    def test_borrowed_match_expression_joins_replacements_and_checks_calls(self):
        source = """
            enum E { A { n: Int }, B { n: Int } }
            fn observe(n: Int) { print(n); }
            fn clear(p: &mut Pool<E>) { p.reset(); }
            fn run(flag: Int) {
                let mut ep = pool<E>(1);
                let mut p = pool<Int>(2);
                let e = if flag == 0 { let a = new(ep) E.A { n: 4 }; <- a }
                        else { let b = new(ep) E.B { n: 8 }; <- b };
                let mut recu = p.new(1);
                let result = match &e {
                    E.A { n: n } => { observe(n); let fresh = p.new(n); recu = <- fresh; n }
                    E.B { n: n } => { observe(n); n }
                };
                print(result);
                print(recu);
                print(e);
            }
            run(0);
            run(1);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "4\n4\n4\nE.A(4)\n8\n8\n1\nE.B(8)\n")
        with self.assertRaisesRegex(Error, "reset interdit"):
            compile_source(source.replace("observe(n);", "clear(&mut ep);").replace("print(e);", ""))
        with self.assertRaisesRegex(Error, "transfert <- explicite"):
            compile_source(source.replace("let fresh = p.new(n); recu = <- fresh;", "recu = p.new(n);"))

    def test_mutable_match_expression_preserves_result_loan_after_call(self):
        source = """
            enum E { A { r: &mut Int } }
            fn write(r: &mut Int, n: Int) { print(n); r.set(7); }
            let mut ep = pool<E>(1);
            let mut p = pool<Int>(1);
            let mut n = p.new(1);
            let mut e = new(ep) E.A { r: &mut n };
            let mut result = match &mut e {
                E.A { r: field } => { write(field, 7); field }
            };
            print(*result);
            result.set(12);
            print(e);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "7\n7\nE.A(12)\n")
        with self.assertRaisesRegex(Error, "incompatible avec un emprunt actif"):
            compile_source(source.replace("result.set(12);\n            print(e);", "print(e); result.set(12);"))

    def test_borrowed_match_expression_allows_loop_exits_in_arm(self):
        run = self.native("""
            enum E { A { n: Int } }
            let mut p = pool<E>(1);
            let mut i = 0;
            while i < 3 {
                let e = new(p) E.A { n: i };
                i = i + 1;
                let v = match &e {
                    E.A { n: n } => {
                        if n == 0 { continue; }
                        if n == 2 { break; }
                        n + 10
                    }
                };
                print(v);
            }
            print(i);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "11\n3\n")
        self.assertEqual(run.stderr.splitlines().count("destroy e=E.A"), 3)

    def test_statement_match_replacements_reach_break_and_continue(self):
        source = """
            enum E { A { n: Int } }
            fn run(ep: &mut Pool<E>, p: &mut Pool<Int>) -> <- Int {
                let mut recu = p.new(1);
                let mut i = 0;
                loop {
                    let e = new(ep) E.A { n: i };
                    i = i + 1;
                    match &e {
                        E.A { n: n } => {
                            let fresh = p.new(*recu + 2);
                            recu = <- fresh;
                            if n == 0 { continue; }
                            break;
                        }
                    }
                }
                return <- recu;
            }
            let mut ep = pool<E>(1);
            let mut p = pool<Int>(2);
            let result = run(&mut ep, &mut p);
            print(result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "5\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy recu=1", "destroy e=E.A", "destroy fresh=3",
                          "destroy e=E.A", "destroy fresh=5"])
        with self.assertRaisesRegex(Error, "la source 'local' ne survit pas"):
            compile_source(source.replace("let fresh = p.new", "let mut local = pool<Int>(1); let fresh = local.new"))

    def test_statement_match_replacement_updates_return_contract(self):
        source = """
            enum E { A }
            fn pick(e: &E, a: &Int, b: &Int) -> &Int {
                let mut refs = [a];
                match &e { E.A => { refs = [b]; } }
                return refs[0];
            }
            let mut ep = pool<E>(1);
            let mut p = pool<Int>(2);
            let e = new(ep) E.A;
            let a = p.new(1);
            let b = p.new(7);
            let result = pick(&e, &a, &b);
            drop(-> a);
            print(*result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "7\n")
        with self.assertRaisesRegex(Error, "emprunt encore utilisé"):
            compile_source(source.replace("drop(-> a)", "drop(-> b)"))

    def test_match_loop_exit_restores_shadowed_parameter(self):
        for subject, parameter, argument in (("&e", "&E", "&e"), ("(-> e)", "-> E", "-> e")):
            with self.subTest(subject=subject):
                run = self.native(f"""
                    enum E {{ A {{ n: Int }} }}
                    fn read(e: {parameter}, n: &Int) -> &Int {{
                        loop {{
                            let x = match {subject} {{ E.A {{ n: n }} => {{ break; }} }};
                            print(x);
                        }}
                        return n;
                    }}
                    let mut p = pool<E>(1);
                    let mut ints = pool<Int>(1);
                    let e = new(p) E.A {{ n: 4 }};
                    let n = ints.new(9);
                    let result = read({argument}, &n);
                    print(result);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, "9\n")

    def test_wildcard_cannot_precede_named_arms_or_duplicate_coverage(self):
        prefix = "enum E { A } let mut p = pool<E>(1); let a = new(p) E.A; "
        for body, message in [("_ => {}, E.A => {}", "terminer le match"),
                              ("E.A => {}, _ => {}", "inaccessible")]:
            with self.subTest(body=body), self.assertRaisesRegex(Error, message):
                compile_source(prefix + "match &a {" + body + "}")

    def test_compact_transfer_marks_only_the_final_local_allocation(self):
        source = """
            fn make(p: &mut Pool<Int>) -> <- Int {
                let <- data = p.new(4);
                address(data);
                data
            }
            let mut p = pool<Int>(2);
            let a = {
                let <- data = make(&mut p);
                data
            };
            address(a);
            let b = if 1 == 1 {
                let <- data = p.new(2);
                data
            } else {
                let <- data = p.new(3);
                data
            };
            print(*a);
            print(*b);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, a, b = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((a, b), ('4', '2'))
        for invalid, diagnostic in (
            ('let <- x = 1;', 'let <- exige une allocation'),
            ('let <- x = pool<Int>(1);', 'let <- exige une allocation'),
            (source + 'print(*data);', 'variable inconnue'),
            ('let a = { let mut q = pool<Int>(1); let <- x = q.new(1); x }; print(*a);', 'ne survit pas'),
            ('let mut p = pool<Int>(1); let <- x = p.new(1); let a = { x }; print(*a);', 'affectation implicite interdite.*<-'),
            ('let mut p = pool<Int>(1); let a = { let <- x = p.new(1); x };', 'sans usage explicite'),
        ):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)
        unreceived = """
            let mut p = pool<Int>(1);
            { let <- x = p.new(1); x }
            let reused = p.new(2);
            print(*reused);
        """
        checked = verify_program(unreceived)
        self.assertTrue(any('transfert sans receveur' in warning for warning in checked.warnings))
        run = self.native(unreceived)
        self.assertEqual((run.returncode, run.stdout), (0, '2\n'), run.stderr)

    def test_typed_pool_new_defaults_transfers_and_reuses_slot(self):
        run = self.native("""
            fn make(p: &mut Pool<Int>) -> <- Int {
                let n = p.new();
                return <- n;
            }
            let mut p = pool<Int>(1);
            let n = make(&mut p);
            print(n);
            drop(-> n);
            let n2 = p.new(41 + 1);
            print(n2);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "0\n42\n")
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy n=0", "destroy n2=42"])

    def test_pool_method_checks_source_type_and_arity(self):
        for factory, arguments, message in [
            ("allocator()", "", "exige un pool<Int>"),
            ("pool<E>(1)", "10", "exige un pool<Int>"),
            ("pool<Int>(1)", "1, 2", "zéro ou un argument"),
        ]:
            with self.subTest(factory=factory, arguments=arguments):
                with self.assertRaisesRegex(Error, message):
                    compile_source(f"enum E {{ A }} let mut p = {factory}; let n = p.new({arguments});")

    def test_allocation_annotation_checks_type_without_changing_storage(self):
        source = """
            fn make(p: &mut Pool<Int>) -> <- Int {
                let n: Int = p.new(10);
                return <- n;
            }
            enum E { A }
            let mut p = pool<Int>(1);
            let n: Int = make(&mut p);
            address(n);
            drop(-> n);
            let other: Int = p.new();
            address(other);
            print(other);
        """
        self.assertEqual(compile_source(source), compile_source(source.replace(": Int =", " =")))
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, default = run.stdout.splitlines()
        self.assertEqual(first, second)
        self.assertEqual(default, "0")
        with self.assertRaisesRegex(Error, "annotation de let : attendu E, reçu Int"):
            verify_program(source.replace("let n: Int = p.new", "let n: E = p.new"))
        with self.assertRaisesRegex(Error, "annotation de let : une allocation est requise"):
            verify_program("let n: Int = 10;")

    def test_struct_pool_defaults_order_and_reuse(self):
        source = """
            struct Point { x: Int, y: Int, z: Int }
            fn show(n: Int) -> Int { print(n); return n; }
            fn make(points: &mut Pool<Point>) -> <- A<Point> {
                let p: A<Point> = points.new(y: show(9), x: show(4));
                return <- p;
            }
            let mut points = pool<Point>(1);
            let p: A<Point> = make(&mut points);
            address(p);
            print(p);
            drop(-> p);
            let q = points.new();
            address(q);
            print(q);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        y, x, first, point, second, default = run.stdout.splitlines()
        self.assertEqual((y, x, point, default), ("9", "4", "Point(4, 9, 0)", "Point(0, 0, 0)"))
        self.assertEqual(first, second)
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy p=Point", "destroy q=Point"])
        for bad, message in (("y: 9, y: 4", "initialisé plusieurs fois"),
                             ("unknown: 9", "champ inconnu")):
            with self.subTest(bad=bad), self.assertRaisesRegex(Error, message):
                verify_program(source.replace("y: show(9), x: show(4)", bad))

    def test_struct_pool_reference_survives_return_and_checks_initializer_effects(self):
        source = """
            struct View { target: &Int, marker: Int }
            fn clear(p: &mut Pool<Int>) -> Int { p.reset(); return 0; }
            fn make(views: &mut Pool<View>, target: &Int) -> <- A<View> {
                let v: A<View> = views.new(target: target);
                return <- v;
            }
            let mut views = pool<View>(1);
            let mut p = pool<Int>(1);
            let target = p.new(7);
            let v = make(&mut views, &target);
            print(v);
            drop(-> v);
            drop(-> target);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "View(7, 0)\n")
        with self.assertRaisesRegex(Error, "aucune valeur par défaut"):
            verify_program(source.replace("views.new(target: target)", "views.new()"))
        with self.assertRaisesRegex(Error, "emprunt encore utilisé"):
            verify_program(source.replace("print(v);", "drop(-> target); print(v);"))
        with self.assertRaisesRegex(Error, "reset interdit"):
            verify_program(source.replace("make(&mut views, &target)",
                                          "views.new(target: &target, marker: clear(&mut p))"))

    def test_structure_copy_reuses_injected_origin_and_returns_fresh_slot(self):
        source = """
            struct Point { x: Int }
            fn duplicate(points: &mut Pool<Point>) -> <- A<Point> {
                let mut original = points.new(x: 9);
                address(original);
                let duplicate = copy(original);
                original.x = 11;
                print(original);
                return <- duplicate;
            }
            let mut points = pool<Point>(2);
            let duplicate = duplicate(&mut points);
            address(duplicate);
            print(duplicate);
            let reused = points.new();
            address(reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, changed, duplicate, copied, reused = run.stdout.splitlines()
        self.assertEqual((changed, copied, reused), ('Point(11)', 'Point(9)', original))
        self.assertNotEqual(original, duplicate)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('print(duplicate);', 'points.reset(); print(duplicate);'))
        full = self.native(source.replace('pool<Point>(2)', 'pool<Point>(1)'))
        self.assertNotEqual(full.returncode, 0)
        self.assertIn('pool', full.stderr)
        with self.assertRaisesRegex(Error, 'arguments aliasés'):
            verify_program("""
                struct Point { x: Int }
                fn consume(points: &mut Pool<Point>, value: -> Point) { print(value); }
                fn duplicate(points: &mut Pool<Point>) {
                    let original = points.new(x: 9);
                    consume(points, -> copy(original));
                }
                let mut points = pool<Point>(2);
                duplicate(&mut points);
            """)

    def test_structure_copy_resolves_pool_from_borrowed_parameter(self):
        source = """
            struct View { target: &Int, code: Int }
            fn duplicate(x: &View) -> <- A<View> { let y = copy(x); return <- y; }
            fn relay(x: &View) -> <- A<View> { let y = duplicate(x); return <- y; }
            fn consume(pool: &mut Pool<View>, value: -> View) { print(value); }
            let mut views = pool<View>(2);
            let mut targets = pool<Int>(1);
            let target = targets.new(7);
            let x = views.new(target: &target, code: 42);
            address(x);
            let y = relay(&x);
            address(y);
            print(x);
            drop(-> x);
            print(y);
            drop(-> y);
            let next = views.new(target: &target);
            address(next);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, duplicate, printed_x, printed_y, reused = run.stdout.splitlines()
        self.assertNotEqual(original, duplicate)
        self.assertEqual((printed_x, printed_y, reused), ('View(7, 42)', 'View(7, 42)', original))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('print(y);', 'drop(-> target); print(y);'))
        with self.assertRaisesRegex(Error, 'pool d’origine emprunté'):
            verify_program(source.replace('let y = relay(&x);', 'consume(&mut views, -> relay(&x));')
                                  .split('address(y);')[0])

    def test_nested_structure_defaults_are_inline_in_one_slot(self):
        source = """
            struct Path { segment: Segment, code: Int }
            struct Segment { start: Point, end: Point }
            struct Point { x: Int, y: Int }
            fn make(paths: &mut Pool<Path>) -> <- A<Path> {
                let path: A<Path> = paths.new(code: 9);
                return <- path;
            }
            let mut paths = pool<Path>(1);
            let path = make(&mut paths);
            address(path);
            print(path);
            drop(-> path);
            let next = paths.new();
            address(next);
            print(next);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, path, second, default = run.stdout.splitlines()
        self.assertEqual((path, default), ("Path(0, 0, 0, 0, 9)", "Path(0, 0, 0, 0, 0)"))
        self.assertEqual(first, second)
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith("destroy ")],
                         ["destroy path=Path", "destroy next=Path"])
        with self.assertRaisesRegex(Error, r"champ 'segment\.start\.x' : aucune valeur par défaut"):
            verify_program(source.replace("x: Int", "x: &Int"))

    def test_nested_structure_named_paths_initialize_inline_in_written_order(self):
        source = """
            struct Path { segment: Segment, code: Int }
            struct Segment { start: Point, end: Int }
            struct Point { x: Int, target: &Int }
            fn mark(n: Int) -> Int { print(n); return n; }
            fn make(paths: &mut Pool<Path>, target: &Int) -> <- A<Path> {
                let path = paths.new(code: mark(1), segment.start.target: target,
                                     segment.start.x: mark(2));
                return <- path;
            }
            let mut paths = pool<Path>(1);
            let mut ints = pool<Int>(1);
            let target = ints.new(7);
            let path = make(&mut paths, &target);
            address(path);
            print(path);
            drop(-> path);
            let next = paths.new(segment.start.target: &target);
            address(next);
            print(next);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, address, path, reused, default = run.stdout.splitlines()
        self.assertEqual((first, second, path, reused, default),
                         ('1', '2', 'Path(2, 7, 0, 1)', address, 'Path(0, 7, 0, 0)'))
        for old, new, diagnostic in (
            ('segment.start.x: mark(2)', 'segment.start.x: mark(2), segment.start.x: 3',
             'champ initialisé plusieurs fois'),
            ('segment.start.x: mark(2)', 'segment.start.missing: mark(2)', 'champ inconnu'),
            ('segment.start.x: mark(2)', 'segment.start: mark(2)', 'construction inline Point'),
            ('segment.start.target: target,', '', 'aucune valeur par défaut'),
            ('print(path);', 'drop(-> target); print(path);', 'emprunt encore utilisé'),
            ('make(&mut paths, &target)',
             'paths.new(segment.start.target: &target, code: clear(&mut ints))', 'reset interdit'),
        ):
            with self.subTest(new=new), self.assertRaisesRegex(Error, diagnostic):
                verify_program('fn clear(pool: &mut Pool<Int>) -> Int { pool.reset(); return 3; }'
                               + source.replace(old, new))

    def test_explicit_read_through_nested_shared_structure_field(self):
        source = """
            struct View { target: &Int }
            struct BoxedView { inner: View }
            fn read(v: &BoxedView) -> Int { return *v.inner.target; }
            let mut ints = pool<Int>(2);
            let old = ints.new(5);
            let current = ints.new(7);
            let mut views = pool<BoxedView>(1);
            let mut v = views.new(inner.target: &old);
            print(*v.inner.target);
            v.inner.target = &current;
            drop(-> old);
            CHECK
            print(read(&v));
            let value = *v.inner.target;
            drop(-> v);
            drop(-> current);
            print(value);
        """
        run = self.native(source.replace('CHECK', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '5\n7\n7\n'), run.stderr)
        for statement, diagnostic in (
            ('drop(-> current);', 'emprunt encore utilisé'),
            ('ints.reset();', 'reset interdit'),
            ('let bad = &mut *v.inner.target; print(*bad);', 'champ &mut Int'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_shared_field_reborrow_detaches_from_nested_carrier(self):
        source = """
            struct View { target: &Int }
            struct Outer { view: View }
            fn get(v: &Outer) -> &Int { return &*v.view.target; }
            fn relay(v: &Outer) -> &Int { return get(v); }
            fn read(n: &Int) -> Int { return *n; }
            let mut ints = pool<Int>(2);
            let mut a = ints.new(5);
            let b = ints.new(7);
            let mut carriers = pool<Outer>(1);
            let mut v = carriers.new(view.target: &a);
            print(read(&*v.view.target));
            let saved = relay(&v);
            v.view.target = &b;
            let next = &*v.view.target;
            drop(-> v);
            let reused = carriers.new(view.target: &b);
            drop(-> reused);
            CHECK
            print(*saved);
            print(*next);
            a = 9;
            print(a);
        """
        valid = source.replace('CHECK', '')
        checked = verify_program(valid)
        targets = checked.function_results['relay'].reference_targets
        self.assertEqual({(t.kind, t.parameter, t.field) for t in targets},
                         {('detached_field_parameter', 0, '.view.target')})
        run = self.native(valid)
        self.assertEqual((run.returncode, run.stdout), (0, '5\n5\n7\n9\n'), run.stderr)
        for statement, diagnostic in (
            ('a = 9;', 'emprunt actif'),
            ('drop(-> b);', 'emprunt encore utilisé'),
            ('ints.reset();', 'reset interdit'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', statement))

    def test_shared_field_reborrow_after_conditional_update_keeps_both_targets(self):
        source = """
            struct View { target: &Int }
            fn choose(v: &mut View, candidate: &Int, change: Int) -> &Int {
                if change > 0 { v.target = &*candidate; }
                return &*v.target;
            }
            fn relay(v: &mut View, candidate: &Int, change: Int) -> &Int {
                return choose(v, candidate, change);
            }
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let a = first.new(5);
            let b = second.new(7);
            let mut views = pool<View>(1);
            let mut v = views.new(target: &a);
            let result = relay(&mut v, &b, FLAG);
            drop(-> v);
            CHECK
            print(*result);
            first.reset();
            second.reset();
        """
        for flag, output in ((0, '5\n'), (1, '7\n')):
            with self.subTest(flag=flag):
                program = source.replace('FLAG', str(flag))
                valid = program.replace('CHECK', '')
                contract = verify_program(valid).function_results['relay']
                self.assertEqual({(t.kind, t.parameter, t.field) for t in contract.reference_targets},
                                 {('detached_field_parameter', 0, '.target'), ('parameter', 1, '')})
                run = self.native(valid)
                self.assertEqual((run.returncode, run.stdout), (0, output), run.stderr)
                for pool in ('first', 'second'):
                    with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                        verify_program(program.replace('CHECK', f'{pool}.reset();'))

    def test_shared_structure_field_update_through_mutable_parameter(self):
        prefix = """
            struct View { target: &Int }
            fn update(v: &mut View, target: &Int) { v.target = &*target; }
            fn relay(v: &mut View, target: &Int) { update(v, target); }
            fn conditional(v: &mut View, target: &Int, change: Int) {
                if change > 0 { relay(v, target); }
            }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let old = ints.new(5);
            let new_target = ints.new(7);
            let mut v = views.new(target: &old);
        """
        run = self.native(prefix + """
            relay(&mut v, &new_target);
            drop(-> old);
            print(v);
            drop(-> v);
            drop(-> new_target);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, 'View(7)\n'), run.stderr)
        for change, target in ((0, 5), (1, 7)):
            call = f'conditional(&mut v, &new_target, {change});'
            run = self.native(prefix + call + 'print(v);')
            self.assertEqual((run.returncode, run.stdout), (0, f'View({target})\n'), run.stderr)
            for name in ('old', 'new_target'):
                with self.subTest(change=change, name=name), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(prefix + call + f'drop(-> {name}); print(v);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(prefix + 'print(new_target); { let short = ints.new(9); relay(&mut v, &short); } print(v);')
        with self.assertRaisesRegex(Error, 'cible non durable'):
            verify_program(prefix + """
                print(new_target); print(v);
                fn invalid(v: &mut View) {
                    let mut local = pool<Int>(1);
                    let short = local.new(9);
                    v.target = &short;
                }
            """)

    def test_mutable_structure_field_update_transfers_reservation_via_contract(self):
        prefix = """
            struct Writer { target: &mut Int }
            fn update(w: &mut Writer, target: &mut Int) { w.target = &mut *target; }
            fn relay(w: &mut Writer, target: &mut Int) { update(w, target); }
            fn maybe(w: &mut Writer, target: &mut Int, change: Int) {
                if change > 0 { relay(w, target); }
            }
            let mut writers = pool<Writer>(1);
            let mut ints = pool<Int>(2);
            let mut old = ints.new(5);
            let mut incoming = ints.new(7);
            let mut w = writers.new(target: &mut old);
            let loan = &mut incoming;
        """
        direct = 'relay(&mut w, loan);'
        run = self.native(prefix + direct + """
            old = 9;
            let target = &mut *w.target;
            *target = 11;
            print(w);
            drop(-> w);
            *loan = 13;
            print(old);
            print(incoming);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, 'Writer(11)\n9\n13\n'), run.stderr)
        for use in ('*loan = 9;', 'incoming = 9;', 'drop(-> incoming);'):
            with self.subTest(use=use), self.assertRaisesRegex(Error, 'emprunt'):
                verify_program(prefix + direct + use + 'print(w);')
        for flag, expected in ((0, '11\n7\n'), (1, '5\n11\n')):
            call = f'maybe(&mut w, loan, {flag});'
            run = self.native(prefix + call + """
                let target = &mut *w.target;
                *target = 11;
                print(w);
                drop(-> w);
                print(old);
                print(incoming);
            """)
            self.assertEqual((run.returncode, run.stdout), (0, 'Writer(11)\n' + expected), run.stderr)
            with self.subTest(flag=flag), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(prefix + call + 'old = 9; print(w);')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program("""
                struct Writer { left: &mut Int, right: &mut Int }
                fn invalid(w: &mut Writer, target: &mut Int) {
                    w.left = &mut *target;
                    w.right = &mut *target;
                }
            """)

    def test_returned_reborrow_follows_reassigned_mutable_structure_field(self):
        source = """
            struct Writer { target: &mut Int, tag: Int }
            fn update(w: &mut Writer, target: &mut Int) -> &mut Int {
                w.target = &mut *target;
                return &mut *w.target;
            }
            fn relay(w: &mut Writer, target: &mut Int) -> &mut Int { return update(w, target); }
            let mut writers = pool<Writer>(1);
            let mut ints = pool<Int>(2);
            let mut old = ints.new(5);
            let mut incoming = ints.new(7);
            let mut w = writers.new(target: &mut old);
            let out = relay(&mut w, &mut incoming);
        """
        run = self.native(source + 'old = 8; w.tag = 3; *out = 9; print(w); print(old);')
        self.assertEqual((run.returncode, run.stdout), (0, 'Writer(9, 3)\n8\n'), run.stderr)
        for before in ('print(w);', 'incoming = 8;', 'drop(-> w);'):
            with self.subTest(before=before), self.assertRaisesRegex(Error, 'emprunt'):
                verify_program(source + before + '*out = 9;')
        array_source = source.replace('-> &mut Int {', '-> [&mut Int; 1] {').replace(
            'return &mut *w.target;', 'return <- [&mut *w.target];').replace(
            'return update(w, target);', 'let out = update(w, target); return <- out;')
        run = self.native(array_source + 'old = 8; *out[0] = 9; print(w); print(old);')
        self.assertEqual((run.returncode, run.stdout), (0, 'Writer(9, 0)\n8\n'), run.stderr)

    def test_structure_field_exchange_returns_previous_target_via_contract(self):
        prefix = """
            struct View { target: &Int }
            fn exchange(v: &mut View, incoming: &Int) -> &Int {
                let previous = v.target;
                v.target = &*incoming;
                return previous;
            }
            fn relay(v: &mut View, incoming: &Int) -> &Int {
                return exchange(v, incoming);
            }
            let mut views = pool<View>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let old = p.new(5);
            let incoming = q.new(7);
            let mut v = views.new(target: &old);
            let previous = relay(&mut v, &incoming);
        """
        run = self.native(prefix + """
            print(*previous);
            drop(-> old);
            print(v);
            drop(-> v);
            drop(-> incoming);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '5\nView(7)\n'), run.stderr)
        for body in (
            'drop(-> old); print(*previous);',
            'print(*previous); drop(-> incoming); print(v);',
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(prefix + body)

    def test_structure_field_update_relay_preserves_possible_holders(self):
        prefix = """
            struct View { target: &Int }
            fn select(a: &mut View, b: &mut View, flag: Int) -> &mut View {
                if flag > 0 { return a; }
                return b;
            }
            fn update(v: &mut View, target: &Int) { v.target = &*target; }
            fn relay(a: &mut View, b: &mut View, target: &Int, flag: Int) {
                let selected = select(a, b, flag);
                update(selected, target);
            }
            let mut views = pool<View>(2);
            let mut ints = pool<Int>(3);
            let a = ints.new(1);
            let b = ints.new(2);
            let n = ints.new(3);
            let mut left = views.new(target: &a);
            let mut right = views.new(target: &b);
        """
        for flag, expected in ((0, 'View(1)\nView(3)\n'), (1, 'View(3)\nView(2)\n')):
            call = f'relay(&mut left, &mut right, &n, {flag});'
            output = 'print(left); print(right);'
            run = self.native(prefix + call + output)
            self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
            for name in ('a', 'b', 'n'):
                with self.subTest(flag=flag, name=name), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(prefix + call + f'drop(-> {name});' + output)
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(prefix + """
                print(n);
                { let mut other = pool<Int>(1); let short = other.new(4);
                  relay(&mut left, &mut right, &short, 1); }
                print(left);
            """)
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(prefix + """
                print(n);
                let selected = select(&mut left, &mut right, 0);
                drop(-> b);
                print(selected);
            """)
        direct = prefix.replace('update(selected, target);', 'selected.target = &*target;')
        for flag, expected in ((0, 'View(1)\nView(3)\n'), (1, 'View(3)\nView(2)\n')):
            call = f'relay(&mut left, &mut right, &n, {flag});'
            run = self.native(direct + call + 'print(left); print(right);')
            self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(direct + call + 'drop(-> n); print(left); print(right);')

    def test_structure_field_update_tracks_local_holders_in_same_pool(self):
        prefix = """
            struct View { target: &Int }
            fn select(a: &mut View, b: &mut View, flag: Int) -> &mut View {
                if flag > 0 { return a; }
                return b;
            }
            fn build(views: &mut Pool<View>, a: &Int, b: &Int, n: &Int, flag: Int) -> <- A<View> {
                let mut left = views.new(target: a);
                let mut right = views.new(target: b);
                let selected = select(&mut left, &mut right, flag);
                selected.target = &*n;
                return <- left;
            }
            let mut views = pool<View>(2);
            let mut ints = pool<Int>(3);
            let a = ints.new(1);
            let b = ints.new(2);
            let n = ints.new(3);
        """
        for flag, expected in ((0, 'View(1)\n'), (1, 'View(3)\n')):
            call = f'let v = build(&mut views, &a, &b, &n, {flag});'
            run = self.native(prefix + call + 'drop(-> b); print(v);')
            self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
            for name in ('a', 'n'):
                with self.subTest(flag=flag, name=name), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(prefix + call + f'drop(-> {name}); print(v);')

    def test_structure_field_update_follows_shadowed_local_holder(self):
        source = """
            struct View { target: &Int }
            fn select(v: &mut View) -> &mut View { return v; }
            fn build(views: &mut Pool<View>, a: &Int, n: &Int, flag: Int) -> <- A<View> {
                let mut item = views.new(target: a);
                let selected = select(&mut item);
                {
                    let item = 17;
                    if flag > 0 { selected.target = &*n; }
                    print(item);
                }
                return <- item;
            }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let a = ints.new(1);
            let n = ints.new(3);
        """
        for flag, value in ((0, 1), (1, 3)):
            call = f'let view = build(&mut views, &a, &n, {flag});'
            run = self.native(source + call + 'print(view);')
            self.assertEqual((run.returncode, run.stdout), (0, f'17\nView({value})\n'), run.stderr)
            for name in ('a', 'n'):
                with self.subTest(flag=flag, name=name), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(source + call + f'drop(-> {name}); print(view);')

    def test_direct_recursive_structure_layout_is_rejected(self):
        for source in ("struct Node { next: Node }",
                       "struct A { b: B } struct B { c: C } struct C { a: A }"):
            with self.subTest(source=source), self.assertRaisesRegex(Error, "cycle de champs contenus directement"):
                verify_program(source)

    def test_struct_int_fields_use_same_slot_and_respect_whole_borrows(self):
        source = """
            struct Point { x: Int }
            struct Segment { start: Point, end: Point }
            fn write(s: &mut Segment) -> Int {
                s.end.x = s.start.x + 4;
                return s.end.x;
            }
            fn clear(p: &mut Pool<Segment>) -> Int { p.reset(); return 0; }
            let mut p = pool<Segment>(1);
            let mut s = p.new();
            address(s);
            s.start.x = 3;
            let current = &s;
            s.start.x = current.start.x;
            print(write(&mut s));
            address(s);
            print(s.start.x);
            print(s.end.x);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, updated, second, start, end = run.stdout.splitlines()
        self.assertEqual(first, second)
        self.assertEqual((updated, start, end), ("7", "3", "7"))
        self.assertEqual(run.stderr.splitlines().count("destroy s=Segment"), 1)
        cases = (
            (source.replace("let mut s =", "let s ="), "immuable"),
            (source.replace("s.start.x = 3;", "let view = &s; s.start.x = 3; print(view.start.x);"),
             "emprunt actif"),
            (source.replace("s.start.x = 3;", "s.start.x = clear(&mut p);"), "libérée|reset interdit"),
            (source.replace("s.start.x = 3;", "s.start.y = 3;"), "champ inconnu"),
        )
        for invalid, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_struct_int_field_loans_distinguish_siblings_and_keep_carrier_alive(self):
        source = """
            struct Point { x: Int }
            struct Segment { start: Point, end: Point, tag: Int }
            fn update(a: &mut Int, b: &mut Int) { *a = 8; *b = 9; }
            fn edit(s: &mut Segment) {
                let a = &mut s.start.x;
                let b = &mut s.end.x;
                s.tag = 7;
                update(a, b);
                print(s);
            }
            let mut p = pool<Segment>(1);
            let mut s = p.new();
            edit(&mut s);
            update(&mut s.start.x, &mut s.end.x);
            let target = &s.start.x;
            let alias = &s.start.x;
            s.end.x = 11;
            print(*target);
            print(*alias);
            drop(-> s);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "Segment(8, 9, 7)\n8\n8\n")
        self.assertEqual(run.stderr.splitlines().count("destroy s=Segment"), 1)
        cases = (
            ("let b = &mut s.end.x;", "let b = &mut s.start.x;", "emprunt actif"),
            ("s.tag = 7;", "print(s);", "emprunt actif"),
            ("s.end.x = 11;", "s.start.x = 11;", "emprunt actif"),
            ("s.end.x = 11;", "drop(-> s);", "emprunt encore utilisé"),
            ("s.end.x = 11;", "p.reset();", "reset interdit"),
            ("s.end.x = 11;", "edit(&mut s);", "emprunt actif"),
        )
        for before, after, diagnostic in cases:
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_returned_struct_field_contract_preserves_exact_paths(self):
        source = """
            struct Point { x: Int }
            struct Segment { start: Point, end: Point, tag: Int }
            fn choose(s: &mut Segment, side: Int) -> &mut Int {
                if side == 0 { return &mut s.start.x; }
                return &mut s.end.x;
            }
            fn relay(s: &mut Segment, side: Int) -> &mut Int { return choose(s, side); }
            fn start(s: &Segment) -> &Int { return &s.start.x; }
            let mut p = pool<Segment>(1);
            let mut s = p.new();
            let left = relay(&mut s, 0);
            s.tag = 4;
            *left = 8;
            let right = relay(&mut s, 1);
            *right = 9;
            let same = start(&s);
            let another = &s.start.x;
            s.end.x = 11;
            print(*same);
            print(*another);
            print(s);
        """
        checked = verify_program(source)
        targets = checked.function_results['relay'].reference_targets
        self.assertEqual({(item.kind, item.parameter, item.field) for item in targets},
                         {('inline_field_parameter', 0, 'start.x'), ('inline_field_parameter', 0, 'end.x')})
        self.assertIn('choose', checked.body_call_contracts['relay'])
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "8\n8\nSegment(8, 11, 4)\n")
        for field in ('start.x', 'end.x'):
            with self.subTest(field=field), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('s.tag = 4;', f's.{field} = 4;'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('s.end.x = 11;', 'drop(-> s);'))
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(source.replace('fn start(s: &Segment) -> &Int { return &s.start.x; }',
                                          'fn start(s: -> Segment) -> &Int { return &s.start.x; }'))

    def test_returned_reference_array_preserves_inline_field_path(self):
        source = """
            struct Point { x: Int, y: Int }
            fn one(p: &Point) -> [&Int; 1] { return <- [&p.x]; }
            fn relay(p: &Point) -> [&Int; 1] { let a = one(p); return <- a; }
            let mut points = pool<Point>(1);
            let mut p = points.new(x: 9);
            let refs = relay(&p);
            p.y = 11;
            print(*refs[0]);
            print(p);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "9\nPoint(9, 11)\n")
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('p.y = 11;', 'p.x = 11;'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('p.y = 11;', 'drop(-> p);'))

    def test_array_update_contracts_relay_inline_field_paths(self):
        write = """
            struct Point { x: Int, y: Int }
            fn write(v: &mut [&Int; 1], p: &Point) { v[0] = &p.x; }
        """
        inputs = """
            let mut points = pool<Point>(1);
            let mut ints = pool<Int>(1);
            let old = ints.new(3);
            let mut p = points.new(x: 9);
            let mut v = [&old];
        """
        tail = 'drop(-> old); p.y = 11; print(*v[0]); print(p);'
        direct = ('fn relay(v: &mut [&Int; 1], p: &Point) { write(v, p); }',
                  'relay(&mut v, &p);')
        nested = ("""
            fn row(rows: -> [&mut [&Int; 1]; 1], p: &Point) { write(&mut *rows[0], p); }
            fn relay(rows: -> [&mut [&Int; 1]; 1], p: &Point) { row(-> rows, p); }
        """, 'let rows = [&mut v]; relay(-> rows, &p);')
        for declarations, call in (direct, nested):
            with self.subTest(call=call):
                source = write + declarations + inputs + call + tail
                run = self.native(source)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, '9\nPoint(9, 11)\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('p.y = 11;', 'p.x = 11;'))
                with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(source.replace('p.y = 11;', 'drop(-> p);'))
        with self.assertRaisesRegex(Error, 'cible locale non durable'):
            verify_program(write.replace('p: &Point', 'p: -> Point'))

    def test_shared_struct_field_return_detaches_from_carrier(self):
        source = """
            struct View { target: &Int }
            fn read(v: &View) -> &Int { return v.target; }
            fn relay(v: &View) -> &Int { return read(v); }
            fn wrap(v: &View) -> [&Int; 1] { return <- [relay(v)]; }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let n = ints.new(9);
            let m = ints.new(4);
            let v = views.new(target: &n);
            let a = relay(&v);
            let refs = wrap(&v);
            drop(-> v);
            let v2 = views.new(target: &m);
            print(*a);
            print(*refs[0]);
            print(v2);
            drop(-> n);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '9\n9\nView(4)\n')
        self.assertEqual(run.stderr.splitlines().count('destroy v=View'), 1)
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('drop(-> v);', 'drop(-> n);'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('drop(-> v);', 'ints.reset();'))
        with self.assertRaisesRegex(Error, 'référence partagée est copiable'):
            verify_program('struct V { target: &mut Int } let mut p = pool<Int>(1); '
                           'let mut n = p.new(); let mut q = pool<V>(1); '
                           'let v = q.new(target: &mut n); let copy = v.target;')

    def test_struct_shared_field_replacement_keeps_old_copies(self):
        source = """
            struct View { target: &Int }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let a = ints.new(1);
            let b = ints.new(2);
            let mut v = views.new(target: &a);
            let old = v.target;
            address(v);
            v.target = &b;
            address(v);
            print(*old);
            drop(-> a);
            print(v);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, old, view = run.stdout.splitlines()
        self.assertEqual(first, second)
        self.assertEqual((old, view), ('1', 'View(2)'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('print(*old);\n            drop(-> a);', 'drop(-> a); print(*old);'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('drop(-> a);', 'drop(-> b);'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(source.replace('v.target = &b;', 'print(b); { let local = ints.new(); v.target = &local; }'))

    def test_struct_shared_field_replacement_joins_returned_provenances(self):
        source = """
            struct View { target: &Int }
            fn identity(x: &Int) -> &Int { return x; }
            fn make(views: &mut Pool<View>, a: &Int, b: &Int, c: &Int, side: Int) -> <- A<View> {
                let mut v = views.new(target: a);
                if side == 0 { v.target = identity(b); }
                else { v.target = identity(c); }
                return <- v;
            }
            let mut views = pool<View>(2);
            let mut ints = pool<Int>(3);
            let a = ints.new(1);
            let b = ints.new(2);
            let c = ints.new(3);
            let left = make(&mut views, &a, &b, &c, 0);
            let right = make(&mut views, &a, &b, &c, 1);
            drop(-> a);
            print(left);
            print(right);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'View(2)\nView(3)\n')
        for name in ('b', 'c'):
            with self.subTest(name=name), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(source.replace('drop(-> a);', f'drop(-> {name});'))

    def test_mutable_struct_field_reborrow_reserves_path_and_target(self):
        source = """
            struct View { left: &mut Int, right: &mut Int, tag: Int }
            fn write(a: &mut Int, b: &mut Int) { *a = 8; *b = 9; }
            fn edit(v: &mut View) {
                let a = &mut *v.left;
                let b = &mut *v.right;
                v.tag = 4;
                write(a, b);
                print(*v.left);
            }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let mut n = ints.new(1);
            let mut m = ints.new(2);
            let mut v = views.new(left: &mut n, right: &mut m);
            edit(&mut v);
            let a = &mut *v.left;
            v.tag = 5;
            *a = 11;
            let shared = &*v.left;
            let alias = &*v.left;
            print(*shared + *alias);
            print(v);
            drop(-> v);
            print(n);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '8\n22\nView(11, 9, 5)\n11\n')
        for bad, diagnostic in (
            ('drop(-> v);', 'emprunt encore utilisé'),
            ('views.reset();', 'reset interdit'),
            ('ints.reset();', 'reset interdit'),
            ('print(*v.left);', 'emprunt actif'),
            ('n.set(20);', 'emprunt actif'),
        ):
            with self.subTest(bad=bad), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('v.tag = 5;', bad))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('let b = &mut *v.right;', 'let b = &mut *v.left;'))

    def test_returned_mutable_struct_field_reserves_carrier_path_and_target(self):
        source = """
            struct View { left: &mut Int, right: &mut Int, tag: Int }
            fn choose(v: &mut View, side: Int) -> &mut Int {
                if side == 0 { return &mut *v.left; }
                return &mut *v.right;
            }
            fn relay(v: &mut View, side: Int) -> &mut Int { return choose(v, side); }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let mut n = ints.new(1);
            let mut m = ints.new(2);
            let mut v = views.new(left: &mut n, right: &mut m);
            let a = relay(&mut v, 0);
            v.tag = 5;
            *a = 8;
            let b = relay(&mut v, 1);
            *b = 9;
            print(v);
            drop(-> v);
            print(n);
            print(m);
        """
        checked = verify_program(source)
        targets = checked.function_results['relay'].reference_targets
        self.assertEqual({(t.kind, t.parameter, t.field) for t in targets},
                         {('indirect_field_parameter', 0, 'left'), ('indirect_field_parameter', 0, 'right')})
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'View(8, 9, 5)\n8\n9\n')
        for bad, diagnostic in (
            ('print(*v.left);', 'emprunt actif'),
            ('print(*v.right);', 'emprunt actif'),
            ('drop(-> v);', 'emprunt encore utilisé'),
            ('views.reset();', 'reset interdit'),
            ('ints.reset();', 'reset interdit'),
        ):
            with self.subTest(bad=bad), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('v.tag = 5;', bad))
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program('struct V { t: &mut Int } fn bad(mut v: -> V) -> &mut Int { return &mut *v.t; }')

    def test_returned_reference_array_keeps_mutable_struct_carrier_alive(self):
        source = """
            struct View { target: &mut Int, tag: Int }
            fn read(v: &View) -> [&Int; 1] { return <- [&*v.target]; }
            fn relay(v: &View) -> [&Int; 1] { let refs = read(v); return <- refs; }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(1);
            let mut n = ints.new(7);
            let mut v = views.new(target: &mut n);
            let refs = relay(&v);
            v.tag = 3;
            print(*refs[0]);
            drop(-> v);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '7\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('v.tag = 3;', 'drop(-> v);'))

    def test_replace_mutable_struct_field_after_last_reborrow(self):
        source = """
            struct View { target: &mut Int, other: &mut Int }
            fn get(v: &mut View) -> &mut Int { return &mut *v.target; }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(3);
            let mut a = ints.new(1);
            let mut b = ints.new(2);
            let mut c = ints.new(3);
            let mut v = views.new(target: &mut a, other: &mut c);
            let first = get(&mut v);
            *first = 4;
            address(v);
            v.target = &mut b;
            address(v);
            a.set(5);
            let second = get(&mut v);
            *second = 6;
            print(v);
            drop(-> v);
            print(a);
            print(b);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, view, a, b = run.stdout.splitlines()
        self.assertEqual(first, second)
        self.assertEqual((view, a, b), ('View(6, 3)', '5', '6'))
        cases = (
            ('*first = 4;\n            address(v);\n            v.target = &mut b;',
             'v.target = &mut b; *first = 4; address(v);', 'emprunt actif'),
            ('v.target = &mut b;', 'v.target = &b;', 'exige &mut Int'),
            ('v.target = &mut b;', 'v.target = &mut c;', 'emprunt actif'),
            ('v.target = &mut b;', '{ let mut local = ints.new(); v.target = &mut local; }', 'non durable'),
        )
        for before, after, diagnostic in cases:
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_returned_structure_uses_replacement_mutable_target(self):
        source = """
            struct View { target: &mut Int }
            fn identity(n: &mut Int) -> &mut Int { return n; }
            fn make(p: &mut Pool<View>, a: &mut Int, b: &mut Int) -> <- A<View> {
                let mut v = p.new(target: a);
                v.target = identity(b);
                return <- v;
            }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let mut a = ints.new(1);
            let mut b = ints.new(2);
            let v = make(&mut views, &mut a, &mut b);
            drop(-> a);
            print(v);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'View(2)\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('drop(-> a);', 'drop(-> b);'))

    def test_local_struct_borrow_updates_owner_contract(self):
        source = """
            struct View { target: &mut Int }
            fn identity(n: &mut Int) -> &mut Int { return n; }
            fn make(p: &mut Pool<View>, a: &mut Int, b: &mut Int, side: Int) -> <- A<View> {
                let mut v = p.new(target: a);
                {
                    let view = &mut v;
                    if side == 0 { view.target = identity(b); }
                    else { view.target = identity(b); }
                    print(*view.target);
                }
                return <- v;
            }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let mut a = ints.new(1);
            let mut b = ints.new(2);
            let v = make(&mut views, &mut a, &mut b, 1);
            drop(-> a);
            print(v);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '2\nView(2)\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('drop(-> a);', 'drop(-> b);'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('if side == 0', 'let old = &*view.target; if side == 0')
                           .replace('print(*view.target);', 'print(*old);'))

    def test_whole_structure_replacement_constructs_before_drop(self):
        source = """
            struct Point { x: Int }
            let mut points = pool<Point>(2);
            let mut p = points.new(x: 5);
            address(p);
            let last = &p.x;
            p = <- points.new(x: *last + 3);
            address(p);
            let next = points.new();
            address(next);
            print(p);
            print(next);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        old, new, reused, result, next = run.stdout.splitlines()
        self.assertNotEqual(old, new)
        self.assertEqual(old, reused)
        self.assertEqual((result, next), ('Point(8)', 'Point(0)'))
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy p=Point', 'destroy next=Point', 'destroy p=Point'])
        full = self.native(source.replace('pool<Point>(2)', 'pool<Point>(1)'))
        self.assertNotEqual(full.returncode, 0)
        self.assertIn('pool capacity exceeded', full.stderr)
        self.assertNotIn('destroy ', full.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(p);', 'print(*last); print(p);'))
        with self.assertRaisesRegex(Error, 'transfert <- explicite requis'):
            verify_program(source.replace('p = <- points.new', 'p = points.new'))

    def test_structure_field_cannot_be_moved_out(self):
        prefix = ('struct View { target: &mut Int } let mut ints = pool<Int>(1); '
                  'let mut views = pool<View>(1); let mut n = ints.new(); '
                  'let v = views.new(target: &mut n); ')
        with self.assertRaisesRegex(Error, 'déplacement d’un champ'):
            verify_program(prefix + 'let stolen = <- v.target;')

    def test_structure_copy_retains_shared_targets_and_uses_distinct_slots(self):
        source = """
            struct Point { x: Int }
            struct View { target: &Int, inline: Point }
            fn clone(p: &mut Pool<View>, v: &View) -> <- A<View> {
                let c = p.copy(v);
                return <- c;
            }
            let mut ints = pool<Int>(1);
            let mut originals = pool<View>(2);
            let mut copies = pool<View>(1);
            let n = ints.new(9);
            let mut v = originals.new(target: &n);
            v.inline.x = 1;
            let c = clone(&mut copies, &v);
            let mut d = copy(v);
            d.inline.x = 4;
            address(v);
            address(c);
            address(d);
            print(v);
            drop(-> v);
            print(c);
            print(d);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        a, b, c, original, explicit, implicit = run.stdout.splitlines()
        self.assertEqual(len({a, b, c}), 3)
        self.assertEqual((original, explicit, implicit), ('View(9, 1)', 'View(9, 1)', 'View(9, 4)'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('drop(-> v);', 'drop(-> n);'))
        with self.assertRaisesRegex(Error, 'Pool<View>'):
            verify_program(source.replace('let mut d = copy(v);', 'let mut d = ints.copy(v);'))
        with self.assertRaisesRegex(Error, 'structure non copiable'):
            verify_program('struct Inner { x: &mut Int } struct Outer { inner: Inner } '
                           'fn bad(p: &mut Pool<Outer>, v: &Outer) { let c = p.copy(v); }')

    def test_implicit_structure_copy_uses_runtime_origin_pool(self):
        source = """
            struct Point { x: Int }
            fn choose(a: &mut Pool<Point>, b: &mut Pool<Point>, side: Int) -> <- A<Point> {
                if side == 0 { let x = a.new(x: 1); return <- x; }
                let x = b.new(x: 2);
                return <- x;
            }
            let mut a = pool<Point>(1);
            let mut b = pool<Point>(2);
            let p = choose(&mut a, &mut b, 1);
            let c = copy(p);
            print(c);
            let available = a.new(x: 3);
            print(available);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'Point(2)\nPoint(3)\n')
        full = self.native(source.replace('choose(&mut a, &mut b, 1)', 'choose(&mut a, &mut b, 0)'))
        self.assertNotEqual(full.returncode, 0)
        self.assertIn('pool capacity exceeded', full.stderr)

    def test_impl_declarations_validate_receiver_and_field_names(self):
        source = """
            impl Point {
                fn read(self: &Point) -> Int { return self.x; }
                fn write(self: &mut Point) -> Int { self.x = self.x + 1; return self.x; }
                fn finish(self: -> Point) -> Int { return self.x; }
            }
            struct Point { x: Int }
            struct Other { x: Int }
            impl Other { fn read(self: &Other) -> Int { return self.x; } }
        """
        checked = verify_program(source)
        self.assertEqual({name: contract.parameters[0] for name, contract in checked.function_contracts.items()}, {
            'Point.read': ('self', 'ref', 'Point'),
            'Point.write': ('self', 'mut', 'Point'),
            'Point.finish': ('self', 'owned', 'Point'),
            'Other.read': ('self', 'ref', 'Other'),
        })
        for before, after, diagnostic in (
            ('fn write(', 'fn x(', 'même nom qu’un champ'),
            ('fn write(self: &mut Point)', 'fn write(self: &mut Other)', 'exige un receveur self'),
            ('fn write(self: &mut Point)', 'fn write(p: &mut Point)', 'exige un receveur self'),
            ('fn write(self: &mut Point)', 'fn write(self: &Point)', 'lecture'),
        ):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))
        with self.assertRaisesRegex(Error, 'nom de fonction déjà utilisé'):
            verify_program(source + 'impl Point { fn read(self: &Point) -> Int { return self.x; } }')

    def test_methods_dispatch_and_preserve_receiver_modes(self):
        source = """
            struct Point { x: Int }
            struct Other { x: Int }
            impl Point {
                fn read(self: &Point) -> Int { return self.x; }
                fn write(self: &mut Point, n: Int) { self.x = n; }
                fn finish(self: -> Point) -> Int { return self.x; }
            }
            impl Other { fn read(self: &Other) -> Int { return self.x + 10; } }
            fn relay(p: &mut Point) -> Int { p.write(7); return p.read(); }
            fn main() {
                let mut points = pool<Point>(1);
                let mut others = pool<Other>(1);
                let mut p = points.new(x: 3);
                let o = others.new(x: 3);
                print(p.read());
                print(o.read());
                print(relay(&mut p));
                print((-> p).finish());
                let next = points.new();
                print(next);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '3\n13\n7\n7\nPoint(0)\n')
        self.assertEqual(run.stderr.splitlines().count('destroy p=Point'), 1)
        for before, after, diagnostic in (
            ('(-> p).finish()', 'p.finish()', 'receveur consommé exige'),
            ('p.read());', '(-> p).read());', 'interdit pour une méthode'),
            ('print(relay(&mut p));', 'let loan = &p.x; p.write(7); print(*loan);', 'emprunt actif'),
            ('print(relay(&mut p));', 'let view = &p; view.write(7);', 'lecture'),
            ('let next = points.new();', 'print(p.read()); let next = points.new();', 'plus utilisable'),
        ):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_consuming_handle_method_keeps_pool_contract_and_address(self):
        source = """
            struct Point { x: Int }
            impl Point {
                fn keep(self: -> A<Point>) -> <- A<Point> { return <- self; }
                fn take(self: -> Point) -> Int { return self.x; }
            }
            fn relay(p: -> A<Point>) -> <- A<Point> {
                let out = (-> p).keep();
                return <- out;
            }
            let mut p = pool<Point>(1);
            let a = p.new(x: 4);
            address(a);
            let b = relay(-> a);
            address(b);
            print((-> b).take());
            let reused = p.new();
            address(reused);
        """
        contracts = verify_program(source).function_contracts
        self.assertEqual(contracts['Point.keep'].handle_parameters, {'self'})
        self.assertTrue(contracts['Point.keep'].handle_result)
        self.assertFalse(contracts['Point.take'].handle_parameters)
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value, reused = run.stdout.splitlines()
        self.assertEqual((before, after, value), (reused, reused, '4'))
        self.assertEqual(run.stderr.splitlines().count('destroy a=Point'), 1)
        for invalid, diagnostic in (
            (source.replace('(-> p).keep()', 'p.keep()'), 'receveur consommé exige'),
            (source.replace('address(b);', 'address(a);'), 'plus utilisable'),
            (source.replace('keep(self: -> A<Point>)', 'keep(self: -> Point)'),
             'allocation de Pool<Point>'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_overloaded_methods_resolve_control_flow_receivers_in_effects(self):
        source = """
            struct A { x: Int }
            struct B { x: Int }
            enum Choice { First, Second }
            impl A {
                fn read(self: &A, out: &mut Pool<Int>) -> Int {
                    let n = out.new(self.x);
                    return *n;
                }
            }
            impl B { fn read(self: &B, out: &mut Pool<Int>) -> Int { return 99; } }
            fn work(out: &mut Pool<Int>, side: Int) -> Int {
                let mut a = pool<A>(3);
                let mut choices = pool<Choice>(1);
                let p = if side == 0 { let k = a.new(x: 1); <- k }
                        else { let k = a.new(x: 2); <- k };
                let e = new(choices) Choice.First;
                let q = match (-> e) {
                    Choice.First => { let k = a.new(x: 3); <- k },
                    Choice.Second => { let k = a.new(x: 4); <- k }
                };
                let r = loop { loop { break; } let k = a.new(x: 5); break <- k; };
                return p.read(out) + q.read(out) + r.read(out);
            }
            let mut out = pool<Int>(1);
            print(work(&mut out, 0));
            print(work(&mut out, 1));
        """
        compiler = verify_program(source)
        self.assertEqual(compiler.function_effects['work'].allocations, {(0, 'Int')})
        self.assertEqual(compiler.function_effects['B.read'].allocations, set())
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '9\n10\n')

    def test_struct_methods_do_not_shadow_storage_or_int_operations(self):
        source = """
            struct Point { x: Int }
            impl Point {
                fn set(self: &mut Point, n: Int, m: Int) { self.x = n + m; }
                fn reset(self: &mut Point) { self.x = 10; }
                fn drop(self: &Point) { print(self.x); }
            }
            fn run(ints: &mut Pool<Int>) {
                let mut points = pool<Point>(1);
                let mut p = points.new();
                let mut n = ints.new(1);
                n.set(3);
                p.set(*n, 4);
                p.drop();
                ints.drop(-> n);
                p.reset();
                print(p.x);
                let next = ints.new(5);
                print(next);
                ints.reset();
            }
            let mut ints = pool<Int>(1);
            run(&mut ints);
        """
        compiler = verify_program(source)
        self.assertEqual(compiler.function_effects['run'].resets, {0})
        self.assertEqual(compiler.function_effects['Point.reset'].resets, set())
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '7\n10\n5\n')
        self.assertEqual(run.stderr.splitlines().count('reset'), 1)
        with self.assertRaisesRegex(Error, 'attend 3 argument'):
            verify_program(source.replace('p.set(*n, 4);', 'p.set(*n);'))
        with self.assertRaisesRegex(Error, 'set exige un entier'):
            verify_program(source.replace('n.set(3);', 'n.set(3, 4);'))

    def test_structure_methods_share_names_with_expression_builtins(self):
        source = """
            struct Point { x: Int }
            impl Point {
                fn new(self: &Point) -> Int { return self.x; }
                fn copy(self: &Point, other: &Point) -> Int { return self.x + other.x; }
                fn len(self: &Point, extra: Int) -> Int { return self.x + extra; }
                fn swap(self: &mut Point, a: Int, b: Int) { self.x = a + b; }
                fn ref(self: &Point) -> Int { return self.x; }
                fn replace(self: &mut Point, a: Int, b: Int) { self.x = a - b; }
            }
            fn main() {
                let mut points = pool<Point>(2);
                let mut p = points.new(x: 4);
                let q = points.copy(p);
                let view = &q;
                let mut a = [3, 7];
                a.swap(0, 1);
                p.swap(2, 3);
                print(p.new());
                print(p.copy(view));
                print(p.len(2));
                print(a.len());
                print(a[0]);
                let table = a.ref();
                print(table[0]);
                p.replace(9, 1);
                print(p.ref());
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '5\n9\n7\n2\n7\n7\n8\n')
        with self.assertRaisesRegex(Error, 'len exige 0 argument'):
            verify_program(source.replace('print(a.len());', 'print(a.len(2));'))
        with self.assertRaisesRegex(Error, 'attend 2 argument'):
            verify_program(source.replace('print(p.len(2));', 'print(p.len());'))

    def test_split_at_mut_dispatches_structure_methods_and_vector_builtin(self):
        source = """
            struct Counter { value: Int }
            struct Point { x: Int }
            impl Counter {
                fn split_at_mut(self: &mut Counter) { self.value = 8; }
            }
            impl Point {
                fn split_at_mut(self: &Point, ignored: Int) -> &Int { return &self.x; }
            }
            fn relay(p: &Point) -> &Int { return p.split_at_mut(0); }
            let mut counters = pool<Counter>(1);
            let mut points = pool<Point>(1);
            let mut counter = counters.new();
            let mut point = points.new(x: 9);
            counter.split_at_mut();
            print(counter.value);
            let held = relay(&point);
            CHECK
            print(*held);
            let mut vectors = pool<Vector<Int>>(1);
            let mut v = vectors.new();
            v.push(1);
            v.push(2);
            let (mut left, mut right) = v.split_at_mut(1);
            left[0] = 3;
            right[0] = 4;
            print(v[0]);
            print(v[1]);
        """
        valid = source.replace('CHECK', '')
        run = self.native(valid)
        self.assertEqual((run.returncode, run.stdout), (0, '8\n9\n3\n4\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'point.x = 1;'))
        with self.assertRaisesRegex(Error, 'attend 2 argument'):
            verify_program(valid.replace('p.split_at_mut(0)', 'p.split_at_mut()'))
        with self.assertRaisesRegex(Error, 'split_at_mut exige un indice'):
            verify_program(valid.replace('v.split_at_mut(1)', 'v.split_at_mut()'))

    def test_join_method_dispatches_on_structure_and_retains_receiver(self):
        source = """
            struct Point { x: Int }
            impl Point { fn join(self: &Point) -> &Int { return &self.x; } }
            fn relay(p: &Point) -> &Int { return p.join(); }
            fn read(n: &Int) -> Int { return *n; }
            let mut points = pool<Point>(1);
            let mut p = points.new(x: 7);
            let view = &p;
            BEFORE
            print(read(view.join()));
            let saved = relay(&p);
            AFTER
            print(*saved);
            p.x = 9;
            print(p.x);
        """
        run = self.native(source.replace('BEFORE', '').replace('AFTER', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n7\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('BEFORE', 'drop(-> p);').replace('AFTER', ''))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', '').replace('AFTER', 'p.x = 8;'))

    def test_method_borrow_result_is_reserved_as_direct_argument(self):
        source = """
            struct Point { x: Int }
            impl Point {
                fn ref(self: &Point) -> &Int { return &self.x; }
                fn edit(self: &mut Point) -> &mut Int { return &mut self.x; }
            }
            fn read(x: &Int, n: Int) -> Int { return *x + n; }
            fn write(x: &mut Int, n: Int) { *x = n; }
            fn pair(a: &mut Int, b: &mut Int) { *a = 1; *b = 2; }
            fn clear(p: &mut Pool<Point>) -> Int { p.reset(); return 0; }
            fn main() {
                let mut points = pool<Point>(1);
                let mut p = points.new(x: 4);
                print(read(p.ref(), 2));
                write(p.edit(), 8);
                print(p);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '6\nPoint(8)\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('read(p.ref(), 2)', 'read(p.ref(), clear(&mut points))'))
        with self.assertRaisesRegex(Error, 'exige un emprunt mut'):
            verify_program(source.replace('write(p.edit(), 8)', 'write(p.ref(), 8)'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('write(p.edit(), 8)', 'pair(p.edit(), p.edit())'))

    def test_method_detached_borrow_argument_allows_carrier_reset(self):
        source = """
            struct View { target: &Int }
            impl View { fn get(self: &View) -> &Int { return self.target; } }
            fn read(x: &Int, n: Int) -> Int { return *x + n; }
            fn clear_views(p: &mut Pool<View>) -> Int { p.reset(); return 1; }
            fn clear_ints(p: &mut Pool<Int>) -> Int { p.reset(); return 1; }
            fn main() {
                let mut views = pool<View>(1);
                let mut ints = pool<Int>(1);
                let n = ints.new(9);
                let v = views.new(target: &n);
                print(read(v.get(), clear_views(&mut views)));
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '10\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('clear_views(&mut views)', 'clear_ints(&mut ints)'))

    def test_consuming_structure_method_can_return_shared_field(self):
        source = """
            struct View { target: &Int }
            impl View {
                fn take(self: -> View) -> &Int { return self.target; }
                fn wrap(self: -> View) -> [&Int; 1] { return <- [self.target]; }
            }
            fn relay(v: -> View) -> &Int { return (-> v).take(); }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(2);
            let n = ints.new(9);
            let m = ints.new(4);
            let first = views.new(target: &n);
            address(first);
            let a = relay(-> first);
            let second = views.new(target: &m);
            address(second);
            let refs = (-> second).wrap();
            let third = views.new(target: &n);
            address(third);
            print(*a);
            print(*refs[0]);
            print(third);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, third, a, b, view = run.stdout.splitlines()
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual((a, b, view), ('9', '4', 'View(9)'))
        for name in ('n', 'm'):
            with self.subTest(name=name), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(source.replace('address(third);', f'drop(-> {name});'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('let a = relay(-> first);', 'let a = relay(-> first); print(first);'))

    def test_consuming_method_result_initializes_shared_field_in_reused_slot(self):
        source = """
            struct View { target: &Int, tag: Int }
            impl View { fn take(self: -> View) -> &Int { return self.target; } }
            fn repack(p: &mut Pool<View>, v: -> View) -> <- A<View> {
                let replacement = p.new(target: (-> v).take(), tag: 8);
                return <- replacement;
            }
            fn clear(p: &mut Pool<Int>) -> Int { p.reset(); return 0; }
            let mut views = pool<View>(1);
            let mut ints = pool<Int>(1);
            let n = ints.new(9);
            let v = views.new(target: &n);
            address(v);
            let w = repack(&mut views, -> v);
            address(w);
            print(w);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, view = run.stdout.splitlines()
        self.assertEqual(first, second)
        self.assertEqual(view, 'View(9, 8)')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('repack(&mut views, -> v)',
                                          'views.new(target: (-> v).take(), tag: clear(&mut ints))'))

    def test_static_utf8_views_preserve_bytes_through_calls_and_returns(self):
        source = r'''
            fn select_text(side: Int) -> &str {
                let text = if side == 0 { "été" } else { "🌍" };
                return text;
            }
            fn show(text: &str) {
                print(text);
                print(text.byte_len());
            }
            fn main() {
                let text: &str = select_text(0);
                show(text);
                show(select_text(1));
                show("a\u0000b");
                show("e\u0301//");
                show("");
                print("é".byte_len());
                let mut caption = "before";
                if text.byte_len() == 5 { caption = "after"; }
                print(caption);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'été\n5\n🌍\n4\na\x00b\n3\ne\u0301//\n5\n\n0\n2\nafter\n')
        self.assertEqual(run.stderr, '')
        self.assertIn('static const unsigned char', compile_source(source))

    def test_utf8_literals_reject_invalid_escape_and_int_coercion(self):
        for source, diagnostic in (
            (r'print("\uD800");', 'littéral de texte UTF-8 invalide'),
            (r'print("\q");', 'littéral de texte UTF-8 invalide'),
            ('let text: &str = 1;', 'attendu &str'),
            ('fn size(text: &str) -> Int { return text.byte_len(1); }', 'aucun argument'),
            ('fn f(x: Int) {} f("é");', 'Int copiable'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_utf8_byte_reads_and_shared_borrows_across_calls(self):
        source = '''
            fn text() -> &str { print(1); return "été"; }
            fn index() -> Int { print(2); return 1; }
            fn borrow(t: &str, i: Int) -> &u8 { return &t[i]; }
            fn read(r: &u8) -> u8 { return *r; }
            fn use_byte(b: u8) { print(3); }
            fn main() {
                let mut view = text();
                let loan: &u8 = borrow(view, index());
                view = "🌍";
                let byte: u8 = read(loan);
                use_byte(byte);
                use_byte(view[3]);
                use_byte(text()[index()]);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n2\n3\n3\n1\n2\n3\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_index_rejects_type_confusion_and_mutable_access(self):
        for source, diagnostic in (
            ('let b = "é"[2];', 'hors bornes'),
            ('let t = "é"; let b = t[-1];', 'hors bornes'),
            ('let b = "é"["x"];', 'indice UTF-8 doit être Int'),
            ('let t = "é"; let b = &mut t[0];', 'immuables'),
            ('let t = "é"; t[0] = 1;', 'tableau'),
            ('let b: &u8 = "é"[0];', 'attendu &u8'),
            ('let b: u8 = &"é"[0];', 'attendu u8'),
            ('fn f(x: Int) {} f("é"[1]);', 'Int copiable'),
            ('fn f(x: u8) {} f(1);', 'attend u8'),
            ('fn f(t: &str) -> u8 { return &t[1]; }', 'retour'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_utf8_index_checks_dynamic_bounds_before_reading_or_borrowing(self):
        for text, index, borrow in (('""', 0, ''), ('"é"', 2, ''), ('"é"', -1, '&'), ('"🌍"', 4, '&')):
            with self.subTest(text=text, index=index, borrow=borrow):
                typ = '&u8' if borrow else 'u8'
                run = self.native(f'''
                    fn checked(t: &str, i: Int) -> {typ} {{ return {borrow}t[i]; }}
                    fn consume(b: {typ}) {{ print(7); }}
                    consume(checked({text}, {index}));
                ''')
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(run.stderr, 'indice UTF-8 hors bornes\n')
                self.assertEqual(run.stdout, '')

    def test_char_at_matches_all_tags_through_typed_calls(self):
        run = self.native(r'''
            fn get(t: &str, i: Int) -> Result<char, CharAtError> {
                return t.char_at(i);
            }
            fn show(c: char) -> Int {
                print(c);
                return c.utf8_len();
            }
            fn probe(t: &str, i: Int) -> Int {
                let result: Result<char, CharAtError> = get(t, i);
                match result {
                    Err(CharAtError::NotCharBoundary) => { return 92; },
                    Ok(c) => { return show(c); },
                    Err(CharAtError::OutOfBounds) => { return 91; }
                }
            }
            print(probe("été", 0));
            print(probe("été", 1));
            print(probe("été", 2));
            print(probe("été", 3));
            print(probe("été", 5));
            print(probe("", 0));
            print(probe("🌍", -1));
            print(probe("🌍", 0));
            print(probe("\u0000", 0));
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr, '')
        self.assertEqual(run.stdout, 'é\n2\n92\nt\n1\né\n2\n91\n91\n91\n🌍\n4\n\0\n1\n')

    def test_char_from_str_preserves_scalar_and_matches_typed_errors(self):
        run = self.native(r'''
            fn identity(c: char) -> char { return c; }
            fn test(t: &str) {
                match char::from_str(t) {
                    Err(CharFromStrError::Empty) => { print(1); },
                    Err(CharFromStrError::MultipleChars) => { print(2); },
                    Ok(c) => {
                        let decoded: char = identity(c);
                        print(decoded);
                        print(decoded.utf8_len());
                    }
                }
            }
            test("");
            test("e\u0301");
            test("é");
            test("€");
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr, '')
        self.assertEqual(run.stdout, '1\n2\né\n2\n€\n3\n')

    def test_char_match_preserves_single_evaluation_and_pool_effects(self):
        run = self.native('''
            fn index(p: &mut Pool<Int>, n: -> Int) -> Int {
                drop(-> n);
                print(10);
                return 1;
            }
            let mut p = pool<Int>(1);
            let n = p.new(10);
            match "é".char_at(index(&mut p, -> n)) {
                Ok(_) => { print(99); },
                Err(CharAtError::NotCharBoundary) => {
                    let replacement = p.new(20);
                    print(replacement);
                },
                _ => { print(98); }
            }
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '10\n20\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy n=10', 'reclaim n',
                                                   'destroy replacement=20', 'reclaim replacement'])

    def test_char_result_rejects_invalid_patterns_and_scalar_confusion(self):
        for source, diagnostic in (
            ('match "a".char_at(0) { Ok(c) => { print(c); } }', 'non exhaustif'),
            ('match "a".char_at(0) { Ok(_) => {}, Ok(_) => {}, _ => {} }', 'dupliqué'),
            ('match "a".char_at(0) { _ => {}, Ok(_) => {} }', 'doit terminer'),
            ('match "a".char_at(0) { Err(CharFromStrError::Empty) => {}, _ => {} }',
             'type du résultat ou de l’erreur incompatible'),
            ('match 1 { _ => {} }', 'type du résultat'),
            ('let n = "a".char_at("x");', 'indice Int'),
            ('let n = char::from_str(1);', 'exige un &str'),
            ('fn use(c: char) {} use("é"[0]);', 'attend char'),
            ('fn use(n: Int) {} match char::from_str("é") { Ok(c) => { use(c); }, _ => {} }',
             'Int copiable'),
            ('fn wrong(t: &str) -> Result<char, CharAtError> { return char::from_str(t); }',
             'retour'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_char_match_all_arms_have_the_same_parent_for_transfers(self):
        run = self.native('''
            fn run(t: &str, i: Int, n: -> Int) {
                match t.char_at(i) {
                    Ok(c) => { n ->; drop(-> n); print(c); },
                    Err(CharAtError::NotCharBoundary) => { n ->; drop(-> n); print(1); },
                    Err(CharAtError::OutOfBounds) => { n ->; drop(-> n); print(2); }
                }
            }
            let mut p = pool<Int>(1);
            let a = p.new(10);
            run("é", 0, -> a);
            let b = p.new(20);
            run("é", 1, -> b);
            let c = p.new(30);
            run("é", 2, -> c);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'é\n1\n2\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy a=10', 'reclaim a',
                                                   'destroy b=20', 'reclaim b',
                                                   'destroy c=30', 'reclaim c'])

    def test_utf8_slices_preserve_view_after_reassignment_and_return(self):
        run = self.native(r'''
            fn middle(t: &str, lo: Int, hi: Int) -> &str {
                return &t[lo..hi];
            }
            let mut text = "été🌍";
            let prefix: &str = &text[..2];
            let middle_view = middle(text, 2, 5);
            let suffix = &text[5..];
            let whole = &text[..];
            let empty = &text[9..9];
            text = "changed";
            print(prefix);
            print(middle_view);
            print(suffix);
            print(whole);
            print(empty);
            print(text);
            print((&whole[5..]).byte_len());
            match (&whole[5..]).char_at(0) {
                Ok(c) => { print(c); },
                _ => { print(999); }
            }
            print(&""[..]);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'é\nté\n🌍\nété🌍\n\nchanged\n4\n🌍\n\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_slice_checks_literal_boundaries_and_requires_ampersand(self):
        for source, diagnostic in (
            ('let t: &str = "é"[..2];', 'emprunt explicite'),
            ('let t = &mut "é"[..2];', 'immuable'),
            ('let t = &"é"[..1];', 'continuation'),
            ('let t = &"é"[1..1];', 'continuation'),
            ('let t = &"é"[2..1];', 'continuation|bornes'),
            ('let t = &"é"[3..];', 'bornes'),
            ('let t = &"é"[-1..];', 'bornes'),
            ('let t = &"é"[.. "x"];', 'doit être Int'),
            ('let t = &[1, 2][..];', 'exige un &str'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_utf8_slice_checks_dynamic_boundaries_after_ordered_effects(self):
        source = '''
            fn lower(i: Int) -> Int { print(10); return i; }
            fn upper(i: Int) -> Int { print(20); return i; }
            fn text() -> &str { print(5); return "été"; }
            fn probe(lo: Int, hi: Int) -> &str {
                return &text()[lower(lo)..upper(hi)];
            }
            print(probe(LOW, HIGH));
        '''
        for lo, hi, expected, diagnostic in (
            (2, 5, 'té\n', ''),
            (5, 5, '\n', ''),
            (-1, 5, '', 'bornes de découpe UTF-8 invalides\n'),
            (3, 2, '', 'bornes de découpe UTF-8 invalides\n'),
            (0, 6, '', 'bornes de découpe UTF-8 invalides\n'),
            (1, 5, '', 'borne de découpe sur un octet de continuation UTF-8\n'),
            (0, 4, '', 'borne de découpe sur un octet de continuation UTF-8\n'),
        ):
            with self.subTest(lo=lo, hi=hi):
                run = self.native(source.replace('LOW', str(lo)).replace('HIGH', str(hi)))
                self.assertEqual(run.returncode, int(bool(diagnostic)), run.stderr)
                self.assertEqual(run.stdout, '5\n10\n20\n' + expected)
                self.assertEqual(run.stderr, diagnostic)

    def test_u8_array_initialization_calls_and_mutation(self):
        run = self.native('''
            fn read(t: &[u8; 2], i: Int) -> u8 { return t[i]; }
            fn show(n: u8) { print(3); }
            fn edit(t: &mut [u8; 2], i: Int, b: u8) { t[i] = b; }
            fn make() -> [u8; 2] { return <- [0x61, 0x62]; }
            let mut bytes: [u8; 2] = [0xc3, 0xa9];
            let view = &bytes[0];
            show(*view);
            edit(&mut bytes, 0, "a"[0]);
            show(read(&bytes, 0));
            let old = bytes.replace(0, 0xff);
            show(old);
            show(read(&make(), 1));
            let repeated: [u8; 2] = [0; 2];
            show(repeated[1]);
            let empty: [u8; 0] = [];
            print(empty.len());
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '3\n3\n3\n3\n3\n0\n')
        self.assertEqual(run.stderr, '')

    def test_u8_array_rejects_narrowing_bounds_and_active_loan_conflicts(self):
        for source, diagnostic in (
            ('let b: [u8; 1] = [256];', 'comprise entre 0 et 255'),
            ('let b: [u8; 1] = [-0x1];', 'comprise entre 0 et 255'),
            ('let b: [u8; 2] = [1];', 'longueur'),
            ('fn f(n: Int) { let b: [u8; 1] = [n]; }', 'doit être u8'),
            ('let b: [u8; 0] = []; let x = b[0];', 'tableau vide'),
            ('let b: [u8; 1] = [0]; let x = b[1];', 'hors limites'),
            ('let b: [u8; 1] = [0]; b[0] = 1;', 'immuable'),
            ('''fn show(n: u8) {}
                let mut b: [u8; 2] = [0, 1];
                let view = &b[0];
                b[1] = 2;
                show(*view);
             ''', 'emprunt'),
            ('''fn show(n: u8) {}
                fn edit(b: &mut [u8; 1]) { b[0] = 2; }
                let mut b: [u8; 1] = [1];
                let view = &b[0];
                edit(&mut b);
                show(*view);
             ''', 'emprunt'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_from_utf8_borrows_vector_bytes_in_logical_order(self):
        source = """
            fn decode(bytes: &[u8]) -> Result<&str, Utf8Error> { return str::from_utf8(bytes); }
            let mut p = pool<Vector<u8>>(2);
            let mut strings = pool<String>(1);
            let mut first = p.new();
            first.push(0x61);
            let mut v = p.new();
            v.push(0xc3);
            v.push(0xa9);
            v.push(0x21);
            let mut dest = strings.new();
            match decode(&v[..]) {
                Ok(text) => {
                    print(text);
                    print(&text[..2]);
                    match text.char_at(0) {
                        Ok(c) => { print(c); },
                        _ => {}
                    }
                    dest.push_str(text);
                },
                Err(_) => { print(0); }
            }
            print(&dest[..]);
            match decode(&v[..1]) {
                Ok(_) => { print(0); },
                Err(_) => { print(1); }
            }
            v.push(0x62);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, 'é!\né\né\né!\n1\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('print(&text[..2]);', 'v.push(0x62); print(&text[..2]);'))

    def test_from_utf8_match_retains_bytes_until_last_derived_use(self):
        run = self.native(r'''
            fn read(b: u8) { print(9); }
            fn inspect(t: &[u8; 0]) {
                match str::from_utf8(t) {
                    Ok(empty) => { print(empty.byte_len()); },
                    Err(_) => { print(99); }
                }
            }
            let mut bytes: [u8; 2] = [0xc3, 0xa9];
            let result: Result<&str, Utf8Error> = str::from_utf8(&bytes);
            match result {
                Ok(view) => {
                    let alias: &str = view;
                    print(alias);
                    let whole = &alias[..];
                    let byte: &u8 = &whole[1];
                    read(*byte);
                    bytes[1] = 0xff;
                },
                Err(_) => { print(98); }
            }
            match str::from_utf8(&bytes) {
                Ok(_) => { print(97); },
                Err(_) => { bytes[1] = 0xa9; print(1); }
            }
            match str::from_utf8(&bytes) {
                Ok(view) => {
                    match view.char_at(0) {
                        Ok(c) => { print(c); },
                        _ => { print(96); }
                    }
                },
                Err(_) => { print(95); }
            }
            let empty: [u8; 0] = [];
            inspect(&empty);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'é\n9\n1\né\n0\n')
        self.assertEqual(run.stderr, '')

    def test_from_utf8_rejects_mutation_during_live_view_and_escape(self):
        for source, diagnostic in (
            ('''let mut b: [u8; 1] = [65];
                let result = str::from_utf8(&b);
                b[0] = 66;
                match result { Ok(v) => { print(v); }, Err(_) => {} }''', 'emprunt actif'),
            ('''let mut b: [u8; 1] = [65];
                match str::from_utf8(&b) {
                    Ok(v) => {
                        let view = &v[..];
                        b[0] = 66;
                        print(view);
                    },
                    Err(_) => {}
                }''', 'emprunt actif'),
            ('''fn edit(b: &mut [u8; 1]) -> Int { b[0] = 66; return 0; }
                let mut b: [u8; 1] = [65];
                match str::from_utf8(&b) {
                    Ok(v) => { let c = v.char_at(edit(&mut b)); },
                    Err(_) => {}
                }''', 'emprunt actif'),
            ('''fn edit(b: &mut [u8; 1]) -> Int { b[0] = 66; return 0; }
                let mut b: [u8; 1] = [65];
                match str::from_utf8(&b) {
                    Ok(v) => { let c = v[edit(&mut b)]; },
                    Err(_) => {}
                }''', 'emprunt actif'),
            ('''fn escape() -> &str {
                    let b: [u8; 1] = [65];
                    match str::from_utf8(&b) {
                        Ok(v) => { return v; },
                        Err(_) => { return ""; }
                    }
                }''', 'retour'),
            ('''let mut escaped = "";
                {
                    let b: [u8; 1] = [65];
                    match str::from_utf8(&b) {
                        Ok(v) => { escaped = &v[..]; },
                        Err(_) => {}
                    }
                }
                print(escaped);''', 'non durable'),
            ('''fn take(b: &[u8; 1]) {}
                let b: [u8; 1] = [65];
                match str::from_utf8(&b) {
                    Ok(v) => { take(v); },
                    Err(_) => {}
                }''', 'argument tableau'),
            ('''fn make() -> [u8; 1] { return <- [65]; }
                let r = str::from_utf8(&make());
                match r { Ok(v) => { print(v); }, Err(_) => {} }''',
             'non durable'),
            ('let b = [65]; let r = str::from_utf8(&b);', 'tableau u8'),
            ('let mut b: [u8; 1] = [65]; let r = str::from_utf8(&mut b);', 'emprunt partagé'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_borrowed_utf8_relay_through_text_and_byte_returns(self):
        run = self.native('''
            fn suffix(t: &str) -> &str { return &t[1..]; }
            fn relay(t: &str) -> &str { return suffix(t); }
            fn first(t: &str) -> &u8 { return &t[0]; }
            fn take(b: &u8) -> &u8 { return b; }
            fn use_byte(b: u8) { print(7); }
            let mut bytes: [u8; 2] = [0x61, 0x62];
            match str::from_utf8(&bytes) {
                Ok(t) => {
                    let tail = relay(t);
                    print(tail);
                    let b = take(first(tail));
                    use_byte(*b);
                    bytes[0] = 0x63;
                },
                Err(_) => {}
            }
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'b\n7\n')
        self.assertEqual(run.stderr, '')

    def test_borrowed_utf8_arguments_and_returns_reserve_source(self):
        for declarations, body in (
            ('''fn edit(b: &mut [u8; 1]) -> Int { b[0] = 66; return 0; }
                fn show(v: &str, n: Int) { print(v); }''',
             'show(&v[..], edit(&mut b));'),
            ('fn show(b: &mut [u8; 1], v: &str) { b[0] = 66; print(v); }',
             'show(&mut b, v);'),
            ('fn show(v: &str, b: &mut [u8; 1]) { b[0] = 66; print(v); }',
             'show(v, &mut b);'),
            ('fn relay(v: &str) -> &str { return v; }',
             'let r = relay(v); b[0] = 66; print(r);'),
            ('''fn first(v: &str) -> &u8 { return &v[0]; }
                fn show(n: u8) {}''',
             'let r = first(v); b[0] = 66; show(*r);'),
        ):
            source = declarations + '''
                let mut b: [u8; 1] = [65];
                match str::from_utf8(&b) {
                    Ok(v) => { BODY },
                    Err(_) => {}
                }
            '''.replace('BODY', body)
            with self.subTest(body=body), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source)

    def test_utf8_return_contract_releases_unrelated_arguments(self):
        run = self.native('''
            fn validate(t: &[u8; 1]) -> &str {
                match str::from_utf8(t) {
                    Ok(v) => { return v; },
                    Err(_) => { return ""; }
                }
            }
            fn relay(t: &[u8; 1]) -> &str { return validate(t); }
            fn pick(first: &str, second: &str) -> &str {
                return if first.byte_len() == 0 { "" } else { &first[..] };
            }
            fn literal(t: &str) -> &str { return "fixed"; }
            let mut a: [u8; 1] = [65];
            let mut b: [u8; 1] = [66];
            let left = relay(&a);
            let right = relay(&b);
            let picked = pick(left, right);
            b[0] = 0xff;
            print(picked);
            let constant = literal(picked);
            a[0] = 0xff;
            print(constant);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'A\nfixed\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_return_contract_keeps_all_reachable_origins(self):
        source = '''
            fn view(t: &[u8; 1]) -> &str {
                match str::from_utf8(t) {
                    Ok(v) => { return v; },
                    Err(_) => { return ""; }
                }
            }
            fn pick(a: &str, b: &str, n: Int) -> &str {
                let v = if n == 0 { &a[..] } else { &b[..] };
                return v;
            }
            let mut a: [u8; 1] = [65];
            let mut b: [u8; 1] = [66];
            let v = pick(view(&a), view(&b), 1);
            WRITE
            print(v);
        '''
        for write in ('a[0] = 0xff;', 'b[0] = 0xff;'):
            with self.subTest(write=write), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('WRITE', write))
        run = self.native(source.replace('WRITE', '') + 'a[0] = 0xff; b[0] = 0xff;')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'B\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_result_transport_matches_after_multiple_calls(self):
        run = self.native('''
            fn validate(t: &[u8; 2]) -> Result<&str, Utf8Error> {
                return str::from_utf8(t);
            }
            fn relay(r: Result<&str, Utf8Error>) -> Result<&str, Utf8Error> {
                return r;
            }
            fn handle(r: Result<&str, Utf8Error>) {
                match r {
                    Ok(v) => { print(v); },
                    Err(_) => { print(9); }
                }
            }
            let mut bytes: [u8; 2] = [0xc3, 0xa9];
            let r: Result<&str, Utf8Error> = relay(validate(&bytes));
            handle(r);
            bytes[1] = 0xff;
            handle(relay(validate(&bytes)));
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'é\n9\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_result_transport_preserves_conditional_provenances(self):
        source = '''
            fn pick(a: &[u8; 1], b: &[u8; 1], flag: Int) -> Result<&str, Utf8Error> {
                return if flag == 0 { str::from_utf8(a) } else { str::from_utf8(b) };
            }
            let mut a: [u8; 1] = [65];
            let mut b: [u8; 1] = [66];
            let r = pick(&a, &b, 1);
            WRITE
            match r { Ok(v) => { print(v); }, Err(_) => {} }
        '''
        for write in ('a[0] = 0xff;', 'b[0] = 0xff;'):
            with self.subTest(write=write), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('WRITE', write))
        run = self.native(source.replace('WRITE', '') + 'a[0] = 0xff; b[0] = 0xff;')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'B\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_result_transport_rejects_local_escape_and_argument_conflict(self):
        for source, diagnostic in (
            ('''fn escape() -> Result<&str, Utf8Error> {
                    let b: [u8; 1] = [65];
                    return str::from_utf8(&b);
                }''', 'non durable'),
            ('''let b: [u8; 1] = [65];
                let r = if true {
                    let local: [u8; 1] = [66];
                    str::from_utf8(&local)
                } else { str::from_utf8(&b) };
                match r { Ok(v) => { print(v); }, Err(_) => {} }''', 'non durable'),
            ('''fn edit(b: &mut [u8; 1]) -> Int { b[0] = 0xff; return 0; }
                fn handle(r: Result<&str, Utf8Error>, ignored: Int) {
                    match r { Ok(v) => { print(v); }, Err(_) => {} }
                }
                let mut b: [u8; 1] = [65];
                handle(str::from_utf8(&b), edit(&mut b));''', 'emprunt actif'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_utf8_reassignment_joins_origins_and_preserves_old_alias(self):
        source = '''
            fn as_text(t: &[u8; 1]) -> &str {
                match str::from_utf8(t) {
                    Ok(v) => { return v; },
                    Err(_) => { return ""; }
                }
            }
            fn probe(flag: Int) {
                let mut a: [u8; 1] = [65];
                let mut b: [u8; 1] = [66];
                let mut v = "initial";
                if flag == 0 { v = as_text(&a); } else { v = as_text(&b); }
                let alias = v;
                v = "final";
                EARLY
                print(alias);
                a[0] = 0xff;
                b[0] = 0xff;
                print(v);
            }
            probe(1);
        '''
        for early in ('a[0] = 0xff;', 'b[0] = 0xff;'):
            with self.subTest(early=early), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('EARLY', early))
        run = self.native(source.replace('EARLY', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'B\nfinal\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_reassignment_replaces_result_and_byte_sources(self):
        run = self.native('''
            fn use(b: u8) { print(7); }
            let mut a: [u8; 1] = [65];
            let mut b: [u8; 2] = [0xc3, 0xa9];
            let mut r = str::from_utf8(&a);
            match r { Ok(_) => {}, Err(_) => {} }
            r = str::from_utf8(&b);
            a[0] = 0xff;
            match r {
                Ok(v) => {
                    let mut byte = &v[1];
                    byte = &"A"[0];
                    b[1] = 0xff;
                    use(*byte);
                },
                Err(_) => { print(9); }
            }
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '7\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_reassignment_keeps_borrow_across_loop_reentry(self):
        source = '''
            fn as_text(t: &[u8; 1]) -> &str {
                match str::from_utf8(t) {
                    Ok(v) => { return v; },
                    Err(_) => { return ""; }
                }
            }
            let mut bytes: [u8; 1] = [65];
            let mut v = "initial";
            let mut i = 0;
            while i < 2 {
                print(v);
                v = as_text(&bytes);
                i = i + 1;
                EARLY
            }
            print(v);
            bytes[0] = 0xff;
        '''
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('EARLY', 'bytes[0] = 0xff;'))
        run = self.native(source.replace('EARLY', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'initial\nA\nA\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_temporary_lasts_through_match_and_nested_calls(self):
        run = self.native('''
            fn make() -> [u8; 2] { return <- [0xc3, 0xa9]; }
            fn validate(b: &[u8; 2]) -> Result<&str, Utf8Error> {
                let result = str::from_utf8(b);
                return result;
            }
            fn show(r: Result<&str, Utf8Error>) {
                match r { Ok(v) => { print(v); }, Err(_) => { print(0); } }
            }
            match str::from_utf8(&make()) {
                Ok(v) => { let s = &v[..]; print(s); },
                Err(_) => { print(0); }
            }
            show(validate(&make()));
            match validate(&make()) {
                Ok(v) => { print(v); },
                Err(_) => { print(0); }
            }
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'é\né\né\n')
        self.assertEqual(run.stderr, '')

    def test_utf8_temporary_cannot_escape_its_instruction(self):
        declarations = '''
            fn make() -> [u8; 1] { return <- [65]; }
            fn validate(b: &[u8; 1]) -> Result<&str, Utf8Error> { return str::from_utf8(b); }
        '''
        for source in (
            '''let r = validate(&make());
               match r { Ok(v) => { print(v); }, Err(_) => {} }''',
            '''let mut outside = "";
               match validate(&make()) {
                   Ok(v) => { outside = v; },
                   Err(_) => {}
               }
               print(outside);''',
            '''fn escape() -> Result<&str, Utf8Error> {
                   return validate(&make());
               }''',
            '''let bytes: [u8; 1] = [66];
               match if true { validate(&make()) } else { validate(&bytes) } {
                   Ok(v) => { print(v); },
                   Err(_) => {}
               }''',
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, 'non durable'):
                verify_program(declarations + source)

    def test_string_pool_growth_transfer_and_slot_reuse(self):
        run = self.native('''
            fn make(p: &mut Pool<String>) -> <- String {
                let mut t = p.new();
                t.push_str("é");
                return <- t;
            }
            fn append(s: &mut String, text: &str) { s.push_str(text); }
            let mut p = pool<String>(2);
            let mut s: String = make(&mut p);
            append(&mut s, "");
            match char::from_str("🌍") {
                Ok(c) => { s.push(c); },
                _ => {}
            }
            print(s.byte_len());
            let t = #(directive, stack_region_max_size=1M) {
                let mut inner = p.new();
                inner.push_str("été");
                <- inner
            };
            print(t.byte_len());
            drop(-> s);
            let reuse = p.new();
            print(reuse.byte_len());
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '6\n5\n0\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy t=0', 'reuse reuse',
                                                   'destroy reuse=0', 'destroy inner=0',
                                                   'reclaim inner', 'reclaim reuse'])

    def test_string_methods_enforce_pool_type_and_mutable_receiver(self):
        for source, diagnostic in (
            ('let mut p = pool<String>(1); let s = p.new(); s.push_str("a");', 'immuable'),
            ('let mut p = pool<String>(1); let mut s = p.new(); s.push_str(1);', 'exige un &str'),
            ('let mut p = pool<String>(1); let s = p.new(); print(s);', 'vue &str explicite'),
            ('let mut p = pool<String>(1); let s = p.new(1);', 'incompatible|pool<Int>'),
            ('let mut p = pool<String>(1); let s = p.new(); let c = copy(s);', 'tableau'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_string_views_relay_and_explicit_duplication(self):
        run = self.native('''
            fn view(t: &String) -> &str { return &t[..]; }
            fn read(t: &String) -> &u8 { return &t[1]; }
            fn use(b: u8) { print(7); }
            let mut p = pool<String>(2);
            let mut source = p.new();
            source.push_str("été");
            let text = view(&source);
            print(text);
            let byte = read(&source);
            use(*byte);
            use(*read(&source));
            let mut duplicate = p.new();
            duplicate.push_str(&source[..]);
            source.push_str("🌍");
            print(&source[5..]);
            drop(-> source);
            print(&duplicate[..]);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'été\n7\n7\n🌍\nété\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy source=0', 'destroy duplicate=0',
                                                   'reclaim duplicate', 'reclaim source'])

    def test_string_views_reject_mutation_drop_escape_and_reset_aliasing(self):
        base = 'let mut p = pool<String>(1); let mut s = p.new(); s.push_str("abc");'
        for prefix, body, diagnostic in (
            ('', 'let v = &s[..]; s.push_str("x"); print(v);', 'emprunt actif'),
            ('', 'let v = &s[..]; drop(-> s); print(v);', 'emprunt encore utilisé'),
            ('', 's.push_str(&s[..]);', 'emprunt actif'),
            ('', 'let b = &mut s[0];', 'immuables'),
            ('', 's[0] = 1;', 'tableau'),
            ('fn reborrow(s: &mut String) -> &str { return &s[..]; }',
             'let v = reborrow(&mut s); s.push_str("x"); print(v);', 'emprunt actif'),
            ('fn take(s: -> String) {}', 'let v = &s[..]; take(-> s); print(v);', 'emprunt'),
            ('fn hazard(v: &str, p: &mut Pool<String>) { p.reset(); print(v); }',
             'hazard(&s[..], &mut p);', 'reset interdit'),
            ('fn hazard(s: &String, p: &mut Pool<String>) { let v = &s[..]; p.reset(); print(v); }',
             'hazard(&s, &mut p);', 'reset interdit'),
            ('''fn hazard(b: &u8, p: &mut Pool<String>) { p.reset(); let n = *b; }''',
             'hazard(&s[1], &mut p);', 'reset interdit'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program(prefix + base + body)
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program('''
                fn escape() -> &str {
                    let mut p = pool<String>(1);
                    let s = p.new();
                    return &s[..];
                }
            ''')

    def test_string_view_can_end_before_reset_inside_call(self):
        run = self.native('''
            fn show_then_reset(v: &str, p: &mut Pool<String>) { print(v); p.reset(); }
            let mut p = pool<String>(1);
            let mut s = p.new();
            s.push_str("é");
            show_then_reset(&s[..], &mut p);
            let fresh = p.new();
            print(&fresh[..]);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'é\n\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy s=0', 'reclaim s', 'reset',
                                                   'destroy fresh=0', 'reclaim fresh'])

    def test_string_pop_returns_independent_scalars_and_reuses_suffix(self):
        run = self.native('''
            fn remove(t: &mut String) -> Option<char> { return t.pop(); }
            fn show(r: Option<char>) {
                match r { Some(c) => { print(c); }, None => { print(0); } }
            }
            let mut p = pool<String>(1);
            let mut s = p.new();
            s.push_str("aé€🌍");
            show(remove(&mut s));
            print(&s[..]);
            s.push_str("b");
            show(s.pop());
            show(s.pop());
            show(s.pop());
            let last = s.pop();
            show(s.pop());
            drop(-> s);
            show(last);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '🌍\naé€\nb\n€\né\n0\na\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy s=0', 'reclaim s'])

    def test_string_pop_rejects_live_views_and_wrong_patterns(self):
        for source, diagnostic in (
            ('let mut p = pool<String>(1); let s = p.new(); let r = s.pop();', 'immuable'),
            ('''let mut p = pool<String>(1); let mut s = p.new();
                let v = &s[..]; let r = s.pop(); print(v);''', 'emprunt actif'),
            ('''let mut p = pool<String>(1); let mut s = p.new();
                match s.pop() { Some(c) => { print(c); } }''', 'non exhaustif'),
            ('''let mut p = pool<String>(1); let mut s = p.new();
                match s.pop() { Ok(c) => { print(c); }, None => {} }''', 'types de résultat'),
            ('''let mut p = pool<String>(1); let mut s = p.new();
                match s.pop() { Ok(c) => { print(c); }, _ => {} }''', 'incompatible'),
            ('''match char::from_str("x") { Some(c) => { print(c); }, None => {} }''', 'incompatible'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_string_replacements_validate_before_writing(self):
        run = self.native('''
            fn byte_result(r: Result<u8, ByteReplaceError>) {
                match r {
                    Ok(old) => { let _old = old; print(10); },
                    Err(ByteReplaceError::OutOfBounds) => { print(11); },
                    Err(ByteReplaceError::InvalidUtf8) => { print(12); }
                }
            }
            fn block_result(r: Result<(), ByteReplaceError>) {
                match r {
                    Ok(()) => { print(20); },
                    Err(ByteReplaceError::OutOfBounds) => { print(21); },
                    Err(ByteReplaceError::InvalidUtf8) => { print(22); }
                }
            }
            let mut p = pool<String>(1);
            let mut s = p.new();
            s.push_str("é");
            byte_result(s.replace_byte(1, 0xaa));
            print(&s[..]);
            byte_result(s.replace_byte(0, 0x61));
            print(&s[..]);
            byte_result(s.replace_byte(2, 0x61));
            let pair: [u8; 2] = [0x61, 0x62];
            block_result(s.replace_bytes(0, &pair));
            print(&s[..]);
            let invalid: [u8; 2] = [0xed, 0xa0];
            block_result(s.replace_bytes(0, &invalid));
            block_result(s.replace_bytes(1, &pair));
            let empty: [u8; 0] = [];
            block_result(s.replace_bytes(2, &empty));
            print(&s[..]);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '10\nê\n12\nê\n11\n20\nab\n22\n21\n20\nab\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy s=0', 'reclaim s'])

    def test_string_replaces_bytes_from_borrowed_vector_slice(self):
        source = """
            fn patch(s: &mut String, bytes: &[u8], start: Int) -> Result<(), ByteReplaceError> {
                return s.replace_bytes(start, bytes);
            }
            fn status(r: Result<(), ByteReplaceError>) {
                match r {
                    Ok(()) => { print(0); },
                    Err(ByteReplaceError::OutOfBounds) => { print(1); },
                    Err(ByteReplaceError::InvalidUtf8) => { print(2); }
                }
            }
            let mut p = pool<Vector<u8>>(2);
            let mut strings = pool<String>(1);
            let mut first = p.new();
            first.push(0);
            let mut bytes = p.new();
            bytes.push(0xff);
            bytes.push(0x61);
            bytes.push(0x62);
            let mut s = strings.new();
            s.push_str("é!");
            address(s);
            status(patch(&mut s, &bytes[1..], 0));
            print(&s[..]);
            status(patch(&mut s, &bytes[..2], 0));
            print(&s[..]);
            status(patch(&mut s, &bytes[1..], 2));
            status(patch(&mut s, &bytes[3..], 3));
            address(s);
            print(&s[..]);
            bytes.push(0);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, ok, changed, invalid, kept, bounds, empty, after, final = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((ok, changed, invalid, kept, bounds, empty, final),
                         ('0', 'ab!', '2', 'ab!', '1', '0', 'ab!'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('status(patch(&mut s, &bytes[1..], 0));',
                                          'let view = &s[..]; status(patch(&mut s, &bytes[1..], 0)); print(view);'))

    def test_string_replacements_require_mutability_type_and_no_live_view(self):
        for source, diagnostic in (
            ('let s = p.new(); let r = s.replace_byte(0, 65);', 'immuable'),
            ('let mut s = p.new(); let r = s.replace_byte(0, 256);', 'entre 0 et 255'),
            ('let mut s = p.new(); let r = s.replace_byte("bad", 65);', 'indice Int'),
            ('let mut s = p.new(); let b = [1]; let r = s.replace_bytes(0, &b);', 'tableau u8'),
            ('let mut s = p.new(); let b: [u8; 1] = [65]; let r = s.replace_bytes(0, b);', 'affectation implicite'),
            ('let mut s = p.new(); let v = &s[..]; let r = s.replace_byte(0, 65); print(v);', 'emprunt actif'),
            ('''let mut s = p.new();
                match s.replace_byte(0, 65) { Ok(()) => {}, _ => {} }''', 'incompatible'),
            ('''let mut s = p.new(); let b: [u8; 1] = [65];
                match s.replace_bytes(0, &b) { Ok(old) => {}, _ => {} }''', 'extraction'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program('let mut p = pool<String>(1);' + source)

    def test_utf8_match_expression_handles_values_early_returns_and_subject_effects(self):
        run = self.native('''
            fn index(n: -> Int) -> Int { drop(-> n); print(8); return 0; }
            fn measure(r: Option<char>) -> Int {
                return match r {
                    Some(c) => { c.utf8_len() },
                    None => { return 0; }
                };
            }
            let mut p = pool<Int>(1);
            let n = p.new(10);
            let result = match "é".char_at(index(-> n)) {
                Ok(c) => { let reused = p.new(20); print(reused); c.utf8_len() },
                Err(CharAtError::OutOfBounds) => { 91 },
                Err(CharAtError::NotCharBoundary) => { 92 }
            };
            print(result);
            let mut strings = pool<String>(1);
            let mut s = strings.new();
            s.push_str("🌍");
            print(measure(s.pop()));
            print(measure(s.pop()));
            print(match "x".char_at(0) { _ => { 6 } });
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '8\n20\n2\n4\n0\n6\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy n=10', 'reclaim n', 'destroy reused=20',
                                                   'reclaim reused', 'destroy s=0', 'reclaim s'])

    def test_utf8_match_expression_preserves_view_provenances(self):
        source = '''
            fn choose(a: &String, b: &String) -> &str {
                let bytes: [u8; 1] = [0xff];
                let ok = str::from_utf8(&bytes);
                return match ok {
                    Ok(_) => { &a[..] },
                    Err(_) => { &b[..] }
                };
            }
            let mut p = pool<String>(2);
            let mut a = p.new();
            let mut b = p.new();
            a.push_str("first");
            b.push_str("second");
            let v = choose(&a, &b);
            EARLY
            print(v);
        '''
        for early in ('a.push_str("!");', 'b.push_str("!");'):
            with self.subTest(early=early), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('EARLY', early))
        run = self.native(source.replace('EARLY', '') + 'a.push_str("!"); b.push_str("!");')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'second\n')

    def test_utf8_match_expression_rejects_incompatible_or_escaping_results(self):
        for source, diagnostic in (
            ('''let v = match "x".char_at(0) {
                    Ok(c) => { c }, _ => { 0 }
                }; print(v);''', 'même type'),
            ('''let v = match "x".char_at(0) {
                    Ok(c) => { print(c); }, _ => { 0 }
                }; print(v);''', 'terminer par une valeur'),
            ('''let v = match "x".char_at(0) {
                    _ => {}
                }; print(v);''', 'fournir une valeur'),
            ('''fn make() -> [u8; 1] { return <- [65]; }
                let v = match str::from_utf8(&make()) {
                    Ok(text) => { text }, Err(_) => { "" }
                };
                print(v);''', 'non durable'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_utf8_match_expression_keeps_borrows_assigned_by_arms(self):
        source = '''
            let mut p = pool<String>(1);
            let mut s = p.new();
            s.push_str("abc");
            let mut v = "";
            let n = match "x".char_at(0) {
                Ok(_) => { v = &s[..]; 1 },
                _ => { v = &s[1..]; 2 }
            };
            print(n);
            EARLY
            print(v);
            s.push_str("!");
        '''
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('EARLY', 's.push_str("?");'))
        run = self.native(source.replace('EARLY', ''))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\nabc\n')

    def test_utf8_result_wildcard_error_preserves_declared_family(self):
        source = '''
            fn at(value: Result<char,CharAtError>) -> Int {
                return match value { Ok(ch) => { print(ch); 0 }, Err(_) => { 1 } };
            }
            fn from(value: Result<char,CharFromStrError>) -> Int {
                return match value { Ok(ch) => { print(ch); 0 }, Err(_) => { 2 } };
            }
            fn byte(value: Result<u8,ByteReplaceError>) -> Int {
                return match value { Ok(_) => { 0 }, Err(_) => { 3 } };
            }
            print(at("é".char_at(0))); print(at("é".char_at(1)));
            print(from(char::from_str("🌍"))); print(from(char::from_str("")));
            let mut p = pool<String>(1); let mut s = p.new(); s.push_str("é");
            print(byte(s.replace_byte(1,170))); print(byte(s.replace_byte(1,0)));
            print(&s[..]);
        '''
        result = self.native(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'é\n0\n1\n🌍\n0\n2\n0\n3\nê\n')
        with self.assertRaisesRegex(Error, 'attend Result<char,CharAtError>'):
            verify_program(source.replace('from(char::from_str("🌍"))', 'at(char::from_str("🌍"))'))
        with self.assertRaisesRegex(Error, 'type du résultat'):
            verify_program('''let mut p = pool<String>(1); let mut s = p.new();
                match s.pop() { Ok(_) => {}, Err(_) => {} }
            ''')

    def test_string_merge_consumes_source_and_reuses_its_pool_slot(self):
        run = self.native('''
            let mut first = pool<String>(1);
            let mut second = pool<String>(1);
            let mut destination = first.new();
            let mut source = second.new();
            destination.push_str("été");
            source.push_str("🌍");
            destination.merge(-> source);
            let fresh = second.new();
            print(&destination[..]);
            print(&fresh[..]);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'été🌍\n\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy source=0', 'reclaim source',
                                                   'destroy fresh=0', 'reclaim fresh',
                                                   'destroy destination=0', 'reclaim destination'])

    def test_string_merge_rejects_missing_move_alias_and_reuse(self):
        prefix = '''
            let mut p = pool<String>(2);
            let mut a = p.new();
            let b = p.new();
        '''
        for body, diagnostic in (
            ('a.merge(b);', 'transfert explicite'),
            ('a.merge(-> a);', 'emprunt'),
            ('let view = &b[..]; a.merge(-> b); print(view);', 'emprunt'),
            ('a.merge(-> b); print(&b[..]);', 'plus utilisable'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program(prefix + body)

    def test_vector_int_and_bytes_use_typed_pools_and_calls(self):
        run = self.native('''
            fn create(p: &mut Pool<Vector<Int>>) -> <- Vector<Int> {
                let mut v = p.new();
                v.push(10);
                return <- v;
            }
            fn show(v: &Vector<Int>, i: Int) {
                print(v.len());
                print(v[i]);
            }
            fn byte(b: u8) { print(7); }
            let mut p = pool<Vector<Int>>(2);
            let mut a: Vector<Int> = create(&mut p);
            a.push(20);
            let mut b = p.new();
            print(b.len());
            b.push(30);
            b.push(40);
            show(&a, 1);
            show(&b, 0);
            show(&b, 1);
            let mut bytes = pool<Vector<u8>>(1);
            let mut octets = bytes.new();
            octets.push(0xff);
            octets.push("é"[1]);
            byte(octets[0]);
            byte(octets[1]);
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '0\n2\n20\n2\n30\n2\n40\n7\n7\n')

    def test_vector_pop_matches_list_model_and_preserves_types(self):
        rng = random.Random(4201)
        lines = ["""
            fn take(v: &mut Vector<Int>) -> Option<Int> { return v.pop(); }
            fn take_byte(v: &mut Vector<u8>) -> Option<u8> { return v.pop(); }
            let mut p = pool<Vector<Int>>(2);
            let mut a = p.new();
            let mut b = p.new();
        """]
        expected = []
        for name in ('a', 'b'):
            model = []
            for _ in range(24):
                if rng.randrange(2):
                    value = rng.randint(-30, 30)
                    model.append(value)
                    lines.append(f'{name}.push({value});')
                else:
                    expected.append(model.pop() if model else 99)
                    lines.append(f'match take(&mut {name}) {{ Some(n) => {{ print(n); }}, None => {{ print(99); }} }}')
                expected.append(len(model))
                lines.append(f'print({name}.len());')
        lines.append("""
            let mut p8 = pool<Vector<u8>>(1);
            let mut octets = p8.new();
            octets.push(0xff);
            match take_byte(&mut octets) {
                Some(octet) => { octets.push(octet); },
                None => { print(0); }
            }
            print(octets.len());
        """)
        expected.append(1)
        run = self.native('\n'.join(lines))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines(), [str(value) for value in expected])

    def test_vector_pop_rejects_live_loans_and_invalid_matches(self):
        prefix = 'let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10);'
        for body, error in (
            ('let loan = &v; v.pop(); print(loan.len());', 'emprunt'),
            ('match v.pop() { Some(n) => { print(n); } }', 'non exhaustif'),
            ('match v.pop() { Ok(n) => { print(n); }, _ => {} }', 'incompatible'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_vector_replace_returns_old_or_incoming_after_evaluating_arguments(self):
        run = self.native("""
            fn mark(n: Int) -> Int { print(n); return n; }
            fn change(v: &mut Vector<Int>, i: Int, n: Int) -> Result<Int, Int> {
                return v.replace(mark(i), mark(n));
            }
            fn change_byte(v: &mut Vector<u8>, i: Int, n: u8) -> Result<u8, u8> {
                return v.replace(i, n);
            }
            let mut p = pool<Vector<Int>>(2);
            let mut a = p.new();
            let mut b = p.new();
            a.push(11);
            b.push(10);
            b.push(20);
            let old = match change(&mut b, 1, 30) {
                Ok(n) => { n },
                Err(_) => { 0 }
            };
            print(old);
            match change(&mut b, -1, 40) {
                Ok(_) => { print(0); },
                Err(n) => { print(n); }
            }
            match b.replace(2, 50) {
                Ok(_) => { print(0); },
                Err(n) => { print(n); }
            }
            print(b[0]);
            print(b[1]);
            print(b.len());
            print(a[0]);
            let mut bytes = pool<Vector<u8>>(1);
            let mut v = bytes.new();
            let input = "é"[1];
            match change_byte(&mut v, 0, input) {
                Ok(_) => { print(0); },
                Err(n) => { v.push(n); }
            }
            print(v.len());
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n30\n20\n-1\n40\n40\n50\n10\n30\n2\n11\n1\n')

    def test_vector_replace_rejects_conflicts_and_wrong_types(self):
        prefix = 'let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10);'
        for body, error in (
            ('v.replace(0, v[0]);', 'emprunt'),
            ('let view = &v; v.replace(0, 20); print(view.len());', 'emprunt'),
            ('v.replace(0, "x"[0]);', 'type des cases'),
            ('match v.replace(0, 20) { Some(n) => { print(n); }, None => {} }', 'incompatible'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_vector_remove_preserves_order_and_checks_exclusive_access(self):
        run = self.native("""
            fn take(v: &mut Vector<Int>, i: Int) -> Int {
                return v.remove(i);
            }
            fn byte(v: &mut Vector<u8>) -> u8 { return v.remove(0); }
            let mut p = pool<Vector<Int>>(2);
            let mut a = p.new();
            let mut b = p.new();
            a.push(11);
            b.push(10);
            b.push(20);
            b.push(30);
            print(take(&mut b, 1));
            b.push(40);
            print(b[0]);
            print(b[1]);
            print(b[2]);
            print(a[0]);
            let mut bytes = pool<Vector<u8>>(1);
            let mut v = bytes.new();
            v.push(0xc3);
            let x = byte(&mut v);
            v.push(x);
            print(v.len());
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '20\n10\n30\n40\n11\n1\n')

        prefix = 'let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10);'
        for index in (-1, 1):
            with self.subTest(index=index):
                run = self.native(prefix + f'print(v.remove({index}));')
                self.assertNotEqual(run.returncode, 0)
                self.assertIn('indice de Vector hors limites', run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program(prefix + 'let view = &v; print(v.remove(0)); print(view.len());')

    def test_vector_try_growth_returns_rejected_values_and_keeps_content(self):
        run = self.native("""
            fn push(v: &mut Vector<u8>, n: u8) -> Result<(), u8> {
                return v.try_push(n);
            }
            fn extend(v: &mut Vector<u8>, b: &[u8; 2]) -> Result<(), CapacityError> {
                return v.try_extend(b);
            }
            fn width(b: u8) -> Int {
                let mut p = pool<Vector<u8>>(1);
                let mut v = p.new();
                v.push(b);
                return v.len();
            }
            let mut p = pool<Vector<u8>>(1);
            #(directive, stack_region_max_size=1M) {
                let mut v = p.new();
                let mut i = 0;
                while i < 1048575 {
                    v.push(42);
                    i = i + 1;
                }
                let block: [u8; 2] = [1, 2];
                match extend(&mut v, &block) {
                    Ok(()) => { print(0); },
                    Err(CapacityError::CapacityExceeded) => { print(v.len()); }
                }
                match push(&mut v, "é"[0]) {
                    Ok(()) => { print(v.len()); },
                    Err(_) => { print(0); }
                }
                match push(&mut v, "x"[0]) {
                    Ok(()) => { print(0); },
                    Err(n) => { print(width(n)); }
                }
                print(v.len());
                let mut other = pool<Vector<u8>>(1);
                let mut copy = other.new();
                match copy.try_extend(&block) {
                    Ok(()) => { print(copy.len()); },
                    Err(CapacityError::CapacityExceeded) => { print(0); }
                }
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1048575\n1048576\n1\n1048576\n2\n')

    def test_vector_try_extend_accepts_scoped_byte_slice(self):
        prefix = """
            fn bound(n: Int) -> Int { print(n); return n; }
            let mut p = pool<Vector<u8>>(2);
            let mut dst = p.new();
            let mut src = p.new();
            src.push(5);
            src.push(6);
            src.push(7);
        """
        run = self.native(prefix + """
            match dst.try_extend(&src[bound(1)..bound(3)]) {
                Ok(()) => { print(dst.len()); },
                Err(CapacityError::CapacityExceeded) => { print(0); }
            }
            src.push(8);
            match dst.try_extend(&src[4..]) {
                Ok(()) => { print(dst.len()); },
                Err(CapacityError::CapacityExceeded) => { print(0); }
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n3\n2\n2\n')
        for bounds in ('-1..', '2..1', '0..4', '4..'):
            with self.subTest(bounds=bounds):
                run = self.native(prefix + f'match dst.try_extend(&src[{bounds}]) {{ _ => {{}} }}')
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertIn('bornes de tranche de Vector invalides', run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program(prefix + 'src.try_extend(&src[..]);')
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program('fn mutate(v: &mut Vector<u8>) -> Int { v.push(8); return 0; }'
                           + prefix + 'dst.try_extend(&src[mutate(&mut src)..]);')

    def test_named_byte_slice_holds_the_source_until_last_use(self):
        prefix = """
            let mut p = pool<Vector<u8>>(3);
            let mut src = p.new();
            let mut dst = p.new();
            src.push(10);
            src.push(20);
            let mut view: &[u8] = &src[1..];
        """
        use = 'match dst.try_extend(view) { Ok(()) => { print(dst.len()); }, _ => {} }'
        run = self.native(prefix + use + """
            src.push(30);
            view = &src[..];
            {
                let another = &src[..];
                view = another;
            }
        """ + use + 'drop(-> src);')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n4\n')
        for before, error in (
            ('src.push(30);', 'emprunt actif'),
            ('drop(-> src);', 'emprunt encore utilisé'),
            ('p.reset();', 'référence de tableau'),
            ('{ let child = p.new(); view = &child[..]; }', 'non durable'),
            ('let wrong: &str = view;', 'attendu &str'),
        ):
            with self.subTest(before=before), self.assertRaisesRegex(Error, error):
                verify_program(prefix + before + use)

    def test_byte_slice_contracts_track_multiple_sources_and_nested_calls(self):
        prefix = """
            fn cut(a: &Vector<u8>, b: &Vector<u8>, which: Int) -> &[u8] {
                if which == 0 { return &a[1..]; }
                return &b[..];
            }
            fn relay(v: &[u8]) -> &[u8] { return v; }
            fn append(dst: &mut Vector<u8>, v: &[u8]) {
                match dst.try_extend(v) { Ok(()) => { print(dst.len()); }, _ => {} }
            }
            let mut pa = pool<Vector<u8>>(1);
            let mut pb = pool<Vector<u8>>(1);
            let mut pd = pool<Vector<u8>>(1);
            let mut a = pa.new();
            let mut b = pb.new();
            let mut dst = pd.new();
            a.push(4);
            a.push(7);
            b.push(8);
            b.push(9);
        """
        use = 'append(&mut dst, v);'
        run = self.native(prefix + 'let v = relay(cut(&a, &b, 0));' + use + """
            a.push(5);
            append(&mut dst, relay(cut(&a, &b, 1)));
            match dst.try_extend(cut(&a, &b, 0)) { Ok(()) => { print(dst.len()); }, _ => {} }
            drop(-> a);
            drop(-> b);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n3\n5\n')
        for before, error in (
            ('a.push(5);', 'emprunt actif'),
            ('drop(-> b);', 'emprunt encore utilisé'),
            ('pb.reset();', 'référence de tableau'),
        ):
            with self.subTest(before=before), self.assertRaisesRegex(Error, error):
                verify_program(prefix + 'let v = relay(cut(&a, &b, 0));' + before + use)

    def test_byte_slice_contracts_reject_local_returns_and_aliasing_reset(self):
        for declaration in (
            """fn bad() -> &[u8] {
                let mut p = pool<Vector<u8>>(1);
                let a = p.new();
                return &a[..];
            }""",
            'fn bad(a: -> Vector<u8>) -> &[u8] { return &a[..]; }',
        ):
            with self.subTest(declaration=declaration), self.assertRaisesRegex(Error, 'non durable'):
                verify_program(declaration)
        prefix = """
            fn cut(a: &Vector<u8>) -> &[u8] { return &a[..]; }
            fn read_after_reset(v: &[u8], p: &mut Pool<Vector<u8>>, dst: &mut Vector<u8>) {
                p.reset();
                match dst.try_extend(v) { Ok(()) => { print(dst.len()); }, _ => {} }
            }
            let mut p = pool<Vector<u8>>(1);
            let mut q = pool<Vector<u8>>(1);
            let mut spare = pool<Vector<u8>>(1);
            let mut a = p.new();
            let mut b = q.new();
            a.push(1);
        """
        with self.assertRaisesRegex(Error, 'sources distinctes'):
            verify_program(prefix + 'read_after_reset(cut(&a), &mut p, &mut b);')
        run = self.native(prefix + 'read_after_reset(cut(&a), &mut spare, &mut b);')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n')

    def test_byte_slice_index_tracks_reference_but_copies_the_value(self):
        prefix = """
            fn read(v: &[u8], i: Int) -> u8 { return v[i]; }
            fn borrow(v: &[u8], i: Int) -> &u8 { return &v[i]; }
            fn cut(v: &Vector<u8>) -> &[u8] { return &v[1..2]; }
            fn reset_index(p: &mut Pool<Vector<u8>>) -> Int { p.reset(); return 0; }
            let mut p = pool<Vector<u8>>(1);
            let mut q = pool<Vector<u8>>(1);
            let mut src = p.new();
            let mut dst = q.new();
            src.push(10);
            src.push(20);
            src.push(30);
        """
        run = self.native(prefix + """
            let copied = read(cut(&src), 0);
            let ref = borrow(cut(&src), 0);
            dst.push(*ref);
            dst.push(cut(&src)[0]);
            drop(-> src);
            dst.push(copied);
            print(dst.len());
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '3\n')
        for index in (-1, 1):
            with self.subTest(index=index):
                run = self.native(prefix + f'dst.push(read(cut(&src), {index}));')
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertIn('indice de tranche de Vector hors limites', run.stderr)
        for body, error in (
            ('let r = borrow(cut(&src), 0); drop(-> src); dst.push(*r);', 'emprunt encore utilisé'),
            ('dst.push(cut(&src)[reset_index(&mut p)]);', 'reset interdit'),
            ('let v = cut(&src); let r = &mut v[0];', 'immuables'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_vector_slice_allows_reads_through_its_mutable_parent(self):
        source = """
            fn tail(v: &mut Vector<Int>) -> &[Int] { return &v[1..]; }
            fn measure(view: &[Int], length: Int) -> Int { return view[0] + length; }
            fn mutate(v: &mut Vector<Int>) -> Int { v.push(30); return v.len(); }
            fn read(v: &mut Vector<Int>) -> Int {
                let first = tail(v);
                let second = &v[..];
                BEFORE
                let result = first[0] + measure(second, v.len());
                v.push(30);
                return result;
            }
            let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
            print(read(&mut v));
            print(v.len());
        """
        valid = source.replace('BEFORE', '')
        run = self.native(valid)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '32\n3\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'v.push(30);'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('measure(second, v.len())', 'measure(second, mutate(v))'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('print(read(&mut v));', '''
                let first = tail(&mut v);
                print(v.len());
                print(first[0]);
            '''))

    def test_int_slice_reads_logical_cells_and_preserves_borrow_provenance(self):
        prefix = """
            fn cut(v: &Vector<Int>) -> &[Int] { return &v[1..]; }
            fn relay(v: &[Int]) -> &[Int] { return v; }
            fn read(v: &[Int], i: Int) -> Int { return v[i]; }
            fn get(v: &[Int]) -> &Int { return &v[0]; }
            let mut p = pool<Vector<Int>>(2);
            let mut left = p.new();
            let mut right = p.new();
            left.push(10);
            left.push(20);
            right.push(100);
            right.push(200);
            right.push(-300);
        """
        run = self.native(prefix + """
            let view: &[Int] = relay(cut(&right));
            let copied = read(view, 1);
            let cell = get(view);
            print(*cell);
            print(cut(&left)[0]);
            drop(-> right);
            print(copied);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '200\n20\n-300\n')

        run = self.native(prefix + 'print(read(cut(&right), 2));')
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn('indice de tranche de Vector hors limites', run.stderr)
        for body, error in (
            ('let v = cut(&right); right.push(400); print(v[0]);', 'emprunt actif'),
            ('let r = get(cut(&right)); drop(-> right); print(*r);', 'emprunt encore utilisé'),
            ('let v: &[u8] = cut(&right);', 'attendu'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_vector_push_new_initializes_and_reserves_the_case(self):
        prefix = """
            fn append(v: &mut Vector<Int>) -> &mut Int { return v.push_new(); }
            fn relay(v: &mut Vector<Int>) -> &mut Int { return append(v); }
            let mut p = pool<Vector<Int>>(2);
            let mut left = p.new();
            let mut right = p.new();
            left.push(77);
            right.push(42);
            let mut cell = relay(&mut right);
        """
        run = self.native(prefix + """
            print(*cell);
            *cell = 123;
            print(right[1]);
            let mut next = right.push_new();
            print(*next);
            *next = -500;
            print(right[0]);
            print(right[2]);
            print(left[0]);
            drop(-> right);
            let mut reused = p.new();
            let fresh = reused.push_new();
            print(*fresh);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '0\n123\n0\n42\n-500\n77\n0\n')
        for before, error in (
            ('right.push(1);', 'emprunt actif'),
            ('print(right[0]);', 'emprunt actif'),
            ('drop(-> right);', 'emprunt encore utilisé'),
            ('p.reset();', 'référence de tableau'),
        ):
            with self.subTest(before=before), self.assertRaisesRegex(Error, error):
                verify_program(prefix + before + 'print(*cell);')

    def test_vector_push_new_byte_initializes_and_keeps_adjacent_cases(self):
        prefix = """
            let mut p = pool<Vector<u8>>(2);
            let mut left = p.new();
            let mut right = p.new();
            left.push(76);
            right.push(65);
            let mut cell = right.push_new();
        """
        run = self.native(prefix + """
            let initial = *cell;
            *cell = 66;
            right.push(67);
            let bytes: [u8; 5] = [initial, left[0], right[0], right[1], right[2]];
            match str::from_utf8(&bytes) {
                Ok(text) => { print(text); },
                Err(_) => { print(0); }
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '\x00LABC\n')
        for body, error in (
            ('right.push(67); *cell = 66;', 'emprunt actif'),
            ('drop(-> right); *cell = 66;', 'emprunt encore utilisé'),
            ('*cell = 256;', 'entre 0 et 255'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_mutable_byte_signatures_preserve_cell_and_exclusivity(self):
        prefix = """
            fn append(v: &mut Vector<u8>) -> &mut u8 { return v.push_new(); }
            fn relay(b: &mut u8) -> &mut u8 { return b; }
            fn write(b: &mut u8) -> u8 { *b = 65; return *b; }
            fn pair(a: &mut u8, b: &mut u8) { *a = 66; *b = 67; }
            let mut p = pool<Vector<u8>>(1);
            let mut v = p.new();
            let mut cell = relay(append(&mut v));
        """
        run = self.native(prefix + """
            let byte = write(cell);
            let zero = *append(&mut v);
            let bytes: [u8; 3] = [v[0], byte, zero];
            drop(-> v);
            match str::from_utf8(&bytes) {
                Ok(text) => { print(text); },
                Err(_) => { print(0); }
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'AA\x00\n')
        for body, error in (
            ('pair(cell, cell);', 'emprunt'),
            ('drop(-> v); let b = write(cell);', 'emprunt'),
            ('p.reset(); let b = write(cell);', 'référence de tableau'),
            ('let b = write("A"[0]);', 'mode attendu'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_vector_push_new_checks_capacity_before_exposing_case(self):
        run = self.native("""
            let mut p = pool<Vector<Int>>(1);
            #(directive, stack_region_max_size=1M) {
                let mut v = p.new();
                let mut i = 0;
                while i < 262144 {
                    v.push(i);
                    i = i + 1;
                }
                let last = v.push_new();
                print(*last);
            }
        """)
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(run.stdout, '')
        self.assertEqual(run.stderr, 'capacité de Vector dépassée\n')

    def test_vector_split_mutable_halves_suspend_parent_until_both_end(self):
        prefix = """
            fn mark(i: Int) -> Int { print(i); return i; }
            fn reset_index(p: &mut Pool<Vector<Int>>) -> Int { p.reset(); return 0; }
            let mut p = pool<Vector<Int>>(2);
            let mut a = p.new();
            let mut v = p.new();
            a.push(99);
            v.push(10);
            v.push(20);
            v.push(30);
            let (mut left, mut right) = v.split_at_mut(mark(1));
        """
        run = self.native(prefix + """
            let mut l = &mut left[0];
            let mut r = &mut right[0];
            *l = 11;
            *r = 21;
            right[1] = 31;
            print(v[0]);
            print(v[1]);
            print(v[2]);
            print(a[0]);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n11\n21\n31\n99\n')
        for body, error in (
            ('left[0] = 11; print(v[0]); right[1] = 31;', 'emprunt actif'),
            ('right[1] = 31; v.push(99); left[0] = 11;', 'emprunt actif'),
            ('drop(-> v); print(right[0]);', 'emprunt encore utilisé'),
            ('p.reset(); print(left[0]);', 'référence de tableau'),
            ('left[0] = reset_index(&mut p);', 'allocation empruntée libérée|reset interdit'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_vector_split_pair_returns_through_modular_calls(self):
        source = """
            fn split(v: &mut Vector<Int>, i: Int) -> (&mut [Int], &mut [Int]) {
                return v.split_at_mut(i);
            }
            fn relay(v: &mut Vector<Int>, i: Int) -> (&mut [Int], &mut [Int]) {
                return split(v, i);
            }
            let mut p = pool<Vector<Int>>(1);
            let mut v = p.new();
            v.push(1); v.push(2);
            let (mut left, mut right) = relay(&mut v, 1);
            INSERT
            left[0] = 7;
            right[0] = 8;
            print(left[0]);
            print(right[0]);
            print(v[0]);
        """
        run = self.native(source.replace('INSERT', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n8\n7\n'), run.stderr)
        for statement, diagnostic in (('v.push(3);', 'emprunt actif'),
                                      ('p.reset();', 'référence de tableau|reset interdit')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('INSERT', statement))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn bad() -> (&mut [Int], &mut [Int]) {
                    let mut p = pool<Vector<Int>>(1);
                    let mut v = p.new();
                    return v.split_at_mut(0);
                }
            """)
        with self.assertRaisesRegex(Error, 'résultat de séparation'):
            verify_program('fn number() -> Int { return 1; } let (mut a, mut b) = number();')
        run = self.native("""
            fn split(v: &mut Vector<u8>) -> (&mut [u8], &mut [u8]) {
                return v.split_at_mut(1);
            }
            let mut p = pool<Vector<u8>>(1);
            let mut v = p.new();
            v.push(0x61); v.push(0x62);
            let (mut left, mut right) = split(&mut v);
            left[0] = 0x63;
            right[0] = 0x64;
            match str::from_utf8(&v[..]) { Ok(text) => { print(text); }, _ => {} }
        """)
        self.assertEqual((run.returncode, run.stdout), (0, 'cd\n'), run.stderr)

    def test_vector_split_pair_if_keeps_provenance_and_sibling_disjointness(self):
        source = """
            fn choose(a: &mut Vector<Int>, b: &mut Vector<Int>, flag: Int) -> (&mut [Int], &mut [Int]) {
                return if flag == 0 { a.split_at_mut(1) } else { b.split_at_mut(1) };
            }
            fn run(flag: Int) {
                let mut p = pool<Vector<Int>>(1);
                let mut q = pool<Vector<Int>>(1);
                let mut a = p.new();
                let mut b = q.new();
                a.push(1); a.push(2);
                b.push(3); b.push(4);
                let (mut left, mut right) = CHOICE;
                INSERT
                left[0] = 7;
                right[0] = 8;
                print(a[0]); print(a[1]);
                print(b[0]); print(b[1]);
            }
            run(0);
            run(1);
        """
        for choice in ('choose(&mut a, &mut b, flag)',
                       'if flag == 0 { a.split_at_mut(1) } else { b.split_at_mut(1) }'):
            with self.subTest(choice=choice):
                program = source.replace('CHOICE', choice)
                run = self.native(program.replace('INSERT', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '7\n8\n3\n4\n1\n2\n7\n8\n'), run.stderr)
                for pool in ('p', 'q'):
                    with self.assertRaisesRegex(Error, 'référence de tableau|reset interdit'):
                        verify_program(program.replace('INSERT', f'{pool}.reset();'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(source.replace('CHOICE', '''
                if flag == 0 {
                    let mut local = pool<Vector<Int>>(1);
                    let mut v = local.new();
                    v.split_at_mut(0)
                } else { b.split_at_mut(1) }
            ''').replace('INSERT', ''))

    def test_vector_split_pair_match_keeps_both_halves_of_selected_vector(self):
        source = """
            enum Side { Left, Right }
            fn choose(side: MODE, a: &mut Vector<Int>, b: &mut Vector<Int>) -> (&mut [Int], &mut [Int]) {
                return match SUBJECT {
                    Side.Left => { a.split_at_mut(1) },
                    Side.Right => { b.split_at_mut(1) }
                };
            }
            fn run(flag: Int) {
                let mut pool_side = pool<Side>(1);
                let mut side = if flag == 0 {
                    let s = new(pool_side) Side.Left {}; <- s
                } else {
                    let s = new(pool_side) Side.Right {}; <- s
                };
                let mut p = pool<Vector<Int>>(1);
                let mut q = pool<Vector<Int>>(1);
                let mut a = p.new();
                let mut b = q.new();
                a.push(1); a.push(2);
                b.push(3); b.push(4);
                let (mut left, mut right) = choose(ARG, &mut a, &mut b);
                CHECK
                left[0] = 7;
                right[0] = 8;
                print(a[0]); print(a[1]);
                print(b[0]); print(b[1]);
            }
            run(0);
            run(1);
        """
        for mode, subject, arg in (('-> Side', '(-> side)', '-> side'),
                                    ('&Side', '&side', '&side'),
                                    ('&mut Side', '&mut side', '&mut side')):
            with self.subTest(mode=mode):
                program = source.replace('MODE', mode).replace('SUBJECT', subject).replace('ARG', arg)
                run = self.native(program.replace('CHECK', ''))
                self.assertEqual((run.returncode, run.stdout), (0, '7\n8\n3\n4\n1\n2\n7\n8\n'), run.stderr)
                with self.assertRaisesRegex(Error, 'référence de tableau|reset interdit'):
                    verify_program(program.replace('CHECK', 'q.reset();'))

    def test_vector_split_pair_can_leave_block_only_with_durable_storage(self):
        source = """
            fn split(v: &mut Vector<Int>, i: Int) -> (&mut [Int], &mut [Int]) {
                return { let index = i; v.split_at_mut(index) };
            }
            let mut p = pool<Vector<Int>>(1);
            let mut v = p.new();
            v.push(1); v.push(2);
            let (mut left, mut right) = { let i = 1; split(&mut v, i) };
            INSERT
            left[0] = 7;
            right[0] = 8;
            print(v[0]);
            print(v[1]);
        """
        run = self.native(source.replace('INSERT', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n8\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('INSERT', 'v.push(3);'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                let (mut left, mut right) = {
                let mut local = pool<Vector<Int>>(1);
                let mut tmp = local.new();
                tmp.split_at_mut(0)
                };
            """)
        with self.assertRaisesRegex(Error, 'liaison à deux noms'):
            verify_program(source.replace('let (mut left, mut right) = { let i = 1; split(&mut v, i) };',
                                          'v.split_at_mut(1);').replace('INSERT', ''))

    def test_vector_split_pair_break_keeps_storage_across_loop_exit(self):
        source = """
            fn run(flag: Int) {
                let mut p = pool<Vector<Int>>(1);
                let mut q = pool<Vector<Int>>(1);
                let mut a = p.new();
                let mut b = q.new();
                a.push(1); a.push(2);
                b.push(3); b.push(4);
                let mut count = 0;
                let (mut left, mut right) = loop {
                    if count == 0 {
                        let (mut head, mut tail) = a.split_at_mut(1);
                        head[0] = 5;
                        tail[0] = 6;
                        count = 1;
                        continue;
                    }
                    if flag == 0 { break a.split_at_mut(1); }
                    break b.split_at_mut(1);
                };
                INSERT
                left[0] = 7;
                right[0] = 8;
                print(a[0]); print(a[1]);
                print(b[0]); print(b[1]);
            }
            run(0);
            run(1);
        """
        run = self.native(source.replace('INSERT', ''))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n8\n3\n4\n5\n6\n7\n8\n'), run.stderr)
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'référence de tableau|reset interdit'):
                verify_program(source.replace('INSERT', f'{pool}.reset();'))
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(source.replace('break b.split_at_mut(1);', 'break 0;').replace('INSERT', ''))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(source.replace('break b.split_at_mut(1);', '''
                let mut temporary = q.new();
                break temporary.split_at_mut(0);
            ''').replace('INSERT', ''))

    def test_vector_subsplit_keeps_disjoint_siblings_and_suspends_its_parent(self):
        source = """
            let mut p = pool<Vector<Int>>(2);
            let mut first = p.new();
            first.push(99);
            let mut v = p.new();
            v.push(10);
            v.push(20);
            v.push(30);
            let (mut left, mut right) = v.split_at_mut(2);
            let (mut head, mut tail) = left.split_at_mut(INDEX);
            INSERT
            head[0] = 11;
            right[0] = 31;
            tail[0] = 21;
            print(head[0]);
            print(tail[0]);
            print(right[0]);
            print(left[0]);
            print(v[1]);
            print(first[0]);
        """
        valid = source.replace('INSERT', '').replace('INDEX', '1')
        run = self.native(valid)
        self.assertEqual((run.returncode, run.stdout), (0, '11\n21\n31\n11\n21\n99\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('INSERT', 'left[0] = 90;').replace('INDEX', '1'))
        with self.assertRaisesRegex(Error, 'référence de tableau|reset interdit'):
            verify_program(source.replace('INSERT', 'p.reset();').replace('INDEX', '1'))
        outside = self.native(source.replace('INSERT', '').replace('INDEX', '3'))
        self.assertEqual(outside.returncode, 1, outside.stderr)
        self.assertIn('bornes de tranche de Vector invalides', outside.stderr)
        returned = """
            fn last(view: &mut [Int]) -> &mut [Int] {
                let (mut head, mut tail) = view.split_at_mut(1);
                return tail;
            }
            let mut p = pool<Vector<Int>>(1);
            let mut v = p.new();
            v.push(1); v.push(2); v.push(3);
            let (mut left, mut right) = v.split_at_mut(1);
            let mut tail = last(right);
            left[0] = 8;
            tail[0] = 9;
            print(v[0]);
            print(v[2]);
        """
        run = self.native(returned)
        self.assertEqual((run.returncode, run.stdout), (0, '8\n9\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(returned.replace('left[0] = 8;', 'right[0] = 8;'))

    def test_shared_reborrow_of_split_byte_slice_suspends_only_its_half(self):
        source = """
            fn decode(v: &mut [u8]) -> Result<&str, Utf8Error> { return str::from_utf8(&*v); }
            let mut p = pool<Vector<u8>>(1);
            let mut v = p.new();
            v.push(0xc3);
            v.push(0xa9);
            v.push(0x61);
            let (mut left, mut right) = v.split_at_mut(2);
            match decode(left) {
                Ok(text) => { right[0] = 0x62; print(text); },
                Err(_) => { print(0); }
            }
            let child = &mut *left;
            child[0] = 0x41;
            print(v.len());
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, 'é\n3\n'), run.stderr)
        for invalid in ('left[0] = 0x62;', 'v.push(0x62);'):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('right[0] = 0x62;', invalid))

    def test_shared_reborrow_of_split_int_slice_preserves_range(self):
        source = """
            fn read(v: &[Int]) -> Int { return v[0]; }
            fn relay(v: &[Int]) -> &[Int] { let again = &*v; return &again[1..]; }
            let mut p = pool<Vector<Int>>(2);
            let mut first = p.new();
            first.push(99);
            let mut v = p.new();
            v.push(7);
            v.push(8);
            v.push(11);
            let (mut left, mut right) = v.split_at_mut(1);
            let shared = &*right;
            let relayed = relay(&*shared);
            left[0] = 9;
            print(read(relayed));
            right[0] = 10;
            print(v[0]);
            print(v[1]);
            print(v[2]);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '11\n9\n10\n11\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('left[0] = 9;', 'right[0] = 9;'))
        with self.assertRaisesRegex(Error, 'emprunté en lecture'):
            verify_program(source.replace('relay(&*shared)', 'relay(&mut *shared)'))
        failed = self.native(source.replace('&again[1..]', '&again[3..]'))
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn('bornes de tranche de Vector invalides', failed.stderr)

    def test_vector_split_byte_halves_can_be_written_inside_function(self):
        run = self.native("""
            fn edit(v: &mut Vector<u8>, middle: Int) {
                let (mut left, mut right) = v.split_at_mut(middle);
                left[0] = 65;
                right[0] = 66;
            }
            let mut p = pool<Vector<u8>>(1);
            let mut v = p.new();
            v.push(0);
            v.push(0);
            edit(&mut v, 1);
            let bytes: [u8; 2] = [v[0], v[1]];
            match str::from_utf8(&bytes) {
                Ok(text) => { print(text); },
                Err(_) => { print(0); }
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'AB\n')

    def test_mutable_slice_calls_preserve_disjointness_and_parent_reservation(self):
        prefix = """
            fn set_both(l: &mut [Int], r: &mut [Int]) { l[0] = 10; r[0] = 20; }
            fn relay(v: &mut [Int]) -> &mut [Int] { return v; }
            let mut p = pool<Vector<Int>>(1);
            let mut v = p.new();
            v.push(1);
            v.push(2);
            let (mut left, mut right) = v.split_at_mut(1);
        """
        run = self.native(prefix + """
            let returned = relay(left);
            set_both(returned, relay(right));
            print(v[0]);
            print(v[1]);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '10\n20\n')
        for body, error in (
            ('set_both(left, left);', 'emprunt actif'),
            ('let returned = relay(left); left[0] = 99; print(returned[0]);', 'emprunt actif'),
            ('let returned = relay(left); print(v[0]); print(returned[0]);', 'emprunt actif'),
            ('let copy = left;', 'se réemprunte'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_mutable_byte_slice_can_return_one_half_of_borrowed_vector(self):
        run = self.native("""
            fn right(v: &mut Vector<u8>) -> &mut [u8] {
                let (mut l, mut r) = v.split_at_mut(1);
                return r;
            }
            fn write(v: &mut [u8]) { v[0] = 66; }
            let mut p = pool<Vector<u8>>(1);
            let mut v = p.new();
            v.push(65);
            v.push(0);
            write(right(&mut v));
            let bytes: [u8; 2] = [v[0], v[1]];
            match str::from_utf8(&bytes) {
                Ok(text) => { print(text); },
                Err(_) => { print(0); }
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'AB\n')
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn invalid(v: -> Vector<u8>) -> &mut [u8] {
                    let (mut l, mut r) = v.split_at_mut(0);
                    return r;
                }
            """)

    def test_explicit_allocation_annotation_keeps_address_and_origin_pool(self):
        run = self.native("""
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut handle: A<Int> = p.new(10);
            let other: A<Int> = q.new(20);
            address(handle);
            address(other);
            handle = <- other;
            address(handle);
            let reuse: A<Int> = p.new(30);
            address(reuse);
            print(*handle);
            drop(-> handle);
            let again: A<Int> = q.new(40);
            address(again);
            print(*again);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        old, incoming, moved, reused, value, again, second_value = run.stdout.splitlines()
        self.assertEqual((old, incoming, incoming), (reused, moved, again))
        self.assertNotEqual(old, incoming)
        self.assertEqual((value, second_value), ('20', '40'))
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(len(destroyed), 4)

    def test_explicit_allocation_annotation_rejects_other_storage_and_types(self):
        for body in (
            'let a: A<Int> = 4;',
            'let mut p = pool<String>(1); let a: A<Int> = p.new();',
            'let mut s = stack(4096); let a: A<Int> = new(s) Int(4);',
            """let mut p = pool<Int>(1); let mut s = stack(4096);
                let mut a: A<Int> = p.new(1);
                let b = new(s) Int(2); a = <- b; print(*a);""",
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, 'allocation de Pool<Int>'):
                verify_program(body)

    def test_allocation_value_borrows_read_and_mutate_without_moving(self):
        run = self.native("""
            fn read(value: &Int) -> Int { return *value; }
            fn write(value: &mut Int) { *value = 20; }
            fn prepare(p: &mut Pool<Int>) -> <- Int {
                let mut a: A<Int> = p.new(4);
                address(a);
                write(a.mut_vref());
                print(read(a.vref()));
                return <- a;
            }
            let mut p = pool<Int>(1);
            let a: A<Int> = prepare(&mut p);
            address(a);
            print(*a);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, read, after, copied = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((read, copied), ('20', '20'))
        self.assertEqual(run.stderr.splitlines(), ['destroy a=20', 'reclaim a'])

    def test_allocation_value_borrows_reject_conflicts(self):
        prefix = 'let mut p = pool<Int>(1); let mut a: A<Int> = p.new(4);'
        for body, error in (
            ('let v = a.vref(); let mut w = a.mut_vref(); print(*v); print(*w);', 'emprunt actif'),
            ('let v = a.vref(); drop(-> a); print(*v);', 'emprunt encore utilisé'),
            ('let v = a.vref(); p.reset(); print(*v);', 'reset interdit'),
            ('let b = a.mut_vref(1); print(*b);', 'aucun argument'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)
        with self.assertRaisesRegex(Error, 'immuable'):
            verify_program(prefix.replace('let mut a', 'let a') + 'let v = a.mut_vref(); print(*v);')

    def test_handle_borrows_and_vequals_compare_contents_across_pools(self):
        run = self.native("""
            fn compare(p: &mut Pool<Int>, q: &mut Pool<Int>) -> bool {
                let a: A<Int> = p.new(7);
                let mut b: A<Int> = q.new(7);
                let h = b.ref();
                let same = a.vequals(h);
                b = 8;
                let exclusive = b.mut_ref();
                if a.vequals(exclusive) { return false; }
                return same;
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            if compare(&mut p, &mut q) { print(1); } else { print(0); }
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n')

    def test_row_projection_contract_protects_targets_during_index_effects(self):
        source = """
            fn index(memory: &mut Pool<Int>) -> Int {
                memory.reset();
                return 0;
            }
            fn get(rows: &[&[&Int; 1]; 1], memory: &mut Pool<Int>) -> &[&Int; 1] {
                return rows[index(memory)];
            }
            let mut values = pool<Int>(1);
            let value = values.new(7);
            let mut other = pool<Int>(1);
            let row = [&value];
            let rows = [&row];
            let view = get(&rows, &mut TARGET);
            print(*view[0]);
        """
        contained = (source.replace('rows: &[&[&Int; 1]; 1]', 'rows: [[&Int; 1]; 1]')
                     .replace('-> &[&Int; 1]', '-> [&Int; 1]')
                     .replace('return rows[index(memory)];', 'return <- copy(rows[index(memory)]);')
                     .replace('let rows = [&row];', 'let rows = [copy(row)];')
                     .replace('get(&rows,', 'get(copy(rows),'))
        for case in (source, contained):
            run = self.native(case.replace('TARGET', 'other'))
            self.assertEqual((run.returncode, run.stdout), (0, '7\n'), run.stderr)
            with self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
                verify_program(case.replace('TARGET', 'values'))

    def test_reference_array_literal_contract_protects_earlier_elements(self):
        source = """
            fn next(data: &Int, memory: &mut Pool<Int>) -> &Int {
                memory.reset();
                return data;
            }
            fn build(first: &Int, second: &Int, memory: &mut Pool<Int>) -> [&Int; 2] {
                return <- [first, next(second, memory)];
            }
            let mut first = pool<Int>(1);
            let a = first.new(7);
            let mut second = pool<Int>(1);
            let b = second.new(9);
            let mut other = pool<Int>(1);
            let array = build(&a, &b, &mut TARGET);
            print(*array[0]);
            print(*array[1]);
        """
        run = self.native(source.replace('TARGET', 'other'))
        self.assertEqual((run.returncode, run.stdout), (0, '7\n9\n'), run.stderr)
        for pool in ('first', 'second'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'contrainte de sources distinctes'):
                verify_program(source.replace('TARGET', pool))

    def test_vequals_contract_keeps_receiver_live_through_argument_effects(self):
        source = """
            fn next(b: &A<Int>, memory: &mut Pool<Int>) -> &A<Int> {
                memory.reset();
                return b;
            }
            fn compare(a: -> A<Int>, b: &A<Int>, memory: &mut Pool<Int>) -> bool {
                return a.vequals(next(b, memory));
            }
            let mut first = pool<Int>(1);
            let a = first.new(7);
            let mut second = pool<Int>(1);
            let b = second.new(7);
            let mut other = pool<Int>(1);
            if compare(-> a, b.ref(), &mut TARGET) { print(1); }
        """
        run = self.native(source.replace('TARGET', 'other'))
        self.assertEqual((run.returncode, run.stdout), (0, '1\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
        self.assertEqual(run.stderr.count('destroy b=7\n'), 1)
        for pool in ('first', 'second'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('TARGET', pool))

    def test_handle_borrows_are_distinct_from_content_and_protect_replacement(self):
        prefix = """
            fn read(x: &Int) -> Int { return *x; }
            let mut p = pool<Int>(3);
            let mut a: A<Int> = p.new(7);
            let mut b: A<Int> = p.new(8);
        """
        for body, error in (
            ('if a.vequals(b.vref()) { print(1); }', 'emprunt du handle'),
            ('print(read(b.ref()));', 'mode attendu ref'),
            ('let h = b.ref(); drop(-> b); if a.vequals(h) { print(1); }', 'emprunt encore utilisé'),
            ('let h = b.ref(); let c = p.new(9); b = <- c; if a.vequals(h) { print(1); }', 'emprunt actif'),
            ('let h = b.mut_ref(); print(*b); if a.vequals(h) { print(1); }', 'emprunt actif'),
            ('let equal: bool = a.vequals(b.ref()); print(equal + 1);', 'deux valeurs Int'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + "print(*a); print(*b);" + body)

    def test_mutable_handle_replacement_keeps_new_origin_and_orders_cleanup(self):
        run = self.native("""
            fn value() -> Int {
                let mut temps = pool<Int>(1);
                let marker = temps.new(9);
                return *marker;
            }
            fn swap(p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- Int {
                let mut a: A<Int> = p.new(1);
                let h = a.mut_ref();
                *h = <- q.new(value());
                let witness = p.new(9);
                if witness.vequals(h) { print(1); }
                return <- a;
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a: A<Int> = swap(&mut p, &mut q);
            p.reset();
            print(*a);
            drop(-> a);
            let reused = q.new(10);
            print(*reused);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n9\n10\n')
        self.assertEqual(run.stderr.splitlines()[:4], ['destroy marker=9', 'reclaim marker',
                                                      'destroy a=1', 'reclaim a'])

    def test_mutable_handle_reborrow_replaces_and_updates_its_parent(self):
        source = """
            fn swap(p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- A<Int> {
                let mut a: A<Int> = p.new(1);
                let h = a.mut_ref();
                let child = &mut *h;
                *child = <- q.new(2);
                let witness = p.new(2);
                if witness.vequals(h) { print(1); }
                return <- a;
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = swap(&mut p, &mut q);
            p.reset();
            print(*a);
            drop(-> a);
            let reused = q.new(3);
            print(*reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n2\n3\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('return <- a;', '*child = <- q.new(3); return <- a;'))
        with self.assertRaisesRegex(Error, 'référence de tableau|reset interdit'):
            verify_program(source.replace('if witness.vequals(h)', 'q.reset(); if witness.vequals(h)'))

    def test_mutable_handle_parameter_replacement_through_relay(self):
        source = """
            fn swap(h: &mut A<Int>, b: -> A<Int>) { *h = <- b; }
            fn relay(h: &mut A<Int>, b: -> A<Int>) { swap(h, -> b); }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a: A<Int> = p.new(1);
            let h = a.mut_ref();
            {
                let b = q.new(2);
                address(b);
                relay(h, -> b);
            }
            p.reset();
            print(*a);
            address(a);
            drop(-> a);
            let reused = q.new(3);
            print(*reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, value, after, reused = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((value, reused), ('2', '3'))
        self.assertEqual(run.stderr.splitlines()[:5],
                         ['destroy a=1', 'reclaim a', 'reset', 'destroy b=2', 'reclaim b'])
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('p.reset()', 'q.reset()'))
        with self.assertRaisesRegex(Error, 'doit survivre au handle injecté'):
            verify_program(source.split('let mut p =')[0] + """
                let mut p = pool<Int>(1);
                let mut a = p.new(1);
                {
                    let mut q = pool<Int>(1);
                    let b = q.new(2);
                    relay(a.mut_ref(), -> b);
                }
                print(*a);
            """)

    def test_conditional_mutable_handle_parameter_retains_old_pool(self):
        source = """
            fn swap(h: &mut A<Int>, q: &mut Pool<Int>, flag: Int) {
                if flag == 0 { return; }
                let child = &mut *h;
                *child = <- q.new(2);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a: A<Int> = p.new(1);
            swap(a.mut_ref(), &mut q, FLAG);
            print(*a);
        """
        for flag, expected in ((0, '1\n'), (1, '2\n')):
            with self.subTest(flag=flag):
                run = self.native(source.replace('FLAG', str(flag)))
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('FLAG', '1').replace('print(*a);', 'p.reset(); print(*a);'))

    def test_typed_mutable_handle_parameter_replacement(self):
        cases = (
            ('Point', 'struct Point { x: Int }',
             'let mut a = p.new(x: 1); let b = q.new(x: 2);',
             'print(a.x);', '2\n'),
            ('Choice', 'enum Choice { A, B { value: Int } }',
             'let mut a = new(p) Choice.A; let b = new(q) Choice.B { value: 7 };',
             'match &a { Choice.A => {}, Choice.B { value: v } => { print(v); } }', '7\n'),
            ('String', '',
             'let mut a = p.new(); let mut b = q.new(); b.push_str("é");',
             'a.push_str("té"); print(&a[..]);', 'été\n'),
            ('Vector<Int>', '',
             'let mut a = p.new(); let mut b = q.new(); b.push(4);',
             'a.push(9); print(a[0]); print(a[1]);', '4\n9\n'),
            ('Vector<u8>', '',
             'let mut a = p.new(); let mut b = q.new(); b.push(0x41);',
             'a.push(0x42); print(a.len());', '2\n'),
        )
        for typ, declaration, create, observe, expected in cases:
            with self.subTest(typ=typ):
                source = f"""
                    {declaration}
                    fn swap(h: &mut A<{typ}>, b: -> A<{typ}>) {{ *h = <- b; }}
                    fn relay(h: &mut A<{typ}>, b: -> A<{typ}>) {{ swap(h, -> b); }}
                    let mut p = pool<{typ}>(1);
                    let mut q = pool<{typ}>(1);
                    {create}
                    address(b);
                    relay(a.mut_ref(), -> b);
                    p.reset();
                    address(a);
                    {observe}
                """
                run = self.native(source)
                self.assertEqual(run.returncode, 0, run.stderr)
                before, after, *output = run.stdout.splitlines(keepends=True)
                self.assertEqual(before, after)
                self.assertEqual(''.join(output), expected)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(source.replace('p.reset()', 'q.reset()'))

    def test_conditional_typed_handle_replacement_after_control_flow_join(self):
        source = """
            enum Choice { A, B { n: Int } }
            fn swap(h: &mut A<Choice>, q: &mut Pool<Choice>, flag: Int) {
                if flag == 0 { return; }
                let b = new(q) Choice.B { n: 42 };
                *h = <- b;
            }
            let mut p = pool<Choice>(1);
            let mut q = pool<Choice>(1);
            let mut a = new(p) Choice.A;
            swap(a.mut_ref(), &mut q, FLAG);
            match &a { Choice.A => {}, Choice.B { n: n } => { print(n); } }
        """
        for flag, expected in ((0, ''), (1, '42\n')):
            with self.subTest(flag=flag):
                run = self.native(source.replace('FLAG', str(flag)))
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected)

    def test_handle_replacement_call_updates_cleanup_across_branch_join(self):
        source = """
            fn swap(h: &mut A<Int>, q: &mut Pool<Int>) RESULT {
                *h = <- q.new(2);
                RETURN
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a = p.new(1);
            if FLAG == 1 { CALL }
            print(*a);
        """
        for returns_value in (False, True):
            for flag in (0, 1):
                with self.subTest(returns_value=returns_value, flag=flag):
                    program = (source.replace('RESULT', '-> Int' if returns_value else '')
                               .replace('RETURN', 'return 7;' if returns_value else '')
                               .replace('CALL', 'let n = swap(a.mut_ref(), &mut q); print(n);'
                                        if returns_value else 'swap(a.mut_ref(), &mut q);')
                               .replace('FLAG', str(flag)))
                    run = self.native(program)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    expected = ('7\n' if returns_value and flag else '') + f'{1 + flag}\n'
                    self.assertEqual(run.stdout, expected)
                    destroyed = [line.rsplit('=', 1)[-1] for line in run.stderr.splitlines()
                                 if line.startswith('destroy ')]
                    self.assertEqual(destroyed, ['1', '2'] if flag else ['1'])
        incompatible_order = (source.replace('RESULT', '').replace('RETURN', '')
                              .replace('CALL', 'swap(a.mut_ref(), &mut q);').replace('FLAG', '1')
                              .replace('if 1 == 1', 'let other = p.new(3); print(*other); if 1 == 1')
                              .replace('pool<Int>(1)', 'pool<Int>(2)'))
        with self.assertRaisesRegex(Error, 'ordre de réception différent'):
            verify_program(incompatible_order)

    def test_handle_replacement_across_continue_break_and_function_return(self):
        source = """
            fn swap(h: &mut A<Int>, b: -> A<Int>) { *h = <- b; }
            fn repeat(p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- A<Int> {
                let mut a = p.new(0);
                let h = a.mut_ref();
                let mut i = 0;
                loop {
                    if i == 3 { break; }
                    let b = if i == 1 { let x = p.new(i + 1); <- x }
                            else { let x = q.new(i + 1); <- x };
                    swap(h, -> b);
                    i = i + 1;
                    continue;
                }
                return <- a;
            }
            let mut p = pool<Int>(2);
            let mut q = pool<Int>(1);
            let a = repeat(&mut p, &mut q);
            print(*a);
            drop(-> a);
            let reused = q.new(4);
            print(*reused);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '3\n4\n'), run.stderr)
        self.assertEqual([line.rsplit('=', 1)[-1] for line in run.stderr.splitlines()
                          if line.startswith('destroy ')], ['0', '1', '2', '3', '4'])
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('print(*a);', f'{pool}.reset(); print(*a);'))

    def test_handle_replacement_cannot_restore_a_different_imported_object(self):
        prefix = """
            fn swap(h: &mut A<Int>, q: &mut Pool<Int>) { *h = <- q.new(2); }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a = p.new(1);
        """
        replacement_without_receiver = prefix + '{ -> a; swap(a.mut_ref(), &mut q); <- a; }'
        checked = verify_program(replacement_without_receiver)
        self.assertTrue(any('transfert sans receveur' in warning for warning in checked.warnings))
        for compile_check in (verify_program, compile_source):
            with self.subTest(check=compile_check.__name__):
                with self.assertRaisesRegex(Error, 'plus utilisable'):
                    compile_check(replacement_without_receiver + 'print(*a);')
                with self.assertRaisesRegex(Error, 'transfert déjà marqué'):
                    compile_check(prefix + '{ -> a; <- a; swap(a.mut_ref(), &mut q); } print(*a);')
        run = self.native(prefix + 'swap(a.mut_ref(), &mut q); { -> a; <- a; } print(*a);')
        self.assertEqual((run.returncode, run.stdout), (0, '2\n'), run.stderr)
        run = self.native(prefix + 'let b = { -> a; swap(a.mut_ref(), &mut q); <- a }; print(*b);')
        self.assertEqual((run.returncode, run.stdout), (0, '2\n'), run.stderr)

    def test_mutable_handle_replacement_from_child_updates_ancestor_cleanup(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a = p.new(1);
            let h = a.mut_ref();
            {
                let b = q.new(2);
                address(b);
                let child = &mut *h;
                *child = <- b;
            }
            p.reset();
            address(a);
            print(*a);
            drop(-> a);
            let reused = q.new(3);
            address(reused);
            print(*reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, value, reused, reused_value = run.stdout.splitlines()
        self.assertEqual((before, after), (reused, reused))
        self.assertEqual((value, reused_value), ('2', '3'))
        with self.assertRaisesRegex(Error, 'doit survivre au receveur'):
            verify_program(source.replace('let mut q = pool<Int>(1);', '')
                           .replace('let b = q.new(2);', 'let mut q = pool<Int>(1); let b = q.new(2);'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('p.reset();', 'q.reset();'))
        conditional = (source.split('p.reset();')[0].replace('\n            {', '\n            if FLAG == 1 {')
                       .replace('address(b);', '') + 'print(*a);')
        for flag, expected in ((0, '1\n'), (1, '2\n')):
            with self.subTest(flag=flag):
                run = self.native(conditional.replace('FLAG', str(flag)))
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(conditional.replace('FLAG', '1').replace('print(*a);', 'p.reset(); print(*a);'))

    def test_mutable_handle_replacement_transfers_stored_borrows(self):
        prefix = """
            struct View { target: &Int }
            fn swap(h: &mut A<View>, b: -> A<View>) { *h = <- b; }
            fn relay(h: &mut A<View>, b: -> A<View>) { swap(h, -> b); }
            let mut p = pool<View>(1);
            let mut q = pool<View>(1);
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let old = first.new(4);
            let mut a = p.new(target: &old);
        """
        source = prefix + """
            let next = second.new(9);
            let b = q.new(target: &next);
            relay(a.mut_ref(), -> b);
            first.reset();
            print(a);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, 'View(9)\n'), run.stderr)
        for invalid in ('second.reset();', 'drop(-> next);'):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(Error, 'reset interdit|emprunt'):
                verify_program(source.replace('first.reset();', invalid))
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(prefix + """
                {
                    let next = second.new(9);
                    let b = q.new(target: &next);
                    relay(a.mut_ref(), -> b);
                }
                print(a);
            """)
        exclusive = (source.replace('target: &Int', 'target: &mut Int')
                     .replace('let old =', 'let mut old =').replace('let next =', 'let mut next =')
                     .replace('target: &old', 'target: &mut old').replace('target: &next', 'target: &mut next')
                     .replace('first.reset();', 'old = 5; print(*old);'))
        run = self.native(exclusive + 'drop(-> a); next = 10; print(*next);')
        self.assertEqual((run.returncode, run.stdout), (0, '5\nView(9)\n10\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(exclusive.replace('print(a);', 'next = 10; print(a);'))

    def test_handle_replacement_infers_fields_created_or_changed_in_callee(self):
        for replacement in ('fresh', 'updated'):
            with self.subTest(replacement=replacement):
                argument = 'q: &mut Pool<View>' if replacement == 'fresh' else 'mut b: -> A<View>'
                relay_argument = 'q' if replacement == 'fresh' else '-> b'
                body = ('let b = q.new(target: &mut *next);' if replacement == 'fresh'
                        else 'b.target = &mut *next;')
                prepare = '' if replacement == 'fresh' else 'let b = q.new(target: &mut spare);'
                actual = '&mut q' if replacement == 'fresh' else '-> b'
                source = f"""
                    struct View {{ target: &mut Int }}
                    fn put(h: &mut A<View>, {argument}, next: &mut Int) {{
                        {body}
                        *h = <- b;
                    }}
                    fn relay(h: &mut A<View>, {argument}, next: &mut Int) {{
                        put(h, {relay_argument}, next);
                    }}
                    let mut p = pool<View>(1);
                    let mut q = pool<View>(1);
                    let mut ints = pool<Int>(3);
                    let mut old = ints.new(4);
                    let mut next = ints.new(9);
                    let mut spare = ints.new(0);
                    let mut a = p.new(target: &mut old);
                    {prepare}
                    relay(a.mut_ref(), {actual}, &mut next);
                    old = 5;
                    spare = 6;
                    print(*old);
                    print(*spare);
                    print(a);
                    drop(-> a);
                    next = 10;
                    print(*next);
                """
                run = self.native(source)
                self.assertEqual((run.returncode, run.stdout), (0, '5\n6\nView(9)\n10\n'), run.stderr)
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('print(a);', 'next = 12; print(a);'))
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program("""
                struct View { target: &Int }
                fn put(h: &mut A<View>, q: &mut Pool<View>) {
                    let mut ints = pool<Int>(1);
                    let local = ints.new(9);
                    let b = q.new(target: &local);
                    *h = <- b;
                }
            """)

    def test_mutable_handle_replacement_rejects_invalid_transfers_and_keeps_loan(self):
        prefix = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(2);
            let mut a: A<Int> = p.new(1);
            let b = q.new(2);
            let witness = q.new(2);
        """
        for body, error in (
            ('let h = a.ref(); *h = <- b;', 'emprunt mutable direct'),
            ('let h = a.mut_ref(); *h = 42;', 'transfert <- explicite'),
            ('let h = a.mut_ref(); *h = <- a;', 'emprunt encore utilisé'),
            ('let h = a.mut_ref(); *h = <- b; drop(-> a); if witness.vequals(h) {}', 'emprunt encore utilisé'),
            ('let h = a.mut_ref(); *h = <- b; q.reset(); if witness.vequals(h) {}', 'référence de tableau'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + "print(*b); print(*witness);" + body)

    def test_handle_reference_signatures_reborrow_across_calls(self):
        prefix = """
            fn relay(v: &mut A<Int>) -> &mut A<Int> { return v; }
            fn equal(p: &mut Pool<Int>, v: &A<Int>) -> bool {
                let expected = p.new(7);
                return expected.vequals(v);
            }
            fn pair(a: &mut A<Int>, b: &mut A<Int>) {}
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a: A<Int> = p.new(7);
            let h = relay(a.mut_ref());
        """
        run = self.native(prefix + """
            if equal(&mut q, h) { print(1); }
            if equal(&mut q, a.ref()) { print(2); }
            print(*a);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n2\n7\n')
        for body, error in (
            ('pair(h, h);', 'emprunt actif'),
            ('drop(-> a); if equal(&mut q, h) {}', 'emprunt encore utilisé'),
            ('p.reset(); if equal(&mut q, h) {}', 'référence de tableau'),
            ('if equal(&mut q, a.vref()) {}', 'emprunt ref vers A<Int>'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_handle_reference_cannot_escape_local_receiver(self):
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn escape(p: &mut Pool<Int>) -> &A<Int> {
                    let a = p.new(7);
                    return a.ref();
                }
            """)

    def test_typed_handle_can_borrow_non_copy_content(self):
        source = """
            struct Point { x: Int, y: Int }
            fn write(p: &mut Point) { p.x = 17; }
            fn read(p: &Point) -> Int { return p.x; }
            let mut points = pool<Point>(1);
            let mut point: A<Point> = points.new();
            address(point);
            let view = point.mut_vref();
            address(view);
            write(view);
            print(read(point.vref()));

            let mut vectors = pool<Vector<Int>>(1);
            let mut numbers = vectors.new();
            let writable = numbers.mut_vref();
            writable.push(19);
            let readable = numbers.vref();
            print(readable[0]);

            let mut strings = pool<String>(1);
            let mut text = strings.new();
            let writer = text.mut_vref();
            writer.push_str("é");
            let reader = text.vref();
            print(&reader[..]);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, borrowed, point, element, string = run.stdout.splitlines()
        self.assertEqual((borrowed, point, element, string), (original, '17', '19', 'é'))
        for operation, diagnostic in (
            ('drop(-> point);', 'emprunt encore utilisé'),
            ('points.reset();', 'reset interdit'),
        ):
            with self.subTest(operation=operation), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('print(read(point.vref()));',
                    f'let held = point.vref(); {operation} print(read(held));'))

    def test_vequals_compares_strings_and_vectors_in_logical_order(self):
        source = """
            let mut strings = pool<String>(2);
            let mut a = strings.new();
            let mut b = strings.new();
            if a.vequals(b.ref()) { print(1); }
            a.push_str("été");
            b.push_str("é");
            if a.vequals(b.ref()) { print(2); }
            b.push_str("té");
            if a.vequals(b.ref()) { print(3); }

            let mut numbers = pool<Vector<Int>>(2);
            let mut low = numbers.new();
            low.push(-7);
            low.push(19);
            let mut high = numbers.new();
            high.push(-7);
            high.push(19);
            let view = high.ref();
            if low.vequals(view) { print(4); }
            match high.replace(0, 19) { Ok(_) => {}, Err(_) => {} }
            match high.replace(1, -7) { Ok(_) => {}, Err(_) => {} }
            if low.vequals(high.ref()) { print(5); }

            let mut bytes = pool<Vector<u8>>(2);
            let mut first = bytes.new();
            let mut second = bytes.new();
            first.push(0xff);
            first.push(0x00);
            second.push(0xff);
            second.push(0x00);
            if first.vequals(second.ref()) { print(6); }
            match second.replace(1, 0xff) { Ok(_) => {}, Err(_) => {} }
            if first.vequals(second.ref()) { print(7); }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n3\n4\n6\n')
        with self.assertRaisesRegex(Error, 'emprunt du handle A<Vector<Int>>'):
            verify_program(source + 'if low.vequals(second.ref()) {}')
        with self.assertRaisesRegex(Error, 'référence de tableau|reset interdit'):
            verify_program(source.replace('if low.vequals(view)', 'numbers.reset(); if low.vequals(view)'))

    def test_vequals_compares_struct_fields_and_enum_variants(self):
        source = """
            struct Point { x: Int, y: Int }
            struct Other { x: Int, y: Int }
            enum Choice { First { n: Int }, Second { n: Int }, Empty }
            let mut left = pool<Point>(1);
            let mut right = pool<Point>(2);
            let mut others = pool<Other>(1);
            let mut choices = pool<Choice>(2);
            let a = left.new(x: 7, y: 11);
            let b = right.new(x: 7, y: 11);
            let c = right.new(x: 7, y: 13);
            let borrowed = b.ref();
            if a.vequals(borrowed) { print(1); }
            if a.vequals(c.ref()) { print(2); }
            let first = new(choices) Choice.First { n: 7 };
            let second = new(choices) Choice.Second { n: 7 };
            let equal = new(choices) Choice.First { n: 7 };
            let empty = new(choices) Choice.Empty;
            if first.vequals(second.ref()) { print(3); }
            if first.vequals(equal.ref()) { print(4); }
            if first.vequals(empty.ref()) { print(5); }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n4\n')
        wrong = source.replace('let borrowed = b.ref();',
                               'print(b); let wrong = others.new(x: 7, y: 11); let borrowed = wrong.ref();')
        with self.assertRaisesRegex(Error, 'emprunt du handle A<Point>'):
            verify_program(wrong)

    def test_generic_handle_slot_preserves_type_across_borrow_and_replacement(self):
        source = """
            struct Point { x: Int }
            struct Other { x: Int }
            fn relay(slot: &A<Point>) -> &A<Point> { return slot; }
            fn inspect(slot: &A<Point>) {}
            let mut p = pool<Point>(2);
            let mut other = pool<Other>(1);
            let mut point = p.new(x: 13);
            address(point);
            let replacement = p.new(x: 17);
            address(replacement);
            let loan = point.mut_ref();
            *loan = <- replacement;
            address(point);
            let reader = relay(point.ref());
            inspect(reader);
            print(point.x);
            let reused = p.new(x: 23);
            address(reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        old, replacement, result, value, reused = run.stdout.splitlines()
        self.assertNotEqual(old, replacement)
        self.assertEqual((result, value, reused), (replacement, '17', old))
        for previous, modified, diagnostic in (
            ('*loan = <- replacement;', '*loan = <- other.new();', 'annotation A<Point>'),
            ('inspect(reader);', 'drop(-> point); inspect(reader);', 'emprunt encore utilisé'),
        ):
            with self.subTest(modified=modified), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(previous, modified))
        wrong_type = source.replace('let reader = relay(point.ref());',
                                    'let wrong = other.new(); let reader = relay(wrong.ref());')
        with self.assertRaisesRegex(Error, 'emprunt ref vers A<Point>'):
            verify_program(wrong_type)

    def test_owned_handle_signatures_preserve_identity_across_functions(self):
        run = self.native("""
            fn relay(a: -> A<Int>) -> <- A<Int> { return <- a; }
            fn make(p: &mut Pool<Int>) -> <- A<Int> {
                let a = p.new(7);
                address(a);
                let b = relay(-> a);
                return <- b;
            }
            let mut p = pool<Int>(1);
            let result: A<Int> = make(&mut p);
            address(result);
            print(*result);
            drop(-> result);
            let reused = p.new(8);
            address(reused);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, returned, value, reused = run.stdout.splitlines()
        self.assertEqual((returned, reused, value), (before, before, '7'))

    def test_owned_handle_signatures_require_typed_pool_provenance(self):
        for source in (
            """
                fn relay(a: -> A<Int>) -> <- A<Int> { return <- a; }
                let mut s = stack(4096);
                let a = new(s) Int(1);
                let b = relay(-> a);
                print(*b);
            """,
            """
                fn invalid(s: &mut Allocator) -> <- A<Int> {
                    let a = new(s) Int(1);
                    return <- a;
                }
            """,
            'fn invalid(a: -> Int) -> <- A<Int> { return <- a; }',
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, 'allocation de Pool<Int>'):
                verify_program(source)

    def test_mutable_handle_replacement_transfers_vector_slots(self):
        source = """
            fn put(h: &mut A<Vector<A<Int>>>, b: -> A<Vector<A<Int>>>) { *h = <- b; }
            fn relay(h: &mut A<Vector<A<Int>>>, b: -> A<Vector<A<Int>>>) { put(h, -> b); }
            let mut p = pool<Vector<A<Int>>>(1);
            let mut q = pool<Vector<A<Int>>>(1);
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let mut third = pool<Int>(1);
            let mut a = p.new();
            a.push(-> first.new(1));
            let mut b = q.new();
            b.push(-> second.new(2));
            b.push(-> third.new(3));
            relay(a.mut_ref(), -> b);
            first.reset();
            p.reset();
            let selected = <- a.remove(0);
            print(*selected);
            drop(-> selected);
            second.reset();
            let remaining = <- a.remove(0);
            print(*remaining);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '2\n3\n'), run.stderr)
        for pool in ('second', 'third'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('first.reset();', f'{pool}.reset();'))

    def test_handle_replacement_builds_vector_slots_in_callee(self):
        source = """
            fn put(h: &mut A<Vector<A<Int>>>, v: &mut Pool<Vector<A<Int>>>, p: &mut Pool<Int>, x: -> A<Int>) {
                let mut b = v.new();
                b.push(-> p.new(2));
                b.push(-> x);
                *h = <- b;
            }
            fn relay(h: &mut A<Vector<A<Int>>>, v: &mut Pool<Vector<A<Int>>>, p: &mut Pool<Int>, x: -> A<Int>) {
                put(h, v, p, -> x);
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut vq = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a = vp.new();
            let x = q.new(3);
            address(x);
            relay(a.mut_ref(), &mut vq, &mut p, -> x);
            vp.reset();
            let first = <- a.remove(0);
            print(*first);
            drop(-> first);
            p.reset();
            let next = <- a.remove(0);
            address(next);
            print(*next);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, first, after, second = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((first, second), ('2', '3'))
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('vp.reset();', f'{pool}.reset();'))
        with self.assertRaisesRegex(Error, 'source durable vérifiable|pool de l’élément doit survivre'):
            verify_program(source.replace('b.push(-> p.new(2));',
                                          'let mut local = pool<Int>(1); b.push(-> local.new(2));'))

    def test_handle_replacement_transports_transformed_vector_inventory(self):
        source = """
            fn put(h: &mut A<Vector<A<Int>>>, mut b: -> A<Vector<A<Int>>>, r: &mut Pool<Int>) {
                let discarded = <- b.remove(0);
                drop(-> discarded);
                b.push(-> r.new(4));
                *h = <- b;
            }
            fn relay(h: &mut A<Vector<A<Int>>>, b: -> A<Vector<A<Int>>>, r: &mut Pool<Int>) {
                put(h, -> b, r);
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut vq = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut r = pool<Int>(1);
            let mut a = vp.new();
            let mut b = vq.new();
            b.push(-> p.new(2));
            let original = q.new(3);
            address(original);
            b.push(-> original);
            relay(a.mut_ref(), -> b, &mut r);
            p.reset();
            let first = <- a.remove(0);
            address(first);
            print(*first);
            drop(-> first);
            q.reset();
            let next = <- a.remove(0);
            print(*next);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, first, second = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((first, second), ('3', '4'))
        for pool in ('q', 'r'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source.replace('p.reset();', f'{pool}.reset();'))
        indexed = source.replace(
            'let discarded = <- b.remove(0);\n                drop(-> discarded);\n                b.push(-> r.new(4));',
            'match <- b.replace(0, -> r.new(4)) { Ok(old) => { drop(-> old); }, Err(rejected) => { drop(-> rejected); loop {} } }'
        ).replace('address(first);', '').replace('q.reset();', 'r.reset();').replace('print(*next);', 'address(next); print(*next);')
        run = self.native(indexed)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, first, after, second = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((first, second), ('4', '3'))
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(indexed.replace('r.reset();', 'q.reset();'))

    def test_handle_replacement_builds_vector_with_conditional_inventory(self):
        source = """
            fn put(h: &mut A<Vector<A<Int>>>, v: &mut Pool<Vector<A<Int>>>, p: &mut Pool<Int>, flag: Int) {
                let mut b = v.new();
                if flag == 1 { b.push(-> p.new(2)); }
                *h = <- b;
            }
            fn relay(h: &mut A<Vector<A<Int>>>, v: &mut Pool<Vector<A<Int>>>, p: &mut Pool<Int>, flag: Int) {
                put(h, v, p, flag);
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut vq = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut a = vp.new();
            relay(a.mut_ref(), &mut vq, &mut p, FLAG);
            print(a.len());
            drop(-> a);
            p.reset();
        """
        for flag in (0, 1):
            with self.subTest(flag=flag):
                run = self.native(source.replace('FLAG', str(flag)))
                self.assertEqual((run.returncode, run.stdout), (0, f'{flag}\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(source.replace('FLAG', '1').replace('print(a.len());', 'p.reset(); print(a.len());'))

    def test_buffered_handle_pop_cleans_only_a_present_payload(self):
        source = """
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                if flag == 1 { v.push(-> p.new(4)); }
                let saved = <- v.pop();
                print(v.len());
                if flag == 0 { print(8); }
                CLEANUP
            }
            run(0);
            run(1);
        """
        automatic = self.native(source.replace('CLEANUP', 'if flag == 2 { saved ->; drop(-> saved); }'))
        self.assertEqual((automatic.returncode, automatic.stdout), (0, '0\n8\n0\n'), automatic.stderr)
        self.assertEqual(automatic.stderr.count('destroy appel=4'), 1)
        explicit = source.replace('CLEANUP', 'drop(-> saved); let again = p.new(7); print(*again);')
        run = self.native(explicit)
        self.assertEqual((run.returncode, run.stdout), (0, '0\n8\n7\n0\n7\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(explicit.replace('drop(-> saved);', 'p.reset(); drop(-> saved);'))
        with self.assertRaisesRegex(Error, 'consommation explicite'):
            verify_program(source.replace('CLEANUP', 'let copied = saved;'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('CLEANUP', 'drop(-> saved); drop(-> saved);'))

    def test_buffered_handle_pop_match_consumes_saved_result(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut v = vp.new();
            let initial = p.new(4);
            address(initial);
            v.push(-> initial);
            let saved = <- v.pop();
            v.push(-> q.new(8));
            let a = match (-> saved) {
                Some(x) => { <- x },
                None => { loop {} }
            };
            address(a);
            print(*a);
            print(v.len());
            drop(-> a);
            let reused = p.new(9);
            address(reused);
            let next = <- v.pop();
            match (-> next) { Some(x) => { print(*x); }, None => {} }
            let empty = <- v.pop();
            match (-> empty) { Some(value) => { drop(-> value); print(0); }, _ => { print(1); } }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, transferred, value, length, reused, next_value, empty = run.stdout.splitlines()
        self.assertEqual((transferred, reused), (original, original))
        self.assertEqual((value, length, next_value, empty), ('4', '1', '8', '1'))
        destroyed = [line.split('=')[-1] for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(destroyed.count('4'), 1)
        self.assertEqual(destroyed.count('8'), 1)
        for invalid, diagnostic in (
            (source.replace('let a = match', 'p.reset(); let a = match'), 'reset interdit'),
            (source.replace('match (-> saved)', 'match saved'), 'consommation explicite'),
            (source + 'match (-> empty) { Some(value) => { drop(-> value); }, None => {} }', 'plus utilisable'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_buffered_handle_pop_match_wildcard_releases_only_present_payload(self):
        source = """
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                if flag == 1 { v.push(-> p.new(4)); }
                let saved = <- v.pop();
                let result = match (-> saved) {
                    Some(value) => { drop(-> value); let reused = p.new(9); *reused },
                    None => { let reused = p.new(9); *reused }
                };
                print(result);
                let empty = <- v.pop();
                match (-> empty) { Some(value) => { drop(-> value); }, None => {} } print(v.len());
            }
            run(0);
            run(1);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '9\n0\n9\n0\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy appel=4'), 1)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('print(result);', 'print(result); drop(-> saved);'))
        with self.assertRaisesRegex(Error, 'bras _ inaccessible'):
            verify_program(source.replace('Some(value) => { drop(-> value); }, None => {}',
                'Some(value) => { drop(-> value); }, None => {}, _ => { print(v.len()); }'))

    def test_buffered_handle_pop_moves_across_explicit_scope_entries(self):
        source = """
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                if flag == 1 { v.push(-> p.new(4)); }
                let saved = <- v.pop();
                let moved = <- saved;
                {
                    moved ->;
                    {
                        moved ->;
                        match (-> moved) {
                            Some(x) => { print(*x); },
                            None => { print(0); }
                        }
                    }
                }
                let reused = p.new(9);
                print(*reused);
                let empty = <- v.pop();
                {
                    empty ->;
                    match (-> empty) { Some(value) => { drop(-> value); print(v.len()); }, None => { print(v.len()); } }
                }
            }
            run(0);
            run(1);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '0\n9\n0\n4\n9\n0\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy appel=4'), 1)
        for invalid, diagnostic in (
            (source.replace('moved ->;', '', 1), 'parent direct'),
            (source.replace('let reused', 'drop(-> moved); let reused'), 'plus utilisable'),
            (source.replace('let moved = <- saved;', 'let moved = <- saved; drop(-> saved);'), 'plus utilisable'),
            (source.replace('match (-> moved)', 'p.reset(); match (-> moved)'), 'reset interdit'),
            (source.replace('empty ->;', 'drop(-> empty);'), 'avant de détruire depuis un enfant'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_vector_result_can_be_produced_directly_at_end_of_block(self):
        source = """
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut v = vp.new();
            let initial = p.new(4);
            address(initial);
            v.push(-> initial);
            let replaced: Result<A<Int>, A<Int>> = { <- v.replace(0, -> q.new(8)) };
            let popped: Option<A<Int>> = { <- v.pop() };
            let empty: Option<A<Int>> = { <- v.pop() };
            match (-> replaced) { Ok(x) => { address(x); print(*x); }, Err(rejected) => { drop(-> rejected); } }
            match (-> popped) { Some(x) => { print(*x); }, None => {} }
            drop(-> empty); print(0);
            v.push(-> p.new(9));
            let removed = { <- v.remove(0) };
            print(*removed);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        initial, selected, old, new, empty, removed = run.stdout.splitlines()
        self.assertEqual((selected, old, new, empty, removed), (initial, '4', '8', '0', '9'))
        with self.assertRaisesRegex(Error, 'sans point-virgule'):
            verify_program(source.replace('{ <- v.pop() }', '{ <- v.pop(); }', 1))
        for actual, incorrect in (('Result<A<Int>, A<Int>>', 'Result<(), A<Int>>'),
                                  ('Option<A<Int>>', 'Option<Int>')):
            with self.subTest(incorrect=incorrect), self.assertRaisesRegex(Error, 'annotation de let'):
                verify_program(source.replace(actual, incorrect, 1))
        with self.assertRaisesRegex(Error, 'ne survit pas à ce bloc'):
            verify_program("""
                let mut vp = pool<Vector<A<Int>>>(1);
                let saved = {
                    let mut p = pool<Int>(1);
                    let mut v = vp.new();
                    v.push(-> p.new(4));
                    <- v.pop()
                };
                drop(-> saved);
            """)

    def test_buffered_handle_pop_returns_through_block_receivers(self):
        source = """
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let received = {
                    let forwarded = {
                        let mut v = vp.new();
                        if flag == 1 { v.push(-> p.new(4)); }
                        let saved = <- v.pop();
                        <- saved
                    };
                    <- forwarded
                };
                match (-> received) {
                    Some(x) => { print(*x); },
                    None => { print(0); }
                }
                let empty = {
                    let mut v = vp.new();
                    let saved = <- v.pop();
                    <- saved
                };
                drop(-> empty);
                let reused = p.new(9);
                print(*reused);
            }
            run(0);
            run(1);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '0\n9\n4\n9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy appel=4'), 1)
        for invalid, diagnostic in (
            (source.replace('let mut p = pool<Int>(1);', '').replace(
                'let mut v = vp.new();', 'let mut p = pool<Int>(1); let mut v = vp.new();').replace(
                'let reused = p.new(9);', 'let mut q = pool<Int>(1); let reused = q.new(9);'),
             'ne survit pas à ce bloc'),
            (source.replace('match (-> received)', 'p.reset(); match (-> received)'), 'reset interdit'),
            (source.replace('<- forwarded\n', '<- forwarded;\n'), 'sans point-virgule'),
            (source.replace('match (-> received)', 'let another = <- v.pop(); match (-> another)').replace(
                'let received = {', 'let mut v = vp.new(); let received = {'), 'sans usage explicite'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_buffered_handle_pop_restores_only_returned_imports(self):
        source = """
            let mut p = pool<Int>(1);
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut v = vp.new();
            let initial = p.new(4);
            address(initial);
            v.push(-> initial);
            let saved = <- v.pop();
            {
                saved ->;
                let moved = <- saved;
                <- moved;
            }
            match (-> saved) { Some(x) => { address(x); }, None => {} }
            let empty = <- v.pop();
            {
                empty ->;
                <- empty;
            }
            match (-> empty) { Some(value) => { drop(-> value); print(v.len()); }, None => { print(v.len()); } }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        initial, returned, length = run.stdout.splitlines()
        self.assertEqual((returned, length), (initial, '0'))
        self.assertEqual(run.stderr.count('destroy initial=4'), 1)
        with_receiver = source.replace('{\n                saved ->;', 'let received = {\n                saved ->;')
        with_receiver = with_receiver.replace('<- moved;\n            }', '<- moved\n            };')
        with_receiver = with_receiver.replace('match (-> saved)', 'match (-> received)')
        received = self.native(with_receiver)
        self.assertEqual(received.returncode, 0, received.stderr)
        first, second, remaining = received.stdout.splitlines()
        self.assertEqual((second, remaining), (first, '0'))
        for invalid, diagnostic in (
            (source.replace('<- moved;', 'drop(-> moved);'), 'plus utilisable'),
            (source.replace('<- empty;', '<- empty; drop(-> empty);'), 'plus utilisable'),
            (source.replace('<- empty;', '<- empty; <- empty;'), 'déjà marqué'),
            (source.replace('match (-> saved)', 'p.reset(); match (-> saved)'), 'reset interdit'),
            (with_receiver.replace('match (-> received)', 'drop(-> saved); match (-> received)'),
             'plus utilisable'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_buffered_handle_pop_joins_discriminant_and_provenance(self):
        source = """
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                let saved = if flag == 1 {
                    v.push(-> p.new(4));
                    let value = <- v.pop();
                    <- value
                } else if flag == 2 {
                    v.push(-> q.new(7));
                    <- v.pop()
                } else {
                    <- v.pop()
                };
                CONSUME
                let a = p.new(11);
                let b = q.new(12);
                print(*a + *b);
            }
            run(0);
            run(1);
            run(2);
        """
        match = 'match (-> saved) { Some(x) => { print(*x); }, None => { print(0); } }'
        run = self.native(source.replace('CONSUME', match))
        self.assertEqual((run.returncode, run.stdout), (0, '0\n23\n4\n23\n7\n23\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy appel=4'), 1)
        self.assertEqual(run.stderr.count('destroy appel=7'), 1)
        dropped = self.native(source.replace('CONSUME', 'drop(-> saved);'))
        self.assertEqual((dropped.returncode, dropped.stdout), (0, '23\n23\n23\n'), dropped.stderr)
        self.assertEqual(dropped.stderr.count('destroy appel=4'), 1)
        self.assertEqual(dropped.stderr.count('destroy appel=7'), 1)
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('CONSUME', f'{pool}.reset(); {match}'))
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(source.replace('CONSUME', match).replace('<- value\n', 'drop(-> value); 4\n'))

    def test_buffered_handle_pop_survives_break_and_cleans_continue(self):
        source = """
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut count = 0;
                let saved = loop {
                    let mut v = vp.new();
                    if count == 0 {
                        v.push(-> p.new(4));
                        let discarded = <- v.pop();
                        if flag == 2 { discarded ->; drop(-> discarded); }
                        count = 1;
                        continue;
                    }
                    if flag == 1 {
                        v.push(-> p.new(7));
                        let kept = <- v.pop();
                        break <- kept;
                    }
                    break <- v.pop();
                };
                match (-> saved) { Some(x) => { print(*x); }, None => { print(0); } }
                let reused = p.new(9);
                print(*reused);
            }
            run(0);
            run(1);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '0\n9\n7\n9\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy appel=4'), 2)
        self.assertEqual(run.stderr.count('destroy appel=7'), 1)
        for invalid, diagnostic in (
            (source.replace('break <- v.pop();', 'break 0;'), 'même type'),
            (source.replace('match (-> saved)', 'p.reset(); match (-> saved)'), 'reset interdit'),
            (source.replace('v.push(-> p.new(7));',
                            'let mut q = pool<Int>(1); let mut v = vp.new(); v.push(-> q.new(7));'),
             'ne survit pas à la boucle'),
            (source.replace('let saved = loop {',
                            'let mut outside = vp.new(); let empty = <- outside.pop(); let saved = loop {')
                   .replace('break <- v.pop();', 'break <- empty;'), 'scope quitté'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_buffered_handle_pop_return_contract_across_calls(self):
        source = """
            fn take(mut v: -> Vector<A<Int>>, early: Int) -> <- Option<A<Int>> {
                if early == 1 { return <- v.pop(); }
                let saved = <- v.pop();
                return <- saved;
            }
            fn relay(v: -> Vector<A<Int>>, early: Int) -> <- Option<A<Int>> {
                let saved = take(-> v, early);
                return <- saved;
            }
            let mut p = pool<Int>(1);
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut v = vp.new();
            let initial = p.new(4);
            address(initial);
            v.push(-> initial);
            let saved = relay(-> v, 1);
            match (-> saved) { Some(x) => { address(x); print(*x); }, None => {} }
            let empty_vector = vp.new();
            let empty = relay(-> empty_vector, 0);
            match (-> empty) { Some(value) => { drop(-> value); print(9); }, None => { print(9); } }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, value, empty = run.stdout.splitlines()
        self.assertEqual((returned, value, empty), (original, '4', '9'))
        self.assertEqual(run.stderr.count('destroy initial=4'), 1)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('match (-> saved)', 'p.reset(); match (-> saved)'))
        with self.assertRaisesRegex(Error, 'ne survit pas à ce bloc'):
            verify_program(source.replace('if early == 1 { return <- v.pop(); }', '''
                let mut p = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut local = vp.new();
                local.push(-> p.new(3));
                if early == 1 { return <- local.pop(); }
            '''))

    def test_buffered_handle_pop_passes_statically_empty_option_from_function(self):
        source = """
            fn empty(vp: &mut Pool<Vector<A<Int>>>) -> <- Option<A<Int>> {
                let mut v = vp.new();
                return <- v.pop();
            }
            fn relay(value: -> Option<A<Int>>) -> <- Option<A<Int>> {
                return <- value;
            }
            fn run() {
                let mut vp = pool<Vector<A<Int>>>(1);
                let saved = empty(&mut vp);
                let forwarded = relay(-> saved);
                match (-> forwarded) { Some(x) => { print(*x); }, None => { print(0); } }
                let mut v = vp.new();
                let direct = <- v.pop();
                let again = relay(-> direct);
                drop(-> again);
            }
            run();
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '0\n'), run.stderr)
        self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()), 2)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('let again = relay(-> direct);',
                'let again = relay(-> direct); drop(-> direct);'))

    def test_buffered_handle_pop_transfers_as_argument(self):
        source = """
            fn forward(saved: -> Option<A<Int>>) -> <- Option<A<Int>> {
                return <- saved;
            }
            fn consume(saved: -> Option<A<Int>>, marker: Int) {
                let result = forward(-> saved);
                match (-> result) { Some(x) => { address(x); print(*x); }, None => { print(0); } }
                print(marker);
            }
            fn clear(p: &mut Pool<Int>) -> Int { p.reset(); return 8; }
            let mut p = pool<Int>(1);
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut v = vp.new();
            let initial = p.new(4);
            address(initial);
            v.push(-> initial);
            let saved = <- v.pop();
            consume(-> saved, 1);
            consume(-> <- v.pop(), clear(&mut p));
            let reused = p.new(9);
            address(reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, value, first, empty, second, reused = run.stdout.splitlines()
        self.assertEqual((returned, reused), (original, original))
        self.assertEqual((value, first, empty, second), ('4', '1', '0', '8'))
        self.assertEqual(run.stderr.count('destroy initial=4'), 1)
        for invalid, diagnostic in (
            ('consume(saved, 1);', 'mode attendu'),
            ('consume(-> saved, clear(&mut p));', 'argument en cours'),
            ('consume(-> saved, 1); drop(-> saved);', 'plus utilisable'),
            ('{ consume(-> saved, 1); }', 'scope appelant direct'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('consume(-> saved, 1);', invalid))

    def test_buffered_handle_replace_preserves_result_after_vector_changes(self):
        source = """
            let mut p = pool<Int>(2);
            let mut q = pool<Int>(1);
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut v = vp.new();
            let initial = p.new(4);
            address(initial);
            v.push(-> initial);
            let saved = <- v.replace(0, -> q.new(8));
            let rejected = <- v.replace(9, -> p.new(7));
            drop(-> v);
            match (-> saved) { Ok(x) => { address(x); print(*x); }, Err(rejected) => { drop(-> rejected); print(0); } }
            match (-> rejected) { Ok(old) => { drop(-> old); print(0); }, Err(x) => { print(*x); } }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, old, rejected = run.stdout.splitlines()
        self.assertEqual((returned, old, rejected), (original, '4', '7'))
        self.assertEqual(run.stderr.count('destroy initial=4'), 1)
        for invalid, diagnostic in (
            ('p.reset(); match (-> saved)', 'reset interdit'),
            ('q.reset(); match (-> saved)', 'reset interdit'),
            ('print(saved); match (-> saved)', 'valeur scalaire'),
            ('let copied = saved; match (-> saved)', 'consommation explicite'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('match (-> saved)', invalid))

    def test_buffered_handle_replace_refines_pool_per_arm(self):
        source = """
            fn run(index: Int) {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                v.push(-> p.new(4));
                let saved = <- v.replace(index, -> q.new(8));
                drop(-> v);
                let received = {
                    saved ->;
                    let moved = <- saved;
                    <- moved
                };
                match (-> received) {
                    Ok(old) => { q.reset(); print(*old); },
                    Err(incoming) => { p.reset(); print(*incoming); }
                }
            }
            run(0);
            run(9);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '4\n8\n'), run.stderr)
        for reset, invalid in (('q.reset(); print(*old);', 'p.reset(); print(*old);'),
                               ('p.reset(); print(*incoming);', 'q.reset(); print(*incoming);')):
            with self.subTest(reset=reset), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace(reset, invalid))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('match (-> received)', 'drop(-> saved); match (-> received)'))

    def test_buffered_handle_replace_joins_each_arm_separately(self):
        source = """
            fn run(flag: Int, index: Int) {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut r = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let saved = CHOICE;
                match (-> saved) {
                    Ok(old) => { q.reset(); print(*old); },
                    Err(incoming) => { p.reset(); r.reset(); print(*incoming); }
                }
            }
            run(0, 0);
            run(1, 0);
            run(0, 7);
            run(1, 7);
        """
        left = """
            let mut v = vp.new();
            v.push(-> p.new(4));
            let result = <- v.replace(index, -> q.new(8));
        """
        right = left.replace('p.new(4)', 'r.new(7)')
        choices = (
            f'if flag == 0 {{ {left} <- result }} else {{ {right} <- result }}',
            f'loop {{ if flag == 0 {{ {left} break <- result; }} {right} break <- result; }}',
        )
        for choice in choices:
            with self.subTest(choice=choice):
                program = source.replace('CHOICE', choice)
                run = self.native(program)
                self.assertEqual((run.returncode, run.stdout), (0, '4\n7\n8\n8\n'), run.stderr)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('q.reset(); print(*old);', 'r.reset(); print(*old);'))
                with self.assertRaisesRegex(Error, 'même type'):
                    verify_program(program.replace('v.replace(index, -> q.new(8))', 'v.try_push(-> q.new(8))', 1))

    def test_buffered_handle_results_return_by_contract(self):
        source = """
            fn choose(index: Int, p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- Result<A<Int>, A<Int>> {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                v.push(-> p.new(4));
                if index == 0 { return <- v.replace(index, -> q.new(8)); }
                let saved = <- v.replace(index, -> q.new(9));
                return <- saved;
            }
            fn relay(index: Int, p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- Result<A<Int>, A<Int>> {
                let saved = choose(index, p, q);
                let forwarded = forward(-> saved);
                return <- forwarded;
            }
            fn forward(saved: -> Result<A<Int>, A<Int>>) -> <- Result<A<Int>, A<Int>> {
                return <- saved;
            }
            fn push(mut v: -> Vector<A<Int>>, p: &mut Pool<Int>) -> <- Result<(), A<Int>> {
                return <- v.try_push(-> p.new(11));
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let saved = relay(0, &mut p, &mut q);
            match (-> saved) { Ok(x) => { q.reset(); print(*x); }, Err(x) => { p.reset(); print(*x); } }
            let again = relay(9, &mut p, &mut q);
            match (-> again) { Ok(x) => { q.reset(); print(*x); }, Err(x) => { p.reset(); print(*x); } }
            let mut vp = pool<Vector<A<Int>>>(1);
            let v = vp.new();
            let pushed = push(-> v, &mut p);
            drop(-> pushed);
            let reused = p.new(12);
            print(*reused);
        """
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '4\n9\n12\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy return=11'), 1)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('q.reset(); print(*x);', 'p.reset(); print(*x);'))
        with self.assertRaisesRegex(Error, 'ne survit pas à ce bloc'):
            verify_program(source.replace('v.push(-> p.new(4));',
                'let mut local = pool<Int>(1); v.push(-> local.new(4));'))
        with self.assertRaisesRegex(Error, 'transféré attendu'):
            verify_program(source.replace('forward(-> saved)', 'forward(-> <- v.try_push(-> p.new(1)))')
                .replace('let forwarded', 'drop(-> saved); let mut vp = pool<Vector<A<Int>>>(1); let mut v = vp.new(); let forwarded'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('return <- forwarded;', 'drop(-> saved); return <- forwarded;'))

    def test_buffered_handle_try_push_returns_err_at_capacity_through_calls(self):
        source = """
            fn push(mut v: -> Vector<A<Int>>, incoming: -> A<Int>) -> <- Result<(), A<Int>> {
                return <- v.try_push(-> incoming);
            }
            fn relay(result: -> Result<(), A<Int>>, marker: Int) -> <- Result<(), A<Int>> {
                print(marker);
                return <- result;
            }
            fn clear(q: &mut Pool<Int>) -> Int { q.reset(); return 0; }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(131072);
            let mut q = pool<Int>(1);
            #(directive, stack_region_max_size=1M) {
                let mut v = vp.new();
                let mut i = 0;
                while i < 131072 { v.push(-> p.new(i)); i = i + 1; }
                let incoming = q.new(37);
                address(incoming);
                let result = push(-> v, -> incoming);
                let returned = relay(-> result, 1);
                match (-> returned) { Ok(()) => { print(0); }, Err(x) => { address(x); print(*x); } }
                let reused = q.new(38);
                address(reused);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        initial, marker, returned, value, reused = run.stdout.splitlines()
        self.assertEqual((marker, returned, value, reused), ('1', initial, '37', initial))
        self.assertEqual(run.stderr.count('destroy incoming=37'), 1)
        with self.assertRaisesRegex(Error, 'argument en cours'):
            verify_program(source.replace('relay(-> result, 1)', 'relay(-> result, clear(&mut q))'))

    def test_buffered_handle_replace_allows_disjoint_injected_reset_after_vector_cleanup(self):
        source = """
            fn choose(index: Int, p: &mut Pool<Int>, q: &mut Pool<Int>) -> <- A<Int> {
                let mut vp = pool<Vector<A<Int>>>(1);
                let saved = CHOICE;
                match (-> saved) {
                    Ok(x) => { q.reset(); return <- x; },
                    Err(x) => { p.reset(); return <- x; }
                }
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let first = choose(0, &mut p, &mut q);
            print(*first);
            drop(-> first);
            let second = choose(9, &mut p, &mut q);
            print(*second);
        """
        setup = """
            let mut v = vp.new();
            v.push(-> p.new(4));
            let replaced = <- v.replace(index, -> q.new(8));
        """
        programs = (
            source.replace('CHOICE', f'loop {{ {setup} break <- replaced; }}'),
            source.replace('let saved = CHOICE;', f'{setup} drop(-> v); let saved = <- replaced;'),
        )
        for program in programs:
            with self.subTest(loop='loop {' in program):
                run = self.native(program)
                self.assertEqual((run.returncode, run.stdout), (0, '4\n8\n'), run.stderr)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('q.reset(); return <- x;', 'p.reset(); return <- x;'))
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('let replaced =', 'p.reset(); let replaced ='))

    def test_buffered_handle_exchange_wildcard_consumes_remaining_arm(self):
        source = """
            fn run(index: Int) {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                v.push(-> p.new(4));
                let saved = <- v.replace(index, -> q.new(8));
                drop(-> v);
                let value = match (-> saved) {
                    EXPLICIT,
                    _ => { let reused = POOL.new(9); *reused }
                };
                print(value);
            }
            run(0);
            run(7);
        """
        for arm, pool, expected in (
            ('Ok(x) => { *x }', 'q', '4\n9\n'),
            ('Err(x) => { *x }', 'p', '9\n8\n'),
        ):
            with self.subTest(arm=arm):
                opposite = 'Err' if arm.startswith('Ok') else 'Ok'
                program = source.replace('EXPLICIT', arm).replace('POOL', pool).replace(
                    '_ => { let reused', opposite + '(discarded) => { drop(-> discarded); let reused')
                run = self.native(program)
                self.assertEqual((run.returncode, run.stdout), (0, expected), run.stderr)
                self.assertEqual(run.stderr.count('destroy appel=4'), 2)
                with self.assertRaisesRegex(Error, 'plus utilisable'):
                    verify_program(program.replace('print(value);', 'print(value); drop(-> saved);'))
        with self.assertRaisesRegex(Error, 'bras _ inaccessible'):
            verify_program(source.replace('EXPLICIT', 'Ok(x) => { *x }, Err(x) => { *x }').replace('POOL', 'p'))
        run = self.native("""
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut v = vp.new();
            let saved = <- v.try_push(-> p.new(4));
            match (-> saved) { Err(x) => { print(*x); }, _ => { print(v.len()); } }
            drop(-> v);
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '1\n'), run.stderr)
        self.assertEqual(run.stderr.count('destroy saved=4'), 1)

    def test_immediate_handle_vector_match_cleans_wildcard_payloads(self):
        run = self.native("""
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            match <- v.try_push(-> p.new(4)) {
                Err(x) => { print(*x); },
                _ => { print(v.len()); }
            }
            let replaced = match <- v.replace(0, -> q.new(8)) {
                Ok(old) => { drop(-> old); let reused = p.new(7); *reused },
                Err(rejected) => { drop(-> rejected); let reused = p.new(7); *reused }
            };
            print(replaced);
            let rejected = match <- v.replace(9, -> p.new(6)) {
                Ok(x) => { *x },
                Err(rejected) => { drop(-> rejected); let reused = p.new(9); *reused }
            };
            print(rejected);
            match <- v.pop() {
                None => { print(0); },
                Some(value) => { drop(-> value); let reused = q.new(11); print(*reused); }
            }
            match <- v.pop() { Some(value) => { drop(-> value); print(v.len()); }, None => { print(v.len()); } }
        """)
        self.assertEqual((run.returncode, run.stdout), (0, '1\n7\n9\n11\n0\n'), run.stderr)
        for value in ('4', '8', '6'):
            self.assertEqual(sum(line.endswith('=' + value) for line in run.stderr.splitlines()
                                 if line.startswith('destroy ')), 1)

    def test_immediate_handle_replace_expression_transfers_selected_allocation(self):
        source = """
            fn run(index: Int) {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut v = vp.new();
                let old = p.new(4);
                let incoming = q.new(8);
                address(old);
                address(incoming);
                v.push(-> old);
                let selected = match <- v.replace(index, -> incoming) {
                    Ok(item) => { <- item },
                    Err(item) => { <- item }
                };
                drop(-> v);
                address(selected);
                print(*selected);
            }
            run(0);
            run(9);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        a, _, success, old, _, b, failure, incoming = run.stdout.splitlines()
        self.assertEqual((success, failure, old, incoming), (a, b, '4', '8'))
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('address(selected);', f'{pool}.reset(); address(selected);'))
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(source.replace('Err(item) => { <- item }', 'Err(item) => { drop(-> item); 0 }'))

    def test_buffered_handle_try_push_cleans_only_rejected_handle(self):
        run = self.native("""
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(131072);
            let mut q = pool<Int>(1);
            #(directive, stack_region_max_size=1M) {
                let mut v = vp.new();
                let success: Result<(), A<Int>> = if true { <- v.try_push(-> p.new(4)) }
                              else { <- v.try_push(-> p.new(5)) };
                drop(-> success);
                print(v.len());
                let mut i = 1;
                while i < 131072 {
                    v.push(-> p.new(i));
                    i = i + 1;
                }
                let incoming = q.new(37);
                address(incoming);
                let rejected = <- v.try_push(-> incoming);
                print(v.len());
                match (-> rejected) {
                    Ok(()) => { print(0); },
                    Err(x) => { address(x); print(*x); }
                }
                let reused = q.new(38);
                address(reused);
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        first, original, length, returned, value, reused = run.stdout.splitlines()
        self.assertEqual((first, length, value), ('1', '131072', '37'))
        self.assertEqual((returned, reused), (original, original))
        self.assertEqual(run.stderr.count('destroy incoming=37'), 1)

    def test_handle_vector_push_transfers_cleanup_to_vector(self):
        run = self.native("""
            let mut vectors = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vectors.new();
            let first: A<Int> = p.new(10);
            address(first);
            v.push(-> first);
            let second = q.new(20);
            address(second);
            v.push(-> second);
            print(v.len());
            drop(-> v);
            let a = p.new(30);
            let b = q.new(40);
            address(a);
            address(b);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, length, reused_p, reused_q = run.stdout.splitlines()
        self.assertEqual((reused_p, reused_q, length), (first, second, '2'))
        self.assertEqual(run.stderr.splitlines()[:6], [
            'destroy second=20', 'reclaim second', 'destroy first=10', 'reclaim first',
            'destroy v=0', 'reclaim v',
        ])

    def test_handle_vector_push_rejects_early_pool_reset_and_invalid_transfer(self):
        prefix = """
            fn clear(p: &mut Pool<Int>) { p.reset(); }
            let mut vectors = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut v = vectors.new();
        """
        for body, error in (
            ('let x = p.new(1); v.push(x);', 'transfert explicite'),
            ('let x = p.new(1); v.push(-> x); print(*x);', 'plus utilisable'),
            ('{ let mut short = pool<Int>(1); v.push(-> short.new(1)); }', 'doit survivre'),
            ('if true { v.push(-> p.new(1)); } p.reset();', 'handles encore stockés'),
            ('v.push(-> p.new(1)); clear(&mut p);', 'handles encore stockés'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_handle_vector_push_tracks_injected_origins_across_calls(self):
        source = """
            fn clear(p: &mut Pool<Int>) { p.reset(); }
            fn store(a: -> A<Int>, p: &mut Pool<Int>) {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                v.push(-> a);
                clear(p);
                print(v.len());
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(10);
            address(a);
            store(-> a, &mut q);
            let reused = p.new(20);
            address(reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, length, reused = run.stdout.splitlines()
        self.assertEqual((length, reused), ('1', original))
        self.assertEqual(run.stderr.splitlines().count('destroy a=10'), 1)
        for reset in ('clear(p);', 'p.reset();'):
            with self.subTest(reset=reset), self.assertRaisesRegex(Error, 'sources distinctes'):
                verify_program(source.replace('clear(p);', reset).replace('&mut q);', '&mut p);'))

    def test_handle_vector_borrowed_slot_replacement_tracks_injected_origin(self):
        source = """
            fn replace_slot(a: -> A<Int>, p: &mut Pool<Int>) {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut old = pool<Int>(1);
                let mut v = vp.new();
                v.push(-> old.new(7));
                let h = &mut v[0];
                *h = <- a;
                old.reset();
                p.reset();
                let extracted = <- v.remove(0);
                address(extracted);
                print(*extracted);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(13);
            address(a);
            replace_slot(-> a, &mut q);
            let reused = p.new(19);
            address(reused);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, extracted, value, reused = run.stdout.splitlines()
        self.assertEqual((extracted, value, reused), (original, '13', original))
        self.assertEqual(run.stderr.count('destroy a=13'), 1)
        with self.assertRaisesRegex(Error, 'sources distinctes'):
            verify_program(source.replace('replace_slot(-> a, &mut q)', 'replace_slot(-> a, &mut p)'))

    def test_handle_vector_remove_preserves_identity_and_frees_origin_after_drop(self):
        prefix = """
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            let x = p.new(10);
            let y = q.new(20);
            address(x);
            address(y);
            v.push(-> x);
            v.push(-> y);
        """
        run = self.native(prefix + """
            let a: A<Int> = <- v.remove(0);
            address(a);
            print(*a);
            drop(-> a);
            p.reset();
            let b: A<Int> = <- v.remove(0);
            address(b);
            print(*b);
            drop(-> b);
            q.reset();
            print(v.len());
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, removed_first, a, removed_second, b, length = run.stdout.splitlines()
        self.assertEqual((removed_first, removed_second), (first, second))
        self.assertEqual((a, b, length), ('10', '20', '0'))
        for body, error in (
            ('let a = v.remove(0); print(*a);', 'transfert <- explicite'),
            ('let a = <- v.remove(0); p.reset(); print(*a);', 'reset interdit'),
            ('let a = <- v.remove(0); q.reset(); print(*a);', 'handles encore stockés'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)
        failed = self.native(prefix + 'let a = <- v.remove(2); print(*a);')
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn('indice de Vector hors limites', failed.stderr)

    def test_handle_vector_remove_dynamic_index_inside_function(self):
        run = self.native("""
            fn read(i: Int) -> Int {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut v = vp.new();
                v.push(-> p.new(10));
                v.push(-> q.new(20));
                let removed = <- v.remove(i);
                return *removed;
            }
            print(read(1));
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '20\n')

    def test_handle_vector_cell_borrows_keep_the_slot_and_its_vector_alive(self):
        prefix = """
            fn compare(h: &A<Int>, p: &mut Pool<Int>) -> bool {
                let expected = p.new(20);
                return expected.vequals(h);
            }
            let mut vp = pool<Vector<A<Int>>>(2);
            let mut p = pool<Int>(2);
            let mut q = pool<Int>(1);
            let mut low = vp.new();
            let mut high = vp.new();
            low.push(-> p.new(10));
            high.push(-> p.new(20));
        """
        run = self.native(prefix + """
            let h = &high[0];
            if compare(h, &mut q) { print(1); }
            let exclusive = &mut high[0];
            if compare(exclusive, &mut q) { print(2); }
            let a = <- high.remove(0);
            print(*a);
            print(low.len());
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n2\n20\n1\n')
        for body, error in (
            ('let h = high[0];', 'emprunt explicite'),
            ('let h = &high[0]; let x = <- high.remove(0); if compare(h, &mut q) {}', 'emprunt actif'),
            ('let h = &mut high[0]; print(high.len()); if compare(h, &mut q) {}', 'emprunt actif'),
            ('let h = &high[0]; p.reset(); if compare(h, &mut q) {}', 'handles encore stockés'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)
        failed = self.native(prefix + 'if compare(&high[1], &mut q) {}')
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn('indice de Vector hors limites', failed.stderr)

    def test_handle_vector_distinct_literal_slots_allow_two_mutable_loans(self):
        prefix = """
            fn both(a: &mut A<Int>, b: &mut A<Int>, p: &mut Pool<Int>) -> bool {
                let expected = p.new(7);
                if expected.vequals(b) { return false; }
                return expected.vequals(a);
            }
            fn index() -> Int { return 1; }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(2);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(7));
            v.push(-> p.new(9));
        """
        run = self.native(prefix + """
            let a = &mut v[0];
            let b = &mut v[1];
            if both(a, b, &mut q) { print(1); }
            let removed = <- v.remove(1);
            print(*removed);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n9\n')
        for second in ('0', 'index()'):
            with self.subTest(second=second), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(prefix + f'let a = &mut v[0]; let b = &mut v[{second}];'
                               + 'if both(a, b, &mut q) {}')

    def test_handle_vector_replace_through_borrow_keeps_disjoint_case(self):
        prefix = """
            fn payload() -> Int {
                let mut temps = pool<Int>(1);
                let marker = temps.new(30);
                return *marker;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(2);
            let mut r = pool<Int>(1);
            let mut v = vp.new();
            let first = p.new(10);
            let second = q.new(20);
            v.push(-> first);
            v.push(-> second);
        """
        run = self.native(prefix + """
            let a = &mut v[0];
            let b = &v[1];
            *a = <- r.new(payload());
            p.reset();
            let witness = q.new(20);
            if witness.vequals(b) { print(1); }
            let result = <- v.remove(0);
            print(*result);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n30\n')
        self.assertEqual(run.stderr.splitlines()[:5],
                         ['destroy marker=30', 'reclaim marker', 'destroy first=10', 'reclaim first', 'reset'])
        for body, error in (
            ('let h = &v[0]; *h = <- r.new(30);', 'immuable'),
            ('let h = &mut v[0]; *h = 30;', 'transfert <- explicite'),
            ('let h = &mut v[0]; *h = <- r.new(30); r.reset();', 'handles encore stockés'),
            ('let h = &mut v[0]; { let mut short = pool<Int>(1); *h = <- short.new(30); }', 'doit survivre'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_handle_vector_transfers_preserve_cases_across_blocks_and_loop(self):
        run = self.native("""
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = loop {
                let mut local = vp.new();
                local.push(-> p.new(10));
                address(local);
                break <- local;
            };
            {
                v ->;
                v.push(-> q.new(20));
                <- v;
            }
            address(v);
            let first = <- v.remove(0);
            print(*first);
            drop(-> first);
            p.reset();
            let second = <- v.remove(0);
            print(*second);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        before, after, first, second = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual((first, second), ('10', '20'))

    def test_handle_vector_transfers_retain_pool_requirements_at_joins(self):
        prefix = """
            let mut vp = pool<Vector<A<Int>>>(2);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
        """
        for body, error in (
            ("""let v = { let mut short = pool<Int>(1); let mut local = vp.new();
                    local.push(-> short.new(10)); <- local }; print(v.len());""",
             'pool d’élément ne survit pas'),
            ("""let v = if true {
                    let mut a = vp.new(); a.push(-> p.new(1)); <- a
                } else {
                    let mut b = vp.new(); b.push(-> q.new(2)); <- b
                };
                q.reset(); print(v.len());""", 'handles encore stockés'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_shared_handle_vector_signature_relays_a_case_borrow(self):
        prefix = """
            fn pick(a: &Vector<A<Int>>, b: &Vector<A<Int>>, n: Int) -> &A<Int> {
                if n == 0 { return &a[0]; }
                return &b[0];
            }
            fn relay(a: &Vector<A<Int>>, b: &Vector<A<Int>>) -> &A<Int> {
                return pick(a, b, 0);
            }
            let mut vp = pool<Vector<A<Int>>>(2);
            let mut p = pool<Int>(3);
            let mut a = vp.new();
            let mut b = vp.new();
            a.push(-> p.new(7));
            b.push(-> p.new(9));
            let witness = p.new(7);
            let h = relay(&a, &b);
        """
        run = self.native(prefix + """
            if witness.vequals(h) { print(1); }
            let x = <- a.remove(0);
            let y = <- b.remove(0);
            print(*x);
            print(*y);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '1\n7\n9\n')
        for vector in ('a', 'b'):
            with self.subTest(vector=vector), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(prefix + f'let x = <- {vector}.remove(0); if witness.vequals(h) {{}}')

    def test_shared_handle_vector_signature_rejects_escape_and_mutation(self):
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn escape() -> &A<Int> {
                    let mut vp = pool<Vector<A<Int>>>(1);
                    let mut p = pool<Int>(1);
                    let mut v = vp.new();
                    v.push(-> p.new(7));
                    return &v[0];
                }
            """)
        with self.assertRaisesRegex(Error, 'lecture'):
            verify_program("""
                fn invalid(v: &Vector<A<Int>>) {
                    let x = <- v.remove(0);
                    print(*x);
                }
            """)

    def test_mutable_handle_vector_signature_returns_case_for_caller_replacement(self):
        prefix = """
            fn pick(v: &mut Vector<A<Int>>, i: Int) -> &mut A<Int> { return &mut v[i]; }
            fn relay(v: &mut Vector<A<Int>>) -> &mut A<Int> { return pick(v, 0); }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(7));
            let h = relay(&mut v);
        """
        run = self.native(prefix + """
            *h = <- q.new(9);
            p.reset();
            let x = <- v.remove(0);
            print(*x);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '9\n')
        for body, diagnostic in (
            ('print(v.len()); *h = <- q.new(9);', 'emprunt actif'),
            ('drop(-> v); *h = <- q.new(9);', 'emprunt encore utilisé'),
            ('p.reset(); *h = <- q.new(9);', 'handles encore stockés'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program(prefix + body)
        with self.assertRaisesRegex(Error, 'paramètre mutable'):
            verify_program('fn bad(v: &Vector<A<Int>>) -> &mut A<Int> { return &mut v[0]; }')

    def test_owned_handle_vectors_preserve_possible_item_pools_at_call(self):
        prefix = """
            fn choose(a: -> Vector<A<Int>>, b: -> Vector<A<Int>>, i: Int) -> <- Vector<A<Int>> {
                if i == 0 { return <- a; }
                return <- b;
            }
            fn relay(v: -> Vector<A<Int>>) -> <- Vector<A<Int>> { return <- v; }
            let mut vp = pool<Vector<A<Int>>>(2);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut a = vp.new();
            let mut b = vp.new();
            a.push(-> p.new(7));
            b.push(-> q.new(9));
            address(b);
            let mut returned = relay(-> choose(-> a, -> b, 1));
        """
        run = self.native(prefix + """
            address(returned);
            let n = <- returned.remove(0);
            print(*n);
            drop(-> n);
            p.reset();
            q.reset();
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, value = run.stdout.splitlines()
        self.assertEqual(original, returned)
        self.assertEqual(value, '9')
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(prefix + f'{pool}.reset(); print(returned.len());')

    def test_owned_handle_vector_can_be_consumed_and_dropped_in_function(self):
        run = self.native("""
            fn dispose(v: -> Vector<A<Int>>) { drop(-> v); }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(7));
            dispose(-> v);
            let reused = p.new(11);
            print(*reused);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '11\n')

    def test_handle_vector_pop_match_cleans_only_the_extracted_handle(self):
        run = self.native("""
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            match <- v.pop() {
                Some(a) => { print(*a); },
                None => { print(0); }
            }
            let a = p.new(7);
            let b = q.new(9);
            address(b);
            v.push(-> a);
            v.push(-> b);
            match <- v.pop() {
                Some(last) => { address(last); print(*last); },
                None => { print(0); }
            }
            q.reset();
            print(v.len());
            match <- v.pop() {
                Some(last) => { drop(-> last); },
                None => { print(0); }
            }
            print(v.len());
            drop(-> v);
            p.reset();
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        empty, address, extracted, value, remaining, final = run.stdout.splitlines()
        self.assertEqual(address, extracted)
        self.assertEqual((empty, value, remaining, final), ('0', '9', '1', '0'))
        self.assertEqual(run.stderr.count('destroy b=9'), 1)
        self.assertEqual(run.stderr.count('destroy a=7'), 1)

    def test_handle_vector_pop_match_requires_transfer_and_exclusivity(self):
        prefix = """
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(2);
            let mut v = vp.new();
            v.push(-> p.new(7));
        """
        for body, diagnostic in (
            ('match v.pop() { Some(a) => {}, None => {} }', 'méthode inconnue'),
            ('match <- v.pop() { Some(a) => {}, None => {}, _ => {} }', 'bras _ inaccessible'),
            ('let h = &v[0]; match <- v.pop() { Some(a) => {}, None => {} } '
             'let a = p.new(7); if a.vequals(h) {}', 'emprunt actif'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program(prefix + body)

    def test_handle_vector_replace_match_returns_old_or_incoming(self):
        run = self.native("""
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            let first = p.new(7);
            address(first);
            v.push(-> first);
            let rejected = q.new(8);
            address(rejected);
            match <- v.replace(1, -> rejected) {
                Ok(old) => { drop(-> old); print(0); },
                Err(value) => { address(value); print(*value); }
            }
            match <- v.replace(0, -> q.new(9)) {
                Ok(old) => { address(old); print(*old); drop(-> old); p.reset(); },
                Err(value) => { print(*value); }
            }
            let result = <- v.remove(0);
            print(*result);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, rejected, error_address, error_value, old_address, old_value, current = run.stdout.splitlines()
        self.assertEqual((error_address, old_address), (rejected, first))
        self.assertEqual((error_value, old_value, current), ('8', '7', '9'))

    def test_handle_vector_exchanges_track_injected_origin_in_both_arms(self):
        prefix = """
            fn clear(p: &mut Pool<Int>) { p.reset(); }
            fn exchange(a: -> A<Int>, p: &mut Pool<Int>, index: Int) {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut original = pool<Int>(1);
                let mut v = vp.new();
                v.push(-> original.new(7));
                OPERATION
                print(v.len());
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(13);
            address(a);
            exchange(-> a, &mut q, 0);
            let b = p.new(17);
            address(b);
            exchange(-> b, &mut q, 1);
            let reused = p.new(19);
            address(reused);
        """
        for operation, output in (
            ("""match <- v.replace(index, -> a) {
                Ok(old) => { clear(p); print(*old); },
                Err(rejected) => { clear(p); print(*rejected); }
            }""", ('7', '1', '17', '1')),
            ("""match <- v.try_push(-> a) {
                Ok(()) => { clear(p); print(1); },
                Err(rejected) => { clear(p); print(*rejected); }
            }""", ('1', '2', '1', '2')),
        ):
            with self.subTest(operation=operation):
                source = prefix.replace('OPERATION', operation)
                run = self.native(source)
                self.assertEqual(run.returncode, 0, run.stderr)
                first, out1, len1, second, out2, len2, reused = run.stdout.splitlines()
                self.assertEqual((first, second), (reused, reused))
                self.assertEqual((out1, len1, out2, len2), output)
                self.assertEqual(run.stderr.count('destroy a=13'), 1)
                self.assertEqual(run.stderr.count('destroy b=17'), 1)
                for arm in ('Ok', 'Err'):
                    safe_arm = 'Err' if arm == 'Ok' else 'Ok'
                    lines = [line.replace('clear(p);', '') if safe_arm + '(' in line else line
                             for line in operation.splitlines()]
                    aliased = prefix.replace('OPERATION', '\n'.join(lines)).replace('&mut q,', '&mut p,')
                    with self.subTest(arm=arm), self.assertRaisesRegex(Error, 'sources distinctes'):
                        verify_program(aliased)

    def test_handle_vector_extraction_returns_injected_handle(self):
        variants = {
            'remove': 'let got = <- v.remove(0); return <- got;',
            'pop': """
                match <- v.pop() {
                    Some(got) => { return <- got; },
                    None => { loop {} }
                }
            """,
            'replace': """
                match <- v.replace(0, -> q.new(17)) {
                    Ok(got) => { return <- got; },
                    Err(rejected) => { drop(-> rejected); loop {} }
                }
            """,
        }
        for operation, body in variants.items():
            with self.subTest(operation=operation):
                prefix = """
                    fn extract(a: -> A<Int>, q: &mut Pool<Int>) -> <- A<Int> {
                        let mut vp = pool<Vector<A<Int>>>(1);
                        let mut v = vp.new();
                        v.push(-> a);
                """ + body + """
                    }
                    let mut p = pool<Int>(1);
                    let mut q = pool<Int>(1);
                    let a = p.new(13);
                    address(a);
                    let got = extract(-> a, &mut q);
                """
                run = self.native(prefix + """
                    address(got);
                    print(*got);
                    drop(-> got);
                    let reused = p.new(31);
                    address(reused);
                    let other = q.new(37);
                    print(*other);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                original, returned, value, reused, other = run.stdout.splitlines()
                self.assertEqual((returned, reused, value, other), (original, original, '13', '37'))
                with self.assertRaisesRegex(Error, 'got.*doit encore être utilisé'):
                    verify_program(prefix + 'p.reset(); print(*got);')
                with self.assertRaisesRegex(Error, 'ne survit pas'):
                    verify_program(prefix.replace('v.push(-> a);', """
                        let mut local = pool<Int>(1);
                        v.push(-> local.new(23));
                    """))

    def test_owned_handle_vector_parameter_can_return_an_element(self):
        template = """
            fn take(mut v: -> Vector<A<Int>>, target: &mut Pool<Int>) -> <- A<Int> {
                target.reset();
                EXTRACT
            }
            fn relay(v: -> Vector<A<Int>>, target: &mut Pool<Int>) -> <- A<Int> {
                let item = take(-> v, target);
                return <- item;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut scratch = pool<Int>(1);
            let mut v = vp.new();
            let a = p.new(13);
            let b = q.new(17);
            address(a);
            address(b);
            v.push(-> a);
            v.push(-> b);
            let result = relay(-> v, &mut scratch);
        """
        for extraction, selected, expected, pool, unrelated in (
            ('let item = <- v.remove(0); return <- item;', 0, '13', 'p', 'q'),
            ('let first = <- v.remove(0); drop(-> first); let item = <- v.remove(0); return <- item;',
             1, '17', 'q', 'p'),
            ('match <- v.pop() { Some(item) => { return <- item; }, None => { loop {} } }',
             1, '17', 'q', 'p'),
            ('let old = <- v.remove(1); drop(-> old); '
             'match <- v.pop() { Some(item) => { return <- item; }, None => { loop {} } }',
             0, '13', 'p', 'q'),
            ('''match <- v.pop() {
                Some(old) => {
                    drop(-> old);
                    match <- v.pop() {
                        Some(item) => { return <- item; },
                        None => { loop {} }
                    }
                },
                None => { loop {} }
            }''', 0, '13', 'p', 'q'),
        ):
            with self.subTest(extraction=extraction):
                source = template.replace('EXTRACT', extraction)
                reset = f'{unrelated}.reset();' if unrelated is not None else ''
                run = self.native(source + reset + """
                    address(result);
                    print(*result);
                    drop(-> result);
                    let pa = p.new(19);
                    let qb = q.new(23);
                    address(pa);
                    address(qb);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                a, b, result, value, pa, qb = run.stdout.splitlines()
                self.assertEqual((result, value, pa, qb), ((a, b)[selected], expected, a, b))
                self.assertEqual(run.stderr.count('destroy a=13'), 1)
                self.assertEqual(run.stderr.count('destroy b=17'), 1)
                with self.assertRaisesRegex(Error, 'doit encore être utilisé'):
                    verify_program(source + f'{pool}.reset(); print(*result);')
                with self.assertRaisesRegex(Error, 'sources distinctes'):
                    verify_program(source.replace('&mut scratch', '&mut p') + 'print(*result);')

    def test_handle_vector_push_through_borrow_updates_caller(self):
        template = """
            fn append(v: &mut Vector<A<Int>>, a: -> A<Int>) {
                v.push(-> a);
            }
            fn relay(v: &mut Vector<A<Int>>, a: -> A<Int>) {
                append(v, -> a);
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(13));
            let a = q.new(17);
            address(a);
            relay(&mut v, -> a);
        """
        run = self.native(template + """
            let item = <- v.remove(1);
            drop(-> v);
            p.reset();
            address(item);
            print(*item);
            drop(-> item);
            let reused = q.new(23);
            address(reused);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        original, returned, value, reused = run.stdout.splitlines()
        self.assertEqual((returned, value, reused), (original, '17', original))
        self.assertEqual(run.stderr.count('destroy a=17'), 1)
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(template + 'q.reset(); print(v.len());')
        shorter = template[:template.index('let a = q.new(17);')] + """
            {
                let mut local = pool<Int>(1);
                let a = local.new(17);
                relay(&mut v, -> a);
            }
            print(v.len());
        """
        with self.assertRaisesRegex(Error, 'pool d’élément ne survit pas'):
            verify_program(shorter)

    def test_handle_vector_optional_push_through_borrow_keeps_possible_pool(self):
        template = """
            fn append(v: &mut Vector<A<Int>>, a: -> A<Int>, flag: Int) {
                WRITE
            }
            fn relay(v: &mut Vector<A<Int>>, a: -> A<Int>, flag: Int) {
                append(v, -> a, flag);
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(13));
            let a = q.new(17);
            address(a);
            relay(&mut v, -> a, FLAG);
        """
        for write, flag, length in (
            ('if flag == 0 { a ->; v.push(-> a); }', 0, '2'),
            ('if flag == 0 { a ->; v.push(-> a); }', 1, '1'),
            ('match <- v.try_push(-> a) { Ok(()) => {}, Err(item) => { drop(-> item); } }', 0, '2'),
        ):
            with self.subTest(write=write, flag=flag):
                source = template.replace('WRITE', write).replace('FLAG', str(flag))
                run = self.native(source + """
                    print(v.len());
                    drop(-> v);
                    let reused = q.new(23);
                    address(reused);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                original, actual, reused = run.stdout.splitlines()
                self.assertEqual((actual, reused), (length, original))
                self.assertEqual(run.stderr.count('destroy a=17'), 1)
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(source + 'q.reset(); print(v.len());')

    def test_handle_vector_replacement_through_borrow_updates_caller(self):
        template = """
            fn update(v: &mut Vector<A<Int>>, a: -> A<Int>) {
                WRITE
            }
            fn relay(v: &mut Vector<A<Int>>, a: -> A<Int>) {
                update(v, -> a);
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(13));
            let a = q.new(17);
            address(a);
            relay(&mut v, -> a);
        """
        for write in (
            'let slot = &mut v[0]; *slot = <- a;',
            'match <- v.replace(0, -> a) { Ok(old) => { drop(-> old); }, Err(rejected) => { drop(-> rejected); loop {} } }',
        ):
            with self.subTest(write=write):
                source = template.replace('WRITE', write)
                run = self.native(source + """
                    p.reset();
                    let item = <- v.remove(0);
                    address(item);
                    print(*item);
                    drop(-> item);
                    let reused = q.new(23);
                    address(reused);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                original, returned, value, reused = run.stdout.splitlines()
                self.assertEqual((returned, value, reused), (original, '17', original))
                self.assertEqual(run.stderr.count('destroy a=17'), 1)
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(source + 'q.reset(); print(v.len());')
        uncertain = template.replace('WRITE',
            'match <- v.replace(0, -> a) { Ok(old) => { drop(-> old); }, Err(item) => { drop(-> item); } }')
        with self.assertRaisesRegex(Error, 'handles encore stockés'):
            verify_program(uncertain + 'p.reset(); print(v.len());')

    def test_handle_vector_extract_through_borrow_updates_caller(self):
        template = """
            fn take(v: &mut Vector<A<Int>>) -> <- A<Int> {
                TAKE
            }
            fn relay(v: &mut Vector<A<Int>>) -> <- A<Int> {
                let item = take(v);
                return <- item;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            let first = p.new(13);
            let last = q.new(17);
            address(first);
            address(last);
            v.push(-> first);
            v.push(-> last);
            let item = relay(&mut v);
        """
        for take, index, removed, retained, value in (
            ('let item = <- v.remove(0); return <- item;', 0, 'p', 'q', '13'),
            ('match <- v.pop() { Some(item) => { return <- item; }, None => { loop {} } }',
             1, 'q', 'p', '17'),
        ):
            with self.subTest(take=take):
                source = template.replace('TAKE', take)
                run = self.native(source + """
                    address(item);
                    print(*item);
                    drop(-> item);
                """ + f'{removed}.reset();' + """
                    let remaining = <- v.remove(0);
                    address(remaining);
                    print(*remaining);
                    drop(-> remaining);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                first, last, extracted, read, remaining, final = run.stdout.splitlines()
                self.assertEqual((extracted, read, remaining, final),
                                 ((first, last)[index], value, (last, first)[index], ('17', '13')[index]))
                self.assertEqual(run.stderr.count('destroy first=13'), 1)
                self.assertEqual(run.stderr.count('destroy last=17'), 1)
                with self.assertRaisesRegex(Error, 'item.*doit encore être utilisé'):
                    verify_program(source + f'{removed}.reset(); print(*item);')
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(source + f'{retained}.reset(); print(v.len()); print(*item);')

    def test_owned_handle_vector_consumed_after_writing_slots(self):
        template = """
            fn consume(mut v: -> Vector<A<Int>>, a: -> A<Int>, target: &mut Pool<Int>) {
                WRITE
                target.reset();
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut scratch = pool<Int>(1);
            let mut v = vp.new();
            let old = p.new(13);
            let a = q.new(17);
            address(old);
            address(a);
            v.push(-> old);
            consume(-> v, -> a, &mut TARGET);
            let pa = p.new(19);
            let qb = q.new(23);
            address(pa);
            address(qb);
        """
        for write in (
            'v.push(-> a);',
            'match <- v.try_push(-> a) { Ok(()) => {}, Err(item) => { drop(-> item); } }',
            'match <- v.replace(0, -> a) { Ok(item) => { drop(-> item); }, Err(item) => { drop(-> item); } }',
            'let slot = &mut v[0]; *slot = <- a;',
        ):
            with self.subTest(write=write):
                source = template.replace('WRITE', write)
                run = self.native(source.replace('TARGET', 'scratch'))
                self.assertEqual(run.returncode, 0, run.stderr)
                old, new, pa, qb = run.stdout.splitlines()
                self.assertEqual((pa, qb), (old, new))
                self.assertEqual(run.stderr.count('destroy old=13'), 1)
                self.assertEqual(run.stderr.count('destroy a=17'), 1)
                with self.assertRaisesRegex(Error, 'sources distinctes'):
                    verify_program(source.replace('TARGET', 'q'))
        with self.assertRaisesRegex(Error, 'pool de l’élément doit survivre'):
            verify_program("""
                fn invalid(mut v: -> Vector<A<Int>>) {
                    {
                        let mut short = pool<Int>(1);
                        v.push(-> short.new(13));
                    }
                }
            """)

    def test_owned_handle_vector_return_keeps_inserted_parameter_pool(self):
        template = """
            fn update(mut v: -> Vector<A<Int>>, a: -> A<Int>) -> <- Vector<A<Int>> {
                WRITE
                return <- v;
            }
            fn relay(v: -> Vector<A<Int>>, a: -> A<Int>) -> <- Vector<A<Int>> {
                let updated = update(-> v, -> a);
                return <- updated;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            let old = p.new(13);
            v.push(-> old);
            let a = q.new(17);
            address(a);
            let mut updated = relay(-> v, -> a);
        """
        for write, index in (
            ('v.push(-> a);', 1),
            ('match <- v.try_push(-> a) { Ok(()) => {}, Err(item) => { drop(-> item); } }', 1),
            ('match <- v.replace(0, -> a) { Ok(item) => { drop(-> item); }, Err(item) => { drop(-> item); } }', 0),
            ('let slot = &mut v[0]; *slot = <- a;', 0),
        ):
            with self.subTest(write=write):
                source = template.replace('WRITE', write)
                extraction = f'let item = <- updated.remove({index}); drop(-> updated);'
                reset_old_pool = 'p.reset();' if write == 'v.push(-> a);' else ''
                run = self.native(source + extraction + reset_old_pool + """
                    address(item);
                    print(*item);
                    drop(-> item);
                    let reused = q.new(23);
                    address(reused);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                original, returned, value, reused = run.stdout.splitlines()
                self.assertEqual((returned, value, reused), (original, '17', original))
                self.assertEqual(run.stderr.count('destroy old=13'), 1)
                self.assertEqual(run.stderr.count('destroy a=17'), 1)
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(source + 'q.reset(); print(updated.len());')
                with self.assertRaisesRegex(Error, 'item.*doit encore être utilisé'):
                    verify_program(source + extraction + 'q.reset(); print(*item);')

        with self.assertRaisesRegex(Error, 'écriture sans source durable'):
            verify_program("""
                fn escape(mut v: -> Vector<A<Int>>) -> <- Vector<A<Int>> {
                    let mut local = pool<Int>(1);
                    v.push(-> local.new(17));
                    return <- v;
                }
            """)

    def test_returned_handle_vector_keeps_unmodified_slot_positions(self):
        template = """
            fn update(mut v: -> Vector<A<Int>>, a: -> A<Int>) -> <- Vector<A<Int>> {
                WRITE
                return <- v;
            }
            fn relay(v: -> Vector<A<Int>>, a: -> A<Int>) -> <- Vector<A<Int>> {
                let result = update(-> v, -> a);
                return <- result;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut r = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(13));
            let neighbor = r.new(19);
            address(neighbor);
            v.push(-> neighbor);
            let incoming = q.new(17);
            address(incoming);
            let mut updated = relay(-> v, -> incoming);
            p.reset();
        """
        for write in (
            'let slot = &mut v[0]; *slot = <- a;',
            'match <- v.replace(0, -> a) { Ok(old) => { drop(-> old); }, Err(rejected) => { drop(-> rejected); loop {} } }',
        ):
            with self.subTest(write=write):
                source = template.replace('WRITE', write)
                run = self.native(source + """
                    let unchanged = <- updated.remove(1);
                    let inserted = <- updated.remove(0);
                    drop(-> updated);
                    address(inserted);
                    print(*inserted);
                    drop(-> inserted);
                    q.reset();
                    address(unchanged);
                    print(*unchanged);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                neighbor, incoming, inserted, first, unchanged, second = run.stdout.splitlines()
                self.assertEqual((inserted, first, unchanged, second), (incoming, '17', neighbor, '19'))
                for pool in ('q', 'r'):
                    with self.assertRaisesRegex(Error, 'handles encore stockés'):
                        verify_program(source + f'{pool}.reset(); print(updated.len());')

    def test_handle_vector_join_forgets_removed_identity_in_same_pool(self):
        template = """
            fn take(a: -> A<Int>, b: -> A<Int>, fallback: -> A<Int>, p: &mut Pool<Int>, flag: Int) -> <- A<Int> {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut v = vp.new();
                v.push(-> a);
                v.push(-> b);
                let gone = <- v.remove(1);
                p.drop(-> gone);
                if flag == 0 {
                    let first = <- v.remove(0);
                    p.drop(-> first);
                }
                match <- v.pop() {
                    Some(item) => { return <- item; },
                    None => { fallback ->; return <- fallback; }
                }
            }
            let mut p = pool<Int>(2);
            let mut q = pool<Int>(1);
            let a = p.new(13);
            let b = p.new(17);
            let fallback = q.new(19);
            address(a);
            address(fallback);
            let item = take(-> a, -> b, -> fallback, &mut p, FLAG);
        """
        for flag, expected, pool in ((0, '19', 'q'), (1, '13', 'p')):
            with self.subTest(flag=flag):
                source = template.replace('FLAG', str(flag))
                run = self.native(source + 'address(item); print(*item); drop(-> item);')
                self.assertEqual(run.returncode, 0, run.stderr)
                original, fallback, returned, value = run.stdout.splitlines()
                self.assertEqual((returned, value), ((fallback, original)[flag], expected))
                self.assertEqual(run.stderr.count('destroy b=17'), 1)
                with self.assertRaisesRegex(Error, 'item.*doit encore être utilisé'):
                    verify_program(source + f'{pool}.reset(); print(*item);')

    def test_handle_vector_return_shifts_replaced_slot_after_removal(self):
        template = """
            fn update(mut v: -> Vector<A<Int>>, a: -> A<Int>) -> <- Vector<A<Int>> {
                let slot = &mut v[1];
                *slot = <- a;
                INNER_REMOVAL
                return <- v;
            }
            fn relay(v: -> Vector<A<Int>>, a: -> A<Int>) -> <- Vector<A<Int>> {
                let mut result = update(-> v, -> a);
                OUTER_REMOVAL
                return <- result;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(2);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(13));
            v.push(-> p.new(19));
            let a = q.new(17);
            address(a);
            let mut updated = relay(-> v, -> a);
            p.reset();
        """
        for inner in (True, False):
            with self.subTest(inner=inner):
                source = template.replace('INNER_REMOVAL',
                    'let old = <- v.remove(0); drop(-> old);' if inner else '').replace('OUTER_REMOVAL',
                    '' if inner else 'let old = <- result.remove(0); drop(-> old);')
                run = self.native(source + """
                    let item = <- updated.remove(0);
                    address(item);
                    print(*item);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                original, received, value = run.stdout.splitlines()
                self.assertEqual((received, value), (original, '17'))
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(source + 'q.reset(); print(updated.len());')

    def test_handle_vector_return_merges_replacements_per_slot(self):
        template = """
            fn update(mut v: -> Vector<A<Int>>, a: -> A<Int>, b: -> A<Int>, flag: Int) -> <- Vector<A<Int>> {
                if flag == 0 {
                    a ->;
                    let slot = &mut v[0];
                    *slot = <- a;
                } else {
                    b ->;
                    let slot = &mut v[OTHER_INDEX];
                    *slot = <- b;
                }
                return <- v;
            }
            fn relay(v: -> Vector<A<Int>>, a: -> A<Int>, b: -> A<Int>, flag: Int) -> <- Vector<A<Int>> {
                let result = update(-> v, -> a, -> b, flag);
                return <- result;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut r = pool<Int>(1);
            let mut s = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(13));
            v.push(-> r.new(19));
            let a = q.new(17);
            let b = s.new(23);
            let mut result = relay(-> v, -> a, -> b, FLAG);
            let item = <- result.remove(0);
            drop(-> result);
        """
        for other_index, disjoint, values in ((0, 'p', ('17', '23')), (1, 's', ('17', '13'))):
            for flag, value in enumerate(values):
                with self.subTest(other_index=other_index, flag=flag):
                    source = template.replace('OTHER_INDEX', str(other_index)).replace('FLAG', str(flag))
                    run = self.native(source + f'{disjoint}.reset(); print(*item);')
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, value + '\n')
                    with self.assertRaisesRegex(Error, 'item.*doit encore être utilisé'):
                        verify_program(source + 'q.reset(); print(*item);')

    def test_handle_vector_return_preserves_donated_element_pool(self):
        template = """
            fn combine(mut dst: -> Vector<A<Int>>, mut donor: -> Vector<A<Int>>) -> <- Vector<A<Int>> {
                MOVE
                return <- dst;
            }
            fn relay(dst: -> Vector<A<Int>>, donor: -> Vector<A<Int>>) -> <- Vector<A<Int>> {
                let result = combine(-> dst, -> donor);
                return <- result;
            }
            let mut vp = pool<Vector<A<Int>>>(2);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut r = pool<Int>(1);
            let mut dst = vp.new();
            let mut donor = vp.new();
            dst.push(-> p.new(11));
            let first = q.new(13);
            let last = r.new(17);
            address(first);
            address(last);
            donor.push(-> first);
            donor.push(-> last);
            let mut result = relay(-> dst, -> donor);
            let donated = <- result.remove(1);
            drop(-> result);
        """
        for move, kept, discarded, index, expected in (
            ('let item = <- donor.remove(0); dst.push(-> item);', 'q', 'r', 0, '13'),
            ('match <- donor.pop() { Some(item) => { dst.push(-> item); }, None => { loop {} } }',
             'r', 'q', 1, '17'),
        ):
            with self.subTest(move=move):
                source = template.replace('MOVE', move)
                run = self.native(source + f'{discarded}.reset();' + """
                    address(donated);
                    print(*donated);
                    drop(-> donated);
                    let q_again = q.new(19);
                    let r_again = r.new(23);
                    address(q_again);
                    address(r_again);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                first, last, address, value, q_again, r_again = run.stdout.splitlines()
                self.assertEqual((address, value, q_again, r_again), ((first, last)[index], expected, first, last))
                self.assertEqual(run.stderr.count('destroy first=13'), 1)
                self.assertEqual(run.stderr.count('destroy last=17'), 1)
                with self.assertRaisesRegex(Error, 'donated.*doit encore être utilisé'):
                    verify_program(source + f'{kept}.reset(); print(*donated);')

    def test_fresh_handle_is_allowed_only_in_its_contract_slot(self):
        from dataclasses import replace
        from unittest.mock import patch
        from results import ResultCandidate, ResultContext

        source = """
            fn make(vp: &mut Pool<Vector<A<Int>>>, p: &mut Pool<Int>, a: -> A<Int>) -> <- Vector<A<Int>> {
                p.drop(-> a);
                let mut v = vp.new();
                v.push(-> p.new(17));
                v.push(-> p.new(19));
                return <- v;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(2);
            let a = p.new(13);
            let v = make(&mut vp, &mut p, -> a);
            print(v.len());
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '2\n')
        infer = ResultContext.infer

        def wrong_first_slot(context):
            summary = infer(context)
            if context.name != 'make':
                return summary
            candidates = frozenset(replace(candidate, vector_layout=(
                (ResultCandidate('parameter', 2),), *candidate.vector_layout[1:]))
                for candidate in summary.candidates)
            return replace(summary, candidates=candidates)

        with patch.object(ResultContext, 'infer', wrong_first_slot):
            with self.assertRaisesRegex(Error, 'cases restantes absentes'):
                compile_source(source)

    def test_new_handle_vector_return_keeps_element_pools(self):
        source = """
            fn make(vp: &mut Pool<Vector<A<Int>>>, a: -> A<Int>, src: &mut Pool<Int>) -> <- Vector<A<Int>> {
                let mut v = vp.new();
                v.push(-> a);
                let fresh = src.new(17);
                address(fresh);
                v.push(-> fresh);
                return <- v;
            }
            fn relay(vp: &mut Pool<Vector<A<Int>>>, a: -> A<Int>, src: &mut Pool<Int>) -> <- Vector<A<Int>> {
                let v = make(vp, -> a, src);
                return <- v;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(13);
            address(a);
            let mut v = relay(&mut vp, -> a, &mut q);
        """
        extraction = 'let first = <- v.remove(0); let second = <- v.remove(0); drop(-> v);'
        run = self.native(source + extraction + """
            address(first);
            address(second);
            print(*first);
            drop(-> first);
            p.reset();
            print(*second);
            drop(-> second);
            let p_again = p.new(19);
            let q_again = q.new(23);
            address(p_again);
            address(q_again);
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        a, fresh, first, second, value_a, value_fresh, reused_a, reused_fresh = run.stdout.splitlines()
        self.assertEqual((first, second, value_a, value_fresh, reused_a, reused_fresh),
                         (a, fresh, '13', '17', a, fresh))
        self.assertEqual(run.stderr.count('destroy a=13'), 1)
        self.assertEqual(run.stderr.count('destroy fresh=17'), 1)
        for pool in ('p', 'q'):
            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'handles encore stockés'):
                verify_program(source + f'{pool}.reset(); print(v.len());')
        with self.assertRaisesRegex(Error, 'second.*doit encore être utilisé'):
            verify_program(source + extraction + 'print(*first); q.reset(); print(*second);')
        local = source.replace('let fresh = src.new(17);',
                               'let mut short = pool<Int>(1); let fresh = short.new(17);')
        with self.assertRaisesRegex(Error, 'sans source durable'):
            verify_program(local)

    def test_owned_handle_vector_return_keeps_fresh_injected_pool(self):
        template = """
            fn update(mut v: -> Vector<A<Int>>, src: &mut Pool<Int>) -> <- Vector<A<Int>> {
                let fresh = src.new(17);
                address(fresh);
                WRITE
                return <- v;
            }
            fn relay(v: -> Vector<A<Int>>, src: &mut Pool<Int>) -> <- Vector<A<Int>> {
                let updated = update(-> v, src);
                return <- updated;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            v.push(-> p.new(13));
            let mut updated = relay(-> v, &mut q);
        """
        for write, index in (
            ('v.push(-> fresh);', 1),
            ('let slot = &mut v[0]; *slot = <- fresh;', 0),
        ):
            with self.subTest(write=write):
                source = template.replace('WRITE', write)
                extraction = f'let item = <- updated.remove({index}); drop(-> updated);'
                run = self.native(source + extraction + """
                    address(item);
                    print(*item);
                    drop(-> item);
                    let reused = q.new(23);
                    address(reused);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                original, returned, value, reused = run.stdout.splitlines()
                self.assertEqual((returned, value, reused), (original, '17', original))
                self.assertEqual(run.stderr.count('destroy fresh=17'), 1)
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(source + 'q.reset(); print(updated.len());')
                with self.assertRaisesRegex(Error, 'item.*doit encore être utilisé'):
                    verify_program(source + extraction + 'q.reset(); print(*item);')

    def test_owned_handle_vector_result_reports_remaining_positions(self):
        template = """
            fn shrink(mut v: -> Vector<A<Int>>) -> <- Vector<A<Int>> {
                SHRINK
            }
            fn relay(v: -> Vector<A<Int>>) -> <- Vector<A<Int>> {
                let result = shrink(-> v);
                return <- result;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            let a = p.new(13);
            let b = q.new(17);
            address(a);
            address(b);
            v.push(-> a);
            v.push(-> b);
            let mut shrunk = relay(-> v);
        """
        for shrink, removed, retained, index, value in (
            ('let item = <- v.remove(0); drop(-> item); return <- v;', 'p', 'q', 1, '17'),
            ('match <- v.pop() { Some(item) => { drop(-> item); return <- v; }, None => { loop {} } }',
             'q', 'p', 0, '13'),
        ):
            with self.subTest(shrink=shrink):
                source = template.replace('SHRINK', shrink)
                run = self.native(source + f'{removed}.reset();' + """
                    let item = <- shrunk.remove(0);
                    address(item);
                    print(*item);
                    drop(-> item);
                    let pa = p.new(19);
                    let qb = q.new(23);
                    address(pa);
                    address(qb);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                a, b, address, actual, pa, qb = run.stdout.splitlines()
                self.assertEqual((address, actual, pa, qb), ((a, b)[index], value, a, b))
                self.assertEqual(run.stderr.count('destroy a=13'), 1)
                self.assertEqual(run.stderr.count('destroy b=17'), 1)
                with self.assertRaisesRegex(Error, 'handles encore stockés'):
                    verify_program(source + f'{retained}.reset(); print(shrunk.len());')

    def test_handle_vector_result_after_dynamic_removal_keeps_possible_pools(self):
        template = """
            fn shrink(mut v: -> Vector<A<Int>>, index: Int) -> <- Vector<A<Int>> {
                REMOVE
                return <- v;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut v = vp.new();
            let a = p.new(13);
            let b = q.new(17);
            address(a);
            address(b);
            v.push(-> a);
            v.push(-> b);
            let mut shrunk = shrink(-> v, INDEX);
            let remaining = <- shrunk.remove(0);
            drop(-> shrunk);
        """
        for removal in (
            'let item = <- v.remove(index); drop(-> item);',
            """if index == 0 {
                let item = <- v.remove(0);
                drop(-> item);
            } else {
                let item = <- v.remove(1);
                drop(-> item);
            }""",
        ):
            for index, retained, value in ((0, 'q', '17'), (1, 'p', '13')):
                with self.subTest(index=index, removal=removal):
                    source = template.replace('INDEX', str(index)).replace('REMOVE', removal)
                    run = self.native(source + """
                        address(remaining);
                        print(*remaining);
                        drop(-> remaining);
                        p.reset();
                        q.reset();
                    """)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    a, b, address, actual = run.stdout.splitlines()
                    self.assertEqual((address, actual), ((b, a)[index], value))
                    self.assertEqual(run.stderr.count('destroy a=13'), 1)
                    self.assertEqual(run.stderr.count('destroy b=17'), 1)
                    with self.assertRaisesRegex(Error, 'remaining.*doit encore être utilisé'):
                        verify_program(source + f'{retained}.reset(); print(*remaining);')

    def test_unknown_vector_contents_do_not_hide_extraction_before_return(self):
        source = """
            fn touch(a: &mut A<Int>) {}
            fn shrink(mut v: -> Vector<A<Int>>, other: &mut A<Int>) -> <- Vector<A<Int>> {
                touch(other);
                let item = <- v.remove(0);
                drop(-> item);
                return <- v;
            }
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let mut o = pool<Int>(1);
            let mut other = o.new(5);
            let mut v = vp.new();
            v.push(-> p.new(10));
            v.push(-> q.new(20));
            let mut shrunk = shrink(-> v, other.mut_ref());
            let a = <- shrunk.remove(0);
            drop(-> shrunk);
            q.reset();
            print(*a);
        """
        for compiler in (verify_program, compile_source):
            with self.subTest(compiler=compiler.__name__), self.assertRaisesRegex(
                Error, 'vecteur injecté après extraction'
            ):
                compiler(source)

    def test_handle_vector_extraction_infers_drop_pool_through_a_call(self):
        template = """
            fn slot_zero(v: &mut Vector<A<Int>>) -> &mut A<Int> { return &mut v[0]; }
            fn release(a: -> A<Int>, b: -> A<Int>, target: &mut Pool<Int>) {
                let mut vp = pool<Vector<A<Int>>>(2);
                let mut v = vp.new();
                v.push(-> a);
                INSTALL
                let item = <- v.remove(INDEX);
                target.drop(-> item);
            }
            fn relay(a: -> A<Int>, b: -> A<Int>, target: &mut Pool<Int>) {
                release(-> a, -> b, target);
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(13);
            let b = q.new(17);
            address(b);
            relay(-> a, -> b, &mut TARGET);
            let again = q.new(19);
            address(again);
        """
        for install, index in (
            ('v.push(-> b);', '1'),
            ('let slot = &mut v[0]; *slot = <- b;', '0'),
            ('let slot = slot_zero(&mut v); *slot = <- b;', '0'),
        ):
            with self.subTest(install=install):
                source = template.replace('INSTALL', install).replace('INDEX', index)
                run = self.native(source.replace('TARGET', 'q'))
                self.assertEqual(run.returncode, 0, run.stderr)
                original, reused = run.stdout.splitlines()
                self.assertEqual(original, reused)
                self.assertEqual(run.stderr.count('destroy b=17'), 1)
                with self.assertRaisesRegex(Error, 'contrainte d’égalité'):
                    verify_program(source.replace('TARGET', 'p'))

    def test_handle_vector_result_tracks_replacement_through_a_slot_loan(self):
        template = """
            fn slot_zero(v: &mut Vector<A<Int>>) -> &mut A<Int> { return &mut v[0]; }
            fn relay_slot(v: &mut Vector<A<Int>>) -> &mut A<Int> { return slot_zero(v); }
            fn relay(v: -> Vector<A<Int>>) -> <- Vector<A<Int>> { return <- v; }
            fn extract(a: -> A<Int>) -> <- A<Int> {
                let mut vp = pool<Vector<A<Int>>>(2);
                let mut local = pool<Int>(2);
                let mut v = vp.new();
                v.push(-> local.new(23));
                v.push(-> SECOND);
                {
                    DOWN
                    let slot = SLOT;
                    *slot = <- REPLACEMENT;
                }
                let mut relayed = relay(-> v);
                let got = <- relayed.remove(INDEX);
                return <- got;
            }
            let mut p = pool<Int>(1);
            let a = p.new(13);
            address(a);
            let got = extract(-> a);
            address(got);
            print(*got);
            drop(-> got);
            let reused = p.new(19);
            address(reused);
        """
        for second, replacement, index, slot in (
            ('local.new(29)', 'a', '0', '&mut v[0]'),
            ('a', 'local.new(29)', '1', '&mut v[0]'),
            ('local.new(29)', 'a', '0', 'relay_slot(&mut v)'),
            ('a', 'local.new(29)', '1', 'relay_slot(&mut v)'),
        ):
            with self.subTest(index=index, slot=slot):
                source = (template.replace('SECOND', second).replace('REPLACEMENT', replacement)
                          .replace('DOWN', 'a ->;' if replacement == 'a' else '').replace('SLOT', slot))
                run = self.native(source.replace('INDEX', index))
                self.assertEqual(run.returncode, 0, run.stderr)
                original, returned, value, reused = run.stdout.splitlines()
                self.assertEqual((returned, value, reused), (original, '13', original))
                self.assertEqual(run.stderr.count('destroy a=13'), 1)
                with self.assertRaisesRegex(Error, "'local' ne survit pas"):
                    verify_program(source.replace('INDEX', str(1 - int(index))))

    def test_handle_vector_result_distinguishes_item_positions(self):
        template = """
            fn extract(a: -> A<Int>, b: -> A<Int>) -> <- A<Int> {
                let mut vp = pool<Vector<A<Int>>>(2);
                let mut v = vp.new();
                v.push(-> a);
                INSERT
                let got = <- v.remove(INDEX);
                return <- got;
            }
            let mut p = pool<Int>(2);
            let a = p.new(13);
            let b = p.new(17);
            address(a);
            let got = extract(-> a, -> b);
            address(got);
            print(*got);
            drop(-> got);
        """
        for insert in (
            'v.push(-> b);',
            'let mut local = pool<Int>(1); v.push(-> local.new(23));',
        ):
            with self.subTest(insert=insert):
                source = template.replace('INSERT', insert)
                run = self.native(source.replace('INDEX', '0'))
                self.assertEqual(run.returncode, 0, run.stderr)
                original, returned, value = run.stdout.splitlines()
                self.assertEqual((returned, value), (original, '13'))
                if 'local' in insert:
                    with self.assertRaisesRegex(Error, "'local' ne survit pas"):
                        verify_program(source.replace('INDEX', '1'))

    def test_handle_vector_replace_error_return_preserves_parameter_identity(self):
        prefix = """
            fn exchange(a: -> A<Int>, fallback: -> A<Int>, index: Int) -> <- A<Int> {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut local = pool<Int>(1);
                let mut v = vp.new();
                v.push(-> local.new(7));
                match <- v.replace(index, -> a) {
                    Ok(old) => { fallback ->; drop(-> old); return <- fallback; },
                    Err(value) => { return <- value; }
                }
            }
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = p.new(13);
            let b = q.new(17);
            address(a);
            address(b);
        """
        for index, selected, value in ((0, 1, '17'), (1, 0, '13')):
            with self.subTest(index=index):
                call = f'let got = exchange(-> a, -> b, {index});'
                run = self.native(prefix + call + """
                    address(got);
                    print(*got);
                    drop(-> got);
                    let ap = p.new(31);
                    let bq = q.new(37);
                    address(ap);
                    address(bq);
                """)
                self.assertEqual(run.returncode, 0, run.stderr)
                first, second, got, printed, reuse_p, reuse_q = run.stdout.splitlines()
                self.assertEqual((got, printed), ((first, second)[selected], value))
                self.assertEqual((reuse_p, reuse_q), (first, second))
                with self.assertRaisesRegex(Error, 'got.*doit encore être utilisé'):
                    verify_program(prefix + call + 'p.reset(); print(*got);')
        local_escape = prefix.replace('v.replace(index, -> a)', 'v.replace(index, -> local.new(11))')
        with self.assertRaisesRegex(Error, 'ne survit pas'):
            verify_program(local_escape)

    def test_handle_vector_replace_match_requires_explicit_transfer(self):
        prefix = """
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(2);
            let mut v = vp.new();
            v.push(-> p.new(7));
            let incoming = p.new(9);
        """
        for body, diagnostic in (
            ('match <- v.replace(0, incoming) { Ok(old) => { drop(-> old); }, Err(rejected) => { drop(-> rejected); } }', 'transfert explicite'),
            ('match <- v.replace(0, -> incoming) { Ok(old) => { drop(-> old); }, Err(rejected) => { drop(-> rejected); } } print(*incoming);', 'plus utilisable'),
            ('match <- v.replace(0, -> incoming) { Ok(old) => { drop(-> old); }, Err(rejected) => { drop(-> rejected); }, _ => {} }', 'bras _ inaccessible'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program(prefix + body)

    def test_handle_vector_try_push_returns_incoming_at_capacity(self):
        run = self.native("""
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(131073);
            let mut q = pool<Int>(1);
            #(directive, stack_region_max_size=1M) {
                let mut v = vp.new();
                match <- v.try_push(-> p.new(11)) {
                    Ok(()) => { print(v.len()); },
                    Err(rejected) => { drop(-> rejected); print(0); }
                }
                let mut i = 1;
                while i < 131072 {
                    v.push(-> p.new(i));
                    i = i + 1;
                }
                let incoming = q.new(37);
                address(incoming);
                match <- v.try_push(-> incoming) {
                    Ok(()) => { print(0); },
                    Err(returned) => {
                        address(returned);
                        print(*returned);
                        drop(-> returned);
                        q.reset();
                    }
                }
                print(v.len());
            }
        """)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        first, incoming, returned, value, length = run.stdout.splitlines()
        self.assertEqual(incoming, returned)
        self.assertEqual((first, value, length), ('1', '37', '131072'))

    def test_handle_vector_try_push_requires_transfer_and_unit_success(self):
        prefix = """
            let mut vp = pool<Vector<A<Int>>>(1);
            let mut p = pool<Int>(1);
            let mut v = vp.new();
            let incoming = p.new(7);
        """
        for body, diagnostic in (
            ('match <- v.try_push(incoming) { Ok(()) => {}, Err(rejected) => { drop(-> rejected); } }', 'transfert explicite'),
            ('match <- v.try_push(-> incoming) { Ok(a) => {}, Err(rejected) => { drop(-> rejected); } }', 'exige Ok'),
            ('match <- v.try_push(-> incoming) { Ok(()) => { p.reset(); }, Err(rejected) => { drop(-> rejected); } }',
             'handles encore stockés'),
            ('match <- v.try_push(-> incoming) { Ok(()) => {}, Err(rejected) => { drop(-> rejected); } } print(*incoming);', 'plus utilisable'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program(prefix + body)

    def test_handle_vector_try_push_at_capacity_returns_injected_handle(self):
        run = self.native("""
            fn fill(incoming: -> A<Int>) {
                let mut vp = pool<Vector<A<Int>>>(1);
                let mut items = pool<Int>(131072);
                #(directive, stack_region_max_size=1M) {
                    incoming ->;
                    let mut v = vp.new();
                    let mut i = 0;
                    while i < 131072 {
                        v.push(-> items.new(i));
                        i = i + 1;
                    }
                    match <- v.try_push(-> incoming) {
                        Ok(()) => { print(0); },
                        Err(returned) => { address(returned); print(*returned); }
                    }
                    print(v.len());
                }
            }
            let mut p = pool<Int>(1);
            let incoming = p.new(37);
            address(incoming);
            fill(-> incoming);
            let reused = p.new(41);
            address(reused);
        """)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        original, returned, value, length, reused = run.stdout.splitlines()
        self.assertEqual((returned, value, length, reused), (original, '37', '131072', original))

    def test_growing_value_length_is_read_before_return_cleanup(self):
        run = self.native("""
            fn count() -> Int {
                let mut p = pool<String>(1);
                let mut s = p.new();
                s.push_str("é");
                return s.byte_len();
            }
            print(count());
        """)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '2\n')

    def test_vector_try_growth_rejects_conflicts_and_wrong_types(self):
        prefix = 'let mut p = pool<Vector<u8>>(1); let mut v = p.new();'
        for body, error in (
            ('let view = &v; v.try_push(1); print(view.len());', 'emprunt'),
            ('v.try_extend("x");', 'tableau u8'),
            ('v.try_push(256);', 'entre 0 et 255'),
            ('match v.try_push(1) { Ok(n) => { v.push(n); }, Err(_) => {} }', 'incompatible'),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, error):
                verify_program(prefix + body)

    def test_vector_region_limit_survives_transfer_and_bounds_are_checked(self):
        run = self.native('''
            let mut p = pool<Vector<Int>>(1);
            #(directive, stack_region_max_size=2M) {
                let mut v = #(directive, stack_region_max_size=1M) {
                    let fresh = p.new();
                    <- fresh
                };
                let mut i = 0;
                while i < 262144 {
                    v.push(i);
                    i = i + 1;
                }
                print(v.len());
                print(v[262143]);
                v.push(1);
            }
        ''')
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(run.stdout, '262144\n262143\n')
        self.assertEqual(run.stderr, 'capacité de Vector dépassée\n')

        run = self.native('''
            fn read(v: &Vector<Int>, i: Int) -> Int { return v[i]; }
            let mut p = pool<Vector<Int>>(1);
            let mut v = p.new();
            v.push(7);
            print(read(&v, 1));
        ''')
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(run.stdout, '')
        self.assertEqual(run.stderr, 'indice de Vector hors limites\n')

    def test_stack_reserves_transferred_slot_before_shorter_lived_cells(self):
        source = """
            fn mark(n: Int) -> Int { print(n); return n; }
            let mut storage = stack(4096);
            let result = {
                let outer = new(storage) Int(1);
                print(outer);
                address(outer);
                let received = {
                    let inner = new(storage) Int(2);
                    print(inner);
                    address(inner);
                    let exported = new(storage) Int(mark(3));
                    address(exported);
                    <- exported
                };
                <- received
            };
            address(result);
            print(result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        one, outer, two, inner, three, before, after, result = run.stdout.splitlines()
        self.assertEqual((one, two, three, result), ('1', '2', '3', '3'))
        self.assertEqual(before, after)
        self.assertLess(int(before, 16), int(outer, 16))
        self.assertLess(int(outer, 16), int(inner, 16))
        self.assertEqual(run.stderr.splitlines(), [
            'destroy inner=2', 'reclaim inner', 'destroy outer=1', 'reclaim outer',
            'destroy exported=3', 'reclaim exported',
        ])

    def test_stack_shares_one_reservation_between_conditional_producers(self):
        template = """
            fn mark(n: Int) -> Int { print(n); return n; }
            let mut s = stack(4096);
            let result = {
                let outer = new(s) Int(1);
                address(outer);
                let chosen = if FLAG > 0 {
                    let temp = new(s) Int(2);
                    address(temp);
                    let a = new(s) Int(mark(7));
                    address(a);
                    <- a
                } else {
                    let temp = new(s) Int(3);
                    address(temp);
                    let b = new(s) Int(mark(9));
                    address(b);
                    <- b
                };
                <- chosen
            };
            address(result);
            print(result);
        """
        for flag, expected in ((0, '9'), (1, '7')):
            with self.subTest(flag=flag):
                source = template.replace('FLAG', str(flag))
                code = compile_source(source)
                self.assertEqual(code.count(' = cell_reserve_for_transfer('), 1)
                main = code.split('int main(void)', 1)[1]
                self.assertEqual(main.count(' = cell_construct_reserved('), 2)
                run = self.native(source)
                self.assertEqual(run.returncode, 0, run.stderr)
                outer, temp, effect, before, after, value = run.stdout.splitlines()
                self.assertEqual((effect, value, after), (expected, expected, before))
                self.assertLess(int(before, 16), int(outer, 16))
                self.assertLess(int(outer, 16), int(temp, 16))

    def test_stack_reserves_break_result_after_continue_paths(self):
        source = """
            fn mark(n: Int) -> Int { print(n); return n; }
            let mut storage = stack(4096);
            let mut i = 0;
            let result = loop {
                if i < 2 {
                    let skipped = new(storage) Int(1);
                    address(skipped);
                    i = i + 1;
                    continue;
                }
                let temp = new(storage) Int(2);
                address(temp);
                let selected = new(storage) Int(mark(3));
                address(selected);
                break <- selected;
            };
            address(result);
            print(result);
        """
        code = compile_source(source)
        self.assertEqual(code.count(' = cell_reserve_for_transfer('), 1)
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        skipped_a, skipped_b, temp, effect, before, after, value = run.stdout.splitlines()
        self.assertEqual((skipped_a, skipped_b, before, after), (after,) * 4)
        self.assertEqual((effect, value), ('3', '3'))
        self.assertLess(int(before, 16), int(temp, 16))
        self.assertEqual(run.stderr.splitlines(), [
            'destroy skipped=1', 'reclaim skipped', 'destroy skipped=1', 'reclaim skipped',
            'destroy temp=2', 'reclaim temp', 'destroy selected=3', 'reclaim selected',
        ])

    def test_stack_reserves_growing_descriptors_and_constructs_payload_later(self):
        template = """
            let mut p = pool<TYPE>(2);
            let mut received = #(directive, stack_region_max_size=1M) {
                let temp = p.new();
                address(temp);
                let value = p.new();
                address(value);
                <- value
            };
            address(received);
            USE
        """
        for typ, use, expected in (
            ('Vector<Int>', 'received.push(17); print(received[0]);', '17'),
            ('String', 'received.push_str("été"); print(received.byte_len());', '5'),
            ('Vector<A<Int>>', """
                let mut ints = pool<Int>(1);
                let item = ints.new(17);
                address(item);
                received.push(-> item);
                print(received.len());
                drop(-> received);
                let reused = ints.new(9);
                address(reused);
            """, '1'),
        ):
            with self.subTest(typ=typ):
                source = template.replace('TYPE', typ).replace('USE', use)
                code = compile_source(source)
                self.assertEqual(code.count(' = vector_construct_reserved('), 1)
                self.assertEqual(code.count(' = vector_reserve_region('), 1)
                run = self.native(source)
                self.assertEqual(run.returncode, 0, run.stderr)
                temp, before, after, *output = run.stdout.splitlines()
                self.assertEqual(before, after)
                self.assertLess(int(before, 16), int(temp, 16))
                if typ == 'Vector<A<Int>>':
                    original, length, reused = output
                    self.assertEqual((length, reused), (expected, original))
                    self.assertEqual(run.stderr.count('destroy item=17'), 1)
                else:
                    self.assertEqual(output, [expected])
                full = self.native(source.replace(f'pool<{typ}>(2)', f'pool<{typ}>(1)'))
                self.assertEqual(full.returncode, 1)
                self.assertEqual(len(full.stdout.splitlines()), 1)
                self.assertIn('pool capacity exceeded', full.stderr)
        warm = template.replace('TYPE', 'Vector<Int>').replace(
            'pool<Vector<Int>>(2);', '''pool<Vector<Int>>(3);
                let warm = #(directive, stack_region_max_size=1M) { let v = p.new(); <- v };
                address(warm);''').replace('USE', 'received.push(17); print(received[0]);')
        run = self.native(warm)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, temporary, before, after, value = run.stdout.splitlines()
        self.assertEqual((before, value), (after, '17'))
        self.assertLess(int(first, 16), int(before, 16))
        self.assertLess(int(before, 16), int(temporary, 16))
        unannotated = template.replace('TYPE', 'Vector<Int>').replace(
            '#(directive, stack_region_max_size=1M) ', '').replace(
            'USE', 'received.push(17); received.push(19); print(received[0]); print(received[1]);')
        self.assertEqual(compile_source(unannotated).count(' = vector_reserve_front('), 1)
        run = self.native(unannotated)
        self.assertEqual(run.returncode, 0, run.stderr)
        temporary, before, after, first, second = run.stdout.splitlines()
        self.assertEqual((before, first, second), (after, '17', '19'))
        self.assertLess(int(before, 16), int(temporary, 16))

        text = template.replace('TYPE', 'String').replace('#(directive, stack_region_max_size=1M) ', '').replace('USE', '''
            received.push_str("é🌍");
            print(&received[2..]);
            match received.pop() { Some(ch) => { print(ch); }, None => { print(99); } }
            print(&received[..]);
        ''')
        self.assertEqual(compile_source(text).count(' = vector_reserve_dedicated_front('), 1)
        run = self.native(text)
        self.assertEqual(run.returncode, 0, run.stderr)
        temporary, before, after, sliced, popped, remaining = run.stdout.splitlines()
        self.assertEqual((before, sliced, popped, remaining), (after, '🌍', '🌍', 'é'))
        self.assertLess(int(before, 16), int(temporary, 16))

    def test_stack_reserves_transferred_string_in_indexed_holes(self):
        source = """
            let mut strings = pool<String>(3);
            #(directive, stack_region_max_size=1M) {
                let first = strings.new();
                let second = strings.new();
                let mut live = strings.new();
                live.push_str("🌍");
                address(first);
                address(second);
                drop(-> first);
                drop(-> second);
                let mut received = {
                    let mut temporary = strings.new();
                    temporary.push_str("temp");
                    address(temporary);
                    let mut value = strings.new();
                    value.push_str("é");
                    address(value);
                    <- value
                };
                address(received);
                print(&received[..]);
                print(&live[..]);
            }
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second, temporary, value, received, result, live = run.stdout.splitlines()
        self.assertEqual((temporary, value, received), (first, second, second))
        self.assertEqual((result, live), ('é', '🌍'))

        ordinary = self.native(source.replace('temporary.push_str("temp")', 'temporary.push_str(&live[..])'))
        self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
        first, second, temporary, value, received, result, live = ordinary.stdout.splitlines()
        self.assertEqual((temporary, value, received), (second, first, first))
        self.assertEqual((result, live), ('é', '🌍'))

    def test_stack_reserves_transferred_region_across_match_arms(self):
        source = """
            enum Choice { A, B }
            let mut choices = pool<Choice>(1);
            let choice = new(choices) Choice.ARM;
            let mut strings = pool<String>(2);
            #(directive, stack_region_max_size=1M) {
                let mut received = match &choice {
                    Choice.A => {
                        let temporary = strings.new();
                        address(temporary);
                        let value = strings.new();
                        address(value);
                        <- value
                    },
                    Choice.B => {
                        let temporary = strings.new();
                        address(temporary);
                        let value = strings.new();
                        address(value);
                        <- value
                    }
                };
                address(received);
                received.push_str("é");
                print(&received[..]);
            }
        """
        for arm in ('A', 'B'):
            with self.subTest(arm=arm):
                candidate = source.replace('Choice.ARM', f'Choice.{arm}')
                self.assertEqual(compile_source(candidate).count(' = vector_reserve_region('), 1)
                run = self.native(candidate)
                self.assertEqual(run.returncode, 0, run.stderr)
                temporary, value, received, content = run.stdout.splitlines()
                self.assertLess(int(value, 16), int(temporary, 16))
                self.assertEqual((value, content), (received, 'é'))

        full = self.native(source.replace('Choice.ARM', 'Choice.A').replace('pool<String>(2)', 'pool<String>(1)'))
        self.assertEqual(full.returncode, 1)
        self.assertEqual(len(full.stdout.splitlines()), 1)
        self.assertIn('pool capacity exceeded', full.stderr)

        prefix, second = source.replace('Choice.ARM', 'Choice.B').split('Choice.B =>', 1)
        separate = prefix.replace('let mut strings = pool<String>(2);',
                                  'let mut strings = pool<String>(2); let mut other = pool<String>(2);')
        separate += 'Choice.B =>' + second.replace('strings.new()', 'other.new()')
        self.assertNotIn(' = vector_reserve_region(', compile_source(separate))
        ordinary = self.native(separate)
        self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
        temporary, value, received, content = ordinary.stdout.splitlines()
        self.assertLess(int(temporary, 16), int(value, 16))
        self.assertEqual((value, content), (received, 'é'))

    def test_stack_reserves_enum_arm_without_advancing_field_initializers(self):
        source = """
            enum E { A { x: Int }, B { y: Int } }
            fn mark(n: Int) -> Int { print(n); return n; }
            let mut p = pool<E>(2);
            let result = {
                let temp = new(p) E.A { x: 1 };
                address(temp);
                let other = new(p) E.B { y: 2 };
                print(other);
                let selected = new(p) E.A { x: mark(3) };
                address(selected);
                <- selected
            };
            address(result);
            print(result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        temporary, other, effect, before, after, value = run.stdout.splitlines()
        self.assertEqual((other, effect, after, value), ('E.B(2)', '3', before, 'E.A(3)'))
        self.assertLess(int(before, 16), int(temporary, 16))
        full = self.native(source.replace('pool<E>(2)', 'pool<E>(1)'))
        self.assertEqual(full.returncode, 1)
        self.assertEqual(full.stdout.splitlines()[1:], ['E.B(2)', '3'])
        self.assertIn('pool capacity exceeded', full.stderr)

    def test_stack_reserves_structure_slot_without_losing_borrowed_fields(self):
        source = """
            struct View { target: &Int, code: Int }
            let mut views = pool<View>(2);
            let mut ints = pool<Int>(1);
            let n = ints.new(9);
            let result = {
                let temp = views.new(target: &n);
                address(temp);
                let selected = views.new(target: &n, code: 3);
                address(selected);
                <- selected
            };
            address(result);
            print(result);
        """
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        temporary, before, after, value = run.stdout.splitlines()
        self.assertEqual((after, value), (before, 'View(9, 3)'))
        self.assertLess(int(before, 16), int(temporary, 16))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('print(result);', 'drop(-> n); print(result);'))

    def test_vector_rejects_type_mismatch_and_effectful_alias(self):
        for source, diagnostic in (
            ('let mut p = pool<Vector<Int>>(1); let v = p.new(); v.push(1);', 'immuable'),
            ('let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push("é"[0]);', 'type des cases'),
            ('let mut p = pool<Vector<u8>>(1); let mut v = p.new(); v.push(256);', 'entre 0 et 255'),
            ('let mut p = pool<Vector<u8>>(1); let mut v = p.new(); print(v["x"]);', 'indice|élément'),
            ('''fn index(v: &mut Vector<Int>) -> Int { v.push(2); return 0; }
                let mut p = pool<Vector<Int>>(1);
                let mut v = p.new();
                v.push(1);
                print(v[index(&mut v)]);''', 'emprunt actif'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)
