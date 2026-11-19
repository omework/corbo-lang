"""Whole transferred carriers preserve the loans held by their fields."""
from pathlib import Path
import unittest
from crust import verify_program
import test_select_source as source_tests
import test_native_blocks as native_tests

ROOT=Path(__file__).resolve().parents[1]

class OwnedBorrowedCaptureTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused
    run_native=native_tests.NativeBlockTests.run_native

    def program(self):
        return (ROOT/'validation/open-owned-borrowed-structure-capture.crb').read_text()

    def test_direct_launch_failure_and_inactive_cleanup(self):
        source=self.program()
        for failure,expected in ((None,'7\n'),(1,'99\n')):
            run=self.run_native(source,fail_submission_at=failure)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('destroy view=View\n'),1)
            self.assertEqual(run.stderr.count('destroy number=7\n'),1)
        inactive=source[:source.index('    let execution')]+'''let task=read(->view);drop(->task);print(*number);drop(->number);}'''
        run=self.run_source(inactive)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy view=View\n'),1)
        self.refused(source.replace('drop(->number);','').replace('match execution.join()',
                     'drop(->number);match execution.join()'),'emprunt|réserv|référenc')
        self.refused(inactive.replace('drop(->task);print(*number);','drop(->number);drop(->task);'),
                     'emprunt|réserv|référenc')

    def test_factory_and_relay_keep_field_contract(self):
        source=(ROOT/'validation/open-owned-borrowed-capture-factory.crb').read_text()
        invalid=(ROOT/'validation/open-owned-borrowed-capture-factory-invalid.crb').read_text()
        for relay in (False,True):
            extra='fn again(v:->View)-><-read{return <-make(->v);} '
            program=source.replace('fn main()',extra+'fn main()').replace('->make(->view)','->again(->view)') if relay else source
            self.assertEqual(self.run_source(program).stdout,'7\n')
            bad=invalid.replace('fn main()',extra+'fn main()').replace('->make(->view)','->again(->view)') if relay else invalid
            self.refused(bad,'emprunt|réserv|référenc')
            summary=verify_program(program).function_contracts['again' if relay else 'make'].result
            self.assertEqual({(t.kind,t.parameter,t.field) for _,ts in summary.borrowed_fields for t in ts},
                             {('owned_capture_field',0,'.data')})

    def test_mutable_field_exclusive_until_join(self):
        source=self.program().replace('&Int','&mut Int').replace('read(view:','read(mut view:').replace(
            'let number =','let mut number =').replace('data: &number','data: &mut number').replace(
            'return *view.data;', 'let mut target=&mut *view.data;target.set(20);return *target;').replace(
            'drop(->number);','print(*number);drop(->number);')
        self.assertEqual(self.run_source(source).stdout,'20\n20\n')
        for operation in ('print(*number);','number=30;','drop(->number);'):
            invalid=source.replace('print(*number);drop(->number);','').replace('match execution.join()',operation+'match execution.join()')
            self.refused(invalid,'emprunt|réserv|référenc')
        factory='fn make(v:->View)-><-read{return <-read(->v);} '
        relayed=source.replace('fn main()',factory+'fn main()').replace('->read(->view)','->make(->view)')
        self.assertEqual(self.run_source(relayed).stdout,'20\n20\n')
        self.refused(relayed.replace('match execution.join()','print(*number);match execution.join()'),'emprunt|réserv|référenc')

    def test_task_relay_keeps_owned_capture_loans(self):
        source=(ROOT/'validation/open-owned-borrowed-task-relay.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('drop(->number);','').replace('match execution.join()',
            'drop(->number);match execution.join()'),'emprunt|réserv|référenc')

    def test_detached_reference_survives_carrier_cleanup(self):
        source=(ROOT/'validation/open-owned-borrowed-capture-result-reference.crb').read_text()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('=View\n'),1)
        self.refused((ROOT/'validation/open-owned-borrowed-detached-reference-invalid.crb').read_text(),
                     'emprunt|réserv|référenc')

    def test_async_caller_transfers_field_loans(self):
        prefix='''struct View{data:&Int}async fn read(v:->View)->Int{yield;return *v.data;}
          fn make(v:->View)-><-read{return <-read(->v);}'''
        for call in ('read','make'):
            source=prefix+'''async fn work()->Int{let mut p=pool<Int>(1);let n=p.new(7);
              let v=View{data:&n};let child=CALL(->v);yield;
              let result=child.await;drop(->n);return result;}
              fn main(){let h=runtime::spawn(->work());match h.join(){Ok(x)=>{print(x);},Err(_)=>{}}}'''.replace('CALL',call)
            self.assertEqual(self.run_source(source).stdout,'7\n')
            invalid=source.replace('drop(->n);','').replace('let result=child.await;','drop(->n);let result=child.await;')
            self.refused(invalid,'emprunt|réserv|référenc|capture')

    def test_source_and_target_scope_model(self):
        prefix='''struct View{data:&Int}async fn read(v:->A<View>)->Int{yield;return *v.data;}
          fn make(v:->A<View>)-><-read{return <-read(->v);}'''
        # Independent model: both the carrier's pool and the borrowed allocation
        # must outlive the task exported from the child scope.
        for carrier_outer in (False,True):
            for target_outer in (False,True):
                for factory in ('read','make'):
                    before=('let mut vs=pool<View>(1);' if carrier_outer else '')
                    before+=('let mut ns=pool<Int>(1);let n=ns.new(7);' if target_outer else '')
                    inside=('' if carrier_outer else 'let mut vs=pool<View>(1);')
                    inside+=('' if target_outer else 'let mut ns=pool<Int>(1);let n=ns.new(7);')
                    source=prefix+'fn main(){'+before+'let task={'+inside+'let v=vs.new(data:&n);let task='+factory+'(->v);<-task};'+'''
                      let h=runtime::spawn(->task);match h.join(){Ok(x)=>{print(x);},Err(_)=>{}}}'''
                    with self.subTest(carrier=carrier_outer,target=target_outer,factory=factory):
                        if carrier_outer and target_outer:self.assertEqual(self.run_source(source).stdout,'7\n')
                        else:self.refused(source,'survi|durable|emprunt|capture')

    def test_two_fields_keep_modes_and_sources(self):
        source='''struct Pair{read:&Int,write:&mut Int}
          async fn compute(mut v:->Pair)->Int{yield;let mut out=&mut *v.write;out.set(*v.read);return *out;}
          fn make(v:->Pair)-><-compute{return <-compute(->v);}
          fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let mut b=ns.new(9);
            let v=Pair{read:&a,write:&mut b};let task=make(->v);print(*a);
            let h=runtime::spawn(->task);match h.join(){Ok(x)=>{print(x);},Err(_)=>{}}print(*b);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n7\n7\n')
        for operation in ('drop(->a);','drop(->b);','print(*b);'):
            self.refused(source.replace('let h=runtime::spawn',operation+'let h=runtime::spawn'),'emprunt|réserv|référenc')

    def test_native_thread_capture(self):
        source='''struct View{data:&Int}fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
          let v=View{data:&n};let h=runtime::thread({->(v);return *v.data;});
          match h.join(){Ok(x)=>{print(x);},Err(_)=>{print(99);}}drop(->n);}'''
        for failure,expected in ((False,'7\n'),(True,'99\n')):
            run=self.run_native(source,fail_native=failure)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('=View\n'),1)
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.refused(source.replace('drop(->n);','').replace('match h.join()','drop(->n);match h.join()'),
                     'emprunt|réserv|référenc')

    def test_select_retains_losing_carrier_until_drop(self):
        source='''struct View{data:&Int}async fn read(v:->View)->Int{yield;return *v.data;}
          async fn ready()->Int{return 9;}
          async fn work()->Int{let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{data:&n};
            let mut s=runtime::select(->read(->v),->ready());let value=s.await;
            drop(->s);drop(->n);return value;}
          fn main(){let h=runtime::spawn(->work());match h.join(){Ok(x)=>{print(x);},Err(_)=>{}}}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('=View\n'),1)
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.refused(source.replace('drop(->s);drop(->n);','drop(->n);drop(->s);'),'emprunt|réserv|référenc')

    def test_prepared_owner_keeps_target_across_later_argument(self):
        prefix='''struct View{data:&Int}async fn read(v:->View,x:Int)->Int{yield;return *v.data+x;}
          async fn pause()->Int{yield;return 1;}'''
        source=prefix+'''async fn work()->Int{let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{data:&n};
          let result=read(->v,pause().await).await;drop(->n);return result;}
          fn main(){let h=runtime::spawn(->work());match h.join(){Ok(x)=>{print(x);},Err(_)=>{}}}'''
        self.assertEqual(self.run_source(source).stdout,'8\n')
        early=source.replace('pause().await).await;drop(->n);return result;',
                             '{yield;return 9;}).await;drop(->n);return result;')
        run=self.run_source(early)
        self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('=View\n'),1)
        self.refused(source.replace('pause().await).await;drop(->n);',
                                   '{n ->;drop(->n);pause().await}).await;'),'emprunt|réserv|référenc')

if __name__=='__main__':unittest.main()
