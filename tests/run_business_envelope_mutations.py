"""Fault injection for independent outer status, payload, and return typing."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('sync_capture_type_erased','crust.py',
  "elif mode in ('runtime_error', *ERROR_VALUE_TYPES, *PLAIN_JOIN_TYPES) and kind != mode:",
  "elif False:", 'test_sync_creation_checks_the_full_capture_type'),
 ('unused_business_result_accepted','async_lowering.py',
  "if VALUE_MODES[payload_field].startswith('Result<') and not has_future_value_use(payload, body):",
  "if False:", 'test_extracted_fallible_payload_requires_use'),
 ('async_business_status_erased','async_lowering.py',
  "steps.append(f'frame->{fields[payload]} = {result}.{field};')",
  "steps.append(f'frame->{fields[payload]} = {result}.{field};')\n                        if payload_field == 'integer_conversion_result':\n                            steps.append(f'frame->{fields[payload]}.status = 0;')",
  'test_business_outcomes_survive_nested_contracts_and_capture'),
 ('sync_business_status_erased','crust.py',
  "self.lines.append(f'{c}.{field} = {storage};')",
  "self.lines.append(f'{c}.{field} = {storage};')\n            if mode == 'integer_conversion_result':\n                self.lines.append(f'{c}.{field}.status = 0;')",
  'test_business_outcomes_survive_nested_contracts_and_capture'),
]


def main():
    success=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: mutation anchor changed')
        with tempfile.TemporaryDirectory(prefix='crust-business-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_business_result_envelopes.BusinessResultEnvelopeTests.{test}')
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
