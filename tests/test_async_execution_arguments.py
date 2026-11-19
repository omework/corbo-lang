"""Launched handles cross sync calls from async states without hidden waits."""
from pathlib import Path
import unittest
from crust import verify_program,compile_source
import test_select_source as sources
from scheduler_faults import inject_submission_failure

ROOT=Path(__file__).resolve().parents[1]

class AsyncExecutionArgumentTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    program=staticmethod(sources.SelectSourceTests.program)

    def test_recorded_structure_handle(self):
        source=(ROOT/'validation/open-public-structure-async-relay.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n1\n')
        for marker in ('let next=relay', 'yield;print(*result.target);'):
            self.refused(source.replace('drop(->n);','').replace(marker,'drop(->n);'+marker),'emprunt|réserv|référenc')

    def test_scalar_handle_relay_and_result_detachment(self):
        helpers='''async fn read(n:&Int)->Int{yield;return *n;}
fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
fn again(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-relay(->h);}'''
        body='''let mut ns=pool<Int>(1);let n=ns.new(7);
let h=runtime::spawn(->read(&n));let next=again(->h);
let result=match next.await{Ok(found)=>{found},Err(_)=>{return 99;}};drop(->n);
let reuse=ns.new(9);print(*reuse);return result;'''
        source=self.program(body,helpers)
        self.assertEqual(self.run_source(source).stdout,'9\n7\n')
        for marker in ('let next=again', 'let result=match'):
            self.refused(self.program(body.replace('drop(->n);','').replace(marker,'drop(->n);'+marker),helpers),'emprunt|réserv|référenc')
        self.refused(self.program(body.replace('let result=match','let old=h.await;print(old);let result=match'),helpers),'consomm|attendu|utilisable|déplac')
        self.refused(self.program(body.replace('again(->h)','again(h)'),helpers),'transfert|mode')

    def test_shared_and_mutable_results_keep_last_use(self):
        for access in ('','mut '):
            helpers='async fn read(n:&'+access+'Int)->&'+access+'Int{yield;return n;}'+'''
fn relay(h:->runtime::Handle<TYPE>)-><-runtime::Handle<TYPE>{return <-h;}'''.replace('TYPE','&'+access+'Int')
            body='''let mut ns=pool<Int>(1);let mut n=ns.new(7);let h=runtime::spawn(->read(&ACCESSn));
let next=relay(->h);let mut view=match next.await{Ok(v)=>{v},Err(_)=>{return 99;}};
yield;print(*view);drop(->n);return 1;'''.replace('ACCESS',access)
            self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'7\n1\n')
            self.refused(self.program(body.replace('drop(->n);','').replace('yield;print(*view);','drop(->n);yield;print(*view);'),helpers),'emprunt|réserv|référenc')

    def test_later_argument_suspends_with_handle_obligation(self):
        helpers='''async fn read(n:&Int)->Int{yield;return *n;}
fn relay(h:->runtime::Handle<Int>,x:Int)-><-runtime::Handle<Int>{print(x);return <-h;}'''
        body='''let mut ns=pool<Int>(1);let mut n=ns.new(7);let h=runtime::spawn(->read(&n));
let next=relay(->h,{yield;print(2);3});let r=match next.await{Ok(found)=>{found},Err(_)=>{return 99;}};drop(->n);return r;'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'2\n3\n7\n')
        for replacement in ('{yield;n=9;3}', '{n ->;yield;drop(->n);3}', '{yield;return 3;}'):
            self.refused(self.program(body.replace('{yield;print(2);3}',replacement),helpers),'emprunt|réserv|référenc|attente|handle|attend')

    def test_computed_handle_arguments(self):
        helpers='''async fn read()->Int{yield;return 7;}
fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
fn start()-><-runtime::Handle<Int>{return <-runtime::spawn(->read());}'''
        for operand in ('runtime::spawn(->read())', 'start()', '{let h=runtime::spawn(->read());<-h}'):
            source=self.program('let next=relay(->'+operand+');return match next.await{Ok(found)=>{found},Err(_)=>{99}};',helpers)
            self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_no_resubmission_and_launch_failure_relay(self):
        helpers='''#(directive, async_pool_sizes={read:1,work:1})
async fn read()->Int{yield;return 7;}
fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}'''
        body='''let h=runtime::spawn(->read());let a=relay(->h);yield;let b=relay(->a);
