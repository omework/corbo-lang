"""Stored reference dependencies follow carriers across scopes and suspension."""
from pathlib import Path
import unittest
from crust import verify_program
import test_select_source as sources
import test_suspended_cleanup as cleanup

ROOT=Path(__file__).resolve().parents[1]

class AsyncBorrowedStructPoolTests(unittest.TestCase):
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    run_source=sources.SelectSourceTests.run_source
    refused=sources.SelectSourceTests.refused
    native=cleanup.SuspendedCleanupTests.native

    @staticmethod
    def program(body,helpers='',types='struct View{data:&Int}'):
        return types+helpers+'async fn work()->Int{'+body+'''}fn main(){let h=runtime::spawn(->work());
        match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded(self):
        source=(ROOT/'validation/open-async-struct-pool-borrowed-field.crb').read_text()+'''
        fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_shared_target_drop_and_last_use(self):
        prefix='let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let n=ns.new(7);let v=vs.new(data:&n);yield;'
        source=self.program(prefix+'print(*v.data);drop(->v);drop(->n);let next=ns.new(9);return *next;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(self.program(prefix+'drop(->n);return *v.data;'),'emprunt|réserv')
        # No later explicit use of the carrier: its stored reference has ended.
        source=self.program(prefix+'print(*v.data);drop(->n);return 9;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')

    def test_shared_projection_detaches_but_target_remains(self):
        prefix='let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let n=ns.new(7);let v=vs.new(data:&n);'
        source=self.program(prefix+'let w=v.data;drop(->v);yield;print(*w);drop(->n);return 9;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('yield;print(*w);drop(->n);','drop(->n);yield;print(*w);'),'emprunt|réserv')

    def test_mutable_reborrow_exclusivity_and_last_use(self):
        prefix='let mut ns=pool<Int>(1);let mut vs=pool<Writer>(1);let mut n=ns.new(7);let mut v=vs.new(data:&mut n);'
        body=prefix+'let mut w=&mut *v.data;edit(w).await;print(*w);drop(->v);return *n;'
        helpers='async fn edit(n:&mut Int){yield;n.set(20);}'
        source=self.program(body,helpers,types='struct Writer{data:&mut Int}')
        self.assertEqual(self.run_source(source).stdout,'20\n20\n')
        for fragment in ('print(*n);','drop(->v);','let mut again=&mut *v.data;again.set(30);'):
            self.refused(source.replace('edit(w).await;',fragment+'edit(w).await;'),'emprunt|réserv')

    def test_constructor_arguments_keep_loans_across_suspend(self):
        body='let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let mut n=ns.new(7);let v=vs.new(data:&n,number:pause().await);return *v.data+v.number;'
        helpers='async fn pause()->Int{yield;return 9;}async fn edit(n:&mut Int)->Int{yield;n.set(30);return 9;}'
        source=self.program(body,helpers,types='struct View{data:&Int,number:Int}')
        self.assertEqual(self.run_source(source).stdout,'16\n')
        self.refused(source.replace('number:pause().await','number:edit(&mut n).await'),'emprunt|réserv')
        self.refused(source.replace('let v=vs.new(data:&n,','print(*n);let v=vs.new('),'défaut')
        run=self.native(source,'''CrustTask *t=crust_async_work_create();assert(task_poll(t)==TASK_SUSPENDED);
          assert(task_drop_owned(t));''')
        self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.assertNotIn('destroy v=',run.stderr)

    def test_receiver_transfer_and_short_target(self):
        body='let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let n=ns.new(7);let v={let a=vs.new(data:&n);yield;<-a};return *v.data;'
        self.assertEqual(self.run_source(self.program(body)).stdout,'7\n')
        moved=body.replace('let n=ns.new(7);let v={','let v={let n=ns.new(7);')
        self.refused(self.program(moved),'emprunt|durable|survit')
        self.refused(self.program(body.replace('return *v.data;','drop(->n);return *v.data;')),'emprunt|réserv')
        renamed=body.replace('return *v.data;','let autre=<-v;yield;return *autre.data;')
        self.assertEqual(self.run_source(self.program(renamed)).stdout,'7\n')

    def test_branch_result_protects_both_targets(self):
        body='''let mut ns=pool<Int>(2);let mut vs=pool<View>(1);let a=ns.new(7);let b=ns.new(9);
          let v=if FLAG{let v=vs.new(data:&a);yield;<-v}else{let v=vs.new(data:&b);yield;<-v};
          print(*v.data);drop(->v);drop(->a);drop(->b);return 11;'''
        for flag,value in (('true',7),('false',9)):
            source=self.program(body.replace('FLAG',flag));self.assertEqual(self.run_source(source).stdout,f'{value}\n11\n')
            for target in ('a','b'):
                self.refused(source.replace('print(*v.data);',f'drop(->{target});print(*v.data);'),'emprunt|réserv')

    def test_direct_and_helper_field_replacement(self):
        prefix='let mut ns=pool<Int>(2);let mut vs=pool<View>(1);let a=ns.new(7);let b=ns.new(9);let mut v=vs.new(data:&a);'
        helpers='fn change(v:&mut View,n:&Int){v.data=&*n;}async fn child(v:&mut View,n:&Int){yield;change(v,n);}'
        for write in ('v.data=&b;','change(&mut v,&b);','child(&mut v,&b).await;'):
            source=self.program(prefix+write+'drop(->a);yield;print(*v.data);drop(->v);drop(->b);return 11;',helpers)
            with self.subTest(write=write):
                self.assertEqual(self.run_source(source).stdout,'9\n11\n')
                self.refused(source.replace('yield;print(*v.data);','drop(->b);yield;print(*v.data);'),'emprunt|réserv')

    def test_loop_receivers_and_field_target_fixed_point(self):
        prefix='let mut ns=pool<Int>(2);let mut vs=pool<View>(1);let a=ns.new(7);let b=ns.new(9);'
        source=self.program(prefix+"""let v=loop{let v=vs.new(data:&a);yield;break <-v;};
          print(*v.data);drop(->v);drop(->a);return *b;""")
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('print(*v.data);','drop(->a);print(*v.data);'),'emprunt|réserv')
        for count in (0,1,3):
            body=prefix+"""let mut v=vs.new(data:&a);let mut i=0;while i<COUNT{
              print(*v.data);v.data=&b;yield;i=i+1;if i<COUNT{continue;}}
              print(*v.data);drop(->v);drop(->a);drop(->b);return i;""".replace('COUNT',str(count))
            run=self.run_source(self.program(body))
            self.assertEqual(run.stdout,('7\n'+'9\n'*count)+str(count)+'\n')
            self.refused(self.program(body.replace('print(*v.data);drop(->v);','drop(->b);print(*v.data);drop(->v);')),'emprunt|réserv')

    def test_mutable_fields_disjoint_and_shared_reborrow(self):
        body="""let mut ns=pool<Int>(2);let mut ps=pool<Pair>(1);let mut a=ns.new(7);let mut b=ns.new(9);
          let mut p=ps.new(left:&mut a,right:&mut b);let mut x=&mut *p.left;let mut y=&mut *p.right;
          edit(x).await;edit(y).await;print(*x);print(*y);drop(->p);return *a+*b;"""
        helpers='async fn edit(n:&mut Int){yield;n.set(20);}'
        types='struct Pair{left:&mut Int,right:&mut Int}'
        source=self.program(body,helpers,types)
        self.assertEqual(self.run_source(source).stdout,'20\n20\n40\n')
        self.refused(source.replace('right:&mut b','right:&mut a'),'emprunt|réserv')
        self.refused(source.replace('let mut y=&mut *p.right','let mut y=&mut *p.left'),'emprunt|réserv')

    def test_saved_old_target_and_scope_restoration(self):
        prefix='let mut ns=pool<Int>(2);let mut vs=pool<View>(1);let a=ns.new(7);let b=ns.new(9);let mut v=vs.new(data:&a);'
        source=self.program(prefix+'let old=v.data;v.data=&b;yield;print(*old);drop(->a);return *v.data;')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('print(*old);drop(->a);','drop(->a);print(*old);'),'emprunt|réserv')
        body='let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let a=ns.new(7);let mut v=vs.new(data:&a);'
        body+='{let mut inner=pool<Int>(1);let b=inner.new(9);v.data=&b;yield;print(*v.data);RESTORE}return *v.data;'
        self.assertEqual(self.run_source(self.program(body.replace('RESTORE','v.data=&a;'))).stdout,'9\n7\n')
        self.refused(self.program(body.replace('RESTORE','')),'emprunt|durable|survit')

    def test_injected_target_descriptor_and_borrowed_child(self):
        helper='struct View{data:&Int}async fn read(v:&View)->Int{yield;return *v.data;}\n          async fn work(n:&Int)->Int{let mut vs=pool<View>(1);let v=vs.new(data:n);\n            let t=read(&v);let r=t.await;drop(->v);return r;}\n          fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->work(&n));\n            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'
        self.assertEqual(self.run_source(helper).stdout,'7\n')
        self.refused(helper.replace('let r=t.await;drop(->v);','drop(->v);let r=t.await;'),'emprunt|réserv')

    def test_returned_shared_reference_after_carrier_drop(self):
        source='struct View{data:&Int}fn expose(v:&View)->&Int{return v.data;}\n          async fn leaf(n:&Int)->&Int{let mut vs=pool<View>(1);let v=vs.new(data:n);\n            let w=expose(&v);drop(->v);yield;return w;}\n          fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->leaf(&n));\n            let w=match h.join(){Ok(v)=>{v},Err(_)=>{return;}};BEFORE print(*w);drop(->n);}'
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'7\n')
        self.refused(source.replace('BEFORE','drop(->n);'),'emprunt|réserv|référenc')
        local='struct View{data:&Int}async fn bad()->&Int{let mut ns=pool<Int>(1);let n=ns.new(7);\n          let mut vs=pool<View>(1);let v=vs.new(data:&n);return v.data;}'
        self.refused(local,'local|durable|origine|paramètre')

    def test_parent_replacement_and_suspended_destruction(self):
        body='let mut ns=pool<Int>(2);let mut vs=pool<View>(2);let a=ns.new(7);let b=ns.new(9);\n          let mut v=vs.new(data:&a);{v=<-vs.new(data:&b);yield;}drop(->a);print(*v.data);drop(->v);return *b;'
        source=self.program(body)
        self.assertEqual(self.run_source(source).stdout,'9\n9\n')
        self.refused(source.replace('print(*v.data);','drop(->b);print(*v.data);'),'emprunt|réserv')
        run=self.native(source,'CrustTask *t=crust_async_work_create();assert(task_poll(t)==TASK_SUSPENDED);\n          assert(task_drop_owned(t));')
        self.assertEqual(run.stderr.count('destroy a=7\n'),1)
        self.assertEqual(run.stderr.count('destroy b=9\n'),1)
        self.assertEqual(run.stderr.count('=View\n'),2)

    def test_live_task_and_alias_keep_carrier_targets(self):
        invalid=(ROOT/'validation/rejected-async-local-view-task-target.crb').read_text()
        self.refused(invalid,'emprunt|réserv')
        valid=invalid.replace('drop(->n);let r=t.await;','let r=t.await;drop(->n);')
        self.assertEqual(self.run_source(valid).stdout,'7\n')
        # A launched task and a plain carrier alias retain the same dependency.
        launched=invalid.replace('let t=read(&v);','let t=runtime::spawn(->read(&v));').replace(
          'let r=t.await;return r;', 'match t.await{Ok(r)=>{return r;},Err(_)=>{return 99;}}')
        self.refused(launched,'emprunt|réserv')
        alias=invalid.replace('let t=read(&v);drop(->n);let r=t.await;',
          'let alias=&v;drop(->n);let r=*alias.data;')
        self.refused(alias,'emprunt|réserv')
        valid_alias=alias.replace('let alias=&v;drop(->n);let r=*alias.data;', 'let alias=&v;let r=*alias.data;drop(->n);')
        self.assertEqual(self.run_source(valid_alias).stdout,'7\n')
        disjoint=self.program('let mut ns=pool<Int>(1);let mut vs=pool<View>(1);let n=ns.new(7);\n          let v=vs.new(data:&n,number:11);let keep=&v.number;drop(->n);yield;return *keep;',types='struct View{data:&Int,number:Int}')
        self.assertEqual(self.run_source(disjoint).stdout,'11\n')

if __name__=='__main__':unittest.main()
