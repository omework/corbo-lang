"""Direct construction from injected pools: identity, loans and cleanup."""
from pathlib import Path
import unittest

from crust import Error, compile_source, verify_program
import test_native_blocks as native


class AsyncCollectionNewTests(unittest.TestCase):
    run_c_oracle = native.NativeBlockTests.run_c_oracle
    run_native = native.NativeBlockTests.run_native
    cases = (
        ('String', 'value.push_str("été");', 'print(&value[..]);', 'été\n'),
        ('Vector<Int>', 'value.push(7);value.push(9);', 'print(value[0]);print(value[1]);', '7\n9\n'),
        ('Vector<u8>', 'value.push(195);value.push(169);', 'print(value[0] as Int);print(value[1] as Int);', '195\n169\n'),
    )

    @staticmethod
    def program(typ, body, display, *, capacity=1, helpers='', before='', after=''):
        return helpers+f'''async fn work(p:&mut Pool<{typ}>)-><-{typ}{{{body}}}
          fn main(){{let mut p=pool<{typ}>({capacity});let task=work(&mut p);{before}
            let h=runtime::spawn(->task);
            match h.join(){{Ok(value)=>{{{display}drop(->value);}},Err(_)=>{{print(99);}}}}
            {after} let next=p.new();drop(->next);}}'''

    def destroyed(self, run, count):
        self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()), count)

    def test_default_named_creation_growth_return_and_reuse(self):
        for typ, edit, display, expected in self.cases:
            with self.subTest(typ=typ):
                body=f'let mut value:A<{typ}>=p.new();{edit}yield;return <-value;'
                run=self.run_native(self.program(typ, body, display))
                self.assertEqual(run.stdout,expected);self.destroyed(run,2)
                for invalid in ('A<Int>', 'A<Vector<u8>>' if typ!='Vector<u8>' else 'A<String>'):
                    with self.assertRaises(Error):
                        verify_program(self.program(typ,body.replace(f'A<{typ}>',invalid),display))

    def test_default_empty_direct_return_and_nested_child(self):
        for typ, _, _, _ in self.cases:
            display='print(value.byte_len());' if typ=='String' else 'print(value.len());'
            for body in ('return <-p.new();','let value=child(p).await;return <-value;'):
                helpers=f'async fn child(p:&mut Pool<{typ}>)-><-{typ}{{yield;return <-p.new();}}'
                with self.subTest(typ=typ,body=body):
                    run=self.run_native(self.program(typ,body,display,helpers=helpers))
                    self.assertEqual(run.stdout,'0\n');self.destroyed(run,2)

    def test_modes_types_initializers_and_usage_rejected(self):
        for typ, edit, display, _ in self.cases:
            source=self.program(typ,f'let mut value=p.new();{edit}return <-value;',display)
            alternatives=(
                source.replace('let mut value','let value'),
                source.replace('p.new();'+edit,'p.new(7);'+edit),
                source.replace(f'work(p:&mut Pool<{typ}>)',f'work(p:&Pool<{typ}>)').replace('work(&mut p)','work(&p)'),
                source.replace('return <-value;','return value;'),
                source.replace('let mut value=p.new();','let unused=p.new();let mut value=p.new();'),
                source.replace('let mut value=p.new();','let _=p.new();let mut value=p.new();'),
            )
            for invalid in alternatives:
                with self.subTest(typ=typ,invalid=invalid), self.assertRaises(Error):verify_program(invalid)

    def test_pool_reserved_then_released_without_executing_inactive_task(self):
        for typ, _, display, _ in self.cases:
            source=self.program(typ,'return <-p.new();','')
            invalid=source.replace('let h=runtime::spawn','let other=p.new();drop(->other);let h=runtime::spawn')
            with self.subTest(typ=typ), self.assertRaises(Error):verify_program(invalid)
            inactive=source.replace('let h=runtime::spawn(->task);','drop(->task);let h=runtime::spawn(->work(&mut p));')
            run=self.run_native(inactive);self.assertEqual(run.stdout,'');self.destroyed(run,2)
            failed=self.run_native(source,fail_at=1)
            self.assertEqual(failed.stdout,'99\n');self.destroyed(failed,1)

    def test_borrow_survives_yield_and_prevents_drop_or_replacement(self):
        for typ, edit, display, expected in self.cases:
            read='print(view);' if typ=='String' else ('print(*view);' if typ=='Vector<Int>' else 'print(*view as Int);')
            borrow='&value[..]' if typ=='String' else '&value[0]'
            body=f'let mut value=p.new();{edit}let view={borrow};yield;BEFORE {read}return <-value;'
            source=self.program(typ,body.replace('BEFORE',''),display,capacity=2)
            run=self.run_native(source)
            self.assertEqual(run.stdout,(expected if typ=='String' else expected.splitlines()[0]+'\n')+expected)
            self.destroyed(run,2)
            for conflict in ('drop(->value);','value=p.new();'):
                with self.subTest(typ=typ,conflict=conflict),self.assertRaises(Error):
                    verify_program(self.program(typ,body.replace('BEFORE',conflict),display,capacity=2))

    def test_replacement_and_loop_cleanup_before_reuse(self):
        for typ, edit, display, expected in self.cases:
            body=f'''let mut i=0;while i<3{{let mut scratch=p.new();drop(->scratch);i=i+1;yield;continue;}}
              let mut value=p.new();value=p.new();{edit}return <-value;'''
            with self.subTest(typ=typ):
                run=self.run_native(self.program(typ,body,display,capacity=2))
                self.assertEqual(run.stdout,expected);self.destroyed(run,6)

    def test_direct_result_keeps_only_its_source(self):
        for typ, _, _, _ in self.cases:
            declarations=f'''async fn work(p:&mut Pool<{typ}>,q:&mut Pool<{typ}>)-><-{typ}{{
              let other=q.new();drop(->other);yield;return <-p.new();}}'''
            main=f'''fn main(){{let mut p=pool<{typ}>(1);
              let value={{let mut q=pool<{typ}>(1);let h=runtime::spawn(->work(&mut p,&mut q));
                let received=match h.join(){{Ok(v)=>{{<-v}},Err(_)=>{{return;}}}};<-received}};
              drop(->value);let next=p.new();drop(->next);}}'''
            with self.subTest(typ=typ):
                run=self.run_native(declarations+main);self.assertEqual(run.stdout,'');self.destroyed(run,3)
                with self.assertRaises(Error):
                    verify_program(declarations.replace('return <-p.new();','return <-q.new();')+main)

    def test_native_block_creation_and_pointer_identity(self):
        for typ, edit, display, expected in self.cases:
            helpers=f'fn locate(value:->{typ})-><-{typ}{{address(value);return <-value;}}'
            body=f'let mut value=p.new();{edit}let located=locate(->value);return <-located;'
            source=helpers+f'''fn main(){{let mut memory=pool<{typ}>(1);let p=&mut memory;
              let h=runtime::thread({{->(p);{body}}});
              match h.join(){{Ok(value)=>{{address(value);{display}drop(->value);}},Err(_)=>{{}}}}
              let next=memory.new();address(next);drop(->next);}}'''
            with self.subTest(typ=typ):
                run=self.run_native(source);lines=run.stdout.splitlines()
                self.assertEqual(lines[0],lines[1]);self.assertEqual(lines[0],lines[-1])
                self.assertEqual('\n'.join(lines[2:-1])+'\n',expected);self.destroyed(run,2)

    def test_element_reborrows_child_and_last_use(self):
        for typ, scalar in (('Vector<Int>','Int'),('Vector<u8>','u8')):
            child=f'async fn relay(v:&mut {scalar})->&mut {scalar}{{yield;return v;}}'
            body='''let mut value=p.new();value.push(7);value.push(9);
              let child=relay(&mut value[1]);BEFORE
              let mut view=child.await;DURING print(*view as Int);
              drop(->value);let mut next=p.new();next.push(11);return <-next;'''
            source=self.program(typ,body.replace('BEFORE','').replace('DURING',''),
                                'print(value[0] as Int);',helpers=child)
            with self.subTest(typ=typ):
                run=self.run_native(source);self.assertEqual(run.stdout,'9\n11\n');self.destroyed(run,3)
                for location in ('BEFORE','DURING'):
                    for conflict in ('drop(->value);','value.push(10);','print(value[1] as Int);'):
                        invalid=body.replace(location,conflict).replace('BEFORE','').replace('DURING','')
                        with self.assertRaises(Error):verify_program(self.program(typ,invalid,'',helpers=child))
                immutable=source.replace('let mut value=p.new();value.push(7);value.push(9);',
                                         'let value=p.new();')
                with self.assertRaises(Error):verify_program(immutable)

    def test_index_suspension_reserves_collection_before_child_capture(self):
        for typ, scalar in (('Vector<Int>','Int'),('Vector<u8>','u8')):
            helper=f'async fn read(v:&{scalar})->Int{{yield;return *v as Int;}}'
            body='''let mut value=p.new();value.push(7);value.push(9);
              let view=&value[{yield;INDEX 1}];let child=read(view);
              let n=child.await;print(n);return <-value;'''
            source=self.program(typ,body.replace('INDEX',''),'print(value[0] as Int);',helpers=helper)
            with self.subTest(typ=typ):
                run=self.run_native(source);self.assertEqual(run.stdout,'9\n7\n');self.destroyed(run,2)
                for operation in ('drop(->value);','value=p.new();','value.push(11);'):
                    with self.assertRaises(Error):
                        verify_program(self.program(typ,body.replace('INDEX',operation),'',helpers=helper))

    def test_element_local_escape_and_invalid_access_rejected(self):
        for typ,scalar in (('Vector<Int>','Int'),('Vector<u8>','u8')):
            for mode in ('&','&mut '):
                source=f'''async fn bad(p:&mut Pool<{typ}>)->{mode}{scalar}{{
                  let mut value=p.new();value.push(7);return {mode}value[0];}}
                  fn main(){{let mut p=pool<{typ}>(1);let h=runtime::spawn(->bad(&mut p));
                    match h.join(){{Ok(v)=>{{print(*v as Int);}},Err(_)=>{{}}}}}}'''
                with self.subTest(typ=typ,mode=mode),self.assertRaises(Error):verify_program(source)
            body='let mut value=p.new();value.push(7);let view=&mut value[0];CONFLICT print(*view as Int);return <-value;'
            for conflict in ('let other=&mut value[0];print(*other as Int);','let other=&value[0];print(*other as Int);'):
                with self.assertRaises(Error):
                    verify_program(self.program(typ,body.replace('CONFLICT',conflict),''))

    def test_transferred_temporary_is_cleaned_if_later_argument_returns(self):
        for typ,_,_,_ in self.cases:
            source=f'''fn consume(v:->{typ},n:Int)->Int{{drop(->v);return n;}}
              async fn work(p:&mut Pool<{typ}>)->Int{{return consume(->p.new(),{{yield;return 42;}});}}
              fn main(){{let mut p=pool<{typ}>(1);let h=runtime::spawn(->work(&mut p));
                match h.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}
                let next=p.new();drop(->next);}}'''
            with self.subTest(typ=typ):
                run=self.run_native(source);self.assertEqual(run.stdout,'42\n');self.destroyed(run,2)

    def test_capacity_exhaustion_precedes_replacement_cleanup(self):
        for typ,_,_,_ in self.cases:
            source=self.program(typ,'let mut value=p.new();value=p.new();return <-value;','')
            with self.subTest(typ=typ):
                run=self.run_c_oracle(compile_source(source),expected_error='pool capacity exceeded')
                self.destroyed(run,0)

    def test_borrow_index_bounds_checked_before_pointer_exposure(self):
        for typ in ('Vector<Int>','Vector<u8>'):
            for index in (-1,1):
                body=f'''let mut value=p.new();value.push(7);let i={index};
                  let view=&value[{{yield;i}}];print(*view as Int);return <-value;'''
                with self.subTest(typ=typ,index=index):
                    self.run_c_oracle(compile_source(self.program(typ,body,'')),
                                      expected_error='indice de Vector hors limites')


if __name__=='__main__':unittest.main()
