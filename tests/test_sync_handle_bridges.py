"""Synchronous handle factories invoked inside running async/native states."""
from pathlib import Path
import itertools
import unittest
from crust import compile_source, verify_program, Error
import test_async_runtime
from scheduler_faults import inject_submission_failure

class SyncHandleBridgeTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, pattern='emprunt|capture|surviv|durable|attend|handle|consomm|signature'):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaisesRegex(Error, pattern):check(source)

    def test_recorded_counterexample(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-public-view-handle-async-helper.crb').read_text()
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'été\n')

    def test_scalar_launch_modes_and_explicit_wait(self):
        for expression in ('runtime::spawn(->leaf(n))','runtime::spawn_blocking(->leaf(n))',
                           'runtime::thread({->(n);n})'):
            source='''async fn leaf(n:Int)->Int{yield;return n;}
                fn launch(n:Int)-><-runtime::Handle<Int>{let h=LAUNCH;return <-h;}
                fn relay(n:Int)-><-runtime::Handle<Int>{let h=launch(n);return <-h;}
                async fn parent()->Int{let h:runtime::Handle<Int>=relay(42);yield;
                    match h.await{Ok(n)=>{return n;},Err(_)=>{return 99;}}}
                fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''.replace('LAUNCH',expression)
            with self.subTest(launch=expression):
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'42\n')
                self.rejected(source.replace('yield;\n                    match h.await','drop(->h);\n                    match h.await'))
                self.rejected(source.replace('yield;\n                    match h.await','return 7;\n                    match h.await'))
                self.rejected(source.replace('match h.await','match h.join()'),'join réservé|synchrone|résultat de handle requis')

    def test_capture_release_and_returned_target(self):
        source='''async fn leaf(v:&str,scratch:&str)->&str{print(scratch);yield;return v;}
            fn launch(v:&str,scratch:&str)-><-runtime::Handle<&str>{let h=runtime::spawn(->leaf(v,scratch));return <-h;}
            async fn parent(v:&str,scratch:&str)->&str{let h=launch(v,scratch);yield;
                match h.await{Ok(view)=>{return view;},Err(_)=>{return "backup";}}}
            fn main(){let mut p=pool<String>(2);let mut text=p.new();text.push_str("été");
                let mut scratch=p.new();scratch.push_str("temporary");
                let h=runtime::spawn(->parent(&text[..],&scratch[..]));
                match h.join(){Ok(view)=>{scratch ->;drop(->scratch);print(view);},Err(_)=>{}}}'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'temporary\nété\n')
        self.rejected(source.replace('scratch ->;drop(->scratch);','text ->;drop(->text);'))

    def test_borrowed_results(self):
        for mutable in (False,True):
            typ='&mut Int' if mutable else '&Int'
            value='&mut *v' if mutable else 'v'
            source=f'''async fn leaf(v:{typ})->{typ}{{yield;return {value};}}
                fn launch(v:{typ})-><-runtime::Handle<{typ}>{{let h=runtime::spawn(->leaf(v));return <-h;}}
                async fn parent(v:{typ})->{typ}{{let h=launch(v);match h.await{{
                    Ok(view)=>{{return {'&mut *view' if mutable else 'view'};}},Err(_)=>{{return {value};}}}}}}
                fn main(){{let mut p=pool<Int>(1);let mut data=p.new(7);
                    let h=runtime::spawn(->parent({'&mut' if mutable else '&'} data));
                    match h.join(){{Ok(view)=>{{CHECK print(*view);}},Err(_)=>{{}}}}drop(->data);}}'''
            with self.subTest(mutable=mutable):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'7\n')
                self.rejected(source.replace('drop(->data);','').replace('CHECK','data ->;drop(->data);'))

    def test_launch_failure_cleans_owner_and_reuses_slot(self):
        source='''async fn leaf(v:->Int)->Int{yield;return *v;}
            fn launch(v:->Int)-><-runtime::Handle<Int>{let h=runtime::spawn(->leaf(->v));return <-h;}
            async fn parent()->Int{let mut p=pool<Int>(1);let mut data=p.new(7);
                let h=launch(->data);let result=match h.await{Ok(n)=>{n},Err(_)=>{99}};
                let other=p.new(8);print(*other);drop(->other);return result;}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'8\n7\n')
        failed=inject_submission_failure(code,asynchronous=False,at=2,maximum=2)
        run=self.run_c_oracle(failed)
        self.assertEqual(run.stdout,'8\n99\n')
        self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()),2)
        self.assertEqual(sum(line.startswith('reclaim ') for line in run.stderr.splitlines()),2)

    def test_local_capture_reserved_until_wait(self):
        source='''async fn leaf(v:&str)->Int{yield;return v.byte_len();}
            fn launch(v:&str)-><-runtime::Handle<Int>{let h=runtime::spawn(->leaf(v));return <-h;}
            async fn parent()->Int{let mut p=pool<String>(1);let mut data=p.new();data.push_str("abc");
                let h=launch(&data[..]);CHECK
                let n=match h.await{Ok(n)=>{n},Err(_)=>{99}};drop(->data);return n;}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK','yield;'))).stdout,'3\n')
        self.rejected(source.replace('drop(->data);','').replace('CHECK','drop(->data);'))
        self.rejected(source.replace('CHECK','data.push_str("x");'))

    def test_independent_dependency_model(self):
        declarations='''async fn leaf(a:&str,b:&str,scratch:&str,flag:Bool)->&str{
                print(scratch);yield;return if flag{a}else{b};}
            fn launch(a:&str,b:&str,scratch:&str,flag:bool)-><-runtime::Handle<&str>{
                let h=runtime::spawn(->leaf(a,b,scratch,flag));return <-h;}'''
        names=('a','b','scratch')
        for joined in (False,True):
            required={'a','b'} if joined else set(names)
            for mask in itertools.product((False,True),repeat=3):
                destroyed={n for n,chosen in zip(names,mask) if chosen}
                for flag in ('true','false'):
                    prefix='async fn parent(){let mut p=pool<String>(3);'
                    prefix+=''.join(f'let mut {n}=p.new();{n}.push_str("{n}");' for n in names)
                    prefix+=f'let h=launch(&a[..],&b[..],&scratch[..],{flag});'
                    cleanup=''.join(f'drop(->{n});' for n in names if n in destroyed)
                    wait='let view=match h.await{Ok(v)=>{v},Err(_)=>{"backup"}};'
                    body=(wait+cleanup if joined else cleanup+wait)+'yield;print(view);}'
                    source=declarations+prefix+body+'''fn main(){let h=runtime::spawn(->parent());
                        match h.join(){Ok(())=>{},Err(_)=>{}}}'''
                    with self.subTest(joined=joined,destroyed=destroyed,flag=flag):
                        if destroyed & required:self.rejected(source)
                        else:self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'scratch\n'+('a' if flag=='true' else 'b')+'\n')

    def test_owned_results_local_pool_and_reuse(self):
        for typ,arg,init,read,expected in (
            ('Int','7','','*value','7'),
            ('String','','value.push_str("été");','value.byte_len()','5'),
            ('Vector<Int>','','value.push(7);','value[0]','7'),
            ('Vector<u8>','','value.push(7);','value[0] as Int','7'),
        ):
            source=f'''async fn leaf(p:&mut Pool<{typ}>)-><-{typ}{{let mut value=p.new({arg});{init}yield;return <-value;}}
                fn launch(p:&mut Pool<{typ}>)-><-runtime::Handle<A<{typ}>>{{let h=runtime::spawn(->leaf(p));return <-h;}}
                async fn parent(){{let mut p=pool<{typ}>(1);let h=launch(&mut p);
                    let value=match h.await{{Ok(value)=>{{<-value}},Err(_)=>{{let mut value=p.new({arg});{init}<-value}}}};
                    yield;print({read});drop(->value);let reused=p.new({arg});drop(->reused);}}
                fn main(){{let h=runtime::spawn(->parent());match h.join(){{Ok(())=>{{}},Err(_)=>{{}}}}}}'''
            with self.subTest(typ=typ):
                code=compile_source(source)
                self.assertEqual(self.run_c_oracle(code).stdout,expected+'\n')
                self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=2)).stdout,expected+'\n')

    def test_returned_slices_and_last_use(self):
        for element in ('Int','u8'):
            for mutable in (False,True):
                mode='&mut ' if mutable else '&'
                typ=f'{mode}[{element}]'
                result='&mut *v' if mutable else 'v'
                prepare='let (mut empty,mut part)=data.split_at_mut(0);' if mutable else ''
                argument='part' if mutable else '&data[..]'
                source=f'''async fn leaf(v:{typ})->{typ}{{yield;return {result};}}
                    fn launch(v:{typ})-><-runtime::Handle<{typ}>{{let h=runtime::spawn(->leaf(v));return <-h;}}
                    async fn parent(){{let mut p=pool<Vector<{element}>>(1);let mut data=p.new();data.push(7);{prepare}
                        let h=launch({argument});match h.await{{Ok(view)=>{{CHECK print(view[0] as Int);}},Err(_)=>{{}}}}
                        data.push(8);drop(->data);}}
                    fn main(){{let h=runtime::spawn(->parent());match h.join(){{Ok(())=>{{}},Err(_)=>{{}}}}}}'''
                with self.subTest(element=element,mutable=mutable):
                    self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK','yield;'))).stdout,'7\n')
                    self.rejected(source.replace('CHECK','data.push(9);'))

    def test_nested_factories_suspend_and_reuse_frames(self):
        declarations='async fn level0(n:Int)->Int{yield;return n;}'
        for index in range(6):
            declarations+=f'''fn launch{index}(n:Int)-><-runtime::Handle<Int>{{
                let h=runtime::spawn(->level{index}(n));return <-h;}}
                async fn level{index+1}(n:Int)->Int{{let h=launch{index}(n);yield;
                    match h.await{{Ok(value)=>{{return value+1;}},Err(_)=>{{return 99;}}}}}}'''
        source=declarations+'''fn main(){let mut i=0;while i<12{let h=runtime::spawn(->level6(i));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(999);}}i=i+1;}}'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,''.join(f'{i+6}\n' for i in range(12)))

    def test_runtime_adoption_resource_contract(self):
        from async_runtime import TASK_RUNTIME, TASK_THREAD_RUNTIME, TASK_ASYNC_THREAD_RUNTIME
        code=TASK_RUNTIME+TASK_THREAD_RUNTIME+TASK_ASYNC_THREAD_RUNTIME+r'''
