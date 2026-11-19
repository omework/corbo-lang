"""Structure references cross task boundaries without copying their storage."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncStructCaptureTests(unittest.TestCase):
    run_c_oracle = native.NativeBlockTests.run_c_oracle
    run_native = native.NativeBlockTests.run_native

    @staticmethod
    def wrap(work, main, helpers=''):
        return 'struct Point{x:Int,y:Int}\n'+helpers+work+'fn main(){'+main+'}'

    def test_recorded_direct_and_feature_method_capture(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('open-async-struct-reference','open-feature-async-structure'):
            with self.subTest(name=name):
                run=self.run_native((root/'validation'/f'{name}.crb').read_text())
                self.assertEqual(run.stdout,'7\n')

    def test_mutable_fields_and_nested_layout(self):
        source='''struct Point{x:Int,y:Int} struct Pair{left:Point,right:Point}
          async fn work(p:&mut Pair)->Int{p.left.x=p.right.y+1;yield;
            p.right.x=p.left.x+2;return p.left.x+p.right.x;}
          fn main(){let mut p=Pair{};p.left.x=1;p.left.y=2;p.right.x=3;p.right.y=4;
            let h=runtime::spawn(->work(&mut p));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
            print(p.left.x);print(p.left.y);print(p.right.x);print(p.right.y);}'''
        self.assertEqual(self.run_native(source).stdout,'12\n5\n2\n7\n4\n')
        with self.assertRaises(Error):verify_program(source.replace('p:&mut Pair','p:&Pair').replace('work(&mut p)','work(&p)'))

    def test_caller_exclusivity_and_last_wait(self):
        work='async fn work(p:&mut Point)->Int{yield;p.x=p.x+1;return p.x;}'
        main='''let mut p=Point{x:7,y:9};let t=work(&mut p);BEFORE
          let h=runtime::spawn(->t);RUNNING match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          p.y=11;print(p.x);print(p.y);'''
        self.assertEqual(self.run_native(self.wrap(work,main.replace('BEFORE','').replace('RUNNING',''))).stdout,'8\n8\n11\n')
        for at in ('BEFORE','RUNNING'):
            for operation in ('print(p.x);','p.y=3;','drop(->p);','let second=work(&mut p);drop(->second);'):
                with self.subTest(at=at,operation=operation),self.assertRaises(Error):
                    verify_program(self.wrap(work,main.replace(at,operation).replace('BEFORE','').replace('RUNNING','')))

    def test_shared_captures_coexist_and_block_writes(self):
        source=self.wrap('async fn work(p:&Point)->Int{yield;return p.x;}',
          '''let mut p=Point{x:7,y:9};let a=work(&p);let b=work(&p);print(p.y);
          let h=runtime::spawn(->a);match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          BEFORE let k=runtime::spawn(->b);match k.join(){Ok(n)=>{print(n);},Err(_)=>{}}p.x=11;print(p.x);''')
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'9\n7\n7\n11\n')
        with self.assertRaises(Error):verify_program(source.replace('BEFORE','p.x=10;'))

    def test_pool_identity_drop_and_reuse(self):
        source=self.wrap('async fn work(p:&mut Point)->Int{yield;p.x=8;return p.y;}',
          '''let mut points=pool<Point>(1);let mut p=points.new(x:7,y:9);address(p);
          let h=runtime::spawn(->work(&mut p));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
          address(p);print(p.x);drop(->p);let q=points.new(x:1,y:2);address(q);print(q.x);''')
        run=self.run_native(source)
        first,n,same,x,reused,last=run.stdout.splitlines()
        self.assertEqual((n,same,x,reused,last),('9',first,'8',first,'1'))
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy p=Point','destroy q=Point'])

    def test_escape_and_inactive_drop(self):
        work='async fn work(p:&Point)->Int{print(p.x);yield;return p.y;}'
        valid=self.wrap(work,'let p=Point{x:7,y:9};let t=work(&p);drop(->t);drop(->p);')
        self.assertEqual(self.run_native(valid).stdout,'')
        invalid=self.wrap(work,'let t={let p=Point{x:7,y:9};let t=work(&p);<-t};drop(->t);')
        with self.assertRaises(Error):verify_program(invalid)

    def test_relay_reborrow_and_child_lifetime(self):
        work='''async fn leaf(p:&mut Point)->Int{yield;p.x=p.x+1;return p.x;}
          async fn work(p:&mut Point)->Int{let mut view=&mut *p;let child=leaf(view);
            BEFORE let n=child.await;view.y=n+1;return p.y;}'''
        main='''let mut p=Point{x:7,y:9};let h=runtime::spawn(->work(&mut p));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(p.x);print(p.y);'''
        self.assertEqual(self.run_native(self.wrap(work.replace('BEFORE',''),main)).stdout,'9\n8\n9\n')
        for operation in ('print(p.x);','view.x=3;'):
            with self.assertRaises(Error):verify_program(self.wrap(work.replace('BEFORE',operation),main))

    def test_sync_helpers_and_methods(self):
        helpers='''fn sum(p:&Point)->Int{return p.x+p.y;}
          fn put(p:&mut Point,n:Int){p.x=n;}
          impl Point{fn sum(self:&Point)->Int{return self.x+self.y;}
            fn put(self:&mut Point,n:Int){self.y=n;}}'''
        work='''async fn work(p:&mut Point)->Int{let n=sum(p);put(p,n);yield;p.put(n+1);return p.sum();}'''
        main='''let mut p=Point{x:7,y:9};let h=runtime::spawn(->work(&mut p));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(p.x);print(p.y);'''
        self.assertEqual(self.run_native(self.wrap(work,main,helpers)).stdout,'33\n16\n17\n')
        with self.assertRaises(Error):verify_program(self.wrap(work.replace('return p.sum();','p.sum();return 0;'),main,helpers))

    def test_native_block_capture_and_launch_failure(self):
        source=self.wrap('', '''let mut p=Point{x:7,y:9};let view=&mut p;
          let h=runtime::thread({->(view);view.x=11;return view.x+view.y;});
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}print(p.x);''')
        for failure,expected in ((None,'20\n11\n'),(1,'99\n7\n')):
            run=self.run_native(source,fail_at=failure)
            self.assertEqual(run.stdout,expected)
            self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                             ['destroy p=Point'])

    def test_type_mismatch_and_scalar_shortcuts_rejected(self):
        base=self.wrap('async fn work(p:&mut Point)->Int{OP return p.x;}',
          'let mut p=Point{x:7,y:9};let h=runtime::spawn(->work(&mut p));match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}')
        for operation in ('print(*p);','p.set(7);','p.x=true;','print(p.missing);','let v=&p;'):
            with self.subTest(operation=operation),self.assertRaises(Error):verify_program(base.replace('OP',operation))
        wrong=base.replace('OP','').replace('let mut p=Point{x:7,y:9};','let mut p=8;')
        with self.assertRaises(Error):verify_program(wrong)

    def test_export_child_out_of_alias_block_preserves_root_loan(self):
        work='''async fn leaf(p:&mut Point)->Int{yield;p.x=11;return p.x;}
          async fn work(p:&mut Point)->Int{let child={let view=&mut *p;let t=leaf(view);<-t};
            BEFORE let n=child.await;p.y=n;return p.y;}'''
        main='''let mut p=Point{x:7,y:9};let h=runtime::spawn(->work(&mut p));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(p.x);'''
        self.assertEqual(self.run_native(self.wrap(work.replace('BEFORE',''),main)).stdout,'11\n11\n')
        for operation in ('print(p.x);','p.x=3;'):
            with self.assertRaises(Error):verify_program(self.wrap(work.replace('BEFORE',operation),main))

    def test_helper_returns_struct_reference_and_argument_order(self):
        helpers='''fn same(p:&mut Point)->&mut Point{return p;}
          fn read(p:&Point)->Int{return p.x;}
          fn put(p:&mut Point,n:Int){p.x=n;}
          fn ordered(n:Int,p:&mut Point){p.y=n;}'''
        work='''async fn work(p:&mut Point)->Int{let mut view=same(p);view.x=11;yield;
          let n=read(view);ordered(n,p);return p.x+p.y;}'''
        main='''let mut p=Point{x:7,y:9};let h=runtime::spawn(->work(&mut p));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}'''
        self.assertEqual(self.run_native(self.wrap(work,main,helpers)).stdout,'22\n')
        self.assertEqual(self.run_native(self.wrap(work.replace('let mut view','let view'),main,helpers)).stdout,'22\n')
        for old,new in (('ordered(n,p);','put(p,read(p));'),
                        ('yield;','print(p.x);yield;')):
            with self.subTest(new=new),self.assertRaises(Error):verify_program(self.wrap(work.replace(old,new),main,helpers))

    def test_nominal_types_in_child_and_helper_arguments(self):
        source='''struct Point{x:Int}struct Other{x:Int}
          async fn leaf(p:&Point)->Int{return p.x;}
          fn read(p:&Point)->Int{return p.x;}
          async fn bad(q:&Other)->Int{return CALL;}'''
        for call in ('leaf(q).await','read(q)'):
            with self.subTest(call=call),self.assertRaises(Error):verify_program(source.replace('CALL',call))

    def test_shared_reborrow_keeps_mutable_parent_suspended(self):
        work='''async fn leaf(p:&Point)->Int{yield;return p.x;}
          async fn work(p:&mut Point)->Int{let view=&*p;let child=leaf(view);
            BEFORE let n=child.await;p.y=n+1;return p.y;}'''
        main='''let mut p=Point{x:7,y:9};let h=runtime::spawn(->work(&mut p));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(p.y);'''
        self.assertEqual(self.run_native(self.wrap(work.replace('BEFORE',''),main)).stdout,'8\n8\n')
        for operation in ('print(p.x);','p.y=3;'):
            with self.subTest(operation=operation),self.assertRaises(Error):verify_program(self.wrap(work.replace('BEFORE',operation),main))
        dropped=work.replace('BEFORE','').replace('let n=child.await;','drop(->child);let n=p.x;')
        self.assertEqual(self.run_native(self.wrap(dropped,main)).stdout,'8\n8\n')


if __name__=='__main__':unittest.main()
