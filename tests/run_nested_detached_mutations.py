"""Fault injection for detached references reached through owned descendants."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('project_detached_target_twice', 'async_lowering.py',
     "if target.kind == 'detached_field_parameter' and captured is not None:",
     'if False:', 'test_public_handle_selects_only_returned_target'),
    ('lose_returned_target', 'async_lowering.py',
     "returned_loans.extend(field_loans['.' + field])", 'pass',
     'test_target_survives_direct_and_factory_await'),
    ('lose_owned_projection_type', 'results.py',
     "if declared.startswith('A<') and declared[2:-1] in self.analyzer.enums:",
     'if False:', 'test_nested_helper_chain'),
    ('lose_contract_path_normalization', 'async_lowering.py',
     "path = stored_field_path('.' + '.'.join(path))", 'pass',
     'test_nested_helper_chain'),
    ('lose_owned_carrier_traversal', 'crust.py',
     'children = dict(carrier.owned_fields).get(head)', 'children = None',
     'test_public_handle_and_waiter'),
    ('lose_borrowed_bridge_children', 'crust.py',
     "root.bindings[parameter] = Binding(parameter, mode, parameter, allocation)\n                owned_bridge_fields(allocation, parameter)",
     "root.bindings[parameter] = Binding(parameter, mode, parameter, allocation)",
     'test_nested_helper_chain'),
    ('lose_detached_capture_origin', 'results.py',
     "projected = frozenset(replace(origin, kind='detached_field_parameter')",
     "projected = frozenset(replace(origin, kind='local')",
     'test_public_handle_selects_only_returned_target'),
)


def main():
    suite = 'test_nested_detached_references.NestedDetachedReferenceTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-nested-detached-mutant-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target/path.name)
            path = target/filename
            source = path.read_text()
            assert source.count(before) == 1, (name, source.count(before))
            path.write_text(source.replace(before, after))
            result = run(target, suite + '.' + method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
