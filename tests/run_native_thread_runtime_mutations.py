"""Faults in the RT8 native-launch boundary; run only in temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('native_routed_through_scheduler', [
        ('return task_start_joinable(execution, task, task_pthread_launch,\n'
         '                              task_pthread_wait, pthread_detach, task_native_run);',
         'return task_thread_start_mode(execution, task, &task_default_scheduler, 0);'),
        ('task_start_detached(execution, task, task_pthread_launch, task_native_run);',
         'task_async_start_mode(execution, task, &task_default_scheduler, 0);')],
     'test_native_launch_bypasses_both_scheduler_callbacks'),
    ('native_suspension_accepted', [
        ('if (task_resume_claimed(task) != TASK_COMPLETE) abort();',
         'CrustTaskState state = task_resume_claimed(task);\n'
         '    while (state == TASK_SUSPENDED) state = task_poll(task);')],
     'test_native_runner_rejects_a_suspended_block'),
    ('failed_launch_cleanup_erased', [
        ('if (!task_drop_inactive(task)) abort();', '(void)task;')],
     'test_native_waits_publish_result_cleanup_and_slot_reuse'),
    ('completion_published_before_body', [
        ('if (task_resume_claimed(task) != TASK_COMPLETE) abort();\n'
         '    /* No access to the task slot is allowed after this publication. */\n'
         '    task_external_complete(task);',
         'atomic_store_explicit(&task->worker_done, 1, memory_order_release);\n'
         '    if (task_resume_claimed(task) != TASK_COMPLETE) abort();')],
     'test_native_waits_publish_result_cleanup_and_slot_reuse'),
    ('release_before_result_extraction', [
        ('task->ops->take_result(task, result);\n    task->ops->release(task);',
         'task->ops->release(task);\n    task->ops->take_result(task, result);')],
     'test_native_waits_publish_result_cleanup_and_slot_reuse'),
]


def main():
    success = True
    cases = [('async_runtime.py', 'test_native_thread_runtime', 'NativeThreadRuntimeTests', *case)
             for case in MUTATIONS]
    cases.append(('crust.py', 'test_native_thread_parser', 'NativeThreadParserTests',
                  'native_block_inherits_async', [
                      ('self.async_body = False\n            try:\n                body = self.block(if_value=True, native_captures=captures)',
                       'self.async_body = previous\n            try:\n                body = self.block(if_value=True, native_captures=captures)')],
                  'test_suspensions_are_refused_inside_native_block_in_async_function'))
    for filename, module, classname, name, substitutions, test in cases:
        if sys.argv[1:] and name not in sys.argv[1:]:
            continue
        source = (ROOT / 'prototype' / filename).read_text()
        for before, after in substitutions:
            expected = 4 if name == 'failed_launch_cleanup_erased' else 1
            if source.count(before) != expected:
                raise SystemExit(f'{name}: changed anchor ({source.count(before)})')
            source = source.replace(before, after)
        with tempfile.TemporaryDirectory(prefix='crust-native-thread-mut-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            (target / filename).write_text(source)
            script = f'''import sys, unittest
sys.path[:0] = [{directory!r}, {str(ROOT / 'tests')!r}]
suite = unittest.defaultTestLoader.loadTestsFromName(
    '{module}.{classname}.{test}')
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run = subprocess.run([sys.executable, '-c', script], cwd=directory,
                                 capture_output=True, text=True, timeout=120)
            detected = run.returncode == 1 and 'FAIL:' in run.stderr
            print(name, 'DETECTED' if detected else 'SURVIVED' if run.returncode == 0
                  else 'INCONCLUSIVE', flush=True)
            print(run.stderr[-3000:], flush=True)
            success &= detected
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
