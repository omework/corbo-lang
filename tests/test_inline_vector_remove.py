"""Explicit extraction of inline structures preserves sequence and local lifetime."""
import unittest
from crust import compile_source, verify_program
import test_select_source as harness

PREFIX = '''struct Point{x:Int,y:Int}fn main(){
let mut p=pool<Vector<Point>>(1);let mut v=p.new();
v.push(->Point{x:7,y:70});v.push(->Point{x:9,y:90});'''


class InlineVectorRemoveTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_remove_preserves_sequence_and_independent_result(self):
        source = PREFIX + '''let first=<-v.remove(0);let last=copy(v[0]);print(v.len());
            print(first.x);print(last.x);drop(->v);print(first.y);}'''
        self.assertEqual(self.run_source(source).stdout, '1\n7\n9\n70\n')
        self.refused(source.replace('<-v.remove', 'v.remove'), 'transfert.*explicite')
        self.refused(source.replace('let mut v=', 'let v='), 'let mut|mutable')

    def test_function_return_and_relay_survive_vector(self):
        helper = '''struct Point{x:Int,y:Int}
            fn take(v:&mut Vector<Point>)-><-Point{return <-v.remove(0);}
            fn relay(v:&mut Vector<Point>)-><-Point{let r=take(v);return <-r;}'''
        source = helper + PREFIX[PREFIX.index('fn main()'):] + '''let first=relay(&mut v);
            let second=take(&mut v);print(v.len());drop(->v);print(first.x);print(second.x);}'''
        self.assertEqual(self.run_source(source).stdout, '0\n7\n9\n')
        self.refused(source.replace('let first=relay(&mut v);',
            'let view=&v;let first=relay(&mut v);print(view.len());'), 'emprunt|réserv')
        self.refused(source.replace('-><-Point', '-><-A<Point>'), 'stockage|allocation|A<Point>|local')

    def test_builtin_feature_resolves_struct_result(self):
        helper = '''struct Point{x:Int,y:Int}
            type feature Retirer{fn remove(&mut self,index:Int)-><-Point;}
            fn take(v:&mut Retirer)-><-Point{return <-v.remove(0);}'''
        source=helper+PREFIX[PREFIX.index('fn main()'):]+'let r=take(&mut v);drop(->v);print(r.x);}'
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.refused(source.replace('fn remove(&mut self,index:Int)-><-Point;',
                                    'fn remove(&mut self,index:Int)->Int;'), 'feature|signature')

    def test_parent_conditional_and_loop_receivers(self):
        for expression, expected in (
            ('{let r=<-v.remove(0);<-r}', '7\n1\n'),
            ('if true{let r=<-v.remove(0);<-r}else{let r=<-v.remove(1);<-r}', '7\n1\n'),
            ('if false{let r=<-v.remove(0);<-r}else{let r=<-v.remove(1);<-r}', '9\n1\n'),
            ('loop{break <-v.remove(0);}', '7\n1\n'),
        ):
            source = PREFIX + 'let r='+expression+';print(r.x);print(v.len());}'
            self.assertEqual(self.run_source(source).stdout, expected)
        source = '''struct Point{x:Int}fn main(){let r={let mut p=pool<Vector<Point>>(1);
            let mut v=p.new();v.push(->Point{x:7});let result=<-v.remove(0);<-result};print(r.x);}'''
        self.assertEqual(self.run_source(source).stdout, '7\n')

    def test_drop_result_and_reuse_in_loop(self):
        source = '''struct Point{x:Int}fn main(){let mut p=pool<Vector<Point>>(1);
            let mut i=0;while i<4{let mut v=p.new();v.push(->Point{x:i});
            drop(->v.remove(0));print(v.len());drop(->v);i=i+1;}}'''
        self.assertEqual(self.run_source(source).stdout, '0\n'*4)

    def test_borrow_reservations_and_evaluated_index(self):
        source = PREFIX + '''let last=v.len()-1;let r=<-v.remove(last);print(r.x);print(v.len());}'''
        self.assertEqual(self.run_source(source).stdout, '9\n1\n')
        # ME1/B4a reserve the mutable receiver before later arguments.
        self.refused(source.replace('v.remove(last)', 'v.remove(v.len()-1)'), 'emprunt|réserv')
        self.refused(source.replace('let r=', 'let view=&v;let r=').replace('print(r.x);',
            'print(view.len());print(r.x);'), 'emprunt|réserv')
        allowed = source.replace('let r=', 'let view=&v;print(view.len());let r=')
        self.assertEqual(self.run_source(allowed).stdout, '2\n9\n1\n')
        self.refused(source.replace('let r=', 'drop(->v);let r='), 'détruit|utilisable|invalid|libér')

    def test_nested_empty_and_two_growth_fronts(self):
        nested = '''struct Point{x:Int}struct Pair{a:Point,b:Point}fn main(){
            let mut p=pool<Vector<Pair>>(2);let mut a=p.new();let mut b=p.new();
            a.push(->Pair{a:Point{x:1},b:Point{x:2}});
            b.push(->Pair{a:Point{x:3},b:Point{x:4}});b.push(->Pair{a:Point{x:5},b:Point{x:6}});
            let first=<-b.remove(0);let second=<-b.remove(0);drop(->a);drop(->b);
            print(first.a.x);print(second.b.x);}'''
        self.assertEqual(self.run_source(nested).stdout, '3\n6\n')
        empty = '''struct Empty{}fn main(){let mut p=pool<Vector<Empty>>(1);let mut v=p.new();
            v.push(->Empty{});let e=<-v.remove(0);print(v.len());drop(->v);drop(->e);}'''
        self.assertEqual(self.run_source(empty).stdout, '0\n')

    def test_invalid_index_stops_before_read(self):
        for index in ('-1', '2'):
            source=PREFIX+'let r=<-v.remove('+index+');print(r.x);}'
            verify_program(source)
            self.run_c_oracle(compile_source(source), expected_error='indice de Vector hors limites')


if __name__ == '__main__':
    unittest.main()
