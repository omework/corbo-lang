"""Controlled faults in branch selection, returned provenance and cleanup."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('source_loan_removed','async_lowering.py',
  'loans = list(dict.fromkeys(selected_reference_loans))', 'loans = list(dict.fromkeys(selected_reference_loans))[:1]', 'test_exclusive_alternatives_last_use_and_ancestry'),
 ('contract_alternative_removed','async_lowering.py',
  "return mode, set().union(*(origins for _, origins in possibilities))", "return mode, possibilities[0][1]", 'test_await_branches_forwarded_to_child_and_returned'),
 ('ancestor_chain_removed','async_lowering.py',
  "loans = [(name, reservation), *received_refs.get(name, ())]", "loans = [(name, reservation)]", 'test_departing_alias_keeps_ancestors_and_releases_after_use'),
 ('swapped_pointer_choice','async_lowering.py',
  "return emit_branches(test, expr[2], expr[3], line, valued=True, construct='if',", "return emit_branches(test, expr[3], expr[2], line, valued=True, construct='if',", 'test_aliases_nested_blocks_both_modes'),
]

def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-async-local-ref-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_local_references.AsyncLocalReferenceTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   detected=run.returncode==1 and 'FAIL:' in run.stderr
   print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
