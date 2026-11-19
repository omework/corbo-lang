#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Targeted root STD collection imports; existing storage behavior is unchanged."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

GROUPED = '''use std::{Vector, HashMap, String};
fn main() {
    let mut memory = pool<Vector<i64>>(1);
    let mut values = memory.new();
    values.push(12); values.push(18);
    print(values[0]);
    print(values[1]);
    print(values.len());
    let mut map = HashMap<i64, i64>::new();
    drop(map.insert(1, 9));
    let key: i64 = 1;
    match map.get(&key) { Some(value) => { print(*value); }, None => {} }
    match map.remove(&key) { Some(value) => { print(value); }, None => {} }
    let mut texts = pool<String>(1);
    let text = texts.new(); print(text.byte_len());
}'''

OWNED = '''use std::{Vector as Values, HashMap as Index};
fn main() {
    let mut numbers = pool<i64>(1);
    let mut vectors = pool<Values<A<i64>>>(1);
    let mut values = vectors.new();
    values.push(numbers.new(7));
    let mut map = Index<i64, A<i64>>::new();
    let item = values.remove(0);
    drop(map.insert(1, item));
    let key: i64 = 1;
    match map.remove(&key) { Some(value) => { print(*value); drop(value); }, None => {} }
    let reused = numbers.new(11); print(*reused);
}'''

QUALIFIED = '''fn main() {
    let mut memory = pool<std::Vector<i64>>(1);
    let mut values = memory.new(); values.push(4); print(values[0]);
    let mut map = std::HashMap<i64, i64>::new();
    drop(map.insert(1, 6)); let key: i64 = 1;
    match map.get(&key) { Some(value) => { print(*value); }, None => {} }
    let mut texts = pool<std::String>(1); let text = texts.new(); print(text.byte_len());
}'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corboc', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--runner', default='')
    parser.add_argument('--keep', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='corbo-collection-imports-') as temporary:
        root = args.keep.resolve() if args.keep else Path(temporary)
        (root / 'src').mkdir(parents=True, exist_ok=True)
        (root / 'package.toml').write_text('[package]\nname="exports"\n')

        def compile_source(source):
            (root / 'src/main.crb').write_text(source)
            return subprocess.run([args.corboc.resolve(), '--emit-package-c', root,
                                   '--stdlib-dir', ROOT / 'stdlib/src'],
                                  capture_output=True, text=True, timeout=60)

        def execute(name, source, expected):
            result = compile_source(source)
            assert result.returncode == 0 and result.stdout.startswith('#'), (name, result)
            generated = root / f'{name}.c'
            generated.write_text(result.stdout)
            binary = root / f'{name}.exe'
            subprocess.run([*shlex.split(args.cc), '-std=c11', '-pthread', '-O2',
                            '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            generated, '-lm', '-o', binary], check=True, timeout=180)
            run = subprocess.run([*shlex.split(args.runner), binary], capture_output=True,
                                 text=True, timeout=30)
            assert (run.returncode, run.stdout, run.stderr) == (0, expected, ''), (name, run)
            print(f'passed: {name}', flush=True)

        execute('grouped', GROUPED, '12\n18\n2\n9\n9\n0\n')
        execute('aliases_and_ownership', OWNED, '7\n11\n')
        execute('qualified', QUALIFIED, '4\n6\n0\n')
        helper = root / 'src/worker'
        helper.mkdir(exist_ok=True)
        (helper / 'worker.crb').write_text(GROUPED.replace('fn main()', 'pub fn run()'))
        execute('cross_module', 'use exports::worker::run; fn main() { run(); }',
                '12\n18\n2\n9\n9\n0\n')
        (helper / 'worker.crb').unlink()
        helper.rmdir()
        for name, source, expected_code in (
            ('duplicate_import', 'use std::{Vector, Vector}; fn main() {}', 14),
            ('alias_collision', 'use std::Vector as Values; struct Values {} fn main() {}', 14),
            ('unknown_export', 'use std::NotACollection; fn main() {}', 13),
            ('reserved_declaration', 'pub struct Vector<T> {} fn main() {}', 7),
        ):
            result = compile_source(source)
            assert result.returncode == expected_code, (name, result)
            print(f'refused: {name} (exit {expected_code})', flush=True)


if __name__ == '__main__':
    main()
