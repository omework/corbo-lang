"""Storage obligations of opaque task results; T never silently becomes A<T>."""
from pathlib import Path
import unittest
from crust import verify_program
import test_select_source as sources

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'struct Point{x:Int} async fn own(p:->Point)-><-Point{yield;return <-p;}'


def helper(kind='local'):
    typ = 'Point' if kind == 'local' else 'A<Point>'
    return 'fn consume(t:->own)->Int{let h=runtime::spawn(->t);let p:'+typ+'''=match h.join(){
Ok(v)=>{<-v},Err(_)=>{return 99;}};let x=p.x;drop(->p);return x;}'''


class TaskResultStorageTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    program = staticmethod(sources.SelectSourceTests.program)

    def test_recorded_local_result(self):
        source = (ROOT/'validation/open-task-result-storage-contract.crb').read_text()
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.assertEqual(verify_program(source).function_contracts['consume'].storage_requirements, ((0,'local'),))

    def test_storage_matrix_and_relays(self):
        # Independent finite model: input storage must equal the annotation.
        for required in ('local', 'pool'):
            helpers = helper(required) + '''fn relay(t:->own)->Int{return consume(->t);}
fn outer(t:->own)->Int{return relay(->t);}'''
            for actual in ('local', 'pool'):
                value = 'Point{x:7}' if actual == 'local' else 'ps.new(x:7)'
                source = (PREFIX if required == 'local' else PREFIX.replace('-><-Point','-><-A<Point>')) + helpers + 'fn main(){let mut ps=pool<Point>(1);let p='+value+''';
let t=own(->p);print(outer(->t));}'''
                with self.subTest(required=required, actual=actual):
                    if actual != required:
                        self.refused(source, 'stockage|local|allocation')
                    else:
                        self.assertEqual(self.run_source(source).stdout, '7\n')
                        check = verify_program(source)
                        for name in ('consume', 'relay', 'outer'):
                            self.assertEqual(check.function_contracts[name].storage_requirements, ((0,required),))

    def test_sync_wait_cannot_be_hidden_in_async_call(self):
        source = self.program('let p=Point{x:7};return consume(->own(->p));', PREFIX+helper())
        self.refused(source, 'join réservé au code synchrone')

    def test_conditional_task_input_requires_each_result(self):
        helpers = helper() + '''fn choose(a:->own,b:->own,flag:bool)->Int{
let task=if flag{a ->;b ->;drop(->b);<-a}else{a ->;b ->;drop(->a);<-b};return consume(->task);}'''
        for flag, expected in (('true', '7\n'), ('false', '9\n')):
            source = PREFIX+helpers+'''fn main(){let mut ps=pool<Point>(1);
let a=Point{x:7};let b=Point{x:9};print(choose(->own(->a),->own(->b),FLAG));}'''.replace('FLAG',flag)
            self.assertEqual(self.run_source(source).stdout, expected)
            self.assertEqual(verify_program(source).function_contracts['choose'].storage_requirements, ((0,'local'),(1,'local')))
            for name, n in (('a',7), ('b',9)):
                self.refused(source.replace('let '+name+'=Point{x:'+str(n)+'}', 'let '+name+'=ps.new(x:'+str(n)+')'), 'stockage|local|allocation')

    def test_known_fresh_storage_is_not_reclassified(self):
        for annotation in ('Point','A<Point>'):
            source = '''struct Point{x:Int} async fn own()-><-Point{yield;let p=Point{x:7};return <-p;}
fn consume(t:->own)->Int{let h=runtime::spawn(->t);let p:TYPE=match h.join(){
Ok(v)=>{<-v},Err(_)=>{return 99;}};let x=p.x;drop(->p);return x;}
fn main(){print(consume(->own()));}'''.replace('TYPE', annotation)
            if annotation == 'Point':
                self.assertEqual(self.run_source(source).stdout, '7\n')
            else:
                self.refused(source, 'stockage|local|allocation')

    def test_launched_handle_contract_and_relay(self):
        for kind in ('local', 'pool'):
            value = 'Point{x:7}' if kind == 'local' else 'ps.new(x:7)'
            helpers = helper(kind).replace('t:->own', 'h:->Execution<own>').replace('let h=runtime::spawn(->t);', '')
            helpers += 'fn relay(h:->Execution<own>)->Int{return consume(->h);}'
            source = (PREFIX if kind == 'local' else PREFIX.replace('-><-Point','-><-A<Point>'))+helpers+'fn main(){let mut ps=pool<Point>(1);let p='+value+''';
let h=runtime::spawn(->own(->p));print(relay(->h));}'''
            self.assertEqual(self.run_source(source).stdout, '7\n')
            check = verify_program(source)
            self.assertEqual(check.function_contracts['relay'].storage_requirements, ((0,kind),))
            wrong = 'ps.new(x:7)' if kind == 'local' else 'Point{x:7}'
            self.refused(source.replace('let p='+value, 'let p='+wrong), 'stockage|local|allocation')

    def test_result_storage_is_distinct_from_other_captures(self):
        prefix = '''struct Point{x:Int}
async fn own(p:->Point,other:->Point)-><-Point{yield;drop(->other);return <-p;}'''
        for kind in ('local', 'pool'):
            returned = 'Point{x:7}' if kind == 'local' else 'ps.new(x:7)'
            other = 'ps.new(x:9)' if kind == 'local' else 'Point{x:9}'
            source = (prefix if kind == 'local' else prefix.replace('-><-Point','-><-A<Point>'))+helper(kind)+'fn main(){let mut ps=pool<Point>(2);let p='+returned+';let other='+other+''';
print(consume(->own(->p,->other)));}'''
            self.assertEqual(self.run_source(source).stdout, '7\n')
            self.refused(source.replace('let p='+returned, 'let p='+other), 'stockage|local|allocation')

    def test_result_annotation_does_not_release_borrow(self):
        prefix = '''struct View{target:&Int}
async fn own(v:->View)-><-View{yield;return <-v;}
fn consume(t:->own)-><-View{let h=runtime::spawn(->t);let v:View=match h.join(){
Ok(found)=>{<-found},Err(_)=>{loop{}}};return <-v;}
fn relay(t:->own)-><-View{return <-consume(->t);}'''
        source = prefix+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{target:&n};
