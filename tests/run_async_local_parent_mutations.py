"""Independent source/identity oracles challenged by temporary placement faults."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('choose_shorter_receiver_storage','async_lowering.py',
     'depths.get(targets[name], len(scopes)) < depths.get(previous, len(scopes))',
     'depths.get(targets[name], len(scopes)) > depths.get(previous, len(scopes))',
     'test_two_receivers_choose_the_enclosing_storage'),
    ('forget_named_receiver_destination','async_lowering.py',
     '                place_local_assignments(branch)',
     '                pass',
     'test_existing_parent_receiver_in_child_blocks_and_loops'),
    ('omit_parent_destination','async_lowering.py',
     '                local_destinations[id(constructor)] = destination',
     '                pass',
     'test_recorded_parent_and_successive_transfers'),
    ('overwrite_outer_destination','async_lowering.py',
     'unplaced = [constructor for constructor in constructors if id(constructor) not in local_destinations]',
     'unplaced = list(constructors)',
     'test_recorded_parent_and_successive_transfers'),
    ('omit_owned_field_sources','async_lowering.py',
     '                for _, child in summary.owned_fields:',
     '                for _, child in ():',
     'test_field_pool_cannot_be_promoted_with_root'),
    ('omit_scope_stack_close','async_lowering.py',
     "                steps.append(f'source_close(&{local_pools[name]});')",
     '                pass',
     'test_parent_identity_survives_child_reclamation'),
    ('retain_copied_input_stack','async_lowering.py',
     "                if candidate.kind == 'fresh' and (candidate.source.kind == 'local_value'\n"
     "                        or candidate.source.kind == 'allocation_parameter'\n"
     '                        and candidate.source.index in local_parameters):',
     '                if False:',
     'test_copies_do_not_retain_original_child_stack'),
    ('lose_final_transfer_use','async_lowering.py',
     'return emit_region_block(body, expr[3] if len(expr) > 3 else None, line, valued=False,',
     'return emit_region_block(body[:-1], expr[3] if len(expr) > 3 else None, line, valued=False,',
     'test_match_result_and_branch_assignment'),
)


def main():
    suite='test_async_local_parent.AsyncLocalParentTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-parent-placement-') as directory:
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
