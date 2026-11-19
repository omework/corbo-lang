#!/usr/bin/env python3
"""Execute STD-owned iterator algorithms with corboc and a selected C target."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
COUNTER = (ROOT / 'validation/fixtures/iter_adapters/src/main.crb').read_text().split('fn main()')[0]
CASES = [
    ('composed', (ROOT / 'validation/fixtures/iter_adapters/src/main.crb').read_text(), '1\n120\n7\n'),
    ('empty', COUNTER + '''
fn main() {
    let mut source = Counter { position: 1, end: 1 };
    let mut pipeline = iter(&mut source).reduce(|acc: i64, item: i64| { print(99); acc + item });
    match pipeline.next() { Some(v) => { print(v); }, None => { print(0); } }
    match pipeline.next() { Some(v) => { print(v); }, None => { print(0); } }
}
''', '0\n0\n'),
    ('singleton', COUNTER + '''
fn main() {
    let mut source = Counter { position: 4, end: 5 };
    let mut pipeline = iter(&mut source).reduce(|acc: i64, item: i64| { print(99); acc + item });
    match pipeline.next() { Some(v) => { print(v); }, None => { print(0); } }
    match pipeline.next() { Some(v) => { print(v); }, None => { print(0); } }
    print(source.position);
}
''', '4\n0\n5\n'),
    ('capturing_predicate', COUNTER + '''
fn main() {
    let mut source = Counter { position: 1, end: 5 };
    let mut limit = 0;
    let mut pipeline = iter(&mut source).filter(|item: &i64| {
        limit = limit + 1;
        *item > limit - 1
    }).map(|item: i64| { item * 2 });
    match pipeline.next() { Some(v) => { print(v); }, None => {} }
    match pipeline.next() { Some(v) => { print(v); }, None => {} }
    print(limit);
    print(source.position);
}
''', '2\n4\n0\n3\n'),
    ('capturing_reducer', COUNTER + '''
fn main() {
    let mut source = Counter { position: 1, end: 4 };
    let extra = 10;
    let mut pipeline = iter(&mut source).reduce(|acc: i64, item: i64| { acc + item + extra });
    match pipeline.next() { Some(v) => { print(v); }, None => {} }
    print(extra);
    print(source.position);
}
''', '26\n10\n4\n'),
    ('rejected_items_cleanup', '''
use std::iter::iter;
struct Item { value: i64 }
impl Item { fn drop(&mut self) { print((*self).value); } }
struct Source { next_value: i64 }
impl Source {
    fn next(&mut self) -> Option<Item> {
        let value = (*self).next_value;
        if copy(value) == 4 { return None; }
        let next_value = &mut (*self).next_value;
        *next_value = copy(value) + 1;
        Some(Item { value: value })
    }
}
fn main() {
    let mut source = Source { next_value: 1 };
    let mut pipeline = iter(&mut source).filter(|item: &Item| -> bool { (*item).value == 2 });
    match pipeline.next() { Some(item) => { print(99); drop(item); }, None => {} }
    match pipeline.next() { Some(item) => { drop(item); }, None => { print(88); } }
}
''', '1\n99\n2\n3\n88\n'),
]
CASES.append(('reduce_owned_items', CASES[5][1].replace(
    '.filter(|item: &Item| -> bool { (*item).value == 2 })',
    '.reduce(|acc: Item, item: Item| -> Item { let value = acc.value + item.value; drop(acc); drop(item); Item { value: value } })'
), '1\n2\n3\n3\n99\n6\n88\n'))

CASES.append(('replacement_order', """
struct Item { value: i64 }
impl Item { fn drop(&mut self) { print((*self).value); } }
fn fresh() -> Item { print(5); Item { value: 2 } }
fn main() {
    let mut value = Item { value: 1 };
    value = fresh();
    print(99);
    drop(value);
}
""", '5\n1\n99\n2\n'))

CASES.append(('named_map_collect', COUNTER + """
fn main() {
    let mut source = Counter { position: 2, end: 5 };
    let chain = iter(&mut source).map(|item: i64| { item * 3 });
    let mut memory = pool<Vector<i64>>(1);
    let mut destination = memory.new();
    chain.collect(&mut destination);
    print(destination.len()); print(destination[2]); print(source.position);
}
""", '3\n12\n5\n'))

CASES.append(('filter_collect', COUNTER + """
fn main() {
    let mut source = Counter { position: 1, end: 4 };
    let filtered = iter(&mut source).filter(|item: &i64| { *item % 2 == 0 });
    let mut memory = pool<Vector<i64>>(1);
    let mut destination = memory.new();
    filtered.collect(&mut destination);
    print(destination.len()); print(destination[0]); print(source.position);
}
""", '1\n2\n4\n'))

REFUSED = [
    ('collect_consumes_chain', COUNTER + """fn main() {
        let mut source = Counter { position: 1, end: 4 };
        let mut chain = iter(&mut source).map(|item: i64| { item });
        let mut memory = pool<Vector<i64>>(1);
        let mut destination = memory.new();
        chain.collect(&mut destination);
        let item = chain.next(); drop(item);
    }"""),
    ('source_live_loan', COUNTER + '''fn main() {
        let mut source = Counter { position: 0, end: 4 };
        let mut pipeline = iter(&mut source).filter(|item: &i64| { *item > 0 });
        print(source.position);
        let next = pipeline.next(); drop(next);
    }'''),
    ('replacement_live_loan', """
        struct Item { value: i64 }
        impl Item { fn get(&self) -> i64 { (*self).value } }
        struct View { source: &Item }
        impl View {
            fn new(source: &Item) -> View { View { source: source } }
            fn get(&self) -> i64 { let source = &*(*self).source; source.get() }
        }
        fn fresh() -> Item { Item { value: 2 } }
        fn main() {
            let mut value = Item { value: 1 };
            let view = View::new(&value);
            value = fresh();
            print(view.get());
        }
    """),
    ('wrong_predicate', COUNTER + '''fn main() {
        let mut source = Counter { position: 0, end: 4 };
        let p = iter(&mut source).filter(|item: i64| { item > 0 }); drop(p);
    }'''),
    ('wrong_reducer', COUNTER + '''fn main() {
        let mut source = Counter { position: 0, end: 4 };
        let p = iter(&mut source).reduce(|acc: i64, item: bool| { acc }); drop(p);
    }'''),
    ('moved_predecessor', COUNTER + '''fn main() {
        let mut source = Counter { position: 0, end: 4 };
        let mut first = iter(&mut source);
        let second = first.filter(|item: &i64| { *item > 0 });
        let next = first.next(); drop(next); drop(second);
    }'''),
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corboc', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--runner', default='')
    parser.add_argument('--keep', type=Path)
    parser.add_argument('--reference-c', type=Path, help='require byte-identical C to already executed platform witnesses')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='corbo-std-iter-') as temp:
        root = args.keep.resolve() if args.keep else Path(temp)
        (root / 'src').mkdir(parents=True, exist_ok=True)
        (root / 'package.toml').write_text('[package]\nname="iterator_test"\n')
        for name, source, expected in CASES:
            (root / 'src/main.crb').write_text(source)
            result = subprocess.run([args.corboc.resolve(), '--emit-package-c', root,
                                     '--stdlib-dir', ROOT / 'stdlib/src'], capture_output=True, text=True, timeout=60)
            assert result.returncode == 0 and result.stdout.startswith('#'), (name, result.returncode, result.stdout, result.stderr)
            generated = root / f'{name}.c'
            generated.write_text(result.stdout)
            if args.reference_c:
                assert result.stdout == (args.reference_c / f'{name}.c').read_text(), (name, 'generated C differs from the executed reference')
            for opt in ('O0', 'O2'):
                binary = root / f'{name}-{opt}.exe'
                subprocess.run([*shlex.split(args.cc), '-std=c11', '-pthread', f'-{opt}',
                                '-fsanitize=undefined', '-fno-sanitize-recover=all', generated, '-lm', '-o', binary], check=True, timeout=180)
                run = subprocess.run([*shlex.split(args.runner), binary], capture_output=True, text=True, timeout=30)
                assert (run.returncode, run.stdout, run.stderr) == (0, expected, ''), (name, opt, run)
            print(f'passed: {name} (O0, O2, fatal UBSan)', flush=True)
        for name, source in REFUSED:
            (root / 'src/main.crb').write_text(source)
            result = subprocess.run([args.corboc.resolve(), '--emit-package-c', root,
                                     '--stdlib-dir', ROOT / 'stdlib/src'], capture_output=True, text=True, timeout=60)
            expected_rule = {'collect_consumes_chain': '6', 'source_live_loan': '5', 'replacement_live_loan': '5', 'wrong_predicate': '1', 'wrong_reducer': '1', 'moved_predecessor': '6'}[name]
            assert result.returncode == 8 and result.stdout.splitlines()[0] == expected_rule, (name, result)
            print(f'refused: {name}', flush=True)
        (root / 'src/main.crb').write_text(COUNTER + """fn main() {
            let mut source = Counter { position: 1, end: 4 };
            let chain = iter(&mut source).map(|item: i64| { item });
            let mut memory = pool<Vector<i64>>(1);
            let mut destination = memory.new();
            std::iter::collect(chain, &mut destination);
        }""")
        result = subprocess.run([args.corboc.resolve(), '--emit-package-c', root,
                                 '--stdlib-dir', ROOT / 'stdlib/src'], capture_output=True, text=True, timeout=60)
        assert result.returncode == 13 and 'std::iter::collect' in result.stderr, result
        print('refused: no package-level collect export', flush=True)


if __name__ == '__main__':
    main()
