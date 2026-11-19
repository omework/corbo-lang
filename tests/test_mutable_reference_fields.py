"""Exclusive fields: containers retain capabilities, aliases do not duplicate them."""
from functools import partial, update_wrapper
from pathlib import Path
import random
import sys
import unittest
sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Compiler, Parser, Error, verify_program, compile_source

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
import test_crust

DECL='enum W{Bound{data:&mut Int}}'
SETUP='let mut p=pool<Int>(3);let mut q=pool<W>(3);let mut n=new(p)Int(10);'
HOLDER='let mut w=new(q)W.Bound{data:&mut n};'
MAKE='fn make(q:&mut Pool<W>,d:&mut Int)-><-W{let w=new(q)W.Bound{data:d};return<-w;}'
READ='fn read(w:&W){print(w);}'
MATCH='match &w{W.Bound{data:r}=>{print(r);}}'

class MutableReferenceFieldTests(unittest.TestCase):
    execute=test_crust.PrototypeTests.execute
    with_source=staticmethod(test_crust.PrototypeTests.with_source)
    def reject(self,source,pattern='emprunt|reset|durable|mutable|lecture|mode|immuable|champ|allocation|retour'):
        for stage in (verify_program,compile_source):
            with self.subTest(stage=stage.__name__):
                with self.assertRaisesRegex(Error,pattern):stage(source)
    def run_source(self,s):return self.execute(s,add_source=False)
    def test_last_use_restores_access_and_preserves_cleanup(self):
        r=self.run_source(DECL+SETUP+HOLDER+'print(w);n=30;print(n);')
        self.assertEqual(r.stdout,'W.Bound(10)\n30\n')
        self.assertEqual([x for x in r.stderr.splitlines() if x.startswith('destroy ')],['destroy w=W.Bound','destroy n=30'])
    def test_original_accesses_are_excluded(self):
        for op in ('print(n);','address(n);','n=20;','n.set(20);','drop(->n);','p.reset();','let m=<-n;','let r=&n;print(r);','let r=&mut n;print(r);'):
            self.reject(DECL+SETUP+HOLDER+op+'print(w);')
    def test_readonly_input_cannot_supply_mutable_field(self):
        self.reject(DECL+SETUP+'let r=&n;let w=new(q)W.Bound{data:r};print(w);')
        self.reject(DECL+'fn bad(q:&mut Pool<W>,d:&Int)-><-W{let w=new(q)W.Bound{data:d};return<-w;}')
    def test_container_reference_cannot_supply_int_field(self):
        # A capability descriptor must retain its real target type, not default Int.
        self.reject(DECL+SETUP+HOLDER+'let x=new(q)W.Bound{data:&mut w};print(x);')
        self.reject(DECL+'enum R{A{x:&Int}}'+SETUP+HOLDER+'let mut r=pool<R>(1);let x=new(r)R.A{x:&w};print(x);')
    def test_immutable_target_is_rejected(self):
        self.reject(DECL+SETUP.replace('let mut n=','let n=')+HOLDER+'print(w);')
    def test_parent_reference_resumes_after_holder(self):
        r=self.run_source(DECL+SETUP+'let m=&mut n;let w=new(q)W.Bound{data:m};print(w);m.set(30);print(m);')
        self.assertEqual(r.stdout,'W.Bound(10)\n30\n')
        self.reject(DECL+SETUP+'let m=&mut n;let w=new(q)W.Bound{data:m};m.set(30);print(w);')
    def test_multiple_readonly_container_aliases_retain_one_capability(self):
        r=self.run_source(DECL+SETUP+HOLDER+'let a=&w;let b=&w;print(a);print(b);n=30;print(n);')
        self.assertEqual(r.stdout,'W.Bound(10)\nW.Bound(10)\n30\n')
        for op in ('print(n);','n=20;','p.reset();','drop(->n);'):
            self.reject(DECL+SETUP+HOLDER+'let a=&w;let b=&w;'+op+'print(a);print(b);')
    def test_readonly_match_projection_retains_exclusivity(self):
        r=self.run_source(DECL+SETUP+HOLDER+MATCH+'n=30;print(n);')
        self.assertEqual(r.stdout,'10\n30\n')
        self.reject(DECL+SETUP+HOLDER+'match &w{W.Bound{data:r}=>{print(n);print(r);}}')
    def test_two_mutable_fields_cannot_alias(self):
        d='enum Pair{Both{a:&mut Int,b:&mut Int}}'
        s='let mut p=pool<Int>(1);let mut q=pool<Pair>(1);let mut n=new(p)Int(10);'
        self.reject(d+s+'let x=new(q)Pair.Both{a:&mut n,b:&mut n};print(x);')
    def test_mixed_shared_mutable_aliases_are_rejected_both_orders(self):
        for fields,values in [('a:&mut Int,b:&Int','a:&mut n,b:&n'),('a:&Int,b:&mut Int','a:&n,b:&mut n')]:
            self.reject(f'enum Pair{{Both{{{fields}}}}}let mut p=pool<Int>(1);let mut q=pool<Pair>(1);let mut n=new(p)Int(10);'+f'let x=new(q)Pair.Both{{{values}}};print(x);')
    def test_mixed_pointer_layout_and_identity(self):
        s='enum Mix{A{a:Int,x:&mut Int,b:Int,y:&Int,c:Int}}let mut p=pool<Int>(2);let mut q=pool<Mix>(1);let mut n=new(p)Int(10);let y=new(p)Int(20);address(n);let w=new(q)Mix.A{a:1,x:&mut n,b:2,y:&y,c:3};print(w);match &w{Mix.A{a:_,x:r,b:_,y:s,c:_}=>{address(r);print(r);print(s);}}n=30;'
        r=self.run_source(s);lines=r.stdout.splitlines()
        self.assertEqual(lines[0],lines[2]);self.assertEqual(lines[1],'Mix.A(1, 10, 2, 20, 3)');self.assertEqual(lines[3:],['10','20'])
    def test_drop_holder_then_reuse_slot(self):
        r=self.run_source(DECL+SETUP.replace('pool<W>(3)','pool<W>(1)')+HOLDER+'address(w);drop(->w);n=30;let z=new(q)W.Bound{data:&mut n};address(z);print(z);')
        lines=r.stdout.splitlines();self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[2],'W.Bound(30)')
        self.assertEqual(r.stderr.count('destroy w=W.Bound'),1);self.assertEqual(r.stderr.count('destroy z=W.Bound'),1)
    def test_reset_holder_releases_target(self):
        r=self.run_source(DECL+SETUP+HOLDER+'print(w);q.reset();n=30;print(n);p.reset();')
        self.assertEqual(r.stdout,'W.Bound(10)\n30\n');self.assertEqual(r.stderr.count('destroy w=W.Bound'),1)
    def test_moved_holder_retains_capability(self):
        self.reject(DECL+SETUP+HOLDER+'let z=<-w;print(n);print(z);')
        self.assertEqual(self.run_source(DECL+SETUP+HOLDER+'let z=<-w;print(z);n=30;print(n);').stdout,'W.Bound(10)\n30\n')
    def test_returned_holder_and_successive_calls(self):
        wrappers=MAKE+'fn forward(q:&mut Pool<W>,d:&mut Int)-><-W{let w=make(q,d);return<-w;}'
        s=DECL+READ+wrappers+SETUP+'let w=forward(&mut q,&mut n);read(&w);n=30;print(n);'
        self.assertEqual(self.run_source(s).stdout,'W.Bound(10)\n30\n')
        self.reject(s.replace('read(&w);n=30;','n=30;read(&w);'))
    def test_forward_owned_holder(self):
        f='fn pass(w:->W)-><-W{return<-w;}'
        s=DECL+f+SETUP+HOLDER+'let z=pass(->w);print(z);n=30;print(n);'
        self.assertEqual(self.run_source(s).stdout,'W.Bound(10)\n30\n')
        self.reject(s.replace('print(z);n=30;','n=30;print(z);'))
    def test_child_parent_transfer(self):
        s=DECL+SETUP+'let w={let z={let x=new(q)W.Bound{data:&mut n};<-x};<-z};print(w);n=30;print(n);'
        self.assertEqual(self.run_source(s).stdout,'W.Bound(10)\n30\n')
        self.reject(s.replace('print(w);n=30;','n=30;print(w);'))
    def test_local_target_not_promoted_even_with_durable_pool(self):
        self.reject(DECL+MAKE+'fn bad(q:&mut Pool<W>,p:&mut Pool<Int>)-><-W{let mut n=new(p)Int(10);let w=make(q,&mut n);return<-w;}')
        self.reject(DECL+SETUP+'print(n);let w={let mut a=new(p)Int(20);let w=new(q)W.Bound{data:&mut a};<-w};print(w);')
    def test_prepared_holder_argument_protects_target(self):
        funcs='fn pair(w:&W,n:&Int){print(w);print(n);}fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;}fn use(w:&W,n:Int){print(w);print(n);}'
        self.reject(DECL+funcs+SETUP+HOLDER+'pair(&w,&n);')
        self.reject(DECL+funcs+SETUP+HOLDER+'use(&w,clear(&mut p));')
        self.reject(DECL+'fn use(w:->W,n:Int){print(w);print(n);}fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;}'+SETUP+HOLDER+'use(->w,clear(&mut p));')
    def test_pending_initializer_protects_target(self):
        d='enum Mix{A{x:&mut Int,b:Int}}fn clear(p:&mut Pool<Int>)->Int{p.reset();return 1;}'
        self.reject(d+'let mut p=pool<Int>(1);let mut q=pool<Mix>(1);let mut n=new(p)Int(10);let w=new(q)Mix.A{x:&mut n,b:clear(&mut p)};print(w);')
    def test_replacement_releases_old_and_protects_new(self):
        s=DECL+SETUP+HOLDER+'print(w);let mut other=new(p)Int(20);w=new(q)W.Bound{data:&mut other};n=30;print(w);other=40;print(other);'
        self.assertEqual(self.run_source(s).stdout,'W.Bound(10)\nW.Bound(20)\n40\n')
        self.reject(s.replace('print(w);other=40;','other=40;print(w);'))
    def test_conditional_targets_all_protected(self):
        f='fn choose(q:&mut Pool<W>,k:Int,a:&mut Int,b:&mut Int)-><-W{if k==0{let w=new(q)W.Bound{data:a};return<-w;}let w=new(q)W.Bound{data:b};return<-w;}'
        for k in (0,1):
            s=DECL+f+SETUP+f'let mut b=new(p)Int(20);let w=choose(&mut q,{k},&mut n,&mut b);'
            self.assertEqual(self.run_source(s+'print(w);n=30;b=40;').stdout,f'W.Bound({10 if k==0 else 20})\n')
            for op in ('n=30;','b=40;','p.reset();'):self.reject(s+op+'print(w);')
    def test_loop_continue_cleanup_releases_capability(self):
        s=DECL+SETUP+'let mut i=0;while i<1{let w=new(q)W.Bound{data:&mut n};print(w);i=1;continue;}n=30;print(n);'
        r=self.run_source(s);self.assertEqual(r.stdout,'W.Bound(10)\n30\n');self.assertEqual(r.stderr.count('destroy w=W.Bound'),1)
    def test_shared_arguments_to_same_holder_are_allowed(self):
        f='fn pair(a:&W,b:&W){print(a);print(b);}'
        self.assertEqual(self.run_source(DECL+f+SETUP+HOLDER+'pair(&w,&w);n=30;').stdout,'W.Bound(10)\nW.Bound(10)\n')
    def test_opaque_contract_protects_field_without_body(self):
        interface=verify_program(DECL+'fn clear_read(p:&mut Pool<Int>,w:&W){p.reset();print(w);}')
        checker=Compiler(allow_legacy_reset=True);checker.enums=interface.enums;checker.function_contracts=interface.function_contracts;checker.contract_calls=True
        nodes=Parser(SETUP+HOLDER+'clear_read(&mut p,&w);').parse();checker.index(nodes)
        with self.assertRaisesRegex(Error,'reset interdit'):checker.block('root',nodes)
        self.assertEqual(checker.functions,{})
    def test_reset_after_read_inside_function_is_allowed(self):
        f='fn read_clear(p:&mut Pool<Int>,w:&W){print(w);p.reset();}'
        r=self.run_source(DECL+f+SETUP+HOLDER+'read_clear(&mut p,&w);')
        self.assertEqual(r.stdout,'W.Bound(10)\n');self.assertEqual(r.stderr.count('destroy n=10'),1)
    def test_conditional_variants_keep_strongest_capability(self):
        d='enum E{A{x:&mut Int},B{x:&Int}}fn choose(q:&mut Pool<E>,k:Int,n:&mut Int)-><-E{if k==0{let e=new(q)E.A{x:n};return<-e;}let e=new(q)E.B{x:n};return<-e;}'
        for k in (0,1):
            s=d+f'let mut p=pool<Int>(1);let mut q=pool<E>(1);let mut n=new(p)Int(10);let w=choose(&mut q,{k},&mut n);'
            self.assertEqual(self.run_source(s+'print(w);n=30;').stdout,f'E.{"A" if k==0 else "B"}(10)\n')
            self.reject(s+'print(n);print(w);')
    def test_returned_mutable_loan_can_supply_field(self):
        f='fn borrow_mut(n:&mut Int)->&mut Int{return n;}'
        s=DECL+f+SETUP+'let m=borrow_mut(&mut n);let w=new(q)W.Bound{data:m};print(w);m.set(30);print(m);'
        self.assertEqual(self.run_source(s).stdout,'W.Bound(10)\n30\n')
        self.reject(s.replace('print(w);m.set(30);','m.set(30);print(w);'))
    def test_independent_permission_model(self):
        # Expected permission uses a lifetime interval, independent of compiler contracts.
        rng=random.Random(381)
        accepted=rejected=0
        for seed in range(24):
            operation=rng.choice(('read','write','drop','reset'))
            holder_use_after=bool(seed%2)
            op={'read':'print(n);','write':'n=20;','drop':'drop(->n);','reset':'p.reset();'}[operation]
            s=DECL+SETUP+HOLDER+(op+'print(w);' if holder_use_after else 'print(w);'+op)
            allowed=not holder_use_after
            with self.subTest(seed=seed,operation=operation):
                if allowed:
                    r=self.run_source(s);self.assertIn('W.Bound(10)',r.stdout);accepted+=1
                else:self.reject(s);rejected+=1
        self.assertEqual((accepted,rejected),(12,12))

if __name__=='__main__':unittest.main()
