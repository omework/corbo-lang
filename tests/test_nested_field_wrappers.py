"""Projected field updates cross contracts borrowing the whole owned graph."""
from pathlib import Path
import unittest
from crust import verify_program,compile_source
import test_select_source as sources
from scheduler_faults import inject_submission_failure
from test_nested_field_replacement import NestedFieldReplacementTests

ROOT=Path(__file__).resolve().parents[1]

class NestedFieldWrapperTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    test_independent_target_set_model=NestedFieldReplacementTests.test_independent_target_set_model

    def source(self):
        return (ROOT/'validation/open-nested-field-wrapper.crb').read_text()

    def test_recorded_wrapper_contract(self):
        source=self.source()
        self.assertEqual(self.run_source(source).stdout,'1\n')
        summary=verify_program(source).function_results['change_outer']
        self.assertEqual(summary.structure_fields[0][0],0)
        self.assertEqual(summary.structure_fields[0][1][0][0],'.inner/.view')
        self.assertEqual({(t.kind,t.parameter) for t in summary.structure_fields[0][1][0][1]}, {('parameter',1)})
        self.refused(source.replace('    drop(->second);','').replace('    let result = task.await;',
            '    drop(->second);let result=task.await;'),'emprunt|réserv|référenc')

    def test_recorded_conditional_counterexample(self):
        source=(ROOT/'validation/counterexample-nested-field-wrapper-conditional.crb').read_text()
        self.refused(source,'emprunt|réserv|référenc')

    def test_read_updated_child_then_update_its_sibling(self):
        source=(ROOT/'validation/open-nested-field-read-after-write.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('    drop(->second);','').replace('    let result = task.await;',
            '    drop(->second);let result=task.await;'),'emprunt|réserv|référenc')

    def test_two_relays_and_named_parent_loan(self):
        source=self.source().replace('async fn consume',
            'fn relay(value:&mut Outer,target:&Int){change_outer(value,target);}\nasync fn consume')
        for call in ('relay(&mut outer,&second);','let mut parent=&mut outer;relay(parent,&second);'):
            current=source.replace('change_outer(&mut outer,&second);',call)
            self.assertEqual(self.run_source(current).stdout,'1\n')
            self.refused(current.replace('    drop(->second);','').replace('    let task =',
                '    drop(->second);let task ='),'emprunt|réserv|référenc')

    def test_conditional_contract_keeps_old_and_new(self):
        source=self.source().replace('value.view = &*target;', 'if 1==1{value.view = &*target;}')
        source=source.replace('    drop(->first);','').replace('    drop(->second);','    drop(->first);drop(->second);')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        for name in ('first','second'):
            self.refused(source.replace('drop(->'+name+');','').replace('    let result = task.await;',
                '    drop(->'+name+');let result=task.await;'),'emprunt|réserv|référenc')

    def test_borrow_from_another_descendant(self):
        source=self.source().replace('struct Outer { inner: A<Inner> }','struct Outer{inner:A<Inner>,other:A<Inner>}')
        source=source.replace('fn change_outer(value:&mut Outer,target:&Int){change(&mut *value.inner,target);}',
            'fn change_outer(value:&mut Outer,target:&Inner){change(&mut *value.inner,target.view);}')
        source=source.replace('pool<Inner>(1)','pool<Inner>(3)').replace('    let mut outer = Outer { inner: <-inner };',
            '    let other=inners.new(view:&first);let donor=inners.new(view:&second);let mut outer=Outer{inner:<-inner,other:<-other};')
        source=source.replace('change_outer(&mut outer,&second);','change_outer(&mut outer,&donor);drop(->donor);')
        source=source.replace('    drop(->first);','').replace('    drop(->second);','    drop(->first);drop(->second);')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        for name in ('first','second'):
            self.refused(source.replace('drop(->'+name+');','').replace('    let result = task.await;',
                '    drop(->'+name+');let result=task.await;'),'emprunt|réserv|référenc')

    def test_sync_caller_and_conditional_old_target(self):
        source=self.source().replace('async fn work() -> Int','fn work() -> Int').replace('    let result = task.await;',
            '    let h=runtime::spawn(->task);let result=match h.join(){Ok(n)=>{n},Err(_)=>{99}};')
        source=source[:source.index('fn main()')]+'fn main(){print(work());}'
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('    drop(->second);','').replace('    let h=runtime::spawn',
            '    drop(->second);let h=runtime::spawn'),'emprunt|réserv|référenc')

    def test_mutable_target_and_last_use(self):
        source=self.source().replace('view: &Int','view: &mut Int').replace('target: &Int','target: &mut Int').replace('target:&Int','target:&mut Int')
        source=source.replace('value.view = &*target','value.view = &mut *target').replace('let first =','let mut first =').replace('let second =','let mut second =')
        source=source.replace('view: &first','view: &mut first').replace('outer,&second','outer,&mut second')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('    let result = task.await;', 'print(*second);let result=task.await;'),'emprunt|réserv|référenc')

    def test_launch_failure_after_wrapper_and_pool_reuse(self):
        source=self.source().replace('    let result = task.await;',
            '    let h=runtime::spawn(->task);let result=match h.await{Ok(n)=>{n},Err(_)=>{99}};')
        source=source.replace('    return result;', '    let reuse=inners.new(view:&first);drop(->reuse);return result;')
        # Reusing the slot also requires a live target for the new occupant.
        source=source.replace('view:&first);drop(->reuse)', 'view:&second);drop(->reuse)').replace('    drop(->second);','')
        self.assertEqual(self.run_source(source).stdout,'1\n')
        run=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=True,at=1))
        self.assertEqual(run.stdout,'99\n')
        self.assertEqual(run.stderr.count('=Inner\n'),2)

if __name__=='__main__':unittest.main()
