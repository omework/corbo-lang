"""Direct async structure borrows survive extraction of the task result."""
import unittest
import test_select_source as harness

TYPES = 'struct Point{x:Int}struct Pair{a:Point,b:Point}'
INIT = 'let mut pair=Pair{a:Point{x:1},b:Point{x:7}};'


class AsyncNominalResultTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def source(self, helpers, body):
        return TYPES+helpers+'fn main(){'+INIT+body+'}'

    def test_shared_join_whole_and_interior_targets(self):
        helpers = 'async fn identity(p:&Point)->&Point{yield;return p;}'
        for target, expected in (('&point','3\n'), ('&pair.b','7\n')):
            source = self.source(helpers, 'let point=Point{x:3};let h=runtime::spawn(->identity('+target+'''));
                match h.join(){Ok(p)=>{print(p.x);},Err(_)=>{print(99);}}drop(->point);drop(->pair);''')
            with self.subTest(target=target):
                self.assertEqual(self.run_source(source).stdout, expected)

    def test_mutable_join_keeps_root_reserved(self):
        source = self.source('async fn identity(p:&mut Point)->&mut Point{yield;return p;}',
            '''let h=runtime::spawn(->identity(&mut pair.b));match h.join(){
                Ok(p)=>{p.x=13;print(p.x);},Err(_)=>{print(99);}}print(pair.b.x);''')
        self.assertEqual(self.run_source(source).stdout,'13\n13\n')
        self.refused(source.replace('p.x=13;', 'pair.b.x=30;p.x=13;'),'emprunt|réserv|référenc')

    def test_awaited_mutable_relay(self):
        helpers = '''async fn leaf(p:&mut Point)->&mut Point{yield;return p;}
            async fn relay(p:&mut Point)->Int{let mut q=leaf(p).await;yield;q.x=17;return q.x;}'''
        source = self.source(helpers, '''let h=runtime::spawn(->relay(&mut pair.b));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}print(pair.b.x);''')
        self.assertEqual(self.run_source(source).stdout,'17\n17\n')
        self.refused(source.replace('yield;q.x=17;', 'yield;p.x=30;q.x=17;'),'emprunt|réserv|référenc')


    def test_return_stored_shared_reference_and_drop_carrier(self):
        helpers = '''struct View{target:&Point}
            async fn get(v:->View)->&Point{yield;return v.target;}'''
        source = self.source(helpers, '''let v=View{target:&pair.b};let h=runtime::spawn(->get(->v));
            match h.join(){Ok(p)=>{print(p.x);},Err(_)=>{print(99);}}''')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(p.x);', 'pair.b.x=30;print(p.x);'), 'emprunt|réserv|référenc')

    def test_return_mutable_stored_reference(self):
        helpers = '''struct Writer{target:&mut Point}
            async fn get(w:&mut Writer)->&mut Point{yield;return &mut *w.target;}'''
        source = self.source(helpers, '''let mut w=Writer{target:&mut pair.b};let h=runtime::spawn(->get(&mut w));
            match h.join(){Ok(p)=>{p.x=19;print(p.x);},Err(_)=>{print(99);}}drop(->w);print(pair.b.x);''')
        self.assertEqual(self.run_source(source).stdout,'19\n19\n')
        self.refused(source.replace('p.x=19;', 'pair.b.x=30;p.x=19;'), 'emprunt|réserv|référenc')

    def test_async_handle_await_uses_nominal_result(self):
        helpers = '''async fn leaf(p:&mut Point)->&mut Point{yield;return p;}
            async fn work(p:&mut Point)->Int{let child=runtime::spawn(->leaf(p));let result=child.await;
                return match result{Ok(q)=>{q.x=23;q.x},Err(_)=>{0}};}'''
        source = self.source(helpers, '''let h=runtime::spawn(->work(&mut pair.b));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}print(pair.b.x);''')
        self.assertEqual(self.run_source(source).stdout,'23\n23\n')

    def test_conditional_whole_and_interior_results(self):
        helpers = 'async fn choose(f:Bool,a:&Point,b:&Point)->&Point{yield;return if f{a}else{b};}'
        for flag, expected in (('true','3\n'), ('false','7\n')):
            source = self.source(helpers, 'let point=Point{x:3};let h=runtime::spawn(->choose('+flag+''',&point,&pair.b));
                match h.join(){Ok(p)=>{print(p.x);},Err(_)=>{print(99);}}''')
            with self.subTest(flag=flag):
                self.assertEqual(self.run_source(source).stdout, expected)


    def test_return_interior_projection(self):
        helpers = 'async fn get(p:&mut Pair)->&mut Point{yield;return &mut p.b;}'
        source = self.source(helpers, '''let h=runtime::spawn(->get(&mut pair));
            match h.join(){Ok(p)=>{p.x=29;print(p.x);},Err(_)=>{print(99);}}print(pair.b.x);''')
        self.assertEqual(self.run_source(source).stdout, '29\n29\n')
        self.refused(source.replace('p.x=29;', 'pair.b.x=30;p.x=29;'), 'emprunt|réserv|référenc')

    def test_local_structure_cannot_be_returned_by_borrow(self):
        for body in ('let p=Point{x:3};return &p;', 'let p=Pair{};return &p.b;'):
            source = self.source('async fn bad()->&Point{'+body+'}', 'drop(->pair);let task=bad();drop(->task);')
            self.refused(source, 'retour|durable|local|provenance')


    def test_factory_and_select_keep_nominal_reference(self):
        helpers = '''async fn leaf(p:&Point)->&Point{yield;return p;}
            fn make(p:&Point)-><-leaf{return <-leaf(p);}
            async fn work(a:&Point,b:&Point)->Int{let mut s=runtime::select(->make(a),->leaf(b));
                let q=s.await;let n=q.x;drop(->s);return n;}'''
        source = self.source(helpers, '''let point=Point{x:3};let h=runtime::spawn(->work(&point,&pair.b));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}''')
        self.assertEqual(self.run_source(source).stdout, '3\n')


    def test_public_handle_contract_keeps_nominal_type(self):
        helpers = '''async fn leaf(p:&Point)->&Point{yield;return p;}
            fn finish(h:->runtime::Handle<&Point>)->Int{
                return match h.join(){Ok(p)=>{p.x},Err(_)=>{0}};}'''
        source = self.source(helpers, '''let h:runtime::Handle<&Point>=runtime::spawn(->leaf(&pair.b));
            let n=finish(->h);print(n);pair.b.x=31;print(pair.b.x);''')
        self.assertEqual(self.run_source(source).stdout, '7\n31\n')
        self.refused(source.replace('Handle<&Point>=', 'Handle<&mut Point>='), 'annotation|type|attendu')


if __name__ == '__main__':
    unittest.main()
