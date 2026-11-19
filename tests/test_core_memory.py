"""N1–N8: current-profile memory transitions, without collection API expansion."""
import unittest
import test_select_source as harness


class CoreMemoryTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_n1_types_and_complete_initialization(self):
        source = '''struct View{target:&Int}
        fn main(){let mut p=pool<Int>(1);let n=p.new(7);
        let v=View{target:&n};print(*v.target);}'''
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.refused(source.replace('let v=', 'print(*n);let v=').replace('target:&n', ''), 'champ|défaut')
        self.refused(source.replace('let v=', 'print(*n);let v=').replace('target:&n', 'target:7'), '&Int requis')
        self.refused('struct Point{x:Int}fn main(){let mut p=pool<Point>(1);let n:Point=p.new(x:7);print(n.x);}',
                     'local|allocation|annotation|stockage')

    def test_n2_transfer_has_one_cleanup_and_keeps_identity(self):
        source = '''fn relay(n:->A<Int>)-><-A<Int>{address(n);return <-n;}
        fn main(){let mut p=pool<Int>(1);let a=p.new(7);address(a);
        let b=relay(->a);address(b);print(*b);drop(->b);
        let c=p.new(9);address(c);print(*c);}'''
        run = self.run_source(source)
        a, inside, b, seven, c, nine = run.stdout.splitlines()
        self.assertEqual((a, inside, b, c), (a, a, a, a))
        self.assertEqual((seven, nine), ('7', '9'))
        drops = [line for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(sum(line.endswith('=7') for line in drops), 1)
        self.assertEqual(sum(line.endswith('=9') for line in drops), 1)
        self.refused(source.replace('address(b);', 'print(*a);address(b);'), 'utilisable|déplac|consomm')

    def test_n3_explicit_copy_transfer_and_result_use(self):
        source = '''struct Point{x:Int}fn main(){let original=Point{x:7};
        let mut duplicate=copy(original);duplicate.x=9;print(original.x);print(duplicate.x);}'''
        self.assertEqual(self.run_source(source).stdout, '7\n9\n')
        self.refused(source.replace('copy(original)', 'original'), 'utilisable|déplac')
        self.refused('fn main(){let mut p=pool<Int>(1);let unused=p.new(7);}', 'usage explicite')
        self.refused('fn main(){u8::try_from(300);}', 'usage|résultat|explicite')

    def test_n4_child_parent_dependencies(self):
        source = '''struct View{target:&Int}fn main(){let mut p=pool<Int>(1);let n=p.new(7);
        let result={let v=View{target:&n};<-v};print(*result.target);}'''
        self.assertEqual(self.run_source(source).stdout, '7\n')
        self.refused(source.replace('let n=p.new(7);\n        let result={', 'let result={let n=p.new(7);'),
                     'durable|scope|cible|transfert|référenc')
        self.refused('fn main(){let n={let mut p=pool<Int>(1);let n=p.new(7);<-n};print(*n);}',
                     'source|pool|scope|durable')

    def test_n5_disjoint_access_and_last_use(self):
        source = '''struct Pair{x:Int,y:Int}
        fn edit(a:&mut Int,b:&mut Int){*a=11;*b=13;}
        fn main(){let mut pair=Pair{x:7,y:9};edit(&mut pair.x,&mut pair.y);
        let view=&pair.x;print(*view);pair.x=17;print(pair.x);print(pair.y);}'''
        self.assertEqual(self.run_source(source).stdout, '11\n17\n13\n')
        self.refused(source.replace('&mut pair.y', '&mut pair.x'), 'emprunt|alias|réserv')
        self.refused(source.replace('pair.x=17;print(pair.x)', 'pair.x=17;print(*view);print(pair.x)'),
                     'emprunt|réserv')
        borrowed = '''fn main(){let mut p=pool<Int>(1);let n=p.new(7);let v=&n;
        drop(->n);print(*v);}'''
        self.refused(borrowed, 'emprunt|réserv')
        self.assertEqual(self.run_source(borrowed.replace('drop(->n);print(*v)', 'print(*v);drop(->n)')).stdout, '7\n')

    def test_n6_paths_and_iteration_cleanup(self):
        source = '''fn run(flag:bool){let mut p=pool<Int>(1);let n=p.new(7);
        if flag{n ->;drop(->n);return;}print(*n);}
        fn main(){run(true);run(false);let mut p=pool<Int>(1);let mut i=0;
        loop{let n=p.new(i);print(*n);i=i+1;if i<3{continue;}break;}
        let last=p.new(9);print(*last);}'''
        run = self.run_source(source)
        self.assertEqual(run.stdout, '7\n0\n1\n2\n9\n')
        self.refused(source.replace('drop(->n);return;', 'drop(->n);'), 'utilisable|détruit|déplac')
        self.assertEqual(sum(line.startswith('destroy ') for line in run.stderr.splitlines()), 6)

    def test_n7_replace_then_destroy_and_exit_cleanup(self):
        source = '''fn replacement()->Int{print(1);return 9;}
        fn main(){let mut p=pool<Int>(2);let mut n=p.new(7);print(*n);address(n);
        n=<-p.new(replacement());address(n);print(*n);drop(->n);let last=p.new(11);print(*last);}'''
        run = self.run_source(source)
        seven, before, one, after, nine, eleven = run.stdout.splitlines()
        self.assertEqual((seven, one, nine, eleven), ('7', '1', '9', '11'))
        self.assertNotEqual(before, after)
        destroyed = [line.rsplit('=', 1)[-1] for line in run.stderr.splitlines() if line.startswith('destroy ')]
        self.assertEqual(destroyed, ['7', '9', '11'])
        self.refused(source.replace('n=<-p.new', 'let view=&n;n=<-p.new').replace('print(*n);drop', 'print(*view);print(*n);drop'),
                     'emprunt|réserv')
        self.refused('fn main(){let mut p=pool<Int>(1);p.reset();}', 'retir|reset|prototype')

    def test_n8_contract_preserves_returned_borrow(self):
        helper = '''fn borrow(n:&mut Int)->&mut Int{return n;}
        fn relay(n:&mut Int)->&mut Int{return borrow(n);}'''
        source = helper+'''fn main(){let mut p=pool<Int>(1);let mut n=p.new(7);
        let mut v=relay(&mut n);v.set(9);print(*v);n=11;print(*n);}'''
        self.assertEqual(self.run_source(source).stdout, '9\n11\n')
        self.refused(source.replace('v.set(9);', 'print(*n);v.set(9);'), 'emprunt|réserv')
        self.refused('fn invalid()->&Int{let mut p=pool<Int>(1);let n=p.new(7);return &n;}',
                     'durable|local|cible|retour')

    def test_ancestor_receipt_survives_a_child_shadow(self):
        source = '''fn main(){let mut p=pool<Int>(1);let mut q=pool<Int>(1);
        let mut r=p.new(10);print(*r);
        {let incoming=q.new(20);r=<-incoming;let r=p.new(30);print(*r);EXIT}
        AFTER}'''
        valid = source.replace('EXIT', '').replace('AFTER', 'print(*r);')
        run = self.run_source(valid)
        self.assertEqual(run.stdout, '10\n30\n20\n')
        self.assertEqual([line for line in run.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy r=10', 'destroy r=30', 'destroy incoming=20'])
        self.refused(source.replace('EXIT', '').replace('AFTER', ''), 'sans usage explicite')
        self.refused(source.replace('EXIT', 'return;').replace('AFTER', 'print(*r);'), 'sans usage explicite')


if __name__ == '__main__':
    unittest.main()
