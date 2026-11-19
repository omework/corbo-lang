"""Source ST7 views: reserve the subtree and retain its root through calls."""
from pathlib import Path
import unittest
import test_select_source as source_tests

ROOT=Path(__file__).resolve().parents[1]
TYPES='struct Point{x:Int,y:Int}struct Segment{debut:Point,fin:Point}'
INIT='let mut s=Segment{debut:Point{x:1,y:2},fin:Point{x:3,y:4}};'


class InlineStructureBorrowTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused

    def program(self, body, helpers=''):
        return TYPES+helpers+'fn main(){'+INIT+body+'}'

    def test_recorded_call_and_disjoint_sibling(self):
        source=(ROOT/'validation/open-inline-structure-borrow.crb').read_text()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'3\n20\n')
        self.assertEqual(run.stderr.count('destroy '),1)

    def test_subtree_reserved_until_last_use(self):
        source=self.program('let mut v=&mut s.debut;BEFORE print(v.x);AFTER')
        self.assertEqual(self.run_source(source.replace('BEFORE','print(s.fin.x);')
                                        .replace('AFTER','s.debut.x=8;print(s.debut.x);')).stdout,'3\n1\n8\n')
        for operation in ('print(s.debut.x);','s.debut.y=9;','print(s);','drop(->s);',
                          'let x=&mut s.debut.x;print(*x);'):
            with self.subTest(operation=operation):
                self.refused(source.replace('BEFORE',operation).replace('AFTER',''),
                             'emprunt|réserv|référenc')

    def test_shared_view_and_two_disjoint_mutable_arguments(self):
        source=self.program('let v=&s.debut;s.fin.x=9;print(v);print(s.debut.x);')
        self.assertEqual(self.run_source(source).stdout,'Point(1, 2)\n1\n')
        self.refused(source.replace('s.fin.x=9;','s.debut.x=9;'),'emprunt|réserv|référenc')
        source=self.program('''let mut a=&mut s.debut;let mut b=&mut s.fin;
            edit(a,b);print(a.x);print(b.x);''',
            'fn edit(a:&mut Point,b:&mut Point){a.x=7;b.x=9;}')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')

    def test_returned_substructure_through_relay(self):
        helpers='''fn first(s:&mut Segment)->&mut Point{return &mut s.debut;}
            fn relay(s:&mut Segment)->&mut Point{return first(s);}'''
        source=self.program('let mut v=relay(&mut s);s.fin.x=9;v.x=7;print(v.x);print(s.fin.x);',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('s.fin.x=9;','s.debut.y=9;'),'emprunt|réserv|référenc')
        self.refused(source.replace('print(v.x);','drop(->s);print(v.x);'),'emprunt|réserv|référenc')

    def test_leaf_reborrow_and_return(self):
        helpers='fn first(p:&mut Point)->&mut Int{return &mut p.x;}'
        source=self.program('''let mut v=&mut s.debut;let mut x=first(v);
            v.y=9;x.set(7);print(*x);print(v.y);''',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('v.y=9;','v.x=9;'),'emprunt|réserv|référenc')

    def test_child_scope_cannot_lend_its_root_to_parent(self):
        valid=self.program('let v={let inside=&s.debut;inside};print(v.x);')
        self.assertEqual(self.run_source(valid).stdout,'1\n')
        invalid=TYPES+'''fn main(){let v={let s=Segment{debut:Point{x:1}};
            let inside=&s.debut;inside};print(v.x);}'''
        self.refused(invalid,'durable|survi|libéré')

    def test_branch_and_loop_results_keep_the_substructure_address(self):
        for expression in ('if true {&mut s.debut} else {&mut s.fin}',
                           'loop {break &mut s.debut;}'):
            with self.subTest(expression=expression):
                source=self.program('let mut v='+expression+';address(v);v.x=7;'
                                    'address(v);print(v.x);')
                lines=self.run_source(source).stdout.splitlines()
                self.assertEqual(lines[0],lines[1])
                self.assertEqual(lines[2],'7')


if __name__=='__main__':
    unittest.main()
