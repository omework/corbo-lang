"""RT5/RT6: every join adds one independently observable Result layer."""
from pathlib import Path
import unittest
from crust import Error, compile_source, verify_program
import test_plain_join_contracts as contracts


def result_type(payload, depth):
    for _ in range(depth):
        payload = f'Result<{payload},runtime::Error>'
    return payload


def observe(subject, depth, pattern, body):
    if depth == 1:
        success = pattern + '=>{' + body + '}'
    else:
        success = f'Ok(layer{depth})=>{{' + observe(f'layer{depth}', depth - 1, pattern, body) + '}'
    return 'match ' + subject + '{' + success + f',Err(e)=>{{match e{{runtime::Error::LaunchFailed=>{{print({100 + depth});}}}}}}' + '}'


def program(payload='Int', depth=2, failed_layer=None, inspect=False):
    declaration, (pattern, body, expected) = contracts.PlainJoinContractTests.case(payload)
    char = payload == 'char'
    parameters = 'c:char' if char else ''
    arguments = 'c' if char else ''
    previous = 'leaf'
    for level in range(1, depth):
        launch = 'spawn_blocking' if failed_layer == level else 'spawn'
        declaration += f'''async fn layer{level}({parameters})->{result_type(payload, level)}{{
            let h=runtime::{launch}(->{previous}({arguments}));
            let r=h.await;yield;return r;}}'''
        previous = f'layer{level}'
    launch = 'spawn_blocking' if failed_layer == depth else 'spawn'
    main = f'let h=runtime::{launch}(->{previous}({arguments}));let r=h.join();'
    if inspect:
        declaration += f'''async fn inspect(r:{result_type(payload, depth)}){{yield;
            let copy=r;drop(->r);yield;{observe('copy', depth, pattern, body)}}}'''
        main += 'let consumer=runtime::spawn(->inspect(r));match consumer.join(){Ok(())=>{},Err(_)=>{print(999);}}'
    else:
        main += observe('r', depth, pattern, body)
    if char:
        main = 'match char::from_str("é"){Ok(c)=>{' + main + '},Err(_)=>{print(998);}}'
    return declaration + 'fn main(){' + main + '}', expected


