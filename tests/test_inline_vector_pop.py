"""VE3: pop transfers a local inline T, including loans and owned fields."""
from pathlib import Path
import unittest
import test_select_source as harness
import test_inline_vector_borrows as borrowed_vectors

BASE=Path(__file__).resolve().parents[1].joinpath('validation/inline-vector-pop.crb').read_text()

class InlineVectorPopTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_some_none_and_annotation(self):
        self.assertEqual(self.run_source(BASE.replace('let result=', 'let result:Option<Point>=')).stdout,'7\n')
        empty=BASE.replace('v.push(->Point{x:7});','')
        self.assertEqual(self.run_source(empty).stdout,'0\n')
        self.refused(BASE.replace('let result=', 'let result:Option<A<Point>>='),'annotation|stockage')
        self.refused(BASE.replace('drop(->point);','drop(->point);print(point.x);'),'utilisable|consomm|détruit')

    def test_last_in_first_out_and_direct_drop(self):
        source=BASE.replace('let result=<-v.pop();','v.push(->Point{x:9});drop(->v.pop());let result=<-v.pop();')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.assertEqual(self.run_source(BASE.replace('v.push(->Point{x:7});let result=<-v.pop();',
            'drop(->v.pop());v.push(->Point{x:7});let result=<-v.pop();')).stdout,'7\n')

    def test_owned_field_cleanup_once(self):
        source='''struct Item{value:A<Int>}fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
            let mut vs=pool<Vector<Item>>(1);let mut v=vs.new();v.push(->Item{value:<-n});
            let out=<-v.pop();drop(->v);match (->out){Some(item)=>{print(*item.value);drop(->item);},None=>{print(0);}}
            let again=ns.new(9);print(*again);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n9\n');self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.refused(source.replace('Some(item)=>{print(*item.value);drop(->item);}','Some(_)=>{}'),'motif|usage|ignor|propriétaire|allocation')

    def test_shared_target_outlives_carrier(self):
        source='''struct View{value:&Int}fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);
            let mut vs=pool<Vector<View>>(1);let mut v=vs.new();v.push(->View{value:&n});
            let out=<-v.pop();drop(->v);match (->out){Some(item)=>{let r=item.value;drop(->item);print(*r);},None=>{print(0);}}
            n=19;print(*n);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n19\n')
        self.refused(source.replace('print(*r);','n=20;print(*r);'),'emprunt|réserv|référenc')

    def test_mutable_target_and_remaining_case(self):
        source='''struct View{value:&mut Int}fn main(){let mut ns=pool<Int>(2);let mut a=ns.new(3);let mut b=ns.new(7);
            let mut vs=pool<Vector<View>>(1);let mut v=vs.new();v.push(->View{value:&mut a});v.push(->View{value:&mut b});
            let out=<-v.pop();match (->out){Some(item)=>{let mut owned=<-item;let mut r=&mut *owned.value;r.set(11);drop(->owned);},None=>{print(0);}}
            b=13;print(*b);let other=<-v.remove(0);drop(->v);print(*other.value);drop(->other);}'''
        self.assertEqual(self.run_source(source).stdout,'13\n3\n')
        self.refused(source.replace('b=13;','a=20;b=13;'),'emprunt|réserv|référenc')

    def test_function_return_and_relay(self):
        helper='''fn take(v:&mut Vector<Point>)-><-Option<Point>{return <-v.pop();}
            fn relay(r:->Option<Point>)-><-Option<Point>{return <-r;}'''
        source=helper+BASE.replace('<-v.pop()', 'relay(->take(&mut v))')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('fn take(v:&mut Vector<Point>)-><-Option<Point>',
            'fn take(v:&mut Vector<Point>)-><-Option<A<Point>>'),'stockage|local|allocation|pool')

    def test_loop_reuse_and_empty_structure(self):
        source='''struct Empty{}fn main(){let mut vs=pool<Vector<Empty>>(1);let mut i=0;
            while i<3{let mut v=vs.new();v.push(->Empty{});let out=<-v.pop();drop(->v);
              match (->out){Some(item)=>{drop(->item);print(i);},None=>{print(99);}}i=i+1;}}'''
        self.assertEqual(self.run_source(source).stdout,'0\n1\n2\n')

