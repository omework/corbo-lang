"""SL1 prerequisites: generated destruction at actual suspension points.

These probes exclusively own an unlaunched root and revoke any Select routes
before destruction. They do not add a public cancellation operation.
"""
import unittest

from async_runtime import TASK_SELECT_RUNTIME
from crust import Error, compile_source, verify_program
import scheduler_faults
import test_async_runtime


class SuspendedCleanupTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def native(self, source, body, *, failure=False):
        code = compile_source(source)
        anchor = 'static void source_close(Source *source) {'
        self.assertEqual(code.count(anchor), 1)
        code = code.replace(anchor, anchor + '\n    ++observed_closes;')
        if failure:
            code = scheduler_faults.inject_submission_failure(code)
        code = 'static int observed_closes;\n#define main original_main\n' + code
        code += '\n#undef main\n' + TASK_SELECT_RUNTIME + '\n#include <assert.h>\n'
        return self.run_c_oracle(code + '''
int main(void) {
    crust_task_context_init();
''' + body + '''
    crust_task_context_close();
    return 0;
}
''')

    def test_locals_replacements_and_conditional_suspension_points(self):
        source = '''async fn work(n:-> Int, pick:Int)->Int {
            print(*n);drop(->n);
            let mut p=pool<Int>(2);let mut a=p.new(10);print(*a);yield;
            if pick==0 {let b=p.new(20);print(*b);yield;}
            else {let c=p.new(30);print(*c);yield;}
            a=<-p.new(40);yield;return *a;}
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);
                let h=runtime::spawn(->work(->n,0));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        for pick in (0, 1):
            for polls in (1, 2, 3):
                with self.subTest(pick=pick, polls=polls):
                    run = self.native(source, f'''
    Source incoming=source_pool(1); Cell *n=cell_new(&incoming,7,"incoming");
    CrustTask *task=crust_async_work_create(n,{pick});
    for (int i=0;i<{polls};++i) assert(task_poll(task)==TASK_SUSPENDED);
    assert(task_owned_discardable(task));
    int before=observed_closes;
    assert(task_drop_owned(task)); assert(observed_closes==before+1);
    assert(!task_drop_owned(task));
    Cell *reused=cell_new(&incoming,8,"reused");assert(reused==n);
    cell_drop(reused);source_close(&incoming);
