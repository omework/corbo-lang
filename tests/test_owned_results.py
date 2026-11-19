"""Brouillon 01: explicit consumption and type-based owned-pattern checks."""
import unittest
import test_foundation_rules
from crust import Error, compile_source, verify_program


class OwnedResultTests(unittest.TestCase):
    native = test_foundation_rules.FoundationTests.native
    prefix = '''let mut p=pool<Int>(2);let mut q=pool<Int>(1);
        let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();'''

    def test_drop_pop_reuses_slot_through_function_contract_and_empty_result(self):
        run=self.native('''
            fn remove(v:&mut Vector<A<Int>>){drop(-> v.pop());}
            fn relay(v:&mut Vector<A<Int>>){remove(v);}
            fn main(){let mut p=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);let mut v=vp.new();
                let x=p.new(7);address(x);v.push(-> x);
                relay(&mut v);
                let next=p.new(9);address(next);print(*next);
                drop(-> v.pop());print(v.len());
            }
        ''')
        self.assertEqual(run.returncode,0,run.stderr)
        first,reused,value,length=run.stdout.splitlines()
        self.assertEqual((first,value,length),(reused,'9','0'))
        self.assertEqual(run.stderr.count('destroy x=7'),1)
        self.assertLess(run.stderr.index('destroy x=7'),run.stderr.index('destroy next=9'))

    def test_pop_patterns_are_checked_even_when_empty(self):
        patterns=(
            'Some(_)=>{},None=>{}',
            'Some(unused)=>{},None=>{}',
            'Some(_unused)=>{},None=>{}',
            'None=>{},_=>{}',
            '_=>{}',
        )
        for fill in ('','v.push(-> p.new(7));'):
            for pattern in patterns:
                for subject in ('match <- v.pop()', 'let result=<- v.pop();match (-> result)'):
                    source='fn main(){'+self.prefix+fill+subject+'{'+pattern+'}}'
                    with self.subTest(fill=fill,pattern=pattern,subject=subject),self.assertRaisesRegex(Error,'motif _|sans usage explicite'):
                        compile_source(source)
            for statement in ('let _=<- v.pop();','let unused=<- v.pop();','let _unused=<- v.pop();'):
                with self.subTest(statement=statement),self.assertRaisesRegex(Error,'motif _|sans usage explicite'):
                    compile_source('fn main(){'+self.prefix+fill+statement+'}')

    def test_named_owned_payload_can_be_used_conditionally_and_cleanup_at_arm_exit(self):
        source='''fn run(flag:Int){PREFIX
            v.push(-> p.new(7));
            match <- v.pop(){Some(value)=>{if flag==1 {print(*value);}},None=>{}}
            let reused=p.new(9);print(*reused);
        }fn main(){run(0);run(1);}'''.replace('PREFIX',self.prefix)
        run=self.native(source)
        self.assertEqual((run.returncode,run.stdout),(0,'9\n7\n9\n'),run.stderr)
        self.assertEqual(sum(line.endswith('=7') for line in run.stderr.splitlines() if line.startswith('destroy ')),2)

    def test_replace_and_try_push_patterns_require_the_owned_payload(self):
        for operation in ('v.replace(0, -> q.new(9))','v.replace(8, -> q.new(9))','v.try_push(-> q.new(9))'):
            success='Ok(())' if 'try_push' in operation else 'Ok(old)'
            success_body='' if 'try_push' in operation else 'drop(-> old);'
            for patterns in (f'{success}=>{{{success_body}}},Err(_)=>{{}}',
                             f'{success}=>{{{success_body}}},Err(unused)=>{{}}',
                             f'{success}=>{{{success_body}}},_=>{{}}'):
                for subject in ('match <- '+operation,'let result=<- '+operation+';match (-> result)'):
                    source='fn main(){'+self.prefix+'v.push(-> p.new(7));'+subject+'{'+patterns+'}}'
                    with self.subTest(operation=operation,subject=subject),self.assertRaisesRegex(Error,'motif _|sans usage explicite'):
                        compile_source(source)
        run=self.native('fn main(){'+self.prefix+'''
            let result=<- v.try_push(-> p.new(7));
            match (-> result){Err(value)=>{drop(-> value);},_=>{print(v.len());}}
        }''')
        self.assertEqual((run.returncode,run.stdout),(0,'1\n'),run.stderr)

    def test_drop_try_push_only_destroys_rejected_handle(self):
        run=self.native('''fn main(){
            let mut p=pool<Int>(131072);let mut q=pool<Int>(1);
            let mut vp=pool<Vector<A<Int>>>(1);
            #(directive, stack_region_max_size=1M){let mut v=vp.new();
                drop(-> v.try_push(-> p.new(7)));print(v.len());
                let mut i=1;while i<131072{v.push(-> p.new(i));i=i+1;}
                let incoming=q.new(37);address(incoming);
                drop(-> v.try_push(-> incoming));
                let reused=q.new(38);address(reused);print(v.len());
            }
        }''')
        self.assertEqual(run.returncode,0,run.stderr[-1000:])
        initial,incoming,reused,length=run.stdout.splitlines()
        self.assertEqual((initial,incoming,length),('1',reused,'131072'))
        self.assertEqual(run.stderr.count('destroy incoming=37'),1)

    def test_nonowning_payloads_can_still_be_ignored_or_dropped(self):
        run=self.native('''fn main(){let mut numbers=pool<Vector<Int>>(1);let mut v=numbers.new();
            v.push(7);drop(-> v.pop());drop(-> v.pop());
            v.push(8);match v.pop(){Some(_)=>{},None=>{}}print(v.len());
            let mut strings=pool<String>(1);let mut s=strings.new();s.push_str("é");
            drop(-> s.pop());print(s.byte_len());
        }''')
        self.assertEqual((run.returncode,run.stdout),(0,'0\n0\n'),run.stderr)

    def test_consuming_enum_cannot_discard_owned_fields_on_any_variant(self):
        prefix='''enum Item { Value { data:A<Int> }, Empty }
            let mut p=pool<Int>(1);let mut items=pool<Item>(1);'''
        for construction in ('let item=new(items) Item.Empty;',
                             'let data=p.new(7);let item=new(items) Item.Value {data:<- data};'):
            for patterns in ('Item.Value {data:_}=>{},Item.Empty=>{}',
                             'Item.Empty=>{},_=>{}',
                             'Item.Value {data:unused}=>{},Item.Empty=>{}'):
                with self.subTest(construction=construction,patterns=patterns),self.assertRaisesRegex(Error,'motif _|sans usage explicite'):
                    compile_source(prefix+construction+'match (-> item){'+patterns+'}')
        run=self.native(prefix+'''let data=p.new(7);let item=new(items) Item.Value {data:<- data};
            match (-> item){Item.Value {data:value}=>{print(*value);},Item.Empty=>{}}
            let reused=p.new(9);print(*reused);
        ''')
        self.assertEqual((run.returncode,run.stdout),(0,'7\n9\n'),run.stderr)

    def test_async_join_owned_patterns_and_bindings_require_explicit_usage(self):
        prefix='''async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            async fn run(n: -> Int) {let t=work(-> n);let h=runtime::spawn(-> t);
                BODY
            }
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);let t=run(-> n);
                let h=runtime::spawn(-> t);let r=h.join();
                match r {Ok(())=>{},Err(_)=>{}}
                let reused=p.new(9);print(*reused);
            }'''
        for body in ('let unused=h.await;', 'let _unused=h.await;', 'let _=h.await;',
                     'let r=h.await;match r {Ok(_)=>{},Err(_)=>{}}',
                     'let r=h.await;match r {Ok(unused)=>{},Err(_)=>{}}',
                     'match h.await {Ok(_)=>{},Err(_)=>{}}'):
            with self.subTest(body=body),self.assertRaisesRegex(Error,'motif _|sans usage explicite'):
                compile_source(prefix.replace('BODY',body))
        run=self.native(prefix.replace('BODY',
            'let r=h.await;match r {Ok(value)=>{print(*value);},Err(_)=>{}}'))
        self.assertEqual((run.returncode,run.stdout),(0,'7\n9\n'),run.stderr)
        self.assertEqual(run.stderr.count('destroy n=7'),1)

    def test_drop_pop_respects_last_borrow_use_and_invalidates_transferred_name(self):
        prefix='''fn consume(v:&mut Vector<A<Int>>){drop(-> v.pop());}
            fn relay(v:&mut Vector<A<Int>>){consume(v);}
            fn main(){let mut p=pool<Int>(1);let mut vp=pool<Vector<A<Int>>>(1);
                let mut v=vp.new();let original=p.new(7);v.push(-> original);
                let mut q=pool<Int>(1);let checker=q.new(7);
                let view=&v[0]; BODY
            }'''
        run=self.native(prefix.replace('BODY',
            'if checker.vequals(view) {print(7);}relay(&mut v);let reused=p.new(9);print(*reused);'))
        self.assertEqual((run.returncode,run.stdout),(0,'7\n9\n'),run.stderr)
        for body,diagnostic in (
            ('relay(&mut v);if checker.vequals(view) {print(7);}','emprunt actif'),
            ('if checker.vequals(view) {print(7);}relay(&mut v);print(*original);','plus utilisable'),
        ):
            with self.subTest(body=body),self.assertRaisesRegex(Error,diagnostic):
                compile_source(prefix.replace('BODY',body))
