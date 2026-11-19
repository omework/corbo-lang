"""By-value transfers and lexical block captures through both public entries."""

import unittest

from crust import Error, Parser
import test_select_source as harness


class ValueMoveTests(unittest.TestCase):
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    run_source = harness.SelectSourceTests.run_source
    refused = harness.SelectSourceTests.refused

    def test_raw_block_tail_is_preserved_before_return_checks(self):
        function, = Parser('fn main(){ { 1+2 } 3 }').parse_syntax()
        block, tail = function.args[3]
        self.assertEqual(block.args[1][0].op, 'if_yield')
        self.assertEqual(tail.op, 'if_yield')
        self.assertEqual(tail.args[0], ('numeric_integer', 3))
        annotated, = Parser('fn read()->i64 {42}').parse_syntax()
        self.assertEqual(annotated.args[3][0].op, 'if_yield')
        for expression, operation in (('{42}', 'scope'), ('if true {42} else {0}', 'if_expr'),
                                      ('loop {break 42;}', 'loop_expr'), ('unsafe {42}', 'scope')):
            with self.subTest(expression=expression):
                function, = Parser(f'fn read()->i64 {{ {expression} }}').parse_syntax()
                tail, = function.args[3]
                self.assertEqual(tail.op, 'if_yield')
                self.assertEqual(tail.args[0][0], operation)
        for source in ('fn main(){1+2 3}', 'fn main(){return}', 'fn read()->i64{return}', 'fn main(){let}'):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(source).parse_syntax()

    def test_raw_expression_statements_keep_separator(self):
        function, = Parser('fn main(){ 1+2; (3*4); value; let n=0; n=2; 5 }').parse_syntax()
        first, second, name, declaration, assignment, tail = function.args[3]
        self.assertEqual(first.args[0][0:2], ('numeric_binary', '+'))
        self.assertEqual(second.args[0][0:2], ('numeric_binary', '*'))
        self.assertEqual(name.args[0], ('name', 'value'))
        self.assertEqual([declaration.op, assignment.op, tail.op], ['var', 'assign', 'if_yield'])
        for body in ('1+2 let n=0;', 'bool();', 'runtime();', 'bool', '_'):
            with self.subTest(body=body), self.assertRaises(Error):
                Parser(f'fn main(){{ {body} }}').parse_syntax()
        with self.assertRaisesRegex(Error, "reçu ';'"):
            Parser('fn main(){ 1 + ; }').parse_syntax()

    def test_raw_assignment_preserves_dereference_and_projection_order(self):
        function, = Parser("""
            fn main() {
                table.rows[1].amount += 2;
                **refs[0].amount = 3;
            }
        """).parse_syntax()
        first, second = function.args[3]
        self.assertEqual(first.args[:4], (
            0, 'table', (('field', 'rows'), ('index', ('numeric_integer', 1)), ('field', 'amount')), '+='))
        self.assertEqual(second.args[:4], (
            2, 'refs', (('index', ('numeric_integer', 0)), ('field', 'amount')), '='))
        for place in ('table.get(1).amount', 'table.rows[1..3].amount', '***refs[0]',
                      'table.rows[].amount', 'bool', 'runtime.slot', 'table._', 'table.return'):
            with self.subTest(place=place), self.assertRaises(Error):
                Parser(f'fn main(){{{place}=2;}}').parse_syntax()

    def test_raw_assignment_accepts_self_and_bare_compound_target(self):
        impl, = Parser('impl Counter { fn update(&mut self) { self.total += 1; total %= 2; } }').parse_syntax()
        first, second = impl.args[1][0].args[3]
        self.assertEqual(first.args[:4], (0, 'self', (('field', 'total'),), '+='))
        self.assertEqual(second.args[:4], (0, 'total', (), '%='))

    def test_raw_postfix_chains_preserve_receiver_order(self):
        function, = Parser("""
            fn main() {
                let amount=table.rows[1].amount;
                let view=factory().read().rows[2].amount;
            }
        """).parse_syntax()
        first, second = (node.args[1] for node in function.args[3])
        self.assertEqual(first, ('project_field',
            ('array_index', ('field', 'table', 'rows'), ('numeric_integer', 1)), 'amount'))
        self.assertEqual(second, ('project_field', ('array_index', ('project_field',
            ('method_call', ('call', 'factory', []), 'read', []), 'rows'),
            ('numeric_integer', 2)), 'amount'))
        for expression in ('table.rows[1].', 'factory().read(,)', 'factory().rows[]'):
            with self.subTest(expression=expression), self.assertRaises(Error):
                Parser(f'fn main(){{let value={expression};}}').parse_syntax()

    def test_raw_borrow_preserves_slice_operand_before_mutability_checks(self):
        function, = Parser('fn main(){let view=&mut text[1..3];}').parse_syntax()
        self.assertEqual(function.args[3][0].args[1], (
            'mut_expr', ('utf8_slice_place', ('name', 'text'),
                         ('numeric_integer', 1), ('numeric_integer', 3))))
        with self.assertRaisesRegex(Error, 'découpe &str est immuable'):
            Parser('fn main(){let view=&mut text[1..3];}').parse()
        with self.assertRaises(Error):
            Parser('fn main(){let view=&mut text[];}').parse_syntax()

    def test_raw_method_calls_preserve_arguments_before_arity_checks(self):
        function, = Parser('''fn main(){
            let a = "text".byte_len(1,);
            let b = factory().join(2);
            let c = text.try_slice(..2);
            let d = factory().try_slice(1, 2);
            let e = factory().try_slice();
        }''').parse_syntax()
        first, second, third, fourth, fifth = (node.args[1] for node in function.args[3])
        self.assertEqual(first, ('method_call', ('text', b'text'), 'byte_len', [('numeric_integer', 1)]))
        self.assertEqual(second, ('method_call', ('call', 'factory', []), 'join', [('numeric_integer', 2)]))
        self.assertEqual(third[0], 'utf8_try_slice')
        self.assertEqual(fourth, ('method_call', ('call', 'factory', []), 'try_slice',
                                  [('numeric_integer', 1), ('numeric_integer', 2)]))
        self.assertEqual(fifth, ('method_call', ('call', 'factory', []), 'try_slice', []))
        with self.assertRaises(Error):
            Parser('fn main(){ let a = factory().join(,); }').parse_syntax()

    def test_raw_copy_call_preserves_written_arguments(self):
        function, = Parser('fn main(){ let result = copy([1, 2]); }').parse_syntax()
        self.assertEqual(function.args[3][0].args[1], (
            'call', 'copy', [('array_literal', ('numeric_integer', 1), ('numeric_integer', 2))]))

    def test_raw_conditional_keeps_optional_else_before_value_checks(self):
        source = 'fn main(){let value=if true {42};}'
        function, = Parser(source).parse_syntax()
        conditional = function.args[3][0].args[1]
        self.assertEqual(conditional[0], 'if_expr')
        self.assertEqual(conditional[3], [])
        with self.assertRaisesRegex(Error, 'exige une branche else'):
            Parser(source).parse()
        nested = 'fn main(){let value=if true {42} else if false {7};}'
        function, = Parser(nested).parse_syntax()
        self.assertEqual(function.args[3][0].args[1][3][0], 'if_expr')
        for source in ('fn main(){let x=if true {} else;}',
                       'fn main(){let x=if true 42;}'):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(source).parse_syntax()

    def test_raw_dereference_accepts_unary_and_postfix_operands(self):
        function, = Parser("""
            fn main() {
                let read=*(lookup())[1] + 2;
                let nested=**(lookup());
            }
        """).parse_syntax()
        read, nested = (node.args[1] for node in function.args[3])
        self.assertEqual(read, ('numeric_binary', '+', ('syntax_deref',
            ('array_index', ('call', 'lookup', []), ('numeric_integer', 1))), ('numeric_integer', 2)))
        self.assertEqual(nested, ('syntax_deref', ('syntax_deref', ('call', 'lookup', []))))
        for expression in ('*', '*;', '*(lookup(,))'):
            with self.subTest(expression=expression), self.assertRaises(Error):
                Parser(f'fn main(){{let value={expression};}}').parse_syntax()

    def test_raw_core_uses_current_syntax_without_legacy_profile_inference(self):
        function, = Parser('fn read(text:&str){let value=1+2; value}').parse_syntax()
        self.assertEqual(function.args[3][0].args[1][0], 'numeric_binary')
        Parser('fn main(){let read=|| -> i64 {42}; {move read;} }').parse_syntax()
        for source in ('fn main(){let x=<-value;}', 'fn main(){send(->value);}',
                       'fn main(){let h=runtime::thread({ -> (a); });}'):
            with self.subTest(source=source), self.assertRaisesRegex(Error, 'déplacements par valeur'):
                Parser(source).parse_syntax()

    def test_raw_unit_and_immediate_closure_call(self):
        function, = Parser("""
            fn main() {
                let empty=();
                let value=(|x:i64| { x })(42,);
                consume(());
            }
        """).parse_syntax()
        empty, value, call = function.args[3]
        self.assertEqual(empty.args[1], ('unit',))
        application = value.args[1]
        self.assertEqual(application[0], 'closure_apply')
        self.assertEqual(application[2], [('numeric_integer', 42)])
        self.assertEqual(call.args[0], ('call', 'consume', [('unit',)]))
        Parser('fn main(){ let value=(move || {42})(); let read=((|| {42})); }').parse_syntax()
        for expression in ('(,)', '()(1)', '(|x:i64| {x})(,)', '((|| {42}))()', '(read)()'):
            with self.subTest(expression=expression), self.assertRaises(Error):
                Parser(f'fn main(){{let value={expression};}}').parse_syntax()

    def test_core_move_header_and_block_are_distinct_syntax(self):
        function, = Parser('fn main(){ { move a; move b; print(a); } move { 7 } }').parse_syntax()
        block, capture = function.args[3]
        self.assertEqual([node.args[0] for node in block.args[1][:2]], ['a', 'b'])
        self.assertTrue(all(node.move_import for node in block.args[1][:2]))
        self.assertEqual(capture.op, 'if_yield')
        self.assertEqual(capture.args[0][0], 'capture_scope')
        Parser('fn main(){ { move first; let read=move || {first}; } }').parse_syntax()
        for source in ('fn main(){ { print(1); move a; } }',
                       'fn main(){ runtime::thread({ print(1); move a; }); }'):
            with self.subTest(source=source), self.assertRaisesRegex(Error, 'entrée du bloc'):
                Parser(source).parse_syntax()

    def test_raw_core_rejects_legacy_pair_binding_and_type_feature_declaration(self):
        for body in ('let (mut left, mut right) = split();',
                     'type feature Read { fn read(&self); }'):
            with self.subTest(body=body), self.assertRaises(Error):
                Parser(f'fn main(){{ {body} }}').parse_syntax()

    def test_binding_call_return_and_drop_keep_the_allocation(self):
        source = '''
        fn relayer(n: A<Int>) -> A<Int> { n }
        fn main() {
            let mut p = pool<Int>(1);
            let a = p.new(7);
            address(a);
            let b = a;
            let c = relayer(b);
            address(c);
            drop(c);
            let d = p.new(9);
            address(d);
            print(*d);
        }'''
        run = self.run_source(source)
        first, received, reused, value = run.stdout.splitlines()
        self.assertEqual((received, reused, value), (first, first, '9'))
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy a=7', 'destroy d=9'])
        self.refused(source.replace('address(c);', 'print(*a);address(c);'), 'plus utilisable')
        self.refused(source.replace('address(c);', 'print(*b);address(c);'), 'plus utilisable')

    def test_argument_move_is_immediate_and_checks_loans(self):
        source = '''
        fn consommer(a: A<Int>, b: Int) {
            print(b);
            drop(a);
        }
        fn main() {
            let mut p = pool<Int>(1);
            let a = p.new(7);
            consommer(a, 9);
        }'''
        self.assertEqual(self.run_source(source).stdout, '9\n')
        self.refused(source.replace('consommer(a, 9)', 'consommer(a, *a)'), 'plus utilisable')
        self.refused(source.replace('consommer(a, 9);', 'let vue = &a; consommer(a, 9); print(*vue);'),
                     'emprunt')

    def test_replacement_and_fixed_array_arguments(self):
        source = '''
        fn somme(a: [Int; 2]) -> Int { a[0] + a[1] }
        fn main() {
            let mut p = pool<Int>(2);
            let mut a = p.new(7);
            print(*a);
            let b = p.new(9);
            a = b;
            print(*a);
            let tableau = [2, 3];
            print(somme(copy(tableau)));
            print(somme(tableau));
        }'''
        self.assertEqual(self.run_source(source).stdout, '7\n9\n5\n5\n')
        self.refused(source.replace('let tableau =', 'print(*b);let tableau ='),
                     'plus utilisable')
        self.refused(source.replace('print(somme(tableau));', 'print(somme(tableau));print(tableau[0]);'),
                     'plus utilisable')

    def test_explicit_move_import_and_result_receiver(self):
        source = '''
        fn main() {
            let mut p = pool<Int>(1);
            let a = p.new(7);
            let recu = {
                move a;
                print(*a);
                a
            };
            print(*recu);
        }'''
        self.assertEqual(self.run_source(source).stdout, '7\n7\n')
        computed = 'fn relayer(n:A<Int>)->A<Int>{n}' + source.replace(
            'print(*a);\n                a', 'print(*a);\n                relayer(a)')
        self.assertEqual(self.run_source(computed).stdout, '7\n7\n')
        fresh = 'fn main(){let mut p=pool<Int>(1);let recu={p.new(7)};print(*recu);}'
        self.assertEqual(self.run_source(fresh).stdout, '7\n')
        self.refused(source.replace('print(*recu);', 'print(*a);print(*recu);'), 'plus utilisable')
        self.refused(source.replace('move a;', 'print(1);move a;'), 'entrée')

    def test_block_captures_by_value_and_respects_shadowing(self):
        source = '''
        fn main() {
            let mut p = pool<Int>(1);
            let a = p.new(7);
            let mut bonus = 2;
            let recu = move {
                bonus = 4;
                print(*a + bonus);
                a
            };
            move { let recu = 9; print(recu); }
            print(*recu);
            print(bonus);
        }'''
        self.assertEqual(self.run_source(source).stdout, '11\n9\n7\n2\n')
        self.refused(source.replace('print(bonus);', 'print(*a); print(bonus);'), 'plus utilisable')

    def test_capturing_a_prepared_shared_reference_keeps_its_target(self):
        source = '''
        fn main() {
            let mut p = pool<Int>(1);
            let a = p.new(7);
            let vue = &a;
            move { print(*vue); }
            print(*a);
            print(*vue);
        }'''
        self.assertEqual(self.run_source(source).stdout, '7\n7\n7\n')
        self.refused(source.replace('move { print(*vue); }', 'move { let dedans=&a; print(*dedans); }'),
                     'emprunt|plus utilisable')

    def test_condition_and_loop_results_keep_their_sources(self):
        source = '''
        fn choisir(flag: bool, p: &mut Pool<Int>, q: &mut Pool<Int>) -> A<Int> {
            if flag { let a = p.new(7); a } else { let b = q.new(9); b }
        }
        fn main() {
            let mut p = pool<Int>(1);
            let mut q = pool<Int>(1);
            let a = choisir(true, &mut p, &mut q);
            let b = loop { move a; break a; };
            print(*b);
            drop(b);
            let c = choisir(false, &mut p, &mut q);
            print(*c);
        }'''
        self.assertEqual(self.run_source(source).stdout, '7\n9\n')
        self.refused('fn main(){let a={let mut p=pool<Int>(1);let a=p.new(7);a};print(*a);}',
                     'survit|durable|source')

    def test_async_uses_by_value_arguments_and_owned_returns(self):
        source = '''
        async fn relayer(n: A<Int>) -> A<Int> {
            yield;
            let recu = move {
                print(*n);
                n
            };
            recu
        }
        fn main() {
            let mut p = pool<Int>(1);
            let a = p.new(7);
            let execution = runtime::spawn(relayer(a));
            match execution.join() {
                Ok(recu) => { print(*recu); drop(recu); },
                Err(_) => {},
            }
            let suivant = p.new(9);
            print(*suivant);
        }'''
        self.assertEqual(self.run_source(source).stdout, '7\n7\n9\n')
        self.refused(source.replace('match execution.join()', 'print(*a); match execution.join()'),
                     'plus utilisable')

    def test_async_copies_scalar_at_entry(self):
        source = '''
        async fn calculer() -> Int {
            let mut n = 7;
            move {
                n = 9;
                yield;
                print(n);
            }
            n
        }
        fn main() {
            let h = runtime::spawn(calculer());
            match h.join() { Ok(n) => { print(n); }, Err(_) => {} }
        }'''
        self.assertEqual(self.run_source(source).stdout, '9\n7\n')


if __name__ == '__main__':
    unittest.main()
