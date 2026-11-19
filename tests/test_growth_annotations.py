"""Check the scope configuration seen by the compiler."""

import unittest

from crust import Compiler, Error, Parser, verify_program


class ScopeRecorder(Compiler):
    def __init__(self):
        super().__init__()
        self.limits = {}

    def statements(self, scope, nodes, returns, *args, **kwargs):
        for node in nodes:
            if node.op == 'var' and node.args[0].startswith('probe_'):
                self.limits[node.args[0]] = scope.region_limit
        return super().statements(scope, nodes, returns, *args, **kwargs)


class GrowthAnnotationTests(unittest.TestCase):
    def test_core_directive_syntax_requires_colon_and_binary_units(self):
        for unit, size in (('K', 1024), ('M', 1024 ** 2), ('G', 1024 ** 3)):
            source = f'fn main() {{ #(directive: stack_region_max_size=1{unit}) {{}} }}'
            function, = Parser(source).parse_syntax()
            block, = function.args[3]
            self.assertEqual(block.args[0][3], size)
        pool = '#(directive: async_pool_sizes={network::read:2}) fn main() {}'
        directive, _ = Parser(pool).parse_syntax()
        self.assertEqual(directive.args[0][:2], ('network::read', 2))
        for source in (
            pool.replace('directive:', 'directive,'),
            'fn main() { #(directive, stack_region_max_size=1K) {} }',
            'fn main() { #(directive: stack_region_max_size=1Ki) {} }',
            'fn main() { #(directive: stack_region_max_size=0M) {} }',
            'fn main() { #(directive: stack_region_max_size=0x10M) {} }',
        ):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(source).parse_syntax()

    def test_raw_region_directive_can_annotate_function_and_control_blocks(self):
        function, = Parser("""
            fn main() #(directive: stack_region_max_size=1M) {
                if true #(directive: stack_region_max_size=4K) {}
                match value { Some(v) => #(directive: stack_region_max_size=8K) {} }
            }
        """).parse_syntax()
        outer, = function.args[3]
        condition, match = outer.args[1]
        self.assertEqual(outer.region_limit, 1024 ** 2)
        self.assertEqual(condition.args[1][0].region_limit, 4 * 1024)
        self.assertEqual(match.args[0][2][0][1][0].region_limit, 8 * 1024)
        for source in (
            'fn main() #(directive: stack_region_max_size=1K) print(1);',
            'fn main(){let f=|| #(directive: stack_region_max_size=1K) {};}',
        ):
            with self.subTest(source=source), self.assertRaises(Error):
                Parser(source).parse_syntax()

    def test_raw_region_directive_occurs_once_per_block(self):
        region = '#(directive: stack_region_max_size=1K)'
        Parser(f'fn main(){{ {region} {{ {region} {{}} }} }}').parse_syntax()
        for body in (f'{region} {region} {{}}', f'move {region} {region} {{}}',
                     f'let value={region} {region} {{}};'):
            with self.subTest(body=body), self.assertRaises(Error):
                Parser(f'fn main(){{ {body} }}').parse_syntax()

    def test_raw_capacity_directive_keeps_integer_before_capacity_check(self):
        large = '9' * 30
        directive, = Parser(f'#(directive: async_pool_sizes={{network::work:{large}, idle:0}})').parse_syntax()
        self.assertEqual([(name, capacity) for name, capacity, _ in directive.args],
                         [('network::work', large), ('idle', 0)])
        for capacity in ('-1', '1.5'):
            with self.subTest(capacity=capacity), self.assertRaisesRegex(Error, 'entier non signé'):
                Parser(f'#(directive: async_pool_sizes={{work:{capacity}}})').parse_syntax()
        with self.assertRaisesRegex(Error, 'strictement positive'):
            Parser('#(directive: async_pool_sizes={work:0})').parse()

    def test_raw_region_size_preserves_positive_literal_beyond_representation(self):
        for size in ('8589934592G', '9' * 5000 + 'K'):
            with self.subTest(size=size[:24]):
                source = f'fn main() #(directive: stack_region_max_size={size}) {{}}'
                function, = Parser(source).parse_syntax()
                self.assertEqual(function.args[3][0].region_limit, size)
                with self.assertRaisesRegex(Error, 'hors limites'):
                    Parser(f'fn main(){{#(directive: stack_region_max_size={size}) {{}}}}').parse()
        with self.assertRaisesRegex(Error, 'hors limites'):
            Parser('fn main() #(directive: stack_region_max_size=0K) {}').parse_syntax()

    def test_region_limits_follow_lexical_scopes(self):
        source = '''
            fn plain() { let probe_callee = 0; }
            let probe_root = 0;
            #(directive: stack_region_max_size=4K) {
                let probe_outer = 0;
                {
                    let probe_child = 0;
                    plain();
                }
                #(directive: stack_region_max_size=1G) {
                    let probe_override = 0;
                    if true { let probe_branch = 0; }
                }
                let probe_restored = 0;
                let mut p = pool<Int>(1);
                let n = #(directive: stack_region_max_size=8M) {
                    let probe_expression = 0;
                    let local = p.new(2);
                    <- local
                };
                print(n);
            }
            let probe_after = 0;
        '''
        compiler = ScopeRecorder()
        compiler.compile(Parser(source).parse())
        self.assertEqual(compiler.limits, {
            'probe_root': None,
            'probe_outer': 4 << 10,
            'probe_child': 4 << 10,
            'probe_callee': None,
            'probe_override': 1 << 30,
            'probe_branch': 1 << 30,
            'probe_restored': 4 << 10,
            'probe_expression': 8 << 20,
            'probe_after': None,
        })

    def test_invalid_region_annotations_are_rejected(self):
        for source in (
            '#(directive, stack_region_max_size=0M) {}',
            '#(directive, stack_region_max_size=-1G) {}',
            '#(directive: stack_region_max_size=1T) {}',
            '#(directive, stack_region_max_size=8589934592G) {}',
            '#(other=1M) {}',
            '#(directive, stack_region_max_size=1M) print(1);',
        ):
            with self.subTest(source=source), self.assertRaises(Error):
                verify_program(source)

    def test_directive_category_and_separator_are_required(self):
        for annotation in (
            '#(stack_region_max_size=1M)',
            '#(type, stack_region_max_size=1M)',
            '#(types, stack_region_max_size=1M)',
            '#(other, stack_region_max_size=1M)',
            '#(directive stack_region_max_size=1M)',
            '#(directive, other=1M)',
            '#(directive, stack_region_max_size=1M, stack_region_max_size=2M)',
        ):
            for context in ('ANNOTATION {}', 'let n=ANNOTATION { 1 };print(n);'):
                with self.subTest(annotation=annotation, context=context), self.assertRaises(Error):
                    verify_program(context.replace('ANNOTATION', annotation))

    def test_directive_whitespace_and_numeric_boundaries(self):
        # Independent decimal arithmetic specifies the prototype representation;
        # it does not reuse region_annotation or its constants.
        for unit, maximum, multiplier in (('K', 9007199254740991, 1024),
                                           ('M', 8796093022207, 1048576),
                                           ('G', 8589934591, 1073741824)):
            for number in (1, maximum):
                for space in ('', ' ', '\n'):
                    source = (f'#(directive,{space}stack_region_max_size{space}='
                              f'{space}00{number}{unit}) {{let probe_boundary=0;}}')
                    compiler = ScopeRecorder()
                    compiler.compile(Parser(source).parse())
                    self.assertEqual(compiler.limits['probe_boundary'], number * multiplier)
            for number in (0, maximum + 1, 10**100):
                source = f'#(directive, stack_region_max_size={number}{unit}) {{}}'
                with self.subTest(unit=unit, number=number), self.assertRaisesRegex(Error, 'hors limites'):
                    verify_program(source)
