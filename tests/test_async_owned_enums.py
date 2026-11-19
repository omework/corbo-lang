"""Enums keep their active arm, source pools and field loans through async."""
from pathlib import Path
from itertools import product
import unittest
from crust import compile_source, verify_program
from scheduler_faults import inject_submission_failure
import test_select_source as sources

ROOT=Path(__file__).resolve().parents[1]
TYPES='enum Choice{Left{x:Int},Right{x:Int,y:Int},Empty{}}'
OWN='async fn own(v:->Choice)-><-Choice{yield;return <-v;}'


class AsyncOwnedEnumTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused
    program=staticmethod(sources.SelectSourceTests.program)

    def test_recorded_enum_and_variants(self):
        source=(ROOT/'validation/open-async-owned-enum.crb').read_text()
        for arm in ('Left','Right'):
            run=self.run_source(source.replace('Choice.Left','Choice.'+arm))
            self.assertEqual(run.stdout,f'Choice.{arm}(7)\n')
            self.assertEqual(run.stderr.count(f'destroy v=Choice.{arm}\n'),1)
        self.refused(source.replace('own(->v)','own(v)'), 'transfert|explicite|mode')
        self.refused(source.replace('let h=runtime', 'print(v);let h=runtime').replace(
            'match h.join()', 'print(v);match h.join()'), 'transfér|utilisable|emprunt')

    def test_relay_and_consumption_in_sync_helper(self):
        helpers=TYPES+OWN+'''fn show(v:&Choice){print(v);}
fn relay(v:->Choice)-><-Choice{return <-v;}
async fn work(v:->Choice)-><-Choice{let r=own(->v).await;yield;show(&r);return <-relay(->r);}'''
        source=helpers+'''fn main(){let mut p=pool<Choice>(1);let v=new(p) Choice.Right{x:7,y:9};
let h=runtime::spawn(->work(->v));match h.join(){Ok(r)=>{print(r);drop(->r);},Err(_)=>{}}
let next=new(p) Choice.Right{x:20,y:30};print(next);}'''
        self.assertEqual(self.run_source(source).stdout,'Choice.Right(7, 9)\nChoice.Right(7, 9)\nChoice.Right(20, 30)\n')

    def test_local_pools_keep_per_arm_layout_and_capacity(self):
        helpers=TYPES+'fn show(v:&Choice){print(v);}'
        body='''let mut p=pool<Choice>(1);
let a=new(p) Choice.Left{x:7};let b=new(p) Choice.Right{x:9,y:11};let e=new(p) Choice.Empty{};
yield;show(&a);show(&b);show(&e);drop(->b);let next=new(p) Choice.Right{x:20,y:30};
show(&next);return 1;'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,
                         'Choice.Left(7)\nChoice.Right(9, 11)\nChoice.Empty()\nChoice.Right(20, 30)\n1\n')
        self.refused(self.program(body.replace('drop(->b);','drop(->p);'),helpers),'pool|source|transfér')
        self.refused(self.program(body.replace('Choice.Right{x:9,y:11}', 'Choice.Right{x:9}'),helpers), 'champs incorrects')

    def test_fresh_enum_from_injected_pool(self):
        helpers=TYPES+'''async fn make(p:&mut Pool<Choice>)-><-Choice{
let v=new(p) Choice.Right{x:7,y:9};yield;return <-v;}'''
        source=helpers+'''fn main(){let mut p=pool<Choice>(1);let h=runtime::spawn(->make(&mut p));
match h.join(){Ok(r)=>{print(r);drop(->r);},Err(_)=>{}}
let next=new(p) Choice.Right{x:20,y:30};print(next);}'''
        self.assertEqual(self.run_source(source).stdout,'Choice.Right(7, 9)\nChoice.Right(20, 30)\n')
        self.refused(source.replace('make(p:&mut Pool<Choice>)','make()').replace(
            'let v=new(p)', 'let mut p=pool<Choice>(1);let v=new(p)').replace('make(&mut p)','make()'),
            'pool|source|survi|durable')

    def test_select_winner_and_loser_reuse_model(self):
        for left_pause,right_pause in product(range(2),repeat=2):
            # Ordered polls: left wins except when only left first suspends.
            winner='Right' if left_pause and not right_pause else 'Left'
            helpers=TYPES+'''fn show(v:&Choice){print(v);}
async fn left(v:->Choice)-><-Choice{LEFT return <-v;}
async fn right(v:->Choice)-><-Choice{RIGHT return <-v;}'''.replace(
                'LEFT','yield;'*left_pause).replace('RIGHT','yield;'*right_pause)
            body='''let mut p=pool<Choice>(1);let a=new(p) Choice.Left{x:7};
