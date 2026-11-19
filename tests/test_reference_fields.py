"""Read-only &Int fields: lifetime dependencies, pools and opaque call contracts."""
from functools import partial, update_wrapper
from pathlib import Path
import random
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Compiler, Error, Parser, PathsReturned, verify_program, compile_program

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
import test_crust

DECL = ('enum View { Item { prefix: Int, data: &Int, tail: Int }, Empty {} } '
        'fn use_view(view: &View) { match &view { '
        'View.Item { prefix: a, data: r, tail: b } => { print(a); print(r); print(b); }, '
        'View.Empty {} => {} } } ')
SETUP = ('let mut data_pool = pool<Int>(3); let mut view_pool = pool<View>(2); '
         'let mut data = new(data_pool) Int(42); '
         'let mut view = new(view_pool) View.Item { prefix: 1, data: &data, tail: 2 }; ')


class ReferenceFieldTests(unittest.TestCase):
    execute = test_crust.PrototypeTests.execute
    with_source = staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self, code, pattern='emprunt|reset interdit|libérée|durable|différé'):
        with self.assertRaisesRegex(Error, pattern):
            verify_program(code)

    def test_original_drop_then_use_view_is_rejected(self):
        self.reject(DECL + SETUP + 'drop(-> data); use_view(&view);')

    def test_read_field_through_function_and_match(self):
        result = self.execute(DECL + SETUP + 'use_view(&view);', add_source=False)
        self.assertEqual(result.stdout, '1\n42\n2\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy view=View.Item', 'destroy data=42'])

    def test_last_holder_use_allows_referent_drop_before_implicit_holder_cleanup(self):
        result = self.execute(DECL + SETUP + 'use_view(&view); drop(-> data);', add_source=False)
        self.assertEqual(result.stdout, '1\n42\n2\n')
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy data=42', 'destroy view=View.Item'])

    def test_mutation_move_and_reassignment_of_live_referent_are_rejected(self):
        for operation in ('data.set(20);', 'let mut next = <- data;', 'data = new(data_pool) Int(20);'):
            with self.subTest(operation=operation):
                self.reject(DECL + SETUP + operation + 'use_view(&view);')

    def test_reference_to_readonly_field_cannot_be_made_mutable(self):
        self.reject(DECL + SETUP + 'match &view { View.Item{prefix:_,data:r,tail:_}=>{r.set(20);},View.Empty{}=>{} }', 'match|lecture|instruction')

    def test_mutable_borrow_prevents_field_construction(self):
        code = DECL + ('let mut data_pool=pool<Int>(1);let mut view_pool=pool<View>(1); '
            'let mut data=new(data_pool)Int(42);let mut loan=&mut data; '
            'let mut view=new(view_pool)View.Item{prefix:1,data:&data,tail:2};print(loan);use_view(&view);')
        self.reject(code)

    def test_reset_of_referent_pool_before_holder_use_rejected(self):
        self.reject(DECL + SETUP + 'data_pool.reset(); use_view(&view);')

    def test_reset_of_holder_pool_then_referent_drop_is_allowed(self):
        result = self.execute(DECL + SETUP + 'use_view(&view);view_pool.reset(); drop(-> data);', add_source=False)
        self.assertEqual(result.stderr.count('destroy view=View.Item'), 1)
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_holder_move_keeps_dependency(self):
        self.reject(DECL + SETUP + 'let mut moved=<- view;drop(-> data);use_view(&moved);')

    def test_explicit_holder_drop_releases_borrow(self):
        result = self.execute(DECL + SETUP + 'drop(-> view);data.set(20);print(data);', add_source=False)
        self.assertEqual(result.stdout, '20\n')

    def test_holder_reassignment_releases_old_dependency_and_keeps_new_one(self):
        prefix = DECL + SETUP + 'use_view(&view);let mut other = new(data_pool) Int(7); '
        assignment = 'view=new(view_pool)View.Item{prefix:3,data:&other,tail:4};'
        result = self.execute(prefix + assignment + 'drop(-> data);use_view(&view);', add_source=False)
        self.assertEqual(result.stdout, '1\n42\n2\n3\n7\n4\n')
        self.reject(prefix + assignment + 'drop(-> other);use_view(&view);')

    def test_pending_reference_field_survives_later_initializer_effects(self):
        declaration = DECL + 'fn clear(p:&mut Pool<Int>)->Int{p.reset();return 1;} '
        self.reject(declaration + ('let mut data_pool=pool<Int>(1);let mut view_pool=pool<View>(1); '
            'let mut data=new(data_pool)Int(42);let mut view=new(view_pool)View.Item{'
            'prefix:1,data:&data,tail:clear(&mut data_pool)};use_view(&view);'))
        consume = DECL + 'fn consume(mut x:->Int)->Int{drop(-> x);return 0;} '
        self.reject(consume + ('let mut data_pool=pool<Int>(1);let mut view_pool=pool<View>(1); '
            'let mut data=new(data_pool)Int(42);let mut view=new(view_pool)View.Item{'
            'prefix:1,data:&data,tail:consume(-> data)};'))

    def test_reference_field_requires_explicit_named_int_borrow(self):
        prefix = DECL + 'let mut data_pool=pool<Int>(1);let mut view_pool=pool<View>(1);let mut data=new(data_pool)Int(42);print(data);'
        for rhs in ('42', 'data', '&mut data', '&new(data_pool) Int(7)'):
            with self.subTest(rhs=rhs):
                self.reject(prefix + f'let mut view=new(view_pool)View.Item{{prefix:1,data:{rhs},tail:2}};use_view(&view);',
                            'champ|implicite|mode')

    def test_mixed_layout_and_addresses_are_preserved(self):
        source = ('enum Mixed { A { a: Int, x: &Int, b: Int, y: &Int, c: Int } } '
            'let mut p=pool<Int>(2);let mut q=pool<Mixed>(1);let mut x=new(p)Int(10);let mut y=new(p)Int(20);'
            'let mut m=new(q)Mixed.A{a:1,x:&x,b:2,y:&y,c:3};print(m);address(x);'
            'match &m { Mixed.A{a:_,x:r,b:_,y:s,c:_}=>{address(r);print(r);print(s);} }')
        result = self.execute(source, add_source=False)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], 'Mixed.A(1, 10, 2, 20, 3)')
        self.assertEqual(lines[1], lines[2])
        self.assertEqual(lines[3:], ['10', '20'])

    def test_empty_variant_has_no_reference_dependencies(self):
        result = self.execute(DECL + ('let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut data=new(p)Int(42);'
            'let mut view=new(q)View.Empty{};drop(-> data);use_view(&view);'), add_source=False)
        self.assertEqual(result.stdout, '')
        self.execute('enum V{Item{data:&Int},Empty{}}let mut p=pool<V>(1);let mut v=new(p)V.Empty{};'
            'match &v{V.Item{data:r}=>{let mut n=*r;print(n);address(r);},V.Empty{}=>{}}', add_source=False)

    def test_conditional_holder_unions_referents_in_both_branches(self):
        prefix = DECL + ('let mut p=pool<Int>(2);let mut q=pool<View>(1);let mut x=new(p)Int(10);let mut y=new(p)Int(20);'
            'let mut view=if true {let mut a=new(q)View.Item{prefix:1,data:&x,tail:2};<-a} '
            'else {let mut b=new(q)View.Item{prefix:3,data:&y,tail:4};<-b};')
        for name in ('x', 'y'):
            self.reject(prefix + f'drop(-> {name});use_view(&view);')
        result = self.execute(prefix + 'use_view(&view);', add_source=False)
        self.assertEqual(result.stdout, '1\n10\n2\n')

    def test_block_transfer_allowed_when_referent_already_in_parent(self):
        source = DECL + ('let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut data=new(p)Int(42);'
            'let mut view={let mut local=new(q)View.Item{prefix:1,data:&data,tail:2};<-local};use_view(&view);')
        result = self.execute(source, add_source=False)
        self.assertEqual(result.stdout, '1\n42\n2\n')

    def test_block_transfer_of_same_scope_referent_is_explicitly_deferred(self):
        self.reject(DECL + ('let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut view={'
            'let mut data=new(p)Int(42);let mut local=new(q)View.Item{prefix:1,data:&data,tail:2};<-local};use_view(&view);'))

    def test_function_return_of_reference_holding_type_requires_result(self):
        self.reject(DECL + 'fn make(p:&mut Pool<View>,data:&Int)-><-View {}', 'retour.*attendu owned')

    def test_uninvoked_function_reset_then_read_field_has_contract_obligation(self):
        source = DECL + ('fn clear_read(p:&mut Pool<Int>,v:&View){p.reset();use_view(v);} '
            'fn relay(v:&View,p:&mut Pool<Int>){clear_read(p,v);}')
        checked = verify_program(source)
        requirements = checked.function_constraints['relay'].requirements
        self.assertTrue(any(c.left.kind == 'allocation_field_parameter' or c.right.kind == 'allocation_field_parameter'
                            for c in requirements))
        self.reject(source + SETUP + 'clear_read(&mut data_pool,&view);')

    def test_read_field_then_reset_at_last_use_is_allowed(self):
        source = DECL + 'fn read_clear(p:&mut Pool<Int>,v:&View){use_view(v);p.reset();}'
        result = self.execute(source + SETUP + 'read_clear(&mut data_pool,&view);', add_source=False)
        self.assertEqual(result.stdout, '1\n42\n2\n')
        self.assertEqual(result.stderr.count('destroy data=42'), 1)

    def test_opaque_contract_protects_field_source_without_body_access(self):
        source = DECL + 'fn clear_read(p:&mut Pool<Int>,v:&View){p.reset();use_view(v);}'
        interface = verify_program(source)
        checker = Compiler(allow_legacy_reset=True)
        checker.enums, checker.function_contracts = interface.enums, interface.function_contracts
        checker.contract_calls = True
        nodes = Parser(SETUP + 'clear_read(&mut data_pool,&view);').parse()
        checker.index(nodes)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            checker.block('root', nodes)
        self.assertEqual(checker.functions, {})

    def test_pending_holder_argument_protects_target_from_nested_reset(self):
        source = DECL + ('fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;} '
            'fn observe(v:&View,n:Int){}')
        self.reject(source + SETUP + 'observe(&view,clear(&mut data_pool));')

    def test_pool_slot_reuse_does_not_revive_old_referent(self):
        self.reject(DECL + SETUP + 'drop(-> data);let mut next=new(data_pool)Int(7);use_view(&view);')
        result = self.execute(DECL + SETUP + 'use_view(&view);drop(-> data);'
            'let mut next=new(data_pool)Int(7);print(next);', add_source=False)
        self.assertEqual(result.stdout, '1\n42\n2\n7\n')

    def test_loop_future_holder_use_keeps_target_borrowed(self):
        self.reject(DECL + SETUP + 'loop{use_view(&view);data.set(20);continue;}')
        self.execute(DECL + SETUP + 'loop{use_view(&view);break;}data.set(20);', add_source=False)

    def test_conservative_nonreturning_reset_policy_is_kept(self):
        source = ('fn maybe(p:&mut Pool<Int>,stop:Int){if stop==1{p.reset();loop{}}}'
            'let mut p=pool<Int>(1);let mut data=new(p)Int(42);maybe(&mut p,0);print(data);')
        self.reject(source, 'reset interdit')

    def test_independent_dependency_frontier_model(self):
        accepted = rejected = 0
        for seed in range(32):
            rng = random.Random(seed)
            targets = [rng.randrange(3), rng.randrange(3)]
            affected = rng.randrange(3)
            before = bool(seed % 2)
            operation = ('drop', 'mutate', 'reset')[seed % 3]
            # Model knows object identities and the next holder read, no compiler state.
            expected_valid = not before or (operation != 'reset' and affected not in targets)
            code = ['enum Pair { Item { x: &Int, y: &Int } }',
                    'let mut p=pool<Int>(3);let mut q=pool<Pair>(1);']
            code.extend(f'let mut d{i}=new(p)Int({10+i});print(d{i});' for i in range(3))
            code.append(f'let mut view=new(q)Pair.Item{{x:&d{targets[0]},y:&d{targets[1]}}};')
            action = {'drop':f'drop(-> d{affected});','mutate':f'd{affected}.set(99);','reset':'p.reset();'}[operation]
            code.extend([action, 'print(view);'] if before else ['print(view);', action])
            with self.subTest(seed=seed, operation=operation, targets=targets):
                source = ' '.join(code)
                if expected_valid:
                    result = self.execute(source, add_source=False)
                    self.assertEqual(result.stdout, f'10\n11\n12\nPair.Item({10+targets[0]}, {10+targets[1]})\n')
                    accepted += 1
                else:
                    self.reject(source)
                    rejected += 1
        self.assertEqual((accepted, rejected), (19, 13))


if __name__ == '__main__':
    unittest.main()
