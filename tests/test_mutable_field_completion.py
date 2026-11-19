"""Mutable field replacements retain targets and field capabilities separately."""
import unittest
from itertools import product
from crust import verify_program,compile_source
import test_async_field_application as application

BASE='''struct Writer{data:&mut Int}
 fn change(v:&mut Writer,n:&mut Int){v.data=&mut *n;}
'''
def task(body,result='Int'):
    return BASE+'async fn work(v:&mut Writer,n:&mut Int)->'+result+'{'+body+'}'

class MutableFieldCompletionTests(unittest.TestCase):
    run_native=application.AsyncFieldApplicationTests.run_native
    run_c_oracle=application.AsyncFieldApplicationTests.run_c_oracle
    refused=application.AsyncFieldApplicationTests.refused

    @staticmethod
    def program(body,helpers):
        return helpers+'''fn main(){let mut p=pool<Int>(2);let mut a=p.new(7);let mut b=p.new(9);
          let mut v=Writer{data:&mut a};'''+body+'}'

    def test_direct_and_helper_store_then_reborrow(self):
        for store in ('change(v,n);','v.data=&mut *n;'):
            helpers=task(store+'yield;let mut r=&mut *v.data;r.set(21);return *r;')
            source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);drop(->v);print(a);print(b);''',helpers)
            with self.subTest(store=store):
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'21\n21\n7\n21\n')
                self.assertEqual(self.run_native(source.replace('BEFORE',''),fail_submission_at=1).stdout,'7\n7\n9\n')
                for operation in ('print(b);','b=30;','drop(->b);'):
                    self.refused(source.replace('BEFORE',operation))

    def test_new_target_access_blocked_inside_task(self):
        for store in ('change(v,n);','v.data=&mut *n;'):
            helpers=task(store+'BEFORE yield;return *v.data;')
            source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
            self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'9\n9\n')
            for op in ('print(*n);','n.set(20);'):
                self.refused(source.replace('BEFORE',op))

    def test_returned_mutable_and_shared_reborrows_reserve_field(self):
        for mode,ret,use,expected in (('&mut Int','&mut *v.data','r.set(21);print(*r);','21'),
                                      ('&Int','&*v.data','print(*r);','9')):
            helpers=task('v.data=&mut *n;yield;return '+ret+';',mode)
            source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
              match h.join(){Ok(r)=>{BEFORE '''+use+'''},Err(_)=>{}}print(*v.data);''',helpers)
            self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,expected+'\n'+expected+'\n')
            for op in ('print(*v.data);','print(b);','b=30;'):
                self.refused(source.replace('BEFORE',op))

    def test_child_wait_and_factory(self):
        helpers=task('v.data=&mut *n;yield;return *v.data;')+'''
          async fn parent(v:&mut Writer,n:&mut Int)->Int{let result=work(v,n).await;
            print(result);let mut r=&mut *v.data;r.set(21);return *r;}
          fn make(v:&mut Writer,n:&mut Int)-><-runtime::Handle<Int>{
            let h=runtime::spawn(->parent(v,n));return <-h;}'''
        source=self.program('''let h=make(&mut v,&mut b);
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'9\n21\n21\n')
        self.refused(source.replace('BEFORE','print(b);'))

    def test_named_reborrow_blocks_replacement_until_last_use(self):
        helpers=task('v.data=&mut *n;let mut r=&mut *v.data;yield;BEFORE r.set(21);print(*r);return *v.data;')
        source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'21\n21\n21\n')
        self.refused(source.replace('BEFORE','print(*v.data);'))

    def test_conditional_store_retains_every_target(self):
        helpers=BASE+'''async fn work(v:&mut Writer,n:&mut Int,flag:Bool)->Int{
          if flag{v.data=&mut *n;}yield;let mut r=&mut *v.data;r.set(21);return *r;}'''
        for flag in ('true','false'):
            source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b,'''+flag+'''));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
            self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'21\n21\n')
            self.refused(source.replace('BEFORE','print(b);'))

    def test_conditional_child_completion_does_not_borrow_its_own_field(self):
        helpers=BASE+'''async fn child(v:&mut Writer,n:&mut Int,flag:Bool)->Int{
          if flag{v.data=&mut *n;}yield;return *v.data;}
          async fn work(v:&mut Writer,n:&mut Int,flag:Bool)->Int{
            let result=child(v,n,flag).await;print(result);
            BEFORE let mut r=&mut *v.data;r.set(21);return *r;}'''
        for flag in ('true','false'):
            source=self.program('let h=runtime::spawn(->work(&mut v,&mut b,'+flag+'''));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
            self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,
                             ('9' if flag=='true' else '7')+'\n21\n21\n')
            self.refused(source.replace('BEFORE','print(*n);'))

    def test_legacy_reset_and_pool_reuse(self):
        source=task('v.data=&mut *n;yield;return *v.data;')+'''fn main(){
          let mut p=pool<Int>(1);let mut q=pool<Int>(1);let mut a=p.new(7);let mut b=q.new(9);
          let mut v=Writer{data:&mut a};let h=runtime::spawn(->work(&mut v,&mut b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);
          drop(->v);q.reset();let next=q.new(19);print(next);}'''
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE',''),allow_legacy_reset=True)).stdout,'9\n9\n19\n')
        self.refused(source.replace('BEFORE','q.reset();'),'reset interdit',legacy=True)

    def test_returned_child_reborrow_keeps_target_and_carrier(self):
        helpers=task('v.data=&mut *n;yield;return &mut *v.data;','&mut Int')+'''
          async fn relay(v:&mut Writer,n:&mut Int)->&mut Int{
            let mut r=work(v,n).await;BEFORE r.set(21);yield;return r;}'''
        source=self.program('''let h=runtime::spawn(->relay(&mut v,&mut b));
          match h.join(){Ok(r)=>{print(*r);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'21\n21\n')
        for op in ('print(*n);','print(*v.data);'):
            self.refused(source.replace('BEFORE',op))

    def test_inactive_and_completed_target_model(self):
        accepted=rejected=0
        helpers=task('v.data=&mut *n;yield;return *v.data;')
        for inactive,dead,target in product((False,True),(False,True),('a','b')):
            reserved=set() if dead else {'a'} if inactive else {'a','b'}
            action=('let t=work(&mut v,&mut b);drop(->t);' if inactive else
              'let h=runtime::spawn(->work(&mut v,&mut b));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}')
            source=self.program(action+('drop(->v);' if dead else '')+f'drop(->{target});'+
                                ('' if dead else 'print(*v.data);'),helpers)
            with self.subTest(inactive=inactive,dead=dead,target=target):
                if target in reserved:
                    self.refused(source);rejected+=1
                else:
                    self.assertEqual(self.run_native(source).stdout,('' if inactive else '9\n')+
                                     ('' if dead else '7\n' if inactive else '9\n'));accepted+=1
        self.assertEqual((accepted,rejected),(5,3))

if __name__=='__main__':unittest.main()
