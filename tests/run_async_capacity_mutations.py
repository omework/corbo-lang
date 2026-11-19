"""AS7 faults in temporary copies; independent live-instance tests must detect them."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ('fixed_sixteen_cap', 'async_capacity.py',
     'result[name] = max(1, bound)', 'result[name] = max(1, min(16, bound))',
     'test_more_than_sixteen_retained_tasks_and_function_returns'),
    ('children_not_counted', 'async_capacity.py',
     'bound += result[parent] * frame_slots[parent]', 'bound += 0',
     'test_independent_live_instance_model_matches_nested_frames'),
    ('branch_history_lost', 'crust.py',
     '    def restore(self, state):\n        self.record_async_slots()',
     '    def restore(self, state):\n        # faulty: forget non-continuing branches',
     'test_all_returning_branch_slots_are_counted'),
    ('explicit_bound_enlarged', 'async_capacity.py',
     'result = dict(explicit)', 'result = {name: size + 1 for name, size in explicit.items()}',
     'test_recursive_parent_occupies_slot_until_child_finishes'),
]


def main():
    success=True
    for name, filename, before, after, test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:
            raise SystemExit(f'{name}: mutation anchor changed')
        with tempfile.TemporaryDirectory(prefix='crust-async-capacity-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path,target/path.name)
            (target/filename).write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_async_capacity.AsyncCapacityTests.{test}')
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not r.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            status='DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE'
            print(name,status,flush=True)
            print(run.stderr[-1800:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':
    sys.exit(main())
