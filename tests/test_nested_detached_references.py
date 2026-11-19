"""Only the selected descendant target survives an owning task's completion."""
from pathlib import Path
import unittest
import test_select_source as sources
import test_native_blocks as native

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '''struct Inner{view:&Int}struct Outer{inner:A<Inner>}
fn read(value:&Inner)->&Int{return value.view;}
async fn detach(value:->Outer)->&Int{yield;return read(&*value.inner);}
fn make(value:->Outer)-><-detach{return <-detach(->value);}'''
SETUP = '''let mut ns=pool<Int>(1);let n=ns.new(9);
let mut ins=pool<Inner>(1);let inner=ins.new(view:&n);
let outer=Outer{inner:<-inner};'''


class NestedDetachedReferenceTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    run_native = native.NativeBlockTests.run_native

    @staticmethod
    def program(body, prefix=PREFIX):
        return prefix + 'async fn work()->Int{' + body + '''}
fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_detachment(self):
        source = (ROOT/'validation/open-nested-detached-reference.crb').read_text()
        run = self.run_source(source)
        self.assertEqual(run.stdout, '9\n')
        self.assertEqual(run.stderr.count('=Outer\n'), 1)
        self.assertEqual(run.stderr.count('=Inner\n'), 1)
        invalid = source.replace('    drop(->number);', '').replace('    print(*view);', '    drop(->number);\n    print(*view);')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_target_survives_direct_and_factory_await(self):
        for call in ('detach', 'make'):
            body = SETUP + 'let view=' + call + '(->outer).await;yield;print(*view);drop(->n);return 1;'
            with self.subTest(call=call):
                self.assertEqual(self.run_source(self.program(body)).stdout, '9\n1\n')
                invalid = body.replace('drop(->n);', '').replace('yield;print(*view);', 'drop(->n);yield;print(*view);')
                self.refused(self.program(invalid), 'emprunt|réserv|référenc')

    def test_carrier_pools_may_end_but_target_may_not(self):
        for call in ('detach', 'make'):
            body = '''let mut ns=pool<Int>(1);let n=ns.new(9);
let view={let mut ins=pool<Inner>(1);let mut outs=pool<Outer>(1);
let inner=ins.new(view:&n);let outer=outs.new(inner:<-inner);
let view=CALL(->outer).await;view};yield;print(*view);drop(->n);return 1;'''.replace('CALL', call)
            self.assertEqual(self.run_source(self.program(body)).stdout, '9\n1\n')
            invalid = body.replace('let mut ns=pool<Int>(1);let n=ns.new(9);', '').replace(
                'let view={', 'let view={let mut ns=pool<Int>(1);let n=ns.new(9);', 1).replace('drop(->n);', '')
            self.refused(self.program(invalid), 'durable|survi|emprunt|référenc|local')

    def test_exact_target_access_model(self):
        prefix = '''struct Inner{view:&Int}struct Pair{left:A<Inner>,right:A<Inner>}
