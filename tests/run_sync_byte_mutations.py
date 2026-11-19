"""Faults applied only to temporary compiler copies, after a green baseline."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('byte_argument_unprotected',
  'held = list(local_utf8_loans(operand, value))\n                    loans.extend(held)',
  'held = list(local_utf8_loans(operand, value))\n                    pass',
  'test_prepared_source_through_suspended_argument_and_early_return'),
 ('byte_return_alternative_lost', 'retained_views.extend(argument_loans[target.parameter])',
  'if target.parameter == 0: retained_views.extend(argument_loans[target.parameter])',
  'test_conditional_result_and_unreturned_argument'),
 ('byte_result_wrong_address',
  "steps.append(f'{value} = {call};')\n        if signature in owned_sync_types:",
  "steps.append(f'{value} = {prepared[0] if signature in view_sync_types and prepared else call};')\n        if signature in owned_sync_types:",
  'test_conditional_result_and_unreturned_argument'),
 ('byte_source_contract_ignored',
  "if (contract is not None and contract.result_type[0] in ASYNC_CAPTURE_VIEW_MODES",
  "if (False and contract is not None and contract.result_type[0] in ASYNC_CAPTURE_VIEW_MODES",
  'test_async_contract_drops_unreturned_source_after_join'),
 ('local_byte_loan_lost',
  "if expr[0] == 'ref' and expr[1] in byte_bindings:\n            return ((expr[1], 'ref'),)",
  "if expr[0] == 'ref' and expr[1] in byte_bindings:\n            return ()",
  'test_direct_byte_place_drop_and_future_loop_use'),
]

def run(folder,test):
    return subprocess.run([sys.executable,'-c',f'''import sys,unittest
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName({test!r})
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not r.wasSuccessful())
'''],cwd=folder,capture_output=True,text=True,timeout=120)

def main():
    baseline=run(ROOT,'test_sync_byte_borrows')
    print('BASELINE', 'PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-sync-byte-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/'async_lowering.py').write_text(source.replace(before,after))
            result=run(folder,'test_sync_byte_borrows.SyncByteBorrowTests.'+test)
            # Rejection of the valid oracle case is also a semantic detection,
            # provided it is the compiler's Error, not a broken mutation/import.
            semantic_error=('crust.Error:' in result.stderr and 'ERROR:' in result.stderr)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or semantic_error)
            print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(result.stderr[-4500:],flush=True)
            success &= detected
    return 0 if success else 1

if __name__=='__main__':sys.exit(main())
