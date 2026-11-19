"""Controlled faults against unchanged direct-collection construction oracles."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('collection_type_erased', "owned_result_types[cell] = typ", "owned_result_types[cell] = 'Int'",
     'test_default_named_creation_growth_return_and_reuse'),
    ('direct_result_origin_ignored', "if op in ('task_spawn', 'transfer', 'array_transfer', 'new_transfer'):\n            return expression(expr[1], bindings, breaks)",
     "if op in ('task_spawn', 'transfer', 'array_transfer'):\n            return expression(expr[1], bindings, breaks)",
     'test_direct_result_keeps_only_its_source'),
    ('slot_cleanup_omitted', "steps.extend((f'cell_drop({member});', f'{member} = NULL;'))",
     "steps.append(f'{member} = NULL;')", 'test_replacement_and_loop_cleanup_before_reuse'),
    ('element_index_erased', "({element} *)vector_checked_item(frame->{fields[name]}, {index});",
     "({element} *)vector_checked_item(frame->{fields[name]}, 0);", 'test_element_reborrows_child_and_last_use'),
    ('index_evaluation_unreserved', "active_loans[id(loans)] = loans\n            try:\n                index = expression(projection[2], line)",
     "# omit collection reservation\n            try:\n                index = expression(projection[2], line)",
     'test_index_suspension_reserves_collection_before_child_capture'),
    ('immutable_element_mutable', "if mode == 'mut' and not (references.get(name) == 'mut'\n                                     or references.get(name) == 'owned' and name in mutable):",
     "if False: # mutable access to immutable collection", 'test_element_reborrows_child_and_last_use'),
]


def run(folder, test):
    script = f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_collection_new as m
counts={{'native_success':0,'expected_runtime_failure':0,'rejected_programs':0}}
original=m.AsyncCollectionNewTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success' if expected_error is None else 'expected_runtime_failure']+=1
    return result
m.AsyncCollectionNewTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_collection_new')
    print('BASELINE', 'PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-collection-new-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/'async_lowering.py').write_text(source.replace(before,after))
            result=run(folder,'test_async_collection_new.AsyncCollectionNewTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
