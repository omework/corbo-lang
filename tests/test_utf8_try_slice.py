"""TX4: byte-range oracle, evaluation order and borrowed Result lifetimes."""
import unittest

import test_foundation_rules
from crust import Error, compile_source, verify_program


class TrySliceTests(unittest.TestCase):
    native = test_foundation_rules.FoundationTests.native

    def test_ranges_match_independent_unicode_prefix_model(self):
        text = 'été🌍'
        raw = text.encode('utf-8')
        boundaries = {len(text[:i].encode('utf-8')) for i in range(len(text) + 1)}
        expected = []
        for lo in range(-1, len(raw) + 2):
            for hi in range(-1, len(raw) + 2):
                if not 0 <= lo <= hi <= len(raw):
                    expected.append('OUT')
                elif lo not in boundaries or hi not in boundaries:
                    expected.append('CUT')
                else:
                    expected.append(raw[lo:hi].decode('utf-8'))
        run = self.native('''
            fn cut(text:&str, lo:Int, hi:Int)->Result<&str,SliceError> {
                return text.try_slice(lo..hi);
            }
            fn relay(text:&str, lo:Int, hi:Int)->Result<&str,SliceError> {
                return cut(text,lo,hi);
            }
            fn main() {
                let mut lo=-1;
                while lo < 11 {
                    let mut hi=-1;
                    while hi < 11 {
                        match relay("été🌍",lo,hi) {
                            Err(SliceError::OutOfBounds)=>{print("OUT");},
                            Err(SliceError::NotCharBoundary)=>{print("CUT");},
                            Ok(view)=>{print(view);}
                        }
                        hi=hi+1;
                    }
                    lo=lo+1;
                }
            }
        ''')
        self.assertEqual((run.returncode, run.stderr), (0, ''))
        self.assertEqual(run.stdout.splitlines(), expected)

    def test_runtime_view_identity_in_both_storage_directions(self):
        harness = r'''
            const unsigned char forward[] = {195,169,116,195,169};
            const unsigned char reverse[] = {169,195,116,169,195};
            for (int direction = 0; direction < 2; ++direction) {
                CrustText text = {direction ? reverse : forward, 5, direction};
                CrustTextResult result = text_try_slice(text, 2, 5, 1);
                const unsigned char *expected = direction ? reverse : forward + 2;
                if (result.status || result.text.bytes != expected || result.text.length != 3
                        || result.text.descends != direction) return 80;
                text_print(result.text);
                result = text_try_slice(text, 5, 5, 1);
                if (result.status || result.text.length != 0) return 81;
                if (text_try_slice(text, INT_MIN, INT_MAX, 1).status != 1) return 82;
            }
            CrustTextResult empty = text_try_slice((CrustText){0}, 0, 0, 0);
            if (empty.status || empty.text.bytes != NULL || empty.text.length != 0) return 83;
        '''
        run=self.native('fn main(){}',transform=lambda c:c.replace('int main(void) {','int main(void) {'+harness))
        self.assertEqual((run.returncode,run.stdout,run.stderr),(0,'té\nté\n',''))

    def test_omitted_bounds_and_literal_failures_are_recoverable(self):
        run = self.native('''fn main() {
            match "été".try_slice(..2) {Ok(v)=>{print(v);},Err(_)=>{print("ERR");}}
            match "été".try_slice(2..) {Ok(v)=>{print(v);},Err(_)=>{print("ERR");}}
            match "été".try_slice(..) {Ok(v)=>{print(v);},Err(_)=>{print("ERR");}}
            match "".try_slice(..) {Ok(v)=>{print(v);},Err(_)=>{print("ERR");}}
            match "été".try_slice(..1) {
                Ok(v)=>{print(v);},Err(OutOfBounds)=>{print("OUT");},
                Err(NotCharBoundary)=>{print("CUT");}
            }
            match "été".try_slice(1..8) {Err(_)=>{print("ERR");},Ok(v)=>{print(v);}}
            drop(-> "été".try_slice(-1..));
        }''')
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0,'é\nté\nété\n\nCUT\nERR\n',''))

    def test_receiver_and_bounds_evaluate_once_in_order(self):
        run = self.native('''
            fn text()->&str {print(1);return "été";}
            fn lo()->Int {print(2);return 1;}
            fn hi()->Int {print(3);return 8;}
            fn main() {
                match text().try_slice(lo()..hi()) {
                    Ok(v)=>{print(v);},Err(OutOfBounds)=>{print(4);},
                    Err(NotCharBoundary)=>{print(5);}
                }
                print(6);
            }
        ''')
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0,'1\n2\n3\n4\n6\n',''))

    def test_string_views_preserve_storage_and_release_at_last_use(self):
        source = '''
            fn cut(t:&str)->Result<&str,SliceError> { return t.try_slice(..2); }
            fn relay(t:&str)->Result<&str,SliceError> { return cut(t); }
            fn main() {
                let mut strings=pool<String>(2);
                let mut first=strings.new(); first.push_str("été");
                let mut second=strings.new(); second.push_str("été");
                let a:Result<&str,SliceError> =relay(&first[..]);
                let b=second.try_slice(2..);
                EFFECT
                match a {Ok(v)=>{print(v);},Err(_)=>{print(0);}}
                match b {Ok(v)=>{print(v);},Err(_)=>{print(0);}}
                first.push_str("!");
                second.push_str("!");
                print(&first[..]); print(&second[..]);
                drop(-> first); drop(-> second);
                let reused=strings.new();print(reused.byte_len());
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\nté\nété!\nété!\n0\n'),run.stderr)
        for effect in ('drop(-> first);','strings.reset();','first.push_str("!");'):
            with self.subTest(effect=effect), self.assertRaisesRegex(Error,'emprunt|encore .*utilisée'):
                verify_program(source.replace('EFFECT',effect),allow_legacy_reset=True)
        run=self.native(source.replace('EFFECT','drop(-> a); first.push_str("!");').replace(
            'match a {Ok(v)=>{print(v);},Err(_)=>{print(0);}}',''))
        self.assertEqual((run.returncode,run.stdout),(0,'té\nété!!\nété!\n0\n'),run.stderr)

    def test_contract_keeps_both_conditional_sources_and_bound_effects(self):
        source = '''
            fn choose(a:&str,b:&str,flag:Int)->Result<&str,SliceError> {
                return if flag == 0 {a.try_slice(..)} else {b.try_slice(..)};
            }
            fn main() {
                let mut strings=pool<String>(2);
                let mut a=strings.new();a.push_str("a");
                let mut b=strings.new();b.push_str("b");
                let result=choose(&a[..],&b[..],FLAG);
                EFFECT
                match result{Ok(view)=>{print(view);},Err(_)=>{}}
                drop(-> a);drop(-> b);
            }
        '''
        for flag in (0,1):
            program=source.replace('FLAG',str(flag))
            run=self.native(program.replace('EFFECT',''))
            self.assertEqual((run.returncode,run.stdout),(0,('a' if flag == 0 else 'b')+'\n'),run.stderr)
            for effect in ('drop(-> a);','drop(-> b);','strings.reset();'):
                with self.subTest(flag=flag,effect=effect), self.assertRaisesRegex(Error,'emprunt|encore .*utilisée'):
                    verify_program(program.replace('EFFECT',effect),allow_legacy_reset=True)
        with self.assertRaisesRegex(Error,'emprunt|encore .*utilisée|retenue par un argument'):
            verify_program('''
                fn bound(p:&mut Pool<String>)->Int{p.reset();return 1;}
                let mut strings=pool<String>(1);
                let mut t=strings.new();t.push_str("a");
                let result=t.try_slice(0..bound(&mut strings));
                drop(-> result);
            ''',allow_legacy_reset=True)

    def test_result_alias_return_and_reassignment_keep_original_storage(self):
        source='''
            fn relay(result:Result<&str,SliceError>)->Result<&str,SliceError>{return result;}
            fn main(){
                let mut strings=pool<String>(2);
                let mut a=strings.new();a.push_str("é");
                let mut b=strings.new();b.push_str("b");
                let mut result=a.try_slice(..);
                let alias=relay(result);
                drop(-> result);
                EFFECT
                match alias {Ok(v)=>{print(v);},Err(_)=>{}}
                a.push_str("!");
                let mut replacement=a.try_slice(..);
                match replacement {Ok(v)=>{print(v);},Err(_)=>{}}
                replacement=b.try_slice(..);
                a.push_str("!");
                match replacement {Ok(v)=>{print(v);},Err(_)=>{}}
                print(&a[..]);
            }
        '''
        run=self.native(source.replace('EFFECT',''))
        self.assertEqual((run.returncode,run.stdout),(0,'é\né!\nb\né!!\n'),run.stderr)
        for effect in ('drop(-> a);','a.push_str("!");','strings.reset();'):
            with self.subTest(effect=effect), self.assertRaisesRegex(Error,'emprunt|encore .*utilisée'):
                verify_program(source.replace('EFFECT',effect),allow_legacy_reset=True)

    def test_short_error_patterns_also_work_for_async_char_at(self):
        run=self.native('''
            async fn inspect()->Int {
                yield;
                match "é".char_at(1) {
                    Ok(c)=>{print(c);},Err(OutOfBounds)=>{print(1);},
                    Err(NotCharBoundary)=>{print(2);}
                }
                return 3;
            }
            fn main(){let task=runtime::spawn(-> inspect());
                match task.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}}
        ''')
        self.assertEqual((run.returncode,run.stdout),(0,'2\n3\n'),run.stderr)

    def test_rejects_dangling_result_mutation_and_unused_results(self):
        invalid = (
            ('fn main(){let _="a".try_slice(..);}', 'sans usage'),
            ('fn main(){let result="a".try_slice(..);}', 'sans usage'),
            ('fn main(){let result="a".try_slice(..);drop(-> result);drop(-> result);}', 'plus utilisable'),
            ('fn main(){let result=42.try_slice(..);drop(-> result);}', 'try_slice|&str'),
            ('fn main(){drop(-> "a".try_slice(..true));}', 'borne.*Int'),
            ('''fn bad()->Result<&str,SliceError> {
                let mut strings=pool<String>(1);
                let mut text=strings.new();text.push_str("abc");
                return text.try_slice(..);
            } fn main(){drop(-> bad());}''', 'locale|survit|durable'),
            ('''fn main(){let mut bytes:[u8;2]=[195,169];
                match str::from_utf8(&bytes) {Ok(t)=>{
                    let result=t.try_slice(..);bytes[0]=65;
                    match result{Ok(v)=>{print(v);},Err(_)=>{}}
                },Err(_)=>{}}
            }''','emprunt'),
            ('''fn main(){match "a".try_slice(..){
                Ok(v)=>{print(v);},Err(CharAtError::OutOfBounds)=>{},
                Err(CharAtError::NotCharBoundary)=>{}}}''','incompatible'),
        )
        for source, diagnostic in invalid:
            with self.subTest(source=source), self.assertRaisesRegex(Error,diagnostic):
                compile_source(source)
