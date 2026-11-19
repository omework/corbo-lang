"""Crust source integration for HashMap HM1–HM6."""
import unittest

from crust import Error, compile_source, verify_program
import test_async_runtime


class HashMapTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_shared_nominal_reference_is_tracked_per_entry(self):
        source = """
            struct Point { n:i64 }
            fn main() {
                let mut p=Point { n:42 };
                let mut q=Point { n:9 };
                let key:i64=1;
                let mut m=HashMap<i64,&Point>::new();
                m.insert(1,&p);
                m.insert(2,&q);
                match m.get(&key) {
                    Some(slot)=>{ let view=*slot; print(view.n); }, None=>{}
                }
                match m.remove(&key) { Some(view)=>{ print(view.n); }, None=>{} }
                p.n=7;
                print(p.n);
                drop(m);
            }
        """
        self.runs(source, '42\n42\n7\n')
        self.refuses(source.replace('p.n=7;', 'q.n=7;'), 'emprunt actif')
        self.refuses(source.replace('match m.get(&key)', 'p.n=7; match m.get(&key)'), 'emprunt actif')
        escaped = """
            struct Point { n:i64 }
            fn main() {
                let mut m=HashMap<i64,&Point>::new();
                { let local=Point { n:42 }; m.insert(1,&local); }
                drop(m);
            }
        """
        self.refuses(escaped, 'cible.*survit|non durable')

    def test_shared_inline_reference_keeps_its_projection(self):
        source = """
            struct Point { n:i64 }
            struct Pair { first:Point, second:Point }
            fn main() {
                let mut pair=Pair { first:Point { n:42 }, second:Point { n:1 } };
                let key:i64=1;
                let mut m=HashMap<i64,&Point>::new();
                m.insert(1,&pair.first);
                pair.second.n=3;
                match m.get(&key) {
                    Some(slot)=>{ let view=*slot; print(view.n); }, None=>{}
                }
                match m.remove(&key) { Some(view)=>{ print(view.n); }, None=>{} }
                pair.first.n=7;
                print(pair.first.n);
                print(pair.second.n);
            }
        """
        self.runs(source, '42\n42\n7\n3\n')
        self.refuses(source.replace('pair.second.n=3;', 'pair.first.n=3;'), 'emprunt actif')
        self.refuses(source.replace('Some(view)=>{ print(view.n); }',
                                    'Some(view)=>{ pair.first.n=3; print(view.n); }'), 'emprunt actif')

    def test_mutable_nominal_reference_moves_into_entry_and_out_on_remove(self):
        source = """
            struct Point { n:i64 }
            struct Pair { first:Point, second:Point }
            fn main() {
                let mut pair=Pair { first:Point { n:42 }, second:Point { n:1 } };
                let key:i64=1;
                let mut m=HashMap<i64,&mut Point>::new();
                let original=&mut pair.first;
                m.insert(1,original);
                pair.second.n=8;
                match m.remove(&key) {
                    Some(view)=>{ view.n=7; print(view.n); }, None=>{}
                }
                print(pair.first.n);
                print(pair.second.n);
            }
        """
        self.runs(source, '7\n7\n8\n')
        self.refuses(source.replace('pair.second.n=8;', 'print(original.n);'), 'plus utilisable')
        self.refuses(source.replace('pair.second.n=8;', 'print(pair.first.n);'), 'emprunt actif')
        self.refuses(source.replace('view.n=7;', 'pair.first.n=7;'), 'emprunt actif')

    def test_shared_parameter_can_read_a_reference_entry(self):
        source = """
            fn read(m: &HashMap<i64, &i64>, key: &i64) -> i64 {
                match m.get(key) { Some(view) => { **view }, None => { 0 } }
            }
            fn main() {
                let mut n: i64 = 42;
                let key: i64 = 1;
                let mut m = HashMap<i64, &i64>::new();
                m.insert(1, &n);
                print(read(&m, &key));
                drop(m);
                n = 7;
                print(n);
            }
        """
        self.runs(source, '42\n7\n')
        self.refuses(source.replace('print(read(&m, &key));', 'n = 7; print(read(&m, &key));'),
                     'emprunt actif')
        self.refuses(source.replace('match m.get(key)', 'm.remove(key); match m.get(key)'),
                     'emprunt en lecture')

    def test_function_contract_replaces_one_reference_entry(self):
        source = '''
            fn poser(m: &mut HashMap<i64, &i64>, vue: &i64) { m.insert(42, vue); }
            fn main() {
                let mut old: i64 = 1;
                let next: i64 = 42;
                let mut m = HashMap<i64, &i64>::new();
                m.insert(42, &old);
                poser(&mut m, &next);
                old = 7;
                let key: i64 = 42;
                match m.get(&key) { Some(v) => { print(**v); }, None => { print(0); } }
                print(old);
            }
        '''
        self.runs(source, '42\n7\n')
        self.refuses(source.replace('poser(&mut m, &next);', '''
            { let local: i64 = 42; poser(&mut m, &local); }
        '''), 'cible empruntée non durable')
        self.refuses(source.replace('let next:', 'let mut next:').replace('old = 7;', 'next = 7;'),
                     'emprunt actif')
        relay = source.replace('fn main()', '''
            fn relayer(m: &mut HashMap<i64, &i64>, vue: &i64) { poser(m, vue); }
            fn main()
        ''').replace('poser(&mut m, &next);', 'relayer(&mut m, &next);')
        self.runs(relay, '42\n7\n')
        conditional = source.replace('vue: &i64) { m.insert(42, vue); }',
                                     'vue: &i64, ok: bool) { if ok { m.insert(42, vue); } }')
        conditional = conditional.replace('poser(&mut m, &next);', 'poser(&mut m, &next, false);')
        self.refuses(conditional, 'emprunt actif')
        self.runs(conditional.replace('old = 7;', ''), '1\n1\n')

    def runs(self, source, stdout):
        verify_program(source)
        result = self.run_c_oracle(compile_source(source))
        self.assertEqual(result.stdout, stdout)
        return result

    def refuses(self, source, diagnostic):
        for entry in (verify_program, compile_source):
            with self.subTest(entry=entry.__name__):
                with self.assertRaisesRegex(Error, diagnostic):
                    entry(source)

    def test_scalar_operations_replace_and_lookup(self):
        self.runs('''fn main(){
            let mut m=HashMap<i64,i32>::new();
            m.insert(42,10);
            let k:i64=42;
            let old=m.insert(42,20);
            match old{Some(x)=>{print(x);},None=>{}}
            match m.get_mut(&k){Some(x)=>{*x=30;},None=>{}}
            match m.get(&k){Some(x)=>{print(*x);},None=>{}}
            match m.remove(&k){Some(x)=>{print(x);},None=>{}}
            match m.get(&k){Some(x)=>{print(*x);},None=>{print(99);}}
        }''', '10\n30\n30\n99\n')
        self.runs('''fn main(){let mut m=HashMap<bool,i32>::new();m.insert(true,8);
            let k=true;match m.get(&k){Some(x)=>{print(*x);},None=>{}}}''', '8\n')
        self.refuses('fn main(){let m=HashMap<f32,i32>::new();drop(m);}', 'clé HashMap')

    def test_shared_and_mutable_loans_cover_the_table(self):
        setup = '''fn main(){let mut m=HashMap<i64,i32>::new();
            m.insert(7,20);let k:i64=7;let other:i64=42;'''
        for method, access in (
            ('get', 'm.insert(42,90);'),
            ('get_mut', 'match m.get(&other){Some(y)=>{print(*y);},None=>{}}'),
        ):
            source = setup + f'match m.{method}(&k){{Some(x)=>{{{access}print(*x);}},None=>{{}}}}}}'
            self.refuses(source, 'emprunt actif')
            source = setup + f'match m.{method}(&k){{Some(x)=>{{print(*x);{access}}},None=>{{}}}}}}'
            self.runs(source, '20\n')

    def test_scalar_table_and_key_can_be_borrowed_by_functions(self):
        self.runs('''fn poser(m:&mut HashMap<i64,i32>){m.insert(42,10);}
            fn lire(m:&HashMap<i64,i32>,k:&i64){
                match m.get(k){Some(n)=>{print(*n);},None=>{}}
            }
            fn main(){let mut m=HashMap<i64,i32>::new();poser(&mut m);
                let k:i64=42;lire(&m,&k);
                let r=m.get(&k);drop(k);match r{Some(n)=>{print(*n);},None=>{}}
            }''', '10\n10\n')

    def test_nominal_payload_is_owned_until_extraction(self):
        self.runs('''struct Point{x:i32}
            fn main(){let mut m=HashMap<i64,Point>::new();m.insert(7,Point{x:12});
                let k:i64=7;
                match m.get(&k){Some(p)=>{print(p.x);},None=>{}}
                match m.remove(&k){Some(p)=>{print(p.x);drop(p);},None=>{}}
            }''', '12\n12\n')

    def test_public_operations_match_dictionary_model(self):
        sequence = [('insert', 5, 15), ('insert', 13, 30), ('insert', 5, 27),
                    ('remove', 17, None), ('get', 13, None), ('remove', 5, None),
                    ('insert', -11, 2), ('get', 5, None), ('get', -11, None)]
        source = ['fn main(){let mut table=HashMap<i64,i32>::new();']
        expected = []
        model = {}
        for position, (operation, key, value) in enumerate(sequence):
            old = model.get(key, -1)
            if operation == 'insert':
                model[key] = value
                call = f'table.insert({key},{value})'
                printed = 'result'
            else:
                if operation == 'remove':
                    model.pop(key, None)
                source.append(f'let key{position}:i64={key};')
                call = f'table.{operation}(&key{position})'
                printed = '*result' if operation == 'get' else 'result'
            source.append(f'match {call}{{Some(result)=>{{print({printed});}},None=>{{print(-1);}}}}')
            expected.append(f'{old}\n')
        self.runs(''.join(source) + '}', ''.join(expected))

    def test_pool_dependencies_are_per_key(self):
        setup = '''fn main(){
            let mut p=pool<i32>(1);let mut m=HashMap<i64,A<i32>>::new();
            m.insert(42,p.new(10));
            {let mut child=pool<i32>(1);m.insert(7,child.new(20));'''
        extraction = '''let k:i64=7;match m.remove(&k){Some(n)=>{print(*n);drop(n);},None=>{}}'''
        remainder = '''}
            let k:i64=42;match m.get(&k){Some(n)=>{print(**n);},None=>{}}
            drop(m);
            let n=p.new(30);print(*n);drop(n);
        }'''
        self.runs(setup + extraction + remainder, '20\n10\n30\n')
        self.refuses(setup + remainder, "source 'child' serait détruite")

    def test_reference_replacement_changes_only_its_entry(self):
        source = '''fn main(){let mut a:i32=10;let mut b:i32=20;let mut c:i32=30;
            let mut m=HashMap<i64,&mut i32>::new();
            m.insert(1,&mut a);m.insert(2,&mut b);
            let cle:i64=1;
            match m.get_mut(&cle){Some(slot)=>{**slot=11;*slot=&mut c;},None=>{}}
            let cle_b:i64=2;
            match m.get(&cle_b){Some(slot)=>{print(**slot);},None=>{}}
            drop(m);
            print(a);print(c);
        }'''
        self.runs(source, '20\n11\n30\n')
        self.refuses(source.replace('drop(m);', 'b=99;drop(m);'), 'emprunt actif|incompatible')
        self.refuses('''fn main(){let mut m=HashMap<i64,&i32>::new();
            {let a:i32=10;m.insert(1,&a);}drop(m);}''', 'cible qui ne survit pas')

    def test_try_insert_restores_owned_value_when_capacity_is_exhausted(self):
        self.runs('''fn main(){let mut p=pool<i32>(2);
            let mut m=HashMap<i64,A<i32>>::new();
            m.insert(42,p.new(10));
            match m.try_insert(42,p.new(20)){
                Ok(Some(old))=>{print(*old);drop(old);},
                Ok(None)=>{},
                Err(value)=>{drop(value);},
            }
            let k:i64=42;match m.get(&k){Some(x)=>{print(**x);},None=>{}}
        }''', '10\n20\n')
        source = '''fn main(){let mut outer=pool<i32>(2);
            let mut m=HashMap<i64,A<i32>>::new();
            m.insert(42,outer.new(10));
            {let mut inner=pool<i32>(1);
                let result=m.try_insert(7,inner.new(20));
                m.insert(42,outer.new(11));
                match result{
                    Ok(Some(old))=>{drop(old);loop{}},
                    Ok(None)=>{loop{}},
                    Err(value)=>{print(*value);drop(value);},
                }
            }
            let k:i64=42;match m.get(&k){Some(x)=>{print(**x);},None=>{}}
        }'''
        verify_program(source)
        # One entry fits. Force this boundary without allocating thousands of Crust objects.
        code = compile_source(source)
        capacity = '16777216, sizeof(Cell *), _Alignof(Cell *), 1)'
        self.assertIn(capacity, code)
        code = code.replace(capacity,
            'sizeof(CrustMapEntry) + _Alignof(max_align_t) + 4*sizeof(size_t), sizeof(Cell *), _Alignof(Cell *), 1)')
        self.assertEqual(self.run_c_oracle(code).stdout, '20\n11\n')
