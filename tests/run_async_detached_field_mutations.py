"""Path/ancestry faults exercised against unchanged tests on temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('carrier_retained_in_local_result', 'async_lowering.py', "return [(target, 'shared_target' if mode != 'storage' else mode) for target, mode in projected]", 'return projected', 'test_detached_local_value_allows_mutable_carrier_call'), ('detached_target_omitted', 'crust.py', 'cell_dependencies.append((f\'ref.{key.split(".")[1]}\', roots))', 'cell_dependencies.append((f\'ref.{key.split(".")[1]}\', ()))', 'test_direct_named_and_explicit_shared_reborrow'), ('detached_ancestry_omitted', 'crust.py', 'parents.update(cell_parents)', 'pass # omit detached ancestry', 'test_shared_result_keeps_external_mutable_ancestor'), ('mutable_field_detached', 'crust.py', "if typ == '&Int':\n                            roots, parents = self.struct_shared_reference", "if typ in ('&Int', '&mut Int'):\n                            roots, parents = self.struct_shared_reference", 'test_mutable_fields_do_not_detach_or_copy'), ('helper_pointer_abi_wrong', 'crust.py', "value = f'&({value})->value'", 'value = value', 'test_sync_helpers_methods_and_reverse_relay'), ('block_lifetime_check_omitted', 'crust.py', "if result and result[0] in ('ref', 'mut'):\n                self.check_reference_destination(result[2], parent)", "if False and result and result[0] in ('ref', 'mut'):\n                self.check_reference_destination(result[2], parent)", 'test_block_reference_keeps_target_and_mutable_capability')]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_detached_field_returns as m
counts={{'native_success':0,'rejected_checks':0}}
original=m.AsyncDetachedFieldTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success']+=1
    return result
m.AsyncDetachedFieldTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_detached_field_returns')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,module,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/module).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-detached-field-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/module).write_text(source.replace(before,after))
            result=run(folder,'test_async_detached_field_returns.AsyncDetachedFieldTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
