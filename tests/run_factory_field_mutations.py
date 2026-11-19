"""Fault injection into synchronous deferred-effect contracts."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(('omit_factory_return_contract', 'results.py', 'for carrier, fields in value.deferred_field_updates:', 'for carrier, fields in ():', 'test_opaque_factory_contract'), ('omit_factory_composition', 'results.py', 'self.instantiate_deferred_fields(summary.task_field_updates, actuals)', 'frozenset()', 'test_opaque_factory_contract'), ('omit_fresh_wait_effect', 'results.py', 'self.apply_deferred_field_updates(actuals[index], environment, line)', 'pass # missing completion', 'test_fresh_task_waited_inside_factory'), ('omit_factory_reception', 'crust.py', 'replace(summary, structure_fields=summary.task_field_updates)', 'replace(summary, structure_fields=())', 'test_opaque_factory_contract'), ('omit_native_bridge_effects', 'async_lowering.py', 'replace(contract.result, structure_fields=contract.result.task_field_updates)', 'replace(contract.result, structure_fields=())', 'test_completed_factory_child_keeps_stored_target_reserved'), ('omit_spawn_failure_alternative', 'results.py', 'dict(current.fields).get(field, frozenset()) | targets', 'targets', 'test_alternative_updates_waited_inside_helper'), ('omit_direct_fresh_wait', 'results.py', 'self.apply_deferred_field_updates(execution, environment, line)', 'pass # missing direct completion', 'test_direct_wait_inside_factory'), ('stop_contracts_before_fixed_point', 'crust.py', 'if self.function_results == previous_results:', 'if True: # missing feedback to async contract', 'test_native_wait_and_reset_contract_order'))


def main():
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-factory-fields-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_factory_field_effects.FactoryFieldEffectsTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run=subprocess.run([sys.executable,'-c',script],cwd=directory,
                               capture_output=True,text=True,timeout=60)
        detected=run.returncode==1 and ('AssertionError' in run.stderr or 'crust.Error:' in run.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(run.stdout+run.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
