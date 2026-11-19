"""Controlled faults in initialization, provenance and address selection."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('default_not_zero','async_lowering.py',
  "steps.extend((f'{initial} = 0;',", "steps.extend((f'{initial} = 7;',", 'test_types_and_fronts'),
 ('receiver_loan_erased','async_lowering.py',
  "loans = [(receiver, 'mut'), *received_refs.get(receiver, ())]", "loans = []", 'test_receiver_reserved_until_last_use'),
 ('wrong_case_address','crust.py',
  'return vector_item_at(items, items->length - 1);', 'return vector_item_at(items, 0);', 'test_types_and_fronts'),
 ('returned_provenance_erased','async_lowering.py',
  "return 'mut', {(index, ())}", "return 'mut', set()", 'test_returned_borrow_through_two_tasks'),
]
def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-push-new-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_vector_push_new.AsyncVectorPushNewTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   detected=run.returncode==1 and 'FAIL:' in run.stderr
   print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
