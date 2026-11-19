"""Handle replacement in suspended states transfers either old or rejected input."""
from pathlib import Path
import unittest
import test_select_source as harness

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-vector-replace.crb').read_text()


class AsyncHandleVectorReplaceTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_direct_success_failure_and_explicit_input(self):
        for index,expected in ((0,'7\n8\n9\n'),(5,'0\n7\n9\n')):
            source=BASE.replace('v.replace(0,','v.replace('+str(index)+',')
            run=self.run_source(source)
            self.assertEqual(run.stdout,expected)
            for value in (7,8):
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('='+str(value)) for s in run.stderr.splitlines()),1)
        self.refused(BASE.replace('v.replace(0,->incoming)','v.replace(0,incoming)'),'transfert|->')
        self.refused(BASE.replace('let n=*old;','print(*incoming);let n=*old;'),'utilisable|consomm|transfér')

    def test_named_result_yield_move_and_drop(self):
        for middle,receiver in (('yield;','r'),('let moved=<-r;yield;','moved')):
            source=BASE.replace('match <-v.replace(0,->incoming)',
                'let r=<-v.replace(0,->incoming);'+middle+'match (->'+receiver+')')
            self.assertEqual(self.run_source(source).stdout,'7\n8\n9\n')
        start=BASE.index('    match <-')
        end=BASE.index('\n}\nfn main')
        source=BASE[:start]+'    let r=<-v.replace(0,->incoming);yield;drop(->r);return 42;'+BASE[end:]
        run=self.run_source(source)
        self.assertEqual(run.stdout,'42\n8\n9\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)
        for index,expected in ((0,'42\n8\n9\n'),(5,'42\n7\n9\n')):
            direct=source.replace('let r=<-v.replace(0,->incoming);yield;drop(->r);',
                                  'drop(->v.replace('+str(index)+',->incoming));')
            self.assertEqual(self.run_source(direct).stdout,expected)
        self.refused(source.replace('drop(->r);',''), 'sans usage explicite')
        self.refused(source.replace('drop(->r);','drop(->r);drop(->r);'), 'consomm|utilisable')

    def test_borrow_last_use_and_shared_receiver(self):
        source=BASE.replace('    yield;', '    let view=&*v[0];yield;print(*view);')
        self.assertEqual(self.run_source(source).stdout,'7\n7\n8\n9\n')
        self.refused(source.replace('print(*view);','').replace('let n=*old;','print(*view);let n=*old;'),'emprunt|réserv')
        self.refused(BASE.replace('v:&mut Vector','v:&Vector').replace('replace(&mut v,','replace(&v,'),'mutable|exclus')

    def test_index_and_incoming_await_order(self):
        helpers='''async fn index()->Int{yield;print(1);return 0;}
            async fn make(p:&mut Pool<Int>)-><-Int{yield;print(2);let n=p.new(8);return <-n;}'''
        source=helpers+BASE.replace('incoming:->Int','p:&mut Pool<Int>').replace(
            'v.replace(0,->incoming)','v.replace(index().await,->make(p).await)').replace(
            'let next=p.new(8);','').replace('replace(&mut v,->next)','replace(&mut v,&mut p)')
        self.assertEqual(self.run_source(source).stdout,'1\n2\n7\n8\n9\n')

    def test_select_loser_cleans_old_value_and_keeps_new(self):
        prefix='''async fn ready()->Int{return 4;}
            async fn choose(v:&mut Vector<A<Int>>,incoming:->Int)->Int{
                let mut s=runtime::select(->replace(v,->incoming),->ready());
                let n=s.await;drop(->s);return n;}'''
        source=prefix+BASE.replace('    yield;','').replace('match <-v.replace(0,->incoming)',
            'let r=<-v.replace(0,->incoming);yield;match (->r)').replace('spawn(->replace(','spawn(->choose(')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'4\n8\n9\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_pool_lifetime_of_incoming(self):
        source=BASE.replace('    yield;', '    let mut local=pool<Int>(1);let x=local.new(10);yield;').replace(
            'v.replace(0,->incoming)','v.replace(0,->x)')
        self.refused(source,'pool|source|survi')


    def test_returned_old_value_keeps_its_pool_through_factory(self):
        source='''async fn exchange(v:&mut Vector<A<Int>>,incoming:->Int,p:&mut Pool<Int>)-><-Int{
            yield;match <-v.replace(INDEX,->incoming){Ok(old)=>{return <-old;},
            Err(rejected)=>{drop(->rejected);let n=p.new(17);return <-n;}}}
            fn make(v:&mut Vector<A<Int>>,incoming:->Int,p:&mut Pool<Int>)-><-exchange{
                return <-exchange(v,->incoming,p);}
            fn main(){let mut p=pool<Int>(2);let r={let mut q=pool<Int>(1);
                let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();v.push(->p.new(7));
                let next=q.new(8);let h=runtime::spawn(->CALLEE(&mut v,->next,&mut p));
                let x=h.join();<-x};match r{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}
                let reused=p.new(9);print(*reused);}'''
        for callee in ('exchange','make'):
            for index,expected in ((0,'7\n9\n'),(5,'17\n9\n')):
                with self.subTest(callee=callee,index=index):
                    self.assertEqual(self.run_source(source.replace('CALLEE',callee).replace('INDEX',str(index))).stdout,expected)


if __name__=='__main__':unittest.main()
