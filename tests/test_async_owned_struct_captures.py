"""Transferred structure graphs keep every pool alive until task cleanup."""
from pathlib import Path
from itertools import product
import unittest

from crust import verify_program
import test_native_blocks as native_tests
import test_select_source as source_tests
import test_suspended_cleanup as cleanup_tests

ROOT=Path(__file__).resolve().parents[1]


class AsyncOwnedStructCaptureTests(unittest.TestCase):
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    run_native=native_tests.NativeBlockTests.run_native
    run_source=source_tests.SelectSourceTests.run_source
    refused=source_tests.SelectSourceTests.refused
    native=cleanup_tests.SuspendedCleanupTests.native

    def test_recorded_capture_normal_failure_and_inactive_drop(self):
        source=(ROOT/'validation/open-owned-async-struct.crb').read_text()
        for failure,expected in ((None,'9\n30\n'),(1,'20\n30\n')):
            with self.subTest(failure=failure):
                run=self.run_native(source,fail_submission_at=failure)
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy value=7\n'),1)
                self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)
                self.assertLess(run.stderr.index('destroy value=7'),run.stderr.index('destroy holder=Holder'))
        inactive=source.replace('let h=runtime::spawn(->consume(->holder));\n    match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(20);}}',
                                'let task=consume(->holder);drop(->task);')
        run=self.run_source(inactive)
        self.assertEqual(run.stdout,'30\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)
        self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)

    def test_named_fields_mutability_and_local_transfer(self):
        source='''struct Holder{value:A<Int>,mark:Int}
            async fn consume(mut h:->Holder)->Int{
                h.mark=3;yield;print(*h.value);print(h.mark);
                {h ->;let moved=<-h;print(*moved.value);drop(->moved);}
                return 9;}
            fn main(){let mut values=pool<Int>(1);let mut holders=pool<Holder>(1);
                let value=values.new(7);let holder=holders.new(value:<-value);
                let h=runtime::spawn(->consume(->holder));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                let reused=values.new(30);print(*reused);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n3\n7\n9\n30\n')
        self.refused(source.replace('consume(mut h:', 'consume(h:'),'mutable')
        self.refused(source.replace('consume(->holder)','consume(holder)'),'transfert|utiliser ->')
        self.refused(source.replace('return 9;', 'print(*h.value);return 9;'),'consommé|utilisable|transfér')

    def test_forwarded_captures_and_prepared_cleanup(self):
        source='''struct Holder{value:A<Int>}
            async fn child(h:->Holder,n:Int)->Int{yield;print(*h.value);return n;}
            async fn pause()->Int{yield;return 8;}
            async fn work(h:->Holder)->Int{yield;return child(->h,ARG).await;}
            fn main(){let mut values=pool<Int>(1);let mut holders=pool<Holder>(1);
                let value=values.new(7);let holder=holders.new(value:<-value);
                let h=runtime::spawn(->work(->holder));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                let reused=values.new(30);print(*reused);}'''
        for argument,expected in (('pause().await','7\n8\n30\n'),('{yield;return 9;}','9\n30\n')):
            with self.subTest(argument=argument):
                run=self.run_source(source.replace('ARG',argument))
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy value=7\n'),1)
                self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)
        self.refused(source.replace('ARG','pause().await').replace('yield;return child','yield;let other=child(->h,1);drop(->other);return child'),
                     'consommé|utilisable|transfér')

    def test_factory_contract_keeps_descendant_source(self):
        invalid=(ROOT/'validation/open-owned-task-factory-short-pool.crb').read_text()
        self.refused(invalid,'pool de capture|survit')
        prefix=invalid[:invalid.index('fn main')]
        contract=verify_program(prefix).function_contracts['make']
        self.assertEqual({(s.kind,s.index,s.name) for s in contract.result.task_sources},
                         {('allocation_parameter',0,''),('allocation_field_parameter',0,'.value')})
        # The relayed contract must retain this field without a concrete pool.
        prefix+='fn again(h:->Holder)-><-consume{return <-make(->h);}'
        summary=verify_program(prefix).function_contracts['again'].result
        self.assertEqual(summary.task_sources,contract.result.task_sources)
        self.refused(invalid.replace('fn main', 'fn again(h:->Holder)-><-consume{return <-make(->h);}\nfn main').replace(
            'let task=make(->holder)','let task=again(->holder)'), 'pool de capture|survit')
        valid=prefix+'''fn main(){let mut holders=pool<Holder>(1);let mut values=pool<Int>(1);
            let value=values.new(7);let holder=holders.new(value:<-value);
            let task=again(->holder);let h=runtime::spawn(->task);
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
            let reused=values.new(30);print(*reused);}'''
        self.assertEqual(self.run_source(valid).stdout,'9\n30\n')

    def test_native_thread_whole_capture(self):
        source='''struct Holder{value:A<Int>}
            fn main(){let mut values=pool<Int>(1);let mut holders=pool<Holder>(1);
                let value=values.new(7);let holder=holders.new(value:<-value);
                let h=runtime::thread({->(holder);return *holder.value;});
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(20);}}
                let reused=values.new(30);print(*reused);}'''
        for failure,expected in ((False,'7\n30\n'),(True,'20\n30\n')):
            with self.subTest(failure=failure):
                run=self.run_native(source,fail_native=failure)
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy value=7\n'),1)
                self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)

    def test_collection_fields_and_strict_projection_type(self):
        for typ,fill in (('String','let mut value=p.new();value.push_str("text");'),
                         ('Vector<Int>','let mut value=p.new();value.push(7);'),
                         ('Vector<u8>','let mut value=p.new();value.push(7);')):
            source=f'''struct Holder{{value:A<{typ}>}}
                async fn work(h:->Holder)->Int{{yield;drop(->h);return 9;}}
                fn main(){{let mut p=pool<{typ}>(1);let mut holders=pool<Holder>(1);
                    {fill}let holder=holders.new(value:<-value);
                    let h=runtime::spawn(->work(->holder));
                    match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}
                    let reused=p.new();drop(->reused);}}'''
            with self.subTest(typ=typ):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'9\n')
                self.assertEqual(run.stderr.count('destroy value='),1)
                self.refused(source.replace('yield;drop(->h);','yield;print(*h.value);drop(->h);'),
                             'type|Int|incompatible')

    def test_field_borrow_ends_before_whole_capture(self):
        source=(ROOT/'validation/open-owned-async-struct.crb').read_text()
        borrowed=source.replace('let h=runtime::spawn',
                                'let view=&*holder.value;print(*view);let h=runtime::spawn')
        self.assertEqual(self.run_source(borrowed).stdout,'7\n9\n30\n')
        self.refused(borrowed.replace('match h.join()', 'print(*view);match h.join()'),
                     'emprunt encore utilisé')
        self.refused(source.replace('let h=runtime::spawn',
                                   'drop(->holder);let h=runtime::spawn'),
                     'consommé|utilisable|détruit')

    def test_nested_graph_source_model(self):
        # Each path has one distinct pool per owned allocation. Any of these
        # pools ending before the inactive task makes the transfer invalid.
        prefix='''struct Child{value:A<Int>} struct Root{child:A<Child>,mark:Int}
            async fn work(r:->Root)->Int{yield;return r.mark;}
            fn make(r:->Root)-><-work{return <-work(->r);}
            fn relay(r:->Root)-><-work{return <-make(->r);}'''
        pools={'numbers':'let mut numbers=pool<Int>(1);',
               'children':'let mut children=pool<Child>(1);',
               'roots':'let mut roots=pool<Root>(1);'}
        body='''let value=numbers.new(7);let child=children.new(value:<-value);
                let root=roots.new(child:<-child,mark:9);let task=relay(->root);'''
        for factory,mask in product(('work','make','relay'),product((False,True),repeat=3)):
            short={name for name,inside in zip(pools,mask) if inside}
            outside=''.join(v for k,v in pools.items() if k not in short)
            inner=''.join(v for k,v in pools.items() if k in short)
            source=prefix+'fn main(){'+outside+'let task={'+inner+body.replace('relay(->root)',factory+'(->root)')+'''<-task};
                let h=runtime::spawn(->task);match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
            with self.subTest(factory=factory,short=short):
                if short:
                    self.refused(source,'pool|survit')
                else:
                    run=self.run_source(source)
                    self.assertEqual(run.stdout,'9\n')
                    destroyed=[line for line in run.stderr.splitlines() if line.startswith('destroy ')]
                    self.assertEqual(destroyed,['destroy value=7','destroy child=Child','destroy root=Root'])
        summary=verify_program(prefix).function_contracts['relay'].result
        self.assertEqual({s.name for s in summary.task_sources if s.kind=='allocation_field_parameter'},
                         {'.child','.child/.value'})

    def test_identity_and_cleanup_at_each_task_state(self):
        source=(ROOT/'validation/open-owned-async-struct.crb').read_text()
        for state in ('inactive','suspended','complete','prepared'):
            program=source
            if state=='prepared':
                program='''async fn pause()->Int{yield;return 8;}
                    async fn child(h:->Holder,n:Int)->Int{drop(->h);return n;}'''+source.replace(
                    'yield;drop(->h);return 9;', 'return child(->h,pause().await).await;')
            steps='' if state=='inactive' else 'assert(task_poll(task)==TASK_SUSPENDED);'
            if state=='complete':
                steps+='assert(task_poll(task)==TASK_COMPLETE);int result=0;assert(task_take(task,&result));assert(result==9);'
            else:
                steps+='assert(task_owned_discardable(task));assert(task_drop_owned(task));'
            with self.subTest(state=state):
                run=self.native(program,'''
    Source numbers=source_pool(1);
    Source arms[]={source_pool_layout(1,sizeof(Cell *))};
    size_t offsets[]={0};unsigned char kinds[]={2};
    arms[0].arm_name="";arms[0].field_count=1;
    arms[0].field_offsets=offsets;arms[0].field_kinds=kinds;
    Source holders=source_enum_pool(arms,1,"Holder");
    Cell *value=cell_new(&numbers,7,"leaf");Cell *holder=enum_new(&holders,0,"root");
    cell_store_ref(holder,0,value);
    CrustTask *task=crust_async_consume_create(holder);
    assert(((crust_async_consume_state *)task)->value_0==holder);
    assert(cell_load_ref(holder,0)==value);
'''+steps+'''
    Cell *next=cell_new(&numbers,8,"next");assert(next==value);cell_drop(next);
    Cell *other=enum_new(&holders,0,"other");assert(other==holder);
    cell_store_ref(other,0,cell_new(&numbers,9,"other_leaf"));cell_drop(other);
    source_close(&holders);source_close(&numbers);
''')
                self.assertEqual(run.stderr.count('destroy leaf=7\n'),1)
                self.assertEqual(run.stderr.count('destroy root=Holder\n'),1)
                self.assertLess(run.stderr.index('destroy leaf=7'),run.stderr.index('destroy root=Holder'))


if __name__=='__main__':unittest.main()
