"""Temporary faults in specialization, state layout and type boundaries."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('forget_child_variant','async_lowering.py',
  'target = specialize(callee, frozenset(local_captures)) if local_captures else callee',
  'target = callee','test_copy_storage_and_suspended_cleanup'),
 ('forget_sync_variant','crust.py',
  'target_name = self.reserve_async_local_variant(name, frozenset(local_captures)) if local_captures else name',
  'target_name = name','test_sync_caller_and_mixed_copy_variants'),
 ('forget_captured_source','async_lowering.py',
  'storage_bindings[parameter] = frozenset({origin})',
  'storage_bindings[parameter] = frozenset()','test_copy_storage_and_suspended_cleanup'),
 ('wrong_slot_stride','async_lowering.py',
  "f'sizeof({storage_type}), {capacity}, crust_task_context.generations_{name});'",
  "f'sizeof({prefix}_state), {capacity}, crust_task_context.generations_{name});'",
  'test_copy_storage_and_suspended_cleanup'),
 ('allow_local_as_allocated_return','async_lowering.py',
  'if node.handle_result and storage_of(member) & implicit_stacks:',
  'if False:','test_explicit_allocation_return_rejects_local'),
 ('allow_local_as_allocated_capture','async_lowering.py',
  'if declaration.args[1][index][0] in declaration.handle_parameters:',
  'if False:','test_explicit_allocation_type_rejects_local'),
)

def main():
 suite='test_async_local_captures.AsyncLocalCaptureTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-local-capture-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;source=path.read_text();assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr and not 'clang: error:' in result.stderr
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)

if __name__=='__main__':sys.exit(main())
