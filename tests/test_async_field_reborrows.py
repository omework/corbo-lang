"""Field paths, capability ancestry and last use inside suspended states."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncFieldReborrowTests(unittest.TestCase):
    run_c_oracle=native.NativeBlockTests.run_c_oracle
    run_native=native.NativeBlockTests.run_native

    @staticmethod
    def program(body, helpers='', *, shared=False):
        mode='&' if shared else '&mut'
        return f'''struct View{{left:Int,data:&mut Int,right:Int}}
          {helpers} async fn work(v:{mode} View)->Int{{{body}}}
          fn main(){{let mut memory=pool<Int>(1);let mut data=memory.new(7);
            let mut v=View{{left:2,data:&mut data,right:3}};
            let h=runtime::spawn(->work({mode} v));
            match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(99);}}}}
            print(v.left);print(v.right);print(data);}}'''

    def refused(self, source, pattern=None):
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__):
                if pattern:
                    with self.assertRaisesRegex(Error,pattern):check(source)
                else:
                    with self.assertRaises(Error):check(source)

    def test_recorded_field_reborrow(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-struct-field-reborrow.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'20\n20\n')

    def test_disjoint_fields_and_target_identity(self):
        body='''let a=&mut v.left;let target=&mut *v.data;let b=&mut v.right;
          yield;a.set(11);target.set(20);*b=13;return *a+*target+*b;'''
        self.assertEqual(self.run_native(self.program(body)).stdout,'44\n11\n13\n20\n')
        for conflict in ('print(v.left);','v.left=9;','let other=&mut v.left;print(*other);'):
            self.refused(self.program(body.replace('yield;',conflict+'yield;')),'emprunt actif')

    def test_same_field_and_whole_argument_blocked_until_last_use(self):
        body='let target=&mut *v.data;BEFORE yield;target.set(20);print(*target);AFTER return *v.data;'
        helpers='fn read(v:&View)->Int{return *v.data;}fn change(v:&mut View){v.right=4;}'
        for operation in ('print(*v.data);','print(read(v));','change(v);','let alias=&mut *v;print(alias.left);'):
            self.refused(self.program(body.replace('BEFORE',operation).replace('AFTER',''),helpers))
        self.assertEqual(self.run_native(self.program(body.replace('BEFORE','v.right=5;').replace('AFTER','change(v);'),helpers)).stdout,
                         '20\n20\n2\n4\n20\n')

    def test_shared_parent_supports_parallel_shared_reborrows(self):
        body='let a=&*v.data;let b=&*v.data;yield;return *a+*b;'
        self.assertEqual(self.run_native(self.program(body,shared=True)).stdout,'14\n2\n3\n7\n')
        self.refused(self.program(body.replace('&*v.data','&mut *v.data',1),shared=True),'mutable')

    def test_modes_levels_and_reference_binding(self):
        for body in ('let a=&mut v.data;return *a;', 'let a=&v.data;return *a;',
                     'let a=&mut *v.left;return *a;', 'let a=&v.left;a.set(9);return *a;',
                     'let a:&Int=&mut *v.data;return *a;'):
            self.refused(self.program(body))
        # A mutable reference grants target writes even when its binding is immutable (V4).
        body='let a=&mut *v.data;yield;a.set(9);*a=11;return *a;'
        self.assertEqual(self.run_native(self.program(body)).stdout,'11\n2\n3\n11\n')
        self.refused(self.program('let a=&mut *v.data;a=&mut v.left;return *a;'))

    def test_child_await_and_inactive_drop_keep_field_path(self):
        helpers='async fn leaf(x:&mut Int)->Int{yield;x.set(21);return *x;}'
        for argument in ('&mut *v.data','target'):
            body=('let target=&mut *v.data;' if argument=='target' else '')+f'''
              let child=leaf({argument});BEFORE v.right=9;yield;let n=child.await;
              return n+*v.data;'''
            self.assertEqual(self.run_native(self.program(body.replace('BEFORE',''),helpers)).stdout,'42\n2\n9\n21\n')
            self.refused(self.program(body.replace('BEFORE','print(*v.data);'),helpers),'emprunt actif')
        body='let child=leaf(&mut *v.data);drop(->child);return *v.data;'
        self.assertEqual(self.run_native(self.program(body,helpers)).stdout,'7\n2\n3\n7\n')

    def test_child_result_keeps_projected_field_reserved(self):
        helpers='async fn same(x:&mut Int)->&mut Int{yield;return x;}'
        body='let result=same(&mut *v.data).await;BEFORE v.left=4;yield;result.set(15);return *result;'
        self.assertEqual(self.run_native(self.program(body.replace('BEFORE',''),helpers)).stdout,'15\n4\n3\n15\n')
        self.refused(self.program(body.replace('BEFORE','print(*v.data);'),helpers),'emprunt actif')

    def test_alias_scope_and_ancestry_projection(self):
        body='''let target={let alias=&mut *v;&mut *alias.data};v.left=4;
          BEFORE yield;target.set(17);return *target;'''
        self.assertEqual(self.run_native(self.program(body.replace('BEFORE',''))).stdout,'17\n4\n3\n17\n')
        self.refused(self.program(body.replace('BEFORE','print(*v.data);')),'emprunt actif')
        helpers='async fn leaf(x:&mut Int)->Int{yield;x.set(17);return *x;}'
        local='let child={let mut local=7;let target=&mut local;let child=leaf(target);<-child};return child.await;'
        self.refused(self.program(local,helpers),'non durable')
        body='''let child={let alias=&mut *v;let target=&mut *alias.data;
          let child=leaf(target);<-child};v.right=4;BEFORE return child.await;'''
        self.assertEqual(self.run_native(self.program(body.replace('BEFORE',''),helpers)).stdout,'17\n2\n4\n17\n')
        self.refused(self.program(body.replace('BEFORE','print(*v.data);'),helpers),'emprunt actif')

    def test_helper_and_method_projected_results(self):
        helpers='''fn target(v:&mut View)->&mut Int{return &mut *v.data;}
          fn side(v:&mut View)->&mut Int{return &mut v.left;}
          impl View{fn target(self:&mut View)->&mut Int{return &mut *self.data;}}'''
        for call in ('target(v)','v.target()'):
            body=f'let t={call};v.right=6;BEFORE yield;t.set(13);return *t;'
            self.assertEqual(self.run_native(self.program(body.replace('BEFORE',''),helpers)).stdout,'13\n2\n6\n13\n')
            self.refused(self.program(body.replace('BEFORE','print(*v.data);'),helpers),'emprunt actif')
        body='let left=side(v);yield;v.right=4;left.set(5);return v.right+*left;'
        self.assertEqual(self.run_native(self.program(body,helpers)).stdout,'9\n5\n4\n7\n')
        helpers+='async fn leaf(x:&mut Int)->Int{yield;x.set(23);return *x;}'
        for argument in ('target(v)','v.target()'):
            body=f'let child=leaf({argument});v.left=4;BEFORE return child.await;'
            self.assertEqual(self.run_native(self.program(body.replace('BEFORE',''),helpers)).stdout,'23\n4\n3\n23\n')
            self.refused(self.program(body.replace('BEFORE','print(*v.data);'),helpers),'emprunt actif')

    def test_conditional_results_union_fields_and_nested_paths(self):
        helpers='fn choose(v:&mut View,flag:Int)->&mut Int{if flag==1{return &mut v.left;}return &mut v.right;}'
        for flag in (0,1):
            body=f'let r=choose(v,{flag});BEFORE yield;r.set(19);return *r;'
            self.assertEqual(self.run_native(self.program(body.replace('BEFORE',''),helpers)).stdout,
                             '19\n'+('19\n3\n' if flag else '2\n19\n')+'7\n')
            for field in ('left','right'):
                self.refused(self.program(body.replace('BEFORE',f'v.{field}=9;'),helpers),'emprunt actif')
        source='''struct Point{x:Int,y:Int}struct Pair{left:Point,right:Point}
          async fn work(p:&mut Pair)->Int{let a=&mut p.left.x;let b=&mut p.right.x;
            yield;a.set(7);b.set(9);return *a+*b;}
          fn main(){let mut p=Pair{};let h=runtime::spawn(->work(&mut p));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(p.left.x);print(p.right.x);}'''
        self.assertEqual(self.run_native(source).stdout,'16\n7\n9\n')

    def test_native_block_and_prepared_arguments(self):
        helpers='fn write(n:&mut Int,k:Int){*n=k;}fn read(v:&View)->Int{return *v.data;}'
        body='write(&mut *v.data,read(v));return 0;'
        self.refused(self.program(body,helpers),'emprunt actif')
        source=self.program('return 0;').replace('let h=runtime::spawn(->work(&mut v));',
          'let view=&mut v;let h=runtime::thread({->(view);let r=&mut *view.data;*r=27;return *r;});')
        self.assertEqual(self.run_native(source).stdout,'27\n2\n3\n27\n')

    def test_loop_and_branch_reborrow_lifetimes(self):
        body='''let mut n=0;while n<2{let r=&mut *v.data;yield;r.set(10+n);
          n=n+1;continue;}let result=if true{let r=&mut v.left;yield;r}else{&mut v.right};
          yield;result.set(8);return *v.data+*result;'''
        self.assertEqual(self.run_native(self.program(body)).stdout,'19\n8\n3\n11\n')


if __name__=='__main__':unittest.main()
