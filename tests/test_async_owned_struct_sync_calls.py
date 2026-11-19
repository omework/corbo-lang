"""Whole owned graphs cross synchronous calls without losing their sources."""
from pathlib import Path
from itertools import product
import unittest
from crust import verify_program
import test_select_source as source_tests
import test_native_blocks as native_tests
import test_suspended_cleanup as cleanup_tests

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-owned-struct-sync-call.crb').read_text()
RETURN=(ROOT/'validation/open-owned-async-struct-return.crb').read_text()


class AsyncOwnedStructSyncCallTests(unittest.TestCase):
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    run_source=source_tests.SelectSourceTests.run_source
    run_native=native_tests.NativeBlockTests.run_native
    refused=source_tests.SelectSourceTests.refused
    native=cleanup_tests.SuspendedCleanupTests.native

    def test_recorded_consume_and_explicit_marker(self):
        run=self.run_source(BASE)
        self.assertEqual(run.stdout,'7\n30\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)
        self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)
        self.refused(BASE.replace('inspect(->h)','inspect(h)'),'transfert|explicite')
        self.refused(BASE.replace('return inspect(->h);','let n=inspect(->h);print(*h.value);return n;'),
                     'consommé|utilisable|transfér')

    def test_return_and_repeated_transfer(self):
        helpers='''fn identity(h:->A<Holder>)-><-A<Holder>{return <-h;}
            fn again(h:->A<Holder>)-><-A<Holder>{return <-identity(->h);}'''
        for expression in ('identity(->h)','again(->h)','identity(->again(->h))'):
            source=helpers+RETURN.replace('return <-h;','return <-'+expression+';')
            with self.subTest(expression=expression):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'7\n30\n')
                self.assertEqual(run.stderr.count('destroy value=7\n'),1)

    def test_mutable_inline_field_and_wrong_type(self):
        source=BASE.replace('struct Holder { value: A<Int> }','struct Holder { value: A<Int>, count:Int }').replace(
            'fn inspect(h: ->A<Holder>) -> Int { return *h.value; }',
            'fn inspect(mut h:->A<Holder>)->Int{h.count=3;return *h.value+h.count;}')
        self.assertEqual(self.run_source(source).stdout,'10\n30\n')
        self.refused(source.replace('inspect(mut h:', 'inspect(h:'),'immuable|mutable|mutation')
        self.refused(source.replace('inspect(mut h:->A<Holder>)', 'inspect(mut h:->Int)'),
                     'type|champ|Int|incompatible')

    def test_prepared_graph_across_argument_suspension(self):
        source=BASE.replace('fn inspect(h: ->A<Holder>) -> Int { return *h.value; }',
            'fn inspect(h:->A<Holder>,n:Int)->Int{print(*h.value);return n;}\nasync fn pause()->Int{yield;return 8;}').replace(
            'inspect(->h)','inspect(->h,ARG)')
        for argument,expected in (('pause().await','7\n8\n30\n'),('{yield;return 9;}','9\n30\n')):
            with self.subTest(argument=argument):
                run=self.run_source(source.replace('ARG',argument))
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy value=7\n'),1)
                self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)

    def test_result_argument_handles_success_and_error(self):
        source=RETURN.replace('fn main()', '''fn identity(r:->Result<A<Holder>,runtime::Error>)-><-Result<A<Holder>,runtime::Error>{return <-r;}
            async fn wrap(h:->A<Holder>)-><-Result<A<Holder>,runtime::Error>{
                let execution=runtime::spawn(->relay(->h));
                let result=execution.await;return <-identity(->result);}
            fn main()''').replace('runtime::spawn(->relay(->holder))','runtime::spawn(->wrap(->holder))').replace(
            'Ok(received) => { print(*received.value); drop(->received); }',
            'Ok(inner)=>{match inner{Ok(received)=>{print(*received.value);drop(->received);},Err(_)=>{print(20);}}}')
        self.assertEqual(self.run_source(source).stdout,'7\n30\n')
        run=self.run_native(source,fail_submission_at=2)
        self.assertEqual(run.stdout,'20\n30\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)

    def test_nested_result_argument_distinguishes_two_errors(self):
        prefix='''struct Holder{value:A<Int>}
            async fn leaf(h:->A<Holder>)-><-A<Holder>{yield;return <-h;}
            async fn wrap(h:->A<Holder>)-><-Result<A<Holder>,runtime::Error>{
                let e=runtime::spawn(->leaf(->h));return <-e.await;}
            fn identity(r:->Result<Result<A<Holder>,runtime::Error>,runtime::Error>)
                -><-Result<Result<A<Holder>,runtime::Error>,runtime::Error>{return <-r;}
            async fn work(h:->A<Holder>)->Int{
                let e=runtime::spawn(->wrap(->h));let r=e.await;let n=identity(->r);
                return match n{Ok(inner)=>{match inner{
                    Ok(v)=>{let value=*v.value;drop(->v);value},Err(_)=>{20}}},Err(_)=>{30}};}
            '''
        source=prefix+BASE[BASE.index('fn main'):]
        for fail_at,expected in ((None,7),(2,30),(3,20)):
            with self.subTest(fail_at=fail_at):
                run=self.run_native(source,fail_submission_at=fail_at)
                self.assertEqual(run.stdout,f'{expected}\n30\n')
                self.assertEqual(run.stderr.count('destroy value=7\n'),1)
                self.assertEqual(run.stderr.count('destroy holder=Holder\n'),1)

    def test_nested_owned_graph(self):
        source='''struct Child{value:A<Int>}struct Root{child:A<Child>,mark:Int}
            fn identity(r:->A<Root>)-><-A<Root>{return <-r;}
            async fn relay(r:->A<Root>)-><-A<Root>{yield;return <-identity(->r);}
            fn main(){let mut numbers=pool<Int>(1);let mut children=pool<Child>(1);let mut roots=pool<Root>(1);
                let value=numbers.new(7);let child=children.new(value:<-value);let root=roots.new(child:<-child,mark:9);
                let h=runtime::spawn(->relay(->root));match h.join(){Ok(r)=>{print(r.mark);drop(->r);},Err(_)=>{}}
                let next=numbers.new(30);print(*next);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n30\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy value=7','destroy child=Child','destroy root=Root','destroy next=30'])

    def test_collection_fields_are_cleaned(self):
        for typ,fill in (('String','value.push_str("text");'),('Vector<Int>','value.push(7);'),('Vector<u8>','value.push(7);')):
            source=f'''struct Holder{{value:A<{typ}>}}
                fn consume(h:->A<Holder>)->Int{{drop(->h);return 9;}}
                async fn work(h:->A<Holder>)->Int{{yield;return consume(->h);}}
                fn main(){{let mut p=pool<{typ}>(1);let mut roots=pool<Holder>(1);
                    let mut value=p.new();{fill}let root=roots.new(value:<-value);
                    let h=runtime::spawn(->work(->root));match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}
                    let next=p.new();drop(->next);}}'''
            with self.subTest(typ=typ):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'9\n')
                self.assertEqual(run.stderr.count('destroy value='),1)

    def test_returned_graph_lifetime_model(self):
        # The oracle only compares scope depths: every node's storage must
        # enclose the result receiver, independently of compiler metadata.
        prefix='''struct Child{value:A<Int>}struct Root{child:A<Child>,mark:Int}
            fn identity(r:->A<Root>)-><-A<Root>{return <-r;}
            async fn work(r:->A<Root>)-><-A<Root>{yield;return <-identity(->r);}'''
        pools={'numbers':'let mut numbers=pool<Int>(1);',
               'children':'let mut children=pool<Child>(1);',
               'roots':'let mut roots=pool<Root>(1);'}
        for depths in product((0,1),repeat=3):
            outside=''.join(code for code,depth in zip(pools.values(),depths) if depth==0)
            inside=''.join(code for code,depth in zip(pools.values(),depths) if depth==1)
            source=prefix+'fn main(){'+outside+'let result={'+inside+'''
                let value=numbers.new(7);let child=children.new(value:<-value);
                let root=roots.new(child:<-child,mark:9);
                let execution=runtime::spawn(->work(->root));let r=execution.join();<-r};
                match result{Ok(root)=>{print(root.mark);drop(->root);},Err(_)=>{}}}'''
            with self.subTest(depths=depths):
                if all(depth<=0 for depth in depths):
                    self.assertEqual(self.run_source(source).stdout,'9\n')
                else:
                    self.refused(source,'pool|source|survit|surviv')

    def test_identity_and_suspended_prepared_cleanup(self):
        for state in ('before_call','after_call','prepared'):
            source='fn identity(h:->A<Holder>)-><-A<Holder>{return <-h;}'+RETURN.replace(
                'return <-h;','return <-identity(->h);')
            # The helper declaration is prepended after replacing the async body.
            steps='assert(task_poll(task)==TASK_SUSPENDED);'
            if state=='after_call':
                steps+='''assert(task_poll(task)==TASK_COMPLETE);Cell *result=NULL;
                    assert(task_take(task,&result));assert(result==holder);
                    assert(cell_load_ref(result,0)==value);cell_drop(result);'''
            else:
                steps+='assert(task_owned_discardable(task));assert(task_drop_owned(task));'
            if state=='prepared':
                source='''fn identity(h:->A<Holder>,n:Int)-><-A<Holder>{return <-h;}
                    async fn pause()->Int{yield;return 1;}'''+RETURN.replace(
                    'yield;','').replace('return <-h;','return <-identity(->h,pause().await);')
            with self.subTest(state=state):
                run=self.native(source,'''
    Source numbers=source_pool(1);Source arms[]={source_pool_layout(1,sizeof(Cell *))};
    size_t offsets[]={0};unsigned char kinds[]={2};
    arms[0].arm_name="";arms[0].field_count=1;arms[0].field_offsets=offsets;arms[0].field_kinds=kinds;
    Source holders=source_enum_pool(arms,1,"Holder");
    Cell *value=cell_new(&numbers,7,"leaf");Cell *holder=enum_new(&holders,0,"root");
    cell_store_ref(holder,0,value);CrustTask *task=crust_async_relay_create(holder);
