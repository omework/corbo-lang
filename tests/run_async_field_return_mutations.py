"""Path/ancestry faults exercised against unchanged tests on temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('field_path_erased',
  'async_lowering.py',
  "origins = tuple((index, path + tuple(place[2].split('.'))) for index, path in inherited)",
  'origins = tuple((index, ()) for index, path in inherited)',
  'test_direct_and_named_results_retain_only_the_field'),
 ('relay_suffix_erased',
  'async_lowering.py',
  'origins.update((source, prefix + suffix) for source, prefix in inherited)',
  'origins.update((source, prefix) for source, prefix in inherited)',
  'test_async_relays_and_synchronous_projected_helpers'),
 ('await_projection_omitted',
  'async_lowering.py',
  'returned_loans.extend(project_result_field_loans(capture_loans, typ, path))',
  'pass # omit returned projection',
  'test_async_relays_and_synchronous_projected_helpers'),
 ('join_reserves_whole_carrier',
  'crust.py',
  'if target.typ in self.struct_fields and any(path for path in paths):',
  'if False and target.typ in self.struct_fields and any(path for path in paths):',
  'test_direct_and_named_results_retain_only_the_field'),
 ('join_target_capability_omitted',
  'crust.py',
  'field_paths = self.struct_mutable_field_paths(binding, field, binding)',
  'field_paths = tuple((root, binding) for root in self.struct_int_roots(binding, field))',
  'test_mutable_field_target_and_carrier_remain_protected'),
 ('return_pointer_offset',
  'async_lowering.py',
  "steps.append(f'frame->result = {pointer};')\n        elif returns_int:",
  "steps.append(f'frame->result = {pointer} + 1;')\n        elif returns_int:",
  'test_recorded_case'),
 ('sync_join_contract_path_omitted',
  'results.py',
  'origins = self.async_structure_result_targets(value, capture_type, result_paths[index])',
  'pass # keep whole argument origin',
  'test_synchronous_join_relay_preserves_path_and_ancestry'),
 ('sync_join_ancestry_omitted',
  'crust.py',
  'borrow_parents=(*ancestry, *target.borrow_parents))',
  'borrow_parents=target.borrow_parents)',
  'test_synchronous_join_relay_preserves_path_and_ancestry')]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_field_reference_returns as m
counts={{'native_success':0,'rejected_checks':0}}
original=m.AsyncFieldReturnTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success']+=1
    return result
m.AsyncFieldReturnTests.run_c_oracle=counted
def wrap(original):
    def checked(*a,**kw):
        try:return original(*a,**kw)
        except m.Error:
            counts['rejected_checks']+=1
            raise
    checked.__name__=original.__name__
    return checked
m.verify_program=wrap(m.verify_program)
m.compile_source=wrap(m.compile_source)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName({test!r}))
print(json.dumps(counts))
sys.exit(not result.wasSuccessful())
'''
    return subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=180)


def main():
    baseline=run(ROOT,'test_async_field_reference_returns')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,module,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/module).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-field-return-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/module).write_text(source.replace(before,after))
            result=run(folder,'test_async_field_reference_returns.AsyncFieldReturnTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
