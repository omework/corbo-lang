"""Inline struct vector payloads survive suspension and keep their storage kinds."""
import unittest
import test_select_source as harness

POINT = 'struct Point{x:Int,y:Int}'


class AsyncInlineVectorTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    @staticmethod
    def launch(body, helpers=''):
        return POINT+helpers+'async fn work()->Int{'+body+'''}
            fn main(){let h=runtime::spawn(->work());match h.join(){
            Ok(n)=>{print(n);},Err(_)=>{print(99);}}}'''

    def test_local_vectors_copy_remove_two_fronts_and_region(self):
        body='''let mut p=pool<Vector<Point>>(2);let mut a=p.new();let mut b=p.new();
            a.push(->Point{x:7,y:70});b.push(->Point{x:9,y:90});yield;
            let c=copy(a[0]);let d=<-b.remove(0);drop(->a);drop(->b);yield;
            print(c.y);print(d.y);return c.x+d.x;'''
        self.assertEqual(self.run_source(self.launch(body)).stdout, '70\n90\n16\n')
        region='let r=#(directive, stack_region_max_size=1M){'+body.replace('return c.x+d.x;',
            'let r=Point{x:c.x+d.x,y:0};<-r')+'};return r.x;'
        self.assertEqual(self.run_source(self.launch(region)).stdout, '70\n90\n16\n')
        self.refused(self.launch(body.replace('copy(a[0])', 'a[0]')), 'copie|tableau|expression|Int')
        self.refused(self.launch(body.replace('<-b.remove', 'b.remove')), 'transfert|explicite')

    def test_captured_mutable_vector_reserves_caller_until_join(self):
        source=POINT+'''async fn work(v:&mut Vector<Point>)->Int{yield;
            let r=<-v.remove(0);yield;return r.x;}
            fn main(){let mut p=pool<Vector<Point>>(1);let mut v=p.new();
            v.push(->Point{x:7,y:70});let h=runtime::spawn(->work(&mut v));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}print(v.len());}'''
        self.assertEqual(self.run_source(source).stdout, '7\n0\n')
        for access in ('print(v.len());', 'drop(->v);'):
            self.refused(source.replace('match h.join()', access+'match h.join()'), 'emprunt|réserv')

    def test_owned_capture_completion_and_inactive_cleanup(self):
        source=POINT+'''async fn work(mut v:->A<Vector<Point>>)->Int{yield;
            let r=<-v.remove(0);return r.x;}
            fn main(){let mut p=pool<Vector<Point>>(1);let mut v=p.new();
            v.push(->Point{x:7,y:70});let task=work(->v);ACTION
            let mut fresh=p.new();fresh.push(->Point{x:9,y:90});let r=copy(fresh[0]);print(r.x);}'''
        active='let h=runtime::spawn(->task);match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}'
        self.assertEqual(self.run_source(source.replace('ACTION',active)).stdout, '7\n9\n')
        self.assertEqual(self.run_source(source.replace('ACTION','drop(->task);')).stdout, '9\n')
        self.refused(source.replace('ACTION','print(v.len());drop(->task);'), 'utilisable|déplac|invalid')

    def test_local_results_return_by_join_and_await(self):
        for extraction in ('copy(v[0])', '<-v.remove(0)'):
            helper='''async fn leaf()-><-Point{let mut p=pool<Vector<Point>>(1);let mut v=p.new();
                v.push(->Point{x:7,y:70});let r=EXTRACT;drop(->v);yield;return <-r;}'''.replace('EXTRACT',extraction)
            self.assertEqual(self.run_source(self.launch('let r=leaf().await;yield;return r.x;',helper)).stdout, '7\n')
            source=POINT+helper+'''fn main(){let h=runtime::spawn(->leaf());match h.join(){
                Ok(r)=>{print(r.y);drop(->r);},Err(_)=>{print(99);}}}'''
            self.assertEqual(self.run_source(source).stdout, '70\n')
            self.refused(source.replace('-><-Point', '-><-A<Point>'), 'stockage|local|A<T>|provenance')

    def test_injected_pool_and_whole_vector_result(self):
        source=POINT+'''async fn make(p:&mut Pool<Vector<Point>>)-><-A<Vector<Point>>{
            let mut v=p.new();v.push(->Point{x:7,y:70});yield;return <-v;}
            fn main(){let mut p=pool<Vector<Point>>(1);let h=runtime::spawn(->make(&mut p));
            match h.join(){Ok(v)=>{let mut received=<-v;let r=<-received.remove(0);
                print(r.x);drop(->received);},Err(_)=>{print(99);}}let fresh=p.new();print(fresh.len());}'''
        self.assertEqual(self.run_source(source).stdout, '7\n0\n')
        helpers='''fn wait(h:->runtime::Handle<A<Vector<Point>>>)-><-Result<A<Vector<Point>>,runtime::Error>{return <-h.join();}
            fn relay(r:->Result<A<Vector<Point>>,runtime::Error>)-><-Result<A<Vector<Point>>,runtime::Error>{return <-r;}'''
        public=source.replace('fn main()',helpers+'fn main()').replace('match h.join()',
            'let result=wait(->h);let next=relay(->result);match next')
        self.assertEqual(self.run_source(public).stdout, '7\n0\n')
        self.refused(source.replace('let h=runtime::spawn(->make(&mut p));',
            'let h={let mut short=pool<Vector<Point>>(1);let h=runtime::spawn(->make(&mut short));<-h};'),
            'pool|source|survi|emprunt|join')

    def test_suspended_index_and_drop_result(self):
        helper='async fn index()->Int{yield;return 0;}'
        body='''let mut p=pool<Vector<Point>>(1);let mut v=p.new();
            v.push(->Point{x:7,y:70});v.push(->Point{x:9,y:90});
            let r=<-v.remove(index().await);yield;drop(->v.remove(0));return r.x+v.len();'''
        self.assertEqual(self.run_source(self.launch(body,helper)).stdout, '7\n')

    def test_scope_and_branch_results_survive_suspension(self):
        body='''let mut p=pool<Vector<Point>>(1);let mut v=p.new();v.push(->Point{x:7,y:70});
            let r=if true{let r=<-v.remove(0);yield;<-r}else{let r=copy(v[0]);yield;<-r};
            drop(->v);yield;return r.x;'''
        self.assertEqual(self.run_source(self.launch(body)).stdout, '7\n')

    def test_empty_struct(self):
        source=self.launch('''let mut p=pool<Vector<Empty>>(1);let mut v=p.new();v.push(->Empty{});
            yield;let e=<-v.remove(0);drop(->e);return v.len();''','struct Empty{}')
        self.assertEqual(self.run_source(source).stdout, '0\n')


if __name__ == '__main__':
    unittest.main()
