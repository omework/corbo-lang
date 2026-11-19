"""Typed replace/try_push results preserve their own handle and source per arm."""
import struct
import unittest
import test_select_source as harness

REPLACE='Result<A<Point>,A<Point>>'
PUSH='Result<(),A<Point>>'
ACTION='let r=<-v.replace(INDEX,->incoming);'
READ='match (->r){Ok(old)=>{print(old.x);drop(->old);},Err(rejected)=>{print(rejected.x);drop(->rejected);}}'
BASE='''struct Point{x:Int}fn main(){let mut p=pool<Point>(1);let mut q=pool<Point>(1);
    let mut vectors=pool<Vector<A<Point>>>(1);let mut v=vectors.new();
    let first=p.new(x:7);v.push(->first);let incoming=q.new(x:9);
    ACTION READ
    let current=<-v.remove(0);print(current.x);drop(->current);drop(->v);
    let a=p.new(x:10);let b=q.new(x:11);print(a.x);print(b.x);}'''.replace('ACTION',ACTION).replace('READ',READ)


def filled(source):
    limit=1048576//struct.calcsize('P')
    source=source.replace('fn main(){','fn main(){#(directive, stack_region_max_size=1M) {')
    source=source.replace('let incoming=p.new(x:9);',f'''let mut fill=pool<Point>({limit});
        let mut i=0;while i<{limit}{{v.push(->fill.new(x:1));i=i+1;}}
        let incoming=p.new(x:9);''')
    return source+'}'


class TypedVectorExchangeTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused

    def test_replace_direct_named_and_moved(self):
        for action in (ACTION, ACTION.replace('let r=',f'let r:{REPLACE}='),
                       ACTION.replace('let r=','let initial=')+'let r=<-initial;'):
            for index,expected in ((0,'7\n9\n10\n11\n'),(4,'9\n7\n10\n11\n')):
                source=BASE.replace(ACTION,action).replace('INDEX',str(index))
                run=self.run_source(source)
                self.assertEqual(run.stdout,expected)
                self.assertEqual(run.stderr.count('destroy first=Point\n'),1)
                self.assertEqual(run.stderr.count('destroy incoming=Point\n'),1)

    def test_returned_and_relayed_result(self):
        helpers=f'''fn exchange(v:&mut Vector<A<Point>>,next:->A<Point>,i:Int)-><-{REPLACE}{{
                return <-v.replace(i,->next);}}
            fn relay(r:->{REPLACE})-><-{REPLACE}{{return <-r;}}'''
        source=helpers+BASE.replace(ACTION,'let r=relay(->exchange(&mut v,->incoming,INDEX));')
        for index,expected in ((0,'7\n9\n10\n11\n'),(4,'9\n7\n10\n11\n')):
            self.assertEqual(self.run_source(source.replace('INDEX',str(index))).stdout,expected)

        self.refused(source.replace('INDEX','0').replace('relay(->exchange','relay(exchange'),'transfert|->|mode attendu')

    def test_consumer_returns_handle_from_either_arm(self):
        helper=f'''fn take(r:->{REPLACE})-><-A<Point>{{match (->r){{
            Ok(n)=>{{return <-n;}},Err(n)=>{{return <-n;}}}}}}'''
        source=helper+BASE.replace(READ,'let item=take(->r);print(item.x);drop(->item);')
        for index,expected in ((0,'7\n9\n10\n11\n'),(4,'9\n7\n10\n11\n')):
            self.assertEqual(self.run_source(source.replace('INDEX',str(index))).stdout,expected)
        self.refused(source.replace('INDEX','0').replace('return <-n;',
            'let local:Point=<-n;return <-local;'),'stockage|local|A<T>')

    def test_immediate_consuming_match(self):
        direct=BASE.replace(ACTION+' '+READ,'match <-v.replace(INDEX,->incoming)'+READ.split(')',1)[1])
        for index,expected in ((0,'7\n9\n10\n11\n'),(4,'9\n7\n10\n11\n')):
            self.assertEqual(self.run_source(direct.replace('INDEX',str(index))).stdout,expected)

    def test_growing_payloads_through_typed_result(self):
        for typ,fill,read in (
            ('String','value.push_str("hello");','print(&item[..]);'),
            ('Vector<Int>','value.push(7);','print(item[0]);'),
            ('Vector<u8>','let byte:u8=7;value.push(byte);','print(item[0] as Int);'),
        ):
            result=f'Result<A<{typ}>,A<{typ}>>'
            source=f'''fn exchange(v:&mut Vector<A<{typ}>>,n:->A<{typ}>,i:Int)-><-{result}{{return <-v.replace(i,->n);}}
                fn main(){{let mut p=pool<{typ}>(2);let mut vp=pool<Vector<A<{typ}>>>(1);
                let mut v=vp.new();let mut value=p.new();{fill}v.push(->value);
                let mut next=p.new();{fill.replace('value','next').replace('byte','next_byte')}let r=exchange(&mut v,->next,INDEX);
                match (->r){{Ok(item)=>{{{read}drop(->item);}},Err(item)=>{{{read}drop(->item);}}}}
                drop(->v);let a=p.new();let b=p.new();drop(->a);drop(->b);}}'''
            for index in (0,4):
                with self.subTest(typ=typ,index=index):
                    self.assertEqual(self.run_source(source.replace('INDEX',str(index))).stdout,'hello\n' if typ=='String' else '7\n')

    def test_direct_drop_and_branch_results(self):
        for expression in (
            'drop(->v.replace(INDEX,->incoming));',
            'let r=if true{incoming ->;let x=<-v.replace(INDEX,->incoming);<-x}else{incoming ->;let x=<-v.replace(INDEX,->incoming);<-x};drop(->r);',
            'let r=loop{incoming ->;let x=<-v.replace(INDEX,->incoming);break <-x;};drop(->r);',
        ):
            for index,expected in ((0,'9\n10\n11\n'),(4,'7\n10\n11\n')):
                source=BASE.replace(ACTION+ ' '+READ,expression).replace('INDEX',str(index))
                self.assertEqual(self.run_source(source).stdout,expected)

    def test_try_push_both_outcomes_through_contract(self):
        helpers=f'''struct Point{{x:Int}}
            fn append(v:&mut Vector<A<Point>>,n:->A<Point>)-><-{PUSH}{{return <-v.try_push(->n);}}
            fn relay(r:->{PUSH})-><-{PUSH}{{return <-r;}}'''
        source=helpers+'''fn main(){let mut p=pool<Point>(1);let mut vp=pool<Vector<A<Point>>>(1);
            let mut v=vp.new();let incoming=p.new(x:9);
            let r=relay(->append(&mut v,->incoming));
            match (->r){Ok(())=>{print(1);},Err(rejected)=>{print(rejected.x);drop(->rejected);}}
            drop(->v);let next=p.new(x:10);print(next.x);}'''
        for program,expected in ((source,'1\n10\n'),(filled(source),'9\n10\n')):
            run=self.run_source(program)
            self.assertEqual(run.stdout,expected)
            self.assertEqual(run.stderr.count('destroy incoming=Point\n'),1)
        direct=source.replace('let r=relay(->append(&mut v,->incoming));\n            match (->r){Ok(())=>{print(1);},Err(rejected)=>{print(rejected.x);drop(->rejected);}}',
            'drop(->v.try_push(->incoming));')
        for program in (direct,filled(direct)):
            self.assertEqual(self.run_source(program).stdout,'10\n')

    def test_type_transfer_and_result_usage(self):
        source=BASE.replace('INDEX','0')
        self.refused(source.replace('replace(0,->incoming)','replace(0,incoming)'),'transfert|->')
        self.refused(source.replace(READ,''),'sans usage explicite')
        self.refused(source.replace(READ,'drop(->r);drop(->r);'),'utilisable|consomm')
        self.refused(source.replace('let r=',f'let r:{PUSH}='),'annotation|type|incompatible')
        self.refused(source.replace('let r=','let r:Result<A<Int>,A<Int>>='),'annotation|type|incompatible')
        self.refused(source.replace('Ok(old)=>{print(old.x);drop(->old);}','Ok(_)=>{}'),'motif|allocation|usage')

    def test_separate_arm_can_escape_short_other_pool(self):
        helpers=f'''struct Point{{x:Int}}
            fn exchange(v:&mut Vector<A<Point>>,next:->A<Point>,i:Int)-><-{REPLACE}{{return <-v.replace(i,->next);}}
            fn take(v:&mut Vector<A<Point>>,next:->A<Point>,p:&mut Pool<Point>,i:Int)-><-A<Point>{{
                let r=exchange(&mut *v,->next,i);match (->r){{Ok(old)=>{{return <-old;}},
                Err(rejected)=>{{drop(->rejected);let fallback=p.new(x:17);return <-fallback;}}}}}}'''
        main='''fn main(){let mut p=pool<Point>(2);let result={let mut q=pool<Point>(1);
            let mut vp=pool<Vector<A<Point>>>(1);let mut v=vp.new();v.push(->p.new(x:7));
            let next=q.new(x:9);let r=take(&mut v,->next,&mut p,INDEX);<-r};
            print(result.x);drop(->result);let reused=p.new(x:20);print(reused.x);}'''
        for index,expected in ((0,'7\n20\n'),(4,'17\n20\n')):
            self.assertEqual(self.run_source(helpers+main.replace('INDEX',str(index))).stdout,expected)
        invalid=(helpers+main.replace('INDEX','0')).replace('v.push(->p.new(x:7))','v.push(->q.new(x:7))').replace('q=pool<Point>(1)','q=pool<Point>(2)')
        self.refused(invalid,'source|pool|survi')


if __name__=='__main__':unittest.main()
