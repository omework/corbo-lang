"""Inline vector cases own their children; extraction transfers cleanup once."""
from pathlib import Path
import unittest
import test_select_source as harness
import test_inline_vector_borrows as borrowed_vectors

BASE=Path('validation/inline-vector-owned.crb').read_text()

class InlineVectorOwnedTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_remove_and_reuse(self):
        result=self.run_source(BASE)
        self.assertEqual(result.stdout,'7\n9\n')
        self.assertEqual(result.stderr.count('destroy number=7\n'),1)
        self.refused(BASE.replace('let out=','print(*number);let out='),'utilisable|déplac|consomm|détruit')
        self.refused(BASE.replace('<-v.remove(0)','copy(v[0])'),'non copiable|copie')

    def test_drop_nonempty_vector_and_cross_pool_fields(self):
        source='''struct Item{left:A<Int>,right:A<Int>}fn main(){
            let mut p=pool<Int>(1);let mut q=pool<Int>(1);let a=p.new(3);let b=q.new(7);
            let mut vs=pool<Vector<Item>>(1);let mut v=vs.new();
            v.push(->Item{left:<-a,right:<-b});drop(->v);
            let c=p.new(11);let d=q.new(13);print(*c);print(*d);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'11\n13\n')
        for name,value in (('a',3),('b',7)):
            self.assertEqual(run.stderr.count(f'destroy {name}={value}\n'),1)
        self.assertLess(run.stderr.index('destroy b=7'),run.stderr.index('destroy a=3'))

    def test_nested_owner_and_borrowed_descendant(self):
        source='''struct Leaf{view:&Int}struct Item{leaf:A<Leaf>}
            fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut leaves=pool<Leaf>(1);
            let leaf=leaves.new(view:&n);let mut vs=pool<Vector<Item>>(1);let mut v=vs.new();
            let item=Item{leaf:<-leaf};v.push(->item);let out=<-v.remove(0);drop(->v);
            let loan=&*out.leaf;print(*loan.view);drop(->out);n=19;print(*n);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n19\n')
        self.assertEqual(run.stderr.count('=Leaf\n'),1)
        for where in ('let out=', 'let loan='):
            self.refused(source.replace(where,'n=20;'+where),'emprunt|réserv|référenc')

    def test_contained_owner_layout_and_scope_exit(self):
        source='struct Inner{value:A<Int>}struct Item{tag:Int,inner:Inner}\n            fn main(){let mut ns=pool<Int>(1);let mut vs=pool<Vector<Item>>(1);\n            {let n=ns.new(7);let mut v=vs.new();v.push(->Item{tag:3,inner:Inner{value:<-n}});\n              let out=<-v.remove(0);print(out.tag);print(*out.inner.value);}\n            let again=ns.new(9);print(*again);}'
        run=self.run_source(source)
        self.assertEqual(run.stdout,'3\n7\n9\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)

    def test_child_pool_cannot_escape_into_vector(self):
        source='''struct Item{value:A<Int>}fn main(){let mut vs=pool<Vector<Item>>(1);let mut v=vs.new();
            {let mut ns=pool<Int>(1);let n=ns.new(7);v.push(->Item{value:<-n});}
            let out=<-v.remove(0);print(*out.value);}'''
        self.refused(source,'pool|survit|durable')

    def test_contract_insert_extract_and_relay(self):
        helpers='''fn put(v:&mut Vector<Item>,item:->Item){v.push(->item);}
            fn take(v:&mut Vector<Item>)-><-Item{return <-v.remove(0);}
            fn relay(v:&mut Vector<Item>)-><-Item{return <-take(&mut *v);}'''
        source=helpers+BASE.replace('v.push(->item);','put(&mut v,->item);').replace('<-v.remove(0)','relay(&mut v)')
        result=self.run_source(source)
        self.assertEqual(result.stdout,'7\n9\n')
        self.assertEqual(result.stderr.count('destroy number=7\n'),1)

    def test_injected_contract_rejects_short_pool(self):
        source='struct Item{value:A<Int>}\n            fn put(v:&mut Vector<Item>,item:->Item){v.push(->item);}\n            fn main(){let mut vs=pool<Vector<Item>>(1);let mut v=vs.new();\n              {let mut ns=pool<Int>(1);let n=ns.new(7);let item=Item{value:<-n};put(&mut v,->item);}\n              let out=<-v.remove(0);print(*out.value);}'
        self.refused(source,'pool|survit|durable|source')

    def test_borrowed_descendant_through_contract(self):
        source='struct Leaf{view:&Int}struct Item{leaf:A<Leaf>}\n            fn put(v:&mut Vector<Item>,item:->Item){v.push(->item);}\n            fn take(v:&mut Vector<Item>)-><-Item{return <-v.remove(0);}\n            fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut leaves=pool<Leaf>(1);\n              let leaf=leaves.new(view:&n);let mut vs=pool<Vector<Item>>(1);let mut v=vs.new();\n              let item=Item{leaf:<-leaf};put(&mut v,->item);let out=take(&mut v);drop(->v);\n              let loan=&*out.leaf;print(*loan.view);drop(->out);n=19;print(*n);}'
        self.assertEqual(self.run_source(source).stdout,'7\n19\n')
        self.refused(source.replace('let loan=','n=20;let loan='),'emprunt|réserv|référenc')

    def test_move_between_vectors_and_scope_cleanup(self):
        source='''struct Item{value:A<Int>}fn main(){let mut ns=pool<Int>(1);
            let mut vs=pool<Vector<Item>>(2);let mut a=vs.new();let mut b=vs.new();
            let mut i=0;while i<3{let n=ns.new(i);a.push(->Item{value:<-n});
                let item=<-a.remove(0);b.push(->item);let out=<-b.remove(0);print(*out.value);
                drop(->out);i=i+1;}drop(->a);drop(->b);let again=ns.new(9);print(*again);}'''
        self.assertEqual(self.run_source(source).stdout,'0\n1\n2\n9\n')

class InlineVectorAsyncOwnedTests(InlineVectorOwnedTests):
    def run_source(self, source):
        return harness.SelectSourceTests.run_source(self,borrowed_vectors.InlineVectorAsyncBorrowTests.async_source(source))
    def refused(self, source, diagnostic):
        return harness.SelectSourceTests.refused(self,borrowed_vectors.InlineVectorAsyncBorrowTests.async_source(source),diagnostic)

class InlineVectorOwnedCaptureTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_capture_result_and_inactive_cleanup(self):
        helper='async fn take(mut v:->A<Vector<Item>>)-><-Item{yield;let r=<-v.remove(0);return <-r;}'
        source=helper+BASE.replace('let out=<-v.remove(0);drop(->v);print(*out.value);drop(->out);',
            'let h=runtime::spawn(->take(->v));match h.join(){Ok(out)=>{print(*out.value);drop(->out);},Err(_)=>{print(99);}}')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        inactive=helper+BASE.replace('let out=<-v.remove(0);drop(->v);print(*out.value);drop(->out);',
            'let task=take(->v);drop(->task);')
        run=self.run_source(inactive)
        self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('destroy number=7\n'),1)

if __name__=='__main__':unittest.main()
