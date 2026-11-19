"""RT8 grammar and synchronous boundary, not completed semantic support."""
import unittest

from crust import Error, Parser, compile_source, verify_program


class NativeThreadParserTests(unittest.TestCase):
    def test_branch_annotation_grammar_does_not_inspect_function_body(self):
        for annotation, method in (
            ('#(branch)', 'none'),
            ('#(branch: join=result.join())', 'join'),
            ('#(branch: join=result.await)', 'await'),
        ):
            with self.subTest(annotation=annotation):
                node, = Parser(annotation + ' async fn launch() -> runtime::AsyncHandle<i64> {}').parse_syntax()
                self.assertEqual(node.branch_wait, method)
        for annotation in (
            '#(branch: join=result.join)',
            '#(branch: join=result.await())',
            '#(branch: join=result.42())',
            '#(branch: join=other.join())',
        ):
            with self.subTest(annotation=annotation), self.assertRaises(Error):
                Parser(annotation + ' fn launch() {}').parse_syntax()

    def test_raw_syntax_accepts_closure_before_return_type_check(self):
        valid = 'fn main() { let read = || -> i64 { true }; }'
        node, = Parser(valid).parse_syntax()
        self.assertEqual(node.op, 'fn')
        with self.assertRaises(Error):
            Parser('fn main() { let read = |x| { x }; }').parse_syntax()

    def test_core_match_requires_comma_between_arms(self):
        for match in (
            'match x { Some(value) => {}, None => {} }',
            'match &x { Choice.First => {}, Choice.Second => {} }',
        ):
            with self.subTest(match=match):
                Parser(f'fn main() {{ {match} }}').parse_syntax()
                Parser(f'fn main() {{ {match[:-1]}, }} }}').parse_syntax()
                with self.assertRaisesRegex(Error, "attendu ','"):
                    Parser(f'fn main() {{ {match.replace(",", "")} }}').parse_syntax()
        with self.assertRaisesRegex(Error, 'au moins un bras'):
            Parser('fn main() { match &x {} }').parse_syntax()

    def test_core_match_syntax_preserves_patterns_before_exhaustiveness(self):
        function, = Parser("""
            fn main() {
                match result { Ok(Some(value)) => {}, _ => {}, Err(()) => {} }
                match &item { Choice.First { field:_ } => {} }
            }
        """).parse_syntax()
        result, nominal = function.args[3]
        self.assertEqual(result.op, 'syntax_match')
        self.assertEqual([pattern for pattern, _ in result.args[1]], [
            ('pattern_call', 'Ok', ('pattern_call', 'Some', ('pattern_name', 'value'))),
            ('wildcard',),
            ('pattern_call', 'Err', ('unit',)),
        ])
        self.assertEqual(nominal.op, 'if_yield')
        self.assertEqual(nominal.args[0][2][0][0], ('variant', 'Choice', 'First', [('field', '_')]))
        for pattern in ('Ok(Some())', 'Choice.First { field: }', 'runtime::'):
            with self.subTest(pattern=pattern), self.assertRaises(Error):
                Parser(f'fn main() {{ match value {{ {pattern} => {{}} }} }}').parse_syntax()

    def test_raw_patterns_follow_value_path_syntax(self):
        Parser('''fn main() { match value {
            Err(runtime::Error::LaunchFailed) => {},
            NumericConversionError::OutOfRange => {},
            network::Ready(_) => {},
        } }''').parse_syntax()
        for pattern in ('bool', 'self', 'runtime::Ready', 'runtime::Error',
                        'runtime::Error::bool', 'runtime::Error::LaunchFailed.More', 'network::bool'):
            with self.subTest(pattern=pattern), self.assertRaises(Error):
                Parser(f'fn main() {{ match value {{ {pattern} => {{}} }} }}').parse_syntax()

    @staticmethod
    def expression(body, asynchronous=False):
        nodes = Parser(('async ' if asynchronous else '') +
                       'fn work() { let h = runtime::thread({' + body + '}); }').parse()
        return nodes[0].args[3][0].args[1]

    def test_capture_header_preserves_order_and_return_boundary(self):
        expression = self.expression('-> (vue, nombre); return *vue + nombre;')
        self.assertEqual(expression[0], 'native_thread')
        self.assertEqual(expression[1], ('vue', 'nombre'))
        self.assertEqual([node.op for node in expression[2]], ['return'])
        self.assertEqual(expression[2][0].args[0],
                         ('arithmetic', '+', ('deref', 'vue'), ('name', 'nombre')))
        self.assertEqual(expression[3], 1)

    def test_empty_tail_early_and_owned_return_forms(self):
        cases = (
            ('', []),
            ('return;', ['return']),
            ('7', ['if_yield']),
            ('-> (a,); <- a', ['<-']),
            ('-> (a); return <- a;', ['return']),
            ('-> (a); if a == 0 { return 7; } 9', ['if', 'if_yield']),
            ('-> (h); let result = h.join(); result', ['var', 'if_yield']),
        )
        for body, operations in cases:
            with self.subTest(body=body):
                self.assertEqual([node.op for node in self.expression(body)[2]], operations)

    def test_suspensions_are_refused_inside_native_block_in_async_function(self):
        for body in ('yield;', 'let value = task.await;',
                     'if true { yield; }', '{ let value = task.await; }',
                     'return task.await;', 'take(task.await);'):
            with self.subTest(body=body), self.assertRaisesRegex(Error, 'exige un corps async fn'):
                self.expression(body, asynchronous=True)

    def test_raw_thread_block_precedes_capture_and_suspension_checks(self):
        function, = Parser('fn main(){ let h=runtime::thread({move x; move x; yield; task.await}); }').parse_syntax()
        _, captures, body, *_ = function.args[3][0].args[1]
        self.assertEqual(captures, ('x', 'x'))
        self.assertEqual([node.op for node in body], ['yield', 'if_yield'])
        for body in ('move _;', 'move bool;', 'yield', 'task.await()'):
            with self.subTest(body=body), self.assertRaises(Error):
                Parser(f'fn main(){{let h=runtime::thread({{{body}}});}}').parse_syntax()

    def test_async_context_is_restored_after_native_block(self):
        source = '''async fn work() {
            let result = runtime::thread({ return 7; }).await;
            yield;
            let next = other().await;
        }'''
        body = Parser(source).parse()[0].args[3]
        self.assertEqual(body[0].args[1][0], 'await')
        self.assertEqual(body[0].args[1][1][0], 'native_thread')
        self.assertEqual(body[1].op, 'yield')
        self.assertEqual(body[2].args[1][0], 'await')
        with self.assertRaisesRegex(Error, '.await exige un corps async fn'):
            Parser(source.replace('async fn', 'fn')).parse()

    def test_nested_native_blocks_keep_distinct_captures(self):
        outer = self.expression('''-> (a);
            let child = runtime::thread({ -> (b); return b; });
            return child.join();''')
        inner = outer[2][0].args[1]
        self.assertEqual(outer[1], ('a',))
        self.assertEqual(inner[1], ('b',))
        self.assertEqual(inner[2][0].op, 'return')
        self.assertEqual(outer[2][1].op, 'return')

    def test_malformed_capture_headers_and_nonblocks_are_refused(self):
        for body in ('-> (a, a); return 7;', '-> (a) return 7;',
                     '-> (&a); return 7;', '-> (a + b); return 7;',
                     '-> (a); -> (b); return 7;'):
            with self.subTest(body=body), self.assertRaises(Error):
                self.expression(body)
        for argument in ('7', 'function()', '{ return 7; }, 8'):
            with self.subTest(argument=argument), self.assertRaises(Error):
                Parser('fn work() { let h = runtime::thread(' + argument + '); }').parse()

    def test_native_blocks_require_wait_for_borrowed_dependencies(self):
        for source in (
            'fn main(){let value:i32=7; let view=&value; let h=runtime::thread({move view; *view});}',
            'fn main(){let value:i32=7; let view=&value; let h=runtime::thread({move view; *view}); drop(h);}',
        ):
            for check in (verify_program, compile_source):
                with self.subTest(source=source, check=check.__name__):
                    with self.assertRaisesRegex(Error, 'attente requise|join requis'):
                        check(source)

    def test_autonomous_native_blocks_allow_abandoning_the_handle(self):
        for source in (
            'fn main() { let h = runtime::thread({ return 7; }); drop(h); }',
            'async fn work() { let h = runtime::thread({ return 7; }); return; } fn main() {}',
        ):
            for check in (verify_program, compile_source):
                with self.subTest(source=source, check=check.__name__):
                    check(source)


if __name__ == '__main__':
    unittest.main()
