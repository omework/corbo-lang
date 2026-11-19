"""Executable completion effects through nested tasks and handles."""
import unittest
from itertools import product
from pathlib import Path
from crust import compile_source, verify_program
import test_async_field_application as application

BASE = application.BASE


class AsyncChildFieldEffectsTests(unittest.TestCase):
    run_native = application.AsyncFieldApplicationTests.run_native
    run_c_oracle = application.AsyncFieldApplicationTests.run_c_oracle
    refused = application.AsyncFieldApplicationTests.refused
    program = staticmethod(application.AsyncFieldApplicationTests.program)

    def test_direct_named_nested_waits_and_caller_protection(self):
        helpers=BASE+'''async fn first(v:&mut View,n:&Int)->Int{
            let t=update(v,n);yield;return t.await;}
          async fn second(n:&Int,v:&mut View)->Int{let x=first(v,n).await;print(x);return read(v.data);}
          async fn third(v:&mut View,n:&Int)->Int{return second(n,v).await;}'''
        source=self.program('''let h=runtime::spawn(->third(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n9\n')
        for op in ('drop(->b);','b=20;','drop(->a);'):
            self.refused(source.replace('BEFORE',op))
        self.assertEqual(self.run_native(source.replace('BEFORE',''),fail_submission_at=1).stdout,'11\n7\n')

    def test_inactive_child_does_not_publish_effects(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&mut Int)->Int{
          let t=update(v,&*n);yield;drop(->t);n.set(20);return read(v.data);}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}drop(->b);print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source).stdout,'11\n7\n7\n')

    def test_completed_child_keeps_target_reserved_in_parent(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&mut Int)->Int{
          let x=update(v,&*n).await;print(x);BEFORE yield;return read(v.data);}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n9\n')
        self.refused(source.replace('BEFORE','n.set(20);'))

    def test_spawned_child_success_and_submission_failure(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&Int)->Int{
          let h=runtime::spawn(->update(v,n));yield;
          match h.await{Ok(value)=>{print(value);},Err(_)=>{print(99);}}
          return read(v.data);}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n9\n')
        self.assertEqual(self.run_native(source.replace('BEFORE',''),fail_submission_at=2).stdout,'11\n99\n7\n7\n')
        for target in ('a','b'):
            self.refused(source.replace('BEFORE',f'drop(->{target});'))

    def test_task_and_handle_choices_and_loop_exports(self):
        choices=(
            'if flag{let t=update(v,a);<-t}else{let t=update(v,b);<-t}',
            'loop{let t=update(v,a);break <-t;}',
            '{let t=update(v,a);<-t}',
        )
        for launched,choice,flag in product((False,True),choices,('true','false')):
            creation='let t='+choice+';'
            wait=('let h=runtime::spawn(->t);match h.await{Ok(n)=>{print(n);},Err(_)=>{}}'
                  if launched else 'let n=t.await;print(n);')
            helpers=BASE+'''async fn work(v:&mut View,a:&Int,b:&Int,flag:Bool)->Int{
              print(*b);'''+creation+wait+'yield;return read(v.data);}'
            source=self.program('''let h=runtime::spawn(->work(&mut v,&b,&c,'''+flag+'''));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
            expected='11' if choice.startswith('if') and flag=='false' else '9'
            with self.subTest(launched=launched,choice=choice,flag=flag):
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,
                                 '11\n11\n'+(expected+'\n')*3)
                self.refused(source.replace('BEFORE','drop(->b);'))
                if choice.startswith('if'):
                    self.refused(source.replace('BEFORE','drop(->c);'))

    def test_conditional_child_store_and_snapshot_before_wait(self):
        for flag in ('true','false'):
            helpers=BASE+'''async fn maybe(v:&mut View,n:&Int,flag:Bool)->Int{
              if flag{change(v,n);}yield;return read(v.data);}
              async fn work(v:&mut View,n:&Int,flag:Bool)->Int{
                let old=v.data;let t=maybe(v,n,flag);let x=t.await;
                print(x);yield;return read(old)+read(v.data);}'''
            source=self.program('''let h=runtime::spawn(->work(&mut v,&b,'''+flag+'''));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
            self.assertEqual(self.run_native(source).stdout,
                             '11\n'+('9\n16\n9\n' if flag=='true' else '7\n14\n7\n'))

    def test_source_field_and_simultaneous_swap(self):
        helpers='''struct Pair{left:&Int,right:&Int}
          fn swap(v:&mut Pair){let old=v.left;v.left=v.right;v.right=&*old;}
          fn read(n:&Int)->Int{let p=Pair{left:&*n,right:&*n};return *p.left;}
          async fn child(v:&mut Pair)->Int{swap(v);yield;return read(v.left);}
          async fn work(v:&mut Pair)->Int{let n=child(v).await;print(n);return read(v.right);}'''
        source=helpers+'''fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
          let mut v=Pair{left:&a,right:&b};let h=runtime::spawn(->work(&mut v));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.left);print(*v.right);}'''
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'9\n7\n9\n7\n')
        for target in ('a','b'):
            self.refused(source.replace('BEFORE',f'drop(->{target});'))

    def test_void_completion_and_native_child(self):
        helpers=BASE+'''async fn write(v:&mut View,n:&Int){change(v,n);yield;}
          async fn work(v:&mut View,n:&Int)->Int{write(v,n).await;return read(v.data);}
          async fn native(v:&mut View,n:&Int)->Int{
            let h=runtime::thread({->(v,n);change(v,n);return *v.data;});
            return match h.await{Ok(value)=>{value},Err(_)=>{0}};}'''
        for name in ('work','native'):
            source=self.program('let h=runtime::spawn(->'+name+'''(&mut v,&b));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
            with self.subTest(name=name):
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
                self.refused(source.replace('BEFORE','drop(->b);'))

    def test_nested_completion_does_not_promote_short_lived_target(self):
        helpers=BASE+'async fn relay(v:&mut View,n:&Int)->Int{return update(v,n).await;}'
        source=helpers+'''fn main(){let mut p=pool<Int>(1);let a=p.new(7);let mut v=View{data:&a};
          {let mut q=pool<Int>(1);let b=q.new(9);let h=runtime::spawn(->relay(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}print(*v.data);}'''
        self.refused(source)

    def test_recorded_void_child_counterexample(self):
        source=(Path(__file__).resolve().parents[1]/'validation/counterexample-async-void-child-field-effect.crb').read_text()
        self.refused(source)
        self.assertEqual(self.run_native(source.replace('drop(->b);','')).stdout,'11\n9\n9\n')
        compiler=verify_program(source.replace('drop(->b);',''))
        self.assertTrue(compiler.async_structure_effects['work'].structure_fields)

    def test_independent_nested_retention_model(self):
        accepted=rejected=0
        for mode,carrier_dead,target in product(('inactive','direct','spawned'),(False,True),('a','b')):
            # Independent state set: a launched parent may itself fail. Once
            # it completes, an inactive child leaves a; an awaited writer leaves b.
            possible_fields={'a'} if mode=='inactive' else {'a','b'}
            allowed=carrier_dead or target not in possible_fields
            body={'inactive':'let t=update(v,n);drop(->t);',
                  'direct':'let value=update(v,n).await;print(value);',
                  'spawned':'let h=runtime::spawn(->update(v,n));match h.await{Ok(value)=>{print(value);},Err(_)=>{}}'}[mode]
            helpers=BASE+'async fn work(v:&mut View,n:&Int)->Int{'+body+'return read(v.data);}'
            source=self.program('''let h=runtime::spawn(->work(&mut v,&b));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}'''+
              ('drop(->v);' if carrier_dead else '')+f'drop(->{target});'+
              ('' if carrier_dead else 'print(*v.data);'),helpers)
            with self.subTest(mode=mode,carrier_dead=carrier_dead,target=target):
                if allowed:
                    current='7' if mode=='inactive' else '9'
                    self.assertEqual(self.run_native(source).stdout,'11\n'+
                                     ('' if mode=='inactive' else '9\n')+current+'\n'+
                                     ('' if carrier_dead else current+'\n'))
                    accepted+=1
                else:
                    self.refused(source)
                    rejected+=1
        self.assertEqual((accepted,rejected),(7,5))


if __name__=='__main__':unittest.main()
