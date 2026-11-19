"""Faults in async output placement, lifetime contracts and cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('omit_output_storage_flag','async_result_storage.py',
  "return any(candidate.kind == 'fresh'", "return False and any(candidate.kind == 'fresh'", 'test_recorded_copy_return'),
 ('omit_return_producers','async_local_placement.py',
  'returned.append(evaluate(args[0], env))', 'pass', 'test_result_identity_after_child_release'),
 ('forget_pool_result_source','async_result_storage.py',
  "kinds.add('pool'); parameters.add(source.index)", "kinds.add('pool')", 'test_pool_copy_keeps_pool_but_not_original'),
 ('close_external_output_source','async_lowering.py',
  "local_pools[destination] = '(*frame->result_storage)'", "local_pools[destination] = '(*frame->result_storage)'\n        scopes[0][0][destination] = None", 'test_suspended_child_discards_partial_result'),
 ('overwrite_parameter_map','crust.py',
  "captured_targets = tuple(self.async_reference_row_captures(loan))", "captured_targets = tuple(self.async_reference_row_captures(loan)); targets_by_parameter = {}", 'test_reference_row_capture_and_independent_result'),
 ('lose_runtime_destination','async_lowering.py',
  'frame->result_storage = result_storage;', 'frame->result_storage = NULL; (void)result_storage;',
  'test_result_identity_after_child_release'),
)


def main():
 suite='test_async_result_storage.AsyncResultStorageTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-result-storage-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;source=path.read_text();assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)

if __name__=='__main__':sys.exit(main())
