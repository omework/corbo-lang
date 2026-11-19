"""Opaque Handle borrow results: post-join targets versus transient captures."""
from pathlib import Path
import itertools
import unittest

from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_runtime
from scheduler_faults import inject_submission_failure


class PublicBorrowedHandleTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, pattern='emprunt|capture|survit|durée|invalide|plus utilisable', **options):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaisesRegex(Error, pattern):
                check(source, **options)

    @staticmethod
    def declarations(mode='&Int'):
        return f'''async fn work(v:{mode},scratch:&Int)->{mode}{{print(*scratch);yield;return v;}}
            fn launch(v:{mode},scratch:&Int)-><-runtime::Handle<{mode}>{{
                let h=runtime::spawn(->work(v,scratch));return <-h;}}
            fn relay(h:->runtime::Handle<{mode}>)-><-runtime::Handle<{mode}>{{return <-h;}}
            fn again(h:->runtime::Handle<{mode}>)-><-runtime::Handle<{mode}>{{
                let next=relay(->h);return <-next;}}
            fn finish(h:->runtime::Handle<{mode}>,backup:{mode})->{mode}{{
                match h.join(){{Ok(v)=>{{return v;}},Err(_)=>{{return backup;}}}}}}'''

    def test_initial_counterexample(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-public-handle-borrow-contract.crb').read_text()
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'7\n')
        self.rejected(source.replace('Handle<&Int>','Handle<&mut Int>'),'handle .*attendu')

    def test_relay_join_helper_mutability_cleanup_and_failure(self):
        for mode in ('&Int','&mut Int'):
            mut='mut ' if mode=='&mut Int' else ''
            source=self.declarations(mode)+f'''fn main(){{let mut p=pool<Int>(3);
                let mut n=p.new(7);let mut backup=p.new(99);
                let {mut}view={{let scratch=p.new(12);let h=launch(&{mut}n,&scratch);
                    let next=again(->h);BEFORE
                    let {mut}view=finish(->next,&{mut}backup);drop(->scratch);view}};
                AFTER print(*view);LAST drop(->n);drop(->backup);
                let reuse=p.new(11);print(*reuse);}}'''
            valid=source.replace('BEFORE','').replace('AFTER','').replace('LAST','')
            with self.subTest(mode=mode):
                verify_program(valid)
                code=compile_source(valid)
                result=self.run_c_oracle(code)
                self.assertEqual(result.stdout,'12\n7\n11\n')
                self.assertEqual(result.stderr.count('destroy scratch=12'),1)
                failure=self.run_c_oracle(inject_submission_failure(code, asynchronous=False, at=1))
                self.assertEqual(failure.stdout,'99\n11\n')
                self.assertEqual(failure.stderr.count('destroy scratch=12'),1)
                for where,operation in (('BEFORE','drop(->scratch);'),('AFTER','drop(->n);'),
                                        ('AFTER','drop(->backup);'),('AFTER','n.set(8);')):
                    bad=source.replace(where,operation).replace('BEFORE','').replace('AFTER','').replace('LAST','')
                    if operation in ('drop(->n);','drop(->backup);'):
                        final=bad.rfind(operation)
                        bad=bad[:final]+bad[final+len(operation):]
                    self.rejected(bad)
                self.rejected(source.replace('BEFORE','').replace('AFTER','p.reset();').replace('LAST',''),
                              'reset interdit',allow_legacy_reset=True)
                after=source.replace('BEFORE','').replace('AFTER','').replace('LAST','n.set(8);')
                self.assertEqual(self.run_c_oracle(compile_source(after)).stdout,'12\n7\n11\n')

    def test_opaque_caller_has_no_function_bodies(self):
        declarations=self.declarations()
        interface=verify_program(declarations)
        script='''let mut p=pool<Int>(3);let n=p.new(7);let backup=p.new(99);let scratch=p.new(12);
            let h=launch(&n,&scratch);let next=again(->h);let view=finish(->next,&backup);
            drop(->scratch);CHECK print(*view);drop(->n);drop(->backup);'''
        for operation in ('','drop(->n);','drop(->backup);'):
            check=Compiler();check.contract_calls=True;check.function_contracts=interface.function_contracts
            actual=script.replace('CHECK',operation)
            if operation:
                last=actual.rfind(operation)
                actual=actual[:last]+actual[last+len(operation):]
            nodes=Parser(actual).parse();check.index(nodes)
            if operation:
                with self.assertRaisesRegex(Error,'emprunt|capture'):check.block('root',nodes)
            else:
                check.block('root',nodes)
                self.assertEqual(check.async_definitions,{})
                self.assertEqual(check.functions,{})

    def test_shared_result_from_mutable_capture_keeps_ancestor(self):
        source='''async fn work(v:&mut Int)->&Int{yield;return &*v;}
            fn launch(v:&mut Int)-><-runtime::Handle<&Int>{let h=runtime::spawn(->work(v));return <-h;}
            fn relay(h:->runtime::Handle<&Int>)-><-runtime::Handle<&Int>{return <-h;}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);let mut writer=&mut n;
                let h=launch(&mut *writer);let next=relay(->h);
                match next.join(){Ok(view)=>{CHECK print(*view);writer.set(9);},Err(_)=>{}}
                print(*n);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'7\n9\n')
        for operation in ('writer.set(8);','print(*n);','drop(->n);'):
            self.rejected(source.replace('CHECK',operation))
        direct=source.replace('let mut writer=&mut n;','').replace(
            'launch(&mut *writer)','runtime::spawn(->work(&mut n))').replace('writer.set','n.set')
        self.assertEqual(self.run_c_oracle(compile_source(direct.replace('CHECK',''))).stdout,'7\n9\n')
        for operation in ('n.set(8);','print(*n);'):
            self.rejected(direct.replace('CHECK',operation))

    def test_lifetime_model(self):
        declarations='''async fn first(a:&Int,scratch:&Int)->&Int{print(*scratch);yield;return a;}
            async fn second(scratch:&Int,b:&Int)->&Int{print(*scratch);yield;return b;}
            fn choose(flag:bool,a:&Int,b:&Int,scratch:&Int)-><-runtime::Handle<&Int>{
                let h=if flag{let h=runtime::spawn(->first(a,scratch));<-h}
                    else{let h=runtime::spawn(->second(scratch,b));<-h};return <-h;}
            fn finish(h:->runtime::Handle<&Int>,backup:&Int)->&Int{
                match h.join(){Ok(v)=>{return v;},Err(_)=>{return backup;}}}'''
        # Independent sets of objects reachable before and after joining.
        # scratch is used during execution, never returned. Both branches count.
        names=('a','b','scratch')
        bindings={n:f'let {n}=p.new({v});' for n,v in zip(names,(7,9,12))}
        for joined in (False,True):
            required={'a','b'} if joined else set(names)
            for outer in itertools.product((False,True),repeat=3):
                available={n for n,flag in zip(names,outer) if flag}
                for flag in ('true','false'):
                    source=declarations+'fn main(){let mut p=pool<Int>(4);let backup=p.new(99);'
                    source+=''.join(bindings[n] for n in names if n in available)
                    source+='let received={'+''.join(bindings[n] for n in names if n not in available)
                    source+=f'let h=choose({flag},&a,&b,&scratch);'
                    if joined:source+='let view=finish(->h,&backup);view};print(*received);}'
                    else:source+='<-h};let view=finish(->received,&backup);print(*view);}'
                    with self.subTest(joined=joined,outer=outer,flag=flag):
                        if required <= available:
                            verify_program(source)
                            self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,
                                             '12\n'+('7' if flag=='true' else '9')+'\n')
                        else:self.rejected(source)

    def test_inline_array_and_structure_targets(self):
        for declaration,initialize,argument,invalid in (
            ('','let mut data=[7,8];','&mut data[0]','data[0]=9;'),
            ('struct Point{x:Int,y:Int}','let mut data=Point{x:7,y:8};','&mut data.x','data.x=9;'),
        ):
            source=declaration+'''async fn work(v:&mut Int)->&mut Int{yield;return v;}
                fn launch(v:&mut Int)-><-runtime::Handle<&mut Int>{let h=runtime::spawn(->work(v));return <-h;}
                fn relay(h:->runtime::Handle<&mut Int>)-><-runtime::Handle<&mut Int>{return <-h;}
                fn main(){'''+initialize+f'''let h=launch({argument});let next=relay(->h);
                match next.join(){{Ok(view)=>{{CHECK print(*view);*view=11;}},Err(_)=>{{}}}}}}'''
            with self.subTest(argument=argument):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'7\n')
                self.rejected(source.replace('CHECK',invalid))
                shared=source.replace('&mut ', '&').replace('*view=11;', '')
                self.assertEqual(self.run_c_oracle(compile_source(shared.replace('CHECK',''))).stdout,'7\n')
                self.rejected(shared.replace('CHECK',invalid))

    def test_mutable_byte_result_and_payload_mismatch(self):
        source='''async fn work(v:&mut u8)->&mut u8{yield;return v;}
            fn launch(v:&mut u8)-><-runtime::Handle<&mut u8>{let h=runtime::spawn(->work(v));return <-h;}
            fn relay(h:->runtime::Handle<&mut u8>)-><-runtime::Handle<&mut u8>{return <-h;}
            fn main(){let mut p=pool<Vector<u8>>(1);let mut bytes=p.new();let byte:u8=7;bytes.push(byte);
                let h=launch(&mut bytes[0]);let next=relay(->h);
                match next.join(){Ok(view)=>{CHECK print(*view as Int);let replacement:u8=11;*view=replacement;},Err(_)=>{}}
                print(bytes[0] as Int);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'7\n11\n')
        self.rejected(source.replace('CHECK','drop(->bytes);'))
        self.rejected(source.replace('CHECK','').replace('Handle<&mut u8>','Handle<&mut Int>'),
                      'handle .*attendu|type|Int.*attendu')

    def test_detached_field_and_retained_mutable_ancestor(self):
        import test_async_detached_field_returns as detached
        import test_stored_field_reborrows as stored
        for source in (detached.AsyncDetachedFieldTests.program(),
                       stored.StoredFieldReborrowTests.program(async_result=True,use="")):
            declarations='''fn launch(v:&View)-><-runtime::Handle<&Int>{let h=runtime::spawn(->work(v));return <-h;}
                fn relay(h:->runtime::Handle<&Int>)-><-runtime::Handle<&Int>{return <-h;}'''
            source=source.replace('fn main()',declarations+'fn main()').replace(
                'let h=runtime::spawn(->work(&v));','let initial=launch(&v);let h=relay(->initial);')
            with self.subTest(source=source):
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'7\n7\n')
                self.rejected(source.replace('print(r);','drop(->data);print(r);'))
                if 'writer' in source:
                    self.rejected(source.replace('print(r);drop(->writer);','drop(->writer);print(r);'))

    def test_scalar_vector_element_borrow_boundaries(self):
        for typ,decl in (('Int','let value=7;'),('u8','let value:u8=7;')):
            source=f'''fn take(v:->Vector<{typ}>)->Int{{drop(->v);return 0;}}
                fn main(){{let mut p=pool<Vector<{typ}>>(1);let mut values=p.new();{decl}values.push(value);
                    let mut view=&mut values[0];CHECK print(*view as Int);drop(->values);}}'''
            with self.subTest(typ=typ):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',''))).stdout,'7\n')
                for operation in ('values.push(value);','print(values[0] as Int);'):
                    self.rejected(source.replace('CHECK',operation))
                self.rejected(f'fn readonly(v:&Vector<{typ}>){{let mut view=&mut v[0];print(*view as Int);}}'+
                              source.replace('CHECK',''), 'mutable|immuable|emprunt en lecture')
                self.rejected(source.replace('CHECK','').replace('&mut values[0]',
                                                        '&mut values[take(->values)]'))
                failed=source.replace('CHECK','').replace('&mut values[0]','&mut values[2]')
                self.run_c_oracle(compile_source(failed),expected_error='indice')

    def test_byte_join_helper_returns_inline_reference(self):
        source=(Path(__file__).resolve().parents[1]/'validation/public-borrowed-handle-byte-finish.crb').read_text()
        verify_program(source)
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'7\n11\n')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1)).stdout,
                         '99\n7\n')
        for operation in ('drop(->values);','drop(->backup);'):
            self.rejected(source.replace('print(*view as Int);',operation+'print(*view as Int);'))

if __name__=='__main__':unittest.main()
