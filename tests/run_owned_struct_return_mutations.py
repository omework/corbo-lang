"""Keep result-field source and destruction oracles independent of mutations."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('collapse_field_pool_into_root','crust.py',
     'sources, origins = storage.get(path, ((), frozenset()))',
     'sources, origins = allocation.sources, allocation.origins',
     'test_nested_owned_graph_lifetime_model'),
    ('omit_result_field_graph','crust.py',
     '        self.restore_async_owned_fields(payload, owned_fields)',
     '        # missing result fields',
     'test_recorded_return_and_failure'),
    ('lose_factory_result_fields','results.py',
     'task_result_fields=tuple((path, resolve_sources(sources)) for path, sources in summary.task_result_fields)',
     'task_result_fields=()',
     'test_factories_and_task_forwarding'),
    ('destroy_return_before_remittance','async_lowering.py',
     "            steps.extend((f'frame->result = {member};', f'{member} = NULL;'))",
     "            steps.append(f'cell_drop({member});')\n            steps.extend((f'frame->result = {member};', f'{member} = NULL;'))",
     'test_identity_and_cleanup_before_and_after_remittance'),
    ('omit_field_source_constraint','constraints.py',
     'return paths, Value(kind, definition.args[2][1], execution.task_result_assets, execution.task_result_fields)',
     'return paths, Value(kind, definition.args[2][1], execution.task_result_assets)',
     'test_field_source_requirement_in_legacy_contract'),
)


def main():
    suite='test_async_owned_struct_returns.AsyncOwnedStructReturnTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-owned-return-') as directory:
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
