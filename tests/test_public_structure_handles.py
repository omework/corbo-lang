"""Public structure handles preserve payload storage and returned field loans."""
from pathlib import Path
import unittest
from crust import Compiler, Parser, Error, compile_source, verify_program
from scheduler_faults import inject_submission_failure
import test_select_source as sources

ROOT = Path(__file__).resolve().parents[1]

class PublicStructureHandleTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    program = staticmethod(sources.SelectSourceTests.program)

    def test_recorded_local_structure_and_returned_loan(self):
        source = (ROOT/'validation/open-public-local-structure-handle.crb').read_text()
        self.assertEqual(self.run_source(source).stdout, '7\n1\n')
        self.assertEqual(verify_program(source).function_contracts['start'].storage_requirements, ((0,'local'),))
        for marker in ('let result=match h.await', 'yield;print(*result.target);'):
            invalid = source.replace('drop(->n);', '').replace(marker, 'drop(->n);'+marker)
            self.refused(invalid, 'emprunt|réserv|référenc')

    def test_public_parameter_relays_preserve_returned_loan(self):
        source = (ROOT/'validation/open-public-structure-handle-relays.crb').read_text()
        self.assertEqual(self.run_source(source).stdout, '7\n')
        for marker in ('let result=finish', 'print(*result.target);'):
            self.refused(source.replace('drop(->n);','').replace(marker, 'drop(->n);'+marker),
                         'emprunt|réserv|référenc')

    def test_factory_from_owned_structure_argument(self):
        source = (ROOT/'validation/open-public-local-structure-handle.crb').read_text()
        source = source.replace('fn start(t:->own)', 'fn start(v:->View)').replace('runtime::spawn(->t)', 'runtime::spawn(->own(->v))')
        source = source.replace('start(->own(->v))','start(->v)')
        self.assertEqual(self.run_source(source).stdout, '7\n1\n')
        invalid = source.replace('drop(->n);','').replace('yield;print(*result.target);','drop(->n);yield;print(*result.target);')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_annotation_keeps_local_and_pool_distinct(self):
        for asynchronous in (False, True):
            for kind, other in (('View', 'A<View>'), ('A<View>', 'View')):
                helpers = 'struct View{target:&Int}async fn own(v:->View)-><-View{yield;return <-v;}'
                if kind == 'A<View>': helpers = helpers.replace('-><-View','-><-A<View>')
                made = 'View{target:&n}' if kind == 'View' else 'vs.new(target:&n)'
                body = 'let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let n=ns.new(7);let v='+made+''';
let h:runtime::Handle<TYPE>=runtime::spawn(->own(->v));
let result=match WAIT{Ok(found)=>{<-found},Err(_)=>{return;}};
print(*result.target);drop(->result);drop(->n);'''
                if asynchronous:
                    body = body.replace('return;','return 99;').replace('WAIT','h.await')+'return 1;'
                    source = self.program(body.replace('TYPE',kind), helpers)
                    expected = '7\n1\n'
                else:
                    source = helpers+'fn main(){'+body.replace('TYPE',kind).replace('WAIT','h.join()')+'}'
                    expected = '7\n'
                self.assertEqual(self.run_source(source).stdout, expected)
                self.refused(source.replace('runtime::Handle<'+kind+'>', 'runtime::Handle<'+other+'>'), 'stockage|handle|local|allocation')

    def test_factory_contract_checks_storage_even_if_caller_drops_result(self):
        for public, init in (('View', 'View{target:&n}'), ('A<View>', 'vs.new(target:&n)')):
            for parameter, argument in (('t:->own','->own(->v)'), ('v:->View','->v')):
                call = 't' if parameter.startswith('t:') else 'own(->v)'
                helpers = 'struct View{target:&Int}async fn own(v:->View)-><-View{yield;return <-v;}'
                if public == 'A<View>': helpers = helpers.replace('-><-View','-><-A<View>')
                helpers += 'fn start('+parameter+')-><-runtime::Handle<'+public+'>{return <-runtime::spawn(->'+call+');}'
                body = 'let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let n=ns.new(7);let v='+init+''';
let h=start(ARG);let result=match h.await{Ok(found)=>{<-found},Err(_)=>{return 99;}};
drop(->result);drop(->n);return 1;'''.replace('ARG',argument)
                source = self.program(body, helpers)
                self.assertEqual(self.run_source(source).stdout, '1\n')
                wrong = 'vs.new(target:&n)' if public == 'View' else 'View{target:&n}'
                self.refused(source.replace('let v='+init, 'let v='+wrong), 'stockage|local|allocation')

    def test_exclusive_result_and_shared_reborrow_keep_writer_reserved(self):
        for mode in ('&Int', '&mut Int'):
            source = (ROOT/'validation/open-public-structure-handle-relays.crb').read_text()
            source = source.replace('target:&Int', 'target:'+mode).replace('let n=ns.new(7);','let mut n=ns.new(7);let mut writer=&mut n;')
            capture = '&*writer' if mode == '&Int' else '&mut *writer'
            source = source.replace('View{target:&n}', 'View{target:'+capture+'}')
            source = source.replace('print(*result.target);', 'BEFORE print(*result.target);')
            source = source.replace('drop(->result);', 'drop(->result);writer.set(9);')
            self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout, '7\n')
            for operation in ('writer.set(8);','print(*n);','drop(->n);'):
                self.refused(source.replace('BEFORE',operation), 'emprunt|réserv|référenc')

    def test_nested_graph_result_retains_sources_and_loans(self):
        helpers = '''struct Inner{view:&Int}struct Outer{inner:A<Inner>}
fn get(v:&Inner)->Int{return *v.view;}
async fn own(v:->Outer)-><-Outer{yield;return <-v;}
fn start(v:->Outer)-><-runtime::Handle<Outer>{return <-runtime::spawn(->own(->v));}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(7);let mut ins=pool<Inner>(1);
let inner=ins.new(view:&n);let outer=Outer{inner:<-inner};
let h=start(->outer);let result=match h.await{Ok(found)=>{<-found},Err(_)=>{return 99;}};
yield;print(get(&*result.inner));drop(->result);let next=ins.new(view:&n);drop(->next);drop(->n);return 1;'''
        source = self.program(body, helpers)
        self.assertEqual(self.run_source(source).stdout, '7\n1\n')
        self.refused(source.replace('drop(->n);','').replace('yield;print(get', 'drop(->n);yield;print(get'), 'emprunt|réserv|référenc')

    def test_public_handle_cannot_export_short_source(self):
        helpers = '''struct Point{x:Int}async fn own(v:->Point)-><-A<Point>{yield;return <-v;}
fn start(v:->Point)-><-runtime::Handle<A<Point>>{return <-runtime::spawn(->own(->v));}'''
        source = helpers+'''fn main(){let h={let mut ps=pool<Point>(1);let p=ps.new(x:7);
let h=start(->p);<-h};match h.join(){Ok(v)=>{print(v.x);drop(->v);},Err(_)=>{}}}'''
        self.refused(source, 'pool|source|survi|durable')

    def test_two_routine_types_share_a_public_structure_result(self):
        helpers = '''struct Point{x:Int}
async fn first(v:->Point)-><-Point{yield;return <-v;}
async fn second(v:->Point)-><-Point{yield;yield;return <-v;}
fn start(v:->Point,flag:bool)-><-runtime::Handle<Point>{let h=if flag{
v ->;let first_handle=runtime::spawn(->first(->v));<-first_handle
}else{v ->;let second_handle=runtime::spawn(->second(->v));<-second_handle};return <-h;}'''
        for flag in ('true','false'):
            source = helpers+'''fn main(){let p=Point{x:7};let h=start(->p,FLAG);
match h.join(){Ok(v)=>{print(v.x);drop(->v);},Err(_)=>{}}}'''.replace('FLAG',flag)
            self.assertEqual(self.run_source(source).stdout, '7\n')
            self.refused(source.replace('let p=Point{x:7};','let mut ps=pool<Point>(1);let p=ps.new(x:7);'), 'stockage|local|allocation')

    def test_public_contracts_work_without_routine_or_function_bodies(self):
        source = (ROOT/'validation/open-public-structure-handle-relays.crb').read_text()
        declarations, main = source.split('fn main(){')
        declarations = declarations.replace('start(t:->own)', 'start(v:->View)').replace('runtime::spawn(->t)', 'runtime::spawn(->own(->v))')
        interface = verify_program(declarations)
        script = main.rsplit('}',1)[0].replace('start(->own(->v))','start(->v)')
        for operation in ('', 'drop(->n);'):
            check = Compiler()
            check.contract_calls = True
            check.function_contracts = interface.function_contracts
            check.enums = interface.enums
            check.struct_fields.update(interface.struct_fields)
            actual = script.replace('drop(->n);','').replace('print(*result.target);',operation+'print(*result.target);')
            parser = Parser(actual)
            parser.structure_names.update(interface.struct_fields)
            nodes = parser.parse()
            check.index(nodes)
            if operation:
                with self.assertRaisesRegex(Error, 'emprunt|réserv|référenc'):
                    check.block('root',nodes)
            else:
                check.block('root',nodes)
            self.assertEqual(check.functions,{})
            self.assertEqual(check.async_definitions,{})

    def test_cleanup_failure_and_repeated_pool_slot_reuse(self):
        source = '''#(directive, async_pool_sizes={own:1})
struct Point{x:Int}async fn own(v:->Point)-><-A<Point>{yield;return <-v;}
fn start(v:->A<Point>)-><-runtime::Handle<A<Point>>{return <-runtime::spawn(->own(->v));}
fn main(){let mut ps=pool<Point>(1);let mut i=0;while i<3{let p=ps.new(x:i);
let h=start(->p);match h.join(){Ok(v)=>{print(v.x);drop(->v);},Err(_)=>{print(99);}}i=i+1;}
let last=ps.new(x:9);print(last.x);}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout,'0\n1\n2\n9\n')
        self.assertEqual(run.stderr.count('=Point\n'),4)
        failed = self.run_c_oracle(inject_submission_failure(compile_source(source), asynchronous=False, at=1))
        self.assertEqual(failed.stdout,'99\n1\n2\n9\n')
        self.assertEqual(failed.stderr.count('=Point\n'),4)

    def test_nested_result_preserves_local_structure_and_error_levels(self):
        source = '''struct View{target:&Int}
