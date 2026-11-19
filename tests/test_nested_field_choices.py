"""Alternative borrowed descendants retain every possible old/new target."""
from pathlib import Path
import unittest
from crust import verify_program
import test_select_source as sources

ROOT=Path(__file__).resolve().parents[1]

class NestedFieldChoiceTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused

    def source(self):
        return (ROOT/'validation/open-nested-field-choice.crb').read_text()

    def test_recorded_choice_and_both_possible_targets(self):
        source=self.source()
        self.assertEqual(self.run_source(source).stdout,'1\n')
        fields=dict(verify_program(source).function_results['change_outer'].structure_fields[0][1])
        self.assertEqual(set(fields),{'.inner/.view','.other/.view'})
        for path,targets in fields.items():
            self.assertEqual({(t.kind,t.parameter,t.field) for t in targets},
                {('parameter',1,''),('field_parameter',0,path)})
        for target in ('first','second'):
            self.refused(source.replace('drop(->'+target+');','').replace('    let result = task.await;',
                '    drop(->'+target+');let result=task.await;'),'emprunt|réserv|référenc')

    def test_runtime_updates_only_selected_child(self):
        source=self.source().replace('async fn consume', 'fn read(value:&Inner)->Int{return *value.view;}\nasync fn consume')
        source=source.replace('yield; drop(->value); return 1;',
            'yield;print(read(&*value.inner));print(read(&*value.other));drop(->value);return 1;')
        for condition,expected in (('1==1','9\n7\n1\n'),('1==2','7\n9\n1\n')):
            self.assertEqual(self.run_source(source.replace('if 1==1', 'if '+condition)).stdout,expected)

    def test_identical_projection_is_definite(self):
        source=self.source().replace('struct Outer{inner:A<Inner>,other:A<Inner>}', 'struct Outer{inner:A<Inner>}')
        source=source.replace('&mut *value.other','&mut *value.inner')
        source=source.replace('let other=inners.new(view:&first);let mut outer=Outer{inner:<-inner,other:<-other};',
            'let mut outer=Outer{inner:<-inner};')
        source=source.replace('drop(->first);drop(->second);','drop(->second);').replace('    let task =',
            '    drop(->first);let task =')
        self.assertEqual(self.run_source(source).stdout,'1\n')

    def test_loop_result_keeps_each_projection(self):
        source=self.source().replace('if 1==1 {&mut *value.inner}else{&mut *value.other}',
            'loop{if 1==1{break &mut *value.inner;}break &mut *value.other;}')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        for target in ('first','second'):
            self.refused(source.replace('drop(->'+target+');','').replace('    let result = task.await;',
                '    drop(->'+target+');let result=task.await;'),'emprunt|réserv|référenc')

    def test_successive_writes_through_selected_alias(self):
        source=self.source().replace('change(child,target);','change(child,target);change(child,target);')
        self.assertEqual(self.run_source(source).stdout,'1\n')

    def test_mixed_whole_object_and_descendant(self):
        source=self.source().replace('fn change_outer(value:&mut Outer,target:&Int)',
            'fn change_outer(value:&mut Outer,outside:&mut Inner,target:&Int)')
        source=source.replace('else{&mut *value.other}', 'else{outside}')
        source=source.replace('pool<Inner>(2)','pool<Inner>(3)').replace('    change_outer(&mut outer,&second);',
            '    let mut outside=inners.new(view:&first);change_outer(&mut outer,&mut outside,&second);')
        source=source.replace('    drop(->first);drop(->second);','    drop(->outside);drop(->first);drop(->second);')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('drop(->outside);drop(->first);drop(->second);',
            'drop(->second);drop(->outside);drop(->first);'),'emprunt|réserv|référenc')

    def test_mutable_target_choice(self):
        source=self.source().replace('view: &Int','view: &mut Int').replace('target: &Int','target: &mut Int').replace('target:&Int','target:&mut Int')
        source=source.replace('value.view = &*target','value.view = &mut *target').replace('let first =','let mut first =').replace('let second =','let mut second =')
        # Distinct initial targets are necessary for the two mutable fields.
        source=source.replace('pool<Int>(2)','pool<Int>(3)').replace('let other=inners.new(view:&first);',
            'let mut third=numbers.new(11);let other=inners.new(view:&mut third);')
        source=source.replace('view: &first','view: &mut first').replace('outer,&second','outer,&mut second')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('    let result = task.await;', 'print(*second);let result=task.await;'),'emprunt|réserv|référenc')

    def test_recorded_sync_counterexample(self):
        source=(ROOT/'validation/counterexample-choice-sync-first.crb').read_text()
        self.refused(source,'emprunt|réserv|référenc')

    def test_project_another_level_after_the_choice(self):
        source=self.source().replace('struct Outer{inner:A<Inner>,other:A<Inner>}',
            'struct Middle{child:A<Inner>}struct Outer{inner:A<Middle>,other:A<Middle>}')
        source=source.replace('change(child,target);','change(&mut *child.child,target);')
        source=source.replace('let other=inners.new(view:&first);let mut outer=Outer{inner:<-inner,other:<-other};',
            'let other=inners.new(view:&first);let mut mids=pool<Middle>(2);'
            'let left=mids.new(child:<-inner);let right=mids.new(child:<-other);'
            'let mut outer=Outer{inner:<-left,other:<-right};')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('drop(->second);','').replace('    let result = task.await;',
            '    drop(->second);let result=task.await;'),'emprunt|réserv|référenc')

    def test_independent_possible_location_model(self):
        base=self.source().replace('pool<Int>(2)','pool<Int>(3)').replace('let other=inners.new(view:&first);',
            'let third=numbers.new(11);let other=inners.new(view:&third);')
        base=base.replace('drop(->first);drop(->second);','')
        for same in (False,True):
            reachable={'second','third'} | (set() if same else {'first'})
            source=base.replace('&mut *value.other','&mut *value.inner') if same else base
            for waited in (False,True):
                for target in ('first','second','third'):
                    action='drop(->'+target+');'
                    program=source.replace('    let result = task.await;',
                        ('let result=task.await;'+action) if waited else (action+'let result=task.await;'))
                    with self.subTest(same=same,waited=waited,target=target):
                        if not waited and target in reachable:
                            self.refused(program,'emprunt|réserv|référenc')
                        else:
                            self.assertEqual(self.run_source(program).stdout,'1\n')

    def test_sync_caller_uses_conditional_contract(self):
        source=self.source().replace('async fn work() -> Int','fn work() -> Int').replace('    let result = task.await;',
            '    let h=runtime::spawn(->task);let result=match h.join(){Ok(n)=>{n},Err(_)=>{99}};')
        source=source[:source.index('fn main()')]+'fn main(){print(work());}'
        self.assertEqual(self.run_source(source).stdout,'1\n')
        for target in ('first','second'):
            self.refused(source.replace('drop(->'+target+');','').replace('    let h=runtime::spawn',
                '    drop(->'+target+');let h=runtime::spawn'),'emprunt|réserv|référenc')

if __name__=='__main__':unittest.main()
