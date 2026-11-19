"""Challenge completion effects in isolated compiler copies, never the checkout."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('forget_untouched_branch_target', 'async_lowering.py',
     "initial = [((holder, path), 'shared_target')]",
     'initial = []',
     'test_conditional_stores_preserve_all_target_descriptors'),
    ('lose_enum_match_effects', 'crust.py',
     'async_field_updates=tuple(update for item in items for update in item.async_field_updates),',
     'async_field_updates=(),',
     'test_enum_match_and_loop_transfers_preserve_pending_writes'),
    ('omit_join_effects', 'crust.py',
     '        self.apply_async_field_updates(allocation)',
     '        # mutated: forget completion effects',
     'test_new_target_is_protected_after_join'),
    ('lose_spawn_effects', 'crust.py',
     'async_field_updates=allocation.async_field_updates)',
     'async_field_updates=())',
     'test_new_target_is_protected_after_join'),
    ('lose_loop_effects', 'crust.py',
     'async_field_updates=tuple(update for a in values for update in a.async_field_updates),',
     'async_field_updates=(),',
     'test_enum_match_and_loop_transfers_preserve_pending_writes'),
    ('lose_match_effects', 'crust.py',
     "async_field_updates=tuple(update for state in selected_item_states\n                                                              for update in state['async_field_updates']),",
     'async_field_updates=(),',
     'test_distinct_concrete_handles_and_match_keep_effects'),
    ('skip_completion_lifetime', 'crust.py',
     '            self.check_borrow_destination(proposed, destination)\n        for holder, proposed in updates.values():',
     '            pass # mutated: no completion lifetime check\n        for holder, proposed in updates.values():',
     'test_short_lived_target_cannot_remain_in_parent_carrier'),
    ('forget_stored_field_reservation', 'async_lowering.py',
     '            active_loans[key] = list(held)',
     '            pass # mutated: forget stored field loan',
     'test_captured_mutable_input_is_reserved_by_stored_shared_reference'),
    ('old_reference_uses_current_cell', 'async_lowering.py',
     "candidates.append('frame->' + initial_field_cells[key][0])",
     "candidates.append(f'cell_load_ref(frame->{fields[root]}, {position})')",
     'test_detached_old_field_keeps_its_cell_after_change'),
)


def main():
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-field-application-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            path = target / filename
            original = path.read_text()
            assert original.count(before) == 1, (name, original.count(before))
            path.write_text(original.replace(before, after))
            script = f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT / 'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_async_field_application.AsyncFieldApplicationTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run = subprocess.run([sys.executable, '-c', script], cwd=directory,
                                 capture_output=True, text=True, timeout=60)
        detected = run.returncode == 1 and 'AssertionError' in run.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if run.returncode == 0 else 'INCONCLUSIVE', flush=True)
        print(run.stdout + run.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
