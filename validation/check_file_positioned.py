#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Focused sync/async positioned File I/O validation with an independent byte oracle."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


# Interpose only the witness's native calls: owned companions and per-request
# events must close, including EOF, before exit. Real Win32 I/O still runs.
WINDOWS_TRACKING = r"""
#include <windows.h>
#include <stdlib.h>
static HANDLE positioned_live[16];
static unsigned positioned_total;
static unsigned positioned_events;
__attribute__((used)) HANDLE WINAPI corbo_test_reopen(HANDLE file, DWORD access, DWORD share, DWORD flags) {
    HANDLE result = ReOpenFile(file, access, share, flags);
    DWORD error = GetLastError();
    if (result != INVALID_HANDLE_VALUE) {
        unsigned at = 0;
        while (at < 16 && positioned_live[at]) ++at;
        if (at == 16) exit(91);
        positioned_live[at] = result;
        ++positioned_total;
    }
    SetLastError(error);
    return result;
}
__attribute__((used)) HANDLE WINAPI corbo_test_event(LPSECURITY_ATTRIBUTES security, BOOL manual, BOOL initial, LPCWSTR name) {
    HANDLE result = CreateEventW(security, manual, initial, name);
    DWORD error = GetLastError();
    if (result) {
        unsigned at = 0;
        while (at < 16 && positioned_live[at]) ++at;
        if (at == 16) exit(95);
        positioned_live[at] = result;
        ++positioned_events;
    }
    SetLastError(error);
    return result;
}
__attribute__((used)) BOOL WINAPI corbo_test_close(HANDLE file) {
    BOOL result = CloseHandle(file);
    DWORD error = GetLastError();
    for (unsigned at = 0; at < 16; ++at) {
        if (positioned_live[at] == file) {
            if (!result) exit(92);
            positioned_live[at] = NULL;
            break;
        }
    }
    SetLastError(error);
    return result;
}
static void positioned_check_closed(void) {
    if (positioned_total != 4 || positioned_events != 4) exit(93);
    for (unsigned at = 0; at < 16; ++at) if (positioned_live[at]) exit(94);
}
__attribute__((constructor)) static void positioned_install_checks(void) { atexit(positioned_check_closed); }
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/file-positioned')
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--runner', default='', help='Runner command; {cwd} expands to the test working directory')
    parser.add_argument('--windows', action='store_true')
    parser.add_argument('--compile-only', action='store_true')
    parser.add_argument('--ubsan', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for mode, fixture in [('sync', 'file_positioned'), ('async', 'file_positioned_async')]:
        emitted = subprocess.run([str(args.compiler.resolve()), '--emit-package-c',
                                  str(ROOT / 'validation/fixtures' / fixture),
                                  '--stdlib-dir', str(ROOT / 'stdlib/src')],
                                 capture_output=True, text=True, timeout=90)
        assert emitted.returncode == 0, (mode, emitted.returncode, emitted.stdout[:400], emitted.stderr)
        source = out / (mode + '.c')
        code = emitted.stdout
        if args.windows:
            code = WINDOWS_TRACKING + code.replace('call ReOpenFile', 'call corbo_test_reopen').replace('bl ReOpenFile', 'bl corbo_test_reopen').replace('call CreateEventW', 'call corbo_test_event').replace('bl CreateEventW', 'bl corbo_test_event').replace('call CloseHandle', 'call corbo_test_close').replace('bl CloseHandle', 'bl corbo_test_close')
        source.write_text(code)
        binary = out / (mode + ('.exe' if args.windows else ''))
        flags = ['-std=c11', '-pthread', '-O1']
        if args.ubsan:
            flags += ['-fsanitize=undefined', '-fno-sanitize-recover=all']
        libraries = ['-lm'] + (['-ladvapi32', '-lws2_32'] if args.windows else [])
        built = subprocess.run([*shlex.split(args.cc), *flags, str(source), *libraries, '-o', str(binary)],
                               capture_output=True, text=True, timeout=180)
        assert built.returncode == 0, (mode, built.stderr[-2500:])
        if args.compile_only:
            results.append({'mode': mode, 'status': 'compiled only; execution deferred'})
            print(mode, 'compiled only', flush=True)
            continue
        with tempfile.TemporaryDirectory(prefix=mode + '-run-', dir=out) as temporary:
            work = Path(temporary)
            runner = [item.replace('{cwd}', str(work)) for item in shlex.split(args.runner)]
            ran = subprocess.run([*runner, str(binary)], cwd=work, capture_output=True,
                                 text=True, timeout=40)
            assert ran.returncode == 0 and ran.stdout.split() == ['42'], (mode, ran.returncode, ran.stdout, ran.stderr[-1500:])
            # Wine may write non-fatal loader notices; other runners must be clean.
            if not args.windows:
                assert not ran.stderr, (mode, ran.stderr)
            assert (work / 'moved').read_bytes() == b'abcZXY', mode
            assert not (work / 'positioned').exists(), mode
        results.append({'mode': mode, 'status': 'executed', 'stdout': ['42'],
                        'independent_bytes': 'abcZXY', 'fatal_ubsan': args.ubsan, 'temporary_handles_checked': args.windows})
        print(mode, 'passed', flush=True)
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
