"""Mutate preparation and publication, without changing semantic oracles."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('receiver_reservation_removed',
  "preparation = [(receiver, 'mut')]\n        active_loans[id(preparation)] = preparation\n        prepared = []",
  "preparation = []\n        active_loans[id(preparation)] = preparation\n        prepared = []",
  'test_receiver_is_reserved_during_argument_await'),
 ('argument_snapshot_removed',
  "steps.append(f'{snapshot} = {value};')\n                prepared.append(snapshot)",
  "steps.append(f'{snapshot} = {value};')\n                prepared.append(value)",
  'test_suspended_arguments_are_snapshotted_left_to_right'),
 ('replace_payload_erased',
  "steps.append(f'{result}.status = vector_replace({cell}, {prepared[0]}, &{result}.value);')",
  "steps.append(f'{result}.status = vector_replace({cell}, {prepared[0]}, &{result}.value); {result}.value = 0;')",
  'test_generated_operation_sequences_against_list_model'),
 ('extend_success_faked',
  "steps.append(f'{result} = vector_try_extend_slice({cell}, {prepared[0]});')",
  "steps.append(f'{result} = vector_try_extend_slice({cell}, {prepared[0]}); {result}.status = 0;')",
  'test_atomic_extension_capacity_and_read_priority'),
 ('fallible_statement_guard_removed',
  "if operation[0] not in ('int_option', 'byte_option'):\n                    fail(statement.line, 'résultat faillible sans usage explicite')",
  "if False:\n                    fail(statement.line, 'résultat faillible sans usage explicite')",
  'test_discarded_fallible_operations_require_explicit_use'),
]


def main():
    source=(ROOT / 'prototype'/'async_lowering.py').read_text();success=True
    for name,before,after,test in MUTATIONS:
        if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor')
        with tempfile.TemporaryDirectory(prefix='crust-vector-operation-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/'async_lowering.py').write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_vector_operations.AsyncVectorOperationTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-2000:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
