"""Captured Int references preserve existing allocation descriptors across tasks."""
from itertools import product
import unittest

from crust import Error, compile_source, verify_program
import test_cell_reference_bridges as bridges


class CapturedCellDescriptorTests(unittest.TestCase):
    run_native = bridges.CellReferenceBridgeTests.run_native
    run_c_oracle = bridges.CellReferenceBridgeTests.run_c_oracle
    program = staticmethod(bridges.CellReferenceBridgeTests.program)

    def refused(self, source, pattern='emprunt|réserv|descripteur|plus utilisable', legacy=False):
        for stage in (verify_program, compile_source):
            with self.subTest(stage=stage.__name__):
                with self.assertRaisesRegex(Error, pattern) as caught:
                    stage(source, allow_legacy_reset=legacy)
                self.assertNotIn('invariant interne', str(caught.exception))

    def test_captured_cell_and_mutable_cell(self):
        for mode, call, value in (('&', 'forward(n)', 7), ('&mut ', 'edit(n,12)', 12)):
            source = self.program('yield;return '+call+';', parameters='n:'+mode+'Int',
                argument=mode+'n', setup='let mut p=pool<Int>(1);let mut n=p.new(7);')
            compiler = verify_program(source)
            self.assertEqual(compiler.async_definitions['work'][0].cell_reference_parameters, {0})
            result = self.run_native(source)
            self.assertEqual(result.stdout, str(value)+'\n')
            self.assertEqual(result.stderr.count(f'destroy n={value}\n'), 1)
            failed = self.run_native(source, fail_at=1)
            self.assertEqual(failed.stdout, '99\n')
            self.assertEqual(failed.stderr.count('destroy n=7\n'), 1)

    def test_address_identity_through_reborrow_and_suspension(self):
        helpers = bridges.HELPERS + '''fn identity(n:&Int)->Int{
          address(n);let v=View{data:&*n};return *v.data;}'''
        source = self.program('let a=&*n;let x=identity(a);yield;return identity(n)+x;',
            helpers=helpers, parameters='n:&Int', argument='&n',
            setup='let mut p=pool<Int>(1);let n=p.new(7);address(n);')
        result = self.run_native(source)
        original, first, second, value = result.stdout.splitlines()
        self.assertEqual((first, second, value), (original, original, '14'))

    def test_requirements_reach_fixed_point_independent_of_declaration_order(self):
        chain = [f'async fn level{i}(n:&Int)->Int{{yield;return '+
                 (f'level{i+1}(n).await;' if i < 4 else 'forward(n);')+'}' for i in range(5)]
        for declarations in (chain, chain[::-1]):
            source = self.program('yield;return level0(n).await;',
                helpers=bridges.HELPERS+''.join(declarations), parameters='n:&Int', argument='&n',
                setup='let mut p=pool<Int>(1);let n=p.new(7);')
            compiler = verify_program(source)
            for name in ('work', *(f'level{i}' for i in range(5))):
                self.assertEqual(compiler.async_definitions[name][0].cell_reference_parameters, {0})
            self.assertEqual(self.run_native(source).stdout, '7\n')

    def test_only_required_nonfirst_capture_gets_descriptor(self):
        source = self.program('yield;return x+forward(b)+read_only(a);',
            parameters='x:Int,a:&Int,b:&Int', argument='3,&a,&b',
            setup='let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);')
        compiler = verify_program(source)
        self.assertEqual(compiler.async_definitions['work'][0].cell_reference_parameters, {2})
        self.assertEqual(self.run_native(source).stdout, '19\n')

    def test_recursive_capture_with_explicit_frame_capacity(self):
        source = '#(directive, async_pool_sizes={rec:4})'+bridges.HELPERS+'''
          async fn rec(n:&Int,count:Int)->Int{
            if count>0{return rec(n,count-1).await;}yield;return forward(n);}
          fn main(){let mut p=pool<Int>(1);let n=p.new(7);
            let h=runtime::spawn(->rec(&n,3));
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        result = self.run_native(source)
        self.assertEqual(result.stdout, '7\n')
        self.assertEqual(result.stderr.count('destroy n=7\n'), 1)

    def test_child_selects_real_cell_from_multiple_captured_targets(self):
        helpers = bridges.HELPERS+'async fn leaf(n:&Int)->Int{yield;return forward(n);}'
        for flag in ('true','false'):
            source = self.program('let selected=if flag{&*a}else{&*b};return leaf(selected).await;',
                helpers=helpers, parameters='flag:Bool,a:&Int,b:&Int', argument=flag+',&a,&b',
                setup='let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);')
            self.assertEqual(self.run_native(source).stdout, '7\n' if flag=='true' else '9\n')

    def test_synchronous_factory_and_relay_keep_requirements(self):
        helpers = bridges.HELPERS+'''async fn leaf(n:&Int)->Int{yield;return forward(n);}
          fn make(n:&Int)-><-runtime::Handle<Int>{let h=runtime::spawn(->leaf(n));return <-h;}
          fn relay(n:&Int)-><-runtime::Handle<Int>{let h=make(n);return <-h;}'''
        source = self.program('let h=relay(n);yield;match h.await{Ok(v)=>{return v;},Err(_)=>{return 88;}}',
            helpers=helpers, parameters='n:&Int', argument='&n',
            setup='let mut p=pool<Int>(1);let n=p.new(7);')
        compiler = verify_program(source)
        for name in ('make','relay'):
            self.assertEqual(compiler.function_results[name].stored_reference_parameters, frozenset({0}))
        self.assertEqual(self.run_native(source).stdout, '7\n')
        self.assertEqual(self.run_native(source, fail_submission_at=2).stdout, '88\n')

    def test_native_block_capture_uses_same_descriptor(self):
        source = bridges.HELPERS+'''fn main(){let mut p=pool<Int>(1);let n=p.new(7);
          let r=&n;let h=runtime::thread({->(r);return forward(r);});
          match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout, '7\n')
        self.assertEqual(self.run_native(source, fail_native=True).stdout, '99\n')

    def test_inactive_task_cleanup_then_pool_slot_reuse(self):
        source = bridges.HELPERS+'''async fn work(n:&Int)->Int{yield;return forward(n);}
          fn main(){let mut p=pool<Int>(1);let n=p.new(7);
            let task=work(&n);drop(->task);drop(->n);
            let replacement=p.new(9);print(replacement);}'''
        result = self.run_native(source)
        self.assertEqual(result.stdout, '9\n')
        self.assertEqual(result.stderr.count('destroy n=7\n'), 1)
        self.assertFalse(any(line.endswith('=View') for line in result.stderr.splitlines()))

    def test_inline_sources_remain_explicit_backend_gap(self):
        for setup, argument in (('let a=[7];', '&a[0]'), ('let a=[[7]];', '&a[0][0]')):
            source = self.program('return forward(n);',parameters='n:&Int',argument=argument,setup=setup)
            self.refused(source, 'descripteur')

    def test_retained_reference_model_across_join_drop_and_legacy_reset(self):
        # After join, a scalar no longer retains its target; a reference does
        # until its last use. Before join the running capture always retains it.
        accepted = rejected = 0
        for borrowed, before_join, operation in product((False, True), repeat=3):
            result_type = '&Int' if borrowed else 'Int'
            helper = 'detach' if borrowed else 'forward'
            release = 'p.reset();' if operation else 'drop(->n);'
            source = bridges.HELPERS+f'''async fn work(n:&Int)->{result_type}{{yield;return {helper}(n);}}
              fn main(){{let mut p=pool<Int>(1);let n=p.new(7);
                let h=runtime::spawn(->work(&n));BEFORE
                let result=h.join();AFTER
                match result{{Ok(v)=>{{print(v);}},Err(_)=>{{print(99);}}}}}}'''
            source = source.replace('BEFORE',release if before_join else '').replace('AFTER','' if before_join else release)
            allowed = not before_join and not borrowed
            with self.subTest(borrowed=borrowed,before_join=before_join,reset=operation):
                if allowed:
                    self.assertEqual(self.run_c_oracle(compile_source(source,allow_legacy_reset=True)).stdout,'7\n')
                    accepted += 1
                else:
                    self.refused(source,pattern='reset interdit' if operation else 'emprunt|réserv|plus utilisable',legacy=True)
                    rejected += 1
        self.assertEqual((accepted,rejected),(2,6))

    def test_result_last_use_releases_target_before_drop(self):
        source = bridges.HELPERS+'''async fn work(n:&Int)->&Int{yield;return detach(n);}
          fn main(){let mut p=pool<Int>(1);let n=p.new(7);let h=runtime::spawn(->work(&n));
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}drop(->n);let b=p.new(9);print(b);}'''
        self.assertEqual(self.run_native(source).stdout,'7\n9\n')

    def test_mutable_return_keeps_target_reserved_until_last_use(self):
        source = bridges.HELPERS+'''fn reedit(n:&mut Int)->&mut Int{
            {let mut w=Writer{data:&mut *n};let mut target=&mut *w.data;target.set(8);}
            return n;}
          async fn work(n:&mut Int)->&mut Int{let mut view=reedit(n);yield;return view;}
          fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);
            let h=runtime::spawn(->work(&mut n));BEFORE
            match h.join(){Ok(v)=>{DURING v.set(12);print(v);},Err(_)=>{print(99);}}
            n.set(19);print(n);}'''
        valid = source.replace('BEFORE','').replace('DURING','')
        self.assertEqual(self.run_native(valid).stdout,'12\n19\n')
        self.refused(source.replace('BEFORE','print(n);').replace('DURING',''))
        self.refused(source.replace('BEFORE','').replace('DURING','print(n);'))
        # ST12 keeps the mutable field's carrier reserved. It cannot be local
        # to the returning helper even when the ultimate Int outlives it.
        invalid = valid.replace(
            '{let mut w=Writer{data:&mut *n};let mut target=&mut *w.data;target.set(8);}\n            return n;',
            'let mut w=Writer{data:&mut *n};return &mut *w.data;')
        self.assertNotEqual(invalid, valid)
        self.refused(invalid, 'non durable')


if __name__ == '__main__':
    unittest.main()
