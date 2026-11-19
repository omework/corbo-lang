"""RT4/RT6/RT7: blocking intent, typed launch failure, and mandatory waits."""
import itertools
import unittest
import test_async_runtime
import test_type_features
from async_runtime import TASK_RUNTIME, TASK_THREAD_RUNTIME, TASK_ASYNC_THREAD_RUNTIME
from crust import Error, compile_source, verify_program


class SpawnBlockingTests(unittest.TestCase):
    native = test_type_features.TypeFeatureTests.native
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle
    leaf='async fn leaf(n:-> Int)->Int{yield;return *n;}'
    rejecting_callback='''
static int reject_blocking(pthread_t *t, int detached, void *(*run)(void *), void *p) {
    (void)t; (void)detached; (void)run; (void)p;
    return EAGAIN;
}
'''

    def reject_blocking(self, code):
        anchor='static const CrustThreadScheduler task_default_scheduler = {'
        self.assertIn(anchor,code)
        return code.replace(anchor,self.rejecting_callback+anchor).replace(
            '.launch_blocking = task_pthread_launch', '.launch_blocking = reject_blocking')

    def test_sync_and_async_dispatch_keep_blocking_intent_and_cleanup(self):
        # Independent expectation: only the explicitly blocking launch is
        # rejected by this scheduler. Normal launches must still run.
        for method, asynchronous in itertools.product(('spawn','spawn_blocking'),(False,True)):
            invocation=f'let h=runtime::{method}(-> leaf(-> n));'
            wait='await' if asynchronous else 'join()'
            body=invocation+f'''match h.{wait}{{Ok(v)=>{{print(v);}},
                Err(runtime::Error::LaunchFailed)=>{{print(99);}}}}'''
            if asynchronous:
                source=self.leaf+'async fn parent(n:-> Int){'+body+'}'+'''
                    fn main(){let mut p=pool<Int>(1);let n=p.new(17);address(n);
                        let h=runtime::spawn(-> parent(-> n));
                        match h.join(){Ok(())=>{},Err(runtime::Error::LaunchFailed)=>{print(88);}}
                        let reused=p.new(21);address(reused);print(reused);}
                '''
            else:
                source=self.leaf+'''fn main(){let mut p=pool<Int>(1);let n=p.new(17);address(n);'''+body+'''
                    let reused=p.new(21);address(reused);print(reused);}
                '''
            for reject in (False,True):
                code=compile_source(source)
                if reject:
                    code=self.reject_blocking(code)
                expected=99 if reject and method=='spawn_blocking' else 17
                with self.subTest(method=method,asynchronous=asynchronous,reject=reject):
                    run=self.run_c_oracle(code)
                    lines=run.stdout.splitlines()
                    self.assertEqual(lines[0],lines[2])
                    self.assertEqual(lines[1],str(expected))
                    self.assertEqual(lines[3],'21')
                    self.assertEqual(run.stderr.count('destroy n=17'),1)

    def test_blocking_handle_contract_relay_and_borrow_reservations(self):
        source='''async fn edit(n:&mut Int)->Int{yield;n.set(8);return *n;}
            fn launch(n:&mut Int)-><- Execution<edit>{
                let h=runtime::spawn_blocking(-> edit(n));return <- h;}
            fn relay(h:-> Execution<edit>)-><- Execution<edit>{return <- h;}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(3);
                let h=launch(&mut n);let received=relay(->h);BEFORE
                match received.join(){Ok(v)=>{print(v);},Err(runtime::Error::LaunchFailed)=>{print(99);}}
                n.set(9);print(n);}
        '''
        self.assertEqual(self.native(source.replace('BEFORE','')).stdout,'8\n9\n')
        for conflict in ('print(n);','n.set(4);','drop(->n);','p.reset();'):
            with self.subTest(conflict=conflict),self.assertRaisesRegex(Error,'emprunt|exécution|utilisée'):
                verify_program(source.replace('BEFORE',conflict),allow_legacy_reset=True)

    def test_blocking_launch_requires_move_and_wait_on_every_path(self):
        prefix='async fn leaf()->Int{return 7;}'
        for invocation in ('runtime::spawn_blocking()', 'runtime::spawn_blocking(leaf(),leaf())',
                           'runtime::spawn_blocking(->leaf(),->leaf())'):
            with self.subTest(invocation=invocation),self.assertRaisesRegex(Error,'transférée'):
                verify_program(prefix+'fn main(){let h='+invocation+';}')
        for ending in ('','drop(->h);','if true{h ->;drop(->h);}else{}'):
            with self.subTest(ending=ending),self.assertRaisesRegex(Error,'join requis'):
                verify_program(prefix+'fn main(){let h=runtime::spawn_blocking(->leaf());'+ending+'}')
        with self.assertRaisesRegex(Error,'attente requise'):
            verify_program(prefix+'async fn parent(){let h=runtime::spawn_blocking(->leaf());yield;}fn main(){}')
        with self.assertRaisesRegex(Error,'inactive'):
            verify_program(prefix+'''fn main(){let h=runtime::spawn_blocking(->leaf());
                let second=runtime::spawn_blocking(->h);match second.join(){Ok(n)=>{print(n);},Err(_)=>{}}}''')

    def test_public_runtime_error_in_owned_and_nested_result_contracts(self):
        source='''async fn leaf(n:-> Int)-><- Int{yield;return <- n;}
            fn take(n:-> Int)-><- Result<A<Int>,runtime::Error>{
                let h=runtime::spawn_blocking(->leaf(->n));let r=h.join();return <- r;}
            async fn relay(r:-> Result<A<Int>,runtime::Error>)-><- Result<A<Int>,runtime::Error>{
                yield;return <- r;}
            fn main(){let mut p=pool<Int>(1);let n=p.new(5);let r=take(->n);
                let h=runtime::spawn(->relay(->r));
                match h.join(){Ok(inner)=>{match inner{Ok(value)=>{print(value);drop(->value);},
                    Err(runtime::Error::LaunchFailed)=>{print(99);}}},Err(runtime::Error::LaunchFailed)=>{print(88);}}
                let next=p.new(6);print(next);}
        '''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,'5\n6\n')
        self.assertEqual(self.run_c_oracle(self.reject_blocking(compile_source(source))).stdout,'99\n6\n')
        with self.assertRaisesRegex(Error,'variante'):
            verify_program(source.replace('runtime::Error::LaunchFailed','runtime::Error::Cancelled'))
        with self.assertRaisesRegex(Error,'incompatible'):
            verify_program('fn main(){match "é".char_at(0){Ok(c)=>{print(c);},Err(runtime::Error::LaunchFailed)=>{}}}')
        with self.assertRaisesRegex(Error,'incompatible'):
            verify_program('async fn leaf()->Int{return 1;}fn main(){let h=runtime::spawn(->leaf());match h.join(){Ok(n)=>{print(n);},Err(CharAtError::OutOfBounds)=>{},Err(CharAtError::NotCharBoundary)=>{}}}')

    def test_scheduler_callbacks_are_distinct_and_missing_blocking_rejects_cleanly(self):
        code=TASK_RUNTIME+TASK_THREAD_RUNTIME+TASK_ASYNC_THREAD_RUNTIME+r'''
#include <assert.h>
#include <stdio.h>
static int ordinary, blocking, released;
static CrustTaskStep resume(CrustTask *t){(void)t;return TASK_STEP_RETURN;}
static void take(CrustTask *t,void *out){(void)t;*(int *)out=7;}
static void release(CrustTask *t){(void)t;++released;}
static const CrustTaskOps ops={resume,take,release};
static int launch(pthread_t *t,int d,void *(*run)(void *),void *p){
    ++ordinary;return task_pthread_launch(t,d,run,p);
}
static int blocked(pthread_t *t,int d,void *(*run)(void *),void *p){
    (void)t;(void)d;(void)run;(void)p;++blocking;return EAGAIN;
}
int main(void){
    const CrustThreadScheduler scheduler={.launch=launch,.wait=task_pthread_wait,.launch_blocking=blocked};
    CrustTask a,b,c,d;CrustExecution x,y;CrustAsyncExecution z;
    task_init(&a,&ops);task_init(&b,&ops);task_init(&c,&ops);task_init(&d,&ops);
    assert(task_thread_start_with(&x,&a,&scheduler)==0);
    assert(task_join_result(&x).value==7);
    assert(task_thread_start_blocking_with(&y,&b,&scheduler)==EAGAIN);
    assert(task_join_result(&y).status==CRUST_RUNTIME_LAUNCH_FAILED);
    task_async_start_blocking_with(&z,&c,&scheduler);
    CrustJoinResult result;assert(task_async_take(&z,&result));
    assert(result.status==CRUST_RUNTIME_LAUNCH_FAILED);
    const CrustThreadScheduler missing={.launch=launch,.wait=task_pthread_wait};
    assert(task_thread_start_blocking_with(&y,&d,&missing)==ENOTSUP);
    assert(task_join_result(&y).status==CRUST_RUNTIME_LAUNCH_FAILED);
    assert(ordinary==1 && blocking==2 && released==4);
    puts("dispatch ok");return 0;
}
'''
        self.assertEqual(self.run_c_oracle(code).stdout,'dispatch ok\n')

    def test_default_blocking_worker_leaves_other_worker_able_to_progress(self):
        code=TASK_RUNTIME+TASK_THREAD_RUNTIME+r'''
#include <assert.h>
#include <stdio.h>
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
static int entered, ready, released;
static CrustTaskStep wait_for_peer(CrustTask *t){
    (void)t;assert(pthread_mutex_lock(&lock)==0);entered=1;
    assert(pthread_cond_broadcast(&condition)==0);
    while(!ready) assert(pthread_cond_wait(&condition,&lock)==0);
    assert(pthread_mutex_unlock(&lock)==0);return TASK_STEP_RETURN;
}
static CrustTaskStep notify_peer(CrustTask *t){
    (void)t;assert(pthread_mutex_lock(&lock)==0);assert(entered);ready=1;
    assert(pthread_cond_broadcast(&condition)==0);
    assert(pthread_mutex_unlock(&lock)==0);return TASK_STEP_RETURN;
}
static void take(CrustTask *t,void *out){(void)t;*(int *)out=1;}
static void release(CrustTask *t){(void)t;++released;}
static const CrustTaskOps blocking_ops={wait_for_peer,take,release}, ordinary_ops={notify_peer,take,release};
int main(void){
    CrustTask a,b;CrustExecution x,y;task_init(&a,&blocking_ops);task_init(&b,&ordinary_ops);
    assert(task_thread_start_blocking(&x,&a)==0);
    assert(pthread_mutex_lock(&lock)==0);
    while(!entered) assert(pthread_cond_wait(&condition,&lock)==0);
    assert(pthread_mutex_unlock(&lock)==0);
    assert(task_thread_start(&y,&b)==0);
    assert(task_join_result(&x).value==1);assert(task_join_result(&y).value==1);
    assert(released==2);puts("progress ok");return 0;
}
'''
        self.assertEqual(self.run_c_oracle(code).stdout,'progress ok\n')


if __name__=='__main__':
    unittest.main()
