"""Fresh local roots retain independently pooled descendants across task returns."""
from pathlib import Path
import unittest
import test_select_source as sources
import test_async_result_storage as storage
import test_native_blocks as native

ROOT=Path(__file__).resolve().parents[1]
PREFIX='''struct Holder{data:A<Int>}
fn wrap(n:->A<Int>)-><-Holder{let v=Holder{data:<-n};return <-v;}
async fn leaf(n:->A<Int>)-><-Holder{let v=wrap(->n);yield;return <-v;}'''
class AsyncLocalOwnedResultGraphTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    run_native=native.NativeBlockTests.run_native
    storage_probe=storage.AsyncResultStorageTests.storage_probe

    @staticmethod
    def program(body,helpers=''):
        return PREFIX+helpers+'async fn work()->Int{'+body+'''}fn main(){let h=runtime::spawn(->work());
        match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_local_owned_result(self):
        source=(ROOT/'validation/open-async-result-storage-owned.crb').read_text()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.assertEqual(run.stderr.count('destroy v=Holder\n'),1)

    def test_async_caller_parent_and_relay(self):
        helper='async fn relay(n:->A<Int>)-><-Holder{let v=leaf(->n).await;yield;return <-v;}'
        for creation in ('let v=leaf(->n).await;', 'let t=leaf(->n);let v=t.await;', 'let v=relay(->n).await;'):
            source=self.program('let mut ns=pool<Int>(1);let n=ns.new(7);let result={'+creation+'<-v};yield;return *result.data;',helper)
            with self.subTest(creation=creation):
                self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_short_pool_rejected_before_and_after_wait(self):
        for body in (
            'let v={let mut ns=pool<Int>(1);let n=ns.new(7);let v=leaf(->n).await;<-v};return *v.data;',
            'let t={let mut ns=pool<Int>(1);let n=ns.new(7);let t=leaf(->n);<-t};let v=t.await;return *v.data;'):
            self.refused(self.program(body),'pool|source|survi|durable')
        source=PREFIX+'''fn main(){let v={let mut ns=pool<Int>(1);let n=ns.new(7);
          let h=runtime::spawn(->leaf(->n));let v=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};<-v};print(*v.data);}'''
        self.refused(source,'pool|source|survi|durable')

    def test_factory_and_result_source(self):
        helpers='fn prepare(n:->A<Int>)-><-leaf{return <-leaf(->n);}fn relay(t:->leaf)-><-leaf{return <-t;}'
        source=PREFIX+helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
          let t=relay(->prepare(->n));let h=runtime::spawn(->t);
          let v=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};print(*v.data);drop(->v);
          let next=ns.new(9);print(*next);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        short=source.replace('let mut ns=pool<Int>(1);','let v={let mut ns=pool<Int>(1);').replace(
          ';print(*v.data);drop(->v);\n          let next=ns.new(9);print(*next);', ';<-v};print(*v.data);')
        self.refused(short,'pool|source|survi|durable')

    def test_result_field_borrow_then_drop(self):
        source=self.program('let mut ns=pool<Int>(1);let n=ns.new(7);let v=leaf(->n).await;\n          let view=&*v.data;yield;print(*view);drop(->v);let next=ns.new(9);return *next;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('print(*view);drop(->v);','drop(->v);print(*view);'),'emprunt|réserv|référenc')

    def test_branches_loops_and_replacement(self):
        for count in (1,3):
            body='''let mut ns=pool<Int>(2);let first=ns.new(1);let mut v=leaf(->first).await;let mut i=0;
              while i<COUNT{let n=ns.new(i+2);{v=<-leaf(->n).await;}print(*v.data);i=i+1;}
              drop(->v);let next=ns.new(9);return *next;'''.replace('COUNT',str(count))
            run=self.run_source(self.program(body))
            self.assertEqual(run.stdout,''.join(f'{n}\n' for n in range(2,count+2))+'9\n')
            self.assertEqual(run.stderr.count('=Holder\n'),count+1)

    def test_inactive_and_launch_failure_destroy_captured_owner(self):
        source=PREFIX+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let t=leaf(->n);
          ACTION let next=ns.new(9);print(*next);}'''
        self.assertEqual(self.run_source(source.replace('ACTION','drop(->t);')).stdout,'9\n')
        launched=source.replace('ACTION','let h=runtime::spawn(->t);match h.join(){Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{print(99);}}')
        for failure,output in ((None,'7\n9\n'),(1,'99\n9\n')):
            run=self.run_native(launched,fail_submission_at=failure)
            self.assertEqual(run.stdout,output)
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)

    def test_type_and_short_local_child_pool(self):
        source=PREFIX.replace('async fn leaf(n:->A<Int>)-><-Holder','async fn leaf(n:->A<Int>)-><-A<Holder>')+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->leaf(->n));
          match h.join(){Ok(v)=>{print(*v.data);},Err(_)=>{}}}'''
        self.refused(source,'A<T>|allocation|local|type')
        invalid='''struct Holder{data:A<Int>}async fn bad()-><-Holder{let mut ns=pool<Int>(1);let n=ns.new(7);
          let v=Holder{data:<-n};return <-v;}'''
        self.refused(invalid,'pool|source|survi|propriétaires|provenance|local')

    def test_conditional_targets_and_discarded_alternative(self):
        helper='async fn choose(a:->A<Int>,b:->A<Int>,flag:Bool)-><-Holder{if flag{a ->;return <-wrap(->a);}yield;return <-wrap(->b);}'
        for flag,expected in (('true',7),('false',9)):
            body='let mut ps=pool<Int>(1);let mut qs=pool<Int>(1);let a=ps.new(7);let b=qs.new(9);let v=choose(->a,->b,FLAG).await;return *v.data;'.replace('FLAG',flag)
            run=self.run_source(self.program(body,helper))
            self.assertEqual(run.stdout,f'{expected}\n')
            self.assertEqual(run.stderr.count('destroy a=7\n'),1)
            self.assertEqual(run.stderr.count('destroy b=9\n'),1)
            short=body.replace('let mut qs=', 'let v={let mut qs=').replace('return *v.data;', '<-v};return *v.data;')
            self.refused(self.program(short,helper),'pool|source|survi|durable')

    def test_nested_owned_descendant_sources(self):
        source='struct Leaf{data:A<Int>}struct Root{child:A<Leaf>,tag:Int}\n          fn wrap_leaf(l:->A<Leaf>)-><-Root{let r=Root{child:<-l,tag:11};return <-r;}\n          async fn make(l:->A<Leaf>)-><-Root{let r=wrap_leaf(->l);yield;return <-r;}\n          fn prepare(l:->A<Leaf>)-><-make{return <-make(->l);}\n          fn main(){let mut ns=pool<Int>(1);let mut ls=pool<Leaf>(1);\n            let n=ns.new(7);let l=ls.new(data:<-n);let h=runtime::spawn(->prepare(->l));\n            let r=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};print(r.tag);drop(->r);\n            let next=ns.new(9);print(*next);}'
        run=self.run_source(source)
        self.assertEqual(run.stdout,'11\n9\n')
        for name in ('n=7','l=Leaf','r=Root'):
            self.assertEqual(run.stderr.count('destroy '+name+'\n'),1)
        short=source.replace('fn main(){let mut ns=', 'fn main(){let r={let mut ns=').replace(
            ';print(r.tag);drop(->r);\n            let next=ns.new(9);print(*next);',';<-r};print(r.tag);')
        self.refused(short,'pool|source|survi|durable')

    def test_each_descendant_pool_must_survive_result(self):
        helpers='struct Leaf{data:A<Int>}struct Root{child:A<Leaf>,tag:Int}\n          fn wrap_leaf(l:->A<Leaf>)-><-Root{let r=Root{child:<-l,tag:11};return <-r;}\n          async fn make(l:->A<Leaf>)-><-Root{let r=wrap_leaf(->l);yield;return <-r;}\n          async fn relay(l:->A<Leaf>)-><-Root{return <-make(->l).await;}\n          fn prepare(l:->A<Leaf>)-><-make{return <-make(->l);}'
        for factory in ('make','prepare','relay'):
            for int_outer in (False,True):
                for leaf_outer in (False,True):
                    outer='';inner=''
                    for outside,pool in ((int_outer,'let mut ns=pool<Int>(1);'),(leaf_outer,'let mut ls=pool<Leaf>(1);')):
                        if outside:outer+=pool
                        else:inner+=pool
                    source=helpers+'fn main(){'+outer+'let result={'+inner+'\n                      let n=ns.new(7);let l=ls.new(data:<-n);let h=runtime::spawn(->FACTORY(->l));\n                      let r=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};<-r};print(result.tag);}'.replace('FACTORY',factory)
                    with self.subTest(factory=factory,int_outer=int_outer,leaf_outer=leaf_outer):
                        if int_outer and leaf_outer:
                            self.assertEqual(self.run_source(source).stdout,'11\n')
                        else:
                            self.refused(source,'pool|source|survi|durable')

    def test_identity_and_suspended_cleanup(self):
        source=self.program('let mut ns=pool<Int>(1);let n=ns.new(7);let v=leaf(->n).await;yield;return *v.data;')
        for finish in (False,True):
            ending=('assert(task_poll(t)==TASK_COMPLETE);int answer;assert(task_take(t,&answer));assert(answer==7);'
                    if finish else 'assert(task_drop_owned(t));')
            run=self.storage_probe(source,'\n              CrustTask *t=crust_async_work_create();assert(task_poll(t)==TASK_SUSPENDED);\n              assert(observed_count==1);Cell *root=observed_cells[0];Cell *child=cell_load_ref(root,0);\n              Source *root_source=root->source;Source *child_source=child->source;\n              assert(root_source!=child_source && root_source->stack && child_source->pool);\n              assert(root->alive && child->alive && child->value==7);\n              assert(task_poll(t)==TASK_SUSPENDED);assert(task_pool_is_empty(&crust_task_context.pool_leaf));\n              assert(root==observed_cells[0] && root->alive && cell_load_ref(root,0)==child && child->alive);\n            '+ending)
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)
            self.assertEqual(run.stderr.count('destroy v=Holder\n'),1)

if __name__=='__main__':unittest.main()
