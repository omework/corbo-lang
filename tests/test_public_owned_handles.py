"""Owned public handle payloads retain result storage, not unrelated captures."""
from pathlib import Path
import itertools
import unittest

from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_runtime
from scheduler_faults import inject_submission_failure


class PublicOwnedHandleTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, message, **options):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaisesRegex(Error, message):
                check(source, **options)

    def test_initial_owned_contract_example(self):
        source = (Path(__file__).resolve().parents[1]/'validation/open-public-handle-owned-contract.crb').read_text()
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')
        self.rejected(source.replace('Handle<A<Int>>', 'Handle<A<String>>'), 'handle .*attendu|type')

    @staticmethod
    def declarations(typ, argument, initialize):
        return f'''async fn work(p:&mut Pool<{typ}>,scratch:->Int)-><-{typ}{{
                drop(->scratch);let mut value=p.new({argument});{initialize}yield;return <-value;}}
            fn launch(p:&mut Pool<{typ}>,scratch:->Int)-><-runtime::Handle<A<{typ}>>{{
                let h=runtime::spawn(->work(p,->scratch));return <-h;}}
            fn relay(h:->runtime::Handle<A<{typ}>>)-><-runtime::Handle<A<{typ}>>{{return <-h;}}
            fn again(h:->runtime::Handle<A<{typ}>>)-><-runtime::Handle<A<{typ}>>{{
                let next=relay(->h);return <-next;}}'''

    def test_result_outlives_unrelated_capture_pool_for_each_owned_type(self):
        for typ, argument, initialize, read, expected in (
            ('Int', '7', '', '*result', '7'),
            ('String', '', 'value.push_str("é");', 'result.byte_len()', '2'),
            ('Vector<Int>', '', 'value.push(7);', 'result[0]', '7'),
            ('Vector<u8>', '', 'let byte:u8=7;value.push(byte);', 'result[0] as Int', '7'),
        ):
            declarations = self.declarations(typ, argument, initialize)
            main = f'''fn main(){{let mut p=pool<{typ}>(1);let result={{
                    let mut scratch_pool=pool<Int>(1);let scratch=scratch_pool.new(123);
                    let h=launch(&mut p,->scratch);let next=again(->h);
                    let result=match next.join(){{Ok(value)=>{{<-value}},
                        Err(_)=>{{let mut value=p.new({argument});{initialize}<-value}}}};
                    let reused=scratch_pool.new(9);print(*reused);<-result}};
                print({read});drop(->result);let reused=p.new({argument});drop(->reused);}}'''
            source = declarations+main
            with self.subTest(typ=typ):
                verify_program(source)
                code = compile_source(source)
                run = self.run_c_oracle(code)
                self.assertEqual(run.stdout, '9\n'+expected+'\n')
                self.assertEqual(run.stderr.count('destroy scratch=123'), 1)
                failed = self.run_c_oracle(inject_submission_failure(code, asynchronous=False, at=1))
                self.assertEqual(failed.stdout, '9\n'+expected+'\n')
                self.assertEqual(failed.stderr.count('destroy scratch=123'), 1)
                self.rejected(source.replace('let next=again(->h);',
                    f'let early=p.new({argument});drop(->early);let next=again(->h);'), 'emprunt|capture|pool incompatible')

    def test_opaque_contract_preserves_result_source_through_join_helper(self):
        declarations = self.declarations('Int', '7', '') + '''
            fn finish(h:->runtime::Handle<A<Int>>,backup:&mut Pool<Int>)-><-Int{
                match h.join(){Ok(value)=>{return <-value;},
                    Err(_)=>{let value=backup.new(99);return <-value;}}}'''
        interface = verify_program(declarations)
        for short_result_pool in (False, True):
            pool = 'let mut p=pool<Int>(1);'
            script = 'let mut backup=pool<Int>(1);' + ('' if short_result_pool else pool)
            script += 'let result={' + (pool if short_result_pool else '') + '''
                let mut scratch_pool=pool<Int>(1);let scratch=scratch_pool.new(123);
                let h=launch(&mut p,->scratch);let next=again(->h);
                let result=finish(->next,&mut backup);<-result};print(*result);'''
            checker = Compiler()
            checker.contract_calls = True
            checker.function_contracts = interface.function_contracts
            nodes = Parser(script).parse()
            checker.index(nodes)
            with self.subTest(short_result_pool=short_result_pool):
                if short_result_pool:
                    with self.assertRaisesRegex(Error, 'pool|source|survit'):
                        checker.block('root', nodes)
                    self.rejected(declarations+'fn main(){'+script+'}', 'pool|source|survit')
                else:
                    checker.block('root', nodes)
                    self.assertEqual(checker.async_definitions, {})
                    self.assertEqual(self.run_c_oracle(compile_source(declarations+'fn main(){'+script+'}')).stdout, '7\n')

    def test_result_borrow_blocks_drop_and_legacy_reset(self):
        source = '''async fn work(p:&mut Pool<Int>)-><-Int{let n=p.new(7);yield;return <-n;}
            fn relay(h:->runtime::Handle<A<Int>>)-><-runtime::Handle<A<Int>>{return <-h;}
            fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));let next=relay(->h);
                match next.join(){Ok(n)=>{let view=&n;CHECK print(*view);drop(->n);},Err(_)=>{print(99);}}
                let reused=p.new(11);print(*reused);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK', ''))).stdout, '7\n11\n')
        self.rejected(source.replace('CHECK', 'drop(->n);'), 'emprunt')
        self.rejected(source.replace('CHECK', 'p.reset();'), 'reset interdit', allow_legacy_reset=True)
        self.rejected(source.replace('CHECK', '').replace('Ok(n)=>{let view=&n; print(*view);drop(->n);}',
                                                        'Ok(_)=>{}'), 'motif _|propriétaire|usage explicite')

    def test_nested_result_keeps_two_error_levels_and_result_pool(self):
        source = '''async fn leaf(p:&mut Pool<Int>)-><-Int{let n=p.new(7);yield;return <-n;}
            async fn work(p:&mut Pool<Int>)-><-Result<A<Int>,runtime::Error>{
                let h=runtime::spawn(->leaf(p));let result=h.await;return <-result;}
            fn relay(h:->runtime::Handle<Result<A<Int>,runtime::Error>>)
                -><-runtime::Handle<Result<A<Int>,runtime::Error>>{return <-h;}
            fn again(h:->runtime::Handle<Result<A<Int>,runtime::Error>>)
                -><-runtime::Handle<Result<A<Int>,runtime::Error>>{let next=relay(->h);return <-next;}
            fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));let next=again(->h);
                let result=next.join();CHECK
                match result{Ok(inner)=>{match inner{Ok(n)=>{print(*n);},Err(_)=>{print(98);}}},
                    Err(_)=>{print(99);}}
                let reused=p.new(11);print(*reused);}'''
        code = compile_source(source.replace('CHECK', ''))
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '7\n11\n')
        self.assertEqual(run.stderr.count('destroy n=7'), 1)
        for asynchronous, expected in ((False, '99\n11\n'), (True, '98\n11\n')):
            with self.subTest(asynchronous=asynchronous):
                failed = inject_submission_failure(code, asynchronous=asynchronous, at=1)
                self.assertEqual(self.run_c_oracle(failed).stdout, expected)
        self.rejected(source.replace('CHECK', 'p.reset();'), 'reset interdit', allow_legacy_reset=True)

    def test_wrong_owned_payload_rejected_even_if_only_dropped(self):
        source = '''async fn work(p:&mut Pool<Int>)-><-Int{let n=p.new(7);yield;return <-n;}
            fn finish(h:->runtime::Handle<A<Int>>){match h.join(){Ok(n)=>{drop(->n);},Err(_)=>{}}}
            fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));finish(->h);
                let reused=p.new(11);print(*reused);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '11\n')
        self.rejected(source.replace('Handle<A<Int>>', 'Handle<A<String>>'), 'handle .*attendu')
        self.rejected(source.replace('Handle<A<Int>>', 'Handle<Int>'), 'handle .*attendu|drop.*allocation')

    def test_lifetime_model_distinguishes_pending_and_joined_storage(self):
        declarations = '''async fn first(p:&mut Pool<Int>,scratch:&mut Pool<String>)-><-Int{
                let text=scratch.new();drop(->text);let n=p.new(7);yield;return <-n;}
            async fn second(scratch:&mut Pool<String>,p:&mut Pool<Int>)-><-Int{
                let text=scratch.new();drop(->text);let n=p.new(9);yield;return <-n;}
            fn choose(flag:bool,a:&mut Pool<Int>,b:&mut Pool<Int>,scratch:&mut Pool<String>)
                -><-runtime::Handle<A<Int>>{
                let h=if flag{let one=runtime::spawn(->first(a,scratch));<-one}
                    else{let two=runtime::spawn(->second(scratch,b));<-two};return <-h;}
            fn relay(h:->runtime::Handle<A<Int>>)-><-runtime::Handle<A<Int>>{return <-h;}'''
        # Independent lifetime oracle: the pending execution can touch all
        # three pools; its result can come only from a or b (or outer backup).
        pools = ('a', 'b', 'scratch')
        declarations_by_pool = {
            name: f'let mut {name}=pool<{"String" if name == "scratch" else "Int"}>(1);'
            for name in pools
        }
        join = '''let value=match next.join(){Ok(n)=>{<-n},
            Err(_)=>{let n=backup.new(99);<-n}};'''
        for joined in (False, True):
            required = {'a', 'b'} if joined else set(pools)
            for outer_flags in itertools.product((False, True), repeat=3):
                outer = {pool for pool, durable in zip(pools, outer_flags) if durable}
                allowed = required <= outer
                prefix = 'let mut backup=pool<Int>(1);' + ''.join(declarations_by_pool[p] for p in pools if p in outer)
                block = ''.join(declarations_by_pool[p] for p in pools if p not in outer)
                block += 'let h=choose(FLAG,&mut a,&mut b,&mut scratch);let next=relay(->h);'
                main = prefix + ('let result={'+block+join+'<-value};print(*result);' if joined else
                                 'let next={'+block+'<-next};'+join+'print(*value);')
                for flag, expected in (('true', '7\n'), ('false', '9\n')):
                    source = declarations+'fn main(){'+main.replace('FLAG', flag)+'}'
                    with self.subTest(joined=joined, outer=sorted(outer), flag=flag):
                        if allowed:
                            verify_program(source)
                            self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, expected)
                        else:
                            self.rejected(source, 'source|pool|survit|locale|durée')

    def test_transferred_allocation_keeps_identity_through_public_factories(self):
        source = '''async fn work(value:->Int)-><-Int{yield;return <-value;}
            fn start(value:->Int)-><-runtime::Handle<A<Int>>{
                let h=runtime::spawn(->work(->value));return <-h;}
            fn relay(h:->runtime::Handle<A<Int>>)-><-runtime::Handle<A<Int>>{return <-h;}
            fn main(){let mut p=pool<Int>(1);let data=p.new(7);address(data);
                let h=start(->data);let next=relay(->h);
                match next.join(){Ok(value)=>{address(value);print(*value);drop(->value);},Err(_)=>{print(99);}}
                let reused=p.new(11);address(reused);print(*reused);}'''
        code = compile_source(source)
        run = self.run_c_oracle(code)
        before, returned, value, reused, later = run.stdout.splitlines()
        self.assertEqual((returned, reused, value, later), (before, before, '7', '11'))
        self.assertEqual(run.stderr.count('destroy data=7'), 1)
        self.rejected(source.replace('let next=relay(->h);', 'print(*data);let next=relay(->h);'), 'plus utilisable')
        failed = self.run_c_oracle(inject_submission_failure(code, asynchronous=False, at=1))
        before, error, reused, later = failed.stdout.splitlines()
        self.assertEqual((error, reused, later), ('99', before, '11'))
        self.assertEqual(failed.stderr.count('destroy data=7'), 1)

    def test_typed_owned_results_cross_wait_helper_and_backup_pool(self):
        for typ, argument, initialize, read, expected in (
            ('Int', '7', '', '*result', '7'),
            ('String', '', 'value.push_str("é");', 'result.byte_len()', '2'),
            ('Vector<Int>', '', 'value.push(7);', 'result[0]', '7'),
            ('Vector<u8>', '', 'let byte:u8=7;value.push(byte);', 'result[0] as Int', '7'),
        ):
            declarations = self.declarations(typ, argument, initialize) + f'''
                fn finish(h:->runtime::Handle<A<{typ}>>,backup:&mut Pool<{typ}>)-><-{typ}{{
                    match h.join(){{Ok(value)=>{{return <-value;}},
                        Err(_)=>{{let mut value=backup.new({argument});{initialize}return <-value;}}}}}}'''
            main = f'''fn main(){{let mut p=pool<{typ}>(1);let mut backup=pool<{typ}>(1);
                let result={{let mut scratch_pool=pool<Int>(1);let scratch=scratch_pool.new(123);
                    let h=launch(&mut p,->scratch);let next=again(->h);
                    let value=finish(->next,&mut backup);<-value}};
                print({read});drop(->result);
                let reused=p.new({argument});drop(->reused);let other=backup.new({argument});drop(->other);}}'''
            source = declarations + main
            with self.subTest(typ=typ):
                code = compile_source(source)
                self.assertEqual(self.run_c_oracle(code).stdout, expected+'\n')
                self.assertEqual(self.run_c_oracle(inject_submission_failure(
                    code, asynchronous=False, at=1)).stdout, expected+'\n')
                short = source.replace(f'let mut backup=pool<{typ}>(1);', '').replace(
                    'let result={', f'let result={{let mut backup=pool<{typ}>(1);').replace(
                    f'let other=backup.new({argument});drop(->other);', '')
                self.rejected(short, 'pool|source|survit')


if __name__ == '__main__':
    unittest.main()
