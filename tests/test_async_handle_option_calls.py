"""Synchronous calls from async preserve optional owner storage and cleanup."""
from pathlib import Path
import unittest
import test_select_source as harness

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-option-call.crb').read_text()
RELAY='fn relay(x:->Option<A<Int>>,marker:Int)-><-Option<A<Int>>{print(marker);return <-x;}'
PAUSE='async fn pause()->Int{yield;return 4;}'


class AsyncHandleOptionCallTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_recorded_return_some_and_none(self):
        for inserted in (True,False):
            source=BASE if inserted else BASE.replace('v.push(->p.new(7));','')
            run=self.run_source(source)
            self.assertEqual(run.stdout,('7' if inserted else '0')+'\n8\n')
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=7') for s in run.stderr.splitlines()),int(inserted))
        self.refused(BASE.replace('let saved=extract(v);', 'extract(v);let saved=extract(v);'), 'propriétaire|explicite')
        self.refused(BASE.replace('let saved=extract(v);match (->saved)', 'match extract(v)'), 'consomm|transfert|explicite')

    def test_statically_empty_option_forwarding(self):
        source=(ROOT/'validation/empty-handle-option-forward.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'')

    def test_explicit_arguments_and_suspended_later_argument(self):
        for setup,argument in (('let first=extract(v);','->first'),
                               ('','->extract(v)'),
                               ('','-> <-v.pop()'),
                               ('','->{let first=<-v.pop();<-first}')):
            source=RELAY+PAUSE+BASE.replace('let saved=extract(v);',setup+'let saved=relay('+argument+',pause().await);')
            with self.subTest(argument=argument):
                self.assertEqual(self.run_source(source).stdout,'4\n7\n8\n')
        source=RELAY+BASE.replace('let saved=extract(v);','let first=extract(v);let saved=relay(->first,4);')
        self.refused(source.replace('relay(->first,4)','relay(first,4)'), 'transfert|explicite')
        self.refused(source.replace('match (->saved)', 'drop(->first);match (->saved)'), 'consomm|utilisable|détruit')
        self.refused(RELAY+BASE.replace('let saved=extract(v);','let first=<-v.remove(0);let saved=relay(->first,4);'),
                     'type|propriétaire|allocation')

    def test_void_consumer_and_direct_drop(self):
        helper='fn consume(x:->Option<A<Int>>){drop(->x);}'
        original='let saved=extract(v);match (->saved){Some(n)=>{let value=*n;drop(->n);return value;},None=>{return 0;}}'
        for body in ('consume(->extract(v));return v.len();',
                     'drop(->extract(v));return v.len();'):
            for inserted in (True,False):
                source=helper+BASE.replace(original,body)
                if not inserted:source=source.replace('v.push(->p.new(7));','')
                self.assertEqual(self.run_source(source).stdout,'0\n8\n')

    def test_named_result_keeps_source_after_vector_drop(self):
        source=BASE.replace('async fn take(v:&mut Vector<A<Int>>)', 'async fn take(mut v:->Vector<A<Int>>)').replace(
            'extract(v);match', 'extract(&mut v);drop(->v);yield;match').replace(
            'take(&mut v)', 'take(->v)').replace('    drop(->v);','')
        self.assertEqual(self.run_source(source).stdout,'7\n8\n')

    def test_select_loser_cleans_prepared_argument(self):
        source=RELAY+'''fn extract(v:&mut Vector<A<Int>>)-><-Option<A<Int>>{return <-v.pop();}
            async fn pause()->Int{yield;return 4;}
            async fn hold(v:&mut Vector<A<Int>>)->Int{
                let saved=relay(->extract(v),pause().await);drop(->saved);return 1;}
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

    def test_extracted_result_keeps_element_pool_through_helper(self):
        source='''fn extract(v:&mut Vector<A<Int>>)-><-Option<A<Int>>{return <-v.pop();}
            async fn take(v:&mut Vector<A<Int>>,p:&mut Pool<Int>)-><-Int{
                let saved=extract(v);yield;
                match (->saved){Some(n)=>{return <-n;},None=>{let n=p.new(9);return <-n;}}}
            fn main(){OUTER let result={INNER let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
                INSERT let h=runtime::spawn(->take(&mut v,&mut p));let r=h.join();<-r};
                match result{Ok(n)=>{print(*n);drop(->n);},Err(_)=>{print(99);}}}'''
        pool='let mut p=pool<Int>(1);'
        for insert,expected in (('v.push(->p.new(7));','7\n'),('', '9\n')):
            program=source.replace('INSERT',insert)
            self.assertEqual(self.run_source(program.replace('OUTER',pool).replace('INNER','')).stdout,expected)
            self.refused(program.replace('OUTER','').replace('INNER',pool), 'pool|source|survi')


if __name__=='__main__':unittest.main()
