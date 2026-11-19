"""RT7 and launch-failure cleanup faults, applied only to temporary copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('sync_abandonment_restored', 'crust.py',
     "            self.fail('join requis : un handle doit être attendu explicitement, pas détruit ou abandonné')",
     "            drop, value = 'task_abandon', f'&{value}'",
     'test_each_branch_disposes_its_obligation_in_independent_path_model'),
    ('async_abandonment_restored', 'async_lowering.py',
     '''        fail(line, f"attente requise : le handle '{name}' doit être attendu avec .await, pas détruit ou abandonné")''',
     '''        handle, _, loans, _, _ = consume_execution(name, line)
        steps.append(f'task_abandon_async({handle});')
        del active_loans[id(loans)]''',
     'test_async_scalar_handles_require_await_even_without_borrows'),
    ('launch_failure_cleanup_omitted', 'async_runtime.py',
     '        if (!task_drop_inactive(task)) abort();',
     '        /* faulty launch failure: captures and slot retained */',
     'test_failure_is_awaited_after_capture_cleanup_and_before_slot_reuse'),
]


def main():
    successful = True
    for name, filename, before, after, test in MUTATIONS:
        source = (ROOT / 'prototype' / filename).read_text()
        expected = 2 if name == 'launch_failure_cleanup_omitted' else 1
        if source.count(before) != expected:
            raise SystemExit(f'{name}: changed mutation anchor')
        with tempfile.TemporaryDirectory(prefix='crust-handle-obligation-mut-') as folder:
            target = Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            (target / filename).write_text(source.replace(before, after))
            script = f'''import sys, unittest
sys.path[:0] = [{folder!r}, {str(ROOT / 'tests')!r}]
suite = unittest.defaultTestLoader.loadTestsFromName('test_handle_obligations.HandleObligationTests.{test}')
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run = subprocess.run([sys.executable, '-c', script], cwd=folder,
                                 capture_output=True, text=True, timeout=120)
            detected = run.returncode == 1 and 'FAIL:' in run.stderr
            status = 'DETECTED' if detected else 'SURVIVED' if not run.returncode else 'INCONCLUSIVE'
            print(name, status, flush=True)
            print(run.stderr[-1800:], flush=True)
            successful &= detected
    return 0 if successful else 1


if __name__ == '__main__':
    sys.exit(main())
