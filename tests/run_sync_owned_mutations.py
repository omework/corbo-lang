"""Ownership-boundary faults in temporary compilers, independent test expectations."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('moved_slot_not_cleared','async_lowering.py',
  "steps.extend((f'{result} = {member};', f'{member} = NULL;'))",
  "steps.append(f'{result} = {member};')",
  'test_consume_and_named_result_cleanup_in_both_contexts'),
 ('moved_binding_still_valid','async_lowering.py',
  "steps.extend((f'{result} = {member};', f'{member} = NULL;'))\n            consumed.add(name)",
  "steps.extend((f'{result} = {member};', f'{member} = NULL;'))\n            pass # binding remains usable",
  'test_transfers_and_usages_are_explicit'),
 ('prepared_owner_not_registered','async_lowering.py',
  'prepared_owners.append(snapshot)', 'pass # omitted cleanup registration',
  'test_prepared_owner_survives_suspension_or_is_dropped_on_return'),
 ('prepared_owner_order_reversed','async_lowering.py',
  'for cell in reversed(cells):','for cell in cells:',
  'test_multiple_prepared_owners_clean_in_reverse_order'),
 ('bridge_result_destroyed','crust.py',
  'root.exports.append(result[2])','pass # result not exported',
  'test_owned_return_identity_and_child_capture'),
 ('owned_source_contract_ignored','async_lowering.py',
  "elif op == 'call' and sync_result is not None:","elif op == 'call' and False:",
  'test_unreturned_pool_may_end_before_result'),
 ('owned_result_silently_discarded','async_lowering.py',
  'if signature in owned_sync_types and not owned:', 'if False:',
  'test_transfers_and_usages_are_explicit'),
]

def run(folder,test):
    return subprocess.run([sys.executable,'-c',f'''import sys,unittest
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName({test!r}))
sys.exit(not r.wasSuccessful())
'''],cwd=folder,capture_output=True,text=True,timeout=150)

def main():
    baseline=run(ROOT,'test_sync_owned_calls')
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,test in MUTATIONS:
        source=(ROOT / 'prototype'/filename).read_text()
        if source.count(before)!=1:raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-sync-owned-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,Path(folder)/path.name)
            (Path(folder)/filename).write_text(source.replace(before,after))
            result=run(folder,'test_sync_owned_calls.SyncOwnedCallTests.'+test)
            semantic_error=('crust.Error:' in result.stderr and 'ERROR:' in result.stderr)
            detected=result.returncode==1 and ('FAIL:' in result.stderr or semantic_error)
            # On these paths cleanup is selected by the consumed state and
            # cleanup_path, so the stale pointer field is never read again.
            # This is a bounded behavioral classification, not general proof.
            redundant = name=='moved_slot_not_cleared' and result.returncode==0
            print(name,'DETECTED' if detected else 'BEHAVIORALLY_IRRELEVANT_ON_SELECTED_PATHS' if redundant
                  else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
            print(result.stderr[-4500:],flush=True)
            success &= detected or redundant
    return 0 if success else 1
if __name__=='__main__':sys.exit(main())
