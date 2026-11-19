"""Field paths in public handles returned by synchronous factories to async states."""
from pathlib import Path
import itertools
import unittest
from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_runtime
from scheduler_faults import inject_submission_failure

class SyncHandleFieldTests(unittest.TestCase):
    run_c_oracle=test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, pattern='emprunt|capture|durable|surviv|source|réserv|durée'):
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaisesRegex(Error,pattern) as caught:check(source)
                self.assertNotIn('invariant interne',str(caught.exception))

    def test_recorded_field_return(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-sync-handle-field-result.crb').read_text()
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'7\n')
        bad=source.replace('print(*v);','drop(->p);print(*v);')
        # An outer owner must first be imported into the match arm.
        self.rejected(bad.replace('drop(->p);','p ->;drop(->p);'))

    @staticmethod
    def direct_program(mutable=False,direct=False):
        mode='&mut' if mutable else '&'
        reference=f'{mode} p.x'
        preparation='' if direct else 'let h=launch(p);'
        wait='launch(p).await' if direct else 'h.await'
        use='view.set(9);' if mutable else ''
        return f'''struct Point{{x:Int,y:Int}}
            async fn leaf(p:{mode} Point)->{mode} Int{{yield;return {reference};}}
            fn launch(p:{mode} Point)-><-runtime::Handle<{mode} Int>{{let h=runtime::spawn(->leaf(p));return <-h;}}
            async fn parent(p:&mut Point)->Int{{{preparation}BEFORE
                let mut view=match {wait}{{Ok(v)=>{{v}},Err(_)=>{{return 99;}}}};
                yield;CHECK {use}let n=*view;AFTER return n;}}
            fn main(){{let mut p=Point{{x:7,y:8}};let h=runtime::spawn(->parent(&mut p));
                match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}print(p.x);print(p.y);}}'''

    def test_inline_fields_and_named_or_direct_wait(self):
        for mutable,direct in itertools.product((False,True),repeat=2):
            source=self.direct_program(mutable,direct)
            with self.subTest(mutable=mutable,direct=direct):
                valid=source.replace('BEFORE','').replace('CHECK','p.y=20;').replace('AFTER','p.x=30;')
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout,('9' if mutable else '7')+'\n30\n20\n')
                self.rejected(source.replace('BEFORE','').replace('CHECK','p.x=20;').replace('AFTER',''))
                if not direct:self.rejected(source.replace('BEFORE','p.y=20;').replace('CHECK','').replace('AFTER',''))

    def test_indirect_mutable_field_keeps_capability(self):
        source='''struct Writer{left:Int,data:&mut Int,right:Int}
            async fn leaf(v:&mut Writer)->&mut Int{yield;return &mut *v.data;}
            fn launch(v:&mut Writer)-><-runtime::Handle<&mut Int>{let h=runtime::spawn(->leaf(v));return <-h;}
            fn relay(v:&mut Writer)-><-runtime::Handle<&mut Int>{let h=launch(v);return <-h;}
            async fn parent(v:&mut Writer)->&mut Int{let h=relay(v);yield;match h.await{
                Ok(n)=>{CHECK return &mut *n;},Err(_)=>{return &mut *v.data;}}}
            fn main(){let mut p=pool<Int>(1);let mut data=p.new(7);
                let mut writer=Writer{left:2,data:&mut data,right:3};let h=runtime::spawn(->parent(&mut writer));
                match h.join(){Ok(n)=>{OUT n.set(9);print(*n);},Err(_)=>{}}print(writer.right);print(*data);}'''
        valid=source.replace('CHECK','v.right=8;').replace('OUT','writer.left=5;')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout,'9\n8\n9\n')
        for access in ('print(*writer.data);','writer ->;drop(->writer);','data ->;drop(->data);','print(*data);'):
            with self.subTest(access=access):self.rejected(source.replace('CHECK','').replace('OUT',access))
        self.rejected(source.replace('CHECK','print(*v.data);').replace('OUT',''))

    def test_detached_shared_field_outlives_carrier(self):
        source='''struct View{data:&Int}
            async fn leaf(v:&View)->&Int{yield;return v.data;}
            fn launch(v:&View)-><-runtime::Handle<&Int>{let h=runtime::spawn(->leaf(v));return <-h;}
            async fn parent(v:&View)->&Int{match launch(v).await{Ok(n)=>{return n;},Err(_)=>{return v.data;}}}
            fn main(){let mut p=pool<Int>(1);let data=p.new(7);
                let view=View{data:&data};let h=runtime::spawn(->parent(&view));
                match h.join(){Ok(n)=>{view ->;drop(->view);CHECK print(*n);},Err(_)=>{}}drop(->data);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'7\n')
        self.rejected(source.replace('drop(->data);','').replace('view ->;','data ->;view ->;').replace('CHECK','drop(->data);'))

    def test_independent_field_access_model(self):
        for choices in (('x',),('y',),('x','y')):
            expr=f'&mut p.{choices[0]}' if len(choices)==1 else 'if flag{&mut p.x}else{&mut p.y}'
            for written,after,flag in itertools.product(('x','y','z'),(False,True),('true','false')):
                source=f'''struct Point{{x:Int,y:Int,z:Int}}
                    async fn leaf(p:&mut Point,flag:Bool)->&mut Int{{yield;return {expr};}}
                    fn launch(p:&mut Point,flag:bool)-><-runtime::Handle<&mut Int>{{let h=runtime::spawn(->leaf(p,flag));return <-h;}}
                    fn relay(p:&mut Point,flag:bool)-><-runtime::Handle<&mut Int>{{let h=launch(p,flag);return <-h;}}
                    async fn parent(p:&mut Point)->Int{{let h=relay(p,{flag});
                        let mut view=match h.await{{Ok(v)=>{{v}},Err(_)=>{{return 99;}}}};yield;BEFORE
                        let n=*view;AFTER return n;}}
                    fn main(){{let mut p=Point{{x:7,y:8,z:9}};let h=runtime::spawn(->parent(&mut p));
                        match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}print(p.{written});}}'''
                assignment=f'p.{written}=42;'
                source=source.replace('BEFORE','' if after else assignment).replace('AFTER',assignment if after else '')
                with self.subTest(choices=choices,written=written,after=after,flag=flag):
                    if not after and written in choices:self.rejected(source)
                    else:
                        selected=choices[0] if len(choices)==1 or flag=='true' else choices[1]
                        expected={'x':7,'y':8,'z':9}[selected]
                        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,f'{expected}\n42\n')

    def test_failure_keeps_fallback_and_releases_capture(self):
        source=self.direct_program(True,False).replace('BEFORE','').replace('CHECK','p.y=20;').replace('AFTER','p.x=30;')
        code=compile_source(source)
        run=self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=2,maximum=2))
        self.assertEqual(run.stdout,'99\n7\n8\n')

    def test_independent_capture_is_not_coalesced(self):
        source=self.direct_program(True,False)
        for operation in ('let other=launch(p);let result=other.await;drop(->result);',
                          'let mut other=&mut p.x;other.set(4);'):
            with self.subTest(operation=operation):
                self.rejected(source.replace('BEFORE',operation).replace('CHECK','').replace('AFTER',''))

    def test_field_result_reset_contract_without_bodies(self):
        declarations='''struct Writer{data:&mut Int}
            async fn leaf(v:&mut Writer)->&mut Int{yield;return &mut *v.data;}
            fn launch(v:&mut Writer)-><-runtime::Handle<&mut Int>{let h=runtime::spawn(->leaf(v));return <-h;}
            fn finish(h:->runtime::Handle<&mut Int>,p:&mut Pool<Int>)->&mut Int{
                let n=match h.join(){Ok(v)=>{v},Err(_)=>{loop{}}};p.reset();return n;}
            fn route(v:&mut Writer,p:&mut Pool<Int>)->&mut Int{let h=launch(v);return finish(->h,p);}'''
        interface=verify_program(declarations,allow_legacy_reset=True)
        def pairs(name):
            return {frozenset(((r.left.kind,r.left.index,r.left.name),
                              (r.right.kind,r.right.index,r.right.name)))
                    for r in interface.function_constraints[name].all_requirements if r.relation=='distinct'}
        self.assertIn(frozenset((('source_parameter',1,''),('task_borrow_parameter',0,'4'))),pairs('finish'))
        self.assertIn(frozenset((('source_parameter',1,''),('allocation_field_parameter',0,'.data'))),pairs('route'))
        for target,direct in itertools.product(('p','q'),(False,True)):
            call=(f'let h=launch(&mut writer);let mut n=finish(->h,&mut {target});' if direct
                  else f'let mut n=route(&mut writer,&mut {target});')
            script=f'''let mut p=pool<Int>(1);let mut q=pool<Int>(1);let mut data=p.new(7);
                let mut writer=Writer{{data:&mut data}};{call}n.set(9);print(*n);'''
            source=declarations+'fn main(){'+script+'}'
            with self.subTest(target=target,direct=direct):
                if target=='q':
                    self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'9\n')
                else:
                    for stage in (verify_program,compile_source):
                        with self.assertRaisesRegex(Error,'reset|distinct'):
                            stage(source,allow_legacy_reset=True)
                check=Compiler(allow_legacy_reset=True);check.contract_calls=True
                check.function_contracts=interface.function_contracts
                check.enums=interface.enums
                nodes=Parser('struct Writer{data:&mut Int}'+script).parse();check.index(nodes)
                nodes=nodes[1:]
                if target=='q':check.block('root',nodes)
                else:
                    with self.assertRaisesRegex(Error,'reset|distinct'):check.block('root',nodes)
                self.assertFalse(check.functions)
                self.assertFalse(check.async_definitions)

    def test_nested_inline_field_and_conditional_receiver(self):
        source='''struct Point{x:Int,y:Int}struct Pair{left:Point,right:Point}
            async fn leaf(p:&mut Pair)->&mut Int{yield;return &mut p.left.x;}
            fn launch(p:&mut Pair)-><-runtime::Handle<&mut Int>{let h=runtime::spawn(->leaf(p));return <-h;}
            async fn parent(p:&mut Pair)->Int{let h={let h=launch(p);<-h};
                let mut view=match h.await{Ok(v)=>{v},Err(_)=>{return 99;}};
                CHECK view.set(11);return *view;}
            fn main(){let mut pair=Pair{};pair.left.x=7;pair.left.y=8;pair.right.x=9;pair.right.y=10;
                let h=runtime::spawn(->parent(&mut pair));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                print(pair.left.y);print(pair.right.x);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK','p.left.y=12;p.right.x=13;'))).stdout,'11\n12\n13\n')
        self.rejected(source.replace('CHECK','p.left.x=14;'))

if __name__=='__main__':unittest.main()
