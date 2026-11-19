"""Enum values use implicit local storage while preserving their active layout."""
import unittest
import test_select_source as harness

TYPES='enum Choice{One{x:Int},Two{x:Int,y:Int},Empty{}}'
READ='fn read(c:&Choice)->Int{return match &c{Choice.One{x:x}=>{x},Choice.Two{x:x,y:y}=>{x+y},Choice.Empty{}=>{0}};}'

class LocalEnumTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_sync_literals_and_match(self):
        source=TYPES+READ+'''fn main(){let a=Choice.One{x:7};let b=Choice.Two{x:9,y:11};let e=Choice.Empty{};
print(read(&a));print(read(&b));print(read(&e));print(b);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n20\n0\nChoice.Two(9, 11)\n')
        self.refused(source.replace('Choice.Two{x:9,y:11}', 'Choice.Two{x:9}'),'champ')

    def test_async_literals_and_match(self):
        body='''let a=Choice.One{x:7};let b=Choice.Two{x:9,y:11};yield;
let n=match &b{Choice.One{x:x}=>{x},Choice.Two{x:x,y:y}=>{yield;x+y},Choice.Empty{}=>{0}};
print(read(&a));print(b);return n;'''
        self.assertEqual(self.run_source(self.program(body,TYPES+READ)).stdout,'7\nChoice.Two(9, 11)\n20\n')

    def test_sync_conditional_return(self):
        helper='''fn make(flag:bool)-><-Choice{if flag{let a=Choice.One{x:7};return <-a;}
let b=Choice.Two{x:9,y:11};return <-b;}'''
        for flag,expected in (('true',7),('false',20)):
            source=TYPES+READ+helper+'fn main(){let c=make('+flag+');print(read(&c));}'
            self.assertEqual(self.run_source(source).stdout,str(expected)+'\n')

    def test_async_return_and_sync_helper(self):
        helper='''fn make()-><-Choice{let c=Choice.Two{x:9,y:11};return <-c;}
async fn produce()-><-Choice{let c=make();yield;return <-c;}'''
        source=TYPES+READ+helper+'''fn main(){let h=runtime::spawn(->produce());
match h.join(){Ok(c)=>{print(read(&c));drop(->c);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_source(source).stdout,'20\n')

    def test_local_reference_cannot_escape(self):
        source='''enum View{One{n:&Int}}async fn bad()-><-View{
let mut p=pool<Int>(1);let n=p.new(7);let v=View.One{n:&n};return <-v;}
fn main(){let t=bad();drop(->t);}'''
        self.refused(source,'emprunt|local|survi|durable|référenc')

    def test_async_direct_return_and_local_capture(self):
        helpers='''async fn make(flag:Bool)-><-Choice{if flag{let c=Choice.One{x:7};yield;return <-c;}
let c=Choice.Two{x:9,y:11};yield;return <-c;}
async fn relay(c:->Choice)-><-Choice{yield;return <-c;}
async fn work(flag:Bool)->Int{let c=make(flag).await;let r=relay(->c).await;return read(&r);}'''
        for flag,expected in (('true',7),('false',20)):
            source=TYPES+READ+helpers+'''fn main(){let h=runtime::spawn(->work(FLAG));
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''.replace('FLAG',flag)
            self.assertEqual(self.run_source(source).stdout,str(expected)+'\n')

    def test_parent_receivers_and_loop_exit(self):
        body='''let c={let e=Choice.Two{x:9,y:11};yield;<-e};
let d=loop{let e=Choice.One{x:7};yield;break <-e;};
print(read(&c));return read(&d);'''
        self.assertEqual(self.run_source(self.program(body,TYPES+READ)).stdout,'20\n7\n')
        sync=TYPES+READ+'''fn main(){let c=if 1==1{let e=Choice.Two{x:9,y:11};<-e}
else{let e=Choice.Empty{};<-e};print(read(&c));}'''
        self.assertEqual(self.run_source(sync).stdout,'20\n')

    def test_owned_child_and_reference_cleanup(self):
        helpers='''enum Boxed{One{n:A<Int>,view:&Int},Empty{}}
async fn make(p:&mut Pool<Int>,view:&Int)-><-Boxed{
let n=p.new(7);let e=Boxed.One{n:<-n,view:view};yield;return <-e;}'''
        source=helpers+'''fn main(){let mut ns=pool<Int>(1);let mut vs=pool<Int>(1);let v=vs.new(11);
let h=runtime::spawn(->make(&mut ns,&v));match h.join(){Ok(e)=>{
match (->e){Boxed.One{n:n,view:r}=>{print(*n);print(*r);drop(->n);},Boxed.Empty{}=>{}}
},Err(_)=>{}}let next=ns.new(20);print(*next);drop(->v);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n11\n20\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.refused(source.replace('print(*r);', 'drop(->v);print(*r);'), 'emprunt|référenc|survi|transfert')

if __name__=='__main__':unittest.main()
