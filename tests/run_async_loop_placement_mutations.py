"""Challenge loop placement without modifying source or storage oracles."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('single_pass','if updated == head:', 'if True:', 'test_finite_origin_model_requires_multiple_passes'),
    ('forget_continue','loop_back.append(env.copy())','pass','test_finite_origin_model_requires_multiple_passes'),
    ('forget_break_exit','loop_exits.append(env.copy())\n                return None, results',
     'pass\n                return None, results','test_continue_and_break'),
    ('forget_zero_iteration','loop_exits.append(env.copy())\n            elif op in',
     'pass\n            elif op in','test_recorded_and_zero_iterations'),
    ('unknown_is_empty','if not values or any(value is None for value in values):',
     'values = [value for value in values if value is not None]\n        if not values:','test_finite_origin_model_requires_multiple_passes'),
)

def main():
    suite='test_async_loop_placement.AsyncLoopPlacementTests'
    baseline=run(ROOT,suite)
    print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    ok=True
    for name,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-loop-placement-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/'async_local_placement.py';source=path.read_text()
            assert source.count(before)==1,(name,source.count(before))
            path.write_text(source.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr
        print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        ok &= detected
    return int(not ok)

if __name__=='__main__':sys.exit(main())
