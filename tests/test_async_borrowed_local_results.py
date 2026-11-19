"""Returned carriers keep their target loans after task destruction."""
from pathlib import Path
import unittest
import test_select_source as source_tests
import test_native_blocks as native_tests
import test_async_result_storage as storage_tests

ROOT=Path(__file__).resolve().parents[1]
PREFIX='''struct View{data:&Int}fn wrap(n:&Int)-><-View{let v=View{data:n};return <-v;}
async fn leaf(n:&Int)-><-View{let v=wrap(n);yield;return <-v;}'''
class AsyncBorrowedLocalResultTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused
    run_native=native_tests.NativeBlockTests.run_native
    storage_probe=storage_tests.AsyncResultStorageTests.storage_probe

    @staticmethod
    def program(body,helpers='',prefix=PREFIX):
        return prefix+helpers+'async fn work()->Int{'+body+'''}fn main(){let h=runtime::spawn(->work());
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_and_target_lifetime(self):
        source=(ROOT/'validation/open-async-result-storage-borrowed.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(*v.data);','drop(->n);print(*v.data);'),'emprunt|réserv|référenc')
        valid=source.replace('drop(->v);','drop(->v);drop(->n);let next=ints.new(9);print(*next);')
        self.assertEqual(self.run_source(valid).stdout,'7\n9\n')

    def test_direct_await_named_and_launched(self):
        prefix='let mut ns=pool<Int>(1);let n=ns.new(7);'
        for receive in ('let v=leaf(&n).await;', 'let t=leaf(&n);let v=t.await;',
                        'let t=runtime::spawn(->leaf(&n));let v=match t.await{Ok(v)=>{<-v},Err(_)=>{return 99;}};'):
            source=self.program(prefix+receive+'yield;print(*v.data);drop(->v);drop(->n);let next=ns.new(9);return *next;')
            with self.subTest(receive=receive):
                self.assertEqual(self.run_source(source).stdout,'7\n9\n')
                self.refused(source.replace('yield;print(*v.data);','drop(->n);yield;print(*v.data);'),'emprunt|réserv|référenc')

    def test_factory_relay_and_parent_receiver(self):
        helpers='fn prepare(n:&Int)-><-leaf{return <-leaf(n);}async fn relay(n:&Int)-><-View{return <-leaf(n).await;}'
        for call in ('prepare(&n)','relay(&n)'):
            source=self.program('let mut ns=pool<Int>(1);let n=ns.new(7);let v={let t=CALL;let v=t.await;<-v};yield;return *v.data;'.replace('CALL',call),helpers)
            self.assertEqual(self.run_source(source).stdout,'7\n')
            self.refused(source.replace('yield;return *v.data;', 'drop(->n);yield;return *v.data;'),'emprunt|réserv|référenc')
        source=PREFIX+helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let v={let t=prepare(&n);
          let h=runtime::spawn(->t);let v=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};<-v};print(*v.data);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(*v.data);','drop(->n);print(*v.data);'),'emprunt|réserv|référenc')

    def test_shared_projection_outlives_carrier(self):
        source=self.program('let mut ns=pool<Int>(1);let n=ns.new(7);let v=leaf(&n).await;let view=v.data;drop(->v);yield;print(*view);drop(->n);return 9;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('yield;print(*view);','drop(->n);yield;print(*view);'),'emprunt|réserv|référenc')

    def test_mutable_result_reborrow(self):
        prefix='''struct Writer{data:&mut Int}fn wrap(n:&mut Int)-><-Writer{let v=Writer{data:n};return <-v;}
          async fn leaf(n:&mut Int)-><-Writer{let v=wrap(n);yield;return <-v;}'''
        body='let mut ns=pool<Int>(1);let mut n=ns.new(7);let mut v=leaf(&mut n).await;let mut w=&mut *v.data;yield;w.set(20);print(*w);drop(->v);return *n;'
        source=self.program(body,prefix=prefix)
        self.assertEqual(self.run_source(source).stdout,'20\n20\n')
        for invalid in ('print(*n);','drop(->v);','let mut x=&mut *v.data;x.set(30);'):
            self.refused(source.replace('yield;w.set(20);',invalid+'yield;w.set(20);'),'emprunt|réserv|référenc')

    def test_short_target_and_owned_capture_rejected(self):
        source=self.program('let v={let mut ns=pool<Int>(1);let n=ns.new(7);let v=leaf(&n).await;<-v};return *v.data;')
        self.refused(source,'durable|survi|emprunt|réserv|référenc')
        for body in ('let mut ns=pool<Int>(1);let n=ns.new(7);let v=wrap(&n);return <-v;',):
            self.refused(PREFIX+'async fn bad()-><-View{'+body+'}','durable|emprunt|local')
        self.refused(PREFIX+'async fn bad(n:->A<Int>)-><-View{let v=wrap(&n);return <-v;}','durable|emprunt|local')

    def test_inactive_and_failed_launch_release_capture(self):
        source=PREFIX+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let t=leaf(&n);drop(->t);drop(->n);let next=ns.new(9);print(*next);}'''
        self.assertEqual(self.run_source(source).stdout,'9\n')
        launched=source.replace('drop(->t);','let h=runtime::spawn(->t);match h.join(){Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{print(99);}}')
        run=self.run_native(launched,fail_submission_at=1)
        self.assertEqual(run.stdout,'99\n9\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)

    def test_fields_detach_independently(self):
        prefix='struct Pair{left:&Int,right:&Int}\n          fn wrap(a:&Int,b:&Int)-><-Pair{let p=Pair{left:a,right:b};return <-p;}\n          async fn pair(a:&Int,b:&Int)-><-Pair{yield;return <-wrap(a,b);}'
        body='let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let p=pair(&a,&b).await;let left=p.left;drop(->p);drop(->b);yield;print(*left);drop(->a);return 11;'
        source=self.program(body,prefix=prefix)
        self.assertEqual(self.run_source(source).stdout,'7\n11\n')
        self.refused(source.replace('yield;print(*left);','drop(->a);yield;print(*left);'),'emprunt|réserv|référenc')

    def test_conditional_results_and_named_tasks(self):
        helper='async fn choose(a:&Int,b:&Int,flag:Bool)-><-View{if flag{return <-wrap(a);}yield;return <-wrap(b);}'
        for flag,expected in (('true',7),('false',9)):
            body='let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let v=choose(&a,&b,FLAG).await;print(*v.data);drop(->v);drop(->a);drop(->b);return 11;'.replace('FLAG',flag)
            source=self.program(body,helper)
            self.assertEqual(self.run_source(source).stdout,f'{expected}\n11\n')
            for target in ('a','b'):
                self.refused(source.replace('print(*v.data);',f'drop(->{target});print(*v.data);'),'emprunt|réserv|référenc')
            task='let t=if FLAG{let t=leaf(&a);<-t}else{let t=leaf(&b);<-t};let v=t.await;'.replace('FLAG',flag)
            source=self.program(body.replace('let v=choose(&a,&b,FLAG).await;'.replace('FLAG',flag),task))
            self.assertEqual(self.run_source(source).stdout,f'{expected}\n11\n')

    def test_loop_replacement_and_last_use(self):
        body='let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let mut v=leaf(&a).await;let mut i=0; while i<3{print(*v.data);v=<-leaf(&b).await;i=i+1;}print(*v.data);drop(->v);drop(->a);drop(->b);return i;'
        source=self.program(body)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n9\n9\n3\n')
        self.refused(source.replace('print(*v.data);drop(->v);','drop(->b);print(*v.data);drop(->v);'),'emprunt|réserv|référenc')
        last=self.program('let mut ns=pool<Int>(1);let n=ns.new(7);let v=leaf(&n).await;print(*v.data);drop(->n);return 9;')
        self.assertEqual(self.run_source(last).stdout,'7\n9\n')

    def test_select_result_and_loser_capture(self):
        body='let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let mut s=runtime::select(->leaf(&a),->leaf(&b)); let v=s.await;print(*v.data);drop(->s);drop(->v);drop(->a);drop(->b);return 11;'
        source=self.program(body)
        self.assertEqual(self.run_source(source).stdout,'7\n11\n')
        self.refused(source.replace('print(*v.data);drop(->s);','drop(->s);drop(->a);print(*v.data);'),'emprunt|réserv|référenc')
        inactive=self.program(body.replace('let v=s.await;print(*v.data);drop(->s);drop(->v);','drop(->s);'))
        self.assertEqual(self.run_source(inactive).stdout,'11\n')

    def test_join_returned_by_sync_helper(self):
        helpers='fn finish(h:->Execution<leaf>,fallback:&Int)-><-View{let v=match h.join(){Ok(v)=>{<-v},Err(_)=>{let v=wrap(fallback);<-v}};return <-v;}'
        source=PREFIX+helpers+'fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->leaf(&n));\n          let v=finish(->h,&n);print(*v.data);drop(->v);drop(->n);}'
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(*v.data);','drop(->n);print(*v.data);'),'emprunt|réserv|référenc')
        self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'7\n')

    def test_helper_chain_keeps_both_possible_targets(self):
        helpers='''fn finish(h:->Execution<leaf>,fallback:&Int)-><-View{
          let v=match h.join(){Ok(v)=>{<-v},Err(_)=>{let v=wrap(fallback);<-v}};return <-v;}
          fn relay(h:->Execution<leaf>,fallback:&Int)-><-View{return <-finish(->h,fallback);}'''
        source=PREFIX+helpers+'''fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
          let h=runtime::spawn(->leaf(&a));let v=relay(->h,&b);print(*v.data);drop(->v);drop(->a);drop(->b);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'9\n')
        for target in ('a','b'):
            self.refused(source.replace('print(*v.data);',f'drop(->{target});print(*v.data);'),'emprunt|réserv|référenc')

    def test_mutable_sync_result_and_helper(self):
        prefix='''struct Writer{data:&mut Int}fn wrap(n:&mut Int)-><-Writer{let v=Writer{data:n};return <-v;}
          async fn leaf(n:&mut Int)-><-Writer{let v=wrap(n);yield;return <-v;}'''
        helpers='''fn finish(h:->Execution<leaf>,fallback:&mut Int)-><-Writer{
          let v=match h.join(){Ok(v)=>{<-v},Err(_)=>{let v=wrap(fallback);<-v}};return <-v;}'''
        for receiver in ('match h.join(){Ok(v)=>{<-v},Err(_)=>{let v=wrap(&mut b);<-v}}',
                         'finish(->h,&mut b)'):
            source=prefix+helpers+'''fn main(){let mut ns=pool<Int>(2);let mut a=ns.new(7);let mut b=ns.new(9);
              let h=runtime::spawn(->leaf(&mut a));let mut v=RECEIVE;let mut w=&mut *v.data;
              w.set(20);print(*w);drop(->v);print(*a);print(*b);}'''.replace('RECEIVE',receiver)
            self.assertEqual(self.run_source(source).stdout,'20\n20\n9\n')
            self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'20\n7\n20\n')
            for access in ('print(*a);','print(*b);','drop(->v);'):
                self.refused(source.replace('w.set(20);',access+'w.set(20);'),'emprunt|réserv|référenc')

    def test_two_target_scope_model(self):
        prefix='''struct Pair{left:&Int,right:&Int}
          fn wrap(a:&Int,b:&Int)-><-Pair{let p=Pair{left:a,right:b};return <-p;}
          async fn pair(a:&Int,b:&Int)-><-Pair{yield;return <-wrap(a,b);}'''
        # Independent finite oracle: both target lifetimes must include the
        # receiver scope, regardless of the lifetime of the async state slot.
        for a_outer in (False,True):
            for b_outer in (False,True):
                outer='let mut outer=pool<Int>(2);'
                inner='let mut inner=pool<Int>(2);'
                for name,value,is_outer in (('a',7,a_outer),('b',9,b_outer)):
                    if is_outer:outer+=f'let {name}=outer.new({value});'
                    else:inner+=f'let {name}=inner.new({value});'
                source=prefix+'fn main(){'+outer+'let p={'+inner+'''
                  let h=runtime::spawn(->pair(&a,&b));
                  let p=match h.join(){Ok(p)=>{<-p},Err(_)=>{return;}};<-p};
                  print(*p.left);print(*p.right);}'''
                with self.subTest(a_outer=a_outer,b_outer=b_outer):
                    if a_outer and b_outer:self.assertEqual(self.run_source(source).stdout,'7\n9\n')
                    else:self.refused(source,'durable|survi|emprunt|réserv|référenc')

    def test_direct_constructor_parent_and_borrow_guard(self):
        for mutable in (False,True):
            reference='&mut Int' if mutable else '&Int'
            prefix=f'''struct View{{data:{reference}}}
              async fn leaf(n:{reference})-><-View{{let v=View{{data:n}};yield;return <-v;}}'''
            borrow='&mut n' if mutable else '&n'
            source=self.program('''let mut ns=pool<Int>(1);let mut n=ns.new(7);
              let v={let v={let v=leaf(BORROW).await;<-v};<-v};yield;print(*v.data);
              drop(->v);drop(->n);let next=ns.new(9);return *next;'''.replace('BORROW',borrow),prefix=prefix)
            self.assertEqual(self.run_source(source).stdout,'7\n9\n')
            self.refused(source.replace('yield;print(*v.data);','drop(->n);yield;print(*v.data);'),
                         'emprunt|réserv|référenc')
        prefix='struct View{data:&Int}'
        self.refused(prefix+'''async fn bad()-><-View{let mut ns=pool<Int>(1);let n=ns.new(7);
          let v=View{data:&n};yield;return <-v;}''','durable|emprunt|local')

    def test_suspended_cleanup_and_identity(self):
        source=self.program('let mut ns=pool<Int>(1);let n=ns.new(7);let v=leaf(&n).await;yield;return *v.data;')
        for direct in (False,True):
            program=source.replace('let v=wrap(n);yield;', 'let v=View{data:n};yield;') if direct else source
            for finish in (False,True):
                ending=('assert(task_poll(t)==TASK_COMPLETE);int answer;assert(task_take(t,&answer));assert(answer==7);'
                        if finish else 'assert(task_drop_owned(t));')
                with self.subTest(direct=direct,finish=finish):
                    run=self.storage_probe(program,'CrustTask *t=crust_async_work_create();assert(task_poll(t)==TASK_SUSPENDED);\n              assert(observed_count==1);Cell *root=observed_cells[0];Cell *target=cell_load_ref(root,0);\n              assert(root->alive && target->alive && root->source!=target->source);\n              assert(task_poll(t)==TASK_SUSPENDED);assert(task_pool_is_empty(&crust_task_context.pool_leaf));\n              assert(root==observed_cells[0] && root->alive && cell_load_ref(root,0)==target && target->alive);\n            '+ending)
                    self.assertEqual(run.stderr.count('destroy n=7\n'),1)
                    self.assertEqual(run.stderr.count('=View\n'),1)

if __name__=='__main__':unittest.main()