class NestedPlainResultTests(unittest.TestCase):
    native = contracts.PlainJoinContractTests.native
    run_c_oracle = contracts.PlainJoinContractTests.run_c_oracle
    reject_blocking = contracts.PlainJoinContractTests.reject_blocking
    rejecting_callback = contracts.PlainJoinContractTests.rejecting_callback

    def test_recorded_async_return_gap(self):
        source = (Path(__file__).resolve().parents[1] / 'validation/open-async-plain-result-return.crb').read_text()
        self.assertEqual(self.native(source).stdout, '7\n')

    def test_payload_depth_and_capture_matrix(self):
        # Oracle depends only on the leaf value, not on compiler type tables.
        for payload in ('Int', 'Bool', 'u8', 'char', '()', 'runtime::Error'):
            for depth in (2, 4):
                for inspect in (False, True):
                    with self.subTest(payload=payload, depth=depth, inspect=inspect):
                        source, expected = program(payload, depth, inspect=inspect)
                        self.assertEqual(self.native(source).stdout, expected + '\n')

    def test_failure_remains_at_its_own_layer(self):
        # Reject one selected launch site. Outer successful joins must preserve
        # that inner error; a failed outer launch must not execute inner code.
        for failed_layer in (1, 2, 3, 4):
            for inspect in (False, True):
                source, _ = program(depth=4, failed_layer=failed_layer, inspect=inspect)
                with self.subTest(failed_layer=failed_layer, inspect=inspect):
                    code = self.reject_blocking(compile_source(source))
                    self.assertEqual(self.run_c_oracle(code).stdout, f'{100 + failed_layer}\n')

    def test_direct_await_and_computed_subjects_preserve_depth(self):
        prefix = '''async fn leaf()->Int{yield;return 17;}
            async fn wait()->Result<Int,runtime::Error>{
                let h=runtime::spawn(->leaf());let r=h.await;return r;}
            async fn relay()->Result<Int,runtime::Error>{return wait().await;}'''
        for expression in ('relay().await', '{let t=relay();<-t}.await',
                           'if true{relay().await}else{wait().await}',
                           'loop{break relay().await;}'):
            source = prefix + 'async fn parent(){' + observe(expression, 1, 'Ok(v)', 'print(v);') + '''}
                fn main(){let h=runtime::spawn(->parent());match h.join(){Ok(())=>{},Err(_)=>{print(999);}}}'''
            with self.subTest(expression=expression):
                self.assertEqual(self.native(source).stdout, '17\n')

    def test_direct_handle_return_and_control_expression(self):
        for returned in ('return h.await;', 'return if true{h.await}else{h.await};'):
            for computed in (False, True):
                body = 'let h=runtime::spawn_blocking(->leaf());' + returned
                if computed:
                    body = returned.replace('h.await', 'runtime::spawn_blocking(->leaf()).await')
                source = 'async fn leaf()->Int{yield;return 17;}async fn parent()->Result<Int,runtime::Error>{' + body + '}'
                source += 'fn main(){let h=runtime::spawn(->parent());' + observe('h.join()', 2, 'Ok(v)', 'print(v);') + '}'
                with self.subTest(returned=returned, computed=computed):
                    code = compile_source(source)
                    self.assertEqual(self.run_c_oracle(code).stdout, '17\n')
                    self.assertEqual(self.run_c_oracle(self.reject_blocking(code)).stdout, '101\n')

    def test_nested_contracts_copies_control_flow_assignment_and_drop(self):
        typ = result_type('Int', 2)
        prefix, _ = program(depth=2)
        prefix = prefix[:prefix.index('fn main()')]
        source = prefix + f'''fn relay(r:{typ})->{typ}{{return r;}}
            async fn use_result(r:{typ}){{
                let mut copy:{typ}=if true{{r}}else{{r}};
                {observe('copy', 2, 'Ok(v)', 'print(v);')}
                copy=loop{{break r;}};yield;
                {observe('copy', 2, 'Ok(v)', 'print(v);')}
                drop(->copy);drop(->r);
            }}
            fn main(){{let h=runtime::spawn(->layer1());let r=relay(h.join());
                let mut copy:{typ}=r;
                {observe('copy', 2, 'Ok(v)', 'print(v);')}
                copy=if true{{r}}else{{r}};
                let t=runtime::spawn(->use_result(copy));
                match t.join(){{Ok(())=>{{}},Err(_)=>{{print(999);}}}}
                drop(->copy);drop(->r);}}'''
        self.assertEqual(self.native(source).stdout, '17\n17\n17\n')
        for bad in ('drop(->copy);let after=copy;drop(->after);',
                    'drop(->copy);print(copy);'):
            with self.subTest(bad=bad), self.assertRaises(Error):
                verify_program(source.replace('drop(->copy);drop(->r);', bad + 'drop(->r);'))

    def test_depth_and_payload_mismatches_are_rejected(self):
        source, _ = program(depth=3)
        for payload, depth in (('Int', 1), ('Int', 2), ('Int', 4), ('u8', 3), ('Bool', 3), ('&Int', 3), ('A<Int>', 3)):
            bad = source.replace('let r=h.join();', f'let r:{result_type(payload, depth)}=h.join();')
            with self.subTest(payload=payload, depth=depth), self.assertRaises(Error):
                verify_program(bad)
        for replacement in ('return 3;', 'return runtime::Error::LaunchFailed;'):
            with self.subTest(replacement=replacement), self.assertRaises(Error):
                verify_program(source.replace('return r;', replacement))

    def test_async_result_return_type_is_not_erased(self):
        source = """async fn leaf()->Int{return 17;}
            async fn parent()->Result<Int,runtime::Error>{
                let h=runtime::spawn(->leaf());let r=h.await;return r;}
            fn main(){let h=runtime::spawn(->parent());let r=h.join();drop(->r);}"""
        self.assertEqual(self.native(source).stdout, '')
        for payload in ('u8', 'Bool', 'char', '()', 'runtime::Error', result_type('Int', 1)):
            with self.subTest(payload=payload), self.assertRaisesRegex(Error, 'résultat attendu'):
                verify_program(source.replace('parent()->Result<Int,runtime::Error>',
                                               f'parent()->Result<{payload},runtime::Error>'))

    def test_nested_fallible_bindings_require_use(self):
        source, _ = program(depth=2, inspect=True)
        for bad in (source.replace('let copy=r;drop(->r);', 'let unused=r;let copy=r;drop(->r);'),
                    source.replace(observe('copy', 2, 'Ok(v)', 'print(v);'), 'match copy{Ok(inner)=>{},Err(_)=>{}}'),
                    source.replace('let r=h.await;yield;return r;', 'let unused=h.await;yield;return 1;')):
            with self.subTest(source=bad), self.assertRaisesRegex(Error, "résultat faillible.*sans usage explicite"):
                verify_program(bad)

    def test_nested_plain_result_releases_captures_and_reuses_slots(self):
        source = """async fn leaf(n:->Int)->Int{yield;return *n;}
            async fn parent(n:->Int)->Result<Int,runtime::Error>{
                let h=runtime::spawn_blocking(->leaf(->n));let r=h.await;return r;}
            fn main(){let mut p=pool<Int>(1);let n=p.new(17);address(n);
                let h=runtime::spawn(->parent(->n));let r=h.join();
                OBSERVE
                let reused=p.new(23);address(reused);print(reused);}
        """.replace('OBSERVE', observe('r', 2, 'Ok(v)', 'print(v);'))
        for failed in (False, True):
            with self.subTest(failed=failed):
                code = compile_source(source)
                run = self.run_c_oracle(self.reject_blocking(code) if failed else code)
                lines = run.stdout.splitlines()
                self.assertEqual(lines[0], lines[2])
                self.assertEqual(lines[1], '101' if failed else '17')
                self.assertEqual(lines[3], '23')
                self.assertEqual(run.stderr.count('destroy n=17'), 1)
        borrowed = """async fn leaf(n:&mut Int)->Int{yield;n.set(9);return *n;}
            async fn parent(n:&mut Int)->Result<Int,runtime::Error>{
                let h=runtime::spawn(->leaf(n));let r=h.await;return r;}
            fn main(){let mut p=pool<Int>(1);let mut n=p.new(17);
                let h=runtime::spawn(->parent(&mut n));BEFORE
                let r=h.join();drop(->n);
                OBSERVE
                let reused=p.new(23);print(reused);}
        """.replace('OBSERVE', observe('r', 2, 'Ok(v)', 'print(v);'))
        self.assertEqual(self.native(borrowed.replace('BEFORE', '')).stdout, '9\n23\n')
        for invalid in ('print(n);', 'drop(->n);', 'p.reset();'):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(Error, 'emprunt|exécution|utilisée'):
                verify_program(borrowed.replace('BEFORE', invalid), allow_legacy_reset=True)

    def test_layout_generation_is_independent_of_previous_programs(self):
        shallow, _ = program(depth=2)
        before = compile_source(shallow)
        deep, _ = program(depth=7)
        self.assertEqual(self.native(deep).stdout, '17\n')
        self.assertEqual(compile_source(shallow), before)
        self.assertNotIn('CrustPlainJoin7', before)
        self.assertEqual(self.native(f'fn relay(r:{result_type("Int", 5)})->{result_type("Int", 5)}{{return r;}}fn main(){{print(7);}}').stdout, '7\n')


if __name__ == '__main__':
    unittest.main()
