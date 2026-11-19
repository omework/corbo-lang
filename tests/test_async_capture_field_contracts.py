"""Capture field identities survive task relays and whole owned results."""
from pathlib import Path
import unittest
from crust import verify_program
import test_select_source as source_tests
import test_native_blocks as native_tests

ROOT = Path(__file__).resolve().parents[1]
VIEW = 'struct View{data:&Int}async fn relay(v:->View)-><-View{yield;return <-v;}'
PAIR = 'struct Pair{read:&Int,write:&mut Int}async fn relay(v:->Pair)-><-Pair{yield;return <-v;}'

class CaptureFieldContractTests(unittest.TestCase):
    run_source = source_tests.SelectSourceTests.run_source
    run_c_oracle = source_tests.SelectSourceTests.run_c_oracle
    refused = source_tests.SelectSourceTests.refused
    run_native = native_tests.NativeBlockTests.run_native

    def test_mixed_task_relay_and_independent_access_model(self):
        source = (ROOT/'validation/open-owned-borrowed-mixed-task-relay.crb').read_text()
        for relay in ('relay(->task)', 'again(->task)'):
            program = source.replace('fn main()', 'fn again(t:->compute)-><-compute{return <-relay(->t);}fn main()')
            program = program.replace('let forwarded=relay(->task)', 'let forwarded='+relay)
            self.assertEqual(self.run_source(program).stdout, '7\n7\n7\n')
            # Independent access table: a shared loan permits read only;
            # a mutable loan permits no access through the original binding.
            for target, access, allowed in (
                    ('a','read',True),('a','write',False),('a','drop',False),
                    ('b','read',False),('b','write',False),('b','drop',False)):
                operation = {'read':f'print(*{target});', 'write':f'{target}=20;', 'drop':f'drop(->{target});'}[access]
                variant = program.replace('let a=', 'let mut a=').replace('let h=runtime::spawn', operation+'let h=runtime::spawn')
                with self.subTest(relay=relay,target=target,access=access):
                    if allowed:self.assertEqual(self.run_source(variant).stdout, '7\n7\n7\n7\n')
                    else:self.refused(variant,'emprunt|réserv|référenc')
        contract = verify_program(source).function_contracts['relay'].result
        self.assertEqual({(key,t.field) for key,targets in contract.borrowed_fields for t in targets},
                         {('ref.0/.read','0/.read'),('mut.0/.write','0/.write')})

    def test_whole_return_recorded_and_drop_boundary(self):
        source = (ROOT/'validation/open-owned-borrowed-capture-result-owner.crb').read_text()
        run = self.run_source(source)
        self.assertEqual(run.stdout,'7\n')
        self.assertEqual(run.stderr.count('=View\n'),1)
        self.refused(source.replace('Ok(v)=>{print','Ok(v)=>{drop(->n);print'),'emprunt|réserv|référenc')
        self.refused(source.replace('match h.join()', 'drop(->n);match h.join()'),'emprunt|réserv|référenc')

    def test_return_factory_and_task_relays(self):
        source = (ROOT/'validation/open-owned-borrowed-capture-result-owner.crb').read_text()
        helpers = 'fn make(v:->View)-><-relay{return <-relay(->v);}fn again(t:->relay)-><-relay{return <-t;}'
        source = source.replace('fn main()', helpers+'fn main()')
        for call in ('make(->v)','again(->make(->v))'):
            program = source.replace('runtime::spawn(->relay(->v))','runtime::spawn(->'+call+')')
            self.assertEqual(self.run_source(program).stdout,'7\n')
            self.refused(program.replace('Ok(v)=>{print','Ok(v)=>{drop(->n);print'),'emprunt|réserv|référenc')

    def test_mutable_return_and_last_use(self):
        source = PAIR+'''fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let mut b=ns.new(9);
            let v=Pair{read:&a,write:&mut b};let h=runtime::spawn(->relay(->v));
            match h.join(){Ok(v)=>{let mut got=<-v;let mut w=&mut *got.write;w.set(*got.read);print(*w);drop(->got);},Err(_)=>{}}
            print(*b);drop(->a);drop(->b);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n7\n')
        for operation in ('print(*b);','b=11;','drop(->a);','drop(->b);','drop(->got);'):
            self.refused(source.replace('w.set(*got.read);',operation+'w.set(*got.read);'),'emprunt|réserv|référenc')

    @staticmethod
    def async_program(body,helpers='',prefix=VIEW):
        return prefix+helpers+'async fn work()->Int{'+body+'''}fn main(){let h=runtime::spawn(->work());
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_async_caller_direct_and_factory(self):
        helpers='fn make(v:->View)-><-relay{return <-relay(->v);}'
        for call in ('relay(->v)','make(->v)'):
            body='''let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{data:&n};let child=CALL;
                let got=child.await;yield;print(*got.data);drop(->got);drop(->n);let next=ns.new(9);return *next;'''.replace('CALL',call)
            source=self.async_program(body,helpers)
            self.assertEqual(self.run_source(source).stdout,'7\n9\n')
            for marker in ('let got=child.await;','yield;print(*got.data);'):
                self.refused(source.replace('drop(->n);','').replace(marker,'drop(->n);'+marker),'emprunt|réserv|référenc|capture')

    def test_shared_fields_detach_independently_after_relay(self):
        prefix='struct Pair{left:&Int,right:&Int}async fn relay(v:->Pair)-><-Pair{yield;return <-v;}'
        source=prefix+'''fn make(v:->Pair)-><-relay{return <-relay(->v);}fn again(t:->relay)-><-relay{return <-t;}
            fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let v=Pair{left:&a,right:&b};
            let h=runtime::spawn(->again(->make(->v)));let got=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};
            let left=got.left;drop(->got);drop(->b);print(*left);drop(->a);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('print(*left);','drop(->a);print(*left);'),'emprunt|réserv|référenc')
        async_body='''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let v=Pair{left:&a,right:&b};
            let got=relay(->v).await;let left=got.left;drop(->got);drop(->b);yield;print(*left);drop(->a);return 11;'''
        for call in ('relay','make'):
            program=self.async_program(async_body.replace('relay(->v).await','CALL(->v).await'.replace('CALL',call)),
                helpers='fn make(v:->Pair)-><-relay{return <-relay(->v);}',prefix=prefix)
            self.assertEqual(self.run_source(program).stdout,'7\n11\n')
            self.refused(program.replace('yield;print(*left);','drop(->a);yield;print(*left);'),'emprunt|réserv|référenc')

    def test_pool_root_and_target_lifetime_model(self):
        prefix='struct View{data:&Int}async fn relay(v:->A<View>)-><-A<View>{yield;return <-v;}'
        for root_outer in (False,True):
            for target_outer in (False,True):
                root='let mut vs=pool<View>(1);'
                target='let mut ns=pool<Int>(1);let n=ns.new(7);'
                source=prefix+'fn main(){'+(root if root_outer else '')+(target if target_outer else '')+'let got={'+(
                    '' if root_outer else root)+('' if target_outer else target)+'''let v=vs.new(data:&n);
                    let h=runtime::spawn(->relay(->v));let got=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};<-got};
                    print(*got.data);drop(->got);}'''
                with self.subTest(root=root_outer,target=target_outer):
                    if root_outer and target_outer:self.assertEqual(self.run_source(source).stdout,'7\n')
                    else:self.refused(source,'survi|durable|emprunt|source|scope')

    def test_failure_and_inactive_cleanup_once(self):
        source=VIEW+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{data:&n};let t=relay(->v);
            let h=runtime::spawn(->t);match h.join(){Ok(v)=>{print(*v.data);drop(->v);},Err(_)=>{print(99);}}
            drop(->n);let next=ns.new(9);print(*next);}'''
        for fail,expected in ((None,'7\n9\n'),(1,'99\n9\n')):
            run=self.run_native(source,fail_submission_at=fail)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('=View\n'),1)
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)
        inactive=source[:source.index('let h=runtime::spawn')]+ 'drop(->t);drop(->n);let next=ns.new(9);print(*next);}'
        self.assertEqual(self.run_source(inactive).stdout,'9\n')

    def test_return_through_parent_and_loop(self):
        body='''let mut ns=pool<Int>(1);let n=ns.new(7);let v=View{data:&n};let got={let child=relay(->v);let got=child.await;<-got};
            let mut i=0;while i<2{yield;print(*got.data);i=i+1;continue;}drop(->got);drop(->n);return i;'''
        # The carrier must enter the child explicitly before being consumed there.
        body=body.replace('let got={let child=', 'let got={v ->;let child=')
        source=self.async_program(body)
        self.assertEqual(self.run_source(source).stdout,'7\n7\n2\n')
        self.refused(source.replace('while i<2{','while i<2{n ->;drop(->n);'),'emprunt|réserv|référenc')

    def test_detached_result_releases_unrelated_field(self):
        source='''struct Pair{left:&Int,right:&Int}async fn detach(v:->Pair)->&Int{yield;return v.left;}
            fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let v=Pair{left:&a,right:&b};
            let h=runtime::spawn(->detach(->v));let view=match h.join(){Ok(view)=>{view},Err(_)=>{return;}};
            drop(->b);print(*view);drop(->a);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        self.refused(source.replace('drop(->b);','drop(->a);'),'emprunt|réserv|référenc')

    def test_select_retains_loser_and_returns_winner_fields(self):
        prefix='''struct View{data:&Int}async fn slow(v:->View)-><-View{yield;yield;return <-v;}
            async fn ready(v:->View)-><-View{return <-v;}'''
        body='''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
            let left=View{data:&a};let right=View{data:&b};let mut s=runtime::select(->slow(->left),->ready(->right));
            let got=s.await;drop(->s);yield;print(*got.data);drop(->got);drop(->a);drop(->b);return 11;'''
        source=self.async_program(body,prefix=prefix)
        self.assertEqual(self.run_source(source).stdout,'9\n11\n')
        for marker,target in (('drop(->s);','a'),('print(*got.data);','b')):
            self.refused(source.replace(marker,f'drop(->{target});'+marker),'emprunt|réserv|référenc')

    def test_conditional_return_keeps_each_possible_field(self):
        prefix='''struct View{data:&Int}async fn choose(a:->View,b:->View,flag:Bool)-><-View{
            if flag{return <-a;}yield;return <-b;}'''
        for flag,value in (('true',7),('false',9)):
            source=prefix+'''fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
                let left=View{data:&a};let right=View{data:&b};let h=runtime::spawn(->choose(->left,->right,FLAG));
                let got=match h.join(){Ok(v)=>{<-v},Err(_)=>{return;}};print(*got.data);drop(->got);drop(->a);drop(->b);}'''.replace('FLAG',flag)
            run=self.run_source(source)
            self.assertEqual(run.stdout,f'{value}\n')
            self.assertEqual(run.stderr.count('=View\n'),2)
            for target in ('a','b'):
                self.refused(source.replace('print(*got.data);',f'drop(->{target});print(*got.data);'),'emprunt|réserv|référenc')

    def test_address_stability_and_pool_slot_reuse(self):
        for pooled in (False,True):
            typ='A<View>' if pooled else 'View'
            setup='let mut vs=pool<View>(1);let v=vs.new(data:&n);' if pooled else 'let v=View{data:&n};'
            reuse='let next=vs.new(data:&n);address(next);drop(->next);' if pooled else ''
            source='struct View{data:&Int}async fn relay(v:->'+typ+')-><-'+typ+'''{yield;yield;return <-v;}
                fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);'''+setup+'''address(v);
                let h=runtime::spawn(->relay(->v));match h.join(){Ok(got)=>{address(got);print(*got.data);drop(->got);},Err(_)=>{}}
                '''+reuse+'drop(->n);}'
            lines=self.run_source(source).stdout.splitlines()
            self.assertEqual(lines[0],lines[1])
            self.assertEqual(lines[2],'7')
            if pooled:self.assertEqual(lines[0],lines[3])

if __name__=='__main__':unittest.main()
