"""Fault injection for exact error kinds and status extraction."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('vector_error_status_erased','async_lowering.py',
  "return f'{storage}.status', ERROR_VALUE_TYPES[RESULT_ERROR_MODES[mode]]",
  "return '0', ERROR_VALUE_TYPES[RESULT_ERROR_MODES[mode]]",
  'test_error_from_each_operation_is_status_not_success_payload'),
 ('utf8_error_status_erased','async_lowering.py',
  "return f'{storage}.status', ERROR_VALUE_TYPES[mode]",
  "return '0', ERROR_VALUE_TYPES[mode]",
  'test_error_from_each_operation_is_status_not_success_payload'),
 ('sync_error_status_erased','crust.py',
  "return RESULT_ERROR_MODES[kind], f'(int)({value}).status', None",
  "return RESULT_ERROR_MODES[kind], '0', None",
  'test_sync_extraction_and_contracts_do_not_treat_errors_as_success'),
 ('nominal_capture_guard_removed','crust.py',
  "elif mode in ('runtime_error', *ERROR_VALUE_TYPES, *PLAIN_JOIN_TYPES) and kind != mode:",
  'elif False:',
  'test_nominal_type_boundaries'),
 ('error_match_type_guard_removed','async_lowering.py',
  "if tag[2] not in (('int', 0), ('int', ERROR_VALUE_TAGS[mode])) or tag[3] != ('int', 0):",
  'if False:',
  'test_nominal_type_boundaries'),
]


def main():
    success=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor')
        with tempfile.TemporaryDirectory(prefix='crust-error-value-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_builtin_error_values.BuiltinErrorValueTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-2200:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
