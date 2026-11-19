"""Completed task contracts preserve only the borrowed fields returned after await."""
from pathlib import Path
import unittest
from crust import verify_program
import test_select_source as source_tests
import test_native_blocks as native_tests

ROOT=Path(__file__).resolve().parents[1]
STRUCT='struct Pair{left:&Int,right:&Int}'
DETACH='async fn detach(v:->Pair)->&Int{yield;return v.left;}'
MAKE='fn make(v:->Pair)-><-detach{return <-detach(->v);}'
SETUP='let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let v=Pair{left:&a,right:&b};'

class DetachedTaskFactoryTests(unittest.TestCase):
    run_source=source_tests.SelectSourceTests.run_source
    run_c_oracle=source_tests.SelectSourceTests.run_c_oracle
    refused=source_tests.SelectSourceTests.refused
    run_native=native_tests.NativeBlockTests.run_native

    @staticmethod
    def program(body,prefix=STRUCT+DETACH+MAKE):
        return prefix+'async fn work()->Int{'+body+'''}fn main(){let h=runtime::spawn(->work());
          match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_factory_and_task_relay(self):
        source=(ROOT/'validation/open-owned-borrowed-detached-factory.crb').read_text()
        for extra,call in (('', 'make(->v)'),
            ('fn again(t:->detach)-><-detach{return <-t;}', 'again(->make(->v))')):
            program=source.replace('fn main()',extra+'fn main()').replace('spawn(->make(->v))','spawn(->'+call+')')
            self.assertEqual(self.run_source(program).stdout,'7\n')
            self.refused(program.replace('drop(->b);','drop(->a);').replace('print(*view);\n    drop(->a);','print(*view);'),
                         'emprunt|réserv|référenc')

    def test_direct_child_target_must_survive(self):
        self.refused((ROOT/'validation/open-detached-child-target-dropped.crb').read_text(),'emprunt|réserv|référenc')
        source=self.program(SETUP+'let view=detach(->v).await;drop(->b);yield;print(*view);drop(->a);return 11;')
        self.assertEqual(self.run_source(source).stdout,'7\n11\n')
        invalid=source.replace('drop(->a);','').replace('yield;print(*view);','drop(->a);yield;print(*view);')
        self.refused(invalid,'emprunt|réserv|référenc')

    def test_factory_child_exact_target_access_model(self):
        # Before completion both fields are live. After completion only left
        # is returned. The expectation is independent of compiler summaries.
        for call in ('detach','make','again'):
            prefix=STRUCT+DETACH+MAKE+'fn again(v:->Pair)-><-detach{return <-make(->v);}'
            for target in ('a','b'):
                for completed in (False,True):
                    body=SETUP+'let t=CALL(->v);BEFORE let view=t.await;AFTER yield;print(*view);return 11;'
                    operation='drop(->'+target+');'
                    body=body.replace('CALL',call).replace('BEFORE','' if completed else operation).replace('AFTER',operation if completed else '')
                    program=self.program(body,prefix)
                    with self.subTest(call=call,target=target,completed=completed):
                        if completed and target=='b':self.assertEqual(self.run_source(program).stdout,'7\n11\n')
                        else:self.refused(program,'emprunt|réserv|référenc')

    def test_inference_follows_helpers_independent_of_declaration_order(self):
        helper='fn field(v:&Pair)->&Int{return v.left;}'
        task='async fn detach(v:->Pair)->&Int{yield;return field(&v);}'
        main='''fn main(){'''+SETUP+'''let h=runtime::spawn(->make(->v));let view=match h.join(){Ok(r)=>{r},Err(_)=>{return;}};
             drop(->b);print(*view);drop(->a);}'''
        for parts in ((helper,task,MAKE),(MAKE,task,helper),(task,MAKE,helper)):
            source=STRUCT+''.join(parts)+main
            self.assertEqual(self.run_source(source).stdout,'7\n')
            self.refused(source.replace('drop(->b);','drop(->a);').replace('print(*view);drop(->a);','print(*view);'),
                         'emprunt|réserv|référenc')

    def test_inline_value_is_not_a_durable_target(self):
        for result in ('return &v.value;','let view=&v.value;yield;return view;'):
            source='struct Bad{value:Int}async fn detach(v:->Bad)->&Int{'+result+'''}
                fn make(v:->Bad)-><-detach{return <-detach(->v);}
                fn main(){let v=Bad{value:7};let h=runtime::spawn(->make(->v));match h.join(){Ok(r)=>{print(*r);},Err(_)=>{}}}'''
            self.refused(source,'local|durable|retour|emprunt|propriétaire|paramètre')

    def test_conditional_projection_unions_possible_targets(self):
        task='async fn detach(v:->Pair,flag:Bool)->&Int{if flag{return v.left;}yield;return v.right;}'
        factory='fn make(v:->Pair,flag:bool)-><-detach{return <-detach(->v,flag);}'
        for flag,value in (('true',7),('false',9)):
            source=self.program(SETUP+'let view=make(->v,'+flag+').await;yield;print(*view);drop(->a);drop(->b);return 11;',STRUCT+task+factory)
            self.assertEqual(self.run_source(source).stdout,f'{value}\n11\n')
            for target in ('a','b'):
                invalid=source.replace('drop(->'+target+');','').replace('yield;print(*view);','drop(->'+target+');yield;print(*view);')
                self.refused(invalid,'emprunt|réserv|référenc')

    def test_target_survives_carrier_pool(self):
        task='async fn detach(v:->A<Pair>)->&Int{yield;return v.left;}'
        factory='fn make(v:->A<Pair>)-><-detach{return <-detach(->v);}'
        body='''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let view={let mut ps=pool<Pair>(1);
          let v=ps.new(left:&a,right:&b);let r=make(->v).await;r};drop(->b);yield;print(*view);drop(->a);return 11;'''
        self.assertEqual(self.run_source(self.program(body,STRUCT+task+factory)).stdout,'7\n11\n')
        invalid='''let view={let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let mut ps=pool<Pair>(1);
          let v=ps.new(left:&a,right:&b);let r=make(->v).await;r};yield;return *view;'''
        self.refused(self.program(invalid,STRUCT+task+factory),'survi|durable|emprunt|réserv|référenc|local')

    def test_launch_failure_and_inactive_cleanup(self):
        source=STRUCT+DETACH+MAKE+'fn main(){'+SETUP+'''let t=make(->v);let h=runtime::spawn(->t);
            match h.join(){Ok(r)=>{print(*r);},Err(_)=>{print(99);}}drop(->a);drop(->b);}'''
        for failure,expected in ((None,'7\n'),(1,'99\n')):
            run=self.run_native(source,fail_submission_at=failure)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('=Pair\n'),1)
        inactive=source[:source.index('let h=runtime::spawn')]+ 'drop(->t);drop(->a);drop(->b);}'
        self.assertEqual(self.run_source(inactive).stderr.count('=Pair\n'),1)

    def test_public_handle_result_keeps_target_only(self):
        prefix=STRUCT+DETACH+'''fn start(v:->Pair)-><-runtime::Handle<&Int>{return <-runtime::spawn(->detach(->v));}'''
        source=prefix+'fn main(){'+SETUP+'''let h=start(->v);let view=match h.join(){Ok(r)=>{r},Err(_)=>{return;}};
            drop(->b);print(*view);drop(->a);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('drop(->b);','drop(->a);').replace('print(*view);drop(->a);','print(*view);'),'emprunt|réserv|référenc')

    def test_waiter_contract_projects_field_after_join(self):
        helper='''fn finish(h:->Execution<detach>,fallback:&Int)->&Int{
            match h.join(){Ok(view)=>{return view;},Err(_)=>{return fallback;}}}'''
        source=STRUCT+DETACH+MAKE+helper+'fn main(){'+SETUP+'''let h=runtime::spawn(->make(->v));
            let view=finish(->h,&a);drop(->b);print(*view);drop(->a);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'7\n')
        self.refused(source.replace('drop(->b);','drop(->a);').replace('print(*view);drop(->a);','print(*view);'),'emprunt|réserv|référenc')

    def test_select_keeps_loser_until_drop(self):
        prefix=STRUCT+DETACH+MAKE+'async fn ready(n:&Int)->&Int{return n;}'
        body=SETUP+'''let mut other=pool<Int>(1);let c=other.new(11);
            let mut s=runtime::select(->make(->v),->ready(&c));let view=s.await;
            drop(->s);drop(->b);yield;print(*view);drop(->a);drop(->c);return 13;'''
        source=self.program(body,prefix)
        self.assertEqual(self.run_source(source).stdout,'11\n13\n')
        invalid=source.replace('drop(->b);','').replace('drop(->s);','drop(->b);drop(->s);')
        self.refused(invalid,'emprunt|réserv|référenc')
        invalid=source.replace('drop(->c);','').replace('yield;print(*view);','drop(->c);yield;print(*view);')
        self.refused(invalid,'emprunt|réserv|référenc')

    def test_return_follows_field_replacement_at_completion(self):
        prefix=STRUCT+'async fn detach(mut v:->Pair)->&Int{v.left=v.right;yield;return v.left;}'+MAKE
        body=SETUP+'let view=make(->v).await;drop(->a);yield;print(*view);drop(->b);return 11;'
        source=self.program(body,prefix)
        self.assertEqual(self.run_source(source).stdout,'9\n11\n')
        invalid=source.replace('drop(->b);','').replace('yield;print(*view);','drop(->b);yield;print(*view);')
        self.refused(invalid,'emprunt|réserv|référenc')
        invalid=source.replace('v.left=v.right;', 'let mut ps=pool<Int>(1);let n=ps.new(3);v.left=&n;')
        self.refused(invalid,'local|durable|retour|emprunt|paramètre')

    def test_repeated_return_releases_target_after_last_use(self):
        body='''let mut ns=pool<Int>(2);let b=ns.new(9);let mut i=0;
            while i<3{let a=ns.new(i);let v=Pair{left:&a,right:&b};let view=make(->v).await;
              yield;print(*view);drop(->a);i=i+1;continue;}print(*b);drop(->b);return i;'''
        source=self.program(body)
        self.assertEqual(self.run_source(source).stdout,'0\n1\n2\n9\n3\n')
        invalid=source.replace('drop(->a);','').replace('yield;print(*view);','drop(->a);yield;print(*view);')
        self.refused(invalid,'emprunt|réserv|référenc')

if __name__=='__main__':unittest.main()