'''+steps+'''
    Cell *next=cell_new(&numbers,8,"next");assert(next==value);
    Cell *other=enum_new(&holders,0,"other");assert(other==holder);
    cell_store_ref(other,0,next);cell_drop(other);
    source_close(&holders);source_close(&numbers);
''')
                self.assertEqual(run.stderr.count('destroy leaf=7\n'),1)
                self.assertEqual(run.stderr.count('destroy root=Holder\n'),1)
                self.assertLess(run.stderr.index('destroy leaf=7'),run.stderr.index('destroy root=Holder'))

    def test_field_borrow_blocks_consuming_call(self):
        source=BASE.replace('return inspect(->h);',
            'let view=&*h.value;print(*view);return inspect(->h);')
        self.assertEqual(self.run_source(source).stdout,'7\n7\n30\n')
        self.refused(source.replace('print(*view);return inspect(->h);',
            'let n=inspect(->h);print(*view);return n;'),'emprunt|référenc|réserv')

    def test_mutable_field_borrow_across_suspension(self):
        source=BASE.replace('work(h:','work(mut h:').replace('return inspect(->h);',
            'let mut view=&mut *h.value;yield;view.set(12);return inspect(->h);')
        self.assertEqual(self.run_source(source).stdout,'12\n30\n')
        self.refused(source.replace('view.set(12);return inspect(->h);',
            'let n=inspect(->h);view.set(12);return n;'),'emprunt|référenc|réserv')
        self.refused(source.replace('work(mut h:','work(h:'),'immuable|mutable')
        self.refused(source.replace('view.set(12);return inspect(->h);',
            'print(*h.value);view.set(12);return inspect(->h);'),'emprunt|référenc|réserv')

    def test_replacing_owned_field_then_consuming_graph(self):
        source=BASE.replace('fn inspect(h: ->A<Holder>) -> Int { return *h.value; }',
            'fn inspect(mut h:->A<Holder>,p:&mut Pool<Int>)->Int{h.value=<-p.new(11);return *h.value;}').replace(
            'work(h: ->A<Holder>)','work(h: ->A<Holder>,p:&mut Pool<Int>)').replace(
            'inspect(->h)','inspect(->h,p)').replace('work(->holder)','work(->holder,&mut other)').replace(
            'let execution =','let mut other=pool<Int>(1);let execution =')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'11\n30\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
            ['destroy value=7','destroy champ=11','destroy holder=Holder','destroy reused=30'])

    def test_legacy_reset_tracks_root_and_field_after_helper(self):
        # Public reset is removed. This uses its historical contract solely
        # as an independent query of the retained source dependencies.
        source='fn identity(h:->A<Holder>)-><-A<Holder>{return <-h;}'+RETURN[:RETURN.index('fn main')].replace(
            'return <-h;', 'return <-identity(->h);')+'''
            fn finish(e:->Execution<relay>,p:&mut Pool<Int>)->Int{
                let r=e.join();p.reset();return match r{
                    Ok(h)=>{let n=*h.value;drop(->h);n},Err(_)=>{0}};}'''
        contract=verify_program(source,allow_legacy_reset=True).function_contracts['finish']
        pairs={frozenset((side.kind,side.index,side.name) for side in (r.left,r.right))
               for r in contract.constraints.requirements if r.relation=='distinct'}
        for target in (('task_result_parameter',0,''),('task_result_field_parameter',0,'.value')):
            self.assertIn(frozenset({('source_parameter',1,''),target}),pairs)


if __name__=='__main__':unittest.main()
