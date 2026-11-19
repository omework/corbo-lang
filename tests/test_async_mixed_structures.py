"""Owned children and borrowed targets retain distinct lifetime obligations."""
from pathlib import Path
from itertools import product
import unittest
import test_select_source as sources
import test_native_blocks as native
import test_async_local_parent as placement

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '''struct Mixed{item:A<Int>,view:&Int}
async fn relay(v:->Mixed)-><-Mixed{yield;return <-v;}
fn make(v:->Mixed)-><-relay{return <-relay(->v);}'''
SETUP = '''let mut ns=pool<Int>(1);let a=ns.new(7);
let mut targets=pool<Int>(1);let b=targets.new(9);
let v=Mixed{item:<-a,view:&b};'''


class AsyncMixedStructureTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    run_native = native.NativeBlockTests.run_native
    storage_probe = placement.AsyncLocalParentTests.storage_probe

    @staticmethod
    def program(body, prefix=PREFIX):
        return prefix + 'async fn work()->Int{' + body + '''}
fn main(){let h=runtime::spawn(->work());
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_recorded_capture(self):
        source = (ROOT/'validation/open-mixed-owned-borrowed-capture.crb').read_text()
        self.assertEqual(self.run_source(source).stdout, '16\n')
        invalid = source.replace('    drop(->b);', '').replace(
            '    match h.join()', '    drop(->b);\n    match h.join()')
        self.refused(invalid, 'emprunt|réserv|référenc')

    def test_return_from_direct_and_factory_tasks(self):
        for call in ('relay', 'make'):
            source = self.program(SETUP + 'let r=' + call + '''(->v).await;
yield;print(*r.item);print(*r.view);drop(->r);drop(->b);
let next=ns.new(11);return *next;''')
            with self.subTest(call=call):
                run = self.run_source(source)
                self.assertEqual(run.stdout, '7\n9\n11\n')
                self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
                self.assertEqual(run.stderr.count('=Mixed\n'), 1)
                invalid = source.replace('drop(->b);', '').replace(
                    'yield;print(*r.item);', 'drop(->b);yield;print(*r.item);')
                self.refused(invalid, 'emprunt|réserv|référenc')

    def test_each_owned_source_and_borrow_target_must_survive(self):
        # Independent model: the result needs all three storage lifetimes.
        # A target allocated in an outer pool but created inside also fails:
        # moving the holder cannot promote the borrowed allocation.
        for call in ('relay', 'make'):
            for durable in product((False, True), repeat=3):
                declarations = ('let mut rs=pool<Mixed>(1);',
                                'let mut ns=pool<Int>(1);',
                                'let mut ts=pool<Int>(1);let b=ts.new(9);')
                outer = ''.join(text for text, survives in zip(declarations, durable) if survives)
                inner = ''.join(text for text, survives in zip(declarations, durable) if not survives)
                source = self.program(outer + 'let result={' + inner + '''
let a=ns.new(7);let v=rs.new(item:<-a,view:&b);
let r=CALL(->v).await;<-r};yield;return *result.item+*result.view;'''.replace('CALL', call),
                    prefix=PREFIX.replace('v:->Mixed', 'v:->A<Mixed>').replace('-><-Mixed', '-><-A<Mixed>'))
                with self.subTest(call=call, durable=durable):
                    if all(durable):
                        self.assertEqual(self.run_source(source).stdout, '16\n')
                    else:
                        self.refused(source, 'pool|source|survi|durable|emprunt|référenc|local')

    def test_owner_is_not_structurally_copyable(self):
        for expression in ('copy(v)', 'rs.copy(v)'):
            source = self.program('''let mut ns=pool<Int>(1);let a=ns.new(7);
let mut ts=pool<Int>(1);let b=ts.new(9);let mut rs=pool<Mixed>(2);
let v=rs.new(item:<-a,view:&b);let duplicate=EXPR;
print(*v.item);drop(->duplicate);return 11;'''.replace('EXPR', expression))
            self.refused(source, 'cop|Copy|propriétaire')

    def test_mutable_target_reserved_through_return(self):
        prefix = PREFIX.replace('view:&Int', 'view:&mut Int').replace(
            'relay(v:->Mixed)', 'relay(mut v:->Mixed)').replace(
            'yield;return <-v;', 'yield;let mut p=&mut *v.view;p.set(*v.item);return <-v;')
        setup = SETUP.replace('let b=', 'let mut b=').replace('view:&b', 'view:&mut b')
        for call in ('relay', 'make'):
            source = self.program(setup + 'let r=' + call + '''(->v).await;
yield;print(*r.view);drop(->r);print(*b);return 11;''', prefix)
            self.assertEqual(self.run_source(source).stdout, '7\n7\n11\n')
            for operation in ('print(*b);', 'b=30;', 'drop(->b);'):
                self.refused(source.replace('yield;print(*r.view);', operation + 'yield;print(*r.view);'),
                             'emprunt|réserv|référenc')

    def test_launch_failure_inactive_and_native_cleanup(self):
        body = SETUP + '''let t=make(->v);ACTION
