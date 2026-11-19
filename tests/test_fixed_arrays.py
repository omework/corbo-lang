"""Executable examples for the value subset of fixed arrays."""
from functools import partial, update_wrapper
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Compiler, Error, Parser, compile_source, verify_program

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)


class FixedArrayTests(unittest.TestCase):
    def execute(self, source, expected, *, diagnostic=None, trace=''):
        cc = shutil.which('clang') or shutil.which('cc')
        if cc is None:
            self.skipTest('C compiler unavailable')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'array.c'
            binary = path.with_suffix('')
            path.write_text(compile_source(source))
            args = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-variable', '-Wno-unused-function']
            sanitize = os.environ.get('CRUST_SANITIZE')
            if sanitize:
                args += [f'-fsanitize={sanitize}', '-fno-sanitize-recover=all']
            optimize = os.environ.get('CRUST_ARRAY_OPT')
            if optimize:
                args.append(optimize)
            build = subprocess.run([*args, str(path), '-o', str(binary)],
                                   capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.stdout.splitlines(), [str(value) for value in expected])
            if diagnostic:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)
                self.assertNotIn('runtime error:', result.stderr)
                self.assertNotIn('Sanitizer', result.stderr)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, trace)

    def test_literals_evaluate_once_in_order_even_at_zero(self):
        self.execute('''
            fn marque(n: Int) -> Int { print(n); return n; }
            fn main() {
                let ordonne = [marque(1), marque(2), marque(3)];
                let repete = [marque(4); 3];
                let vide = [marque(5); 0];
                print(ordonne[1]); print(repete[2]); print(vide.len());
            }
        ''', [1, 2, 3, 4, 5, 2, 4, 0])

    def test_nested_bounds_stop_before_column_or_rhs(self):
        self.execute('''
            fn marque(n: Int) -> Int { print(n); return n; }
            fn ecrire(ligne: Int) {
                let mut grille = [[10, 20], [30, 40]];
                grille[ligne][marque(1)] = marque(99);
                print(grille[1][1]);
            }
            fn main() { ecrire(1); ecrire(2); }
        ''', [1, 99, 99], diagnostic='indice hors limites')

    def test_negative_runtime_index(self):
        self.execute('''
            fn lire(i: Int) { let tableau = [10]; print(tableau[i]); }
            fn main() { lire(-1); }
        ''', [], diagnostic='indice hors limites')

    def test_guard_does_not_validate_a_later_index_value(self):
        self.execute('''
            fn lire(mut i: Int) {
                let tableau = [10, 20];
                if i < tableau.len() {
                    print(tableau[i]);
                    i = 2;
                    print(tableau[i]);
                }
            }
            fn main() { lire(1); }
        ''', [20], diagnostic='indice hors limites')

    def test_value_transfers_across_calls_and_control_flow(self):
        self.execute('''
            fn vide() -> [Int; 0] { return <- []; }
            fn selection(mut entree: [Int; 2], choix: Int) -> [Int; 2] {
                entree[0] = 50;
                let retenu = if choix == 0 { <- copy(entree) } else { <- [7, 8] };
                let ligne = loop {
                    let grille = [copy(retenu), [30, 40]];
                    break <- copy(grille[0]);
                };
                return <- ligne;
            }
            fn main() {
                let source = [10, 20];
                let premier = selection(copy(source), 0);
                let second = selection(copy(source), 1);
                let rien = vide();
                print(source[0]); print(premier[0]); print(second[0]); print(rien.len());
            }
        ''', [10, 50, 7, 0])

    def test_generated_operations_against_list_model(self):
        rng = random.Random(20261104)
        for length in (1, 2, 7):
            model = [0] * length
            lines = [f'let mut tableau = [0; {length}];']
            expected = []
            for _ in range(30):
                first, second = (rng.randrange(length) for _ in range(2))
                value = rng.randrange(-50, 51)
                op = rng.randrange(3)
                if op == 0:
                    lines.append(f'tableau[{first}] = {value};')
                    model[first] = value
                elif op == 1:
                    lines.append(f'tableau.swap({first}, {second});')
                    model[first], model[second] = model[second], model[first]
                else:
                    lines.append(f'print(tableau.replace({first}, {value}));')
                    expected.append(model[first])
                    model[first] = value
                lines.extend(f'print(tableau[{index}]);' for index in range(length))
                expected.extend(model)
            with self.subTest(length=length):
                self.execute('fn main() {\n' + '\n'.join(lines) + '\n}', expected)

    def test_reject_invalid_programs_at_verification(self):
        cases = (
            ('let a = [1]; print(a[1]);', 'hors limites'),
            ('let a = [1]; print(a[-1]);', 'hors limites'),
            ('let a = [1; 0]; print(a[0]);', 'tableau vide'),
            ('let a = []; print(a.len());', 'type de contexte'),
            ('let a = [1]; a[0] = 2;', 'immuable'),
            ('let a = [[1], [2]]; let b = a[1];', 'copie implicite'),
            ('let mut a = [1]; a = [1, 2];', 'conserver le type'),
            ('let mut a = [[1]]; a[0] = [2, 3];', 'conserver le type'),
            ('let mut a = [[1]]; a.replace(0, [2, 3]);', 'conserver le type'),
            ('let a = [[1]]; let b = loop { break <- a[0]; };', 'déplacement d’une case'),
            ('let a = [[1]]; let b = loop { break copy(a[0]); };', 'par <- requis'),
            ('let a = if 1 == 1 { <- [1] } else { <- [1, 2] };', 'même type'),
            ('let a = [1]; let b = <- a; print(a[0]);', 'plus utilisable'),
            ('let a = [[1], [2, 3]]; print(a.len());', 'même type'),
        )
        for body, diagnostic in cases:
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program('fn main() { ' + body + ' }')

    def test_local_borrows_end_after_last_use_and_reborrow(self):
        self.execute('''
            fn main() {
                let mut a = [1, 2];
                let lecture = &a[0];
                a[1] = *lecture;
                let ecriture = a.mut_ref();
                let enfant = &mut ecriture[0];
                print(a.len());
                *enfant = 7;
                ecriture[1] = 9;
                print(a[0]); print(a[1]);
            }
        ''', [2, 7, 9])

    def test_array_loans_across_arguments_and_temporary_calls(self):
        self.execute('''
            fn lire(tableau: &[Int; 2]) -> Int { return tableau[0]; }
            fn changer(tableau: &mut [Int; 2], n: Int) { tableau[0] = n; }
            fn main() {
                let mut a = [1, 2];
                changer(a.mut_ref(), 9);
                print(lire(a.ref()));
                changer(copy(a).mut_ref(), 7);
                print(a[0]);
            }
        ''', [9, 9])

    def test_conflicting_array_loans_are_rejected(self):
        cases = (
            ('let mut a = [1, 2]; let b = &mut a[0]; print(a[1]); *b = 7;', 'emprunt actif'),
            ('let mut a = [1, 2]; let b = &a[0]; a[1] = 9; print(*b);', 'emprunt actif'),
            ('let mut a = [1]; let b = &mut a[0]; let c = &mut *b; *b = 3; *c = 7;', 'emprunt actif'),
            ('let mut a = [1]; let b = &mut a[0]; let c = &*b; print(a[0]); print(*c);', 'emprunt actif'),
            ('let a = [1]; let b = copy(a).mut_ref(); print(b[0]);', 'temporaire'),
            ('let mut a = [1]; let b = &a[0]; let c = <- a; print(*b);', 'emprunt actif'),
        )
        for body, diagnostic in cases:
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program('fn main() { ' + body + ' }')

        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program('''
                fn changer(tableau: &mut [Int; 2], n: Int) { tableau[0] = n; }
                fn main() {
                    let mut a = [1, 2];
                    changer(a.mut_ref(), a[1]);
                }
            ''')

    def test_borrow_liveness_at_loop_back_edge(self):
        self.execute('''
            fn main() {
                let mut a = [1, 2];
                let mut i = 0;
                loop {
                    let vue = &mut a[i];
                    *vue = 7;
                    print(a[i]);
                    if i == 1 { break; }
                    i = 1;
                    continue;
                }
            }
        ''', [7, 7])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program('''
                fn f(continuer: Int) {
                    let mut a = [1, 2];
                    let vue = &mut a[0];
                    loop {
                        *vue = 7;
                        print(a[1]);
                        if continuer == 0 { break; }
                        continue;
                    }
                }
            ''')

    def test_break_borrow_preserves_every_possible_array_root(self):
        program = """
            fn choisir(i: Int) {
                let mut gauche = [1];
                let mut droite = [2];
                let vue = loop {
                    if i == 0 { break &mut gauche[0]; }
                    break &mut droite[0];
                };
                *vue = 5;
                print(gauche[0]); print(droite[0]);
            }
            fn main() { choisir(0); choisir(1); }
        """
        self.execute(program, [5, 2, 1, 5])
        for name in ('gauche', 'droite'):
            with self.subTest(name=name), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(program.replace('*vue = 5;', f'print({name}[0]); *vue = 5;'))

        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn main() {
                    let vue = loop { let a = [1]; break &a[0]; };
                    print(*vue);
                }
            """)

    def test_immutable_index_guards_remove_only_proven_bounds_checks(self):
        program = """
            fn lire(i: Int) {
                let a = [1, 2];
                if i >= 0 { if i < 2 { print(a[i]); } }
            }
            fn main() { lire(1); }
        """
        self.assertNotIn('indice hors limites du tableau', compile_source(program))
        self.assertIn('indice hors limites du tableau',
                      compile_source(program.replace('lire(i: Int)', 'lire(mut i: Int)')))
        self.execute(program, [2])

    def test_element_borrow_returned_through_relay_and_temporary(self):
        program = """
            fn element(a: &mut [Int; 2], i: Int) -> &mut Int { return &mut a[i]; }
            fn relais(a: &mut [Int; 2]) -> &mut Int { return element(a, 0); }
            fn main() {
                let mut a = [10, 20];
                let vue = relais(a.mut_ref());
                *vue = 30;
                print(a[0]);
                let lu = *element(copy(a).mut_ref(), 1);
                print(lu);
            }
        """
        self.execute(program, [30, 20])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*vue = 30;', 'print(a[1]); *vue = 30;'))
        with self.assertRaisesRegex(Error, 'temporaire'):
            verify_program(program.replace('relais(a.mut_ref())', 'relais(copy(a).mut_ref())'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn mauvais() -> &Int { let a = [1]; return &a[0]; }
                fn main() {}
            """)

    def test_pass_element_to_existing_int_reference_parameters(self):
        program = """
            fn changer(v: &mut Int) { v.set(12); }
            fn lire(v: &Int) -> Int { return *v; }
            fn identite(v: &mut Int) -> &mut Int { return v; }
            fn element(a: &mut [Int; 2]) -> &mut Int { return identite(&mut a[1]); }
            fn main() {
                let mut a = [10, 20];
                changer(&mut a[0]);
                print(lire(&a[0]));
                let vue = element(a.mut_ref());
                changer(vue);
                print(a[1]);
            }
        """
        self.execute(program, [12, 12])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('changer(vue);', 'print(a[0]); changer(vue);'))

    def test_stored_references_copy_and_slot_specific_last_use(self):
        program = """
            fn main() {
                let mut a = [1];
                let mut b = [2];
                let vues = [&mut a[0], &mut b[0]];
                let vue = &mut *vues[0];
                *vues[1] = 4;
                *vue = 5;
                print(a[0]);
                *vues[1] = 6;
                print(b[0]);
                let lectures = [&a[0], &b[0]];
                let copie = copy(lectures);
                print(*copie[1]);
            }
        """
        self.execute(program, [5, 6, 6])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*vues[1] = 4;', '*vues[0] = 4;'))
        with self.assertRaisesRegex(Error, 'références mutables'):
            verify_program(program.replace('let vue =', 'let interdit = copy(vues); let vue ='))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*vues[1] = 6;', 'let i = 1; *vues[i] = 6;'))

    def test_replace_stored_reference_transfers_old_loan(self):
        program = """
            fn main() {
                let mut a = [1];
                let mut b = [2];
                let mut vues = [&mut a[0]];
                let ancien = vues.replace(0, &mut b[0]);
                *ancien = 5;
                *vues[0] = 6;
                print(a[0]); print(b[0]);
            }
        """
        self.execute(program, [5, 6])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*ancien = 5;', 'print(a[0]); *ancien = 5;'))

    def test_reference_arrays_transfer_through_loop_and_if(self):
        program = """
            fn choisir(i: Int) {
                let a = [1];
                let b = [2];
                let v = loop {
                    let r = if i == 0 { let t = [&a[0]]; <- t } else { <- [&b[0]] };
                    break <- r;
                };
                print(*v[0]);
            }
            fn main() { choisir(0); choisir(1); }
        """
        self.execute(program, [1, 2])
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(program.replace('let t = [&a[0]];', 'let local = [3]; let t = [&local[0]];'))

    def test_reference_array_result_contract_is_resolved_per_slot(self):
        program = """
            fn f(a: &[Int; 1], b: &[Int; 1]) -> [&Int; 2] {
                return <- [&a[0], &b[0]];
            }
            fn relais(v: [&Int; 2]) -> [&Int; 2] {
                return <- copy(v);
            }
            fn changer(v: -> [&mut Int; 1]) { *v[0] = 9; }
            fn main() {
                let mut a = [1];
                let mut b = [2];
                let v = f(&a, &b);
                let r = relais(copy(v));
                a[0] = 3;
                print(*r[1]);
                let m = [&mut b[0]];
                changer(-> m);
                print(b[0]);
            }
        """
        self.execute(program, [2, 9])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('print(*r[1]);', 'print(*r[0]);'))

    def test_empty_arrays_use_parameter_and_destination_types(self):
        self.execute('''
            fn longueur(tableau: [Int; 0]) -> Int { return tableau.len(); }
            fn main() {
                let mut a = [[1; 0], [2; 0]];
                a[0] = [];
                let avant = a.replace(1, []);
                print(avant.len());
                print(longueur([]));
            }
        ''', [0, 0])

    def test_call_contract_sees_reset_inside_index(self):
        with self.assertRaisesRegex(Error, 'libérée|reset|distinct'):
            verify_program('''
                fn indice(p: &mut Pool<Int>) -> Int { p.reset(); return 0; }
                fn lire(p: &mut Pool<Int>, data: &Int) {
                    let a = [1];
                    print(a[indice(p)]);
                    print(data);
                }
                fn main() {
                    let mut p = pool<Int>(1);
                    let data = new(p) Int(3);
                    lire(&mut p, &data);
                }
            ''')

    def test_pool_reference_in_returned_array_blocks_reset(self):
        program = """
            fn ranger(a: &Int) -> [&Int; 1] { return <- [a]; }
            fn main() {
                let mut p = pool<Int>(1);
                let a = new(p) Int(7);
                let vues = ranger(&a);
                print(*vues[0]);
                p.reset();
                let b = new(p) Int(8);
                print(b);
            }
        """
        self.execute(program, [7, 8], trace='destroy a=7\nreclaim a\nreset\ndestroy b=8\nreclaim b\n')
        with self.assertRaisesRegex(Error, 'reset|emprunt'):
            verify_program(program.replace('print(*vues[0]);\n                p.reset();',
                                           'p.reset(); print(*vues[0]);'))

    def test_swap_stored_references_moves_provenance(self):
        program = """
            fn main() {
                let mut a = [1];
                let mut b = [2];
                let mut vues = [&mut a[0], &mut b[0]];
                vues.swap(0, 1);
                *vues[0] = 8;
                print(b[0]);
                *vues[1] = 9;
                print(a[0]);
            }
        """
        self.execute(program, [8, 9])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('print(b[0]);', 'print(a[0]);'))

    def test_slot_sources_cross_modular_reset_contract(self):
        program = """
            fn lire(p: &mut Pool<Int>, vues: [&Int; 2]) {
                print(*vues[0]);
                p.reset();
                print(*vues[1]);
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let a = new(p) Int(1);
                let b = new(q) Int(2);
                let vues = [&a, &b];
                lire(&mut p, copy(vues));
            }
        """
        self.execute(program, [1, 2],
                     trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        with self.assertRaisesRegex(Error, 'distinct|reset|libérée'):
            verify_program(program.replace('new(q)', 'new(p)'))

    def test_mixed_array_element_and_pool_borrow_result(self):
        program = """
            fn choisir(a: &mut [Int; 1], b: &mut Int, i: Int) -> &mut Int {
                if i == 0 { return &mut a[0]; }
                return b;
            }
            fn jouer(i: Int) {
                let mut p = pool<Int>(1);
                let mut b = new(p) Int(2);
                let mut a = [1];
                let mut v = choisir(&mut a, &mut b, i);
                *v = 7;
                print(a[0]); print(b);
            }
            fn main() { jouer(0); jouer(1); }
        """
        self.execute(program, [7, 2, 1, 7],
                     trace='destroy b=2\nreclaim b\ndestroy b=7\nreclaim b\n')
        for conflict in ('print(a[0]);', 'print(b);', 'p.reset();'):
            with self.assertRaisesRegex(Error, 'emprunt|reset'):
                verify_program(program.replace('*v = 7;', conflict + ' *v = 7;'))

    def test_function_reborrow_of_stored_mutable_reference(self):
        program = """
            fn reemprunter(v: &mut Int) -> &mut Int { return v; }
            fn main() {
                let mut a = [1];
                let mut vues = [&mut a[0]];
                let mut autre = reemprunter(&mut *vues[0]);
                *autre = 8;
                *vues[0] = 9;
                print(a[0]);
            }
        """
        self.execute(program, [9])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*autre = 8;', '*vues[0] = 3; *autre = 8;'))

    def test_dynamic_reference_swap_preserves_distinct_slots(self):
        program = """
            fn jouer(i: Int) {
                let mut a = [1];
                let mut b = [2];
                let mut v = [&mut a[0], &mut b[0]];
                v.swap(0, i);
                let mut vue = &mut *v[0];
                *v[1] = 6;
                *vue = 5;
                print(a[0]); print(b[0]);
            }
            fn main() { jouer(0); jouer(1); }
        """
        self.execute(program, [5, 6, 6, 5])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*v[1] = 6;', '*v[0] = 6;'))

    def test_dynamic_replace_keeps_removed_capability_distinct(self):
        program = """
            fn jouer(i: Int) {
                let mut a = [1]; let mut b = [2]; let mut c = [3];
                let mut v = [&mut a[0], &mut b[0]];
                let mut old = v.replace(i, &mut c[0]);
                *old = 8;
                *v[0] = 9; *v[1] = 10;
                print(a[0]); print(b[0]); print(c[0]);
            }
            fn main() { jouer(0); jouer(1); }
        """
        self.execute(program, [8, 10, 9, 9, 8, 10])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*old = 8;',
                'let mut emprunt = &mut *old; *old = 4; *emprunt = 8;'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*old = 8;',
                'let ancien = v.replace(0, &mut *old); *old = 8; print(*v[0]);'))

    def test_shared_reference_returned_from_copied_reference_array(self):
        program = """
            fn premiere(v: [&Int; 1]) -> &Int { return &*v[0]; }
            fn relais(v: [&Int; 1]) -> &Int { return premiere(copy(v)); }
            fn main() {
                let mut p = pool<Int>(1);
                let a = new(p) Int(4);
                let v = [&a];
                let r = relais(copy(v));
                print(*r);
                p.reset();
            }
        """
        self.execute(program, [4], trace='destroy a=4\nreclaim a\nreset\n')
        with self.assertRaisesRegex(Error, 'emprunt|reset|libérée'):
            verify_program(program.replace('print(*r);\n                p.reset();',
                                           'p.reset(); print(*r);'))

    def test_reference_swaps_and_replacements_against_list_model(self):
        rng = random.Random(20261105)
        declarations = [f'let mut x{i} = [{i * 10}];' for i in range(7)]
        operations = []
        for i in range(4):
            operations.append(('swap', rng.randrange(3)))
            operations.append(('replace', 3 + i))
        body = declarations + ['let mut v = [&mut x0[0], &mut x1[0], &mut x2[0]];']
        for number, (operation, value) in enumerate(operations):
            if operation == 'swap':
                body.append(f'v.swap(i, {value});')
            else:
                body.append(f'let mut old{number} = v.replace(i, &mut x{value}[0]);')
                body.append(f'*old{number} = {100 + number};')
        body += [f'*v[{slot}] = {200 + slot};' for slot in range(3)]
        body += [f'print(x{slot}[0]);' for slot in range(7)]
        expected = []
        for index in range(3):
            values = [i * 10 for i in range(7)]
            references = list(range(3))
            for number, (operation, value) in enumerate(operations):
                if operation == 'swap':
                    references[index], references[value] = references[value], references[index]
                else:
                    removed = references[index]
                    references[index] = value
                    values[removed] = 100 + number
            for slot, referent in enumerate(references):
                values[referent] = 200 + slot
            expected.extend(values)
        self.execute('fn jouer(i: Int) {' + '\n'.join(body) +
                     '} fn main() { jouer(0); jouer(1); jouer(2); }', expected)

    def test_reference_array_calls_use_only_opaque_contracts(self):
        declarations = """
            fn lire(p: &mut Pool<Int>, v: [&Int; 2]) {
                print(*v[0]); p.reset(); print(*v[1]);
            }
            fn premiere(v: [&Int; 2]) -> &Int { return &*v[0]; }
        """
        interface = verify_program(declarations)

        def check(script):
            caller = Compiler(allow_legacy_reset=True)
            caller.contract_calls = True
            caller.function_contracts = interface.function_contracts
            nodes = Parser(script).parse()
            caller.index(nodes)
            caller.block('root', nodes)
            self.assertEqual(caller.functions, {})
            self.assertEqual(caller.function_results, {})
            return caller

        setup = ('let mut p = pool<Int>(2); let mut q = pool<Int>(1); '
                 'let a = new(p) Int(1); let b = new(q) Int(2); let v = [&a, &b]; ')
        check(setup + 'lire(&mut p, copy(v));')
        with self.assertRaisesRegex(Error, 'reset|distinct|libérée'):
            check(setup.replace('new(q)', 'new(p)') + 'lire(&mut p, copy(v));')
        check(setup + 'let r = premiere(copy(v)); print(*r); p.reset();')
        with self.assertRaisesRegex(Error, 'reset|emprunt'):
            check(setup + 'let r = premiere(copy(v)); p.reset(); print(*r);')

    def test_replacement_can_suspend_a_reference_in_another_slot(self):
        program = """
            fn main() {
                let mut a = [1]; let mut b = [2];
                let mut v = [&mut a[0], &mut b[0]];
                let mut r = &mut *v[0];
                let old = v.replace(1, &mut *r);
                *v[1] = 4;
                *v[0] = 3;
                print(a[0]); print(b[0]);
            }
        """
        self.execute(program, [3, 2])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*v[1] = 4;\n                *v[0] = 3;',
                                           '*v[0] = 3; *v[1] = 4;'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('v.replace(1,', 'v.replace(0,'))

    def test_conditional_replacement_preserves_slot_reborrow_relationship(self):
        program = """
            fn jouer(i: Int) {
                let mut a = [1]; let mut b = [2];
                let mut v = [&mut a[0], &mut b[0]];
                let mut r = &mut *v[0];
                if i == 0 { let old = v.replace(1, &mut *r); }
                *v[1] = 4;
                *v[0] = 3;
                print(a[0]); print(b[0]);
            }
            fn main() { jouer(0); jouer(1); }
        """
        self.execute(program, [3, 2, 3, 4])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*v[1] = 4;\n                *v[0] = 3;',
                                           '*v[0] = 3; *v[1] = 4;'))

    def test_reference_array_receiver_replacement(self):
        program = """
            fn main() {
                let mut a = [1]; let mut b = [2];
                let mut v = [&mut a[0]];
                let nouveau = [&mut b[0]];
                v = <- nouveau;
                *v[0] = 4;
                print(a[0]); print(b[0]);
            }
        """
        self.execute(program, [1, 4])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('v = <- nouveau;',
                'let mut r = &mut *v[0]; v = <- nouveau; *r = 3;'))
        with self.assertRaisesRegex(Error, 'let mut|immuable'):
            verify_program(program.replace('let mut v =', 'let v ='))
        with self.assertRaisesRegex(Error, 'déplac|transfér'):
            verify_program(program.replace('*v[0] = 4;', '*nouveau[0] = 4; *v[0] = 4;'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(program.replace('let nouveau = [&mut b[0]];\n                v = <- nouveau;',
                '{ let mut local = [3]; v = <- [&mut local[0]]; }'))

    def test_shared_reference_repetition_and_typed_empty_arrays(self):
        program = """
            fn repeter(a: &Int) -> [&Int; 2] { return <- [a; 2]; }
            fn vide(a: &Int) -> [&Int; 0] { return <- [a; 0]; }
            fn creer() -> [&mut Int; 0] { return <- []; }
            fn longueur(v: -> [&mut Int; 0]) -> Int { return v.len(); }
            fn main() {
                let mut a = [4];
                let v = repeter(&a[0]); print(*v[1]);
                let z = vide(&a[0]); a[0] = 8;
                let c = copy(z); print(c.len()); print(a[0]);
                let m = creer(); print(longueur(-> m));
            }
        """
        self.execute(program, [4, 0, 8, 0])
        with self.assertRaisesRegex(Error, 'références mutables'):
            verify_program(program.replace('print(longueur(-> m));',
                                           'let interdit = copy(m); print(interdit.len());'))
        with self.assertRaisesRegex(Error, 'copiable'):
            verify_program('fn main() { let mut a = [1]; let v = [&mut a[0]; 2]; print(v.len()); }')

    def test_enum_field_borrow_in_array_keeps_holder_reserved(self):
        program = """
            enum W { Bound { data: &mut Int } }
            fn emprunter(w: &mut W) -> &mut Int {
                let mut r = match &mut w { W.Bound { data: vue } => { vue } };
                return r;
            }
            fn ranger(w: &mut W) -> [&mut Int; 1] { return <- [emprunter(w)]; }
            fn choisir(a: &mut [Int; 1], w: &mut W, i: Int) -> &mut Int {
                if i == 0 { return &mut a[0]; }
                return emprunter(w);
            }
            fn jouer(i: Int) {
                let mut p = pool<Int>(1); let mut q = pool<W>(1);
                let mut n = new(p) Int(1);
                let mut w = new(q) W.Bound { data: &mut n };
                let mut a = [2];
                let v = ranger(&mut w); *v[0] = 3;
                let mut r = choisir(&mut a, &mut w, i);
                *r = 8;
                print(a[0]); print(w);
            }
            fn main() { jouer(0); jouer(1); }
        """
        self.execute(program, [8, 'W.Bound(3)', 2, 'W.Bound(8)'],
            trace='destroy w=W.Bound\nreclaim w\ndestroy n=3\nreclaim n\n'
                  'destroy w=W.Bound\nreclaim w\ndestroy n=8\nreclaim n\n')
        for operation in ('print(w);', 'q.reset();', 'p.reset();', 'drop(-> w);'):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(Error, 'emprunt|reset'):
                    verify_program(program.replace('*v[0] = 3;', operation + '*v[0] = 3;'))

    def test_shared_reference_projection_is_a_copy_with_its_target(self):
        program = """
            fn lire(v: &Int) -> Int { return *v; }
            fn premiere(v: [&Int; 1]) -> &Int { return v[0]; }
            fn main() {
                let mut a = [4];
                let vues = [&a[0]];
                let r = premiere(copy(vues)); print(*r);
                print(lire(vues[0]));
                let dehors = loop { let local = [&a[0]]; break local[0]; };
                print(*dehors);
                a[0] = 8; print(a[0]);
            }
        """
        self.execute(program, [4, 4, 4, 8])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('print(*dehors);', 'a[0] = 5; print(*dehors);'))
        with self.assertRaisesRegex(Error, 'référence mutable'):
            verify_program('fn main() { let mut a = [1]; let v = [&mut a[0]]; let r = v[0]; print(*r); }')

    def test_reference_array_replacement_across_continue_and_break(self):
        program = """
            fn main() {
                let mut a = [1]; let mut b = [2];
                let mut v = [&mut a[0]];
                let mut tours = 0;
                loop {
                    *v[0] = 3;
                    if tours == 1 { break; }
                    v = <- [&mut b[0]];
                    tours = 1;
                    continue;
                }
                print(a[0]); print(b[0]);
            }
        """
        self.execute(program, [3, 3])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('tours = 1;', 'b[0] = 9; tours = 1;'))
        conditional = program.replace('v = <- [&mut b[0]];',
                                      'if tours == 0 { v = <- [&mut b[0]]; }')
        self.execute(conditional, [3, 3])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conditional.replace('tours = 1;', 'b[0] = 9; tours = 1;'))

    def test_borrowed_reference_container_read_and_mutable_result(self):
        program = """
            fn lire(v: &[&Int; 1]) -> Int { return *v[0]; }
            fn premiere(v: &mut [&mut Int; 1]) -> &mut Int { return &mut *v[0]; }
            fn main() {
                let mut a = [4];
                let lectures = [&a[0]]; print(lire(&lectures));
                let mut v = [&mut a[0]];
                let mut r = premiere(&mut v);
                *r = 8;
                *v[0] = 9;
                print(a[0]);
            }
        """
        self.execute(program, [4, 9])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*r = 8;', '*v[0] = 3; *r = 8;'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('let mut r = premiere(&mut v);',
                'let mut enfant = &mut *v[0]; let mut r = premiere(&mut v); *enfant = 3;'))

    def test_borrowed_container_updates_cross_function_contracts(self):
        program = """
            fn echanger(v: &mut [&mut Int; 2]) { v.swap(0, 1); }
            fn relais(v: &mut [&mut Int; 2]) { echanger(&mut *v); }
            fn main() {
                let mut a = [1]; let mut b = [2];
                let mut v = [&mut a[0], &mut b[0]];
                relais(v.mut_ref());
                *v[0] = 8; print(b[0]);
                *v[1] = 9; print(a[0]);
            }
        """
        self.execute(program, [8, 9])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('print(b[0]);', 'print(a[0]);'))

    def test_borrowed_container_replacement_before_reset(self):
        program = """
            fn changer(v: &mut [&Int; 1], d: &Int) -> &Int { return v.replace(0, d); }
            fn relayer(v: &mut [&Int; 1], p: &mut Pool<Int>, d: &Int) {
                let old = changer(v, d);
                p.reset();
                print(*v[0]);
            }
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let a = new(p) Int(1); let b = new(q) Int(2);
                let mut v = [&a];
                relayer(&mut v, &mut p, &b);
                print(*v[0]);
            }
        """
        self.execute(program, [2, 2],
                     trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        with self.assertRaisesRegex(Error, 'distinct|reset|libérée'):
            verify_program(program.replace('new(q)', 'new(p)'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn changer(v: &mut [&Int; 1], d: &Int) { let old = v.replace(0, d); }
                fn main() {
                    let a = [1]; let mut v = [&a[0]];
                    { let local = [2]; changer(&mut v, &local[0]); }
                    print(*v[0]);
                }
            """)

    def test_slot_parent_reservation_survives_borrowed_container_update_contract(self):
        program = """
            fn lier(v: &mut [&mut Int; 2]) {
                let mut r = &mut *v[0];
                let old = v.replace(1, &mut *r);
            }
            fn relais(v: &mut [&mut Int; 2]) { lier(v); }
            fn main() {
                let mut a = [1]; let mut b = [2];
                let mut v = [&mut a[0], &mut b[0]];
                relais(&mut v);
                *v[1] = 4; *v[0] = 3;
                print(a[0]); print(b[0]);
            }
        """
        self.execute(program, [3, 2])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*v[1] = 4; *v[0] = 3;',
                                           '*v[0] = 3; *v[1] = 4;'))

    def test_pool_reference_return_through_local_array_retains_payload_representation(self):
        program = """
            fn f(d: &mut Int) -> &mut Int { let v = [d]; return &mut *v[0]; }
            fn g(d: &mut Int) -> &mut Int { return f(d); }
            fn main() {
                let mut p = pool<Int>(1);
                let mut d = new(p) Int(1);
                let mut r = g(&mut d);
                *r = 8;
                print(d);
            }
        """
        self.execute(program, [8], trace='destroy d=8\nreclaim d\n')
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program(program.replace('*r = 8;', 'print(d); *r = 8;'))

    def test_borrowed_container_update_is_usable_with_only_opaque_contracts(self):
        declarations = """
            fn changer(v: &mut [&Int; 1], d: &Int) { let old = v.replace(0, d); }
            fn relayer(v: &mut [&Int; 1], p: &mut Pool<Int>, d: &Int) {
                changer(v, d); p.reset(); print(*v[0]);
            }
        """
        interface = verify_program(declarations)
        script = ('let mut p = pool<Int>(1); let mut q = pool<Int>(1); '
                  'let a = new(p) Int(1); let b = new(q) Int(2); '
                  'let mut v = [&a]; relayer(&mut v, &mut p, &b); print(*v[0]);')
        caller = Compiler(allow_legacy_reset=True)
        caller.contract_calls = True
        caller.function_contracts = interface.function_contracts
        nodes = Parser(script).parse()
        caller.index(nodes)
        caller.block('root', nodes)
        self.assertEqual(caller.functions, {})
        self.assertEqual(caller.function_results, {})
        self.assertEqual(caller.contract_call_log, ['relayer'])
        self.assertTrue(interface.function_contracts['relayer'].result.parameter_fields)

    def test_whole_borrowed_reference_array_write_updates_contract(self):
        program = """
            fn changer(v: &mut [&Int; 1], d: &Int) -> &Int {
                let old = v[0];
                *v = <- [d];
                return old;
            }
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let a = new(p) Int(1); let b = new(q) Int(2);
                let mut v = [&a];
                let old = changer(&mut v, &b);
                print(*old);
                p.reset();
                print(*v[0]);
            }
        """
        self.execute(program, [1, 2],
                     trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        with self.assertRaisesRegex(Error, 'reset|emprunt'):
            verify_program(program.replace('print(*old);\n                p.reset();',
                                           'p.reset(); print(*old);'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                fn changer(v: &mut [&Int; 1], d: &Int) { *v = <- [d]; }
                fn main() {
                    let a = [1]; let mut v = [&a[0]];
                    { let local = [2]; changer(&mut v, &local[0]); }
                    print(*v[0]);
                }
            """)

    def test_container_postcondition_follows_local_alias_and_shadowing(self):
        for body in (
            'let mut alias = &mut *v; let old = alias.replace(0, d);',
            'let mut alias = &mut *v; { let local = [3]; let v = [&local[0]]; '
            'let old = alias.replace(0, d); print(*v[0]); }',
        ):
            with self.subTest(body=body):
                declaration = 'fn changer(v: &mut [&Int; 1], d: &Int) {' + body + '}'
                setup = ('fn main() { let mut p = pool<Int>(1); let mut q = pool<Int>(1); '
                         'let a = new(p) Int(1); let b = new(q) Int(2); '
                         'let mut v = [&a]; changer(&mut v, &b); ')
                expected = [3, 2] if 'let local' in body else [2]
                self.execute(declaration + setup + 'p.reset(); print(*v[0]); }', expected,
                             trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
                with self.assertRaisesRegex(Error, 'reset|emprunt'):
                    verify_program(declaration + setup + 'q.reset(); print(*v[0]); }')

    def test_temporary_copy_of_reference_container_is_independent(self):
        program = """
            fn lire(v: &[&Int; 1]) -> Int { return *v[0]; }
            fn changer(v: &mut [&Int; 1], d: &Int) { let old = v.replace(0, d); }
            fn main() {
                let a = [1]; let b = [2]; let v = [&a[0]];
                print(lire(copy(v).ref()));
                changer(copy(v).mut_ref(), &b[0]);
                print(*v[0]);
            }
        """
        self.execute(program, [1, 1])
        with self.assertRaisesRegex(Error, 'temporaire'):
            verify_program(program.replace('print(lire(copy(v).ref()));',
                                           'let vue = copy(v).ref(); print(*vue[0]);'))

    def test_alias_postcondition_prevents_reset_of_the_new_target(self):
        with self.assertRaisesRegex(Error, 'reset|emprunt'):
            verify_program("""
                fn changer(v: &mut [&Int; 1], d: &Int) {
                    let mut alias = &mut *v;
                    let old = alias.replace(0, d);
                }
                fn main() {
                    let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                    let a = new(p) Int(1); let b = new(q) Int(2);
                    let mut v = [&a];
                    changer(&mut v, &b);
                    q.reset();
                    print(*v[0]);
                }
            """)

    def test_shared_container_does_not_make_its_mutable_references_copyable(self):
        self.execute("""
            fn lire(v: &[&mut Int; 1]) -> Int { return *v[0]; }
            fn main() {
                let mut a = [3]; let v = [&mut a[0]];
                print(lire(&v));
            }
        """, [3])
        with self.assertRaisesRegex(Error, 'référence mutable'):
            verify_program("""
                fn copier(v: &[&mut Int; 1]) -> &Int { return v[0]; }
                fn main() { let mut a = [3]; let v = [&mut a[0]]; let r = copier(&v); print(*r); }
            """)

    def test_update_contract_cannot_write_through_shared_container_parameter(self):
        from dataclasses import replace
        interface = verify_program("""
            fn changer(v: &mut [&Int; 1], d: &Int) { let old = v.replace(0, d); }
            fn lire(v: &[&Int; 1], d: &Int) { print(*v[0]); }
        """)
        original = interface.function_contracts['lire']
        forged_result = replace(original.result,
            parameter_fields=interface.function_contracts['changer'].result.parameter_fields)
        caller = Compiler(allow_legacy_reset=True)
        caller.contract_calls = True
        caller.function_contracts = dict(interface.function_contracts)
        caller.function_contracts['lire'] = replace(original, result=forged_result)
        nodes = Parser('let a = [1]; let b = [2]; let v = [&a[0]]; lire(&v, &b[0]);').parse()
        caller.index(nodes)
        with self.assertRaisesRegex(Error, 'conteneur emprunté mutable'):
            caller.block('root', nodes)

    def test_write_contract_keeps_target_valid_after_rhs_reset(self):
        declarations = """
            fn indice(p: &mut Pool<Int>) -> Int { p.reset(); return 1; }
            fn ecrire(v: &mut [&mut Int; 1], p: &mut Pool<Int>) { *v[0] = indice(p); }
        """
        program = declarations + """
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let mut n = new(q) Int(2);
                let mut v = [&mut n];
                ecrire(&mut v, &mut p);
                print(n);
            }
        """
        self.execute(program, [1], trace='reset\ndestroy n=1\nreclaim n\n')
        invalid = program.replace('new(q)', 'new(p)').replace('print(n);', '')
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, 'reset|distinct'):
                stage(invalid)

    def test_nested_reference_row_copy_and_return_keep_leaf_sources(self):
        program = """
            fn ligne(g: [[&Int; 2]; 2]) -> [&Int; 2] { return <- copy(g[1]); }
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let a = new(p) Int(1); let b = new(q) Int(2);
                let grille = [[&a, &b], [&b, &a]];
                let row = ligne(copy(grille));
                print(*row[0]);
                q.reset();
                print(*row[1]);
                p.reset();
            }
        """
        self.execute(program, [2, 1],
                     trace='destroy b=2\nreclaim b\nreset\ndestroy a=1\nreclaim a\nreset\n')
        with self.assertRaisesRegex(Error, 'reset|emprunt'):
            verify_program(program.replace('print(*row[0]);\n                q.reset();',
                                           'q.reset(); print(*row[0]);'))
        with self.assertRaisesRegex(Error, 'reset|emprunt'):
            verify_program(program.replace('print(*row[1]);\n                p.reset();',
                                           'p.reset(); print(*row[1]);'))

    def test_nested_mutable_reference_projection_returns_all_possible_leaves(self):
        program = """
            fn choisir(g: &mut [[&mut Int; 1]; 2], i: Int) -> &mut Int { return &mut *g[i][0]; }
            fn jouer(i: Int) {
                let mut a = [1]; let mut b = [2];
                let mut g = [[&mut a[0]], [&mut b[0]]];
                let mut r = choisir(&mut g, i);
                *r = 8;
                *g[0][0] = 3; *g[1][0] = 4;
                print(a[0]); print(b[0]);
            }
            fn main() { jouer(0); jouer(1); }
        """
        self.execute(program, [3, 4, 3, 4])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(program.replace('*r = 8;', '*g[1][0] = 9; *r = 8;'))


    def test_borrowed_row_overwrite_ends_only_the_replaced_leaf_lifetime(self):
        self.execute("""
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let a = new(p) Int(1); let b = new(q) Int(2);
                let mut g = [[&a], [&b]];
                let mut row = &mut g[0];
                p.reset(); row[0] = &b;
                print(*g[0][0]); print(*g[1][0]);
            }
        """, [2, 2], trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        with self.assertRaisesRegex(Error, 'emprunt|incompatible'):
            verify_program("""
                fn changer(v: &mut [&mut Int; 1], d: &mut Int) { v[0] = d; }
                fn main() {
                    let mut a = [1]; let mut b = [2];
                    let mut g = [[&mut a[0]], [&mut b[0]]];
                    changer(&mut g[0], &mut b[0]);
                    *g[0][0] = 3; *g[1][0] = 4;
                }
            """)

    def test_row_update_contract_preserves_unchanged_rows_and_new_sources(self):
        program = """
            fn changer(v: &mut [&Int; 1], d: &Int) { v[0] = d; }
            fn relayer(g: &mut [[&Int; 1]; 2], d: &Int) { changer(&mut g[1], d); }
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let a = new(p) Int(1); let b = new(q) Int(2);
                let mut g = [[&b], [&a]];
                relayer(&mut g, &b);
                p.reset(); print(*g[1][0]); print(*g[0][0]);
            }
        """
        self.execute(program, [2, 2],
                     trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, 'reset|emprunt'):
                stage(program.replace('p.reset(); print', 'q.reset(); print'))

    def test_returned_payload_write_contract_keeps_target_alive_through_rhs(self):
        program = """
            fn indice(p: &mut Pool<Int>) -> Int { p.reset(); return 1; }
            fn ecrire(d: &mut Int, p: &mut Pool<Int>) { *d = indice(p); }
            fn emprunter(v: &mut [&mut Int; 1]) -> &mut Int { return &mut *v[0]; }
            fn main() {
                let mut p = pool<Int>(1); let mut q = pool<Int>(1);
                let mut n = new(q) Int(2);
                let mut v = [&mut n]; let mut r = emprunter(&mut v);
                ecrire(r, &mut p);
            }
        """
        self.execute(program, [], trace='reset\ndestroy n=1\nreclaim n\n')
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, 'reset|distinct'):
                stage(program.replace('new(q)', 'new(p)'))

    def test_borrow_reassignment_preserves_old_reborrow_and_pointer_identity(self):
        self.execute('''
            fn main() {
                let mut a = [1]; let mut b = [2];
                let mut r = &mut a;
                let mut ancien = &mut *r;
                r = &mut b;
                ancien[0] = 3; r[0] = 4;
                print(a[0]); print(b[0]);
            }
        ''', [3, 4])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program('''
                fn main() {
                    let mut a = [1]; let mut b = [2];
                    let mut r = &mut a; let mut ancien = &mut *r;
                    r = &mut b; a[0] = 9; ancien[0] = 3;
                }
            ''')

    def test_borrow_reassignment_requires_mutability_type_and_durability(self):
        invalid = [
            ('let a=[1];let b=[2];let r=&a;r=&b;print(r[0]);', 'let mut'),
            ('let a=[1];let b=[2,3];let mut r=&a;r=&b;print(r[0]);', 'type'),
            ('let a=[1];let mut r=&a;{let b=[2];r=&b;}print(r[0]);', 'durable'),
            ('let mut a=[1];let b=[2];let mut r=&mut a;r=&b;print(r[0]);', 'mode'),
            ('let a=[1];let b=[2];let mut r=&a;r=copy(b).ref();print(r[0]);', 'temporaire'),
        ]
        for body, diagnostic in invalid:
            for stage in (verify_program, compile_source):
                with self.subTest(body=body, stage=stage.__name__), self.assertRaisesRegex(Error, diagnostic):
                    stage('fn main(){' + body + '}')

    def test_reassigned_borrow_unions_conditional_targets_and_loop_edges(self):
        self.execute('''
            fn jouer(choix: Int) {
                let a=[1]; let b=[2]; let mut r=&a;
                if choix == 0 { r=&b; }
                print(r[0]);
                let mut i=0;
                loop {
                    print(r[0]); r=&b;
                    if i == 1 { break; }
                    i=1; continue;
                }
                print(r[0]);
            }
            fn main(){jouer(0);jouer(1);}
        ''', [2, 2, 2, 2, 1, 1, 2, 2])
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program('''
                fn jouer(choix:Int){
                    let mut a=[1];let mut b=[2];let mut r=&mut a;
                    if choix==0 {r=&mut b;}
                    b[0]=9; r[0]=3;
                }
                fn main(){jouer(1);}
            ''')

    def test_reassigned_reference_container_releases_old_pool_only(self):
        program = '''
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);
                let v=[&a];let w=[&b];let mut r=&v;
                r=&w; p.reset(); print(*r[0]);
            }
        '''
        self.execute(program, [2], trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, 'reset|emprunt'):
                stage(program.replace('p.reset()', 'q.reset()'))

    def test_reassigned_container_parameter_updates_its_new_referent(self):
        program = '''
            fn changer(mut v:&mut [&Int;1], w:&mut [&Int;1], d:&Int){
                v=&mut *w; v[0]=d;
            }
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);
                let mut v=[&a];let mut w=[&a];
                changer(&mut v,&mut w,&b);
                print(*v[0]); p.reset(); print(*w[0]);
            }
        '''
        self.execute(program, [1, 2], trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, 'reset|emprunt'):
                stage(program.replace('p.reset(); print', 'q.reset(); print'))

    def test_stored_row_references_copy_replace_swap_and_index_once(self):
        self.execute('''
            fn marque(i:Int)->Int{print(i);return i;}
            fn lire(v:[&[Int;2];2])->Int{return v[1][0];}
            fn main(){
                let a=[1,2];let b=[3,4];let c=[5,6];let mut rows=[&a,&b];
                print(rows[marque(0)][marque(1)]);
                let old=rows.replace(0,&c); print(old[0]);print(rows[0][1]);
                rows.swap(0,1);print(lire(copy(rows)));
                let repeated=[&a;2];print(repeated[1][1]);
                let empty=[&b;0];print(empty.len());
            }
        ''', [0, 1, 2, 1, 6, 5, 2, 0])

    def test_stored_mutable_row_references_return_reborrow_and_resume(self):
        program = '''
            fn emprunter(v:&mut [&mut [Int;2];2], i:Int)->&mut [Int;2]{
                return &mut *v[i];
            }
            fn jouer(i:Int){
                let mut a=[1,2];let mut b=[3,4];let mut rows=[&mut a,&mut b];
                let mut r=emprunter(&mut rows,i);r[0]=8;
                rows[0][1]=9; rows[1][1]=7;
                print(a[1]);print(b[1]);
            }
            fn main(){jouer(0);jouer(1);}
        '''
        self.execute(program, [9, 7, 9, 7])
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, 'emprunt actif'):
                stage(program.replace('r[0]=8;', 'rows[0][1]=5;r[0]=8;'))
        with self.assertRaisesRegex(Error, 'copie.*mutable'):
            verify_program('fn main(){let mut a=[1];let rows=[&mut a];let c=copy(rows);}')

    def test_row_references_cross_opaque_results_and_update_contracts(self):
        program = '''
            fn extraire(g:&[[Int;2];2])->[&[Int;2];2]{return <-[&g[0],&g[1]];}
            fn relayer(g:&[[Int;2];2])->[&[Int;2];2]{let r=extraire(g);return <-r;}
            fn changer(v:&mut [&[Int;2];2], r:&[Int;2]){v[0]=r;}
            fn ligne(g:&[[Int;2];2])->&[Int;2]{return &g[1];}
            fn main(){
                let g=[[1,2],[3,4]];let b=[5,6];let mut rows=relayer(&g);
                changer(&mut rows,&b);print(rows[0][1]);
                let r=ligne(&g);print(r[0]);print(rows[1][1]);
            }
        '''
        self.execute(program, [6, 3, 4])
        with self.assertRaisesRegex(Error, 'durable|locale'):
            verify_program('''
                fn mauvais()->[&[Int;2];1]{let a=[1,2];return <-[&a];}
                fn main(){let rows=mauvais();print(rows[0][0]);}
            ''')
        interface=verify_program('fn ligne(v:[&[Int;2];1])->&[Int;2]{return v[0];}')
        caller=Compiler(allow_legacy_reset=True);caller.contract_calls=True
        caller.function_contracts=dict(interface.function_contracts)
        nodes=Parser('let a=[1,2];let rows=[&a];let r=ligne(copy(rows));print(r[0]);').parse()
        caller.index(nodes);caller.block('root',nodes)

    def test_stored_row_reference_bounds_and_whole_root_protection(self):
        self.execute('''
            fn lire(rows:[&[Int;2];1], i:Int){print(rows[0][i]);}
            fn main(){let a=[1,2];let rows=[&a];lire(copy(rows),2);}
        ''', [], diagnostic='indice hors limites')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program('''
                fn main(){let mut g=[[1,2],[3,4]];let rows=[&g[0]];
                    g[1][0]=9;print(rows[0][0]);}
            ''')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program('''
                fn main(){let mut g=[[1,2],[3,4]];
                    let rows=[&mut g[0],&mut g[1]];rows[0][0]=9;}
            ''')

    def test_old_container_reborrow_updates_old_storage_after_rebinding(self):
        program='''
            fn main(){
                let mut p=pool<Int>(2);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let c=new(p)Int(3);
                let mut va=[&a];let mut vb=[&b];let mut r=&mut va;
                let mut old=&mut *r;r=&mut vb;
                old[0]=&c;print(*va[0]);
                print(*vb[0]);q.reset();
            }
        '''
        self.execute(program, [3, 2], trace='destroy b=2\nreclaim b\nreset\ndestroy c=3\nreclaim c\ndestroy a=1\nreclaim a\n')
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, 'reset|emprunt'):
                stage(program.replace('print(*vb[0]);q.reset();','q.reset();print(*vb[0]);'))
        released = program.replace('q=pool<Int>(1)', 'q=pool<Int>(2)').replace('c=new(p)', 'c=new(q)')
        released = released.replace('old[0]=&c;print(*va[0]);', 'old[0]=&c;p.reset();print(*va[0]);')
        released = released.replace('print(*vb[0]);q.reset();', 'print(*vb[0]);')
        self.execute(released, [3, 2], trace='destroy a=1\nreclaim a\nreset\ndestroy c=3\nreclaim c\ndestroy b=2\nreclaim b\n')

    def test_row_reference_operations_against_pointer_index_model(self):
        rng=random.Random(20261106)
        model=[0,1,2]
        rows=[[10,11],[20,21],[30,31],[40,41]]
        body=['let a=[10,11];let b=[20,21];let c=[30,31];let d=[40,41];',
              'let mut v=[&a,&b,&c];']
        expected=[]
        for _ in range(40):
            left=rng.randrange(3)
            if rng.randrange(2):
                right=rng.randrange(3)
                body.append(f'v.swap({left},{right});')
                model[left],model[right]=model[right],model[left]
            else:
                incoming=rng.randrange(4)
                body.append(f'{{let old=v.replace({left},&{("a","b","c","d")[incoming]});print(old[0]);}}')
                expected.append(rows[model[left]][0]);model[left]=incoming
            column=rng.randrange(2)
            body.append(f'print(v[{left}][{column}]);')
            expected.append(rows[model[left]][column])
        self.execute('fn main(){'+''.join(body)+'}',expected)

    def test_self_reborrow_reassignment_converges_at_loop_back_edge(self):
        self.execute('''
            fn main(){
                let mut a=[1];let mut r=&mut a;let mut i=0;
                loop {
                    r=&mut *r; r[0]=3;
                    if i==1 {break;}
                    i=1;continue;
                }
                print(r[0]);print(a[0]);
            }
        ''', [3, 3])