fn read(v:&Inner)->&Int{return v.view;}
async fn detach(v:->Pair)->&Int{yield;return read(&*v.left);}
fn make(v:->Pair)-><-detach{return <-detach(->v);}'''
        setup = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let mut ins=pool<Inner>(2);let l=ins.new(view:&a);let r=ins.new(view:&b);
let v=Pair{left:<-l,right:<-r};'''
        # Independent rule model: both targets are held before completion,
        # only the selected left target remains held by the returned view.
        for call in ('detach', 'make'):
            for target in ('a', 'b'):
                for completed in (False, True):
                    body = setup + 'let t=CALL(->v);BEFORE let view=t.await;AFTER yield;print(*view);return 1;'
                    operation = 'drop(->' + target + ');'
                    body = body.replace('CALL', call).replace('BEFORE', '' if completed else operation).replace(
                        'AFTER', operation if completed else '')
                    with self.subTest(call=call, target=target, completed=completed):
                        if completed and target == 'b':
                            self.assertEqual(self.run_source(self.program(body, prefix)).stdout, '7\n1\n')
                        else:
                            self.refused(self.program(body, prefix), 'emprunt|réserv|référenc')

    def test_nested_helper_chain(self):
        prefix = '''struct Inner{view:&Int}struct Middle{inner:A<Inner>}struct Outer{middle:A<Middle>}
fn read(v:&Inner)->&Int{return v.view;}
fn through(v:&Middle)->&Int{return read(&*v.inner);}
async fn detach(v:->Outer)->&Int{yield;return through(&*v.middle);}
fn make(v:->Outer)-><-detach{return <-detach(->v);}'''
        body = '''let mut ns=pool<Int>(1);let n=ns.new(9);
let view={let mut ins=pool<Inner>(1);let mut mids=pool<Middle>(1);
let i=ins.new(view:&n);let m=mids.new(inner:<-i);let o=Outer{middle:<-m};
let view=make(->o).await;view};yield;print(*view);drop(->n);return 1;'''
        self.assertEqual(self.run_source(self.program(body, prefix)).stdout, '9\n1\n')
        invalid = body.replace('drop(->n);', '').replace('yield;print(*view);', 'drop(->n);yield;print(*view);')
        self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_public_handle_and_waiter(self):
        extras = '''fn start(v:->Outer)-><-runtime::Handle<&Int>{return <-runtime::spawn(->make(->v));}
fn finish(h:->Execution<detach>,fallback:&Int)->&Int{
match h.join(){Ok(view)=>{return view;},Err(_)=>{return fallback;}}}'''
        for creation in ('''let h=start(->outer);let view=match h.join(){Ok(r)=>{r},Err(_)=>{return;}};''',
                         '''let h=runtime::spawn(->make(->outer));let view=finish(->h,&n);'''):
            source = PREFIX + extras + 'fn main(){' + SETUP + creation + 'print(*view);drop(->n);}'
            self.assertEqual(self.run_source(source).stdout, '9\n')
            self.refused(source.replace('print(*view);drop(->n);', 'drop(->n);print(*view);'),
                         'emprunt|réserv|référenc')

    def test_launch_failure_inactive_and_reuse(self):
        source = PREFIX + 'fn main(){' + SETUP + '''let t=make(->outer);ACTION
let next=ins.new(view:&n);drop(->next);drop(->n);}'''
        self.assertEqual(self.run_source(source.replace('ACTION', 'drop(->t);')).stdout, '')
        launched = source.replace('ACTION', '''let h=runtime::spawn(->t);
match h.join(){Ok(view)=>{print(*view);},Err(_)=>{print(99);}}''')
        for failure, expected in ((None, '9\n'), (1, '99\n')):
            run = self.run_native(launched, fail_submission_at=failure)
            self.assertEqual(run.stdout, expected)
            self.assertEqual(run.stderr.count('=Inner\n'), 2)
            self.assertEqual(run.stderr.count('=Outer\n'), 1)

    def test_public_handle_selects_only_returned_target(self):
        prefix = '''struct Inner{view:&Int}struct Pair{left:A<Inner>,right:A<Inner>}
fn read(v:&Inner)->&Int{return v.view;}
async fn detach(v:->Pair)->&Int{yield;return read(&*v.left);}
fn make(v:->Pair)-><-detach{return <-detach(->v);}
fn start(v:->Pair)-><-runtime::Handle<&Int>{return <-runtime::spawn(->make(->v));}'''
        body = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let mut ins=pool<Inner>(2);let l=ins.new(view:&a);let r=ins.new(view:&b);
let v=Pair{left:<-l,right:<-r};let h=start(->v);
let view=match h.join(){Ok(r)=>{r},Err(_)=>{return;}};
drop(->b);print(*view);drop(->a);'''
        source = prefix + 'fn main(){' + body + '}'
        self.assertEqual(self.run_source(source).stdout, '7\n')
        invalid = source.replace('drop(->a);', '').replace('drop(->b);', 'drop(->a);')
        self.refused(invalid, 'emprunt|réserv|référenc')
        async_body = body.replace('h.join()', 'h.await').replace('return;', 'return 99;').replace(
            'Ok(r)=>{r}', 'Ok(found)=>{found}') + 'return 1;'
        async_source = self.program(async_body, prefix)
        self.assertEqual(self.run_source(async_source).stdout, '7\n1\n')
        invalid = async_source.replace('drop(->a);', '').replace('drop(->b);', 'drop(->a);')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_conditional_return_keeps_all_possible_targets(self):
        prefix = '''struct Inner{view:&Int}struct Pair{left:A<Inner>,right:A<Inner>}
fn read(v:&Inner)->&Int{return v.view;}
async fn detach(v:->Pair,flag:Bool)->&Int{
if flag{return read(&*v.left);}yield;return read(&*v.right);}
fn make(v:->Pair,flag:bool)-><-detach{return <-detach(->v,flag);}'''
        for flag, expected in (('true', 7), ('false', 9)):
            body = '''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let mut ins=pool<Inner>(2);let l=ins.new(view:&a);let r=ins.new(view:&b);
