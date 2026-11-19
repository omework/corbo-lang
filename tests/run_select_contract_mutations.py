"""Mutate Select contract composition without editing its independent oracles."""
from pathlib import Path
import shutil
import sys
import tempfile

from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('allow_implicit_branches', 'crust.py',
     "not arguments or any(argument[0] not in ('down', 'transfer') for argument in arguments)",
     'not arguments', 'test_parser_requires_each_explicit_transfer'),
    ('use_final_effect_for_loser', 'async_structure_effects.py',
     "summary.suspension_result, actuals, environment, line, 'suspension')\n                finally:",
     "summary.completion_result, actuals, environment, line, 'suspension')\n                finally:",
     'test_loser_retains_prefix_instead_of_final_restoration'),
    ('forget_unpolled_alternative', 'async_structure_effects.py',
     "alternatives = [({'next'}, environment.copy())] if unpolled else []", 'alternatives = []',
     'test_later_loser_can_be_unpolled_after_conditional_first_pause'),
    ('erase_winner_result_targets', 'async_structure_effects.py',
     'reference_targets=frozenset(target for value in values for target in value.reference_targets)',
     'reference_targets=frozenset()',
     'test_returned_borrow_is_only_from_a_possible_winner'),
    ('forget_parent_suspension', 'async_structure_effects.py',
     'self.observe_suspension(partial, line)', 'pass',
     'test_all_branches_can_suspend_then_parent_has_prefix'),
    ('accept_mixed_results', 'async_structure_effects.py',
     "raise IncompleteStructureEffects('Select exige le même type de résultat dans chaque branche')",
     'pass', 'test_unknown_prefix_and_different_result_types_remain_unknown'),
    ('observe_never_polled_recursive_body', 'async_structure_effects.py',
     'candidates = [] if unreachable else self.select_candidates(task)',
     'candidates = self.select_candidates(task)',
     'test_unreachable_later_body_does_not_need_a_prefix_contract'),
    ('lose_selection_captures', 'async_structure_effects.py',
     "Value('selection', f'Select<{mode}:{typ}>', pending_structure_calls=frozenset({token}))",
     "Value('selection', f'Select<{mode}:{typ}>')",
     'test_conditional_selection_transfer_keeps_capture_alternatives'),
)


def main():
    suite = 'test_select_contracts.SelectContractTests'
    baseline = run(ROOT, suite)
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-select-contracts-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            path = target / filename
            original = path.read_text()
            expected = 2 if name == 'accept_mixed_results' else 1
            assert original.count(before) == expected, (name, original.count(before))
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
