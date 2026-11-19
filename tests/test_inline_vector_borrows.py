"""Inline vector fields retain their loans through moves, copies and extraction."""
from pathlib import Path
import unittest
import test_select_source as harness

ROOT=Path(__file__).resolve().parents[1]
SHARED='struct View{value:&Int}'
SETUP='let mut p=pool<Int>(2);let mut number=p.new(7);let mut q=pool<Vector<View>>(1);let mut v=q.new();'

class InlineVectorBorrowTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_recorded_shared_remove_and_drop(self):
        s=(ROOT/'validation/inline-vector-borrows-sync.crb').read_text()
        self.assertEqual(self.run_source(s).stdout,'7\n')
        for where in ('let result=', 'print(*result.value);'):
            for bad in ('drop(->number);','number=20;'):
                self.refused(s.replace('let number=','let mut number=').replace(where,bad+where),
                             'emprunt|réserv|détruit|valide')

    def test_shared_copy_preserves_target_not_vector(self):
        s=SHARED+'fn main(){'+SETUP+'''v.push(->View{value:&number});
            let a=copy(v[0]);let b=copy(a);drop(->v);print(*a.value);drop(->a);
            print(*b.value);drop(->b);number=19;print(*number);}'''
        self.assertEqual(self.run_source(s).stdout,'7\n7\n19\n')
        self.refused(s.replace('print(*b.value);','number=20;print(*b.value);'),'emprunt|réserv')

    def test_mutable_field_transfer_and_release(self):
        s='struct View{value:&mut Int}fn main(){'+SETUP+'''let item=View{value:&mut number};v.push(->item);
            let mut r=<-v.remove(0);drop(->v);let mut loan=&mut *r.value;loan.set(11);print(*r.value);
            drop(->r);number=19;print(*number);}'''
        self.assertEqual(self.run_source(s).stdout,'11\n19\n')
        self.refused(s.replace('let mut r=', 'print(*number);let mut r='),'emprunt|réserv|exclus')
        self.refused(s.replace('let mut r=<-v.remove(0);','let mut r=copy(v[0]);'),'copiable|copie')
        self.refused(s.replace('let mut loan=&mut *r.value;loan.set(11);','number=20;let mut loan=&mut *r.value;loan.set(11);'),'emprunt|réserv')

    def test_two_positions_release_only_extracted_loan(self):
        s='struct View{value:&mut Int}fn main(){'+SETUP+'''let mut other=p.new(9);
            v.push(->View{value:&mut number});v.push(->View{value:&mut other});
            let r=<-v.remove(0);drop(->r);number=11;
            let mut remaining=<-v.remove(0);let mut loan=&mut *remaining.value;loan.set(13);drop(->remaining);
            print(*number);print(*other);}'''
        self.assertEqual(self.run_source(s).stdout,'11\n13\n')
        self.refused(s.replace('number=11;','number=11;other=20;'),'emprunt|réserv')

    def test_scope_dependency_survives_carrier_move(self):
        s=SHARED+'fn main(){'+SETUP+'''{let item=View{value:&number};v.push(->item);}
            let r=<-v.remove(0);print(*r.value);}'''
        self.assertEqual(self.run_source(s).stdout,'7\n')
        self.refused(s.replace('{let item=View{value:&number};',
            '{print(*number);let local=p.new(9);let item=View{value:&local};'),'durable|survit|scope|emprunt actif')

    def test_functions_and_returned_element(self):
        helpers='''fn insert(v:&mut Vector<View>, item:->View){v.push(->item);}
            fn take(v:&mut Vector<View>)-><-View{return <-v.remove(0);}
            fn relay(v:&mut Vector<View>)-><-View{return <-take(&mut *v);}'''
        s=SHARED+helpers+'fn main(){'+SETUP+'''let item=View{value:&number};insert(&mut v,->item);
            let r=relay(&mut v);drop(->v);print(*r.value);drop(->r);number=19;print(*number);}'''
        self.assertEqual(self.run_source(s).stdout,'7\n19\n')
        self.refused(s.replace('drop(->r);number=19;print(*number);','drop(->r);').replace(
            'print(*r.value);','drop(->number);print(*r.value);'),'emprunt|réserv|détruit')

    def test_branch_merge_and_slot_reuse_in_loop(self):
        s=SHARED+'fn main(){'+SETUP+'''let other=p.new(9);
            if true{v.push(->View{value:&number});}else{v.push(->View{value:&other});}
            let r=<-v.remove(0);drop(->v);print(*r.value);drop(->r);
            let mut i=0;while i<3{let mut current=q.new();current.push(->View{value:&number});
                let out=<-current.remove(0);print(*out.value);drop(->out);drop(->current);i=i+1;}
            number=19;print(*number);}'''
        self.assertEqual(self.run_source(s).stdout,'7\n7\n7\n7\n19\n')
        self.refused(s.replace('print(*r.value);','drop(->other);print(*r.value);'),'emprunt|réserv|détruit')

    def test_fresh_injected_insert_and_shared_copy_contract(self):
        helpers='''fn fill(v:&mut Vector<View>, n:&Int){v.push(->View{value:n});}
            fn read(v:&Vector<View>)-><-View{let r=copy(v[0]);return <-r;}'''
        s=SHARED+helpers+'fn main(){'+SETUP+'''fill(&mut v,&number);
            let a=read(&v);let b=read(&v);drop(->v);print(*a.value);drop(->a);
            print(*b.value);drop(->b);}'''
        self.assertEqual(self.run_source(s).stdout,'7\n7\n')
        self.refused(s.replace('print(*b.value);','drop(->number);print(*b.value);'),'emprunt|réserv')

    def test_nested_fields_and_return_from_child(self):
        s='struct Inner{value:&Int}struct View{left:Int,inner:Inner}fn main(){'+SETUP+'''
            let r={v.push(->View{left:3,inner:Inner{value:&number}});let out=<-v.remove(0);<-out};
            drop(->v);print(r.left);print(*r.inner.value);drop(->r);number=19;print(*number);}'''
        self.assertEqual(self.run_source(s).stdout,'3\n7\n19\n')
        self.refused(s.replace('print(r.left);','number=20;print(r.left);'),'emprunt|réserv')

