"""Mutate field-effect inference in isolated module copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('omit_completed_writes', 'async_structure_effects.py',
     'self.results.summaries[symbol] = result',
     'self.results.summaries[symbol] = replace(result, structure_fields=())',
     'test_nested_awaits_and_parameter_permutation'),
    ('forget_launch_failure', 'async_structure_effects.py',
     "if task.mode == 'execution':\n                # LaunchFailed executes no body.",
     "if False:\n                # LaunchFailed executes no body.",
     'test_launch_failure_preserves_old_field_alternative'),
    ('invent_divergent_continuation', 'async_structure_effects.py',
     'if not summary.may_complete:\n                    continue\n                branch, completed',
     'if False:\n                    continue\n                branch, completed',
     'test_noncompleting_child_does_not_invent_a_continuation'),
    ('unknown_becomes_empty', 'async_structure_effects.py',
     'AsyncStructureEffects(parameters, None, str(error))',
     'AsyncStructureEffects(parameters, (), str(error))',
     'test_incomplete_is_not_an_empty_contract'),
    ('lose_choice_captures', 'results.py',
     'pending_structure_calls=frozenset(call for value in returning for call in value.pending_structure_calls)',
     'pending_structure_calls=frozenset()',
     'test_task_choices_keep_capture_alternatives'),
    ('skip_sync_field_effect', 'results.py',
     'for parameter, fields in summary.structure_fields:',
     'for parameter, fields in ():',
     'test_independent_branch_model'),
    ('forget_deferred_sync_boundary', 'async_structure_effects.py',
     'if any(isinstance(value, Value) and value.pending_structure_calls for value in actuals):',
     'if False:',
     'test_deferred_writes_cannot_disappear_inside_sync_handle_helper'),
    ('drop_completed_reference_targets', 'async_structure_effects.py',
     'reference_targets=frozenset(target for value in values for target in value.reference_targets),',
     'reference_targets=frozenset(),',
     'test_completion_pairs_field_writes_with_detached_result'),
    ('lose_mutable_result_carrier', 'async_structure_effects.py',
     "symbol = '\\0async_' + phase + ':' + name",
     "result = replace(result, reference_targets=frozenset(replace(t, kind='parameter', field='') if t.kind == 'indirect_field_parameter' else t for t in result.reference_targets))\n        symbol = '\\0async_' + phase + ':' + name",
     'test_mutable_return_preserves_carrier_in_completion_contract'),
    ('use_current_field_instead_of_input_snapshot', 'async_structure_effects.py',
     "symbol = '\\0async_' + phase + ':' + name",
     "result = replace(result, reference_targets=frozenset(replace(t, kind='field_parameter') if t.kind == 'detached_field_parameter' else t for t in result.reference_targets))\n        symbol = '\\0async_' + phase + ':' + name",
     'test_result_detached_before_write_uses_input_snapshot'),
    ('lose_named_carrier_update', 'async_structure_effects.py',
     'for index, _ in result.structure_fields:', 'for index, _ in ():',
     'test_independent_completion_result_and_write_model'),
)


def main():
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-async-field-effects-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            path = target / filename
            original = path.read_text()
            assert original.count(before) == 1, (name, original.count(before))
            path.write_text(original.replace(before, after))
            script = f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT / 'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_async_structure_effects.AsyncStructureEffectsTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            run = subprocess.run([sys.executable, '-c', script], cwd=directory,
                                 capture_output=True, text=True, timeout=60)
        detected = run.returncode == 1 and 'AssertionError' in run.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if run.returncode == 0 else 'INCONCLUSIVE', flush=True)
        print(run.stdout + run.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