class InlineVectorAsyncPopTests(InlineVectorPopTests):
    def run_source(self, source):
        return harness.SelectSourceTests.run_source(self,borrowed_vectors.InlineVectorAsyncBorrowTests.async_source(source))
    def refused(self, source, diagnostic):
        return harness.SelectSourceTests.refused(self,borrowed_vectors.InlineVectorAsyncBorrowTests.async_source(source),diagnostic)


class InlineVectorPopTaskReturnTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    source=Path(__file__).resolve().parents[1].joinpath('validation/inline-vector-pop-async-return.crb').read_text()

    def test_join_some_none_and_storage_kind(self):
        self.assertEqual(self.run_source(self.source).stdout,'7\n')
        self.assertEqual(self.run_source(self.source.replace('v.push(->Point{x:7});','')).stdout,'0\n')
        self.refused(self.source.replace('-><-Option<Point>', '-><-Option<A<Point>>'), 'stockage|local|allocation|pool')

    def test_await_some_none(self):
        source=self.source.replace('fn main()', 'async fn work()->Int').replace(
            'let h=runtime::spawn(->take(->v));match h.join(){Ok(out)=>{',
            'let out=take(->v).await;yield;').replace('},Err(_)=>{print(99);}}}', 'return 1;}')
        source+='fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'
        self.assertEqual(self.run_source(source).stdout,'7\n1\n')
        self.assertEqual(self.run_source(source.replace('v.push(->Point{x:7});','')).stdout,'0\n1\n')

    def test_await_launched_execution(self):
        source=self.source.replace('fn main()', 'async fn work()->Int').replace('h.join()', 'h.await')
        source=source.rstrip()[:-1]+'return 1;}'
        source+='fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'
        self.assertEqual(self.run_source(source).stdout,'7\n1\n')

    def test_public_handle_and_result_relay(self):
        helpers='fn wait(h:->runtime::Handle<Option<Point>>)-><-Result<Option<Point>,runtime::Error>{return <-h.join();}\n            fn relay(r:->Result<Option<Point>,runtime::Error>)-><-Result<Option<Point>,runtime::Error>{return <-r;}'
        source=helpers+self.source.replace('match h.join()', 'let result=wait(->h);let next=relay(->result);match next')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('runtime::Handle<Option<Point>>', 'runtime::Handle<Option<A<Point>>>'), 'type|stockage|local|allocation|pool')

    def test_join_borrowed_field_keeps_target(self):
        source=self.source.replace('x:Int','x:&Int').replace('let mut p=pool<Vector<Point>>(1);',
            'let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut p=pool<Vector<Point>>(1);').replace(
            'Point{x:7}', 'Point{x:&n}').replace('print(point.x)', 'print(*point.x)').replace(
            'match h.join()', 'let result=h.join();match result')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('match result', 'n=20;match result'), 'emprunt|réserv|référenc')
        helper='fn wait(h:->runtime::Handle<Option<Point>>)-><-Result<Option<Point>,runtime::Error>{return <-h.join();}'
        public=helper+source.replace('let result=h.join();','let result=wait(->h);')
        self.assertEqual(self.run_source(public).stdout,'7\n')
        self.refused(public.replace('match result','n=20;match result'),'emprunt|réserv|référenc')

    def test_join_owned_field_cleanup(self):
        source=self.source.replace('x:Int','x:A<Int>').replace('let mut p=pool<Vector<Point>>(1);',
            'let mut ns=pool<Int>(1);let n=ns.new(7);let mut p=pool<Vector<Point>>(1);').replace(
            'Point{x:7}', 'Point{x:<-n}').replace('print(point.x)', 'print(*point.x)')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n');self.assertEqual(run.stderr.count('destroy n=7\n'),1)

if __name__=='__main__':unittest.main()
