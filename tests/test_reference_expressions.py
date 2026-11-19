"""B5/D1: references selected by if and builtin match expressions."""
from pathlib import Path
import random
import unittest
from crust import Error, compile_source, verify_program
import test_async_vector_results as native
import test_async_runtime as runtime

class ReferenceExpressionTests(unittest.TestCase):
    run_native=native.AsyncVectorResultTests.run_native
    reject_blocking=native.AsyncVectorResultTests.reject_blocking
    rejecting_callback=native.AsyncVectorResultTests.rejecting_callback
    run_c_oracle=runtime.AsyncRuntimeTests.run_c_oracle

    def test_recorded_join_match(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-join-element-match-expression.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'255\n')
        self.assertEqual(self.run_native(source.replace('runtime::spawn(', 'runtime::spawn_blocking('),reject=True).stdout,'255\n')

    def test_pool_targets_and_shared_or_mutable_modes(self):
        for mode in ('ref','mut'):
            marker='&' if mode=='ref' else '&mut '
            write='*picked=99;' if mode=='mut' else ''
            for flag in ('1','0'):
                source=f'''fn pick(flag:Int,a:{marker}Int,b:{marker}Int)->{marker}Int{{
                    return if flag==1{{a}}else{{b}};
                }}
                fn main(){{let mut p=pool<Int>(2);let mut a=p.new(17);let mut b=p.new(42);
                    let mut picked=pick({flag},{marker}a,{marker}b);print(*picked);{write}print(a);print(b);}}'''
                expected=('17' if flag=='1' else '42')+'\n'
                expected+=('99\n42\n' if flag=='1' else '17\n99\n') if mode=='mut' else '17\n42\n'
                with self.subTest(mode=mode,flag=flag):self.assertEqual(self.run_native(source).stdout,expected)
                for operation in ('drop(->a);','drop(->b);','a=8;','b=8;'):
                    with self.subTest(mode=mode,operation=operation),self.assertRaises(Error):
                        verify_program(source.replace('print(*picked);',operation+'print(*picked);'))

    def test_mixed_inline_and_pool_pointer_layout(self):
        for reversed_arms in (False,True):
            for flag in ('1','0'):
                left,right=('&mut row[1]','&mut *fallback')
                if reversed_arms:left,right=right,left
                source=f'''fn pick(flag:Int,row:&mut [Int;2],fallback:&mut Int)->&mut Int{{
                    return if flag==1{{{left}}}else{{{right}}};}}
                    fn main(){{let mut p=pool<Int>(1);let mut fallback=p.new(70);let mut row=[10,20];
                    let mut picked=pick({flag},&mut row,&mut fallback);print(*picked);*picked=99;
                    print(row[0]);print(row[1]);print(fallback);}}'''
                row_selected=(flag=='1') != reversed_arms
                expected='20\n10\n99\n70\n' if row_selected else '70\n10\n20\n99\n'
                with self.subTest(reversed_arms=reversed_arms,flag=flag):
                    self.assertEqual(self.run_native(source).stdout,expected)

    def test_vector_cases_from_two_pools_and_last_use(self):
        for element in ('Int','u8'):
            suffix=' as Int' if element=='u8' else ''
            for flag in ('1','0'):
                source=f'''fn pick(flag:Int,a:&mut Vector<{element}>,b:&mut Vector<{element}>)->&mut {element}{{
                    return if flag==1{{a.push_new()}}else{{b.push_new()}};
                }}
                fn main(){{let mut p=pool<Vector<{element}>>(1);let mut q=pool<Vector<{element}>>(1);
                    let mut a=p.new();let mut b=q.new();let mut cell=pick({flag},&mut a,&mut b);
                    print(*cell{suffix});*cell=255;print(a.len());print(b.len());
                    drop(->a);drop(->b);let again=p.new();let other=q.new();print(again.len());print(other.len());}}'''
                with self.subTest(element=element,flag=flag):
                    self.assertEqual(self.run_native(source).stdout,'0\n'+('1\n0\n' if flag=='1' else '0\n1\n')+'0\n0\n')
                    for name in ('a','b'):
                        with self.subTest(invalid_source=name),self.assertRaises(Error):
                            verify_program(source.replace('print(*cell'+suffix+');',f'drop(->{name});print(*cell{suffix});'))

    def test_join_expression_keeps_ancestor_and_fallback(self):
        for failed in (False,True):
            source='''async fn append(v:&mut Vector<u8>)->&mut u8{yield;print(11);return v.push_new();}
                fn relay(v:&mut Vector<u8>,fallback:&mut Vector<u8>)->&mut u8{
                    let h=runtime::spawn_blocking(->append(v));
                    return match h.join(){Ok(c)=>{print(1);&mut *c},Err(_)=>{print(2);fallback.push_new()}};
                }
                fn main(){let mut p=pool<Vector<u8>>(2);let mut a=p.new();let mut b=p.new();
                    let mut c=relay(&mut a,&mut b);*c=255;print(a.len());print(b.len());}'''
            with self.subTest(failed=failed):
                self.assertEqual(self.run_native(source,reject=failed).stdout,'2\n0\n1\n' if failed else '11\n1\n1\n0\n')
            for name in ('a','b'):
                with self.subTest(name=name),self.assertRaises(Error):
                    verify_program(source.replace('*c=255;',f'{name}.push(9);*c=255;'))

    def test_local_sources_and_wrong_modes_rejected(self):
        sources=(
            '''fn bad(flag:Int,a:&mut Int)->&mut Int{return if flag==1{let mut p=pool<Int>(1);let mut x=p.new(1);&mut x}else{a};}''',
            '''fn bad(flag:Int,a:&mut Vector<Int>)->&mut Int{return if flag==1{let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push_new()}else{a.push_new()};}''',
            '''fn bad(flag:Int,a:&mut Int,b:&Int)->&mut Int{return if flag==1{a}else{b};}''',
            '''fn bad(flag:Int,a:&mut Int,b:&mut u8)->&mut Int{return if flag==1{a}else{b};}''',
            '''fn bad(flag:Int,a:&mut Int)->&mut Int{return if flag==1{let mut table=[1,2];&mut table[0]}else{a};}''',
        )
        for source in sources:
            with self.subTest(source=source),self.assertRaises(Error):verify_program(source)

    def test_nested_conditions_and_early_returns(self):
        for first,second in ((True,False),(False,True),(False,False)):
            source=f'''fn pick(first:Int,second:Int,a:&mut Int,b:&mut Int,c:&mut Int)->&mut Int{{
                return if first==1{{return a;}}else{{if second==1{{b}}else{{c}}}};
            }}
            fn main(){{let mut p=pool<Int>(3);let mut a=p.new(10);let mut b=p.new(20);let mut c=p.new(30);
                let mut r=pick({int(first)},{int(second)},&mut a,&mut b,&mut c);print(*r);*r=99;
                print(a);print(b);print(c);}}'''
            values=[10,20,30];index=0 if first else 1 if second else 2;old=values[index];values[index]=99
            self.assertEqual(self.run_native(source).stdout,''.join(f'{n}\n' for n in (old,*values)))

    def test_local_bindings_reborrows_and_iteration_exits(self):
        source='''fn main(){let mut p=pool<Vector<Int>>(2);let mut a=p.new();let mut b=p.new();
            let mut i=0;loop{
                let mut cell=if i==0{let mut inner=a.push_new();&mut *inner}else{b.push_new()};
                *cell=17;print(*cell);i=i+1;if i==1{continue;}break;
            }print(a.len());print(b.len());print(a[0]);print(b[0]);
            let mut c=if a[0]==17{a.push_new()}else{b.push_new()};*c=29;print(a[1]);}'''
        self.assertEqual(self.run_native(source).stdout,'17\n17\n1\n1\n17\n17\n29\n')
        for name in ('a','b'):
            with self.subTest(name=name),self.assertRaises(Error):
                verify_program(source.replace('*cell=17;',f'{name}.push(8);*cell=17;'))

    def test_shared_structure_reference_keeps_selected_target(self):
        for flag in (0,1):
            source=f'''struct Point{{x:Int}}
                fn pick(flag:Int,a:&Point,b:&Point)->&Point{{return if flag==1{{a}}else{{b}};}}
                fn main(){{let mut p=pool<Point>(2);let a=p.new(x:17);let b=p.new(x:42);
                    let selected=pick({flag},&a,&b);print(selected.x);drop(->a);drop(->b);}}'''
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source).stdout,'17\n' if flag else '42\n')
                for name in ('a','b'):
                    with self.subTest(drop=name),self.assertRaises(Error):
                        verify_program(source.replace('print(selected.x);',f'drop(->{name});print(selected.x);'))

    def test_condition_and_selected_arm_evaluate_once_in_order(self):
        source='''fn tick(n:&mut Int)->Int{*n=*n+1;print(*n);return *n;}
            fn main(){let mut p=pool<Int>(3);let mut n=p.new(0);let mut a=p.new(17);let mut b=p.new(42);
                let mut r=if tick(&mut n)==1{print(10);&mut a}else{print(20);&mut b};
                *r=99;print(n);print(a);print(b);}'''
        self.assertEqual(self.run_native(source).stdout,'1\n10\n1\n99\n42\n')

    def test_model_selects_target_and_rejects_every_possible_source_release(self):
        rng=random.Random(1771)
        for first,second in [(rng.randrange(2),rng.randrange(2)) for _ in range(5)]:
            source=f'''fn pick(a:&mut Int,b:&mut Int,c:&mut Int,x:Int,y:Int)->&mut Int{{
                return if x==1{{if y==1{{a}}else{{b}}}}else{{c}};
            }}fn main(){{let mut p=pool<Int>(3);let mut a=p.new(1);let mut b=p.new(2);let mut c=p.new(3);
                let mut r=pick(&mut a,&mut b,&mut c,{first},{second});*r=50;print(a);print(b);print(c);}}'''
            values=[1,2,3];selected=0 if first and second else 1 if first else 2;values[selected]=50
            self.assertEqual(self.run_native(source).stdout,''.join(f'{n}\n' for n in values))
            for name in ('a','b','c'):
                with self.subTest(first=first,second=second,drop=name),self.assertRaises(Error):
                    verify_program(source.replace('*r=50;',f'drop(->{name});*r=50;'))

    def test_scope_boundary_before_array_source_cleanup(self):
        # No function summary can hide an invalid arm-local array or vector.
        for local in (
            'let mut table=[1,2];&mut table[0]',
            'let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push_new()',
        ):
            source=f'''fn main(){{let mut p=pool<Int>(1);let mut outer=p.new(7);
                let mut r=if true{{{local}}}else{{&mut outer}};*r=99;}}'''
            with self.subTest(local=local),self.assertRaisesRegex(Error,'non durable'):
                verify_program(source)

    def test_reset_default_and_historical_borrow_check(self):
        source='''fn pick(a:&mut Vector<Int>,b:&mut Vector<Int>,n:Int)->&mut Int{
                return if n==1{a.push_new()}else{b.push_new()};}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut q=pool<Vector<Int>>(1);
                let mut a=p.new();let mut b=q.new();let mut c=pick(&mut a,&mut b,1);
                p.reset();print(*c);}'''
        with self.assertRaises(Error):verify_program(source)
        for pool in ('p','q'):
            with self.subTest(pool=pool),self.assertRaises(Error):
                verify_program(source.replace('p.reset();',pool+'.reset();'),allow_legacy_reset=True)

    def test_conditional_match_projection_keeps_writer_reserved(self):
        for flag in (0,1):
            prefix=f'''enum W{{Bound{{data:&mut Int}}}}
                fn main(){{let mut p=pool<Int>(2);let mut q=pool<W>(1);
                let mut n=p.new(10);let mut fallback=p.new(20);
                let mut w=new(q)W.Bound{{data:&mut n}};
                let mut out=if {flag}==1{{match &mut w{{W.Bound{{data:r}}=>{{r}}}}}}else{{&mut fallback}};'''
            source=prefix+'out.set(30);print(w);print(fallback);print(n);}'
            self.assertEqual(self.run_native(source).stdout,'W.Bound(30)\n20\n30\n' if flag else 'W.Bound(10)\n30\n10\n')
            for action in ('print(w);','drop(->w);'):
                with self.subTest(flag=flag,action=action),self.assertRaisesRegex(Error,'emprunt|réserv'):
                    verify_program(prefix+action+'out.set(30);}')
