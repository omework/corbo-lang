"""Mutate result storage contracts in temporary compiler copies."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('forget_task_projection', 'storage_requirements.py',
     'value = context.completed_task(value)', 'return', 'test_storage_matrix_and_relays'),
    ('forget_task_obligation', 'storage_requirements.py',
     'demand(source.index)\n                elif actual != required:',
     'pass\n                elif actual != required:', 'test_recorded_local_result'),
    ('first_candidate_only', 'storage_requirements.py',
     'for asset in value.assets:', 'for asset in list(value.assets)[:1]:',
     'test_conditional_task_input_requires_each_result'),
    ('symbolic_root_always_pool', 'crust.py',
     "kind = 'local_stack' if position in result_indexes and result_storage_kind == 'local' else 'symbolic'",
     "kind = 'symbolic'", 'test_recorded_local_result'),
    ('descendants_are_root_storage', 'async_result_storage.py',
     'effect = getattr(node, \'field_effect_summary\', None)\n    completed = effect.completion_result if effect and effect.complete else None',
     'return fallback\n    effect = None\n    completed = None', 'test_fresh_local_root_keeps_pool_descendant'),
    ('omit_copied_root', 'crust.py',
     'if position in result_indexes:\n                # A borrowed capture',
     'if False:\n                # A borrowed capture', 'test_copy_from_borrowed_capture'),
    ('capture_sources_instead_of_result', 'crust.py',
     "target.task_result_sources if binding.kind in ('task', 'execution') else target.sources",
     "target.item_sources if binding.kind in ('task', 'execution') else target.sources",
     'test_result_storage_is_distinct_from_other_captures'),
)


def main():
    suite = 'test_task_result_storage.TaskResultStorageTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout+baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-task-storage-') as directory:
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
        print(result.stdout+result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
