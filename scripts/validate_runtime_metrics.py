#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Focused runtime metrics checks: Corbo API, C reference ABI and Corbo ABI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Build only the three metrics witnesses, using the supplied development compiler."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/runtime-metrics')
    args = parser.parse_args()
    compiler = args.compiler.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = []

    def execute(name, sources, expected):
        """Compile with fatal UBSan and retain the exact completed observation."""
        binary = out / name
        subprocess.run(['cc', '-O1', '-pthread', '-fsanitize=undefined',
                        '-fno-sanitize-recover=all', '-I', str(ROOT / 'runtime'),
                        *map(str, sources), '-lm', '-o', str(binary)], check=True)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
        assert run.returncode == 0 and run.stdout.split() == expected, (name, run.returncode, run.stdout, run.stderr)
        results.append({'case': name, 'status': 'executed, fatal UBSan', 'output': run.stdout.split()})
        print(name, 'passed', flush=True)

    emitted = subprocess.run([str(compiler), '--emit-package-c',
                              str(ROOT / 'validation/runtime_metrics/api'), '--stdlib-dir',
                              str(ROOT / 'stdlib/src')], capture_output=True, text=True, timeout=60)
    assert emitted.returncode == 0, (emitted.returncode, emitted.stdout[:200], emitted.stderr)
    api = out / 'api.c'
    api.write_text(emitted.stdout)
    execute('api', [api], ['true'] * 8)
    witness = ROOT / 'validation/runtime_metrics/memory_stats.c'
    execute('c-reference', [witness, ROOT / 'runtime/corbo_runtime.c'], [])
    generated = out / 'runtime'
    subprocess.run([sys.executable, str(ROOT / 'runtime/corbo/build.py'), '--compiler',
                    str(compiler), '--out', str(generated)], check=True, stdout=subprocess.DEVNULL)
    sections = ['c_runtime_header', 'base_runtime', 'pool_runtime', 'c_runtime_api']
    source = out / 'corbo-abi.c'
    source.write_text('\n'.join((generated / (part + '.c.inc')).read_text() for part in sections)
                      + '\n' + witness.read_text())
    execute('corbo-abi', [source], [])
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
