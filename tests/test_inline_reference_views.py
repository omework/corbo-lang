"""ST7/ST10-ST18: reference fields projected through a contained structure."""
import unittest
import test_select_source as source_tests

SHARED='struct Link{data:&Int,tag:Int}struct Pair{left:Link,right:Link}'
INIT='''let mut memory=pool<Int>(2);let mut a=memory.new(7);let mut b=memory.new(9);
    let mut s=Pair{left:Link{data:&a},right:Link{data:&b}};'''


class InlineReferenceViewTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused

    def program(self, body, helpers=''):
        return SHARED+helpers+'fn main(){'+INIT+body+'}'

    def test_shared_view_and_copy_keep_target_without_root(self):
        source=self.program('let v=&s.left;let c=copy(v);drop(->s);print(c);drop(->c);a=11;print(a);')
        self.assertEqual(self.run_source(source).stdout,'Link(7, 0)\n11\n')
        self.refused(source.replace('print(c);','drop(->a);print(c);'),'emprunt|réserv|référenc')

    def test_shared_field_return_detaches_from_view_and_root(self):
        helpers='''fn first(p:&Pair)->&Link{return &p.left;}
            fn target(v:&Link)->&Int{return v.data;}
            fn relay(p:&Pair)->&Int{let v=first(p);return target(v);}'''
        source=self.program('let n=relay(&s);drop(->s);print(*n);',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(*n);','drop(->a);print(*n);'),'emprunt|réserv|référenc')

    def test_returned_copy_keeps_shared_target_after_root_drop(self):
        helpers='''fn duplicate(s:&Pair)-><-Link{
            let v=&s.left;let c=copy(v);return <-c;}'''
        source=self.program('let c=duplicate(&s);drop(->s);print(c);',helpers)
        self.assertEqual(self.run_source(source).stdout,'Link(7, 0)\n')
        self.refused(source.replace('print(c);','drop(->a);print(c);'),'emprunt|réserv|référenc')

    def test_reference_replacement_updates_root(self):
        source=self.program('''let mut v=&mut s.left;v.data=&b;print(*v.data);
            print(*s.left.data);drop(->a);print(*s.left.data);''')
        self.assertEqual(self.run_source(source).stdout,'9\n9\n9\n')
        self.refused(source.replace('drop(->a);','drop(->b);'),'emprunt|réserv|référenc')

    def test_reference_replacement_through_contract(self):
        helpers='''fn change(v:&mut Link,n:&Int){v.data=&*n;}
            fn update(s:&mut Pair,n:&Int){let mut v=&mut s.left;change(v,n);}'''
        source=self.program('update(&mut s,&b);drop(->a);print(*s.left.data);',helpers)
        self.assertEqual(self.run_source(source).stdout,'9\n')
        self.refused(source.replace('drop(->a);','drop(->b);'),'emprunt|réserv|référenc')

    def test_returned_mutable_view_updates_root(self):
        helpers='''fn first(s:&mut Pair)->&mut Link{return &mut s.left;}
            fn relay(s:&mut Pair)->&mut Link{return first(s);}'''
        source=self.program('let mut v=relay(&mut s);v.data=&b;print(*v.data);drop(->a);print(*s.left.data);',helpers)
        self.assertEqual(self.run_source(source).stdout,'9\n9\n')
        self.refused(source.replace('v.data=&b;','s.left.data=&b;'),'emprunt|réserv|référenc')

    def test_replacement_result_keeps_new_target_after_root_drop(self):
        helpers='''fn change(v:&mut Link,n:&Int)->&Int{v.data=&*n;return v.data;}
            fn update(s:&mut Pair,n:&Int)->&Int{
                let mut v=&mut s.left;return change(v,n);}'''
        source=self.program('let n=update(&mut s,&b);drop(->s);drop(->a);print(*n);',helpers)
        self.assertEqual(self.run_source(source).stdout,'9\n')
        self.refused(source.replace('print(*n);','drop(->b);print(*n);'),'emprunt|réserv|référenc')

    def test_mutable_field_reborrow_keeps_capacity_and_target(self):
        types='struct Writer{data:&mut Int,tag:Int}struct Pair{left:Writer,right:Writer}'
        helpers='fn take(w:&mut Writer)->&mut Int{return &mut *w.data;}'
        source=types+helpers+'''fn main(){let mut p=pool<Int>(2);
            let mut a=p.new(7);let mut b=p.new(9);
            let mut s=Pair{left:Writer{data:&mut a},right:Writer{data:&mut b}};
            let mut v=&mut s.left;let mut n=take(v);s.right.tag=3;
            n.set(11);print(*n);print(*v.data);drop(->s);print(a);}'''
        self.assertEqual(self.run_source(source).stdout,'11\n11\n11\n')
        for operation in ('print(*v.data);','drop(->s);','a=20;'):
            with self.subTest(operation=operation):
                self.refused(source.replace('n.set(11);',operation+'n.set(11);'),'emprunt|réserv|référenc')
        self.refused(source.replace('let mut n=take(v);','let c=copy(v);print(c);let mut n=take(v);'),
                     'copiable|mutable')

    def test_mutable_field_replacement_releases_previous_target(self):
        source='''struct Writer{data:&mut Int}struct Outer{writer:Writer}
            fn main(){let mut p=pool<Int>(2);let mut a=p.new(7);let mut b=p.new(9);
                let mut s=Outer{writer:Writer{data:&mut a}};
                let mut v=&mut s.writer;v.data=&mut b;print(*v.data);
                drop(->a);print(*s.writer.data);drop(->s);b=11;print(b);}'''
        self.assertEqual(self.run_source(source).stdout,'9\n9\n11\n')
        self.refused(source.replace('drop(->a);','drop(->b);'),'emprunt|réserv|référenc')


if __name__=='__main__':
    unittest.main()
