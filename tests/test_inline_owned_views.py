"""ST7/ST15-ST18: an interior view borrows, but never owns, contained handles."""
import unittest
import test_select_source as harness


TYPES = 'struct Inner{value:A<Int>,tag:Int}struct Outer{inner:Inner,tag:Int}'
SETUP = '''let mut p=pool<Int>(1);let n=p.new(7);
    let mut s=Outer{inner:Inner{value:<-n}};'''


class InlineOwnedViewTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def program(self, body, helpers=''):
        return TYPES + helpers + 'fn main(){' + SETUP + body + '}'

    def test_shared_read_preserves_cleanup_and_slot_reuse(self):
        source = self.program('''let v=&s.inner;print(read(v));drop(->s);
            let m=p.new(9);print(*m);''', 'fn read(v:&Inner)->Int{return *v.value;}')
        run = self.run_source(source)
        self.assertEqual(run.stdout, '7\n9\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        self.assertLess(run.stderr.index('destroy n=7'), run.stderr.index('destroy s=Outer'))
        self.refused(source.replace('print(read(v));', 'drop(->s);print(read(v));'), 'emprunt|réserv|référenc')
        self.refused(source.replace('print(read(v));', 'let c=copy(v);print(read(&c));'), 'copi|Copy|propriétaire')

    def test_mutable_child_and_disjoint_sibling(self):
        source = self.program('''let mut v=&mut s.inner;edit(v);s.tag=3;
            print(*s.inner.value);drop(->s);let m=p.new(9);print(*m);''',
            'fn edit(v:&mut Inner){let mut n=&mut *v.value;n.set(11);}')
        self.assertEqual(self.run_source(source).stdout, '11\n9\n')

    def test_returned_child_retains_root_until_last_use(self):
        helpers = '''fn take(v:&mut Inner)->&mut Int{return &mut *v.value;}
            fn relay(s:&mut Outer)->&mut Int{let mut v=&mut s.inner;return take(v);}'''
        source = self.program('''let mut child=relay(&mut s);s.tag=3;child.set(11);
            print(*child);drop(->s);let m=p.new(9);print(*m);''', helpers)
        self.assertEqual(self.run_source(source).stdout, '11\n9\n')
        for operation in ('drop(->s);', 'print(*s.inner.value);'):
            self.refused(source.replace('child.set(11);', operation+'child.set(11);'), 'emprunt|réserv|référenc')

    def test_direct_replacement_updates_root_and_releases_old_slot(self):
        source = self.program('''let mut q=pool<Int>(1);let mut v=&mut s.inner;
            v.value=<-q.new(11);print(*v.value);let m=p.new(9);print(*m);
            print(*s.inner.value);drop(->s);let k=q.new(13);print(*k);''')
        run = self.run_source(source)
        self.assertEqual(run.stdout, '11\n9\n11\n13\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        self.assertEqual(run.stderr.count('destroy champ=11\n'), 1)
        self.refused(source.replace('v.value=<-q.new(11);', 'v.value=q.new(11);'), 'transfert explicite')

    def test_replacement_via_contract(self):
        helpers = '''fn change(v:&mut Inner,p:&mut Pool<Int>){v.value=<-p.new(11);}
            fn relay(s:&mut Outer,p:&mut Pool<Int>){let mut v=&mut s.inner;change(v,p);}'''
        source = self.program('''let mut q=pool<Int>(1);relay(&mut s,&mut q);
            let m=p.new(9);print(*m);print(*s.inner.value);
            drop(->s);let k=q.new(13);print(*k);''', helpers)
        self.assertEqual(self.run_source(source).stdout, '9\n11\n13\n')
        self.refused(source.replace('let mut q=pool<Int>(1);relay(&mut s,&mut q);',
            '{let mut q=pool<Int>(1);relay(&mut s,&mut q);}').replace(
            'let k=q.new(13);print(*k);', ''), 'source|pool|survi|durée')

    def test_replacement_on_returned_view_and_direct_argument(self):
        helpers = '''fn change(v:&mut Inner,p:&mut Pool<Int>){v.value=<-p.new(11);}
            fn view(s:&mut Outer)->&mut Inner{return &mut s.inner;}
            fn relay(s:&mut Outer,p:&mut Pool<Int>){CALL}'''
        for call in ('let mut v=view(s);change(v,p);', 'change(&mut s.inner,p);'):
            with self.subTest(call=call):
                source = self.program('''let mut q=pool<Int>(1);relay(&mut s,&mut q);
                    print(*s.inner.value);drop(->s);let k=q.new(13);print(*k);''',
                    helpers.replace('CALL', call))
                self.assertEqual(self.run_source(source).stdout, '11\n13\n')

    def test_borrowed_descendant_update_keeps_new_target(self):
        source = '''struct Leaf{data:&Int}struct Inner{leaf:A<Leaf>}struct Outer{inner:Inner}
            fn change(leaf:&mut Leaf,n:&Int){leaf.data=&*n;}
            fn relay(s:&mut Outer,n:&Int){let mut v=&mut s.inner;
                let mut leaf=&mut *v.leaf;change(leaf,n);}
            fn read(s:&Outer)->&Int{let v=&s.inner;let leaf=&*v.leaf;return leaf.data;}
            fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
                let mut leaves=pool<Leaf>(1);let leaf=leaves.new(data:&a);
                let mut s=Outer{inner:Inner{leaf:<-leaf}};
                relay(&mut s,&b);drop(->a);let result=read(&s);drop(->s);print(*result);}'''
        self.assertEqual(self.run_source(source).stdout, '9\n')
        self.refused(source.replace('print(*result);', 'drop(->b);print(*result);'), 'emprunt|réserv|référenc')


if __name__ == '__main__':
    unittest.main()
