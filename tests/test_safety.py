"""Adversarial regressions and an independent runtime allocation oracle."""
from functools import partial, update_wrapper
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source, Error, PROTOTYPE_RUNTIME, RUNTIME

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust


class SafetyTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    rejected = test_crust.PrototypeTests.rejected
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def test_explicit_receiver_invalidates_original_access(self):
        self.rejected('let mut a = new(memory) Int(1); let mut b = { -> a; <- a }; '
                      'let mut c = <- b; print(a); print(c);', 'plus utilisable')

    def test_explicit_receiver_has_single_usable_access(self):
        result = self.execute('let mut a = new(memory) Int(1); let mut b = { -> a; <- a }; '
                              'let mut c = <- b; print(c); memory.drop(-> c); memory.reset();')
        self.assertEqual(result.stdout, '1\n')
        self.assertEqual(result.stderr.count('destroy '), 1)

    def test_standalone_return_restores_original_access(self):
        result = self.execute('let mut a = new(memory) Int(1); '
                              '{ -> a; { -> a; let mut moved = <- a; moved.set(2); <- moved; } <- a; } '
                              'print(a); memory.drop(-> a); memory.reset();')
        self.assertEqual(result.stdout, '2\n')
        self.assertEqual(result.stderr.count('destroy '), 1)

    def test_return_through_nested_imports_does_not_duplicate_access(self):
        result = self.execute('fn forward(mut a: -> Int) -> <- Int { { -> a; return <- a; } } '
                              'let mut a = new(memory) Int(3); let mut b = forward(-> a); '
                              'print(b); memory.drop(-> b); memory.reset();')
        self.assertEqual(result.stdout, '3\n')
        self.assertEqual(result.stderr.count('destroy '), 1)

    def test_nested_expression_initializers_have_checked_diagnostics(self):
        sources = [
            'let mut memory = allocator(); let mut a = new(memory) Int({ '
            'let mut b = new(memory) Int(1); <- b });',
            'enum E { A { n: Int } } let mut memory = pool<E>(1); '
            'let mut a = new(memory) E.A { n: { let mut b = new(memory) E.A { n: 1 }; <- b } };',
            'fn f(mem: &mut Allocator) -> <- Int { return { '
            'let mut a = new(mem) Int(1); <- a }; } '
            'let mut memory = allocator(); let mut a = f(&mut memory); print(a);',
        ]
        for source in sources:
            with self.subTest(source=source), self.assertRaises(Error):
                compile_source(source)

    def test_malformed_sources_do_not_escape_as_python_exceptions(self):
        valid = ('enum E { A { n: Int }, B } fn main() { let mut memory = pool<E>(2); '
                 'let mut a = new(memory) E.A { n: 1 }; match &a { '
                 'E.A { n: x } => { print(x); } E.B => {} } }')
        candidates = [valid[:i] for i in range(len(valid))]
        candidates += [
            'let mut a = ' + '9' * 10000 + ';',
            'let mut a = ²;',
            '{' * 2000 + '}' * 2000,
            'let mut a = new(',
        ]
        for source in candidates:
            with self.subTest(source=source[:80]):
                try:
                    compile_source(source)
                except Error:
                    pass

    def test_allocator_lifecycle_across_sources(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(4)'):
            with self.subTest(factory=factory):
                result = self.execute('let mut memory = ' + factory + '; '
                                      'fn make(mem: &mut Allocator, n: Int) -> <- Int { '
                                      'let mut a = new(mem) Int(n); return <- a; } '
                                      'let mut a = make(&mut memory, 5); '
                                      '{ -> a; let mut r = &a; print(r); <- a; } '
                                      'let mut b = <- a; memory.drop(-> b); memory.reset();')
                self.assertEqual(result.stdout, '5\n')
                self.assertEqual(result.stderr.count('destroy '), 1)

    def test_direct_drop_uses_existing_provenance(self):
        for factory in ('allocator()', 'stack(65536)', 'pool<Int>(2)'):
            with self.subTest(factory=factory):
                result = self.execute('let mut memory = ' + factory + '; '
                                      'fn consume(mut a: -> Int) { print(a); drop(-> a); } '
                                      'let mut a = new(memory) Int(7); consume(-> a); '
                                      'memory.reset();')
                self.assertEqual(result.stdout, '7\n')
                self.assertEqual(result.stderr.count('destroy '), 1)
                self.assertTrue(result.stderr.endswith('reset\n'))

    def test_direct_drop_enum_uses_active_arm(self):
        result = self.execute('enum E { A, B { n: Int } } let mut memory = pool<E>(1); '
                              'fn consume(mut e: -> E) { drop(-> e); } '
                              'let mut a = new(memory) E.A; let mut b = new(memory) E.B { n: 1 }; '
                              'consume(-> a); drop(-> b); memory.reset();')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy a=E.A', 'destroy b=E.B'])

    def test_direct_drop_keeps_move_and_borrow_checks(self):
        cases = [
            ('let mut a = new(memory) Int(1); let mut r = &a; drop(-> a); print(r);', 'emprunt'),
            ('let mut a = new(memory) Int(1); drop(-> a); print(a);', 'plus utilisable'),
            ('let mut a = new(memory) Int(1); drop(-> a); drop(-> a);', 'plus utilisable'),
            ('let mut a = new(memory) Int(1); drop(&a);', "attendu '->'"),
            ('let mut a = new(memory) Int(1); { drop(-> a); }', 'transférer avec ->'),
            ('fn consume(a: &Int) { drop(-> a); } let mut a = new(memory) Int(1); consume(&a);',
             'allocation explicite'),
            ('fn drop(mut a: -> Int) {}', 'nom de fonction déjà utilisé'),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                self.rejected(source, message)

    def test_direct_and_explicit_drop_have_same_cleanup(self):
        template = 'let mut a = new(memory) Int(8); {operation} memory.reset();'
        direct = self.execute(template.format(operation='drop(-> a);'))
        explicit = self.execute(template.format(operation='memory.drop(-> a);'))
        self.assertEqual(direct.stderr, explicit.stderr)

    def test_runtime_pool_oracle(self):
        """Drive the runtime directly, independently from code generation."""
        harness = r'''
#include <assert.h>
static void validate(Source *s) {
    assert(s->used <= s->capacity);
    assert(s->used % s->stride == 0);
    size_t count = s->used / s->stride, live = 0, free_count = 0;
    Cell *prev = NULL;
    for (size_t i = 0; i < count; i++) {
        Cell *cell = (Cell *)(s->base + i * s->stride);
        assert(cell->source == s && cell->prev == prev);
        assert(cell->next == (i + 1 < count ? (Cell *)(s->base + (i + 1) * s->stride) : NULL));
        live += cell->alive != 0;
        prev = cell;
    }
    assert(s->tail == prev && live == s->live);
    if (s->tail) assert(s->tail->alive);
    Cell *free_prev = NULL;
    for (Cell *cell = s->free_head; cell; cell = cell->free_next) {
        assert(++free_count <= count);
        assert((unsigned char *)cell >= s->base && (unsigned char *)cell < s->base + s->used);
        assert((size_t)((unsigned char *)cell - s->base) % s->stride == 0);
        assert(cell->source == s && !cell->alive && cell->free_prev == free_prev);
        free_prev = cell;
    }
    assert(free_count == count - live);
}
int main(void) {
    Source arms[] = {source_pool_layout(8, sizeof(int)), source_pool_layout(8, 5 * sizeof(int))};
    arms[0].arm_name = "Small"; arms[0].field_count = 1;
    arms[1].arm_name = "Large"; arms[1].field_count = 5;
    Source root = source_enum_pool(arms, 2, "E");
    Cell *handles[2][8] = {{0}};
    int expected[2][8] = {{0}};
    unsigned random = 12345;
    for (int step = 1; step <= 3000; step++) {
        random = random * 1664525u + 1013904223u;
        unsigned arm = (random >> 12) % 2, index = (random >> 17) % 8;
        if (handles[arm][index]) {
            cell_drop(handles[arm][index]);
            handles[arm][index] = NULL;
        } else {
            Cell *cell = enum_new(&root, arm, "oracle");
            for (size_t f = 0; f < arms[arm].field_count; f++) cell->fields[f] = step + (int)f;
            handles[arm][index] = cell;
            expected[arm][index] = step;
        }
        for (size_t a = 0; a < 2; a++) {
            validate(&arms[a]);
            for (size_t i = 0; i < 8; i++) if (handles[a][i]) {
                assert(handles[a][i]->source == &arms[a]);
                for (size_t f = 0; f < arms[a].field_count; f++)
                    assert(handles[a][i]->fields[f] == expected[a][i] + (int)f);
                for (size_t j = i + 1; j < 8; j++) assert(handles[a][i] != handles[a][j]);
            }
        }
    }
    for (size_t a = 0; a < 2; a++) for (size_t i = 0; i < 8; i++)
        if (handles[a][i]) cell_drop(handles[a][i]);
    source_reset(&root);
    for (size_t a = 0; a < 2; a++) { validate(&arms[a]); assert(arms[a].used == 0); }
    source_close(&root);
    puts("oracle ok");
    return 0;
}
'''
        cc = shutil.which('clang') or shutil.which('cc')
        if not cc:
            self.skipTest('C compiler unavailable')
        for legacy, runtime in ((False, PROTOTYPE_RUNTIME), (True, RUNTIME)):
            with self.subTest(legacy_reset=legacy):
                with tempfile.TemporaryDirectory() as directory:
                    source, binary = Path(directory) / 'oracle.c', Path(directory) / 'oracle'
                    source.write_text(runtime + (harness if legacy else harness.replace('    source_reset(&root);\n', '')))
                    command = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                               str(source), '-o', str(binary)]
                    sanitizers = os.environ.get('CRUST_SANITIZE')
                    if sanitizers:
                        if sanitizers == '1':
                            sanitizers = 'address,undefined'
                        if sanitizers not in ('address', 'undefined', 'address,undefined'):
                            raise ValueError('invalid sanitizer selection')
                        command[1:1] = [f'-fsanitize={sanitizers}', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
                    build = subprocess.run(command, capture_output=True, text=True, timeout=30)
                    self.assertEqual(build.returncode, 0, build.stderr)
                    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr[-4000:])
                    self.assertEqual(result.stdout, 'oracle ok\n')


if __name__ == '__main__':
    unittest.main()
