"""References selected by builtin matches in an async frame."""
from pathlib import Path
import unittest
from crust import Error, verify_program
import test_async_vector_results as native

class AsyncMatchReferenceTests(unittest.TestCase):
    run_native=native.AsyncVectorResultTests.run_native
    reject_blocking=native.AsyncVectorResultTests.reject_blocking
    rejecting_callback=native.AsyncVectorResultTests.rejecting_callback

    @staticmethod
    def program(mode='mut',stored=False,reverse=False,direct_return=False,task_binding=False):
        ref='&mut Int' if mode=='mut' else '&Int'
        arg='&mut' if mode=='mut' else '&'
        start=('let task=identity(a);let h=runtime::spawn_blocking(->task);' if task_binding
               else 'let h=runtime::spawn_blocking(->identity(a));')
        subject='h.await'
        if stored:start+='let outcome=h.await;';subject='outcome'
        ok='Ok(value)=>{print(1);yield;value}'
        err='Err(_)=>{print(2);yield;b}'
        match='match '+subject+'{'+(','.join((err,ok) if reverse else (ok,err)))+'}'
        body='return '+match+';' if direct_return else 'let mut selected='+match+';yield;return selected;'
        effect='*r=42;' if mode=='mut' else 'print(*r);'
        return f'''async fn identity(a:{ref})->{ref}{{yield;print(7);return a;}}
        async fn choose(a:{ref},b:{ref})->{ref}{{{start}{body}}}
        fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
          let h=runtime::spawn(->choose({arg} a,{arg} b));
          match h.join(){{Ok(r)=>{{{effect}}},Err(_)=>{{print(999);}}}}
          print(a);print(b);drop(->a);drop(->b);let reused=p.new(77);print(reused);
        }}'''

    def test_recorded_case(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-local-reference-match.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'30\n20\n')

    def test_modes_branch_order_and_launch_failure(self):
        for mode in ('ref','mut'):
            for reverse in (False,True):
                for failed in (False,True):
                    expected='2\n' if failed else '7\n1\n'
                    expected+=('10\n42\n' if failed else '42\n20\n') if mode=='mut' else f'{20 if failed else 10}\n10\n20\n'
                    with self.subTest(mode=mode,reverse=reverse,failed=failed):
                        self.assertEqual(self.run_native(self.program(mode,reverse=reverse),reject=failed).stdout,expected+'77\n')

    def test_stored_result_task_binding_and_direct_return(self):
        for stored,direct,task in ((True,False,False),(False,True,False),(False,False,True)):
            for failed in (False,True):
                with self.subTest(stored=stored,direct=direct,task=task,failed=failed):
                    self.assertEqual(self.run_native(self.program(stored=stored,direct_return=direct,task_binding=task),reject=failed).stdout,
                                     '2\n10\n42\n77\n' if failed else '7\n1\n42\n20\n77\n')

    def test_every_source_reserved_after_return(self):
        source=self.program()
        for action in ('print(a);','print(b);','a=3;','b=3;','drop(->a);','drop(->b);'):
            with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt|réserv|utilisé'):
                verify_program(source.replace('*r=42;',action+'*r=42;'))

    def test_match_binding_keeps_ancestor_inside_frame(self):
        source=self.program().replace('yield;return selected;','yield;selected.set(23);return selected;')
        self.assertEqual(self.run_native(source).stdout,'7\n1\n42\n20\n77\n')
        for action in ('a.set(3);','b.set(3);','print(*a);','print(*b);'):
            with self.subTest(action=action),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(source.replace('selected.set(23);',action+'selected.set(23);'))

    def test_vector_byte_case_and_fallback(self):
        for element in ('Int','u8'):
            cast=' as Int' if element=='u8' else ''
            source=f'''async fn append(a:&mut Vector<{element}>)->&mut {element}{{yield;return a.push_new();}}
            async fn choose(a:&mut Vector<{element}>,b:&mut Vector<{element}>)->&mut {element}{{
              let h=runtime::spawn_blocking(->append(a));
              let mut selected=match h.await{{Ok(cell)=>{{yield;cell}},Err(_)=>{{b.push_new()}}}};
              yield;return selected;
            }}
            async fn work(a:&mut Vector<{element}>,b:&mut Vector<{element}>){{
              let mut r=choose(a,b).await;print(*r{cast});yield;r.set(255);print(a.len());print(b.len());
            }}
            fn main(){{let mut p=pool<Vector<{element}>>(2);let mut a=p.new();let mut b=p.new();
              let h=runtime::spawn(->work(&mut a,&mut b));drop(->h.join());}}'''
            for failed in (False,True):
                with self.subTest(element=element,failed=failed):
                    self.assertEqual(self.run_native(source,reject=failed).stdout,'0\n0\n1\n' if failed else '0\n1\n0\n')
            for target in ('a','b'):
                with self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(source.replace('yield;r.set(255);',f'{target}.push(7);yield;r.set(255);'))

    def test_scalar_result_selects_external_borrows(self):
        for value in (3,300):
            source=f'''async fn choose(a:&mut Int,b:&mut Int)->&mut Int{{
              let mut selected=match u8::try_from({value}) {{Ok(n)=>{{print(n as Int);yield;a}},Err(_)=>{{yield;b}}}};
              yield;return selected;
            }}
            fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
              let h=runtime::spawn(->choose(&mut a,&mut b));match h.join(){{Ok(r)=>{{*r=42;}},Err(_)=>{{print(999);}}}}
              print(a);print(b);
            }}'''
            self.assertEqual(self.run_native(source).stdout,'3\n42\n20\n' if value==3 else '10\n42\n')

    def test_nested_error_matches_and_vector_result(self):
        cases=(
          ('match IntegerConversionError::OutOfRange {IntegerConversionError::OutOfRange=>{yield;b}}','10\n42\n'),
          ('match runtime::Error::LaunchFailed {runtime::Error::LaunchFailed=>{yield;b}}','10\n42\n'),
          ('match u8::try_from(300) {Ok(n)=>{print(n as Int);a},Err(e)=>{match e {IntegerConversionError::OutOfRange=>{yield;b}}}}','10\n42\n'),
          ('match v.pop() {Some(n)=>{print(n);yield;a},None=>{b}}','9\n42\n20\n'),
        )
        for expression,expected in cases:
            source=f'''async fn choose(v:&mut Vector<Int>,a:&mut Int,b:&mut Int)->&mut Int{{
              let mut selected={expression};yield;return selected;
            }}
            fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
              let mut vectors=pool<Vector<Int>>(1);let mut v=vectors.new();v.push(9);
              let h=runtime::spawn(->choose(&mut v,&mut a,&mut b));
              let mut out=match h.join(){{Ok(r)=>{{r}},Err(_)=>{{&mut b}}}};
              drop(->v);out.set(42);print(a);print(b);
            }}'''
            with self.subTest(expression=expression):
                self.assertEqual(self.run_native(source).stdout,expected)

    def test_three_target_model(self):
        for failed in (False,True):
            for number in (3,300):
                source=f'''async fn identity(a:&mut Int)->&mut Int{{yield;return a;}}
                async fn choose(n:Int,a:&mut Int,b:&mut Int,c:&mut Int)->&mut Int{{
                  let h=runtime::spawn_blocking(->identity(a));
                  let mut out=match h.await{{Ok(r)=>{{r}},Err(_)=>{{match u8::try_from(n){{Ok(_)=>{{b}},Err(_)=>{{c}}}}}}}};
                  yield;return out;
                }}
                fn main(){{let mut p=pool<Int>(3);let mut a=p.new(11);let mut b=p.new(22);let mut c=p.new(33);
                  let h=runtime::spawn(->choose({number},&mut a,&mut b,&mut c));
                  match h.join(){{Ok(r)=>{{*r=99;}},Err(_)=>{{print(999);}}}}
                  print(a);print(b);print(c);
                }}'''
                chosen=0 if not failed else 1 if 0<=number<=255 else 2
                expected=[11,22,33];expected[chosen]=99
                with self.subTest(failed=failed,number=number):
                    self.assertEqual(self.run_native(source,reject=failed).stdout,''.join(f'{n}\n' for n in expected))
                    for target in ('a','b','c'):
                        with self.assertRaisesRegex(Error,'emprunt|réserv|utilisé'):
                            verify_program(source.replace('*r=99;',f'{target}=7;*r=99;'))

    def test_error_arm_returns_early_and_direct_spawn_subject(self):
        source=self.program().replace('Err(_)=>{print(2);yield;b}', 'Err(_)=>{print(2);yield;return b;}')
        for direct in (False,True):
            program=source
            if direct:
                program=program.replace('let h=runtime::spawn_blocking(->identity(a));','').replace('match h.await','match runtime::spawn_blocking(->identity(a)).await')
            for failed in (False,True):
                with self.subTest(direct=direct,failed=failed):
                    self.assertEqual(self.run_native(program,reject=failed).stdout,'2\n10\n42\n77\n' if failed else '7\n1\n42\n20\n77\n')

    def test_result_carrier_exclusive_until_last_use(self):
        source=(Path(__file__).resolve().parents[1]/'validation/async-match-overlapping-result-borrows.crb').read_text()
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(source)
        valid=source.replace(' let mut second=', ' first.set(4);let mut second=').replace(' first.set(4);return second;', ' return second;')
        self.assertEqual(self.run_native(valid).stdout,'9\n2\n3\n')
        shared=source.replace('&mut Int','&Int').replace('&mut a','&a').replace('&mut b','&b').replace('&mut c','&c')
        shared=shared.replace('first.set(4);','print(*first);').replace('*r=9;','print(*r);')
        self.assertEqual(self.run_native(shared).stdout,'1\n1\n1\n2\n3\n')

    def test_result_container_is_not_a_reference(self):
        source=self.program().replace('let mut selected=match h.await{Ok(value)=>{print(1);yield;value},Err(_)=>{print(2);yield;b}};yield;return selected;',
                                     'let outcome=h.await;return outcome;')
        with self.assertRaisesRegex(Error,'référence requise'):
            verify_program(source)

    def test_reject_modes_local_target_and_missing_arm(self):
        source=self.program()
        for changed in (
            source.replace('print(2);yield;b','print(2);yield;&*b'),
            source.replace('print(2);yield;b','let mut local=[1];&mut local[0]'),
            source.replace('print(2);yield;b','print(2);yield;'),
            source.replace(',Err(_)=>{print(2);yield;b}',''),
        ):
            with self.subTest(source=changed),self.assertRaises(Error):verify_program(changed)

if __name__=='__main__':unittest.main()
