"""Direct readonly borrowed returns; target lifetimes never move with a pointer."""
from functools import partial, update_wrapper
from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Compiler, Parser, Error, compile_source, compile_program, verify_program

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
from effects import EffectAnalyzer
from results import ResultAnalyzer, BorrowTarget
import test_crust

BORROW='fn borrow(data:&Int)->&Int{return data;} '
CHOOSE='fn choose(n:Int,a:&Int,b:&Int)->&Int{if n==0{return a;}return b;} '
SETUP='let mut p=pool<Int>(3);let mut data=new(p)Int(42);'
VIEW='enum View{Item{data:&Int}} fn make(q:&mut Pool<View>,d:&Int)-><-View{let mut v=new(q)View.Item{data:d};return<-v;}'

class DirectBorrowReturnTests(unittest.TestCase):
    execute=test_crust.PrototypeTests.execute
    with_source=staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self, source, pattern='emprunt|reset interdit|durable|retour|allocation|mode attendu'):
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__):
                with self.assertRaisesRegex(Error,pattern):stage(source)

    def test_contract_records_target_without_owned_candidate(self):
        c=verify_program(BORROW)
        r=c.function_results['borrow']
        self.assertEqual(r.mode,'ref')
        self.assertFalse(r.candidates)
        self.assertEqual(r.reference_targets,{BorrowTarget('parameter',0)})
        self.assertEqual(r.describe(c.function_contracts['borrow'].parameters)['reference_targets'],
                         [{'kind':'parameter','parameter':'data'}])

    def test_direct_result_preserves_address_and_single_cleanup(self):
        r=self.execute(BORROW+SETUP+'address(data);let mut r=borrow(&data);address(r);print(r);',add_source=False)
        lines=r.stdout.splitlines()
        self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[2:],['42'])
        self.assertEqual([l for l in r.stderr.splitlines() if l.startswith('destroy ')],['destroy data=42'])

    def test_no_extra_allocation_or_cleanup_registration(self):
        c,_=compile_program(BORROW+SETUP+'let mut r=borrow(&data);print(r);')
        self.assertEqual(len(c.allocations),1)
        generated=compile_source(BORROW+SETUP+'let mut r=borrow(&data);print(r);')
        main=generated[generated.index('int main(void)'):]
        self.assertEqual(main.count('cell_new('),1);self.assertEqual(main.count('cell_drop('),1)

    def test_local_target_rejected_by_result_inference_alone(self):
        for body in ('let mut d=new(p)Int(1);return &d;',
                     'let mut d=new(p)Int(1);let mut r=borrow(&d);return r;',
                     'return borrow(&new(p)Int(1));'):
            source=BORROW+'fn bad(p:&mut Pool<Int>)->&Int{'+body+'}'
            nodes=Parser(source).parse();functions={n.args[0]:n for n in nodes}
            effects=EffectAnalyzer(functions,{},Error).infer_all()
            with self.assertRaisesRegex(Error,'durable'):ResultAnalyzer(functions,effects,Error).infer_all()
            self.reject(source,'durable')

    def test_owned_parameter_cannot_be_borrowed_out(self):
        self.reject('fn bad(mut d:->Int)->&Int{return &d;}','durable')
        self.reject(BORROW+'fn bad(mut d:->Int)->&Int{return borrow(&d);}','durable')

    def test_successive_calls_substitute_targets(self):
        source=BORROW+'fn middle(d:&Int)->&Int{let mut r=borrow(d);return r;}'
        source+='fn outer(unused:Int,d:&Int)->&Int{return middle(d);}'
        checked=verify_program(source)
        self.assertEqual(checked.function_results['outer'].reference_targets,{BorrowTarget('parameter',1)})
        prefix=source+SETUP+'let mut r=outer(0,&data);'
        self.assertEqual(self.execute(prefix+'print(r);',add_source=False).stdout,'42\n')
        for action in ('drop(->data);','p.reset();','data.set(7);','let mut moved=<-data;','data=new(p)Int(7);'):
            self.reject(prefix+action+'print(r);')

    def test_parent_and_ancestor_targets_survive_nested_return_boundaries(self):
        source='fn nested(d:&Int)->&Int{{{return d;}}}'
        self.assertEqual(self.execute(source+SETUP+'{let mut r=nested(&data);print(r);}',add_source=False).stdout,'42\n')

    def test_last_use_allows_drop_and_pool_slot_reuse(self):
        source=BORROW+'let mut p=pool<Int>(1);let mut data=new(p)Int(42);address(data);'
        source+='let mut r=borrow(&data);print(r);drop(->data);let mut fresh=new(p)Int(7);address(fresh);print(fresh);'
        r=self.execute(source,add_source=False);lines=r.stdout.splitlines()
        self.assertEqual(lines[0],lines[2]);self.assertEqual([lines[1],lines[3]],['42','7'])
        self.assertEqual(r.stderr.count('destroy data=42'),1);self.assertEqual(r.stderr.count('destroy fresh=7'),1)

    def test_last_use_allows_reset_and_new_identity(self):
        source=BORROW+'let mut p=pool<Int>(1);let mut data=new(p)Int(42);let mut r=borrow(&data);print(r);p.reset();'
        source+='let mut fresh=new(p)Int(7);print(fresh);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'42\n7\n')
        self.reject(source+'print(r);')

    def test_conditional_result_protects_every_possible_target(self):
        prefix=CHOOSE+SETUP+'let mut b=new(p)Int(7);let mut r=choose(0,&data,&b);'
        self.assertEqual(self.execute(prefix+'print(r);',add_source=False).stdout,'42\n')
        for name in ('data','b'):
            self.reject(prefix+f'drop(->{name});print(r);')
            self.reject(prefix+f'{name}.set(9);print(r);')
        self.reject(prefix+'p.reset();print(r);')

    def test_different_pools_protect_each_source_then_allow_reset(self):
        prefix=CHOOSE+SETUP+'let mut q=pool<Int>(1);let mut b=new(q)Int(7);let mut r=choose(1,&data,&b);'
        for pool in ('p','q'):self.reject(prefix+pool+'.reset();print(r);')
        self.assertEqual(self.execute(prefix+'print(r);p.reset();q.reset();',add_source=False).stdout,'7\n')

    def test_conditional_wrapper_keeps_both_targets(self):
        source=CHOOSE+'fn wrap(a:&Int,b:&Int)->&Int{let mut r=choose(0,b,a);return r;}'
        checked=verify_program(source)
        self.assertEqual(checked.function_results['wrap'].reference_targets,
                         {BorrowTarget('parameter',0),BorrowTarget('parameter',1)})
        self.reject(source+SETUP+'let mut b=new(p)Int(7);let mut r=wrap(&data,&b);drop(->b);print(r);')

    def test_mutable_parent_suspended_until_last_returned_ref_use(self):
        prefix=BORROW+SETUP+'let mut m=&mut data;let mut r=borrow(m);'
        self.assertEqual(self.execute(prefix+'print(r);m.set(7);print(m);',add_source=False).stdout,'42\n7\n')
        self.reject(prefix+'m.set(7);print(r);','emprunt actif')
        self.reject(prefix+'let mut alias=&data;print(r);print(alias);m.set(7);','emprunt actif')

    def test_return_from_mutable_parameter_is_readonly(self):
        source='fn shared(d:&mut Int)->&Int{return d;}'
        prefix=source+SETUP+'let mut r=shared(&mut data);'
        self.reject(prefix+'r.set(7);','lecture')
        self.assertEqual(self.execute(prefix+'print(r);data.set(7);print(data);',add_source=False).stdout,'42\n7\n')

    def test_conditional_mutable_parents_resume_after_last_use(self):
        prefix=CHOOSE+SETUP+'let mut b=new(p)Int(7);let mut ma=&mut data;let mut mb=&mut b;let mut r=choose(0,ma,mb);'
        self.assertEqual(self.execute(prefix+'print(r);ma.set(8);mb.set(9);print(ma);print(mb);',add_source=False).stdout,'42\n8\n9\n')
        self.reject(prefix+'mb.set(9);print(r);')

    def test_nested_argument_and_deref(self):
        source=BORROW+'fn read(d:&Int)->Int{return *d;}'+SETUP
        source+='let mut x=read(borrow(&data));print(x);let mut r=borrow(borrow(&data));let mut y=*r;print(y);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'42\n42\n')

    def test_prepared_union_borrow_blocks_mutable_alias_in_next_argument(self):
        fn='fn both(a:&Int,b:&mut Int){print(a);b.set(9);}'
        source=CHOOSE+fn+SETUP+'let mut b=new(p)Int(7);let mut r=choose(1,&data,&b);both(r,&mut b);'
        self.reject(source,'aliasés|emprunt')
        self.reject(source.replace('let mut r=choose(1,&data,&b);','').replace('both(r,&mut b)','both(choose(1,&data,&b),&mut b)'),'aliasés|emprunt')

    def test_prepared_union_borrow_blocks_reset_in_next_argument(self):
        source=CHOOSE+'fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;}fn read(d:&Int,n:Int){print(d);}'
        source+=SETUP+'let mut q=pool<Int>(1);let mut b=new(q)Int(7);let mut r=choose(1,&data,&b);read(r,clear(&mut q));'
        self.reject(source,'reset interdit')

    def test_returned_ref_stored_in_holder_protects_all_targets(self):
        prefix=CHOOSE+VIEW+SETUP+'let mut q=pool<View>(1);let mut b=new(p)Int(7);let mut r=choose(1,&data,&b);'
        for construct in ('let mut v=new(q)View.Item{data:r};','let mut v=make(&mut q,r);'):
            self.assertEqual(self.execute(prefix+construct+'print(v);',add_source=False).stdout,'View.Item(7)\n')
            for target in ('data','b'):self.reject(prefix+construct+f'drop(->{target});print(v);')

    def test_reset_in_wrapper_uses_original_target_history(self):
        source=BORROW+'fn bad(p:&mut Pool<Int>,d:&Int)->&Int{let mut r=borrow(d);p.reset();return r;}'
        self.reject(source+SETUP+'let mut r=bad(&mut p,&data);print(r);','reset interdit')
        source=BORROW+'fn valid(p:&mut Pool<Int>,d:&Int)->&Int{p.reset();return d;}'
        self.assertEqual(self.execute(source+SETUP+'let mut q=pool<Int>(1);let mut r=valid(&mut q,&data);print(r);',add_source=False).stdout,'42\n')

    def test_reset_in_conditional_branch_protects_caller_alias(self):
        source=BORROW+'fn stop(p:&mut Pool<Int>,n:Int){if n==0{p.reset();}}'+SETUP
        self.reject(source+'let mut r=borrow(&data);stop(&mut p,1);print(r);','reset interdit')

    def test_reference_reassignment_does_not_destroy_either_target(self):
        source=BORROW+SETUP+'let mut b=new(p)Int(7);let mut r=borrow(&data);print(r);r=borrow(&b);drop(->data);print(r);'
        r=self.execute(source,add_source=False)
        self.assertEqual(r.stdout,'42\n7\n');self.assertEqual(r.stderr.count('destroy data=42'),1)
        self.assertEqual(r.stderr.count('destroy b=7'),1)

    def test_loop_cleanup_does_not_destroy_borrowed_parent_target(self):
        source=BORROW+SETUP+'let mut n=new(p)Int(0);while *n<2{let mut r=borrow(&data);print(r);n.set(2);continue;}print(data);'
        r=self.execute(source,add_source=False);self.assertEqual(r.stdout,'42\n42\n')
        self.assertEqual(r.stderr.count('destroy data=42'),1)

    def test_owned_and_mutable_escalation_rejected(self):
        prefix=BORROW+SETUP+'let mut r=borrow(&data);'
        for suffix in ('drop(->r);','let mut moved=<-r;','fn_noop(->r);'):
            self.reject('fn fn_noop(mut d:->Int){}'+prefix+suffix)
        self.reject('fn mutate(d:&mut Int){d.set(1);}'+prefix+'mutate(r);','lecture|mutable')

    def test_opaque_application_reads_no_callee_body(self):
        class OpaqueBody:
            def __iter__(self):raise AssertionError('callee body read during contract application')
        checked=verify_program(BORROW)
        old=checked.functions['borrow'];checked.functions['borrow']=replace(old,args=(*old.args[:3],OpaqueBody()))
        # The standalone public checker has already checked the body once.
        with patch.object(Compiler,'block',side_effect=AssertionError('body replay')):
            from crust import Scope,MemorySource,Allocation,Binding,Node
            root=Scope(100,'caller',None);p=MemorySource(101,100,'pool','p','p','Int')
            a=Allocation(102,100,'data',(p,),c='data');b=Binding('data','owned','data',a,last=100)
            root.bindings['data']=b;root.allocations=[a];checked.scopes=[root];checked.allocations=[a]
            checked.contract_calls=True
            expr=('call','borrow',[('ref','data')]);checked.index([Node('call',(expr,),1)])
            result=checked.invoke(expr,root)
        self.assertIs(result[2].reference_targets[0],a)

    def test_wrong_direct_contract_is_detected_by_specialized_backend(self):
        source=CHOOSE+SETUP+'let mut b=new(p)Int(7);let mut r=choose(0,&data,&b);print(r);'
        original=ResultAnalyzer.infer_all
        def corrupt(analyzer):
            summaries=original(analyzer)
            summaries['choose']=replace(summaries['choose'],reference_targets=frozenset({BorrowTarget('parameter',1)}))
            return summaries
        with patch.object(ResultAnalyzer,'infer_all',corrupt):
            with self.assertRaisesRegex(Error,'absente du contrat'):compile_source(source)

    def test_independent_generated_target_sets(self):
        # Oracle: mathematical union of leaf input indices, independent of compiler summaries.
        # Each seed uses a permuted call chain; invalid action precedes the final reference read.
        for seed in range(24):
            rng=random.Random(seed);depth=rng.randrange(1,5);union=seed%4>=2
            selected={0,1} if union else {0}
            runtime_choice=0
            declarations=BORROW+('fn pick(a:&Int,b:&Int)->&Int{if true{return a;}return b;}' if union else '')
            previous='pick' if union else 'borrow';arity=2 if union else 1
            for level in range(depth):
                swap=rng.randrange(2);name=f'f{level}'
                if swap:
                    declarations+=f'fn {name}(a:&Int,b:&Int)->&Int{{return {previous}(b'+(',a' if arity==2 else '')+');}'
                    selected={1-i for i in selected}
                    runtime_choice=1-runtime_choice
                else:
                    declarations+=f'fn {name}(a:&Int,b:&Int)->&Int{{return {previous}(a'+(',b' if arity==2 else '')+');}'
                previous=name;arity=2
            chosen=min(selected);invalid=seed%2==1
            # Runtime chooses the first arm; symbolic oracle retains both arms, including `if true`.
            destroy=rng.choice(sorted(selected)) if invalid or union else 1-chosen
            action='drop(->'+('data' if destroy==0 else 'b')+');'
            source=declarations+SETUP+'let mut b=new(p)Int(7);'+f'let mut r={previous}(&data,&b);'
            source+=('print(r);'+action if union and not invalid else action+'print(r);')
            with self.subTest(seed=seed):
                if invalid:self.reject(source)
                else:
                    self.assertEqual(self.execute(source,add_source=False).stdout,'42\n' if runtime_choice==0 else '7\n')

if __name__=='__main__':unittest.main()
