"""Fault injection into borrowed completion origins and stores."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(('forget_exclusive_stored_target', 'async_lowering.py', 'active_loans[key] = list(loans)', 'pass # no stored loan', 'test_new_target_access_blocked_inside_task'), ('skip_direct_mutable_store', 'async_lowering.py', "steps.append(f'cell_store_ref({cell}, {offset}, {saved});')", "steps.append(f'(void)({cell}); (void)({offset}); (void)({saved});')", 'test_direct_and_helper_store_then_reborrow'), ('self_borrow_unchanged_field', 'async_lowering.py', "current = [(origin, 'stored_mut_target' if field_type == '&mut Int'", "current = [(origin, 'mut' if field_type == '&mut Int'", 'test_conditional_child_completion_does_not_borrow_its_own_field'), ('read_stored_exclusive_target', 'async_lowering.py', "mode not in ('storage', 'shared_target', 'stored_mut_target')", "mode not in ('storage', 'shared_target', 'stored_mut_target', 'mut')", 'test_new_target_access_blocked_inside_task'), ('drop_mutable_field_capability', 'async_lowering.py', 'retained = list(projected)', 'retained = []', 'test_named_reborrow_blocks_replacement_until_last_use'))


def main():
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-mutable-completion-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_mutable_field_completion.MutableFieldCompletionTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run=subprocess.run([sys.executable,'-c',script],cwd=directory,
                               capture_output=True,text=True,timeout=60)
        detected=run.returncode==1 and ('AssertionError' in run.stderr or 'crust.Error:' in run.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(run.stdout+run.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