print(*b);let next=ns.new(11);print(*next);}'''
        inactive = PREFIX + 'fn main(){' + body.replace('ACTION', 'drop(->t);')
        run = self.run_source(inactive)
        self.assertEqual(run.stdout, '9\n11\n')
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
        launched = PREFIX + 'fn main(){' + body.replace('ACTION', '''
let h=runtime::spawn(->t);match h.join(){
Ok(r)=>{print(*r.item);drop(->r);},Err(_)=>{print(99);}}''')
        for failure, expected in ((None, '7\n9\n11\n'), (1, '99\n9\n11\n')):
            run = self.run_native(launched, fail_submission_at=failure)
            self.assertEqual(run.stdout, expected)
            self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
            self.assertEqual(run.stderr.count('=Mixed\n'), 1)
        source = PREFIX + 'fn main(){' + SETUP + '''
let h=runtime::thread({->(v);return *v.item+*v.view;});
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
print(*b);let next=ns.new(11);print(*next);}'''
        for failure, expected in ((False, '16\n9\n11\n'), (True, '99\n9\n11\n')):
            run = self.run_native(source, fail_native=failure)
            self.assertEqual(run.stdout, expected)
            self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
            self.assertEqual(run.stderr.count('=Mixed\n'), 1)

    def test_select_losing_owner_retains_borrow_until_cleanup(self):
        prefix = '''struct Mixed{item:A<Int>,view:&Int}
async fn consume(v:->Mixed)->Int{yield;return *v.item+*v.view;}
fn make(v:->Mixed)-><-consume{return <-consume(->v);}
async fn ready()->Int{return 3;}'''
        source = self.program(SETUP + '''
let mut s=runtime::select(->make(->v),->ready());let n=s.await;
drop(->s);drop(->b);let next=ns.new(11);print(*next);return n;''', prefix)
        run = self.run_source(source)
        self.assertEqual(run.stdout, '11\n3\n')
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
        self.assertEqual(run.stderr.count('=Mixed\n'), 1)
        self.refused(source.replace('drop(->s);drop(->b);', 'drop(->b);drop(->s);'),
                     'emprunt|réserv|référenc')

    def test_prepared_mixed_owner_cleanup_on_early_return(self):
        prefix = '''struct Mixed{item:A<Int>,view:&Int}
async fn consume(v:->Mixed,n:Int)->Int{yield;return *v.item+*v.view+n;}
async fn pause()->Int{yield;return 1;}'''
        body = SETUP + 'let n=consume(->v,pause().await).await;return n;'
        self.assertEqual(self.run_source(self.program(body, prefix)).stdout, '17\n')
        early = body.replace('pause().await', '{yield;return 3;}')
        run = self.run_source(self.program(early, prefix))
        self.assertEqual(run.stdout, '3\n')
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
        self.assertEqual(run.stderr.count('=Mixed\n'), 1)
        invalid = body.replace('pause().await', '{b ->;drop(->b);pause().await}')
        self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')
        # The pools outlive the callee: closing its local pools cannot hide
        # an omitted destructor for the already prepared first argument.
        external = prefix + '''
async fn early(ps:&mut Pool<Mixed>,ns:&mut Pool<Int>,b:&Int)->Int{
let a=ns.new(7);let v=ps.new(item:<-a,view:b);
let n=consume(->v,{yield;return 3;}).await;return n;}
fn main(){let mut ps=pool<Mixed>(1);let mut ns=pool<Int>(1);
let mut ts=pool<Int>(1);let b=ts.new(9);
let h=runtime::spawn(->early(&mut ps,&mut ns,&b));
match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
let next=ns.new(11);let root=ps.new(item:<-next,view:&b);print(*root.item);}'''
        run = self.run_source(external)
        self.assertEqual(run.stdout, '3\n11\n')
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)

    def test_detached_view_releases_owned_child_and_root(self):
        prefix = '''struct Mixed{item:A<Int>,view:&Int}
fn get(v:&Mixed)->&Int{return v.view;}
async fn detach(v:->Mixed)->&Int{yield;return get(&v);}
fn make(v:->Mixed)-><-detach{return <-detach(->v);}'''
        for call in ('detach', 'make'):
            body = '''let mut ts=pool<Int>(1);let b=ts.new(9);
let view={let mut rs=pool<Mixed>(1);let mut ns=pool<Int>(1);
let a=ns.new(7);let v=rs.new(item:<-a,view:&b);
let view=CALL(->v).await;view};yield;print(*view);drop(->b);return 11;'''.replace('CALL', call)
            run = self.run_source(self.program(body, prefix))
            self.assertEqual(run.stdout, '9\n11\n')
            self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
            self.assertEqual(run.stderr.count('=Mixed\n'), 1)
            invalid = body.replace('drop(->b);', '').replace('yield;print(*view);',
                                                                      'drop(->b);yield;print(*view);')
            self.refused(self.program(invalid, prefix), 'emprunt|réserv|référenc')

    def test_suspended_prepared_owner_releases_external_slots(self):
        prefix = '''struct Mixed{item:A<Int>,view:&Int}
