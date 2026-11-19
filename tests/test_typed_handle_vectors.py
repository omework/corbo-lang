"""Typed pool handles retain their payload type through vectors and extraction."""
from pathlib import Path
import unittest
import test_select_source as harness

BASE=Path(__file__).resolve().parents[1].joinpath('validation/open-vector-allocated-structure.crb').read_text()
EXTRACT='''let result=<-values.pop();
    match (->result){Some(point)=>{print(point.x);drop(->point);},None=>{print(0);}}'''
REMOVE='let point=<-values.remove(0);print(point.x);drop(->point);'


class TypedHandleVectorTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_local_pop_remove_and_remaining_cleanup(self):
        for operation, expected in ((EXTRACT,'7\n8\n'),(REMOVE,'7\n8\n'),('','8\n')):
            with self.subTest(operation=operation):
                run=self.run_source(BASE.replace(EXTRACT,operation))
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy p=Point\n'),1)
                self.assertEqual(run.stderr.count('destroy reused=Point\n'),1)

    def test_two_pools_remove_order_and_scope_transfer(self):
        source='''struct Point{x:Int}fn main(){let mut a=pool<Point>(1);let mut b=pool<Point>(1);
            let mut vectors=pool<Vector<A<Point>>>(1);
            let mut values={let mut local=vectors.new();let first=a.new(x:7);let second=b.new(x:9);
                local.push(->first);local.push(->second);<-local};
            let first=<-values.remove(0);print(first.x);drop(->first);
            let reused=a.new(x:8);print(reused.x);
            let last=<-values.remove(0);print(last.x);drop(->last);
            drop(->values);let other=b.new(x:10);print(other.x);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n8\n9\n10\n')

    def test_function_inputs_and_returned_handle(self):
        helpers='''fn insert(v:&mut Vector<A<Point>>,p:->A<Point>){v.push(->p);}
            fn count(v:&Vector<A<Point>>)->Int{return v.len();}
            fn take(v:&mut Vector<A<Point>>)-><-A<Point>{return <-v.remove(0);}
            fn relay(v:&mut Vector<A<Point>>)-><-A<Point>{return <-take(&mut *v);}'''
        source=helpers+BASE.replace('values.push(->p);','insert(&mut values,->p);print(count(&values));').replace(
            EXTRACT,'let point=relay(&mut values);print(point.x);drop(->point);')
        self.assertEqual(self.run_source(source).stdout,'1\n7\n8\n')
        self.refused(source.replace('insert(&mut values,->p);','insert(&mut values,->p);drop(->p);'),'consomm|utilisable|transfert')

    def test_string_and_numeric_vector_payloads(self):
        for typ, fill, read in (
            ('String','value.push_str("hello");','print(&item[..]);'),
            ('Vector<Int>','value.push(7);','print(item[0]);'),
            ('Vector<u8>','let byte:u8=7;value.push(byte);','print(item[0] as Int);'),
        ):
            source=f'''fn main(){{let mut p=pool<{typ}>(1);let mut vectors=pool<Vector<A<{typ}>>>(1);
                let mut values=vectors.new();let mut value=p.new();{fill}values.push(->value);
                let item=<-values.remove(0);{read}drop(->item);drop(->values);
                let reused=p.new();drop(->reused);}}'''
            with self.subTest(typ=typ):
                self.assertEqual(self.run_source(source).stdout,'hello\n' if typ=='String' else '7\n')

    def test_borrowed_typed_slot_and_replacement(self):
        body='''let slot=&values[0];
            let mut expected_pool=pool<Point>(1);let expected=expected_pool.new(x:7);
            if expected.vequals(slot){print(1);}
            let mut incoming_pool=pool<Point>(1);let incoming=incoming_pool.new(x:9);
            let mut exclusive=&mut values[0];*exclusive=<-incoming;'''
        source=BASE.replace(EXTRACT,body+REMOVE)
        run=self.run_source(source)
        self.assertEqual(run.stdout,'1\n9\n8\n')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),1)
        self.assertEqual(run.stderr.count('destroy incoming=Point\n'),1)
        invalid=source.replace('if expected.vequals(slot)', 'let removed=<-values.remove(0);drop(->removed);if expected.vequals(slot)')
        self.refused(invalid,'emprunt actif')

    def test_explicit_transfer_type_and_borrow_checks(self):
        self.refused(BASE.replace('push(->p)','push(p)'),'transfert|->')
        self.refused(BASE.replace('let p=points.new(x:7);','let mut ints=pool<Int>(1);let p=ints.new(7);'),'A<Point>|Pool<Point>')
        self.refused(BASE.replace('values.push(->p);','values.push(->p);print(p.x);'),'consomm|utilisable|transfert')
        self.refused(BASE.replace(EXTRACT,REMOVE.replace('<-values.remove(0)','values.remove(0)')),'transfert|<-')
        source='''fn consume(v:&A<Point>){drop(->v);}'''+BASE
        # Borrowed handles cannot become owned merely because their case is typed.
        self.refused(source,'transfert|emprunt|allocation|scope')

    def test_short_pool_and_noncopy_contents_are_not_promoted(self):
        self.refused('''struct Point{x:Int}fn main(){let mut vectors=pool<Vector<A<Point>>>(1);
            let mut values=vectors.new();{let mut local=pool<Point>(1);let p=local.new(x:7);
            values.push(->p);}drop(->values);}''','pool|survi|scope')
        self.refused(BASE.replace('let p=points.new(x:7);','let p=Point{x:7};'),'A<Point>|Pool<Point>')


if __name__=='__main__':unittest.main()
