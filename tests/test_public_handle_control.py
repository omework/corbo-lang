"""Different frames share a public handle type, never their capture identities."""
import unittest

from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_runtime


class PublicHandleControlTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, message):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaisesRegex(Error, message):
                check(source)

    @staticmethod
    def factory(construct):
        a = 'let h=runtime::spawn(->first(a,s));'
        b = 'let h=runtime::spawn(->second(s,b));'
        before = ''
        if construct == 'if':
            body = f'if flag {{{a} <-h}} else {{{b} <-h}}'
        elif construct == 'loop':
            before = 'let mut i=0;'
            body = f'''loop{{if i==0{{i=1;continue;}}
                if flag{{{a} break <-h;}} {b} break <-h;}}'''
        else:
            before = '''let mut choices=pool<Choice>(1);
                let choice=if flag{let c=new(choices) Choice.A; <-c}
                    else{let c=new(choices) Choice.B; <-c};'''
            subject = {'match': '(-> choice)', 'shared_match': '&choice', 'mutable_match': '&mut choice'}[construct]
            if construct == 'mutable_match':
                before = before.replace('let choice=', 'let mut choice=')
            body = f'match {subject}{{Choice.A=>{{{a} <-h}},Choice.B=>{{{b} <-h}}}}'
        return f'''enum Choice{{A,B}}
            async fn first(x:&mut Int,s:&Int)->Int{{yield;*x=*x+*s;return *x;}}
            async fn second(s:&Int,y:&mut Int)->Int{{let padding=[1,2];yield;*y=*y+*s;return *y+padding[0];}}
            fn choose(flag:bool,a:&mut Int,b:&mut Int,s:&Int)-><-runtime::Handle<Int>{{
                {before} let h={body};return <-h;}}
            fn finish(h:->runtime::Handle<Int>)->Int{{
                match h.join(){{Ok(n)=>{{return n;}},Err(_)=>{{return 99;}}}}}}'''

    @staticmethod
    def caller(flag, before=''):
        return f'''let mut p=pool<Int>(3);let mut a=p.new(7);let mut b=p.new(9);let s=p.new(1);
            let h=choose({flag},&mut a,&mut b,&s);print(*s);{before}
            print(finish(->h));print(*a);print(*b);'''

    def test_control_results_union_captures_and_keep_permissions(self):
        for construct in ('if', 'loop', 'match', 'shared_match', 'mutable_match'):
            declarations = self.factory(construct)
            for flag, output in (('true', '1\n8\n8\n9\n'), ('false', '1\n11\n7\n10\n')):
                source = declarations+'fn main(){'+self.caller(flag)+'}'
                with self.subTest(construct=construct, flag=flag):
                    verify_program(source)
                    self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, output)
            for access in ('print(*a);', 'print(*b);', 'drop(->s);'):
                with self.subTest(construct=construct, access=access):
                    self.rejected(declarations+'fn main(){'+self.caller('true', access)+'}', 'emprunt|capture')

    def test_control_result_contracts_need_no_task_bodies_at_call_site(self):
        for construct in ('if', 'loop', 'match', 'shared_match', 'mutable_match'):
            interface = verify_program(self.factory(construct))
            for access in ('', 'print(*a);', 'print(*b);'):
                checker = Compiler()
                checker.contract_calls = True
                checker.function_contracts = interface.function_contracts
                nodes = Parser(self.caller('true', access)).parse()
                checker.index(nodes)
                with self.subTest(construct=construct, access=access):
                    if access:
                        with self.assertRaisesRegex(Error, 'emprunt|capture'):
                            checker.block('root', nodes)
                    else:
                        checker.block('root', nodes)
                        self.assertEqual(checker.async_definitions, {})

    def test_distinct_result_types_remain_incompatible(self):
        for construct in ('if', 'loop', 'match', 'shared_match', 'mutable_match'):
            source = self.factory(construct).replace('second(s:&Int,y:&mut Int)->Int',
                                                     'second(s:&Int,y:&mut Int)->Bool').replace(
                'return *y+padding[0];', 'print(padding[0]);return true;')
            with self.subTest(construct=construct):
                self.rejected(source, 'même type|handle .*attendu')

    def test_owned_capture_sources_survive_control_and_opaque_relay(self):
        for construct in ('if', 'loop', 'match', 'shared_match', 'mutable_match'):
            declarations = self.factory(construct)
            declarations = '''enum Choice{A,B}
                async fn first(text:->String)->Int{yield;return text.byte_len();}
                async fn second(text:->String)->Int{yield;return text.byte_len()+1;}
                fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
                ''' + declarations[declarations.index('fn choose'):]
            declarations = declarations.replace('a:&mut Int,b:&mut Int,s:&Int',
                                                'a:&mut Pool<String>,b:&mut Pool<String>')
            declarations = declarations.replace('let h=runtime::spawn(->first(a,s));',
                'let mut text=a.new();text.push_str("abc");let h=runtime::spawn(->first(->text));')
            declarations = declarations.replace('let h=runtime::spawn(->second(s,b));',
                'let mut text=b.new();text.push_str("abcd");let h=runtime::spawn(->second(->text));')
            interface = verify_program(declarations)
            for flag, expected in (('true', '3\n0\n0\n'), ('false', '5\n0\n0\n')):
                script = f'''let mut p=pool<String>(1);let mut q=pool<String>(1);
                    let h=choose({flag},&mut p,&mut q);let next=relay(->h);print(finish(->next));
                    let x=p.new();let y=q.new();print(x.byte_len());print(y.byte_len());'''
                with self.subTest(construct=construct, flag=flag):
                    self.assertEqual(self.run_c_oracle(compile_source(declarations+'fn main(){'+script+'}')).stdout,
                                     expected)
            for short_pool in (False, True):
                pool = 'let mut q=pool<String>(1);'
                script = 'let mut p=pool<String>(1);' + ('' if short_pool else pool) + 'let h={'
                script += (pool if short_pool else '') + '''
                    let selected=choose(true,&mut p,&mut q);let next=relay(->selected);<-next};print(finish(->h));'''
                checker = Compiler()
                checker.contract_calls = True
                checker.function_contracts = interface.function_contracts
                nodes = Parser(script).parse()
                checker.index(nodes)
                with self.subTest(construct=construct, short_pool=short_pool):
                    if short_pool:
                        with self.assertRaisesRegex(Error, 'pool|source|survit'):
                            checker.block('root', nodes)
                    else:
                        checker.block('root', nodes)

    def test_if_handles_return_fixed_arrays_from_distinct_frames(self):
        source = '''async fn first()->[Int;2]{let a=[7,8];yield;return <-a;}
            async fn second()->[Int;2]{let b=[9,10];return <-b;}
            fn choose(flag:bool)-><-runtime::Handle<[Int;2]>{
                let h=if flag{let one=runtime::spawn(->first());<-one}
                    else{let two=runtime::spawn(->second());<-two};return <-h;}
            fn main(){let h=choose(FLAG);match h.join(){
                Ok(a)=>{print(a[0]);print(a[1]);},Err(_)=>{print(99);}}}'''
        for flag, expected in (('true', '7\n8\n'), ('false', '9\n10\n')):
            with self.subTest(flag=flag):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('FLAG', flag))).stdout, expected)


if __name__ == '__main__':
    unittest.main()
