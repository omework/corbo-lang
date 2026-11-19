"""V1/T6: a nominal return is local; a pool return explicitly spells A<T>."""
from pathlib import Path
import unittest
from crust import verify_program
import test_select_source as harness

ROOT = Path(__file__).resolve().parents[1]
POINT = 'struct Point{x:Int}'


class StrictStructureReturnTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_recorded_exchange_payload_return(self):
        source = (ROOT/'validation/open-plain-structure-return-from-handle-result.crb').read_text()
        self.refused(source, r'exigence de stockage incompatible avec le résultat déclaré \(T / A<T>\)')
        self.assertEqual(self.run_source(source.replace(')-><-Point{', ')-><-A<Point>{')).stdout,
                         '7\n9\n10\n11\n')

    def test_local_and_pool_factories(self):
        source = POINT + '''fn local()-><-Point{return <-Point{x:7};}
            fn allocated(p:&mut Pool<Point>)-><-A<Point>{return <-p.new(x:9);}
            fn main(){let mut p=pool<Point>(1);let a:Point=local();
            let b:A<Point>=allocated(&mut p);print(a.x);print(b.x);drop(->b);
            let again=p.new(x:11);print(again.x);}'''
        self.assertEqual(self.run_source(source).stdout, '7\n9\n11\n')
        self.refused(source.replace('allocated(p:&mut Pool<Point>)-><-A<Point>',
                                    'allocated(p:&mut Pool<Point>)-><-Point'), 'stockage local')
        self.refused(source.replace('local()-><-Point', 'local()-><-A<Point>'), 'stockage pool|allocation')

    def test_contract_relay_and_last_use(self):
        for typ, value in (('Point','Point{x:7}'), ('A<Point>','p.new(x:7)')):
            source = POINT + '''fn identity(v:->TYPE)-><-TYPE{return <-v;}
                fn relay(v:->TYPE)-><-TYPE{return <-identity(->v);}
                fn main(){let mut p=pool<Point>(1);let v=VALUE;
                let view=&v;print(view.x);let moved=relay(->v);print(moved.x);drop(->moved);
                let again=p.new(x:9);print(again.x);}'''.replace('TYPE',typ).replace('VALUE',value)
            self.assertEqual(self.run_source(source).stdout, '7\n7\n9\n')
            self.assertEqual(verify_program(source).function_contracts['relay'].storage_requirements,
                             ((0,'local' if typ == 'Point' else 'pool'),))
            self.refused(source.replace('let moved=relay(->v);', 'let moved=relay(->v);print(view.x);'),
                         'emprunt|réserv|référenc')
            wrong = 'p.new(x:7)' if typ == 'Point' else 'Point{x:7}'
            self.refused(source.replace('let v='+value, 'let v='+wrong), 'stockage|allocation|local')

    def test_each_return_path_obeys_signature(self):
        source = POINT + '''fn choose(p:&mut Pool<Point>,flag:bool)-><-Point{
            if flag{return <-Point{x:7};}return <-p.new(x:9);}
            fn main(){let mut p=pool<Point>(1);let v=choose(&mut p,true);print(v.x);}'''
        self.refused(source, 'stockage local')
        # The unused definition is checked as well.
        self.refused(source[:source.index('fn main')], 'stockage local')
        self.assertEqual(self.run_source(source.replace('return <-p.new(x:9);',
                                                         'return <-Point{x:9};')).stdout, '7\n')

    def test_implicit_tail_keeps_storage_contract(self):
        for typ, value in (('Point','Point{x:7}'), ('A<Point>','p.new(x:7)')):
            source = POINT + '''fn identity(v:->TYPE)-><-TYPE{<-v}
                fn relay(v:->TYPE)-><-TYPE{let next=identity(->v);<-next}
                fn main(){let mut p=pool<Point>(1);let v=VALUE;
                let result=relay(->v);print(result.x);drop(->result);
                let again=p.new(x:9);print(again.x);}'''.replace('TYPE',typ).replace('VALUE',value)
            self.assertEqual(self.run_source(source).stdout, '7\n9\n')
            self.assertEqual(verify_program(source).function_contracts['relay'].storage_requirements,
                             ((0,'local' if typ == 'Point' else 'pool'),))
            wrong = 'p.new(x:7)' if typ == 'Point' else 'Point{x:7}'
            self.refused(source.replace('let v='+value, 'let v='+wrong), 'stockage|allocation|local')
        self.refused(POINT + 'fn bad(p:&mut Pool<Point>)-><-Point{let n=p.new(x:7);<-n}',
                     'stockage local')

    def test_async_return_and_join(self):
        for typ, value in (('Point','Point{x:7}'), ('A<Point>','p.new(x:7)')):
            source = POINT + '''async fn identity(v:->TYPE)-><-TYPE{yield;return <-v;}
                fn main(){let mut p=pool<Point>(1);let v=VALUE;
                let h=runtime::spawn(->identity(->v));
                match h.join(){Ok(n)=>{print(n.x);drop(->n);},Err(_)=>{print(99);}}
                let again=p.new(x:9);print(again.x);}'''.replace('TYPE',typ).replace('VALUE',value)
            self.assertEqual(self.run_source(source).stdout, '7\n9\n')
            wrong = 'p.new(x:7)' if typ == 'Point' else 'Point{x:7}'
            self.refused(source.replace('let v='+value, 'let v='+wrong), 'stockage|allocation|local')


if __name__ == '__main__':
    unittest.main()
