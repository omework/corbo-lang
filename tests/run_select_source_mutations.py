"""Mutate source Select lowering; keep acceptance and native oracles unchanged."""
from pathlib import Path
import shutil
import sys
import tempfile

from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('release_loser_loans_after_await',
     'selections[selection_name] = replace(selection, awaited=True, loans=retained)',
     'selections[selection_name] = replace(selection, awaited=True, loans=retained)\n            active_loans.pop(id(retained), None)',
     'test_shared_loser_holds_capture_until_drop_or_scope_end'),
    ('forget_awaited_state',
     'selections[selection_name] = replace(selection, awaited=True, loans=retained)',
     'selections[selection_name] = replace(selection, loans=retained)',
     'test_single_await_mutability_and_explicit_move'),
    ('forget_lexical_mutability',
     'del selections[name]\n                mutable.discard(name)',
     'del selections[name]',
     'test_selection_mutability_is_lexical'),
    ('omit_selection_drop',
     "steps.append(f'task_select_drop(&{selection.c});')",
     "steps.append('/* omitted selection drop */')",
     'test_owned_loser_cleanup_and_loop_slot_reuse'),
    ('omit_suspended_selection_drop',
     "cleanup.append(f'task_select_drop(&{selection.c});')",
     "cleanup.append('/* omitted nested selection cleanup */')",
     'test_nested_suspended_selection_uses_generated_cleanup'),
    ('forget_exported_capture_lifetimes',
     "if kind == 'selection':\n            loans = value.loans",
     "if kind == 'selection':\n            loans = []",
     'test_transferred_selection_cannot_outlive_capture_or_owned_pool'),
    ('forget_returned_borrow_targets',
     'returned_loans = list(dict.fromkeys(loan for path in poll_paths for record, candidates in path\n'
     '                if any(effects.may_complete for effects, _, _ in candidates) for loan in record[4]))',
     'returned_loans = []',
     'test_returned_borrows_survive_selection_drop_but_keep_targets'),
    ('reset_awaited_state_on_export',
     'return kind, SelectionState(f\'(*{target})\', tuple(selected_branches), loans, child_returns_int,',
     'return kind, SelectionState(f\'(*{target})\', tuple(selected_branches), loans, False,',
     'test_transferred_awaited_selection_stays_consumed_and_keeps_loser'),
    ('flatten_selection_paths',
     'for path in selection.paths or (selection.branches,):',
     'for path in (selection.branches,):',
     'test_selection_alternatives_keep_distinct_poll_orders'),
    ('require_never_polled_contract',
     'if all(not effects.may_suspend for effects, _, _ in candidates):',
     'if False:',
     'test_never_polled_branch_needs_no_suspension_contract'),
    ('retain_certain_winner_capture',
     'certain = winners[0] if len(winners) == 1 else None',
     'certain = None',
     'test_certain_winner_releases_only_its_finished_captures'),
    ('split_equivalent_wait_reservations',
     'return selection_loan_sets.setdefault((selection.c, tuple(retained)), retained)',
     'return retained',
     'test_outer_selection_waited_once_on_each_path'),
)


def main():
    suite = 'test_select_source.SelectSourceTests'
    baseline = run(ROOT, suite)
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-select-source-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            path = target / 'async_lowering.py'
            original = path.read_text()
            assert original.count(before) == 1, (name, original.count(before))
            path.write_text(original.replace(before, after))
            result = run(target, suite + '.' + method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr
            and 'internal error:' not in result.stderr)
        status = 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE'
        print(name, status, flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
