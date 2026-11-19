"""Owned-field effects cross synchronous task factories without running them."""
from pathlib import Path
import unittest

from async_structure_effects import AsyncStructureEffectAnalyzer
from crust import Parser, Error, verify_program, compile_source
from scheduler_faults import inject_submission_failure
import test_async_owned_field_writes as owned
import test_async_owned_borrow_writes as borrowed
import test_select_source as harness

FACTORY = '''fn prepare(root:&mut Root,p:&mut Pool<Int>,q:&mut Pool<Int>)-><-modify{
    return <-modify(root,p,q);}
fn again(q:&mut Pool<Int>,root:&mut Root,p:&mut Pool<Int>)-><-modify{
    return <-prepare(root,p,q);}
fn forward(t:->modify)-><-modify{return <-t;}
async fn relay(root:&mut Root,p:&mut Pool<Int>,q:&mut Pool<Int>)->Int{
    let t=forward(->again(q,root,p));return t.await;}'''
HELPERS = owned.TYPES + owned.MODIFY + FACTORY


class FactoryOwnedEffectTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused
    program = staticmethod(harness.SelectSourceTests.program)

    def test_contracts_keep_suspended_and_final_pool_without_sync_bodies(self):
        checked = verify_program(HELPERS)
        definitions = {node.args[0]: node for node in Parser(HELPERS).parse() if node.op == 'async_fn'}
        analyzer = AsyncStructureEffectAnalyzer(definitions, checked.function_contracts, checked.enums, Error)
        self.assertTrue(all(not node.args[3] for node in analyzer.results.functions.values()))
        effect = analyzer.infer('relay')
        self.assertTrue(effect.complete, effect.reason)
        self.assertTrue(effect.suspension_complete, effect.suspension_reason)
        factory = checked.function_results['prepare']
        for writes, index in ((factory.task_owned_updates, 2), (factory.task_suspension_owned, 1),
                              (effect.completion_result.owned_field_writes, 2),
                              (effect.suspension_result.owned_field_writes, 1)):
            self.assertEqual([(p, path, {(c.kind, c.source.kind, c.source.index) for c in child.candidates})
                              for p, path, child in writes],
                             [(0, '.item', {('fresh', 'source_parameter', index)})])

    def test_join_and_launch_failure_clean_original_and_reuse_slots(self):
        source = HELPERS + 'fn main(){' + owned.SETUP + '''
            let h=runtime::spawn(->prepare(&mut root,&mut p,&mut q));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
            print(read(&root));drop(->root);
            let a=first.new(20);let b=p.new(30);let c=q.new(40);print(a);print(b);print(c);}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout, '1\n11\n20\n30\n40\n')
        self.assertEqual(run.stderr.count('destroy old=7\n'), 1)
        failed = self.run_c_oracle(inject_submission_failure(compile_source(source), asynchronous=False, at=1))
        self.assertEqual(failed.stdout, '7\n20\n30\n40\n')
        self.assertEqual(failed.stderr.count('destroy old=7\n'), 1)

    def test_relay_await_and_inactive_drop(self):
        body = owned.SETUP + '''let n=relay(&mut root,&mut p,&mut q).await;
            print(n);print(read(&root));drop(->root);let fresh=q.new(40);return *fresh;'''
        self.assertEqual(self.run_source(self.program(body, HELPERS)).stdout, '1\n11\n40\n')
        inactive = owned.SETUP + '''let t=prepare(&mut root,&mut p,&mut q);
            yield;drop(->t);print(read(&root));drop(->root);let n=first.new(40);return *n;'''
        self.assertEqual(self.run_source(self.program(inactive, HELPERS)).stdout, '7\n40\n')

    def test_select_loser_keeps_intermediate_pool(self):
        recorded = Path(__file__).resolve().parents[1] / 'validation/open-factory-owned-suspension.crb'
        self.assertEqual(self.run_source(recorded.read_text()).stdout, '99\n9\n20\n30\n1\n')
        source = recorded.read_text().replace('->relay(&mut root,&mut p,&mut q)',
                                            '->prepare(&mut root,&mut p,&mut q)')
        self.assertEqual(self.run_source(source).stdout, '99\n9\n20\n30\n1\n')

    def test_final_pool_must_survive_receiver(self):
        body = owned.SETUP + '''{let mut short=pool<Int>(1);
            let n=relay(&mut root,&mut short,&mut q).await;print(n);}
            print(read(&root));drop(->root);return 1;'''
        self.assertEqual(self.run_source(self.program(body, HELPERS)).stdout, '1\n11\n1\n')
        self.refused(self.program(body.replace('relay(&mut root,&mut short,&mut q)',
                     'relay(&mut root,&mut p,&mut short)'), HELPERS), 'pool|source|survi|durée|dépend')
        direct = HELPERS + 'fn main(){' + owned.SETUP + '''{let mut short=pool<Int>(1);
            let h=runtime::spawn(->prepare(&mut root,&mut p,&mut short));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}
            print(read(&root));drop(->root);}'''
        self.refused(direct, 'pool|source|survi|durée|dépend')

    def test_replacement_retains_borrow_through_permuted_factory(self):
        factory = '''fn prepare(n:&Int,root:&mut Root,p:&mut Pool<Leaf>)-><-modify{
            return <-modify(root,p,n);}
            async fn relay(root:&mut Root,p:&mut Pool<Leaf>,n:&Int)->Int{
                return prepare(n,root,p).await;}
            async fn ready()->Int{return 99;}'''
        helpers = borrowed.TYPES + borrowed.MODIFY + factory
        body = borrowed.SETUP + '''let mut s=runtime::select(->relay(&mut root,&mut leaves,&next),->ready());
            let n=s.await;print(n);drop(->s);print(read(&root));drop(->root);
            drop(->next);let again=values.new(20);print(*again);return 1;'''
        source = self.program(body, helpers)
        self.assertEqual(self.run_source(source).stdout, '99\n9\n20\n1\n')
        self.refused(source.replace('print(read(&root));', 'drop(->next);print(read(&root));'),
                     'emprunt|référenc|réserv|utilisé')


if __name__ == '__main__':
    unittest.main()