let b=new(p) Choice.Right{x:9,y:11};
let mut s=runtime::select(->left(->a),->right(->b));let r=s.await;drop(->s);show(&r);drop(->r);
let next=new(p) Choice.Left{x:20};let other=new(p) Choice.Right{x:30,y:40};
show(&next);show(&other);return 1;'''
            with self.subTest(pauses=(left_pause,right_pause)):
                run=self.run_source(self.program(body,helpers))
                expected='Choice.Right(9, 11)' if winner=='Right' else 'Choice.Left(7)'
                self.assertEqual(run.stdout,expected+'\nChoice.Left(20)\nChoice.Right(30, 40)\n1\n')
                self.assertEqual(run.stderr.count('destroy a=Choice.Left\n'),1)
                self.assertEqual(run.stderr.count('destroy b=Choice.Right\n'),1)

    def test_borrowed_field_return_keeps_target(self):
        for ref in ('&Int','&mut Int'):
            prefix='enum View{Item{target:REF},Empty{}}async fn own(v:->View)-><-View{yield;return <-v;}'.replace('REF',ref)
            source=prefix+'''fn main(){let mut ns=pool<Int>(1);let mut n=ns.new(7);
let mut vs=pool<View>(1);let v=new(vs) View.Item{target:BORROW};
let h=runtime::spawn(->own(->v));match h.join(){Ok(r)=>{BEFORE print(r);drop(->r);},Err(_)=>{}}
drop(->n);}'''.replace('BORROW','&mut n' if ref=='&mut Int' else '&n')
            self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'View.Item(7)\n')
            self.refused(source.replace('drop(->n);','').replace('BEFORE','drop(->n);'), 'emprunt|référenc|survi')

    def test_owned_children_cleanup_on_inactive_and_launch_failure(self):
        helpers='enum Tree{Leaf{n:A<Int>},Empty{}}async fn own(v:->Tree)-><-Tree{yield;return <-v;}'
        source=helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
let mut trees=pool<Tree>(1);let tree=new(trees) Tree.Leaf{n:<-n};
let task=own(->tree);START
let next=ns.new(20);let another=new(trees) Tree.Empty{};print(next);print(another);}'''
        waited=source.replace('START','let h=runtime::spawn(->task);match h.join(){Ok(r)=>{print(r);drop(->r);},Err(_)=>{print(99);}}')
        for program,failed,expected in ((source.replace('START','drop(->task);'),False,'20\nTree.Empty()\n'),
                (waited,False,'Tree.Leaf(7)\n20\nTree.Empty()\n'),(waited,True,'99\n20\nTree.Empty()\n')):
            code=compile_source(program)
            if failed:code=inject_submission_failure(code,asynchronous=False,at=1)
            run=self.run_c_oracle(code)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('destroy n=7\n'),1)
            self.assertEqual(run.stderr.count('destroy tree=Tree.Leaf\n'),1)
            self.assertLess(run.stderr.index('destroy n=7'),run.stderr.index('destroy tree=Tree.Leaf'))

    def test_public_handle_and_relay_keep_reference_field(self):
        source='''enum View{Item{target:&Int},Other{pad:Int,target:&Int},Empty{}}
async fn own(v:->View)-><-View{yield;return <-v;}
fn start(v:->View)-><-runtime::Handle<A<View>>{return <-runtime::spawn(->own(->v));}
fn forward(h:->runtime::Handle<A<View>>)-><-runtime::Handle<A<View>>{return <-h;}
fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let mut vs=pool<View>(1);
let v=new(vs) View.Item{target:&n};let h=forward(->start(->v));
match h.join(){Ok(r)=>{BEFORE print(r);drop(->r);},Err(_)=>{}}drop(->n);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'View.Item(7)\n')
        self.refused(source.replace('drop(->n);','').replace('BEFORE','drop(->n);'), 'emprunt|référenc|survi')
        self.refused(source.replace('BEFORE','').replace('Handle<A<View>>','Handle<View>'), 'stockage|local|allocation')

    def test_sync_bridge_reads_only_active_variant(self):
        helpers='''enum View{Item{target:&Int},Pair{x:Int,target:&Int},Empty{}}
fn show(v:&View){print(v);}
fn relay(v:->View)-><-View{return <-v;}
async fn own(v:->View)-><-View{show(&v);yield;return <-relay(->v);}'''
        for variant, fields, expected in (('Item','target:&n','7'),('Pair','x:9,target:&n','9, 7'),('Empty','','')):
            source=helpers+'''fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);let mut vs=pool<View>(1);
