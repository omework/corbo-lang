"""Isolated faults in deferred child field updates and capture snapshots."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('ignore_void_await_statement',
     "            elif op in ('call', 'await_statement'):",
     "            elif op == 'call':",
     'test_recorded_void_child_counterexample', 'results.py'),
    ('erase_scalar_execution_envelope',
     "return flow, Value({'Int': 'join_int', 'Bool': 'join_bool',\n                    'bool': 'join_bool', 'u8': 'join_byte', 'char': 'join_char'}\n                    .get(typ, 'join_void'), typ)",
     'return flow, Value(mode, typ)',
     'test_void_completion_and_native_child', 'async_structure_effects.py'),
    ('forget_direct_completion',
     '        apply_child_field_changes(field_changes, line, launched=False)',
     '        pass # mutated: no direct completion effects',
     'test_completed_child_keeps_target_reserved_in_parent'),
    ('forget_handle_completion',
     '        apply_child_field_changes(field_changes, line, launched=True)',
     '        pass # mutated: no handle completion effects',
     'test_spawned_child_success_and_submission_failure'),
    ('publish_at_creation',
     "            return task, declaration.args[2] == ('scalar', 'Int'), loans, callee, returned_loans, (changes,)",
     "            apply_child_field_changes((changes,), line, launched=False)\n            return task, declaration.args[2] == ('scalar', 'Int'), loans, callee, returned_loans, (changes,)",
     'test_inactive_child_does_not_publish_effects'),
    ('forget_launch_failure_state',
     '            held = list(initial) if launched else []',
     '            held = []',
     'test_spawned_child_success_and_submission_failure'),
    ('forget_branch_effects',
     '                            selected_field_changes.extend(field_changes)',
     '                            pass # mutated: lost selected effects',
     'test_task_and_handle_choices_and_loop_exports'),
    ('forget_break_effects',
     "                loop['field_changes'].extend(record[5])",
     '                pass # mutated: lost break effects',
     'test_task_and_handle_choices_and_loop_exports'),
    ('old_borrow_reads_updated_field',
     "candidates.append('frame->' + initial_field_cells[key][0])",
     "candidates.append(f'cell_load_ref(frame->{fields[root]}, {position})')",
     'test_conditional_child_store_and_snapshot_before_wait'),
)


def main():
    success=True
    for name,before,after,method,*files in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-child-fields-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path,target/path.name)
            path=target/(files[0] if files else 'async_lowering.py')
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_async_child_field_effects.AsyncChildFieldEffectsTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run=subprocess.run([sys.executable,'-c',script],cwd=directory,
                               capture_output=True,text=True,timeout=60)
        detected=run.returncode==1 and ('AssertionError' in run.stderr or 'crust.Error:' in run.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(run.stdout+run.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
