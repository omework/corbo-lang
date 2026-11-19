"""Faults in async output placement, lifetime contracts and cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('omit_future_output_contract','results.py',
  'output_sources = task_result_origins(declaration, captured_actuals)', 'output_sources = None', 'test_recorded_factory'),
 ('forget_forwarded_output','results.py',
  "getattr(definition, 'result_storage', False) or owned_result_parameters(", "False or owned_result_parameters(", 'test_nested_factories_and_forwarded_task_contracts'),
 ('reuse_original_local_source','async_result_storage.py',
  "return SourceOrigin('task_output_parameter', source.index, element=typ)", "return source", 'test_copy_factory_local_and_pool'),
 ('ignore_factory_output_plan','crust.py',
  'planned = self.task_output_destinations.get(id(expr))', 'planned = None', 'test_recorded_factory'),
 ('destroy_returned_task_in_bridge','crust.py',
  "if result is not None and result[0] in ('owned', 'task', 'execution', *JOIN_RESULT_TYPES):",
  "if result is not None and result[0] in ('owned', 'execution', *JOIN_RESULT_TYPES):", 'test_async_caller_and_parent_receiver'),
 ('lose_runtime_destination','async_lowering.py',
  'frame->result_storage = result_storage;', 'frame->result_storage = NULL; (void)result_storage;',
  'test_destination_and_cleanup_after_factory_return'),
 ('keep_old_completion_field','async_structure_effects.py',
  'for carrier, fields in task.deferred_field_updates:', 'for carrier, fields in ():',
  'test_factory_completion_updates_caller_fields'),
 ('forget_text_result_capture','async_lowering.py',
  'result_captures |= utf8_result_parameters(functions[signature[1]], functions,',
  'result_captures |= frozenset() if True else utf8_result_parameters(functions[signature[1]], functions,',
  'test_factory_text_result_retains_view'),
)


def main():
 suite='test_async_result_factories.AsyncResultFactoryTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-result-factories-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;source=path.read_text();assert source.count(before)==(2 if name=='ignore_factory_output_plan' else 1),(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)

if __name__=='__main__':sys.exit(main())
