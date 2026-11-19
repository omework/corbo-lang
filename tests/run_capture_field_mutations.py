"""Field-contract faults in disposable compilers; source oracles stay intact."""
from pathlib import Path
import shutil,sys,tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('merge_capture_fields','capture_paths.py',
  'selector = str(selector)',"selector = str(selector).partition('/')[0]",
  'test_mixed_task_relay_and_independent_access_model'),
 ('erase_result_targets','crust.py',
  '            fields.append((field, tuple(roots.values())))',
  '            fields.append((field, ()))',
  'test_whole_return_recorded_and_drop_boundary'),
 ('rejoin_async_field_loans','async_lowering.py',
  '                    held.extend(captured)',
  '                    held.extend(argument_loans[target.parameter])',
  'test_shared_fields_detach_independently_after_relay'),
 ('erase_async_field_loans','async_lowering.py',
  '                    held.extend(captured)',
  '                    pass',
  'test_async_caller_direct_and_factory'),
 ('erase_result_field_path','capture_paths.py',
  "return f'{target.parameter}/{target.field}'", 'return str(target.parameter)',
  'test_shared_fields_detach_independently_after_relay'),
 ('retain_unreturned_field','crust.py',
  "            if field:\n                paths = tuple(path for path in paths if not path or '.' + '.'.join(path) == field)",
  '            if False:\n                paths = ()',
  'test_detached_result_releases_unrelated_field'),
 ('forget_factory_field_loan','async_lowering.py',
  'held.extend(argument_fields[(target.parameter, target.field)])', 'pass',
  'test_async_caller_direct_and_factory'),
)
def main():
 suite='test_async_capture_field_contracts.CaptureFieldContractTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 success=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-capture-field-mutant-') as directory:
   target=Path(directory)
   for p in (ROOT / 'prototype').glob('*.py'):shutil.copy2(p,target/p.name)
   path=target/filename;source=path.read_text()
   assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and ('AssertionError' in result.stderr or 'crust.Error:' in result.stderr)
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);success &= detected
 return int(not success)
if __name__=='__main__':sys.exit(main())
