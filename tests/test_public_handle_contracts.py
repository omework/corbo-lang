"""Opaque public scalar-handle contracts retain captures independently of T."""
from pathlib import Path
import itertools
import unittest

from crust import Compiler, Parser, Error, compile_source, verify_program
import test_async_runtime
from scheduler_faults import inject_submission_failure


class PublicHandleContractTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def run_source(self, source, output):
        run = self.run_c_oracle(compile_source(source))
        self.assertEqual(run.stdout, output)
        return run

    def rejected(self, source, pattern):
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaisesRegex(Error, pattern):
                check(source)

    def test_two_frame_types_use_one_signature(self):
        source = (Path(__file__).resolve().parents[1] / 'validation/open-public-handle.crb').read_text()
        self.run_source(source, '7\n9\n')
        self.rejected(source.replace('handle: -> runtime::Handle<Int>', 'handle: -> runtime::Handle<Bool>'),
                      'handle .*attendu')
        self.rejected(source.replace('handle: -> runtime::Handle<Int>', 'handle: runtime::Handle<Int>'),
                      'transfert ->')

    def test_fixed_array_payloads_preserve_shape_and_detach_after_join(self):
        for typ, literal, zero, access, output in (
            ('[Int;2]', '[*v,*v+1]', '[0,0]', 'received[1]', '9\n'),
            ('[[Int;2];2]', '[[*v,*v+1],[*v+2,*v+3]]', '[[0,0],[0,0]]',
             'received[1][1]', '11\n'),
            ('[u8;2]', '[7,8]', '[0,0]', 'received[1] as Int', '8\n'),
        ):
            source = f'''async fn work(v:&mut Int)->{typ}{{
                *v=8;let values:{typ}={literal};yield;return <-values;}}
                fn launch(v:&mut Int)-><-runtime::Handle<{typ}>{{
                    let h=runtime::spawn(->work(v));return <-h;}}
                fn relay(h:->runtime::Handle<{typ}>)-><-runtime::Handle<{typ}>{{return <-h;}}
                fn finish(h:->runtime::Handle<{typ}>)->{typ}{{
                    match h.join(){{Ok(values)=>{{return <-values;}},
                        Err(_)=>{{let zero:{typ}={zero};return <-zero;}}}}}}
                fn main(){{let mut p=pool<Int>(1);let mut data=p.new(7);
                    let h=launch(&mut data);let next=relay(->h);
                    let received=finish(->next);drop(->data);
                    let reused=p.new(99);print(*reused);print({access});}}'''
            with self.subTest(typ=typ):
                self.run_source(source, '99\n'+output)
                self.rejected(source.replace('let received=finish', 'print(*data);let received=finish'),
                              'emprunt|capture')
                self.rejected(source.replace('let received=finish', 'drop(->data);let received=finish'),
                              'emprunt|capture')
                self.rejected(source.replace('runtime::Handle<'+typ+'>', 'runtime::Handle<Int>'),
                              'handle .*attendu|tableau.*attendu|type.*retour|retour.*attendu')

    def test_array_handle_contract_checks_extents_even_if_result_is_discarded(self):
        source = '''async fn first()->[Int;2]{let a:[Int;2]=[7,8];yield;return <-a;}
            async fn second()->[Int;2]{let b=[9,10];return <-b;}
            fn finish(h:->runtime::Handle<[Int;2]>){match h.join(){Ok(_)=>{},Err(_)=>{}}}
            fn main(){let h=runtime::spawn(->first());finish(->h);
                let next=runtime::spawn(->second());finish(->next);}'''
        self.run_source(source, '')
        for signature, values in (('[Int;3]', '[7,8,9]'), ('[[Int;1];2]', '[[7],[8]]'),
                                  ('[u8;2]', '[7,8]')):
            self.rejected(source.replace('first()->[Int;2]', 'first()->'+signature).replace(
                'a:[Int;2]', 'a:'+signature).replace('[7,8]', values),
                          'handle .*attendu')

    def test_calls_need_only_public_contracts(self):
        declarations = '''async fn work(v:&mut Int)->Int{yield;*v=9;return *v;}
            fn start(v:&mut Int)-><-runtime::Handle<Int>{
                let h=runtime::spawn(->work(v));return <-h;}
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
            fn finish(h:->runtime::Handle<Int>)->Int{
                match h.join(){Ok(n)=>{return n;},Err(_)=>{return 99;}}}'''
        interface = verify_program(declarations)
        script = '''let mut p=pool<Int>(1);let mut data=p.new(7);
            let h=start(&mut data);let next=relay(->h);
            USE
            print(finish(->next));print(*data);'''
        def caller(use):
            checker = Compiler()
            checker.contract_calls = True
            checker.function_contracts = interface.function_contracts
            nodes = Parser(script.replace('USE', use)).parse()
            checker.index(nodes)
            checker.block('root', nodes)
            return checker
        checked = caller('')
        self.assertEqual(checked.contract_call_log, ['start', 'relay', 'finish'])
        self.assertEqual(checked.functions, {})
        self.assertEqual(checked.async_definitions, {})
        self.assertEqual(checked.function_results, {})
        for use in ('print(*data);', 'drop(->data);'):
            with self.subTest(use=use), self.assertRaisesRegex(Error, 'emprunt|capture'):
                caller(use)

    def test_opaque_relay_cannot_drop_owned_capture_source(self):
        declarations = '''async fn work(text:->String)->Int{yield;return text.byte_len();}
            fn start(text:->String)-><-runtime::Handle<Int>{
                let h=runtime::spawn(->work(->text));return <-h;}
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
            fn again(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{
                let next=relay(->h);return <-next;}
            fn finish(h:->runtime::Handle<Int>)->Int{
                match h.join(){Ok(n)=>{return n;},Err(_)=>{return 99;}}}'''
        interface = verify_program(declarations)
        for short_pool in (False, True):
            pool = 'let mut p=pool<String>(1);'
            script = ('' if short_pool else pool) + 'let received={' + (pool if short_pool else '') + '''
                let text=p.new();let h=start(->text);let next=again(->h);<-next};
                print(finish(->received));'''
            checker = Compiler()
            checker.contract_calls = True
            checker.function_contracts = interface.function_contracts
            nodes = Parser(script).parse()
            checker.index(nodes)
            if short_pool:
                with self.assertRaisesRegex(Error, 'pool|source|survit'):
                    checker.block('root', nodes)
            else:
                checker.block('root', nodes)

    def test_payload_checked_even_when_callee_discards_value(self):
        source = '''async fn work()->Bool{yield;return true;}
            fn drain(h:->runtime::Handle<Bool>){match h.join(){Ok(_)=>{},Err(_)=>{}}}
            fn main(){let h=runtime::spawn(->work());drain(->h);}'''
        self.run_source(source, '')
        self.rejected(source.replace('work()->Bool', 'work()->Int').replace('return true;', 'return 7;'),
                      'handle .*attendu')

    def test_shared_vector_reborrow_survives_public_factory(self):
        source = '''async fn observe(v:&Vector<Int>)->Int{yield;return v.len();}
            fn launch(v:&mut Vector<Int>)-><-runtime::Handle<Int>{
                let h=runtime::spawn(->observe(v));return <-h;}
            fn relay(v:&mut Vector<Int>)->Int{let h=launch(v);
                let part=&v[..];let length=v.len();
                return match h.join(){Ok(n)=>{n+length+part[0]},Err(_)=>{99}};}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push(10);v.push(20);
                print(relay(&mut v));v.push(30);print(v.len());}'''
        self.run_source(source, '14\n3\n')
        self.rejected(source.replace('let part=&v[..];', 'v.push(30);let part=&v[..];'), 'emprunt')

    def test_factory_and_relays_preserve_mutable_capture(self):
        source = '''async fn work(v:&mut Int)->Int{yield;*v=9;return *v;}
            fn start(v:&mut Int)-><-runtime::Handle<Int>{
                let h=runtime::spawn(->work(v));return <-h;}
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
            fn again(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{
                let next=relay(->h);return <-next;}
            fn finish(h:->runtime::Handle<Int>)->Int{
                match h.join(){Ok(n)=>{return n;},Err(_)=>{return 99;}}}
            fn main(){let mut p=pool<Int>(1);let mut data=p.new(7);
                let h=start(&mut data);let next=again(->h);
                print(finish(->next));print(*data);
                drop(->data);let reused=p.new(11);print(*reused);}'''
        run = self.run_source(source, '9\n9\n11\n')
        self.assertEqual(run.stderr.count('destroy data=9'), 1)
        for statement in ('print(*data);', 'drop(->data);'):
            self.rejected(source.replace('print(finish(->next));', statement+'print(finish(->next));'),
                          'emprunt|capture')
        self.rejected(source.replace('print(finish(->next));', 'drop(->next);'), 'join requis')
        self.rejected(source.replace('return <-h;', 'return h;', 1), 'transfert|copi|déplacement|retour')

    def test_shared_capture_stays_shared_through_public_relay(self):
        source = '''async fn read(v:&Int)->Int{yield;return *v;}
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
            fn finish(h:->runtime::Handle<Int>)->Int{
                match h.join(){Ok(n)=>{return n;},Err(_)=>{return 99;}}}
            fn main(){let mut p=pool<Int>(1);let mut data=p.new(7);
                let h=runtime::spawn(->read(&data));let next=relay(->h);
                print(*data);print(finish(->next));data=9;print(*data);}'''
        self.run_source(source, '7\n7\n9\n')
        self.rejected(source.replace('print(*data);print(finish', 'data=8;print(finish'), 'emprunt|capture')

    def test_conditional_factory_unions_two_different_tasks(self):
        source = '''async fn first(v:&Int)->Int{yield;return *v;}
            async fn second(v:&Int)->Int{let extra=[1,2];yield;return *v+extra[1];}
            fn choose(flag:bool,a:&Int,b:&Int)-><-runtime::Handle<Int>{
                if flag {let h=runtime::spawn(->first(a));return <-h;}
                else {let h=runtime::spawn(->second(b));return <-h;}}
            fn finish(h:->runtime::Handle<Int>)->Int{
                match h.join(){Ok(n)=>{return n;},Err(_)=>{return 99;}}}
            fn main(){let mut p=pool<Int>(2);let mut a=p.new(7);let mut b=p.new(9);
                let h=choose(true,&a,&b);print(finish(->h));
                let next=choose(false,&a,&b);print(finish(->next));}'''
        self.run_source(source, '7\n11\n')
        for target in ('a', 'b'):
            self.rejected(source.replace('print(finish(->h));', f'{target}=8;print(finish(->h));'), 'emprunt|capture')

    def test_obligation_verified_even_for_uncalled_helper(self):
        for body in ('', 'drop(->h);'):
            self.rejected('fn ignore(h:->runtime::Handle<Int>){'+body+'}fn main(){}', 'join requis')

    def test_mixed_captures_do_not_merge_shared_and_exclusive_permissions(self):
        source = '''async fn work(a:&Int,b:&mut Int,c:&Int)->Int{
                yield;*b=*a+*c;return *b;}
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
            fn main(){let mut p=pool<Int>(3);let a=p.new(7);let mut b=p.new(0);let c=p.new(9);
                let h=runtime::spawn(->work(&a,&mut b,&c));let next=relay(->h);
                print(*a);print(*c);
                match next.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                print(*b);}'''
        self.run_source(source, '7\n9\n16\n16\n')
        self.rejected(source.replace('print(*a);print(*c);', 'print(*b);'), 'emprunt|capture')
        self.rejected(source.replace('print(*a);print(*c);', 'drop(->c);'), 'emprunt|capture')

    def test_generic_handle_preserves_injected_pool_of_another_type(self):
        source = '''async fn work(p:&mut Pool<String>)->Int{
                let mut text=p.new();text.push_str("abc");yield;return text.byte_len();}
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
            fn main(){let mut strings=pool<String>(1);
                let h=runtime::spawn(->work(&mut strings));let next=relay(->h);
                match next.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                let text=strings.new();print(text.byte_len());}'''
        self.run_source(source, '3\n0\n')
        self.rejected(source.replace('match next.join()', 'let busy=strings.new();print(busy.byte_len());match next.join()'),
                      'pool incompatible|capture|emprunt')

    def test_generic_handle_keeps_owned_capture_pool_alive(self):
        source = '''async fn work(text:->String)->Int{yield;return text.byte_len();}
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}
            fn main(){let mut strings=pool<String>(1);let mut text=strings.new();text.push_str("abc");
                let h=runtime::spawn(->work(->text));let next=relay(->h);
                match next.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
                let reused=strings.new();print(reused.byte_len());}'''
        run = self.run_source(source, '3\n0\n')
        self.assertEqual(run.stderr.count('destroy text='), 1)
        failed = self.run_c_oracle(inject_submission_failure(compile_source(source), asynchronous=False, at=1))
        self.assertEqual(failed.stdout, '99\n0\n')
        self.assertEqual(failed.stderr.count('destroy text='), 1)
        invalid = '''async fn work(text:->String)->Int{yield;return text.byte_len();}
            fn make()-><-runtime::Handle<Int>{let mut p=pool<String>(1);let text=p.new();
                let h=runtime::spawn(->work(->text));return <-h;}
            fn main(){let h=make();match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.rejected(invalid, 'pool|survit|source')
        relayed = invalid.replace('return <-h;', 'let next=relay(->h);return <-next;') + '''
            fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{return <-h;}'''
        self.rejected(relayed, 'pool|survit|source')

    def test_legacy_reset_cannot_cross_pending_view_capture(self):
        source = '''async fn work(view:&str)->Int{yield;return view.byte_len();}
            fn finish(h:->runtime::Handle<Int>,p:&mut Pool<String>)->Int{
                RESET
                let n=match h.join(){Ok(n)=>{n},Err(_)=>{99}};
                AFTER
                return n;}
            fn main(){let mut p=pool<String>(1);let mut text=p.new();text.push_str("abc");
                let h=runtime::spawn(->work(&text[..]));print(finish(->h,&mut p));}'''
        # Captures remain protected until join. A reset after that wait may
        # occur inside the helper as well as after its return.
        valid = source.replace('RESET', '').replace('AFTER', '').replace(
            'print(finish(->h,&mut p));', 'print(finish(->h,&mut p));p.reset();')
        self.assertEqual(self.run_c_oracle(compile_source(valid, allow_legacy_reset=True)).stdout, '3\n')
        after_join = source.replace('RESET', '').replace('AFTER', 'p.reset();')
        self.assertEqual(self.run_c_oracle(compile_source(after_join, allow_legacy_reset=True)).stdout, '3\n')
        invalid = source.replace('RESET', 'p.reset();').replace('AFTER', '')
        for check in (verify_program, compile_source):
            with self.subTest(stage=check.__name__), self.assertRaises(Error):
                check(invalid, allow_legacy_reset=True)

    def test_capture_permission_model(self):
        # Independent rule: read conflicts with exclusive capture, write with
        # any capture. Parameter position and concrete task name are irrelevant.
        for modes in itertools.product(('none', 'ref', 'mut'), repeat=2):
            parameters, arguments = [], []
            for name, mode in zip(('a', 'b'), modes):
                if mode != 'none':
                    prefix = '&mut ' if mode == 'mut' else '&'
                    parameters.append(f'{name}:{prefix}Int')
                    arguments.append(prefix + name)
            base = f'''async fn work({','.join(parameters)})->Int{{yield;return 7;}}
                fn relay(h:->runtime::Handle<Int>)-><-runtime::Handle<Int>{{return <-h;}}
                fn main(){{let mut p=pool<Int>(2);let mut a=p.new(10);let mut b=p.new(20);
                    let h=runtime::spawn(->work({','.join(arguments)}));let next=relay(->h);
                    ACTION
                    match next.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{print(99);}}}}
                    print(*a);print(*b);}}
            '''
            for index, name in enumerate(('a', 'b')):
                for write in (False, True):
                    operation = f'{name}=8;' if write else f'print(*{name});'
                    conflict = modes[index] != 'none' if write else modes[index] == 'mut'
                    source = base.replace('ACTION', operation)
                    with self.subTest(modes=modes, target=name, write=write):
                        if conflict:
                            self.rejected(source, 'emprunt|capture')
                        else:
                            output = '' if write else f'{10 if index == 0 else 20}\n'
                            values = [10, 20]
                            if write:
                                values[index] = 8
                            self.run_source(source, output + f'7\n{values[0]}\n{values[1]}\n')

    def test_public_payload_shape_not_nominal_frame(self):
        cases = (
            ('Bool', '->Bool', 'return true;', 'Ok(v)=>{if v{return 7;}else{return 8;}}'),
            ('u8', '->u8', 'let text="A";return text[0];', 'Ok(v)=>{return v as Int;}'),
            ('Void', '', 'return;', 'Ok(())=>{return 7;}'),
        )
        for typ, result, body, arm in cases:
            source = f'''async fn work(){result}{{yield;{body}}}
                fn relay(h:->runtime::Handle<{typ}>)-><-runtime::Handle<{typ}>{{return <-h;}}
                fn finish(h:->runtime::Handle<{typ}>)->Int{{
                    match h.join(){{{arm},Err(_)=>{{return 99;}}}}}}
                fn main(){{let h=runtime::spawn(->work());let next=relay(->h);print(finish(->next));}}'''
            with self.subTest(typ=typ):
                self.run_source(source, '65\n' if typ == 'u8' else '7\n')
                self.rejected(source.replace(f'h:->runtime::Handle<{typ}>', 'h:->runtime::Handle<Int>', 1),
                              'handle .*attendu|retour')


if __name__ == '__main__':
    unittest.main()
