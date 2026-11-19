"""Optional allocation payloads remain distinct from runtime launch errors."""
from pathlib import Path
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-option-join.crb').read_text()
RESULT='Result<Option<A<Int>>,runtime::Error>'
OBSERVE='match RESULT{Ok(option)=>{match (->option){Some(n)=>{print(*n);drop(->n);},None=>{print(0);}}},Err(_)=>{print(99);}}'


class AsyncOptionJoinTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_join_some_none_and_launch_failure(self):
        for inserted in (True,False):
            source=BASE if inserted else BASE.replace('v.push(->p.new(7));','')
            run=self.run_source(source)
            self.assertEqual(run.stdout,('7' if inserted else '0')+'\n8\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),int(inserted))
            failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
            self.assertEqual(failed.stdout,'99\n8\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in failed.stderr.splitlines()),int(inserted))
        self.refused(BASE.replace('Ok(option)=>{match (->option){Some(n)=>{print(*n);drop(->n);},None=>{print(0);}}}', 'Ok(_)=>{}'), 'motif|propriétaire|usage')
        self.refused(BASE.replace(OBSERVE.replace('RESULT','h.join()'),'let unused=h.join();'),'sans usage explicite|propriétaire')

    def test_async_handle_await_and_result_return(self):
        prefix='''async fn work(v:&mut Vector<A<Int>>)->Int{
            let h=runtime::spawn(->extract(v));OBSERVE return 42;}
            async fn wrapped(v:&mut Vector<A<Int>>)-><-RESULT{
            let h=runtime::spawn(->extract(v));return <-h.await;}'''.replace('RESULT',RESULT)
        main=BASE[BASE.index('fn main()'):]
        extract=BASE[:BASE.index('fn main()')]
        for expression in ('h.await','wrapped(v).await'):
            body=prefix.replace('let h=runtime::spawn(->extract(v));OBSERVE',
                ('let h=runtime::spawn(->extract(v));' if expression=='h.await' else '')+OBSERVE.replace('RESULT',expression))
            source=extract+body+main.replace('spawn(->extract(', 'spawn(->work(').replace(
                OBSERVE.replace('RESULT','h.join()'), 'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(98);}}')
            self.assertEqual(self.run_source(source).stdout,'7\n42\n8\n')
            failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=True,at=1))
            self.assertEqual(failed.stdout,'99\n42\n8\n')

    def test_sync_helpers_and_public_handle(self):
        helpers=f'''fn wait(h:->runtime::Handle<Option<A<Int>>>)-><-{RESULT}{{return <-h.join();}}
            fn relay(r:->{RESULT})-><-{RESULT}{{return <-r;}}'''
        source=helpers+BASE.replace('match h.join()', 'let result=relay(->wait(->h));match result')
        for inserted in (True,False):
            program=source if inserted else source.replace('v.push(->p.new(7));','')
            self.assertEqual(self.run_source(program).stdout,('7' if inserted else '0')+'\n8\n')
        self.refused(source.replace('wait(->h)','wait(h)'), 'transfert|->')

    def test_named_drop_and_capture(self):
        observe=OBSERVE.replace('RESULT','h.join()')
        for replacement in ('let r=h.join();drop(->r);', 'drop(->h.join());'):
            run=self.run_source(BASE.replace(observe,replacement))
            self.assertEqual(run.stdout,'8\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)
        helpers=f'async fn consume(r:->{RESULT})->Int{{yield;{OBSERVE.replace("RESULT","r")}return 42;}}'
        source=helpers+BASE.replace(observe,'let r=h.join();let t=consume(->r);drop(->t);')
        self.assertEqual(self.run_source(source).stdout,'8\n')
        self.refused(source.replace('drop(->t);','drop(->t);drop(->r);'),'utilisable|consomm|transfert')

    def test_sources_outlive_result(self):
        source='''async fn extract(v:&mut Vector<A<Int>>)-><-Option<A<Int>>{yield;return <-v.pop();}
            fn main(){OUTER let r={INNER let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
            v.push(->p.new(7));let h=runtime::spawn(->extract(&mut v));let x=h.join();<-x};OBSERVE}'''.replace('OBSERVE',OBSERVE.replace('RESULT','r'))
        pool='let mut p=pool<Int>(1);'
        self.assertEqual(self.run_source(source.replace('OUTER',pool).replace('INNER','')).stdout,'7\n')
        self.refused(source.replace('OUTER','').replace('INNER',pool),'pool|source|survi')


    def test_prepared_envelope_and_select_cleanup(self):
        helpers=f"""fn relay(r:->{RESULT},n:Int)-><-{RESULT}{{print(n);return <-r;}}
            async fn pause()->Int{{yield;return 4;}}
            async fn consume(r:->{RESULT})->Int{{
                let moved=relay(->r,pause().await);{OBSERVE.replace('RESULT','moved')}return 42;}}
            async fn ready()->Int{{return 9;}}
            async fn choose(r:->{RESULT})->Int{{
                let mut s=runtime::select(->consume(->r),->ready());let n=s.await;drop(->s);return n;}}"""
        for selected,expected in (('consume','4\n7\n42\n8\n'),('choose','9\n8\n')):
            source=helpers+BASE.replace(OBSERVE.replace('RESULT','h.join()'),
                'let r=h.join();let handle=runtime::spawn(->'+selected+'(->r));'
                'match handle.join(){Ok(n)=>{print(n);},Err(_)=>{print(98);}}')
            run=self.run_source(source)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),1)

    def test_envelope_transfers_through_block_branch_and_loop(self):
        for expression in ('{h ->;let x=h.join();<-x}',
                           'if true{h ->;let x=h.join();<-x}else{h ->;let x=h.join();<-x}',
                           'loop{h ->;let x=h.join();break <-x;}'):
            source=BASE.replace('match h.join()', 'let r='+expression+';match r')
            with self.subTest(expression=expression):
                self.assertEqual(self.run_source(source).stdout,'7\n8\n')


if __name__=='__main__':unittest.main()