async fn leaf(v:->View)-><-View{yield;return <-v;}
async fn work(v:->View)-><-Result<View,runtime::Error>{let h=runtime::spawn(->leaf(->v));let result=h.await;return <-result;}
fn relay(h:->runtime::Handle<Result<View,runtime::Error>>)-><-runtime::Handle<Result<View,runtime::Error>>{return <-h;}
fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{target:&n};
let h=runtime::spawn(->work(->v));let next=relay(->h);let result=next.join();BEFORE
match result{Ok(inner)=>{match inner{Ok(v)=>{print(*v.target);drop(->v);},Err(_)=>{print(98);}}},Err(_)=>{print(99);}}drop(->n);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'7\n')
        self.refused(source.replace('drop(->n);','').replace('BEFORE','drop(->n);'), 'emprunt|réserv|référenc')
        code = compile_source(source.replace('BEFORE',''))
        for asynchronous, expected in ((False,'99\n'),(True,'98\n')):
            self.assertEqual(self.run_c_oracle(inject_submission_failure(code, asynchronous=asynchronous, at=1)).stdout, expected)

    def test_fresh_factory_and_async_branch(self):
        source = (ROOT/'validation/open-public-structure-fresh-factory.crb').read_text()
        self.assertEqual(self.run_source(source).stdout, '7\n')
        source = (ROOT/'validation/open-public-structure-local-branch.crb').read_text()
        for flag in ('true','false'):
            self.assertEqual(self.run_source(source.replace('work(true)', 'work('+flag+')')).stdout, '7\n')

    def test_async_branches_cannot_mix_local_and_pool_payloads(self):
        for annotated in (False,True):
            source = '''struct Point{x:Int}async fn own(v:->Point)-><-Point{yield;return <-v;}
async fn work(flag:Bool)->Int{let mut ps=pool<Point>(1);let local=Point{x:7};let pooled=ps.new(x:9);
let h ANNOTATION =if flag{local ->;pooled ->;drop(->pooled);let a=runtime::spawn(->own(->local));<-a
}else{local ->;pooled ->;drop(->local);let b=runtime::spawn(->own(->pooled));<-b};
let result=match h.await{Ok(found)=>{<-found},Err(_)=>{return 99;}};
let n=result.x;drop(->result);return n;}
fn main(){let h=runtime::spawn(->work(true));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
            source = source.replace('ANNOTATION', ':runtime::Handle<Point>' if annotated else '')
            self.refused(source, 'stockage|local|allocation')

if __name__ == '__main__':unittest.main()
