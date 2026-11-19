"""Fault injection for mixed ownership layouts, cleanup and result loans."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('reject_field_storage', 'async_lowering.py',
     "'allocation_field_parameter', 'task_output_parameter'):",
     "'task_output_parameter'):", 'test_return_from_direct_and_factory_tasks'),
    ('reject_mixed_layout', 'structure_shapes.py',
     "declared in ('Int', '&Int', '&mut Int') or declared.startswith('A<') and declared[2:-1] in available",
     "declared == 'Int' or declared.startswith('A<') and declared[2:-1] in available", 'test_recorded_capture'),
    ('leak_owned_child', 'async_lowering.py',
     "str(2 if field_type.startswith('A<') else 1 if field_type.startswith('&') else 0)",
     "str(1 if field_type.startswith('A<') else 1 if field_type.startswith('&') else 0)",
     'test_return_from_direct_and_factory_tasks'),
    ('destroy_borrowed_target', 'async_lowering.py',
     "str(2 if field_type.startswith('A<') else 1 if field_type.startswith('&') else 0)",
     "str(2 if field_type.startswith('A<') else 2 if field_type.startswith('&') else 0)",
     'test_return_from_direct_and_factory_tasks'),
    ('omit_prepared_owner', 'async_lowering.py',
     'for _, cells, _ in reversed(pending_capture_groups):',
     'for _, cells, _ in ():', 'test_suspended_prepared_owner_releases_external_slots'),
    ('lose_direct_result_target', 'async_lowering.py',
     "returned_loans.extend(field_loans['.' + field])", 'pass',
     'test_detached_view_releases_owned_child_and_root'),
    ('lose_factory_result_target', 'async_lowering.py',
     'for index, path in result_capture_paths)):\n                    returned.extend(held)',
     'for index, path in result_capture_paths)):\n                    pass',
     'test_detached_view_releases_owned_child_and_root'),
    ('lose_async_origin_placement', 'async_local_placement.py',
     "if candidates and all(candidate.kind == 'parameter' for candidate in candidates):",
     "if False and candidates and all(candidate.kind == 'parameter' for candidate in candidates):",
     'test_replacement_and_reuse_across_iterations'),
    ('lose_factory_origin_placement', 'async_local_placement.py',
     "if sources and all(source.kind == 'allocation_parameter' for source in sources):",
     "if False and sources and all(source.kind == 'allocation_parameter' for source in sources):",
     'test_replacement_and_reuse_across_iterations'),
)


def main():
    suite = 'test_async_mixed_structures.AsyncMixedStructureTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-mixed-structure-mutant-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target/path.name)
            path = target/filename
            source = path.read_text()
            assert source.count(before) == 1, (name, source.count(before))
            path.write_text(source.replace(before, after))
            result = run(target, suite + '.' + method)
        detected = result.returncode == 1 and ('AssertionError' in result.stderr or 'crust.Error:' in result.stderr)
        print(name, 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
