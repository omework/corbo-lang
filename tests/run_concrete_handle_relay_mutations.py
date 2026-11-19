"""Fault injection for input snapshots and ordered handle source contracts."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('input_descriptor_not_saved','crust.py',
  "                    or mode in ('task', 'execution')):",
  "                    or False):",'test_recorded_return_and_last_use',('capture empruntée introuvable',)),
 ('empty_public_group_becomes_local','results.py',
  "if not origins and isinstance(actual, Value) and is_public_handle(actual.typ):",
  "if False and not origins and isinstance(actual, Value) and is_public_handle(actual.typ):",
  'test_inline_indirect_and_detached_fields',('cible empruntée non durable',)),
 ('concrete_result_source_erased','constraints.py',
  'reference_assets = frozenset({asset})','reference_assets = frozenset()',
  'test_concrete_sources_survive_public_conversion',('not found',)),
 ('owned_capture_not_checked_at_join','constraints.py',
  "self.touch_assets(execution.all_assets, paths['next'], line)",
  "self.touch_assets(execution.reservations, paths['next'], line)",
  'test_owned_capture_reset_order',('Error not raised',)),
 ('shared_field_retains_carrier','constraints.py',
  "actual.assets | actual.reservations if declared == '&mut Int' else frozenset()",
  'actual.assets | actual.reservations',
  'test_projected_field_sources_through_concrete_factory',('True is not false',)),
 ('public_conversion_forgets_nonresult_captures','constraints.py',
  "return replace(value, typ=public, fields=fields)",
  "return replace(value, typ=public, fields=tuple((key, targets) for key, targets in fields if key in ('4','5')))",
  'test_pending_nonresult_capture_reset_order',('False != True','Error not raised')),
 ('pending_execution_untracked','constraints.py',
  'state.pending_executions[token] = value.all_assets',
  'state.pending_executions[token] = frozenset()',
  'test_nonreturning_path_keeps_running_captures',('Error not raised',)),
 ('join_does_not_release_pending_execution','constraints.py',
  "paths['next'].pending_executions.pop(token, None)",
  "paths['next'].pending_executions.get(token)",
  'test_owned_capture_reset_order',('AssertionError','reset interdit')),
)

def main():
    success=True
    for name,filename,before,after,method,diagnostics in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-concrete-handle-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_concrete_handle_relays.ConcreteHandleRelayTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            result=subprocess.run([sys.executable,'-c',script],cwd=directory,
                                  capture_output=True,text=True,timeout=120)
        detected=result.returncode==1 and any(d in result.stderr for d in diagnostics)
        print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True);success &= detected
    return int(not success)

if __name__=='__main__':sys.exit(main())