let result=relay(->own(->v));BEFORE print(*result.target);drop(->result);drop(->n);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout, '7\n')
        self.refused(source.replace('BEFORE','drop(->n);').replace('drop(->result);drop(->n);','drop(->result);'), 'emprunt|réserv|référenc')

    def test_copy_from_borrowed_capture(self):
        source = (ROOT/'validation/open-task-result-storage-copy.crb').read_text()
        for kind in ('local', 'pool'):
            typed = source if kind == 'local' else source.replace('let p:Point=', 'let p:A<Point>=').replace('-><-Point','-><-A<Point>')
            inputs = ('let mut ps=pool<Point>(2);let p=Point{x:7};' if kind == 'local'
                      else 'let mut ps=pool<Point>(2);let p=ps.new(x:7);')
            typed = typed.replace('let p=Point{x:7};', inputs)
            self.assertEqual(self.run_source(typed).stdout, '7\n')
            wrong = 'let p=ps.new(x:7);' if kind == 'local' else 'let p=Point{x:7};'
            self.refused(typed.replace(inputs, 'let mut ps=pool<Point>(2);'+wrong), 'stockage|local|allocation')

    def test_fresh_local_root_keeps_pool_descendant(self):
        source = (ROOT/'validation/open-task-result-storage-graph.crb').read_text()
        source = source.replace('print(consume(->own(->p)));',
                                'print(consume(->own(->p)));let next=ps.new(x:9);print(next.x);')
        run = self.run_source(source)
        self.assertEqual(run.stdout, '7\n9\n')
        self.assertEqual(run.stderr.count('=Outer\n'), 1)
        self.assertEqual(run.stderr.count('=Inner\n'), 2)
        self.refused(source.replace('let p:Outer=', 'let p:A<Outer>='), 'stockage|local|allocation')

    def test_declared_pool_result_cannot_be_given_local_requirement(self):
        # Even an uncalled helper cannot require an impossible instantiation.
        source = PREFIX.replace('p:->Point', 'p:->A<Point>').replace('-><-Point','-><-A<Point>')+helper()
        self.refused(source, 'stockage.*incompatible')
        source = '''struct Point{x:Int}
async fn own(ps:&mut Pool<Point>)-><-A<Point>{yield;return <-ps.new(x:7);}'''+helper()
        self.refused(source, 'stockage.*incompatible')


if __name__ == '__main__':
    unittest.main()
