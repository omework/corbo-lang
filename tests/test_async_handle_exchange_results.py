"""Owned exchange results cross task captures and completion without moving cells."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure
from test_async_handle_vector_try_push import BASE as APPEND, full

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-exchange-result.crb').read_text()
TYPE='Result<A<Int>,A<Int>>'
CAPTURE='''async fn consume(r:->Result<A<Int>,A<Int>>)->Int{
    yield;match (->r){Ok(n)=>{let value=*n;drop(->n);return value;},
    Err(n)=>{let value=*n;drop(->n);return value;}}}
fn main(){let mut p=pool<Int>(2);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
    v.push(->p.new(7));let incoming=p.new(8);let r=<-v.replace(INDEX,->incoming);
    let h=runtime::spawn(->consume(->r));
    match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
    print(*v[0]);drop(->v);let next=p.new(9);print(*next);}'''

class AsyncHandleExchangeResultTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_return_variants_and_explicit_move(self):
        for index,expected in ((0,'7\n8\n9\n'),(5,'0\n7\n9\n')):
            for body in ('let r=<-v.replace(INDEX,->incoming);yield;return <-r;',
                         'return <-v.replace(INDEX,->incoming);'):
                start=BASE.index('    let r=<-v.replace')
                end=BASE.index('\n}',start)
                source=BASE[:start]+body.replace('INDEX',str(index))+BASE[end:]
                self.assertEqual(self.run_source(source).stdout,expected)
        self.refused(BASE.replace('return <-r;','return r;'),'transfert|explicite|<-')

    def test_factory_relay_and_sync_helper(self):
        helpers=f'''fn make(v:&mut Vector<A<Int>>,n:->A<Int>)-><-exchange{{return <-exchange(v,->n);}}
        async fn relay(r:->{TYPE})-><-{TYPE}{{yield;return <-r;}}
        fn identity(r:->{TYPE})-><-{TYPE}{{return <-r;}}'''
        for callee in ('exchange','make'):
            source=helpers+BASE.replace('let r=exchange(v,->incoming).await;',
                f'let first={callee}(v,->incoming).await;let r=identity(->relay(->first).await);')
            self.assertEqual(self.run_source(source).stdout,'7\n8\n9\n')

    def test_capture_variants_and_move(self):
        for index,expected in ((0,'7\n8\n9\n'),(5,'8\n7\n9\n')):
            self.assertEqual(self.run_source(CAPTURE.replace('INDEX',str(index))).stdout,expected)
        self.refused(CAPTURE.replace('INDEX','0').replace('consume(->r)','consume(r)'), 'transfert|->')
        self.refused(CAPTURE.replace('INDEX','0').replace('match h.join()', 'drop(->r);match h.join()'), 'utilisable|consomm|transfert')

    def test_inactive_and_failed_submission_cleanup(self):
        for index in (0,5):
            source=CAPTURE.replace('INDEX',str(index))
            inactive=source.replace('let h=runtime::spawn(->consume(->r));','let t=consume(->r);drop(->t);').replace(
                'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}','')
            self.assertEqual(self.run_source(inactive).stdout,('8' if index==0 else '7')+'\n9\n')
            run=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
            self.assertEqual(run.stdout,'99\n'+('8' if index==0 else '7')+'\n9\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('='+str(7 if index==0 else 8)) for s in run.stderr.splitlines()),1)

    def test_try_push_result_and_capture(self):
        helpers='''async fn insert(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-Result<(),A<Int>>{
            yield;return <-v.try_push(->incoming);}
            async fn forward(r:->Result<(),A<Int>>)-><-Result<(),A<Int>>{yield;return <-r;}'''
        source=helpers+APPEND.replace('match <-v.try_push(->incoming)',
            'let first=insert(v,->incoming).await;let r=forward(->first).await;match (->r)')
        for program,expected in ((source,'1\n8\n9\n'),(full(source),'8\n1\n9\n')):
            self.assertEqual(self.run_source(program).stdout,expected)
        self.refused(source.replace('forward(->first)','forward(first)'), 'transfert|->')

    def test_suspended_child_cleanup(self):
        helpers='''async fn ready()->Int{return 3;}
            async fn choose(v:&mut Vector<A<Int>>,incoming:->Int)->Int{
                let mut s=runtime::select(->replace(v,->incoming),->ready());let n=s.await;drop(->s);return n;}'''
        source=helpers+BASE.replace('    yield;\n    let r=<-v.replace', '    let r=<-v.replace').replace(
            'spawn(->replace(', 'spawn(->choose(')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'3\n8\n9\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_try_push_inactive_capture_cleanup(self):
        helpers='''async fn ignore(r:->Result<(),A<Int>>)->Void{yield;drop(->r);}'''
        start=APPEND.index('    yield;')
        end=APPEND.index('\n}\nfn main')
        source=helpers+APPEND[:start]+'''let r=<-v.try_push(->incoming);
            let t=ignore(->r);drop(->t);return 42;'''+APPEND[end:]
        for program,expected in ((source,'42\n8\n9\n'),(full(source),'42\n1\n9\n')):
            run=self.run_source(program)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)

    def test_result_lifetimes_and_live_vector_borrow(self):
        helpers='''async fn extract(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-Result<A<Int>,A<Int>>{
            yield;return <-v.replace(0,->incoming);}
            async fn take(v:&mut Vector<A<Int>>,incoming:->A<Int>,p:&mut Pool<Int>)-><-Int{
                let r=extract(v,->incoming).await;match (->r){Ok(old)=>{return <-old;},
                Err(rejected)=>{drop(->rejected);let n=p.new(17);return <-n;}}}'''
        source=helpers+'''fn main(){let mut p=pool<Int>(2);let r={let mut q=pool<Int>(2);
            let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();v.push(->p.new(7));
            let incoming=q.new(8);let h=runtime::spawn(->take(&mut v,->incoming,&mut p));let r=h.join();<-r};
            match r{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('v.push(->p.new(7))','v.push(->q.new(7))'),'pool|source|survi')
        self.refused(BASE.replace('let r=exchange(v,->incoming).await;',
            'let t=exchange(v,->incoming);print(v.len());let r=t.await;'),'emprunt|réserv')
        self.refused(BASE.replace('match (->r)', 'drop(->r);match (->r)'),'utilisable|consomm|Result')

    def test_try_push_capture_from_main_cleanup(self):
        source=CAPTURE.replace(TYPE,'Result<(),A<Int>>').replace(
            'Ok(n)=>{let value=*n;drop(->n);return value;}', 'Ok(())=>{return 1;}').replace(
            'v.push(->p.new(7));','').replace('v.replace(INDEX,->incoming)', 'v.try_push(->incoming)')
        for filled in (False,True):
            program=full(source) if filled else source
            self.assertEqual(self.run_source(program).stdout,('8\n1' if filled else '1\n8')+'\n9\n')
            inactive=program.replace('let h=runtime::spawn(->consume(->r));', 'let t=consume(->r);drop(->t);').replace(
                'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}','')
            self.assertEqual(self.run_source(inactive).stdout,('1' if filled else '8')+'\n9\n')
            run=self.run_c_oracle(inject_submission_failure(compile_source(program),asynchronous=False,at=1))
            self.assertEqual(run.stdout,'99\n'+('1' if filled else '8')+'\n9\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)

    def test_prepared_capture_from_sync_result_and_select(self):
        helpers='''fn insert(v:&mut Vector<A<Int>>,incoming:->A<Int>)-><-Result<(),A<Int>>{
                return <-v.try_push(->incoming);}
            async fn consume(r:->Result<(),A<Int>>,n:Int)->Int{
                yield;drop(->r);return n;}
            async fn pause()->Int{yield;return 4;}
            async fn ready()->Int{return 3;}
            async fn choose(v:&mut Vector<A<Int>>,incoming:->Int)->Int{
                let mut s=runtime::select(->append(v,->incoming),->ready());let n=s.await;drop(->s);return n;}'''
        start=APPEND.index('    yield;')
        end=APPEND.index('\n}\nfn main')
        source=helpers+APPEND[:start]+'''let t=consume(->insert(v,->incoming),pause().await);
            return t.await;'''+APPEND[end:]
        for selected in (False,True):
            program=source.replace('spawn(->append(', 'spawn(->choose(') if selected else source
            for filled in (False,True):
                run=self.run_source(full(program) if filled else program)
                self.assertEqual(run.stdout,('3' if selected else '4')+'\n'+('1' if filled else '8')+'\n9\n')
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)

if __name__=='__main__':unittest.main()