let v=new(vs) View.VARIANT{FIELDS};let h=runtime::spawn(->own(->v));
match h.join(){Ok(r)=>{print(r);drop(->r);},Err(_)=>{}}drop(->n);}'''.replace('VARIANT',variant).replace('FIELDS',fields)
            with self.subTest(variant=variant):
                verify_program(source)
                code = compile_source(source)
                # A mapped pool page can conceal reads beyond the active arm.
                # Check every logical reference-field read, including reads whose
                # unused result an optimizing C compiler would otherwise remove.
                marker = 'static Cell *cell_load_ref(Cell *cell, size_t offset) {'
                self.assertEqual(code.count(marker), 1)
                code = code.replace(marker, marker + '''
    int valid_reference_field = 0;
    if (cell && cell->alive && cell->layout) {
        for (size_t i = 0; i < cell->layout->field_count; ++i)
            if (cell->layout->field_offsets[i] == offset && cell->layout->field_kinds[i] != 0)
                valid_reference_field = 1;
    }
    if (!valid_reference_field) {
        fputs("invalid active-arm reference read\\n", stderr);
        abort();
    }
''')
                self.assertEqual(self.run_c_oracle(code).stdout,(f'View.{variant}({expected})\n')*2)

    def test_select_borrowed_enum_fields_remain_live(self):
        helpers='''enum View{Item{target:&Int},Empty{}}
fn make(p:&mut Pool<View>,n:&Int)-><-View{let v=new(p) View.Item{target:&*n};return <-v;}
fn show(v:&View){print(v);}
async fn left(v:->View)-><-View{yield;return <-v;}
async fn right(v:->View)-><-View{return <-v;}'''
        body='''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
let mut vs=pool<View>(2);let x=make(&mut vs,&a);let y=make(&mut vs,&b);
let mut s=runtime::select(->left(->x),->right(->y));let r=s.await;
drop(->s);BEFORE show(&r);drop(->r);drop(->a);drop(->b);return 1;'''
        source=self.program(body,helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'View.Item(9)\n1\n')
        self.refused(source.replace('drop(->b);','').replace('BEFORE','drop(->b);'),'emprunt|référenc|réserv')

    def test_conditional_variants_and_reference_targets(self):
        helpers='''enum View{First{x:&Int},Second{pad:Int,y:&Int},Empty{}}
async fn own(v:->View)-><-View{yield;return <-v;}
fn start(v:->View)-><-runtime::Handle<A<View>>{return <-runtime::spawn(->own(->v));}'''
        for flag,expected in (('true','View.First(7)'),('false','View.Second(1, 9)')):
            source=helpers+'''fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let mut vs=pool<View>(1);
let v=if FLAG{let x=new(vs) View.First{x:&a};<-x}else{let y=new(vs) View.Second{pad:1,y:&b};<-y};
let h=start(->v);match h.join(){Ok(r)=>{BEFORE print(r);drop(->r);},Err(_)=>{}}
drop(->a);drop(->b);}'''.replace('FLAG',flag)
            self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,expected+'\n')
            for target in ('a','b'):
                self.refused(source.replace('drop(->'+target+');','').replace('BEFORE','drop(->'+target+');'),
                             'emprunt|référenc|survi')

    def test_owned_fields_of_inactive_variants_are_not_read(self):
        helpers='''enum Tree{Leaf{n:A<Int>},Pair{x:Int,n:A<Int>,other:A<Int>},Empty{}}
fn relay(v:->Tree)-><-Tree{return <-v;}
async fn own(v:->Tree)-><-Tree{yield;return <-relay(->v);}'''
        for variant,fields in (('Leaf','n:<-a'),('Pair','x:1,n:<-a,other:<-b'),('Empty','')):
            body='''let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);let mut trees=pool<Tree>(1);
let v=new(trees) Tree.VARIANT{FIELDS};DROP
let h=runtime::spawn(->own(->v));match h.join(){Ok(r)=>{drop(->r);},Err(_)=>{}}
let next=ns.new(20);let another=ns.new(30);print(next);print(another);'''.replace('VARIANT',variant).replace('FIELDS',fields)
            unused='drop(->b);' if variant=='Leaf' else 'drop(->a);drop(->b);' if variant=='Empty' else ''
            run=self.run_source(helpers+'fn main(){'+body.replace('DROP',unused)+'}')
            self.assertEqual(run.stdout,'20\n30\n')
            for value in (7,9):self.assertEqual(run.stderr.count(f'={value}\n'),1)


if __name__=='__main__':unittest.main()
