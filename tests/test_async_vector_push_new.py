"""VE6 × AS9: initialized, typed element borrows across suspension."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_async_runtime
import test_async_vector_results as results
from test_async_vector_operations import launch

class AsyncVectorPushNewTests(unittest.TestCase):
    run_native=results.AsyncVectorResultTests.run_native
    run_c_oracle=test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_recorded_case(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-vector-push-new.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'0\n23\n1\n23\n')

    def test_types_and_fronts(self):
        for element in ('Int','u8'):
            for reverse in (False,True):
                suffix=' as Int' if element=='u8' else ''
                source=launch(f'''let mut cell=v.push_new();print(*cell{suffix});yield;
                    cell.set(255);print(*cell{suffix});
                    v.push(42);print(v[0]{suffix});print(v[1]{suffix});print(v[2]{suffix});''',
                    element=element,before='v.push(17);')
                source=source.replace('#(directive,stack_region_max_size=1M)', '')
                if reverse:
                    source=source.replace('>>(1)','>>(2)').replace('let mut v=p.new();','let mut blocker=p.new();blocker.push(7);let mut v=p.new();')
                code=compile_source(source)
                marker='static void *vector_push_new(Cell *cell, const void *initial) {'
                self.assertEqual(code.count(marker),1)
                code=code.replace(marker,marker+f'\nif(vector_descends(vector_items(cell)) != {int(reverse)}) abort();')
                with self.subTest(element=element,reverse=reverse):
                    self.assertEqual(self.run_c_oracle(code).stdout,'0\n255\n17\n255\n42\n')

    def test_receiver_reserved_until_last_use(self):
        for action in ('v.push(1);','print(v.len());','v.remove(0);','let mut next=v.push_new();next.set(1);'):
            with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(launch('let mut cell=v.push_new();'+action+'yield;cell.set(3);'))
        self.assertEqual(self.run_native(launch('let mut cell=v.push_new();yield;cell.set(3);v.push(4);print(v.len());')).stdout,'2\n')

    def test_nested_reborrow_keeps_parent_reserved(self):
        for element in ('Int','u8'):
            helpers=f'''async fn write(x:&mut {element}){{yield;x.set(42);}}'''
            suffix=' as Int' if element=='u8' else ''
            body=f'let mut cell=v.push_new();write(&mut *cell).await;print(*cell{suffix});'
            with self.subTest(element=element):
                self.assertEqual(self.run_native(launch(body,element=element,helpers=helpers)).stdout,'42\n')
                with self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(launch(body.replace('write(&mut *cell).await;', 'let t=write(&mut *cell);cell.set(9);t.await;'),element=element,helpers=helpers))

    def test_returned_borrow_through_two_tasks(self):
        for element in ('Int','u8'):
            helpers=f'''async fn append(v:&mut Vector<{element}>)->&mut {element}{{yield;return v.push_new();}}
                async fn relay(v:&mut Vector<{element}>)->&mut {element}{{let mut r=append(&mut *v).await;yield;return r;}}'''
            suffix=' as Int' if element=='u8' else ''
            body=f'let mut cell=relay(&mut *v).await;print(*cell{suffix});cell.set(255);print(v[0]{suffix});'
            with self.subTest(element=element):
                self.assertEqual(self.run_native(launch(body,element=element,helpers=helpers)).stdout,'0\n255\n')
                with self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(launch(body.replace('cell.set(255);','v.push(9);cell.set(255);'),element=element,helpers=helpers))

    def test_local_reference_return_and_owned_escape(self):
        helpers='async fn append(v:&mut Vector<Int>)->&mut Int{let mut cell=v.push_new();yield;cell.set(17);return cell;}'
        self.assertEqual(self.run_native(launch('let mut cell=append(&mut *v).await;print(*cell);',helpers=helpers)).stdout,'17\n')
        for returned in ('v.push_new()','cell'):
            source=f'''async fn bad(mut v:->Vector<Int>)->&mut Int{{let mut cell=v.push_new();yield;return {returned};}}
                fn main(){{let mut p=pool<Vector<Int>>(1);let mut v=p.new();let h=runtime::spawn(->bad(->v));drop(->h.join());}}'''
            with self.subTest(returned=returned),self.assertRaisesRegex(Error,'paramètre mutable durable'):
                verify_program(source)

    def test_nominal_types_mutability_and_arity(self):
        for body,element in (
            ('let mut c:Int=v.push_new();print(c);','Int'),
            ('let mut c:&mut Int=v.push_new();c.set(2);','u8'),
            ('let mut c=v.push_new(1);c.set(2);','Int'),
            ('let mut c=v.push_new();c.set(256);','u8'),
            ('let mut c=v.push_new();let n:Int=*c;print(n);','u8'),
            ('let mut c=v.push_new();let n:u8=*c;print(n as Int);','Int'),
        ):
            with self.subTest(body=body),self.assertRaises(Error):verify_program(launch(body,element=element))
        with self.assertRaisesRegex(Error,'mutable'):
            verify_program(launch('let c=v.push_new();print(*c);').replace('v:&mut Vector','v:&Vector').replace('work(&mut v)','work(&v)'))
        self.assertEqual(self.run_native(launch('let c=v.push_new();yield;c.set(2);print(*c);')).stdout,'2\n')

    def test_joined_reference_preserves_element_type_and_source(self):
        for element in ('Int','u8'):
            suffix=' as Int' if element=='u8' else ''
            helper=f'async fn append(v:&mut Vector<{element}>)->&mut {element}{{yield;return v.push_new();}}'
            source=helper+f'''fn main(){{let mut p=pool<Vector<{element}>>(1);let mut v=p.new();v.push(17);
                let h=runtime::spawn(->append(&mut v));let r=h.join();
                match r{{Ok(cell)=>{{print(*cell{suffix});*cell=255;}},Err(_)=>{{print(999);}}}}
                print(v[0]{suffix});print(v[1]{suffix});drop(->v);let fresh=p.new();print(fresh.len());}}'''
            with self.subTest(element=element):
                self.assertEqual(self.run_native(source).stdout,'0\n17\n255\n0\n')
                with self.assertRaises(Error):verify_program(source.replace('let r=h.join();','let r=h.join();drop(->v);'))
            body=f'''let h=runtime::spawn(->append(&mut *v));
                match h.await{{Ok(cell)=>{{print(*cell{suffix});cell.set(255);}},Err(_)=>{{print(999);}}}}
                print(v[0]{suffix});'''
            with self.subTest(element=element,caller='async'):
                self.assertEqual(self.run_native(launch(body,element=element,helpers=helper)).stdout,'0\n255\n')

    def test_sync_capture_of_byte_element(self):
        source='''async fn set(b:&mut u8){yield;b.set(255);}
            fn main(){let mut p=pool<Vector<u8>>(1);let mut v=p.new();v.push(17);
            let mut cell=v.push_new();let h=runtime::spawn(->set(cell));
            match h.join(){Ok(())=>{},Err(_)=>{print(999);}}print(v[0] as Int);print(v[1] as Int);}'''
        self.assertEqual(self.run_native(source).stdout,'17\n255\n')
        with self.assertRaises(Error):verify_program(source.replace('set(b:&mut u8)','set(b:&mut Int)'))

    def test_branches_loops_and_direct_store(self):
        for element in ('Int','u8'):
            suffix=' as Int' if element=='u8' else ''
            body=f'''let mut n=0;loop{{
                let mut cell=v.push_new();yield;*cell=17;
                if n==0{{n=n+1;continue;}}
                print(*cell{suffix});break;
            }}print(v.len());print(v[0]{suffix});print(v[1]{suffix});
            if true{{let mut cell=v.push_new();yield;cell.set(255);}}
            print(v[2]{suffix});'''
            with self.subTest(element=element):
                self.assertEqual(self.run_native(launch(body,element=element)).stdout,'17\n2\n17\n17\n255\n')
                with self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(launch(body.replace('yield;*cell=17;', 'v.push(7);yield;*cell=17;'),element=element))

    def test_growth_matches_list_model(self):
        import random
        for seed,element in ((817,'Int'),(810,'u8')):
            rng=random.Random(seed);values=[];body=[];expected=[]
            suffix=' as Int' if element=='u8' else ''
            for i in range(16):
                n=rng.randrange(256) if element=='u8' else rng.randrange(-100,100)
                body.append(f'let mut c{i}=v.push_new();print(*c{i}{suffix});yield;c{i}.set({n});')
                expected.append(0);values.append(n)
                body.append('print(v.len());');expected.append(len(values))
                for j,value in enumerate(values):
                    body.append(f'print(v[{j}]{suffix});');expected.append(value)
            with self.subTest(seed=seed):
                self.assertEqual(self.run_native(launch(''.join(body),element=element)).stdout,''.join(f'{n}\n' for n in expected))

    def test_capacity_failure_before_reference_publication(self):
        for element,width in (('Int',4),('u8',1)):
            count=1048576//width
            body=f'''let mut i=0;while i<{count}{{v.push(7);i=i+1;}}
                yield;let mut cell=v.push_new();print(999);cell.set(1);'''
            with self.subTest(element=element):
                run=self.run_c_oracle(compile_source(launch(body,element=element)), 'capacité')
                self.assertNotIn('999',run.stdout)
                self.assertNotIn('runtime error:',run.stderr)

    def test_owned_source_lifetime_and_reuse(self):
        for element in ('Int','u8'):
            suffix=' as Int' if element=='u8' else ''
            source=f'''async fn work(mut v:->Vector<{element}>)->{element}{{
                let mut cell=v.push_new();yield;cell.set(255);let value=*cell;drop(->v);return value;}}
                fn main(){{let mut p=pool<Vector<{element}>>(1);let mut v=p.new();address(v);
                let h=runtime::spawn(->work(->v));let r=h.join();
                let fresh=p.new();address(fresh);
                match r{{Ok(n)=>{{print(n{suffix});}},Err(_)=>{{print(999);}}}}}}'''
            with self.subTest(element=element):
                lines=self.run_native(source).stdout.splitlines()
                self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[2],'255')
                with self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(source.replace('let value=*cell;drop(->v);','drop(->v);let value=*cell;'))
                with self.assertRaisesRegex(Error,'plus utilisable'):
                    verify_program(source.replace('let mut cell=v.push_new();','drop(->v);let mut cell=v.push_new();'))

    def test_contract_relay_of_joined_byte(self):
        source='''async fn append(v:&mut Vector<u8>)->&mut u8{yield;return v.push_new();}
            fn relay(v:&mut Vector<u8>)->&mut u8{
                let h=runtime::spawn(->append(v));
                match h.join(){Ok(cell)=>{return &mut *cell;},Err(_)=>{return v.push_new();}}
            }
            fn main(){let mut p=pool<Vector<u8>>(1);let mut v=p.new();
                let mut c=relay(&mut v);*c=255;print(v[0] as Int);}'''
        self.assertEqual(self.run_native(source).stdout,'255\n')
        with self.assertRaises(Error):verify_program(source.replace('*c=255;','drop(->v);*c=255;'))

    def test_shared_byte_reborrow_preserves_mutable_ancestry(self):
        helpers='''async fn read(b:&u8)->u8{yield;return *b;}
            async fn view(b:&mut u8)->&u8{yield;return &*b;}'''
        body='''let mut cell=v.push_new();cell.set(42);
            let shared=&*cell;let t=read(shared);yield;let n=t.await;print(n as Int);
            let shared2=view(&mut *cell).await;print(*shared2 as Int);
            cell.set(255);print(v[0] as Int);'''
        self.assertEqual(self.run_native(launch(body,element='u8',helpers=helpers)).stdout,'42\n42\n255\n')
        for mutation in ('cell.set(1);','v.push(1);'):
            with self.subTest(mutation=mutation),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(launch(body.replace('yield;let n=', mutation+'yield;let n='),element='u8',helpers=helpers))
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(launch(body.replace('print(*shared2 as Int);','cell.set(1);print(*shared2 as Int);'),element='u8',helpers=helpers))
