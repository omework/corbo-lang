"""Functional coverage of the integrated core entry points."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from crust import __file__ as prototype_file
from crust import Error, compile_source, verify_program
import test_async_runtime as harness


class CoreIntegrationTests(unittest.TestCase):
    run_c_oracle = harness.AsyncRuntimeTests.run_c_oracle

    def refuses(self, source, diagnostic, **options):
        for check in (verify_program, compile_source):
            with self.subTest(entry=check.__name__), self.assertRaisesRegex(Error, diagnostic):
                check(source, **options)

    def test_pool_content_borrow_annotations_and_numeric_context(self):
        source = '''fn main() {
            let mut pool_i32 = pool<i32>(1);
            let mut nombre: A<i32> = pool_i32.new(10);
            let lecture: &i32 = nombre.vref();
            print(*lecture);
            let mut ecriture = nombre.mut_vref();
            *ecriture = 20;
            print(*ecriture);
            drop(nombre);
        }'''
        for program in (source, source.replace('let mut ecriture =', 'let mut ecriture: &mut i32 =')):
            with self.subTest(program=program):
                verify_program(program)
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '10\n20\n')
        for annotation in ('&mut i32', '&i64', '&A<i32>'):
            self.refuses(source.replace('lecture: &i32', f'lecture: {annotation}'), 'annotation de let')
        self.refuses(source.replace('print(*lecture);', 'drop(nombre); print(*lecture);'), 'emprunt encore utilisé')
        self.refuses(source.replace('*ecriture = 20;', '*ecriture = 2147483648;'), 'hors des bornes de i32')

    def test_async_annotation_on_existing_numeric_borrow(self):
        source = '''async fn work()->u64 {
            let mut nombre: u64 = 10;
            let mut vue: &mut u64 = &mut nombre;
            yield;
            *vue = 20;
            nombre
        }
        fn main() {
            let h = runtime::spawn(work());
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{},}
        }'''
        verify_program(source)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '20\n')
        self.refuses(source.replace('vue: &mut u64', 'vue: &u64'), 'annotation incompatible')

    def test_async_numeric_borrow_results_through_all_wait_forms(self):
        declaration = 'async fn give(x:&mut u64)->&mut u64{yield;x}'
        main = '''fn main(){let h=runtime::spawn(relay());
            match h.join(){Ok(x)=>{print(x);},Err(_)=>{},}}'''
        for source in (
            declaration + '''async fn relay()->u64{let mut n:u64=6;
                let mut r=give(&mut n).await;*r+=1;n}''' + main,
            declaration + '''async fn relay()->u64{let mut n:u64=6;
                let h=runtime::spawn(give(&mut n));
                match h.await{Ok(r)=>{*r+=1;},Err(_)=>{},}n}''' + main,
            declaration + '''fn main(){let mut numbers=pool<u64>(1);let mut n=numbers.new(6);
                let h=runtime::spawn(give(&mut n));
                match h.join(){Ok(r)=>{*r+=1;},Err(_)=>{},}print(*n);}''',
            declaration + '''fn take(h:runtime::Handle<&mut u64>)->&mut u64{
                return match h.join(){Ok(r)=>{r},Err(_)=>{loop{}},};
            }
            fn main(){let mut n:u64=6;let h=runtime::spawn(give(&mut n));
                let mut r=take(h);*r+=1;print(n);}''',
        ):
            with self.subTest(source=source):
                verify_program(source)
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')
                blocked = source.replace('*r+=1;', ('print(*n);' if 'pool<u64>' in source else 'print(n);') + '*r+=1;')
                self.refuses(blocked, 'emprunt actif|réserv|incompatible')
        self.refuses('async fn local()->&u64{let n:u64=6;&n}fn main(){}', 'durable|provenance')

    def test_async_shared_float_field_result(self):
        source = '''struct Point{b:u8,x:f64}
            async fn field(p:&Point)->&f64{yield;&p.x}
            fn main(){let mut p=Point{b:1,x:2.5};let h=runtime::spawn(field(&p));
                match h.join(){Ok(r)=>{print(*r);},Err(_)=>{},}
                p.x=3.5;print(p.x);}'''
        verify_program(source)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '2.5\n3.5\n')
        self.refuses(source.replace('print(*r);', 'p.x=3.5;print(*r);'), 'emprunt actif|réserv|incompatible')

    def run_with_c(self, source, *units):
        verify_program(source)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            program = root / 'main.crb'
            program.write_text(source)
            command = [sys.executable, str(Path(prototype_file).resolve()),
                       'run', str(program)]
            for index, unit in enumerate(units):
                path = root / f'unit{index}.c'
                path.write_text(unit)
                command.extend(('--c-source', str(path)))
            return subprocess.run(command, capture_output=True, text=True, timeout=30)

    def test_c_build_links_scalar_signatures(self):
        source = '''extern "C" fn low(n:u64)->u64;
            extern "C" fn odd(n:u8)->bool;
            extern "C" fn measure()->f32;
            extern "C" fn sink(n:i32);
            fn main(){
                unsafe {sink(7);}
                let n=unsafe{low(300)};
                if unsafe{odd(3)} {print(n);}
                print(unsafe{measure()});
            }'''
        a = '''#include <stdint.h>
            #include <stdio.h>
            uint64_t low(uint64_t n){return n & UINT64_C(255);}
            void sink(int32_t n){printf("%d\\n",n);}'''
        b = '''#include <stdint.h>
            _Bool odd(uint8_t n){return n & 1;}
            float measure(void){return 1.5f;}'''
        run = self.run_with_c(source, a, b)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '7\n44\n1.5\n')

    def test_c_boundary_is_lexical_and_checks_ordinary_crust(self):
        header = 'extern "C" fn identite(n:i32)->i32;'
        self.refuses(header+'fn main(){print(identite(7));}', 'unsafe')
        self.refuses(header+'fn f()->i32{identite(7)}fn main(){print(unsafe{f()});}', 'unsafe')
        self.refuses(header+'fn main(){print(unsafe{identite(7.)});}', 'famille')
        self.refuses('extern "C" fn read(n:&i32);fn main(){}', 'scalaire')
        self.refuses(header+'''fn main(){let mut p=pool<i32>(1);let n=p.new(7);
            unsafe {move n;print(identite(*n));drop(n);print(*n);}
        }''', 'plus utilisable|déplac')

    def test_c_float_ingress_and_missing_symbol(self):
        source = 'extern "C" fn measure()->f64;fn main(){print(unsafe{measure()});}'
        for special in ('INFINITY', '-INFINITY', 'NAN'):
            with self.subTest(special=special):
                run = self.run_with_c(source, f'#include <math.h>\ndouble measure(void){{return {special};}}')
                self.assertNotEqual(run.returncode, 0)
                self.assertIn('résultat flottant C non fini', run.stderr)
        run = self.run_with_c(source, 'double measure(void){return -0.0;}')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '-0\n')
        missing = self.run_with_c(source, 'int autre(void){return 0;}')
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('measure', missing.stderr)

    def test_c_scalar_call_after_suspension(self):
        source = '''extern "C" fn foreign(n:i64)->i64;
            async fn task()->i64{yield;unsafe {foreign(3)}}
            fn main(){let h=runtime::spawn(task());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{},}}'''
        run = self.run_with_c(source, '#include <stdint.h>\nint64_t foreign(int64_t n){return n+4;}')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, '7\n')

    def test_modern_thread_headers_copy_scalars_and_move_allocations(self):
        prefix = 'fn main(){let n:i64=7;'
        suffix = 'print(n);match h.join(){Ok(v)=>{print(v);},Err(_)=>{},}}'
        for header in ('{move n;n+1}', 'move {n+1}'):
            with self.subTest(header=header):
                program = prefix + 'let h=runtime::thread(' + header + ');' + suffix
                verify_program(program)
                self.assertEqual(self.run_c_oracle(compile_source(program)).stdout, '7\n8\n')
        source = '''fn main(){let mut p=pool<i32>(1);let n=p.new(7);
            let h=runtime::thread(move {*n});
            match h.join(){Ok(v)=>{print(v);},Err(_)=>{},}
        }'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')
        self.refuses(source.replace('match h.join()', 'print(*n);match h.join()'), 'plus utilisable|déplac')

    def test_numeric_fields_and_indirect_compound_assignment(self):
        source = '''struct Point{b:u8,x:f64,n:u64}
            fn main(){
                let mut p=Point{b:1,x:1.5,n:18446744073709551615};
                p.x+={p.n=3;p.x};
                print(p.x);print(p.n);
                let mut mem=pool<u64>(1);let mut n=mem.new(7);
                let mut r=&mut n;*r+=*r+1;print(*r);
            }'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '3\n3\n15\n')
        self.refuses(source.replace('p.n=3;', 'p.x=3.;'), 'emprunt actif')
        enum = '''enum E {N{value:u64},F{value:f64}}
            fn main(){let e=E.N{value:18446744073709551615};
                match &e {E.N{value:n}=>{print(n);},E.F{value:f}=>{print(f);},}}
        '''
        self.assertEqual(self.run_c_oracle(compile_source(enum)).stdout, '18446744073709551615\n')
        aligned = '''struct Mixed {small:u8, n:i32}
            fn main(){let mut m=Mixed{small:1,n:3};let mut n=&mut m.n;*n+=4;print(*n);}'''
        self.assertEqual(self.run_c_oracle(compile_source(aligned)).stdout, '7\n')

    def test_async_numeric_pools_fields_and_conversion_results(self):
        source = '''struct Point{x:f64,n:u64}
            async fn convertir(x:f64)->Result<i64,NumericConversionError>{
                yield;i64::try_from(x)
            }
            async fn run(n:A<u64>)->i64{
                let mut local=pool<u64>(1);let v=local.new(*n);
                let mut p=Point{x:1.5,n:*v};yield;p.x=3.5;
                let result=convertir(p.x).await;
                match result{Ok(converti)=>{converti},Err(NumericConversionError::NotRepresentable)=>{9},}
            }
            fn main(){let mut p=pool<u64>(1);let n=p.new(7);let h=runtime::spawn(run(n));
                match h.join(){Ok(v)=>{print(v);},Err(_)=>{},}}
        '''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '9\n')

    def test_sync_mutex_unlocks_on_scope_exit(self):
        source = '''fn main(){
            let m=Mutex::new(0);
            {let mut g=m.lock();*g+=1;print(*g);}
            let g=m.lock();print(*g);
        }'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '1\n1\n')
        self.refuses('fn main(){let m=Mutex::new(0);let g=m.lock();drop(m);print(*g);}',
                     'emprunt encore utilisé')

    def test_async_mutex_releases_guard_at_return_before_handle_cleanup(self):
        source = '''async fn increment(m:&AsyncMutex<i64>)->i64{
                let mut g=m.lock().await;*g=*g+1;yield;*g
            }
            fn main(){
                let m=AsyncMutex::new(0);
                let a=runtime::spawn(increment(&m));let b=runtime::spawn(increment(&m));
                match a.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);},}
                match b.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);},}
            }
        '''
        self.assertEqual(sorted(self.run_c_oracle(compile_source(source)).stdout.splitlines()), ['1', '2'])
        self.refuses('async fn f()->i64{let m=Mutex::new(0);let g=m.lock();yield;*g}fn main(){}',
                     'garde de Mutex synchrone')

    def test_async_guard_reborrows_into_child(self):
        source = '''async fn update(n:&mut i32){yield;*n=7;}
            async fn f(m:&AsyncMutex<i32>)->i32{
                let mut g=m.lock().await;update(&mut *g).await;*g
            }
            fn main(){let n:i32=0;let m=AsyncMutex::new(n);let h=runtime::spawn(f(&m));
                match h.join(){Ok(x)=>{print(x);},Err(_)=>{},}
            }'''
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')

    def test_owned_async_struct_moves_in_current_profile(self):
        setup = '''struct Holder{value:A<i32>}
            fn main(){
                let mut values=pool<i32>(1);let mut holders=pool<Holder>(1);
                let value=values.new(7);let holder=holders.new(value:value);
                let h=runtime::spawn(work(holder));
                RESULT
                let reused=values.new(30);print(*reused);
            }'''
        cases = (
            ('''async fn work(h:A<Holder>)->A<Holder>{yield;h}''',
             'match h.join(){Ok(result)=>{print(*result.value);drop(result);},Err(_)=>{},}'),
            ('''fn inspect(h:A<Holder>)->i32{*h.value}
                 async fn work(h:A<Holder>)->i32{yield;inspect(h)}''',
             'match h.join(){Ok(n)=>{print(n);},Err(_)=>{},}'),
        )
        for functions, result in cases:
            with self.subTest(functions=functions):
                source = functions + setup.replace('RESULT', result)
                verify_program(source)
                run = self.run_c_oracle(compile_source(source))
                self.assertEqual(run.stdout, '7\n30\n')
                self.assertEqual(run.stderr.count('destroy holder=Holder'), 1)

    def test_bare_numeric_defaults_in_core_program(self):
        for source, expected in (
            ('fn main(){let n=9223372036854775807;move {print(n);}}', '9223372036854775807\n'),
            ('fn main(){let fraction=.5;print(fraction);}', '0.5\n'),
        ):
            with self.subTest(source=source):
                verify_program(source)
                self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, expected)

    def test_scheduler_registers_poller_delivers_wake_and_reports_launch_failure(self):
        source = '''struct Scheduler{workers:i32}
            impl Scheduler {
                fn spawn(self:&mut Scheduler,f:runtime::Future){
                    if self.workers == 0 {
                        if runtime::start_poller() {self.workers=1;}
                        else {f.launch_failed();return;}
                    }
                    f.enqueue();
                }
                fn spawn_blocking(self:&mut Scheduler,f:runtime::Future){f.launch_failed();}
                fn wake(self:&mut Scheduler,id:runtime::TaskId){print(11);}
            }
            async fn task()->i64{yield;7}
            fn main(){
                let scheduler=Scheduler{workers:0};runtime::set_scheduler(scheduler);
                let h=runtime::spawn(task());
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);},}
                let b=runtime::spawn_blocking(task());
                match b.join(){Ok(n)=>{print(n);},Err(runtime::Error::LaunchFailed)=>{print(0);},}
            }'''
        self.refuses(source, '--experimental-scheduler')
        self.refuses('fn main(){runtime::set_scheduler(s);}', '--experimental-scheduler')
        self.refuses('fn main(){let b=runtime::start_poller();print(b);}', '--experimental-scheduler')
        options = {'experimental_scheduler': True}
        verify_program(source, **options)
        self.assertEqual(self.run_c_oracle(compile_source(source, **options)).stdout, '11\n7\n0\n')
        self.refuses(source.replace('id:runtime::TaskId', 'id:i64'), 'signature incompatible', **options)
        self.refuses(source.replace('f.enqueue();', ''), 'scheduler doit enfiler la Future', **options)

    def test_scheduler_installation_is_confined_to_main(self):
        self.refuses('''struct S{x:i32}
            fn install(){let s=S{x:0};runtime::set_scheduler(s);}
            fn main(){install();}''', 'directement dans main', experimental_scheduler=True)

    def test_scheduler_installation_is_checked_on_each_path(self):
        declarations = '''struct S{x:i32}
            impl S{
                fn spawn(self:&mut S,f:runtime::Future){f.launch_failed();}
                fn spawn_blocking(self:&mut S,f:runtime::Future){f.launch_failed();}
                fn wake(self:&mut S,id:runtime::TaskId){}
            }
            fn launch(){
                let h=runtime::thread({7});
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{},}
            }'''
        def main(body):
            second = 'let b=S{x:2};' if 'set_scheduler(b)' in body else ''
            return declarations + 'fn main(){let a=S{x:1};' + second + body + '}'
        valid = main('if true{runtime::set_scheduler(a);}else{runtime::set_scheduler(b);}launch();')
        options = {'experimental_scheduler': True}
        verify_program(valid, **options)
        self.assertEqual(self.run_c_oracle(compile_source(valid, **options)).stdout, '7\n')
        for body in ('launch();runtime::set_scheduler(a);',
                     'runtime::set_scheduler(a);runtime::set_scheduler(b);',
                     'if true{launch();}runtime::set_scheduler(a);',
                     'loop{runtime::set_scheduler(a);continue;}'):
            with self.subTest(body=body):
                self.refuses(main(body), 'installation du scheduler|plus utilisable|reprise', **options)

    def test_wide_field_loans_cross_calls_and_suspension(self):
        source = '''struct P{b:u8,n:u64}
            fn field(p:&mut P)->&mut u64{&mut p.n}
            fn add(n:&mut u64){*n+=2;}
            async fn update(n:&mut u64){yield;add(n);}
            fn main(){let mut p=P{b:1,n:7};
                let mut n=field(&mut p);add(n);
                let h=runtime::spawn(update(&mut p.n));
                match h.join(){Ok(_)=>{},Err(_)=>{},}
                print(p.n);
            }'''
        verify_program(source)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '11\n')
        self.refuses(source.replace('match h.join()', 'p.n=1;match h.join()'), 'emprunt actif|réserv')

    def test_mutex_moves_structural_payload_and_reborrows_it(self):
        source = '''struct P{n:i64}
            async fn update(p:&mut P){yield;p.n=7;}
            async fn run(m:&AsyncMutex<P>)->i64{
                let mut g=m.lock().await;update(&mut *g).await;let p=&*g;p.n
            }
            fn main(){let p=P{n:1};let m=AsyncMutex::new(p);let h=runtime::spawn(run(&m));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{},}}
        '''
        verify_program(source)
        run = self.run_c_oracle(compile_source(source))
        self.assertEqual(run.stdout, '7\n')
        self.assertEqual(run.stderr.count('destroy p=P'), 1)
        self.refuses(source.replace('let h=runtime::spawn', 'print(p.n);let h=runtime::spawn'),
                     'plus utilisable|déplac')
        self.refuses('struct P{n:i64} fn main(){let m=Mutex::new(P{n:1});'
                     'let g=m.lock();let p=&*g;drop(g);print(p.n);}', 'emprunt encore utilisé')

    def test_wide_guard_reborrows_into_a_child(self):
        source = '''async fn update(n:&mut i64){yield;*n=7;}
            async fn f(m:&AsyncMutex<i64>)->i64{
                let mut g=m.lock().await;update(&mut *g).await;*g
            }
            fn main(){let m=AsyncMutex::new(0);let h=runtime::spawn(f(&m));
                match h.join(){Ok(n)=>{print(n);},Err(_)=>{},}}'''
        verify_program(source)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '7\n')

    def test_mutex_payload_retains_borrow_and_owned_pool(self):
        declarations = 'struct Item{x:i32} struct Payload{view:&i32,item:A<Item>}'
        setup = '''let mut numbers=pool<i32>(1);let n=numbers.new(6);
            let mut items=pool<Item>(1);let i=items.new(x:4);
            let obj=Payload{view:&n,item:i};'''
        read = 'let p=&*g;let item=&*p.item;'
        sync = declarations + 'fn main(){' + setup + (
            'let m=Mutex::new(obj);{let g=m.lock();' + read +
            'print(*p.view+item.x);}drop(m);let again=items.new(x:7);print(again.x);}')
        async_read = 'let g=m.lock().await;' + read + 'yield;*p.view+item.x'
        main = '''let h=runtime::spawn(read(&m));
            match h.join(){Ok(x)=>{print(x);},Err(_)=>{},}
            drop(m);let again=items.new(x:7);print(again.x);'''
        asynchronous = (declarations + 'async fn read(m:&AsyncMutex<Payload>)->i32{' + async_read +
                        '}fn main(){' + setup + 'let m=AsyncMutex::new(obj);' + main + '}')
        local = (declarations + 'async fn read()->i32{' + setup + 'let m=AsyncMutex::new(obj);' +
                 async_read + '''}fn main(){let h=runtime::spawn(read());
                     match h.join(){Ok(x)=>{print(x);},Err(_)=>{},}}''')
        for source, expected in ((sync, '10\n7\n'), (asynchronous, '10\n7\n'), (local, '10\n')):
            with self.subTest(expected=expected, source=source):
                verify_program(source)
                run = self.run_c_oracle(compile_source(source))
                self.assertEqual(run.stdout, expected)
                self.assertEqual(run.stderr.count('destroy i=Item'), 1)
                self.assertEqual(run.stderr.count('destroy n=6'), 1)
        self.refuses(asynchronous.replace('match h.join()', 'drop(n);match h.join()'), 'emprunt actif|emprunt encore')
        self.refuses(local.replace('let g=m.lock()', 'drop(n);let g=m.lock()'), 'emprunt actif|emprunt encore')
        self.refuses(sync.replace('let item=', 'drop(g);let item='), 'emprunt actif|emprunt encore')

    def test_guarded_replacement_updates_borrow_and_pool_provenance(self):
        declarations = '''struct Item{x:i32} struct Payload{view:&i32,item:A<Item>}
            fn change(p:&mut Payload,n:&i32){p.view=&*n;}
            fn put(p:&mut Payload,item:A<Item>){p.item=item;}'''
        body = '''
            let mut numbers=pool<i32>(2);
            let old=numbers.new(6);
            let replacement=numbers.new(8);
            let mut first=pool<Item>(1);
            let mut second=pool<Item>(1);
            let payload=Payload{view:&old,item:first.new(x:4)};
            let m=Mutex::new(payload);
            {
                let mut g=m.lock();
                let mut p=&mut *g;
                p.view=&replacement;
                let incoming=second.new(x:11);
                p.item=incoming;
            }
            drop(old);
            let reuse=first.new(x:7);
            print(reuse.x);
            {
                let g=m.lock();
                let p=&*g;
                let item=&*p.item;
                print(*p.view+item.x);
            }
            drop(m);
            drop(replacement);
            let reuse2=second.new(x:13);
            print(reuse2.x);
        '''
        for asynchronous in (False, True):
            if asynchronous:
                header = 'async fn run(){'
                code = body.replace('Mutex::new', 'AsyncMutex::new').replace('.lock()', '.lock().await')
                end = '''}fn main(){let h=runtime::spawn(run());
                    match h.join(){Ok(_)=>{},Err(_)=>{},}}'''
            else:
                header, code, end = 'fn main(){', body, '}'
            source = declarations + header + code + end
            for by_call in (False, True):
                with self.subTest(asynchronous=asynchronous, by_call=by_call):
                    variant = source
                    if by_call:
                        variant = (variant.replace('p.view=&replacement;', 'change(p,&replacement);')
                                   .replace('p.item=incoming;', 'put(p,incoming);'))
                    verify_program(variant)
                    run = self.run_c_oracle(compile_source(variant))
                    self.assertEqual(run.stdout, '7\n19\n13\n')
                    self.assertEqual(run.stderr.count('destroy incoming=Item'), 1)
                    self.assertLess(run.stderr.index('destroy incoming=Item'), run.stderr.index('destroy m='))
            with self.subTest(asynchronous=asynchronous):
                self.refuses(source.replace('drop(old);', 'drop(old);drop(replacement);'),
                             'emprunt actif|emprunt encore')
                self.refuses(source.replace('p.view=&replacement;', '''
                    let mut local=pool<i32>(1);let short=local.new(9);p.view=&short;'''),
                    'cible empruntée non durable')
                self.refuses(source.replace('let incoming=second.new', 'let mut local=pool<Item>(1);let incoming=local.new'),
                             'pool.*survit pas')

    def test_guarded_task_publishes_dependencies_by_join_outcome(self):
        from scheduler_faults import inject_submission_failure

        source = '''struct Payload{view:&i32}
            async fn change(m:&AsyncMutex<Payload>,n:&i32){
                let mut g=m.lock().await;let mut p=&mut *g;p.view=&*n;
            }
            async fn read(m:&AsyncMutex<Payload>)->i32{
                let g=m.lock().await;let p=&*g;*p.view
            }
            fn main(){
                let mut memory=pool<i32>(2);let old=memory.new(1);let n=memory.new(2);
                let m=AsyncMutex::new(Payload{view:&old});
                let h=runtime::spawn(change(&m,&n));
                match h.join(){
                    Ok(())=>{
                        move old;drop(old);
                        let reader=runtime::spawn(read(&m));
                        match reader.join(){Ok(value)=>{print(value);},Err(_)=>{},}
                    },
                    Err(runtime::Error::LaunchFailed)=>{
                        move n;drop(n);
                        let reader=runtime::spawn(read(&m));
                        match reader.join(){Ok(value)=>{print(value);},Err(_)=>{},}
                    },
                }
                drop(m);
            }'''
        for program in (source, source.replace('match h.join()', 'let status=h.join();match status')):
            with self.subTest(named_result=program != source):
                compiler = verify_program(program)
                contract = compiler.async_structure_effects['change']
                self.assertEqual(contract.guarded_writes, ((0, '.view', 1),))
                fields = dict(dict(contract.guarded_fields)[0])
                self.assertEqual({(target.kind, target.parameter) for target in fields['.view']}, {('parameter', 1)})
                code = compile_source(program)
                for failure, expected, released in ((False, '2\n', 'old=1'), (True, '1\n', 'n=2')):
                    with self.subTest(launch_failed=failure):
                        run = self.run_c_oracle(inject_submission_failure(code, asynchronous=False, at=1)
                                                if failure else code)
                        self.assertEqual(run.stdout, expected)
                        self.assertEqual(run.stderr.count('destroy old=1'), 1)
                        self.assertEqual(run.stderr.count('destroy n=2'), 1)
                        self.assertLess(run.stderr.index('destroy ' + released), run.stderr.index('destroy m='))
        for safe, unsafe in (('move old;drop(old);', 'move n;drop(n);'),
                             ('move n;drop(n);', 'move old;drop(old);')):
            self.refuses(source.replace(safe, unsafe, 1), 'emprunt actif|emprunt encore')
        self.refuses(source.replace('match h.join(){', 'drop(n);match h.join(){', 1), 'emprunt actif|emprunt encore')
        self.refuses(source.replace('match h.join(){',
                                    'let overlap=runtime::spawn(read(&m));'
                                    'match overlap.join(){Ok(_)=>{},Err(_)=>{},}match h.join(){', 1),
                     'emprunt actif')
        self.refuses(source.replace('p.view=&*n;', 'if update{p.view=&*n;}').replace(
            'n:&i32){', 'n:&i32,update:bool){').replace('change(&m,&n)', 'change(&m,&n,true)'),
            'emprunt actif|emprunt encore')
        prefix = source[:source.index('let h=runtime::spawn(change')]
        short = prefix.replace('let n=memory.new(2);', '') + '''
                {
                    let mut local=pool<i32>(1);let n=local.new(2);
                    let h=runtime::spawn(change(&m,&n));
                    match h.join(){Ok(())=>{},Err(_)=>{},}
                }
                drop(m);
            }'''
        self.refuses(short, 'cible empruntée non durable')
        unchecked = prefix + '''
                let h=runtime::spawn(change(&m,&n));
                match h.join(){_=>{},}
                drop(old);
                let reader=runtime::spawn(read(&m));
                match reader.join(){Ok(value)=>{print(value);},Err(_)=>{},}
                drop(m);
            }'''
        self.refuses(unchecked, 'emprunt actif|emprunt encore')

    def test_guarded_task_publishes_dependencies_by_await_outcome(self):
        from scheduler_faults import inject_submission_failure

        source = '''struct Payload{view:&i32}
            async fn change(m:&AsyncMutex<Payload>,n:&i32){
                let mut g=m.lock().await;let mut p=&mut *g;yield;p.view=&*n;
            }
            async fn read(m:&AsyncMutex<Payload>)->i32{
                let g=m.lock().await;let p=&*g;*p.view
            }
            async fn run(){
                let mut memory=pool<i32>(2);let old=memory.new(1);let n=memory.new(2);
                let m=AsyncMutex::new(Payload{view:&old});
                let h=runtime::spawn(change(&m,&n));
                yield;
                match h.await{
                    Ok(())=>{
                        move old;drop(old);
                        let value=read(&m).await;print(value);return;
                    },
                    Err(runtime::Error::LaunchFailed)=>{
                        move n;drop(n);
                        let value=read(&m).await;print(value);return;
                    },
                }
            }
            fn main(){
                let h=runtime::spawn(run());match h.join(){Ok(())=>{},Err(_)=>{},}
            }'''
        for program in (source, source.replace('match h.await', 'let status=h.await;match status')):
            with self.subTest(named_result=program != source):
                verify_program(program)
                code = compile_source(program)
                for failure, expected, released in ((False, '2\n', 'old=1'), (True, '1\n', 'n=2')):
                    with self.subTest(launch_failed=failure):
                        run = self.run_c_oracle(inject_submission_failure(code, at=1) if failure else code)
                        self.assertEqual(run.stdout, expected)
                        self.assertEqual(run.stderr.count('destroy old=1'), 1)
                        self.assertEqual(run.stderr.count('destroy n=2'), 1)
                        self.assertLess(run.stderr.index('destroy ' + released), run.stderr.index('destroy m='))
        for safe, unsafe in (('move old;drop(old);', 'move n;drop(n);'),
                             ('move n;drop(n);', 'move old;drop(old);')):
            self.refuses(source.replace(safe, unsafe, 1), 'emprunt actif')
        for operation in ('drop(old);', 'drop(n);', 'drop(m);', 'let value=read(&m).await;print(value);'):
            with self.subTest(before_await=operation):
                self.refuses(source.replace('match h.await', operation + 'match h.await', 1), 'emprunt actif')
        conditional = source.replace('yield;p.view=&*n;', 'yield;if update{p.view=&*n;}').replace(
            'n:&i32){', 'n:&i32,update:bool){').replace('change(&m,&n)', 'change(&m,&n,true)')
        self.refuses(conditional, 'emprunt actif')

        prefix, main = source[:source.index('let h=runtime::spawn(change')], source[source.index('fn main()'):]
        short = prefix.replace('let n=memory.new(2);', '') + '''
                {
                    let mut local=pool<i32>(1);let n=local.new(2);
                    let h=runtime::spawn(change(&m,&n));
                    match h.await{Ok(())=>{},Err(_)=>{},}
                }
                drop(m);
            }''' + main
        self.refuses(short, 'cible empruntée non durable')
        unchecked = prefix + '''
                let h=runtime::spawn(change(&m,&n));
                match h.await{Ok(())=>{},Err(_)=>{},}
                drop(old);
                let value=read(&m).await;print(value);
                drop(m);
            }''' + main
        self.refuses(unchecked, 'emprunt actif')
        stale = source.replace('match h.await', '''
                let status=h.await;
                let next=runtime::spawn(change(&m,&old));
                match next.await{Ok(())=>{},Err(_)=>{},}
                match status''', 1)
        self.refuses(stale, 'emprunt actif')

    def test_async_mutex_serializes_its_mutable_dependency(self):
        source = '''struct Payload{view:&mut i32}
            async fn bump(m:&AsyncMutex<Payload>)->i32{
                let mut g=m.lock().await;let mut p=&mut *g;let mut v=&mut *p.view;
                *v+=1;yield;*v
            }
            fn main(){
                let mut numbers=pool<i32>(1);let mut n=numbers.new(6);
                let obj=Payload{view:&mut n};let m=AsyncMutex::new(obj);
                let a=runtime::spawn(bump(&m));let b=runtime::spawn(bump(&m));
                match a.join(){Ok(x)=>{print(x);},Err(_)=>{},}
                match b.join(){Ok(x)=>{print(x);},Err(_)=>{},}
                drop(m);print(*n);
            }'''
        verify_program(source)
        result = self.run_c_oracle(compile_source(source)).stdout.splitlines()
        self.assertEqual((sorted(result[:2]), result[2:]), (['7', '8'], ['8']))
        self.refuses(source.replace('drop(m);print(*n);', 'print(*n);drop(m);'), 'emprunt actif')

    def test_wide_local_scalar_is_reserved_until_join(self):
        source = '''fn add(n:&mut u64){*n+=2;}
            async fn update(n:&mut u64){yield;add(n);}
            fn main(){let mut n:u64=7;add(&mut n);
                let h=runtime::spawn(update(&mut n));
                match h.join(){Ok(_)=>{},Err(_)=>{},}print(n);
            }'''
        verify_program(source)
        self.assertEqual(self.run_c_oracle(compile_source(source)).stdout, '11\n')
        self.refuses(source.replace('match h.join()', '{move n;print(n);}match h.join()'),
                     'emprunt actif')

    def test_parent_reservation_with_a_diverging_branch(self):
        for condition, expected in (('true', '1\n7\n'), ('false', '')):
            source = f'''struct P{{n:i32}} fn main(){{
                let p=if {condition} {{
                    let tmp=P{{n:1}};print(tmp.n);let a=P{{n:7}};a
                }} else {{return;}};
                print(p.n);
            }}'''
            with self.subTest(condition=condition):
                verify_program(source)
                code = compile_source(source)
                self.assertIn('cell_construct_reserved(local_reserved', code)
                run = self.run_c_oracle(code)
                self.assertEqual(run.stdout, expected)
                if expected:
                    self.assertLess(run.stderr.index('reclaim tmp'), run.stderr.index('destroy a=P'))

    def test_parent_reservation_with_control_flow_around_the_producer(self):
        for body in ('if true{print(tmp.x);}let conserve=P{x:9};',
                     'let conserve=P{x:9};if true{print(tmp.x);}'):
            source = ('struct P{x:i32} fn main(){let recu={let tmp=P{x:7};' +
                      body + 'conserve};print(recu.x);}')
            with self.subTest(body=body):
                verify_program(source)
                code = compile_source(source)
                self.assertIn('cell_construct_reserved(local_reserved', code)
                run = self.run_c_oracle(code)
                self.assertEqual(run.stdout, '7\n9\n')
                self.assertLess(run.stderr.index('reclaim tmp'), run.stderr.index('destroy conserve=P'))
