"""Behavioral faults in await notification delivery; unmodified test oracles."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('root_ticket_not_forwarded', 'TASK_RUNTIME_BODY',
     'child->wake_target = parent->wake_target;', '(void)parent;', 1),
    ('waiter_not_registered', 'TASK_THREAD_RUNTIME',
     'entry->waiter = target;', '(void)target;', 1),
    ('notification_omitted', 'TASK_THREAD_RUNTIME',
     'task_queue_wake(waiter);', '(void)waiter;', 2),
    ('pending_becomes_busy_poll', 'TASK_THREAD_RUNTIME',
     'step = TASK_STEP_PENDING;', 'step = TASK_STEP_YIELD;', 1),
    ('detached_entry_sleeps_forever', 'TASK_THREAD_RUNTIME',
     'CrustTaskStep step = TASK_STEP_YIELD;', 'CrustTaskStep step = TASK_STEP_PENDING;', 1),
    ('completion_visible_before_notification', 'TASK_THREAD_RUNTIME',
     'task_queue_wake(waiter);',
     'atomic_store_explicit(&task->worker_done, 1, memory_order_release); task_queue_wake(waiter);', 2),
    ('submission_does_not_bind_entry', 'TASK_THREAD_RUNTIME',
     'task->queue_entry = entry;', '/* entry not bound */', 1),
]


def run(mutation=None):
    script = f'''import sys, unittest
sys.path[:0] = [{str(ROOT / 'prototype')!r}, {str(ROOT/'tests')!r}]
import async_runtime
'''
    if mutation:
        _, constant, before, after, count = mutation
        script += f'''assert async_runtime.{constant}.count({before!r}) == {count}
async_runtime.{constant} = async_runtime.{constant}.replace({before!r}, {after!r})
async_runtime.TASK_RUNTIME = async_runtime.UTF8_VALUE_TYPES_C + async_runtime.TASK_RUNTIME_BODY
'''
    script += '''suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(
    'test_await_notifications.AwaitNotificationTests.' + name) for name in (
        'test_completion_before_during_and_after_subscription',
        'test_nested_generated_await_sleeps_and_reuses_slots'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
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
        print(mutation[0], 'DETECTED' if detected else
              'SURVIVED' if not result.returncode else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
