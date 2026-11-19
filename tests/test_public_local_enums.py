"""Opaque public handles retain local enum payloads and borrowed dependencies."""
import unittest
import test_select_source as harness
from crust import compile_source
from scheduler_faults import inject_submission_failure

TYPES='enum Choice{One{x:Int},Two{x:Int,y:Int},Empty{}}'
READ='fn read(c:&Choice)->Int{return match &c{Choice.One{x:x}=>{x},Choice.Two{x:x,y:y}=>{x+y},Choice.Empty{}=>{0}};}'

class PublicLocalEnumTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_public_factory_and_join_helper(self):
        helpers=TYPES+READ+'''async fn make()-><-Choice{let c=Choice.Two{x:9,y:11};yield;return <-c;}
fn start()-><-runtime::Handle<Choice>{return <-runtime::spawn(->make());}
fn finish(h:->runtime::Handle<Choice>)-><-Result<Choice,runtime::Error>{return <-h.join();}'''
        source=helpers+'''fn main(){let h=start();match finish(->h){Ok(c)=>{print(read(&c));drop(->c);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_source(source).stdout,'20\n')
        failed=self.run_c_oracle(inject_submission_failure(compile_source(source),asynchronous=False,at=1))
        self.assertEqual(failed.stdout,'99\n')
        self.refused(source.replace('Handle<Choice>', 'Handle<A<Choice>>'),'stockage|local|allocation|handle')

    def test_public_handle_await_and_two_routines(self):
        helpers=TYPES+READ+'''async fn one()-><-Choice{let c=Choice.One{x:7};yield;return <-c;}
async fn two()-><-Choice{let c=Choice.Two{x:9,y:11};yield;return <-c;}
fn start(flag:bool)-><-runtime::Handle<Choice>{if flag{return <-runtime::spawn(->one());}
return <-runtime::spawn(->two());}'''
        for flag,value in (('true',7),('false',20)):
            source=self.program('''let h=start(FLAG);let result=h.await;
let c=match result{Ok(c)=>{<-c},Err(_)=>{return 99;}};
yield;let n=read(&c);drop(->c);return n;'''.replace('FLAG',flag),helpers)
            self.assertEqual(self.run_source(source).stdout,str(value)+'\n')

    def test_result_keeps_shared_target(self):
        helpers='''enum View{One{n:&Int},Empty{}}
async fn make(n:&Int)-><-View{let v=View.One{n:n};yield;return <-v;}
fn start(n:&Int)-><-runtime::Handle<View>{return <-runtime::spawn(->make(n));}
fn finish(h:->runtime::Handle<View>)-><-Result<View,runtime::Error>{return <-h.join();}'''
        source=helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=start(&n);
let v=match finish(->h){Ok(v)=>{<-v},Err(_)=>{return;}};
match &v{View.One{n:r}=>{print(*r);},View.Empty{}=>{}}drop(->v);drop(->n);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('match &v{', 'drop(->n);match &v{'),'emprunt|référenc|survi|invalide')

    def test_result_keeps_mutable_target(self):
        helpers='''enum Writer{One{n:&mut Int},Empty{}}
async fn make(n:&mut Int)-><-Writer{let w=Writer.One{n:n};yield;return <-w;}
fn start(n:&mut Int)-><-runtime::Handle<Writer>{return <-runtime::spawn(->make(n));}'''
        source=self.program('''let mut ns=pool<Int>(1);let mut n=ns.new(7);let h=start(&mut n);
let w=match h.await{Ok(w)=>{<-w},Err(_)=>{return 99;}};
match &mut w{Writer.One{n:r}=>{r.set(20);print(*r);},Writer.Empty{}=>{}}
drop(->w);print(*n);return 1;'''.replace('let w=match','let mut w=match'),helpers)
        self.assertEqual(self.run_source(source).stdout,'20\n20\n1\n')
        for op in ('n=30;', 'drop(->n);'):
            self.refused(source.replace('match &mut w{',op+'match &mut w{'),'emprunt|référenc|réserv|invalide')

    def test_owned_payload_retains_source_and_cleans_once(self):
        helpers='''enum Boxed{One{n:A<Int>},Empty{}}
async fn make(n:->Int)-><-Boxed{let b=Boxed.One{n:<-n};yield;return <-b;}
fn start(n:->Int)-><-runtime::Handle<Boxed>{return <-runtime::spawn(->make(->n));}
fn finish(h:->runtime::Handle<Boxed>)-><-Result<Boxed,runtime::Error>{return <-h.join();}'''
        source=helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=start(->n);
let b=match finish(->h){Ok(b)=>{<-b},Err(_)=>{return;}};
match (->b){Boxed.One{n:n}=>{print(*n);drop(->n);},Boxed.Empty{}=>{}}
let next=ns.new(20);print(*next);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n20\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.refused(source.replace('match (->b){','drop(->ns);match (->b){'),'source|pool|allocation|utilis')

if __name__=='__main__':unittest.main()
