"""Inject enum-match faults in isolated compiler copies."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('wrong_arm_tag','async_lowering.py',
     'tags = tuple(list(enum_layouts[enum_type]).index(arm[1]) for arm in match.args[1])',
     'tags = tuple(0 for arm in match.args[1])',
     'test_three_arms_reordered_with_suspension_model'),
    ('release_match_too_early','async_lowering.py',
     "local_refs['\\0match:' + holder] = held, float('inf')",
     "local_refs['\\0match:' + holder] = held, -1",
     'test_match_reserves_carrier_until_arm_exit'),
    ('lose_mutable_carrier','crust.py',
     "key = ('.' if binding.alloc.typ in self.struct_fields else '') + binding.reserved_field",
     "key = '.' + binding.reserved_field",
     'test_returned_mutable_projection_reserves_caller'),
    ('lose_shared_capture_projection','crust.py',
     "paths = tuple(path for path in paths if not path or '.'.join(path) == field.lstrip('.'))",
     "paths = ()",
     'test_shared_projection_outlives_owned_carrier'),
    ('read_instead_of_reborrow','async_lowering.py',
     "mode = 'mut' if (match.mutable or match.consuming) and (declared == '&mut Int' or owned) else 'ref'",
     "mode = 'ref'",
     'test_mutable_projection_and_reborrow_inside_arm'),
)

def main():
    suite='test_async_enum_match.AsyncEnumMatchTests'
    baseline=run(ROOT,suite)
    print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    passed=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-enum-match-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;source=path.read_text()
            assert source.count(before)==1,(name,source.count(before))
            path.write_text(source.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        passed &= detected
    return int(not passed)

if __name__=='__main__':sys.exit(main())
