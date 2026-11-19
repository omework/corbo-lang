"""Faults in storage requirement inference and its contract publication."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('omit_annotation','storage_requirements.py',
  "require(context, value, 'local', line)", 'pass', 'test_recorded_annotation'),
 ('omit_call_propagation','storage_requirements.py',
  'require(context, actuals[index], required, line)', 'pass', 'test_sync_factory_preserves_requirement'),
 ('one_inference_pass','storage_requirements.py',
  'if all(node.storage_requirements == previous[name] for name, node in catalog.items()):',
  'if True:', 'test_sync_factory_preserves_requirement'),
 ('forget_contract_requirement','contracts.py',
  "storage_requirements=getattr(node, 'storage_requirements', ())", 'storage_requirements=()',
  'test_sync_helper_requirement_and_async_relay'),
 ('first_origin_only','storage_requirements.py',
  'for asset in value.assets:', 'for asset in list(value.assets)[:1]:',
  'test_two_possible_sources_require_both_local'),
 ('forget_symbolic_local_input','crust.py',
  "storage_kind = ('local_stack' if dict(node.storage_requirements).get(index) == 'local'\n                                    else 'symbolic')",
  "storage_kind = 'symbolic'", 'test_sync_helper_requirement_and_async_relay'),
)

def main():
 suite='test_storage_requirements.StorageRequirementTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-storage-requirements-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;source=path.read_text();assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)

if __name__=='__main__':sys.exit(main())
