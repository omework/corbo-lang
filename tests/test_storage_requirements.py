"""Storage-kind contracts propagate through calls without weakening type checks."""
from pathlib import Path
import unittest
from crust import verify_program
import test_async_local_captures as captures

ROOT=Path(__file__).resolve().parents[1]
PREFIX=captures.PREFIX
DUPLICATE='fn duplicate(p:&Point)-><-Point{let q=copy(p);return <-q;}'
POOL_DUPLICATE='fn duplicate_pool(p:&Point)-><-A<Point>{let q=copy(p);return <-q;}'

class StorageRequirementTests(unittest.TestCase):
    run_source=captures.AsyncLocalCaptureTests.run_source
    run_c_oracle=captures.AsyncLocalCaptureTests.run_c_oracle
    refused=captures.AsyncLocalCaptureTests.refused
    program=staticmethod(captures.AsyncLocalCaptureTests.program)

    def test_owned_field_storage_is_independent_of_carrier(self):
        helpers='''struct Item{value:Int}enum Wrapper{Hold{item:A<Item>}}
fn extract(w:->Wrapper)-><-A<Item>{
    let result:A<Item>=match (->w){Wrapper.Hold{item:child}=>{<-child}};
    return <-result;
}'''
        for carrier in ('Wrapper.Hold{item:<-item}', 'new(wrappers) Wrapper.Hold{item:<-item}'):
            source=helpers+'''fn main(){let mut items=pool<Item>(1);
let mut wrappers=pool<Wrapper>(1);let item=items.new(value:7);
let wrapper='''+carrier+''';let result=extract(->wrapper);print(result.value);}'''
            self.assertEqual(self.run_source(source).stdout,'7\n')
            self.refused(source.replace('let result:A<Item>', 'let result:Item'),
                         'stockage local incompatible.*champ allocation')

    def test_recorded_annotation(self):
        source=(ROOT/'validation/open-async-local-only-copy-annotation.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')
        check=verify_program(source)
        self.assertEqual(check.async_definitions['leaf'][0].storage_requirements,((0,'local'),))

    def test_pool_caller_cannot_satisfy_local_annotation(self):
        source=PREFIX+DUPLICATE+'''async fn leaf(p:&Point)->Int{let q:Point=duplicate(p);yield;return q.x;}
            fn main(){let mut points=pool<Point>(2);let p=points.new(x:7);let h=runtime::spawn(->leaf(&p));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.refused(source,'stockage|local|allocation')
        source=self.program('let p=make(7);return leaf(&p).await;',DUPLICATE+
                'async fn leaf(p:&Point)->Int{let q:A<Point>=duplicate(p);yield;return q.x;}')
        self.refused(source,'stockage|local|allocation')

    def test_sync_helper_requirement_and_async_relay(self):
        helpers='''fn duplicate(p:&Point)-><-Point{let q:Point=copy(p);return <-q;}
            async fn leaf(p:&Point)->Int{let q=duplicate(p);yield;return q.x;}
            async fn relay(p:&Point)->Int{yield;return leaf(p).await;}'''
        source=self.program('let p=make(7);return relay(&p).await;',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        check=verify_program(source)
        self.assertEqual(check.function_contracts['duplicate'].storage_requirements,((0,'local'),))
        for name in ('leaf','relay'):
            self.assertEqual(check.async_definitions[name][0].storage_requirements,((0,'local'),))

    def test_sync_factory_preserves_requirement(self):
        helpers=DUPLICATE+'''async fn leaf(p:&Point)->Int{let q:Point=duplicate(p);yield;return q.x;}
            fn factory(p:&Point)-><-leaf{return <-leaf(p);}
            fn again(p:&Point)-><-leaf{return <-factory(p);}'''
        source=PREFIX+helpers+'''fn main(){let p=make(9);let task=again(&p);let h=runtime::spawn(->task);
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_source(source).stdout,'9\n')
        check=verify_program(source)
        for name in ('factory','again'):
            self.assertEqual(check.function_contracts[name].storage_requirements,((0,'local'),))
        self.refused(source.replace('let p=make(9);','let mut points=pool<Point>(2);let p=points.new(x:9);'),
                     'stockage|local|allocation')

    def test_two_possible_sources_require_both_local(self):
        helpers=DUPLICATE+'''fn choose(a:&Point,b:&Point,flag:Int)-><-Point{
            if flag==1{return <-duplicate(a);}return <-duplicate(b);}
            async fn leaf(a:&Point,b:&Point,flag:Int)->Int{let q:Point=choose(a,b,flag);yield;return q.x;}'''
        for flag,expected in (('1','7\n'),('0','9\n')):
            source=self.program('let a=make(7);let b=make(9);return leaf(&a,&b,'+flag+').await;',helpers)
            self.assertEqual(self.run_source(source).stdout,expected)
            self.assertEqual(verify_program(source).async_definitions['leaf'][0].storage_requirements,
                             ((0,'local'),(1,'local')))

    def test_incompatible_requirements_rejected(self):
        source=PREFIX+DUPLICATE+'''async fn leaf(p:&Point)->Int{
            let a:Point=duplicate(p);let b:A<Point>=duplicate(p);return a.x+b.x;}'''
        self.refused(source,'stockage.*incompatibles')

    def test_requirements_do_not_relax_borrow_lifetime(self):
        helpers=DUPLICATE+'async fn leaf(p:&Point)->Int{let q:Point=duplicate(p);yield;return q.x;}'
        source=self.program('let p=make(7);let task=leaf(&p);BEFORE let n=task.await;drop(->p);return n;',helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'7\n')
        self.refused(source.replace('BEFORE','drop(->p);'),'emprunt|réserv|référenc')

    def test_pool_requirement_accepts_matching_source(self):
        source=PREFIX+POOL_DUPLICATE+'''async fn leaf(p:&Point)->Int{let q:A<Point>=duplicate_pool(p);yield;return q.x;}
            fn main(){let mut points=pool<Point>(2);let p=points.new(x:8);let h=runtime::spawn(->leaf(&p));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_source(source).stdout,'8\n')
        self.assertEqual(verify_program(source).async_definitions['leaf'][0].storage_requirements,((0,'pool'),))

    def test_two_parameter_storage_model(self):
        for mask in range(4):
            types=['Point' if mask & (1<<i) else 'A<Point>' for i in range(2)]
            inputs=['make('+str(i+2)+')' if mask & (1<<i) else 'points.new(x:'+str(i+2)+')'
                    for i in range(2)]
            source=PREFIX+DUPLICATE+POOL_DUPLICATE+'''async fn leaf(a:&Point,b:&Point)->Int{
                let x:TYPE0=COPY0(a);yield;let y:TYPE1=COPY1(b);return x.x+y.x;}
                fn main(){let mut points=pool<Point>(4);let a=INPUT0;let b=INPUT1;
                    let h=runtime::spawn(->leaf(&a,&b));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
            for i in range(2):
                source=source.replace('TYPE'+str(i),types[i]).replace('INPUT'+str(i),inputs[i])
                source=source.replace('COPY'+str(i),'duplicate' if mask & (1<<i) else 'duplicate_pool')
            with self.subTest(mask=mask):
                self.assertEqual(self.run_source(source).stdout,'5\n')
                expected=tuple((i,'local' if mask & (1<<i) else 'pool') for i in range(2))
                self.assertEqual(verify_program(source).async_definitions['leaf'][0].storage_requirements,expected)
                wrong='points.new(x:2)' if mask & 1 else 'make(2)'
                self.refused(source.replace('let a='+inputs[0], 'let a='+wrong),'stockage|local|allocation')

    def test_annotation_combines_with_select_and_conversion(self):
        helpers=DUPLICATE+'''async fn byte()->u8{yield;return 3;}
            async fn leaf(p:&Point)->Int{let q:Point=duplicate(p);
                let mut selection=runtime::select(->byte());let n=selection.await;
                drop(->selection);return q.x+(n as Int);}'''
        source=self.program('let p=make(7);return leaf(&p).await;',helpers)
        self.assertEqual(self.run_source(source).stdout,'10\n')

if __name__=='__main__':unittest.main()
