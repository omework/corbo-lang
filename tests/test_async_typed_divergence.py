"""Typed receivers do not materialize when their initializer cannot continue."""
from pathlib import Path
import unittest
from crust import Error, verify_program
import test_async_loop_references as loops

class AsyncTypedDivergenceTests(unittest.TestCase):
    run_native=loops.AsyncLoopReferenceTests.run_native
    reject_blocking=loops.AsyncLoopReferenceTests.reject_blocking
    rejecting_callback=loops.AsyncLoopReferenceTests.rejecting_callback
    program=staticmethod(loops.AsyncLoopReferenceTests.program)

    def test_recorded_typed_initializer(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-diverging-typed-initializer.crb').read_text()
        try:
            run=self.run_native(source)
        except Error as e:
            self.fail(f'valid typed initializer rejected: {e}')
        self.assertEqual(run.stdout,'42\n20\n77\n')

    def test_array_shapes_reference_elements_and_scalars(self):
        types=('[Int;0]','[[u8;2];3]','[&Int;1]','[&mut Int;2]',
               'Bool','char','runtime::Error','Result<char,CharFromStrError>')
        for typ in types:
            body=f'''let mut r=loop{{let unused:{typ}=if flag==1{{yield;break &mut *a;}}else{{yield;break &mut *b;}};print(999);}};return r;'''
            for flag in (0,1):
                with self.subTest(typ=typ,flag=flag):
                    self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                        ('42\n20\n' if flag else '10\n42\n')+'77\n')
            for target in ('a','b'):
                with self.subTest(typ=typ,target=target),self.assertRaisesRegex(Error,'emprunt actif'):
                    verify_program(self.program(body).replace('*r=42;',f'{target}=3;*r=42;'))

    def test_blocks_match_return_and_continue(self):
        forms=(
            ('let unused:[Int;1]={yield;return a;};print(999);','42\n20\n77\n'),
            ('let unused:[u8;2]=match u8::try_from(flag){Ok(n)=>{print(n as Int);return a;},Err(_)=>{return b;}};print(999);','1\n42\n20\n77\n'),
            ('let mut i=0;let mut r=loop{i=i+1;let unused:[Int;3]=if i<3{yield;continue;}else{yield;break &mut *a;};print(999);};print(i);return r;','3\n42\n20\n77\n'),
            ('let unused:[&mut Int;1]=loop{yield;return a;};print(999);','42\n20\n77\n'),
        )
        for body,expected in forms:
            with self.subTest(body=body):self.assertEqual(self.run_native(self.program(body)).stdout,expected)

    def test_continuing_array_branch_has_exact_type(self):
        body='''let mut r=loop{
          let items:[Int;1]=if flag==1{yield;break &mut *a;}else{let local=[7];<-local};
          print(items[0]);break &mut *b;
        };return r;'''
        for flag in (0,1):
            self.assertEqual(self.run_native(self.program(body,flag)).stdout,
                             '42\n20\n77\n' if flag else '7\n10\n42\n77\n')
        for typ in ('[Int;2]','[u8;1]','Bool'):
            with self.subTest(typ=typ),self.assertRaises(Error):
                verify_program(self.program(body.replace('items:[Int;1]','items:'+typ)))

    def test_annotations_do_not_skip_lifetime_type_or_consumption_checks(self):
        bodies=(
            'let unused:[Int;1]=if flag==1{let mut local=[7];return &mut local[0];}else{return b;};',
            'let mut r=loop{let unused:[Int;1]=if flag==1{break &*a;}else{break &mut *b;};};return r;',
            'let mut r=loop{let unused:[Int;1]=if flag==1{break;}else{break &mut *b;};};return r;',
            'let unused:[Int;1]=if flag==1{return a;}else{7};return b;',
            'let unused:Bool=if flag==1{return a;}else{7};return b;',
        )
        for body in bodies:
            with self.subTest(body=body),self.assertRaises(Error):verify_program(self.program(body))
        for typ in ('UnknownType','[UnknownType;1]','[[UnknownType;2];1]'):
            with self.subTest(typ=typ),self.assertRaises(Error):
                verify_program(self.program(f'let unused:{typ}=if flag==1{{return a;}}else{{return b;}};'))

    def test_typed_exit_cleans_owned_child_before_reuse(self):
        source=(Path(__file__).resolve().parents[1]/'validation/async-diverging-prepared-owner.crb').read_text()
        old='let inactive=hold(->junk,if flag==1{yield;return a;}else{yield;return a;});'
        new='let inactive=hold(->junk,{let unused:[Int;1]=if flag==1{yield;return a;}else{yield;return a;};7});'
        for flag in (0,1):
            run=self.run_native(source.replace(old,new).replace('pick(1,',f'pick({flag},'))
            self.assertEqual(run.stdout,'88\n42\n')
            self.assertEqual(run.stderr.count('destroy junk=77\n'),1)

if __name__=='__main__':unittest.main()
