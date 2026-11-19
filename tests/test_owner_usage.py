"""U1: every received owner needs an explicit possible use, before replacement."""
import unittest
import test_foundation_rules
from crust import Error, compile_source


class OwnerUsageTests(unittest.TestCase):
    native = test_foundation_rules.FoundationTests.native

    def test_allocation_and_move_cannot_hide_unused_receivers(self):
        for name in ('unused', '_unused', '_'):
            for operation in ('p.new(7)', 'new(p) Int(7)'):
                with self.subTest(name=name, operation=operation), self.assertRaisesRegex(Error, 'sans usage explicite|motif _'):
                    compile_source(f'let mut p=pool<Int>(1);let {name}={operation};')
            with self.subTest(name=name, move=True), self.assertRaisesRegex(Error, 'sans usage explicite|motif _'):
                compile_source(f'let mut p=pool<Int>(1);let initial=p.new(7);let {name}=<- initial;')
        for declaration in ('struct Point {x:Int} let unused=Point {x:7};',
                            'struct Point {x:Int} let original=Point {x:7};let unused=copy(original);',
                            'let mut p=pool<Vector<Int>>(1);let unused=p.new();',
                            'let mut p=pool<String>(1);let unused=p.new();'):
            with self.subTest(declaration=declaration),self.assertRaisesRegex(Error,'sans usage explicite'):
                compile_source(declaration)

    def test_possible_read_keeps_ordinary_scope_cleanup(self):
        run=self.native('''fn run(flag:Int){let mut p=pool<Int>(1);
            {let value=p.new(7);if flag==1 {print(*value);} }
            let next=p.new(9);print(*next);
        }fn main(){run(0);run(1);}''')
        self.assertEqual((run.returncode,run.stdout),(0,'9\n7\n9\n'),run.stderr)
        self.assertEqual(run.stderr.count('destroy value=7'),2)
        self.assertEqual(run.stderr.count('destroy next=9'),2)

    def test_content_write_counts_but_implicit_replacement_drop_does_not(self):
        prefix='let mut p=pool<Int>(2);'
        for statements in (
            'let mut value=p.new(7);value=<- p.new(9);print(*value);',
            'let mut value=p.new(7);print(*value);value=<- p.new(9);',
        ):
            with self.subTest(statements=statements),self.assertRaisesRegex(Error,'sans usage explicite'):
                compile_source(prefix+statements)
        run=self.native(prefix+'''let mut value=p.new(7);value=8;
            value=<- p.new(9);print(*value);''')
        self.assertEqual((run.returncode,run.stdout),(0,'9\n'),run.stderr)
        self.assertEqual(run.stderr.count('destroy value=8'),1)
        self.assertEqual(sum(line.endswith('=9') for line in run.stderr.splitlines() if line.startswith('destroy')),1)

    def test_nested_receiver_replacement_counts_use_in_parent(self):
        run=self.native('''let mut p=pool<Int>(2);let mut result=p.new(7);print(*result);
            {let next=p.new(9);result=<- next;}
            print(*result);''')
        self.assertEqual((run.returncode,run.stdout),(0,'7\n9\n'),run.stderr)

    async_prefix='''async fn leaf(n: -> Int) -> <- Int {yield;return <- n;}
        async fn run(n: -> Int) { BODY }
        fn main(){let mut p=pool<Int>(1);let n=p.new(7);
            let h=runtime::spawn(-> run(-> n));
            match h.join(){Ok(())=>{},Err(_)=>{}}
            let reused=p.new(9);print(*reused);
        }'''

    def test_async_await_move_and_control_receivers_need_usage(self):
        forms=(
            'let VALUE=leaf(-> n).await;',
            'let task=leaf(-> n);let VALUE=task.await;',
            'let VALUE=(if true {let task=leaf(-> n);<- task} else {let task=leaf(-> n);<- task}).await;',
            'let received=leaf(-> n).await;let VALUE=<- received;',
            'let VALUE={let received=leaf(-> n).await;<- received};',
            'let VALUE=if true {let received=leaf(-> n).await;<- received} else {let received=leaf(-> n).await;<- received};',
            'let VALUE=loop {let received=leaf(-> n).await;break <- received;};',
        )
        for form in forms:
            for name in ('unused','_unused','_'):
                with self.subTest(form=form,name=name),self.assertRaisesRegex(Error,'sans usage explicite|motif _'):
                    compile_source(self.async_prefix.replace('BODY',form.replace('VALUE',name)))
            with self.subTest(form=form,used=True):
                run=self.native(self.async_prefix.replace('BODY',form.replace('VALUE','received_final')+'print(*received_final);'))
                self.assertEqual((run.returncode,run.stdout),(0,'7\n9\n'),run.stderr)
                self.assertEqual(run.stderr.count('destroy n=7'),1)

    def test_async_join_result_rename_and_block_do_not_hide_unused_owner(self):
        start='let task=leaf(-> n);let h=runtime::spawn(-> task);'
        forms=('let result=h.await;let unused=<- result;',
               'let unused={let result=h.await;<- result};',
               'let unused=if true {let result=h.await;<- result} else {let result=h.await;<- result};')
        for form in forms:
            with self.subTest(form=form),self.assertRaisesRegex(Error,'sans usage explicite'):
                compile_source(self.async_prefix.replace('BODY',start+form))
            run=self.native(self.async_prefix.replace('BODY',start+form+'drop(-> unused);'))
            self.assertEqual((run.returncode,run.stdout),(0,'9\n'),run.stderr)

    def test_ancestor_replacement_does_not_reuse_past_read_as_proof(self):
        prefix='let mut p=pool<Int>(3);let mut result=p.new(7);print(*result);'
        with self.assertRaisesRegex(Error,'sans usage explicite'):
            compile_source(prefix+'{let next=p.new(9);result=<- next;}')
        run=self.native(prefix+'''let mut i=0;loop {
            print(*result);result=<- p.new(9);i=i+1;
            if i<2 {continue;}break;
        }print(*result);''')
        self.assertEqual((run.returncode,run.stdout),(0,'7\n7\n9\n9\n'),run.stderr)

    def test_async_replacement_checks_new_value_and_parent_continuation(self):
        prefix='''async fn leaf(n:->Int)-><-Int {yield;return <- n;}
            async fn work(mut a:->Int,b:->Int) { ACTION }
            fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
                let h=runtime::spawn(-> work(-> a,-> b));
                match h.join(){Ok(())=>{},Err(_)=>{}}
            }'''
        for action in ('a=leaf(-> b).await;', '{b ->;a=leaf(-> b).await;}',
                       'print(*a);a=<- b;'):
            with self.subTest(action=action),self.assertRaisesRegex(Error,'sans usage explicite'):
                compile_source(prefix.replace('ACTION',action))
        for action,output in (
            ('a=leaf(-> b).await;print(*a);','9\n'),
            ('{b ->;a=leaf(-> b).await;}print(*a);','9\n'),
            ('a=leaf(-> b).await;a=10;',''),
        ):
            run=self.native(prefix.replace('ACTION',action))
            self.assertEqual((run.returncode,run.stdout),(0,output),run.stderr)
            self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()),2)

    def test_generated_receipt_epochs_match_forward_usage_model(self):
        # Independent forward model: each replacement closes one receipt epoch.
        # Scope cleanup is deliberately not an explicit use of that epoch.
        from itertools import product
        for operations in product(('read', 'write', 'replace', 'conditional'), repeat=2):
            for final_drop in (False, True):
                used=False
                permitted=True
                value=7
                destroyed=[]
                fragments=[]
                outputs={0:[],1:[]}
                for operation in operations:
                    if operation=='replace':
                        permitted &= used
                        destroyed.append(value)
                        used=False
                        value=9
                        fragments.append('value=<- p.new(9);')
                    elif operation=='write':
                        used=True
                        value=11
                        fragments.append('value=11;')
                    elif operation=='read':
                        used=True
                        fragments.append('print(*value);')
                        for flag in outputs:outputs[flag].append(str(value))
                    else:
                        used=True
                        fragments.append('if flag==1 {print(*value);}')
                        outputs[1].append(str(value))
                if final_drop:
                    used=True
                    fragments.append('drop(-> value);')
                permitted &= used
                destroyed.append(value)
                for flag in (0,1):
                    source='fn main(){let flag='+str(flag)+';let mut p=pool<Int>(3);let mut value=p.new(7);'+''.join(fragments)+'}'
                    with self.subTest(operations=operations,final_drop=final_drop,flag=flag):
                        if not permitted:
                            with self.assertRaisesRegex(Error,'sans usage explicite'):
                                compile_source(source)
                        else:
                            run=self.native(source)
                            self.assertEqual(run.returncode,0,run.stderr)
                            self.assertEqual(run.stdout.splitlines(),outputs[flag])
                            actual=[int(line.rsplit('=',1)[1]) for line in run.stderr.splitlines() if line.startswith('destroy ')]
                            self.assertEqual(actual,destroyed)

    def test_future_read_of_another_receipt_or_shadow_does_not_count(self):
        invalid=(
            'let mut value=p.new(7);print(*value);{value=<-p.new(9);value=<-p.new(11);}print(*value);',
            'let mut value=p.new(7);if flag==1{value=<-p.new(9);}else{value=<-p.new(11);}print(*value);',
            'let value=p.new(7);{let value=p.new(9);print(*value);}',
        )
        for body in invalid:
            with self.subTest(body=body),self.assertRaisesRegex(Error,'sans usage explicite'):
                compile_source('fn run(flag:Int){let mut p=pool<Int>(3);'+body+'}run(1);')
        valid=(
            ('let mut value=p.new(7);if flag==1{value=<-p.new(9);}print(*value);','7\n9\n'),
            ('let value=p.new(7);{let value=p.new(9);print(*value);}print(*value);','9\n7\n9\n7\n'),
        )
        for body,expected in valid:
            run=self.native('fn run(flag:Int){let mut p=pool<Int>(3);'+body+'}run(0);run(1);')
            self.assertEqual((run.returncode,run.stdout),(0,expected),run.stderr)

    def test_async_argument_replacement_uses_enclosing_statement_continuation(self):
        source='''async fn leaf(n:->Int)-><-Int {yield;return <- n;}
            async fn marker(tag:Int) {print(tag);}
            async fn work(mut a:->Int,b:->Int) {
                marker(if true {b ->;a=leaf(-> b).await;1}
                       else {b ->;a=<- b;2}).await;
                USE
            }
            fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
                let h=runtime::spawn(-> work(-> a,-> b));
                match h.join(){Ok(())=>{},Err(_)=>{}}
            }'''
        run=self.native(source.replace('USE','print(*a);'))
        self.assertEqual((run.returncode,run.stdout),(0,'1\n9\n'),run.stderr)
        with self.assertRaisesRegex(Error,'sans usage explicite'):
            compile_source(source.replace('USE',''))

    def test_async_following_argument_uses_current_receipt_before_replacement(self):
        source='''async fn leaf(n:->Int)-><-Int {yield;return <- n;}
            async fn observe(first:Int,second:Int,view:&Int){print(*view);}
            async fn work(mut a:->Int,b:->Int,c:->Int){
                observe(if true {b ->;a=leaf(-> b).await;1} else {b ->;a=<-b;1},
                        if true {c ->;READ a=leaf(-> c).await;2} else {c ->;READ a=<-c;2},
                        &a).await;
            }
            fn main(){let mut p=pool<Int>(3);let a=p.new(7);let b=p.new(9);let c=p.new(11);
                let h=runtime::spawn(->work(->a,->b,->c));
                match h.join(){Ok(())=>{},Err(_)=>{}}
            }'''
        with self.assertRaisesRegex(Error,'sans usage explicite'):
            compile_source(source.replace('READ',''))
        run=self.native(source.replace('READ','print(*a);'))
        self.assertEqual((run.returncode,run.stdout),(0,'9\n11\n'),run.stderr)
        self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()),3)
