#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Focused STD text-splitting executions and original-storage lifetime checks."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def consume(expression):
    return f'''let mut parts = {expression};
    loop {{ match parts.next() {{
        Some(piece) => {{ print(piece.byte_len()); }},
        None => {{ break; }},
    }} }}'''


CASES = {
    'empty_owned': ('use std::String;fn main(){let mut p=pool<String>(1);let text=p.new();let mut parts=text.split(",");match parts.next(){Some(s)=>{print(s.byte_len());},None=>{print(99);}}}', '0\n'),
    'literal': ('fn main(){' + consume('"a,,b,".split(",")') + '}', '1\n0\n1\n0\n'),
    'unicode': ('fn main(){' + consume('"été∷x∷".split("∷")') + '}', '5\n1\n0\n'),
    'empty_separator': ('fn main(){' + consume('"é🦀x".split("")') + '}', '0\n2\n4\n1\n0\n'),
    'empty_text': ('fn main(){' + consume('"".split(",")') + consume('"".split("")') + '}', '0\n0\n0\n'),
    'overlap_and_missing': ('fn main(){' + consume('"aaaa".split("aa")') + consume('"ab".split("longer")') + '}', '0\n0\n0\n2\n'),
    'owned_and_exhausted': ('''use std::String;
fn main(){let mut strings=pool<String>(1);let mut text=strings.new();text.push_str("left::right::");
''' + consume('text.split("::")') + '''
match parts.next(){Some(piece)=>{print(piece.byte_len());},None=>{print(99);}}
match parts.next(){Some(piece)=>{print(piece.byte_len());},None=>{print(99);}}
print(text.byte_len());}''', '4\n5\n0\n99\n99\n13\n'),
    'pieces_survive_cursor': ('''use std::String;
fn main(){let mut strings=pool<String>(1);let mut text=strings.new();text.push_str("first,last");
let mut parts=text.split(",");
match parts.next(){Some(first)=>{
    match parts.next(){Some(second)=>{print(second.byte_len());},None=>{}}
    drop(parts);print(first.byte_len());
},None=>{}}
}''', '4\n5\n'),
    'iterator_wrapper': ('''use std::iter::iter;
fn main(){let mut parts="a,b".split(",");let mut chain=iter(&mut parts);
loop{match chain.next(){Some(piece)=>{print(piece.byte_len());},None=>{break;}}}}
''', '1\n1\n'),
    'piece_contents': ('''fn main(){let mut parts="é::x".split("::");
loop{match parts.next(){Some(piece)=>{let bytes=piece.as_bytes();let mut i:usize=0;while i<bytes.len(){print(bytes[i]);i+=1;}},None=>{break;}}}}
''', '195\n169\n120\n'),
    'independent_separator': ('''use std::String;fn main(){let mut strings=pool<String>(1);let mut separator=strings.new();separator.push_str(",");
let view=&separator[..];let mut parts="a,b".split(view);
match parts.next(){Some(piece)=>{drop(separator);print(piece.byte_len());},None=>{}}}
''', '1\n'),
    'named_view': ('''fn main(){let text="one:two";let view=&text[..];''' + consume('view.split(":")') + '}', '3\n3\n'),
}

REJECT = {
    'drop_text': '''use std::String;fn main(){let mut p=pool<String>(1);let mut text=p.new();text.push_str("a,b");let mut parts=text.split(",");drop(text);match parts.next(){Some(s)=>{print(s.byte_len());},None=>{}}}''',
    'mutate_text': '''use std::String;fn main(){let mut p=pool<String>(1);let mut text=p.new();text.push_str("a,b");let mut parts=text.split(",");text.push_str("x");match parts.next(){Some(s)=>{print(s.byte_len());},None=>{}}}''',
    'drop_piece_storage': '''use std::String;fn main(){let mut p=pool<String>(1);let mut text=p.new();text.push_str("a,b");let mut parts=text.split(",");match parts.next(){Some(s)=>{drop(text);print(s.byte_len());},None=>{}}}''',
    'drop_separator': '''use std::String;fn main(){let mut p=pool<String>(1);let mut separator=p.new();separator.push_str(",");let view=&separator[..];let mut parts="a,b".split(view);drop(separator);match parts.next(){Some(s)=>{print(s.byte_len());},None=>{}}}''',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corboc', type=Path, required=True)
    parser.add_argument('--keep', type=Path, default=ROOT/'build/text-split/validation')
    args = parser.parse_args()
    compiler = args.corboc.resolve()
    args.keep.mkdir(parents=True, exist_ok=True)
    report = []
    for name, source in list((k,v[0]) for k,v in CASES.items()) + list(REJECT.items()):
        work = (args.keep/name).resolve()
        (work/'src').mkdir(parents=True, exist_ok=True)
        (work/'package.toml').write_text('[package]\nname="split_validation"\n')
        (work/'src/main.crb').write_text(source+'\n')
        result = subprocess.run([compiler, '--emit-package-c', work, '--stdlib-dir', ROOT/'stdlib/src'], capture_output=True, text=True, timeout=120)
        (work/'compiler.txt').write_text(result.stdout+result.stderr)
        if name in REJECT:
            passed = result.returncode == 8 and result.stdout.splitlines()[0] == '5'
            row = {'name':name, 'passed':passed, 'kind':'rejection', 'status':result.returncode, 'diagnostic':result.stdout[:1000]}
        elif result.returncode:
            row = {'name':name, 'passed':False, 'kind':'execution', 'status':result.returncode, 'diagnostic':result.stdout[:1000]}
        else:
            c = work/'program.c'; c.write_text(result.stdout)
            built = subprocess.run(['cc', '-std=c11', '-O1', '-pthread', '-fsanitize=undefined', '-fno-sanitize-recover=all', c, '-lm', '-o', work/'program'], capture_output=True, text=True, timeout=120)
            (work/'cc.txt').write_text(built.stderr)
            executed = subprocess.run([work/'program'], capture_output=True, text=True, timeout=30) if built.returncode == 0 else built
            row = {'name':name, 'passed':built.returncode == 0 and executed.returncode == 0 and executed.stdout == CASES[name][1] and not executed.stderr, 'kind':'execution', 'status':executed.returncode, 'stdout':executed.stdout, 'stderr':executed.stderr[:1000]}
        report.append(row)
        print(('PASS' if row['passed'] else 'FAIL')+' '+name, flush=True)
    (args.keep/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if all(r['passed'] for r in report) else 1)


if __name__ == '__main__':
    main()
