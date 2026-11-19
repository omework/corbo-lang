"""VE3/VE4 × AS2/AS8: operations executed inside suspendable bodies."""
from pathlib import Path
import random
import re
import unittest
from crust import Error, compile_source, verify_program
import test_async_runtime
import test_async_vector_results as results
from test_async_vector_results import CASES


def launch(body, *, element='Int', before='', after='', helpers='', parameter=None):
    parameter = parameter or f'v:&mut Vector<{element}>'
    return helpers + f'''async fn work({parameter}){{{body}}}
        fn main(){{let mut p=pool<Vector<{element}>>(1);
        #(directive,stack_region_max_size=1M){{let mut v=p.new();{before}
        let h=runtime::spawn(->work(&mut v));
        match h.join(){{Ok(())=>{{}},Err(_)=>{{print(999);}}}}{after}}}}}'''


class AsyncVectorOperationTests(unittest.TestCase):
    run_native = results.AsyncVectorResultTests.run_native
    reject_blocking = results.AsyncVectorResultTests.reject_blocking
    rejecting_callback = results.AsyncVectorResultTests.rejecting_callback

    def test_recorded_producer(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-vector-result-producer.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'1\n1\n')

    def test_operation_families_and_failure_publication(self):
        for case,(typ,element,operation,arms,answers) in CASES.items():
            for failed in (False,True):
                operation=CASES[case][2]
                arms=re.sub(r'\bv\b','payload',arms)
                setup=''; oldlen=0
                if case.endswith('option'):
                    if not failed:setup='v.push(17);';oldlen=1
                    length=0
                elif case.endswith('replace'):
                    setup='v.push(17);';length=1
                    operation=operation.replace('INDEX','1' if failed else '0')
                elif case in ('int_try_push','byte_try_push','capacity_result'):
                    if failed:
                        oldlen=1048576//(4 if element=='Int' else 1)
                        setup=f'let mut i=0;while i<{oldlen}{{v.push(0);i=i+1;}}'
                    length=oldlen+(not failed)
                    if case=='capacity_result':setup+='let bytes:[u8;1]=[42];'
                else:
                    operation=operation.replace('FD','-1' if failed else '0')
                    length=0 if failed else 3
                body=f'{setup}yield;let r:{typ}={operation};yield;match r{{{arms}}}print(v.len());'
                expected=answers[int(failed)]+'\n'+str(int(length))+'\n'
                if case.endswith('replace'):
                    body+='print(v[0]'+(' as Int' if element=='u8' else '')+');'
                    expected+=('17' if failed else '-23' if element=='Int' else '255')+'\n'
                with self.subTest(case=case,failed=failed):
                    self.assertEqual(self.run_native(launch(body,element=element)).stdout,expected)

    def test_suspended_arguments_are_snapshotted_left_to_right(self):
        helpers='''async fn next(n:&mut Int)->Int{yield;n.set(*n+1);return *n;}
            async fn value(n:&mut Int)->Int{yield;n.set(*n+1);return 40+*n;}'''
        body='''let mut index=0;
            match v.replace(index,value(&mut index).await){Ok(n)=>{print(n);},Err(n)=>{print(n);}}
            match v.replace(next(&mut index).await,value(&mut index).await){Ok(n)=>{print(n);},Err(n)=>{print(n);}}
            print(index);print(v[0]);print(v[1]);print(v[2]);'''
        self.assertEqual(self.run_native(launch(body,helpers=helpers,before='v.push(10);v.push(20);v.push(30);')).stdout,
                         '10\n30\n3\n41\n20\n43\n')

    def test_receiver_is_reserved_during_argument_await(self):
        helper='async fn size(v:&Vector<Int>)->Int{yield;return v.len();}'
        valid=launch('drop(->v.try_push(size(&*other).await));',helpers=helper,
                     parameter='v:&mut Vector<Int>,other:&Vector<Int>')
        valid=valid.replace('let h=','let mut other=p.new();other.push(7);let h=').replace('>>(1)','>>(2)').replace('work(&mut v)','work(&mut v,&other)')
        self.assertEqual(self.run_native(valid).stdout,'')
        for operation in ('v.try_push(size(&*v).await)','v.replace(size(&*v).await,4)',
                          'v.replace(0,size(&*v).await)'):
            with self.subTest(operation=operation),self.assertRaisesRegex(Error,'emprunt actif|incompatible'):
                verify_program(launch('drop(->'+operation+');',helpers=helper))

    def test_previous_view_last_use_and_continuations(self):
        prefix='let view=&v[..];print(view[0]);'
        operation='drop(->v.try_push(20));'
        self.assertEqual(self.run_native(launch(prefix+operation,before='v.push(10);',after='print(v.len());')).stdout,'10\n2\n')
        for tail in ('print(view[0]);','yield;print(view[0]);','if true{print(view[0]);}'):
            with self.subTest(tail=tail),self.assertRaisesRegex(Error,'emprunt actif|incompatible'):
                verify_program(launch(prefix+operation+tail,before='v.push(10);'))

    def test_byte_block_extension_and_self_aliasing(self):
        body='''let bytes:[u8;3]=[1,2,3];
            match v.try_extend(&bytes){Ok(())=>{},Err(CapacityError::CapacityExceeded)=>{print(99);}}
            yield;print(v[0] as Int);print(v[2] as Int);'''
        self.assertEqual(self.run_native(launch(body,element='u8',after='print(v.len());')).stdout,'1\n3\n3\n')
        with self.assertRaisesRegex(Error,'emprunt actif|incompatible'):
            verify_program(launch('drop(->v.try_extend(&v[..]));',element='u8'))

    def test_read_eof_and_error_leave_length_unchanged(self):
        arms=re.sub(r'\bv\b','payload',CASES['read_result'][3])
        for fd,stdin,expected in ((0,'','91\n1\n17\n'),(-1,'abc','93\n1\n17\n')):
            body=f'yield;match v.read_fd({fd}){{{arms}}}print(v.len());print(v[0] as Int);'
            with self.subTest(fd=fd):
                self.assertEqual(self.run_native(launch(body,element='u8',before='v.push(17);'),stdin=stdin).stdout,expected)

    def test_discarded_fallible_operations_require_explicit_use(self):
        for operation in ('v.try_push(20)','v.replace(0,20)'):
            source=launch('drop(->'+operation+');',before='v.push(10);',after='print(v.len());')
            self.assertEqual(self.run_native(source).stdout,('2' if 'push' in operation else '1')+'\n')
            for unused in (operation+';','let unused='+operation+';'):
                with self.subTest(unused=unused),self.assertRaisesRegex(Error,'usage explicite|sans usage'):
                    verify_program(launch(unused))
        self.assertEqual(self.run_native(launch('v.pop();',before='v.push(10);',after='print(v.len());')).stdout,'0\n')

    def test_scalar_types_and_receiver_mutability(self):
        for element,operation in (('Int','v.try_push(true)'),('Int','v.replace(false,3)'),
                                  ('u8','v.try_push(300)'),('Int','v.try_extend(&[1,2])'),
                                  ('Int','v.read_fd(0)'),('u8','v.read_fd(true)')):
            with self.subTest(operation=operation),self.assertRaises(Error):
                verify_program(launch('drop(->'+operation+');',element=element))
        with self.assertRaisesRegex(Error,'mutable'):
            verify_program(launch('drop(->v.try_push(1));').replace('v:&mut Vector<Int>','v:&Vector<Int>').replace('work(&mut v)','work(&v)'))

    def test_generated_operation_sequences_against_list_model(self):
        for seed in (37,91):
            rng=random.Random(seed);values=[];body=[];expected=[]
            for _ in range(28):
                operation=rng.choice(('push','replace','pop'));incoming=rng.randrange(-100,100)
                if operation=='push':
                    values.append(incoming)
                    body.append(f'match v.try_push({incoming}){{Ok(())=>{{print(777);}},Err(n)=>{{print(n);}}}}')
                    expected.append(777)
                elif operation=='replace':
                    index=rng.randrange(-1,len(values)+2)
                    old=incoming
                    if 0<=index<len(values):old,values[index]=values[index],incoming
                    body.append(f'match v.replace({index},{incoming}){{Ok(n)=>{{print(n);}},Err(n)=>{{print(n);}}}}')
                    expected.append(old)
                else:
                    expected.append(values.pop() if values else 888)
                    body.append('match v.pop(){Some(n)=>{print(n);},None=>{print(888);}}')
                body.append('yield;print(v.len());');expected.append(len(values))
            with self.subTest(seed=seed):
                self.assertEqual(self.run_native(launch(''.join(body))).stdout,''.join(f'{n}\n' for n in expected))

    def test_atomic_extension_capacity_and_read_priority(self):
        body='''let mut i=0;while i<1048575{v.push(7);i=i+1;}
            let bytes:[u8;2]=[8,9];yield;
            match v.try_extend(&bytes){Ok(())=>{print(999);},Err(CapacityError::CapacityExceeded)=>{print(v.len());}}
            v.push(10);
            match v.read_fd(-1){Ok(n)=>{print(n);},Err(ReadError::CapacityExceeded)=>{print(92);},Err(ReadError::EndOfStream)=>{print(999);},Err(ReadError::Io)=>{print(999);}}
            print(v.len());print(v[1048574] as Int);print(v[1048575] as Int);'''
        self.assertEqual(self.run_native(launch(body,element='u8')).stdout,'1048575\n92\n1048576\n7\n10\n')

    def test_owned_capture_cleanup_and_pool_reuse_on_launch_failure(self):
        source='''async fn work(mut v:->Vector<Int>)->Result<Int,Int>{
                yield;return v.replace(0,23);}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push(17);
                let h=runtime::spawn_blocking(->work(->v));let r=h.join();
                let mut replacement=p.new();replacement.push(39);
                match r{Ok(inner)=>{match inner{Ok(n)=>{print(n);},Err(n)=>{print(n);}}},Err(_)=>{print(99);}}
                print(replacement[0]);}'''
        for failed in (False,True):
            with self.subTest(failed=failed):
                self.assertEqual(self.run_native(source,reject=failed).stdout,('99' if failed else '17')+'\n39\n')

    def test_cleanup_count_and_stable_slot_identity(self):
        source='''async fn work(mut v:->Vector<Int>)->Result<Int,Int>{yield;return v.replace(0,23);}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push(17);address(v);
                let h=runtime::spawn_blocking(->work(->v));let r=h.join();
                let mut replacement=p.new();address(replacement);replacement.push(39);
                match r{Ok(inner)=>{match inner{Ok(n)=>{print(n);},Err(n)=>{print(n);}}},Err(_)=>{print(99);}}
                print(replacement[0]);}'''
        code=compile_source(source)
        anchor='static void cell_drop_impl(Cell *cell, int resetting) {'
        self.assertEqual(code.count(anchor),1)
        code=code.replace(anchor,'static int observed_drops;\n'+anchor+'\n++observed_drops;')
        self.assertEqual(code.count('crust_task_context_close();'),1)
        code=code.replace('crust_task_context_close();','if(observed_drops!=2) abort();\ncrust_task_context_close();')
        for failed in (False,True):
            with self.subTest(failed=failed):
                run=test_async_runtime.AsyncRuntimeTests().run_c_oracle(self.reject_blocking(code) if failed else code)
                first,second,result,value=run.stdout.splitlines()
                self.assertEqual(first,second)
                self.assertEqual((result,value),('99' if failed else '17','39'))

    def test_suspended_byte_and_slice_arguments(self):
        helpers='''async fn byte()->u8{yield;let n:u8=255;return n;}
            async fn view(src:&Vector<u8>)->&[u8]{yield;return &src[..];}'''
        body='''drop(->v.try_push(byte().await));
            drop(->v.try_extend(view(&*other).await));
            print(v[0] as Int);print(v[1] as Int);'''
        source=launch(body,element='u8',helpers=helpers,
                      parameter='v:&mut Vector<u8>,other:&Vector<u8>')
        source=source.replace('>>(1)','>>(2)').replace('let h=',
                  'let mut other=p.new();other.push(33);let h=').replace('work(&mut v)','work(&mut v,&other)')
        self.assertEqual(self.run_native(source).stdout,'255\n33\n')

    def test_caller_cannot_drop_or_use_vector_before_join(self):
        source=launch('yield;drop(->v.try_push(20));',after='drop(->v);let mut reused=p.new();reused.push(42);print(reused[0]);')
        self.assertEqual(self.run_native(source).stdout,'42\n')
        for action in ('drop(->v);','print(v.len());','v.push(3);'):
            with self.subTest(action=action),self.assertRaises(Error):
                verify_program(source.replace('match h.join()',action+'match h.join()'))


if __name__=='__main__':unittest.main()
