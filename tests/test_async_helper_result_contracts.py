"""Result summaries cross sync helpers, suspended children and sync joins."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncHelperContractTests(unittest.TestCase):
    run_c_oracle=native.NativeBlockTests.run_c_oracle
    run_native=native.NativeBlockTests.run_native

    def refused(self,source):
        for check in (verify_program,compile_source):
            with self.subTest(stage=check.__name__):
                with self.assertRaises(Error):check(source)

    @staticmethod
    def program():
        return (Path(__file__).resolve().parents[1]/'validation/open-async-helper-result-sync-contract.crb').read_text()

    def test_recorded_contract_and_conflicts(self):
        source=self.program()
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n')
        for operation in ('print(*v.data);','print(data);','drop(->v);','drop(->data);'):
            self.refused(source.replace('v.right=8;',operation+'v.right=8;'))

    def test_definition_order_methods_and_async_relays(self):
        source=self.program()
        method='impl View{fn target(self:&mut View)->&mut Int{return &mut *self.data;}}'
        source=source.replace('fn target(v:&mut View)->&mut Int{return &mut *v.data;}',method)
        source=source.replace('return target(v);','return v.target();')
        source=source.replace('fn get(v:', 'async fn relay(v:&mut View)->&mut Int{yield;return leaf(v).await;}\nfn get(v:')
        source=source.replace('spawn(->leaf(v))','spawn(->relay(v))')
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n')
        source=source.replace(method,'')+'\n'+method
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n')
        self.refused(source.replace('v.right=8;','print(*v.data);v.right=8;'))

    def test_multiple_synchronous_relays_and_aliases(self):
        source=self.program().replace('return target(v);','let alias=&mut *v;return alias_target(alias);')
        source+='\nfn alias_target(v:&mut View)->&mut Int{return target(v);}'
        source=source.replace('fn main()', 'fn again(v:&mut View)->&mut Int{return get(v);}\nfn main()')
        source=source.replace('let r=get(&mut v);','let r=again(&mut v);')
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n')
        self.refused(source.replace('v.right=8;','drop(->v);v.right=8;'))

    def test_conditional_helper_preserves_both_paths(self):
        source=self.program()
        source=source.replace('return &mut *v.data;',
          'return if true {&mut v.left} else {&mut *v.data};',1)
        self.assertEqual(self.run_native(source).stdout,'21\n8\n7\n')
        for field in ('v.left','*v.data'):
            self.refused(source.replace('v.right=8;',f'print({field});v.right=8;'))

    def test_handle_factory_and_parameter_contract(self):
        source=self.program()
        source=source.replace('let h=runtime::spawn(->leaf(v));','let h=launch(v);')
        source+='''fn launch(v:&mut View)-><- Execution<leaf>{
          let h=runtime::spawn(->leaf(v));return <-h;}'''
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n')
        self.refused(source.replace('v.right=8;','print(*v.data);v.right=8;'))

    def test_finished_handle_parameter(self):
        source=self.program()
        source=source.replace('return match h.join(){Ok(n)=>{n},Err(_)=>{&mut *v.data}};',
          'return finish(->h,v);')
        source+='''fn finish(h:->Execution<leaf>,v:&mut View)->&mut Int{
          return match h.join(){Ok(n)=>{n},Err(_)=>{&mut *v.data}};}'''
        # v is captured by h; it cannot simultaneously be a mutable argument.
        self.refused(source)

        source=self.program().replace('return match h.join(){Ok(n)=>{n},Err(_)=>{&mut *v.data}};',
          'return finish(->h);')
        source+='''fn finish(h:->Execution<leaf>)->&mut Int{
          return match h.join(){Ok(n)=>{n},Err(_)=>{loop{}}};}'''
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n')
        self.refused(source.replace('v.right=8;','print(*v.data);v.right=8;'))

        inline=source.replace('return &mut *v.data;','return &mut v.left;',1)
        self.assertEqual(self.run_native(inline).stdout,'21\n8\n7\n')
        self.refused(inline.replace('v.right=8;','print(v.left);v.right=8;'))

    def test_invalid_helper_source_or_mode(self):
        for helper in ('let mut local=8;return &mut local;',
                       'return &v.left;', 'return &mut v.data;'):
            self.refused(self.program().replace('return &mut *v.data;',helper,1))
        # No fabricated summary is allowed to break a dependency cycle.
        self.refused(self.program().replace('return target(v);','return get(v);'))

    def test_launch_error_and_slot_reuse(self):
        source=self.program()
        self.assertEqual(self.run_native(source,fail_at=1).stdout,'21\n8\n21\n')
        source=source.replace('print(data);','drop(->v);print(data);drop(->data);let next=memory.new(77);print(next);')
        self.assertEqual(self.run_native(source).stdout,'21\n8\n21\n77\n')


if __name__=='__main__':unittest.main()
