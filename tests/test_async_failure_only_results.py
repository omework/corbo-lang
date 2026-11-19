"""A proven nonreturning child can still fail to launch, without a payload."""
from pathlib import Path
import unittest

from async_structure_effects import AsyncStructureEffectAnalyzer
from crust import Error, Parser, verify_program
import test_native_blocks as native_tests
import test_select_source as source_tests


ROOT = Path(__file__).resolve().parents[1]
TYPES = 'struct View{data:&Int}'


class AsyncFailureOnlyResultsTests(unittest.TestCase):
    run_c_oracle = source_tests.SelectSourceTests.run_c_oracle
    run_native = native_tests.NativeBlockTests.run_native
    run_source = source_tests.SelectSourceTests.run_source
    refused = source_tests.SelectSourceTests.refused

    def analyzer(self, source):
        baseline = verify_program(TYPES+'''fn relay(r:->Result<A<Int>,runtime::Error>)-><-Result<A<Int>,runtime::Error>{
            return <-r;}''')
        definitions = {node.args[0]: node for node in Parser(source).parse() if node.op == 'async_fn'}
        return AsyncStructureEffectAnalyzer(definitions, baseline.function_contracts, baseline.enums, Error)

    def test_recorded_field_write_after_failure_only_handle(self):
        source = (ROOT/'validation/open-owned-noncompleting-child.crb').read_text()
        summary = self.analyzer(source).infer('work')
        self.assertTrue(summary.complete, summary.reason)
        verify_program(source)
        self.assertTrue(summary.may_complete)
        self.assertEqual({(target.kind, target.parameter) for target in
                          dict(dict(summary.structure_fields)[0])['.data']}, {('parameter', 1)})
        # Never run the uninstrumented infinite worker. The first failure skips
        # work; the second lets work continue only through child LaunchFailed.
        for position, expected in ((1, '99\n1\n'), (2, '2\n2\n')):
            with self.subTest(position=position):
                run = self.run_native(source, fail_submission_at=position)
                self.assertEqual(run.stdout, expected)
                for name, value in (('first', 1), ('second', 2)):
                    self.assertEqual(run.stderr.count(f'destroy {name}={value}\n'), 1)
        self.refused(source.replace('print(*view.data);', 'drop(->second);print(*view.data);'),
                     'emprunt|référenc')

    def test_failure_only_result_families_keep_no_child_completion(self):
        for typ, use in (
            ('<-Int', 'drop(->value);'),
            ('<-String', 'drop(->value);'),
            ('<-Vector<Int>', 'drop(->value);'),
            ('<-Vector<u8>', 'drop(->value);'),
            ('&str', 'print(value);'),
            ('&u8', 'print(*value as Int);'),
            ('&[Int]', 'print(value[0]);'),
            ('&mut [Int]', 'print(value[0]);'),
            ('Result<&str,SliceError>', 'drop(->value);'),
        ):
            source = TYPES+f'''async fn child(v:&mut View,n:&Int)->{typ}{{
                    v.data=&*n;loop{{yield;}}}}
                async fn work(v:&mut View,a:&Int,b:&Int)->Int{{
                    let h=runtime::spawn(->child(v,a));
                    match h.await{{Ok(value)=>{{{use}}},Err(_)=>{{}}}}
                    v.data=&*b;return *v.data;}}
                fn main(){{let mut p=pool<Int>(3);let a=p.new(1);let b=p.new(2);let c=p.new(3);
                    let mut v=View{{data:&a}};
                    let h=runtime::spawn(->work(&mut v,&b,&c));
                    match h.join(){{Ok(x)=>{{print(x);}},Err(_)=>{{print(99);}}}}
                    print(*v.data);}}'''
            with self.subTest(typ=typ):
                analyzer = self.analyzer(source)
                child, work = analyzer.infer('child'), analyzer.infer('work')
                self.assertTrue(child.complete, child.reason)
                self.assertFalse(child.may_complete)
                self.assertTrue(work.complete, work.reason)
                targets = dict(dict(work.structure_fields)[0])['.data']
                self.assertEqual({(t.kind, t.parameter) for t in targets}, {('parameter', 2)})
                verify_program(source)
                self.assertEqual(self.run_native(source, fail_submission_at=2).stdout, '3\n3\n')

    def test_direct_await_still_has_no_continuation(self):
        source = TYPES+'''async fn child(v:&mut View,n:&Int)-><-Int{
                v.data=&*n;loop{yield;}}
            async fn work(v:&mut View,a:&Int,b:&Int,flag:Bool)->Int{
                if flag{let x=child(v,a).await;drop(->x);v.data=&*a;return 0;}
                v.data=&*b;return 1;}'''
        summary = self.analyzer(source).infer('work')
        self.assertTrue(summary.complete, summary.reason)
        self.assertTrue(summary.may_complete)
        self.assertEqual({(target.kind, target.parameter) for target in
                          dict(dict(summary.structure_fields)[0])['.data']}, {('parameter', 2)})

    def test_unknown_child_does_not_become_failure_only(self):
        source = TYPES+'''async fn child(v:&mut View,n:&Int)-><-Int{
                let x=child(v,n).await;return <-x;}
            async fn work(v:&mut View,n:&Int)->Int{
                let h=runtime::spawn(->child(v,n));
                match h.await{Ok(x)=>{drop(->x);},Err(_)=>{}}
                v.data=&*n;return 0;}'''
        summary = self.analyzer(source).infer('work')
        self.assertFalse(summary.complete)
        self.assertIsNone(summary.structure_fields)
        self.assertIn('récursif', summary.reason)

    def test_failure_only_owned_envelope_can_be_returned(self):
        source = TYPES+'''async fn child(v:&mut View,n:&Int,p:&mut Pool<Int>)-><-Int{
                v.data=&*n;loop{yield;}}
            async fn work(v:&mut View,n:&Int,p:&mut Pool<Int>)-><-Result<A<Int>,runtime::Error>{
                let h=runtime::spawn(->child(v,n,p));let result=h.await;
                v.data=&*n;return <-result;}
            fn main(){let mut data=pool<Int>(2);let a=data.new(1);let b=data.new(2);
                let mut p=pool<Int>(1);let mut v=View{data:&a};
                let h=runtime::spawn(->work(&mut v,&b,&mut p));
                match h.join(){Ok(result)=>{match result{
                    Ok(value)=>{print(*value);drop(->value);},Err(_)=>{print(20);}}},
                    Err(_)=>{print(10);}}
                print(*v.data);let reused=p.new(30);print(*reused);}'''
        summary = self.analyzer(source).infer('work')
        self.assertTrue(summary.complete, summary.reason)
        self.assertEqual(summary.completion_result.mode, 'join_owned')
        self.assertEqual(summary.completion_result.candidates, frozenset())
        self.assertTrue(summary.completion_result.absent_owned_payload)
        verify_program(source)
        for position, expected in ((1, '10\n1\n30\n'), (2, '20\n2\n30\n')):
            with self.subTest(position=position):
                self.assertEqual(self.run_native(source, fail_submission_at=position).stdout, expected)
        self.refused(source.replace('return <-result;', 'return result;'), 'transfert|explicite')

    def test_proven_absence_survives_control_and_contract_relays(self):
        helpers = '''fn relay(r:->Result<A<Int>,runtime::Error>)-><-Result<A<Int>,runtime::Error>{return <-r;}
            async fn child()-><-Int{loop{yield;}}
            async fn work(v:&mut View,n:&Int,flag:Bool)-><-Result<A<Int>,runtime::Error>{
                let h=runtime::spawn(->child());let result=h.await;v.data=&*n;BODY}
            fn main(){let mut p=pool<Int>(2);let a=p.new(1);let b=p.new(2);let mut v=View{data:&a};
                let h=runtime::spawn(->work(&mut v,&b,true));
                match h.join(){Ok(r)=>{match r{Ok(x)=>{drop(->x);},Err(_)=>{print(20);}}},Err(_)=>{print(10);}}
                print(*v.data);}'''
        for body in (
            'let moved=<-result;return <-moved;',
            'let moved=if flag{result ->; <-result}else{result ->; <-result};return <-moved;',
            'let moved=loop{result ->;break <-result;};return <-moved;',
            'let moved=relay(->result);return <-moved;',
        ):
            with self.subTest(body=body):
                source=TYPES+helpers.replace('BODY',body)
                summary=self.analyzer(source).infer('work')
                self.assertTrue(summary.complete,summary.reason)
                self.assertTrue(summary.completion_result.absent_owned_payload)
                self.assertEqual(summary.completion_result.candidates,frozenset())
                verify_program(source)
                self.assertEqual(self.run_native(source,fail_submission_at=2).stdout,'20\n2\n')
                self.refused(source.replace('return <-moved;','drop(->result);return <-moved;'),
                             'consommé|utilisable|transfér')

    def test_completing_alternative_keeps_payload_source(self):
        source = TYPES+'''async fn forever(v:&mut View,n:&Int,p:&mut Pool<Int>)-><-Int{
                v.data=&*n;loop{yield;}}
            async fn ready(v:&mut View,n:&Int,p:&mut Pool<Int>)-><-Int{
                v.data=&*n;let value=p.new(7);return <-value;}
            async fn work(v:&mut View,n:&Int,p:&mut Pool<Int>,flag:Bool)-><-Result<A<Int>,runtime::Error>{
                let h=if flag{let h=runtime::spawn(->forever(v,n,p));<-h}
                    else{let h=runtime::spawn(->ready(v,n,p));<-h};
                let result=h.await;return <-result;}
            fn main(){let mut data=pool<Int>(2);let a=data.new(1);let b=data.new(2);
                let mut p=pool<Int>(1);let mut v=View{data:&a};
                let h=runtime::spawn(->work(&mut v,&b,&mut p,FLAG));
                match h.join(){Ok(result)=>{match result{
                    Ok(value)=>{print(*value);drop(->value);},Err(_)=>{print(20);}}},
                    Err(_)=>{print(10);}}
                print(*v.data);let reused=p.new(30);print(*reused);}'''
        summary = self.analyzer(source.replace('FLAG','false')).infer('work')
        self.assertTrue(summary.complete, summary.reason)
        self.assertEqual({(c.kind,c.source.kind,c.source.index) for c in summary.completion_result.candidates},
                         {('fresh','source_parameter',2)})
        self.assertFalse(summary.completion_result.absent_owned_payload)
        # A tiny independent execution model: successful nonterminating launches
        # cannot reach the prints. Every other pair has a finite expected trace.
        for forever in (False, True):
            for failure in (None, 1, 2):
                if forever and failure is None:
                    continue
                outer_started = failure != 1
                child_started = outer_started and failure != 2
                value = 7 if child_started else 20 if outer_started else 10
                field = 2 if child_started else 1
                with self.subTest(forever=forever,failure=failure):
                    program = source.replace('FLAG',str(forever).lower())
                    verify_program(program)
                    run = self.run_native(program,fail_submission_at=failure)
                    self.assertEqual(run.stdout,f'{value}\n{field}\n30\n')
                    self.assertEqual(run.stderr.count('destroy value=7\n'),int(child_started))
        self.refused(source.replace('FLAG','false').replace('print(*v.data);','drop(->b);print(*v.data);'),
                     'emprunt|référenc')

    def test_sync_owned_result_bridge_cleanup_and_prepared_argument(self):
        for typ,fill,read in (
            ('Int','let value=p.new(7);','print(*value);'),
            ('String','let mut value=p.new();value.push_str("7");','print(&value[..]);'),
            ('Vector<Int>','let mut value=p.new();value.push(7);','print(value[0]);'),
            ('Vector<u8>','let mut value=p.new();value.push(7);','print(value[0] as Int);'),
        ):
            source=f'''async fn leaf(p:&mut Pool<{typ}>)-><-{typ}{{{fill}return <-value;}}
                async fn later()->Int{{yield;return 0;}}
                fn relay(r:->Result<A<{typ}>,runtime::Error>,n:Int)-><-Result<A<{typ}>,runtime::Error>{{
                    print(n);return <-r;}}
                async fn work(p:&mut Pool<{typ}>)->Int{{let h=runtime::spawn(->leaf(p));let r=h.await;
                    let moved=relay(->r,ARG);
                    match moved{{Ok(value)=>{{{read}drop(->value);}},Err(_)=>{{print(20);}}}}
                    return 9;}}
                fn main(){{let mut p=pool<{typ}>(1);let h=runtime::spawn(->work(&mut p));
                    match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(10);}}}}
                    let reused=p.new();drop(->reused);}}'''
            for argument, expected in (('later().await','0\n7\n9\n'), ('{return 8;}','8\n')):
                with self.subTest(typ=typ,argument=argument):
                    program=source.replace('ARG',argument)
                    run=self.run_source(program)
                    self.assertEqual(run.stdout,expected)
                    self.assertEqual(run.stderr.count('destroy value='),1)
            valid=source.replace('ARG','later().await')
            self.assertEqual(self.run_native(valid,fail_submission_at=2).stdout,'0\n20\n9\n')
            self.refused(valid.replace('relay(->r,','relay(r,'),'transfert|explicite')
            self.refused(valid.replace('return 9;','drop(->r);return 9;'),'consommé|utilisable|transfér')
            if typ == 'Int':
                self.refused(valid.replace('fn relay(r:->Result<A<Int>,runtime::Error>,n:Int)-><-Result<A<Int>,runtime::Error>',
                    'fn relay(r:->Result<A<String>,runtime::Error>,n:Int)-><-Result<A<String>,runtime::Error>'),
                    'type incompatible|attendu')

    def test_nested_owned_result_bridge(self):
        source='''async fn leaf(p:&mut Pool<Int>)-><-Int{let value=p.new(7);return <-value;}
            async fn wrap(p:&mut Pool<Int>)-><-Result<A<Int>,runtime::Error>{
                let h=runtime::spawn(->leaf(p));let r=h.await;return <-r;}
            fn relay(r:->Result<Result<A<Int>,runtime::Error>,runtime::Error>)
                -><-Result<Result<A<Int>,runtime::Error>,runtime::Error>{return <-r;}
            async fn work(p:&mut Pool<Int>)->Int{let h=runtime::spawn(->wrap(p));let r=h.await;
                let moved=relay(->r);match moved{Ok(inner)=>{match inner{
                    Ok(value)=>{print(*value);drop(->value);},Err(_)=>{print(30);}}},Err(_)=>{print(20);}}
                return 9;}
            fn main(){let mut p=pool<Int>(1);let h=runtime::spawn(->work(&mut p));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(10);}}
                let reused=p.new(40);print(*reused);}'''
        for failure, expected in ((None,'7\n9\n40\n'),(1,'10\n40\n'),(2,'20\n9\n40\n'),(3,'30\n9\n40\n')):
            with self.subTest(failure=failure):
                verify_program(source)
                run=self.run_native(source,fail_submission_at=failure)
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy value=7\n'),int(failure is None))

    def test_distinct_handle_frames_keep_borrowed_origins(self):
        source='''async fn left(n:&Int)->&Int{yield;return n;}
            async fn right(n:&Int)->&Int{return n;}
            async fn work(a:&Int,b:&Int,flag:Bool)->&Int{
                let h=if flag{let x=runtime::spawn(->left(a));<-x}
                    else{let x=runtime::spawn(->right(b));<-x};
                match h.await{Ok(view)=>{return view;},Err(_)=>{return a;}}}
            fn main(){let mut p=pool<Int>(2);let a=p.new(10);let b=p.new(20);
                let h=runtime::spawn(->work(&a,&b,FLAG));
                match h.join(){Ok(view)=>{BEFORE print(*view);},Err(_)=>{}}
                drop(->a);drop(->b);let reused=p.new(30);print(*reused);}'''
        for flag,expected in (('true','10\n30\n'),('false','20\n30\n')):
            with self.subTest(flag=flag):
                valid=source.replace('FLAG',flag)
                self.assertEqual(self.run_source(valid.replace('BEFORE','')).stdout,expected)
                for target in ('a','b'):
                    self.refused(valid.replace('BEFORE',f'drop(->{target});'),'emprunt|référenc')

    def test_sync_owned_result_direct_drop_match_and_return(self):
        for typ,fill,read in (
            ('Int','let value=p.new(7);','print(*value);'),
            ('String','let mut value=p.new();value.push_str("7");','print(&value[..]);'),
            ('Vector<Int>','let mut value=p.new();value.push(7);','print(value[0]);'),
            ('Vector<u8>','let mut value=p.new();value.push(7);','print(value[0] as Int);'),
        ):
            prefix=f'''async fn leaf(p:&mut Pool<{typ}>)-><-{typ}{{{fill}return <-value;}}
                fn relay(r:->Result<A<{typ}>,runtime::Error>)-><-Result<A<{typ}>,runtime::Error>{{return <-r;}}'''
            result=f'Result<A<{typ}>,runtime::Error>'
            observe=f'match RESULT{{Ok(value)=>{{{read}drop(->value);}},Err(_)=>{{print(20);}}}}'
            for style,signature,body,main_use,expected in (
                ('drop','Int','drop(->relay(->r));return 9;','print(out);','9\n'),
                ('match','Int',observe.replace('RESULT','relay(->r)')+'return 9;','print(out);','7\n9\n'),
                ('return','<-'+result,'return <-relay(->r);',observe.replace('RESULT','out'),'7\n'),
            ):
                source=prefix+f'''async fn work(p:&mut Pool<{typ}>)->{signature}{{
                        let h=runtime::spawn(->leaf(p));let r=h.await;{body}}}
                    fn main(){{let mut p=pool<{typ}>(1);let h=runtime::spawn(->work(&mut p));
                        match h.join(){{Ok(out)=>{{{main_use}}},Err(_)=>{{print(10);}}}}
                        let reused=p.new();drop(->reused);}}'''
                with self.subTest(typ=typ,style=style):
                    run=self.run_source(source)
                    self.assertEqual(run.stdout,expected)
                    self.assertEqual(run.stderr.count('destroy value='),1)
                    if style=='return':
                        self.refused(source.replace('return <-relay(->r);','return relay(->r);'),
                                     'explicite|transfert')

    def test_nested_transferred_result_arguments(self):
        source=(ROOT/'validation/open-nested-owned-result-argument.crb').read_text()
        for depth in (2,3,5):
            expression='r'
            for _ in range(depth):
                expression=f'relay(->{expression})'
            program=source.replace('relay(->relay(->r))',expression)
            with self.subTest(depth=depth):
                self.assertEqual(self.run_source(program).stdout,'7\n9\n10\n')
                self.assertEqual(self.run_native(program,fail_submission_at=2).stdout,'9\n10\n')
                self.refused(program.replace(expression,expression.replace('relay(->','relay(',1)),
                             'transfert|explicite')
        with_later=source.replace('r:->Result<A<Int>,runtime::Error>)',
                                 'r:->Result<A<Int>,runtime::Error>,n:Int)').replace(
            '{return <-r;}','{print(n);return <-r;}').replace(
            'relay(->relay(->r))','relay(->relay(->r,1),{return 8;})')
        run=self.run_source(with_later)
        self.assertEqual(run.stdout,'1\n8\n10\n')
        self.assertEqual(run.stderr.count('destroy value=7\n'),1)


if __name__ == '__main__':
    unittest.main()