#include <assert.h>
static int detached;
static int detach_probe(pthread_t unused) { (void)unused; ++detached; return 0; }
int main(void) {
    CrustTask task = {0};
    for (int pooled = 0; pooled <= 1; ++pooled) {
        for (int failed = 0; failed <= 1; ++failed) {
            CrustExecution input = { .task = failed ? NULL : &task,
                .error = failed ? EAGAIN : 0, .pooled = pooled, .detach = detach_probe };
            atomic_init(&input.joined, 0);
            CrustAsyncExecution output = {0};
            int before = detached;
            task_async_adopt(&output, &input);
            assert(!input.task && !input.error && atomic_load(&input.joined));
            assert(output.task == (failed ? NULL : &task));
            assert(output.error == (failed ? EAGAIN : 0));
            assert(detached - before == (!pooled && !failed));
        }
    }
    return 0;
}'''
        self.assertEqual(self.run_c_oracle(code).returncode,0)

    def test_owned_result_cannot_escape_local_pool(self):
        source='''async fn leaf(p:&mut Pool<Int>)-><-Int{let v=p.new(7);yield;return <-v;}
            fn launch(p:&mut Pool<Int>)-><-runtime::Handle<A<Int>>{let h=runtime::spawn(->leaf(p));return <-h;}
            async fn parent()-><-Int{let value={let mut p=pool<Int>(1);let h=launch(&mut p);
                let value=match h.await{Ok(v)=>{<-v},Err(_)=>{let v=p.new(9);<-v}};<-value};return <-value;}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(v)=>{print(*v);},Err(_)=>{}}}'''
        self.rejected(source,'pool|source|durable')

    def test_argument_order_and_protected_capture(self):
        source='''async fn leaf(v:&mut Int,n:Int)->Int{yield;v.set(n);return *v;}
            fn launch(v:&mut Int,n:Int)-><-runtime::Handle<Int>{let h=runtime::spawn(->leaf(v,n));return <-h;}
            async fn number()->Int{print(1);yield;return 9;}
            async fn parent()->Int{let mut value=3;let h=launch(&mut value,ARG);
                print(2);let n=match h.await{Ok(n)=>{n},Err(_)=>{99}};print(value);return n;}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('ARG','number().await'))).stdout,'1\n2\n9\n9\n')
        self.rejected(source.replace('ARG','{yield;value=10;9}'))

    def test_fallible_view_result(self):
        source='''async fn leaf(v:&str,n:Int)->Result<&str,SliceError>{yield;return v.try_slice(..n);}
            fn launch(v:&str,n:Int)-><-runtime::Handle<Result<&str,SliceError>>{
                let h=runtime::spawn(->leaf(v,n));return <-h;}
            async fn parent(){let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                let h=launch(&data[..],BOUND);match h.await{Ok(inner)=>{CHECK yield;
                    match inner{Ok(view)=>{print(view);},Err(_)=>{print(99);}}},Err(_)=>{print(98);}}
                drop(->data);}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(())=>{},Err(_)=>{}}}'''
        for bound,expected in ((2,'é\n'),(1,'99\n'),(9,'99\n')):
            with self.subTest(bound=bound):
                code=compile_source(source.replace('BOUND',str(bound)).replace('CHECK',''))
                self.assertEqual(self.run_c_oracle(code).stdout,expected)
        self.rejected(source.replace('BOUND','2').replace('drop(->data);','').replace('CHECK','data ->;drop(->data);'))

    def test_duplicate_wait_and_unreceived_handle(self):
        source='''async fn leaf()->Int{return 7;}
            fn launch()-><-runtime::Handle<Int>{let h=runtime::spawn(->leaf());return <-h;}
            async fn parent(){ACTION}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(())=>{},Err(_)=>{}}}'''
        wait='match h.await{Ok(n)=>{print(n);},Err(_)=>{}}'
        for action in ('launch();', 'let h=launch();'+wait+wait):
            with self.subTest(action=action):self.rejected(source.replace('ACTION',action))
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('ACTION','let h=launch();'+wait))).stdout,'7\n')

    def test_direct_factory_await(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-sync-handle-direct-await.crb').read_text()
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'7\n')
        view='''async fn leaf(v:&str)->&str{yield;return v;}
            fn launch(v:&str)-><-runtime::Handle<&str>{let h=runtime::spawn(->leaf(v));return <-h;}
            async fn parent(){let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");
                let result=launch(&data[..]).await;yield;CHECK
                match result{Ok(v)=>{print(v);},Err(_)=>{}}drop(->data);}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(())=>{},Err(_)=>{}}}'''
        self.assertEqual(self.run_c_oracle(compile_source(view.replace('CHECK',''))).stdout,'été\n')
        self.rejected(view.replace('drop(->data);','').replace('CHECK','drop(->data);'))
        self.rejected(source.replace('match launch().await{Ok(n)=>{return n;},Err(_)=>{return 99;}}',
                                     'launch().await;return 7;'),'usage explicite|résultat|receveur')

if __name__=='__main__':unittest.main()
