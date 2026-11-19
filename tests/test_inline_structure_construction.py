"""ST1/ST3/ST4: nested literals initialize one complete outer allocation."""
from pathlib import Path
import unittest
from crust import compile_source
import test_select_source as sources
import test_suspended_cleanup as cleanup

TYPES = 'struct Pair{left:Int,right:Int}struct Outer{a:Pair,b:Pair}'
ROOT = Path(__file__).resolve().parents[1]


class InlineStructureConstructionTests(unittest.TestCase):
    run_source = sources.SelectSourceTests.run_source
    run_c_oracle = sources.SelectSourceTests.run_c_oracle
    refused = sources.SelectSourceTests.refused
    native = cleanup.SuspendedCleanupTests.native

    def program(self, body, helpers='', types=TYPES, asynchronous=False):
        if asynchronous:
            return types + helpers + 'async fn work()->Int{' + body + '''}
                fn main(){let h=runtime::spawn(->work());match h.join(){
                    Ok(n)=>{print(n);},Err(_)=>{}}}'''
        return types + helpers + 'fn main(){' + body + '}'

    def test_recorded_literal_has_only_outer_allocation(self):
        source = (ROOT / 'validation/open-nested-structure-literal.crb').read_text()
        run = self.run_source(source)
        self.assertEqual(run.stdout, '1\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy v=Outer'])
        code = compile_source(source)
        self.assertEqual(code.count('= local_cell_new('), 1)

    def test_written_order_defaults_and_pool_alias(self):
        helpers = 'fn step(n:Int)->Int{print(n);return n;}'
        body = '''let mut items=pool<Outer>(1);let alias=&mut items;
            let mut v=alias.new(b:Pair{right:step(4),left:step(3)},a:Pair{left:step(1)});
            print(v.a.right);v.a.right=2;print(v.a.left+v.a.right+v.b.left+v.b.right);
            drop(->v);let next=items.new();print(next.a.left);'''
        run = self.run_source(self.program(body, helpers))
        self.assertEqual(run.stdout, '4\n3\n1\n0\n10\n0\n')
        self.assertNotIn('=Pair', run.stderr)

    def test_function_return_copy_and_disjoint_field_borrows(self):
        helpers = '''fn make()-><-Outer{
            let p=Outer{a:Pair{left:1},b:Pair{left:3}};return <-p;}
            fn take(p:&mut Outer)->&mut Int{return &mut p.a.left;}'''
        source = self.program('''let mut p=make();let q=copy(p);
            let mut x=take(&mut p);let mut y=&mut p.b.left;
            x.set(7);y.set(9);print(*x);print(*y);drop(->p);print(q.a.left);''', helpers)
        self.assertEqual(self.run_source(source).stdout, '7\n9\n1\n')
        self.refused(source.replace('x.set(7);', 'p.a.left=8;x.set(7);'), 'emprunt|réserv|référenc')

    def test_async_nested_construction_suspension_and_return(self):
        helpers = '''async fn step(n:Int)->Int{print(n);yield;return n;}
            async fn make()-><-Outer{
                let p=Outer{b:Pair{right:step(4).await},a:Pair{left:step(1).await}};
                yield;return <-p;}'''
        source = self.program('let p=make().await;let q=copy(p);drop(->p);yield;return q.a.left+q.b.right;',
                              helpers, asynchronous=True)
        run = self.run_source(source)
        self.assertEqual(run.stdout, '4\n1\n5\n')
        self.assertEqual(run.stderr.count('=Outer\n'), 2)
        self.assertNotIn('=Pair', run.stderr)

    def test_injected_pool_constructors_sync_and_async(self):
        helpers = '''fn make(p:&mut Pool<Outer>)-><-A<Outer>{
                let v=p.new(a:Pair{left:7});return <-v;}
            async fn child(p:&mut Pool<Outer>)-><-A<Outer>{
                yield;return <-p.new(b:Pair{right:9});}'''
        source = self.program('''let mut p=pool<Outer>(2);let a=make(&mut p);
            let b=child(&mut p).await;print(a.a.left);return b.b.right;''', helpers, asynchronous=True)
        self.assertEqual(self.run_source(source).stdout, '7\n9\n')

    def test_shared_target_returned_in_contained_structure(self):
        types = 'struct View{n:&Int}struct Outer{v:View}'
        for asynchronous in (False, True):
            helpers = ('async ' if asynchronous else '') + '''fn make(n:&Int)-><-Outer{
                let p=Outer{v:View{n:n}};return <-p;}'''
            source = self.program('''let mut ns=pool<Int>(1);let n=ns.new(7);
                let p=make(&n)AWAIT;let q=copy(p);drop(->p);
                print(*q.v.n);drop(->q);drop(->n);END'''
                .replace('AWAIT', '.await' if asynchronous else '')
                .replace('END', 'return 1;' if asynchronous else ''), helpers, types, asynchronous)
            with self.subTest(asynchronous=asynchronous):
                self.assertEqual(self.run_source(source).stdout, '7\n1\n' if asynchronous else '7\n')
                self.refused(source.replace('print(*q.v.n);drop(->q);drop(->n);',
                                           'drop(->n);print(*q.v.n);drop(->q);'), 'emprunt|réserv|référenc')

    def test_owned_field_prepared_before_suspension_is_cleaned(self):
        types = 'struct Item{n:A<Int>,after:Int}struct Outer{v:Item}'
        source = self.program('''let mut ns=pool<Int>(1);let n=ns.new(7);
            let p=Outer{v:Item{n:<-n,after:pause().await}};
            print(*p.v.n);return p.v.after;''', 'async fn pause()->Int{yield;return 9;}',
            types, asynchronous=True)
        run = self.run_source(source)
        self.assertEqual(run.stdout, '7\n9\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        self.assertLess(run.stderr.index('destroy n='), run.stderr.index('destroy p='))
        run = self.native(source, '''
            CrustTask *task=crust_async_work_create();
            assert(task_poll(task)==TASK_SUSPENDED);
            assert(task_owned_discardable(task));assert(task_drop_owned(task));
        ''')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        self.assertNotIn('destroy p=', run.stderr)

    def test_nominal_types_duplicates_unknown_and_missing_reference(self):
        for literal, diagnostic in (
            ('Outer{a:Other{left:1}}', 'construction inline Pair'),
            ('Outer{a:Pair{left:1,left:2}}', 'plusieurs fois'),
            ('Outer{a:Pair{missing:1}}', 'champ inconnu'),
            ('Outer{a:Pair{},a:Pair{}}', 'plusieurs fois'),
        ):
            with self.subTest(literal=literal):
                self.refused(self.program('let p='+literal+';print(p.a.left);',
                                         types=TYPES+'struct Other{left:Int,right:Int}'), diagnostic)
        self.refused(self.program('let p=Outer{v:View{}};drop(->p);',
                                 types='struct View{n:&Int}struct Outer{v:View}'), 'aucune valeur par défaut')


if __name__ == '__main__':
    unittest.main()
