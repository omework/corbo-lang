"""Vector handles retain the borrowed/owned graph of each payload."""
from pathlib import Path
import unittest
import test_select_source as harness

BASE = Path(__file__).resolve().parents[1].joinpath('validation/open-vector-handle-borrowed-fields.crb').read_text()
EXTRACT = 'let extracted=<-values.remove(0);'
READ = 'print(*extracted.value);drop(->extracted);'


class VectorPayloadGraphTests(unittest.TestCase):
    run_source = harness.SelectSourceTests.run_source
    run_c_oracle = harness.SelectSourceTests.run_c_oracle
    refused = harness.SelectSourceTests.refused

    def test_remove_preserves_borrow_and_reuses_slots(self):
        self.assertEqual(self.run_source(BASE).stdout, '7\n9\n')
        for before in (EXTRACT, READ):
            invalid = BASE.replace('drop(->number);', '').replace(before, 'drop(->number);'+before)
            self.refused(invalid, 'emprunt|réserv|référenc')
        self.refused(BASE.replace(EXTRACT, 'print(*item.value);'+EXTRACT), 'utilisable|déplac')

    def test_pop_direct_buffered_and_joined(self):
        for expression in ('values.pop()',
                           'if true{let r=<-values.pop();<-r}else{let r=<-values.pop();<-r}',
                           'loop{let r=<-values.pop();break <-r;}'):
            source=BASE.replace(EXTRACT, 'let result=<-'+expression+';' if expression=='values.pop()' else 'let result='+expression+';').replace(
                READ, 'match (->result){Some(extracted)=>{'+READ+'},None=>{print(0);}}')
            self.assertEqual(self.run_source(source).stdout, '7\n9\n')
            invalid=source.replace('drop(->number);','').replace('match (->result)', 'drop(->number);match (->result)')
            self.refused(invalid, 'emprunt|réserv|référenc')
        direct=BASE.replace(EXTRACT,'').replace(READ,'match <-values.pop(){Some(extracted)=>{'+READ+'},None=>{print(0);}}')
        self.assertEqual(self.run_source(direct).stdout, '7\n9\n')

    def test_nested_owned_cleanup_and_borrow(self):
        source='''struct Inner{value:&Int}struct Item{inner:A<Inner>}
            fn read(i:&Inner)->Int{return *i.value;}
            fn main(){let mut numbers=pool<Int>(1);let number=numbers.new(7);
            let mut inners=pool<Inner>(1);let mut items=pool<Item>(1);
            let inner=inners.new(value:&number);let item=items.new(inner:<-inner);
            let mut vectors=pool<Vector<A<Item>>>(1);let mut values=vectors.new();values.push(->item);
            let extracted=<-values.remove(0);print(read(&*extracted.inner));drop(->extracted);
            let next=inners.new(value:&number);let next_item=items.new(inner:<-next);drop(->next_item);
            drop(->values);drop(->number);let reused=numbers.new(9);print(*reused);}'''
        run=self.run_source(source)
        self.assertEqual(run.stdout,'7\n9\n')
        self.assertEqual(run.stderr.count('=Inner\n'),2)
        self.assertEqual(run.stderr.count('=Item\n'),2)
        self.refused(source.replace('drop(->number);','').replace('let extracted=', 'drop(->number);let extracted='),'emprunt|réserv|référenc')
        self.refused(source.replace('drop(->number);','').replace('print(read(', 'drop(->number);print(read('),'emprunt|réserv|référenc')
        self.assertEqual(self.run_source(source.replace('let extracted=<-values.remove(0);print(read(&*extracted.inner));drop(->extracted);', 'drop(->values);').replace('drop(->values);drop(->number);','drop(->number);')).stdout,'9\n')

    def test_mutable_payload_reserves_target(self):
        source=BASE.replace('value:&Int','value:&mut Int').replace('let number=','let mut number=').replace('value:&number','value:&mut number')
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        for operation in ('print(*number);','number=21;', 'drop(->number);'):
            candidate=source.replace('drop(->number);','') if operation.startswith('drop') else source
            for marker in (EXTRACT,READ):
                self.refused(candidate.replace(marker,operation+marker),'emprunt|réserv|référenc')

    def test_replace_results_keep_selected_graph(self):
        prefix='''struct Item{value:&Int}fn main(){let mut ns=pool<Int>(2);
            let a=ns.new(7);let b=ns.new(9);let mut p=pool<Item>(2);
            let mut vp=pool<Vector<A<Item>>>(1);let mut v=vp.new();
            v.push(->p.new(value:&a));let incoming=p.new(value:&b);'''
        for index,expected in ((0,'7\n9\n'),(3,'9\n7\n')):
            body=f'''let result=<-v.replace({index},->incoming);
                match (->result){{Ok(old)=>{{print(*old.value);drop(->old);}},Err(back)=>{{print(*back.value);drop(->back);}}}}
                let last=<-v.remove(0);print(*last.value);drop(->last);drop(->v);drop(->a);drop(->b);'''
            self.assertEqual(self.run_source(prefix+body+'}').stdout,expected)
            for target in ('a','b'):
                invalid=body.replace('drop(->'+target+');','').replace('match (->result)','drop(->'+target+');match (->result)')
                self.refused(prefix+invalid+'}', 'emprunt|réserv|référenc')

    def test_transfer_checks_target_and_child_pool_lifetimes(self):
        source='''struct Item{value:&Int}fn main(){let mut ns=pool<Int>(1);let n=ns.new(7);
            let mut p=pool<Item>(1);let mut vp=pool<Vector<A<Item>>>(1);
            let result={let mut v=vp.new();v.push(->p.new(value:&n));<-v};
            let mut values=<-result;let extracted=<-values.remove(0);print(*extracted.value);
            drop(->extracted);drop(->values);drop(->n);}'''
        self.assertEqual(self.run_source(source).stdout,'7\n')
        for decl in ('let mut ns=pool<Int>(1);let n=ns.new(7);','let mut p=pool<Item>(1);'):
            invalid=source.replace(decl,'').replace('let result={','let result={'+decl).replace('drop(->n);','')
            self.refused(invalid,'pool|source|survi|emprunt|référenc|scope')

    def test_function_returns_extracted_payload_with_contract(self):
        helper = """struct Item{value:&Int}
            fn roundtrip(p:&mut Pool<Item>,n:&Int)-><-A<Item>{
            let mut vp=pool<Vector<A<Item>>>(1);let mut v=vp.new();
            v.push(->p.new(value:n));return <-v.remove(0);}
            fn relay(p:&mut Pool<Item>,n:&Int)-><-A<Item>{return <-roundtrip(p,n);}"""
        for call in ('roundtrip', 'relay'):
            source=helper+f"""fn main(){{let mut ns=pool<Int>(1);let n=ns.new(7);let mut p=pool<Item>(1);
                let result={call}(&mut p,&n);print(*result.value);drop(->result);drop(->n);
                let next=ns.new(9);print(*next);}}"""
            self.assertEqual(self.run_source(source).stdout,'7\n9\n')
            self.refused(source.replace('drop(->n);','').replace('print(*result.value);','drop(->n);print(*result.value);'),'emprunt|réserv|référenc')

    def test_loop_and_precise_removal(self):
        source="""struct Item{value:&Int}fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
            let mut p=pool<Item>(2);let mut vp=pool<Vector<A<Item>>>(1);let mut v=vp.new();
            v.push(->p.new(value:&a));v.push(->p.new(value:&b));
            let first=<-v.remove(0);print(*first.value);drop(->first);drop(->a);
            let second=<-v.remove(0);print(*second.value);drop(->second);
            let mut i=0;while i<3{v.push(->p.new(value:&b));let item=<-v.remove(0);
                print(*item.value);drop(->item);i=i+1;}
            drop(->v);drop(->b);}"""
        self.assertEqual(self.run_source(source).stdout,'7\n9\n9\n9\n9\n')
        self.refused(source.replace('drop(->b);','').replace('let first=', 'drop(->b);let first='),'emprunt|réserv|référenc')

    def test_try_push_and_immediate_cleanup(self):
        source=BASE.replace('values.push(->item);'+EXTRACT,
            'let r=<-values.try_push(->item);match (->r){Ok(())=>{},Err(back)=>{drop(->back);}}'+EXTRACT)
        self.assertEqual(self.run_source(source).stdout,'7\n9\n')
        self.refused(source.replace('drop(->number);','').replace('match (->r)','drop(->number);match (->r)'),'emprunt|réserv|référenc')
        for operation in ('values.remove(0)', 'values.pop()'):
            source=BASE.replace(EXTRACT,'').replace(READ, 'drop(->'+operation+');')
            self.assertEqual(self.run_source(source).stdout,'9\n')

    def test_transferred_vector_branch_and_loop(self):
        for expression in ('if true{item ->;let mut v=vectors.new();v.push(->item);<-v}else{item ->;let mut v=vectors.new();v.push(->item);<-v}',
                           'loop{item ->;let mut v=vectors.new();v.push(->item);break <-v;}'):
            source=BASE.replace('let mut values=vectors.new();\n    values.push(->item);', 'let mut values='+expression+';')
            self.assertNotEqual(source,BASE)
            self.assertEqual(self.run_source(source).stdout,'7\n9\n')
            self.refused(source.replace('drop(->number);','').replace(EXTRACT,'drop(->number);'+EXTRACT),'emprunt|réserv|référenc')

    def test_borrowed_slot_replacement_updates_payload(self):
        source="""struct Item{value:&Int}fn main(){let mut ns=pool<Int>(2);let a=ns.new(7);let b=ns.new(9);
            let mut p=pool<Item>(2);let mut vp=pool<Vector<A<Item>>>(1);let mut v=vp.new();
            v.push(->p.new(value:&a));let incoming=p.new(value:&b);
            let mut slot=&mut v[0];*slot=<-incoming;drop(->a);
            let extracted=<-v.remove(0);print(*extracted.value);drop(->extracted);drop(->v);drop(->b);}"""
        run=self.run_source(source)
        self.assertEqual(run.stdout,'9\n')
        self.assertEqual(run.stderr.count('=Item\n'),2)
        for marker in ('let extracted=', 'print(*extracted.value);'):
            self.refused(source.replace('drop(->b);','').replace(marker,'drop(->b);'+marker),'emprunt|réserv|référenc')


if __name__=='__main__':unittest.main()
