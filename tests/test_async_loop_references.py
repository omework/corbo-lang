"""S5a × B5 × AS12: borrowed loop results and iteration cleanup."""
from pathlib import Path
import unittest
from crust import Error, verify_program
import test_async_vector_results as native

class AsyncLoopReferenceTests(unittest.TestCase):
    run_native=native.AsyncVectorResultTests.run_native
    reject_blocking=native.AsyncVectorResultTests.reject_blocking
    rejecting_callback=native.AsyncVectorResultTests.rejecting_callback

    @staticmethod
    def program(body,flag=1,mode='mut'):
        typ='&mut Int' if mode=='mut' else '&Int';arg='&mut' if mode=='mut' else '&'
        effect='*r=42;' if mode=='mut' else 'print(*r);'
        return f'''async fn pick(flag:Int,a:{typ},b:{typ})->{typ}{{{body}}}
        fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
          let h=runtime::spawn(->pick({flag},{arg} a,{arg} b));
          match h.join(){{Ok(r)=>{{{effect}}},Err(_)=>{{print(999);}}}}
          print(a);print(b);drop(->a);drop(->b);let reused=p.new(77);print(reused);
        }}'''

    def test_recorded_loop_result(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-reference-loop-result.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'30\n20\n')

    def test_continue_then_each_break_and_both_modes(self):
        for mode in ('ref','mut'):
            for flag in (0,1):
                borrow='&mut *' if mode=='mut' else '&*'
                body=f'''let mut i=0;let mut r=loop{{i=i+1;yield;if i<3{{continue;}}
                  if flag==1{{break {borrow}a;}}break {borrow}b;}};print(i);yield;return r;'''
                expected=('42\n20\n' if flag else '10\n42\n') if mode=='mut' else f'{10 if flag else 20}\n10\n20\n'
                with self.subTest(mode=mode,flag=flag):
                    self.assertEqual(self.run_native(self.program(body,flag,mode)).stdout,'3\n'+expected+'77\n')

    def test_nested_loops_and_local_reborrow_exits(self):
        for flag in (0,1):
            body='''let mut r=loop{let mut other=loop{yield;break &mut *b;};other.set(21);
              if flag==1 {let mut local=&mut *a;yield;break &mut *local;}
              break &mut *other;};yield;return r;'''
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(self.program(body,flag)).stdout,('42\n21\n' if flag else '10\n42\n')+'77\n')
        invalid=body.replace('other.set(21);','b.set(3);other.set(21);')
        with self.assertRaisesRegex(Error,'emprunt actif'):verify_program(self.program(invalid))

    def test_return_expression_and_early_function_return(self):
        body='return loop{yield;if flag==1{return a;}break &mut *b;};'
        for flag in (0,1):
            self.assertEqual(self.run_native(self.program(body,flag)).stdout,('42\n20\n' if flag else '10\n42\n')+'77\n')

    def test_early_return_keeps_its_source_in_contract(self):
        source=self.program('return loop{yield;if flag==1{return a;}break &mut *b;};')
        for name in ('a','b'):
            for action in (f'print({name});',f'{name}=3;',f'drop(->{name});'):
                with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt|réserv|utilisé'):
                    verify_program(source.replace('*r=42;',action+'*r=42;'))

    def test_returned_result_reserves_every_source(self):
        source=self.program('let mut r=loop{if flag==1{break &mut *a;}break &mut *b;};yield;return r;')
        for action in ('print(a);','print(b);','a=3;','b=3;','drop(->a);','drop(->b);'):
            with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt|réserv|utilisé'):
                verify_program(source.replace('*r=42;',action+'*r=42;'))
        for action in ('a.set(3);','b.set(3);'):
            with self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(source.replace('yield;return r;',action+'yield;return r;'))

    def test_break_cleans_inactive_owned_child_before_receiving_reference(self):
        for flag in (0,1):
            source=f'''async fn hold(junk:->Int){{print(*junk);}}
            async fn choose(f:Int,a:&mut Int,b:&mut Int,junk:->Int)->&mut Int{{
              let mut i=0;
              let mut r=loop{{i=i+1;yield;if i<3{{continue;}}
                let inactive=hold(->junk);
                if f==1{{yield;break &mut *a;}}yield;break &mut *b;
              }};print(i);yield;return r;
            }}
            fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
              let mut garbage=pool<Int>(1);let junk=garbage.new(77);
              let h=runtime::spawn(->choose({flag},&mut a,&mut b,->junk));
              match h.join(){{Ok(r)=>{{let reused=garbage.new(88);print(reused);*r=42;}},Err(_)=>{{print(999);}}}}
              print(a);print(b);
            }}'''
            with self.subTest(flag=flag):
                run=self.run_native(source)
                self.assertEqual(run.stdout,'3\n88\n'+('42\n20\n' if flag else '10\n42\n'))
                self.assertEqual(run.stderr.count('destroy junk=77\n'),1)
                self.assertLess(run.stderr.index('destroy junk=77'),run.stderr.index('destroy reused=88'))

    def test_array_slots_and_independent_index_model(self):
        for index in (0,1,2):
            source=f'''async fn work(a:&mut [Int;3]){{
              let mut n=0;let mut cell=loop{{yield;if n<{index}{{n=n+1;continue;}}break &mut a[n];}};
              yield;cell.set(99);print(a[0]);print(a[1]);print(a[2]);
            }}
            fn main(){{let mut a=[11,22,33];let h=runtime::spawn(->work(&mut a));drop(->h.join());}}'''
            expected=[11,22,33];expected[index]=99
            self.assertEqual(self.run_native(source).stdout,''.join(f'{n}\n' for n in expected))
            with self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(source.replace('yield;cell.set(99);','a[0]=3;yield;cell.set(99);'))

    def test_vector_cases_through_await_and_join_match(self):
        for element in ('Int','u8'):
            cast=' as Int' if element=='u8' else ''
            source=f'''async fn append(v:&mut Vector<{element}>)->&mut {element}{{yield;return v.push_new();}}
            async fn pick(a:&mut Vector<{element}>,b:&mut Vector<{element}>)->&mut {element}{{
              let mut selected=loop{{let h=runtime::spawn_blocking(->append(a));
                let mut r=match h.await{{Ok(c)=>{{c}},Err(_)=>{{b.push_new()}}}};yield;break &mut *r;
              }};yield;return selected;
            }}
            async fn work(a:&mut Vector<{element}>,b:&mut Vector<{element}>){{
              let mut r=pick(a,b).await;print(*r{cast});yield;r.set(255);print(a.len());print(b.len());
            }}
            fn main(){{let mut p=pool<Vector<{element}>>(2);let mut a=p.new();let mut b=p.new();
              let h=runtime::spawn(->work(&mut a,&mut b));drop(->h.join());}}'''
            for failed in (False,True):
                with self.subTest(element=element,failed=failed):
                    self.assertEqual(self.run_native(source,reject=failed).stdout,'0\n0\n1\n' if failed else '0\n1\n0\n')
            for target in ('a','b'):
                with self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(source.replace('yield;r.set(255);',f'{target}.push(3);yield;r.set(255);'))

    def test_rejected_types_modes_missing_values_and_local_sources(self):
        for body in (
          'let mut r=loop{if flag==1{break &mut *a;}break &*b;};return r;',
          'let mut r=loop{if flag==1{break &mut *a;}break 7;};return r;',
          'let mut r=loop{if flag==1{break &mut *a;}break;};return r;',
          'let mut r=loop{let mut local=[1];break &mut local[0];};return r;',
          'let mut r=loop{if flag==1{let mut local=[1];break &mut local[0];}break &mut *b;};return r;',
        ):
            with self.subTest(body=body),self.assertRaises(Error):verify_program(self.program(body))
        source='''async fn bad(a:&mut Int){let mut r=loop{let mut local=[1];break &mut local[0];};yield;r.set(7);}
          fn main(){let mut p=pool<Int>(1);let mut a=p.new(10);let h=runtime::spawn(->bad(&mut a));drop(->h.join());}'''
        with self.assertRaisesRegex(Error,'locale non durable'):verify_program(source)

if __name__=='__main__':unittest.main()
