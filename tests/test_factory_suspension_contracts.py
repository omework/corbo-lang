"""A synchronous task factory preserves prefixes separately from completion."""
from pathlib import Path
import unittest

from async_structure_effects import AsyncStructureEffectAnalyzer
from crust import Error, Parser, verify_program
import test_select_source as harness


ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / 'validation/open-factory-suspended-field.crb'


class FactorySuspensionContractTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def infer(self, source, name='relay'):
        checked = verify_program(source)
        definitions = {node.args[0]: node for node in Parser(source).parse() if node.op == 'async_fn'}
        analyzer = AsyncStructureEffectAnalyzer(definitions, checked.function_contracts, checked.enums, Error)
        self.assertTrue(all(not node.args[3] for node in analyzer.results.functions.values()))
        effect = analyzer.infer(name)
        self.assertTrue(effect.complete, effect.reason)
        self.assertTrue(effect.suspension_complete, effect.suspension_reason)
        return checked, effect

    @staticmethod
    def fields(result):
        return {index: {field: {(t.kind, t.parameter, t.field) for t in targets}
                        for field, targets in fields} for index, fields in result.structure_fields}

    def test_recorded_select_loser_keeps_suspended_write(self):
        source = RECORDED.read_text()
        self.assertEqual(self.run_source(source).stdout, '99\n9\n1\n')
        self.refused(source.replace('print(*v.data);', 'drop(->b);print(*v.data);'),
                     'emprunt|référenc|réserv')
        checked, effect = self.infer(source)
        self.assertEqual(self.fields(effect.suspension_result), {0: {'.data': {('parameter', 1, '')}}})
        self.assertEqual(self.fields(effect.completion_result),
                         {0: {'.data': {('detached_field_parameter', 0, '.data')}}})
        factory = checked.function_results['prepare']
        self.assertTrue(factory.task_may_suspend)
        self.assertEqual(dict(dict(factory.task_suspension_fields)[0])['.data'],
                         dict(dict(effect.suspension_result.structure_fields)[0])['.data'])

    def test_normal_completion_restores_and_inactive_drop_does_not_write(self):
        source = RECORDED.read_text()
        start = source.index('let mut s=runtime::select')
        end = source.index('return 1;}', start) + len('return 1;')
        direct = source[:start] + ' let n=relay(&mut v,&b).await;print(n);drop(->b);print(*v.data);return 1;' + source[end:]
        self.assertEqual(self.run_source(direct).stdout, '7\n7\n1\n')
        self.refused(direct.replace('drop(->b);', 'drop(->a);'), 'emprunt|référenc|réserv')
        inactive = source.replace('let t=prepare(v,n);return t.await;',
                                  'let t=prepare(v,n);yield;drop(->t);return 1;')
        self.assertEqual(self.run_source(inactive).stdout, '99\n7\n1\n')
        _, effect = self.infer(inactive)
        self.assertEqual(self.fields(effect.suspension_result), {})
        self.assertEqual(self.fields(effect.completion_result), {})

    def test_nested_factory_permutation_and_task_forwarding(self):
        source = RECORDED.read_text().replace('async fn relay', '''
            fn permute(n:&Int,v:&mut View)-><-leaf{return <-prepare(v,n);}
            fn forward(t:->leaf)-><-leaf{return <-t;}
            async fn relay''')
        source = source.replace('let t=prepare(v,n);return t.await;',
                                'let t=forward(->permute(n,v));return t.await;')
        self.assertEqual(self.run_source(source).stdout, '99\n9\n1\n')
        _, effect = self.infer(source)
        self.assertEqual(self.fields(effect.suspension_result), {0: {'.data': {('parameter', 1, '')}}})
        self.refused(source.replace('print(*v.data);', 'drop(->b);print(*v.data);'),
                     'emprunt|référenc|réserv')

    def test_factory_as_select_branch_publishes_prefix_to_caller(self):
        source = RECORDED.read_text().replace(
            'async fn relay(v:&mut View,n:&Int)->Int{let t=prepare(v,n);return t.await;}', '''
            async fn relay(v:&mut View,n:&Int)->Int{
                let mut s=runtime::select(->prepare(v,n),->ready());
                let r=s.await;drop(->s);return r;}''').replace(
            'let mut s=runtime::select(->relay(&mut v,&b),->ready());let n=s.await;print(n);drop(->s);',
            'let n=relay(&mut v,&b).await;print(n);')
        self.assertEqual(self.run_source(source).stdout, '99\n9\n1\n')
        _, effect = self.infer(source)
        self.assertFalse(effect.may_suspend)
        # may_suspend does not promise a yield before every completion. The
        # contract conservatively retains the leaf's restored completion too.
        self.assertEqual(self.fields(effect.completion_result),
                         {0: {'.data': {('parameter', 1, ''), ('detached_field_parameter', 0, '.data')}}})
        self.refused(source.replace('print(*v.data);', 'drop(->b);print(*v.data);'),
                     'emprunt|référenc|réserv')

    def test_conditional_factory_preserves_both_captures(self):
        source = RECORDED.read_text().replace(
            'async fn relay(v:&mut View,n:&Int)->Int{let t=prepare(v,n);return t.await;}', '''
            fn choose(v:&mut View,a:&Int,b:&Int,flag:Int)-><-leaf{
                if flag==0{return <-prepare(v,a);}return <-prepare(v,b);}
            async fn relay(v:&mut View,a:&Int,b:&Int,flag:Int)->Int{
                let t=choose(v,a,b,flag);return t.await;}''')
        source = source.replace('pool<Int>(2)', 'pool<Int>(3)').replace(
            'let b=p.new(9);', 'let b=p.new(9);let c=p.new(11);').replace(
            'relay(&mut v,&b)', 'relay(&mut v,&b,&c,FLAG)')
        for flag, expected in (('0', 9), ('1', 11)):
            case = source.replace('FLAG', flag)
            self.assertEqual(self.run_source(case).stdout, f'99\n{expected}\n1\n')
        _, effect = self.infer(source.replace('FLAG', '0'))
        self.assertEqual(self.fields(effect.suspension_result),
                         {0: {'.data': {('parameter', 1, ''), ('parameter', 2, '')}}})
        for target in ('b', 'c'):
            self.refused(source.replace('FLAG', '0').replace('print(*v.data);',
                         f'drop(->{target});print(*v.data);'), 'emprunt|référenc|réserv')
        # The same choice in the async caller merges task descriptors before
        # awaiting; those prefixes are alternatives, never sequential stores.
        source = source.replace('let t=choose(v,a,b,flag);',
            'let t=if flag==0{let t=prepare(v,a);<-t}else{let t=prepare(v,b);<-t};')
        _, effect = self.infer(source.replace('FLAG', '0'))
        self.assertEqual(self.fields(effect.suspension_result),
                         {0: {'.data': {('parameter', 1, ''), ('parameter', 2, '')}}})
        for flag, expected in (('0', 9), ('1', 11)):
            self.assertEqual(self.run_source(source.replace('FLAG', flag)).stdout, f'99\n{expected}\n1\n')


if __name__ == '__main__':
    unittest.main()
