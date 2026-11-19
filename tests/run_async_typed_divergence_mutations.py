"""Controlled faults in branch selection, returned provenance and cleanup."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('typed_noncontinuation_disabled',
  'async_lowering.py',
  '            if known_type:',
  '            if False:',
  'test_recorded_typed_initializer'),
 ('unknown_annotation_accepted',
  'async_lowering.py',
  '            if known_type:',
  '            if True:',
  'test_annotations_do_not_skip_lifetime_type_or_consumption_checks'),
 ('returned_source_erased',
  'async_lowering.py',
  'cache[name] = frozenset(scan(body, {}, {}))',
  'cache[name] = frozenset(sorted(scan(body, {}, {}))[:1])',
  'test_array_shapes_reference_elements_and_scalars'),
 ('prepared_cleanup_erased',
  'async_lowering.py',
  '        for owner_depth, cells, loans in reversed(pending_capture_groups):',
  '        for owner_depth, cells, loans in ():',
  'test_typed_exit_cleans_owned_child_before_reuse')]

def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-async-typed-divergence-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_typed_divergence.AsyncTypedDivergenceTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   detected=run.returncode==1 and 'FAIL:' in run.stderr
   print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
