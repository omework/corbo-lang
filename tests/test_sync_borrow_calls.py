"""Reference contracts across synchronous calls from native/async states."""
import unittest
from unittest.mock import patch

from crust import Compiler, Error, verify_program
import test_native_blocks as native_tests


class SyncBorrowCallTests(unittest.TestCase):
    run_c_oracle = native_tests.NativeBlockTests.run_c_oracle
    run_native = native_tests.NativeBlockTests.run_native
    assert_destroyed = native_tests.NativeBlockTests.assert_destroyed

    @staticmethod
    def wrap(body, declarations='', native=False):
        if native:
            return declarations + '''fn main(){let h=runtime::thread({BODY});
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''.replace('BODY',body)
        return declarations + '''async fn run()->Int{BODY}
            fn main(){let h=runtime::spawn(->run());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''.replace('BODY',body)

    def test_named_captures_and_direct_scalar_places(self):
        declarations='fn read(v:&Int)->Int{return *v;}fn edit(v:&mut Int,n:Int){*v=n;}'
        for native in (False,True):
            source=self.wrap('let mut a=7;edit(&mut a,9);return read(&a);',declarations,native)
            self.assertEqual(self.run_native(source).stdout,'9\n')
        source=declarations+'''fn main(){let mut p=pool<Int>(1);let mut a=p.new(7);let v=&mut a;
          let h=runtime::thread({->(v);edit(v,9);return read(v);});BEFORE
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}print(a);drop(->a);}'''
        run=self.run_native(source.replace('BEFORE',''))
        self.assertEqual(run.stdout,'9\n9\n')
        self.assert_destroyed(run,[9])
        for before in ('print(a);','drop(->a);','a=2;','print(v);'):
            with self.subTest(before=before),self.assertRaises(Error):
                verify_program(source.replace('BEFORE',before))

    def test_array_and_byte_mutable_places(self):
        declarations='''fn edit(v:&mut Int,n:Int){*v=n;}
          fn read(v:&Int)->Int{return *v;}
          fn byte(v:&mut u8,n:u8){*v=n;}
          fn same_byte(v:&mut u8)->&mut u8{return v;}'''
        source=self.wrap('''let mut values=[7,8];edit(&mut values[0],9);
          let first=read(&values[0]);let mut bytes:[u8;2]=[3,4];
          let mut view=same_byte(&mut bytes[1]);byte(view,6);
          yield;let last=*view;bytes[1]=10;return first+(last as Int);''',declarations)
        self.assertEqual(self.run_native(source).stdout,'15\n')
        for old,new in [('byte(view,6)','byte(view,256)'),('byte(view,6)','edit(view,6)'),
                        ('yield;let last','bytes[1]=10;yield;let last'),
                        ('edit(&mut values[0],9)','edit(&values[0],9)')]:
            with self.subTest(new=new),self.assertRaises(Error):
                verify_program(source.replace(old,new))

    def test_prepared_references_reserve_later_arguments(self):
        declarations='''fn pair(a:&mut Int,b:&mut Int){a.set(10);b.set(20);}
          fn read(a:&Int)->Int{return *a;}fn write_value(a:&mut Int,n:Int){*a=n;}
          fn shared(a:&Int,b:&Int)->Int{return *a+*b;}'''
        self.assertEqual(self.run_native(self.wrap('let a=7;return shared(&a,&a);',declarations)).stdout,'14\n')
        for body in ('let mut a=7;pair(&mut a,&mut a);return a;',
                     'let mut a=7;write_value(&mut a,read(&a));return a;',
                     'let mut a=7;write_value(&mut a,a);return a;',
                     'let mut a=7;write_value(&mut a,{a=8;8});return a;',
                     'let a=7;write_value(&mut a,8);return a;'):
            with self.subTest(body=body),self.assertRaises(Error):
                verify_program(self.wrap(body,declarations))

    def test_last_use_inside_earlier_argument_and_future_uses(self):
        declarations='''fn same(a:&mut Int)->&mut Int{return a;}
          fn read(a:&Int)->Int{return *a;}
          fn pair(a:Int,b:&mut Int){*b=a;}'''
        body='''let mut a=7;let mut r=same(&mut a);
          pair(read(r),&mut a);AFTER return a;'''
        self.assertEqual(self.run_native(self.wrap(body.replace('AFTER',''),declarations)).stdout,'7\n')
        for after in ('r.set(9);','print(*r);','let n=read(r);print(n);'):
            with self.subTest(after=after),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(self.wrap(body.replace('AFTER',after),declarations))
        invalid='''let mut a=7;let mut r=same(&mut a);let mut i=0;
          while i<2{let n=read(r);a=9;i=i+1;}return a;'''
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(self.wrap(invalid,declarations))

    def test_mutable_result_reserves_parent_until_last_use(self):
        declarations='''fn same(a:&mut Int)->&mut Int{return a;}
          fn relay(a:&mut Int)->&mut Int{return same(a);}'''
        body='''let mut a=7;let mut r=relay(&mut a);BEFORE
          yield;r.set(9);a=10;return a;'''
        self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE',''),declarations)).stdout,'10\n')
        for before in ('a=8;','print(a);','drop(->a);'):
            with self.subTest(before=before),self.assertRaises(Error):
                verify_program(self.wrap(body.replace('BEFORE',before),declarations))
        for call in ('same(&r)','same(&mut r)'):
            with self.subTest(call=call),self.assertRaises(Error):
                verify_program(self.wrap(body.replace('BEFORE',f'let mut s={call};s.set(8);'),declarations))

    def test_conditional_reference_result_reaches_join_and_protects_both_sources(self):
        template='''fn choose(a:&mut Int,b:&mut Int,n:Int)->&mut Int{if n==0{return a;}return b;}
          fn relay(a:&mut Int,b:&mut Int,n:Int)->&mut Int{return choose(a,b,n);}
          fn main(){let mut p=pool<Int>(2);let mut a=p.new(7);let mut b=p.new(8);
            let va=&mut a;let vb=&mut b;let n=FLAG;
            let h=runtime::thread({->(va,vb,n);return relay(va,vb,n);});BEFORE
            let joined=h.join();DURING
            match joined{Ok(v)=>{v.set(42);},Err(_)=>{}}
            print(a);print(b);drop(->a);drop(->b);}'''
        for flag,expected in ((0,'42\n8\n'),(1,'7\n42\n')):
            source=template.replace('FLAG',str(flag))
            self.assertEqual(self.run_native(source.replace('BEFORE','').replace('DURING','')).stdout,expected)
            for place in ('BEFORE','DURING'):
                for conflict in ('a=3;','b=3;','drop(->a);','drop(->b);'):
                    with self.subTest(flag=flag,place=place,conflict=conflict),self.assertRaises(Error):
                        verify_program(source.replace(place,conflict).replace('BEFORE','').replace('DURING',''))
        self.assertEqual(self.run_native(template.replace('FLAG','0').replace('BEFORE','').replace('DURING',''),fail_at=1).stdout,'7\n8\n')

    def test_async_reference_return_and_local_reference_escape(self):
        declarations='''fn same(a:&mut Int)->&mut Int{return a;}
          async fn work(a:&mut Int)->&mut Int{let mut r=same(a);yield;return r;}'''
        source=declarations+'''fn main(){let mut p=pool<Int>(1);let mut a=p.new(7);
          let h=runtime::spawn(->work(&mut a));let result=h.join();BEFORE
          match result{Ok(v)=>{v.set(9);},Err(_)=>{}}print(a);}'''
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'9\n')
        with self.assertRaises(Error):verify_program(source.replace('BEFORE','drop(->a);'))
        for definition in (
            'async fn bad()->&mut Int{let mut local=[7];return same(&mut local[0]);}',
            'async fn bad(mut a:->Int)->&mut Int{return same(&mut a);}',
        ):
            with self.subTest(definition=definition),self.assertRaises(Error):
                verify_program(declarations+definition)

    def test_nested_reference_result_as_argument_and_shared_downgrade(self):
        declarations='''fn same(a:&mut Int)->&mut Int{return a;}
          fn view(a:&mut Int)->&Int{return a;}
          fn read(a:&Int)->Int{return *a;}'''
        body='let mut a=7;let n=read(same(&mut a));let r=view(&mut a);print(*r);a=9;return n+a;'
        self.assertEqual(self.run_native(self.wrap(body,declarations)).stdout,'7\n16\n')
        with self.assertRaises(Error):
            verify_program(self.wrap(body.replace('print(*r);','a=8;print(*r);'),declarations))

    def test_early_return_releases_prepared_reference_without_calling_helper(self):
        declarations='fn write_value(a:&mut Int,n:Int){print(99);*a=n;}'
        body='let mut a=7;write_value(&mut a,{return 8;});return a;'
        self.assertEqual(self.run_native(self.wrap(body,declarations)).stdout,'8\n')

    def test_call_verification_keeps_bodies_opaque(self):
        source=self.wrap('let mut a=7;edit(&mut a);return a;','fn edit(a:&mut Int){a.set(9);}')
        with patch.object(Compiler,'emit_async_sync_bridge',side_effect=AssertionError('backend during check')):
            checked=verify_program(source)
        self.assertEqual(checked.definitions,[])

    def test_prepared_reference_survives_suspension_and_rejects_alias(self):
        declarations='''fn write_value(a:&mut Int,n:Int){*a=n;}
          async fn delay()->Int{yield;return 9;}
          async fn read(a:&Int)->Int{yield;return *a;}'''
        body='let mut a=7;write_value(&mut a,delay().await);return a;'
        self.assertEqual(self.run_native(self.wrap(body,declarations)).stdout,'9\n')
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(self.wrap(body.replace('delay()','read(&a)'),declarations))

    def test_aborted_call_cleans_owned_target_once_and_reuses_slot(self):
        source='''fn write_value(a:&mut Int,n:Int){print(99);*a=n;}
          async fn work(mut a:->Int)->Int{
            write_value(&mut a,{yield;return 8;});return *a;}
          fn main(){let mut p=pool<Int>(1);let a=p.new(7);
            let h=runtime::spawn(->work(->a));
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}
            let b=p.new(9);print(b);drop(->b);}'''
        run=self.run_native(source)
        self.assertEqual(run.stdout,'8\n9\n')
        self.assert_destroyed(run,[7,9])

    def test_outer_continuation_keeps_named_loan_active(self):
        declarations='fn same(a:&mut Int)->&mut Int{return a;}fn read(a:&Int)->Int{return *a;}'
        body='''let mut a=7;let mut r=same(&mut a);
          {let n=read(r);print(n);a=9;}r.set(10);return a;'''
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(self.wrap(body,declarations))

    def test_local_result_tracks_union_but_not_unreturned_parameters(self):
        declarations='''fn choose(a:&mut Int,b:&mut Int,n:Int)->&mut Int{if n==0{return a;}return b;}
          fn first(a:&mut Int,b:&mut Int,n:Int)->&mut Int{return a;}'''
        for flag,expected in ((0,'42\n8\n50\n'),(1,'7\n42\n49\n')):
            body=f'''let mut a=7;let mut b=8;let mut r=choose(&mut a,&mut b,{flag});
              BEFORE yield;r.set(42);print(a);print(b);return a+b;'''
            self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE',''),declarations)).stdout,expected)
            for conflict in ('a=3;','b=3;','drop(->a);','drop(->b);'):
                with self.subTest(flag=flag,conflict=conflict),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.wrap(body.replace('BEFORE',conflict),declarations))
        body='''let mut a=7;let mut b=8;let mut r=first(&mut a,&mut b,0);
          b=10;r.set(42);return a+b;'''
        self.assertEqual(self.run_native(self.wrap(body,declarations)).stdout,'52\n')

    def test_drop_scalar_target_after_last_reference_use(self):
        declarations='fn same(a:&mut Int)->&mut Int{return a;}fn read(a:&Int)->Int{return *a;}'
        body='''let mut a=7;let mut r=same(&mut a);let result=read(r);
          drop(->a);AFTER return result;'''
        for native in (False,True):
            self.assertEqual(self.run_native(self.wrap(body.replace('AFTER',''),declarations,native)).stdout,'7\n')
            for after in ('print(a);','a=8;','drop(->a);'):
                with self.subTest(native=native,after=after),self.assertRaisesRegex(Error,'plus utilisable'):
                    verify_program(self.wrap(body.replace('AFTER',after),declarations,native))
        for typ,initializer,usage in [('Int','7','print(a);'),('u8','7','print(a as Int);'),('Bool','true','if a{print(1);}')]:
            with self.subTest(typ=typ),self.assertRaisesRegex(Error,'plus utilisable'):
                verify_program(self.wrap(f'let a:{typ}={initializer};drop(->a);{usage}return 0;'))

    def test_returned_reference_is_captured_by_async_child(self):
        declarations='''fn same(a:&mut Int)->&mut Int{return a;}
          async fn edit(a:&mut Int)->&mut Int{yield;a.set(9);return a;}
          async fn relay(a:&mut Int)->&mut Int{return edit(same(a)).await;}'''
        body='''let mut a=7;let task=edit(same(&mut a));BEFORE
          let mut r=task.await;DURING r.set(10);return a;'''
        self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE','').replace('DURING',''),declarations)).stdout,'10\n')
        for position in ('BEFORE','DURING'):
            for conflict in ('a=3;','drop(->a);'):
                with self.subTest(position=position,conflict=conflict),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.wrap(body.replace(position,conflict).replace('BEFORE','').replace('DURING',''),declarations))
        source=declarations+'''fn main(){let mut p=pool<Int>(1);let mut a=p.new(7);
          let h=runtime::spawn(->relay(&mut a));match h.join(){Ok(v)=>{v.set(42);},Err(_)=>{}}print(a);}'''
        self.assertEqual(self.run_native(source).stdout,'42\n')


if __name__=='__main__':unittest.main()
