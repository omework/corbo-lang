"""Temporary faults for local output injection, source kind and cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('omit_caller_reservation','crust.py',
     '            check.local_reservations[id(call)] = source, layout, reserved',
     '            # missing caller destination',
     'test_recorded_owned_child_and_suspension'),
    ('erase_local_input_kind','crust.py',
     "'local_stack' if index in local_parameters else 'symbolic'",
     "'symbolic'",
     'test_copy_owned_and_borrowed_local_values'),
    ('omit_suspended_stack_close','async_lowering.py',
     '                    cleanup.append(f\'source_close(&{local_pools[name]});\')',
     '                    pass',
     'test_suspended_cleanup_releases_receiver_stack'),
    ('allow_local_as_pool_allocation','async_lowering.py',
     'if contract.parameters[index][0] in contract.handle_parameters and storage_of(value) & implicit_stacks:',
     'if False:',
     'test_local_value_is_not_a_pool_allocation'),
    ('erase_replacement_type_distinction','async_lowering.py',
     'if receiver_is_local != bool(storage_of(replacement) & implicit_stacks):',
     'if False:',
     'test_replacement_preserves_local_or_allocated_type'),
)


def main():
    suite='test_async_local_struct_helpers.AsyncLocalStructHelperTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-local-helper-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;original=path.read_text()
            expected=2 if name=='erase_local_input_kind' else 1
            assert original.count(before)==expected,(name,original.count(before))
            changed=original.replace(before,after)
            if name=='erase_local_input_kind':
                # The first campaign stopped at an unused-reservation warning.
                # Silence that warning only in the mutant to exercise its
                # incorrect copy path and live unclaimed reservation at runtime.
                anchor='            check.local_reservations[id(call)] = source, layout, reserved'
                assert changed.count(anchor)==1
                changed=changed.replace(anchor,"            check.lines.append(f'(void){reserved};')\n"+anchor)
            path.write_text(changed)
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr and
            'internal error:' not in result.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
