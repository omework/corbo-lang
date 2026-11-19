"""Faults in selected pointer, alternative provenance and writer ancestry."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('condition_inverted','crust.py',
  "self.lines.append(f'if ({value}) {{')\n        self.lines.extend(branch_lines[0])",
  "self.lines.append(f'if (!({value})) {{')\n        self.lines.extend(branch_lines[0])",
  'test_mixed_inline_and_pool_pointer_layout'),
 ('one_source_forgotten','crust.py',
  'return selected_kind, result_c, (selected_type, tuple(selected_reference_paths.values()))',
  'return selected_kind, result_c, (selected_type, tuple(selected_reference_paths.values())[:1])',
  'test_local_bindings_reborrows_and_iteration_exits'),
 ('writer_ancestry_erased','crust.py',
  'descriptor = self.reference_descriptor(result_c, selected_reference_targets.values(),\n                                                       selected_parents.values())',
  'descriptor = self.reference_descriptor(result_c, selected_reference_targets.values(),\n                                                       ())',
  'test_conditional_match_projection_keeps_writer_reserved'),
 ('null_mixed_layout_pointer','crust.py',
  "code[index] = f'{result_c} = {pointer};'", "code[index] = f'{result_c} = NULL;'",
  'test_mixed_inline_and_pool_pointer_layout'),
]
def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-ref-expr-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_reference_expressions.ReferenceExpressionTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   invariant=(name=='writer_ancestry_erased' and run.returncode==1
              and 'crust.Error:' in run.stderr
              and 'invariant interne : emprunt mutable non exclusif' in run.stderr)
   detected=run.returncode==1 and 'FAIL:' in run.stderr or invariant
   print(name,'DETECTED (compiler invariant)' if invariant else 'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2300:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
