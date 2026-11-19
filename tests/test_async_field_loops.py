"""Field target fixed points across async loop backedges."""
from itertools import product
import unittest
from crust import verify_program,compile_source
import test_async_field_application as application

BASE='''struct View{data:&Int}fn change(v:&mut View,n:&Int){v.data=&*n;}
 async fn child(v:&mut View,n:&Int)->Int{change(v,n);yield;return *v.data;}
'''
class AsyncFieldLoopTests(unittest.TestCase):
    run_native=application.AsyncFieldApplicationTests.run_native
    run_c_oracle=application.AsyncFieldApplicationTests.run_c_oracle
    refused=application.AsyncFieldApplicationTests.refused
    program=staticmethod(application.AsyncFieldApplicationTests.program)

    def test_while_zero_one_and_many_iterations(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&Int,limit:Int)->Int{
          let mut i=0;while i<limit{print(*v.data);v.data=&*n;i=i+1;yield;}return *v.data;}'''
        for count in (0,1,3):
            source=self.program('let h=runtime::spawn(->work(&mut v,&b,'+str(count)+'''));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
            expected=('7\n'+'9\n'*(count-1) if count else '')+('9\n9\n' if count else '7\n7\n')
            self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n'+expected)
            self.refused(source.replace('BEFORE','drop(->b);'))

    def test_continue_and_child_wait(self):
        for store in ('change(v,n);','v.data=&*n;','let value=child(v,n).await;print(value);'):
            helpers=BASE+'''async fn work(v:&mut View,n:&Int)->Int{let mut i=0;
              loop{if i==3{break;}print(*v.data);'''+store+'''i=i+1;yield;continue;}
              return *v.data;}'''
            source=self.program('''let h=runtime::spawn(->work(&mut v,&b));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
            expected='11\n7\n9\n9\n9\n9\n' if 'await' not in store else '11\n7\n9\n9\n9\n9\n9\n9\n9\n'
            self.assertEqual(self.run_native(source).stdout,expected)

    def test_backedge_reserves_new_target_before_next_iteration(self):
        helpers=BASE+'''async fn work(v:&mut View,n:&mut Int)->Int{let mut i=0;
          while i<3{BEFORE v.data=&*n;i=i+1;yield;}return *v.data;}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&mut b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        for access in ('print(*n);','n.set(20);'):
            self.refused(source.replace('BEFORE',access))
        # Shared input permits repeated reads and captures at each iteration.
        safe=source.replace('n:&mut Int','n:&Int').replace('work(&mut v,&mut b)','work(&mut v,&b)').replace('BEFORE','print(*n);')
        self.assertEqual(self.run_native(safe).stdout,'11\n9\n9\n9\n9\n9\n')

    def test_nested_loops_and_early_return(self):
        helpers=BASE+'''async fn work(v:&mut View,a:&Int,b:&Int)->Int{
          let mut i=0;while i<2{let mut j=0;while j<2{
            print(*v.data);if j==0{v.data=&*a;}else{v.data=&*b;}
            j=j+1;yield;}i=i+1;}return *v.data;}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b,&c));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source.replace('BEFORE','')).stdout,'11\n7\n9\n11\n9\n11\n11\n')
        for target in ('b','c'):
            self.refused(source.replace('BEFORE',f'drop(->{target});'))
        early=source.replace('j=j+1;yield;','if i==1{return *v.data;}j=j+1;yield;').replace('BEFORE','')
        self.assertEqual(self.run_native(early).stdout,'11\n7\n9\n11\n9\n9\n')

    def test_swapped_fields_keep_capture_time_cells(self):
        helpers='''struct Pair{left:&Int,right:&Int}
          fn swap(v:&mut Pair){let old=v.left;v.left=v.right;v.right=&*old;}
          async fn work(v:&mut Pair)->Int{let mut i=0;while i<3{
            swap(v);yield;print(*v.left);print(*v.right);i=i+1;}return *v.left;}'''
        source=helpers+'''fn main(){let mut p=pool<Int>(2);let a=p.new(7);let b=p.new(9);
          let mut v=Pair{left:&a,right:&b};let h=runtime::spawn(->work(&mut v));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.left);print(*v.right);}'''
        self.assertEqual(self.run_native(source).stdout,'9\n7\n7\n9\n9\n7\n9\n9\n7\n')
        self.refused(source.replace('print(*v.left);print(*v.right);}', 'drop(->a);print(*v.left);print(*v.right);}'))

    def test_iteration_snapshot_keeps_initial_and_later_cells(self):
        helpers=BASE+'''fn read(n:&Int)->Int{let local=View{data:&*n};return *local.data;}
          async fn work(v:&mut View,n:&Int)->Int{let mut i=0;
            while i<3{let old=v.data;v.data=&*n;print(read(old));i=i+1;yield;}return *v.data;}'''
        source=self.program('''let h=runtime::spawn(->work(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
        self.assertEqual(self.run_native(source).stdout,'11\n7\n9\n9\n9\n9\n')

    def test_legacy_reset_after_loop_completion(self):
        source=BASE+'''async fn work(v:&mut View,n:&Int)->Int{let mut i=0;
          while i<3{v.data=&*n;i=i+1;yield;}return *v.data;}
          fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);let a=p.new(7);let b=q.new(9);
          let mut v=View{data:&a};let h=runtime::spawn(->work(&mut v,&b));
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}BEFORE print(*v.data);
          drop(->v);q.reset();let next=q.new(19);print(next);}'''
        self.refused(source.replace('BEFORE','q.reset();'),'reset interdit',legacy=True)
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE',''),allow_legacy_reset=True)).stdout,'9\n9\n19\n')

    def test_independent_iteration_trace_model(self):
        helpers=BASE+'''async fn work(v:&mut View,a:&Int,b:&Int,limit:Int)->Int{
          let mut i=0;while i<limit{print(*v.data);if i==0{v.data=&*a;}else{v.data=&*b;}i=i+1;yield;}
          return *v.data;}'''
        for count,first,second in product((0,1,3),(9,13),(17,21)):
            state=7;trace=['11']
            for index in range(count):
                trace.append(str(state));state=first if index==0 else second
            trace.extend((str(state),str(state)))
            source=self.program('''let h=runtime::spawn(->work(&mut v,&b,&c,'''+str(count)+'''));
              match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}print(*v.data);''',helpers)
            source=source.replace('b=p.new(9)','b=p.new('+str(first)+')').replace('c=p.new(11)','c=p.new('+str(second)+')')
            trace[0]=str(second)
            with self.subTest(count=count,first=first,second=second):
                self.assertEqual(self.run_native(source).stdout,'\n'.join(trace)+'\n')

if __name__=='__main__':unittest.main()
