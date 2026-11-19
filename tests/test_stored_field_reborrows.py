"""ST11-ST13: storing an indirect reborrow retains its mutable capability."""
from pathlib import Path
import unittest
from crust import Error, verify_program, compile_source
import test_native_blocks as native


class StoredFieldReborrowTests(unittest.TestCase):
    run_native = native.NativeBlockTests.run_native
    run_c_oracle = native.NativeBlockTests.run_c_oracle

    def refused(self, source, **options):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaises(Error): check(source, **options)

    @staticmethod
    def program(initializer='&*writer.data', use='print(*v.data);', helpers='', async_result=False):
        consume = ('let h=runtime::spawn(->work(&v));'
                   'let r=match h.join(){Ok(n)=>{n},Err(_)=>{return;}};'
                   'drop(->v);USE print(r);drop(->writer);print(data);' if async_result else
                   'USE drop(->v);drop(->writer);print(data);')
        return f'''struct Writer{{data:&mut Int,spare:Int}}
          struct View{{data:&Int}}
          {helpers}
          async fn work(v:&View)->&Int{{yield;return v.data;}}
          fn main(){{let mut memory=pool<Int>(1);let mut data=memory.new(7);
            let mut writers=pool<Writer>(1);let mut writer=writers.new(data:&mut data,spare:3);
            let mut views=pool<View>(1);let v=views.new(data:{initializer});
            {consume.replace('USE',use)}}}'''

    def test_recorded_case_and_original_carrier_protection(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-struct-field-reborrow-stored-shared.crb').read_text()
        run=self.run_native(source)
        self.assertEqual(run.stdout,'7\n7\n')
        self.assertEqual(run.stderr.splitlines(), ['destroy v=View','reclaim v',
                         'destroy writer=Writer','reclaim writer','destroy data=7','reclaim data'])
        failed=self.run_native(source,fail_at=1)
        self.assertEqual(failed.stdout,'')
        self.assertEqual(failed.stderr,run.stderr)
        self.refused(source.replace('print(r);drop(->writer);','drop(->writer);print(r);'))
        self.refused(source.replace('drop(->v);print(r);','drop(->v);data=9;print(r);'))
        for source_name in ('writers','memory'):
            self.refused(source.replace('drop(->v);print(r);',f'drop(->v);{source_name}.reset();print(r);'),
                         allow_legacy_reset=True)

    def test_direct_and_named_shared_construction(self):
        for named in (False, True):
            source=self.program('&*parent' if named else '&*writer.data')
            if named: source=source.replace('let mut views=', 'let mut parent=&mut *writer.data;let mut views=')
            self.assertEqual(self.run_native(source).stdout,'7\n7\n')
            for conflict in ('drop(->writer);','drop(->data);','data=9;',
                             'let mut conflict=&mut *writer.data;conflict.set(9);'):
                self.refused(source.replace('print(*v.data);',conflict+'print(*v.data);'))
            if named: self.refused(source.replace('print(*v.data);','parent.set(9);print(*v.data);'))

    def test_async_and_native_results_preserve_original_reservation(self):
        for native_thread in (False, True):
            source=self.program(use='writer.spare=9;print(writer.spare);',async_result=True)
            if native_thread:
                source=source.replace('let h=runtime::spawn(->work(&v));',
                                      'let view=&v;let h=runtime::thread({->(view);return view.data;});')
            self.assertEqual(self.run_native(source).stdout,'9\n7\n7\n')
            self.refused(source.replace('writer.spare=9;', 'drop(->writer);'))
            self.refused(source.replace('writer.spare=9;', 'let mut conflict=&mut *writer.data;conflict.set(9);'))

    def test_sync_helpers_methods_and_relay_into_constructor(self):
        helpers='''fn target(w:&mut Writer)->&mut Int{return &mut *w.data;}
          fn relay(w:&mut Writer)->&mut Int{return target(w);}
          fn shared(w:&Writer)->&Int{return &*w.data;}
          impl Writer{fn target(self:&mut Writer)->&mut Int{return &mut *self.data;}}'''
        for call in ('target(&mut writer)','relay(&mut writer)','writer.target()','shared(&writer)'):
            source=self.program('&*parent', helpers=helpers, use='', async_result=True)
            source=source.replace('let mut views=',f'let mut parent={call};let mut views=')
            self.assertEqual(self.run_native(source).stdout,'7\n7\n')
            self.refused(source.replace('print(r);drop(->writer);','drop(->writer);print(r);'))

    def test_mutable_field_stored_and_reborrowed(self):
        source=self.program('&mut *parent',use='let mut r=&mut *v.data;r.set(19);print(r);')
        source=source.replace('struct View{data:&Int}', 'struct View{data:&mut Int}')
        source=source.replace('return v.data;', 'return &*v.data;')
        source=source.replace('let mut views=', 'let mut parent=&mut *writer.data;let mut views=')
        source=source.replace('let v=views.new','let mut v=views.new')
        self.assertEqual(self.run_native(source).stdout,'19\n19\n')
        self.refused(source.replace('r.set(19);','parent.set(9);r.set(19);'))
        self.refused(source.replace('r.set(19);','drop(->v);r.set(19);'))
        self.refused(source.replace('r.set(19);','drop(->writer);r.set(19);'))

    def test_no_promotion_of_original_carrier(self):
        source='''struct Writer{data:&mut Int} struct View{data:&Int}
          fn main(){let mut memory=pool<Int>(1);let mut data=memory.new(7);
            let mut views=pool<View>(1);
            let v={let mut writers=pool<Writer>(1);let mut writer=writers.new(data:&mut data);
              let v=views.new(data:&*writer.data);<-v};print(*v.data);}'''
        self.refused(source)

    def test_returned_and_copied_shared_container_keeps_capability(self):
        helpers='''fn make(p:&mut Pool<View>,w:&mut Writer)-><-A<View>{
          let v=p.new(data:&*w.data);return <-v;}'''
        source=self.program(helpers=helpers, use='', async_result=True)
        source=source.replace('views.new(data:&*writer.data)', 'make(&mut views,&mut writer)')
        self.assertEqual(self.run_native(source).stdout,'7\n7\n')
        self.refused(source.replace('print(r);drop(->writer);','drop(->writer);print(r);'))
        source=self.program(use='let copied=copy(v);drop(->v);print(*copied.data);drop(->copied);')
        source=source.replace('pool<View>(1)', 'pool<View>(2)')
        source=source.replace('drop(->copied); drop(->v);', 'drop(->copied);')
        self.assertEqual(self.run_native(source).stdout,'7\n7\n')
        self.refused(source.replace('print(*copied.data);','drop(->writer);print(*copied.data);'))

    def test_original_slot_reusable_only_after_last_result_use(self):
        source=self.program(use='',async_result=True)
        reuse='drop(->writer);let replacement=writers.new(data:&mut data,spare:8);print(replacement.spare);drop(->replacement);'
        source=source.replace('drop(->writer);',reuse)
        self.assertEqual(self.run_native(source).stdout,'7\n8\n7\n')
        self.refused(source.replace('print(r);'+reuse,reuse+'print(r);'))


if __name__=='__main__': unittest.main()
