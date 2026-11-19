"""Synchronous view contracts called from suspended states."""
from pathlib import Path
import itertools
import unittest
from crust import Error, compile_source, verify_program
import test_async_runtime

class SyncViewBridgeTests(unittest.TestCase):
    run_c_oracle=test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, pattern='emprunt|capture|surviv|durable|durée|plus utilisable|transfert', **options):
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__),self.assertRaisesRegex(Error,pattern):check(source,**options)

    def test_initial_precision_counterexample(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-public-view-result-helper-precision.crb').read_text()
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'temporary\nété\n')
        bad=source.replace('scratch ->;drop(->scratch);','text ->;drop(->text);')
        self.rejected(bad)

    def test_text_local_result_survives_suspension_and_releases_other_capture(self):
        source='''fn pick(v:&str,scratch:&str)->&str{print(scratch);return v;}
            fn relay(v:&str,scratch:&str)->&str{return pick(v,scratch);}
            async fn run()->Int{let mut p=pool<String>(2);let mut data=p.new();data.push_str("été");
                let mut scratch=p.new();scratch.push_str("temporary");
                let view=relay(&data[..],&scratch[..]);drop(->scratch);yield;
                CHECK print(view);let length=view.byte_len();AFTER drop(->data);return length;}
            fn main(){let h=runtime::spawn(->run());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        valid=source.replace('CHECK','').replace('AFTER','')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout,'temporary\nété\n5\n')
        self.rejected(source.replace('drop(->data);','').replace('CHECK','drop(->data);').replace('AFTER',''))
        self.rejected(source.replace('CHECK','data.push_str("x");').replace('AFTER',''))
        after=source.replace('CHECK','').replace('AFTER','data.push_str("x");print(&data[..]);')
        self.assertEqual(self.run_c_oracle(compile_source(after)).stdout,'temporary\nété\nétéx\n5\n')

    def test_slice_parameters_results_and_mutation(self):
        for element in ('Int','u8'):
            for mutable in (False,True):
                mode='&mut ' if mutable else '&'
                view=f'{mode}[{element}]'
                result='&mut *v' if mutable else 'v'
                prepare='let (mut empty, mut part)=data.split_at_mut(0);' if mutable else ''
                argument='part' if mutable else '&data[..]'
                edit=f'let replacement:{element}=9;view[0]=replacement;' if mutable else ''
                source=f'''fn identity(v:{view})->{view}{{return {result};}}
                    fn relay(v:{view})->{view}{{return identity(v);}}
                    async fn run()->Int{{let mut p=pool<Vector<{element}>>(1);let mut data=p.new();
                        let n:{element}=7;data.push(n);{prepare}
                        let view=relay({argument});yield;CHECK {edit}
                        let answer=view[0] as Int;data.push(n);drop(->data);return answer;}}
                    fn main(){{let h=runtime::spawn(->run());match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}}}'''
                with self.subTest(element=element,mutable=mutable):
                    self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,('9' if mutable else '7')+'\n')
                    self.rejected(source.replace('CHECK','data.push(n);'))
                    if mutable:self.rejected(source.replace('CHECK','print(data[0] as Int);'))
                    else:self.rejected(source.replace('CHECK','view[0]=n;'),'partagée|mutable|readonly|affectation')

    def test_fallible_slice_arguments_and_result(self):
        source='''fn cut(v:&str,end:Int)->Result<&str,SliceError>{return v.try_slice(..end);}
            fn relay(v:Result<&str,SliceError>)->Result<&str,SliceError>{return v;}
            async fn run()->Int{let mut p=pool<String>(1);let mut text=p.new();text.push_str("été");
                let result=relay(cut(&text[..],BOUND));yield;CHECK
                let size=match result{Ok(view)=>{print(view);view.byte_len()},Err(_)=>{99}};
                drop(->text);return size;}
            fn main(){let h=runtime::spawn(->run());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        for bound,output in ((2,'é\n2\n'),(1,'99\n'),(9,'99\n')):
            with self.subTest(bound=bound):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('BOUND',str(bound)).replace('CHECK',''))).stdout,output)
        self.rejected(source.replace('BOUND','2').replace('drop(->text);','').replace('CHECK','drop(->text);'))

    def test_composed_text_and_byte_views_keep_storage(self):
        for expression,observe,output in (
            ('&identity(&data[..])[..2]','print(view);','é\n'),
            ('&identity(&data[..])[0]','print(*view as Int);','195\n'),
        ):
            source='''fn identity(v:&str)->&str{return v;}
                async fn run(){let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                    let view=EXPR;yield;CHECK OBSERVE drop(->data);}
                fn main(){let h=runtime::spawn(->run());match h.join(){Ok(())=>{},Err(_)=>{}}}'''
            source=source.replace('EXPR',expression).replace('OBSERVE',observe)
            with self.subTest(expression=expression):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,output)
                self.rejected(source.replace('drop(->data);','').replace('CHECK','drop(->data);'))
                self.rejected(source.replace('CHECK','data.push_str("x");'))
        escaped='''fn identity(v:&str)->&str{return v;}
            async fn bad()->&str{let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                return &identity(&data[..])[..2];}
            fn main(){let h=runtime::spawn(->bad());match h.join(){Ok(v)=>{print(v);},Err(_)=>{}}}'''
        self.rejected(escaped)

    def test_ordered_arguments_and_suspension(self):
        source='''fn mark(v:&str)->&str{print(1);return v;}
            fn sink(v:&str,n:Int)->Int{print(3);return v.byte_len()+n;}
            async fn number()->Int{print(2);yield;return 4;}
            async fn mutate(v:&mut String)->Int{v.push_str("x");return 4;}
            async fn run()->Int{let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                let answer=sink(mark(&data[..]),SECOND);drop(->data);return answer;}
            fn main(){let h=runtime::spawn(->run());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('SECOND','number().await'))).stdout,'1\n2\n3\n9\n')
        self.rejected(source.replace('SECOND','mutate(&mut data).await'))

    def test_independent_result_dependency_model(self):
        definitions='''fn choose(flag:bool,a:&str,b:&str,scratch:&str)->&str{
                print(scratch);return if flag{a}else{b};}
            fn again(flag:bool,a:&str,b:&str,scratch:&str)->&str{return choose(flag,a,b,scratch);}
            async fn work(flag:Bool,a:&str,b:&str,scratch:&str)->&str{
                yield;let view=again(flag,a,b,scratch);yield;return view;}
            fn launch(flag:bool,a:&str,b:&str,scratch:&str)-><-runtime::Handle<&str>{
                let h=runtime::spawn(->work(flag,a,b,scratch));return <-h;}
            fn finish(h:->runtime::Handle<&str>)->&str{
                match h.join(){Ok(v)=>{return v;},Err(_)=>{return "backup";}}}'''
        names=('a','b','scratch')
        initialize=''.join(f'let mut {n}=p.new();{n}.push_str("{n}");' for n in names)
        for joined in (False,True):
            # Pure reachability model: all captures before completion, only
            # candidate result storage afterwards. No compiler facts used.
            required={'a','b'} if joined else set(names)
            for mask in itertools.product((False,True),repeat=3):
                destroyed={n for n,drop in zip(names,mask) if drop}
                cleanup=''.join(f'drop(->{n});' for n in names if n in destroyed)
                for flag in ('true','false'):
                    source=definitions+'fn main(){let mut p=pool<String>(3);'+initialize
                    source+=f'let h=launch({flag},&a[..],&b[..],&scratch[..]);'
                    source+=('let view=finish(->h);'+cleanup if joined else cleanup+'let view=finish(->h);')
                    source+='print(view);}'
                    with self.subTest(joined=joined,destroyed=destroyed,flag=flag):
                        if destroyed & required:self.rejected(source)
                        else:self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'scratch\n'+('a' if flag=='true' else 'b')+'\n')

    def test_native_thread_view_result(self):
        source='''fn identity(v:&str)->&str{return v;}
            fn main(){let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                let input=&data[..];let h=runtime::thread({->(input);identity(input)});
                match h.join(){Ok(view)=>{CHECK print(view);},Err(_)=>{}}drop(->data);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'été\n')
        self.rejected(source.replace('drop(->data);','').replace('CHECK','data ->;drop(->data);'))

    def test_argument_early_return_skips_call_and_cleans_scope(self):
        source='''fn forbidden(v:&str,n:Int)->Int{print(999);return v.byte_len()+n;}
            async fn run()->Int{let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                let unused=forbidden(&data[..],{return 7;});return unused;}
            fn main(){let h=runtime::spawn(->run());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        run=self.run_c_oracle(compile_source(source))
        self.assertEqual(run.stdout,'7\n')
        trace=run.stderr.splitlines()
        self.assertEqual(len(trace),2)
        self.assertTrue(trace[0].startswith('destroy data='),trace)
        self.assertEqual(trace[1],'reclaim data')

    def test_native_inferred_vector_slice_result(self):
        for element in ('Int', 'u8'):
            source=f'''fn identity(v:&[{element}])->&[{element}]{{return v;}}
                fn main(){{let mut p=pool<Vector<{element}>>(1);let mut data=p.new();
                    let n:{element}=7;data.push(n);let input=&data[..];
                    let h=runtime::thread({{->(input);identity(input)}});
                    match h.join(){{Ok(view)=>{{CHECK print(view[0] as Int);}},Err(_)=>{{}}}}
                    drop(->data);}}'''
            with self.subTest(element=element):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'7\n')
                self.rejected(source.replace('drop(->data);','').replace('CHECK','data ->;drop(->data);'))

    def test_computed_receiver_reserved_during_suspended_index(self):
        source='''fn identity(v:&str)->&str{return v;}
            async fn bound()->Int{yield;return 2;}
            async fn mutate(v:&mut String)->Int{v.push_str("x");return 2;}
            async fn run(){let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                let view=EXPR;OBSERVE drop(->data);}
            fn main(){let h=runtime::spawn(->run());match h.join(){Ok(())=>{},Err(_)=>{}}}'''
        for expr,observe,expected in (
            ('&identity(&data[..])[..INDEX]','print(view);','é\n'),
            ('&identity(&data[..])[INDEX]','print(*view as Int);','116\n'),
        ):
            template=source.replace('EXPR',expr).replace('OBSERVE',observe)
            with self.subTest(expr=expr):
                self.assertEqual(self.run_c_oracle(compile_source(template.replace('INDEX','bound().await'))).stdout,expected)
                self.rejected(template.replace('INDEX','mutate(&mut data).await'))

    def test_fallible_helper_result_requires_explicit_use(self):
        source='''fn cut(v:&str)->Result<&str,SliceError>{print(7);return v.try_slice(..);}
            async fn run(){ACTION}
            fn main(){let h=runtime::spawn(->run());match h.join(){Ok(())=>{},Err(_)=>{}}}'''
        for action in ('cut("été");','let unused=cut("été");','let _=cut("été");'):
            with self.subTest(action=action):self.rejected(source.replace('ACTION',action),'sans usage|usage explicite')
        explicit=source.replace('ACTION','drop(->cut("été"));')
        self.assertEqual(self.run_c_oracle(compile_source(explicit)).stdout,'7\n')

if __name__=='__main__':unittest.main()
