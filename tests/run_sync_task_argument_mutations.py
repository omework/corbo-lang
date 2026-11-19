"""Fault injection for task arguments, cleanup and forwarding contracts."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('forget_consumption', 'async_lowering.py', 'tasks[name] = None', 'pass',
     'test_relay_borrowed_result_and_last_use'),
    ('lose_prepared_loans', 'async_lowering.py',
     'value, held = record[0], list(record[2])', 'value, held = record[0], []',
     'test_left_to_right_prepared_task_holds_capture'),
    ('lose_forwarded_captures', 'async_lowering.py', 'retained.extend(record[2])', 'pass',
     'test_recorded_nested_owned_capture'),
    ('lose_returned_loan', 'async_lowering.py', 'returned.extend(record[4])', 'pass',
     'test_relay_borrowed_result_and_last_use'),
    ('omit_suspended_argument_task', 'async_lowering.py', 'owned_child(cell[1])', 'pass',
     'test_select_cleanup_in_later_suspended_argument'),
    ('omit_early_argument_task', 'async_lowering.py',
     "steps.extend((f'task_discard({cell[1]});', f'{cell[1]} = NULL;'))", 'pass',
     'test_early_return_destroys_prepared_task_before_pool'),
    ('assume_all_returns_forward', 'results.py', 'self.task_forward_only &= value.task_forward_only', 'pass',
     'test_forwarding_contract_marks_fresh_alternative'),
)


def main():
    suite = 'test_sync_task_arguments.SyncTaskArgumentTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-sync-task-mutant-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target/path.name)
            path = target/filename
            source = path.read_text()
            assert source.count(before) == 1, (name, source.count(before))
            path.write_text(source.replace(before, after))
            result = run(target, suite + '.' + method)
        assertion = result.returncode == 1 and 'AssertionError' in result.stderr
        crash = result.returncode == 1 and 'KeyError:' in result.stderr
        detected = assertion or crash
        print(name, 'DETECTED' if assertion else 'DETECTED_COMPILER_CRASH' if crash else
              'SURVIVED' if not result.returncode else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
