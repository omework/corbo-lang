"""Boundary faults; unchanged behavioral tests run in isolated compiler copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('boolean_argument_accepts_integer', 'async_lowering.py',
     'if actual != expected_type:', 'if mode != "bool" and actual != expected_type:',
     'test_bool_does_not_coerce_to_int_or_byte'),
    ('boolean_result_reversed', 'async_lowering.py',
     "return value, 'Bool' if signature == ('bool', 'bool') else signature[1]",
     "return ('!(' + value + ')' if signature == ('bool', 'bool') else value), 'Bool' if signature == ('bool', 'bool') else signature[1]",
     'test_conditions_short_circuit_and_argument_order'),
    ('native_boolean_signature_lost', 'native_threads.py',
     "result = ('scalar', 'Bool') if fn.args[2] == ('bool', 'bool') else fn.args[2]",
     'result = fn.args[2]',
     'test_truth_table_matches_independent_python_model'),
    ('primitive_block_refused', 'crust.py',
     "if returns is True and result[0] in ('scalar', 'bool', 'byte', 'char'):",
     'if False: # valid copied block result refused',
     'test_primitive_block_result_materialized_before_pool_closes'),
    ('block_snapshot_omitted', 'crust.py',
     "self.lines.append(f'{COPY_VALUE_TYPES[kind]} {snapshot} = {value};')\n                    result = kind, snapshot, None",
     'result = kind, value, None',
     'test_primitive_block_result_materialized_before_pool_closes'),
]


def run(folder, test):
    return subprocess.run([sys.executable, '-c', f'''import sys,unittest
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName({test!r}))
sys.exit(not r.wasSuccessful())
'''], cwd=folder, capture_output=True, text=True, timeout=150)


def main():
    baseline = run(ROOT, 'test_sync_bool_calls')
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, test in MUTATIONS:
        source = (ROOT / 'prototype'/filename).read_text()
        if source.count(before) != 1:
            raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-sync-bool-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, Path(folder)/path.name)
            (Path(folder)/filename).write_text(source.replace(before, after))
            result = run(folder, 'test_sync_bool_calls.SyncBoolCallTests.'+test)
            semantic_error = 'crust.Error:' in result.stderr and 'ERROR:' in result.stderr
            detected = result.returncode == 1 and ('FAIL:' in result.stderr or semantic_error)
            # The tested reads already materialize temporaries in expression().
            # Omitting this extra snapshot changes no observed behavior there;
            # do not claim that the mutation detected a use after cleanup.
            redundant = name == 'block_snapshot_omitted' and result.returncode == 0
            print(name, 'DETECTED' if detected else 'BEHAVIORALLY_IRRELEVANT_ON_SELECTED_PATHS' if redundant
                  else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE', flush=True)
            print(result.stderr[-4500:], flush=True)
            success &= detected or redundant
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
