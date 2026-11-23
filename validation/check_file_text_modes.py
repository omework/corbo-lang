#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Focused UTF-8 File path and combinable-mode validation, sync and async."""
import argparse
import json
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def asynchronous(source):
    source = source.replace('use std::io::{File, FileMode, FilePerm, FileError, SeekFrom};',
                            'use std::io::{FileMode, FilePerm, SeekFrom};\nuse std::io::asyn::{File, FileError};')
    source = source.replace('fn probe()', 'async fn probe()')
    # Insert awaits at balanced call boundaries, including FilePerm and seek args.
    matches = list(re.finditer(r'\b(?:File::(?:open|create|delete|rename)|file\.(?:write|read_at|seek|stats))\(', source))
    for match in reversed(matches):
        at = match.end(); depth = 1; quoted = False
        while depth:
            char = source[at]
            if quoted:
                if char == '\\': at += 2; continue
                if char == '"': quoted = False
            elif char == '"': quoted = True
            elif char == '(': depth += 1
            elif char == ')': depth -= 1
            at += 1
        source = source[:at] + '.await' + source[at:]
    source = source[:source.index('fn main()')] + '''fn main() {
    let execution = runtime::spawn(probe());
    match execution.join() {
        Ok(result) => {
            match result {
                Ok(value) => { print(value); },
                Err(_error) => { print(999); },
            }
        },
        Err(_error) => { print(998); },
    };
}
'''
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--runner', default='')
    parser.add_argument('--windows', action='store_true')
    parser.add_argument('--compile-only', action='store_true')
    parser.add_argument('--ubsan', action='store_true')
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    original = (ROOT / 'validation/fixtures/file_text_modes/src/main.crb').read_text()
    if args.windows:
        # Wine's host filesystem rejects exact ACL verification (ERROR_NOT_SUPPORTED).
        # This API cycle exercises default Windows permissions, not ACL emulation.
        original = original.replace('FilePerm.Perm(0x180)', 'FilePerm.DefaultMode')
    results = []
    for mode in ['sync', 'async']:
        package = out / mode; (package / 'src').mkdir(parents=True, exist_ok=True)
        (package / 'package.toml').write_text('[package]\nname="file_modes"\n')
        (package / 'src/main.crb').write_text(original if mode == 'sync' else asynchronous(original))
        emitted = subprocess.run([str(args.compiler.resolve()), '--emit-package-c', str(package),
                                  '--stdlib-dir', str(ROOT / 'stdlib/src')], capture_output=True, text=True, timeout=120)
        assert emitted.returncode == 0, (mode, emitted.returncode, emitted.stdout[-1000:], emitted.stderr)
        c = package / 'probe.c'; c.write_text(emitted.stdout)
        binary = package / ('probe.exe' if args.windows else 'probe')
        flags = ['-std=c11', '-O1', '-pthread']
        if args.ubsan: flags += ['-fsanitize=undefined', '-fno-sanitize-recover=all']
        libraries = ['-lm'] + (['-ladvapi32', '-lws2_32'] if args.windows else [])
        built = subprocess.run([*shlex.split(args.cc), *flags, str(c), *libraries, '-o', str(binary)], capture_output=True, text=True, timeout=180)
        assert built.returncode == 0, (mode, built.stderr[-3000:])
        if args.compile_only:
            results.append({'mode': mode, 'status': 'compiled; execution deferred'}); continue
        with tempfile.TemporaryDirectory(prefix='run-', dir=package) as directory:
            work = Path(directory)
            runner = [part.replace('{cwd}', str(work)) for part in shlex.split(args.runner)]
            ran = subprocess.run([*runner, str(binary)], cwd=work, capture_output=True, text=True, timeout=60)
            assert (ran.returncode, ran.stdout.split()) == (0, ['42']), (mode, ran.returncode, ran.stdout, ran.stderr)
            assert (work / 'final-é.bin').read_bytes() == b'abc!', mode
            assert not (work / 'private.bin').exists() and not (work / 'text-é.bin').exists(), mode
            results.append({'mode': mode, 'status': 'executed', 'stdout': ran.stdout,
                            'independent_bytes': 'abc!', 'ubsan': args.ubsan,
                            'creation_permissions': 'default' if args.windows else 'owner read/write'})
        print(mode, 'passed', flush=True)
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__': main()
