"""TF1–TF5: abstract guarantees, static resolution and concrete memory contracts."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from crust import Compiler, Error, Parser, compile_source, verify_program


class FunctionTypeContractTests(unittest.TestCase):
    def test_callable_syntax_preserves_explicit_passage_and_result_borrow(self):
        read, advance, take, ordinary = Parser('''
            fn read(f: &fn() -> &i64) -> &i64 { f() }
            fn advance(f: &mut fn() -> i64) -> i64 { f() }
            fn take(mut f: fn() -> i64) -> i64 { f() }
            fn closure() {}
        ''').parse_syntax()
        self.assertEqual(read.args[1], [('f', 'ref', 'fn()->&i64')])
        self.assertEqual(advance.args[1], [('f', 'mut', 'fn()->i64')])
        self.assertEqual(take.args[1], [('f', 'scalar', 'fn()->i64')])
        self.assertEqual(take.mutable_parameters, frozenset({'f'}))
        self.assertEqual(ordinary.args[0], 'closure')
        for typ in ('closure() -> i64', '&mut fn mut() -> i64', 'fn()'):
            with self.subTest(typ=typ), self.assertRaises(Error):
                Parser(f'fn read(f: {typ}) {{}}').parse_syntax()

    def test_qualified_type_paths_are_preserved_in_syntax(self):
        function, = Parser("""
            fn read(callback: fn(&network::Packet) -> &network::Packet,
                    table: &HashMap<i64, &network::Packet>)
                -> runtime::AsyncHandle<network::Packet> {}
        """).parse_syntax()
        self.assertEqual(function.args[1], [
            ('callback', 'scalar', 'fn(&network::Packet)->&network::Packet'),
            ('table', 'ref', 'HashMap<i64,&network::Packet>'),
        ])
        self.assertEqual(function.args[2][1], 'runtime::AsyncHandle<network::Packet>')
        for name in ('network::', 'network:Packet', 'network::42', 'network::bool',
                     'bool::Packet', 'A', 'Execution<i64>', 'runtime'):
            with self.subTest(name=name), self.assertRaises(Error):
                Parser(f'fn read(packet: &{name}) {{}}').parse_syntax()

    def test_raw_core_does_not_accept_experimental_runtime_type(self):
        source = 'fn read(task: runtime::Future) {}'
        with self.assertRaisesRegex(Error, 'hors du core'):
            Parser(source, experimental_scheduler=True).parse_syntax()

    def test_raw_path_separator_is_one_token_next_to_nested_generics(self):
        function, = Parser('fn main(){let p:Option<A<network::Packet>>=value; "a: :b";}').parse_syntax()
        self.assertEqual(function.args[3][0].annotation, 'Option<A<network::Packet>>')
        for separator in (': :', ':\n:', ': // comment\n:'):
            with self.subTest(separator=separator), self.assertRaisesRegex(Error, 'doit être contigu'):
                Parser(f'fn main(){{let p:Option<A<network{separator}Packet>>=value;}}').parse_syntax()

    def test_nested_type_arguments_and_closure_parameter_separators(self):
        node, = Parser("""
            fn consume(callback: fn(Pool<&i64>, Mutex<&mut i64>) -> A<&i64>) {}
        """).parse_syntax()
        self.assertEqual(node.args[1][0][2], 'fn(Pool<&i64>,Mutex<&mut i64>)->A<&i64>')
        node, = Parser('fn main(){let read=|x:&i64,| -> &i64 {x};}').parse_syntax()
        literal = node.args[3][0].args[1]
        self.assertEqual(literal[2], (('x', '&i64', False),))
        for source in (
            'fn consume(x:fn(&i64,)->i64) {}',
            'fn consume(x:Pool<&>) {}',
            'fn consume(x:A<&&i64>) {}',
        ):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(source).parse_syntax()

    def test_slice_syntax_requires_borrow_and_keeps_element_type(self):
        function, = Parser("""
            fn read(values: &[i64], points: &mut [network::Point],
                    callback: fn(&[i64]) -> &[i64]) -> &[i64] {}
        """).parse_syntax()
        self.assertEqual(function.args[1], [
            ('values', 'ref', '[i64]'),
            ('points', 'mut', '[network::Point]'),
            ('callback', 'scalar', 'fn(&[i64])->&[i64]'),
        ])
        self.assertEqual(function.args[2], ('ref', '[i64]'))
        for typ in ('[i64]', 'fn([u8])->i64', 'Option<[u8]>'):
            with self.subTest(typ=typ), self.assertRaisesRegex(Error, 'tranche dynamique'):
                Parser(f'fn read(x: {typ}) {{}}').parse_syntax()

    def test_syntax_preserves_handle_types_and_annotated_literals_before_typing(self):
        declaration = """
            fn inspect(handle: &runtime::AsyncHandle<i64>) -> runtime::AsyncHandle<i64> {}
        """
        node, = Parser(declaration).parse_syntax()
        self.assertEqual(node.args[1], [('handle', 'ref', 'runtime::AsyncHandle<i64>')])
        self.assertEqual(node.args[2][1], 'runtime::AsyncHandle<i64>')
        with self.assertRaisesRegex(Error, 'se transmet par valeur'):
            Parser(declaration).parse()
        node, = Parser('fn main(){let value:u8=256;}').parse_syntax()
        self.assertEqual(node.args[3][0].annotation, 'u8')
        with self.assertRaisesRegex(Error, 'hors des bornes'):
            Parser('fn main(){let value:u8=256;}').parse()

    def test_qualified_implementation_and_lock_annotation_syntax(self):
        node, = Parser("""
            impl network::Point {
                #(lock: on=self)
                fn read(&self) -> i64 {}
                #(lock: on=self, through_result=true)
                fn acquire(&mut self) -> Ticket {}
            }
        """).parse_syntax()
        self.assertEqual(node.args[0], 'network::Point')
        self.assertEqual([method.lock_contract for method in node.args[1]], [False, True])
        for source in (
            'impl network:: {}',
            'impl Point { #(lock, on=self) fn read(&self) {} }',
            'impl Point { #(lock: on=self, through_result=false) fn read(&self) {} }',
        ):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(source).parse_syntax()

    def test_core_enum_requires_a_variant(self):
        node, _ = Parser('enum Choice { First, Second { value:i64 }, } fn main() {}').parse_syntax()
        self.assertEqual([name for name, _ in node.args[1]], ['First', 'Second'])
        with self.assertRaisesRegex(Error, 'au moins une variante'):
            Parser('enum Choice {}').parse_syntax()

    def test_qualified_value_paths_and_calls_in_raw_syntax(self):
        function, = Parser("""
            async fn read() {
                network::io::prepare();
                let port = network::DEFAULT;
                network::io::read(port).await;
            }
        """).parse_syntax()
        prepare, binding, wait = function.args[3]
        self.assertEqual(prepare.args[0], ('call', 'network::io::prepare', []))
        self.assertEqual(binding.args[1], ('name', 'network::DEFAULT'))
        self.assertEqual(wait.args[0], ('await', ('call', 'network::io::read', [('name', 'port')])))
        for source in ('network::io::();', 'let n=network::42;', 'let n=network::bool;', 'let n=network:DEFAULT;',
                       'runtime::select_group();'):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(f'fn main() {{ {source} }}').parse_syntax()

    def test_pool_new_suffix_accepts_composed_receivers(self):
        function, = Parser("""
            fn main() {
                let named=get_pool().new(x:1, y:2,);
                let defaulted=holder.points.new();
                let positional=get_pool().new(3);
            }
        """).parse_syntax()
        named, defaulted, positional = (node.args[1] for node in function.args[3])
        self.assertEqual(named, ('syntax_new', ('call', 'get_pool', []),
                                (('x', ('numeric_integer', 1)), ('y', ('numeric_integer', 2)))))
        self.assertEqual(defaulted, ('method_call', ('field', 'holder', 'points'), 'new', []))
        self.assertEqual(positional, ('method_call', ('call', 'get_pool', []), 'new', [('numeric_integer', 3)]))
        function, = Parser('fn main(){let x=points.new(data::value); }').parse_syntax()
        self.assertEqual(function.args[3][0].args[1],
                         ('method_call', ('name', 'points'), 'new', [('name', 'data::value')]))
        for args in ('x:', 'x:1, 2', '1, 2', 'point.x:1', 'bool:1'):
            with self.subTest(args=args), self.assertRaises(Error):
                Parser(f'fn main(){{let point=get_pool().new({args});}}').parse_syntax()

    def test_raw_core_type_parentheses_only_spell_unit(self):
        function, = Parser('fn main() -> () { () }').parse_syntax()
        self.assertEqual(function.args[2][1], '()')
        with self.assertRaises(Error):
            Parser('fn split() -> (&mut [u8], &mut [u8]) {}').parse_syntax()

    def test_raw_core_program_only_accepts_declarations_at_root(self):
        source = """
            #(directive: async_pool_sizes={work:1})
            struct Point { x:i64 }
            enum Choice { First, Second }
            impl Point { fn read(&self) -> i64 { self.x } }
            extern "C" fn external(x:i64) -> i64;
            async fn work() {}
            fn main() {}
        """
        self.assertEqual([node.op for node in Parser(source).parse_syntax()],
                         ['async_pool_sizes', 'struct', 'enum', 'impl', 'fn', 'async_fn', 'fn'])
        for source in ('let value=1;', 'print(1);', 'fn main(){fn inner(){}}',
                       'fn main(){struct Inner {}}', 'fn main(){async fn inner(){}}'):
            with self.subTest(source=source), self.assertRaisesRegex(Error, 'niveau du programme'):
                Parser(source).parse_syntax()
        self.assertEqual(Parser('let value=1;').parse()[0].op, 'var')

    def test_raw_foreign_declaration_and_call_precede_unsafe_check(self):
        source = 'extern "C" fn send(value:i64,) -> (); fn main(){send(42);}'
        foreign, main = Parser(source).parse_syntax()
        self.assertTrue(foreign.foreign)
        self.assertEqual(foreign.args[1:4], ([('value', 'i64', 'i64')], ('void', 'Void'), []))
        self.assertEqual(main.args[3][0].args[0][0:2], ('call', 'send'))
        with self.assertRaisesRegex(Error, 'exige un bloc unsafe'):
            Parser(source).parse()
        for invalid in (source.replace('"C"', '"Rust"'), source.replace('value:i64', 'value:&i64'),
                        source.replace('-> ();', '-> () {}')):
            with self.subTest(source=invalid), self.assertRaises(Error):
                Parser(invalid).parse_syntax()

    def test_raw_entry_declarations_precede_entry_point_checks(self):
        source = 'extern "C" fn main();'
        foreign, = Parser(source).parse_syntax()
        self.assertTrue(foreign.foreign)
        self.assertEqual(foreign.args[0], 'main')
        asynchronous, = Parser('async fn main() {}').parse_syntax()
        self.assertEqual(asynchronous.op, 'async_fn')
        with self.assertRaisesRegex(Error, 'main doit être une fonction Crust synchrone'):
            Parser(source).parse()
        with self.assertRaises(Error):
            Parser('extern "C" fn main() {}').parse_syntax()

    def test_raw_core_preserves_i32_spelling_before_abi_lowering(self):
        foreign, function = Parser('''extern "C" fn measure(value:i32) -> i32;
            fn read(map: HashMap<i32, &i32>) -> i32 { let x:i32=1; x }
        ''').parse_syntax()
        self.assertEqual(foreign.args[1][0][2], 'i32')
        self.assertEqual(foreign.args[2][1], 'i32')
        self.assertEqual(function.args[1][0][2], 'HashMap<i32,&i32>')
        self.assertEqual(function.args[2][1], 'i32')
        self.assertEqual(function.args[3][0].annotation, 'i32')
        with self.assertRaisesRegex(Error, 'clé HashMap'):
            Parser('fn read(map: HashMap<Int, i32>) {}').parse_syntax()

    def test_raw_signature_preserves_types_before_signature_lowering(self):
        function, = Parser('''async fn work(value: A<i32>, flag: bool,
            view: &[u8], handle: runtime::AsyncHandle<i64>) -> A<i32> {}
        ''').parse_syntax()
        self.assertEqual(function.args[1], [
            ('value', 'scalar', 'A<i32>'), ('flag', 'scalar', 'bool'),
            ('view', 'ref', '[u8]'), ('handle', 'scalar', 'runtime::AsyncHandle<i64>'),
        ])
        self.assertEqual(function.args[2], ('scalar', 'A<i32>'))

    def test_raw_method_signature_requires_self_first(self):
        node, = Parser("""
            impl Point {
                fn read(&self) {}
                fn edit(&mut self, value:i64,) {}
                fn finish(mut self:Point) {}
            }
        """).parse_syntax()
        self.assertEqual([method.args[1][0] for method in node.args[1]], [
            ('self', 'ref', 'Point'), ('self', 'mut', 'Point'), ('self', 'scalar', 'Point'),
        ])
        for declaration in ('impl Point { fn read() {} }',
                            'impl Point { fn read(value:i64, self:Point) {} }',
                            'fn read(self:Point) {}'):
            with self.subTest(declaration=declaration), self.assertRaisesRegex(Error, 'self'):
                Parser(declaration).parse_syntax()

    def test_raw_enum_construction_distinguishes_variant_from_field(self):
        declaration = 'enum Choice { First, Second { n:i64 } }'
        _, function = Parser(declaration + """
            fn main() {
                let simple=Choice.First;
                let populated=Choice.Second { n:42 };
                let projected=holder.First;
            }
        """).parse_syntax()
        simple, populated, projected = (node.args[1] for node in function.args[3])
        self.assertEqual(simple, ('new_enum', None, 'Choice', 'First', []))
        self.assertEqual(populated, ('new_enum', None, 'Choice', 'Second', [('n', ('numeric_integer', 42))]))
        self.assertEqual(projected, ('field', 'holder', 'First'))
        _, function = Parser(declaration + 'fn main(){ match Choice.First { Choice.First => {} } }').parse_syntax()
        self.assertEqual(function.args[3][0].args[0][1], simple)
        for expression in ('Choice.', 'Choice.42', 'Choice.Second { n: }'):
            with self.subTest(expression=expression), self.assertRaises(Error):
                Parser(declaration + f'fn main(){{let value={expression};}}').parse_syntax()

    def test_raw_reserved_identifiers_are_contextual(self):
        Parser("""
            struct Packet { bytes:u8 }
            impl Packet { fn read(self:Packet)->u8 { self.bytes } }
            fn main(){ match result { Some(_) => {}, None => {} } }
        """).parse_syntax()
        for source in ('fn runtime() {}', 'struct Vector {}', 'enum Choice { bool }',
                       'fn read(self:i64) {}', 'fn main(){let _=0;}',
                       'fn main(){let read=|return:i64| {1};}'):
            with self.subTest(source=source), self.assertRaisesRegex(Error, 'identifiant réservé'):
                Parser(source).parse_syntax()

    def test_raw_value_paths_require_ordinary_identifiers(self):
        Parser('impl Packet { fn read(&self) { self.bytes; i64::try_from(1); runtime::Error::LaunchFailed } }').parse_syntax()
        for expression in ('bool', 'runtime', 'self::bytes', 'self()', 'packet._', 'packet.return',
                           'i64::bool', 'runtime::Error::bool', 'runtime::select(work())',
                           'runtime::start_poller()', 'runtime::set_scheduler(scheduler)'):
            with self.subTest(expression=expression), self.assertRaises(Error):
                Parser(f'fn main(){{let value={expression};}}', experimental_scheduler=True).parse_syntax()

    def test_raw_empty_enum_initializer_and_following_block_are_distinct(self):
        _, function = Parser('''enum Choice { First }
            fn main(){
                if Choice.First {} else {}
                while Choice.First {} {}
                let value = Choice.First {};
                if Choice.First {} {}
            }
        ''').parse_syntax()
        conditional, loop, binding, tail = function.args[3]
        variant = ('new_enum', None, 'Choice', 'First', [])
        self.assertEqual(conditional.args[0][2], variant)
        self.assertEqual(loop.args[0][0].args[0][2], variant)
        self.assertEqual(binding.args[1], variant)
        self.assertEqual(tail.args[0][0], 'if_expr')

    def test_raw_struct_name_before_condition_block_keeps_both_forms(self):
        _, function = Parser('''struct Packet { field:i64 }
            fn inspect(Packet: bool) {
                if Packet { print(1); }
                while Packet {} 
                if Packet {} else {}
                if Packet { field: 1 } {}
            }
        ''').parse_syntax()
        first, loop, conditional, tail = function.args[3]
        self.assertEqual(first.args[0][2], ('name', 'Packet'))
        self.assertEqual(loop.args[0][0].args[0][2], ('name', 'Packet'))
        self.assertEqual(conditional.args[0][2], ('name', 'Packet'))
        self.assertEqual(tail.args[0][1][2], (
            'new_enum', None, 'Packet', '', [('field', ('numeric_integer', 1))]))

    def test_raw_enum_name_can_start_an_ordinary_method_call(self):
        _, impl = Parser('''enum Choice { First }
            impl Choice { fn inspect(&self, Choice: i64) {
                let result = Choice.read();
                let waiting = Choice.await;
            } }
        ''').parse_syntax()
        result, waiting = (node.args[1] for node in impl.args[1][0].args[3])
        self.assertEqual(result, ('method_call', ('name', 'Choice'), 'read', []))
        self.assertEqual(waiting, ('await', ('name', 'Choice')))

    def test_raw_empty_if_block_can_precede_an_operator_or_suffix(self):
        _, function = Parser('''enum Choice { First }
            fn main() {
                let sum = if Choice.First {} + 1;
                let call = if Choice.First {}.read();
                let test = if Choice.First {} == 1 {};
            }
        ''').parse_syntax()
        total, call, test = (node.args[1] for node in function.args[3])
        self.assertEqual(total[:2], ('numeric_binary', '+'))
        self.assertEqual(total[2][0], 'if_expr')
        self.assertEqual(call[0], 'method_call')
        self.assertEqual(call[1][0], 'if_expr')
        self.assertEqual(test[1][2][0], 'if_expr')

    def test_raw_pool_constructor_accepts_reference_type_syntax(self):
        function, = Parser('fn main(){ let values = pool<&mut i64>(4); }').parse_syntax()
        self.assertEqual(function.args[3][0].args[1], ('source', 'pool', 4, '&mut i64'))
        with self.assertRaises(Error):
            Parser('fn main(){ let values = pool<&mut>(4); }').parse_syntax()

    def test_raw_pool_name_is_contextual(self):
        _, function = Parser('''fn pool() {}
            fn main(){
                let source = pool<Pool<[i32; 2]>>(4);
                let pool = source;
                pool.new();
                let ordered = pool < limit >> 1;
                pool();
                let nested = pool < (threshold > (0));
                let closures = pool<fn(Pool<i32>) -> i32>(4);
            }
        ''').parse_syntax()
        self.assertEqual(function.args[3][0].args[1], ('source', 'pool', 4, 'Pool<[i32;2]>'))
        self.assertEqual(function.args[3][2].args[0], ('method_call', ('name', 'pool'), 'new', []))
        self.assertEqual(function.args[3][3].args[1][1][3][1], '>>')
        self.assertEqual(function.args[3][4].args[0], ('call', 'pool', []))
        self.assertEqual(function.args[3][5].args[1][1][1], '<')
        self.assertEqual(function.args[3][6].args[1], ('source', 'pool', 4, 'fn(Pool<i32>)->i32'))

    def test_raw_core_builtin_constructors_use_core_forms(self):
        function, = Parser('''fn main(){
            let a = Mutex::new(42);
            let b = AsyncMutex::new(value);
            let c = HashMap<u16, i64>::new();
            let d = stack(0);
        }''').parse_syntax()
        self.assertEqual([node.args[1][0] for node in function.args[3]],
                         ['array_mutex_new', 'array_mutex_new', 'array_hashmap_new', 'call'])
        for expr in ('Mutex::new()', 'Mutex::new(1,)', 'AsyncMutex::new(1, 2)',
                     'HashMap<f32, i64>::new()', 'new(values) Int(1)'):
            with self.subTest(expr=expr), self.assertRaises(Error):
                Parser(f'fn main(){{let a={expr};}}').parse_syntax()

    def test_raw_enum_patterns_require_identifiers_for_fields_and_bindings(self):
        prefix = 'enum Choice { First { value:i64 } } fn main(){ match item { '
        suffix = ' => {} } }'
        for pattern in ('Choice.First {value: result}', 'Choice.First {value: _}'):
            with self.subTest(pattern=pattern):
                Parser(prefix + pattern + suffix).parse_syntax()
        for pattern in ('Choice.bool {}', 'Choice.First {_: result}',
                        'Choice.First {value: self}'):
            with self.subTest(pattern=pattern), self.assertRaisesRegex(Error, 'identifiant réservé'):
                Parser(prefix + pattern + suffix).parse_syntax()

    def test_raw_contract_syntax_precedes_distinctness_and_receiver_type_checks(self):
        source = '''
            #(type: T<T: &i64, bool> with {
                fn read(self: Other);
                fn read(&self);
            })
            fn inspect(value: T) {}
        '''
        function, = Parser(source).parse_syntax()
        _, (_, _, alternatives, methods, _) = function.type_annotations[0]
        self.assertEqual(alternatives, ('&i64', 'bool'))
        self.assertEqual(len(methods), 2)
        with self.assertRaisesRegex(Error, 'noms distincts'):
            Parser(source).parse()
        for annotation in ('#(type: T<R> with {})', '#(type: bool *)',
                           '#(branch: join=result.bool())'):
            with self.subTest(annotation=annotation), self.assertRaises(Error):
                Parser(annotation + ' fn inspect() {}').parse_syntax()

    def test_raw_launch_syntax_precedes_context_and_task_checks(self):
        function, = Parser('fn main(){ runtime::spawn_blocking(42); runtime::spawn(work()); }').parse_syntax()
        blocking, ordinary = (node.args[0] for node in function.args[3])
        self.assertEqual(blocking, ('call', 'runtime::spawn_blocking', [('numeric_integer', 42)]))
        self.assertEqual(ordinary, ('call', 'runtime::spawn', [('call', 'work', [])]))
        for args in ('', 'work(), other()', 'work(),'):
            with self.subTest(args=args), self.assertRaises(Error):
                Parser(f'fn main(){{runtime::spawn({args});}}').parse_syntax()

    def test_stacked_type_annotations_are_parsed_in_order(self):
        signature = """
            #(type: R *)
            #(type: T<R> with {
                fn id(&self) -> i64;
                fn poll(&mut self, ctx: &mut runtime::Context) -> runtime::Poll<R>;
            })
            #(branch: join=result.join())
            fn spawn(t: T) -> runtime::Handle<R> {}
        """
        for keyword, mode in ((' with', 'with'), ('', 'exact')):
            with self.subTest(mode=mode):
                source = signature.replace(' with', keyword)
                function, = Parser(source).parse_syntax()
                free, methods = function.type_annotations
                self.assertEqual(free, ('free', 'R'))
                self.assertEqual(methods[0], mode)
                self.assertEqual([method.args[0] for method in methods[1][3]], ['id', 'poll'])
                self.assertEqual(function.branch_wait, 'join')
        for source in (signature.replace('R *', 'R'), signature.replace('T<R>', 'T<>'),
                       signature.replace('-> i64;', '-> i64')):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(source).parse_syntax()

    declarations = '''
        struct Counter { n: i64 }
        struct Flag { enabled: bool }
        impl Counter {
            fn id(&self) -> i64 { self.n }
            fn read(&self) -> i64 { self.n }
            fn extra(&self) {}
        }
        impl Flag {
            fn id(&self) -> i64 { 7 }
            fn read(&self) -> bool { self.enabled }
        }
    '''
    contract = '''
        #(type: T<R: i64, bool> with {
            fn id(&self) -> i64;
            fn read(&self) -> R;
        })
        fn inspect(t: &T) -> R { print(t.id()); t.read() }
    '''
    future_contract = '''
        #(type: T<R> with {
            fn id(&self) -> i64;
            fn poll(&mut self, ctx: &mut runtime::Context) -> runtime::Poll<R>;
        })
        fn launch(t: T) -> runtime::Handle<R> { runtime::spawn(t) }
    '''

    def test_nominal_types_specialize_result_and_keep_numeric_context(self):
        result = TypeFeatureTests.native(self, self.declarations + self.contract + '''
            fn main() {
                let c = Counter {n: 42};
                let flag = Flag {enabled: true};
                print(inspect(&c) + 1);
                if inspect(&flag) { print(1); }
            }
        ''')
        self.assertEqual(result.stdout, '42\n43\n7\n1\n')

    def test_requirements_are_checked_without_call_and_per_specialization(self):
        with self.assertRaisesRegex(Error, 'extra.*non garantie'):
            verify_program(self.declarations + self.contract.replace('print(t.id());', 't.extra();'))
        use = 'fn main(){let flag=Flag{enabled:true};if inspect(&flag){print(1);}}'
        with self.assertRaisesRegex(Error, 'paramètre de type unique compatible'):
            verify_program(self.declarations + self.contract.replace('i64, bool', 'i64') + use)
        with self.assertRaisesRegex(Error, "exigence de contrat.*id"):
            verify_program(self.declarations.replace('fn id(&self) -> i64 { 7 }',
                'fn id(&mut self) -> i64 { 7 }') + self.contract + use)
        inconsistent = self.contract.replace('fn id(&self) -> i64;', 'fn id(&self) -> R;')
        with self.assertRaisesRegex(Error, "exigence de contrat.*read"):
            verify_program(self.declarations + inconsistent + use)

    def test_future_contract_preserves_result_and_capture_through_join(self):
        source = self.future_contract + '''
            async fn calculer(n: &i64) -> i64 { yield; *n }
            fn main() {
                let mut numbers = pool<i64>(1);
                let n = numbers.new(6);
                let h = launch(calculer(n.vref()));
                match h.join() {
                    Ok(value) => { print(value); },
                    Err(_) => { print(0); },
                }
                drop(n);
            }
        '''
        self.assertEqual(TypeFeatureTests.native(self, source).stdout, '6\n')
        invalid = source.replace('                drop(n);', '').replace(
            '                match h.join()', '                drop(n);\n                match h.join()')
        with self.assertRaisesRegex(Error, 'emprunt|référenc|réserv'):
            verify_program(invalid)
        with self.assertRaisesRegex(Error, 'spawn exige le contrat Future'):
            verify_program(self.future_contract.replace('fn id(&self) -> i64;', ''))


class TypeFeatureTests(unittest.TestCase):
    declarations = '''
        type feature Tracer { fn trace(&self); }
        struct Console { niveau: Int }
        struct Journal { compteur: Int }
        impl Console { fn trace(self: &Console) { print(self.niveau); }
                       fn flush(self: &Console) { print(99); } }
        impl Journal { fn trace(self: &Journal) { print(self.compteur); } }
    '''

    def native(self, source, **options):
        cc = shutil.which('clang') or shutil.which('cc')
        if cc is None:
            self.skipTest('C compiler unavailable')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'program.c'
            binary = Path(folder)/'program'
            code = compile_source(source, **options)
            path.write_text(code)
            flags = ['-pthread'] if code.startswith('#define CRUST_THREAD_RUNTIME 1\n') else []
            build = subprocess.run([cc, '-std=c11', os.environ.get('CRUST_TEST_OPT', '-O2'),
                                    '-fsanitize=undefined', '-fno-sanitize-recover=all',
                                    *flags, str(path), '-o', str(binary)], capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result

    def test_independent_arguments_relay_and_concrete_borrowed_result(self):
        source = self.declarations + '''
            fn tracer(t: &Tracer) { t.trace(); }
            fn tracer_deux(a: &Tracer, b: &Tracer) { tracer(a); tracer(b); }
            fn restituer(t: &Tracer) -> &Tracer { t.trace(); return t; }
            fn relay(t: &Tracer) -> &Tracer { return restituer(t); }
            fn main() {
                let console=Console {niveau:1}; let journal=Journal {compteur:2};
                tracer_deux(&console,&journal);
                let result=relay(&console);print(result.niveau);
                let second=relay(&journal);print(second.compteur);
            }
        '''
        result = self.native(source)
        self.assertEqual(result.stdout, '1\n2\n1\n1\n2\n2\n')
        self.assertEqual(result.stderr.count('destroy console=Console'), 1)
        self.assertEqual(result.stderr.count('destroy journal=Journal'), 1)
        compiler=Compiler();compiler.compile(Parser(source).parse())
        concrete=[node.args[2] for name,node in compiler.functions.items() if name.startswith('relay$feature')]
        self.assertCountEqual(concrete, [('ref','Console'),('ref','Journal')])
        self.assertEqual(compiler.verified_functions,set(compiler.functions))
        for node in compiler.functions.values():
            self.assertNotIn('Tracer',[typ for _,_,typ in node.args[1]])
        self.assertTrue(all(name in compiler.function_contracts
                            for names in compiler.body_call_contracts.values() for name in names))

    def test_abstract_guarantees_reject_extra_methods_even_without_calls(self):
        for body in ('t.flush();', 'let alias=t;alias.flush();',
                     'if false {t.flush();}', 'let ignored=if true {t.flush();1}else{2};print(ignored);'):
            for call in ('', 'let c=Console{niveau:1};bad(&c);'):
                source=self.declarations+f'fn bad(t:&Tracer){{{body}}}fn main(){{{call}}}'
                with self.subTest(body=body,call=call), self.assertRaisesRegex(Error,'non garantie'):
                    verify_program(source)

    def test_indirect_requirements_are_checked_structurally(self):
        source=self.declarations+'''
            type feature AutreTrace { fn trace(&self); }
            fn inner(x:&AutreTrace){x.trace();}
            fn outer(x:&Tracer){inner(x);}
            fn main(){let c=Console{niveau:4};outer(&c);}
        '''
        self.assertEqual(self.native(source).stdout,'4\n')
        bad=source.replace('fn trace(&self); }\n            fn inner','fn flush(&self); }\n            fn inner').replace('fn inner(x:&AutreTrace){x.trace();}','fn inner(x:&AutreTrace){x.flush();}')
        with self.assertRaisesRegex(Error,'exigence de feature.*non garantie'):
            verify_program(bad)
        with self.assertRaisesRegex(Error,'type concret.*non garanti'):
            verify_program(self.declarations+'fn concrete(c:&Console){c.flush();}fn bad(t:&Tracer){concrete(t);}')

    def test_declaration_storage_and_signature_rejections(self):
        for declaration in ('type feature Empty {}',
                            'type feature Many {fn a(&self);fn b(&self);}',
                            'type feature Static {fn a();}',
                            'type feature Plain {fn a(self);}',
                            'type feature Duplicate {fn a(&self,n:Int,n:Int);}',
                            'type feature T {fn a(&self){}}'):
            with self.subTest(declaration=declaration),self.assertRaises(Error):
                verify_program(declaration+'fn main(){}')
        with self.assertRaisesRegex(Error,'main doit'):
            verify_program(self.declarations+'fn main(t:&Tracer){t.trace();}')
        for body in ('struct Bad{value:Tracer}', 'struct Bad{value:&Tracer}',
                     'struct Bad{value:Vector<Tracer>}',
                     'fn bad(x:Vector<Tracer>){}', 'fn bad(x:Tracer){}',
                     'fn main(){let p=pool<Tracer>(1);}',
                     'fn bad(x:&Tracer){let y:Tracer=x;}',
                     'fn bad(x:-> A<Tracer>){drop(->x);}'):
            with self.subTest(body=body),self.assertRaises(Error):
                verify_program(self.declarations+body)
        for method in ('', 'fn trace(mut self:&mut Wrong){}',
                       'fn trace(self:&Wrong,n:Int){}', 'fn trace(self:&Wrong)->Int{return 1;}'):
            source=self.declarations+f'struct Wrong{{x:Int}}impl Wrong{{{method}}}'+'''
                fn use(t:&Tracer){t.trace();}fn main(){let w=Wrong{x:1};use(&w);}
            '''
            with self.subTest(method=method),self.assertRaisesRegex(Error,'exigence de feature'):
                verify_program(source)
        # A declared requirement remains mandatory when this body happens not
        # to invoke the method; ordinary call-result checks cannot stand in for it.
        with self.assertRaisesRegex(Error,'exigence de feature'):
            verify_program(self.declarations+'''
                struct Wrong{x:Int}
                impl Wrong{fn trace(self:&Wrong)->Int{return 1;}}
                fn accept(t:&Tracer){print(1);}
                fn main(){let w=Wrong{x:1};accept(&w);}
            ''')

    def test_mutable_receiver_preserves_exclusivity_and_last_use(self):
        source='''
            type feature Ajouter {fn ajouter(&mut self,n:Int);}
            struct Counter{value:Int}
            impl Counter{fn ajouter(mut self:&mut Counter,n:Int){self.value=n;}}
            fn add(mut c:&mut Ajouter,n:Int){c.ajouter(n);}
            fn main(){let mut c=Counter{value:1};add(&mut c,7);print(c.value);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('add(&mut c,7);','let view=&c;add(&mut c,7);print(view.value);'))
        with self.assertRaisesRegex(Error,'mutable'):
            verify_program(source.replace('fn add(mut c:&mut Ajouter','fn add(c:&Ajouter'))

    def test_consuming_receiver_cleans_original_pool_and_invalidates_caller(self):
        source='''
            type feature Fermer {fn fermer(-> self);}
            struct Item{value:Int}
            impl Item{fn fermer(self:-> Item){print(self.value);}}
            fn close(item:-> Fermer){(-> item).fermer();}
            fn main(){let mut p=pool<Item>(1);let item=p.new(value:7);
                address(item);close(-> item);
                let next=p.new(value:9);address(next);print(next.value);}
        '''
        result=self.native(source)
        before,value,after,next_value=result.stdout.splitlines()
        self.assertEqual((before,value,next_value),(after,'7','9'))
        self.assertEqual(result.stderr.count('destroy item=Item'),1)
        with self.assertRaisesRegex(Error,'plus utilisable'):
            verify_program(source.replace('let next=', 'print(item.value);let next='))
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('close(-> item);','let view=&item;close(-> item);print(view.value);'))
        with self.assertRaisesRegex(Error,'receveur consommé'):
            verify_program(source.replace('(-> item).fermer();','item.fermer();'))

    def test_borrowed_result_keeps_concrete_dependency_until_last_use(self):
        source='''
            type feature Lire {fn lire(&self)->&Int;}
            struct Holder{value:&Int}
            impl Holder{fn lire(self:&Holder)->&Int{return self.value;}}
            fn read(h:&Lire)->&Int{return h.lire();}
            fn relay(h:&Lire)->&Int{return read(h);}
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);
                let h=Holder{value:&n};let view=relay(&h);print(*view);
                drop(-> h);drop(-> n);let next=p.new(9);print(*next);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n9\n')
        with self.assertRaisesRegex(Error,'emprunt|dépend'):
            verify_program(source.replace('print(*view);\n                drop(-> h);drop(-> n);',
                                          'drop(-> h);drop(-> n);print(*view);'))

    def test_concrete_reset_effect_is_not_erased_by_feature(self):
        source='''
            type feature Effacer {fn effacer(&self,p:&mut Pool<Int>);}
            struct Cleaner{value:Int}
            impl Cleaner{fn effacer(self:&Cleaner,p:&mut Pool<Int>){p.reset();}}
            fn clear(c:&Effacer,p:&mut Pool<Int>){c.effacer(p);}
            fn relay(c:&Effacer,p:&mut Pool<Int>){clear(c,p);}
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);print(*n);
                let c=Cleaner{value:0};relay(&c,&mut p);}
        '''
        result=self.native(source,allow_legacy_reset=True)
        self.assertEqual(result.stdout,'7\n')
        self.assertEqual(result.stderr.count('destroy n=7'),1)
        with self.assertRaisesRegex(Error,'reset|plus utilisable'):
            verify_program(source.replace('relay(&c,&mut p);','relay(&c,&mut p);print(*n);'),allow_legacy_reset=True)

    def test_result_feature_requires_one_concrete_type_on_all_paths(self):
        prefix=self.declarations+'''
            fn choose(a:&Tracer,b:&Tracer,n:Int)->&Tracer{
                if n==0{return a;}return b;
            }
        '''
        good=prefix+'''fn main(){let a=Console{niveau:3};let b=Console{niveau:4};
            let x=choose(&a,&b,1);print(x.niveau);}'''
        self.assertEqual(self.native(good).stdout,'4\n')
        with self.assertRaisesRegex(Error,'type concret unique'):
            verify_program(good.replace('let b=Console{niveau:4}','let b=Journal{compteur:4}'))

    def test_nested_block_and_conditional_argument_resolve_actual_type(self):
        source=self.declarations+'''
            fn tracer(t:&Tracer){t.trace();}
            fn main(){let selected=if true {let a=Console{niveau:5};<- a}
                                             else {let b=Console{niveau:6};<- b};
                tracer(&selected);
                let second={let c=Console{niveau:6};<- c};tracer(&second);}
        '''
        self.assertEqual(self.native(source).stdout,'5\n6\n')

    def test_explicit_reborrows_and_generic_method_parameters(self):
        source=self.declarations+'''
            struct Forward{value:Int}
            impl Forward{fn forward(self:&Forward,t:&Tracer){t.trace();}}
            fn tracer(t:&Tracer){t.trace();}
            fn relay(t:&Tracer){tracer(&*t);let again=&*t;tracer(again);}
            fn main(){let c=Console{niveau:8};let f=Forward{value:0};
                f.forward(&c);relay(&c);}
        '''
        self.assertEqual(self.native(source).stdout,'8\n8\n8\n')
        with self.assertRaisesRegex(Error,'non garantie'):
            verify_program(self.declarations+'fn bad(t:&Tracer){let again=&*t;again.flush();}')

    def test_feature_result_does_not_promote_a_function_local(self):
        source=self.declarations+'''
            fn id(t:&Tracer)->&Tracer{return t;}
            fn escape()->&Tracer{let c=Console{niveau:7};return id(&c);}
            fn main(){let r=escape();print(r.niveau);}
        '''
        with self.assertRaisesRegex(Error,'emprunt|local|survit|retourn'):
            verify_program(source)

    def test_owned_feature_result_keeps_local_identity_and_rejects_pool_value(self):
        source='''
            type feature Fermer{fn fermer(-> self);}
            struct Item{value:Int}
            impl Item{fn fermer(self:-> Item){print(self.value);}}
            fn identity(item:-> Fermer)-><- Fermer{return <- item;}
            fn relay(item:-> Fermer)-><- Fermer{let result=identity(-> item);return <- result;}
            fn main(){let mut p=pool<Item>(1);let first=p.new(value:7);address(first);
                let second=relay(-> first);address(second);print(second.value);
                drop(-> second);let reused=p.new(value:9);address(reused);print(reused.value);}
        '''
        # The consuming implementation above takes Item, not A<Item> (H3).
        # A pool allocation cannot silently acquire the local storage contract.
        for checker in (verify_program, compile_source):
            with self.subTest(checker=checker.__name__), self.assertRaisesRegex(Error, 'stockage local.*pool'):
                checker(source)
        source=source.replace('let mut p=pool<Item>(1);let first=p.new(value:7);',
                              'let first=Item{value:7};').replace('let reused=p.new(value:9);',
                                                                 'let reused=Item{value:9};')
        result=self.native(source)
        first,second,value,reused,next_value=result.stdout.splitlines()
        self.assertEqual((first,second,value,next_value),(reused,reused,'7','9'))
        with self.assertRaisesRegex(Error,'plus utilisable'):
            verify_program(source.replace('address(second);','address(second);print(first.value);'))
        bad=source[:source.index('fn main()')]+'''
            fn main(){let second={let mut p=pool<Item>(1);let first=p.new(value:7);
                let returned=identity(-> first);<- returned};print(second.value);}
        '''
        for checker in (verify_program, compile_source):
            with self.subTest(checker=checker.__name__), self.assertRaisesRegex(Error, 'stockage local.*pool'):
                checker(bad)

    def test_mutable_feature_result_reserves_caller_until_last_use(self):
        source='''
            type feature Ajouter{fn ajouter(&mut self,n:Int);}
            struct Counter{value:Int}
            impl Counter{fn ajouter(mut self:&mut Counter,n:Int){self.value=n;}}
            fn identity(mut c:&mut Ajouter)->&mut Ajouter{return c;}
            fn add(mut c:&mut Ajouter){c.ajouter(7);}
            fn main(){let mut c=Counter{value:1};let mut view=identity(&mut c);
                add(view);print(c.value);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('add(view);print(c.value);','print(c.value);add(view);'))

    def test_statement_loop_break_does_not_become_a_function_result(self):
        source=self.declarations+'''
            fn identity(t:&Tracer)->&Tracer{loop{break;}return t;}
            fn main(){let c=Console{niveau:9};let result=identity(&c);print(result.niveau);}
        '''
        self.assertEqual(self.native(source).stdout,'9\n')

    def test_method_feature_arguments_do_not_imply_equal_concrete_types(self):
        source='''
            type feature Visit{fn visit(&self,other:&Visit)->Int;}
            struct Left{value:Int}struct Right{value:Int}
            impl Left{fn visit(self:&Left,other:&Visit)->Int{return self.value;}}
            impl Right{fn visit(self:&Right,other:&Visit)->Int{return self.value;}}
            fn apply(a:&Visit,b:&Visit)->Int{return a.visit(b);}
            fn relay(a:&Visit,b:&Visit)->Int{return apply(a,b);}
            fn main(){let a=Left{value:7};let b=Right{value:9};
                print(relay(&a,&b));print(relay(&b,&a));}
        '''
        self.assertEqual(self.native(source).stdout,'7\n9\n')
        # A method accepting only Left is not the declared independent
        # structural constraint, even if this caller happens to pass Left.
        bad=source.replace('self:&Left,other:&Visit','self:&Left,other:&Left')
        with self.assertRaisesRegex(Error,'exigence de feature'):
            verify_program(bad.replace('relay(&a,&b)','relay(&a,&a)'))

    def test_method_different_feature_argument_keeps_indirect_guarantees(self):
        source=self.declarations+'''
            type feature Forward{fn forward(&self,t:&Tracer);}
            struct Relay{value:Int}
            impl Relay{fn forward(self:&Relay,t:&Tracer){t.trace();}}
            fn apply(f:&Forward,t:&Tracer){f.forward(t);}
            fn main(){let f=Relay{value:0};let a=Console{niveau:7};
                let b=Journal{compteur:9};apply(&f,&a);apply(&f,&b);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n9\n')
        with self.assertRaisesRegex(Error,'non garantie'):
            verify_program(source.replace('{t.trace();}','{t.flush();}'))

    def test_method_independent_mutable_feature_argument_keeps_borrow(self):
        source='''
            type feature Change{fn change(&mut self,n:Int);}
            type feature Forward{fn forward(&self,t:&mut Change);}
            struct Relay{value:Int}struct Counter{value:Int}
            impl Counter{fn change(mut self:&mut Counter,n:Int){self.value=n;}}
            impl Relay{fn forward(self:&Relay,mut t:&mut Change){t.change(9);}}
            fn apply(f:&Forward,mut t:&mut Change){f.forward(t);}
            fn main(){let f=Relay{value:0};let mut a=Counter{value:7};
                apply(&f,&mut a);print(a.value);}
        '''
        self.assertEqual(self.native(source).stdout,'9\n')
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('apply(&f,&mut a);','let view=&a;apply(&f,&mut a);print(view.value);'))

    def test_method_feature_result_keeps_its_own_concrete_type(self):
        source='''
            type feature View{fn view(&self)->&View;}
            struct Target{value:Int}
            struct Wrapper{target:&Target}
            impl Target{fn view(self:&Target)->&Target{return self;}}
            impl Wrapper{fn view(self:&Wrapper)->&Target{return self.target;}}
            fn view(v:&View)->&View{return v.view();}
            fn relay(v:&View)->&View{return view(v);}
            fn main(){let target=Target{value:7};let wrapper=Wrapper{target:&target};
                let result=relay(&wrapper);print(result.value);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        with self.assertRaisesRegex(Error,'emprunt|dépend'):
            verify_program(source.replace('print(result.value);','drop(-> wrapper);drop(-> target);print(result.value);'))
        with self.assertRaisesRegex(Error,'exigence de feature'):
            verify_program(source.replace('fn view(self:&Target)->&Target{return self;}',
                                          'fn view(self:&Target)->Int{return 7;}'))

    def test_recursive_result_requirement_checks_leaf_even_when_unused(self):
        source='''
            type feature View{fn view(&self)->&View;}
            struct Leaf{value:Int}struct Middle{leaf:&Leaf}struct Outer{middle:&Middle}
            impl Leaf{fn view(self:&Leaf)->&Leaf{return self;}}
            impl Middle{fn view(self:&Middle)->&Leaf{return self.leaf;}}
            impl Outer{fn view(self:&Outer)->&Middle{return self.middle;}}
            fn accept(v:&View){print(1);}
            fn main(){let leaf=Leaf{value:7};let middle=Middle{leaf:&leaf};
                let outer=Outer{middle:&middle};accept(&outer);}
        '''
        self.assertEqual(self.native(source).stdout,'1\n')
        # A cycle at Leaf is a finite structural requirement, but an actual
        # mismatch at that leaf must not be hidden by the recursion guard.
        for method in ('fn view(self:&Leaf)->Int{return 7;}',
                       'fn view(mut self:&mut Leaf)->&Leaf{return &*self;}',
                       'fn other(self:&Leaf)->&Leaf{return self;}'):
            with self.subTest(method=method),self.assertRaisesRegex(Error,'exigence de feature'):
                verify_program(source.replace('fn view(self:&Leaf)->&Leaf{return self;}',method))

    def test_recursive_feature_requirements_compare_full_signatures(self):
        source='''
            type feature First{fn visit(&self,other:&First)->Int;}
            type feature Second{fn visit(&self,other:&Second)->Int;}
            struct Left{value:Int}struct Right{value:Int}
            impl Left{fn visit(self:&Left,other:&Second)->Int{return self.value;}}
            impl Right{fn visit(self:&Right,other:&Second)->Int{return self.value;}}
            fn apply(a:&First,b:&First)->Int{return a.visit(b);}
            fn main(){let a=Left{value:7};let b=Right{value:9};print(apply(&a,&b));}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        for declaration in ('fn visit(&mut self,other:&Second)->Int;',
                            'fn visit(&self,other:&Second);',
                            'fn visit(&self,other:&Second,n:Int)->Int;'):
            with self.subTest(declaration=declaration),self.assertRaisesRegex(Error,'exigence de feature'):
                verify_program(source.replace('fn visit(&self,other:&Second)->Int;',declaration))

    def test_signature_modes_against_independent_cartesian_model(self):
        # The oracle compares source-level capabilities, not normalized compiler
        # signatures. Receiver and argument capabilities vary independently.
        receivers=[('&self','&C','&Feature','&c','t.op(ARG)'),
                   ('&mut self','&mut C','&mut Feature','&mut c','t.op(ARG)'),
                   ('-> self','-> C','-> Feature','-> c','(-> t).op(ARG)')]
        values=[('Int','7','n'),('&Int','&n','n'),('-> Int','-> n','-> n')]
        for wanted_receiver,requested in enumerate(receivers):
            for wanted_value,(value_signature,call_value,forward) in enumerate(values):
                for actual_receiver,actual in enumerate(receivers):
                    for actual_value,(actual_signature,_,_) in enumerate(values):
                        method_call=requested[4].replace('ARG',forward)
                        source=f'''
                            type feature Feature{{fn op({requested[0]},n:{value_signature});}}
                            struct C{{value:Int}}
                            impl C{{fn op(mut self:{actual[1]},n:{actual_signature}){{print(n);}}}}
                            fn apply(mut t:{requested[2]},n:{value_signature}){{{method_call};}}
                            fn main(){{let mut c=C{{value:0}};
                                {'let mut p=pool<Int>(1);let n=p.new(7);' if wanted_value else ''}
                                apply({requested[3]},{call_value});}}
                        '''
                        admitted=(wanted_receiver==actual_receiver and wanted_value==actual_value)
                        with self.subTest(required=(wanted_receiver,wanted_value),actual=(actual_receiver,actual_value)):
                            if admitted:
                                self.assertEqual(self.native(source).stdout,'7\n')
                            else:
                                with self.assertRaisesRegex(Error,'exigence de feature'):
                                    verify_program(source)


if __name__=='__main__':
    unittest.main()
