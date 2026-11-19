"""Owned Result expressions keep transfers, sources and pending cleanup at await."""
from pathlib import Path
import unittest

from crust import Error, verify_program
import test_native_blocks as native_tests
import test_select_source as source_tests
import test_suspended_cleanup as cleanup_tests

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = (
    ('Int', 'let value=p.new(7);', 'print(*value);'),
    ('String', 'let mut value=p.new();value.push_str("7");', 'print(&value[..]);'),
    ('Vector<Int>', 'let mut value=p.new();value.push(7);', 'print(value[0]);'),
    ('Vector<u8>', 'let mut value=p.new();value.push(7);', 'print(value[0] as Int);'),
)


class AsyncAwaitedOwnedResultsTests(unittest.TestCase):
    run_c_oracle = source_tests.SelectSourceTests.run_c_oracle
    run_native = native_tests.NativeBlockTests.run_native
    run_source = source_tests.SelectSourceTests.run_source
    refused = source_tests.SelectSourceTests.refused
    native = cleanup_tests.SuspendedCleanupTests.native

    @staticmethod
    def prefix(typ, fill):
        result = f'Result<A<{typ}>,runtime::Error>'
        return f'''async fn leaf(p:&mut Pool<{typ}>)-><-{typ}{{yield;{fill}return <-value;}}
            async fn wrapped(p:&mut Pool<{typ}>)-><-{result}{{
                let h=runtime::spawn(->leaf(p));return <-h.await;}}
            fn relay(r:->{result},n:Int)-><-{result}{{print(n);return <-r;}}
            async fn pause()->Int{{yield;return 4;}}'''

    @staticmethod
    def observe(read, expression='moved'):
        return f'match {expression}{{Ok(value)=>{{{read}drop(->value);}},Err(_)=>{{print(20);}}}}'

    @staticmethod
    def main(typ, use='print(n);'):
        return f'''fn main(){{let mut p=pool<{typ}>(1);let h=runtime::spawn(->work(&mut p));
            match h.join(){{Ok(n)=>{{{use}}},Err(_)=>{{print(10);}}}}
            let reused=p.new();drop(->reused);}}'''

    def test_recorded_argument_and_handle_consumption(self):
        source=(ROOT/'validation/open-awaited-owned-result-argument.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n9\n30\n')
        self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'20\n9\n30\n')
        self.refused(source.replace('relay(->h.await)','relay(h.await)'), 'transfert|explicite')
        self.refused(source.replace('return 9;', 'drop(->h.await);return 9;'), 'consommé|attendu|utilisable')

    def test_argument_expression_families_and_forms(self):
        for typ,fill,read in FAMILIES:
            for label,setup,expression in (
                ('handle','let h=runtime::spawn(->leaf(p));','h.await'),
                ('spawn','','runtime::spawn(->leaf(p)).await'),
                ('task','','wrapped(p).await'),
                ('named_task','let t=wrapped(p);','t.await'),
                ('block_task','','{let t=wrapped(p);<-t}.await'),
                ('block_handle','','{let h=runtime::spawn(->leaf(p));<-h}.await'),
            ):
                source=self.prefix(typ,fill)+f'''async fn work(p:&mut Pool<{typ}>)->Int{{
                    {setup}let moved=relay(->{expression},pause().await);
                    {self.observe(read)}return 9;}}'''+self.main(typ)
                with self.subTest(typ=typ,form=label):
                    run=self.run_source(source)
                    self.assertEqual(run.stdout,'4\n7\n9\n')
                    self.assertEqual(run.stderr.count('destroy value='),1)
                    self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'4\n20\n9\n')

    def test_return_task_and_computed_handle_expressions(self):
        typ,fill,read=FAMILIES[0]
        for expression in ('wrapped(p).await','{let t=wrapped(p);<-t}.await',
                           'runtime::spawn(->leaf(p)).await',
                           '{let h=runtime::spawn(->leaf(p));<-h}.await'):
            source=self.prefix(typ,fill)+f'''async fn work(p:&mut Pool<Int>)-><-Result<A<Int>,runtime::Error>{{
                return <-{expression};}}'''+self.main(typ,self.observe(read,'n'))
            with self.subTest(expression=expression):
                self.assertEqual(self.run_source(source).stdout,'7\n')
                self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'20\n')
                self.refused(source.replace('return <-'+expression,'return '+expression),'explicite|transfert')

    def test_match_task_result_directly(self):
        for typ,fill,read in FAMILIES:
            for expression in ('wrapped(p).await','{let t=wrapped(p);<-t}.await'):
                source=self.prefix(typ,fill)+f'''async fn work(p:&mut Pool<{typ}>)->Int{{
                    {self.observe(read,expression)}return 9;}}'''+self.main(typ)
                with self.subTest(typ=typ,expression=expression):
                    self.assertEqual(self.run_source(source).stdout,'7\n9\n')
                    self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'20\n9\n')
                    self.refused(source.replace('Ok(value)=>{'+read+'drop(->value);}', 'Ok(_)=>{}'),
                                 'motif|allocation|propriétaire')

    def test_async_capture_and_interrupted_later_argument(self):
        for typ,fill,read in FAMILIES:
            result=f'Result<A<{typ}>,runtime::Error>'
            prefix=self.prefix(typ,fill)+f'''async fn receive(r:->{result},n:Int)->Int{{
                yield;print(n);{self.observe(read,'r')}return 8;}}'''
            for call,expected in (('relay(->wrapped(p).await,ARG)','4\n7\n9\n'),
                                  ('receive(->wrapped(p).await,ARG).await','4\n7\n8\n9\n')):
                consume=self.observe(read) if call.startswith('relay') else 'print(moved);'
                template=prefix+f'''async fn work(p:&mut Pool<{typ}>)->Int{{
                    let moved={call};{consume}return 9;}}'''+self.main(typ)
                with self.subTest(typ=typ,call=call):
                    run=self.run_source(template.replace('ARG','pause().await'))
                    self.assertEqual(run.stdout,expected)
                    self.assertEqual(run.stderr.count('destroy value='),1)
                    interrupted=self.run_source(template.replace('ARG','{yield;return 6;}'))
                    self.assertEqual(interrupted.stdout,'6\n')
                    self.assertEqual(interrupted.stderr.count('destroy value='),1)

    def test_nested_result_errors_remain_distinct(self):
        for typ,fill,read in (FAMILIES[0],FAMILIES[1]):
            inner=f'Result<A<{typ}>,runtime::Error>'
            outer=f'Result<{inner},runtime::Error>'
            source=self.prefix(typ,fill)+f'''
                async fn nested(p:&mut Pool<{typ}>)-><-{outer}{{
                    return <-runtime::spawn(->wrapped(p)).await;}}
                fn relay_nested(r:->{outer},n:Int)-><-{outer}{{print(n);return <-r;}}
                async fn work(p:&mut Pool<{typ}>)->Int{{
                    let r=relay_nested(->nested(p).await,pause().await);
                    match r{{Ok(inner)=>{{{self.observe(read,'inner')}}},Err(_)=>{{print(30);}}}}
                    return 9;}}'''+self.main(typ)
            # Each launch boundary contributes its own error level. No failure
            # creates the leaf; only the successful path destroys that value.
            for failure,expected in ((None,'4\n7\n9\n'),(1,'10\n'),
                                     (2,'4\n30\n9\n'),(3,'4\n20\n9\n')):
                with self.subTest(typ=typ,failure=failure):
                    run=self.run_native(source,fail_submission_at=failure)
                    self.assertEqual(run.stdout,expected)
                    self.assertEqual(run.stderr.count('destroy value='),int(failure is None))

    def test_suspended_prepared_result_cleanup(self):
        # Independent finite lifetime model: during the first pause the child
        # owns the input, during the second the pending call does; an async
        # receiver adds a third pause while owning it. Every suspended exit
        # destroys the sole present allocation once, or none for Err.
        for asynchronous in (False,True):
            prefix=self.prefix(*FAMILIES[0][:2])+'''
                async fn deliver(r:->Result<A<Int>,runtime::Error>)-><-Result<A<Int>,runtime::Error>{
                    yield;return <-r;}
            '''
            if asynchronous:
                prefix+='''async fn consume(r:->Result<A<Int>,runtime::Error>,n:Int)->Int{
                    yield;drop(->r);return n;}'''
                body='let n=consume(->deliver(->r).await,pause().await).await;return n;'
            else:
                body='let moved=relay(->deliver(->r).await,pause().await);drop(->moved);return 9;'
            source=prefix+'''async fn work(r:->Result<A<Int>,runtime::Error>)->Int{'''+body+'''}
                fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->leaf(&mut p));
                    let r=h.join();let top=runtime::spawn(->work(->r));
                    match top.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
            holders=['child','prepared']+(['receiver'] if asynchronous else [])
            for present in (False,True):
                for polls,holder in enumerate(holders,1):
                    with self.subTest(asynchronous=asynchronous,present=present,holder=holder):
                        run=self.native(source,f'''
    Source pool=source_pool(1);
    Cell *cell={ 'cell_new(&pool,7,"incoming")' if present else 'NULL'};
    CrustJoinResult r={{0}};r.status={0 if present else 5};r.allocation=cell;
    CrustTask *task=crust_async_work_create(r);
    for(int i=0;i<{polls};++i) assert(task_poll(task)==TASK_SUSPENDED);
    assert(task_owned_discardable(task));assert(task_drop_owned(task));
    assert(!task_drop_owned(task));
    Cell *reused=cell_new(&pool,8,"reused");
    if(cell) assert(reused==cell);
    cell_drop(reused);source_close(&pool);
