"""Concrete feature specialization must retain async capture/result contracts."""
import unittest
import test_type_features
from crust import Error, verify_program


class AsyncTypeFeatureTests(unittest.TestCase):
    native = test_type_features.TypeFeatureTests.native

    def test_independent_vector_specializations_across_await(self):
        source='''
            type feature Length{fn len(&self)->Int;}
            async fn count(v:&Length)->Int{yield;return v.len();}
            async fn both(a:&Length,b:&Length)->Int{
                let left=count(a).await;yield;let right=count(b).await;return left+right;}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut a=p.new();a.push(7);
                let mut q=pool<Vector<u8>>(1);let mut b=q.new();let n:u8=9;b.push(n);b.push(n);
                let e=runtime::spawn(-> both(&a,&b));
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}
                a.push(8);print(a.len());}
        '''
        run=self.native(source)
        self.assertEqual((run.returncode,run.stdout),(0,'3\n2\n'),run.stderr)
        with self.assertRaisesRegex(Error,'emprunt|exécution|tâche'):
            verify_program(source.replace('match e.join()', 'a.push(8);match e.join()'))

    def test_borrowed_feature_result_remains_attached_after_join(self):
        source='''
            type feature Slice{fn try_slice(&self,a:Int,b:Int)->Result<&str,SliceError>;}
            async fn cut(v:&Slice)->Result<&str,SliceError>{yield;return v.try_slice(0..2);}
            async fn relay(v:&Slice)->Result<&str,SliceError>{let r=cut(v).await;yield;return r;}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("é!");
                let e=runtime::spawn(-> relay(&s));
                match e.join(){Ok(r)=>{EFFECT match r{Ok(t)=>{print(t);},Err(_)=>{}}},Err(_)=>{}}
                s.push_str("x");print(&s[..]);drop(-> s);let next=p.new();print(next.byte_len());}
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\né!x\n0\n'),run.stderr)
        for effect in ('s.push_str("x");','s ->;drop(-> s);','p.reset();'):
            with self.subTest(effect=effect),self.assertRaisesRegex(Error,'emprunt|utilisée|tâche'):
                verify_program(source.replace('EFFECT',effect),allow_legacy_reset=True)

    def test_mutable_capture_reserves_target_from_creation(self):
        source='''
            type feature Append{fn push(&mut self,n:Int);}
            async fn append(mut v:&mut Append)->Int{v.push(7);yield;v.push(9);return 2;}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();
                let task=append(&mut v);BEFORE
                let e=runtime::spawn(-> task);
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                print(v[0]);print(v[1]);}
        '''
        run=self.native(source.replace('BEFORE',''))
        self.assertEqual((run.returncode,run.stdout),(0,'2\n7\n9\n'),run.stderr)
        for effect in ('print(v.len());','v.push(3);','drop(-> v);'):
            with self.subTest(effect=effect),self.assertRaisesRegex(Error,'emprunt|tâche|utilisée'):
                verify_program(source.replace('BEFORE',effect))

    def test_owned_feature_capture_cleans_pool_slot_after_completion(self):
        source='''
            type feature Length{fn byte_len(&self)->Int;}
            async fn measure(s:-> Length)->Int{yield;return s.byte_len();}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("é");address(s);
                let e=runtime::spawn(-> measure(-> s));
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                let next=p.new();address(next);print(next.byte_len());}
        '''
        run=self.native(source)
        self.assertEqual(run.returncode,0,run.stderr)
        before,count,after,length=run.stdout.splitlines()
        self.assertEqual((before,count,length),(after,'2','0'))
        self.assertEqual(run.stderr.count('destroy s=0'),1)
        with self.assertRaisesRegex(Error,'plus utilisable|transfér'):
            verify_program(source.replace('let next=', 'print(s.byte_len());let next='))


if __name__ == '__main__':
    unittest.main()
