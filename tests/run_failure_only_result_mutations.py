"""Challenge known absence, unknown summaries, and successful alternatives."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('reject_failure_only_result', 'async_structure_effects.py',
     '(not values and not joined)', 'not values',
     'test_recorded_field_write_after_failure_only_handle'),
    ('unknown_becomes_nonreturning', 'async_structure_effects.py',
     '                if not summary.complete:\n                    raise IncompleteStructureEffects(summary.reason)',
     '                if False:\n                    raise IncompleteStructureEffects(summary.reason)',
     'test_unknown_child_does_not_become_failure_only'),
    ('invent_direct_completion', 'async_structure_effects.py',
     '                if not summary.may_complete:\n                    continue',
     '                if False:\n                    continue',
     'test_direct_await_still_has_no_continuation'),
    ('lose_possible_owned_source', 'async_structure_effects.py',
     'value = merge_owned_values(values) if values else Value(mode, typ, absent_owned_payload=True)',
     'value = Value(mode, typ, absent_owned_payload=True)',
     'test_completing_alternative_keeps_payload_source'),
    ('lose_absence_evidence', 'async_structure_effects.py',
     'else Value(mode, typ, absent_owned_payload=True)',
     'else Value(mode, typ)',
     'test_failure_only_owned_envelope_can_be_returned'),
    ('forget_absence_at_contract_call', 'results.py',
     'absent_owned_payload=not candidates and (summary.absent_owned_payload or',
     'absent_owned_payload=False and (summary.absent_owned_payload or',
     'test_proven_absence_survives_control_and_contract_relays'),
    ('leak_prepared_result', 'async_lowering.py',
     'prepared_owners.append(pending)', 'pass  # forgotten prepared owner',
     'test_sync_owned_result_bridge_cleanup_and_prepared_argument'),
    ('destroy_exported_result_in_bridge', 'crust.py',
     "result[0] in ('owned', 'task', 'execution', *JOIN_RESULT_TYPES)",
     "result[0] in ('owned', 'task', 'execution')",
     'test_nested_owned_result_bridge'),
)


def main():
    suite = 'test_async_failure_only_results.AsyncFailureOnlyResultsTests'
    baseline = run(ROOT, suite)
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout+baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-failure-only-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            result=run(target,suite+'.'+method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr and 'internal error:' not in result.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
