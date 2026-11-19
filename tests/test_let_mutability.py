"""Bindings, mutation capability and allocation identity are independent."""
from functools import partial, update_wrapper
from pathlib import Path
import random
import sys
import unittest
sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Error, verify_program, compile_program, compile_source

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust

POOL='let mut p=pool<Int>(2);'
DATA=POOL+'let mut d=new(p)Int(10);'
BORROW='fn borrow(d:&Int)->&Int{return d;}'

class LetMutabilityTests(unittest.TestCase):
    execute=test_crust.PrototypeTests.execute
    with_source=staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self,source,pattern='immuable|lecture|emprunt|reset interdit|allocation|mode|type'):
        for stage in (verify_program,compile_source):
            with self.subTest(stage=stage.__name__):
                with self.assertRaisesRegex(Error,pattern):stage(source)

    def test_assignment_and_method_mutate_the_same_allocation(self):
        result=self.execute(DATA+'address(d);d=20;address(d);d.set(30);address(d);print(d);',add_source=False)
        rows=result.stdout.splitlines()
        self.assertEqual(rows[0],rows[1]);self.assertEqual(rows[1],rows[2]);self.assertEqual(rows[3:],['30'])
        self.assertEqual([r for r in result.stderr.splitlines() if r.startswith('destroy ')],['destroy d=30'])
        checked,c=compile_program(DATA+'d=20;d.set(30);print(d);')
        self.assertEqual(len(checked.allocations),1)
        self.assertEqual(c[c.index('int main(void)'):].count('cell_new('),1)

    def test_immutable_owner_cannot_be_mutated_or_borrowed_mutably(self):
        source=POOL+'let d=new(p)Int(10);'
        for operation in ('d=20;','d.set(20);','let r=&mut d;print(r);'):
            self.reject(source+operation,'immuable')

    def test_binding_mutability_does_not_change_shared_reference_capability(self):
        source=DATA+'let mut r=&d;'
        self.reject(source+'r.set(20);','lecture')
        self.reject(source+'r=20;','type|mode')
        self.reject(source+'fn edit(d:&mut Int){d.set(20);}edit(r);','lecture|mutable')

    def test_immutable_binding_to_mutable_reference_can_mutate_target(self):
        source=DATA+'let r=&mut d;r.set(20);print(r);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'20\n')
        self.reject(source+'let mut b=new(p)Int(7);r=&mut b;print(r);','immuable')

    def test_mutable_reference_binding_can_be_reassigned(self):
        source=DATA+'let mut b=new(p)Int(7);let mut r=&mut d;r.set(20);r=&mut b;r.set(30);print(d);print(r);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'20\n30\n')

    def test_mutable_owned_parameter_can_receive_an_immutable_binding(self):
        functions='fn edit(mut d:->Int){d=20;d.set(30);print(d);}'
        source=functions+POOL+'let d=new(p)Int(10);edit(->d);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'30\n')
        for operation in ('d=20;','d.set(20);','let r=&mut d;print(r);'):
            self.reject('fn bad(d:->Int){'+operation+'}','immuable')

    def test_mutable_reference_parameter_needs_no_mut_binding(self):
        functions='fn edit(d:&mut Int){d.set(20);}fn relay(d:&mut Int){edit(d);}'
        self.assertEqual(self.execute(functions+DATA+'relay(&mut d);print(d);',add_source=False).stdout,'20\n')
        self.reject('fn bad(d:&Int){d.set(20);}','lecture')

    def test_mutable_scalar_assignment_works_across_nested_scopes(self):
        source='let mut n=0;if true{n=20;}while n==20{n=30;continue;}print(n);n.set(40);print(n);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'30\n40\n')
        self.reject('let n=0;n=20;','immuable')
        self.reject('let n=0;n.set(20);','immuable')

    def test_scalar_function_parameters_have_explicit_mutability(self):
        self.reject('fn bad(n:Int){n=20;}','immuable')
        self.assertEqual(self.execute('fn edit(mut n:Int)->Int{n=20;return n;}let n=edit(10);print(n);',add_source=False).stdout,'20\n')
        self.assertEqual(self.execute('fn edit(mut n:Int)->Int{n=20;return n;}let n=10;let result=edit(n);print(n);print(result);',add_source=False).stdout,'10\n20\n')

    def test_read_borrow_blocks_both_mutation_spellings_until_last_use(self):
        for operation in ('d=20;','d.set(20);'):
            self.reject(DATA+'let r=&d;'+operation+'print(r);','emprunt')
            self.assertEqual(self.execute(DATA+'let r=&d;print(r);'+operation+'print(d);',add_source=False).stdout,'10\n20\n')

    def test_mutable_borrow_blocks_direct_owner_write(self):
        for operation in ('d=20;','d.set(20);'):
            self.reject(DATA+'let r=&mut d;'+operation+'r.set(30);','emprunt')

    def test_content_write_preserves_return_contract_identity(self):
        functions='fn edit(mut d:->Int)-><-Int{d=20;d.set(30);return<-d;}'
        source=functions+DATA+'address(d);let result=edit(->d);address(result);print(result);'
        c=verify_program(functions)
        self.assertEqual(c.function_results['edit'].same_parameter,0)
        self.assertEqual(c.function_contracts['edit'].mutable_parameters,{'d'})
        rows=self.execute(source,add_source=False).stdout.splitlines()
        self.assertEqual(rows[0],rows[1]);self.assertEqual(rows[2:],['30'])

    def test_rhs_last_borrow_use_can_precede_content_write(self):
        functions='fn read(d:&Int)->Int{return *d;}'
        self.assertEqual(self.execute(functions+DATA+'let r=&d;d=read(r);print(d);',add_source=False).stdout,'10\n')
        self.reject(functions+DATA+'let r=&d;d=read(r);print(r);','emprunt')

    def test_rhs_reset_cannot_make_old_target_writable(self):
        functions='fn clear(p:&mut Pool<Int>)->Int{p.reset();return 20;}'
        self.reject(functions+DATA+'d=clear(&mut p);','reset|utilisable|libérée')
        functions='fn consume(d:->Int)->Int{drop(->d);return 20;}'
        self.reject(functions+DATA+'d=consume(->d);','utilisable|libérée|emprunt')

    def test_wrapper_contract_keeps_write_target_source_history(self):
        functions='fn clear(p:&mut Pool<Int>)->Int{p.reset();return 20;}'
        functions+='fn write(p:&mut Pool<Int>,mut d:->Int)-><-Int{d=clear(p);return<-d;}'
        self.reject(functions+DATA+'let result=write(&mut p,->d);print(result);','reset interdit')
        void_write='fn clear(p:&mut Pool<Int>)->Int{p.reset();return 20;}fn write(p:&mut Pool<Int>,mut d:->Int){d=clear(p);}'
        self.reject(void_write+DATA+'write(&mut p,->d);','reset interdit')

    def test_replacement_still_destroys_after_rhs_and_requires_mut(self):
        result=self.execute(DATA+'d=20;d=new(p)Int(30);print(d);',add_source=False)
        self.assertEqual([r for r in result.stderr.splitlines() if r.startswith('destroy ')],['destroy d=20','destroy d=30'])
        self.reject(POOL+'let d=new(p)Int(10);if *d!=10{print(999);}d=new(p)Int(30);print(d);','immuable')

    def test_immutable_owner_can_be_consumed_without_mut(self):
        result=self.execute(POOL+'let d=new(p)Int(10);drop(->d);p.reset();',add_source=False)
        self.assertEqual(result.stderr.count('destroy d=10'),1)
        self.reject(POOL+'let d=new(p)Int(10);let r=&d;drop(->d);print(r);','emprunt')

    def test_mutation_then_drop_and_reset_reuses_the_same_slot(self):
        source='let mut p=pool<Int>(1);let mut d=new(p)Int(10);address(d);d=20;d.set(30);drop(->d);p.reset();'
        source+='let fresh=new(p)Int(7);address(fresh);print(fresh);'
        result=self.execute(source,add_source=False);rows=result.stdout.splitlines()
        self.assertEqual(rows[0],rows[1]);self.assertEqual(rows[2:],['7'])
        self.assertEqual(result.stderr.count('destroy d=30'),1)

    def test_returned_reference_blocks_mutation_drop_and_reset(self):
        for operation in ('d=20;','d.set(20);','drop(->d);','p.reset();'):
            self.reject(BORROW+DATA+'let r=borrow(&d);'+operation+'print(r);','emprunt|reset interdit')

    def test_pool_binding_mutability_is_distinct_from_parameter_capability(self):
        self.reject('let p=pool<Int>(1);let d=new(p)Int(10);print(d);','mutable')
        self.reject('let p=pool<Int>(1);p.reset();','mutable')
        self.reject('fn bad(p:&Pool<Int>){p.reset();}','mutable')
        self.assertEqual(self.execute('fn make(p:&mut Pool<Int>)-><-Int{let d=new(p)Int(10);return<-d;}'+POOL+'let d=make(&mut p);print(d);',add_source=False).stdout,'10\n')

    def test_child_import_preserves_binding_mutability(self):
        self.reject(POOL+'let d=new(p)Int(10);{->d;d=20;}','immuable')
        self.assertEqual(self.execute(DATA+'{->d;d=20;print(d);<-d;}print(d);',add_source=False).stdout,'20\n20\n')

    def test_reference_assignment_does_not_write_through_implicitly(self):
        self.reject(DATA+'let mut r=&mut d;r=20;','type|mode')
        self.reject(DATA+'let r=&mut d;r=20;','immuable|type|mode')

    def test_legacy_spellings_are_rejected(self):
        self.reject('var n=10;','remplacé')
        self.reject('let mut n=10;set(n,20);','remplacé')

    def test_binding_capability_matrix(self):
        # Declarative permission table, independent of compiler bindings and loans.
        permissions={
            ('owner',False):set(), ('owner',True):{'assign','method','borrow'},
            ('shared',False):set(), ('shared',True):set(),
            ('exclusive',False):{'method'}, ('exclusive',True):{'method'},
        }
        accepted=rejected=0
        for (kind,mutable),allowed in permissions.items():
            for operation in ('assign','method','borrow'):
                declaration='let '+('mut ' if mutable else '')
                name='d' if kind=='owner' else 'r'
                setup=(POOL+declaration+'d=new(p)Int(10);' if kind=='owner' else
                       DATA+declaration+'r='+('&d;' if kind=='shared' else '&mut d;'))
                statement=(name+'=20;print('+name+');' if operation=='assign' else
                           name+'.set(20);print('+name+');' if operation=='method' else
                           'let probe=&mut '+name+';print(probe);')
                with self.subTest(kind=kind,mutable=mutable,operation=operation):
                    if operation in allowed:
                        self.assertEqual(self.execute(setup+statement,add_source=False).stdout,
                                         '10\n' if operation=='borrow' else '20\n')
                        accepted+=1
                    else:
                        self.reject(setup+statement)
                        rejected+=1
        self.assertEqual((accepted,rejected),(5,13))

    def test_independent_payload_model(self):
        # Oracle is a list of integer states; no compiler identity or C bookkeeping.
        for seed in range(12):
            rng=random.Random(seed);expected=[];source=DATA+'address(d);'
            for step in range(12):
                value=rng.randrange(-100,101);expected.append(str(value))
                source+=(f'd={value};' if rng.randrange(2) else f'd.set({value});')+'print(d);'
            source+='address(d);drop(->d);p.reset();'
            with self.subTest(seed=seed):
                result=self.execute(source,add_source=False);rows=result.stdout.splitlines()
                self.assertEqual(rows[0],rows[-1]);self.assertEqual(rows[1:-1],expected)
                self.assertEqual([r for r in result.stderr.splitlines() if r.startswith('destroy ')],['destroy d='+expected[-1]])

if __name__=='__main__':unittest.main()
