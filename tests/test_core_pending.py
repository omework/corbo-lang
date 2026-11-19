import unittest

from crust import Error, compile_source, verify_program
from scheduler_faults import inject_submission_failure
import test_async_runtime
import test_type_features


class CorePendingTests(unittest.TestCase):
    native = test_type_features.TypeFeatureTests.native
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_projected_array_borrow_survives_join(self):
        source = '''
            async fn pick(row: &mut [i32; 2]) -> &mut i32 { &mut row[0] }
            fn main() {
                let mut row: [i32; 2] = [1, 2];
                let h = runtime::spawn(pick(&mut row));
                match h.join() {
                    Ok(v) => { print(*v); },
                    Err(_) => { print(0); },
                }
                print(row[1]);
            }
        '''
        self.assertEqual(self.native(source).stdout, '1\n2\n')
        with self.assertRaisesRegex(Error, 'emprunt|réserv'):
            verify_program(source.replace('print(*v);', 'print(row[0]); print(*v);'))

    def test_projected_array_borrow_survives_await_and_launch_failure(self):
        source = '''
            async fn pick(row: &mut [i32; 2], index: i64) -> &mut i32 { &mut row[index] }
            async fn worker() -> i64 {
                let mut row: [i32; 2] = [1, 2];
                let h = runtime::spawn(pick(&mut row, 1));
                match h.await {
                    Ok(v) => { print(*v); },
                    Err(_) => { print(row[0]); },
                }
                print(row[1]);
                0
            }
            fn main() {
                let h = runtime::spawn(worker());
                match h.join() { Ok(v) => { print(v); }, Err(_) => { print(99); } }
            }
        '''
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '2\n2\n0\n')
        failed = inject_submission_failure(code, at=1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '1\n2\n0\n')

    def test_bool_payload_and_suspending_if(self):
        source = '''
            async fn yes() -> bool { yield; true }
            async fn worker(flag: bool) -> i64 {
                let local = if flag { yes().await } else { false };
                let h = runtime::spawn_blocking(yes());
                let result = match h.await { Ok(value) => { value }, Err(_) => { false } };
                if local && result { 7 } else { 9 }
            }
            fn main() {
                let h = runtime::spawn(worker(true));
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(0); } }
            }
        '''
        self.assertEqual(self.native(source).stdout, '7\n')
        self.assertEqual(self.native(source.replace('worker(true)', 'worker(false)')).stdout, '9\n')

    def test_scalar_annotation_distinguishes_allocations(self):
        source = 'fn main(){let mut p=pool<i32>(1);let n:A<i32>=p.new(10);print(*n);}'
        self.assertEqual(self.native(source).stdout, '10\n')
        with self.assertRaisesRegex(Error, 'annotation.*incompatible.*allocation'):
            verify_program(source.replace('A<i32>', 'i32'))

    def test_async_array_write_uses_the_element_type(self):
        source = '''
            async fn set(row: &mut [i32; 2]) { row[0] = 12; }
            fn main() {
                let mut row: [i32; 2] = [1, 2];
                let h = runtime::spawn(set(&mut row));
                match h.join() { Ok(_) => { print(row[0]); }, Err(_) => { print(0); } }
            }
        '''
        self.assertEqual(self.native(source).stdout, '12\n')
        with self.assertRaisesRegex(Error, 'hors des bornes'):
            verify_program(source.replace('12;', '2147483648;'))

    def test_async_handle_annotation_and_context(self):
        source = '''
            async fn work() -> i64 { yield; 42 }
            async fn parent() -> i64 {
                let h: runtime::AsyncHandle<i64> = runtime::spawn_blocking(work());
                match h.await { Ok(value) => { value }, Err(_) => { 0 } }
            }
            fn main() {
                let h = runtime::spawn(parent());
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(0); } }
            }
        '''
        self.assertEqual(self.native(source).stdout, '42\n')
        moved = source.replace(
            'match h.await', 'let moved: runtime::AsyncHandle<i64> = h; match moved.await')
        self.assertEqual(self.native(moved).stdout, '42\n')
        with self.assertRaisesRegex(Error, 'AsyncHandle<i64> attendu'):
            verify_program(moved.replace('let moved: runtime::AsyncHandle<i64>', 'let moved: runtime::Handle<i64>'))
        ordinary = source.replace(
            'AsyncHandle<i64> = runtime::spawn_blocking(work())', 'Handle<i64> = runtime::spawn(work())')
        self.assertEqual(self.native(ordinary).stdout, '42\n')
        thread = ordinary.replace('runtime::spawn(work())',
                                  'runtime::thread({ let value: i64 = 42; value })')
        self.assertEqual(self.native(thread).stdout, '42\n')
        with self.assertRaisesRegex(Error, 'AsyncHandle<i64> attendu'):
            verify_program(source.replace('AsyncHandle<i64>', 'AsyncHandle<i32>').replace(
                'Ok(value) => { value }', 'Ok(_) => { 42 }'))
        with self.assertRaisesRegex(Error, 'retourne un AsyncHandle'):
            verify_program(source.replace('AsyncHandle<i64>', 'Handle<i64>'))
        with self.assertRaisesRegex(Error, 'exige un contexte async'):
            verify_program(source.replace('runtime::spawn(parent())', 'runtime::spawn_blocking(work())'))

    def test_async_handle_transfers_into_async_parameter(self):
        source = """
            async fn work() -> i64 { yield; 42 }
            async fn receive(h: runtime::AsyncHandle<i64>) -> i64 {
                match h.await { Ok(v) => { v }, Err(_) => { 0 } }
            }
            async fn parent() -> i64 {
                let h = runtime::spawn_blocking(work());
                receive(h).await
            }
            fn main() {
                let h = runtime::spawn(parent());
                match h.join() { Ok(v) => { print(v); }, Err(_) => { print(0); } }
            }
        """
        self.assertEqual(self.native(source).stdout, '42\n')
        code = compile_source(source)
        dispatch = 'int error = crust_scheduler_dispatch(blocking);'
        self.assertIn(dispatch, code)
        failed = code.replace(dispatch, 'int error = blocking ? EAGAIN : crust_scheduler_dispatch(0);')
        self.assertEqual(self.run_c_oracle(failed).stdout, '0\n')
        with self.assertRaisesRegex(Error, 'AsyncHandle<i64> attendu'):
            verify_program(source.replace('spawn_blocking(work())', 'spawn(work())'))
        with self.assertRaisesRegex(Error, 'déjà consommé'):
            verify_program(source.replace('receive(h).await', 'let n=receive(h).await; receive(h).await'))
        dropped = source.replace('receive(h).await', 'let pending=receive(h); drop(pending); 9')
        self.assertEqual(self.native(dropped).stdout, '9\n')
        borrowed = source.replace('work() -> i64 { yield; 42 }',
                                  'work(x: &i64) -> i64 { yield; *x }')
        borrowed = borrowed.replace('let h = runtime::spawn_blocking(work());',
                                    'let n: i64=42; let h=runtime::spawn_blocking(work(&n));')
        with self.assertRaisesRegex(Error, 'branche doit être autonome'):
            verify_program(borrowed)

    def test_async_handle_keeps_its_type_through_control_flow(self):
        program = """
            async fn work() -> i64 { 42 }
            async fn parent(flag: bool) -> i64 {
                let h: runtime::AsyncHandle<i64> = INITIALIZER;
                match h.await { Ok(value) => { value }, Err(_) => { 0 } }
            }
            fn main() {
                let h = runtime::spawn(parent(true));
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(0); } }
            }
        """
        initializers = (
            """if flag {
                let a = runtime::spawn_blocking(work()); a
            } else {
                let b = runtime::spawn_blocking(work()); b
            }""",
            "loop { let a = runtime::spawn_blocking(work()); break a; }",
        )
        for initializer in initializers:
            with self.subTest(initializer=initializer):
                source = program.replace('INITIALIZER', initializer)
                self.assertEqual(self.native(source).stdout, '42\n')
                with self.assertRaisesRegex(Error, 'type de handle|annotation de handle'):
                    verify_program(source.replace('spawn_blocking', 'spawn', 1))

    def test_copied_fixed_array_does_not_require_waiting_for_branch(self):
        source = """
            async fn work(row: [i64; 2]) -> i64 {
                yield;
                print(row[0]);
                row[0]
            }
            fn main() {
                let row: [i64; 2] = [42, 7];
                let h = runtime::spawn(work(row));
                drop(h);
            }
        """
        self.assertEqual(self.native(source).stdout, '42\n')
        borrowed = source.replace('row: [i64; 2])', 'row: &[i64; 2])').replace('work(row)', 'work(&row)')
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(borrowed)

    def test_branch_contract_and_cleanup_without_wait(self):
        prefix = '''
            async fn work(x: i64) -> i64 { yield; print(x); x }
            #(branch: join=result.join())
            fn start(x: i64) -> runtime::Handle<i64> { runtime::spawn(work(x)) }
        '''
        joined = prefix + '''
            fn main() {
                let h = start(42);
                match h.join() { Ok(v) => { print(v); }, Err(_) => { print(0); } }
            }
        '''
        self.assertEqual(self.native(joined).stdout, '42\n42\n')
        branched = prefix.replace('{ runtime::spawn(work(x)) }', '''
            { if x == 42 { return runtime::spawn(work(x)); } runtime::spawn(work(7)) }
        ''')
        self.assertEqual(self.native(branched + 'fn main(){let h=start(42);drop(h);}').stdout, '42\n')
        self.assertEqual(self.native(branched + 'fn main(){let h=start(0);drop(h);}').stdout, '7\n')
        relay = branched + '''
            #(branch: join=result.join())
            fn forward(x: i64) -> runtime::Handle<i64> { let h = start(x); h }
            fn main() { let h = forward(42); drop(h); }
        '''
        self.assertEqual(self.native(relay).stdout, '42\n')
        with self.assertRaisesRegex(Error, 'contrat branch.*indéterminé'):
            verify_program(relay.replace('#(branch: join=result.join())', '', 1))
        for end in ('drop(h);', ''):
            source = prefix.split('#(branch', 1)[0] + 'fn main(){let h=runtime::spawn(work(42));' + end + '}'
            self.assertEqual(self.native(source).stdout, '42\n')
        discarded = prefix.split('#(branch', 1)[0] + 'fn main(){runtime::spawn(work(42));}'
        self.assertEqual(self.native(discarded).stdout, '42\n')
        code = compile_source(discarded)
        self.assertEqual(code.count('    crust_task_context_close();'), 1)
        # No factory or context shutdown may reap this slot before the check.
        code = code.replace('    crust_task_context_close();', '''
    while (!task_pool_is_empty(&crust_task_context.pool_work)) sched_yield();
    crust_task_context_close();
''')
        self.assertEqual(self.run_c_oracle(code).stdout, '42\n')
        with self.assertRaisesRegex(Error, 'attente disponible'):
            verify_program(prefix.replace('result.join()', 'result.close()'))
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program('''
                async fn work(x: &i64) { yield; print(*x); }
                fn main(){let x:i64=42;let h=runtime::spawn(work(&x));drop(h);}
            ''')
