"""Optional handles keep their type even when the payload is statically absent."""
from pathlib import Path
import unittest
import test_select_source as harness

BASE=Path(__file__).resolve().parents[1].joinpath('validation/open-typed-vector-option-contract.crb').read_text()
READ='match (->result){Some(n)=>{print(n.x);drop(->n);},None=>{print(0);}}'
FILL='v.push(->p.new(x:7));'


class TypedVectorOptionTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_some_none_annotated_and_relayed(self):
        helper='fn relay(r:->Option<A<Point>>)-><-Option<A<Point>>{return <-r;}'
        source=helper+BASE.replace('let result=pop(&mut v);',
            'let original:Option<A<Point>>=pop(&mut v);let result=relay(->original);')
        for filled,expected in ((True,'7\n9\n'),(False,'0\n9\n')):
            candidate=source if filled else source.replace(FILL,'')
            self.assertEqual(self.run_source(candidate).stdout,expected)
            self.refused(candidate.replace('let original:Option<A<Point>>','let original:Option<A<Int>>'),'annotation|type|attendu')
        self.refused(source.replace('relay(->original)','relay(original)'),'mode attendu|transfert|->')

    def test_slot_borrow_ends_before_pop(self):
        helper='''fn compare(h:&A<Point>,p:&mut Pool<Point>)->bool{
            let expected=p.new(x:7);return expected.vequals(h);}'''
        before='let mut q=pool<Point>(1);let loan=&v[0];if compare(loan,&mut q){print(1);}'
        source=helper+BASE.replace('let result=pop(&mut v);',before+'let result=pop(&mut v);')
        self.assertEqual(self.run_source(source).stdout,'1\n7\n9\n')
        invalid=source.replace('if compare(loan,&mut q){print(1);}','').replace(READ,
            'if compare(loan,&mut q){print(1);}'+READ)
        self.refused(invalid,'emprunt actif|emprunt|réserv')

    def test_none_keeps_type_in_argument(self):
        helper='fn consume(r:->Option<A<Int>>){drop(->r);}'
        source=helper+BASE.replace(FILL,'').replace(READ,'consume(->result);')
        self.refused(source,'attend|type|Int')
        self.assertEqual(self.run_source(source.replace('consume(r:->Option<A<Int>>','consume(r:->Option<A<Point>>')).stdout,'9\n')

    def test_conditional_and_loop_results(self):
        for expression in (
            'if true{let r=<-v.pop();<-r}else{let r=<-v.pop();<-r}',
            'loop{let r=<-v.pop();break <-r;}',
        ):
            source=BASE.replace('pop(&mut v);',expression+';')
            for filled,expected in ((True,'7\n9\n'),(False,'0\n9\n')):
                self.assertEqual(self.run_source(source if filled else source.replace(FILL,'')).stdout,expected)
        invalid='''struct Point{x:Int}fn main(){let mut vp=pool<Vector<A<Point>>>(1);
            let mut vi=pool<Vector<A<Int>>>(1);let mut a=vp.new();let mut b=vi.new();
            let result=if true{let r=<-a.pop();<-r}else{let r=<-b.pop();<-r};drop(->result);}'''
        self.refused(invalid,'même type|type.*branches|Int.*Point|Point.*Int')

    def test_result_outlives_vector_but_not_payload_pool(self):
        source='''struct Point{x:Int}
            fn take(v:&mut Vector<A<Point>>)-><-Option<A<Point>>{return <-v.pop();}
            fn main(){let mut p=pool<Point>(1);let result={let mut vp=pool<Vector<A<Point>>>(1);
                let mut v=vp.new();v.push(->p.new(x:7));let r=take(&mut v);<-r};
                match (->result){Some(n)=>{print(n.x);drop(->n);},None=>{print(0);}}
                let reused=p.new(x:9);print(reused.x);}'''
        for filled,expected in ((True,'7\n9\n'),(False,'0\n9\n')):
            self.assertEqual(self.run_source(source if filled else source.replace(FILL,'')).stdout,expected)
        invalid=source.replace('let mut p=pool<Point>(1);let result={','let result={let mut p=pool<Point>(1);').replace(
            'let reused=p.new(x:9);print(reused.x);','')
        self.refused(invalid,'pool|source|survi')

    def test_consumer_returns_typed_payload(self):
        helper='''fn consume(r:->Option<A<Point>>,p:&mut Pool<Point>)-><-A<Point>{
            match (->r){Some(n)=>{return <-n;},None=>{let fallback=p.new(x:17);return <-fallback;}}}'''
        source=helper+BASE.replace(READ,'let n=consume(->result,&mut p);print(n.x);drop(->n);')
        for filled,expected in ((True,'7\n9\n'),(False,'17\n9\n')):
            self.assertEqual(self.run_source(source if filled else source.replace(FILL,'')).stdout,expected)
        self.refused(source.replace('return <-n;','let local:Point=<-n;return <-local;'),'stockage|local|Option')

    def test_drop_results_and_explicit_usage(self):
        for action in ('drop(->pop(&mut v));','let r=pop(&mut v);let moved=<-r;drop(->moved);','drop(->v.pop());'):
            source=BASE.replace('let result=pop(&mut v);\n'+READ,action)
            for filled in (True,False):
                self.assertEqual(self.run_source(source if filled else source.replace(FILL,'')).stdout,'9\n')
        self.refused(BASE.replace(READ,''),'sans usage explicite')
        self.refused(BASE.replace(READ,'drop(->result);drop(->result);'),'utilisable|consomm')
        self.refused(BASE.replace('Some(n)=>{print(n.x);drop(->n);}','Some(_)=>{}'),'motif|allocation|usage')

    def test_growing_payloads(self):
        for typ,fill,read in (
            ('String','item.push_str("hello");','print(&item[..]);'),
            ('Vector<Int>','item.push(7);','print(item[0]);'),
            ('Vector<u8>','let byte:u8=7;item.push(byte);','print(item[0] as Int);'),
        ):
            source=f'''fn take(v:&mut Vector<A<{typ}>>)-><-Option<A<{typ}>>{{return <-v.pop();}}
                fn main(){{let mut p=pool<{typ}>(1);let mut vp=pool<Vector<A<{typ}>>>(1);
                let mut v=vp.new();let mut item=p.new();{fill}v.push(->item);
                let result=take(&mut v);match (->result){{Some(item)=>{{{read}drop(->item);}},None=>{{print(0);}}}}
                drop(->v);let reused=p.new();drop(->reused);}}'''
            self.assertEqual(self.run_source(source).stdout,'hello\n' if typ=='String' else '7\n')


if __name__=='__main__':unittest.main()
