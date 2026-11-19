"""Fault injection for independent outer status, payload, and return typing."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('sync_outer_status_erased','crust.py',
  "self.lines.append(f'{c}.status = task_join_into(&{value}, &{c}.value).status;')",
  "self.lines.append(f'(void)task_join_into(&{value}, &{c}.value);')",
  'test_failure_remains_at_its_own_layer'),
 ('async_outer_status_erased','async_lowering.py',
  "steps.append(f'{result}.status = {status_result}.status;')",
  "steps.append(f'{result}.status = 0;')",
  'test_failure_remains_at_its_own_layer'),
 ('inner_status_erased','async_lowering.py',
  "steps.append(f'{result}.status = {status_result}.status;')",
  "steps.append(f'{result}.status = {status_result}.status; {result}.value.status = 0;')",
  'test_failure_remains_at_its_own_layer'),
 ('return_payload_type_erased','async_lowering.py',
  'if plain_join_mode(expr) != mode:', 'if False:',
  'test_async_result_return_type_is_not_erased'),
 ('unused_inner_result_accepted','async_lowering.py',
  'if not has_future_value_use(payload, body):', 'if False:',
  'test_nested_fallible_bindings_require_use'),
]


def main():
    success=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: mutation anchor changed')
        with tempfile.TemporaryDirectory(prefix='crust-nested-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_nested_plain_results.NestedPlainResultTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-1800:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
