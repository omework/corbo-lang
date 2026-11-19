"""Select results retain their own origins and the losing branch's field writes."""
from itertools import product
from pathlib import Path
import unittest

from async_structure_effects import AsyncStructureEffectAnalyzer
from crust import Error, Parser, verify_program
import test_select_source as source_tests
import test_native_blocks as native_tests

ROOT = Path(__file__).resolve().parents[1]
TYPES = 'struct View{data:&Int}'


class SelectResultsTests(unittest.TestCase):
    run_c_oracle = source_tests.SelectSourceTests.run_c_oracle
    run_source = source_tests.SelectSourceTests.run_source
    refused = source_tests.SelectSourceTests.refused
    run_native = native_tests.NativeBlockTests.run_native

    def infer(self, source, name='work'):
        baseline=verify_program(TYPES)
        definitions={node.args[0]:node for node in Parser(source).parse() if node.op=='async_fn'}
        analyzer=AsyncStructureEffectAnalyzer(definitions,baseline.function_contracts,baseline.enums,Error)
        summary=analyzer.infer(name)
        self.assertTrue(summary.complete,summary.reason)
        self.assertTrue(summary.suspension_complete,summary.suspension_reason)
        return summary

    @staticmethod
    def main(call, setup='', after='print(*v.data);'):
        return '''fn main(){let mut data=pool<Int>(2);let a=data.new(1);let b=data.new(2);
            let mut v=View{data:&a};SETUP let h=runtime::spawn(->CALL);
            match h.join(){Ok(r)=>{print(r);},Err(_)=>{print(99);}}AFTER}'''.replace(
                'SETUP',setup).replace('CALL',call).replace('AFTER',after)

    def test_recorded_owned_result_preserves_loser_field(self):
        source=(ROOT/'validation/open-select-owned-result-field.crb').read_text()
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n2\n17\n')
        for n in (7,9):self.assertEqual(run.stderr.count(f'destroy x={n}\n'),1)
        self.refused(source.replace('print(*v.data);','drop(->b);print(*v.data);'),'emprunt|référenc')
        self.refused(source.replace('return *x;','return 0;'),'usage explicite|sans usage')

    def test_completed_owned_winner_publishes_field(self):
        source=(ROOT/'validation/open-select-owned-result-field.crb').read_text().replace('yield;','')
        self.assertEqual(self.run_source(source).stdout,'7\n2\n17\n')
        self.refused(source.replace('print(*v.data);','drop(->b);print(*v.data);'),'emprunt|référenc')
        summary=self.infer(source)
        fields=dict(dict(summary.completion_result.structure_fields)[0])
        self.assertEqual({(t.kind,t.parameter) for t in fields['.data']},{('parameter',1)})

    def test_owned_result_return_and_pool_provenance(self):
        source=(ROOT/'validation/open-select-owned-result-field.crb').read_text().replace(
            'q:&mut Pool<Int>)->Int','q:&mut Pool<Int>)-><-Int').replace(
            'drop(->s);return *x;','drop(->s);return <-x;').replace(
            'Ok(r)=>{print(r);}','Ok(r)=>{print(r);drop(->r);}')
        self.assertEqual(self.run_source(source).stdout,'9\n2\n17\n')
        summary=self.infer(source)
        self.assertEqual((summary.completion_result.mode,summary.completion_result.typ),('owned','Int'))
        self.assertEqual({(c.kind,c.source.kind,c.source.index) for c in summary.completion_result.candidates},
                         {('fresh','source_parameter',2),('fresh','source_parameter',3)})
        fields=dict(dict(summary.completion_result.structure_fields)[0])
        self.assertIn(('parameter',1),{(t.kind,t.parameter) for t in fields['.data']})
        # Moving the winning allocation out cannot extend a locally created pool.
        invalid=source.replace('p:&mut Pool<Int>,q:&mut Pool<Int>','p:&mut Pool<Int>').replace(
            'let mut s=runtime::select','let mut local=pool<Int>(1);let mut s=runtime::select').replace(
            '->right(q)','->right(&mut local)').replace('work(&mut v,&b,&mut p,&mut q)','work(&mut v,&b,&mut p)')
        self.refused(invalid,'survit|durable|origine|source')

    def test_text_result_after_drop_retains_source_and_field(self):
        helpers='''async fn left(v:&mut View,n:&Int,t:&str)->&str{v.data=&*n;yield;return t;}
            async fn right(t:&str)->&str{return t;}
            async fn work(v:&mut View,n:&Int)->Int{
                let mut strings=pool<String>(2);
                let mut a=strings.new();a.push_str("left");
                let mut b=strings.new();b.push_str("right");
                let mut s=runtime::select(->left(v,n,&a[..]),->right(&b[..]));
                let text=s.await;drop(->s);BEFORE print(text);drop(->a);drop(->b);return 9;}'''
        source=TYPES+helpers+self.main('work(&mut v,&b)')
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'right\n9\n2\n')
        for name in ('a','b'):
            self.refused(source.replace('BEFORE',f'drop(->{name});'),'emprunt actif')

    def test_returned_view_contract_through_direct_relay(self):
        source='''async fn left(v:&mut View,n:&Int,t:&str)->&str{v.data=&*n;yield;return t;}
            async fn right(t:&str)->&str{return t;}
            async fn choose(v:&mut View,n:&Int,a:&str,b:&str)->&str{
                let mut s=runtime::select(->left(v,n,a),->right(b));
                let t=s.await;drop(->s);return t;}
            async fn work(v:&mut View,n:&Int,a:&str,b:&str)->&str{
                let text=choose(v,n,a,b).await;yield;return text;}'''
        summary=self.infer(source)
        self.assertEqual((summary.completion_result.mode,summary.completion_result.typ),('text','str'))
        self.assertEqual({(t.kind,t.parameter) for t in summary.completion_result.reference_targets},
                         {('utf8_parameter',2),('utf8_parameter',3)})
        self.assertEqual(self.run_source(TYPES+source+self.main('work(&mut v,&b,"left","right")')).stdout,
                         'right\n2\n')

    def test_fallible_text_result_and_last_use(self):
        helpers='''async fn left(v:&mut View,n:&Int,t:&str)->Result<&str,SliceError>{
                v.data=&*n;yield;return t.try_slice(0..1);}
            async fn right(t:&str)->Result<&str,SliceError>{return t.try_slice(0..1);}
            async fn work(v:&mut View,n:&Int)->Int{
                let mut strings=pool<String>(2);let mut a=strings.new();a.push_str("left");
                let mut b=strings.new();b.push_str("right");
                let mut s=runtime::select(->left(v,n,&a[..]),->right(&b[..]));
                let selected=s.await;drop(->s);BEFORE
                match selected{Ok(text)=>{print(text);},Err(_)=>{print(99);}}
                drop(->a);drop(->b);return 9;}'''
        source=TYPES+helpers+self.main('work(&mut v,&b)')
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'r\n9\n2\n')
        unused=source.replace('BEFORE','').replace(
            'match selected{Ok(text)=>{print(text);},Err(_)=>{print(99);}}','')
        self.refused(unused,'usage explicite|sans usage')
        for name in ('a','b'):
            self.refused(source.replace('BEFORE',f'drop(->{name});'),'emprunt actif')

    def test_plain_error_and_array_payloads_preserve_field_updates(self):
        for typ,left,right,use,expected in (
            ('Result<u8,IntegerConversionError>','u8::try_from(300)','u8::try_from(200)',
             'match selected{Ok(byte)=>{print(byte as Int);},Err(_)=>{print(99);}}','200'),
            ('[Int;2]','<-[3,4]','<-[5,6]','print(selected[1]);','6'),
        ):
            helpers=f'''async fn left(v:&mut View,n:&Int)->{typ}{{v.data=&*n;yield;return {left};}}
                async fn right()->{typ}{{return {right};}}
                async fn work(v:&mut View,n:&Int)->Int{{
                    let mut s=runtime::select(->left(v,n),->right());let selected=s.await;
                    drop(->s);{use}return 9;}}'''
            with self.subTest(typ=typ):
                source=TYPES+helpers+self.main('work(&mut v,&b)')
                self.assertEqual(self.run_source(source).stdout,expected+'\n9\n2\n')
                self.refused(source.replace('print(*v.data);','drop(->b);print(*v.data);'),'emprunt|référenc')

    def test_independent_owned_winner_and_reuse_model(self):
        for pauses in product(range(3),repeat=2):
            pending=list(pauses)
            while True:
                winner=None
                for i in range(2):
                    if pending[i]==0:winner=i;break
                    pending[i]-=1
                if winner is not None:break
            helpers=''.join(f'async fn branch{i}(p:&mut Pool<Int>)-><-Int{{let x=p.new({10+i});'+
                'yield;'*count+'return <-x;}' for i,count in enumerate(pauses))
            helpers+='''async fn work(p:&mut Pool<Int>,q:&mut Pool<Int>)-><-Int{
                let mut s=runtime::select(->branch0(p),->branch1(q));
                let x=s.await;drop(->s);return <-x;}'''
            source=helpers+'''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
                let h=runtime::spawn(->work(&mut p,&mut q));
                match h.join(){Ok(x)=>{print(x);drop(->x);},Err(_)=>{print(99);}}
                let a=p.new(30);let b=q.new(40);print(a);print(b);}'''
            with self.subTest(pauses=pauses):
                result=self.run_source(source)
                self.assertEqual(result.stdout,f'{10+winner}\n30\n40\n')
                self.assertEqual(result.stderr.count(f'destroy x={10+winner}\n'),1)
                # Branch 1 is never polled if branch 0 is immediately ready.
                self.assertEqual(result.stderr.count(f'destroy x={11-winner}\n'),int(pauses[0]>0))
                summary=self.infer(helpers)
                actual_source={c.source.index for c in summary.completion_result.candidates}
                self.assertIn(winner,actual_source)
                if pauses[0]==0:self.assertEqual(actual_source,{0})

    def test_owned_child_handle_keeps_failure_separate_from_payload(self):
        source=TYPES+'''async fn child(v:&mut View,n:&Int,p:&mut Pool<Int>)-><-Int{
                v.data=&*n;let x=p.new(7);yield;return <-x;}
            async fn work(v:&mut View,n:&Int,p:&mut Pool<Int>)->Int{
                let h=runtime::spawn(->child(v,n,p));
                match h.await{Ok(x)=>{print(*x);drop(->x);},Err(_)=>{print(99);}}
                return *v.data;}'''+self.main('work(&mut v,&b,&mut p)','let mut p=pool<Int>(1);',
                    'print(*v.data);let next=p.new(20);print(next);')
        self.assertEqual(self.run_source(source).stdout,'7\n2\n2\n20\n')
        self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'99\n1\n1\n20\n')
        self.assertEqual(self.run_native(source,fail_submission_at=1).stdout,'99\n1\n20\n')
        self.refused(source.replace('print(*v.data);let next','drop(->b);print(*v.data);let next'),'emprunt|référenc')

    def test_mutable_slice_keeps_its_vector_after_selection_drop(self):
        source=TYPES+'''async fn left(v:&mut View,n:&Int,a:&mut Vector<Int>)->&mut [Int]{
                v.data=&*n;let (mut empty,mut whole)=a.split_at_mut(0);yield;return whole;}
            async fn right(a:&mut Vector<Int>)->&mut [Int]{
                let (mut empty,mut whole)=a.split_at_mut(0);return whole;}
            async fn work(v:&mut View,n:&Int)->Int{
                let mut p=pool<Vector<Int>>(2);let mut a=p.new();a.push(1);
                let mut b=p.new();b.push(2);
                let mut s=runtime::select(->left(v,n,&mut a),->right(&mut b));
                let mut selected=s.await;drop(->s);BEFORE selected[0]=30;return selected[0];
            }'''+self.main('work(&mut v,&b)')
        for element in ('Int','u8'):
            program=source if element=='Int' else source.replace('Vector<Int>','Vector<u8>').replace(
                '&mut [Int]','&mut [u8]').replace('return selected[0];','return selected[0] as Int;')
            with self.subTest(element=element):
                self.assertEqual(self.run_source(program.replace('BEFORE','')).stdout,'30\n2\n')
                for target in ('a','b'):
                    self.refused(program.replace('BEFORE',target+'.push(8);'),'emprunt actif')

    def test_owned_collections_keep_type_and_cleanup_across_return(self):
        for typ,left_fill,right_fill,observe,expected in (
            ('String','x.push_str("left");','x.push_str("right");','print(&x[..]);','right'),
            ('Vector<Int>','x.push(7);','x.push(9);','print(x[0]);','9'),
            ('Vector<u8>','x.push(7);','x.push(9);','print(x[0] as Int);','9'),
        ):
            source=TYPES+f'''async fn left(v:&mut View,n:&Int,p:&mut Pool<{typ}>)-><-{typ}{{
                    v.data=&*n;let mut x=p.new();{left_fill}yield;return <-x;}}
                async fn right(p:&mut Pool<{typ}>)-><-{typ}{{let mut x=p.new();{right_fill}return <-x;}}
                async fn work(v:&mut View,n:&Int,p:&mut Pool<{typ}>,q:&mut Pool<{typ}>)-><-{typ}{{
                    let mut s=runtime::select(->left(v,n,p),->right(q));
                    let x=s.await;drop(->s);return <-x;}}
                fn main(){{let mut data=pool<Int>(2);let a=data.new(1);let b=data.new(2);
                    let mut v=View{{data:&a}};let mut p=pool<{typ}>(1);let mut q=pool<{typ}>(1);
                    let h=runtime::spawn(->work(&mut v,&b,&mut p,&mut q));
                    match h.join(){{Ok(x)=>{{{observe}drop(->x);}},Err(_)=>{{print(99);}}}}
                    print(*v.data);let reused=p.new();drop(->reused);
                }}'''
            with self.subTest(typ=typ):
                run=self.run_source(source)
                self.assertEqual(run.stdout,expected+'\n2\n')
                self.assertEqual(run.stderr.count('destroy x='),2)

    def test_byte_and_shared_slice_results_keep_sources(self):
        for parameter,result,returned,storage,fill_a,fill_b,use,expected in (
            ('&str','&u8','&t[0]','String','a.push_str("a");','b.push_str("b");','print(*selected as Int);','98'),
            ('&[Int]','&[Int]','t','Vector<Int>','a.push(1);','b.push(2);','print(selected[0]);','2'),
        ):
            source=TYPES+f'''async fn left(v:&mut View,n:&Int,t:{parameter})->{result}{{
                    v.data=&*n;yield;return {returned};}}
                async fn right(t:{parameter})->{result}{{return {returned};}}
                async fn work(v:&mut View,n:&Int)->Int{{let mut p=pool<{storage}>(2);
                    let mut a=p.new();{fill_a}let mut b=p.new();{fill_b}
                    let mut s=runtime::select(->left(v,n,&a[..]),->right(&b[..]));
                    let selected=s.await;drop(->s);BEFORE {use}drop(->a);drop(->b);return 9;
                }}'''+self.main('work(&mut v,&b)')
            with self.subTest(result=result):
                self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,expected+'\n9\n2\n')
                for name in ('a','b'):
                    self.refused(source.replace('BEFORE',f'drop(->{name});'),'emprunt actif')


if __name__=='__main__':
    unittest.main()
