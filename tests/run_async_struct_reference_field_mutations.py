"""Controlled faults on disposable copies; source expectations stay unchanged."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('mixed_layout_as_ints','async_lowering.py',
  "return name, f'frame->{fields[name]}', offset, tuple(path.split('.')), field_type",
  "return name, f'frame->{fields[name]}', f'{index} * sizeof(int)', tuple(path.split('.')), field_type",
  'test_recorded_case_and_mixed_offsets'),
 ('field_read_replaced','async_lowering.py',
  "else f'cell_load_ref({cell}, {offset})->value')", "else '0')",
  'test_recorded_case_and_mixed_offsets'),
 ('bridge_dependencies_lost','crust.py',
  'allocation.dependencies = tuple(links)', 'allocation.dependencies = ()',
  'test_helpers_methods_and_mutable_pointee'),
 ('reset_only_direct_capture','crust.py',
  'allocation.item_sources, *(target.sources for target in self.retained_dependencies(allocation))',
  'allocation.item_sources, *(target.sources for target in self.dependency_targets(allocation))',
  'test_escape_and_legacy_reset'),
 ('capture_root_lost','crust.py',
  "dependencies.append((f'{reservation}.{index}', roots))",
  "dependencies.append((f'{reservation}.{index}', ()))",
  'test_transitive_reservation_before_and_after_launch'),
 ('unsummarized_updates_allowed','async_lowering.py',
  'if contract.result.structure_fields:', 'if False:',
  'test_type_and_dependency_update_boundaries'),
]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_struct_reference_fields as m
counts={{'native_success':0,'rejected_checks':0}}
original=m.AsyncStructReferenceFieldTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success']+=1
    return result
m.AsyncStructReferenceFieldTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_struct_reference_fields')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    successful=True
    for name,module,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/module).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-reference-field-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/module).write_text(source.replace(before,after))
            result=run(folder,'test_async_struct_reference_fields.AsyncStructReferenceFieldTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            # This defensive boundary can be backed by an unrelated unsupported
            # representation check. A changed diagnostic is not evidence that a
            # memory-safety violation was detected.
            rejected_elsewhere=(name=='unsummarized_updates_allowed' and
                                'does not match' in result.stderr and 'Error not raised' not in result.stderr)
            stage_divergence=(name=='unsummarized_updates_allowed' and
                              'does not match' in result.stderr and 'Error not raised' in result.stderr)
            status=('STAGE_DIVERGENCE' if stage_divergence else
                    'REJECTED_ELSEWHERE' if rejected_elsewhere else 'DETECTED' if detected
                    else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE')
            print(name,status,flush=True)
            print(result.stdout+result.stderr[-6500:],flush=True)
            successful &= detected or rejected_elsewhere
    return 0 if successful else 1


if __name__=='__main__':sys.exit(main())
