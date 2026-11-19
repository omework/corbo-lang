"""ST17/ST18: copying the contents of an inline view creates fresh storage."""
import unittest
import test_select_source as source_tests

TYPES='struct Point{x:Int,y:Int}struct Segment{debut:Point,fin:Point}'
INIT='let mut s=Segment{debut:Point{x:1,y:2},fin:Point{x:3,y:4}};'


class InlineViewCopyTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused

    def test_local_copy_is_independent_and_does_not_retain_root(self):
        source=TYPES+'fn main(){'+INIT+'''
            let v=&s.debut;address(v);let mut copied=copy(v);address(copied);
            s.debut.x=9;print(s.debut.x);drop(->s);
            copied.x=8;print(copied);drop(->copied);}'''
        run=self.run_source(source)
        original,copied,changed,value=run.stdout.splitlines()
        self.assertNotEqual(original,copied)
        self.assertEqual((changed,value),('9','Point(8, 2)'))
        self.assertEqual(run.stderr.count('destroy '),2)

    def test_explicit_pool_copy_and_reuse(self):
        source=TYPES+'''fn main(){
            let mut segments=pool<Segment>(1);let s=segments.new(debut.x:7);
            let v=&s.debut;let mut points=pool<Point>(1);
            let copied=points.copy(v);address(copied);drop(->s);print(copied);
            drop(->copied);let reused=points.new(x:9);address(reused);print(reused);}'''
        run=self.run_source(source)
        first,value,second,reused=run.stdout.splitlines()
        self.assertEqual(first,second)
        self.assertEqual((value,reused),('Point(7, 0)','Point(9, 0)'))
        self.refused(source.replace('points.copy(v)','copy(v)'), 'stockage local incompatible.*pool')
        self.refused(source.replace('points.copy(v)','segments.copy(v)'), 'type|Pool')

    def test_copy_through_parameter_and_returned_view(self):
        helpers='''fn view(s:&Segment)->&Point{return &s.debut;}
            fn relay(s:&Segment)->&Point{return view(s);}
            fn duplicate(p:&Point)-><-Point{let c=copy(p);return <-c;}
            fn from_segment(s:&Segment)-><-Point{
                let v=relay(s);let c=duplicate(v);return <-c;}'''
        source=TYPES+helpers+'fn main(){'+INIT+'''
            let c=from_segment(&s);drop(->s);print(c);}'''
        self.assertEqual(self.run_source(source).stdout,'Point(1, 2)\n')

    def test_pool_copy_return_keeps_destination_pool(self):
        source=TYPES+'''fn duplicate(points:&mut Pool<Point>,p:&Point)-><-A<Point>{
            let c=points.copy(p);return <-c;}
            fn main(){let mut segments=pool<Segment>(1);let s=segments.new(debut.x:7);
                let mut points=pool<Point>(1);let v=&s.debut;
                let c=duplicate(&mut points,v);drop(->s);print(c);}'''
        self.assertEqual(self.run_source(source).stdout,'Point(7, 0)\n')
        invalid=TYPES+'''fn main(){let c={let mut points=pool<Point>(1);
            let s=Segment{debut:Point{x:7}};let v=&s.debut;
            let c=points.copy(v);<-c};print(c);}'''
        self.refused(invalid,'source|survi|durable')

    def test_copy_escapes_child_and_loop_without_retaining_child(self):
        for expression in ('{BODY <-copy(v)}', 'loop {BODY break <-copy(v);}'):
            with self.subTest(expression=expression):
                body=INIT+'let v=&s.debut;'
                source=TYPES+'fn main(){let c='+expression.replace('BODY',body)+';print(c);}'
                run=self.run_source(source)
                self.assertEqual(run.stdout,'Point(1, 2)\n')
                self.assertEqual(run.stderr.count('destroy '),2)

    def test_copy_respects_active_reborrow(self):
        body=INIT+'''let mut v=&mut s.debut;let mut x=&mut v.x;
            BEFORE x.set(7);print(*x);AFTER'''
        source=TYPES+'fn main(){'+body+'}'
        self.refused(source.replace('BEFORE','let c=copy(v);print(c);').replace('AFTER',''),
                     'emprunt|réserv')
        allowed=source.replace('BEFORE','').replace('AFTER','let c=copy(v);print(c);')
        self.assertEqual(self.run_source(allowed).stdout,'7\nPoint(7, 2)\n')


if __name__=='__main__':
    unittest.main()
