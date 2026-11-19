"""Interior structure descriptors crossing the async frame boundary."""
import unittest
import test_select_source as harness

TYPES = 'struct Point{x:Int,y:Int}struct Pair{a:Point,b:Point}'
INIT = 'let mut pair=Pair{a:Point{x:1},b:Point{x:7}};'
JOIN = 'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}'


class AsyncInlineViewTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def source(self, helpers, body):
        return TYPES + helpers + 'fn main(){' + INIT + body + '}'

    def test_read_view_after_yield_on_worker(self):
        source = self.source('async fn read(p:&Point)->Int{yield;return p.x;}',
            'let t=read(&pair.b);let h=runtime::spawn(->t);' + JOIN)
        self.assertEqual(self.run_source(source).stdout, '7\n')
        for operation in ('drop(->pair);', 'pair.b.x=30;'):
            self.refused(source.replace('let h=', operation+'let h='), 'emprunt|réserv|référenc')

    def test_mutation_through_sync_bridge_and_nested_await(self):
        helpers = '''fn edit(p:&mut Point)->Int{p.x=11;return p.x;}
            async fn inner(p:&mut Point)->Int{yield;return edit(p);}
            async fn outer(p:&mut Point)->Int{yield;let n=inner(p).await;return n;}'''
        source = self.source(helpers,
            'let t=outer(&mut pair.b);let h=runtime::spawn(->t);'+JOIN+'print(pair.b.x);')
        self.assertEqual(self.run_source(source).stdout, '11\n11\n')
        self.refused(source.replace('let h=', 'print(pair.b.x);let h='), 'emprunt|réserv|référenc')

    def test_whole_and_interior_use_same_routine(self):
        source = self.source('async fn read(p:&Point)->Int{yield;return p.y+p.x;}',
            'let p=Point{x:3};let h=runtime::spawn(->read(&p));'+JOIN+
            'let other=runtime::spawn(->read(&pair.b));'+JOIN.replace('h.join()', 'other.join()'))
        self.assertEqual(self.run_source(source).stdout, '3\n7\n')

    def test_discard_inactive_releases_borrow_without_running(self):
        source = self.source('async fn edit(p:&mut Point)->Int{yield;p.x=99;return p.x;}',
            'let task=edit(&mut pair.b);drop(->task);pair.b.x=12;print(pair.b.x);')
        self.assertEqual(self.run_source(source).stdout, '12\n')

    def test_field_reference_survives_task_completion(self):
        helpers = 'async fn field(p:&mut Point)->&mut Int{yield;return &mut p.x;}'
        source = self.source(helpers, 'let h=runtime::spawn(->field(&mut pair.b));'
            'match h.join(){Ok(n)=>{n.set(21);print(*n);},Err(_)=>{print(99);}}print(pair.b.x);')
        self.assertEqual(self.run_source(source).stdout, '21\n21\n')
        self.refused(source.replace('n.set(21);', 'drop(->pair);n.set(21);'), 'emprunt|réserv|référenc')

    def test_copy_from_view_and_mutable_reborrow(self):
        helpers = '''fn target(p:&mut Point)->&mut Point{return p;}
            async fn work(p:&mut Point)->Int{let mut alias=target(p);yield;alias.x=13;
                let c=copy(alias);yield;return c.x;}'''
        source = self.source(helpers, 'let h=runtime::spawn(->work(&mut pair.b));'+JOIN+'print(pair.b.x);')
        self.assertEqual(self.run_source(source).stdout, '13\n13\n')

    def test_view_keeps_owned_child_and_borrowed_target(self):
        helpers = '''struct Inner{child:A<Int>,view:&Int}struct Outer{first:Int,inner:Inner}
            async fn work(p:&mut Inner)->Int{yield;let mut n=&mut *p.child;n.set(17);
                return *p.child+*p.view;}'''
        source = self.source(helpers, '''drop(->pair);let mut ns=pool<Int>(2);let child=ns.new(3);let target=ns.new(5);
            let mut outer=Outer{first:99,inner:Inner{child:<-child,view:&target}};
            let t=work(&mut outer.inner);let h=runtime::spawn(->t);'''+JOIN+'drop(->outer);print(*target);')
        self.assertEqual(self.run_source(source).stdout, '22\n5\n')
        self.refused(source.replace('let h=', 'drop(->target);let h='), 'emprunt|réserv|référenc')

    def test_pool_view_copy_requires_explicit_destination(self):
        implicit = '''async fn work(p:&Point)->Int{yield;let c=copy(p);return c.x;}
            async fn relay(p:&Point)->Int{return work(p).await;}'''
        body = '''drop(->pair);let mut pairs=pool<Pair>(1);let pooled=pairs.new(b.x:7);
            let h=runtime::spawn(->CALL(&pooled.b));'''+JOIN
        for call in ('work', 'relay'):
            source = self.source(implicit, body.replace('CALL', call))
            self.refused(source, 'copie implicite|stockage local')
        explicit = '''async fn work(p:&Point,dest:&mut Pool<Point>)->Int{
            yield;let c=dest.copy(p);return c.x;}'''
        source = self.source(explicit, body.replace('CALL(&pooled.b)', 'work(&pooled.b,&mut points)').replace(
            'let h=', 'let mut points=pool<Point>(1);let h='))
        self.assertEqual(self.run_source(source).stdout, '7\n')

    def test_copy_requirement_through_sync_task_factory(self):
        helpers = '''async fn leaf(p:&Point)->Int{yield;let c=copy(p);return c.x;}
            fn make(p:&Point)-><-leaf{return <-leaf(p);}
            async fn relay(p:&Point)->Int{let t=make(p);return t.await;}'''
        body = '''drop(->pair);let mut ps=pool<Point>(2);let p=ps.new(x:3);
            let h=runtime::spawn(->relay(&p));'''+JOIN+'drop(->p);'
        self.assertEqual(self.run_source(self.source(helpers, body)).stdout, '3\n')
        invalid = body.replace('drop(->pair);', 'let mut pairs=pool<Pair>(1);let pooled=pairs.new();drop(->pair);').replace(
            'relay(&p)', 'relay(&pooled.b)')
        self.refused(self.source(helpers, invalid), 'copie implicite|stockage local')


if __name__ == '__main__':
    unittest.main()
