"""Opaque execution handles preserve returned vector storage and loans."""
from pathlib import Path
import unittest
import test_select_source as harness
BASE=Path(__file__).resolve().parents[1].joinpath('validation/open-async-vector-payload-handle-return.crb').read_text()

class AsyncVectorPublicHandleTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def check_return(self,source):
        source=source.replace('match wait(', 'let result=wait(').replace('){Ok(received)', ');match result{Ok(received)')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('drop(->n);','').replace('match result','drop(->n);match result'),'emprunt|réserv|référenc')

    def test_recorded_public_handle(self):
        self.check_return(BASE)

    def test_handle_relay(self):
        helper='fn forward(h:->runtime::Handle<A<Vector<A<Item>>>>)-><-runtime::Handle<A<Vector<A<Item>>>>{return <-h;}'
        self.check_return(helper+BASE.replace('wait(->h)','wait(->forward(->h))'))

    def test_nested_owned_element(self):
        source=BASE.replace('struct Item{value:&Int}','struct Inner{value:&Int}struct Item{inner:A<Inner>}').replace(
            'let mut p=pool<Item>(1);','let mut p=pool<Item>(1);let mut ip=pool<Inner>(1);').replace(
            'v.push(->p.new(value:&n));','let inner=ip.new(value:&n);v.push(->p.new(inner:<-inner));').replace(
            'print(*item.value);','print(inspect(&*item.inner));')
        self.check_return('fn inspect(i:&Inner)->Int{return *i.value;}'+source)

    def test_mutable_result_exclusivity(self):
        source=BASE.replace('value:&Int','value:&mut Int').replace('let n=ns.new','let mut n=ns.new').replace('value:&n','value:&mut n')
        self.check_return(source)
        source=source.replace('match wait(->h)','let result=wait(->h);match result')
        for access in ('print(*n);','n=20;'):
            self.refused(source.replace('match result',access+'match result'),'emprunt|réserv|référenc')

if __name__=='__main__':unittest.main()
