"""Controlled faults in branch selection, returned provenance and cleanup."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('swapped_arms','async_lowering.py',
  "args=(expr[1], arm(expr[2]), arm(expr[3]))", "args=(expr[1], arm(expr[3]), arm(expr[2]))", 'test_both_modes_and_suspended_arms'),
 ('one_origin_removed','async_lowering.py',
  'cache[name] = frozenset(scan(body, {}, {}))', 'cache[name] = frozenset(sorted(scan(body, {}, {}))[:1])', 'test_join_retains_both_sources_until_last_use'),
 ('cleanup_path_lost','async_lowering.py',
  "steps.append(f'frame->cleanup_path = {cleanup_paths.index(path) + 1};')", "steps.append('frame->cleanup_path = 0;')", 'test_cleanup_of_inactive_child_on_each_return'),
]

def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-async-ref-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_reference_returns.AsyncReferenceReturnTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   detected=run.returncode==1 and 'FAIL:' in run.stderr
   print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