return match b.await{Ok(found)=>{found},Err(_)=>{99}};'''
        source=self.program(body,helpers)
        self.assertEqual(self.run_source(source).stdout,'7\n')
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=True,at=0,maximum=1)).stdout,'7\n')
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=True,at=1,maximum=1)).stdout,'99\n')

    def test_native_and_blocking_handles_relay_without_relaunch(self):
        helpers='async fn read()->Int{yield;return 7;}fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}'
        for operand in ('runtime::spawn_blocking(->read())','runtime::thread({7})'):
            source=self.program('let h='+operand+';let next=relay(->h);return match next.await{Ok(found)=>{found},Err(_)=>{99}};',helpers)
            self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_join_cannot_be_hidden_by_sync_helper(self):
        helpers='''async fn read()->Int{return 7;}
fn wait(h:->runtime::Handle<Int>)->Int{return match h.join(){Ok(found)=>{found},Err(_)=>{99}};}'''
        self.refused(self.program('let h=runtime::spawn(->read());return wait(->h);',helpers),'join réservé au code synchrone')

    def test_loop_exits_preserve_prepared_handle_obligation(self):
        helpers='''async fn read()->Int{yield;return 7;}
fn relay(h:->runtime::Handle<Int>,x:Int)-><-runtime::Handle<Int>{return <-h;}'''
        for exit in ('break','continue'):
            body='''let mut i=0;while i<2{let h=runtime::spawn(->read());i=i+1;
let next=relay(->h,{yield;EXIT;});let r=next.await;print(r);}return i;'''.replace('EXIT',exit)
            self.refused(self.program(body,helpers),'attente|handle|attend')
        body='''let h=runtime::spawn(->read());let next=relay(->h,loop{yield;break 3;});
return match next.await{Ok(found)=>{found},Err(_)=>{99}};'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'7\n')

    def test_return_before_handle_argument_does_not_launch_it(self):
        helpers='''async fn read()->Int{yield;return 7;}
fn relay(x:Int,h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}'''
        body='''let next=relay({yield;return 3;},->runtime::spawn(->read()));
return match next.await{Ok(found)=>{found},Err(_)=>{99}};'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'3\n')

    def test_select_refuses_prepared_launched_handle(self):
        helpers='''async fn read()->Int{yield;return 7;}
fn relay(h:->runtime::Handle<Int>,x:Int)-><-runtime::Handle<Int>{return <-h;}
async fn left()->Int{let h=runtime::spawn(->read());let next=relay(->h,{yield;3});
return match next.await{Ok(found)=>{found},Err(_)=>{99}};}
async fn ready()->Int{return 9;}'''
        body='let mut s=runtime::select(->left(),->ready());let n=s.await;drop(->s);return n;'
        self.refused(self.program(body,helpers),'SL2|handle lancé|attente|suspendu')

    def test_pool_result_and_repeated_state_slot_reuse(self):
        source='''#(directive, async_pool_sizes={own:1,work:1})
struct Point{x:Int}async fn own(p:->Point)-><-A<Point>{yield;return <-p;}
fn relay(h:->runtime::Handle<A<Point>>)-><-runtime::Handle<A<Point>>{return <-h;}
async fn work()->Int{let mut ps=pool<Point>(1);let mut i=0;while i<3{let p=ps.new(x:i);
let h=runtime::spawn(->own(->p));let next=relay(->h);
let result=match next.await{Ok(found)=>{<-found},Err(_)=>{return 99;}};print(result.x);drop(->result);i=i+1;}return i;}
fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'0\n1\n2\n3\n')
        self.assertEqual(run.stderr.count('=Point\n'),3)
        self.refused(source.replace('let p=ps.new(x:i);','let p=Point{x:i};'),'stockage|local|allocation')

    def test_concrete_handle_type_and_short_capture_scope(self):
        helpers='''async fn first(n:&Int)->Int{yield;return *n;}
async fn second(n:&Int)->Int{yield;return *n;}
fn relay(h:->Execution<first>)-><-Execution<first>{return <-h;}'''
        body='''let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->first(&n));let next=relay(->h);
return match next.await{Ok(found)=>{found},Err(_)=>{99}};'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'7\n')
        self.refused(self.program(body.replace('spawn(->first(&n))','spawn(->second(&n))'),helpers),'type|attendu|requis')
        body='''let next={let mut ns=pool<Int>(1);let n=ns.new(7);let h=runtime::spawn(->first(&n));
let relayed=relay(->h);<-relayed};return match next.await{Ok(found)=>{found},Err(_)=>{99}};'''
        self.refused(self.program(body,helpers),'survi|durable|capture|emprunt')

    def test_array_payload_and_borrowed_view(self):
        helpers='''async fn read(a:&mut [Int;2])->[Int;2]{yield;let result=[a[0],a[1]];return <-result;}
