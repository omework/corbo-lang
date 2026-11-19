"""AS7: source capacities and conservative bounds on simultaneously live states."""
import itertools
import unittest
from crust import Compiler, Error, Parser, compile_source, verify_program
import test_type_features
import test_async_runtime


class AsyncCapacityTests(unittest.TestCase):
    native = test_type_features.TypeFeatureTests.native
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle
    leaf = 'async fn leaf(n:Int)->Int{yield;return n;}'

    def compiler(self, source):
        compiler = Compiler()
        compiler.compile(Parser(source).parse())
        return compiler

    def test_repeated_abandonment_requires_explicit_capacity(self):
        leaf = 'async fn leaf(x:i64)->i64 { yield; x }'
        repeat = """
            let mut i:i64 = 0;
            while i < 4 {
                let h=runtime::spawn(leaf(i));
                drop(h);
                i += 1;
            }
        """
        sync = leaf + 'fn main(){' + repeat + 'print(i);}'
        asynchronous = leaf + 'async fn parent()->i64{' + repeat + 'i}' + """
            fn main() {
                let h=runtime::spawn(parent());
                match h.join() { Ok(n)=>{ print(n); }, Err(_)=>{ print(0); } }
            }
        """
        relay = leaf + '''
            #(branch: join=result.join())
            fn start(x:i64) -> runtime::Handle<i64> { runtime::spawn(leaf(x)) }
            fn forget(x:i64) { let h=start(x); drop(h); }
            fn main() {
                let mut i:i64=0;
                while i < 4 { forget(i); i += 1; }
                print(i);
            }
        '''
        async_relay = relay[:relay.index('fn main')] + asynchronous[asynchronous.index('async fn parent'):]
        async_relay = async_relay.replace('let h=runtime::spawn(leaf(i));\n                drop(h);',
                                          'forget(i);')
        nested = async_relay.replace(relay[:relay.index('fn main')], leaf + """
            async fn forget(x:i64) { let h=runtime::spawn(leaf(x)); drop(h); }
        """).replace('forget(i);', 'forget(i).await;')
        async_wrapper = async_relay.replace('forget(i);', 'let h=start(i); drop(h);')
        for source in (sync, asynchronous, relay, async_relay, nested, async_wrapper):
            with self.assertRaisesRegex(Error, 'async_pool_sizes requis.*abandons répétés.*leaf'):
                verify_program(source)
            configured = '#(directive: async_pool_sizes={leaf:4})' + source
            self.assertEqual(self.native(configured).stdout, '4\n')
        once = leaf + 'fn main(){loop {let h=runtime::spawn(leaf(1));drop(h);break;}}'
        self.assertEqual(self.native(once).stdout, '')

    def test_directive_validation(self):
        for directive, diagnostic in (
            ('{}', 'au moins une capacité'),
            ('{leaf:0}', 'strictement positive'),
            ('{leaf:-1}', 'strictement positive'),
            ('{leaf:2147483648}', 'hors limites'),
            ('{leaf:1,leaf:2}', 'dupliquée'),
            ('{unknown:2}', 'inconnu'),
            ('{network::read:2}', 'network::read'),
        ):
            with self.subTest(directive=directive), self.assertRaisesRegex(Error, diagnostic):
                verify_program('#(directive: async_pool_sizes='+directive+')'+self.leaf+'fn main(){}')
        with self.assertRaisesRegex(Error, 'niveau du programme'):
            verify_program(self.leaf+'fn main(){#(directive, async_pool_sizes={leaf:2})}')
        with self.assertRaisesRegex(Error, 'dupliquée'):
            verify_program('#(directive, async_pool_sizes={leaf:2})'*2+self.leaf+'fn main(){}')
        source='#(directive: async_pool_sizes={leaf:3,})'+self.leaf+'fn main(){}'
        self.assertEqual(self.compiler(source).async_pool_capacities, {'leaf':3})
        self.native(source)

    def test_more_than_sixteen_retained_tasks_and_function_returns(self):
        source=self.leaf+'fn make(n:Int)-><- leaf{let t=leaf(n);return <- t;}fn main(){'
        source+=''.join(f'let t{i}=make({i});' for i in range(19))
        source+=''.join(f'drop(-> t{i});' for i in reversed(range(19)))+'print(19);}'
        compiler=self.compiler(source)
        self.assertGreaterEqual(compiler.async_pool_capacities['leaf'], 19)
        self.assertEqual(self.native(source).stdout, '19\n')

    def test_all_returning_branch_slots_are_counted(self):
        source=self.leaf+'fn choose(flag:Int){if flag==0{'
        source+=''.join(f'let t{i}=leaf({i});' for i in range(19))
        source+=''.join(f'drop(-> t{i});' for i in range(19))+'return;}else{return;}}'
        source+='fn main(){choose(0);choose(1);}'
        self.assertGreaterEqual(self.compiler(source).async_pool_capacities['leaf'], 19)
        self.native(source)

    def test_cycles_report_every_missing_pool_and_explicit_cut_bounds_descendants(self):
        declarations='''
            async fn a(n:Int)->Int{if n==0{return 0;}let v=b(n-1).await;return v;}
            async fn b(n:Int)->Int{if n==0{return 1;}let v=a(n-1).await;return v;}
            async fn c()->Int{let v=c().await;return v;}
        '''
        with self.assertRaises(Error) as raised:
            verify_program(declarations+'fn main(){}')
        for name in ('a','b','c'):
            self.assertIn('- '+name+' : cycle', str(raised.exception))
        source='#(directive, async_pool_sizes={a:3,c:1})'+declarations+'''
            fn main(){let h=runtime::spawn(-> a(4));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}
        '''
        compiler=self.compiler(source)
        self.assertEqual(compiler.async_pool_capacities['a'],3)
        self.assertGreaterEqual(compiler.async_pool_capacities['b'],2)
        self.assertEqual(self.native(source).stdout,'0\n')

    def test_recursive_parent_occupies_slot_until_child_finishes(self):
        source='''#(directive, async_pool_sizes={recur:4})
            async fn recur(n:Int)->Int{
                if n==0{return 10;}
                let value=recur(n-1).await;
                return value+1;
            }
            fn main(){let h=runtime::spawn(-> recur(3));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}
        '''
        self.assertEqual(self.native(source).stdout,'13\n')
        # Exhaustion is a checked runtime failure, not live-slot reuse. No
        # source bound may silently grow beyond the explicit capacity.
        code=compile_source(source.replace('recur:4','recur:3'))
        run=self.run_c_oracle(code, expected_error='task pool capacity exceeded')
        self.assertIn('task pool capacity exceeded',run.stderr)

    def test_independent_live_instance_model_matches_nested_frames(self):
        # Model: roots are retained together. Each parent retains width inactive
        # leaves before any is released. Thus the maximum is roots*width leaves,
        # even though parents themselves are executed one by one below. A raw C
        # driver polls all parents to their yield before continuing any of them.
        for roots,width in itertools.product((1,3),(1,3)):
            children=''.join(f'let child{i}=leaf({i});' for i in range(width))
            dispose=''.join(f'drop(-> child{i});' for i in range(width))
            source=self.leaf+f'async fn parent(){{{children}yield;{dispose}}}fn main(){{'
            source+=''.join(f'let p{i}=parent();' for i in range(roots))
            source+=''.join(f'drop(-> p{i});' for i in range(roots))+'}'
            compiler=self.compiler(source)
            self.assertGreaterEqual(compiler.async_pool_capacities['parent'],roots)
            self.assertGreaterEqual(compiler.async_pool_capacities['leaf'],roots*width)
            code='#define main crust_sync_main\n'+compile_source(source)
            code+='\n#undef main\nint main(void){crust_task_context_init();\n'
            code+=''.join(f'CrustTask *p{i}=crust_async_parent_create();\n' for i in range(roots))
            code+=''.join(f'if(task_poll(p{i})!=TASK_SUSPENDED) abort();\n' for i in range(roots))
            code+=''.join(f'if(task_poll(p{i})!=TASK_COMPLETE) abort();\n' for i in range(roots))
            code+=''.join(f'if(!task_drop_complete(p{i})) abort();\n' for i in range(roots))
            code+='crust_task_context_close();puts("model ok");return 0;}'
            with self.subTest(roots=roots,width=width):
                self.assertEqual(self.run_c_oracle(code).stdout,'model ok\n')

    def test_oversized_inferred_bound_requires_explicit_capacity(self):
        declarations='async fn level0(){}'
        for level in range(1,32):
            declarations+=f'''async fn level{level}(){{
                let a=level{level-1}();let b=level{level-1}();
                drop(-> a);drop(-> b);}}'''
        source=declarations+'fn main(){let t=level31();drop(->t);}'
        with self.assertRaisesRegex(Error,'async_pool_sizes requis.*trop grande'):
            verify_program(source)
        # A hard bound interrupts exponential propagation. The root is never
        # polled in this case; no huge native storage allocation is attempted.
        configured='#(directive, async_pool_sizes={level1:2})'+source
        capacities=self.compiler(configured).async_pool_capacities
        self.assertEqual(capacities['level0'],4)
        self.assertEqual(capacities['level1'],2)

    def test_feature_specializations_receive_the_named_capacity(self):
        source='''#(directive, async_pool_sizes={count:2})
            type feature Length{fn len(&self)->Int;}
            async fn count(v:&Length)->Int{yield;return v.len();}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut a=p.new();a.push(7);
                let mut q=pool<Vector<u8>>(1);let mut b=q.new();let n:u8=9;b.push(n);
                let left=runtime::spawn(-> count(&a));let right=runtime::spawn(-> count(&b));
                match left.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}
                match right.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}
                a.push(8);print(a.len());}
        '''
        capacities=self.compiler(source).async_pool_capacities
        self.assertEqual(len(capacities),2)
        self.assertTrue(all(name.startswith('count$feature') and size==2
                            for name,size in capacities.items()))
        self.assertEqual(self.native(source).stdout,'1\n1\n2\n')
        with self.assertRaisesRegex(Error,'emprunt|exécution|tâche'):
            verify_program(source.replace('match left.join()', 'a.push(8);match left.join()'))

    def test_transferred_capture_cleanup_and_parent_child_waits(self):
        source='''async fn leaf(n:-> Int)->Int{yield;return *n;}
            async fn parent(n:-> Int)->Int{let child=leaf(-> n);yield;
                let value=child.await;return value;}
            fn launch(n:-> Int)-><- Execution<parent>{
                let h=runtime::spawn(-> parent(-> n));return <- h;}
            fn main(){let mut p=pool<Int>(1);let n=p.new(17);address(n);
                let h=launch(-> n);match h.join(){Ok(v)=>{print(v);},Err(_)=>{print(99);}}
                let reused=p.new(21);address(reused);print(reused);}
        '''
        run=self.native(source)
        lines=run.stdout.splitlines()
        self.assertEqual(lines[0],lines[2])
        self.assertEqual((lines[1],lines[3]),('17','21'))
        self.assertEqual(run.stderr.count('destroy n=17'),1)
        with self.assertRaisesRegex(Error,'plus utilisable|transférée'):
            verify_program(source.replace('match h.join()', 'print(n);match h.join()'))

    def test_loops_reuse_slots_and_do_not_accumulate_state(self):
        source=self.leaf+'''fn main(){let mut i=0;while i<30{
            let t=leaf(i);drop(->t);i=i+1;
            if i==10{continue;}if i==25{break;}
        }print(i);}'''
        self.assertEqual(self.native(source).stdout,'25\n')


if __name__=='__main__':
    unittest.main()
