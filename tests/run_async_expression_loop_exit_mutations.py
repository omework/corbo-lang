"""Controlled faults in branch selection, returned provenance and cleanup."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS = [('initializer_exit_erased',
  'async_lowering.py',
  '            yield from in_expression(statement.args[1], definitions)',
  '            pass # injected fault: omit initializer exits',
  'test_recorded_initializer_and_provenance'),
 ('continue_emits_break',
  'async_lowering.py',
  "        steps.append(f'{op};')",
  "        steps.append('break;')",
  'test_continue_in_initializer_and_assignment'),
 ('expression_cleanup_erased',
  'async_lowering.py',
  '        cleanup_async_values(names, returned, line)',
  '        cleanup_async_values((), returned, line)',
  'test_break_cleans_expression_child_and_scope_before_slot_reuse'),
 ('native_child_cleanup_erased',
  'async_lowering.py',
  "        steps.append(f'task_discard({task});')",
  "        steps.append(f'(void){task};')",
  'test_break_cleans_expression_child_and_scope_before_slot_reuse')]

def main():
 success=True
 for name,filename,before,after,test in MUTATIONS:
  if sys.argv[1:] and name not in sys.argv[1:]:continue
  source=(ROOT / 'prototype'/filename).read_text()
  if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
  with tempfile.TemporaryDirectory(prefix='crust-async-expr-exit-mut-') as folder:
   target=Path(folder)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   (target/filename).write_text(source.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_expression_loop_exits.AsyncExpressionLoopExitTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
   run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
   invariant=(name=='expression_cleanup_erased' and 'crust.Error:' in run.stderr
              and 'les sorties de boucle async doivent conserver les mêmes obligations de nettoyage' in run.stderr)
   detected=run.returncode==1 and ('FAIL:' in run.stderr or invariant)
   print(name, 'DETECTED (compiler invariant)' if detected and invariant else
         'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
   print(run.stderr[-2000:],flush=True);success &= detected
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
