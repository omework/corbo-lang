"""VE3 × AS8: ordered removal, suspension, aliasing and slot lifetime."""
from pathlib import Path
import random
import unittest
from crust import Error, compile_source, verify_program
import test_async_runtime
import test_async_vector_results as results
from test_async_vector_operations import launch


class AsyncVectorRemoveTests(unittest.TestCase):
    run_native=results.AsyncVectorResultTests.run_native
    reject_blocking=results.AsyncVectorResultTests.reject_blocking
    rejecting_callback=results.AsyncVectorResultTests.rejecting_callback
    run_c_oracle=test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_recorded_remove(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-vector-remove.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'17\n1\n29\n')

    def test_remove_preserves_order_on_both_storage_fronts(self):
        for element in ('Int','u8'):
            for reverse in (False,True):
                data=[11,255,30,42]
                suffix=' as Int' if element=='u8' else ''
                body=''
                expected=[]
                for step,index in enumerate((1,0,1,0)):
                    expected.append(data.pop(index));expected.append(len(data));expected.extend(data)
                    body+=f'let n{step}=v.remove({index});yield;print(n{step}{suffix});print(v.len());'
                    body+=''.join(f'print(v[{i}]{suffix});' for i in range(len(data)))
                source=f'''async fn work(v:&mut Vector<{element}>){{{body}}}
                    fn main(){{let mut p=pool<Vector<{element}>>(2);BLOCKER
                        let mut v=p.new();v.push(11);v.push(255);v.push(30);v.push(42);
                        let h=runtime::spawn(->work(&mut v));match h.join(){{Ok(())=>{{}},Err(_)=>{{print(999);}}}}}}'''
                source=source.replace('BLOCKER','let mut first=p.new();first.push(0);' if reverse else '')
                code=compile_source(source)
                marker='static void vector_remove(Cell *cell, int index, void *value) {'
                self.assertEqual(code.count(marker),1)
                code=code.replace(marker,marker+f'\nif(vector_descends(vector_items(cell)) != {int(reverse)}) abort();')
                with self.subTest(element=element,reverse=reverse):
                    self.assertEqual(self.run_c_oracle(code).stdout,''.join(f'{n}\n' for n in expected))

    def test_suspended_indices_and_binary_expression_evaluate_once_in_order(self):
        helpers='''async fn next(n:&mut Int)->Int{print(*n);yield;n.set(*n+1);return *n-1;}'''
        body='''let mut index=0;
            let first=v.remove(next(&mut index).await);
            let pair=v.remove(0)+v.remove(0);yield;
            print(index);print(first);print(pair);print(v[0]);'''
        source=launch(body,helpers=helpers,before='v.push(10);v.push(20);v.push(30);v.push(40);')
        self.assertEqual(self.run_native(source).stdout,'0\n1\n10\n50\n40\n')

    def test_receiver_reserved_during_suspended_index(self):
        helpers='async fn index(v:&Vector<Int>)->Int{yield;return v.len()-1;}'
        for expr in ('v.remove(index(&*v).await)','v.remove(v.len()-1)','v.remove(v.remove(0))'):
            with self.subTest(expr=expr),self.assertRaisesRegex(Error,'emprunt actif|incompatible'):
                verify_program(launch('print('+expr+');',helpers=helpers,before='v.push(0);'))
        source=launch('let i=other.len()-1;print(v.remove(i));',parameter='v:&mut Vector<Int>,other:&Vector<Int>',before='v.push(7);')
        source=source.replace('>>(1)','>>(2)').replace('let h=','let mut other=p.new();other.push(1);let h=').replace('work(&mut v)','work(&mut v,&other)')
        self.assertEqual(self.run_native(source).stdout,'7\n')

    def test_view_last_use_and_branch_continuations(self):
        before='v.push(10);v.push(20);'
        prefix='let view=&v[..];print(view[0]);'
        self.assertEqual(self.run_native(launch(prefix+'print(v.remove(0));',before=before,after='print(v[0]);')).stdout,'10\n10\n20\n')
        for tail in ('print(view[0]);','yield;print(view[0]);','if true{print(view[0]);}'):
            with self.subTest(tail=tail),self.assertRaisesRegex(Error,'emprunt actif|incompatible'):
                verify_program(launch(prefix+'print(v.remove(0));'+tail,before=before))

    def test_mutability_types_arity_and_consumption(self):
        for body,element in (
            ('let n:Int=v.remove(0);print(n);','u8'),
            ('let n:u8=v.remove(0);print(n as Int);','Int'),
            ('print(v.remove(true));','Int'),
            ('print(v.remove());','Int'),
            ('print(v.remove(0,1));','Int'),
        ):
            with self.subTest(body=body),self.assertRaises(Error):verify_program(launch(body,element=element))
        source=launch('print(v.remove(0));',before='v.push(10);')
        with self.assertRaisesRegex(Error,'mutable'):
            verify_program(source.replace('v:&mut Vector<Int>','v:&Vector<Int>').replace('work(&mut v)','work(&v)'))
        source='''async fn work(mut v:->Vector<Int>)->Int{drop(->v);return v.remove(0);}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push(1);let h=runtime::spawn(->work(->v));drop(->h.join());}'''
        with self.assertRaisesRegex(Error,'plus utilisable'):verify_program(source)

    def test_discarded_copy_removes_once(self):
        source=launch('v.remove(0);yield;print(v.len());print(v[0]);',before='v.push(10);v.push(20);')
        self.assertEqual(self.run_native(source).stdout,'1\n20\n')

    def test_loop_continue_and_break_keep_mutation_and_cleanup_order(self):
        body='''let mut sum=0;
            let total=loop{
                if v.len()==0{break sum;}
                let view=&v[..];let old=view[0];
                let n=v.remove(0);yield;
                if old==20{continue;}
                sum=sum+n;
            };print(total);print(v.len());'''
        self.assertEqual(self.run_native(launch(body,before='v.push(10);v.push(20);v.push(30);')).stdout,'40\n0\n')
        with self.assertRaisesRegex(Error,'emprunt actif|incompatible'):
            verify_program(launch(body.replace('yield;','yield;print(view[0]);'),before='v.push(10);'))

    def test_byte_result_crosses_nested_await_and_join(self):
        source='''async fn child(v:&mut Vector<u8>)->u8{yield;return v.remove(0);}
            async fn parent(v:&mut Vector<u8>)->u8{let n=child(&mut *v).await;yield;return n;}
            fn main(){let mut p=pool<Vector<u8>>(1);let mut v=p.new();v.push(255);
                let h=runtime::spawn(->parent(&mut v));let r=h.join();drop(->v);
                let fresh=p.new();drop(->fresh);
                match r{Ok(n)=>{print(n as Int);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout,'255\n')
        with self.assertRaisesRegex(Error,'Int|u8'):
            verify_program(source.replace('child(v:&mut Vector<u8>)->u8','child(v:&mut Vector<u8>)->Int'))

    def test_dynamic_bounds_fail_before_access(self):
        helper='async fn index(n:Int)->Int{yield;return n;}'
        for index in (-1,1,2147483647):
            for element in ('Int','u8'):
                source=launch(f'v.remove(index({index}).await);print(999);',element=element,helpers=helper,before='v.push(17);')
                with self.subTest(index=index,element=element):
                    run=self.run_c_oracle(compile_source(source),'indice de Vector hors limites')
                    self.assertNotIn('999',run.stdout)
                    self.assertNotIn('runtime error:',run.stderr)

    def test_generated_removals_match_list_model(self):
        for seed,element in ((81,'Int'),(183,'u8')):
            rng=random.Random(seed);data=[];body=[];expected=[]
            suffix=' as Int' if element=='u8' else ''
            for step in range(32):
                if not data or rng.randrange(3)==0:
                    value=rng.randrange(256) if element=='u8' else rng.randrange(-100,100)
                    data.append(value);body.append(f'v.push({value});')
                else:
                    index=rng.randrange(len(data));expected.append(data.pop(index))
                    body.append(f'let n{step}=v.remove({index});print(n{step}{suffix});')
                body.append('yield;print(v.len());');expected.append(len(data))
                body.extend(f'print(v[{i}]{suffix});' for i in range(len(data)));expected.extend(data)
            with self.subTest(seed=seed,element=element):
                self.assertEqual(self.run_native(launch(''.join(body),element=element)).stdout,''.join(f'{n}\n' for n in expected))

    def test_owned_capture_cleanup_identity_and_launch_failure(self):
        source='''async fn work(mut v:->Vector<Int>)->Int{yield;return v.remove(0);}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push(17);address(v);
                let h=runtime::spawn_blocking(->work(->v));let r=h.join();
                let fresh=p.new();address(fresh);
                match r{Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        code=compile_source(source)
        marker='static void cell_drop_impl(Cell *cell, int resetting) {'
        self.assertEqual(code.count(marker),1)
        code=code.replace(marker,'static int observed_drops;\n'+marker+'\n++observed_drops;')
        code=code.replace('crust_task_context_close();','if(observed_drops!=2) abort();\ncrust_task_context_close();')
        for failed in (False,True):
            with self.subTest(failed=failed):
                run=self.run_c_oracle(self.reject_blocking(code) if failed else code)
                before,after,result=run.stdout.splitlines()
                self.assertEqual(before,after)
                self.assertEqual(result,'99' if failed else '17')


if __name__=='__main__':unittest.main()
