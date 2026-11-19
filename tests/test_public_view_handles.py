"""Public view handles retain result storage independently of execution captures."""
from pathlib import Path
import itertools
import unittest
from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_runtime
from scheduler_faults import inject_submission_failure


class PublicViewHandleTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, pattern='emprunt|capture|durable|durée|survit|invalide|plus utilisable', **options):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaisesRegex(Error, pattern):
                check(source, **options)

    def test_text_contract_cleanup_last_use_and_launch_failure(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-public-handle-view-contract.crb').read_text()
        verify_program(source)
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'12\nété\n')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1)).stdout,'backup\n')
        # No second drop can mask acceptance of the deliberately premature one.
        self.rejected(source.replace('print(view);drop(->text);','drop(->text);print(view);'))
        self.rejected(source.replace('print(view);','text.push_str("x");print(view);'))
        self.rejected(source.replace('print(view);','p.reset();print(view);'), 'reset interdit', allow_legacy_reset=True)
        self.rejected(source.replace('let next=relay(->h);','drop(->scratch);let next=relay(->h);').replace('drop(->scratch);\n',''))
        after=source.replace('print(view);','print(view);text.push_str("x");print(&text[..]);')
        self.assertEqual(self.run_c_oracle(compile_source(after)).stdout,'12\nété\nétéx\n')

    @staticmethod
    def slice_program(element='Int', mutable=False):
        mode='&mut ' if mutable else '&'
        view=f'{mode}[{element}]'
        reborrow='&mut *v' if mutable else 'v'
        backup='&mut *backup' if mutable else 'backup'
        prepare = ('let (mut empty, mut input)=data.split_at_mut(0);'
                   'let (mut empty2, mut spare)=fallback.split_at_mut(0);') if mutable else ''
        incoming = 'input' if mutable else '&data[..]'
        spare = 'spare' if mutable else '&fallback[..]'
        return f'''async fn work(scratch:&Int,v:{view})->{view}{{print(*scratch);yield;return {reborrow};}}
            fn launch(scratch:&Int,v:{view})-><-runtime::Handle<{view}>{{
                let h=runtime::spawn(->work(scratch,v));return <-h;}}
            fn relay(h:->runtime::Handle<{view}>)-><-runtime::Handle<{view}>{{return <-h;}}
            fn finish(h:->runtime::Handle<{view}>,backup:{view})->{view}{{
                return match h.join(){{Ok(v)=>{{{reborrow}}},Err(_)=>{{{backup}}}}};}}
            fn main(){{let mut p=pool<Vector<{element}>>(2);let mut data=p.new();let mut fallback=p.new();
                let n:{element}=7;let f:{element}=99;data.push(n);fallback.push(f);
                let mut q=pool<Int>(1);let scratch=q.new(12);
                {prepare}let h=launch(&scratch,{incoming});let next=relay(->h);
                let view=finish(->next,{spare});drop(->scratch);
                CHECK print(view[0] as Int);AFTER drop(->data);drop(->fallback);}}'''

    def test_shared_and_mutable_slices(self):
        for element in ('Int','u8'):
            for mutable in (False,True):
                source=self.slice_program(element,mutable)
                with self.subTest(element=element,mutable=mutable):
                    valid=source.replace('CHECK','').replace('AFTER','')
                    verify_program(valid)
                    code=compile_source(valid)
                    self.assertEqual(self.run_c_oracle(code).stdout,'12\n7\n')
                    self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1)).stdout,'99\n')
                    for target in ('data','fallback'):
                        operation=f'drop(->{target});'
                        self.rejected(source.replace(operation,'').replace('CHECK',operation).replace('AFTER',''))
                        self.rejected(source.replace('CHECK',f'{target}.push(n);').replace('AFTER',''))
                    if mutable:
                        self.rejected(source.replace('CHECK','print(data[0] as Int);').replace('AFTER',''))
                        edit=source.replace('CHECK',f'let replacement:{element}=9;view[0]=replacement;').replace('AFTER','print(data[0] as Int);')
                        self.assertEqual(self.run_c_oracle(compile_source(edit)).stdout,'12\n9\n9\n')
                    else:
                        self.rejected(source.replace('CHECK','view[0]=n;').replace('AFTER',''), 'partagée|mutable|readonly|vue UTF-8 empruntée')

    def test_shared_result_keeps_exclusive_capture(self):
        source='''async fn work(v:&mut Vector<Int>)->&[Int]{yield;return &v[..];}
            fn launch(v:&mut Vector<Int>)-><-runtime::Handle<&[Int]>{
                let h=runtime::spawn(->work(v));return <-h;}
            fn relay(h:->runtime::Handle<&[Int]>)-><-runtime::Handle<&[Int]>{return <-h;}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut data=p.new();data.push(7);
                let h=launch(&mut data);let next=relay(->h);
                match next.join(){Ok(view)=>{CHECK print(view[0]);data.push(9);},Err(_)=>{}}
                print(data[0]);}'''
        for direct in (False,True):
            template=source.replace('launch(&mut data)', 'runtime::spawn(->work(&mut data))') if direct else source
            with self.subTest(direct=direct):
                self.assertEqual(self.run_c_oracle(compile_source(template.replace('CHECK',''))).stdout,'7\n7\n')
                for operation in ('print(data[0]);','data.push(8);','drop(->data);'):
                    self.rejected(template.replace('CHECK',operation))

    def test_opaque_text_contract_has_no_callee_bodies(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-public-handle-view-contract.crb').read_text()
        declarations,main=source.split('fn main(){')
        interface=verify_program(declarations)
        script=main.rsplit('}',1)[0]
        for operation in ('','drop(->text);','text.push_str("x");'):
            check=Compiler();check.contract_calls=True;check.function_contracts=interface.function_contracts
            actual=script.replace('print(view);drop(->text);',operation+'print(view);')
            nodes=Parser(actual).parse();check.index(nodes)
            with self.subTest(operation=operation):
                if operation:
                    with self.assertRaisesRegex(Error,'emprunt|capture'):check.block('root',nodes)
                else:
                    check.block('root',nodes)
                    self.assertEqual(check.async_definitions,{})
                    self.assertEqual(check.functions,{})

    def test_fallible_slice_result_retains_origin(self):
        source='''async fn cut(v:&str,end:Int)->Result<&str,SliceError>{yield;return v.try_slice(..end);}
            fn launch(v:&str,end:Int)-><-runtime::Handle<Result<&str,SliceError>>{
                let h=runtime::spawn(->cut(v,end));return <-h;}
            fn relay(h:->runtime::Handle<Result<&str,SliceError>>)-><-runtime::Handle<Result<&str,SliceError>>{return <-h;}
            fn main(){let mut p=pool<String>(1);let mut text=p.new();text.push_str("été");
                let h=launch(&text[..],BOUND);let next=relay(->h);
                match next.join(){Ok(result)=>{CHECK
                    match result{Ok(view)=>{print(view);},Err(_)=>{print("slice error");}}
                },Err(_)=>{print("launch error");}}drop(->text);}'''
        for bound,output in ((2,'é\n'),(1,'slice error\n'),(9,'slice error\n')):
            with self.subTest(bound=bound):
                valid=source.replace('BOUND',str(bound)).replace('CHECK','')
                code=compile_source(valid)
                self.assertEqual(self.run_c_oracle(code).stdout,output)
                self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1)).stdout,'launch error\n')
        self.rejected(source.replace('BOUND','2').replace('drop(->text);','').replace('CHECK','drop(->text);'))

    def test_independent_lifetime_model_and_heterogeneous_frames(self):
        definitions='''async fn first(a:&str,scratch:&str)->&str{print(scratch);yield;return a;}
            async fn second(scratch:&str,b:&str)->&str{print(scratch);yield;return b;}
            fn choose(flag:bool,a:&str,b:&str,scratch:&str)-><-runtime::Handle<&str>{
                let h=if flag{let h=runtime::spawn(->first(a,scratch));<-h}
                    else{let h=runtime::spawn(->second(scratch,b));<-h};return <-h;}
            fn finish(h:->runtime::Handle<&str>)->&str{
                match h.join(){Ok(v)=>{return v;},Err(_)=>{return "backup";}}}'''
        names=('a','b','scratch')
        initialize=''.join(f'let mut {name}=p.new();{name}.push_str("{name}");' for name in names)
        for joined in (False,True):
            # The oracle sees just abstract objects reachable by execution or result.
            protected={'a','b'} if joined else set(names)
            for mask in itertools.product((False,True),repeat=3):
                destroyed={name for name,drop in zip(names,mask) if drop}
                drops=''.join(f'drop(->{name});' for name in names if name in destroyed)
                for flag in ('true','false'):
                    source=definitions+'fn main(){let mut p=pool<String>(3);'+initialize
                    source+=f'let h=choose({flag},&a[..],&b[..],&scratch[..]);'
                    source+=('let view=finish(->h);'+drops if joined else drops+'let view=finish(->h);')
                    source+='print(view);}'
                    with self.subTest(joined=joined,destroyed=destroyed,flag=flag):
                        if destroyed & protected:self.rejected(source)
                        else:
                            verify_program(source)
                            self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,
                                             'scratch\n'+('a' if flag=='true' else 'b')+'\n')

    def test_ordered_reset_constraints_through_two_relays(self):
        source='''async fn work(v:&str)->&str{yield;return v;}
            fn read(h:->runtime::Handle<&str>,p:&mut Pool<String>)->Int{
                let view=match h.join(){Ok(v)=>{v},Err(_)=>{"backup"}};
                p.reset();return view.byte_len();}
            fn relay(h:->runtime::Handle<&str>,p:&mut Pool<String>)->Int{return read(->h,p);}
            fn concrete(h:->Execution<work>,p:&mut Pool<String>)->Int{return relay(->h,p);}
            fn main(){let mut p=pool<String>(1);let mut q=pool<String>(1);
                let mut text=p.new();text.push_str("été");let mut other=q.new();other.push_str("x");
                let h=runtime::spawn(->work(&text[..]));let size=concrete(->h,&mut TARGET);print(size);}'''
        valid=source.replace('TARGET','q')
        checked=verify_program(valid,allow_legacy_reset=True)
        # Independent contract obligation: resetting p before reading the joined
        # view requires p to differ from the sole storage captured by work.
        pairs={frozenset(((r.left.kind,r.left.index,r.left.name),
                          (r.right.kind,r.right.index,r.right.name)))
               for r in checked.function_constraints['concrete'].all_requirements if r.relation=='distinct'}
        self.assertIn(frozenset((('source_parameter',1,''),('task_utf8_parameter',0,'0'))),pairs)
        self.assertEqual(self.run_c_oracle(compile_source(valid,allow_legacy_reset=True)).stdout,'5\n')
        self.rejected(source.replace('TARGET','p'),'reset|distinct|capture|emprunt',allow_legacy_reset=True)

    def test_borrowed_byte_from_string_and_fixed_array(self):
        declarations='''async fn work(v:&u8)->&u8{yield;return v;}
            fn launch(v:&u8)-><-runtime::Handle<&u8>{let h=runtime::spawn(->work(v));return <-h;}
            fn relay(h:->runtime::Handle<&u8>)-><-runtime::Handle<&u8>{return <-h;}
            fn finish(h:->runtime::Handle<&u8>)->&u8{
                match h.join(){Ok(v)=>{return v;},Err(_)=>{let text="B";return &text[0];}}}'''
        for initialization,argument in (
            ('let mut p=pool<String>(1);let mut data=p.new();data.push_str("A");','&data[0]'),
            ('let data:[u8;1]=[65];','&data[0]'),
        ):
            source=declarations+'fn main(){'+initialization+f'''let h=launch({argument});let next=relay(->h);
                let v=finish(->next);CHECK print(*v as Int);drop(->data);}}'''
            with self.subTest(initialization=initialization):
                code=compile_source(source.replace('CHECK',''))
                self.assertEqual(self.run_c_oracle(code).stdout,'65\n')
                self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1)).stdout,'66\n')
                self.rejected(source.replace('drop(->data);','').replace('CHECK','drop(->data);'))

    def test_direct_concrete_to_public_view_conversion(self):
        source='''async fn work(v:&[Int])->&[Int]{yield;return v;}
            fn relay(h:->runtime::Handle<&[Int]>)-><-runtime::Handle<&[Int]>{return <-h;}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut data=p.new();data.push(7);
                let h=runtime::spawn(->work(&data[..]));let next=relay(->h);
                match next.join(){Ok(view)=>{CHECK print(view[0]);},Err(_)=>{}}drop(->data);}'''
        valid=source.replace('CHECK','')
        verify_program(valid)
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout,'7\n')
        self.rejected(source.replace('drop(->data);','').replace('CHECK','drop(->data);'))

    def test_static_text_and_shared_byte(self):
        for typ,body,observe,output in (
            ('&str','return "été";','print(v);','été\n'),
            ('&u8','let text="A";return &text[0];','print(*v as Int);','65\n'),
        ):
            source=f'''async fn work()->{typ}{{yield;{body}}}
                fn launch()-><-runtime::Handle<{typ}>{{let h=runtime::spawn(->work());return <-h;}}
                fn relay(h:->runtime::Handle<{typ}>)-><-runtime::Handle<{typ}>{{return <-h;}}
                fn main(){{let h=launch();let next=relay(->h);match next.join(){{Ok(v)=>{{{observe}}},Err(_)=>{{}}}}}}'''
            with self.subTest(typ=typ):
                verify_program(source)
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,output)

if __name__=='__main__':unittest.main()
