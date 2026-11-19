"""Ownership, identity and cleanup across synchronous calls from task states."""
import unittest
from unittest.mock import patch
from crust import Compiler, Error, verify_program
import test_native_blocks as native

class SyncOwnedCallTests(unittest.TestCase):
    run_c_oracle=native.NativeBlockTests.run_c_oracle
    run_native=native.NativeBlockTests.run_native
    assert_destroyed=native.NativeBlockTests.assert_destroyed
    declarations='''fn consume(a:->Int){print(a);}
      fn same(a:->Int)-><-Int{return <-a;}
      fn edit(mut a:->Int,n:Int)-><-Int{a=n;return <-a;}
      fn read(a:&Int)->Int{return *a;}'''

    @staticmethod
    def program(body,declarations='',native_block=False,result='Int'):
        main='''fn main(){let mut p=pool<Int>(1);let a=p.new(7);START
          match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}
          let b=p.new(9);print(b);drop(->b);}'''
        if native_block:
            return declarations+main.replace('START','let h=runtime::thread({->(a);'+body+'});')
        return declarations+'async fn run(a:->Int)->'+result+'{'+body+'}'+main.replace('START','let h=runtime::spawn(->run(->a));')

    def test_consume_and_named_result_cleanup_in_both_contexts(self):
        for native_block in (False,True):
            for body,trace in [('consume(->a);return 8;',[7,9]),
                               ('let b=edit(->a,10);print(*b);drop(->b);return 8;',[10,9])]:
                with self.subTest(native=native_block,body=body):
                    run=self.run_native(self.program(body,self.declarations,native_block))
                    self.assertEqual(run.stdout,('7' if trace[0]==7 else '10')+'\n8\n9\n')
                    self.assert_destroyed(run,trace)

    def test_transfers_and_usages_are_explicit(self):
        for body in ('consume(a);return 8;', 'consume(&a);return 8;',
                     'consume(->a);print(*a);return 8;', 'consume(->a);consume(->a);return 8;',
                     'same(->a);return 8;', 'let _=same(->a);return 8;',
                     'let unused=same(->a);return 8;', 'return same(->a);'):
            with self.subTest(body=body),self.assertRaises(Error):
                verify_program(self.program(body,self.declarations))
        run=self.run_native(self.program('drop(->same(->a));return 8;',self.declarations))
        self.assertEqual(run.stdout,'8\n9\n');self.assert_destroyed(run,[7,9])

    def test_argument_order_temporary_read_and_stored_loan(self):
        declarations=self.declarations+'''fn use_after(n:Int,a:->Int){print(n);print(a);}
          fn use_before(a:->Int,n:Int){print(a);print(n);}
          fn alias(a:&Int,b:->Int){print(a);print(b);}'''
        body='let view=&a;use_after(read(view),->a);AFTER return 8;'
        run=self.run_native(self.program(body.replace('AFTER',''),declarations))
        self.assertEqual(run.stdout,'7\n7\n8\n9\n');self.assert_destroyed(run,[7,9])
        for invalid in (body.replace('AFTER','print(*view);'),
                        'use_before(->a,read(&a));return 8;',
                        'alias(&a,->a);return 8;'):
            with self.subTest(invalid=invalid),self.assertRaises(Error):
                verify_program(self.program(invalid,declarations))

    def test_prepared_owner_survives_suspension_or_is_dropped_on_return(self):
        declarations=self.declarations+'''fn take(a:->Int,n:Int){print(90);print(a);print(n);}
          async fn delay()->Int{yield;return 6;}'''
        for argument,expected in [('delay().await','90\n7\n6\n8\n9\n'),
                                  ('{yield;return 42;}','42\n9\n')]:
            run=self.run_native(self.program(f'take(->a,{argument});return 8;',declarations))
            self.assertEqual(run.stdout,expected);self.assert_destroyed(run,[7,9])
        with self.assertRaisesRegex(Error,'plus utilisable'):
            verify_program(self.program('take(->a,{yield;print(*a);6});return 8;',declarations))

    def test_nested_calls_and_loop_inside_later_argument(self):
        declarations=self.declarations+'fn take(a:->Int,n:Int){print(a);print(n);}'
        body='''take(->same(->same(->a)),{let n=loop{yield;break 6;};n});return 8;'''
        run=self.run_native(self.program(body,declarations))
        self.assertEqual(run.stdout,'7\n6\n8\n9\n');self.assert_destroyed(run,[7,9])

    def test_multiple_prepared_owners_clean_in_reverse_order(self):
        source='''fn take(a:->Int,b:->Int,n:Int){print(99);print(a);print(b);print(n);}
          async fn run(a:->Int,b:->Int)->Int{take(->a,->b,{yield;return 42;});return 0;}
          fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(8);
          let h=runtime::spawn(->run(->a,->b));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          let c=p.new(9);let d=p.new(10);drop(->c);drop(->d);}'''
        run=self.run_native(source);self.assertEqual(run.stdout,'42\n');self.assert_destroyed(run,[8,7,9,10])

    def test_owned_result_annotation_and_direct_mutable_loan(self):
        body='''let mut b:A<Int>=same(->a);let mut v=&mut b;*v=10;
          let n=read(v);consume(->b);return n;'''
        run=self.run_native(self.program(body,self.declarations))
        self.assertEqual(run.stdout,'10\n10\n9\n');self.assert_destroyed(run,[10,9])
        for before,after in [('A<Int>','Int'),('A<Int>','A<String>'),
                             ('consume(->b);','consume(->b);print(*v);')]:
            with self.subTest(after=after),self.assertRaises(Error):
                verify_program(self.program(body.replace(before,after),self.declarations))

    def test_owned_return_identity_and_child_capture(self):
        declarations=self.declarations+'''async fn child(a:->Int)-><-Int{yield;return <-a;}'''
        for body in ('let b=same(->a);return <-b;', 'return <-same(->a);',
                     'let task=child(->same(->a));let b=task.await;return <-b;'):
            source=declarations+'async fn run(a:->Int)-><-Int{'+body+'''}
              fn main(){let mut p=pool<Int>(1);let a=p.new(7);address(a);
              let h=runtime::spawn(->run(->a));match h.join(){Ok(v)=>{address(v);print(v);drop(->v);},Err(_)=>{}}
              let b=p.new(9);address(b);drop(->b);}'''
            with self.subTest(body=body):
                run=self.run_native(source);lines=run.stdout.splitlines()
                self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[0],lines[3]);self.assertEqual(lines[2],'7')
                self.assert_destroyed(run,[7,9])

    def test_conditional_return_uses_real_pool_and_cleans_other_parameter(self):
        source='''fn choose(a:->Int,b:->Int,n:Int)-><-Int{if n==0{return <-a;}return <-b;}
          async fn run(a:->Int,b:->Int,n:Int)-><-Int{yield;let value=choose(->a,->b,n);return <-value;}
          fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);let a=p.new(7);let b=q.new(8);
          address(a);address(b);let h=runtime::spawn(->run(->a,->b,FLAG));
          match h.join(){Ok(v)=>{address(v);print(v);drop(->v);},Err(_)=>{}}
          let c=p.new(9);let d=q.new(10);drop(->c);drop(->d);}'''
        for flag in (0,1):
            run=self.run_native(source.replace('FLAG',str(flag)));lines=run.stdout.splitlines()
            self.assertEqual(lines[2],lines[flag]);self.assertEqual(lines[3],str(7+flag))
            self.assert_destroyed(run,([8,7] if flag==0 else [7,8])+[9,10])

    def test_unreturned_pool_may_end_before_result(self):
        source='''fn first(a:->Int,b:->Int)-><-Int{print(b);return <-a;}
          async fn run(a:->Int,b:->Int)-><-Int{yield;return <-first(->a,->b);}
          fn factory(a:->Int,b:->Int)-><-run{let t=run(->a,->b);return <-t;}
          fn main(){let mut p=pool<Int>(1);let a=p.new(7);address(a);
          let result={a ->;let mut q=pool<Int>(1);let b=q.new(8);
            let task=factory(->a,->b);let h=runtime::spawn(->task);
            let value=match h.join(){Ok(v)=>{<-v},Err(_)=>{let fallback=p.new(9);<-fallback}};
            <-value};address(result);print(result);drop(->result);}'''
        run=self.run_native(source);lines=run.stdout.splitlines()
        self.assertEqual(lines[0],lines[2]);self.assertEqual((lines[1],lines[3]),('8','7'))
        self.assert_destroyed(run,[8,7])
        invalid=source.replace('print(b);return <-a;','if b==0{return <-a;}return <-b;')
        with self.assertRaises(Error):verify_program(invalid)
        # Only the result may forget q. A live handle still owns its captures.
        pending='''fn first(a:->Int,b:->Int)-><-Int{return <-a;}
          async fn run(a:->Int,b:->Int)-><-Int{yield;return <-first(->a,->b);}
          fn main(){let mut p=pool<Int>(1);let a=p.new(7);
            let h={a ->;let mut q=pool<Int>(1);let b=q.new(8);
              let child=runtime::spawn(->run(->a,->b));<-child};
            match h.join(){Ok(v)=>{drop(->v);},Err(_)=>{}}}'''
        with self.assertRaises(Error):verify_program(pending)
        with self.assertRaises(Error):
            verify_program('fn bad(a:->Int)->&Int{return &a;} async fn run(a:->Int)->&Int{return bad(->a);}')

    def test_collections_keep_their_type_and_cleanup(self):
        for typ,initialize,edit,display,expected in (
            ('String','a.push_str("A");','a.push_str("B");','print(&v[..]);','AB\n'),
            ('Vector<Int>','a.push(7);','a.push(8);','print(v[0]);print(v[1]);','7\n8\n'),
            ('Vector<u8>','a.push(7);','a.push(8);','print(v[0] as Int);print(v[1] as Int);','7\n8\n')):
            source=f'''fn edit(mut a:->{typ})-><-{typ}{{{edit}return <-a;}}
              async fn run(a:->{typ})-><-{typ}{{let b=edit(->a);yield;return <-b;}}
              fn main(){{let mut p=pool<{typ}>(1);let mut a=p.new();{initialize}
                let h=runtime::spawn(->run(->a));match h.join(){{Ok(v)=>{{{display}drop(->v);}},Err(_)=>{{}}}}
                let b=p.new();drop(->b);}}'''
            with self.subTest(typ=typ):
                run=self.run_native(source);self.assertEqual(run.stdout,expected)
                self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()),2)
        invalid='''fn consume(a:->Int){} async fn run(a:->String){consume(->a);}'''
        with self.assertRaisesRegex(Error,'allocation Int attendue'):verify_program(invalid)

    def test_replacement_evaluates_new_before_destroying_old(self):
        source=self.declarations+'''async fn run(mut a:->Int,b:->Int)->Int{
          a=same(->b);let n=*a;drop(->a);return n;}
          fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(8);
          let h=runtime::spawn(->run(->a,->b));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          let c=p.new(9);let d=p.new(10);drop(->c);drop(->d);}'''
        run=self.run_native(source);self.assertEqual(run.stdout,'8\n');self.assert_destroyed(run,[7,8,9,10])
        with self.assertRaises(Error):verify_program(source.replace('a=same(->b);','let view=&a;a=same(->b);print(*view);'))

    def test_verification_uses_contracts_and_failed_launch_cleans_input(self):
        source=self.program('consume(->a);return 8;',self.declarations)
        with patch.object(Compiler,'emit_async_sync_bridge',side_effect=AssertionError('backend during check')):
            verify_program(source)
        run=self.run_native(source,fail_at=1)
        self.assertEqual(run.stdout,'99\n9\n');self.assert_destroyed(run,[7,9])

if __name__=='__main__':unittest.main()
