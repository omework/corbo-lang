"""Injected pool lifetimes and exclusive loans through real task states."""
from pathlib import Path
import unittest
from unittest.mock import patch
from crust import Compiler, Error, verify_program
import test_native_blocks as native


class AsyncPoolInjectionTests(unittest.TestCase):
    run_c_oracle = native.NativeBlockTests.run_c_oracle
    run_native = native.NativeBlockTests.run_native
    assert_destroyed = native.NativeBlockTests.assert_destroyed
    helpers = '''fn make(p:&mut Pool<Int>,n:Int)-><-Int{let a=p.new(n);return <-a;}
      fn relay(p:&mut Pool<Int>,n:Int)-><-Int{let a=make(p,n);return <-a;}'''

    @classmethod
    def program(cls, body, *, before='', after='', declarations='', capacity=1, result='<-Int'):
        return cls.helpers+declarations+'async fn work(p:&mut Pool<Int>)->'+result+'{'+body+f'''}}
          fn main(){{let mut p=pool<Int>({capacity});let t=work(&mut p);BEFORE
            let h=runtime::spawn(->t);match h.join(){{Ok(v)=>{{print(v);drop(->v);}},Err(_)=>{{print(99);}}}}
            AFTER let b=p.new(9);print(b);drop(->b);}}'''.replace('BEFORE',before).replace('AFTER',after)

    def test_recorded_case_and_contracts_only_verification(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-pool-helper.crb').read_text()
        with patch.object(Compiler,'emit_async_sync_bridge',side_effect=AssertionError('codegen during verify')):
            verify_program(source)
        run=self.run_native(source)
        self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7])

    def test_direct_helper_and_nested_helper_creation(self):
        for body in ('let a=relay(p,7);yield;return <-a;',
                     'let a=p.new(7);yield;return <-a;',
                     'return <-p.new(7);', 'return <-make(p,7);'):
            with self.subTest(body=body):
                run=self.run_native(self.program(body))
                self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[7,9])

    def test_pool_reserved_before_spawn_until_join(self):
        body='yield;return <-make(p,7);'
        for operation in ('let a=p.new(8);drop(->a);',
                          'let other=work(&mut p);drop(->other);',
                          'let a=make(&mut p,8);drop(->a);', 'p.reset();'):
            for running in (False, True):
                source=self.program(body,before='' if running else operation)
                if running:
                    source=source.replace('match h.join()',operation+'match h.join()')
                with self.subTest(operation=operation,running=running),self.assertRaises(Error):
                    verify_program(source)
        # Dropping an inactive instance releases the loan without allocating.
        source=self.program(body).replace('let h=runtime::spawn(->t);','drop(->t);let h=runtime::spawn(->work(&mut p));')
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[7,9])

    def test_pool_mode_type_and_explicit_reference(self):
        source=self.program('return <-make(p,7);')
        for before,after in (('work(&mut p)','work(p)'), ('work(&mut p)','work(&p)'),
                             ('pool<Int>(1)','pool<String>(1)'), ('make(p,7)','make(&mut p,7)'),
                             ('async fn work(p:&mut Pool<Int>)','async fn work(p:&Pool<Int>)'),
                             ('let mut p=pool<Int>(1)','let p=pool<Int>(1)'),
                             ('return <-make(p,7);','print(*p);return <-make(p,7);')):
            with self.subTest(after=after),self.assertRaises(Error):verify_program(source.replace(before,after))
        readonly=source.replace('async fn work(p:&mut Pool<Int>)','async fn work(p:&Pool<Int>)')
        with self.assertRaisesRegex(Error,'mutable.*pool|pool.*mutable'):
            verify_program(readonly.replace('work(&mut p)','work(&p)'))
        for body in ('let a=new(p) String(7);return <-a;',
                     'return <-new(p) String(7);'):
            with self.subTest(body=body),self.assertRaisesRegex(Error,'type incompatible'):
                verify_program(self.program(body))

    def test_shared_pool_captures_can_coexist_but_not_allocate(self):
        source='''fn inspect(p:&Pool<Int>)->Int{return 7;}
          async fn read(p:&Pool<Int>)->Int{yield;return inspect(p);}
          fn main(){let mut p=pool<Int>(1);let a=read(&p);let b=read(&p);
            let h=runtime::spawn(->a);match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
            drop(->b);let v=p.new(9);print(v);}'''
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[9])
        with self.assertRaisesRegex(Error,'pool.*capture|capture.*pool'):
            verify_program(source.replace('drop(->b);','let v=p.new(8);drop(->v);drop(->b);'))

    def test_returned_allocation_preserves_pool_but_not_exclusive_loan(self):
        source=self.program('return <-make(p,7);',capacity=2)
        source=source.replace('print(v);drop(->v);','let other=p.new(8);print(v);print(other);drop(->other);drop(->v);')
        run=self.run_native(source)
        self.assertEqual(run.stdout,'7\n8\n9\n');self.assert_destroyed(run,[8,7,9])
        escaped=self.program('return <-make(p,7);').replace(
          'let mut p=pool<Int>(1);let t=work(&mut p);',
          'let t={let mut p=pool<Int>(1);let inner=work(&mut p);<-inner};')
        with self.assertRaises(Error):verify_program(escaped)
        escaped_result=self.helpers+'''async fn work(p:&mut Pool<Int>)-><-Int{return <-make(p,7);}
          fn main(){let a={let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));
            let value=match h.join(){Ok(a)=>{<-a},Err(_)=>{return;}};<-value};print(a);}'''
        with self.assertRaises(Error):verify_program(escaped_result)

    def test_factory_and_handle_relay_keep_source_reservation(self):
        factory='''fn start(p:&mut Pool<Int>)-><-Execution<work>{
          let h=runtime::spawn(->work(p));return <-h;}
          fn again(h:->Execution<work>)-><-Execution<work>{return <-h;}'''
        source=self.program('return <-make(p,7);',declarations=factory)
        source=source.replace('let t=work(&mut p);','').replace('let h=runtime::spawn(->t);','let h=again(->start(&mut p));')
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[7,9])
        with self.assertRaisesRegex(Error,'capture async'):
            verify_program(source.replace('match h.join()','let x=p.new(8);drop(->x);match h.join()'))

    def test_child_keeps_pool_reserved_until_await(self):
        child='async fn child(p:&mut Pool<Int>)-><-Int{yield;return <-make(p,7);}'
        body='let child=child(p);BEFORE let a=child.await;let b=p.new(8);drop(->b);return <-a;'
        source=self.program(body.replace('BEFORE',''),declarations=child,capacity=2)
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[8,7,9])
        for bad in ('let b=p.new(8);drop(->b);','let b=make(p,8);drop(->b);',
                    'let other=child(p);drop(->other);'):
            with self.subTest(bad=bad),self.assertRaisesRegex(Error,'emprunt actif'):
                verify_program(self.program(body.replace('BEFORE',bad),declarations=child,capacity=2))

    def test_left_to_right_source_arguments_remain_exclusive(self):
        declarations='fn both(a:&mut Pool<Int>,b:&mut Pool<Int>){let x=a.new(1);let y=b.new(2);print(x);print(y);}'
        body='both(p,p);return <-make(p,7);'
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(self.program(body,declarations=declarations))
        source=self.program('return <-make(p,{yield;7});')
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n9\n')
        with self.assertRaisesRegex(Error,'emprunt actif'):
            verify_program(self.program('return <-make(p,{let a=p.new(8);drop(->a);7});'))

    def test_collection_factory_returns_from_injected_pool(self):
        for typ,edit,display,expected in (
            ('String','a.push_str("A");','print(&v[..]);','A\n'),
            ('Vector<Int>','a.push(7);','print(v[0]);','7\n'),
            ('Vector<u8>','a.push(7);','print(v[0] as Int);','7\n')):
            source=f'''fn make(p:&mut Pool<{typ}>)-><-{typ}{{let mut a=p.new();{edit}return <-a;}}
              async fn work(p:&mut Pool<{typ}>)-><-{typ}{{yield;return <-make(p);}}
              fn main(){{let mut p=pool<{typ}>(1);let h=runtime::spawn(->work(&mut p));
                match h.join(){{Ok(v)=>{{{display}drop(->v);}},Err(_)=>{{}}}}
                let b=p.new();drop(->b);}}'''
            with self.subTest(typ=typ):
                run=self.run_native(source);self.assertEqual(run.stdout,expected)
                self.assertEqual(sum(x.startswith('destroy ') for x in run.stderr.splitlines()),2)

    def test_failed_launch_does_not_run_factory_and_releases_pool(self):
        run=self.run_native(self.program('return <-make(p,7);'),fail_at=1)
        self.assertEqual(run.stdout,'99\n9\n');self.assert_destroyed(run,[9])

    def test_distinct_live_allocation_can_drop_while_pool_is_borrowed(self):
        source=self.program('yield;return <-make(p,7);',capacity=2)
        source=source.replace('let t=work(&mut p);','let old=p.new(4);let t=work(&mut p);')
        source=source.replace('match h.join()', 'drop(->old);match h.join()')
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n9\n')
        values=[line.rsplit('=',1)[-1] for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertCountEqual(values,['4','7','9'])

    def test_native_block_transfers_pool_reference_binding(self):
        source=self.helpers+'''fn main(){let mut p=pool<Int>(1);
          let memory:&mut Pool<Int>=&mut p;
          let h=runtime::thread({->(memory);let a=relay(memory,7);return <-a;});BEFORE
          match h.join(){Ok(a)=>{print(a);drop(->a);},Err(_)=>{}}
          AFTER let b=p.new(9);print(b);}'''
        run=self.run_native(source.replace('BEFORE','').replace('AFTER',''))
        self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[7,9])
        for marker,statement in (('BEFORE','let a=p.new(8);drop(->a);'),
                                 ('AFTER','let a=make(memory,8);drop(->a);')):
            invalid=source.replace(marker,statement).replace('BEFORE','').replace('AFTER','')
            with self.subTest(statement=statement),self.assertRaises(Error):verify_program(invalid)
        # The child can allocate directly with the same stable Source pointer.
        direct=source.replace('let a=relay(memory,7);','let a=memory.new(7);')
        self.assertEqual(self.run_native(direct.replace('BEFORE','').replace('AFTER','')).stdout,'7\n9\n')

    def test_named_pool_loan_ends_at_last_use_and_shared_loans_coexist(self):
        source=self.helpers+'''fn main(){let mut p=pool<Int>(2);let memory=&mut p;
          BEFORE let a=make(memory,7);let b=p.new(8);print(a);print(b);AFTER}'''
        run=self.run_native(source.replace('BEFORE','').replace('AFTER',''))
        self.assertEqual(run.stdout,'7\n8\n');self.assert_destroyed(run,[8,7])
        for marker,operation in (('BEFORE','let b=p.new(1);drop(->b);'),
                                  ('AFTER','let b=make(memory,9);drop(->b);')):
            invalid=source.replace(marker,operation).replace('BEFORE','').replace('AFTER','')
            with self.subTest(operation=operation),self.assertRaisesRegex(Error,'pool.*emprunt nommé'):
                verify_program(invalid)
        shared='''fn see(p:&Pool<Int>){print(1);}
          fn main(){let mut p=pool<Int>(1);let a=&p;let b=&p;see(a);see(b);let v=p.new(2);print(v);}'''
        self.assertEqual(self.run_native(shared).stdout,'1\n1\n2\n')

    def test_precise_result_pool_survives_while_other_capture_pool_closes(self):
        declarations='''fn first(p:&mut Pool<Int>,q:&mut Pool<Int>)-><-Int{
          let b=q.new(8);print(b);let a=p.new(7);return <-a;}
          async fn work(p:&mut Pool<Int>,q:&mut Pool<Int>)-><-Int{yield;return <-first(p,q);}'''
        main='''fn main(){let mut p=pool<Int>(1);let result={let mut q=pool<Int>(1);
          let h=runtime::spawn(->work(&mut p,&mut q));
          let result=match h.join(){Ok(a)=>{<-a},Err(_)=>{return;}};<-result};
          print(result);drop(->result);let reused=p.new(9);print(reused);}'''
        run=self.run_native(declarations+main)
        self.assertEqual(run.stdout,'8\n7\n9\n');self.assert_destroyed(run,[8,7,9])
        with self.assertRaises(Error):
            verify_program(declarations.replace('return <-a;','return <-b;')+main)
        # Both candidates must remain in the result contract, independent of
        # the particular flag observed during either execution below.
        choose='''fn choose(p:&mut Pool<Int>,q:&mut Pool<Int>,flag:Int)-><-Int{
          let a=p.new(7);let b=q.new(8);if flag==0{return <-a;}return <-b;}
          async fn work(p:&mut Pool<Int>,q:&mut Pool<Int>,flag:Int)-><-Int{
            return <-choose(p,q,flag);}'''
        both='''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
          let h=runtime::spawn(->work(&mut p,&mut q,FLAG));
          match h.join(){Ok(a)=>{print(a);drop(->a);},Err(_)=>{}}}'''
        for flag in (0,1):
            with self.subTest(flag=flag):
                run=self.run_native(choose+both.replace('FLAG',str(flag)))
                self.assertEqual(run.stdout,f'{7+flag}\n')
                self.assert_destroyed(run,[8,7] if flag==0 else [7,8])
                escaped=main.replace('work(&mut p,&mut q)','work(&mut p,&mut q,'+str(flag)+')')
                with self.assertRaises(Error):verify_program(choose+escaped)

    def test_direct_pool_allocation_replacement_and_control_cleanup(self):
        body='''let mut a=p.new(1);a=p.new(2);let view=&a;let n=*view;
          drop(->a);let b=p.new(n+5);return <-b;'''
        run=self.run_native(self.program(body,capacity=2))
        self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[1,2,7,9])
        with self.assertRaises(Error):
            verify_program(self.program(body.replace('let view=&a;','let view=&a;drop(->a);'),capacity=2))
        # No pool entry exists when an initializer exits before construction.
        early='''async fn work(p:&mut Pool<Int>)->Int{
          let a=p.new({yield;return 42;});print(a);return 0;}
          fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
            let b=p.new(9);print(b);}'''
        run=self.run_native(early)
        self.assertEqual(run.stdout,'42\n9\n');self.assert_destroyed(run,[9])

    def test_return_keeps_address_and_reuses_same_slot(self):
        source=self.program('let a=p.new(7);let b=locate(->a);yield;return <-b;',
                            declarations='fn locate(a:->Int)-><-Int{address(a);return <-a;}')
        source=source.replace('print(v);drop(->v);','address(v);print(v);drop(->v);')
        source=source.replace('print(b);drop(->b);','address(b);print(b);drop(->b);')
        run=self.run_native(source)
        initial,returned,value,reused,next_value=run.stdout.splitlines()
        self.assertEqual((initial,returned),(returned,reused))
        self.assertEqual((value,next_value),('7','9'));self.assert_destroyed(run,[7,9])

    def test_native_child_can_use_parent_injected_pool(self):
        # Return an owned result only on success; on an error return directly
        # from the Int parent so the pool can still be reused by its caller.
        source=self.helpers+'''async fn work(p:&mut Pool<Int>)->Int{
          let h=runtime::thread({->(p);let a=make(p,7);return <-a;});
          match h.await{Ok(a)=>{let n=*a;drop(->a);return n;},Err(_)=>{return 99;}}}
          fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
            let b=p.new(9);print(b);}'''
        run=self.run_native(source)
        self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[7,9])
        with self.assertRaises(Error):
            verify_program(source.replace('match h.await','let a=make(p,8);drop(->a);match h.await'))

    def test_iteration_cleanup_reuses_slot_before_continue_and_break(self):
        body='''let mut n=0;while n<3{let a=p.new(n);print(*a);yield;n=n+1;continue;}
          let result=loop{let b=p.new(7);break <-b;};return <-result;'''
        run=self.run_native(self.program(body))
        self.assertEqual(run.stdout,'0\n1\n2\n7\n9\n')
        self.assert_destroyed(run,[0,1,2,7,9])


if __name__ == '__main__':
    unittest.main()
