"""Fault injection into borrowed completion origins and stores."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(('omit_completion_result_origins', 'async_lowering.py', 'if completion and completion.complete and completion.structure_fields:', 'if False and completion and completion.complete and completion.structure_fields:', 'test_old_and_new_result_have_distinct_targets'), ('project_after_completed_stores', 'crust.py', 'reference_result = (self.project_task_result_captures(task_name, allocation.dependencies,', 'self.apply_async_field_updates(allocation)\n        reference_result = (self.project_task_result_captures(task_name, allocation.dependencies,', 'test_old_and_new_result_have_distinct_targets'), ('omit_direct_store', 'async_lowering.py', "steps.append(f'cell_store_ref({cell}, {offset}, {saved});')", "steps.append(f'(void)({cell}); (void)({offset}); (void)({saved});')", 'test_direct_reference_store_matches_helper'), ('omit_stored_target_reservation', 'async_lowering.py', 'active_loans[key] = list(loans)', 'pass # lost shared target', 'test_direct_store_keeps_shared_target_reserved'), ('check_constraints_before_origins', 'crust.py', 'incomplete_constraints = {name: None for name in self.functions}', 'ConstraintAnalyzer(self.functions, self.function_effects, self.function_results, Error, self.enums, async_functions).infer_all()\n        incomplete_constraints = {name: None for name in self.functions}', 'test_result_and_field_require_independent_pools'))


def main():
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-borrowed-completion-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_borrowed_field_completion.BorrowedFieldCompletionTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run=subprocess.run([sys.executable,'-c',script],cwd=directory,
                               capture_output=True,text=True,timeout=60)
        detected=run.returncode==1 and ('AssertionError' in run.stderr or 'crust.Error:' in run.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(run.stdout+run.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
