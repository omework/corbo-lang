"""Local conditional references: selection, lexical ancestry, suspension and cleanup."""
from pathlib import Path
import random
import unittest
from crust import Error, verify_program
import test_async_vector_results as native

class AsyncLocalReferenceTests(unittest.TestCase):
    run_native=native.AsyncVectorResultTests.run_native

    @staticmethod
    def program(body, flag=1, mode='mut'):
        ref='&mut Int' if mode=='mut' else '&Int'
        arg='&mut' if mode=='mut' else '&'
        effect='*r=42;' if mode=='mut' else 'print(*r);'
        return f'''async fn pick(flag:Int,a:{ref},b:{ref})->{ref}{{{body}}}
        fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
          let h=runtime::spawn(->pick({flag},{arg} a,{arg} b));
          match h.join(){{Ok(r)=>{{{effect}}},Err(_)=>{{print(999);}}}}
          print(a);print(b);drop(->a);drop(->b);let reused=p.new(77);print(reused);
        }}'''

    def test_recorded_case(self):
        self.assertEqual(self.run_native((Path(__file__).resolve().parents[1]/'validation/open-async-local-reference-if.crb').read_text()).stdout,'30\n20\n')

    def test_aliases_nested_blocks_both_modes(self):
        for mode in ('ref','mut'):
            for flag in (0,1):
                borrow='&mut *' if mode=='mut' else '&*'
                body=f'let mut r=if flag==1 {{let mut x={borrow}a;yield;{{x}}}} else {{let mut y={borrow}b;yield;y}};yield;let mut alias={borrow}r;return alias;'
                expected=('42\n20\n' if flag else '10\n42\n') if mode=='mut' else f'{10 if flag else 20}\n10\n20\n'
                with self.subTest(mode=mode,flag=flag):
                    self.assertEqual(self.run_native(self.program(body,flag,mode)).stdout,expected+'77\n')

    def test_exclusive_alternatives_last_use_and_ancestry(self):
        body='let mut r=if flag==1 {a} else {b};yield;let mut child=&mut *r;yield;child.set(7);r.set(8);return r;'
        for flag in (0,1):
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(self.program(body,flag)).stdout,('42\n20\n' if flag else '10\n42\n')+'77\n')
        for action in ('a.set(3);','b.set(3);','print(*a);','print(*b);','r.set(3);'):
            with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(self.program(body.replace('child.set(7);',action+'child.set(7);')))

    def test_shared_reborrow_of_selected_mutable_reference(self):
        body='let mut r=if flag==1 {a} else {b};let shared=&*r;yield;return shared;'
        source=self.program(body).replace(')->&mut Int',')->&Int').replace('*r=42;','print(*r);')
        self.assertEqual(self.run_native(source).stdout,'10\n10\n20\n77\n')
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(source.replace('yield;return shared;','r.set(3);yield;return shared;'))

    def test_branches_with_early_return(self):
        for flag in (0,1):
            body='let mut r=if flag==1 {return a;} else {yield;b};yield;return r;'
            self.assertEqual(self.run_native(self.program(body,flag)).stdout,('42\n20\n' if flag else '10\n42\n')+'77\n')

    def test_await_branches_forwarded_to_child_and_returned(self):
        for element in ('Int','u8'):
            for flag in (0,1):
                cast=' as Int' if element=='u8' else ''
                source=f'''async fn append(v:&mut Vector<{element}>)->&mut {element}{{yield;return v.push_new();}}
                async fn identity(x:&mut {element})->&mut {element}{{yield;return x;}}
                async fn pick(f:Int,a:&mut Vector<{element}>,b:&mut Vector<{element}>)->&mut {element}{{
                  let mut r=if f==1 {{append(&mut *a).await}} else {{let mut c=b.push_new();yield;c}};
                  yield;let mut alias=&mut *r;let mut result=identity(&mut *alias).await;return result;
                }}
                async fn work(a:&mut Vector<{element}>,b:&mut Vector<{element}>){{
                  let mut r=pick({flag},&mut *a,&mut *b).await;yield;print(*r{cast});r.set(255);print(a.len());print(b.len());
                }}
                fn main(){{let mut p=pool<Vector<{element}>>(2);let mut a=p.new();let mut b=p.new();
                  let h=runtime::spawn(->work(&mut a,&mut b));drop(->h.join());}}
                '''
                with self.subTest(element=element,flag=flag):
                    self.assertEqual(self.run_native(source).stdout,'0\n1\n0\n' if flag else '0\n0\n1\n')
                    for target in ('a','b'):
                        with self.assertRaisesRegex(Error,'emprunt actif'):
                            verify_program(source.replace('yield;print(*r',f'{target}.push(3);yield;print(*r'))

    def test_refused_types_modes_local_targets_and_mutable_binding(self):
        cases=[
         'let mut alias=a;return alias;',
         'let mut r=if flag==1 {a} else {&*b};return r;',
         'let mut r:&Int=if flag==1 {a} else {b};return r;',
         'let mut r=if flag==1 {a} else {1};return r;',
         'let mut r=if flag==1 {let mut local=[1];&mut local[0]} else {b};return r;',
         'let mut r=if flag==1 {a} else {yield;};return r;',
        ]
        for body in cases:
            with self.subTest(body=body),self.assertRaises(Error):verify_program(self.program(body))
        # Scope-lifetime checking must also run in a Void function, without return inference.
        source='''async fn work(a:&mut Int){let mut r=if true {let mut local=[1];&mut local[0]}else{a};yield;r.set(7);}
          fn main(){let mut p=pool<Int>(1);let mut a=p.new(1);let h=runtime::spawn(->work(&mut a));drop(->h.join());}'''
        with self.assertRaisesRegex(Error,'locale non durable'):verify_program(source)

    def test_immutable_binding_can_write_through_mutable_reference(self):
        body='let r=if flag==1 {a} else {b};yield;r.set(3);print(*r);return r;'
        # V4: mutation of the target does not reassign the reference binding.
        for flag in (0,1):
            self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                             '3\n'+('42\n20\n' if flag else '10\n42\n')+'77\n')

    def test_departing_alias_keeps_ancestors_and_releases_after_use(self):
        body='let mut child={let mut r=if flag==1 {a} else {b};&mut *r};yield;child.set(7);a.set(8);b.set(9);return a;'
        for flag in (0,1):
            self.assertEqual(self.run_native(self.program(body,flag)).stdout,'42\n9\n77\n')
        for target in ('a','b'):
            with self.subTest(target=target),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(self.program(body.replace('child.set(7);',f'{target}.set(3);child.set(7);')))

    def test_array_case_selection_inside_loop(self):
        source='''async fn work(a:&mut [Int;2]){
          let mut i=0;while i<3 {
            let mut cell=if i==1 {&mut a[1]} else {&mut a[0]};
            yield;cell.set(i);i=i+1;if i==2 {continue;} if i==3 {break;}
          }
          print(a[0]);print(a[1]);
        }
        fn main(){let mut a=[10,20];let h=runtime::spawn(->work(&mut a));drop(->h.join());}
        '''
        self.assertEqual(self.run_native(source).stdout,'2\n1\n')
        for action in ('a[0]=99;','a[1]=99;'):
            with self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(source.replace('yield;cell.set',action+'yield;cell.set'))

    def test_joined_local_selection_drop_and_transfer(self):
        for flag in (0,1):
            source=f'''async fn pick(f:Int,a:&mut Int,b:&mut Int)->&mut Int{{
              let mut r=if f==1 {{a}} else {{b}};yield;return r;
            }}
            fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
              let h=runtime::spawn(->pick({flag},&mut a,&mut b));
              let mut out=match h.join(){{Ok(r)=>{{r}},Err(_)=>{{&mut a}}}};
              out.set(42);print(a);print(b);drop(->a);drop(->b);
              let reused=p.new(77);print(reused);
            }}'''
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source).stdout,('42\n20\n' if flag else '10\n42\n')+'77\n')
                for action in ('drop(->a);','drop(->b);','let moved=<-a;print(moved);','let moved=<-b;print(moved);'):
                    with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt|réserv|utilisé'):
                        verify_program(source.replace('out.set(42);',action+'out.set(42);'))

    def test_independent_selection_and_frame_reuse(self):
        rng=random.Random(2097)
        for flag in [0,1,*[rng.randrange(2) for _ in range(2)]]:
            body='let mut r=if flag==1 {yield;a} else {yield;b};r.set(6);yield;return r;'
            source=self.program(body,flag)
            expected=[10,20];expected[0 if flag else 1]=42
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source).stdout,''.join(f'{v}\n' for v in expected)+'77\n')

if __name__=='__main__':unittest.main()
