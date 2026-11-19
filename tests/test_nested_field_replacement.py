"""Changes to a descendant preserve its new targets through async transfers."""
from pathlib import Path
import unittest
from crust import verify_program, compile_source
import test_select_source as sources
from scheduler_faults import inject_submission_failure

ROOT=Path(__file__).resolve().parents[1]

class NestedFieldReplacementTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused

    def source(self):
        return (ROOT/'validation/open-nested-field-replacement.crb').read_text()

    def test_recorded_transfer_releases_only_old_target(self):
        source=self.source()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'1\n')
        self.assertLess(run.stderr.index('destroy first=7'),run.stderr.index('destroy inner=Inner'))
        self.assertLess(run.stderr.index('destroy inner=Inner'),run.stderr.index('destroy second=9'))
        invalid=source.replace('    drop(->second);','').replace('    let result = task.await;','    drop(->second);let result = task.await;')
        self.refused(invalid,'emprunt|réserv|référenc')

    def test_alias_then_child_read_observes_new_target(self):
        source=self.source().replace('async fn consume', 'fn read(value:&Inner)->Int{return *value.view;}\nasync fn consume')
        source=source.replace('yield; drop(->value); return 1;', 'yield;let n=read(&*value.inner);drop(->value);return n;')
        for call in ('change(&mut *outer.inner, &second);',
                     'let mut child=&mut *outer.inner;change(child,&second);'):
            current=source.replace('change(&mut *outer.inner, &second);',call)
            self.assertEqual(self.run_source(current).stdout,'9\n')
            self.refused(current.replace('    drop(->second);','').replace('    let task =','    drop(->second);let task ='),'emprunt|réserv|référenc')

    def test_whole_return_retains_new_target(self):
        source=self.source().replace('async fn consume(value: -> Outer) -> Int { yield; drop(->value); return 1; }',
            'async fn consume(value:->Outer)-><-Outer{yield;return <-value;}')
        source=source.replace('    drop(->second);\n    return result;', '    drop(->result);drop(->second);return 1;')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('drop(->result);drop(->second);','drop(->second);drop(->result);'),'emprunt|réserv|référenc')

    def test_conditional_replacement_retains_both_targets(self):
        source=self.source().replace('value.view = &*target;', 'if 1==1{value.view = &*target;}')
        source=source.replace('    drop(->first);','').replace('    drop(->second);','    drop(->first);drop(->second);')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        for name in ('first','second'):
            self.refused(source.replace('drop(->'+name+');','').replace('    let result = task.await;',
                '    drop(->'+name+');let result = task.await;'),'emprunt|réserv|référenc')

    def test_mutable_field_replacement_keeps_exclusivity(self):
        source=self.source().replace('view: &Int','view: &mut Int').replace('target: &Int','target: &mut Int')
        source=source.replace('value.view = &*target','value.view = &mut *target').replace('let first =','let mut first =').replace('let second =','let mut second =')
        source=source.replace('view: &first','view: &mut first').replace('outer.inner, &second','outer.inner, &mut second')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        for operation in ('print(*second);','second=12;'):
            self.refused(source.replace('    let result = task.await;',operation+'let result = task.await;'),'emprunt|réserv|référenc')

    def test_two_children_do_not_share_field_metadata(self):
        source=self.source().replace('struct Outer { inner: A<Inner> }','struct Outer { inner: A<Inner>, other: A<Inner> }')
        source=source.replace('pool<Inner>(1)','pool<Inner>(2)').replace('    let mut outer = Outer { inner: <-inner };',
            '    let other=inners.new(view:&first);let mut outer=Outer{inner:<-inner,other:<-other};')
        source=source.replace('    drop(->first);','').replace('    drop(->second);','    drop(->first);drop(->second);')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        for name in ('first','second'):
            self.refused(source.replace('drop(->'+name+');','').replace('    let result = task.await;',
                '    drop(->'+name+');let result = task.await;'),'emprunt|réserv|référenc')

    def test_two_owned_levels_through_aliases(self):
        source=self.source().replace('struct Outer { inner: A<Inner> }',
            'struct Middle{inner:A<Inner>}struct Outer{middle:A<Middle>}')
        source=source.replace('    let mut outer = Outer { inner: <-inner };',
            '    let mut ms=pool<Middle>(1);let middle=ms.new(inner:<-inner);let mut outer=Outer{middle:<-middle};')
        source=source.replace('change(&mut *outer.inner, &second);',
            'let mut mid=&mut *outer.middle;let mut child=&mut *mid.inner;change(child,&second);')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('    drop(->second);','').replace('    let result = task.await;',
            '    drop(->second);let result = task.await;'),'emprunt|réserv|référenc')

    def test_async_changes_owned_graph_and_returns_it(self):
        source=self.source().replace('async fn consume(value: -> Outer) -> Int { yield; drop(->value); return 1; }',
            'async fn consume(mut value:->Outer,target:&Int)-><-Outer{change(&mut *value.inner,target);yield;return <-value;}')
        source=source.replace('fn make(value: -> Outer) -> <-consume { return <-consume(->value); }',
            'fn make(value:->Outer,target:&Int)-><-consume{return <-consume(->value,target);}')
        source=source.replace('    change(&mut *outer.inner, &second);','').replace('make(->outer)','make(->outer,&second)')
        source=source.replace('    drop(->first);','').replace('    drop(->second);\n    return result;',
            '    drop(->first);drop(->result);drop(->second);return 1;')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('drop(->result);drop(->second);','drop(->second);drop(->result);'),'emprunt|réserv|référenc')

    def test_short_new_target_cannot_escape(self):
        source=self.source().replace('    let second = numbers.new(9);','')
        source=source.replace('    change(&mut *outer.inner, &second);',
            '    {let second=numbers.new(9);change(&mut *outer.inner,&second);}')
        source=source.replace('    drop(->second);','')
        self.refused(source,'emprunt|réserv|référenc|survi|durée')

    def test_launched_failure_cleans_new_target_capture(self):
        source=self.source().replace('    let result = task.await;',
            '    let h=runtime::spawn(->task);let result=match h.await{Ok(n)=>{n},Err(_)=>{99}};')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        run=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=True,at=1))
        self.assertEqual(run.stdout,'99\n')
        self.assertEqual(run.stderr.count('=Inner\n'),1)
        self.assertEqual(run.stderr.count('=Outer\n'),1)

    def test_independent_target_set_model(self):
        # Two distinct owned edges. Replacing the left edge changes its
        # reachable set, never the right edge; completion removes both edges.
        source=self.source().replace('struct Outer { inner: A<Inner> }','struct Outer{inner:A<Inner>,other:A<Inner>}')
        source=source.replace('pool<Int>(2)','pool<Int>(3)').replace('pool<Inner>(1)','pool<Inner>(2)')
        source=source.replace('    let mut outer = Outer { inner: <-inner };',
            '    let third=numbers.new(11);let other=inners.new(view:&third);let mut outer=Outer{inner:<-inner,other:<-other};')
        source=source.replace('    drop(->first);','').replace('    drop(->second);','')
        for conditional in (False,True):
            reachable={'second','third'} | ({'first'} if conditional else set())
            current=source.replace('value.view = &*target;', 'if 1==1{value.view = &*target;}') if conditional else source
            for waited in (False,True):
                for target in ('first','second','third'):
                    action='drop(->'+target+');'
                    program=current.replace('    let result = task.await;',
                        ('let result=task.await;'+action) if waited else (action+'let result=task.await;'))
                    with self.subTest(conditional=conditional,waited=waited,target=target):
                        if not waited and target in reachable:
                            self.refused(program,'emprunt|réserv|référenc')
                        else:
                            self.assertEqual(self.run_source(program).stdout,'1\n')

if __name__=='__main__':unittest.main()
