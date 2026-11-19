"""Fault injection for independent outer status, payload, and return typing."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('direct_join_payload_erased','crust.py',
  "self.lines.append(f'{c}.{field} = {storage};')",
  "self.lines.append(f'{c}.{field} = {storage};')\n            if mode == 'int_option':\n                self.lines.append(f'{c}.{field}.value = 0;')",
  'test_direct_join_preserves_each_payload_field'),
 ('vector_capture_mode_erased','crust.py',
  'elif mode in ASYNC_VALUE_RESULT_FAMILIES and kind != mode:',
  'elif False:', 'test_sync_creation_does_not_erase_vector_result_mode'),
 ('vector_match_status_erased','async_lowering.py',
  "result = temporary(VECTOR_VALUE_RESULT_CTYPES[mode])\n        steps.append(f'{result} = {value};')",
  "result = temporary(VECTOR_VALUE_RESULT_CTYPES[mode])\n        steps.append(f'{result} = {value}; {result}.status = 0;')",
  'test_result_families_and_variants_cross_nested_waits'),
 ('rejected_scalar_payload_erased','async_lowering.py',
  "return f'{storage}.value', 'u8' if mode in ('byte_option', 'byte_replace', 'byte_try_push') else 'Int'",
  "return ('0' if error else f'{storage}.value'), 'u8' if mode in ('byte_option', 'byte_replace', 'byte_try_push') else 'Int'",
  'test_result_families_and_variants_cross_nested_waits'),
 ('result_pattern_shape_erased','async_lowering.py',
  "if tag[2] not in tuple(('int', value) for value in allowed) or bad_payload:\n            fail(line, 'match de résultat Vector : type ou motif incompatible')",
  "if False:\n            fail(line, 'match de résultat Vector : type ou motif incompatible')",
  'test_match_checks_option_result_unit_and_byte'),
]


def main():
    success=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: mutation anchor changed')
        with tempfile.TemporaryDirectory(prefix='crust-vector-result-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_vector_results.AsyncVectorResultTests.{test}')
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
