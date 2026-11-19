"""Fault injection for projected field dependencies, in temporary copies."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('lose_owned_prefix','async_lowering.py','full_path = (*prefix, *path)','full_path = path',
     'test_recorded_transfer_releases_only_old_target'),
    ('forget_projected_update','results.py',
     'environment[carrier.storage_owner] = update_descendant(owner, carrier.owned_path)',
     'pass # lost descendant update','test_async_changes_owned_graph_and_returns_it'),
    ('forget_flattened_targets','results.py',
     "flattened = dict(value.fields) | {prefix + field: targets for field, targets in changes.items()}",
     'flattened = dict(value.fields)','test_async_changes_owned_graph_and_returns_it'),
    ('forget_child_targets','results.py',
     'return replace(value, fields=tuple((dict(value.fields) | changes).items()))',
     'return value','test_async_changes_owned_graph_and_returns_it'),
)

def main():
    suite='test_nested_field_replacement.NestedFieldReplacementTests'
    baseline=run(ROOT,suite)
    print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-nested-fields-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            source=path.read_text()
            assert source.count(before)==1,(name,source.count(before))
            path.write_text(source.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)

if __name__=='__main__':sys.exit(main())
