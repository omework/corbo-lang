"""Returning an input preserves its identity and its updated owned graph."""
from pathlib import Path
import unittest

from crust import compile_source, verify_program
from scheduler_faults import inject_submission_failure
import test_select_source as harness

ROOT = Path(__file__).resolve().parents[1]
# Preserve the historical fixture while making its pool return explicit.
BASE = (ROOT / 'validation/open-async-return-replaced-owned-field.crb').read_text().replace(
    '-> <-Holder', '-> <-A<Holder>')
HELPERS = BASE[:BASE.index('fn main')]
SETUP = '''let mut old_values=pool<Int>(1);let mut new_values=pool<Int>(1);
    let mut holders=pool<Holder>(1);let value=old_values.new(7);
    let holder=holders.new(value:<-value);'''


class ReturnedOwnedReplacementTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused
    program = staticmethod(harness.SelectSourceTests.program)

    def test_recorded_join_preserves_root_address_and_drops_both_children(self):
        source = BASE.replace('let execution =', 'address(holder);let execution =').replace(
            'print(*h.value);', 'address(h);print(*h.value);')
        run = self.run_source(source)
        before, after, value = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual(value, '11')
        self.assertEqual(run.stderr.count('destroy value=7\n'), 1)
        self.assertEqual(run.stderr.count('destroy champ=11\n'), 1)
        self.assertEqual(run.stderr.count('destroy holder=Holder\n'), 1)
        failed = self.run_c_oracle(inject_submission_failure(compile_source(BASE), asynchronous=False, at=1))
        self.assertEqual(failed.stdout, '')
        self.assertEqual(failed.stderr.count('destroy value=7\n'), 1)
        self.assertNotIn('=11\n', failed.stderr)

    def test_synchronous_result_contract_and_slot_reuse(self):
        source = HELPERS + 'fn main(){' + SETUP + '''address(holder);
            let h=replace_field(->holder,&mut new_values);address(h);print(*h.value);
            let a=old_values.new(20);print(a);drop(->h);
            let b=new_values.new(30);let again=holders.new(value:<-b);print(*again.value);drop(->again);}'''
        run = self.run_source(source)
        before, after, *values = run.stdout.splitlines()
        self.assertEqual(before, after)
        self.assertEqual(values, ['11', '20', '30'])
        result = verify_program(source).function_results['replace_field']
        self.assertEqual(result.same_parameter, 0)
        child = dict(result.owned_fields)['.value']
        self.assertEqual({(c.kind, c.source.kind, c.source.index) for c in child.candidates},
                         {('fresh', 'source_parameter', 1)})
        self.refused(source.replace('address(h);', 'print(holder);address(h);'),
                     'utilisable|transfér|consomm|invalide')

    def test_direct_await_and_relay_keep_new_pool(self):
        helpers = HELPERS.replace('async fn work(', 'async fn replace_async(') + '''
            async fn relay(h:->Holder,p:&mut Pool<Int>)-><-A<Holder>{
                let result=replace_async(->h,p).await;yield;return <-result;}'''
        body = SETUP + '''let h=relay(->holder,&mut new_values).await;print(*h.value);
            let a=old_values.new(20);print(*a);drop(->h);
            let b=new_values.new(30);return *b;'''
        self.assertEqual(self.run_source(self.program(body, helpers)).stdout, '11\n20\n30\n')

    def test_returned_child_cannot_outlive_replacement_pool(self):
        for await_source in (False, True):
            invocation = ('work(->holder,&mut short).await' if await_source else
                          'replace_field(->holder,&mut short)')
            body = SETUP + '''let h={holder ->;let mut short=pool<Int>(1);
                let result=CALL;<-result};print(*h.value);drop(->h);return 1;'''.replace('CALL', invocation)
            if await_source:
                source = self.program(body.replace('work(->holder', 'inner(->holder'),
                                      HELPERS.replace('async fn work(', 'async fn inner('))
            else:
                source = HELPERS + 'fn main(){' + body.replace('return 1;', '') + '}'
            self.refused(source, 'pool|source|survi|durée|dépend')

    def test_unchanged_owned_sibling_survives_restitution(self):
        source = BASE.replace('value: A<Int> }', 'value: A<Int>, other:A<Int> }').replace(
            'let holder = holders.new(value: <-value);',
            'let mut siblings=pool<Int>(1);let other=siblings.new(13);'
            'let holder = holders.new(value: <-value,other:<-other);').replace(
            'print(*h.value);', 'print(*h.value);print(*h.other);')
        run = self.run_source(source)
        self.assertEqual(run.stdout, '11\n13\n')
        self.assertEqual(run.stderr.count('destroy other=13\n'), 1)

    def test_returned_replacement_keeps_contained_borrow(self):
        source = '''struct Leaf{view:&Int}struct Root{item:A<Leaf>}
            fn replace(mut root:->Root,p:&mut Pool<Leaf>,n:&Int)-><-A<Root>{
                root.item=<-p.new(view:n);return <-root;}
            async fn work(root:->Root,p:&mut Pool<Leaf>,n:&Int)-><-A<Root>{
                yield;return <-replace(->root,p,n);}
            fn main(){let mut values=pool<Int>(2);let old=values.new(7);let next=values.new(9);
                let mut leaves=pool<Leaf>(2);let leaf=leaves.new(view:&old);
                let mut roots=pool<Root>(1);let root=roots.new(item:<-leaf);
                let h=runtime::spawn(->work(->root,&mut leaves,&next));
                match h.join(){Ok(r)=>{let view=&*r.item;print(*view.view);drop(->r);},Err(_)=>{}}
                drop(->next);let again=values.new(20);print(*again);}'''
        self.assertEqual(self.run_source(source).stdout, '9\n20\n')
        self.refused(source.replace('let view=&*r.item;', 'drop(->next);let view=&*r.item;'),
                     'emprunt|référenc|utilis|réserv')


if __name__ == '__main__':
    unittest.main()
