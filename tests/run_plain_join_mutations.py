"""Contract typing, whole-result transfer, and fallible-use faults."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('sync_payload_type_erased','crust.py',
  "elif kind != mode:\n                    expected = '&' + typ if mode in ('text', 'byte_ref', *VECTOR_SLICE_MODES.values()) else typ",
  "elif False:\n                    expected = '&' + typ if mode in ('text', 'byte_ref', *VECTOR_SLICE_MODES.values()) else typ",
  'test_payload_type_is_checked_in_every_contract_and_annotation'),
 ('async_payload_type_erased','async_lowering.py',
  'if plain_join_mode(expr) != mode:', 'if False:',
  'test_async_capture_checks_payload_type_at_the_call'),
 ('launch_error_replaced_by_success','async_lowering.py',
  "steps.append(f'frame->{member} = {result[0]};')",
  "steps.append(f'frame->{member} = (CrustJoinResult){{.status=0, .value=17}};')",
  'test_async_join_annotation_assignment_alias_and_loop'),
 ('unused_loop_result_accepted','async_lowering.py',
  "if typ.startswith('Result<') and (name == '_' or\n                        name != export_name and not has_future_value_use(name, body[position + 1:])):",
  "if False:",
  'test_async_join_annotation_assignment_alias_and_loop'),
]


def main():
    success=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: mutation anchor changed')
        with tempfile.TemporaryDirectory(prefix='crust-join-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_plain_join_contracts.PlainJoinContractTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-1600:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
