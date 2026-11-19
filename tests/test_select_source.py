"""Source Select: retained captures, one await, scopes and generated cleanup."""
import unittest

from crust import Error, compile_source, verify_program
import test_async_runtime


class SelectSourceTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def run_source(self, source):
        try:
            verify_program(source)
            code = compile_source(source)
        except Error as error:
            self.fail(f'programme attendu valide refusé : {error}')
        return self.run_c_oracle(code)

    def refused(self, source, diagnostic):
        for checker in (verify_program, compile_source):
            with self.subTest(checker=checker.__name__), self.assertRaisesRegex(Error, diagnostic):
                checker(source)

    @staticmethod
    def program(body, helpers=''):
        return helpers + 'async fn work()->Int{'+body+'''}
        fn main(){let h=runtime::spawn(->work());match h.join(){Ok(r)=>{print(r);},Err(_)=>{print(99);}}}'''

    def test_first_ready_and_resumed_first_branch(self):
        for pause, expected in (('', '9\n'), ('yield;', '7\n')):
            source = self.program('''let mut s=runtime::select(->left(),->right());
                let r=s.await;drop(->s);return r;''',
                'async fn left()->Int{yield;return 7;}async fn right()->Int{'+pause+'return 9;}')
            self.assertEqual(self.run_source(source).stdout, expected)

    def test_single_await_mutability_and_explicit_move(self):
        helpers = 'async fn leaf()->Int{yield;return 7;}'
        body = 'let mut s=runtime::select(->leaf());let r=s.await;drop(->s);return r;'
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'7\n')
        for invalid, diagnostic in (
            (body.replace('let mut s','let s'),'let mut'),
            (body.replace('drop(->s);','let other=s.await;print(other);drop(->s);'),'déjà attendu'),
            (body.replace('let r=s.await;drop(->s);','drop(->s);let r=s.await;'),'déjà attendu'),
        ):
            self.refused(self.program(invalid,helpers),diagnostic)
        moved = 'let s=runtime::select(->leaf());let mut other=<-s;let r=other.await;drop(->other);return r;'
        self.assertEqual(self.run_source(self.program(moved,helpers)).stdout,'7\n')
        self.refused(self.program(moved.replace('let r=other.await;','let wrong=s.await;print(wrong);let r=other.await;'),helpers),'déjà attendu')

    def test_shared_loser_holds_capture_until_drop_or_scope_end(self):
        helpers = 'async fn read(n:&Int)->Int{yield;return *n;}async fn ready()->Int{return 9;}'
        before = 'let mut p=pool<Int>(1);let mut n=p.new(7);'
        selection = 'let mut s=runtime::select(->read(&n),->ready());let r=s.await;print(r);'
        source = self.program(before+selection+'BEFORE drop(->s);n=21;return *n;',helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'9\n21\n')
        for operation in ('n=30;','drop(->n);'):
            self.refused(source.replace('BEFORE',operation),'emprunt actif')
        automatic = self.program(before+'{'+selection+'}n=21;return *n;',helpers)
        self.assertEqual(self.run_source(automatic).stdout,'9\n21\n')

    def test_mutable_capture_conflicts_at_construction_and_after_await(self):
        helpers = 'async fn edit(n:&mut Int)->Int{yield;n.set(11);return *n;}async fn ready()->Int{return 9;}'
        body = '''let mut p=pool<Int>(1);let mut n=p.new(7);
            let mut s=runtime::select(->edit(&mut n),->ready());let r=s.await;print(r);
            BEFORE drop(->s);return *n;'''
        self.assertEqual(self.run_source(self.program(body.replace('BEFORE',''),helpers)).stdout,'9\n7\n')
        self.refused(self.program(body.replace('BEFORE','print(*n);'),helpers),'emprunt actif')
        duplicate = body.replace('->ready()', '->edit(&mut n)').replace('BEFORE','')
        self.refused(self.program(duplicate,helpers),'emprunt actif')

    def test_owned_loser_cleanup_and_loop_slot_reuse(self):
        helpers = '''#(directive, async_pool_sizes={left:1,right:1,work:1})
        async fn left(n:->Int)->Int{yield;return *n;}
        async fn right()->Int{return 9;}'''
        source = self.program('''let mut i=0;while i<8{
            let mut p=pool<Int>(1);let n=p.new(i);
            let mut s=runtime::select(->left(->n),->right());let r=s.await;print(r);
            drop(->s);let next=p.new(20);print(*next);i=i+1;}
            return i;''',helpers)
        run = self.run_source(source)
        self.assertEqual(run.stdout, '9\n20\n'*8+'8\n')
        for i in range(8):
            self.assertEqual(run.stderr.count('destroy n='+str(i)+'\n'),1)

    def test_inactive_selection_drop_does_not_run_bodies(self):
        helpers = 'async fn leaf(n:->Int)->Int{print(99);return *n;}'
        source = self.program('''let mut p=pool<Int>(1);let n=p.new(7);
            let s=runtime::select(->leaf(->n));drop(->s);let next=p.new(8);return *next;''',helpers)
        run = self.run_source(source)
        self.assertEqual(run.stdout,'8\n')
        self.assertEqual(run.stderr.count('destroy n=7'),1)

    def test_suspended_constructor_cleans_earlier_transferred_branch(self):
        helpers = '''async fn leaf(n:->Int)->Int{yield;return *n;}
        async fn delayed()->Int{yield;return 2;}
        async fn second(n:Int)->Int{return n;}
        async fn building()->Int{
            let mut p=pool<Int>(1);let n=p.new(7);
            let mut s=runtime::select(->leaf(->n),->second(delayed().await));
            let r=s.await;drop(->s);return r;}
        async fn ready()->Int{return 9;}'''
        source = self.program('''let mut s=runtime::select(->building(),->ready());
            let r=s.await;drop(->s);return r;''',helpers)
        run = self.run_source(source)
        self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('destroy n=7'),1)

    def test_nested_suspended_selection_uses_generated_cleanup(self):
        helpers = '''async fn leaf(n:->Int)->Int{yield;yield;return *n;}
        async fn nested()->Int{let mut p=pool<Int>(1);let n=p.new(7);
            let mut s=runtime::select(->leaf(->n));let r=s.await;drop(->s);return r;}
        async fn ready()->Int{return 9;}'''
        run = self.run_source(self.program('''let mut s=runtime::select(->nested(),->ready());
            let r=s.await;drop(->s);return r;''',helpers))
        self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('destroy n=7'),1)

    def test_partial_field_write_survives_selection_and_reaches_caller(self):
        source = '''struct View{data:&Int}
        async fn left(v:&mut View,n:&Int)->Int{
            let old=v.data;v.data=&*n;yield;v.data=old;return 7;}
        async fn ready()->Int{return 9;}
        async fn choose(v:&mut View,n:&Int)->Int{
            let mut s=runtime::select(->left(v,n),->ready());let r=s.await;drop(->s);return r;}
        fn main(){let mut p=pool<Int>(2);let a=p.new(1);let b=p.new(2);
            let mut v=View{data:&a};let h=runtime::spawn(->choose(&mut v,&b));
            match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}
            BEFORE print(*v.data);}'''
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'9\n2\n')
        self.refused(source.replace('BEFORE','drop(->b);'),'emprunt|référenc')

    def test_transfers_through_blocks_conditionals_and_loop_results(self):
        helpers = '''async fn slow(n:&Int)->Int{yield;return *n;}
        async fn first()->Int{return 11;}async fn second()->Int{return 22;}'''
        for constructor, expected in (
            ('{let s=runtime::select(->slow(&n),->first());<-s}', 11),
            ('if FLAG {let s=runtime::select(->slow(&n),->first());<-s}'
             'else {let s=runtime::select(->second());<-s}', None),
            ('loop {if FLAG {let s=runtime::select(->slow(&n),->first());break <-s;}'
             'let s=runtime::select(->second());break <-s;}', None),
        ):
            for flag in ('true','false'):
                with self.subTest(constructor=constructor, flag=flag):
                    body = '''let mut p=pool<Int>(1);let mut n=p.new(7);
                    let mut chosen=CONSTRUCTOR;BEFORE let r=chosen.await;
                    drop(->chosen);n=30;print(*n);return r;'''.replace('CONSTRUCTOR',constructor.replace('FLAG',flag))
                    run=self.run_source(self.program(body.replace('BEFORE',''),helpers))
                    self.assertEqual(run.stdout,'30\n'+str(expected or (11 if flag=='true' else 22))+'\n')
                    self.refused(self.program(body.replace('BEFORE','drop(->n);'),helpers),'emprunt actif')

    def test_transferred_selection_cannot_outlive_capture_or_owned_pool(self):
        for mode, argument in (('&Int','&n'),('->Int','->n')):
            helpers='async fn read(n:'+mode+')->Int{yield;return *n;}'
            source=self.program('''let mut s={let mut p=pool<Int>(1);let n=p.new(7);
                let chosen=runtime::select(->read(ARG));<-chosen};
                let r=s.await;drop(->s);return r;'''.replace('ARG',argument),helpers)
            self.refused(source,'non durable|survit à son pool')

    def test_transferred_awaited_selection_stays_consumed_and_keeps_loser(self):
        helpers='async fn read(n:&Int)->Int{yield;return *n;}async fn ready()->Int{return 9;}'
        source=self.program('''let mut p=pool<Int>(1);let mut n=p.new(7);
            let mut outside={let mut s=runtime::select(->read(&n),->ready());
                let r=s.await;print(r);<-s};
            BEFORE drop(->outside);n=30;return *n;''',helpers)
        self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,'9\n30\n')
        self.refused(source.replace('BEFORE','let again=outside.await;print(again);'),'déjà attendu')
        self.refused(source.replace('BEFORE','drop(->n);'),'emprunt actif')
        # A branch merge has its own result record. It must retain the spent
        # state too; testing a single exported block would miss this path.
        arm='''{let mut s=runtime::select(->read(&n),->ready());
            let r=s.await;print(r);<-s}'''
        for flag in ('true','false'):
            conditional=self.program('''let mut p=pool<Int>(1);let mut n=p.new(7);
                let mut outside=if FLAG ARM else ARM;
                BEFORE drop(->outside);n=30;return *n;'''.replace('FLAG',flag).replace('ARM',arm),helpers)
            self.assertEqual(self.run_source(conditional.replace('BEFORE','')).stdout,'9\n30\n')
            self.refused(conditional.replace('BEFORE','let again=outside.await;print(again);'),'déjà attendu')

    def test_selection_mutability_is_lexical(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'validation/select-immutable-shadow-counterexample.crb').read_text()
        self.refused(source,'let mut')
        self.assertEqual(self.run_source(source.replace('}let s=', '}let mut s=')).stdout,'7\n')

    def test_returned_borrows_survive_selection_drop_but_keep_targets(self):
        for mode in ('&Int','&mut Int'):
            helpers='async fn read(n:'+mode+')->'+mode+'{yield;return n;}'
            capture=mode.replace('Int','').strip()
            body='''let mut p=pool<Int>(2);let mut a=p.new(1);let mut b=p.new(2);
                let mut s=runtime::select(->read(CAP a),->read(CAP b));
                let mut r=s.await;USE drop(->s);BEFORE return *r;'''.replace('CAP',capture).replace(
                    'USE','r.set(20);' if mode=='&mut Int' else 'print(*r);')
            with self.subTest(mode=mode):
                self.assertEqual(self.run_source(self.program(body.replace('BEFORE',''),helpers)).stdout,
                                 '20\n' if mode=='&mut Int' else '1\n1\n')
                for target in ('a','b'):
                    self.refused(self.program(body.replace('BEFORE',f'drop(->{target});'),helpers),'emprunt actif')

    def test_early_exits_and_explicit_child_round_trip(self):
        helpers='async fn read(n:->Int)->Int{yield;return *n;}async fn ready()->Int{return 9;}'
        body='''let mut p=pool<Int>(1);let mut i=0;while i<4{
            let n=p.new(i);let mut s=runtime::select(->read(->n),->ready());
            let r=s.await;print(r);i=i+1;if i<3 {continue;}break;}
            let next=p.new(30);return *next;'''
        run=self.run_source(self.program(body,helpers))
        self.assertEqual(run.stdout,'9\n'*3+'30\n')
        for i in range(3):self.assertEqual(run.stderr.count(f'destroy n={i}\n'),1)
        body='''let mut p=pool<Int>(1);let n=p.new(7);
            let mut s=runtime::select(->read(->n),->ready());
            {s ->;yield;<-s;}let r=s.await;drop(->s);return r;'''
        self.assertEqual(self.run_source(self.program(body,helpers)).stdout,'9\n')

    def test_move_preserves_destruction_order_and_addresses(self):
        helpers='async fn read(n:->Int)->Int{yield;return *n;}'
        body='''let mut p=pool<Int>(2);let first=p.new(1);let last=p.new(2);
            let s=runtime::select(->read(->first));
            let later=runtime::select(->read(->last));
            let renamed=<-s;return 0;'''
        run=self.run_source(self.program(body,helpers))
        self.assertLess(run.stderr.index('destroy last=2'),run.stderr.index('destroy first=1'))

    def test_scalar_and_array_results(self):
        for typ, value, use, expected in (
            ('Bool','true','if r {print(1);}else {print(2);}','1\n0\n'),
            ('u8','65','print(r as Int);','65\n0\n'),
            ('&str','"été"','print(r);','été\n0\n'),
            ('[Int;2]','<-[3,4]','print(r[1]);','4\n0\n'),
        ):
            helpers='async fn read()->'+typ+'{yield;return '+value+';}'
            body='let mut s=runtime::select(->read());let r=s.await;'+use+'drop(->s);return 0;'
            with self.subTest(typ=typ):
                self.assertEqual(self.run_source(self.program(body,helpers)).stdout,expected)
        char_source='''async fn read(c:char)->char{yield;return c;}
            async fn work(c:char)->Int{let mut s=runtime::select(->read(c));
                let r=s.await;drop(->s);return r.utf8_len();}
            fn main(){match "é".char_at(0){Ok(c)=>{
                let h=runtime::spawn(->work(c));match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}
            },Err(_)=>{}}}'''
        self.assertEqual(self.run_source(char_source).stdout,'2\n')

    def test_computed_branches_keep_all_capture_alternatives(self):
        helpers='async fn read(n:&Int)->Int{yield;return *n;}async fn ready()->Int{return 9;}'
        for constructor in (
            'if FLAG {let t=read(&a);<-t}else {let t=read(&b);<-t}',
            'loop {if FLAG {let t=read(&a);break <-t;}let t=read(&b);break <-t;}',
        ):
            for flag in ('true','false'):
                body='''let mut p=pool<Int>(2);let a=p.new(1);let b=p.new(2);
                    let mut s=runtime::select(->(CONSTRUCTOR),->ready());
                    let r=s.await;BEFORE drop(->s);return r;'''.replace('CONSTRUCTOR',constructor.replace('FLAG',flag))
                with self.subTest(constructor=constructor,flag=flag):
                    self.assertEqual(self.run_source(self.program(body.replace('BEFORE',''),helpers)).stdout,'9\n')
                    for target in ('a','b'):
                        self.refused(self.program(body.replace('BEFORE',f'drop(->{target});'),helpers),'emprunt actif')

    def test_owned_result_and_loser_reuse_independent_pools(self):
        helpers='async fn make(p:&mut Pool<Int>,n:Int)-><-Int{let v=p.new(n);yield;return <-v;}'
        body='''let mut p=pool<Int>(1);let mut q=pool<Int>(1);
            let mut s=runtime::select(->make(&mut p,7),->make(&mut q,8));
            let v=s.await;print(*v);drop(->s);drop(->v);
            let a=p.new(17);let b=q.new(18);print(*a);return *b;'''
        run=self.run_source(self.program(body,helpers))
        self.assertEqual(run.stdout,'7\n17\n18\n')
        for n in (7,8):self.assertEqual(run.stderr.count(f'destroy v={n}\n'),1)

    def test_independent_ordered_poll_and_cleanup_model(self):
        # The model is just remaining voluntary pauses, with no compiler or
        # runtime state. All YIELD branches become eligible on the next round.
        from itertools import product
        for pauses in product(range(3),repeat=2):
            remaining=list(pauses)
            while True:
                winner=None
                for i in range(2):
                    if remaining[i]==0:
                        winner=i
                        break
                    remaining[i]-=1
                if winner is not None:break
            helpers=''.join('async fn branch'+str(i)+'(n:->Int)->Int{'+
                'yield;'*count+'return *n;}' for i,count in enumerate(pauses))
            source=self.program('''let mut p=pool<Int>(2);let a=p.new(10);let b=p.new(20);
                let mut s=runtime::select(->branch0(->a),->branch1(->b));
                let r=s.await;drop(->s);let next=p.new(30);print(*next);return r;''',helpers)
            with self.subTest(pauses=pauses):
                run=self.run_source(source)
                self.assertEqual(run.stdout,f'30\n{10 if winner==0 else 20}\n')
                self.assertEqual(run.stderr.count('destroy a=10\n'),1)
                self.assertEqual(run.stderr.count('destroy b=20\n'),1)

    def test_never_polled_branch_needs_no_suspension_contract(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'validation/open-select-source-unpolled-contract.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'1\n7\n')
        # The unreachable body's effects are irrelevant; the captured loan is
        # still retained by the inactive loser until Select is destroyed.
        self.refused(source.replace('drop(->s);','print(*v.data);drop(->s);'),'emprunt actif')

    def test_selection_alternatives_keep_distinct_poll_orders(self):
        for control in ('if FLAG {FIRST}else {SECOND}',
                        'loop {if FLAG {FIRST_BREAK}SECOND_BREAK}'):
            for flag in ('true','false'):
                first='let s=runtime::select(->ready());<-s'
                second='let s=runtime::select(->write(v,&*n),->ready());<-s'
                choice=control.replace('FLAG',flag).replace('FIRST_BREAK',first.replace('<-s','break <-s;')).replace(
                    'SECOND_BREAK',second.replace('<-s','break <-s;')).replace('FIRST',first).replace('SECOND',second)
                source='''struct View{data:&Int}
                    async fn ready()->Int{return 9;}
                    async fn write(v:&mut View,n:&Int)->Int{v.data=&*n;yield;return 7;}
                    async fn work(v:&mut View,n:&mut Int)->Int{
                        let mut s=CHOICE;let r=s.await;drop(->s);
                        let saved=v.data;yield;print(*saved);return r;}
                    fn main(){let mut p=pool<Int>(2);let a=p.new(1);let mut b=p.new(2);
                        let mut v=View{data:&a};let h=runtime::spawn(->work(&mut v,&mut b));
                        match h.join(){Ok(r)=>{print(r);},Err(_)=>{}}
                        BEFORE print(*v.data);}'''.replace('CHOICE',choice)
                with self.subTest(control=control,flag=flag):
                    expected='1' if flag=='true' else '2'
                    self.assertEqual(self.run_source(source.replace('BEFORE','')).stdout,f'{expected}\n9\n{expected}\n')
                    self.refused(source.replace('BEFORE','drop(->b);'),'emprunt|référenc')
                    self.refused(source.replace('BEFORE','').replace('drop(->s);','drop(->s);n.set(30);'),'emprunt actif')

    def test_certain_winner_releases_only_its_finished_captures(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'validation/open-select-single-winner-loan.crb').read_text()
        self.assertEqual(self.run_source(source).stdout,'7\n')
        helpers='async fn ready(n:&Int)->Int{return *n;}async fn slow(n:&Int)->Int{yield;return *n;}'
        body='''let mut p=pool<Int>(2);let mut a=p.new(1);let mut b=p.new(2);
            let mut s=runtime::select(->ready(&a),->slow(&b));let r=s.await;
            a=11;BEFORE drop(->s);b=22;print(*a);print(*b);return r;'''
        self.assertEqual(self.run_source(self.program(body.replace('BEFORE',''),helpers)).stdout,'11\n22\n1\n')
        self.refused(self.program(body.replace('BEFORE','b=12;'),helpers),'emprunt actif')
        # The finished winner's capture ends, but its returned borrow does not.
        borrowed=self.program('''let mut p=pool<Int>(1);let mut a=p.new(1);
            let mut s=runtime::select(->view(&a));let r=s.await;
            BEFORE print(*r);a=20;drop(->s);return *a;''',
            'async fn view(n:&Int)->&Int{yield;return n;}')
        self.assertEqual(self.run_source(borrowed.replace('BEFORE','')).stdout,'1\n20\n')
        self.refused(borrowed.replace('BEFORE','a=12;'),'emprunt actif')

    def test_outer_selection_waited_once_on_each_path(self):
        helpers='async fn ready(n:&Int)->Int{return *n;}async fn slow(n:&Int)->Int{yield;return *n;}'
        for flag in ('true','false'):
            body='''let mut p=pool<Int>(2);let mut a=p.new(1);let mut b=p.new(2);
                let mut s=runtime::select(->ready(&a),->slow(&b));
                if FLAG {let r=s.await;print(r);}else {let r=s.await;print(r);}
                a=11;BEFORE drop(->s);b=22;return *a;'''.replace('FLAG',flag)
            self.assertEqual(self.run_source(self.program(body.replace('BEFORE',''),helpers)).stdout,'1\n11\n')
            self.refused(self.program(body.replace('BEFORE','b=12;'),helpers),'emprunt actif')
            self.refused(self.program(body.replace('BEFORE','let r=s.await;print(r);'),helpers),'déjà attendu')


if __name__ == '__main__':
    unittest.main()
