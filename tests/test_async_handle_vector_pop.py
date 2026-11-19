"""Async pop transfers exactly the optional handle that was extracted."""
from pathlib import Path
import unittest
import test_select_source as harness

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-vector-pop.crb').read_text()
NAMED='let result=<-v.pop();yield;match (->result){Some(n)=>{let value=*n;drop(->n);return value;},None=>{return 0;}}'


class AsyncHandleVectorPopTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def named(self):
        return BASE.replace('match <- v.pop(){Some(n)=>{let value=*n;drop(->n);return value;},None=>{return 0;}}', NAMED)

    def test_direct_some_none_and_explicit_transfer(self):
        for inserted in (True,False):
            source=BASE if inserted else BASE.replace('v.push(->p.new(7));','')
            run=self.run_source(source)
            self.assertEqual(run.stdout,('7' if inserted else '0')+'\n8\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),int(inserted))
        self.refused(BASE.replace('match <- v.pop()', 'match v.pop()'),'transfert|explicite|Option|pop')
        self.refused(BASE.replace('&mut Vector','&Vector').replace('take(&mut v)','take(&v)'), 'mutable')

    def test_named_result_and_move(self):
        for statement in ('', 'let moved=<-result;'):
            source=self.named()
            if statement:
                source=source.replace('yield;match (->result)', 'yield;'+statement+'match (->moved)')
            self.assertEqual(self.run_source(source).stdout,'7\n8\n')
        self.refused(self.named().replace('yield;match (->result)', 'drop(->result);yield;match (->result)'), 'consomm|utilisable|détruit')
        self.refused(self.named().replace('let result=<-v.pop();yield;match (->result)',
                                          'let unused=<-v.pop();let result=<-v.pop();yield;match (->result)'), 'sans usage explicite')
        self.assertEqual(self.run_source(self.named().replace('let result=', 'let result:Option<A<Int>>=')).stdout,'7\n8\n')
        self.refused(self.named().replace('let result=', 'let result:Int='), 'annotation|type')

    def test_drop_direct_and_named_empty_or_present(self):
        for body in ('drop(->v.pop());yield;return v.len();',
                     'let result=<-v.pop();yield;drop(->result);return v.len();'):
            for inserted in (True,False):
                source=self.named().replace(NAMED,body)
                if not inserted:source=source.replace('v.push(->p.new(7));','')
                run=self.run_source(source)
                self.assertEqual(run.stdout,'0\n8\n')
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),int(inserted))

    def test_borrow_last_use(self):
        source=self.named().replace('let result=<-v.pop();', 'let view=&*v[0];print(*view);let result=<-v.pop();')
        self.assertEqual(self.run_source(source).stdout,'7\n7\n8\n')
        self.refused(source.replace('yield;match (->result)', 'yield;print(*view);match (->result)'), 'emprunt actif')

    def test_result_transferred_from_block_branch_and_loop(self):
        for expression in ('{let r=<-v.pop();yield;<-r}',
                           'if true{let r=<-v.pop();<-r}else{let r=<-v.pop();<-r}',
                           'loop{let r=<-v.pop();yield;break <-r;}'):
            source=self.named().replace('<-v.pop()',expression,1)
            with self.subTest(expression=expression):
                self.assertEqual(self.run_source(source).stdout,'7\n8\n')

    def test_return_extracted_element_through_factory(self):
        helpers='''async fn take(v:&mut Vector<A<Int>>,p:&mut Pool<Int>)-><-Int{
            yield;match <-v.pop(){Some(n)=>{return <-n;},None=>{let n=p.new(9);return <-n;}}}
            fn make(v:&mut Vector<A<Int>>,p:&mut Pool<Int>)-><-take{return <-take(v,p);}'''
        main='''fn main(){let mut p=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
            INSERT let h=runtime::spawn(->make(&mut v,&mut p));
            match h.join(){Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}
            drop(->v);let next=p.new(8);print(*next);}'''
        for insert,expected in (('v.push(->p.new(7));','7\n8\n'),('', '9\n8\n')):
            self.assertEqual(self.run_source(helpers+main.replace('INSERT',insert)).stdout,expected)

    def test_select_loser_cleans_extracted_result(self):
        source='''async fn hold(v:&mut Vector<A<Int>>)->Int{
            let result=<-v.pop();yield;drop(->result);return 1;}
            async fn ready()->Int{return 9;}
            async fn choose(v:&mut Vector<A<Int>>)->Int{
                let mut s=runtime::select(->hold(v),->ready());let n=s.await;drop(->s);return n;}
            fn main(){let mut p=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
                v.push(->p.new(7));let h=runtime::spawn(->choose(&mut v));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                print(v.len());drop(->v);let next=p.new(8);print(*next);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n0\n8\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_last_element_uses_its_origin_pool(self):
        source=BASE.replace('let mut p=pool<Int>(1);','let mut p=pool<Int>(1);let mut q=pool<Int>(1);').replace(
            'v.push(->p.new(7));', 'v.push(->p.new(7));v.push(->q.new(9));').replace(
            'drop(->v);', 'print(*v[0]);drop(->v);let last=q.new(10);print(*last);')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n7\n10\n8\n')
        for n in (7,9):
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('='+str(n)) for s in run.stderr.splitlines()),1)


if __name__=='__main__':unittest.main()
