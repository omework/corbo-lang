"""Local source lifetime faults, using unchanged tests in temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ('new_source_origin_lost', "keep_storage(cell, pool_storage(expr[1]))",
     'keep_storage(cell, ())', 'test_pool_does_not_escape_with_returned_allocation'),
    ('boundary_check_omitted', 'if storage_of(value) & leaving:', 'if False:',
     'test_pool_does_not_escape_with_returned_allocation'),
    ('mapping_close_omitted', "steps.append(f'source_close(&{local_pools[name]});')", 'pass # leak mapping',
     'test_mapping_closed_once_per_iteration_and_final_scope'),
    ('child_storage_dependency_lost', '                    loans.extend(held_storage)\n', '                    pass # forget source kept by child\n',
     'test_inner_scope_task_and_join_cannot_escape_pool'),
    ('await_result_origin_lost', "keep_storage(result, (target for target, mode in returned_loans if mode == 'storage'))",
     'keep_storage(result, ())', 'test_pool_does_not_escape_with_returned_allocation'),
    ('left_branch_origin_lost', "storage = {name: left[8].get(name, frozenset()) | right[8].get(name, frozenset())",
     "storage = {name: right[8].get(name, frozenset())", 'test_branch_origin_union_blocks_only_the_local_alternative'),
]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_local_pools as m
counts={{'native_success':0,'expected_runtime_failure':0,'rejected_programs':0}}
original=m.AsyncLocalPoolTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success' if expected_error is None else 'expected_runtime_failure']+=1
    return result
m.AsyncLocalPoolTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_local_pools')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-local-pool-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/'async_lowering.py').write_text(source.replace(before,after))
            result=run(folder,'test_async_local_pools.AsyncLocalPoolTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
