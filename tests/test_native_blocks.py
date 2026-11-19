"""Execute RT8 blocks through the real parser, checker and C backend."""
from pathlib import Path
import unittest

from crust import Error, compile_source, verify_program
import test_async_runtime as runtime_tests


class NativeBlockTests(unittest.TestCase):
    run_c_oracle = runtime_tests.AsyncRuntimeTests.run_c_oracle

    def run_native(self, source, *, fail_at=None, fail_submission_at=None, fail_native=False):
        code = compile_source(source)
        if fail_submission_at is not None:
            anchor = 'static int task_default_submit(CrustTask *task) {'
            self.assertEqual(code.count(anchor), 1)
            code = code.replace(anchor, '_Atomic int injected_submission_count;\n' + anchor +
                                f'\n    if (atomic_fetch_add(&injected_submission_count, 1) + 1 == {fail_submission_at}) return EAGAIN;')
        if fail_at is not None or fail_native:
            boundary = r'''
#include <pthread.h>
#include <errno.h>
#include <stdatomic.h>
static _Atomic int native_launch_count;
static void *task_native_run(void *pointer);
static int selective_launch(pthread_t *thread, const pthread_attr_t *attr,
                            void *(*run)(void *), void *data) {
    if (FAIL_NATIVE ? run == task_native_run :
            atomic_fetch_add(&native_launch_count, 1) + 1 == FAIL_AT) return EAGAIN;
    return pthread_create(thread, attr, run, data);
}
#define pthread_create selective_launch
'''.replace('FAIL_AT', str(fail_at or 0)).replace('FAIL_NATIVE', str(int(fail_native)))
            code = code.replace('#include <pthread.h>', boundary, 1)
        return self.run_c_oracle(code)

    def assert_destroyed(self, run, values):
        trace = [line.rsplit('=',1)[-1] for line in run.stderr.splitlines()
                 if line.startswith('destroy ')]
        self.assertEqual(trace,[str(value) for value in values])

    @staticmethod
    def wrap(body, asynchronous=False):
        if not asynchronous:
            return 'fn main(){' + body + '}'
        return ('async fn work(){' + body.replace('h.join()', 'h.await') + '}'
                'fn main(){let top=runtime::spawn(->work());'
                'match top.join(){Ok(())=>{},Err(_)=>{print(999);}}}')

    def test_recorded_program_tail_early_and_primitive_results(self):
        source = (Path(__file__).resolve().parents[1] / 'validation/open-native-thread-basic.crb').read_text()
        self.assertEqual(self.run_native(source).stdout, '7\n')
        for body, expected, pattern in (
            ('7', '7\n', 'v'),
            ('if true{return 7;}return 9;', '7\n', 'v'),
            ('return false;', '0\n', 'v'),
            ('let b:u8=8;return b;', '8\n', 'v'),
            ('print(7);', '7\n', '()'),
            ('let n=loop{break 11;};return n;', '11\n', 'v'),
        ):
            out = '' if pattern == '()' else 'print(v);'
            if body == 'return false;':
                out = 'if v{print(1);}else{print(0);}'
            elif body == 'let b:u8=8;return b;':
                out = 'print(v as Int);'
            with self.subTest(body=body):
                self.assertEqual(self.run_native('fn main(){let h=runtime::thread({' + body +
                    '});match h.join(){Ok(' + pattern + ')=>{' + out + '},Err(_)=>{print(99);}}}').stdout, expected)

    def test_scalar_capture_consumes_binding_in_both_callers(self):
        body = '''let n=5;let h=runtime::thread({->(n);return n+1;});
            BEFORE match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}} AFTER'''
        for asynchronous in (False, True):
            self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE','').replace('AFTER',''), asynchronous)).stdout, '6\n')
            for position in ('BEFORE', 'AFTER'):
                invalid = body.replace(position, 'print(n);').replace('BEFORE','').replace('AFTER','')
                with self.subTest(asynchronous=asynchronous, position=position), self.assertRaises(Error):
                    verify_program(self.wrap(invalid, asynchronous))

    def test_mutable_capture_and_return_keep_target_reserved(self):
        body = '''let mut p=pool<Int>(1);let mut a=p.new(7);let vue=&mut a;
          let h=runtime::thread({->(vue);vue.set(20);return vue;}); BEFORE
          let result=h.join(); DURING
          match result{Ok(v)=>{v.set(42);},Err(_)=>{}}
          print(a);a=50;print(a);'''
        for asynchronous in (False, True):
            selected = body
            if asynchronous:
                selected = selected.replace('let mut p=pool<Int>(1);let mut a=p.new(7);let vue=&mut a;',
                                            'let mut values=[7];let vue=&mut values[0];')
                selected = selected.replace('print(a);a=50;print(a);', 'print(values[0]);values[0]=50;print(values[0]);')
            valid = selected.replace('BEFORE','').replace('DURING','')
            self.assertEqual(self.run_native(self.wrap(valid, asynchronous)).stdout, '42\n50\n')
            for position in ('BEFORE', 'DURING'):
                for conflict in ('print(a);', 'a=3;', 'drop(->a);'):
                    if asynchronous:
                        conflict = {'print(a);':'print(values[0]);','a=3;':'values[0]=3;',
                                    'drop(->a);':'drop(->values);'}[conflict]
                    source = selected.replace(position, conflict).replace('BEFORE','').replace('DURING','')
                    with self.subTest(asynchronous=asynchronous, position=position, conflict=conflict), self.assertRaises(Error):
                        verify_program(self.wrap(source, asynchronous))
            with self.assertRaises(Error):
                verify_program(self.wrap(selected.replace('BEFORE','print(vue);').replace('DURING',''), asynchronous))

    def test_array_targets_survive_native_wait_and_then_mutate(self):
        body = '''let mut values=[7];let vue=&values[0];
          let h=runtime::thread({->(vue);return *vue;}); BEFORE
          match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}
          values[0]=20;print(values[0]);'''
        for asynchronous in (False, True):
            self.assertEqual(self.run_native(self.wrap(body.replace('BEFORE',''), asynchronous)).stdout, '7\n20\n')
            with self.assertRaises(Error):
                verify_program(self.wrap(body.replace('BEFORE','values[0]=3;'), asynchronous))

    def test_owned_capture_cleanup_failure_and_reuse(self):
        body = '''let mut p=pool<Int>(1);let a=p.new(7);
          let h=runtime::thread({->(a);return *a;});
          match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}
          let b=p.new(9);print(b);drop(->b);'''
        for asynchronous in (False, True):
            source = self.wrap(body, asynchronous)
            if asynchronous:
                source = '''async fn work(a: -> Int)->Int{
                  let h=runtime::thread({->(a);return *a;});
                  match h.await{Ok(v)=>{return v;},Err(_)=>{return 99;}}
                }fn main(){let mut p=pool<Int>(1);let a=p.new(7);
                  let top=runtime::spawn(->work(->a));
                  match top.join(){Ok(v)=>{print(v);},Err(_)=>{print(999);}}
                  let b=p.new(9);print(b);drop(->b);}'''
            run = self.run_native(source)
            self.assertEqual(run.stdout, '7\n9\n')
            self.assert_destroyed(run,[7,9])
            # Fail the native child, independently of scheduler worker creation.
            failed = self.run_native(source, fail_native=True)
            self.assertEqual(failed.stdout, '99\n9\n')
            self.assert_destroyed(failed,[7,9])
            with self.assertRaises(Error):
                verify_program(source.replace('let b=p.new(9);', 'print(a);let b=p.new(9);'))

    def test_owned_result_is_transferred_before_frame_release(self):
        source = '''fn main(){let mut p=pool<Int>(1);let a=p.new(7);address(a);
          let h=runtime::thread({->(a);return <-a;});
          match h.join(){Ok(v)=>{address(v);print(v);drop(->v);},Err(_)=>{print(99);}}
          let b=p.new(9);address(b);print(b);drop(->b);}'''
        run = self.run_native(source)
        self.assert_destroyed(run,[7,9])
        output = run.stdout.splitlines()
        self.assertEqual((output[2],output[4]),('7','9'))
        self.assertEqual(output[0],output[1])
        self.assertEqual(output[0],output[3])
        failed_run = self.run_native(source, fail_at=1)
        self.assert_destroyed(failed_run,[7,9])
        failed = failed_run.stdout.splitlines()
        self.assertEqual((failed[1],failed[3]),('99','9'))
        self.assertEqual(failed[0],failed[2])
        with self.assertRaises(Error):
            verify_program(source.replace('return <-a;', 'return a;'))

    def test_nested_thread_join_stays_synchronous(self):
        source = '''fn main(){let h=runtime::thread({
          let child=runtime::thread({return 7;});
          match child.join(){Ok(v)=>{return v+1;},Err(_)=>{return 90;}}
        });match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout, '8\n')
        self.assertEqual(self.run_native(source, fail_at=2).stdout, '90\n')
        self.assertEqual(self.run_native(source, fail_at=1).stdout, '99\n')
        with self.assertRaises(Error):
            verify_program(source.replace('match child.join(){Ok(v)=>{return v+1;},Err(_)=>{return 90;}}', 'return 8;'))

    def test_type_capture_mutability_and_lifetime_rejections(self):
        invalid = (
            'let n=7;let h=runtime::thread({return n;});',
            'let n=7;let h=runtime::thread({->(n);n=8;return n;});',
            'let h=runtime::thread({if true{return 7;}return false;});',
            'let h=runtime::thread({if true{return 7;}});',
            'let mut p=pool<Int>(1);let h=runtime::thread({->(p);return 7;});',
            'let h=runtime::thread({let data=[7];return &data[0];});',
            'let h={let mut p=pool<Int>(1);let a=p.new(7);let inner=runtime::thread({->(a);return 7;});<-inner};',
            'let h={let data=[7];let vue=&data[0];let inner=runtime::thread({->(vue);return *vue;});<-inner};',
        )
        for prefix in invalid:
            with self.subTest(prefix=prefix), self.assertRaises(Error):
                verify_program('fn main(){' + prefix +
                               'match h.join(){Ok(v)=>{print(v);},Err(_)=>{}}}')

    def test_wait_obligation_on_both_return_paths(self):
        body = '''let h=runtime::thread({return 7;});
          if true{return;}match h.join(){Ok(v)=>{print(v);},Err(_)=>{}}'''
        for asynchronous in (False, True):
            with self.subTest(asynchronous=asynchronous), self.assertRaisesRegex(Error,'attente requise|join requis'):
                verify_program(self.wrap(body, asynchronous))

    def test_sync_function_contract_captures_its_reference_parameter(self):
        source = '''fn read(data:&Int)->Int{
          let h=runtime::thread({->(data);return *data;});
          match h.join(){Ok(v)=>{return v;},Err(_)=>{return 99;}}
        }fn main(){let mut p=pool<Int>(1);let mut a=p.new(7);
          print(read(&a));a=20;print(a);}'''
        self.assertEqual(self.run_native(source).stdout, '7\n20\n')
        self.assertEqual(self.run_native(source, fail_at=1).stdout, '99\n20\n')
        with self.assertRaises(Error):
            verify_program(source.replace('match h.join()', 'print(data);match h.join()'))

    def test_conditional_reference_result_preserves_both_sources(self):
        template = '''fn main(){let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
          let av=&mut a;let bv=&mut b;let flag=FLAG;
          let h=runtime::thread({->(flag,av,bv);return if flag==1{av}else{bv};});
          let r=h.join();CONFLICT
          match r{Ok(v)=>{v.set(42);},Err(_)=>{}}
          print(a);print(b);}'''
        for flag in (0,1):
            source = template.replace('FLAG',str(flag))
            self.assertEqual(self.run_native(source.replace('CONFLICT','')).stdout,
                             '42\n20\n' if flag else '10\n42\n')
            for target in ('a','b'):
                with self.subTest(flag=flag,target=target), self.assertRaises(Error):
                    verify_program(source.replace('CONFLICT',target+'=3;'))

    def test_whole_array_capture_moves_and_preserves_contents(self):
        source = '''fn main(){let values=[3,4];
          let h=runtime::thread({->(values);return values[0]+values[1];});
          match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout,'7\n')
        with self.assertRaises(Error):
            verify_program(source.replace('match h.join()','print(values[0]);match h.join()'))

    def test_generated_native_launch_bypasses_rejecting_scheduler(self):
        body = 'let h=runtime::thread({return 7;});match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}'
        for asynchronous in (False,True):
            code = compile_source(self.wrap(body,asynchronous))
            callback = '''static _Atomic int scheduled_launches;
static int checked_scheduler(pthread_t *thread,int detached,void *(*run)(void *),void *data){
    if(atomic_fetch_add(&scheduled_launches,1) >= ALLOWED) return EAGAIN;
    return task_pthread_launch(thread,detached,run,data);
}
'''.replace('ALLOWED','1' if asynchronous else '0')
            code = code.replace('static const CrustThreadScheduler task_default_scheduler',
                                callback+'static const CrustThreadScheduler task_default_scheduler')
            code = code.replace('.launch = task_pthread_launch,','.launch = checked_scheduler,')
            code = code.replace('.launch_blocking = task_pthread_launch','.launch_blocking = checked_scheduler')
            self.assertEqual(self.run_c_oracle(code).stdout,'7\n')


if __name__ == '__main__':
    unittest.main()
