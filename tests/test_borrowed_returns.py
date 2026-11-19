"""Borrowed fields returned through verified child-to-parent boundaries."""
from functools import partial, update_wrapper
from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import Compiler, Parser, Error, verify_program, compile_program

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
compile_program = update_wrapper(partial(compile_program, allow_legacy_reset=True), compile_program)
from results import BorrowTarget
from results import ResultAnalyzer
from effects import EffectAnalyzer
import test_crust

DECL='enum View { Item { data: &Int }, Empty {} } '
MAKE=('fn make_view(views:&mut Pool<View>,data:&Int)-><-View { '
      'let mut view=new(views)View.Item{data:data};return<-view;} ')
SETUP='let mut p=pool<Int>(2);let mut q=pool<View>(2);let mut data=new(p)Int(42);'


class BorrowedReturnTests(unittest.TestCase):
    execute=test_crust.PrototypeTests.execute
    with_source=staticmethod(test_crust.PrototypeTests.with_source)

    def reject(self,source,pattern='emprunt|reset interdit|durable|survit|retour'):
        with self.assertRaisesRegex(Error,pattern):
            verify_program(source)

    def test_make_view_contract_records_input_identity(self):
        checked=verify_program(DECL+MAKE)
        summary=checked.function_results['make_view']
        self.assertEqual(dict(summary.borrowed_fields),{'Item.data':frozenset({BorrowTarget('parameter',1)})})
        self.assertEqual(summary.fresh_variants,{'Item'})

    def test_returned_shared_reborrow_suspends_then_restores_mutable_parent(self):
        prefix=DECL+MAKE+SETUP+'let mut loan=&mut data;let mut view=make_view(&mut q,loan);'
        result=self.execute(prefix+'print(view);loan.set(7);print(loan);',add_source=False)
        self.assertEqual(result.stdout,'View.Item(42)\n7\n')
        self.reject(prefix+'loan.set(7);print(view);','emprunt actif')
        mutable=MAKE.replace('data:&Int','data:&mut Int')
        result=self.execute(DECL+mutable+SETUP+'let mut view=make_view(&mut q,&mut data);print(view);data.set(7);',add_source=False)
        self.assertEqual(result.stdout,'View.Item(42)\n')

    def test_forwarded_holder_preserves_mutable_reborrow_parent(self):
        prefix=DECL+MAKE+'fn forward(mut v:->View)-><-View{return<-v;}'+SETUP
        prefix+='let mut loan=&mut data;let mut first=make_view(&mut q,loan);let mut view=forward(->first);'
        self.assertEqual(self.execute(prefix+'print(view);loan.set(7);print(loan);',add_source=False).stdout,
                         'View.Item(42)\n7\n')
        self.reject(prefix+'loan.set(7);print(view);','emprunt actif')

    def test_shared_child_does_not_authorize_unrelated_alias_of_original_handle(self):
        prefix=DECL+MAKE+SETUP+'let mut loan=&mut data;let mut view=make_view(&mut q,loan);'
        self.reject(prefix+'let mut alias=&data;print(view);print(alias);loan.set(7);','emprunt actif')
        declaration='fn both(q:&mut Pool<View>,a:&Int,b:&Int)-><-View{let mut v=make_view(q,b);return<-v;}'
        self.reject(DECL+MAKE+declaration+SETUP+'let mut loan=&mut data;'
                    'let mut view=both(&mut q,loan,&data);print(view);loan.set(7);','emprunt actif')

    def test_basic_return_uses_parent_target_and_keeps_address(self):
        source=DECL+MAKE+SETUP+'address(data);let mut view=make_view(&mut q,&data);'
        source+='match &view{View.Item{data:r}=>{address(r);print(r);},View.Empty{}=>{}}'
        result=self.execute(source,add_source=False)
        lines=result.stdout.splitlines()
        self.assertEqual(lines[0],lines[1])
        self.assertEqual(lines[2:],['42'])
        self.assertEqual([s for s in result.stderr.splitlines() if s.startswith('destroy ')],
                         ['destroy view=View.Item','destroy data=42'])

    def test_drop_mutation_and_move_before_returned_view_usage_rejected(self):
        prefix=DECL+MAKE+SETUP+'let mut view=make_view(&mut q,&data);'
        for action in ('drop(->data);','data.set(7);','let mut moved=<-data;','data=new(p)Int(7);','p.reset();'):
            with self.subTest(action=action):
                self.reject(prefix+action+'print(view);')

    def test_last_use_allows_drop_and_slot_reuse(self):
        result=self.execute(DECL+MAKE+SETUP+'let mut view=make_view(&mut q,&data);print(view);drop(->data);'
                            'let mut fresh=new(p)Int(7);print(fresh);',add_source=False)
        self.assertEqual(result.stdout,'View.Item(42)\n7\n')
        self.assertEqual(result.stderr.count('destroy data=42'),1)

    def test_last_use_allows_reset(self):
        result=self.execute(DECL+MAKE+SETUP+'let mut view=make_view(&mut q,&data);print(view);p.reset();',add_source=False)
        self.assertEqual(result.stdout,'View.Item(42)\n')
        self.assertEqual(result.stderr.count('destroy data=42'),1)

    def test_successive_function_returns_preserve_borrow(self):
        wrappers=('fn middle(p:&mut Pool<View>,d:&Int)-><-View{let mut v=make_view(p,d);return<-v;} '
                  'fn outer(d:&Int,p:&mut Pool<View>)-><-View{let mut v=middle(p,d);return<-v;} ')
        source=DECL+MAKE+wrappers+SETUP+'let mut view=outer(&data,&mut q);print(view);'
        checked=verify_program(source)
        self.assertEqual(dict(checked.function_results['outer'].borrowed_fields),
                         {'Item.data':frozenset({BorrowTarget('parameter',0)})})
        self.assertEqual(self.execute(source,add_source=False).stdout,'View.Item(42)\n')
        self.reject(source.replace('print(view);','drop(->data);print(view);'))

    def test_intermediate_local_target_fails_second_boundary(self):
        source=DECL+MAKE+('fn outer(p:&mut Pool<Int>,q:&mut Pool<View>)-><-View{'
            'let mut data=new(p)Int(42);let mut view=make_view(q,&data);return<-view;}')
        self.reject(source,'cible empruntée non durable')

    def test_owned_injected_int_is_not_a_parent_borrow(self):
        self.reject(DECL+'fn wrong(q:&mut Pool<View>,mut data:->Int)-><-View{'
                    'let mut view=new(q)View.Item{data:&data};return<-view;}','non durable')

    def test_result_inference_rejects_local_target_without_memory_backend(self):
        source=DECL+'fn wrong(p:&mut Pool<Int>,q:&mut Pool<View>)-><-View{'
        source+='let mut data=new(p)Int(42);let mut view=new(q)View.Item{data:&data};return<-view;}'
        nodes=Parser(source).parse()
        enums={node.args[0]:dict(node.args[1]) for node in nodes if node.op=='enum'}
        functions={node.args[0]:node for node in nodes if node.op=='fn'}
        effects=EffectAnalyzer(functions,enums,Error).infer_all()
        with self.assertRaisesRegex(Error,'non durable'):
            ResultAnalyzer(functions,effects,Error,enums).infer_all()

    def test_local_pool_does_not_make_local_target_durable(self):
        self.reject(DECL+'fn wrong(q:&mut Pool<View>)-><-View{let mut p=pool<Int>(1);'
                    'let mut data=new(p)Int(42);let mut v=new(q)View.Item{data:&data};return<-v;}','non durable')

    def test_local_holder_pool_still_cannot_escape(self):
        self.reject(DECL+'fn wrong(data:&Int)-><-View{let mut q=pool<View>(1);'
                    'let mut v=new(q)View.Item{data:data};return<-v;}','survit')

    def test_nested_block_can_transfer_holder_but_not_promote_local_target(self):
        source=DECL+MAKE+SETUP+'let mut view={let mut inner=make_view(&mut q,&data);<-inner};print(view);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'View.Item(42)\n')
        self.reject(DECL+MAKE+'let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut view={'
                    'let mut data=new(p)Int(42);let mut inner=make_view(&mut q,&data);<-inner};print(view);','non durable')

    def test_owned_holder_roundtrip_preserves_identity_and_dependencies(self):
        identity='fn forward(mut v:->View)-><-View{return<-v;} '
        source=DECL+MAKE+identity+SETUP+'let mut first=make_view(&mut q,&data);address(first);'
        source+='let mut second=forward(->first);address(second);print(second);'
        result=self.execute(source,add_source=False)
        lines=result.stdout.splitlines()
        self.assertEqual(lines[0],lines[1])
        self.assertEqual(lines[2:],['View.Item(42)'])
        self.reject(source.replace('print(second);','drop(->data);print(second);'))
        self.reject(source+'print(first);','plus utilisable')

    def test_plain_import_return_after_roundtrip_restores_only_holder(self):
        source=DECL+MAKE+'fn forward(mut v:->View)-><-View{return<-v;} '+SETUP
        source+='let mut view=make_view(&mut q,&data);{->view;view=forward(->view);<-view;}print(view);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'View.Item(42)\n')

    def test_conditional_return_protects_each_possible_target(self):
        choose=('fn choose(q:&mut Pool<View>,a:&Int,b:&Int,n:Int)-><-View{'
                'if n==0{let mut v=new(q)View.Item{data:a};return<-v;}'
                'let mut v=new(q)View.Item{data:b};return<-v;} ')
        for flag in (0,1):
            source=DECL+choose+SETUP+'let mut other=new(p)Int(7);'+f'let mut view=choose(&mut q,&data,&other,{flag});'
            self.assertEqual(self.execute(source+'print(view);',add_source=False).stdout,
                             'View.Item(42)\n' if flag==0 else 'View.Item(7)\n')
            for name in ('data','other'):
                self.reject(source+f'drop(->{name});print(view);')

    def test_conditional_expression_in_function_propagates_borrow_targets(self):
        source=DECL+('fn choose(q:&mut Pool<View>,a:&Int,b:&Int,n:Int)-><-View{'
            'let mut view=if n==0{let mut v=new(q)View.Item{data:a};<-v}'
            'else{let mut v=new(q)View.Item{data:b};<-v};return<-view;}')
        self.reject(source+SETUP+'let mut other=new(p)Int(7);let mut view=choose(&mut q,&data,&other,0);p.reset();print(view);')

    def test_empty_variant_and_forwarding_do_not_invent_borrow(self):
        source=DECL+('fn empty(q:&mut Pool<View>)-><-View{let mut v=new(q)View.Empty{};return<-v;}'
                     'fn forward(mut v:->View)-><-View{return<-v;}')+SETUP
        source+='let mut original=empty(&mut q);let mut view=forward(->original);drop(->data);print(view);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'View.Empty()\n')

    def test_empty_or_borrowed_variant_retains_conservative_dependency(self):
        source=DECL+('fn choose(q:&mut Pool<View>,d:&Int,n:Int)-><-View{'
            'if n==0{let mut v=new(q)View.Empty{};return<-v;}'
            'let mut v=new(q)View.Item{data:d};return<-v;}')+SETUP
        self.reject(source+'let mut view=choose(&mut q,&data,0);drop(->data);print(view);')

    def test_return_from_owned_holder_parameter_tracks_its_field_identity(self):
        # A new view references an Int injected separately; forwarding an owned
        # holder uses a field-parameter identity rather than its storage pool.
        checked=verify_program(DECL+'fn forward(mut v:->View)-><-View{return<-v;}')
        self.assertEqual(dict(checked.function_results['forward'].borrowed_fields),
                         {'Item.data':frozenset({BorrowTarget('field_parameter',0,'Item.data')})})

    def test_opaque_call_needs_no_body_or_inference_tables(self):
        interface=verify_program(DECL+MAKE)
        checker=Compiler(allow_legacy_reset=True);checker.contract_calls=True
        checker.enums,checker.function_contracts=interface.enums,interface.function_contracts
        nodes=Parser(SETUP+'let mut view=make_view(&mut q,&data);drop(->data);print(view);').parse()
        checker.index(nodes)
        with self.assertRaisesRegex(Error,'emprunt'):
            checker.block('root',nodes)
        self.assertEqual(checker.functions,{})
        self.assertEqual(checker.function_results,{})

    def test_nested_reset_preserves_read_before_reset_and_rejects_reset_before_read(self):
        read=('fn read_then_clear(p:&mut Pool<Int>,v:&View){print(v);p.reset();}')
        prefix=DECL+MAKE+read+SETUP+'let mut view=make_view(&mut q,&data);'
        self.assertEqual(self.execute(prefix+'read_then_clear(&mut p,&view);',add_source=False).stdout,'View.Item(42)\n')
        self.reject(prefix+'read_then_clear(&mut p,&view);print(view);')
        wrong='fn clear_then_read(p:&mut Pool<Int>,v:&View){p.reset();print(v);}'
        self.reject(DECL+MAKE+wrong+SETUP+'let mut view=make_view(&mut q,&data);clear_then_read(&mut p,&view);')

    def test_reset_of_holder_pool_ends_borrow_without_destroying_target(self):
        result=self.execute(DECL+MAKE+SETUP+'let mut view=make_view(&mut q,&data);print(view);q.reset();data.set(7);print(data);',add_source=False)
        self.assertEqual(result.stdout,'View.Item(42)\n7\n')
        self.assertEqual(result.stderr.count('destroy data=7'),1)

    def test_pending_returned_holder_protects_target_during_later_argument(self):
        funcs='fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;}fn consume(mut v:->View,n:Int){}'
        self.reject(DECL+MAKE+funcs+SETUP+'consume(->make_view(&mut q,&data),clear(&mut p));')

    def test_temporary_referent_argument_belongs_to_caller_scope(self):
        source=DECL+MAKE+'let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut view=make_view(&mut q,&new(p)Int(42));print(view);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'View.Item(42)\n')
        self.reject(source.replace('print(view);','p.reset();print(view);'))

    def test_discarding_old_view_during_reassignment_releases_old_dependency(self):
        source=DECL+MAKE+SETUP+'let mut other=new(p)Int(7);let mut view=make_view(&mut q,&data);print(view);'
        source+='view=make_view(&mut q,&other);drop(->data);print(view);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'View.Item(42)\nView.Item(7)\n')
        self.reject(source.replace('drop(->data);print(view);','drop(->data);drop(->other);print(view);'))

    def test_loop_future_usage_keeps_returned_dependency(self):
        prefix=DECL+MAKE+SETUP+'let mut view=make_view(&mut q,&data);'
        self.reject(prefix+'loop{print(view);p.reset();continue;}')
        self.execute(prefix+'loop{print(view);break;}p.reset();',add_source=False)

    def test_successive_nested_blocks_verify_each_parent_boundary(self):
        prefix=DECL+MAKE+SETUP
        source=prefix+'let mut view={let mut middle={let mut inner=make_view(&mut q,&data);<-inner};<-middle};print(view);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'View.Item(42)\n')
        self.reject(source.replace('print(view);','p.reset();print(view);'))

    def test_holder_pool_can_reset_before_fresh_view_is_returned(self):
        function='fn rebuild(q:&mut Pool<View>,d:&Int)-><-View{q.reset();let mut v=new(q)View.Item{data:d};return<-v;}'
        source=DECL+function+SETUP+'let mut old=new(q)View.Empty{};print(old);let mut view=rebuild(&mut q,&data);print(view);'
        result=self.execute(source,add_source=False)
        self.assertEqual(result.stdout,'View.Empty()\nView.Item(42)\n')
        self.assertEqual(result.stderr.count('destroy old=View.Empty'),1)

    def test_mixed_fresh_and_input_variants_resolve_only_possible_fields(self):
        declaration=('enum V{A{x:&Int},B{y:&Int},Empty{}}'
            'fn choose(q:&mut Pool<V>,d:&Int,mut v:->V,n:Int)-><-V{'
            'if n==0{let mut fresh=new(q)V.A{x:d};return<-fresh;}return<-v;}')
        for flag in (0,1):
            prefix=declaration+'let mut p=pool<Int>(2);let mut q=pool<V>(2);let mut x=new(p)Int(10);let mut y=new(p)Int(20);'
            source=prefix+f'let mut input=new(q)V.B{{y:&y}};let mut result=choose(&mut q,&x,->input,{flag});print(result);'
            self.assertEqual(self.execute(source,add_source=False).stdout,'V.A(10)\n' if flag==0 else 'V.B(20)\n')
        identity='fn forward(mut v:->V)-><-V{return<-v;}'
        source='enum V{A{x:&Int},B{y:&Int},Empty{}}'+identity
        source+='let mut p=pool<Int>(1);let mut q=pool<V>(1);let mut x=new(p)Int(10);let mut input=new(q)V.A{x:&x};'
        source+='let mut result=forward(->input);print(result);'
        self.assertEqual(self.execute(source,add_source=False).stdout,'V.A(10)\n')

    def test_independent_scope_route_model(self):
        # Model uses the level where the target was created and the destination
        # level, not storage lifetime or compiler summaries. No implicit promotion.
        valid=invalid=0
        for seed in range(24):
            rng=random.Random(seed)
            depth=rng.randrange(1,5)
            local=bool(seed%2)
            functions=[MAKE]
            for level in range(depth):
                child='make_view' if level==0 else f'f{level-1}'
                if level==depth-1 and local:
                    signature=f'fn f{level}(q:&mut Pool<View>,p:&mut Pool<Int>)-><-View'
                    body=f'let mut data=new(p)Int(42);let mut v={child}(q,&data);return<-v;'
                else:
                    signature=f'fn f{level}(q:&mut Pool<View>,data:&Int)-><-View'
                    body=f'let mut v={child}(q,data);return<-v;'
                functions.append(signature+'{'+body+'}')
            with self.subTest(seed=seed,depth=depth,local_target=local):
                source=DECL+' '.join(functions)
                # Local target is born at the last wrapper, so it cannot cross
                # that wrapper's boundary. External targets outlive all children.
                if local:
                    self.reject(source,'non durable')
                    invalid+=1
                else:
                    source+=SETUP+f'let mut view=f{depth-1}(&mut q,&data);print(view);'
                    self.assertEqual(self.execute(source,add_source=False).stdout,'View.Item(42)\n')
                    valid+=1
        self.assertEqual((valid,invalid),(12,12))


if __name__=='__main__':
    unittest.main()