let v=Pair{left:<-l,right:<-r};let view=make(->v,FLAG).await;
yield;print(*view);drop(->a);drop(->b);return 1;'''.replace('FLAG', flag)
            source = self.program(body, prefix)
            self.assertEqual(self.run_source(source).stdout, f'{expected}\n1\n')
            for target in ('a', 'b'):
                invalid = source.replace('drop(->' + target + ');', '').replace(
                    'yield;print(*view);', 'drop(->' + target + ');yield;print(*view);')
                self.refused(invalid, 'emprunt|réserv|référenc')

    def test_owned_storage_and_mutable_field_cannot_be_detached_by_copy(self):
        for field, result, initializer in (
                ('Int', '&v.view', '9'), ('&mut Int', 'v.view', '&mut n')):
            prefix = '''struct Inner{view:FIELD}struct Outer{inner:A<Inner>}
fn read(v:&Inner)->&Int{return RESULT;}
async fn detach(v:->Outer)->&Int{yield;return read(&*v.inner);}
fn make(v:->Outer)-><-detach{return <-detach(->v);}'''.replace('FIELD', field).replace('RESULT', result)
            setup = SETUP.replace('let n=', 'let mut n=').replace('view:&n', 'view:' + initializer)
            source = self.program(setup + 'let view=make(->outer).await;return *view;', prefix)
            self.refused(source, 'local|durable|retour|emprunt|propriétaire|mutable|partagé|paramètre|type')

    def test_select_loser_keeps_nested_capture_until_drop(self):
        prefix = PREFIX + 'async fn ready(n:&Int)->&Int{return n;}'
        body = SETUP + '''let mut other=pool<Int>(1);let b=other.new(11);
let mut s=runtime::select(->make(->outer),->ready(&b));let view=s.await;
drop(->s);yield;print(*view);drop(->n);drop(->b);return 1;'''
        source = self.program(body, prefix)
        run = self.run_source(source)
        self.assertEqual(run.stdout, '11\n1\n')
        self.assertEqual(run.stderr.count('=Inner\n'), 1)
        self.assertEqual(run.stderr.count('=Outer\n'), 1)
        invalid = source.replace('drop(->n);', '').replace('drop(->s);', 'drop(->n);drop(->s);')
        self.refused(invalid, 'emprunt|réserv|référenc')
        invalid = source.replace('drop(->b);', '').replace('yield;print(*view);', 'drop(->b);yield;print(*view);')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_loop_reuses_carrier_slot_after_detachment(self):
        body = '''let mut ns=pool<Int>(1);let mut ins=pool<Inner>(1);let mut i=0;
while i<3{let n=ns.new(i);let inner=ins.new(view:&n);let outer=Outer{inner:<-inner};
let view=make(->outer).await;let next=ins.new(view:&n);drop(->next);
yield;print(*view);drop(->n);i=i+1;continue;}return i;'''
        source = self.program(body)
        run = self.run_source(source)
        self.assertEqual(run.stdout, '0\n1\n2\n3\n')
        self.assertEqual(run.stderr.count('=Inner\n'), 6)
        self.assertEqual(run.stderr.count('=Outer\n'), 3)
        invalid = source.replace('drop(->n);', '').replace('yield;print(*view);', 'drop(->n);yield;print(*view);')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_native_thread_returns_target_without_carriers(self):
        source = PREFIX + 'fn main(){' + SETUP + '''
let h=runtime::thread({->(outer);return read(&*outer.inner);});
let view=match h.join(){Ok(r)=>{r},Err(_)=>{return;}};
let next=ins.new(view:&n);drop(->next);print(*view);drop(->n);}'''
        run = self.run_native(source)
        self.assertEqual(run.stdout, '9\n')
        self.assertEqual(run.stderr.count('=Inner\n'), 2)
        self.assertEqual(run.stderr.count('=Outer\n'), 1)
        failed = self.run_native(source, fail_native=True)
        self.assertEqual(failed.stdout, '')
        self.assertEqual(failed.stderr.count('=Inner\n'), 1)
        self.assertEqual(failed.stderr.count('=Outer\n'), 1)
        invalid = source.replace('drop(->n);', '').replace('print(*view);', 'drop(->n);print(*view);')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_sync_owned_detacher_preserves_target_in_async_caller(self):
        prefix = PREFIX + 'fn take(v:->Outer)->&Int{return read(&*v.inner);}'
        body = SETUP + 'let view=take(->outer);yield;print(*view);drop(->n);return 1;'
        source = self.program(body, prefix)
        self.assertEqual(self.run_source(source).stdout, '9\n1\n')
        invalid = source.replace('drop(->n);', '').replace('yield;print(*view);', 'drop(->n);yield;print(*view);')
        self.refused(invalid, 'emprunt|réserv|référenc')


if __name__ == '__main__':
    unittest.main()
