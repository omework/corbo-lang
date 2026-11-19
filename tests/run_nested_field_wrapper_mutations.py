"""Mutate projected contracts without changing the external test oracle."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('forget_child_targets','results.py',
     'return replace(value, fields=tuple((dict(value.fields) | changes).items()))',
     'return value','test_read_updated_child_then_update_its_sibling'),
    ('omit_initial_descendant_fields','results.py',
     "fields=nested_reference_fields(environment[name].fields, f'{prefix}{arm}.{field}'),",
     'fields=(),','test_conditional_contract_keeps_old_and_new'),
    ('forget_constraint_projection','constraints.py',
     "owned_path=(*carrier.owned_path, key) if declared.startswith('A<') else ()",
     'owned_path=()','test_recorded_wrapper_contract'),
    ('forget_concrete_descendants','crust.py',
     "if any('/' in path for path, _ in fields):",
     'if False:','test_sync_caller_and_conditional_old_target'),
    ('lose_nested_effect_path','async_lowering.py',
     'path = stored_field_path(field)\n                field_type = borrowed_field_type(typ, path)',
     "path = tuple(field.lstrip('.').split('.'))\n                field_type = borrowed_field_type(typ, path)",
     'test_recorded_wrapper_contract'),
)

def main():
    suite='test_nested_field_wrappers.NestedFieldWrapperTests'
    baseline=run(ROOT,suite)
    print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-wrapper-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;source=path.read_text()
            assert source.count(before)==1,(name,source.count(before))
            path.write_text(source.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)

if __name__=='__main__':sys.exit(main())
