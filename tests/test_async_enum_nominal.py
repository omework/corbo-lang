"""Nominal references stored in enum arms retain descriptors across suspension."""
import unittest
import test_select_source as harness

TYPES = 'struct Point{x:Int}struct Pair{a:Point,b:Point}'
INIT = 'let mut pair=Pair{a:Point{x:1},b:Point{x:7}};'

class AsyncEnumNominalTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_shared_projection_and_return(self):
        helpers = TYPES+'''enum View{One{p:&Point},Two{pad:Int,p:&Point}}
            async fn read(v:->View)->&Point{
                let r=match &v{View.One{p:r}=>{yield;r},View.Two{pad:_,p:r}=>{yield;r}};
                return r;}'''
        for arm, fields in (('One','p:&pair.b'),('Two','pad:9,p:&pair.b')):
            source=helpers+'fn main(){'+INIT+'''let mut vs=pool<View>(1);
                let v=new(vs) View.ARM{FIELDS};let h=runtime::spawn(->read(->v));
                match h.join(){Ok(r)=>{print(r.x);},Err(_)=>{print(99);}}
                let again=new(vs) View.ARM{FIELDS};drop(->again);pair.b.x=20;print(pair.b.x);}'''
            source=source.replace('ARM',arm).replace('FIELDS',fields)
            self.assertEqual(self.run_source(source).stdout,'7\n20\n')
            self.refused(source.replace('print(r.x);','pair.b.x=30;print(r.x);'),'emprunt|réserv|référenc')

    def test_mutable_projection_reborrow(self):
        helpers=TYPES+'''enum Writer{One{p:&mut Point}}
            fn borrow(p:&mut Point)->&mut Point{return p;}
            async fn edit(w:&mut Writer)->Int{let n=match &mut w{
                Writer.One{p:r}=>{let mut other=borrow(r);yield;other.x=20;r.x=30;r.x}};return n;}'''
        source=helpers+'fn main(){'+INIT+'''let mut ws=pool<Writer>(1);
            let mut w=new(ws) Writer.One{p:&mut pair.b};let h=runtime::spawn(->edit(&mut w));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}drop(->w);print(pair.b.x);}'''
        self.assertEqual(self.run_source(source).stdout,'30\n30\n')
        self.refused(source.replace('r.x=30;r.x','r.x=30;print(other.x);r.x'),'emprunt|réserv|référenc|incompatible')

    def test_mutable_result_reserves_carrier_and_target(self):
        helpers=TYPES+'''enum Writer{One{p:&mut Point}}
            async fn get(w:&mut Writer)->&mut Point{
                let mut r=match &mut w{Writer.One{p:r}=>{yield;r}};return r;}'''
        source=helpers+'fn main(){'+INIT+'''let mut ws=pool<Writer>(1);
            let mut w=new(ws) Writer.One{p:&mut pair.b};let h=runtime::spawn(->get(&mut w));
            match h.join(){Ok(r)=>{r.x=31;print(r.x);},Err(_)=>{print(99);}}
            drop(->w);print(pair.b.x);}'''
        self.assertEqual(self.run_source(source).stdout,'31\n31\n')
        self.refused(source.replace('r.x=31;', 'pair.b.x=90;r.x=31;'),'emprunt|réserv|référenc')
        self.refused(source.replace('r.x=31;', 'print(w);r.x=31;'),'emprunt|réserv|référenc|incompatible')

    def test_consuming_match_detaches_reference_and_reuses_slot(self):
        helpers=TYPES+'''enum View{One{p:&Point}}
            async fn consume(v:->View)->&Point{
                let r=match (->v){View.One{p:r}=>{yield;r}};return r;}'''
        source=helpers+'fn main(){'+INIT+'''let mut vs=pool<View>(1);
            let v=new(vs) View.One{p:&pair.b};let h=runtime::spawn(->consume(->v));
            match h.join(){Ok(r)=>{let next=new(vs) View.One{p:&pair.a};print(r.x);drop(->next);},Err(_)=>{print(99);}}}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy v=View.One\n'),1)
        self.refused(source.replace('print(r.x);','pair.b.x=90;print(r.x);'),'emprunt|réserv|référenc')

    def test_async_construction_and_child_await(self):
        helpers=TYPES+'''enum View{One{p:&Point}}
            async fn read(v:->View)->Int{
                let n=match &v{View.One{p:r}=>{yield;r.x}};return n;}
            async fn work(p:&Point)->Int{let mut vs=pool<View>(1);
                let v=new(vs) View.One{p:p};let n=read(->v).await;
                let next=new(vs) View.One{p:p};drop(->next);return n;}'''
        source=helpers+'fn main(){'+INIT+'''let h=runtime::spawn(->work(&pair.b));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')

if __name__=='__main__':unittest.main()
