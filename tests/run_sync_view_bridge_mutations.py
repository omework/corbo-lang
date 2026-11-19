"""Mutate copied compilers to challenge sync/async view contracts."""
from pathlib import Path
import shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('fallible_call_discard_allowed', 'async_lowering.py',
  "if sync_signature(statement.args[0])[1].startswith('Result<'):",
  "if False and sync_signature(statement.args[0])[1].startswith('Result<'):",
  'test_fallible_helper_result_requires_explicit_use', ('Error not raised',)),
 ('result_loans_erased', 'async_lowering.py',
  'utf8_result_loans[value] = tuple(retained_views)', 'utf8_result_loans[value] = ()',
  'test_text_local_result_survives_suspension_and_releases_other_capture', ('Error not raised',)),
 ('prepared_view_loan_erased','async_lowering.py',
  'held = list(local_utf8_loans(operand, value))\n                    loans.extend(held)',
  'held = list(local_utf8_loans(operand, value))\n                    loans.extend(())',
  'test_ordered_arguments_and_suspension',('Error not raised',)),
 ('computed_slice_loan_erased','async_lowering.py',
  "utf8_result_loans[value] = tuple(loans)\n        return value\n\n    def condition_value",
  "utf8_result_loans[value] = ()\n        return value\n\n    def condition_value",
  'test_composed_text_and_byte_views_keep_storage',('Error not raised',)),
 ('helper_result_contract_ignored','async_lowering.py',
  'if (contract is not None and contract.result_type[0] in ASYNC_CAPTURE_VIEW_MODES',
  'if (False and contract is not None and contract.result_type[0] in ASYNC_CAPTURE_VIEW_MODES',
  'test_independent_result_dependency_model',('emprunt encore utilisé',)),
)

def main():
 success=True
 for name,filename,before,after,method,diagnostics in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-sync-view-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;original=path.read_text();assert original.count(before)==1,(name,original.count(before))
   path.write_text(original.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_sync_view_bridges.SyncViewBridgeTests.{method}'))
sys.exit(not r.wasSuccessful())'''
   result=subprocess.run([sys.executable,'-c',script],cwd=directory,capture_output=True,text=True,timeout=120)
  detected=result.returncode==1 and any(d in result.stderr for d in diagnostics)
  print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);success &= detected
 return int(not success)
if __name__=='__main__':sys.exit(main())
