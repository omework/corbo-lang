"""Direct struct payloads occupy vector cases, separately from A<T> handles."""
import unittest
from crust import compile_source, verify_program
import test_select_source as harness


BASE = '''struct Point{x:Int,y:Int}
fn main(){let mut p=pool<Vector<Point>>(1);let mut v=p.new();
v.push(->Point{x:7,y:9});let point=copy(v[0]);drop(->v);
print(point.x);print(point.y);}'''


class InlineStructVectorTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_payload_copy_survives_vector_and_pool(self):
        self.assertEqual(self.run_source(BASE).stdout, '7\n9\n')
        source = '''struct Point{x:Int,y:Int}fn main(){let point={
            let mut p=pool<Vector<Point>>(1);let mut v=p.new();v.push(->Point{x:7,y:9});
            let result=copy(v[0]);<-result};print(point.x);print(point.y);}'''
        self.assertEqual(self.run_source(source).stdout, '7\n9\n')
        code = compile_source(BASE)
        self.assertIn('sizeof(int) + sizeof(int), _Alignof(int)', code)
        self.assertRegex(code, r'vector_push\(\w+, \w+->fields\)')

    def test_nested_structs_and_independent_explicit_copy(self):
        source = '''struct Point{x:Int,y:Int}struct Pair{left:Point,right:Point}
            fn main(){let mut p=pool<Vector<Pair>>(1);let mut v=p.new();
            let original=Pair{left:Point{x:1,y:2},right:Point{x:3,y:4}};
            v.push(->copy(original));print(original.right.y);
            let result=copy(v[0]);drop(->v);print(result.left.x);print(result.right.y);}'''
        self.assertEqual(self.run_source(source).stdout, '4\n1\n4\n')

    def test_two_fronts_regions_growth_and_slot_reuse(self):
        body = '''struct Point{x:Int,y:Int}fn main(){
            let mut p=pool<Vector<Point>>(2);let mut a=p.new();let mut b=p.new();
            let mut i=0;while i<4{a.push(->Point{x:i,y:10});b.push(->Point{x:20,y:i});i=i+1;}
            let mut j=0;while j<4{let x=copy(a[j]);let y=copy(b[j]);print(x.x);print(y.y);j=j+1;}
            drop(->a);drop(->b);let mut c=p.new();c.push(->Point{x:99,y:0});
            let result=copy(c[0]);print(result.x);}'''
        region = body.replace('fn main(){', 'fn main(){#(directive, stack_region_max_size=1M){') + '}'
        for source in (body, region):
            self.assertEqual(self.run_source(source).stdout, '0\n0\n1\n1\n2\n2\n3\n3\n99\n')

    def test_copy_and_handle_types_are_explicit(self):
        self.refused(BASE.replace('copy(v[0])', 'v[0]'), 'copie.*explicite')
        self.refused(BASE.replace('->Point', 'Point'), 'transfert.*explicite')
        self.refused(BASE.replace('v.push(->Point{x:7,y:9});',
            'let mut points=pool<Point>(1);v.push(->points.new(x:7,y:9));'), 'valeur Point.*A<Point>')
        self.refused(BASE.replace('let point=copy(v[0]);drop(->v);',
            'drop(->v);let point=copy(v[0]);'), 'détruit|utilisable|libér|invalid')
        self.refused(BASE.replace('let mut v=', 'let v='), 'let mut|mutable')

    def test_shared_borrow_blocks_push_until_last_use(self):
        source = BASE.replace('v.push(->Point{x:7,y:9});',
            'let view=&v;v.push(->Point{x:7,y:9});print(view.len());')
        self.refused(source, 'emprunt|réserv')
        allowed = source.replace('let view=&v;v.push(->Point{x:7,y:9});print(view.len());',
            'let view=&v;print(view.len());v.push(->Point{x:7,y:9});')
        self.assertEqual(self.run_source(allowed).stdout, '0\n7\n9\n')

    def test_bounds_checked_in_native_code(self):
        for index in ('1', '-1'):
            source = BASE.replace('v[0]', 'v['+index+']')
            verify_program(source)
            self.run_c_oracle(compile_source(source), expected_error='indice de Vector hors limites')

    def test_function_contracts_return_independent_local_copy(self):
        source = '''struct Point{x:Int}
            fn read(v:&Vector<Point>)-><-Point{let r=copy(v[0]);return <-r;}
            fn relay(v:&Vector<Point>)-><-Point{return <-read(v);}
            fn fill(v:&mut Vector<Point>){v.push(->Point{x:7});}
            fn main(){let mut p=pool<Vector<Point>>(1);let mut v=p.new();
            fill(&mut v);let r=relay(&v);drop(->v);print(r.x);}'''
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.refused(source.replace('fill(&mut v);let r=relay(&v);',
            'fill(&mut v);drop(->v);let r=relay(&v);').replace('drop(->v);print', 'print'),
            'détruit|utilisable|invalid|libér')

    def test_empty_struct_and_reuse(self):
        source = '''struct Empty{}fn main(){let mut p=pool<Vector<Empty>>(1);let mut v=p.new();
            v.push(->Empty{});v.push(->Empty{});let r=copy(v[1]);print(v.len());drop(->r);
            drop(->v);let mut w=p.new();w.push(->Empty{});print(w.len());}'''
        self.assertEqual(self.run_source(source).stdout, '2\n1\n')


if __name__ == '__main__':
    unittest.main()
