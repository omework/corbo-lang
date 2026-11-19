"""Suspended prefixes are not normal exits or effects of inactive creation."""
from itertools import product
import unittest

from async_structure_effects import AsyncStructureEffectAnalyzer
from crust import Error, Parser, compile_source, verify_program
from test_async_structure_effects import BASE
import test_suspended_cleanup


class SuspensionEffectsTests(unittest.TestCase):
    native = test_suspended_cleanup.SuspendedCleanupTests.native
    run_c_oracle = test_suspended_cleanup.SuspendedCleanupTests.run_c_oracle

    @classmethod
    def setUpClass(cls):
        cls.baseline = verify_program(BASE)

    def infer(self, source, name='work'):
        definitions = {node.args[0]: node for node in Parser(source).parse() if node.op == 'async_fn'}
        analyzer = AsyncStructureEffectAnalyzer(definitions, self.baseline.function_contracts,
                                                self.baseline.enums, Error)
        self.assertTrue(all(not node.args[3] for node in analyzer.results.functions.values()))
        summary = analyzer.infer(name)
        self.assertTrue(summary.complete, summary.reason)
        return summary

    def fields(self, result):
        self.assertIsNotNone(result)
        return {index: {field: {(t.kind, t.parameter, t.field) for t in targets}
                        for field, targets in fields} for index, fields in result.structure_fields}

    def test_restoration_is_completion_only(self):
        source = '''async fn work(v:&mut View,n:&Int)->Int {
            let old=v.data;v.data=&*n;yield;v.data=old;return 7;}'''
        summary = self.infer(source)
        self.assertTrue(summary.may_suspend)
        self.assertEqual(self.fields(summary.suspension_result), {0: {'.data': {('parameter',1,'')}}})
        self.assertEqual(self.fields(summary.completion_result),
                         {0: {'.data': {('detached_field_parameter',0,'.data')}}})
        # Restoring before yielding must not retain an unobservable intermediate store.
        summary = self.infer(source.replace('yield;v.data=old;', 'v.data=old;yield;'))
        self.assertEqual(self.fields(summary.suspension_result), self.fields(summary.completion_result))
        summary = self.infer(source.replace('yield;', ''))
        self.assertFalse(summary.may_suspend)
        self.assertEqual(self.fields(summary.suspension_result), {})

    def test_inactive_child_has_no_prefix_effect(self):
        source = '''async fn child(v:&mut View,n:&Int)->Int{change(v,n);yield;return 1;}
        async fn work(v:&mut View,n:&Int)->Int{let t=child(v,n);yield;drop(->t);return 0;}'''
        summary = self.infer(source)
        self.assertTrue(summary.may_suspend)
        self.assertEqual(self.fields(summary.suspension_result), {})
        self.assertEqual(self.fields(summary.completion_result), {})

    def test_completed_child_is_observed_only_at_parent_suspension(self):
        child = 'async fn child(v:&mut View,n:&Int)->Int{change(v,n);return 1;}'
        for pause in ('', 'yield;'):
            with self.subTest(pause=pause):
                summary = self.infer(child + '''async fn work(v:&mut View,n:&Int)->Int{
                    let result=child(v,n).await;'''+pause+'return result;}')
                self.assertEqual(summary.may_suspend, bool(pause))
                expected = {0:{'.data':{('parameter',1,'')}}}
                self.assertEqual(self.fields(summary.completion_result), expected)
                self.assertEqual(self.fields(summary.suspension_result), expected if pause else {})

    def test_suspended_rhs_precedes_field_assignment(self):
        summary = self.infer('''async fn delayed(n:&Int)->&Int{yield;return n;}
        async fn work(v:&mut View,n:&Int)->Int{
            v.data=delayed(n).await;return 0;}''')
        self.assertTrue(summary.may_suspend)
        self.assertEqual(self.fields(summary.suspension_result), {})
        self.assertEqual(self.fields(summary.completion_result), {0:{'.data':{('parameter',1,'')}}})

    def test_conditional_task_captures_preserve_each_suspended_target(self):
        summary = self.infer('''async fn child(v:&mut View,n:&Int)->Int{
            let old=v.data;change(v,n);yield;v.data=old;return 1;}
        async fn work(v:&mut View,a:&Int,b:&Int,flag:Bool)->Int{
            let t=if flag{let t=child(v,a);<-t}else{let t=child(v,b);<-t};
            return t.await;}''')
        self.assertEqual(self.fields(summary.suspension_result),
                         {0:{'.data':{('parameter',1,''),('parameter',2,'')}}})
        self.assertEqual(self.fields(summary.completion_result),
                         {0:{'.data':{('detached_field_parameter',0,'.data')}}})

    def test_child_prefix_survives_permutation_alias_and_shadow(self):
        source = '''async fn leaf(v:&mut View,n:&Int)->Int{
            let old=v.data;change(v,n);yield;v.data=old;return 1;}
        async fn relay(n:&Int,v:&mut View)->Int{return leaf(v,n).await;}
        async fn work(v:&mut View,a:&Int,b:&Int)->Int{
            let mut alias=&mut *v;let t=relay(a,alias);
            {let a=b;print(*a);let n=t.await;print(n);}return 0;}'''
        summary = self.infer(source)
        self.assertEqual(self.fields(summary.suspension_result), {0: {'.data': {('parameter',1,'')}}})
        self.assertEqual(self.fields(summary.completion_result),
                         {0: {'.data': {('detached_field_parameter',0,'.data')}}})

    def test_noncompleting_child_still_contributes_suspended_states(self):
        source = '''async fn child(v:&mut View,n:&Int)->Int{change(v,n);loop{yield;}}
        async fn work(v:&mut View,a:&Int,b:&Int,flag:Bool)->Int{
            if flag{return child(v,a).await;}change(v,b);return 1;}'''
        summary = self.infer(source)
        self.assertEqual(self.fields(summary.suspension_result), {0: {'.data': {('parameter',1,'')}}})
        self.assertEqual(self.fields(summary.completion_result), {0: {'.data': {('parameter',2,'')}}})
        child = self.infer(source, 'child')
        self.assertFalse(child.may_complete)
        self.assertTrue(child.may_suspend)

    def test_branch_without_write_contributes_unchanged_target(self):
        summary = self.infer('''async fn work(v:&mut View,n:&Int,flag:Bool)->Int{
            if flag{change(v,n);yield;}else{yield;}return 0;}''')
        self.assertEqual(self.fields(summary.suspension_result),
                         {0:{'.data':{('parameter',1,''),('field_parameter',0,'.data')}}})

    def test_mutable_field_prefix_and_returned_capability_are_distinct(self):
        baseline = verify_program('struct Writer{data:&mut Int}')
        source = '''async fn child(v:&mut Writer,n:&mut Int)->&mut Int{
            v.data=&mut *n;yield;return &mut *v.data;}
        async fn work(v:&mut Writer,n:&mut Int)->&mut Int{
            let mut r=child(v,n).await;yield;return r;}'''
        definitions = {node.args[0]:node for node in Parser(source).parse()}
        summary = AsyncStructureEffectAnalyzer(definitions, baseline.function_contracts,
                                                baseline.enums, Error).infer('work')
        self.assertTrue(summary.complete, summary.reason)
        self.assertTrue(summary.may_suspend)
        self.assertEqual(self.fields(summary.suspension_result), {0:{'.data':{('parameter',1,'')}}})
        self.assertFalse(summary.suspension_result.reference_targets)
        self.assertTrue(summary.completion_result.reference_targets)

    def test_normal_completion_keeps_precise_drop_checks(self):
        source = '''struct View{data:&Int}
        async fn child(v:&mut View,n:&Int)->Int{
            let old=v.data;v.data=&*n;yield;v.data=old;return 7;}
        async fn work(v:&mut View,n:&Int)->Int{return child(v,n).await;}
        fn main(){let mut p=pool<Int>(2);let a=p.new(1);let b=p.new(2);
            let mut v=View{data:&a};let h=runtime::spawn(->work(&mut v,&b));
            match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}
            drop(->b);print(*v.data);}'''
        verify_program(source)
        run = self.run_c_oracle(compile_source(source))
        self.assertEqual(run.stdout, '7\n1\n')
        for checker in (verify_program, compile_source):
            with self.assertRaises(Error):
                checker(source.replace('drop(->b);','drop(->a);'))

    def test_loop_prefixes_follow_swapped_fields(self):
        summary = self.infer('''async fn work(v:&mut View,flag:Bool)->Int{
            while flag{swap(v);yield;}return 0;}''')
        fields = self.fields(summary.suspension_result)[0]
        for field in ('.data', '.spare'):
            self.assertEqual({path for kind,index,path in fields[field]}, {'.data','.spare'})
            self.assertTrue(all(index == 0 for kind,index,path in fields[field]))

    def test_unsupported_prefix_does_not_disguise_itself_as_empty(self):
        for body in (
            'let h=runtime::spawn(->child(v,n));let r=h.await;return 0;',
            'let old=v.data;let mut p=pool<Int>(1);let a=p.new(7);change(v,&a);yield;v.data=old;return 0;',
        ):
            with self.subTest(body=body):
                source = '''async fn child(v:&mut View,n:&Int)->Int{change(v,n);return 1;}
                    async fn work(v:&mut View,n:&Int)->Int{'''+body+'''}
                    async fn parent(v:&mut View,n:&Int)->Int{return work(v,n).await;}'''
                for name in ('work','parent'):
                    summary = self.infer(source, name)
                    self.assertIsNone(summary.suspension_result)
                    self.assertFalse(summary.suspension_complete)
                    self.assertIsNone(summary.may_suspend)
                    self.assertTrue(summary.suspension_reason)
                    self.assertIsNotNone(summary.completion_result)

    def test_untracked_reference_containers_are_not_empty_effects(self):
        for typ in ('&mut [&Int;1]', '&[&mut Int;1]'):
            with self.subTest(typ=typ):
                summary = self.infer('async fn work(v:'+typ+')->Int{yield;return 0;}')
                self.assertTrue(summary.complete)
                self.assertFalse(summary.suspension_complete)
                self.assertIsNone(summary.suspension_result)
                self.assertIn('porteurs', summary.suspension_reason)

    def test_independent_finite_trace_model(self):
        # Concrete list-of-targets model: no compiler values, contracts or CFG.
        # Observe only yield events, even when later actions overwrite a target.
        actions = ('a', 'b', 'swap', 'pause')
        for sequence in product(actions, repeat=3):
            state = ['data', 'spare']
            observations = []
            code = []
            for action in sequence:
                if action in ('a', 'b'):
                    state[0] = action
                    code.append('change(v,'+action+');')
                elif action == 'swap':
                    state.reverse()
                    code.append('swap(v);')
                else:
                    observations.append(tuple(state))
                    code.append('yield;')
            with self.subTest(sequence=sequence):
                summary = self.infer('async fn work(v:&mut View,a:&Int,b:&Int)->Int{'+''.join(code)+'return 0;}')
                self.assertEqual(summary.may_suspend, bool(observations))
                def concrete(result):
                    fields = self.fields(result).get(0, {})
                    return [{('a' if index == 1 else 'b') if kind == 'parameter' else path[1:]
                             for kind,index,path in fields.get('.'+field, {('field_parameter',0,'.'+field)})}
                            for field in ('data','spare')]
                self.assertEqual(concrete(summary.completion_result), [{item} for item in state])
                expected = [{row[i] for row in observations} for i in (0,1)] if observations else [{'data'},{'spare'}]
                self.assertEqual(concrete(summary.suspension_result), expected)

    def test_generated_select_loser_keeps_last_write_not_restoration(self):
        source = '''struct View{data:&Int}
        async fn work(v:&mut View,n:&Int)->Int{
            let old=v.data;v.data=&*n;yield;v.data=old;return 7;}
        async fn ready()->Int{return 9;}
        fn main(){let mut p=pool<Int>(2);let a=p.new(1);let b=p.new(2);
            let mut v=View{data:&a};let h=runtime::spawn(->work(&mut v,&b));
            match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}print(*v.data);
            let other=runtime::spawn(->ready());match other.join(){Ok(s)=>{print(s);},Err(_)=>{}}}'''
        run = self.native(source, '''
    Source p=source_pool(2);Source local=source_stack(4096);
    static const size_t offsets[]={0};static const unsigned char kinds[]={1};
    static const Source layout={.enum_name="View",.arm_name="",.field_count=1,
        .field_offsets=offsets,.field_kinds=kinds};
    for(int i=0;i<8;++i){
        Cell *a=cell_new(&p,1,"a"),*b=cell_new(&p,2,"b");
        Cell *v=local_cell_new(&local,&layout,sizeof(Cell *),"v");cell_store_ref(v,0,a);
        CrustTask *left=crust_async_work_create(v,&b->value,b);
        CrustTask *right=crust_async_ready_create();
        CrustSelectBranch branches[]={{left,left->discard_suspended},{right,right->discard_suspended}};
        CrustSelect selection;task_select_init(&selection,branches,2);
        CrustTask parent={0};
        assert(task_select_poll(&selection,&parent)==TASK_STEP_RETURN);
        int out=0;assert(task_select_take(&selection,&out)&&out==9);
        assert(cell_load_ref(v,0)==b);
        assert(task_owned_discardable(left));task_select_drop(&selection);
        assert(cell_load_ref(v,0)==b && cell_load_ref(v,0)->value==2);
        cell_drop(v);cell_drop(b);cell_drop(a);
    }
    source_close(&local);source_close(&p);
''')
        self.assertEqual(run.stderr.count('destroy b=2'),8)
        self.assertEqual(run.stderr.count('destroy a=1'),8)


if __name__ == '__main__':
    unittest.main()
