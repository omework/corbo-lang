"""Local pool storage is tied to the state and the lexical scope."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncLocalPoolTests(unittest.TestCase):
    run_c_oracle=native.NativeBlockTests.run_c_oracle
    run_native=native.NativeBlockTests.run_native
    assert_destroyed=native.NativeBlockTests.assert_destroyed

    @staticmethod
    def wrap(body,helpers='',result='Int'):
        return helpers+f'''async fn work()->{result}{{{body}}}
          fn main(){{let h=runtime::spawn(->work());match h.join(){{Ok(v)=>{{print(v);}},Err(_)=>{{print(99);}}}}}}'''

    def test_recorded_native_child(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-native-async-local-pool.crb').read_text()
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7])

    def test_local_pool_survives_suspend_drop_and_reuse(self):
        source=self.wrap('''let mut p=pool<Int>(1);let mut a=p.new(7);yield;a=9;
          let view=&a;print(*view);drop(->a);let b=p.new(11);yield;return *b;''')
        run=self.run_native(source);self.assertEqual(run.stdout,'9\n11\n');self.assert_destroyed(run,[9,11])
        for text in ('print(a);','drop(->a);'):
            with self.assertRaises(Error):verify_program(source.replace('let b=p.new(11);',text+'let b=p.new(11);'))

    def test_local_collections_cleanup_and_state_reuse(self):
        for typ,edit,read,expected in (
            ('String','a.push_str("été");','print(&a[..]);','été\n'),
            ('Vector<Int>','a.push(7);','print(a[0]);','7\n'),
            ('Vector<u8>','a.push(255);','print(a[0] as Int);','255\n')):
            body=f'let mut p=pool<{typ}>(1);let mut a=p.new();{edit}yield;{read}drop(->a);let b=p.new();drop(->b);return 42;'
            source=self.wrap(body)
            # Two sequential instances reuse one state slot and fresh sources.
            source=source.replace('fn main(){','fn main(){let first=runtime::spawn(->work());match first.join(){Ok(v)=>{print(v);},Err(_)=>{}}')
            with self.subTest(typ=typ):
                run=self.run_native(source);self.assertEqual(run.stdout,(expected+'42\n')*2)
                self.assertEqual(sum(x.startswith('destroy ') for x in run.stderr.splitlines()),4)

    def test_child_pool_injection_and_owned_return(self):
        helper='''async fn make(p:&mut Pool<Int>)-><-Int{yield;return <-p.new(7);}
          fn relay(p:&mut Pool<Int>)-><-Int{let a=p.new(11);return <-a;}'''
        body='''let mut p=pool<Int>(2);let task=make(&mut p);BEFORE
          let a=task.await;let b=relay(&mut p);yield;return *a+*b;'''
        source=self.wrap(body.replace('BEFORE',''),helper)
        run=self.run_native(source);self.assertEqual(run.stdout,'18\n');self.assert_destroyed(run,[11,7])
        with self.assertRaises(Error):verify_program(self.wrap(body.replace('BEFORE','let c=p.new(8);drop(->c);'),helper))
        with self.assertRaises(Error):verify_program(source.replace('make(&mut p)','make(p)'))

    def test_owned_child_roundtrip_and_join_result(self):
        helper='async fn relay(a:->Int)-><-Int{yield;return <-a;}'
        for wait in ('let a=relay(->first).await;',
                     'let h=runtime::spawn(->relay(->first));let result=h.await;let a=match result{Ok(v)=>{<-v},Err(_)=>{return 99;}};'):
            body=f'let mut p=pool<Int>(1);let first=p.new(7);{wait}print(*a);drop(->a);let b=p.new(9);return *b;'
            with self.subTest(wait=wait):
                run=self.run_native(self.wrap(body,helper));self.assertEqual(run.stdout,'7\n9\n');self.assert_destroyed(run,[7,9])

    def test_pool_does_not_escape_with_returned_allocation(self):
        helpers='''fn make(p:&mut Pool<Int>)-><-Int{let a=p.new(7);return <-a;}
          async fn child(p:&mut Pool<Int>)-><-Int{return <-p.new(7);}
          async fn relay(a:->Int)-><-Int{return <-a;}'''
        bodies=(
            'let a=p.new(7);return <-a;',
            'return <-p.new(7);',
            'let a=make(&mut p);return <-a;',
            'let a=child(&mut p).await;return <-a;',
            'let first=p.new(7);let a=relay(->first).await;return <-a;',
            'let h=runtime::spawn(->child(&mut p));let result=h.await;let a=match result{Ok(v)=>{<-v},Err(_)=>{return <-p.new(8);}};return <-a;',
        )
        for body in bodies:
            source=helpers+'async fn work()-><-Int{let mut p=pool<Int>(2);'+body+'}'
            with self.subTest(body=body),self.assertRaisesRegex(Error,'pool local|source.*survit'):
                verify_program(source)

    def test_parent_pool_allows_transfer_and_inner_pool_does_not(self):
        body='let mut p=pool<Int>(1);let a={let value=p.new(7);yield;<-value};return *a;'
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7])
        invalids=(
            'let a={let mut p=pool<Int>(1);let value=p.new(7);yield;<-value};return *a;',
            'let a=loop{let mut p=pool<Int>(1);let value=p.new(7);break <-value;};return *a;',
            'let mut p=pool<Int>(1);let mut a=p.new(1);{let mut q=pool<Int>(1);a=q.new(7);}return *a;',
        )
        for body in invalids:
            with self.subTest(body=body),self.assertRaisesRegex(Error,'pool local'):
                verify_program(self.wrap(body))

    def test_inner_scope_task_and_join_cannot_escape_pool(self):
        helper='async fn relay(a:->Int)-><-Int{yield;return <-a;}'
        body='''let task={let mut p=pool<Int>(1);let a=p.new(7);let task=relay(->a);<-task};
          let a=task.await;return *a;'''
        with self.assertRaises(Error):verify_program(self.wrap(body,helper))
        body='''let result={let mut p=pool<Int>(1);let a=p.new(7);let h=runtime::spawn(->relay(->a));
          let result=h.await;<-result};match result{Ok(a)=>{return *a;},Err(_)=>{return 99;}}'''
        with self.assertRaisesRegex(Error,'pool local'):verify_program(self.wrap(body,helper))

    def test_loop_pool_reinitialization_on_continue_and_break(self):
        body='''let mut i=0;let n=loop{let mut p=pool<Int>(1);let a=p.new(i);
          yield;i=i+1;if i<3{continue;}break *a;};return n;'''
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'2\n');self.assert_destroyed(run,[0,1,2])

    def test_inactive_and_failed_start_do_not_construct_local_pool(self):
        body='let mut p=pool<Int>(1);let a=p.new(7);print(*a);return 42;'
        source=self.wrap(body)
        run=self.run_native(source,fail_at=1);self.assertEqual(run.stdout,'99\n');self.assert_destroyed(run,[])
        inactive=source[:source.index('fn main()')]+'fn main(){let t=work();drop(->t);}'
        run=self.run_native(inactive);self.assertEqual(run.stdout,'');self.assert_destroyed(run,[])

    def test_pool_mutability_transfer_and_capacity(self):
        source=self.wrap('let mut p=pool<Int>(1);let a=p.new(7);return *a;')
        for old,new in (('let mut p','let p'),('let a=p.new(7);','let q=<-p;let a=q.new(7);'),
                        ('let a=p.new(7);','drop(->p);let a=p.new(7);')):
            with self.assertRaises(Error):verify_program(source.replace(old,new))
        invalid=source.replace('return *a;','let b=p.new(8);return *a+*b;')
        run=self.run_c_oracle(compile_source(invalid),expected_error='pool capacity exceeded')
        self.assert_destroyed(run,[])

    def test_replacement_restores_outer_source_before_inner_pool_closes(self):
        body='''let mut p=pool<Int>(2);let mut a=p.new(1);
          {let mut q=pool<Int>(1);a=q.new(7);yield;a=p.new(9);}return *a;'''
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'9\n');self.assert_destroyed(run,[1,7,9])
        with self.assertRaisesRegex(Error,'pool local'):
            verify_program(self.wrap(body.replace('a=p.new(9);','')))

    def test_branch_origin_union_blocks_only_the_local_alternative(self):
        helpers='''async fn work(p:&mut Pool<Int>,flag:Int)-><-Int{
          let mut q=pool<Int>(1);let mut a=p.new(1);if flag==0{a=SOURCE.new(7);}return <-a;}
          fn main(){let mut p=pool<Int>(2);let h=runtime::spawn(->work(&mut p,0));
            match h.join(){Ok(v)=>{print(v);drop(->v);},Err(_)=>{}}}'''
        run=self.run_native(helpers.replace('SOURCE','p'));self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[1,7])
        with self.assertRaisesRegex(Error,'pool local'):verify_program(helpers.replace('SOURCE','q'))

    def test_inactive_child_is_destroyed_before_its_local_source(self):
        helper='async fn child(a:->Int)->Int{yield;return *a;}'
        body='let mut p=pool<Int>(1);let a=p.new(7);let task=child(->a);yield;return 42;'
        run=self.run_native(self.wrap(body,helper));self.assertEqual(run.stdout,'42\n');self.assert_destroyed(run,[7])

    def test_mapping_closed_once_per_iteration_and_final_scope(self):
        body='''let mut root=pool<Int>(1);let outer=root.new(90);let mut i=0;
          while i<3{let mut p=pool<Int>(1);let a=p.new(i);yield;i=i+1;if i<3{continue;}print(*a);}
          return *outer;'''
        code=compile_source(self.wrap(body))
        opening='static Source source_pool_layout(size_t slots, size_t payload_size) {'
        closing='static void source_close(Source *source) {'
        self.assertEqual(code.count(opening),1);self.assertEqual(code.count(closing),1)
        code=code.replace(opening,'static _Atomic int observed_pool_open, observed_pool_close;\n'+opening+'\nobserved_pool_open++;')
        code=code.replace(closing,closing+'\nif(source->pool) observed_pool_close++;')
        code+='''\n__attribute__((destructor)) static void verify_pool_balance(void) {
          if (observed_pool_open != 4 || observed_pool_close != 4) abort();
        }\n'''
        run=self.run_c_oracle(code);self.assertEqual(run.stdout,'2\n90\n');self.assert_destroyed(run,[0,1,2,90])

    def test_native_block_local_pool_and_two_candidate_result_sources(self):
        source='''fn main(){let h=runtime::thread({let mut p=pool<Int>(1);let a=p.new(7);return *a;});
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7])
        helper='''fn choose(p:&mut Pool<Int>,q:&mut Pool<Int>,flag:Int)-><-Int{
          let a=p.new(7);let b=q.new(9);if flag==0{return <-a;}return <-b;}'''
        for flag in (0,1):
            body=f'let mut p=pool<Int>(1);let mut q=pool<Int>(1);let a=choose(&mut p,&mut q,{flag});yield;return *a;'
            run=self.run_native(self.wrap(body,helper));self.assertEqual(run.stdout,f'{7+2*flag}\n')
            self.assert_destroyed(run,[9,7] if flag==0 else [7,9])

    def test_pool_closed_after_early_exit_from_argument(self):
        helper='async fn consume(a:->Int,n:Int)->Int{return *a+n;}'
        body='''let mut p=pool<Int>(1);let a=p.new(7);
          let child=consume(->a,{yield;return 42;});return child.await;'''
        run=self.run_native(self.wrap(body,helper));self.assertEqual(run.stdout,'42\n');self.assert_destroyed(run,[7])

    def test_owned_child_does_not_exclusively_borrow_source(self):
        helper='async fn child(a:->Int)->Int{yield;return *a;}'
        body='''let mut p=pool<Int>(2);let a=p.new(7);let h=runtime::spawn(->child(->a));
          let b=p.new(9);let result=h.await;
          match result{Ok(n)=>{return n+*b;},Err(_)=>{return 99;}}'''
        run=self.run_native(self.wrap(body,helper));self.assertEqual(run.stdout,'16\n');self.assert_destroyed(run,[7,9])


if __name__=='__main__':unittest.main()
