"""Recursive container/reference lifetime interactions, with executable C oracles."""
from functools import partial, update_wrapper
import unittest
import random
import test_fixed_arrays
from crust import Compiler, Error, Parser, compile_source, verify_program

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)


class NestedReferenceRowTests(unittest.TestCase):
    execute = test_fixed_arrays.FixedArrayTests.execute

    def reject(self, source, diagnostic='reset|emprunt|durable|libérée|locale'):
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__), self.assertRaisesRegex(Error, diagnostic):
                stage(source)

    def test_nested_leaf_last_use_allows_only_the_finished_pool(self):
        program='''
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);
                let row=[&a,&b];let refs=[&row];
                print(*refs[0][0]);p.reset();print(*refs[0][1]);
            }
        '''
        self.execute(program,[1,2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))
        self.reject(program.replace('print(*refs[0][0]);p.reset();','p.reset();print(*refs[0][0]);'))
        self.reject(program.replace('p.reset()', 'drop(-> b)'))
        self.execute(program.replace('p.reset()', 'drop(-> a)'),[1,2],
                     trace='destroy a=1\nreclaim a\ndestroy b=2\nreclaim b\n')

    def test_nested_mutable_reborrow_suspends_and_restores_the_selected_leaf(self):
        program='''
            fn main(){
                let mut a=[1];let mut b=[2];
                let mut row=[&mut a[0],&mut b[0]];let mut refs=[&mut row];
                let mut child=&mut *refs[0][0];*child=3;
                *refs[0][0]=4;*refs[0][1]=5;
                print(a[0]);print(b[0]);
            }
        '''
        self.execute(program,[4,5])
        self.reject(program.replace('*child=3;', '*refs[0][0]=9;*child=3;'))
        self.reject(program.replace('*child=3;', 'a[0]=9;*child=3;'))
        self.reject(program.replace('let mut child=&mut *refs[0][0];', 'a[0]=9;let mut child=&mut *refs[0][0];'))
        self.execute(program.replace('*child=3;', '*refs[0][1]=9;*child=3;'),[4,5])
        self.reject(program.replace('let mut refs=[&mut row]', 'let mut refs=[&row]'), 'lecture|immuable|mutable')

    def test_returned_reference_tree_keeps_container_and_leaf_sources(self):
        program='''
            fn wrap(r:&[&Int;2])->[&[&Int;2];1]{return <-[r];}
            fn relay(r:&[&Int;2])->[&[&Int;2];1]{let v=wrap(r);return <-v;}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let row=[&a,&b];
                let refs=relay(&row);print(*refs[0][0]);p.reset();print(*refs[0][1]);
            }
        '''
        self.execute(program,[1,2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))
        self.reject('''
            fn bad(d:&Int)->[&[&Int;1];1]{let row=[d];return <-[&row];}
            fn main(){let mut p=pool<Int>(1);let a=new(p)Int(1);let v=bad(&a);print(*v[0][0]);}
        ''')

    def test_direct_container_result_transports_its_content_contract(self):
        program='''
            fn inner(v:[&[&Int;2];1])->&[&Int;2]{return v[0];}
            fn relay(v:[&[&Int;2];1])->&[&Int;2]{return inner(copy(v));}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let row=[&a,&b];let v=[&row];
                let r=relay(copy(v));print(*r[0]);p.reset();print(*r[1]);
            }
        '''
        self.execute(program,[1,2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))
        interface=verify_program('fn inner(v:[&[&Int;1];1])->&[&Int;1]{return v[0];}')
        caller=Compiler(allow_legacy_reset=True);caller.contract_calls=True
        caller.function_contracts=dict(interface.function_contracts)
        nodes=Parser('let mut p=pool<Int>(1);let a=new(p)Int(1);let row=[&a];let v=[&row];let r=inner(copy(v));print(*r[0]);').parse()
        caller.index(nodes);caller.block('root',nodes)

    def test_nested_update_contract_changes_the_actual_row_and_pool_requirement(self):
        program='''
            fn update(v:&mut [&mut [&Int;1];1],d:&Int){v[0][0]=d;}
            fn relay(v:&mut [&mut [&Int;1];1],d:&Int){update(v,d);}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let mut row=[&a];
                let mut refs=[&mut row];relay(&mut refs,&b);
                p.reset();print(*refs[0][0]);print(*row[0]);
            }
        '''
        self.execute(program,[2,2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))
        self.reject(program.replace('p.reset()', 'drop(-> b)'))

    def test_nested_local_overwrite_updates_liveness_before_reset(self):
        program='''
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let mut row=[&a];
                let mut refs=[&mut row];refs[0][0]=&b;
                p.reset();print(*refs[0][0]);
            }
        '''
        self.execute(program,[2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))

    def test_nested_reference_tree_transfer_through_branch_and_loop(self):
        program='''
            fn choose(a:&[&Int;1],b:&[&Int;1],i:Int)->[&[&Int;1];1]{
                let v=if i==0 { <-[a] } else { <-[b] };
                let r=loop{let local=copy(v);break <-local;};return <-r;
            }
            fn play(i:Int){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let ra=[&a];let rb=[&b];
                let refs=choose(&ra,&rb,i);print(*refs[0][0]);
            }
            fn main(){play(0);play(1);}
        '''
        self.execute(program,[1,2],trace='destroy b=2\nreclaim b\ndestroy a=1\nreclaim a\n'*2)
        self.reject(program.replace('print(*refs[0][0]);','p.reset();print(*refs[0][0]);'))
        self.reject(program.replace('print(*refs[0][0]);','q.reset();print(*refs[0][0]);'))

    def test_nested_indices_evaluate_once_and_stop_before_inner_effect(self):
        self.execute('''
            fn mark(i:Int)->Int{print(i);return i;}
            fn read(v:[&[&Int;1];1],i:Int){print(*v[i][mark(0)]);}
            fn main(){
                let mut p=pool<Int>(1);let a=new(p)Int(7);let row=[&a];let v=[&row];
                print(*v[mark(0)][mark(0)]);read(copy(v),1);
            }
        ''',[0,0,7],diagnostic='indice hors limites')

    def test_recursive_depth_three_retains_the_leaf_allocation(self):
        program='''
            fn read(v:[&[&[&Int;1];1];1])->Int{return *v[0][0][0];}
            fn main(){let mut p=pool<Int>(1);let a=new(p)Int(7);
                let row=[&a];let middle=[&row];let top=[&middle];print(read(copy(top)));}
        '''
        self.execute(program,[7],trace='destroy a=7\nreclaim a\n')
        self.reject(program.replace('print(read(copy(top)));','p.reset();print(read(copy(top)));'))

    def test_nested_replace_returns_old_tree_and_installs_new_tree(self):
        program='''
            fn change(v:&mut [&[&Int;1];1],r:&[&Int;1])->&[&Int;1]{return v.replace(0,r);}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let ra=[&a];let rb=[&b];
                let mut v=[&ra];let old=change(&mut v,&rb);
                print(*old[0]);p.reset();print(*v[0][0]);
            }
        '''
        self.execute(program,[1,2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('print(*old[0]);p.reset();','p.reset();print(*old[0]);'))
        self.reject(program.replace('p.reset()', 'q.reset()'))

    def test_nested_mutable_result_keeps_parent_reserved_until_last_use(self):
        program='''
            fn inner(v:&mut [&mut [&mut Int;1];1])->&mut Int{return &mut *v[0][0];}
            fn relay(v:&mut [&mut [&mut Int;1];1])->&mut Int{return inner(v);}
            fn main(){
                let mut a=[1];let mut row=[&mut a[0]];let mut v=[&mut row];
                let mut r=relay(&mut v);*r=3;*v[0][0]=4;print(a[0]);
            }
        '''
        self.execute(program,[4])
        self.reject(program.replace('*r=3;', '*v[0][0]=8;*r=3;'))
        self.reject(program.replace('*r=3;', 'a[0]=8;*r=3;'))

    def test_nested_enum_field_keeps_both_holder_and_target_reserved(self):
        program='''
            enum W{Bound{data:&mut Int}}
            fn borrow(w:&mut W)->&mut Int{
                let mut r=match &mut w{W.Bound{data:v}=>{v}};return r;
            }
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<W>(1);
                let mut n=new(p)Int(1);let mut w=new(q)W.Bound{data:&mut n};
                let mut row=[borrow(&mut w)];let mut v=[&mut row];
                *v[0][0]=3;print(w);print(n);
            }
        '''
        self.execute(program,['W.Bound(3)',3],trace='destroy w=W.Bound\nreclaim w\ndestroy n=3\nreclaim n\n')
        for operation in ('q.reset();','p.reset();','drop(-> w);','drop(-> n);','print(w);'):
            with self.subTest(operation=operation):
                self.reject(program.replace('*v[0][0]=3;',operation+'*v[0][0]=3;'))

    def test_nested_reset_inside_scalar_write_rhs_is_rejected_by_contract(self):
        program='''
            fn reset(p:&mut Pool<Int>)->Int{p.reset();return 9;}
            fn write(v:&mut [&mut [&mut Int;1];1],p:&mut Pool<Int>){*v[0][0]=reset(p);}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);let mut n=new(q)Int(1);
                let mut row=[&mut n];let mut v=[&mut row];write(&mut v,&mut p);print(n);
            }
        '''
        self.execute(program,[9],trace='reset\ndestroy n=9\nreclaim n\n')
        self.reject(program.replace('new(q)', 'new(p)').replace('print(n);',''))

    def test_nested_shared_pointer_copy_swap_and_replace_against_list_model(self):
        rng=random.Random(20261107)
        model=[0,1,2]
        body=['let a=[10];let b=[20];let c=[30];',
              'let ra=[&a[0]];let rb=[&b[0]];let rc=[&c[0]];',
              'let mut v=[&ra,&rb,&rc];']
        expected=[]
        for _ in range(24):
            a,b=rng.randrange(3),rng.randrange(3)
            if rng.randrange(2):
                body.append(f'v.swap({a},{b});')
                model[a],model[b]=model[b],model[a]
            else:
                body.append(f'{{let old=v.replace({a},&{("ra","rb","rc")[b]});print(*old[0]);}}')
                expected.append((model[a]+1)*10);model[a]=b
            body.append(f'let copy{_}=copy(v);print(*copy{_}[{a}][0]);')
            expected.append((model[a]+1)*10)
        self.execute('fn main(){'+''.join(body)+'}',expected)

    def test_shadowed_alias_updates_the_injected_tree_contract(self):
        program='''
            fn update(v:&mut [&mut [&Int;1];1],d:&Int){
                let mut alias=&mut *v;
                {let mut v=&mut *alias;v[0][0]=d;}
            }
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let mut row=[&a];
                let mut refs=[&mut row];update(&mut refs,&b);
                p.reset();print(*refs[0][0]);
            }
        '''
        self.execute(program,[2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))

    def test_generated_nested_leaf_drop_windows_against_path_model(self):
        for depth in (1,2,3):
            for freed in (0,1):
                for used in (0,1):
                    declarations=['let row=[&a,&b];']
                    name='row'
                    for level in range(depth):
                        declarations.append(f'let r{level}=[&{name}];');name=f'r{level}'
                    access=name+'[0]'*depth+f'[{used}]'
                    source='''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                        let a=new(p)Int(1);let b=new(q)Int(2);'''+''.join(declarations)
                    source+=f'drop(-> {("a","b")[freed]});print(*{access});}}'
                    with self.subTest(depth=depth,freed=freed,used=used):
                        if freed==used:
                            self.reject(source)
                        else:
                            first,second=('a','b') if freed==0 else ('b','a')
                            trace=f'destroy {first}={freed+1}\nreclaim {first}\ndestroy {second}={used+1}\nreclaim {second}\n'
                            self.execute(source,[used+1],trace=trace)

    def test_dynamic_nested_result_reserves_all_possible_pools(self):
        program='''
            fn choose(v:&mut [&mut [&mut Int;1];2],i:Int)->&mut Int{return &mut *v[i][0];}
            fn play(i:Int){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let mut a=new(p)Int(1);let mut b=new(q)Int(2);
                let mut ra=[&mut a];let mut rb=[&mut b];let mut v=[&mut ra,&mut rb];
                let mut r=choose(&mut v,i);*r=9;print(*r);
                *v[0][0]=3;*v[1][0]=4;p.reset();print(b);
            }
            fn main(){play(0);play(1);}
        '''
        self.execute(program,[9,4,9,4],trace='destroy a=3\nreclaim a\nreset\ndestroy b=4\nreclaim b\n'*2)
        for source in ('p','q'):
            self.reject(program.replace('*r=9;',source+'.reset();*r=9;'))

    def test_nested_overwrite_survives_continue_without_reviving_old_leaf(self):
        program='''
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let mut row=[&a];let mut v=[&mut row];
                let mut i=0;
                loop{
                    v[0][0]=&b;print(*v[0][0]);p.reset();
                    if i==1 {break;}
                    i=1;continue;
                }
                print(*v[0][0]);
            }
        '''
        self.execute(program,[2,2,2],trace='destroy a=1\nreclaim a\nreset\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))

    def test_opaque_contract_cannot_mutate_contents_through_shared_row(self):
        from dataclasses import replace
        interface=verify_program('''
            fn update(v:&mut [&mut [&Int;1];1],d:&Int){v[0][0]=d;}
            fn read(v:&mut [&[&Int;1];1],d:&Int){print(*v[0][0]);}
        ''')
        original=interface.function_contracts['read']
        forged=replace(original.result,parameter_fields=interface.function_contracts['update'].result.parameter_fields)
        caller=Compiler(allow_legacy_reset=True);caller.contract_calls=True
        caller.function_contracts=dict(interface.function_contracts)
        caller.function_contracts['read']=replace(original,result=forged)
        nodes=Parser('let a=[1];let b=[2];let row=[&a[0]];let mut v=[&row];read(&mut v,&b[0]);').parse()
        caller.index(nodes)
        with self.assertRaisesRegex(Error,'ligne empruntée en lecture'):
            caller.block('root',nodes)

    def test_returned_inline_row_projection_updates_only_its_actual_slots(self):
        program='''
            fn line(g:&mut [[&Int;1];2])->&mut [&Int;1]{return &mut g[1];}
            fn update(g:&mut [[&Int;1];2],d:&Int){let mut r=line(g);r[0]=d;}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(2);
                let a=new(p)Int(1);let b=new(q)Int(2);let c=new(q)Int(3);
                let mut g=[[&a],[&b]];update(&mut g,&c);
                print(*g[0][0]);p.reset();print(*g[1][0]);
            }
        '''
        self.execute(program,[1,3],trace='destroy a=1\nreclaim a\nreset\ndestroy c=3\nreclaim c\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('print(*g[0][0]);p.reset();','p.reset();print(*g[0][0]);'))
        self.reject(program.replace('p.reset()', 'q.reset()'))

    def test_transferred_outer_container_preserves_writes_to_parent_rows(self):
        program='''
            fn consume(mut v: -> [&mut [&Int;1];1],other:&mut [&Int;1],d:&Int){
                v[0][0]=d;v[0]=other;
            }
            fn relay(v: -> [&mut [&Int;1];1],other:&mut [&Int;1],d:&Int){consume(->v,other,d);}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(2);
                let a=new(p)Int(1);let b=new(q)Int(2);let c=new(q)Int(3);
                let mut ra=[&a];let mut rb=[&b];let v=[&mut ra];
                relay(->v,&mut rb,&c);p.reset();print(*ra[0]);print(*rb[0]);
            }
        '''
        self.execute(program,[3,2],trace='destroy a=1\nreclaim a\nreset\ndestroy c=3\nreclaim c\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))
        self.reject(program.replace('p.reset()', 'drop(-> c)'))

    def test_temporary_outer_argument_preserves_injected_row_effects(self):
        program='''
            fn consume(v: -> [&mut [&Int;1];1],d:&Int){v[0][0]=d;}
            fn main(){
                let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let a=new(p)Int(1);let b=new(q)Int(2);let mut row=[&a];
                consume(-> [&mut row],&b);p.reset();print(*row[0]);
            }
        '''
        self.execute(program,[2],trace='destroy a=1\nreclaim a\nreset\ndestroy b=2\nreclaim b\n')
        self.reject(program.replace('p.reset()', 'q.reset()'))
