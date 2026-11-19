"""Controlled dispatch and failure faults in isolated compiler/runtime copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ('runtime_error_confused_with_utf8_error','crust.py',
     '14: join_results,', '14: results,',1,
     'test_public_runtime_error_in_owned_and_nested_result_contracts'),
    ('sync_intent_lost','crust.py',
     "start = 'task_thread_start_blocking' if len(expr) > 2 and expr[2] == 'blocking' else 'task_thread_start'",
     "start = 'task_thread_start'",1,'test_sync_and_async_dispatch_keep_blocking_intent_and_cleanup'),
    ('async_intent_lost','async_lowering.py',
     "start = 'task_async_start_blocking' if blocking else 'task_async_start'",
     "start = 'task_async_start'",1,'test_sync_and_async_dispatch_keep_blocking_intent_and_cleanup'),
    ('callback_selection_lost','async_runtime.py',
     'blocking ? scheduler->launch_blocking : scheduler->launch',
     'blocking ? scheduler->launch : scheduler->launch',2,
     'test_scheduler_callbacks_are_distinct_and_missing_blocking_rejects_cleanly'),
    ('launch_failure_cleanup_missing','async_runtime.py',
     '        if (!task_drop_inactive(task)) abort();',
     '        /* faulty: failed launch retains the inactive state */',2,
     'test_sync_and_async_dispatch_keep_blocking_intent_and_cleanup'),
]


def main():
    success=True
    for name,filename,before,after,count,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=count:
            raise SystemExit(f'{name}: mutation anchor changed')
        with tempfile.TemporaryDirectory(prefix='crust-blocking-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_spawn_blocking.SpawnBlockingTests.{test}')
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not r.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if not run.returncode else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-1600:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':
    sys.exit(main())