async fn consume(v:->Mixed,n:Int)->Int{yield;return *v.item+*v.view+n;}
async fn pause()->Int{yield;return 1;}
async fn ready()->Int{return 3;}
async fn waiting(ps:&mut Pool<Mixed>,ns:&mut Pool<Int>,b:&Int)->Int{
let a=ns.new(7);let v=ps.new(item:<-a,view:b);
return consume(->v,pause().await).await;}'''
        body = '''let mut ps=pool<Mixed>(1);let mut ns=pool<Int>(1);
let mut ts=pool<Int>(1);let b=ts.new(9);
let mut s=runtime::select(->waiting(&mut ps,&mut ns,&b),->ready());
let result=s.await;drop(->s);
let next=ns.new(11);let root=ps.new(item:<-next,view:&b);print(*root.item);
drop(->root);drop(->b);return result;'''
        run = self.run_source(self.program(body, prefix))
        self.assertEqual(run.stdout, '11\n3\n')
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
        self.assertEqual(run.stderr.count('=Mixed\n'), 2)

    def test_replacement_and_reuse_across_iterations(self):
        body = '''let mut ns=pool<Int>(2);let mut ts=pool<Int>(1);let b=ts.new(9);
let first=ns.new(1);let mut current=Mixed{item:<-first,view:&b};let mut i=0;
while i<3{let value=ns.new(i+2);let incoming=Mixed{item:<-value,view:&b};
current=<-make(->incoming).await;print(*current.item);i=i+1;}
drop(->current);let next=ns.new(11);print(*next);drop(->b);return 12;'''
        for call in ('relay', 'make'):
            run = self.run_source(self.program(body.replace('make(->incoming)', call + '(->incoming)')))
            self.assertEqual(run.stdout, '2\n3\n4\n11\n12\n')
            self.assertEqual(run.stderr.count('=Mixed\n'), 4)

    def test_transfers_preserve_root_and_child_addresses(self):
        body = '''let mut ns=pool<Int>(1);let a=ns.new(7);
let mut ts=pool<Int>(1);let b=ts.new(9);
let result={a ->;let v=Mixed{item:<-a,view:&b};yield;
let r=make(->v).await;yield;<-r};yield;return *result.item+*result.view;'''
        self.storage_probe(self.program(body), '''
CrustTask *task=crust_async_work_create();Cell *root=NULL,*child=NULL,*target=NULL;
int suspensions=0;
while(task_poll(task)==TASK_SUSPENDED){
    assert(observed_count==1);
    if(!root){root=observed_cells[0];child=cell_load_ref(root,0);
        target=cell_load_ref(root,sizeof(Cell *));}
    assert(root==observed_cells[0] && root->alive);
    assert(cell_load_ref(root,0)==child && cell_load_ref(root,sizeof(Cell *))==target);
    assert(child->alive && target->alive);
    assert(child->value==7 && target->value==9);
    assert(++suspensions<10);
}
assert(suspensions>=3);int answer;assert(task_take(task,&answer));assert(answer==16);
''')
        invalid = '''let mut ns=pool<Int>(1);let mut ts=pool<Int>(1);
let result={let a=ns.new(7);let b=ts.new(9);
let v=Mixed{item:<-a,view:&b};let r=make(->v).await;<-r};return *result.view;'''
        self.refused(self.program(invalid), 'survi|durable|emprunt|référenc|local')

    def test_owned_descendants_keep_their_independent_pools(self):
        prefix = '''struct Leaf{value:A<Int>}
struct Mixed{item:A<Leaf>,view:&Int}
async fn relay(v:->Mixed)-><-Mixed{yield;return <-v;}
fn make(v:->Mixed)-><-relay{return <-relay(->v);}'''
        body = '''let mut ns=pool<Int>(1);let mut ls=pool<Leaf>(1);
let mut ts=pool<Int>(1);let b=ts.new(9);
let a=ns.new(7);let leaf=ls.new(value:<-a);let v=Mixed{item:<-leaf,view:&b};
let r=make(->v).await;yield;print(*r.view);drop(->r);
let next=ns.new(11);let next_leaf=ls.new(value:<-next);drop(->next_leaf);
drop(->b);return 12;'''
        run = self.run_source(self.program(body, prefix))
        self.assertEqual(run.stdout, '9\n12\n')
        self.assertEqual(run.stderr.count('=Leaf\n'), 2)
        self.assertEqual(run.stderr.count('destroy a=7\n'), 1)
        for declaration in ('let mut ns=pool<Int>(1);', 'let mut ls=pool<Leaf>(1);'):
            short = body.replace(declaration, '').replace('let a=ns.new(7);',
                'let r={' + declaration + 'let a=ns.new(7);').replace(
                'let r=make(->v).await;yield;print(*r.view);drop(->r);',
                'let r=make(->v).await;<-r};yield;print(*r.view);drop(->r);')
            short = short[:short.index('let next=ns.new(11);')] + 'drop(->b);return 12;'
            self.refused(self.program(short, prefix), 'pool|source|survi|durable|local')


if __name__ == '__main__':
    unittest.main()
