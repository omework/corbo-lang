"""VE3: inline replacement returns the old value or the unchanged incoming value."""
from pathlib import Path
import unittest
import test_select_source as harness

BASE=Path(__file__).resolve().parents[1].joinpath('validation/inline-vector-replace.crb').read_text()

class InlineVectorReplaceTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_success_and_rejection_preserve_length(self):
        self.assertEqual(self.run_source(BASE).stdout,'7\n9\n')
        for index in ('-1','1'):
            self.assertEqual(self.run_source(BASE.replace('replace(0,','replace('+index+',')).stdout,'9\n7\n')
        self.assertEqual(self.run_source(BASE.replace('let result =', 'let result: Result<Point,Point> =')).stdout,'7\n9\n')
        self.refused(BASE.replace('let result =', 'let result: Result<A<Point>,A<Point>> ='),'annotation|type')

    def test_named_value_and_explicit_transfers(self):
        source=BASE.replace('let result =', 'let incoming=Point{x:9};let result =').replace('->Point { x: 9 }','->incoming')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('match (->result)','print(incoming.x);match (->result)'), 'utilisable|déplac|consomm')
        self.refused(BASE.replace('->Point { x: 9 }','Point { x: 9 }'),'transfert|explicite')
        self.refused(BASE.replace('<-values.replace','values.replace'),'transfert|explicite')

    def test_pool_value_and_borrowed_incoming_refused(self):
        source=BASE.replace('let result =', 'let mut pp=pool<Point>(1);let incoming=pp.new(x:9);let result =').replace('->Point { x: 9 }','->incoming')
        self.refused(source,'Point|allocation|local')
        local=source.replace('let mut pp=pool<Point>(1);let incoming=pp.new(x:9);',
            'let incoming=Point{x:9};let view=&incoming;').replace('match (->result)','print(view.x);match (->result)')
        self.refused(local,'emprunt|réserv')

    def test_owned_fields_cleanup_once_and_pool_reuse(self):
        source='''struct Item{n:A<Int>}fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
            let mut vp=pool<Vector<Item>>(1);let mut v=vp.new();v.push(->Item{n:<-a});
            let r=<-v.replace(INDEX,->Item{n:<-b});drop(->v);
            match (->r){Ok(old)=>{print(*old.n);drop(->old);},Err(incoming)=>{print(*incoming.n);drop(->incoming);}}
            let x=p.new(11);let y=p.new(13);print(*x+*y);}'''
        for index,expected in (('0','7\n24\n'),('1','9\n24\n')):
            run=self.run_source(source.replace('INDEX',index));self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('destroy a=7\n'),1);self.assertEqual(run.stderr.count('destroy b=9\n'),1)
        self.refused(source.replace('INDEX','0').replace('Ok(old)=>{print(*old.n);drop(->old);}','Ok(_)=>{}'),'motif|propriétaire|allocation|usage')

    def test_borrowed_fields_survive_vector_drop(self):
        source='''struct Item{n:&Int}fn main(){let mut p=pool<Int>(2);let mut a=p.new(7);let mut b=p.new(9);
            let mut vp=pool<Vector<Item>>(1);let mut v=vp.new();v.push(->Item{n:&a});
            let r=<-v.replace(INDEX,->Item{n:&b});drop(->v);
            match (->r){Ok(old)=>{let view=old.n;drop(->old);print(*view);},Err(incoming)=>{print(*incoming.n);drop(->incoming);}}
            a=11;b=13;print(*a+*b);}'''
        for index,expected in (('0','7\n24\n'),('1','9\n24\n')):
            self.assertEqual(self.run_source(source.replace('INDEX',index)).stdout,expected)
        self.refused(source.replace('INDEX','0').replace('print(*view);','a=20;print(*view);'),'emprunt|réserv|référenc')

    def test_function_consumes_result_and_evaluation_order(self):
        source='fn update(v:&mut Vector<Point>){let r=<-v.replace(0,->Point{x:9});drop(->r);}'
        source+=BASE[:BASE.index('    let result =')]+'update(&mut values);let r=<-values.remove(0);print(r.x);}'
        self.assertEqual(self.run_source(source).stdout,'9\n')
        helper='fn index()->Int{print(1);return 0;}fn incoming()-><-Point{print(2);return <-Point{x:9};}'
        self.assertEqual(self.run_source(helper+BASE.replace('replace(0, ->Point { x: 9 })','replace(index(), ->incoming())')).stdout,'1\n2\n7\n9\n')

    def test_empty_struct_and_direct_drop(self):
        self.assertEqual(self.run_source('''struct Empty{}fn main(){let mut p=pool<Vector<Empty>>(1);let mut v=p.new();
            v.push(->Empty{});let r=<-v.replace(0,->Empty{});drop(->r);print(v.len());}''').stdout,'1\n')
        source=BASE[:BASE.index('    let result =')]+'''drop(->values.replace(0,->Point{x:9}));
            let current=<-values.remove(0);print(current.x);}'''
        self.assertEqual(self.run_source(source).stdout,'9\n')

if __name__=='__main__':unittest.main()
