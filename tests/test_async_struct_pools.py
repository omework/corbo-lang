"""Structure slots and prepared fields outlive polls, but never their pools."""
from pathlib import Path
import unittest
from crust import compile_source
import test_select_source as sources
import test_suspended_cleanup as cleanup
import test_native_blocks as native_tests

ROOT=Path(__file__).resolve().parents[1]
POINT='struct Point{x:Int,y:Int,z:Int}'

class AsyncStructPoolTests(unittest.TestCase):
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    run_source=sources.SelectSourceTests.run_source
    refused=sources.SelectSourceTests.refused
    native=cleanup.SuspendedCleanupTests.native
    run_native=native_tests.NativeBlockTests.run_native

    @staticmethod
    def program(body,helpers='',types=POINT):
        return types+helpers+'async fn work()->Int{'+body+'''}
        fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_local_pool(self):
        source=(ROOT/'validation/open-async-result-factory-local_struct_pool.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_defaults_named_order_and_multiple_slots(self):
        source=self.program('''let mut p=pool<Point>(2);let a=p.new();print(a.x+a.y+a.z);
          let b=p.new(z:step(3).await,x:step(7).await);yield;print(b.z);return b.x+b.y;''',
          'async fn step(n:Int)->Int{print(n);yield;return n;}')
        run=self.run_source(source)
        self.assertEqual(run.stdout,'0\n3\n7\n3\n7\n')
        self.assertEqual(run.stderr.count('=Point\n'),2)

    def test_fields_reborrow_methods_and_drop(self):
        source=self.program('''let mut p=pool<Point>(1);let mut a=p.new(x:7,y:9);let mut v=&mut a.x;
          edit(v).await;print(*v);drop(->a);let b=p.new(z:11);return b.sum();''',
          'async fn edit(n:&mut Int){yield;n.set(20);}impl Point{fn sum(self:&Point)->Int{return self.x+self.y+self.z;}}')
        self.assertEqual(self.run_source(source).stdout,'20\n11\n')
        self.refused(source.replace('print(*v);drop(->a);','drop(->a);print(*v);'),'emprunt|réserv|référenc')
        self.refused(source.replace('edit(v).await;', 'let t=edit(v);print(a.x);t.await;'),'emprunt|réserv|référenc')

    def test_injected_pool_sync_async_and_alias(self):
        helpers='''fn make(p:&mut Pool<Point>,n:Int)-><-A<Point>{let a=p.new(x:n);return <-a;}
          async fn child(p:&mut Pool<Point>)-><-A<Point>{yield;return <-p.new(x:9);}
          async fn relay(a:->A<Point>)-><-A<Point>{yield;return <-a;}'''
        source=self.program('''let mut p=pool<Point>(2);let alias=&mut p;
          let a=make(alias,7);let b=child(alias).await;print(a.x);drop(->a);
          let c=relay(->b).await;return c.x;''',helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('let b=child(alias).await;', 'let t=child(alias);let other=make(alias,3);print(other.x);let b=t.await;'), 'emprunt|réserv')

    def test_parent_receiver_and_short_sources(self):
        source=self.program('''let mut p=pool<Point>(2);let mut a=p.new(x:1);
          {a=<-p.new(x:7);yield;}return a.x;''')
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('{a=<-p.new(x:7);','{let mut q=pool<Point>(1);a=<-q.new(x:7);'),'pool local|survit')
        direct='''struct Point{x:Int}async fn bad()-><-A<Point>{let mut p=pool<Point>(1);return <-p.new(x:7);}'''
        self.refused(direct,'pool local|survit|source')
        self.refused(source.replace('return a.x;', 'drop(->a);return a.x;'),'consomm|utilis|transfér')

    def test_loop_cleanup_continue_break_and_native_block(self):
        source=self.program('''let mut i=0;let n=loop{let mut p=pool<Point>(1);let a=p.new(x:i);
          yield;i=i+1;if i<3{continue;}break a.x;};return n;''')
        run=self.run_source(source);self.assertEqual(run.stdout,'2\n')
        self.assertEqual(run.stderr.count('destroy a=Point\n'),3)
        source='''struct Point{x:Int}fn main(){let h=runtime::thread({let mut p=pool<Point>(1);
          let a=p.new(x:7);return a.x;});match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_ownership_of_fields_and_cross_pool_lifetimes(self):
        types='struct Holder{before:Int,value:A<Int>,after:Int}'
        source=self.program('''let mut nums=pool<Int>(1);let mut holders=pool<Holder>(1);
          let n=nums.new(7);let h=holders.new(before:1,value:<-n,after:2);yield;
          print(*h.value);drop(->h);let next=nums.new(11);return *next;''',types=types)
        run=self.run_source(source);self.assertEqual(run.stdout,'7\n11\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.assertLess(run.stderr.index('destroy n='),run.stderr.index('destroy h='))
        self.refused(source.replace('yield;','print(*n);yield;'),'consomm|utilis|transfér')
        self.refused(source.replace('value:<-n','value:n'),'transfert|champ')
        short=self.program('''let mut holders=pool<Holder>(1);let h={let mut nums=pool<Int>(1);
          let n=nums.new(7);let h=holders.new(value:<-n);<-h};return *h.value;''',types=types)
        self.refused(short,'pool local|survit')

    def test_pending_owner_cleanup_during_later_field(self):
        source=self.program('''let mut nums=pool<Int>(1);let mut holders=pool<Holder>(1);
          let n=nums.new(7);let h=holders.new(value:<-n,after:pause().await);return h.after;''',
          'async fn pause()->Int{yield;return 9;}',types='struct Holder{value:A<Int>,after:Int}')
        run=self.run_source(source);self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        run=self.native(source,'''CrustTask *task=crust_async_work_create();int before=observed_closes;
          assert(task_poll(task)==TASK_SUSPENDED);assert(task_owned_discardable(task));
          assert(task_drop_owned(task));assert(observed_closes==before+3);''')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.assertNotIn('destroy h=',run.stderr)
        early=source.replace('pause().await','{return 42;}')
        run=self.run_source(early);self.assertEqual(run.stdout,'42\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.assertNotIn('destroy h=',run.stderr)

    def test_nested_owned_graph_and_injected_source_return(self):
        types='struct Leaf{n:A<Int>}struct Tree{left:A<Leaf>,right:A<Leaf>,total:Int}'
        helpers='async fn relay(t:->A<Tree>)-><-A<Tree>{yield;return <-t;}fn read(t:->A<Tree>)->Int{return t.total;}'
        source=self.program("""let mut nums=pool<Int>(2);let mut leaves=pool<Leaf>(2);let mut trees=pool<Tree>(1);
          let a=nums.new(7);let b=nums.new(9);let l=leaves.new(n:<-a);let r=leaves.new(n:<-b);
          let t=trees.new(left:<-l,right:<-r,total:16);let out=relay(->t).await;let n=read(->out);
          let next=nums.new(11);print(*next);return n;""",helpers,types)
        run=self.run_source(source);self.assertEqual(run.stdout,'11\n16\n')
        for name in ('a=7','b=9','l=Leaf','r=Leaf','t=Tree'):
            self.assertEqual(run.stderr.count('destroy '+name+'\n'),1)
        # Returning an allocation in an injected pool must retain that pool,
        # and also each independently injected source of its owned fields.
        factory='struct Holder{n:A<Int>}async fn make(p:&mut Pool<Holder>,n:->Int)-><-A<Holder>{\n          yield;return <-p.new(n:<-n);}fn main(){let mut nums=pool<Int>(1);let mut p=pool<Holder>(1);\n          let n=nums.new(7);let h=runtime::spawn(->make(&mut p,->n));match h.join(){Ok(v)=>{print(*v.n);drop(->v);},Err(_)=>{}}}'
        self.assertEqual(self.run_source(factory).stdout,'7\n')

    def test_fresh_graph_factory_and_short_descendant_pool(self):
        prefix='struct Holder{n:A<Int>}async fn make(p:&mut Pool<Holder>,n:->Int)-><-A<Holder>{\n          yield;return <-p.new(n:<-n);}fn prepare(p:&mut Pool<Holder>,n:->Int)-><-make{return <-make(p,->n);}\n          fn forward(t:->make)-><-make{return <-t;}'
        source=prefix+'fn main(){let mut p=pool<Holder>(1);OUTER\n          let v={INNER let n=nums.new(7);let t=forward(->prepare(&mut p,->n));let h=runtime::spawn(->t);\n            let v=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};<-v};print(*v.n);drop(->v);}'
        pool='let mut nums=pool<Int>(1);'
        self.assertEqual(self.run_source(source.replace('OUTER',pool).replace('INNER','')).stdout,'7\n')
        self.refused(source.replace('OUTER','').replace('INNER',pool),'source|pool|survit|surviv')
        asynchronous=self.program("""let mut p=pool<Holder>(1);let mut nums=pool<Int>(1);let n=nums.new(7);
          let v=prepare(&mut p,->n).await;yield;return *v.n;""",prefix,types='')
        self.assertEqual(self.run_source(asynchronous).stdout,'7\n')

    def test_scalar_snapshot_and_borrowed_arguments(self):
        helpers='async fn change(n:&mut Int)->Int{yield;n.set(20);return *n;}'
        source=self.program("""let mut nums=pool<Int>(1);let mut p=pool<Point>(1);let mut n=nums.new(7);
          let a=p.new(x:*n,y:change(&mut n).await);return a.x+a.y;""",helpers)
        self.assertEqual(self.run_source(source).stdout,'27\n')
        # A previously transferred field cannot also be captured by a later one.
        invalid=self.program('let mut nums=pool<Int>(1);let mut p=pool<Holder>(1);let mut n=nums.new(7);\n          let h=p.new(value:<-n,after:change(&mut n).await);return h.after;',helpers,
          'struct Holder{value:A<Int>,after:Int}')
        self.refused(invalid,'consomm|utilis|transfér')

    def test_scope_cycles_model(self):
        # Independent expected values/destruction count from the chosen loop lengths.
        for count in (0,1,4):
            source=self.program("""let mut i=0;let mut total=0;while i<COUNT{let mut p=pool<Point>(2);
              let a=p.new(x:i,y:i+1,z:i+2);let b=p.new(x:i+3);yield;
              total=total+a.x+a.y+a.z+b.x;i=i+1;if i<COUNT{continue;}}return total;""".replace('COUNT',str(count)))
            run=self.run_source(source)
            self.assertEqual(run.stdout,str(sum(4*i+6 for i in range(count)))+'\n')
            self.assertEqual(run.stderr.count('=Point\n'),2*count)

    def test_inactive_failed_start_and_select_loser(self):
        body='let mut p=pool<Point>(1);let a=p.new(x:7);yield;return a.x;'
        source=self.program(body)
        inactive=source[:source.index('fn main()')]+'fn main(){let t=work();drop(->t);}'
        run=self.run_source(inactive);self.assertEqual(run.stdout,'');self.assertNotIn('destroy a=',run.stderr)
        run=self.run_native(source,fail_submission_at=1)
        self.assertEqual(run.stdout,'99\n');self.assertNotIn('destroy a=',run.stderr)
        losing=source.replace('fn main()',"""async fn ready()->Int{return 9;}
          async fn select_one()->Int{let mut s=runtime::select(->work(),->ready());
            let n=s.await;drop(->s);return n;}fn main()""").replace('runtime::spawn(->work())','runtime::spawn(->select_one())')
        run=self.run_source(losing);self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('destroy a=Point\n'),1)

    def test_constructor_type_checks(self):
        source=self.program('let mut p=pool<Point>(1);let a=p.new(x:7);return a.x;')
        for before,after,reason in (
            ('let mut p','let p','mutable'),('x:7','x:true','Int'),
            ('x:7','x:7,x:9','plusieurs|doubl'),('x:7','missing:7','inconnu'),
            ('p.new(x:7)','p.new(7)','nommés|construction|type'),
            ('return a.x;','let q=<-p;return a.x;','pool|source|transfér'),
            ('let a=','let a:A<Other>=','annotation|type'),
        ):
            with self.subTest(after=after):self.refused(source.replace(before,after),reason)
        self.refused(self.program('let mut p=pool<Holder>(1);let h=p.new();return h.x;',
             types='struct Holder{x:Int,n:A<Int>}'),'défaut')

    def test_slot_identity_capacity_and_suspended_cleanup(self):
        source=self.program('''let mut p=pool<Point>(2);let a=p.new(x:7,y:8,z:9);
          let b=p.new(x:11,y:12,z:13);yield;drop(->a);let c=p.new(x:21,y:22,z:23);
          yield;return b.x+c.z;''')
        code=compile_source(source)
        # Probe the public ABI and logical values, not the allocator's free-list algorithm.
        hook='static Cell *enum_new(Source *source, size_t tag, const char *label) {'
        self.assertEqual(code.count(hook),1)
        # A typed source closes its wrapper and its one arm.
        for finish in (False,True):
            terminal=('assert(task_poll(task)==TASK_COMPLETE);int n;assert(task_take(task,&n));assert(n==34);'
                      if finish else 'assert(task_drop_owned(task));')
            run=self.native(source,'''CrustTask *task=crust_async_work_create();int before=observed_closes;
              assert(task_poll(task)==TASK_SUSPENDED);crust_async_work_state *frame=(crust_async_work_state*)task;
              Cell *a=frame->value_1;Cell *b=frame->value_2;assert(a!=b);
              assert(cell_load_int(a,0)==7);assert(cell_load_int(b,2*sizeof(int))==13);
              assert(task_poll(task)==TASK_SUSPENDED);Cell *c=frame->value_3;assert(c==a);
              assert(b->alive && cell_load_int(b,sizeof(int))==12);assert(cell_load_int(c,2*sizeof(int))==23);
            '''+terminal+'''assert(observed_closes==before+2);''')
            self.assertEqual(run.stderr.count('=Point\n'),3)
        overflow=source.replace('yield;drop(->a);','yield;print(a.x);')
        run=self.run_c_oracle(compile_source(overflow),expected_error='pool capacity exceeded')
        self.assertEqual(run.returncode,1)

if __name__=='__main__':unittest.main()
