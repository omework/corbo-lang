"""Structural requirements on actual builtin operations, with concrete contracts."""
import unittest
from crust import Error, verify_program
import test_type_features


class BuiltinFeatureTests(unittest.TestCase):
    native = test_type_features.TypeFeatureTests.native

    def test_vector_and_fixed_array_readers_resolve_independently(self):
        source='''
            type feature Length{fn len(&self)->Int;}
            fn count(v:&Length)->Int{return v.len();}
            fn both(a:&Length,b:&Length)->Int{return count(a)+count(b);}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();v.push(7);
                let a=[1,2,3];print(both(&v,&a));
                let mut bytes=pool<Vector<u8>>(1);let b=bytes.new();print(count(&b));
                let mut handles=pool<Vector<A<Int>>>(1);let h=handles.new();print(count(&h));}
        '''
        self.assertEqual(self.native(source).stdout,'4\n0\n0\n')
        with self.assertRaisesRegex(Error,'exigence de feature'):
            verify_program(source.replace('fn len(&self)->Int','fn len(&mut self)->Int').replace('return v.len();','return 1;'))

    def test_vector_mutation_and_element_type_requirements(self):
        source='''
            type feature Append{fn push(&mut self,n:Int);}
            fn append(mut v:&mut Append,n:Int){v.push(n);}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();
                append(&mut v,7);print(v[0]);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        with self.assertRaisesRegex(Error,'exigence de feature'):
            verify_program(source.replace('Vector<Int>','Vector<u8>'))
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('append(&mut v,7);','let r=&v;append(&mut v,7);print(r.len());'))

    def test_push_new_result_retains_mutable_reservation(self):
        source='''
            type feature AppendZero{fn push_new(&mut self)->&mut Int;}
            fn append(mut v:&mut AppendZero)->&mut Int{return v.push_new();}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();
                let mut cell=append(&mut v);cell.set(7);print(v[0]);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        for before in ('print(v.len());','drop(-> v);'):
            with self.subTest(before=before),self.assertRaisesRegex(Error,'emprunt'):
                verify_program(source.replace('cell.set(7);',before+'cell.set(7);'))

    def test_fallible_vector_result_requires_explicit_use(self):
        source='''
            type feature TryAppend{fn try_push(&mut self,n:Int)->Result<(),Int>;}
            fn append(mut v:&mut TryAppend,n:Int)->Result<(),Int>{return v.try_push(n);}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();
                drop(-> append(&mut v,7));print(v[0]);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        for statement in ('append(&mut v,7);','let unused=append(&mut v,7);'):
            with self.subTest(statement=statement),self.assertRaisesRegex(Error,'usage|receveur|utilisé'):
                verify_program(source.replace('drop(-> append(&mut v,7));',statement))

    def test_string_and_str_normalize_borrow_modes_and_nested_receivers(self):
        source='''
            type feature Length{fn byte_len(&self)->Int;}
            fn identity(t:&Length)->&Length{return t;}
            fn measure(t:&Length)->Int{return identity(t).byte_len();}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("été");
                print(measure(&s));print(measure("é"));}
        '''
        self.assertEqual(self.native(source).stdout,'5\n2\n')

    def test_parser_lowered_method_cannot_bypass_abstract_guarantee(self):
        prefix='''type feature Length{fn byte_len(&self)->Int;}
            fn identity(t:&Length)->&Length{return t;}'''
        for body in ('drop(-> t.try_slice(0..1));',
                     'drop(-> identity(t).char_at(0));',
                     'drop(-> identity(t).try_slice(0..1));'):
            with self.subTest(body=body),self.assertRaisesRegex(Error,'non garantie'):
                verify_program(prefix+'fn bad(t:&Length){'+body+'}fn main(){}')

    def test_slice_result_preserves_borrow_through_generic_relay(self):
        source='''
            type feature Slice{fn try_slice(&self,start:Int,end:Int)->Result<&str,SliceError>;}
            fn cut(t:&Slice)->Result<&str,SliceError>{return t.try_slice(0..2);}
            fn relay(t:&Slice)->Result<&str,SliceError>{return cut(t);}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("é!");
                let result=relay(&s);
                match result{Ok(view)=>{print(view);},Err(_)=>{print("error");}}
                s.push_str("x");print(&s[..]);}
        '''
        self.assertEqual(self.native(source).stdout,'é\né!x\n')
        for bad in ('drop(-> s);','s.push_str("x");'):
            with self.subTest(bad=bad),self.assertRaisesRegex(Error,'emprunt'):
                verify_program(source.replace('match result',bad+'match result'))
        literal=source[:source.index('fn main()')]+'''fn main(){let result=relay("é!");
            match result{Ok(view)=>{print(view);},Err(_)=>{print("error");}}}'''
        self.assertEqual(self.native(literal).stdout,'é\n')

    def test_decoded_char_result_does_not_keep_source_borrow(self):
        source='''
            type feature Decode{fn char_at(&self,index:Int)->Result<char,CharAtError>;}
            fn decode(t:&Decode)->Result<char,CharAtError>{return t.char_at(0);}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("é");
                let view=&s[..];let result=decode(view);drop(-> s);
                match result{Ok(c)=>{print(c.utf8_len());},Err(_)=>{print(0);}}}
        '''
        self.assertEqual(self.native(source).stdout,'2\n')

    def test_string_mutator_preserves_alias_conflicts_and_result_atomicity(self):
        source='''
            type feature Append{fn push_str(&mut self,text:&str);}
            fn append(mut s:&mut Append,text:&str){s.push_str(text);}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("é");
                append(&mut s,"!");print(&s[..]);}
        '''
        self.assertEqual(self.native(source).stdout,'é!\n')
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('append(&mut s,"!");','let view=&s[..];append(&mut s,view);'))
        source='''
            type feature Replace{fn replace_byte(&mut self,index:Int,value:u8)->Result<u8,ByteReplaceError>;}
            fn change(mut s:&mut Replace,value:u8)->Result<u8,ByteReplaceError>{return s.replace_byte(0,value);}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("é");
                let value:u8=65;let result=change(&mut s,value);
                match result{Ok(old)=>{print(old as Int);},Err(_)=>{print("invalid");}}print(&s[..]);}
        '''
        self.assertEqual(self.native(source).stdout,'invalid\né\n')

    def test_string_merge_consumes_source_and_reuses_its_slot(self):
        source='''
            type feature Merge{fn merge(&mut self,other:-> String);}
            fn merge(mut s:&mut Merge,other:-> String){s.merge(-> other);}
            fn main(){let mut p=pool<String>(2);let mut a=p.new();a.push_str("a");
                let mut b=p.new();b.push_str("é");address(b);merge(&mut a,-> b);
                let next=p.new();address(next);print(&a[..]);}
        '''
        result=self.native(source);before,after,text=result.stdout.splitlines()
        self.assertEqual((before,text),(after,'aé'))
        self.assertEqual(result.stderr.count('destroy b=0'),1)
        with self.assertRaisesRegex(Error,'plus utilisable'):
            verify_program(source.replace('let next=', 'print(&b[..]);let next='))

    def test_pool_constructor_feature_keeps_source_contract(self):
        source='''
            type feature Create{fn new(&mut self,n:Int)-><- A<Int>;}
            fn create(p:&mut Create)-><- A<Int>{let result=p.new(7);return <- result;}
            fn relay(p:&mut Create)-><- A<Int>{let result=create(p);return <- result;}
            fn main(){let mut p=pool<Int>(1);let result=relay(&mut p);print(*result);
                address(result);drop(-> result);let next=p.new(9);address(next);print(*next);}
        '''
        result=self.native(source);first,before,after,last=result.stdout.splitlines()
        self.assertEqual((first,before,last),('7',after,'9'))
        with self.assertRaisesRegex(Error,'exigence de feature'):
            verify_program(source.replace('pool<Int>','pool<String>'))
        bad=source[:source.index('fn main()')]+'''fn main(){let result={let mut p=pool<Int>(1);
            let value=create(&mut p);<- value};print(*result);}'''
        with self.assertRaisesRegex(Error,'survit|source'):
            verify_program(bad)

    def test_fixed_array_mutator_keeps_value_and_borrow_contract(self):
        source='''
            type feature Replace{fn replace(&mut self,index:Int,value:Int)->Int;}
            fn change(mut a:&mut Replace)->Int{return a.replace(0,9);}
            fn main(){let mut a=[1,2];print(change(&mut a));print(a[0]);}
        '''
        self.assertEqual(self.native(source).stdout,'1\n9\n')
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('print(change(&mut a));','let view=&a[0];print(change(&mut a));print(*view);'))

    def test_returned_string_reference_preserves_targets_and_pending_arguments(self):
        source='''
            type feature Length{fn byte_len(&self)->Int;}
            fn identity(s:&Length)->&Length{return s;}
            fn main(){let mut p=pool<String>(1);let mut s=p.new();s.push_str("é!");
                let result=identity(&s).try_slice(0..2);
                match result{Ok(view)=>{print(view);},Err(_)=>{print("error");}}
                drop(-> s);let next=p.new();print(next.byte_len());}
        '''
        self.assertEqual(self.native(source).stdout,'é\n0\n')
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('match result','drop(-> s);match result').replace('drop(-> s);let next','let next'))
        reset='fn clear(p:&mut Pool<String>)->Int{p.reset();return 2;}'
        with self.assertRaisesRegex(Error,'reset|emprunt'):
            verify_program(reset+source.replace('try_slice(0..2)','try_slice(0..clear(&mut p))'),allow_legacy_reset=True)
        with self.assertRaisesRegex(Error,'survit|local|emprunt'):
            verify_program('''fn escape()->&String{let mut p=pool<String>(1);let s=p.new();return &s;}
                fn main(){let r=escape();print(r.byte_len());}''')

    def test_returned_vector_reference_keeps_exclusivity(self):
        source='''
            type feature Append{fn push(&mut self,n:Int);}
            fn identity(mut v:&mut Append)->&mut Append{return v;}
            fn main(){let mut p=pool<Vector<Int>>(1);let mut v=p.new();
                let mut alias=identity(&mut v);alias.push(7);print(v[0]);}
        '''
        self.assertEqual(self.native(source).stdout,'7\n')
        for forbidden in ('v.push(9);','drop(-> v);'):
            with self.subTest(forbidden=forbidden),self.assertRaisesRegex(Error,'emprunt'):
                verify_program(source.replace('alias.push(7);',forbidden+'alias.push(7);'))

    def test_builtin_signature_boundaries_against_source_level_model(self):
        for operation in ('len','push'):
            for receiver in ('&self','&mut self','-> self'):
                for variant in range(3):
                    for returns_value in (False,True):
                        if operation=='len':
                            arguments=('',',n:Int',',n:u8')[variant]
                            admitted=(receiver=='&self' and variant==0 and returns_value)
                        else:
                            arguments=(',n:Int',',n:u8',',n:&Int')[variant]
                            admitted=(receiver=='&mut self' and variant==0 and not returns_value)
                        result='->Int' if returns_value else ''
                        source=f'''
                            type feature Requirement{{fn {operation}({receiver}{arguments}){result};}}
                            fn accept(v:&Requirement){{print(1);}}
                            fn main(){{let mut p=pool<Vector<Int>>(1);let v=p.new();accept(&v);}}
                        '''
                        with self.subTest(operation=operation,receiver=receiver,variant=variant,result=result):
                            if admitted:
                                self.assertEqual(self.native(source).stdout,'1\n')
                            else:
                                with self.assertRaisesRegex(Error,'exigence de feature'):
                                    verify_program(source)

    def test_fixed_array_feature_result_keeps_concrete_shape_and_target(self):
        source='''
            type feature Length{fn len(&self)->Int;}
            fn identity(a:&Length)->&Length{return a;}
            fn main(){let mut a=[1,2,3];let result=identity(&a);print(result.len());print(result[0]);}
        '''
        self.assertEqual(self.native(source).stdout,'3\n1\n')
        with self.assertRaisesRegex(Error,'emprunt'):
            verify_program(source.replace('print(result.len());','a[0]=7;print(result.len());'))


if __name__=='__main__':
    unittest.main()
