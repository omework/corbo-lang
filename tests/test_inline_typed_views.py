"""ST7/ST10-ST18: typed references contained in an inline structure view."""
import unittest
import test_select_source as source_tests

TYPES='struct Point{x:Int}struct Link{point:&Point,tag:Int}struct Outer{link:Link,tag:Int}'
INIT='let mut a=Point{x:7};let mut s=Outer{link:Link{point:&a}};'


class InlineTypedViewTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused

    def program(self, body, helpers=''):
        return TYPES+helpers+'fn main(){'+INIT+body+'}'

    def test_shared_typed_reference_return_detaches_from_root(self):
        helpers='''fn first(s:&Outer)->&Link{return &s.link;}
            fn get(v:&Link)->&Point{return v.point;}
            fn relay(s:&Outer)->&Point{let v=first(s);return get(v);}'''
        source=self.program('let p=relay(&s);drop(->s);print(p.x);',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        for action in ('drop(->a);','a.x=11;'):
            self.refused(source.replace('print(p.x);',action+'print(p.x);'),'emprunt|réserv|référenc')

    def test_copy_preserves_typed_reference_without_root(self):
        helpers='fn duplicate(s:&Outer)-><-Link{let v=&s.link;let c=copy(v);return <-c;}'
        source=self.program('let c=duplicate(&s);drop(->s);let p=c.point;drop(->c);print(p.x);',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(p.x);','drop(->a);print(p.x);'),'emprunt|réserv|référenc')

    def test_typed_reference_replacement_through_call_and_root(self):
        helpers='''fn change(v:&mut Link,n:&Point){v.point=&*n;}
            fn update(s:&mut Outer,n:&Point){let mut v=&mut s.link;change(v,n);}'''
        source=self.program('let b=Point{x:9};update(&mut s,&b);drop(->a);let p=s.link.point;print(p.x);',helpers)
        self.assertEqual(self.run_source(source).stdout,'9\n')
        self.refused(source.replace('drop(->a);','drop(->b);'),'emprunt|réserv|référenc')

    def test_mutable_typed_reborrow_reserves_field_and_target(self):
        types='struct Point{x:Int}struct Writer{point:&mut Point,tag:Int}struct Outer{writer:Writer,tag:Int}'
        helpers='''fn take(w:&mut Writer)->&mut Point{return &mut *w.point;}
            fn relay(w:&mut Writer)->&mut Point{return take(w);}'''
        source=types+helpers+'''fn main(){let mut a=Point{x:7};
            let mut s=Outer{writer:Writer{point:&mut a}};
            let mut w=&mut s.writer;let mut p=relay(w);s.tag=3;
            p.x=11;print(p.x);drop(->s);print(a.x);}'''
        self.assertEqual(self.run_source(source).stdout,'11\n11\n')
        for action in ('drop(->s);','a.x=20;','let q=&*w.point;print(q.x);'):
            self.refused(source.replace('p.x=11;',action+'p.x=11;'),'emprunt|réserv|référenc')

    def test_transitive_target_can_outlive_intermediate_holders(self):
        source='''struct Leaf{data:&Int}struct Link{leaf:&Leaf}struct Outer{link:Link}
            fn extract(s:&Outer)->&Int{let v=&s.link;let leaf=v.leaf;return leaf.data;}
            fn main(){let mut memory=pool<Int>(1);let a=memory.new(7);
                let leaf=Leaf{data:&a};let s=Outer{link:Link{leaf:&leaf}};
                let n=extract(&s);drop(->s);drop(->leaf);print(*n);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(*n);','drop(->a);print(*n);'),'emprunt|réserv|référenc')

    def test_mutable_replacement_return_uses_new_target(self):
        source='''struct Point{x:Int}struct Writer{point:&mut Point}struct Outer{writer:Writer}
            fn change(w:&mut Writer,n:&mut Point)->&mut Point{
                w.point=&mut *n;return &mut *w.point;}
            fn update(s:&mut Outer,n:&mut Point)->&mut Point{
                let mut w=&mut s.writer;return change(w,n);}
            fn main(){let mut a=Point{x:7};let mut b=Point{x:9};
                let mut s=Outer{writer:Writer{point:&mut a}};
                let mut p=update(&mut s,&mut b);drop(->a);p.x=11;
                print(p.x);drop(->s);print(b.x);}'''
        self.assertEqual(self.run_source(source).stdout,'11\n11\n')
        self.refused(source.replace('drop(->a);','drop(->b);'),'emprunt|réserv|référenc')
        self.refused(source.replace('p.x=11;','drop(->s);p.x=11;'),'emprunt|réserv|référenc')


if __name__=='__main__':
    unittest.main()
