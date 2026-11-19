"""Loop producer fixed points, checked against source and C storage oracles."""
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from async_local_placement import result_constructors
import test_async_local_parent as parent_tests

ROOT=Path(__file__).resolve().parents[1]

class AsyncLoopPlacementTests(unittest.TestCase):
    program=staticmethod(parent_tests.AsyncLocalParentTests.program)
    run_source=parent_tests.AsyncLocalParentTests.run_source
    run_c_oracle=parent_tests.AsyncLocalParentTests.run_c_oracle
    refused=parent_tests.AsyncLocalParentTests.refused
    storage_probe=parent_tests.AsyncLocalParentTests.storage_probe

    def test_recorded_and_zero_iterations(self):
        source=(ROOT/'validation/open-async-local-loop-updated-parent-result.crb').read_text()
        for bound in (0,1,2,5):
            with self.subTest(bound=bound):
                run=self.run_source(source.replace('i<2',f'i<{bound}'))
                self.assertEqual(run.stdout,''.join(f'{n}\n' for n in range(1,bound+2)))
                self.assertEqual(run.stderr.count('destroy p=Point\n'),bound+1)

    def test_continue_and_break(self):
        for kind in ('while i<5','loop'):
            source=self.program('''let r={let mut p=make(1);let mut i=0;LOOP{
                print(p.x);p=<-make(p.x+1);yield;i=i+1;
                if i<3{continue;}break;}<-p};return r.x;'''.replace('LOOP',kind))
            run=self.run_source(source)
            self.assertEqual(run.stdout,'1\n2\n3\n4\n')
            self.assertEqual(run.stderr.count('destroy p=Point\n'),4)

    def test_nested_loop_and_scope(self):
        source=self.program('''let r={let mut p=make(1);let mut i=0;while i<2{
            let mut j=0;while j<2{{print(p.x);p=<-make(p.x+1);}yield;j=j+1;}
            i=i+1;}<-p};return r.x;''')
        self.assertEqual(self.run_source(source).stdout,'1\n2\n3\n4\n5\n')

    def test_borrow_and_move_restrictions(self):
        source=self.program('''let r={let mut p=make(1);let mut i=0;while i<2{
            let view=&p.x;print(*view);p=<-make(p.x+1);yield;i=i+1;}<-p};return r.x;''')
        self.assertEqual(self.run_source(source).stdout,'1\n2\n3\n')
        self.refused(source.replace('print(*view);p=<-make(p.x+1);',
                                    'p=<-make(p.x+1);print(*view);'),'emprunt|réserv|référenc')
        self.refused(source.replace('p=<-make(p.x+1)','let q=make(p.x+1);p=q'), 'transfert|explicite')

    def test_field_source_does_not_follow_root_promotion(self):
        source='''struct Holder{value:A<Int>}fn wrap(n:->A<Int>)-><-Holder{
            let h=Holder{value:<-n};return <-h;}
            async fn work()->Int{OUTER let r={INNER let n=memory.new(1);let mut h=wrap(->n);
                let mut i=0;while i<2{print(*h.value);let next=memory.new(i+2);h=<-wrap(->next);i=i+1;}<-h};
                return *r.value;}fn main(){let h=runtime::spawn(->work());match h.join(){Ok(n)=>{print(n);},Err(_)=>{}}}'''
        pool='let mut memory=pool<Int>(2);'
        self.assertEqual(self.run_source(source.replace('OUTER',pool).replace('INNER','')).stdout,'1\n2\n3\n')
        self.refused(source.replace('OUTER','').replace('INNER',pool),'pool|source|survi')

    def test_loop_storage_and_result_identity(self):
        source=self.program('''let r={let mut p=make(1);let mut i=0;while i<3{
            print(p.x);p=<-make(p.x+1);yield;i=i+1;}<-p};yield;return r.x;''')
        run=self.storage_probe(source, '''
            CrustTask *task=crust_async_work_create();Source *parent=NULL;Cell *last=NULL;
            for(int i=0;i<3;++i){assert(task_poll(task)==TASK_SUSPENDED);
                assert(observed_count==i+2);last=observed_cells[i+1];
                if(i==0)parent=observed_cells[0]->source;
                assert(last->source==parent && parent->live==1);
                assert(last!=observed_cells[i]);
                assert(last->alive && cell_load_int(last,0)==i+2);
            }
            assert(task_poll(task)==TASK_SUSPENDED);
            assert(last->alive && last->source==parent && cell_load_int(last,0)==4);
            assert(task_poll(task)==TASK_COMPLETE);int answer;assert(task_take(task,&answer));assert(answer==4);
            assert(parent->live==0 && parent->used==0);
        ''')
        self.assertEqual(run.stderr.count('destroy p=Point\n'),4)

    def test_finite_origin_model_requires_multiple_passes(self):
        # Model only: these assignments describe dataflow, not ownership syntax.
        def node(op,*args):return NS(op=op,args=args,terminated=True)
        contracts={'make':NS(result=NS(typ='Point',candidates=[
            NS(kind='fresh',source=NS(kind='local_value'))]))}
        calls=[('call','make',[('int',i)]) for i in range(3)]
        declarations=[node('var',name,call) for name,call in zip(('a','b','c'),calls)]
        body=[node('while_check',('name','condition')),node('assign','a',('name','b')),
              node('assign','b',('name','c')),node('continue')]
        end=node('<-','a');end.terminated=False
        expr=('scope',None,[*declarations,node('while',body),end])
        self.assertEqual({id(c) for c in result_constructors(expr,contracts,{})}, {id(c) for c in calls})
        # Unknown producers must not be confused with an empty producer set.
        body.insert(-1,node('assign','c',('call','unknown',[])))
        self.assertEqual(result_constructors(expr,contracts,{}),())

if __name__=='__main__':unittest.main()
