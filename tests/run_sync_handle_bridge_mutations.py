"""Mutate copied compilers to challenge sync/async handle contracts and resource transfer."""
from pathlib import Path
import shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('capture_loans_erased','async_lowering.py',
  'retained.extend(returned)\n            active_loans[id(retained)] = retained',
  'retained.clear()\n            active_loans[id(retained)] = retained',
  'test_local_capture_reserved_until_wait',('Error not raised',)),
 ('returned_loans_erased','async_lowering.py',
  "retained, signature[1], returned", "retained, signature[1], []",
  'test_returned_slices_and_last_use',('Error not raised',)),
 ('helper_result_projection_ignored','async_lowering.py',
  "if contract.result_type[0] == 'execution':", "if False and contract.result_type[0] == 'execution':",
  'test_capture_release_and_returned_target',('emprunt encore utilisé',)),
 ('joinable_resource_not_detached','async_runtime.py',
  'if (!source->error && !source->pooled &&', 'if (0 && !source->error && !source->pooled &&',
  'test_runtime_adoption_resource_contract',('AssertionError',)),
 ('launch_failure_erased','async_runtime.py',
  'target->error = source->error;', 'target->error = 0;',
  'test_runtime_adoption_resource_contract',('AssertionError',)),
 ('source_not_consumed','async_runtime.py',
  'if (atomic_exchange(&source->joined, 1)) abort();', 'if (atomic_load(&source->joined)) abort();',
  'test_runtime_adoption_resource_contract',('AssertionError',)),
)

def main():
 success=True
 for name,filename,before,after,method,diagnostics in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-sync-handle-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;original=path.read_text();assert original.count(before)==1,(name,original.count(before))
   path.write_text(original.replace(before,after))
   script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_sync_handle_bridges.SyncHandleBridgeTests.{method}'))
sys.exit(not r.wasSuccessful())'''
   result=subprocess.run([sys.executable,'-c',script],cwd=directory,capture_output=True,text=True,timeout=120)
  detected=result.returncode==1 and any(d in result.stderr for d in diagnostics)
  print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);success &= detected
 return int(not success)
if __name__=='__main__':sys.exit(main())
