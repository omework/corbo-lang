"""Sync call contracts must publish vector payload loans to an async caller."""
from pathlib import Path
import unittest
import test_select_source as harness

SOURCE=Path(__file__).resolve().parents[1].joinpath('validation/open-async-vector-payload-sync-call.crb').read_text()

class AsyncVectorPayloadContractTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_insertion_and_relay(self):
        helper='fn relay(v:&mut Vector<A<Item>>,p:&mut Pool<Item>,n:&Int){put(v,p,n);}'
        for name in ('put','relay'):
            source=helper+SOURCE.replace('put(&mut v,&mut p,&n)',name+'(&mut v,&mut p,&n)')
            self.assertEqual(self.run_source(source).stdout,'7\n')
            for marker in ('yield;let item=','yield;let result='):
                self.refused(source.replace('drop(->n);','').replace(marker,'drop(->n);'+marker),'emprunt|réserv|référenc|captur')

    def test_extraction_uses_input_payload(self):
        helper='fn take(v:&mut Vector<A<Item>>)-><-A<Item>{return <-v.remove(0);}'
        source=helper+SOURCE.replace('let item=<-v.remove(0);','let item=take(&mut v);')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('drop(->n);','').replace('yield;let result=','drop(->n);yield;let result='),'emprunt|réserv|référenc|captur')

    def test_mutable_payload_stays_exclusive(self):
        source=SOURCE.replace('value:&Int','value:&mut Int').replace('n:&Int','n:&mut Int').replace('let n=ns.new','let mut n=ns.new').replace('&mut p,&n','&mut p,&mut n')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        for access in ('print(*n);','n=20;'):
            self.refused(source.replace('yield;let item=',access+'yield;let item='),'emprunt|réserv|référenc|captur')

    def test_owned_vector_extraction_cleans_container(self):
        helper='fn take(v:->Vector<A<Item>>)-><-A<Item>{let mut items=<-v;return <-items.remove(0);}'
        source=helper+SOURCE.replace('let item=<-v.remove(0);drop(->v);','let item=take(->v);')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('drop(->n);','').replace('yield;let result=','drop(->n);yield;let result='),'emprunt|réserv|référenc|captur')

    def test_optional_extraction_and_empty_input(self):
        helper='fn take(v:&mut Vector<A<Item>>)-><-Option<A<Item>>{return <-v.pop();}'
        source=helper+SOURCE.replace('let item=<-v.remove(0);drop(->v);yield;let result=*item.value;\n drop(->item);',
            'let popped=take(&mut v);drop(->v);yield;let result=match (->popped){Some(item)=>{let x=*item.value;drop(->item);x},None=>{0}};')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('drop(->n);','').replace('let result=match','drop(->n);let result=match'),'emprunt|réserv|référenc|captur')
        self.assertEqual(self.run_source(source.replace('put(&mut v,&mut p,&n);','')).stdout,'0\n')

    def test_nested_owned_graph_through_sync_helpers(self):
        source='''struct Inner{value:&Int}struct Item{inner:A<Inner>}
        fn put(v:&mut Vector<A<Item>>,p:&mut Pool<Item>,ip:&mut Pool<Inner>,n:&Int){
            let inner=ip.new(value:n);v.push(->p.new(inner:<-inner));}
        fn take(v:&mut Vector<A<Item>>)-><-A<Item>{return <-v.remove(0);}
        fn inspect(i:&Inner)->Int{return *i.value;}
        async fn work()->Int{
            let mut ns=pool<Int>(1);let n=ns.new(7);let mut p=pool<Item>(1);let mut ip=pool<Inner>(1);
            let mut vp=pool<Vector<A<Item>>>(1);let mut v=vp.new();put(&mut v,&mut p,&mut ip,&n);
            yield;let item=take(&mut v);drop(->v);yield;let value=inspect(&*item.inner);
            drop(->item);let reused=ip.new(value:&n);drop(->reused);drop(->n);return value;
        }
        fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('=Inner\n'),2)
        short=source.replace('let mut ip=pool<Inner>(1);','').replace('put(&mut v,&mut p,&mut ip,&n);','{let mut ip=pool<Inner>(1);put(&mut v,&mut p,&mut ip,&n);}')
        short=short.replace('let reused=ip.new(value:&n);drop(->reused);','')
        self.refused(short,'pool|source|survi|durée')
        self.refused(source.replace('let reused=ip.new(value:&n);drop(->reused);','').replace('drop(->n);','').replace('yield;let value=','drop(->n);yield;let value='),'emprunt|réserv|référenc|captur')

if __name__=='__main__':unittest.main()
