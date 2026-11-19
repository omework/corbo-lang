"""Synchronous factories inject caller storage into deferred task results."""
from pathlib import Path
import re
import unittest
from crust import compile_source,verify_program
import test_async_result_storage as output

ROOT=Path(__file__).resolve().parents[1]
PREFIX=output.PREFIX
LEAF='async fn leaf(n:Int)-><-Point{let p=make(n);yield;return <-p;}'
FACTORY='fn prepare(n:Int)-><-leaf{let t=leaf(n);return <-t;}'
MAIN='fn main(){let h=runtime::spawn(->EXPR);match h.join(){Ok(q)=>{print(q.x);drop(->q);},Err(_)=>{}}}'

class AsyncResultFactoryTests(unittest.TestCase):
    run_source=output.AsyncResultStorageTests.run_source
    run_c_oracle=output.AsyncResultStorageTests.run_c_oracle
    refused=output.AsyncResultStorageTests.refused
    run_native=output.AsyncResultStorageTests.run_native
    storage_probe=output.AsyncResultStorageTests.storage_probe

    def test_recorded_factory(self):
        self.assertEqual(self.run_source((ROOT/'validation/open-async-result-storage-factory.crb').read_text()).stdout,'7\n')

    def test_async_caller_and_parent_receiver(self):
        self.assertEqual(self.run_source((ROOT/'validation/open-async-result-factory-async-caller.crb').read_text()).stdout,'7\n')
        for body in ('let q=prepare(7).await;return q.x;',
                     'let q={let t=prepare(7);let q=t.await;<-q};return q.x;'):
            self.assertEqual(self.run_source(output.AsyncResultStorageTests.program(body,LEAF+FACTORY)).stdout,'7\n')
        source=(ROOT/'validation/open-async-result-factory-relay.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_factory_completion_updates_caller_fields(self):
        valid=(ROOT/'validation/open-async-factory-field-valid.crb').read_text()
        invalid=(ROOT/'validation/open-async-factory-field-invalid.crb').read_text()
        self.assertEqual(self.run_source(valid).stdout,'9\n9\n')
        self.refused(invalid,'emprunt|réserv|référenc|capture')
        effect=verify_program(valid).async_definitions['outer'][0].field_effect_summary
        targets=dict(dict(effect.completion_result.structure_fields)[0])['.data']
        self.assertEqual({(target.kind,target.parameter) for target in targets},{('parameter',1)})

    def test_async_caller_copy_lifetimes(self):
        helpers=output.DUPLICATE+'''async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}
            fn prepare(p:&Point)-><-leaf{return <-leaf(p);}'''
        for allocation in ('let p=make(7);',):
            body=allocation+'let t=prepare(&p);let q=t.await;drop(->p);yield;return q.x;'
            source=output.AsyncResultStorageTests.program(body,helpers)
            self.assertEqual(self.run_source(source).stdout,'7\n')
            self.refused(source.replace('let t=prepare(&p);let q=t.await;',
                         'let t=prepare(&p);drop(->p);let q=t.await;'), 'emprunt|réserv|référenc|capture')
        source=output.AsyncResultStorageTests.program('let q={let p=make(7);let t=prepare(&p);let q=t.await;<-q};return q.x;',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        source=PREFIX+helpers.replace('-><-Point','-><-A<Point>')+'''async fn work(p:->Point)->Int{let t=prepare(&p);let q=t.await;drop(->p);yield;return q.x;}
            fn main(){let mut points=pool<Point>(2);let p=points.new(x:7);let h=runtime::spawn(->work(->p));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_task_transfer_across_sync_parent_blocks(self):
        for expr in ('{let t=prepare(7);<-t}', '{let t={let t=prepare(7);<-t};<-t}'):
            source=PREFIX+LEAF+FACTORY+'fn main(){let t='+expr+';let h=runtime::spawn(->t);match h.join(){Ok(q)=>{print(q.x);drop(->q);},Err(_)=>{}}}'
            self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_factory_task_in_select_and_inactive_drop(self):
        helpers=LEAF+FACTORY
        body='let a=prepare(7);let b=prepare(9);let mut s=runtime::select(->a,->b);let q=s.await;drop(->s);return q.x;'
        self.assertEqual(self.run_source(output.AsyncResultStorageTests.program(body,helpers)).stdout,'7\n')
        run=self.run_source(output.AsyncResultStorageTests.program('let t=prepare(7);drop(->t);return 9;',helpers))
        self.assertEqual(run.stdout,'9\n');self.assertNotIn('destroy p=Point',run.stderr)

    def test_borrowed_factory_result_reserves_input(self):
        helpers='async fn leaf(n:&mut Int)->&mut Int{yield;return n;}fn prepare(n:&mut Int)-><-leaf{return <-leaf(n);}'
        body='let mut ints=pool<Int>(1);let mut n=ints.new(7);let t=prepare(&mut n);let mut view=t.await;view.set(9);return *n;'
        source=output.AsyncResultStorageTests.program(body,helpers)
        self.assertEqual(self.run_source(source).stdout,'9\n')
        self.refused(source.replace('view.set(9);','drop(->n);view.set(9);'),'emprunt|réserv|référenc|capture')

    def test_factory_text_result_retains_view(self):
        helpers='async fn leaf(v:&str)->&str{yield;return v;}fn prepare(v:&str)-><-leaf{return <-leaf(v);}'
        body='let mut p=pool<String>(1);let mut data=p.new();data.push_str("été");let v=&data[..];let t=prepare(v);let text=t.await;yield;print(text);drop(->data);return 7;'
        source=output.AsyncResultStorageTests.program(body,helpers)
        self.assertEqual(self.run_source(source).stdout,'été\n7\n')
        self.refused(source.replace('print(text);drop(->data);','drop(->data);print(text);'),
                     'emprunt|réserv|référenc|capture')

    def test_nested_factories_and_forwarded_task_contracts(self):
        helpers=FACTORY+'fn again(n:Int)-><-leaf{return <-prepare(n);}fn forward(t:->leaf)-><-leaf{return <-t;}'
        for expr in ('prepare(7)','again(7)','forward(->again(7))'):
            source=PREFIX+LEAF+helpers+MAIN.replace('EXPR',expr)
            self.assertEqual(self.run_source(source).stdout,'7\n')
        check=verify_program(source)
        for name in ('prepare','again'):
            self.assertEqual({s.kind for s in check.function_results[name].task_result_sources},{'task_output'})
        self.assertEqual({s.kind for s in check.function_results['forward'].task_result_sources},{'task_result_parameter'})

    def test_conditional_and_loop_factory(self):
        for body in ('if n==7{let t=leaf(n);return <-t;}return <-leaf(9);',
                     'let t=if n==7{let t=leaf(n);<-t}else{let t=leaf(9);<-t};return <-t;',
                     'let t=loop{let t=leaf(n);break <-t;};return <-t;'):
            for n in (7,9):
                source=PREFIX+LEAF+'fn prepare(n:Int)-><-leaf{'+body+'}'+MAIN.replace('EXPR',f'prepare({n})')
                self.assertEqual(self.run_source(source).stdout,str(n)+'\n')

    def test_copy_factory_local_and_pool(self):
        helpers=output.DUPLICATE+'''async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}
            fn prepare(p:&Point)-><-leaf{return <-leaf(p);}fn again(p:&Point)-><-leaf{return <-prepare(p);}'''
        for allocation in ('let p=make(7);','let mut points=pool<Point>(2);let p=points.new(x:7);'):
            source=PREFIX+(helpers if 'make(' in allocation else helpers.replace('-><-Point','-><-A<Point>'))+'fn main(){'+allocation+'''let h=runtime::spawn(->again(&p));
                let q=match h.join(){Ok(q)=>{<-q},Err(_)=>{return;}};drop(->p);print(q.x);drop(->q);}'''
            self.assertEqual(self.run_source(source).stdout,'7\n')
            check=verify_program(source)
            for name in ('prepare','again'):
                self.assertEqual({s.kind for s in check.function_results[name].task_result_sources},{'task_output_parameter'})
            self.refused(source.replace('let h=runtime::spawn(->again(&p));',
                'let t=again(&p);drop(->p);let h=runtime::spawn(->t);'), 'emprunt|réserv|référenc|capture')

    def test_short_pool_and_short_capture_still_refused(self):
        helpers=output.DUPLICATE+'''async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}
            fn prepare(p:&Point)-><-leaf{return <-leaf(p);}'''
        source=PREFIX+helpers.replace('-><-Point','-><-A<Point>')+'''fn main(){let q={let mut points=pool<Point>(2);let p=points.new(x:7);
            let h=runtime::spawn(->prepare(&p));let q=match h.join(){Ok(q)=>{<-q},Err(_)=>{return;}};<-q};print(q.x);drop(->q);}'''
        self.refused(source,'pool|source|survi')
        self.refused(PREFIX+helpers+'fn main(){let t={let p=make(7);let t=prepare(&p);<-t};'+
                     'let h=runtime::spawn(->t);match h.join(){Ok(q)=>{print(q.x);drop(->q);},Err(_)=>{}}}',
                     'pool|source|survi|emprunt|capture')

    def test_conditional_copy_sources_keep_storage_type(self):
        helpers=output.DUPLICATE+'''async fn leaf(p:&Point)-><-Point{let q=duplicate(p);yield;return <-q;}
            fn prepare(a:&Point,b:&Point,n:Int)-><-leaf{if n==0{return <-leaf(a);}return <-leaf(b);}'''
        for allocation in ('let a=make(7);let b=make(9);',
                           'let mut points=pool<Point>(3);let a=points.new(x:7);let b=points.new(x:9);'):
            for flag,expected in ((0,'7\n'),(1,'9\n')):
                source=PREFIX+(helpers if 'make(' in allocation else helpers.replace('-><-Point','-><-A<Point>'))+'fn main(){'+allocation+MAIN[MAIN.index('let h='):].replace('EXPR',f'prepare(&a,&b,{flag})')
                self.assertEqual(self.run_source(source).stdout,expected)
        mixed=PREFIX+helpers+'fn main(){let a=make(7);let mut points=pool<Point>(2);let b=points.new(x:9);'+MAIN[MAIN.index('let h='):].replace('EXPR','prepare(&a,&b,0)')
        self.refused(mixed,'stockage|local|allocation')

    def test_inactive_cleanup_and_launch_failure(self):
        source=PREFIX+LEAF+FACTORY+'fn main(){let t=prepare(7);drop(->t);}'
        self.assertNotIn('destroy p=Point',self.run_source(source).stderr)
        source=PREFIX+LEAF+FACTORY+MAIN.replace('EXPR','prepare(7)').replace('Err(_)=>{}','Err(_)=>{print(99);}')
        result=self.run_native(source,fail_submission_at=1)
        self.assertEqual(result.stdout,'99\n');self.assertNotIn('destroy p=Point',result.stderr)

    def test_two_results_share_caller_storage(self):
        source=PREFIX+LEAF+FACTORY+'''fn main(){let a=runtime::spawn(->prepare(7));let b=runtime::spawn(->prepare(9));
            let x=a.join();let y=b.join();match x{Ok(q)=>{print(q.x);drop(->q);},Err(_)=>{}}
            match y{Ok(q)=>{print(q.x);drop(->q);},Err(_)=>{}}}'''
        self.assertEqual(self.run_native(source).stdout,'7\n9\n')

    def test_destination_and_cleanup_after_factory_return(self):
        source=PREFIX+LEAF+FACTORY+MAIN.replace('EXPR','prepare(7)')
        code=compile_source(source)
        functions=re.findall(r'static CrustTask \* (crust_fn_\d+)\(int \w+, Source \* \w+\)',code)
        self.assertEqual(len(functions),1)
        for finish in (False,True):
            ending=('assert(task_poll(task)==TASK_COMPLETE);Cell *result=NULL;assert(task_take(task,&result));'
                    'assert(task_pool_is_empty(&crust_task_context.pool_leaf));'
                    'assert(result==created && result->alive && result->source==&destination);'
                    'assert(cell_load_int(result,0)==7);cell_drop(result);'
                    if finish else 'assert(task_owned_discardable(task));assert(task_drop_owned(task));')
            run=self.storage_probe(source, '''
                Source destination=source_stack(4096);
                CrustTask *task=FACTORY(7,&destination);
                assert(destination.live==0 && observed_count==0 && observed_close_count==0);
                assert(task_poll(task)==TASK_SUSPENDED);assert(observed_count==1);
                Cell *created=observed_cells[0];assert(created->source==&destination && created->alive);
            '''.replace('FACTORY',functions[0])+ending+'''
                assert(destination.live==0 && destination.used==0 && observed_close_count==0);
                source_close(&destination);assert(observed_close_count==1);
                assert(task_pool_is_empty(&crust_task_context.pool_leaf));
            ''')
            self.assertEqual(run.stderr.count('destroy p=Point\n'),1)

if __name__=='__main__':unittest.main()
