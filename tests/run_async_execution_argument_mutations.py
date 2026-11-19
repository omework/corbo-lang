"""Inject faults into temporary copies, preserving the original test oracles."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('lose_launch_error', 'async_runtime.py',
     'target->error = source->error;\n    target->pooled = 1;', 'target->error = 0;\n    target->pooled = 1;',
     'test_runtime_handoff_preserves_wait_obligation'),
    ('lose_task_pointer', 'async_runtime.py',
     '*target = (CrustExecution){0};\n    target->task = source->task;', '*target = (CrustExecution){0};\n    target->task = NULL;',
     'test_runtime_handoff_preserves_wait_obligation'),
    ('forget_result_loans', 'async_lowering.py',
     'returned.extend(record[4])', 'pass # lost result loans',
     'test_shared_and_mutable_results_keep_last_use'),
    ('forget_wait_field_changes', 'async_lowering.py',
     'apply_child_field_changes(argument_tasks[index][5], line, launched=True)',
     'pass # lost completion effects', 'test_native_helper_wait_applies_field_changes'),
    ('forget_outward_wait_fields', 'async_structure_effects.py',
     'if not task.pending_structure_calls:\n            return',
     'if True:\n            return', 'test_native_helper_wait_publishes_captured_field_changes'),
    ('allow_prepared_handle_abandonment', 'async_lowering.py',
     "fail(node.line, 'attente requise : sortie abandonnant un handle préparé comme argument')",
     'pass', 'test_loop_exits_preserve_prepared_handle_obligation'),
)


def main():
    suite = 'test_async_execution_arguments.AsyncExecutionArgumentTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-execution-args-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target/path.name)
            path = target/filename
            source = path.read_text()
            assert source.count(before) == 1, (name, source.count(before))
            path.write_text(source.replace(before, after))
            result = run(target, suite+'.'+method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
