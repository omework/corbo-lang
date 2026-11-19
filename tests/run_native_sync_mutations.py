"""Inject faults into temporary compilers; keep the tests/oracles unchanged."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('arguments_reversed', 'async_lowering.py',
     'for index, (argument, (_, mode, typ)) in enumerate(zip(expr[2], contract.parameters)):',
     'for index, (argument, (_, mode, typ)) in reversed(list(enumerate(zip(expr[2], contract.parameters)))):',
     'test_nested_calls_preserve_argument_and_cleanup_order'),
    ('hidden_join_accepted', 'async_lowering.py',
     'if contract.effects.blocking_join and not node.native_block:',
     'if False:', 'test_transitive_join_allowed_in_native_refused_in_async'),
    ('indirect_creation_edges_lost', 'async_capacity.py',
     'synchronous = synchronous or {}', 'synchronous = {}',
     'test_hidden_creation_cycle_needs_explicit_capacity'),
    ('helper_slots_omitted', 'crust.py',
     'self.async_frame_slots[parent] += sum(', 'self.async_frame_slots[parent] += 0 * sum(',
     'test_indirect_state_slots_count_for_each_live_parent'),
]


def main():
    detected_all = True
    for name, filename, before, after, test in MUTATIONS:
        if sys.argv[1:] and name not in sys.argv[1:]:
            continue
        source = (ROOT / 'prototype' / filename).read_text()
        if source.count(before) != 1:
            raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-native-sync-mut-') as folder:
            target = Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            (target / filename).write_text(source.replace(before, after))
            script = f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_native_sync_calls.NativeSyncCallTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run = subprocess.run([sys.executable, '-c', script], cwd=folder,
                                 capture_output=True, text=True, timeout=120)
            detected = run.returncode == 1 and 'FAIL:' in run.stderr
            print(name, 'DETECTED' if detected else 'SURVIVED' if run.returncode == 0 else 'INCONCLUSIVE', flush=True)
            print(run.stderr[-3500:], flush=True)
            detected_all &= detected
    return 0 if detected_all else 1


if __name__ == '__main__':
    sys.exit(main())
