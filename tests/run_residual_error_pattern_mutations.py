"""Check residual coverage, side effects, and exhaustiveness independently."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('only_first_residual_error_lowered',
  'arms.extend((value, copy.deepcopy(body)) for value in residual_errors)',
  'arms.extend((value, copy.deepcopy(body)) for value in residual_errors[:1])',
  'test_residual_read_errors_do_not_capture_success'),
 ('residual_side_effects_erased',
  'arms.extend((value, copy.deepcopy(body)) for value in residual_errors)',
  'arms.extend((value, []) for value in residual_errors)',
  'test_residual_read_errors_do_not_capture_success'),
 ('exhaustiveness_removed',
  'if None not in seen and (family is None or seen != expected):',
  'if False:',
  'test_missing_success_duplicates_and_type_mismatch_remain_rejected'),
]


def main():
    source=(ROOT / 'prototype'/'crust.py').read_text();success=True
    for name,before,after,test in MUTATIONS:
        if source.count(before)!=1:raise SystemExit(f'{name}: changed anchor')
        with tempfile.TemporaryDirectory(prefix='crust-residual-pattern-mut-') as folder:
            target=Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            (target/'crust.py').write_text(source.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{folder!r},{str(ROOT/'tests')!r}]
suite=unittest.defaultTestLoader.loadTestsFromName('test_residual_error_patterns.ResidualErrorPatternTests.{test}')
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
