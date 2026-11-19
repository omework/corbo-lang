"""Challenge demand inference and exact post-completion loans."""
from pathlib import Path
import shutil,sys,tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('reject_captured_field_replacement','async_lowering.py',
  "captured_reference = parameter_modes.get(root) == 'owned' and source_path and durable_type", 'captured_reference = False',
  'test_return_follows_field_replacement_at_completion'),
 ('skip_completion_publication','results.py',
  '            node.field_effect_summary = summary','            pass',
  'test_recorded_factory_and_task_relay'),
 ('use_empty_helper_body','async_structure_effects.py',
  '        summary = self.resolver(name)','        summary = super().infer(name)',
  'test_inference_follows_helpers_independent_of_declaration_order'),
 ('drop_child_result_loan','async_lowering.py',
  "returned_loans.extend(field_loans['.' + field])",'pass',
  'test_direct_child_target_must_survive'),
 ('keep_all_factory_fields','async_lowering.py',
  'if position in result_captures and (not selected_field or any(',
  'if position in result_captures and (True or any(',
  'test_factory_child_exact_target_access_model'),
 ('drop_factory_result_loans','async_lowering.py',
  'for index, path in result_capture_paths)):\n                    returned.extend(held)',
  'for index, path in result_capture_paths)):\n                    pass',
  'test_factory_child_exact_target_access_model'),
 ('merge_waiter_result_fields','results.py',
  'targets = capture_result_origins(result_fields, {index for index, _ in paths}',
  'targets = capture_result_origins(fields, {index for index, _ in paths}',
  'test_waiter_contract_projects_field_after_join'),
 ('wrong_child_field','async_lowering.py',
  "returned_loans.extend(field_loans['.' + field])", "returned_loans.extend(field_loans.get('.right', ()))",
  'test_factory_child_exact_target_access_model'),
)
def main():
 suite='test_detached_task_factories.DetachedTaskFactoryTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 success=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-detached-factory-mutant-') as directory:
   target=Path(directory)
   for p in (ROOT / 'prototype').glob('*.py'):shutil.copy2(p,target/p.name)
   path=target/filename;source=path.read_text()
   assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and ('AssertionError' in result.stderr or 'crust.Error:' in result.stderr)
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);success &= detected
 return int(not success)
if __name__=='__main__':sys.exit(main())