''')
                    branch = 'b=20' if pick == 0 else 'c=30'
                    expected = ['incoming=7']
                    if polls >= 2:
                        expected.append(branch)
                    expected += ['a=10']
                    if polls == 3:
                        # Anonymous construction keeps its diagnostic label;
                        # the values/order identify the old and new allocations.
                        expected.append('async allocation=40')
                    expected.append('reused=8')
                    destroyed = [line.removeprefix('destroy ') for line in run.stderr.splitlines()
                                 if line.startswith('destroy ')]
                    self.assertEqual(destroyed, expected)

    def test_direct_await_tree_cleans_child_before_parent_storage(self):
        source = '''async fn leaf(n:&Int)->Int {
                let mut q=pool<Int>(1);let m=q.new(2);yield;return *m+*n;}
            async fn relay(n:&Int)->Int {return leaf(n).await;}
            async fn work()->Int {let mut p=pool<Int>(1);let n=p.new(1);
                return relay(&n).await;}
            fn main(){let h=runtime::spawn(->work());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        run = self.native(source, '''
    for(int i=0;i<12;++i){
        CrustTask *task=crust_async_work_create();
        assert(task_poll(task)==TASK_SUSPENDED && task_owned_discardable(task));
        int before=observed_closes;
        assert(task_drop_owned(task)); assert(observed_closes==before+2);
    }
''')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy m=2', 'destroy n=1'] * 12)

    def test_prepared_moves_during_later_argument_await(self):
        for asynchronous in (False, True):
            source = (('async ' if asynchronous else '') +
                'fn consume(n:-> Int,value:Int)->Int{'+('yield;' if asynchronous else '')+
                'return *n+value;}'+'''
                async fn number()->Int {yield;return 5;}
                async fn work()->Int {let mut p=pool<Int>(1);let n=p.new(7);
                    return consume(->n,number().await)'''+('.await' if asynchronous else '')+''';}
                fn main(){let h=runtime::spawn(->work());
                    match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}''')
            for polls in range(1, 3 if asynchronous else 2):
                with self.subTest(asynchronous=asynchronous, polls=polls):
                    run = self.native(source, f'''
    CrustTask *task=crust_async_work_create();
    for(int i=0;i<{polls};++i) assert(task_poll(task)==TASK_SUSPENDED);
    assert(task_owned_discardable(task));
    assert(task_drop_owned(task));assert(observed_closes==1);
''')
                    self.assertEqual(run.stderr.count('destroy n=7'), 1)

    def test_inactive_children_transfers_and_resumed_loop(self):
        source = '''async fn child(n:-> Int)->Int{yield;return *n;}
            async fn work(n:-> Int)->Int {
                { n ->;yield;<- n; }
                let renamed=<-n;
                let mut i=0;
                while i<3 {let mut p=pool<Int>(1);let a=p.new(i+10);
                    let inactive=child(->a);yield;drop(->inactive);i=i+1;}
                yield;return *renamed;}
            fn main(){let mut p=pool<Int>(1);let n=p.new(7);
                let h=runtime::spawn(->work(->n));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        for polls in range(1, 6):
            with self.subTest(polls=polls):
                run = self.native(source, f'''
    Source pool=source_pool(1);Cell *n=cell_new(&pool,7,"incoming");
    CrustTask *task=crust_async_work_create(n);
    for(int i=0;i<{polls};++i) assert(task_poll(task)==TASK_SUSPENDED);
    assert(task_drop_owned(task));
    assert(observed_closes=={min(polls-1,3)});
    Cell *reused=cell_new(&pool,8,"reused");assert(reused==n);
    cell_drop(reused);source_close(&pool);
''')
                expected = [f'destroy a={i+10}' for i in range(min(polls-1, 3))]
                expected += ['destroy incoming=7', 'destroy reused=8']
                self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')], expected)

    def test_result_allocation_cleaned_after_success_or_launch_failure(self):
        source = '''async fn give(n:-> Int)-><- Int{yield;return <-n;}
            async fn work()->Int{let mut p=pool<Int>(1);let n=p.new(7);
                let h=runtime::spawn(->give(->n));let result=h.await;yield;
                match result{Ok(answer)=>{return *answer;},Err(_)=>{return 0;}}}
            fn main(){let h=runtime::spawn(->work());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        for failure in (False, True):
            with self.subTest(failure=failure):
                run = self.native(source, '''
    CrustTask *task=crust_async_work_create();
    do {assert(task_poll(task)==TASK_SUSPENDED);sched_yield();}
    while(!task_owned_discardable(task));
    assert(task_drop_owned(task));assert(observed_closes==1);
''', failure=failure)
                self.assertEqual(run.stderr.count('destroy n=7'), 1)

    def test_outstanding_handle_preflight_preserves_normal_execution(self):
        source = '''async fn read(n:&Int)->Int{yield;return *n;}
            async fn work()->Int{let mut p=pool<Int>(1);let n=p.new(7);
                let h=runtime::spawn(->read(&n));yield;
                match h.await{Ok(answer)=>{return answer;},Err(_)=>{return 0;}}}
            async fn relay()->Int{return work().await;}
            fn main(){let h=runtime::spawn(->relay());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        self.native(source, '''
    CrustTask *task=crust_async_relay_create();
    assert(task_poll(task)==TASK_SUSPENDED);
    assert(!task_owned_discardable(task));
    assert(!task_drop_owned(task));assert(observed_closes==0);
    while(task_poll(task)==TASK_SUSPENDED) sched_yield();
    int result=-1;assert(task_take(task,&result)&&result==7);
    assert(observed_closes==1);
''')

    def test_select_uses_generated_suspended_destructor(self):
        source = '''async fn left()->Int{
                let mut p=pool<Int>(1);let n=p.new(7);yield;return *n;}
            async fn right()->Int{return 9;}
            fn main(){let a=runtime::spawn(->left());let b=runtime::spawn(->right());
                match a.join(){Ok(n)=>{print(n);},Err(_)=>{}}
                match b.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        run = self.native(source, '''
    CrustTask *left=crust_async_left_create(),*right=crust_async_right_create();
    CrustSelectBranch branches[]={{left,left->discard_suspended},{right,right->discard_suspended}};
    CrustSelect selection;task_select_init(&selection,branches,2);
    CrustTask parent;task_init(&parent,&crust_async_left_ops);
    assert(task_select_poll(&selection,&parent)==TASK_STEP_RETURN);
    int out=-1;assert(task_select_take(&selection,&out)&&out==9);
    assert(observed_closes==0);assert(task_owned_discardable(left));
    task_select_drop(&selection);assert(observed_closes==1);
''')
        self.assertEqual(run.stderr.count('destroy n=7'), 1)

    def test_replacement_wait_keeps_old_allocation_until_new_value_exists(self):
        source = '''async fn read(n:&Int)->Int{yield;return *n+1;}
            async fn work()->Int{let mut p=pool<Int>(2);let mut a=p.new(10);
                a=<-p.new(read(&a).await);yield;return *a;}
            fn main(){let h=runtime::spawn(->work());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        for polls, expected in ((1, [10]), (2, [10, 11])):
            with self.subTest(polls=polls):
                run = self.native(source, f'''
    CrustTask *task=crust_async_work_create();
    for(int i=0;i<{polls};++i)assert(task_poll(task)==TASK_SUSPENDED);
    assert(task_drop_owned(task));assert(observed_closes==1);
''')
                self.assertEqual([int(line.rsplit('=', 1)[1]) for line in run.stderr.splitlines()
                                  if line.startswith('destroy ')], expected)
        valid = source.replace('a=<-p.new(read(&a).await);',
                               'a=<-make(&mut p,read(&a).await);')
        valid = '''fn make(memory:&mut Pool<Int>,n:Int)-><- Int {
            let result=memory.new(n);return <-result;}
        ''' + valid
        run = self.run_c_oracle(compile_source(valid))
        self.assertEqual(run.stdout, '11\n')
        for invalid in (source.replace('let mut a=', 'let a='),
                        source.replace('a=<-p.new(read(&a).await);yield;return *a;',
                                       'let view=&a;a=<-p.new(11);yield;print(*a);return *view;')):
            with self.subTest(invalid=invalid):
                for check in (verify_program, compile_source):
                    with self.assertRaisesRegex(Error, 'mutable|emprunt'):
                        check(invalid)

    def test_independent_scope_and_replacement_model(self):
        # Model lexical storage as a list of live values. At each suspension,
        # append the reverse live list to the destruction history. No compiler
        # state, generated member, pc or cleanup callback enters this oracle.
        rows, expected = [], []
        for turns in (0, 1, 3):
            for choice in (0, 1):
                history, live, points = [], [100], []
                for i in range(turns):
                    live.append(i + 10)
                    points.append((history + list(reversed(live)), i + 2))
                    history.append(live.pop())
                    live.append(i + (20 if choice == 0 else 30))
                    points.append((history + list(reversed(live)), i + 2))
                    history.append(live.pop())
                points.append((history + list(reversed(live)), turns + 1))
                for polls, (destroyed, closes) in enumerate(points, 1):
                    rows.append(f'{{{turns},{choice},{polls},{closes}}}')
                    expected.extend(destroyed)
        self.assertEqual(len(rows), 22)
        source = '''async fn work(turns:Int,choice:Int)->Int{
            let mut outer=pool<Int>(1);let keep=outer.new(100);let mut i=0;
            while i<turns {let mut inner=pool<Int>(2);let mut current=inner.new(i+10);
                yield;print(*current);if choice==0{current=<-inner.new(i+20);}
                else{current=<-inner.new(i+30);}yield;print(*current);i=i+1;}
            yield;return *keep;}
            fn main(){let h=runtime::spawn(->work(3,1));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        body = '''
    const int rows[][4]={ROWS};
    for(size_t i=0;i<sizeof(rows)/sizeof(*rows);++i){
        const int *r=rows[i];int before=observed_closes;
        CrustTask *task=crust_async_work_create(r[0],r[1]);
        for(int j=0;j<r[2];++j)assert(task_poll(task)==TASK_SUSPENDED);
        assert(task_drop_owned(task));assert(observed_closes-before==r[3]);
    }
'''.replace('ROWS', ','.join(rows))
        run = self.native(source, body)
        self.assertEqual([int(line.rsplit('=', 1)[1]) for line in run.stderr.splitlines()
                          if line.startswith('destroy ')], expected)

    def test_growing_collections_and_borrowed_views_at_suspension(self):
        for typ, edit, view, read in (
                ('String', 'value.push_str("été");', 'let view=&value[..];', 'print(view);'),
                ('Vector<Int>', 'value.push(7);', 'let view=&value[0];', 'print(*view);'),
                ('Vector<u8>', 'value.push(255);', 'let view=&value[0];', 'print(*view as Int);')):
            source = f'''async fn left()->Int{{let mut p=pool<{typ}>(1);
                #(directive,stack_region_max_size=1M){{let mut value=p.new();
                    {edit}{view}yield;{read}return 7;}}}}
                async fn right()->Int{{return 9;}}
                fn main(){{let a=runtime::spawn(->left());let b=runtime::spawn(->right());
                    match a.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}
                    match b.join(){{Ok(n)=>{{print(n);}},Err(_)=>{{}}}}}}'''
            with self.subTest(typ=typ):
                run = self.native(source, '''
    for(int i=0;i<6;++i){
        CrustTask *left=crust_async_left_create(),*right=crust_async_right_create();
        CrustSelectBranch branches[]={{left,left->discard_suspended},{right,right->discard_suspended}};
        CrustSelect selection;task_select_init(&selection,branches,2);
        CrustTask parent;task_init(&parent,&crust_async_left_ops);
        assert(task_select_poll(&selection,&parent)==TASK_STEP_RETURN);
        int out=-1;assert(task_select_take(&selection,&out)&&out==9);
        int before=observed_closes;
        assert(task_owned_discardable(left));task_select_drop(&selection);
        assert(observed_closes>before);
    }
''')
                self.assertEqual(run.stdout, '')
                self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()), 6)


if __name__ == '__main__':
    unittest.main()