''')
                        self.assertEqual(run.stderr.count('destroy incoming=7\n'),int(present))
                        self.assertEqual(run.stderr.count('destroy reused=8\n'),1)

    def test_sources_and_exact_payload_types(self):
        # The allocation pool, unlike the frame pool, must outlive the caller's
        # receiver. Removing the intermediate Result does not erase this source.
        prefix=self.prefix(*FAMILIES[0][:2])
        invalid=prefix+'''async fn work()-><-Result<A<Int>,runtime::Error>{
            let mut p=pool<Int>(1);return <-wrapped(&mut p).await;}
            fn main(){let h=runtime::spawn(->work());match h.join(){
                Ok(r)=>{drop(->r);},Err(_)=>{}}}'''
        self.refused(invalid,'source|pool|durée|surviv|local')
        source=(ROOT/'validation/open-awaited-owned-result-argument.crb').read_text()
        self.refused(source.replace('r:->Result<A<Int>', 'r:->Result<A<String>').replace(
            '-><-Result<A<Int>', '-><-Result<A<String>'), 'type incompatible|attendu')
        self.refused(source.replace('-><-Int{yield;let value=p.new(7);return <-value;}',
            '->Int{yield;let value=p.new(7);print(*value);return 7;}'), 'type incompatible|attendu')

    def test_select_loser_cleans_prepared_awaited_result(self):
        prefix=self.prefix(*FAMILIES[0][:2])+'''
            async fn deliver(r:->Result<A<Int>,runtime::Error>)-><-Result<A<Int>,runtime::Error>{
                yield;return <-r;}
            async fn left(r:->Result<A<Int>,runtime::Error>)->Int{
                let moved=relay(->deliver(->r).await,pause().await);drop(->moved);return 8;}
            async fn right()->Int{yield;return 99;}
        '''
        source=prefix+'''async fn work(p:&mut Pool<Int>)->Int{
                let h=runtime::spawn(->leaf(p));let r=h.await;
                let mut selection=runtime::select(->left(->r),->right());
                let answer=selection.await;print(answer);drop(->selection);
                let reused=p.new(30);return *reused;}'''+self.main('Int')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'99\n30\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)
        self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'99\n30\n')


if __name__=='__main__':
    unittest.main()
