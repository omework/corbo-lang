"""Task Option results and captures preserve optional ownership across await."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-option-result.crb').read_text()
CAPTURE='''async fn consume(x:->Option<A<Int>>)->Int{
    yield;match (->x){Some(n)=>{let answer=*n;drop(->n);return answer;},None=>{return 0;}}}
fn main(){let mut p=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
    v.push(->p.new(7));let x=<-v.pop();let h=runtime::spawn(->consume(->x));
    match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
    drop(->v);let next=p.new(8);print(*next);}'''


class AsyncHandleOptionResultTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_await_some_none_and_return_marker(self):
        for inserted in (True,False):
            source=BASE if inserted else BASE.replace('v.push(->p.new(7));','')
            run=self.run_source(source)
            self.assertEqual(run.stdout,('7' if inserted else '0')+'\n8\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),int(inserted))
        self.refused(BASE.replace('return <-v.pop();','return v.pop();'), 'explicite|transfert|<-')

    def test_named_return_factory_and_relay(self):
        helper='''fn make(v:&mut Vector<A<Int>>)-><-extract{return <-extract(v);}
            async fn relay(v:&mut Vector<A<Int>>)-><-Option<A<Int>>{
                let saved=make(v).await;yield;return <-saved;}'''
        for callee in ('extract','make','relay'):
            source=helper+BASE.replace('{yield;return <-v.pop();}',
                                       '{let result=<-v.pop();yield;return <-result;}').replace(
                                       'let saved=extract(v).await;', 'let saved='+callee+'(v).await;')
            with self.subTest(callee=callee):
                self.assertEqual(self.run_source(source).stdout,'7\n8\n')

    def test_capture_some_none_and_explicit_transfer(self):
        for inserted in (True,False):
            source=CAPTURE if inserted else CAPTURE.replace('v.push(->p.new(7));','')
            self.assertEqual(self.run_source(source).stdout,('7' if inserted else '0')+'\n8\n')
        self.refused(CAPTURE.replace('consume(->x)','consume(x)'), 'transfert|->')
        self.refused(CAPTURE.replace('match h.join()', 'drop(->x);match h.join()'), 'utilisable|transfert|consomm')

    def test_inactive_and_failed_launch_clean_capture(self):
        source=CAPTURE.replace('let h=runtime::spawn(->consume(->x));', 'let task=consume(->x);drop(->task);').replace(
            'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}','')
        self.assertEqual(self.run_source(source).stdout,'8\n')
        run=self.run_c_oracle(inject_submission_failure(compile_source(CAPTURE),asynchronous=False,at=1))
        self.assertEqual(run.stdout,'99\n8\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_child_capture_returns_option_to_sync_helper(self):
        helpers='''async fn forward(x:->Option<A<Int>>)-><-Option<A<Int>>{yield;return <-x;}
            fn relay(x:->Option<A<Int>>)-><-Option<A<Int>>{return <-x;}'''
        source=helpers+BASE.replace('let saved=extract(v).await;',
            'let first=extract(v).await;let saved=relay(->forward(->first).await);')
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')

    def test_suspended_child_result_cleanup(self):
        helpers='''async fn ready()->Int{return 9;}
            async fn choose(v:&mut Vector<A<Int>>)->Int{
                let mut s=runtime::select(->take(v),->ready());let n=s.await;drop(->s);return n;}'''
        source=helpers+BASE.replace('{yield;return <-v.pop();}', '{let x=<-v.pop();yield;return <-x;}').replace(
            '    yield;\n    let saved=', '    let saved=').replace('spawn(->take(', 'spawn(->choose(')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n8\n')
        self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_await_releases_vector_borrow_and_option_requires_use(self):
        source=BASE.replace('let saved=extract(v).await;', 'let saved=extract(v).await;print(v.len());')
        self.assertEqual(self.run_source(source).stdout,'0\n7\n8\n')
        self.refused(BASE.replace('let saved=extract(v).await;',
                                  'let task=extract(v);print(v.len());let saved=task.await;'), 'emprunt|réserv')
        self.refused(BASE.replace('let saved=extract(v).await;',
                                  'let unused=extract(v).await;let saved=extract(v).await;'), 'sans usage explicite')

    def test_output_and_capture_require_surviving_pool(self):
        source='''async fn extract(v:&mut Vector<A<Int>>)-><-Option<A<Int>>{yield;return <-v.pop();}
            async fn take(v:&mut Vector<A<Int>>,p:&mut Pool<Int>)-><-Int{
                let saved=extract(v).await;
                match (->saved){Some(n)=>{return <-n;},None=>{let n=p.new(9);return <-n;}}}
            fn main(){OUTER let result={INNER let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
                v.push(->p.new(7));let h=runtime::spawn(->take(&mut v,&mut p));let r=h.join();<-r};
                match result{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}}'''
        pool='let mut p=pool<Int>(1);'
        self.assertEqual(self.run_source(source.replace('OUTER',pool).replace('INNER','')).stdout,'7\n')
        self.refused(source.replace('OUTER','').replace('INNER',pool), 'pool|source|survi')
        capture=CAPTURE.replace('let mut p=pool<Int>(1);','').replace(
            'v.push(->p.new(7));let x=<-v.pop();let h=runtime::spawn(->consume(->x));',
            'let task={let mut p=pool<Int>(1);v.push(->p.new(7));let x=<-v.pop();let t=consume(->x);<-t};let h=runtime::spawn(->task);').replace(
            'let next=p.new(8);print(*next);','')
        self.refused(capture,'pool|source|survi')


if __name__=='__main__':unittest.main()
