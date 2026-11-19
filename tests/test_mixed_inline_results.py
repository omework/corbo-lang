"""One reference result may designate a whole object or an interior of the same type."""
import unittest
import test_select_source as harness

TYPES='struct Point{x:Int}struct Pair{a:Point,b:Point}'
INIT='let mut a=Point{x:3};let mut pair=Pair{a:Point{x:1},b:Point{x:7}};'


class MixedInlineResultTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def program(self, body, helpers=''):
        return TYPES+helpers+'fn main(){'+INIT+body+'}'

    def test_conditional_function_return_and_relay_keep_address(self):
        helpers='''fn pick(a:&Point,p:&Pair,flag:Int)->&Point{
            if flag==0{return a;}return &p.b;}
            fn relay(a:&Point,p:&Pair,flag:Int)->&Point{return pick(a,p,flag);}'''
        for flag,expected in ((0,'3'),(1,'7')):
            source=self.program('''let interior=&pair.b;address(a);address(interior);
                let result=relay(&a,&pair,FLAG);address(result);print(result.x);'''.replace('FLAG',str(flag)),helpers)
            with self.subTest(flag=flag):
                run=self.run_source(source)
                whole,interior,actual,value=run.stdout.splitlines()
                self.assertEqual(actual,whole if flag==0 else interior)
                self.assertEqual(value,expected)
            for name in ('a','pair'):
                self.refused(source.replace('print(result.x);',f'drop(->{name});print(result.x);'),'emprunt|réserv|référenc')

    def test_if_expression_mutable_result(self):
        for flag,expected in ((0,'11\n7\n'),(1,'3\n11\n')):
            source=self.program('''let mut result=if FLAG==0{&mut a}else{&mut pair.b};
                result.x=11;print(a.x);print(pair.b.x);'''.replace('FLAG',str(flag)))
            with self.subTest(flag=flag):
                self.assertEqual(self.run_source(source).stdout,expected)
            self.refused(source.replace('result.x=11;','a.x=20;result.x=11;'),'emprunt|réserv|référenc')

    def test_loop_break_results(self):
        for flag,expected in ((0,'3\n'),(1,'7\n')):
            source=self.program('''let result=loop{if FLAG==0{break &a;}break &pair.b;};
                print(result.x);'''.replace('FLAG',str(flag)))
            with self.subTest(flag=flag):
                self.assertEqual(self.run_source(source).stdout,expected)

    def test_match_results(self):
        helpers='enum Side{Left,Right}'
        for arm,expected in (('Left','3\n'),('Right','7\n')):
            source=self.program('''let mut sides=pool<Side>(1);let side=new(sides) Side.ARM;
                let result=match &side{Side.Left=>{&a},Side.Right=>{&pair.b}};
                print(result.x);'''.replace('ARM',arm),helpers)
            with self.subTest(arm=arm):
                self.assertEqual(self.run_source(source).stdout,expected)

    def test_store_and_copy_mixed_reference(self):
        helpers='struct View{point:&Point}'
        for flag,expected in ((0,'3\n3\n'),(1,'7\n7\n')):
            source=self.program('''let result=if FLAG==0{&a}else{&pair.b};
                let copied=copy(result);let v=View{point:result};
                let r=v.point;drop(->v);print(r.x);print(copied.x);'''.replace('FLAG',str(flag)),helpers)
            with self.subTest(flag=flag):
                self.assertEqual(self.run_source(source).stdout,expected)

    def test_mutable_function_result_stored_and_reborrowed(self):
        helpers='''struct Writer{point:&mut Point}
            fn pick(a:&mut Point,p:&mut Pair,flag:Int)->&mut Point{
                if flag==0{return a;}return &mut p.b;}
            fn edit(p:&mut Point){p.x=11;}
            fn get(w:&mut Writer)->&mut Point{return &mut *w.point;}'''
        for flag,expected in ((0,'11\n7\n'),(1,'3\n11\n')):
            source=self.program('''let mut result=pick(&mut a,&mut pair,FLAG);
                let mut w=Writer{point:result};let mut again=get(&mut w);
                edit(again);drop(->w);print(a.x);print(pair.b.x);'''.replace('FLAG',str(flag)),helpers)
            with self.subTest(flag=flag):
                self.assertEqual(self.run_source(source).stdout,expected)
            for operation in ('drop(->w);','a.x=20;'):
                self.refused(source.replace('edit(again);',operation+'edit(again);'),'emprunt|réserv|référenc')

    def test_short_interior_branch_cannot_escape(self):
        source=TYPES+'''fn bad(a:&Point,flag:Int)->&Point{
            if flag==0{return a;}let pair=Pair{a:Point{x:1},b:Point{x:7}};
            return &pair.b;}fn main(){}'''
        self.refused(source,'durable|scope parent')


if __name__=='__main__':
    unittest.main()
