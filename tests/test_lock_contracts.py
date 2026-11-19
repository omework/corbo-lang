"""MT10 caller contracts for results that retain an exclusive lock."""
import unittest

from crust import Error, compile_source, verify_program
import test_async_runtime


DECLARATIONS = '''
struct Objet { n:i32 }
struct Ticket { n:i32 }
impl Objet {
    #(lock: on=self, through_result=true)
    fn ouvrir(&self)->Ticket { Ticket { n:self.n } }

    #(lock: on=self)
    fn lire(&self)->i32 { self.n }
}
fn lire_indirect(m:&Objet)->i32 { m.lire() }
fn ouvrir_indirect(m:&Objet)->Ticket { m.ouvrir() }
fn comparer(x:&Objet, y:&Objet)->i32 {
    let ticket=x.ouvrir();
    let n=y.lire();
    drop(ticket);
    n
}
'''


class LockContractTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def test_vector_pop_option_preserves_lock_until_payload_drop(self):
        source = """
            struct Objet { n:i32 }
            struct Ticket { n:i32 }
            impl Objet {
                #(lock: on=self, through_result=true)
                fn ouvrir(&self, p:&mut Pool<Ticket>)->A<Ticket> { p.new(n:self.n) }
                #(lock: on=self)
                fn lire(&self)->i32 { self.n }
            }
            fn main() {
                let m=Objet { n:42 };
                let mut p=pool<Ticket>(1);
                let mut vp=pool<Vector<A<Ticket>>>(1);
                let mut v=vp.new();
                let t=m.ouvrir(&mut p);
                v.push(t);
                let r=v.pop();
                match r { Some(x)=>{ print(x.n); drop(x); }, None=>{} }
                print(m.lire());
            }
        """
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '42\n42\n')
        with self.assertRaisesRegex(Error, 'lock|verrou'):
            verify_program(source.replace('print(x.n); drop(x);', 'print(m.lire()); drop(x);'))

    def test_owned_result_field_retains_the_lock_through_a_function(self):
        declarations = '''
            struct Objet { n: i32 }
            struct Ticket { n: i32 }
            struct Pack { item: A<Ticket> }
            impl Objet {
                #(lock: on=self, through_result=true)
                fn ouvrir(&self, p: &mut Pool<Ticket>) -> A<Ticket> { p.new(n:self.n) }
                #(lock: on=self)
                fn lire(&self) -> i32 { self.n }
            }
        '''
        source = declarations + '''
            fn wrap(t: A<Ticket>) -> Pack { Pack { item: t } }
            fn main() {
                let m = Objet { n:42 };
                let mut p = pool<Ticket>(1);
                let t = m.ouvrir(&mut p);
                let w = wrap(t);
                drop(w);
                print(m.lire());
            }
        '''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '42\n')
        with self.assertRaisesRegex(Error, 'verrou déjà maintenu'):
            verify_program(source.replace('drop(w);\n                print(m.lire());',
                                          'print(m.lire()); drop(w);'))
        with self.assertRaisesRegex(Error, 'verrou déjà maintenu'):
            verify_program(source.replace('fn wrap(t: A<Ticket>) -> Pack { Pack { item: t } }', '''
                fn wrap(t: A<Ticket>, m: &Objet) -> Pack {
                    let w = Pack { item: t };
                    print(m.lire());
                    w
                }
            ''').replace('wrap(t);', 'wrap(t, &m);'))

    @staticmethod
    def program(body):
        return DECLARATIONS + 'fn main(){let m=Objet{n:4};let autre=Objet{n:7};' + body + 'drop(autre);}'

    def test_result_move_drop_scope_and_distinct_receivers(self):
        source = self.program('''
            let a=m.ouvrir();
            let b=a;
            print(b.n);
            print(lire_indirect(&autre));
            drop(b);
            {let c=m.ouvrir();print(c.n);}
            print(m.lire());
            print(m.lire());
            print(comparer(&m,&autre));
            let relay=ouvrir_indirect(&m);
            drop(relay);
            let bloc={let ticket=m.ouvrir();ticket};
            drop(bloc);
        ''')
        verify_program(source)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '4\n7\n4\n4\n4\n7\n')

    def test_refusal_with_live_result_even_after_last_use(self):
        for body in (
            'let a=m.ouvrir();print(a.n);let b=m.ouvrir();print(b.n);',
            'let a=m.ouvrir();let b=a;print(b.n);print(m.lire());',
            'let a=m.ouvrir();print(a.n);print(lire_indirect(&m));',
            'let a=ouvrir_indirect(&m);print(a.n);print(m.lire());',
            'let a={let ticket=m.ouvrir();ticket};print(a.n);print(m.lire());',
            'let a=m.ouvrir();print(a.n);let alias=&m;print(alias.lire());',
            'print(comparer(&m,&m));',
        ):
            for entry in (verify_program, compile_source):
                with self.subTest(body=body, entry=entry.__name__):
                    with self.assertRaisesRegex(Error, 'verrou déjà maintenu'):
                        entry(self.program(body))

    def test_conditional_drop_and_receiver_lifetime(self):
        for body, diagnostic in (
            ('let a=m.ouvrir();print(a.n);if m.n==4 {move a;drop(a);}print(m.lire());', 'verrou déjà maintenu'),
            ('let a=m.ouvrir();print(a.n);drop(m);', 'maintient le verrou'),
            ('let a=m.ouvrir();let b=copy(a);print(b.n);', 'copie interdite'),
        ):
            for entry in (verify_program, compile_source):
                with self.subTest(body=body, entry=entry.__name__):
                    with self.assertRaisesRegex(Error, diagnostic):
                        entry(self.program(body))

    def test_invalid_annotation_and_async_result_limit(self):
        for source, diagnostic in (
            (DECLARATIONS.replace('through_result=true', 'through_result=false') + 'fn main(){}',
             'attendu .true.'),
            (DECLARATIONS.replace('#(lock: on=self)\n', '#(lock: on=self, through_result=true)\n')
             + 'fn main(){}', 'résultat propriétaire'),
            (DECLARATIONS + 'async fn work(m:&Objet){let a=m.ouvrir();drop(a);}fn main(){}',
             'résultat qui maintient un verrou|méthode.*async|appel.*async'),
        ):
            for entry in (verify_program, compile_source):
                with self.subTest(source=source, entry=entry.__name__):
                    with self.assertRaisesRegex(Error, diagnostic):
                        entry(source)

    def test_arguments_preserve_or_end_the_lock(self):
        functions = '''
fn relayer(t:Ticket)->Ticket { t }
fn inspecter(t:&Ticket)->i32 { t.n }
fn liberer(t:Ticket,m:&Objet)->i32 { drop(t);m.lire() }
'''
        valid = self.program('''
            let a=m.ouvrir();
            print(inspecter(&a));
            let b=relayer(a);
            print(liberer(b,&m));
        ''')
        verify_program(functions + valid)
        self.assertEqual(self.run_c_oracle(compile_source(functions + valid)).stdout, '4\n4\n')
        invalid = (
            (functions + valid.replace('print(liberer(b,&m));', 'print(m.lire());drop(b);'),
             'verrou déjà maintenu'),
            (functions.replace('drop(t);m.lire()', 'let n=m.lire();drop(t);n') + valid,
             'verrou déjà maintenu'),
            (functions.replace('t.n }', 'let duplicate=copy(t);let n=duplicate.n;drop(duplicate);n }') + valid,
             'copie interdite'),
        )
        for source, diagnostic in invalid:
            for entry in (verify_program, compile_source):
                with self.subTest(diagnostic=diagnostic, entry=entry.__name__):
                    with self.assertRaisesRegex(Error, diagnostic):
                        entry(source)

    def test_async_capture_retains_until_cleanup_and_restitutes_on_join(self):
        from scheduler_faults import inject_submission_failure

        functions = '''async fn relayer(t:Ticket)->Ticket{yield;t}
            async fn consommer(t:Ticket){yield;print(t.n);drop(t);}
        '''
        valid = self.program('''
            let a=m.ouvrir();
            let inactive=consommer(a);
            drop(inactive);
            print(m.lire());
            let b=m.ouvrir();
            let job=relayer(b);
            let h=runtime::spawn(job);
            match h.join(){
                Ok(c)=>{print(c.n);drop(c);},
                Err(runtime::Error::LaunchFailed)=>{print(9);},
            }
            print(m.lire());
        ''')
        verify_program(functions + valid)
        code = compile_source(functions + valid)
        self.assertEqual(self.run_c_oracle(code).stdout, '4\n4\n4\n')
        failed = inject_submission_failure(code, asynchronous=False, at=1)
        self.assertEqual(self.run_c_oracle(failed).stdout, '4\n9\n4\n')
        for program in (
            valid.replace('drop(inactive);', 'print(m.lire());drop(inactive);'),
            valid.replace('match h.join(){', 'print(m.lire());match h.join(){'),
            valid.replace('print(c.n);drop(c);', 'print(c.n);print(m.lire());drop(c);'),
        ):
            for entry in (verify_program, compile_source):
                with self.subTest(entry=entry.__name__):
                    with self.assertRaisesRegex(Error, 'verrou déjà maintenu'):
                        entry(functions + program)

    def test_wait_checks_lock_conflicts_with_the_task(self):
        functions = '''async fn lire_async(m:&Objet)->i32{yield;m.lire()}'''
        valid = self.program('''
            let a=m.ouvrir();
            let h=runtime::spawn(lire_async(&m));
            drop(a);
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}
        ''')
        self.assertEqual(self.run_c_oracle(compile_source(functions + valid)).stdout, '4\n')
        invalid = valid.replace('drop(a);', '').replace('drop(autre);', 'drop(a);drop(autre);')
        for entry in (verify_program, compile_source):
            with self.subTest(entry=entry.__name__):
                with self.assertRaisesRegex(Error, 'verrou déjà maintenu'):
                    entry(functions + invalid)

    def test_borrowed_capture_and_nested_await(self):
        functions = '''
            async fn inspecter(t:&Ticket)->i32{yield;t.n}
            async fn inner(t:Ticket)->Ticket{yield;t}
            async fn outer(t:Ticket)->Ticket{let r=inner(t).await;r}
            async fn copier(t:Ticket){let b=copy(t);drop(t);drop(b);}
        '''
        body = '''
            let a=m.ouvrir();
            let read=runtime::spawn(inspecter(&a));
            match read.join(){Ok(n)=>{print(n);},Err(_)=>{}}
            let h=runtime::spawn(outer(a));
            match h.join(){Ok(c)=>{print(c.n);drop(c);},Err(_)=>{}}
            print(m.lire());
        '''
        source = functions + self.program(body)
        verify_program(source)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '4\n4\n4\n')
        for body, diagnostic in (
            (body.replace('print(c.n);drop(c);', 'print(c.n);print(m.lire());drop(c);'),
             'verrou déjà maintenu'),
            ('let a=m.ouvrir();let job=copier(a);drop(job);', 'copie interdite'),
        ):
            for entry in (verify_program, compile_source):
                with self.subTest(entry=entry.__name__, diagnostic=diagnostic):
                    with self.assertRaisesRegex(Error, diagnostic):
                        entry(functions + self.program(body))
