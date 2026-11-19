"""Temporary faults in synchronous borrowed calls; independent tests unchanged."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ('prepared_reference_unprotected',
     'value, held = sync_borrow_argument(argument, mode, typ, line)\n                    loans.extend(held)',
     'value, held = sync_borrow_argument(argument, mode, typ, line)\n                    pass # lost prepared reference',
     'test_prepared_references_reserve_later_arguments'),
    ('returned_alternative_lost', 'retained.extend(argument_loans[target.parameter])',
     'if target.parameter == 0: retained.extend(argument_loans[target.parameter])',
     'test_local_result_tracks_union_but_not_unreturned_parameters'),
    ('future_named_uses_ignored',
     'if not utf8_current_live(tail, name, earlier=remaining,\n                                         owner_depth=owner_depth, owned=True):',
     'if True:', 'test_last_use_inside_earlier_argument_and_future_uses'),
    ('wrong_returned_pointer', "steps.append(f'{value} = {call};')\n        if signature in owned_sync_types:",
     "steps.append(f'{value} = {prepared[0] if signature in reference_sync_types else call};')\n        if signature in owned_sync_types:",
     'test_local_result_tracks_union_but_not_unreturned_parameters'),
    ('child_return_loan_lost',
     'if index in result_paths:\n                        returned_loans.extend(inherited)',
     'if False:\n                        returned_loans.extend(inherited)',
     'test_returned_reference_is_captured_by_async_child'),
]


def main():
    baseline=subprocess.run([sys.executable,'-c',f'''import sys,unittest
sys.path[:0]=[{str(ROOT / 'prototype')!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_sync_borrow_calls')
result=unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
'''],cwd=ROOT,capture_output=True,text=True,timeout=120)
    print('BASELINE', 'PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,test in MUTATIONS:
        if sys.argv[1:] and name not in sys.argv[1:]:continue
        source=(ROOT / 'prototype'/'async_lowering.py').read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-sync-borrow-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/'async_lowering.py').write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_sync_borrow_calls.SyncBorrowCallTests.{test}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            run=subprocess.run([sys.executable,'-c',script],cwd=folder,capture_output=True,text=True,timeout=120)
            detected=run.returncode==1 and 'FAIL:' in run.stderr
            print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(run.stderr[-3500:],flush=True)
            success &= detected
    return 0 if success else 1


if __name__=='__main__':sys.exit(main())
