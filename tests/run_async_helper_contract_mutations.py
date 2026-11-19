"""Path/ancestry faults exercised against unchanged tests on temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('helper_contract_unavailable',
  'async_lowering.py',
  'contract = sync_result_contract(callee)',
  'contract = None',
  'test_recorded_contract_and_conflicts'),
 ('helper_path_erased',
  'async_lowering.py',
  "suffix = tuple(target.field.lstrip('.').split('.')) if target.kind != 'parameter' else ()",
  'suffix = ()',
  'test_recorded_contract_and_conflicts'),
 ('factory_path_unprojected',
  'results.py',
  "projects_structure = index in result_paths and '' in self.analyzer.enums.get(capture_type, {})",
  'projects_structure = False',
  'test_handle_factory_and_parameter_contract'),
 ('helper_alternative_omitted',
  'async_lowering.py',
  'for target in contract.result.reference_targets:\n'
  "                if target.kind not in ('parameter', 'inline_field_parameter', "
  "'indirect_field_parameter', 'detached_field_parameter'):",
  'for target in sorted(contract.result.reference_targets)[:1]:\n'
  "                if target.kind not in ('parameter', 'inline_field_parameter', "
  "'indirect_field_parameter', 'detached_field_parameter'):",
  'test_conditional_helper_preserves_both_paths'),
 ('symbolic_capture_fields_omitted',
  'crust.py',
  "add_field_dependencies(target, index, prefix=f'capture.{position}/')",
  'pass # symbolic capture fields omitted',
  'test_finished_handle_parameter'),
 ('projected_signature_classification_omitted',
  'crust.py',
  'if any(candidate.array_capture is not None for _, candidates in dependencies for candidate in candidates):',
  'if False and any(candidate.array_capture is not None for _, candidates in dependencies for candidate in candidates):',
  'test_finished_handle_parameter')]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_helper_result_contracts as m
counts={{'native_success':0,'rejected_checks':0}}
original=m.AsyncHelperContractTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success']+=1
    return result
m.AsyncHelperContractTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_helper_result_contracts')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,module,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/module).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-helper-contract-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/module).write_text(source.replace(before,after))
            result=run(folder,'test_async_helper_result_contracts.AsyncHelperContractTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
