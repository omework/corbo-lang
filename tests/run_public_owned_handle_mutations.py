"""Fault injection at public owned-result provenance and type boundaries."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('opaque_result_provenance_lost', [('async_lowering.py',
        'return frozenset({position})', 'return frozenset()')],
     'test_opaque_contract_preserves_result_source_through_join_helper',
     ('Error not raised', 'retour sans provenance symbolique vérifiable')),
    ('all_capture_pools_retained_after_join', [('results.py',
        'sources.update(actual.task_result_sources)', 'sources.update(actual.task_sources)')],
     'test_result_outlives_unrelated_capture_pool_for_each_owned_type', ('ne survit pas', 'source de stockage')),
    ('received_handle_result_storage_lost', [('crust.py',
        'item_origins=origins, task_result_sources=result_sources,',
        'item_origins=origins, task_result_sources=(),')],
     'test_opaque_contract_preserves_result_source_through_join_helper', ('Error not raised',)),
    ('public_owned_payload_check_lost', [
        ('crust.py', "if actual != expected:\n            self.fail(f'handle", "if False:\n            self.fail(f'handle"),
        ('results.py', 'if actual != typ:', 'if False:'),
        ('constraints.py', 'if actual_type != typ:', 'if False:')],
     'test_wrong_owned_payload_rejected_even_if_only_dropped', ('Error not raised',)),
    ('effect_task_type_erased', [('effects.py',
        "return f'{mode.capitalize()}<{typ}>'", 'return typ')],
     'test_result_outlives_unrelated_capture_pool_for_each_owned_type',
     ("méthode inconnue ou receveur indéterminé 'byte_len'",)),
)


def main():
    success = True
    for name, edits, method, diagnostics in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-owned-handles-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target/path.name)
            for filename, before, after in edits:
                path = target/filename
                original = path.read_text()
                assert original.count(before) == 1, (name, original.count(before))
                path.write_text(original.replace(before, after))
            script = f'''import sys, unittest
sys.path[:0] = [{directory!r}, {str(ROOT/'tests')!r}]
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
    'test_public_owned_handles.PublicOwnedHandleTests.{method}'))
sys.exit(not result.wasSuccessful())
'''
            result = subprocess.run([sys.executable, '-c', script], cwd=directory,
                                    capture_output=True, text=True, timeout=120)
        detected = result.returncode == 1 and any(message in result.stderr for message in diagnostics)
        print(name, 'DETECTED' if detected else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE', flush=True)
        print(result.stdout+result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
