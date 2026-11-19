"""Fault injection into synchronous deferred-effect contracts."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('omit_wait_summary','results.py',
     'self.task_wait_parameters.update(execution.task_parameters)',
     'pass # mutated: wait absent from contract',
     'test_wait_and_forward_across_three_calls'),
    ('omit_wait_composition','results.py',
     'self.task_wait_parameters.update(actuals[index].task_parameters)',
     'pass # mutated: wait lost across relay',
     'test_opaque_caller_uses_only_synchronous_contracts'),
    ('omit_forward_summary','results.py',
     'self.task_forward_parameters.update(value.task_parameters)',
     'pass # mutated: returned task input lost',
     'test_wait_and_forward_across_three_calls'),
    ('omit_returned_effects','crust.py',
     'async_field_updates=tuple(update for index in summary.task_forward_parameters\n                                    for update in bindings[params[index][0]].alloc.async_field_updates)',
     'async_field_updates=()',
     'test_wait_and_forward_across_three_calls'),
    ('omit_opaque_wait_application','crust.py',
     'self.apply_async_field_updates(bindings[params[index][0]].alloc)',
     'pass # mutated: opaque wait has no external effect',
     'test_opaque_caller_uses_only_synchronous_contracts'),
    ('skip_scalar_handle_analysis','results.py',
     'and not scalar_reference_inputs and not task_inputs:',
     'and not scalar_reference_inputs:',
     'test_wait_and_forward_across_three_calls'),
)


def main():
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-sync-handle-fields-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_sync_handle_field_effects.SyncHandleFieldEffectsTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run=subprocess.run([sys.executable,'-c',script],cwd=directory,
                               capture_output=True,text=True,timeout=60)
        detected=run.returncode==1 and ('AssertionError' in run.stderr or 'crust.Error:' in run.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(run.stdout+run.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
