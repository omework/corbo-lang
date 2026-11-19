"""Fault injection on independent copies for public view handle contracts."""
from pathlib import Path
import shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('view_result_contract_erased','results.py',
  'fields += tuple((key, frozenset(targets)) for key, targets in result_fields.items())\n        return replace(value, typ=typ, fields=fields)',
  'fields += ()\n        return replace(value, typ=typ, fields=fields)',
  'test_opaque_text_contract_has_no_callee_bodies',('Error not raised',)),
 ('view_projection_erased','crust.py',
  'for index in indexes for key, targets in capture_fields(allocation.dependencies, index))',
  'for index in () for key, targets in capture_fields(allocation.dependencies, index))',
  'test_direct_concrete_to_public_view_conversion',('tranche sans provenance','emprunt','Error not raised')),
 ('all_view_captures_retained','async_lowering.py',
  'return frozenset(node.public_result_views)',
  'return frozenset((1, 2, 3, *node.public_result_views))',
  'test_independent_lifetime_model_and_heterogeneous_frames',('emprunt','capture','AssertionError')),
 ('view_exclusive_capability_erased','crust.py',
  "(('mut.5' if key.startswith('mut.') else 'ref.4')\n                 if mode in ASYNC_SHARED_VIEW_MODES else 'mut.4', targets)",
  "('ref.4' if mode in ASYNC_SHARED_VIEW_MODES else 'mut.4', targets)",
  'test_shared_result_keeps_exclusive_capture',('Error not raised',)),
 ('view_source_constraint_erased','constraints.py',
  "returned = frozenset(asset for key, assets in value.fields\n                                                 if int(key) in indexes for asset in assets)",
  'returned = frozenset()',
  'test_ordered_reset_constraints_through_two_relays',('Error not raised','invariant','reset')),
)

def main():
    success=True
    for name,filename,before,after,method,diagnostics in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-view-handles-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_public_view_handles.PublicViewHandleTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            result=subprocess.run([sys.executable,'-c',script],cwd=directory,capture_output=True,text=True,timeout=120)
        detected=result.returncode==1 and any(message in result.stderr for message in diagnostics)
        print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True);success &= detected
    return int(not success)
if __name__=='__main__':sys.exit(main())
