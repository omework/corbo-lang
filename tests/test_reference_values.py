"""Borrow creation and passing an existing reference have distinct syntax."""
from functools import partial, update_wrapper
from pathlib import Path
import sys
import unittest
sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Error, Parser, verify_program, compile_source

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
from effects import EffectAnalyzer
from results import ResultAnalyzer
import test_crust

READ='fn read(d:&Int)->Int{return *d;}'
IDENTITY='fn identity(d:&Int)->&Int{return d;}'
SETUP='let mut p=pool<Int>(2);let mut d=new(p)Int(42);'

class ReferenceValueTests(unittest.TestCase):
    execute=test_crust.PrototypeTests.execute
    with_source=staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self,source,pattern):
        for stage in (verify_program,compile_source):
            with self.subTest(stage=stage.__name__):
                with self.assertRaisesRegex(Error,pattern):stage(source)

    def test_create_borrow_from_owner_pass_existing_borrow_by_name(self):
        source=READ+SETUP+'let mut r=&d;let mut a=read(&d);let mut b=read(r);print(a);print(b);print(r);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'42\n42\n42\n')

    def test_nested_reference_is_not_flattened_at_call(self):
        for call,expression in (('read','&r'),('write','&mut r'),('read','&identity(&d)')):
            source=READ+IDENTITY+'fn write(d:&mut Int)->Int{return *d;}'+SETUP+'let mut r=&d;let mut n='+call+'('+expression+');print(n);'
            self.reject(source,'emprunt imbriqué')

    def test_nested_reference_is_not_flattened_in_unused_function(self):
        self.reject(READ+'fn bad(d:&Int){let mut n=read(&d);print(n);}','emprunt imbriqué')
        self.reject('fn bad(d:&Int)->&Int{return &d;}','emprunt imbriqué')
        self.reject('fn bad(d:&mut Int)->&Int{return &mut d;}','emprunt imbriqué')

    def test_nested_reference_is_rejected_by_result_inference_alone(self):
        nodes=Parser('fn bad(d:&Int)->&Int{return &d;}').parse()
        functions={n.args[0]:n for n in nodes}
        effects=EffectAnalyzer(functions,{},Error).infer_all()
        with self.assertRaisesRegex(Error,'emprunt imbriqué'):
            ResultAnalyzer(functions,effects,Error).infer_all()

    def test_named_owner_is_not_implicitly_borrowed_or_moved(self):
        self.reject(READ+SETUP+'let mut n=read(d);print(n);','emprunt explicite|mode attendu')
        self.reject('fn consume(mut d:->Int){}'+SETUP+'consume(d);','mode attendu')
        self.reject('fn bad(mut d:->Int)->&Int{return d;}','allocation|retour')

    def test_named_reference_cannot_be_used_as_scalar_or_owner(self):
        source='fn scalar(n:Int){}fn consume(mut d:->Int){}'+SETUP+'let mut r=&d;'
        self.reject(source+'scalar(r);','implicite|Int copiable')
        self.reject(source+'consume(->r);','allocation explicite|emprunt')

    def test_return_and_forward_reference_without_new_borrow(self):
        functions=IDENTITY+'fn relay(d:&Int)->&Int{let mut r=identity(d);return r;}'
        source=functions+READ+SETUP+'address(d);let mut r=relay(&d);address(r);let mut n=read(r);print(n);'
        result=self.execute(source,add_source=False);lines=result.stdout.splitlines()
        self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[2:],['42'])
        self.assertEqual(result.stderr.count('destroy d=42'),1)

    def test_nested_reference_call_result_is_passed_directly(self):
        source=IDENTITY+READ+SETUP+'let mut n=read(identity(identity(&d)));print(n);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'42\n')

    def test_drop_and_reset_still_protect_returned_named_reference(self):
        source=IDENTITY+SETUP+'let mut r=identity(&d);'
        for operation in ('drop(->d);','p.reset();'):
            self.reject(source+operation+'print(r);','emprunt|reset interdit')
        result=self.execute(source+'print(r);drop(->d);let mut fresh=new(p)Int(7);print(fresh);p.reset();',add_source=False)
        self.assertEqual(result.stdout,'42\n7\n')
        self.assertEqual(result.stderr.count('destroy d=42'),1)

    def test_named_mutable_parameter_remains_exclusive_during_calls(self):
        functions='fn edit(d:&mut Int){d.set(7);}fn relay(d:&mut Int){edit(d);print(d);}'
        self.assertEqual(self.execute(functions+SETUP+'let mut r=&mut d;relay(r);print(r);',add_source=False).stdout,'7\n7\n')
        self.reject('fn pair(a:&Int,b:&mut Int){}'+SETUP+'let mut r=&mut d;pair(r,r);','aliasés|emprunt')
        self.reject(functions+SETUP+'let mut r=&d;relay(r);','lecture|mutable')

    def test_shared_result_from_mutable_input_keeps_parent_protection(self):
        source=IDENTITY+SETUP+'let mut m=&mut d;let mut r=identity(m);'
        self.reject(source+'m.set(7);print(r);','emprunt')
        self.assertEqual(self.execute(source+'print(r);m.set(7);print(m);',add_source=False).stdout,'42\n7\n')

    def test_named_pool_parameter_is_forwarded_without_another_ampersand(self):
        functions='fn make(p:&mut Pool<Int>)-><-Int{let mut d=new(p)Int(42);return<-d;}'
        functions+='fn relay(p:&mut Pool<Int>)-><-Int{let mut d=make(p);return<-d;}'
        source=functions+'let mut p=pool<Int>(1);let mut d=relay(&mut p);print(d);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'42\n')
        self.reject(functions.replace('make(p)','make(&mut p)'),'emprunt imbriqué')
        self.reject(functions+'let mut p=pool<Int>(1);let mut d=relay(p);print(d);','emprunt explicite|mode attendu')

    def test_readonly_pool_cannot_gain_mutable_capability_by_name(self):
        self.reject('fn clear(p:&mut Pool<Int>){p.reset();}fn bad(p:&Pool<Int>){clear(p);}','mutable')

    def test_named_reference_keeps_prepared_argument_alive(self):
        source=IDENTITY+'fn pair(d:&Int,n:Int){print(d);}fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;}'
        self.reject(source+SETUP+'let mut r=identity(&d);pair(r,clear(&mut p));','reset interdit')
        self.reject(source+SETUP+'pair(identity(&d),clear(&mut p));','reset interdit')

    def test_named_field_initializer_preserves_the_same_target(self):
        prefix='enum V{Item{d:&Int}}fn make(p:&mut Pool<V>,d:&Int)-><-V{let mut v=new(p)V.Item{d:d};return<-v;}'
        setup=SETUP+'let mut q=pool<V>(1);let mut r=&d;let mut v=make(&mut q,r);'
        self.reject(prefix+setup+'drop(->d);print(v);','emprunt')
        self.assertEqual(self.execute(prefix+setup+'print(v);',add_source=False).stdout,'V.Item(42)\n')
        self.reject(prefix.replace('{d:d}','{d:&d}'),'emprunt imbriqué')

if __name__=='__main__':unittest.main()
