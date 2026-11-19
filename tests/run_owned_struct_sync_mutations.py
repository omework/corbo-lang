"""Mutate bridge/loan/cleanup code in isolated copies, keeping oracles intact."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('omit_bridge_graph','crust.py',
     '                owned_bridge_fields(allocation, parameter)',
     '                # missing graph metadata',
     'test_recorded_consume_and_explicit_marker'),
    ('read_err_payload','crust.py',
     '{pointer} ? cell_load_ref({pointer}, {offset}) : NULL;',
     'cell_load_ref({pointer}, {offset});',
     'test_result_argument_handles_success_and_error'),
    ('omit_prepared_graph_cleanup','async_lowering.py',
     'for _, cells, _ in reversed(pending_capture_groups):',
     'for _, cells, _ in ():',
     'test_identity_and_suspended_prepared_cleanup'),
    ('drop_returned_graph','async_lowering.py',
     "                steps.extend((f'frame->result = {received};', f'{received} = NULL;'))",
     "                steps.append(f'cell_drop({received});')\n                steps.extend((f'frame->result = {received};', f'{received} = NULL;'))",
     'test_identity_and_suspended_prepared_cleanup'),
    ('lose_owned_field_loan','async_lowering.py',
     '            loans = project_field_loans(origins, path)',
     '            loans = []',
     'test_field_borrow_blocks_consuming_call'),
)


def main():
    suite='test_async_owned_struct_sync_calls.AsyncOwnedStructSyncCallTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-owned-sync-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr and
            'internal error:' not in result.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