fn relay(h:->runtime::Handle<[Int;2]>)-><-runtime::Handle<[Int;2]>{return <-h;}'''
        body='''let mut a=[7,9];let h=runtime::spawn(->read(&mut a));let next=relay(->h);
let values=match next.await{Ok(v)=>{<-v},Err(_)=>{return 99;}};drop(->a);return values[1];'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'9\n')
        self.refused(self.program(body.replace('drop(->a);','').replace('let values=match','drop(->a);let values=match'),helpers),'emprunt|réserv|référenc')
        helpers='''async fn text(s:&str)->&str{yield;return s;}
fn relay(h:->runtime::Handle<&str>)-><-runtime::Handle<&str>{return <-h;}'''
        body='let h=runtime::spawn(->text("é"));let next=relay(->h);match next.await{Ok(v)=>{print(v);},Err(_)=>{return 99;}}return 1;'
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'é\n1\n')

    def test_pending_field_changes_cross_the_relay(self):
        source=(ROOT/'validation/open-async-execution-argument-field-effects.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'9\n9\n')
        check=verify_program(source)
        self.assertTrue(check.async_definitions['work'][0].field_effect_summary.complete)
        for name in ('a','b'):
            self.refused(source.replace('print(*v.data);','drop(->'+name+');print(*v.data);'),'emprunt|réserv|référenc')
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=True,at=1)).stdout,'99\n7\n')

    def test_native_block_can_explicitly_wait_via_helper(self):
        helpers='''async fn read()->Int{yield;return 7;}
fn wait(h:->runtime::Handle<Int>)->Int{return match h.join(){Ok(found)=>{found},Err(_)=>{99}};}'''
        body='''let outer=runtime::thread({let h=runtime::spawn(->read());wait(->h)});
return match outer.await{Ok(found)=>{found},Err(_)=>{99}};'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'7\n')

    def test_native_helper_wait_applies_field_changes(self):
        source=(ROOT/'validation/open-native-wait-argument-field-effects.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'9\n9\n1\n')
        for name in ('a','b'):
            invalid=source.replace('drop(->'+name+');','').replace('print(*v.data);','drop(->'+name+');print(*v.data);')
            self.refused(invalid,'emprunt|réserv|référenc')

    def test_native_helper_wait_publishes_captured_field_changes(self):
        helpers=(ROOT/'validation/open-native-wait-argument-field-effects.crb').read_text().split('fn main()')[0]
        source=helpers+'''fn main(){
let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let mut v=View{data:&a};
let mut porteur=&mut v;let cible=&b;
let outer=runtime::thread({->(porteur,cible);
let h=runtime::spawn(->update(porteur,cible));let n=wait(->h);print(n);1});
match outer.join(){Ok(n)=>{print(n);},Err(_)=>{}}
print(*v.data);drop(->v);drop(->a);drop(->b);}'''
        self.assertEqual(self.run_source(source).stdout,'9\n1\n9\n')
        for name in ('a','b'):
            invalid=source.replace('drop(->'+name+');','').replace('print(*v.data);','drop(->'+name+');print(*v.data);')
            self.refused(invalid,'emprunt|réserv|référenc')
        code=compile_source(source)
        self.assertEqual(self.run_c_oracle(inject_submission_failure(code,asynchronous=True,at=1)).stdout,'99\n1\n7\n')

    def test_runtime_handoff_preserves_wait_obligation(self):
        # Exercise the ABI handoff directly, without a scheduler or a wait:
        # both a live execution and a launch error must survive conversion.
        code=compile_source(self.program(
            'let h=runtime::spawn(->read());return match h.await{Ok(n)=>{n},Err(_)=>{99}};',
            'async fn read()->Int{return 7;}'))
        code=code.replace('int main(void) {','int crust_program_main(void) {')
        code+='''
int main(void) {
    CrustTask task = {0};
    for (int failed = 0; failed < 2; ++failed) {
        CrustAsyncExecution source = {failed ? NULL : &task, failed ? EAGAIN : 0};
        CrustExecution received;
        task_sync_adopt(&received, &source);
        if (received.task != (failed ? NULL : &task)) return 1;
        if (received.error != (failed ? EAGAIN : 0)) return 2;
        if (source.task || source.error || atomic_load(&received.joined)) return 3;
        if (!received.pooled) return 4;
    }
    return 0;
}
'''
        self.run_c_oracle(code)

if __name__=='__main__':unittest.main()
