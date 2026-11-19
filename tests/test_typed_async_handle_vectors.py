"""Typed handle collections retain payload type and pools across suspension."""
import unittest
from pathlib import Path
import test_select_source as harness

POINT = 'struct Point{x:Int}'
MAIN = '''fn main(){let mut p=pool<Point>(2);let mut vp=pool<Vector<A<Point>>>(1);
    let mut v=vp.new();let h=runtime::spawn(->work(&mut v,&mut p));
    match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
    drop(->v);let again=p.new(x:9);print(again.x);}'''


class TypedAsyncHandleVectorTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_borrowed_push_remove_and_sync_relay(self):
        helper = 'fn take(v:&mut Vector<A<Point>>)-><-A<Point>{return <-v.remove(0);}'
        for extraction in ('<-v.remove(0)', 'take(&mut *v)'):
            source = POINT + helper + '''async fn work(v:&mut Vector<A<Point>>,p:&mut Pool<Point>)->Int{
                let a=p.new(x:7);v.push(->a);yield;let item=EXTRACTION;
                yield;let n=item.x;drop(->item);return n;}'''.replace('EXTRACTION',extraction) + MAIN
            self.assertEqual(self.run_source(source).stdout, '7\n9\n')
            self.refused(source.replace('v.push(->a);', 'v.push(a);'), 'transfert|->|move')
        wrong = source.replace('let a=p.new(x:7);', 'let a=Point{x:7};')
        self.refused(wrong, 'allocation|pool|local')
        wrong = source.replace('let a=p.new(x:7);', 'let mut ints=pool<Int>(1);let a=ints.new(7);')
        self.refused(wrong, 'allocation Point|type|Pool<Point>')

    def test_local_pools_and_cross_pool_cleanup(self):
        source = POINT + '''async fn work()->Int{
            let mut first=pool<Point>(1);let mut second=pool<Point>(1);
            let mut vectors=pool<Vector<A<Point>>>(1);let mut v=vectors.new();
            v.push(->first.new(x:7));yield;v.push(->second.new(x:8));yield;
            let item=<-v.remove(0);let n=item.x;drop(->item);drop(->v);
            let a=first.new(x:9);let b=second.new(x:10);print(a.x);print(b.x);return n;}
            fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout, '9\n10\n7\n')
        self.assertEqual(run.stderr.count('=Point\n'), 4)

    def test_shared_and_owned_captures(self):
        for parameter, argument, after in (
            ('&Vector<A<Point>>','&v','drop(->v);'),
            ('->Vector<A<Point>>','->v',''),
        ):
            source = POINT + f'''async fn work(v:{parameter})->Int{{yield;return v.len();}}
                fn main(){{let mut p=pool<Point>(1);let mut vp=pool<Vector<A<Point>>>(1);
                let mut v=vp.new();v.push(->p.new(x:7));let h=runtime::spawn(->work({argument}));
                match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(99);}}}}
                {after}let again=p.new(x:9);print(again.x);}}'''
            self.assertEqual(self.run_source(source).stdout, '1\n9\n')
            self.refused(source.replace('match h.join()', 'drop(->v);match h.join()'),
                         'emprunt|réserv|transfér|consomm|utilis')

    def test_typed_option_survives_yield_and_sync_call(self):
        helper = 'fn take(v:&mut Vector<A<Point>>)-><-Option<A<Point>>{return <-v.pop();}'
        for pop in ('<-v.pop()', 'take(&mut *v)'):
            for filled, expected in ((True,'7\n9\n'), (False,'0\n9\n')):
                fill = 'v.push(->p.new(x:7));' if filled else ''
                source = POINT + helper + '''async fn work(v:&mut Vector<A<Point>>,p:&mut Pool<Point>)->Int{
                    FILL yield;let result:Option<A<Point>>=POP;yield;
                    match (->result){Some(item)=>{let n=item.x;drop(->item);return n;},None=>{return 0;}}}
                    '''.replace('FILL',fill).replace('POP',pop) + MAIN
                self.assertEqual(self.run_source(source).stdout, expected)
                self.refused(source.replace('let result:Option<A<Point>>','let result:Option<A<Int>>'),
                             'annotation|type|Int')

    def test_shared_sync_call_and_capture_lifetimes(self):
        source = POINT + '''fn inspect(v:&Vector<A<Point>>)->Int{return v.len();}
            async fn work(v:&mut Vector<A<Point>>,p:&mut Pool<Point>)->Int{
                v.push(->p.new(x:7));yield;return inspect(&*v);}''' + MAIN
        self.assertEqual(self.run_source(source).stdout, '1\n9\n')
        invalid = source.replace('match h.join()', 'let another=p.new(x:8);drop(->another);match h.join()')
        self.refused(invalid, 'emprunt|réserv|captur')

    def test_inactive_owned_capture_drops_remaining_elements(self):
        source = POINT + '''async fn work(v:->Vector<A<Point>>)->Int{print(77);yield;return v.len();}
            fn main(){let mut p=pool<Point>(1);let mut vp=pool<Vector<A<Point>>>(1);
            let mut v=vp.new();v.push(->p.new(x:7));let task=work(->v);drop(->task);
            let again=p.new(x:9);print(again.x);}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout, '9\n')
        self.assertEqual(run.stderr.count('=Point\n'), 2)
        self.refused(source.replace('drop(->task);', 'drop(->task);drop(->v);'),
                     'transfér|consomm|utilis')

    def test_growing_payloads_keep_their_type(self):
        for typ, fill, read, expected in (
            ('String','item.push_str("été");','print(&item[..]);','été\n1\n'),
            ('Vector<Int>','item.push(7);','print(item[0]);','7\n1\n'),
            ('Vector<u8>','let byte:u8=7;item.push(byte);','print(item[0] as Int);','7\n1\n'),
        ):
            source = f'''async fn work()->Int{{let mut p=pool<{typ}>(1);
                let mut vectors=pool<Vector<A<{typ}>>>(1);let mut v=vectors.new();
                let mut initial=p.new();{fill.replace('item.', 'initial.')}v.push(->initial);yield;
                let result=<-v.pop();yield;
                match (->result){{Some(item)=>{{{read}drop(->item);}},None=>{{print(0);}}}}
                drop(->v);let again=p.new();drop(->again);return 1;}}
                fn main(){{let h=runtime::spawn(->work());match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(99);}}}}}}'''
            self.assertEqual(self.run_source(source).stdout, expected)

    def test_local_exchange_checks_payload_type_and_cleans_both_pools(self):
        wrong = Path(__file__).resolve().parents[1].joinpath(
            'validation/typed-async-handle-vectors-wrong-replace.crb').read_text()
        self.refused(wrong, 'allocation Point')
        for index, expected in ((0,'7\n9\n11\n12\n1\n'), (4,'9\n7\n11\n12\n1\n')):
            source = POINT + f'''async fn work()->Int{{let mut p=pool<Point>(1);let mut q=pool<Point>(1);
                let mut vp=pool<Vector<A<Point>>>(1);let mut v=vp.new();v.push(->p.new(x:7));
                let incoming=q.new(x:9);yield;
                let r:Result<A<Point>,A<Point>>=<-v.replace({index},->incoming);yield;
                match (->r){{Ok(item)=>{{print(item.x);drop(->item);}},Err(item)=>{{print(item.x);drop(->item);}}}}
                let resident=<-v.remove(0);print(resident.x);drop(->resident);drop(->v);
                let a=p.new(x:11);let b=q.new(x:12);print(a.x);print(b.x);return 1;}}
                fn main(){{let h=runtime::spawn(->work());match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(99);}}}}}}'''
            self.assertEqual(self.run_source(source).stdout, expected)

    def test_nested_payload_types_are_supported_in_empty_vectors(self):
        for field in ('&Int','A<Int>'):
            helper = 'struct Item{value:'+field+'}'
            for declaration,argument,setup in (
                ('async fn work(v:->Vector<A<Item>>)->Int{yield;return v.len();}',
                 '->v','let mut p=pool<Vector<A<Item>>>(1);let v=p.new();'),
                ('async fn work()->Int{let mut p=pool<Vector<A<Item>>>(1);let v=p.new();yield;return v.len();}',
                 '', ''),
            ):
                source=helper+declaration+'fn main(){'+setup+'let h=runtime::spawn(->work('+argument+'));match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'
                self.assertEqual(self.run_source(source).stdout,'0\n')


if __name__ == '__main__':
    unittest.main()
