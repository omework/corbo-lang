"""Mutate emitted runtime strings in isolated processes; keep model unchanged."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('poll_without_wake', 'TASK_SELECT_RUNTIME',
     'if (task_poll(task) == TASK_COMPLETE)',
     'task_wake(task);\n        if (task_poll(task) == TASK_COMPLETE)',
     'test_independent_eligibility_model'),
    ('reverse_eligible_order', 'TASK_SELECT_RUNTIME',
     'selection->started = 1;\n    for (size_t i = 0; i < selection->count; ++i) {',
     'selection->started = 1;\n    for (size_t end = selection->count; end > 0; --end) {\n'
     '        size_t i = end - 1;',
     'test_independent_eligibility_model'),
    ('release_losers_at_take', 'TASK_SELECT_RUNTIME',
     'selection->taken = 1;',
     'for (size_t i=0; i<selection->count; ++i)\n'
     '        if (selection->branches[i].task)\n'
     '            selection->branches[i].task->ops->release(selection->branches[i].task);\n'
     '    selection->taken = 1;',
     'test_independent_eligibility_model'),
    ('lose_parent_notification', 'TASK_THREAD_RUNTIME',
     'if (forward.entry) task_queue_wake(forward);', '(void)forward;',
     'test_nested_routes_wake_only_the_selected_chain'),
    ('keep_loser_wake_route', 'TASK_SELECT_RUNTIME',
     'task_external_forget(selection->branches[i].task);', '(void)selection;',
     'test_independent_eligibility_model'),
    ('ignore_ticket_generation', 'TASK_THREAD_RUNTIME',
     'entry->generation == ticket.generation && entry->task', 'entry->task != NULL',
     'test_concurrent_old_tickets_after_free_and_entry_reuse'),
    ('omit_suspended_destructor', 'TASK_SELECT_RUNTIME',
     'if (state == TASK_SUSPENDED) branch->discard_suspended(task);',
     'if (state == TASK_SUSPENDED) (void)task;',
     'test_cleanup_inactive_pending_completed_and_taken'),
]


def run(mutation=None):
    script = f'''import sys, unittest
sys.path[:0]=[{str(ROOT / 'prototype')!r},{str(ROOT/'tests')!r}]
import async_runtime
'''
    target = 'test_select_runtime.SelectRuntimeTests'
    if mutation:
        _, constant, before, after, test = mutation
        script += f'''code=async_runtime.{constant}
assert code.count({before!r})==1
async_runtime.{constant}=code.replace({before!r},{after!r})
'''
        target += '.' + test
    script += f'''result=unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromName({target!r}))
sys.exit(not result.wasSuccessful())
'''
    return subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                          capture_output=True, text=True, timeout=90)


def main():
    baseline = run()
    print('BASELINE', 'PASS' if not baseline.returncode else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for mutation in MUTATIONS:
        result = run(mutation)
        detected = result.returncode == 1 and 'Assertion failed:' in result.stderr
        status = 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE'
        print(mutation[0], status, flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
