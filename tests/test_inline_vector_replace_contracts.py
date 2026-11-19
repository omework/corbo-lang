"""VE3/T6: the local carrier and the per-arm payload have separate contracts."""
from pathlib import Path
import unittest
import test_select_source as harness

BASE = Path(__file__).resolve().parents[1].joinpath('validation/inline-vector-replace-return.crb').read_text()

class InlineVectorReplaceContractTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_fresh_and_named_return_through_relay(self):
        for body in ('return <-v.replace(0,->Point{x:9});',
                     'let incoming=Point{x:9};let r=<-v.replace(0,->incoming);return <-r;'):
            source=BASE.replace('return <-v.replace(0,->Point{x:9});',body)
            for index,expected in (('0','7\n9\n'),('1','9\n7\n')):
                program=source.replace('v.replace(0,','v.replace('+index+',')
                program='fn relay(v:&mut Vector<Point>)-><-Result<Point,Point>{return <-replace(&mut *v);}' + program
                program=program.replace('let result = replace(&mut values);','let result=relay(&mut values);')
                self.assertEqual(self.run_source(program).stdout,expected)

    def test_conditional_returns(self):
        body='if flag==1{return <-v.replace(0,->Point{x:9});}return <-v.replace(1,->Point{x:11});'
        source=BASE.replace('replace(v:&mut Vector<Point>)','replace(v:&mut Vector<Point>,flag:Int)')
        source=source.replace('return <-v.replace(0,->Point{x:9});',body)
        for flag,expected in (('1','7\n9\n'),('0','11\n7\n')):
            program=source.replace('replace(&mut values)', 'replace(&mut values,'+flag+')')
            self.assertEqual(self.run_source(program).stdout,expected)

    def test_parameter_carrier(self):
        source=BASE.replace('replace(v:&mut Vector<Point>)', 'replace(v:&mut Vector<Point>,incoming:->Point)')
        source=source.replace('->Point{x:9}', '->incoming')
        source=source.replace('let result = replace(&mut values);','let incoming=Point{x:9};let result=replace(&mut values,->incoming);')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('match (->result)', 'print(incoming.x);match(->result)'), 'utilisable|déplac|consomm')

    def test_owned_payloads_in_both_arms(self):
        source='''struct Item{n:A<Int>}
        fn change(v:&mut Vector<Item>,n:->A<Int>,i:Int)-><-Result<Item,Item>{return <-v.replace(i,->Item{n:<-n});}
        fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
        let mut vp=pool<Vector<Item>>(1);let mut v=vp.new();v.push(->Item{n:<-a});
        let r=change(&mut v,->b,INDEX);drop(->v);
        match(->r){Ok(old)=>{print(*old.n);drop(->old);},Err(incoming)=>{print(*incoming.n);drop(->incoming);}}
        let x=p.new(11);let y=p.new(13);print(*x+*y);}'''
        for index,expected in (('0','7\n24\n'),('1','9\n24\n')):
            run=self.run_source(source.replace('INDEX',index));self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('destroy a=7\n'),1)
            self.assertEqual(run.stderr.count('destroy b=9\n'),1)

    def test_borrowed_payloads_and_last_use(self):
        source='''struct Item{n:&Int}
        fn change(v:&mut Vector<Item>,n:&Int,i:Int)-><-Result<Item,Item>{return <-v.replace(i,->Item{n:&*n});}
        fn main(){let mut p=pool<Int>(2);let mut a=p.new(7);let mut b=p.new(9);
        let mut vp=pool<Vector<Item>>(1);let mut v=vp.new();v.push(->Item{n:&a});
        let r=change(&mut v,&b,INDEX);drop(->v);
        match(->r){Ok(old)=>{print(*old.n);drop(->old);},Err(incoming)=>{print(*incoming.n);drop(->incoming);}}
        a=11;b=13;print(*a+*b);}'''
        for index,expected in (('0','7\n24\n'),('1','9\n24\n')):
            self.assertEqual(self.run_source(source.replace('INDEX',index)).stdout,expected)
        for name in ('a','b'):
            self.refused(source.replace('INDEX','0').replace('match(->r)',name+'=20;match(->r)'), 'emprunt|réserv|référenc')

    def test_result_parameter_preserves_local_storage(self):
        helper='fn identity(r:->Result<Point,Point>)-><-Result<Point,Point>{return <-r;}'
        source=helper+BASE.replace('match (->result)', 'let relayed=identity(->result);match (->relayed)')
        for index,expected in (('0','7\n9\n'),('1','9\n7\n')):
            self.assertEqual(self.run_source(source.replace('v.replace(0,','v.replace('+index+',')).stdout,expected)
        self.refused(source.replace('identity(r:->Result<Point,Point>)',
                                    'identity(r:->Result<A<Point>,A<Point>>)'),'type|stockage|local|transféré|allocation')
        self.refused(source.replace('return <-r;','return r;'),'explicite|transfert')

    def test_result_parameter_preserves_payload_graph(self):
        source='struct Item{n:FIELD}\n        fn relay(r:->Result<Item,Item>)-><-Result<Item,Item>{return <-r;}\n        fn change(v:&mut Vector<Item>,n:->Item,i:Int)-><-Result<Item,Item>{return <-v.replace(i,->n);}\n        fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);\n        let mut vp=pool<Vector<Item>>(1);let mut v=vp.new();v.push(->Item{n:LEFT});\n        let incoming=Item{n:RIGHT};let first=change(&mut v,->incoming,INDEX);\n        let r=relay(->first);drop(->v);\n        match(->r){Ok(old)=>{print(*old.n);drop(->old);},Err(other)=>{print(*other.n);drop(->other);}}}'
        for field,left,right in (('A<Int>','<-a','<-b'),('&Int','&a','&b')):
            for index,expected in (('0','7\n'),('1','9\n')):
                program=source.replace('FIELD',field).replace('LEFT',left).replace('RIGHT',right).replace('INDEX',index)
                self.assertEqual(self.run_source(program).stdout,expected)

    def test_local_allocation_types_stay_distinct(self):
        self.refused(BASE.replace('Result<Point,Point>','Result<A<Point>,A<Point>>'),'local|allocation|stockage|type')

if __name__=='__main__':unittest.main()
