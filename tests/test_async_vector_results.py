"""AS2/RT5/RT6: existing scalar vector results retain status and payload."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
from crust import Error, compile_source, verify_program
import test_plain_join_contracts as contracts
from test_business_result_envelopes import inspect_result
from test_nested_plain_results import result_type

CASES={
 'int_option':('Option<Int>','Int','v.pop()', 'Some(v)=>{print(v);},None=>{print(90);}',('17','90')),
 'byte_option':('Option<u8>','u8','v.pop()', 'Some(v)=>{print(v as Int);},None=>{print(90);}',('17','90')),
 'int_replace':('Result<Int,Int>','Int','v.replace(INDEX,-23)', 'Ok(v)=>{print(v);},Err(v)=>{print(v);}',('17','-23')),
 'byte_replace':('Result<u8,u8>','u8','v.replace(INDEX,255)', 'Ok(v)=>{print(v as Int);},Err(v)=>{print(v as Int);}',('17','255')),
 'int_try_push':('Result<(),Int>','Int','v.try_push(-23)', 'Ok(())=>{print(7);},Err(v)=>{print(v);}',('7','-23')),
 'byte_try_push':('Result<(),u8>','u8','v.try_push(255)', 'Ok(())=>{print(7);},Err(v)=>{print(v as Int);}',('7','255')),
 'capacity_result':('Result<(),CapacityError>','u8','v.try_extend(&bytes)',
                    'Ok(())=>{print(7);},Err(CapacityError::CapacityExceeded)=>{print(90);}',('7','90')),
 'read_result':('Result<Int,ReadError>','u8','v.read_fd(FD)',
                'Ok(v)=>{print(v);},Err(ReadError::EndOfStream)=>{print(91);},Err(ReadError::CapacityExceeded)=>{print(92);},Err(ReadError::Io)=>{print(93);}',('3','93')),
}


def program(case,failed=False,*,captured=False,fail_launch=False):
    typ,element,operation,arms,expected=CASES[case]
    declarations=f'''async fn relay(r:{typ})->{typ}{{let copy=r;drop(->r);yield;return copy;}}
        async fn parent(r:{typ})->{result_type(typ,1)}{{
            let h=runtime::{'spawn_blocking' if fail_launch else 'spawn'}(->relay(r));
            let result=h.await;yield;return result;}}'''
    body=f'let mut v=p.new();'
    if case.endswith('option'):
        if not failed:body+='v.push(17);'
    elif case.endswith('replace'):
        body+='v.push(17);'
        operation=operation.replace('INDEX','1' if failed else '0')
    elif case in ('int_try_push','byte_try_push','capacity_result'):
        if failed:
            count=1048576//(4 if element=='Int' else 1)
            body+=f'let mut i=0;while i<{count}{{v.push(0);i=i+1;}}'
        if case=='capacity_result':body+='let bytes:[u8;1]=[42];'
    elif case=='read_result':
        operation=operation.replace('FD','-1' if failed else '0')
    body+=f'let r:{typ}={operation};drop(->v);let h=runtime::spawn(->parent(r));let outer=h.join();'
    if captured:
        declarations+=f'async fn inspect(r:{result_type(typ,2)}){{yield;'+inspect_result('r',2,arms)+'}'
        body+='let h2=runtime::spawn(->inspect(outer));match h2.join(){Ok(())=>{},Err(_)=>{print(999);}}'
    else:
        body+=inspect_result('outer',2,arms)
    return declarations+f'fn main(){{let mut p=pool<Vector<{element}>>(1);#(directive,stack_region_max_size=1M){{'+body+'}}',expected[int(failed)]


class AsyncVectorResultTests(unittest.TestCase):
    reject_blocking=contracts.PlainJoinContractTests.reject_blocking
    rejecting_callback=contracts.PlainJoinContractTests.rejecting_callback

    def run_native(self,source,*,stdin='abc',reject=False):
        cc=shutil.which('clang') or shutil.which('cc')
        if cc is None:self.skipTest('C compiler unavailable')
        code=compile_source(source)
        if reject:code=self.reject_blocking(code)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'program.c';binary=Path(folder)/'program';path.write_text(code)
            build=subprocess.run([cc,'-std=c11',os.environ.get('CRUST_TEST_OPT','-O2'),'-pthread',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror','-Wno-unused-function',
                str(path),'-o',str(binary)],capture_output=True,text=True,timeout=30)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(binary)],input=stdin,capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stderr)
            return run

    def test_recorded_vector_result_capture(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-vector-value-result.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'1\n')

    def test_result_families_and_variants_cross_nested_waits(self):
        for case in CASES:
            for failed in (False,True):
                for captured in (False,True):
                    with self.subTest(case=case,failed=failed,captured=captured):
                        source,expected=program(case,failed,captured=captured)
                        self.assertEqual(self.run_native(source).stdout,expected+'\n')

    def test_direct_join_preserves_each_payload_field(self):
        for case,data in CASES.items():
            for failed in (False,True):
                source,expected=program(case,failed)
                source=source.replace('spawn(->parent(r))','spawn(->relay(r))')
                source=source.replace(inspect_result('outer',2,data[3]),inspect_result('outer',1,data[3]))
                with self.subTest(case=case,failed=failed):
                    self.assertEqual(self.run_native(source).stdout,expected+'\n')

    def test_launch_error_does_not_become_rejected_value(self):
        for case in ('int_try_push','byte_try_push','capacity_result','read_result'):
            source,_=program(case,True,captured=True,fail_launch=True)
            with self.subTest(case=case):
                self.assertEqual(self.run_native(source,reject=True).stdout,'101\n')

    def test_read_eof_is_preserved_through_contracts(self):
        source,_=program('read_result',captured=True)
        self.assertEqual(self.run_native(source,stdin='').stdout,'91\n')

    def test_read_capacity_error_precedes_io_and_survives_join(self):
        source,_=program('read_result',True,captured=True)
        marker='let r:Result<Int,ReadError>=v.read_fd(-1);'
        self.assertIn(marker,source)
        source=source.replace(marker,'let mut i=0;while i<1048576{v.push(0);i=i+1;}'+marker)
        self.assertEqual(self.run_native(source).stdout,'92\n')

    def test_captures_and_returns_enforce_exact_payload_types(self):
        source,_=program('int_replace',captured=True)
        for old,new in (
            ('relay(r:Result<Int,Int>)','relay(r:Result<u8,u8>)'),
            ('relay(r:Result<Int,Int>)->Result<Int,Int>','relay(r:Result<Int,Int>)->Result<u8,u8>'),
            ('let r:Result<Int,Int>','let r:Result<Int,ReadError>'),
        ):
            with self.subTest(new=new),self.assertRaises(Error):verify_program(source.replace(old,new))

    def test_match_checks_option_result_unit_and_byte(self):
        tests=(
            ('int_option','Some(v)=>{print(v);},None=>{print(90);}','Ok(v)=>{print(v);},Err(_)=>{}'),
            ('int_try_push','Ok(())=>{print(7);}','Ok(v)=>{print(v);}'),
            ('int_replace','Ok(v)=>{print(v);}','Ok(())=>{}'),
            ('byte_replace','print(v as Int);','let integer:Int=v;print(integer);'),
        )
        for case,old,new in tests:
            source,_=program(case,captured=True)
            with self.subTest(case=case),self.assertRaises(Error):verify_program(source.replace(old,new))

    def test_direct_await_control_flow_and_reassignment(self):
        source,_=program('byte_replace',True,captured=True)
        old='async fn relay(r:Result<u8,u8>)->Result<u8,u8>{let copy=r;drop(->r);yield;return copy;}'
        replacement='''async fn relay(r:Result<u8,u8>)->Result<u8,u8>{
            let mut copy=if true{r}else{r};drop(->r);
            match copy{Ok(v)=>{print(v as Int);},Err(v)=>{print(v as Int);}}
            let saved=copy;drop(->copy);yield;
            let mut received:Result<u8,u8>=loop{break saved;};
            match received{Ok(v)=>{print(v as Int);},Err(v)=>{print(v as Int);}}
            received=saved;return received;}
            async fn relay_direct(r:Result<u8,u8>)->Result<u8,u8>{
                return if true{relay(r).await}else{relay(r).await};}'''
        self.assertIn(old,source)
        source=source.replace(old,replacement).replace('spawn(->relay(r))','spawn(->relay_direct(r))')
        self.assertEqual(self.run_native(source).stdout,'255\n255\n255\n')

    def test_sync_creation_does_not_erase_vector_result_mode(self):
        for typ in ('Result<(),Int>','Option<Int>','Result<Int,ReadError>','Result<u8,u8>'):
            source=f'async fn inspect(r:{typ}){{drop(->r);}}'+'''fn main(){
                let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push(17);
                let r=v.replace(0,23);let pending=inspect(r);drop(->pending);}'''
            with self.subTest(typ=typ),self.assertRaisesRegex(Error,'capture async : attendu'):
                verify_program(source)

    def test_drop_and_fallible_usage_remain_checked(self):
        source,_=program('int_try_push',captured=True)
        for change in ('let unused=r;let copy=r;', 'drop(->r);let copy=r;'):
            with self.subTest(change=change),self.assertRaises(Error):
                verify_program(source.replace('let copy=r;',change))


if __name__=='__main__':unittest.main()
