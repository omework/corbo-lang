"""Explicit consuming Result matches preserve payloads, loans and cleanup."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

ROOT = Path(__file__).resolve().parents[1]
SCALAR = (ROOT/'validation/open-consuming-join-match.crb').read_text()
VECTOR = (ROOT/'validation/open-async-inline-public.crb').read_text()


class ConsumingJoinMatchTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_recorded_scalar_and_public_vector(self):
        self.assertEqual(self.run_source(SCALAR).stdout, '7\n')
        self.assertEqual(self.run_source(VECTOR).stdout, '7\n0\n')
        self.refused(VECTOR.replace('let fresh=p.new();', 'drop(->next);let fresh=p.new();'),
                     'utilisable|consomm|déplac|invalid')

    def test_owned_payload_receiver_and_slot_reuse(self):
        source='''async fn make(p:&mut Pool<Int>)-><-A<Int>{let n=p.new(7);yield;return <-n;}
            fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->make(&mut p));let r=h.join();
            let n=match (->r){Ok(n)=>{<-n},Err(_)=>{return;}};
            print(*n);drop(->n);let fresh=p.new(9);print(*fresh);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n9\n')
        self.assertEqual(run.stderr.count('=7\n'),1)
        self.refused(source.replace('Ok(n)=>{<-n}','Ok(_)=>{return;}'), 'motif|allocation|posséd')
        self.refused(source.replace('Ok(n)=>{<-n}','_=>{return;}').replace(',Err(_)=>{return;}',''),
                     'motif|allocation|posséd|exhaustif')

    def test_error_arm_and_failed_launch(self):
        source='''async fn make(p:&mut Pool<Int>)-><-A<Int>{let n=p.new(7);return <-n;}
            fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->make(&mut p));let r=h.join();
            match (->r){Ok(n)=>{drop(->n);},Err(error)=>{match error{
                runtime::Error::LaunchFailed=>{print(99);}}}}
            let fresh=p.new(9);print(*fresh);}'''
        self.assertEqual(self.run_source(source).stdout,'9\n')
        failed=inject_submission_failure(compile_source(source),asynchronous=False,at=1)
        self.assertEqual(self.run_c_oracle(failed).stdout,'99\n9\n')
        wildcard=source.replace('Err(error)=>{match error{\n                runtime::Error::LaunchFailed=>{print(99);}}}', '_=>{print(99);}')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(
            compile_source(wildcard),asynchronous=False,at=1)).stdout,'99\n9\n')

    def test_borrowed_payload_keeps_target_reserved(self):
        source='''async fn read(n:&Int)->&Int{yield;return n;}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);let h=runtime::spawn(->read(&n));
            let r=h.join();match (->r){Ok(view)=>{print(*view);},Err(_)=>{return;}}
            n=9;print(*n);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        for operation in ('drop(->n);','n=20;'):
            self.refused(source.replace('print(*view);',operation+'print(*view);'),
                         'emprunt|réserv|référenc')

    def test_local_struct_return_and_relay(self):
        source='''struct Point{x:Int}
            async fn make()-><-Point{let p=Point{x:7};yield;return <-p;}
            fn relay(r:->Result<Point,runtime::Error>)-><-Point{
                match (->r){Ok(p)=>{return <-p;},Err(_)=>{let p=Point{x:9};return <-p;}}}
            fn main(){let h=runtime::spawn(->make());let result=h.join();let p=relay(->result);print(p.x);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(
            compile_source(source),asynchronous=False,at=1)).stdout,'9\n')
        self.refused(source.replace('-><-Point{\n                match', '-><-A<Point>{\n                match'),
                     'stockage|local|A<T>|provenance')

    def test_unit_result_in_sync_and_async_matches(self):
        helper='async fn noop(){yield;}'
        source=helper+'''fn main(){let h=runtime::spawn(->noop());let r=h.join();
            match (->r){Ok(())=>{print(1);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_source(source).stdout,'1\n')
        source=helper+'''async fn work()->Int{let h=runtime::spawn(->noop());let r=h.await;
            match (->r){Ok(())=>{yield;return 1;},Err(_)=>{return 99;}}}
            fn main(){let h=runtime::spawn(->work());let r=h.join();
            match (->r){Ok(n)=>{print(n);},Err(_)=>{print(88);}}}'''
        self.assertEqual(self.run_source(source).stdout,'1\n')

    def test_async_named_result_and_suspend_in_arm(self):
        helper='''async fn leaf(p:&mut Pool<Int>)-><-A<Int>{let n=p.new(7);yield;return <-n;}
            async fn work()->Int{let mut p=pool<Int>(1);let h=runtime::spawn(->leaf(&mut p));
                let r=h.await;match (->r){Ok(n)=>{yield;let value=*n;drop(->n);return value;},
                Err(_)=>{return 99;}}}'''
        source=helper+'''fn main(){let h=runtime::spawn(->work());let r=h.join();
            match (->r){Ok(n)=>{print(n);},Err(_)=>{print(88);}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('Ok(n)=>{yield;', 'Ok(n)=>{r ->;yield;'),
                     'consomm|utilisable|déplac|inconn|disponible')


if __name__ == '__main__':
    unittest.main()
