"""B5 × AS11/12: tail conditional borrows keep every durable origin."""
from pathlib import Path
import random
import unittest
from crust import Error, verify_program
import test_async_vector_results as native


class AsyncReferenceReturnTests(unittest.TestCase):
    run_native = native.AsyncVectorResultTests.run_native

    def test_recorded_counterexample(self):
        source = (Path(__file__).resolve().parents[1] / 'validation/open-async-reference-if-expression.crb').read_text()
        self.assertEqual(self.run_native(source).stdout, '30\n20\n')

    @staticmethod
    def program(flag, mode='mut', body=None):
        reference = '&mut Int' if mode == 'mut' else '&Int'
        capture = '&mut' if mode == 'mut' else '&'
        body = body or 'yield; return if flag == 1 { yield; left } else { yield; right };'
        effect = '*cell=42;' if mode == 'mut' else 'print(*cell);'
        return f'''async fn choose(flag:Int,left:{reference},right:{reference})->{reference}{{{body}}}
        fn main(){{let mut p=pool<Int>(2);let mut left=p.new(10);let mut right=p.new(20);
          let h=runtime::spawn(->choose({flag},{capture} left,{capture} right));
          match h.join(){{Ok(cell)=>{{{effect}}},Err(_)=>{{print(999);}}}}
          print(left);print(right);drop(->left);drop(->right);
          let reused=p.new(77);print(reused);
        }}'''

    def test_both_modes_and_suspended_arms(self):
        for mode in ('ref','mut'):
            for flag in (0,1):
                expected = ('10\n42\n' if flag == 0 else '42\n20\n') if mode == 'mut' else f'{10 if flag else 20}\n10\n20\n'
                with self.subTest(mode=mode,flag=flag):
                    self.assertEqual(self.run_native(self.program(flag,mode)).stdout, expected+'77\n')

    def test_nested_early_returns_and_condition_once(self):
        body = '''let mut tick=0;return if {tick=tick+1;print(tick);flag==1} {
          if flag==1 {yield;return left;} yield;right
        } else if flag==2 {yield;left} else {yield;right};'''
        for flag in (0,1,2):
            with self.subTest(flag=flag):
                expected='10\n42\n' if flag==0 else '42\n20\n'
                self.assertEqual(self.run_native(self.program(flag,body=body)).stdout,'1\n'+expected+'77\n')

    def test_return_from_array_slots(self):
        for flag in (0,1):
            source=f'''async fn choose(flag:Int,a:&mut [Int;2])->&mut Int{{
              return if flag==1 {{yield;&mut a[0]}} else {{yield;&mut a[1]}};
            }}
            async fn work(a:&mut [Int;2]){{let mut cell=choose({flag},&mut *a).await;
              yield;cell.set(42);print(a[0]);print(a[1]);}}
            fn main(){{let mut a=[10,20];let h=runtime::spawn(->work(&mut a));drop(->h.join());}}'''
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source).stdout,'42\n20\n' if flag else '10\n42\n')
                for action in ('a[0]=3;','a[1]=3;'):
                    with self.assertRaisesRegex(Error,'emprunt actif'):
                        verify_program(source.replace('yield;cell.set',action+'yield;cell.set'))

    def test_awaited_vector_cases_and_relay(self):
        for element in ('Int','u8'):
            for flag in (0,1):
                cast=' as Int' if element=='u8' else ''
                source=f'''async fn append(v:&mut Vector<{element}>)->&mut {element}{{yield;return v.push_new();}}
                async fn choose(f:Int,a:&mut Vector<{element}>,b:&mut Vector<{element}>)->&mut {element}{{
                  return if f==1 {{append(&mut *a).await}} else {{let mut c=append(&mut *b).await;yield;c}};
                }}
                async fn relay(f:Int,a:&mut Vector<{element}>,b:&mut Vector<{element}>)->&mut {element}{{
                  let mut c=choose(f,&mut *a,&mut *b).await;yield;return c;
                }}
                async fn work(a:&mut Vector<{element}>,b:&mut Vector<{element}>){{
                  let mut c=relay({flag},&mut *a,&mut *b).await;print(*c{cast});yield;c.set(255);
                  print(a.len());print(b.len());
                }}
                fn main(){{let mut p=pool<Vector<{element}>>(2);let mut a=p.new();let mut b=p.new();
                  let h=runtime::spawn(->work(&mut a,&mut b));drop(->h.join());
                }}'''
                with self.subTest(element=element,flag=flag):
                    self.assertEqual(self.run_native(source).stdout,'0\n1\n0\n' if flag else '0\n0\n1\n')
                    for target in ('a','b'):
                        with self.assertRaisesRegex(Error,'emprunt actif'):
                            verify_program(source.replace('yield;c.set(255);',f'{target}.push(3);yield;c.set(255);'))

    def test_reject_local_owned_wrong_mode_and_missing_result(self):
        invalid = [
          'return if flag==1 {let mut local=1;&mut local} else {right};',
          'return if flag==1 {let mut p=pool<Int>(1);let mut local=p.new(1);&mut local} else {right};',
          'return if flag==1 {&*left} else {right};',
          'return if flag==1 {left} else {yield;};',
          'return if flag==1 {left} else {1};',
        ]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(Error):
                verify_program(self.program(1,body=body))
        owned=self.program(1).replace('left:&mut Int','mut left:->Int').replace('choose(1,&mut left','choose(1,->left').replace('print(left);','').replace('drop(->left);','')
        with self.assertRaisesRegex(Error,'durable'):verify_program(owned)

    def test_join_retains_both_sources_until_last_use(self):
        source=self.program(1)
        for target in ('left','right'):
            for action in (f'print({target});',f'{target}=3;',f'drop(->{target});'):
                with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt|réserv|utilisé'):
                    verify_program(source.replace('*cell=42;',action+'*cell=42;'))

    def test_cleanup_before_join_and_nonreturned_capture_release(self):
        for flag in (0,1):
            source=f'''async fn choose(f:Int,a:&mut Int,b:&mut Int,ignored:&mut Int,mut junk:->Int)->&mut Int{{
              print(*ignored);print(*junk);
              return if f==1 {{yield;a}} else {{yield;b}};
            }}
            fn main(){{let mut p=pool<Int>(3);let mut a=p.new(10);let mut b=p.new(20);let mut ignored=p.new(30);
              let mut garbage=pool<Int>(1);let junk=garbage.new(77);
              let h=runtime::spawn(->choose({flag},&mut a,&mut b,&mut ignored,->junk));
              match h.join(){{Ok(r)=>{{-> ignored;
                drop(->ignored);let reused=garbage.new(88);print(reused);*r=42;
              }},Err(_)=>{{print(999);}}}}
              print(a);print(b);
            }}'''
            with self.subTest(flag=flag):
                run=self.run_native(source)
                self.assertEqual(run.stdout,'30\n77\n88\n'+('42\n20\n' if flag else '10\n42\n'))
                trace=[line for line in run.stderr.splitlines() if line.startswith('destroy ')]
                self.assertEqual(trace[:3],['destroy junk=77','destroy ignored=30','destroy reused=88'])
                self.assertEqual(run.stderr.count('destroy junk=77\n'),1)

    def test_cleanup_of_inactive_child_on_each_return(self):
        for flag in (0,1):
            source=f'''async fn hold(junk:->Int){{print(*junk);}}
            async fn choose(f:Int,a:&mut Int,b:&mut Int,mut junk:->Int)->&mut Int{{
              let inactive=hold(->junk);
              return if f==1 {{yield;a}} else {{yield;b}};
            }}
            fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
              let mut garbage=pool<Int>(1);let junk=garbage.new(77);
              let h=runtime::spawn(->choose({flag},&mut a,&mut b,->junk));
              match h.join(){{Ok(r)=>{{let reused=garbage.new(88);print(reused);*r=42;}},Err(_)=>{{print(999);}}}}
              print(a);print(b);
            }}'''
            with self.subTest(flag=flag):
                run=self.run_native(source)
                self.assertEqual(run.stdout,'88\n'+('42\n20\n' if flag else '10\n42\n'))
                self.assertEqual(run.stderr.count('destroy junk=77\n'),1)
                self.assertLess(run.stderr.index('destroy junk=77'),run.stderr.index('destroy reused=88'))

    def test_independent_three_way_selection(self):
        rng=random.Random(2041)
        for flag in [0,1,2,*[rng.randrange(3) for _ in range(2)]]:
            source=f'''async fn pick(f:Int,a:&mut Int,b:&mut Int,c:&mut Int)->&mut Int{{
              return if f==0 {{yield;a}} else if f==1 {{yield;b}} else {{yield;c}};
            }}
            fn main(){{let mut p=pool<Int>(3);let mut a=p.new(11);let mut b=p.new(22);let mut c=p.new(33);
              let h=runtime::spawn(->pick({flag},&mut a,&mut b,&mut c));
              match h.join(){{Ok(r)=>{{*r=99;}},Err(_)=>{{print(999);}}}}
              print(a);print(b);print(c);
            }}'''
            expected=[11,22,33];expected[flag]=99
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source).stdout,''.join(f'{n}\n' for n in expected))

if __name__=='__main__':unittest.main()
