"""Controlled faults in branch selection, returned provenance and cleanup."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('result_carrier_erased','async_lowering.py',
  'if result_carrier is not None:', 'if False:', 'test_result_carrier_exclusive_until_last_use'),
 ('payload_ancestry_erased','async_lowering.py',
  "elif result_loans is not None:\n                            if direct:\n                                active_loans.pop(id(result_loans), None)\n                            payload_loans = list(result_loans)",
  "elif result_loans is not None:\n                            if direct:\n                                active_loans.pop(id(result_loans), None)\n                            payload_loans = []", 'test_match_binding_keeps_ancestor_inside_frame'),
 ('contract_fallback_erased','async_lowering.py',
  'return mode, set().union(*(origins for _, origins in possibilities))', 'return mode, possibilities[0][1]', 'test_every_source_reserved_after_return'),
 ('wrong_join_branch','async_lowering.py',
  "test = f'{result}.status == {status}'", "test = f'{result}.status != {status}'", 'test_modes_branch_order_and_launch_failure'),
]

def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-async-match-ref-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_match_references.AsyncMatchReferenceTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   detected=run.returncode==1 and 'FAIL:' in run.stderr
   print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