class InlineVectorAsyncBorrowTests(InlineVectorBorrowTests):
    @staticmethod
    def async_source(source):
        helpers, body=source.split('fn main(){',1)
        body=body.strip()
        assert body.endswith('}')
        body=body[:-1].replace('drop(->v);','drop(->v);yield;')
        return helpers+'async fn work()->Int{yield;'+body+'''return 0;}
            fn main(){let h=runtime::spawn(->work());match h.join(){
                Ok(_)=>{},Err(_)=>{print(99);}}}'''

    def run_source(self, source):
        return harness.SelectSourceTests.run_source(self,self.async_source(source))

    def refused(self, source, diagnostic):
        return harness.SelectSourceTests.refused(self,self.async_source(source),diagnostic)


class InlineVectorCaptureTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_owned_capture_returns_borrowed_payload(self):
        original=(ROOT/'validation/inline-vector-borrows-capture.crb').read_text()
        for mutable in (False,True):
            source=(original.replace('value:&Int','value:&mut Int').replace('value:&number','value:&mut number')
                    if mutable else original)
            self.assertEqual(self.run_source(source).stdout,'7\n19\n0\n')
            self.refused(source.replace('number=19;print(*number);','').replace(
                'let h=','drop(->number);let h='),'emprunt|réserv|utilisable')
            self.refused(source.replace('number=19;print(*number);','').replace(
                'print(*r.value);','drop(->number);print(*r.value);'),'emprunt|réserv')


if __name__=='__main__':unittest.main()
