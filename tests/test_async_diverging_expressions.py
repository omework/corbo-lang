"""S5/S5a: expressions without a continuation do not produce receivers."""
from pathlib import Path
import unittest
from crust import Error, verify_program
import test_async_loop_references as loops

class AsyncDivergingExpressionTests(unittest.TestCase):
    run_native=loops.AsyncLoopReferenceTests.run_native
    reject_blocking=loops.AsyncLoopReferenceTests.reject_blocking
    rejecting_callback=loops.AsyncLoopReferenceTests.rejecting_callback
    program=staticmethod(loops.AsyncLoopReferenceTests.program)

    def test_recorded_diverging_initializer(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-diverging-initializer.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'42\n20\n77\n')

    def test_unreachable_return_does_not_add_a_source(self):
        source=(Path(__file__).resolve().parents[1]/'validation/async-diverging-dead-source.crb').read_text()
        initializer='let unused=if flag==1 {return a;}else{return b;};'
        variants=(source,
                  source.replace(initializer,'let unused={'+initializer+'print(999);7};'),
                  source.replace(initializer,'let unused=loop{if flag==1{return a;}return b;};'))
        for index,variant in enumerate(variants):
            with self.subTest(variant=index):
                try:
                    run=self.run_native(variant)
                except Error as e:
                    self.fail(f'valid program rejected: {e}')
                self.assertEqual(run.stdout,'42\n20\n50\n')
            for target in ('a','b'):
                with self.subTest(variant=index,target=target),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(variant.replace('c=50;',f'{target}=50;'))

    def test_all_breaks_from_initializer_assignment_and_print(self):
        expression='if flag==1 {yield;break &mut *a;} else {yield;break &mut *b;}'
        forms=('let unused=EXPR;', 'let mut n=0;n=EXPR;', 'print(EXPR);',
               'let unused={let inner=EXPR; print(999); 7};')
        for form in forms:
            body='let mut r=loop{'+form.replace('EXPR',expression)+'print(998);};yield;return r;'
            for flag in (0,1):
                with self.subTest(form=form,flag=flag):
                    self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                        ('42\n20\n' if flag else '10\n42\n')+'77\n')
            for name in ('a','b'):
                with self.subTest(form=form,target=name),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.program(body).replace('*r=42;',f'{name}=3;*r=42;'))

    def test_return_expressions_and_dead_receiver(self):
        for body in (
            'let unused=if flag==1{yield;return a;}else{yield;return b;};print(999);',
            'return loop{if flag==1{yield;return a;}yield;return b;};',
            'let unused=loop{if flag==1{yield;return a;}yield;return b;};print(999);',
            'let unused=if flag==1{{yield;return a;}}else{{yield;return b;}};print(999);',
        ):
            for flag in (0,1):
                with self.subTest(body=body,flag=flag):
                    self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                        ('42\n20\n' if flag else '10\n42\n')+'77\n')
            for name in ('a','b'):
                with self.subTest(body=body,target=name),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.program(body).replace('*r=42;',f'{name}=3;*r=42;'))

    def test_continue_and_break_paths_with_independent_iteration_model(self):
        for limit in (1,2,4):
            source=f'''async fn count()->Int{{let mut i=0;
              let result=loop{{i=i+1;
                let unused=if i<{limit}{{yield;continue;}}else{{yield;break i;}};
                print(999);
              }};yield;return result;
            }}
            fn main(){{let h=runtime::spawn(->count());match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(998);}}}}}}'''
            # Independent arithmetic expectation: exactly `limit` increments.
            self.assertEqual(self.run_native(source).stdout,f'{limit}\n')

    def test_short_circuit_keeps_the_continuing_path(self):
        for operator in ('&&','||'):
            body=f'''let gate=flag==1 {operator} (if flag==1{{yield;return a;}}else{{yield;return a;}});
              if gate{{print(7);}}return b;'''
            for flag in (0,1):
                with self.subTest(operator=operator,flag=flag):
                    reaches_a=bool(flag) if operator=='&&' else not bool(flag)
                    prefix='7\n' if operator=='||' and flag else ''
                    self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                        prefix+('42\n20\n' if reaches_a else '10\n42\n')+'77\n')
            for target in ('a','b'):
                with self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.program(body).replace('*r=42;',f'{target}=3;*r=42;'))

    def test_match_all_exits_and_failed_launch(self):
        source='''async fn read(a:&mut Int)->&mut Int{yield;return a;}
          async fn pick(a:&mut Int,b:&mut Int)->&mut Int{
            let mut r=loop{let h=runtime::spawn_blocking(->read(a));
              let unused=match h.await{Ok(r)=>{yield;break &mut *r;},Err(_)=>{yield;break &mut *b;}};
              print(999);
            };yield;return r;
          }
          fn main(){let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
            let h=runtime::spawn(->pick(&mut a,&mut b));
            match h.join(){Ok(r)=>{*r=42;},Err(_)=>{print(998);}}
            print(a);print(b);
          }'''
        for failed in (False,True):
            self.assertEqual(self.run_native(source,reject=failed).stdout,'10\n42\n' if failed else '42\n20\n')
        for target in ('a','b'):
            with self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(source.replace('*r=42;',f'{target}=3;*r=42;'))

    def test_owned_child_cleaned_once_on_break_or_return(self):
        for exit_op in ('break','return'):
            for flag in (0,1):
                source=f'''async fn hold(junk:->Int){{print(*junk);}}
                async fn pick(f:Int,a:&mut Int,b:&mut Int,junk:->Int)->&mut Int{{
                  let inactive=hold(->junk);
                  let mut r=loop{{let unused=if f==1{{yield;{exit_op} &mut *a;}}else{{yield;{exit_op} &mut *b;}};print(999);}};
                  yield;return r;
                }}
                fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
                  let mut garbage=pool<Int>(1);let junk=garbage.new(77);
                  let h=runtime::spawn(->pick({flag},&mut a,&mut b,->junk));
                  match h.join(){{Ok(r)=>{{let reused=garbage.new(88);print(reused);*r=42;}},Err(_)=>{{print(998);}}}}
                  print(a);print(b);
                }}'''
                with self.subTest(exit_op=exit_op,flag=flag):
                    run=self.run_native(source)
                    self.assertEqual(run.stdout,'88\n'+('42\n20\n' if flag else '10\n42\n'))
                    self.assertEqual(run.stderr.count('destroy junk=77\n'),1)
                    self.assertLess(run.stderr.index('destroy junk=77'),run.stderr.index('destroy reused=88'))

    def test_prepared_owner_cleanup_on_aborted_or_completed_call(self):
        original=(Path(__file__).resolve().parents[1]/'validation/async-diverging-prepared-owner.crb').read_text()
        for partial in (False,True):
            source=original.replace('else{yield;return a;}','else{7}') if partial else original
            for flag in (0,1):
                with self.subTest(partial=partial,flag=flag):
                    run=self.run_native(source.replace('pick(1,','pick('+str(flag)+','))
                    expected=('77\n7\n' if partial and not flag else '')+'88\n42\n'
                    self.assertEqual(run.stdout,expected)
                    self.assertEqual(run.stderr.count('destroy junk=77\n'),1)
                    self.assertLess(run.stderr.index('destroy junk=77'),run.stderr.index('destroy reused=88'))
        with self.assertRaisesRegex(Error,'consomm|drop|transfert'):
            verify_program(original.replace('if flag==1{yield;return a;}else{yield;return a;}','*junk'))

    def test_prepared_owner_break_depth(self):
        source=(Path(__file__).resolve().parents[1]/'validation/async-diverging-prepared-owner.crb').read_text()
        start=source.index(' let inactive=')
        end=source.index('\n}',start)
        bodies=(
            ('let mut r=loop{let inactive=hold(->junk,if flag==1{yield;break &mut *a;}else{yield;break &mut *a;});inactive.await;break &mut *a;};return r;', '88\n42\n'),
            ('let inactive=hold(->junk,loop{yield;break 7;});inactive.await;return a;', '77\n7\n88\n42\n'),
        )
        for body,expected in bodies:
            with self.subTest(body=body):
                run=self.run_native(source[:start]+body+source[end:])
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy junk=77\n'),1)

    def test_prepared_owned_result_cleanup(self):
        source='''async fn give(junk:->Int)-><-Int{print(*junk);yield;return <-junk;}
          async fn hold(r:->Result<A<Int>,runtime::Error>,n:Int){drop(->r);print(n);}
          async fn pick(a:&mut Int,junk:->Int)->&mut Int{
            let h=runtime::spawn_blocking(->give(->junk));let r=h.await;
            let unused=hold(->r,{yield;return a;});unused.await;return a;
          }
          fn main(){let mut p=pool<Int>(1);let mut a=p.new(10);
            let mut garbage=pool<Int>(1);let junk=garbage.new(77);
            let h=runtime::spawn(->pick(&mut a,->junk));
            match h.join(){Ok(r)=>{let reused=garbage.new(88);print(reused);*r=42;},Err(_)=>{print(999);}}
            print(a);
          }'''
        for failed in (False,True):
            with self.subTest(failed=failed):
                run=self.run_native(source,reject=failed)
                self.assertEqual(run.stdout,('' if failed else '77\n')+'88\n42\n')
                self.assertEqual(run.stderr.count('destroy junk=77\n'),1)
        run=self.run_native(source.replace('hold(->r,{yield;return a;})','hold(->r,{yield;7})'))
        self.assertEqual(run.stdout,'77\n7\n88\n42\n')
        self.assertEqual(run.stderr.count('destroy junk=77\n'),1)

    def test_lifetime_modes_and_partial_continuation_still_checked(self):
        forms=(
            'if flag==1{break &*a;}else{break &mut *b;}',
            'if flag==1{let mut local=[1];break &mut local[0];}else{break &mut *b;}',
            'if flag==1{break;}else{break &mut *b;}',
            'if flag==1{print(7);}else{break &mut *b;}',
        )
        for form in forms:
            with self.subTest(form=form),self.assertRaises(Error):
                verify_program(self.program(f'let mut r=loop{{let unused={form};}};return r;'))

if __name__=='__main__':unittest.main()
