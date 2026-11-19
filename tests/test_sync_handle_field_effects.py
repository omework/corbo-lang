"""Opaque synchronous wait/forward contracts preserve deferred field writes."""
import unittest
from itertools import product
from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_field_application as application

BASE=application.BASE
HELPERS=BASE+'''fn finish(h:->runtime::Handle<Int>)->Int{
    return match h.join(){Ok(n)=>{n},Err(_)=>{0}};}
  fn relay(h:->runtime::Handle<Int>)->Int{return finish(->h);}
  fn forward(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
'''


class SyncHandleFieldEffectsTests(unittest.TestCase):
    run_native=application.AsyncFieldApplicationTests.run_native
    run_c_oracle=application.AsyncFieldApplicationTests.run_c_oracle
    refused=application.AsyncFieldApplicationTests.refused
    program=staticmethod(application.AsyncFieldApplicationTests.program)

    def test_wait_and_forward_across_three_calls(self):
        source=self.program('''let h=runtime::spawn(->update(&mut v,&b));
          let next=forward(->h);print(relay(->next));BEFORE print(*v.data);''',HELPERS)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        for op in ('drop(->b);','b=20;','drop(->a);'):
            self.refused(source.replace('BEFORE',op))
        self.assertEqual(self.run_native(source.replace('BEFORE',''),fail_submission_at=1).stdout,'11\n0\n7\n')
        checker=verify_program(source.replace('BEFORE',''))
        self.assertEqual(checker.function_results['relay'].task_wait_parameters,frozenset({0}))
        self.assertEqual(checker.function_results['forward'].task_forward_parameters,frozenset({0}))
        self.assertEqual(checker.function_results['forward'].task_wait_parameters,frozenset())

    def test_inactive_forward_launch_and_discard(self):
        helpers=HELPERS+'''fn pass(t:->update)-><-update{return <-t;}
          fn start(t:->update)-><-runtime::Handle<Int>{let h=runtime::spawn(->t);return <-h;}
          fn discard(t:->update){drop(->t);}'''
        source=self.program('''let t=update(&mut v,&b);let next=pass(->t);
          let h=start(->next);print(finish(->h));BEFORE print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(source.replace('BEFORE','drop(->b);'))
        inactive=self.program('''let t=update(&mut v,&b);let next=pass(->t);
          discard(->next);drop(->b);let replacement=p.new(19);print(replacement);print(*v.data);''',helpers)
        self.assertEqual(self.run_native(inactive).stdout,'11\n19\n7\n')

    def test_conditional_and_loop_forwarding(self):
        helpers=HELPERS+'''fn branch(h:->runtime::Handle<Int>,flag:bool)-><-runtime::Handle<Int>{
            if flag{return <-h;}let next=forward(->h);return <-next;}
          fn cycling(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{
            let result=loop{h ->;break <-h;};return <-result;}'''
        for flag in ('true','false'):
            source=self.program('''let h=runtime::spawn(->update(&mut v,&b));
              let next=branch(->h,'''+flag+''');let last=cycling(->next);
              print(finish(->last));BEFORE print(*v.data);''',helpers)
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
                self.refused(source.replace('BEFORE','drop(->b);'))

    def test_opaque_caller_uses_only_synchronous_contracts(self):
        interface=verify_program(HELPERS)
        def caller(operation):
            checker=Compiler()
            checker.contract_calls=True
            checker.function_contracts=interface.function_contracts
            checker.async_definitions=interface.async_definitions.copy()
            checker.enums=interface.enums.copy()
            checker.struct_fields=interface.struct_fields.copy()
            script='''let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
              let mut v=View{data:&a};let h:runtime::Handle<Int>=runtime::spawn(->update(&mut v,&b));
              let next=forward(->h);print(relay(->next));'''+operation+'print(*v.data);'
            nodes=Parser('struct View{data:&Int}'+script).parse()[1:]
            checker.index(nodes)
            checker.block('root',nodes)
            return checker
        checked=caller('')
        self.assertEqual(checked.contract_call_log,['forward','relay'])
        self.assertEqual(checked.functions,{})
        self.assertEqual(checked.function_results,{})
        self.assertEqual(checked.definitions,[])
        with self.assertRaisesRegex(Error,'emprunt'):
            caller('drop(->b);')

    def test_legacy_reset_after_wait_still_protects_external_carrier(self):
        source=HELPERS+'''fn clear(h:->runtime::Handle<Int>,q:&mut Pool<Int>)->Int{
          let n=finish(->h);q.reset();return n;}
          fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
            let a=p.new(7);let b=q.new(9);let mut v=View{data:&a};
            let h=runtime::spawn(->update(&mut v,&b));print(clear(->h,&mut q));print(*v.data);}'''
        self.refused(source,'reset interdit|emprunt',legacy=True)
        safe=source.replace('print(clear(->h,&mut q));print(*v.data);',
                            'print(finish(->h));print(*v.data);drop(->v);q.reset();let next=q.new(19);print(next);')
        self.assertEqual(self.run_c_oracle(compile_source(safe,allow_legacy_reset=True)).stdout,'9\n9\n19\n')

    def test_two_handles_waited_or_returned_by_path(self):
        helpers=HELPERS+'''fn choose(a:->runtime::Handle<Int>,b:->runtime::Handle<Int>,flag:bool)-><-runtime::Handle<Int>{
          if flag{a ->;b ->;print(finish(->a));return <-b;}print(finish(->b));return <-a;}'''
        for flag in ('true','false'):
            source=helpers+'''fn main(){let mut p=pool<Int>(4);
              let a=p.new(1);let b=p.new(2);let c=p.new(3);let d=p.new(4);
              let mut left=View{data:&a};let mut right=View{data:&c};
              let one=runtime::spawn(->update(&mut left,&b));
              let two=runtime::spawn(->update(&mut right,&d));
              let pending=choose(->one,->two,'''+flag+''');print(finish(->pending));
              BEFORE print(*left.data);print(*right.data);}'''
            with self.subTest(flag=flag):
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,
                                 ('2\n4\n' if flag=='true' else '4\n2\n')+'2\n4\n')
                for target in ('b','d'):
                    self.refused(source.replace('BEFORE',f'drop(->{target});'))

    def test_independent_opaque_wait_retention_model(self):
        helpers=HELPERS+'fn discard(t:->update){drop(->t);}'
        accepted=rejected=0
        for inactive,dead,target in product((False,True),(False,True),('a','b')):
            retained=set() if dead else {'a'} if inactive else {'a','b'}
            completion=('let t=update(&mut v,&b);discard(->t);' if inactive else
                        'let h=runtime::spawn(->update(&mut v,&b));let next=forward(->h);print(relay(->next));')
            source=self.program(completion+('drop(->v);' if dead else '')+
                                f'drop(->{target});'+('' if dead else 'print(*v.data);'),helpers)
            with self.subTest(inactive=inactive,dead=dead,target=target):
                if target in retained:
                    self.refused(source)
                    rejected+=1
                else:
                    self.assertEqual(self.run_native(source).stdout,'11\n'+('' if inactive else '9\n')+
                                     ('' if dead else '7\n' if inactive else '9\n'))
                    accepted+=1
        self.assertEqual((accepted,rejected),(5,3))


if __name__=='__main__':unittest.main()
