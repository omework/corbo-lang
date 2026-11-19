"""Completion writes and borrowed outputs preserve distinct target identities."""
from itertools import product
from pathlib import Path
import unittest
from crust import verify_program,compile_source
import test_async_field_application as application

BASE='''struct View{data:&Int}
 fn change(v:&mut View,n:&Int){v.data=&*n;}
'''
def worker(result='old', store='change(v,n);'):
    return BASE+'''async fn work(v:&mut View,n:&Int)->&Int{
      let old=v.data;print(*old);'''+store+'yield;return '+result+';}'

class BorrowedFieldCompletionTests(unittest.TestCase):
    run_native=application.AsyncFieldApplicationTests.run_native
    run_c_oracle=application.AsyncFieldApplicationTests.run_c_oracle
    refused=application.AsyncFieldApplicationTests.refused
    program=staticmethod(application.AsyncFieldApplicationTests.program)

    def joined(self,body,helpers):
        return self.program('''let h=runtime::spawn(->work(&mut v,&b));
          let r=match h.join(){Ok(view)=>{view},Err(_)=>{&c}};'''+body,helpers)

    def test_old_and_new_result_have_distinct_targets(self):
        for result,discard,retained,expected in (('old','b','a','7'),('v.data','a','b','9')):
            source=self.joined('drop(->v);drop(->'+discard+');print(*r);',worker(result))
            with self.subTest(result=result):
                self.assertEqual(self.run_native(source).stdout,'11\n7\n'+expected+'\n')
                self.refused(source.replace('drop(->'+discard+');','drop(->'+retained+');'))
                self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'11\n11\n')

    def test_stores_retain_new_target_even_with_old_result(self):
        for result in ('old','v.data'):
            source=self.joined('BEFORE print(*r);print(*v.data);',worker(result))
            expected='7' if result=='old' else '9'
            self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n7\n'+expected+'\n9\n')
            for target in ('a','b'):
                self.refused(source.replace('BEFORE',f'drop(->{target});'))

    def test_direct_reference_store_matches_helper(self):
        for result in ('old','v.data'):
            helpers=worker(result,'v.data=&*n;')
            source=self.joined('print(*r);print(*v.data);',helpers)
            self.assertEqual(self.run_native(source).stdout,'11\n7\n'+('7' if result=='old' else '9')+'\n9\n')
            self.refused(source.replace('print(*r);','drop(->b);print(*r);'))

    def test_recorded_child_write_and_borrowed_output(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-completion-result-and-write.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'16\n9\n7\n')
        for target in ('a','b'):
            self.refused(source.replace('print(*view.data);',f'drop(->{target});print(*view.data);'))

    def test_nested_direct_waits_and_returned_snapshot(self):
        for result,discard,expected in (('old','b','7'),('v.data','a','9')):
            helpers=worker(result)+'''async fn middle(n:&Int,v:&mut View)->&Int{
              let r=work(v,n).await;yield;return r;}
              async fn top(v:&mut View,n:&Int)->&Int{return middle(n,v).await;}'''
            source=self.joined('drop(->v);drop(->'+discard+');print(*r);',helpers).replace(
                'runtime::spawn(->work(&mut v,&b))','runtime::spawn(->top(&mut v,&b))')
            self.assertEqual(self.run_native(source).stdout,'11\n7\n'+expected+'\n')
            self.refused(source.replace('drop(->'+discard+');','drop(->'+('a' if discard=='b' else 'b')+');'))

    def test_factory_and_public_handle_relay(self):
        for result,discard,expected in (('old','b','7'),('v.data','a','9')):
            helpers=worker(result)+'''fn make(v:&mut View,n:&Int)-><-runtime::Handle<&Int>{
              let h=runtime::spawn(->work(v,n));return <-h;}
              fn pass(h:->runtime::Handle<&Int>)-><-runtime::Handle<&Int>{return <-h;}'''
            source=self.program('''let h=make(&mut v,&b);let next=pass(->h);
              let r=match next.join(){Ok(view)=>{view},Err(_)=>{&c}};
              drop(->v);drop(->'''+discard+');print(*r);',helpers)
            self.assertEqual(self.run_native(source).stdout,'11\n7\n'+expected+'\n')
            self.refused(source.replace('drop(->'+discard+');','drop(->'+('a' if discard=='b' else 'b')+');'))

    def test_result_and_field_require_independent_pools(self):
        for result,reset,expected in (('old','q','7'),('v.data','p','9')):
            source=worker(result)+'''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
              let a=p.new(7);let b=q.new(9);let mut v=View{data:&a};
              let h=runtime::spawn(->work(&mut v,&b));
              match h.join(){Ok(r)=>{v ->;drop(->v);RESET.reset();print(*r);},Err(_)=>{}}}'''
            self.assertEqual(self.run_c_oracle(compile_source(source.replace('RESET',reset),allow_legacy_reset=True)).stdout,
                             '7\n'+expected+'\n')
            self.refused(source.replace('RESET','p' if reset=='q' else 'q'),'reset interdit',legacy=True)

    def test_mutable_result_independent_of_stored_shared_reference(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&Int,m:&mut Int)->&mut Int{
          v.data=&*n;yield;return m;}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b,&mut c));
          match h.join(){Ok(r)=>{BEFORE r.set(21);print(*r);},Err(_)=>{}}
          print(*v.data);print(c);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n21\n9\n21\n')
        self.refused(source.replace('BEFORE','print(c);'))
        self.refused(source.replace('BEFORE','').replace('print(*v.data);','drop(->b);print(*v.data);'))

    def test_direct_store_keeps_shared_target_reserved(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&mut Int)->&Int{
          let old=v.data;v.data=&*n;BEFORE print(*v.data);yield;return old;}'''
        source=self.joined('print(*r);print(*v.data);',helpers).replace('work(&mut v,&b)','work(&mut v,&mut b)')
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n7\n9\n')
        self.refused(source.replace('BEFORE','n.set(20);'))

    def test_direct_store_refuses_local_target(self):
        helpers=BASE+'''async fn work(v:&mut View)->Int{
          let mut p=pool<Int>(1);let local=p.new(7);v.data=&local;yield;return 1;}'''
        self.refused(helpers,'cible|contrat de terminaison')

    def test_independent_result_and_carrier_model(self):
        accepted=rejected=0
        for old,dead,target in product((False,True),(False,True),('a','b')):
            retained={'a' if old else 'b'}
            if not dead:retained|={'a','b'}
            source=self.joined(('drop(->v);' if dead else '')+f'drop(->{target});print(*r);'+
                               ('' if dead else 'print(*v.data);'),worker('old' if old else 'v.data'))
            with self.subTest(old=old,dead=dead,target=target):
                if target in retained:
                    self.refused(source);rejected+=1
                else:
                    self.assertEqual(self.run_native(source).stdout,'11\n7\n'+('7' if old else '9')+'\n');accepted+=1
        self.assertEqual((accepted,rejected),(2,6))

if __name__=='__main__':unittest.main()
