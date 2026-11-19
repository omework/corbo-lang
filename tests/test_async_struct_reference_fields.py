"""Transitive storage and exclusivity for reference-bearing task captures."""
from pathlib import Path
import unittest

from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncStructReferenceFieldTests(unittest.TestCase):
    run_c_oracle = native.NativeBlockTests.run_c_oracle
    run_native = native.NativeBlockTests.run_native

    @staticmethod
    def program(body='yield;return *v.data;', *, mutable=False, main='', helpers=''):
        mode = '&mut' if mutable else '&'
        return f'''struct View{{before:Int,data:{mode} Int,after:Int}}
          {helpers} async fn work(v:{mode} View)->Int{{{body}}}
          fn main(){{let mut memory=pool<Int>(2);let mut data=memory.new(7);
            let mut v=View{{before:2,data:{mode} data,after:3}};
            {main or f'let h=runtime::spawn(->work({mode} v));match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}print(data);'} }}'''

    def assert_refused(self, source, pattern=None, **options):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__):
                if pattern:
                    with self.assertRaisesRegex(Error, pattern):check(source, **options)
                else:
                    with self.assertRaises(Error):check(source, **options)

    def test_recorded_case_and_mixed_offsets(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(self.run_native((root/'validation/open-async-struct-reference-field.crb').read_text()).stdout,'7\n')
        for mutable in (False, True):
            source=self.program('yield;return v.before+*v.data+v.after;',mutable=mutable)
            self.assertEqual(self.run_native(source).stdout,'12\n7\n')

    def test_transitive_reservation_before_and_after_launch(self):
        for mutable in (False, True):
            mode='&mut' if mutable else '&'
            main=f'''let t=work({mode} v);BEFORE let h=runtime::spawn(->t);
              DURING match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}
              data=11;print(data);'''
            base=self.program(mutable=mutable,main=main)
            self.assertEqual(self.run_native(base.replace('BEFORE','').replace('DURING','')).stdout,'7\n11\n')
            for at in ('BEFORE','DURING'):
                operations=['data=9;', 'drop(->data);', 'drop(->v);']
                if mutable:operations.append('print(data);')
                for op in operations:
                    with self.subTest(mutable=mutable,at=at,op=op):
                        self.assert_refused(base.replace(at,op).replace('BEFORE','').replace('DURING',''))

    def test_shared_tasks_and_shared_caller(self):
        source=self.program(main='''let a=work(&v);let b=work(&v);print(data);
          let h=runtime::spawn(->a);match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          BEFORE let k=runtime::spawn(->b);match k.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          data=11;print(data);''')
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'7\n7\n7\n11\n')
        self.assert_refused(source.replace('BEFORE','data=9;'))

    def test_helpers_methods_and_mutable_pointee(self):
        source=self.program('let n=v.read();yield;write(v,n+1);v.after=4;return *v.data+v.after;',mutable=True,
          helpers='''fn write(v:&mut View,n:Int){let mut target=&mut *v.data;*target=n;}
            impl View{fn read(self:&View)->Int{return self.before+*self.data+self.after;}}''')
        self.assertEqual(self.run_native(source).stdout,'17\n13\n')
        # Read-only access to the carrier cannot manufacture mutable access to its field.
        self.assert_refused(source.replace('fn write(v:&mut View','fn write(v:&View'))

    def test_alias_relay_and_root_after_alias_scope(self):
        source=self.program('''let child={let mut alias=&mut *v;let t=leaf(alias);<-t};
          BEFORE yield;let n=child.await;v.after=n;return v.after;''',mutable=True,
          helpers='async fn leaf(v:&mut View)->Int{yield;return *v.data+v.before;}')
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'9\n7\n')
        self.assert_refused(source.replace('BEFORE','print(*v.data);'))
        self.assert_refused(source.replace('BEFORE','v.after=99;'))

    def test_pool_reuse_only_after_wait_and_drop(self):
        source=self.program(main='''let h=runtime::spawn(->work(&v));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          address(data);drop(->v);drop(->data);let replacement=memory.new(19);
          address(replacement);print(replacement);''').replace('pool<Int>(2)','pool<Int>(1)')
        run=self.run_native(source)
        result,old,new,value=run.stdout.splitlines()
        self.assertEqual((result,new,value),('7',old,'19'))
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy v=View','destroy data=7','destroy replacement=19'])

    def test_inactive_drop_and_launch_failure_release_targets(self):
        source=self.program('print(99);yield;return *v.data;',mutable=True,
          main='let t=work(&mut v);drop(->t);data=11;print(data);')
        self.assertEqual(self.run_native(source).stdout,'11\n')
        source=self.program('print(99);yield;return *v.data;',mutable=True,
          main='''let h=runtime::spawn(->work(&mut v));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(77);}}data=11;print(data);''')
        run=self.run_native(source,fail_at=1)
        self.assertEqual(run.stdout,'77\n11\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy v=View','destroy data=11'])

    def test_native_thread_field_dereference(self):
        for mutable in (False,True):
            mode='&mut' if mutable else '&'
            source=self.program(mutable=mutable,main=f'''let view={mode} v;
              let h=runtime::thread({{->(view);return *view.data+view.after;}});
              match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}data=11;print(data);''')
            self.assertEqual(self.run_native(source).stdout,'10\n11\n')

    def test_escape_and_legacy_reset(self):
        source='''struct View{data:&Int} async fn work(v:&View)->Int{yield;return *v.data;}
          fn main(){let t={let mut memory=pool<Int>(1);let data=memory.new(7);
            let v=View{data:&data};let t=work(&v);<-t};drop(->t);}'''
        self.assert_refused(source)
        base=self.program(main='''let h=runtime::spawn(->work(&v));BEFORE
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}memory.reset();''')
        self.assert_refused(base.replace('BEFORE','memory.reset();'),allow_legacy_reset=True)
        # Compatibility-only validation: reset is still absent from the public prototype.
        code=compile_source(base.replace('BEFORE',''),allow_legacy_reset=True)
        self.assertEqual(self.run_c_oracle(code).stdout,'7\n')

    def test_type_and_dependency_update_boundaries(self):
        for body in ('return v.data;', 'v.data=4;return 0;', 'return *v.before;'):
            self.assert_refused(self.program(body,mutable=True))
        source=self.program('replace(v,p);return *v.data;',mutable=True,
          helpers='fn replace(v:&mut View,p:&mut Int){v.data=&mut *p;}')
        # ST10/ST12: completion now propagates mutable-field replacements.
        # The new target stays reserved while the execution is outstanding.
        source=source.replace('work(v:&mut View)','work(v:&mut View,p:&mut Int)')
        source=source.replace('let h=runtime::spawn(->work(&mut v));',
                              'let mut other=memory.new(9);let h=runtime::spawn(->work(&mut v,&mut other));')
        verify_program(source)
        self.assertEqual(self.run_native(source).stdout,'9\n7\n')
        self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'7\n')
        self.assert_refused(source.replace('match h.join()', 'other=20;match h.join()'),
                            'emprunt actif')

    def test_distinct_and_aliased_arguments(self):
        source=self.program('increment(other);yield;return *v.data;',
          helpers='fn increment(n:&mut Int){*n=*n+1;}')
        source=source.replace('work(v:& View)', 'work(v:& View,other:&mut Int)')
        source=source.replace('let h=runtime::spawn(->work(& v));',
            'let mut other=memory.new(19);let h=runtime::spawn(->work(& v,&mut other));')
        self.assertEqual(self.run_native(source).stdout,'7\n7\n')
        self.assert_refused(source.replace('work(& v,&mut other)','work(& v,&mut data)'))

    def test_multiple_reference_fields_and_loops(self):
        source='''struct View{head:Int,first:&Int,middle:Int,data:&mut Int,tail:Int}
          fn read(v:&View)->Int{return v.head+*v.first+v.middle+*v.data+v.tail;}
          async fn work(v:&mut View)->Int{let mut n=0;loop{yield;n=n+1;
            if n<2{continue;}break;}v.tail=4;return read(v);}
          fn main(){let mut p=pool<Int>(2);let a=p.new(7);let mut b=p.new(11);
            let mut v=View{head:1,first:&a,middle:2,data:&mut b,tail:3};
            let h=runtime::spawn(->work(&mut v));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_native(source).stdout,'25\n')



if __name__=='__main__':unittest.main()
