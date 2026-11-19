"""Challenge awaited Result routing and owners held across suspension."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('reject_awaited_result','''        if expr[0] == 'await':
            if awaits_execution(expr):''',
     '''        if expr[0] == 'await':
            fail(line, 'mutant: awaited Result rejected')
            if awaits_execution(expr):''', 'test_recorded_argument_and_handle_consumption'),
    ('leak_sync_prepared_result','prepared_owners.append(pending)',
     'pass  # mutant: lost pending Result', 'test_async_capture_and_interrupted_later_argument'),
    ('leak_async_prepared_result',"prepared_owners.append(f'{captured}.{JOIN_CELLS[mode]}')",
     'pass  # mutant: lost pending capture', 'test_async_capture_and_interrupted_later_argument'),
    ('forget_suspended_arguments','for _, cells, _ in reversed(pending_capture_groups):',
     'for _, cells, _ in ():', 'test_select_loser_cleans_prepared_awaited_result'),
    ('destroy_returned_payload',
     "            steps.extend((f'frame->result = {joined};', f'{joined}.{JOIN_CELLS[join_return_mode]} = NULL;'))",
     "            steps.append(f'if ({joined}.{JOIN_CELLS[join_return_mode]}) cell_drop({joined}.{JOIN_CELLS[join_return_mode]});')\n"
     "            steps.extend((f'frame->result = {joined};', f'{joined}.{JOIN_CELLS[join_return_mode]} = NULL;'))",
     'test_return_task_and_computed_handle_expressions'),
)


def main():
    suite='test_async_awaited_owned_results.AsyncAwaitedOwnedResultsTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-awaited-results-') as directory:
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
