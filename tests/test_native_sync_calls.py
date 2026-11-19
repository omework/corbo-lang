"""Synchronous contracts and C calls used by native/async states."""
from pathlib import Path
import unittest
from unittest.mock import patch

from crust import Compiler, Error, Parser, compile_source, verify_program
import test_native_blocks as native_tests


class NativeSyncCallTests(unittest.TestCase):
    run_c_oracle = native_tests.NativeBlockTests.run_c_oracle
    run_native = native_tests.NativeBlockTests.run_native
    assert_destroyed = native_tests.NativeBlockTests.assert_destroyed
    wrap = staticmethod(native_tests.NativeBlockTests.wrap)

    def test_recorded_minimal_helper(self):
        source = (Path(__file__).resolve().parents[1] / 'validation/open-native-sync-helper.crb').read_text()
        self.assertEqual(self.run_native(source).stdout, '8\n')

    def test_nested_calls_preserve_argument_and_cleanup_order(self):
        declarations = '''
          fn item(n:Int)->Int{print(n);return n;}
          fn pair(a:Int,b:Int)->Int{print(30);return a*10+b;}
          fn leaf(n:Int)->Int{
            let mut p=pool<Int>(1);let a=p.new(n);let vue=&a;
            let value=*vue;drop(->a);let b=p.new(value+1);return *b;
          }
          fn relay(n:Int)->Int{return leaf(n)+1;}
          fn observe(n:Int){print(n);}
        '''
        for asynchronous in (False, True):
            body = 'let n=pair(item(1),item(2));observe(n);return relay(n);'
            source = declarations + ('''async fn work()->Int{BODY}
                fn main(){let h=runtime::spawn(->work());
                match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
                if asynchronous else '''fn main(){let h=runtime::thread({BODY});
                match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}''').replace('BODY', body)
            with self.subTest(asynchronous=asynchronous):
                run = self.run_native(source)
                self.assertEqual(run.stdout, '1\n2\n30\n12\n14\n')
                self.assert_destroyed(run, [12,13])

    def test_helper_local_borrow_contracts_drop_and_source_lifetime(self):
        template = '''
          fn read(v:&Int)->Int{return *v;}
          fn helper(n:Int)->Int{let mut p=pool<Int>(1);let a=p.new(n);
            let vue=&a;BEFORE let result=read(vue);AFTER return result;}
          fn main(){let h=runtime::thread({return helper(7);});
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}
        '''
        source = template.replace('BEFORE','').replace('AFTER','drop(->a);')
        run = self.run_native(source)
        self.assertEqual(run.stdout,'7\n')
        self.assert_destroyed(run,[7])
        for before,after in [('drop(->a);',''),('', 'drop(->a);print(vue);'),('', 'p.reset();')]:
            with self.subTest(before=before,after=after),self.assertRaises(Error):
                verify_program(template.replace('BEFORE',before).replace('AFTER',after))

    def test_byte_char_and_explicit_conversion(self):
        source = '''fn byte(b:u8)->u8{return b;}
          fn character(c:char)->char{return c;}
          fn main(){let h=runtime::thread({
            let a:u8=7;let b=byte(a);print(b as Int);
            let result="é".char_at(0);
            match result{Ok(c)=>{print(character(c));},Err(_)=>{print(99);}}
            return byte(8);
          });match h.join(){Ok(v)=>{print(v as Int);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout,'7\né\n8\n')
        for old,new in [('byte(a)','byte(256)'),('byte(a)','byte(true)'),
                        ('byte(a)','byte(1,2)'),('byte(a)','byte(&a)'),
                        ('print(b as Int)','print(byte(a))')]:
            with self.subTest(new=new),self.assertRaises(Error):
                verify_program(source.replace(old,new))

    def test_captured_allocation_read_by_value_stays_reserved_until_wait(self):
        template = '''fn add(n:Int)->Int{return n+1;}
          fn main(){let mut p=pool<Int>(1);let mut a=p.new(7);let vue=&mut a;
            let h=runtime::thread({->(vue);return add(*vue);});BEFORE
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}
            a=9;print(a);drop(->a);}'''
        self.assertEqual(self.run_native(template.replace('BEFORE','')).stdout,'8\n9\n')
        for conflict in ('print(a);','a=2;','drop(->a);','print(vue);'):
            with self.subTest(conflict=conflict),self.assertRaises(Error):
                verify_program(template.replace('BEFORE',conflict))

    def test_transitive_join_allowed_in_native_refused_in_async(self):
        declarations = '''async fn child(n:Int)->Int{yield;return n;}
          fn wait(n:Int)->Int{let h=runtime::spawn(->child(n));
            match h.join(){Ok(v)=>{return v;},Err(_)=>{return 90;}}}
          fn relay(n:Int)->Int{return wait(n);}
        '''
        source = declarations + '''fn main(){let h=runtime::thread({return relay(7);});
          match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout,'7\n')
        self.assertEqual(self.run_native(source,fail_at=2).stdout,'90\n')
        self.assertEqual(self.run_native(source,fail_at=1).stdout,'99\n')
        for fn in ('wait','relay'):
            invalid = declarations + 'async fn work()->Int{return '+fn+'(7);}'
            with self.subTest(fn=fn),self.assertRaisesRegex(Error,'join réservé.*auxiliaires'):
                verify_program(invalid)
        with self.assertRaisesRegex(Error,'attente requise|join requis'):
            verify_program(source.replace('match h.join(){Ok(v)=>{return v;},Err(_)=>{return 90;}}','return 7;'))

    def test_indirect_state_slots_count_for_each_live_parent(self):
        source = '''async fn child(n:Int)->Int{yield;return n;}
          fn helper(n:Int)->Int{
            let a=runtime::spawn(->child(n));let b=runtime::spawn(->child(n+1));
            let c=runtime::spawn(->child(n+2));
            let x=match a.join(){Ok(v)=>{v},Err(_)=>{90}};
            let y=match b.join(){Ok(v)=>{v},Err(_)=>{90}};
            let z=match c.join(){Ok(v)=>{v},Err(_)=>{90}};return x+y+z;
          }
          fn relay(n:Int)->Int{return helper(n);}
        '''
        # Eight retained parents can each hold three child handles. Keeping
        # only two parents let unrelated conservative counts hide a missing
        # per-frame contribution (the first mutation run exposed that gap).
        source += 'fn main(){' + ''.join(
            f'let h{i}=runtime::thread({{return relay({i});}});' for i in range(8))
        source += ''.join(
            f'match h{i}.join(){{Ok(v)=>{{print(v);}},Err(_)=>{{print(99);}}}}' for i in range(8)) + '}'
        compiler=Compiler()
        compiler.compile(Parser(source).parse())
        self.assertGreaterEqual(compiler.async_pool_capacities['child'],24)
        self.assertEqual(self.run_native(source).stdout,''.join(f'{3*i+3}\n' for i in range(8)))

    def test_helper_task_creation_without_join_is_not_a_blocking_effect(self):
        source='''async fn child(n:Int)->Int{yield;return n;}
          fn helper(n:Int)->Int{let task=child(n);drop(->task);return n+1;}
          async fn run()->Int{return helper(7);}
          fn main(){let h=runtime::spawn(->run());
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout,'8\n')

    def test_hidden_creation_cycle_needs_explicit_capacity(self):
        source='''async fn recur(n:Int)->Int{return helper(n);}
          fn helper(n:Int)->Int{let t=recur(n);drop(->t);return n;}
          fn main(){let h=runtime::spawn(->recur(7));
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        with self.assertRaisesRegex(Error,'async_pool_sizes requis.*'):
            verify_program(source)
        self.assertEqual(self.run_native('#(directive, async_pool_sizes={recur:2})'+source).stdout,'7\n')

    def test_argument_return_leaves_caller_without_invoking_helper(self):
        source='''fn first()->Int{print(1);return 3;}
          fn pair(a:Int,b:Int)->Int{print(99);return a+b;}
          fn main(){let h=runtime::thread({return pair(first(),{return 7;});});
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(90);}}}'''
        self.assertEqual(self.run_native(source).stdout,'1\n7\n')

    def test_local_method_creation_is_included_in_capacity_graph(self):
        source='''struct Maker{n:Int}
          impl Maker{fn make(self:&Maker)->Int{
            let task=child(self.n);drop(->task);return self.n;}}
          async fn child(n:Int)->Int{return helper(n);}
          fn helper(n:Int)->Int{let m=Maker{n:n};return m.make();}
          fn main(){let h=runtime::spawn(->child(7));
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        with self.assertRaisesRegex(Error,'async_pool_sizes requis'):
            verify_program(source)
        self.assertEqual(self.run_native('#(directive, async_pool_sizes={child:2})'+source).stdout,'7\n')

    def test_check_uses_contracts_without_emitting_synchronous_callees(self):
        source='''fn add(n:Int)->Int{return n+1;}
          fn relay(n:Int)->Int{return add(n);}
          fn main(){let h=runtime::thread({return relay(1)+relay(2);});
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        visits=[]
        original=Compiler.block
        def track(check,*args,**kwargs):
            if args and args[0].startswith('appel '):
                visits.append((args[0],tuple(check.call_stack)))
            return original(check,*args,**kwargs)
        with patch.object(Compiler,'block',track), patch.object(
                Compiler,'emit_async_sync_bridge',side_effect=AssertionError('backend reached during check')):
            checked=verify_program(source)
        self.assertEqual(visits,[('appel add',('add',)),('appel relay',('relay',)),('appel main',('main',))])
        self.assertEqual(checked.definitions,[])
        self.assertEqual(checked.body_call_contracts['relay'],('add',))


if __name__ == '__main__':
    unittest.main()
