"""RT5/RT6: typed nonowning join results survive synchronous contracts."""
from pathlib import Path
import unittest
import test_spawn_blocking
import test_type_features
from crust import Compiler, Error, Parser, compile_source, verify_program


class PlainJoinContractTests(unittest.TestCase):
    native=test_type_features.TypeFeatureTests.native
    run_c_oracle=test_spawn_blocking.SpawnBlockingTests.run_c_oracle
    reject_blocking=test_spawn_blocking.SpawnBlockingTests.reject_blocking
    rejecting_callback=test_spawn_blocking.SpawnBlockingTests.rejecting_callback

    @staticmethod
    def case(payload):
        declaration={
            'Int':'async fn leaf()->Int{yield;return 17;}',
            'Bool':'async fn leaf()->Bool{yield;return true;}',
            'u8':'async fn leaf()->u8{yield;let b:u8=255;return b;}',
            'char':'async fn leaf(c:char)->char{yield;return c;}',
            '()':'async fn leaf(){yield;}',
            'runtime::Error':'async fn leaf()->runtime::Error{yield;return runtime::Error::LaunchFailed;}',
        }[payload]
        success={
            'Int':('Ok(v)','print(v);','17'),
            'Bool':('Ok(v)','if v{print(1);}else{print(0);}','1'),
            'u8':('Ok(v)','print(v as Int);','255'),
            'char':('Ok(v)','print(v);','é'),
            '()':('Ok(())','print(7);','7'),
            'runtime::Error':('Ok(v)','match v{runtime::Error::LaunchFailed=>{print(5);}}','5'),
        }[payload]
        return declaration,success

    def test_all_plain_payloads_through_contracts_with_both_launch_outcomes(self):
        for payload in ('Int','Bool','u8','char','()','runtime::Error'):
            declaration,(pattern,body,expected)=self.case(payload)
            typ=f'Result<{payload},runtime::Error>'
            functions=f'''fn relay(r:{typ})->{typ}{{return r;}}
                fn again(r:{typ})->{typ}{{return relay(r);}}'''
            call='leaf(c)' if payload=='char' else 'leaf()'
            statements=f'''let h=runtime::spawn_blocking(->{call});
                let received:{typ}=again(h.join());
                let copied=received;
                match copied{{{pattern}=>{{{body}}},Err(e)=>{{match e{{runtime::Error::LaunchFailed=>{{print(99);}}}}}}}}
                drop(->received);'''
            if payload=='char':
                statements='match char::from_str("é"){Ok(c)=>{'+statements+'},Err(_)=>{print(998);}}'
            source=declaration+functions+'fn main(){'+statements+'}'
            compiler=Compiler();code=compiler.compile(Parser(source).parse())
            self.assertIn('relay',compiler.verified_functions)
            self.assertIn('again',compiler.verified_functions)
            self.assertIn('relay',compiler.body_call_contracts['again'])
            for failed in (False,True):
                with self.subTest(payload=payload,failed=failed):
                    output=self.run_c_oracle(self.reject_blocking(code) if failed else code).stdout
                    self.assertEqual(output,('99' if failed else expected)+'\n')

    def test_recorded_contract_gap_runs(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-runtime-result-contract.crb').read_text()
        self.assertEqual(self.native(source).stdout,'7\n')

    def test_result_through_if_loop_assignment_and_drop(self):
        source='''async fn leaf(n:Int)->Int{yield;return n;}
            fn wait(n:Int)->Result<Int,runtime::Error>{let h=runtime::spawn_blocking(->leaf(n));return h.join();}
            fn choose(flag:Int)->Result<Int,runtime::Error>{
                let r=if flag==0{wait(10)}else{wait(20)};
                let out=loop{break r;};return out;}
            fn main(){let mut first:Result<Int,runtime::Error>=choose(0);
                match first{Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                first=choose(1);
                match first{Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                drop(->first);drop(->choose(0));}
        '''
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'10\n20\n')
        self.assertEqual(self.run_c_oracle(self.reject_blocking(code)).stdout,'99\n99\n')
        with self.assertRaises(Error):
            verify_program(source.replace('drop(->first);','drop(->first);let reuse=first;drop(->reuse);'))

    def test_payload_type_is_checked_in_every_contract_and_annotation(self):
        prefix='''async fn leaf()->Int{return 7;}
            fn wait()->Result<Int,runtime::Error>{let h=runtime::spawn(->leaf());return h.join();}'''
        for wrong in ('Bool','u8','char','()','runtime::Error','A<Int>','&Int','&mut Int'):
            typ=f'Result<{wrong},runtime::Error>'
            for statement in (f'let r:{typ}=wait();drop(->r);',f'let r=wrong(wait());drop(->r);'):
                source=prefix+f'fn wrong(r:{typ})->{typ}{{return r;}}fn main(){{'+statement+'}'
                with self.subTest(wrong=wrong,statement=statement),self.assertRaises(Error):verify_program(source)
        for body in ('wait();','let _=wait();','let unused=wait();',
                     'let mut r=wait();r=wait();drop(->r);'):
            with self.subTest(body=body),self.assertRaisesRegex(Error,'usage explicite|faillible|receveur explicitement'):
                verify_program(prefix+'fn main(){'+body+'}')

    def test_function_signatures_do_not_require_a_live_runtime_instance(self):
        self.assertEqual(self.native('''fn relay(r:Result<Int,runtime::Error>)->Result<Int,runtime::Error>{return r;}
            fn main(){print(7);}''').stdout,'7\n')

    def test_plain_results_capture_by_value_and_survive_suspension(self):
        for payload in ('Int','Bool','u8','char','()','runtime::Error'):
            declaration,(pattern,body,expected)=self.case(payload)
            typ=f'Result<{payload},runtime::Error>'
            inspect=f'''async fn inspect(r:{typ})->Int{{yield;
                {{let temporary=r;drop(->temporary);}}
                let temporary=3;print(temporary);
                let copy=r;drop(->r);yield;
                match copy{{{pattern}=>{{{body}return 7;}},
                    Err(error)=>{{match error{{runtime::Error::LaunchFailed=>{{print(98);}}}}return 99;}}}}
            }}'''
            call='leaf(c)' if payload=='char' else 'leaf()'
            statements=f'''let h=runtime::spawn_blocking(->{call});let r:{typ}=h.join();
                let child=runtime::spawn(->inspect(r));drop(->r);
                match child.join(){{Ok(v)=>{{print(v);}},Err(_)=>{{print(998);}}}}'''
            if payload=='char':
                statements='match char::from_str("é"){Ok(c)=>{'+statements+'},Err(_)=>{print(997);}}'
            code=compile_source(declaration+inspect+'fn main(){'+statements+'}')
            for failed in (False,True):
                with self.subTest(payload=payload,failed=failed):
                    out=self.run_c_oracle(self.reject_blocking(code) if failed else code).stdout
                    self.assertEqual(out,'3\n98\n99\n' if failed else f'3\n{expected}\n7\n')

    def test_async_join_annotation_assignment_alias_and_loop(self):
        source='''async fn leaf(n:Int)->Int{yield;return n;}
            async fn inspect(r:Result<Int,runtime::Error>)->Int{
                yield;match r{Ok(n)=>{return n;},Err(_)=>{return 99;}}}
            async fn parent()->Int{
                let h=runtime::spawn_blocking(->leaf(17));
                let mut r:Result<Int,runtime::Error>=h.await;
                let copy=r;let first=inspect(copy).await;print(first);
                r=if true{copy}else{r};
                let selected=loop{yield;break r;};drop(->r);
                let second=inspect(selected).await;return second;}
            fn main(){let h=runtime::spawn(->parent());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(998);}}}
        '''
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'17\n17\n')
        self.assertEqual(self.run_c_oracle(self.reject_blocking(code)).stdout,'99\n99\n')
        for old,new in (
                ('let selected=loop','drop(->r);let selected=loop'),
                ('let mut r:Result<Int,runtime::Error>','let mut r:Result<u8,runtime::Error>'),
                ('r=if true{copy}else{r};','r=5;'),
                ('let selected=loop{yield;break r;};drop(->r);',
                 'let ignored=loop{break copy;};let selected=r;drop(->r);')):
            with self.subTest(change=new),self.assertRaises(Error):verify_program(source.replace(old,new))

    def test_async_cannot_reinterpret_result_as_payload_or_int_reference(self):
        prefix='''async fn read(n:&Int)->Int{return *n;}
            async fn edit(n:&mut Int){n.set(9);}'''
        for misuse in ('let n:Int=r;', 'let n=r+1;', 'let n=r as Int;',
                       'let t=read(&r);drop(->t);','let t=edit(&mut r);drop(->t);',
                       'drop(->r);match r{Ok(n)=>{print(n);},Err(_)=>{}}'):
            source=prefix+'async fn bad(mut r:Result<Int,runtime::Error>){'+misuse+'}fn main(){}'
            with self.subTest(misuse=misuse),self.assertRaises(Error):verify_program(source)

    def test_async_capture_checks_payload_type_at_the_call(self):
        source='''async fn leaf()->Int{return 255;}
            async fn octet(r:Result<u8,runtime::Error>)->Int{
                match r{Ok(v)=>{return v as Int;},Err(_)=>{return 99;}}}
            async fn parent()->Int{let h=runtime::spawn(->leaf());let r=h.await;
                let result=octet(r).await;return result;}
            fn main(){}'''
        with self.assertRaisesRegex(Error,'Result<u8,runtime::Error>'):
            verify_program(source)
        # The consumer body is valid independently; only the call is wrong.
        verify_program(source.replace('async fn leaf()->Int{return 255;}',
                                      'async fn leaf()->u8{let n:u8=255;return n;}'))

    def test_adjacent_type_assignment_preserves_comparison_and_parser_rewind(self):
        source='''async fn leaf()->Int{return 7;}
            fn wait()->Result<Int,runtime::Error>{let h=runtime::spawn(->leaf());return h.join();}
            fn main(){let selected=if 2>=1 {
                let r:Result<Int,runtime::Error>=wait();r
            }else{wait()};
            match selected{Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.native(source).stdout,'7\n')
        self.assertEqual(self.native(source.replace('>=wait()', '> = wait()')).stdout,'7\n')

    def test_borrowed_and_owned_join_cannot_enter_a_plain_contract(self):
        for declaration, argument in (
                ('async fn leaf(n:&Int)->&Int{return n;}', '&n'),
                ('async fn leaf(n:&mut Int)->&mut Int{return n;}', '&mut n'),
                ('async fn leaf(n:->Int)-><-Int{return <- n;}', '->n')):
            for receive in ('let r=relay(h.join());',
                            'let r:Result<Int,runtime::Error>=h.join();'):
                source=declaration+'''fn relay(r:Result<Int,runtime::Error>)->Result<Int,runtime::Error>{return r;}
                    fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);'''+f'''
                    let h=runtime::spawn(->leaf({argument}));{receive}
                    match r{{Ok(v)=>{{print(v);}},Err(_)=>{{}}}}}}'''
                with self.subTest(argument=argument,receive=receive),self.assertRaisesRegex(
                        Error,'attend.*Result|résultat (emprunté|alloué) de join|annotation de Result : type de charge incompatible'):
                    verify_program(source)


if __name__=='__main__':unittest.main()
