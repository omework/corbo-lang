"""Controlled faults in branch selection, returned provenance and cleanup."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('unreachable_returns_included',
  'async_lowering.py',
  "                if hasattr(item, 'op') and branch_control_exit([item]):",
  '                if False:',
  'test_unreachable_return_does_not_add_a_source'),
 ('prepared_capture_cleanup_erased',
  'async_lowering.py',
  '        for owner_depth, cells, loans in reversed(pending_capture_groups):',
  '        for owner_depth, cells, loans in ():',
  'test_prepared_owner_cleanup_on_aborted_or_completed_call'),
 ('prepared_capture_depth_erased',
  'async_lowering.py',
  '            if owner_depth < depth:\n'
  '                continue\n'
  '            active_loans.pop(id(loans), None)',
  '            if owner_depth >= depth:\n'
  '                active_loans.pop(id(loans), None)',
  'test_prepared_owner_break_depth'),
 ('returned_source_erased',
  'async_lowering.py',
  'cache[name] = frozenset(scan(body, {}, {}))',
  'cache[name] = frozenset(sorted(scan(body, {}, {}))[:1])',
  'test_all_breaks_from_initializer_assignment_and_print')]

def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-async-diverging-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_diverging_expressions.AsyncDivergingExpressionTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   detected=run.returncode==1 and 'FAIL:' in run.stderr
   print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
