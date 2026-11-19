"""F2/B5/AS8: error values remain typed and detached from Result storage."""
from pathlib import Path
import unittest
from crust import Error, verify_program
import test_async_vector_results as results

VARIANTS={
    'ReadError':('EndOfStream','CapacityExceeded','Io'),
    'CapacityError':('CapacityExceeded',),
    'ByteReplaceError':('OutOfBounds','InvalidUtf8'),
    'CharAtError':('OutOfBounds','NotCharBoundary'),
    'CharFromStrError':('Empty','MultipleChars'),
    'IntegerConversionError':('OutOfRange',),
    'SliceError':('OutOfBounds','NotCharBoundary'),
}


def observe(typ,name='e'):
    return 'match '+name+'{'+','.join(f'{typ}::{v}=>{{print({i+1});}}' for i,v in enumerate(VARIANTS[typ]))+'}'


class BuiltinErrorValueTests(unittest.TestCase):
    run_native=results.AsyncVectorResultTests.run_native
    reject_blocking=results.AsyncVectorResultTests.reject_blocking
    rejecting_callback=results.AsyncVectorResultTests.rejecting_callback

    def test_recorded_error_binding(self):
        source=(Path(__file__).resolve().parents[1]/'validation/open-async-read-error-binding.crb').read_text()
        self.assertEqual(self.run_native(source).stdout,'-1\n')

    def test_every_variant_through_captures_returns_and_sync_contract(self):
        for typ,variants in VARIANTS.items():
            for index,variant in enumerate(variants):
                for async_observer in (False,True):
                    source=f'''fn relay(e:{typ})->{typ}{{return e;}}
                        async fn child(e:{typ})->{typ}{{let saved=e;drop(->e);yield;return saved;}}
                        async fn parent(e:{typ})->{typ}{{return child(e).await;}}
                        async fn inspect(e:{typ}){{yield;{observe(typ)}}}
                        fn main(){{let h=runtime::spawn(->parent(relay({typ}::{variant})));
                        match h.join(){{Ok(e)=>{{BODY}},Err(_)=>{{print(99);}}}}}}'''
                    body=('let h2=runtime::spawn(->inspect(e));match h2.join(){Ok(())=>{},Err(_)=>{print(98);}}'
                          if async_observer else observe(typ))
                    with self.subTest(typ=typ,variant=variant,async_observer=async_observer):
                        self.assertEqual(self.run_native(source.replace('BODY',body)).stdout,f'{index+1}\n')

    def test_error_from_each_operation_is_status_not_success_payload(self):
        cases=(
            ('ReadError','v:&mut Vector<u8>','v.read_fd(-1)','',3),
            ('ReadError','v:&mut Vector<u8>','v.read_fd(0)','',1),
            ('ReadError','v:&mut Vector<u8>','v.read_fd(-1)',
             'let mut i=0;while i<1048576{v.push(0);i=i+1;}',2),
            ('CapacityError','v:&mut Vector<u8>','v.try_extend(&bytes)',
             'let mut i=0;while i<1048576{v.push(0);i=i+1;}let bytes:[u8;1]=[9];',1),
            ('ByteReplaceError','v:&mut String','v.replace_byte(0,0)','v.push_str("é");',2),
            ('ByteReplaceError','v:&mut String','v.replace_byte(9,0)','v.push_str("é");',1),
            ('CharAtError','v:&mut String','v.char_at(1)','v.push_str("é");',2),
            ('CharAtError','v:&mut String','v.char_at(9)','v.push_str("é");',1),
            ('CharFromStrError','v:&mut String','char::from_str("ab")','v.push_str("x");',2),
            ('CharFromStrError','v:&mut String','char::from_str("")','v.push_str("x");',1),
            ('IntegerConversionError','v:&mut String','u8::try_from(300)','v.push_str("x");',1),
            ('SliceError','v:&mut String','v.try_slice(..1)','v.push_str("é");',2),
            ('SliceError','v:&mut String','v.try_slice(..9)','v.push_str("é");',1),
        )
        for typ,param,operation,setup,expected in cases:
            pool='Vector<u8>' if 'Vector' in param else 'String'
            fallback=VARIANTS[typ][0]
            source=f'''async fn work({param})->{typ}{{{setup}yield;
                match {operation}{{Ok(_)=>{{return {typ}::{fallback};}},
                    Err(e)=>{{let saved=e;drop(->e);yield;return saved;}}}}}}
                fn main(){{let mut p=pool<{pool}>(1);#(directive,stack_region_max_size=1M){{
                    let mut v=p.new();let h=runtime::spawn(->work(&mut v));let result=h.join();
                    drop(->v);let fresh=p.new();drop(->fresh);
                    match result{{Ok(e)=>{{{observe(typ)}}},Err(_)=>{{print(99);}}}}}}}}'''
            with self.subTest(typ=typ,operation=operation,expected=expected):
                self.assertEqual(self.run_native(source,stdin='').stdout,f'{expected}\n')

    def test_sync_extraction_and_contracts_do_not_treat_errors_as_success(self):
        for typ,operation,expected in (
            ('ReadError','v.read_fd(-1)',3),
            ('CharFromStrError','char::from_str("ab")',2),
            ('CharFromStrError','char::from_str("")',1),
            ('IntegerConversionError','u8::try_from(300)',1),
        ):
            source=f'''fn extract(v:&mut Vector<u8>)->{typ}{{
                match {operation}{{Ok(_)=>{{return {typ}::{VARIANTS[typ][0]};}},Err(e)=>{{return e;}}}}}}
                fn relay(v:&mut Vector<u8>)->{typ}{{return extract(&mut *v);}}
                fn main(){{let mut p=pool<Vector<u8>>(1);let mut v=p.new();let e=relay(&mut v);drop(->v);{observe(typ)}}}'''
            with self.subTest(typ=typ):
                self.assertEqual(self.run_native(source).stdout,f'{expected}\n')

    def test_control_results_assignment_and_drop(self):
        source='''async fn choose()->ReadError{
            let mut e:ReadError=if true{ReadError::Io}else{ReadError::EndOfStream};
            let saved=e;drop(->e);yield;
            let mut out:ReadError=loop{break saved;};
            out=ReadError::CapacityExceeded;return out;}
            fn main(){let h=runtime::spawn(->choose());match h.join(){Ok(e)=>{BODY},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source.replace('BODY',observe('ReadError'))).stdout,'2\n')

    def test_typed_envelopes_and_launch_error(self):
        source='''async fn leaf(e:ReadError)->ReadError{yield;return e;}
            async fn parent(e:ReadError)->Result<ReadError,runtime::Error>{
                let h=runtime::spawn_blocking(->leaf(e));return h.await;}
            fn relay(r:Result<Result<ReadError,runtime::Error>,runtime::Error>)->Result<Result<ReadError,runtime::Error>,runtime::Error>{return r;}
            fn main(){let h=runtime::spawn(->parent(ReadError::Io));
                match relay(h.join()){Ok(inner)=>{match inner{Ok(e)=>{BODY},Err(_)=>{print(88);}}},Err(_)=>{print(99);}}}'''
        for failed in (False,True):
            with self.subTest(failed=failed):
                self.assertEqual(self.run_native(source.replace('BODY',observe('ReadError')),reject=failed).stdout,
                                 '88\n' if failed else '3\n')

    def test_handle_await_payload_in_async_caller(self):
        for typ,variants in VARIANTS.items():
            source=f'''async fn child(e:{typ})->{typ}{{yield;return e;}}
                async fn parent(e:{typ})->{typ}{{let h=runtime::spawn(->child(e));
                    match h.await{{Ok(value)=>{{yield;return value;}},Err(_)=>{{return {typ}::{variants[0]};}}}}}}
                fn main(){{let h=runtime::spawn(->parent({typ}::{variants[-1]}));
                    match h.join(){{Ok(e)=>{{{observe(typ)}}},Err(_)=>{{print(99);}}}}}}'''
            with self.subTest(typ=typ):
                self.assertEqual(self.run_native(source).stdout,f'{len(variants)}\n')

    def test_named_match_error_does_not_become_a_borrow_of_result(self):
        source='''async fn work(text:&String)->SliceError{
            let r=text.try_slice(..1);
            let saved=match r{Ok(_)=>{SliceError::OutOfBounds},Err(e)=>{e}};
            drop(->r);yield;return saved;}
            fn main(){let mut p=pool<String>(1);let mut text=p.new();text.push_str("é");
                let h=runtime::spawn(->work(&text));let r=h.join();drop(->text);
                let fresh=p.new();drop(->fresh);
                match r{Ok(e)=>{BODY},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source.replace('BODY',observe('SliceError'))).stdout,'2\n')

    def test_async_capture_and_sync_contract_reject_type_erasure(self):
        prefix='async fn leaf(e:ReadError){drop(->e);}'
        for value in ('1','true','CapacityError::CapacityExceeded','runtime::Error::LaunchFailed'):
            with self.subTest(value=value),self.assertRaises(Error):
                verify_program(prefix+f'async fn parent(){{let t=leaf({value});drop(->t);}}fn main(){{let t=parent();drop(->t);}}')
        for typ,fallback in (('Int','0'),('ByteReplaceError','ByteReplaceError::OutOfBounds')):
            source=f'''fn bad(v:&mut Vector<u8>)->{typ}{{
                match v.read_fd(-1){{Ok(_)=>{{return {fallback};}},Err(e)=>{{return e;}}}}}}
                fn main(){{let mut p=pool<Vector<u8>>(1);let mut v=p.new();let ignored=bad(&mut v);drop(->ignored);}}'''
            with self.subTest(typ=typ),self.assertRaises(Error):verify_program(source)

    def test_match_must_cover_exact_error_type(self):
        for expression in (
            'match e{ReadError::Io=>{print(1);}}',
            'match e{ReadError::Io=>{},ReadError::Io=>{},_=>{}}',
            'match e{ReadError::Missing=>{},_=>{}}',
            'match e{Ok(n)=>{print(n);},Err(_)=>{}}',
        ):
            with self.subTest(expression=expression),self.assertRaises(Error):
                verify_program('async fn work(e:ReadError){'+expression+'}fn main(){let t=work(ReadError::Io);drop(->t);}')

    def test_computed_error_wildcard_evaluates_once(self):
        source='''async fn choose(n:&mut Int)->ReadError{yield;n.set(*n+1);return ReadError::Io;}
            async fn work(){let mut count=0;
                match (if true{choose(&mut count).await}else{ReadError::EndOfStream}){_=>{print(count);}}}
            fn main(){let h=runtime::spawn(->work());match h.join(){Ok(())=>{},Err(_)=>{print(99);}}}'''
        self.assertEqual(self.run_native(source).stdout,'1\n')

    def test_error_binding_after_specific_variant_keeps_actual_error(self):
        for asynchronous in (False,True):
            for fd,expected in ((-1,'3\n'),(0,'8\n')):
                body=f'''match v.read_fd({fd}){{Ok(n)=>{{print(n);}},
                    Err(ReadError::EndOfStream)=>{{print(8);}},Err(e)=>{{{observe('ReadError')}}}}}'''
                if asynchronous:
                    source='async fn work(v:&mut Vector<u8>){yield;'+body+'''}
                        fn main(){let mut p=pool<Vector<u8>>(1);let mut v=p.new();let h=runtime::spawn(->work(&mut v));
                        match h.join(){Ok(())=>{},Err(_)=>{print(99);}}}'''
                else:
                    source='fn main(){let mut p=pool<Vector<u8>>(1);let mut v=p.new();'+body+'}'
                with self.subTest(asynchronous=asynchronous,fd=fd):
                    self.assertEqual(self.run_native(source,stdin='').stdout,expected)
        for arms in (
            'Err(ReadError::Io)=>{},Err(e)=>{drop(->e);}',
            'Ok(n)=>{print(n);},Err(ReadError::Io)=>{},Err(ReadError::EndOfStream)=>{},Err(ReadError::CapacityExceeded)=>{},Err(e)=>{drop(->e);}',
        ):
            with self.subTest(arms=arms),self.assertRaises(Error):
                verify_program('fn main(){let mut p=pool<Vector<u8>>(1);let mut v=p.new();match v.read_fd(-1){'+arms+'}}')

    def test_nominal_type_boundaries(self):
        for expected in VARIANTS:
            for actual,variants in VARIANTS.items():
                if actual==expected:continue
                source=f'''async fn take(e:{expected}){{drop(->e);}}
                    fn main(){{let t=take({actual}::{variants[0]});drop(->t);}}'''
                with self.subTest(expected=expected,actual=actual),self.assertRaisesRegex(Error,'attendu'):
                    verify_program(source)
        for body in ('let n:Int=e;print(n);','print(e);','let n=e as Int;print(n);',
                     'drop(->e);let alias=e;drop(->alias);',
                     'match e{CharAtError::OutOfBounds=>{},CharAtError::NotCharBoundary=>{}}'):
            with self.subTest(body=body),self.assertRaises(Error):
                verify_program('async fn work(e:ReadError){'+body+'}fn main(){let t=work(ReadError::Io);drop(->t);}')

    def test_wrong_return_and_extraction_annotation(self):
        for typ in ('Int','CharFromStrError'):
            source=f'''async fn work(v:&mut Vector<u8>)->{typ}{{
                match v.read_fd(-1){{Ok(_)=>{{return {'0' if typ=='Int' else 'CharFromStrError::Empty'};}},
                    Err(e)=>{{return e;}}}}}}
                fn main(){{let mut p=pool<Vector<u8>>(1);let mut v=p.new();
                    let h=runtime::spawn(->work(&mut v));drop(->h.join());}}'''
            with self.subTest(typ=typ),self.assertRaises(Error):verify_program(source)


if __name__=='__main__':unittest.main()
