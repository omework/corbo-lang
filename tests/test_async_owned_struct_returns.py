"""Returned owned graphs retain every field source beyond await and join."""
from pathlib import Path
from itertools import product
import unittest
from crust import verify_program
import test_select_source as source_tests
import test_native_blocks as native_tests
import test_suspended_cleanup as cleanup_tests

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-owned-async-struct-return.crb').read_text()


class AsyncOwnedStructReturnTests(unittest.TestCase):
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    run_source=source_tests.SelectSourceTests.run_source
    run_native=native_tests.NativeBlockTests.run_native
    refused=source_tests.SelectSourceTests.refused
    native=cleanup_tests.SuspendedCleanupTests.native

    def test_recorded_return_and_failure(self):
        run=self.run_source(BASE)
        self.assertEqual(run.stdout,'7\n30\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)
        self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)
        self.assertLess(run.stderr.index('destroy value=7'),run.stderr.index('destroy holder=Holder'))
        failed=self.run_native(BASE,fail_submission_at=1)
        self.assertEqual(failed.stdout,'30\n')
        self.assertEqual(failed.stderr.count('destroy value=7\n'),1)
        self.assertEqual(failed.stderr.count('destroy holder=Holder\n'),1)
        self.refused(BASE.replace('return <-h','return h'),'explicite|transfert')
        self.refused('fn bad()-><-Result<A<Unknown>,runtime::Error>{loop{}}fn main(){}',
                     'inconnu')

    def test_async_chain_and_field_usage_after_wait(self):
        for body in ('return <-relay(->h).await;',
                     'let value=relay(->h).await;print(*value.value);return <-value;'):
            source=BASE.replace('fn main()', 'async fn outer(h:->A<Holder>)-><-A<Holder>{'+body+'}\nfn main()')
            source=source.replace('runtime::spawn(->relay(->holder))','runtime::spawn(->outer(->holder))')
            with self.subTest(body=body):
                self.assertEqual(self.run_source(source).stdout,
                                 ('7\n' if 'print' in body else '')+'7\n30\n')

    def test_factories_and_task_forwarding(self):
        helpers='''fn make(h:->A<Holder>)-><-relay{return <-relay(->h);}
            fn again(h:->A<Holder>)-><-relay{return <-make(->h);}
            fn forward(t:->relay)-><-relay{return <-t;}'''
        for expr in ('make(->holder)','again(->holder)','forward(->again(->holder))'):
            source=BASE.replace('fn main()', helpers+'fn main()').replace(
                'runtime::spawn(->relay(->holder))','runtime::spawn(->'+expr+')')
            with self.subTest(expr=expr):
                self.assertEqual(self.run_source(source).stdout,'7\n30\n')

    def test_returned_graph_cannot_outlive_child_pool(self):
        prefix=BASE[:BASE.index('fn main')]
        source=prefix+'''fn main(){let mut holders=pool<Holder>(1);POOLS
            let received={INNER
                let value=values.new(7);let holder=holders.new(value:<-value);
                let h=runtime::spawn(->relay(->holder));
                let result=match h.join(){Ok(received)=>{<-received},Err(_)=>{
                    let value=values.new(9);let holder=holders.new(value:<-value);<-holder}};
                <-result
            };
            print(*received.value);drop(->received);let next=values.new(30);print(*next);}'''
        pool='let mut values=pool<Int>(1);'
        self.assertEqual(self.run_source(source.replace('POOLS',pool).replace('INNER','')).stdout,'7\n30\n')
        self.refused(source.replace('POOLS','').replace('INNER',pool).replace(
            'let next=values.new(30);print(*next);',''), 'pool|source|survit|surviv')

    def test_result_through_sync_helper(self):
        helper='''fn finish(e:->Execution<relay>)-><-Result<A<Holder>,runtime::Error>{
            let result=e.join();return <-result;}'''
        source=BASE.replace('fn main()',helper+'fn main()').replace(
            'match execution.join()', 'match finish(->execution)')
        self.assertEqual(self.run_source(source).stdout,'7\n30\n')
        relay='''fn pass(r:->Result<A<Holder>,runtime::Error>)-><-Result<A<Holder>,runtime::Error>{return <-r;}'''
        source=source.replace('fn main()',relay+'fn main()').replace(
            'match finish(->execution)','match pass(->finish(->execution))')
        self.assertEqual(self.run_source(source).stdout,'7\n30\n')

    def test_conditional_tasks_keep_graph(self):
        for flag in ('true','false'):
            source=BASE.replace('let execution = runtime::spawn(->relay(->holder));',
                'let task=if '+flag+'{holder ->;let t=relay(->holder);<-t}else{holder ->;let t=relay(->holder);<-t};'
                'let execution=runtime::spawn(->task);')
            with self.subTest(flag=flag):
                self.assertEqual(self.run_source(source).stdout,'7\n30\n')

    def test_result_junctions_keep_descendants(self):
        for expression in (
            'if true{execution ->;let r=execution.join();<-r}else{execution ->;let r=execution.join();<-r}',
            'loop{execution ->;let r=execution.join();break <-r;}',
        ):
            source=BASE.replace('match execution.join()', 'let r='+expression+';match r')
            with self.subTest(expression=expression):
                self.assertEqual(self.run_source(source).stdout,'7\n30\n')

    def test_nested_owned_graph_lifetime_model(self):
        prefix='''struct Child{value:A<Int>}struct Root{child:A<Child>,mark:Int}
            async fn work(r:->A<Root>)-><-A<Root>{yield;return <-r;}
            fn make(r:->A<Root>)-><-work{return <-work(->r);}'''
        pools={'numbers':'let mut numbers=pool<Int>(1);',
               'children':'let mut children=pool<Child>(1);',
               'roots':'let mut roots=pool<Root>(1);'}
        for flags in product((False,True),repeat=3):
            short={name for name,inside in zip(pools,flags) if inside}
            before=''.join(v for k,v in pools.items() if k not in short)
            inside=''.join(v for k,v in pools.items() if k in short)
            source=prefix+'fn main(){'+before+'let result={'+inside+'''
                let value=numbers.new(7);let child=children.new(value:<-value);
                let root=roots.new(child:<-child,mark:9);
                let execution=runtime::spawn(->make(->root));
                let result=execution.join();<-result};
                match result{Ok(root)=>{print(root.mark);drop(->root);},Err(_)=>{}}}'''
            with self.subTest(short=short):
                if short:
                    self.refused(source,'pool|source|survit|surviv')
                else:
                    run=self.run_source(source)
                    self.assertEqual(run.stdout,'9\n')
                    self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                                     ['destroy value=7','destroy child=Child','destroy root=Root'])

    def test_field_loan_reserves_returned_graph(self):
        body='let view=&*received.value;print(*view);drop(->received);'
        source=BASE.replace('print(*received.value); drop(->received);',body)
        self.assertEqual(self.run_source(source).stdout,'7\n30\n')
        self.refused(source.replace(body,'let view=&*received.value;drop(->received);print(*view);'),
                     'emprunt|référenc')

    def test_nested_result_and_async_capture(self):
        helpers='''async fn deliver(r:->Result<A<Holder>,runtime::Error>)-><-Result<A<Holder>,runtime::Error>{
            yield;return <-r;}
            async fn wrap(h:->A<Holder>)-><-Result<A<Holder>,runtime::Error>{
                let execution=runtime::spawn(->relay(->h));
                let result=execution.await;return <-deliver(->result).await;}'''
        source=BASE.replace('fn main()',helpers+'fn main()').replace(
            'runtime::spawn(->relay(->holder))','runtime::spawn(->wrap(->holder))').replace(
            'Ok(received) => { print(*received.value); drop(->received); }',
            'Ok(inner) => {match inner{Ok(received)=>{print(*received.value);drop(->received);},Err(_)=>{}}}')
        self.assertEqual(self.run_source(source).stdout,'7\n30\n')

    def test_identity_and_cleanup_before_and_after_remittance(self):
        for finished in (False,True):
            ending=('assert(task_poll(task)==TASK_COMPLETE);Cell *result=NULL;'
                    'assert(task_take(task,&result));assert(result==holder);'
                    'assert(cell_load_ref(result,0)==value);cell_drop(result);' if finished else
                    'assert(task_owned_discardable(task));assert(task_drop_owned(task));')
            with self.subTest(finished=finished):
                run=self.native(BASE,'''
    Source numbers=source_pool(1);Source arms[]={source_pool_layout(1,sizeof(Cell *))};
    size_t offsets[]={0};unsigned char kinds[]={2};
    arms[0].arm_name="";arms[0].field_count=1;arms[0].field_offsets=offsets;arms[0].field_kinds=kinds;
    Source holders=source_enum_pool(arms,1,"Holder");
    Cell *value=cell_new(&numbers,7,"leaf");Cell *holder=enum_new(&holders,0,"root");
    cell_store_ref(holder,0,value);CrustTask *task=crust_async_relay_create(holder);
    assert(task_poll(task)==TASK_SUSPENDED);
'''+ending+'''
    Cell *next=cell_new(&numbers,8,"next");assert(next==value);
    Cell *other=enum_new(&holders,0,"other");assert(other==holder);cell_store_ref(other,0,next);cell_drop(other);
    source_close(&holders);source_close(&numbers);
''')
                self.assertEqual(run.stderr.count('destroy leaf=7\n'),1)
                self.assertEqual(run.stderr.count('destroy root=Holder\n'),1)
                self.assertLess(run.stderr.index('destroy leaf=7'),run.stderr.index('destroy root=Holder'))

    def test_field_source_requirement_in_legacy_contract(self):
        # reset is absent from the normal prototype. Its historical checking
        # mode exposes the source-disjointness contract independently of C.
        source=BASE[:BASE.index('fn main')]+'''
            fn finish(e:->Execution<relay>,p:&mut Pool<Int>)->Int{
                let r=e.join();p.reset();return match r{
                    Ok(h)=>{let n=*h.value;drop(->h);n},Err(_)=>{0}};}'''
        contract=verify_program(source,allow_legacy_reset=True).function_contracts['finish']
        pairs={frozenset((side.kind,side.index,side.name) for side in (r.left,r.right))
               for r in contract.constraints.requirements if r.relation=='distinct'}
        for retained in (('task_result_parameter',0,''),('task_result_field_parameter',0,'.value')):
            self.assertIn(frozenset({('source_parameter',1,''),retained}),pairs)


if __name__=='__main__':unittest.main()
