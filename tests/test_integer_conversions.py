"""F5: integer conversion acceptance, values, effects and memory interactions."""

import unittest

import test_foundation_rules
from crust import Error, compile_source, verify_program


class IntegerConversionTests(unittest.TestCase):
    native = test_foundation_rules.FoundationTests.native

    def test_try_from_matches_interval_model_through_function_contracts(self):
        run = self.native('''
            fn convert(n: Int) -> Result<u8,IntegerConversionError> {
                return u8::try_from(n);
            }
            fn relay(n: Int) -> Result<u8,IntegerConversionError> { return convert(n); }
            fn main() {
                let mut n = -2;
                while n < 258 {
                    let result = relay(n);
                    match result {
                        Err(_) => { print(-999); },
                        Ok(byte) => { print(byte as Int); }
                    }
                    n = n + 1;
                }
                match convert(-2147483648) {
                    Ok(byte) => { print(byte as Int); },
                    Err(IntegerConversionError::OutOfRange) => { print(-999); }
                }
                match convert(2147483647) {
                    Err(IntegerConversionError::OutOfRange) => { print(-999); },
                    Ok(byte) => { print(byte as Int); }
                }
            }
        ''')
        self.assertEqual(run.returncode, 0, run.stderr)
        expected = [n if 0 <= n <= 255 else -999 for n in range(-2, 258)] + [-999, -999]
        self.assertEqual(list(map(int, run.stdout.splitlines())), expected)

    def test_try_from_drop_expression_evaluates_once_before_next_statement(self):
        run = self.native('''
            fn convert(n: Int) -> Result<u8,IntegerConversionError> {
                print(n);
                return u8::try_from(n);
            }
            fn main() {
                drop(-> convert(-1));
                print(7);
                drop(-> convert(42));
                print(8);
                let result = u8::try_from(255);
                drop(-> result);
                print(9);
            }
        ''')
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, '-1\n7\n42\n8\n9\n', ''))

    def test_try_from_conditional_use_and_transmission_are_explicit_uses(self):
        run = self.native('''
            fn consume(result: Result<u8,IntegerConversionError>) { drop(-> result); }
            fn inspect(flag: Int) {
                let result = u8::try_from(42);
                if flag == 1 {
                    match result { Ok(byte) => { print(byte as Int); }, Err(_) => { print(-1); } }
                }
            }
            fn main() {
                inspect(0);
                inspect(1);
                let byte: u8 = 255;
                consume(u8::try_from(byte));
                print(9);
            }
        ''')
        self.assertEqual((run.returncode, run.stdout), (0, '42\n9\n'), run.stderr)

    def test_drop_expression_reclaims_owned_result_before_next_allocation(self):
        source = '''
            fn main() {
                let mut numbers = pool<Int>(2);
                let mut vectors = pool<Vector<A<Int>>>(1);
                let mut values = vectors.new();
                let first = numbers.new(7);
                address(first);
                values.push(-> first);
                let incoming = numbers.new(9);
                address(incoming);
                drop(-> values.replace(INDEX, -> incoming));
                let next = numbers.new(11);
                address(next);
                drop(-> next);
                let content = <- values.remove(0);
                print(*content);
                drop(-> content);
            }
        '''
        for index in (0, 1):
            with self.subTest(index=index):
                run = self.native(source.replace('INDEX', str(index)))
                self.assertEqual(run.returncode, 0, run.stderr)
                first, incoming, reused, content = run.stdout.splitlines()
                self.assertEqual((reused, content), (first, '9') if index == 0 else (incoming, '7'))
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy')]
                self.assertEqual(destroyed[:2], ['destroy first=7' if index == 0 else 'destroy incoming=9',
                                                 'destroy next=11'])
        direct = '''fn main() {
            let mut numbers=pool<Int>(1);
            drop(-> numbers.new(7));
            let next=numbers.new(9);
            print(*next);
        }'''
        self.assertNotIn('\0', compile_source(direct))
        run = self.native(direct)
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)

    def test_try_from_requires_use_and_consumes_dropped_binding(self):
        invalid = (
            ('u8::try_from(42);', 'sans receveur'),
            ('let _ = u8::try_from(42);', 'sans usage explicite'),
            ('let _unused = u8::try_from(42);', 'sans usage explicite'),
            ('let result = u8::try_from(300);', 'sans usage explicite'),
            ('let result = u8::try_from(42); drop(-> result); drop(-> result);', 'plus utilisable'),
            ('drop(-> u8::try_from(true));', 'Int ou un u8'),
            ('drop(-> u8::try_from("42"));', 'Int ou un u8'),
            ('drop(-> u8::try_from());', 'un argument'),
            ('drop(-> u8::try_from(1, 2));', 'un argument'),
            ('let mut result=u8::try_from(42); result=u8::try_from(43); drop(-> result);',
             'sans usage explicite'),
            ('let result = char::from_str("A");', 'sans usage explicite'),
            ('let bytes:[u8;1]=[65]; let result = str::from_utf8(&bytes);', 'sans usage explicite'),
        )
        for body, diagnostic in invalid:
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                compile_source('fn main(){' + body + '}')
        compile_source('fn main(){drop(u8::try_from(42));}')

    def test_try_from_result_survives_source_drop_and_reset(self):
        source = '''
            fn main() {
                let mut numbers = pool<Int>(1);
                let number = numbers.new(256);
                let view = &number;
                let result = u8::try_from(*view);
                drop(-> number);
                let reused = numbers.new(42);
                match result { Err(_) => { print(7); }, Ok(byte) => { print(byte as Int); } }
                print(*reused);
            }
        '''
        for program in (source, source.replace('drop(-> number);', 'numbers.reset();')):
            run = self.native(program)
            self.assertEqual((run.returncode, run.stdout), (0, '7\n42\n'), run.stderr)
        for effect in ('drop(-> number);', 'numbers.reset();'):
            with self.subTest(effect=effect), self.assertRaisesRegex(Error, 'emprunt|encore .*utilisée'):
                verify_program(source.replace('let result =', effect + 'let result ='), allow_legacy_reset=True)
        run = self.native('''
            fn main() {
                let mut bytes:[u8;1]=[65];
                let result=str::from_utf8(&bytes);
                drop(-> result);
                bytes[0]=255;
                print(9);
            }
        ''')
        self.assertEqual((run.returncode, run.stdout), (0, '9\n'), run.stderr)

    def test_try_from_async_await_join_and_explicit_drop(self):
        source = '''
            async fn convert(n: Int) -> Result<u8,IntegerConversionError> {
                let result = u8::try_from(n);
                yield;
                return result;
            }
            async fn run() -> Int {
                let result = convert(256).await;
                yield;
                match result { Err(_) => { print(-1); }, Ok(byte) => { print(byte as Int); } }
                drop(-> u8::try_from(42));
                return 9;
            }
            fn main() {
                let task = run();
                let execution = runtime::spawn(-> task);
                match execution.join() { Ok(n) => { print(n); }, Err(_) => { print(-2); } }
                let other = runtime::spawn(-> convert(42));
                match other.join() {
                    Ok(result) => {
                        match result { Err(_) => { print(-3); }, Ok(byte) => { print(byte as Int); } }
                    },
                    Err(_) => { print(-4); }
                }
            }
        '''
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '-1\n9\n42\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'sans usage explicite'):
            compile_source(source.replace('drop(-> u8::try_from(42));', 'let ignored = u8::try_from(42);'))
        with self.assertRaisesRegex(Error, 'sans usage explicite'):
            compile_source(source.replace('drop(-> u8::try_from(42));',
                'let mut ignored = u8::try_from(42); ignored = u8::try_from(43); drop(-> ignored);'))
        with self.assertRaisesRegex(Error, 'après drop|déjà consomm'):
            compile_source(source.replace('return result;', 'drop(-> result); return result;'))

    def test_widening_preserves_every_u8_value(self):
        source = '''
            fn widen(value: u8) -> Int { return value as Int; }
            fn main() {
                let values: [u8;256] = [''' + ','.join(map(str, range(256))) + '''];
                let mut index = 0;
                while index < 256 {
                    print(widen(values[index] as u8));
                    index = index + 1;
                }
                let octet: u8 = 42;
                let count: Int = 300;
                print(octet as Int * 2 + 1);
                print(-(octet as Int));
                print(count as Int);
                print(-2147483648 as Int);
                print(2147483647 as Int);
            }
        '''
        run = self.native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(list(map(int, run.stdout.splitlines())),
                         [*range(256), 85, -42, 300, -(2 ** 31), 2 ** 31 - 1])

    def test_cast_uses_types_even_for_known_small_values(self):
        cases = (
            ('let byte = 42 as u8; print(byte as Int);', 'non exacte'),
            ('let number: Int = 42; let byte = number as u8; print(byte as Int);', 'non exacte'),
            ('let number = 0; let byte = number as u8; print(byte as Int);', 'non exacte'),
            ('print(true as Int);', 'deux types entiers'),
            ('print("42" as Int);', 'deux types entiers'),
            ('print(42 as bool);', 'deux types entiers|non exacte'),
            ('let byte:u8=42; print(-byte as Int);', 'Int'),
            ('let numbers = pool<Int>(1); print(numbers as Int);', 'deux types entiers'),
            ('let mut numbers = pool<Int>(1); let number = numbers.new(42); print(number as Int);',
             'deux types entiers'),
            ('let number: u8 = 256; print(number as Int);', 'hors des bornes'),
            ('let number: u8 = -1; print(number as Int);', 'hors des bornes'),
            ('let source = 42; let number: u8 = source; print(number as Int);', 'attendu u8'),
        )
        for body, diagnostic in cases:
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                compile_source('fn main() {' + body + '}')

    def test_cast_evaluates_once_and_keeps_argument_order(self):
        run = self.native('''
            fn first(mut count: &mut Int) -> u8 {
                count.set(1);
                print(*count);
                let value: u8 = 255;
                return value;
            }
            fn second(mut count: &mut Int) -> u8 {
                count.set(2);
                print(*count);
                let value: u8 = 255;
                return value;
            }
            fn combine(first: Int, second: Int) -> Int { return first + second; }
            fn main() {
                let mut numbers = pool<Int>(1);
                let mut count = numbers.new(0);
                print(combine(first(&mut count) as Int, second(&mut count) as Int));
                print(*count);
            }
        ''')
        self.assertEqual((run.returncode, run.stdout), (0, '1\n2\n510\n2\n'), run.stderr)

    def test_cast_finishes_read_but_never_extends_a_dead_borrow(self):
        source = '''
            fn main() {
                let mut numbers = pool<Int>(1);
                let number = numbers.new(10);
                let view = &number;
                let copied = *view as Int;
                drop(-> number);
                let reused = numbers.new(20);
                print(copied);
                print(*reused);
            }
        '''
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '10\n20\n'), run.stderr)
        for operation in ('drop(-> number);', 'numbers.reset();'):
            invalid = source.replace('let copied =', operation + 'let copied =')
            with self.subTest(operation=operation), self.assertRaisesRegex(Error, 'emprunt|encore .*utilisée'):
                verify_program(invalid, allow_legacy_reset=True)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            compile_source('fn main(){let byte:u8=42;drop(-> byte);print(byte as Int);}')

    def test_async_cast_preserves_values_across_suspension(self):
        source = '''
            async fn widen(value: u8) -> Int {
                let base: u8 = 42;
                yield;
                return value as Int + base as Int;
            }
            fn main() {
                let byte: u8 = 255;
                let task = widen(byte);
                let execution = runtime::spawn(-> task);
                match execution.join() {
                    Ok(value) => { print(value); },
                    Err(_) => { print(-1); }
                }
            }
        '''
        run = self.native(source)
        self.assertEqual((run.returncode, run.stdout), (0, '297\n'), run.stderr)
        with self.assertRaisesRegex(Error, 'non exacte'):
            compile_source(source.replace('let base: u8 = 42;', 'let base: u8 = 42 as u8;'))


if __name__ == '__main__':
    unittest.main()
