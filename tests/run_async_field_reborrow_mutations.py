"""Path/ancestry faults exercised against unchanged tests on temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('whole_carrier_reserved',
  "loans = project_result_field_loans([(name, reservation), *received_refs.get(name, ())],\n                                           reference_types[name], path)",
  'loans = [(name, reservation), *received_refs.get(name, ())]',
  'test_disjoint_fields_and_target_identity'),
 ('ancestry_omitted',
  "loans = project_result_field_loans([(name, reservation), *received_refs.get(name, ())],\n                                           reference_types[name], path)",
  'loans = [((name, path), reservation)]',
  'test_alias_scope_and_ancestry_projection'),
 ('borrow_conflict_check_omitted',
  'check_access(name, line, write=reservation == \'mut\', path=path)\n        loans = project_result_field_loans(',
  'pass # skip borrow conflict check\n        loans = project_result_field_loans(',
  'test_disjoint_fields_and_target_identity'),
 ('helper_projection_loan_omitted',
  "retained.extend(project_result_field_loans(argument_loans[target.parameter], typ,\n                                                               tuple(target.field.lstrip('.').split('.'))))",
  'pass # omit returned projection loan',
  'test_helper_and_method_projected_results'),
 ('child_result_loan_omitted',
  "fail(line, 'capture de champ : type ou mode incompatible')\n                    active_loans.pop(id(inherited), None)\n                    loans.extend(inherited)\n                    if index in result_paths:\n                        returned_loans.extend(inherited)",
  "fail(line, 'capture de champ : type ou mode incompatible')\n                    active_loans.pop(id(inherited), None)\n                    loans.extend(inherited)",
  'test_child_result_keeps_projected_field_reserved'),
 ('direct_field_pointer_collapsed',
  "pointer = f'(int *)((unsigned char *){cell}->fields + ({offset}))'",
  "pointer = f'{cell}->fields'",
  'test_disjoint_fields_and_target_identity'),
 ('immutable_reference_binding_denied',
  'member = declare(name, statement.line)\n            references[name], reference_types[name] = mode, typ',
  "if mode == 'mut' and not statement.mutable:\n                fail(statement.line, 'mutation: immutable binding denied')\n            member = declare(name, statement.line)\n            references[name], reference_types[name] = mode, typ",
  'test_modes_levels_and_reference_binding'),
]


def run(folder,test):
    script=f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_field_reborrows as m
counts={{'native_success':0,'rejected_checks':0}}
original=m.AsyncFieldReborrowTests.run_c_oracle
def counted(self,code,expected_error=None):
    result=original(self,code,expected_error)
    counts['native_success']+=1
    return result
m.AsyncFieldReborrowTests.run_c_oracle=counted
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
    baseline=run(ROOT,'test_async_field_reborrows')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-field-reborrow-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/'async_lowering.py').write_text(source.replace(before,after))
            result=run(folder,'test_async_field_reborrows.AsyncFieldReborrowTests.'+test)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or
                       'ERROR:' in result.stderr and 'crust.Error:' in result.stderr)
            status='DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True);print(result.stdout+result.stderr[-6000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
