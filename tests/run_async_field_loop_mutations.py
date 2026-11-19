"""Fault injection into borrowed completion origins and stores."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(('forget_backedge_field_targets', 'async_lowering.py', 'if set(roots) - set(initial):', 'if False: # missing backedge sources', 'test_backedge_reserves_new_target_before_next_iteration'), ('ignore_field_hints', 'async_lowering.py', 'active_loans[key] = list(roots)', 'pass # widened sources never installed', 'test_while_zero_one_and_many_iterations'), ('forget_initial_field_target', 'async_lowering.py', 'roots = tuple(dict.fromkeys((*initial, *additions)))', 'roots = tuple(dict.fromkeys(additions))', 'test_iteration_snapshot_keeps_initial_and_later_cells'), ('confuse_nested_loop_identity', 'async_lowering.py', 'additions[key] = tuple(roots)', "additions[('stored_field', holder, ('missing',))] = tuple(roots)", 'test_nested_loops_and_early_return'))


def main():
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-field-loops-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_async_field_loops.AsyncFieldLoopTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run=subprocess.run([sys.executable,'-c',script],cwd=directory,
                               capture_output=True,text=True,timeout=60)
        detected=run.returncode==1 and ('AssertionError' in run.stderr or 'crust.Error:' in run.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if run.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(run.stdout+run.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
