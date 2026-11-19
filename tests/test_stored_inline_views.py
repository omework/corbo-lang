"""Stored interior references preserve the root, offset and borrow contract."""
import unittest
import test_select_source as harness

TYPES = '''struct Point{x:Int,y:Int}struct Pair{a:Point,b:Point}
    struct View{tag:Int,target:&Point,tail:Int}'''
INIT = 'let mut pair=Pair{a:Point{x:1},b:Point{x:7}};'


class StoredInlineViewTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def program(self, body, helpers=''):
        return TYPES+helpers+'fn main(){'+INIT+body+'}'

    def test_shared_copy_detaches_from_carrier_but_keeps_root(self):
        source = self.program('''let v=View{tag:3,target:&pair.b,tail:5};
            let c=copy(v);drop(->v);let p=c.target;print(c.tag);print(c.tail);
            drop(->c);print(p.x);''')
        self.assertEqual(self.run_source(source).stdout, '3\n5\n7\n')
        self.refused(source.replace('print(p.x);','drop(->pair);print(p.x);'),'emprunt|réserv|référenc')

    def test_returned_carrier_and_reference_survive_producer(self):
        helpers = '''fn make(p:&Pair)-><-View{return <-View{target:&p.b};}
            fn extract(v:&View)->&Point{return v.target;}
            fn relay(p:&Pair)->&Point{let v=make(p);return extract(&v);}'''
        source = self.program('let p=relay(&pair);print(p.x);', helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(p.x);','drop(->pair);print(p.x);'),'emprunt|réserv|référenc')

    def test_mutable_stored_view_reborrow_through_function(self):
        helpers = '''struct Writer{target:&mut Point}
            fn get(w:&mut Writer)->&mut Point{return &mut *w.target;}'''
        source = self.program('''let mut w=Writer{target:&mut pair.b};
            let mut p=get(&mut w);p.x=11;print(p.x);drop(->w);print(pair.b.x);''',helpers)
        self.assertEqual(self.run_source(source).stdout,'11\n11\n')
        for operation in ('drop(->w);','pair.b.x=20;'):
            self.refused(source.replace('p.x=11;',operation+'p.x=11;'),'emprunt|réserv|référenc')

    def test_replace_between_whole_and_interior_references(self):
        source = self.program('''let point=Point{x:3};let mut v=View{target:&point};
            v.target=&pair.b;let p=v.target;print(p.x);
            v.target=&point;let q=v.target;drop(->pair);print(q.x);''')
        self.assertEqual(self.run_source(source).stdout,'7\n3\n')

    def test_store_through_interior_carrier(self):
        source = self.program('''let point=Point{x:3};let mut e=Envelope{view:View{target:&point}};
            let mut v=&mut e.view;v.target=&pair.b;let p=v.target;
            drop(->e);drop(->point);print(p.x);''','struct Envelope{view:View}')
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_enum_match_loads_stored_descriptor(self):
        helpers = 'enum Choice{Here{point:&Point},Empty}'
        for subject in ('&c', '(->c)'):
            with self.subTest(subject=subject):
                source = self.program('''let mut choices=pool<Choice>(1);let c=new(choices) Choice.Here{point:&pair.b};
                    match SUBJECT{Choice.Here{point:p}=>{let x=p.x;print(x);},Choice.Empty=>{}}'''.replace(
                    'SUBJECT',subject), helpers)
                self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_pool_copy_keeps_descriptor_after_slot_reuse(self):
        source = self.program('''let mut p=pool<View>(2);let v=p.new(target:&pair.b);
            let c=p.copy(v);drop(->v);let reused=p.new(target:&pair.a);
            let r=c.target;drop(->c);let other=reused.target;print(other.x);print(r.x);''')
        self.assertEqual(self.run_source(source).stdout,'1\n7\n')

    def test_async_capture_of_stored_view_can_be_discarded_inactive(self):
        source = self.program('''let v=View{target:&pair.b};let task=read(&v);drop(->task);''',
            'async fn read(v:&View)->Int{yield;let p=v.target;return p.x;}')
        self.assertEqual(self.run_source(source).stdout, '')

    def test_stored_view_cannot_make_its_root_self_referential(self):
        source = '''struct Point{x:Int}struct Root{point:Point,view:&Point}
            fn main(){let external=Point{x:1};let mut r=Root{point:Point{x:7},view:&external};
                r.view=&r.point;let p=r.view;print(p.x);}'''
        self.refused(source,'cycle entre allocations empruntées')


if __name__ == '__main__':
    unittest.main()
