"""Target native capture consumption, returned provenance and dispatch."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ('sync_capture_not_consumed','crust.py',
     "if node.native_block and mode not in ('owned', *JOIN_RESULT_TYPES):",
     'if False:', 'test_scalar_capture_consumes_binding_in_both_callers'),
    ('async_capture_not_consumed','async_lowering.py',
     'if declaration.native_block:\n                    consumed.add(argument[1])',
     'if False:\n                    consumed.add(argument[1])',
     'test_scalar_capture_consumes_binding_in_both_callers'),
    ('returned_origin_lost','async_lowering.py',
     'cache[name] = frozenset(scan(body, {}, {}))',
     'cache[name] = frozenset(sorted(scan(body, {}, {}))[:1])',
     'test_conditional_reference_result_preserves_both_sources'),
    ('native_dispatched_as_spawn','native_threads.py',
     "return ('task_spawn', ('transfer', ('call', name, arguments)), 'native'), ('execution', name)",
     "return ('task_spawn', ('transfer', ('call', name, arguments))), ('execution', name)",
     'test_generated_native_launch_bypasses_rejecting_scheduler'),
]


def main():
    success=True
    for name, filename, before, after, test in MUTATIONS:
        if sys.argv[1:] and name not in sys.argv[1:]: continue
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1: raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-native-block-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'): shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_native_blocks.NativeBlockTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-3500:],flush=True)
            success &= detected
    return 0 if success else 1

if __name__=='__main__':sys.exit(main())
