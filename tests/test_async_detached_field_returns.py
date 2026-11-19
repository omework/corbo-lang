"""ST13: returned shared targets are independent of their former carrier."""
from pathlib import Path
import unittest
from crust import Error,verify_program,compile_source
import test_native_blocks as native


class AsyncDetachedFieldTests(unittest.TestCase):
    run_c_oracle=native.NativeBlockTests.run_c_oracle
    run_native=native.NativeBlockTests.run_native

    def refused(self,source,**options):
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaises(Error):check(source,**options)

    @staticmethod
    def program(body='yield;return v.data;',use='drop(->v);print(r);',helpers='',mutable=False):
        mode='&mut' if mutable else '&'
        return f'''struct View{{left:Int,data:&Int,right:Int}}
          {helpers} async fn work(v:{mode} View)->&Int{{{body}}}
          fn main(){{let mut memory=pool<Int>(1);let mut data=memory.new(7);
            let mut views=pool<View>(1);let mut v=views.new(left:2,data:&data,right:3);
            let h=runtime::spawn(->work({mode} v));
            let r=match h.join(){{Ok(n)=>{{n}},Err(_)=>{{&data}}}};
            {use} print(data);}}'''

    def test_recorded_case_with_explicit_scope_import(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-detached-field-return.crb').read_text()
        source=source.replace('drop(->v);','-> v;drop(->v);')
        self.assertEqual(self.run_native(source).stdout,'7\n7\n')

    def test_direct_named_and_explicit_shared_reborrow(self):
        for body in ('yield;return v.data;','let r=v.data;yield;return r;',
                     'yield;return &*v.data;'):
            for mutable in (False,True):
                with self.subTest(body=body,mutable=mutable):
                    run=self.run_native(self.program(body,mutable=mutable))
                    self.assertEqual(run.stdout,'7\n7\n')
                    self.assertEqual(run.stderr.splitlines(),
                                     ['destroy v=View','reclaim v','destroy data=7','reclaim data'])
                    self.refused(self.program(body,use='drop(->data);print(r);',mutable=mutable))
                    self.refused(self.program(body,use='drop(->v);data=8;print(r);',mutable=mutable))

    def test_carrier_pool_reuse_and_close(self):
        source='''struct View{left:Int,data:&Int}
          async fn work(v:&View)->&Int{yield;return v.data;}
          fn main(){let mut memory=pool<Int>(1);let mut data=memory.new(7);
            let r={let mut views=pool<View>(1);let v=views.new(data:&data);
              let h=runtime::spawn(->work(&v));
              let r=match h.join(){Ok(n)=>{n},Err(_)=>{&data}};
              drop(->v);let replacement=views.new(data:&data);print(replacement.left);
              drop(->replacement);&*r};print(r);print(data);}'''
        self.assertEqual(self.run_native(source).stdout,'0\n7\n7\n')
        self.refused(source.replace('};print(r);','};drop(->data);print(r);'))
        self.refused(self.program(use='drop(->v);memory.reset();print(r);'),allow_legacy_reset=True)
        source=self.program(use='drop(->v);views.reset();print(r);')
        self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n7\n')

    def test_target_released_only_after_last_use(self):
        use='drop(->v);print(r);data=21;print(data);drop(->data);let next=memory.new(77);print(next);'
        source=self.program(use=use).replace('print(next); print(data);','print(next);')
        self.assertEqual(self.run_native(source).stdout,'7\n21\n77\n')

    def test_detached_local_value_allows_mutable_carrier_call(self):
        helpers='fn change(v:&mut View){v.left=9;}'
        for body in ('let r=v.data;change(v);yield;print(v.left);return r;',
                     'let alias=&mut *v;let r=alias.data;change(v);yield;print(v.left);return r;'):
            self.assertEqual(self.run_native(self.program(body,helpers=helpers,mutable=True)).stdout,'9\n7\n7\n')

    def test_child_capture_and_return_detach(self):
        helpers='''async fn identity(n:&Int)->&Int{yield;return n;}
          fn change(v:&mut View){v.right=12;}'''
        for body in ('let r=identity(v.data).await;change(v);yield;return r;',
                     'let child=identity(v.data);change(v);yield;return child.await;'):
            self.assertEqual(self.run_native(self.program(body,helpers=helpers,mutable=True)).stdout,'7\n7\n')

    def test_sync_helpers_methods_and_reverse_relay(self):
        helpers='''fn target(v:&View)->&Int{return v.data;}
          impl View{fn target(self:&View)->&Int{return self.data;}}
          fn change(v:&mut View){v.left=8;}'''
        for call in ('target(v)','v.target()'):
            body=f'let r={call};change(v);yield;return r;'
            self.assertEqual(self.run_native(self.program(body,helpers=helpers,mutable=True)).stdout,'7\n7\n')
        source=self.program(helpers=helpers)
        source=source.replace('let h=runtime::spawn(->work(& v));\n            let r=match h.join(){Ok(n)=>{n},Err(_)=>{&data}};',
          'let r=get(&v);')
        source+='''fn get(v:&View)->&Int{let h=runtime::spawn(->work(v));
          return match h.join(){Ok(n)=>{n},Err(_)=>{v.data}};}'''
        self.assertEqual(self.run_native(source).stdout,'7\n7\n')
        self.refused(source.replace('drop(->v);print(r);','drop(->v);drop(->data);print(r);'))

    def test_shared_result_keeps_external_mutable_ancestor(self):
        source=self.program().replace('let mut views=','let parent=&mut data;let mut views=')
        source=source.replace('data:&data,right:3','data:&*parent,right:3').replace('Err(_)=>{&data}','Err(_)=>{&*parent}')
        self.assertEqual(self.run_native(source).stdout,'7\n7\n')
        self.refused(source.replace('drop(->v);print(r);','drop(->v);parent.set(8);print(r);'))
        source=source.replace('Err(_)=>{&*parent}', 'Err(_)=>{return;}')
        self.assertEqual(self.run_native(source).stdout,'7\n7\n')
        self.refused(source.replace('drop(->v);print(r);','drop(->v);parent.set(8);print(r);'))

    def test_mutable_fields_do_not_detach_or_copy(self):
        source=self.program().replace('data:&Int','data:&mut Int').replace('data:&data','data:&mut data')
        self.refused(source)
        source=source.replace('return v.data;','return &*v.data;')
        self.refused(source)
        self.assertEqual(self.run_native(source.replace('drop(->v);print(r);','print(r);')).stdout,'7\n7\n')

    def test_mixed_direct_and_detached_results_preserve_both_dependencies(self):
        for flag in (False,True):
            body=f'yield;return if {str(flag).lower()} {{v.data}} else {{&v.left}};'
            source=self.program(body,use='print(r);')
            self.assertEqual(self.run_native(source).stdout,'7\n7\n' if flag else '2\n7\n')
            self.refused(self.program(body))
            self.refused(self.program(body,use='drop(->data);print(r);'))

    def test_launch_failure_still_releases_capture(self):
        self.assertEqual(self.run_native(self.program(),fail_at=1).stdout,'7\n7\n')

    def test_block_reference_keeps_target_and_mutable_capability(self):
        for tail in ('&data', 'let view=&data;view', 'let view=&data;&*view'):
            source=f'''fn main(){{let mut memory=pool<Int>(1);let mut data=memory.new(7);
              let r={{{tail}}};print(r);data=8;print(data);}}'''
            self.assertEqual(self.run_native(source).stdout,'7\n8\n')
            self.refused(source.replace('};print(r);','};drop(->data);print(r);'))
            self.refused(source.replace('};print(r);','};data=9;print(r);'))
        source='''fn main(){let mut memory=pool<Int>(1);let mut data=memory.new(7);
          let parent=&mut data;let mut r={&mut *parent};r.set(8);print(r);parent.set(9);print(data);}'''
        self.assertEqual(self.run_native(source).stdout,'8\n9\n')
        self.refused(source.replace('r.set(8);','parent.set(9);r.set(8);'))
        for tail in ('&data','&mut data'):
            self.refused(f'''fn main(){{let r={{let mut memory=pool<Int>(1);
              let mut data=memory.new(7);{tail}}};print(r);}}''')


if __name__=='__main__':unittest.main()
