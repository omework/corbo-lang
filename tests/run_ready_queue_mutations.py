"""Queue mutations are applied to emitted C constants, never to model oracles."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('stale_generation_accepted', 'entry->generation == ticket.generation && entry->task',
     'entry->task != NULL', 'test_old_tickets_cannot_wake_reused_frame'),
    ('completed_entry_not_detached', 'entry->task = NULL;\n        entry->scheduled = 0;\n        task_queue_lock(&queue->mutex);',
     '/* retain stale frame */\n        entry->scheduled = 0;\n        task_queue_lock(&queue->mutex);',
     'test_old_tickets_cannot_wake_reused_frame'),
    ('wake_enqueues_duplicates', 'if (valid && !entry->scheduled) task_queue_push(entry->queue, entry);',
     'if (valid) task_queue_push(entry->queue, entry);', 'test_fifo_model'),
    ('yield_not_requeued', 'if (ready) task_queue_push(queue, entry);',
     '(void)ready;', 'test_fifo_model'),
    ('lifo_instead_of_fifo',
     'entry->next = NULL;\n    if (queue->tail) queue->tail->next = entry;\n'
     '    else queue->head = entry;\n    queue->tail = entry;',
     'entry->next = queue->head;\n    queue->head = entry;\n'
     '    if (!queue->tail) queue->tail = entry;', 'test_fifo_model'),
    ('generation_wrap_accepted', 'else if (entry->generation == UINT64_MAX) error = EOVERFLOW;',
     'else if (0) error = EOVERFLOW;', 'test_old_tickets_cannot_wake_reused_frame'),
]


def run(mutation=None):
    script = f'''import sys, unittest
sys.path[:0] = [{str(ROOT / 'prototype')!r}, {str(ROOT/'tests')!r}]
import async_runtime
'''
    target = 'test_ready_queue.ReadyQueueTests'
    if mutation:
        _, before, after, test = mutation
        script += f'''assert async_runtime.TASK_THREAD_RUNTIME.count({before!r}) == 1
async_runtime.TASK_THREAD_RUNTIME = async_runtime.TASK_THREAD_RUNTIME.replace({before!r}, {after!r})
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
    print('BASELINE', 'PASS' if not baseline.returncode else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode: return 1
    success = True
    for mutation in MUTATIONS:
        result = run(mutation)
        detected = result.returncode == 1 and (
            'Assertion failed:' in result.stderr or 'AssertionError: -6 != 0' in result.stderr)
        status = 'DETECTED' if detected else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE'
        print(mutation[0], status, flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__': sys.exit(main())
