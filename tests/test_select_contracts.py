"""Parsed Select expressions and composition of completion/prefix contracts.

These are contract tests, not an authorization from the source loan checker.
"""
from itertools import product
import unittest

from async_structure_effects import AsyncStructureEffectAnalyzer
from crust import Error, Parser, compile_source, verify_program
from test_async_structure_effects import BASE
import test_suspension_effects


class SelectContractTests(unittest.TestCase):
    infer = test_suspension_effects.SuspensionEffectsTests.infer
    fields = test_suspension_effects.SuspensionEffectsTests.fields
    native = test_suspension_effects.SuspensionEffectsTests.native
    run_c_oracle = test_suspension_effects.SuspensionEffectsTests.run_c_oracle

    @classmethod
    def setUpClass(cls):
        cls.baseline = verify_program(BASE)

    def test_parser_requires_each_explicit_transfer(self):
        for arguments in ('', 'left(), ->right()', '->left(), right()'):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(Error, 'transfert ->'):
                Parser('async fn work()->Int{let s=runtime::select('+arguments+');return 0;}').parse()
        nodes = Parser('async fn work()->Int{let s=runtime::select(->left(),->right());return 0;}').parse()
        self.assertEqual(nodes[0].args[3][0].args[1][0], 'task_select')

    def test_loser_retains_prefix_instead_of_final_restoration(self):
        source = '''async fn left(v:&mut View,n:&Int)->Int{
            let old=v.data;change(v,n);yield;v.data=old;return 7;}
        async fn right()->Int{return 9;}
        async fn work(v:&mut View,n:&Int)->Int{
            let mut selection=runtime::select(->left(v,n),->right());
            let result=selection.await;drop(->selection);return result;}'''
        summary = self.infer(source)
        self.assertFalse(summary.may_suspend)
        self.assertIn(('parameter',1,''), self.fields(summary.completion_result)[0]['.data'])
        # The current summary conservatively also permits left to win: it
        # describes possible suspensions, not a guaranteed first suspension.
        self.assertEqual(self.fields(summary.completion_result)[0]['.data'],
                         {('parameter',1,''),('detached_field_parameter',0,'.data')})

    def test_ready_first_branch_leaves_later_branch_unpolled(self):
        summary = self.infer('''async fn left()->Int{return 7;}
        async fn right(v:&mut View,n:&Int)->Int{change(v,n);yield;return 9;}
        async fn work(v:&mut View,n:&Int)->Int{
            let mut s=runtime::select(->left(),->right(v,n));
            let result=s.await;drop(->s);return result;}''')
        self.assertFalse(summary.may_suspend)
        self.assertEqual(self.fields(summary.completion_result), {})

    def test_unreachable_later_body_does_not_need_a_prefix_contract(self):
        summary = self.infer('''async fn ready()->Int{return 1;}
        async fn recursive(v:&mut View)->Int{return recursive(v).await;}
        async fn work(v:&mut View)->Int{
            let mut s=runtime::select(->ready(),->recursive(v));
            let r=s.await;drop(->s);return r;}''')
        self.assertFalse(summary.may_suspend)
        self.assertEqual(self.fields(summary.completion_result), {})

    def test_nonterminating_earlier_loser_must_have_been_polled(self):
        summary = self.infer('''async fn left(v:&mut View,n:&Int)->Int{
            change(v,n);loop{yield;}}
        async fn right()->Int{return 9;}
        async fn work(v:&mut View,n:&Int)->Int{
            let mut s=runtime::select(->left(v,n),->right());
            let result=s.await;drop(->s);return result;}''')
        self.assertEqual(self.fields(summary.completion_result), {0:{'.data':{('parameter',1,'')}}})

    def test_later_loser_can_be_unpolled_after_conditional_first_pause(self):
        summary = self.infer('''async fn first(flag:Bool)->Int{if flag{yield;}return 1;}
        async fn later(v:&mut View,n:&Int)->Int{change(v,n);yield;return 2;}
        async fn work(v:&mut View,n:&Int,flag:Bool)->Int{
            let mut s=runtime::select(->first(flag),->later(v,n));
            let r=s.await;drop(->s);return r;}''')
        self.assertEqual(self.fields(summary.completion_result),
                         {0:{'.data':{('field_parameter',0,'.data'),('parameter',1,'')}}})

    def test_all_branches_can_suspend_then_parent_has_prefix(self):
        summary = self.infer('''async fn left(v:&mut View,n:&Int)->Int{change(v,n);yield;return 7;}
        async fn right(v:&mut View,n:&Int)->Int{change(v,n);yield;return 9;}
        async fn work(v:&mut View,w:&mut View,a:&Int,b:&Int)->Int{
            let mut s=runtime::select(->left(v,a),->right(w,b));
            let result=s.await;drop(->s);return result;}''')
        self.assertTrue(summary.may_suspend)
        self.assertEqual(self.fields(summary.suspension_result),
                         {0:{'.data':{('parameter',2,'')}},1:{'.data':{('parameter',3,'')}}})

    def test_creation_and_drop_do_not_require_running_branch_contracts(self):
        summary = self.infer('''async fn child(v:&mut View)->Int{return child(v).await;}
        async fn work(v:&mut View)->Int{
            let s=runtime::select(->child(v));drop(->s);return 0;}''')
        self.assertEqual(self.fields(summary.completion_result), {})
        self.assertFalse(summary.may_suspend)

    def test_constructor_evaluates_arguments_without_running_tasks(self):
        baseline = verify_program(BASE+'''fn prepare(v:&mut View,n:&Int)->Int{change(v,n);return 1;}''')
        source = '''async fn first(value:Int)->Int{return value;}
        async fn second(v:&mut View,n:&Int)->Int{change(v,n);return 2;}
        async fn work(v:&mut View,w:&mut View,a:&Int,b:&Int)->Int{
            let s=runtime::select(->first(prepare(v,a)),->second(w,b));drop(->s);return 0;}'''
        definitions = {node.args[0]:node for node in Parser(source).parse()}
        summary = AsyncStructureEffectAnalyzer(definitions, baseline.function_contracts,
                                                baseline.enums, Error).infer('work')
        self.assertTrue(summary.complete, summary.reason)
        self.assertEqual(self.fields(summary.completion_result), {0:{'.data':{('parameter',2,'')}}})
        self.assertFalse(summary.may_suspend)

    def test_unknown_prefix_and_different_result_types_remain_unknown(self):
        sources = (
            '''async fn left()->Int{return 1;} async fn right()->Bool{return true;}
                async fn work()->Int{let s=runtime::select(->left(),->right());return 0;}''',
            '''async fn child()->Int{return 1;}
                async fn left()->Int{let h=runtime::spawn(->child());let r=h.await;return 1;}
                async fn work()->Int{let s=runtime::select(->left());let r=s.await;drop(->s);return r;}''',
            '''async fn left()->Int{return 1;} async fn right()->Bool{return true;}
                async fn work(flag:Bool)->Int{
                  let s=if flag{let s=runtime::select(->left());<-s}
                    else{let s=runtime::select(->right());<-s};drop(->s);return 0;}''',
        )
        for source in sources:
            with self.subTest(source=source):
                definitions = {node.args[0]:node for node in Parser(source).parse()}
                summary = AsyncStructureEffectAnalyzer(definitions, self.baseline.function_contracts,
                                                        self.baseline.enums, Error).infer('work')
                self.assertFalse(summary.complete)
                self.assertTrue(summary.reason)

    def test_returned_borrow_is_only_from_a_possible_winner(self):
        summary = self.infer('''async fn first(a:&Int)->&Int{return a;}
        async fn later(b:&Int)->&Int{yield;return b;}
        async fn work(a:&Int,b:&Int)->&Int{
            let mut s=runtime::select(->first(a),->later(b));let r=s.await;drop(->s);return r;}''')
        self.assertEqual({(t.kind,t.parameter,t.field) for t in summary.completion_result.reference_targets},
                         {('parameter',0,'')})

    def test_captures_and_nested_selection_effects_reach_parent(self):
        summary = self.infer('''async fn leaf(v:&mut View,n:&Int)->Int{change(v,n);loop{yield;}}
        async fn ready()->Int{return 1;}
        async fn choose(v:&mut View,n:&Int)->Int{
            let mut s=runtime::select(->leaf(v,n),->ready());let r=s.await;drop(->s);return r;}
        async fn work(v:&mut View,a:&Int,b:&Int)->Int{
            let task=choose(v,a);{let a=b;print(*a);
            let mut s=runtime::select(->task);let r=s.await;drop(->s);print(r);}return 0;}''')
        self.assertEqual(self.fields(summary.completion_result), {0:{'.data':{('parameter',1,'')}}})

    def test_conditional_selection_transfer_keeps_capture_alternatives(self):
        for value in (
            'if flag{let s=runtime::select(->leaf(v,a),->ready());<-s}'
            'else{let s=runtime::select(->leaf(v,b),->ready());<-s}',
            'loop{if flag{let s=runtime::select(->leaf(v,a),->ready());break <-s;}'
            'let s=runtime::select(->leaf(v,b),->ready());break <-s;}',
        ):
            with self.subTest(value=value):
                summary = self.infer('''async fn leaf(v:&mut View,n:&Int)->Int{change(v,n);loop{yield;}}
                async fn ready()->Int{return 1;}
                async fn work(v:&mut View,a:&Int,b:&Int,flag:Bool)->Int{
                    let first='''+value+''';let mut s=<-first;let r=s.await;drop(->s);return r;}''')
                self.assertEqual(self.fields(summary.completion_result),
                                 {0:{'.data':{('parameter',1,''),('parameter',2,'')}}})

    def test_independent_concrete_scheduler_model(self):
        # Each branch owns a separate external field. Execute an actual ordered
        # round-robin scheduler over instruction lists, stopping on first ready.
        # Contract unions may overapproximate, but must contain the real state.
        programs = (('return',), ('write','return'), ('write','pause','return'),
                    ('write','pause','restore','return'), ('pause','write','pause','return'))
        for first, second in product(programs, repeat=2):
            state, positions = ['initial0','initial1'], [0,0]
            winner = None
            while winner is None:
                for branch, instructions in enumerate((first,second)):
                    while True:
                        action = instructions[positions[branch]]
                        positions[branch] += 1
                        if action == 'write': state[branch] = 'new'+str(branch)
                        elif action == 'restore': state[branch] = 'initial'+str(branch)
                        elif action == 'pause': break
                        else:
                            winner = branch
                            break
                    if winner is not None: break
            def body(instructions):
                return 'let old=v.data;'+''.join({'write':'change(v,n);','restore':'v.data=old;',
                    'pause':'yield;','return':'return 1;'}[action] for action in instructions)
            source = ('async fn first(v:&mut View,n:&Int)->Int{'+body(first)+'}'+
                      'async fn second(v:&mut View,n:&Int)->Int{'+body(second)+'}'+'''
                async fn work(v:&mut View,w:&mut View,a:&Int,b:&Int)->Int{
                    let mut s=runtime::select(->first(v,a),->second(w,b));
                    let r=s.await;drop(->s);return r;}''')
            with self.subTest(first=first, second=second):
                summary = self.infer(source)
                fields = self.fields(summary.completion_result)
                for index in (0,1):
                    targets = fields.get(index,{}).get('.data',{('field_parameter',index,'.data')})
                    concrete = {'new'+str(parameter-2) if kind == 'parameter' else 'initial'+str(parameter)
                                for kind,parameter,path in targets}
                    self.assertIn(state[index], concrete)

    def test_simple_source_selection_is_now_executable(self):
        source = '''async fn leaf()->Int{return 1;}
        async fn work()->Int{let mut s=runtime::select(->leaf());let r=s.await;drop(->s);return r;}
        fn main(){let h=runtime::spawn(->work());match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}}'''
        Parser(source).parse()
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '1\n')

    def test_native_selection_combines_winner_and_suspended_loser_stores(self):
        source = '''struct View{data:&Int}
        async fn left(v:&mut View,n:&Int)->Int{
            let old=v.data;v.data=&*n;yield;v.data=old;return 7;}
        async fn right(v:&mut View,n:&Int)->Int{v.data=&*n;return 9;}
        fn main(){let mut p=pool<Int>(4);let a=p.new(1);let b=p.new(2);let c=p.new(3);let d=p.new(4);
            let mut v=View{data:&a};let mut w=View{data:&b};
            let h=runtime::spawn(->left(&mut v,&c));match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}
            let j=runtime::spawn(->right(&mut w,&d));match j.join(){Ok(s)=>{print(s);},Err(_)=>{}}
            print(*v.data);print(*w.data);}'''
        run = self.native(source, '''
    Source p=source_pool(4);Source local=source_stack(4096);
    static const size_t offsets[]={0};static const unsigned char kinds[]={1};
    static const Source layout={.enum_name="View",.arm_name="",.field_count=1,
        .field_offsets=offsets,.field_kinds=kinds};
    for(int i=0;i<8;++i){
        Cell *a=cell_new(&p,1,"a"),*b=cell_new(&p,2,"b");
        Cell *c=cell_new(&p,3,"c"),*d=cell_new(&p,4,"d");
        Cell *v=local_cell_new(&local,&layout,sizeof(Cell *),"v");cell_store_ref(v,0,a);
        Cell *w=local_cell_new(&local,&layout,sizeof(Cell *),"w");cell_store_ref(w,0,b);
        CrustTask *left=crust_async_left_create(structure_reference_for((CrustStructureView){0},v),&c->value,c);
        CrustTask *right=crust_async_right_create(structure_reference_for((CrustStructureView){0},w),&d->value,d);
        CrustSelectBranch branches[]={{left,left->discard_suspended},{right,right->discard_suspended}};
        CrustSelect selection;task_select_init(&selection,branches,2);
        CrustTask parent={0};assert(task_select_poll(&selection,&parent)==TASK_STEP_RETURN);
        int out=0;assert(task_select_take(&selection,&out)&&out==9);
        assert(cell_load_ref(v,0)==c && cell_load_ref(w,0)==d);
        task_select_drop(&selection);
        assert(cell_load_ref(v,0)==c && cell_load_ref(w,0)==d);
        cell_drop(w);cell_drop(v);cell_drop(d);cell_drop(c);cell_drop(b);cell_drop(a);
    }
    source_close(&local);source_close(&p);
''')
        self.assertEqual(run.stderr.count('destroy c=3'),8)
        self.assertEqual(run.stderr.count('destroy d=4'),8)


if __name__ == '__main__':
    unittest.main()
