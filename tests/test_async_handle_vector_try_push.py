"""Fallible handle insertion owns only its rejected payload across suspension."""
from pathlib import Path
import struct
import unittest
import test_select_source as harness

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-async-handle-vector-try-push.crb').read_text()
LIMIT=1048576//struct.calcsize('P')


def full(source):
    source=source.replace('fn main(){','fn main(){#(directive, stack_region_max_size=1M) {')
    source=source.replace('let incoming=p.new(8);',
        'let mut fill=pool<Int>('+str(LIMIT)+');let mut i=0;while i<'+str(LIMIT)+
        '{v.push(->fill.new(1));i=i+1;}let incoming=p.new(8);')
    return source+'}'


class AsyncHandleVectorTryPushTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_direct_success_and_capacity_failure(self):
        for source,expected in ((BASE,'1\n8\n9\n'),(full(BASE),'8\n1\n9\n')):
            run=self.run_source(source)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)
        self.refused(BASE.replace('try_push(->incoming)','try_push(incoming)'),'transfert|->')
        self.refused(BASE.replace('Ok(())','Ok(value)'),'Ok|type')
        self.refused(BASE.replace('return 1;','print(*incoming);return 1;'),'consomm|utilisable|transfér')

    def test_named_yield_move_and_annotation(self):
        source=BASE.replace('match <-v.try_push(->incoming)',
            'let r:Result<(),A<Int>>=<-v.try_push(->incoming);yield;let moved=<-r;match (->moved)')
        self.assertEqual(self.run_source(source).stdout,'1\n8\n9\n')
        self.assertEqual(self.run_source(full(source)).stdout,'8\n1\n9\n')
        self.refused(source.replace('match (->moved)','match moved'),'consomm|explicite|prototype|type')

    def test_drop_direct_and_named_only_destroy_rejected(self):
        start=BASE.index('    match <-')
        end=BASE.index('\n}\nfn main')
        for operation in ('drop(->v.try_push(->incoming));',
                          'let r=<-v.try_push(->incoming);yield;drop(->r);'):
            source=BASE[:start]+'    '+operation+'return 42;'+BASE[end:]
            for program,expected in ((source,'42\n8\n9\n'),(full(source),'42\n1\n9\n')):
                run=self.run_source(program)
                self.assertEqual(run.stdout,expected)
                self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)
            if operation.startswith('let r'):
                self.refused(source.replace('drop(->r);',''),'sans usage explicite')
                self.refused(source.replace('drop(->r);','drop(->r);drop(->r);'),'consomm|utilisable')

    def test_direct_unit_match_can_continue(self):
        source=BASE.replace('return 1;','print(1);').replace('return n;','print(n);').replace(
            '\n}\nfn main','\nreturn 42;\n}\nfn main')
        self.assertEqual(self.run_source(source).stdout,'1\n42\n8\n9\n')

    def test_borrow_last_use_and_pool_lifetime(self):
        source=BASE.replace('let incoming=p.new(8);','v.push(->p.new(7));let incoming=p.new(8);').replace(
            '    yield;', '    let view=&*v[0];yield;print(*view);')
        self.assertEqual(self.run_source(source).stdout,'7\n1\n7\n9\n')
        self.refused(source.replace('print(*view);','').replace('return 1;','print(*view);return 1;'),'emprunt|réserv')
        self.refused(BASE.replace('v:&mut Vector','v:&Vector').replace('append(&mut v,','append(&v,'),'mutable')
        self.refused(BASE.replace('    yield;', '    let mut local=pool<Int>(1);let other=local.new(6);yield;').replace(
            'try_push(->incoming)','try_push(->other)'),'pool|source|survi')

    def test_select_cleanup_preserves_inserted_value(self):
        helpers='''async fn ready()->Int{return 4;}
            async fn choose(v:&mut Vector<A<Int>>,incoming:->Int)->Int{
                let mut s=runtime::select(->append(v,->incoming),->ready());
                let n=s.await;drop(->s);return n;}'''
        source=helpers+BASE.replace('    yield;','').replace('match <-v.try_push(->incoming)',
            'let r=<-v.try_push(->incoming);yield;match (->r)').replace('spawn(->append(','spawn(->choose(')
        for program,expected in ((source,'4\n8\n9\n'),(full(source),'4\n1\n9\n')):
            run=self.run_source(program)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(sum(s.startswith('destroy ') and s.endswith('=8') for s in run.stderr.splitlines()),1)


    def test_awaited_incoming_and_named_unit_continuation(self):
        helper='async fn make(p:&mut Pool<Int>)-><-Int{yield;let n=p.new(8);return <-n;}'
        source=helper+BASE.replace('incoming:->Int','p:&mut Pool<Int>').replace(
            'try_push(->incoming)','try_push(->make(p).await)').replace('let incoming=p.new(8);','').replace(
            'append(&mut v,->incoming)','append(&mut v,&mut p)')
        self.assertEqual(self.run_source(source).stdout,'1\n8\n9\n')
        source=BASE.replace('match <-v.try_push(->incoming)',
            'let r=<-v.try_push(->incoming);yield;match (->r)').replace('return 1;','print(1);').replace(
            'return n;','print(n);').replace('\n}\nfn main','\nreturn 42;\n}\nfn main')
        self.assertEqual(self.run_source(source).stdout,'1\n42\n8\n9\n')


if __name__=='__main__':unittest.main()
