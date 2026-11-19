"""RT7: every execution handle carries an explicit, transferable wait obligation."""
import itertools
import unittest
import test_async_runtime
import test_type_features
from crust import Error, compile_source, verify_program


class HandleObligationTests(unittest.TestCase):
    native = test_type_features.TypeFeatureTests.native
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle
    leaf = 'async fn leaf(n:Int)->Int{yield;return n;}'
    join = 'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}'
    wait = 'match h.await{Ok(n)=>{print(n);},Err(_)=>{print(0);}}'

    def test_scalar_handles_cannot_be_dropped_or_fall_out_of_scope(self):
        for end in ('drop(-> h);', '', 'return;', '{h ->;}'):
            source=self.leaf+'fn main(){let h=runtime::spawn(-> leaf(7));'+end+'}'
            with self.subTest(end=end),self.assertRaisesRegex(Error,'join requis'):
                verify_program(source)
        run=self.native(self.leaf+'fn main(){let h=runtime::spawn(-> leaf(7));'+self.join+'}')
        self.assertEqual(run.stdout,'7\n')

    def test_async_scalar_handles_require_await_even_without_borrows(self):
        prefix=self.leaf+'async fn parent(){let h=runtime::spawn(-> leaf(7));BODY}'
        main='fn main(){let h=runtime::spawn(-> parent());match h.join(){Ok(())=>{},Err(_)=>{}}}'
        for body in ('drop(-> h);', '', 'yield;return;', '{h ->;}'):
            with self.subTest(body=body),self.assertRaisesRegex(Error,'attente requise'):
                verify_program(prefix.replace('BODY',body)+main)
        self.assertEqual(self.native(prefix.replace('BODY',self.wait)+main).stdout,'7\n')

    def test_obligation_follows_contracts_and_receiver_transfers(self):
        source=self.leaf+'''
            fn launch()-><- Execution<leaf>{let h=runtime::spawn(-> leaf(7));return <- h;}
            fn relay(h:-> Execution<leaf>)-><- Execution<leaf>{return <- h;}
            fn finish(h:-> Execution<leaf>)->Int{
                match h.join(){Ok(n)=>{return n;},Err(_)=>{return 0;}}}
            fn main(){let received={let h=launch();let moved=relay(-> h);<- moved};
                print(finish(-> received));}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        for replacement in ('drop(-> received);',''):
            with self.subTest(replacement=replacement),self.assertRaisesRegex(Error,'join requis'):
                verify_program(source.replace('print(finish(-> received));',replacement))
        with self.assertRaisesRegex(Error,'join requis'):
            verify_program(self.leaf+'fn ignore(h:-> Execution<leaf>){drop(-> h);}fn main(){}')

    def test_each_branch_disposes_its_obligation_in_independent_path_model(self):
        # The oracle tracks one obligation per path: only an explicit wait
        # consumes it. This does not inspect compiler states or emitted C.
        actions={'wait':self.join, 'drop':'drop(-> h);', 'leave':''}
        for left,right in itertools.product(actions,repeat=2):
            source=self.leaf+f'''
                fn run(flag:Int){{let h=runtime::spawn(-> leaf(7));
                    if flag==0{{h ->;{actions[left]}}}else{{h ->;{actions[right]}}}}}
                fn main(){{run(0);run(1);}}
            '''
            obligations=[int(action!='wait') for action in (left,right)]
            with self.subTest(left=left,right=right):
                if not any(obligations):
                    self.assertEqual(self.native(source).stdout,'7\n7\n')
                else:
                    with self.assertRaisesRegex(Error,'join requis'):
                        verify_program(source)

    def test_break_continue_and_replacement_cannot_abandon_handle(self):
        for exit in ('break;', 'continue;', 'return;'):
            source=self.leaf+'fn main(){loop{let h=runtime::spawn(-> leaf(7));'+exit+'}}'
            with self.subTest(exit=exit),self.assertRaisesRegex(Error,'join requis'):
                verify_program(source)
        source=self.leaf+'''fn main(){let mut h=runtime::spawn(-> leaf(7));
            h=runtime::spawn(-> leaf(9));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        with self.assertRaisesRegex(Error,'join requis'):
            verify_program(source)
        valid=self.leaf+'''fn main(){let received=loop{let h=runtime::spawn(-> leaf(7));break <- h;};
            match received.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.native(valid).stdout,'7\n')

    def test_async_branches_and_loop_exits_preserve_wait_obligation(self):
        actions={'wait':self.wait, 'drop':'drop(-> h);', 'leave':''}
        main='fn main(){let h=runtime::spawn(-> parent(0));match h.join(){Ok(())=>{},Err(_)=>{}}}'
        for left,right in itertools.product(actions,repeat=2):
            source=self.leaf+f'''
                async fn parent(flag:Int){{let h=runtime::spawn(-> leaf(7));
                    if flag==0{{h ->;{actions[left]}}}else{{h ->;{actions[right]}}}}}
            '''+main
            obligations=[int(action!='wait') for action in (left,right)]
            with self.subTest(left=left,right=right):
                if not any(obligations):
                    for flag in (0,1):
                        self.assertEqual(self.native(source.replace('parent(0)',f'parent({flag})')).stdout,'7\n')
                else:
                    with self.assertRaisesRegex(Error,'attente requise'):
                        verify_program(source)
        for exit in ('break;', 'continue;', 'return;'):
            source=self.leaf+'async fn parent(flag:Int){loop{let h=runtime::spawn(-> leaf(7));'+exit+'}}'+main
            with self.subTest(exit=exit),self.assertRaisesRegex(Error,'attente requise'):
                verify_program(source)

    def test_failure_is_awaited_after_capture_cleanup_and_before_slot_reuse(self):
        source='''async fn own(n:-> Int)->Int{yield;return *n;}
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);address(n);
                let h=runtime::spawn(-> own(-> n));
                match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(0);}}
                let next=p.new(9);address(next);print(*next);}'''
        code=compile_source(source)
        for fail_start in (False,True):
            injected=code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                  '#define pthread_create(t,a,r,p) EAGAIN') if fail_start else code
            run=self.run_c_oracle(injected)
            before,result,after,number=run.stdout.splitlines()
            self.assertEqual((before,result,number),(after,'0' if fail_start else '7','9'))
            self.assertEqual(run.stderr.count('destroy n=7'),1)

    def test_inactive_task_destruction_remains_allowed(self):
        source='async fn leaf(){yield;print(99);}fn main(){let t=leaf();drop(-> t);let unused=leaf();}'
        compiler=verify_program(source)
        self.assertTrue(any('inactive' in warning for warning in compiler.warnings))
        self.assertEqual(self.native(source).stdout,'')


if __name__=='__main__':
    unittest.main()
