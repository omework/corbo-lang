"""Perturb prefix inference only, using unchanged contract/runtime oracles."""
from pathlib import Path
import shutil
import sys
import tempfile

from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('forget_yield', 'results.py',
     'self.observe_suspension(environment, line)', 'pass',
     'test_independent_finite_trace_model'),
    ('replace_union_by_last_state', 'async_structure_effects.py',
     'fields[field] = fields.get(field, frozenset()) | targets', 'fields[field] = targets',
     'test_independent_finite_trace_model'),
    ('forget_awaited_child_prefix', 'async_structure_effects.py',
     'self.observe_child_suspensions(name, summary, actuals, environment, line)', 'pass',
     'test_child_prefix_survives_permutation_alias_and_shadow'),
    ('invent_completion_for_nonterminating_child', 'async_structure_effects.py',
     'if not summary.may_complete:\n                    continue\n                branch, completed',
     'if False:\n                    continue\n                branch, completed',
     'test_noncompleting_child_still_contributes_suspended_states'),
    ('confuse_completion_and_suspension', 'async_structure_effects.py',
     'completion_result=result,', 'completion_result=context.suspension_summary(),',
     'test_restoration_is_completion_only'),
    ('unknown_becomes_empty', 'async_structure_effects.py',
     'if self.suspension_reason:\n            return None',
     "if self.suspension_reason:\n            return FunctionResult('void', 'Void')",
     'test_unsupported_prefix_does_not_disguise_itself_as_empty'),
    ('ignore_nondurable_prefix', 'async_structure_effects.py',
     "self.suspension_reason = 'cible non durable dans un champ au point de suspension'", 'pass',
     'test_unsupported_prefix_does_not_disguise_itself_as_empty'),
    ('untracked_containers_become_empty', 'async_structure_effects.py',
     "self.suspension_reason = 'effets suspendus des autres porteurs de références non raccordés'", 'pass',
     'test_untracked_reference_containers_are_not_empty_effects'),
)


def main():
    suite = 'test_suspension_effects.SuspensionEffectsTests'
    baseline = run(ROOT, suite)
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-suspension-effects-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            path = target / filename
            original = path.read_text()
            assert original.count(before) == 1, (name, original.count(before))
            path.write_text(original.replace(before, after))
            result = run(target, suite + '.' + method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr
        status = 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE'
        print(name, status, flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
