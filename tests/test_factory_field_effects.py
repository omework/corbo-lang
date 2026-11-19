"""Factories publish deferred field effects without retaining their bodies."""
import unittest
from itertools import product
from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_field_application as application

HELPERS=application.BASE+'''
 fn make(v:&mut View,n:&Int)-><-runtime::Handle<Int>{
   let h=runtime::spawn(->update(v,n));return <-h;}
 fn prepare(v:&mut View,n:&Int)-><-update{let t=update(v,n);return <-t;}
 fn relay(n:&Int,v:&mut View)-><-runtime::Handle<Int>{let h=make(v,n);return <-h;}
 fn finish(h:->runtime::Handle<Int>)->Int{
   return match h.join(){Ok(n)=>{n},Err(_)=>{0}};}
 fn complete(v:&mut View,n:&Int)->Int{let h=relay(n,v);return finish(->h);}
'''

class FactoryFieldEffectsTests(unittest.TestCase):
    run_native=application.AsyncFieldApplicationTests.run_native
    run_c_oracle=application.AsyncFieldApplicationTests.run_c_oracle
    refused=application.AsyncFieldApplicationTests.refused
    program=staticmethod(application.AsyncFieldApplicationTests.program)

    def test_factory_relay_and_wait(self):
        source=self.program('let h=relay(&b,&mut v);print(finish(->h));BEFORE print(*v.data);',HELPERS)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.assertEqual(self.run_native(source.replace('BEFORE',''),fail_submission_at=1).stdout,'11\n0\n7\n')
        for op in ('drop(->b);','b=20;','drop(->a);'):
            self.refused(source.replace('BEFORE',op))
        checked=verify_program(source.replace('BEFORE',''))
        self.assertTrue(checked.function_results['make'].task_field_updates)
        self.assertTrue(checked.function_results['relay'].task_field_updates)
        self.assertFalse(checked.function_results['make'].structure_fields)

    def test_fresh_task_waited_inside_factory(self):
        source=self.program('print(complete(&mut v,&b));BEFORE print(*v.data);',HELPERS)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(source.replace('BEFORE','drop(->b);'))
        self.assertTrue(verify_program(source.replace('BEFORE','')).function_results['complete'].structure_fields)

    def test_direct_wait_inside_factory(self):
        helpers=HELPERS+'''fn direct(v:&mut View,n:&Int)->Int{
          let h=make(v,n);return match h.join(){Ok(answer)=>{answer},Err(_)=>{0}};}'''
        source=self.program('print(direct(&mut v,&b));BEFORE print(*v.data);',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(source.replace('BEFORE','drop(->b);'))
        self.assertTrue(verify_program(source.replace('BEFORE','')).function_results['direct'].structure_fields)

    def test_inactive_factory_discard_and_launch(self):
        discarded=self.program('let t=prepare(&mut v,&b);drop(->t);drop(->b);let next=p.new(19);print(next);print(*v.data);',HELPERS)
        self.assertEqual(self.run_native(discarded).stdout,'11\n19\n7\n')
        launched=self.program('let t=prepare(&mut v,&b);let h=runtime::spawn(->t);print(finish(->h));BEFORE print(*v.data);',HELPERS)
        self.assertEqual(self.run_native(launched.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(launched.replace('BEFORE','drop(->b);'))

    def test_choice_and_loop_factory(self):
        helpers=HELPERS+'''fn choose(v:&mut View,a:&Int,b:&Int,flag:bool)-><-runtime::Handle<Int>{
          let h=if flag{let h=make(v,a);<-h}else{let h=make(v,b);<-h};
          let result=loop{h ->;break <-h;};return <-result;}'''
        for flag in ('true','false'):
            source=self.program('let h=choose(&mut v,&b,&c,'+flag+');print(finish(->h));BEFORE print(*v.data);',helpers)
            with self.subTest(flag=flag):
                expected='9' if flag=='true' else '11'
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n'+expected+'\n'+expected+'\n')
                for target in ('b','c'):
                    self.refused(source.replace('BEFORE',f'drop(->{target});'))

    def test_opaque_factory_contract(self):
        interface=verify_program(HELPERS)
        def caller(operation):
            checker=Compiler();checker.contract_calls=True
            checker.function_contracts=interface.function_contracts
            checker.async_definitions=interface.async_definitions.copy()
            checker.enums=interface.enums.copy();checker.struct_fields=interface.struct_fields.copy()
            source='''struct View{data:&Int}let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
             let mut v=View{data:&a};let h=relay(&b,&mut v);print(finish(->h));'''+operation+'print(*v.data);'
            nodes=Parser(source).parse()[1:];checker.index(nodes);checker.block('root',nodes)
            return checker
        checked=caller('')
        self.assertEqual(checked.contract_call_log,['relay','finish'])
        self.assertEqual(checked.functions,{})
        with self.assertRaisesRegex(Error,'emprunt'):caller('drop(->b);')

    def test_pool_survival_and_legacy_reset(self):
        source=HELPERS+'''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
          let a=p.new(7);let b=q.new(9);let mut v=View{data:&a};
          let h=make(&mut v,&b);print(finish(->h));BEFORE print(*v.data);
          drop(->v);q.reset();let next=q.new(19);print(next);}'''
        self.refused(source.replace('BEFORE','q.reset();'),'reset interdit',legacy=True)
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE',''),allow_legacy_reset=True)).stdout,'9\n9\n19\n')
        short=HELPERS+'''fn main(){let mut p=pool<Int>(1);let a=p.new(7);let mut v=View{data:&a};
          let h={let mut q=pool<Int>(1);let b=q.new(9);let h=make(&mut v,&b);<-h};
          print(finish(->h));print(*v.data);}'''
        self.refused(short)

    def test_factory_called_from_async_state(self):
        helpers=HELPERS+'''async fn parent(v:&mut View,n:&Int)->Int{
          let h=make(v,n);yield;let r=h.await;
          return match r{Ok(answer)=>{answer},Err(_)=>{0}};}'''
        source=self.program('let h=runtime::spawn(->parent(&mut v,&b));print(finish(->h));BEFORE print(*v.data);',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.assertEqual(self.run_native(source.replace('BEFORE',''),fail_submission_at=2).stdout,'11\n0\n7\n')
        self.refused(source.replace('BEFORE','drop(->b);'))
        # The child's replacement is already observable before parent completion.
        invalid=helpers.replace('return match r', 'print(*n);return match r')
        self.assertEqual(self.run_native(self.program(
            'let h=runtime::spawn(->parent(&mut v,&b));print(finish(->h));print(*v.data);',invalid)).stdout,
            '11\n9\n9\n9\n')

    def test_captured_field_snapshot_and_alias(self):
        helpers=HELPERS+'''fn from_field(v:&mut View,s:&View)-><-runtime::Handle<Int>{
          let saved=s.data;let mut alias=&mut *v;let h=make(alias,saved);return <-h;}'''
        source=self.program('''let mut other=View{data:&b};let h=from_field(&mut v,&other);
          print(finish(->h));change(&mut other,&c);BEFORE print(*v.data);print(*other.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n11\n')
        self.refused(source.replace('BEFORE','drop(->b);'))

    def test_completed_factory_child_keeps_stored_target_reserved(self):
        helpers=HELPERS+'''async fn parent(v:&mut View,n:&mut Int)->Int{
          let h=make(v,&*n);let r=h.await;match r{Ok(answer)=>{print(answer);},Err(_)=>{}}
          BEFORE return *v.data;}'''
        source=self.program('let h=runtime::spawn(->parent(&mut v,&mut b));print(finish(->h));print(*v.data);',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n9\n')
        self.refused(source.replace('BEFORE','n.set(20);'))

    def test_alternative_updates_waited_inside_helper(self):
        helpers=HELPERS+'''fn choose(v:&mut View,a:&Int,b:&Int,flag:bool)->Int{
          let h=if flag{let h=make(v,a);<-h}else{let h=make(v,b);<-h};
          return finish(->h);}'''
        for flag in ('true','false'):
            source=self.program('print(choose(&mut v,&b,&c,'+flag+'));BEFORE print(*v.data);',helpers)
            with self.subTest(flag=flag):
                expected='9' if flag=='true' else '11'
                self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n'+expected+'\n'+expected+'\n')
                for target in ('b','c'):
                    self.refused(source.replace('BEFORE',f'drop(->{target});'))

    def test_native_wait_and_reset_contract_order(self):
        source=self.program('''let mut carrier=&mut v;let input=&b;
          let h=runtime::thread({->(carrier,input);return complete(carrier,input);});
          print(finish(->h));BEFORE print(*v.data);''',HELPERS)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n9\n9\n')
        self.refused(source.replace('BEFORE','drop(->b);'))
        reset=HELPERS+'''fn clear(v:&mut View,n:&Int,q:&mut Pool<Int>)->Int{
          let h=make(v,n);let result=finish(->h);q.reset();return result;}
          fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
            let a=p.new(7);let b=q.new(9);let mut v=View{data:&a};
            print(clear(&mut v,&b,&mut q));print(*v.data);}'''
        self.refused(reset,'reset interdit',legacy=True)

    def test_independent_retention_model(self):
        admitted=refused=0
        for inactive,dead,target in product((False,True),(False,True),('a','b')):
            retained=set() if dead else {'a'} if inactive else {'a','b'}
            action=('let t=prepare(&mut v,&b);drop(->t);' if inactive else
                    'let h=relay(&b,&mut v);print(finish(->h));')
            source=self.program(action+('drop(->v);' if dead else '')+f'drop(->{target});'+
                                ('' if dead else 'print(*v.data);'),HELPERS)
            with self.subTest(inactive=inactive,dead=dead,target=target):
                if target in retained:
                    self.refused(source);refused+=1
                else:
                    self.assertEqual(self.run_native(source).stdout,'11\n'+('' if inactive else '9\n')+
                                     ('' if dead else '7\n' if inactive else '9\n'));admitted+=1
        self.assertEqual((admitted,refused),(5,3))

if __name__=='__main__':unittest.main()
