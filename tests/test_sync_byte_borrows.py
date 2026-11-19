"""Shared byte contracts across async/native calls, with actual C execution."""
import unittest
from unittest.mock import patch
from crust import Compiler, Error, verify_program
import test_sync_borrow_calls as borrowed

class SyncByteBorrowTests(unittest.TestCase):
    run_c_oracle = borrowed.SyncBorrowCallTests.run_c_oracle
    run_native = borrowed.SyncBorrowCallTests.run_native
    wrap = staticmethod(borrowed.SyncBorrowCallTests.wrap)
    declarations = '''fn read(v:&u8)->u8{return *v;}
      fn same(v:&u8)->&u8{return v;}
      fn relay(v:&u8)->&u8{return same(v);}
      fn choose(a:&u8,b:&u8,n:Int)->&u8{if n==0{return a;}return b;}
      fn first(a:&u8,b:&u8)->&u8{return a;}'''

    def test_literal_array_and_nested_calls(self):
        body='''let mut bytes:[u8;2]=[7,8];let r:&u8=relay(&bytes[0]);
          yield;let n=read(r);bytes[0]=9;let c=read(same(&"A"[0]));return (n as Int)+(c as Int);'''
        for native in (False,True):
            self.assertEqual(self.run_native(self.wrap(body.replace('yield;','') if native else body,self.declarations,native)).stdout,'72\n')
        for old,new in [('yield;','bytes[0]=2;yield;'),('yield;','drop(->bytes);yield;'),
                        ('read(r)','read(&r)'),('read(r)','read(&mut bytes[0])'),
                        ('[u8;2]','[Int;2]')]:
            with self.subTest(new=new),self.assertRaises(Error):
                verify_program(self.wrap(body.replace(old,new),self.declarations))
        with patch.object(Compiler,'emit_async_sync_bridge',side_effect=AssertionError('backend during check')):
            verify_program(self.wrap(body,self.declarations))

    def test_conditional_result_and_unreturned_argument(self):
        for flag,expected in [(0,'7\n'),(1,'8\n')]:
            body=f'''let mut a:[u8;1]=[7];let mut b:[u8;1]=[8];
              let r=choose(&a[0],&b[0],{flag});BEFORE yield;return *r as Int;'''
            self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE',''),self.declarations)).stdout,expected)
            for conflict in ('a[0]=1;','b[0]=1;','drop(->a);','drop(->b);'):
                with self.subTest(flag=flag,conflict=conflict),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.wrap(body.replace('BEFORE',conflict),self.declarations))
        body='''let mut a:[u8;1]=[7];let mut b:[u8;1]=[8];
          let r=first(&a[0],&b[0]);b[0]=9;let n=*r;drop(->a);return (n as Int)+(b[0] as Int);'''
        self.assertEqual(self.run_native(self.wrap(body,self.declarations)).stdout,'16\n')

    def test_direct_byte_place_drop_and_future_loop_use(self):
        body='''let mut a:u8=7;let r=relay(&a);BEFORE yield;
          let n=*r;drop(->a);AFTER return n as Int;'''
        self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE','').replace('AFTER',''),self.declarations)).stdout,'7\n')
        for conflict in ('a=8;','drop(->a);'):
            with self.subTest(conflict=conflict),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(self.wrap(body.replace('BEFORE',conflict).replace('AFTER',''),self.declarations))
        with self.assertRaisesRegex(Error,'plus utilisable'):
            verify_program(self.wrap(body.replace('BEFORE','').replace('AFTER','print(a as Int);'),self.declarations))
        with self.assertRaisesRegex(Error,'non durable'):
            verify_program(self.declarations+'async fn bad()->&u8{let a:u8=7;return same(&a);}')
        loop='''let mut a:u8=7;let r=same(&a);let mut i=0;
          while i<2{print(read(r) as Int);a=8;i=i+1;}return 0;'''
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(self.wrap(loop,self.declarations))

    def test_prepared_source_through_suspended_argument_and_early_return(self):
        declarations=self.declarations+'''fn later(a:&u8,b:Int)->Int{print(b);return *a as Int;}
          async fn delay()->Int{yield;return 9;}'''
        body='let mut a:[u8;1]=[7];return later(same(&a[0]),delay().await);'
        self.assertEqual(self.run_native(self.wrap(body,declarations)).stdout,'9\n7\n')
        for argument in ('{a[0]=1;9}','{yield;a[0]=1;9}'):
            with self.subTest(argument=argument),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(self.wrap(body.replace('delay().await',argument),declarations))
        body=body.replace('delay().await','{yield;return 42;}')
        self.assertEqual(self.run_native(self.wrap(body,declarations)).stdout,'42\n')

    def test_last_use_before_mutable_argument(self):
        declarations=self.declarations+'fn write_after(n:u8,b:&mut u8){*b=n;}'
        body='''let mut a:[u8;1]=[7];let r=same(&a[0]);
          write_after(read(r),&mut a[0]);AFTER return a[0] as Int;'''
        self.assertEqual(self.run_native(self.wrap(body.replace('AFTER',''),declarations)).stdout,'7\n')
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(self.wrap(body.replace('AFTER','print(*r as Int);'),declarations))

    def test_child_capture_return_and_local_escape(self):
        declarations=self.declarations+'''async fn child(v:&u8)->&u8{yield;return relay(v);}
          async fn outer(v:&u8)->&u8{return child(same(v)).await;}'''
        body='''let mut a:[u8;1]=[7];let task=child(same(&a[0]));BEFORE
          let r=task.await;DURING let n=read(r);a[0]=9;return n as Int;'''
        self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE','').replace('DURING',''),declarations)).stdout,'7\n')
        for position in ('BEFORE','DURING'):
            for conflict in ('a[0]=1;','drop(->a);'):
                with self.subTest(position=position,conflict=conflict),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.wrap(body.replace(position,conflict).replace('BEFORE','').replace('DURING',''),declarations))
        for bad in ('async fn bad()->&u8{let a:[u8;1]=[7];return same(&a[0]);}',
                    'async fn bad()->&u8{let a:[u8;1]=[7];return child(same(&a[0])).await;}'):
            with self.subTest(bad=bad),self.assertRaisesRegex(Error,'non durable'):
                verify_program(declarations+bad)

    def test_pool_target_join_last_use_and_reuse(self):
        source=self.declarations+'''async fn child(v:&u8)->&u8{yield;return relay(v);}
          fn main(){let mut p=pool<String>(1);let mut a=p.new();a.push_str("A");
            let h=runtime::spawn(->child(&a[0]));BEFORE let joined=h.join();DURING
            match joined{Ok(v)=>{print(*v as Int);},Err(_)=>{print(99);}}
            drop(->a);let mut b=p.new();b.push_str("B");print(&b[..]);}'''
        self.assertEqual(self.run_native(source.replace('BEFORE','').replace('DURING','')).stdout,'65\nB\n')
        self.assertEqual(self.run_native(source.replace('BEFORE','').replace('DURING',''),fail_at=1).stdout,'99\nB\n')
        for position in ('BEFORE','DURING'):
            for conflict in ('a.push_str("C");','drop(->a);'):
                with self.subTest(position=position,conflict=conflict),self.assertRaises(Error):
                    verify_program(source.replace(position,conflict).replace('BEFORE','').replace('DURING',''))

    def test_native_capture_from_string_and_return(self):
        source=self.declarations+'''fn main(){let mut p=pool<String>(1);
          let mut a=p.new();a.push_str("A");let v=&a[0];
          let h=runtime::thread({->(v);return same(v);});BEFORE
          let joined=h.join();DURING
          match joined{Ok(r)=>{print(*r as Int);},Err(_)=>{}}
          drop(->a);let mut b=p.new();b.push_str("B");print(&b[..]);}'''
        self.assertEqual(self.run_native(source.replace('BEFORE','').replace('DURING','')).stdout,'65\nB\n')
        for position in ('BEFORE','DURING'):
            with self.subTest(position=position),self.assertRaises(Error):
                verify_program(source.replace(position,'drop(->a);').replace('BEFORE','').replace('DURING',''))

    def test_async_contract_drops_unreturned_source_after_join(self):
        declarations=self.declarations+'''async fn only_first(a:&u8,b:&u8)->&u8{yield;return first(a,b);}
          async fn relay_first(a:&u8,b:&u8)->&u8{return only_first(a,b).await;}'''
        source=declarations+'''fn main(){let mut p=pool<String>(2);
          let mut a=p.new();a.push_str("A");let mut b=p.new();b.push_str("B");
          let h=runtime::spawn(->relay_first(&a[0],&b[0]));let joined=h.join();
          drop(->b);BEFORE match joined{Ok(v)=>{print(*v as Int);},Err(_)=>{}}
          drop(->a);}'''
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'65\n')
        with self.assertRaises(Error):verify_program(source.replace('BEFORE','drop(->a);'))

    def test_async_conditional_result_keeps_both_pools_after_join(self):
        source=self.declarations+'''async fn child(a:&u8,b:&u8,n:Int)->&u8{
          yield;return choose(a,b,n);}
          fn main(){let mut p=pool<String>(1);let mut q=pool<String>(1);
          let mut a=p.new();a.push_str("A");let mut b=q.new();b.push_str("B");
          let h=runtime::spawn(->child(&a[0],&b[0],FLAG));BEFORE
          let joined=h.join();DURING
          match joined{Ok(v)=>{print(*v as Int);},Err(_)=>{}}
          drop(->a);drop(->b);}'''
        for flag,expected in ((0,'65\n'),(1,'66\n')):
            selected=source.replace('FLAG',str(flag))
            self.assertEqual(self.run_native(selected.replace('BEFORE','').replace('DURING','')).stdout,expected)
            for position in ('BEFORE','DURING'):
                for conflict in ('drop(->a);','drop(->b);'):
                    with self.subTest(flag=flag,position=position,conflict=conflict),self.assertRaises(Error):
                        verify_program(selected.replace(position,conflict).replace('BEFORE','').replace('DURING',''))

    def test_legacy_reset_after_join_keeps_returned_source(self):
        source=self.declarations+'''async fn child(v:&u8)->&u8{yield;return same(v);}
          fn main(){let mut p=pool<String>(1);let mut a=p.new();a.push_str("A");
          let h=runtime::spawn(->child(&a[0]));let joined=h.join();BEFORE
          match joined{Ok(v)=>{print(*v as Int);},Err(_)=>{}}p.reset();}'''
        verify_program(source.replace('BEFORE',''),allow_legacy_reset=True)
        with self.assertRaisesRegex(Error,'reset interdit'):
            verify_program(source.replace('BEFORE','p.reset();'),allow_legacy_reset=True)

    def test_static_result_has_no_source_and_mutable_parent_stays_protected(self):
        declarations=self.declarations+'''fn literal()->&u8{return &"Z"[0];}'''
        body='let r=literal();yield;return read(r) as Int;'
        self.assertEqual(self.run_native(self.wrap(body,declarations)).stdout,'90\n')
        body='''let mut a:[u8;1]=[7];let mut parent=&mut a[0];
          let r=same(&*parent);BEFORE let n=*r;*parent=9;return n as Int;'''
        for argument in ('&*parent','parent'):
            selected=body.replace('&*parent',argument)
            self.assertEqual(self.run_native(self.wrap(selected.replace('BEFORE',''),declarations)).stdout,'7\n')
            for conflict in ('*parent=8;','a[0]=8;'):
                with self.subTest(argument=argument,conflict=conflict),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.wrap(selected.replace('BEFORE',conflict),declarations))

if __name__=='__main__':unittest.main()
