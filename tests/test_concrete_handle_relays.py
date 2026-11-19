"""Concrete-to-public handle conversions preserve input result contracts."""
from pathlib import Path
import itertools
import unittest
from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_runtime
from scheduler_faults import inject_submission_failure


class ConcreteHandleRelayTests(unittest.TestCase):
    run_c_oracle=test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def rejected(self, source, **options):
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaisesRegex(Error,'emprunt|capture|réserv|reset|distinct') as caught:
                    check(source,**options)
                self.assertNotIn('invariant interne',str(caught.exception))

    def test_recorded_return_and_last_use(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-concrete-borrowed-handle-relay.crb').read_text()
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'9\n')
        for operation in ('print(*data);','drop(->data);'):
            self.rejected(source.replace('view.set(9);',operation+'view.set(9);'))
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('print(*view);',
            'print(*view);data.set(11);print(*data);'))).stdout,'9\n11\n')

    @staticmethod
    def field_program(field='inline',shared=False):
        mode='&' if shared else '&mut'
        fields={'inline':'data:Int,other:Int','mutable':'data:&mut Int,other:Int',
                'shared':'data:&Int,other:Int'}[field]
        expression=f'{mode} v.data' if field=='inline' else 'v.data' if field=='shared' else f'{mode} *v.data'
        initializer='data:7,other:8' if field=='inline' else ('data:&data,other:8' if field=='shared' else 'data:&mut data,other:8')
        output='print(*n);' if shared else 'n.set(9);print(*n);'
        storage='' if field=='inline' else 'let mut p=pool<Int>(1);let mut data=p.new(7);'
        return f'''struct View{{{fields}}}
            async fn leaf(v:&mut View)->{mode} Int{{yield;return {expression};}}
            fn launch(v:&mut View)-><-Execution<leaf>{{let h=runtime::spawn(->leaf(v));return <-h;}}
            fn finish(h:->runtime::Handle<{mode} Int>)->{mode} Int{{
                return match h.join(){{Ok(v)=>{{v}},Err(_)=>{{loop{{}}}}}};}}
            fn relay(h:->Execution<leaf>)->{mode} Int{{return finish(->h);}}
            fn main(){{{storage}let mut v=View{{{initializer}}};
                let h=launch(&mut v);let mut n=relay(->h);CHECK {output}}}'''

    def test_inline_indirect_and_detached_fields(self):
        for field,shared in (('inline',False),('inline',True),('mutable',False),('mutable',True),('shared',True)):
            source=self.field_program(field,shared)
            with self.subTest(field=field,shared=shared):
                operation='drop(->v);' if field=='shared' else 'v.other=12;'
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK',operation))).stdout,
                                 '7\n' if shared else '9\n')
                self.rejected(source.replace('CHECK','drop(->data);' if field=='shared' else 'drop(->v);'))

    def test_independent_capture_lifetime_model(self):
        declarations='''async fn leaf(a:&mut Int,b:&mut Int,scratch:&Int,flag:Bool)->&mut Int{
                print(*scratch);yield;return if flag{a}else{b};}
            fn finish(h:->runtime::Handle<&mut Int>)->&mut Int{
                return match h.join(){Ok(v)=>{v},Err(_)=>{loop{}}};}
            fn relay(h:->Execution<leaf>)->&mut Int{return finish(->h);}'''
        for joined,mask,flag in itertools.product((False,True),range(8),('true','false')):
            names=('a','b','scratch')
            protected={'a','b'} if joined else set(names)
            destroyed={name for i,name in enumerate(names) if mask&(1<<i)}
            drops=''.join(f'drop(->{name});' for name in names if name in destroyed)
            source=declarations+'''fn main(){let mut p=pool<Int>(3);let mut a=p.new(7);
                let mut b=p.new(8);let scratch=p.new(12);'''
            source+=f'let h=runtime::spawn(->leaf(&mut a,&mut b,&scratch,{flag}));'
            source+=('let mut n=relay(->h);'+drops if joined else drops+'let mut n=relay(->h);')
            source+='print(*n);}'
            with self.subTest(joined=joined,mask=mask,flag=flag):
                if destroyed&protected:self.rejected(source)
                else:self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'12\n'+('7' if flag=='true' else '8')+'\n')

    def test_concrete_sources_survive_public_conversion(self):
        declarations='''async fn leaf(v:&mut Int)->&mut Int{yield;return v;}
            fn launch(v:&mut Int)-><-Execution<leaf>{let h=runtime::spawn(->leaf(v));return <-h;}
            fn finish(h:->runtime::Handle<&mut Int>)->&mut Int{
                return match h.join(){Ok(v)=>{v},Err(_)=>{loop{}}};}
            fn read(h:->Execution<leaf>,p:&mut Pool<Int>)->Int{
                let n=finish(->h);p.reset();return *n;}
            fn route(v:&mut Int,p:&mut Pool<Int>)->Int{let h=launch(v);return read(->h,p);}'''
        interface=verify_program(declarations,allow_legacy_reset=True)
        def pairs(name):
            return {frozenset(((r.left.kind,r.left.index),(r.right.kind,r.right.index)))
                    for r in interface.function_constraints[name].all_requirements if r.relation=='distinct'}
        self.assertIn(frozenset((('source_parameter',1),('task_reference_result_parameter',0))),pairs('read'))
        self.assertIn(frozenset((('source_parameter',1),('allocation_parameter',0))),pairs('route'))
        for target in ('p','q'):
            script=f'''let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let mut data=p.new(7);let n=route(&mut data,&mut {target});print(n);'''
            source=declarations+'fn main(){'+script+'}'
            with self.subTest(target=target):
                if target=='p':self.rejected(source,allow_legacy_reset=True)
                else:self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n')
                opaque=Compiler(allow_legacy_reset=True);opaque.contract_calls=True
                opaque.function_contracts=interface.function_contracts
                nodes=Parser(script).parse();opaque.index(nodes)
                if target=='q':opaque.block('root',nodes)
                else:
                    with self.assertRaisesRegex(Error,'distinct'):opaque.block('root',nodes)
                self.assertFalse(opaque.functions)
                self.assertFalse(opaque.async_definitions)

    def test_reset_after_last_use_and_direct_construction(self):
        declarations='''async fn leaf(v:&mut Int)->&mut Int{yield;return v;}
            fn finish(h:->runtime::Handle<&mut Int>)->&mut Int{
                return match h.join(){Ok(v)=>{v},Err(_)=>{loop{}}};}
            fn read(h:->Execution<leaf>,p:&mut Pool<Int>)->Int{
                let n=finish(->h);let result=*n;p.reset();return result;}
            fn route(v:&mut Int,p:&mut Pool<Int>)->Int{
                let h=runtime::spawn(->leaf(v));return read(->h,p);}'''
        checked=verify_program(declarations,allow_legacy_reset=True)
        self.assertFalse(checked.function_constraints['read'].all_requirements)
        source=declarations+'''fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);
            let old=route(&mut n,&mut p);print(old);let next=p.new(9);print(*next);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n9\n')
        bad=declarations.replace('let result=*n;p.reset();','p.reset();let result=*n;')
        self.rejected(source.replace(declarations,bad),allow_legacy_reset=True)

    def test_failed_launch_fallback_keeps_both_possible_targets(self):
        source='''async fn leaf(v:&mut Int)->&mut Int{yield;return v;}
            fn finish(h:->runtime::Handle<&mut Int>,backup:&mut Int)->&mut Int{
                return match h.join(){Ok(v)=>{v},Err(_)=>{backup}};}
            fn relay(h:->Execution<leaf>,backup:&mut Int)->&mut Int{return finish(->h,backup);}
            fn main(){let mut p=pool<Int>(2);let mut data=p.new(7);let mut backup=p.new(99);
                let h=runtime::spawn(->leaf(&mut data));let mut n=relay(->h,&mut backup);
                CHECK print(*n);n.set(12);print(*data);print(*backup);}'''
        code=compile_source(source.replace('CHECK',''))
        self.assertEqual(self.run_c_oracle(code).stdout,'7\n12\n99\n')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1)).stdout,'99\n7\n12\n')
        for name in ('data','backup'):self.rejected(source.replace('CHECK',f'drop(->{name});'))

    def test_projected_field_sources_through_concrete_factory(self):
        for field,shared in (('mutable',False),('mutable',True),('shared',True)):
            declarations=self.field_program(field,shared).split('fn main()')[0]
            declarations+='''fn route(v:&mut View,p:&mut Pool<Int>)->Int{
                let h=launch(v);let n=relay(->h);p.reset();return *n;}'''
            checked=verify_program(declarations,allow_legacy_reset=True)
            obligations=checked.function_constraints['route'].all_requirements
            pairs={frozenset(((r.left.kind,r.left.index,r.left.name),
                              (r.right.kind,r.right.index,r.right.name))) for r in obligations}
            with self.subTest(field=field,shared=shared):
                self.assertIn(frozenset((('source_parameter',1,''),('allocation_field_parameter',0,'.data'))),pairs)
                if field=='shared':
                    self.assertFalse(any(s.kind in ('allocation_parameter','reservation_parameter')
                                         and s.index==0 for r in obligations for s in (r.left,r.right)))
                reference='&data' if field=='shared' else '&mut data'
                for target in ('p','q'):
                    source=declarations+f'''fn main(){{let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                        let mut data=p.new(7);let mut v=View{{data:{reference},other:8}};
                        let result=route(&mut v,&mut {target});print(result);}}'''
                    if target=='p':self.rejected(source,allow_legacy_reset=True)
                    else:self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n')

    def test_pending_nonresult_capture_reset_order(self):
        template='''async fn leaf(v:&mut Int,scratch:&Int)->&mut Int{print(*scratch);yield;return v;}
            fn finish(h:->runtime::Handle<&mut Int>,p:&mut Pool<Int>)->Int{
                BEFORE let n=match h.join(){Ok(v)=>{v},Err(_)=>{return 99;}};
                let result=*n;AFTER return result;}
            fn route(v:&mut Int,scratch:&Int,p:&mut Pool<Int>)->Int{
                let h=runtime::spawn(->leaf(v,scratch));return finish(->h,p);}'''
        script='''let mut p=pool<Int>(1);let mut q=pool<Int>(1);let mut data=p.new(7);
            let scratch=q.new(12);let n=route(&mut data,&scratch,&mut q);print(n);'''
        for before in (False,True):
            declarations=template.replace('BEFORE','p.reset();' if before else '').replace('AFTER','' if before else 'p.reset();')
            interface=verify_program(declarations,allow_legacy_reset=True)
            with self.subTest(before=before):
                obligations=interface.function_constraints['route'].all_requirements
                self.assertEqual(any(s.kind=='allocation_parameter' and s.index==1
                                     for r in obligations for s in (r.left,r.right)),before)
                source=declarations+'fn main(){'+script+'}'
                if before:self.rejected(source,allow_legacy_reset=True)
                else:self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'12\n7\n')
                opaque=Compiler(allow_legacy_reset=True);opaque.contract_calls=True
                opaque.function_contracts=interface.function_contracts
                nodes=Parser(script).parse();opaque.index(nodes)
                if before:
                    with self.assertRaisesRegex(Error,'distinct'):opaque.block('root',nodes)
                else:opaque.block('root',nodes)
                self.assertFalse(opaque.functions)

    def test_owned_capture_reset_order(self):
        declarations='''async fn leaf(v:->Int)->Int{yield;return *v;}
            fn finish(h:->runtime::Handle<Int>,p:&mut Pool<Int>)->Int{
                BEFORE let n=match h.join(){Ok(v)=>{v},Err(_)=>{99}};AFTER return n;}
            fn route(v:->Int,p:&mut Pool<Int>)->Int{
                let h=runtime::spawn(->leaf(->v));return finish(->h,p);}'''
        script='''let mut p=pool<Int>(1);let data=p.new(7);
            let n=route(->data,&mut p);print(n);let next=p.new(9);print(*next);'''
        for before in (False,True):
            body=declarations.replace('BEFORE','p.reset();' if before else '').replace('AFTER','' if before else 'p.reset();')
            with self.subTest(before=before):
                source=body+'fn main(){'+script+'}'
                if before:self.rejected(source,allow_legacy_reset=True)
                else:self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n9\n')
                interface=verify_program(body,allow_legacy_reset=True)
                opaque=Compiler(allow_legacy_reset=True);opaque.contract_calls=True
                opaque.function_contracts=interface.function_contracts
                nodes=Parser(script).parse();opaque.index(nodes)
                if before:
                    with self.assertRaisesRegex(Error,'reset|distinct'):opaque.block('root',nodes)
                else:opaque.block('root',nodes)

    def test_byte_result_keeps_inline_address(self):
        source=(Path(__file__).resolve().parents[1]/'validation/public-borrowed-handle-byte-finish.crb').read_text()
        source=source.replace('fn launch(v:&mut u8)-><-runtime::Handle<&mut u8>',
                              'fn launch(v:&mut u8)-><-Execution<work>')
        source=source.replace('fn main()', '''fn relay(h:->Execution<work>,backup:&mut u8)->&mut u8{
            return finish(->h,backup);}fn main()''')
        source=source.replace('let mut view=finish(->h,','let mut view=relay(->h,')
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout,'7\n11\n')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=False,at=1)).stdout,'99\n7\n')
        for target in ('values','backup'):
            self.rejected(source.replace('print(*view as Int);',f'drop(->{target});print(*view as Int);'))

    def test_other_live_handle_still_blocks_reset(self):
        template='''async fn leaf(v:&Int)->Int{yield;return *v;}
            fn finish(h:->runtime::Handle<Int>,p:&mut Pool<Int>)->Int{
                let n=match h.join(){Ok(v)=>{v},Err(_)=>{99}};p.reset();return n;}
            fn main(){let mut p=pool<Int>(1);let data=p.new(7);
                let h=runtime::spawn(->leaf(&data));let other=runtime::spawn(->leaf(&data));
                BEFORE let n=finish(->h,&mut p);print(n);AFTER}'''
        wait='match other.join(){Ok(n)=>{print(n);},Err(_)=>{}}'
        valid=template.replace('BEFORE',wait).replace('AFTER','')
        self.assertEqual(self.run_c_oracle(compile_source(valid,allow_legacy_reset=True)).stdout,'7\n7\n')
        self.rejected(template.replace('BEFORE','').replace('AFTER',wait),allow_legacy_reset=True)

    def test_reference_row_result_sources(self):
        for slot,factory in itertools.product(('0','1','i'),(False,True)):
            declarations=f'''async fn leaf(row:&[&Int;2],i:Int)->&Int{{yield;return &*row[{slot}];}}
                fn finish(h:->runtime::Handle<&Int>)->&Int{{
                    return match h.join(){{Ok(v)=>{{v}},Err(_)=>{{loop{{}}}}}};}}
                fn route(row:&[&Int;2],p:&mut Pool<Int>,i:Int)->Int{{
                    let h=runtime::spawn(->leaf(row,i));let view=finish(->h);p.reset();return *view;}}'''
            if factory:
                declarations=declarations.replace('let h=runtime::spawn(->leaf(row,i));','let h=launch(row,i);')
                declarations+='''fn launch(row:&[&Int;2],i:Int)-><-Execution<leaf>{
                    let h=runtime::spawn(->leaf(row,i));return <-h;}'''
            checked=verify_program(declarations,allow_legacy_reset=True)
            fields={s.name for r in checked.function_constraints['route'].all_requirements
                    for s in (r.left,r.right) if s.kind=='allocation_field_parameter' and s.index==0}
            with self.subTest(slot=slot,factory=factory):
                self.assertEqual(fields,{'0','1'} if slot=='i' else {slot})
                source=declarations+'''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                    let a=p.new(7);let b=q.new(9);let row=[&a,&b];
                    let n=route(&row,&mut q,0);print(n);}'''
                if slot=='0':self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n')
                else:self.rejected(source,allow_legacy_reset=True)

    def test_nonreturning_path_keeps_running_captures(self):
        for owned in (False,True):
            parameter='v:->Int' if owned else 'v:&Int'
            argument='->data' if owned else '&data'
            declarations=f'''async fn leaf({parameter})->Int{{yield;return *v;}}
                fn hang(h:->runtime::Handle<Int>,p:&mut Pool<Int>){{p.reset();loop{{}}}}'''
            for target in ('p','q'):
                source=declarations+f'''fn main(){{let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                    let data=p.new(7);let h=runtime::spawn(->leaf({argument}));hang(->h,&mut {target});}}'''
                with self.subTest(owned=owned,target=target):
                    if target=='p':self.rejected(source,allow_legacy_reset=True)
                    else:
                        verify_program(source,allow_legacy_reset=True)
                        # The accepted program intentionally never terminates.
                        self.assertIn('int main(',compile_source(source,allow_legacy_reset=True))

    def test_spawned_argument_protected_during_later_argument(self):
        declarations='''async fn leaf(v:&Int)->Int{yield;return *v;}
            fn clear(p:&mut Pool<Int>)->Int{p.reset();return 0;}
            fn finish(h:->runtime::Handle<Int>,extra:Int)->Int{
                return match h.join(){Ok(n)=>{n+extra},Err(_)=>{99}};}
            fn route(v:&Int,p:&mut Pool<Int>)->Int{
                return finish(->runtime::spawn(->leaf(v)),clear(p));}'''
        for target in ('p','q'):
            source=declarations+f'''fn main(){{let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let data=p.new(7);let result=route(&data,&mut {target});print(result);}}'''
            with self.subTest(target=target):
                if target=='p':self.rejected(source,allow_legacy_reset=True)
                else:self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n')

    def test_divergent_branch_does_not_retain_capture_on_continuing_path(self):
        source='''async fn leaf(v:&Int)->Int{yield;return *v;}
            fn finish(h:->runtime::Handle<Int>,p:&mut Pool<Int>,flag:bool)->Int{
                let n=if flag{h ->;match h.join(){Ok(v)=>{v},Err(_)=>{99}}}else{loop{}};
                p.reset();return n;}
            fn main(){let mut p=pool<Int>(1);let data=p.new(7);
                let h=runtime::spawn(->leaf(&data));let result=finish(->h,&mut p,true);print(result);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n')

    def test_loop_wait_reset_and_slot_reuse(self):
        source='''async fn leaf(v:&Int)->Int{yield;return *v;}
            fn cycle(p:&mut Pool<Int>)->Int{let mut result=0;let mut i=0;
                while i<3{let data=p.new(i);let h=runtime::spawn(->leaf(&data));
                    result=match h.join(){Ok(v)=>{v},Err(_)=>{99}};p.reset();i=i+1;}
                return result;}
            fn main(){let mut p=pool<Int>(1);print(cycle(&mut p));let next=p.new(9);print(*next);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'2\n9\n')


if __name__=='__main__':unittest.main()
