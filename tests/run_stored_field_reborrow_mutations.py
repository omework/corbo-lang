"""Path/ancestry faults exercised against unchanged tests on temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('allocation_reference_replaced_by_inline',
  'crust.py',
  "if capability and capability[0] == 'mut' and (capability[1] == 'Int' or capability[1] in "
  'self.enums):',
  "if capability and capability[0] == 'mut' and capability[1] in self.enums:",
  'test_direct_and_named_shared_construction'),
 ('helper_payload_classification_wrong',
  'results.py',
  "targets = self.inline_field_targets(carrier, path, 'indirect_field_parameter')\n"
  "            return {'next'}, Value(mode, 'Int',\n"
  '                                    reference_targets=targets)',
  "targets = self.inline_field_targets(carrier, path, 'indirect_field_parameter')\n"
  "            return {'next'}, Value(mode, 'Int',\n"
  '                                    reference_targets=targets, payload_reference=True)',
  'test_sync_helpers_methods_and_relay_into_constructor'),
 ('original_field_reservation_omitted',
  'crust.py',
  'borrow_parents=(binding,), match_reservation=True,\n'
  '                                   reserved_field=place[2]))',
  'borrow_parents=(binding,), match_reservation=False,\n'
  '                                   reserved_field=place[2]))',
  'test_direct_and_named_shared_construction'),
 ('detached_ancestry_omitted',
  'crust.py',
  'parents.update(cell_parents)',
  'pass # lose original mutable capability',
  'test_recorded_case_and_original_carrier_protection'),
 ('projected_capture_forbidden',
  'crust.py',
  'or parent.array_root or parent.match_reservation and parent.reserved_field is None',
  'or parent.array_root or parent.match_reservation',
  'test_recorded_case_and_original_carrier_protection'),
 ('borrowed_container_origin_omitted',
  'crust.py',
  "if target.kind == 'indirect_field_parameter':\n"
  "                    mode = self.field_modes(summary.typ).get(name, 'ref')",
  "if False and target.kind == 'indirect_field_parameter':\n"
  "                    mode = self.field_modes(summary.typ).get(name, 'ref')",
  'test_returned_and_copied_shared_container_keeps_capability')]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_stored_field_reborrows as m
counts={{'native_success':0,'rejected_checks':0}}
original=m.StoredFieldReborrowTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success']+=1
    return result
m.StoredFieldReborrowTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_stored_field_reborrows')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,module,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/module).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-stored-field-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/module).write_text(source.replace(before,after))
            result=run(folder,'test_stored_field_reborrows.StoredFieldReborrowTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
