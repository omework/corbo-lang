"""Boolean synchronous contracts crossing async and native state boundaries."""
import unittest
from unittest.mock import patch

from crust import Compiler, Error, verify_program
import test_native_blocks as native


class SyncBoolCallTests(unittest.TestCase):
    run_c_oracle = native.NativeBlockTests.run_c_oracle
    run_native = native.NativeBlockTests.run_native
    assert_destroyed = native.NativeBlockTests.assert_destroyed

    declarations = '''fn flag(b:bool)->bool{return b;}
      fn mark(n:Int,b:bool)->bool{print(n);return b;}
      fn both(a:bool,b:bool)->bool{return a && b;}
      fn integer(n:Int)->Int{return n;}'''

    @classmethod
    def program(cls, body, *, native_block=False, result='Bool', declarations=''):
        work = '' if native_block else 'async fn work()->'+result+'{'+body+'}'
        start = 'runtime::thread({'+body+'})' if native_block else 'runtime::spawn(->work())'
        display = 'if v{print(1);}else{print(0);}' if result == 'Bool' else 'print(v);'
        return cls.declarations+declarations+work+'fn main(){let h='+start+''';
          match h.join(){Ok(v)=>{DISPLAY},Err(_)=>{print(99);}}}'''.replace('DISPLAY',display)

    def test_truth_table_matches_independent_python_model(self):
        for native_block in (False, True):
            for left in (False, True):
                for right in (False, True):
                    with self.subTest(native=native_block,left=left,right=right):
                        body=f'return both(flag({str(left).lower()}),flag({str(right).lower()}));'
                        self.assertEqual(self.run_native(self.program(body,native_block=native_block)).stdout,
                                         f'{int(left and right)}\n')

    def test_named_annotated_mutated_and_native_captured_bool(self):
        body='''let mut b:Bool=flag(false);b=flag(true);
          let h=runtime::thread({->(b);return flag(b);});
          match h.WAIT{Ok(v)=>{return flag(v);},Err(_)=>{return false;}}'''
        for native_block in (False, True):
            with self.subTest(native=native_block):
                source=self.program(body.replace('WAIT','join()' if native_block else 'await'),native_block=native_block)
                self.assertEqual(self.run_native(source).stdout,'1\n')

    def test_conditions_short_circuit_and_argument_order(self):
        body='''if mark(1,false) && mark(2,true){print(20);}
          if mark(3,true) || mark(4,false){print(30);}
          let n=if both(mark(5,true),mark(6,false)){10}else{11};
          print(n);return flag(true);'''
        for native_block in (False, True):
            with self.subTest(native=native_block):
                run=self.run_native(self.program(body,native_block=native_block))
                self.assertEqual(run.stdout,'1\n3\n30\n5\n6\n11\n1\n')

    def test_bool_does_not_coerce_to_int_or_byte(self):
        for body in ('return integer(flag(true));','return flag(1);',
                     'let n:Int=flag(true);return true;',
                     'let b:Bool=integer(1);return b;',
                     'let b:u8=flag(true);return true;',
                     'return flag(true)+1;', 'if flag(true)<false{return true;}return false;'):
            with self.subTest(body=body), self.assertRaises(Error):
                verify_program(self.program(body))
        for declarations in ('fn wrong()->bool{return 1;}',
                             'fn wrong(b:bool)->Int{return b;}'):
            with self.subTest(declarations=declarations),self.assertRaises(Error):
                verify_program(self.program('return true;',declarations=declarations))

    def test_bool_call_can_feed_child_and_suspend_in_later_argument(self):
        declarations='async fn child(b:Bool)->Bool{yield;return b;}'
        body='''let task=child(flag(true));
          return both(mark(1,true),task.await);'''
        self.assertEqual(self.run_native(self.program(body,declarations=declarations)).stdout,'1\n1\n')

    def test_loan_ends_before_owner_transfer_and_bool_has_no_provenance(self):
        declarations='''fn positive(a:&Int)->bool{return *a>0;}
          fn consume(b:bool,a:->Int)->bool{print(a);return b;}
          async fn work(a:->Int)->Bool{
            let view=&a;return consume(positive(view),->a);
          }'''
        main='''fn main(){let mut p=pool<Int>(1);let a=p.new(7);
          let h=runtime::spawn(->work(->a));
          match h.join(){Ok(v)=>{if v{print(1);}},Err(_)=>{}}
          let b=p.new(9);drop(->b);}'''
        run=self.run_native(declarations+main)
        self.assertEqual(run.stdout,'7\n1\n');self.assert_destroyed(run,[7,9])
        invalid=declarations.replace('return consume(positive(view),->a);',
          'let result=consume(positive(view),->a);print(*view);return result;')+main
        with self.assertRaisesRegex(Error,'emprunt|utilis|réserv'):
            verify_program(invalid)
        # A copied boolean result can outlive the input's pool after join.
        independent='''fn positive(a:&Int)->bool{return *a>0;}
          async fn work(a:&Int)->Bool{yield;return positive(a);}
          fn main(){let result={let mut p=pool<Int>(1);let a=p.new(7);
            let h=runtime::spawn(->work(&a));
            let b=match h.join(){Ok(v)=>{v},Err(_)=>{false}};drop(->a);b};
            if result{print(1);}else{print(0);}}'''
        run=self.run_native(independent)
        self.assertEqual(run.stdout,'1\n');self.assert_destroyed(run,[7])

    def test_prepared_owner_cleanup_on_bool_argument_return(self):
        source='''fn take(a:->Int,b:bool)->bool{print(99);print(a);return b;}
          async fn work(a:->Int)->Bool{
            return take(->a,{yield;return true;});
          }
          fn main(){let mut p=pool<Int>(1);let a=p.new(7);
            let h=runtime::spawn(->work(->a));
            match h.join(){Ok(v)=>{if v{print(1);}},Err(_)=>{}}
            let b=p.new(9);drop(->b);}'''
        run=self.run_native(source)
        self.assertEqual(run.stdout,'1\n');self.assert_destroyed(run,[7,9])
        for forbidden in ('drop(->a);','p.reset();'):
            with self.subTest(forbidden=forbidden),self.assertRaises(Error):
                verify_program(source.replace('let h=runtime::spawn(->work(->a));',
                  'let h=runtime::spawn(->work(->a));'+forbidden))

    def test_verification_uses_contract_without_emitting_bridge(self):
        with patch.object(Compiler,'emit_async_sync_bridge',side_effect=AssertionError('codegen during verify')):
            verify_program(self.program('return flag(true);'))

    def test_mutable_argument_reservation_and_snapshot(self):
        declarations='''fn positive(a:&Int)->bool{return *a>0;}
          fn update(b:bool,a:&mut Int)->bool{a.set(0);return b;}
          fn conflict(a:&mut Int,b:bool)->bool{a.set(0);return b;}
          async fn work(mut a:->Int)->Bool{
            let result=update(positive(&a),&mut a);print(*a);return result;
          }'''
        main='''fn main(){let mut p=pool<Int>(1);let a=p.new(7);
          let h=runtime::spawn(->work(->a));
          match h.join(){Ok(b)=>{if b{print(1);}},Err(_)=>{}}}'''
        run=self.run_native(declarations+main)
        self.assertEqual(run.stdout,'0\n1\n');self.assert_destroyed(run,[0])
        with self.assertRaisesRegex(Error,'emprunt|réserv|alias'):
            verify_program(declarations.replace('update(positive(&a),&mut a)',
              'conflict(&mut a,positive(&a))')+main)

    def test_primitive_block_result_materialized_before_pool_closes(self):
        source='''fn number()->Int{return {let mut p=pool<Int>(1);let a=p.new(17);*a};}
          fn truth()->bool{return {let mut p=pool<Int>(1);let a=p.new(18);*a>0};}
          fn octet()->u8{return {let b:u8=19;b};}
          fn main(){print(number());if truth(){print(1);}print(octet() as Int);
            let parsed="é".char_at(0);match parsed{Ok(c)=>{let value={c};print(value);},Err(_)=>{}}}'''
        run=self.run_native(source)
        self.assertEqual(run.stdout,'17\n1\n19\né\n');self.assert_destroyed(run,[17,18])
        # Copying the payload does not relax the borrow's own lifetime rules.
        for replacement in ('let view=&a;drop(->a);*view',
                            'let view=&a;return view;', 'a'):
            with self.subTest(replacement=replacement),self.assertRaises(Error):
                verify_program(source.replace('let a=p.new(17);*a', 'let a=p.new(17);'+replacement))


if __name__ == '__main__':
    unittest.main()
