"""Result preserves local payload storage, loans and explicit consumption."""
from pathlib import Path
import unittest
from crust import Parser, verify_program
import test_select_source as source_tests
import test_native_blocks as native_tests

ROOT=Path(__file__).resolve().parents[1]
PREFIX='''struct View{data:&Int}fn wrap(n:&Int)-><-View{let v=View{data:n};return <-v;}
async fn leaf(n:&Int)-><-View{let v=wrap(n);yield;return <-v;}
fn finish(h:->Execution<leaf>)-><-Result<View,runtime::Error>{let r=h.join();return <-r;}'''

class LocalResultEnvelopeTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused
    run_native=native_tests.NativeBlockTests.run_native

    def test_recorded_and_target_lifetime(self):
        source=(ROOT/'validation/open-sync-join-local-payload-type.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(*v.data);','drop(->n);print(*v.data);'),'emprunt|réserv|référenc')

    def test_named_envelope_and_relay(self):
        source=PREFIX+'''fn relay(r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>{return <-r;}
          fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->leaf(&n));
          let r=finish(->h);let r2=relay(->r);let v=match r2{Ok(v)=>{<-v},Err(_)=>{return;}};
          print(*v.data);drop(->v);drop(->n);let next=ns.new(9);print(*next);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        for before in ('let r2=relay(->r);','print(*v.data);'):
            self.refused(source.replace(before,'drop(->n);'+before),'emprunt|réserv|référenc')
        self.refused(source.replace('relay(->r)','relay(r)'),'transfér|mode attendu|explicite')

    def test_modular_bridge_and_declared_storage(self):
        source=PREFIX+'''fn relay(r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>{return <-r;}
          fn bridge(h:->Execution<leaf>)-><-Result<View,runtime::Error>{return <-relay(->finish(->h));}
          fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->leaf(&n));
          let r=bridge(->h);match r{Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{return;}}}'''
        compiler=verify_program(source)
        self.assertIn('relay',compiler.body_call_contracts['bridge'])
        self.assertEqual(compiler.function_contracts['relay'].storage_requirements,((0,'local'),))
        self.assertEqual(compiler.function_contracts['bridge'].join_storage_result,'local')
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_failed_launch_and_drop_whole_result(self):
        source=PREFIX+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
          let h=runtime::spawn(->leaf(&n));let r=finish(->h);drop(->r);drop(->n);
          let next=ns.new(9);print(*next);}'''
        for fail in (False,True):
            run=self.run_native(source,fail_submission_at=1 if fail else None)
            self.assertEqual(run.stdout,'9\n')
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)
            self.assertEqual(run.stderr.count('=View\n'),0 if fail else 1)
        self.refused(source.replace('let r=finish(->h);drop(->r);','finish(->h);'),'résultat|explicite')

    def test_proven_absent_local_payload_through_contracts(self):
        source=(ROOT/'validation/open-local-result-absent-payload.crb').read_text()
        relay='''fn relay(r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>{return <-r;}
          fn bridge(h:->Execution<leaf>)-><-Result<View,runtime::Error>{return <-relay(->finish(->h));}'''
        programs=[source, source.replace('fn main()',relay+'fn main()').replace(
                'let r=finish(->h);','let r=bridge(->h);')]
        for expression in ('{raw ->; <-raw}', 'if true{raw ->; <-raw}else{raw ->; <-raw}',
                           'loop{raw ->;break <-raw;}'):
            programs.append(source.replace('let r=finish(->h);',
                'let raw=finish(->h);let r='+expression+';'))
        for program in programs:
            with self.subTest(bridge='fn bridge' in program):
                # Never launch the infinite body: this run exercises LaunchFailed.
                result=self.run_native(program,fail_submission_at=1)
                self.assertEqual(result.stdout,'99\n')
                self.assertEqual(result.stderr.count('destroy n=7\n'),1)
                self.assertNotIn('=View\n',result.stderr)
                self.refused(program.replace('drop(->n);','drop(->n);print(*n);'),'détruit|déplac|valide|disponible')
        self.refused(source.replace('-><-Result<View,runtime::Error>',
                                    '-><-Result<A<View>,runtime::Error>'),'stockage|local|A<T>')
        self.refused(source.replace('let r=finish(->h);',
            'let r:Result<A<View>,runtime::Error>=finish(->h);'),'stockage|local|A<T>')

    def test_possible_completion_preserves_local_payload(self):
        source='''struct View{data:&Int}
          async fn leaf(n:&Int,flag:Bool)-><-View{
            if flag{let v=View{data:n};return <-v;}loop{yield;}}
          fn finish(h:->Execution<leaf>)-><-Result<View,runtime::Error>{return <-h.join();}
          fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
            let h=runtime::spawn(->leaf(&n,true));let r=finish(->h);
            match r{Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{print(99);}}drop(->n);}'''
        for fail,expected in ((None,'7\n'),(1,'99\n')):
            result=self.run_native(source,fail_submission_at=fail)
            self.assertEqual(result.stdout,expected)
            self.assertEqual(result.stderr.count('destroy n=7\n'),1)
            self.assertEqual(result.stderr.count('=View\n'),0 if fail else 1)
        self.refused(source.replace('print(*v.data);','drop(->n);print(*v.data);'),
                     'emprunt|réserv|référenc')

    def test_control_results_preserve_loans_and_storage_type(self):
        for expression in ('{raw ->; <-raw}', 'if true{raw ->; <-raw}else{raw ->; <-raw}',
                           'loop{raw ->;break <-raw;}'):
            source=PREFIX+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
              let h=runtime::spawn(->leaf(&n));let raw=finish(->h);let r=EXPRESSION;
              match r{Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{return;}}drop(->n);}'''.replace('EXPRESSION',expression)
            self.assertEqual(self.run_source(source).stdout,'7\n')
            self.refused(source.replace('match r{','drop(->n);match r{'),'emprunt|réserv|référenc')
        mixed=(ROOT/'validation/open-local-result-mixed-storage.crb').read_text()
        self.refused(mixed,'stockage|local|A<T>')
        # An impossible successful payload still has its declared storage type.
        absent=mixed.replace('let p=Point{x:7};return <-p;','loop{yield;}').replace(
            'let p=ps.new(x:9);return <-p;','loop{yield;}')
        self.refused(absent,'stockage|local|A<T>')

    def test_prepared_envelope_keeps_target_during_next_argument(self):
        helpers='''fn consume(r:->Result<View,runtime::Error>,value:Int){drop(->r);print(value);}
          fn release(n:->A<Int>)->Int{drop(->n);return 1;}'''
        source=PREFIX+helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
          let h=runtime::spawn(->leaf(&n));consume(->finish(->h),1);drop(->n);}'''
        self.assertEqual(self.run_source(source).stdout,'1\n')
        self.refused(source.replace('finish(->h),1','finish(->h),release(->n)'),
                     'emprunt|réserv|référenc|argument')

    def test_feature_signatures_keep_payload_storage(self):
        declarations='''type feature Forward{fn forward(&self,r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>;}
          struct Console{x:Int}impl Console{fn forward(self:&Console,r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>{return <-r;}}
          fn drive(f:&Forward,r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>{return <-f.forward(->r);}'''
        source=PREFIX+declarations+'''fn main(){let c=Console{x:1};let mut ns=pool<Int>(1);let n=ns.new(7);
          let h=runtime::spawn(->leaf(&n));let r=drive(&c,->finish(->h));drop(->r);}'''
        self.assertEqual(self.run_source(source).stdout,'')
        wrong=declarations.replace('fn forward(self:&Console,r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>',
          'fn forward(self:&Console,r:->Result<A<View>,runtime::Error>)-><-Result<A<View>,runtime::Error>')
        self.refused(source.replace(declarations,wrong),'feature|signature')

    def test_payload_storage_kind_is_part_of_signature(self):
        local=PREFIX+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->leaf(&n));
          let r=finish(->h);drop(->r);}'''
        self.refused(local.replace('-><-Result<View,runtime::Error>','-><-Result<A<View>,runtime::Error>'),
                     'stockage|local|A<T>')
        pooled='''struct Point{x:Int}async fn leaf(ps:&mut Pool<Point>)-><-A<Point>{
          let p=ps.new(x:7);yield;return <-p;}
          fn finish(h:->Execution<leaf>)-><-Result<A<Point>,runtime::Error>{return <-h.join();}
          fn main(){let mut ps=pool<Point>(1);let h=runtime::spawn(->leaf(&mut ps));
          let r=finish(->h);match r{Ok(p)=>{print(p.x);drop(->p);},Err(_)=>{return;}}}'''
        self.assertEqual(self.run_source(pooled).stdout,'7\n')
        self.refused(pooled.replace('-><-Result<A<Point>,runtime::Error>','-><-Result<Point,runtime::Error>'),
                     'stockage|local|A<T>')

    def test_parameter_storage_mismatch_is_rejected(self):
        body='''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->leaf(&n));
          let r=finish(->h);let next=relay(->r);drop(->next);}'''
        for storage in ('View','A<View>'):
            typ=f'Result<{storage},runtime::Error>'
            source=PREFIX+f'fn relay(r:->{typ})-><-{typ}{{return <-r;}}'+body
            if storage=='View':self.assertEqual(self.run_source(source).stdout,'')
            else:self.refused(source,'stockage|local|A<T>')

    def test_two_storage_kind_model(self):
        for source_kind in ('local','pool'):
            for required in ('local','pool'):
                payload='Point' if required=='local' else 'A<Point>'
                signature=f'Result<{payload},runtime::Error>'
                leaf=('async fn leaf()-><-Point{let p=Point{x:7};yield;return <-p;}' if source_kind=='local' else
                      'async fn leaf(ps:&mut Pool<Point>)-><-A<Point>{let p=ps.new(x:7);yield;return <-p;}')
                setup='' if source_kind=='local' else 'let mut ps=pool<Point>(1);'
                argument='' if source_kind=='local' else '&mut ps'
                source='struct Point{x:Int}'+leaf+f'fn relay(r:->{signature})-><-{signature}{{return <-r;}}'+f'''
                  fn main(){{{setup}let h=runtime::spawn(->leaf({argument}));let r=h.join();let next=relay(->r);
                  match next{{Ok(p)=>{{print(p.x);drop(->p);}},Err(_)=>{{return;}}}}}}'''
                with self.subTest(source_kind=source_kind,required=required):
                    if source_kind==required:self.assertEqual(self.run_source(source).stdout,'7\n')
                    else:self.refused(source,'stockage|local|A<T>')

    def test_mutable_payload_through_envelope_relay(self):
        prefix=PREFIX.replace('View','Writer').replace('&Int','&mut Int')
        source=prefix+'''fn relay(r:->Result<Writer,runtime::Error>)-><-Result<Writer,runtime::Error>{return <-r;}
          fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);let h=runtime::spawn(->leaf(&mut n));
          let r=relay(->finish(->h));let mut v=match r{Ok(v)=>{<-v},Err(_)=>{return;}};
          let mut w=&mut *v.data;w.set(20);print(*w);drop(->v);print(*n);}'''
        self.assertEqual(self.run_source(source).stdout,'20\n20\n')
        for before in ('print(*n);','drop(->n);','drop(->v);'):
            self.refused(source.replace('w.set(20);',before+'w.set(20);'),'emprunt|réserv|référenc')

    def test_target_cannot_escape_child_in_envelope(self):
        source=PREFIX+'''fn main(){let r={let mut ns=pool<Int>(1);let n=ns.new(7);
          let h=runtime::spawn(->leaf(&n));let r=finish(->h);<-r};
          match r{Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{return;}}}'''
        self.refused(source,'durable|survi|emprunt|réserv|référenc')

    def test_conditional_envelope_keeps_possible_targets(self):
        helpers='''fn choose(left:->Execution<leaf>,right:->Execution<leaf>,flag:bool)-><-Result<View,runtime::Error>{
          let a=left.join();let b=right.join();if flag{a ->;b ->;drop(->b);return <-a;}
          drop(->a);return <-b;}'''
        for flag,expected in (('true','7\n'),('false','9\n')):
            source=PREFIX+helpers+'''fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
              let left=runtime::spawn(->leaf(&a));let right=runtime::spawn(->leaf(&b));
              let r=choose(->left,->right,FLAG);match r{Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{return;}}
              drop(->a);drop(->b);}'''.replace('FLAG',flag)
            self.assertEqual(self.run_source(source).stdout,expected)
            for target in ('a','b'):
                self.refused(source.replace('match r{',f'drop(->{target});match r{{'),'emprunt|réserv|référenc')

    def test_loop_envelope_reuse_and_annotations(self):
        source=PREFIX+'''fn relay(r:->Result<View,runtime::Error>)-><-Result<View,runtime::Error>{return <-r;}
          fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let mut i=0;
          while i<3{let h=runtime::spawn(->leaf(&n));let r:Result<View,runtime::Error> = relay(->finish(->h));
            match r{Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{return;}}i=i+1;}
          drop(->n);let next=ns.new(9);print(*next);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n7\n7\n9\n')
        self.assertEqual(run.stderr.count('=View\n'),3)
        self.refused(source.replace('let r:Result<View,runtime::Error>', 'let r:Result<A<View>,runtime::Error>'),
                     'type|annotation|stockage|local')

    def test_parser_preserves_nested_payload_storage(self):
        for payload,expected in (('View','local'),('A<View>','pool')):
            typ=f'Result<Result<{payload},runtime::Error>,runtime::Error>'
            node=Parser(f'fn relay(r:->{typ})-><-{typ}{{return <-r;}}').parse()[0]
            self.assertEqual(node.args[1],[('r','join_nested','View')])
            self.assertEqual(node.args[2],('join_nested','View'))
            self.assertEqual(node.join_storage_parameters,(('r',expected),))
            self.assertEqual(node.join_storage_result,expected)

    def test_async_envelope_nested_join_and_failure_levels(self):
        source=(ROOT/'validation/open-async-local-result-envelope.crb').read_text()
        source=source.replace('Err(_)=>{return;}}},Err(_)=>{return;}',
                              'Err(_)=>{print(88);return;}}},Err(_)=>{print(99);return;}')
        helper='''fn finish(h:->Execution<envelope>)-><-Result<Result<View,runtime::Error>,runtime::Error>{
          return <-h.join();}'''
        source=source.replace('fn main()',helper+'fn main()').replace('let r=h.join();','let r=finish(->h);')
        for failure,expected in ((None,'7\n'),(1,'99\n'),(2,'88\n')):
            run=self.run_native(source,fail_submission_at=failure)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('=View\n'),int(failure is None))
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        self.refused(source.replace('match r{','drop(->n);match r{'),'emprunt|réserv|référenc')

    def test_direct_await_envelope_preserves_loans(self):
        helpers='''async fn envelope(n:&Int)-><-Result<View,runtime::Error>{
          let h=runtime::spawn(->leaf(n));return <-h.await;}
          async fn work()->Int{let mut ns=pool<Int>(1);let n=ns.new(7);
            let r={let r=envelope(&n).await;<-r};yield;
            let v=match r{Ok(v)=>{<-v},Err(_)=>{return 99;}};print(*v.data);drop(->v);drop(->n);return 9;}'''
        source=PREFIX+helpers+'''fn main(){let h=runtime::spawn(->work());
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(88);}}}'''
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('yield;\n            let v=', 'drop(->n);yield;\n            let v='),
                     'emprunt|réserv|référenc')

if __name__=='__main__':unittest.main()
