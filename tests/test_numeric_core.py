"""Numeric typing, checked evaluation and storage through both compiler entries."""

import unittest

from crust import Error, Parser, compile_source, verify_program
import test_async_runtime as harness


class NumericCoreTests(unittest.TestCase):
    run_c_oracle = harness.AsyncRuntimeTests.run_c_oracle

    def native(self, source, error=None):
        verify_program(source, numeric_core=True)
        return self.run_c_oracle(compile_source(source, numeric_core=True), expected_error=error)

    def refuses(self, source, diagnostic):
        for check in (verify_program, compile_source):
            with self.subTest(entry=check.__name__, source=source), self.assertRaisesRegex(Error, diagnostic):
                check(source, numeric_core=True)

    def test_contextual_widths_across_control_flow_and_arrays(self):
        source = '''
            fn pair(n:u16)->[u16;2] { [1,n] }
            fn pick(n:u16, b:bool)->u16 {
                let x=if b {2} else {n};
                let y=match u16::try_from(x) { Ok(v)=>{v}, Err(_)=>{3}, };
                let z=loop { if b {break 4;} break y; };
                z
            }
            fn main() {
                let a=pair(65535); let k:u64=1; print(a[k]); print(a.len());
                print(pick(7,true)); print(pick(8,false));
                let wide=9223372036854775807; print(wide);
            }
        '''
        self.assertEqual(self.native(source).stdout, '65535\n2\n4\n8\n9223372036854775807\n')

    def test_builtin_qualified_paths_are_parsed_before_lookup_and_arity(self):
        function, = Parser("""
            fn main() {
                let result=i64::try_from(1, 2);
                let error=runtime::Error::FutureVariant;
                let value=bool::named_value;
                let character=char::from_str("a");
            }
        """).parse_syntax()
        result, error, value, character = (node.args[1] for node in function.args[3])
        self.assertEqual(result, ('call', 'i64::try_from', [('numeric_integer', 1), ('numeric_integer', 2)]))
        self.assertEqual(error, ('name', 'runtime::Error::FutureVariant'))
        self.assertEqual(value, ('name', 'bool::named_value'))
        self.assertEqual(character, ('call', 'char::from_str', [('text', b'a')]))
        for expression in ('i64::', 'runtime::Error::42', 'bool::a::b'):
            with self.subTest(expression=expression), self.assertRaises(Error):
                Parser(f'fn main(){{let value={expression};}}').parse_syntax()
        with self.assertRaisesRegex(Error, 'exactement une valeur'):
            Parser('fn main(){let value=i64::try_from(1,2);}').parse()

    def test_raw_conversion_preserves_target_type_before_numeric_checks(self):
        function, = Parser('fn main(){let value=1 as &mut [network::Packet] as u64 + 2;}').parse_syntax()
        self.assertEqual(function.args[3][0].args[1], (
            'numeric_binary', '+', ('numeric_cast',
                ('numeric_cast', ('numeric_integer', 1), '&mut [network::Packet]'), 'u64'),
            ('numeric_integer', 2)))
        for target in ('&mut', '[i64]', 'network::'):
            with self.subTest(target=target), self.assertRaises(Error):
                Parser(f'fn main(){{let value=1 as {target};}}').parse_syntax()

    def test_raw_generic_closers_can_touch_following_operators(self):
        function, = Parser('''fn main(){
            let comparison=value as A<i32>==other;
            let inclusive=value as A<i32>>=other;
            let shifted=value as A<i32>>>2;
            let nested=value as A<A<A<i32>>>;
        }''').parse_syntax()
        comparison, inclusive, shifted, nested = (node.args[1] for node in function.args[3])
        self.assertEqual(comparison[1][1], '==')
        self.assertEqual(inclusive[1][1], '>=')
        self.assertEqual(shifted[:2], ('numeric_binary', '>>'))
        self.assertEqual(nested[2], 'A<A<A<i32>>>')
        for body in ('let value=4>>>1;', 'value>>=1;', 'let value=x as A<i32>> = other;'):
            with self.subTest(body=body), self.assertRaises(Error):
                Parser(f'fn main(){{{body}}}').parse_syntax()

    def test_raw_sizes_use_unsigned_integer_syntax_before_capacity_checks(self):
        large = '9' * 5000
        source = f'fn read(values:[i64;{large}]){{let a=[1;{large}];let p=pool<i64>(0);}}'
        function, = Parser(source).parse_syntax()
        self.assertEqual(function.args[1][0][2], f'[i64;{large}]')
        repeated, pool = (node.args[1] for node in function.args[3])
        self.assertEqual(repeated[2], large)
        self.assertEqual(pool[2], 0)
        for invalid in ('fn read(a:[i64;-1]) {}', 'fn main(){let a=[1;-1];}',
                        'fn main(){let p=pool<i64>(1.5); }'):
            with self.subTest(source=invalid), self.assertRaisesRegex(Error, 'entier non signé'):
                Parser(invalid).parse_syntax()
        with self.assertRaisesRegex(Error, 'capacité du pool'):
            Parser('fn main(){let p=pool<i64>(0);}').parse()

    def test_numeric_literal_syntax_precedes_range_checks(self):
        for literal in ('1.5', '1.', '.5', '-.5'):
            with self.subTest(literal=literal):
                function, = Parser(f'fn main(){{let value={literal};}}').parse_syntax()
                self.assertEqual(function.args[3][0].args[1], ('numeric_decimal', literal))
        for literal in ('9' * 25, '-0x' + 'f' * 17):
            with self.subTest(literal=literal):
                source = f'fn main(){{let value={literal};}}'
                function, = Parser(source).parse_syntax()
                self.assertEqual(function.args[3][0].args[1], ('numeric_integer_token', literal))
                with self.assertRaisesRegex(Error, 'hors des bornes'):
                    Parser(source).parse()
        for expression in ('1e3', '1.4e-3', '1<2<3'):
            with self.subTest(expression=expression), self.assertRaises(Error):
                Parser(f'fn main(){{let value={expression};}}').parse_syntax()
        Parser('fn main(){let x=(1<2) == true; let part=&text[1..3];}').parse_syntax()

    def test_literal_family_and_bounds(self):
        self.assertEqual(self.native('fn main(){let n:i32=-2147483648;print(n);let f:f32=.5;print(1.+f);}'
                                     ).stdout, '-2147483648\n1.5\n')
        for body, diagnostic in (
            ('let n:i32=-2147483649;', 'bornes'),
            ('let n:u8=256;', 'bornes'),
            ('let n:f32=0;print(n);', 'famille'),
            ('let n:f32=1.;print(n+1);', 'famille'),
            ('let a:u32=1;let b:u64=2;print(a+b);', 'types différents'),
            ('if 1 {print(7);}', 'types différents|bool'),
            ('print(1e3);', 'attendu|inconnu'),
            ('let a:[u8;0]=[];print(a[0]);', 'hors limites|vide'),
            ('print(' + '9' * 400 + '.);', 'débordement flottant'),
            ('print(0.' + '0' * 400 + '1);', 'arrondi à zéro'),
        ):
            self.refuses('fn main(){'+body+'}', diagnostic)

    def test_integer_operators_and_short_circuit(self):
        source = '''
            fn shift(n:i32,k:u8)->i32 { n >> k }
            fn zero(n:i64)->i64 { n % -1 }
            fn safe(n:i64)->bool { n != 0 && 1 / n > 0 }
            fn main(){
                print(shift(-3,1)); print(zero(-9223372036854775808));
                let n:u8=1; print(~n); print((n<<3)|2); print((n^3)&3);
                if !safe(0) || safe(1) {print(42);}
            }
        '''
        self.assertEqual(self.native(source).stdout, '-2\n0\n254\n10\n2\n42\n')
        for body, diagnostic in (
            ('let n:u8=255;print(n+1);', 'débordement'),
            ('let n:i32=1;print(n<<32);', 'positions'),
            ('print(-9223372036854775808 / -1);', 'débordement'),
            ('print(0/0);', 'division par zéro'),
        ):
            self.refuses('fn main(){'+body+'}', diagnostic)

    def test_runtime_checks_keep_original_width(self):
        for helper, argument, error in (
            ('fn f(n:i64)->i64{n / -1}', '-9223372036854775808', 'débordement'),
            ('fn f(n:u64)->u64{n*n}', '18446744073709551615', 'débordement'),
            ('fn f(n:u64)->u8{let a:u8=2;a<<n}', '18446744073709551615', 'positions'),
            ('fn f(n:u64)->i64{let a=[1,2];a[n]}', '18446744073709551615', 'hors limites'),
            ('fn f(n:i32)->i64{let a=[1,2];a[n]}', '-1', 'hors limites'),
            ('fn f(n:f64)->f64{0./n}', '-0.', 'division par zéro'),
            ('fn f(n:f32)->f32{n*n}', '0.000000000000000000000000000001', 'arrondi à zéro'),
            ('fn f(n:f32)->f32{n*n}', '100000000000000000000.', 'débordement flottant'),
        ):
            with self.subTest(helper=helper, argument=argument):
                self.native(helper+'fn main(){print(f('+argument+'));}', error)

    def test_explicit_conversions(self):
        source = '''
            fn f(x:f64)->i64 {
                match i64::try_from(x) { Ok(n)=>{n}, Err(NumericConversionError::NotRepresentable)=>{0}, }
            }
            fn g(n:u64)->u8 {
                match u8::try_from(n) { Ok(b)=>{b}, Err(NumericConversionError::NotRepresentable)=>{0}, }
            }
            fn main(){
                let u:u16=65535; print(u as f32); print(f(3.)); print(f(3.5));
                print(g(255)); print(g(256));
                match f64::try_from(9007199254740993) { Ok(_)=>{print(1);}, Err(_)=>{print(2);}, }
                match f32::try_from(0.1) { Ok(_)=>{print(1);}, Err(_)=>{print(2);}, }
            }
        '''
        self.assertEqual(self.native(source).stdout, '65535\n3\n0\n255\n0\n2\n2\n')
        self.refuses('fn main(){let n:u64=1;print(n as f64);}', 'non exacte')
        self.refuses('fn main(){let n:f64=1.;print(n as f32);}', 'non exacte')

    def test_float_rounding_and_signed_zero(self):
        source = '''
            fn add(a:f32,b:f32)->f32 {a+b}
            fn main(){
                let constant:f32=16777218.+1.;
                print(constant); print(add(16777218.,1.));
                print(add(16777216.,1.)); print(.5-.5); print(-0.);
            }
        '''
        self.assertEqual(self.native(source).stdout, '16777220\n16777220\n16777216\n0\n-0\n')

    def test_compound_assignment_reserves_the_selected_place(self):
        source = '''
            fn index()->u64 {print(42);1}
            fn rhs()->u64 {print(43);2}
            fn main(){
                let mut a:[u64;2]=[3,4];
                a[index()] += rhs();
                a[0] += {a[1]=9; a[0]};
                let mut n:u64=a[0];
                n *= 2; n -= 1; n /= 2; n %= 3;
                print(n); print(a[0]); print(a[1]);
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n43\n2\n6\n9\n')
        self.refuses(source.replace('a[1]=9;', 'a[0]=9;'), 'emprunt actif')
        self.refuses('fn main(){let mut n:i32=2;n+={n=4;1};}', 'composée')
        self.refuses('fn main(){let n:u64=2;n+=1;}', 'immuable')
        runtime_failure = self.native(source.replace('print(42);1', 'print(42);2'), 'hors limites')
        self.assertNotIn('43\n', runtime_failure.stdout)

    def test_scalar_tasks_and_compound_assignment_across_await(self):
        source = '''
            async fn f(x:f32)->f32 {yield; x+1.}
            async fn g()->f32 {
                let mut a:[f32;2]=[3.,4.];
                let value=f(.5).await;
                a[1]+={a[0]=7.25;f(value).await};
                a[1]
            }
            fn main(){let h=runtime::spawn(g());match h.join(){Ok(n)=>{print(n);},Err(_)=>{},}}
        '''
        self.assertEqual(self.native(source).stdout, '6.5\n')
        self.refuses(source.replace('a[0]=7.25', 'a[1]=7.25'), 'emprunt actif')
        bool_task = '''
            async fn flip(n:bool)->bool{yield;!n}
            async fn both()->bool{let n=flip(false).await;n&&true}
            fn main(){let h=runtime::spawn(both());
                match h.join(){Ok(n)=>{if n {print(1);}},Err(_)=>{},}}
        '''
        self.assertEqual(self.native(bool_task).stdout, '1\n')

    def test_slice_length_uses_the_same_unsigned_type_as_array_length(self):
        source = '''
            fn length(v:&[u8])->u64 {v.len()}
            fn main(){
                let mut p=pool<Vector<u8>>(1); let mut v=p.new();
                print(length(&v[..])); let b:u8=7; v.push(b);
                print(length(&v[..]));
            }
        '''
        self.assertEqual(self.native(source).stdout, '0\n1\n')

    def test_typed_pool_reclaims_the_slot_and_preserves_width(self):
        source = '''
            fn relay(value:A<u64>)->A<u64>{value}
            fn update(value:&mut u64){*value=2;}
            fn main(){
                let mut p=pool<u64>(1);
                let mut n=relay(p.new(18446744073709551615));
                address(n); print(*n); n=1; print(*n);
                update(&mut n); print(*n); n.set(3); print(*n);
                drop(n); let next=p.new(); address(next); print(*next);
            }
        '''
        a, large, one, two, three, b, zero = self.native(source).stdout.splitlines()
        self.assertEqual(a,b)
        self.assertEqual((large,one,two,three,zero), ('18446744073709551615','1','2','3','0'))
        self.refuses(source.replace('drop(n);', 'drop(n);print(*n);'), 'plus utilisable|déplac')
