"""Counterexamples and bounded independent cleanup-order checks from the audit."""
from functools import partial, update_wrapper
from pathlib import Path
import random
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class AuditRegressionTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def test_enum_fields_capture_scalars_before_later_effects(self):
        result = self.execute('enum E { A { x: Int, y: Int } } '
            'fn read(a: &Int) -> Int { return *a; } '
            'let mut memory = pool<E>(1); let mut temps = allocator(); let mut n = 10; '
            'let mut e = new(memory) E.A { x: n, y: read(& { n.set(20); '
            'let mut a = new(temps) Int(1); <- a }) }; print(e); print(n);')
        self.assertEqual(result.stdout, 'E.A(10, 1)\n20\n')
        self.assertEqual(result.stderr.count('destroy e=E.A'), 1)
        self.assertEqual(result.stderr.count('destroy a=1'), 1)

    def test_enum_initializers_follow_written_order_not_declaration_order(self):
        result = self.execute('enum E { A { x: Int, y: Int } } '
            'fn read(a: &Int) -> Int { return *a; } '
            'let mut memory = pool<E>(1); let mut temps = allocator(); let mut n = 10; '
            'let mut e = new(memory) E.A { y: n, x: read(& { n.set(20); '
            'let mut a = new(temps) Int(1); <- a }) }; print(e);')
        self.assertEqual(result.stdout, 'E.A(1, 10)\n')

    def test_enum_earlier_field_is_still_captured_before_conditional_effect(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute('enum E { A { x: Int, y: Int } } '
                    'fn read(a: &Int) -> Int { return *a; } '
                    'let mut memory = pool<E>(1); let mut temps = pool<Int>(1); let mut n = 10; '
                    'let mut flag = ' + str(flag) + '; let mut e = new(memory) E.A { x: n, '
                    'y: read(&if flag == 1 { n.set(20); let mut a = new(temps) Int(1); <- a } '
                    'else { n.set(30); let mut a = new(temps) Int(2); <- a }) }; print(e); print(n);')
                self.assertEqual(result.stdout, 'E.A(10, 1)\n20\n' if flag else 'E.A(10, 2)\n30\n')

    def test_abrupt_later_initializer_does_not_publish_partial_enum(self):
        result = self.execute('enum E { A { x: Int, y: Int } } '
            'fn work(mem: &mut Pool<E>, temps: &mut Allocator) { let mut n = 10; '
            'let mut e = new(mem) E.A { x: n, y: { let mut a = new(temps) Int(7); return; } }; print(e); } '
            'let mut memory = pool<E>(1); let mut temps = allocator(); work(&mut memory, &mut temps); memory.reset();')
        self.assertEqual(result.stdout, '')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')], ['destroy a=7'])

    def test_conditional_identity_preserves_import_and_export_reception(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(2)'):
            for flag in (0, 1):
                with self.subTest(factory=factory, flag=flag):
                    result = self.execute('fn forward(mut a: -> Int, n: Int) -> <- Int { '
                        'if n == 0 { return <- a; } return <- a; } '
                        'let mut memory = ' + factory + '; let mut a = new(memory) Int(42); '
                        'address(a); { -> a; a = forward(-> a, ' + str(flag) + '); <- a; } '
                        'address(a); print(a); drop(-> a); memory.reset();')
                    lines = result.stdout.splitlines()
                    self.assertEqual(lines[0], lines[1])
                    self.assertEqual(lines[2:], ['42'])
                    self.assertEqual(result.stderr.count('destroy a=42'), 1)

    def test_pending_export_survives_conditional_identity_call(self):
        result = self.execute('fn forward(mut a: -> Int, n: Int) -> <- Int { '
            'if n == 0 { return <- a; } return <- a; } '
            'let mut a = new(memory) Int(42); { -> a; <- a; a = forward(-> a, 0); print(a); } print(a);')
        self.assertEqual(result.stdout, '42\n42\n')
        self.assertEqual(result.stderr.count('destroy a=42'), 1)

    def test_nested_conditional_identity_preserves_repeated_imports(self):
        result = self.execute('fn forward(mut a: -> Int, n: Int) -> <- Int { '
            'if n == 0 { return <- a; } return <- a; } '
            'fn outer(mut a: -> Int, n: Int) -> <- Int { if n == 0 { -> a; '
            'let mut b = forward(-> a, n); return <- b; } '
            'let mut b = forward(-> a, n); return <- b; } '
            'let mut a = new(memory) Int(42); { -> a; { -> a; '
            'a = outer(-> a, 1); <- a; } <- a; } print(a);')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.count('destroy a=42'), 1)

    def test_same_identity_keeps_guards_correct_across_loop_backedges(self):
        result = self.execute('fn forward(mut a: -> Int, n: Int) -> <- Int { '
            'if n == 0 { return <- a; } return <- a; } '
            'let mut memory = pool<Int>(1); let mut controls = allocator(); let mut state = new(controls) Int(0); '
            'let mut a = new(memory) Int(42); while *state < 2 { -> a; '
            'a = forward(-> a, *state); <- a; if *state == 0 { state.set(1); continue; } state.set(2); } '
            'print(a); drop(-> a); memory.reset();')
        self.assertEqual(result.stdout, '42\n')
        self.assertEqual(result.stderr.count('destroy a=42'), 1)

    def test_same_identity_keeps_guards_correct_across_joins(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute('fn forward(mut a: -> Int, n: Int) -> <- Int { '
                    'if n == 0 { return <- a; } return <- a; } '
                    'let mut a = new(memory) Int(42); let mut flag = ' + str(flag) + '; '
                    'if flag == 0 { -> a; a = forward(-> a, flag); <- a; } '
                    'else { -> a; a = forward(-> a, flag); <- a; } print(a); memory.reset();')
                self.assertEqual(result.stdout, '42\n')
                self.assertEqual(result.stderr.count('destroy a=42'), 1)

    def test_enum_identity_preserves_arm_and_source(self):
        result = self.execute('enum E { A { n: Int }, B } '
            'fn forward(mut a: -> E, n: Int) -> <- E { if n == 0 { return <- a; } return <- a; } '
            'let mut memory = pool<E>(1); let mut a = new(memory) E.A { n: 42 }; '
            '{ -> a; a = forward(-> a, 1); <- a; } print(a); drop(-> a); memory.reset();')
        self.assertEqual(result.stdout, 'E.A(42)\n')
        self.assertEqual(result.stderr.count('destroy a=E.A'), 1)

    def test_conditional_identity_does_not_reactivate_consumed_name(self):
        prelude = ('fn forward(mut a: -> Int, n: Int) -> <- Int { '
                   'if n == 0 { return <- a; } return <- a; } ')
        for tail in ('print(a); print(b);', 'drop(-> b); print(b);',
                     'let mut v = &b; drop(-> b); print(v);'):
            with self.subTest(tail=tail):
                self.rejected(prelude + 'let mut a = new(memory) Int(42); let mut b = forward(-> a, 0); ' + tail,
                              'plus utilisable|emprunt')

    def test_distinct_return_candidates_keep_selected_cleanup(self):
        for flag in (0, 1):
            with self.subTest(flag=flag):
                result = self.execute('fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int { '
                    'if n == 0 { return <- a; } return <- b; } '
                    'let mut memory = pool<Int>(2); let mut a = new(memory) Int(1); let mut b = new(memory) Int(2); '
                    'let mut chosen = choose(-> a, -> b, ' + str(flag) + '); print(chosen); memory.reset();')
                self.assertEqual(result.stdout, str(flag + 1) + '\n')
                self.assertEqual(result.stderr.count('destroy a=1'), 1)
                self.assertEqual(result.stderr.count('destroy b=2'), 1)

    def test_future_loans_remain_protected_through_nested_control_flow(self):
        contexts = ('{ OP } print(view);',
                    'if true { OP } print(view);',
                    'while false { OP } print(view);',
                    'loop { OP break; } print(view);',
                    'loop { print(view); OP continue; }')
        for loan in ('&', '&mut'):
            for operation in ('data.set(20);', '-> data; drop(-> data);', 'memory.reset();'):
                for context in contexts:
                    with self.subTest(loan=loan, operation=operation, context=context):
                        self.rejected('let mut data = new(memory) Int(42); let mut view = ' + loan + ' data; '
                                      + context.replace('OP', operation),
                                      'emprunt|reset interdit|entrée')

    def test_independent_cleanup_model_for_moves_returns_and_conditional_drops(self):
        # Model only allocation identity, value and reception order. It neither
        # imports verifier state nor uses generated C to compute expectations.
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(64)'):
            for seed in (17, 83):
                with self.subTest(factory=factory, seed=seed):
                    rng = random.Random(seed)
                    program = ['fn forward(mut a: -> Int, n: Int) -> <- Int { '
                               'if n == 0 { return <- a; } return <- a; }',
                               'let mut memory = ' + factory + ';']
                    order, available, values, labels = [], {}, {}, {}
                    expected_prints, expected_drops = [], []
                    serial = 0
                    for step in range(32):
                        operation = rng.choice(('new', 'move', 'return', 'scope', 'drop', 'conditional'))
                        if not available or operation == 'new':
                            serial += 1
                            name, key = 'v' + str(serial), serial
                            value = rng.randrange(100)
                            program.append(f'let mut {name} = new(memory) Int({value});')
                            order.append(key)
                            available[name], values[key], labels[key] = key, value, name
                            continue
                        name = rng.choice(list(available))
                        key = available[name]
                        if operation in ('move', 'return'):
                            serial += 1
                            new_name = 'v' + str(serial)
                            rhs = '<- ' + name if operation == 'move' else f'forward(-> {name}, {step % 2})'
                            program.append(f'let mut {new_name} = {rhs};')
                            del available[name]
                            available[new_name] = key
                            if operation == 'return':
                                order.remove(key)
                                order.append(key)
                            program.append(f'print({new_name});')
                            expected_prints.append(str(values[key]))
                        elif operation == 'scope':
                            program.append(f'{{ -> {name}; <- {name}; }} print({name});')
                            order.remove(key)
                            order.append(key)
                            expected_prints.append(str(values[key]))
                        else:
                            del available[name]
                            destroy = operation == 'drop' or rng.randrange(2) == 1
                            if operation == 'drop':
                                program.append(f'drop(-> {name});')
                            else:
                                program.append(f'if {"true" if destroy else "false"} {{ -> {name}; drop(-> {name}); }}')
                            if destroy:
                                order.remove(key)
                                expected_drops.append(f'destroy {labels[key]}={values[key]}')
                    program.append('memory.reset();')
                    expected_drops.extend(f'destroy {labels[k]}={values[k]}' for k in reversed(order))
                    result = self.execute(' '.join(program))
                    self.assertEqual(result.stdout.splitlines(), expected_prints)
                    self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                                     expected_drops)


if __name__ == '__main__':
    unittest.main()
