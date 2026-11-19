"""Detect rejected valid returns, premature destruction and missing child cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('reject_direct_owned_return',
     "        elif returns_owned:\n            if value[0] in ('array_transfer', 'new_transfer'):",
     "        elif returns_owned:\n            if value[0] in ('array_transfer', 'new_transfer') and (sync_signature(value[1]) in owned_sync_types or value[1][0] == 'new'):",
     'test_recorded_direct_return'),
    ('destroy_returned_allocation',
     "                steps.extend((f'frame->result = {received};', f'{received} = NULL;'))",
     "                steps.append(f'cell_drop({received});')\n"
     "                steps.extend((f'frame->result = {received};', f'{received} = NULL;'))",
     'test_direct_return_identity_and_suspended_destruction'),
    ('forget_suspended_child',
     'if child is not None:\n            owned_child(child)',
     'if child is not None:\n            pass',
     'test_direct_return_identity_and_suspended_destruction'),
)


def main():
    suite='test_async_direct_owned_returns.AsyncDirectOwnedReturnsTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-direct-owned-return-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/'async_lowering.py'
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr and 'internal error:' not in result.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
