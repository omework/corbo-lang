"""Exercise compiler reservations and runtime ordering/reclamation faults."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('remove_receiver_reservation_erased','async_lowering.py',
  "reservation = [(receiver, 'mut')]\n        active_loans[id(reservation)] = reservation\n        try:\n            value = expression(arguments[0], line)",
  "reservation = []\n        active_loans[id(reservation)] = reservation\n        try:\n            value = expression(arguments[0], line)",
  'test_receiver_reserved_during_suspended_index'),
 ('remove_index_forced_to_zero','async_lowering.py',
  "steps.append(f'vector_remove(frame->{fields[receiver]}, {index}, &{result});')",
  "steps.append(f'vector_remove(frame->{fields[receiver]}, 0, &{result});')",
  'test_remove_preserves_order_on_both_storage_fronts'),
 ('runtime_shift_omitted','crust.py',
  'memcpy(vector_item_at(items, i), vector_item_at(items, i + 1), items->element_size);',
  'memcpy(vector_item_at(items, i), vector_item_at(items, i), items->element_size);',
  'test_remove_preserves_order_on_both_storage_fronts'),
 ('runtime_length_not_reclaimed','crust.py',
  'vector_truncate(items, items->length - 1);',
  'vector_truncate(items, items->length);',
  'test_generated_removals_match_list_model'),
]


def main():
    success=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor')
        with tempfile.TemporaryDirectory(prefix='crust-remove-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_vector_remove.AsyncVectorRemoveTests.{test}')
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
