"""Completion contracts and executable neighbors of async field changes."""
from itertools import product
from pathlib import Path
import unittest

from async_structure_effects import AsyncStructureEffectAnalyzer
from crust import Compiler, Error, Parser, compile_source, verify_program
import test_async_runtime


BASE = '''
struct View { data: &Int, spare: &Int }
fn change(view: &mut View, next: &Int) { view.data = &*next; }
fn relay(view: &mut View, next: &Int) { change(view, next); }
fn fields(view: &mut View, source: &View) { view.data = source.spare; }
fn swap(view: &mut View) {
    let previous = view.data;
    view.data = view.spare;
    view.spare = &*previous;
}
'''


class AsyncStructureEffectsTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle
    @classmethod
    def setUpClass(cls):
        cls.baseline = verify_program(BASE)

    def analyzer(self, declarations):
        definitions = {node.args[0]: node for node in Parser(declarations).parse()
                       if node.op == 'async_fn'}
        return AsyncStructureEffectAnalyzer(definitions, self.baseline.function_contracts,
                                            self.baseline.enums, Error)

    def effects(self, body, prefix='', name='work'):
        declarations = prefix + '''async fn work(view: &mut View, a: &Int, b: &Int,
                                                flag: Bool) -> Int {''' + body + '}'
        summary = self.analyzer(declarations).infer(name)
        self.assertTrue(summary.complete, summary.reason)
        return {index: {field: {(origin.kind, origin.parameter, origin.field) for origin in targets}
                        for field, targets in fields}
                for index, fields in summary.structure_fields}

    def test_input_snapshots_and_synchronous_contracts_without_bodies(self):
        analyzer = self.analyzer('''async fn work(view:&mut View,a:&Int)->Int {
            relay(view,a);yield;return *view.data;
        }''')
        self.assertTrue(all(not node.args[3] for node in analyzer.results.functions.values()))
        summary = analyzer.infer('work')
        self.assertTrue(summary.complete, summary.reason)
        self.assertEqual(summary.structure_fields[0][1][0][1],
                         self.baseline.function_results['change'].structure_fields[0][1][0][1])
        self.assertEqual(self.effects('swap(view);yield;return *view.data;'), {0: {
            '.data': {('detached_field_parameter', 0, '.spare')},
            '.spare': {('detached_field_parameter', 0, '.data')}}})

    def test_order_and_returning_branches(self):
        target = {('parameter', 2, '')}
        self.assertEqual(self.effects('change(view,a);yield;relay(view,b);return 0;'),
                         {0: {'.data': target}})
        self.assertEqual(self.effects('if flag {change(view,a);return 0;}change(view,b);return 1;'),
                         {0: {'.data': {('parameter', 1, ''), *target}}})
        self.assertEqual(self.effects('if flag {return 0;}change(view,b);return 1;'),
                         {0: {'.data': {('field_parameter', 0, '.data'), *target}}})

    def test_lazy_creation_drop_and_await(self):
        child = 'async fn child(v:&mut View,n:&Int)->Int{change(v,n);yield;return 1;}'
        self.assertEqual(self.effects('let t=child(view,a);drop(->t);return 0;', child), {})
        self.assertEqual(self.effects('let t=child(view,a);yield;let n=t.await;return n;', child),
                         {0: {'.data': {('parameter', 1, '')}}})

    def test_nested_awaits_and_parameter_permutation(self):
        prefix = '''async fn leaf(v:&mut View,n:&Int)->Int{relay(v,n);yield;return 1;}
          async fn middle(n:&Int,v:&mut View)->Int{let t=leaf(v,n);return t.await;}
          async fn top(v:&mut View,n:&Int)->Int{return middle(n,v).await;}'''
        self.assertEqual(self.effects('return top(view,b).await;', prefix),
                         {0: {'.data': {('parameter', 2, '')}}})

    def test_captures_are_snapshots_not_late_name_lookups(self):
        child = 'async fn child(v:&mut View,n:&Int)->Int{change(v,n);return 1;}'
        self.assertEqual(self.effects('''let t=child(view,a);
            {let a=b;print(*a);let n=t.await;print(n);}return 0;''', child),
            {0: {'.data': {('parameter', 1, '')}}})

    def test_renamed_carrier_and_field_origin(self):
        self.assertEqual(self.effects('''let mut alias=&mut *view;
            relay(alias,b);yield;return 0;'''), {0: {'.data': {('parameter', 2, '')}}})
        analyzer = self.analyzer('''async fn work(v:&mut View,s:&View)->Int {
            fields(v,s);yield;return 1;
        }''')
        summary = analyzer.infer('work')
        self.assertTrue(summary.complete, summary.reason)
        origins = summary.structure_fields[0][1][0][1]
        self.assertEqual({(x.kind,x.parameter,x.field) for x in origins},
                         {('detached_field_parameter',1,'.spare')})

    def test_launch_failure_preserves_old_field_alternative(self):
        child = 'async fn child(v:&mut View,n:&Int)->Int{change(v,n);return 1;}'
        self.assertEqual(self.effects('let h=runtime::spawn(->child(view,a));let n=h.await;return 0;', child),
                         {0: {'.data': {('field_parameter',0,'.data'), ('parameter',1,'')}}})

    def test_loop_edges_preserve_dependencies(self):
        self.assertEqual(self.effects('''loop {change(view,a);yield;
            if flag {change(view,b);break;}continue;}return 0;'''),
                         {0: {'.data': {('parameter',2,'')}}})
        self.assertEqual(self.effects('''while flag {change(view,b);yield;}return 0;'''),
                         {0: {'.data': {('field_parameter',0,'.data'), ('parameter',2,'')}}})

    def test_loop_of_awaited_swaps_converges_without_losing_input_targets(self):
        child = 'async fn child(v:&mut View)->Int{swap(v);yield;return 1;}'
        actual = self.effects('while flag {let n=child(view).await;print(n);}return 0;',child)
        # A concrete swap has period two. Zero/even and odd iterations are all
        # possible; both fields must retain exactly these two original targets.
        states = set()
        state = ('data','spare')
        for _ in range(4):
            states.add(state)
            state = (state[1],state[0])
        expected = {'.'+field: {'.'+state[index] for state in states}
                    for index,field in enumerate(('data','spare'))}
        self.assertEqual({field:{path for _,index,path in targets}
                          for field,targets in actual[0].items()},expected)
        self.assertTrue(all(index==0 for targets in actual[0].values() for _,index,_ in targets))

    def test_task_choices_keep_capture_alternatives(self):
        child = 'async fn child(v:&mut View,n:&Int)->Int{change(v,n);return 1;}'
        for initializer in (
            'if flag {let t=child(view,a);<-t}else{let t=child(view,b);<-t}',
            'loop{if flag {let t=child(view,a);break <-t;}let t=child(view,b);break <-t;}',
        ):
            with self.subTest(initializer=initializer):
                self.assertEqual(self.effects('let t='+initializer+';return t.await;',child),
                                 {0:{'.data':{('parameter',1,''),('parameter',2,'')}}})
        distinct = child + 'async fn other(v:&mut View,n:&Int)->Int{relay(v,n);return 2;}'
        self.assertEqual(self.effects('''let h=if flag {
            let h=runtime::spawn(->child(view,a));<-h
          }else{let h=runtime::spawn(->other(view,b));<-h};
          let result=h.await;return 0;''',distinct),
          {0:{'.data':{('field_parameter',0,'.data'),('parameter',1,''),('parameter',2,'')}}})

    def test_noncompleting_child_does_not_invent_a_continuation(self):
        child = 'async fn child(v:&mut View,n:&Int)->Int{change(v,n);loop{yield;}}'
        source = child + '''async fn work(view:&mut View,a:&Int,b:&Int,flag:Bool)->Int{
          if flag {let n=child(view,a).await;print(n);change(view,a);return 0;}
          change(view,b);return 1;}'''
        analyzer = self.analyzer(source)
        self.assertEqual(analyzer.infer('child').may_complete,False)
        summary = analyzer.infer('work')
        self.assertTrue(summary.complete,summary.reason)
        self.assertTrue(summary.may_complete)
        self.assertEqual({(x.kind,x.parameter,x.field) for x in summary.structure_fields[0][1][0][1]},
                         {('parameter',2,'')})
        # A failed launch can return even though the body never completes.
        self.assertEqual(self.effects('let h=runtime::spawn(->child(view,a));let n=h.await;return 0;',child),{})

    def test_incomplete_is_not_an_empty_contract(self):
        programs = (
            '''async fn work(v:&mut View)->Int{let mut p=pool<Int>(1);
               let a=p.new(7);change(v,&a);return 0;}''',
            '''async fn work(v:&mut View)->Int{return work(v).await;}''',
            '''async fn leaf(v:&View)->&View{return v;}
               async fn work(v:&mut View)->Int{let r=leaf(v).await;print(r);return 0;}''',
        )
        for source in programs:
            with self.subTest(source=source):
                summary = self.analyzer(source).infer('work')
                self.assertFalse(summary.complete)
                self.assertIsNone(summary.structure_fields)
                self.assertTrue(summary.reason)

    def test_awaited_reference_supplies_new_field_target(self):
        child = 'async fn leaf(n:&Int)->&Int{yield;return n;}'
        self.assertEqual(self.effects('let n=leaf(a).await;change(view,n);return 0;',child),
                         {0:{'.data':{('parameter',1,'')}}})
        launched = '''let h=runtime::spawn(->leaf(a));let result=h.await;
          match result{Ok(n)=>{change(view,n);},Err(_)=>{}}return 0;'''
        self.assertEqual(self.effects(launched,child),
                         {0:{'.data':{('parameter',1,''),('field_parameter',0,'.data')}}})

    def test_completion_pairs_field_writes_with_detached_result(self):
        child = '''async fn leaf(view:&mut View,n:&Int)->&Int{
          change(view,n);yield;return view.data;}'''
        analyzer = self.analyzer(child+'''async fn work(view:&mut View,a:&Int)->&Int{
          let n=leaf(view,a).await;yield;return n;}''')
        summary = analyzer.infer('work')
        self.assertTrue(summary.complete,summary.reason)
        self.assertEqual({(t.kind,t.parameter,t.field) for t in summary.completion_result.reference_targets},
                         {('parameter',1,'')})
        self.assertEqual({(t.kind,t.parameter,t.field) for t in summary.structure_fields[0][1][0][1]},
                         {('parameter',1,'')})
        self.assertTrue(all(not node.args[3] for node in analyzer.results.functions.values()))

    def test_result_detached_before_write_uses_input_snapshot(self):
        child = '''async fn leaf(view:&mut View,n:&Int)->&Int{
          let old=view.data;change(view,n);yield;return old;}'''
        analyzer = self.analyzer(child+'''async fn work(view:&mut View,a:&Int)->&Int{
          let n=leaf(view,a).await;yield;return n;}''')
        summary = analyzer.infer('work')
        self.assertTrue(summary.complete,summary.reason)
        self.assertEqual({(t.kind,t.parameter,t.field) for t in summary.completion_result.reference_targets},
                         {('detached_field_parameter',0,'.data')})
        self.assertEqual({(t.kind,t.parameter,t.field) for t in summary.structure_fields[0][1][0][1]},
                         {('parameter',1,'')})

    def test_reference_choices_retain_both_targets_through_relays(self):
        child = '''async fn left(a:&Int,b:&Int)->&Int{yield;return a;}
          async fn right(a:&Int,b:&Int)->&Int{yield;return b;}
          async fn choose(a:&Int,b:&Int,flag:Bool)->&Int{
            let t=if flag{let x=left(a,b);<-x}else{let x=left(b,a);<-x};
            let n=t.await;return n;}'''
        self.assertEqual(self.effects('let n=choose(a,b,flag).await;change(view,n);return 0;',child),
                         {0:{'.data':{('parameter',1,''),('parameter',2,'')}}})
        handles = '''let h=if flag{let h=runtime::spawn(->left(a,b));<-h}
          else{let h=runtime::spawn(->right(a,b));<-h};
          match h.await{Ok(n)=>{change(view,n);},Err(_)=>{}}return 0;'''
        self.assertEqual(self.effects(handles,child),
                         {0:{'.data':{('field_parameter',0,'.data'),('parameter',1,''),('parameter',2,'')}}})

    def test_mutable_return_preserves_carrier_in_completion_contract(self):
        baseline = verify_program('struct Writer{data:&mut Int}')
        definitions = {node.args[0]:node for node in Parser('''
          async fn leaf(w:&mut Writer)->&mut Int{yield;return &mut *w.data;}
          async fn work(w:&mut Writer)->&mut Int{let mut n=leaf(w).await;return n;}
        ''').parse()}
        summary = AsyncStructureEffectAnalyzer(definitions,baseline.function_contracts,
                                               baseline.enums,Error).infer('work')
        self.assertTrue(summary.complete,summary.reason)
        self.assertEqual({(t.kind,t.parameter,t.field) for t in summary.completion_result.reference_targets},
                         {('indirect_field_parameter',0,'data')})

    def test_borrowed_local_result_is_incomplete_not_empty(self):
        summary = self.analyzer('''async fn leaf()->&Int{let mut p=pool<Int>(1);
          let n=p.new(7);return &n;}
          async fn work(v:&mut View)->Int{let n=leaf().await;change(v,n);return 0;}''').infer('work')
        self.assertFalse(summary.complete)
        self.assertIsNone(summary.structure_fields)
        self.assertIn('durable',summary.reason)

    def test_independent_completion_result_and_write_model(self):
        # Concrete identities, not contract origins: an old data target, an
        # old spare target and two candidate replacements.
        for action, before, launched in product(('none','a','b','choice'),(False,True),(False,True)):
            write = {'none':'', 'a':'change(v,a);', 'b':'change(v,b);',
                     'choice':'if flag{change(v,a);}else{change(v,b);}'}[action]
            child = '''async fn child(v:&mut View,a:&Int,b:&Int,flag:Bool)->&Int{
              let previous=v.data;'''+write+('return previous;' if before else 'return v.data;')+'}'
            # Reading previous explicitly keeps both source forms meaningful.
            if not before:
                child = child.replace('let previous=v.data;','')
            call = 'child(view,a,b,flag)'
            body = ('let h=runtime::spawn(->'+call+');match h.await{Ok(n)=>{view.spare=&*n;},Err(_)=>{}}'
                    if launched else 'let n='+call+'.await;view.spare=&*n;')+'return 0;'
            expected = set()
            for flag in (False,True):
                data = {'none':'old','a':'a','b':'b','choice':'a' if flag else 'b'}[action]
                expected.add((data,'old' if before else data))
            if launched:
                expected.add(('old','spare'))
            identity = {('parameter',1,''):'a',('parameter',2,''):'b',
                        ('field_parameter',0,'.data'):'old',('detached_field_parameter',0,'.data'):'old',
                        ('field_parameter',0,'.spare'):'spare',('detached_field_parameter',0,'.spare'):'spare'}
            with self.subTest(action=action,before=before,launched=launched):
                fields = self.effects(body,child).get(0,{})
                actual = {'.data':{'old'},'.spare':{'spare'}}
                actual.update({key:{identity[target] for target in targets} for key,targets in fields.items()})
                self.assertEqual(actual,{key:{state[i] for state in expected}
                                         for i,key in enumerate(('.data','.spare'))})

    def test_executable_neighbor_awaits_reference_then_stores_locally(self):
        source = BASE+'''fn inspect(n:&Int)->Int{let v=View{data:&*n,spare:&*n};return *v.data+*v.spare;}
          async fn leaf(n:&Int)->&Int{yield;return n;}
          async fn work(n:&Int)->Int{let r=leaf(n).await;yield;return inspect(r);}
          fn main(){let mut p=pool<Int>(1);let n=p.new(7);
            let h=runtime::spawn(->work(&n));BEFORE
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}drop(->n);}'''
        compiler = verify_program(source.replace('BEFORE',''))
        self.assertTrue(compiler.async_structure_effects['leaf'].complete)
        self.assertTrue(compiler.async_structure_effects['work'].complete)
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE',''))).stdout,'14\n')
        for stage in (verify_program,compile_source):
            with self.subTest(stage=stage.__name__),self.assertRaisesRegex(Error,'emprunt|réserv'):
                stage(source.replace('BEFORE','drop(->n);'))

    def test_deferred_writes_cannot_disappear_inside_sync_handle_helper(self):
        source = BASE + '''
          async fn child(v:&mut View,n:&Int)->Int{change(v,n);return 1;}
          fn finish(h:->Execution<child>)->Int{
            return match h.join(){Ok(n)=>{n},Err(_)=>{0}};
          }
          async fn work(v:&mut View,n:&Int)->Int{
            let h=runtime::spawn(->child(v,n));return finish(->h);
          }'''
        compiler = Compiler()
        with self.assertRaisesRegex(Error,'join réservé au code synchrone'):
            compiler.verify(Parser(source).parse())
        summary = compiler.async_structure_effects['work']
        # Handle-wait contracts now propagate these effects. The illegal
        # synchronous wait above is still rejected independently of inference.
        self.assertTrue(summary.complete,summary.reason)
        fields = {index: {field: {(origin.kind, origin.parameter, origin.field)
                                  for origin in targets} for field, targets in changes}
                  for index, changes in summary.structure_fields}
        self.assertEqual(fields, {0: {'.data': {
            ('field_parameter', 0, '.data'), ('parameter', 1, '')}}})

    def test_mutable_reference_field_summary(self):
        baseline = verify_program('''struct Writer{data:&mut Int}
            fn change(w:&mut Writer,n:&mut Int){w.data=&mut *n;}''')
        definitions = {node.args[0]:node for node in Parser('''
            async fn work(w:&mut Writer,n:&mut Int)->Int{change(w,n);yield;return 1;}
        ''').parse()}
        summary = AsyncStructureEffectAnalyzer(definitions, baseline.function_contracts,
                                               baseline.enums, Error).infer('work')
        self.assertTrue(summary.complete, summary.reason)
        self.assertEqual(summary.structure_fields, baseline.function_results['change'].structure_fields)

    def test_independent_branch_model(self):
        # Concrete state machine: a slot contains either old, a or b. Neither
        # the compiler's origin mapping nor its branch join computes this oracle.
        actions = ('none', 'a', 'b', 'await_a', 'discard_b')
        statements = {'none':'yield;', 'a':'change(view,a);', 'b':'relay(view,b);',
                      'await_a':'let n=child(view,a).await;print(n);',
                      'discard_b':'let t=child(view,b);drop(->t);'}
        def execute(state, action):
            return {'a':'a', 'b':'b', 'await_a':'a'}.get(action,state)
        origins = {'old':('field_parameter',0,'.data'), 'a':('parameter',1,''),
                   'b':('parameter',2,'')}
        child = 'async fn child(v:&mut View,n:&Int)->Int{change(v,n);yield;return 1;}'
        count = 0
        for before, left, right in product(actions, repeat=3):
            state = execute('old',before)
            possible = {execute(state,left),execute(state,right)}
            expected = {} if possible == {'old'} else {0:{'.data':{origins[x] for x in possible}}}
            body = statements[before] + 'if flag {' + statements[left] + '}else{' + statements[right] + '}return 0;'
            with self.subTest(before=before,left=left,right=right):
                self.assertEqual(self.effects(body,child),expected)
            count += 1
        self.assertEqual(count,125)

    def test_compiler_applies_supported_shared_field_summary(self):
        source = (Path(__file__).resolve().parents[1]/'validation/open-async-sync-field-replacement.crb').read_text()
        compiler = verify_program(source)
        self.assertTrue(compiler.async_structure_effects['update'].complete)
        self.assertTrue(compiler.async_structure_effects['update'].structure_fields)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'9\n9\n')

    def test_synchronous_neighbor_changes_target_and_releases_old_one(self):
        source = '''struct View{data:&Int}
          fn change(view:&mut View,next:&Int){view.data=&*next;}
          fn update(view:&mut View,next:&Int)->Int{change(view,next);return *view.data;}
          fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
            let mut view=View{data:&a};let n=update(&mut view,&b);print(n);
            drop(->a);BEFORE print(*view.data);}'''
        valid = source.replace('BEFORE','')
        verify_program(valid)
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout,'9\n9\n')
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaisesRegex(Error,'emprunt|référ|dépend'):
                    check(source.replace('BEFORE','drop(->b);'))


if __name__ == '__main__':
    unittest.main()
