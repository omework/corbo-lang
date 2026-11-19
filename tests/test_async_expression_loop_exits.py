"""S5/S5a: noncontinuing expression arms exit their enclosing async loop."""
from pathlib import Path
import unittest
from crust import Error, verify_program
import test_async_loop_references as loop_tests


class AsyncExpressionLoopExitTests(unittest.TestCase):
    run_native = loop_tests.AsyncLoopReferenceTests.run_native
    reject_blocking = loop_tests.AsyncLoopReferenceTests.reject_blocking
    rejecting_callback = loop_tests.AsyncLoopReferenceTests.rejecting_callback
    program = staticmethod(loop_tests.AsyncLoopReferenceTests.program)

    def test_recorded_initializer_and_provenance(self):
        root=Path(__file__).resolve().parents[1]/'validation'
        self.assertEqual(self.run_native((root/'open-async-loop-break-in-initializer.crb').read_text()).stdout,
                         '42\n20\n77\n')
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program((root/'async-loop-nested-expression-provenance.crb').read_text())

    def test_nested_if_block_match_and_both_targets(self):
        forms=(
            'if flag==1 {yield;break &mut *a;} else {7}',
            '{if flag==1 {let mut local=&mut *a;yield;break &mut *local;} 7}',
            'if flag==1 {if flag==1 {yield;break &mut *a;} else {break &mut *b;}} else {7}',
            'match u8::try_from(flag-1) {Ok(n)=>{print(n as Int);yield;break &mut *a;},Err(_)=>{7}}',
        )
        for index,form in enumerate(forms):
            body=f'let mut r=loop{{let marker={form};print(marker);yield;break &mut *b;}};yield;return r;'
            for flag in (0,1):
                with self.subTest(form=index,flag=flag):
                    prefix='0\n' if index==3 and flag else '' if flag else '7\n'
                    expected=prefix+('42\n20\n' if flag else '10\n42\n')+'77\n'
                    self.assertEqual(self.run_native(self.program(body,flag)).stdout,expected)
            for target in ('a','b'):
                with self.subTest(form=index,target=target),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.program(body).replace('*r=42;',f'{target}=3;*r=42;'))

    def test_continue_in_initializer_and_assignment(self):
        for assignment in (False,True):
            setup='let mut marker=0;' if assignment else ''
            receiver='marker' if assignment else 'let marker'
            body=f'''let mut i=0;{setup}let mut r=loop{{i=i+1;
                {receiver}=if i<3 {{yield;continue;}} else {{7}};
                print(marker);print(i);if flag==1 {{break &mut *a;}}break &mut *b;
            }};yield;return r;'''
            for flag in (0,1):
                with self.subTest(assignment=assignment,flag=flag):
                    self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                        '7\n3\n'+('42\n20\n' if flag else '10\n42\n')+'77\n')

    def test_nested_loop_keeps_its_own_break(self):
        body='''let mut r=loop{
          let marker=if flag==1 {let mut inner=loop{yield;break &mut *b;};inner.set(21);break &mut *a;} else {7};
          print(marker);break &mut *a;
        };yield;return r;'''
        for flag in (0,1):
            source=self.program(body,flag).replace('*r=42;','b=50;*r=42;')
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source).stdout,('' if flag else '7\n')+'42\n50\n77\n')

    def test_break_in_break_operand_and_return_operand(self):
        for exit_op in ('break','return'):
            body=f'''let mut r=loop{{
              {exit_op} if flag==1 {{yield;break &mut *a;}} else {{yield;&mut *b}};
            }};yield;return r;'''
            for flag in (0,1):
                with self.subTest(exit_op=exit_op,flag=flag):
                    self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                                     ('42\n20\n' if flag else '10\n42\n')+'77\n')
            for target in ('a','b'):
                with self.subTest(exit_op=exit_op,target=target),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.program(body).replace('*r=42;',f'{target}=3;*r=42;'))

    def test_break_from_awaited_match_preserves_payload_source(self):
        source='''async fn read(a:&mut Int)->&mut Int{yield;return a;}
          async fn pick(a:&mut Int,b:&mut Int)->&mut Int{
            let mut r=loop{let h=runtime::spawn_blocking(->read(a));
              let marker=match h.await {Ok(r)=>{yield;break &mut *r;},Err(_)=>{7}};
              print(marker);break &mut *b;
            };yield;return r;
          }
          fn main(){let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
            let h=runtime::spawn(->pick(&mut a,&mut b));
            match h.join(){Ok(r)=>{*r=42;},Err(_)=>{print(999);}}
            print(a);print(b);
          }'''
        for failed in (False,True):
            with self.subTest(failed=failed):
                self.assertEqual(self.run_native(source,reject=failed).stdout,
                                 '7\n10\n42\n' if failed else '42\n20\n')
        for target in ('a','b'):
            with self.subTest(target=target),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(source.replace('*r=42;',f'{target}=3;*r=42;'))

    def test_break_cleans_expression_child_and_scope_before_slot_reuse(self):
        for flag in (0,1):
            source=f'''async fn hold(junk:->Int){{print(*junk);}}
            async fn pick(f:Int,a:&mut Int,b:&mut Int,junk:->Int)->&mut Int{{
              let mut result=loop{{
                let marker=if f==1 {{let inactive=hold(->junk);yield;break &mut *a;}} else {{7}};
                print(marker);let inactive=hold(->junk);yield;break &mut *b;
              }};yield;return result;
            }}
            fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
              let mut garbage=pool<Int>(1);let junk=garbage.new(77);
              let h=runtime::spawn(->pick({flag},&mut a,&mut b,->junk));
              match h.join(){{Ok(r)=>{{let reused=garbage.new(88);print(reused);*r=42;}},Err(_)=>{{print(999);}}}}
              print(a);print(b);
            }}'''
            run=self.run_native(source)
            self.assertEqual(run.stdout,('' if flag else '7\n')+'88\n'+('42\n20\n' if flag else '10\n42\n'))
            self.assertEqual(run.stderr.count('destroy junk=77\n'),1)
            self.assertLess(run.stderr.index('destroy junk=77'),run.stderr.index('destroy reused=88'))

    def test_reject_bad_exit_and_missing_continuing_result(self):
        forms=(
            'if flag==1 {break &*a;} else {7}',
            'if flag==1 {break 7;} else {7}',
            'if flag==1 {break;} else {7}',
            'if flag==1 {let mut local=[1];break &mut local[0];} else {7}',
            'if flag==1 {print(1);} else {7}',
        )
        for form in forms:
            with self.subTest(form=form),self.assertRaises(Error):
                verify_program(self.program(f'let mut r=loop{{let marker={form};print(marker);break &mut *b;}};return r;'))
        # A continue must not silently revive a child consumed on the previous pass.
        source='''async fn child(a:&Int){yield;print(*a);}
          async fn bad(a:&Int){let t=child(a);loop{let n=if 1==1 {t.await;continue;} else {7};print(n);break;}}
          fn main(){let mut p=pool<Int>(1);let a=p.new(10);let h=runtime::spawn(->bad(&a));drop(->h.join());}'''
        with self.assertRaisesRegex(Error,'continue doit préserver'):
            verify_program(source)

if __name__=='__main__':unittest.main()
