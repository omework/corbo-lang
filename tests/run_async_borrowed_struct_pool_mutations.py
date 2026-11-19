"""Keep oracles unchanged while corrupting stored-loan flow and cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('destroy_borrowed_target', 'else 1 if field_type.startswith("&") else 0', 'else 2 if field_type.startswith("&") else 0', 'test_shared_target_drop_and_last_use'),
 ('forget_constructed_targets', "active_loans[('stored_field', cell, path)] = held", 'pass # missing stored target', 'test_shared_target_drop_and_last_use'),
 ('forget_transferred_fields', '    def move_stored_fields(source, destination):\n        for key in list(active_loans):', '    def move_stored_fields(source, destination):\n        for key in ():', 'test_receiver_transfer_and_short_target'),
 ('keep_replaced_targets', '        clear_stored_fields(name)\n        storage_bindings.pop(name, None)', '        pass # old field dependencies remain\n        storage_bindings.pop(name, None)', 'test_parent_replacement_and_suspended_destruction'),
 ('lose_mutable_field_capability', '            retained = list(projected)', '            retained = []', 'test_mutable_reborrow_exclusivity_and_last_use'),
 ('lose_detached_target', "retained.extend(active_loans.get(('stored_field',root,full_path),\n                    [(target,", "retained.extend({}.get(('stored_field',root,full_path),\n                    [(target,", 'test_shared_projection_detaches_but_target_remains'),
 ('retain_dead_carrier_loan', "                if references.get(holder) == 'owned' and not borrowed and not utf8_current_live(", "                if False and references.get(holder) == 'owned' and not borrowed and not utf8_current_live(", 'test_shared_target_drop_and_last_use'),
 ('forget_prepared_field_loan', "                    loans.extend(held)\n                    stored_fields[tuple(field.split('.'))]", "                    pass # field not reserved during later arguments\n                    stored_fields[tuple(field.split('.'))]", 'test_constructor_arguments_keep_loans_across_suspend'),
 ('ignore_carrier_loans', "and not borrowed and not utf8_current_live(", "and not utf8_current_live(", 'test_live_task_and_alias_keep_carrier_targets'),
 ('ignore_local_completion_origins', 'if completion and completion.complete and (completion.structure_fields or completed_targets and all(', 'if completion and completion.complete and (completion.structure_fields or False and all(', 'test_returned_shared_reference_after_carrier_drop'),
)
def main():
 suite='test_async_borrowed_struct_pools.AsyncBorrowedStructPoolTests'
 baseline=run(ROOT,suite);print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-borrowed-pool-mutant-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/'async_lowering.py';source=path.read_text();assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)
if __name__=='__main__':sys.exit(main())
