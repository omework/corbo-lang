"""F2: a nested Err wildcard covers remaining errors, not success."""
from pathlib import Path
import unittest
from crust import Error, verify_program
import test_async_vector_results as results
from test_async_vector_operations import launch


class ResidualErrorPatternTests(unittest.TestCase):
    run_native=results.AsyncVectorResultTests.run_native
    reject_blocking=results.AsyncVectorResultTests.reject_blocking
    rejecting_callback=results.AsyncVectorResultTests.rejecting_callback

    def test_recorded_residual_read_error(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-read-error-residual-pattern.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'99\n')

    def test_residual_read_errors_do_not_capture_success(self):
        cases=[(0,'abc','',3),(0,'','',90),(-1,'abc','',90),
               (-1,'abc','let mut i=0;while i<1048576{v.push(7);i=i+1;}',92)]
        for asynchronous in (False,True):
            for fd,stdin,setup,expected in cases:
                body=setup+f'''match v.read_fd({fd}){{
                    Err(ReadError::CapacityExceeded)=>{{print(92);}},
                    Err(_)=>{{print(90);}},Ok(n)=>{{print(n);}}}}'''
                source=launch(body,element='u8') if asynchronous else '''fn main(){
                    let mut p=pool<Vector<u8>>(1);#(directive,stack_region_max_size=1M){
                    let mut v=p.new();'''+body+'}}'
                with self.subTest(asynchronous=asynchronous,fd=fd,stdin=stdin,full=bool(setup)):
                    self.assertEqual(self.run_native(source,stdin=stdin).stdout,f'{expected}\n')

    def test_value_match_residual_body_suspends_and_runs_once(self):
        body='''let mut count=0;
            let code=match v.read_fd(-1){Ok(n)=>{n},
                Err(ReadError::CapacityExceeded)=>{92},Err(_)=>{count=count+1;yield;93}};
            print(code);print(count);'''
        self.assertEqual(self.run_native(launch(body,element='u8')).stdout,'93\n1\n')

    def test_decoding_errors_in_sync_and_async(self):
        for asynchronous in (False,True):
            for text,expected in (('',10),('ab',20),('z',30)):
                body=f'''match char::from_str("{text}"){{
                    Err(CharFromStrError::Empty)=>{{print(10);}},
                    Err(_)=>{{print(20);}},Ok(c)=>{{print(c.utf8_len()+29);}}}}'''
                source=(('async fn work(){yield;'+body+'}fn main(){let h=runtime::spawn(->work());match h.join(){Ok(())=>{},Err(_)=>{print(99);}}}')
                        if asynchronous else 'fn main(){'+body+'}')
                with self.subTest(asynchronous=asynchronous,text=text):
                    self.assertEqual(self.run_native(source).stdout,f'{expected}\n')

    def test_slice_result_keeps_error_family_and_borrowed_success(self):
        for end,expected in ((1,'CUT'),(2,'é'),(4,'OUT')):
            source=f'''async fn work(text:&str){{yield;
                match text.try_slice(..{end}){{Ok(view)=>{{print(view);}},
                    Err(SliceError::OutOfBounds)=>{{print("OUT");}},Err(_)=>{{print("CUT");}}}}}}
                fn main(){{let h=runtime::spawn(->work("é"));match h.join(){{Ok(())=>{{}},Err(_)=>{{print("LAUNCH");}}}}}}'''
            with self.subTest(end=end):
                self.assertEqual(self.run_native(source).stdout,expected+'\n')

    def test_missing_success_duplicates_and_type_mismatch_remain_rejected(self):
        prefix='fn main(){let mut p=pool<Vector<u8>>(1);let mut v=p.new();match v.read_fd(-1){'
        for arms,diagnostic in (
            ('Err(ReadError::CapacityExceeded)=>{},Err(_)=>{}','non exhaustif'),
            ('Ok(n)=>{print(n);},Err(ReadError::CapacityExceeded)=>{},Err(_)=>{},Err(ReadError::Io)=>{}','dupliqué'),
            ('Ok(n)=>{print(n);},Err(ReadError::CapacityExceeded)=>{},Err(ReadError::EndOfStream)=>{},Err(ReadError::Io)=>{},Err(_)=>{}','inaccessible'),
            ('Ok(n)=>{print(n);},Err(ReadError::CapacityExceeded)=>{},Err(_)=>{},Err(_)=>{}','inaccessible'),
            ('Ok(n)=>{print(n);},Err(SliceError::OutOfBounds)=>{},Err(_)=>{}','incompatible'),
        ):
            with self.subTest(arms=arms),self.assertRaisesRegex(Error,diagnostic):
                verify_program(prefix+arms+'}}')


if __name__=='__main__':unittest.main()
