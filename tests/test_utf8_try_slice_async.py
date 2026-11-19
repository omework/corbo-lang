"""TX4 x AS8/AS11/AS12: borrowed results survive suspension, not their source."""
import unittest
import test_foundation_rules
from crust import Error, compile_source, verify_program


class AsyncTrySliceTests(unittest.TestCase):
    native = test_foundation_rules.FoundationTests.native

    def test_suspendable_bounds_and_result_relay(self):
        source='''
            async fn bound(value:Int)->Int {print(value);yield;return value;}
            async fn cut(t:&str, end:Int)->Result<&str,SliceError> {
                let r=t.try_slice(bound(0).await..bound(end).await);
                yield;return r;
            }
            async fn relay(t:&str,end:Int)->Result<&str,SliceError> {
                let r=cut(t,end).await;yield;return r;
            }
            fn main(){let e=runtime::spawn(-> relay("été",END));
                match e.join(){Ok(r)=>{match r{
                    Err(SliceError::OutOfBounds)=>{print("OUT");},
                    Err(SliceError::NotCharBoundary)=>{print("CUT");},
                    Ok(v)=>{print(v);}
                }},Err(_)=>{print("TASK");}}
            }
        '''
        for end,value in ((2,'é'),(1,'CUT'),(8,'OUT')):
            run=self.native(source.replace('END',str(end)))
            self.assertEqual((run.returncode,run.stdout,run.stderr),(0,f'0\n{end}\n{value}\n',''))

    def test_returned_view_keeps_caller_source_reserved_after_join(self):
        source='''
            async fn cut(t:&String)->Result<&str,SliceError>{yield;return t.try_slice(..2);}
            async fn relay(t:&String)->Result<&str,SliceError>{let r=cut(t).await;yield;return r;}
            fn main(){let mut p=pool<String>(1);let mut t=p.new();t.push_str("été");
                let e=runtime::spawn(-> relay(&t));
                match e.join(){Ok(r)=>{
                    EFFECT
                    match r{Ok(v)=>{print(v);},Err(_)=>{}}
                },Err(_)=>{}}
                t.push_str("!");print(&t[..]);
                drop(-> t);let reused=p.new();print(reused.byte_len());
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\nété!\n0\n'),run.stderr)
        for effect in ('t.push_str("!");','p.reset();'):
            with self.subTest(effect=effect), self.assertRaisesRegex(Error,'emprunt|encore .*utilisée'):
                verify_program(source.replace('EFFECT',effect),allow_legacy_reset=True)
        # Explicit import is required before dropping the caller's allocation in the arm.
        with self.assertRaisesRegex(Error,'emprunt|encore .*utilisée'):
            verify_program(source.replace('EFFECT','t ->; drop(-> t);'))

    def test_execution_await_transmits_result_and_borrow_in_async_caller(self):
        source='''
            async fn cut(t:&str)->Result<&str,SliceError>{yield;return t.try_slice(..2);}
            async fn run(t:&mut String)->Int {
                let e=runtime::spawn(-> cut(&t[..]));
                match e.await {Ok(r)=>{
                    yield;
                    EFFECT
                    match r{Ok(v)=>{print(v);},Err(_)=>{}}
                },Err(_)=>{}}
                t.push_str("!");return 9;
            }
            fn main(){let mut p=pool<String>(1);let mut t=p.new();t.push_str("été");
                let e=runtime::spawn(-> run(&mut t));
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                print(&t[..]);
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\n9\nété!\n'),run.stderr)
        with self.assertRaisesRegex(Error,'emprunt'):
            compile_source(source.replace('EFFECT','t.push_str("!");'))

    def test_captured_result_and_alias_preserve_original_source(self):
        source='''
            async fn relay(r:Result<&str,SliceError>)->Result<&str,SliceError>{yield;return r;}
            async fn run(t:&mut String)->Int {
                let result=t.try_slice(..2);
                let alias=result;
                drop(-> result);
                let received=relay(alias).await;
                yield;
                EFFECT
                match received{Ok(v)=>{print(v);},Err(_)=>{}}
                t.push_str("!");return 9;
            }
            fn main(){let mut p=pool<String>(1);let mut t=p.new();t.push_str("été");
                let e=runtime::spawn(-> run(&mut t));
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                print(&t[..]);
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\n9\nété!\n'),run.stderr)
        with self.assertRaisesRegex(Error,'emprunt'):
            compile_source(source.replace('EFFECT','t.push_str("!");'))
        run=self.native('''
            async fn relay(r:Result<&str,SliceError>)->Result<&str,SliceError>{yield;return r;}
            fn main(){let result="été".try_slice(..2);
                let e=runtime::spawn(-> relay(result));
                match e.join(){Ok(r)=>{match r{Ok(v)=>{print(v);},Err(_)=>{}}},Err(_)=>{}}
            }
        ''')
        self.assertEqual((run.returncode,run.stdout,run.stderr),(0,'é\n',''))

    def test_owned_source_rejected_on_escape_but_allowed_inside_frame(self):
        source='''
            async fn run(t:-> String)->Int {
                let result=t.try_slice(..2);yield;
                EFFECT
                match result{Ok(v)=>{print(v);},Err(_)=>{}}
                return 9;
            }
            fn main(){let mut p=pool<String>(1);let mut t=p.new();t.push_str("été");
                let e=runtime::spawn(-> run(-> t));
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                let reused=p.new();print(reused.byte_len());
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\n9\n0\n'),run.stderr)
        with self.assertRaisesRegex(Error,'emprunt'):
            compile_source(source.replace('EFFECT','drop(-> t);'))
        with self.assertRaisesRegex(Error,'durable|locale'):
            compile_source('''
                async fn bad(t:-> String)->Result<&str,SliceError>{
                    let r=t.try_slice(..);yield;return r;
                }
                fn main(){let mut p=pool<String>(1);let t=p.new();
                    let e=runtime::spawn(-> bad(-> t));
                    match e.join(){Ok(r)=>{drop(-> r);},Err(_)=>{}}
                }
            ''')

    def test_conditional_result_reserves_both_sources_after_join(self):
        source='''
            async fn choose(a:&str,b:&str,flag:Int)->Result<&str,SliceError>{
                let result=if flag == 0 {a.try_slice(..)} else {b.try_slice(..)};
                yield;return result;
            }
            fn main(){let mut p=pool<String>(2);
                let mut a=p.new();a.push_str("a");
                let mut b=p.new();b.push_str("b");
                let e=runtime::spawn(-> choose(&a[..],&b[..],FLAG));
                match e.join(){Ok(result)=>{
                    EFFECT
                    match result{Ok(v)=>{print(v);},Err(_)=>{}}
                },Err(_)=>{}}
                a.push_str("!");b.push_str("!");
                print(&a[..]);print(&b[..]);
            }
        '''
        for flag in (0,1):
            program=source.replace('FLAG',str(flag))
            run=self.native(program.replace('EFFECT',''))
            self.assertEqual((run.returncode,run.stdout),(0,('a' if flag==0 else 'b')+'\na!\nb!\n'),run.stderr)
            for effect in ('a.push_str("!");','b.push_str("!");','p.reset();'):
                with self.subTest(flag=flag,effect=effect),self.assertRaisesRegex(Error,'emprunt|encore .*utilisée'):
                    verify_program(program.replace('EFFECT',effect),allow_legacy_reset=True)

    def test_result_reassignment_and_branch_extraction_release_old_borrow(self):
        source='''
            async fn work(a:&mut String,b:&mut String)->Int {
                let mut result=a.try_slice(..);
                match result{Ok(v)=>{print(v);},Err(_)=>{}}
                result=b.try_slice(..);
                a.push_str("!");
                yield;
                match result{Ok(v)=>{EFFECT print(v);},Err(_)=>{}}
                b.push_str("!");
                return 9;
            }
            fn main(){let mut p=pool<String>(2);let mut a=p.new();a.push_str("a");
                let mut b=p.new();b.push_str("b");
                let e=runtime::spawn(-> work(&mut a,&mut b));
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                print(&a[..]);print(&b[..]);
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'a\nb\n9\na!\nb!\n'),run.stderr)
        with self.assertRaisesRegex(Error,'emprunt'):
            compile_source(source.replace('EFFECT','b.push_str("!");'))

    def test_dynamic_result_capture_and_loop_result_keep_source(self):
        source='''
            async fn relay(r:Result<&str,SliceError>)->Result<&str,SliceError>{yield;return r;}
            fn main(){let mut p=pool<String>(1);let mut text=p.new();text.push_str("été");
                let result=text.try_slice(..2);
                let e=runtime::spawn(-> relay(result));drop(-> result);
                match e.join(){Ok(r)=>{EFFECT
                    match r{Ok(v)=>{print(v);},Err(_)=>{}}
                },Err(_)=>{}}
                text.push_str("!");print(&text[..]);
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\nété!\n'),run.stderr)
        with self.assertRaisesRegex(Error,'emprunt'):
            compile_source(source.replace('EFFECT','text.push_str("!");'))
        run=self.native('''
            async fn choose(a:&str,b:&str,flag:Int)->Result<&str,SliceError>{
                let r=loop{if flag==0 {break a.try_slice(..);}break b.try_slice(..);};
                yield;return r;
            }
            fn main(){let e=runtime::spawn(-> choose("a","b",1));
                match e.join(){Ok(r)=>{match r{Ok(v)=>{print(v);},Err(_)=>{}}},Err(_)=>{}}}
        ''')
        self.assertEqual((run.returncode,run.stdout,run.stderr),(0,'b\n',''))

    def test_computed_await_requires_explicit_result_use(self):
        source='''
            async fn cut()->Result<&str,SliceError>{yield;return "a".try_slice(..);}
            async fn run(flag:Int)->Int{
                let result=(if flag==0 {let t=cut(); <- t}else{let u=cut(); <- u}).await;
                USE
                return 9;
            }
            fn main(){let e=runtime::spawn(-> run(0));
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}}
        '''
        for program in (source.replace('USE',''),source.replace('USE','').replace('let result=','let _=')):
            with self.assertRaisesRegex(Error,'sans usage explicite'):
                compile_source(program)
        run=self.native(source.replace('USE','drop(-> result);'))
        self.assertEqual((run.returncode,run.stdout,run.stderr),(0,'9\n',''))

    def test_bound_capture_does_not_become_result_source(self):
        source='''
            async fn cut(text:&str,bound:&str)->Result<&str,SliceError>{
                yield;return text.try_slice(..bound.byte_len());
            }
            fn main(){let mut p=pool<String>(2);
                let mut text=p.new();text.push_str("été");
                let mut bound=p.new();bound.push_str("xx");
                let e=runtime::spawn(-> cut(&text[..],&bound[..]));
                match e.join(){Ok(r)=>{
                    bound.push_str("!");
                    EFFECT
                    match r{Ok(v)=>{print(v);},Err(_)=>{}}
                },Err(_)=>{}}
                text.push_str("!");print(&bound[..]);
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\nxx!\n'),run.stderr)
        with self.assertRaisesRegex(Error,'emprunt'):
            compile_source(source.replace('EFFECT','text.push_str("!");'))

    def test_fallible_usage_drop_and_types_across_suspension(self):
        source='''async fn work()->Int{BODY yield;return 9;}
            fn main(){let e=runtime::spawn(-> work());
                match e.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        run=self.native(source.replace('BODY','drop(-> "été".try_slice(..1));'))
        self.assertEqual((run.returncode,run.stdout,run.stderr),(0,'9\n',''))
        for body,message in (
            ('let r="é".try_slice(..);','sans usage'),
            ('let _="é".try_slice(..);','sans usage'),
            ('let r="é".try_slice(..);drop(-> r);drop(-> r);','plus utilisable'),
            ('drop(-> "é".try_slice(..true));','Int'),
        ):
            with self.subTest(body=body),self.assertRaisesRegex(Error,message):
                compile_source(source.replace('BODY',body))
