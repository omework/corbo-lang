"""RT5/RT6 with pre-existing fallible/optional scalar payloads."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_plain_join_contracts as contracts
from test_nested_plain_results import result_type


CASES = {
    'conversion': ('Result<u8,IntegerConversionError>', 'n:Int', 'n', 'N', '',
                   'return u8::try_from(n);',
                   'Ok(v)=>{print(v as Int);},Err(IntegerConversionError::OutOfRange)=>{print(90);}',
                   (255, 256), ('255', '90')),
    'char_at': ('Result<char,CharAtError>', 'n:Int', 'n', 'N', '',
                'return "é".char_at(n);',
                'Ok(v)=>{print(v);},Err(_)=>{print(90);}', (0, 1), ('é', '90')),
    'from_str': ('Result<char,CharFromStrError>', 'n:Int', 'n', 'N', '',
                 'if n==0{return char::from_str("é");}else{return char::from_str("ab");}',
                 'Ok(v)=>{print(v);},Err(_)=>{print(90);}', (0, 1), ('é', '90')),
    'pop': ('Option<char>', 's:&mut String,n:Int', 's,n', '&mut s,N',
            'let mut p=pool<String>(1);let mut s=p.new();if N==0{s.push_str("é");}',
            'return s.pop();', 'Some(v)=>{print(v);},None=>{print(90);}', (0, 1), ('é', '90')),
    'replace_byte': ('Result<u8,ByteReplaceError>', 's:&mut String,n:Int', 's,n', '&mut s,N',
                     'let mut p=pool<String>(1);let mut s=p.new();s.push_str("A");',
                     'let b:u8=120;return s.replace_byte(n,b);',
                     'Ok(v)=>{print(v as Int);},Err(_)=>{print(90);}', (0, 2), ('65', '90')),
    'replace_bytes': ('Result<(),ByteReplaceError>', 's:&mut String,n:Int', 's,n', '&mut s,N',
                      'let mut p=pool<String>(1);let mut s=p.new();s.push_str("A");',
                      'let bytes:[u8;1]=[120];return s.replace_bytes(n,&bytes);',
                      'Ok(())=>{print(7);},Err(_)=>{print(90);}', (0, 2), ('7', '90')),
}


def inspect_result(subject, wrappers, arms):
    if wrappers == 0:
        return f'match {subject}{{{arms}}}'
    return f'match {subject}{{Ok(inner{wrappers})=>{{' + inspect_result(f'inner{wrappers}', wrappers-1, arms) + f'}},Err(runtime::Error::LaunchFailed)=>{{print({100+wrappers});}}}}'


def program(case, value, wrappers=3, *, captured=False, failed_layer=None):
    typ, parameters, forwards, args, setup, leaf, arms, inputs, outcomes = CASES[case]
    source = f'async fn leaf({parameters})->{typ}{{yield;{leaf}}}'
    previous = 'leaf'
    for level in range(1, wrappers):
        launch = 'spawn_blocking' if failed_layer == level else 'spawn'
        source += f'async fn layer{level}({parameters})->{result_type(typ,level)}{{let h=runtime::{launch}(->{previous}({forwards}));let r=h.await;yield;return r;}}'
        previous = f'layer{level}'
    launch = 'spawn_blocking' if failed_layer == wrappers else 'spawn'
    main = setup.replace('N',str(value)) + f'let h=runtime::{launch}(->{previous}({args.replace("N",str(value))}));let r=h.join();'
    # A decoded scalar result does not retain the String used to compute it.
    if setup:
        main += 'drop(->s);'
    if captured:
        source += f'async fn inspect(r:{result_type(typ,wrappers)}){{let copy=r;drop(->r);yield;'+inspect_result('copy',wrappers,arms)+'}'
        main += 'let h2=runtime::spawn(->inspect(r));match h2.join(){Ok(())=>{},Err(_)=>{print(999);}}'
    else:
        main += inspect_result('r',wrappers,arms)
    return source+'fn main(){'+main+'}', outcomes[inputs.index(value)]


class BusinessResultEnvelopeTests(unittest.TestCase):
    native=contracts.PlainJoinContractTests.native
    run_c_oracle=contracts.PlainJoinContractTests.run_c_oracle
    reject_blocking=contracts.PlainJoinContractTests.reject_blocking
    rejecting_callback=contracts.PlainJoinContractTests.rejecting_callback

    def test_recorded_envelope_gap(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-business-result-envelope.crb').read_text()
        self.assertEqual(self.native(source).stdout,'')

    def test_business_outcomes_survive_nested_contracts_and_capture(self):
        for case,data in CASES.items():
            for value in data[-2]:
                for wrappers in (1,3):
                    for captured in (False,True):
                        with self.subTest(case=case,value=value,wrappers=wrappers,captured=captured):
                            source,expected=program(case,value,wrappers=wrappers,captured=captured)
                            self.assertEqual(self.native(source).stdout,expected+'\n')

    def test_runtime_failure_is_distinct_from_business_failure(self):
        for failed_layer in (1,2,3):
            for captured in (False,True):
                source,_=program('conversion',256,captured=captured,failed_layer=failed_layer)
                with self.subTest(failed_layer=failed_layer,captured=captured):
                    code=self.reject_blocking(compile_source(source))
                    self.assertEqual(self.run_c_oracle(code).stdout,f'{100+failed_layer}\n')

    def test_contracts_annotations_copies_and_reassignment(self):
        typ=result_type(CASES['conversion'][0],2)
        source='''async fn leaf(n:Int)->Result<u8,IntegerConversionError>{yield;return u8::try_from(n);}
            async fn wait(n:Int)->Result<Result<u8,IntegerConversionError>,runtime::Error>{
                return runtime::spawn(->leaf(n)).await;}
            async fn again(n:Int)->Result<Result<u8,IntegerConversionError>,runtime::Error>{return wait(n).await;}'''
        source+=f'''fn relay(r:{typ})->{typ}{{return r;}}
            async fn inspect(r:{typ}){{let mut copy:{typ}=if true{{r}}else{{r}};
                {inspect_result('copy',2,CASES['conversion'][6])}
                copy=loop{{break r;}};yield;
                {inspect_result('copy',2,CASES['conversion'][6])}
                drop(->copy);drop(->r);}}
            fn main(){{let h=runtime::spawn(->again(255));let r:{typ}=relay(h.join());
                let h2=runtime::spawn(->inspect(r));
                match h2.join(){{Ok(())=>{{}},Err(_)=>{{print(999);}}}}
                drop(->r);}}'''
        self.assertEqual(self.native(source).stdout,'255\n255\n')
        for wrong in (result_type('Int',2),result_type(CASES['char_at'][0],2),result_type(CASES['conversion'][0],1)):
            with self.subTest(wrong=wrong),self.assertRaises(Error):
                verify_program(source.replace(f'let r:{typ}=relay',f'let r:{wrong}=relay'))
        with self.assertRaisesRegex(Error,'plus utilisable'):
            verify_program(source.replace('drop(->copy);drop(->r);','drop(->copy);let after=copy;drop(->after);drop(->r);'))

    def test_sync_creation_checks_the_full_capture_type(self):
        target='Result<Result<u8,IntegerConversionError>,runtime::Error>'
        prefix=f'async fn inspect(r:{target}){{drop(->r);}}'
        declarations={
            'Int':'async fn leaf()->Int{return 3;}',
            'Bool':'async fn leaf()->Bool{return true;}',
            'u8':'async fn leaf()->u8{let n:u8=3;return n;}',
            'char':'async fn leaf(c:char)->char{return c;}',
            '()':'async fn leaf(){}',
            'runtime::Error':'async fn leaf()->runtime::Error{return runtime::Error::LaunchFailed;}',
            'Result<char,CharAtError>':'async fn leaf()->Result<char,CharAtError>{return "é".char_at(0);}',
            'Result<char,CharFromStrError>':'async fn leaf()->Result<char,CharFromStrError>{return char::from_str("é");}',
        }
        for actual, declaration in declarations.items():
            call='leaf(c)' if actual=='char' else 'leaf()'
            body=f'let h=runtime::spawn(->{call});let r=h.join();let pending=inspect(r);drop(->pending);'
            if actual=='char':
                body='match char::from_str("é"){Ok(c)=>{'+body+'},Err(_)=>{}}'
            source=prefix+declaration+'fn main(){'+body+'}'
            with self.subTest(actual=actual),self.assertRaisesRegex(Error,'capture async : attendu'):
                verify_program(source)
        for value in ('3', 'true'):
            source='async fn inspect(e:runtime::Error){match e{runtime::Error::LaunchFailed=>{}}}fn main(){let t=inspect('+value+');drop(->t);}'
            with self.subTest(value=value),self.assertRaisesRegex(Error,'capture async : attendu'):
                verify_program(source)

    def test_extracted_fallible_payload_requires_use(self):
        source='''async fn leaf()->Result<u8,IntegerConversionError>{return u8::try_from(255);}
            async fn parent(){let h=runtime::spawn(->leaf());let r=h.await;
                match r{Ok(inner)=>{BODY},Err(_)=>{}}}
            fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(())=>{},Err(_)=>{}}}'''
        self.assertEqual(self.native(source.replace('BODY','drop(->inner);')).stdout,'')
        with self.assertRaisesRegex(Error,'résultat faillible.*sans usage explicite'):
            verify_program(source.replace('BODY',''))

    def test_borrowed_slice_cannot_enter_nonborrowing_envelope(self):
        source='''async fn leaf(s:&String)->Result<&str,SliceError>{return s.try_slice(0..1);}
            async fn consume(r:Result<Result<u8,IntegerConversionError>,runtime::Error>){drop(->r);}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("a");
                let h=runtime::spawn(->leaf(&s));let r=h.join();
                let h2=runtime::spawn(->consume(r));match h2.join(){Ok(())=>{},Err(_)=>{}}}'''
        valid=source.replace('let h2=runtime::spawn(->consume(r));match h2.join(){Ok(())=>{},Err(_)=>{}}',
            'match r{Ok(view)=>{match view{Ok(text)=>{print(text);},Err(_)=>{}}},Err(_)=>{}}')
        self.assertEqual(self.native(valid).stdout,'a\n')
        with self.assertRaisesRegex(Error, 'attendu.*Result|résultat.*emprunt'):
            verify_program(source)


if __name__=='__main__':unittest.main()
