"""Typed error/status faults tested in isolated compiler copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ('dead_payload_status_lost','crust.py',
     "return 'runtime_error', f'(CrustRuntimeError)({tag.c})', None",
     "return 'runtime_error', '(CrustRuntimeError)0', None",
     'test_error_stays_valid_after_owned_capture_and_result_cleanup'),
    ('async_result_field_confused','async_lowering.py',
     "payload_field == 'runtime_error_value':\n                            runtime_error_bindings.add(payload)",
     "payload_field == 'runtime_error_value':\n                            runtime_error_bindings.add(payload)\n                            field = 'value'",
     'test_async_error_capture_return_direct_await_join_and_scope_types'),
    ('error_accepted_as_integer','async_lowering.py',
     "        if is_runtime_error(expr):\n            fail(line, 'une valeur Int est requise, reçu runtime::Error')",
     "        if is_runtime_error(expr):\n            return value_place(expr[1]) if expr[0] == 'name' else '5'",
     'test_runtime_error_cannot_be_reinterpreted_as_integer_or_reference'),
    ('async_error_status_lost','async_lowering.py',
     "steps.append(f'frame->{member} = (CrustRuntimeError){result}.status;')",
     "steps.append(f'frame->{member} = (CrustRuntimeError)0;')",
     'test_async_error_branch_survives_yield_and_leaves_no_borrow'),
]


def main():
    successful=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: mutation anchor changed')
        with tempfile.TemporaryDirectory(prefix='crust-error-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_runtime_error_values.RuntimeErrorValueTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-1800:],flush=True)
            successful &= detected
    return 0 if successful else 1


if __name__=='__main__':sys.exit(main())
