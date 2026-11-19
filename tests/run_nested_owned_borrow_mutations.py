"""Fault injection against nested capture paths and restored dependencies."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('cut_nested_paths', 'array_syntax.py',
     "yield from owned_reference_paths(enums, declared[2:-1], path + '/', visited | {typ})",
     'pass', 'test_factories_and_task_relay'),
    ('lose_concrete_prefix', 'crust.py',
     "yield from self.owned_dependency_fields(child, prefix + field + '/', visited | {id(allocation)})",
     'yield from self.owned_dependency_fields(child, prefix, visited | {id(allocation)})',
     'test_factories_and_task_relay'),
    ('lose_constructed_target', 'async_lowering.py',
     "stored_fields[(*field.split('.'), *stored_field_path(path))] = held",
     'pass', 'test_factories_and_task_relay'),
    ('lose_restored_child_target', 'crust.py',
     'restore_borrowed_fields(child, descendants)', 'pass',
     'test_sync_caller_result_keeps_nested_target'),
    ('lose_symbolic_descendant_target', 'results.py',
     "for path, _, _ in owned_reference_paths(self.analyzer.enums, typ) if '/' in path)",
     "for path, _, _ in owned_reference_paths(self.analyzer.enums, typ) if False)",
     'test_whole_result_keeps_nested_target'),
    ('confuse_owned_borrowed_layout', 'async_lowering.py',
     "str(2 if field_type.startswith('A<') else 1 if field_type.startswith('&') else 0)",
     "str(1 if field_type.startswith('A<') else 1 if field_type.startswith('&') else 0)",
     'test_two_same_named_fields_keep_distinct_targets'),
)


def main():
    suite = 'test_nested_owned_borrows.NestedOwnedBorrowTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-nested-borrow-mutant-') as directory:
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
