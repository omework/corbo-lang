"""Controlled faults in branch selection, returned provenance and cleanup."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('early_return_origin_erased',
  'async_lowering.py',
  '            yield from scan(expr, task_calls, awaited)\n'
  '            mode, origins = reference_origin(expr, task_calls, awaited, value.line)',
  '            mode, origins = reference_origin(expr, task_calls, awaited, value.line)',
  'test_early_return_keeps_its_source_in_contract'),
 ('one_break_origin_erased',
  'async_lowering.py',
  'return possibilities[0][0], set().union(*(origins for _, origins in possibilities))',
  'return possibilities[0][0], possibilities[0][1]',
  'test_returned_result_reserves_every_source'),
 ('loop_reservations_erased',
  'async_lowering.py',
  "loans = list(dict.fromkeys(loop['reference_loans']))",
  'loans = []',
  'test_returned_result_reserves_every_source'),
 ('scope_cleanup_erased',
  'async_lowering.py',
  '        cleanup_async_values(names, returned, line)',
  '        cleanup_async_values((), returned, line)',
  'test_break_cleans_inactive_owned_child_before_receiving_reference')]

def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-async-loop-ref-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_loop_references.AsyncLoopReferenceTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   detected=run.returncode==1 and 'FAIL:' in run.stderr
   print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
