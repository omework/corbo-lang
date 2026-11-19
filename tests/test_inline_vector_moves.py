"""Named local T moves into Vector<T>; A<T> and live borrows stay distinct."""
import unittest
from crust import verify_program
import test_select_source as harness

POINT='struct Point{x:Int,y:Int}'
SETUP='let mut p=pool<Vector<Point>>(1);let mut v=p.new();'


class InlineVectorMoveTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    @staticmethod
    def source(body, *, asynchronous=False, helpers=''):
        if not asynchronous:
            return POINT+helpers+'fn main(){'+body+'}'
        return POINT+helpers+'async fn work()->Int{'+body+'''return 0;}
            fn main(){let h=runtime::spawn(->work());match h.join(){
                Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_named_move_and_invalidation_sync_async(self):
        body=SETUP+'''let point=Point{x:7,y:9};v.push(->point);
            let r=copy(v[0]);drop(->v);print(r.x);print(r.y);'''
        for asynchronous in (False,True):
            source=self.source(body,asynchronous=asynchronous)
            self.assertEqual(self.run_source(source).stdout,'7\n9\n'+('0\n' if asynchronous else ''))
            for operation in ('print(point.x);','drop(->point);'):
                self.refused(source.replace('let r=copy(v[0]);',operation+'let r=copy(v[0]);'),
                             'utilisable|déplac|consomm|invalid|détruit')
            self.refused(source.replace('v.push(->point)','v.push(point)'), 'transfert|explicite')

    def test_borrow_ends_before_move(self):
        body=SETUP+'''let point=Point{x:7,y:9};let view=&point;print(view.x);
            v.push(->point);let r=<-v.remove(0);print(r.y);'''
        for asynchronous in (False,True):
            source=self.source(body,asynchronous=asynchronous)
            self.assertEqual(self.run_source(source).stdout,'7\n9\n'+('0\n' if asynchronous else ''))
            self.refused(source.replace('print(view.x);\n            v.push(->point);',
                                       'v.push(->point);print(view.x);'), 'emprunt|réserv')
            self.refused(source.replace('let point=Point{x:7,y:9};',
                'let mut points=pool<Point>(1);let point=points.new(x:7,y:9);'), 'valeur.*Point|locale.*Point|A<Point>|A<T>')

    def test_function_parameter_and_relay(self):
        helper='''fn append(v:&mut Vector<Point>,point:->Point){v.push(->point);}
            fn relay(v:&mut Vector<Point>,point:->Point){append(&mut *v,->point);}'''
        body=SETUP+'''let point=Point{x:7,y:9};relay(&mut v,->point);
            let r=<-v.remove(0);drop(->v);print(r.x);'''
        for asynchronous in (False,True):
            source=self.source(body,asynchronous=asynchronous,helpers=helper)
            self.assertEqual(self.run_source(source).stdout,'7\n'+('0\n' if asynchronous else ''))
            self.refused(source.replace('relay(&mut v,->point)','relay(&mut v,point)'), 'transfert|mode attendu|->')
            check=verify_program(source)
            for name in ('append','relay'):
                self.assertEqual(check.function_contracts[name].storage_requirements,((1,'local'),))
            self.refused(source.replace('let point=Point{x:7,y:9};',
                'let mut points=pool<Point>(1);let point=points.new(x:7,y:9);'), 'stockage|local|allocation')

    def test_async_owned_capture_and_injected_vector(self):
        helper='''async fn append(v:&mut Vector<Point>,point:->Point){yield;v.push(->point);yield;}'''
        body=SETUP+'''let point=Point{x:7,y:9};let task=append(&mut v,->point);yield;
            task.await;let r=<-v.remove(0);print(r.x);'''
        source=self.source(body,asynchronous=True,helpers=helper)
        self.assertEqual(self.run_source(source).stdout,'7\n0\n')
        self.assertEqual(verify_program(source).async_definitions['append'][0].storage_requirements,((1,'local'),))
        self.refused(source.replace('let point=Point{x:7,y:9};',
            'let mut points=pool<Point>(1);let point=points.new(x:7,y:9);'), 'stockage|local|allocation')
        self.refused(source.replace('task.await;', 'print(point.x);task.await;'), 'utilisable|déplac|invalid|consomm')
        self.refused(source.replace('task.await;', 'print(v.len());task.await;'), 'emprunt|réserv')

    def test_child_scope_and_explicit_import(self):
        body=SETUP+'''let point=Point{x:7,y:9};{point ->;v.push(->point);}
            let r=copy(v[0]);print(r.x);'''
        for asynchronous in (False,True):
            source=self.source(body,asynchronous=asynchronous)
            self.assertEqual(self.run_source(source).stdout,'7\n'+('0\n' if asynchronous else ''))
            self.refused(source.replace('point ->;',''), 'scope|rattach|entrée')
            child=self.source(SETUP+'''{let point=Point{x:7,y:9};v.push(->point);}
                let r=copy(v[0]);print(r.y);''',asynchronous=asynchronous)
            self.assertEqual(self.run_source(child).stdout,'9\n'+('0\n' if asynchronous else ''))

    def test_extract_move_between_vectors_and_loop_cleanup(self):
        body='''let mut p=pool<Vector<Point>>(2);let mut a=p.new();let mut b=p.new();
            let mut i=0;while i<3{let point=Point{x:i,y:9};a.push(->point);i=i+1;}
            let mut j=0;while j<3{let point=<-a.remove(0);b.push(->point);j=j+1;}
            drop(->a);let r=copy(b[2]);drop(->b);print(r.x);
            let fresh=p.new();print(fresh.len());'''
        for asynchronous in (False,True):
            source=self.source(body,asynchronous=asynchronous)
            self.assertEqual(self.run_source(source).stdout,'2\n0\n'+('0\n' if asynchronous else ''))

    def test_nested_and_empty_named_values(self):
        body='''let mut p=pool<Vector<Pair>>(1);let mut v=p.new();
            let pair=Pair{left:Point{x:7,y:9},right:Point{x:11,y:13}};v.push(->pair);
            let r=<-v.remove(0);print(r.right.y);drop(->v);
            let mut es=pool<Vector<Empty>>(1);let mut ev=es.new();let e=Empty{};ev.push(->e);
            let out=<-ev.remove(0);drop(->out);print(ev.len());'''
        helper='struct Pair{left:Point,right:Point}struct Empty{}'
        for asynchronous in (False,True):
            self.assertEqual(self.run_source(self.source(body,asynchronous=asynchronous,helpers=helper)).stdout,
                             '13\n0\n'+('0\n' if asynchronous else ''))


if __name__=='__main__':unittest.main()
