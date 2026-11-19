"""End-to-end shared-reference field replacement by launched tasks."""
from pathlib import Path
from itertools import product
import unittest

from crust import Error, compile_source, verify_program
import test_native_blocks

BASE = '''struct View{data:&Int}
  fn change(v:&mut View,n:&Int){v.data=&*n;}
  fn read(n:&Int)->Int{let local=View{data:&*n};return *local.data;}
  async fn update(v:&mut View,n:&Int)->Int{change(v,n);yield;return *v.data;}
'''


class AsyncFieldApplicationTests(unittest.TestCase):
    run_native = test_native_blocks.NativeBlockTests.run_native
    run_c_oracle = test_native_blocks.NativeBlockTests.run_c_oracle

    def refused(self,source,pattern='emprunt|durable|surviv|raccord|dépendance',legacy=False):
        for stage in (verify_program,compile_source):
            with self.subTest(stage=stage.__name__):
                with self.assertRaisesRegex(Error,pattern) as caught:
                    stage(source,allow_legacy_reset=legacy)
                self.assertNotIn('invariant interne',str(caught.exception))

    @staticmethod
    def program(body, helpers=BASE):
        return helpers+'''fn main(){let mut p=pool<Int>(3);
          let mut a=p.new(7);let mut b=p.new(9);let mut c=p.new(11);
          print(c);let mut v=View{data:&a};'''+body+'}'

    def test_recorded_program_and_launch_failure(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-sync-field-replacement.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'9\n9\n')
        self.assertEqual(self.run_native(source,fail_at=1).stdout,'7\n')

    def test_new_target_is_protected_after_join(self):
        source=self.program('''let h=runtime::spawn(->update(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          BEFORE print(*v.data);drop(->v);drop(->a);drop(->b);''')
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        for op in ('drop(->b);','b=20;','drop(->a);','a=20;'):
            self.refused(source.replace('BEFORE',op))

    def test_inactive_task_applies_no_write_and_releases_slot(self):
        source=self.program('''let t=update(&mut v,&b);drop(->t);drop(->b);
          let replacement=p.new(19);print(replacement);print(*v.data);''')
        result=self.run_native(source)
        self.assertEqual(result.stdout,'11\n19\n7\n')
        self.assertEqual(result.stderr.count('destroy b=9\n'),1)

    def test_short_lived_target_cannot_remain_in_parent_carrier(self):
        prefix='''let mut p=pool<Int>(1);let a=p.new(7);let mut v=View{data:&a};
          {let mut q=pool<Int>(1);let b=q.new(9);'''
        active=BASE+'fn main(){'+prefix+'''let h=runtime::spawn(->update(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}print(*v.data);}'''
        self.refused(active)
        inactive=BASE+'fn main(){'+prefix+'let t=update(&mut v,&b);drop(->t);}print(*v.data);}'
        self.assertEqual(self.run_native(inactive).stdout,'7\n')

    def test_captured_mutable_input_is_reserved_by_stored_shared_reference(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&mut Int)->Int{
          change(v,&*n);yield;BEFORE return *v.data;}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(source.replace('BEFORE','n.set(20);'))

    def test_field_reborrow_after_change_uses_new_cell(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&Int)->Int{
          change(v,n);let r=v.data;yield;return read(r);}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source).stdout,'11\n9\n9\n')

    def test_detached_old_field_keeps_its_cell_after_change(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&Int)->Int{
          let old=v.data;change(v,n);yield;return read(old)+read(v.data);}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source).stdout,'11\n16\n9\n')

    def test_sequential_replacements_and_original_source_cleanup(self):
        helpers=BASE+'''async fn work(v:&mut View,a:&Int,b:&Int)->Int{
          change(v,a);yield;change(v,b);return *v.data;}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b,&c));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}drop(->b);print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source).stdout,'11\n11\n11\n')

    def test_conditional_handle_keeps_both_possible_writes(self):
        for flag in ('true','false'):
            source=self.program('''let flag='''+flag+''';let h=if flag{
              let h=runtime::spawn(->update(&mut v,&b));<-h
            }else{let h=runtime::spawn(->update(&mut v,&c));<-h};
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''')
            expected='9' if flag=='true' else '11'
            self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n'+expected+'\n'+expected+'\n')
            for op in ('drop(->b);','drop(->c);'):
                self.refused(source.replace('BEFORE',op))

    def test_independent_join_retention_model(self):
        accepted=rejected=0
        for inactive,dead_carrier,target in product((False,True),(False,True),('a','b')):
            finish=('let t=update(&mut v,&b);drop(->t);' if inactive else
                    'let h=runtime::spawn(->update(&mut v,&b));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}')
            release='drop(->v);' if dead_carrier else ''
            observe='' if dead_carrier else 'print(*v.data);'
            source=self.program(finish+release+f'drop(->{target});'+observe)
            # Inactive: v retains a only. Joined: launch may have failed, so
            # v retains either a or b until it is destroyed.
            allowed=dead_carrier or inactive and target=='b'
            with self.subTest(inactive=inactive,dead_carrier=dead_carrier,target=target):
                if allowed:
                    self.assertEqual(self.run_native(source).stdout,'11\n'+('' if inactive else '9\n')+('' if dead_carrier else '7\n'))
                    accepted+=1
                else:
                    self.refused(source)
                    rejected+=1
        self.assertEqual((accepted,rejected),(5,3))

    def test_legacy_reset_tracks_new_pool_until_carrier_destruction(self):
        source=BASE+'''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
          let a=p.new(7);let b=q.new(9);let mut v=View{data:&a};
          let h=runtime::spawn(->update(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE
          print(*v.data);drop(->v);q.reset();let next=q.new(19);print(next);}'''
        self.refused(source.replace('BEFORE','q.reset();'),'reset interdit',legacy=True)
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE',''),allow_legacy_reset=True)).stdout,'9\n9\n19\n')

    def test_methods_and_native_threads(self):
        helpers=BASE+'''impl View{fn change(self:&mut View,n:&Int){self.data=&*n;}}
          async fn work(v:&mut View,n:&Int)->Int{v.change(n);yield;return *v.data;}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source).stdout,'11\n9\n9\n')
        native=self.program('''let mut carrier=&mut v;let input=&b;
          let h=runtime::thread({->(carrier,input);change(carrier,input);return *carrier.data;});
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''')
        self.assertEqual(self.run_native(native.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(native.replace('BEFORE','drop(->b);'))

    def test_distinct_concrete_handles_and_match_keep_effects(self):
        helpers=BASE+'async fn other(v:&mut View,n:&Int)->Int{yield;change(v,n);return *v.data;}'
        choices=(
            'if true{let h=runtime::spawn(->update(&mut v,&b));<-h}else{let h=runtime::spawn(->other(&mut v,&c));<-h}',
            'match u8::try_from(1){Ok(n)=>{print(n as Int);let h=runtime::spawn(->update(&mut v,&b));<-h},Err(_)=>{let h=runtime::spawn(->other(&mut v,&c));<-h}}',
        )
        for choice in choices:
            source=self.program('let h='+choice+''';match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
              BEFORE print(*v.data);''',helpers)
            with self.subTest(choice=choice):
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,
                                 '11\n'+('1\n' if choice.startswith('match') else '')+'9\n9\n')
                for target in ('b','c'):
                    self.refused(source.replace('BEFORE',f'drop(->{target});'))

    def test_factory_contract_preserves_pending_effects(self):
        factory=BASE+'''fn make(v:&mut View,n:&Int)-><-runtime::Handle<Int>{
          let h=runtime::spawn(->update(v,n));return <-h;}'''
        checked=verify_program(factory)
        self.assertTrue(checked.function_results['make'].task_field_updates)
        self.assertFalse(checked.function_results['make'].structure_fields)

    def test_enum_match_and_loop_transfers_preserve_pending_writes(self):
        for variant in ('Left','Right'):
            for subject in ('&choice','(->choice)'):
                source=self.program('''let mut choices=pool<Choice>(1);
                  let choice=new(choices) Choice.'''+variant+'''{};
                  let h=match '''+subject+'''{
                    Choice.Left{}=>{let h=runtime::spawn(->update(&mut v,&b));<-h},
                    Choice.Right{}=>{let h=runtime::spawn(->update(&mut v,&c));<-h}};
                  match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',
                  BASE+'enum Choice{Left{},Right{}}')
                with self.subTest(variant=variant,subject=subject):
                    expected='9' if variant=='Left' else '11'
                    self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,
                                     '11\n'+expected+'\n'+expected+'\n')
                    target='b' if variant=='Left' else 'c'
                    other='c' if variant=='Left' else 'b'
                    self.refused(source.replace('BEFORE',f'drop(->{target});'))
                    self.assertEqual(self.run_native(source.replace('BEFORE',f'drop(->{other});')).stdout,
                                     '11\n'+expected+'\n'+expected+'\n')
        source=self.program('''let mut i=0;let h=loop{
          i=i+1;if i<2{continue;}
          let h=runtime::spawn(->update(&mut v,&b));break <-h;};
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''')
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(source.replace('BEFORE','drop(->b);'))

    def test_conditional_stores_preserve_all_target_descriptors(self):
        for flag in ('true','false'):
            for other_branch in ('change(v,b);','print(*b);'):
                helpers=BASE+'''async fn work(v:&mut View,a:&Int,b:&Int,flag:Bool)->Int{
                  if flag{change(v,a);}else{'''+other_branch+'''}
                  yield;return read(v.data);}'''
                source=self.program('''let h=runtime::spawn(->work(&mut v,&b,&c,'''+flag+'''));
                  match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
                expected='9' if flag=='true' else ('11' if other_branch.startswith('change') else '7')
                with self.subTest(flag=flag,other_branch=other_branch):
                    self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,
                                     '11\n'+('11\n' if flag=='false' and other_branch.startswith('print') else '')+
                                     expected+'\n'+expected+'\n')
                    for target in ('a','b') if other_branch.startswith('print') else ('a','b','c'):
                        self.refused(source.replace('BEFORE',f'drop(->{target});'))


if __name__=='__main__':unittest.main()
