"""Direct returns of awaited allocations preserve identity, sources and cleanup."""
from pathlib import Path
import unittest

import test_async_awaited_owned_results as result_tests
import test_native_blocks as native_tests
import test_select_source as source_tests
import test_suspended_cleanup as cleanup_tests

ROOT=Path(__file__).resolve().parents[1]


class AsyncDirectOwnedReturnsTests(unittest.TestCase):
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    run_native=native_tests.NativeBlockTests.run_native
    run_source=source_tests.SelectSourceTests.run_source
    refused=source_tests.SelectSourceTests.refused
    native=cleanup_tests.SuspendedCleanupTests.native

    def test_recorded_direct_return(self):
        source=(ROOT/'validation/open-direct-awaited-allocation-return.crb').read_text()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n30\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)
        self.refused(source.replace('return <-leaf(p).await','return leaf(p).await'),'transfert|explicite')

    def test_owned_families_and_task_expressions(self):
        for typ,fill,read in result_tests.FAMILIES:
            for setup,expression in (
                ('','leaf(p).await'),
                ('let task=leaf(p);','task.await'),
                ('','{let task=leaf(p);<-task}.await'),
                ('','if true{let value=leaf(p).await;<-value}else{let value=leaf(p).await;<-value}'),
            ):
                source=f'''async fn leaf(p:&mut Pool<{typ}>)-><-{typ}{{yield;{fill}return <-value;}}
                    async fn work(p:&mut Pool<{typ}>)-><-{typ}{{{setup}return <-{expression};}}
                    fn main(){{let mut p=pool<{typ}>(1);let h=runtime::spawn(->work(&mut p));
                        match h.join(){{Ok(value)=>{{{read}drop(->value);}},Err(_)=>{{print(20);}}}}
                        let reused=p.new();drop(->reused);}}'''
                with self.subTest(typ=typ,expression=expression):
                    run=self.run_source(source)
                    self.assertEqual(run.stdout,'7\n')
                    self.assertEqual(run.stderr.count('destroy value='),1)
                    self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'20\n')

    def test_select_return_keeps_payload_and_cleans_selection(self):
        source='''async fn leaf(p:&mut Pool<Int>,n:Int)-><-Int{yield;let value=p.new(n);return <-value;}
            async fn work(p:&mut Pool<Int>,q:&mut Pool<Int>)-><-Int{
                let mut selection=runtime::select(->leaf(p,7),->leaf(q,9));
                return <-selection.await;}
            fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let h=runtime::spawn(->work(&mut p,&mut q));
                match h.join(){Ok(value)=>{print(*value);drop(->value);},Err(_)=>{}}
                let a=p.new(20);let b=q.new(30);print(*a+*b);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n50\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)
        self.assertNotIn('destroy value=9\n',run.stderr)

    def test_computed_await_argument_then_early_exit(self):
        for asynchronous in (False,True):
            source=('async ' if asynchronous else '')+'''fn consume(n:->Int,last:Int)->Int{
                    print(*n);return last;}
                async fn leaf(p:&mut Pool<Int>)-><-Int{yield;let value=p.new(7);return <-value;}
                async fn work(p:&mut Pool<Int>)->Int{
                    let result=consume(->{let task=leaf(p);<-task}.await,{yield;return 9;})'''+(
                        '.await' if asynchronous else '')+''';return result;}
                fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));
                    match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                    let reused=p.new(30);print(*reused);}'''
            with self.subTest(asynchronous=asynchronous):
                run=self.run_source(source)
                self.assertEqual(run.stdout,'9\n30\n')
                self.assertEqual(run.stderr.count('destroy value=7\n'),1)

    def test_return_keeps_sources_and_exact_type(self):
        source=(ROOT/'validation/open-direct-awaited-allocation-return.crb').read_text()
        self.refused(source.replace('async fn relay(p:&mut Pool<Int>)-><-Int{',
            'async fn relay()-><-Int{let mut p=pool<Int>(1);').replace(
            'return <-leaf(p).await','return <-leaf(&mut p).await').replace('relay(&mut p)','relay()'),
            'source|pool|surviv|durée|local')
        self.refused(source.replace('return <-leaf(p).await','return <-runtime::spawn(->leaf(p)).await'),
            'Result|incompatible')
        self.refused(source.replace('async fn relay(p:&mut Pool<Int>)-><-Int',
            'async fn relay(p:&mut Pool<Int>)-><-String'), 'incompatible|attendu')

    def test_direct_return_identity_and_suspended_destruction(self):
        source='''async fn child(n:->Int)-><-Int{yield;return <-n;}
            async fn work(n:->Int)-><-Int{return <-child(->n).await;}
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);let h=runtime::spawn(->work(->n));
                match h.join(){Ok(value)=>{print(*value);drop(->value);},Err(_)=>{}}}'''
        for completed in (False,True):
            consume=('Cell *result=NULL;assert(task_poll(task)==TASK_COMPLETE);'
                     'assert(task_take(task,&result));assert(result==cell);'
                     'assert(result->value==7);cell_drop(result);' if completed else
                     'assert(task_owned_discardable(task));assert(task_drop_owned(task));')
            with self.subTest(completed=completed):
                run=self.native(source,'''
    Source pool=source_pool(1);Cell *cell=cell_new(&pool,7,"incoming");
    CrustTask *task=crust_async_work_create(cell);
    assert(task_poll(task)==TASK_SUSPENDED);
'''+consume+'''
    Cell *reused=cell_new(&pool,8,"reused");assert(reused==cell);
    cell_drop(reused);source_close(&pool);
''')
                self.assertEqual(run.stderr.count('destroy incoming=7\n'),1)
                self.assertEqual(run.stderr.count('destroy reused=8\n'),1)


if __name__=='__main__':unittest.main()
