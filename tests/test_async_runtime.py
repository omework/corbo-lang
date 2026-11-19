"""Exercise the task transition ABI without going through code generation."""

from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from async_runtime import TASK_ASYNC_THREAD_RUNTIME, TASK_POOL_RUNTIME, TASK_RUNTIME, TASK_THREAD_RUNTIME
from crust import Error, compile_source, verify_program
from scheduler_faults import inject_submission_failure


class AsyncRuntimeTests(unittest.TestCase):
    def test_storage_draft_drop_consumes_async_local_arrays_after_last_loan(self):
        source = """
            async fn read(a: &[Int; 2]) -> Int { yield; return a[0]; }
            async fn run() -> Int {
                let values = [1, 2];
                let child = read(&values);
                BEFORE
                let first = child.await;
                drop(-> values);
                AFTER
                let next = [3, 4];
                yield;
                return first + next[0];
            }
            fn main() {
                let h = runtime::spawn(-> run());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('BEFORE', '').replace('AFTER', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '4\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'drop(-> values);').replace('AFTER', ''))
        for statement in ('print(values[0]);', 'print(values.len());', 'drop(-> values);'):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, 'plus utilisable'):
                verify_program(source.replace('BEFORE', '').replace('AFTER', statement))

    def test_mutable_capture_reserves_before_start_and_until_join(self):
        source = """
            async fn increment(n: &mut Int, amount: Int) {
                yield;
                n.set(*n + amount);
            }
            fn main() {
                let mut numbers = pool<Int>(1);
                let mut n = new(numbers) Int(10);
                let task = {
                    let inner = increment(&mut n, 5);
                    <- inner
                };
                BEFORE
                let h = runtime::spawn(-> task);
                RUNNING
                match h.join() {
                    Ok(()) => { print(1); },
                    Err(_) => { print(0); }
                }
                print(n);
                n.set(21);
                print(n);
            }
        """
        valid = source.replace('BEFORE', '').replace('RUNNING', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '1\n15\n21\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, runner, pointer) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '0\n10\n21\n')
        for position in ('BEFORE', 'RUNNING'):
            for conflict in ('print(n);', 'n.set(3);', 'drop(-> n);',
                             'let other = increment(&mut n, 5); drop(-> other);'):
                with self.subTest(position=position, conflict=conflict):
                    invalid = source.replace(position, conflict).replace('BEFORE', '').replace('RUNNING', '')
                    with self.assertRaisesRegex(Error, 'emprunt'):
                        verify_program(invalid)
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program(valid.replace('increment(&mut n, 5)', 'increment(&mut n, *n)'))
        both = """
            async fn pair(first: &mut Int, second: &Int) { yield; }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(10);
                let task = pair(&mut n, &n);
                drop(-> task);
            }
        """
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(both)
        discarded = valid[:valid.index('let h =')] + 'drop(-> task); print(n); }'
        self.assertEqual(self.run_c_oracle(compile_source(discarded)).stdout, '10\n')

    def test_async_worker_awaits_spawned_child_with_local_borrow(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(9); return *n; }
            async fn parent() -> Int {
                let mut local = 3;
                let t = edit(&mut local);
                let h = runtime::spawn(-> t);
                CHECK
                let result = h.await;
                let n = match result { Ok(v) => { v }, Err(_) => { 100 } };
                return n + local;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        valid = source.replace('CHECK', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '18\n')
        simulated_error = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(simulated_error).stdout, '103\n')
        void_child = (valid.replace('-> Int { yield; n.set(9); return *n; }', '{ yield; n.set(9); }', 1)
                      .replace('let result = h.await;\n                ', '')
                      .replace('match result { Ok(v) => { v }, Err(_) => { 100 } }',
                               'match h.await { Ok(()) => { 1 }, Err(_) => { 100 } }'))
        self.assertEqual(self.run_c_oracle(compile_source(void_child)).stdout, '10\n')
        renamed = valid.replace('let result = h.await;', 'let moved = <- h; let result = moved.await;')
        self.assertEqual(self.run_c_oracle(compile_source(renamed)).stdout, '18\n')
        with self.assertRaisesRegex(Error, 'déjà consommé'):
            verify_program(renamed.replace('let result = moved.await;', 'let result = h.await;'))


        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(local);'))
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(source.replace('CHECK', '').replace(
                'let result = h.await;', 'return 0;').replace(
                'let n = match result { Ok(v) => { v }, Err(_) => { 100 } };\n                return n + local;', ''))
        with self.assertRaisesRegex(Error, 'déjà consommé'):
            verify_program(valid.replace('let result = h.await;', 'let result = h.await; let again = h.await;'))

        self.run_c_oracle('#define main crust_sync_main\n' + code + r"""
#undef main
#include <assert.h>
static _Atomic int entered, finish;
static pthread_t caller;
static CrustTaskStep wait_for_caller(CrustTask *task) {
    (void)task;
    assert(!pthread_equal(caller, pthread_self()));
    atomic_store(&entered, 1);
    while (!atomic_load(&finish)) sched_yield();
    return TASK_STEP_RETURN;
}
static void extract(CrustTask *task, void *result) {
    (void)task;
    *(int *)result = 42;
}
static void release(CrustTask *task) { (void)task; }
int main(void) {
    CrustTask task;
    CrustAsyncExecution handle;
    CrustJoinResult result;
    const CrustTaskOps ops = {wait_for_caller, extract, release};
    task_init(&task, &ops);
    caller = pthread_self();
    task_async_start(&handle, &task);
    while (!atomic_load(&entered)) sched_yield();
    assert(!task_async_take(&handle, &result));
    atomic_store(&finish, 1);
    while (!task_async_take(&handle, &result)) sched_yield();
    assert(result.status == 0 && result.value == 42);
    return 0;
}
""")

    def test_async_match_resumes_the_selected_arm_and_joins_ownership(self):
        source = """
            async fn first() -> Int { yield; return 3; }
            async fn later() -> Int { yield; yield; return 5; }
            async fn parent() -> Int {
                let launch = first();
                let h = runtime::spawn(-> launch);
                let pending = later();
                let result = match h.await {
                    Ok(n) => { let saved = n; yield; saved + pending.await },
                    Err(_) => { yield; 90 + pending.await }
                };
                return result;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '8\n')
        simulated_error = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(simulated_error).stdout, '95\n')
        with self.assertRaisesRegex(Error, 'mêmes obligations de nettoyage'):
            verify_program(source.replace('90 + pending.await', '90'))
        with self.assertRaisesRegex(Error, 'déjà consommée'):
            verify_program(source.replace('return result;', 'return result + pending.await;'))

    def test_async_early_return_proves_all_handles_finished_on_that_path(self):
        source = """
            async fn set_value(n: &mut Int) -> Int { yield; n.set(7); return *n; }
            async fn parent() -> Int {
                let mut a = 1;
                let mut b = 2;
                let second_task = set_value(&mut b);
                let second = runtime::spawn(-> second_task);
                let first_task = set_value(&mut a);
                let first = runtime::spawn(-> first_task);
                let value = match first.await {
                    Ok(n) => { n },
                    Err(_) => {
                        let other = match second.await { Ok(n) => { n }, Err(_) => { 50 } };
                        return 100 + other + b;
                    }
                };
                let other = match second.await { Ok(n) => { n }, Err(_) => { 50 } };
                return value + other + b;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '21\n')
        # Parent, second_task, first_task: reject the third logical submission,
        # independently of how many native workers the scheduler reuses.
        anchor = 'static int task_default_submit(CrustTask *task) {'
        self.assertEqual(code.count(anchor), 1)
        failed_first = code.replace(anchor, r"""
static _Atomic int submissions;
static int task_default_submit(CrustTask *task) {
    if (atomic_fetch_add(&submissions, 1) + 1 == 3) return EAGAIN;
""", 1)
        self.assertEqual(self.run_c_oracle(failed_first).stdout, '114\n')
        escaped = source.replace('let other = match second.await { Ok(n) => { n }, Err(_) => { 50 } };',
                                 'let other = 0;', 1).replace('return 100 + other + b;', 'return 100 + other;')
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(escaped)

        statement = source.replace('let value = match first.await', 'match first.await')
        statement = statement.replace('Ok(n) => { n },\n                    Err', 'Ok(n) => { print(n); },\n                    Err', 1)
        statement = statement.replace('};\n                let other', '}\n                let other', 1)
        statement = statement.replace('return value + other + b;', 'return other + b;')
        self.assertEqual(self.run_c_oracle(compile_source(statement)).stdout, '7\n14\n')

    def test_async_if_preserves_condition_order_and_branch_reservations(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(9); return *n; }
            async fn parent(seed: Int) -> Int {
                let mut local = seed;
                let answer = if local < edit(&mut local).await {
                    yield;
                    if local == 9 { local = local + 1; }
                    local
                } else {
                    yield;
                    return 80 + local;
                };
                return answer;
            }
            fn main() {
                let yes = parent(4);
                let first = runtime::spawn(-> yes);
                match first.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
                let no = parent(12);
                let second = runtime::spawn(-> no);
                match second.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '10\n89\n')
        reserved = source.replace('let answer = if local < edit(&mut local).await {',
                                  'let child = edit(&mut local); let answer = if seed < 9 {')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(reserved)
        divergent = source.replace('let answer = if local < edit(&mut local).await {',
                                   'let child = edit(&mut local); let answer = if seed < 9 {').replace(
            'if local == 9 { local = local + 1; }', 'let output = child.await;').replace(
            '                    local\n', '                    output\n').replace('return 80 + local;', '80')
        with self.assertRaisesRegex(Error, 'mêmes obligations de nettoyage'):
            verify_program(divergent)

    def test_async_short_circuit_skips_suspending_right_operand(self):
        source = """
            async fn edit(n: &mut Int, value: Int) -> Int {
                yield;
                n.set(value);
                return *n;
            }
            async fn run(seed: Int) -> Int {
                let mut n = 0;
                if seed == 1 || (seed == 2 && edit(&mut n, 7).await == 7) {
                    yield;
                    return n + 10;
                }
                return n;
            }
            fn main() {
                let one = run(1);
                let a = runtime::spawn(-> one);
                match a.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
                let two = run(2);
                let b = runtime::spawn(-> two);
                match b.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
                let three = run(3);
                let c = runtime::spawn(-> three);
                match c.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '10\n17\n0\n')
        divergent = source.replace('if seed == 1 || (seed == 2 && edit(&mut n, 7).await == 7)',
                                   'let child = edit(&mut n, 7); if seed == 1 || child.await == 7')
        with self.assertRaisesRegex(Error, 'mêmes obligations de nettoyage'):
            verify_program(divergent)

    def test_async_loop_resumes_and_cleans_each_iteration(self):
        source = """
            async fn count(n: Int) -> Int { yield; return n; }
            async fn pending(n: &Int) { yield; print(*n); }
            async fn run() -> Int {
                let mut i = 0;
                let mut sum = 0;
                while count(i).await < 5 {
                    i = i + 1;
                    let unused = pending(&i);
                    yield;
                    if i == 2 { continue; }
                    if i == 4 { break; }
                    sum = sum + i;
                }
                let value = loop {
                    yield;
                    break count(sum + i).await;
                };
                i = 8;
                return value + i;
            }
            fn main() {
                let t = run();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        code = '#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '16\n')
        no_break = source.replace('if i == 4 { break; }', '')
        self.assertEqual(self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(no_break)).stdout,
                         '26\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('sum = sum + i;', 'i = 7;'))
        with self.assertRaisesRegex(Error, 'résultat attendu'):
            verify_program(source.replace('break count(sum + i).await;', 'break;'))
        carried = source.replace('while count(i).await < 5 {',
                                 'let child = pending(&i); while count(i).await < 5 {').replace(
            'if i == 2 { continue; }', 'if i == 2 { child.await; continue; }')
        # Use a separate local so the intended conflict is the back edge.
        carried = carried.replace('let child = pending(&i);', 'let frozen = 0; let child = pending(&frozen);')
        with self.assertRaisesRegex(Error, 'continue doit préserver'):
            verify_program(carried)

    def test_async_loop_exit_can_finish_a_worker_from_the_enclosing_scope(self):
        source = """
            async fn edit(n: &mut Int) { yield; n.set(7); }
            async fn run(flag: Int) -> Int {
                let mut n = 1;
                let t = edit(&mut n);
                let worker = runtime::spawn(-> t);
                loop {
                    if flag == 1 {
                        match worker.await { Ok(()) => {}, Err(_) => {} }
                        break;
                    }
                    yield;
                    match worker.await { Ok(()) => {}, Err(_) => {} }
                    break;
                }
                CHECK
                n = n + 1;
                return n;
            }
            fn main() {
                let a = run(1);
                let first = runtime::spawn(-> a);
                match first.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
                let b = run(0);
                let second = runtime::spawn(-> b);
                match second.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        valid = source.replace('CHECK', '')
        code = '#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '8\n8\n')
        valued = source.replace('loop {', 'let count = loop {', 1).replace('break;', 'break 1;')
        valued = valued.replace('}\n                CHECK', '};').replace('n + 1;', 'n + count;')
        self.assertEqual(self.run_c_oracle(compile_source(valued)).stdout, '8\n8\n')
        unmatched = valid.replace('yield;\n                    match worker.await { Ok(()) => {}, Err(_) => {} }',
                                  'yield;')
        with self.assertRaisesRegex(Error, 'sorties de boucle async'):
            verify_program(unmatched)
        zero_iterations = valid.replace('loop {', 'while flag == 1 {', 1)
        with self.assertRaisesRegex(Error, 'sorties de boucle async'):
            verify_program(zero_iterations)
        after = source.replace('CHECK', 'match worker.await { Ok(()) => {}, Err(_) => {} }')
        with self.assertRaisesRegex(Error, 'déjà consommé'):
            verify_program(after)
        premature = valid.replace('yield;\n                    match worker.await',
                                  'n = 9; match worker.await')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(premature)

    def test_async_iteration_waits_for_worker_before_reusing_local(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(*n + 1); return *n; }
            async fn run() -> Int {
                let mut i = 0;
                let mut total = 0;
                while i < 4 {
                    i = i + 1;
                    let mut local = i;
                    let task = edit(&mut local);
                    let worker = runtime::spawn(-> task);
                    yield;
                    BEFORE
                    let joined = worker.await;
                    match joined {
                        Ok(n) => { total = total + n + local; },
                        Err(_) => { return 99; }
                    }
                    if i == 2 { continue; }
                    if i == 3 { break; }
                }
                return total;
            }
            fn main() {
                let task = run();
                let h = runtime::spawn(-> task);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        valid = source.replace('BEFORE', '')
        self.assertEqual(self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(valid)).stdout,
                         '18\n')
        for early_exit in ('break;', 'continue;', 'return 0;'):
            with self.subTest(early_exit=early_exit):
                with self.assertRaisesRegex(Error, 'attente requise'):
                    verify_program(source.replace('BEFORE', f'if i == 1 {{ {early_exit} }}'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'local = 0;'))
        with self.assertRaisesRegex(Error, 'tâche.*déjà consommée'):
            verify_program(source.replace('BEFORE', 'let duplicate = runtime::spawn(-> task);'))

    def test_async_break_transfers_task_or_handle_and_joins_possible_loans(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(*n + 1); return *n; }
            async fn run(choice: Int) -> Int {
                let mut a = 10;
                let mut b = 20;
                let selected = loop {
                    yield;
                    if choice == 0 {
                        let task = edit(&mut a);
                        let worker = runtime::spawn(-> task);
                        break <- worker;
                    }
                    let task = edit(&mut b);
                    let worker = runtime::spawn(-> task);
                    break <- worker;
                };
                CHECK
                let result = match selected.await { Ok(n) => { n }, Err(_) => { 99 } };
                return result + a + b;
            }
            fn main() {
                let t = run(0);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
                let u = run(1);
                let j = runtime::spawn(-> u);
                match j.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '42\n52\n')
        inactive = valid.replace('let worker = runtime::spawn(-> task);', '').replace(
            'break <- worker;', 'break <- task;').replace(
            'match selected.await { Ok(n) => { n }, Err(_) => { 99 } }', 'selected.await')
        self.assertEqual(self.run_c_oracle(compile_source(inactive)).stdout, '42\n52\n')
        for target in ('a', 'b'):
            with self.subTest(target=target):
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('CHECK', f'print({target});'))
        escaping = valid.replace('let task = edit(&mut a);', 'let mut local = 10; let task = edit(&mut local);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaping)
        with self.assertRaisesRegex(Error, 'même type et le même mode'):
            verify_program(valid.replace('let worker = runtime::spawn(-> task);', '', 1)
                           .replace('break <- worker;', 'break 0;', 1))

    def test_async_scalar_handle_abandonment_is_rejected_and_legacy_drain_is_explicit(self):
        source = """
            async fn leaf(n: Int) { yield; print(n); }
            async fn parent() {
                let t = leaf(7);
                let worker = runtime::spawn(-> t);
                DROP
                print(8);
            }
            fn main() {
                let t = parent();
                let worker = runtime::spawn(-> t);
                drop(-> worker);
            }
        """
        # RT7 now forbids source-level abandonment, even without borrowed
        # captures. Keep the internal C drain oracle below as historical ABI
        # coverage, not as an accepted language operation.
        for cleanup in ('drop(-> worker);', ''):
            with self.subTest(cleanup=cleanup), self.assertRaisesRegex(Error, 'attente requise'):
                verify_program(source.replace('DROP', cleanup))
        valid = source.replace('DROP', 'match worker.await { Ok(()) => {}, Err(_) => {} }').replace(
            'drop(-> worker);', 'match worker.join() { Ok(()) => {}, Err(_) => {} }')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '7\n8\n')

        self.run_c_oracle('#define main crust_sync_main\n' + code + r"""
#undef main
#include <assert.h>
static _Atomic int entered, finish;
static int released;
static CrustTaskStep resume(CrustTask *task) {
    (void)task;
    atomic_store(&entered, 1);
    while (!atomic_load(&finish)) sched_yield();
    return TASK_STEP_RETURN;
}
static void extract(CrustTask *task, void *output) {
    (void)task;
    *(int *)output = 9;
}
static void release(CrustTask *task) { (void)task; ++released; }
static void abandon(CrustTask *task, CrustAbandonedTasks *registry) {
    CrustAsyncExecution handle;
    task_async_start(&handle, task);
    while (!atomic_load(&entered)) sched_yield();
    task_async_abandon(registry, &handle);
}
int main(void) {
    CrustTask task;
    CrustAbandonedExecution entry;
    CrustAbandonedTasks registry = {.entries = &entry, .capacity = 1};
    const CrustTaskOps ops = {resume, extract, release};
    task_init(&task, &ops);
    abandon(&task, &registry);
    assert(!released);
    atomic_store(&finish, 1);
    task_thread_drain(&registry);
    assert(released == 1 && !registry.count);
    return 0;
}
""")

    def test_async_shared_result_retains_only_returned_provenance(self):
        source = """
            async fn select(first: &Int, other: &Int) -> &Int {
                yield;
                print(*other);
                return first;
            }
            async fn run() -> Int {
                let mut a = 10;
                let mut b = 20;
                let child = select(&a, &b);
                let view = child.await;
                b = 30;
                CHECK
                let saved = *view;
                a = 40;
                return saved + a + b;
            }
            fn main() {
                let task = run();
                let h = runtime::spawn(-> task);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '20\n80\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'a = 99;'))
        with self.assertRaisesRegex(Error, 'paramètre partagé durable'):
            verify_program(valid.replace('return first;', 'let local = 7; return &local;'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('return first;', 'if *first == 0 { return other; } return first;'))

    def test_async_mutable_result_extends_exclusivity_until_its_last_use(self):
        source = """
            async fn lend(n: &mut Int) -> &mut Int { yield; return &mut *n; }
            async fn parent() -> Int {
                let mut n = 1;
                let mut view = lend(&mut n).await;
                CHECK
                yield;
                view.set(*view + 3);
                return n;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '4\n')
        for conflict in ('print(n);', 'n = 9;'):
            with self.subTest(conflict=conflict):
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('CHECK', conflict))
        # V4: the reference type grants writes to the target; `mut` on the
        # binding only controls reassignment of the reference itself.
        fixed_binding = valid.replace('let mut view', 'let view')
        verify_program(fixed_binding)
        self.assertEqual(self.run_c_oracle(compile_source(fixed_binding)).stdout, '4\n')
        with self.assertRaisesRegex(Error, 'paramètre mutable durable'):
            verify_program(valid.replace('return &mut *n;', 'let mut local = 0; return &mut local;'))
        shared = source.replace('-> &mut Int', '-> &Int').replace('return &mut *n;', 'return &*n;').replace(
            'let mut view', 'let view').replace('view.set(*view + 3);', 'print(*view);')
        self.assertEqual(self.run_c_oracle(compile_source(shared.replace('CHECK', ''))).stdout, '1\n1\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(shared.replace('CHECK', 'print(n);'))

    def test_async_subblock_borrow_results_end_at_usage_and_iteration_exits(self):
        source = """
            async fn lend(n: &mut Int) -> &mut Int { yield; return n; }
            async fn run() -> Int {
                let mut n = 1;
                let mut count = 0;
                let result = loop {
                    count = count + 1;
                    let mut view = lend(&mut n).await;
                    CHECK
                    if count == 1 {
                        view.set(7);
                        continue;
                    }
                    break *view;
                };
                let saved = if result == 7 {
                    let mut view = lend(&mut n).await;
                    view.set(*view + 2);
                    n = n + 1;
                    n
                } else { 100 };
                n = 8;
                return saved + n;
            }
            fn main() {
                let t = run();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(valid)).stdout,
                         '18\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'n = 99;'))
        with self.assertRaisesRegex(Error, 'variable inconnue'):
            verify_program(valid.replace('return saved + n;', 'return view;'))

    def test_async_relay_infers_returned_loan_through_multiple_awaits(self):
        source = """
            async fn leaf(n: &mut Int, side: &Int) -> &mut Int {
                yield;
                print(*side);
                return n;
            }
            async fn relay(side: &Int, target: &mut Int) -> &mut Int {
                let pending = leaf(target, side);
                return pending.await;
            }
            async fn outer(target: &mut Int, side: &Int) -> &mut Int {
                let mut result = relay(side, target).await;
                yield;
                return result;
            }
            async fn parent() -> Int {
                let mut a = 1;
                let mut b = 10;
                let mut view = outer(&mut a, &b).await;
                b = 20;
                CHECK
                view.set(7);
                return a + b;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '10\n27\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(a);'))
        with self.assertRaisesRegex(Error, 'paramètre mutable durable'):
            verify_program(valid.replace('let pending = leaf(target, side);',
                                         'let mut local = 0; let pending = leaf(&mut local, side);'))
        # AS7 now rejects an unbounded creation cycle first. Supply its
        # capacity to keep exercising the unresolved recursive-loan analysis.
        with self.assertRaisesRegex(Error, 'provenance récursive'):
            verify_program('#(directive, async_pool_sizes={relay:4})' +
                           valid.replace('let pending = leaf(target, side);',
                                         'let pending = relay(side, target);'))

    def test_async_recapture_of_result_keeps_target_and_parent_reserved(self):
        source = """
            async fn lend(n: &mut Int) -> &mut Int { yield; return n; }
            async fn edit(n: &mut Int) { yield; n.set(9); }
            async fn relay(n: &mut Int) -> &mut Int {
                let mut view = lend(n).await;
                return lend(view).await;
            }
            async fn parent() -> Int {
                let mut n = 1;
                let mut view = relay(&mut n).await;
                let child = edit(view);
                yield;
                CHECK
                child.await;
                return n;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '9\n')
        for use in ('print(n);', 'view.set(2);', 'let duplicate = edit(view);'):
            with self.subTest(use=use):
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('CHECK', use))
        discarded = valid.replace('child.await;', 'drop(-> child);')
        self.assertEqual(self.run_c_oracle(compile_source(discarded)).stdout, '1\n')
        resumed = valid.replace('child.await;', 'child.await; view.set(11);')
        self.assertEqual(self.run_c_oracle(compile_source(resumed)).stdout, '11\n')

    def test_async_handle_result_keeps_loan_before_and_inside_match(self):
        source = """
            async fn lend(n: &mut Int) -> &mut Int { yield; return n; }
            async fn parent() -> Int {
                let mut n = 1;
                let t = lend(&mut n);
                let h = runtime::spawn(-> t);
                let result = h.await;
                BEFORE
                let v = match result {
                    Ok(view) => {
                        INSIDE
                        yield;
                        view.set(8);
                        *view
                    },
                    Err(_) => {
                        n = 2;
                        90
                    }
                };
                return v + n;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        valid = source.replace('BEFORE', '').replace('INSIDE', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '16\n')
        for marker in ('BEFORE', 'INSIDE'):
            with self.subTest(marker=marker):
                invalid = source.replace(marker, 'n = 3;').replace('BEFORE', '').replace('INSIDE', '')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(invalid)
        direct = valid.replace('let result = h.await;', '').replace('match result', 'match h.await')
        self.assertEqual(self.run_c_oracle(compile_source(direct)).stdout, '16\n')
        failed = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed).stdout, '92\n')
        shared = valid.replace('n: &mut Int) -> &mut Int', 'n: &Int) -> &Int').replace(
            'lend(&mut n)', 'lend(&n)').replace('view.set(8);', '')
        self.assertEqual(self.run_c_oracle(compile_source(shared)).stdout, '2\n')

    def test_sync_join_borrow_result_protects_pool_cell(self):
        source = """
            async fn lend(extra: Int, n: &mut Int) -> &mut Int { yield; return n; }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(1);
                let t = lend(5, &mut n);
                let h = runtime::spawn(-> t);
                let result = h.join();
                BEFORE
                match result {
                    Ok(view) => {
                        INSIDE
                        view.set(8);
                        print(*view);
                    },
                    Err(_) => { n.set(2); }
                }
                print(n);
                drop(-> n);
            }
        """
        valid = source.replace('BEFORE', '').replace('INSIDE', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '8\n8\n')
        direct = valid.replace('let result = h.join();', '').replace('match result', 'match h.join()')
        self.assertEqual(self.run_c_oracle(compile_source(direct)).stdout, '8\n8\n')
        discarded = valid[:valid.index('match result')] + 'drop(-> result); n.set(3); print(n); }'
        self.assertEqual(self.run_c_oracle(compile_source(discarded)).stdout, '3\n')

        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, runner, pointer) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '2\n')
        for marker in ('BEFORE', 'INSIDE'):
            with self.subTest(marker=marker):
                invalid = source.replace(marker, 'print(n);').replace('BEFORE', '').replace('INSIDE', '')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(invalid)
        with self.assertRaisesRegex(Error, 'emprunt'):
            verify_program(source.replace('BEFORE', 'drop(-> n);').replace('INSIDE', ''))
        shared = valid.replace('n: &mut Int) -> &mut Int', 'n: &Int) -> &Int').replace(
            'lend(5, &mut n)', 'lend(5, &n)').replace('view.set(8);', '')
        self.assertEqual(self.run_c_oracle(compile_source(shared)).stdout, '1\n1\n')

    def test_sync_join_shared_reborrow_preserves_exclusive_origin(self):
        source = """
            async fn lend(n: &mut Int) -> &Int { yield; return &*n; }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(1);
                PARENT
                let t = lend(ARG);
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => {
                        CHECK
                        print(*view);
                        AFTER
                    },
                    Err(_) => {}
                }
                print(n);
            }
        """
        for parent, argument, access in (('', '&mut n', 'print(n);'),
                                         ('let writer = &mut n;', 'writer', 'print(*writer);')):
            with self.subTest(argument=argument):
                template = source.replace('PARENT', parent).replace('ARG', argument)
                valid = template.replace('CHECK', '').replace('AFTER', access)
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '1\n1\n1\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(template.replace('CHECK', access).replace('AFTER', ''))
                with self.assertRaisesRegex(Error, 'emprunt en lecture'):
                    verify_program(template.replace('CHECK', 'view.set(2);').replace('AFTER', ''))

    def test_sync_recapture_carries_join_loan_through_another_worker(self):
        source = """
            async fn share(n: &mut Int) -> &Int { yield; return &*n; }
            async fn relay(n: &Int) -> &Int { yield; return n; }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(4);
                let t = share(&mut n);
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => {
                        let child = relay(view);
                        BEFORE
                        let j = runtime::spawn(-> child);
                        match j.join() {
                            Ok(result) => { INSIDE print(*result); },
                            Err(_) => {}
                        }
                    },
                    Err(_) => {}
                }
                n.set(5);
                print(n);
            }
        """
        valid = source.replace('BEFORE', '').replace('INSIDE', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '4\n5\n')
        for marker in ('BEFORE', 'INSIDE'):
            with self.subTest(marker=marker):
                invalid = source.replace(marker, 'print(n);').replace('BEFORE', '').replace('INSIDE', '')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(invalid)
        start = source.index('let j =')
        end = source.index('                    },\n                    Err', start)
        inactive = source[:start] + source[end:]
        inactive = inactive.replace('BEFORE', 'print(n);')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(inactive)

    def test_sync_contract_relays_exclusive_origin_of_joined_reference(self):
        source = """
            async fn lend(n: &mut Int) -> &Int { yield; return &*n; }
            fn joined(n: &mut Int) -> &Int {
                let t = lend(n);
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => { return view; },
                    Err(_) => { return &*n; }
                }
            }
            fn relay(n: &mut Int) -> &Int { return joined(n); }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(3);
                let writer = &mut n;
                let view = relay(writer);
                CHECK
                print(*view);
                print(*writer);
            }
        """
        valid = source.replace('CHECK', '')
        compiler = verify_program(valid)
        contract = compiler.function_contracts['relay']
        targets = contract.result.describe(contract.parameters)['reference_targets']
        self.assertIn({'kind': 'exclusive_join_parameter', 'parameter': 'n'}, targets)
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '3\n3\n')
        for use in ('print(n);', 'print(*writer);'):
            with self.subTest(use=use):
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('CHECK', use))
        escaped = valid.replace('let t = lend(n);',
                                'let mut p = pool<Int>(1); let mut local = new(p) Int(0); let t = lend(&mut local);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaped)

    def test_sync_function_returns_inactive_task_with_capture_contract(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(7); return *n; }
            fn prepare(n: &mut Int, yes: Int) -> <- edit {
                if yes == 1 {
                    let first = edit(n);
                    return <- first;
                }
                let fallback = edit(n);
                <- fallback
            }
            fn relay(n: &mut Int) -> <- edit {
                let task = prepare(n, 1);
                return <- task;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(4);
                let task = relay(&mut n);
                CHECK
                let h = runtime::spawn(-> task);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
                print(n);
            }
        """
        valid = source.replace('CHECK', '')
        summary = verify_program(valid).function_contracts['relay'].result
        self.assertEqual((summary.mode, summary.typ), ('task', 'edit'))
        self.assertEqual(summary.borrowed_fields[0][0], 'mut.0')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '7\n7\n')
        self.assertEqual(self.run_c_oracle(compile_source(valid.replace('prepare(n, 1)', 'prepare(n, 0)'))).stdout,
                         '7\n7\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(n);'))
        escaped = valid.replace('let first = edit(n);',
                                'let mut local_pool = pool<Int>(1); let mut local = new(local_pool) Int(0); '
                                'let first = edit(&mut local);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaped)

    def test_returned_task_keeps_pool_of_transferred_capture(self):
        source = """
            async fn work(n: -> Int) -> Int { yield; return *n; }
            fn prepare(n: -> Int) -> <- work {
                let t = work(-> n);
                return <- t;
            }
            fn allocate(p: &mut Pool<Int>) -> <- work {
                let n = new(p) Int(4);
                let t = prepare(-> n);
                <- t
            }
            fn main() {
                let mut p = pool<Int>(1);
                let task = allocate(&mut p);
                CHECK
                let h = runtime::spawn(-> task);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
                let reused = new(p) Int(8);
                print(reused);
            }
        """
        valid = source.replace('CHECK', '')
        compiler = verify_program(valid)
        for name, expected in (('prepare', 'allocation_parameter'), ('allocate', 'source_parameter')):
            self.assertEqual({source.kind for source in compiler.function_contracts[name].result.task_sources},
                             {expected})
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '4\n8\n')
        discarded = valid.replace('let h = runtime::spawn(-> task);', 'drop(-> task);').replace(
            'match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }', '')
        self.assertEqual(self.run_c_oracle(compile_source(discarded)).stdout, '8\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'p.reset();'), allow_legacy_reset=True)
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(valid.replace('match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }',
                                         'drop(-> h);'))
        escaped = valid.replace('let n = new(p) Int(4);',
                                'let mut local = pool<Int>(1); let n = new(local) Int(4);')
        with self.assertRaisesRegex(Error, 'pool de capture ne survit'):
            verify_program(escaped)

    def test_sync_function_returns_execution_with_capture_contract(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(7); return *n; }
            fn launch(n: &mut Int) -> <- Execution<edit> {
                let t = edit(n);
                let h = runtime::spawn(-> t);
                return <- h;
            }
            fn relay(n: &mut Int) -> <- Execution<edit> {
                let h = launch(n);
                <- h
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(4);
                let h = relay(&mut n);
                CHECK
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
                print(n);
            }
        """
        valid = source.replace('CHECK', '')
        summary = verify_program(valid).function_contracts['relay'].result
        self.assertEqual((summary.mode, summary.typ), ('execution', 'edit'))
        self.assertEqual(summary.borrowed_fields[0][0], 'mut.0')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '7\n7\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, runner, pointer) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '999\n4\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(n);'))
        owned = """
            async fn work(n: -> Int) -> Int { yield; return *n; }
            fn launch(p: &mut Pool<Int>) -> <- Execution<work> {
                let n = new(p) Int(4);
                let task = work(-> n);
                let worker = runtime::spawn(-> task);
                return <- worker;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let worker = launch(&mut p);
                match worker.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
                let reused = new(p) Int(8);
                print(reused);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(owned)).stdout, '4\n8\n')
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(owned.replace('match worker.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }',
                                         'drop(-> worker);'))
        escaped = valid.replace('let t = edit(n);',
                                'let mut local_pool = pool<Int>(1); let mut local = new(local_pool) Int(0); '
                                'let t = edit(&mut local);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaped)

    def test_sync_parameters_consume_task_and_execution_transfers(self):
        source = """
            async fn work(n: Int) -> Int { yield; return n; }
            async fn other(n: Int) -> Int { yield; return n; }
            fn launch(t: -> work) -> <- Execution<work> {
                let h = runtime::spawn(-> t);
                return <- h;
            }
            fn finish(h: -> Execution<work>) -> Int {
                match h.join() { Ok(n) => { return n; }, Err(_) => { return 99; } }
            }
            fn discard(t: -> work) { drop(-> t); }
            fn main() {
                let pending = work(1);
                discard(-> pending);
                let t = work(7);
                let h = launch(-> t);
                BEFORE
                let x = finish(-> h);
                AFTER
                print(x);
            }
        """
        valid = source.replace('BEFORE', '').replace('AFTER', '')
        self.assertEqual(self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(valid)).stdout,
                         '7\n')
        with self.assertRaisesRegex(Error, 'transfert -> requis'):
            verify_program(valid.replace('launch(-> t)', 'launch(t)'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('BEFORE', 'drop(-> t);').replace('AFTER', ''))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('AFTER', 'drop(-> h);').replace('BEFORE', ''))
        with self.assertRaisesRegex(Error, 'task de work'):
            verify_program(valid.replace('let t = work(7);', 'let t = other(7);'))

    def test_transferred_async_parameters_retain_owned_capture_sources(self):
        source = """
            async fn work(n: -> Int) -> Int { yield; return *n; }
            fn launch(t: -> work) -> <- Execution<work> {
                let h = runtime::spawn(-> t);
                return <- h;
            }
            fn relay(h: -> Execution<work>) -> <- Execution<work> { return <- h; }
            fn finish(h: -> Execution<work>) -> Int {
                match h.join() { Ok(x) => { return x; }, Err(_) => { return 999; } }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                let t = work(-> n);
                let h = launch(-> t);
                let moved = relay(-> h);
                CHECK
                let x = finish(-> moved);
                print(x);
                let reused = new(p) Int(8);
                print(reused);
            }
        """
        valid = source.replace('CHECK', '')
        compiler = verify_program(valid)
        for name in ('launch', 'relay'):
            self.assertEqual({origin.kind for origin in compiler.function_contracts[name].result.task_sources},
                             {'task_parameter'})
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '7\n8\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'p.reset();'), allow_legacy_reset=True)
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(valid.replace('let x = finish(-> moved);', 'drop(-> moved); let x = 0;'))
        reset_alias = valid.replace('fn finish(h: -> Execution<work>) -> Int {',
                                    'fn finish(h: -> Execution<work>, p: &mut Pool<Int>) -> Int { p.reset();').replace(
            'finish(-> moved)', 'finish(-> moved, &mut p)')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(reset_alias, allow_legacy_reset=True)

    def test_transferred_async_parameters_preserve_borrow_through_join_return(self):
        source = """
            async fn work(n: &mut Int) -> &Int { yield; n.set(7); return &*n; }
            fn launch(t: -> work) -> <- Execution<work> {
                let h = runtime::spawn(-> t);
                return <- h;
            }
            fn relay(h: -> Execution<work>) -> <- Execution<work> { return <- h; }
            fn finish(h: -> Execution<work>, fallback: &Int) -> &Int {
                match h.join() { Ok(v) => { return v; }, Err(_) => { return fallback; } }
            }
            fn finish_again(h: -> Execution<work>, fallback: &Int) -> &Int {
                return finish(-> h, fallback);
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut n = new(p) Int(4);
                let fallback = new(q) Int(999);
                let t = work(&mut n);
                let h = launch(-> t);
                let moved = relay(-> h);
                BEFORE
                let v = finish_again(-> moved, &fallback);
                DURING
                print(v);
                n.set(8);
                print(n);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        contracts = verify_program(valid).function_contracts
        for name in ('launch', 'relay'):
            origins = dict(contracts[name].result.borrowed_fields)['mut.0']
            self.assertEqual({(target.kind, target.parameter, target.field) for target in origins},
                             {('task_capture_parameter', 0, '0')})
        for name in ('finish', 'finish_again'):
            self.assertEqual({target.kind for target in contracts[name].result.reference_targets},
                             {'task_capture_parameter', 'parameter'})
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '7\n8\n')
        for location in ('BEFORE', 'DURING'):
            invalid = source.replace(location, 'print(n);').replace('BEFORE', '').replace('DURING', '')
            with self.subTest(location=location), self.assertRaisesRegex(Error, 'emprunt'):
                verify_program(invalid)
        direct = valid.replace('finish_again(-> moved, &fallback)', 'finish(-> moved, &fallback)')
        alias = direct.replace('finish(-> moved, &fallback)', 'finish(-> moved, &n)').replace(
            'let fallback = new(q) Int(999);', '')
        reverse_alias = alias.replace('h: -> Execution<work>, fallback: &Int',
                                      'fallback: &Int, h: -> Execution<work>').replace(
            'finish(-> h, fallback)', 'finish(fallback, -> h)').replace('finish(-> moved, &n)', 'finish(&n, -> moved)')
        for invalid in (alias, reverse_alias):
            with self.assertRaisesRegex(Error, 'emprunt'):
                verify_program(invalid)
        reset = direct.replace(
            'fn finish(h: -> Execution<work>, fallback: &Int) -> &Int {',
            'fn finish(h: -> Execution<work>, fallback: &Int, p: &mut Pool<Int>) -> &Int { p.reset();')
        reset = reset.replace('finish(-> h, fallback)', 'finish(-> h, fallback, p)').replace(
            'fn finish_again(h: -> Execution<work>, fallback: &Int) -> &Int {',
            'fn finish_again(h: -> Execution<work>, fallback: &Int, p: &mut Pool<Int>) -> &Int {').replace(
            'finish(-> moved, &fallback)', 'finish(-> moved, &fallback, &mut p)')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(reset, allow_legacy_reset=True)

    def test_async_local_int_keeps_its_address_across_child_suspension(self):
        source = """
            async fn increment(n: &mut Int) { yield; n.set(*n + 1); }
            async fn observe(n: &Int) -> Int { yield; return *n; }
            async fn parent(seed: Int) -> Int {
                let mut local = seed;
                let child = increment(&mut local);
                yield;
                EXCLUSIVE
                child.await;
                let left = observe(&local);
                let right = observe(&local);
                let before = local;
                let first = left.await;
                SHARED
                let second = right.await;
                local = local + 1;
                return before + first + second + local;
            }
            fn main() {
                let t = parent(10);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('EXCLUSIVE', '').replace('SHARED', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '45\n')
        for position, operation in (('EXCLUSIVE', 'print(local);'), ('SHARED', 'local = 9;')):
            with self.subTest(position=position):
                invalid = source.replace(position, operation).replace('EXCLUSIVE', '').replace('SHARED', '')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(invalid)
        with self.assertRaisesRegex(Error, 'mode incompatible'):
            verify_program(valid.replace('let mut local', 'let local').replace('local = local + 1;', ''))
        with self.assertRaisesRegex(Error, 'mode incompatible'):
            verify_program(valid.replace('increment(&mut local)', 'increment(&mut seed)'))

    def test_nested_task_captures_hold_loans_and_transfer_cleanup(self):
        source = """
            async fn amount() -> Int { yield; return 2; }
            async fn leaf(delta: Int, n: &mut Int) -> Int {
                yield;
                n.set(*n + delta);
                return *n;
            }
            async fn consume(n: -> Int) -> Int { yield; return *n; }
            async fn relay(mut n: -> Int) -> Int {
                let child = leaf(amount().await, &mut n);
                BEFORE
                let renamed = <- child;
                yield;
                let value = renamed.await;
                let moved = consume(-> n);
                MOVED
                return value + moved.await;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(10);
                let t = relay(-> n);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let reused = new(p) Int(7);
                print(reused);
            }
        """
        valid = source.replace('BEFORE', '').replace('MOVED', '')
        run = self.run_c_oracle(compile_source(valid))
        self.assertEqual(run.stdout, '24\n7\n')
        self.assertEqual(run.stderr.count('destroy n=12\n'), 1)
        for conflict in ('print(*n);', 'drop(-> n);', 'let second = leaf(2, &mut n);'):
            with self.subTest(conflict=conflict):
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('BEFORE', conflict).replace('MOVED', ''))
        with self.assertRaisesRegex(Error, 'plus utilisable après drop ou transfert'):
            verify_program(source.replace('BEFORE', '').replace('MOVED', 'print(*n);'))
        conflicting_await = (valid.replace('amount()', 'amount(input: &Int)', 1)
                             .replace('leaf(delta: Int, n: &mut Int)', 'leaf(n: &mut Int, delta: Int)')
                             .replace('leaf(amount().await, &mut n)', 'leaf(&mut n, amount(&n).await)'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conflicting_await)
        with self.assertRaisesRegex(Error, 'plus utilisable après drop ou transfert'):
            verify_program(valid.replace('let moved = consume(-> n);', 'n.set(consume(-> n).await);'))
        discarded = valid.replace('let value = renamed.await;', 'drop(-> renamed); let value = *n;')
        run = self.run_c_oracle(compile_source(discarded))
        self.assertEqual(run.stdout, '20\n7\n')
        self.assertEqual(run.stderr.count('destroy n=10\n'), 1)

    def test_worker_drop_and_concurrent_pool_reuse(self):
        source = """
            async fn release(n: -> Int) { drop(-> n); yield; print(1); }
            fn main() {
                let mut p = pool<Int>(2);
                let n = new(p) Int(10);
                let t = release(-> n);
                let h = runtime::spawn(-> t);
                let other = new(p) Int(20);
                print(other);
                drop(-> other);
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
            }
        """
        code = compile_source(source)
        run = self.run_c_oracle(code)
        self.assertEqual(sorted(run.stdout.splitlines()), ['1', '20'])
        self.assertEqual(run.stderr.count('destroy n=10\n'), 1)
        for use in ('drop(-> n);', 'print(*n);'):
            with self.assertRaisesRegex(Error, 'plus utilisable après drop'):
                verify_program(source.replace('yield; print(1);', f'yield; {use}'))

        self.run_c_oracle('#define main crust_sync_main\n' + code + r"""
#undef main
#include <assert.h>
static _Atomic int ready, start;
static void *cycle_slots(void *pointer) {
    Source *pool = pointer;
    atomic_fetch_add(&ready, 1);
    while (!atomic_load(&start)) sched_yield();
    for (int value = 0; value < 4000; ++value) {
        Cell *cell = cell_try_new(pool, value, NULL);
        assert(cell && cell->value == value);
        cell_drop(cell);
    }
    return NULL;
}
int main(void) {
    Source pool = source_pool(4);
    pthread_t workers[4];
    for (size_t i = 0; i < 4; ++i)
        assert(pthread_create(&workers[i], NULL, cycle_slots, &pool) == 0);
    while (atomic_load(&ready) != 4) sched_yield();
    atomic_store(&start, 1);
    for (size_t i = 0; i < 4; ++i) assert(pthread_join(workers[i], NULL) == 0);
    assert(pool.live == 0 && pool.used == 0 && !pool.tail && !pool.free_head);
    source_close(&pool);
    return 0;
}
""")

    def test_async_await_transfers_allocation_without_releasing_its_slot(self):
        source = """
            async fn relay(n: -> Int) -> <- Int { yield; return <- n; }
            async fn chain(n: -> Int) -> <- Int {
                let task = relay(-> n);
                let received = task.await;
                return <- received;
            }
            async fn read(n: &Int) -> Int { yield; return *n; }
            async fn worker(n: -> Int) -> Int {
                {
                    let mut value = chain(-> n).await;
                    let borrowed = read(&value);
                    CHECK
                    let old = borrowed.await;
                    yield;
                    value.set(old + 6);
                    return *value;
                }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(1);
                let t = worker(-> n);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
                let next = new(p) Int(2);
                print(next);
            }
        """
        valid = source.replace('CHECK', '')
        code = '#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(valid)
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '7\n2\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy n=7', 'destroy next=2'])
        block_exit = valid.replace('return *value;\n                }', 'print(*value); } return 8;')
        for program in (block_exit, block_exit.replace('print(*value);', 'print(*value); drop(-> value);')):
            finished = self.run_c_oracle(compile_source(program))
            self.assertEqual(finished.stdout, '7\n8\n2\n')
            self.assertEqual(finished.stderr.count('destroy n=7\n'), 1)
        self.run_c_oracle('#define main crust_sync_main\n' + code + r'''
#undef main
#include <assert.h>
int main(void) {
    crust_task_context_init();
    Source pool = source_pool(1);
    Cell *original = cell_new(&pool, 31, "original");
    CrustTask *task = crust_async_chain_create(original);
    while (task_poll(task) == TASK_SUSPENDED) {}
    Cell *result = NULL;
    assert(task_take(task, &result));
    assert(result == original && result->value == 31);
    assert(!cell_try_new(&pool, 0, "premature"));
    cell_drop(result);
    Cell *reused = cell_new(&pool, 32, "reused");
    assert(reused == original);
    cell_drop(reused);
    crust_task_context_close();
    source_close(&pool);
    return 0;
}
''')
        for invalid, diagnostic in (
            (valid.replace('return <- n;', 'return *n;'), 'transfert explicite'),
            (source.replace('CHECK', 'drop(-> value);'), 'emprunt actif'),
            (valid.replace('return <- received;', 'drop(-> received); return <- n;'), 'plus utilisable'),
            (valid.replace('let received = task.await;', 'task.await;'), 'résultat transféré'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_async_worker_transfers_owned_result_into_ok_arm(self):
        source = """
            async fn work(mut n: -> Int) -> <- Int {
                yield;
                n.set(7);
                return <- n;
            }
            async fn parent(n: -> Int) -> Int {
                let task = work(-> n);
                let handle = runtime::spawn(-> task);
                match handle.await {
                    Ok(value) => { yield; return *value; },
                    Err(_) => { return 99; }
                }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(1);
                let t = parent(-> n);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
                let next = new(p) Int(2);
                print(next);
            }
        """
        code = compile_source(source)
        normal = self.run_c_oracle(code)
        self.assertEqual(normal.stdout, '7\n2\n')
        self.assertEqual(normal.stderr.count('destroy n=7\n'), 1)
        failed = inject_submission_failure(code)
        failed_run = self.run_c_oracle(failed)
        self.assertEqual(failed_run.stdout, '99\n2\n')
        self.assertEqual(failed_run.stderr.count('destroy n=1\n'), 1)
        ignored = source.replace('Ok(value) => { yield; return *value; }', 'Ok(_) => { yield; return 8; }')
        with self.assertRaisesRegex(Error, 'motif _'):
            compile_source(ignored)
        explicit = ignored.replace('Ok(_) => { yield;', 'Ok(value) => { drop(-> value); yield;')
        ignored_run = self.run_c_oracle(compile_source(explicit))
        self.assertEqual(ignored_run.stdout, '8\n2\n')
        self.assertEqual(ignored_run.stderr.count('destroy n=7\n'), 1)
        valued = source.replace('match handle.await {', 'let code = match handle.await {').replace(
            'yield; return *value;', 'yield; *value').replace('return 99; }\n                }',
                                                            '99 }\n                }; return code;')
        self.assertEqual(self.run_c_oracle(compile_source(valued)).stdout, '7\n2\n')
        named = source.replace('match handle.await {', 'let result = handle.await; yield; match result {')
        self.assertEqual(self.run_c_oracle(compile_source(named)).stdout, '7\n2\n')
        start, end = named.index('match result {'), named.index('            fn main()')
        unused = named[:start] + 'return 8;\n}\n' + named[end:]
        with self.assertRaisesRegex(Error, 'sans usage explicite'):
            compile_source(unused)
        for finish in ('drop(-> result); return 8;',):
            discarded = named[:start] + finish + '\n}\n' + named[end:]
            discarded_run = self.run_c_oracle(compile_source(discarded))
            self.assertEqual(discarded_run.stdout, '8\n2\n')
            self.assertEqual(discarded_run.stderr.count('destroy n=7\n'), 1)
        for invalid, diagnostic in (
            (named.replace('match result {', 'drop(-> result); match result {'), 'déjà consommé'),
            (source.replace('match handle.await {', 'drop(-> handle); match handle.await {'),
             'attente requise'),
            (source.replace('yield; return *value;', 'drop(-> value); yield; return *value;'),
             'plus utilisable'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_blocking_join_transfers_and_cleans_owned_result(self):
        source = """
            async fn work(mut n: -> Int) -> <- Int { yield; n.set(7); return <- n; }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(1);
                let t = work(-> n);
                let h = runtime::spawn(-> t);
                let result = h.join();
                CHECK
                match result { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                let next = new(p) Int(2);
                print(next);
            }
        """
        valid = source.replace('CHECK', '')
        code = compile_source(valid)
        success = self.run_c_oracle(code)
        self.assertEqual(success.stdout, '7\n2\n')
        self.assertEqual(success.stderr.count('destroy n=7\n'), 1)
        self.run_c_oracle('#define main crust_sync_main\n' + code + r'''
#undef main
#include <assert.h>
int main(void) {
    crust_task_context_init();
    Source pool = source_pool(1);
    Cell *original = cell_new(&pool, 1, "original");
    CrustExecution execution;
    assert(task_thread_start(&execution, crust_async_work_create(original)) == 0);
    CrustJoinResult result = task_join_allocation(&execution);
    assert(result.status == 0 && result.allocation == original && original->value == 7);
    assert(!cell_try_new(&pool, 0, "premature"));
    cell_drop(result.allocation);
    Cell *reused = cell_new(&pool, 2, "reused");
    assert(reused == original);
    cell_drop(reused);
    crust_task_context_close();
    source_close(&pool);
    return 0;
}
''')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN', 1)
        failure = self.run_c_oracle(failed)
        self.assertEqual(failure.stdout, '99\n2\n')
        self.assertEqual(failure.stderr.count('destroy n=1\n'), 1)
        direct = valid.replace('let result = h.join();', '').replace('match result', 'match h.join()')
        ignored = direct.replace('Ok(value) => { print(value); }', 'Ok(_) => {}')
        discarded = valid.replace('match result { Ok(value) => { print(value); }, Err(_) => { print(99); } }',
                                  'drop(-> result);')
        with self.assertRaisesRegex(Error, 'motif _'):
            compile_source(ignored)
        for program, output in ((direct, '7\n2\n'), (discarded, '2\n')):
            run = self.run_c_oracle(compile_source(program))
            self.assertEqual(run.stdout, output)
            self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        implicit = discarded.replace('drop(-> result);', '}').replace('let result = h.join();', '{ h ->; let result = h.join();')
        with self.assertRaisesRegex(Error, 'sans usage explicite'):
            compile_source(implicit)
        via_function = source.replace('fn main() {', """
            fn release(value: -> Int) { print(value); drop(-> value); }
            fn finish(h: -> Execution<work>) {
                match h.join() { Ok(value) => { release(-> value); }, Err(_) => { print(99); } }
            }
            fn main() {
        """, 1)
        via_function = via_function.replace('let result = h.join();\n                CHECK\n'
                                           '                match result { Ok(value) => { print(value); }, Err(_) => { print(99); } }',
                                           'finish(-> h);')
        self.assertEqual(self.run_c_oracle(compile_source(via_function)).stdout, '7\n2\n')
        two_pools = valid.replace('work(mut n: -> Int) -> <- Int { yield; n.set(7); return <- n; }',
                                  'work(flag: Int, mut n: -> Int, other: -> Int) -> <- Int { '
                                  'yield; if flag == 1 { n.set(7); return <- n; } return <- other; }')
        two_pools = two_pools.replace('let t = work(-> n);', 'let mut q = pool<Int>(1); '
                                      'let other = new(q) Int(8); let t = work(FLAG, -> n, -> other);')
        for flag, expected in ((0, '8\n2\n'), (1, '7\n2\n')):
            self.assertEqual(self.run_c_oracle(compile_source(two_pools.replace('FLAG', str(flag)))).stdout,
                             expected)
        for line, diagnostic in (
            ('let copied = result; drop(-> copied);', 'ne peut pas être copié'),
            ('drop(-> result);', 'plus utilisable'),
        ):
            with self.subTest(line=line), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('CHECK', line))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'p.reset();'), allow_legacy_reset=True)

    def test_sync_contract_returns_allocation_extracted_from_join(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn start(n: -> Int) -> <- Execution<work> {
                let t = work(-> n);
                let h = runtime::spawn(-> t);
                return <- h;
            }
            fn collect(h: -> Execution<work>, fallback: -> Int) -> <- Int {
                match h.join() { Ok(n) => { return <- n; }, Err(_) => { return <- fallback; } }
            }
            fn relay(n: -> Int, fallback: -> Int) -> <- Int {
                let h = start(-> n);
                let result = collect(-> h, -> fallback);
                return <- result;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let n = new(p) Int(7);
                let other = new(q) Int(99);
                let result = relay(-> n, -> other);
                print(result);
                drop(-> result);
                let next = new(p) Int(2);
                let again = new(q) Int(3);
                print(next);
                print(again);
            }
        """
        summaries = verify_program(source).function_contracts
        self.assertEqual({(item.kind, item.parameter) for item in summaries['collect'].result.candidates},
                         {('task_capture', 0), ('parameter', 1)})
        self.assertEqual({(item.kind, item.parameter) for item in summaries['relay'].result.candidates},
                         {('parameter', 0), ('parameter', 1)})
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '7\n2\n3\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n2\n3\n')
        direct = source.replace('let h = start(-> n);', 'let t = work(-> n); let h = runtime::spawn(-> t);')
        self.assertEqual(self.run_c_oracle(compile_source(direct)).stdout, '7\n2\n3\n')
        fresh = source.replace('fn start(n: -> Int) -> <- Execution<work> {',
                               'fn start(p: &mut Pool<Int>) -> <- Execution<work> { let n = new(p) Int(7);')
        fresh = fresh.replace('fn relay(n: -> Int,', 'fn relay(p: &mut Pool<Int>,').replace(
            'start(-> n)', 'start(p)')
        fresh = fresh.replace('let n = new(p) Int(7);\n                let other', 'let other').replace(
            'relay(-> n, -> other)', 'relay(&mut p, -> other)')
        self.assertEqual(self.run_c_oracle(compile_source(fresh)).stdout, '7\n2\n3\n')
        pool_drop = """
            async fn work(n: -> Int) -> <- Int { return <- n; }
            fn release(h: -> Execution<work>, pool: &mut Pool<Int>) {
                match h.join() { Ok(value) => { pool.drop(-> value); }, Err(_) => {} }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let n = new(p) Int(7);
                let t = work(-> n);
                let h = runtime::spawn(-> t);
                release(-> h, &mut p);
                let next = new(p) Int(2);
                print(next);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(pool_drop)).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'source de stockage d’origine'):
            verify_program(pool_drop.replace('release(-> h, &mut p);', 'release(-> h, &mut q);'))
        local = source.replace('fn start(n: -> Int) -> <- Execution<work> {',
                               'fn start() -> <- Execution<work> { let mut local = pool<Int>(1); let n = new(local) Int(7);')
        local = local.replace('start(-> n)', 'start()')
        with self.assertRaisesRegex(Error, 'pool de capture ne survit'):
            verify_program(local)

    def test_owned_join_result_moves_across_names_and_block_scopes(self):
        task = 'async fn work(n: -> Int) -> <- Int { yield; return <- n; }'
        body = """
            let t = work(-> n);
            let h = runtime::spawn(-> t);
            let result = {
                h ->;
                let original = WAIT;
                let moved = <- original;
                CHECK
                <- moved
            };
            { result ->; <- result; }
            match result { Ok(value) => { print(READ); }, Err(_) => { print(99); } }
        """
        entry = """
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                RUN
                let next = new(p) Int(2);
                print(next);
            }
        """
        caller = ('let task = parent(-> n); let h = runtime::spawn(-> task); '
                  'match h.join() { Ok(()) => {}, Err(_) => { print(999); } }')
        programs = (
            task + entry.replace('RUN', body.replace('WAIT', 'h.join()').replace('READ', 'value')),
            task + 'async fn parent(n: -> Int) {' + body.replace('WAIT', 'h.await').replace('READ', '*value')
            + '}' + entry.replace('RUN', caller),
        )
        loop = programs[1].replace('let result = {', 'let result = loop {').replace(
            '<- moved\n', 'break <- moved;\n').replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(loop)).stdout, '7\n2\n')
        for mode, program in zip(('sync', 'async'), programs, strict=True):
            with self.subTest(mode=mode):
                valid = program.replace('CHECK', '')
                run = self.run_c_oracle(compile_source(valid))
                self.assertEqual(run.stdout, '7\n2\n')
                self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
                with self.assertRaisesRegex(Error, 'plus utilisable|déjà consommé'):
                    verify_program(program.replace('CHECK', 'drop(-> original);'))
                skipped = valid.replace('{ result ->; <- result; }',
                                        '{ let hidden = <- result; drop(-> hidden); }')
                with self.assertRaisesRegex(Error, 'scope courant'):
                    verify_program(skipped)

    def test_sync_loop_returns_owned_join_results_from_distinct_pools(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut i = 0;
                let result = loop {
                    i = i + 1;
                    if i == 1 {
                        let ignored = new(p) Int(5);
                        let task = work(-> ignored);
                        let h = runtime::spawn(-> task);
                        let discarded = h.join();
                        drop(-> discarded);
                        continue;
                    }
                    if flag == 1 {
                        let left = new(p) Int(7);
                        let task = work(-> left);
                        let h = runtime::spawn(-> task);
                        let joined = h.join();
                        break <- joined;
                    } else {
                        let right = new(q) Int(8);
                        let task = work(-> right);
                        let h = runtime::spawn(-> task);
                        let joined = h.join();
                        break <- joined;
                    }
                };
                match result { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                let a = new(p) Int(2);
                let b = new(q) Int(3);
                print(a);
                print(b);
            }
            fn main() { run(1); run(0); }
        """
        code = compile_source(source)
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '7\n2\n3\n8\n2\n3\n')
        self.assertEqual(run.stderr.count('destroy ignored=5\n'), 2)
        self.assertEqual(run.stderr.count('destroy left=7\n'), 1)
        self.assertEqual(run.stderr.count('destroy right=8\n'), 1)
        nested = source.replace('let result = loop {', 'let result = { let inner = loop {').replace(
            '};\n                match result', '}; <- inner };\n                match result')
        self.assertEqual(self.run_c_oracle(compile_source(nested)).stdout, run.stdout)
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n2\n3\n99\n2\n3\n')
        for invalid, diagnostic in (
            (source.replace('break <- joined;', 'break joined;', 1), '<- explicite'),
            (source.replace('break <- joined;', 'drop(-> joined); break 1;', 1), 'même type'),
            (source.replace('let left = new(p)', 'let mut local = pool<Int>(1); let left = new(local)'),
             'ne survit pas à la boucle'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_sync_if_transfers_owned_join_result_from_each_continuing_branch(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let result = if flag == 1 {
                    let left = new(p) Int(7);
                    let task = work(-> left);
                    let h = runtime::spawn(-> task);
                    let joined = h.join();
                    <- joined
                } else {
                    let right = new(q) Int(8);
                    let task = work(-> right);
                    let h = runtime::spawn(-> task);
                    let joined = h.join();
                    <- joined
                };
                match result { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                let a = new(p) Int(2);
                let b = new(q) Int(3);
                print(a);
                print(b);
            }
            fn main() { run(1); run(0); }
        """
        code = compile_source(source)
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '7\n2\n3\n8\n2\n3\n')
        self.assertEqual(run.stderr.count('destroy left=7\n'), 1)
        self.assertEqual(run.stderr.count('destroy right=8\n'), 1)
        nested = source.replace('let result = if', 'let result = { let selected = if').replace(
            '};\n                match result', '}; <- selected };\n                match result')
        self.assertEqual(self.run_c_oracle(compile_source(nested)).stdout, run.stdout)
        early = source.replace('let joined = h.join();\n                    <- joined',
                               'let joined = h.join(); drop(-> joined); return;', 1)
        self.assertEqual(self.run_c_oracle(compile_source(early)).stdout, '8\n2\n3\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n2\n3\n99\n2\n3\n')
        for invalid, diagnostic in (
            (source.replace('<- joined', 'joined', 1), 'transférée par <-'),
            (source.replace('<- joined', 'drop(-> joined); 1', 1), 'même (type|mode)'),
            (source.replace('let left = new(p)', 'let mut local = pool<Int>(1); let left = new(local)'),
             'ne survit pas'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_async_if_transfers_owned_join_result_across_suspension(self):
        source = """
            async fn work(mut n: -> Int, amount: Int) -> <- Int {
                yield; n.set(amount); return <- n;
            }
            async fn parent(flag: Int, n: -> Int) {
                let result = if flag == 1 {
                    let t = work(-> n, 7);
                    let h = runtime::spawn(-> t);
                    let r = h.await;
                    <- r
                } else {
                    let t = work(-> n, 8);
                    let h = runtime::spawn(-> t);
                    let r = h.await;
                    <- r
                };
                yield;
                match result { Ok(v) => { print(*v); }, Err(_) => { print(99); } }
            }
            fn run(flag: Int) {
                let mut p = pool<Int>(1);
                let n = new(p) Int(1);
                let t = parent(flag, -> n);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(()) => {}, Err(_) => { print(999); } }
                let other = new(p) Int(2);
                print(other);
            }
            fn main() { run(1); run(0); }
        """
        run = self.run_c_oracle(compile_source(source))
        self.assertEqual(run.stdout, '7\n2\n8\n2\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        self.assertEqual(run.stderr.count('destroy n=8\n'), 1)
        early = source.replace('let r = h.await;\n                    <- r', 'let r = h.await; drop(-> r); return;', 1)
        self.assertEqual(self.run_c_oracle(compile_source(early)).stdout, '2\n8\n2\n')
        with self.assertRaisesRegex(Error, 'branche continuante.*transférer'):
            verify_program(source.replace('<- r', 'drop(-> r); 1', 1))

    def test_async_match_returns_owned_join_result_from_ok_or_err(self):
        source = """
            async fn gate() -> Int { yield; return 7; }
            async fn work(mut n: -> Int, amount: Int) -> <- Int {
                n.set(amount); yield; return <- n;
            }
            async fn parent(n: -> Int) {
                let gate_task = gate();
                let first = runtime::spawn(-> gate_task);
                let result = match first.await {
                    Ok(amount) => {
                        let task = work(-> n, amount);
                        let worker = runtime::spawn(-> task);
                        let r = worker.await;
                        <- r
                    },
                    Err(_) => {
                        let task = work(-> n, 8);
                        let worker = runtime::spawn(-> task);
                        let r = worker.await;
                        <- r
                    }
                };
                yield;
                match result { Ok(value) => { print(*value); }, Err(_) => { print(99); } }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(1);
                let t = parent(-> n);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(()) => {}, Err(_) => { print(999); } }
                let next = new(p) Int(2);
                print(next);
            }
        """
        def fail_first_async_submission(code):
            return inject_submission_failure(code, at=1)

        code = compile_source(source)
        for c, amount in ((code, 7), (fail_first_async_submission(code), 8)):
            run = self.run_c_oracle(c)
            self.assertEqual(run.stdout, f'{amount}\n2\n')
            self.assertEqual(run.stderr.count(f'destroy n={amount}\n'), 1)
        start = source.index('Ok(amount) =>')
        middle = source.index('Err(_) =>', start)
        end = source.index('\n                };', middle)
        ok = source[start:middle].rstrip().removesuffix(',')
        reversed_arms = source[:start] + source[middle:end] + ',\n                    ' + ok + source[end:]
        self.assertEqual(self.run_c_oracle(compile_source(reversed_arms)).stdout, '7\n2\n')
        early = source.replace('let r = worker.await;\n                        <- r',
                               'let r = worker.await; drop(-> r); return;', 1)
        self.assertEqual(self.run_c_oracle(compile_source(early)).stdout, '2\n')
        named = source.replace('match first.await {', 'match ready {').replace(
            'let result = match ready', 'let ready = first.await; yield; let result = match ready')
        self.assertEqual(self.run_c_oracle(compile_source(named)).stdout, '7\n2\n')
        with self.assertRaisesRegex(Error, 'branche continuante.*transférer'):
            verify_program(source.replace('<- r', 'drop(-> r); 1', 1))

    def test_sync_functions_transfer_the_whole_owned_join_result(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn collect(h: -> Execution<work>) -> <- Result<A<Int>,runtime::Error> {
                let result = h.join();
                return <- result;
            }
            fn relay(result: -> Result<A<Int>,runtime::Error>) -> <- Result<A<Int>,runtime::Error> {
                return <- result;
            }
            fn finish(result: -> Result<A<Int>,runtime::Error>) {
                match result { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                let task = work(-> n);
                let h = runtime::spawn(-> task);
                let result = { h ->; let inner = collect(-> h); <- inner };
                let moved = relay(-> result);
                CHECK
                finish(-> moved);
                let reused = new(p) Int(2);
                print(reused);
            }
        """
        valid = source.replace('CHECK', '')
        summaries = verify_program(valid).function_contracts
        self.assertEqual({(item.kind, item.parameter) for item in summaries['collect'].result.candidates},
                         {('task_capture', 0)})
        self.assertEqual({(item.kind, item.parameter) for item in summaries['relay'].result.candidates},
                         {('parameter', 0)})
        code = compile_source(valid)
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '7\n2\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        tail_return = valid.replace('return <- result;', '<- result', 1)
        self.assertEqual(self.run_c_oracle(compile_source(tail_return)).stdout, '7\n2\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n2\n')
        discard = valid.replace('match result { Ok(n) => { print(n); }, Err(_) => { print(99); } }',
                                'drop(-> result);')
        self.assertEqual(self.run_c_oracle(compile_source(discard)).stdout, '2\n')
        unwrap = valid.replace('fn finish(result: -> Result<A<Int>,runtime::Error>) {',
                               'fn finish(result: -> Result<A<Int>,runtime::Error>, fallback: -> Int) -> <- Int {')
        unwrap = unwrap.replace('Ok(n) => { print(n); }, Err(_) => { print(99); }',
                                'Ok(n) => { return <- n; }, Err(_) => { return <- fallback; }')
        unwrap = unwrap.replace('finish(-> moved);', 'let mut q = pool<Int>(1); let fallback = new(q) Int(99); '
                                'let final = finish(-> moved, -> fallback); print(final); drop(-> final);')
        self.assertEqual(self.run_c_oracle(compile_source(unwrap)).stdout, '7\n2\n')
        local = """
            async fn work(n: -> Int) -> <- Int { return <- n; }
            fn invalid() -> <- Result<A<Int>,runtime::Error> {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                let t = work(-> n);
                let h = runtime::spawn(-> t);
                let result = h.join();
                return <- result;
            }
        """
        with self.assertRaisesRegex(Error, 'ne survit pas'):
            verify_program(local)
        for invalid, diagnostic in (
            (valid.replace('finish(-> moved);', 'finish(moved);'), 'mode attendu join_owned'),
            (source.replace('CHECK', 'drop(-> result);'), 'plus utilisable'),
            (valid.replace('return <- result;', 'return result;', 1), 'explicite'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_async_signatures_transfer_owned_join_result_across_await(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            async fn relay(r: -> Result<A<Int>,runtime::Error>) -> <- Result<A<Int>,runtime::Error> {
                yield;
                <- r
            }
            async fn parent(n: -> Int) {
                let t = work(-> n);
                let h = runtime::spawn(-> t);
                let joined = h.await;
                let child = relay(-> joined);
                CHECK
                let moved = child.await;
                yield;
                match moved { Ok(v) => { print(*v); }, Err(_) => { print(99); } }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                let t = parent(-> n);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(()) => {}, Err(_) => { print(999); } }
                let next = new(p) Int(2);
                print(next);
            }
        """
        valid = source.replace('CHECK', '')
        code = compile_source(valid)
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '7\n2\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        failed = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n2\n')
        discard = valid.replace('let moved = child.await;', 'drop(-> child);').replace(
            'match moved { Ok(v) => { print(*v); }, Err(_) => { print(99); } }', '')
        discarded = self.run_c_oracle(compile_source(discard))
        self.assertEqual(discarded.stdout, '2\n')
        self.assertEqual(discarded.stderr.count('destroy n=7\n'), 1)
        mixed = """
            async fn work(n: -> Int) -> <- Int { return <- n; }
            async fn release(result: -> Result<A<Int>,runtime::Error>, plain: -> Int) {
                let renamed = <- result;
                { renamed ->; <- renamed; }
                yield;
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = new(p) Int(7);
                let b = new(p) Int(8);
                let task = work(-> a);
                let h = runtime::spawn(-> task);
                let result = h.join();
                let cleanup = release(-> result, -> b);
                let execution = runtime::spawn(-> cleanup);
                match execution.join() { Ok(()) => {}, Err(_) => {} }
            }
        """
        cleanup = self.run_c_oracle(compile_source(mixed))
        self.assertEqual([line for line in cleanup.stderr.splitlines() if line.startswith('destroy ')],
                         # Returning renamed from its child scope is a new reception.
                         ['destroy a=7', 'destroy b=8'])
        for invalid, diagnostic in (
            (valid.replace('relay(-> joined)', 'relay(joined)'), 'transfert -> requis'),
            (source.replace('CHECK', 'drop(-> joined);'), 'déjà consommé'),
            (valid.replace('<- r', 'return r;'), '<- explicite'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_nested_join_keeps_inner_error_and_outer_error_distinct(self):
        definitions = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            async fn relay(r: -> Result<A<Int>,runtime::Error>) -> <- Result<A<Int>,runtime::Error> {
                yield; <- r
            }
        """
        body = """
            let t = work(-> n);
            let first = runtime::spawn(-> t);
            let inner = FIRST;
            let relay_task = relay(-> inner);
            let second = runtime::spawn(-> relay_task);
            let nested = SECOND;
            CHECK
            match nested {
                Ok(payload) => {
                    match payload { Ok(v) => { print(READ); }, Err(_) => { print(8); } }
                },
                Err(_) => { print(9); }
            }
        """
        entry = """
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                RUN
                let next = new(p) Int(2);
                print(next);
            }
        """
        sync = body.replace('FIRST', 'first.join()').replace('SECOND', 'second.join()').replace('READ', 'v')
        asynchronous = body.replace('FIRST', 'first.await').replace('SECOND', 'second.await').replace('READ', '*v')
        programs = (
            (definitions + entry.replace('RUN', sync), '1'),
            (definitions + 'async fn parent(n: -> Int) {' + asynchronous + '}' + entry.replace(
                'RUN', 'let t = parent(-> n); let h = runtime::spawn(-> t); '
                'match h.join() { Ok(()) => {}, Err(_) => { print(999); } }'), '(a)'),
        )
        for source, worker in programs:
            valid = source.replace('CHECK', '')
            code = compile_source(valid)
            for fail_at, expected in ((0, 7), (1, 8), (2, 9)):
                with self.subTest(worker=worker, fail_at=fail_at):
                    run = self.run_c_oracle(inject_submission_failure(code, asynchronous=worker != '1', at=fail_at))
                    self.assertEqual(run.stdout, f'{expected}\n2\n')
                    self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
            wait = 'second.join()' if worker == '1' else 'second.await'
            moved = valid.replace(f'let nested = {wait};', 'let nested = { second ->; '
                                  f'let pending = {wait}; let renamed = <- pending; <- renamed }};')
            self.assertEqual(self.run_c_oracle(compile_source(moved)).stdout, '7\n2\n')
            received = f'let nested = {wait};'
            branch = f'second ->; let outcome = {wait}; <- outcome'
            conditional = valid.replace(received, 'let nested = if true { ' + branch +
                                        ' } else { ' + branch + ' };')
            loop = valid.replace(received, f'let nested = loop {{ second ->; let outcome = {wait}; '
                                 'break <- outcome; };')
            gate_wait = 'gate_handle.join()' if worker == '1' else 'gate_handle.await'
            ok_branch = branch.replace('second ->;', 'second ->; print(flag);', 1)
            matched = 'async fn gate() -> Int { return 1; } ' + valid.replace(
                received, 'let gate_task = gate(); let gate_handle = runtime::spawn(-> gate_task); '
                f'let nested = match {gate_wait} {{ Ok(flag) => {{ {ok_branch} }}, '
                f'Err(_) => {{ {branch} }} }};')
            for context, program, expected_output in (
                ('if', conditional, '7\n2\n'), ('loop', loop, '7\n2\n'), ('match', matched, '1\n7\n2\n'),
            ):
                with self.subTest(worker=worker, context=context):
                    run = self.run_c_oracle(compile_source(program))
                    self.assertEqual(run.stdout, expected_output)
                    self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
            invalid = conditional.replace('<- outcome', 'drop(-> outcome); 1', 1)
            with self.assertRaisesRegex(Error, 'même (type|mode)|branche continuante'):
                verify_program(invalid)
            start = valid.index('match nested {')
            end = valid.index('Err(_) => { print(9); }', start) + len('Err(_) => { print(9); }\n            }')
            ignored = valid[:start] + 'match nested { Ok(_) => {}, Err(_) => {} }' + valid[end:]
            with self.assertRaisesRegex(Error, 'motif _'):
                verify_program(ignored)
            explicit = ignored.replace('match nested { Ok(_) => {},',
                                       'match nested { Ok(payload) => { drop(-> payload); },')
            self.assertEqual(self.run_c_oracle(compile_source(explicit)).stdout, '2\n')
            discarded = valid[:start] + 'drop(-> nested);' + valid[end:]
            discarded_c = compile_source(discarded)
            for fail_at in (0, 1, 2):
                run = self.run_c_oracle(inject_submission_failure(discarded_c, asynchronous=worker != '1', at=fail_at))
                self.assertEqual(run.stdout, '2\n')
                self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
            with self.assertRaisesRegex(Error, 'plus utilisable|déjà consommé'):
                verify_program(source.replace('CHECK', 'drop(-> nested);'))
            abandoned = valid.replace('let nested =', 'drop(-> second); let nested =')
            with self.assertRaisesRegex(Error, 'join requis|attente requise'):
                verify_program(abandoned)

    def test_nested_join_result_transfers_through_sync_and_async_signatures(self):
        nested_type = 'Result<Result<A<Int>,runtime::Error>,runtime::Error>'
        definitions = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            async fn relay(r: -> Result<A<Int>,runtime::Error>) -> <- Result<A<Int>,runtime::Error> {
                yield; <- r
            }
        """
        launches = """
            let t = work(-> n);
            let h = runtime::spawn(-> t);
            let first = WAIT1;
            let task = relay(-> first);
            let execution = runtime::spawn(-> task);
            let nested = WAIT2;
        """
        matching = """
            match moved {
                Ok(inner) => { match inner { Ok(v) => { print(READ); }, Err(_) => { print(8); } } },
                Err(_) => { print(9); }
            }
        """
        main = """
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                RUN
                let next = new(p) Int(2);
                print(next);
            }
        """
        passthrough = f'fn pass(r: -> {nested_type}) -> <- {nested_type} {{ <- r }}'
        sync_body = launches.replace('WAIT1', 'h.join()').replace('WAIT2', 'execution.join()')
        sync = definitions + passthrough + main.replace(
            'RUN', sync_body + 'let moved = pass(-> nested);' + matching.replace('READ', 'v'))
        async_body = launches.replace('WAIT1', 'h.await').replace('WAIT2', 'execution.await')
        async_body += 'let child = pass(-> nested); let moved = child.await; yield;'
        parent = 'async fn parent(n: -> Int) {' + async_body + matching.replace('READ', '*v') + '}'
        asynchronous = definitions + 'async ' + passthrough.replace('<- r }', 'yield; <- r }') + parent
        asynchronous += main.replace('RUN', 'let t = parent(-> n); let h = runtime::spawn(-> t); '
                                     'match h.join() { Ok(()) => {}, Err(_) => { print(999); } }')
        for source, eligible in ((sync, '1'), (asynchronous, '(a)')):
            with self.subTest(eligible=eligible):
                code = compile_source(source)
                for fail_at, value in ((0, 7), (1, 8), (2, 9)):
                    run = self.run_c_oracle(inject_submission_failure(code, asynchronous=eligible != '1', at=fail_at))
                    self.assertEqual(run.stdout, f'{value}\n2\n')
                    self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
                invalid = source.replace('pass(-> nested)', 'pass(nested)')
                with self.assertRaisesRegex(Error, 'mode attendu|transfert -> requis'):
                    verify_program(invalid)
        discard_body = sync_body + 'let holder = retain(-> nested); drop(-> holder);'
        inactive = definitions + f'async fn retain(r: -> {nested_type}) {{ yield; }}'
        inactive += main.replace('RUN', discard_body)
        run = self.run_c_oracle(compile_source(inactive))
        self.assertEqual(run.stdout, '2\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        triple = asynchronous.replace(
            'let moved = child.await; yield;' + matching.replace('READ', '*v'),
            'let third = runtime::spawn(-> child); let outer = third.await; '
            'match outer { Ok(moved) => {' + matching.replace('READ', '*v') +
            '} Err(_) => { print(10); } }')
        run = self.run_c_oracle(compile_source(triple))
        self.assertEqual(run.stdout, '7\n2\n')
        self.assertEqual(run.stderr.count('destroy n=7\n'), 1)
        with self.assertRaisesRegex(Error, 'attente|join requis'):
            verify_program(triple.replace('let outer = third.await;', 'return; let outer = third.await;'))

    def test_join_retains_only_the_directly_returned_capture_sources(self):
        source = """
            async fn pick(a: -> Int, b: -> Int) -> <- Int { yield; return <- a; }
            fn start(a: -> Int, b: -> Int) -> <- Execution<pick> {
                let t = pick(-> a, -> b);
                let h = runtime::spawn(-> t);
                return <- h;
            }
            fn relay(h: -> Execution<pick>) -> <- Execution<pick> { if true {} else {} return <- h; }
            fn release(h: -> Execution<pick>, p: &mut Pool<Int>) {
                let result = h.join();
                match result { Ok(v) => { p.drop(-> v); }, Err(_) => {} }
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let a = new(p) Int(7);
                let b = new(q) Int(8);
                let h = start(-> a, -> b);
                let moved = relay(-> h);
                BEFORE
                let result = moved.join();
                AFTER
                match result { Ok(v) => { p.drop(-> v); }, Err(_) => {} }
                let again = new(p) Int(2);
                print(again);
            }
        """
        valid = source.replace('BEFORE', '').replace('AFTER', 'q.reset();')
        compiler = verify_program(valid, allow_legacy_reset=True)
        start = compiler.function_contracts['start'].result
        self.assertEqual({origin.index for origin in start.task_sources}, {0, 1})
        self.assertEqual({origin.index for origin in start.task_result_sources}, {0})
        relay = compiler.function_contracts['relay'].result
        self.assertEqual({origin.kind for origin in relay.task_result_sources}, {'task_result_parameter'})
        run = self.run_c_oracle(compile_source(valid, allow_legacy_reset=True))
        self.assertEqual(run.stdout, '2\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy b=8', 'destroy a=7', 'destroy again=2'])
        for before, after in (('q.reset();', ''), ('', 'p.reset();')):
            with self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(source.replace('BEFORE', before).replace('AFTER', after), allow_legacy_reset=True)
        alternative = valid.replace('yield; return <- a;', 'yield; if *a == 7 { return <- a; } return <- b;')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(alternative, allow_legacy_reset=True)
        release = source.replace('BEFORE\n                let result = moved.join();\n                AFTER\n'
                                 '                match result { Ok(v) => { p.drop(-> v); }, Err(_) => {} }',
                                 'release(-> moved, &mut p);')
        self.assertEqual(self.run_c_oracle(compile_source(release)).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'source de stockage d’origine'):
            verify_program(release.replace('release(-> moved, &mut p);', 'release(-> moved, &mut q);'))

        scalar = """
            async fn worker(n: -> Int) -> Int { yield; return *n; }
            fn relay(h: -> Execution<worker>) -> <- Execution<worker> {
                if true {} else {}
                return <- h;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = new(p) Int(7);
                let task = worker(-> n);
                let h = runtime::spawn(-> task);
                let moved = relay(-> h);
                p.reset();
                match moved.join() { Ok(v) => { print(v); }, Err(_) => {} }
            }
        """
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(scalar, allow_legacy_reset=True)

    def test_join_tracks_owned_provenance_through_awaited_bindings(self):
        source = """
            async fn leaf(unused: -> Int, chosen: -> Int) -> <- Int {
                yield;
                return <- chosen;
            }
            async fn relay(a: -> Int, b: -> Int) -> <- Int {
                let task = leaf(-> b, -> a);
                let moved = <- task;
                let value = moved.await;
                yield;
                return <- value;
            }
            async fn outer(a: -> Int, b: -> Int) -> <- Int {
                let value = relay(-> a, -> b).await;
                return <- value;
            }
            fn prepare(a: -> Int, b: -> Int) -> <- Execution<outer> {
                let task = outer(-> a, -> b);
                let h = runtime::spawn(-> task);
                return <- h;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let a = new(p) Int(7);
                let b = new(q) Int(8);
                let h = prepare(-> a, -> b);
                let result = h.join();
                q.reset();
                match result { Ok(value) => { print(value); p.drop(-> value); }, Err(_) => {} }
                let reused = new(p) Int(2);
                print(reused);
            }
        """
        compiler = verify_program(source, allow_legacy_reset=True)
        result = compiler.function_contracts['prepare'].result
        self.assertEqual({origin.index for origin in result.task_result_sources}, {0})
        run = self.run_c_oracle(compile_source(source, allow_legacy_reset=True))
        self.assertEqual(run.stdout, '7\n2\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy b=8', 'destroy a=7', 'destroy reused=2'])
        selected_other = source.replace('leaf(-> b, -> a)', 'leaf(-> a, -> b)')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(selected_other, allow_legacy_reset=True)
        threaded = source.replace(
            'async fn outer(a: -> Int, b: -> Int) -> <- Int {\n'
            '                let value = relay(-> a, -> b).await;\n'
            '                return <- value;',
            'async fn outer(a: -> Int, b: -> Int) -> <- Result<A<Int>,runtime::Error> { '
            'let task = relay(-> a, -> b); let worker = runtime::spawn(-> task); '
            'let value = worker.await; return <- value;')
        threaded = threaded.replace(
            'match result { Ok(value) => { print(value); p.drop(-> value); }, Err(_) => {} }',
            'match result { Ok(inner) => { match inner { Ok(value) => { print(value); p.drop(-> value); }, '
            'Err(_) => {} } }, Err(_) => {} }')
        self.assertEqual(self.run_c_oracle(compile_source(threaded, allow_legacy_reset=True)).stdout, '7\n2\n')
        wrong_pool = source.replace('q.reset();', '').replace('p.drop(-> value);', 'q.drop(-> value);')
        with self.assertRaisesRegex(Error, 'source de stockage d’origine'):
            verify_program(wrong_pool, allow_legacy_reset=True)

    def test_owned_provenance_follows_block_branch_and_loop_results(self):
        source = """
            async fn leaf(unused: -> Int, chosen: -> Int) -> <- Int {
                yield; return <- chosen;
            }
            async fn gate() -> Int { return 1; }
            async fn work(a: -> Int, b: -> Int) -> <- Result<A<Int>,runtime::Error> {
                BODY
                return <- selected;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let a = new(p) Int(7);
                let b = new(q) Int(8);
                let task = work(-> a, -> b);
                let h = runtime::spawn(-> task);
                let result = h.join();
                q.reset();
                match result {
                    Ok(inner) => { match inner { Ok(value) => { print(value); }, Err(_) => {} } },
                    Err(_) => {}
                }
                let reused = new(p) Int(2);
                print(reused);
            }
        """
        wait = 'let task = leaf(-> b, -> a); let h = runtime::spawn(-> task); let r = h.await;'
        transfer = wait + ' <- r'
        cases = {
            'block': 'let selected = { ' + transfer + ' };',
            'if': 'let selected = if true { ' + transfer + ' } else { ' + transfer + ' };',
            'loop': 'let selected = loop { ' + wait + ' break <- r; };',
            'match': 'let gate_task = gate(); let gate_handle = runtime::spawn(-> gate_task); '
                     'let selected = match gate_handle.await { Ok(flag) => { ' + transfer +
                     ' }, Err(_) => { ' + transfer + ' } };',
        }
        for kind, body in cases.items():
            with self.subTest(kind=kind):
                run = self.run_c_oracle(compile_source(source.replace('BODY', body), allow_legacy_reset=True))
                self.assertEqual(run.stdout, '7\n2\n')
                self.assertEqual(run.stderr.count('destroy b=8\n'), 1)
        first, separator, second = cases['if'].partition(' else ')
        alternate = first + separator + second.replace('leaf(-> b, -> a)', 'leaf(-> a, -> b)')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('BODY', alternate), allow_legacy_reset=True)
        different_breaks = ('let selected = loop { if true { ' + wait + ' break <- r; } else { ' +
                            wait.replace('leaf(-> b, -> a)', 'leaf(-> a, -> b)') + ' break <- r; } };')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('BODY', different_breaks), allow_legacy_reset=True)

    def test_returned_task_preserves_detached_shared_field_capture(self):
        source = """
            struct View { target: &Int }
            async fn read(n: &Int) -> &Int { yield; return n; }
            fn prepare(v: &View) -> <- read {
                let task = read(&*v.target);
                return <- task;
            }
            fn relay(v: &View) -> <- read {
                let task = prepare(v);
                return <- task;
            }
            fn main() {
                let mut ints = pool<Int>(1);
                let mut n = ints.new(7);
                let mut views = pool<View>(1);
                let v = views.new(target: &n);
                let t = relay(&v);
                drop(-> v);
                let reused = views.new(target: &n);
                print(reused);
                drop(-> reused);
                let h = runtime::spawn(-> t);
                RUNNING
                match h.join() {
                    Ok(x) => { RESULT print(*x); },
                    Err(_) => { print(99); }
                }
                n = 8;
                print(n);
            }
        """
        valid = source.replace('RUNNING', '').replace('RESULT', '')
        fields = dict(verify_program(valid).function_contracts['relay'].result.borrowed_fields)
        self.assertEqual({(o.kind, o.parameter, o.field) for o in fields['ref.0']},
                         {('detached_field_parameter', 0, '.target')})
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, 'View(7)\n7\n8\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, run, data) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, 'View(7)\n99\n8\n')
        for position in ('RUNNING', 'RESULT'):
            for statement, diagnostic in (('drop(-> n);', 'emprunt encore utilisé'),
                                          ('n = 9;', 'emprunt actif'),
                                          ('ints.reset();', 'reset interdit')):
                with self.subTest(position=position, statement=statement), self.assertRaisesRegex(Error, diagnostic):
                    invalid = source.replace(position, statement).replace('RUNNING', '').replace('RESULT', '')
                    verify_program(invalid, allow_legacy_reset=True)
        escaped = valid.replace('let task = read(&*v.target);', """
                let mut local_pool = pool<Int>(1);
                let local = local_pool.new(9);
                let mut local_views = pool<View>(1);
                let temporary = local_views.new(target: &local);
                let task = read(&*temporary.target);
        """)
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaped)

        consumed = source.replace('v: &View', 'v: -> View').replace(
            'prepare(v)', 'prepare(-> v)',
        ).replace('relay(&v)', 'relay(-> v)').replace('drop(-> v);', '')
        valid_consumed = consumed.replace('RUNNING', '').replace('RESULT', '')
        run = self.run_c_oracle(compile_source(valid_consumed))
        self.assertEqual(run.stdout, 'View(7)\n7\n8\n')
        for position in ('RUNNING', 'RESULT'):
            with self.subTest(consuming=True, position=position):
                invalid = consumed.replace(position, 'drop(-> n);').replace('RUNNING', '').replace('RESULT', '')
                with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(invalid)

    def test_async_break_owned_without_receiver_warns_and_respects_scope_cleanup(self):
        source = """
            async fn parent(n: -> Int) -> Int {
                loop { IMPORT yield; break <- n; }
                AFTER
                return 11;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = p.new(5);
                let h = runtime::spawn(-> parent(-> n));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let reused = p.new(7);
                print(reused);
            }
        """
        for imports, after, expected in (('n ->;', '', '11\n7\n'), ('', 'print(*n);', '5\n11\n7\n')):
            with self.subTest(imports=imports):
                program = source.replace('IMPORT', imports).replace('AFTER', after)
                checked = verify_program(program)
                self.assertTrue(any('transfert sans receveur' in warning for warning in checked.warnings))
                run = self.run_c_oracle(compile_source(program))
                self.assertEqual(run.stdout, expected)
                self.assertEqual(run.stderr.count('destroy n=5\n'), 1)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('IMPORT', 'n ->;').replace('AFTER', 'print(*n);'))
        with self.assertRaisesRegex(Error, 'déjà consommé'):
            verify_program(source.replace('IMPORT', 'n ->; <- n; drop(-> n);').replace(
                'break <- n;', 'break;',
            ).replace('AFTER', ''))
        borrowed = 'async fn edit(n: &mut Int) { yield; n.set(9); }' + source.replace(
            'parent(n: -> Int)', 'parent(mut n: -> Int)',
        ).replace('loop { IMPORT', 'let t = edit(&mut n); loop {').replace('AFTER', 't.await; print(*n);')
        self.assertEqual(self.run_c_oracle(compile_source(borrowed)).stdout, '9\n11\n7\n')
        returned = 'async fn edit(n: &mut Int) { yield; n.set(9); }' + source.replace(
            'parent(n: -> Int)', 'parent(mut n: -> Int)',
        ).replace('IMPORT', 'n ->; let t = edit(&mut n); <- n; t.await;').replace('AFTER', 'print(*n);')
        self.assertEqual(self.run_c_oracle(compile_source(returned)).stdout, '9\n11\n7\n')

    def test_async_owned_rename_keeps_slot_and_cleanup_order(self):
        source = """
            async fn worker(a: -> Int, b: -> Int) -> Int {
                BODY
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = p.new(5);
                let b = p.new(7);
                let h = runtime::spawn(-> worker(-> a, -> b));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let next_a = p.new(15);
                let next_b = p.new(17);
                print(next_a);
                print(next_b);
            }
        """
        body = 'let mut renamed = <- a; yield; renamed.set(9); CHECK return *renamed + *b;'
        program = source.replace('BODY', body)
        run = self.run_c_oracle(compile_source(program.replace('CHECK', '')))
        self.assertEqual(run.stdout, '16\n15\n17\n')
        destroys = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(destroys[:2], ['destroy b=7', 'destroy a=9'])
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(program.replace('CHECK', 'print(*a);'))
        child = """
            let kept = {
                a ->;
                let renamed = <- a;
                yield;
                <- renamed
            };
            return *kept + *b;
        """
        run = self.run_c_oracle(compile_source(source.replace('BODY', child)))
        self.assertEqual(run.stdout, '12\n15\n17\n')
        self.assertEqual(run.stderr.count('destroy a=5\n'), 1)
        self.assertEqual(run.stderr.count('destroy b=7\n'), 1)

    def test_async_return_selects_capture_cleanup_order(self):
        source = """
            async fn worker(a: -> Int, b: -> Int, flag: Int) -> Int {
                if flag == 0 { return *a + *b; }
                { a ->; yield; <- a; }
                return *a + *b;
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = p.new(5);
                let b = p.new(7);
                let task = worker(-> a, -> b, FLAG);
                RUN
                let next_a = p.new(15);
                let next_b = p.new(17);
                print(next_a);
                print(next_b);
            }
        """
        join = """
            let h = runtime::spawn(-> task);
            match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
        """
        default_order = ['destroy b=7', 'destroy a=5']
        for scenario, flag, action, expected_output, order in (
            ('early return', '0', join, '12\n', default_order),
            ('restitution', '1', join, '12\n', list(reversed(default_order))),
            ('inactive drop', '1', 'drop(-> task);', '', default_order),
            ('failed launch', '1', join, '99\n', default_order),
        ):
            with self.subTest(scenario=scenario):
                code = compile_source(source.replace('FLAG', flag).replace('RUN', action))
                if scenario == 'failed launch':
                    code = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                        '#define pthread_create(thread, attr, runner, pointer) EAGAIN')
                run = self.run_c_oracle(code)
                self.assertEqual(run.stdout, expected_output + '15\n17\n')
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
                self.assertEqual(destroyed, order + ['destroy next_b=17', 'destroy next_a=15'])

    def test_async_terminal_cleanup_interleaves_capture_and_local_receipt(self):
        code = compile_source("""
            async fn relay(n: -> Int) -> <- Int { yield; return <- n; }
            async fn worker(a: -> Int, b: -> Int, c: -> Int) -> Int {
                let received = relay(-> c).await;
                { a ->; yield; <- a; }
                return *a + *b + *received;
            }
            fn main() {
                let mut p = pool<Int>(3);
                let a = p.new(5);
                let b = p.new(7);
                let c = p.new(9);
                let h = runtime::spawn(-> worker(-> a, -> b, -> c));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let first = p.new(15);
                let second = p.new(17);
                let third = p.new(19);
                print(first);
                print(second);
                print(third);
            }
        """)
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '21\n15\n17\n19\n')
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(destroyed, [
            'destroy a=5', 'destroy c=9', 'destroy b=7',
            'destroy third=19', 'destroy second=17', 'destroy first=15',
        ])

    def test_async_owned_receiver_replacement(self):
        source = """
            async fn relay(n: -> Int) -> <- Int { yield; return <- n; }
            async fn worker(mut a: -> Int, b: -> Int) -> <- Int {
                REPLACE
                return <- a;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let a = p.new(5);
                let b = q.new(7);
                let h = runtime::spawn(-> worker(-> a, -> b));
                match h.join() { Ok(x) => { print(x); drop(-> x); }, Err(_) => { print(99); } }
                let again_a = p.new(15);
                let again_b = q.new(17);
                print(again_a);
                print(again_b);
            }
        """
        for action, result, order in (
            ('a = <- b;', 7, ['destroy a=5', 'destroy b=7']),
            ('a = relay(-> b).await;', 7, ['destroy a=5', 'destroy b=7']),
            ('a = relay(-> a).await;', 5, ['destroy b=7', 'destroy a=5']),
            ('a = <- a;', 5, ['destroy b=7', 'destroy a=5']),
            ('a = { b ->; yield; <- b };', 7, ['destroy a=5', 'destroy b=7']),
            ('a = if *a == 5 { b ->; yield; <- b } else { b ->; <- b };',
             7, ['destroy a=5', 'destroy b=7']),
            ('a = loop { b ->; yield; break <- b; };', 7, ['destroy a=5', 'destroy b=7']),
        ):
            with self.subTest(action=action):
                run = self.run_c_oracle(compile_source(source.replace('REPLACE', action)))
                self.assertEqual(run.stdout, f'{result}\n15\n17\n')
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
                self.assertEqual(destroyed, order + ['destroy again_b=17', 'destroy again_a=15'])
        reuse_old_pool = source.replace('REPLACE', 'a = relay(-> b).await;').replace(
            'print(x); drop(-> x);',
            'let recycled = p.new(25); print(recycled); print(x); drop(-> x);',
        )
        run = self.run_c_oracle(compile_source(reuse_old_pool))
        self.assertEqual(run.stdout, '25\n7\n15\n17\n')
        for action in (
            '{ b ->; a = relay(-> b).await; }',
            'if *a == 5 { b ->; a = relay(-> b).await; } else { b ->; a = <- b; }',
        ):
            with self.subTest(action=action):
                run = self.run_c_oracle(compile_source(reuse_old_pool.replace('a = relay(-> b).await;', action)))
                self.assertEqual(run.stdout, '25\n7\n15\n17\n')
        borrowed_rhs = """
            async fn view(n: &Int) -> &Int { return n; }
            async fn carry(old: &Int, n: -> Int) -> <- Int {
                yield;
                print(*old);
                return <- n;
            }
        """ + source.replace('REPLACE', 'let previous = view(&a).await; a = carry(previous, -> b).await;')
        run = self.run_c_oracle(compile_source(borrowed_rhs))
        self.assertEqual(run.stdout, '5\n7\n15\n17\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(borrowed_rhs.replace('return <- a;', 'print(*previous); return <- a;'))
        nested_rhs = borrowed_rhs.replace(
            'a = carry(previous, -> b).await;',
            '{ b ->; { b ->; a = carry(previous, -> b).await; } }',
        )
        self.assertEqual(self.run_c_oracle(compile_source(nested_rhs)).stdout, '5\n7\n15\n17\n')
        for later_use in (
            nested_rhs.replace('return <- a;', 'print(*previous); return <- a;'),
            nested_rhs.replace('await; } }', 'await; } print(*previous); }'),
            nested_rhs.replace('await; } }', 'await; print(*previous); } }'),
            nested_rhs.replace('let previous = view(&a).await;',
                               'let previous = view(&a).await; let pending = view(previous);')
                      .replace('return <- a;', 'let still = pending.await; print(*still); return <- a;'),
        ):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(later_use)
        branched_rhs = borrowed_rhs.replace(
            'a = carry(previous, -> b).await;',
            """
            if FLAG == 0 {
                b ->;
                a = carry(previous, -> b).await;
            } else {
                b ->;
                print(*previous);
                drop(-> b);
            }
            """,
        )
        for flag, expected in (('0', 7), ('1', 5)):
            with self.subTest(flag=flag):
                program = branched_rhs.replace('FLAG', flag)
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout,
                                 f'5\n{expected}\n15\n17\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('return <- a;', 'print(*previous); return <- a;'))
        valued_rhs = branched_rhs.replace('if FLAG == 0 {', 'let tag = if FLAG == 0 {').replace(
            'a = carry(previous, -> b).await;', 'a = carry(previous, -> b).await; 11',
        ).replace('drop(-> b);\n            }', 'drop(-> b); 22\n            }; print(tag);')
        for flag, tag, result in (('0', 11, 7), ('1', 22, 5)):
            with self.subTest(valued_flag=flag):
                program = valued_rhs.replace('FLAG', flag)
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout,
                                 f'5\n{tag}\n{result}\n15\n17\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('return <- a;', 'print(*previous); return <- a;'))
        owned_rhs = borrowed_rhs.replace(
            'a = carry(previous, -> b).await;',
            'let result = { b ->; c ->; a = carry(previous, -> b).await; <- c }; print(*result);',
        ).replace('b: -> Int) -> <- Int', 'b: -> Int, c: -> Int) -> <- Int').replace(
            'let h = runtime::spawn(-> worker(-> a, -> b));',
            'let mut r = pool<Int>(1); let c = r.new(9); let h = runtime::spawn(-> worker(-> a, -> b, -> c));',
        )
        self.assertEqual(self.run_c_oracle(compile_source(owned_rhs)).stdout, '5\n9\n7\n15\n17\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(owned_rhs.replace('return <- a;', 'print(*previous); return <- a;'))
        argument_rhs = 'async fn pair(tag: Int, old: &Int) { print(tag + *old); }' + valued_rhs.replace(
            'let tag = if FLAG == 0 {', 'pair(if 0 == 0 {',
        ).replace('}; print(tag);', '}, previous).await;')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(argument_rhs)
        matched_rhs = 'async fn gate() -> Int { yield; return 1; }' + valued_rhs.replace(
            'let tag = if FLAG == 0 {', '''
            let gate_task = gate();
            let gate_handle = runtime::spawn(-> gate_task);
            let tag = match gate_handle.await { Ok(n) => {
            ''',
        ).replace('await; 11', 'await; n + 10').replace(
            '} else {\n                b ->;', '}, Err(_) => {\n                b ->;',
        ).replace('}; print(tag);', '} }; print(tag);')
        self.assertEqual(self.run_c_oracle(compile_source(matched_rhs)).stdout, '5\n11\n7\n15\n17\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(matched_rhs.replace('return <- a;', 'print(*previous); return <- a;'))
        breaking_rhs = borrowed_rhs.replace(
            'a = carry(previous, -> b).await;',
            'loop { b ->; a = carry(previous, -> b).await; break; }',
        )
        self.assertEqual(self.run_c_oracle(compile_source(breaking_rhs)).stdout, '5\n7\n15\n17\n')
        valued_break = breaking_rhs.replace('loop { b ->;', 'let tag = loop { b ->;').replace(
            'break; }', 'break 11; }; print(tag);',
        )
        self.assertEqual(self.run_c_oracle(compile_source(valued_break)).stdout, '5\n11\n7\n15\n17\n')
        delayed_break = breaking_rhs.replace('await; break;', 'await; yield; print(*a); break;')
        self.assertEqual(self.run_c_oracle(compile_source(delayed_break)).stdout, '5\n7\n7\n15\n17\n')
        outer_break = delayed_break.replace('b ->; a = carry', 'b ->; { b ->; a = carry').replace(
            'await; yield;', 'await; } yield;',
        )
        self.assertEqual(self.run_c_oracle(compile_source(outer_break)).stdout, '5\n7\n7\n15\n17\n')
        for later_use in (
            breaking_rhs.replace('await; break;', 'await; print(*a); continue;'),
            breaking_rhs.replace('return <- a;', 'print(*previous); return <- a;'),
            valued_break.replace('break 11;', 'break *previous;'),
            delayed_break.replace('yield; print(*a); break;', 'yield; print(*previous); break;'),
            delayed_break.replace('yield; print(*a); break;', 'if *a == 7 { continue; } break;'),
            outer_break.replace('yield; print(*a); break;', 'yield; print(*previous); break;'),
        ):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(later_use)
        for action, diagnostic in (
            ('drop(-> a); a = <- b;', 'plus utilisable'),
            ('let task = relay_ref(&a); a = <- b; task.await;', 'emprunt actif'),
        ):
            with self.subTest(action=action), self.assertRaisesRegex(Error, diagnostic):
                verify_program('async fn relay_ref(a: &Int) { print(*a); }' + source.replace('REPLACE', action))

    def test_async_replacement_joins_returned_pool_origins(self):
        source = """
            async fn choose(mut a: -> Int, b: -> Int, c: -> Int, flag: Int) -> <- Int {
                if flag == 0 {
                    b ->; c ->;
                    a = <- b;
                    drop(-> c);
                } else {
                    b ->; c ->;
                    a = <- c;
                    drop(-> b);
                }
                return <- a;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut q = pool<Int>(1);
                let mut r = pool<Int>(1);
                let a = p.new(5);
                let b = q.new(7);
                let c = r.new(9);
                let h = runtime::spawn(-> choose(-> a, -> b, -> c, FLAG));
                match h.join() {
                    Ok(x) => { let reused = p.new(25); print(reused); print(x); }
                    Err(_) => { print(99); }
                }
                let again_b = q.new(17);
                let again_c = r.new(19);
                print(again_b);
                print(again_c);
            }
        """
        loop = source.replace('if flag == 0 {', 'loop { b ->; c ->; if flag == 0 {').replace(
            'return <- a;', 'break; } return <- a;',
        )
        for case, flag, expected in (
            (source, '0', 7), (source, '1', 9), (loop, '0', 7), (loop, '1', 9),
        ):
            with self.subTest(loop=case == loop, flag=flag):
                program = case.replace('FLAG', flag)
                run = self.run_c_oracle(compile_source(program))
                self.assertEqual(run.stdout, f'25\n{expected}\n17\n19\n')
                for pool in ('p', 'q', 'r'):
                    reset = program.replace('let reused = p.new(25);', f'{pool}.reset(); let reused = p.new(25);')
                    if pool == 'p':
                        self.assertEqual(self.run_c_oracle(compile_source(reset, allow_legacy_reset=True)).stdout,
                                         run.stdout)
                    else:
                        with self.assertRaisesRegex(Error, 'invalide|détruit|reset'):
                            verify_program(reset, allow_legacy_reset=True)

    def test_async_loop_carries_replaced_outer_receiver(self):
        source = """
            async fn tick(mut value: -> Int) -> <- Int {
                yield;
                value.set(*value + 1);
                return <- value;
            }
            async fn run(replacement: -> Int, mut value: -> Int) -> <- Int {
                let mut i = 0;
                loop {
                    value ->;
                    i = i + 1;
                    value = tick(-> value).await;
                    <- value;
                    if i == 1 { continue; }
                    if i == 3 { break; }
                }
                print(*value);
                loop {
                    replacement ->;
                    value = <- replacement;
                    break;
                }
                return <- value;
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = p.new(5);
                let b = p.new(30);
                let h = runtime::spawn(-> run(-> b, -> a));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let first = p.new(15);
                let second = p.new(17);
                print(first);
                print(second);
            }
        """
        run = self.run_c_oracle(compile_source(source))
        self.assertEqual(run.stdout, '8\n30\n15\n17\n')
        destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(destroyed, ['destroy a=8', 'destroy b=30', 'destroy second=17', 'destroy first=15'])
        with self.assertRaisesRegex(Error, 'sorties de boucle async'):
            verify_program(source.replace('loop {\n                    replacement ->;',
                                          'while i < 4 {\n                    replacement ->;'))
        for count in (0, 3):
            with self.subTest(iterations=count):
                program = source.replace('loop {', f'while i < {count} {{', 1).replace(
                    'loop {\n                    replacement ->;\n                    value = <- replacement;'
                    '\n                    break;\n                }', '',
                ).replace(
                    'let b = p.new(30);', 'let mut q = pool<Int>(1); let b = q.new(30);',
                ).replace('Ok(x) => { print(x); }', 'Ok(x) => { q.reset(); print(x); }')
                run = self.run_c_oracle(compile_source(program, allow_legacy_reset=True))
                result = 5 + count
                self.assertEqual(run.stdout, f'{result}\n{result}\n15\n17\n')

    def test_async_fixed_array_elements_are_stable_and_reserved(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(*n + 1); return *n; }
            async fn parent(i: Int) -> Int {
                let mut a: [Int; 2] = [10, 20];
                let child = runtime::spawn(-> edit(&mut a[INDEX]));
                a[1] = 21;
                yield;
                match child.await {
                    Ok(n) => { return n + a[0] + a[1]; },
                    Err(_) => { return 99; }
                }
            }
            fn main() {
                let h = runtime::spawn(-> parent(ARG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        program = source.replace('INDEX', '0').replace('ARG', '0')
        self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '43\n')
        shared = program.replace('n: &mut Int', 'n: &Int').replace('n.set(*n + 1); ', '').replace(
            'edit(&mut a[0])', 'edit(&a[0])',
        ).replace('a[1] = 21;', 'print(a[0]); a[1] = 21;')
        self.assertEqual(self.run_c_oracle(compile_source(shared)).stdout, '10\n41\n')
        dynamic = source.replace('INDEX', 'i').replace('a[1] = 21;', '').replace('ARG', '0')
        self.assertEqual(self.run_c_oracle(compile_source(dynamic)).stdout, '42\n')
        self.run_c_oracle(compile_source(dynamic.replace('parent(0)', 'parent(2)')), 'indice hors limites')
        for bad, diagnostic in (
            (program.replace('a[1] = 21;', 'a[0] = 21;'), 'emprunt actif'),
            (source.replace('INDEX', 'i').replace('ARG', '0'), 'emprunt actif'),
            (program.replace('let mut a:', 'let a:'), 'immuable'),
            (program.replace('&mut a[0]', '&mut a[2]'), 'hors limites'),
            (program.replace('a[1] = 21;', 'a[1] = 21; return 0;')
                    .split('                yield;')[0] + '} fn main() {}', 'attente requise'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad)
        returned_loan = """
            async fn lend(n: &mut Int) -> &mut Int { yield; return n; }
            async fn parent() -> Int {
                let mut a = [10, 20];
                let mut view = lend(&mut a[0]).await;
                a[1] = 21;
                CHECK
                view.set(12);
                return a[0] + a[1];
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(returned_loan.replace('CHECK', ''))).stdout, '33\n')
        rhs = returned_loan.replace('CHECK\n                view.set(12);', 'a[0] = *view + 2;')
        self.assertEqual(self.run_c_oracle(compile_source(rhs)).stdout, '33\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(returned_loan.replace('CHECK', 'print(a[0]);'))
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program("""
                async fn read(n: &Int) { yield; print(*n); }
                async fn parent() {
                    let child = { let a = [10]; let pending = read(&a[0]); <- pending };
                    child.await;
                }
                fn main() {}
            """)

    def test_async_nested_array_capture_checks_path_and_index_order(self):
        source = """
            async fn index() -> Int { print(77); yield; return 0; }
            async fn edit(n: &mut Int) { yield; n.set(*n + 1); }
            async fn parent(i: Int) -> Int {
                let mut a: [[Int; 2]; 2] = [[10, 20], [30, 40]];
                let child = runtime::spawn(-> edit(&mut a[i][index().await]));
                WRITE
                match child.await {
                    Ok(()) => { return a[0][0] + a[1][1]; },
                    Err(_) => { return 99; }
                }
            }
            fn main() {
                let h = runtime::spawn(-> parent(ARG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        dynamic = source.replace('WRITE', '').replace('ARG', '0')
        self.assertEqual(self.run_c_oracle(compile_source(dynamic)).stdout, '77\n51\n')
        out_of_bounds = dynamic.replace('parent(0)', 'parent(2)')
        run = self.run_c_oracle(compile_source(out_of_bounds), 'indice hors limites')
        self.assertEqual(run.stdout, '')
        projected = source.replace('index().await]', '0]').replace('ARG', '0')
        valid = projected.replace('WRITE', 'a[1][1] = 41;')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '52\n')
        for bad, diagnostic in (
            (projected.replace('WRITE', 'a[1][0] = 41;'), 'emprunt actif'),
            (valid.replace('a[i][0]', 'a[i][2]'), 'hors limites'),
            (valid.replace('[[10, 20], [30, 40]]', '[[10, 20], [30]]'), 'dimensions incompatibles'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad)

    def test_async_borrowed_row_reserves_only_its_projection(self):
        source = """
            async fn read(n: &Int) -> Int { yield; return *n; }
            async fn edit(row: &mut [Int; 2]) {
                let before = read(&row[0]).await;
                row[0] = before + 1;
                yield;
                row[1] = row[1] + 2;
            }
            async fn parent() -> Int {
                let mut a = [[10, 20], [30, 40]];
                let child = runtime::spawn(-> edit(&mut a[0]));
                a[1][0] = 31;
                yield;
                match child.await {
                    Ok(()) => { return a[0][0] + a[0][1] + a[1][0]; },
                    Err(_) => { return 99; }
                }
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '64\n')
        relayed = source.replace('async fn parent() -> Int {', '''
            async fn relay(row: &mut [Int; 2]) { edit(&mut *row).await; }
            async fn parent() -> Int {
        ''').replace('spawn(-> edit(&mut a[0]))', 'spawn(-> relay(&mut a[0]))')
        self.assertEqual(self.run_c_oracle(compile_source(relayed)).stdout, '64\n')
        shared = source.replace(
            'async fn edit(row: &mut [Int; 2]) {',
            'async fn edit(row: &[Int; 2]) {',
        ).replace('row[0] = before + 1;', 'print(before);').replace(
            'row[1] = row[1] + 2;', '',
        ).replace('edit(&mut a[0])', 'edit(&a[0])')
        self.assertEqual(self.run_c_oracle(compile_source(shared)).stdout, '10\n61\n')
        for bad, diagnostic in (
            (source.replace('a[1][0] = 31;', 'a[0][1] = 31;'), 'emprunt actif'),
            (source.replace('edit(&mut a[0])', 'edit(&mut a[0][0])'), 'dimensions incompatibles'),
            (source.replace('let mut a =', 'let a ='), 'immuable'),
            (source.replace('row: &mut', 'row: &'), 'immuable'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad)

    def test_async_borrowed_row_can_return_an_element_reference(self):
        source = """
            async fn lend(row: &mut [Int; 2]) -> &mut Int {
                yield;
                return &mut row[1];
            }
            async fn relay(row: &mut [Int; 2]) -> &mut Int {
                return lend(&mut *row).await;
            }
            async fn parent() -> Int {
                let mut table = [[10, 20], [30, 40]];
                let mut element = relay(&mut table[0]).await;
                table[1][0] = 31;
                CHECK
                element.set(22);
                table[0][0] = 11;
                return table[0][0] + table[0][1] + table[1][0];
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        disjoint = source.replace('CHECK', 'table[0][0] = 11;')
        self.assertEqual(self.run_c_oracle(compile_source(disjoint)).stdout, '64\n')
        via_cell = 'async fn cell(n: &mut Int) -> &mut Int { return n; }' + disjoint.replace(
            'return &mut row[1];', 'return cell(&mut row[1]).await;',
        )
        self.assertEqual(self.run_c_oracle(compile_source(via_cell)).stdout, '64\n')
        joined = disjoint.replace(
            'let mut element = relay(&mut table[0]).await;',
            'let h = runtime::spawn(-> relay(&mut table[0])); match h.await { Ok(element) => {',
        ).replace(
            'return table[0][0] + table[0][1] + table[1][0];',
            'return table[0][0] + table[0][1] + table[1][0]; } Err(_) => { return 99; } }',
        )
        self.assertEqual(self.run_c_oracle(compile_source(joined)).stdout, '64\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(table[0][1]);'))
        conditional = disjoint.replace(
            'return &mut row[1];',
            'if row[0] > 0 { return &mut row[1]; } return &mut row[0];',
        )
        dynamic = disjoint.replace('return &mut row[1];', 'let i = 1; return &mut row[i];')
        for unresolved in (conditional, dynamic):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(unresolved)
        local = source.replace('return &mut row[1];', 'let mut local = [0]; return &mut local[0];').replace('CHECK', '')
        with self.assertRaisesRegex(Error, 'paramètre mutable durable'):
            verify_program(local)
        shared = source.replace('&mut [Int;', '&[Int;').replace('&mut Int', '&Int').replace(
            '&mut row[1]', '&row[1]',
        ).replace('&mut *row', '&*row').replace('&mut table[0]', '&table[0]').replace(
            'element.set(22);', 'print(*element);',
        )
        self.assertEqual(self.run_c_oracle(compile_source(shared.replace('CHECK', ''))).stdout, '20\n62\n')

    def test_sync_tableau_capture_survives_spawn_and_releases_at_join(self):
        source = """
            async fn edit(row: &mut [Int; 2]) { yield; row[0] = 12; }
            fn main() {
                let mut table = [[10, 20], [30, 40]];
                let child = { let t = edit(&mut table[0]); <- t };
                BEFORE
                let h = runtime::spawn(-> child);
                RUN
                print(table[0][0]);
            }
        """
        joined = 'match h.join() { Ok(()) => {}, Err(_) => { print(99); } }'
        program = source.replace('BEFORE', '').replace('RUN', joined)
        self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '12\n')
        disjoint = source.replace('BEFORE', 'table[1][0] = 31;').replace(
            'RUN', 'print(table[1][0]); ' + joined,
        )
        self.assertEqual(self.run_c_oracle(compile_source(disjoint)).stdout, '31\n12\n')
        cell = program.replace(
            'edit(row: &mut [Int; 2]) { yield; row[0] = 12; }',
            'edit(n: &mut Int) { yield; n.set(12); }',
        ).replace('edit(&mut table[0])', 'edit(&mut table[0][0])')
        self.assertEqual(self.run_c_oracle(compile_source(cell)).stdout, '12\n')
        two_cells = cell.replace('let h = runtime::spawn(-> child);', '''
            let other = runtime::spawn(-> edit(&mut table[0][1]));
            let h = runtime::spawn(-> child);
            match other.join() { Ok(()) => {}, Err(_) => { print(99); } }
        ''').replace('print(table[0][0]);', 'print(table[0][0]); print(table[0][1]);')
        self.assertEqual(self.run_c_oracle(compile_source(two_cells)).stdout, '12\n12\n')
        alias = cell.replace(
            'let t = edit(&mut table[0][0]);',
            'let row = &mut table[0]; let t = edit(&mut row[0]);',
        ).replace(joined, 'table[0][1] = 22; ' + joined).replace(
            'print(table[0][0]);', 'print(table[0][0]); print(table[0][1]);',
        )
        self.assertEqual(self.run_c_oracle(compile_source(alias)).stdout, '12\n22\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(alias.replace('table[0][1] = 22;', 'table[0][0] = 22;'))
        inactive = program.replace('let h = runtime::spawn(-> child);', 'drop(-> child);').replace(joined, '')
        self.assertEqual(self.run_c_oracle(compile_source(inactive)).stdout, '10\n')
        for bad, diagnostic in (
            (source.replace('BEFORE', 'print(table[0][0]);').replace('RUN', joined), 'emprunt actif'),
            (source.replace('BEFORE', '').replace('RUN', 'print(table[0][0]); ' + joined), 'emprunt actif'),
            (program.replace(joined, 'drop(-> h);'), 'join requis'),
            (program.replace('let t = edit(&mut table[0]);', 'let mut local = [0, 0]; let t = edit(&mut local);'),
             'cible empruntée non durable'),
            (disjoint.replace('let t = edit(&mut table[0]);', 'let i = 0; let t = edit(&mut table[i]);'),
             'emprunt actif'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad)

    def test_sync_join_returns_an_inline_array_element(self):
        source = """
            async fn lend(row: &mut [Int; 2]) -> &mut Int { yield; return &mut row[1]; }
            fn main() {
                let mut table = [[10, 20], [30, 40]];
                let h = runtime::spawn(-> lend(&mut table[0]));
                let result = h.join();
                table[0][0] = 11;
                BEFORE
                match result {
                    Ok(view) => {
                        table[0][0] = 12;
                        DURING
                        *view = 23;
                    },
                    Err(_) => { print(99); }
                }
                print(table[0][0]);
                print(table[0][1]);
            }
        """
        program = source.replace('BEFORE', '').replace('DURING', '')
        self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '12\n23\n')
        direct = program.replace('let result = h.join();', '').replace('table[0][0] = 11;', '').replace(
            'match result {', 'match h.join() {',
        )
        self.assertEqual(self.run_c_oracle(compile_source(direct)).stdout, '12\n23\n')
        failure = program.replace('Err(_) => { print(99); }', 'Err(_) => { table[0][1] = 24; }')
        failed_launch = compile_source(failure).replace('#include <pthread.h>', '#include <pthread.h>\n'
                                                      '#define pthread_create(thread, attr, runner, pointer) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed_launch).stdout, '11\n24\n')
        for position in ('BEFORE', 'DURING'):
            bad = source.replace(position, 'table[0][1] = 22;').replace('BEFORE', '').replace('DURING', '')
            with self.subTest(position=position), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad)
        shared = program.replace('&mut [Int;', '&[Int;').replace('&mut Int', '&Int').replace(
            '&mut row[1]', '&row[1]',
        ).replace('&mut table[0]', '&table[0]').replace('*view = 23;', 'print(*view);')
        self.assertEqual(self.run_c_oracle(compile_source(shared)).stdout, '20\n12\n20\n')

    def test_sync_join_borrow_can_choose_inline_or_pool_storage(self):
        source = """
            async fn pick(row: &mut [Int; 2], fallback: &mut Int, flag: Int) -> &mut Int {
                yield;
                if flag == 0 { return &mut row[1]; }
                return fallback;
            }
            fn main() {
                let mut table = [10, 20];
                let mut p = pool<Int>(1);
                let mut value = p.new(30);
                let h = runtime::spawn(-> pick(&mut table, &mut value, FLAG));
                let result = h.join();
                BEFORE
                match result {
                    Ok(view) => {
                        table[0] = 11;
                        DURING
                        *view = 23;
                    },
                    Err(_) => { print(99); }
                }
                print(table[0]);
                print(table[1]);
                print(value);
            }
        """
        for flag, expected in (('0', '11\n23\n30\n'), ('1', '11\n20\n23\n')):
            with self.subTest(flag=flag):
                program = source.replace('FLAG', flag)
                valid = program.replace('BEFORE', '').replace('DURING', '')
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, expected)
                recaptured = 'async fn pass(n: &mut Int) -> &mut Int { yield; return n; }' + valid.replace(
                    '*view = 23;', '''
                    let second = runtime::spawn(-> pass(view));
                    table[0] = 11;
                    match second.join() {
                        Ok(again) => { table[0] = 11; *again = 23; },
                        Err(_) => { print(99); }
                    }
                    ''',
                )
                self.assertEqual(self.run_c_oracle(compile_source(recaptured)).stdout, expected)
                for operation in ('table[1] = 21;', 'value = 31;'):
                    bad = recaptured.replace('match second.join()', f'{operation} match second.join()')
                    with self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(bad)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(recaptured.replace('match second.join()', 'p.reset(); match second.join()'),
                                   allow_legacy_reset=True)
                for position in ('BEFORE', 'DURING'):
                    for operation in ('table[1] = 21;', 'value = 31;'):
                        bad = program.replace(position, operation).replace('BEFORE', '').replace('DURING', '')
                        with self.assertRaisesRegex(Error, 'emprunt actif'):
                            verify_program(bad)
        shared = source.replace('-> &mut Int {', '-> &Int {').replace(
            'return &mut row[1];', 'return &row[1];',
        ).replace('return fallback;', 'return &*fallback;').replace(
            '*view = 23;', 'print(*view);',
        ).replace('FLAG', '1').replace('BEFORE', '')
        self.assertEqual(self.run_c_oracle(compile_source(shared.replace('DURING', ''))).stdout,
                         '30\n11\n20\n30\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(shared.replace('DURING', 'print(value);'))

    def test_sync_contract_relays_task_with_array_capture(self):
        source = """
            async fn edit(row: &mut [Int; 2]) { yield; row[0] = 12; }
            fn relay(t: -> edit) -> <- edit { return <- t; }
            fn launch(t: -> edit) -> <- Execution<edit> {
                let h = runtime::spawn(-> t);
                return <- h;
            }
            fn finish(h: -> Execution<edit>) {
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
            }
            fn main() {
                let mut table = [[10, 20], [30, 40]];
                let task = relay(-> edit(&mut table[0]));
                BEFORE
                let h = launch(-> task);
                table[1][0] = 31;
                DURING
                finish(-> h);
                print(table[0][0]);
                print(table[1][0]);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '12\n31\n')
        stopped = valid.replace(
            'let h = launch(-> task);', 'stop(-> task);',
        ).replace('finish(-> h);', '')
        stop = 'fn stop(t: -> edit) { drop(-> t); }' + stopped
        self.assertEqual(self.run_c_oracle(compile_source(stop)).stdout, '10\n31\n')
        two_args = 'fn stop(t: -> edit, other: &mut Int) { drop(-> t); other.set(41); }' + stopped.replace(
            'stop(-> task);', 'stop(-> task, &mut table[1][0]);',
        ).replace('table[1][0] = 31;', '')
        self.assertEqual(self.run_c_oracle(compile_source(two_args)).stdout, '10\n41\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(two_args.replace('stop(-> task, &mut table[1][0]);', 'stop(-> task, &mut table[0][0]);'))
        for position in ('BEFORE', 'DURING'):
            bad = source.replace(position, 'table[0][0] = 13;').replace('BEFORE', '').replace('DURING', '')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad)
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(valid.replace(
                'match h.join() { Ok(()) => {}, Err(_) => { print(99); } }', 'drop(-> h);',
            ))

    def test_factory_returns_task_borrowing_array_parameter(self):
        source = """
            async fn edit(row: &mut [Int; 2]) -> &mut Int {
                yield;
                row[0] = 12;
                return &mut row[1];
            }
            fn factory(row: &mut [Int; 2]) -> <- edit {
                let t = edit(row);
                return <- t;
            }
            fn relay(row: &mut [Int; 2]) -> <- edit {
                let t = factory(row);
                return <- t;
            }
            fn main() {
                let mut table = [[10, 20], [30, 40]];
                let t = relay(&mut table[0]);
                BEFORE
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => { DURING *view = 13; },
                    Err(_) => { print(99); }
                }
                print(table[0][0]);
                print(table[0][1]);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '12\n13\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n10\n20\n')
        for position in ('BEFORE', 'DURING'):
            bad = source.replace(position, 'table[1][0] = 15;')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad.replace('BEFORE', '').replace('DURING', ''))
        local = valid.replace('let t = relay(&mut table[0]);',
                              'let t = { let mut row = [1, 2]; '
                              'let pending = relay(&mut row); <- pending };')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(local)

        shared = source.replace('&mut', '&').replace('row[0] = 12;', '').replace('*view = 13;', 'print(*view);')
        readable = shared.replace('BEFORE', 'print(table[1][0]);').replace('DURING', '')
        self.assertEqual(self.run_c_oracle(compile_source(readable)).stdout, '30\n20\n10\n20\n')
        for position in ('BEFORE', 'DURING'):
            bad = shared.replace(position, 'table[0][1] = 15;')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad.replace('BEFORE', '').replace('DURING', ''))

    def test_factory_captures_shared_reference_before_array_slot_replacement(self):
        source = """
            async fn read(n: &Int) -> &Int { yield; return n; }
            fn prepare(row: &mut [&Int; 1], replacement: &Int) -> <- read {
                let t = read(&*row[0]);
                let old = row.replace(0, replacement);
                print(*old);
                return <- t;
            }
            fn relay(row: &mut [&Int; 1], replacement: &Int) -> <- read {
                UPDATE
                let t = prepare(row, replacement);
                return <- t;
            }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let n = first.new(7);
                let other = second.new(9);
                let mut row = [&n];
                let t = relay(&mut row, &other);
                BEFORE
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => { DURING print(*view); },
                    Err(_) => { print(99); }
                }
            }
        """
        for update, captured, other, pool, expected in (
                ('', 'n', 'other', 'first', '7\n7\n'),
                ('let old = row.replace(0, replacement); print(*old);', 'other', 'n', 'second', '7\n9\n9\n')):
            with self.subTest(captured=captured):
                program = source.replace('UPDATE', update)
                valid = program.replace('BEFORE', f'drop(-> {other});').replace('DURING', '')
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, expected)
                for position in ('BEFORE', 'DURING'):
                    bad = program.replace(position, f'drop(-> {captured});')
                    with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                        verify_program(bad.replace('BEFORE', '').replace('DURING', ''))
                bad = program.replace('BEFORE', f'{pool}.reset();').replace('DURING', '')
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(bad, allow_legacy_reset=True)

    def test_factory_retains_reborrow_of_stored_mutable_reference(self):
        source = """
            async fn edit(n: &mut Int) -> &mut Int { yield; n.set(8); return n; }
            fn prepare(row: &mut [&mut Int; 2]) -> <- edit {
                let t = edit(&mut *row[0]);
                return <- t;
            }
            fn relay(row: &mut [&mut Int; 2]) -> <- edit {
                let t = prepare(row);
                return <- t;
            }
            fn main() {
                let mut p = pool<Int>(2);
                let mut n = p.new(7);
                let mut m = p.new(4);
                let mut row = [&mut n, &mut m];
                let t = relay(&mut row);
                BEFORE
                *row[1] = 12;
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => { DURING *row[1] = 13; *view = 9; },
                    Err(_) => { print(99); }
                }
                *row[0] = 10;
                print(n);
                print(m);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '10\n13\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n10\n12\n')
        for position in ('BEFORE', 'DURING'):
            for operation in ('*row[0] = 15;', 'row.swap(0, 1);'):
                bad = source.replace(position, operation).replace('BEFORE', '').replace('DURING', '')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(bad)
            bad = source.replace(position, 'p.reset();').replace('BEFORE', '').replace('DURING', '')
            with self.assertRaisesRegex(Error, 'reset interdit'):
                verify_program(bad, allow_legacy_reset=True)
        shared = source.replace('edit(n: &mut Int) -> &mut Int { yield; n.set(8);',
                                'edit(n: &Int) -> &Int { yield;')
        shared = shared.replace('edit(&mut *row[0])', 'edit(&*row[0])').replace('*view = 9;', 'print(*view);')
        self.assertEqual(self.run_c_oracle(compile_source(shared.replace('BEFORE', '').replace('DURING', ''))).stdout,
                         '7\n10\n13\n')
        for position in ('BEFORE', 'DURING'):
            bad = shared.replace(position, 'print(n);').replace('BEFORE', '').replace('DURING', '')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad)

    def test_factory_retains_all_dynamic_stored_reference_origins(self):
        source = """
            async fn edit(n: &mut Int) -> &mut Int { yield; n.set(8); return n; }
            fn prepare(row: &mut [&mut Int; 2], index: Int) -> <- edit {
                let t = edit(&mut *row[index]);
                return <- t;
            }
            fn relay(row: &mut [&mut Int; 2], index: Int) -> <- edit {
                let t = prepare(row, index);
                return <- t;
            }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let mut n = first.new(7);
                let mut m = second.new(4);
                let mut row = [&mut n, &mut m];
                let t = relay(&mut row, INDEX);
                BEFORE
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => { DURING *view = 9; },
                    Err(_) => { print(99); }
                }
                print(n);
                print(m);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        nested = valid.replace('[&mut Int; 2]', '[&mut [&mut Int; 1]; 2]').replace('row[index]', 'row[index][0]')
        nested = nested.replace('let mut row = [&mut n, &mut m];',
                                'let mut a = [&mut n]; let mut b = [&mut m]; let mut row = [&mut a, &mut b];')
        for index in (0, 1):
            with self.subTest(index=index):
                expected = [7, 4]
                expected[index] = 9
                for program in (valid, nested):
                    code = compile_source(program.replace('INDEX', str(index)))
                    self.assertEqual(self.run_c_oracle(code).stdout, ''.join(f'{value}\n' for value in expected))
        for index in ('-1', '2'):
            self.run_c_oracle(compile_source(valid.replace('INDEX', index)), 'indice hors limites')
        for position in ('BEFORE', 'DURING'):
            for operation in ('*row[0] = 15;', '*row[1] = 15;', 'row.swap(0, 1);'):
                bad = source.replace(position, operation).replace('BEFORE', '').replace('DURING', '')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(bad.replace('INDEX', '0'))
            for pool in ('first', 'second'):
                bad = source.replace(position, f'{pool}.reset();').replace('BEFORE', '').replace('DURING', '')
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(bad.replace('INDEX', '0'), allow_legacy_reset=True)

    def test_spawn_captures_shared_reference_row_and_its_targets(self):
        source = """
            async fn read(row: &[&Int; 2], i: Int) -> Int {
                yield;
                return *row[i] + row.len();
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = p.new(7);
                let b = p.new(9);
                let mut row = [&a, &b];
                let h = runtime::spawn(-> read(&row, INDEX));
                CHECK
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                drop(-> a);
                drop(-> b);
            }
        """
        for index, expected in ((0, '9\n'), (1, '11\n')):
            valid = source.replace('INDEX', str(index)).replace('CHECK', '')
            self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, expected)
        valid = source.replace('INDEX', '1')
        shared = valid.replace('CHECK', 'print(*row[0]);')
        self.assertEqual(self.run_c_oracle(compile_source(shared)).stdout, '7\n11\n')
        for name in ('a', 'b'):
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                bad = valid.replace(f'\n                drop(-> {name});', '')
                verify_program(bad.replace('CHECK', f'drop(-> {name});'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('CHECK', 'let previous = row.replace(0, &b); print(*previous);'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(valid.replace('CHECK', 'p.reset();'), allow_legacy_reset=True)
        self.run_c_oracle(compile_source(source.replace('INDEX', '2').replace('CHECK', '')), 'indice hors limites')
        escaped = valid.replace('let mut row = [&a, &b];\n                let h = runtime::spawn(-> read(&row, 1));',
                                'let pending = { let row = [&a, &b]; let t = read(&row, 1); <- t };\n'
                                'let h = runtime::spawn(-> pending);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaped.replace('CHECK', ''))

    def test_factory_relay_captures_shared_reference_row_after_update(self):
        source = """
            async fn read(row: &[&Int; 2]) -> Int { yield; return *row[1]; }
            fn prepare(row: &mut [&Int; 2], replacement: &Int) -> <- read {
                UPDATE
                let task = read(&*row);
                AFTER
                return <- task;
            }
            fn relay(row: &mut [&Int; 2], replacement: &Int) -> <- read {
                let task = prepare(row, replacement);
                return <- task;
            }
            fn main() {
                let mut p = pool<Int>(3);
                let a = p.new(7);
                let b = p.new(9);
                let c = p.new(12);
                let mut row = [&a, &b];
                let task = relay(&mut row, &c);
                CHECK
                let h = runtime::spawn(-> task);
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
            }
        """
        update = 'let old = row.replace(1, replacement); print(*old);'
        valid = source.replace('UPDATE', update).replace('AFTER', '')
        code = compile_source(valid.replace('CHECK', 'drop(-> b);'))
        self.assertEqual(self.run_c_oracle(code).stdout, '9\n12\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '9\n99\n')
        for name in ('a', 'c'):
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(valid.replace('CHECK', f'drop(-> {name});'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('UPDATE', '').replace('AFTER', update).replace('CHECK', ''))

    def test_async_parent_relays_shared_reference_row_to_child(self):
        source = """
            async fn read(row: &[&Int; 2]) -> Int { yield; return *row[1]; }
            async fn parent(row: &[&Int; 2]) -> Int {
                let t = read(row);
                let h = runtime::spawn(-> t);
                yield;
                let value = match h.await { Ok(n) => { n }, Err(_) => { 100 } };
                return value + *row[0];
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = p.new(7);
                let b = p.new(9);
                let row = [&a, &b];
                let h = runtime::spawn(-> parent(&row));
                CHECK
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('CHECK', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '16\n')
        failure = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failure).stdout, '107\n')
        inline = valid.replace('let h = runtime::spawn(-> t);', '').replace(
            'let value = match h.await { Ok(n) => { n }, Err(_) => { 100 } };', 'let value = t.await;')
        self.assertEqual(self.run_c_oracle(compile_source(inline)).stdout, '16\n')
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(valid.replace('let value = match h.await { Ok(n) => { n }, Err(_) => { 100 } };',
                                         'let value = 0;'))
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(source.replace('CHECK', 'drop(-> b);'))
        with self.assertRaisesRegex(Error, 'tableau de références du type déclaré'):
            verify_program(valid.replace('async fn read(row: &[&Int; 2]) -> Int { yield; return *row[1]; }',
                                         'async fn read(row: &[&Int; 1]) -> Int { yield; return *row[0]; }'))

    def test_async_mutable_reference_row_is_reserved_through_child_await(self):
        source = """
            async fn edit(row: &mut [&mut Int; 2], i: Int) -> Int {
                yield;
                if i > 0 { *row[i] = 12; }
                return *row[i];
            }
            async fn parent(row: &mut [&mut Int; 2], i: Int) -> Int {
                let t = edit(row, i);
                INSIDE
                let value = t.await;
                return value + *row[0];
            }
            fn main() {
                let mut p = pool<Int>(2);
                let mut a = p.new(7);
                let mut b = p.new(9);
                let mut row = [&mut a, &mut b];
                let h = runtime::spawn(-> parent(&mut row, INDEX));
                OUTSIDE
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                print(*row[1]);
            }
        """
        valid = source.replace('INSIDE', '').replace('OUTSIDE', '')
        for index, expected in ((0, '14\n9\n'), (1, '19\n12\n')):
            self.assertEqual(self.run_c_oracle(compile_source(valid.replace('INDEX', str(index)))).stdout, expected)
        self.run_c_oracle(compile_source(valid.replace('INDEX', '2')), 'indice hors limites')
        for position, operation in (('INSIDE', 'print(*row[0]);'), ('OUTSIDE', 'print(*row[0]);'),
                                    ('OUTSIDE', '*row[1] = 15;'), ('OUTSIDE', 'row.swap(0, 1);')):
            bad = source.replace(position, operation).replace('INSIDE', '').replace('OUTSIDE', '')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad.replace('INDEX', '1'))

    def test_async_child_reborrows_stored_scalar_reference(self):
        source = """
            async fn edit(n: &mut Int) -> &mut Int { yield; n.set(12); return n; }
            async fn parent(row: &mut [&mut Int; 2], i: Int) -> Int {
                let t = edit(&mut *row[i]);
                BEFORE
                let mut view = t.await;
                AFTER
                view.set(15);
                return *row[0] + *row[1];
            }
            fn main() {
                let mut p = pool<Int>(2);
                let mut a = p.new(7);
                let mut b = p.new(9);
                let mut row = [&mut a, &mut b];
                let h = runtime::spawn(-> parent(&mut row, INDEX));
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                print(*row[0]);
                print(*row[1]);
            }
        """
        valid = source.replace('BEFORE', '').replace('AFTER', '')
        for index, expected in ((0, '24\n15\n9\n'), (1, '22\n7\n15\n')):
            self.assertEqual(self.run_c_oracle(compile_source(valid.replace('INDEX', str(index)))).stdout, expected)
        for position in ('BEFORE', 'AFTER'):
            bad = source.replace(position, 'print(*row[0]);').replace('BEFORE', '').replace('AFTER', '')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad.replace('INDEX', '0'))
        self.run_c_oracle(compile_source(valid.replace('INDEX', '2')), 'indice hors limites')

    def test_join_projects_result_from_reference_row(self):
        source = """
            async fn read(row: &[&Int; 2], i: Int) -> &Int {
                yield;
                return &*row[SLOT];
            }
            async fn relay(row: &[&Int; 2], i: Int) -> &Int {
                return read(row, i).await;
            }
            fn main() {
                let mut p = pool<Int>(2);
                let mut a = p.new(7);
                let b = p.new(9);
                let mut row = [&a, &b];
                let h = runtime::spawn(-> relay(&row, 1));
                match h.join() {
                    Ok(view) => {
                        let old = row.replace(0, &b);
                        print(*old);
                        CHECK
                        print(*view);
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        constant = source.replace('SLOT', '1')
        self.assertEqual(self.run_c_oracle(compile_source(constant.replace('CHECK', 'a.set(13);'))).stdout,
                         '7\n9\n')
        dynamic = source.replace('SLOT', 'i')
        self.assertEqual(self.run_c_oracle(compile_source(dynamic.replace('CHECK', ''))).stdout, '7\n9\n')
        with self.assertRaisesRegex(Error, 'emprunt actif|emprunt encore utilisé'):
            verify_program(dynamic.replace('CHECK', 'a.set(13);'))
        mutable = constant.replace('&[&Int; 2]', '&mut [&mut Int; 2]').replace('-> &Int', '-> &mut Int')
        mutable = mutable.replace('&*row[1]', '&mut *row[1]').replace('let b =', 'let mut b =')
        mutable = mutable.replace('[&a, &b]', '[&mut a, &mut b]').replace('relay(&row, 1)', 'relay(&mut row, 1)')
        mutable = mutable.replace('let old = row.replace(0, &b);\n                        print(*old);', '*row[0] = 13;')
        mutable = mutable.replace('print(*view);', '*view = 11; print(*view);')
        self.assertEqual(self.run_c_oracle(compile_source(mutable.replace('CHECK', ''))).stdout, '11\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(mutable.replace('CHECK', '*row[1] = 14;'))

    def test_sync_join_returns_stored_reference_through_contract(self):
        source = """
            async fn read(row: &[&Int; 2], i: Int) -> &Int { return &*row[SLOT]; }
            fn finish(row: &[&Int; 2], fallback: &Int) -> &Int {
                let h = runtime::spawn(-> read(row, 1));
                match h.join() {
                    Ok(view) => { return view; },
                    Err(_) => { return fallback; }
                }
            }
            fn relay(row: &[&Int; 2], fallback: &Int) -> &Int { return finish(row, fallback); }
            fn main() {
                let mut p = pool<Int>(3);
                let mut a = p.new(7);
                let mut b = p.new(9);
                let mut backup = p.new(12);
                let row = [&a, &b];
                let view = relay(&row, &backup);
                CHECK
                print(*view);
            }
        """
        constant = source.replace('SLOT', '1')
        code = compile_source(constant.replace('CHECK', 'a.set(13);'))
        self.assertEqual(self.run_c_oracle(code).stdout, '9\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '12\n')
        for program, name in ((constant, 'b'), (constant, 'backup'), (source.replace('SLOT', 'i'), 'a')):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(program.replace('CHECK', f'{name}.set(13);'))
        mutable = constant.replace('&[&Int; 2]', '&mut [&mut Int; 2]').replace('&Int', '&mut Int')
        mutable = mutable.replace('&*row[1]', '&mut *row[1]').replace('let row = [&a, &b];',
                                                                    'let mut row = [&mut a, &mut b];')
        mutable = mutable.replace('let view = relay(&row, &backup);',
                                  'let mut view = relay(&mut row, &mut backup);')
        self.assertEqual(self.run_c_oracle(compile_source(
            mutable.replace('CHECK', '*row[0] = 13; *view = 15;'))).stdout, '15\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(mutable.replace('CHECK', '*row[1] = 13;'))
        factory = source.replace('fn finish(', """
            fn factory(row: &[&Int; 2]) -> <- read {
                let task = read(row, 1);
                return <- task;
            }
            fn forward(task: -> read) -> <- read { return <- task; }
            fn finish(""").replace('spawn(-> read(row, 1))', 'spawn(-> forward(-> factory(row)))')
        factory_constant = factory.replace('SLOT', '1')
        self.assertEqual(self.run_c_oracle(compile_source(
            factory_constant.replace('CHECK', 'a.set(13);'))).stdout, '9\n')
        for program, name in ((factory_constant, 'b'), (factory.replace('SLOT', 'i'), 'a')):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(program.replace('CHECK', f'{name}.set(13);'))
        updated = factory_constant.replace('fn factory(row: &[&Int; 2])',
                                           'fn factory(row: &mut [&Int; 2], replacement: &Int)')
        updated = updated.replace('let task = read(row, 1);',
                                  'let old = row.replace(1, replacement); print(*old); let task = read(&*row, 1);')
        updated = updated.replace('row: &[&Int; 2], fallback:', 'row: &mut [&Int; 2], fallback:')
        updated = updated.replace('factory(row)', 'factory(row, fallback)').replace('relay(&row, &backup)',
                                                                                   'relay(&mut row, &backup)')
        updated = updated.replace('let row = [&a, &b];', 'let mut row = [&a, &b];')
        self.assertEqual(self.run_c_oracle(compile_source(updated.replace('CHECK', 'b.set(13);'))).stdout,
                         '9\n12\n')

    def test_async_join_preserves_nested_reference_coordinates(self):
        source = """
            async fn read(grid: &[[&Int; 2]; 2], i: Int) -> &Int {
                yield;
                return &*grid[i][1];
            }
            fn factory(grid: &[[&Int; 2]; 2], i: Int) -> <- read {
                let task = read(grid, i);
                return <- task;
            }
            fn finish(grid: &[[&Int; 2]; 2], i: Int, backup: &Int) -> &Int {
                let h = runtime::spawn(-> factory(grid, i));
                match h.join() {
                    Ok(view) => { return view; },
                    Err(_) => { return backup; }
                }
            }
            fn main() {
                let mut p = pool<Int>(5);
                let mut a = p.new(7);
                let mut b = p.new(9);
                let mut c = p.new(11);
                let mut d = p.new(13);
                let backup = p.new(15);
                let grid = [[&a, &b], [&c, &d]];
                let view = finish(&grid, INDEX, &backup);
                a.set(17);
                c.set(19);
                CHECK
                print(*view);
            }
        """
        for index, expected in ((0, '9\n'), (1, '13\n')):
            program = source.replace('INDEX', str(index)).replace('CHECK', '')
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, expected)
        for name in ('b', 'd'):
            program = source.replace('INDEX', '0').replace('CHECK', f'{name}.set(21);')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(program)
        bad_index = source.replace('INDEX', '2').replace('CHECK', '')
        self.run_c_oracle(compile_source(bad_index), 'indice hors limites')
        mutable = source.replace('&[[&Int; 2]; 2]', '&mut [[&mut Int; 2]; 2]').replace('-> &Int', '-> &mut Int')
        mutable = mutable.replace('backup: &Int', 'backup: &mut Int').replace('return &*grid', 'return &mut *grid')
        mutable = mutable.replace('let backup =', 'let mut backup =').replace('let grid = [[&a, &b], [&c, &d]];',
                                                                            'let mut grid = [[&mut a, &mut b], [&mut c, &mut d]];')
        mutable = mutable.replace('let view = finish(&grid, INDEX, &backup);',
                                  'let mut view = finish(&mut grid, INDEX, &mut backup);')
        mutable = mutable.replace('a.set(17);', '*grid[0][0] = 17;').replace('c.set(19);', '*grid[1][0] = 19;')
        mutable = mutable.replace('CHECK', '*view = 21;').replace('INDEX', '1')
        self.assertEqual(self.run_c_oracle(compile_source(mutable)).stdout, '21\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(mutable.replace('*grid[1][0] = 19;', '*grid[1][1] = 19;'))
        relayed = source.replace('async fn read(grid: &[[&Int; 2]; 2], i: Int) -> &Int {',
                                 'async fn leaf(row: &[&Int; 2]) -> &Int {')
        relayed = relayed.replace('return &*grid[i][1];', 'return &*row[1];')
        relayed = relayed.replace('fn factory(', """
            async fn read(grid: &[[&Int; 2]; 2], i: Int) -> &Int {
                return leaf(&grid[i]).await;
            }
            fn factory(""")
        for index, expected in (('0', '9\n'), ('1', '13\n')):
            program = relayed.replace('INDEX', index).replace('CHECK', '')
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, expected)
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(relayed.replace('INDEX', '0').replace('CHECK', 'd.set(21);'))
        self.run_c_oracle(compile_source(relayed.replace('INDEX', '2').replace('CHECK', '')),
                          'indice hors limites')
        mutable_relay = mutable.replace('async fn read(grid: &mut [[&mut Int; 2]; 2], i: Int) -> &mut Int {',
                                        'async fn leaf(row: &mut [&mut Int; 2]) -> &mut Int {')
        mutable_relay = mutable_relay.replace('return &mut *grid[i][1];', 'return &mut *row[1];')
        mutable_relay = mutable_relay.replace('fn factory(', """
            async fn read(grid: &mut [[&mut Int; 2]; 2], i: Int) -> &mut Int {
                let child = leaf(&mut grid[i]);
                CHECK_PARENT
                return child.await;
            }
            fn factory(""")
        self.assertEqual(self.run_c_oracle(compile_source(mutable_relay.replace('CHECK_PARENT', ''))).stdout, '21\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(mutable_relay.replace('CHECK_PARENT', 'print(*grid[0][0]);'))

    def test_async_capture_follows_referenced_rows(self):
        source = """
            async fn read(grid: &[&[&Int; 1]; 2], i: Int) -> &Int {
                yield;
                return &*grid[i][0];
            }
            fn factory(grid: &[&[&Int; 1]; 2], i: Int) -> <- read {
                let t = read(grid, i);
                return <- t;
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = p.new(7);
                let b = p.new(9);
                let mut x = [&a];
                let y = [&b];
                let grid = [&x, &y];
                let h = runtime::spawn(-> factory(&grid, INDEX));
                CHECK
                match h.join() {
                    Ok(view) => { print(*view); },
                    Err(_) => { print(99); }
                }
            }
        """
        for index, expected in (('0', '7\n'), ('1', '9\n')):
            program = source.replace('INDEX', index).replace('CHECK', '')
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, expected)
        valid = source.replace('INDEX', '1')
        for operation in ('drop(-> a);', 'drop(-> b);'):
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(valid.replace('CHECK', operation))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('CHECK', 'let old = x.replace(0, &b); print(*old);'))
        self.run_c_oracle(compile_source(source.replace('INDEX', '2').replace('CHECK', '')), 'indice hors limites')
        mutable = valid.replace('&[&[&Int; 1]; 2]', '&mut [&mut [&mut Int; 1]; 2]')
        mutable = mutable.replace('-> &Int', '-> &mut Int').replace('&*grid', '&mut *grid')
        mutable = mutable.replace('let a =', 'let mut a =').replace('let b =', 'let mut b =')
        mutable = mutable.replace('[&a]', '[&mut a]').replace('let y = [&b]', 'let mut y = [&mut b]')
        mutable = mutable.replace('let grid = [&x, &y]', 'let mut grid = [&mut x, &mut y]')
        mutable = mutable.replace('factory(&grid, 1)', 'factory(&mut grid, 1)')
        mutable = mutable.replace('print(*view);', '*view = 12; print(*view);')
        self.assertEqual(self.run_c_oracle(compile_source(mutable.replace('CHECK', ''))).stdout, '12\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(mutable.replace('CHECK', '*grid[0][0] = 13;'))
        synchronous = valid.replace('grid[i][0]', 'grid[1][0]').replace('let a =', 'let mut a =')
        synchronous = synchronous.replace('fn main()', """
            fn finish(grid: &[&[&Int; 1]; 2], backup: &Int) -> &Int {
                let h = runtime::spawn(-> factory(grid, 1));
                match h.join() {
                    Ok(view) => { return view; },
                    Err(_) => { return backup; }
                }
            }
            fn main()""")
        start = synchronous.index('let h = runtime::spawn(-> factory(&grid, 1));')
        synchronous = synchronous[:start] + 'let view = finish(&grid, &b); a.set(13); print(*view); }'
        self.assertEqual(self.run_c_oracle(compile_source(synchronous)).stdout, '9\n')

    def test_async_mixed_reference_rows_respect_shared_boundaries(self):
        source = """
            async fn read(grid: &mut [&[&mut Int; 1]; 1]) -> &Int {
                yield;
                WORKER
                return &*grid[0][0];
            }
            fn main() {
                let mut p = pool<Int>(1);
                let mut a = p.new(7);
                let row = [&mut a];
                let mut grid = [&row];
                let h = runtime::spawn(-> read(&mut grid));
                match h.join() {
                    Ok(view) => { AFTER print(*view); },
                    Err(_) => { print(99); }
                }
                print(a);
            }
        """
        valid = source.replace('WORKER', '').replace('AFTER', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '7\n7\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('WORKER', '').replace('AFTER', 'print(a);'))
        for operation in ('*grid[0][0] = 13;', 'let t = edit(&mut *grid[0][0]); t.await;'):
            bad = source.replace('WORKER', operation).replace('AFTER', '')
            bad = 'async fn edit(n: &mut Int) { n.set(13); }\n' + bad
            with self.assertRaisesRegex(Error, 'écriture interdite à travers une référence partagée'):
                verify_program(bad)
        shared_leaf = valid.replace('&mut [&[&mut Int; 1]; 1]', '&[&mut [&Int; 1]; 1]')
        shared_leaf = shared_leaf.replace('let row = [&mut a];', 'let mut row = [&a];')
        shared_leaf = shared_leaf.replace('let mut grid = [&row];', 'let grid = [&mut row];')
        shared_leaf = shared_leaf.replace('read(&mut grid)', 'read(&grid)')
        self.assertEqual(self.run_c_oracle(compile_source(shared_leaf)).stdout, '7\n7\n')

    def test_empty_array_borrow_survives_async_relay(self):
        source = """
            async fn count(row: &[ITEM; 0]) -> Int { yield; return row.len(); }
            async fn relay(row: &[ITEM; 0]) -> Int { return count(row).await; }
            fn main() {
                let row: [ITEM; 0] = [];
                let h = runtime::spawn(-> relay(&row));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for item, access in (('Int', 'row[0]'), ('&Int', '*row[0]')):
            with self.subTest(item=item):
                program = source.replace('ITEM', item)
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '0\n')
                with self.assertRaisesRegex(Error, 'hors limites'):
                    verify_program(program.replace('return row.len();', f'return {access};'))
                nested = program.replace(f'let row: [{item}; 0] = [];',
                                         f'let rows: [[{item}; 0]; 2] = [[], []];')
                nested = nested.replace('relay(&row)', 'relay(&rows[1])')
                self.assertEqual(self.run_c_oracle(compile_source(nested)).stdout, '0\n')
                with self.assertRaisesRegex(Error, 'longueur zéro'):
                    verify_program(nested.replace(f'[[{item}; 0]; 2] =', f'[[{item}; 1]; 2] ='))
                typ = f'[[{item}; 0]; 2]'
                for body in ('return <- [[], []];', f'let local: {typ} = [[], []]; return <- local;'):
                    returned = f'fn make() -> {typ} {{ {body} }}\n' + nested.replace(
                        f'let rows: {typ} = [[], []];', 'let rows = make();')
                    self.assertEqual(self.run_c_oracle(compile_source(returned)).stdout, '0\n')
        invalid = """
            fn make() -> [[&Int; 1]; 2] { return <- [[], []]; }
            fn main() { let rows = make(); }
        """
        with self.assertRaisesRegex(Error, 'longueur zéro|attendu array_refs'):
            verify_program(invalid)
        plain = source.replace('ITEM', 'Int')
        with self.assertRaisesRegex(Error, 'longueur zéro'):
            verify_program(plain.replace('let row: [Int; 0]', 'let row: [Int; 1]'))
        with self.assertRaisesRegex(Error, 'annotation de let'):
            verify_program(plain.replace('let row: [Int; 0] = [];', 'let row: [Int; 0] = [1];'))

    def test_signature_types_nested_empty_array_arguments(self):
        source = """
            fn identity(rows: INPUT [[ITEM; 0]; 2]) -> [[ITEM; 0]; 2] {
                return <- rows;
            }
            fn relay() -> [[ITEM; 0]; 2] {
                let rows = identity(ARGUMENT [[], []]);
                return <- rows;
            }
            async fn count(row: &[ITEM; 0]) -> Int { yield; return row.len(); }
            fn main() {
                let rows = relay();
                let h = runtime::spawn(-> count(&rows[1]));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for item, transfer in (('Int', ''), ('&Int', ''), ('&mut Int', '->')):
            with self.subTest(item=item):
                program = source.replace('ITEM', item).replace('INPUT', transfer).replace('ARGUMENT', transfer)
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '0\n')
                with self.assertRaisesRegex(Error, 'longueur|attend un tableau'):
                    verify_program(program.replace('[[], []]', '[[]]'))
        missing_transfer = source.replace('ITEM', '&mut Int').replace('INPUT', '->').replace('ARGUMENT', '')
        with self.assertRaisesRegex(Error, 'transfert -> requis'):
            verify_program(missing_transfer)

    def test_signature_types_temporary_nested_array_borrow(self):
        source = """
            fn inspect(rows: MODE [[ITEM; 0]; 2]) -> Int { return rows.len(); }
            fn main() { print(inspect(MODE [[], []])); }
        """
        for item in ('Int', '&Int'):
            for mode in ('&', '&mut'):
                program = source.replace('ITEM', item).replace('MODE', mode)
                with self.subTest(item=item, mode=mode):
                    self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '2\n')
                    with self.assertRaisesRegex(Error, 'longueur|attend un tableau'):
                        verify_program(program.replace('[[], []]', '[[]]'))
            escape = f"""
                fn identity(rows: &[[{item}; 0]; 2]) -> &[[{item}; 0]; 2] {{ return rows; }}
                fn main() {{ let escaped = identity(&[[], []]); print(escaped.len()); }}
            """
            with self.assertRaisesRegex(Error, 'tableau temporaire'):
                verify_program(escape)

    def test_if_receivers_type_nested_empty_array_branches(self):
        source = """
            fn make(flag: Int) -> [[ITEM; 0]; 2] {
                RECEIVER if flag > 0 { <- [[], []] } else { <- [[], []] };
                RETURN
            }
            async fn count(row: &[ITEM; 0]) -> Int { return row.len(); }
            fn main() {
                let a = make(0);
                let b = make(1);
                let h = runtime::spawn(-> count(&a[0]));
                let j = runtime::spawn(-> count(&b[1]));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                match j.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for item in ('Int', '&Int'):
            for receiver, returned in (('let rows: [[ITEM; 0]; 2] =', 'return <- rows;'),
                                       ('return <-', '')):
                program = source.replace('RECEIVER', receiver).replace('RETURN', returned).replace('ITEM', item)
                with self.subTest(item=item, receiver=receiver):
                    self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '0\n0\n')
                    with self.assertRaisesRegex(Error, 'longueur|même type'):
                        verify_program(program.replace('else { <- [[], []] }', 'else { <- [[]] }'))
                    with self.assertRaisesRegex(Error, 'transférée par <-'):
                        verify_program(program.replace('else { <- [[], []] }', 'else { [[], []] }'))

    def test_loop_receivers_type_nested_empty_array_breaks(self):
        source = """
            fn make(flag: Int) -> [[ITEM; 0]; 2] {
                let mut iteration = 0;
                RECEIVER loop {
                    if iteration == 0 { iteration = 1; continue; }
                    if flag > 0 { break <- [[], []]; }
                    break <- [[], []];
                };
                RETURN
            }
            async fn count(row: &[ITEM; 0]) -> Int { return row.len(); }
            fn main() {
                let a = make(0);
                let b = make(1);
                let h = runtime::spawn(-> count(&a[0]));
                let j = runtime::spawn(-> count(&b[1]));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                match j.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for item in ('Int', '&Int'):
            for receiver, returned in (('let rows: [[ITEM; 0]; 2] =', 'return <- rows;'), ('return <-', '')):
                program = source.replace('RECEIVER', receiver).replace('RETURN', returned).replace('ITEM', item)
                with self.subTest(item=item, receiver=receiver):
                    self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '0\n0\n')
                    with self.assertRaisesRegex(Error, 'longueur|même type'):
                        verify_program(program.replace('break <- [[], []];', 'break <- [[]];', 1))
                    with self.assertRaisesRegex(Error, 'transfert de tableau par <- requis'):
                        verify_program(program.replace('break <- [[], []];', 'break [[], []];', 1))

    def test_match_receivers_type_nested_empty_array_arms(self):
        source = """
            async fn child() -> Int { return 1; }
            fn make() -> [[&Int; 0]; 2] {
                let h = runtime::spawn(-> child());
                return <- match h.join() {
                    Ok(_) => { print(7); <- [[], []] },
                    Err(_) => { print(9); <- [[], []] }
                };
            }
            fn length(rows: &[[&Int; 0]; 2]) -> Int { return rows.len(); }
            fn main() { let rows = make(); print(length(&rows)); }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '7\n2\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '9\n2\n')
        with self.assertRaisesRegex(Error, 'longueur|même type'):
            verify_program(source.replace('print(9); <- [[], []]', 'print(9); <- [[]]'))
        with self.assertRaisesRegex(Error, 'transférée par <-'):
            verify_program(source.replace('print(9); <- [[], []]', 'print(9); [[], []]'))
        nominal = """
            enum Choice { Yes, No }
            fn main() {
                let mut pool = pool<Choice>(1);
                let choice = new(pool) Choice.Yes;
                let rows: [[Int; 0]; 2] = match &choice {
                    Choice.Yes => { <- [[], []] },
                    Choice.No => { <- [[], []] }
                };
                print(length(&rows));
            }
            fn length(rows: &[[Int; 0]; 2]) -> Int { return rows.len(); }
        """
        self.assertEqual(self.run_c_oracle(compile_source(nominal)).stdout, '2\n')

    def test_block_receiver_types_empty_rows_and_checks_reference_lifetime(self):
        source = """
            fn make() -> [[ITEM; 0]; 2] {
                let rows: [[ITEM; 0]; 2] = { <- [[], []] };
                return <- rows;
            }
            fn length(rows: &[[ITEM; 0]; 2]) -> Int { return rows.len(); }
            fn main() { let rows = make(); print(length(&rows)); }
        """
        for item in ('Int', '&Int'):
            program = source.replace('ITEM', item)
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '2\n')
            with self.assertRaisesRegex(Error, 'longueur|attendu'):
                verify_program(program.replace('{ <- [[], []] }', '{ <- [[]] }'))
        parent = """
            fn main() {
                let a = [7];
                let rows = { <- [&a[0]] };
                print(*rows[0]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(parent)).stdout, '7\n')
        local = parent.replace('let a = [7];', '').replace('{ <- [&a[0]] }', '{ let a = [7]; <- [&a[0]] }')
        with self.assertRaisesRegex(Error, 'tableau emprunté non durable'):
            verify_program(local)

    def test_sync_nested_int_array_capture_preserves_storage_and_projection(self):
        source = """
            async fn edit(grid: &mut [[Int; 2]; 2]) -> &mut Int {
                yield;
                grid.swap(0, 1);
                grid[0][0] = 17;
                return &mut grid[0][1];
            }
            async fn relay(grid: &mut [[Int; 2]; 2]) -> &mut Int {
                return edit(grid).await;
            }
            fn main() {
                let mut grid = [[1, 2], [3, 4]];
                let h = runtime::spawn(-> relay(&mut grid));
                BEFORE
                match h.join() {
                    Ok(view) => { grid[1][0] = 13; DURING *view = 9; },
                    Err(_) => { print(99); }
                }
                print(grid[0][0]);
                print(grid[0][1]);
                print(grid[1][0]);
                print(grid[1][1]);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '17\n9\n13\n2\n')
        for position, operation in (('BEFORE', 'grid[1][0] = 7;'), ('DURING', 'grid[0][1] = 7;')):
            bad = source.replace(position, operation).replace('BEFORE', '').replace('DURING', '')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad)
        copied = valid.replace('grid.swap(0, 1);', 'let old = copy(grid[1]);')
        copied = copied.replace('grid[0][0] = 17;', 'grid[0][0] = old[0];')
        self.assertEqual(self.run_c_oracle(compile_source(copied)).stdout, '3\n9\n13\n4\n')

    def test_nested_int_borrowed_layout_matches_list_model(self):
        template = """
            async fn edit(grid: &mut [[Int; WIDTH]; HEIGHT], i: Int) -> Int {
                yield;
                let old = grid.replace(i, REPLACEMENT);
                grid.swap(0, LAST);
                return old[0] + grid[0][WIDTH_LAST] * 10 + grid[LAST][0] * 100;
            }
            async fn native(i: Int) -> Int {
                let mut grid = INITIAL;
                return edit(&mut grid, i).await;
            }
            fn main() {
                let mut grid = INITIAL;
                let h = runtime::spawn(-> edit(&mut grid, INDEX));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                let j = runtime::spawn(-> native(INDEX));
                match j.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                PRINT_GRID
            }
        """
        for height, width, index in ((2, 3, 1), (3, 2, 1), (4, 3, 2)):
            with self.subTest(height=height, width=width, index=index):
                grid = [[1 + row * width + column for column in range(width)] for row in range(height)]
                replacement = list(range(20, 20 + width))
                prints = ' '.join(f'print(grid[{row}][{column}]);'
                                  for row in range(height) for column in range(width))
                program = (template.replace('WIDTH_LAST', str(width - 1)).replace('WIDTH', str(width))
                           .replace('HEIGHT', str(height)).replace('LAST', str(height - 1))
                           .replace('REPLACEMENT', str(replacement)).replace('INITIAL', str(grid))
                           .replace('PRINT_GRID', prints))
                old = grid[index]
                grid[index] = replacement
                grid[0], grid[-1] = grid[-1], grid[0]
                result = old[0] + grid[0][-1] * 10 + grid[-1][0] * 100
                expected = [result, result, *(value for row in grid for value in row)]
                code = compile_source(program.replace('INDEX', str(index)))
                self.assertEqual(self.run_c_oracle(code).stdout, ''.join(f'{value}\n' for value in expected))
                if height == 2:
                    invalid = compile_source(program.replace('INDEX', str(height)))
                    self.run_c_oracle(invalid, 'indice hors limites')

    def test_async_bool_capture_is_typed_and_copied_at_creation(self):
        source = """
            async fn leaf(flag: Bool) -> Int {
                yield;
                if flag { return 7; }
                return 9;
            }
            async fn relay(flag: Bool) -> Int { return leaf(flag).await; }
            fn main() {
                let mut enabled = true;
                let task = relay(enabled);
                enabled = false;
                let h = runtime::spawn(-> task);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                if enabled { print(88); }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')
        self.assertEqual(self.run_c_oracle(compile_source(
            source.replace('let mut enabled = true;', 'let mut enabled = false;'))).stdout, '9\n')
        for before, after, diagnostic in (
                ('relay(enabled)', 'relay(1)', 'capture async Bool'),
                ('leaf(flag).await', 'leaf(1).await', 'valeur Bool'),
                ('return 7;', 'return flag + 1;', 'valeur Int'),
                ('if flag {', 'if flag > false {', 'comparaison async incompatible')):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_int_borrow_cannot_reinterpret_a_bool_frame_member(self):
        source = """
            async fn write(value: &mut Int) {
                yield;
                value.set(42);
            }
            async fn read(value: &Int) -> Int {
                yield;
                return *value;
            }
            async fn relay(flag: Bool) -> Int {
                let mut local = 1;
                write(&mut local).await;
                return read(&local).await;
            }
            fn main() {
                let h = runtime::spawn(-> relay(false));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '42\n')
        for before, after in (
                ('let mut local = 1;', 'let mut local = flag;'),
                ('read(&local)', 'read(&flag)')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, 'emprunt Int.*Bool'):
                verify_program(source.replace(before, after))

    def test_async_byte_capture_copies_before_start_and_preserves_type(self):
        source = """
            async fn leaf(byte: u8) -> Int { yield; return 7; }
            async fn relay(byte: u8) -> Int { return leaf(byte).await; }
            async fn inspect(value: &Int) -> Int { return *value; }
            fn main() {
                let mut text = "é";
                let task = relay(text[1]);
                text = "ab";
                let h = runtime::spawn(-> task);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        code = compile_source(source)
        resume = 'resume_1: ;'
        self.assertIn(resume, code)
        # The public async subset cannot consume u8 in an Int expression.
        # Observe the byte in the leaf frame after its first suspension.
        code = code.replace(resume, resume + '\n    if (frame->value_0 != 169) abort();', 1)
        self.assertEqual(self.run_c_oracle(code).stdout, '7\n')
        # A literal receives the declared u8 context, as in synchronous
        # calls. A named Int does not narrow implicitly (covered below).
        for before, after in (('relay(text[1])', 'relay(169)'),
                              ('leaf(byte).await', 'leaf(169).await')):
            literal_code = compile_source(source.replace(before, after))
            literal_code = literal_code.replace(resume, resume + '\n    if (frame->value_0 != 169) abort();', 1)
            self.assertEqual(self.run_c_oracle(literal_code).stdout, '7\n')
        for before, after, diagnostic in (
                ('relay(text[1])', 'relay(256)', 'u8'),
                ('leaf(byte).await', 'leaf(256).await', 'u8'),
                ('leaf(byte).await', 'inspect(&byte).await', 'emprunt Int'),
                ('return 7;', 'return byte + 1;', 'valeur Int')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_local_byte_survives_yield_and_keeps_lexical_type(self):
        source = """
            async fn leaf(byte: u8) -> Int { yield; return 7; }
            async fn relay(first: u8, second: u8) -> Int {
                let mut saved: u8 = first;
                if true {
                    let local = second;
                    yield;
                    saved = local;
                }
                let local = 3;
                let chosen: u8 = loop {
                    if true { break saved; }
                    break second;
                };
                return leaf(chosen).await + local;
            }
            fn main() {
                let h = runtime::spawn(-> relay("ab"[1], "é"[1]));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        resume = 'resume_1: ;'
        code = compile_source(source)
        self.assertIn(resume, code)
        instrumented = code.replace(resume, resume + '\n    if (frame->value_0 != 169) abort();', 1)
        self.assertEqual(self.run_c_oracle(instrumented).stdout, '10\n')
        literal = source.replace('saved: u8 = first', 'saved: u8 = 3').replace('saved = local;', '')
        literal_code = compile_source(literal).replace(
            resume, resume + '\n    if (frame->value_0 != 3) abort();', 1)
        self.assertEqual(self.run_c_oracle(literal_code).stdout, '10\n')
        for before, after, diagnostic in (
                ('saved: u8 = first', 'saved: u8 = 256', 'u8'),
                ('saved = local', 'saved = 256', 'opération u8'),
                ('let mut saved', 'let saved', 'receveur mutable'),
                ('if true {', 'if first == second {', 'comparaison async incompatible'),
                ('break second;', 'break local;', 'break async doivent fournir le même type'),
                ('leaf(chosen).await + local', 'leaf(local).await', 'capture async u8')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_byte_result_crosses_await_and_thread_join(self):
        source = """
            async fn leaf(byte: u8) -> u8 { yield; return byte; }
            async fn relay(byte: u8) -> u8 {
                let x: u8 = leaf(byte).await;
                return leaf(x).await;
            }
            async fn outer(byte: u8, fallback: u8) -> u8 {
                let h = runtime::spawn(-> relay(byte));
                return match h.await { Ok(x) => { x }, Err(_) => { fallback } };
            }
            fn main() {
                let h = runtime::spawn(-> outer("é"[1], "a"[0]));
                match h.join() {
                    Ok(n) => { let result: u8 = n; let echo = leaf(result); drop(-> echo); print(7); },
                    Err(_) => { print(99); }
                }
            }
        """
        code = compile_source(source)
        instrumented, count = re.subn(
            r'(uint8_t (\w+) = \(\w+\)\.byte_value;)',
            r'\1 if (\2 != 169) abort();', code)
        self.assertEqual(count, 1)
        self.assertEqual(self.run_c_oracle(instrumented).stdout, '7\n')
        inner_failure = instrumented.replace('!= 169) abort();', '!= 97) abort();')
        inner_failure = inject_submission_failure(inner_failure)
        self.assertEqual(self.run_c_oracle(inner_failure).stdout, '7\n')
        outer_failure = instrumented.replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(outer_failure).stdout, '99\n')
        literal_code = compile_source(source.replace('yield; return byte;', 'yield; return 169;'))
        literal_code, count = re.subn(
            r'(uint8_t (\w+) = \(\w+\)\.byte_value;)',
            r'\1 if (\2 != 169) abort();', literal_code)
        self.assertEqual(count, 1)
        self.assertEqual(self.run_c_oracle(literal_code).stdout, '7\n')
        for before, after, diagnostic in (
                ('yield; return byte;', 'yield; return 256;', 'u8'),
                ('let x: u8 = leaf(byte).await', 'let x: Int = leaf(byte).await', 'receveur u8'),
                ('Ok(x) => { x }', 'Ok(x) => { 7 }', 'même type scalaire'),
                ('let result: u8 = n', 'let result: Int = n', 'annotation de let')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_byte_join_survives_handle_transfer_and_sync_return(self):
        source = """
            async fn work(x: u8) -> u8 { yield; return x; }
            async fn observe(x: u8) -> Int { yield; return 7; }
            fn launch(x: u8) -> <- Execution<work> {
                let h = runtime::spawn(-> work(x));
                return <- h;
            }
            fn finish(h: -> Execution<work>, fallback: u8) -> u8 {
                return match h.join() { Ok(n) => { n }, Err(_) => { fallback } };
            }
            fn main() {
                let h = launch("é"[1]);
                let result = finish(-> h, "a"[0]);
                let reader = runtime::spawn(-> observe(result));
                match reader.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        code = compile_source(source)
        # Observe the result after it has crossed the synchronous return and
        # been captured into a different task.
        resume = 'crust_async_observe_resume(CrustTask *task) {'
        prefix, marker, observer = code.partition(resume)
        self.assertTrue(marker)
        probe = 'resume_1: ;'
        self.assertIn(probe, observer)
        code = prefix + marker + observer.replace(probe, probe + '\n    if (frame->value_0 != 169) abort();', 1)
        self.assertEqual(self.run_c_oracle(code).stdout, '7\n')
        failed_launch = code.replace('!= 169) abort();', '!= 97) abort();')
        failed_launch = failed_launch.replace(
            '#include <pthread.h>',
            '#include <pthread.h>\nstatic int starts;\n'
            '#define pthread_create(t,a,r,p) (++starts == 1 ? EAGAIN : pthread_create(t,a,r,p))', 1)
        self.assertEqual(self.run_c_oracle(failed_launch).stdout, '7\n')
        for before, after, diagnostic in (
                ('let result = finish', 'let result: Int = finish', 'annotation de let'),
                ('Ok(n) => { n }', 'Ok(n) => { 7 }', 'même type'),
                ('let reader =', 'let again = finish(-> h, "a"[0]); let reader =', 'plus utilisable|transfert|consomm')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_char_capture_keeps_unicode_scalar_through_yield(self):
        source = """
            async fn width(c: char) -> Int { yield; return c.utf8_len(); }
            async fn read(n: &Int) -> Int { return *n; }
            async fn relay(c: char) -> Int { return width(c).await; }
            fn report(t: &str) {
                match t.char_at(0) {
                    Ok(c) => {
                        let h = runtime::spawn(-> relay(c));
                        match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                    },
                    Err(CharAtError::OutOfBounds) => { print(98); },
                    Err(CharAtError::NotCharBoundary) => { print(97); }
                }
            }
            fn main() { report("a"); report("é"); report("€"); report("🌍"); }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '1\n2\n3\n4\n')
        for before, after, diagnostic in (
                ('relay(c));', 'relay(t[0]));', 'capture async char'),
                ('width(c).await', 'width(65).await', 'capture async char'),
                ('width(c).await', 'read(&c).await', 'emprunt Int.*char'),
                ('fn relay(c: char) -> Int {', 'fn relay(mut c: char) -> Int { c = 65;', 'affectation char'),
                ('c.utf8_len()', 'c + 1', 'Int.*char'),
                ('c.utf8_len()', 'c.utf8_len(1)', 'aucun argument')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_local_char_preserves_type_across_control_flow(self):
        source = """
            async fn width(c: char) -> Int { return c.utf8_len(); }
            async fn relay(c: char) -> Int {
                let mut saved: char = c;
                {
                    let local = c;
                    yield;
                    saved = local;
                }
                let local = 1;
                let selected: char = loop {
                    if true { break saved; }
                    break c;
                };
                let result = if true { selected } else { c };
                return width(result).await + local;
            }
            fn main() {
                match "🌍".char_at(0) {
                    Ok(c) => {
                        let h = runtime::spawn(-> relay(c));
                        match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                    },
                    Err(CharAtError::OutOfBounds) => { print(98); },
                    Err(CharAtError::NotCharBoundary) => { print(97); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '5\n')
        for before, after, diagnostic in (
                ('saved: char = c', 'saved: char = 65', 'liaison char'),
                ('saved = local', 'saved = 65', 'affectation char'),
                ('break c;', 'break local;', 'break async doivent fournir le même type'),
                ('else { c }', 'else { local }', 'même type scalaire'),
                ('width(result)', 'width(local)', 'capture async char')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_char_result_survives_direct_await_and_thread_join(self):
        source = """
            async fn work(c: char) -> char { yield; return c; }
            async fn relay(c: char) -> char {
                let task = work(c);
                let saved: char = task.await;
                if true { print(saved); }
                print(work(saved).await);
                return saved;
            }
            async fn outer(c: char) -> char {
                let h = runtime::spawn(-> relay(c));
                return match h.await { Ok(value) => { value }, Err(_) => { c } };
            }
            fn main() {
                match "🌍".char_at(0) {
                    Ok(c) => {
                        let h = runtime::spawn(-> outer(c));
                        match h.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                    },
                    Err(CharAtError::OutOfBounds) => { print(98); },
                    Err(CharAtError::NotCharBoundary) => { print(97); }
                }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '🌍\n🌍\n🌍\n')
        failure = code.replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failure).stdout, '99\n')
        for before, after, diagnostic in (
                ('yield; return c;', 'yield; return 65;', 'retour char'),
                ('let saved: char', 'let saved: u8', 'opération u8'),
                ('print(saved);', 'print(true);', 'print async exige'),
                ('print(work(saved).await);', 'print(task.await);', 'déjà consommée'),
                ('Ok(value) => { value }', 'Ok(value) => { 65 }', 'même type scalaire')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_static_text_capture_preserves_bytes_through_yield(self):
        source = r"""
            async fn show(t: &str) -> Int {
                yield;
                if true { print(t); }
                return t.byte_len();
            }
            async fn relay(t: &str) -> Int {
                print("é\u0000🌍");
                return show(t).await;
            }
            fn main() {
                let h = runtime::spawn(-> relay("a\u0000é"));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'é\0🌍\na\0é\n4\n')
        for before, after, diagnostic in (
                ('show(t).await', 'show(1).await', '&str statique'),
                ('return t.byte_len()', 'return t', 'Int.*&str'),
                (r'relay("a\u0000é")', 'relay(&s[..])', 'emprunt encore utilisé')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                candidate = source.replace(before, after)
                if after == 'relay(&s[..])':
                    candidate = candidate.replace('fn main() {',
                        'fn main() { let mut p = pool<String>(1); let s = p.new();')
                    candidate = candidate.replace('match h.join()', 'drop(-> s); match h.join()')
                verify_program(candidate)

    def test_async_static_text_local_slice_evaluates_bounds_in_order(self):
        source = """
            async fn bound(n: Int) -> Int { print(n); yield; return n; }
            async fn width(t: &str) -> Int { yield; print(t); return t.byte_len(); }
            async fn relay(t: &str) -> Int {
                let mut saved: &str = "";
                {
                    let local = &t[bound(1).await..bound(3).await];
                    saved = local;
                    yield;
                }
                let local = 4;
                return width(saved).await + local;
            }
            fn main() {
                let h = runtime::spawn(-> relay("aé🌍"));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '1\n3\né\n6\n')
        dynamic = compile_source(source.replace('bound(3)', 'bound(2)'))
        self.run_c_oracle(dynamic, 'octet de continuation')
        for before, after, diagnostic in (
                ('&t[bound(1).await..bound(3).await]', '&"é"[..1]', 'octet de continuation'),
                ('saved = local;', 'saved = 1;', '&str statique'),
                ('width(saved)', 'width(local)', '&str statique')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_capture_proves_immutable_static_text_aliases(self):
        source = """
            async fn show(t: &str) -> Int { yield; print(t); return t.byte_len(); }
            fn literal() -> &str { return "é🌍"; }
            fn cut(t: &str, fallback: &str, flag: Int) -> &str {
                if flag == 1 { return &t[2..]; }
                return fallback;
            }
            fn prepare() -> <- show {
                let original = literal();
                let view: &str = cut(original, "secours", 1);
                let alias = view;
                let task = show(alias);
                return <- task;
            }
            fn main() {
                let task = prepare();
                let h = runtime::spawn(-> task);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '🌍\n4\n')
        mutable = source.replace('let alias = view;', 'let mut alias = view;')
        self.assertEqual(self.run_c_oracle(compile_source(mutable)).stdout, '🌍\n4\n')
        borrowed = 'let mut strings = pool<String>(1); let s = strings.new();'
        parameter = source.replace('fn prepare()', 'fn prepare(original: &str)').replace(
            'let original = literal();', '')
        for origin, candidate in (
                ('borrowed', source.replace('let original = literal();', borrowed + ' let original = &s[..];')),
                ('mixed', source.replace('let view: &str = cut(original, "secours", 1);',
                                         borrowed + ' let view: &str = cut(original, &s[..], 1);')),
                ('parameter', parameter.replace('let task = prepare();',
                                                borrowed + ' let task = prepare(&s[..]);')
                                       .replace('match h.join()', 'drop(-> s); match h.join()'))):
            diagnostic = ('emprunt encore utilisé' if origin == 'parameter'
                          else 'cible empruntée non durable')
            with self.subTest(origin=origin), self.assertRaisesRegex(Error, diagnostic):
                verify_program(candidate)

    def test_async_static_text_control_results_keep_view_type(self):
        source = """
            async fn work() -> Int { yield; return 1; }
            async fn relay(flag: Bool, text: &str) -> Int {
                let chosen = if flag { text } else { "a" };
                let loop_view: &str = loop {
                    if flag { break chosen; }
                    break "é";
                };
                let h = runtime::spawn(-> work());
                let final_view: &str = match h.await {
                    Ok(n) => { loop_view },
                    Err(_) => { "!" }
                };
                print(final_view);
                return final_view.byte_len();
            }
            fn main() {
                let h = runtime::spawn(-> relay(true, "🌍"));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '🌍\n4\n')
        second_path = source.replace('relay(true', 'relay(false')
        self.assertEqual(self.run_c_oracle(compile_source(second_path)).stdout, 'é\n2\n')
        failed_inner_launch = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed_inner_launch).stdout, '!\n1\n')
        for before, after, diagnostic in (
                ('else { "a" }', 'else { 1 }', 'même type scalaire'),
                ('break "é";', 'break 1;', 'break async doivent fournir le même type'),
                ('Err(_) => { "!" }', 'Err(_) => { 1 }', 'même type scalaire')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_static_text_result_keeps_view_after_task_slot_release(self):
        source = r"""
            async fn leaf(t: &str) -> &str { yield; return &t[1..]; }
            async fn relay(t: &str) -> &str {
                let view: &str = leaf(t).await;
                let other = leaf("xy").await;
                print(other.byte_len());
                return view;
            }
            async fn outer(t: &str) -> &str {
                let h = runtime::spawn(-> relay(t));
                return match h.await { Ok(view) => { view }, Err(_) => { "secours" } };
            }
            async fn display(view: &str) { yield; print(view); }
            fn main() {
                let h = runtime::spawn(-> outer("xé\u0000🌍"));
                match h.join() {
                    Ok(view) => {
                        let h2 = runtime::spawn(-> display(view));
                        match h2.join() { Ok(()) => {}, Err(_) => { print(98); } }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '1\né\0🌍\n')
        failed_inner_launch = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed_inner_launch).stdout, 'secours\n')
        for before, after, diagnostic in (
                ('return &t[1..]', 'return 1', '&str statique'),
                ('let view: &str = leaf(t).await', 'let view: Int = leaf(t).await', 'Int.*&str'),
                ('Ok(view) => { view }', 'Ok(view) => { 1 }', 'même type scalaire')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_text_index_reads_continuation_after_ordered_suspensions(self):
        source = """
            async fn produce() -> &str { print(10); yield; return "é"; }
            async fn index() -> Int { print(20); yield; return 1; }
            async fn read() -> u8 {
                let byte = produce().await[index().await];
                return byte;
            }
            fn main() {
                let h = runtime::spawn(-> read());
                match h.join() {
                    Ok(byte) => {
                        let mut strings = pool<String>(1);
                        let mut s = strings.new();
                        s.push_str("è");
                        match s.replace_byte(1, byte) {
                            Ok(_) => { print(&s[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '10\n20\né\n')
        dynamic = source.replace('yield; return 1;', 'yield; return 2;')
        self.run_c_oracle(compile_source(dynamic), 'indice UTF-8 hors bornes')
        borrowed = source.replace(
            'async fn read() -> u8 {\n                let byte = produce().await[index().await];\n                return byte;',
            'async fn load(loan: &u8) -> u8 { yield; return *loan; }\n'
            '            async fn read(initial: &u8) -> u8 {\n'
            '                let mut loan: &u8 = initial;\n'
            '                loan = &produce().await[index().await];\n'
            '                return load(loan).await;'
        ).replace('-> read()', '-> read(&"x"[0])')
        self.assertEqual(self.run_c_oracle(compile_source(borrowed)).stdout, '10\n20\né\n')
        for before, after, diagnostic in (
                ('loan = &produce()', 'loan = produce()', '&u8.*statique'),
                ('-> read(&"x"[0])', '-> read("x"[0])', 'capture async &u8'),
                ('yield; return *loan;', 'yield; return loan;', 'opération u8')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(borrowed.replace(before, after))
        dynamic_borrow = borrowed.replace('let h = runtime::spawn(-> read(&"x"[0]));',
            'let mut strings = pool<String>(1); let mut s = strings.new(); s.push_str("x"); '
            'let h = runtime::spawn(-> read(&s[0]));')
        self.assertEqual(self.run_c_oracle(compile_source(dynamic_borrow)).stdout, '10\n20\né\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(dynamic_borrow.replace('match h.join()', 'drop(-> s); match h.join()'))
        for before, after, diagnostic in (
                ('produce().await[index().await]', '"é"[2]', 'indice UTF-8 hors bornes'),
                ('let byte =', 'let byte: Int =', 'Int.*u8'),
                ('index().await]', 'false]', 'valeur Int')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_static_byte_reference_result_survives_await_and_join(self):
        source = """
            async fn leaf(t: &str) -> &u8 { yield; return &t[1]; }
            async fn relay(t: &str) -> &u8 {
                let view: &u8 = leaf(t).await;
                let h = runtime::spawn(-> leaf("è"));
                return match h.await { Ok(other) => { other }, Err(_) => { view } };
            }
            async fn load(loan: &u8) -> u8 { yield; return *loan; }
            fn octet(t: &str) -> &u8 { return &t[1]; }
            fn display(byte: u8) {
                let mut strings = pool<String>(1);
                let mut s = strings.new();
                s.push_str("ê");
                match s.replace_byte(1, byte) {
                    Ok(_) => { print(&s[..]); },
                    Err(ByteReplaceError::OutOfBounds) => { print(98); },
                    Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                }
            }
            fn main() {
                let h = runtime::spawn(-> relay("é"));
                match h.join() {
                    Ok(loan) => {
                        let alias = loan;
                        let h2 = runtime::spawn(-> load(alias));
                        match h2.join() { Ok(byte) => { display(byte); }, Err(_) => { print(96); } }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, 'è\n')
        failed_inner_launch = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed_inner_launch).stdout, 'é\n')
        computed = source.replace('let view: &u8 = leaf(t).await;',
            'let view: &u8 = (if true { let a = leaf(t); <- a } '
            'else { let b = leaf("ê"); <- b }).await;')
        computed_failure = inject_submission_failure(compile_source(computed))
        self.assertEqual(self.run_c_oracle(computed_failure).stdout, 'é\n')
        named_literal = source.replace('let alias = loan;', 'let alias = octet("ê");')
        named_literal = named_literal.replace('Ok(loan) =>', 'Ok(_) =>')
        self.assertEqual(self.run_c_oracle(compile_source(named_literal)).stdout, 'ê\n')
        named_dynamic = named_literal.replace(
            'let alias = octet("ê");',
            'let mut strings = pool<String>(1); let mut s = strings.new(); '
            's.push_str("ê"); let alias = &s[1];')
        self.assertEqual(self.run_c_oracle(compile_source(named_dynamic)).stdout, 'ê\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(named_dynamic.replace('match h2.join()', 'drop(-> s); match h2.join()'))
        via_parameter = named_dynamic.replace('fn main() {', """
            fn read_sync(loan: &u8) {
                let h = runtime::spawn(-> load(loan));
                match h.join() { Ok(byte) => { display(byte); }, Err(_) => { print(96); } }
            }
            fn main() {
        """).replace(
            'let h2 = runtime::spawn(-> load(alias));\n'
            '                        match h2.join() { Ok(byte) => { display(byte); }, Err(_) => { print(96); } }',
            'read_sync(alias);')
        self.assertEqual(self.run_c_oracle(compile_source(via_parameter)).stdout, 'ê\n')
        projected_parameter = (via_parameter.replace('fn read_sync(loan: &u8)', 'fn read_sync(view: &str)')
                               .replace('load(loan));', 'load(&view[1]));')
                               .replace('let alias = &s[1];', '')
                               .replace('read_sync(alias);', 'read_sync(&s[..]);'))
        self.assertEqual(self.run_c_oracle(compile_source(projected_parameter)).stdout, 'ê\n')
        returned_dynamic = source.replace('let h = runtime::spawn(-> relay("é"));',
            'let mut strings = pool<String>(1); let mut s = strings.new(); s.push_str("ê"); '
            'let h = runtime::spawn(-> relay(&s[..]));')
        self.assertEqual(self.run_c_oracle(compile_source(returned_dynamic)).stdout, 'è\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(returned_dynamic.replace('let alias = loan;', 'drop(-> s); let alias = loan;'))
        for before, after, diagnostic in (
                ('return &t[1]', 'return t[1]', '&u8.*stockage statique'),
                ('let view: &u8 =', 'let view: u8 =', 'opération u8'),
                ('Ok(other) => { other }', 'Ok(other) => { 1 }', 'même type scalaire')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                # Mutate the async return only, not the same text in octet().
                # A malformed sync helper otherwise fails contract inference
                # first and hides the async diagnostic under test.
                verify_program(source.replace(before, after, 1))

    def test_async_char_at_matches_typed_errors_after_suspension(self):
        source = """
            async fn index(n: Int) -> Int { yield; return n; }
            async fn probe(t: &str, i: Int) -> Int {
                match char::from_str("🌍") {
                    Ok(c) => { yield; print(c); },
                    Err(CharFromStrError::Empty) => { print(90); },
                    Err(CharFromStrError::MultipleChars) => { print(91); }
                }
                return match t.char_at(index(i).await) {
                    Ok(c) => { yield; c.utf8_len() },
                    Err(CharAtError::OutOfBounds) => { 98 },
                    Err(CharAtError::NotCharBoundary) => { 97 }
                };
            }
            fn main() {
                let h = runtime::spawn(-> probe("é", INDEX));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for index, expected in ((0, 2), (1, 97), (2, 98)):
            with self.subTest(index=index):
                code = compile_source(source.replace('INDEX', str(index)))
                self.assertEqual(self.run_c_oracle(code).stdout, f'🌍\n{expected}\n')
        for value, expected in (('', 90), ('ab', 91)):
            with self.subTest(text=value):
                program = source.replace('INDEX', '0').replace('from_str("🌍")', f'from_str("{value}")')
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, f'{expected}\n2\n')
        named = source.replace('return match t.char_at(index(i).await) {',
            'let mut decoded: Result<char, CharAtError> = t.char_at(0);\n'
            '                match decoded { Ok(_) => {}, Err(_) => {} }\n'
            '                decoded = t.char_at(index(i).await);\n'
            '                let saved = decoded; yield;\n'
            '                return match saved {')
        self.assertEqual(self.run_c_oracle(compile_source(named.replace('INDEX', '1'))).stdout, '🌍\n97\n')
        for before, after, diagnostic in (
                ('decoded = t.char_at(index(i).await)', 'decoded = char::from_str(t)', 'famille du résultat'),
                ('let saved = decoded', 'let saved: Int = decoded', 'liaison UTF-8'),
                ('Err(CharAtError::OutOfBounds)', 'Err(CharFromStrError::Empty)', 'type du résultat')):
            candidate = named.replace('INDEX', '1').replace(before, after)
            if before.startswith('Err('):
                candidate = candidate.replace('Err(CharAtError::NotCharBoundary)',
                                              'Err(CharFromStrError::MultipleChars)')
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(candidate)
        for before, after, diagnostic in (
                ('index(i).await', 'false', 'valeur Int'),
                ('Ok(c) => { yield; c.utf8_len() }', 'Ok(()) => { 2 }', 'type du résultat'),
                ('CharAtError::OutOfBounds', 'CharFromStrError::Empty', 'types d’erreur')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('INDEX', '0').replace(before, after))

    def test_async_decode_result_capture_copies_before_source_drop(self):
        source = """
            async fn inspect(r: Result<char, CharAtError>) -> Int {
                yield;
                return match r {
                    Ok(c) => { print(c); c.utf8_len() },
                    Err(CharAtError::OutOfBounds) => { 98 },
                    Err(CharAtError::NotCharBoundary) => { 97 }
                };
            }
            async fn relay(r: Result<char, CharAtError>) -> Int {
                return inspect(r).await;
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new();
                s.push_str("🌍");
                let mut decoded = (&s[..]).char_at(INDEX);
                match decoded { Ok(_) => {}, Err(_) => {} }
                let task = relay(decoded);
                decoded = "é".char_at(0);
                drop(-> decoded);
                drop(-> s);
                let h = runtime::spawn(-> task);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for index, expected in ((0, '🌍\n4\n'), (1, '97\n')):
            with self.subTest(index=index):
                code = compile_source(source.replace('INDEX', str(index)))
                self.assertEqual(self.run_c_oracle(code).stdout, expected)
        for before, after, diagnostic in (
                ('relay(decoded)', 'relay(char::from_str("é"))', 'capture async.*CharAtError'),
                ('inspect(r).await', 'inspect(char::from_str("é")).await', 'capture async.*CharAtError')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('INDEX', '0').replace(before, after))

    def test_async_decode_result_distinguishes_join_and_decode_errors(self):
        source = """
            async fn work(t: &str, i: Int) -> Result<char, CharAtError> {
                yield;
                return t.char_at(i);
            }
            async fn relay(t: &str, i: Int) -> Result<char, CharAtError> {
                let fallback: Result<char, CharAtError> = work(t, 0).await;
                let h = runtime::spawn(-> work(t, i));
                return match h.await { Ok(decoded) => { decoded }, Err(_) => { fallback } };
            }
            fn main() {
                let h = runtime::spawn(-> relay("é", INDEX));
                match h.join() {
                    Ok(decoded) => {
                        match decoded {
                            Ok(c) => { print(c); },
                            Err(CharAtError::OutOfBounds) => { print(98); },
                            Err(CharAtError::NotCharBoundary) => { print(97); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        for index, expected in ((0, 'é\n'), (1, '97\n'), (2, '98\n')):
            with self.subTest(index=index):
                code = compile_source(source.replace('INDEX', str(index)))
                self.assertEqual(self.run_c_oracle(code).stdout, expected)
        code = compile_source(source.replace('INDEX', '1'))
        failed_inner_launch = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed_inner_launch).stdout, 'é\n')
        failed_outer_launch = code.replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed_outer_launch).stdout, '99\n')
        from_str = (source.replace('INDEX', '0')
                    .replace('return t.char_at(i)', 'return char::from_str(t)')
                    .replace('CharAtError::OutOfBounds', 'CharFromStrError::Empty')
                    .replace('CharAtError::NotCharBoundary', 'CharFromStrError::MultipleChars')
                    .replace('CharAtError', 'CharFromStrError')
                    .replace('relay("é",', 'relay("ab",'))
        self.assertEqual(self.run_c_oracle(compile_source(from_str)).stdout, '97\n')
        for before, after, diagnostic in (
                ('return t.char_at(i)', 'return char::from_str(t)', 'retour UTF-8.*CharAtError'),
                ('let fallback: Result<char, CharAtError>', 'let fallback: Result<char, CharFromStrError>',
                 'liaison UTF-8.*CharAtError')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('INDEX', '0').replace(before, after))

    def test_async_dynamic_text_capture_reserves_local_string_until_join(self):
        source = """
            async fn leaf(view: &str) -> Int { yield; print(view); return view.byte_len(); }
            async fn relay(view: &str) -> Int { return leaf(view).await; }
            async fn read(view: &str) -> Int {
                let alias = view;
                let child = runtime::spawn(-> relay(alias));
                return match child.await { Ok(n) => { n }, Err(_) => { 98 } };
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new();
                s.push_str("été");
                let view = &s[2..];
                let task = read(view);
                let h = runtime::spawn(-> task);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                s.push_str("!");
                print(&s[..]);
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, 'té\n3\nété!\n')
        failed_launch = code.replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed_launch).stdout, '99\nété!\n')
        discarded = source.replace(
            'let h = runtime::spawn(-> task);\n'
            '                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }',
            'drop(-> task);')
        self.assertEqual(self.run_c_oracle(compile_source(discarded)).stdout, 'été!\n')
        for before, after, diagnostic in (
                ('return match child.await { Ok(n) => { n }, Err(_) => { 98 } };',
                 'drop(-> child); return 0;', 'attente requise'),
                ('let h = runtime::spawn', 's.push_str("!"); let h = runtime::spawn', 'emprunt actif'),
                ('match h.join()', 'drop(-> s); match h.join()', 'emprunt encore utilisé'),
                ('match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }',
                 'drop(-> h);', 'join requis'),
                ('match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }',
                 'ignore(-> h);', 'join requis')):
            with self.subTest(after=after), self.assertRaisesRegex(Error, diagnostic):
                invalid = source.replace(before, after)
                if after == 'ignore(-> h);':
                    invalid += 'fn ignore(h: -> Execution<read>) { drop(-> h); }'
                verify_program(invalid)

        returned_view = source.replace(
            'async fn relay(view: &str) -> Int { return leaf(view).await; }',
            'async fn echo(view: &str) -> &str { return view; }\n'
            '            async fn relay(view: &str) -> Int {\n'
            '                let saved = echo(view).await; return leaf(saved).await;\n'
            '            }')
        self.assertEqual(self.run_c_oracle(compile_source(returned_view)).stdout, 'té\n3\nété!\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(returned_view.replace('match h.join()', 'drop(-> s); match h.join()'))

    def test_async_utf8_capture_keeps_local_byte_array_reserved(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn main() {
                let mut bytes: [u8; 2] = [0xc3, 0xa9];
                match str::from_utf8(&bytes) {
                    Ok(view) => {
                        let first = runtime::spawn(-> width(view));
                        let second = runtime::spawn(-> width(view));
                        match first.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                        match second.join() { Ok(n) => { print(n); }, Err(_) => { print(98); } }
                        bytes[1] = 0xa8;
                    },
                    Err(_) => { print(97); }
                }
                match str::from_utf8(&bytes) {
                    Ok(view) => { print(view); },
                    Err(_) => { print(96); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '2\n2\nè\n')
        for after in ('match first.join()', 'match second.join()'):
            candidate = source.replace('bytes[1] = 0xa8;', '').replace(after, 'bytes[1] = 0xa8; ' + after)
            with self.subTest(after=after), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(candidate)

    def test_async_utf8_capture_requires_disjoint_reset_source_in_contract(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn report(s: &String, pool_to_clear: &mut Pool<String>) {
                let task = { let child = width(&s[..]); <- child };
                let h = runtime::spawn(-> task);
                pool_to_clear.reset();
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
            fn relay(s: &String, pool_to_clear: &mut Pool<String>) {
                report(s, pool_to_clear);
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut spare = pool<String>(1);
                let mut s = strings.new();
                s.push_str("é");
                relay(&s, &mut TARGET);
            }
        """
        distinct = source.replace('TARGET', 'spare')
        self.assertEqual(self.run_c_oracle(compile_source(distinct, allow_legacy_reset=True)).stdout, '2\n')
        alias = source.replace('TARGET', 'strings')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(alias, allow_legacy_reset=True)
        after_join = alias.replace('pool_to_clear.reset();', '').replace(
            'Err(_) => { print(99); } }',
            'Err(_) => { print(99); } }\n                pool_to_clear.reset();')
        self.assertEqual(self.run_c_oracle(compile_source(after_join, allow_legacy_reset=True)).stdout, '2\n')
        view_parameter = (source.replace('fn report(s: &String,', 'fn report(view: &str,')
                          .replace('width(&s[..])', 'width(view)')
                          .replace('fn relay(s: &String,', 'fn relay(view: &str,')
                          .replace('report(s, pool_to_clear)', 'let alias = view; report(alias, pool_to_clear)')
                          .replace('relay(&s, &mut TARGET)', 'relay(&s[..], &mut TARGET)'))
        self.assertEqual(self.run_c_oracle(
            compile_source(view_parameter.replace('TARGET', 'spare'), allow_legacy_reset=True)).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(view_parameter.replace('TARGET', 'strings'), allow_legacy_reset=True)
        mutable = view_parameter.replace('fn report(view: &str,', 'fn report(mut view: &str,')
        self.assertEqual(self.run_c_oracle(compile_source(
            mutable.replace('TARGET', 'spare'), allow_legacy_reset=True)).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(mutable.replace('TARGET', 'strings'), allow_legacy_reset=True)
        mutable_alias = view_parameter.replace('let alias = view;', 'let mut alias = view;')
        self.assertEqual(self.run_c_oracle(compile_source(
            mutable_alias.replace('TARGET', 'spare'), allow_legacy_reset=True)).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(mutable_alias.replace('TARGET', 'strings'), allow_legacy_reset=True)
        static = view_parameter.replace('relay(&s[..], &mut TARGET);', 'relay("é", &mut strings);')
        self.assertEqual(self.run_c_oracle(compile_source(static, allow_legacy_reset=True)).stdout, '2\n')
        projected = view_parameter.replace('width(view)', 'width(&view[1..])').replace('s.push_str("é")', 's.push_str("aé")')
        self.assertEqual(self.run_c_oracle(
            compile_source(projected.replace('TARGET', 'spare'), allow_legacy_reset=True)).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(projected.replace('TARGET', 'strings'), allow_legacy_reset=True)

    def test_async_utf8_capture_uses_reassigned_parameter_source(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn prepare(mut view: &str, replacement: &str, change: Int) -> <- width {
                REASSIGN
                let task = width(view);
                return <- task;
            }
            fn main() {
                let mut old = pool<String>(1);
                let mut fresh = pool<String>(1);
                let mut first = old.new();
                let mut second = fresh.new();
                first.push_str("a");
                second.push_str("é");
                let task = prepare(&first[..], &second[..], 1);
                let h = runtime::spawn(-> task);
                TARGET.reset();
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        unchanged = source.replace('REASSIGN', '')
        self.assertEqual(self.run_c_oracle(compile_source(
            unchanged.replace('TARGET.reset();', 'drop(-> second);'))).stdout, '1\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(unchanged.replace('TARGET.reset();', 'drop(-> first);'))
        byte = (source.replace('&str', '&u8').replace('[..]', '[0]')
                .replace('-> Int { yield; return view.byte_len(); }', '-> u8 { yield; return *view; }')
                .replace('print(n);', 'display(n);')
                .replace('fn main() {', """
                    fn display(byte: u8) {
                        let mut strings = pool<String>(1);
                        let mut s = strings.new();
                        s.push_str("x");
                        match s.replace_byte(0, byte) {
                            Ok(_) => { print(&s[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    }
                    fn main() {
                """).replace('second.push_str("é")', 'second.push_str("z")'))
        for program, expected in ((source, '2\n'), (byte, 'z\n')):
            unconditional = program.replace('REASSIGN', 'view = replacement;')
            self.assertEqual(self.run_c_oracle(compile_source(
                unconditional.replace('TARGET', 'old'), allow_legacy_reset=True)).stdout, expected)
            conditional = program.replace('REASSIGN', 'if change == 1 { view = replacement; }')
            for candidate in (unconditional.replace('TARGET', 'fresh'),
                              conditional.replace('TARGET', 'old'),
                              conditional.replace('TARGET', 'fresh')):
                with self.subTest(candidate=candidate), self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(candidate, allow_legacy_reset=True)

    def test_async_utf8_capture_mixes_literal_and_borrowed_storage(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn prepare(mut view: &str, change: Int) -> <- width {
                REASSIGN
                let task = width(view);
                return <- task;
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("🌍");
                let task = prepare(INPUT, CHANGE);
                let h = runtime::spawn(-> task);
                RESET
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        static = source.replace('INPUT', '"a"').replace('CHANGE', '1').replace('RESET', '')
        static = static.replace('REASSIGN', 'if change == 1 { view = "é"; }')
        self.assertEqual(self.run_c_oracle(compile_source(static)).stdout, '2\n')

        dynamic = source.replace('INPUT', '&text[..]')
        for reassign in ('view = "é";',
                         'if change == 1 { view = "é"; } else { view = "ë"; }',
                         'loop { view = "é"; break; }'):
            certain = dynamic.replace('REASSIGN', reassign).replace('CHANGE', '1')
            self.assertEqual(self.run_c_oracle(compile_source(
                certain.replace('RESET', 'strings.reset();'), allow_legacy_reset=True)).stdout, '2\n')
        for reassign in ('if change == 1 { view = "é"; }',
                         'while change == 1 { view = "é"; break; }'):
            mixed = dynamic.replace('REASSIGN', reassign)
            for flag, expected in (('0', '4\n'), ('1', '2\n')):
                candidate = mixed.replace('CHANGE', flag)
                self.assertEqual(self.run_c_oracle(compile_source(
                    candidate.replace('RESET', ''))).stdout, expected)
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(candidate.replace('RESET', 'strings.reset();'), allow_legacy_reset=True)

    def test_async_utf8_capture_proves_computed_static_storage(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn main() {
                let h = runtime::spawn(-> width(VIEW));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        conditional = 'if 1 == 1 { let local = "é"; local } else { "🌍" }'
        matching = """
            match "a".char_at(0) {
                Ok(_) => { "é" },
                Err(CharAtError::OutOfBounds) => { "🌍" },
                Err(CharAtError::NotCharBoundary) => { "" }
            }
        """
        for view in (conditional, matching, f'&({conditional})[..]'):
            with self.subTest(view=view):
                direct = source.replace('VIEW', view)
                self.assertEqual(self.run_c_oracle(compile_source(direct)).stdout, '2\n')
                named = source.replace('let h =', f'let mut saved = {view}; let h =').replace('VIEW', 'saved')
                self.assertEqual(self.run_c_oracle(compile_source(named)).stdout, '2\n')

        byte = (source.replace('&str) -> Int', '&u8) -> u8').replace('view.byte_len()', '*view')
                .replace('Ok(n) => { print(n); }', 'Ok(_) => { print(1); }')
                .replace('VIEW', 'if 1 == 1 { &"é"[0] } else { &"a"[0] }'))
        self.assertEqual(self.run_c_oracle(compile_source(byte)).stdout, '1\n')

    def test_async_utf8_capture_composes_computed_view_with_call_contract(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn relay(view: &str) -> &str { return view; }
            fn main() {
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("🌍");
                let h = runtime::spawn(-> width(relay(relay(
                    if 1 == 1 { "é" } else { ALTERNATIVE }
                ))));
                DROP
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        static = source.replace('ALTERNATIVE', '"a"').replace('DROP', 'drop(-> text);')
        self.assertEqual(self.run_c_oracle(compile_source(static)).stdout, '2\n')
        mixed = source.replace('ALTERNATIVE', '&text[..]')
        self.assertEqual(self.run_c_oracle(compile_source(mixed.replace('DROP', ''))).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(mixed.replace('DROP', 'drop(-> text);'))

    def test_async_local_string_views_hold_storage_until_last_use(self):
        source = """
            async fn relay(view: &str) -> &str { yield; return view; }
            async fn work(text: &mut String) -> Int {
                let view = &text[2..];
                let alias = view;
                yield;
                BEFORE
                let returned = relay(alias).await;
                DURING
                print(returned);
                text.push_str("x");
                let byte = &text[1];
                yield;
                let copied = *byte;
                text.push_str("y");
                return text.byte_len();
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("é🌍");
                let h = runtime::spawn(-> work(&mut text));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(&text[..]);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '🌍\n8\né🌍xy\n')
        for slot in ('BEFORE', 'DURING'):
            candidate = source.replace(slot, 'text.push_str("!");').replace('BEFORE', '').replace('DURING', '')
            with self.subTest(slot=slot), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(candidate)
        owned = valid.replace('work(text: &mut String)', 'work(mut text: -> String)').replace(
            'work(&mut text)', 'work(-> text)').replace('print(&text[..]);',
            'let reused = strings.new(); print(reused.byte_len());')
        self.assertEqual(self.run_c_oracle(compile_source(owned)).stdout, '🌍\n8\n0\n')
        dangling = '''
            async fn bad(text: -> String) -> &str {
                let view = &text[..];
                yield;
                return view;
            }
            fn main() {}
        '''
        with self.assertRaisesRegex(Error, 'retour de vue'):
            verify_program(dangling)
        branch = valid.replace('print(returned);\n                text.push_str("x");',
                               'if true { print(returned); text.push_str("x"); }')
        self.assertEqual(self.run_c_oracle(compile_source(branch)).stdout, '🌍\n8\né🌍xy\n')

    def test_async_computed_utf8_await_preserves_local_source_loans(self):
        source = """
            async fn relay(view: &str) -> &str { yield; return view; }
            async fn work(text: &mut String, flag: Int) -> Int {
                let returned = (TASK).await;
                BEFORE
                yield;
                print(returned);
                text.push_str("x");
                return text.byte_len();
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("é🌍");
                let h = runtime::spawn(-> work(&mut text, FLAG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(&text[..]);
            }
        """
        variants = (
            '{ let t = relay(&text[2..]); <- t }',
            'if flag > 0 { let t = relay(&text[2..]); <- t } else { let t = relay(&text[..2]); <- t }',
            'loop { let t = relay(&text[2..]); break <- t; }',
        )
        for task in variants:
            for flag in (0, 1):
                with self.subTest(task=task, flag=flag):
                    program = source.replace('TASK', task).replace('FLAG', str(flag))
                    expected = 'é' if flag == 0 and task.startswith('if') else '🌍'
                    self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout,
                                     expected + '\n7\né🌍x\n')
                    with self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(program.replace('BEFORE', 'text.push_str("!");'))

    def test_async_computed_local_utf8_views_reserve_each_possible_source(self):
        source = """
            async fn work(a: &mut String, b: &mut String, flag: Int) -> Int {
                let returned = VIEW;
                BEFORE
                yield;
                USE
                a.push_str("x");
                b.push_str("y");
                return a.byte_len() + b.byte_len();
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new();
                let mut b = strings.new();
                a.push_str("é");
                b.push_str("🌍");
                let h = runtime::spawn(-> work(&mut a, &mut b, FLAG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(&a[..]); print(&b[..]);
            }
        """
        for byte in (False, True):
            first, second = ('&a[0]', '&b[0]') if byte else ('&a[..]', '&b[..]')
            variants = (
                f'if flag > 0 {{ {first} }} else {{ {second} }}',
                f'{{ let local = {first}; local }}',
                f'loop {{ if flag > 0 {{ break {first}; }} break {second}; }}',
            )
            for view in variants:
                for flag in (0, 1):
                    with self.subTest(byte=byte, view=view, flag=flag):
                        program = source.replace('VIEW', view).replace('FLAG', str(flag)).replace(
                            'USE', 'let copied = *returned;' if byte else 'print(returned);')
                        prefix = '' if byte else ('é' if flag or view.startswith('{') else '🌍') + '\n'
                        self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout,
                                         prefix + '8\néx\n🌍y\n')
                        for target in (('a',) if view.startswith('{') else ('a', 'b')):
                            with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                                verify_program(program.replace('BEFORE', f'{target}.push_str("!");'))
        for typ, value, use, prefix in (
                ('&str', '{ let alias = &a[..]; alias }', 'print(returned);', 'é\n'),
                ('&u8', '{ let alias = &a[0]; alias }', 'let copied = *returned;', '')):
            annotated = source.replace('let returned = VIEW;', f'let returned: {typ} = {value};').replace(
                'FLAG', '1').replace('BEFORE', '').replace('USE', use)
            self.assertEqual(self.run_c_oracle(compile_source(annotated)).stdout, prefix + '8\néx\n🌍y\n')
        owned = source.replace('work(a: &mut String, b: &mut String,',
                               'work(mut a: -> String, mut b: -> String,').replace(
            'work(&mut a, &mut b, FLAG)', 'work(-> a, -> b, FLAG)').replace(
            'print(&a[..]); print(&b[..]);',
            'let first = strings.new(); let second = strings.new(); print(first.byte_len() + second.byte_len());')
        owned = owned.replace('VIEW', 'if flag > 0 { &a[..] } else { &b[..] }').replace(
            'FLAG', '1').replace('USE', 'print(returned);')
        self.assertEqual(self.run_c_oracle(compile_source(owned.replace('BEFORE', ''))).stdout, 'é\n8\n0\n')
        for target in ('a', 'b'):
            with self.subTest(drop=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(owned.replace('BEFORE', f'drop(-> {target});'))
        dangling = """
            async fn take(s: -> String) -> <- String { yield; return <- s; }
            async fn bad(s: -> String) -> Int {
                let view = { let local = take(-> s).await; &local[..] };
                yield;
                print(view);
                return 0;
            }
            fn main() {}
        """
        for expression in ('{ let local = take(-> s).await; &local[..] }',
                           'loop { let local = take(-> s).await; break &local[..]; }'):
            with self.subTest(dangling=expression), self.assertRaisesRegex(Error, 'collection source locale'):
                verify_program(dangling.replace('{ let local = take(-> s).await; &local[..] }', expression))

    def test_async_push_str_keeps_argument_loan_through_call(self):
        source = """
            async fn work(a: &mut String, b: &mut String, flag: Int) {
                let view = &a[..];
                yield;
                TARGET.push_str(ARGUMENT);
                a.push_str("!");
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new();
                let mut b = strings.new();
                a.push_str("é");
                let h = runtime::spawn(-> work(&mut a, &mut b, 1));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&a[..]); print(&b[..]);
            }
        """
        for arg in ('view', '&a[..]', 'if flag > 0 { view } else { "x" }',
                    '{ let alias = view; alias }', 'loop { break view; }'):
            with self.subTest(argument=arg):
                program = source.replace('ARGUMENT', arg)
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('TARGET', 'b'))).stdout,
                                 'é!\né\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('TARGET', 'a'))

    def test_async_mutable_local_utf8_bindings_replace_loans_without_losing_aliases(self):
        source = """
            async fn relay(v: &str) -> &str { yield; return v; }
            async fn work(a: &mut String, b: &mut String) {
                let mut view = &a[..];
                yield;
                print(view);
                a.push_str("1");
                view = &b[..];
                BEFORE_ALIAS
                let alias = view;
                view = "x";
                AFTER_REPLACE
                print(alias);
                b.push_str("2");
                print(view);
                view = &a[..];
                let task = relay(view);
                view = "done";
                CHILD
                let returned = task.await;
                print(returned);
                a.push_str("3");
                print(view);
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é"); b.push_str("🌍");
                let h = runtime::spawn(-> work(&mut a, &mut b));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&a[..]); print(&b[..]);
            }
        """
        valid = source.replace('BEFORE_ALIAS', '').replace('AFTER_REPLACE', '').replace('CHILD', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, 'é\n🌍\nx\né1\ndone\né13\n🌍2\n')
        for point, target in (('BEFORE_ALIAS', 'b'), ('AFTER_REPLACE', 'b'), ('CHILD', 'a')):
            invalid = source.replace(point, f'{target}.push_str("!");').replace(
                'BEFORE_ALIAS', '').replace('AFTER_REPLACE', '').replace('CHILD', '')
            with self.subTest(point=point), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(invalid)
        owned = valid.replace('work(a: &mut String, b: &mut String)', 'work(mut a: -> String, mut b: -> String)').replace(
            'work(&mut a, &mut b)', 'work(-> a, -> b)').replace('print(&a[..]); print(&b[..]);',
            'let x = strings.new(); let y = strings.new(); print(x.byte_len() + y.byte_len());')
        self.assertEqual(self.run_c_oracle(compile_source(owned)).stdout, 'é\n🌍\nx\né1\ndone\n0\n')
        byte = """
            async fn work(a: &mut String, b: &mut String) -> u8 {
                let mut view = &a[1];
                let alias = view;
                yield;
                view = &b[1];
                let old = *alias;
                a.push_str("x");
                let result = *view;
                b.push_str("y");
                return result;
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é"); b.push_str("ê");
                let h = runtime::spawn(-> work(&mut a, &mut b));
                match h.join() {
                    Ok(value) => {
                        match a.replace_byte(1, value) {
                            Ok(_) => { print(&a[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(byte)).stdout, 'êx\n')

    def test_async_mutable_utf8_views_merge_assignments_by_path(self):
        source = """
            async fn work(a: &mut String, b: &mut String, flag: Int) {
                let mut view = "initial";
                ASSIGN
                yield;
                BEFORE
                print(view);
                a.push_str("x"); b.push_str("y");
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é"); b.push_str("🌍");
                let h = runtime::spawn(-> work(&mut a, &mut b, FLAG));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&a[..]); print(&b[..]);
            }
        """
        assignments = (
            'if flag > 0 { view = &a[..]; } else { view = &b[..]; }',
            'loop { if flag > 0 { view = &a[..]; break; } view = &b[..]; break; }',
            '{ view = if flag > 0 { &a[..] } else { &b[..] }; }',
        )
        for assignment in assignments:
            for flag in (0, 1):
                with self.subTest(assignment=assignment, flag=flag):
                    program = source.replace('ASSIGN', assignment).replace('FLAG', str(flag))
                    self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout,
                                     ('é' if flag else '🌍') + '\néx\n🌍y\n')
                    for target in ('a', 'b'):
                        with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                            verify_program(program.replace('BEFORE', f'{target}.push_str("!");'))
        source = source.replace('let mut view = "initial";', 'let mut view = &a[..];')
        branch = source.replace('ASSIGN', 'if flag > 0 { view = &b[..]; }').replace('FLAG', '0')
        self.assertEqual(self.run_c_oracle(compile_source(branch.replace('BEFORE', ''))).stdout,
                         'é\néx\n🌍y\n')
        for target in ('a', 'b'):
            with self.subTest(partial_branch=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(branch.replace('BEFORE', f'{target}.push_str("!");'))

    def test_async_mutable_utf8_bindings_match_small_alias_model(self):
        # Independent finite model: views carry the label of their byte storage;
        # replacement changes one view, never a saved copy of that view.
        for initial in ('a', 'b'):
            other = 'b' if initial == 'a' else 'a'
            for replacement in (other, None):
                for saved in (False, True):
                    for target in ('a', 'b'):
                        with self.subTest(initial=initial, replacement=replacement, saved=saved, target=target):
                            roots = {replacement} if replacement is not None else set()
                            if saved:
                                roots.add(initial)
                            allowed = target not in roots
                            value = f'&{replacement}[..]' if replacement else '"z"'
                            source = f"""
                                async fn work(a: &mut String, b: &mut String) {{
                                    let mut view = &{initial}[..];
                                    {'let alias = view;' if saved else ''}
                                    view = {value};
                                    yield;
                                    {target}.push_str("!");
                                    print(view);
                                    {'print(alias);' if saved else ''}
                                }}
                                fn main() {{
                                    let mut strings = pool<String>(2);
                                    let mut a = strings.new(); let mut b = strings.new();
                                    a.push_str("a"); b.push_str("b");
                                    let h = runtime::spawn(-> work(&mut a, &mut b));
                                    match h.join() {{ Ok(()) => {{}}, Err(_) => {{ print(99); }} }}
                                    print(&a[..]); print(&b[..]);
                                }}
                            """
                            if not allowed:
                                with self.assertRaisesRegex(Error, 'emprunt actif'):
                                    verify_program(source)
                            else:
                                expected = [replacement or 'z']
                                if saved:
                                    expected.append(initial)
                                expected.extend(name + ('!' if target == name else '') for name in ('a', 'b'))
                                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,
                                                 '\n'.join(expected) + '\n')

    def test_async_mutable_utf8_view_obeys_source_scope_and_loop_backedge(self):
        source = """
            async fn take(s: -> String) -> <- String { yield; return <- s; }
            async fn work(s: -> String) {
                let mut view = "initial";
                {
                    let local = take(-> s).await;
                    view = &local[..];
                    yield;
                    print(view);
                    INNER
                }
                AFTER
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é");
                let h = runtime::spawn(-> work(-> s));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                let reused = strings.new(); print(reused.byte_len());
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('INNER', '').replace('AFTER', ''))).stdout,
                         'é\n0\n')
        for marker, replacement in (('AFTER', 'print(view);'), ('INNER', 'drop(-> local); print(view);')):
            with self.subTest(marker=marker), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace(marker, replacement).replace('INNER', '').replace('AFTER', ''))
        backedge = """
            async fn work(a: &mut String, flag: Int) {
                let mut view = &a[..];
                loop {
                    print(view);
                    a.push_str("!");
                    if flag > 0 { continue; }
                }
            }
            fn main() {}
        """
        with self.assertRaises(Error):
            verify_program(backedge)

    def test_async_mutable_utf8_view_replaced_before_continue(self):
        source = """
            async fn work(a: &mut String) {
                let mut view = "";
                let mut rounds = 0;
                loop {
                    view = &a[..];
                    yield;
                    print(view);
                    view = "";
                    a.push_str("x");
                    rounds = rounds + 1;
                    if rounds == 2 { break; }
                    CONTINUE
                }
                print(view);
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut a = strings.new(); a.push_str("é");
                let h = runtime::spawn(-> work(&mut a));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&a[..]);
            }
        """
        for tail in ('continue;', ''):
            with self.subTest(tail=tail):
                self.assertEqual(self.run_c_oracle(compile_source(source.replace('CONTINUE', tail))).stdout,
                                 'é\néx\n\néxx\n')

    def test_async_joined_utf8_view_keeps_local_collection_until_payload_last_use(self):
        source = """
            async fn relay(v: &str) -> &str { yield; return v; }
            async fn work(a: &mut String) {
                let view = &a[..];
                let handle = runtime::spawn(-> relay(view));
                BIND
                BEFORE
                match SUBJECT {
                    Ok(value) => {
                        DURING
                        yield;
                        print(value);
                        a.push_str("x");
                    },
                    Err(_) => { print(99); }
                }
                a.push_str("y");
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut a = strings.new(); a.push_str("é");
                let h = runtime::spawn(-> work(&mut a));
                match h.join() { Ok(()) => {}, Err(_) => { print(98); } }
                print(&a[..]);
            }
        """
        for bind, subject in (('', 'handle.await'), ('let result = handle.await;', 'result')):
            with self.subTest(bind=bind):
                program = source.replace('BIND', bind).replace('SUBJECT', subject)
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', '').replace('DURING', ''))).stdout,
                                 'é\néxy\n')
                for point in ('BEFORE', 'DURING'):
                    with self.subTest(point=point), self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(program.replace(point, 'a.push_str("!");').replace('BEFORE', '').replace('DURING', ''))
        escaped = """
            async fn relay(v: &str) -> &str { yield; return v; }
            async fn work(a: &mut String) {
                let handle = runtime::spawn(-> relay(&a[..]));
                let received = match handle.await {
                    Ok(value) => { yield; value },
                    Err(_) => { "fallback" }
                };
                ESCAPED
                print(received);
                a.push_str("y");
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut a = strings.new(); a.push_str("é");
                let h = runtime::spawn(-> work(&mut a));
                match h.join() { Ok(()) => {}, Err(_) => { print(98); } }
                print(&a[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(escaped.replace('ESCAPED', ''))).stdout, 'é\néy\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(escaped.replace('ESCAPED', 'a.push_str("!");'))

    def test_async_joined_utf8_result_retains_independent_payload_and_result_loans(self):
        source = """
            async fn relay(v: &str) -> &str { yield; return v; }
            async fn work(a: &mut String) {
                let h = runtime::spawn(-> relay(&a[..]));
                let result = h.await;
                match result { Ok(value) => { print(value); }, Err(_) => {} }
                BETWEEN
                match result { Ok(value) => { yield; print(value); a.push_str("x"); }, Err(_) => {} }
                a.push_str("y");
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut a = strings.new(); a.push_str("é");
                let h = runtime::spawn(-> work(&mut a));
                match h.join() { Ok(()) => {}, Err(_) => { print(98); } }
                print(&a[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BETWEEN', ''))).stdout, 'é\né\néxy\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BETWEEN', 'a.push_str("!");'))
        owned = source.replace('work(a: &mut String)', 'work(mut a: -> String)').replace(
            'work(&mut a)', 'work(-> a)').replace('print(&a[..]);',
            'let reused = strings.new(); print(reused.byte_len());')
        self.assertEqual(self.run_c_oracle(compile_source(owned.replace('BETWEEN', ''))).stdout, 'é\né\n0\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(owned.replace('BETWEEN', 'drop(-> a);'))
        computed = source.replace('let h = runtime::spawn(-> relay(&a[..]));',
            'let h = if true { let child = runtime::spawn(-> relay(&a[..])); <- child } '
            'else { let child = runtime::spawn(-> relay(&a[..])); <- child };')
        self.assertEqual(self.run_c_oracle(compile_source(computed.replace('BETWEEN', ''))).stdout, 'é\né\néxy\n')
        byte = """
            async fn relay(v: &u8) -> &u8 { yield; return v; }
            async fn work(a: &mut String) -> u8 {
                let h = runtime::spawn(-> relay(&a[1]));
                let result = h.await;
                return match result {
                    Ok(value) => { CHECK yield; let copied = *value; a.push_str("x"); copied },
                    Err(_) => { a[1] }
                };
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut a = strings.new(); a.push_str("ê");
                let h = runtime::spawn(-> work(&mut a));
                match h.join() {
                    Ok(value) => {
                        match a.replace_byte(1, value) {
                            Ok(_) => { print(&a[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(97); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(96); }
                        }
                    },
                    Err(_) => { print(98); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(byte.replace('CHECK', ''))).stdout, 'êx\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(byte.replace('CHECK', 'a.push_str("!");'))

    def test_async_string_capture_return_projects_storage_to_caller(self):
        source = """
            async fn view(a: &String) -> &str {
                let text = &a[2..];
                yield;
                return text;
            }
            async fn relay(a: &String, b: &String) -> &str {
                yield;
                return view(a).await;
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é🌍"); b.push_str("b");
                let h = runtime::spawn(-> relay(&a, &b));
                match h.join() {
                    Ok(value) => {
                        b.push_str("!");
                        BEFORE
                        print(&a[..]);
                        print(value);
                        a.push_str("x");
                    },
                    Err(_) => { print(99); }
                }
                print(&a[..]); print(&b[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE', ''))).stdout,
                         'é🌍\n🌍\né🌍x\nb!\n')
        with self.assertRaisesRegex(Error, 'emprunt|réserv'):
            verify_program(source.replace('BEFORE', 'a.push_str("!");'))
        destroyed = source.replace('Ok(value) => {', 'Ok(value) => { a ->;', 1).replace(
            'BEFORE', 'drop(-> a);').replace('print(&a[..]);', '').replace('a.push_str("x");', '')
        with self.assertRaisesRegex(Error, 'emprunt|réserv|déplac'):
            verify_program(destroyed)
        via_handle = source.replace('return view(a).await;', """
                let child = runtime::spawn(-> view(a));
                return match child.await { Ok(value) => { value }, Err(_) => { "fallback" } };
            """)
        self.assertEqual(self.run_c_oracle(compile_source(via_handle.replace('BEFORE', ''))).stdout,
                         'é🌍\n🌍\né🌍x\nb!\n')
        with self.assertRaisesRegex(Error, 'emprunt|réserv'):
            verify_program(via_handle.replace('BEFORE', 'a.push_str("!");'))
        computed = source.replace('let text = &a[2..];\n                yield;\n                return text;',
                                 'return { let text = &a[2..]; yield; text };')
        self.assertIn('return { let text', computed)
        self.assertEqual(self.run_c_oracle(compile_source(computed.replace('BEFORE', ''))).stdout,
                         'é🌍\n🌍\né🌍x\nb!\n')
        exclusive = source.replace('view(a: &String)', 'view(a: &mut String)').replace(
            'relay(a: &String,', 'relay(a: &mut String,').replace(
            'relay(&a, &b)', 'relay(&mut a, &b)').replace('print(&a[..]);\n                        print(value);', 'print(value);')
        self.assertEqual(self.run_c_oracle(compile_source(exclusive.replace('BEFORE', ''))).stdout,
                         '🌍\né🌍x\nb!\n')
        with self.assertRaisesRegex(Error, 'emprunt|réserv'):
            verify_program(exclusive.replace('BEFORE', 'print(&a[..]);'))
        dangling = source.replace('view(a: &String)', 'view(a: -> String)').replace(
            'relay(a: &String,', 'relay(a: -> String,').replace('view(a).await', 'view(-> a).await').replace(
            'relay(&a, &b)', 'relay(-> a, &b)')
        with self.assertRaisesRegex(Error, 'retour de vue'):
            verify_program(dangling.replace('BEFORE', ''))

    def test_async_string_view_join_contract_projects_collection_capture(self):
        source = """
            async fn view(a: &String, b: &String) -> &str { yield; return &a[2..]; }
            fn launch(a: &String, b: &String) -> <- Execution<view> {
                let h = runtime::spawn(-> view(a, b));
                return <- h;
            }
            fn read(a: &String, b: &String) -> &str {
                let h = launch(a, b);
                return match h.join() {
                    Ok(value) => { value },
                    Err(_) => { "fallback" }
                };
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é🌍"); b.push_str("b");
                let received = read(&a, &b);
                b.push_str("!");
                BEFORE
                print(received);
                a.push_str("x");
                print(&a[..]); print(&b[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE', ''))).stdout,
                         '🌍\né🌍x\nb!\n')
        for operation in ('a.push_str("!");', 'drop(-> a);'):
            with self.subTest(operation=operation), self.assertRaisesRegex(Error, 'emprunt|réserv|déplac'):
                verify_program(source.replace('BEFORE', operation))
        exclusive = source.replace('a: &String', 'a: &mut String').replace('read(&a, &b)', 'read(&mut a, &b)')
        self.assertEqual(self.run_c_oracle(compile_source(exclusive.replace('BEFORE', ''))).stdout,
                         '🌍\né🌍x\nb!\n')
        with self.assertRaisesRegex(Error, 'emprunt|réserv'):
            verify_program(exclusive.replace('BEFORE', 'print(&a[..]);'))
        # A separate consumer exercises symbolic Execution<view> input contracts.
        transferred = source.replace('return match h.join() {', """return receive(-> h); }
            fn receive(h: -> Execution<view>) -> &str { return match h.join() {""", 1)
        self.assertEqual(self.run_c_oracle(compile_source(transferred.replace('BEFORE', ''))).stdout,
                         '🌍\né🌍x\nb!\n')
        with self.assertRaisesRegex(Error, 'emprunt|réserv'):
            verify_program(transferred.replace('BEFORE', 'a.push_str("!");'))

        for parameter, declaration in (('', 'let mut strings = pool<String>(1);'),
                                       ('strings: &mut Pool<String>', '')):
            local = f"""
                async fn view(s: &String) -> &str {{ yield; return &s[..]; }}
                fn bad({parameter}) -> &str {{
                    {declaration}
                    let mut s = strings.new(); s.push_str("local");
                    let h = runtime::spawn(-> view(&s));
                    return match h.join() {{ Ok(value) => {{ value }}, Err(_) => {{ "fallback" }} }};
                }}
                fn main() {{}}
            """
            with self.subTest(local_pool=not parameter), self.assertRaisesRegex(Error, 'UTF-8.*non durable'):
                verify_program(local)

    def test_async_string_byte_return_keeps_conditional_collection_provenances(self):
        source = """
            async fn pick(a: &String, b: &String, flag: Int) -> &u8 {
                yield;
                if flag > 0 { return &a[1]; }
                return &b[1];
            }
            fn fetch(a: &String, b: &String, flag: Int) -> &u8 {
                let h = runtime::spawn(-> pick(a, b, flag));
                return match h.join() {
                    Ok(value) => { value },
                    Err(_) => { &"x"[0] }
                };
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("ê"); b.push_str("é");
                let byte = fetch(&a, &b, FLAG);
                BEFORE
                let copied = *byte;
                a.push_str("x"); b.push_str("y");
                match a.replace_byte(1, copied) {
                    Ok(_) => { print(&a[..]); },
                    Err(ByteReplaceError::OutOfBounds) => { print(99); },
                    Err(ByteReplaceError::InvalidUtf8) => { print(98); }
                }
                print(&b[..]);
            }
        """
        for flag, expected in ((0, 'éx'), (1, 'êx')):
            with self.subTest(flag=flag):
                program = source.replace('FLAG', str(flag))
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout,
                                 expected + '\néy\n')
                for target in ('a', 'b'):
                    with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt|réserv'):
                        verify_program(program.replace('BEFORE', f'{target}.push_str("!");'))

    def test_async_loop_carried_utf8_views_widen_before_verifying_reprises(self):
        source = """
            async fn work(a: &mut String, b: &mut String) {
                let mut view = &a[..];
                let mut rounds = 0;
                loop {
                    yield;
                    print(view);
                    b.push_str("!");
                    view = &b[..];
                    rounds = rounds + 1;
                    if rounds == 2 { break; }
                    CONTINUE
                }
                a.push_str("x");
                BEFORE
                print(view);
                b.push_str("y");
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é"); b.push_str("🌍");
                let h = runtime::spawn(-> work(&mut a, &mut b));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&a[..]); print(&b[..]);
            }
        """
        for tail in ('continue;', ''):
            with self.subTest(tail=tail):
                program = source.replace('CONTINUE', tail)
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout,
                                 'é\n🌍!\n🌍!!\néx\n🌍!!y\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('BEFORE', 'b.push_str("?");'))
        invalid = source.replace('CONTINUE', 'continue;').replace('BEFORE', '').replace(
            'print(view);\n                    b.push_str("!");', 'b.push_str("!"); print(view);')
        alias = source.replace('CONTINUE', 'continue;').replace('BEFORE', '').replace(
            'print(view);\n                    b.push_str("!");',
            'let old = view; view = ""; b.push_str("!"); print(old);')
        for name, candidate in (('direct', invalid), ('alias', alias)):
            with self.subTest(conflict=name), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(candidate)

    def test_async_while_carried_utf8_view_preserves_zero_iteration_source(self):
        source = """
            async fn work(a: &mut String, b: &mut String, limit: Int) {
                let mut view = &a[..];
                let mut rounds = 0;
                while rounds < limit {
                    print(view);
                    view = &b[..];
                    rounds = rounds + 1;
                    yield;
                    continue;
                }
                BEFORE
                print(view);
                a.push_str("x"); b.push_str("y");
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é"); b.push_str("🌍");
                let h = runtime::spawn(-> work(&mut a, &mut b, LIMIT));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&a[..]); print(&b[..]);
            }
        """
        for limit, prefix in ((0, 'é'), (2, 'é\n🌍\n🌍')):
            with self.subTest(limit=limit):
                program = source.replace('LIMIT', str(limit))
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout,
                                 prefix + '\néx\n🌍y\n')
                for target in ('a', 'b'):
                    with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(program.replace('BEFORE', f'{target}.push_str("!");'))

    def test_async_nested_loop_carried_utf8_view_reaches_fixed_point(self):
        source = """
            async fn work(a: &mut String, b: &mut String) {
                let mut view = &a[..];
                let mut outer = 0;
                loop {
                    let mut inner = 0;
                    loop {
                        print(view);
                        view = &b[..];
                        inner = inner + 1;
                        if inner == 2 { break; }
                        yield;
                        continue;
                    }
                    outer = outer + 1;
                    if outer == 2 { break; }
                    yield;
                    continue;
                }
                a.push_str("x");
                BEFORE
                print(view);
                b.push_str("y");
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("é"); b.push_str("🌍");
                let h = runtime::spawn(-> work(&mut a, &mut b));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&a[..]); print(&b[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE', ''))).stdout,
                         'é\n🌍\n🌍\n🌍\n🌍\néx\n🌍y\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'b.push_str("!");'))

    def test_async_loop_carried_byte_view_with_value_and_task_cleanup(self):
        source = """
            async fn quiet() { print(99); yield; }
            async fn work(a: &mut String, b: &mut String) -> u8 {
                let mut view = &a[1];
                let mut rounds = 0;
                let result = loop {
                    let unused = quiet();
                    let previous = *view;
                    b.push_str("!");
                    view = &b[1];
                    rounds = rounds + 1;
                    if rounds == 2 { break rounds; }
                    yield;
                    continue;
                };
                print(result);
                a.push_str("x");
                BEFORE
                let copied = *view;
                b.push_str("y");
                return copied;
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); let mut b = strings.new();
                a.push_str("ê"); b.push_str("é");
                let h = runtime::spawn(-> work(&mut a, &mut b));
                match h.join() {
                    Ok(value) => {
                        match a.replace_byte(1, value) {
                            Ok(_) => { print(&a[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(_) => { print(96); }
                }
                print(&b[..]);
            }
        """
        valid = source.replace('BEFORE', '')
        compiler = verify_program(valid)
        warnings = {warning for warning in compiler.warnings if 'inactive nettoyée' in warning}
        cleanup_lines = [line for line, text in enumerate(source.splitlines(), 1)
                         if 'break rounds;' in text or text.strip() == 'continue;']
        self.assertEqual(warnings, {
            f"ligne {line}: tâche inactive nettoyée sans avoir été démarrée : 'unused'"
            for line in cleanup_lines})
        code = compile_source(valid)
        self.assertEqual(code.count('= crust_async_quiet_create('), 1)
        self.assertEqual(self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n' + code).stdout,
                         '2\néx\né!!y\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'b.push_str("?");'))

    def test_async_loop_carried_utf8_alias_chain_matches_concrete_trace_model(self):
        source = """
            async fn work(a: &String, b: &String, c: &String, limit: Int) -> &str {
                let mut view = &a[..];
                let mut next = &b[..];
                let mut rounds = 0;
                while rounds < limit {
                    print(view);
                    view = next;
                    next = &c[..];
                    rounds = rounds + 1;
                    yield;
                    continue;
                }
                return view;
            }
            fn main() {
                let mut strings = pool<String>(3);
                let mut a = strings.new(); let mut b = strings.new(); let mut c = strings.new();
                a.push_str("α"); b.push_str("β"); c.push_str("γ");
                let h = runtime::spawn(-> work(&a, &b, &c, LIMIT));
                match h.join() {
                    Ok(value) => {
                        BEFORE
                        print(value);
                        a.push_str("x"); b.push_str("y"); c.push_str("z");
                    },
                    Err(_) => { print(99); }
                }
                print(&a[..]); print(&b[..]); print(&c[..]);
            }
        """
        for count in range(4):
            # Concrete interpretation of reference values, independent of any
            # compiler origin sets or loop convergence implementation.
            view, following, trace = 'α', 'β', []
            for _ in range(count):
                trace.append(view)
                view, following = following, 'γ'
            expected = '\n'.join([*trace, view, 'αx', 'βy', 'γz']) + '\n'
            program = source.replace('LIMIT', str(count))
            with self.subTest(iterations=count):
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout, expected)
                for target in ('a', 'b', 'c'):
                    with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt|réserv'):
                        verify_program(program.replace('BEFORE', f'{target}.push_str("!");'))

    def test_async_loop_carried_utf8_view_rejects_iteration_local_storage(self):
        source = """
            async fn take(s: -> String) -> <- String { yield; return <- s; }
            async fn bad(s: -> String) {
                let mut view = "";
                loop {
                    print(view);
                    let local = take(-> s).await;
                    view = &local[..];
                    yield;
                    EXIT
                }
                AFTER
            }
            fn main() {}
        """
        for exit, following in (('continue;', ''), ('break;', 'print(view);')):
            with self.subTest(exit=exit), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('EXIT', exit).replace('AFTER', following))

    def test_async_string_pop_preserves_utf8_and_returns_independent_char_option(self):
        source = """
            async fn work(s: &mut String) -> Option<char> {
                let first = s.pop();
                yield;
                print(&s[..]);
                match s.pop() { Some(ch) => { print(ch); }, None => { print(99); } }
                let empty: Option<char> = s.pop();
                match empty { Some(ch) => { print(ch); }, None => { print(0); } }
                return first;
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é🌍");
                let h = runtime::spawn(-> work(&mut s));
                match h.join() {
                    Ok(first) => {
                        s.push_str("x");
                        match first { Some(ch) => { print(ch); }, None => { print(98); } }
                    },
                    Err(_) => { print(97); }
                }
                print(&s[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'é\né\n0\n🌍\nx\n')
        invalid = source.replace('let first = s.pop();', 'let view = &s[..]; let first = s.pop(); print(view);')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(invalid)
        with self.assertRaisesRegex(Error, 'mutable'):
            verify_program(source.replace('work(s: &mut String)', 'work(s: &String)').replace('work(&mut s)', 'work(&s)'))
        with self.assertRaisesRegex(Error, 'aucun argument'):
            verify_program(source.replace('let first = s.pop();', 'let first = s.pop(0);'))
        with self.assertRaisesRegex(Error, 'match UTF-8'):
            verify_program(source.replace('match empty { Some(ch)', 'match empty { Ok(ch)').replace('None => { print(0); }', 'Err(_) => { print(0); }'))

        capture = source.replace('async fn work(s: &mut String) -> Option<char> {', """
            async fn consume(v: &str, option: Option<char>) -> Option<char> { print(v); return option; }
            async fn work(s: &mut String) -> Option<char> {""").replace(
            'let first = s.pop();', 'let first = consume(&s[..], s.pop()).await;')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(capture)
        mismatch = source.replace('work(s: &mut String) -> Option<char>',
                                  'work(s: &mut String) -> Result<char,CharAtError>')
        with self.assertRaisesRegex(Error, 'attendu Result<char,CharAtError>'):
            verify_program(mismatch)

    def test_async_string_pop_option_survives_source_drop_and_slot_reuse(self):
        source = """
            async fn discard(s: -> String) -> Int { yield; return 1; }
            async fn pass(value: Option<char>, n: Int) -> Option<char> {
                print(n); yield; return value;
            }
            async fn work(mut s: -> String) -> Option<char> {
                return pass(s.pop(), discard(-> s).await).await;
            }
            fn finish(h: -> Execution<work>, fallback: Option<char>) -> Option<char> {
                return match h.join() { Ok(value) => { value }, Err(_) => { fallback } };
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é🌍");
                let fallback = s.pop();
                let h = runtime::spawn(-> work(-> s));
                let result = finish(-> h, fallback);
                let mut reused = strings.new(); reused.push_str("z");
                match result { Some(ch) => { print(ch); }, None => { print(0); } }
                print(&reused[..]);
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '1\né\nz\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, runner, pointer) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '🌍\nz\n')
        conditional = source.replace('pass(s.pop(), discard(-> s).await)',
                                     'pass((if true { s.pop() } else { s.pop() }), discard(-> s).await)')
        self.assertEqual(self.run_c_oracle(compile_source(conditional)).stdout, '1\né\nz\n')
        reassigned = source.replace('return pass(s.pop(), discard(-> s).await).await;', """
            let mut result = s.pop();
            result = if false { result } else { s.pop() };
            return pass(result, discard(-> s).await).await;
        """)
        self.assertEqual(self.run_c_oracle(compile_source(reassigned)).stdout, '1\n0\nz\n')
        mismatch = source.replace('pass(value: Option<char>, n: Int) -> Option<char>',
                                  'pass(value: Result<char,CharFromStrError>, n: Int) -> Result<char,CharFromStrError>')
        with self.assertRaisesRegex(Error, 'attendu Result<char,CharFromStrError>'):
            verify_program(mismatch)

    def test_async_string_pop_discarded_result_still_mutates_once(self):
        source = """
            async fn work(s: &mut String) { s.pop(); yield; print(&s[..]); }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é🌍");
                let h = runtime::spawn(-> work(&mut s));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&s[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'é\né\n')

    def test_async_string_pop_sequence_matches_unicode_scalar_model(self):
        template = """
            async fn drain(s: &mut String) -> Int {
                let mut count = 0;
                loop {
                    let next = s.pop();
                    yield;
                    match next {
                        Some(ch) => { print(ch); count = count + 1; },
                        None => { break; }
                    }
                }
                return count;
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("TEXT");
                let h = runtime::spawn(-> drain(&mut s));
                match h.join() { Ok(count) => { print(count); }, Err(_) => { print(99); } }
                print(&s[..]);
            }
        """
        for text in ('', 'a', 'é', '🌍', 'é', 'aé🌍'):
            with self.subTest(text=text):
                expected = ''.join(ch + '\n' for ch in reversed(text)) + str(len(text)) + '\n\n'
                self.assertEqual(self.run_c_oracle(compile_source(template.replace('TEXT', text))).stdout, expected)

    def test_async_mutating_method_reserves_receiver_during_suspended_argument(self):
        template = """
            async fn argument(other: &mut TYPE MORE_PARAM) -> OUTPUT {
                SIDE_EFFECT
                print(10); yield;
                return VALUE;
            }
            async fn work(destination: &mut TYPE, other: &mut TYPE MORE_PARAM) {
                destination.METHOD(argument(other MORE_ARG).await);
                yield;
                OBSERVE
            }
            fn main() {
                let mut pools = pool<TYPE>(2);
                let mut destination = pools.new(); let mut other = pools.new();
                BEFORE
                let h = runtime::spawn(-> work(&mut destination, &mut other MORE_ARG));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                AFTER
            }
        """
        cases = (
            ('String', '&str', 'push_str', 'other.push_str("x");', '"é"',
             'print(&destination[..]);', '10\né\n'),
            ('String', 'char', 'push', 'other.push_str("x");', 'fallback',
             'print(&destination[..]);', '10\né\n'),
            ('Vector<Int>', 'Int', 'push', 'other.push(7);', '8',
             'print(destination[0]);', '10\n8\n'),
            ('Vector<u8>', 'u8', 'push', 'other.push(7);', '8',
             'print(destination.len());', '10\n1\n'))
        for typ, output, method, effect, value, observe, expected in cases:
            with self.subTest(typ=typ, method=method):
                source = (template.replace('TYPE', typ).replace('OUTPUT', output).replace('METHOD', method)
                          .replace('SIDE_EFFECT', effect).replace('VALUE', value).replace('OBSERVE', observe)
                          .replace('MORE_PARAM', ', fallback: char' if output == 'char' else '')
                          .replace('MORE_ARG', ', fallback' if output == 'char' else '')
                          .replace('BEFORE', 'match "é".char_at(0) { Ok(fallback) => {' if output == 'char' else '')
                          .replace('AFTER', '}, Err(_) => { print(98); } }' if output == 'char' else ''))
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, expected)
                invalid = source.replace('argument(other ', 'argument(destination ')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(invalid)
                shared = source.replace('argument(other: &mut', 'argument(other: &').replace(
                    'argument(other ', 'argument(&*destination ').replace(
                    effect, 'print(other.byte_len());' if typ == 'String' else 'print(other.len());')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(shared)
                if typ == 'String':
                    call = f'destination.{method}(argument(other '
                    # An outer view ends inside this child block, before the
                    # receiver is reserved; a later use must keep it alive.
                    nested = source.replace(call, 'let view = &destination[..]; if true { print(view); ' + call)
                    nested = nested.replace('yield;\n                ' + observe,
                                            '} yield;\n                ' + observe)
                    self.assertEqual(self.run_c_oracle(compile_source(nested)).stdout, '\n' + expected)
                    with self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(nested.replace('} yield;', 'print(view); } yield;'))

    def test_async_string_merge_consumes_source_across_pools_and_reuses_slot(self):
        source = """
            async fn combine(destination: &mut String, source: -> String) {
                yield;
                destination.merge(-> source);
                yield;
                print(&destination[..]);
            }
            fn finish(h: -> Execution<combine>) {
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
            }
            fn main() {
                let mut first = pool<String>(1);
                let mut second = pool<String>(1);
                let mut destination = first.new(); destination.push_str("été");
                let mut source = second.new(); source.push_str("🌍");
                address(destination); address(source);
                let h = runtime::spawn(-> combine(&mut destination, -> source));
                finish(-> h);
                let mut reused = second.new(); reused.push_str("ok");
                address(destination); address(reused);
                destination.push_str("!");
                print(&destination[..]); print(&reused[..]);
            }
        """
        code = compile_source(source)
        # Count destructor entries independently of pool free-list decisions.
        marker = 'static void cell_drop_impl(Cell *cell, int resetting) {'
        instrumented = code.replace(marker, 'static int observed_drops;\n' + marker + '\n    ++observed_drops;', 1)
        instrumented, count = re.subn(r'(text_print\(text_slice\(frame->)',
            r'if (observed_drops != 1) abort();\n    \1', instrumented)
        self.assertEqual(count, 1)
        instrumented = instrumented.replace('crust_task_context_close();',
            'if (observed_drops != 3) abort();\n    crust_task_context_close();', 1)
        a, b, merged, after, reused, final, fresh = self.run_c_oracle(instrumented).stdout.splitlines()
        self.assertEqual((after, reused, merged, final, fresh), (a, b, 'été🌍', 'été🌍!', 'ok'))
        failed = instrumented.replace('#include <pthread.h>', '#include <pthread.h>\n'
            '#define pthread_create(thread, attr, runner, pointer) EAGAIN', 1)
        a, b, error, after, reused, final, fresh = self.run_c_oracle(failed).stdout.splitlines()
        self.assertEqual((error, after, reused, final, fresh), ('99', a, b, 'été!', 'ok'))
        for body, diagnostic in (
                ('destination.merge(source);', 'transfert explicite'),
                ('destination.merge(-> source); print(&source[..]);', 'plus utilisable'),
                ('let view = &source[..]; destination.merge(-> source); print(view);', 'emprunt actif'),
                ('let view = &destination[..]; destination.merge(-> source); print(view);', 'emprunt actif')):
            with self.subTest(body=body), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('destination.merge(-> source);', body))
        with self.assertRaisesRegex(Error, 'mutable'):
            verify_program(source.replace('destination: &mut String', 'destination: &String').replace(
                'combine(&mut destination', 'combine(&destination'))
        with self.assertRaisesRegex(Error, 'allocation String'):
            verify_program(source.replace('source: -> String', 'source: -> Int').replace(
                'let mut second = pool<String>(1)', 'let mut second = pool<Int>(1)').replace(
                'let mut source = second.new(); source.push_str("🌍");', 'let source = new(second) Int(7);').replace(
                'let mut reused = second.new(); reused.push_str("ok");', 'let reused = new(second) Int(8);').replace(
                'print(&reused[..]);', 'print(reused);'))

    def test_async_string_merge_accepts_awaited_and_computed_transfers(self):
        template = """
            async fn forward(source: -> String) -> <- String { yield; return <- source; }
            async fn combine(destination: &mut String, source: -> String, flag: Bool) {
                yield;
                destination.merge(ARGUMENT);
                print(&destination[..]);
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new(); a.push_str("é");
                let mut b = strings.new(); b.push_str("🌍");
                let h = runtime::spawn(-> combine(&mut a, -> b, FLAG));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                let reused = strings.new();
                print(&a[..]); print(&reused[..]);
            }
        """
        for argument in ('-> forward(-> source).await',
                         '-> { let next = forward(-> source).await; <- next }',
                         '-> if flag { source ->; <- source } else { source ->; <- source }',
                         '-> loop { source ->; break <- source; }'):
            for flag in ('true', 'false'):
                with self.subTest(argument=argument, flag=flag):
                    source = template.replace('ARGUMENT', argument).replace('FLAG', flag)
                    self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'é🌍\né🌍\n\n')
        conflicting = template.replace('ARGUMENT', '-> conflicting(destination, -> source).await').replace('FLAG', 'true')
        conflicting += """
            async fn conflicting(destination: &mut String, source: -> String) -> <- String {
                destination.push_str("x"); yield; return <- source;
            }
        """
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conflicting)
        alias = """
            async fn work(mut value: -> String) { value.merge(-> value); }
            fn main() { let mut p = pool<String>(1); let value = p.new(); let h = runtime::spawn(-> work(-> value));
                match h.join() { Ok(()) => {}, Err(_) => {} } }
        """
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(alias)

    def test_async_string_merge_return_does_not_retain_consumed_source_pool(self):
        template = """
            async fn combine(mut destination: -> String, source: -> String) -> <- String {
                yield;
                destination.merge(-> source);
                yield;
                return <- destination;
            }
            fn main() {
                let mut destinations = pool<String>(1);
                let mut destination = destinations.new(); destination.push_str("PREFIX");
                address(destination);
                let result = {
                    destination ->;
                    let mut sources = pool<String>(1);
                    let mut source = sources.new(); source.push_str("SUFFIX");
                    let h = runtime::spawn(-> combine(-> destination, -> source));
                    let value = match h.join() {
                        Ok(value) => { <- value },
                        Err(_) => {
                            let mut fallback = destinations.new(); fallback.push_str("fallback");
                            <- fallback
                        }
                    };
                    <- value
                };
                address(result); print(&result[..]);
            }
        """
        for prefix, suffix in (('', ''), ('a', 'b'), ('é', '🌍'), ('é', '🐈'), ('', 'é'), ('🌍', '')):
            source = template.replace('PREFIX', prefix).replace('SUFFIX', suffix)
            with self.subTest(prefix=prefix, suffix=suffix):
                before, after, text = self.run_c_oracle(compile_source(source)).stdout.splitlines()
                self.assertEqual(before, after)
                self.assertEqual(text, prefix + suffix)
        source = template.replace('PREFIX', 'é').replace('SUFFIX', '🌍')
        failed = compile_source(source).replace('#include <pthread.h>', '#include <pthread.h>\n'
            '#define pthread_create(thread, attr, runner, pointer) EAGAIN', 1)
        before, after, text = self.run_c_oracle(failed).stdout.splitlines()
        self.assertEqual((after, text), (before, 'fallback'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('return <- destination;', 'return <- source;'))

    def test_async_shared_vector_slice_order_and_subslice_bounds(self):
        source = """
            async fn index(value: Int) -> Int { print(value); yield; return value; }
            async fn tail(view: &[Int], start: Int) -> &[Int] {
                yield;
                return &view[index(start).await..];
            }
            async fn run(v: &Vector<Int>, start: Int) -> Int {
                let view: &[Int] = &v[1..];
                let part = tail(view, start).await;
                yield;
                let child = runtime::spawn(-> tail(part, 0));
                return match child.await { Ok(result) => { result[0] }, Err(_) => { 98 } };
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2);
                BLOCKER
                let mut v = p.new();
                v.push(10); v.push(20); v.push(30); v.push(40);
                let h = runtime::spawn(-> run(&v, START));
                match h.join() { Ok(result) => { print(result); }, Err(_) => { print(99); } }
            }
        """
        data = [10,20,30,40]
        for reverse in (False, True):
            prepared = source.replace('BLOCKER', 'let mut first = p.new(); first.push(0);' if reverse else '')
            for start in (0,1,2):
                with self.subTest(reverse=reverse, start=start):
                    view = data[1+start:]
                    code = compile_source(prepared.replace('START', str(start)))
                    marker = ('static VectorSlice vector_subslice(VectorSlice slice, int start, int end, '
                              'int has_end, size_t element_size) {')
                    self.assertEqual(code.count(marker), 1)
                    code = code.replace(marker, marker +
                                        f'\n    if (slice.length && slice.descends != {int(reverse)}) abort();', 1)
                    self.assertEqual(self.run_c_oracle(code).stdout, f'{start}\n0\n{view[0]}\n')
        invalid_bound = source.replace('BLOCKER','').replace('START','4')
        self.run_c_oracle(compile_source(invalid_bound), 'bornes de tranche de Vector invalides')
        self.run_c_oracle(compile_source(invalid_bound.replace('run(&v, 4)','run(&v, 3)')),
                          'indice de tranche de Vector hors limites')
        for expression, diagnostic in (
            ('let view: &[u8] = &v[1..];', 'tranche u8'),
            ('let view: &[Int] = &v[2..1];', 'bornes de tranche'),
            ('let view: &[Int] = &v[1..]; view[0] = 100;', 'tranche partagée'),
        ):
            with self.subTest(expression=expression), self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid_bound.replace('let view: &[Int] = &v[1..];', expression))

        for mode in ('', 'mut '):
            with self.subTest(mode=mode), self.assertRaisesRegex(Error, 'emprunt Int.*tranche'):
                verify_program(f"""
                    async fn inspect(value: &{mode}Int) {{ print(*value); }}
                    async fn run(v: &Vector<Int>) {{
                        let mut view = &v[..];
                        let child = inspect(&{mode}view);
                        child.await;
                    }}
                    fn main() {{}}
                """)

    def test_async_shared_vector_slice_join_retains_both_contract_origins(self):
        source = """
            async fn tail(view: &[u8], start: Int) -> &[u8] {
                yield;
                return &view[start..];
            }
            fn launch(source: &[u8]) -> <- Execution<tail> {
                let h = runtime::spawn(-> tail(source,1));
                return <- h;
            }
            fn finish(h: -> Execution<tail>, fallback: &[u8]) -> &[u8] {
                return match h.join() { Ok(part) => { part }, Err(_) => { fallback } };
            }
            fn main() {
                let mut texts = pool<String>(1); let mut s = texts.new(); s.push_str("é");
                let mut p = pool<Vector<u8>>(2); let mut v = p.new(); let mut backup = p.new();
                v.push(120); v.push(97); v.push(98);
                backup.push(121); backup.push(122);
                let h = launch(&v[..]);
                BEFORE_JOIN
                let part = finish(-> h,&backup[..]);
                BEFORE_USE
                match s.replace_bytes(0,part) { Ok(()) => { print(&s[..]); }, Err(_) => { print(99); } }
                v.push(110);
                backup.push(111);
            }
        """
        valid = source.replace('BEFORE_JOIN','').replace('BEFORE_USE','')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, 'ab\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, 'yz\n')
        from_vector = source.replace('view: &[u8]', 'view: &Vector<u8>').replace(
            'source: &[u8]', 'source: &Vector<u8>').replace('launch(&v[..])','launch(&v)')
        self.assertEqual(self.run_c_oracle(compile_source(from_vector.replace('BEFORE_JOIN','')
                                                        .replace('BEFORE_USE',''))).stdout, 'ab\n')
        for template in (source, from_vector):
            for marker, statement in (
                ('BEFORE_JOIN','v.push(101);'),
                ('BEFORE_USE','v.push(102);'),
                ('BEFORE_USE','backup.push(103);'),
                ('BEFORE_USE','drop(-> v);'),
            ):
                with self.subTest(marker=marker, statement=statement, from_vector=template==from_vector):
                    candidate = template.replace(marker,statement).replace('BEFORE_JOIN','').replace('BEFORE_USE','')
                    diagnostic = 'emprunt encore utilisé' if statement.startswith('drop') else 'emprunt actif'
                    with self.assertRaisesRegex(Error, diagnostic):
                        verify_program(candidate)

    def test_async_shared_vector_slice_reassignment_and_loop_sources(self):
        source = """
            async fn work(a: &mut Vector<Int>, b: &mut Vector<Int>, count: Int) -> Int {
                let mut view = &a[..];
                let mut i = 0;
                let mut sum = 0;
                while i < count {
                    BEFORE
                    sum = sum + view[0];
                    view = &b[..];
                    i = i + 1;
                    yield;
                }
                a.push(77);
                b.push(88);
                return sum;
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut a = p.new(); let mut b = p.new();
                a.push(10); b.push(20);
                let h = runtime::spawn(-> work(&mut a,&mut b,COUNT));
                match h.join() { Ok(result) => { print(result); }, Err(_) => { print(99); } }
            }
        """
        for count in (0,1,3):
            values = [10] + [20]*count
            program = source.replace('COUNT',str(count)).replace('BEFORE','')
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, f'{sum(values[:count])}\n')
        for target in ('a','b'):
            with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('COUNT','3').replace('BEFORE',f'{target}.push(70);'))

    def test_async_shared_vector_slice_bounds_preserve_the_receiver_snapshot(self):
        source = """
            async fn work(a: &mut Vector<Int>, b: &mut Vector<Int>, choose: Bool) -> Int {
                let mut view = &a[..];
                let old = &view[if choose { view = &b[..]; IN_BOUND 0 } else { view = &b[..]; 1 }..];
                yield;
                BEFORE_READ
                let first = old[0];
                a.push(9);
                return first + view[0];
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut a = p.new(); let mut b = p.new();
                a.push(10); a.push(11); b.push(20);
                let h = runtime::spawn(-> work(&mut a, &mut b, CHOOSE));
                match h.join() { Ok(result) => { print(result); }, Err(_) => { print(99); } }
            }
        """
        for condition, offset in (('true', 0), ('false', 1)):
            program = source.replace('CHOOSE', condition).replace('IN_BOUND', '').replace('BEFORE_READ', '')
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, f'{[10, 11][offset] + 20}\n')
        for position in ('IN_BOUND', 'BEFORE_READ'):
            invalid = source.replace('CHOOSE', 'true').replace(position, 'a.push(9);')
            with self.subTest(position=position), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(invalid.replace('IN_BOUND', '').replace('BEFORE_READ', ''))

    def test_async_shared_vector_slice_bounds_do_not_become_result_origins(self):
        source = """
            async fn tail(view: &[Int], bounds: &[Int]) -> &[Int] {
                yield;
                return &view[bounds[0]..];
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut data = p.new(); let mut bounds = p.new();
                data.push(10); data.push(20); bounds.push(1);
                let h = runtime::spawn(-> tail(&data[..], &bounds[..]));
                match h.join() {
                    Ok(part) => { bounds.push(0); print(part[0]); data.push(30); },
                    Err(_) => { print(99); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '20\n')
        for invalid in (
            source.replace('bounds.push(0);', 'data.push(0);'),
            source.replace('match h.join()', 'bounds.push(0); match h.join()'),
        ):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(invalid)

    def test_async_shared_vector_slice_byte_reads_and_replacement(self):
        source = """
            async fn identity(part: &[u8]) -> &[u8] { yield; return part; }
            async fn work(s: &mut String, bytes: &mut Vector<u8>) {
                let view = &bytes[1..];
                let part = identity(view).await;
                let alias = &part[0];
                yield;
                BEFORE
                s.replace_bytes(0,&part[..2]);
                s.replace_byte(1,*alias);
                s.replace_byte(0,part[1]);
                bytes.push(100);
            }
            fn main() {
                let mut strings = pool<String>(1); let mut s = strings.new(); s.push_str("é");
                let mut vectors = pool<Vector<u8>>(1); let mut bytes = vectors.new();
                bytes.push(120); bytes.push(97); bytes.push(98);
                let h = runtime::spawn(-> work(&mut s,&mut bytes));
                match h.join() { Ok(()) => { print(&s[..]); }, Err(_) => { print(99); } }
                print(bytes.len());
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE',''))).stdout, 'ba\n4\n')
        conflict = source.replace('BEFORE','bytes.push(103);')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conflict)
        released = source.replace('let part = identity(view).await;',
                                  'let pending = identity(view); drop(-> pending); let part = &bytes[1..];')
        self.assertEqual(self.run_c_oracle(compile_source(released.replace('BEFORE',''))).stdout, 'ba\n4\n')

    def test_async_shared_vector_slice_returns_a_byte_loan_through_join(self):
        source = """
            async fn first(view: &[u8], i: Int) -> &u8 { yield; return &view[i]; }
            async fn pick(v: &Vector<u8>) -> &u8 {
                let value = { let view = &v[1..]; first(view, 0).await };
                yield;
                return value;
            }
            fn main() {
                let mut texts = pool<String>(1); let mut text = texts.new(); text.push_str("a");
                let mut vectors = pool<Vector<u8>>(1); let mut v = vectors.new();
                v.push(97); v.push(98);
                let h = runtime::spawn(-> pick(&v));
                match h.join() {
                    Ok(value) => {
                        BEFORE
                        match text.replace_byte(0,*value) {
                            Ok(_) => { print(&text[..]); }, Err(_) => { print(98); }
                        }
                        AFTER
                    },
                    Err(_) => { print(99); }
                }
                print(v.len());
            }
        """
        valid = source.replace('BEFORE', '').replace('AFTER', 'v.push(99);')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, 'b\n3\n')
        invalid = source.replace('BEFORE', 'v.push(99);').replace('AFTER', '')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(invalid)

    def test_async_shared_vector_slice_reborrows_a_mutable_parent_for_reading(self):
        source = """
            async fn tail(v: &mut Vector<Int>) -> &[Int] { yield; return &v[1..]; }
            async fn size(v: &Vector<Int>) -> Int { yield; return v.len(); }
            async fn sum(a: &[Int], b: &[Int]) -> Int { yield; return a[0] + b[0]; }
            async fn work(v: &mut Vector<Int>) -> Int {
                let first = tail(v).await;
                let second = &v[..];
                let child = runtime::spawn(-> sum(first, second));
                BEFORE_JOIN
                let length = size(v).await;
                let total = match child.await { Ok(value) => { value }, Err(_) => { 99 } };
                BEFORE_READ
                let result = total + length + first[0];
                v.push(30);
                return result;
            }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                let h = runtime::spawn(-> work(&mut v));
                match h.join() { Ok(result) => { print(result); }, Err(_) => { print(99); } }
                print(v.len());
            }
        """
        valid = source.replace('BEFORE_JOIN', '').replace('BEFORE_READ', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '52\n3\n')
        for point in ('BEFORE_JOIN', 'BEFORE_READ'):
            with self.subTest(point=point), self.assertRaisesRegex(Error, 'emprunt actif'):
                invalid = source.replace(point, 'v.push(30);')
                verify_program(invalid.replace('BEFORE_JOIN', '').replace('BEFORE_READ', ''))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(valid.replace('let length = size(v).await;', 'let length = tail(v).await[0];'))

    def test_sync_launch_of_vector_reborrow_keeps_the_named_parent_through_join(self):
        source = """
            async fn tail(v: &mut Vector<Int>) -> &[Int] {
                v.push(30);
                yield;
                return &v[1..];
            }
            fn launch(v: &mut Vector<Int>) -> <- Execution<tail> {
                let h = runtime::spawn(-> tail(v));
                return <- h;
            }
            fn relay(v: &mut Vector<Int>) -> Int {
                let h = LAUNCH;
                BEFORE_JOIN
                return match h.join() {
                    Ok(part) => {
                        BEFORE_USE
                        let result = part[0] + v.len();
                        v.push(40);
                        result
                    },
                    Err(_) => { v.push(50); v.len() }
                };
            }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                print(relay(&mut v)); print(v.len());
            }
        """
        for launch in ('runtime::spawn(-> tail(v))', 'launch(v)'):
            with self.subTest(launch=launch):
                template = source.replace('LAUNCH', launch)
                valid = template.replace('BEFORE_JOIN', '').replace('BEFORE_USE', '')
                code = compile_source(valid)
                self.assertEqual(self.run_c_oracle(code).stdout, '23\n4\n')
                failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                      '#define pthread_create(t,a,r,p) EAGAIN', 1)
                self.assertEqual(self.run_c_oracle(failed).stdout, '3\n3\n')
                for position, action in (
                    ('BEFORE_JOIN', 'print(v.len());'),
                    ('BEFORE_JOIN', 'v.push(60);'),
                    ('BEFORE_USE', 'v.push(60);'),
                ):
                    with self.subTest(position=position, action=action), self.assertRaisesRegex(Error, 'emprunt actif'):
                        invalid = template.replace(position, action).replace('BEFORE_JOIN', '').replace('BEFORE_USE', '')
                        verify_program(invalid)
        owner = source[:source.index('            fn relay')] + """
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                let h = LAUNCH;
                match h.join() { Ok(part) => { print(v.len()); print(part[0]); }, Err(_) => {} }
            }
        """
        for launch in ('runtime::spawn(-> tail(&mut v))', 'launch(&mut v)'):
            with self.subTest(owner_launch=launch), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(owner.replace('LAUNCH', launch))

    def test_sync_launch_shared_vector_reborrow_allows_reads_while_pending(self):
        source = """
            async fn observe(v: &Vector<Int>) -> Int { yield; return v.len(); }
            fn launch(v: &mut Vector<Int>) -> <- Execution<observe> {
                let h = runtime::spawn(-> observe(v));
                return <- h;
            }
            fn relay(v: &mut Vector<Int>) -> Int {
                let h = LAUNCH;
                BEFORE
                let part = &v[..];
                let length = v.len();
                return match h.join() { Ok(n) => { n + length + part[0] }, Err(_) => { 99 } };
            }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                print(relay(&mut v)); v.push(30); print(v.len());
            }
        """
        for launch in ('runtime::spawn(-> observe(v))', 'launch(v)'):
            with self.subTest(launch=launch):
                template = source.replace('LAUNCH', launch)
                self.assertEqual(self.run_c_oracle(compile_source(template.replace('BEFORE', ''))).stdout, '14\n3\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(template.replace('BEFORE', 'v.push(30);'))

    def test_sync_launch_vector_reborrow_keeps_both_contract_alternatives(self):
        source = """
            async fn tail(v: &mut Vector<Int>) -> &[Int] { v.push(90); yield; return &v[1..]; }
            fn choose(a: &mut Vector<Int>, b: &mut Vector<Int>, side: Int) -> <- Execution<tail> {
                let h = if side == 1 {
                    let left = runtime::spawn(-> tail(a));
                    <- left
                } else {
                    let right = runtime::spawn(-> tail(b));
                    <- right
                };
                return <- h;
            }
            fn relay(a: &mut Vector<Int>, b: &mut Vector<Int>, side: Int) -> Int {
                let h = choose(a,b,side);
                BEFORE_JOIN
                return match h.join() {
                    Ok(part) => {
                        BEFORE_USE
                        let result = part[0] + a.len() + b.len();
                        a.push(80); b.push(81);
                        result
                    },
                    Err(_) => { 99 }
                };
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut a = p.new(); a.push(10); a.push(11);
                let mut b = p.new(); b.push(20); b.push(21);
                print(relay(&mut a,&mut b,CHOICE)); print(a.len()); print(b.len());
            }
        """
        for choice in (0, 1):
            values = [[10, 11], [20, 21]]
            selected = values[1 - choice]
            selected.append(90)
            result = selected[1] + sum(map(len, values))
            expected = f'{result}\n{len(values[0]) + 1}\n{len(values[1]) + 1}\n'
            program = source.replace('CHOICE', str(choice)).replace('BEFORE_JOIN', '').replace('BEFORE_USE', '')
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, expected)
        for target in ('a', 'b'):
            for point in ('BEFORE_JOIN', 'BEFORE_USE'):
                with self.subTest(target=target, point=point), self.assertRaisesRegex(Error, 'emprunt actif'):
                    invalid = source.replace('CHOICE', '0').replace(point, f'{target}.push(42);')
                    verify_program(invalid.replace('BEFORE_JOIN', '').replace('BEFORE_USE', ''))

    def test_sync_launch_vector_reborrow_checks_scope_drop_and_argument_order(self):
        source = """
            async fn inspect(v: &Vector<Int>) -> Int { yield; return v.len(); }
            async fn pair(a: &Vector<Int>, b: &mut Vector<Int>) -> Int { b.push(7); return a.len(); }
            fn launch(v: &Vector<Int>) -> <- Execution<inspect> {
                let h = runtime::spawn(-> inspect(v)); return <- h;
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut v = p.new(); v.push(5);
                let h = { let active = launch(&v); <- active };
                AFTER_LAUNCH
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                drop(-> v);
                let mut next = p.new(); next.push(7); print(next.len());
            }
        """
        valid = source.replace('AFTER_LAUNCH', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '1\n1\n')
        for invalid, diagnostic in (
            (valid.replace('let active = launch(&v);', 'let local = p.new(); let active = launch(&local);'),
             'non durable'),
            (source.replace('AFTER_LAUNCH', 'drop(-> v);'), 'emprunt encore utilisé'),
            (valid.replace('let h = { let active = launch(&v); <- active };',
                           'let h = runtime::spawn(-> pair(&v, &mut v));'), 'emprunt actif'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_sync_launch_explicit_vector_reborrow_preserves_parent_and_mode(self):
        source = """
            fn length(v: &Vector<Int>) -> Int { return v.len(); }
            async fn size(v: &Vector<Int>) -> Int { yield; return v.len(); }
            async fn tail(v: &mut Vector<Int>) -> &[Int] { v.push(30); yield; return &v[1..]; }
            fn launch(v: &mut Vector<Int>) -> <- Execution<tail> {
                let h = runtime::spawn(-> tail(&mut *v));
                return <- h;
            }
            fn worker(v: &mut Vector<Int>) -> Int {
                let first = runtime::spawn(-> size(&*v));
                let second = runtime::spawn(-> size(&*v));
                let initial = length(&*v);
                let left = match first.join() { Ok(n) => { n }, Err(_) => { 99 } };
                PENDING_SHARED
                let right = match second.join() { Ok(n) => { n }, Err(_) => { 99 } };
                let next = launch(&mut *v);
                PENDING_MUTABLE
                return match next.join() {
                    Ok(part) => { initial + left + right + part[0] + length(&*v) },
                    Err(_) => { 99 }
                };
            }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                print(worker(&mut v)); print(v.len());
            }
        """
        valid = source.replace('PENDING_SHARED', '').replace('PENDING_MUTABLE', '')
        for program in (valid, valid.replace('size(&*v)', 'size(v)').replace('length(&*v)', 'length(v)')):
            self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '29\n3\n')
        for invalid, diagnostic in (
            (valid.replace('size(&*v)', 'size(&v)'), 'emprunt imbriqué'),
            (valid.replace('length(&*v)', 'length(&v)'), 'emprunt imbriqué'),
            (valid.replace('tail(&mut *v)', 'tail(&mut v)'), 'emprunt imbriqué'),
            (valid.replace('size(&*v)', 'size(&mut *v)'), 'mode incompatible'),
            (valid.replace('fn launch(v: &mut Vector<Int>)', 'fn launch(v: &Vector<Int>)'), 'référence mutable'),
            (valid.replace('worker(&mut v)', 'worker(&mut *v)'), 'emprunt explicite requis'),
            (source.replace('PENDING_SHARED', 'v.push(40);').replace('PENDING_MUTABLE', ''), 'emprunt actif'),
            (source.replace('PENDING_SHARED', '').replace('PENDING_MUTABLE', 'print(length(&*v));'), 'emprunt actif'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(invalid)

    def test_async_local_vector_split_keeps_disjoint_halves_across_suspensions(self):
        source = """
            async fn number(n: Int) -> Int { print(n); yield; return n; }
            async fn work(v: &mut Vector<Int>) -> Int {
                let (mut left, mut right) = v.split_at_mut(number(PIVOT).await);
                yield;
                BEFORE
                left[INDEX] = right[0] + number(5).await;
                let (mut middle, mut last) = right.split_at_mut(1);
                BEFORE_CHILD
                middle[0] = left[0];
                last[0] = middle[0] + 1;
                let result = left[0] + middle[0] + last[0];
                v.push(40);
                return result;
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2);
                BLOCKER
                let mut v = p.new(); v.push(10); v.push(20); v.push(30); v.push(35);
                let h = runtime::spawn(-> work(&mut v));
                match h.join() { Ok(result) => { print(result); }, Err(_) => { print(99); } }
                print(v.len());
            }
        """
        data = [10, 20, 30, 35]
        left, right = data[:2], data[2:]
        left[0] = right[0] + 5
        middle, last = right[:1], right[1:]
        middle[0] = left[0]
        last[0] = middle[0] + 1
        expected = f'2\n5\n{left[0] + middle[0] + last[0]}\n{len(data) + 1}\n'
        normal = source.replace('PIVOT', '2').replace('INDEX', '0').replace('BEFORE_CHILD', '').replace('BEFORE', '')
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                blocker = 'let mut other = p.new(); other.push(0);' if reverse else ''
                code = compile_source(normal.replace('BLOCKER', blocker))
                marker = 'static VectorSplit vector_split_at_mut(Cell *cell, int index) {\n    VectorItems *items = vector_items(cell);'
                self.assertEqual(code.count(marker), 1)
                code = code.replace(marker, marker + f'\n    if (vector_descends(items) != {int(reverse)}) abort();')
                self.assertEqual(self.run_c_oracle(code).stdout, expected)
        clean = normal.replace('BLOCKER', '')
        bound = clean.replace('number(2).await', 'number(5).await')
        index = clean.replace('left[0] = right[0]', 'left[2] = right[0]')
        self.assertEqual(self.run_c_oracle(compile_source(bound), 'indice de séparation de Vector hors limites').stdout,
                         '5\n')
        self.assertEqual(self.run_c_oracle(compile_source(index), 'indice de tranche de Vector hors limites').stdout,
                         '2\n')
        for statement, point, diagnostic in (
            ('print(v.len());', 'BEFORE', 'emprunt actif'),
            ('v.push(9);', 'BEFORE', 'emprunt actif'),
            ('right[0] = 9;', 'BEFORE_CHILD', 'emprunt actif'),
            ('let alias = left;', 'BEFORE', 'reçu une tranche'),
            ('left = &right[..];', 'BEFORE', 'affectation de tranche mutable'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                program = source.replace('PIVOT', '2').replace('INDEX', '0').replace('BLOCKER', '')
                program = program.replace('BEFORE_CHILD', statement if point == 'BEFORE_CHILD' else '')
                verify_program(program.replace('BEFORE', statement if point == 'BEFORE' else ''))

    def test_async_local_vector_split_shared_byte_reborrow_keeps_only_its_half_frozen(self):
        source = """
            async fn relay(part: &[u8]) -> &[u8] { yield; return part; }
            async fn work(v: &mut Vector<u8>, s: &mut String) {
                {
                    let (mut left, mut right) = v.split_at_mut(1);
                    let view = relay(&*left).await;
                    yield;
                    BEFORE
                    right[0] = 98;
                    s.replace_bytes(0, view);
                    left[0] = right[0];
                    s.replace_bytes(1, &left[..]);
                }
                v.push(100);
            }
            fn main() {
                let mut texts = pool<String>(1); let mut s = texts.new(); s.push_str("xx");
                let mut p = pool<Vector<u8>>(1); let mut v = p.new(); v.push(97); v.push(99);
                let h = runtime::spawn(-> work(&mut v, &mut s));
                match h.join() { Ok(()) => { print(&s[..]); }, Err(_) => { print(99); } }
                print(v.len());
            }
        """
        valid = source.replace('BEFORE', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, 'ab\n3\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'left[0] = 120;'))
        with self.assertRaisesRegex(Error, 'tranche u8'):
            verify_program(valid.replace('relay(&*left)', 'relay(left)'))

    def test_async_split_shared_result_keeps_storage_across_control_boundaries(self):
        source = """
            async fn relay(view: &[Int]) -> &[Int] { yield; return view; }
            async fn tail(v: &mut Vector<Int>, bounds: &[Int], choose: Bool) -> &[Int] { BODY }
            fn run(v: &mut Vector<Int>, bounds: &mut Vector<Int>) -> Int {
                let h = runtime::spawn(-> tail(v, &bounds[..], true));
                BEFORE_JOIN
                return match h.join() {
                    Ok(part) => {
                        bounds.push(0);
                        BEFORE_USE
                        let n = v.len() + part[0];
                        v.push(40);
                        n
                    },
                    Err(_) => { 99 }
                };
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut v = p.new(); let mut bounds = p.new();
                v.push(10); v.push(20); bounds.push(1);
                print(run(&mut v,&mut bounds)); print(v.len()); print(bounds.len());
            }
        """
        split = 'let (mut left, mut right) = v.split_at_mut(bounds[0]);'
        for body in (
            f'{split} yield; return &*right;',
            f'let part = {{ {split} yield; &*right }}; return part;',
            f'let part = if choose {{ {split} &*right }} else {{ &v[1..] }}; return part;',
            f'let part = loop {{ {split} break &*right; }}; return part;',
            f'let mut part = &v[..]; {{ {split} part = &*right; }} return part;',
            f'let task = {{ {split} let child = relay(&*right); <- child }}; return task.await;',
            f'let h = {{ {split} let child = runtime::spawn(-> relay(&*right)); <- child }}; '
            'return match h.await { Ok(part) => { part }, Err(_) => { &v[1..] } };',
        ):
            with self.subTest(body=body):
                program = source.replace('BODY', body)
                valid = program.replace('BEFORE_JOIN', '').replace('BEFORE_USE', '')
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '22\n3\n2\n')
                for invalid in (
                    program.replace('BEFORE_JOIN', 'bounds.push(0);').replace('BEFORE_USE', ''),
                    program.replace('BEFORE_JOIN', '').replace('BEFORE_USE', 'v.push(0);'),
                ):
                    with self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(invalid)
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(f'async fn bad(mut v: -> Vector<Int>, bounds: &[Int]) -> &[Int] '
                           f'{{ {split} return &*right; }} fn main() {{}}')
        for body in (
            f'let part = {{ {split} &*right }}; v.push(0); return part;',
            f'let mut part = &v[..]; {{ {split} part = &*right; }} v.push(0); return part;',
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('BODY', body).replace('BEFORE_JOIN', '').replace('BEFORE_USE', ''))
        with self.assertRaisesRegex(Error, 'cible interdit pendant un emprunt actif'):
            verify_program(f'''
                async fn bad(mut v: -> Vector<Int>, bounds: &[Int]) -> Int {{
                    let view = loop {{ v ->; {split} <- v; break &*right; }};
                    return view[0];
                }}
                fn main() {{}}
            ''')

    def test_async_split_shared_byte_result_allows_reads_through_its_mutable_parent(self):
        source = """
            async fn select_byte(v: &mut Vector<u8>) -> &u8 {
                let (mut left, mut right) = v.split_at_mut(1);
                yield;
                return &right[0];
            }
            async fn run(v: &mut Vector<u8>, text: &mut String) -> Int {
                let byte = select_byte(v).await;
                BEFORE
                let length = v.len();
                text.replace_byte(0, *byte);
                v.push(99);
                return length;
            }
            fn main() {
                let mut texts = pool<String>(1); let mut text = texts.new(); text.push_str("x");
                let mut p = pool<Vector<u8>>(1); let mut v = p.new(); v.push(97); v.push(98);
                let h = runtime::spawn(-> run(&mut v, &mut text));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(&text[..]); print(v.len());
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE', ''))).stdout, '2\nb\n3\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'v.push(99);'))

    def test_async_split_shared_capture_checks_storage_on_task_scope_exit(self):
        source = """
            async fn read(view: &[Int]) -> Int { yield; return view[0]; }
            async fn run(mut v: -> Vector<Int>, mut replacement: -> Vector<Int>, flag: Bool) -> Int {
                let task = SOURCE;
                replacement.push(73);
                return task.await;
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut v = p.new(); v.push(42);
                let replacement = p.new();
                let h = runtime::spawn(-> run(-> v, -> replacement, true));
                match h.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
            }
        """
        for capture in ('let t = read(&v[..]);',
                        'let (mut left, mut right) = v.split_at_mut(0); let t = read(&*right);'):
            for control in (
                f'{{ ENTER {capture} EXIT <- t }}',
                f'loop {{ ENTER {capture} EXIT break <- t; }}',
                f'if flag {{ ENTER {capture} EXIT <- t }} else {{ ENTER {capture} EXIT <- t }}',
            ):
                with self.subTest(control=control):
                    program = source.replace('SOURCE', control)
                    valid = program.replace('ENTER', '').replace('EXIT', '')
                    self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '42\n')
                    imported = program.replace('ENTER', 'v ->;')
                    with self.assertRaisesRegex(Error, 'non durable'):
                        verify_program(imported.replace('EXIT', ''))
                    with self.assertRaisesRegex(Error, 'cible interdit pendant un emprunt actif'):
                        verify_program(imported.replace('EXIT', '<- v;'))

    def test_async_mutable_slice_captures_allow_disjoint_workers_and_suspend_each_parent(self):
        source = """
            async fn edit(part: &mut [Int], value: Int) -> Int {
                yield;
                part[0] = value;
                return part[0];
            }
            fn launch(part: &mut [Int], value: Int) -> <- Execution<edit> {
                let h = runtime::spawn(-> edit(part, value)); return <- h;
            }
            async fn work(v: &mut Vector<Int>) -> Int {
                let (mut left, mut right) = v.split_at_mut(1);
                let pending = edit(left, 80);
                UNSTARTED
                drop(-> pending);
                let l = runtime::spawn(-> edit(left, 300));
                let r = runtime::spawn(-> edit(&mut *right, 400));
                DURING_WORK
                let a = match l.await { Ok(n) => { n }, Err(_) => { 99 } };
                BETWEEN
                let after_left = left[0];
                let b = match r.await { Ok(n) => { n }, Err(_) => { 99 } };
                return a + b + after_left + right[0];
            }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                MAIN
            }
        """
        async_main = ('let h = runtime::spawn(-> work(&mut v)); '
                      'match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }')
        sync_main = """
            let (mut left, mut right) = v.split_at_mut(1);
            let l = runtime::spawn(-> edit(&mut *left, 300));
            let r = launch(right,400);
            SYNC_ACTIVE
            match l.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            SYNC_BETWEEN
            print(left[0]);
            match r.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            print(right[0]);
        """

        def with_workers(code):
            header = 'static CrustTaskStep crust_async_edit_resume(CrustTask *task) {\n'
            marker = header + '    crust_async_edit_state *frame = (crust_async_edit_state *)task;\n    switch (frame->pc)'
            self.assertEqual(code.count(marker), 1)
            return code.replace(marker, header + '''    crust_async_edit_state *frame = (crust_async_edit_state *)task;
    static atomic_int crust_test_ready;
    if (frame->pc == 0) {
        atomic_fetch_add(&crust_test_ready, 1);
        while (atomic_load(&crust_test_ready) < 2) sched_yield();
    }
    switch (frame->pc)''')

        async_template = source.replace('MAIN', async_main)
        # Fill the top-level markers before substituting the synchronous body.
        synchronous = (source.replace('UNSTARTED', '').replace('DURING_WORK', '').replace('BETWEEN', '')
                       .replace('MAIN', sync_main))
        valid = async_template.replace('UNSTARTED', '').replace('DURING_WORK', '').replace('BETWEEN', '')
        self.assertEqual(self.run_c_oracle(with_workers(compile_source(valid))).stdout, '1400\n')
        valid_sync = synchronous.replace('SYNC_ACTIVE', '').replace('SYNC_BETWEEN', '')
        self.assertEqual(self.run_c_oracle(with_workers(compile_source(valid_sync))).stdout, '300\n300\n400\n400\n')
        for marker, action in (
            ('UNSTARTED', 'left[0] = 50;'),
            ('DURING_WORK', 'let duplicate = edit(left, 50);'),
            ('BETWEEN', 'print(right[0]);'),
        ):
            invalid = async_template.replace(marker, action).replace('UNSTARTED', '').replace('DURING_WORK', '').replace('BETWEEN', '')
            with self.subTest(marker=marker), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(invalid)
        for marker, action in (
            ('SYNC_ACTIVE', 'let duplicate = launch(left, 50);'),
            ('SYNC_BETWEEN', 'print(right[0]);'),
            ('SYNC_BETWEEN', 'v.push(50);'),
        ):
            invalid = synchronous.replace(marker, action).replace('SYNC_ACTIVE', '').replace('SYNC_BETWEEN', '')
            with self.subTest(marker=marker, action=action), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(invalid)

    def test_async_mutable_slice_capture_transfers_a_shared_result_without_losing_its_half(self):
        source = """
            async fn update(part: &mut [u8]) -> &[u8] { part[0] = 98; yield; return &*part; }
            fn launch(part: &mut [u8]) -> <- Execution<update> {
                let h = runtime::spawn(-> update(part)); return <- h;
            }
            fn main() {
                let mut p = pool<Vector<u8>>(1); let mut v = p.new(); v.push(97); v.push(99);
                let (mut left, mut right) = v.split_at_mut(1);
                let h = launch(left);
                BEFORE_JOIN
                right[0] = 100;
                match h.join() {
                    Ok(part) => {
                        BEFORE_USE
                        match str::from_utf8(part) { Ok(text) => { print(text); }, Err(_) => { print(98); } }
                        left[0] = 101;
                    },
                    Err(_) => { left[0] = 102; print(99); }
                }
                match str::from_utf8(&v[..]) { Ok(text) => { print(text); }, Err(_) => { print(98); } }
            }
        """
        valid = source.replace('BEFORE_JOIN', '').replace('BEFORE_USE', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, 'b\ned\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\nfd\n')
        for position in ('BEFORE_JOIN', 'BEFORE_USE'):
            with self.subTest(position=position), self.assertRaisesRegex(Error, 'emprunt actif'):
                invalid = source.replace(position, 'left[0] = 102;')
                verify_program(invalid.replace('BEFORE_JOIN', '').replace('BEFORE_USE', ''))
        with self.assertRaisesRegex(Error, 'tranche mutable'):
            verify_program(valid.replace('launch(left)', 'update(&*left)'))

        awaited = """
            async fn update(part: &mut [u8]) -> &[u8] { part[0] = 98; yield; return &*part; }
            async fn run(v: &mut Vector<u8>, text: &mut String) {
                let (mut left, mut right) = v.split_at_mut(1);
                let part = update(left).await;
                BEFORE
                right[0] = 100;
                text.replace_bytes(0, part);
                text.replace_bytes(1, &right[..]);
                left[0] = 101;
            }
            fn main() {
                let mut p = pool<Vector<u8>>(1); let mut v = p.new(); v.push(97); v.push(99);
                let mut strings = pool<String>(1); let mut text = strings.new(); text.push_str("xx");
                let h = runtime::spawn(-> run(&mut v, &mut text));
                match h.join() { Ok(()) => { print(&text[..]); }, Err(_) => { print(99); } }
                match str::from_utf8(&v[..]) { Ok(s) => { print(s); }, Err(_) => { print(98); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(awaited.replace('BEFORE', ''))).stdout, 'bd\ned\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(awaited.replace('BEFORE', 'left[0] = 102;'))

    def test_async_mutable_slice_capture_needs_durable_storage_after_scope_transfer(self):
        source = """
            async fn edit(part: &mut [Int]) -> Int { yield; part[0] = 80; return part[0]; }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10);
                let h = {
                    ENTER
                    let (mut left, mut right) = v.split_at_mut(0);
                    let inner = runtime::spawn(-> edit(right));
                    <- inner
                };
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(v[0]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('ENTER', ''))).stdout, '80\n80\n')
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(source.replace('ENTER', 'v ->;'))

    def test_async_mutable_slice_return_preserves_the_loan_through_await_and_spawn(self):
        source = """
            async fn relay(part: &mut [Int]) -> &mut [Int] { yield; return part; }
            async fn tail(v: &mut Vector<Int>) -> &mut [Int] {
                let (mut left, mut right) = v.split_at_mut(1);
                yield;
                return relay(right).await;
            }
            async fn edit(part: &mut [Int]) { yield; part[0] = 40; }
            async fn run(v: &mut Vector<Int>) -> Int {
                let (mut left, mut right) = v.split_at_mut(1);
                BODY
                return left[0] + right[0];
            }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                MAIN
            }
        """
        main = ('let h=runtime::spawn(-> run(&mut v)); '
                'match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }')
        for body in (
            'let out = relay(right).await; CHECK left[0] = 30; out[0] = 40;',
            'let out = { let child = relay(right); child.await }; CHECK left[0] = 30; out[0] = 40;',
            'let h = runtime::spawn(-> relay(right)); let result = h.await; CHECK left[0] = 30; '
            'match result { Ok(out) => { out[0] = 40; }, Err(_) => { right[0] = 80; } }',
        ):
            with self.subTest(body=body):
                program = source.replace('BODY', body).replace('MAIN', main)
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('CHECK', ''))).stdout, '70\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('CHECK', 'print(right[0]);'))
        forwarded = source.replace('BODY', 'edit(relay(right).await).await; left[0] = 30;').replace('MAIN', main)
        self.assertEqual(self.run_c_oracle(compile_source(forwarded)).stdout, '70\n')
        repeated = ('let h = runtime::spawn(-> relay(right)); let result = h.await; '
                    + 'match result { Ok(out) => { out[0] = 40; }, Err(_) => {} } ' * 2)
        with self.assertRaisesRegex(Error, 'déjà consommé'):
            verify_program(source.replace('BODY', repeated).replace('MAIN', main))
        tail = source.replace('BODY', '').replace('MAIN', '''
            let h=runtime::spawn(-> tail(&mut v));
            match h.join() { Ok(out) => { out[0] = 50; }, Err(_) => { print(99); } }
            print(v[1]);
        ''')
        self.assertEqual(self.run_c_oracle(compile_source(tail)).stdout, '50\n')
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(tail.replace('tail(v: &mut Vector<Int>)', 'tail(mut v: -> Vector<Int>)')
                           .replace('tail(&mut v)', 'tail(-> v)').replace('print(v[1]);', ''))
        byte_tail = """
            async fn tail(v: &mut Vector<u8>) -> &mut [u8] {
                let (mut left, mut right) = v.split_at_mut(1);
                yield;
                return &mut *right;
            }
            fn main() {
                let mut p = pool<Vector<u8>>(1); let mut v = p.new(); v.push(65); v.push(0);
                let h = runtime::spawn(-> tail(&mut v));
                match h.join() { Ok(out) => { out[0] = 66; }, Err(_) => { print(99); } }
                match str::from_utf8(&v[..]) { Ok(text) => { print(text); }, Err(_) => { print(98); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(byte_tail)).stdout, 'AB\n')

    def test_async_mutable_slice_return_join_consumes_payload_and_releases_err_path(self):
        source = """
            async fn relay(part: &mut [Int]) -> &mut [Int] { yield; return part; }
            fn main() {
                let mut p = pool<Vector<Int>>(1); let mut v = p.new(); v.push(10); v.push(20);
                let (mut left, mut right) = v.split_at_mut(1);
                let h = runtime::spawn(-> relay(right));
                let result = h.join();
                BEFORE
                left[0] = 30;
                match result {
                    Ok(out) => { INSIDE out[0] = 50; },
                    Err(_) => { right[0] = 80; }
                }
                AFTER
                print(v[0]); print(v[1]);
            }
        """
        valid = source.replace('BEFORE', '').replace('INSIDE', '').replace('AFTER', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '30\n50\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '30\n80\n')
        for point, statement, diagnostic in (
            ('BEFORE', 'print(right[0]);', 'emprunt actif'),
            ('INSIDE', 'print(right[0]);', 'emprunt actif'),
            ('AFTER', 'match result { Ok(out) => { out[0] = 70; }, Err(_) => {} }', 'plus utilisable'),
        ):
            with self.subTest(point=point, statement=statement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(point, statement).replace('BEFORE', '').replace('INSIDE', '').replace('AFTER', ''))
        with self.assertRaisesRegex(Error, 'résultat de tranche mutable'):
            verify_program(valid.replace('match result {', 'let alias = result; match alias {'))

    def test_async_mutable_slice_return_contract_keeps_all_candidate_intervals(self):
        source = """
            async fn choose(a: &mut [Int], b: &mut [Int], first: Bool) -> &mut [Int] {
                yield;
                return if first { &mut *a } else { &mut *b };
            }
            fn finish(h: -> Execution<choose>, fallback: &mut [Int]) -> &mut [Int] {
                return match h.join() { Ok(view) => { &mut *view }, Err(_) => { &mut *fallback } };
            }
            fn main() {
                let mut p = pool<Vector<Int>>(2); let mut v = p.new(); let mut w = p.new();
                v.push(10); v.push(20); w.push(30);
                let (mut left, mut right) = v.split_at_mut(1);
                let (mut empty, mut fallback) = w.split_at_mut(0);
                let h = runtime::spawn(-> choose(left, right, FIRST));
                let out = finish(-> h, fallback);
                BEFORE
                out[0] = 95;
                print(v[0]); print(v[1]); print(w[0]);
            }
        """
        direct = source.replace('finish(-> h, fallback)',
                                'match h.join() { Ok(view) => { &mut *view }, Err(_) => { &mut *fallback } }')
        for template in (source, direct):
            for first, position in (('true', 0), ('false', 1)):
                values = [10, 20, 30]
                values[position] = 95
                program = template.replace('FIRST', first).replace('BEFORE', '')
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout,
                                 ''.join(f'{value}\n' for value in values))
            for parent in ('left', 'right', 'fallback'):
                with self.subTest(parent=parent, direct=template==direct), self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(template.replace('FIRST', 'true').replace('BEFORE', f'print({parent}[0]);'))
        failed = compile_source(source.replace('FIRST', 'true').replace('BEFORE', '')).replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '10\n20\n95\n')

    def test_async_shared_vector_slice_rejects_escaping_storage(self):
        for body in (
            'return &v[..];',
            'let view = &v[..]; yield; return view;',
            'let view = &v[..]; return relay(view).await;',
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Error, 'non durable'):
                verify_program(f"""
                    async fn relay(view: &[Int]) -> &[Int] {{ yield; return view; }}
                    async fn bad(v: -> Vector<Int>) -> &[Int] {{ {body} }}
                    fn main() {{}}
                """)
        with self.assertRaisesRegex(Error, 'ne peut survivre'):
            verify_program("""
                async fn bad(v: -> Vector<Int>) -> Int {
                    let view = { v ->; let inner = &v[..]; inner };
                    return view[0];
                }
                fn main() {}
            """)

    def test_async_string_replace_bytes_preserves_unit_type_and_suspended_order(self):
        source = """
            async fn bound(value: Int) -> Int { print(value); yield; return value; }
            async fn pass(value: Result<(),ByteReplaceError>) -> Result<(),ByteReplaceError> {
                yield; return value;
            }
            async fn work(s: &mut String, bytes: &mut Vector<u8>) -> Result<(),ByteReplaceError> {
                let result = s.replace_bytes(bound(0).await, &bytes[bound(1).await..bound(3).await]);
                yield; print(&s[..]);
                return pass(result).await;
            }
            fn finish(h: -> Execution<work>, fallback: Result<(),ByteReplaceError>) -> Result<(),ByteReplaceError> {
                return match h.join() { Ok(value) => { value }, Err(_) => { fallback } };
            }
            fn main() {
                let mut texts = pool<String>(1);
                let mut s = texts.new(); s.push_str("été");
                let mut vectors = pool<Vector<u8>>(1);
                let mut bytes = vectors.new();
                bytes.push(120); bytes.push(97); bytes.push(98); bytes.push(121);
                let fallback = s.replace_bytes(99, &bytes[..]);
                let h = runtime::spawn(-> work(&mut s, &mut bytes));
                let result = finish(-> h, fallback);
                drop(-> bytes); let reused = vectors.new();
                s.push_str("!");
                match result {
                    Ok(()) => { print(0); },
                    Err(ByteReplaceError::OutOfBounds) => { print(1); },
                    Err(ByteReplaceError::InvalidUtf8) => { print(2); }
                }
                print(&s[..]); print(reused.len());
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '0\n1\n3\nabté\n0\nabté!\n0\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
            '#define pthread_create(thread, attr, runner, pointer) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '1\nété!\n0\n')
        snapshotted = source.replace('let result = s.replace_bytes(bound(0).await,',
            'let mut position = 0; let result = s.replace_bytes(position,').replace(
            'bound(1).await', 'flip(&mut position).await')
        snapshotted += 'async fn flip(position: &mut Int) -> Int { position.set(1); print(1); yield; return 1; }'
        self.assertEqual(self.run_c_oracle(compile_source(snapshotted)).stdout, '1\n3\nabté\n0\nabté!\n0\n')
        saved_bound = source.replace('let result = s.replace_bytes', 'let mut first = 1; let result = s.replace_bytes').replace(
            'bound(1).await..bound(3).await', 'first..flip(&mut first).await')
        saved_bound += 'async fn flip(first: &mut Int) -> Int { first.set(0); print(3); yield; return 3; }'
        self.assertEqual(self.run_c_oracle(compile_source(saved_bound)).stdout, '0\n3\nabté\n0\nabté!\n0\n')
        joined = source.replace('return pass(result).await;',
            'let child = runtime::spawn(-> pass(result)); '
            'return match child.await { Ok(value) => { value }, Err(_) => { result } };')
        self.assertEqual(self.run_c_oracle(compile_source(joined)).stdout, '0\n1\n3\nabté\n0\nabté!\n0\n')
        owned_source = source.replace('bytes: &mut Vector<u8>', 'bytes: -> Vector<u8>').replace(
            'work(&mut s, &mut bytes)', 'work(&mut s, -> bytes)').replace('drop(-> bytes); ', '')
        self.assertEqual(self.run_c_oracle(compile_source(owned_source)).stdout, '0\n1\n3\nabté\n0\nabté!\n0\n')
        moved = owned_source.replace('bound(1).await', 'consume(-> bytes).await')
        moved += 'async fn consume(bytes: -> Vector<u8>) -> Int { drop(-> bytes); yield; return 1; }'
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(moved)
        bad_pattern = source.replace('return pass(result).await;',
            'return match result { Ok(previous) => { result }, Err(_) => { result } };')
        with self.assertRaisesRegex(Error, 'type du résultat'):
            verify_program(bad_pattern)
        with self.assertRaisesRegex(Error, 'type du résultat|extraction'):
            verify_program(source.replace('Ok(()) => { print(0); }', 'Ok(previous) => { print(0); }'))
        wrong_type = source.replace('return pass(result).await;', 'drop(-> result); return s.replace_byte(1,170);')
        with self.assertRaisesRegex(Error, r'attendu Result<\(\),ByteReplaceError>'):
            verify_program(wrong_type)
        with self.assertRaisesRegex(Error, 'capture async.*Result'):
            verify_program(source.replace('return pass(result).await;', 'drop(-> result); return pass(s.replace_byte(1,170)).await;'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('let result = s.replace_bytes', 'let view = &s[..]; let result = s.replace_bytes').replace(
                'yield; print(&s[..]);', 'yield; print(view); print(&s[..]);'))
        conflict = source.replace('bound(0).await', 'change(s).await')
        conflict += 'async fn change(s: &mut String) -> Int { s.push_str("x"); return 0; }'
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conflict)
        conflict = source.replace('bound(1).await', 'change(bytes).await')
        conflict += 'async fn change(bytes: &mut Vector<u8>) -> Int { bytes.push(7); return 1; }'
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conflict)
        with self.assertRaisesRegex(Error, 'mutable'):
            verify_program(source.replace('work(s: &mut String', 'work(s: &String').replace('work(&mut s', 'work(&s'))

    def test_async_string_replace_bytes_matches_transactional_model(self):
        template = """
            async fn work(s: &mut String, bytes: &Vector<u8>, start: Int) -> Int {
                let result = s.replace_bytes(start, &bytes[..]);
                yield;
                return match result {
                    Ok(()) => { 0 },
                    Err(ByteReplaceError::OutOfBounds) => { 1 },
                    Err(ByteReplaceError::InvalidUtf8) => { 2 }
                };
            }
            fn main() {
                let mut texts = pool<String>(1); let mut s = texts.new();
                let mut vectors = pool<Vector<u8>>(2); BLOCKER let mut bytes = vectors.new();
                INITIALIZE
                let h = runtime::spawn(-> work(&mut s, &bytes, START));
                match h.join() { Ok(status) => { print(status); }, Err(_) => { print(99); } }
                print(&s[..]);
            }
        """
        cases = [('é',0,[97,98]),('é',1,[97]),('é',-1,[97]),('é',2,[]),('é',3,[]),
                 ('é',0,[255,255]),('été',0,[97,98]),('a🌍',1,[240,159,144,136]),('',0,[]),('a',0,[195,169])]
        for text, start, replacement in cases:
            original = text.encode('utf-8'); expected, status = text, 1
            if 0 <= start <= len(original) and len(replacement) <= len(original)-start:
                prospective = original[:start]+bytes(replacement)+original[start+len(replacement):]
                try:
                    expected, status = prospective.decode('utf-8'), 0
                except UnicodeDecodeError:
                    status = 2
            text_init = f's.push_str("{text}");'
            bytes_init = ''.join(f'bytes.push({value});' for value in replacement)
            for reverse_order in (False, True):
                with self.subTest(text=text, start=start, replacement=replacement, reverse=reverse_order):
                    init = bytes_init+text_init if reverse_order else text_init+bytes_init
                    source = template.replace('INITIALIZE', init).replace('START', str(start)).replace(
                        'BLOCKER', 'let mut blocker = vectors.new(); blocker.push(0);' if reverse_order else '')
                    code = compile_source(source)
                    marker = 'static CrustByteResult string_replace_slice(Cell *cell, int index, VectorSlice replacement) {'
                    self.assertEqual(code.count(marker), 1)
                    code = code.replace(marker, marker +
                        f'\n    if (replacement.length && replacement.descends != {int(reverse_order)}) abort();', 1)
                    self.assertEqual(self.run_c_oracle(code).stdout, f'{status}\n{expected}\n')

    def test_async_string_replace_bytes_discarded_result_and_slice_guards(self):
        source = """
            async fn work(s: &mut String, bytes: &Vector<u8>, end: Int) {
                s.replace_bytes(0, &bytes[..end]); yield; print(&s[..]);
            }
            fn main() {
                let mut p = pool<String>(1); let mut s = p.new(); s.push_str("é");
                let mut v = pool<Vector<u8>>(1); let mut bytes = v.new(); bytes.push(97); bytes.push(98);
                let h = runtime::spawn(-> work(&mut s,&bytes,2));
                match h.join() { Ok(()) => {}, Err(_) => {} }
                print(&s[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'ab\nab\n')
        own_length = source.replace('bytes: &Vector<u8>', 'bytes: &mut Vector<u8>').replace(
            '&bytes[..end]', '&bytes[..bytes.len()]').replace('work(&mut s,&bytes,2)', 'work(&mut s,&mut bytes,2)')
        self.assertEqual(self.run_c_oracle(compile_source(own_length)).stdout, 'ab\nab\n')
        self.run_c_oracle(compile_source(source.replace('&bytes,2)', '&bytes,3)')),
                          'bornes de tranche de Vector invalides')
        for replacement, diagnostic in (('&bytes[-1..2]', 'bornes'), ('&bytes[2..1]', 'bornes'),
                                         ('&s[..]', 'tranche u8'), ('bytes', 'tranche u8')):
            with self.subTest(replacement=replacement), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace('&bytes[..end]', replacement))

    def test_async_string_replace_bytes_respects_last_use_in_loop_and_value_branch(self):
        template = """
            async fn offset(view: &str) -> Int { print(view); yield; return 0; }
            async fn work(s: &mut String, bytes: &Vector<u8>) -> Result<(),ByteReplaceError> {
                let view = &s[..];
                BODY
            }
            fn main() {
                let mut p = pool<String>(1); let mut s = p.new(); s.push_str("é");
                let mut v = pool<Vector<u8>>(1); let mut b = v.new(); b.push(97); b.push(98);
                let h = runtime::spawn(-> work(&mut s,&b));
                match h.join() {
                    Ok(result) => { match result { Ok(()) => { print(&s[..]); }, Err(_) => { print(98); } } },
                    Err(_) => { print(99); }
                }
            }
        """
        bodies = (
            'return loop { print(view); break s.replace_bytes(0, &bytes[..]); };',
            'if true { print(view); let result = s.replace_bytes(0,&bytes[..]); return result; } '
            'return s.replace_bytes(0,&bytes[..]);',
            'let result = if true { print(view); s.replace_bytes(0,&bytes[..]) } '
            'else { s.replace_bytes(0,&bytes[..]) }; return result;',
        )
        for body in bodies:
            with self.subTest(body=body):
                source = template.replace('BODY', body)
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'é\nab\n')
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(source.replace('replace_bytes(0,', 'replace_bytes(offset(view).await,', 1))
        omitted = template.replace('BODY',
            'loop { s.replace_bytes(offset(view).await, &bytes[..]); break; } '
            'return s.replace_bytes(0, &bytes[..]);')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(omitted)

    def test_async_string_replace_bytes_result_outlives_source_pools(self):
        source = """
            async fn pass(value: Result<(),ByteReplaceError>) -> Result<(),ByteReplaceError> {
                yield; return value;
            }
            fn relay(value: Result<(),ByteReplaceError>) -> Result<(),ByteReplaceError> { return value; }
            fn finish(h: -> Execution<pass>) -> Int {
                return match h.join() {
                    Ok(value) => { match value { Ok(()) => { 0 }, Err(_) => { 1 } } },
                    Err(_) => { 2 }
                };
            }
            fn create() -> Result<(),ByteReplaceError> {
                let mut texts = pool<String>(1); let mut s = texts.new(); s.push_str("é");
                let bytes: [u8;2] = [97,98];
                let result = s.replace_bytes(0,&bytes);
                print(&s[..]);
                return result;
            }
            fn main() {
                let saved = create();
                let handle = runtime::spawn(-> pass(relay(saved)));
                print(finish(-> handle));
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'ab\n0\n')
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('[97,98]', '[255,255]'))).stdout, 'é\n1\n')

    def test_async_string_replace_byte_sequences_suspended_arguments_and_preserves_type(self):
        source = """
            async fn index(b: &String) -> Int { print(1); yield; return b.byte_len(); }
            async fn octet(value: u8) -> u8 { print(2); yield; return value; }
            async fn work(s: &mut String, b: &String) -> Result<u8,ByteReplaceError> {
                let view = &s[..]; print(view);
                let result = s.replace_byte(index(b).await, octet(170).await);
                yield;
                print(&s[..]);
                return result;
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut s = strings.new(); let mut b = strings.new();
                s.push_str("é"); b.push_str("b");
                let h = runtime::spawn(-> work(&mut s, &b));
                match h.join() {
                    Ok(result) => {
                        s.push_str("x");
                        match result {
                            Ok(old) => {
                                match s.replace_byte(1, old) {
                                    Ok(_) => { print(&s[..]); },
                                    Err(ByteReplaceError::OutOfBounds) => { print(98); },
                                    Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                                }
                            },
                            Err(ByteReplaceError::OutOfBounds) => { print(96); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(95); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'é\n1\n2\nê\néx\n')
        snapshotted = source.replace('let result = s.replace_byte(index(b).await, octet(170).await);',
            'let mut position = 1; let result = s.replace_byte(position, flip(&mut position).await); print(position);')
        snapshotted += """
            async fn flip(position: &mut Int) -> u8 { position.set(0); yield; return 170; }
        """
        self.assertEqual(self.run_c_oracle(compile_source(snapshotted)).stdout, 'é\n0\nê\néx\n')
        copied = source.replace('let result = s.replace_byte(index(b).await, octet(170).await);',
                                'let byte = s[1]; let result = s.replace_byte(1, byte);')
        self.assertEqual(self.run_c_oracle(compile_source(copied)).stdout, 'é\né\néx\n')
        with self.subTest(conflict='receiver read in argument'), self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('octet(170).await', 's[1]'))
        active = source.replace('let view = &s[..]; print(view);', 'let view = &s[..];').replace(
            'yield;\n                print(&s[..]);', 'yield; print(view);\n                print(&s[..]);')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(active)
        conflicting = source.replace('index(b).await', 'change(s).await') + """
            async fn change(s: &mut String) -> Int { s.push_str("x"); return 1; }
        """
        with self.subTest(conflict='receiver mutation in argument'), self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conflicting)
        with self.assertRaisesRegex(Error, 'mutable'):
            verify_program(source.replace('work(s: &mut String,', 'work(s: &String,').replace('work(&mut s,', 'work(&s,'))
        mismatch = source.replace('work(s: &mut String, b: &String) -> Result<u8,ByteReplaceError>',
                                  'work(s: &mut String, b: &String) -> Result<char,CharAtError>')
        with self.assertRaisesRegex(Error, 'attendu Result<char,CharAtError>'):
            verify_program(mismatch)

    def test_async_string_replace_byte_matches_transactional_utf8_model(self):
        template = """
            async fn attempt(s: &mut String, offset: Int, byte: u8) -> Int {
                let result = s.replace_byte(offset, byte);
                yield;
                return match result {
                    Ok(_) => { 0 },
                    Err(ByteReplaceError::OutOfBounds) => { 1 },
                    Err(ByteReplaceError::InvalidUtf8) => { 2 }
                };
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("TEXT");
                let h = runtime::spawn(-> attempt(&mut s, OFFSET, BYTE));
                match h.join() { Ok(status) => { print(status); }, Err(_) => { print(99); } }
                print(&s[..]);
            }
        """
        for text, offset, byte in (('é', -1, 170), ('é', 2, 170), ('é', 1, 0), ('é', 0, 65),
                                   ('é', 1, 170), ('', 0, 65), ('a🌍', 0, 65)):
            # Independent transaction model: try the complete prospective byte
            # sequence with Python's UTF-8 decoder before committing any change.
            original = text.encode('utf-8')
            expected, status = text, 1
            if 0 <= offset < len(original):
                candidate = bytearray(original)
                candidate[offset] = byte
                try:
                    expected, status = candidate.decode('utf-8'), 0
                except UnicodeDecodeError:
                    status = 2
            source = template.replace('TEXT', text).replace('OFFSET', str(offset)).replace('BYTE', str(byte))
            with self.subTest(text=text, offset=offset, byte=byte):
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, f'{status}\n{expected}\n')
        for value in (-1, 256):
            source = template.replace('TEXT', 'é').replace('OFFSET', '1').replace('BYTE', str(value))
            with self.subTest(range=value), self.assertRaisesRegex(Error, 'u8'):
                verify_program(source)
        source = template.replace('TEXT', 'é').replace('OFFSET', '1').replace('BYTE', 'value').replace(
            'let h = runtime::spawn', 'let value = 170; let h = runtime::spawn')
        with self.assertRaisesRegex(Error, 'u8.*même type'):
            verify_program(source)

    def test_async_string_replace_result_survives_drop_and_typed_join_contract(self):
        source = """
            async fn work(mut s: -> String) -> Result<u8,ByteReplaceError> {
                let result = s.replace_byte(1, 170);
                yield;
                return result;
            }
            fn finish(h: -> Execution<work>, fallback: Result<u8,ByteReplaceError>) -> Result<u8,ByteReplaceError> {
                return match h.join() { Ok(value) => { value }, Err(_) => { fallback } };
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é");
                let fallback = s.replace_byte(99, 65);
                let h = runtime::spawn(-> work(-> s));
                let result = finish(-> h, fallback);
                let mut reused = strings.new(); reused.push_str("ê");
                match result {
                    Ok(old) => {
                        match reused.replace_byte(1, old) {
                            Ok(_) => {},
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(ByteReplaceError::OutOfBounds) => { print(7); },
                    Err(ByteReplaceError::InvalidUtf8) => { print(8); }
                }
                print(&reused[..]);
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, 'é\n')
        relayed = source.replace('return result;', 'return pass(result).await;', 1).replace(
            'async fn work(', """async fn pass(value: Result<u8,ByteReplaceError>) -> Result<u8,ByteReplaceError> {
                yield; return value;
            }
            async fn work(""", 1)
        self.assertEqual(self.run_c_oracle(compile_source(relayed)).stdout, 'é\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, runner, pointer) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '7\nê\n')

    def test_async_string_replace_byte_discarded_result_executes_write(self):
        source = """
            async fn work(s: &mut String) { s.replace_byte(1, 170); yield; print(&s[..]); }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é");
                let h = runtime::spawn(-> work(&mut s));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(&s[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'ê\nê\n')

    def test_async_string_replace_byte_payload_is_u8_detached_from_source(self):
        source = """
            async fn work(mut s: -> String) -> u8 {
                let result = s.replace_byte(1, 170);
                yield;
                return match result {
                    Ok(old) => { s.push_str("x"); old },
                    Err(ByteReplaceError::OutOfBounds) => { let zero: u8 = 0; zero },
                    Err(ByteReplaceError::InvalidUtf8) => { let zero: u8 = 0; zero }
                };
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é");
                let h = runtime::spawn(-> work(-> s));
                match h.join() {
                    Ok(old) => {
                        let mut reused = strings.new(); reused.push_str("ê");
                        match reused.replace_byte(1, old) {
                            Ok(_) => { print(&reused[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'é\n')

    def test_async_string_replace_computed_match_subject_evaluates_once(self):
        template = """
            async fn work(s: &mut String, flag: Bool) -> Int {
                return match SUBJECT {
                    Ok(_) => { 1 },
                    Err(ByteReplaceError::OutOfBounds) => { 2 },
                    Err(ByteReplaceError::InvalidUtf8) => { 3 }
                };
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new(); s.push_str("é");
                let h = runtime::spawn(-> work(&mut s, FLAG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(&s[..]);
            }
        """
        conditional = 'if flag { print(10); yield; s.replace_byte(1,170) } else { print(20); yield; s.replace_byte(1,168) }'
        for subject in (conditional, '{ ' + conditional + ' }',
                        'loop { if flag { print(10); yield; break s.replace_byte(1,170); } print(20); yield; break s.replace_byte(1,168); }',
                        'match s.replace_byte(99,65) { Ok(_) => { ' + conditional + ' }, Err(_) => { ' + conditional + ' } }'):
            for flag, text, trace in (('true', 'ê', 10), ('false', 'è', 20)):
                source = template.replace('SUBJECT', subject).replace('FLAG', flag)
                with self.subTest(subject=subject, flag=flag):
                    self.assertEqual(self.run_c_oracle(compile_source(source)).stdout,
                                     f'{trace}\n1\n{text}\n')
        source = template.replace('SUBJECT', conditional).replace('FLAG', 'true')
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(source.replace('s.replace_byte(1,168)', 's.char_at(0)'))
        with self.assertRaisesRegex(Error, 'type du résultat'):
            verify_program(source.replace('ByteReplaceError::', 'CharAtError::').replace(
                'CharAtError::InvalidUtf8', 'CharAtError::NotCharBoundary'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('return match', 'let view = &s[..]; let value = match').replace(
                '};\n            }', '}; print(view); return value;\n            }', 1))

    def test_async_string_scalar_reads_copy_utf8_values_after_yield(self):
        source = """
            async fn at(n: Int) -> Int { print(n); yield; return n; }
            async fn pick(text: &String, fallback: char) -> char {
                yield;
                return match text.char_at(at(2).await) {
                    Ok(ch) => { ch },
                    Err(CharAtError::OutOfBounds) => { fallback },
                    Err(CharAtError::NotCharBoundary) => { fallback }
                };
            }
            async fn octet(text: &String) -> u8 { yield; return text[1]; }
            fn main() {
                let mut strings = pool<String>(2);
                let mut text = strings.new();
                text.push_str("é🌍");
                match "x".char_at(0) {
                    Ok(fallback) => {
                        let handle = runtime::spawn(-> pick(&text, fallback));
                        match handle.join() { Ok(ch) => { text.push_str("!"); print(ch); }, Err(_) => { print(99); } }
                    },
                    Err(CharAtError::OutOfBounds) => { print(96); },
                    Err(CharAtError::NotCharBoundary) => { print(95); }
                }
                let second = runtime::spawn(-> octet(&text));
                match second.join() {
                    Ok(value) => {
                        text ->;
                        drop(-> text);
                        let mut output = strings.new();
                        output.push_str("ê");
                        match output.replace_byte(1, value) {
                            Ok(_) => { print(&output[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '2\n🌍\né\n')
        self.run_c_oracle(compile_source(source.replace('return text[1]', 'return text[99]')),
                          'indice UTF-8 hors bornes')
        conflicting = source.replace('async fn pick(text: &String,', 'async fn pick(text: &mut String,').replace(
            'at(2).await', 'change(text).await').replace('pick(&text, fallback)', 'pick(&mut text, fallback)')
        conflicting += '''
            async fn change(text: &mut String) -> Int { text.push_str("x"); return 2; }
        '''
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(conflicting)
        with self.assertRaisesRegex(Error, 'u8'):
            verify_program(source.replace('async fn octet(text: &String) -> u8', 'async fn octet(text: &String) -> Int'))

    def test_collection_borrows_reserve_until_join_and_preserve_contents(self):
        source = """
            async fn edit(values: &mut Vector<Int>) -> Int {
                values.push(9);
                yield;
                values[0] = values[0] + 1;
                return values.len();
            }
            async fn read(values: &Vector<Int>) -> Int { yield; return values[0]; }
            async fn grow(text: &mut String) -> Int {
                text.push_str("é");
                yield;
                return text.byte_len();
            }
            fn main() {
                let mut vectors = pool<Vector<Int>>(1);
                let mut values = vectors.new();
                values.push(7);
                let task = edit(&mut values);
                RESERVED
                let h = runtime::spawn(-> task);
                RUNNING
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(values[0]);
                print(values[1]);
                let read1 = runtime::spawn(-> read(&values));
                let read2 = runtime::spawn(-> read(&values));
                print(values[0]);
                match read1.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                BETWEEN
                match read2.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                values.push(11);
                print(values.len());
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                let last = runtime::spawn(-> grow(&mut text));
                match last.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(&text[..]);
            }
        """
        valid = source.replace('RESERVED', '').replace('RUNNING', '').replace('BETWEEN', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '2\n8\n9\n8\n8\n8\n3\n2\né\n')
        relayed = valid.replace('fn main() {', '''
            async fn relay(values: &mut Vector<Int>) -> Int {
                let child = edit(values);
                return child.await;
            }
            fn main() {
        ''').replace('let task = edit(&mut values);', 'let task = relay(&mut values);')
        self.assertEqual(self.run_c_oracle(compile_source(relayed)).stdout, '2\n8\n9\n8\n8\n8\n3\n2\né\n')
        for placeholder, operation in (('RESERVED', 'values.push(3);'), ('RUNNING', 'print(values[0]);'),
                                       ('BETWEEN', 'drop(-> values);')):
            with self.subTest(placeholder=placeholder), self.assertRaisesRegex(Error, 'emprunt'):
                verify_program(source.replace(placeholder, operation).replace(
                    'RESERVED', '').replace('RUNNING', '').replace('BETWEEN', ''))
        bytes_source = '''
            async fn edit(values: &mut Vector<u8>) -> Int {
                values[0] = "z"[0];
                yield;
                let value = values[0];
                values.push(value);
                return values.len();
            }
            fn main() {
                let mut bytes = pool<Vector<u8>>(1);
                let mut data = bytes.new();
                data.push("a"[0]);
                let handle = runtime::spawn(-> edit(&mut data));
                match handle.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                match str::from_utf8(&data[..]) {
                    Ok(text) => { print(text); }, Err(_) => { print(98); }
                }
            }
        '''
        self.assertEqual(self.run_c_oracle(compile_source(bytes_source)).stdout, '2\nzz\n')
        for candidate in (valid.replace('values: &mut Vector<Int>', 'values: &Vector<Int>'),
                          valid.replace('text: &mut String', 'mut text: &String')):
            with self.assertRaises(Error):
                verify_program(candidate)

    def test_nested_collection_join_results_preserve_payload_type(self):
        source = """
            async fn leaf(mut value: -> String) -> <- String {
                value.push_str("é");
                yield;
                return <- value;
            }
            async fn wrap(value: -> String) -> <- Result<A<String>,runtime::Error> {
                let h = runtime::spawn(-> leaf(-> value));
                let result = h.await;
                return <- result;
            }
            fn launch(value: -> String) -> <- Result<Result<A<String>,runtime::Error>,runtime::Error> {
                let h = runtime::spawn(-> wrap(-> value));
                let result = h.join();
                return <- result;
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut value = strings.new();
                value.push_str("a");
                address(value);
                let result = launch(-> value);
                match result {
                    Ok(inner) => {
                        match inner {
                            Ok(received) => { address(received); print(&received[..]); drop(-> received); },
                            Err(_) => { print(98); }
                        }
                    },
                    Err(_) => { print(99); }
                }
                let reused = strings.new();
                address(reused);
                print(reused.byte_len());
            }
        """
        code = compile_source(source)
        address, received, text, reused, length = self.run_c_oracle(code).stdout.splitlines()
        self.assertEqual((received, text, reused, length), (address, 'aé', address, '0'))
        for failure, expected in (('((a) ? EAGAIN : pthread_create(t,a,r,p))', '98'), ('EAGAIN', '99')):
            failed = code.replace('#include <pthread.h>',
                '#include <pthread.h>\n#define pthread_create(t,a,r,p) ' + failure, 1)
            if failure != 'EAGAIN':
                failed = inject_submission_failure(code)
            address, error, reused, length = self.run_c_oracle(failed).stdout.splitlines()
            self.assertEqual((error, reused, length), (expected, address, '0'))
        relayed = source.replace('async fn wrap(value: -> String)', '''
            async fn relay(result: -> Result<A<String>,runtime::Error>) -> <- Result<A<String>,runtime::Error> {
                yield;
                return <- result;
            }
            async fn wrap(value: -> String)
        ''').replace('let result = h.await;\n                return <- result;', '''
                let result = h.await;
                let forwarded = relay(-> result).await;
                return <- forwarded;
        ''')
        address, received, text, reused, length = self.run_c_oracle(compile_source(relayed)).stdout.splitlines()
        self.assertEqual((received, text, reused, length), (address, 'aé', address, '0'))
        selected = relayed.replace('let forwarded = relay(-> result).await;',
            'let forwarded = if true { result ->; let next = relay(-> result).await; <- next } '
            'else { result ->; let next = relay(-> result).await; <- next };')
        address, received, text, reused, length = self.run_c_oracle(compile_source(selected)).stdout.splitlines()
        self.assertEqual((received, text, reused, length), (address, 'aé', address, '0'))
        vector = (source.replace('String', 'Vector<Int>').replace('value.push_str("é")', 'value.push(9)')
                  .replace('value.push_str("a")', 'value.push(7)')
                  .replace('print(&received[..]);', 'print(received[0]); print(received[1]);')
                  .replace('reused.byte_len()', 'reused.len()'))
        address, received, first, second, reused, length = self.run_c_oracle(compile_source(vector)).stdout.splitlines()
        self.assertEqual((received, first, second, reused, length), (address, '7', '9', address, '0'))
        wrong = source.replace('async fn wrap(value: -> String) -> <- Result<A<String>,runtime::Error>',
                               'async fn wrap(value: -> String) -> <- Result<A<Int>,runtime::Error>')
        with self.assertRaisesRegex(Error, 'type de Result incompatible|retour conditionnel : allocation String attendue, reçu Int'):
            verify_program(wrong)

    def test_owned_collection_join_result_crosses_sync_contract(self):
        source = """
            async fn work(mut values: -> Vector<Int>) -> <- Vector<Int> {
                values.push(9);
                yield;
                return <- values;
            }
            fn relay(result: -> Result<A<Vector<Int>>,runtime::Error>) -> <- Result<A<Vector<Int>>,runtime::Error> {
                return <- result;
            }
            fn launch(values: -> Vector<Int>) -> <- Result<A<Vector<Int>>,runtime::Error> {
                let h = runtime::spawn(-> work(-> values));
                let result = h.join();
                let forwarded = relay(-> result);
                return <- forwarded;
            }
            fn main() {
                let mut vectors = pool<Vector<Int>>(1);
                let mut values = vectors.new();
                values.push(7);
                address(values);
                let result = launch(-> values);
                match result {
                    Ok(value) => { address(value); print(value[0]); print(value[1]); drop(-> value); },
                    Err(_) => { print(99); }
                }
                let reused = vectors.new();
                address(reused);
            }
        """
        address, received, first, second, reused = self.run_c_oracle(compile_source(source)).stdout.splitlines()
        self.assertEqual((received, first, second, reused), (address, '7', '9', address))
        text = (source.replace('Vector<Int>', 'String').replace('values.push(9)', 'values.push_str("é")')
                .replace('values.push(7)', 'values.push_str("a")')
                .replace('print(value[0]); print(value[1]);', 'print(&value[..]); print(value.byte_len());'))
        address, received, content, length, reused = self.run_c_oracle(compile_source(text)).stdout.splitlines()
        self.assertEqual((received, content, length, reused), (address, 'aé', '3', address))
        failed = compile_source(text).replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        address, error, reused = self.run_c_oracle(failed).stdout.splitlines()
        self.assertEqual((error, reused), ('99', address))
        wrong_call = source.replace('fn main() {', '''
            fn sink(result: -> Result<A<Int>,runtime::Error>) { drop(-> result); }
            fn main() {
        ''')
        start, end = wrong_call.index('                match result {'), wrong_call.index('                let reused')
        wrong_call = wrong_call[:start] + 'sink(-> result);' + wrong_call[end:]
        with self.assertRaisesRegex(Error, 'transféré attendu'):
            verify_program(wrong_call)
        wrong = source.replace('fn relay(result: -> Result<A<Vector<Int>>,runtime::Error>)',
                               'fn relay(result: -> Result<A<Int>,runtime::Error>)')
        with self.assertRaises(Error):
            verify_program(wrong)

    def test_owned_collection_reassignment_evaluates_rhs_before_drop(self):
        source = """
            async fn produce(values: -> Vector<Int>, old: Int) -> <- Vector<Int> {
                print(old);
                yield;
                return <- values;
            }
            async fn replace(mut current: -> Vector<Int>, next: -> Vector<Int>) -> <- Vector<Int> {
                current = RHS;
                current.push(11);
                return <- current;
            }
            fn main() {
                let mut vectors = pool<Vector<Int>>(2);
                let mut original = vectors.new();
                original.push(7);
                let mut replacement = vectors.new();
                replacement.push(9);
                address(original);
                address(replacement);
                let handle = runtime::spawn(-> replace(-> original, -> replacement));
                match handle.join() {
                    Ok(result) => {
                        address(result);
                        print(result[0]);
                        print(result[1]);
                        drop(-> result);
                    },
                    Err(_) => { print(99); }
                }
                let reused = vectors.new();
                address(reused);
            }
        """
        call = 'produce(-> next, current[0]).await'
        for rhs, expected_old in ((call, ['7']), ('<- next', []),
                                  ('{ let ready = ' + call + '; <- ready }', ['7']),
                                  ('if true { let ready = ' + call + '; <- ready } '
                                   'else { let ready = ' + call + '; <- ready }', ['7']),
                                  ('loop { let ready = ' + call + '; break <- ready; }', ['7'])):
            with self.subTest(rhs=rhs):
                run = self.run_c_oracle(compile_source(source.replace('RHS', rhs)))
                original, replacement, *remaining = run.stdout.splitlines()
                self.assertEqual(remaining, [*expected_old, replacement, '9', '11', original])
                self.assertEqual(run.stderr.count('destroy original='), 1)
                self.assertEqual(run.stderr.count('destroy replacement='), 1)
                self.assertLess(run.stderr.index('destroy original='), run.stderr.index('destroy replacement='))
        returned_same = source.replace('RHS', 'produce(-> current, 7).await')
        run = self.run_c_oracle(compile_source(returned_same))
        original, replacement, *remaining = run.stdout.splitlines()
        self.assertEqual(remaining, ['7', original, '7', '11', original])
        self.assertEqual(run.stderr.count('destroy original='), 1)
        self.assertEqual(run.stderr.count('destroy replacement='), 1)
        text = (source.replace('Vector<Int>', 'String').replace('original.push(7)', 'original.push_str("é")')
                .replace('replacement.push(9)', 'replacement.push_str("🌍")')
                .replace('current.push(11)', 'current.push_str("x")')
                .replace('print(result[0]);', 'print(&result[..]);')
                .replace('print(result[1]);', 'print(result.byte_len());')
                .replace('RHS', 'produce(-> next, current.byte_len()).await'))
        run = self.run_c_oracle(compile_source(text))
        original, replacement, *remaining = run.stdout.splitlines()
        self.assertEqual(remaining, ['2', replacement, '🌍x', '5', original])
        for wrong in ('3', 'next', '"a"[0]'):
            with self.assertRaises(Error):
                verify_program(source.replace('RHS', wrong))

    def test_owned_collection_await_receives_exact_type_and_cleanup(self):
        source = """
            async fn leaf(mut values: -> Vector<Int>) -> <- Vector<Int> {
                values.push(9);
                yield;
                return <- values;
            }
            async fn direct(values: -> Vector<Int>) -> <- Vector<Int> {
                let mut received = leaf(-> values).await;
                received.push(11);
                yield;
                return <- received;
            }
            async fn handled(values: -> Vector<Int>) -> Int {
                let h = runtime::spawn(-> direct(-> values));
                let result = h.await;
                return match result {
                    Ok(received) => {
                        let mut renamed = <- received;
                        renamed.push(13);
                        yield;
                        renamed[0] + renamed[1] + renamed[2] + renamed[3]
                    },
                    Err(_) => { 99 }
                };
            }
            fn main() {
                let mut vectors = pool<Vector<Int>>(1);
                let mut values = vectors.new();
                values.push(7);
                address(values);
                let h = runtime::spawn(-> handled(-> values));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                let reused = vectors.new();
                address(reused);
                print(reused.len());
            }
        """
        address, result, reused, length = self.run_c_oracle(compile_source(source)).stdout.splitlines()
        self.assertEqual((result, reused, length), ('40', address, '0'))
        for expression in (
                '{ let child = leaf(-> values).await; <- child }',
                'if true { let child = leaf(-> values).await; <- child } '
                'else { let child = leaf(-> values).await; <- child }',
                'loop { let child = leaf(-> values).await; break <- child; }'):
            candidate = source.replace('let mut received = leaf(-> values).await;',
                                       f'let mut received = {expression};')
            with self.subTest(expression=expression):
                address, result, reused, length = self.run_c_oracle(compile_source(candidate)).stdout.splitlines()
                self.assertEqual((result, reused, length), ('40', address, '0'))
        inline = source.replace('let result = h.await;', '').replace('match result {', 'match h.await {')
        address, result, reused, length = self.run_c_oracle(compile_source(inline)).stdout.splitlines()
        self.assertEqual((result, reused, length), ('40', address, '0'))
        text = (source.replace('Vector<Int>', 'String').replace('values.push(9)', 'values.push_str("a")')
                .replace('received.push(11)', 'received.push_str("b")').replace('renamed.push(13)', 'renamed.push_str("c")')
                .replace('renamed[0] + renamed[1] + renamed[2] + renamed[3]', 'renamed.byte_len()')
                .replace('values.push(7)', 'values.push_str("é")').replace('reused.len()', 'reused.byte_len()'))
        address, result, reused, length = self.run_c_oracle(compile_source(text)).stdout.splitlines()
        self.assertEqual((result, reused, length), ('5', address, '0'))
        failed = inject_submission_failure(compile_source(text))
        address, result, reused, length = self.run_c_oracle(failed).stdout.splitlines()
        self.assertEqual((result, reused, length), ('99', address, '0'))
        mismatch = '''
            async fn vector(values: -> Vector<Int>) -> <- Vector<Int> { return <- values; }
            async fn text(value: -> String) -> <- String { return <- value; }
            async fn bad(values: -> Vector<Int>, value: -> String) -> Int {
                let selected = if true {
                    let child = vector(-> values).await;
                    <- child
                } else {
                    let child = text(-> value).await;
                    <- child
                };
                drop(-> selected);
                return 1;
            }
            fn main() {}
        '''
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(mismatch)
        for candidate in (source.replace('let mut received = leaf', 'let received = leaf'),
                          source.replace('renamed.push(13);', 'renamed.set(13);'),
                          source.replace('received.push(11);', 'received.push("a"[0]);')):
            with self.assertRaises(Error):
                verify_program(candidate)

    def test_owned_collection_result_keeps_type_pool_and_identity(self):
        source = """
            async fn work(mut values: -> Vector<Int>) -> <- Vector<Int> {
                values.push(9);
                yield;
                return <- values;
            }
            fn main() {
                let mut vectors = pool<Vector<Int>>(1);
                let mut original = vectors.new();
                original.push(7);
                address(original);
                let h = runtime::spawn(-> work(-> original));
                match h.join() {
                    Ok(result) => {
                        let mut received = <- result;
                        address(received);
                        print(received[0]);
                        print(received[1]);
                        received.push(11);
                        print(received.len());
                        drop(-> received);
                    },
                    Err(_) => { print(99); }
                }
                let reused = vectors.new();
                address(reused);
                print(reused.len());
            }
        """
        first, result, a, b, length, reused, empty = self.run_c_oracle(compile_source(source)).stdout.splitlines()
        self.assertEqual((result, a, b, length, reused, empty), (first, '7', '9', '3', first, '0'))
        text = (source.replace('Vector<Int>', 'String').replace('values.push(9)', 'values.push_str("é")')
                .replace('original.push(7)', 'original.push_str("a")')
                .replace('print(received[0]);', 'print(&received[..]);')
                .replace('print(received[1]);', 'print(received.byte_len());')
                .replace('received.push(11)', 'received.push_str("b")').replace('received.len()', 'received.byte_len()')
                .replace('reused.len()', 'reused.byte_len()'))
        first, result, value, length, grown, reused, empty = self.run_c_oracle(compile_source(text)).stdout.splitlines()
        self.assertEqual((result, value, length, grown, reused, empty), (first, 'aé', '3', '4', first, '0'))
        failed = compile_source(text).replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        first, error, reused, empty = self.run_c_oracle(failed).stdout.splitlines()
        self.assertEqual((error, reused, empty), ('99', first, '0'))
        ignored = text.replace('Ok(result) => {', 'Ok(_) => {').replace('let mut received = <- result;', '')
        start = ignored.index('                        address(received);')
        end = ignored.index('                    },', start)
        ignored = ignored[:start] + ignored[end:]
        with self.assertRaisesRegex(Error, 'motif _'):
            compile_source(ignored)
        explicit = ignored.replace('Ok(_) => {', 'Ok(value) => { drop(-> value);')
        first, reused, empty = self.run_c_oracle(compile_source(explicit)).stdout.splitlines()
        self.assertEqual((reused, empty), (first, '0'))
        wrong = source.replace('-> <- Vector<Int>', '-> <- Int')
        # Isolate the declared return mismatch: the caller's Vector-only method
        # otherwise rejects the Int result before the return contract is checked.
        wrong = wrong.replace('received.push(11);', '')
        with self.assertRaisesRegex(Error, 'type déclaré'):
            verify_program(wrong)

    def test_owned_collection_forwarding_preserves_cleanup_obligation(self):
        source = """
            async fn leaf(mut values: -> Vector<Int>) -> Int {
                values.push(5);
                yield;
                return values[0] + values[1];
            }
            async fn parent(values: -> Vector<Int>) -> Int {
                let task = leaf(-> values);
                yield;
                let child = runtime::spawn(-> task);
                return match child.await { Ok(n) => { n }, Err(_) => { 99 } };
            }
            fn main() {
                let mut vectors = pool<Vector<Int>>(1);
                let mut values = vectors.new();
                values.push(7);
                address(values);
                let h = runtime::spawn(-> parent(-> values));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                let reused = vectors.new();
                address(reused);
                print(reused.len());
            }
        """
        first, result, reused, length = self.run_c_oracle(compile_source(source)).stdout.splitlines()
        self.assertEqual((result, reused, length), ('12', first, '0'))
        inactive = source.replace('let child = runtime::spawn(-> task);', 'drop(-> task);').replace(
            'return match child.await { Ok(n) => { n }, Err(_) => { 99 } };', 'return 3;')
        first, result, reused, length = self.run_c_oracle(compile_source(inactive)).stdout.splitlines()
        self.assertEqual((result, reused, length), ('3', first, '0'))
        abandoned = source.replace('return match child.await { Ok(n) => { n }, Err(_) => { 99 } };', 'return 3;')
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(abandoned)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('yield;\n                let child', 'print(values.len()); yield;\n                let child'))
        wrong_type = source.replace('async fn leaf(mut values: -> Vector<Int>)', 'async fn leaf(mut values: -> String)').replace(
            'values.push(5);', 'values.push_str("x");').replace('return values[0] + values[1];', 'return values.byte_len();')
        with self.assertRaisesRegex(Error, 'type incompatible'):
            verify_program(wrong_type)

    def test_owned_vector_index_reads_writes_and_suspended_order(self):
        source = """
            async fn at(n: Int) -> Int { print(n); yield; return n; }
            async fn edit(mut values: -> Vector<Int>) -> Int {
                values[at(0).await] = values[at(1).await] + 1;
                yield;
                return values[0];
            }
            async fn byte(mut values: -> Vector<u8>) -> u8 {
                values[0] = "z"[0];
                yield;
                return values[0];
            }
            fn main() {
                let mut ints = pool<Vector<Int>>(1);
                let mut values = ints.new();
                values.push(7);
                values.push(9);
                let h = runtime::spawn(-> edit(-> values));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                let mut bytes = pool<Vector<u8>>(1);
                let mut data = bytes.new();
                data.push("a"[0]);
                let second = runtime::spawn(-> byte(-> data));
                match second.join() {
                    Ok(n) => {
                        let mut strings = pool<String>(1);
                        let mut text = strings.new();
                        text.push_str("x");
                        match text.replace_byte(0, n) {
                            Ok(_) => { print(&text[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '0\n1\n10\nz\n')
        literal = source.replace('values[0] = "z"[0]', 'values[0] = 122')
        self.assertEqual(self.run_c_oracle(compile_source(literal)).stdout, '0\n1\n10\nz\n')
        for candidate in (source.replace('mut values: ->', 'values: ->'),
                          source.replace('values[0] = "z"[0]', 'values[0] = 256'),
                          source.replace('values[at(1).await] + 1', '"z"[0]'),
                          source.replace('async fn byte(mut values: -> Vector<u8>) -> u8',
                                         'async fn byte(mut values: -> Vector<u8>) -> Int')):
            with self.assertRaises(Error):
                verify_program(candidate)
        self.run_c_oracle(compile_source(source.replace('values[at(0).await]', 'values[at(2).await]')),
                          'indice de Vector hors limites')

    def test_owned_vector_capture_grows_and_cleans_original_pool(self):
        source = """
            async fn work(mut values: -> Vector<Int>, item: Int) -> Int {
                values.push(item);
                yield;
                values.push(item);
                return values.len();
            }
            fn relay(values: -> Vector<Int>, item: Int) -> <- work {
                let task = work(-> values, item);
                return <- task;
            }
            fn main() {
                let mut vectors = pool<Vector<Int>>(2);
                let mut a = vectors.new();
                let mut b = vectors.new();
                a.push(1);
                b.push(2);
                address(a);
                address(b);
                let h1 = runtime::spawn(-> relay(-> a, 7));
                let h2 = runtime::spawn(-> relay(-> b, 9));
                match h1.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                match h2.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                let reused = vectors.new();
                address(reused);
                print(reused.len());
            }
        """
        for typ, initial, one, two in (('Int', '1', '7', '9'), ('u8', '"a"[0]', '"b"[0]', '"c"[0]')):
            program = (source.replace('Vector<Int>', f'Vector<{typ}>').replace('item: Int', f'item: {typ}')
                       .replace('a.push(1)', f'a.push({initial})').replace('b.push(2)', f'b.push({initial})')
                       .replace('relay(-> a, 7)', f'relay(-> a, {one})')
                       .replace('relay(-> b, 9)', f'relay(-> b, {two})'))
            with self.subTest(typ=typ):
                a, b, first, second, reused, length = self.run_c_oracle(compile_source(program)).stdout.splitlines()
                self.assertIn(reused, (a, b))
                self.assertEqual((first, second, length), ('3', '3', '0'))
        contents = source.replace('return values.len();', 'return values[0] + values[1] + values[2];')
        a, b, first, second, reused, length = self.run_c_oracle(compile_source(contents)).stdout.splitlines()
        self.assertEqual((first, second, length), ('15', '20', '0'))
        self.run_c_oracle(compile_source(contents.replace('values[2]', 'values[3]')),
                          'indice de Vector hors limites')
        for candidate in (source.replace('mut values: ->', 'values: ->'),
                          source.replace('values.push(item);', 'values.set(item);'),
                          source.replace('values.push(item);', 'values.push("a"[0]);')):
            with self.assertRaises(Error):
                verify_program(candidate)

    def test_owned_string_capture_cleans_original_pool_after_join(self):
        source = """
            async fn write(mut text: -> String, suffix: &str) -> Int {
                text.push_str(suffix);
                yield;
                text.push_str("é");
                return text.byte_len();
            }
            fn launch(text: -> String) -> <- Execution<write> {
                let task = write(-> text, "x");
                let handle = runtime::spawn(-> task);
                return <- handle;
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut first = strings.new();
                first.push_str("a");
                let mut second = strings.new();
                second.push_str("b");
                address(first);
                address(second);
                let h1 = launch(-> first);
                let h2 = launch(-> second);
                match h1.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                match h2.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                let mut reused = strings.new();
                address(reused);
                reused.push_str("ok");
                print(&reused[..]);
            }
        """
        first, second, a, b, reused, text = self.run_c_oracle(compile_source(source)).stdout.splitlines()
        self.assertIn(reused, (first, second))
        self.assertEqual((a, b, text), ('4', '4', 'ok'))
        failed = compile_source(source).replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        first, second, a, b, reused, text = self.run_c_oracle(failed).stdout.splitlines()
        self.assertIn(reused, (first, second))
        self.assertEqual((a, b, text), ('99', '99', 'ok'))
        inactive = source.replace('let h1 = launch(-> first);', 'let t = write(-> first, "x"); drop(-> t);')
        inactive = inactive.replace('match h1.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }', '')
        first, second, n, reused, text = self.run_c_oracle(compile_source(inactive)).stdout.splitlines()
        self.assertIn(reused, (first, second))
        self.assertEqual((n, text), ('4', 'ok'))
        for candidate in (source.replace('return text.byte_len();', 'return *text;'),
                          source.replace('text.push_str(suffix);', 'text.set(3);'),
                          source.replace('let h2 = launch(-> second);', 'let h2 = launch(-> first);')):
            with self.assertRaises(Error):
                verify_program(candidate)

    def test_async_utf8_return_keeps_dedicated_string_live_until_last_use(self):
        source = """
            async fn tail(view: &str) -> &str {
                yield;
                return &view[2..];
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut first = strings.new();
                first.push_str("left");
                let mut text = strings.new();
                text.push_str("é🌍");
                address(text);
                let handle = runtime::spawn(-> tail(&text[..]));
                BEFORE_JOIN
                match handle.join() {
                    Ok(view) => {
                        BEFORE_USE
                        print(view);
                        AFTER_USE
                    },
                    Err(_) => { print(99); }
                }
                drop(-> text);
                let mut reused = strings.new();
                address(reused);
                reused.push_str("again");
                print(&reused[..]);
                print(&first[..]);
            }
        """
        def with_operations(before_join='', before_use='', after_use=''):
            return (source.replace('BEFORE_JOIN', before_join).replace('BEFORE_USE', before_use)
                    .replace('AFTER_USE', after_use))

        valid = with_operations(before_join='first.push_str("!");',
                                after_use='text.push_str("!"); print(&text[..]);')
        address, returned, grown, reused, reused_text, other = self.run_c_oracle(
            compile_source(valid)).stdout.splitlines()
        self.assertEqual((returned, grown, reused, reused_text, other),
                         ('🌍', 'é🌍!', address, 'again', 'left!'))
        for candidate in (with_operations(before_join='text.push_str("!");'),
                          with_operations(before_use='text.push_str("!");')):
            with self.assertRaisesRegex(Error, 'emprunt'):
                verify_program(candidate)

    def test_async_utf8_byte_reborrow_keeps_capture_provenance(self):
        source = """
            async fn load(byte: &u8) -> u8 { yield; return *byte; }
            fn prepare(byte: &u8) -> <- load {
                let child = load(&*byte);
                return <- child;
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut text = strings.new();
                text.push_str("é");
                let mut output = strings.new();
                output.push_str("ê");
                let byte = ORIGIN;
                let child = prepare(byte);
                let h = runtime::spawn(-> child);
                BEFORE
                match h.join() {
                    Ok(value) => {
                        match output.replace_byte(1, value) {
                            Ok(_) => { print(&output[..]); },
                            Err(ByteReplaceError::OutOfBounds) => { print(98); },
                            Err(ByteReplaceError::InvalidUtf8) => { print(97); }
                        }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        static = source.replace('ORIGIN', '&"é"[1]').replace('BEFORE', 'drop(-> text);')
        self.assertEqual(self.run_c_oracle(compile_source(static)).stdout, 'é\n')
        borrowed = source.replace('ORIGIN', '&text[1]')
        self.assertEqual(self.run_c_oracle(compile_source(borrowed.replace('BEFORE', ''))).stdout, 'é\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(borrowed.replace('BEFORE', 'drop(-> text);'))
        with self.assertRaisesRegex(Error, 'immuables|incompatible'):
            verify_program(static.replace('load(&*byte)', 'load(&mut *byte)'))

        nested = borrowed.replace('async fn load(byte: &u8) -> u8 { yield; return *byte; }', '''
            async fn relay(byte: &u8) -> &u8 { yield; return &*byte; }
            async fn load(byte: &u8) -> u8 {
                let loan = relay(&*byte).await;
                return *loan;
            }
        ''')
        self.assertEqual(self.run_c_oracle(compile_source(nested.replace('BEFORE', ''))).stdout, 'é\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(nested.replace('BEFORE', 'drop(-> text);'))
        returned = (nested.replace('fn load(byte: &u8) -> u8', 'fn load(byte: &u8) -> &u8')
                    .replace('return *loan;', 'return loan;').replace('1, value', '1, *value')
                    .replace('BEFORE', ''))
        self.assertEqual(self.run_c_oracle(compile_source(returned)).stdout, 'é\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(returned.replace('Ok(value) => {', 'Ok(value) => { drop(-> text);'))

    def test_async_utf8_capture_from_loop_break_values(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn main() {
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("🌍");
                let view = &text[..];
                let mut i = 0;
                let chosen = loop {
                    if i < 2 { i = i + 1; continue; }
                    if i == LIMIT { break "é"; }
                    break ALTERNATIVE;
                };
                let h = runtime::spawn(-> width(chosen));
                DROP
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for limit, expected in (('2', '2\n'), ('3', '4\n')):
            program = source.replace('LIMIT', limit)
            static = (program.replace('ALTERNATIVE', '"🌍"').replace('DROP', 'drop(-> text);')
                      .replace('let view = &text[..];', ''))
            self.assertEqual(self.run_c_oracle(compile_source(static)).stdout, expected)
            mixed = program.replace('ALTERNATIVE', 'view')
            self.assertEqual(self.run_c_oracle(compile_source(mixed.replace('DROP', ''))).stdout, expected)
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(mixed.replace('DROP', 'drop(-> text);'))
        local = (source.replace('LIMIT', '3').replace('DROP', '')
                 .replace('break ALTERNATIVE;', 'let local = strings.new(); break &local[..];'))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program(local)
        mismatched = source.replace('LIMIT', '2').replace('ALTERNATIVE', '3').replace('DROP', '')
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(mismatched)
        byte = (source.replace('&str) -> Int', '&u8) -> u8').replace('view.byte_len()', '*view')
                .replace('Ok(n) => { print(n); }', 'Ok(_) => { print(1); }')
                .replace('break "é";', 'break &"é"[0];').replace('&text[..]', '&text[0]')
                .replace('LIMIT', '3').replace('ALTERNATIVE', 'view'))
        self.assertEqual(self.run_c_oracle(compile_source(byte.replace('DROP', ''))).stdout, '1\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(byte.replace('DROP', 'drop(-> text);'))

    def test_async_utf8_capture_from_nominal_match(self):
        source = """
            enum Choice { First, Second }
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn prepare(choice: &Choice, view: &str) -> <- width {
                let chosen = match &choice {
                    Choice.First => { let local = "é"; local },
                    Choice.Second => { SECOND }
                };
                let task = width(chosen);
                return <- task;
            }
            fn main() {
                let mut choices = pool<Choice>(1);
                let choice = new(choices) Choice.VARIANT;
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("🌍");
                let task = prepare(&choice, &text[..]);
                let h = runtime::spawn(-> task);
                DROP
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for variant, expected in (('First', '2\n'), ('Second', '4\n')):
            candidate = source.replace('VARIANT', variant)
            static = candidate.replace('SECOND', '"🌍"').replace('DROP', 'drop(-> text);')
            self.assertEqual(self.run_c_oracle(compile_source(static)).stdout, expected)
            borrowed = candidate.replace('SECOND', 'view')
            self.assertEqual(self.run_c_oracle(compile_source(borrowed.replace('DROP', ''))).stdout, expected)
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(borrowed.replace('DROP', 'drop(-> text);'))
        mismatched = source.replace('VARIANT', 'First').replace('SECOND', '1').replace('DROP', '')
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(mismatched)

    def test_async_utf8_capture_preserves_parameter_in_computed_view(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn prepare(first: &str, second: &String, flag: Int) -> <- width {
                let chosen = if flag == 1 { first } else { &second[..] };
                let task = width(chosen);
                return <- task;
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut first = strings.new();
                let mut second = strings.new();
                first.push_str("é");
                second.push_str("🌍");
                let task = prepare(&first[..], &second, FLAG);
                let h = runtime::spawn(-> task);
                DROP
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for flag, expected in (('0', '4\n'), ('1', '2\n')):
            candidate = source.replace('FLAG', flag)
            self.assertEqual(self.run_c_oracle(compile_source(candidate.replace('DROP', ''))).stdout, expected)
            for owner in ('first', 'second'):
                with self.subTest(flag=flag, owner=owner), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(candidate.replace('DROP', f'drop(-> {owner});'))
        mixed = source.replace('&second[..]', '"a"').replace('FLAG', '1')
        self.assertEqual(self.run_c_oracle(compile_source(
            mixed.replace('DROP', 'drop(-> second);'))).stdout, '2\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(mixed.replace('DROP', 'drop(-> first);'))

    def test_async_utf8_capture_tracks_view_across_continue(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn main() {
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("🌍");
                let mut view = "a";
                let mut i = 0;
                loop {
                    if i < 2 {
                        view = &text[..];
                        i = i + 1;
                        continue;
                    }
                    FINAL_VIEW
                    break;
                }
                let task = width(view);
                let h = runtime::spawn(-> task);
                DROP
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        borrowed = source.replace('FINAL_VIEW', '')
        self.assertEqual(self.run_c_oracle(compile_source(borrowed.replace('DROP', ''))).stdout, '4\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(borrowed.replace('DROP', 'drop(-> text);'))
        static = source.replace('FINAL_VIEW', 'view = "é";').replace('DROP', 'drop(-> text);')
        self.assertEqual(self.run_c_oracle(compile_source(static)).stdout, '2\n')
        two_sources = borrowed.replace('pool<String>(1)', 'pool<String>(2)').replace(
            'let mut view = "a";', 'let initial = strings.new(); let mut view = &initial[..];')
        self.assertEqual(self.run_c_oracle(compile_source(two_sources.replace('DROP', ''))).stdout, '4\n')
        for owner in ('initial', 'text'):
            with self.subTest(owner=owner), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(two_sources.replace('DROP', f'drop(-> {owner});'))

    def test_async_utf8_capture_keeps_storage_after_view_reassignment(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn main() {
                let mut strings = pool<String>(1);
                let mut text = strings.new();
                text.push_str("🌍");
                let mut view = "a";
                view = &text[..];
                let task = width(view);
                view = "é";
                let h = runtime::spawn(-> task);
                BEFORE_JOIN
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                AFTER_JOIN
                print(view);
            }
        """
        after = source.replace('BEFORE_JOIN', '').replace('AFTER_JOIN', 'strings.reset();')
        self.assertEqual(self.run_c_oracle(compile_source(after, allow_legacy_reset=True)).stdout, '4\né\n')
        before = source.replace('BEFORE_JOIN', 'strings.reset();').replace('AFTER_JOIN', '')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(before, allow_legacy_reset=True)

    def test_async_utf8_factory_returns_capture_with_caller_provenance(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn prepare(view: &str) -> <- width {
                let task = width(view);
                return <- task;
            }
            fn launch(s: &String) -> <- Execution<width> {
                let task = prepare(&s[1..]);
                let h = runtime::spawn(-> task);
                return <- h;
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new();
                s.push_str("aé");
                let h = launch(&s);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                s.push_str("!");
                print(&s[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '2\naé!\n')
        for instruction, diagnostic in (
                ('s.push_str("!");', 'emprunt actif'),
                ('drop(-> s);', 'emprunt encore utilisé'),
                ('drop(-> h);', 'join requis')):
            candidate = source.replace('match h.join()', instruction + ' match h.join()')
            with self.subTest(instruction=instruction), self.assertRaisesRegex(Error, diagnostic):
                verify_program(candidate)
        static = source.replace('let h = launch(&s);',
            'let task = prepare("é"); let h = runtime::spawn(-> task); drop(-> h);')
        static = static.replace('match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }', '')
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(static)

    def test_async_utf8_handle_transfer_keeps_join_obligation(self):
        source = """
            async fn width(view: &str) -> Int { yield; return view.byte_len(); }
            fn forward(h: -> Execution<width>) -> <- Execution<width> { return <- h; }
            fn finish(h: -> Execution<width>) -> Int {
                match h.join() { Ok(n) => { return n; }, Err(_) => { return 99; } }
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new();
                s.push_str("é");
                let h = runtime::spawn(-> width(&s[..]));
                let next = forward(-> h);
                print(finish(-> next));
                s.push_str("!");
                print(&s[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '2\né!\n')
        forbidden = '''fn relay_drop(h: -> Execution<width>) { ignore(-> h); }
                       fn ignore(h: -> Execution<width>) { drop(-> h); }'''
        for statement, diagnostic in (
                ('s.push_str("!"); print(finish(-> next));', 'emprunt actif'),
                ('relay_drop(-> next);', 'join requis')):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                invalid = source.replace('print(finish(-> next));', statement)
                verify_program(invalid + forbidden if statement == 'relay_drop(-> next);' else invalid)
        static = source.replace('width(&s[..])', 'width("é")').replace(
            'print(finish(-> next));', 'relay_drop(-> next);')
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(static + forbidden)
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('width(&s[..])', 'width("é")'))).stdout,
                         '2\né!\n')
        legacy = source.replace('fn finish(h: -> Execution<width>) -> Int {',
            'fn finish(h: -> Execution<width>, target: &mut Pool<String>) -> Int { target.reset();')
        legacy = legacy.replace('print(finish(-> next));', 'print(finish(-> next, &mut strings));')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(legacy, allow_legacy_reset=True)

    def test_async_dynamic_utf8_result_keeps_source_reserved_after_join(self):
        source = """
            async fn slice(t: &str) -> &str { yield; return &t[1..]; }
            async fn relay(t: &str) -> &str {
                let h = runtime::spawn(-> slice(t));
                return match h.await { Ok(view) => { view }, Err(_) => { "interne" } };
            }
            fn finish(h: -> Execution<relay>) -> &str {
                let joined = h.join();
                match joined { Ok(view) => { return view; }, Err(_) => { return "secours"; } }
            }
            fn main() {
                let mut strings = pool<String>(1);
                let mut s = strings.new();
                s.push_str("aé");
                let h = runtime::spawn(-> relay(&s[..]));
                let view = finish(-> h);
                print(view);
                s.push_str("!");
                print(&s[..]);
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, 'é\naé!\n')
        failed_launch = code.replace(
            '#include <pthread.h>', '#include <pthread.h>\n#define pthread_create(t,a,r,p) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed_launch).stdout, 'secours\naé!\n')
        failed_inner_launch = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed_inner_launch).stdout, 'interne\naé!\n')
        for instruction, diagnostic in (
                ('s.push_str("!");', 'emprunt actif'),
                ('drop(-> s);', 'emprunt encore utilisé')):
            candidate = source.replace('print(view);', instruction + ' print(view);')
            with self.subTest(instruction=instruction), self.assertRaisesRegex(Error, diagnostic):
                verify_program(candidate)
        detached = source.replace('return match h.await { Ok(view) => { view }, Err(_) => { "interne" } };',
                                  'drop(-> h); return t;')
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(detached)

    def test_async_utf8_result_releases_capture_unrelated_to_return(self):
        source = """
            async fn select_view(first: &str, second: &str, flag: Bool) -> &str {
                yield;
                print(second);
                let mut selected = first;
                if flag { selected = first; }
                return &selected[1..];
            }
            fn finish(h: -> Execution<select_view>) -> &str {
                match h.join() { Ok(view) => { return view; }, Err(_) => { return "secours"; } }
            }
            fn main() {
                let mut strings = pool<String>(2);
                let mut a = strings.new();
                let mut b = strings.new();
                a.push_str("aé");
                b.push_str("bè");
                let h = runtime::spawn(-> select_view(&a[..], &b[..], true));
                let view = finish(-> h);
                drop(-> b);
                print(view);
                a.push_str("!");
                print(&a[..]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'bè\né\naé!\n')
        nested = source.replace('fn finish(h: -> Execution<select_view>)', """
            async fn relay(first: &str, second: &str, flag: Bool) -> &str {
                let result = select_view(first, second, flag).await;
                yield;
                return result;
            }
            fn finish(h: -> Execution<relay>)
        """).replace('-> select_view(&a[..], &b[..], true)', '-> relay(&a[..], &b[..], true)')
        self.assertEqual(self.run_c_oracle(compile_source(nested)).stdout, 'bè\né\naé!\n')
        named = nested.replace('let result = select_view(first, second, flag).await;',
                               'let task = select_view(first, second, flag); let result = task.await;')
        self.assertEqual(self.run_c_oracle(compile_source(named)).stdout, 'bè\né\naé!\n')
        spawned = nested.replace('let result = select_view(first, second, flag).await;',
            'let task = select_view(first, second, flag);\n'
            '                let h = runtime::spawn(-> task);\n'
            '                let result = match h.await { Ok(view) => { view }, Err(_) => { first } };')
        spawned_code = compile_source(spawned)
        self.assertEqual(self.run_c_oracle(spawned_code).stdout, 'bè\né\naé!\n')
        failed_inner_launch = inject_submission_failure(spawned_code)
        self.assertEqual(self.run_c_oracle(failed_inner_launch).stdout, 'aé\naé!\n')
        computed = nested.replace('let result = select_view(first, second, flag).await;',
            'let result = (if flag {\n'
            '                    let a = select_view(first, second, flag); <- a\n'
            '                } else {\n'
            '                    let b = select_view(first, second, flag); <- b\n'
            '                }).await;')
        self.assertEqual(self.run_c_oracle(compile_source(computed)).stdout, 'bè\né\naé!\n')
        block = nested.replace('let result = select_view(first, second, flag).await;',
            'let result = { let task = select_view(first, second, flag); <- task }.await;')
        self.assertEqual(self.run_c_oracle(compile_source(block)).stdout, 'bè\né\naé!\n')
        matched = nested.replace('async fn relay(first:', 'async fn gate() -> Int { yield; return 1; }\n'
                                 '            async fn relay(first:')
        matched = matched.replace('let result = select_view(first, second, flag).await;',
            'let gate_handle = runtime::spawn(-> gate());\n'
            '                let result = (match gate_handle.await {\n'
            '                    Ok(n) => { let a = select_view(first, second, flag); <- a },\n'
            '                    Err(_) => { let b = select_view(first, second, flag); <- b }\n'
            '                }).await;')
        self.assertEqual(self.run_c_oracle(compile_source(matched)).stdout, 'bè\né\naé!\n')
        looped = nested.replace('let result = select_view(first, second, flag).await;',
            'let result = (loop {\n'
            '                    loop { break; }\n'
            '                    let task = select_view(first, second, flag);\n'
            '                    break <- task;\n'
            '                }).await;')
        self.assertEqual(self.run_c_oracle(compile_source(looped)).stdout, 'bè\né\naé!\n')
        for candidate in (
                source.replace('drop(-> b);', 'drop(-> a);'),
                source.replace('if flag { selected = first; }', 'if flag { selected = second; }'),
                nested.replace('drop(-> b);', 'drop(-> a);'),
                nested.replace('if flag { selected = first; }', 'if flag { selected = second; }'),
                named.replace('if flag { selected = first; }', 'if flag { selected = second; }'),
                spawned.replace('if flag { selected = first; }', 'if flag { selected = second; }'),
                spawned.replace('Err(_) => { first }', 'Err(_) => { second }'),
                computed.replace('let b = select_view(first, second, flag);',
                                 'let b = select_view(second, first, flag);')):
            with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(candidate)
        legacy = source.replace('fn main() {', """
            fn show(a: &String, b: &String, target: &mut Pool<String>) {
                let h = runtime::spawn(-> select_view(&a[..], &b[..], true));
                let view = finish(-> h);
                target.reset();
                print(view);
            }
            fn main() {
        """).replace('let mut b = strings.new();', 'let mut spare = pool<String>(1); let mut b = spare.new();')
        legacy = legacy.replace(
            'let h = runtime::spawn(-> select_view(&a[..], &b[..], true));\n'
            '                let view = finish(-> h);\n                drop(-> b);\n                print(view);',
            'show(&a, &b, &mut TARGET);')
        self.assertEqual(self.run_c_oracle(compile_source(
            legacy.replace('TARGET', 'spare'), allow_legacy_reset=True)).stdout, 'bè\né\naé!\n')
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(legacy.replace('TARGET', 'strings'), allow_legacy_reset=True)

    def test_async_local_bool_keeps_type_across_yield_and_scope_exit(self):
        source = """
            async fn leaf(flag: Bool) -> Int {
                if flag { return 7; }
                return 9;
            }
            async fn run(input: Bool) -> Int {
                let mut flag: Bool = input;
                yield;
                if flag {
                    let local = true;
                    yield;
                    if local { flag = false; }
                }
                let local = 3;
                return leaf(flag).await + local;
            }
            fn main() {
                let h = runtime::spawn(-> run(true));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '12\n')
        for before, after, diagnostic in (
                ('flag: Bool = input', 'flag: Bool = 1', 'liaison Bool'),
                ('let local = true;', 'let local: Int = true;', 'liaison Int'),
                ('flag = false;', 'flag = 1;', 'valeur Bool'),
                ('let mut flag:', 'let flag:', 'receveur mutable')):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_bool_result_preserves_type_through_await(self):
        source = """
            async fn leaf(flag: Bool) -> Bool { yield; return flag; }
            async fn relay(flag: Bool) -> Bool { return leaf(flag).await; }
            async fn parent(flag: Bool) -> Int {
                let task = relay(flag);
                let actual: Bool = task.await;
                if actual == true { return 7; }
                return 9;
            }
            fn main() {
                let h = runtime::spawn(-> parent(INPUT));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for value, expected in (('true', '7\n'), ('false', '9\n')):
            self.assertEqual(self.run_c_oracle(compile_source(source.replace('INPUT', value))).stdout, expected)
        direct = source.replace('let actual: Bool = task.await;\n                if actual == true',
                                'if task.await == true')
        self.assertEqual(self.run_c_oracle(compile_source(direct.replace('INPUT', 'true'))).stdout, '7\n')
        for before, after, diagnostic in (
                ('return flag;', 'return 1;', 'valeur Bool'),
                ('let actual: Bool', 'let actual: Int', 'liaison Int'),
                ('if actual == true', 'if actual == 1', 'comparaison async incompatible'),
                ('let actual: Bool = task.await;', 'task.await; let actual = true;', 'receveur Bool')):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after).replace('INPUT', 'true'))

    def test_threaded_bool_result_preserves_type_in_ok_branch(self):
        source = """
            async fn leaf(flag: Bool) -> Bool { yield; return flag; }
            async fn parent(flag: Bool) -> Int {
                let h = runtime::spawn(-> leaf(flag));
                let joined = h.await;
                match joined {
                    Ok(value) => { if value { return 7; } return 9; },
                    Err(_) => { return 11; }
                }
            }
            fn main() {
                let h = runtime::spawn(-> leaf(true));
                match h.join() {
                    Ok(value) => { if value { print(7); } },
                    Err(_) => { print(99); }
                }
                let j = runtime::spawn(-> parent(false));
                match j.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '7\n9\n')
        failure = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failure).stdout, '7\n11\n')
        for before, after, diagnostic in (
                ('if value { return 7; }', 'if value { return value + 1; }', 'valeur Int'),
                ('if value { print(7); }', 'print(value + 1);', 'Int'),
                ('Ok(value) => { if value { print(7); } }', 'Ok(()) => { print(7); }', 'incompatible')):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(source.replace(before, after))

    def test_async_bool_control_results_preserve_branch_type(self):
        source = """
            async fn leaf(flag: Bool) -> Bool { yield; return flag; }
            async fn select_bool(flag: Bool) -> Bool {
                let selected: Bool = if flag { leaf(false).await } else { leaf(true).await };
                return selected;
            }
            async fn parent(flag: Bool) -> Int {
                let h = runtime::spawn(-> select_bool(flag));
                let actual: Bool = match h.await { Ok(value) => { value }, Err(_) => { true } };
                if actual { return 7; }
                return 9;
            }
            fn main() {
                let h = runtime::spawn(-> parent(INPUT));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for argument, expected in (('false', '7\n'), ('true', '9\n')):
            self.assertEqual(self.run_c_oracle(compile_source(source.replace('INPUT', argument))).stdout, expected)
        computed = source.replace(
            'let selected: Bool = if flag { leaf(false).await } else { leaf(true).await };\n'
            '                return selected;',
            'return (if flag { let task = leaf(false); <- task } '
            'else { let task = leaf(true); <- task }).await;')
        self.assertEqual(self.run_c_oracle(compile_source(computed.replace('INPUT', 'true'))).stdout, '9\n')
        for before, after in (('else { leaf(true).await }', 'else { 1 }'), ('Err(_) => { true }', 'Err(_) => { 1 }')):
            with self.assertRaisesRegex(Error, 'valeur Bool'):
                verify_program(source.replace(before, after).replace('INPUT', 'true'))
        inferred = source.replace('selected: Bool', 'selected').replace('actual: Bool', 'actual')
        inferred = inferred.replace('if flag { leaf(false).await }',
                                    'if flag { let local = leaf(false).await; local }')
        for argument, expected in (('false', '7\n'), ('true', '9\n')):
            self.assertEqual(self.run_c_oracle(compile_source(inferred.replace('INPUT', argument))).stdout, expected)
        for before, after in (('let local = leaf(false).await; local', '1'),
                              ('Ok(value) => { value }', 'Ok(value) => { if value { 1 } else { 2 } }')):
            with self.assertRaisesRegex(Error, 'même type scalaire'):
                verify_program(inferred.replace(before, after).replace('INPUT', 'true'))

    def test_async_loop_breaks_infer_bool_after_continue(self):
        source = """
            async fn leaf(flag: Bool) -> Bool { yield; return flag; }
            async fn pick(flag: Bool) -> Bool {
                let mut i = 0;
                RECEIVER loop {
                    if i == 0 { i = 1; continue; }
                    if flag { break leaf(false).await; }
                    break true;
                };
                RETURN
            }
            fn main() {
                let h = runtime::spawn(-> pick(INPUT));
                match h.join() {
                    Ok(value) => { if value { print(7); } else { print(9); } },
                    Err(_) => { print(99); }
                }
            }
        """
        for receiver, returned in (('let selected =', 'return selected;'),
                                   ('let selected: Bool =', 'return selected;'), ('return', '')):
            program = source.replace('RECEIVER', receiver).replace('RETURN', returned)
            for flag, expected in (('false', '7\n'), ('true', '9\n')):
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('INPUT', flag))).stdout, expected)
            with self.assertRaisesRegex(Error, 'même type et le même mode'):
                verify_program(program.replace('INPUT', 'true').replace('break true;', 'break 1;'))
        invalid = source.replace('RECEIVER', 'let selected: Int =').replace('RETURN', 'return selected;')
        with self.assertRaisesRegex(Error, 'annotation de résultat de boucle'):
            verify_program(invalid.replace('INPUT', 'true'))

    def test_async_conditions_infer_bool_and_keep_operand_order(self):
        source = """
            async fn leaf(flag: Bool, trace: Int) -> Bool {
                print(trace);
                yield;
                return flag;
            }
            async fn run(flag: Bool) -> Int {
                if (if flag { leaf(true, 1).await } else { leaf(false, 2).await }) ==
                   (loop { break (if flag { let t = leaf(true, 3); <- t }
                                       else { let t = leaf(true, 4); <- t }).await; }) {
                    return 7;
                }
                return 9;
            }
            fn main() {
                let h = runtime::spawn(-> run(INPUT));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        for flag, expected in (('true', '1\n3\n7\n'), ('false', '2\n4\n9\n')):
            self.assertEqual(self.run_c_oracle(compile_source(source.replace('INPUT', flag))).stdout, expected)
        with self.assertRaisesRegex(Error, 'comparaison async incompatible'):
            verify_program(source.replace('INPUT', 'true').replace('}) ==', '}) >'))
        with self.assertRaisesRegex(Error, 'même type scalaire'):
            verify_program(source.replace('INPUT', 'true').replace('else { leaf(false, 2).await }', 'else { 1 }'))

    def test_sync_function_joins_handle_returning_array_element(self):
        source = """
            async fn lend(row: &mut [Int; 2]) -> &mut Int { yield; return &mut row[1]; }
            fn relay(t: -> lend) -> <- lend { return <- t; }
            fn finish(h: -> Execution<lend>) -> Int {
                match h.join() {
                    Ok(view) => { *view = *view + 2; return *view; },
                    Err(_) => { return 99; }
                }
            }
            fn main() {
                let mut table = [[10, 20], [30, 40]];
                let task = relay(-> lend(&mut table[0]));
                let h = runtime::spawn(-> task);
                BEFORE
                print(finish(-> h));
                print(table[0][1]);
            }
        """
        program = source.replace('BEFORE', '')
        self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '22\n22\n')
        failed_launch = compile_source(program).replace('#include <pthread.h>', '#include <pthread.h>\n'
                                                      '#define pthread_create(thread, attr, runner, pointer) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed_launch).stdout, '99\n20\n')
        shared = program.replace('&mut [Int;', '&[Int;').replace('&mut Int', '&Int').replace(
            '&mut row[1]', '&row[1]',
        ).replace('&mut table[0]', '&table[0]').replace('*view = *view + 2; ', '')
        self.assertEqual(self.run_c_oracle(compile_source(shared)).stdout, '20\n20\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'table[0][1] = 21;'))

    def test_sync_function_returns_joined_array_reference(self):
        source = """
            async fn lend(row: &mut [Int; 2]) -> &mut Int { return &mut row[1]; }
            fn finish(h: -> Execution<lend>, fallback: &mut Int) -> &mut Int {
                match h.join() {
                    Ok(view) => { return view; },
                    Err(_) => { return fallback; }
                }
            }
            fn main() {
                let mut table = [[10, 20], [30, 40]];
                let mut p = pool<Int>(1);
                let mut fallback = p.new(90);
                let h = runtime::spawn(-> lend(&mut table[0]));
                let mut view = finish(-> h, &mut fallback);
                table[0][0] = 11;
                CHECK
                *view = 23;
                print(table[0][0]);
                print(table[0][1]);
                print(fallback);
            }
        """
        program = source.replace('CHECK', '')
        code = compile_source(program)
        self.assertEqual(self.run_c_oracle(code).stdout, '11\n23\n90\n')
        failed_launch = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                     '#define pthread_create(thread, attr, runner, pointer) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed_launch).stdout, '11\n20\n23\n')
        relayed = program.replace('fn main() {', '''
            fn relay(h: -> Execution<lend>, fallback: &mut Int) -> &mut Int {
                return finish(-> h, fallback);
            }
            fn main() {
        ''').replace('let mut view = finish(-> h, &mut fallback);', 'let mut view = relay(-> h, &mut fallback);')
        self.assertEqual(self.run_c_oracle(compile_source(relayed)).stdout, '11\n23\n90\n')
        scalar_capture = relayed.replace(
            'lend(row: &mut [Int; 2]) -> &mut Int { return &mut row[1]; }',
            'lend(cell: &mut Int) -> &mut Int { return cell; }',
        ).replace('lend(&mut table[0])', 'lend(&mut table[0][1])')
        verify_program(scalar_capture)
        self.assertEqual(self.run_c_oracle(compile_source(scalar_capture)).stdout, '11\n23\n90\n')
        both_storages = scalar_capture.replace('pool<Int>(1)', 'pool<Int>(2)').replace(
            'print(fallback);', '''
                let mut pooled = p.new(60);
                let second = runtime::spawn(-> lend(&mut pooled));
                let mut pool_view = relay(-> second, &mut fallback);
                pool_view.set(61);
                print(pooled);
                print(fallback);
            ''',
        )
        verify_program(both_storages)
        self.assertEqual(self.run_c_oracle(compile_source(both_storages)).stdout, '11\n23\n61\n90\n')
        script = scalar_capture.replace('fn main() {', '').rstrip().removesuffix('}')
        verify_program(script)
        for write in ('table[0][1] = 21;', 'fallback = 91;'):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(scalar_capture.replace('*view = 23;', f'{write} *view = 23;'))
        for write in ('table[0][1] = 21;', 'fallback = 91;'):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('CHECK', write))

    def test_sync_recaptures_joined_array_reference_by_name(self):
        source = """
            async fn lend(row: &mut [Int; 2]) -> &mut Int { return &mut row[1]; }
            async fn edit(cell: &mut Int) { yield; cell.set(23); }
            fn main() {
                let mut table = [[10, 20], [30, 40]];
                let first = runtime::spawn(-> lend(&mut table[0]));
                match first.join() {
                    Ok(view) => {
                        let second = runtime::spawn(-> edit(view));
                        table[0][0] = 11;
                        CHECK
                        match second.join() { Ok(()) => {}, Err(_) => { print(99); } }
                        print(*view);
                    },
                    Err(_) => { print(99); }
                }
                print(table[0][0]);
                print(table[0][1]);
            }
        """
        program = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '23\n11\n23\n')
        explicit = program.replace('edit(view)', 'edit(&mut *view)')
        self.assertEqual(self.run_c_oracle(compile_source(explicit)).stdout, '23\n11\n23\n')
        for access in ('print(*view);', 'table[0][1] = 21;'):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('CHECK', access))
        shared = source.replace(
            'edit(cell: &mut Int) { yield; cell.set(23); }',
            'edit(cell: &Int) -> Int { yield; return *cell; }',
        ).replace('match second.join() { Ok(()) => {},', 'match second.join() { Ok(n) => { print(n); },')
        self.assertEqual(self.run_c_oracle(compile_source(shared.replace('CHECK', ''))).stdout,
                         '20\n20\n11\n20\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(shared.replace('CHECK', 'print(*view);'))

    def test_async_byte_array_layout_survives_await_join_and_control_transfers(self):
        source = """
            async fn make(first: [u8;2]) -> [u8;2] {
                yield;
                return <- copy(first);
            }
            async fn patch(s: &mut String, flag: Int, input: [[u8;2];2]) -> [u8;2] {
                let direct = make(copy(input[0])).await;
                let child = runtime::spawn(-> make(copy(input[1])));
                let joined = match child.await {
                    Ok(value) => { <- value },
                    Err(_) => { let fallback: [u8;2] = [120,121]; <- fallback }
                };
                let selected: [u8;2] = loop {
                    if flag == 0 { let a = copy(direct); break <- a; }
                    let b = copy(joined); break <- b;
                };
                s.replace_bytes(0, &selected);
                return <- selected;
            }
            fn main() {
                let mut p = pool<String>(1); let mut s = p.new(); s.push_str("é");
                let mut input: [[u8;2];2] = [[97,98],[99,100]];
                let task = patch(&mut s, FLAG, copy(input));
                input[0][0] = 122;
                let h = runtime::spawn(-> task);
                match h.join() {
                    Ok(value) => {
                        match s.replace_bytes(0,&value) { Ok(()) => { print(&s[..]); }, Err(_) => { print(98); } }
                    },
                    Err(_) => { print(99); }
                }
            }
        """
        for flag, expected in ((0, 'ab\n'), (1, 'cd\n')):
            with self.subTest(flag=flag):
                code = compile_source(source.replace('FLAG', str(flag)))
                self.assertEqual(self.run_c_oracle(code).stdout, expected)
        literal = source.replace('return <- copy(first);', 'return <- [first[0], first[1]];')
        self.assertEqual(self.run_c_oracle(compile_source(literal.replace('FLAG', '1'))).stdout, 'cd\n')
        for candidate, diagnostic in (
            (source.replace('let b = copy(joined);', 'let b = [99,100];'), 'même type'),
            (source.replace('make(first: [u8;2]) -> [u8;2]', 'make(first: [u8;2]) -> [Int;2]'), 'type d’élément'),
            (source.replace('make(copy(input[0]))', 'make(copy([97,98]))'), 'type|projection'),
            (source.replace('input[0][0] = 122;', 'input[0][0] = 256;'), 'u8'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(candidate.replace('FLAG', '0'))

    def test_async_byte_array_borrows_use_byte_stride_and_check_indices(self):
        source = """
            async fn index(i: Int) -> Int { print(i); yield; return i; }
            async fn edit(a: &mut [[u8;2];2]) {
                let previous = a[1].replace(index(0).await, 97);
                a[1][1] = previous;
                a[1].swap(0,1);
            }
            async fn patch(s: &mut String, a: &mut [[u8;2];2], i: Int) {
                edit(&mut *a).await;
                s.replace_bytes(0, &a[index(i).await]);
                let empty: [u8;0] = [a[0][0];0];
                s.replace_bytes(2, empty.ref());
                yield;
            }
            fn main() {
                let mut p = pool<String>(1); let mut s = p.new(); s.push_str("é");
                let mut a: [[u8;2];2] = [[120,121],[98,99]];
                let h = runtime::spawn(-> patch(&mut s,&mut a,INDEX));
                match h.join() { Ok(()) => { print(&s[..]); }, Err(_) => { print(99); } }
                match s.replace_bytes(0,&a[1]) { Ok(()) => { print(&s[..]); }, Err(_) => { print(98); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('INDEX','1'))).stdout, '0\n1\nba\nba\n')
        self.run_c_oracle(compile_source(source.replace('INDEX','2')), 'indice hors limites')
        temporary = source.replace('&a[index(i).await]', '&copy(a[index(i).await])')
        self.assertEqual(self.run_c_oracle(compile_source(temporary.replace('INDEX','1'))).stdout,
                         '0\n1\nba\nba\n')
        for candidate, diagnostic in (
            (source.replace('&a[index(i).await]', '&a[2]'), 'hors limites'),
            (source.replace('&a[index(i).await]', '&*a'), 'tableau u8'),
            (source.replace('edit(a: &mut [[u8;2];2])', 'edit(a: &mut [[Int;2];2])'), 'type d’élément'),
            (source.replace('a[1].replace(index(0).await, 97)', 'a[1].replace(index(0).await, i)').replace(
                'edit(a: &mut [[u8;2];2])', 'edit(a: &mut [[u8;2];2], i: Int)').replace(
                'edit(&mut *a)', 'edit(&mut *a, i)'), 'même type'),
            (source.replace('let previous = a[1].replace(index(0).await, 97);',
                            'let previous = a[1][0] + 1;'), 'reçu u8'),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(Error, diagnostic):
                verify_program(candidate.replace('INDEX','1'))

    def test_async_byte_array_element_loan_protects_local_frame(self):
        source = """
            async fn read(value: &u8) -> u8 { yield; return *value; }
            async fn patch(s: &mut String) {
                let mut a: [u8;2] = [97,98];
                let view = &a[0];
                BEFORE
                let copied = read(view).await;
                a[0] = 99;
                s.replace_byte(0, copied);
                s.replace_byte(1, a[0]);
            }
            fn main() {
                let mut p = pool<String>(1); let mut s = p.new(); s.push_str("xx");
                let h = runtime::spawn(-> patch(&mut s));
                match h.join() { Ok(()) => { print(&s[..]); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source.replace('BEFORE',''))).stdout, 'ac\n')
        for statement in ('a[1] = 100;', 'let moved = <- a;'):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(source.replace('BEFORE', statement))
        with self.assertRaisesRegex(Error, 'non durable'):
            verify_program("""
                async fn bad() -> &u8 {
                    let a: [u8;1] = [97];
                    yield;
                    return &a[0];
                }
                fn main() {}
            """)

    def test_async_byte_array_returned_loan_keeps_caller_storage_reserved(self):
        source = """
            async fn lend(a: &[u8;2]) -> &u8 { yield; return &a[1]; }
            async fn relay(a: &[u8;2]) -> &u8 { return lend(a).await; }
            fn unwrap(h: -> Execution<relay>, fallback: &u8) -> &u8 {
                return match h.join() { Ok(value) => { value }, Err(_) => { fallback } };
            }
            fn main() {
                let mut a: [u8;2] = [97,98];
                let mut p = pool<String>(1); let mut s = p.new(); s.push_str("xx");
                let h = runtime::spawn(-> relay(&a));
                let r = unwrap(-> h, &"z"[0]);
                BEFORE
                match s.replace_byte(0,*r) { Ok(_) => {}, Err(_) => { print(98); } }
                a[1] = 99;
                match s.replace_byte(1,a[1]) { Ok(_) => {}, Err(_) => { print(98); } }
                print(&s[..]);
            }
        """
        code = compile_source(source.replace('BEFORE', ''))
        self.assertEqual(self.run_c_oracle(code).stdout, 'bc\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, 'zc\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('BEFORE', 'a[0] = 100;'))

        relay = """
            async fn lend(a: &[u8;2]) -> &u8 { yield; return &a[1]; }
            async fn patch(s: &mut String) {
                let mut a: [u8;2] = [97,98];
                let h = runtime::spawn(-> lend(&a));
                match h.await {
                    Ok(r) => {
                        BEFORE
                        s.replace_byte(0,*r);
                        a[1] = 99;
                        s.replace_byte(1,a[1]);
                    },
                    Err(_) => { print(99); }
                }
            }
            fn main() {
                let mut p = pool<String>(1); let mut s = p.new(); s.push_str("xx");
                let h = runtime::spawn(-> patch(&mut s));
                match h.join() { Ok(()) => { print(&s[..]); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(relay.replace('BEFORE', ''))).stdout, 'bc\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(relay.replace('BEFORE', 'a[0] = 100;'))

    def test_async_array_repeat_evaluates_once_and_empty_length_is_static(self):
        source = """
            async fn item(n: Int) -> Int { print(n); yield; return n; }
            async fn empty_len(row: &[Int; 0]) -> Int { return row.len(); }
            async fn parent() -> Int {
                let mut table = [[item(7).await; 2]; 3];
                table[0][0] = 11;
                let zero = [item(8).await; 0];
                let empty: [Int; 0] = [];
                let nested: [[Int; 0]; 2] = [[], []];
                print(table.len());
                print(table[0].len());
                print(zero.len());
                print(empty_len(&empty).await);
                print(nested[1].len());
                return table[0][0] + table[2][1];
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n8\n3\n2\n0\n0\n0\n18\n')
        for bad, diagnostic in (
            (source.replace('let empty: [Int; 0] = [];', 'let empty = [];'), 'type de contexte'),
            (source.replace('let zero = [item(8).await; 0];', 'let zero: [Int; 2] = [item(8).await; 0];'),
             'dimensions incompatibles'),
            (source.replace('print(zero.len());', 'print(zero[0]);'), 'hors limites'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad)

    def test_async_array_replace_and_swap_check_places_in_order(self):
        source = """
            async fn index(mark: Int, value: Int) -> Int { print(mark); yield; return value; }
            async fn parent(i: Int) -> Int {
                let mut table = [[10, 20], [30, 40]];
                let old = table[index(1, 0).await].replace(index(2, i).await, index(3, 70).await);
                table[index(4, 0).await].swap(index(5, 0).await, index(6, 1).await);
                table[0].swap(0, 0);
                print(old);
                print(table[0][0]);
                return table[0][1];
            }
            fn main() {
                let h = runtime::spawn(-> parent(ARG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('ARG', '0')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '1\n2\n3\n4\n5\n6\n10\n20\n70\n')
        bad_replace = self.run_c_oracle(compile_source(source.replace('ARG', '2')), 'indice hors limites')
        self.assertEqual(bad_replace.stdout, '1\n2\n')
        bad_swap = self.run_c_oracle(compile_source(valid.replace('index(5, 0)', 'index(5, 2)')), 'indice hors limites')
        self.assertEqual(bad_swap.stdout, '1\n2\n3\n4\n5\n')
        reserved = valid.replace('async fn parent', 'async fn edit(n: &mut Int) { yield; n.set(8); } async fn parent')
        reserved = reserved.replace('table[0].swap(0, 0);',
                                    'let child = edit(&mut table[0][0]); table[0].swap(0, 1); child.await;')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(reserved)
        disjoint = reserved.replace('edit(&mut table[0][0])', 'edit(&mut table[1][0])')
        self.assertEqual(self.run_c_oracle(compile_source(disjoint)).stdout,
                         '1\n2\n3\n4\n5\n6\n10\n70\n20\n')
        last_use = """
            async fn lend(n: &mut Int) -> &mut Int { return n; }
            async fn parent() -> Int {
                let mut a = [10];
                let mut view = lend(&mut a[0]).await;
                let old = a.replace(0, *view + 1);
                return old + a[0];
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(last_use)).stdout, '21\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(last_use.replace('return old + a[0];', 'print(*view); return old + a[0];'))

    def test_async_row_copy_and_swap_preserve_value_and_reservations(self):
        source = """
            async fn edit(n: &mut Int) { yield; n.set(33); }
            async fn parent() -> Int {
                let mut table = [[10, 20], [30, 40], [50, 60]];
                let child = edit(&mut table[2][0]);
                let mut copied: [Int; 2] = copy(table[0]);
                copied[0] = 11;
                table.swap(0, 1);
                table.swap(0, 0);
                child.await;
                print(copied[0]);
                print(copied[1]);
                print(table[0][0]);
                print(table[0][1]);
                print(table[1][0]);
                print(table[1][1]);
                return table[2][0];
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '11\n20\n30\n40\n10\n20\n33\n')
        for bad, diagnostic in (
            (source.replace('table.swap(0, 1);', 'table.swap(0, 2);'), 'emprunt actif'),
            (source.replace('copy(table[0])', 'copy(table[2])'), 'emprunt actif'),
            (source.replace('[Int; 2] = copy', '[Int; 3] = copy'), 'dimensions incompatibles'),
            (source.replace('copy(table[0])', 'table[0]'), 'liaison Int copiable'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad)

    def test_async_row_replace_returns_an_independent_old_value(self):
        source = """
            async fn value(mark: Int, n: Int) -> Int { print(mark); yield; return n; }
            async fn parent(i: Int) -> Int {
                let mut a = [[10, 20], [30, 40]];
                let mut old: [Int; 2] = a.replace(value(1, i).await, [value(2, 50).await, 60]);
                old[0] = 11;
                let other = a.replace(1, copy(a[1]));
                print(old[0]);
                print(old[1]);
                print(other[0]);
                print(a[0][0]);
                return a[1][1];
            }
            fn main() {
                let h = runtime::spawn(-> parent(ARG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('ARG', '0')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '1\n2\n11\n20\n30\n50\n40\n')
        failure = self.run_c_oracle(compile_source(source.replace('ARG', '2')), 'indice hors limites')
        self.assertEqual(failure.stdout, '1\n')
        with self.assertRaisesRegex(Error, 'dimensions incompatibles'):
            verify_program(valid.replace('[value(2, 50).await, 60]', '[value(2, 50).await]'))
        borrowed = 'async fn lend(n: &mut Int) -> &mut Int { return n; }' + valid.replace(
            'let mut old:', 'let mut view = lend(&mut a[0][0]).await; let mut old:',
        ).replace('value(1, i).await, [value(2, 50).await, 60]', '0, [*view + 40, 60]')
        self.assertEqual(self.run_c_oracle(compile_source(borrowed)).stdout, '11\n20\n30\n50\n40\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(borrowed.replace('old[0] = 11;', 'print(*view); old[0] = 11;'))

    def test_async_array_moves_to_local_and_control_receivers(self):
        source = """
            async fn hold(n: &Int) { yield; print(*n); }
            async fn parent(flag: Int) -> Int {
                let a = [10, 20];
                CHECK_BEFORE
                let mut b: [Int; 2] = <- a;
                CHECK_AFTER
                let c = {
                    let original = <- copy(b);
                    yield;
                    <- original
                };
                let selected = if flag == 0 {
                    let x = copy(c);
                    <- x
                } else {
                    let y = [30, 40];
                    <- y
                };
                b[0] = 11;
                return b[0] + selected[1];
            }
            fn main() {
                let h = runtime::spawn(-> parent(ARG));
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        valid = source.replace('CHECK_BEFORE', '').replace('CHECK_AFTER', '')
        for flag, expected in (('0', '31\n'), ('1', '51\n')):
            self.assertEqual(self.run_c_oracle(compile_source(valid.replace('ARG', flag))).stdout, expected)
        loop = valid.replace('let selected = if flag == 0 {', 'let selected = loop { if flag == 0 {').replace(
            '<- x\n', 'break <- x;\n',
        ).replace('} else {\n                    let y', '}\n                    let y').replace(
            '<- y\n', 'break <- y;\n',
        )
        for flag, expected in (('0', '31\n'), ('1', '51\n')):
            self.assertEqual(self.run_c_oracle(compile_source(loop.replace('ARG', flag))).stdout, expected)
        for bad, diagnostic in (
            (source.replace('CHECK_AFTER', 'print(a.len());'), 'plus utilisable'),
            (source.replace('CHECK_BEFORE', 'let child = hold(&a[0]);').replace('CHECK_AFTER', 'child.await;'),
             'emprunt actif'),
            (source.replace('let y = [30, 40];', 'let y = [30];'), 'même type'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad.replace('CHECK_BEFORE', '').replace('CHECK_AFTER', '').replace('ARG', '0'))

    def test_async_array_value_parameter_captures_a_snapshot(self):
        source = """
            async fn modify(n: &mut Int) -> Int { yield; n.set(90); return 1; }
            async fn read(mut row: [Int; 2], extra: Int) -> Int {
                yield;
                row[1] = row[1] + 2;
                return row[0] + row[1] + extra;
            }
            async fn parent() -> Int {
                let mut a = [10, 20];
                let pending = read(copy(a), modify(&mut a[0]).await);
                let n = pending.await;
                return n + a[0] + a[1];
            }
            async fn matrix(a: [[Int; 2]; 2]) -> Int { yield; return a[1][0]; }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                let mut a = [[10, 20], [30, 40]];
                let child = matrix(copy(a));
                a[1][0] = 80;
                let h2 = runtime::spawn(-> child);
                match h2.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
                print(a[1][0]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '143\n30\n80\n')
        moved = source.replace('read(copy(a), modify(&mut a[0]).await)', 'read(-> a, 1)').replace(
            'return n + a[0] + a[1];', 'return n;',
        )
        self.assertEqual(self.run_c_oracle(compile_source(moved)).stdout, '33\n30\n80\n')
        literal = moved.replace('read(-> a, 1)', 'read([10, 20], 1)')
        self.assertEqual(self.run_c_oracle(compile_source(literal)).stdout, '33\n30\n80\n')
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(moved.replace('return n;', 'return n + a[0];'))
        with self.assertRaisesRegex(Error, 'copie ou déplacement explicite'):
            verify_program(source.replace('read(copy(a),', 'read(a,'))

    def test_async_array_return_is_extracted_before_task_slot_reuse(self):
        source = """
            async fn make(n: Int) -> [Int; 2] {
                let a = [n, n + 1];
                yield;
                return <- a;
            }
            async fn relay(n: Int) -> [Int; 2] {
                let task = make(n);
                let received = task.await;
                return <- copy(received);
            }
            async fn parent() -> Int {
                let mut first: [Int; 2] = relay(10).await;
                let second = relay(30).await;
                first[1] = 12;
                print(first[0]);
                print(first[1]);
                print(second[0]);
                return second[1];
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        code = '#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '10\n12\n30\n31\n')
        for bad, diagnostic in (
            (source.replace('return <- a;', 'return a;'), 'transfert explicite'),
            (source.replace('let a = [n, n + 1];', 'let a = [n];'), 'dimensions incompatibles'),
            (source.replace('first: [Int; 2]', 'first: [Int; 3]'), 'dimensions incompatibles'),
            (source.replace('let second = relay(30).await;', 'relay(30).await;'), 'résultat de tableau'),
        ):
            with self.assertRaisesRegex(Error, diagnostic):
                verify_program(bad)

    def test_async_spawn_array_result_uses_shaped_join_storage(self):
        source = """
            async fn make(n: Int) -> [Int; 2] {
                let a = [n, n + 1];
                yield;
                return <- a;
            }
            async fn parent() -> Int {
                let first = runtime::spawn(-> make(10));
                let received = first.await;
                let a = match received {
                    Ok(value) => { <- value },
                    Err(_) => { let fallback = [90, 91]; <- fallback }
                };
                let second = runtime::spawn(-> make(30));
                let b = match second.await {
                    Ok(value) => { <- value },
                    Err(_) => { let fallback = [92, 93]; <- fallback }
                };
                print(a[0]);
                print(a[1]);
                print(b[0]);
                return b[1];
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        code = '#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '10\n11\n30\n31\n')
        failed = inject_submission_failure(code)
        self.assertEqual(self.run_c_oracle(failed).stdout, '90\n91\n92\n93\n')
        abandoned = source.replace('make(n: Int)', 'make(n: Int, guard: &Int)').replace(
            'let first = runtime::spawn(-> make(10));', 'let guard = 0; let first = runtime::spawn(-> make(10, &guard));',
        ).replace('let received = first.await;', 'drop(-> first);')
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(abandoned)

    def test_sync_join_extracts_array_with_its_declared_shape(self):
        source = """
            async fn make(n: Int) -> [[Int; 2]; 2] {
                let matrix = [[n, n + 1], [n + 2, n + 3]];
                yield;
                return <- matrix;
            }
            fn collect(h: -> Execution<make>) -> Int {
                let result = h.join();
                match result {
                    Ok(matrix) => { return matrix[1][0]; },
                    Err(_) => { return 99; }
                }
            }
            fn main() {
                let first = runtime::spawn(-> make(10));
                print(collect(-> first));
                let second = runtime::spawn(-> make(30));
                match second.join() {
                    Ok(matrix) => { print(matrix[0][1]); print(matrix[1][1]); },
                    Err(_) => { print(98); }
                }
            }
        """
        code = '#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '12\n31\n33\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n98\n')
        valued = source.replace(
            'match second.join() {\n                    Ok(matrix) => { print(matrix[0][1]); print(matrix[1][1]); },'
            '\n                    Err(_) => { print(98); }\n                }',
            '''let selected = match second.join() {
                    Ok(matrix) => { <- matrix },
                    Err(_) => { let fallback = [[0, 0], [0, 0]]; <- fallback }
                };
                print(selected[0][1]);
                print(selected[1][1]);''',
        )
        self.assertIn('let selected = match', valued)
        self.assertEqual(self.run_c_oracle(compile_source(valued)).stdout, '12\n31\n33\n')
        borrowed = source.replace('make(n: Int)', 'make(n: Int, guard: &Int)').replace(
            'let first = runtime::spawn(-> make(10));',
            'let mut p = pool<Int>(1); let guard = p.new(0); let first = runtime::spawn(-> make(10, &guard));',
        ).replace('make(30)', 'make(30, &guard)').replace('print(collect(-> first));', 'drop(-> first);')
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(borrowed)

    def test_array_result_handle_requires_wait_and_internal_release_is_exactly_once(self):
        source = """
            async fn worker(n: Int) -> [Int; 8] {
                yield;
                print(n);
                let a = [n; 8];
                return <- a;
            }
            async fn parent() {
                let h = runtime::spawn(-> worker(20));
                drop(-> h);
            }
            fn main() {
                let first = runtime::spawn(-> worker(10));
                drop(-> first);
                let second = runtime::spawn(-> parent());
                drop(-> second);
            }
        """
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(source)
        valid = source.replace('drop(-> h);', 'match h.await { Ok(a) => { drop(-> a); }, Err(_) => {} }').replace(
            'drop(-> first);', 'match first.join() { Ok(a) => { drop(-> a); }, Err(_) => {} }').replace(
            'drop(-> second);', 'match second.join() { Ok(()) => {}, Err(_) => {} }')
        run = self.run_c_oracle(compile_source(valid))
        self.assertEqual(sorted(run.stdout.splitlines()), ['10', '20'])

        code = compile_source('async fn worker() -> [Int; 8] { let a = [1; 8]; return <- a; } fn main() {}')
        harness = r'''
        #undef main
        static int release_count;
        static void unexpected_take(CrustTask *task, void *out) {
            (void)task; (void)out; abort();
        }
        static void count_release(CrustTask *task) { (void)task; ++release_count; }
        static CrustTaskStep complete(CrustTask *task) { (void)task; return TASK_STEP_RETURN; }
        int main(void) {
            CrustTask task;
            const CrustTaskOps ops = {complete, unexpected_take, count_release};
            task_init(&task, &ops);
            if (task_drop_complete(&task)) return 1;
            if (task_poll(&task) != TASK_COMPLETE) return 2;
            if (!task_drop_complete(&task) || task_drop_complete(&task)) return 3;
            return release_count != 1;
        }
        '''
        self.run_c_oracle('#define main crust_sync_main\n' + code + harness)

    def test_sync_async_capture_of_inline_field_reserves_its_carrier(self):
        source = """
            struct Point { x: Int, y: Int }
            async fn lend(n: &mut Int) -> &mut Int { yield; n.set(7); return n; }
            fn main() {
                let mut p = pool<Point>(1);
                let mut point = p.new(x: 1, y: 2);
                let task = lend(&mut point.x);
                BEFORE
                let h = runtime::spawn(-> task);
                point.y = 4;
                DURING
                match h.join() {
                    Ok(view) => { point.y = 5; MATCH *view = 9; },
                    Err(_) => { print(99); }
                }
                print(point.x);
                print(point.y);
                drop(-> point);
                let again = p.new(x: 11, y: 12);
                print(again.x);
            }
        """
        program = source.replace('BEFORE', '').replace('DURING', '').replace('MATCH', '')
        code = compile_source(program)
        self.assertEqual(self.run_c_oracle(code).stdout, '9\n5\n11\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n1\n4\n11\n')
        for position, operation in (('BEFORE', 'drop(-> point);'), ('DURING', 'point.x = 8;'),
                                    ('MATCH', 'print(point.x);')):
            bad = source.replace(position, operation).replace('BEFORE', '').replace('DURING', '').replace('MATCH', '')
            with self.subTest(position=position), self.assertRaisesRegex(Error, 'emprunt actif|emprunt encore utilisé'):
                verify_program(bad)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(program.replace('point.y = 4;', 'p.reset();'), allow_legacy_reset=True)

    def test_sync_factory_returns_task_capturing_inline_field(self):
        source = """
            struct Point { x: Int, y: Int }
            async fn lend(n: &mut Int) -> &mut Int { yield; n.set(7); return n; }
            fn make(point: &mut Point) -> <- lend {
                let task = lend(&mut point.x);
                return <- task;
            }
            fn relay(point: &mut Point) -> <- lend {
                let task = make(point);
                return <- task;
            }
            fn main() {
                let mut p = pool<Point>(1);
                let mut point = p.new(x: 1, y: 2);
                let t = relay(&mut point);
                point.y = 4;
                BEFORE
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(view) => { point.y = 5; DURING *view = 9; },
                    Err(_) => { print(99); }
                }
                print(point.x);
                print(point.y);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '9\n5\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n1\n4\n')
        for position in ('BEFORE', 'DURING'):
            bad = source.replace(position, 'point.x = 8;').replace('BEFORE', '').replace('DURING', '')
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad)
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(valid.replace('point.y = 4;', 'p.reset();'), allow_legacy_reset=True)
        local_capture = source[:source.index('            fn make')] + """
            fn make() -> <- lend {
                let mut p = pool<Point>(1);
                let mut point = p.new(x: 1, y: 2);
                let task = lend(&mut point.x);
                return <- task;
            }
            fn main() {}
        """
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(local_capture)

    def test_returned_task_captures_inline_field_before_reference_replacement(self):
        source = """
            struct Point { x: Int, y: Int }
            struct View { target: &Point }
            async fn read(n: &Int) -> &Int { yield; return n; }
            fn prepare(v: &mut View, replacement: &Point) -> <- read {
                let point = &*v.target;
                let task = read(&point.x);
                v.target = &*replacement;
                return <- task;
            }
            fn relay(v: &mut View, replacement: &Point) -> <- read {
                REPLACE
                let task = prepare(v, replacement);
                return <- task;
            }
            fn main() {
                let mut first = pool<Point>(1);
                let mut second = pool<Point>(1);
                let a = first.new(x: 5, y: 6);
                let b = second.new(x: 7, y: 8);
                let mut views = pool<View>(1);
                let mut v = views.new(target: &a);
                let t = relay(&mut v, &b);
                drop(-> v);
                BEFORE
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(x) => { AFTER print(*x); },
                    Err(_) => { print(99); }
                }
            }
        """
        for replacement, captured, other, expected in (
                ('', 'a', 'b', '5\n'), ('v.target = &*replacement;', 'b', 'a', '7\n')):
            with self.subTest(captured=captured):
                program = source.replace('REPLACE', replacement)
                drop_other = f'drop(-> {other});'
                valid = program.replace('BEFORE', drop_other).replace('AFTER', '')
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, expected)
                for position in ('BEFORE', 'AFTER'):
                    bad = program.replace(position, f'drop(-> {captured});')
                    bad = bad.replace('BEFORE', drop_other).replace('AFTER', '')
                    with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                        verify_program(bad)
                reset = 'first' if captured == 'a' else 'second'
                bad = program.replace('BEFORE', f'{reset}.reset();').replace('AFTER', '')
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(bad, allow_legacy_reset=True)

        conditional = source.replace('REPLACE', 'if change > 0 { v.target = &*replacement; }')
        conditional = conditional.replace('fn relay(v: &mut View, replacement: &Point)',
                                          'fn relay(v: &mut View, replacement: &Point, change: Int)')
        conditional = conditional.replace('relay(&mut v, &b)', 'relay(&mut v, &b, FLAG)').replace('AFTER', '')
        for flag, expected in ((0, '5\n'), (1, '7\n')):
            program = conditional.replace('FLAG', str(flag))
            self.assertEqual(self.run_c_oracle(compile_source(program.replace('BEFORE', ''))).stdout, expected)
            for candidate in ('a', 'b'):
                with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(program.replace('BEFORE', f'drop(-> {candidate});'))

    def test_returned_task_keeps_each_mutable_projection_carrier_in_scope(self):
        source = """
            struct Leaf { data: Int }
            struct Mid { leaf: &mut Leaf }
            struct Top { mid: &mut Mid }
            async fn change(n: &mut Int) -> &mut Int { yield; n.set(8); return n; }
            fn prepare(top: &mut Top) -> <- change {
                let mut mid = &mut *top.mid;
                let mut leaf = &mut *mid.leaf;
                let t = change(&mut leaf.data);
                return <- t;
            }
            fn relay(top: &mut Top) -> <- change {
                let t = prepare(top);
                return <- t;
            }
            fn main() {
                let mut leaves = pool<Leaf>(1);
                let mut leaf = leaves.new(data: 7);
                let mut mids = pool<Mid>(1);
                let mut mid = mids.new(leaf: &mut leaf);
                let mut tops = pool<Top>(1);
                let mut top = tops.new(mid: &mut mid);
                let t = relay(&mut top);
                BEFORE
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { DURING *x = 9; }, Err(_) => { print(99); } }
                drop(-> top);
                drop(-> mid);
                print(leaf.data);
            }
        """
        valid = source.replace('BEFORE', '').replace('DURING', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '9\n')
        transferred = valid.replace('let t = relay(&mut top);',
                                    'let t = { let inner = relay(&mut top); <- inner };')
        self.assertEqual(self.run_c_oracle(compile_source(transferred)).stdout, '9\n')
        for position in ('BEFORE', 'DURING'):
            for name, pool in (('top', 'tops'), ('mid', 'mids'), ('leaf', 'leaves')):
                with self.subTest(position=position, carrier=name):
                    bad = source.replace(position, f'drop(-> {name});')
                    with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                        verify_program(bad.replace('BEFORE', '').replace('DURING', ''))
                    bad = source.replace(position, f'{pool}.reset();')
                    with self.assertRaisesRegex(Error, 'reset interdit'):
                        verify_program(bad.replace('BEFORE', '').replace('DURING', ''), allow_legacy_reset=True)
        # The task returns a scalar so inspecting join cannot expose the
        # lifetime error later. The transfer itself must be refused.
        escaped = valid.replace('-> &mut Int { yield; n.set(8); return n; }',
                                '-> Int { yield; n.set(8); return *n; }')
        escaped = escaped.replace('let mut tops =', 'let t = { let mut tops =')
        escaped = escaped.replace('let t = relay(&mut top);', 'let inner = relay(&mut top); <- inner };')
        escaped = escaped.replace('drop(-> top);', '').replace('*x = 9;', 'print(x);')
        with self.assertRaisesRegex(Error, 'transfert refusé : cible empruntée non durable'):
            verify_program(escaped)

    def test_factory_captures_two_projected_scalar_arguments(self):
        source = """
            struct Point { x: Int, y: Int }
            async fn change(n: &mut Int, m: &mut Int) -> &mut Int {
                yield;
                n.set(8);
                m.set(12);
                return n;
            }
            fn factory(n: &mut Int, m: &mut Int) -> <- change {
                let task = change(n, m);
                return <- task;
            }
            fn main() {
                let mut p = pool<Point>(1);
                let mut point = p.new(x: 1, y: 2);
                let t = factory(&mut point.x, &mut point.y);
                BEFORE
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(x) => { print(point.y); point.y = 13; *x = 9; },
                    Err(_) => { print(99); }
                }
                print(point.x);
                print(point.y);
            }
        """
        valid = source.replace('BEFORE', '')
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '12\n9\n13\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(t,a,r,p) EAGAIN')
        self.assertEqual(self.run_c_oracle(failed).stdout, '99\n1\n2\n')
        for bad in (source.replace('BEFORE', 'point.y = 13;'),
                    valid.replace('point.y = 13;', 'point.x = 13;'),
                    valid.replace('&mut point.y);', '&mut point.x);')):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad)

    def test_factory_captures_inline_array_cells_from_distinct_roots(self):
        source = """
            async fn change(n: &mut Int, m: &mut Int) -> &mut Int {
                yield;
                n.set(8);
                m.set(12);
                return n;
            }
            fn factory(n: &mut Int, m: &mut Int) -> <- change {
                let t = change(n, m);
                return <- t;
            }
            fn main() {
                let mut row = [1, 2];
                let mut other = [3, 4];
                let t = factory(&mut row[0], &mut other[1]);
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(x) => { other[1] = 13; *x = 9; },
                    Err(_) => { print(99); }
                }
                print(row[0]);
                print(other[1]);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '9\n13\n')
        for bad in (
                source.replace('&mut other[1]);', '&mut row[0]);'),
                source.replace('&mut other[1]);', '&mut row[1]);'),
                source.replace('let h =', 'other[0] = 16; let h ='),
                source.replace('other[1] = 13;', 'row[1] = 13;')):
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(bad)
        escaped = source.replace('let t = factory(&mut row[0], &mut other[1]);',
                                 'let t = { let mut inner = [5]; '
                                 'let pending = factory(&mut inner[0], &mut other[1]); <- pending };')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaped)

    def test_async_owned_int_crosses_computed_scope_and_loop(self):
        source = """
            async fn parent(n: -> Int) -> <- Int {
                let mut i = 0;
                loop {
                    n ->;
                    <- n;
                    if i == 0 { i = 1; yield; continue; }
                    break;
                }
                let received = BODY;
                return <- received;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = p.new(5);
                let h = runtime::spawn(-> parent(-> n));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let next = p.new(7);
                print(next);
            }
        """
        for body in ('{ n ->; yield; <- n }',
                     'if i > 0 { n ->; <- n } else { n ->; <- n }',
                     'loop { n ->; yield; break <- n; }'):
            with self.subTest(body=body):
                program = source.replace('BODY', body)
                run = self.run_c_oracle(compile_source(program))
                self.assertEqual(run.stdout, '5\n7\n')
                self.assertEqual(run.stderr.count('destroy n=5\n'), 1)
                with self.assertRaisesRegex(Error, 'continue doit préserver'):
                    verify_program(program.replace('<- n;', '', 1))

    def test_computed_void_task_cleans_owned_capture_on_await_or_drop(self):
        source = """
            async fn work(n: -> Int) { yield; print(*n); }
            async fn parent(a: -> Int, b: -> Int, flag: Int) {
                CONSUME
            }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let a = first.new(5);
                let b = second.new(7);
                let h = runtime::spawn(-> parent(-> a, -> b, FLAG));
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                let reused_a = first.new(15);
                let reused_b = second.new(17);
                print(reused_a);
                print(reused_b);
            }
        """
        task = """
            if flag > 0 {
                a ->;
                b ->;
                drop(-> b);
                let selected = work(-> a);
                yield;
                <- selected
            } else {
                a ->;
                b ->;
                drop(-> a);
                let selected = work(-> b);
                <- selected
            }
        """
        for consume, reads in ((f'({task}).await;', True), (f'let t = {task}; drop(-> t);', False)):
            for flag, amount in ((0, 7), (1, 5)):
                with self.subTest(reads=reads, flag=flag):
                    program = source.replace('CONSUME', consume).replace('FLAG', str(flag))
                    run = self.run_c_oracle(compile_source(program))
                    self.assertEqual(run.stdout, (f'{amount}\n' if reads else '') + '15\n17\n')
                    self.assertEqual(run.stderr.count('destroy a=5\n'), 1)
                    self.assertEqual(run.stderr.count('destroy b=7\n'), 1)
        returned = source.replace('CONSUME', '{ a ->; yield; <- a; } print(*a); drop(-> b);').replace('FLAG', '1')
        run = self.run_c_oracle(compile_source(returned))
        self.assertEqual(run.stdout, '5\n15\n17\n')
        self.assertEqual(run.stderr.count('destroy a=5\n'), 1)
        self.assertEqual(run.stderr.count('destroy b=7\n'), 1)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(returned.replace('<- a;', ''))

    def test_async_await_statement_consumes_computed_void_task(self):
        source = """
            async fn work(n: &mut Int) { yield; n.set(9); }
            async fn parent(flag: Int) -> Int {
                let mut a = 5;
                let mut b = 7;
                (OPERAND).await;
                return a * 10 + b;
            }
            fn main() {
                let h = runtime::spawn(-> parent(FLAG));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
            }
        """
        branch = 'if flag > 0 { let t = work(&mut a); yield; <- t } else { let t = work(&mut b); <- t }'
        for operand, flag, output in (
                ('{ let t = work(&mut a); <- t }', 1, '97\n'),
                (branch, 1, '97\n'), (branch, 0, '59\n'),
                ('loop { let t = work(&mut b); yield; break <- t; }', 0, '59\n')):
            with self.subTest(operand=operand, flag=flag):
                program = source.replace('OPERAND', operand).replace('FLAG', str(flag))
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, output)
        valid = source.replace('OPERAND', branch).replace('FLAG', '1')
        with self.assertRaisesRegex(Error, 'receveur Int'):
            verify_program(valid.replace('work(n: &mut Int) { yield; n.set(9); }',
                                         'work(n: &mut Int) -> Int { yield; return *n; }'))
        with self.assertRaisesRegex(Error, 'tâche inactive'):
            verify_program(source.replace('OPERAND', 'runtime::spawn(-> work(&mut a))').replace('FLAG', '1'))

    def test_sync_join_consumes_computed_handle_and_keeps_pool_provenance(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn collect(n: -> Int, flag: Int) -> <- Result<A<Int>,runtime::Error> {
                let result = HANDLE.join();
                return <- result;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = p.new(5);
                let result = collect(-> n, 1);
                CHECK
                match result { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let reused = p.new(7);
                print(reused);
            }
        """
        spawn = 'runtime::spawn(-> work(-> n))'
        branch = ('let t = work(-> n); let h = runtime::spawn(-> t); <- h')
        computed = f'(if flag > 0 {{ n ->; {branch} }} else {{ n ->; {branch} }})'
        for handle in (spawn, computed):
            with self.subTest(handle=handle):
                program = source.replace('HANDLE', handle)
                if handle == spawn:
                    program = program.replace('n: -> Int, flag: Int', 'n: -> Int').replace('collect(-> n, 1)', 'collect(-> n)')
                code = compile_source(program.replace('CHECK', ''))
                self.assertEqual(self.run_c_oracle(code).stdout, '5\n7\n')
                failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                      '#define pthread_create(t,a,r,p) EAGAIN', 1)
                self.assertEqual(self.run_c_oracle(failed).stdout, '99\n7\n')
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('CHECK', 'p.reset();'), allow_legacy_reset=True)
        invalid = """
            async fn work(n: Int) -> Int { return n; }
            fn main() { let result = work(5).join(); }
        """
        with self.assertRaisesRegex(Error, 'join exige un handle'):
            verify_program(invalid)

    def test_async_spawn_and_await_in_one_expression_launches_once(self):
        source = """
            async fn work(n: &mut Int) -> &mut Int { yield; return n; }
            async fn parent() -> Int {
                let mut n = 5;
                BIND
                match SUBJECT { Ok(x) => { CHECK x.set(9); }, Err(_) => {} }
                return n;
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        await_spawn = 'runtime::spawn(-> work(&mut n)).await'
        for binding, subject in (('', await_spawn), (f'let r = {await_spawn};', 'r')):
            program = source.replace('BIND', binding).replace('SUBJECT', subject)
            code = compile_source(program.replace('CHECK', ''))
            for launch, expected in (('pthread_create(t,a,r,p)', '9\n'), ('EAGAIN', '5\n')):
                with self.subTest(named=bool(binding), launch=launch):
                    instrumented = inject_submission_failure(
                        code, at=1 if launch == 'EAGAIN' else 0, maximum=1).replace(
                        'static int task_async_ready(const CrustAsyncExecution *execution) {',
                        'static int task_async_ready(const CrustAsyncExecution *execution) {\n'
                        '    static int first_poll = 1;\n'
                        '    if (first_poll) { first_poll = 0; return 0; }',
                        1,
                    )
                    self.assertEqual(self.run_c_oracle(instrumented).stdout, expected)
            with self.assertRaisesRegex(Error, 'emprunt actif'):
                verify_program(program.replace('CHECK', 'print(n);'))

    def test_async_await_computed_handle_preserves_result_loans(self):
        source = """
            async fn worker(n: &mut Int) -> &mut Int { yield; return n; }
            async fn parent(flag: Int) -> Int {
                let mut a = 5;
                let mut b = 7;
                BIND
                match SUBJECT {
                    Ok(x) => { CHECK x.set(9); },
                    Err(_) => { print(a); print(b); }
                }
                return a * 10 + b;
            }
            fn main() {
                let h = runtime::spawn(-> parent(FLAG));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        operand = """(if flag > 0 {
            let t = worker(&mut a); let h = runtime::spawn(-> t); yield; <- h
        } else {
            let t = worker(&mut b); let h = runtime::spawn(-> t); <- h
        }).await"""
        for binding, subject in (('', operand), (f'let result = {operand}; yield;', 'result')):
            for flag, output in ((0, '59\n'), (1, '97\n')):
                with self.subTest(named=bool(binding), flag=flag):
                    program = source.replace('BIND', binding).replace('SUBJECT', subject).replace('FLAG', str(flag))
                    code = compile_source(program.replace('CHECK', ''))
                    self.assertEqual(self.run_c_oracle(code).stdout, output)
                    failed = inject_submission_failure(code)
                    self.assertEqual(self.run_c_oracle(failed).stdout, '5\n7\n57\n')
                    for target in ('a', 'b'):
                        with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                            verify_program(program.replace('CHECK', f'print({target});'))

    def test_async_borrowed_return_tracks_computed_await_origins(self):
        source = """
            async fn read(n: &Int) -> &Int { yield; return n; }
            async fn choose(a: &Int, b: &Int, flag: Int) -> &Int { RETURN }
            async fn relay(a: &Int, b: &Int, flag: Int) -> &Int {
                return choose(a, b, flag).await;
            }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let mut a = first.new(5);
                let mut b = second.new(7);
                let h = runtime::spawn(-> relay(&a, &b, FLAG));
                match h.join() {
                    Ok(x) => { CHECK print(*x); },
                    Err(_) => { print(99); }
                }
                a.set(15);
                b.set(17);
                print(a);
                print(b);
            }
        """
        condition = 'if flag > 0 { let t = read(a); <- t } else { let t = read(b); <- t }'
        variants = (
            f'return ({condition}).await;',
            f'let chosen = {condition}; let got = chosen.await; return got;',
            'return (loop { if flag > 0 { let t = read(a); break <- t; } let t = read(b); break <- t; }).await;',
            f'return ({{ let chosen = {condition}; <- chosen }}).await;',
        )
        for body in variants:
            for flag, value in ((0, 7), (1, 5)):
                with self.subTest(body=body, flag=flag):
                    program = source.replace('RETURN', body).replace('FLAG', str(flag))
                    code = compile_source(program.replace('CHECK', ''))
                    self.assertEqual(self.run_c_oracle(code).stdout, f'{value}\n15\n17\n')
                    for target in ('a', 'b'):
                        with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                            verify_program(program.replace('CHECK', f'{target}.set(1);'))
        escaped = source.replace('RETURN', 'let local = 1; return ({ let t = read(&local); <- t }).await;')
        with self.assertRaisesRegex(Error, 'paramètre partagé durable'):
            verify_program(escaped.replace('FLAG', '1').replace('CHECK', ''))

    def test_async_computed_await_receives_borrowed_and_owned_results(self):
        borrowed = """
            async fn work(n: &mut Int) -> &mut Int { yield; return n; }
            async fn parent(flag: Int) -> Int {
                let mut a = 5;
                let mut b = 7;
                let mut r = (if flag > 0 {
                    let t = work(&mut a);
                    <- t
                } else {
                    let t = work(&mut b);
                    <- t
                }).await;
                CHECK
                r.set(9);
                return a * 10 + b;
            }
            fn main() {
                let h = runtime::spawn(-> parent(FLAG));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
            }
        """
        for flag, output in ((0, '59\n'), (1, '97\n')):
            program = borrowed.replace('FLAG', str(flag))
            self.assertEqual(self.run_c_oracle(compile_source(program.replace('CHECK', ''))).stdout, output)
            for target in ('a', 'b'):
                with self.subTest(flag=flag, target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('CHECK', f'print({target});'))
        owned = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            async fn parent(n: -> Int) -> <- Int {
                let received = ({ let t = work(-> n); <- t }).await;
                return <- received;
            }
            fn main() {
                let mut p = pool<Int>(1);
                let n = p.new(5);
                let h = runtime::spawn(-> parent(-> n));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let reused = p.new(7);
                print(reused);
            }
        """
        run = self.run_c_oracle(compile_source(owned))
        self.assertEqual(run.stdout, '5\n7\n')
        self.assertEqual(run.stderr.count('destroy n=5\n'), 1)

    def test_async_await_consumes_computed_task_across_suspension(self):
        source = """
            async fn work(n: &mut Int) -> Int { yield; n.set(9); return *n; }
            async fn parent(flag: Int) -> Int {
                let mut a = 5;
                let mut b = 7;
                let result = (OPERAND).await;
                return result + a + b;
            }
            fn main() {
                let h = runtime::spawn(-> parent(FLAG));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        operands = (
            ('{ let t = work(&mut a); yield; <- t }', ((1, '25\n'),)),
            ('if flag > 0 { let t = work(&mut a); yield; <- t } else { let t = work(&mut b); <- t }',
             ((1, '25\n'), (0, '23\n'))),
            ('loop { let t = work(&mut b); yield; break <- t; }', ((0, '23\n'),)),
        )
        for operand, cases in operands:
            for flag, output in cases:
                with self.subTest(operand=operand, flag=flag):
                    program = source.replace('OPERAND', operand).replace('FLAG', str(flag))
                    self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, output)
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(source.replace('FLAG', '1').replace(
                'OPERAND', '{ let mut local = 5; let t = work(&mut local); <- t }',
            ))

    def test_async_spawn_transfers_task_chosen_by_join_match(self):
        source = """
            async fn gate() -> Int { yield; return 5; }
            async fn work(n: Int) -> Int { yield; return n; }
            async fn parent() -> Int {
                let gate_handle = runtime::spawn(-> gate());
                let worker = runtime::spawn(-> match gate_handle.await {
                    Ok(n) => { let t = work(n); <- t },
                    Err(_) => { let t = work(7); <- t }
                });
                return match worker.await { Ok(x) => { x }, Err(_) => { 99 } };
            }
            fn main() {
                let h = runtime::spawn(-> parent());
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '5\n')
        failed = inject_submission_failure(code, at=1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '7\n')

    def test_async_if_transfers_task_or_handle_with_all_possible_captures(self):
        source = """
            async fn worker(n: &mut Int) -> Int { yield; n.set(9); return *n; }
            async fn other(n: &mut Int) -> Int { return *n; }
            async fn parent(flag: Int) -> Int {
                let mut a = 5;
                let mut b = 7;
                SELECT
                yield;
                CHECK
                let result = match h.await { Ok(x) => { x }, Err(_) => { 90 } };
                return result + a + b;
            }
            fn main() {
                let h = runtime::spawn(-> parent(FLAG));
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        branch = 'if flag > 0 { let t = worker(&mut a); yield; EXIT } else { let t = worker(&mut b); EXIT }'
        task = branch.replace('EXIT', '<- t')
        started = branch.replace('EXIT', 'let child = runtime::spawn(-> t); <- child')
        for select in (f'let h = runtime::spawn(-> {task});',
                       f'let chosen = {task}; let h = runtime::spawn(-> chosen);',
                       f'let h = {started};'):
            for flag, output in ((0, '23\n'), (1, '25\n')):
                with self.subTest(select=select, flag=flag):
                    program = source.replace('SELECT', select).replace('FLAG', str(flag))
                    code = compile_source(program.replace('CHECK', ''))
                    self.assertEqual(self.run_c_oracle(code).stdout, output)
                    for name in ('a', 'b'):
                        with self.subTest(name=name), self.assertRaisesRegex(Error, 'emprunt actif'):
                            verify_program(program.replace('CHECK', f'print({name});'))
        distinct = source.replace('SELECT', f'let h = runtime::spawn(-> {task});').replace('FLAG', '1')
        with self.assertRaisesRegex(Error, 'même type et même mode'):
            verify_program(distinct.replace('CHECK', '').replace('worker(&mut b)', 'other(&mut b)'))
        escape = task.replace('let t = worker(&mut b);', 'let mut local = 7; let t = worker(&mut local);')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(source.replace('SELECT', f'let h = runtime::spawn(-> {escape});').replace(
                'FLAG', '1',
            ).replace('CHECK', ''))

    def test_spawn_transfers_computed_task_in_sync_and_async_contexts(self):
        source = """
            async fn worker(n: &mut Int) -> Int { yield; n.set(9); return *n; }
            async fn parent() -> Int {
                let mut n = 5;
                let h = runtime::spawn(-> CHILD);
                CHECK
                let result = match h.await { Ok(x) => { x }, Err(_) => { 90 } };
                return result + n;
            }
            fn main() {
                let h = runtime::spawn(-> ROOT);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        for child in ('worker(&mut n)', 'loop { let t = worker(&mut n); break <- t; }'):
            for root in ('parent()', 'if 1 > 0 { let t = parent(); <- t } else { let t = parent(); <- t }'):
                with self.subTest(child=child, root=root):
                    program = source.replace('CHILD', child).replace('ROOT', root)
                    valid = program.replace('CHECK', '')
                    code = compile_source(valid)
                    self.assertEqual(self.run_c_oracle(code).stdout, '18\n')
                    failed = inject_submission_failure(code)
                    self.assertEqual(self.run_c_oracle(failed).stdout, '95\n')
                    with self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(program.replace('CHECK', 'print(n);'))
                    with self.assertRaisesRegex(Error, 'transférée avec ->'):
                        verify_program(valid.replace('runtime::spawn(-> ' + root, 'runtime::spawn(' + root))

    def test_one_task_can_capture_two_shared_descendants_of_writer(self):
        source = """
            struct View { target: &Int }
            async fn read(a: &Int, b: &Int) -> Int { yield; return *a + *b; }
            fn main() {
                let mut ints = pool<Int>(1);
                let mut a = ints.new(5);
                let writer = &mut a;
                let mut views = pool<View>(1);
                let v = views.new(target: &*writer);
                let t = read(&*v.target, &*v.target);
                let h = runtime::spawn(-> t);
                print(v);
                drop(-> v);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                writer.set(6);
                print(*writer);
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, 'View(5)\n10\n6\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('read(&*v.target, &*v.target)', 'read(&*v.target, &*writer)'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('b: &Int', 'b: &mut Int').replace(
                'read(&*v.target, &*v.target)', 'read(&*v.target, writer)',
            ))

    def test_computed_task_argument_reserves_captures_during_later_arguments(self):
        source = """
            enum Side { First, Second }
            async fn edit(n: &mut Int) -> Int { n.set(9); return *n; }
            fn run(PARAMETERS) -> Int {
                let h = runtime::spawn(-> task);
                return match h.join() { Ok(x) => { x + amount }, Err(_) => { 99 } };
            }
            fn main() {
                let mut p = pool<Int>(2);
                let mut a = p.new(5);
                let mut b = p.new(7);
                SETUP
                let total = run(ARGUMENTS);
                print(total);
                print(a);
                print(b);
            }
        """
        first = 'let t = edit(&mut a);'
        second = 'let t = edit(&mut b);'
        constructs = (
            ('if', '', f'if 1 > 0 {{ {first} <- t }} else {{ {second} <- t }}'),
            ('loop', '', f'loop {{ if 1 > 0 {{ {first} break <- t; }} {second} break <- t; }}'),
            ('match', '''let mut choices = pool<Side>(1);
                         let side = if 1 > 0 { let s = new(choices) Side.First {}; <- s }
                                    else { let s = new(choices) Side.Second {}; <- s };''',
             f'match (-> side) {{ Side.First => {{ {first} <- t }}, Side.Second => {{ {second} <- t }} }}'),
        )
        for construct, setup, task in constructs:
            with self.subTest(construct=construct):
                program = source.replace('SETUP', setup)
                earlier = program.replace('PARAMETERS', 'amount: Int, task: -> edit').replace('ARGUMENTS', f'*a, -> {task}')
                self.assertEqual(self.run_c_oracle(compile_source(earlier)).stdout, '14\n9\n7\n')
                later = program.replace('PARAMETERS', 'task: -> edit, amount: Int').replace('ARGUMENTS', f'-> {task}, AMOUNT')
                self.assertEqual(self.run_c_oracle(compile_source(later.replace('AMOUNT', '1'))).stdout, '10\n9\n7\n')
                for target in ('a', 'b'):
                    with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(later.replace('AMOUNT', f'*{target}'))

    def test_task_and_handle_contracts_keep_control_flow_result_sources(self):
        source = """
            enum Choice { A, B }
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn build(a: &mut Pool<Int>, b: &mut Pool<Int>, flag: Int) -> <- NOMINAL {
                let selected = BODY;
                return <- selected;
            }
            fn relay(a: &mut Pool<Int>, b: &mut Pool<Int>, flag: Int) -> <- NOMINAL {
                let selected = build(a, b, flag);
                return <- selected;
            }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let selected = relay(&mut first, &mut second, FLAG);
                START
                let result = h.join();
                CHECK
                match result { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let a = first.new(15);
                let b = second.new(17);
                print(a);
                print(b);
            }
        """
        branch_a = 'let n = a.new(5); let t = work(-> n);'
        branch_b = 'let n = b.new(7); let t = work(-> n);'
        choice = (
            'let mut choices = pool<Choice>(1); '
            'let choice = if flag > 0 { let a = new(choices) Choice.A {}; <- a } '
            'else { let b = new(choices) Choice.B {}; <- b };'
        )
        constructs = (
            ('if', '', 'if flag > 0 { A EXIT } else { B EXIT }', '<- TRANSFERRED'),
            ('loop', '', 'loop { if flag > 0 { A EXIT } B EXIT }', 'break <- TRANSFERRED;'),
            ('match', choice, 'match (-> choice) { Choice.A => { A EXIT }, Choice.B => { B EXIT } }', '<- TRANSFERRED'),
        )
        for construct, setup, body, exit_value in constructs:
            for nominal, setup_exit, transferred, start in (
                    ('work', '', 't', 'let h = runtime::spawn(-> selected);'),
                    ('Execution<work>', 'let worker = runtime::spawn(-> t); ', 'worker', 'let h = <- selected;')):
                body_with_values = body.replace(' A ', f' {branch_a} ').replace(' B ', f' {branch_b} ')
                body_with_values = body_with_values.replace('EXIT', setup_exit + exit_value.replace('TRANSFERRED', transferred))
                program = source.replace('let selected = BODY;', setup + ' let selected = ' + body_with_values + ';')
                program = program.replace('NOMINAL', nominal).replace('START', start)
                for flag, amount in ((0, 7), (1, 5)):
                    with self.subTest(construct=construct, nominal=nominal, flag=flag):
                        case = program.replace('FLAG', str(flag))
                        valid = case.replace('CHECK', '')
                        contract = verify_program(valid).function_contracts['relay'].result
                        expected = {('source_parameter', 0), ('source_parameter', 1)}
                        for sources in (contract.task_sources, contract.task_result_sources):
                            self.assertEqual({(s.kind, s.index) for s in sources}, expected)
                        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, f'{amount}\n15\n17\n')
                        for pool in ('first', 'second'):
                            with self.assertRaisesRegex(Error, 'reset interdit'):
                                verify_program(case.replace('CHECK', f'{pool}.reset();'), allow_legacy_reset=True)

    def test_sync_match_transfers_task_or_execution_with_result_sources(self):
        source = """
            enum Choice { A, B }
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let mut choices = pool<Choice>(1);
                let mut choice = if FLAG > 0 {
                    let a = new(choices) Choice.A {};
                    <- a
                } else {
                    let b = new(choices) Choice.B {};
                    <- b
                };
                let selected = match SUBJECT {
                    Choice.A => { let a = first.new(5); let t = work(-> a); EXIT },
                    Choice.B => { let b = second.new(7); let t = work(-> b); EXIT }
                };
                START
                let result = h.join();
                CHECK
                match result { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let a2 = first.new(15);
                let b2 = second.new(17);
                print(a2);
                print(b2);
            }
        """
        for subject in ('(-> choice)', '&choice', '&mut choice'):
            for end, start in (('<- t', 'let h = runtime::spawn(-> selected);'),
                               ('let worker = runtime::spawn(-> t); <- worker', 'let h = <- selected;')):
                program = source.replace('SUBJECT', subject).replace('EXIT', end).replace('START', start)
                for flag, value in ((1, 5), (0, 7)):
                    with self.subTest(subject=subject, end=end, flag=flag):
                        case = program.replace('FLAG', str(flag))
                        run = self.run_c_oracle(compile_source(case.replace('CHECK', '')))
                        self.assertEqual(run.stdout, f'{value}\n15\n17\n')
                        for pool in ('first', 'second'):
                            with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                                verify_program(case.replace('CHECK', f'{pool}.reset();'), allow_legacy_reset=True)

    def test_sync_join_match_transfers_task_from_ok_or_error_arm(self):
        source = """
            async fn gate() -> Int { yield; return 5; }
            async fn work(n: Int) -> Int { yield; return n; }
            fn main() {
                let gate_task = gate();
                let h = runtime::spawn(-> gate_task);
                let selected = match h.join() {
                    Ok(n) => { let task = work(n); <- task },
                    Err(_) => { let task = work(7); <- task }
                };
                let worker = runtime::spawn(-> selected);
                match worker.join() { Ok(n) => { print(n); }, Err(_) => { print(99); } }
            }
        """
        code = compile_source(source)
        self.assertEqual(self.run_c_oracle(code).stdout, '5\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              'static int starts;\n'
                              '#define pthread_create(t,a,r,p) (++starts == 1 ? EAGAIN : pthread_create(t,a,r,p))', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '7\n')

    def test_sync_if_transfers_task_or_execution_with_result_sources(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let selected = if FLAG > 0 {
                    let a = first.new(5);
                    let t = work(-> a);
                    EXIT
                } else {
                    let b = second.new(7);
                    let t = work(-> b);
                    EXIT
                };
                START
                let result = h.join();
                CHECK
                match result { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let a2 = first.new(15);
                let b2 = second.new(17);
                print(a2);
                print(b2);
            }
        """
        for end, start in (('<- t', 'let h = runtime::spawn(-> selected);'),
                           ('let worker = runtime::spawn(-> t); <- worker', 'let h = <- selected;')):
            program = source.replace('EXIT', end).replace('START', start)
            for flag, value, label in ((0, 7, 'b'), (1, 5, 'a')):
                with self.subTest(end=end, flag=flag):
                    case = program.replace('FLAG', str(flag))
                    code = compile_source(case.replace('CHECK', ''))
                    run = self.run_c_oracle(code)
                    self.assertEqual(run.stdout, f'{value}\n15\n17\n')
                    failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                          '#define pthread_create(t,a,r,p) EAGAIN', 1)
                    failed_run = self.run_c_oracle(failed)
                    self.assertEqual(failed_run.stdout, '99\n15\n17\n')
                    for execution in (run, failed_run):
                        self.assertEqual(execution.stderr.count(f'destroy {label}={value}\n'), 1)
                    for pool in ('first', 'second'):
                        with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                            verify_program(case.replace('CHECK', f'{pool}.reset();'), allow_legacy_reset=True)
        valid = source.replace('FLAG', '1').replace('EXIT', '<- t').replace(
            'START', 'let h = runtime::spawn(-> selected);',
        ).replace('CHECK', '')
        with self.assertRaisesRegex(Error, 'ne peut pas être copiée'):
            verify_program(valid.replace('<- t', 't', 1))
        other = 'async fn other(n: -> Int) -> <- Int { return <- n; }'
        with self.assertRaisesRegex(Error, 'même type'):
            verify_program(other + valid.replace('work(-> b)', 'other(-> b)'))

    def test_sync_loop_transfers_task_or_execution_with_result_sources(self):
        source = """
            async fn work(n: -> Int) -> <- Int { yield; return <- n; }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let selected = loop {
                    if FLAG > 0 {
                        let n = first.new(5);
                        let t = work(-> n);
                        EXIT
                    }
                    let n = second.new(7);
                    let t = work(-> n);
                    EXIT
                };
                START
                let result = h.join();
                CHECK
                match result { Ok(x) => { print(x); }, Err(_) => { print(99); } }
                let a = first.new(15);
                let b = second.new(17);
                print(a);
                print(b);
            }
        """
        for end, start in (('break <- t;', 'let h = runtime::spawn(-> selected);'),
                           ('let worker = runtime::spawn(-> t); break <- worker;', 'let h = <- selected;')):
            program = source.replace('EXIT', end).replace('START', start)
            for flag, output in ((0, '7\n15\n17\n'), (1, '5\n15\n17\n')):
                with self.subTest(end=end, flag=flag):
                    case = program.replace('FLAG', str(flag))
                    code = compile_source(case.replace('CHECK', ''))
                    self.assertEqual(self.run_c_oracle(code).stdout, output)
                    for pool in ('first', 'second'):
                        with self.subTest(pool=pool), self.assertRaisesRegex(Error, 'reset interdit'):
                            verify_program(case.replace('CHECK', f'{pool}.reset();'), allow_legacy_reset=True)
            local = program.replace('FLAG', '1').replace(
                'let n = first.new(5);', 'let mut local = pool<Int>(1); let n = local.new(5);',
            ).replace('CHECK', '')
            with self.assertRaisesRegex(Error, 'pool de capture ne survit pas'):
                verify_program(local)

    def test_workers_share_a_detached_capture_without_releasing_writer_early(self):
        source = """
            struct View { target: &Int }
            async fn read(n: &Int) -> &Int { yield; return n; }
            fn prepare(v: &View) -> <- read {
                let t = read(&*v.target);
                return <- t;
            }
            fn main() {
                let mut ints = pool<Int>(1);
                let mut a = ints.new(5);
                let writer = &mut a;
                let mut views = pool<View>(1);
                let v = views.new(target: &*writer);
                let first = prepare(&v);
                let h1 = runtime::spawn(-> first);
                let second = SECOND;
                let h2 = runtime::spawn(-> second);
                drop(-> v);
                match h1.join() { Ok(x) => { print(*x); }, Err(_) => { print(99); } }
                CHECK
                match h2.join() { Ok(x) => { print(*x); }, Err(_) => { print(99); } }
                writer.set(6);
                print(*writer);
            }
        """
        for second in ('prepare(&v)', 'read(&*v.target)'):
            with self.subTest(second=second):
                program = source.replace('SECOND', second)
                code = compile_source(program.replace('CHECK', ''))
                self.assertEqual(self.run_c_oracle(code).stdout, '5\n5\n6\n')
                failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                      'static int starts;\n'
                                      '#define pthread_create(t,a,r,p) (++starts == 1 ? EAGAIN : pthread_create(t,a,r,p))', 1)
                self.assertEqual(self.run_c_oracle(failed).stdout, '99\n5\n6\n')
                for statement in ('print(*writer);', 'writer.set(9);', 'print(a);'):
                    with self.subTest(statement=statement), self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(program.replace('CHECK', statement))

                first_match = 'match h1.join() { Ok(x) => { print(*x); }, Err(_) => { print(99); } }'
                second_match = first_match.replace('h1.join()', 'h2.join()')
                named = program.replace(first_match, 'let r1 = h1.join();').replace(
                    second_match, 'let r2 = h2.join(); ' + first_match.replace('h1.join()', 'r1')
                    + ' BETWEEN ' + second_match.replace('h2.join()', 'r2'),
                )
                self.assertEqual(self.run_c_oracle(compile_source(
                    named.replace('CHECK', '').replace('BETWEEN', ''),
                )).stdout, '5\n5\n6\n')
                for statement in ('print(*writer);', 'writer.set(9);', 'print(a);'):
                    with self.subTest(after_both_joins=statement), self.assertRaisesRegex(Error, 'emprunt actif'):
                        verify_program(named.replace('CHECK', '').replace('BETWEEN', statement))

    def test_detached_shared_capture_suspends_writer_without_blocking_carrier(self):
        source = """
            struct View { target: &Int }
            async fn read(n: &Int) -> &Int { yield; return n; }
            fn prepare(v: &View) -> <- read {
                let task = read(&*v.target);
                return <- task;
            }
            fn main() {
                let mut ints = pool<Int>(1);
                let mut a = ints.new(5);
                let writer = &mut a;
                let mut views = pool<View>(1);
                let v = views.new(target: &*writer);
                let t = prepare(&v);
                let h = runtime::spawn(-> t);
                print(v);
                drop(-> v);
                RUNNING
                match h.join() {
                    Ok(x) => { RESULT print(*x); },
                    Err(_) => { print(99); }
                }
                writer.set(6);
                print(*writer);
            }
        """
        code = compile_source(source.replace('RUNNING', '').replace('RESULT', ''))
        self.assertEqual(self.run_c_oracle(code).stdout, 'View(5)\n5\n6\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, run, data) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, 'View(5)\n99\n6\n')
        for position in ('RUNNING', 'RESULT'):
            for statement in ('print(*writer);', 'writer.set(9);', 'print(a);'):
                with self.subTest(position=position, statement=statement), self.assertRaisesRegex(Error, 'emprunt actif'):
                    invalid = source.replace(position, statement).replace('RUNNING', '').replace('RESULT', '')
                    verify_program(invalid)

    def test_returned_task_captures_field_value_before_carrier_update(self):
        source = """
            struct View { target: &Int }
            async fn read(n: &Int) -> Int { yield; return *n; }
            fn prepare(v: &mut View, replacement: &Int, change: Int) -> <- read {
                let task = read(&*v.target);
                if change > 0 { v.target = &*replacement; }
                return <- task;
            }
            fn relay(v: &mut View, replacement: &Int, change: Int) -> <- read {
                let task = prepare(v, replacement, change);
                return <- task;
            }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let a = first.new(5);
                let b = second.new(7);
                let mut views = pool<View>(1);
                let mut v = views.new(target: &a);
                let t = relay(&mut v, &b, FLAG);
                print(v);
                drop(-> v);
                CHECK
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
            }
        """
        for flag, expected in ((0, 'View(5)\n5\n'), (1, 'View(7)\n5\n')):
            with self.subTest(flag=flag):
                program = source.replace('FLAG', str(flag))
                valid = program.replace('CHECK', 'drop(-> b);')
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, expected)
                with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                    verify_program(program.replace('CHECK', 'drop(-> a);'))
                with self.assertRaisesRegex(Error, 'reset interdit'):
                    verify_program(program.replace('CHECK', 'first.reset();'), allow_legacy_reset=True)
        after = source.replace('let task = read(&*v.target);\n                if change > 0 { v.target = &*replacement; }',
                               'if change > 0 { v.target = &*replacement; }\n                let task = read(&*v.target);')
        unconditional = source.replace('if change > 0 { v.target = &*replacement; }',
                                       'v.target = &*replacement;').replace('FLAG', '1')
        self.assertEqual(self.run_c_oracle(compile_source(unconditional.replace('CHECK', 'drop(-> b);'))).stdout,
                         'View(7)\n5\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(unconditional.replace('CHECK', 'drop(-> a);'))
        started = unconditional.replace('-> <- read {', '-> <- Execution<read> {').replace(
            'v.target = &*replacement;\n                return <- task;',
            'let h = runtime::spawn(-> task); v.target = &*replacement; return <- h;',
        ).replace('let t = relay(', 'let h = relay(').replace('let h = runtime::spawn(-> t);', '')
        running = started.replace('CHECK', 'drop(-> b);')
        code = compile_source(running)
        self.assertEqual(self.run_c_oracle(code).stdout, 'View(7)\n5\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, run, data) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, 'View(7)\n99\n')
        with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
            verify_program(started.replace('CHECK', 'drop(-> a); let recycled = first.new(42); print(recycled);'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(started.replace('CHECK', 'first.reset();'), allow_legacy_reset=True)
        for flag, expected in ((0, 'View(5)\n5\n'), (1, 'View(7)\n7\n')):
            with self.subTest(flag=flag, after=True):
                program = after.replace('FLAG', str(flag))
                self.assertEqual(self.run_c_oracle(compile_source(program.replace('CHECK', ''))).stdout, expected)
                for target in ('a', 'b'):
                    with self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                        verify_program(program.replace('CHECK', f'drop(-> {target});'))

    def test_sync_join_relay_keeps_entry_field_and_error_fallback(self):
        source = """
            struct View { target: &Int }
            async fn read(n: &Int) -> &Int { yield; return n; }
            fn joined(v: &mut View, replacement: &Int) -> &Int {
                let t = read(&*v.target);
                v.target = &*replacement;
                let h = runtime::spawn(-> t);
                match h.join() {
                    Ok(x) => { return x; },
                    Err(_) => { return &*replacement; }
                }
            }
            fn relay(v: &mut View, replacement: &Int) -> &Int { return joined(v, replacement); }
            fn main() {
                let mut first = pool<Int>(1);
                let mut second = pool<Int>(1);
                let a = first.new(5);
                let b = second.new(7);
                let mut views = pool<View>(1);
                let mut v = views.new(target: &a);
                let r = relay(&mut v, &b);
                print(v);
                drop(-> v);
                CHECK
                print(*r);
                drop(-> a);
                drop(-> b);
            }
        """
        valid = source.replace('CHECK', '')
        contract = verify_program(valid).function_contracts['relay'].result
        self.assertEqual({(o.kind, o.parameter, o.field) for o in contract.reference_targets},
                         {('detached_field_parameter', 0, '.target'), ('parameter', 1, '')})
        code = compile_source(valid)
        self.assertEqual(self.run_c_oracle(code).stdout, 'View(7)\n5\n')
        failed = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                              '#define pthread_create(thread, attr, run, data) EAGAIN', 1)
        self.assertEqual(self.run_c_oracle(failed).stdout, 'View(7)\n7\n')
        for target in ('a', 'b'):
            with self.subTest(target=target), self.assertRaisesRegex(Error, 'emprunt encore utilisé'):
                verify_program(source.replace('CHECK', f'drop(-> {target});'))

    def test_failed_worker_launch_releases_all_transferred_captures(self):
        definitions = """
            async fn worker(a: -> Int, b: -> Int, n: &mut Int) -> Int {
                yield;
                n.set(77);
                return *a + *b;
            }
        """
        setup = """
            let mut first = pool<Int>(1);
            let mut second = pool<Int>(1);
            let a = first.new(5);
            let b = second.new(7);
        """
        body = """
            let task = worker(-> a, -> b, &mut n);
            let h = runtime::spawn(-> task);
            CHECK
            match WAIT { Ok(sum) => { print(sum); }, Err(_) => { print(99); } }
            print(n);
        """
        reuse = """
            let a2 = first.new(15);
            let b2 = second.new(17);
            print(a2);
            print(b2);
        """
        sync = (definitions + 'fn main() {' + setup
                + 'let mut counter = pool<Int>(1); let mut n = counter.new(3);'
                + body.replace('WAIT', 'h.join()') + reuse + '}')
        async_case = (definitions + 'async fn parent(a: -> Int, b: -> Int) { let mut n = 3;'
                      + body.replace('WAIT', 'h.await') + '} fn main() {' + setup
                      + """
                            let task = parent(-> a, -> b);
                            let h = runtime::spawn(-> task);
                            match h.join() { Ok(()) => {}, Err(_) => { print(999); } }
                        """ + reuse + '}')
        for program, failure in ((sync, 'EAGAIN'),
                                 (async_case, '((attr) ? EAGAIN : pthread_create(thread, attr, run, data))')):
            with self.subTest(failure=failure):
                code = compile_source(program.replace('CHECK', ''))
                normal = self.run_c_oracle(code)
                self.assertEqual(normal.stdout, '12\n77\n15\n17\n')
                failed_code = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                    '#define pthread_create(thread, attr, run, data) ' + failure, 1)
                if failure != 'EAGAIN':
                    failed_code = inject_submission_failure(code)
                failed = self.run_c_oracle(failed_code)
                self.assertEqual(failed.stdout, '99\n3\n15\n17\n')
                for run in (normal, failed):
                    self.assertEqual(run.stderr.count('destroy a=5\n'), 1)
                    self.assertEqual(run.stderr.count('destroy b=7\n'), 1)
                with self.assertRaisesRegex(Error, 'emprunt actif'):
                    verify_program(program.replace('CHECK', 'print(n);'))

    def test_transferred_capture_returns_original_slot_on_drop_and_join(self):
        source = """
            async fn work(mut n: -> Int) -> Int { yield; n.set(*n + 1); return *n; }
            fn main() {
                let mut p = pool<Int>(1);
                let task = {
                    let n = new(p) Int(10);
                    let inner = work(-> n);
                    CHECK
                    <- inner
                };
                FINISH
                let reused = new(p) Int(20);
                print(reused);
            }
        """
        clean = source.replace('CHECK', '')
        inactive = self.run_c_oracle(compile_source(clean.replace('FINISH', 'drop(-> task);')))
        self.assertEqual(inactive.stdout, '20\n')
        self.assertIn('destroy n=10\n', inactive.stderr)
        join = """
            let h = runtime::spawn(-> task);
            match h.join() { Ok(x) => { print(x); }, Err(_) => { print(99); } }
        """
        code = compile_source(clean.replace('FINISH', join))
        completed = self.run_c_oracle(code)
        self.assertEqual(completed.stdout, '11\n20\n')
        self.assertIn('destroy n=11\n', completed.stderr)
        failed_start = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                    '#define pthread_create(thread, attr, runner, pointer) EAGAIN')
        failed = self.run_c_oracle(failed_start)
        self.assertEqual(failed.stdout, '99\n20\n')
        self.assertIn('destroy n=10\n', failed.stderr)
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('CHECK', 'print(n);').replace('FINISH', join))
        with self.assertRaisesRegex(Error, 'pool'):
            verify_program(clean.replace(
                'let n = new(p)', 'let mut local = pool<Int>(1); let n = new(local)').replace('FINISH', join))
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(clean.replace('FINISH', 'let h = runtime::spawn(-> task); drop(-> h);'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(clean.replace('FINISH', 'p.reset(); drop(-> task);'), allow_legacy_reset=True)

    def test_task_reborrows_keep_parent_reserved_until_join_or_drop(self):
        source = """
            async fn change(n: &mut Int) { yield; n.set(*n + 3); }
            async fn observe(n: &Int) { yield; print(*n); }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(10);
                let view = &mut n;
                let task = {
                    let inner = CALL;
                    <- inner
                };
                BEFORE
                let h = runtime::spawn(-> task);
                RUNNING
                match h.join() { Ok(()) => {}, Err(_) => { print(99); } }
                print(*view);
                n.set(11);
                print(n);
            }
        """
        for call, expected in (('change(view)', '13\n11\n'), ('observe(view)', '10\n10\n11\n'),
                               ('change(&mut *view)', '13\n11\n')):
            with self.subTest(call=call):
                template = source.replace('CALL', call)
                valid = template.replace('BEFORE', '').replace('RUNNING', '')
                self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, expected)
                for phase in ('BEFORE', 'RUNNING'):
                    for access in ('print(*view);', 'print(n);'):
                        bad = template.replace(phase, access).replace('BEFORE', '').replace('RUNNING', '')
                        with self.assertRaisesRegex(Error, 'incompatible avec un emprunt actif'):
                            verify_program(bad)
        discarded = (source.replace('CALL', 'observe(view)')
                     .replace('BEFORE', '').replace('RUNNING', ''))
        begin = discarded.index('let h =')
        end = discarded.index('print(*view)', begin)
        discarded = discarded[:begin] + 'drop(-> task); ' + discarded[end:]
        self.assertEqual(self.run_c_oracle(compile_source(discarded)).stdout, '10\n11\n')

    def test_execution_handle_moves_keep_exclusive_capture_until_join(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(7); return *n; }
            fn main() {
                let mut p = pool<Int>(1);
                let mut n = new(p) Int(1);
                let h = {
                    let t = edit(&mut n);
                    let inner = runtime::spawn(-> t);
                    <- inner
                };
                let renamed = <- h;
                {
                    renamed ->;
                    <- renamed;
                }
                CHECK
                match renamed.join() { Ok(v) => { print(v); }, Err(_) => { print(99); } }
                print(n);
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '7\n7\n')
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('CHECK', 'let duplicate = h.join();'))
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'print(n);'))
        escaped = source.replace('let mut n = new(p) Int(1);', '').replace(
            'let t = edit(&mut n);', 'let mut n = new(p) Int(1); let t = edit(&mut n);')
        escaped = escaped.replace('print(n);', '').replace('CHECK', '')
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program(escaped)

    def test_async_descending_transfer_requires_a_return_to_reuse_name(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(7); return *n; }
            async fn parent() -> Int {
                let mut n = 1;
                let task = edit(&mut n);
                {
                    task ->;
                    { task ->; yield; <- task; }
                    <- task;
                }
                let h = runtime::spawn(-> task);
                {
                    h ->;
                    yield;
                    <- h;
                }
                let result = match h.await { Ok(x) => { x }, Err(_) => { 99 } };
                return result + n;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '14\n')
        with self.assertRaisesRegex(Error, 'tâche.*déjà consommée'):
            verify_program(source.replace('                    <- task;', '', 1))
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(source.replace('<- h;', ''))
        with self.assertRaisesRegex(Error, 'parent direct'):
            verify_program(source.replace('                    task ->;', '', 1))
        with self.assertRaisesRegex(Error, 'entrée du bloc'):
            verify_program(source.replace('h ->;\n                    yield;', 'yield; h ->;'))

    def test_async_cleanup_order_survives_rename_and_scope_exit(self):
        source = """
            async fn hold(n: -> Int) { print(*n); }
            async fn parent(a: -> Int, b: -> Int) { BODY }
            fn main() {
                let mut p = pool<Int>(2);
                let a = new(p) Int(1);
                let b = new(p) Int(2);
                let t = parent(-> a, -> b);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(()) => {}, Err(_) => { print(999); } }
                let reuse_a = new(p) Int(3);
                let reuse_b = new(p) Int(4);
                print(reuse_a);
                print(reuse_b);
            }
        """
        setup = 'let first = hold(-> a); let second = hold(-> b);'
        rename = 'let renamed = <- first;'
        imported = '{ second ->; first ->; let renamed = <- first; EXIT }'
        cases = {
            'fallthrough': f'{setup} {rename}',
            'return': f'{setup} {rename} return;',
            'block': f'{setup} ' + imported.replace('EXIT', ''),
            'nested return': f'{setup} ' + imported.replace('EXIT', 'return;'),
            'import then local': 'let first = hold(-> a); { first ->; let second = hold(-> b); ' + rename + ' }',
            'break': 'loop { ' + f'{setup} {rename} break;' + ' }',
        }
        for path, body in cases.items():
            with self.subTest(path=path):
                run = self.run_c_oracle(compile_source(source.replace('BODY', body)))
                self.assertEqual(run.stdout, '3\n4\n')
                destroyed = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
                self.assertEqual(destroyed[:2], ['destroy b=2', 'destroy a=1'])

    def test_async_returned_import_gets_a_new_destruction_entry(self):
        source = """
            async fn hold(n: -> Int) { print(*n); }
            async fn parent(flag: Int, a: -> Int, b: -> Int) {
                let first = hold(-> a);
                let second = hold(-> b);
                BODY
            }
            fn main() {
                let mut p = pool<Int>(2);
                let a = new(p) Int(1);
                let b = new(p) Int(2);
                let t = parent(FLAG, -> a, -> b);
                let h = runtime::spawn(-> t);
                match h.join() { Ok(()) => {}, Err(_) => { print(999); } }
                let reused = new(p) Int(3);
                print(reused);
            }
        """
        cases = (
            ('{ first ->; <- first; }', 0, ('a', 'b')),
            ('loop { first ->; <- first; break; }', 0, ('a', 'b')),
            ('if flag == 1 { first ->; <- first; } else { first ->; <- first; }', 0, ('a', 'b')),
            ('if flag == 1 { first ->; <- first; } else { return; }', 0, ('b', 'a')),
        )
        for body, flag, expected in cases:
            with self.subTest(body=body, flag=flag):
                program = source.replace('BODY', body).replace('FLAG', str(flag))
                run = self.run_c_oracle(compile_source(program))
                self.assertEqual(run.stdout, '3\n')
                destroyed = [line.split()[1].split('=')[0] for line in run.stderr.splitlines()
                             if line.startswith('destroy ')]
                self.assertEqual(destroyed, [*expected, 'reused'])
        for body in ('if flag == 1 { first ->; <- first; } else { second ->; <- second; }',
                     'loop { first ->; <- first; continue; }'):
            program = source.replace('BODY', body).replace('FLAG', '1')
            with self.assertRaisesRegex(Error, 'obligations de nettoyage'):
                verify_program(program)

    def test_async_explicit_consumption_cannot_skip_descending_transfer(self):
        source = """
            async fn child(n: Int) { yield; print(n); }
            async fn parent() {
                let inactive = child(1);
                {
                    inactive ->;
                    let alias = <- inactive;
                    drop(-> alias);
                }
                let discarded = child(2);
                { discarded ->; drop(-> discarded); }
                let started = child(3);
                {
                    started ->;
                    let handle = runtime::spawn(-> started);
                    match handle.await { Ok(()) => {}, Err(_) => { print(99); } }
                }
                let worker = child(4);
                let execution = runtime::spawn(-> worker);
                {
                    execution ->;
                    let renamed = <- execution;
                    drop(-> renamed);
                }
                let other = child(5);
                let handle = runtime::spawn(-> other);
                { handle ->; drop(-> handle); }
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(()) => {}, Err(_) => { print(999); } }
            }
        """
        with self.assertRaisesRegex(Error, 'attente requise'):
            verify_program(source)
        source = source.replace('drop(-> renamed);', 'match renamed.await { Ok(()) => {}, Err(_) => {} }').replace(
            '{ handle ->; drop(-> handle); }',
            '{ handle ->; let received = <- handle; match received.await { Ok(()) => {}, Err(_) => {} } }')
        self.assertEqual(sorted(self.run_c_oracle(compile_source(source)).stdout.splitlines()), ['3', '4', '5'])
        for name in ('inactive', 'discarded', 'started', 'execution', 'handle'):
            with self.subTest(name=name), self.assertRaisesRegex(Error, 'scope courant'):
                verify_program(source.replace(f'{name} ->;', '', 1))
        grandchild = source.replace('inactive ->;\n                    let alias = <- inactive;\n                    drop(-> alias);',
                                    'inactive ->; { let alias = <- inactive; drop(-> alias); }')
        with self.assertRaisesRegex(Error, 'scope courant'):
            verify_program(grandchild)

    def test_async_task_and_handle_exports_check_each_scope_boundary(self):
        source = """
            async fn edit(n: &mut Int) -> Int { yield; n.set(7); return *n; }
            async fn parent() -> Int {
                let mut n = 1;
                let outer = {
                    let task = {
                        let leaf = edit(&mut n);
                        yield;
                        <- leaf
                    };
                    let worker = runtime::spawn(-> task);
                    yield;
                    <- worker
                };
                let v = match outer.await { Ok(x) => { x }, Err(_) => { 99 } };
                return n + v;
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(x) => { print(x); }, Err(_) => { print(999); } }
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '14\n')
        block = source.replace('let v = match outer.await', '{ yield; } let v = match outer.await')
        self.assertEqual(self.run_c_oracle(compile_source(block)).stdout, '14\n')

        for insertion in ('let task = {', 'let leaf = edit(&mut n);'):
            with self.subTest(insertion=insertion):
                invalid = source.replace('let mut n = 1;', '').replace('return n + v;', 'return v;')
                invalid = invalid.replace(insertion, 'let mut n = 1; ' + insertion, 1)
                with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
                    verify_program(invalid)
        invalid = source.replace('let v = match outer.await', 'print(n); let v = match outer.await')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(invalid)

    def test_shared_captures_survive_moves_spawn_and_other_joins(self):
        source = """
            async fn read(n: &Int) -> Int { yield; return *n; }
            fn main() {
                let mut numbers = pool<Int>(1);
                let mut n = new(numbers) Int(7);
                let first = {
                    let r = &n;
                    let t = read(r);
                    <- t
                };
                BEFORE
                let a = runtime::spawn(-> first);
                let second = read(&n);
                let b = runtime::spawn(-> second);
                print(n);
                match a.join() {
                    Ok(value) => { print(value); },
                    Err(_) => { print(99); }
                }
                BETWEEN
                match b.join() {
                    Ok(value) => { print(value); },
                    Err(_) => { print(99); }
                }
                n.set(9);
                print(n);
            }
        """
        valid = source.replace('BEFORE', '').replace('BETWEEN', '')
        self.assertEqual(self.run_c_oracle(compile_source(valid)).stdout, '7\n7\n7\n9\n')
        for position in ('BEFORE', 'BETWEEN'):
            for conflict in ('n.set(8);', 'drop(-> n);', 'let w = &mut n; print(w);'):
                with self.subTest(position=position, conflict=conflict):
                    bad = source.replace(position, conflict).replace('BEFORE', '').replace('BETWEEN', '')
                    with self.assertRaisesRegex(Error, 'emprunt'):
                        verify_program(bad)

    def test_shared_capture_cleanup_and_escape(self):
        source = """
            async fn read(n: &Int) { yield; print(*n); }
            fn main() {
                let mut numbers = pool<Int>(1);
                let mut n = new(numbers) Int(7);
                {
                    let t = read(&n);
                    CHECK
                }
                n.set(8);
                print(n);
            }
        """
        for cleanup in ('drop(-> t);', ''):
            self.assertEqual(self.run_c_oracle(compile_source(source.replace('CHECK', cleanup))).stdout, '8\n')
        with self.assertRaisesRegex(Error, 'emprunt actif'):
            verify_program(source.replace('CHECK', 'n.set(9);'))
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(source.replace('CHECK', 'let handle = runtime::spawn(-> t);'))
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(source.replace('CHECK', 'let handle = runtime::spawn(-> t); drop(-> handle);'))
        with self.assertRaisesRegex(Error, 'reset interdit'):
            verify_program(source.replace('CHECK', 'numbers.reset();'), allow_legacy_reset=True)
        with self.assertRaisesRegex(Error, 'cible empruntée non durable'):
            verify_program("""
                async fn read(n: &Int) { yield; print(*n); }
                fn main() {
                    let mut numbers = pool<Int>(1);
                    let escaped = {
                        let n = new(numbers) Int(7);
                        let t = read(&n);
                        <- t
                    };
                    drop(-> escaped);
                }
            """)

    def test_inactive_task_moves_across_scopes_and_keeps_its_slot(self):
        source = """
            async fn work(n: Int) -> Int { yield; return n + 1; }
            fn main() {
                let outer = {
                    let task = work(7);
                    <- task
                };
                {
                    outer ->;
                    <- outer;
                }
                let renamed = <- outer;
                CHECK
                let execution = runtime::spawn(-> renamed);
                match execution.join() {
                    Ok(n) => { print(n); },
                    Err(_) => { print(99); }
                }
            }
        """
        valid = source.replace('CHECK', '')
        self.assertEqual(verify_program(valid).warnings, set())
        run = self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(valid))
        self.assertEqual(run.stdout, '8\n')
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('CHECK', 'drop(-> outer);'))
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(valid.replace('<- outer;', 'drop(-> outer);', 1))

    def test_crust_spawn_and_join_expose_scalar_result_and_start_error(self):
        source = """
            async fn work(n: Int) -> Int { yield; return n + 2; }
            fn main() {
                let task = work(7);
                let execution = runtime::spawn(-> task);
                let result = execution.join();
                CHECK
                match result {
                    Ok(n) => { print(n); },
                    Err(_) => { print(99); }
                }
            }
        """
        code = compile_source(source.replace('CHECK', ''))
        run = self.run_c_oracle(code)
        self.assertEqual(run.stdout, '9\n')
        failed_start = code.replace('#include <pthread.h>', '#include <pthread.h>\n'
                                    '#define pthread_create(thread, attr, runner, pointer) EAGAIN')
        run = self.run_c_oracle(failed_start)
        self.assertEqual(run.stdout, '99\n')
        with self.assertRaisesRegex(Error, 'plus utilisable'):
            verify_program(source.replace('CHECK', 'let again = execution.join();'))
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(source.replace('let result = execution.join();',
                                          'drop(-> execution); let result = execution.join();')
                           .replace('CHECK', ''))
        void = self.run_c_oracle(compile_source("""
            async fn work() { yield; }
            fn main() {
                let t = work();
                let execution = runtime::spawn(-> t);
                match execution.join() {
                    Ok(()) => { print(1); },
                    Err(_) => { print(0); }
                }
            }
        """))
        self.assertEqual(void.stdout, '1\n')

    def test_handles_require_wait_and_legacy_registry_remains_explicit(self):
        source = """
            async fn work(n: Int) { yield; print(n); }
            fn main() {
                let first = work(7);
                let execution = runtime::spawn(-> first);
                drop(-> execution);
                {
                    let second = work(8);
                    let unused = runtime::spawn(-> second);
                }
                print(9);
            }
        """
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(source)
        waited = source.replace('drop(-> execution);',
                                'match execution.join() { Ok(()) => {}, Err(_) => {} }')
        with self.assertRaisesRegex(Error, 'join requis'):
            verify_program(waited)
        code = compile_source(waited.replace('let unused = runtime::spawn(-> second);',
            'let used = runtime::spawn(-> second); match used.join() { Ok(()) => {}, Err(_) => {} }'))
        self.assertEqual(sorted(self.run_c_oracle(code).stdout.splitlines()), ['7', '8', '9'])
        harness = r'''
#include <assert.h>
static _Atomic int entered, proceed;
static int released;
static CrustTaskStep resume(CrustTask *task) {
    (void)task;
    atomic_store(&entered, 1);
    while (!atomic_load(&proceed)) sched_yield();
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *result) {
    (void)task;
    *(int *)result = 42;
}
static void release(CrustTask *task) {
    (void)task;
    released++;
}
static const CrustTaskOps ops = {resume, take, release};
int main(void) {
    CrustTask task;
    CrustAbandonedExecution entries[1];
    CrustAbandonedTasks registry = {.entries = entries, .capacity = 1};
    task_init(&task, &ops);
    {
        CrustExecution execution;
        assert(task_thread_start(&execution, &task) == 0);
        while (!atomic_load(&entered)) sched_yield();
        task_thread_abandon(&registry, &execution);
    }
    task_thread_reap(&registry);
    assert(registry.count == 1 && !released);
    atomic_store(&proceed, 1);
    task_thread_drain(&registry);
    assert(registry.count == 0 && released == 1);
    assert(task_poll(&task) == TASK_CONSUMED);
    return 0;
}
'''
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + harness)

    def test_completed_abandoned_workers_release_slots_before_context_close(self):
        source = """
            async fn work(value: Int) -> Int { yield; return value; }
            async fn parent() -> Int {
                let t = work(7);
                let h = runtime::spawn(-> t);
                match h.await { Ok(n) => { return n; }, Err(_) => { return 99; } }
            }
            fn main() {
                let t = parent();
                let h = runtime::spawn(-> t);
                match h.join() { Ok(n) => { print(n); }, Err(_) => { print(999); } }
            }
        """
        code = '#define CRUST_TASK_POOL_CAPACITY 1\n#define main crust_sync_main\n' + compile_source(source)
        self.run_c_oracle(code + r'''
#undef main
#include <assert.h>

static void wait_for_publication(CrustTask *task) {
    while (!atomic_load_explicit(&task->worker_done, memory_order_acquire)) sched_yield();
}

static void *reap_abandoned(void *unused) {
    (void)unused;
    task_thread_reap(&crust_abandoned_tasks);
    return NULL;
}

int main(void) {
    crust_task_context_init();
    for (int i = 0; i < 32; ++i) {
        CrustTask *task = crust_async_work_create(i);
        if (i % 2 == 0) {
            CrustExecution execution;
            assert(task_thread_start(&execution, task) == 0);
            task_abandon(&execution);
        } else {
            CrustAsyncExecution execution;
            task_async_start(&execution, task);
            assert(!execution.error);
            task_abandon_async(&execution);
        }
        wait_for_publication(task);
        assert(crust_abandoned_tasks.count == 1);
        CrustTask *replacement = crust_async_work_create(i + 1);
        assert(replacement == task && crust_abandoned_tasks.count == 0);
        task_discard(replacement);
    }
    for (int i = 0; i < 32; ++i) {
        CrustExecution execution;
        pthread_t reapers[4];
        CrustTask *task = crust_async_work_create(i);
        assert(task_thread_start(&execution, task) == 0);
        task_abandon(&execution);
        wait_for_publication(task);
        for (int j = 0; j < 4; ++j)
            assert(pthread_create(&reapers[j], NULL, reap_abandoned, NULL) == 0);
        for (int j = 0; j < 4; ++j)
            assert(pthread_join(reapers[j], NULL) == 0);
        assert(crust_abandoned_tasks.count == 0);
        assert(task_pool_is_empty(&crust_task_context.pool_work));
    }
    crust_task_context_close();
    return 0;
}
''')

    def test_default_thread_runner_spawns_and_joins_distinct_workers(self):
        harness = r'''
#include <assert.h>

typedef struct {
    CrustTask task;
    pthread_t worker;
    _Atomic int entered;
    _Atomic int proceed;
    int steps;
    int taken;
    int released;
} State;

static CrustTaskStep resume(CrustTask *task) {
    State *state = (State *)task;
    if (++state->steps == 1) {
        state->worker = pthread_self();
        atomic_store(&state->entered, 1);
        while (!atomic_load(&state->proceed)) sched_yield();
        return TASK_STEP_YIELD;
    }
    assert(pthread_equal(state->worker, pthread_self()));
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *result) {
    State *state = (State *)task;
    assert(state->steps == 2 && !state->released);
    *(int *)result = state->steps;
    state->taken++;
}
static void release(CrustTask *task) {
    State *state = (State *)task;
    assert(state->taken == 1);
    state->released++;
}
static const CrustTaskOps ops = {resume, take, release};

int main(void) {
    State first = {0}, second = {0};
    CrustExecution a, b, duplicate;
    task_init(&first.task, &ops);
    task_init(&second.task, &ops);
    assert(task_thread_start(&a, &first.task) == 0);
    assert(task_thread_start(&b, &second.task) == 0);
    while (!atomic_load(&first.entered) || !atomic_load(&second.entered)) sched_yield();
    assert(!pthread_equal(first.worker, second.worker));
    assert(!pthread_equal(first.worker, pthread_self()));
    assert(!pthread_equal(second.worker, pthread_self()));
    assert(task_thread_start(&duplicate, &first.task) != 0);
    assert(!task_drop_inactive(&first.task));
    atomic_store(&first.proceed, 1);
    atomic_store(&second.proceed, 1);
    int value;
    assert(task_thread_join(&a, &value) && value == 2 && first.released == 1);
    assert(!task_thread_join(&a, &value));
    assert(task_thread_join(&b, &value) && value == 2 && second.released == 1);
    return 0;
}
'''
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + harness)

    def test_scheduler_boundary_preserves_wait_and_cleanup_on_every_path(self):
        harness = r'''
#include <assert.h>

typedef struct {
    CrustTask task;
    int resumes, taken, released;
} State;

static int launches[2], waits, fail_launch;

static int launch(pthread_t *thread, int detached, void *(*run)(void *), void *data) {
    assert(detached == 0 || detached == 1);
    ++launches[detached];
    return fail_launch ? EAGAIN : task_pthread_launch(thread, detached, run, data);
}

static int wait_for_worker(pthread_t thread) {
    ++waits;
    return task_pthread_wait(thread);
}

static CrustTaskStep resume(CrustTask *task) {
    State *state = (State *)task;
    return ++state->resumes == 1 ? TASK_STEP_YIELD : TASK_STEP_RETURN;
}

static void take(CrustTask *task, void *out) {
    State *state = (State *)task;
    assert(state->resumes == 2 && !state->released);
    ++state->taken;
    *(int *)out = 21;
}

static void release(CrustTask *task) {
    State *state = (State *)task;
    assert(!state->released);
    ++state->released;
}

static const CrustTaskOps ops = {resume, take, release};

int main(void) {
    State joined = {0}, abandoned = {0}, polled = {0}, detached = {0}, failed = {0};
    CrustExecution execution;
    CrustAsyncExecution async;
    CrustAbandonedExecution entries[2];
    CrustAbandonedTasks registry = {.entries = entries, .capacity = 2};
    CrustJoinResult result;
    {
        const CrustThreadScheduler scheduler = {.launch = launch, .wait = wait_for_worker};
        task_init(&joined.task, &ops);
        assert(task_thread_start_with(&execution, &joined.task, &scheduler) == 0);
    }
    result = task_join_result(&execution);
    assert(result.status == 0 && result.value == 21 && joined.taken == 1 && joined.released == 1 && waits == 1);
    {
        const CrustThreadScheduler scheduler = {.launch = launch, .wait = wait_for_worker};
        task_init(&abandoned.task, &ops);
        assert(task_thread_start_with(&execution, &abandoned.task, &scheduler) == 0);
        task_thread_abandon(&registry, &execution);
        task_init(&detached.task, &ops);
        task_async_start_with(&async, &detached.task, &scheduler);
        assert(!async.error);
        task_async_abandon(&registry, &async);
        assert(waits == 1 && registry.count == 2);
        task_init(&polled.task, &ops);
        task_async_start_with(&async, &polled.task, &scheduler);
        assert(!async.error);
    }
    while (!task_async_take(&async, &result)) sched_yield();
    assert(result.status == 0 && result.value == 21 && polled.taken == 1 && polled.released == 1);
    while (!atomic_load_explicit(&abandoned.task.worker_done, memory_order_acquire) ||
           !atomic_load_explicit(&detached.task.worker_done, memory_order_acquire)) sched_yield();
    task_thread_reap(&registry);
    assert(registry.count == 1 && !abandoned.released && detached.released == 1 && waits == 1);
    task_thread_drain(&registry);
    assert(registry.count == 0 && abandoned.released == 1 && detached.released == 1 && waits == 2);
    assert(abandoned.resumes == 2 && detached.resumes == 2 && !abandoned.taken && !detached.taken);
    {
        const CrustThreadScheduler scheduler = {.launch = launch, .wait = wait_for_worker};
        fail_launch = 1;
        task_init(&failed.task, &ops);
        task_async_start_with(&async, &failed.task, &scheduler);
    }
    assert(task_async_take(&async, &result));
    assert(result.status == 5 && failed.released == 1 && !failed.resumes && !failed.taken);
    assert(launches[0] == 2 && launches[1] == 3 && waits == 2);
    return 0;
}
'''
        self.run_c_oracle(TASK_RUNTIME + TASK_THREAD_RUNTIME + TASK_ASYNC_THREAD_RUNTIME + harness)

    def test_failed_thread_creation_releases_inactive_task(self):
        shim = r'''
#include <pthread.h>
#define pthread_create(thread, attr, runner, pointer) EAGAIN
'''
        harness = r'''
#include <assert.h>
static int released;
static CrustTaskStep resume(CrustTask *task) {
    (void)task;
    abort();
}
static void take(CrustTask *task, void *result) {
    (void)task;
    (void)result;
    abort();
}
static void release(CrustTask *task) {
    (void)task;
    released++;
}
static const CrustTaskOps ops = {resume, take, release};
int main(void) {
    CrustTask task;
    CrustExecution execution;
    task_init(&task, &ops);
    assert(task_thread_start(&execution, &task) == EAGAIN);
    assert(released == 1 && task_poll(&task) == TASK_CONSUMED);
    assert(!task_thread_join(&execution, NULL));
    return 0;
}
'''
        self.run_c_oracle(TASK_RUNTIME + shim + TASK_THREAD_RUNTIME + harness)

    def test_generated_await_preserves_pending_child_and_argument_temporaries(self):
        source = """
            async fn parent() -> Int {
                let stored = step(1);
                let moved = <- stored;
                let first = moved.await;
                let answer = add(first + 10, step(2).await).await;
                quiet().await;
                return answer;
            }
            async fn step(n: Int) -> Int { print(n); yield; return n + 1; }
            async fn add(a: Int, b: Int) -> Int { return a + b; }
            async fn quiet() { yield; }
            fn main() {}
        """
        code = compile_source(source)
        run = self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n#define main crust_sync_main\n' + code + r'''
#undef main
#include <assert.h>
int main(void) {
    crust_task_context_init();
    CrustTask *task = crust_async_parent_create();
    assert(task_poll(task) == TASK_SUSPENDED);
    assert(task_poll(task) == TASK_SUSPENDED);
    assert(task_poll(task) == TASK_SUSPENDED);
    assert(task_poll(task) == TASK_COMPLETE);
    int value;
    assert(task_take(task, &value) && value == 15);
    crust_task_context_close();
    return 0;
}
''')
        self.assertEqual(run.stdout, '1\n2\n')
        with self.assertRaisesRegex(Error, 'déjà consommée'):
            verify_program(source.replace('quiet().await;', 'let again = stored.await;'))

    def test_source_creates_and_cleans_inactive_tasks_without_running_body(self):
        source = """
            async fn work(a: Int, b: Int) { print(a + b); yield; }
            fn trace(n: Int) -> Int { print(n); return n; }
            fn main() {
                let explicit = work(trace(1), trace(2));
                drop(-> explicit);
                { let automatic = work(trace(3), trace(4)); }
                let again = work(5, 6);
                drop(-> again);
                print(7);
            }
        """
        compiler = verify_program(source)
        warnings = '\n'.join(compiler.warnings)
        self.assertIn("'automatic'", warnings)
        self.assertNotIn("'explicit'", warnings)
        self.assertNotIn("'again'", warnings)
        run = self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n' + compile_source(source))
        self.assertEqual(run.stdout, '1\n2\n3\n4\n7\n')
        for statement, diagnostic in (
            ('let copy = explicit;', 'ne peut pas être copiée'),
            ('drop(-> explicit);', 'plus utilisable'),
        ):
            with self.subTest(statement=statement), self.assertRaisesRegex(Error, diagnostic):
                before = 'drop(-> explicit);'
                replacement = f'{before} {statement}' if statement == before else f'{statement} {before}'
                verify_program(source.replace(before, replacement))

    def test_generated_states_preserve_values_across_yield_and_use_typed_slots(self):
        code = compile_source("""
            async fn first(input: Int) -> Int {
                let mut total = input + 1;
                yield;
                total = total + 2;
                yield;
                return total;
            }
            async fn second(input: Int) -> Int { return input; }
            fn main() {}
        """)
        self.assertIn('    crust_task_context_init();', code)
        self.assertIn('    crust_task_context_close();', code)
        self.run_c_oracle('#define CRUST_TASK_POOL_CAPACITY 1\n#define main crust_sync_main\n' + code + r'''
#undef main
#include <assert.h>
int main(void) {
    crust_task_context_init();
    assert(sizeof(crust_task_context.states_first[0]) > sizeof(crust_task_context.states_second[0]));
    CrustTask *first = crust_async_first_create(7);
    CrustTask *second = crust_async_second_create(4);
    assert(first == &crust_task_context.states_first[0].task);
    assert(second == &crust_task_context.states_second[0].task);
    assert(atomic_load(&first->state) == TASK_INACTIVE && crust_task_context.states_first[0].pc == 0);
    assert(task_poll(first) == TASK_SUSPENDED && crust_task_context.states_first[0].value_1 == 8);
    assert(task_poll(second) == TASK_COMPLETE);
    int result;
    assert(task_take(second, &result) && result == 4);
    assert(task_poll(first) == TASK_SUSPENDED && crust_task_context.states_first[0].value_1 == 10);
    assert(task_poll(first) == TASK_COMPLETE);
    assert(task_take(first, &result) && result == 10);
    CrustTask *reused = crust_async_first_create(99);
    assert(reused == first && task_drop_inactive(reused));
    crust_task_context_close();
    return 0;
}
''')

    def test_async_scalar_body_verifies_types_and_mutability(self):
        for source, diagnostic in (
            ('async fn task() -> Int { yield; }', 'retour Int requis'),
            ('async fn task(x: Int) { yield; x = 1; }', 'receveur mutable'),
            ('async fn task(x: &Int) { x.set(1); }', 'set exige un emprunt mutable'),
            ('async fn task(x: &Int) { print(x); }', 'déréférencement explicite'),
            ('async fn task() -> Int { yield; return missing; }', 'variable inconnue'),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(Error, diagnostic):
                verify_program(source)

    def test_generated_context_rejects_closing_with_live_slot(self):
        code = compile_source('async fn pending() { yield; } fn main() {}')
        self.run_c_oracle('#define main crust_sync_main\n' + code + r'''
#undef main
int main(void) {
    crust_task_context_init();
    crust_async_pending_create();
    crust_task_context_close();
    return 0;
}
''', expected_error='live async task at context close')

    def test_pool_reuses_slots_only_after_concurrent_tasks_release_them(self):
        harness = r'''
#include <assert.h>
#include <pthread.h>
#include <sched.h>

typedef struct {
    CrustTask task;
    CrustTaskSlot slot;
    int value;
} Frame;

static CrustTaskStep resume(CrustTask *task) {
    ((Frame *)task)->value++;
    return TASK_STEP_RETURN;
}
static void take(CrustTask *task, void *result) {
    *(int *)result = ((Frame *)task)->value;
}
static void release(CrustTask *task) {
    assert(task_pool_release(((Frame *)task)->slot));
}
static const CrustTaskOps ops = {resume, take, release};

typedef struct {
    CrustTaskPool *pool;
    CrustTaskSlot slot;
    _Atomic int ready;
    _Atomic int release;
    int result;
} Worker;

static void *run_task(void *pointer) {
    Worker *worker = pointer;
    CrustTaskSlot slot = task_pool_acquire(worker->pool);
    Frame *frame = task_slot_address(slot);
    assert(frame);
    task_init(&frame->task, &ops);
    frame->slot = slot;
    frame->value = 7;
    worker->slot = slot;
    atomic_store(&worker->ready, 1);
    while (!atomic_load(&worker->release)) sched_yield();
    assert(task_poll(&frame->task) == TASK_COMPLETE);
    assert(task_take(&frame->task, &worker->result));
    return NULL;
}

int main(void) {
    CrustTaskPool pool;
    Frame storage[2];
    _Atomic size_t generations[2];
    task_pool_init(&pool, &storage, sizeof(Frame), 2, generations);
    assert(task_pool_is_empty(&pool));
    Worker workers[2] = {{.pool = &pool}, {.pool = &pool}};
    pthread_t threads[2];
    for (size_t i = 0; i < 2; ++i)
        assert(pthread_create(&threads[i], NULL, run_task, &workers[i]) == 0);
    for (size_t i = 0; i < 2; ++i)
        while (!atomic_load(&workers[i].ready)) sched_yield();
    assert(!task_pool_is_empty(&pool));
    assert(!task_pool_acquire(&pool).pool);
    assert(task_slot_address(workers[0].slot) != task_slot_address(workers[1].slot));
    CrustTaskSlot old = workers[0].slot;
    void *address = task_slot_address(old);
    atomic_store(&workers[0].release, 1);
    assert(pthread_join(threads[0], NULL) == 0 && workers[0].result == 8);
    CrustTaskSlot reused = task_pool_acquire(&pool);
    Frame *frame = task_slot_address(reused);
    assert(frame == address);
    assert(!task_slot_address(old) && !task_pool_release(old));
    assert(task_slot_address(reused) == address);
    task_init(&frame->task, &ops);
    frame->slot = reused;
    assert(task_drop_inactive(&frame->task));
    atomic_store(&workers[1].release, 1);
    assert(pthread_join(threads[1], NULL) == 0 && workers[1].result == 8);
    assert(task_pool_is_empty(&pool));
    return 0;
}
'''
        self.run_c_oracle(TASK_RUNTIME + TASK_POOL_RUNTIME + harness)

    def test_task_resumes_once_and_releases_only_after_result_is_taken(self):
        harness = r'''
#include <assert.h>
#include <pthread.h>
#include <sched.h>

typedef struct {
    CrustTask task;
    int pc;
    int capture;
    int result;
    const int *address;
    _Atomic int entered;
    _Atomic int proceed;
    int released;
    int result_taken;
} State;

static CrustTaskStep resume(CrustTask *task) {
    State *state = (State *)task;
    switch (state->pc++) {
    case 0:
        state->address = &state->capture;
        atomic_store(&state->entered, 1);
        while (!atomic_load(&state->proceed)) sched_yield();
        return TASK_STEP_YIELD;
    case 1:
        assert(state->address == &state->capture);
        assert(!state->released);
        state->result = state->capture + 2;
        return TASK_STEP_RETURN;
    default:
        assert(0);
        return TASK_STEP_RETURN;
    }
}

static void take(CrustTask *task, void *result) {
    State *state = (State *)task;
    assert(!state->released);
    *(int *)result = state->result;
    state->result_taken++;
}

static void release(CrustTask *task) {
    State *state = (State *)task;
    assert(!state->released);
    assert(state->pc == 0 || state->result_taken == 1);
    state->released++;
}

static const CrustTaskOps ops = {resume, take, release};

static void *poll_on_thread(void *pointer) {
    assert(task_poll(pointer) == TASK_SUSPENDED);
    return NULL;
}

int main(void) {
    State inactive = {.capture = 4};
    task_init(&inactive.task, &ops);
    assert(inactive.pc == 0);
    assert(task_drop_inactive(&inactive.task));
    assert(inactive.released == 1 && inactive.pc == 0);
    assert(!task_drop_inactive(&inactive.task));
    assert(task_poll(&inactive.task) == TASK_CONSUMED);

    State running = {.capture = 7};
    task_init(&running.task, &ops);
    pthread_t worker;
    assert(pthread_create(&worker, NULL, poll_on_thread, &running.task) == 0);
    while (!atomic_load(&running.entered)) sched_yield();
    assert(task_poll(&running.task) == TASK_RUNNING);
    assert(!task_drop_inactive(&running.task));
    atomic_store(&running.proceed, 1);
    assert(pthread_join(worker, NULL) == 0);
    int value = 0;
    assert(!task_take(&running.task, &value));
    assert(!task_drop_inactive(&running.task));
    assert(task_poll(&running.task) == TASK_COMPLETE);
    assert(!running.released && !running.result_taken);
    assert(task_poll(&running.task) == TASK_COMPLETE);
    assert(task_take(&running.task, &value));
    assert(value == 9 && running.result_taken == 1 && running.released == 1);
    assert(!task_take(&running.task, &value));
    assert(task_poll(&running.task) == TASK_CONSUMED);
    return 0;
}
'''
        self.run_c_oracle(TASK_RUNTIME + harness)

    def run_c_oracle(self, code, expected_error=None):
        cc = shutil.which('clang') or shutil.which('cc')
        if not cc:
            self.skipTest('C compiler unavailable')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'task.c'
            binary = Path(directory) / 'task'
            source.write_text(code)
            build = subprocess.run(
                [cc, '-std=c11', os.environ.get('CRUST_TEST_OPT', '-O2'), '-pthread', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                 '-fsanitize=undefined', '-fno-sanitize-recover=all', str(source), '-o', str(binary)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            if expected_error is None:
                self.assertEqual(run.returncode, 0, run.stderr)
            else:
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_error, run.stderr)
            return run
