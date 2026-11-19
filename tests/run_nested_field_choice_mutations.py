"""Perturb alternative-location analysis in isolated compiler copies."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('keep_first_choice_only','array_syntax.py',
     "for choice in getattr(value, 'structure_choices', ()) or (value,)))",
     "for choice in getattr(value, 'structure_choices', ()) or (value,)))[:1]",
     'test_recorded_choice_and_both_possible_targets'),
    ('apply_all_choices_sequentially','results.py',
     'for choice in carrier.structure_choices:\n                branch = environment.copy()\n                self.update_structure',
     'for choice in carrier.structure_choices:\n                branch = environment\n                self.update_structure',
     'test_independent_possible_location_model'),
    ('forget_constraint_choices','constraints.py',
     'structure_choices=merge_structure_choices(values),',
     'structure_choices=(),','test_mixed_whole_object_and_descendant'),
    ('forget_old_nested_target','crust.py',
     "if target.kind == 'field_parameter' and '/' in target.field:",
     'if False:', 'test_recorded_sync_counterexample'),
    ('forget_unchanged_mutable_capability','async_lowering.py',
     "own_capability = field_type == '&mut Int' and any(",
     'own_capability = False and any(', 'test_mutable_target_choice'),
)

def main():
    suite='test_nested_field_choices.NestedFieldChoiceTests'
    baseline=run(ROOT,suite)
    print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-choice-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;source=path.read_text()
            assert source.count(before)==1,(name,source.count(before))
            path.write_text(source.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)

if __name__=='__main__':sys.exit(main())
