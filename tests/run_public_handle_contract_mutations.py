"""Public handle contract faults, applied to isolated compiler copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('exclusive_capture_downgraded', [('handle_types.py',
        "key = ('mut.3' if shared_capability else 'mut.2') if key.startswith('mut.') else 'ref.1'", "key = 'ref.1'")],
     'test_capture_permission_model'),
    ('shared_capture_made_exclusive', [('handle_types.py',
        "key = ('mut.3' if shared_capability else 'mut.2') if key.startswith('mut.') else 'ref.1'", "key = 'mut.2'")],
     'test_shared_capture_stays_shared_through_public_relay'),
    ('shared_capability_barrier_lost', [('handle_types.py',
        "shared_capability = parameters[int(key.partition('.')[2])][1] == 'ref'",
        'shared_capability = False')],
     'test_shared_vector_reborrow_survives_public_factory'),
    ('owned_capture_source_erased', [('results.py',
        'sources.update(actual.task_sources)', 'pass # lost opaque storage')],
     'test_opaque_relay_cannot_drop_owned_capture_source'),
    ('empty_body_catalog_disables_capture_loans', [('crust.py',
        "for carrier in self.allocations if carrier.alive and carrier.dependencies\n"
        "                      and carrier.typ.startswith(('Task<', 'Execution<')))",
        "for carrier in self.allocations if self.async_definitions and carrier.alive and carrier.dependencies\n"
        "                      and carrier.typ.startswith(('Task<', 'Execution<')))")],
     'test_calls_need_only_public_contracts'),
    ('public_payload_check_erased', [
        ('crust.py', "if actual != expected:\n            self.fail(f'handle", "if False:\n            self.fail(f'handle"),
        ('results.py', 'if actual != typ:', 'if False:'),
        ('constraints.py', 'if actual_type != typ:', 'if False:')],
     'test_payload_checked_even_when_callee_discards_value'),
    ('array_payload_check_erased', [
        ('crust.py', "if actual != expected:\n            self.fail(f'handle", "if False:\n            self.fail(f'handle"),
        ('results.py', 'if actual != typ:', 'if False:'),
        ('constraints.py', 'if actual_type != typ:', 'if False:')],
     'test_array_handle_contract_checks_extents_even_if_result_is_discarded'),
]


def main():
    success = True
    for name, changes, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-public-handle-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            for filename, before, after in changes:
                path = target / filename
                source = path.read_text()
                assert source.count(before) == 1, (name, filename, source.count(before))
                path.write_text(source.replace(before, after))
            script = f'''import sys, unittest
sys.path[:0] = [{directory!r}, {str(ROOT/'tests')!r}]
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
    'test_public_handle_contracts.PublicHandleContractTests.{method}'))
sys.exit(not result.wasSuccessful())
'''
            result = subprocess.run([sys.executable, '-c', script], cwd=directory,
                                    capture_output=True, text=True, timeout=120)
        detected = result.returncode == 1 and (
            'Error not raised' in result.stderr or
            name in ('shared_capture_made_exclusive', 'shared_capability_barrier_lost')
            and 'incompatible avec un emprunt actif' in result.stderr)
        print(name, 'DETECTED' if detected else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
