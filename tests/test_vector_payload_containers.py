"""Whole vector returns retain the graphs of their active handle elements."""
from pathlib import Path
import unittest
import test_select_source as harness
BASE=Path(__file__).resolve().parents[1].joinpath('validation/open-vector-payload-container-contract.crb').read_text()
CALL='make(&mut p,&mut vp,&n)'
READ='print(*item.value);'

class VectorPayloadContainerTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_factory_and_factory_relay(self):
        helper='''fn relay(p:&mut Pool<Item>,vp:&mut Pool<Vector<A<Item>>>,n:&Int)-><-A<Vector<A<Item>>>{return <-make(p,vp,n);}'''
        for relay in (False,True):
            source=helper+BASE if relay else BASE
            if relay:source=source.replace(CALL,'relay(&mut p,&mut vp,&n)')
            run=self.run_source(source)
            self.assertEqual(run.stdout,'7\n')
            self.assertEqual(run.stderr.count('=Item\n'),1)
            for marker in ('let item=<-v.remove',READ):
                self.refused(source.replace('drop(->n);','').replace(marker,'drop(->n);'+marker),'emprunt|réserv|référenc')

    def test_transferred_input_and_relay(self):
        helper='''fn forward(v:->Vector<A<Item>>)-><-Vector<A<Item>>{return <-v;}
            fn relay(v:->Vector<A<Item>>)-><-Vector<A<Item>>{return <-forward(->v);}'''
        for name in ('forward','relay'):
            source=helper+BASE.replace('let mut v='+CALL+';',f'let initial={CALL};let mut v={name}(->initial);')
            self.assertEqual(self.run_source(source).stdout,'7\n')
            self.refused(source.replace('drop(->n);','').replace(READ,'drop(->n);'+READ),'emprunt|réserv|référenc')
        self.refused(source.replace('relay(->initial)','relay(initial)'),'transfert|->|mode attendu')

    def test_nested_owned_factory(self):
        source='''struct Inner{value:&Int}struct Item{inner:A<Inner>}
            fn read(i:&Inner)->Int{return *i.value;}
            fn make(ip:&mut Pool<Inner>,p:&mut Pool<Item>,vp:&mut Pool<Vector<A<Item>>>,n:&Int)-><-A<Vector<A<Item>>>{
                let inner=ip.new(value:n);let mut v=vp.new();v.push(->p.new(inner:<-inner));return <-v;}
            fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let mut ip=pool<Inner>(1);
                let mut p=pool<Item>(1);let mut vp=pool<Vector<A<Item>>>(1);
                let mut v=make(&mut ip,&mut p,&mut vp,&n);let item=<-v.remove(0);
                print(read(&*item.inner));drop(->item);drop(->v);let reused=ip.new(value:&n);drop(->reused);drop(->n);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('=Inner\n'),2)
        self.refused(source.replace('drop(->n);','').replace('print(read','drop(->n);print(read'),'emprunt|réserv|référenc')

    def test_mutable_target_and_reuse(self):
        source=BASE.replace('value:&Int','value:&mut Int').replace('n:&Int','n:&mut Int').replace('let n=','let mut n=').replace('&vp,&n','&vp,&mut n').replace('&mut vp,&n','&mut vp,&mut n')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        for op in ('print(*n);','n=21;'):
            self.refused(source.replace('let item=<-v.remove',op+'let item=<-v.remove'),'emprunt|réserv|référenc')

    def test_child_pool_cannot_escape_with_vector(self):
        for name,decl in (('p','let mut p=pool<Item>(1);'),('vp','let mut vp=pool<Vector<A<Item>>>(1);')):
            source=BASE.replace(decl,'').replace('let mut v='+CALL+';',f'let mut v={{{decl}let local={CALL};<-local}};')
            self.refused(source,'pool|source|survi')

    def test_conditional_factories(self):
        helper='''struct Item{value:&Int}
            fn choose(p:&mut Pool<Item>,vp:&mut Pool<Vector<A<Item>>>,a:&Int,b:&Int,c:Int)-><-A<Vector<A<Item>>>{
                if c==0{let mut v=vp.new();v.push(->p.new(value:a));return <-v;}
                else{let mut v=vp.new();v.push(->p.new(value:b));return <-v;}}'''
        main='''fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
            let mut p=pool<Item>(1);let mut vp=pool<Vector<A<Item>>>(1);
            let mut v=choose(&mut p,&mut vp,&a,&b,INDEX);let item=<-v.remove(0);
            print(*item.value);drop(->item);drop(->v);drop(->a);drop(->b);}'''
        for index,expected in ((0,'7\n'),(1,'9\n')):
            source=helper+main.replace('INDEX',str(index))
            self.assertEqual(self.run_source(source).stdout,expected)
            for name in ('a','b'):
                self.refused(source.replace(f'drop(->{name});','').replace('let item=<-v.remove',f'drop(->{name});let item=<-v.remove'),
                             'emprunt|réserv|référenc')

    def test_empty_or_filled_vector_return(self):
        source=BASE.replace('n:&Int)->','n:&Int,c:Int)->').replace(
            'v.push(->p.new(value:n));','if c==0{v.push(->p.new(value:n));}').replace(CALL,'make(&mut p,&mut vp,&n,INDEX)')
        source=source.replace('let item=<-v.remove(0);print(*item.value);drop(->item);','print(v.len());')
        for index,expected in ((0,'1\n'),(1,'0\n')):
            self.assertEqual(self.run_source(source.replace('INDEX',str(index))).stdout,expected)

    def test_modified_input_keeps_remaining_payload(self):
        helper='''fn change(v:->Vector<A<Item>>,next:->A<Item>)-><-Vector<A<Item>>{
            let mut moved=<-v;drop(->moved.remove(0));moved.push(->next);return <-moved;}'''
        source=helper+BASE.replace('pool<Int>(1)','pool<Int>(2)').replace('pool<Item>(1)','pool<Item>(2)').replace(
            'let n=ns.new(7);','let n=ns.new(7);let other=ns.new(9);').replace(
            'let mut v='+CALL+';',f'let initial={CALL};let next=p.new(value:&other);let mut v=change(->initial,->next);').replace(
            'drop(->n);','drop(->n);drop(->other);')
        self.assertEqual(self.run_source(source).stdout,'9\n')
        self.refused(source.replace('drop(->other);','').replace(READ,'drop(->other);'+READ),'emprunt|réserv|référenc')

    def test_return_after_removal_keeps_remaining_borrow(self):
        helper='''fn trim(v:->Vector<A<Item>>)-><-Vector<A<Item>>{
            let mut moved=<-v;drop(->moved.remove(0));return <-moved;}'''
        source=helper+BASE.replace('pool<Int>(1)','pool<Int>(2)').replace('pool<Item>(1)','pool<Item>(2)').replace(
            'let n=ns.new(7);','let n=ns.new(7);let other=ns.new(9);').replace(
            'let mut v='+CALL+';',f'let mut initial={CALL};initial.push(->p.new(value:&other));let mut v=trim(->initial);').replace(
            'drop(->n);','drop(->n);drop(->other);')
        self.assertEqual(self.run_source(source).stdout,'9\n')
        self.refused(source.replace('drop(->other);','').replace(READ,'drop(->other);'+READ),'emprunt|réserv|référenc')

if __name__=='__main__':unittest.main()
