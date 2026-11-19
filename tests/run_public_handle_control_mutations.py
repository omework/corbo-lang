"""Faults in handle control joins, exercised by unchanged integration oracles."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('contract_join_removed', 'results.py',
     'return [self.public_handle_value(value, public, line) for value in values]', 'return values',
     'test_control_results_union_captures_and_keep_permissions', 'même type'),
    ('backend_join_removed', 'crust.py',
     'def unify_execution_allocations(self, allocations):\n',
     'def unify_execution_allocations(self, allocations):\n        return None\n',
     'test_control_results_union_captures_and_keep_permissions', 'même type'),
    ('second_branch_captures_lost', 'results.py',
     'return [self.public_handle_value(value, public, line) for value in values]',
     'return [self.public_handle_value(values[0], public, line) for value in values]',
     'test_control_result_contracts_need_no_task_bodies_at_call_site', 'Error not raised'),
    ('if_owned_capture_sources_lost', 'results.py',
     'task_sources=frozenset(source for value in returning for source in value.task_sources)',
     'task_sources=frozenset()',
     'test_owned_capture_sources_survive_control_and_opaque_relay', 'Error not raised'),
)


def main():
    success = True
    for name, filename, before, after, method, diagnostic in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-handle-joins-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target/path.name)
            path = target/filename
            original = path.read_text()
            assert original.count(before) == 1, (name, original.count(before))
            path.write_text(original.replace(before, after))
            script = f'''import sys, unittest
sys.path[:0] = [{directory!r}, {str(ROOT/'tests')!r}]
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
    'test_public_handle_control.PublicHandleControlTests.{method}'))
sys.exit(not result.wasSuccessful())
'''
            result = subprocess.run([sys.executable, '-c', script], cwd=directory,
                                    capture_output=True, text=True, timeout=120)
        detected = result.returncode == 1 and diagnostic in result.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE', flush=True)
        print(result.stdout+result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
