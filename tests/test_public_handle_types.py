"""Public handle result annotations preserve the concrete lifetime contract."""
import unittest

from crust import Error, compile_source, verify_program
import test_async_runtime


class PublicHandleTypeTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, message):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaisesRegex(Error, message):
                check(source)

    def test_result_type_matrix_sync_and_async(self):
        cases = [
            ('Int', '->Int', 'return 7;', 'Ok(v)=>{print(v);}', '7\n'),
            ('Bool', '->Bool', 'return true;', 'Ok(v)=>{if v {print(7);}else{print(9);}}', '7\n'),
            ('u8', '->u8', 'let text="A";return text[0];', 'Ok(v)=>{print(v as Int);}', '65\n'),
            ('Void', '', 'return;', 'Ok(())=>{print(7);}', '7\n'),
            ('&str', '->&str', 'return "bonjour";', 'Ok(v)=>{print(v);}', 'bonjour\n'),
            ('[Int;2]', '->[Int;2]', 'let values=[7,9];return <-values;', 'Ok(v)=>{print(v[0]);}', '7\n'),
        ]
        for typ, result, body, arm, output in cases:
            for asynchronous in (False, True):
                source = f'async fn leaf(){result}{{yield;{body}}}'
                code = f'''let h:runtime::Handle<{typ}>=runtime::spawn(->leaf());
                    match h.{'await' if asynchronous else 'join()'}{{{arm},Err(_)=>{{print(99);}}}}'''
                source += ('async fn parent(){' + code + '}' +
                           'fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(())=>{},Err(_)=>{print(99);}}}'
                           if asynchronous else 'fn main(){'+code+'}')
                with self.subTest(typ=typ, asynchronous=asynchronous):
                    self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, output)
                    wrong = 'Bool' if typ != 'Bool' else 'Int'
                    self.rejected(source.replace(f'runtime::Handle<{typ}>', f'runtime::Handle<{wrong}>'),
                                  'annotation de handle')

    def test_different_frames_moves_and_wait_obligation(self):
        source = '''async fn first()->Int{yield;return 7;}
            async fn second()->Int{let a=[8,9];yield;return a[1];}
            async fn parent(){
                let a:runtime::Handle<Int>=runtime::spawn(->first());
                let b:runtime::Handle<Int>=runtime::spawn(->second());
                let moved:runtime::Handle<Int>= <-a;
                match moved.await{Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                match b.await{Ok(n)=>{print(n);},Err(_)=>{print(99);}}
            }
            fn main(){let h:runtime::Handle<Void>=runtime::spawn(->parent());
                match h.join(){Ok(())=>{},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n9\n')
        self.rejected(source.replace('match b.await{Ok(n)=>{print(n);},Err(_)=>{print(99);}}', ''),
                      'attente requise')
        self.rejected(source.replace('match moved.await', 'match a.await'), 'consomm|transfér|inconn|déplac')
        self.rejected('async fn leaf()->Int{return 7;} fn main(){let h:runtime::Handle<Int>=leaf();drop(->h);}',
                      'tâche inactive')

    def test_borrowed_result_keeps_target_reserved(self):
        source = '''async fn leaf(v:&mut Int)->&mut Int{yield;return v;}
            fn main(){let mut p=pool<Int>(1);let mut data=p.new(7);
                let h:runtime::Handle<&mut Int>=runtime::spawn(->leaf(&mut data));
                match h.join(){Ok(view)=>{*view=9;},Err(_)=>{}}
                print(*data);drop(->data);let again=p.new(11);print(*again);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '9\n11\n')
        self.rejected(source.replace('match h.join()', 'print(*data);match h.join()'), 'emprunt|capture')
        self.rejected(source.replace('match h.join()', 'drop(->data);match h.join()'), 'emprunt|capture')
        self.rejected(source.replace('Handle<&mut Int>', 'Handle<&Int>'), 'annotation de handle')

    def test_scalar_result_does_not_erase_live_capture(self):
        source = '''async fn leaf(v:&mut Int)->Int{yield;*v=9;return *v;}
            fn main(){let mut p=pool<Int>(1);let mut data=p.new(7);
                let h:runtime::Handle<Int>=runtime::spawn(->leaf(&mut data));
                match h.join(){Ok(value)=>{print(value);},Err(_)=>{}}
                print(*data);drop(->data);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '9\n9\n')
        self.rejected(source.replace('match h.join()', 'print(*data);match h.join()'), 'emprunt|capture')
        self.rejected(source.replace('match h.join()', 'drop(->data);match h.join()'), 'emprunt|capture')

    def test_owned_result_keeps_pool_and_destroys_once(self):
        source = '''async fn leaf(p:&mut Pool<Int>)-><-Int{let n=p.new(7);yield;return <-n;}
            fn main(){let mut p=pool<Int>(1);
                let h:runtime::Handle<A<Int>>=runtime::spawn(->leaf(&mut p));
                match h.join(){Ok(n)=>{print(*n);},Err(_)=>{print(99);}}
                let again=p.new(11);print(*again);}'''
        run = self.run_c_oracle(compile_source(source))
        self.assertEqual(run.stdout, '7\n11\n')
        self.assertEqual(run.stderr.count('destroy n=7'), 1)
        self.rejected(source.replace('Handle<A<Int>>', 'Handle<Int>'), 'annotation de handle')
        self.rejected(source.replace('match h.join()', 'let busy=p.new(9);print(*busy);match h.join()'),
                      'pool incompatible|capture|emprunt')

    def test_control_flow_and_launch_variants(self):
        expressions = (
            'runtime::spawn(->leaf())',
            'runtime::spawn_blocking(->leaf())',
            'runtime::thread({7})',
            '{let h=runtime::spawn(->leaf());<-h}',
            'loop{let h=runtime::spawn(->leaf());break <-h;}',
            'if true {let h=runtime::spawn(->leaf());<-h} else {let h=runtime::spawn(->leaf());<-h}',
        )
        for expression in expressions:
            for asynchronous in (False, True):
                source = 'async fn leaf()->Int{yield;return 7;}'
                body = f'''let h:runtime::Handle<Int>={expression};
                    match h.{'await' if asynchronous else 'join()'}{{Ok(n)=>{{print(n);}},Err(_)=>{{print(99);}}}}'''
                source += ('async fn parent(){' + body + '}' +
                           'fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(())=>{},Err(_)=>{print(99);}}}'
                           if asynchronous else 'fn main(){'+body+'}')
                with self.subTest(expression=expression, asynchronous=asynchronous):
                    self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')
                    self.rejected(source.replace('runtime::Handle<Int>', 'runtime::Handle<Bool>'),
                                  'annotation de handle')

    def test_nested_result_payload_is_distinct_from_outer_launch_result(self):
        source = '''async fn child()->Int{yield;return 7;}
            async fn leaf()->Result<Int,runtime::Error>{
                let h=runtime::spawn(->child());return h.await;}
            fn main(){let h:runtime::Handle<Result<Int,runtime::Error>>=runtime::spawn(->leaf());
                match h.join(){Ok(inner)=>{
                    match inner{Ok(n)=>{print(n);},Err(_)=>{print(98);}}
                },Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')
        self.rejected(source.replace('runtime::Handle<Result<Int,runtime::Error>>', 'runtime::Handle<Int>'),
                      'annotation de handle')


if __name__ == '__main__':
    unittest.main()
