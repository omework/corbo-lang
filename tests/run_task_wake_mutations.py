"""Inject RT2 protocol faults into C strings; retain the original test oracle."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('pending_repolled_without_wake', 'TASK_RUNTIME',
     'if (step == TASK_STEP_YIELD) task->ready = 1;',
     'if (step != TASK_STEP_RETURN) task->ready = 1;', 'test_readiness_model'),
    ('wake_during_poll_erased', 'TASK_RUNTIME',
     'if (step == TASK_STEP_YIELD) task->ready = 1;',
     'task->ready = 0; if (step == TASK_STEP_YIELD) task->ready = 1;',
     'test_wake_during_poll_and_migration'),
    ('notification_ignored', 'TASK_RUNTIME',
     'if (live) task->ready = 1;', '(void)live;', 'test_readiness_model'),
    ('readiness_not_checked', 'TASK_RUNTIME',
     '(state == TASK_INACTIVE || state == TASK_SUSPENDED) && task->ready',
     '(state == TASK_INACTIVE || state == TASK_SUSPENDED)', 'test_readiness_model'),
    ('queued_permission_not_spent', 'TASK_THREAD_RUNTIME',
     'task->ready = 0;', '/* permission incorrectly retained */',
     'test_launched_pending_task_needs_notification'),
    ('concurrent_poll_allowed', 'TASK_RUNTIME',
     '(state == TASK_INACTIVE || state == TASK_SUSPENDED) && task->ready',
     '(state == TASK_INACTIVE || state == TASK_SUSPENDED || state == TASK_RUNNING) && task->ready',
     'test_wake_during_poll_and_migration'),
]


def run(mutation=None):
    script = f'''import sys, unittest
sys.path[:0] = [{str(ROOT / 'prototype')!r}, {str(ROOT / 'tests')!r}]
import test_task_wakes as tests
'''
    target = 'test_task_wakes.TaskWakeTests'
    if mutation:
        _, symbol, before, after, test = mutation
        script += f'''source = tests.{symbol}
assert source.count({before!r}) == 1
tests.{symbol} = source.replace({before!r}, {after!r})
'''
        target += '.' + test
    script += f'''result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromName({target!r}))
sys.exit(not result.wasSuccessful())
'''
    return subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                          capture_output=True, text=True, timeout=90)


def main():
    baseline = run()
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode: return 1
    success = True
    for mutation in MUTATIONS:
        result = run(mutation)
        # Compilation failures and timeouts do not count as detected faults.
        detected = result.returncode == 1 and 'Assertion failed:' in result.stderr
        status = 'DETECTED' if detected else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE'
        print(mutation[0], status, flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__': sys.exit(main())
