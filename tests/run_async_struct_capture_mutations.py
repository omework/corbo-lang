"""Structure capture boundary faults, using unchanged tests in temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('field_offset_collapsed',
  "return name, f'frame->{fields[name]}', offset, tuple(path.split('.')), field_type",
  "return name, f'frame->{fields[name]}', '0', tuple(path.split('.')), field_type",
  'test_mutable_fields_and_nested_layout'),
 ('field_write_omitted',
  "steps.append(f'cell_store_int({cell}, {offset}, {saved});')",
  'pass # omit field write',
  'test_mutable_fields_and_nested_layout'),
 ('mutable_field_guard_omitted',
  "if write and references.get(name) != 'mut':",
  'if False:',
  'test_mutable_fields_and_nested_layout'),
 ('field_write_loan_check_omitted',
  "check_access(name, line, write=True, path=path)\n        steps.append(f'cell_store_int",
  "pass # omit field access check\n        steps.append(f'cell_store_int",
  'test_relay_reborrow_and_child_lifetime'),
 ('child_root_loan_lost',
  'capture_loans = (loan, *received_refs.get(name, ()))',
  'capture_loans = (loan,)',
  'test_export_child_out_of_alias_block_preserves_root_loan'),
 ('scalar_structure_guard_omitted',
  'if reference_types.get(name) in reference_structs:',
  'if False:',
  'test_type_mismatch_and_scalar_shortcuts_rejected')]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_struct_captures as m
counts={{'native_success':0,'expected_runtime_failure':0,'rejected_programs':0}}
original=m.AsyncStructCaptureTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success' if expected_error is None else 'expected_runtime_failure']+=1
    return result
m.AsyncStructCaptureTests.run_c_oracle=counted
verify=m.verify_program
def checked(*a,**kw):
    try:return verify(*a,**kw)
    except m.Error:
        counts['rejected_programs']+=1
        raise
m.verify_program=checked
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName({test!r}))
print(json.dumps(counts))
sys.exit(not result.wasSuccessful())
'''
    return subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=150)


def main():
    baseline=run(ROOT,'test_async_struct_captures')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-struct-capture-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/'async_lowering.py').write_text(source.replace(before,after))
            result=run(folder,'test_async_struct_captures.AsyncStructCaptureTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
