"""Check that public annotations cannot erase type or lifetime obligations."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('sync_result_check_omitted', 'crust.py', [
        ('if annotation != actual_type:\n                            self.fail(f\'annotation de handle',
         'if False:\n                            self.fail(f\'annotation de handle')],
     'test_result_type_matrix_sync_and_async'),
    ('async_result_checks_omitted', 'async_lowering.py', [
        ('if statement.annotation != actual_type:', 'if False:'),
        ("if statement.annotation is not None and kind != 'array':",
         "if statement.annotation is not None and kind not in ('array', 'execution'):")],
     'test_control_flow_and_launch_variants'),
    ('annotation_erases_capture_dependencies', 'crust.py', [
        ('nominal = allocation.typ[len(\'Execution<\'):-1]',
         'allocation.dependencies = ()\n                        nominal = allocation.typ[len(\'Execution<\'):-1]')],
     'test_scalar_result_does_not_erase_live_capture'),
]


def main():
    success = True
    for name, filename, changes, method in MUTATIONS:
        source = (ROOT / 'prototype' / filename).read_text()
        for before, after in changes:
            assert source.count(before) == 1, (name, source.count(before))
            source = source.replace(before, after)
        with tempfile.TemporaryDirectory(prefix='crust-handle-types-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            (target / filename).write_text(source)
            script = f'''import sys, unittest
sys.path[:0] = [{directory!r}, {str(ROOT/'tests')!r}]
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
    'test_public_handle_types.PublicHandleTypeTests.{method}'))
sys.exit(not result.wasSuccessful())
'''
            result = subprocess.run([sys.executable, '-c', script], cwd=directory,
                                    capture_output=True, text=True, timeout=120)
        detected = result.returncode == 1 and 'Error not raised' in result.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
