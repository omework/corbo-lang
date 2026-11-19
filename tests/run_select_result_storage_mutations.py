"""Concrete storage faults in isolated compiler copies; source oracles unchanged."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('ignore_select_storage', 'signatures.add(task_result_signature(record))',
     'signatures.add(functions[record[3]].args[2])', 'test_recorded_mixed_storage'),
    ('ignore_selection_if_storage',
     'signature = kind, record.awaited, task_result_signature(record.branches[0])',
     'signature = kind, record.awaited, functions[record.branches[0][3]].args[2]',
     'test_selection_through_if_or_loop_keeps_storage'),
    ('ignore_selection_break_storage',
     'returns_int, nominal = record.awaited, task_result_signature(record.branches[0])',
     'returns_int, nominal = record.awaited, functions[record.branches[0][3]].args[2]',
     'test_selection_through_if_or_loop_keeps_storage'),
    ('ignore_task_alternative_storage',
     "if kind in ('task', 'execution') and task_result_signature(record)[2] is not None:",
     "if kind == 'execution' and task_result_signature(record)[2] is not None:",
     'test_task_alternatives_cannot_hide_mixed_result_storage'),
    ('keep_unreturned_local_capture',
     "or effect and effect.complete and effect.completion_result.candidates):",
     "or False):", 'test_fresh_results_do_not_inherit_unreturned_capture_storage'),
)


def main():
    suite='test_select_result_storage.SelectResultStorageTests'
    baseline=run(ROOT,suite)
    print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-select-storage-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/'async_lowering.py';source=path.read_text()
            assert source.count(before)==1,(name,source.count(before))
            path.write_text(source.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
