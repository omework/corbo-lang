"""Named pool loans retain root capability, source and lexical lifetime."""
from pathlib import Path
import unittest
from crust import Error,verify_program
import test_native_blocks as native


class AsyncPoolAliasTests(unittest.TestCase):
    run_c_oracle=native.NativeBlockTests.run_c_oracle
    run_native=native.NativeBlockTests.run_native
    assert_destroyed=native.NativeBlockTests.assert_destroyed
    helpers='''fn make(p:&mut Pool<Int>,n:Int)-><-Int{let a=p.new(n);return <-a;}
      fn inspect(p:&Pool<Int>)->Int{return 42;}
      async fn child(p:&mut Pool<Int>)-><-Int{yield;return <-p.new(7);}
      async fn see(p:&Pool<Int>)->Int{yield;return 42;}'''

    @classmethod
    def wrap(cls,body):
        return cls.helpers+'''async fn work()->Int{let mut p=pool<Int>(3);'''+body+'''}
          fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_case(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-local-pool-alias.crb').read_text()
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7])

    def test_named_pool_direct_creation_helper_and_last_use(self):
        body='''let memory:&mut Pool<Int>=&mut p;let a=memory.new(7);yield;
          let b=make(memory,9);let c=p.new(11);return *a+*b+*c;'''
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'27\n');self.assert_destroyed(run,[11,9,7])
        invalid=body.replace('let b=make(memory,9);','let conflicting=p.new(1);drop(->conflicting);let b=make(memory,9);')
        with self.assertRaises(Error):verify_program(self.wrap(invalid))

    def test_shared_aliases_and_readonly_task_coexist(self):
        body='''let a=&p;let b=&p;let t=see(a);let u=see(b);
          let n=t.await;let m=u.await;let v=p.new(n+m);return *v;'''
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'84\n');self.assert_destroyed(run,[84])
        invalid=body.replace('let m=u.await;','let bad=p.new(1);drop(->bad);let m=u.await;')
        with self.assertRaises(Error):verify_program(self.wrap(invalid))

    def test_mutable_alias_conflicts_and_reference_levels(self):
        body='let memory=&mut p;BEFORE let a=make(memory,7);return *a;'
        for conflict in ('let other=&mut p;let x=make(other,1);drop(->x);',
                         'let other=&p;print(inspect(other));',
                         'let wrong=&mut memory;', 'let wrong=&memory;'):
            with self.subTest(conflict=conflict),self.assertRaises(Error):verify_program(self.wrap(body.replace('BEFORE',conflict)))
        # A dead alias does not freeze the source to the end of its block.
        run=self.run_native(self.wrap('let memory=&mut p;let a=make(memory,7);drop(->a);let second=&mut p;let b=make(second,9);return *b;'))
        self.assertEqual(run.stdout,'9\n');self.assert_destroyed(run,[7,9])

    def test_alias_modes_annotations_and_immutable_source(self):
        valid=self.wrap('let memory:&mut Pool<Int>=&mut p;let a=memory.new(7);return *a;')
        for old,new in (('&mut Pool<Int>=&mut p','&Pool<Int>=&p'),
                        ('&mut Pool<Int>=&mut p','&mut Pool<String>=&mut p'),
                        ('let mut p=pool<Int>','let p=pool<Int>'),
                        ('memory.new(7)','make(&mut memory,7)')):
            with self.subTest(new=new),self.assertRaises(Error):verify_program(valid.replace(old,new))
        with self.assertRaises(Error):verify_program(self.wrap('let memory=&p;let child=&mut *memory;return inspect(memory);'))

    def test_nested_reborrows_suspend_parent_until_last_use(self):
        body='''let memory=&mut p;let inner=&mut *memory;let a=make(inner,7);
          let b=make(memory,9);return *a+*b;'''
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'16\n');self.assert_destroyed(run,[9,7])
        with self.assertRaises(Error):verify_program(self.wrap(body.replace('let a=make(inner,7);','let conflict=make(memory,1);drop(->conflict);let a=make(inner,7);')))
        shared='let memory=&mut p;let inner=&*memory;let n=inspect(inner);let a=make(memory,n);return *a;'
        run=self.run_native(self.wrap(shared));self.assertEqual(run.stdout,'42\n');self.assert_destroyed(run,[42])

    def test_task_keeps_root_reserved_after_alias_last_use(self):
        body='''let memory=&mut p;let t=child(memory);BEFORE
          let a=t.await;let b=p.new(9);return *a+*b;'''
        run=self.run_native(self.wrap(body.replace('BEFORE','')));self.assertEqual(run.stdout,'16\n');self.assert_destroyed(run,[9,7])
        for operation in ('let b=p.new(9);drop(->b);','let again=&mut p;let b=make(again,9);drop(->b);'):
            with self.assertRaises(Error):verify_program(self.wrap(body.replace('BEFORE',operation)))

    def test_task_can_outlive_alias_binding_but_not_pool(self):
        body='''let t={let memory=&mut p;let t=child(memory);<-t};let a=t.await;return *a;'''
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7])
        with self.assertRaises(Error):verify_program(self.wrap(body.replace('let a=t.await;',
            'let conflict=p.new(9);drop(->conflict);let a=t.await;')))
        with self.assertRaises(Error):verify_program(self.wrap(body.replace('let t={','let t={let mut q=pool<Int>(1);').replace('let memory=&mut p','let memory=&mut q')))

    def test_alias_origin_cannot_escape_by_creation_helper_or_child(self):
        for creation in ('memory.new(7)','make(memory,7)','child(memory).await'):
            source=self.helpers+f'''async fn bad()-><-Int{{let mut p=pool<Int>(1);
              let memory=&mut p;let a={creation};return <-a;}}'''
            with self.subTest(creation=creation),self.assertRaisesRegex(Error,'pool local'):verify_program(source)

    def test_native_capture_consumes_alias_and_reserves_pool(self):
        body='''let memory=&mut p;let h=runtime::thread({->(memory);let a=memory.new(7);return *a;});
          BEFORE let result=h.await;AFTER match result{Ok(n)=>{let b=p.new(n);return *b;},Err(_)=>{return 99;}}'''
        source=self.wrap(body.replace('BEFORE','').replace('AFTER',''))
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7,7])
        for where,text in (('BEFORE','let b=p.new(9);drop(->b);'),
                           ('AFTER','let b=memory.new(9);drop(->b);')):
            with self.assertRaises(Error):verify_program(self.wrap(body.replace(where,text).replace('BEFORE','').replace('AFTER','')))

    def test_reborrowed_injected_pool_result_does_not_retain_other_source(self):
        source='''async fn work(p:&mut Pool<Int>,q:&mut Pool<Int>)-><-Int{
          let memory=&mut *p;let other=q.new(8);drop(->other);return <-memory.new(7);}
          fn main(){let mut p=pool<Int>(1);let a={let mut q=pool<Int>(1);
            let h=runtime::spawn(->work(&mut p,&mut q));
            let result=match h.join(){Ok(a)=>{<-a},Err(_)=>{return;}};<-result};print(a);drop(->a);}'''
        run=self.run_native(source);self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[8,7])
        with self.assertRaises(Error):verify_program(source.replace('let memory=&mut *p','let memory=&mut *q').replace('let other=q.new','let other=p.new'))

    def test_prepared_pool_argument_protects_source_during_following_argument(self):
        body='let memory=&mut p;let a=make(memory,{yield;EFFECT 7});return *a;'
        run=self.run_native(self.wrap(body.replace('EFFECT','')));self.assertEqual(run.stdout,'7\n');self.assert_destroyed(run,[7])
        for effect in ('let b=p.new(9);drop(->b);','let b=memory.new(9);drop(->b);'):
            with self.assertRaises(Error):verify_program(self.wrap(body.replace('EFFECT',effect)))

    def test_collection_alias_sources_and_reuse(self):
        for typ,edit,read,expected in (
            ('String','a.push_str("été");','print(&a[..]);','été\n'),
            ('Vector<Int>','a.push(7);','print(a[0]);','7\n'),
            ('Vector<u8>','a.push(255);','print(a[0] as Int);','255\n')):
            source=f'''async fn make(p:&mut Pool<{typ}>)-><-{typ}{{
              let memory=&mut *p;let mut a=memory.new();{edit}yield;return <-a;}}
              async fn work()->Int{{let mut p=pool<{typ}>(1);let memory=&mut p;
                let a=make(memory).await;{read}drop(->a);let b=p.new();drop(->b);return 42;}}
              fn main(){{let h=runtime::spawn(->work());match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}}}'''
            with self.subTest(typ=typ):
                run=self.run_native(source);self.assertEqual(run.stdout,expected+'42\n')
                self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()),2)
                bad=f'''async fn bad()-><-{typ}{{let mut p=pool<{typ}>(1);
                  let memory=&mut p;return <-memory.new();}}'''
                with self.assertRaisesRegex(Error,'pool local'):verify_program(bad)

    def test_alias_loop_releases_each_iteration(self):
        body='''let mut i=0;let result=loop{let memory=&mut p;let t=child(memory);
          let a=t.await;yield;let n=*a;drop(->a);i=i+1;
          if i<3{continue;}break n;};let last=p.new(9);return result+*last;'''
        run=self.run_native(self.wrap(body));self.assertEqual(run.stdout,'16\n')
        self.assert_destroyed(run,[7,7,7,9])


if __name__=='__main__':unittest.main()
