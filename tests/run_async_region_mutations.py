"""Lexical region configuration faults, using unchanged tests in temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('inherited_limit_lost',
  'region_limits[-1] if limit is None else limit',
  '0 if limit is None else limit',
  'test_nested_inheritance_override_and_restoration'),
 ('parent_limit_not_restored',
  '            region_limits.pop()',
  '            pass # configuration leaks',
  'test_nested_inheritance_override_and_restoration'),
 ('string_region_ignored',
  'string_new({source}, UINT64_C({region_limits[-1]})',
  'string_new({source}, UINT64_C(0)',
  'test_nested_inheritance_override_and_restoration'),
 ('vector_region_ignored',
  'vector_new({source}, UINT64_C({region_limits[-1]})',
  'vector_new({source}, UINT64_C(0)',
  'test_region_exhaustion_after_transfer_is_atomic')]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_regions as m
counts={{'native_success':0,'expected_runtime_failure':0,'rejected_programs':0}}
original=m.AsyncRegionTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success' if expected_error is None else 'expected_runtime_failure']+=1
    return result
m.AsyncRegionTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_regions')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-async-region-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/'async_lowering.py').write_text(source.replace(before,after))
            result=run(folder,'test_async_regions.AsyncRegionTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
