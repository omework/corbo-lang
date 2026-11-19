"""Typed stored references retain their interior descriptor across suspension."""
import unittest
import test_select_source as harness

TYPES = 'struct Point{x:Int}struct Pair{a:Point,b:Point}struct View{target:&Point}'
INIT = 'let mut pair=Pair{a:Point{x:1},b:Point{x:7}};'
JOIN = 'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}'


class AsyncStoredViewTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def source(self, helpers, body):
        return TYPES+helpers+'fn main(){'+INIT+body+'}'

    def test_shared_stored_reference_after_suspension(self):
        source = self.source('async fn read(v:&View)->Int{yield;let p=v.target;return p.x;}',
            'let v=View{target:&pair.b};let task=read(&v);let h=runtime::spawn(->task);'+JOIN)
        self.assertEqual(self.run_source(source).stdout, '7\n')
        for operation in ('drop(->pair);', 'pair.b.x=30;', 'drop(->v);'):
            self.refused(source.replace('let h=',operation+'let h='),'emprunt|réserv|référenc')

    def test_mutable_stored_reference_and_child_task(self):
        helpers = '''struct Writer{target:&mut Point}
            async fn edit(p:&mut Point)->Int{yield;p.x=11;return p.x;}
            async fn work(w:&mut Writer)->Int{let mut p=&mut *w.target;yield;return edit(p).await;}'''
        source = self.source(helpers,'let mut w=Writer{target:&mut pair.b};let task=work(&mut w);'
            'let h=runtime::spawn(->task);'+JOIN+'drop(->w);print(pair.b.x);')
        self.assertEqual(self.run_source(source).stdout,'11\n11\n')
        self.refused(source.replace('let h=','pair.b.x=30;let h='),'emprunt|réserv|référenc')

    def test_shared_chain_and_copy_of_carrier(self):
        helpers = '''struct Link{view:&View}
            async fn read(link:&Link)->Int{yield;let v=link.view;let p=v.target;yield;return p.x;}'''
        source = self.source(helpers,'''let v=View{target:&pair.b};let copy=copy(v);drop(->v);
            let link=Link{view:&copy};let h=runtime::spawn(->read(&link));'''+JOIN)
        self.assertEqual(self.run_source(source).stdout, '7\n')

    def test_typed_reference_through_sync_bridge(self):
        helpers = '''fn get(v:&View)->&Point{return v.target;}
            async fn read(v:&View)->Int{yield;let p=get(v);yield;return p.x;}'''
        source = self.source(helpers, 'let v=View{target:&pair.b};let h=runtime::spawn(->read(&v));'+JOIN)
        self.assertEqual(self.run_source(source).stdout, '7\n')

    def test_mutable_field_through_sync_bridge(self):
        helpers = '''struct Writer{target:&mut Point}
            fn get(w:&mut Writer)->&mut Point{return &mut *w.target;}
            async fn work(w:&mut Writer)->Int{let mut p=get(w);yield;p.x=13;return p.x;}'''
        source = self.source(helpers, 'let mut w=Writer{target:&mut pair.b};let h=runtime::spawn(->work(&mut w));'
            +JOIN+'drop(->w);print(pair.b.x);')
        self.assertEqual(self.run_source(source).stdout,'13\n13\n')

    def test_replacement_direct_and_through_contract(self):
        for action in ('v.target=&*p;', 'replace(v,p);'):
            helpers = '''fn replace(v:&mut View,p:&Point){v.target=&*p;}
                async fn work(v:&mut View,p:&Point)->Int{ACTION yield;let q=v.target;return q.x;}'''.replace('ACTION',action)
            source = self.source(helpers, '''let old=Point{x:3};let mut v=View{target:&old};
                let h=runtime::spawn(->work(&mut v,&pair.b));'''+JOIN+
                'let q=v.target;print(q.x);drop(->old);')
            with self.subTest(action=action):
                self.assertEqual(self.run_source(source).stdout, '7\n7\n')
                self.refused(source.replace('print(q.x);', 'drop(->pair);print(q.x);'), 'emprunt|réserv|référenc')
                self.refused(source.replace('print(q.x);drop(->old);', 'drop(->old);print(q.x);'), 'emprunt|réserv|référenc')

    def test_owned_capture_returns_carrier_with_same_interior_target(self):
        helpers = 'async fn relay(v:->View)-><-View{yield;return <-v;}'
        source = self.source(helpers, '''let v=View{target:&pair.b};let h=runtime::spawn(->relay(->v));
            match h.join(){Ok(out)=>{let p=out.target;drop(->out);print(p.x);},Err(_)=>{print(99);}}''')
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.refused(source.replace('print(p.x);', 'pair.b.x=30;print(p.x);'), 'emprunt|réserv|référenc')

    def test_construct_and_copy_carrier_inside_task(self):
        helpers = '''async fn work(p:&Point)->Int{let v=View{target:p};let c=copy(v);
            drop(->v);yield;let q=c.target;drop(->c);return q.x;}'''
        source = self.source(helpers, 'let h=runtime::spawn(->work(&pair.b));'+JOIN)
        self.assertEqual(self.run_source(source).stdout, '7\n')


if __name__ == '__main__':
    unittest.main()
