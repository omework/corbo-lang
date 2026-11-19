"""Enums: fault injection in isolated implementations, with fixed source oracles."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('wrong_arm','async_lowering.py',
     '''steps.append(f'{cell} = enum_new({source}, {arm_index}, "{label}");')''',
     '''steps.append(f'{cell} = enum_new({source}, 0, "{label}");')''',
     'test_local_pools_keep_per_arm_layout_and_capacity'),
    ('inspect_inactive_arm','crust.py',
     "present = f'{pointer} && {pointer}->source->arm_tag == {tag}'", "present = f'{pointer}'",
     'test_sync_bridge_reads_only_active_variant'),
    ('lose_join_variants','crust.py',
     'self.restore_async_owned_fields(payload, owned_fields, variants)',
     'self.restore_async_owned_fields(payload, owned_fields)',
     'test_owned_fields_of_inactive_variants_are_not_read'),
    ('lose_public_variants','crust.py',
     'task_result_variants=self.resolve_task_variants(summary, params, bindings),',
     'task_result_variants=frozenset(),', 'test_public_handle_and_relay_keep_reference_field'),
    ('lose_enum_field_paths','async_lowering.py',
     "return tuple(owned_reference_paths({name: {'': layout} for name, layout in struct_layouts.items()} | enum_layouts, typ))",
     "return tuple(owned_reference_paths({name: {'': layout} for name, layout in struct_layouts.items()}, typ))",
     'test_select_borrowed_enum_fields_remain_live'),
)

def main():
    suite='test_async_owned_enums.AsyncOwnedEnumTests'
    baseline=run(ROOT,suite)
    print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-async-enum-') as directory:
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
