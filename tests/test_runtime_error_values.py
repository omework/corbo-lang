"""Runtime errors are typed, independent values after join/await cleanup."""
from pathlib import Path
import unittest
import test_spawn_blocking
import test_type_features
from crust import Error, compile_source, verify_program


class RuntimeErrorValueTests(unittest.TestCase):
    native=test_type_features.TypeFeatureTests.native
    run_c_oracle=test_spawn_blocking.SpawnBlockingTests.run_c_oracle
    reject_blocking=test_spawn_blocking.SpawnBlockingTests.reject_blocking
    rejecting_callback=test_spawn_blocking.SpawnBlockingTests.rejecting_callback

    def test_recorded_gap_passes_with_success_and_launch_failure(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-runtime-error-value.crb').read_text()
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'7\n')
        self.assertEqual(self.run_c_oracle(self.reject_blocking(code)).stdout,'1\n')

    def test_constructor_copy_parameters_return_and_match_expression(self):
        source='''fn relay(e:runtime::Error)->runtime::Error{return e;}
            fn classify(e:runtime::Error)->Int{
                let n=match e {runtime::Error::LaunchFailed=>{7}};return n;}
            fn main(){let e:runtime::Error=runtime::Error::LaunchFailed;
                let copy=e;let mut received=relay(copy);print(classify(received));received=relay(e);
                print(classify(received));print(classify(e));}
        '''
        self.assertEqual(self.native(source).stdout,'7\n7\n7\n')
        self.assertEqual(self.native(source.replace('runtime::Error::LaunchFailed=>{7}','_=>{7}')).stdout,'7\n7\n7\n')
        for expression in ('5','true','"oops"'):
            with self.subTest(expression=expression),self.assertRaisesRegex(Error,'runtime::Error|annotation|type'):
                verify_program(source.replace('let copy=e;',f'let copy={expression};'))

    def test_error_stays_valid_after_owned_capture_and_result_cleanup(self):
        source='''async fn leaf(n:-> Int)-><- Int{yield;return <- n;}
            async fn diagnose(e:runtime::Error)->Int{yield;match e{runtime::Error::LaunchFailed=>{return 9;}}}
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);address(n);
                let h=runtime::spawn_blocking(->leaf(->n));
                let error=match h.join(){Ok(value)=>{drop(->value);runtime::Error::LaunchFailed},Err(e)=>{e}};
                let next=p.new(8);address(next);drop(->next);
                let checked=runtime::spawn(->diagnose(error));
                match checked.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}
        '''
        for failed in (False,True):
            code=compile_source(source)
            if failed:code=self.reject_blocking(code)
            with self.subTest(failed=failed):
                run=self.run_c_oracle(code)
                lines=run.stdout.splitlines()
                self.assertEqual(lines[0],lines[1])
                self.assertEqual(lines[2],'9')
                self.assertEqual(run.stderr.count('destroy n=7'),1)
                self.assertEqual(run.stderr.count('destroy next=8'),1)

    def test_async_error_capture_return_direct_await_join_and_scope_types(self):
        source='''async fn echo(e:runtime::Error)->runtime::Error{yield;return e;}
            async fn parent()->runtime::Error{
                {let local=runtime::Error::LaunchFailed;match local{runtime::Error::LaunchFailed=>{print(1);}}}
                let local=3;print(local);
                let e=echo(runtime::Error::LaunchFailed).await;
                let mut alias:runtime::Error=e;yield;alias=e;
                let h=runtime::spawn_blocking(->echo(alias));
                let received=match h.await{Ok(value)=>{value},Err(error)=>{error}};
                yield;match received{runtime::Error::LaunchFailed=>{print(6);}}return received;
            }
            fn main(){let h=runtime::spawn(->parent());
                match h.join(){Ok(e)=>{match e{runtime::Error::LaunchFailed=>{print(7);}}},
                    Err(e)=>{match e{runtime::Error::LaunchFailed=>{print(99);}}}}}
        '''
        for failed in (False,True):
            code=compile_source(source)
            if failed:code=self.reject_blocking(code)
            with self.subTest(failed=failed):
                self.assertEqual(self.run_c_oracle(code).stdout,'1\n3\n6\n7\n')

    def test_async_error_branch_survives_yield_and_leaves_no_borrow(self):
        source='''async fn leaf(n:&mut Int)->Int{yield;n.set(4);return *n;}
            async fn parent()->Int{let mut number=1;let h=runtime::spawn_blocking(->leaf(&mut number));
                match h.await{Ok(n)=>{print(n);},Err(error)=>{yield;
                    number=8;match error{runtime::Error::LaunchFailed=>{print(number);}}}}
                number=9;return number;}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}
        '''
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'4\n9\n')
        self.assertEqual(self.run_c_oracle(self.reject_blocking(code)).stdout,'8\n9\n')

    def test_runtime_error_cannot_be_reinterpreted_as_integer_or_reference(self):
        for asynchronous in (False,True):
            for misuse in ('let n:Int=e;', 'let n=e+1;', 'let n=e as Int;',
                           'let bad=read(&e);drop(->bad);','let bad=edit(&mut e);drop(->bad);'):
                source='''async fn read(n:&Int)->Int{return *n;}
                    async fn edit(n:&mut Int){n.set(9);}
                '''+('async fn bad()' if asynchronous else 'fn main()')+'''{
                    let mut e=runtime::Error::LaunchFailed;'''+misuse+'}'
                if asynchronous:source+='fn main(){}'
                with self.subTest(asynchronous=asynchronous,misuse=misuse),self.assertRaises(Error):
                    verify_program(source)
        for declaration in ('fn bad()->Int{return runtime::Error::LaunchFailed;}',
                            'async fn bad()->Int{return runtime::Error::LaunchFailed;}',
                            'async fn bad()->runtime::Error{return 5;}',
                            'fn bad(e:Int){match e{runtime::Error::LaunchFailed=>{}}}',
                            'async fn bad(e:Int){match e{runtime::Error::LaunchFailed=>{}}}'):
            with self.subTest(declaration=declaration),self.assertRaises(Error):
                verify_program(declaration+'fn main(){}')

    def test_error_control_flow_matches_branch_model(self):
        # An independent truth table: choose one side effect, preserve the
        # enum through the loop, then enter its sole variant arm.
        for asynchronous in (False, True):
            for flag, marker in ((False,20),(True,10)):
                prefix='async ' if asynchronous else ''
                suspension='yield;' if asynchronous else ''
                body='''fn choose(flag:Int)->runtime::Error{
                    let e=if flag==1{print(10);runtime::Error::LaunchFailed}
                        else{print(20);runtime::Error::LaunchFailed};
                    let returned=loop{SUSPEND break e;};return returned;}
                '''.replace('SUSPEND',suspension)
                call=f'choose({int(flag)})'
                invoke=(f'let h=runtime::spawn(->{call});match h.join(){{'
                        'Ok(e)=>{match e{runtime::Error::LaunchFailed=>{print(7);}}},'
                        'Err(_)=>{print(99);}}' if asynchronous else
                        f'let e={call};match e{{runtime::Error::LaunchFailed=>{{print(7);}}}}')
                source=prefix+body+'fn main(){'+invoke+'}'
                with self.subTest(asynchronous=asynchronous,flag=flag):
                    self.assertEqual(self.native(source).stdout,f'{marker}\n7\n')
                # The unchecked branch must not smuggle an Int into the enum.
                with self.subTest(wrong_branch=True,asynchronous=asynchronous,flag=flag),self.assertRaises(Error):
                    verify_program(source.replace('print(20);runtime::Error::LaunchFailed','print(20);5'))

    def test_async_wildcard_match_evaluates_computed_error_once(self):
        source='''async fn choose(flag:Bool)->Int{
            match if flag{print(10);runtime::Error::LaunchFailed}
                else{print(20);runtime::Error::LaunchFailed}{_=>{yield;return 7;}}}
            fn main(){let a=runtime::spawn(->choose(true));
                match a.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                let b=runtime::spawn(->choose(false));
                match b.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}
        '''
        self.assertEqual(self.native(source).stdout,'10\n7\n20\n7\n')

    def test_error_function_contract_releases_mutable_capture(self):
        source='''async fn leaf(n:&mut Int)->Int{n.set(2);return *n;}
            fn use_error(n:&mut Int)->runtime::Error{
                let h=runtime::spawn_blocking(->leaf(&mut *n));
                let e=match h.join(){Err(e)=>{e},
                    Ok(v)=>{print(v);runtime::Error::LaunchFailed}};return e;}
            fn relay(n:&mut Int)->runtime::Error{return use_error(n);}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(1);
                let e=relay(&mut n);n=3;drop(->n);
                match e{runtime::Error::LaunchFailed=>{print(7);}}}
        '''
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'2\n7\n')
        self.assertEqual(self.run_c_oracle(self.reject_blocking(code)).stdout,'7\n')
        with self.assertRaisesRegex(Error,'emprunt|réserv|exclus'):
            verify_program(source.replace('let e=match h.join()', 'n.set(4);let e=match h.join()'))

    def test_drop_consumes_only_the_error_binding(self):
        for asynchronous in (False,True):
            prefix='async ' if asynchronous else ''
            body='''fn check()->Int{let e=runtime::Error::LaunchFailed;
                let alias=e;drop(->e);drop(->runtime::Error::LaunchFailed);
                match alias{runtime::Error::LaunchFailed=>{return 7;}}}
            '''
            call=('let h=runtime::spawn(->check());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}'
                  if asynchronous else 'let n=check();print(n);')
            source=prefix+body+'fn main(){'+call+'}'
            with self.subTest(asynchronous=asynchronous):
                self.assertEqual(self.native(source).stdout,'7\n')
            for misuse in ('match e',):
                with self.subTest(asynchronous=asynchronous,misuse=misuse),self.assertRaises(Error):
                    verify_program(source.replace('match alias',misuse))
            with self.subTest(asynchronous=asynchronous,outer_drop=True),self.assertRaises(Error):
                verify_program(source.replace('drop(->e);','{drop(->e);}'))


if __name__=='__main__':unittest.main()
