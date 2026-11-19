"""V4/B4a: computed Int writes keep identity and respect RHS effects."""
import random
import unittest
from crust import Error,compile_source,verify_program
import test_async_runtime


class SetExpressionTests(unittest.TestCase):
    run_c_oracle=test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def native(self,source):
        verify_program(source)
        return self.run_c_oracle(compile_source(source))

    def refused(self,source,pattern='emprunt|capture|plus utilisable|libérée|immuable|lecture',**options):
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__),self.assertRaisesRegex(Error,pattern):check(source,**options)

    def test_calls_order_identity_and_last_borrow_use(self):
        source='''fn number(n:Int)->Int{print(n);return n;}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);address(n);
                let view=&n;n.set(*view+number(2)+number(3));address(n);print(*n);
                drop(->n);let replacement=p.new(99);address(replacement);print(*replacement);}'''
        run=self.native(source);lines=run.stdout.splitlines()
        self.assertEqual(lines[1:3],['2','3']);self.assertEqual(lines[4],'12')
        self.assertEqual(lines[0],lines[3]);self.assertEqual(lines[0],lines[5]);self.assertEqual(lines[6],'99')
        self.assertEqual(run.stderr.count('destroy n=12'),1)
        self.refused(source.replace('address(n);print(*n);','print(*view);address(n);print(*n);'))

    def test_named_mutable_reborrow_scalar_and_inline_target(self):
        source='''fn increment(v:&mut Int,delta:Int){v.set(*v+delta);}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);increment(&mut n,2);print(*n);
                let mut scalar=3;scalar.set(scalar*2);print(scalar);
                let mut values=[10,20];let writer=&mut values[0];writer.set(4+5);print(values[0]);}'''
        self.assertEqual(self.native(source).stdout,'9\n6\n9\n')
        for before,after in (('let mut scalar','let scalar'),('let writer=&mut','let writer=&'),
                             ('v:&mut Int','v:&Int')):
            self.refused(source.replace(before,after))
        source=source.replace('writer.set(4+5);','let view=&*writer;writer.set(4+5);print(*view);')
        self.refused(source)

    def test_rhs_drop_and_reset_cannot_invalidate_receiver(self):
        declarations='''fn consume(v:->Int)->Int{drop(->v);return 8;}
            fn clear(p:&mut Pool<Int>)->Int{p.reset();return 9;}'''
        main='''fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);OP print(*n);}'''
        self.refused(declarations+main.replace('OP','n.set(consume(->n));'),allow_legacy_reset=True)
        self.refused(declarations+main.replace('OP','n.set(clear(&mut p));'),
                     'reset|libérée|plus utilisable',allow_legacy_reset=True)
        good=declarations+main.replace('OP','let mut other=pool<Int>(1);n.set(clear(&mut other));')
        self.assertEqual(self.run_c_oracle(compile_source(good,allow_legacy_reset=True)).stdout,'9\n')

    def test_expression_branches_returns_and_types(self):
        source='''fn write(v:&mut Int,flag:bool){v.set(if flag{20}else{30});}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);write(&mut n,true);print(*n);
                write(&mut n,false);print(*n);n.set({let x=4;x+5});print(*n);}'''
        self.assertEqual(self.native(source).stdout,'20\n30\n9\n')
        base='fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);EXPR print(*n);}'
        for expression in ('n.set(true);','n.set("bad");','n.set(p.new(9));','n.set();','n.set(1,2);'):
            self.refused(base.replace('EXPR',expression),'set exige|Int32|type')

    def test_user_method_named_set_keeps_its_own_contract(self):
        source='''struct Point{x:Int}
            impl Point{fn set(self:&mut Point,v:Int){self.x=v+1;}}
            fn main(){let mut point=Point{x:7};point.set(2+3);print(point.x);}'''
        self.assertEqual(self.native(source).stdout,'6\n')
        self.refused(source.replace('point.set(2+3);','let view=&point;point.set(2+3);print(view.x);'))

    def test_independent_integer_sequence_model(self):
        for seed in (72,190,602):
            rng=random.Random(seed);value=7;steps=[];expected=[]
            for _ in range(12):
                amount=rng.randint(-9,9);factor=rng.randint(-2,2)
                value=value*factor+amount
                steps.append(f'n.set(*n*({factor})+({amount}));print(*n);')
                expected.append(str(value))
            source='fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);'+''.join(steps)+'}'
            with self.subTest(seed=seed):self.assertEqual(self.native(source).stdout,'\n'.join(expected)+'\n')

    def test_match_projection_and_sync_helper_from_async(self):
        source='''enum W{Bound{data:&mut Int}}
            fn edit(v:&mut Int){v.set(*v+2);}
            async fn work(v:&mut Int){yield;edit(v);}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);let mut holders=pool<W>(1);
                let mut w=new(holders) W.Bound{data:&mut n};
                match &mut w{W.Bound{data:r}=>{r.set(*r+3);}}
                print(w);drop(->w);let h=runtime::spawn(->work(&mut n));
                match h.join(){Ok(())=>{},Err(_)=>{}}print(*n);}'''
        self.assertEqual(self.native(source).stdout,'W.Bound(10)\n12\n')
        self.refused(source.replace('r.set(*r+3);','r.set(*r+3);print(*n);'))
        self.refused(source.replace('match &mut w','match &w'))

    def test_effects_inside_rhs_propagate_through_opaque_calls(self):
        declarations='''fn clear(p:&mut Pool<Int>)->Int{p.reset();return 9;}
            fn update(v:&mut Int,p:&mut Pool<Int>){v.set(clear(p));}
            fn relay(v:&mut Int,p:&mut Pool<Int>){update(v,p);}'''
        main='''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);let mut n=p.new(7);
            let other=q.new(12);CHECK relay(&mut n,&mut q);print(*n);AFTER}'''
        good=declarations+main.replace('CHECK','print(*other);').replace('AFTER','')
        self.assertEqual(self.run_c_oracle(compile_source(good,allow_legacy_reset=True)).stdout,'12\n9\n')
        bad=declarations+main.replace('CHECK','').replace('AFTER','print(*other);')
        self.refused(bad,'reset|libérée|plus utilisable',allow_legacy_reset=True)

    def test_rhs_early_return_skips_write(self):
        source='''fn update(v:&mut Int,flag:bool){v.set(if flag{*v+1}else{return;});print(*v);}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);update(&mut n,false);print(*n);
                update(&mut n,true);print(*n);}'''
        run=self.native(source)
        self.assertEqual(run.stdout,'7\n8\n8\n')
        self.assertEqual(run.stderr.count('destroy n=8'),1)

if __name__=='__main__':unittest.main()
