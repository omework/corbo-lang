"""ST8/ST12 × AS12: field paths survive asynchronous result boundaries."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncFieldReturnTests(unittest.TestCase):
    run_c_oracle = native.NativeBlockTests.run_c_oracle
    run_native = native.NativeBlockTests.run_native

    def refused(self, source):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaises(Error):
                    check(source)

    @staticmethod
    def program(body, use='n.set(21);print(n);', helpers='', mode='mut'):
        ref = '&mut' if mode == 'mut' else '&'
        return f'''struct View{{left:Int,data:&mut Int,right:Int}}
          {helpers}
          async fn work(v:{ref} View)->{ref} Int{{{body}}}
          fn main(){{let mut memory=pool<Int>(1);let mut data=memory.new(7);
            let mut v=View{{left:2,data:&mut data,right:3}};
            let h=runtime::spawn(->work({ref} v));
            let result=h.join();
            match result{{Ok(n)=>{{{use}}},Err(_)=>{{print(99);}}}}
            print(v.left);print(v.right);print(data);}}'''

    def test_recorded_case(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-field-reference-return.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'21\n2\n3\n21\n')

    def test_direct_and_named_results_retain_only_the_field(self):
        for expr, expected in (('&mut v.left','21\n21\n9\n7\n'),
                               ('&mut *v.data','21\n2\n9\n21\n')):
            for body in (f'yield;return {expr};',f'let n={expr};yield;return n;'):
                with self.subTest(expr=expr,body=body):
                    source=self.program(body,use='v.right=9;n.set(21);print(n);')
                    self.assertEqual(self.run_native(source).stdout,expected)
                    for operation in ('print(v);','drop(->v);',
                                      'print(v.left);' if 'left' in expr else 'print(*v.data);'):
                        self.refused(source.replace('v.right=9;',operation))
                    self.refused(source.replace('let result=h.join();','print(v.right);let result=h.join();'))

    def test_mutable_field_target_and_carrier_remain_protected(self):
        source=self.program('yield;return &mut *v.data;')
        for op in ('print(data);','data=9;','drop(->data);','drop(->v);'):
            self.refused(source.replace('n.set(21);',op+'n.set(21);'))
        source=self.program('yield;return &mut *v.data;',use='n.set(21);print(n);v.right=8;print(*v.data);')
        self.assertEqual(self.run_native(source).stdout,'21\n21\n2\n8\n21\n')

    def test_shared_result_from_mutable_field(self):
        source=self.program('yield;return &*v.data;',use='print(n);print(v.right);',mode='ref')
        self.assertEqual(self.run_native(source).stdout,'7\n3\n2\n3\n7\n')
        self.refused(source.replace('print(n);','drop(->data);print(n);'))
        self.refused(source.replace('print(n);','n.set(9);print(n);'))

    def test_async_relays_and_synchronous_projected_helpers(self):
        helpers='''fn target(v:&mut View)->&mut Int{return &mut *v.data;}
          impl View{fn target(self:&mut View)->&mut Int{return &mut *self.data;}}
          async fn leaf(v:&mut View)->&mut Int{yield;return &mut *v.data;}
          async fn identity(v:&mut Int)->&mut Int{yield;return v;}'''
        for expr in ('leaf(v).await','identity(&mut *v.data).await','target(v)',
                     'identity(target(v)).await','v.target()','identity(v.target()).await'):
            body=f'let r={expr};v.right=9;yield;return r;'
            source=self.program(body,helpers=helpers)
            with self.subTest(expr=expr):
                self.assertEqual(self.run_native(source).stdout,'21\n2\n9\n21\n')
                self.refused(source.replace('v.right=9;','print(*v.data);v.right=9;'))
                self.refused(source.replace('n.set(21);','print(*v.data);n.set(21);'))

    def test_nested_fields_and_relayed_alias(self):
        source='''struct Pair{left:Int,right:Int}struct Outer{a:Pair,b:Pair}
          async fn leaf(v:&mut Outer)->&mut Int{yield;return &mut v.a.right;}
          async fn relay(v:&mut Outer)->&mut Int{let alias=&mut *v;let r=leaf(alias).await;
            v.b.left=8;yield;return r;}
          fn main(){let mut v=Outer{};v.a.left=1;v.a.right=2;v.b.left=3;v.b.right=4;
            let h=runtime::spawn(->relay(&mut v));match h.join(){Ok(r)=>{
              v.a.left=9;v.b.right=10;r.set(21);print(*r);},Err(_)=>{print(99);}}
            print(v.a.left);print(v.a.right);print(v.b.left);print(v.b.right);}'''
        self.assertEqual(self.run_native(source).stdout,'21\n9\n21\n8\n10\n')
        self.refused(source.replace('v.a.left=9;','print(v.a.right);v.a.left=9;'))
        self.refused(source.replace('v.b.left=8;','print(v.a.right);v.b.left=8;'))

    def test_shared_reborrow_keeps_mutable_ancestry(self):
        source=self.program('yield;return &*v.data;',use='print(n);',mode='ref')
        source=source.replace('work(v:& View)','work(v:&mut View)').replace('work(& v)','work(&mut v)')
        self.assertEqual(self.run_native(source).stdout,'7\n2\n3\n7\n')
        self.refused(source.replace('print(n);','print(*v.data);print(n);'))

    def test_historical_reset_cannot_invalidate_result(self):
        source=self.program('yield;return &mut *v.data;').replace('n.set(21);','memory.reset();n.set(21);')
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaises(Error):check(source,allow_legacy_reset=True)

    def test_spawned_child_result_and_error_branch(self):
        helpers='async fn leaf(v:&mut View)->&mut Int{yield;return &mut *v.data;}'
        body='''let h=runtime::spawn(->leaf(v));let result=h.await;
          return match result{Ok(n)=>{yield;n},Err(_)=>{&mut *v.data}};'''
        source=self.program(body,helpers=helpers)
        self.assertEqual(self.run_native(source).stdout,'21\n2\n3\n21\n')
        self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'21\n2\n3\n21\n')
        self.refused(source.replace('Ok(n)=>{yield;n}','Ok(n)=>{print(*v.data);yield;n}'))

    def test_pool_carrier_cleanup_and_slot_reuse(self):
        source=self.program('yield;return &mut *v.data;')
        source=source.replace('let mut v=View{left:2,data:&mut data,right:3};',
          'let mut views=pool<View>(1);let mut v=views.new(left:2,data:&mut data,right:3);')
        source=source.replace('print(v.left);print(v.right);print(data);',
          'print(v.left);print(v.right);drop(->v);print(data);let next=views.new(data:&mut data);print(*next.data);')
        self.assertEqual(self.run_native(source).stdout,'21\n2\n3\n21\n21\n')
        self.refused(source.replace('n.set(21);','drop(->v);n.set(21);'))
        self.refused(source.replace('n.set(21);','drop(->views);n.set(21);'))

    def test_joined_projection_recaptured_by_another_task(self):
        helpers='async fn touch(n:&mut Int)->Int{yield;n.set(27);return *n;}'
        use='''let child=runtime::spawn(->touch(n));
          BEFORE match child.join(){Ok(value)=>{print(value);},Err(_)=>{print(99);}}
          print(n);'''
        source=self.program('yield;return &mut *v.data;',use=use,helpers=helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','v.left=8;')).stdout,'27\n27\n8\n3\n27\n')
        for conflict in ('print(n);','print(*v.data);','drop(->data);','drop(->v);'):
            self.refused(source.replace('BEFORE',conflict))

    def test_synchronous_join_relay_preserves_path_and_ancestry(self):
        source=(Path(__file__).resolve().parents[1]/'validation/probe-sync-relay-async-field-return.crb').read_text()
        source=source.replace('fn main()',
            'fn relay(v:&mut View)->&mut Int{return get(v);}fn main()').replace('let r=get(&mut v);','let r=relay(&mut v);')
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n')
        for conflict in ('print(*v.data);','print(data);','drop(->v);','drop(->data);'):
            self.refused(source.replace('v.right=8;',conflict+'v.right=8;'))

    def test_conditional_union_and_alias_scope(self):
        for flag in (0,1):
            body=f'''let alias=&mut *v;let result=if {flag}==1 {{yield;&mut alias.left}}
              else {{yield;&mut *alias.data}};return result;'''
            source=self.program(body,use='v.right=9;n.set(21);print(n);')
            self.assertEqual(self.run_native(source).stdout,'21\n21\n9\n7\n' if flag else '21\n2\n9\n21\n')
            for field in ('v.left','*v.data'):
                self.refused(source.replace('v.right=9;',f'print({field});v.right=9;'))

    def test_invalid_local_sources_and_modes(self):
        for body in ('let mut x=1;yield;return &mut x;',
                     'let p=pool<Int>(1);let mut x=p.new(3);return &mut x;',
                     'yield;return &v.left;', 'yield;return &mut v.data;',
                     'yield;return &mut *v.left;'):
            self.refused(self.program(body))

    def test_launch_failure_cleans_capture_before_error(self):
        source=self.program('yield;return &mut *v.data;')
        self.assertEqual(self.run_native(source,fail_at=1).stdout,'99\n2\n3\n7\n')


if __name__=='__main__':unittest.main()
