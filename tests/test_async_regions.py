"""Lexical region limits at async construction, independent of resume/receiver."""
import unittest
import random
from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncRegionTests(unittest.TestCase):
    run_c_oracle = native.NativeBlockTests.run_c_oracle
    run_native = native.NativeBlockTests.run_native

    @staticmethod
    def wrap(body, helpers=''):
        return helpers+'async fn work()->Int{'+body+'''}
          fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def run_regions(self, source, expected):
        code=compile_source(source)
        anchor='return vector_construct_reserved(NULL, 0, source, region_limit, element_size, alignment, forward_only, 0, label);'
        self.assertEqual(code.count(anchor),1)
        replacement='''Cell *built = vector_construct_reserved(NULL, 0, source, region_limit,
            element_size, alignment, forward_only, 0, label);
          GrowthRegionPool *actual = vector_items(built)->region.region.pool;
          fprintf(stderr, "region:%zu\\n", actual ? actual->region_size : (size_t)0);
          return built;'''
        run=self.run_c_oracle(code.replace(anchor,replacement))
        actual=[int(line[7:]) for line in run.stderr.splitlines() if line.startswith('region:')]
        self.assertEqual(actual,expected)
        return run

    def test_nested_inheritance_override_and_restoration(self):
        for typ in ('String','Vector<Int>','Vector<u8>'):
            body=f'''let mut p=pool<{typ}>(1);
              #(directive,stack_region_max_size=1M){{
                let a=p.new();yield;drop(->a);
                {{let b=p.new();yield;drop(->b);}}
                #(directive,stack_region_max_size=2M){{let c=p.new();yield;drop(->c);}}
                let d=p.new();drop(->d);
              }}let e=p.new();drop(->e);return 42;'''
            with self.subTest(typ=typ):
                run=self.run_regions(self.wrap(body),[1048576,1048576,2097152,1048576,0])
                self.assertEqual(run.stdout,'42\n')
                self.assertEqual(sum(x.startswith('destroy ') for x in run.stderr.splitlines()),5)

    def test_transferred_collection_keeps_creation_region(self):
        body='''let mut p=pool<Vector<u8>>(2);
          #(directive,stack_region_max_size=1M){
            let mut result=#(directive,stack_region_max_size=2M){
              let memory=&mut p;let mut v=memory.new();v.push(7);yield;<-v};
            yield;result.push(9);print(result[0] as Int);print(result[1] as Int);
            let other=p.new();drop(->other);drop(->result);
          }return 42;'''
        run=self.run_regions(self.wrap(body),[2097152,1048576])
        self.assertEqual(run.stdout,'7\n9\n42\n')
        with self.assertRaisesRegex(Error,'pool local'):
            verify_program(self.wrap(body.replace('let memory=&mut p;',
                'let mut q=pool<Vector<u8>>(1);let memory=&mut q;')))

    def test_function_boundary_and_return_do_not_inherit_callers_directive(self):
        helpers='''async fn make(p:&mut Pool<String>)-><-String{
          #(directive,stack_region_max_size=2M){let mut s=p.new();s.push_str("été");yield;return <-s;}}
          fn plain(p:&mut Pool<String>)-><-String{let s=p.new();return <-s;}'''
        body='''let mut p=pool<String>(2);#(directive,stack_region_max_size=1M){
          let memory=&mut p;let s=make(memory).await;print(&s[..]);drop(->s);
          let t=plain(&mut p);drop(->t);let u=p.new();drop(->u);}return 42;'''
        run=self.run_regions(self.wrap(body,helpers),[2097152,0,1048576])
        self.assertEqual(run.stdout,'été\n42\n')

    def test_scalar_and_borrowed_block_receivers(self):
        body='''let mut p=pool<String>(1);let value=7;
          let n=#(directive,stack_region_max_size=1M){let s=p.new();yield;drop(->s);9};
          let view=#(directive,stack_region_max_size=2M){let t=p.new();yield;drop(->t);&value};
          print(*view);let u=p.new();drop(->u);return n;'''
        run=self.run_regions(self.wrap(body),[1048576,2097152,0])
        self.assertEqual(run.stdout,'7\n9\n')

    def test_loop_cleanup_and_native_thread_block(self):
        body='''let mut p=pool<Vector<Int>>(1);let mut i=0;
          let n=loop{#(directive,stack_region_max_size=1M){
            let mut v=p.new();v.push(i);yield;i=i+1;if i<3{continue;}break v[0];}};
          let after=p.new();drop(->after);return n;'''
        run=self.run_regions(self.wrap(body),[1048576,1048576,1048576,0])
        self.assertEqual(run.stdout,'2\n')
        source='''fn main(){let h=runtime::thread({let mut p=pool<String>(1);
          #(directive,stack_region_max_size=1M){let mut s=p.new();s.push_str("ok");print(&s[..]);}
          return 42;});match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.assertEqual(self.run_regions(source,[1048576]).stdout,'ok\n42\n')

    def test_region_exhaustion_after_transfer_is_atomic(self):
        body='''let mut p=pool<Vector<u8>>(1);
          let mut v=#(directive,stack_region_max_size=1M){let v=p.new();<-v};
          let mut i=0;while i<1048576{v.push(7);i=i+1;}yield;
          match v.try_push(9){Ok(())=>{print(99);},Err(n)=>{print(n as Int);}}
          print(v.len());print(v[1048575] as Int);return 42;'''
        run=self.run_regions(self.wrap(body),[1048576])
        self.assertEqual(run.stdout,'9\n1048576\n7\n42\n')

    def test_region_does_not_relax_borrows_or_source_lifetime(self):
        body='''let mut p=pool<Vector<Int>>(1);#(directive,stack_region_max_size=1M){
          let mut v=p.new();v.push(7);let view=&v[0];yield;EFFECT print(*view);
        }return 42;'''
        self.assertEqual(self.run_regions(self.wrap(body.replace('EFFECT','')),[1048576]).stdout,'7\n42\n')
        for effect in ('v.push(9);','drop(->v);'):
            with self.subTest(effect=effect),self.assertRaises(Error):verify_program(self.wrap(body.replace('EFFECT',effect)))

    def test_conditional_return_keeps_each_branch_region(self):
        helpers='''async fn make(p:&mut Pool<Vector<Int>>,flag:Bool)-><-Vector<Int>{
          if flag{#(directive,stack_region_max_size=1M){let v=p.new();yield;return <-v;}}
          else{#(directive,stack_region_max_size=2M){let v=p.new();yield;return <-v;}}}'''
        for flag,size in (('true',1048576),('false',2097152)):
            body=f'''let mut p=pool<Vector<Int>>(1);
              #(directive,stack_region_max_size=4M){{let v=make(&mut p,{flag}).await;
                print(v.len());drop(->v);let after=p.new();drop(->after);}}return 42;'''
            with self.subTest(flag=flag):
                self.assertEqual(self.run_regions(self.wrap(body,helpers),[size,4194304]).stdout,'0\n42\n')

    def test_generated_lexical_limits_against_configuration_stack(self):
        for seed in (19,73):
            rng=random.Random(seed)
            expected=[]
            serial=0
            def tree(depth,inherited):
                nonlocal serial
                limit=rng.choice((None,1048576,2097152))
                effective=inherited if limit is None else limit
                prefix='' if limit is None else f'#(directive,stack_region_max_size={limit//1048576}M)'
                def allocation():
                    nonlocal serial
                    serial+=1
                    expected.append(effective)
                    return f'let a{serial}=p.new();yield;drop(->a{serial});'
                body=allocation()
                if depth:
                    body+=tree(depth-1,effective)+tree(depth-1,effective)
                body+=allocation()
                return prefix+'{'+body+'}'
            body='let mut p=pool<Vector<u8>>(1);'+tree(2,0)+'return 42;'
            with self.subTest(seed=seed):
                self.assertEqual(self.run_regions(self.wrap(body),expected).stdout,'42\n')
                self.assertEqual(len(expected),14)


if __name__=='__main__':unittest.main()
