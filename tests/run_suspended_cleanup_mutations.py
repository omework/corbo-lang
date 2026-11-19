"""Faults in temporary compiler/runtime copies, with independent oracles intact."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('omit_direct_child', 'async_lowering.py',
     'if child is not None:\n            owned_child(child)',
     'if child is not None:\n            pass',
     'test_direct_await_tree_cleans_child_before_parent_storage'),
    ('omit_prepared_arguments', 'async_lowering.py',
     'for _, cells, _ in reversed(pending_capture_groups):',
     'for _, cells, _ in ():',
     'test_prepared_moves_during_later_argument_await'),
    ('reverse_cleanup_order', 'async_lowering.py',
     'for names, *_ in reversed(scopes):\n            for name in reversed(names):',
     'for names, *_ in reversed(scopes):\n            for name in names:',
     'test_independent_scope_and_replacement_model'),
    ('forget_handle_obligation', 'async_lowering.py',
     'blocked = waiting_handle or any(value is not None for value in executions.values())',
     'blocked = False',
     'test_outstanding_handle_preflight_preserves_normal_execution'),
    ('forget_child_preflight', 'async_lowering.py',
     "f'task_owned_discardable({child})' for child in children",
     "'1' for child in children",
     'test_outstanding_handle_preflight_preserves_normal_execution'),
    ('forget_result_status', 'async_lowering.py',
     "                    success = f'{result}.status == 0'",
     "                    success = f'{result}.status != 0'",
     'test_result_allocation_cleaned_after_success_or_launch_failure'),
    ('confuse_suspension_points', 'async_lowering.py',
     'suspended_paths[point] = tuple(cleanup), tuple(children), blocked',
     'suspended_paths[1] = tuple(cleanup), tuple(children), blocked',
     'test_locals_replacements_and_conditional_suspension_points'),
    ('leak_state_slot', 'async_lowering.py',
     '    if (!task_pool_release(frame->slot)) fail("invalid suspended async slot");',
     '    /* missing state release */',
     'test_select_uses_generated_suspended_destructor'),
)


def run(directory, target):
    script = f'''import sys,unittest
sys.path[:0]=[{str(directory)!r},{str(ROOT/'tests')!r}]
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName({target!r}))
sys.exit(not result.wasSuccessful())'''
    return subprocess.run([sys.executable, '-c', script], cwd=directory,
                          capture_output=True, text=True, timeout=90)


def main():
    baseline = run(ROOT, 'test_suspended_cleanup.SuspendedCleanupTests')
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-suspended-cleanup-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            path = target / filename
            original = path.read_text()
            assert original.count(before) == 1, (name, original.count(before))
            path.write_text(original.replace(before, after))
            result = run(target, 'test_suspended_cleanup.SuspendedCleanupTests.' + method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr and
            'internal error:' not in result.stderr)
        status = 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE'
        print(name, status, flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
