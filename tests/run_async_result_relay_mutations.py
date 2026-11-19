"""Faults in async output placement, lifetime contracts and cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('omit_async_producer','async_local_placement.py',
  "return ('task', node.args[2][1]), {id(expr): expr}", 'return None', 'test_recorded_parent_and_relay'),
 ('omit_await_producer','async_local_placement.py',
  'return task[0][1], task[1]', 'return None', 'test_named_task_and_successive_parent_transfers'),
 ('forget_local_copy_input','async_local_placement.py',
  'plan = result_storage(node, local_parameters)', 'plan = result_storage(node)', 'test_local_copy_does_not_promote_original'),
 ('shorten_external_destination','async_lowering.py',
  'depths.setdefault(storage, -1)', 'depths.setdefault(storage, len(scopes))', 'test_relay_computed_and_named_returns'),
 ('omit_explicit_await_replacement','async_lowering.py',
  "('scope', 'if_expr', 'value_match', 'loop_expr', 'await')", "('scope', 'if_expr', 'value_match', 'loop_expr')", 'test_parent_replacement_and_loop'),
 ('lose_runtime_destination','async_lowering.py',
  'frame->result_storage = result_storage;', 'frame->result_storage = NULL; (void)result_storage;',
  'test_relay_suspended_cleanup_and_completed_identity'),
)


def main():
 suite='test_async_result_relays.AsyncResultRelayTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-result-relays-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;source=path.read_text();assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)

if __name__=='__main__':sys.exit(main())
