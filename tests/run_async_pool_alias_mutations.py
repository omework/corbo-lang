"""Named pool reference faults, using unchanged tests in temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('argument_root_loan_lost',
  "return f'frame->{fields[name]}', [(name, mode), *received_refs.get(name, ())]",
  "return f'frame->{fields[name]}', [(name, mode)]",
  'test_task_can_outlive_alias_binding_but_not_pool'),
 ('alias_storage_origin_lost',
  'else pool_alias_origins.get(name, frozenset())',
  'else frozenset()',
  'test_alias_origin_cannot_escape_by_creation_helper_or_child'),
 ('reference_level_check_omitted',
  "if (source_name in local_pools) == (operator == 'reborrow'):",
  'if False:',
  'test_mutable_alias_conflicts_and_reference_levels'),
 ('mutable_upgrade_check_omitted',
  "if mode == 'mut' and references[source_name] != 'mut':",
  'if False:',
  'test_alias_modes_annotations_and_immutable_source'),
 ('alias_creation_reservation_omitted',
  "check_access(source_name, statement.line, write=reservation == 'mut')",
  'pass # omit source reservation check',
  'test_mutable_alias_conflicts_and_reference_levels'),
 ('alias_binding_wrongly_kept_at_exit',
  '(mutable_slices | pool_alias_origins.keys()).intersection(local_names)',
  'mutable_slices.intersection(local_names)',
  'test_task_can_outlive_alias_binding_but_not_pool'),
 ('source_summary_alias_omitted',
  "if op in ('ref', 'mut', 'reborrow') and bindings.get(expr[1]) is not None and bindings[expr[1]][0] "
  "== 'source':",
  'if False:',
  'test_reborrowed_injected_pool_result_does_not_retain_other_source')]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_pool_aliases as m
counts={{'native_success':0,'expected_runtime_failure':0,'rejected_programs':0}}
original=m.AsyncPoolAliasTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success' if expected_error is None else 'expected_runtime_failure']+=1
    return result
m.AsyncPoolAliasTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_pool_aliases')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-pool-alias-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/'async_lowering.py').write_text(source.replace(before,after))
            result=run(folder,'test_async_pool_aliases.AsyncPoolAliasTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
