"""Check specified values, identities, drops and exhaustion across C settings."""
from functools import partial, update_wrapper
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)

PROGRAM = '''
enum Message { Empty {}, Full { code: Int } }
fn inspect(p: &Pool<Int>) {}
fn relay(p: &Allocator, mut x: -> Int) -> <- Int { inspect(p); return <- x; }
fn inspect_message(p: &Pool<Message>) {}
fn relay_message(p: &Allocator, mut x: -> Message) -> <- Message { inspect_message(p); return <- x; }
fn select(mut a: -> Int, mut b: -> Int, flag: Int) -> <- Int {
    if flag == 0 { return <- a; }
    return <- b;
}
fn main() {
    let mut memory = pool<Int>(2);
    let mut other = pool<Int>(1);
    let mut messages = pool<Message>(1);
    let mut a = new(memory) Int(1);
    let mut b = new(memory) Int(2);
    address(a);
    drop(-> a);
    let mut c = new(memory) Int(3);
    address(c);
    let mut result = relay(&memory, -> b);
    print(result);
    let mut d = new(other) Int(4);
    let mut chosen = select(-> result, -> d, FLAG);
    print(chosen);
    drop(-> chosen);
    print(c);
    memory.reset();
    other.reset();
    let mut e = new(messages) Message.Full { code: 9 };
    let mut empty = new(messages) Message.Empty {};
    let mut returned = relay_message(&messages, -> e);
    print(returned);
    drop(-> returned);
    messages.reset();
}
'''
EXHAUSTION = '''
fn make(p: &mut Pool<Int>, n: Int) -> <- Int {
    let mut value = new(p) Int(n);
    return <- value;
}
fn main() {
    let mut p = pool<Int>(1);
    let mut first = make(&mut p, 1);
    let mut second = make(&mut p, 2);
    print(first);
    print(second);
}
'''


def toolchains():
    found = {}
    for name in ('clang', 'gcc-15', 'gcc-14', 'gcc-13', 'gcc'):
        path = shutil.which(name)
        if not path:
            continue
        version = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=10).stdout
        family = 'clang' if 'clang' in version.lower() else 'gcc' if 'gcc' in version.lower() else name
        if family not in found:
            found[family] = {'family': family, 'path': path, 'version': version.splitlines()[0]}
    return list(found.values())


def validate(result, case):
    if 'runtime error:' in result.stderr:
        raise AssertionError('UBSan diagnostic: ' + result.stderr)
    if case == 'exhaustion':
        assert result.returncode != 0, 'capacity exhaustion did not stop'
        assert 'pool capacity exceeded' in result.stderr, result.stderr
        assert 'destroy ' not in result.stderr, 'unexpected failure unwinding'
        assert result.stdout == '', result.stdout
        return
    flag = int(case)
    assert result.returncode == 0, result.stderr
    output = result.stdout.splitlines()
    assert len(output) == 6 and output[0] == output[1], output
    assert output[2:] == ['2', '2' if flag == 0 else '4', '3', 'Message.Full(9)'], output
    middle = ['destroy d=4', 'destroy b=2'] if flag == 0 else ['destroy b=2', 'destroy d=4']
    expected = ['destroy a=1', *middle, 'destroy c=3', 'destroy e=Message.Full', 'destroy empty=Message.Empty']
    assert [line for line in result.stderr.splitlines() if line.startswith('destroy ')] == expected, result.stderr
    assert result.stderr.splitlines().count('reset') == 3, result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    compilers = toolchains()
    if not compilers:
        raise RuntimeError('no C toolchain available')
    settings = [('O0', ['-O0']), ('O2', ['-O2']), ('Os', ['-Os']),
                ('O2-UBSan', ['-O2', '-fsanitize=undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer'])]
    report = {'toolchains': compilers, 'runs': [],
              'limitations': ['three fixed supported programs; no general proof',
                              'ASan not run: previously failed even an empty C probe on this host']}
    # Expectations are specified above, not derived from emitted C or verifier state.
    with tempfile.TemporaryDirectory(prefix='crust-pool-c-') as directory:
        folder = Path(directory)
        for case in ('0', '1', 'exhaustion'):
            source = EXHAUSTION if case == 'exhaustion' else PROGRAM.replace('FLAG', case)
            c = folder / 'program.c'
            c.write_text(compile_source(source))
            for compiler in compilers:
                for name, options in settings:
                    binary = folder / 'program'
                    command = [compiler['path'], '-std=c11', '-Wall', '-Wextra', '-Werror',
                               '-Wno-unused-variable', '-Wno-unused-function', *options, str(c), '-o', str(binary)]
                    build = subprocess.run(command, capture_output=True, text=True, timeout=30)
                    if build.returncode:
                        raise RuntimeError(build.stderr)
                    environment = dict(os.environ, UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10, env=environment)
                    validate(result, case)
                    report['runs'].append({'case': case, 'compiler': compiler['family'], 'settings': name,
                                           'returncode': result.returncode, 'stdout': result.stdout,
                                           'stderr': result.stderr, 'expected_result': 'abort' if case == 'exhaustion' else 'success'})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(report["runs"])} C executions passed their specified checks across {len(compilers)} compiler family/families')


if __name__ == '__main__':
    main()
