#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Run one queue/contention witness against the Corbo and retained C runtimes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Build the minimal runtime sections and execute each witness with fatal UBSan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/mutex-runtime')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    generated = out / 'runtime'
    subprocess.run([sys.executable, str(ROOT / 'runtime/corbo/build.py'), '--compiler',
                    str(args.compiler.resolve()), '--out', str(generated)], check=True,
                   stdout=subprocess.DEVNULL)
    witness = (ROOT / 'validation/mutex/queue.c').read_text()
    corbo = ''.join((generated / (name + '.c.inc')).read_text()
                    for name in ['c_runtime_header', 'base_runtime'])
    parts = ['corbo_runtime.h', 'memory/metrics_storage.h', 'memory/datastack.c.inc',
             'collections/vector.c.inc', 'memory/region_release.c.inc',
             'async/task_header.c.inc', 'async/mutex.c.inc', 'async/channel.c.inc']
    reference = '\n'.join((ROOT / 'runtime' / name).read_text() for name in parts)
    results = []
    for name, runtime in [('corbo', corbo), ('c-reference', reference)]:
        source = out / (name + '.c')
        source.write_text(runtime + '\n' + witness)
        binary = out / name
        subprocess.run(['cc', '-O1', '-pthread', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        str(source), '-lm', '-o', str(binary)], check=True)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=20)
        assert run.returncode == 0 and not run.stdout and not run.stderr, (name, run)
        results.append({'runtime': name, 'status': 'executed, fatal UBSan'})
        print(name, 'passed', flush=True)
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
