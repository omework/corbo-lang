"""Returned exclusive loans preserve targets, parents and storage history."""
from functools import partial, update_wrapper
from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Compiler, Parser, Error, verify_program, compile_program, compile_source

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
from effects import EffectAnalyzer
from results import ResultAnalyzer, BorrowTarget
import test_crust

MUT='fn borrow_mut(d:&mut Int)->&mut Int{return d;}'
SHARED='fn borrow(d:&Int)->&Int{return d;}'
CHOOSE='fn choose(n:Int,a:&mut Int,b:&mut Int)->&mut Int{if n==0{return a;}return b;}'
SETUP='let mut p=pool<Int>(3);let mut nombre=new(p)Int(10);'

class MutableBorrowReturnTests(unittest.TestCase):
    execute=test_crust.PrototypeTests.execute
    with_source=staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self,source,pattern='emprunt|reset interdit|durable|mutable|lecture|retour|mode|immuable|allocation'):
        for stage in (verify_program,compile_source):
            with self.subTest(stage=stage.__name__):
                with self.assertRaisesRegex(Error,pattern):stage(source)

    def test_signature_and_contract_record_exclusive_mode(self):
        c=verify_program(MUT)
        summary=c.function_contracts['borrow_mut'].result
        self.assertEqual(summary.mode,'mut')
        self.assertEqual(summary.typ,'Int')
        self.assertEqual(summary.reference_targets,{BorrowTarget('parameter',0)})
        self.assertFalse(summary.candidates)
        self.assertEqual(summary.describe(c.function_contracts['borrow_mut'].parameters)['mode'],'mut')

    def test_preferred_mut_binding_preserves_address_and_cleanup(self):
        source=MUT+SETUP+'address(nombre);let mut vue=borrow_mut(&mut nombre);address(vue);vue.set(30);print(vue);nombre=40;print(nombre);'
        r=self.execute(source,add_source=False);lines=r.stdout.splitlines()
        self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[2:],['30','40'])
        self.assertEqual([x for x in r.stderr.splitlines() if x.startswith('destroy ')],['destroy nombre=40'])
        c,code=compile_program(source)
        self.assertEqual(len(c.allocations),1)
        main=code[code.index('int main(void)'):]
        self.assertEqual(main.count('cell_new('),1);self.assertEqual(main.count('cell_drop('),1)

    def test_exclusive_reference_capability_does_not_require_mut_binding(self):
        self.assertEqual(self.execute(MUT+SETUP+'let vue=borrow_mut(&mut nombre);vue.set(30);print(vue);',add_source=False).stdout,'30\n')
        self.reject(MUT+'let mut p=pool<Int>(1);let nombre=new(p)Int(10);let mut vue=borrow_mut(&mut nombre);vue.set(30);','immuable')

    def test_original_accesses_are_blocked_until_last_use(self):
        prefix=MUT+SETUP+'let mut vue=borrow_mut(&mut nombre);'
        for operation in ('print(nombre);','address(nombre);','nombre=20;','nombre.set(20);',
                          'drop(->nombre);','p.reset();','let moved=<-nombre;',
                          'let other=&nombre;print(other);','let other=&mut nombre;other.set(20);'):
            self.reject(prefix+operation+'print(vue);')

    def test_readonly_reference_cannot_be_returned_as_mutable(self):
        self.reject('fn bad(d:&Int)->&mut Int{return d;}','attendu mut|mutable|lecture')
        self.reject('fn bad(mut d:&Int)->&mut Int{return d;}','attendu mut|mutable|lecture')
        self.reject(SHARED+'fn bad(d:&mut Int)->&mut Int{return borrow(d);}','attendu mut|mutable')

    def test_mutable_result_can_be_narrowed_to_shared(self):
        functions=MUT+'fn shared(d:&mut Int)->&Int{return borrow_mut(d);}'
        prefix=functions+SETUP+'let vue=shared(&mut nombre);'
        self.assertEqual(self.execute(prefix+'print(vue);nombre=20;print(nombre);',add_source=False).stdout,'10\n20\n')
        self.reject(prefix+'vue.set(30);','lecture')
        self.reject(prefix+'nombre=20;print(vue);','emprunt')

    def test_successive_calls_preserve_exclusive_target_and_parents(self):
        functions=MUT+'fn middle(d:&mut Int)->&mut Int{let mut v=borrow_mut(d);return v;}'
        functions+='fn outer(d:&mut Int)->&mut Int{return middle(d);}'
        prefix=functions+SETUP+'let parent=&mut nombre;let mut vue=outer(parent);'
        self.assertEqual(self.execute(prefix+'vue.set(30);parent.set(40);print(parent);',add_source=False).stdout,'40\n')
        for operation in ('print(parent);','parent.set(20);'):
            self.reject(prefix+operation+'vue.set(30);','emprunt')

    def test_nested_mutable_and_shared_arguments_from_mutable_parent(self):
        funcs=MUT+'fn edit(d:&mut Int){d.set(30);}fn read(d:&Int)->Int{return *d;}'
        source=funcs+SETUP+'let parent=&mut nombre;edit(borrow_mut(parent));let n=read(borrow_mut(parent));print(n);parent.set(40);print(parent);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'30\n40\n')

    def test_cannot_prepare_two_overlapping_mutable_arguments(self):
        funcs=MUT+'fn pair(a:&mut Int,b:&mut Int){a.set(20);b.set(30);}'
        self.reject(funcs+SETUP+'let parent=&mut nombre;pair(borrow_mut(parent),borrow_mut(parent));','aliasés|emprunt')
        self.reject(funcs+SETUP+'let mut vue=borrow_mut(&mut nombre);pair(vue,vue);','aliasés|emprunt')

    def test_shared_child_suspends_then_resumes_returned_mutable_loan(self):
        prefix=MUT+SHARED+SETUP+'let parent=&mut nombre;let mut vue=borrow_mut(parent);let child=borrow(vue);'
        self.reject(prefix+'vue.set(20);print(child);','emprunt')
        self.reject(prefix+'parent.set(20);print(child);','emprunt')
        self.assertEqual(self.execute(prefix+'print(child);vue.set(30);parent.set(40);print(parent);',add_source=False).stdout,'10\n40\n')

    def test_local_and_owned_parameter_targets_never_promoted(self):
        sources=[
          'fn bad(p:&mut Pool<Int>)->&mut Int{let mut d=new(p)Int(10);return &mut d;}',
          MUT+'fn bad(p:&mut Pool<Int>)->&mut Int{let mut d=new(p)Int(10);let mut v=borrow_mut(&mut d);return v;}',
          'fn bad(mut d:->Int)->&mut Int{return &mut d;}',
          MUT+'fn bad(mut d:->Int)->&mut Int{return borrow_mut(&mut d);}',
        ]
        for source in sources:
            self.reject(source,'durable')
            nodes=Parser(source).parse();functions={n.args[0]:n for n in nodes}
            effects=EffectAnalyzer(functions,{},Error).infer_all()
            with self.assertRaisesRegex(Error,'durable'):
                ResultAnalyzer(functions,effects,Error).infer_all()

    def test_each_nested_boundary_checks_ancestor_lifetime(self):
        funcs='fn nested(d:&mut Int)->&mut Int{{{return d;}}}'
        self.assertEqual(self.execute(funcs+SETUP+'{let mut v=nested(&mut nombre);v.set(30);print(v);}print(nombre);',add_source=False).stdout,'30\n30\n')

    def test_conditional_result_protects_all_possible_targets(self):
        prefix=CHOOSE+SETUP+'let mut b=new(p)Int(7);let mut vue=choose(0,&mut nombre,&mut b);'
        for target in ('nombre','b'):
            for op in (f'print({target});',f'{target}=20;',f'drop(->{target});'):
                self.reject(prefix+op+'print(vue);')
        self.assertEqual(self.execute(prefix+'vue.set(30);print(vue);print(nombre);print(b);',add_source=False).stdout,'30\n30\n7\n')

    def test_union_of_mutable_parents_resumes_after_last_use(self):
        prefix=CHOOSE+SETUP+'let mut b=new(p)Int(7);let a_ref=&mut nombre;let b_ref=&mut b;let mut vue=choose(1,a_ref,b_ref);'
        self.reject(prefix+'a_ref.set(20);vue.set(30);','emprunt')
        self.reject(prefix+'b_ref.set(20);vue.set(30);','emprunt')
        for name in ('a_ref','b_ref'):
            self.reject(prefix+f'print({name});vue.set(30);','emprunt')
        self.assertEqual(self.execute(prefix+'vue.set(30);a_ref.set(40);b_ref.set(50);print(a_ref);print(b_ref);',add_source=False).stdout,'40\n50\n')

    def test_each_possible_source_blocks_reset_until_last_use(self):
        prefix=CHOOSE+SETUP+'let mut q=pool<Int>(1);let mut b=new(q)Int(7);let mut vue=choose(1,&mut nombre,&mut b);'
        for pool in ('p','q'):self.reject(prefix+pool+'.reset();vue.set(30);','reset interdit')
        self.assertEqual(self.execute(prefix+'vue.set(30);print(vue);p.reset();q.reset();',add_source=False).stdout,'30\n')

    def test_last_use_allows_drop_reset_and_reuse(self):
        source=MUT+'let mut p=pool<Int>(1);let mut nombre=new(p)Int(10);address(nombre);let mut vue=borrow_mut(&mut nombre);vue.set(30);drop(->nombre);p.reset();let fresh=new(p)Int(7);address(fresh);print(fresh);'
        r=self.execute(source,add_source=False);lines=r.stdout.splitlines()
        self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[2:],['7'])
        self.assertEqual(r.stderr.count('destroy nombre=30'),1)
        self.reject(source+'print(vue);')

    def test_prepared_mutable_result_blocks_later_reset(self):
        functions=MUT+'fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;}fn pair(d:&mut Int,n:Int){d.set(20);}'
        self.reject(functions+SETUP+'pair(borrow_mut(&mut nombre),clear(&mut p));','reset interdit')

    def test_prepared_union_keeps_secondary_target_exclusive(self):
        funcs=CHOOSE+'fn pair(a:&mut Int,b:&Int){a.set(20);print(b);}'
        self.reject(funcs+SETUP+'let mut b=new(p)Int(7);pair(choose(0,&mut nombre,&mut b),&b);','aliasés|emprunt')

    def test_field_view_reborrow_suspends_exclusive_parent(self):
        decl='enum V{Item{d:&Int}}'
        prefix=decl+MUT+SETUP+'let mut q=pool<V>(1);let mut vue=borrow_mut(&mut nombre);let holder=new(q)V.Item{d:vue};'
        self.reject(prefix+'vue.set(20);print(holder);','emprunt')
        self.assertEqual(self.execute(prefix+'print(holder);vue.set(30);print(vue);',add_source=False).stdout,'V.Item(10)\n30\n')

    def test_mutable_alias_can_be_reassigned_without_moving_target(self):
        source=MUT+SETUP+'let mut b=new(p)Int(7);let mut vue=borrow_mut(&mut nombre);vue.set(20);vue=borrow_mut(&mut b);vue.set(30);print(nombre);print(b);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'20\n30\n')
        source=MUT+SETUP+'let parent=&mut nombre;let mut vue=borrow_mut(parent);vue=borrow_mut(vue);vue.set(30);print(vue);parent.set(40);print(parent);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'30\n40\n')

    def test_no_implicit_ownership_or_nested_reference(self):
        prefix=MUT+SETUP+'let mut vue=borrow_mut(&mut nombre);'
        self.reject(prefix+'drop(->vue);','allocation explicite')
        self.reject(prefix+'let other=&mut vue;other.set(20);','emprunt imbriqué')
        self.reject(prefix+'print(vue);vue=20;','type|mode')

    def test_loop_keeps_next_iteration_use_protected(self):
        source=MUT+SETUP+'let mut vue=borrow_mut(&mut nombre);let mut n=0;while n==0{vue.set(30);n=1;continue;}print(vue);nombre=40;print(nombre);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'30\n40\n')
        self.reject(MUT+SETUP+'let mut vue=borrow_mut(&mut nombre);loop{vue.set(30);p.reset();continue;}','reset interdit')

    def test_reset_history_survives_mutable_result_calls(self):
        funcs=MUT+'fn bad(p:&mut Pool<Int>,d:&mut Int)->&mut Int{let mut v=borrow_mut(d);p.reset();return v;}'
        self.reject(funcs+SETUP+'let mut vue=bad(&mut p,&mut nombre);vue.set(30);','reset interdit')

    def test_mutable_result_calls_remain_opaque(self):
        c=verify_program(MUT)
        # A caller has only the contract catalogue, with no body or inference maps.
        caller=Compiler(allow_legacy_reset=True);caller.contract_calls=True;caller.function_contracts=c.function_contracts
        nodes=Parser(SETUP+'let mut vue=borrow_mut(&mut nombre);vue.set(30);').parse();caller.index(nodes)
        caller.block('root',nodes)
        self.assertEqual(caller.contract_call_log,['borrow_mut'])
        self.assertEqual(caller.functions,{})
        self.assertEqual(caller.definitions,[])

    def test_forged_mutable_contract_cannot_upgrade_shared_input(self):
        shared=verify_program(SHARED).function_contracts['borrow']
        forged=replace(shared,result_type=('mut','Int'),result=replace(shared.result,mode='mut'))
        caller=Compiler(allow_legacy_reset=True);caller.contract_calls=True;caller.function_contracts={'borrow':forged}
        nodes=Parser(SETUP+'let mut vue=borrow(&nombre);vue.set(30);').parse();caller.index(nodes)
        with self.assertRaisesRegex(Error,'résultat mutable sans paramètre mutable'):caller.block('root',nodes)

    def test_early_return_cancels_call_and_releases_prepared_loan(self):
        functions=MUT+'fn pair(d:&mut Int,other:->Int){d.set(99);}'
        functions+='fn stop(p:&mut Pool<Int>){let mut local=new(p)Int(10);pair(borrow_mut(&mut local),->{return;});}'
        result=self.execute(functions+'let mut p=pool<Int>(1);stop(&mut p);p.reset();',add_source=False)
        self.assertEqual(result.stdout,'')
        self.assertEqual(result.stderr.count('destroy local=10'),1)
        self.assertNotIn('99',result.stderr)

    def test_content_write_is_an_explicit_use_without_ending_owned_binding(self):
        functions='fn make(p:&mut Pool<Int>)-><-Int{let d=new(p)Int(10);return<-d;}fn value()->Int{return 20;}'
        for rhs in ('20','value()'):
            source=functions+'let mut p=pool<Int>(1);let mut n=make(&mut p);n='+rhs+';'
            result=self.execute(source,add_source=False)
            self.assertEqual(result.stdout,'')
            self.assertEqual(result.stderr.count('destroy d=20'),1)
            # An exclusive result used later still blocks the content write.
            self.reject(MUT+source.rsplit('n=',1)[0]+'let mut vue=borrow_mut(&mut n);n='+rhs+';vue.set(30);','emprunt')

    def test_independent_mutable_target_routes(self):
        # Oracle: leaf-index sets + concrete selector; no compiler contract reads.
        accepted=rejected=0
        for seed in range(24):
            rng=random.Random(seed);union=seed%4>=2;depth=rng.randrange(1,5)
            leaves={0,1} if union else {0};chosen=0
            functions=MUT+('fn base(a:&mut Int,b:&mut Int)->&mut Int{if true{return a;}return b;}' if union else '')
            previous='base' if union else 'borrow_mut';arity=2 if union else 1
            for level in range(depth):
                swap=rng.randrange(2);name=f'f{level}'
                args=('b,a' if swap else 'a,b') if arity==2 else ('b' if swap else 'a')
                functions+=f'fn {name}(a:&mut Int,b:&mut Int)->&mut Int{{return {previous}({args});}}'
                if swap:leaves={1-i for i in leaves};chosen=1-chosen
                previous=name;arity=2
            invalid=bool(seed%2);target=rng.choice(sorted(leaves)) if invalid or union else 1-next(iter(leaves))
            name='nombre' if target==0 else 'b';operation=f'print({name});'
            source=functions+SETUP+'let mut b=new(p)Int(7);'+f'let mut vue={previous}(&mut nombre,&mut b);'
            source+=('vue.set(30);'+operation if union and not invalid else operation+'vue.set(30);')
            source+='print(nombre);print(b);'
            with self.subTest(seed=seed):
                if invalid:self.reject(source,'emprunt');rejected+=1
                else:
                    # If union/valid, the read follows the write; otherwise it is unrelated.
                    first='30' if union and target==chosen else '10' if target==0 else '7'
                    expected=first+'\n'+('30\n7\n' if chosen==0 else '10\n30\n')
                    self.assertEqual(self.execute(source,add_source=False).stdout,expected);accepted+=1
        self.assertEqual((accepted,rejected),(12,12))

if __name__=='__main__':unittest.main()
